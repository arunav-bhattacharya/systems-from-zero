package sfz.dist.l01.demo

/**
 * Lesson dist-01, section 4: delay with no upper bound, and what any fixed timeout does with it.
 *
 * Nothing is lost. Each packet takes 1 to 5 ms, but 2% of packets (in each direction) wait behind
 * other traffic for up to 3 seconds. First the round trips the client sees with no timeout at all,
 * then 1,000 payments with timeouts from 100 ms to 5 s.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l01.demo.DelayDemoKt
 * Optional: -Pargs='0.05 10000' sets the queueing chance and the longest wait in ms.
 */
fun main(args: Array<String>) {
    val chance = args.getOrNull(0)?.toDouble() ?: 0.02
    val longest = args.getOrNull(1)?.toLong() ?: 3_000
    val faults = Faults(minDelayMs = 1, maxDelayMs = 5, queueing = chance, queueMs = longest)

    val open = payments(faults = faults, count = 10_000, timeoutMs = 60_000)
    val rtts = open.client.outcomes.entries.map { (key, o) -> o.atMs - (key.removePrefix("pay-").toLong() - 1) * 10 }.sorted()
    fun p(q: Double) = rtts[((rtts.size - 1) * q).toInt()]
    println("10,000 payments, nothing lost, ${(chance * 100).toInt()}% of packets queued for up to $longest ms")
    println("round trip including 50 ms of work: p50 ${p(0.5)} ms, p90 ${p(0.9)} ms, p99 ${p(0.99)} ms, p99.9 ${p(0.999)} ms, max ${rtts.last()} ms")
    println()
    println("%-10s %9s %9s %18s %13s".format("timeout", "approved", "unknown", "unknown, charged", "late replies"))
    for (timeout in listOf(100L, 200L, 500L, 1_000L, 2_000L, 5_000L)) {
        val run = payments(faults = faults, timeoutMs = timeout)
        val a = run.audit
        println("%-10s %9d %9d %18d %13d".format("$timeout ms", a.approved, a.unknown, a.unknownButCharged, run.client.lateReplies))
    }
}
