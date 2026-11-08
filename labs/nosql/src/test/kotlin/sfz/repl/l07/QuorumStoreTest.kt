package sfz.repl.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

class QuorumStoreTest {
    private val key = "ACCT#A-1001"

    private fun ok(r: ReadResult): ReadResult.Ok = r as ReadResult.Ok

    @Test
    fun `a write needs W replicas up, and stores nothing when it can't get them`() {
        val s = QuorumStore(3)
        s.fail("C")
        assertThat(s.write(key, "10000", w = 2)).isEqualTo(WriteResult.Ok(2))
        s.fail("B")
        assertThat(s.write(key, "7000", w = 2)).isEqualTo(WriteResult.Unavailable)
        // the coordinator didn't even try: A still has the first value
        assertThat(s.valueAt("A", key)?.value).isEqualTo("10000")
        assertThat(s.write(key, "7000", w = 1)).isEqualTo(WriteResult.Ok(1))
    }

    @Test
    fun `a write that reaches fewer than W replicas times out but is not rolled back`() {
        val s = QuorumStore(3)
        val result = s.write(key, "7000", w = 2, reaches = listOf("A"))
        assertThat(result).isEqualTo(WriteResult.TimedOut(1))
        // the "failed" write is on A, and a read that asks A will return it
        assertThat(s.valueAt("A", key)?.value).isEqualTo("7000")
        assertThat(s.valueAt("B", key)).isNull()
        assertThat(ok(s.read(key, r = 1, order = listOf("A", "B", "C"))).value?.value).isEqualTo("7000")
    }

    @Test
    fun `a read keeps the version with the newest timestamp`() {
        val s = QuorumStore(3)
        s.write(key, "10000", w = 3)
        s.write(key, "7000", w = 1, reaches = listOf("C"))
        val read = ok(s.read(key, r = 2, order = listOf("B", "C", "A")))
        assertThat(read.value?.value).isEqualTo("7000")
        assertThat(read.value!!.timestamp).isGreaterThan(s.valueAt("A", key)!!.timestamp)
    }

    @Test
    fun `W=1 then R=1 can return a stale value`() {
        val s = QuorumStore(3)
        s.write(key, "10000", w = 3)
        s.fail("C")
        assertThat(s.write(key, "7000", w = 1)).isEqualTo(WriteResult.Ok(2))
        s.recover("C")
        // C came back without the write; a read of one replica that happens to be C is stale
        val read = ok(s.read(key, r = 1, order = listOf("C", "A", "B")))
        assertThat(read.value?.value).isEqualTo("10000")
        assertThat(read.repaired).isEmpty()
    }

    @Test
    fun `R=2 sees the new value and read repair fixes the stale replica it asked`() {
        val s = QuorumStore(3)
        s.write(key, "10000", w = 3)
        s.fail("C")
        s.write(key, "7000", w = 1)
        s.recover("C")
        val read = ok(s.read(key, r = 2, order = listOf("C", "A", "B")))
        assertThat(read.value?.value).isEqualTo("7000")
        assertThat(read.repaired).containsExactly("C")
        assertThat(s.valueAt("C", key)?.value).isEqualTo("7000")
        // now even a read of C alone is fresh
        assertThat(ok(s.read(key, r = 1, order = listOf("C"))).value?.value).isEqualTo("7000")
    }

    @Test
    fun `read repair only fixes the replicas the read asked`() {
        val s = QuorumStore(3)
        s.write(key, "7000", w = 1, reaches = listOf("A"))
        val read = ok(s.read(key, r = 2, order = listOf("A", "B", "C")))
        assertThat(read.repaired).containsExactly("B")
        assertThat(s.valueAt("B", key)?.value).isEqualTo("7000")
        assertThat(s.valueAt("C", key)).isNull()
        // nobody has the other key: an empty answer, and nothing to repair
        assertThat(s.read("ACCT#A-9999", r = 2)).isEqualTo(ReadResult.Ok(null, emptyList()))
    }

    @Test
    fun `a read needs R replicas up and skips the ones that are down`() {
        val s = QuorumStore(3)
        s.write(key, "10000", w = 3)
        s.fail("A")
        val read = ok(s.read(key, r = 2, order = listOf("A", "B", "C")))
        assertThat(read.value?.value).isEqualTo("10000")
        s.fail("B")
        assertThat(s.read(key, r = 2)).isEqualTo(ReadResult.Unavailable)
        assertThat(ok(s.read(key, r = 1)).value?.value).isEqualTo("10000")
    }

    @Test
    fun `staleReadPossible is true exactly when R + W is at most N`() {
        for (n in 1..5) for (r in 1..n) for (w in 1..n) {
            assertThat(QuorumStore.staleReadPossible(n, r, w)).`as`("N=$n R=$r W=$w").isEqualTo(r + w <= n)
        }
    }

    @Test
    fun `with R + W greater than N every read sees the last acknowledged write`() {
        // 2,000 random steps: one replica at a time may be down, messages may be lost
        val random = Random(42)
        val s = QuorumStore(3)
        var lastAcked = 0L
        repeat(2_000) { step ->
            when (random.nextInt(4)) {
                0 -> {
                    s.names.forEach(s::recover)
                    s.fail(s.names.random(random))
                }
                1 -> s.names.forEach(s::recover)
                else -> {}
            }
            val reaches = s.names.filter { random.nextInt(4) != 0 } // about a quarter of messages lost
            val wrote = s.write(key, "v$step", w = 2, reaches = reaches)
            if (wrote is WriteResult.Ok) lastAcked = s.names.mapNotNull { s.valueAt(it, key)?.timestamp }.max()
            val read = s.read(key, r = 2, order = s.names.shuffled(random))
            if (read is ReadResult.Ok && lastAcked > 0) {
                assertThat(read.value!!.timestamp).`as`("step $step").isGreaterThanOrEqualTo(lastAcked)
            }
        }
    }
}
