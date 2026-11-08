package sfz.derive.l01.demo

/**
 * Try it, derive-01 section 1: one store goes down for three minutes.
 *
 * Ten minutes of payments, 50 a second. Four derived stores (search index, cache, warehouse
 * loader, fraud features) are fed two ways:
 *   async: the payment commits to PostgreSQL and its log; each store's consumer reads the log at
 *          up to 2,000 records a second when it is up.
 *   sync:  every payment must be written to PostgreSQL and all four stores before it counts, in
 *          one all-or-nothing step (a distributed transaction).
 * The search index is down from minute 3 to minute 6.
 */
fun main() {
    val seconds = 600
    val rate = 50
    val stores = listOf("search", "cache", "warehouse", "fraud")
    val down = 180 until 360                                // the search index is down
    val drainPerSecond = 2_000

    // async: the log is the system of record; consumers follow at their own pace
    var logEnd = 0L
    val position = stores.associateWith { 0L }.toMutableMap()
    val maxLag = stores.associateWith { 0L }.toMutableMap()
    var caughtUpAt = -1
    for (s in 0 until seconds) {
        logEnd += rate
        for (store in stores) {
            val up = !(store == "search" && s in down)
            if (up) position[store] = minOf(logEnd, position.getValue(store) + drainPerSecond)
            val lag = logEnd - position.getValue(store)
            maxLag[store] = maxOf(maxLag.getValue(store), lag)
        }
        if (s >= down.last + 1 && caughtUpAt < 0 && position["search"] == logEnd) caughtUpAt = s
    }
    println("async (log + consumers): ${"%,d".format(logEnd)} payments accepted, 0 failed")
    for (store in stores) {
        println("  %-10s max lag %,6d records".format(store, maxLag.getValue(store)))
    }
    println("  search caught up ${caughtUpAt - down.last} s after it came back")

    // sync: one write to all five systems, all or nothing
    var accepted = 0
    var failed = 0
    for (s in 0 until seconds) {
        if (s in down) failed += rate else accepted += rate
    }
    println("sync (all-or-nothing):   ${"%,d".format(accepted)} payments accepted, ${"%,d".format(failed)} failed")
    println("  every store but search was healthy for the whole ten minutes")
}
