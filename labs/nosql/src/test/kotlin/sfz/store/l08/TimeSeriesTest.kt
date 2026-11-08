package sfz.store.l08

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import java.time.Duration
import java.time.Instant

class TimeSeriesTest {
    private val t0: Instant = Instant.parse("2026-11-07T09:00:00Z")

    // authorization latencies in ms, one every 10 seconds for an hour; every 7th one is slow
    private val points = (0 until 360).map { i -> Point(t0.plusSeconds(i * 10L), if (i % 7 == 0) 640.0 else 80.0 + i % 5) }

    @Test
    fun `bucketStart is given and floors to the bucket, like time_bucket`() {
        assertThat(TimeSeries.bucketStart(Instant.parse("2026-11-07T09:43:07Z"), Duration.ofMinutes(5)))
            .isEqualTo(Instant.parse("2026-11-07T09:40:00Z"))
    }

    @Test
    fun `downsample makes one bucket per window with count, min, max and sum`() {
        val buckets = TimeSeries.downsample(points, Duration.ofMinutes(5))
        assertThat(buckets).hasSize(12)
        assertThat(buckets.map { it.start }).isSorted()
        assertThat(buckets.first().start).isEqualTo(t0)
        assertThat(buckets).allMatch { it.count == 30 }
        assertThat(buckets.first().min).isEqualTo(80.0)
        assertThat(buckets.first().max).isEqualTo(640.0)
        assertThat(buckets.sumOf { it.sum }).isCloseTo(points.sumOf { it.value }, within(1e-6))
    }

    @Test
    fun `empty windows are left out, and points arrive in any order`() {
        val sparse = listOf(
            Point(Instant.parse("2026-11-07T09:12:00Z"), 90.0),
            Point(Instant.parse("2026-11-07T09:01:00Z"), 100.0),
            Point(Instant.parse("2026-11-07T09:03:30Z"), 300.0),
        )
        val buckets = TimeSeries.downsample(sparse, Duration.ofMinutes(5))
        assertThat(buckets.map { it.start }).containsExactly(Instant.parse("2026-11-07T09:00:00Z"), Instant.parse("2026-11-07T09:10:00Z"))
        assertThat(buckets[0].avg).isEqualTo(200.0)
    }

    @Test
    fun `rolling 5-minute buckets up to an hour gives the same answer as downsampling the raw points`() {
        val fiveMinute = TimeSeries.downsample(points, Duration.ofMinutes(5))
        val hourly = TimeSeries.rollup(fiveMinute, Duration.ofHours(1))
        assertThat(hourly).hasSize(1)
        val direct = TimeSeries.downsample(points, Duration.ofHours(1)).single()
        assertThat(hourly.single().count).isEqualTo(direct.count)
        assertThat(hourly.single().min).isEqualTo(direct.min)
        assertThat(hourly.single().max).isEqualTo(direct.max)
        assertThat(hourly.single().avg).isCloseTo(direct.avg, within(1e-9))
    }

    @Test
    fun `rollup weights by count, so a busy window counts for more than a quiet one`() {
        val busy = Bucket(t0, count = 99, min = 80.0, max = 120.0, sum = 99 * 100.0)  // avg 100
        val quiet = Bucket(t0.plusSeconds(300), count = 1, min = 900.0, max = 900.0, sum = 900.0) // avg 900
        val hour = TimeSeries.rollup(listOf(quiet, busy), Duration.ofHours(1)).single()
        assertThat(hour.avg).isEqualTo(108.0) // the average of the two averages would be 500: wrong
        assertThat(hour.count).isEqualTo(100)
        assertThat(hour.max).isEqualTo(900.0)
    }

    @Test
    fun `retention is given and drops points before the cutoff`() {
        assertThat(TimeSeries.retain(points, t0.plusSeconds(3_000))).hasSize(60)
    }
}
