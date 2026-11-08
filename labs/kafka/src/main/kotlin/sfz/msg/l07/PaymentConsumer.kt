package sfz.msg.l07

import org.apache.kafka.clients.consumer.Consumer
import org.apache.kafka.clients.consumer.ConsumerRecords
import org.apache.kafka.clients.consumer.OffsetAndMetadata
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.errors.WakeupException
import java.time.Duration

/**
 * An at-least-once payment consumer: poll, apply every payment, and only then commit.
 * It works with any [Consumer]: a real `KafkaConsumer`, or a `MockConsumer` in tests.
 */
object PaymentConsumer {
    /**
     * The offsets to commit once every record in [records] has been processed: for each partition in the batch,
     * the offset of its last record plus one. A committed offset is the next record to read, not the last one read.
     */
    fun offsetsToCommit(records: ConsumerRecords<String, String>): Map<TopicPartition, OffsetAndMetadata> {
        TODO("for each partition in records: OffsetAndMetadata(offset of its last record + 1)")
    }

    /**
     * One turn of the poll loop.
     *
     * 1. `poll` with [timeout].
     * 2. Parse every record's value with [Payment.parse] and hand it to [sink], in the order poll returned them.
     * 3. Only after all of them, `commitSync` the offsets from [offsetsToCommit]. Commit nothing for an empty poll.
     *
     * If [sink] throws, let the exception out: the commit must not happen, so a restarted consumer reads the
     * whole batch again. Returns the number of records processed.
     */
    fun pollOnce(consumer: Consumer<String, String>, sink: PaymentSink, timeout: Duration): Int {
        TODO("poll, apply every payment to the sink, then commitSync(offsetsToCommit(records))")
    }

    /**
     * Runs [pollOnce] (with a 100 ms timeout) until another thread calls `consumer.wakeup()`, which makes the blocked
     * or next `poll` throw [WakeupException]. Catch it and return the total number of records processed.
     * Don't close the consumer: whoever created it closes it.
     */
    fun run(consumer: Consumer<String, String>, sink: PaymentSink): Int {
        TODO("loop over pollOnce until WakeupException, then return the total")
    }
}
