package sfz.dist.l01

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
