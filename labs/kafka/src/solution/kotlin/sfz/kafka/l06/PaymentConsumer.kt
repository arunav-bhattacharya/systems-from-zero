package sfz.kafka.l06

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
    fun offsetsToCommit(records: ConsumerRecords<String, String>): Map<TopicPartition, OffsetAndMetadata> =
        records.partitions().associateWith { tp ->
            OffsetAndMetadata(records.records(tp).last().offset() + 1) // next to read
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
        val records = consumer.poll(timeout)
        if (records.isEmpty) return 0
        for (r in records) {
            sink.apply(Payment.parse(r.value())) // a crash here leaves the batch uncommitted
        }
        consumer.commitSync(offsetsToCommit(records)) // only after every record is applied
        return records.count()
    }

    /**
     * Runs [pollOnce] (with a 100 ms timeout) until another thread calls `consumer.wakeup()`, which makes the blocked
     * or next `poll` throw [WakeupException]. Catch it and return the total number of records processed.
     * Don't close the consumer: whoever created it closes it.
     */
    fun run(consumer: Consumer<String, String>, sink: PaymentSink): Int {
        var total = 0
        try {
            while (true) total += pollOnce(consumer, sink, Duration.ofMillis(100))
        } catch (e: WakeupException) {
            // someone asked us to stop; if commitSync was interrupted, the last batch is read again next time
        }
        return total
    }
}
