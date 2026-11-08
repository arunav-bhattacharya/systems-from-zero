package sfz.stream.l06.demo

import java.time.Duration
import java.time.Instant

/** One card authorization result. */
data class Auth(val card: String, val approved: Boolean, val at: Instant)

/**
 * A stored query, compiled to a small state machine per card: three declines in a row, then an approval, all within
 * 2 minutes of the first decline ("card testing": a fraudster tries numbers until one works). The events flow past
 * it; nothing is stored but each card's partial match.
 */
class CardTestingPattern(private val within: Duration = Duration.ofMinutes(2)) {
    /** Per card: the declines seen so far in the current partial match (the state machine's state). */
    private val partial = mutableMapOf<String, MutableList<Instant>>()

    /** Feeds one event; returns a description of the match if this event completes one. */
    fun onEvent(e: Auth): String? {
        val declines = partial.getOrPut(e.card) { mutableListOf() }
        if (declines.isNotEmpty() && Duration.between(declines.first(), e.at) > within) declines.clear() // too old: drop it
        if (!e.approved) {
            declines += e.at
            if (declines.size > 3) declines.removeAt(0)       // keep the three most recent declines
            return null
        }
        val match = if (declines.size == 3) "MATCH ${e.card}: 3 declines from ${hms(declines.first())}, approved at ${hms(e.at)}" else null
        declines.clear()                                      // an approval ends any partial match
        return match
    }

    fun state(card: String): String = "${partial[card]?.size ?: 0} declines"
}

fun main() {
    val t0 = Instant.parse("2026-11-07T10:00:00Z")
    fun ev(card: String, ok: Boolean, sec: Long) = Auth(card, ok, t0.plusSeconds(sec))
    val events = listOf(
        ev("card-1", false, 0), ev("card-2", true, 5), ev("card-1", false, 20), ev("card-1", false, 41),
        ev("card-1", true, 50),                                   // card-1: decline, decline, decline, approve in 50 s
        ev("card-3", false, 60), ev("card-3", false, 70), ev("card-3", true, 80),   // only two declines
        ev("card-4", false, 100), ev("card-4", false, 130), ev("card-4", false, 160), ev("card-4", true, 250),  // too slow
    )
    val pattern = CardTestingPattern()
    for (e in events) {
        val match = pattern.onEvent(e)
        println("%s %-7s %-8s state %-10s %s".format(hms(e.at), e.card,
            if (e.approved) "approved" else "declined", pattern.state(e.card), match ?: ""))
    }
}
