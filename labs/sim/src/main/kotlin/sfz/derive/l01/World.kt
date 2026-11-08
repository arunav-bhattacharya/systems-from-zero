package sfz.derive.l01

import kotlin.random.Random

/*
 * Lesson derive-01 (given, nothing to change in this file).
 */

/** The 20 merchants of the simulated payments company. */
val MERCHANTS: List<String> = (1..20).map { "m-%02d".format(it) }

/**
 * Which of 100 buckets a merchant falls in. Stable: the same merchant always lands in the same
 * bucket, so a gradual shift moves whole merchants, never half of one.
 */
fun bucketOf(merchant: String): Int = Math.floorMod(merchant.hashCode() * 31 + 7, 100)

/**
 * A deterministic payments company. On construction it plays [days] days of history, [perDay]
 * payments a day, through [v1], the old job, which processes each payment the minute it arrives.
 * About 3% of payments are uploaded 6 to 10 hours late by a terminal that was offline, so for
 * those the arrival minute (processing time) and the payment's own minute (event time) differ,
 * sometimes by a day.
 *
 * After construction the clock stands at 09:00 on day [days] ("today"). Each [tick] is one
 * minute: [live] new payments arrive, then the migration's jobs poll. The first live payment of
 * the first tick is a late upload from yesterday 23:50 (merchant m-07, 123.45), so the tests have
 * one late payment they know about.
 */
class World(seed: Long, val days: Int = 30, val perDay: Int = 200) {
    private val random = Random(seed)
    val log = EventLog()

    /** v1, the job that serves the dashboard today. Its table is [DailyGross]. */
    val v1 = Job("v1", log, DailyGross(), batch = 100_000)

    var now: Long = 0
        private set

    val today: Long get() = days.toLong()

    private val arrivals = ArrayList<Long>()
    private var nextId = 0
    private var ticks = 0

    init {
        data class Arrival(val at: Long, val event: PaymentEvent)
        val history = ArrayList<Arrival>()
        for (day in 0 until days) repeat(perDay) {
            val e = payment(day * MINUTES_PER_DAY + 8 * 60 + random.nextLong(14 * 60))
            val delay = if (random.nextDouble() < 0.03) 360 + random.nextLong(240) else random.nextLong(3)
            history += Arrival(e.eventTime + delay, e)
        }
        history.sortWith(compareBy({ it.at }, { it.event.eventTime }))
        for (a in history) {
            now = a.at
            append(a.event, a.at)
            v1.poll(now)                                  // v1 handles each payment as it arrives
        }
        now = days * MINUTES_PER_DAY + 9 * 60
    }

    /** One minute passes: [live] payments arrive, then [migration] lets its jobs poll. */
    fun tick(migration: Migration, live: Int = 5) {
        now += 1
        repeat(live) { i ->
            val e = if (ticks == 0 && i == 0) LATE_UPLOAD.copy(eventTime = (today - 1) * MINUTES_PER_DAY + 23 * 60 + 50)
            else payment(now)
            append(e, now)
        }
        ticks++
        migration.tick(now)
    }

    /** The minute the record at [offset] arrived: its processing time on the live path. */
    fun arrivedAt(offset: Long): Long = arrivals[offset.toInt()]

    private fun append(e: PaymentEvent, at: Long) {
        log.append(e)
        arrivals += at
    }

    private fun payment(eventTime: Long): PaymentEvent {
        val refund = random.nextDouble() < 0.1
        return PaymentEvent(
            paymentId = "pay-%06d".format(nextId++),
            merchant = MERCHANTS[random.nextInt(MERCHANTS.size)],
            eventTime = eventTime,
            kind = if (refund) Kind.REFUNDED else Kind.CAPTURED,
            cents = if (refund) 500 + random.nextLong(3_000) else 500 + random.nextLong(19_500),
        )
    }

    companion object {
        /** The late upload the first tick delivers. */
        val LATE_UPLOAD = PaymentEvent("pay-late-1", "m-07", 0, Kind.CAPTURED, 12_345)
    }
}
