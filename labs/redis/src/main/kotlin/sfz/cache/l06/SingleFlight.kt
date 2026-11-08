package sfz.cache.l06

import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap

/**
 * Collapses concurrent loads of the same key, inside one JVM, into one call of the loader.
 *
 * When 100 threads miss the cache for merchant `m-17` at the same moment, the first one to arrive
 * becomes the leader and runs the loader. The other 99 are followers: they wait for the leader's
 * result instead of calling the database themselves. Once the leader finishes, the key leaves the
 * map, so the next miss starts a new load. This is not a cache; Redis is the cache.
 */
class SingleFlight<V> {
    /** One future per key that is loading right now. Use this map. */
    private val flights = ConcurrentHashMap<String, CompletableFuture<V>>()

    /**
     * Returns `loader()` for [key], calling the loader at most once at a time per key.
     *
     * 1. Make a new `CompletableFuture<V>` and try to claim the key with `flights.putIfAbsent(key, mine)`.
     * 2. Got back another caller's future? You are a follower: `join()` it and return its value. `join()` wraps
     *    the leader's exception in a `CompletionException`; throw `e.cause` instead.
     * 3. Got back null? You are the leader: run the loader, `complete` your future with the value (or
     *    `completeExceptionally` with the exception, then rethrow it), and in a `finally` remove the key with
     *    `flights.remove(key, mine)`.
     */
    fun load(key: String, loader: () -> V): V {
        TODO("lesson 6 lab: claim the key with putIfAbsent, lead or follow")
    }

    /** How many keys are being loaded right now. Done for you. */
    fun inFlight(): Int = flights.size
}
