package sfz.stream.l07

import kotlin.random.Random

/*
 * Given: a tiny dataflow job on virtual time, for lesson stream-07. Two sources feed a keyed counter, which feeds a
 * sink that writes to the outside world:
 *
 *     source 0 --channel 0--\
 *                            counter --channel 2--> sink --> external (what the world sees)
 *     source 1 --channel 1--/
 *
 * Channels are FIFO queues. Nothing here sleeps or starts a thread: every virtual millisecond the job picks one step
 * that can run (a source emits its next record, the counter takes the head of an input channel, the sink takes the
 * head of its channel) with a seeded Random, so the same seed always gives the same run.
 */

/** What flows on a channel. */
sealed interface Item

/** One input record, read from [source] at [offset]. [key] is the card it belongs to. */
data class Record(val source: Int, val offset: Int, val key: String) : Item

/** The counter's output: [key]'s new count, caused by the record at ([source], [offset]). */
data class Update(val key: String, val count: Int, val source: Int, val offset: Int) : Item

/** Checkpoint barrier [id]. Every item before it on a channel belongs to checkpoint [id]; every item after, to later ones. */
data class Barrier(val id: Int) : Item

/** A completed checkpoint: each source's offset when barrier [id] was injected, and the counter's state at [id]. */
data class Snapshot(val id: Int, val offsets: List<Int>, val counts: Map<String, Int>)

/** The last operator: takes the counter's output and writes to the outside world. */
interface Sink {
    /** Handles one item. Returns the barrier's id when [item] is a [Barrier] (the sink's acknowledgement), else null. */
    fun onItem(item: Item): Int?

    /** The coordinator says checkpoint [id] is complete: every operator has stored its part of it. */
    fun onCheckpointComplete(id: Int)
}

/** An at-least-once sink: writes each update to [external] the moment it arrives, and acknowledges barriers at once. */
class AppendSink(private val external: MutableList<Update>) : Sink {
    override fun onItem(item: Item): Int? = when (item) {
        is Update -> { external += item; null }
        is Barrier -> item.id
        is Record -> error("the sink receives updates, not records")
    }

    override fun onCheckpointComplete(id: Int) {}
}

/**
 * The job. [inputs] are the two sources' logs (keys, in offset order). They are durable and replayable, like Kafka
 * partitions. [aligned] is passed to the counter. [sink] makes a new sink that writes into the given external list.
 * A checkpoint starts every [checkpointEvery] virtual ms when none is in flight, and once more at the end so that the
 * last updates are committed.
 *
 * A crash (at virtual time `crashAt` in [run]) loses everything in memory: channel contents, the counter, the sink and
 * the checkpoint in flight. It keeps what is durable: the inputs, [completed] checkpoints and [external]. The job then
 * restarts from the last completed checkpoint: sources rewind to its offsets and the counter starts from its counts.
 */
class Job(
    private val inputs: List<List<String>>,
    private val aligned: Boolean,
    private val sink: (MutableList<Update>) -> Sink,
    private val checkpointEvery: Long = 20,
    seed: Long = 1,
) {
    private val random = Random(seed)

    /** Virtual time, in ms. One step runs per ms. */
    var now = 0L
        private set

    /** Everything the sink wrote to the outside world, in order. Survives a crash. */
    val external = mutableListOf<Update>()

    /** Completed checkpoints, oldest first. Survive a crash. */
    val completed = mutableListOf<Snapshot>()

    /** The checkpoint the job restarted from after the crash (0: it started over from the beginning), or null. */
    var restoredFrom: Int? = null
        private set

    /** Virtual ms an input channel had items waiting but the counter would not take them (alignment). */
    var blockedMs = 0L
        private set

    private class Pending(val id: Int, val offsets: List<Int>) {
        var counts: Map<String, Int>? = null
    }

    private var nextId = 1
    private var offsets = IntArray(inputs.size)
    private var channels = List(inputs.size + 1) { ArrayDeque<Item>() }
    private var pending: Pending? = null
    private lateinit var counter: CountingTask
    private lateinit var out: Sink

    /** Runs the job to the end, crashing once at virtual time [crashAt] if it is given. Returns this job. */
    fun run(crashAt: Long? = null): Job {
        start(null)
        while (true) {
            now++
            if (now == crashAt) {
                val from = completed.lastOrNull()
                restoredFrom = from?.id ?: 0
                start(from)                                    // the crash: memory is gone, restart from durable state
            }
            val inputsDone = inputs.indices.all { offsets[it] == inputs[it].size }
            if (pending == null && (now % checkpointEvery == 0L && !inputsDone || inputsDone && channels.all { it.isEmpty() })) {
                if (inputsDone && completed.lastOrNull()?.offsets == inputs.map { it.size }) break   // all committed: done
                trigger()
            }
            val steps = mutableListOf<() -> Unit>()
            for (s in inputs.indices) if (offsets[s] < inputs[s].size) steps += { emit(s) }
            for (i in inputs.indices) if (channels[i].isNotEmpty()) {
                if (counter.canTake(i)) steps += { deliver(i) } else blockedMs++
            }
            if (channels.last().isNotEmpty()) steps += { toSink() }
            if (steps.isNotEmpty()) steps[random.nextInt(steps.size)]()
        }
        return this
    }

    private fun start(from: Snapshot?) {
        offsets = from?.offsets?.toIntArray() ?: IntArray(inputs.size)
        channels = List(inputs.size + 1) { ArrayDeque() }
        pending = null
        counter = CountingTask(aligned, inputs.size, from?.counts ?: emptyMap()) { id, counts ->
            val p = checkNotNull(pending) { "the counter snapshotted barrier $id, but no checkpoint is in flight" }
            check(p.id == id) { "the counter snapshotted barrier $id during checkpoint ${p.id}" }
            p.counts = counts.toMap()                          // a copy: the live map keeps changing
        }
        out = sink(external)
    }

    private fun trigger() {
        val p = Pending(nextId++, offsets.toList())            // the sources' positions: where checkpoint p.id starts
        pending = p
        for (s in inputs.indices) channels[s].addLast(Barrier(p.id))
    }

    private fun emit(s: Int) {
        channels[s].addLast(Record(s, offsets[s], inputs[s][offsets[s]]))
        offsets[s]++
    }

    private fun deliver(i: Int) {
        channels.last().addAll(counter.onItem(i, channels[i].removeFirst()))
    }

    private fun toSink() {
        val ack = out.onItem(channels.last().removeFirst()) ?: return
        val p = checkNotNull(pending) { "the sink acknowledged barrier $ack, but no checkpoint is in flight" }
        check(p.id == ack) { "the sink acknowledged barrier $ack during checkpoint ${p.id}" }
        completed += Snapshot(p.id, p.offsets, checkNotNull(p.counts) { "barrier ${p.id} reached the sink before the counter snapshotted it" })
        pending = null
        out.onCheckpointComplete(p.id)
    }

    /** The true count per key: what an exactly-once run must end with. */
    fun truth(): Map<String, Int> = inputs.flatten().groupingBy { it }.eachCount()

    /** The count per key as the outside world sees it: the last update written for each key. */
    fun finalCounts(): Map<String, Int> = external.groupBy { it.key }.mapValues { it.value.last().count }

    /** Updates written more than once for the same input record. */
    fun duplicates(): Int = external.size - external.map { it.source to it.offset }.toSet().size
}
