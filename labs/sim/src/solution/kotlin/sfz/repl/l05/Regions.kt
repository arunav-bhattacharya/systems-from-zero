package sfz.repl.l05

import java.util.PriorityQueue
import kotlin.math.ln
import kotlin.random.Random

// Everything in this file is given. It calls your three functions in Conflicts.kt.

/** How a region settles two versions of the key. */
enum class Resolution { LAST_WRITE_WINS, DETECT_CONFLICTS }

/**
 * Virtual time. Actions run in time order (ties in the order they were scheduled), and nothing
 * sleeps, so a simulated minute takes a few milliseconds and the same seed always gives the same run.
 */
class VirtualTime {
    var now: Long = 0
        private set
    private var seq = 0L

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private val queue = PriorityQueue<Event>(compareBy<Event>({ it.at }, { it.seq }))

    fun at(time: Long, action: () -> Unit) {
        require(time >= now) { "can't schedule in the past" }
        queue += Event(time, seq++, action)
    }

    fun run() {
        while (queue.isNotEmpty()) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
    }
}

/** One region's leader for the key. Local clients write here; other regions' writes arrive here. */
class Region(val name: String, val skewMs: Long, private val resolution: Resolution) {
    /** The versions this region keeps: always one under last write wins, one or more siblings when detecting. */
    var versions: List<Write> = emptyList()
        private set

    /** Times [applyDetecting] reported a conflict here. */
    var conflicts = 0
        private set

    private val known = HashSet<String>() // every write id this region has heard of
    private var accepted = 0

    /** This region's clock, which is [skewMs] off the true time. */
    fun clock(now: Long): Long = now + skewMs

    /** What a client reads: the holds in every version. Holds are only ever added, so the union is the right merge. */
    fun read(): Set<String> = versions.flatMapTo(sortedSetOf()) { it.holds }

    /** A local client adds one hold, named after the write: read, add, write back. Acknowledged at once. */
    fun acceptLocal(now: Long): Write {
        val id = "$name:${++accepted}"
        val w = Write(id, name, read() + id, clock(now), known.toSet())
        apply(w)
        return w
    }

    /** Apply a write, local or replicated. */
    fun apply(w: Write) {
        known += w.id
        known += w.seen
        versions = when (resolution) {
            Resolution.LAST_WRITE_WINS -> listOf(versions.singleOrNull()?.let { lastWriteWins(it, w) } ?: w)
            Resolution.DETECT_CONFLICTS -> applyDetecting(versions, w).also { if (it.conflict) conflicts++ }.versions
        }
    }
}

/** What happened in one run. */
data class Report(
    /** Writes the regions acknowledged to clients: each added one hold. */
    val acknowledged: Int,
    /** Acknowledged holds missing from the final value, by write id. */
    val lost: List<String>,
    /** Conflicts the detector found, counted at every region that found one. Always 0 under last write wins. */
    val conflicts: Int,
    /** Every region ends with the same value. */
    val converged: Boolean,
    /** Messages that arrived after a later message from the same region. */
    val reordered: Int,
    /** The most write ids any one write carried in its [Write.seen]. */
    val largestHistory: Int,
    /** The value every region reads at the end (the first region's, if they disagree). */
    val finalHolds: Set<String>,
)

/**
 * Runs several regions, each a leader, replicating every write to every other region (all-to-all)
 * with a random one-way delay per message, so messages can overtake each other.
 *
 * Writes happen at random times, [meanGapMs] apart on average in each region, unless [script] gives
 * the exact (region, time) of every write. [skewMs] sets how far each region's clock is off.
 */
fun simulate(
    resolution: Resolution,
    regions: List<String> = listOf("eu", "us"),
    writesPerRegion: Int = 200,
    meanGapMs: Double = 100.0,
    delayMs: LongRange = 20L..80L,
    skewMs: Map<String, Long> = emptyMap(),
    seed: Long = 1,
    script: List<Pair<String, Long>>? = null,
): Report {
    val random = Random(seed)
    val time = VirtualTime()
    val byName = regions.associateWith { Region(it, skewMs[it] ?: 0, resolution) }
    val written = mutableListOf<Write>()
    val newestArrived = HashMap<Pair<String, String>, Int>() // (from, to) -> highest write number delivered
    var reordered = 0

    fun number(w: Write) = w.id.substringAfter(':').toInt()

    val plan = script ?: regions.flatMap { r ->
        var t = 0.0
        List(writesPerRegion) {
            t += -ln(1 - random.nextDouble()) * meanGapMs // exponential gaps: a Poisson stream of writes
            r to t.toLong()
        }
    }
    for ((r, at) in plan) {
        time.at(at) {
            val w = byName.getValue(r).acceptLocal(time.now)
            written += w
            for (other in regions) if (other != r) {
                time.at(time.now + random.nextLong(delayMs.first, delayMs.last + 1)) {
                    val link = r to other
                    if (number(w) < (newestArrived[link] ?: 0)) reordered++
                    newestArrived[link] = maxOf(newestArrived[link] ?: 0, number(w))
                    byName.getValue(other).apply(w)
                }
            }
        }
    }
    time.run()

    val finals = regions.map { byName.getValue(it).read() }
    val final = finals.first()
    return Report(
        acknowledged = written.size,
        lost = written.map { it.id }.filter { it !in final },
        conflicts = byName.values.sumOf { it.conflicts },
        converged = finals.distinct().size == 1,
        reordered = reordered,
        largestHistory = written.maxOfOrNull { it.seen.size } ?: 0,
        finalHolds = final,
    )
}
