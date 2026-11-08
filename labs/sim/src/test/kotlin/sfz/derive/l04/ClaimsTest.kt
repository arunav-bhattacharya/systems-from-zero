package sfz.derive.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercises 1 and 2: routing by key, and one processor per partition deciding in order. */
class ClaimsTest {
    private val claims = Workload.claims(seed = 42)          // 2,000 users want 200 handles

    @Test
    fun `a key always lands on the same partition, inside the range`() {
        val keys = (0 until 1_000).map { "name-$it" }
        for (k in keys) {
            val p = partitionFor(k, 8)
            assertThat(p).isBetween(0, 7)
            assertThat(partitionFor(k, 8)).isEqualTo(p)
        }
        assertThat(keys.map { partitionFor(it, 8) }.toSet()).hasSize(8)   // and the keys spread out
    }

    @Test
    fun `a key whose hashCode is Int MIN_VALUE still gets a valid partition`() {
        assertThat("polygenelubricants".hashCode()).isEqualTo(Int.MIN_VALUE)
        assertThat(partitionFor("polygenelubricants", 6)).isEqualTo(Math.floorMod(Int.MIN_VALUE, 6))
    }

    @Test
    fun `the processor grants a free handle and rejects the next claimant, naming the holder`() {
        val p = ClaimProcessor()
        assertThat(p.decide(Claim("r1", "u-ana", "ana"))).isEqualTo(Granted("r1", "ana", "u-ana"))
        assertThat(p.decide(Claim("r2", "u-bob", "ana"))).isEqualTo(Rejected("r2", "ana", "u-ana"))
        assertThat(p.decide(Claim("r3", "u-bob", "bob"))).isEqualTo(Granted("r3", "bob", "u-bob"))
    }

    @Test
    fun `a redelivered claim gets the answer it got the first time`() {
        val p = ClaimProcessor()
        p.decide(Claim("r1", "u-ana", "ana"))
        val second = p.decide(Claim("r2", "u-bob", "ana"))
        assertThat(p.decide(Claim("r2", "u-bob", "ana"))).isEqualTo(second)      // same request, same answer
        assertThat(p.decide(Claim("r1", "u-ana", "ana"))).isEqualTo(Granted("r1", "ana", "u-ana"))
    }

    @Test
    fun `a user asking again for a handle they already hold gets it again`() {
        val p = ClaimProcessor()
        p.decide(Claim("r1", "u-ana", "ana"))
        assertThat(p.decide(Claim("r9", "u-ana", "ana"))).isEqualTo(Granted("r9", "ana", "u-ana"))
    }

    @Test
    fun `a fresh processor that replays the partition from offset 0 makes the same decisions`() {
        val partition = claims.filter { partitionFor(it.username, 8) == 3 }
        val first = ClaimProcessor().let { p -> partition.map(p::decide) }
        val replayed = ClaimProcessor().let { p -> partition.map(p::decide) }
        assertThat(replayed).isEqualTo(first)
    }

    @Test
    fun `check-then-insert from 64 servers grants some handles twice`() {
        val run = checkThenInsert(claims, servers = 64, seed = 1)
        assertThat(run.decisions).hasSize(claims.size)
        assertThat(run.duplicates).isGreaterThan(0)
    }

    @Test
    fun `through a log keyed by the handle, no handle is ever granted twice`() {
        val run = throughLog(claims, clients = 64, partitions = 8, seed = 1)
        assertThat(run.decisions).hasSize(claims.size)
        assertThat(run.decisions.map { it.requestId }.toSet()).hasSize(claims.size)   // one answer per request
        assertThat(run.duplicates).isZero()
        assertThat(run.granted).isEqualTo(claims.map { it.username }.toSet().size)     // one owner per wanted handle
    }

    @Test
    fun `keyed by userId instead, the same log grants handles twice again`() {
        val run = throughLog(claims, clients = 64, partitions = 8, seed = 1, keyOf = Claim::userId)
        assertThat(run.duplicates).isGreaterThan(0)
    }

    @Test
    fun `with one partition the key does not matter, but every claim waits behind every other`() {
        val one = throughLog(claims, clients = 64, partitions = 1, seed = 1, keyOf = Claim::userId)
        val eight = throughLog(claims, clients = 64, partitions = 8, seed = 1)
        assertThat(one.duplicates).isZero()
        assertThat(percentile(one.waits, 0.99)).isGreaterThan(percentile(eight.waits, 0.99))
    }
}
