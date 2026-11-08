package sfz.repl.l04

/**
 * A model of PostgreSQL streaming replication, for lesson repl-04. No database, no threads: every
 * step happens when a test calls it, so each test is exact.
 *
 * The data is a map from key to value, standing in for the tables ("refund:7" -> "900"). Every
 * committed transaction is one [WalRecord]. Positions in the WAL are byte offsets (LSNs), printed
 * the way PostgreSQL prints a pg_lsn by [lsn].
 */

/**
 * One committed transaction in the WAL. It occupies the bytes [start] until [end]; [end] is its
 * LSN, the position right after it: what pg_current_wal_lsn() returns just after the commit, and
 * what a standby's flush_lsn reaches once the standby has the whole record on disk.
 * A null value in [writes] deletes the key.
 */
data class WalRecord(
    val end: Long,
    val size: Int,
    val txId: Long,
    val committedAt: Long,
    val writes: Map<String, String?>,
) {
    val start: Long get() = end - size
}

/** A WAL position in PostgreSQL's notation: 0x3000148 prints as 0/3000148. */
fun lsn(position: Long): String = "%X/%X".format(position ushr 32, position and 0xFFFFFFFFL)

/** Applies one record's writes to [data]: the same change on any server, primary, standby or restore. */
fun applyRecord(record: WalRecord, data: MutableMap<String, String>) {
    for ((key, value) in record.writes) {
        if (value == null) data.remove(key) else data[key] = value
    }
}

/** A physical replication slot. [restartLsn] is the oldest position its standby may still ask for. */
data class Slot(val name: String, var restartLsn: Long, var lost: Boolean = false)

/** A copy of the whole data directory as of [lsn], as pg_basebackup takes it. */
data class BaseBackup(val lsn: Long, val data: Map<String, String>)

/** Thrown when a standby asks for WAL the primary has already removed: the standby must be rebuilt. */
class WalRemovedException(message: String) : RuntimeException(message)

/** The primary: the only server that accepts writes. */
class Primary(startLsn: Long = 0x3000000L) {
    /** The tables. */
    val data: MutableMap<String, String> = sortedMapOf()

    /** The WAL still on disk in pg_wal, oldest first. [checkpoint] removes what nobody needs. */
    val wal: MutableList<WalRecord> = mutableListOf()

    /** Every record archive_command has copied away (archive_mode = on). Nothing removes these. */
    val archive: MutableList<WalRecord> = mutableListOf()

    /** The replication slots, by name. */
    val slots: MutableMap<String, Slot> = linkedMapOf()

    /** max_slot_wal_keep_size, in bytes. -1, the default, lets a slot keep any amount of WAL. */
    var maxSlotWalKeepSize: Long = -1

    /** pg_current_wal_lsn(): the end of the last record written. */
    var currentLsn: Long = startLsn
        private set

    private var nextTxId = 750L

    /** Commits one transaction at time [at] (seconds) and returns its WAL record (given). */
    fun commit(at: Long, vararg writes: Pair<String, String?>): WalRecord {
        val size = 48 + writes.sumOf { (k, v) -> 26 + k.length + (v?.length ?: 0) }
        val record = WalRecord(currentLsn + size, size, nextTxId++, at, linkedMapOf(*writes))
        currentLsn = record.end
        wal += record
        archive += record
        applyRecord(record, data)
        return record
    }

    /** pg_create_physical_replication_slot(name, true): the slot reserves WAL from now on (given). */
    fun createSlot(name: String): Slot = Slot(name, currentLsn).also { slots[name] = it }

    /** pg_basebackup (given): a copy of the data as of now. */
    fun baseBackup(): BaseBackup = BaseBackup(currentLsn, data.toMap())

    /** The bytes of WAL in pg_wal right now. */
    fun walOnDisk(): Long = wal.sumOf { it.size.toLong() }

    /**
     * Lesson repl-04, exercise 3 of 5: a checkpoint, and the WAL it may remove.
     *
     * After a checkpoint at [currentLsn], crash recovery would start here, so the primary itself
     * needs no older WAL. What it must keep is what the slots need: a slot that is not lost needs
     * every record that ends after its restartLsn.
     *
     * 1. First apply [maxSlotWalKeepSize] (unless it is -1): a slot whose restartLsn is more than
     *    that many bytes behind [currentLsn] is marked lost (pg_replication_slots.wal_status =
     *    'lost'). A lost slot holds nothing back; its standby will have to be rebuilt.
     * 2. Remove from [wal] every record that ends at or before the oldest restartLsn among the slots
     *    that are not lost (or at or before [currentLsn] when there are none).
     * 3. Return the number of bytes removed.
     *
     * Real PostgreSQL removes whole 16 MB segment files and also keeps wal_keep_size; the model
     * removes single records.
     */
    fun checkpoint(): Long {
        if (maxSlotWalKeepSize >= 0) {
            for (slot in slots.values) {
                if (!slot.lost && currentLsn - slot.restartLsn > maxSlotWalKeepSize) slot.lost = true
            }
        }
        val keepFrom = slots.values.filter { !it.lost }.minOfOrNull { it.restartLsn } ?: currentLsn
        val removable = wal.filter { it.end <= keepFrom }       // records every slot already has
        wal.removeAll(removable)
        return removable.sumOf { it.size.toLong() }
    }
}

/**
 * A standby: a copy of the primary that receives its WAL, writes and flushes it to its own disk,
 * and replays it. pg_stat_replication on the primary reports the three positions: write_lsn,
 * flush_lsn and replay_lsn.
 */
