package sfz.cons.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.cons.l01.Model.CAUSAL
import sfz.cons.l01.Model.EVENTUAL
import sfz.cons.l01.Model.LINEARIZABLE
import sfz.cons.l01.Model.MONOTONIC_READS
import sfz.cons.l01.Model.READ_YOUR_WRITES
import sfz.cons.l01.Model.SEQUENTIAL

/**
 * One small history per rung of the ladder. Keys are payment fields and values are small numbers:
 * `balance` 70 means 70.00, `status` 1 means authorized, 2 captured, 3 refunded.
 */
class ModelsTest {
    private val everything = Model.entries.toSet()

    @Test
    fun `the two order relations`() {
        val h = history {
            "A".write("x", 1, 0..10)
            "A".read("x", 1, 20..30)
            "B".read("x", 1, 5..25)
        }
        val (a1, b1, a2) = h.ops
        assertThat(realTime(a1, a2)).isTrue()
        assertThat(realTime(a1, b1)).describedAs("they overlap").isFalse()
        assertThat(realTime(b1, a1)).isFalse()
        assertThat(programOrder(a1, a2)).isTrue()
        assertThat(programOrder(a2, a1)).isFalse()
        assertThat(programOrder(a1, b1)).describedAs("different processes").isFalse()
    }

    @Test
    fun `causal order is program order plus reads-from, made transitive`() {
        val h = history {
            "A".write("question", 1, 0..10)
            "B".read("question", 1, 20..30)
            "B".write("answer", 2, 40..50)
            "C".read("answer", 2, 60..70)
            "C".read("question", null, 80..90)
            "D".write("other", 9, 0..100)
        }
        val before = causalOrder(h)
        val op = h.ops.associateBy { it.id }
        val aw = op.getValue(0)
        val br = op.getValue(1)
        val bw = op.getValue(2)
        val cr1 = op.getValue(3)
        val cr2 = op.getValue(4)
        val dw = op.getValue(5)
        assertThat(before(aw, br)).describedAs("reads-from").isTrue()
        assertThat(before(br, bw)).describedAs("program order").isTrue()
        assertThat(before(aw, cr2)).describedAs("transitive: A's question caused C's second read").isTrue()
        assertThat(before(cr1, aw)).isFalse()
        assertThat(before(dw, cr1)).describedAs("D's write is concurrent with everything").isFalse()
        assertThat(before(aw, dw)).isFalse()
    }

    @Test
    fun `a store that behaves like one copy satisfies every model`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "ledger".read("balance", 70, 20..30)
            "checkout".read("balance", 70, 40..50)
        }
        assertThat(classify(h)).isEqualTo(everything)
    }

    @Test
    fun `a read that starts after a write finished and misses it is sequential but not linearizable`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "ledger".read("balance", null, 20..30)
        }
        assertThat(classify(h)).isEqualTo(everything - LINEARIZABLE)
    }

    @Test
    fun `a read that overlaps a write may return the old or the new value`() {
        val old = history {
            "checkout".write("status", 2, 0..50)
            "ledger".read("status", null, 10..20)
            "fraud".read("status", 2, 30..40)
        }
        assertThat(classify(old)).contains(LINEARIZABLE)
    }

    @Test
    fun `once one read returns the new value, a read that starts later may not return the old one`() {
        val h = history {
            "checkout".write("status", 2, 0..50)
            "ledger".read("status", 2, 10..20)
            "fraud".read("status", null, 30..40)
        }
        assertThat(classify(h)).isEqualTo(everything - LINEARIZABLE)
    }

    @Test
    fun `two readers that see concurrent writes in opposite orders are causal but not sequential`() {
        val h = history {
            "eu".write("status", 2, 0..10)
            "us".write("status", 3, 0..10)
            "ledger".read("status", 2, 20..30)
            "ledger".read("status", 3, 40..50)
            "fraud".read("status", 3, 20..30)
            "fraud".read("status", 2, 40..50)
        }
        assertThat(classify(h)).isEqualTo(setOf(CAUSAL, READ_YOUR_WRITES, MONOTONIC_READS, EVENTUAL))
    }

    @Test
    fun `seeing the reply without the question it answers breaks causal consistency only`() {
        val h = history {
            "agent".write("question", 1, 0..10)
            "merchant".read("question", 1, 20..30)
            "merchant".write("answer", 2, 40..50)
            "auditor".read("answer", 2, 60..70)
            "auditor".read("question", null, 80..90)
        }
        assertThat(classify(h)).isEqualTo(setOf(READ_YOUR_WRITES, MONOTONIC_READS, EVENTUAL))
    }

    @Test
    fun `missing your own write breaks read your writes`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "checkout".read("balance", null, 20..30)
        }
        assertThat(classify(h)).isEqualTo(setOf(MONOTONIC_READS, EVENTUAL))
    }

    @Test
    fun `seeing a value and then not seeing it breaks monotonic reads`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "ledger".read("balance", 70, 20..30)
            "ledger".read("balance", null, 40..50)
        }
        assertThat(classify(h)).isEqualTo(setOf(READ_YOUR_WRITES, EVENTUAL))
    }

    @Test
    fun `a value that flips back and forth breaks monotonic reads even with two writers`() {
        val h = history {
            "eu".write("status", 2, 0..10)
            "us".write("status", 3, 0..10)
            "ledger".read("status", 3, 20..30)
            "ledger".read("status", 2, 40..50)
            "ledger".read("status", 3, 60..70)
        }
        assertThat(satisfies(h, MONOTONIC_READS)).isFalse()
        assertThat(satisfies(h, READ_YOUR_WRITES)).isTrue()
    }

    @Test
    fun `every finite history is eventually consistent, however stale`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "checkout".read("balance", null, 1_000..1_010)
            "checkout".read("balance", null, 60_000..60_010)
        }
        assertThat(satisfies(h, EVENTUAL)).isTrue()
        assertThat(satisfies(h, READ_YOUR_WRITES)).isFalse()
    }

    @Test
    fun `linearizability is checked across keys too`() {
        // each key on its own is fine; together they need status before balance and balance before status
        val h = history {
            "A".write("status", 2, 0..10)
            "A".read("balance", null, 20..30)
            "B".write("balance", 70, 0..10)
            "B".read("status", null, 20..30)
        }
        assertThat(satisfies(h, LINEARIZABLE)).isFalse()
        assertThat(satisfies(h, SEQUENTIAL)).isFalse()
        assertThat(satisfies(h, CAUSAL)).isTrue()
    }
}
