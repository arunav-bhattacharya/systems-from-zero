package sfz.model.l02

/**
 * A primary key or a secondary index, described only by its key.
 *
 * [partitionKey] decides which partition (which machine) holds an item. The store hashes it,
 * so a query must give EVERY partition key attribute with `=` to find the partition.
 * [sortKey] orders the items inside one partition, attribute by attribute, left to right.
 *
 * DynamoDB calls these the partition key and sort key; Cassandra calls them the partition key
 * and clustering columns. The rules below are the same in both.
 */
data class KeyIndex(val name: String, val partitionKey: List<String>, val sortKey: List<String> = emptyList())

/**
 * One access pattern, written as the query the application will send.
 *
 * @param equals attributes the query fixes with `=` (for example `accountId = 'A-1001'`)
 * @param range at most one attribute the query asks a range of: `<`, `>`, `BETWEEN`, `begins_with`
 * @param orderBy the attribute the results must come back sorted by (either direction), or null
 */
data class AccessPattern(
    val name: String,
    val equals: Set<String>,
    val range: String? = null,
    val orderBy: String? = null,
)

/** How a store answers a query, cheapest first. */
enum class ReadKind {
    /**
     * Every key attribute is fixed with `=`: on the table, one item, found without reading any other.
     * (On a DynamoDB secondary index it is an exact-key Query; index keys need not be unique.)
     */
    KEY_LOOKUP,

    /** One partition, one contiguous slice of its sorted items. Cost grows with the items returned. */
    RANGE_READ,

    /**
     * The key can't pick out the answer: the store reads items and throws some away. At best that is
     * one whole partition plus a filter; at worst every partition of the table.
     */
    SCAN,
}

/** The answer for one access pattern: how it is read, and through which index (null for a scan). */
data class Verdict(val pattern: String, val kind: ReadKind, val index: String?)

object AccessPatternChecker {
    /**
     * How [index] can answer [pattern].
     *
     * Rules (these are DynamoDB's and Cassandra's rules for a query without filtering):
     * 1. Every attribute of the partition key must be in `equals`. Otherwise: [ReadKind.SCAN].
     * 2. Walk the sort key left to right. The attributes fixed with `=` must form a PREFIX of it:
     *    you can't skip one and fix a later one.
     * 3. Every attribute in `equals` must be part of the partition key or of that prefix. An `=` on
     *    any other attribute is a filter, which reads and throws away: [ReadKind.SCAN].
     * 4. `range` and `orderBy`, when given, must both be the sort key attribute right after the
     *    prefix. Anything else: [ReadKind.SCAN].
     * 5. If the whole key (partition key and every sort key attribute) is fixed with `=` and there
     *    is no range: [ReadKind.KEY_LOOKUP]. Otherwise: [ReadKind.RANGE_READ].
     */
    fun classify(pattern: AccessPattern, index: KeyIndex): ReadKind {
        TODO("apply rules 1 to 5")
    }

    /**
     * The cheapest way to answer [pattern] with any of [indexes]: a lookup beats a range read,
     * which beats a scan. Ties go to the index listed first. Given.
     */
    fun check(pattern: AccessPattern, indexes: List<KeyIndex>): Verdict {
        val best = indexes.minByOrNull { classify(pattern, it).ordinal }
        val kind = best?.let { classify(pattern, it) } ?: ReadKind.SCAN
        return Verdict(pattern.name, kind, if (kind == ReadKind.SCAN) null else best?.name)
    }

    /** [check] for every pattern, in order. Given. */
    fun checkAll(patterns: List<AccessPattern>, indexes: List<KeyIndex>): List<Verdict> =
        patterns.map { check(it, indexes) }
}
