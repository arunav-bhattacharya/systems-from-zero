package sfz.net.l10

import java.security.cert.X509Certificate

/** What a client concludes about the certificates a server sent. */
sealed interface Verdict {
    /** Every link checks out and the leaf names the host. [path] holds the subjects, leaf first, root last. */
    data class Trusted(val path: List<String>) : Verdict

    /** [subject]'s issuer is neither the next certificate in the chain nor one of the trusted roots. */
    data class UnknownIssuer(val subject: String) : Verdict

    /** The issuer's public key does not verify [subject]'s signature: someone copied a name. */
    data class BadSignature(val subject: String) : Verdict

    /** [subject] signed another certificate, but it isn't a CA (basicConstraints says CA:FALSE). */
    data class NotACa(val subject: String) : Verdict

    /** [subject] is outside its notBefore..notAfter window at the time of the check. */
    data class Expired(val subject: String) : Verdict

    /** The chain is good but no subjectAltName DNS entry of the leaf matches [host]. */
    data class WrongName(val host: String, val names: List<String>) : Verdict
}

/**
 * The checks a TLS client makes on a server's Certificate message, written out by hand.
 *
 * [roots] are the trust anchors: the certificates this client trusts without proof (the JDK's
 * `cacerts`, or one private root). Time comes from [clock] in milliseconds, so tests can pick it.
 * A subject is written as `cert.subjectX500Principal.name`, for example `"CN=api.pay.test"`.
 */
class ChainCheck(private val roots: List<X509Certificate>, private val clock: () -> Long = System::currentTimeMillis) {

    /**
     * Checks [chain] as a server sent it (leaf first, then intermediates, maybe the root) for [host].
     *
     * Walk up from the leaf. For each certificate:
     * 1. Find its issuer: the next certificate in the chain, or, after the last one, the root in
     *    [roots] whose subject equals this certificate's issuer. The next certificate must have that
     *    subject too. No issuer found: [Verdict.UnknownIssuer]. A certificate that is itself one of
     *    [roots] ends the walk: it needs no issuer.
     * 2. Verify the signature with the issuer's public key (`cert.verify(issuer.publicKey)` throws if
     *    it fails): [Verdict.BadSignature].
     * 3. The issuer must be a CA: `issuer.basicConstraints` is -1 for a non-CA: [Verdict.NotACa].
     * 4. The certificate must be valid at `clock()`: `cert.checkValidity(Date(clock()))` throws if not:
     *    [Verdict.Expired]. Check the root's dates too.
     * Then check the name: some DNS entry (type 2) of the leaf's `subjectAlternativeNames` must match
     * [host] by [hostMatches]. The CN is never used. Otherwise: [Verdict.WrongName].
     */
    fun check(chain: List<X509Certificate>, host: String): Verdict {
        TODO("walk leaf to root: issuer, signature, CA flag, dates; then the name")
    }

    companion object {
        /**
         * Does a certificate's DNS name [pattern] cover [host]? Case doesn't matter. A `*` is allowed
         * only as the whole leftmost label and stands for exactly one label: `*.pay.test` matches
         * `api.pay.test` but not `pay.test` or `a.b.pay.test`. Anything else must match exactly.
         */
        fun hostMatches(pattern: String, host: String): Boolean {
            TODO("exact match, or a leftmost * that covers exactly one label")
        }
    }
}
