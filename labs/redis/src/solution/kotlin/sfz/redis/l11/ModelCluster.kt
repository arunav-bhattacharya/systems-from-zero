package sfz.redis.l11

import redis.clients.jedis.util.JedisClusterCRC16

/** What one cluster node answers, in the model. */
sealed interface NodeReply {
    /** A normal reply: `OK`, a value, a number as text, or null for a missing key. */
    data class Value(val value: String?) : NodeReply

    /** `-MOVED <slot> <node>`: that node owns the slot now. Send this and every later command for the slot there. */
    data class Moved(val slot: Int, val node: String) : NodeReply

    /** `-ASK <slot> <node>`: the slot is moving there. Send only this command there, preceded by ASKING. */
    data class Ask(val slot: Int, val node: String) : NodeReply

    /** `-CROSSSLOT ...`, `-TRYAGAIN ...` or another error. */
    data class Error(val message: String) : NodeReply
}

/**
 * The keys a command names, in order. Done for you: GET, SET, INCR, DEL, EXISTS and MSET.
 * `MSET k1 v1 k2 v2` names k1 and k2; `DEL a b c` names a, b and c.
 */
fun keysOf(command: List<String>): List<String> = when (command[0].uppercase()) {
    "GET", "SET", "INCR" -> listOf(command[1])
    "DEL", "EXISTS" -> command.drop(1)
    "MSET" -> command.drop(1).filterIndexed { i, _ -> i % 2 == 0 }
    else -> throw IllegalArgumentException("the model cluster doesn't know ${command[0]}")
}

/**
 * A Redis Cluster in memory, done for you, so the lab's client can be tested without Docker.
 *
 * Each node has its own keys and its own view of which node owns each of the 16,384 slots, and answers
 * the way a real node does:
 * - Keys in more than one slot: `CROSSSLOT`.
 * - A slot this node owns: run the command. If the slot is being migrated away and none of the keys are
 *   here any more, `ASK` the target; if only some are here, `TRYAGAIN`.
 * - A slot this node doesn't own: run it only if the slot is migrating here and the client sent ASKING
 *   first; otherwise `MOVED` to the owner.
 *
 * The nodes compute slots with Jedis's `JedisClusterCRC16.getSlot`, the same function Jedis's
 * `RedisClusterClient` uses. Your `HashSlots.slot` must agree with it.
 */
class ModelCluster(val nodes: List<String> = listOf("127.0.0.1:7001", "127.0.0.1:7002", "127.0.0.1:7003")) {
    // each node's own copy of the slot table, split the way `redis-cli --cluster create` splits it
    private val views: Map<String, Array<String>> = nodes.associateWith { initialSplit() }
    private val data: Map<String, MutableMap<String, String>> = nodes.associateWith { HashMap() }
    private val migrating = HashMap<Int, String>()               // slot -> the node it is moving to
    private val received = nodes.associateWith { 0 }.toMutableMap()

    /** The node that owns [slot], as the cluster agrees. */
    fun ownerOf(slot: Int): String = views.getValue(nodes[0])[slot]

    /** How many commands [node] has been sent (ASKING itself is not counted). */
    fun received(node: String): Int = received.getValue(node)

    /** `CLUSTER SHARDS`, simplified: which node owns each range of slots. A cluster client loads this when it starts. */
    fun shards(): Map<IntRange, String> {
        val result = LinkedHashMap<IntRange, String>()
        var start = 0
        for (slot in 1..SLOTS) {
            if (slot == SLOTS || ownerOf(slot) != ownerOf(start)) {
                result[start until slot] = ownerOf(start)
                start = slot
            }
        }
        return result
    }

