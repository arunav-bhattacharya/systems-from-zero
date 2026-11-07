package sfz.net.l09

/**
 * The cache inside a recursive resolver: every answer it got, kept until its TTL runs out. Time
 * comes from [clock] (milliseconds), so tests can move it by hand.
 *
 * Entries are found by question name (case doesn't matter in DNS: `EXAMPLE.com` is `example.com`)
 * and type.
 */
class ResolverCache(private val clock: () -> Long = System::currentTimeMillis) {

    /** What [get] found. */
    sealed interface Lookup {
        /** A cached answer. Every record's TTL is the number of whole seconds it has left. */
        data class Hit(val records: List<ResourceRecord>) : Lookup

        /** A cached "no": NXDOMAIN (no such name) or NOERROR with no answers (no record of that type). */
        data class Negative(val rcode: Int, val ttlLeft: Long) : Lookup

        /** Nothing cached, or it expired: the resolver has to ask. */
        data object Miss : Lookup
    }

    // add your map here: key (lower-case name, type), value: what you stored and when it expires

    /**
     * Stores the response to its first question.
     * - With answers (rcode NOERROR): keep all of them, for the smallest TTL among them. With a
     *   CNAME chain, the chain is only as fresh as its shortest-lived link.
     * - With no answers, NXDOMAIN or NOERROR alike, the authority section should hold the zone's SOA:
     *   cache the "no" for `min(SOA record's TTL, SOA minimum field)` seconds (RFC 2308).
     *   Without an SOA, don't cache it.
     * - Anything else (SERVFAIL and the other errors): don't cache.
     */
    fun put(response: DnsMessage) {
        TODO("positive: min TTL of the answers; negative: min(SOA ttl, SOA minimum); else nothing")
    }

    /**
     * Looks up [name] and [type]. An entry is good while `clock()` is before its expiry: return
     * [Lookup.Hit] with each record's TTL replaced by the seconds left (rounded down), or
     * [Lookup.Negative] with the seconds left. Once it has expired, forget it and return [Lookup.Miss].
     */
    fun get(name: String, type: Int): Lookup {
        TODO("find by (lower-case name, type); expired means Miss")
    }
}
