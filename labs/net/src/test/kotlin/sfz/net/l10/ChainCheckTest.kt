package sfz.net.l10

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.support.ManualClock
import java.security.cert.CertPathValidator
import java.security.cert.CertPathValidatorException
import java.security.cert.CertificateFactory
import java.security.cert.PKIXParameters
import java.security.cert.TrustAnchor
import java.security.cert.X509Certificate
import java.time.Instant
import java.util.Date

/**
 * Certificates made by make-certs.sh in src/test/resources/sfz/net/l10/, with fixed dates. The clock
 * stands at 2026-11-10, three days into api.pem's 45 days.
 */
class ChainCheckTest {
    private fun pem(name: String): X509Certificate =
        CertificateFactory.getInstance("X.509").generateCertificate(
            javaClass.classLoader.getResourceAsStream("sfz/net/l10/$name.pem") ?: error("missing $name.pem"),
        ) as X509Certificate

    private val root = pem("root")
    private val inter = pem("inter")
    private val api = pem("api")
    private val clock = ManualClock(Instant.parse("2026-11-10T12:00:00Z").toEpochMilli())
    private val check = ChainCheck(listOf(root), clock)

    private val ROOT = "CN=Pay Test Root CA,O=Pay Test"
    private val INTER = "CN=Pay Test Issuing CA 1,O=Pay Test"

    /** The JDK's own PKIX validator on the same chain: null when it accepts, else its reason. */
    private fun pkix(chain: List<X509Certificate>): String? = try {
        val params = PKIXParameters(setOf(TrustAnchor(root, null))).apply {
            isRevocationEnabled = false
            date = Date(clock())
        }
        CertPathValidator.getInstance("PKIX").validate(CertificateFactory.getInstance("X.509").generateCertPath(chain), params)
        null
    } catch (e: CertPathValidatorException) {
        e.reason.toString()
    }

    @Test
    fun `leaf, intermediate and a trusted root are trusted, and the JDK agrees`() {
        assertThat(check.check(listOf(api, inter), "api.pay.test"))
            .isEqualTo(Verdict.Trusted(listOf("CN=api.pay.test", INTER, ROOT)))
        assertThat(pkix(listOf(api, inter))).isNull()
    }

    @Test
    fun `a root the server sends along changes nothing`() {
        assertThat(check.check(listOf(api, inter, root), "api.pay.test"))
            .isEqualTo(Verdict.Trusted(listOf("CN=api.pay.test", INTER, ROOT)))
    }

    @Test
    fun `a server that forgets its intermediate can't be checked`() {
        assertThat(check.check(listOf(api), "api.pay.test")).isEqualTo(Verdict.UnknownIssuer("CN=api.pay.test"))
        assertThat(pkix(listOf(api))).`as`("the JDK fails it too").isNotNull()
    }

    @Test
    fun `a chain that ends in someone else's root is not trusted`() {
        assertThat(check.check(listOf(pem("other"), pem("other-root")), "api.pay.test"))
            .isEqualTo(Verdict.UnknownIssuer("CN=Issuer Example Root CA,O=Issuer Example"))
    }

    @Test
    fun `copying the issuer's name is not enough, the signature has to verify`() {
        assertThat(check.check(listOf(pem("forged"), inter), "api.pay.test")).isEqualTo(Verdict.BadSignature("CN=api.pay.test"))
        assertThat(check.check(listOf(pem("forged"), pem("fake-inter")), "api.pay.test"))
            .`as`("the impostor CA signed itself, and no trusted root signed it")
            .isEqualTo(Verdict.UnknownIssuer(INTER))
    }

    @Test
    fun `a server certificate can't sign certificates of its own`() {
        assertThat(check.check(listOf(pem("admin"), api, inter), "admin.pay.test")).isEqualTo(Verdict.NotACa("CN=api.pay.test"))
    }

    @Test
    fun `an expired certificate fails however good its chain is`() {
        assertThat(check.check(listOf(pem("api-expired"), inter), "api.pay.test")).isEqualTo(Verdict.Expired("CN=api.pay.test"))
        assertThat(pkix(listOf(pem("api-expired"), inter))).isEqualTo("EXPIRED")
        clock.advanceSeconds(43L * 24 * 3600)                    // 2026-12-23: past api.pem's 45 days
        assertThat(check.check(listOf(api, inter), "api.pay.test")).isEqualTo(Verdict.Expired("CN=api.pay.test"))
    }

    @Test
    fun `the name comes from subjectAltName`() {
        assertThat(check.check(listOf(pem("ledger"), inter), "api.pay.test"))
            .isEqualTo(Verdict.WrongName("api.pay.test", listOf("ledger.pay.test")))
        assertThat(pkix(listOf(pem("ledger"), inter))).`as`("PKIX checks the chain, not the name").isNull()
    }

    @Test
    fun `a wildcard covers exactly one label`() {
        assertThat(ChainCheck.hostMatches("*.pay.test", "api.pay.test")).isTrue()
        assertThat(ChainCheck.hostMatches("*.pay.test", "a.b.pay.test")).isFalse()
        assertThat(ChainCheck.hostMatches("*.pay.test", "pay.test")).isFalse()
        assertThat(ChainCheck.hostMatches("api.*.test", "api.pay.test")).`as`("* only as the whole leftmost label").isFalse()
        assertThat(ChainCheck.hostMatches("API.pay.test", "api.PAY.test")).isTrue()
        assertThat(ChainCheck.hostMatches("api.pay.test", "api.pay.test.evil.example")).isFalse()
        val wildcard = pem("wildcard")
        assertThat(check.check(listOf(wildcard, inter), "ledger.pay.test")).isInstanceOf(Verdict.Trusted::class.java)
        assertThat(check.check(listOf(wildcard, inter), "a.b.pay.test"))
            .isEqualTo(Verdict.WrongName("a.b.pay.test", listOf("*.pay.test", "pay.test")))
    }
}
