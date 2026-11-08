package sfz.enc.l02

import java.io.ByteArrayOutputStream

data class Decoded(val value: Long, val next: Int)

object Varint {
    fun encode(value: Long): ByteArray {
        val out = ByteArrayOutputStream()
        var v = value
        while (v ushr 7 != 0L) {             // ushr: treat the Long as unsigned, so -1 takes 10 bytes
            out.write(((v and 0x7f) or 0x80).toInt()) // 7 bits of payload, top bit = "more follows"
            v = v ushr 7
        }
        out.write(v.toInt())                  // the last byte has its top bit clear
        return out.toByteArray()
    }

    fun decode(bytes: ByteArray, offset: Int = 0): Decoded {
        var result = 0L
        var shift = 0
        var i = offset
        while (true) {
            require(shift < 64) { "varint longer than 10 bytes at offset $offset" }
            val b = bytes[i++].toInt() and 0xff
            result = result or ((b and 0x7f).toLong() shl shift) // lowest group first
            if (b and 0x80 == 0) return Decoded(result, i)
            shift += 7
        }
    }

    // (n shl 1) moves the magnitude up; (n shr 63) is all ones for negatives, all zeros otherwise
    fun zigzag(n: Long): Long = (n shl 1) xor (n shr 63)
}
