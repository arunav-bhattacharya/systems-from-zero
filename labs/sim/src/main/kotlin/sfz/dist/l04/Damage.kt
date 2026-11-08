package sfz.dist.l04

/**
 * The writes that landed when the lease they were made under was no longer valid at the lease service.
 *
 * Look each write's lease up in `run.leases` (by `leaseId`) and ask the lease whether it was valid when the write
 * LANDED (`Lease.validAt`). The holder's own opinion at the time doesn't count: it can be wrong, which is the lesson.
 */
fun staleWrites(run: RunResult): List<Write> =
    TODO("dist-04 lab: writes whose lease wasn't valid when they landed")

/**
 * The stale writes that did real harm: each landed after the ledger had already applied a write under a newer lease,
 * so it overwrote what the newer holder wrote. Lease ids grow with every grant, so "newer" means a larger id. Walk
 * `run.writes` in order (the order the ledger applied them) and remember the largest lease id seen so far.
 */
fun clobbers(run: RunResult): List<Write> =
    TODO("dist-04 lab: stale writes that landed after a newer lease's write")

/**
 * Stale writes summed over [seeds], for each pause length in [pauseLengths]: one run per seed, built with
 * `base.copy(seed = seed, pauseMs = pause)` and [simulate], with [policy] for both holders.
 */
fun sweep(policy: HolderPolicy, pauseLengths: List<Long>, seeds: IntRange, base: Scenario = Scenario()): Map<Long, Int> =
    TODO("dist-04 lab: total stale writes per pause length")
