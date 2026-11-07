package sfz.net.l11

/**
 * One HTTP/2 frame, decoded. Every frame starts with the same 9-byte header (RFC 9113, section 4.1):
 * ```
 * length (24 bits)  type (8)  flags (8)  R (1 bit, ignore it) + stream id (31 bits)
 * ```
 * then `length` bytes of payload. Stream 0 is the connection itself (SETTINGS, PING, GOAWAY and the
 * connection's WINDOW_UPDATE); requests use odd stream ids picked by the client: 1, 3, 5...
 */
sealed interface Frame {
    val streamId: Int

    /** Type 0. Flags: END_STREAM 0x1, PADDED 0x8. [text] is the payload without padding, one char per byte. */
    data class Data(override val streamId: Int, val endStream: Boolean, val text: String) : Frame

    /**
     * Type 1. Flags: END_STREAM 0x1, END_HEADERS 0x4, PADDED 0x8, PRIORITY 0x20. [block] is the
     * HPACK-compressed header block as unsigned bytes, without padding or priority fields.
     */
    data class Headers(override val streamId: Int, val endStream: Boolean, val endHeaders: Boolean, val block: List<Int>) : Frame

    /** Type 3: the sender cancels one stream. Payload: a 32-bit error code. */
    data class RstStream(override val streamId: Int, val errorCode: Long) : Frame

    /** Type 4, always on stream 0. Flag ACK 0x1. Payload: 6 bytes per setting, a 16-bit id and a 32-bit value. */
    data class Settings(val ack: Boolean, val values: List<Pair<Int, Long>>) : Frame {
        override val streamId: Int get() = 0
    }

    /** Type 6, stream 0. Flag ACK 0x1. Payload: 8 opaque bytes, which the answer echoes. */
    data class Ping(val ack: Boolean, val opaque: Long) : Frame {
        override val streamId: Int get() = 0
    }

    /** Type 7, stream 0: the sender is closing. Payload: last stream id (31 bits), error code (32 bits). */
    data class GoAway(val lastStreamId: Int, val errorCode: Long) : Frame {
        override val streamId: Int get() = 0
    }

    /** Type 8. Payload: a 31-bit window increment, for one stream or (on stream 0) the whole connection. */
    data class WindowUpdate(override val streamId: Int, val increment: Long) : Frame

    /** Any other type (PRIORITY, PUSH_PROMISE, CONTINUATION, or one invented later): kept but not decoded. */
    data class Other(val type: Int, val flags: Int, override val streamId: Int, val length: Int) : Frame
}

object Http2Codec {
    /** The 24 bytes a client sends first on every HTTP/2 connection, before any frame. */
    val PREFACE: ByteArray = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n".toByteArray(Charsets.US_ASCII)

    /**
     * Decodes every frame in [bytes], the byte stream one side sent (all its TCP segments joined).
     * Skip the client preface if [bytes] starts with it. Throw IllegalArgumentException if the bytes
     * end in the middle of a frame.
     */
    fun decode(bytes: ByteArray): List<Frame> {
        TODO("skip the preface, then: 9-byte header, payload, a Frame by type; repeat")
    }

    /** The 9-byte frame header for these fields, the inverse of what [decode] reads. */
    fun header(length: Int, type: Int, flags: Int, streamId: Int): ByteArray {
        TODO("length in 3 bytes, type, flags, stream id in 4 bytes with the top bit clear")
    }
}
