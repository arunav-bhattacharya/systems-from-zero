package sfz.found.l05.demo

import kotlin.random.Random

// A copy of the lab's Settlement.kt (demos can't see src/main), plus a main that measures it.
//
// The system under test: the nightly settlement batch, which adds up one day of payments per merchant.
// It runs either on one thread with a hash map, or on a simulated cluster of N workers. Time is
// virtual: the code really does the work (the totals are real), and every step adds its cost, in
// nanoseconds, to a clock. So every run gives the same numbers on every laptop.

/** One day of payments: `merchant[i]` was paid `amountCents[i]`. A few big merchants get most payments. */
class Payments(val merchant: IntArray, val amountCents: LongArray) {
    val size: Int get() = merchant.size
}

fun paymentsOfTheDay(count: Int = 1_000_000, merchants: Int = 5_000, seed: Long = 1): Payments {
    val random = Random(seed)
    val m = IntArray(count) { (merchants * random.nextDouble().let { it * it * it }).toInt() }  // skewed to low ids
    val a = LongArray(count) { 100L + random.nextLong(50_000) }
    return Payments(m, a)
}

/** What each step costs in virtual time. The defaults are made up but keep real proportions. */
data class Costs(
    /** One thread, a plain loop over an array and a hash map. */
    val singlePaymentNs: Double = 100.0,
    /** Serial: the coordinator schedules the job and starts the workers. Nothing else can run meanwhile. */
    val startupMs: Double = 20.0,
    /** On a worker: decode one row through the framework and add it to a partial sum. */
    val clusterPaymentNs: Double = 1_000.0,
    /** The shuffle: every worker opens a connection to every other worker and waits for its answer. */
    val perPeerMs: Double = 0.5,
    /** Sending one partial sum (merchant, amount) to the worker that owns that merchant, and merging it. */
    val perEntryNs: Double = 500.0,
    /** Serial: the coordinator collects the results and commits them. */
    val commitMs: Double = 5.0,
)

/** How long a run took, in virtual seconds, and the total per merchant it computed. */
class BatchRun(val seconds: Double, val totals: Map<Int, Long>)

fun runOnOneThread(p: Payments, costs: Costs = Costs()): BatchRun {
    val totals = HashMap<Int, Long>()
    for (i in 0 until p.size) totals.merge(p.merchant[i], p.amountCents[i], Long::plus)
    return BatchRun(p.size * costs.singlePaymentNs / 1e9, totals)
}

/**
 * Runs the batch on [workers] simulated machines that share nothing: each reads its own slice of the
 * input, sums it per merchant, then sends each partial sum to the worker that owns the merchant
 * (`merchant % workers`). Phases end with a barrier, so each phase lasts as long as its slowest worker.
 */
fun runOnCluster(p: Payments, workers: Int, costs: Costs = Costs()): BatchRun {
    require(workers >= 1)
    var ns = costs.startupMs * 1e6                                   // serial

    // map: each worker sums its slice of the input
    val partial = Array(workers) { HashMap<Int, Long>() }
    var slowestMap = 0.0
    for (w in 0 until workers) {
        val from = (p.size.toLong() * w / workers).toInt()
        val to = (p.size.toLong() * (w + 1) / workers).toInt()
        for (i in from until to) partial[w].merge(p.merchant[i], p.amountCents[i], Long::plus)
        slowestMap = maxOf(slowestMap, (to - from) * costs.clusterPaymentNs)
    }
    ns += slowestMap

    // shuffle: partial sums travel to their owners; every pair of workers pays a connection
    val received = LongArray(workers)
    val sent = LongArray(workers)
    val totals = HashMap<Int, Long>()
    for (w in 0 until workers) for ((merchant, sum) in partial[w]) {
        val owner = merchant % workers
        if (owner != w) { sent[w]++; received[owner]++ }
        totals.merge(merchant, sum, Long::plus)
    }
    var slowestShuffle = 0.0
    for (w in 0 until workers) {
        val t = (workers - 1) * costs.perPeerMs * 1e6 + (sent[w] + received[w]) * costs.perEntryNs
        slowestShuffle = maxOf(slowestShuffle, t)
    }
    ns += slowestShuffle

    ns += costs.commitMs * 1e6                                       // serial
    return BatchRun(ns / 1e9, totals)
}

// Run from the labs folder:
//   ./gradlew :sim:demo -Pmain=sfz.found.l05.demo.ScalingDemoKt --console=plain -q
//   ./gradlew :sim:demo -Pmain=sfz.found.l05.demo.ScalingDemoKt --console=plain -q -Pargs='0.5 20'
// The arguments are the shuffle's cost per pair of workers (ms) and the job's startup time (ms).

fun main(args: Array<String>) {
    val costs = Costs(
        perPeerMs = args.getOrNull(0)?.toDouble() ?: Costs().perPeerMs,
        startupMs = args.getOrNull(1)?.toDouble() ?: Costs().startupMs,
    )
    val payments = paymentsOfTheDay()
    val one = runOnOneThread(payments, costs)
    println("settlement of %,d payments, %,d merchants".format(payments.size, one.totals.size))
    println("one thread, plain loop: %.1f ms".format(one.seconds * 1000))
    println()
    println("workers   time (ms)   payments/s   speed-up")
    val measured = linkedMapOf<Int, Double>()
    val counts = listOf(1, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128)
    for (n in counts) {
        val run = runOnCluster(payments, n, costs)
        check(run.totals == one.totals) { "the cluster got a different answer" }
        measured[n] = payments.size / run.seconds
        println("%7d %11.1f %,12.0f %10.1f".format(n, run.seconds * 1000, measured[n], measured[n]!! / measured[1]!!))
    }
    val fit = fitUsl(measured)
    println()
    println("USL fit: alpha %.4f  beta %.6f  peak at %.0f workers".format(fit.alpha, fit.beta, uslPeak(fit.alpha, fit.beta)))
    val best = measured.maxBy { it.value }
    println("measured best: %d workers, %.1f ms".format(best.key, payments.size / best.value * 1000))
    // COST: walk up from 1 worker. Time falls, bottoms out, then rises, so once it rises the search can stop.
    var previous = Double.MAX_VALUE
    for (n in 1..4096) {
        val t = runOnCluster(payments, n, costs).seconds
        if (t < one.seconds) { println("COST: $n workers to beat one thread (%.1f ms)".format(t * 1000)); return }
        if (t > previous) { println("COST: unbounded, no number of workers beats one thread"); return }
        previous = t
    }
}

fun usl(n: Int, alpha: Double, beta: Double) = n / (1.0 + alpha * (n - 1) + beta * n * (n - 1.0))
fun uslPeak(alpha: Double, beta: Double) = if (beta <= 0) Double.POSITIVE_INFINITY else kotlin.math.sqrt((1 - alpha) / beta)
class Fit(val alpha: Double, val beta: Double)
fun fitUsl(m: Map<Int, Double>): Fit {
    val x1 = m.getValue(1)
    val pts = m.filterKeys { it > 1 }.map { (n, x) -> (n - 1.0) to (n / (x / x1) - 1.0) / (n - 1.0) }
    val mx = pts.map { it.first }.average()
    val mz = pts.map { it.second }.average()
    val slope = pts.sumOf { (x, z) -> (x - mx) * (z - mz) } / pts.sumOf { (x, _) -> (x - mx) * (x - mx) }
    return Fit(alpha = mz - slope * mx - slope, beta = slope)
}
