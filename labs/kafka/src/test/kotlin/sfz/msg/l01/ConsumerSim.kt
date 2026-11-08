package sfz.msg.l01

/**
 * Drives consumers against one [MiniQueue], one tick at a time, with no threads and no randomness, so every run of a
 * test sees the same interleaving.
 *
 * Each tick, every consumer that is up, in turn:
 * 1. tops up what it holds with [MiniQueue.deliver], until it holds `prefetch` unacknowledged deliveries;
 * 2. if it is idle, starts on the oldest delivery it holds (deliveries wait in a local buffer, first in, first out);
 * 3. works one tick on it. A message takes 1 to 3 ticks, depending on the message. When the work is done the
 *    consumer appends the message to [processed] (think: books it in the ledger) and acknowledges it.
 *
 * [crash] is a consumer dying at the worst moment: it has just finished its current message, so the work is done, but
 * the ack never leaves. Everything else it held is lost with its memory, its connection closes, and it comes back
 * after [restartTicks] ticks, as a restarted instance would.
 */
class ConsumerSim(
    private val queue: MiniQueue,
    private val names: List<String>,
    private val prefetch: Int,
    private val autoAck: Boolean = false,
    private val restartTicks: Int = 5,
) {
    /** Every message any consumer finished, in the order they finished. Shared by all consumers, like one ledger. */
    val processed = mutableListOf<Message>()

    /** The same, per consumer. */
    val processedBy: Map<String, MutableList<Message>> = names.associateWith { mutableListOf() }

    /** How many deliveries arrived with the redelivered flag set. */
    var redeliveries = 0
        private set

    private class Work(val delivery: Delivery, var ticksLeft: Int)

    private val held: Map<String, ArrayDeque<Delivery>> = names.associateWith { ArrayDeque() }
    private val working = HashMap<String, Work>()
    private val down = HashMap<String, Int>()            // consumer -> ticks until it is back

    init {
        names.forEach { queue.subscribe(it, prefetch, autoAck) }
    }

    fun tick() {
        for (c in names) {
            val wait = down[c]
            if (wait != null) {
                if (wait > 1) down[c] = wait - 1 else { down.remove(c); queue.subscribe(c, prefetch, autoAck) }
                continue
            }
            val mine = held.getValue(c)
            while (mine.size + (if (working.containsKey(c)) 1 else 0) < prefetch) {
                val d = queue.deliver(c) ?: break
                if (d.redelivered) redeliveries++
                mine.addLast(d)
            }
            val work = working[c] ?: mine.removeFirstOrNull()?.let { Work(it, cost(it.message)).also { w -> working[c] = w } }
                ?: continue
            if (--work.ticksLeft == 0) {
                working.remove(c)
                finish(c, work.delivery.message)
                if (!autoAck) queue.ack(work.delivery.tag)
            }
        }
    }

    fun crash(consumer: String) {
        if (down.containsKey(consumer)) return
        working.remove(consumer)?.let { finish(consumer, it.delivery.message) }   // the work is done, the ack is lost
        held.getValue(consumer).clear()
        queue.disconnect(consumer)
        down[consumer] = restartTicks
    }

    /** Ticks until the queue is empty and every consumer is idle, crashing [crashing] every [crashEvery] ticks. */
    fun run(crashing: String? = null, crashEvery: Int = 0, maxTicks: Int = 100_000) {
        var t = 0
        while (queue.ready > 0 || queue.unacked > 0 || working.isNotEmpty() || down.isNotEmpty() ||
            held.values.any { it.isNotEmpty() }
        ) {
            check(++t <= maxTicks) { "still not drained after $maxTicks ticks" }
            if (crashing != null && crashEvery > 0 && t % crashEvery == 0) crash(crashing)
            tick()
        }
    }

    private fun finish(consumer: String, message: Message) {
        processed += message
        processedBy.getValue(consumer) += message
    }

    companion object {
        /** [n] payment events for [keys] accounts, published round robin: message i is account i % keys, seq i / keys. */
        fun payments(n: Int, keys: Int): List<Message> = (0 until n).map { Message("acct-${it % keys}", it / keys) }

        /** How many ticks a consumer works on [m]: 1, 2 or 3, fixed per message. */
        fun cost(m: Message): Int = 1 + Math.floorMod(m.seq * 7 + m.key.hashCode(), 3)
    }
}
