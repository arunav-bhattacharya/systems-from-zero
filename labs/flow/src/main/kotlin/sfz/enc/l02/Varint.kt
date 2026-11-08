package sfz.enc.l02

/** One decoded varint: its [value], and [next], the offset of the first byte after it. */
data class Decoded(val value: Long, val next: Int)

/**
 * Protobuf's base-128 varints. Each byte carries 7 bits of the number, lowest 7 bits first.
 * The top bit of a byte is 1 when more bytes follow and 0 on the last byte.
 * 1 -> `01`, 150 -> `96 01`, 4000 -> `a0 1f`.
 */
object Varint {
    /**
     * Encodes [value] as an unsigned 64-bit number. A negative Long has its top bit set,
     * so it takes the full 10 bytes: -1 -> `ff ff ff ff ff ff ff ff ff 01`.
     */
    fun encode(value: Long): ByteArray {
        TODO("emit the low 7 bits with the top bit set while more remain (value ushr 7 != 0), then the last 7 bits")
    }

    /** Decodes one varint that starts at [offset] in [bytes]. */
    fun decode(bytes: ByteArray, offset: Int = 0): Decoded {
        TODO("add (byte and 0x7f) shl shift for each byte until one has its top bit clear")
    }

    /**
     * ZigZag, what `sint64` does before the varint: 0 -> 0, -1 -> 1, 1 -> 2, -2 -> 3, 2 -> 4.
     * Small negative numbers become small positive ones, so they take one byte instead of ten.
     */
    fun zigzag(n: Long): Long {
        TODO("shift left by one, xor with the sign spread over all 64 bits")
    }
}
