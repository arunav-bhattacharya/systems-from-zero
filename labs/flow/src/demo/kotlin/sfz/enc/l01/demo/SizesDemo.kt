package sfz.enc.l01.demo

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.dataformat.cbor.databind.CBORMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import org.msgpack.jackson.dataformat.MessagePackMapper
import java.io.ByteArrayOutputStream
import java.io.ObjectOutputStream
import java.io.Serializable

/** The lesson's record, copied here so the demo runs on its own. */
data class Authorization(
    val paymentId: Long,
    val merchant: String,
    val amountMinor: Long,
    val currency: String,
    val tags: List<String>,
) : Serializable

/** Encodes one authorization in five ways and prints the size and the first bytes of each. */
fun main() {
    val auth = Authorization(1849204436731904017, "Fern Bakery", 4000, "EUR", listOf("card", "3ds"))
    val json: ObjectMapper = jacksonObjectMapper()
    val cbor: ObjectMapper = CBORMapper().registerKotlinModule()
    val msgpack: ObjectMapper = MessagePackMapper().registerKotlinModule()

    println(json.writeValueAsString(auth))
    println()
    show("JSON", json.writeValueAsBytes(auth))
    show("CBOR", cbor.writeValueAsBytes(auth))
    show("MessagePack", msgpack.writeValueAsBytes(auth))
    show("Java serialization", ByteArrayOutputStream().also { ObjectOutputStream(it).use { o -> o.writeObject(auth) } }.toByteArray())

    // the same five values with no field names, as an array
    val values = listOf(auth.paymentId, auth.merchant, auth.amountMinor, auth.currency, auth.tags)
    println()
    show("JSON, no names", json.writeValueAsBytes(values))
    show("MessagePack, no names", msgpack.writeValueAsBytes(values))
}

fun show(label: String, bytes: ByteArray) {
    val hex = bytes.take(16).joinToString(" ") { "%02x".format(it) }
    println("%-22s %4d bytes   %s ...".format(label, bytes.size, hex))
}
