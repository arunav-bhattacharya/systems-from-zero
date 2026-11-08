package sfz.found.l03.demo

// This demo carries its own copy of the lab's simulator, including a finished RetryBudget.
// Do the lab first if you want to write the budget yourself.

import java.util.ArrayDeque
import java.util.PriorityQueue
import kotlin.random.Random

/** Decides whether a client may try again after an attempt times out. */
interface RetryPolicy {
    /** Called once for every new request, before its first attempt. */
    fun onRequest() {}

    /** Called when attempt number [attempt] (1 = the first) times out. True sends another attempt. */
    fun allowRetry(attempt: Int): Boolean

    /** How long to wait before that retry, in ms. 0 = straight away. */
    fun delayMs(attempt: Int): Int = 0
}

/** Never retry. */
object NoRetries : RetryPolicy {
    override fun allowRetry(attempt: Int) = false
}

/** Retry every timeout at once, up to [maxAttempts] attempts in all: the default in many clients. */
class RetryUpTo(private val maxAttempts: Int) : RetryPolicy {
    override fun allowRetry(attempt: Int) = attempt < maxAttempts
}

/**
 * Exponential backoff with full jitter: before retry n, wait a random time between 0 and
 * min(cap, base * 2^n) ms. It spreads retries out in time. It does not reduce how many there are.
 */
class BackoffRetry(private val maxAttempts: Int, private val baseMs: Int = 50, private val capMs: Int = 2_000, seed: Long = 1) : RetryPolicy {
    private val rnd = Random(seed)
    override fun allowRetry(attempt: Int) = attempt < maxAttempts
    override fun delayMs(attempt: Int) = rnd.nextInt(minOf(capMs, baseMs shl attempt) + 1)
}

/**
 * A retry budget: retries may add at most [ratio] extra load on top of the first attempts.
 * The policy keeps a bucket of tokens. Every new request adds [ratio] of a token, up to
 * [maxTokens]. Every retry needs one whole token and spends it. With no token in the bucket,
 * the client gives up instead of retrying. It also never goes past [maxAttempts] attempts.
 */
class RetryBudget(private val ratio: Double = 0.1, private val maxTokens: Double = 10.0, private val maxAttempts: Int = 4) : RetryPolicy {
    private var tokens = 0.0

    /** Tokens in the bucket now. The tests read it. */
    val available: Double get() = tokens

    override fun onRequest() {
        tokens = minOf(maxTokens, tokens + ratio)     // first attempts earn the right to retry
    }

    override fun allowRetry(attempt: Int): Boolean {
        if (attempt >= maxAttempts || tokens < 1.0) return false
        tokens -= 1.0                                 // each retry spends a whole token
        return true
    }
}

/** The service and the trigger. Rates are per second; time runs in 1 ms steps. */
data class StormConfig(
    val seconds: Int = 60,
    /** New requests from users per second, whatever the service is doing. */
    val newPerSecond: Int = 800,
    /** Requests the server can finish per second. */
    val capacityPerSecond: Int = 1_000,
    /** A client gives up on an attempt that has not been answered after this long. */
    val timeoutMs: Int = 200,
    /** From [triggerFromSec] to [triggerToSec] the capacity drops to [triggerCapacity]: a slow dependency, a GC storm. */
    val triggerFromSec: Int = 10,
    val triggerToSec: Int = 15,
    val triggerCapacity: Int = 400,
    /** If true, the server drops an attempt whose client has already given up, without working on it. */
    val shedExpired: Boolean = false,
)

/** What happened in one second of the run. */
data class Second(
    val t: Int,
    val newRequests: Int,
    /** Attempts sent: first attempts plus retries. */
    val attempts: Int,
    /** Answers that reached a client that was still waiting: useful work. */
    val goodput: Int,
    /** Answers that came too late: work the server did for nobody. */
    val wasted: Int,
    /** Attempts waiting in the server's queue at the end of the second. */
    val queued: Int,
)

/**
 * Runs the service for [StormConfig.seconds] seconds, in 1 ms steps, and reports each second (finished).
 *
 * Read it for two lines: a timed-out attempt makes the client send another one, and the server
 * still works on the old one, because it can't see that nobody is waiting for it. Together they
 * turn a few seconds of slowness into an outage that stays.
 */
