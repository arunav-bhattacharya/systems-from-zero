package sfz.shard.l02.demo

/** Black Friday: one merchant takes a fifth of all payments. Spread the KEYS evenly, and see what happens to the LOAD. */
fun main() {
    val nodes = (1..6).map { "node-$it" }
    val tokens = ring(nodes, 256) // a well-balanced ring: every node owns close to 1/6
    fun owner(key: String) = (tokens.ceilingEntry(position(key)) ?: tokens.firstEntry()).value

    // one second of writes: 20,000 payments over 2,000 merchants, but M-0042 takes 4,000 of them
    val payments = (0 until 20_000).map { i -> (if (i % 5 == 0) "M-0042" else "M-%04d".format(1_000 + i % 1_999)) to "pay-$i" }

    fun report(title: String, keyOf: (String, String) -> String) {
        val perKey = payments.groupingBy { (m, p) -> keyOf(m, p) }.eachCount()
        val perNode = payments.groupingBy { (m, p) -> owner(keyOf(m, p)) }.eachCount().toSortedMap()
        val hottest = perKey.maxBy { it.value }
        println(title)
        println("  writes per node: $perNode")
        println("  busiest key: ${hottest.key} with ${hottest.value} writes; keys over 1,000: ${perKey.count { it.value > 1_000 }}")
    }
    report("partition key MERCH#<merchant>:") { m, _ -> "MERCH#$m" }
    // write sharding: a suffix calculated from the payment id, 0 to 9
    report("partition key MERCH#<merchant>#<shard of 10>:") { m, p -> "MERCH#$m#${Math.floorMod(position(p), 10L)}" }
}
