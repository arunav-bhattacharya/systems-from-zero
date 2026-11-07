package sfz.redis.l11

/** How Redis Cluster maps a key to one of its 16,384 hash slots. */
object HashSlots {
    const val COUNT = 16_384

    /**
     * CRC16 in the XMODEM variant, which the cluster spec names: polynomial 0x1021, initial value 0,
     * no reflection, no final XOR. For each byte `b`: `crc = crc xor ((b and 0xFF) shl 8)`, then 8 times:
     * if bit 15 of `crc` is set, `crc = (crc shl 1) xor 0x1021`, otherwise `crc = crc shl 1`; keep the low
     * 16 bits (`and 0xFFFF`). The spec's check value: "123456789" gives 0x31C3.
     */
    fun crc16(bytes: ByteArray): Int {
        TODO("lesson 11 lab: CRC16/XMODEM, bit by bit")
    }

    /**
     * The part of [key] that is hashed. If the key has a `{`, a `}` somewhere after it, and at least one
     * character between the first `{` and the first `}` after it, only those characters are hashed:
     * `{merchant:7}:payments` hashes `merchant:7`. Otherwise the whole key is hashed: `foo{}{bar}` hashes
     * all of `foo{}{bar}`, because the first `{` is followed directly by `}`.
     */
    fun hashTag(key: String): String {
        TODO("lesson 11 lab: find the hash tag, or use the whole key")
    }

    /** The slot of [key]: the CRC16 of its hashed part (as UTF-8 bytes), modulo [COUNT]. */
    fun slot(key: String): Int {
        TODO("lesson 11 lab: crc16 of the hash tag, mod 16384")
    }
}

/** The client refused a multi-key command whose keys are in different slots, before sending it anywhere. */
class CrossSlotException(message: String) : RuntimeException(message)

/** A node answered with an error, or the client gave up after too many redirects. */
class ClusterException(message: String) : RuntimeException(message)

/**
 * The routing half of a cluster-aware client such as Jedis's `RedisClusterClient` or Lettuce's
 * `RedisClusterClient`: it keeps its own copy of the slot table, sends each command straight to the
 * node that owns its slot, and follows MOVED and ASK when the table is out of date.
 */
class ClusterRouter(private val cluster: ModelCluster, private val maxRedirects: Int = 5) {
    /** This client's own copy of the slot table: the node it believes owns each slot. */
    private val slotOwner = arrayOfNulls<String>(HashSlots.COUNT)

    /** How many MOVED replies this client has followed. */
    var movedFollowed = 0
        private set

    /** How many ASK replies this client has followed. */
    var askFollowed = 0
        private set

    init {
        refresh()
    }

    /** Loads the whole slot table from the cluster, as a client does when it starts (`CLUSTER SHARDS`). Done for you. */
    fun refresh() {
        for ((slots, node) in cluster.shards()) for (slot in slots) slotOwner[slot] = node
    }

    /** The node this client would send [key]'s commands to right now. Done for you. */
    fun nodeFor(key: String): String = slotOwner[HashSlots.slot(key)] ?: error("no node for $key")

    /**
     * Runs [command] (for example `"SET", "payment:42", "approved"`) on the right node and returns the value.
     *
     * 1. Find the keys with [keysOf] and their slots with [HashSlots.slot]. If they are in more than one
     *    slot, throw [CrossSlotException] without sending anything: no node could run it.
     * 2. Send it to the node in [slotOwner] for that slot: `cluster.send(node, command.toList(), asking)`.
     * 3. Act on the reply, and send again, at most [maxRedirects] times after the first try:
     *    - [NodeReply.Value]: return its value.
     *    - [NodeReply.Moved]: the slot lives elsewhere now. Write the new owner into [slotOwner], count one
     *      in [movedFollowed], and send to that node.
     *    - [NodeReply.Ask]: the slot is moving. Send this one command to that node with `asking = true` and
     *      count one in [askFollowed]. Leave [slotOwner] alone: the next command for the slot still goes
     *      to the old owner, which may still have its key.
     *    - [NodeReply.Error]: throw [ClusterException] with the node's message.
     * 4. Still redirected after [maxRedirects]: throw [ClusterException].
     */
    fun execute(vararg command: String): String? {
        TODO("lesson 11 lab: route by slot, follow MOVED and ASK")
    }
}
