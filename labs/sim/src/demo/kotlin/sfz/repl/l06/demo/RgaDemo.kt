package sfz.repl.l06.demo

import kotlin.random.Random

/**
 * The same two edits as OtDemo, with a CRDT: every character gets a permanent id (counter, site),
 * an insert says which character it goes after, and a delete leaves a tombstone. Then 10,000 random
 * edits show what the ids and tombstones cost.
 */
private data class Id(val counter: Int, val site: String) : Comparable<Id> {
    override fun compareTo(other: Id) = compareValuesBy(this, other, Id::counter, Id::site)
    override fun toString() = "$counter$site"
}

private class Node(val id: Id, val char: Char, var deleted: Boolean = false)

private data class RgaIns(val id: Id, val after: Id?, val char: Char) {
    override fun toString() = "insert '$char' named $id after ${after ?: "the start"}"
}

private class Doc(val site: String) {
    val nodes = mutableListOf<Node>()
    var counter = 0
    fun text() = nodes.filterNot { it.deleted }.joinToString("") { it.char.toString() }
    fun insert(index: Int, c: Char): RgaIns {
        val vis = nodes.filterNot { it.deleted }
        return RgaIns(Id(++counter, site), if (index == 0) null else vis[index - 1].id, c).also(::integrate)
    }
    fun delete(index: Int) {
        nodes.filterNot { it.deleted }[index].deleted = true
    }
    fun integrate(op: RgaIns) {
        counter = maxOf(counter, op.id.counter)
        var at = if (op.after == null) 0 else nodes.indexOfFirst { it.id == op.after } + 1
        while (at < nodes.size && nodes[at].id > op.id) at++ // bigger ids at the same spot go first
        nodes.add(at, Node(op.id, op.char))
    }
    fun ids() = nodes.joinToString(" ") { "${it.char}:${it.id}${if (it.deleted) "(deleted)" else ""}" }
    fun metadataBytes() = nodes.sumOf { 4 + it.id.site.length + 1 }
}

fun main() {
    val a = Doc("a")
    val typed = "pay 40".mapIndexed { i, c -> a.insert(i, c) }
    val b = Doc("b").also { d -> typed.forEach(d::integrate) }
    println("both sites: ${a.ids()}")
    val dollar = a.insert(4, '$')
    val bang = b.insert(6, '!')
    println("a sends $dollar")
    println("b sends $bang")
    a.integrate(bang)
    b.integrate(dollar)
    println("site a: \"${a.text()}\"   site b: \"${b.text()}\"")
    println("ids now: ${a.ids()}")

    println()
    val random = Random(11)
    val doc = Doc("a")
    var deletes = 0
    repeat(10_000) {
        val len = doc.text().length
        if (len > 0 && random.nextInt(10) < 4) { doc.delete(random.nextInt(len)); deletes++ }
        else doc.insert(random.nextInt(len + 1), 'x')
    }
    val visible = doc.text().length
    println("10,000 random edits: ${10_000 - deletes} inserts, $deletes deletes")
    println("visible characters: $visible   nodes kept: ${doc.nodes.size}   tombstones: ${doc.nodes.count { it.deleted }}")
    println("metadata: ${doc.metadataBytes()} bytes, %.1f bytes per visible character (plain text: 0)".format(doc.metadataBytes().toDouble() / visible))
}
