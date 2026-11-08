package sfz.enc.l02

import java.io.ByteArrayOutputStream

object ProtoCodec {
    const val VARINT = 0
    const val I64 = 1
    const val LEN = 2
    const val I32 = 5

    fun key(fieldNumber: Int, wireType: Int): Long = ((fieldNumber shl 3) or wireType).toLong()

    fun encode(a: Authorization): ByteArray {
        val out = ByteArrayOutputStream()
        fun varintField(field: Int, v: Long) {
            if (v == 0L) return                       // proto3: a zero is not written, so it costs nothing
            out.write(Varint.encode(key(field, VARINT)))
            out.write(Varint.encode(v))
        }
        fun stringField(field: Int, s: String) {
            val utf8 = s.toByteArray(Charsets.UTF_8)
            out.write(Varint.encode(key(field, LEN)))
            out.write(Varint.encode(utf8.size.toLong())) // the length tells a reader how far to skip
            out.write(utf8)
        }
        varintField(1, a.paymentId)
        if (a.merchant.isNotEmpty()) stringField(2, a.merchant)
        varintField(3, a.amountMinor)
        if (a.currency.isNotEmpty()) stringField(4, a.currency)
        a.tags.forEach { stringField(5, it) }        // repeated: one entry per element, even an empty one
        return out.toByteArray()
    }

    fun decode(bytes: ByteArray): Authorization {
        var paymentId = 0L
        var merchant = ""
        var amountMinor = 0L
        var currency = ""
        val tags = mutableListOf<String>()
        var i = 0
        while (i < bytes.size) {
            val k = Varint.decode(bytes, i)
            i = k.next
            val field = (k.value ushr 3).toInt()
            when ((k.value and 7).toInt()) {
                VARINT -> {
                    val v = Varint.decode(bytes, i)
                    i = v.next
                    when (field) {
                        1 -> paymentId = v.value
                        3 -> amountMinor = v.value
                        // any other field number: an unknown field, already skipped by reading it
                    }
                }
                LEN -> {
                    val len = Varint.decode(bytes, i)
                    val start = len.next
                    val end = start + len.value.toInt()
                    when (field) {
                        2 -> merchant = String(bytes, start, end - start, Charsets.UTF_8)
                        4 -> currency = String(bytes, start, end - start, Charsets.UTF_8)
                        5 -> tags += String(bytes, start, end - start, Charsets.UTF_8)
                    }
                    i = end                                  // the length lets us skip what we don't know
                }
                I64 -> i += 8
                I32 -> i += 4
                else -> throw IllegalArgumentException("unsupported wire type in key ${k.value} at offset $i")
            }
        }
        return Authorization(paymentId, merchant, amountMinor, currency, tags)
    }
}
