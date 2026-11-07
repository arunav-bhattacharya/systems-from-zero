package sfz.net.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.l09.ResolverCache.Lookup
import sfz.net.support.ManualClock

class ResolverCacheTest {
    private val clock = ManualClock()
    private val cache = ResolverCache(clock)

    /** The real answers from the captures, decoded with the reference decoder written out here. */
    private val example = DnsMessage(
        39300, 0x8180, listOf(Question("example.com", RecordType.A)),
        listOf(
            ResourceRecord("example.com", RecordType.A, 1, 30, RData.Address("172.66.147.243")),
            ResourceRecord("example.com", RecordType.A, 1, 30, RData.Address("104.20.23.154")),
        ),
        emptyList(), emptyList(),
    )
    private val wikipedia = DnsMessage(
        60427, 0x8180, listOf(Question("www.wikipedia.org", RecordType.A)),
        listOf(
            ResourceRecord("www.wikipedia.org", RecordType.CNAME, 1, 86222, RData.Name("dyna.wikimedia.org")),
            ResourceRecord("dyna.wikimedia.org", RecordType.A, 1, 2, RData.Address("198.35.26.224")),
        ),
        emptyList(), emptyList(),
    )

    private fun soa(ttl: Long, minimum: Long) =
        ResourceRecord("pay.test", RecordType.SOA, 1, ttl, RData.Soa("ns.pay.test", "hostmaster.pay.test", 1, 7200, 3600, 1209600, minimum))

    private fun negative(name: String, rcode: Int, vararg authority: ResourceRecord) =
        DnsMessage(1, 0x8180 or rcode, listOf(Question(name, RecordType.A)), emptyList(), authority.toList(), emptyList())

    private fun ttls(lookup: Lookup) = (lookup as Lookup.Hit).records.map { it.ttl }

    @Test
    fun `an answer is served from the cache with its TTL counting down, then it expires`() {
        cache.put(example)
        assertThat(ttls(cache.get("example.com", RecordType.A))).containsExactly(30, 30)
        clock.advanceSeconds(10)
        val hit = cache.get("example.com", RecordType.A) as Lookup.Hit
        assertThat(hit.records.map { it.ttl }).`as`("what the next client is told").containsExactly(20, 20)
        assertThat(hit.records.map { it.data }).containsExactly(RData.Address("172.66.147.243"), RData.Address("104.20.23.154"))
        clock.advanceSeconds(20)
        assertThat(cache.get("example.com", RecordType.A)).isEqualTo(Lookup.Miss)
    }

    @Test
    fun `the TTL left is rounded down to whole seconds`() {
        cache.put(example)
        clock.advance(10_500)
        assertThat(ttls(cache.get("example.com", RecordType.A))).containsExactly(19, 19)
    }

    @Test
    fun `names are case-insensitive, types are not`() {
        cache.put(example)
        assertThat(cache.get("EXAMPLE.com", RecordType.A)).isInstanceOf(Lookup.Hit::class.java)
        assertThat(cache.get("example.com", RecordType.AAAA)).isEqualTo(Lookup.Miss)
    }

    @Test
    fun `a CNAME chain is cached for its shortest TTL`() {
        cache.put(wikipedia)
        clock.advanceSeconds(1)
        assertThat(ttls(cache.get("www.wikipedia.org", RecordType.A))).containsExactly(1, 1)
        clock.advanceSeconds(1)
        assertThat(cache.get("www.wikipedia.org", RecordType.A)).`as`("the A record lived 2 s").isEqualTo(Lookup.Miss)
    }

    @Test
    fun `NXDOMAIN is cached too, for the SOA's TTL`() {
        cache.put(negative("nosuch.pay.test", Rcode.NXDOMAIN, soa(ttl = 60, minimum = 60)))
        clock.advanceSeconds(59)
        assertThat(cache.get("nosuch.pay.test", RecordType.A)).isEqualTo(Lookup.Negative(Rcode.NXDOMAIN, 1))
        clock.advanceSeconds(1)
        assertThat(cache.get("nosuch.pay.test", RecordType.A)).isEqualTo(Lookup.Miss)
    }

    @Test
    fun `the negative TTL is the smaller of the SOA record's TTL and its minimum field`() {
        cache.put(negative("a.pay.test", Rcode.NXDOMAIN, soa(ttl = 900, minimum = 300)))
        cache.put(negative("b.pay.test", Rcode.NXDOMAIN, soa(ttl = 120, minimum = 3600)))
        assertThat(cache.get("a.pay.test", RecordType.A)).isEqualTo(Lookup.Negative(Rcode.NXDOMAIN, 300))
        assertThat(cache.get("b.pay.test", RecordType.A)).isEqualTo(Lookup.Negative(Rcode.NXDOMAIN, 120))
    }

    @Test
    fun `NOERROR with no answers means the name exists without that type, and is cached as a no too`() {
        cache.put(negative("ledger.pay.test", Rcode.NOERROR, soa(ttl = 60, minimum = 60)))
        assertThat(cache.get("ledger.pay.test", RecordType.A)).isEqualTo(Lookup.Negative(Rcode.NOERROR, 60))
    }

    @Test
    fun `a negative answer without an SOA, and a SERVFAIL, are not cached`() {
        cache.put(negative("x.pay.test", Rcode.NXDOMAIN))
        cache.put(negative("y.pay.test", Rcode.SERVFAIL, soa(60, 60)))
        assertThat(cache.get("x.pay.test", RecordType.A)).isEqualTo(Lookup.Miss)
        assertThat(cache.get("y.pay.test", RecordType.A)).isEqualTo(Lookup.Miss)
    }
}
