package sfz.net.l02

/**
 * One host's ARP cache: the table that maps an IP on the local subnet to a MAC address.
 * Linux calls it the neighbour table (`ip neigh`); macOS shows it with `arp -an`.
 *
 * Entries age. [lookup] only trusts an entry for [ttlMillis] after it was last learned or
 * confirmed. Older entries stay in the table (Linux marks them STALE) but lookup ignores them,
 * so the host has to ask again.
 *
 * Time comes from [clock] (milliseconds), so tests can move it by hand.
 */
class ArpCache(
    val myIp: String,
    val myMac: MacAddress,
    private val ttlMillis: Long = 30_000,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    // ip -> the MAC we heard, and when we last heard it
    private class Entry(var mac: MacAddress, var updatedAt: Long)

    private val table = HashMap<String, Entry>()

    /** The MAC for [ip], or null if there is no entry or the entry is [ttlMillis] old or older. */
    fun lookup(ip: String): MacAddress? {
        val e = table[ip] ?: return null
        // an old entry is not deleted, just no longer trusted
        return if (clock() - e.updatedAt < ttlMillis) e.mac else null
    }

    /**
     * Handles one ARP packet that arrived on the wire, following the reception rules of RFC 826,
     * and returns the reply to send back, or null when there is nothing to send.
     *
     * 1. If the sender's IP is already in the table (fresh or old), overwrite its MAC with the
     *    sender's MAC and reset its time. This is how a gratuitous ARP moves an IP to a new card.
     * 2. If the packet is not for [myIp] (its target IP is someone else), stop here: return null.
     *    Do not add strangers: a busy LAN would fill the table with hosts you never talk to.
     * 3. It is for me. If step 1 did not already update the sender, add it now. The requester
     *    is about to talk to you, so learning it here saves an ARP round trip later.
     * 4. Only now look at the operation. If it is a REQUEST, return a REPLY: you are the sender
     *    (myMac, myIp) and the requester is the target. If it is a REPLY, return null.
     */
    fun receive(packet: ArpPacket): ArpPacket? {
        val now = clock()
        // 1. merge: anyone we already know gets updated, whoever the packet is for
        val known = table[packet.senderIp]
        if (known != null) {
            known.mac = packet.senderMac
            known.updatedAt = now
        }
        // 2. not for me: done, and no new entry for a stranger
        if (packet.targetIp != myIp) return null
        // 3. for me: learn the sender if the merge did not
        if (known == null) table[packet.senderIp] = Entry(packet.senderMac, now)
        // 4. only now look at the operation
        if (packet.op != ArpPacket.REQUEST) return null
        return ArpPacket(
            op = ArpPacket.REPLY,
            senderMac = myMac, senderIp = myIp,                             // the answer: me
            targetMac = packet.senderMac, targetIp = packet.senderIp,       // sent straight back, not broadcast
        )
    }

    /** The who-has to broadcast when [lookup] comes back empty. */
    fun requestFor(ip: String): ArpPacket = ArpPacket.request(myMac, myIp, ip)
}
