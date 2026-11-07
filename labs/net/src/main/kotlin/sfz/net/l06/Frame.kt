package sfz.net.l06

import java.nio.ByteBuffer

/**
 * One datagram of a tiny reliable protocol built on UDP: 1 byte for the kind, 4 bytes of sequence
 * number, then the message (DATA only). `DATA 7 "AUTH 4242"` is 14 bytes on the wire.
 *
 * This file is complete.
 */
class Frame(val kind: Kind, val seq: Int, val payload: ByteArray = ByteArray(0)) {
    enum class Kind { DATA, ACK }

    fun encode(): ByteArray =
        ByteBuffer.allocate(5 + payload.size).put(kind.ordinal.toByte()).putInt(seq).put(payload).array()

    override fun equals(other: Any?) =
        other is Frame && other.kind == kind && other.seq == seq && other.payload.contentEquals(payload)

    override fun hashCode() = 31 * (31 * kind.hashCode() + seq) + payload.contentHashCode()

    override fun toString() = "$kind $seq" + if (kind == Kind.DATA) " \"${payload.decodeToString()}\"" else ""

    companion object {
        /** Reads the first [length] bytes of [bytes]; null when they are not a frame (too short, unknown kind). */
        fun decode(bytes: ByteArray, length: Int = bytes.size): Frame? {
            if (length < 5) return null
            val kind = Kind.entries.getOrNull(bytes[0].toInt()) ?: return null
            val seq = ByteBuffer.wrap(bytes, 1, 4).getInt()
            return Frame(kind, seq, bytes.copyOfRange(5, length))
        }
    }
}
