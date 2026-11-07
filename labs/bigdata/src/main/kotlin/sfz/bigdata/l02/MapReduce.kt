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
    fun map(line: String): List<KV> {
        TODO("lowercase, split on anything that is not a to z, drop empty strings, emit KV(word, 1)")
    }

    /**
     * Combine: add up the values per key inside ONE map task's output, before it leaves the
     * machine. Returns one pair per distinct key, in any order.
     */
    fun combine(pairs: List<KV>): List<KV> {
        TODO("group by key and sum the values")
    }

    /** Reduce: all values for one key arrive together. Sum them. */
    fun reduce(key: String, values: List<Int>): KV {
        TODO("KV(key, sum of values)")
    }
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
    fun partition(key: String): Int {
        TODO("(hashCode with the sign bit cleared) % reducers; Math.abs is not enough")
    }
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
        TODO("route each pair to buckets[partitioner.partition(key)], count records and bytes, sort each bucket by key")
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
