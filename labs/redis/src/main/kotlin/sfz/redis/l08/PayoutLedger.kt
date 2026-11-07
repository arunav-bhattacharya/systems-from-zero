package sfz.redis.l08

import java.util.concurrent.ConcurrentHashMap

/**
 * The protected resource: the store that keeps each settlement batch's payout file. It stands in for your database
 * or file service, NOT for Redis, and it does the half of fencing that the lock service can't: it remembers the
 * highest fencing token that has written each batch and refuses writes that carry a smaller one.
 *
 * In Oracle the same rule is one statement:
 * `UPDATE payout_files SET content = :content, fence = :fence WHERE batch = :batch AND fence <= :fence`,
 * and zero rows updated means "refused".
 */
class PayoutLedger {
    /** What is stored for one batch: the content and the fence of the holder that wrote it. */
    data class PayoutFile(val fence: Long, val content: String)

    /** Use this map. */
    private val files = ConcurrentHashMap<String, PayoutFile>()

    /**
     * Writes [content] for [batch] if [fence] is at least as large as the fence of the last accepted write (the
     * same holder may write several times). Returns true if it wrote, false if it refused and changed nothing.
     *
     * The check and the write must be one step, or two writers can both pass the check: use
     * `files.compute(batch) { _, old -> ... }`, which runs your function while it holds that entry, and remember
     * inside it whether you wrote.
     */
    fun write(batch: String, fence: Long, content: String): Boolean {
        TODO("lesson 8 lab: refuse a fence older than the last accepted one, in one compute()")
    }

    /** The current file for [batch], or null. Done for you. */
    fun read(batch: String): PayoutFile? = files[batch]
}
