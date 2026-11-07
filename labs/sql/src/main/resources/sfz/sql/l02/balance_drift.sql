-- Lesson sql-02, exercise 3 of 3: find drift in a denormalized balance (a trap)
--
-- accounts.balance_minor is a cache: it should always equal the sum of amount_minor over that
-- account's rows in ledger_entries. An account with no ledger rows should have a balance of 0.
--
-- List every account whose cached balance differs from its ledger, with the ledger sum
-- (0 when the account has no entries).
--
-- Columns: account_id, cached, ledger
-- Order:   account_id
--
-- The query below finds most kinds of drift. The tests add one kind it misses.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l02.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT a.account_id,
       a.balance_minor AS cached,
       (SELECT sum(e.amount_minor) FROM ledger_entries e WHERE e.account_id = a.account_id) AS ledger
FROM accounts a
WHERE a.balance_minor <> (SELECT sum(e.amount_minor) FROM ledger_entries e WHERE e.account_id = a.account_id)
ORDER BY a.account_id;
