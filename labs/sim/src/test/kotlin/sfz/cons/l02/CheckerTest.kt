package sfz.cons.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercise 1: hand-made histories with known answers. `balance` 70 means 70.00. */
class CheckerTest {
    private fun linearizable(h: History) = Linearizability.check(h).linearizable

    /** A witness must hold every op once, respect real time and replay on one register. */
    private fun assertWitness(h: History, order: List<Op>) {
        assertThat(order).containsExactlyInAnyOrderElementsOf(h.ops)
        for (i in order.indices) for (j in i + 1 until order.size) {
            if (order[i].key == order[j].key) assertThat(order[j].end).describedAs("${order[j]} placed after ${order[i]}").isGreaterThanOrEqualTo(order[i].start)
        }
        for (key in h.keys) {
            var state: Int? = null
            for (op in order.filter { it.key == key }) {
                val (ok, next) = Register.step(state, op)
                assertThat(ok).describedAs("$op from $state").isTrue()
                state = next
            }
        }
    }

    @Test
    fun `operations one after another, each seeing the last write, are linearizable`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "ledger".read("balance", 70, 20..30)
            "checkout".write("balance", 40, 40..50)
            "ledger".read("balance", 40, 60..70)
        }
        val r = Linearizability.check(h)
        assertThat(r.linearizable).isTrue()
        assertThat(r.order).containsExactlyElementsOf(h.ops)
    }

    @Test
    fun `a read that starts after a write finished must see it`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "ledger".read("balance", null, 20..30)
        }
        assertThat(linearizable(h)).isFalse()
    }

    @Test
    fun `a read that overlaps a write may return either value`() {
        val old = history {
            "checkout".write("balance", 70, 0..50)
            "ledger".read("balance", null, 10..20)
        }
        val new = history {
            "checkout".write("balance", 70, 0..50)
            "ledger".read("balance", 70, 10..20)
        }
        assertThat(linearizable(old)).isTrue()
        assertThat(linearizable(new)).isTrue()
    }

    @Test
    fun `once a read has returned the new value, a read that starts later can't return the old one`() {
        val h = history {
            "checkout".write("balance", 70, 0..50)
            "ledger".read("balance", 70, 10..20)
            "fraud".read("balance", null, 30..40)
        }
        assertThat(linearizable(h)).isFalse()
        val swapped = history {
            "checkout".write("balance", 70, 0..50)
            "ledger".read("balance", 70, 30..40)
            "fraud".read("balance", null, 10..20)
        }
        assertThat(linearizable(swapped)).isTrue()
    }

    @Test
    fun `the search may have to put a later-starting write first`() {
        // two overlapping writes; the reads after them say 70 was written second
        val h = history {
            "eu".write("balance", 40, 0..30)
            "us".write("balance", 70, 10..40)
            "ledger".read("balance", 70, 50..60)
            "fraud".read("balance", 70, 70..80)
        }
        val r = Linearizability.check(h)
        assertThat(r.linearizable).isTrue()
        assertWitness(h, r.order)
        val back = history {
            "eu".write("balance", 40, 0..30)
            "us".write("balance", 70, 10..40)
            "ledger".read("balance", 70, 50..60)
            "fraud".read("balance", 40, 70..80)
        }
        assertThat(linearizable(back)).isFalse()
    }

    @Test
    fun `two compare-and-sets from the same value can't both succeed`() {
        val both = history {
            "worker-1".cas("lock", null, 1, true, 0..20)
            "worker-2".cas("lock", null, 2, true, 5..25)
        }
        assertThat(linearizable(both)).isFalse()
        val one = history {
            "worker-1".cas("lock", null, 1, true, 0..20)
            "worker-2".cas("lock", null, 2, false, 5..25)
            "worker-2".read("lock", 1, 30..40)
        }
        val r = Linearizability.check(one)
        assertThat(r.linearizable).isTrue()
        assertWitness(one, r.order)
    }

    @Test
    fun `a compare-and-set that fails although the value matched is not linearizable`() {
        val h = history {
            "checkout".write("status", 1, 0..10)
            "capture".cas("status", 1, 2, false, 20..30)
        }
        assertThat(linearizable(h)).isFalse()
    }

    @Test
    fun `keys are checked separately, and one bad key fails the history`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "checkout".write("status", 2, 20..30)
            "ledger".read("status", 2, 40..50)
            "ledger".read("balance", null, 60..70)
        }
        val r = Linearizability.check(h)
        assertThat(r.linearizable).isFalse()
        assertThat(r.order.map { it.key }.toSet()).describedAs("the longest prefix is about the bad key").containsOnly("balance")
    }

    @Test
    fun `a failed check reports the longest prefix it could linearize`() {
        val h = history {
            "checkout".write("balance", 70, 0..10)
            "ledger".read("balance", 70, 20..30)
            "fraud".read("balance", null, 40..50)
        }
        val r = Linearizability.checkKey(h.ops)
        assertThat(r.linearizable).isFalse()
        assertThat(r.order.map { it.id }).containsExactly(0, 1)
        assertThat(r.explored).isPositive()
    }

    @Test
    fun `an empty history is linearizable`() {
        assertThat(Linearizability.checkKey(emptyList()).linearizable).isTrue()
    }
}
