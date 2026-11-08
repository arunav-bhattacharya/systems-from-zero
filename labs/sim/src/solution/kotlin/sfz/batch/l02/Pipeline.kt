package sfz.batch.l02

// The stages of `awk '{print $7}' access.log | sort | uniq -c | sort -rn | head -5`, as Kotlin functions.

/** One output line of `uniq -c`: a key and how many times it appeared in a row. */
data class KeyCount(val key: String, val count: Long)

/**
 * awk's `$n`: the [n]-th field of [line] (1-based), where fields are separated by runs of spaces or
 * tabs, as in awk's default field splitting. Returns null when the line has fewer than n fields.
 */
fun field(line: String, n: Int): String? {
    require(n >= 1) { "fields are numbered from 1, got $n" }
    // awk skips leading blanks and treats any run of blanks as one separator
    return line.split(' ', '\t').filter { it.isNotEmpty() }.getOrNull(n - 1)
}

/**
 * `uniq -c`: walks [keys] once and counts each run of equal neighbouring keys. It remembers only the
 * current key and its count, so it needs no memory for the keys it has finished. On unsorted input a
 * key that comes back later starts a new run and appears twice in the output.
 */
fun countAdjacent(keys: Sequence<String>): List<KeyCount> {
    val out = mutableListOf<KeyCount>()
    var current: String? = null
    var count = 0L
    for (key in keys) {
        if (key == current) {
            count++
        } else {
            if (current != null) out += KeyCount(current, count)    // the run before this key is over
            current = key
            count = 1
        }
    }
    if (current != null) out += KeyCount(current, count)            // the last run
    return out
}

/** Finished. `sort -rn | head -n [n]`: the [n] largest counts, largest first; equal counts in key order. */
fun topN(counts: Iterable<KeyCount>, n: Int): List<KeyCount> =
    counts.sortedWith(compareByDescending<KeyCount> { it.count }.thenBy { it.key }).take(n)
