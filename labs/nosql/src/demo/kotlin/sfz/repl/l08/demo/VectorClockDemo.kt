package sfz.repl.l08.demo

/** A vector clock as a sorted map of node -> counter. A missing node counts as 0. */
private typealias Clock = Map<String, Int>

private fun Clock.bump(node: String): Clock = (this + (node to (this[node] ?: 0) + 1)).toSortedMap()
private fun Clock.merge(o: Clock): Clock = (keys + o.keys).associateWith { maxOf(this[it] ?: 0, o[it] ?: 0) }.toSortedMap()
private fun Clock.show() = entries.joinToString(", ", "[", "]") { "(${it.key}, ${it.value})" }

/** How [a] relates to [b]: compare every counter. */
private fun relation(a: Clock, b: Clock): String {
    val nodes = a.keys + b.keys
    val smaller = nodes.any { (a[it] ?: 0) < (b[it] ?: 0) }
    val bigger = nodes.any { (a[it] ?: 0) > (b[it] ?: 0) }
    return when {
        smaller && bigger -> "CONCURRENT: neither saw the other, keep both"
        smaller -> "BEFORE: the second one saw it, drop it"
        bigger -> "AFTER: it saw the second one, keep it"
        else -> "EQUAL"
    }
}

/** Replays the shopping-cart example from section 4.4 of the Dynamo paper with payment-world names. */
fun main() {
    val d1 = emptyMap<String, Int>().bump("Sx")
    println("D1 written by Sx            ${d1.show()}")
    val d2 = d1.bump("Sx")
    println("D2 written by Sx            ${d2.show()}   D1 vs D2: ${relation(d1, d2)}")
    val d3 = d2.bump("Sy")
    println("D3 written by Sy (read D2)  ${d3.show()}")
    val d4 = d2.bump("Sz")
    println("D4 written by Sz (read D2)  ${d4.show()}")
    println("D3 vs D4: ${relation(d3, d4)}")
    val context = d3.merge(d4)
    println("a client reads both, merges the carts, sends context ${context.show()}")
    val d5 = context.bump("Sx")
    println("D5 written by Sx            ${d5.show()}")
    println("D3 vs D5: ${relation(d3, d5)}")
    println("D4 vs D5: ${relation(d4, d5)}")
}
