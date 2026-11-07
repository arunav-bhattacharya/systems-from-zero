package sfz.internals.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import sfz.internals.l01.ChannelFactory
import sfz.internals.l03.PAGE_SIZE
import sfz.internals.support.CountingFileChannel
import sfz.internals.support.Crash
import java.nio.ByteBuffer
import java.nio.file.Files
import java.nio.file.Path

class DatabaseTest {
    @TempDir
    lateinit var dir: Path

    private class Channels : ChannelFactory {
        lateinit var log: CountingFileChannel
        override fun open(path: Path) = CountingFileChannel.open(path).also { log = it }
    }

    private val logFile get() = dir.resolve(Database.LOG_FILE)
    private val dataFile get() = dir.resolve(Database.DATA_FILE)

    /** Moves [amount] from account [from] to account [to] in one transaction. */
    private fun Database.transfer(from: Int, to: Int, amount: Long, sync: Boolean = true) {
        val tx = begin()
        write(tx, from, read(tx, from) - amount)
        write(tx, to, read(tx, to) + amount)
        commit(tx, sync)
    }

    /** Sets one account in its own transaction. */
    private fun Database.set(page: Int, value: Long, sync: Boolean = true) {
        val tx = begin()
        write(tx, page, value)
        commit(tx, sync)
    }

    /** The (lsn, balance) of [page] as the data file holds it right now. */
    private fun onDisk(page: Int): Pair<Long, Long> {
        val bytes = Files.readAllBytes(dataFile)
        if (bytes.size < (page + 1) * PAGE_SIZE) return 0L to 0L
        val b = ByteBuffer.wrap(bytes, page * PAGE_SIZE, PAGE_SIZE).slice()
        return b.getLong(Database.LSN_AT) to b.getLong(Database.VALUE_AT)
    }

    /** The WAL rule, checked on the files: no page on disk is ahead of the durable log. */
    private fun assertNoPageAheadOfTheLog() {
        val logEnd = Files.size(logFile)
        for (p in 0 until 16) {
            val (lsn, _) = onDisk(p)
            assertThat(lsn).`as`("LSN of page $p on disk vs the end of the log on disk ($logEnd)").isLessThanOrEqualTo(logEnd)
        }
    }

    @Test
    fun `committed transactions survive a crash`() {
        val db = Database.open(dir)
        db.set(1, 1_000)
        db.transfer(1, 2, 250)
        db.crash()
        val again = Database.open(dir)
        assertThat(again.read(1)).isEqualTo(750)
        assertThat(again.read(2)).isEqualTo(250)
        assertThat(again.lastRecovery.redone).`as`("page changes redone from the log").isEqualTo(3)
    }

    @Test
    fun `commit forces the log and writes no data page`() {
        val channels = Channels()
        val db = Database.open(dir, channels = channels)
        channels.log.resetCounts()
        db.transfer(1, 2, 100)
        assertThat(channels.log.forces).`as`("log forces during one commit").isEqualTo(1)
        assertThat(channels.log.events.last()).`as`("the last thing commit does to the log").isEqualTo("force")
        assertThat(Files.size(logFile)).`as`("log bytes on disk: BEGIN, two UPDATEs, COMMIT").isEqualTo(4L * LogRecord.SIZE)
        assertThat(onDisk(1)).`as`("page 1 on disk after the commit").isEqualTo(0L to 0L)
        assertThat(onDisk(2)).`as`("page 2 on disk after the commit").isEqualTo(0L to 0L)
        assertThat(db.read(2)).`as`("page 2 in memory").isEqualTo(100)
    }

    @Test
    fun `an uncommitted transaction leaves no trace, even when its records reached the log`() {
        val db = Database.open(dir)
        db.set(1, 1_000)
        val open = db.begin()
        db.write(open, 1, 0)                         // half of a transfer ...
        db.write(open, 2, 1_000)
        db.set(3, 42)                                // ... and another transaction's commit flushes those records too
        assertThat(Files.size(logFile)).`as`("the open transaction's records are on disk").isEqualTo(9L * LogRecord.SIZE)
        db.crash()
        val again = Database.open(dir)
        assertThat(again.read(1)).isEqualTo(1_000)
        assertThat(again.read(2)).isEqualTo(0)
        assertThat(again.read(3)).isEqualTo(42)
    }

    @Test
    fun `an aborted transaction changes nothing, before or after a crash`() {
        val db = Database.open(dir)
        db.set(5, 70)
        val tx = db.begin()
        db.write(tx, 5, 0)
        assertThat(db.read(tx, 5)).`as`("the transaction sees its own write").isEqualTo(0)
        assertThat(db.read(5)).`as`("nobody else does").isEqualTo(70)
        db.abort(tx)
        assertThat(db.read(5)).isEqualTo(70)
        db.set(6, 1)                                 // flushes the ABORT record too
        db.crash()
        assertThat(Database.open(dir).read(5)).isEqualTo(70)
    }

    @Test
    fun `a crash that tears the last commit record loses exactly that transaction`() {
        for (cut in 1..LogRecord.SIZE) {
            val d = Files.createDirectory(dir.resolve("cut-$cut"))
            val db = Database.open(d)
            db.set(1, 500)
            db.transfer(1, 2, 200)                   // the last record in the log is this COMMIT
            db.crash()
            Crash.chopTail(d.resolve(Database.LOG_FILE), cut.toLong())
            val again = Database.open(d)
            assertThat(again.read(1)).`as`("page 1 after cutting $cut bytes").isEqualTo(500)
            assertThat(again.read(2)).`as`("page 2 after cutting $cut bytes").isEqualTo(0)
            again.crash()
        }
    }

