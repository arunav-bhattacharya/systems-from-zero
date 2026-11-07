package sfz.kafka.l05

/**
 * One batch: records for one partition that leave together in one request.
 * [closed] means it takes no more records: it is full, or a record did not fit.
 */
class Batch(val partition: Int, val createdMs: Long) {
    var records = 0
        private set
    var bytes = 0
        private set
    var closed = false
        private set

    fun add(sizeBytes: Int) {
        records++
        bytes += sizeBytes
    }

    fun close() {
        closed = true
    }

    override fun toString() = "Batch(p$partition, $records records, $bytes bytes, created $createdMs)"
}

/**
 * A model of the producer's record accumulator: `send()` puts each record into the open batch of its partition,
 * and the sender thread takes batches out when they may leave. Only sizes and times matter here, no data.
 * Time is passed in as `nowMs`, so tests control the clock.
 *
 * @param batchSize the producer's `batch.size` in bytes (default 16384)
 * @param lingerMs  the producer's `linger.ms` (default 5 since Kafka 4.0)
 */
class BatchAccumulator(private val batchSize: Int, private val lingerMs: Long) {
    /** For each partition, its waiting batches, oldest first. Only the last one can still be open. */
    private val queues = sortedMapOf<Int, ArrayDeque<Batch>>()

    /** How many batches are waiting, open or closed. */
    fun waiting(): Int = queues.values.sumOf { it.size }

    /**
     * Adds a record of [sizeBytes] for [partition] at [nowMs] and returns the batch it went into.
     *
     * - If the partition's last batch is open and the record fits (`bytes + sizeBytes <= batchSize`), add it there.
     * - Otherwise close that batch (if there is one) and start a new batch created at [nowMs].
     *   A record bigger than [batchSize] still gets a batch, of its own.
     * - A batch that has reached [batchSize] bytes is full: close it.
     */
    fun append(partition: Int, sizeBytes: Int, nowMs: Long): Batch {
        TODO("find the partition's open batch, close it if the record doesn't fit, start a new one if needed, add, close when full")
    }

    /**
     * The sender thread's turn at [nowMs]: remove and return every batch that may leave now, partition by partition
     * (lowest partition first), oldest batch first. A batch may leave when it is closed, or when it has waited
     * at least `linger.ms` (`nowMs - createdMs >= lingerMs`). Within a partition, stop at the first batch
     * that may not leave yet, so batches leave in order.
     */
    fun drain(nowMs: Long): List<Batch> {
        TODO("for each partition, take batches from the front while they are closed or have lingered long enough")
    }
}
