-- Lesson txn-02, exercise 2 of 2: a transfer between two accounts that cannot deadlock (a trap)
--
-- Each session has its own one-row temporary table with the transfer it should make:
--   transfer (from_account bigint, to_account bigint, amount_minor bigint)
-- The transaction moves amount_minor from from_account to to_account.
--
-- The tests run this whole file as ONE transaction in each of two sessions at once, one
-- statement at a time, taking turns (A's first statement, B's first, A's second, ...). A moves
-- money from 109 to 209 while B moves money from 209 to 109. If a statement fails with a
-- deadlock (40P01), the tests roll that session back and run the file again, as an application
-- would; the balances come out right, but the tests also check that no deadlock happened.
--
-- Below, A locks 109 with its first UPDATE and B locks 209 with its own. Then A waits for 209 and
-- B waits for 109: a deadlock, which PostgreSQL breaks after deadlock_timeout (one second) by
-- aborting one of them. Make every transfer take its locks in the same order, whatever the
-- direction of the transfer. Don't lock more than the two accounts: transfers between other
-- accounts must not wait.
-- Check it: ./gradlew :sql:test --tests 'sfz.txn.l02.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

BEGIN;

UPDATE accounts a
SET balance_minor = a.balance_minor - t.amount_minor
FROM transfer t
WHERE a.account_id = t.from_account;

UPDATE accounts a
SET balance_minor = a.balance_minor + t.amount_minor
FROM transfer t
WHERE a.account_id = t.to_account;

COMMIT;
