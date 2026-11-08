package sfz.dist.l06.demo

/**
 * Lesson dist-06, section 5: a hold and a payout that no message connects. The risk team holds merchant M-0042 on
 * the merchants shard; a webhook tells the merchant, whose own server asks the payouts shard for a payout 30 ms later.
 * The rule: a hold blocks every payout created after it. The payouts shard's clock is 80 ms behind.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l06.demo.ExternalOrderDemoKt -q
 */
fun main() {
    var real = 1_000L
    val merchants = HybridClock(0) { real }                     // this shard's wall clock is right
    val payouts = HybridClock(1) { real - 80 }                  // this one is 80 ms behind

    val hold = merchants.local()
    println("%,d ms  hold on M-0042 commits on the merchants shard with HLC %s".format(real, hold))
    real += 30                                                  // webhook, merchant's server, new request: no HLC rides along
    val payout = payouts.local()
    println("%,d ms  payout P-9 commits on the payouts shard with HLC %s".format(real, payout))
    println("        rule check: is P-9 after the hold? ${payout > hold}  ->  ${if (payout > hold) "blocked" else "PAID, although the hold came first"}")

    // Lamport clocks: the merchants shard has seen 500 events, the payouts shard 300
    val lm = LamportClock(0).apply { repeat(500) { local() } }
    val lp = LamportClock(1).apply { repeat(300) { local() } }
    val lHold = lm.local()
    val lPayout = lp.local()
    println("        with Lamport stamps: hold $lHold, payout $lPayout, payout after hold: ${lPayout > lHold}")

    // One timestamp oracle for both shards: every commit asks it for the next number
    val oracle = TimestampOracle(batch = 1_000)
    val oHold = oracle.next()
    val oPayout = oracle.next()
    println("        with a timestamp oracle: hold $oHold, payout $oPayout, payout after hold: ${oPayout > oHold}  ->  blocked")
    oracle.failOver()
    println("        the oracle fails over; the next timestamp is ${oracle.next()}: numbers skipped, none reused")
}

/**
 * A timestamp oracle in miniature: one counter that every commit asks. It saves a high-water mark [batch] numbers
 * ahead, so after a failover the new leader starts above anything the old one could have handed out.
 */
private class TimestampOracle(val batch: Long) {
    private var next = 1L
    private var saved = 0L                                      // what the replicated store says
    fun next(): Long {
        if (next > saved) saved += batch                        // one replicated write per 1,000 numbers
        return next++
    }
    fun failOver() { next = saved + 1 }                         // the new leader only knows the saved mark
}
