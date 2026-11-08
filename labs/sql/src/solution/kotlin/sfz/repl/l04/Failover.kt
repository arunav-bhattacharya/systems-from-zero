package sfz.repl.l04

/** The result of a failover: the standby that became the primary, and the acknowledged commits it never had. */
data class FailoverResult(val promoted: Standby, val lost: List<WalRecord>)

/** The result of a point-in-time recovery: the data, and the WAL position where replay stopped. */
data class Recovered(val data: Map<String, String>, val stoppedAt: Long)

object Failover {

    /**
     * Lesson repl-04, exercise 4 of 5: the primary is gone; promote a standby.
     *
     * Choose among the running [standbys] the one with the most WAL on its disk: the highest
     * flushLsn. On a tie, the first in the list. A standby more than [maximumLagOnFailover] bytes
     * behind [primaryLsn] (the last position the old primary was known to have) may not be
     * chosen; this is Patroni's maximum_lag_on_failover. If no standby may be chosen, throw
     * IllegalStateException: staying down is better than losing more than you allowed.
     *
     * Promotion first replays everything the chosen standby has flushed (call its replay()), so
     * its data is as complete as its WAL. Then list the [acknowledged] commits (those the old
     * primary told clients about) that end after its flushLsn, in their order: those are lost.
     */
    fun failover(
        standbys: List<Standby>,
        primaryLsn: Long,
        acknowledged: List<WalRecord>,
        maximumLagOnFailover: Long = Long.MAX_VALUE,
    ): FailoverResult {
        val chosen = standbys
            .filter { it.running && primaryLsn - it.flushLsn <= maximumLagOnFailover }
            .maxByOrNull { it.flushLsn }                         // maxBy keeps the first of equal ones
            ?: throw IllegalStateException("no running standby within $maximumLagOnFailover bytes of ${lsn(primaryLsn)}")
        chosen.replay()                                          // pg_promote() finishes replay first
        val lost = acknowledged.filter { it.end > chosen.flushLsn }   // told "committed", never shipped
        return FailoverResult(chosen, lost)
    }
}

object Pitr {

    /**
     * Lesson repl-04, exercise 5 of 5: point-in-time recovery.
     *
     * Start from a copy of [backup]'s data. Walk [archive] in order, skipping records that end at
     * or before [backup].lsn (the backup has them already). Each following record must start
     * exactly where the previous one ended (the first at [backup].lsn): the archive is a chain.
     *
     * With [inclusive] (recovery_target_inclusive = on, the default), replay each record whose
     * committedAt is at or before [targetTime]; with inclusive false, only those strictly before.
     * The first record past the target is not applied: recovery stops just before it, and
     * returns the data and the end of the last record applied (or [backup].lsn if none was).
     *
     * If the chain breaks (a segment archive_command never copied) or the archive ends before
     * any record past the target shows up, throw IllegalStateException: PostgreSQL stops with
     * "recovery ended before configured recovery target was reached".
     */
    fun recover(backup: BaseBackup, archive: List<WalRecord>, targetTime: Long, inclusive: Boolean = true): Recovered {
        val data = backup.data.toSortedMap()
        var position = backup.lsn
        for (record in archive) {
            if (record.end <= backup.lsn) continue                // already inside the base backup
            check(record.start == position) { "recovery ended before configured recovery target was reached: WAL at ${lsn(position)} is missing" }
            val pastTarget = if (inclusive) record.committedAt > targetTime else record.committedAt >= targetTime
            if (pastTarget) return Recovered(data, position)     // "recovery stopping before commit of transaction ..."
            applyRecord(record, data)
            position = record.end
        }
        throw IllegalStateException("recovery ended before configured recovery target was reached at ${lsn(position)}")
    }
}
