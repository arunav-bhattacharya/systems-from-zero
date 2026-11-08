package sfz.enc.l01

/**
 * JSON numbers and 64-bit ids. Many JSON parsers (JavaScript's `JSON.parse`, and any parser that maps
 * numbers to `Double`) keep a number as an IEEE 754 double, which has 53 bits of precision.
 */
object JsonIds {
    /** The largest integer that every JSON parser reads back exactly: 2^53 - 1 (RFC 8259, section 6). */
    const val MAX_SAFE: Long = (1L shl 53) - 1

    /**
     * True when [id] is in the interoperable range, -(2^53 - 1) to 2^53 - 1. Outside it, two different
     * integers can turn into the same double, so a reader can't trust what it got back.
     */
    fun isSafe(id: Long): Boolean {
        TODO("compare against MAX_SAFE in both directions")
    }

    /**
     * True when a reader that parses [id] as a double gets a different integer back.
     * Compare exactly: `java.math.BigDecimal(id.toDouble())` against `java.math.BigDecimal(id)`.
     */
    fun changedByDouble(id: Long): Boolean {
        TODO("convert to a double and back without rounding, then compare")
    }

    /** How many of [ids] a double-based parser would corrupt. */
    fun countChanged(ids: List<Long>): Int {
        TODO("count the ids for which changedByDouble is true")
    }

    /**
     * Encodes [a] as JSON with `paymentId` written as a decimal string, `"1849204436731904017"`,
     * the way the Protobuf JSON mapping writes every 64-bit integer. Every other field stays as it is.
     */
    fun toJson(a: Authorization): String {
        TODO("turn a into an ObjectNode with Formats.json.valueToTree, replace paymentId with its string, write it")
    }

    /**
     * Reads JSON written by [toJson] or by an older producer that still sends `paymentId` as a number.
     * Both must give back the exact id.
     */
    fun fromJson(text: String): Authorization {
        TODO("read it with Formats.json; Jackson accepts a string for a Long property by default")
    }
}
