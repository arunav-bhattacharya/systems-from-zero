package sfz.repl.l05.demo

/**
 * Merchant M-0042's open authorization holds, written from Frankfurt (eu) and Virginia (us).
 * One-way delay between the regions: 35 ms. A local write: 1 ms.
 *
 * First with one leader in us, then with a leader in each region, where two writes made 10 ms
 * apart never see each other and last write wins keeps one of them. Each Version's ts is its
 * region's clock reading: change us's from 10 to -5 (a clock 15 ms behind) and see who wins.
 */
private const val ONE_WAY = 35L

private data class Version(val holds: Set<String>, val ts: Long, val by: String)

private fun lww(a: Version, b: Version) = if (compareValuesBy(a, b, Version::ts, Version::by) >= 0) a else b

private fun line(t: Long, who: String, what: String) = println("t=%-4d %-3s %s".format(t, who, what))

fun main() {
    println("-- one leader, in us --")
    line(0, "eu", "client sends: add hold h-eu")
    line(ONE_WAY, "us", "leader commits [h-eu]")
    line(2 * ONE_WAY, "eu", "client gets OK after ${2 * ONE_WAY} ms; a 4-statement transaction would wait ${8 * ONE_WAY} ms")

    println()
    println("-- a leader in each region --")
    var eu = Version(setOf("h-eu"), 0, "eu")
    line(0, "eu", "leader commits ${eu.holds} at ts ${eu.ts}, client gets OK after 1 ms")
    var us = Version(setOf("h-us"), 10, "us")
    line(10, "us", "leader commits ${us.holds} at ts ${us.ts}, client gets OK after 1 ms")
    val fromEu = eu
    val fromUs = us
    line(ONE_WAY, "us", "receives ${fromEu.holds} from eu; its own ${us.holds} never saw it: a conflict")
    us = lww(us, fromEu)
    line(10 + ONE_WAY, "eu", "receives ${fromUs.holds} from us; its own ${eu.holds} never saw it: a conflict")
    eu = lww(eu, fromUs)
    println()
    println("last write wins keeps ts ${eu.ts} from ${eu.by}:  eu = ${eu.holds}   us = ${us.holds}")
    println("acknowledged: h-eu, h-us   kept: ${eu.holds}   lost: ${setOf("h-eu", "h-us") - eu.holds}")
}
