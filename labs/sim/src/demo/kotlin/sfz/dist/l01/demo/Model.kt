package sfz.dist.l01.demo

import java.util.PriorityQueue
import kotlin.random.Random

// A copy of the lab's reference model (labs/sim/src/solution/kotlin/sfz/dist/l01), so the demos run
// without your exercises. Read the lab's files for the comments on each part.

/**
 * Virtual time for lesson dist-01 (given). Nothing here sleeps or starts a thread. [run] takes the
 * scheduled events in time order and moves [now] from one to the next, so a simulated hour takes a
 * few milliseconds and the same seed always gives the same run. Times are milliseconds.
 *
 * Every random choice in a simulation comes from [random], which is seeded once. Two events at the
 * same millisecond run in the order they were scheduled.
 */
class Sim(seed: Long = 1) {
    val random = Random(seed)

    var now: Long = 0
        private set

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))

    /** Runs [action] at [time]. */
    fun at(time: Long, action: () -> Unit) {
        require(time >= now) { "time $time is in the past (now $now)" }
        queue += Event(time, seq++, action)
    }

    /** Runs [action] [delayMs] from now. */
    fun after(delayMs: Long, action: () -> Unit) = at(now + delayMs, action)

    /** Runs every event scheduled at or before [time], then sets the clock to [time]. */
    fun runUntil(time: Long) {
        while (queue.isNotEmpty() && queue.peek().at <= time) step()
        if (time > now) now = time
    }

    /** Runs events until none are left. */
    fun run() {
        while (queue.isNotEmpty()) step()
    }

    private fun step() {
        val event = queue.poll()
        now = event.at
        event.action()
    }
}

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

/**
 * Lesson dist-01: a shop authorizes card payments with an issuer over the [Network]. The shop sees
 * only the replies that reach it. The issuer's [PaymentServer.charges] list is the truth, which no
 * client can read; the tests compare the two with [audit].
 *
 * Three exercises:
 *  1. [PaymentServer.onRequest]: charge once per idempotency key, however many copies arrive.
 *  2. [PaymentClient.authorize] and [PaymentClient.onReply]: a timeout per attempt, retries with the
 *     same key, and an honest outcome when every attempt timed out.
 *  3. [audit]: count what the client believes against what the issuer did.
 */

/** "Charge [amount] cents under idempotency key [key]"; [attempt] is 1 for the first send, 2 for the first retry... */
data class AuthRequest(val key: String, val amount: Long, val attempt: Int)

/** The issuer's answer: the authorization code for [key]. */
data class AuthReply(val key: String, val code: String)

/** One real charge on a card, as the issuer recorded it. */
data class Charge(val key: String, val amount: Long, val code: String, val atMs: Long)

/** What the client decided about one payment, and when. */
sealed interface Outcome {
    val attempts: Int
    val atMs: Long

    /** A reply arrived: the card was charged and [code] proves it. */
    data class Approved(val code: String, override val attempts: Int, override val atMs: Long) : Outcome

    /** Every attempt timed out. The card may or may not have been charged: the client can't tell. */
    data class Unknown(override val attempts: Int, override val atMs: Long) : Outcome
}

class PaymentServer(
    private val sim: Sim,
    private val net: Network,
    val name: String = "issuer",
    /** How long one charge takes once the issuer starts on it. */
    val workMs: Long = 50,
    /** Remember idempotency keys (true), or charge every request that arrives (false). */
    val dedupe: Boolean = true,
) {
    /** The truth: every charge this issuer made, in order. */
    val charges = mutableListOf<Charge>()

    var crashed = false
        private set
    private var pausedUntil = 0L

    init {
        net.join(name) { packet -> whenAwake { onRequest(packet.from, packet.body as AuthRequest) } }
    }

    /** Given. The process dies: it handles nothing from now on, and work in progress is never finished. */
    fun crash() {
        crashed = true
    }

    /** Given. The process stops (a long GC pause, a frozen VM) and carries on at [timeMs] as if nothing happened. */
    fun pauseUntil(timeMs: Long) {
        pausedUntil = maxOf(pausedUntil, timeMs)
    }

    private fun whenAwake(action: () -> Unit) {
        when {
            crashed -> return                                            // a dead process does nothing
            sim.now < pausedUntil -> sim.at(pausedUntil) { whenAwake(action) }   // packets wait in the socket buffer
            else -> action()
        }
    }

    /**
     * Given. Does the work for [request]: after [workMs] it charges the card once and passes the new
     * authorization code to [done]. If the server crashes first, the card is never charged.
     */
    fun charge(request: AuthRequest, done: (code: String) -> Unit) {
        sim.after(workMs) {
            whenAwake {
                val code = "A%05d".format(charges.size + 1)
                charges += Charge(request.key, request.amount, code, sim.now)
                done(code)
            }
        }
    }

    /** Given. Sends the authorization [code] for [key] to [to]. */
    fun reply(to: String, key: String, code: String) = net.send(name, to, AuthReply(key, code))

    private val codes = mutableMapOf<String, String>()      // key -> code, for keys already charged
    private val working = mutableSetOf<String>()            // keys being charged right now

    /**
     * Exercise 1. Handles one request from [from].
     *
     * Without [dedupe]: [charge] every request that arrives and [reply] with its code.
     * With [dedupe]:
     *  - a key already charged gets the same code back at once, with no second charge;
     *  - a key whose charge is still in progress gets nothing (that charge's reply is on its way);
     *  - a new key is charged, its code stored under the key, then sent back.
     */
    fun onRequest(from: String, request: AuthRequest) {
        if (!dedupe) {
            charge(request) { code -> reply(from, request.key, code) }   // every copy is a new charge
            return
        }
        val known = codes[request.key]
        when {
            known != null -> reply(from, request.key, known)            // a retry or a copy: same answer, no charge
            request.key in working -> Unit                               // the first copy is still being charged
            else -> {
                working += request.key
                charge(request) { code ->
                    codes[request.key] = code                            // store the result with the key, then answer
                    working -= request.key
                    reply(from, request.key, code)
                }
            }
        }
    }
}

