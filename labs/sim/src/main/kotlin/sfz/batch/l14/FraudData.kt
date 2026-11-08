package sfz.batch.l14

import java.time.Duration
import java.time.Instant
import kotlin.random.Random

/** A training example: was this payment fraud? `at` is when it happened, so when a model would have had to decide. */
data class Label(val paymentId: Long, val cardId: Int, val at: Instant, val fraud: Boolean)

/**
 * One value of the feature "chargebacks on this card in the 30 days before [asOf]". The nightly
 * feature job computes it as of midnight ([asOf], its event time) and writes it to the offline
 * store at [computedAt]. A late correction is a second row with the same [asOf] and a later
 * [computedAt].
 */
data class FeatureRow(val cardId: Int, val asOf: Instant, val computedAt: Instant, val value: Int)

/** A label with the feature row chosen for it, or null if none was usable. */
data class TrainingRow(val label: Label, val feature: FeatureRow?)

/**
 * Lesson batch-14 (given): made-up card payments with fraud labels and the chargeback feature, the
 * same on every run. Read it, but you don't need to change it.
 *
 * Each card pays once a day for [days] days from [START]. About 5% of cards get compromised on some
 * day, and after that 60% of their payments are fraud. Every fraud brings a chargeback 2 to 8 days
 * later; an honest payment brings one with chance 0.3%, 5 to 20 days later. The feature job runs
 * every night at 02:00, and on about 5% of card-days a correction for that day arrives four days
 * later.
 */
object FraudData {
    val START: Instant = Instant.parse("2026-10-01T00:00:00Z")

    fun generate(cards: Int = 500, days: Int = 30, seed: Long = 11): Pair<List<Label>, List<FeatureRow>> {
        val rnd = Random(seed)
        val day = Duration.ofDays(1)
        val labels = mutableListOf<Label>()
        val chargebacks = mutableListOf<Pair<Int, Instant>>()
        for (card in 0 until cards) {
            val compromisedFrom = if (rnd.nextDouble() < 0.05) 3 + rnd.nextInt(days - 6) else Int.MAX_VALUE
            for (d in 0 until days) {
                val at = START.plus(day.multipliedBy(d.toLong())).plusSeconds(rnd.nextLong(86_400))
                val fraud = d >= compromisedFrom && rnd.nextDouble() < 0.6
                labels += Label(labels.size.toLong(), card, at, fraud)
                if (fraud) chargebacks += card to at.plus(Duration.ofHours(48 + rnd.nextLong(6 * 24)))
                else if (rnd.nextDouble() < 0.003) chargebacks += card to at.plus(Duration.ofHours(120 + rnd.nextLong(15 * 24)))
            }
        }
        val byCard = chargebacks.groupBy({ it.first }, { it.second })
        val features = mutableListOf<FeatureRow>()
        for (card in 0 until cards) {
            val times = byCard[card].orEmpty()
            for (d in 0..days) {
                val asOf = START.plus(day.multipliedBy(d.toLong()))
                val value = times.count { it < asOf && it >= asOf.minus(Duration.ofDays(30)) }
                features += FeatureRow(card, asOf, asOf.plus(Duration.ofHours(2)), value)
                if (rnd.nextDouble() < 0.05) features += FeatureRow(card, asOf, asOf.plus(Duration.ofDays(4)), value + 1)
            }
        }
        return labels to features
    }
}

/** Lesson batch-14: building a training set from labels and a feature's history. */
object TrainingSet {
    /** Given, and wrong: gives every label its card's newest feature row, whenever that was computed. */
    fun latestJoin(labels: List<Label>, features: List<FeatureRow>): List<TrainingRow> {
        val newest = features.groupBy { it.cardId }.mapValues { (_, rows) -> rows.maxWith(compareBy({ it.asOf }, { it.computedAt })) }
        return labels.map { TrainingRow(it, newest[it.cardId]) }
    }

    /** Given: how many rows got a feature value that didn't exist yet at the label's time. */
    fun leaks(rows: List<TrainingRow>): Int =
        rows.count { r -> r.feature != null && (r.feature.asOf > r.label.at || r.feature.computedAt > r.label.at) }

    /**
     * Exercise 1. The point-in-time join. For each label, in the order given, pick the feature row
     * of the same card that a model could have read at `label.at`:
     *
     * - its `asOf` is at or before `label.at`, and not older than `label.at` minus [ttl];
     * - its `computedAt` is at or before `label.at` (it had been written by then);
     * - of those, the one with the latest `asOf`, and on a tie the latest `computedAt`.
     *
     * No such row: the label gets a null feature. Don't scan every row for every label: group the
     * rows by card and sort them first.
     */
    fun pointInTimeJoin(labels: List<Label>, features: List<FeatureRow>, ttl: Duration = Duration.ofDays(2)): List<TrainingRow> {
        TODO("Exercise 1: per card, the newest row with asOf <= at, computedAt <= at and asOf >= at - ttl")
    }
}
