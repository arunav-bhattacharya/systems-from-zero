package sfz.msg.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/** The queue's rules, one per test. No broker and no Docker: the whole class runs in well under a second. */
class MiniQueueTest {
    private fun m(seq: Int, key: String = "acct-17") = Message(key, seq)

    private fun queueOf(vararg seqs: Int, limit: Int = 20, dlq: MiniQueue? = null) =
        MiniQueue("payments", limit, dlq).apply { seqs.forEach { publish(m(it)) } }

    @Test
    fun `deliver hands out messages from the head, in publish order`() {
        val q = queueOf(1, 2, 3)
        q.subscribe("A", prefetch = 10)
        val got = listOf(q.deliver("A")!!, q.deliver("A")!!, q.deliver("A")!!)
        assertThat(got.map { it.message.seq }).containsExactly(1, 2, 3)
        assertThat(got.map { it.tag }).containsExactly(1L, 2L, 3L)
        assertThat(got).allSatisfy {
            assertThat(it.consumer).isEqualTo("A")
            assertThat(it.redelivered).isFalse()
            assertThat(it.deliveryCount).isZero()
        }
        assertThat(q.deliver("A")).isNull()                       // nothing left
        assertThat(q.ready).isZero()
        assertThat(q.unacked).isEqualTo(3)                        // delivered is not gone: nobody has acked
    }

