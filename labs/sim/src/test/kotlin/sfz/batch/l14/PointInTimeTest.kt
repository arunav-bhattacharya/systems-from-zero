package sfz.batch.l14

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.time.Duration
import java.time.Instant

class PointInTimeTest {
    private fun at(s: String) = Instant.parse(s)
    private fun label(card: Int, time: String) = Label(0, card, at(time), fraud = false)

    // card 1's history: midnight values written at 02:00, and a late correction of 2 November written on 6 November
    private val history = listOf(
        FeatureRow(1, at("2026-11-01T00:00:00Z"), at("2026-11-01T02:00:00Z"), 0),
        FeatureRow(1, at("2026-11-02T00:00:00Z"), at("2026-11-02T02:00:00Z"), 1),
        FeatureRow(1, at("2026-11-02T00:00:00Z"), at("2026-11-06T02:00:00Z"), 2),
        FeatureRow(1, at("2026-11-03T00:00:00Z"), at("2026-11-03T02:00:00Z"), 1),
        FeatureRow(2, at("2026-11-01T00:00:00Z"), at("2026-11-01T02:00:00Z"), 7),
    )

    private fun valueFor(l: Label, ttl: Duration = Duration.ofDays(2)) =
        TrainingSet.pointInTimeJoin(listOf(l), history, ttl).single().feature?.value

    @Test
    fun `a label sees the newest value that existed at its time`() {
        assertThat(valueFor(label(1, "2026-11-02T15:00:00Z"))).describedAs("the 2 Nov value, written at 02:00").isEqualTo(1)
        assertThat(valueFor(label(1, "2026-11-03T15:00:00Z"))).describedAs("the 3 Nov value").isEqualTo(1)
        assertThat(valueFor(label(2, "2026-11-01T09:00:00Z"))).describedAs("another card's history").isEqualTo(7)
    }

    @Test
    fun `a value computed after the label is invisible, even when its asOf is in the past`() {
        assertThat(valueFor(label(1, "2026-11-02T01:00:00Z"))).describedAs("2 Nov not written until 02:00: fall back to 1 Nov").isEqualTo(0)
        // a label on 6 Nov at 03:00, with the ttl wide enough to reach back to the 2 Nov rows: the correction now counts
        val wide = Duration.ofDays(5)
        val rows = listOf(FeatureRow(1, at("2026-11-02T00:00:00Z"), at("2026-11-02T02:00:00Z"), 1),
            FeatureRow(1, at("2026-11-02T00:00:00Z"), at("2026-11-06T02:00:00Z"), 2))
        fun pick(time: String) = TrainingSet.pointInTimeJoin(listOf(label(1, time)), rows, wide).single().feature?.value
        assertThat(pick("2026-11-05T12:00:00Z")).describedAs("before the correction was written").isEqualTo(1)
        assertThat(pick("2026-11-06T03:00:00Z")).describedAs("after it: the latest computedAt wins the tie").isEqualTo(2)
    }

    @Test
    fun `no usable row gives a null feature, never a later one`() {
        assertThat(valueFor(label(1, "2026-10-31T23:00:00Z"))).describedAs("before the first row").isNull()
        assertThat(valueFor(label(3, "2026-11-03T12:00:00Z"))).describedAs("a card with no rows").isNull()
        assertThat(valueFor(label(2, "2026-11-04T12:00:00Z"))).describedAs("card 2's only row is older than the 2-day ttl").isNull()
    }

    @Test
    @Timeout(10)
    fun `on a month of data it never leaks, where the newest-row join leaks into most labels`() {
        val (labels, features) = FraudData.generate()
        val naive = TrainingSet.latestJoin(labels, features)
        val right = TrainingSet.pointInTimeJoin(labels, features)
        assertThat(TrainingSet.leaks(naive)).describedAs("leaks of the newest-row join").isGreaterThan(labels.size / 2)
        assertThat(TrainingSet.leaks(right)).describedAs("leaks of the point-in-time join").isZero()
        assertThat(right.map { it.label }).describedAs("labels kept in order").isEqualTo(labels)
        assertThat(right.filter { it.feature == null }.map { it.label.at }).describedAs("labels with no usable row: only before the first job wrote")
            .allMatch { it < FraudData.START.plus(Duration.ofHours(2)) }
        // the same answer as the obvious, slow scan
        val byCard = features.groupBy { it.cardId }
        val brute = labels.take(3_000).map { l ->
            byCard.getValue(l.cardId).filter { it.asOf <= l.at && it.computedAt <= l.at && it.asOf >= l.at.minus(Duration.ofDays(2)) }
                .maxWithOrNull(compareBy({ it.asOf }, { it.computedAt }))
        }
        assertThat(right.take(3_000).map { it.feature }).isEqualTo(brute)
    }
}
