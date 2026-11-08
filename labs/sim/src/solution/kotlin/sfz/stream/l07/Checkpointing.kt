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
    fun canTake(input: Int): Boolean = !aligned || !seen[input]

    /** Handles one item from input [input] and returns what to send downstream, in order. */
    fun onItem(input: Int, item: Item): List<Item> = when (item) {
        is Record -> {
            val n = (counts[item.key] ?: 0) + 1
            counts[item.key] = n
            listOf(Update(item.key, n, item.source, item.offset))
        }
        is Barrier -> {
            seen[input] = true
            if (seen.all { it }) {                 // the last input's barrier: the state now is the checkpoint's state
                onSnapshot(item.id, counts)
                seen.fill(false)                   // unblock every input
                listOf(item)                       // forward one barrier, before any later update
            } else {
                emptyList()                        // aligned: this input is now blocked until the others catch up
            }
        }
        is Update -> error("the counter receives records, not updates")
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

    override fun onItem(item: Item): Int? = when (item) {
        is Update -> { open += item; null }                  // nothing is visible yet
        is Barrier -> {
            prepared[item.id] = open.toList()               // pre-commit: this transaction belongs to checkpoint id
            open.clear()
            item.id                                          // acknowledge the barrier
        }
        is Record -> error("the sink receives updates, not records")
    }

    override fun onCheckpointComplete(id: Int) {
        val ready = prepared.headMap(id + 1)                 // checkpoint id and anything older
        for (updates in ready.values) external += updates   // commit: now the world sees them
        ready.clear()
    }
}
