package sfz.internals.l11

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

class ColumnChunkTest {
    @Test
    fun `run-length encoding stores each run once`() {
        val rle = RunLength.encode(longArrayOf(7, 7, 7, 2, 2, 9))
        assertThat(rle.values).containsExactly(7, 2, 9)
        assertThat(rle.lengths).containsExactly(3, 2, 1)
        assertThat(rle.count).isEqualTo(6)
        assertThat(rle.decode()).containsExactly(7, 7, 7, 2, 2, 9)
        assertThat(RunLength.encode(LongArray(0)).decode()).isEmpty()
        assertThat(RunLength.encode(longArrayOf(1, 2, 1)).values).`as`("runs are of neighbours only").containsExactly(1, 2, 1)
    }

    @Test
    fun `run-length shrinks a sorted status column more than ten times`() {
        // 100,000 payments sorted by status: 0 = authorized, 1 = captured, 2 = settled, 3 = refunded, 4 = failed
        val status = LongArray(100_000) { i -> if (i < 70_000) 2L else if (i < 90_000) 1L else if (i < 97_000) 0L else if (i < 99_000) 3L else 4L }
        val rle = RunLength.encode(status)
        assertThat(rle.values).hasSize(5)
        assertThat(rle.decode()).isEqualTo(status)
        assertThat(Plain(status).sizeBytes / rle.sizeBytes).`as`("compression ratio").isGreaterThan(10)
        assertThat(rle.sizeBytes).isEqualTo(60)
    }

    @Test
    fun `bit-packing round-trips every width from 1 to 64 bits`() {
        val rnd = Random(11)
        for (bits in 1..64) {
            for (count in listOf(2, 7, 64, 65, 200)) {
                val values = LongArray(count) { rnd.nextLong() ushr (64 - bits) }      // random values of at most `bits` bits
                values[0] = if (bits == 64) Long.MIN_VALUE else 0L                       // the smallest and largest possible,
                values[count - 1] = if (bits == 64) Long.MAX_VALUE else -1L ushr (64 - bits) // so the range needs every bit
                val packed = BitPacked.encode(values)
                assertThat(packed.bits).`as`("bits for width $bits").isEqualTo(bits)
                assertThat(packed.words).`as`("words for $count values of $bits bits").hasSize(((count.toLong() * bits + 63) / 64).toInt())
                assertThat(packed.decode()).`as`("$count values of $bits bits").isEqualTo(values)
            }
        }
    }

    @Test
    fun `bit-packing stores amounts under 100,000 cents in 17 bits each`() {
        val amounts = LongArray(1_000) { (it * 7_919L) % 100_000 }
        val packed = BitPacked.encode(amounts)
        assertThat(packed.base).isEqualTo(0)
        assertThat(packed.bits).isEqualTo(17)
        assertThat(packed.words).`as`("ceil(1,000 x 17 / 64)").hasSize(266)
        assertThat(packed.sizeBytes).isEqualTo(16 + 266 * 8)
        assertThat(Plain(amounts).sizeBytes).isEqualTo(8_000)
        assertThat(packed.decode()).isEqualTo(amounts)
    }

    @Test
    fun `frame of reference packs timestamps by their distance from the smallest`() {
        val hour = 1_793_700_000L                                    // seconds since 1970, some hour in November 2026
        val createdAt = LongArray(3_600) { hour + it }
        val packed = BitPacked.encode(createdAt)
        assertThat(packed.base).isEqualTo(hour)
        assertThat(packed.bits).`as`("0 to 3,599 fits in 12 bits").isEqualTo(12)
        assertThat(packed.decode()).isEqualTo(createdAt)
    }

