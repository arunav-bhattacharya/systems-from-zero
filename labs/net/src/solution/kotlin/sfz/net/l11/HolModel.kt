package sfz.net.l11

data class Packet(val stream: Int, val bytes: Int)

data class Timing(val sendGapMs: Long, val oneWayMs: Long, val resendAfterMs: Long)

object HolModel {

    fun arrival(i: Int, lost: Set<Int>, t: Timing): Long {
        val sent = i * t.sendGapMs
        return if (i in lost) sent + t.resendAfterMs + t.oneWayMs else sent + t.oneWayMs
    }

    fun tcp(packets: List<Packet>, lost: Set<Int>, t: Timing): Map<Int, Long> {
        val done = LinkedHashMap<Int, Long>()
        var inOrder = 0L                                  // the latest arrival so far: nothing passes a hole
        for ((i, p) in packets.withIndex()) {
            inOrder = maxOf(inOrder, arrival(i, lost, t))
            done[p.stream] = inOrder                      // the last packet of a stream decides
        }
        return done
    }

    fun quic(packets: List<Packet>, lost: Set<Int>, t: Timing): Map<Int, Long> {
        val done = LinkedHashMap<Int, Long>()
        val perStream = HashMap<Int, Long>()              // one in-order point per stream
        for ((i, p) in packets.withIndex()) {
            val at = maxOf(perStream[p.stream] ?: 0L, arrival(i, lost, t))
            perStream[p.stream] = at
            done[p.stream] = at
        }
        return done
    }
}
