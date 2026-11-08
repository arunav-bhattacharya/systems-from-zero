package sfz.derive.l02

/*
 * Lesson derive-02. The pieces of a small dataflow app:
 *
 *   write path:  transfer -> Log (the system of record, gives each write an offset)
 *   derivation:  Processor polls the log, runs Balances.apply (application code), publishes Diffs
 *   read path:   readNow / readAfter on the Processor's view
 *   push:        Feed sends each Diff to the clients subscribed to that account
 *
 * Given in this file: Transfer, Entry, Log, Diff, Read, Connection and most of Feed and Processor.
 * Yours: Feed.since, Processor.readAfter and Processor.releaseParked (and Balances.apply and
 * ClientCopy.receive in the other files).
 */

data class Transfer(val id: String, val from: String, val to: String, val cents: Long)

/** A transfer as the log stores it, with its offset. */
data class Entry(val offset: Long, val transfer: Transfer)

/** The system of record: an append-only list of transfers. */
class Log {
    private val entries = ArrayList<Entry>()

    /** Appends [t] and returns its offset (0, 1, 2 ...). The write path ends here. */
    fun append(t: Transfer): Long {
        val e = Entry(entries.size.toLong(), t)
        entries += e
        return e.offset
    }

    fun get(offset: Long): Entry = entries[offset.toInt()]

    /** The offset the next append will get. */
    val end: Long get() = entries.size.toLong()
}

/**
 * One change to one row of the view: [account]'s balance moved by [delta] cents because of the
 * log entry at [offset]. A transfer makes two: minus on the payer, plus on the payee.
 */
data class Diff(val offset: Long, val account: String, val delta: Long)

/** An answer from the view, and the offset the view had applied up to when it answered. */
data class Read(val account: String, val balance: Long, val appliedOffset: Long)

/** One push connection to one client. A diff that lands while the connection is down is lost. */
class Connection(private val sim: Sim, private val client: ClientCopy, private val latencyMs: Long) {
    var up: Boolean = true

    fun send(d: Diff) = sim.after(latencyMs) { if (up) client.receive(d) }
}

/** Pushes every published diff to the connections subscribed to its account, and keeps them all. */
class Feed(private val sim: Sim) {
    private val history = ArrayList<Diff>()                      // every diff ever published, in offset order
    private val subscribers = HashMap<String, MutableList<Connection>>()

    /** Called by the processor after each entry it applies (given). */
    fun publish(diffs: List<Diff>) {
        history += diffs
        for (d in diffs) subscribers[d.account]?.forEach { it.send(d) }
    }

    /** Opens a push connection for [client]'s account (given). */
    fun connect(client: ClientCopy, latencyMs: Long = 20): Connection =
        Connection(sim, client, latencyMs).also { subscribers.getOrPut(client.account) { mutableListOf() } += it }

    /**
     * Every diff for [account] with an offset greater than [afterOffset], in offset order. A
     * client that reconnects asks for this, the way a log consumer resumes from its offset.
     */
    fun since(account: String, afterOffset: Long): List<Diff> {
        TODO("filter the history")
    }
}

/**
 * The derivation job: one consumer that polls the log every 40 to 60 ms (seeded jitter), applies
 * each new entry to [view] in offset order, and publishes the diffs. Between polls the view is
 * behind the log: that is the lag a read right after a write can fall into.
 */
class Processor(
    private val sim: Sim,
    private val log: Log,
    val view: Balances,
    private val feed: Feed,
    private val pollEveryMs: Long = 50,
) {
    /** The offset of the last entry applied to [view]; -1 before the first. */
    var applied: Long = -1
        private set

    /** A read waiting for the view to reach [offset]. */
    class Parked(val account: String, val offset: Long, val reply: (Read) -> Unit)

    private val parked = ArrayList<Parked>()

    /** How many reads are parked right now. */
    val waiting: Int get() = parked.size

    /** Starts the poll loop (given). */
    fun start() {
        sim.after(pollEveryMs) { loop() }
    }

    private fun loop() {
        poll()
        sim.after(pollEveryMs - 10 + sim.random.nextLong(21)) { loop() }
    }

    /** Applies everything new in the log, in order, then answers the reads that were waiting for it (given). */
    fun poll() {
        while (applied + 1 < log.end) {
            val e = log.get(applied + 1)
            val diffs = view.apply(e)
            applied = e.offset
            feed.publish(diffs)
        }
        releaseParked()
    }

    /** The read path as most apps write it: answer from the view as it is now, possibly stale (given). */
    fun readNow(account: String): Read = Read(account, view.get(account), applied)

    /**
     * A read that waits for the caller's own write. If the view has already applied [offset],
     * call [reply] now with [readNow]. Otherwise park the read; [poll] will answer it.
     */
    fun readAfter(account: String, offset: Long, reply: (Read) -> Unit) {
        TODO("reply now if offset is applied, else park")
    }

    /**
     * Answers, with [readNow], every parked read whose offset has now been applied, and removes
     * it, so each is answered exactly once. Reads still ahead of the view stay parked.
     */
    private fun releaseParked() {
        TODO("answer and remove the parked reads the view has caught up with")
    }
}
