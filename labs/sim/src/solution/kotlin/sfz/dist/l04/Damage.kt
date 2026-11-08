package sfz.dist.l04

/** The writes that landed when the lease they were made under was no longer valid at the lease service. */
fun staleWrites(run: RunResult): List<Write> =
    run.writes.filter { !run.leases.getValue(it.leaseId).validAt(it.landedAt) }   // the service's view, at landing

/**
 * The stale writes that did real harm: each landed after the ledger had already applied a write under a newer lease,
 * so it overwrote what the newer holder wrote. Lease ids grow with every grant, so "newer" means a larger id.
 */
fun clobbers(run: RunResult): List<Write> {
    val out = mutableListOf<Write>()
    var newest = 0
    for (w in run.writes) {                      // in the order the ledger applied them
        if (w.leaseId < newest) out += w         // a newer holder has written already
        newest = maxOf(newest, w.leaseId)
    }
    return out
}

/**
 * Stale writes summed over [seeds], for each pause length in [pauseLengths]: one random run per seed, with pauses of
 * that length arriving at random on both holders.
 */
fun sweep(policy: HolderPolicy, pauseLengths: List<Long>, seeds: IntRange, base: Scenario = Scenario()): Map<Long, Int> =
    pauseLengths.associateWith { pause ->
        seeds.sumOf { seed -> staleWrites(simulate(base.copy(seed = seed, pauseMs = pause), policy)).size }
    }
