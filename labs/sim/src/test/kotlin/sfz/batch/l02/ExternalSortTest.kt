package sfz.batch.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.junit.jupiter.api.io.TempDir
import java.nio.file.Files
import java.nio.file.Path
import kotlin.random.Random

class ExternalSortTest {
    @TempDir
    lateinit var tmp: Path

    /** Shuffled keys: "k000000" to "k(n-1)", each once, in a fixed random order. */
    private fun shuffledKeys(n: Int): List<String> = (0 until n).map { "k%06d".format(it) }.shuffled(Random(42))

    private fun lines(run: Path): List<String> = Files.readAllLines(run)

    @Test
    fun `each merge pass turns r runs into ceil(r over fanIn)`() {
        assertThat(mergePasses(100, 16)).isEqualTo(2)        // 100 -> 7 -> 1
        assertThat(mergePasses(100, 128)).isEqualTo(1)
        assertThat(mergePasses(100, 2)).isEqualTo(7)         // 100 -> 50 -> 25 -> 13 -> 7 -> 4 -> 2 -> 1
        assertThat(mergePasses(16, 16)).isEqualTo(1)
        assertThat(mergePasses(17, 16)).isEqualTo(2)
        assertThat(mergePasses(1, 16)).isEqualTo(0)
        assertThat(mergePasses(0, 16)).isEqualTo(0)
    }

    @Test
    fun `run generation writes sorted runs of at most runSize lines`() {
        val store = RunStore(tmp.resolve("runs"))
        val keys = shuffledKeys(10_500)
        val runs = ExternalSorter(runSize = 1_000, fanIn = 16, store = store).writeRuns(keys.asSequence())
        assertThat(runs).hasSize(11)                                           // ceil(10,500 / 1,000)
        assertThat(store.runsWritten).isEqualTo(11)
        for (run in runs) {
            val r = lines(run)
            assertThat(r.size).isLessThanOrEqualTo(1_000)
            assertThat(r).isSorted()
        }
        assertThat(runs.flatMap(::lines).sorted()).isEqualTo(keys.sorted())   // nothing lost, nothing added
    }

    @Test
    fun `one merge reads all its runs at once and leaves one sorted run`() {
        val store = RunStore(tmp.resolve("runs"))
        val sorter = ExternalSorter(runSize = 250, fanIn = 4, store = store)
        val keys = shuffledKeys(1_000) + listOf("k000007", "k000007")          // duplicates must survive
        val runs = sorter.writeRuns(keys.asSequence())
        assertThat(runs).hasSize(5)
        val merged = sorter.mergeGroup(runs.take(4))
        assertThat(store.maxOpenAtOnce).isEqualTo(4)
        assertThat(store.openNow).isZero()                                    // every input closed again
        assertThat(lines(merged)).isSorted().hasSize(1_000)
        assertThat(store.files()).containsExactlyInAnyOrder(merged, runs[4])  // the inputs were deleted
        assertThrows<IllegalArgumentException> { sorter.mergeGroup(List(5) { merged }) }         // more than fanIn
    }

    @Test
    fun `the sort's runs and passes match the formula for any fan-in`() {
        val keys = shuffledKeys(20_000)
        for ((fanIn, passes) in listOf(2 to 7, 16 to 2, 128 to 1)) {
            val store = RunStore(tmp.resolve("fan-in-$fanIn"))
            val result = ExternalSorter(runSize = 200, fanIn = fanIn, store = store).sort(keys.asSequence())
            assertThat(result.runs).isEqualTo(100)
            assertThat(result.mergePasses).isEqualTo(passes).isEqualTo(mergePasses(100, fanIn))
            assertThat(lines(result.output!!)).isEqualTo(keys.sorted())
            assertThat(store.maxOpenAtOnce).isLessThanOrEqualTo(fanIn)
            assertThat(store.files()).containsExactly(result.output)            // only the answer is left
        }
    }

    @Test
    fun `every merge pass reads and writes every line again`() {
        val store = RunStore(tmp.resolve("runs"))
        val result = ExternalSorter(runSize = 100, fanIn = 4, store = store).sort(shuffledKeys(6_400).asSequence())
        assertThat(result.runs).isEqualTo(64)                                  // 64 -> 16 -> 4 -> 1
        assertThat(result.mergePasses).isEqualTo(3)
        assertThat(store.runsWritten).isEqualTo(64 + 16 + 4 + 1)
        assertThat(store.linesWritten).isEqualTo(6_400L * (1 + 3))            // the runs, then once per pass
    }

    @Test
    fun `sorting and hashing give the same counts, and only sorting fits in a small memory`() {
        val keys = AccessLog.lines(200_000, distinctPaths = 100_000).map { field(it, 7)!! }.toList()
        val expected = keys.groupingBy { it }.eachCount().mapValues { it.value.toLong() }

        // about 60,000 distinct paths at about 124 bytes each need over 7 MB: 1 MB is not enough
        val small = HashCounter(budgetBytes = 1L shl 20)
        val e = assertThrows<MemoryBudgetExceeded> { keys.forEach(small::add) }
        assertThat(e.distinctKeys).isBetween(8_000, 9_000)

        // the sorter holds 5,000 lines at a time (well under 1 MB) and still counts every key
        val sorter = ExternalSorter(runSize = 5_000, fanIn = 16, store = RunStore(tmp.resolve("runs")))
        val byMerging = countBySorting(keys.asSequence(), sorter)
        assertThat(byMerging.associate { it.key to it.count }).isEqualTo(expected)
        assertThat(byMerging.map { it.key }).isSorted()

        val big = HashCounter(budgetBytes = 64L shl 20)
        keys.forEach(big::add)
        assertThat(big.counts()).isEqualTo(expected)
        assertThat(topN(byMerging, 3)).isEqualTo(topN(big.counts().map { KeyCount(it.key, it.value) }, 3))
    }

    @Test
    fun `the sorter's run count follows from the input size`() {
        val sorter = ExternalSorter(runSize = 5_000, fanIn = 16, store = RunStore(tmp.resolve("runs")))
        val result = sorter.sort(AccessLog.lines(200_000, distinctPaths = 100_000).map { field(it, 7)!! })
        assertThat(result.runs).isEqualTo(40)                                  // 200,000 / 5,000
        assertThat(result.mergePasses).isEqualTo(2)                            // 40 -> 3 -> 1
        assertThat(ExternalSorter(10, 2, RunStore(tmp.resolve("empty"))).sort(emptySequence()))
            .isEqualTo(SortResult(null, 0, 0))
    }
}
