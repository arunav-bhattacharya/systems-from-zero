package sfz.enc.l01

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.dataformat.cbor.databind.CBORMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import org.msgpack.jackson.dataformat.MessagePackMapper

/** The four encodings the lesson compares. */
enum class Format { JSON, CBOR, MESSAGEPACK, JAVA }

object Formats {
    /** Text JSON. */
    val json: ObjectMapper = jacksonObjectMapper()

    /** CBOR (RFC 8949): JSON's data model in binary. */
    val cbor: ObjectMapper = CBORMapper().registerKotlinModule()

    /** MessagePack: another binary JSON. */
    val messagePack: ObjectMapper = MessagePackMapper().registerKotlinModule()

    /**
     * Encodes [value] in [format] and returns the bytes.
     *
     * - JSON, CBOR and MESSAGEPACK: use the matching mapper above (`writeValueAsBytes`).
     * - JAVA: Java's built-in serialization, an `ObjectOutputStream` over a `ByteArrayOutputStream`.
     */
    fun encode(value: Any, format: Format): ByteArray {
        TODO("one branch per format: three mappers and one ObjectOutputStream")
    }

    /**
     * The values of [a] in field order, with no names:
     * `[paymentId, merchant, amountMinor, currency, tags]`.
     * Encoding this list instead of the object shows how many bytes the field names cost.
     */
    fun positional(a: Authorization): List<Any> {
        TODO("return the five values as a list, in the order the class declares them")
    }
}
