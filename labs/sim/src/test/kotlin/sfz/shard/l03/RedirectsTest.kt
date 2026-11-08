package sfz.shard.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class RedirectsTest {
    private val cluster = Cluster(listOf("A", "B", "C"))
    private val keys = (0 until 300).map { "pay-$it" }

    init {
        keys.forEach { cluster.put(it, "value of $it") }
    }

    /** Slot 0 starts on A. These are its keys. */
    private val slot0 = keys.filter { slotOf(it) == 0 }

    @Test
    fun `a client with the cluster's map reaches every owner in one request`() {
        val client = RoutingClient(cluster, cluster.slotMap())
        keys.forEach { assertThat(client.get(it)).isEqualTo("value of $it") }
        assertThat(cluster.requests).isEqualTo(300)
        assertThat(client.moved).isZero()
        assertThat(client.asks).isZero()
    }

    @Test
    fun `a stale map costs one MOVED per slot, then the client knows`() {
        val client = RoutingClient(cluster, Array(SLOTS) { "A" }) // thinks A owns everything
        keys.forEach { assertThat(client.get(it)).isEqualTo("value of $it") }
        assertThat(client.moved).isEqualTo(10) // slots 6-15 live on B and C
        assertThat(client.slotMap).containsExactly(*cluster.slotMap())
        assertThat(cluster.requests).isEqualTo(310)
    }

    @Test
    fun `a key that has already moved is reached through ASK, and the map stays put`() {
        val client = RoutingClient(cluster, cluster.slotMap())
        cluster.startMigration(0, "C")
        repeat(5) { cluster.tick() } // the five lowest keys of slot 0 are on C now
        slot0.forEach { assertThat(client.get(it)).isEqualTo("value of $it") }
        assertThat(client.asks).isEqualTo(5)
        assertThat(client.moved).isZero()
        assertThat(client.slotMap[0]).isEqualTo("A") // ASK is for one request; the slot is still A's
        assertThat(cluster.requests).isEqualTo(slot0.size + 5)
    }

    @Test
    fun `the importing node refuses a request that didn't say ASKING`() {
        cluster.startMigration(0, "C")
        cluster.tick()
        val first = slot0.min()
        assertThat(cluster.get("C", first)).isEqualTo(Reply.Moved(0, "A"))
        assertThat(cluster.get("C", first, asking = true)).isEqualTo(Reply.Value("value of $first"))
    }

    @Test
    fun `when the migration ends, one MOVED sends the client to the new owner`() {
        val client = RoutingClient(cluster, cluster.slotMap())
        cluster.startMigration(0, "C")
        while (cluster.tick()) Unit
        assertThat(cluster.migratingSlot).isNull()
        slot0.forEach { assertThat(client.get(it)).isEqualTo("value of $it") }
        assertThat(client.moved).isEqualTo(1)
        assertThat(client.asks).isZero()
        assertThat(client.slotMap[0]).isEqualTo("C")
    }

    @Test
    fun `every read during a whole migration returns the right value`() {
        val client = RoutingClient(cluster, cluster.slotMap())
        cluster.startMigration(0, "C")
        var expectedAsks = 0
        var step = 0
        do {
            // one round of reads of the slot's keys between each step of the migration
            slot0.forEach { assertThat(client.get(it)).isEqualTo("value of $it") }
            if (cluster.migratingSlot != null) expectedAsks += minOf(step, slot0.size)
            step++
        } while (cluster.tick())
        slot0.forEach { assertThat(client.get(it)).isEqualTo("value of $it") }
        assertThat(client.asks).isEqualTo(expectedAsks)
        assertThat(client.moved).isEqualTo(1)
    }
}
