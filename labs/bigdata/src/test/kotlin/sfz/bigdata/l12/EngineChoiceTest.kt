package sfz.bigdata.l12

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

class EngineChoiceTest {
    private val MB = 1_000_000L
    // a laptop: 10 cores decoding Parquet at 500 MB/s each, fed by a 3 GB/s NVMe disk
    private val laptop = Machine(cores = 10, memoryBytes = 16 * GB, decodeBytesPerSecondPerCore = 500 * MB, ioBytesPerSecond = 3 * GB)
    // a big cloud VM reading object storage at 1.5 GB/s
    private val vm = Machine(cores = 64, memoryBytes = 256 * GB, decodeBytesPerSecondPerCore = 500 * MB, ioBytesPerSecond = 1_500 * MB)

    // 4 TB of payments over 3 years, 60 columns; the finance report reads 4 columns of the last 30 days
    private val report = Workload("monthly finance report", tableBytes = 4 * TB, partitionsRead = 30.0 / 1095,
        columnsRead = 4.0 / 60, workingSetBytes = 2 * GB, timeBudgetSeconds = 60.0)

    @Test
    fun `bytesRead prunes partitions and columns before anything else`() {
        assertThat(EngineChoice.bytesRead(report)).isCloseTo(7_305_936_073L, within(1L))
        assertThat(EngineChoice.bytesRead(report.copy(partitionsRead = 1.0, columnsRead = 1.0))).isEqualTo(4 * TB)
    }

    @Test
    fun `a scan runs at the speed of its slowest stage`() {
        assertThat(EngineChoice.scanBytesPerSecond(laptop)).describedAs("disk-bound").isEqualTo(3 * GB)
        assertThat(EngineChoice.scanBytesPerSecond(laptop.copy(cores = 2))).describedAs("CPU-bound").isEqualTo(1 * GB)
        assertThat(EngineChoice.scanBytesPerSecond(vm)).describedAs("network-bound").isEqualTo(1_500 * MB)
    }

    @Test
    fun `users running at the same time share one machine's scan speed`() {
        assertThat(EngineChoice.singleNodeSeconds(report, laptop)).isCloseTo(2.435, within(0.001))
        assertThat(EngineChoice.singleNodeSeconds(report.copy(concurrent = 10), laptop)).isCloseTo(24.35, within(0.01))
    }

    @Test
    fun `a report that reads 7 GB of a 4 TB table runs on one machine`() {
        val route = EngineChoice.choose(report, laptop)
        assertThat(route.engine).isEqualTo(Engine.SINGLE_NODE)
        assertThat(route.machines).isEqualTo(1)
        assertThat(route.bytesRead).isEqualTo(EngineChoice.bytesRead(report))
        // exactly at the budget still fits
        val exact = report.copy(timeBudgetSeconds = EngineChoice.singleNodeSeconds(report, laptop))
        assertThat(EngineChoice.choose(exact, laptop).engine).isEqualTo(Engine.SINGLE_NODE)
    }

    @Test
    fun `forty analysts on a 30-second dashboard need an interactive cluster`() {
        val dashboard = Workload("merchant dashboard", tableBytes = 4 * TB, partitionsRead = 90.0 / 1095,
            columnsRead = 0.0608333, workingSetBytes = 1 * GB, timeBudgetSeconds = 30.0, concurrent = 40)
        val route = EngineChoice.choose(dashboard, vm)
        assertThat(EngineChoice.bytesRead(dashboard)).isCloseTo(20 * GB, within(10 * MB))
        assertThat(route.engine).isEqualTo(Engine.INTERACTIVE_CLUSTER)
        assertThat(route.machines).describedAs("ceil(533 s / 30 s)").isEqualTo(18)
    }

    @Test
    fun `a backfill whose join does not fit in memory goes to a batch cluster sized for memory`() {
        val backfill = Workload("fraud feature backfill", tableBytes = 4 * TB, partitionsRead = 1.0, columnsRead = 0.5,
            workingSetBytes = 600 * GB, timeBudgetSeconds = 2 * 3600.0)
        val route = EngineChoice.choose(backfill, vm)
        assertThat(route.singleNodeSeconds).describedAs("time alone would fit").isLessThan(backfill.timeBudgetSeconds)
        assertThat(route.engine).isEqualTo(Engine.BATCH_CLUSTER)
        assertThat(route.machines).describedAs("ceil(600 GB / 256 GB)").isEqualTo(3)
    }

    @Test
    fun `a job that is just slightly too big still gets at least two machines`() {
        val nightly = report.copy(name = "nightly", partitionsRead = 1.0, columnsRead = 0.25, timeBudgetSeconds = 600.0)
        val route = EngineChoice.choose(nightly, vm)
        assertThat(route.singleNodeSeconds).isCloseTo(666.7, within(0.1))
        assertThat(route.engine).isEqualTo(Engine.BATCH_CLUSTER)
        assertThat(route.machines).isEqualTo(2)
    }

    @Test
    fun `continuous work goes to a streaming engine whatever its size`() {
        val velocity = Workload("fraud velocity counts", tableBytes = 0, partitionsRead = 1.0, columnsRead = 1.0,
            workingSetBytes = 1 * GB, timeBudgetSeconds = 1.0, continuous = true)
        assertThat(EngineChoice.choose(velocity, laptop).engine).isEqualTo(Engine.STREAMING)
    }
}
