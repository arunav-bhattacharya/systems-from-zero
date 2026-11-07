package sfz.net.l07

import sfz.net.l07.Flag.ACK
import sfz.net.l07.Flag.FIN
import sfz.net.l07.Flag.PSH
import sfz.net.l07.Flag.RST
import sfz.net.l07.Flag.SYN

/**
 * The ten segments of `src/test/resources/sfz/net/l07/echo-connection.txt`, written out by hand from
 * tcpdump's summary lines, plus the refused connect from the second Try it. Client 10.10.1.10 port
 * 50744, echo server 10.10.1.20 port 9000.
 */
object Captured {
    const val CLIENT_PORT = 50744
    const val SERVER_PORT = 9000
    const val CLIENT_ISN = 244700535L
    const val SERVER_ISN = 4042781690L

    private fun c(seq: Long, ack: Long, vararg f: Flag, win: Int = 502, len: Int = 0, mss: Int? = null) =
        Segment(CLIENT_PORT, SERVER_PORT, seq, ack, f.toSet(), win, len, mss)

    private fun s(seq: Long, ack: Long, vararg f: Flag, win: Int = 509, len: Int = 0, mss: Int? = null) =
        Segment(SERVER_PORT, CLIENT_PORT, seq, ack, f.toSet(), win, len, mss)

    val connection = listOf(
        c(244700535, 0, SYN, win = 64240, mss = 1460),                    // 1  [S]
        s(4042781690, 244700536, SYN, ACK, win = 65160, mss = 1460),      // 2  [S.]
        c(244700536, 4042781691, ACK),                                    // 3  [.]
        c(244700536, 4042781691, PSH, ACK, len = 17),                     // 4  [P.] AUTH 4242 100.00
        s(4042781691, 244700553, ACK),                                    // 5  [.]
        c(244700553, 4042781691, FIN, ACK),                               // 6  [F.] the client closes first
        s(4042781691, 244700554, PSH, ACK, len = 17),                     // 7  [P.] the echo, also ACKs the FIN
        c(244700554, 4042781708, ACK),                                    // 8  [.]
        s(4042781708, 244700554, FIN, ACK),                               // 9  [F.] the server closes
        c(244700554, 4042781709, ACK),                                    // 10 [.] the client is in TIME-WAIT
    )

    /** Connect to 10.10.1.20:9001, where nothing listens: SYN, then RST+ACK with seq 0. */
    val refusedSyn = Segment(60578, 9001, 1259064435, 0, setOf(SYN), 64240, 0, 1460)
    val refusedRst = Segment(9001, 60578, 0, 1259064436, setOf(RST, ACK), 0, 0)
}

/** What the tests compare: everything but the window and the options, which a real kernel tunes. */
fun Segment?.shape(): String =
    if (this == null) "nothing" else "$srcPort > $dstPort ${flags.sortedBy { it.bit }} seq $seq ack $ack len $payloadLength"
