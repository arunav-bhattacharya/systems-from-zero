package sfz.shard.l03

/** A tiny Redis Cluster: 16 hash slots instead of 16,384, so a test can look at every one. */
const val SLOTS = 16

/** The slot of a key. Redis uses CRC16(key) mod 16384; this model uses MD5 mod 16. Given. */
fun slotOf(key: String): Int = Math.floorMod(hash64(key), SLOTS.toLong()).toInt()

/** What a node answers to GET. */
sealed interface Reply {
    /** The answer: the value, or null if the key doesn't exist. */
    data class Value(val value: String?) : Reply

    /** "Not mine, and it won't be: [node] owns [slot]. Update your map." */
    data class Moved(val slot: Int, val node: String) : Reply

    /** "This slot is moving to [node] and that key has already gone. Ask there, this once." */
    data class Ask(val slot: Int, val node: String) : Reply
}

/**
 * The server side of the cluster, given. Each node keeps its own keys. Slots start in contiguous runs:
 * with nodes A, B, C, slots 0-5 on A, 6-10 on B and 11-15 on C.
 *
 * One slot at a time can migrate. While it does, its owner hands over one key per [tick] (virtual
 * time: nothing happens between ticks), and the slot changes owner when its last key has gone. The
 * answers follow the Redis Cluster spec:
 * - the owner serves a key it still has, and answers ASK for a key of a migrating slot it no longer has;
 * - the target serves a key of the slot it is importing only if the request came after ASKING;
 * - every other node answers MOVED with the owner.
 */
class Cluster(nodeNames: List<String>) {
    private val owner = Array(SLOTS) { nodeNames[it * nodeNames.size / SLOTS] }
    private val stores = nodeNames.associateWith { HashMap<String, String>() }
    private var migrating: Int? = null
    private var target: String? = null

    /** Every request any node has received. */
    var requests = 0
        private set

    /** The slot moving right now, or null. */
    val migratingSlot: Int? get() = migrating

    /** The owner of every slot, as `CLUSTER SHARDS` would report it to a client starting up. */
    fun slotMap(): Array<String> = owner.copyOf()

    /** Setup only: stores [key] on the owner of its slot. */
    fun put(key: String, value: String) {
        stores.getValue(owner[slotOf(key)])[key] = value
    }

    /** Starts moving [slot] from its owner to [to]. */
    fun startMigration(slot: Int, to: String) {
        check(migrating == null) { "one migration at a time" }
        require(owner[slot] != to) { "$to already owns slot $slot" }
        migrating = slot
        target = to
    }

    /** One step of virtual time: move one key (lowest first) of the migrating slot. Returns false if nothing is migrating. */
    fun tick(): Boolean {
        val slot = migrating ?: return false
        val from = stores.getValue(owner[slot])
        val to = stores.getValue(target!!)
        val key = from.keys.filter { slotOf(it) == slot }.minOrNull()
        if (key == null) {
            owner[slot] = target!! // the last key has gone: the target owns the slot from now on
            migrating = null
            target = null
        } else {
            to[key] = from.remove(key)!!
        }
        return true
    }

    /** What [node] answers to `GET key`. [asking] means the client sent ASKING to this node just before. */
    fun get(node: String, key: String, asking: Boolean = false): Reply {
        requests++
        val slot = slotOf(key)
        val store = stores.getValue(node)
        return when {
            owner[slot] == node && migrating == slot && key !in store -> Reply.Ask(slot, target!!)
            owner[slot] == node -> Reply.Value(store[key])
            migrating == slot && target == node && asking -> Reply.Value(store[key])
            else -> Reply.Moved(slot, owner[slot])
        }
    }
}

/**
 * A partition-aware client, like a Redis Cluster client (or a Kafka producer with its metadata, or a
 * token-aware Cassandra driver). It keeps its own copy of the slot map and sends each request straight
 * to the node the map names.
 */
class RoutingClient(private val cluster: Cluster, startingMap: Array<String>) {
    /** slot -> node, the client's own copy. It changes only when a node answers MOVED. */
    val slotMap: Array<String> = startingMap.copyOf()

    /** How many MOVED answers this client has received. */
    var moved = 0
        private set

    /** How many ASK answers this client has received. */
    var asks = 0
        private set

    /**
     * Reads [key]. Send GET to the node `slotMap` names for the key's slot.
     * - Value: return it.
     * - Moved: count it, write the new owner into `slotMap`, and send the GET there.
     * - Ask: count it, and send the GET once to the node named, with `asking = true`. Leave `slotMap` alone:
     *   the slot hasn't moved yet, only this key has.
     * After 5 redirects for one key, throw IllegalStateException (a real client would refresh its map).
     */
    fun get(key: String): String? {
        TODO("send to slotMap[slotOf(key)]; follow MOVED (update the map) and ASK (asking = true, map unchanged)")
    }
}
