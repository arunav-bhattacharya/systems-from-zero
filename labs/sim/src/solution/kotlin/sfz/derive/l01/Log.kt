package sfz.derive.l01

/*
 * Lesson derive-01 (given, nothing to change in this file).
 *
 * Time in this lab is in minutes since 00:00 on day 0. Day 30 is "today": the day you migrate.
 */

const val MINUTES_PER_DAY = 1440L

/** The day a minute falls on. */
fun dayOf(minute: Long): Long = Math.floorDiv(minute, MINUTES_PER_DAY)

enum class Kind { CAPTURED, REFUNDED }

/**
 * One fact in the system of record. [eventTime] is when the payment happened on the card
 * terminal, in minutes. It travels inside the event, so a replay a month later still knows it.
 */
data class PaymentEvent(
    val paymentId: String,
    val merchant: String,
    val eventTime: Long,
    val kind: Kind,
    val cents: Long,
)

/** A record in the log: the offset it was given on append, and the event. */
data class Record(val offset: Long, val event: PaymentEvent)

/** The retained log every view is derived from. Offsets start at 0 and never change. */
class EventLog {
    private val events = ArrayList<PaymentEvent>()

    /** Appends one event and returns its offset. */
    fun append(e: PaymentEvent): Long {
        events += e
        return events.size - 1L
    }

    /** Up to [max] records starting at offset [from], in order. */
    fun read(from: Long, max: Int): List<Record> {
        val start = from.toInt().coerceIn(0, events.size)
        val stop = (start.toLong() + max).coerceAtMost(events.size.toLong()).toInt()
        return (start until stop).map { Record(it.toLong(), events[it]) }
    }

    /** The offset the next append will get, which is also the number of records. */
    val end: Long get() = events.size.toLong()
}

/** A derived table: daily revenue per merchant, built only from log records. */
interface View {
    /** Applies one record. [processedAt] is the minute the job handled it: processing time. */
    fun apply(r: Record, processedAt: Long)

    /** Cents for one merchant on one day; 0 if nothing was recorded. */
    fun cents(merchant: String, day: Long): Long

    /** Drops every row. */
    fun clear()
}

/**
 * A stream job: one consumer that reads the log from its own [position] and writes one [view].
 * Each [poll] reads at most [batch] records, so a job that starts at offset 0 takes a while to
 * catch up with the end of the log.
 */
class Job(val name: String, private val log: EventLog, val view: View, private val batch: Int) {
    /** The next offset this job will read. A new job starts at 0: the beginning of the log. */
    var position: Long = 0
        private set

    var running: Boolean = true
        private set

    /** Reads and applies up to [batch] records. Returns how many it applied. */
    fun poll(now: Long): Int {
        if (!running) return 0
        val records = log.read(position, batch)
        for (r in records) view.apply(r, now)
        position += records.size
        return records.size
    }

    /** How many records this job still has to read to reach the end of the log. */
    val lag: Long get() = log.end - position

    /** Stops the job and drops its table. */
    fun stop() {
        running = false
        view.clear()
    }
}
