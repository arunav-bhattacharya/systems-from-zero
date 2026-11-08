package sfz.msg.l09

import org.apache.kafka.clients.consumer.Consumer
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.clients.producer.Producer
import java.time.Duration

/** A failure that may go away on its own: a timeout, a 503 from the card issuer, a lock wait. Worth retrying. */
class TransientFailure(message: String) : RuntimeException(message)

/** Why a record went to the dead-letter topic without being tried: an earlier record with its key failed. */
class ParkedKeyException(blockedBy: String) : RuntimeException("key is parked behind $blockedBy")

/**
 * An at-least-once poll loop that never lets one bad record stop its partition, and never lets a payment overtake
 * an earlier payment of the same account.
 *
 * For each record, in the order `poll` returned them:
 *
 * - If its key is parked (an earlier record with that key went to the dead-letter topic), don't call the handler:
 *   send it to the dead-letter topic too, with a [ParkedKeyException] naming the record it is parked behind.
 * - Otherwise call [handler]. A [TransientFailure] is retried, up to [maxAttempts] calls in all, with
 *   `sleep(backoff(n))` after failed attempt n. Any other exception is permanent: no retry.
 * - A record that still fails goes to [dltTopic] (built with [DeadLetters.deadLetter]), and its key is parked.
 *
 * Every dead letter must be acknowledged by the broker (`send(...).get()`) before the offsets are committed.
 * After the whole batch, `commitSync` the next offset to read of every partition in it. A record counts as handled
 * when it was processed or dead-lettered.
 */
class RetryingConsumer(
    private val consumer: Consumer<String, String>,
    private val dlt: Producer<String, String>,
    private val dltTopic: String,
    private val maxAttempts: Int,
    private val backoff: (attempt: Int) -> Duration,
    private val sleep: (Duration) -> Unit = { Thread.sleep(it.toMillis()) },
    private val handler: (ConsumerRecord<String, String>) -> Unit,
) {
    private val parkedKeys = mutableMapOf<String, String>()

    /** Parked keys, each with the record it is parked behind, written as `topic-partition@offset`. */
    val parked: Map<String, String> get() = parkedKeys

    /** One poll, handled as described above. Returns the number of records handled; 0 for an empty poll. */
    fun pollOnce(timeout: Duration): Int {
        val records = consumer.poll(timeout)
        if (records.isEmpty) return 0
        for (r in records) {
            val blockedBy = r.key()?.let { parkedKeys[it] }
            if (blockedBy != null) {
                deadLetter(r, ParkedKeyException(blockedBy)) // keep the account's order: it waits behind the failure
                continue
            }
            val error = attempt(r) ?: continue               // null: processed
            deadLetter(r, error)
            r.key()?.let { parkedKeys[it] = "${r.topic()}-${r.partition()}@${r.offset()}" }
        }
        // only now, with every dead letter safely written, move the bookmark past the batch
        consumer.commitSync(records.partitions().associateWith { OffsetAndMetadata(records.records(it).last().offset() + 1) })
        return records.count()
    }

    /** Calls the handler until it succeeds or the attempts run out. Returns the last error, or null on success. */
    private fun attempt(r: ConsumerRecord<String, String>): Exception? {
        for (n in 1..maxAttempts) {
            try {
                handler(r)
                return null
            } catch (e: TransientFailure) {
                if (n == maxAttempts) return e
                sleep(backoff(n))                            // wait, then try again: it may go away
            } catch (e: Exception) {
                return e                                     // permanent: the same input fails the same way
            }
        }
        error("unreachable")
    }

    private fun deadLetter(r: ConsumerRecord<String, String>, error: Exception) {
        dlt.send(DeadLetters.deadLetter(r, error, dltTopic)).get() // wait for the broker's ack
    }
}