    /** What [node] answers to [command]. [asking] means the client sent ASKING just before it. */
    fun send(node: String, command: List<String>, asking: Boolean = false): NodeReply {
        received[node] = received.getValue(node) + 1
        val keys = keysOf(command)
        val slots = keys.map { JedisClusterCRC16.getSlot(it) }.distinct()
        if (slots.size > 1) return NodeReply.Error("CROSSSLOT Keys in request don't hash to the same slot")
        val slot = slots.single()
        val store = data.getValue(node)
        if (views.getValue(node)[slot] == node) {
            val target = migrating[slot]
            if (target != null) {
                val here = keys.count { it in store }
                if (here == 0) return NodeReply.Ask(slot, target)       // gone already, or never existed: ask the target
                if (here < keys.size) return NodeReply.Error("TRYAGAIN Multiple keys request during rehashing of slot")
            }
            return NodeReply.Value(run(store, command))
        }
        if (asking && migrating[slot] == node) return NodeReply.Value(run(store, command))   // importing, and asked
        return NodeReply.Moved(slot, views.getValue(node)[slot])
    }

    /** `CLUSTER SETSLOT <slot> MIGRATING` on the owner and `IMPORTING` on [target]: a classic resharding begins. */
    fun startMigration(slot: Int, target: String) {
        require(target in nodes && target != ownerOf(slot)) { "slot $slot can't move to $target" }
        migrating[slot] = target
    }

    /** `MIGRATE`: moves [keys] (all in one migrating slot) from the owner to the target, one atomic step each. */
    fun moveKeys(vararg keys: String) {
        for (key in keys) {
            val slot = JedisClusterCRC16.getSlot(key)
            val target = migrating[slot] ?: error("slot $slot is not migrating")
            data.getValue(ownerOf(slot)).remove(key)?.let { data.getValue(target)[key] = it }
        }
    }

    /** `CLUSTER SETSLOT <slot> NODE <target>` on every node: moves any keys left and makes the target the owner. */
    fun finishMigration(slot: Int) {
        val target = migrating.remove(slot) ?: error("slot $slot is not migrating")
        val source = data.getValue(ownerOf(slot))
        source.keys.filter { JedisClusterCRC16.getSlot(it) == slot }.forEach { key ->
            data.getValue(target)[key] = source.remove(key)!!
        }
        views.values.forEach { it[slot] = target }
    }

    /** Makes [node] believe, wrongly, that [believedOwner] owns [slot], as a node with an old config does for a moment. */
    fun setStaleView(node: String, slot: Int, believedOwner: String) {
        views.getValue(node)[slot] = believedOwner
    }

    /** Reads a key straight from one node's memory, for tests: no routing, no redirects, nothing counted. */
    fun peek(node: String, key: String): String? = data.getValue(node)[key]

    private fun run(store: MutableMap<String, String>, command: List<String>): String? = when (command[0].uppercase()) {
        "GET" -> store[command[1]]
        "SET" -> { store[command[1]] = command[2]; "OK" }
        "INCR" -> ((store[command[1]]?.toLong() ?: 0L) + 1).toString().also { store[command[1]] = it }
        "DEL" -> command.drop(1).count { store.remove(it) != null }.toString()
        "EXISTS" -> command.drop(1).count { it in store }.toString()
        "MSET" -> { command.drop(1).chunked(2).forEach { (k, v) -> store[k] = v }; "OK" }
        else -> throw IllegalArgumentException("the model cluster doesn't know ${command[0]}")
    }

    /** Contiguous ranges of nearly equal size, as redis-cli makes them: 0-5460, 5461-10922 and 10923-16383 for three nodes. */
    private fun initialSplit(): Array<String> {
        val table = Array(SLOTS) { nodes.last() }
        val perNode = SLOTS.toDouble() / nodes.size
        var first = 0
        for ((i, node) in nodes.withIndex()) {
            val last = if (i == nodes.lastIndex) SLOTS - 1 else Math.round(i * perNode + perNode - 1).toInt()
            for (slot in first..last) table[slot] = node
            first = last + 1
        }
        return table
    }

    private companion object {
        const val SLOTS = 16_384
    }
}
