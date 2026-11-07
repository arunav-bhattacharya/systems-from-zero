package sfz.redis.l08

import java.util.concurrent.ConcurrentHashMap

class PayoutLedger {
    data class PayoutFile(val fence: Long, val content: String)

    private val files = ConcurrentHashMap<String, PayoutFile>()

    fun write(batch: String, fence: Long, content: String): Boolean {
        var written = false
        // compute() holds this batch's entry while the lambda runs: check and write are one step
        files.compute(batch) { _, old ->
            if (old != null && fence < old.fence) {
                old                                            // a holder older than one we've seen: refuse
            } else {
                written = true
                PayoutFile(fence, content)                     // equal is fine: the same holder writing again
            }
        }
        return written
    }

    fun read(batch: String): PayoutFile? = files[batch]
}
