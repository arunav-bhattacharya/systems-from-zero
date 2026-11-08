package sfz.repl.l05

/**
 * One write to the replicated key: merchant M-0042's set of open authorization holds.
 *
 * Every write is a read-modify-write: a client read the holds, added one, and wrote the whole set
 * back to its own region's leader.
 *
 * - [id] is unique, like `eu:3`: the third write that region `eu` accepted.
 * - [timestamp] is the writing region's clock in milliseconds. A region's clock can be wrong.
 * - [seen] holds the ids of every write the writing region knew about when it accepted this one:
 *   everything this write's client could have read. It never contains [id] itself.
 */
data class Write(
    val id: String,
    val region: String,
    val holds: Set<String>,
    val timestamp: Long,
    val seen: Set<String>,
)

/** How one write relates to another. */
enum class Order {
    /** The first write happened before the second: the second one's writer had seen it. */
    BEFORE,

    /** The first write happened after the second: its writer had seen the second one. */
    AFTER,

    /** The same write (the same id), for example a message delivered twice. */
    SAME,

    /** Neither writer had seen the other's write, however far apart their clocks say they were. */
    CONCURRENT,
}

/**
 * Last write wins: return the write with the higher [Write.timestamp]. On a tie, the write whose
 * [Write.region] name is greater wins (`"us" > "eu"`), so every region picks the same winner.
 */
fun lastWriteWins(a: Write, b: Write): Write {
    TODO("compare timestamps; on a tie compare region names")
}

/**
 * How [a] relates to [b], decided only by what each writer had seen (never by timestamps):
 * SAME if the ids are equal, BEFORE if b's writer had seen a, AFTER if a's writer had seen b,
 * CONCURRENT otherwise.
 */
fun order(a: Write, b: Write): Order {
    TODO("look for a.id in b.seen and b.id in a.seen")
}

/** What [applyDetecting] did: the versions now kept for the key, and whether it found a conflict. */
data class Applied(val versions: List<Write>, val conflict: Boolean)

/**
 * The conflict detector. A region keeps a list of [current] versions of the key: one normally,
 * several siblings after a conflict. [incoming] has just arrived from another region.
 *
 * 1. If [incoming] is SAME as, or BEFORE, any current version, it's a repeat or an old message that
 *    a newer version already includes: return [current] unchanged, with no conflict.
 * 2. Otherwise drop every current version that is BEFORE [incoming] (its writer saw them), keep the
 *    ones CONCURRENT with it, and add [incoming] at the end.
 * 3. [Applied.conflict] is true when at least one concurrent version was kept next to [incoming].
 */
fun applyDetecting(current: List<Write>, incoming: Write): Applied {
    TODO("ignore old or repeated writes; replace what incoming saw; keep concurrent ones as siblings")
}
