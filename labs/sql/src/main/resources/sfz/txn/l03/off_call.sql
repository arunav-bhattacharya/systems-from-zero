-- Lesson txn-03, exercise 1 of 3: a doctor goes off call only if another one stays on call (a trap)
--
-- Table on_call (shift_id, doctor, on_call) lists who covers each shift. The hospital's rule:
-- every shift keeps at least one doctor with on_call = true. A doctor may go off call only if
-- at least one OTHER doctor of the same shift is still on call.
--
-- The tests run this whole file as ONE transaction in each of two sessions at once, one
-- statement at a time, taking turns (A's first statement, B's first, A's second, ...). Each
-- session has its own temporary table with its request:
--   off_call_request (shift_id bigint, doctor text)          -- one row
-- A request the rule does not allow changes nothing (the UPDATE matches no row).
-- If a statement fails with a serialization failure (40001) or a deadlock (40P01), the tests
-- roll that session back and run the whole file again for it, as your application would.
--
-- Below, the check sits inside the UPDATE. Run alone it is right. Run in two sessions at once,
-- Okafor and Lind both see two doctors on call, each goes off call, and shift 1201 is left with
-- nobody: write skew. The two UPDATEs change different rows, so Repeatable Read sees no conflict.
-- Fix it by locking the rows the rule reads before you decide (or with a stronger isolation
-- level). Doctors on other shifts must not wait for each other.
-- Check it: ./gradlew :sql:test --tests 'sfz.txn.l03.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

BEGIN ISOLATION LEVEL REPEATABLE READ;

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
