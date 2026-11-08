package sfz.store.l06

import sfz.store.l01.ChannelFactory
import sfz.store.l03.FileDiskManager
import sfz.store.l03.PAGE_SIZE
import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.file.Path

/** An open transaction: its id, the LSN of its BEGIN record, and the writes it will apply at commit. */
class Tx(val id: Int, val firstLsn: Long) {
    /** Page id -> new value. Nothing here touches a page until [Database.commit]. */
    val writes = LinkedHashMap<Int, Long>()
    var open = true
}

/** What the last recovery did: records it read from the log, and page changes it redid. */
data class RecoveryStats(val scanned: Int, val redone: Int)

/**
 * A tiny transactional store: [pageCount] accounts, each one a 4 KB page holding a balance, protected by a
 * write-ahead log.
 *
 * A data page holds two numbers: bytes 0..7 are the page LSN (the end LSN of the last log record whose
 * change is in this page) and bytes 8..15 are the balance.
 *
 * The protocol you build:
 * - [write] appends an UPDATE record and remembers the change in the transaction. Pages are not touched
 *   until commit, so a page never holds a change of a transaction that has not committed ("no steal").
 * - [commit] appends a COMMIT record and, if `sync`, flushes the log up to it before returning (the
 *   commit rule). Then it applies the writes to the pages in memory and stamps each page with the commit
 *   record's end LSN. The pages are written to the data file later ("no force").
 * - [flushPage] writes one page to the data file, but first flushes the log up to the page's LSN (the
 *   WAL rule: log before data).
 * - [checkpoint] flushes every dirty page, syncs the data file, logs a CHECKPOINT record with the redo LSN
 *   (where a later recovery must start) and records the checkpoint's LSN in the control file.
 * - [recover] runs on open: read the log from the last checkpoint's redo LSN, and replay each committed
 *   transaction at its COMMIT record onto every page whose LSN is older than that record.
 *
 * Your job: write [write], [commit], [abort], [flushPage], [checkpoint] and [recover]. [Wal], [LogRecord]
 * and [ControlFile] in Wal.kt are done, and so is everything below the "provided" line here.
 */
class Database private constructor(dir: Path, val pageCount: Int, channels: ChannelFactory) : Closeable {

    /** A page in memory: the buffer pool of lesson 3, minus eviction. */
    class Page(var value: Long, var lsn: Long, var dirty: Boolean = false)

    private val wal = Wal(dir.resolve(LOG_FILE), channels)
    private val disk = FileDiskManager(dir.resolve(DATA_FILE))
    private val control = ControlFile(dir.resolve(CONTROL_FILE))
    private val pages = HashMap<Int, Page>()
    private val active = LinkedHashMap<Int, Tx>()
    private var nextTxId = 1

    /** What the recovery in [open] did. */
    var lastRecovery = RecoveryStats(0, 0)
        private set

    /** The durable end of the log, for tests and demos. */
    val flushedLsn: Long get() = wal.flushedLsn

    init {
        while (disk.pageCount < pageCount) disk.allocatePage()
    }

    /** Records that [tx] sets [pageId] to [value]: an UPDATE record in the log, the change in [Tx.writes]. */
    fun write(tx: Tx, pageId: Int, value: Long) {
        TODO("check the tx is open; append an UPDATE record; remember the value in tx.writes")
    }

    /**
     * Commits [tx]. With `sync = true` the COMMIT record is durable when this returns. With `sync = false`
     * (PostgreSQL's `synchronous_commit = off`) it may still be only in the log buffer.
     */
    fun commit(tx: Tx, sync: Boolean = true) {
        TODO("append COMMIT; if sync, flush the log up to its endLsn; apply tx.writes to the pages (value, lsn = commit endLsn, dirty); close the tx")
    }

    /** Rolls [tx] back: an ABORT record, and its writes are dropped. No page was ever changed. */
    fun abort(tx: Tx) {
        TODO("append ABORT; drop the writes; close the tx")
    }

    /** Writes page [pageId] to the data file if it is dirty, obeying the WAL rule. */
    fun flushPage(pageId: Int) {
        TODO("if the page is cached and dirty: flush the log up to the page's LSN FIRST, then writeToDisk, then mark it clean")
    }

    /**
     * Flushes every dirty page, syncs the data file, then logs a CHECKPOINT record whose value is the redo
     * LSN: the BEGIN of the oldest open transaction, or the checkpoint record itself if none is open.
     * Flushes the log and points the control file at the checkpoint record.
     */
    fun checkpoint() {
        TODO("flushPage every page, disk.sync(), append CHECKPOINT(txId = nextTxId, value = redo LSN), flush the log, control.write(its lsn)")
    }

    /**
     * Crash recovery. Find where to start: the redo LSN of the checkpoint the control file points at, or 0.
     * Read the log from there with [Wal.recover]. Collect each transaction's UPDATE records; at its COMMIT
     * record, apply its writes (the last value per page, as [commit] did) to every page whose LSN is below
     * the COMMIT record's end LSN, and stamp the page with that LSN. Forget transactions that ABORT or
     * never commit. Set [nextTxId] past every id seen and [lastRecovery].
     */
    private fun recover() {
        TODO("start at the checkpoint's redo LSN (or 0); wal.recover(start); collect UPDATEs per tx; at COMMIT apply them to pages whose lsn < the commit's endLsn")
    }

    // ---------------------------------------------------------------- provided

    /** Starts a transaction: logs BEGIN (not flushed) and returns it. */
    fun begin(): Tx {
        val rec = wal.append(RecordType.BEGIN, nextTxId)
        val tx = Tx(nextTxId++, rec.lsn)
        active[tx.id] = tx
        return tx
    }

    /** The committed balance of [pageId]. */
    fun read(pageId: Int): Long = page(pageId).value

    /** What [tx] sees: its own uncommitted write, or the committed balance. */
    fun read(tx: Tx, pageId: Int): Long = tx.writes[pageId] ?: read(pageId)

    /** The page LSN of [pageId] in memory. */
    fun pageLsn(pageId: Int): Long = page(pageId).lsn

    /** The page in memory, read from the data file the first time. */
    private fun page(id: Int): Page = pages.getOrPut(id) {
        val b = ByteBuffer.allocate(PAGE_SIZE)
        disk.readPage(id, b)
        Page(value = b.getLong(VALUE_AT), lsn = b.getLong(LSN_AT))
    }

    /** Writes [p] into the data file at page [id]. No WAL rule here: [flushPage] must take care of it. */
    private fun writeToDisk(id: Int, p: Page) {
        val b = ByteBuffer.allocate(PAGE_SIZE)
        b.putLong(LSN_AT, p.lsn).putLong(VALUE_AT, p.value)
        disk.writePage(id, b)
    }

    /** The process dies: memory (pages, open transactions, the log buffer) is lost; files stay as they are. */
    fun crash() {
        wal.crash()
        disk.close()
        pages.clear()
        active.clear()
    }

    /** A clean shutdown: a checkpoint, then close. */
    override fun close() {
        checkpoint()
        wal.close()
        disk.close()
    }

    companion object {
        const val LOG_FILE = "wal.log"
        const val DATA_FILE = "data.db"
        const val CONTROL_FILE = "control"
        const val LSN_AT = 0
        const val VALUE_AT = 8

        /** Opens (or creates) a database of [pages] accounts in [dir] and runs crash recovery. */
        fun open(dir: Path, pages: Int = 16, channels: ChannelFactory = ChannelFactory.DEFAULT): Database =
            Database(dir, pages, channels).also { it.recover() }
    }
}
