package sfz.redis.l11

object HashSlots {
    const val COUNT = 16_384

    fun crc16(bytes: ByteArray): Int {
        var crc = 0
        for (b in bytes) {
            crc = crc xor ((b.toInt() and 0xFF) shl 8)            // the next byte goes into the top 8 bits
            repeat(8) {
                crc = if (crc and 0x8000 != 0) (crc shl 1) xor 0x1021 else crc shl 1
            }
            crc = crc and 0xFFFF                                  // stay a 16-bit number
        }
        return crc
    }

    fun hashTag(key: String): String {
        val open = key.indexOf('{')
        if (open < 0) return key
        val close = key.indexOf('}', open + 1)                    // the first } after the first {
        if (close < 0 || close == open + 1) return key            // no }, or {} with nothing inside: hash it all
        return key.substring(open + 1, close)
    }

    fun slot(key: String): Int = crc16(hashTag(key).toByteArray(Charsets.UTF_8)) % COUNT   // 14 of the 16 bits
}

class CrossSlotException(message: String) : RuntimeException(message)

class ClusterException(message: String) : RuntimeException(message)

class ClusterRouter(private val cluster: ModelCluster, private val maxRedirects: Int = 5) {
    private val slotOwner = arrayOfNulls<String>(HashSlots.COUNT)

    var movedFollowed = 0
        private set

    var askFollowed = 0
        private set

    init {
        refresh()
    }

    fun refresh() {
        for ((slots, node) in cluster.shards()) for (slot in slots) slotOwner[slot] = node
    }

    fun nodeFor(key: String): String = slotOwner[HashSlots.slot(key)] ?: error("no node for $key")

    fun execute(vararg command: String): String? {
        val args = command.toList()
        val slots = keysOf(args).map(HashSlots::slot).distinct()
        if (slots.size != 1) throw CrossSlotException("keys in ${slots.size} slots: $slots")   // checked before any send
        var node = slotOwner[slots.single()] ?: throw ClusterException("slot ${slots.single()} has no owner")
        var asking = false
        repeat(maxRedirects + 1) {
            when (val reply = cluster.send(node, args, asking)) {
                is NodeReply.Value -> return reply.value
                is NodeReply.Moved -> {
                    slotOwner[reply.slot] = reply.node                // the table was stale: fix it for every later call
                    node = reply.node
                    asking = false
                    movedFollowed++
                }
                is NodeReply.Ask -> {
                    node = reply.node                                 // this command only: the table stays as it is
                    asking = true
                    askFollowed++
                }
                is NodeReply.Error -> throw ClusterException(reply.message)
            }
        }
        throw ClusterException("still redirected after $maxRedirects redirects: ${args[0]} ${args.getOrNull(1)}")
    }
}