fun simulateStorm(config: StormConfig, policy: RetryPolicy): List<Second> {
    class Attempt(val request: Int, val number: Int, val deadline: Int)

    val queue = ArrayDeque<Attempt>()                                    // the server's queue, oldest first
    val timeouts = PriorityQueue<Attempt>(compareBy { it.deadline })     // client-side timers
    val retries = PriorityQueue<Pair<Int, Attempt>>(compareBy { it.first }) // (send time, attempt) after a backoff
    val done = HashSet<Int>()
    val out = ArrayList<Second>()
    var nextId = 0
    var newAcc = 0.0
    var capAcc = 0.0
    var newRequests = 0; var attempts = 0; var goodput = 0; var wasted = 0

    fun send(request: Int, number: Int, now: Int) {
        val a = Attempt(request, number, now + config.timeoutMs)
        queue.addLast(a)
        timeouts += a
        attempts++
    }

    for (now in 0 until config.seconds * 1_000) {
        val sec = now / 1_000
        // 1. users send new requests at a steady rate
        newAcc += config.newPerSecond / 1_000.0
        while (newAcc >= 1.0) {
            newAcc -= 1.0
            policy.onRequest()
            send(nextId++, 1, now)
            newRequests++
        }
        // 2. retries whose backoff is over go out
        while (retries.isNotEmpty() && retries.peek().first <= now) {
            val (_, a) = retries.poll()
            send(a.request, a.number, now)
        }
        // 3. the server works through its queue, oldest first
        val capacity = if (sec in config.triggerFromSec until config.triggerToSec) config.triggerCapacity else config.capacityPerSecond
        capAcc += capacity / 1_000.0
        while (capAcc >= 1.0 && queue.isNotEmpty()) {
            val a = queue.pollFirst()
            if (config.shedExpired && now > a.deadline) continue             // nobody is waiting: drop it for free
            capAcc -= 1.0
            if (now <= a.deadline && a.request !in done) { done += a.request; goodput++ }
            else wasted++                                                    // the client gave up long ago
        }
        if (queue.isEmpty()) capAcc = minOf(capAcc, 1.0)                    // idle time can't be saved up
        // 4. clients whose attempt timed out decide whether to try again
        while (timeouts.isNotEmpty() && timeouts.peek().deadline <= now) {
            val a = timeouts.poll()
            if (a.request in done) continue
            if (policy.allowRetry(a.number)) {
                val delay = policy.delayMs(a.number)
                if (delay == 0) send(a.request, a.number + 1, now)
                else retries += (now + delay) to Attempt(a.request, a.number + 1, 0)
            }
        }
        if (now % 1_000 == 999) {
            out += Second(sec, newRequests, attempts, goodput, wasted, queue.size)
            newRequests = 0; attempts = 0; goodput = 0; wasted = 0
        }
    }
    return out
}

/**
 * The first second, at or after the trigger ended, from which every later second had goodput of
 * at least 95% of new requests. Null if the service never got back.
 */
fun recoveredAt(run: List<Second>, config: StormConfig): Int? {
    val after = run.filter { it.t >= config.triggerToSec }
    val firstBad = after.indexOfLast { it.goodput < 0.95 * it.newRequests }
    return when {
        firstBad == -1 -> config.triggerToSec
        firstBad == after.lastIndex -> null
        else -> after[firstBad + 1].t
    }
}


private fun show(name: String, config: StormConfig, policy: RetryPolicy) {
    val run = simulateStorm(config, policy)
    println("-- $name: recovered at ${recoveredAt(run, config)?.let { "t=${it}s" } ?: "never"}")
    println("   t   new  attempts  goodput  wasted  queued")
    for (s in run) if (s.t in listOf(5, 10, 11, 12, 14, 15, 16, 18, 20, 25, 30, 40, 59)) {
        println("%4d %5d %9d %8d %7d %7d".format(s.t, s.newRequests, s.attempts, s.goodput, s.wasted, s.queued))
    }
}

/**
 * 800 requests a second against a server that can do 1,000. From t=10 s to t=15 s a slow
 * dependency cuts that to 400. Clients give up on an attempt after 200 ms.
 */
fun main(args: Array<String>) {
    val which = args.firstOrNull() ?: "all"
    val c = StormConfig()
    if (which == "all" || which == "retry") show("retry up to 4 attempts", c, RetryUpTo(4))
    if (which == "all" || which == "none") show("no retries", c, NoRetries)
    if (which == "all" || which == "backoff") show("backoff with jitter, 4 attempts", c, BackoffRetry(4))
    if (which == "all" || which == "budget") show("retry budget, 10%", c, RetryBudget())
    if (which == "all" || which == "shed") show("retry up to 4, server sheds expired work", c.copy(shedExpired = true), RetryUpTo(4))
}
