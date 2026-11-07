package sfz.kafka.l09

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.kafka.l09.Isolation.READ_COMMITTED
import sfz.kafka.l09.Isolation.READ_UNCOMMITTED

/**
 * The partition model. Several cases replay what a Kafka 4.4 broker did in this lesson's TxnDemo: the same
 * offsets, the same gaps, the same last stable offset.
 */
class TxnPartitionTest {
    private val ledger = 1L // the transactional producer
    private val other = 2L  // a second producer

    private fun TxnPartition.values(isolation: Isolation, from: Long = 0) = read(from, isolation).map { it.value }
    private fun TxnPartition.offsets(isolation: Isolation, from: Long = 0) = read(from, isolation).map { it.offset }

    @Test
    fun `records without a transaction are final at once, for every reader`() {
        val p = TxnPartition()
        assertThat(p.append(other, "a", transactional = false)).isEqualTo(0)
        assertThat(p.append(other, "b", transactional = false)).isEqualTo(1)
        assertThat(p.lastStableOffset()).isEqualTo(2)
        assertThat(p.values(READ_COMMITTED)).containsExactly("a", "b")
        assertThat(p.values(READ_UNCOMMITTED)).containsExactly("a", "b")
    }

    @Test
    fun `a committed transaction is visible, and its marker takes an offset`() {
        val p = TxnPartition()
        p.append(ledger, "a")
        p.append(ledger, "b")
        assertThat(p.commit(ledger)).isEqualTo(2) // the COMMIT marker sits at offset 2
        assertThat(p.append(other, "d", transactional = false)).isEqualTo(3)
        assertThat(p.offsets(READ_COMMITTED)).containsExactly(0, 1, 3) // a gap where the marker is
        assertThat(p.read(0, READ_UNCOMMITTED).map { it.kind }).containsOnly(Entry.Kind.DATA)
    }

    @Test
    fun `an open transaction is visible to read_uncommitted at once, and to read_committed not at all`() {
        val p = TxnPartition()
        p.append(ledger, "a")
        assertThat(p.values(READ_UNCOMMITTED)).containsExactly("a")
        assertThat(p.values(READ_COMMITTED)).isEmpty()
        assertThat(p.lastStableOffset()).isEqualTo(0)
        assertThat(p.logEndOffset()).isEqualTo(1)
    }

    @Test
    fun `an aborted transaction stays in the log, and read_committed skips it`() {
        val p = TxnPartition()
        p.append(ledger, "a"); p.append(ledger, "b"); p.commit(ledger) // 0, 1, marker 2
        p.append(ledger, "c")                                          // 3
        assertThat(p.abort(ledger)).isEqualTo(4)                       // ABORT marker at 4
        p.append(other, "d", transactional = false)                    // 5
        assertThat(p.read(0, READ_UNCOMMITTED).map { "${it.offset}=${it.value}" }).containsExactly("0=a", "1=b", "3=c", "5=d")
        assertThat(p.read(0, READ_COMMITTED).map { "${it.offset}=${it.value}" }).containsExactly("0=a", "1=b", "5=d")
        assertThat(p.lastStableOffset()).isEqualTo(6)
    }

    @Test
    fun `an open transaction holds back everything after it, even records outside any transaction`() {
        val p = TxnPartition()
        p.append(ledger, "a"); p.append(ledger, "b"); p.commit(ledger) // 0, 1, 2
        p.append(ledger, "e")                                          // 3: open
        p.append(other, "f", transactional = false)                    // 4: plain, but behind the open one
        assertThat(p.lastStableOffset()).isEqualTo(3)
        assertThat(p.values(READ_COMMITTED)).containsExactly("a", "b")
        p.commit(ledger)                                               // marker at 5
        assertThat(p.lastStableOffset()).isEqualTo(6)
        assertThat(p.values(READ_COMMITTED)).containsExactly("a", "b", "e", "f")
    }

    @Test
    fun `the oldest open transaction sets the LSO, whoever commits first`() {
        val p = TxnPartition()
        p.append(ledger, "slow-1")   // 0: ledger's transaction opens first
        p.append(other, "fast-1")    // 1: other's transaction
        p.commit(other)              // 2
        assertThat(p.lastStableOffset()).isEqualTo(0) // other committed, but ledger's is still open below it
        assertThat(p.values(READ_COMMITTED)).isEmpty()
        p.abort(ledger)              // 3
        assertThat(p.values(READ_COMMITTED)).containsExactly("fast-1")
        assertThat(p.values(READ_UNCOMMITTED)).containsExactly("slow-1", "fast-1")
    }

    @Test
    fun `a reader that starts in the middle sees only what follows`() {
        val p = TxnPartition()
        p.append(ledger, "a"); p.append(ledger, "b"); p.commit(ledger)
        p.append(ledger, "c"); p.commit(ledger)
        assertThat(p.values(READ_COMMITTED, from = 2)).containsExactly("c")
    }

    @Test
    fun `ending a transaction that is not open is an error`() {
        val p = TxnPartition()
        p.append(ledger, "a", transactional = false)
        assertThatThrownBy { p.commit(ledger) }.isInstanceOf(IllegalStateException::class.java)
        assertThatThrownBy { p.abort(other) }.isInstanceOf(IllegalStateException::class.java)
    }
}
