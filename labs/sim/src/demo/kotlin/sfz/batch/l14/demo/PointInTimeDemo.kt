package sfz.batch.l14.demo

import java.time.Duration
import java.time.Instant
import kotlin.random.Random

/**
 * A month of card payments with fraud labels, and the feature "chargebacks on this card in the
 * last 30 days", computed every night. The training set is built twice: once with each card's
 * newest feature value, once point in time. Then a one-line rule, "flag the payment if the card
 * has had a chargeback", is scored on both, and on what it would really see in production.
 */
private data class Label(val card: Int, val at: Instant, val fraud: Boolean)
private data class Row(val card: Int, val asOf: Instant, val computedAt: Instant, val value: Int)

fun main() {
    val start = Instant.parse("2026-10-01T00:00:00Z")
    val rnd = Random(11)
    val labels = mutableListOf<Label>()
    val chargebacks = mutableListOf<Pair<Int, Instant>>()
    for (card in 0 until 5_000) {
        val compromisedFrom = if (rnd.nextDouble() < 0.05) 3 + rnd.nextInt(24) else Int.MAX_VALUE
        for (d in 0 until 30) {
            val at = start.plus(Duration.ofDays(d.toLong())).plusSeconds(rnd.nextLong(86_400))
            val fraud = d >= compromisedFrom && rnd.nextDouble() < 0.6
            labels += Label(card, at, fraud)
            if (fraud) chargebacks += card to at.plus(Duration.ofHours(48 + rnd.nextLong(144)))
            else if (rnd.nextDouble() < 0.003) chargebacks += card to at.plus(Duration.ofHours(120 + rnd.nextLong(360)))
        }
    }
    val byCard = chargebacks.groupBy({ it.first }, { it.second })
    val rows = (0 until 5_000).flatMap { card ->
        (0..30).map { d ->
            val asOf = start.plus(Duration.ofDays(d.toLong()))
            Row(card, asOf, asOf.plus(Duration.ofHours(2)), byCard[card].orEmpty().count { it < asOf && it >= asOf.minus(Duration.ofDays(30)) })
        }
    }
    val history = rows.groupBy { it.card }.mapValues { (_, r) -> r.sortedBy { it.asOf } }

    val newest = labels.map { l -> l to history.getValue(l.card).last() }
    val pointInTime = labels.map { l -> l to history.getValue(l.card).lastOrNull { it.asOf <= l.at && it.computedAt <= l.at } }
    println("labels: %,d payments, %,d of them fraud; feature rows: %,d".format(labels.size, labels.count { it.fraud }, rows.size))
    println("newest-row join:    %,d labels got a value computed after the payment".format(newest.count { (l, r) -> r.computedAt > l.at }))
    println("point-in-time join: %,d".format(pointInTime.count { (l, r) -> r != null && r.computedAt > l.at }))

    fun score(name: String, set: List<Pair<Label, Row?>>) {
        val flagged = set.filter { (_, r) -> (r?.value ?: 0) >= 1 }
        val caught = flagged.count { it.first.fraud }
        println("%-38s flags %,6d payments: precision %3.0f%%, recall %3.0f%%".format(name, flagged.size,
            100.0 * caught / flagged.size, 100.0 * caught / labels.count { it.fraud }))
    }
    println("the rule \"the card has had a chargeback in the last 30 days\":")
    score("  trained on the newest-row join", newest)
    score("  trained on the point-in-time join", pointInTime)
    score("  in production (what it can see live)", pointInTime)
}
