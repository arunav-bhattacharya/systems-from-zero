package sfz.cache.l07

import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit.SECONDS

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

    @JvmStatic
    fun run(table: MerchantTable, id: String, newName: String, pods: Pods): Outcome {
        val atFill = CountDownLatch(1)               // reader A has read the old row and is about to fill
        val writerDone = CountDownLatch(1)           // the writer has committed and deleted

        // reader A's pod: it stops between its table read and its fill until the writer is done
        val cacheA = pods.cache {
            atFill.countDown()
            writerDone.await(5, SECONDS)
        }
        // the writer's and reader B's pod: no pause anywhere
        val cacheB = pods.cache {}

        val readerA = CompletableFuture.supplyAsync { cacheA.get(id) }
        check(atFill.await(5, SECONDS)) { "reader A never reached its fill: did it miss?" }

        table.write(id, newName)                     // the writer commits version 2...
        cacheB.afterWrite(id)                        // ...and invalidates, while A still holds version 1
        writerDone.countDown()                       // now let A's fill go: it lands after the delete

        val a = readerA.get(5, SECONDS)
        val b = cacheB.get(id)                       // a later request: what every reader sees from now on
        return Outcome(table.read(id)!!.name, a, b)
    }
}
