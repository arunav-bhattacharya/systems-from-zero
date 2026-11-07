package sfz.redis.l11

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import redis.clients.jedis.util.JedisClusterCRC16
import kotlin.random.Random

// a model: no Docker needed
class ClusterRouterTest {
    private val node1 = "127.0.0.1:7001"
    private val node2 = "127.0.0.1:7002"
    private val node3 = "127.0.0.1:7003"

    @Test
    fun `crc16 gives the cluster spec's check value`() {
        assertThat(HashSlots.crc16("123456789".toByteArray())).isEqualTo(0x31C3)
        assertThat(HashSlots.crc16(ByteArray(0))).isZero()
    }

    @Test
    fun `slots match what a real Redis 8 cluster answered to CLUSTER KEYSLOT`() {
        assertThat(HashSlots.slot("payment:42")).isEqualTo(9055)
        assertThat(HashSlots.slot("123456789")).isEqualTo(12739)       // 0x31C3 mod 16384
        assertThat(HashSlots.slot("merchant:7")).isEqualTo(10890)
        assertThat(HashSlots.slot("{merchant:7}:payments")).isEqualTo(10890)
        assertThat(HashSlots.slot("{merchant:7}:refunds")).isEqualTo(10890)
        assertThat(HashSlots.slot("foo{}{bar}")).isEqualTo(8363)
        assertThat(HashSlots.slot("foo{bar}{zap}")).isEqualTo(5061)    // the same slot as "bar"
    }

    @Test
    fun `hash tags follow the cluster spec's rules`() {
        assertThat(HashSlots.hashTag("payment:42")).isEqualTo("payment:42")
        assertThat(HashSlots.hashTag("{user1000}.following")).isEqualTo("user1000")
        assertThat(HashSlots.hashTag("foo{}{bar}")).isEqualTo("foo{}{bar}")
        assertThat(HashSlots.hashTag("foo{{bar}}zap")).isEqualTo("{bar")
        assertThat(HashSlots.hashTag("foo{bar}{zap}")).isEqualTo("bar")
        assertThat(HashSlots.hashTag("{}payment")).isEqualTo("{}payment")
        assertThat(HashSlots.hashTag("payment{42")).isEqualTo("payment{42")
    }

    @Test
    fun `slot agrees with the function Jedis's cluster client uses on 10,000 keys`() {
        val random = Random(11)
        repeat(10_000) {
            val key = when (it % 3) {
                0 -> "payment:${random.nextInt(1_000_000)}"
                1 -> "{merchant:${random.nextInt(500)}}:refunds:${random.nextInt(100)}"
                else -> "card:${random.nextLong()}:auths"
            }
            assertThat(HashSlots.slot(key)).describedAs(key).isEqualTo(JedisClusterCRC16.getSlot(key))
        }
    }

    @Test
    fun `a client with a fresh slot table goes straight to the owner`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster)

        assertThat(client.execute("SET", "payment:42", "approved")).isEqualTo("OK")
        assertThat(client.execute("GET", "payment:42")).isEqualTo("approved")

        assertThat(cluster.peek(node2, "payment:42")).isEqualTo("approved")   // slot 9055 lives on node 2
        assertThat(cluster.received(node2)).isEqualTo(2)
        assertThat(cluster.received(node1) + cluster.received(node3)).isZero()
        assertThat(client.movedFollowed + client.askFollowed).isZero()
    }

    @Test
    fun `a stale table is fixed by one MOVED and never needs it again`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster)
        client.execute("SET", "payment:42", "approved")
        cluster.startMigration(9055, node3)                       // an operator moves the slot to node 3
        cluster.finishMigration(9055)

        assertThat(client.execute("GET", "payment:42")).isEqualTo("approved")
        assertThat(client.movedFollowed).isEqualTo(1)
        assertThat(client.nodeFor("payment:42")).isEqualTo(node3)  // the table now says node 3

        client.execute("INCR", "{payment:42}:retries")             // same slot: straight to node 3
        assertThat(client.movedFollowed).isEqualTo(1)
        assertThat(cluster.received(node3)).isEqualTo(2)
    }

    @Test
    fun `during a migration ASK sends one command to the target and leaves the table alone`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster)
        client.execute("SET", "{payment:42}:a", "approved")
        client.execute("SET", "{payment:42}:b", "declined")
        cluster.startMigration(9055, node3)
        cluster.moveKeys("{payment:42}:a")                          // a has moved, b has not yet

        assertThat(client.execute("GET", "{payment:42}:a")).isEqualTo("approved")   // node 2: ASK; node 3: here it is
        assertThat(client.askFollowed).isEqualTo(1)
        assertThat(client.nodeFor("{payment:42}:a")).isEqualTo(node2)               // still node 2 in the table

        assertThat(client.execute("GET", "{payment:42}:b")).isEqualTo("declined")   // node 2 still has b
        assertThat(client.askFollowed).isEqualTo(1)
        assertThat(client.movedFollowed).isZero()
    }

    @Test
    fun `a new key written during a migration lands on the target`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster)
        cluster.startMigration(9055, node3)

        client.execute("SET", "{payment:42}:new", "pending")

        assertThat(cluster.peek(node3, "{payment:42}:new")).isEqualTo("pending")
        assertThat(cluster.peek(node2, "{payment:42}:new")).isNull()
        assertThat(client.askFollowed).isEqualTo(1)
    }

    @Test
    fun `keys in different slots are refused before anything is sent`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster)

        assertThatThrownBy { client.execute("MSET", "payment:42", "a", "payment:43", "b") }
            .isInstanceOf(CrossSlotException::class.java)
        assertThat(cluster.nodes.sumOf { cluster.received(it) }).isZero()

        // a hash tag puts both keys in slot 10890, so one node can run the whole command
        assertThat(client.execute("MSET", "{merchant:7}:payments", "10", "{merchant:7}:refunds", "2")).isEqualTo("OK")
        assertThat(cluster.peek(node2, "{merchant:7}:refunds")).isEqualTo("2")
    }

    @Test
    fun `an error from a node becomes a ClusterException`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster)
        client.execute("SET", "{payment:42}:a", "approved")
        client.execute("SET", "{payment:42}:b", "declined")
        cluster.startMigration(9055, node3)
        cluster.moveKeys("{payment:42}:a")                          // the two keys are now on different nodes

        assertThatThrownBy { client.execute("DEL", "{payment:42}:a", "{payment:42}:b") }
            .isInstanceOf(ClusterException::class.java)
            .hasMessageContaining("TRYAGAIN")
    }

    @Test
    fun `a client stops after maxRedirects when two nodes point at each other`() {
        val cluster = ModelCluster()
        val client = ClusterRouter(cluster, maxRedirects = 5)
        cluster.setStaleView(node2, 9055, node1)                   // node 2 thinks node 1 owns it...
        cluster.setStaleView(node1, 9055, node2)                   // ...and node 1 thinks node 2 does

        assertThatThrownBy { client.execute("GET", "payment:42") }.isInstanceOf(ClusterException::class.java)
        assertThat(cluster.received(node1) + cluster.received(node2)).isEqualTo(6)   // the first try, then 5 redirects
    }
}
