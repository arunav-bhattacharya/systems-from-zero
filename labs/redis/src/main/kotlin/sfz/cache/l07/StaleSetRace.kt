package sfz.cache.l07

/**
 * Plays the stale-set race on purpose, in the same order on every run: latches decide the
 * interleaving, not luck.
 *
 * Three actors share one Redis and one [MerchantTable]: reader A (a slow pod), the writer, and
 * reader B (a later request). Reader A gets its own cache, built with a pause before its fill; the
 * writer and reader B share a second cache with no pause.
 */
object StaleSetRace {
    /**
     * What everyone ended up with. [readerB] is what every later reader gets: when it differs from
     * [database], the cache is stale, and stays stale until the entry's TTL ends.
     */
    data class Outcome(val database: String, val readerA: String?, val readerB: String?)

    /** Builds one pod's cache around the `beforeFill` hook it is given. */
    fun interface Pods {
        fun cache(beforeFill: Runnable): MerchantCache
    }

    /**
     * The table already holds [id] at version 1, and Redis holds nothing for it. Play this timeline:
     *
     * 1. Make two latches, `atFill` and `writerDone`, each with a count of 1.
     * 2. Build reader A's cache with `pods.cache { ... }`: its hook counts down `atFill`, then waits
     *    (up to 5 seconds) on `writerDone`. Build the second cache with a hook that does nothing.
     * 3. Start reader A on its own thread (`CompletableFuture.supplyAsync { cacheA.get(id) }` is enough).
     *    It misses, reads version 1 from the table, and stops just before its fill.
     * 4. Wait (up to 5 seconds) on `atFill`, so you know reader A is there.
     * 5. The writer: commit [newName] with `table.write`, call `afterWrite(id)` on the second cache, then
     *    count down `writerDone`. Reader A's fill now lands after the writer's delete.
     * 6. Wait (up to 5 seconds) for reader A's result.
     * 7. Reader B: `get(id)` on the second cache.
     *
     * Return the table's name for [id] after all that (`table.read(id)`), and what reader A and reader B got.
     */
    @JvmStatic
    fun run(table: MerchantTable, id: String, newName: String, pods: Pods): Outcome {
        TODO("lesson 7 lab: two latches, reader A on its own thread, the writer in between")
    }
}
