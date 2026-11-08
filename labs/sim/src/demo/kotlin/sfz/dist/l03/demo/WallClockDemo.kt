package sfz.dist.l03.demo

import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset
import kotlin.random.Random

/**
 * Lesson dist-03, section 1: the two clocks on your own machine, and a duration measured with the
 * wrong one.
 *
 * Part 1 reads System.currentTimeMillis() and System.nanoTime() in tight loops and prints the
 * smallest step each one takes (this varies by OS and hardware). Part 2 replays the bug behind
 * Cloudflare's 2017 leap-second outage: a round trip timed with a wall clock that is stepped back
 * one second in the middle, then fed to a random-number call that needs a positive bound.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l03.demo.WallClockDemoKt
 */
fun main() {
    // part 1: smallest steps
    var millisStep = Long.MAX_VALUE
    var last = System.currentTimeMillis()
    var changes = 0
    while (changes < 50) {
        val now = System.currentTimeMillis()
        if (now != last) { millisStep = minOf(millisStep, now - last); last = now; changes++ }
    }
    var nanoStep = Long.MAX_VALUE
    var prev = System.nanoTime()
    repeat(1_000_000) {
        val now = System.nanoTime()
        if (now != prev) nanoStep = minOf(nanoStep, now - prev)
        prev = now
    }
    println("currentTimeMillis: smallest step $millisStep ms (over 50 changes)")
    println("nanoTime:          smallest step $nanoStep ns (over a million reads)")
    println("nanoTime now:      ${System.nanoTime()} (an arbitrary origin: compare it only with this JVM's own readings)")
    println()

    // part 2: a wall clock that NTP (or a leap second) steps back by 1,000 ms during the call
    val wall = SteppedClock(Clock.systemUTC(), stepAfterReads = 1, stepMs = -1_000)
    val start = wall.millis()
    val t0 = System.nanoTime()
    Thread.sleep(12)                                            // the upstream DNS server answers in about 12 ms
    val rttWall = wall.millis() - start                         // the wall clock was stepped back 1 s in between
    val rttMono = (System.nanoTime() - t0) / 1_000_000
    println("round trip from the wall clock: $rttWall ms")
    println("round trip from nanoTime:       $rttMono ms")
    for ((name, rtt) in listOf("wall clock" to rttWall, "nanoTime" to rttMono)) {
        try {
            val jitter = Random(1).nextLong(rtt)                   // pick a server weighted by round trip
            println("Random.nextLong($rtt) with the $name value: $jitter")
        } catch (e: IllegalArgumentException) {
            println("Random.nextLong($rtt) with the $name value: ${e::class.simpleName}: ${e.message}")
        }
    }
}

/** The real wall clock, stepped by [stepMs] after [stepAfterReads] reads, as NTP or a leap second can do. */
private class SteppedClock(private val base: Clock, private val stepAfterReads: Int, private val stepMs: Long) : Clock() {
    private var reads = 0
    override fun millis(): Long = base.millis() + if (reads++ < stepAfterReads) 0 else stepMs
    override fun instant(): Instant = Instant.ofEpochMilli(millis())
    override fun getZone(): ZoneId = ZoneOffset.UTC
    override fun withZone(zone: ZoneId): Clock = this
}
