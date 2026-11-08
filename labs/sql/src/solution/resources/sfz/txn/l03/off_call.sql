-- Lesson txn-03, exercise 1 of 3: a doctor goes off call only if another one stays on call (a trap)
-- Reference answer.

BEGIN;                                  -- Read Committed: each statement gets a fresh snapshot

-- Lock every doctor of the shift who is on call: the rows the rule is about to count. The second
-- doctor's request waits here until the first one commits. Then PostgreSQL rechecks each row
-- against "c.on_call", drops the doctor who has just gone off call, and the UPDATE below, a new
-- statement with a new snapshot, counts one doctor and changes nothing. OF c locks on_call rows
-- only, not the row of the temp table.
SELECT c.doctor
FROM on_call c, off_call_request r
WHERE c.shift_id = r.shift_id
  AND c.on_call
FOR UPDATE OF c;

UPDATE on_call o
SET on_call = false
FROM off_call_request r
WHERE o.shift_id = r.shift_id
  AND o.doctor = r.doctor
  AND (SELECT count(*)
       FROM on_call c
       WHERE c.shift_id = r.shift_id
         AND c.on_call) >= 2;

COMMIT;

-- The other fix is one line: BEGIN ISOLATION LEVEL SERIALIZABLE; with no lock. PostgreSQL sees
-- that each transaction read a row the other wrote, aborts one with 40001, and its retry counts
-- one doctor. At REPEATABLE READ the lock alone still works, but through a 40001 and a retry:
-- the waiting session's snapshot is older than the commit it waited for.
