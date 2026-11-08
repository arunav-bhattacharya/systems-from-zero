package sfz.dist.l08

/**
 * Lesson dist-08: deterministic simulation testing. Run the simulation for seed after seed, stop at
 * the first that breaks the rule, and keep the seed: it is a complete, exact recipe for the failure.
 */
object Dst {
    /**
     * Exercise 1 of 3: find the first failing seed.
     *
     * Run `Simulation(seed, protocol, faultFor?.invoke(seed)).run()` for each seed in [seeds], in
     * order, and return the first [Run] whose violation isn't null. Return null if every seed
     * passes. When [faultFor] is null, each run draws its own fault from its seed.
     */
    fun search(seeds: LongRange, protocol: Protocol, faultFor: ((Long) -> Fault)? = null): Run? {
        for (seed in seeds) {
            val run = Simulation(seed, protocol, faultFor?.invoke(seed)).run()
            if (run.violation != null) return run          // the seed is the whole bug report
        }
        return null
    }

    /** Runs [run]'s seed again, with the same protocol and fault (given). */
    fun replay(run: Run): Run = Simulation(run.seed, run.protocol, run.fault).run()
}
