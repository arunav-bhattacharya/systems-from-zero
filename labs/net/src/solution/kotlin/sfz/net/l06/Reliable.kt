package sfz.net.l06

import java.io.IOException
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.SocketAddress
import java.net.SocketException
import java.net.SocketTimeoutException
import java.time.Duration

/** Thrown when a message got no ACK after every attempt. The peer may be down, or the path may be. */
class DeliveryFailedException(message: String) : IOException(message)

/**
 * The sending half of a stop-and-wait protocol: send one message, wait for its ACK, send it again if
 * the ACK doesn't come within [timeout], and only then move on to the next message. The first message
 * gets sequence number 0, the next 1, and so on.
 *
 * [socket] is already bound; this class only sends DATA to [peer] and reads ACKs from it.
 */
class ReliableSender(
    private val socket: DatagramSocket,
    private val peer: SocketAddress,
    private val timeout: Duration = Duration.ofMillis(200),
    private val maxAttempts: Int = 5,
) {
    private var nextSeq = 0

    /** How many DATA datagrams this sender has sent again after a timeout, over its lifetime. */
    var retransmissions: Int = 0
        private set

    /**
     * Sends [message] and returns once the receiver has acknowledged it, with the number of attempts it
     * took (1 when nothing was lost).
     *
     * Each attempt: send `Frame(DATA, seq, message)` to [peer], then wait up to [timeout] (the socket's
     * `soTimeout`) for `Frame(ACK, seq)`. Ignore anything else that arrives, such as a late ACK for an
     * older seq: keep waiting. When the wait runs out, count a retransmission and try again. After
     * [maxAttempts] attempts throw [DeliveryFailedException]. On success, the next message gets seq + 1.
     */
    fun send(message: ByteArray): Int {
        val seq = nextSeq
        val data = Frame(Frame.Kind.DATA, seq, message).encode()
        val buffer = ByteArray(65_535)
        for (attempt in 1..maxAttempts) {
            if (attempt > 1) retransmissions++
            socket.send(DatagramPacket(data, data.size, peer))      // may vanish: nobody will say
            val deadline = System.nanoTime() + timeout.toNanos()
            while (true) {
                val left = (deadline - System.nanoTime()) / 1_000_000
                if (left <= 0) break                                  // this attempt timed out
                socket.soTimeout = left.toInt()
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(packet)
                } catch (_: SocketTimeoutException) {
                    break
                }
                val frame = Frame.decode(packet.data, packet.length) ?: continue
                if (frame.kind == Frame.Kind.ACK && frame.seq == seq) {   // our ACK, not a stale one
                    nextSeq = seq + 1
                    return attempt
                }
            }
        }
        throw DeliveryFailedException("no ACK for seq $seq after $maxAttempts attempts")
    }
}

/**
 * The receiving half: hands each message to [deliver] exactly once and in order, however many copies
 * arrive, and acknowledges every DATA it sees.
 */
class ReliableReceiver(private val socket: DatagramSocket, private val deliver: (ByteArray) -> Unit) {
    private var expected = 0

    /** How many DATA datagrams arrived for a message that had already been delivered. */
    var duplicates: Int = 0
        private set

    /**
     * Handles one datagram, the first [length] bytes of [data], that came from [from]:
     *
     * - DATA with the seq you expect: deliver its payload, expect seq + 1 from now on, ACK it.
     * - DATA with an older seq: its ACK got lost and the sender tried again. Count it in [duplicates]
     *   and don't deliver it again, but do send the ACK again: the sender is still waiting for it.
     * - Anything else (an ACK, garbage, a seq from the future): ignore it.
     *
     * An ACK is `Frame(ACK, seq).encode()`, sent back to [from].
     */
    fun handle(data: ByteArray, length: Int, from: SocketAddress) {
        val frame = Frame.decode(data, length) ?: return
        if (frame.kind != Frame.Kind.DATA) return
        when {
            frame.seq == expected -> { deliver(frame.payload); expected++ }   // new: hand it over once
            frame.seq < expected -> duplicates++                             // seen it: the ACK was lost
            else -> return                                                   // from the future: ignore
        }
        val ack = Frame(Frame.Kind.ACK, frame.seq).encode()
        socket.send(DatagramPacket(ack, ack.size, from))                     // ACK every copy we accept
    }

    /** Receives and handles datagrams until the socket is closed. This part is finished. */
    fun serve() {
        val buffer = ByteArray(65_535)
        while (!socket.isClosed) {
            val packet = DatagramPacket(buffer, buffer.size)
            try {
                socket.receive(packet)
            } catch (_: SocketException) {
                return                                   // closed while waiting
            }
            handle(packet.data, packet.length, packet.socketAddress)
        }
    }
}
