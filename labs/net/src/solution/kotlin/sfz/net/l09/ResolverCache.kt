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

    private class Entry(val expiresAt: Long, val rcode: Int, val records: List<ResourceRecord>)

    private val entries = HashMap<Pair<String, Int>, Entry>()

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
        val q = response.questions.firstOrNull() ?: return
        val now = clock()
        val keepSeconds = when {
            response.rcode == Rcode.NOERROR && response.answers.isNotEmpty() ->
                response.answers.minOf { it.ttl }                       // the weakest link
            response.rcode == Rcode.NOERROR || response.rcode == Rcode.NXDOMAIN -> {
                val soa = response.authority.firstOrNull { it.type == RecordType.SOA } ?: return
                minOf(soa.ttl, (soa.data as RData.Soa).minimum)         // RFC 2308
            }
            else -> return                                              // SERVFAIL and friends: ask again next time
        }
        entries[key(q.name, q.type)] = Entry(now + keepSeconds * 1000, response.rcode, response.answers)
    }

    /**
     * Looks up [name] and [type]. An entry is good while `clock()` is before its expiry: return
     * [Lookup.Hit] with each record's TTL replaced by the seconds left (rounded down), or
     * [Lookup.Negative] with the seconds left. Once it has expired, forget it and return [Lookup.Miss].
     */
    fun get(name: String, type: Int): Lookup {
        val k = key(name, type)
        val e = entries[k] ?: return Lookup.Miss
        val now = clock()
        if (now >= e.expiresAt) {
            entries.remove(k)                                           // expired: the next query goes out
            return Lookup.Miss
        }
        val left = (e.expiresAt - now) / 1000                           // what the next client is told
        return if (e.records.isEmpty()) Lookup.Negative(e.rcode, left) else Lookup.Hit(e.records.map { it.copy(ttl = left) })
    }

    private fun key(name: String, type: Int) = name.lowercase().removeSuffix(".") to type
}
