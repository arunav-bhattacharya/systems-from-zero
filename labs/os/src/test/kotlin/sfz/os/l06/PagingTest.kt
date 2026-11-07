package sfz.os.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class PagingTest {
    // touch.c in the lab box: reserve 1 GB with mmap, then write one byte in every 4 KB page
    private val run = Captured.text("/sfz/os/l06/touch-1g.txt")
    private val start = Regex("""at 0x([0-9a-f]+)""").find(run)!!.groupValues[1].toLong(16)
    private val realFaults = Regex("""(\d+) page faults""").find(run)!!.groupValues[1].toLong()
    private val tablesKb = Regex("""page tables (\d+) KB""").findAll(run).map { it.groupValues[1].toLong() }.toList()

    private val oneGb = 1L shl 30

    @Test
    fun `splits an address into four 9-bit indices and a 12-bit offset`() {
        assertThat(Paging.split(0x0000_ffff_4240_1234L)).isEqualTo(Paging.Split(listOf(511, 509, 18, 1), 0x234))
        assertThat(Paging.split(0x1000L)).isEqualTo(Paging.Split(listOf(0, 0, 0, 1), 0))
        assertThat(Paging.split(0xfffL)).isEqualTo(Paging.Split(listOf(0, 0, 0, 0), 4095))
    }

    @Test
    fun `the indices and the offset put back together give the address`() {
        for (va in listOf(0x0000_7f3a_1234_5678L, 0x0000_ffff_4840_0000L, 0x0000_0000_dead_beefL)) {
            val (idx, offset) = Paging.split(va)
            val rebuilt = idx.fold(0L) { acc, i -> (acc shl 9) or i.toLong() } shl 12 or offset.toLong()
            assertThat(rebuilt).isEqualTo(va)
        }
    }

    @Test
    fun `mapping one page creates a table at each level, and its neighbour reuses them`() {
        val pt = PageTable()
        assertThat(pt.lookup(0x5000_1000L)).isNull()
        pt.map(0x5000_1000L, 7)
        assertThat(pt.tables).isEqualTo(4)                         // root, then one new table at levels 1, 2 and 3
        assertThat(pt.lookup(0x5000_1abcL)).isEqualTo(7)           // any byte of the page translates to its frame
        pt.map(0x5000_2000L, 8)
        assertThat(pt.tables).isEqualTo(4)                         // the next page lives in the same level-3 table
        assertThat(pt.lookup(0x5000_3000L)).isNull()
    }

    @Test
    fun `the TLB keeps the most recently used translations`() {
        val tlb = Tlb(2)
        tlb.insert(1, 100)
        tlb.insert(2, 200)
        assertThat(tlb.lookup(1)).isEqualTo(100)                   // page 1 is now the most recent
        tlb.insert(3, 300)                                         // so page 2 is evicted, not page 1
        assertThat(tlb.lookup(2)).isNull()
        assertThat(tlb.lookup(1)).isEqualTo(100)
        assertThat(tlb.size).isEqualTo(2)
    }

    @Test
    fun `touching 1 GB faults once per page, like the lab box run`() {
        val mmu = Mmu(listOf(Region("mmap 1 GB", start, oneGb)))
        for (va in start until start + oneGb step Paging.PAGE_SIZE) mmu.access(va)

        assertThat(mmu.pageFaults).isEqualTo(262_144L)
        assertThat(realFaults - mmu.pageFaults).isBetween(0L, 10L)   // the real run adds a few for printf and friends
        // 512 level-3 tables plus a handful above them: about 2 MB of page tables for 1 GB of memory
        assertThat(mmu.pageTable.tables).isEqualTo(516)
        val realGrowthKb = tablesKb[1] - tablesKb[0]
        assertThat(mmu.pageTable.tables * 4L - realGrowthKb).isBetween(0L, 16L)
    }

    @Test
    fun `the second pass over 1 GB has no faults but misses the TLB on every page`() {
        val mmu = Mmu(listOf(Region("mmap 1 GB", start, oneGb)), tlbEntries = 64)
        repeat(2) { for (va in start until start + oneGb step Paging.PAGE_SIZE) mmu.access(va) }
        assertThat(mmu.pageFaults).isEqualTo(262_144L)              // all from the first pass
        assertThat(mmu.tlbHits).isZero()
        assertThat(mmu.walkReads).isEqualTo(2 * 262_144L * 4)      // four reads for every single access
    }

    @Test
    fun `a TLB holds a loop over 64 pages and falls off a cliff at 65`() {
        fun secondPassHits(pages: Int): Long {
            val mmu = Mmu(listOf(Region("buffer", 0x4000_0000L, 1L shl 20)), tlbEntries = 64)
            repeat(2) { for (p in 0 until pages) mmu.access(0x4000_0000L + p * Paging.PAGE_SIZE) }
            return mmu.tlbHits
        }
        assertThat(secondPassHits(64)).isEqualTo(64L)
        assertThat(secondPassHits(65)).isZero()                    // LRU evicts each page just before it is needed again
    }

    @Test
    fun `reading a page byte by byte costs one fault and then only TLB hits`() {
        val mmu = Mmu(listOf(Region("heap", 0x10_0000L, 1L shl 20)))
        val outcomes = (0 until 4096).map { mmu.access(0x10_0000L + it) }
        assertThat(outcomes.first()).isEqualTo(Outcome.PAGE_FAULT)
        assertThat(outcomes.drop(1)).containsOnly(Outcome.TLB_HIT)
        assertThat(mmu.walkReads).isEqualTo(4L)
    }

    @Test
    fun `an address outside every region is a segfault and maps nothing`() {
        val mmu = Mmu(listOf(Region("heap", 0x10_0000L, 1L shl 20)))
        assertThat(mmu.access(0L)).isEqualTo(Outcome.SEGFAULT)    // the null pointer page
        assertThat(mmu.access(0x10_0000L + (1L shl 20))).isEqualTo(Outcome.SEGFAULT)   // one byte past the end
        assertThat(mmu.segfaults).isEqualTo(2L)
        assertThat(mmu.pageFaults).isZero()
        assertThat(mmu.pageTable.tables).isEqualTo(1)
    }
}
