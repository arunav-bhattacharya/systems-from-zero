package sfz.sql.l15

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.sql.support.CourseDb

/**
 * Lesson sql-15, exercise 1: a model of pg_hba.conf. Your code is in src/main/kotlin/sfz/sql/l15/Hba.kt.
 * These tests need no database: they run in a second.
 */
class HbaTest {

    private fun decide(conf: String, attempt: Attempt): Decision = Hba.decide(Hba.parse(conf.trimIndent()), attempt)

    private fun tcp(user: String, database: String, address: String, ssl: Boolean = false, memberOf: Set<String> = emptySet()) =
        Attempt(Transport.TCP, user, database, address, ssl = ssl, memberOf = memberOf)

    // ------------------------------------------------------------------ inCidr

    @Test
    fun `a 16-bit prefix keeps the first two bytes`() {
        assertThat(Hba.inCidr("10.1.0.0", "10.1.0.0/16")).isTrue()
        assertThat(Hba.inCidr("10.1.255.255", "10.1.0.0/16")).isTrue()
        assertThat(Hba.inCidr("10.2.0.0", "10.1.0.0/16")).describedAs("10.2.0.0 is outside 10.1.0.0/16").isFalse()
        assertThat(Hba.inCidr("10.0.255.255", "10.1.0.0/16")).isFalse()
    }

    @Test
    fun `a prefix that does not end on a byte splits the byte`() {
        assertThat(Hba.inCidr("192.168.1.128", "192.168.1.128/25")).isTrue()
        assertThat(Hba.inCidr("192.168.1.255", "192.168.1.128/25")).isTrue()
        assertThat(Hba.inCidr("192.168.1.127", "192.168.1.128/25")).describedAs("/25 is .128 to .255").isFalse()
        assertThat(Hba.inCidr("172.16.0.1", "172.16.0.0/12")).isTrue()
        assertThat(Hba.inCidr("172.31.255.254", "172.16.0.0/12")).isTrue()
        assertThat(Hba.inCidr("172.32.0.1", "172.16.0.0/12")).isFalse()
    }

    @Test
    fun `slash 32 is one address and slash 0 is all of IPv4`() {
        assertThat(Hba.inCidr("10.20.0.7", "10.20.0.7/32")).isTrue()
        assertThat(Hba.inCidr("10.20.0.8", "10.20.0.7/32")).isFalse()
        assertThat(Hba.inCidr("203.0.113.9", "0.0.0.0/0")).isTrue()
    }

    @Test
    fun `IPv4 blocks never match IPv6 clients, and the other way round`() {
        assertThat(Hba.inCidr("::1", "127.0.0.1/32")).describedAs("::1 is IPv6, 127.0.0.1/32 is IPv4").isFalse()
        assertThat(Hba.inCidr("127.0.0.1", "::1/128")).isFalse()
        assertThat(Hba.inCidr("::1", "0.0.0.0/0")).describedAs("0.0.0.0/0 is every IPv4 address, and no IPv6 one").isFalse()
        assertThat(Hba.inCidr("::1", "::1/128")).isTrue()
        assertThat(Hba.inCidr("2001:db8:5:1::20", "2001:db8::/32")).isTrue()
        assertThat(Hba.inCidr("2001:db9::1", "2001:db8::/32")).isFalse()
    }

    // ------------------------------------------------------------------ decide

    @Test
    fun `the first matching line decides, even when a later line is more specific`() {
        val conf = """
            host  all  all  10.0.0.0/8    scram-sha-256
            host  all  all  10.1.2.3/32   trust
        """
        assertThat(decide(conf, tcp("payments_app", "payments", "10.1.2.3")))
            .describedAs("line 1 already matches 10.1.2.3, so line 2 is never read")
            .isEqualTo(Decision.Authenticate(1, "scram-sha-256"))
    }

    @Test
    fun `a broad reject above an allow line locks everyone in its range out`() {
        val conf = """
            # a lockout: the reject was meant to go at the bottom
            host  all       all           0.0.0.0/0    reject
            host  payments  payments_app  10.20.0.0/16 scram-sha-256
        """
        assertThat(decide(conf, tcp("payments_app", "payments", "10.20.0.7"))).isEqualTo(Decision.Rejected(2))
    }

    @Test
    fun `no matching line means no entry, and the client is refused`() {
        val conf = """
            host  payments  payments_app  10.20.0.0/16  scram-sha-256
        """
        val attempt = tcp("payments_app", "payments", "10.30.0.7")
        val d = decide(conf, attempt)
        assertThat(d).describedAs(Hba.message(d, attempt)).isEqualTo(Decision.NoEntry)
        assertThat(Hba.message(d, attempt))
            .isEqualTo("FATAL:  no pg_hba.conf entry for host \"10.30.0.7\", user \"payments_app\", database \"payments\", no encryption")
    }

    @Test
    fun `local lines match only the socket, host lines only TCP`() {
        val conf = """
            local  all  all                 peer
            host   all  all  127.0.0.1/32   scram-sha-256
        """
        assertThat(decide(conf, Attempt(Transport.SOCKET, "postgres", "payments"))).isEqualTo(Decision.Authenticate(1, "peer"))
        assertThat(decide(conf, tcp("postgres", "payments", "127.0.0.1"))).isEqualTo(Decision.Authenticate(2, "scram-sha-256"))
    }

