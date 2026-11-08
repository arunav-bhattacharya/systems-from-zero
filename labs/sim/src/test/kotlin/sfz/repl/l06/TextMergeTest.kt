package sfz.repl.l06

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

class TextMergeTest {
    // ---------- operational transformation ----------

    @Test
    fun `transform moves an insert right past one that landed before it, and leaves it alone otherwise`() {
        assertThat(transform(Insert(6, '!', "b"), Insert(4, '$', "a"))).isEqualTo(Insert(7, '!', "b"))
        assertThat(transform(Insert(4, '$', "a"), Insert(6, '!', "b"))).isEqualTo(Insert(4, '$', "a"))
        // same index: the smaller site name goes first, so only the other one moves
        assertThat(transform(Insert(2, 'y', "b"), Insert(2, 'x', "a"))).isEqualTo(Insert(3, 'y', "b"))
        assertThat(transform(Insert(2, 'x', "a"), Insert(2, 'y', "b"))).isEqualTo(Insert(2, 'x', "a"))
    }

    @Test
    fun `replaying the index of a concurrent insert garbles the note, and transforming it fixes it`() {
        val base = "pay 40"
        val dollar = Insert(4, '$', "a") // site a: "pay $40"
        val bang = Insert(6, '!', "b") //   site b: "pay 40!"
        val atA = applyInsert(base, dollar)
        val atB = applyInsert(base, bang)
        // without transformation, site a applies b's index 6 to text that has grown by one
        assertThat(applyInsert(atA, bang)).isEqualTo("pay $4!0")
        assertThat(applyInsert(atA, transform(bang, dollar))).isEqualTo("pay $40!")
        assertThat(applyInsert(atB, transform(dollar, bang))).isEqualTo("pay $40!")
    }

    @Property(tries = 200)
    fun `OT converges for any two lists of concurrent inserts`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 0, max = 8) baseLength: Int,
        @ForAll @IntRange(min = 1, max = 6) editsA: Int,
        @ForAll @IntRange(min = 1, max = 6) editsB: Int,
    ) {
        val random = Random(seed)
        val base = (1..baseLength).map { ('a' + random.nextInt(26)) }.joinToString("")
        fun edits(site: String, n: Int): List<Insert> {
            var text = base
            return List(n) {
                val op = Insert(random.nextInt(text.length + 1), ('A' + random.nextInt(26)), site)
                text = applyInsert(text, op)
                op
            }
        }
        val a = edits("a", editsA)
        val b = edits("b", editsB)
        val (aAfterB, bAfterA) = transformBoth(a, b)
        val siteA = (a + bAfterA).fold(base, ::applyInsert)
        val siteB = (b + aAfterB).fold(base, ::applyInsert)
        assertThat(siteA).isEqualTo(siteB).hasSize(base.length + editsA + editsB)
    }

    // ---------- the RGA text CRDT ----------

    /** Sites that start from the same text, typed at site "a" and delivered to the others. */
    private fun sites(base: String, vararg names: String): List<RgaText> {
        val origin = RgaText("a")
        val ops = base.mapIndexed { i, c -> origin.insert(i, c) }
        return listOf(origin) + names.map { n -> RgaText(n).also { s -> ops.forEach(s::receive) } }
    }

    @Test
    fun `the same two edits merge correctly with no transformation at all`() {
        val (a, b) = sites("pay 40", "b")
        val dollar = a.insert(4, '$')
        val bang = b.insert(6, '!')
        a.receive(bang)
        b.receive(dollar)
        assertThat(a.text()).isEqualTo("pay $40!")
        assertThat(b.text()).isEqualTo("pay $40!")
    }

    @Test
    fun `two inserts at the same spot land in the same order on both sites, bigger id first`() {
        val (a, b) = sites("ac", "b")
        val x = a.insert(1, 'x')
        val y = b.insert(1, 'y')
        assertThat(x.id.counter).isEqualTo(y.id.counter) // same counter: the site name decides
        a.receive(y)
        b.receive(x)
        assertThat(a.text()).isEqualTo("ayxc").isEqualTo(b.text())
    }

    @Test
    fun `words typed at the same spot on two sites stay whole`() {
        val (a, b) = sites("ref ", "b")
        val typedA = "4417".mapIndexed { i, c -> a.insert(4 + i, c) }
        val typedB = "5310".mapIndexed { i, c -> b.insert(4 + i, c) }
        typedB.forEach(a::receive)
        typedA.forEach(b::receive)
        assertThat(a.text()).isEqualTo(b.text())
        assertThat(a.text()).isIn("ref 44175310", "ref 53104417")
    }

    @Test
    fun `a deleted character stays as a tombstone, so an insert typed next to it still lands`() {
        val (a, b) = sites("void", "b")
        val del = a.delete(3) //       a: "voi"
        val ins = b.insert(4, 'd') //  b: "voidd", typed after the 'd' that a deleted
        a.receive(ins) // arrives at a after the 'd' it refers to is already a tombstone
        b.receive(del)
        assertThat(a.text()).isEqualTo("void").isEqualTo(b.text())
        assertThat(a.nodes).hasSize(5)
        assertThat(a.nodes.count { it.deleted }).isEqualTo(1)
    }

    @Test
    fun `an edit that arrives twice is applied once`() {
        val (a, b) = sites("ab", "b")
        val op = b.insert(2, 'c')
        a.receive(op)
        a.receive(op)
        assertThat(a.text()).isEqualTo("abc")
    }

    @Property(tries = 60)
    fun `three sites converge whatever order the edits arrive in`(@ForAll seed: Long) {
        val random = Random(seed)
        val all = sites("payout", "b", "c")
        val sent = all.associateWith { mutableListOf<Op>() }
        repeat(60) {
            val s = all.random(random)
            val len = s.text().length
            sent.getValue(s) += if (len > 0 && random.nextInt(3) == 0) s.delete(random.nextInt(len))
            else s.insert(random.nextInt(len + 1), ('a' + random.nextInt(26)))
            // now and then one site hears some of another site's edits, in a shuffled order
            if (random.nextInt(4) == 0) {
                val (from, to) = all.shuffled(random)
                sent.getValue(from).shuffled(random).take(random.nextInt(4)).forEach(to::receive)
            }
        }
        // finally everyone receives everything, each in its own shuffled order
        for (to in all) for (from in all) if (from != to) sent.getValue(from).shuffled(random).forEach(to::receive)
        assertThat(all.map { it.text() }.distinct()).hasSize(1)
    }

    @Test
    fun `every character keeps its id forever, so metadata grows with what was ever typed`() {
        val s = RgaText("a")
        repeat(1_000) { s.insert(s.text().length, 'x') }
        repeat(500) { s.delete(0) }
        assertThat(s.text()).hasSize(500)
        assertThat(s.nodes).hasSize(1_000) // 500 tombstones
        // 4-byte counter + 1-byte site name + 1-byte flag, for all 1,000 nodes
        assertThat(s.metadataBytes()).isEqualTo(6_000)
        assertThat(s.metadataBytes() / s.text().length).isEqualTo(12)
    }
}
