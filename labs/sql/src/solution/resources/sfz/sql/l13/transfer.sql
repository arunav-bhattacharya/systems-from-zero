-- Lesson sql-13, exercise 2 of 2: a transfer between two accounts that cannot deadlock (a trap)
-- Reference answer.

BEGIN;

-- Lock both accounts first, lowest account_id first, whichever way the money goes. The second
-- transfer now waits for the first one at its very first lock and holds nothing while it waits,
-- so no cycle can form. OF a locks the account rows only, not the row of the temp table.
SELECT a.account_id
FROM accounts a, transfer t
WHERE a.account_id IN (t.from_account, t.to_account)
ORDER BY a.account_id
FOR UPDATE OF a;

UPDATE accounts a
SET balance_minor = a.balance_minor - t.amount_minor
FROM transfer t
WHERE a.account_id = t.from_account;

UPDATE accounts a
SET balance_minor = a.balance_minor + t.amount_minor
FROM transfer t
WHERE a.account_id = t.to_account;

COMMIT;

-- The order is what matters, not the SQL: in Kotlin, sort the two ids and lock the smaller one
-- first. LOCK TABLE accounts would also stop the deadlock, by making every transfer in the
-- company wait for every other one.
