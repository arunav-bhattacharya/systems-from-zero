package sfz.redis.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

// a model: no Docker needed, runs in milliseconds
class EventLoopTest {

    @Test
    fun `each client gets its replies in the order it sent its commands`() {
        val loop = EventLoop()
        loop.send("A", 0, "SET", "auths:today", "1")
        loop.send("A", 0, "INCR", "auths:today")
        loop.send("A", 0, "INCR", "auths:today")
        loop.send("A", 0, "GET", "auths:today")

        val replies = loop.runUntilIdle()

        assertThat(replies.map { it.command to it.value }).containsExactly(
            "SET auths:today 1" to "OK",
            "INCR auths:today" to "2",
            "INCR auths:today" to "3",
            "GET auths:today" to "3",
        )
    }

    @Test
    fun `the loop never runs two commands at once, so no INCR is lost`() {
        val loop = EventLoop()
        for (i in 0 until 50) {
            for (client in listOf("A", "B", "C")) loop.send(client, i.toLong(), "INCR", "hits")
        }

        val replies = loop.runUntilIdle()

        assertThat(replies).hasSize(150)
        // every command starts after the previous one finished: one thread, no overlap
        replies.zipWithNext { a, b -> assertThat(b.startedAt).isGreaterThanOrEqualTo(a.finishedAt) }
        // 150 increments, 150 different results: none lost, none doubled
        assertThat(replies.map { it.value.toInt() }).containsExactlyInAnyOrderElementsOf(1..150)
    }

    @Test
    fun `one slow command delays every client that arrives behind it`() {
        val loop = EventLoop()
        loop.send("A", 0, "SLOW", "100")                 // a 100-tick script
        loop.send("B", 1, "GET", "card:7:status")        // arrives one tick later
        loop.send("C", 2, "SET", "card:9:status", "ok")  // and another

        val byClient = loop.runUntilIdle().associateBy { it.client }

        assertThat(byClient.getValue("A").finishedAt).isEqualTo(100)
        assertThat(byClient.getValue("B").startedAt).isGreaterThanOrEqualTo(100)
        assertThat(byClient.getValue("B").latency).isGreaterThanOrEqualTo(99)
        assertThat(byClient.getValue("C").latency).isGreaterThanOrEqualTo(99)
    }

    @Test
    fun `a command that arrives during a pass waits for the next pass`() {
        val loop = EventLoop()
        loop.send("A", 0, "SLOW", "10")
        loop.send("B", 0, "SET", "payment:42", "approved")
        loop.send("A", 3, "GET", "payment:42")           // arrives while SLOW runs

        val replies = loop.runUntilIdle()

        // B was already waiting when the pass began, so it runs before A's second command
        assertThat(replies.map { it.client + " " + it.command }).containsExactly(
            "A SLOW 10",
            "B SET payment:42 approved",
            "A GET payment:42",
        )
        assertThat(replies.last().value).isEqualTo("approved")
    }

    @Test
    fun `an idle loop sleeps until the next command arrives`() {
        val loop = EventLoop()
        loop.send("A", 50, "GET", "payment:42")

        val reply = loop.runUntilIdle().single()

        assertThat(reply.startedAt).isEqualTo(50)
        assertThat(reply.finishedAt).isEqualTo(51)
        assertThat(reply.value).isEqualTo("(nil)")
        assertThat(loop.clock).isEqualTo(51)
    }
}