    @Test
    fun `a consumer that has not subscribed gets an error, not a message`() {
        val q = queueOf(1)
        assertThatThrownBy { q.deliver("ghost") }.isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun `prefetch caps how many unacknowledged deliveries one consumer holds`() {
        val q = queueOf(1, 2, 3, 4, 5)
        q.subscribe("A", prefetch = 3)
        q.subscribe("B", prefetch = 1)
        repeat(3) { assertThat(q.deliver("A")).isNotNull() }
        assertThat(q.deliver("A")).isNull()                       // A is at its prefetch: it waits
        assertThat(q.deliver("B")!!.message.seq).isEqualTo(4)     // the cap is per consumer, so B still gets one
        q.ack(1)
        assertThat(q.deliver("A")!!.message.seq).isEqualTo(5)     // one ack, one more delivery
        assertThat(q.unackedBy("A")).isEqualTo(3)
        assertThat(q.unackedBy("B")).isEqualTo(1)
    }

    @Test
    fun `ack removes a message for good, and an unknown or repeated tag is an error`() {
        val q = queueOf(1, 2)
        q.subscribe("A", prefetch = 10)
        val d = q.deliver("A")!!
        q.ack(d.tag)
        assertThat(q.unacked).isZero()
        assertThat(q.ready).isEqualTo(1)
        assertThatThrownBy { q.ack(d.tag) }.isInstanceOf(IllegalStateException::class.java)
        assertThatThrownBy { q.ack(99) }.isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun `a disconnect puts every unacked delivery back at its original position, marked redelivered`() {
        val q = queueOf(1, 2, 3, 4)
        q.subscribe("A", prefetch = 10)
        val first = q.deliver("A")!!
        q.deliver("A")
        q.deliver("A")
        q.ack(first.tag)                                          // seq 1 is done; 2 and 3 are in flight; 4 waits
        q.disconnect("A")
        assertThat(q.unacked).isZero()
        assertThat(q.ready).isEqualTo(3)
        assertThatThrownBy { q.deliver("A") }.isInstanceOf(IllegalStateException::class.java)   // no longer subscribed

        q.subscribe("A", prefetch = 10)                           // the restarted instance
        val again = generateSequence { q.deliver("A") }.toList()
        assertThat(again.map { it.message.seq }).containsExactly(2, 3, 4)   // back at the head, in their old order
        assertThat(again.map { it.redelivered }).containsExactly(true, true, false)
        assertThat(again.map { it.deliveryCount }).containsExactly(1, 1, 0)
        assertThat(again.map { it.tag }).containsExactly(4L, 5L, 6L)         // a redelivery is a new delivery
    }

    @Test
    fun `two competing consumers and one crash turn m1 to m5 into m1 m2 m4 m3 m5`() {
        val q = queueOf(1, 2, 3, 4, 5)
        q.subscribe("A", prefetch = 1)
        q.subscribe("B", prefetch = 1)
        val booked = mutableListOf<Message>()
        fun finish(d: Delivery) { booked += d.message; q.ack(d.tag) }

        finish(q.deliver("A")!!)                                  // m1
        finish(q.deliver("B")!!)                                  // m2
        val m3 = q.deliver("B")!!
        val m4 = q.deliver("A")!!
        assertThat(m3.message.seq to m4.message.seq).isEqualTo(3 to 4)
        q.disconnect("B")                                         // B dies while working on m3
        finish(m4)                                                // A was busy with m4 and books it
        val redelivered = q.deliver("A")!!
        assertThat(redelivered.message.seq).isEqualTo(3)
        assertThat(redelivered.redelivered).isTrue()
        finish(redelivered)
        finish(q.deliver("A")!!)                                  // m5

        assertThat(booked.map { it.seq }).containsExactly(1, 2, 4, 3, 5)
        assertThat(OrderCheck.check(booked).inversions()).isEqualTo(1)
    }

    @Test
    fun `reject with requeue redelivers the message, reject without requeue dead-letters it`() {
        val dlq = MiniQueue("payments.dlq")
        val q = queueOf(1, 2, dlq = dlq)
        q.subscribe("A", prefetch = 10)
        val d1 = q.deliver("A")!!
        q.reject(d1.tag, requeue = true)
        val again = q.deliver("A")!!
        assertThat(again.message.seq).isEqualTo(1)
        assertThat(again.redelivered).isTrue()
        assertThat(again.deliveryCount).isEqualTo(1)

        q.reject(again.tag, requeue = false)                      // "this one can never succeed"
        assertThat(q.unacked).isZero()
        assertThat(q.ready).isEqualTo(1)                          // only seq 2 is left
        assertThat(dlq.ready).isEqualTo(1)
        assertThatThrownBy { q.reject(again.tag, requeue = true) }.isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun `a message over the delivery limit goes to the dead-letter queue`() {
        val dlq = MiniQueue("settlements.dlq")
        val q = MiniQueue("settlements", deliveryLimit = 3, deadLetters = dlq)
        q.publish(m(1, "m-881"))
        q.subscribe("A", prefetch = 1)
        val counts = mutableListOf<Int>()
        while (true) {
            val d = q.deliver("A") ?: break
            counts += d.deliveryCount
            q.reject(d.tag, requeue = true)                       // the consumer fails on it every time
        }
        assertThat(counts).containsExactly(0, 1, 2, 3)            // four deliveries, as in the RabbitMQ Try-it
        assertThat(q.ready).isZero()
        assertThat(dlq.ready).isEqualTo(1)
        assertThat(q.dropped).isEmpty()
    }

    @Test
    fun `without a dead-letter queue the default limit of 20 drops the message after 21 deliveries`() {
        val q = queueOf(1)
        assertThat(q.deliveryLimit).isEqualTo(20)                 // RabbitMQ quorum queues: 20 since 4.0
        q.subscribe("A", prefetch = 1)
        var deliveries = 0
        while (true) {
            val d = q.deliver("A") ?: break
            deliveries++
            q.disconnect("A")                                     // a crash also counts as a failed delivery
            q.subscribe("A", prefetch = 1)
        }
        assertThat(deliveries).isEqualTo(21)
        assertThat(q.dropped).containsExactly(m(1))
    }

    @Test
    fun `with auto-ack a delivery counts as acknowledged at once, so a crash returns nothing`() {
        val q = queueOf(1, 2, 3, 4, 5)
        q.subscribe("A", prefetch = 2, autoAck = true)
        val got = generateSequence { q.deliver("A") }.toList()
        assertThat(got).hasSize(5)                                // prefetch does not apply to auto-ack
        assertThat(q.unacked).isZero()
        q.disconnect("A")                                         // A crashes before it has booked any of them
        assertThat(q.ready).isZero()                              // the broker has nothing to give back: 5 lost
        assertThatThrownBy { q.ack(got[0].tag) }.isInstanceOf(IllegalStateException::class.java)
    }
}
