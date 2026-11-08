package sfz.stream.l07

/**
 * The keyed counter with two inputs. It counts records per key and sends an [Update] downstream for each record.
 *
 * Checkpoints: barrier n arrives on each input. When it has arrived on every input, the counter calls [onSnapshot]
 * with its counts and forwards one `Barrier(n)` downstream, ahead of anything it emits later.
 *
 * With [aligned] = true, an input that has delivered barrier n is blocked ([canTake] returns false) until barrier n has
 * arrived on every input, so no record from after the barrier is counted before the snapshot. With [aligned] = false,
 * the counter keeps taking records from every input (the at-least-once mode).
 */
class CountingTask(
    private val aligned: Boolean,
    inputs: Int,
    restored: Map<String, Int>,
    private val onSnapshot: (barrierId: Int, counts: Map<String, Int>) -> Unit,
) {
    /** The operator's state: the count per key. A restart begins from a checkpoint's counts. */
    val counts: MutableMap<String, Int> = restored.toMutableMap()

    /** Which inputs have delivered the barrier the counter is waiting on. */
    private val seen = BooleanArray(inputs)

    /** May the job deliver the head of input [input] now? Aligned: not while that input waits for the others. */
    fun canTake(input: Int): Boolean {
        TODO("aligned: false while seen[input]; not aligned: always true")
    }

    /**
     * Handles one item from input [input] and returns what to send downstream, in order.
     *
     * - A [Record]: add 1 to its key's count and return one [Update] with the new count and the record's source and offset.
     * - A [Barrier]: mark the input as seen. If every input has now delivered it, call [onSnapshot] with the counts,
     *   clear `seen`, and return the barrier. Otherwise return nothing.
     */
    fun onItem(input: Int, item: Item): List<Item> {
        TODO("count records; on a barrier, snapshot and forward it once every input has delivered it")
    }
}

/**
 * A transactional (two-phase commit) sink. Updates go into an open transaction. On barrier n it pre-commits: the open
 * updates become checkpoint n's prepared transaction, and it acknowledges n. When the coordinator says checkpoint n
 * is complete, it commits: the prepared updates of n (and any earlier ones still waiting) are appended to [external]
 * in order. A crash loses the open and prepared transactions, which is safe: the restart replays their records.
 */
class TransactionalSink(private val external: MutableList<Update>) : Sink {
    private val open = mutableListOf<Update>()
    private val prepared = sortedMapOf<Int, List<Update>>()

    /** An [Update] joins the open transaction. A [Barrier] pre-commits the open transaction under its id and
     * returns the id (the acknowledgement). */
    override fun onItem(item: Item): Int? {
        TODO("Update: add to open, return null. Barrier: move open to prepared[id], return id")
    }

    /** Commit: append the prepared updates of [id] and of every older checkpoint to [external], oldest first. */
    override fun onCheckpointComplete(id: Int) {
        TODO("append prepared transactions up to and including id to external, then forget them")
    }
}
