package sfz.msg.l01.demo

import java.util.TreeMap

/*
 * 1,000 payment events for 10 accounts go through a broker queue, in memory, with no threads and no randomness.
 * Consumers take 1 to 3 ticks per message. A crashing consumer dies just after finishing a message and before its
 * ack, every N ticks (25 unless you pass another number), and comes back 5 ticks later.
 * For each setup the demo counts redeliveries, duplicates, per-account inversions and lost messages.
 */

private data class Message(val key: String, val seq: Int)

private data class Delivery(val tag: Long, val message: Message, val redelivered: Boolean)

/** A queue with acks, prefetch and redelivery to the original position. */
private class Queue {
    data class Entry(val position: Long, val message: Message, val returns: Int)
    data class InFlight(val entry: Entry, val consumer: String)

    val waiting = TreeMap<Long, Entry>()
    val inFlight = LinkedHashMap<Long, InFlight>()
    private val prefetch = HashMap<String, Int>()
    private val autoAck = HashSet<String>()
    private var nextPosition = 0L
    private var nextTag = 1L

    fun publish(m: Message) {
        waiting[nextPosition] = Entry(nextPosition, m, 0)
        nextPosition++
    }

    fun subscribe(c: String, max: Int, auto: Boolean) {
        prefetch[c] = max
        if (auto) autoAck += c
    }

    fun deliver(c: String): Delivery? {
        val auto = c in autoAck
        if (!auto && inFlight.values.count { it.consumer == c } >= prefetch.getValue(c)) return null   // at its prefetch
        val head = waiting.pollFirstEntry()?.value ?: return null
        val tag = nextTag++
        if (!auto) inFlight[tag] = InFlight(head, c)
        return Delivery(tag, head.message, head.returns > 0)
    }

    fun ack(tag: Long) {
        inFlight.remove(tag)
    }

    fun disconnect(c: String) {
        for (tag in inFlight.filterValues { it.consumer == c }.keys.toList()) {
            val e = inFlight.remove(tag)!!.entry
            waiting[e.position] = e.copy(returns = e.returns + 1)   // back to its old place
        }
    }
}

/** Consumers on one queue, one tick at a time. */
private class Sim(val q: Queue, val names: List<String>, val prefetch: Int, val auto: Boolean) {
    val booked = mutableListOf<Message>()
    private val held = names.associateWith { ArrayDeque<Delivery>() }
    private val working = HashMap<String, Delivery>()
    private val ticksLeft = HashMap<String, Int>()
    private val down = HashMap<String, Int>()
    var redelivered = 0
        private set

    init {
        names.forEach { q.subscribe(it, prefetch, auto) }
    }

    fun tick() {
        for (c in names) {
            val wait = down[c]
            if (wait != null) {
                if (wait > 1) down[c] = wait - 1 else down.remove(c)
                continue
            }
            val mine = held.getValue(c)
            while (mine.size + (if (c in working) 1 else 0) < prefetch) {
                val d = q.deliver(c) ?: break
                if (d.redelivered) redelivered++
                mine.addLast(d)
            }
            if (c !in working) {
                val next = mine.removeFirstOrNull() ?: continue
                working[c] = next
                ticksLeft[c] = cost(next.message)
            }
            val left = ticksLeft.getValue(c) - 1
            ticksLeft[c] = left
            if (left == 0) {
                val done = working.remove(c)!!
                booked += done.message
                if (!auto) q.ack(done.tag)
            }
        }
    }

    fun crash(c: String) {
        if (c in down) return
        working.remove(c)?.let { booked += it.message }   // the work is done, the ack is lost
        held.getValue(c).clear()
        q.disconnect(c)
        down[c] = 5                                         // back in 5 ticks
    }

    fun run(crashing: String?, every: Int) {
        var t = 0
        while (q.waiting.isNotEmpty() || q.inFlight.isNotEmpty() || working.isNotEmpty() || down.isNotEmpty() ||
            held.values.any { it.isNotEmpty() }
        ) {
            t++
            if (crashing != null && every > 0 && t % every == 0) crash(crashing)
            tick()
        }
    }

    companion object {
        fun cost(m: Message) = 1 + Math.floorMod(m.seq * 7 + m.key.hashCode(), 3)
    }
}

private fun payments() = (0 until 1000).map { Message("acct-${it % 10}", it / 10) }

/** The row: booked, redelivered, duplicates, inversions, lost. */
private fun row(setup: String, booked: List<Message>, redelivered: Int) {
    val seen = HashSet<Message>()
    val highest = HashMap<String, Int>()
    var duplicates = 0
    var inversions = 0
    for (m in booked) {
        if (!seen.add(m)) {
            duplicates++
            continue
        }
        val top = highest[m.key]
        if (top != null && m.seq < top) inversions++ else highest[m.key] = m.seq
    }
    println("%-38s %6d %11d %10d %10d %5d".format(setup, booked.size, redelivered, duplicates, inversions, 1000 - seen.size))
}

private fun oneQueue(setup: String, consumers: List<String>, prefetch: Int, auto: Boolean, every: Int) {
    val q = Queue()
    payments().forEach(q::publish)
    val sim = Sim(q, consumers, prefetch, auto)
    sim.run(consumers.last(), every)
    row(setup, sim.booked, sim.redelivered)
}

fun main(args: Array<String>) {
    val every = args.firstOrNull()?.toInt() ?: 25
    println("1,000 payments, 10 accounts; a crash every %d ticks".format(every))
    println("%-38s %6s %11s %10s %10s %5s".format("setup", "booked", "redelivered", "duplicates", "inversions", "lost"))
    oneQueue("1 consumer,  prefetch 10, no crash", listOf("A"), 10, false, 0)
    oneQueue("1 consumer,  prefetch 10, crashes", listOf("A"), 10, false, every)
    oneQueue("2 consumers, prefetch 1,  crashes", listOf("A", "B"), 1, false, every)
    oneQueue("2 consumers, prefetch 10, no crash", listOf("A", "B"), 10, false, 0)
    oneQueue("2 consumers, prefetch 10, crashes", listOf("A", "B"), 10, false, every)
    oneQueue("2 consumers, prefetch 100, crashes", listOf("A", "B"), 100, false, every)
    oneQueue("1 consumer,  auto-ack, crashes", listOf("A"), 10, true, every)

    // one queue per half of the accounts, one consumer each: the way a log's partitions work
    val even = Queue()
    val odd = Queue()
    for (m in payments()) (if (m.key.removePrefix("acct-").toInt() % 2 == 0) even else odd).publish(m)
    val a = Sim(even, listOf("A"), 10, false).apply { run("A", every) }
    val b = Sim(odd, listOf("B"), 10, false).apply { run("B", every) }
    row("2 queues by account, 1 consumer each", a.booked + b.booked, a.redelivered + b.redelivered)
}
