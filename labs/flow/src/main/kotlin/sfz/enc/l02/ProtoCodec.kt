package sfz.enc.l02

/**
 * The Protobuf wire format for [Authorization], by hand. The bytes must equal what protobuf-java
 * writes for the same message (the tests compare them).
 *
 * Every field is a key, then a value. The key is a varint: `(fieldNumber shl 3) or wireType`.
 * This message uses two wire types: VARINT for int64, and LEN (a varint byte count, then the bytes)
 * for strings. A repeated field is the same key and value once per element.
 */
object ProtoCodec {
    const val VARINT = 0
    const val I64 = 1
    const val LEN = 2
    const val I32 = 5

    /** The key for [fieldNumber] with [wireType]: field 1 as VARINT is 0x08, field 2 as LEN is 0x12. */
    fun key(fieldNumber: Int, wireType: Int): Long {
        TODO("field number in the high bits, wire type in the low 3 bits")
    }

    /**
     * Writes fields 1 to 5 in field-number order, as proto3 does:
     * - like proto3, a field whose value is 0 or an empty string is not written at all;
     * - each tag in [Authorization.tags] is its own field 5 entry, in list order.
     */
    fun encode(a: Authorization): ByteArray {
        TODO("for each field: Varint.encode(key), then the varint, or the length and the UTF-8 bytes")
    }

    /**
     * Reads bytes written by any version of the schema. Fields 1 to 5 fill the record. A field it doesn't
     * know (a new field number, or a known number with an unexpected wire type) is skipped: read its
     * varint, or skip `length` bytes for LEN, 8 bytes for I64, 4 bytes for I32. A field that isn't there
     * keeps its default: 0, "" or an empty list.
     */
    fun decode(bytes: ByteArray): Authorization {
        TODO("loop: read a key, split it into field number and wire type, read or skip the value")
    }
}
