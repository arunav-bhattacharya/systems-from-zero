package sfz.enc.l01.demo

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import java.math.BigDecimal

/** What happens to a 64-bit id when a JSON reader keeps numbers as doubles. */
fun main() {
    val mapper = jacksonObjectMapper()
    val json = """{"paymentId":1849204436731904017,"amountMinor":4000}"""
    println("sent:              $json")

    val node = mapper.readTree(json).get("paymentId")
    println("read as a Long:    ${node.longValue()}")
    // a double has 53 bits for the digits; JavaScript's JSON.parse does exactly this
    println("read as a double:  ${BigDecimal(node.asDouble()).toPlainString()}")

    val twoTo53 = 1L shl 53
    for (id in listOf(twoTo53 - 1, twoTo53, twoTo53 + 1, twoTo53 + 2)) {
        println("%d -> as a double -> %s".format(id, BigDecimal(id.toDouble()).toPlainString()))
    }

    // the fix: send the id as a string
    val fixed = """{"paymentId":"1849204436731904017","amountMinor":4000}"""
    println("as a string:       ${mapper.readTree(fixed).get("paymentId").asText()}")
}
