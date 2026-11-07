package sfz.bigdata.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

class ScanMathTest {
    private val block = 128 * MiB
    private val sataSsd = 500 * MB
    private val laptopNvme = 3 * GB

    // 10 billion rows x 25 columns x 4 bytes = 1 TB raw
    private val columns = (1..25).map { Column("c$it", 4) }
    private val rowTable = Table(rows = 10_000_000_000L, columns = columns, layout = Layout.ROW)
    private val columnTable = rowTable.copy(layout = Layout.COLUMNAR, compressionRatio = 4.0)

    @Test
    fun `one reader scans 1 TB at 500 MB per second in 2,000 seconds`() {
        assertThat(ScanMath.scanSeconds(TB, sataSsd)).isEqualTo(2_000.0)
        assertThat(ScanMath.scanSeconds(TB, laptopNvme)).isCloseTo(333.3, within(0.1))
    }

    @Test
    fun `a file splits into whole blocks and a short last block still counts`() {
        assertThat(ScanMath.blockCount(TB, block)).isEqualTo(7_451)
        assertThat(ScanMath.blockCount(block, block)).isEqualTo(1)
        assertThat(ScanMath.blockCount(block + 1, block)).isEqualTo(2)
        assertThat(ScanMath.blockCount(0, block)).isEqualTo(0)
        // 10 PB in 1-byte blocks: an Int overflows here, and a Double loses the last byte
        assertThat(ScanMath.blockCount(10_000 * TB + 1, 1)).isEqualTo(10_000 * TB + 1)
    }

    @Test
    fun `100 machines scan 1 TB in about 20 seconds because the busiest reads 75 blocks`() {
        val seconds = ScanMath.clusterSeconds(TB, block, sataSsd, machines = 100)
        assertThat(seconds).isCloseTo(75 * block / 500e6, within(1e-9))
        assertThat(seconds).isCloseTo(20.13, within(0.01))
        assertThat(ScanMath.clusterSeconds(TB, block, sataSsd, machines = 1)).isEqualTo(2_000.0)
    }

    @Test
    fun `startup is paid once, however many machines there are`() {
        val withStartup = ScanMath.clusterSeconds(TB, block, sataSsd, machines = 1_764, startupSeconds = 60.0)
        val without = ScanMath.clusterSeconds(TB, block, sataSsd, machines = 1_764)
        assertThat(withStartup - without).isCloseTo(60.0, within(1e-9))
        // with 1,764 machines the reading itself is tiny; the minute of startup is most of the job
        assertThat(without).isLessThan(2.0)
    }

    @Test
    fun `machines beyond the number of blocks do not make a scan faster`() {
        val tenBlocks = 10 * block
        val ten = ScanMath.clusterSeconds(tenBlocks, block, sataSsd, machines = 10)
        val thousand = ScanMath.clusterSeconds(tenBlocks, block, sataSsd, machines = 1_000)
        assertThat(thousand).isEqualTo(ten)
        // a file smaller than one block is one task, read by one machine
        assertThat(ScanMath.clusterSeconds(50 * MB, block, sataSsd, machines = 100)).isCloseTo(0.1, within(1e-9))
    }

    @Test
    fun `a row layout reads every column, a columnar layout reads only what the query needs`() {
        val need = setOf("c1", "c2", "c3")
        assertThat(ScanMath.bytesRead(rowTable, need)).isEqualTo(TB)
        // 3 of 25 columns: 12 of 100 bytes per row, then 4x compression
        assertThat(ScanMath.bytesRead(columnTable.copy(compressionRatio = 1.0), need)).isEqualTo(120 * GB)
        assertThat(ScanMath.bytesRead(columnTable, need)).isEqualTo(30 * GB)
        // compression helps a row layout too, but it still reads every column
        assertThat(ScanMath.bytesRead(rowTable.copy(compressionRatio = 4.0), need)).isEqualTo(250 * GB)
    }

    @Test
    fun `asking for a column the table does not have is an error`() {
        assertThatThrownBy { ScanMath.bytesRead(columnTable, setOf("c1", "fraud_score")) }
            .isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `34 machines scan 1 TB in a minute, and one laptop is enough once the query reads 30 GB`() {
        assertThat(ScanMath.machinesNeeded(TB, block, sataSsd, targetSeconds = 60.0)).isEqualTo(34)
        val fewerBytes = ScanMath.bytesRead(columnTable, setOf("c1", "c2", "c3"))
        assertThat(ScanMath.machinesNeeded(fewerBytes, block, laptopNvme, targetSeconds = 60.0)).isEqualTo(1)
    }

    @Test
    fun `no number of machines beats the time it takes to read one block`() {
        // one 128 MiB block takes about 0.27 s at 500 MB/s
        assertThat(ScanMath.machinesNeeded(TB, block, sataSsd, targetSeconds = 0.1)).isNull()
        assertThat(ScanMath.machinesNeeded(TB, block, sataSsd, targetSeconds = 0.3)).isEqualTo(7_451)
    }
}
