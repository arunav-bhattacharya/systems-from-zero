package sfz.found.l03

import kotlin.math.ln
import kotlin.math.pow

/**
 * How often disks fail, and what extra copies buy. Every function assumes disks fail
 * independently of each other, which real fleets only approximate (see the lesson).
 *
 * AFR is the annualized failure rate: the fraction of disks that fail in a year (0.0136 is 1.36%).
 */
object DiskOdds {
    const val HOURS_PER_YEAR = 8_760.0

    /** One disk's failure rate per hour, from its AFR (finished): -ln(1 - afr) / 8,760. */
    fun ratePerHour(afr: Double): Double = -ln(1 - afr) / HOURS_PER_YEAR

    /** How many of [disks] disks you should expect to fail in a year: disks x afr. */
    fun expectedFailuresPerYear(disks: Int, afr: Double): Double = disks * afr

    /** The chance that at least one of [disks] disks fails within a year: 1 - (1 - afr)^disks. */
    fun chanceOfAnyFailure(disks: Int, afr: Double): Double = 1 - (1 - afr).pow(disks)

    /**
     * The chance per year that one piece of data kept on [copies] disks loses every copy, when a
     * failed copy takes [repairHours] to re-create on a new disk.
     *
     * With lambda = [ratePerHour] and R = [repairHours], the data is lost at about
     * copies x lambda^copies x R^(copies - 1) times per hour: the first copy dies (copies x lambda),
     * and the others all die before the repairs finish (each about lambda x R). Multiply by the
     * hours in a year. With one copy this is just lambda x 8,760, about the AFR.
     */
    fun lossChancePerYear(copies: Int, afr: Double, repairHours: Double): Double {
        val lambda = ratePerHour(afr)
        return copies * lambda.pow(copies) * repairHours.pow(copies - 1) * HOURS_PER_YEAR
    }

    /**
     * The chance per year that at least one of [groups] independent groups of [copies] disks loses
     * its data (5,000 mirrored pairs is groups = 5,000, copies = 2): 1 - (1 - p)^groups, where p is
     * [lossChancePerYear].
     */
    fun fleetLossChancePerYear(groups: Int, copies: Int, afr: Double, repairHours: Double): Double =
        1 - (1 - lossChancePerYear(copies, afr, repairHours)).pow(groups)
}
