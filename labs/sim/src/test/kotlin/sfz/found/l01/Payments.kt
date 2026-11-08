package sfz.found.l01

import kotlin.random.Random

/**
 * A seeded stream of realistic payment events: every payment is authorized first, some are then
 * captured, and some captured ones are refunded, possibly on a later day. The same seed always
 * gives the same events.
 */
object Payments {
    val merchants = listOf("m-cafe", "m-books", "m-bikes", "m-shoes", "m-hotel")
    val days = listOf("2026-03-01", "2026-03-02", "2026-03-03")

    fun events(seed: Long, payments: Int): List<PaymentEvent> {
        val rnd = Random(seed)
        val out = ArrayList<PaymentEvent>()
        // payments that are waiting for their next step, in a random order
        val open = ArrayList<Pair<PaymentEvent, Kind>>()
        var next = 1
        while (next <= payments || open.isNotEmpty()) {
            val startNew = next <= payments && (open.isEmpty() || rnd.nextInt(3) != 0)
            if (startNew) {
                val e = PaymentEvent(
                    "pay-%06d".format(next++), merchants[rnd.nextInt(merchants.size)],
                    days[rnd.nextInt(days.size)], Kind.AUTHORIZED, 100L * rnd.nextInt(1, 500),
                )
                out += e
                if (rnd.nextInt(10) < 8) open += e to Kind.CAPTURED          // 80% get captured
            } else {
                val (auth, step) = open.removeAt(rnd.nextInt(open.size))
                val day = days[(days.indexOf(auth.day) + rnd.nextInt(2)).coerceAtMost(days.size - 1)]
                out += auth.copy(day = day, kind = step)
                if (step == Kind.CAPTURED && rnd.nextInt(10) == 0) open += auth.copy(day = day) to Kind.REFUNDED
            }
        }
        return out
    }
}
