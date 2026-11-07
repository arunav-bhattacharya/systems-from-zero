package sfz.net.l11

sealed interface Frame {
    val streamId: Int

    data class Data(override val streamId: Int, val endStream: Boolean, val text: String) : Frame
    data class Headers(override val streamId: Int, val endStream: Boolean, val endHeaders: Boolean, val block: List<Int>) : Frame
    data class RstStream(override val streamId: Int, val errorCode: Long) : Frame
    data class Settings(val ack: Boolean, val values: List<Pair<Int, Long>>) : Frame {
        override val streamId: Int get() = 0
    }
    data class Ping(val ack: Boolean, val opaque: Long) : Frame {
        override val streamId: Int get() = 0
    }
    data class GoAway(val lastStreamId: Int, val errorCode: Long) : Frame {
        override val streamId: Int get() = 0
    }
    data class WindowUpdate(override val streamId: Int, val increment: Long) : Frame
    data class Other(val type: Int, val flags: Int, override val streamId: Int, val length: Int) : Frame
}

object Http2Codec {
    val PREFACE: ByteArray = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n".toByteArray(Charsets.US_ASCII)

    private const val END_STREAM = 0x1
    private const val ACK = 0x1
    private const val END_HEADERS = 0x4
    private const val PADDED = 0x8
    private const val PRIORITY = 0x20

    fun decode(bytes: ByteArray): List<Frame> {
        var at = if (bytes.size >= PREFACE.size && bytes.copyOf(PREFACE.size).contentEquals(PREFACE)) PREFACE.size else 0
        val frames = mutableListOf<Frame>()
        while (at < bytes.size) {
            require(bytes.size - at >= 9) { "a frame header is cut off at byte $at" }
            val length = (u8(bytes, at) shl 16) or (u8(bytes, at + 1) shl 8) or u8(bytes, at + 2)
            val type = u8(bytes, at + 3)
            val flags = u8(bytes, at + 4)
            val stream = (u32(bytes, at + 5) and 0x7FFF_FFFFL).toInt()           // the reserved bit is ignored
            val start = at + 9
            require(start + length <= bytes.size) { "frame at byte $at needs $length bytes of payload, ${bytes.size - start} left" }
            frames += frame(type, flags, stream, bytes.copyOfRange(start, start + length))
            at = start + length
        }
        return frames
    }

    private fun frame(type: Int, flags: Int, stream: Int, p: ByteArray): Frame = when (type) {
        0 -> {
            val body = unpad(p, flags, 0)
            Frame.Data(stream, flags and END_STREAM != 0, String(body, Charsets.ISO_8859_1))
        }
        1 -> {
            val body = unpad(p, flags, if (flags and PRIORITY != 0) 5 else 0)    // 5 bytes of priority to skip
            Frame.Headers(stream, flags and END_STREAM != 0, flags and END_HEADERS != 0, body.map { it.toInt() and 0xFF })
        }
        3 -> Frame.RstStream(stream, u32(p, 0))
        4 -> Frame.Settings(flags and ACK != 0, (0 until p.size / 6).map { i ->
            ((u8(p, 6 * i) shl 8) or u8(p, 6 * i + 1)) to u32(p, 6 * i + 2)
        })
        6 -> Frame.Ping(flags and ACK != 0, (u32(p, 0) shl 32) or u32(p, 4))
        7 -> Frame.GoAway((u32(p, 0) and 0x7FFF_FFFFL).toInt(), u32(p, 4))
        8 -> Frame.WindowUpdate(stream, u32(p, 0) and 0x7FFF_FFFFL)
        else -> Frame.Other(type, flags, stream, p.size)
    }

    /** With PADDED, the first byte is the pad length and that many bytes at the end are padding. */
    private fun unpad(p: ByteArray, flags: Int, skip: Int): ByteArray {
        if (flags and PADDED == 0) return p.copyOfRange(skip, p.size)
        val pad = u8(p, 0)
        return p.copyOfRange(1 + skip, p.size - pad)
    }

    fun header(length: Int, type: Int, flags: Int, streamId: Int): ByteArray = byteArrayOf(
        (length ushr 16).toByte(), (length ushr 8).toByte(), length.toByte(),
        type.toByte(), flags.toByte(),
        ((streamId ushr 24) and 0x7F).toByte(), (streamId ushr 16).toByte(), (streamId ushr 8).toByte(), streamId.toByte(),
    )

    private fun u8(b: ByteArray, i: Int) = b[i].toInt() and 0xFF
    private fun u32(b: ByteArray, i: Int): Long =
        ((u8(b, i).toLong() shl 24) or (u8(b, i + 1).toLong() shl 16) or (u8(b, i + 2).toLong() shl 8) or u8(b, i + 3).toLong())
}
