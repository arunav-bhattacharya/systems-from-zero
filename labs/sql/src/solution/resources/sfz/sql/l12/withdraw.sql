-- Lesson sql-12, exercise 1 of 2: a withdrawal that keeps a customer's total at or above zero (a trap)
-- Reference answer.

BEGIN ISOLATION LEVEL SERIALIZABLE;     -- PostgreSQL tracks what each transaction read; when two
                                        -- of them read what the other then wrote, one is aborted
                                        -- with 40001 and must run again: on its second run it sees
                                        -- the first withdrawal and refuses.
UPDATE accounts a
SET balance_minor = a.balance_minor - w.amount_minor
FROM withdrawal w
WHERE a.account_id = w.account_id
  AND (SELECT sum(o.balance_minor)
       FROM accounts o
       WHERE o.customer_id = a.customer_id) >= w.amount_minor;

COMMIT;                                 -- with SERIALIZABLE the failure often comes here, at COMMIT

-- The other fix, at the default level and with no retries: lock every account the rule reads
-- before reading them. The second session waits for the first one's COMMIT, and its next
-- statement (a new snapshot at Read Committed) sees the new balance.
--
--   BEGIN;
--   SELECT 1 FROM accounts
--   WHERE customer_id = (SELECT customer_id FROM accounts JOIN withdrawal USING (account_id))
--   FOR UPDATE;
--   UPDATE accounts a ... (the same UPDATE) ;
--   COMMIT;
--
-- At REPEATABLE READ the lock alone is not enough: the waiting session's snapshot is older than
-- the first session's COMMIT, so its FOR UPDATE fails with 40001 and it must retry anyway.
