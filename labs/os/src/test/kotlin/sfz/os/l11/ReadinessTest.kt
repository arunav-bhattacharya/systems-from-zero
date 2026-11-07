package sfz.os.l11

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ReadinessTest {
    private val k = Kernel()

    @Test
    fun `poll checks every socket, epoll only the ones the kernel marked ready`() {
        val sockets = List(2000) { k.socket() }
        val ep = k.epoll()
        sockets.forEach { ep.add(it, Trigger.LEVEL) }
        val busy = listOf(sockets[7], sockets[1200], sockets[1999])
        busy.forEach { k.arrive(it, "auth ping\n") }

        val poll = Poll()
        assertThat(poll.poll(sockets)).containsExactlyElementsOf(busy)
        assertThat(poll.examined).isEqualTo(2000)                       // the whole list, every call
        assertThat(ep.wait()).containsExactlyElementsOf(busy)
        assertThat(ep.examined).isEqualTo(3)                            // only the ready list
    }

    @Test
    fun `epoll_wait over 2,000 idle sockets returns nothing and looks at nothing`() {
        val ep = k.epoll()
        repeat(2000) { ep.add(k.socket(), Trigger.EDGE) }
        assertThat(ep.wait()).isEmpty()
        assertThat(ep.examined).isZero()
    }

    @Test
    fun `level-triggered keeps reporting a socket until it is drained`() {
        val s = k.socket()
        val ep = k.epoll()
        ep.add(s, Trigger.LEVEL)
        k.arrive(s, "auth-7731\n")                                      // 10 bytes

        val reports = (1..4).map { ep.wait().size.also { k.read(s, 4) } }
        assertThat(reports).containsExactly(1, 1, 1, 0)                 // 4 + 4 + 2 bytes, then nothing left
    }

    @Test
    fun `edge-triggered reports a socket once per arrival, however much is still queued`() {
        val s = k.socket()
        val ep = k.epoll()
        ep.add(s, Trigger.EDGE)
        k.arrive(s, "auth-7731\n")

        assertThat(ep.wait()).containsExactly(s)
        k.read(s, 4)
        assertThat(ep.wait()).isEmpty()                                 // 6 bytes queued, and no new edge
        k.arrive(s, "auth-7732\n")
        assertThat(ep.wait()).containsExactly(s)                        // a new arrival is a new edge
    }

    @Test
    fun `a socket that is already readable when you add it is reported`() {
        val s = k.socket()
        k.arrive(s, "early\n")
        val ep = k.epoll()
        ep.add(s, Trigger.EDGE)
        assertThat(ep.wait()).containsExactly(s)
    }

    @Test
    fun `an edge-triggered loop that reads once per wake-up strands data`() {
        val s = k.socket()
        val loop = EventLoop(k, k.epoll(), chunk = 4, drain = false)
        loop.watch(s, Trigger.EDGE)
        k.arrive(s, "auth-7731\n")

        repeat(3) { loop.turn() }
        assertThat(loop.received[s].toString()).isEqualTo("auth")      // stuck: 6 bytes wait for an edge that never comes
        assertThat(s.queue.toString()).isEqualTo("-7731\n")
    }

    @Test
    fun `an edge-triggered loop that reads until EAGAIN gets everything in one turn`() {
        val s = k.socket()
        val loop = EventLoop(k, k.epoll(), chunk = 4, drain = true)
        loop.watch(s, Trigger.EDGE)
        k.arrive(s, "auth-7731\n")

        assertThat(loop.turn()).isEqualTo(1)
        assertThat(loop.received[s].toString()).isEqualTo("auth-7731\n")
        assertThat(k.reads).isEqualTo(4)                                // 4 + 4 + 2 bytes, then the read that says EAGAIN
        assertThat(k.eagains).isEqualTo(1)
    }

    @Test
    fun `a level-triggered loop gets everything, a little at a time`() {
        val s = k.socket()
        val loop = EventLoop(k, k.epoll(), chunk = 4, drain = false)
        loop.watch(s, Trigger.LEVEL)
        k.arrive(s, "auth-7731\n")

        val handled = (1..4).map { loop.turn() }
        assertThat(handled).containsExactly(1, 1, 1, 0)
        assertThat(loop.received[s].toString()).isEqualTo("auth-7731\n")
        assertThat(k.eagains).isZero()                                  // it never asked a socket that had nothing
    }

    @Test
    fun `a peer that hangs up is reported readable and the loop forgets it`() {
        val a = k.socket()
        val b = k.socket()
        val loop = EventLoop(k, k.epoll(), chunk = 64, drain = true)
        loop.watch(a, Trigger.EDGE)
        loop.watch(b, Trigger.EDGE)
        k.arrive(a, "refund-12\n")
        k.hangUp(a)

        loop.turn()
        assertThat(loop.received[a].toString()).isEqualTo("refund-12\n")
        assertThat(loop.closed).containsExactly(a)
        k.arrive(a, "late\n")                                           // removed from the epoll: never reported again
        assertThat(loop.turn()).isZero()
    }
}