class PaymentClient(
    private val sim: Sim,
    private val net: Network,
    val name: String = "shop",
    val server: String = "issuer",
    /** How long one attempt waits for a reply. */
    val timeoutMs: Long = 1_000,
    /** 1 means no retries. */
    val maxAttempts: Int = 1,
) {
    /** What the client decided, by key, in the order it decided. */
    val outcomes = linkedMapOf<String, Outcome>()

    /** Replies that arrived for a key the client had already decided about. */
    var lateReplies = 0
        private set

    private class Pending(val amount: Long, var attempts: Int = 0)
    private val pending = mutableMapOf<String, Pending>()

    init {
        net.join(name) { packet -> onReply(packet.body as AuthReply) }
    }

    /**
     * Exercise 2a. Starts authorizing [amount] under [key] and returns at once; the decision lands in
     * [outcomes] later.
     *
     * Send an [AuthRequest] with attempt 1 and wait [timeoutMs]. If no reply has arrived by then and
     * fewer than [maxAttempts] attempts were sent, send the same request again with the next attempt
     * number and wait again. When the last attempt times out, record [Outcome.Unknown].
     */
    fun authorize(key: String, amount: Long) {
        pending[key] = Pending(amount)
        attempt(key)
    }

    private fun attempt(key: String) {
        val p = pending.getValue(key)
        p.attempts++
        net.send(name, server, AuthRequest(key, p.amount, p.attempts))   // same key every time
        sim.after(timeoutMs) {
            if (key in outcomes) return@after                             // a reply came in time
            if (p.attempts < maxAttempts) attempt(key)
            else outcomes[key] = Outcome.Unknown(p.attempts, sim.now)     // not "declined": we don't know
        }
    }

    /**
     * Exercise 2b. A reply arrived. If the client is still waiting on that key, record
     * [Outcome.Approved] with the code and the attempts sent so far. If it has already decided
     * (an earlier reply, or it gave up), count a late reply and change nothing.
     */
    fun onReply(reply: AuthReply) {
        val p = pending[reply.key] ?: return
        if (reply.key in outcomes) {
            lateReplies++                                                 // proof it happened, after we stopped listening
            return
        }
        outcomes[reply.key] = Outcome.Approved(reply.code, p.attempts, sim.now)
    }
}

/** The client's beliefs against the issuer's truth. */
data class Audit(
    /** Payments the client decided about. */
    val payments: Int,
    /** The client heard a code. */
    val approved: Int,
    /** The client gave up without an answer. */
    val unknown: Int,
    /** Unknown to the client, but charged at least once. */
    val unknownButCharged: Int,
    /** Keys charged more than once. */
    val doubleCharged: Int,
    /** Charges beyond the first for each key, added up. */
    val extraCharges: Int,
)

/** Exercise 3. Counts each field of [Audit] from the client's [outcomes] and the issuer's [charges]. */
fun audit(outcomes: Map<String, Outcome>, charges: List<Charge>): Audit {
    val perKey = charges.groupingBy { it.key }.eachCount()                // how many times each card was charged
    val unknownKeys = outcomes.filterValues { it is Outcome.Unknown }.keys
    return Audit(
        payments = outcomes.size,
        approved = outcomes.values.count { it is Outcome.Approved },
        unknown = unknownKeys.size,
        unknownButCharged = unknownKeys.count { (perKey[it] ?: 0) > 0 },
        doubleCharged = perKey.values.count { it > 1 },
        extraCharges = perKey.values.sumOf { it - 1 },
    )
}

/** One finished run: the parts, so a test or demo can look at any of them. */
class Run(val sim: Sim, val net: Network, val server: PaymentServer, val client: PaymentClient) {
    val audit: Audit get() = audit(client.outcomes, server.charges)
}

/**
 * Given. Sends [count] payments of 12.50, one every [everyMs], keys `pay-1`, `pay-2`..., through a
 * network with [faults] in both directions, unless [requests] (shop to issuer) or [replies] (issuer
 * to shop) override one direction. [setup] runs before the first payment (crash or pause the issuer
 * there). Runs until nothing is left to happen.
 */
fun payments(
    seed: Long = 1,
    faults: Faults = Faults(),
    requests: Faults? = null,
    replies: Faults? = null,
    count: Int = 1_000,
    everyMs: Long = 10,
    timeoutMs: Long = 1_000,
    maxAttempts: Int = 1,
    dedupe: Boolean = true,
    workMs: Long = 50,
    setup: (Run) -> Unit = {},
): Run {
    val sim = Sim(seed)
    val net = Network(sim, faults)
    requests?.let { net.faults("shop", "issuer", it) }
    replies?.let { net.faults("issuer", "shop", it) }
    val server = PaymentServer(sim, net, workMs = workMs, dedupe = dedupe)
    val client = PaymentClient(sim, net, timeoutMs = timeoutMs, maxAttempts = maxAttempts)
    val run = Run(sim, net, server, client)
    setup(run)
    for (i in 1..count) sim.at((i - 1) * everyMs) { client.authorize("pay-$i", 1_250) }
    sim.run()
    return run
}
