package sfz.dist.l03

/**
 * Lesson dist-03: a register that settles conflicts by timestamp, the way Cassandra settles one cell,
 * and writers that stamp their writes with their own clocks.
 *
 * Two exercises: [LwwRegister.apply] and [Writer.writeWithCommitWait].
 */

/** One write as the store receives it: the value, the timestamp its writer chose, and who wrote it. */
data class Write(val value: String, val timestampMs: Long, val writer: String)

class LwwRegister {
    var current: Write? = null
        private set

    /**
     * Exercise 2. Last write wins: keep [write] if there is no current write, or its timestamp is
     * higher, or the timestamps are equal and its writer name is larger (a fixed tie-break, so every
     * replica picks the same one). Returns whether [write] became current.
     */
    fun apply(write: Write): Boolean {
        val c = current
        val newer = c == null ||
            write.timestampMs > c.timestampMs ||
            (write.timestampMs == c.timestampMs && write.writer > c.writer)
        if (newer) current = write                       // otherwise the write is dropped, silently
        return newer
    }
}

/**
 * Given. A store with one [LwwRegister], [networkMs] one way from every writer. It acknowledges every
 * write it receives, kept or dropped, as a Cassandra replica does: the timestamp decided, not the
 * order of arrival, and nobody was told.
 */
class Store(private val sim: Sim, val networkMs: Long = 1) {
    val register = LwwRegister()

    /** Writes the store acknowledged but dropped because an existing write had a higher timestamp. */
    var dropped = 0
        private set

    fun write(w: Write, ack: () -> Unit) {
        sim.after(networkMs) {
            if (!register.apply(w)) dropped++
            sim.after(networkMs) { ack() }
        }
    }

    fun read(reply: (Write?) -> Unit) {
        sim.after(networkMs) {
            val c = register.current
            sim.after(networkMs) { reply(c) }
        }
    }
}

/** A service instance with its own clock, writing to the [store]. */
class Writer(val name: String, val clock: DriftingClock, private val sim: Sim, private val store: Store) {

    /** Given. Plain last-write-wins: stamp the write with this node's clock reading and send it. */
    fun write(value: String, done: () -> Unit) {
        store.write(Write(value, clock.millis(), name)) { done() }
    }

    /**
     * Exercise 3. Commit wait, as Spanner does it with TrueTime:
     *  - stamp the write with `clock.bounds().latest`, a time that can't be in the past yet;
     *  - send it;
     *  - once the store has acknowledged, check the clock every 1 ms of virtual time and call [done]
     *    when `clock.bounds().earliest` is greater than the stamp: from then on, that time is surely
     *    in the past on every honest clock, so any later write anywhere gets a larger stamp.
     * [done] receives the ms waited after the acknowledgement.
     */
    fun writeWithCommitWait(value: String, done: (waitedMs: Long) -> Unit) {
        val stamp = clock.bounds().latest                  // no honest clock reads past this yet
        store.write(Write(value, stamp, name)) {
            val ackedAt = sim.now
            fun check() {
                if (clock.bounds().earliest > stamp) done(sim.now - ackedAt)   // the stamp is in everyone's past
                else sim.after(1) { check() }
            }
            check()
        }
    }
}

/** What a [causalChain] saw. */
data class ChainResult(
    /** Writes the store acknowledged. */
    val acknowledged: Int,
    /** Acknowledged writes that a read straight after did not return: the register kept an older value. */
    val lost: List<String>,
    /** For commit-wait runs, how long each write waited after its acknowledgement. */
    val waitsMs: List<Long>,
)

/**
 * Given. [rounds] writes in a causal chain: in round i, `writers[i % writers.size]` reads the register,
 * then writes "v<i>", then reads again to check it. The next round starts after a think time drawn
 * from 0 to [maxThinkMs]. Every write is causally after the one before it, because its writer read it
 * first, so a correct store must end each round showing the newest value.
 */
fun causalChain(sim: Sim, store: Store, writers: List<Writer>, rounds: Int, commitWait: Boolean, maxThinkMs: Long = 0): ChainResult {
    var acknowledged = 0
    val lost = mutableListOf<String>()
    val waits = mutableListOf<Long>()
    fun round(i: Int) {
        if (i == rounds) return
        val w = writers[i % writers.size]
        val value = "v$i"
        fun check() {
            acknowledged++
            store.read { seen ->
                if (seen?.value != value) lost += value       // OK was said, the value isn't there
                sim.after(sim.random.nextLong(maxThinkMs + 1)) { round(i + 1) }
            }
        }
        store.read { _ ->                                      // read first: this write follows the last one
            if (commitWait) w.writeWithCommitWait(value) { waited -> waits += waited; check() }
            else w.write(value) { check() }
        }
    }
    sim.at(sim.now) { round(0) }
    sim.run()
    return ChainResult(acknowledged, lost, waits)
}
