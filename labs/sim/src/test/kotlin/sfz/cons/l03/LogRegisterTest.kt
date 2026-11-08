package sfz.cons.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercises 4 to 6: a register on a total order broadcast, checked for linearizability. */
class LogRegisterTest {
    @Test
    fun `the state machine swaps only on a match and always reports the value before`() {
        val r = Replica("r1")
        assertThat(r.apply(Cas(1, "c1", null, "seat-12A:alice"))).isNull()
        assertThat(r.value).isEqualTo("seat-12A:alice")
        assertThat(r.apply(Cas(2, "c2", null, "seat-12A:bob"))).isEqualTo("seat-12A:alice")
        assertThat(r.value).describedAs("expected null, found alice: no swap").isEqualTo("seat-12A:alice")
        assertThat(r.apply(Read(3, "c3"))).isEqualTo("seat-12A:alice")
        assertThat(r.apply(Cas(4, "c1", "seat-12A:alice", "seat-12A:released"))).isEqualTo("seat-12A:alice")
        assertThat(r.value).isEqualTo("seat-12A:released")
        assertThat(r.applied.map { it.id }).containsExactly(1L, 2L, 3L, 4L)
    }

    /** [clients] clients race to claim one key with cas(null -> their name). */
    private fun race(seed: Long, clients: Int = 6): Pair<LogRegister, Map<String, Boolean>> {
        val sim = Sim(seed)
        val net = Network(sim, minMs = 1, maxMs = 20)
        val reg = LogRegister(net)
        val results = mutableMapOf<String, Boolean>()
        for (i in 1..clients) sim.after(sim.random.nextLong(0, 10)) { reg.cas("c$i", null, "c$i") { results["c$i"] = it } }
        sim.run()
        return reg to results
    }

    @Test
    fun `when clients race for a seat, exactly one compare-and-set wins`() {
        for (seed in 1L..200L) {
            val (reg, results) = race(seed)
            assertThat(results).describedAs("seed $seed").hasSize(6)
            val winners = results.filterValues { it }.keys
            assertThat(winners).describedAs("seed $seed").hasSize(1)
            assertThat(reg.replicas.map { it.value }.toSet()).describedAs("every replica agrees").containsExactly(winners.single())
        }
    }

    @Test
    fun `every replica applies the same commands in the same order`() {
        for (seed in 1L..50L) {
            val (reg, _) = race(seed)
            val orders = reg.replicas.map { r -> r.applied.map { it.id } }
            assertThat(orders.toSet()).describedAs("seed $seed").hasSize(1)
        }
    }

    @Test
    fun `consensus from compare-and-set - every proposer gets the same decision`() {
        for (seed in 1L..200L) {
            val sim = Sim(seed)
            val reg = LogRegister(Network(sim, maxMs = 20))
            val decided = mutableMapOf<String, String>()
            val offers = listOf("capture", "void", "capture-partial", "void", "capture")
            offers.forEachIndexed { i, v -> sim.after(sim.random.nextLong(0, 10)) { propose(reg, "c${i + 1}", v) { decided["c${i + 1}"] = it } } }
            sim.run()
            assertThat(decided).describedAs("seed $seed").hasSize(offers.size)
            assertThat(decided.values.toSet()).describedAs("seed $seed").hasSize(1)
            assertThat(offers).contains(decided.values.first())
        }
    }

    /** Clients mixing CAS and reads; reads go through the log, or straight to the home replica. */
    private fun record(seed: Long, localReads: Boolean): List<Op> {
        val sim = Sim(seed)
        val reg = LogRegister(Network(sim, maxMs = 30))
        val ops = mutableListOf<Op>()
        var next = 1
        for (c in 1..3) {
            val client = "c$c"
            var left = 8
            var seen: String? = null
            fun go() {
                if (left-- == 0) return
                sim.after(sim.random.nextLong(0, 10)) {
                    val start = sim.now
                    if (sim.random.nextInt(3) == 0) {
                        val v = "v${next++}"
                        val expected = seen
                        reg.cas(client, expected, v) { ok ->
                            ops += Op(start, sim.now, cas = true, expected = expected, value = v, ok = ok)
                            if (ok) seen = v
                            go()
                        }
                    } else {
                        val read: (String?) -> Unit = { v ->
                            ops += Op(start, sim.now, cas = false, value = v)
                            seen = v
                            go()
                        }
                        if (localReads) reg.localRead(client, read) else reg.read(client, read)
                    }
                }
            }
            go()
        }
        sim.run()
        return ops
    }

    @Test
    fun `compare-and-set and reads through the log are linearizable`() {
        for (seed in 1L..200L) assertThat(linearizable(record(seed, localReads = false))).describedAs("seed $seed").isTrue()
    }

    @Test
    fun `reads that skip the log can return stale values`() {
        val bad = (1L..200L).count { !linearizable(record(it, localReads = true)) }
        assertThat(bad).isPositive()
    }
}
