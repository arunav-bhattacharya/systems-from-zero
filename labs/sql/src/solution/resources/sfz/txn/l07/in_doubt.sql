-- Lesson txn-07, exercise 2 of 2: who is stuck behind an in-doubt transaction? (solution)
--
-- One row per transaction prepared in the current database, with the number of sessions waiting
-- on its transaction id right now, ordered by gid.

SELECT p.gid, count(w.pid) AS waiting                        -- count waiters, so no match gives 0
FROM pg_prepared_xacts p
LEFT JOIN pg_locks w                                         -- LEFT: keep transactions nobody waits for
       ON w.locktype = 'transactionid'
      AND w.transactionid = p.transaction
      AND NOT w.granted                                      -- skip its own granted lock on its id
WHERE p.database = current_database()                        -- the views cover the whole server
GROUP BY p.gid
ORDER BY p.gid;
