package sfz.cons.l05

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout

@Timeout(10)
class CoordinatorTest {
    private val sim = Sim()
    private val c = Coordinator(sim)

    @Test
    fun `every change gets the next revision and sequential names count per parent`() {
        val config = c.create("/config/fx-rate", "1.09")!!
        assertThat(config.createRevision).isEqualTo(1)
        assertThat(config.session).isNull()

        val s = c.openSession(ttlMs = 1_000)
        val a = c.create("/election/n-", "pod-a", session = s, sequential = true)!!
        val b = c.create("/election/n-", "pod-b", session = s, sequential = true)!!
        val lock = c.create("/locks/n-", "pod-a", sequential = true)!!
        assertThat(a.path).isEqualTo("/election/n-0000000000")
        assertThat(b.path).isEqualTo("/election/n-0000000001")
        assertThat(lock.path).`as`("a different parent has its own counter").isEqualTo("/locks/n-0000000000")
        assertThat(listOf(a, b, lock).map { it.createRevision }).containsExactly(2L, 3L, 4L)
        assertThat(a.session).isEqualTo(s)

        assertThat(c.create("/config/fx-rate", "1.10")).`as`("the path exists already").isNull()
        assertThat(c.revision).`as`("a failed create changes nothing").isEqualTo(4)

        assertThat(c.delete(a.path)).isTrue()
        assertThat(c.revision).isEqualTo(5)
        val again = c.create("/election/n-", "pod-c", session = s, sequential = true)!!
        assertThat(again.path).`as`("sequence numbers are never reused").isEqualTo("/election/n-0000000002")
        assertThat(again.createRevision).isEqualTo(6)
        assertThat(c.children("/election").map { it.data }).containsExactly("pod-b", "pod-c")
    }

    @Test
    fun `an ephemeral node lives exactly as long as its session's lease`() {
        val s = c.openSession(ttlMs = 1_000)
        val pod = c.create("/svc/payments/pod-a", "10.0.0.5:8080", session = s)!!
        c.create("/svc/payments/config", "v2")
        sim.runUntil(999)
        assertThat(c.get(pod.path)).isNotNull()
        sim.runUntil(1_000)
        assertThat(c.get(pod.path)).`as`("no keep-alive for 1,000 ms: the service ends the session").isNull()
        assertThat(c.get("/svc/payments/config")).`as`("a node without a session stays").isNotNull()
        assertThat(c.revision).`as`("the deletion is a change too").isEqualTo(3)
        assertThat(c.isAlive(s)).isFalse()
        assertThat(c.keepAlive(s)).`as`("too late to renew").isFalse()
        assertThatThrownBy { c.create("/svc/payments/pod-a", "back", session = s) }
            .`as`("a dead session can't create nodes").isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun `keep-alives move the lease's end forward`() {
        val s = c.openSession(ttlMs = 1_000)
        val pod = c.create("/svc/payments/pod-b", "10.0.0.6:8080", session = s)!!
        sim.at(600) { assertThat(c.keepAlive(s)).isTrue() }
        sim.runUntil(1_599)
        assertThat(c.get(pod.path)).`as`("renewed at 600, so it lasts until 1,600").isNotNull()
        sim.runUntil(1_600)
        assertThat(c.get(pod.path)).isNull()
    }

    @Test
    fun `expiring a session deletes each of its nodes as its own change and fires their watches`() {
        val s = c.openSession(ttlMs = 10_000)
        val other = c.openSession(ttlMs = 10_000)
        c.create("/svc/payments/pod-a", "a", session = s)
        c.create("/svc/payments/pod-b", "b", session = other)
        c.create("/locks/settle", "a", session = s)
        val events = ArrayList<WatchEvent>()
        c.watch("/svc/payments/pod-a") { events += it }
        c.watch("/locks/settle") { events += it }
        c.watch("/svc/payments/pod-b") { events += it }

        sim.at(100) { c.expire(s) }
        sim.runUntil(101)
        assertThat(events).`as`("watch events arrive after a delay, never at the instant of the change").isEmpty()
        sim.runUntil(102)
        assertThat(events).containsExactly(
            WatchEvent(EventType.DELETED, "/locks/settle", 4),           // path order: /locks before /svc
            WatchEvent(EventType.DELETED, "/svc/payments/pod-a", 5),
        )
        assertThat(c.get("/svc/payments/pod-b")).`as`("another session's node").isNotNull()
        assertThat(c.revision).isEqualTo(5)
        c.expire(s)
        assertThat(c.revision).`as`("expiring twice changes nothing").isEqualTo(5)
    }

    @Test
    fun `a watch fires once, for the next change, and then it is gone`() {
        val first = c.create("/election/n-", "pod-a", sequential = true)!!
        val events = ArrayList<WatchEvent>()
        c.watch(first.path) { events += it }
        sim.at(10) { c.delete(first.path) }
        sim.at(20) { c.create(first.path, "pod-a again") }
        sim.at(30) { c.delete(first.path) }
        sim.runUntil(100)
        assertThat(events).containsExactly(WatchEvent(EventType.DELETED, first.path, 2))
        assertThat(c.notificationsSent).isEqualTo(1)

        val later = ArrayList<WatchEvent>()
        c.watch("/election/n-0000000001") { later += it }
        c.create("/election/n-", "pod-b", sequential = true)
        sim.runUntil(200)
        assertThat(later).`as`("a watch on a path that doesn't exist yet hears its creation")
            .containsExactly(WatchEvent(EventType.CREATED, "/election/n-0000000001", 5))
    }
}
