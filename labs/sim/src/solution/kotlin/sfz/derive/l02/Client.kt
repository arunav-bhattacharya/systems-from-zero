package sfz.derive.l02

/**
 * The client's copy of one account's balance: a tiny materialized view on the user's screen,
 * kept current by the diffs the server pushes. It starts from a snapshot taken at
 * [startOffset] and remembers the offset of the last diff it applied, like a log consumer.
 */
class ClientCopy(val account: String, startBalance: Long, startOffset: Long) {
    var balance: Long = startBalance
        private set

    var lastOffset: Long = startOffset
        private set

    /** Diffs that changed the balance. */
    var applied: Int = 0
        private set

    /** Diffs dropped because they were already applied (or older than the snapshot). */
    var ignored: Int = 0
        private set

    /** Applies a diff newer than [lastOffset] once; ignores repeats and diffs the snapshot already had. */
    fun receive(d: Diff) {
        if (d.offset <= lastOffset) {                            // already in the balance
            ignored++
            return
        }
        balance += d.delta
        lastOffset = d.offset
        applied++
    }
}

/**
 * A client that subscribes to its account and sometimes goes offline (given). On [reconnect] it
 * first asks the feed for everything after its last offset, then takes live diffs again.
 */
class Subscription(private val feed: Feed, val client: ClientCopy, latencyMs: Long = 20) {
    private val connection = feed.connect(client, latencyMs)

    fun drop() {
        connection.up = false
    }

    fun reconnect() {
        connection.up = true
        for (d in feed.since(client.account, client.lastOffset)) client.receive(d)
    }
}
