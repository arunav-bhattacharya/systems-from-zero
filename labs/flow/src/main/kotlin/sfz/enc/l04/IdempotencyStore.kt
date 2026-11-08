package sfz.enc.l04

import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap

/** A key arrived again with a different request: a client bug, never something to replay. */
class KeyReusedException(message: String) : RuntimeException(message)

/**
 * The server's memory of idempotency keys, in one JVM. (The Caching track's lesson on idempotency keys
 * built the same idea in Redis, shared by many pods.)
 *
 * [once] runs `work` at most once per key and gives every later call with that key the first result:
 *
 * - The first call for a key claims it, runs `work`, stores the result and returns it.
 * - A later call with the same key and the same `fingerprint` (a summary of the request, such as
 *   `"pay-1|4000"`) returns the stored result without running `work`. If the first call is still running,
 *   it waits for it. That is the usual case for a retry after a timeout.
 * - A later call with the same key and a different fingerprint throws [KeyReusedException].
 * - If `work` throws, nothing is stored: forget the key, so that a retry can run it again.
 *
 * Two calls with the same key can arrive at the same instant on two threads. Claim the key in one atomic
 * step (`ConcurrentHashMap.putIfAbsent`), never with a separate "is it there?" check.
 * A real store also expires keys (Stripe may forget them after 24 hours); this one keeps them.
 */
class IdempotencyStore {
    // one entry per key: what the request looked like, and its result (complete once work() returns)
    private class Entry(val fingerprint: String, val result: CompletableFuture<Any?>)

    private val entries = ConcurrentHashMap<String, Entry>()

    /** How many keys the store remembers. */
    val size: Int
        get() = entries.size

    fun <T> once(key: String, fingerprint: String, work: () -> T): T {
        TODO("claim the key with putIfAbsent; on a hit, check the fingerprint and wait for the result")
    }
}
