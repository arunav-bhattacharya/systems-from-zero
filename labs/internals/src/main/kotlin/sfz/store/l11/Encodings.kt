package sfz.store.l11

// Lesson 11 lab, part 1: three lightweight encodings for one column chunk.
// Your job: RunLength.encode() and decode(), BitPacked.encode() and decode(), and Dictionary.encode().
// Plain, bitsFor() and every sizeBytes formula are done.

/**
 * A column chunk's values in some encoding. [sizeBytes] is what the encoded form would take on disk in the
 * lab's simple format; [decode] gives back exactly the values that went in, in order.
 */
sealed interface Encoded {
    val count: Int
    val sizeBytes: Int
    fun decode(): LongArray
}

/** No encoding: every value as a full 8-byte long. */
class Plain(private val values: LongArray) : Encoded {
    override val count: Int get() = values.size
    override val sizeBytes: Int get() = 8 * values.size
    override fun decode(): LongArray = values.copyOf()
}

/**
 * Run-length encoding: each run of equal neighbours is stored once, as its value and its length.
 * `[7, 7, 7, 2, 2, 9]` becomes values `[7, 2, 9]` and lengths `[3, 2, 1]`. A run costs 12 bytes
 * (an 8-byte value and a 4-byte length), so this wins when runs are long: a sorted column, or a column
 * with few distinct values in long stretches.
 */
class RunLength(val values: LongArray, val lengths: IntArray) : Encoded {
    init {
        require(values.size == lengths.size) { "one length per run" }
    }

    override val count: Int get() = lengths.sum()
    override val sizeBytes: Int get() = 12 * values.size

    /** Writes each run's value [lengths] times, in order. */
    override fun decode(): LongArray {
        TODO("write each run's value lengths[r] times into a LongArray of size count, in order")
    }

    companion object {
        /** Splits [input] into runs of equal neighbours. An empty input gives zero runs. */
        fun encode(input: LongArray): RunLength {
            TODO("walk input; extend the last run while the value repeats, else start a new run of length 1")
        }
    }
}

/** The fewest bits that hold every value from 0 to [maxValue], read as unsigned. At least 1, at most 64. */
fun bitsFor(maxValue: Long): Int = if (maxValue == 0L) 1 else 64 - java.lang.Long.numberOfLeadingZeros(maxValue)

/**
 * Frame of reference plus bit-packing. Subtract the chunk's smallest value, [base], from every value, so the
 * numbers start at 0; then store each one in [bits] bits, the fewest that hold the largest, packed back to
 * back into 64-bit [words]. Amounts below 100,000 cents need 17 bits instead of 64; timestamps from one hour
 * need 12 bits once the hour's first second is subtracted.
 *
 * Value `i` occupies bits `i * bits` to `i * bits + bits - 1` of the packed stream. Bit `p` of the stream is
 * bit `p % 64` of `words[p / 64]`, so a value can start near the end of one word and spill into the next.
 * The header (base, bits, count) costs 16 bytes, each word 8.
 */
class BitPacked(val base: Long, val bits: Int, val words: LongArray, override val count: Int) : Encoded {
    init {
        require(bits in 1..64) { "1 to 64 bits per value" }
    }

    override val sizeBytes: Int get() = 16 + 8 * words.size

    /** Reads [count] values of [bits] bits each back out of [words] and adds [base] to each. */
    override fun decode(): LongArray {
        TODO("for value i: pos = i * bits (as Long), word = pos / 64, offset = pos % 64; x = words[word] ushr offset, OR in words[word + 1] shl (64 - offset) if offset + bits > 64; mask to bits; add base")
    }

    companion object {
        /**
         * base = the smallest value, bits = bitsFor(largest - smallest), words = ceil(count * bits / 64) longs,
         * then OR each `value - base` into place. An empty input packs to base 0, 1 bit, no words.
         */
        fun encode(values: LongArray): BitPacked {
            TODO("empty: BitPacked(0, 1, LongArray(0), 0); else base = min, bits = bitsFor(max - base), words = LongArray(ceil(count * bits / 64)); OR (v - base) shl offset into words[pos / 64], and the spill, (v - base) ushr (64 - offset), into the next word")
        }
    }
}

/**
 * Dictionary encoding for a text column: the distinct strings once, sorted, in [values], and for each row
 * the position of its string in that list, its code, in [codes]. `["USD", "EUR", "USD", "GBP"]` becomes
 * values `["EUR", "GBP", "USD"]` and codes `[2, 0, 2, 1]`. Because the dictionary is sorted, comparing codes
 * gives the same answer as comparing the strings, so a filter like `currency < 'GBP'` can run on the codes.
 * The codes are small numbers, so they bit-pack or run-length encode well.
 */
class Dictionary(val values: List<String>, val codes: LongArray) {
    fun decode(): List<String> = codes.map { values[it.toInt()] }

    /** Each dictionary string with a 4-byte length, plus the codes in their best encoding. */
    val sizeBytes: Int get() = values.sumOf { 4 + it.toByteArray().size } + ColumnChunk.of(codes).encoded.sizeBytes

    companion object {
        /** Sorted distinct strings, then each row's index into them. */
        fun encode(strings: List<String>): Dictionary {
            TODO("values = the distinct strings, sorted; codes[i] = position of strings[i] in values (a HashMap from string to code keeps it fast)")
        }

        /** What the same strings take with no encoding: each one with a 4-byte length, as Parquet's PLAIN stores text. */
        fun plainSize(strings: List<String>): Int = strings.sumOf { 4 + it.toByteArray().size }
    }
}
