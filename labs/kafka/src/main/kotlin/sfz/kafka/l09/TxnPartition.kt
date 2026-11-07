package sfz.kafka.l09

/** One entry in a partition: a data record, or the control marker that ends a transaction. */
data class Entry(val offset: Long, val producerId: Long, val value: String?, val kind: Kind) {
    enum class Kind { DATA, COMMIT, ABORT }
}

/** The consumer's `isolation.level`. */
enum class Isolation { READ_UNCOMMITTED, READ_COMMITTED }

/**
 * One partition the way a broker stores transactional writes. A transactional record is appended at once, like
 * any other, while its transaction is still open. When the transaction ends, the broker appends a marker, a
 * control record that takes an offset of its own, saying COMMIT or ABORT. Nothing is ever removed or rewritten:
 * readers decide what to show.
 */
class TxnPartition {
    private val log = mutableListOf<Entry>()

    // producer id -> offset of the first record of its open transaction
    private val open = mutableMapOf<Long, Long>()

    // producer id -> the offset ranges of its aborted transactions, as [first, marker)
    private val aborted = mutableListOf<Pair<Long, LongRange>>()

    /**
     * Appends a data record for [producerId] and returns its offset. With [transactional] true, the record belongs
     * to the producer's open transaction, which starts here if it has none. A non-transactional record is final at once.
     */
    fun append(producerId: Long, value: String, transactional: Boolean = true): Long {
        TODO("append at the log end; a transactional record opens its producer's transaction if none is open")
    }

    /** Ends [producerId]'s open transaction with a COMMIT marker and returns the marker's offset. */
    fun commit(producerId: Long): Long = end(producerId, Entry.Kind.COMMIT)

    /** Ends [producerId]'s open transaction with an ABORT marker and returns the marker's offset. */
    fun abort(producerId: Long): Long = end(producerId, Entry.Kind.ABORT)

    private fun end(producerId: Long, kind: Entry.Kind): Long {
        TODO("remove the open transaction, append the marker, remember an aborted range")
    }

    /** The offset the next entry will get. */
    fun logEndOffset(): Long = log.size.toLong()

    /**
     * The last stable offset: the first offset of the oldest transaction that is still open, or [logEndOffset]
     * if none is. Everything below it is decided. A `read_committed` reader never reads at or past it.
     */
    fun lastStableOffset(): Long {
        TODO("the first offset of the oldest open transaction, or the log end")
    }

    /**
     * The data records a consumer positioned at [from] receives, in offset order. Never markers.
     *
     * - READ_UNCOMMITTED: every data record up to the log end, even from open or aborted transactions.
     * - READ_COMMITTED: only below [lastStableOffset], and never a record of an aborted transaction.
     */
    fun read(from: Long, isolation: Isolation): List<Entry> {
        TODO("data records from `from`; read_committed stops at the LSO and skips aborted transactions")
    }
}