    @Test
    fun `hostssl matches only TLS connections, hostnossl only plain ones, host both`() {
        val conf = """
            hostnossl  all  all  0.0.0.0/0  reject
            hostssl    all  all  0.0.0.0/0  scram-sha-256
        """
        assertThat(decide(conf, tcp("payments_app", "payments", "10.20.0.7", ssl = false))).isEqualTo(Decision.Rejected(1))
        assertThat(decide(conf, tcp("payments_app", "payments", "10.20.0.7", ssl = true))).isEqualTo(Decision.Authenticate(2, "scram-sha-256"))
        assertThat(decide("host all all 0.0.0.0/0 md5", tcp("a", "b", "10.0.0.1", ssl = true))).isEqualTo(Decision.Authenticate(1, "md5"))
    }

    @Test
    fun `all never matches a replication connection, and replication matches nothing else`() {
        val conf = """
            host  all          all         0.0.0.0/0  scram-sha-256
            host  replication  replicator  0.0.0.0/0  scram-sha-256
        """
        val standby = Attempt(Transport.TCP, "replicator", address = "172.21.0.3", replication = true)
        assertThat(decide(conf, standby)).describedAs("a standby skips line 1").isEqualTo(Decision.Authenticate(2, "scram-sha-256"))
        assertThat(decide("host all all 0.0.0.0/0 scram-sha-256", standby)).isEqualTo(Decision.NoEntry)
        assertThat(decide("host replication all 0.0.0.0/0 trust", tcp("app", "replication", "10.0.0.1")))
            .describedAs("a database literally named replication is not a replication connection")
            .isEqualTo(Decision.NoEntry)
    }

    @Test
    fun `plus role matches the role and its members, a bare name only that role`() {
        val conf = """
            host  all  +ops     10.0.0.0/8  scram-sha-256
            host  all  reports  10.0.0.0/8  reject
        """
        assertThat(decide(conf, tcp("asha", "payments", "10.0.0.5", memberOf = setOf("ops")))).isEqualTo(Decision.Authenticate(1, "scram-sha-256"))
        assertThat(decide(conf, tcp("ops", "payments", "10.0.0.5"))).isEqualTo(Decision.Authenticate(1, "scram-sha-256"))
        assertThat(decide(conf, tcp("reports", "payments", "10.0.0.5", memberOf = setOf("readers")))).isEqualTo(Decision.Rejected(2))
        assertThat(decide("host all ops 10.0.0.0/8 trust", tcp("asha", "payments", "10.0.0.5", memberOf = setOf("ops"))))
            .describedAs("without the +, only the role named ops matches")
            .isEqualTo(Decision.NoEntry)
    }

    @Test
    fun `comma lists, sameuser and samerole`() {
        val conf = """
            host  payments,ledger  payments_app,settlement  10.20.0.0/16  scram-sha-256
            host  sameuser         all                      10.30.0.0/16  scram-sha-256
            host  samerole         all                      10.40.0.0/16  scram-sha-256
        """
        assertThat(decide(conf, tcp("settlement", "ledger", "10.20.1.1"))).isEqualTo(Decision.Authenticate(1, "scram-sha-256"))
        assertThat(decide(conf, tcp("settlement", "reports", "10.20.1.1"))).isEqualTo(Decision.NoEntry)
        assertThat(decide(conf, tcp("kofi", "kofi", "10.30.0.9"))).isEqualTo(Decision.Authenticate(2, "scram-sha-256"))
        assertThat(decide(conf, tcp("kofi", "payments", "10.30.0.9"))).isEqualTo(Decision.NoEntry)
        assertThat(decide(conf, tcp("kofi", "analytics", "10.40.0.9", memberOf = setOf("analytics")))).isEqualTo(Decision.Authenticate(3, "scram-sha-256"))
        assertThat(decide(conf, tcp("kofi", "analytics", "10.40.0.9"))).isEqualTo(Decision.NoEntry)
    }

    @Test
    fun `the Docker image's file with the Try it's reject line on top`() {
        val lines = Hba.parse(CourseDb.resource("sfz/sql/l15/docker_pg_hba.conf"))
        val toCourse = tcp("sfz", "course", "127.0.0.1")
        assertThat(Hba.decide(lines, toCourse)).isEqualTo(Decision.Rejected(1))
        assertThat(Hba.message(Hba.decide(lines, toCourse), toCourse))
            .isEqualTo("FATAL:  pg_hba.conf rejects connection for host \"127.0.0.1\", user \"sfz\", database \"course\", no encryption")
        assertThat(Hba.decide(lines, tcp("sfz", "sfz", "127.0.0.1"))).describedAs("another database").isEqualTo(Decision.Authenticate(9, "trust"))
        assertThat(Hba.decide(lines, Attempt(Transport.SOCKET, "sfz", "course"))).describedAs("the socket").isEqualTo(Decision.Authenticate(7, "trust"))
        assertThat(Hba.decide(lines, tcp("sfz", "course", "::1"))).describedAs("psql -h localhost connects over ::1").isEqualTo(Decision.Authenticate(11, "trust"))
        assertThat(Hba.decide(lines, tcp("sfz", "course", "192.168.65.1"))).describedAs("from the laptop, through Docker").isEqualTo(Decision.Authenticate(18, "scram-sha-256"))
        assertThat(Hba.decide(lines, Attempt(Transport.TCP, "sfz", address = "172.21.0.3", replication = true)))
            .describedAs("a standby on another container: the last line says all, which never matches replication")
            .isEqualTo(Decision.NoEntry)
    }
}
