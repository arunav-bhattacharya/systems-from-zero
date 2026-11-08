package sfz.dist.l01

/**
 * Lesson dist-01 (given): an asynchronous packet network. It promises nothing about whether a packet
 * arrives, how many copies arrive, or when. Read it, but you don't need to change it.
 *
 * Faults apply per packet and per direction, so a test can lose only the replies (a one-way fault,
 * like a network card that sends but no longer receives).
 */
data class Faults(
    /** Chance that a packet vanishes: a full queue dropped it, a link went down, a cable was pulled. */
    val loss: Double = 0.0,
    /** Chance that a second copy is delivered too: a proxy or a client library that resent it for you. */
    val duplicate: Double = 0.0,
    /** Each copy takes a delay drawn uniformly from [minDelayMs] to [maxDelayMs]. */
    val minDelayMs: Long = 1,
    val maxDelayMs: Long = 1,
    /** Chance that a copy waits behind other traffic in a switch, kernel or hypervisor queue... */
    val queueing: Double = 0.0,
    /** ...for an extra delay drawn uniformly from 0 to [queueMs]. */
    val queueMs: Long = 0,
) {
    init {
        require(loss in 0.0..1.0 && duplicate in 0.0..1.0 && queueing in 0.0..1.0) { "chances are 0.0 to 1.0" }
        require(minDelayMs in 0..maxDelayMs && queueMs >= 0) { "delays must be 0 <= min <= max" }
    }
}

/** One message on the wire. */
data class Packet(val from: String, val to: String, val body: Any)

/** What the network did, counted over a whole run. */
data class NetworkStats(
    var sent: Int = 0,
    var lost: Int = 0,
    var duplicated: Int = 0,
    var queued: Int = 0,
    var delivered: Int = 0,
)

class Network(private val sim: Sim, private val defaults: Faults = Faults()) {
    val stats = NetworkStats()
    private val nodes = mutableMapOf<String, (Packet) -> Unit>()
    private val links = mutableMapOf<Pair<String, String>, Faults>()

    /** Registers a node: [onPacket] runs for every packet delivered to [name]. */
    fun join(name: String, onPacket: (Packet) -> Unit) {
        nodes[name] = onPacket
    }

    /** Sets the faults for packets from [from] to [to] (one direction only). */
    fun faults(from: String, to: String, faults: Faults) {
        links[from to to] = faults
    }

    private fun faultsFor(from: String, to: String) = links[from to to] ?: defaults

    /**
     * Sends [body] from [from] to [to]. The sender learns nothing: no error if the packet is lost, no
     * signal when it arrives. The random draws happen here, in a fixed order, so a seed replays a run.
     */
    fun send(from: String, to: String, body: Any) {
        val f = faultsFor(from, to)
        stats.sent++
        if (sim.random.nextDouble() < f.loss) {
            stats.lost++
            return
        }
        deliver(Packet(from, to, body), f)
        if (sim.random.nextDouble() < f.duplicate) {
            stats.duplicated++
            deliver(Packet(from, to, body), f)          // the copy takes its own path and delay
        }
    }

    private fun deliver(packet: Packet, f: Faults) {
        var delay = f.minDelayMs + sim.random.nextLong(f.maxDelayMs - f.minDelayMs + 1)
        if (sim.random.nextDouble() < f.queueing) {
            stats.queued++
            delay += sim.random.nextLong(f.queueMs + 1)  // stuck behind other traffic
        }
        sim.after(delay) {
            stats.delivered++
            nodes[packet.to]?.invoke(packet)             // a node that never joined just doesn't answer
        }
    }
}
