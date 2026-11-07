package sfz.net.l10

import java.security.cert.X509Certificate
import java.util.Date

/** What a client concludes about the certificates a server sent. */
sealed interface Verdict {
    data class Trusted(val path: List<String>) : Verdict
    data class UnknownIssuer(val subject: String) : Verdict
    data class BadSignature(val subject: String) : Verdict
    data class NotACa(val subject: String) : Verdict
    data class Expired(val subject: String) : Verdict
    data class WrongName(val host: String, val names: List<String>) : Verdict
}

class ChainCheck(private val roots: List<X509Certificate>, private val clock: () -> Long = System::currentTimeMillis) {

    fun check(chain: List<X509Certificate>, host: String): Verdict {
        require(chain.isNotEmpty()) { "a server always sends at least its own certificate" }
        val now = Date(clock())
        val path = mutableListOf<String>()
        var cert = chain[0]
        var next = 1
        while (true) {
            path += subject(cert)
            if (cert in roots) {                                        // trusted without proof: the walk ends here
                if (!validAt(cert, now)) return Verdict.Expired(subject(cert))
                break
            }
            // 1. the issuer: the next certificate the server sent, or after the last one a trusted root
            val issuer = if (next < chain.size) chain[next] else roots.firstOrNull {
                it.subjectX500Principal == cert.issuerX500Principal
            }
            if (issuer == null || issuer.subjectX500Principal != cert.issuerX500Principal) {
                return Verdict.UnknownIssuer(subject(cert))
            }
            // 2. matching names prove nothing: only the issuer's public key can check the signature
            try {
                cert.verify(issuer.publicKey)
            } catch (e: Exception) {
                return Verdict.BadSignature(subject(cert))
            }
            // 3. only a CA may sign certificates (basicConstraints is -1 when CA:FALSE)
            if (issuer.basicConstraints < 0) return Verdict.NotACa(subject(issuer))
            // 4. the dates
            if (!validAt(cert, now)) return Verdict.Expired(subject(cert))
            cert = issuer
            next++
        }
        // the name: subjectAltName DNS entries only (type 2); the CN is ignored
        val names = chain[0].subjectAlternativeNames.orEmpty().filter { it[0] == 2 }.map { it[1] as String }
        if (names.none { hostMatches(it, host) }) return Verdict.WrongName(host, names)
        return Verdict.Trusted(path)
    }

    private fun subject(c: X509Certificate) = c.subjectX500Principal.name

    private fun validAt(c: X509Certificate, now: Date) =
        try { c.checkValidity(now); true } catch (e: Exception) { false }

    companion object {
        fun hostMatches(pattern: String, host: String): Boolean {
            val p = pattern.lowercase().trimEnd('.')
            val h = host.lowercase().trimEnd('.')
            if (!p.startsWith("*.")) return p == h
            // "*.pay.test": the host must be exactly one label followed by ".pay.test"
            val rest = p.substring(1)                                   // ".pay.test"
            if (!h.endsWith(rest)) return false
            val label = h.dropLast(rest.length)
            return label.isNotEmpty() && '.' !in label
        }
    }
}
