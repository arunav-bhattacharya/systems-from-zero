-- Lesson txn-07, exercise 2 of 2: who is stuck behind an in-doubt transaction? (a trap)
--
-- When a coordinator dies after PREPARE TRANSACTION, the prepared transaction keeps its locks,
-- and every writer that touches one of its rows waits. This is the query you run first: one row
-- per transaction prepared in the CURRENT database, with
--   gid      its global id (pg_prepared_xacts.gid)
--   waiting  how many sessions are waiting for it right now: lock requests on its transaction id
--            (pg_locks rows with locktype 'transactionid' and that id) that are not granted
-- ordered by gid. An in-doubt transaction that nobody waits for still gets a row, with 0.
--
-- pg_prepared_xacts and pg_locks show the whole server, every database. The prepared transaction
-- itself holds a granted ExclusiveLock on its own transaction id (with pid NULL), as every
-- transaction does. A second writer on the same row queues behind the first waiter, on a tuple
-- lock, so it doesn't wait on the transaction id directly; this query counts direct waiters.
--
-- The query below runs, and its numbers are wrong in three ways. Find them.
-- Check it: ./gradlew :sql:test --tests 'sfz.txn.l07.*'   (from the labs folder)

SELECT p.gid, count(*) AS waiting
FROM pg_prepared_xacts p
JOIN pg_locks w ON w.locktype = 'transactionid' AND w.transactionid = p.transaction
GROUP BY p.gid
ORDER BY p.gid;
