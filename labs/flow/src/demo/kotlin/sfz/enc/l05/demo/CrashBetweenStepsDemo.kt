package sfz.enc.l05.demo

import kotlin.random.Random

/**
 * 10,000 orders run charge -> reserve -> ship, and the process sometimes dies. Each step has two places to die:
 * before its side effect, and after the side effect but before the program has written down that it happened.
 * Four ways to recover, and what each leaves behind. Plain Kotlin, no Temporal.
 */

private const val ORDERS = 10_000
private const val CRASH_CHANCE = 0.005 // at each of the 6 points
private val STEPS = listOf("charge", "reserve", "ship")

private class Outcome {
    var charges = 0; var reservations = 0; var parcels = 0
    var chargedNotShipped = 0; var doubleCharged = 0
}

private enum class Recovery { NONE, RESTART_FROM_TOP, STATUS_COLUMN, STATUS_COLUMN_AND_KEYS }

private fun run(recovery: Recovery, seed: Int): Outcome {
    val rnd = Random(seed)
    val out = Outcome()
    repeat(ORDERS) { n ->
        var status = 0 // the status column: how many steps are recorded as done
        val keysSeen = HashSet<String>() // the bank's idempotency keys, for the last strategy
        var chargesForOrder = 0
        var finished = false
        var attempts = 0
        while (!finished && attempts < 10) {
            attempts++
            var crashed = false
            val from = if (recovery == Recovery.STATUS_COLUMN || recovery == Recovery.STATUS_COLUMN_AND_KEYS) status else 0
            for (i in from until STEPS.size) {
                if (rnd.nextDouble() < CRASH_CHANCE) { crashed = true; break } // died before the side effect
                when (STEPS[i]) { // the side effect
                    "charge" -> {
                        val key = "order-$n/charge"
                        if (recovery != Recovery.STATUS_COLUMN_AND_KEYS || keysSeen.add(key)) { out.charges++; chargesForOrder++ }
                    }
                    "reserve" -> out.reservations++
                    "ship" -> out.parcels++
                }
                if (rnd.nextDouble() < CRASH_CHANCE) { crashed = true; break } // died after it, before recording it
                status = i + 1 // UPDATE orders SET status = ... (one local transaction)
            }
            if (!crashed) finished = true
            if (recovery == Recovery.NONE) break // nobody comes back for it
        }
        if (chargesForOrder > 0 && !finished) out.chargedNotShipped++
        if (chargesForOrder > 1) out.doubleCharged++
    }
    return out
}

fun main() {
    println("$ORDERS orders; at each of 6 points the process dies with probability $CRASH_CHANCE")
    println("%-26s %8s %18s %14s".format("recovery", "charges", "charged, unshipped", "double charges"))
    for (r in Recovery.entries) {
        val o = run(r, seed = 7)
        println("%-26s %8d %18d %14d".format(r.name.lowercase().replace('_', ' '), o.charges, o.chargedNotShipped, o.doubleCharged))
    }
}
