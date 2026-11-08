package sfz.cache.l06

import java.util.concurrent.CompletableFuture
import java.util.concurrent.CompletionException
import java.util.concurrent.ConcurrentHashMap

class SingleFlight<V> {
    private val flights = ConcurrentHashMap<String, CompletableFuture<V>>()

    fun load(key: String, loader: () -> V): V {
        val mine = CompletableFuture<V>()
        // putIfAbsent is atomic: exactly one caller per key sees null and becomes the leader
        val running = flights.putIfAbsent(key, mine) ?: return lead(key, mine, loader)
        return try {
            running.join()                                   // a follower: wait for the leader's result
        } catch (e: CompletionException) {
            throw e.cause ?: e                               // the leader's own exception, not a wrapper
        }
    }

    fun inFlight(): Int = flights.size

    private fun lead(key: String, mine: CompletableFuture<V>, loader: () -> V): V {
        try {
            val value = loader()
            mine.complete(value)                             // wakes every follower with the same value
            return value
        } catch (e: Throwable) {
            mine.completeExceptionally(e)                    // followers get the failure too
            throw e
        } finally {
            flights.remove(key, mine)                        // the next miss starts a new load: this is not a cache
        }
    }
}