    @Test
    fun `dictionary codes follow the sorted order of the strings`() {
        val d = Dictionary.encode(listOf("USD", "EUR", "USD", "GBP"))
        assertThat(d.values).containsExactly("EUR", "GBP", "USD")
        assertThat(d.codes).containsExactly(2, 0, 2, 1)
        assertThat(d.decode()).containsExactly("USD", "EUR", "USD", "GBP")

        val currencies = listOf("EUR", "GBP", "SEK", "USD")
        val column = List(10_000) { currencies[(it * 7) % 4] }
        val dict = Dictionary.encode(column)
        assertThat(dict.decode()).isEqualTo(column)
        for (i in 0 until 100) {
            val byString = column[i].compareTo(column[i + 1]).coerceIn(-1, 1)
            val byCode = dict.codes[i].compareTo(dict.codes[i + 1]).coerceIn(-1, 1)
            assertThat(byCode).`as`("codes compare like the strings").isEqualTo(byString)
        }
        assertThat(Dictionary.plainSize(column) / dict.sizeBytes).`as`("70,000 bytes of text against 2-bit codes").isGreaterThan(20)
    }

    @Test
    fun `a chunk keeps the smallest encoding and its min and max`() {
        val sorted = LongArray(2_048) { it / 512L }                      // 4 long runs
        val small = LongArray(2_048) { (it * 7_919L) % 100_000 }         // amounts: 17 bits
        val random = Random(3).let { r -> LongArray(2_048) { r.nextLong() } }
        assertThat(ColumnChunk.of(sorted).encoded).isInstanceOf(RunLength::class.java)
        assertThat(ColumnChunk.of(small).encoded).isInstanceOf(BitPacked::class.java)
        assertThat(ColumnChunk.of(random).encoded).`as`("nothing beats 64 bits for random longs").isInstanceOf(Plain::class.java)
        val c = ColumnChunk.of(longArrayOf(40, -3, 17, 99, 5))
        assertThat(c.min).isEqualTo(-3)
        assertThat(c.max).isEqualTo(99)
        assertThat(c.encoded.decode()).containsExactly(40, -3, 17, 99, 5)
    }

    /** 204,800 payments, one every 10 seconds, in insertion order: 100 chunks of 2,048, each about 5.7 hours. */
    private val start = 1_793_700_000L
    private val createdAt = LongArray(204_800) { start + 10L * it }

    @Test
    fun `zone maps skip the chunks outside the range`() {
        val col = Column.of(createdAt)
        assertThat(col.chunks).hasSize(100)
        val lo = start + 10L * 50_000                                  // one hour from the middle of the table
        val hi = lo + 3_599
        assertThat(col.countBetween(lo, hi)).isEqualTo(360)
        assertThat(col.chunksDecoded).`as`("chunks decoded for one hour").isLessThanOrEqualTo(2)
    }

    @Test
    fun `a chunk entirely inside the range is counted without decoding it`() {
        val col = Column.of(createdAt)
        val lo = col.chunks[10].min
        val hi = col.chunks[19].max
        assertThat(col.countBetween(lo, hi)).isEqualTo(10L * 2_048)
        assertThat(col.chunksDecoded).isZero()
    }

    @Test
    fun `on shuffled data the zone maps skip nothing`() {
        val shuffled = createdAt.copyOf().also { it.shuffle(Random(7)) }
        val col = Column.of(shuffled)
        val lo = start + 10L * 50_000
        assertThat(col.countBetween(lo, lo + 3_599)).isEqualTo(360)
        assertThat(col.chunksDecoded).`as`("every chunk spans almost the whole period").isEqualTo(100)
    }

    @Test
    fun `countBetween gives the same count as checking every value`() {
        val rnd = Random(5)
        val values = LongArray(50_000) { if (it % 3 == 0) it / 100L else rnd.nextLong(0, 1_000) }
        val col = Column.of(values, chunkRows = 1_000)
        assertThat(col.count).isEqualTo(50_000)
        repeat(50) {
            val a = rnd.nextLong(-10, 1_010)
            val b = rnd.nextLong(-10, 1_010)
            val lo = minOf(a, b)
            val hi = maxOf(a, b)
            assertThat(col.countBetween(lo, hi)).`as`("[$lo, $hi]").isEqualTo(values.count { it in lo..hi }.toLong())
        }
    }
}
