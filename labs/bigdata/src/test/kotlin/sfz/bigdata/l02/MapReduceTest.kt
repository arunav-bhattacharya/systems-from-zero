package sfz.bigdata.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.bigdata.support.TestData

class MapReduceTest {
    // 40 map tasks of 500 lines each, from a skewed vocabulary like real text
    private val splits = TestData.corpus(20_000).chunked(500)

    // the answer, computed the boring single-machine way
    private val expected: Map<String, Int> = splits.flatten()
        .flatMap { it.lowercase().split(Regex("[^a-z]+")) }
        .filter { it.isNotEmpty() }
        .groupingBy { it }.eachCount()

    @Test
    fun `map lowercases and splits on everything that is not a letter`() {
        assertThat(WordCount.map("Card DECLINED, card-present 3DS"))
            .containsExactly(KV("card", 1), KV("declined", 1), KV("card", 1), KV("present", 1), KV("ds", 1))
        assertThat(WordCount.map("  ,,  42 ")).isEmpty()
    }

    @Test
    fun `combine sums each key once within one map task`() {
        val combined = WordCount.combine(listOf(KV("approved", 1), KV("declined", 1), KV("approved", 1), KV("approved", 1)))
        assertThat(combined).containsExactlyInAnyOrder(KV("approved", 3), KV("declined", 1))
    }

    @Test
    fun `reduce adds up every value for its key`() {
        assertThat(WordCount.reduce("approved", listOf(2, 2, 1))).isEqualTo(KV("approved", 5))
    }

    @Test
    fun `the partitioner always sends a key to the same reducer, even for a negative hashCode`() {
        val p = HashPartitioner(3)
        assertThat(p.partition("approved")).isEqualTo(1)
        assertThat(p.partition("declined")).isEqualTo(0)
        assertThat(p.partition("refunded")).isEqualTo(2)       // hashCode is negative
        // this word's hashCode is Int.MIN_VALUE, and Math.abs(Int.MIN_VALUE) is still negative
        assertThat("polygenelubricants".hashCode()).isEqualTo(Int.MIN_VALUE)
        assertThat(p.partition("polygenelubricants")).isBetween(0, 2)
    }

    @Test
    fun `the partitioner spreads many keys roughly evenly`() {
        val p = HashPartitioner(4)
        val perReducer = TestData.vocabulary(10_000).groupingBy { p.partition(it) }.eachCount()
        assertThat(perReducer.keys).containsExactlyInAnyOrder(0, 1, 2, 3)
        assertThat(perReducer.values).allSatisfy { assertThat(it).isBetween(2_000, 3_000) }
    }

    @Test
    fun `the shuffle routes, sorts and counts what it moves`() {
        val p = HashPartitioner(3)
        val result = Shuffle.shuffle(
            listOf(
                listOf(KV("approved", 1), KV("declined", 1), KV("approved", 1)),
                listOf(KV("refunded", 1), KV("approved", 1)),
            ),
            p,
        )
        assertThat(result.buckets).hasSize(3)
        assertThat(result.buckets[0]).containsExactly(KV("declined", 1))
        assertThat(result.buckets[1]).containsExactly(KV("approved", 1), KV("approved", 1), KV("approved", 1))
        assertThat(result.buckets[2]).containsExactly(KV("refunded", 1))
        assertThat(result.records).isEqualTo(5)
        // 3 x "approved" + "declined" + "refunded": 5 keys of 8 bytes, plus 4 bytes per Int
        assertThat(result.bytes).isEqualTo(5L * (8 + 4))
    }

    @Test
    fun `every key lands in exactly one bucket, and each bucket is sorted`() {
        val result = Shuffle.shuffle(splits.map { s -> s.flatMap(WordCount::map) }, HashPartitioner(4))
        val keysPerBucket = result.buckets.map { b -> b.map { it.key }.toSet() }
        for (i in keysPerBucket.indices) for (j in i + 1 until keysPerBucket.size) {
            assertThat(keysPerBucket[i]).doesNotContainAnyElementsOf(keysPerBucket[j])
        }
        result.buckets.forEach { b -> assertThat(b.map { it.key }).isSorted() }
    }

    @Test
    fun `the job counts words exactly like a single-machine groupBy`() {
        val result = MapReduceJob.run(splits, reducers = 4, useCombiner = false)
        assertThat(result.counts()).isEqualTo(expected)
        assertThat(result.shuffledRecords).isEqualTo(expected.values.sumOf { it.toLong() })
    }

    @Test
    fun `a combiner gives the same answer and shuffles under a quarter of the bytes`() {
        val plain = MapReduceJob.run(splits, reducers = 4, useCombiner = false)
        val combined = MapReduceJob.run(splits, reducers = 4, useCombiner = true)
        assertThat(combined.counts()).isEqualTo(plain.counts())
        assertThat(combined.shuffledBytes).isLessThan(plain.shuffledBytes / 4)
        // with a combiner, each map task sends each distinct word once
        val distinctPerTask = splits.sumOf { s -> s.flatMap(WordCount::map).map { it.key }.toSet().size.toLong() }
        assertThat(combined.shuffledRecords).isEqualTo(distinctPerTask)
    }
}
