package sfz.found.l03.demo

import kotlin.math.ln
import kotlin.math.pow
import kotlin.random.Random

/**
 * Disk failures in a fleet, and what one, two or three copies of the data buy. Change AFR and
 * REPAIR_HOURS and run it again.
 */
private const val AFR = 0.0136          // Backblaze's fleet-wide annual failure rate for 2025
private const val REPAIR_HOURS = 24.0   // time to re-create a lost copy on a new disk
private const val HOURS_PER_YEAR = 8_760.0

private fun ratePerHour(afr: Double) = -ln(1 - afr) / HOURS_PER_YEAR
private fun lossPerYear(copies: Int, afr: Double, repair: Double) =
    copies * ratePerHour(afr).pow(copies) * repair.pow(copies - 1) * HOURS_PER_YEAR

/** Monte Carlo: [copies] disks fail at random; a failed one comes back after [repair] hours. Count total losses. */
private fun simulate(copies: Int, lambda: Double, repair: Double, hours: Double, seed: Long): Int {
    val rnd = Random(seed)
    val backAt = DoubleArray(copies)                         // 0 = alive, else the time its repair finishes
    var now = 0.0
    var losses = 0
    while (now < hours) {
        val alive = (0 until copies).filter { backAt[it] <= now }
        // time to the next failure among the alive disks, or to the next repair
        val nextFail = now - ln(1 - rnd.nextDouble()) / (lambda * alive.size.coerceAtLeast(1))
        val nextRepair = backAt.filter { it > now }.minOrNull() ?: Double.MAX_VALUE
        if (alive.isEmpty() || nextRepair < nextFail) { now = nextRepair; continue }
        now = nextFail
        backAt[alive[rnd.nextInt(alive.size)]] = now + repair
        if (backAt.all { it > now }) {                       // every copy is dead at once: data lost
            losses++
            backAt.fill(0.0)                                 // restore from a backup and go on
        }
    }
    return losses
}

fun main() {
    println("AFR %.2f%%, repair %.0f h".format(AFR * 100, REPAIR_HOURS))
    for (disks in listOf(12, 1_000, 10_000)) {
        val chance = 1 - (1 - AFR).pow(disks)
        println("%,7d disks: %6.1f failures a year expected, chance of at least one: %.1f%%".format(disks, disks * AFR, chance * 100))
    }
    println()
    println("one piece of data on N disks, chance per year of losing every copy:")
    for (copies in 1..3) println("  %d cop%s: %.2e".format(copies, if (copies == 1) "y " else "ies", lossPerYear(copies, AFR, REPAIR_HOURS)))
    val pairs = 5_000
    val fleet = 1 - (1 - lossPerYear(2, AFR, REPAIR_HOURS)).pow(pairs)
    println("10,000 disks as %,d mirrored pairs: chance some pair loses its data this year: %.2f%%".format(pairs, fleet * 100))
    println("same pairs, repair takes a week instead of a day: %.2f%%".format((1 - (1 - lossPerYear(2, AFR, 168.0)).pow(pairs)) * 100))
    println()
    // check the formula with a simulation, at rates high enough to see losses
    val lambda = 1e-3
    val hours = 2e7
    val formula = 2 * lambda * lambda * 10.0 * hours
    println("check: 2 copies, 1 failure per 1,000 h, 10 h repair, %.0e hours: formula %.0f losses, simulation %d".format(
        hours, formula, simulate(2, lambda, 10.0, hours, seed = 1)))
}