class Standby(val name: String, backup: BaseBackup, val slot: String? = name) {
    /** False while the standby is stopped, crashed or cut off: it receives nothing. */
    var running: Boolean = true

    /** The tables, as far as replay has got. Queries on the standby read these. */
    val data: MutableMap<String, String> = backup.data.toSortedMap()

    /** The WAL records this standby has received, in order. */
    val wal: MutableList<WalRecord> = mutableListOf()

    var writeLsn: Long = backup.lsn
    var flushLsn: Long = backup.lsn
    var replayLsn: Long = backup.lsn

    /**
     * Lesson repl-04, exercise 1 of 5: replay.
     *
     * Apply, in order, each record in [wal] that ends after [replayLsn] and at or before [upTo],
     * with [applyRecord], and move [replayLsn] to the end of the last record applied. Only whole
     * records count: if [upTo] falls inside a record, stop before it. Replay never goes past
     * [flushLsn], whatever [upTo] says: WAL that is not safely on the standby's disk yet is not
     * replayed.
     */
    fun replay(upTo: Long = flushLsn) {
        val limit = minOf(upTo, flushLsn)                        // only WAL on disk is replayed
        for (record in wal) {
            if (record.end <= replayLsn) continue                // already applied
            if (record.end > limit) break                        // a record past the limit, or cut by it
            applyRecord(record, data)
            replayLsn = record.end
        }
    }
}

/** synchronous_commit: how long a COMMIT on the primary waits before it answers the client. */
enum class SyncCommit { OFF, LOCAL, REMOTE_WRITE, ON, REMOTE_APPLY }

/** A primary and its standbys. */
class Cluster(val primary: Primary, val standbys: List<Standby>) {
    /**
     * synchronous_standby_names, as 'ANY 1 (s1, s2)': a commit waits until any one of these
     * standbys has confirmed it. Empty, the default, means every standby is asynchronous.
     */
    var synchronousStandbyNames: List<String> = emptyList()

    /** synchronous_commit; 'on' is the default. */
    var synchronousCommit: SyncCommit = SyncCommit.ON

    /** A new standby from a base backup of the primary, streaming through its own slot (given). */
    constructor(primary: Primary, vararg names: String) :
        this(primary, names.map { name -> primary.createSlot(name); Standby(name, primary.baseBackup()) })

    fun standby(name: String): Standby = standbys.first { it.name == name }

    /**
     * One round of streaming to [standby] (given). The walsender sends every record the standby
     * lacks; the standby writes it, flushes it if [flush], replays it if [replay], and reports
     * its flush position, which moves its slot's restartLsn. A standby that is not running gets
     * nothing. If the next record it needs is no longer in the primary's pg_wal, it fails with
     * [WalRemovedException], as a real standby does ("requested WAL segment ... has already been removed").
     */
    fun stream(standby: Standby, flush: Boolean = true, replay: Boolean = true) {
        if (!standby.running) return
        val oldestOnDisk = primary.wal.firstOrNull()?.start ?: primary.currentLsn
        if (standby.writeLsn < oldestOnDisk) {
            throw WalRemovedException("${standby.name}: requested WAL at ${lsn(standby.writeLsn)} has already been removed")
        }
        val missing = primary.wal.filter { it.end > standby.writeLsn }
        standby.wal += missing
        missing.lastOrNull()?.let { standby.writeLsn = it.end }
        if (flush) standby.flushLsn = standby.writeLsn
        standby.slot?.let { primary.slots[it] }?.let { if (!it.lost) it.restartLsn = maxOf(it.restartLsn, standby.flushLsn) }
        if (replay) standby.replay()
    }

    /** One round of streaming to every standby (given). */
    fun streamAll(flush: Boolean = true, replay: Boolean = true) = standbys.forEach { stream(it, flush, replay) }

    /** How many bytes of WAL [standby] still has to receive, flush and replay (given). */
    fun lag(standby: Standby): Triple<Long, Long, Long> =
        Triple(primary.currentLsn - standby.writeLsn, primary.currentLsn - standby.flushLsn, primary.currentLsn - standby.replayLsn)

    /**
     * Lesson repl-04, exercise 2 of 5: has the primary answered the client's COMMIT yet?
     *
     * With [synchronousCommit] OFF or LOCAL, or with no [synchronousStandbyNames], the commit is
     * acknowledged as soon as the primary has written it: return true. (OFF answers even before
     * the primary's own disk flush, so a crash of the primary can lose it too; the model never
     * crashes the primary's disk, so OFF and LOCAL look the same here.)
     *
     * Otherwise the commit waits until one of the named standbys has reached [commit]'s end
     * position in the stage the level names: REMOTE_WRITE its writeLsn, ON its flushLsn,
     * REMOTE_APPLY its replayLsn. Until then return false: the client's COMMIT is still waiting,
     * and it waits for as long as no named standby gets there.
     */
    fun isAcknowledged(commit: WalRecord): Boolean {
        if (synchronousCommit == SyncCommit.OFF || synchronousCommit == SyncCommit.LOCAL) return true
        if (synchronousStandbyNames.isEmpty()) return true      // asynchronous replication: answer at once
        return standbys.filter { it.name in synchronousStandbyNames }.any { s ->
            val reached = when (synchronousCommit) {
                SyncCommit.REMOTE_WRITE -> s.writeLsn            // in the standby's OS, not yet on its disk
                SyncCommit.ON -> s.flushLsn                      // on the standby's disk
                else -> s.replayLsn                              // visible to queries on the standby
            }
            reached >= commit.end
        }
    }
}
