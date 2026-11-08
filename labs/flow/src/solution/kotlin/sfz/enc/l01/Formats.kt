package sfz.enc.l01

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.dataformat.cbor.databind.CBORMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import org.msgpack.jackson.dataformat.MessagePackMapper
import java.io.ByteArrayOutputStream
import java.io.ObjectOutputStream

enum class Format { JSON, CBOR, MESSAGEPACK, JAVA }

object Formats {
    val json: ObjectMapper = jacksonObjectMapper()
    val cbor: ObjectMapper = CBORMapper().registerKotlinModule()
    val messagePack: ObjectMapper = MessagePackMapper().registerKotlinModule()

    fun encode(value: Any, format: Format): ByteArray = when (format) {
        Format.JSON -> json.writeValueAsBytes(value)
        Format.CBOR -> cbor.writeValueAsBytes(value)
        Format.MESSAGEPACK -> messagePack.writeValueAsBytes(value)
        Format.JAVA -> {
            // Java serialization writes a header, the class name, every field's name and type, then the values
            val out = ByteArrayOutputStream()
            ObjectOutputStream(out).use { it.writeObject(value) }
            out.toByteArray()
        }
    }

    // the same values without their names: what a schema-based format sends
    fun positional(a: Authorization): List<Any> = listOf(a.paymentId, a.merchant, a.amountMinor, a.currency, a.tags)
}
