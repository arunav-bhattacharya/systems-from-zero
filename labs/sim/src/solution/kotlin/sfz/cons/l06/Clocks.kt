package sfz.cons.l06

/**
 * One server's clock (given): the true time of the simulation plus an offset the server doesn't know.
 * The offset stays fixed for the whole run, so the clock never jumps; it is just wrong by [offsetMs].
 */
class NodeClock(private val sim: Sim, val offsetMs: Long) {
    fun now(): Long = sim.now + offsetMs
}

/**
 * A TrueTime-style clock (given): the server doesn't know its offset, but it does know a bound,
 * [epsilonMs], on how wrong it can be. So instead of one number it reports an interval that surely
 * contains the true time: [earliest] to [latest]. Every server in a cluster has the same bound, so two
 * servers' clocks can differ by up to 2 x epsilon.
 */
class TrueTime(private val clock: NodeClock, val epsilonMs: Long) {
    init {
        require(kotlin.math.abs(clock.offsetMs) <= epsilonMs) { "offset ${clock.offsetMs} is outside the bound $epsilonMs" }
    }

    fun earliest(): Long = clock.now() - epsilonMs
    fun latest(): Long = clock.now() + epsilonMs
}

/** A server: a name, its clock and its TrueTime view of that clock. */
class Server(val name: String, val clock: NodeClock, val tt: TrueTime)
