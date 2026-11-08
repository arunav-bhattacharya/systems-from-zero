package sfz.repl.l05.demo

/**
 * A toy model of the two DynamoDB global table modes as their documentation describes them. It is
 * not DynamoDB: no SDK, no network, just the rules, so you can see what each rule does to one retry.
 *
 * A checkout service stores idempotency keys in a global table with replicas in eu and us, and
 * charges the card only when `put(key) if attribute_not_exists(key)` succeeds. A request lands in
 * eu at t=0; the client times out and retries the same key in us at t=200 ms. Replication between
 * the regions takes 700 ms in this run: "typically within a second or less".
 */
private const val REPLICATION_MS = 700L

/** MREC: each Region checks the condition against its own copy; replication is asynchronous. */
private fun mrec() {
    println("-- MREC (eventual): the condition is checked against the local Region's copy --")
    val copies = mutableMapOf("eu" to mutableMapOf<String, String>(), "us" to mutableMapOf())
    var charges = 0
    fun put(region: String, t: Long, key: String, value: String) {
        val local = copies.getValue(region)
        if (key in local) {
            println("t=%-4d %s ConditionalCheckFailed: replay the stored result".format(t, region))
        } else {
            local[key] = value
            charges++
            println("t=%-4d %s condition passes, card charged (charge #%d)".format(t, region, charges))
        }
    }
    put("eu", 0, "idem-7f3a", "eu-result")
    put("us", 200, "idem-7f3a", "us-result")
    // both writes replicate; last writer wins per item, so both copies end with the later one
    println("t=%-4d both copies converge on one item: %s".format(200 + REPLICATION_MS, "us-result"))
    println("charges: $charges for one checkout")
}

/** MRSC: a write replicates to another Region before it returns; a write racing it fails and is retried. */
private fun mrsc() {
    println("-- MRSC (strong): writes replicate synchronously; a racing write fails --")
    val item = mutableMapOf<String, String>()
    var inFlightUntil = -1L
    var charges = 0
    fun put(region: String, t: Long, key: String, value: String, writeMs: Long): Long {
        if (t < inFlightUntil) {
            println("t=%-4d %s ReplicatedWriteConflictException: item is being modified in another Region".format(t, region))
            return -1
        }
        if (key in item) {
            println("t=%-4d %s ConditionalCheckFailed: replay the stored result".format(t, region))
            return t
        }
        inFlightUntil = t + writeMs
        item[key] = value
        charges++
        println("t=%-4d %s condition passes, card charged (charge #%d), write returns at t=%d".format(t, region, charges, inFlightUntil))
        return inFlightUntil
    }
    // the eu write is slow to return (cross-Region round trips), and the client gives up at t=200
    put("eu", 0, "idem-7f3a", "eu-result", writeMs = 250)
    if (put("us", 200, "idem-7f3a", "us-result", writeMs = 90) < 0) {
        put("us", 300, "idem-7f3a", "us-result", writeMs = 90) // retry after a short backoff
    }
    println("charges: $charges for one checkout")
}

fun main() {
    mrec()
    println()
    mrsc()
}
