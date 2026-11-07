package sfz.bigdata.l02

/** One key/value pair, the only thing that flows between the phases of a MapReduce job. */
data class KV(val key: String, val value: Int)

/** The user code of a word count job: the three functions you would write for Hadoop. */
object WordCount {

    /**
     * Map: turn one line into `(word, 1)` pairs.
     *
     * A word is a run of the letters a to z after lowercasing the line. Everything else (spaces,
     * digits, commas, dashes) separates words. "Card DECLINED, card-present" gives
     * card, declined, card, present: four pairs, in the order they appear.
     */
    // the regex does the tokenizing; filter drops the empty strings that leading separators leave
    fun map(line: String): List<KV> =
        line.lowercase().split(NOT_A_LETTER).filter { it.isNotEmpty() }.map { KV(it, 1) }

    private val NOT_A_LETTER = Regex("[^a-z]+")

    /**
     * Combine: add up the values per key inside ONE map task's output, before it leaves the
     * machine. Returns one pair per distinct key, in any order.
     */
    // the same code as reduce, run early: legal because + is associative and commutative
    fun combine(pairs: List<KV>): List<KV> =
        pairs.groupingBy { it.key }.fold(0) { sum, kv -> sum + kv.value }.map { (k, v) -> KV(k, v) }

    /** Reduce: all values for one key arrive together. Sum them. */
    fun reduce(key: String, values: List<Int>): KV = KV(key, values.sum())
}

/**
 * Decides which reducer gets a key. This is Hadoop's default rule: take the key's `hashCode()`,
 * clear the sign bit so the number is never negative, and take it modulo the number of reducers.
 */
class HashPartitioner(val reducers: Int) {
    init {
        require(reducers > 0) { "need at least one reducer" }
    }

    /** A number in `0 until reducers`, the same one every time for the same key. */
    // Math.abs(Int.MIN_VALUE) is still negative, so clear the sign bit instead (Hadoop does the same)
    fun partition(key: String): Int = (key.hashCode() and Int.MAX_VALUE) % reducers
}

/** What the shuffle hands to the reducers, plus how much it moved over the network. */
data class ShuffleResult(
    /** `buckets[r]` is everything reducer `r` receives, sorted by key. */
    val buckets: List<List<KV>>,
    /** How many pairs crossed the network. */
    val records: Long,
    /** How many bytes those pairs took: each costs its key's UTF-8 length plus 4 bytes for the Int. */
    val bytes: Long,
)

object Shuffle {
    /**
     * The shuffle: send every pair from every map task to the bucket of the reducer that owns its
     * key, then sort each bucket by key so equal keys sit next to each other.
     *
     * [mapOutputs] has one list per map task. Count every pair you route as one record, and add its
     * size (UTF-8 key bytes + 4) to the byte total. The sort must be stable: pairs with the same key
     * keep their arrival order.
     */
    fun shuffle(mapOutputs: List<List<KV>>, partitioner: HashPartitioner): ShuffleResult {
        val buckets = List(partitioner.reducers) { mutableListOf<KV>() }
        var records = 0L
        var bytes = 0L
        for (taskOutput in mapOutputs) {
            for (kv in taskOutput) {
                // in Hadoop the map task writes this pair into partition r of a file on its local disk,
                // and reducer r fetches it later over the network
                buckets[partitioner.partition(kv.key)] += kv
                records++
                bytes += kv.key.toByteArray(Charsets.UTF_8).size + Int.SIZE_BYTES
            }
        }
        // sortedBy is stable; equal keys end up next to each other, ready for reduce
        return ShuffleResult(buckets.map { b -> b.sortedBy { it.key } }, records, bytes)
    }
}

/** The finished job: one sorted output list per reducer (like part-00000, part-00001, ...). */
data class JobResult(val output: List<List<KV>>, val shuffledRecords: Long, val shuffledBytes: Long) {
    /** All reducers' output merged into one map, for checking. */
    fun counts(): Map<String, Int> = output.flatten().associate { it.key to it.value }
}

/** Wires the phases together. You don't need to change this; it runs your functions above. */
object MapReduceJob {
    /**
     * Runs word count over [splits] (one list of lines per map task) with [reducers] reduce tasks.
     * With [useCombiner], each map task combines its own output before the shuffle.
     */
    fun run(splits: List<List<String>>, reducers: Int, useCombiner: Boolean): JobResult {
        // map phase: one map task per split; in Hadoop each would run on the machine holding that block
        val mapOutputs = splits.map { lines ->
            val pairs = lines.flatMap(WordCount::map)
            if (useCombiner) WordCount.combine(pairs) else pairs
        }
        // shuffle phase: partition, move over the network, sort
        val shuffled = Shuffle.shuffle(mapOutputs, HashPartitioner(reducers))
        // reduce phase: each reducer walks its sorted bucket one key at a time
        val output = shuffled.buckets.map { bucket ->
            val result = mutableListOf<KV>()
            var i = 0
            while (i < bucket.size) {
                val key = bucket[i].key
                val values = mutableListOf<Int>()
                while (i < bucket.size && bucket[i].key == key) values += bucket[i++].value
                result += WordCount.reduce(key, values)
            }
            result
        }
        return JobResult(output, shuffled.records, shuffled.bytes)
    }
}
