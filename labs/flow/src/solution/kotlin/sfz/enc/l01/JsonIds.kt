package sfz.enc.l01

import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.module.kotlin.readValue
import java.math.BigDecimal

object JsonIds {
    const val MAX_SAFE: Long = (1L shl 53) - 1

    fun isSafe(id: Long): Boolean = id in -MAX_SAFE..MAX_SAFE

    // BigDecimal(double) is the exact value of the double, so this comparison never rounds
    fun changedByDouble(id: Long): Boolean = BigDecimal(id.toDouble()).compareTo(BigDecimal(id)) != 0

    fun countChanged(ids: List<Long>): Int = ids.count { changedByDouble(it) }

    fun toJson(a: Authorization): String {
        val node = Formats.json.valueToTree<ObjectNode>(a)
        node.put("paymentId", a.paymentId.toString()) // a string survives every parser, digit for digit
        return Formats.json.writeValueAsString(node)
    }

    // Jackson coerces "1849204436731904017" to a Long, and reads a plain number as a Long too: both exact
    fun fromJson(text: String): Authorization = Formats.json.readValue(text)
}
