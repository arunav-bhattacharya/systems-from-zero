package sfz.cons.l03

/**
 * Lesson cons-03, part 2: a linearizable compare-and-set register built on total order broadcast.
 *
 * Every replica receives the same commands in the same order and applies them with the same
 * deterministic code, so every replica computes the same result for every command. A client sends
 * its command into the log and waits until its own replica applies it: the result is the answer.
 */
sealed interface Command {
    val id: Long
    val client: String
}

/** "If the register holds [expected], set it to [value]." */
data class Cas(override val id: Long, override val client: String, val expected: String?, val value: String) : Command

/** A read that goes through the log like any other command. */
data class Read(override val id: Long, override val client: String) : Command

/**
 * Total order broadcast with a fixed sequencer (given). [broadcast] sends a command to the
 * sequencer, which numbers it 1, 2, 3... and sends it to every replica. Messages overtake each other
 * on the way, so each replica holds back a command until it has delivered every lower number.
 *
 * This is the simplest version that works, and its sequencer is a single point of failure: if it
 * dies, nothing is ever delivered again. Making the sequencer fault tolerant is consensus, one
 * Paxos instance per log slot (Multi-Paxos), or Raft.
 */
class TotalOrderBroadcast(
    private val net: Network,
    replicas: Int,
    private val deliver: (replica: Int, Command) -> Unit,
) {
    private var next = 1L
    private val delivered = LongArray(replicas)
    private val waiting = List(replicas) { sortedMapOf<Long, Command>() }

    fun broadcast(cmd: Command) = net.send {
        val seq = next++                                    // the sequencer decides the order
        for (r in waiting.indices) net.send { arrive(r, seq, cmd) }
    }

    private fun arrive(r: Int, seq: Long, cmd: Command) {
        waiting[r][seq] = cmd
        while (waiting[r].isNotEmpty() && waiting[r].firstKey() == delivered[r] + 1) {
            val c = waiting[r].remove(waiting[r].firstKey())!!
            delivered[r]++
            deliver(r, c)
        }
    }
}

/** One replica's copy of the register, and the state machine that changes it. */
class Replica(val name: String) {
    var value: String? = null
        private set
    val applied = mutableListOf<Command>()

    /**
     * Exercise 4. Apply [cmd] and return the value the register held just BEFORE it (this is what
     * Java's `compareAndExchange` returns). A [Cas] sets [value] only if that previous value equals
     * its `expected`; a [Read] changes nothing. Record every command in [applied].
     */
    fun apply(cmd: Command): String? {
        val before = value
        if (cmd is Cas && before == cmd.expected) value = cmd.value   // same input, same order: same result everywhere
        applied += cmd
        return before
    }
}

/**
 * Three replicas behind a total order broadcast. Each client is attached to one replica (its home):
 * c1 to r1, c2 to r2 and so on, round robin.
 */
class LogRegister(private val net: Network) {
    val replicas = listOf(Replica("r1"), Replica("r2"), Replica("r3"))
    private val pending = mutableMapOf<Long, (String?) -> Unit>()
    private var nextId = 1L
    private val tob = TotalOrderBroadcast(net, replicas.size) { r, cmd -> onDeliver(r, cmd) }

    fun home(client: String): Int = (client.removePrefix("c").toInt() - 1) % replicas.size

    /** Every replica applies every command; the client's home replica also sends the result back (given). */
    private fun onDeliver(r: Int, cmd: Command) {
        val before = replicas[r].apply(cmd)
        if (r == home(cmd.client)) pending.remove(cmd.id)?.let { done -> net.send { done(before) } }
    }

    /**
     * Exercise 5. Put [cmd] in the log and arrange for [done] to be called with the result once the
     * client's home replica applies it ([onDeliver] does the calling: it looks in [pending]).
     */
    fun submit(cmd: Command, done: (String?) -> Unit) {
        pending[cmd.id] = done        // answered when the home replica applies it, not before
        tob.broadcast(cmd)
    }

    /** Compare-and-set through the log, answering with the value before it (given). */
    fun compareAndExchange(client: String, expected: String?, value: String, done: (String?) -> Unit) =
        submit(Cas(nextId++, client, expected, value), done)

    /** Compare-and-set through the log, answering whether it swapped (given). */
    fun cas(client: String, expected: String?, value: String, done: (Boolean) -> Unit) =
        compareAndExchange(client, expected, value) { before -> done(before == expected) }

    /** A read through the log (given): linearizable, and as slow as a write. */
    fun read(client: String, done: (String?) -> Unit) = submit(Read(nextId++, client), done)

    /** A read of the home replica's current copy, skipping the log (given): fast, and not linearizable. */
    fun localRead(client: String, done: (String?) -> Unit) = net.send {
        val v = replicas[home(client)].value
        net.send { done(v) }
    }
}

/**
 * Exercise 6: consensus from compare-and-set. Every proposer tries `null -> value` on a fresh
 * register with [LogRegister.compareAndExchange]. Exactly one succeeds. Call [done] with the decided
 * value: yours if the register was empty before your CAS, otherwise what was there (the winner's).
 */
fun propose(register: LogRegister, client: String, value: String, done: (String) -> Unit) =
    register.compareAndExchange(client, null, value) { before -> done(before ?: value) }   // first CAS in the log wins
