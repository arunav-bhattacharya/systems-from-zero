package sfz.repl.l06

/**
 * A character's permanent name: a counter, then the site that typed it. Ids compare by counter
 * first and site second, so every site sorts them the same way.
 */
data class CharId(val counter: Int, val site: String) : Comparable<CharId> {
    override fun compareTo(other: CharId): Int = compareValuesBy(this, other, CharId::counter, CharId::site)

    override fun toString() = "$counter$site"
}

/** An edit as it travels between sites. Given. */
sealed interface Op {
    /** Insert [char], named [id], right after the character named [after] (null: at the very start). */
    data class Ins(val id: CharId, val after: CharId?, val char: Char) : Op

    /** Delete the character named [id]. It stays in the list as a tombstone. */
    data class Del(val id: CharId) : Op
}

/**
 * A text CRDT in the style of RGA (replicated growable array). Every character ever typed keeps an
 * id; an insert says which character it goes after, never at which index; a delete only marks the
 * character as gone. No site ever transforms an edit, and any two sites that have received the
 * same edits show the same text, whatever order the edits arrived in.
 *
 * Your job: [integrate] and [integrateDelete]. Local editing, buffering and measuring are given.
 */
class RgaText(val site: String) {
    /** One character in document order. Deleted characters stay, with [deleted] set. */
    class Node(val id: CharId, val char: Char) {
        var deleted = false
    }

    /** Every character ever inserted here, in document order, tombstones included. */
    val nodes: MutableList<Node> = mutableListOf()

    /** The highest counter this site has seen: a new local id is one more (a Lamport clock). */
    private var counter = 0

    /** Edits that arrived before the character they refer to. */
    private val waiting = mutableListOf<Op>()

    /** The text a user sees. Given. */
    fun text(): String = nodes.filterNot { it.deleted }.joinToString("") { it.char.toString() }

    /** Types [char] so that it becomes visible position [index]. Returns the edit to send. Given. */
    fun insert(index: Int, char: Char): Op.Ins {
        val visible = nodes.filterNot { it.deleted }
        require(index in 0..visible.size) { "index $index outside 0..${visible.size}" }
        val op = Op.Ins(CharId(++counter, site), if (index == 0) null else visible[index - 1].id, char)
        integrate(op)
        return op
    }

    /** Deletes the character at visible position [index]. Returns the edit to send. Given. */
    fun delete(index: Int): Op.Del {
        val op = Op.Del(nodes.filterNot { it.deleted }[index].id)
        integrateDelete(op)
        return op
    }

    /** An edit from another site. It waits until the character it refers to has arrived. Given. */
    fun receive(op: Op) {
        waiting += op
        var progress = true
        while (progress) {
            progress = false
            val it = waiting.iterator()
            while (it.hasNext()) {
                val next = it.next()
                val ready = when (next) {
                    is Op.Ins -> next.after == null || has(next.after)
                    is Op.Del -> has(next.id)
                }
                if (ready) {
                    it.remove()
                    when (next) {
                        is Op.Ins -> {
                            counter = maxOf(counter, next.id.counter)
                            integrate(next)
                        }
                        is Op.Del -> integrateDelete(next)
                    }
                    progress = true
                }
            }
        }
    }

    fun has(id: CharId): Boolean = nodes.any { it.id == id }

    /**
     * Metadata this site keeps beyond the characters themselves: per node a 4-byte counter, the
     * site name in UTF-8 and a 1-byte tombstone flag. (The JVM's object overhead is much bigger;
     * this counts only what a compact encoding would have to store.) Given.
     */
    fun metadataBytes(): Int = nodes.sumOf { 4 + it.id.site.toByteArray().size + 1 }

    /**
     * Puts [op]'s character into [nodes].
     *
     * 1. If a node with [Op.Ins.id] is already there, do nothing (the same edit delivered twice).
     * 2. Start just after the node named [Op.Ins.after], or at index 0 when it is null.
     * 3. Skip every node whose id is bigger than [Op.Ins.id]: those are inserts made at the same
     *    place by sites that hadn't seen this one, plus whatever was typed after them, and the
     *    bigger id goes first.
     * 4. Insert the new node there.
     */
    fun integrate(op: Op.Ins) {
        if (has(op.id)) return // a repeat: integrating twice would type the character twice
        // the reference point is a name, not an index, so other sites' edits can't move it
        var at = if (op.after == null) 0 else nodes.indexOfFirst { it.id == op.after } + 1
        // concurrent inserts after the same character, and everything typed after them, have
        // bigger ids (Lamport counters only grow): they go first, on every site
        while (at < nodes.size && nodes[at].id > op.id) at++
        nodes.add(at, Node(op.id, op.char))
    }

    /** Marks the node named [op]'s id as deleted. Never remove it: a later insert may refer to it. */
    fun integrateDelete(op: Op.Del) {
        // a tombstone: the character disappears from text() but keeps its place for later inserts
        nodes.first { it.id == op.id }.deleted = true
    }
}