    @Test
    fun `recovery truncates a torn tail so the next commit survives the next crash`() {
        val db = Database.open(dir)
        db.set(1, 10)
        db.set(2, 20)
        db.crash()
        Crash.chopTail(logFile, 5)
        val second = Database.open(dir)
        assertThat(Files.size(logFile)).`as`("log size after recovery").isEqualTo(5L * LogRecord.SIZE)
        second.set(3, 30)
        second.crash()
        val third = Database.open(dir)
        assertThat(third.read(1)).isEqualTo(10)
        assertThat(third.read(2)).isEqualTo(0)
        assertThat(third.read(3)).`as`("the commit made after the first recovery").isEqualTo(30)
    }

    @Test
    fun `log before data - a page never reaches the disk ahead of its commit record`() {
        val db = Database.open(dir)
        db.set(1, 1_000)
        db.checkpoint()
        db.transfer(1, 2, 300, sync = false)         // synchronous_commit = off: nothing forced yet
        db.flushPage(1)                              // the debit side goes to disk ...
        assertNoPageAheadOfTheLog()                  // ... so the COMMIT record must have gone first
        db.crash()                                   // the credit side was only in memory
        val again = Database.open(dir)
        assertThat(again.read(1) to again.read(2)).`as`("both sides of the transfer, or neither").isEqualTo(700L to 300L)
    }

    @Test
    fun `an asynchronous commit can lose whole transactions but never half of one`() {
        val channels = Channels()
        val db = Database.open(dir, channels = channels)
        db.set(1, 1_000)
        channels.log.resetCounts()
        db.transfer(1, 2, 300, sync = false)
        assertThat(channels.log.forces).`as`("forces during an asynchronous commit").isZero()
        assertThat(db.read(2)).`as`("visible at once in memory").isEqualTo(300)
        db.crash()
        val again = Database.open(dir)
        assertThat(again.read(1) to again.read(2)).isEqualTo(1_000L to 0L)
    }

    @Test
    fun `recovery is idempotent, and the page LSN skips work that already reached the disk`() {
        val db = Database.open(dir)
        repeat(10) { db.transfer(it % 4, 4 + it % 4, 10L * (it + 1)) }
        db.crash()
        val first = Database.open(dir)
        val state = (0 until 8).map { first.read(it) }
        assertThat(first.lastRecovery.redone).isEqualTo(20)
        first.crash()                                // crash again before anything was written back
        val second = Database.open(dir)
        assertThat((0 until 8).map { second.read(it) }).`as`("state after recovering twice").isEqualTo(state)
        assertThat(second.lastRecovery.redone).isEqualTo(20)
        for (p in 0 until 8) second.flushPage(p)     // the redone pages reach the disk, with their LSNs
        assertNoPageAheadOfTheLog()
        second.crash()
        val third = Database.open(dir)
        assertThat((0 until 8).map { third.read(it) }).isEqualTo(state)
        assertThat(third.lastRecovery.redone).`as`("changes redone when every page already has them").isZero()
        assertThat(third.lastRecovery.scanned).`as`("records still scanned without a checkpoint").isEqualTo(40)
    }

    @Test
    fun `a checkpoint shortens recovery and keeps transactions that are open across it`() {
        val db = Database.open(dir)
        repeat(50) { db.set(it % 16, it.toLong()) }
        val longRunning = db.begin()
        db.write(longRunning, 15, 4_242)             // logged before the checkpoint, committed after it
        db.checkpoint()
        repeat(3) { db.set(it, 1_000L + it) }
        db.commit(longRunning)
        db.crash()
        val again = Database.open(dir)
        assertThat((0 until 3).map { again.read(it) }).isEqualTo(listOf(1_000L, 1_001L, 1_002L))
        assertThat(again.read(15)).`as`("the transaction that was open during the checkpoint").isEqualTo(4_242)
        assertThat(again.read(10)).isEqualTo(42)
        // from the long-running BEGIN: BEGIN, UPDATE, CHECKPOINT, 3 x (BEGIN, UPDATE, COMMIT), COMMIT
        assertThat(again.lastRecovery.scanned).`as`("records read by recovery").isEqualTo(13)
        assertThat(again.lastRecovery.redone).isEqualTo(4)
    }

    @Test
    fun `a damaged record in the middle of the log ends the log there`() {
        val db = Database.open(dir)
        db.set(1, 10)                                 // records 0, 1, 2
        db.set(2, 20)                                 // records 3, 4, 5
        db.set(3, 30)                                 // records 6, 7, 8
        db.crash()
        Crash.flipByte(logFile, 4L * LogRecord.SIZE + 20)   // inside the second transaction's UPDATE
        val again = Database.open(dir)
        assertThat(listOf(again.read(1), again.read(2), again.read(3))).isEqualTo(listOf(10L, 0L, 0L))
        assertThat(Files.size(logFile)).`as`("the log is cut at the damaged record").isEqualTo(4L * LogRecord.SIZE)
    }
}
