package sfz.enc.l04

import java.util.concurrent.CompletableFuture
import java.util.concurrent.CompletionException
import java.util.concurrent.ConcurrentHashMap

class KeyReusedException(message: String) : RuntimeException(message)

class IdempotencyStore {
    private class Entry(val fingerprint: String, val result: CompletableFuture<Any?>)

    private val entries = ConcurrentHashMap<String, Entry>()

    val size: Int
        get() = entries.size

    fun <T> once(key: String, fingerprint: String, work: () -> T): T {
        val mine = Entry(fingerprint, CompletableFuture())
        // the claim: exactly one caller gets null back, however many arrive at the same moment
        val first = entries.putIfAbsent(key, mine)
        if (first != null) {
            if (first.fingerprint != fingerprint) throw KeyReusedException("key $key was first used for a different request")
            try {
                @Suppress("UNCHECKED_CAST")
                return first.result.join() as T // a replay; waits if the first attempt is still running
            } catch (e: CompletionException) {
                throw e.cause ?: e
            }
        }
        try {
            val value = work()
            mine.result.complete(value)
            return value
        } catch (e: Throwable) {
            entries.remove(key, mine) // nothing happened, so a retry may try again
            mine.result.completeExceptionally(e)
            throw e
        }
    }
}
