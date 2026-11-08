package sfz.found.l05

// Models of how throughput grows with workers, a fit to measured numbers, and the COST of a cluster.

/**
 * Amdahl's law: the speed-up on [workers] when a fraction [serial] of the work can only run on one
 * worker: `1 / (serial + (1 - serial) / workers)`. With serial = 0.05 the speed-up never passes 20.
 */
fun amdahl(workers: Int, serial: Double): Double {
    TODO("1 / (serial + (1 - serial) / workers)")
}

/**
 * The Universal Scalability Law: relative capacity `C(N) = N / (1 + alpha (N - 1) + beta N (N - 1))`.
 * [alpha] is contention (the share that waits for something only one worker can use at a time),
 * [beta] is coherency (the cost of every worker keeping in step with every other one).
 * With beta = 0 this is Amdahl's law.
 */
fun usl(workers: Int, alpha: Double, beta: Double): Double {
    TODO("N / (1 + alpha (N - 1) + beta N (N - 1))")
}

/** The number of workers at which the USL curve peaks: `sqrt((1 - alpha) / beta)`; infinite if beta <= 0. */
fun uslPeak(alpha: Double, beta: Double): Double {
    TODO("sqrt((1 - alpha) / beta), or Double.POSITIVE_INFINITY when beta <= 0")
}

/** A fitted model: [single] is the throughput of one worker. */
data class UslFit(val alpha: Double, val beta: Double, val single: Double) {
    fun throughput(workers: Int): Double = single * usl(workers, alpha, beta)
}

/**
 * Fits the USL to measured throughput (jobs per second by number of workers; must contain 1 and at
 * least two other worker counts).
 *
 * The trick: with `C = X(N) / X(1)`, the USL rearranges to a straight line.
 *   z = (N / C - 1) / (N - 1)   and   x = N - 1   give   z = (alpha + beta) + beta * x
 * So for every N > 1 compute (x, z), fit a straight line z = intercept + slope * x by ordinary least
 * squares (slope = sum((x - meanX)(z - meanZ)) / sum((x - meanX)^2), intercept = meanZ - slope * meanX),
 * then beta = slope and alpha = intercept - slope.
 */
fun fitUsl(measured: Map<Int, Double>): UslFit {
    TODO("C = X(N) / X(1); points (N - 1, (N / C - 1) / (N - 1)); straight-line fit; beta = slope, alpha = intercept - slope")
}

/**
 * COST, "the Configuration that Outperforms a Single Thread": the smallest number of workers, from 1 to
 * [maxWorkers], whose time is strictly less than [singleThreadSeconds]. Returns null if no configuration
 * up to [maxWorkers] beats the single thread (the paper calls that an unbounded COST).
 */
fun cost(singleThreadSeconds: Double, clusterSeconds: (workers: Int) -> Double, maxWorkers: Int): Int? {
    TODO("try 1, 2, 3 ... maxWorkers and return the first that is faster than one thread")
}
