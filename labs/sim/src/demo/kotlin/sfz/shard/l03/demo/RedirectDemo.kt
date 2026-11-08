package sfz.shard.l03.demo

/** Three nodes, 16 slots. Slot 0 moves from A to C while a client keeps reading it. */
fun main() {
    val slotOf = { key: String -> Math.floorMod(md5(key), 16L).toInt() }
    val owner = Array(16) { listOf("A", "B", "C")[it * 3 / 16] }
    val stores = mapOf("A" to HashMap<String, String>(), "B" to HashMap(), "C" to HashMap())
    val keys = (0 until 300).map { "pay-$it" }.filter { slotOf(it) == 0 }.sorted().take(3)
    keys.forEach { stores.getValue(owner[0])[it] = "value of $it" }
    var migratingTo: String? = null

    // the server side: what node answers to GET key
    fun serve(node: String, key: String, asking: Boolean): String {
        val slot = slotOf(key)
        return when {
            owner[slot] == node && migratingTo != null && key !in stores.getValue(node) -> "ASK $slot $migratingTo"
            owner[slot] == node -> "\"${stores.getValue(node)[key]}\""
            migratingTo == node && asking -> "\"${stores.getValue(node)[key]}\""
            else -> "MOVED $slot ${owner[slot]}"
        }
    }

    // the client: its own slot map; MOVED updates it, ASK doesn't
    val slotMap = owner.copyOf()
    fun get(key: String) {
        var node = slotMap[slotOf(key)]
        var asking = false
        val trace = StringBuilder("GET $key")
        while (true) {
            val reply = serve(node, key, asking)
            trace.append(" -> ${if (asking) "ASKING, " else ""}$node: $reply")
            val parts = reply.split(" ")
            when (parts[0]) {
                "MOVED" -> { slotMap[parts[1].toInt()] = parts[2]; node = parts[2]; asking = false }
                "ASK" -> { node = parts[2]; asking = true }
                else -> break
            }
        }
        println("  $trace   (client map: slot 0 on ${slotMap[0]})")
    }

    println("before the migration")
    keys.forEach(::get)
    println("slot 0 starts moving to C; ${keys[0]} has been copied")
    migratingTo = "C"
    stores.getValue("C")[keys[0]] = stores.getValue("A").remove(keys[0])!!
    keys.forEach(::get)
    println("the rest are copied, and C owns slot 0")
    keys.drop(1).forEach { stores.getValue("C")[it] = stores.getValue("A").remove(it)!! }
    owner[0] = "C"
    migratingTo = null
    keys.forEach(::get)
}
