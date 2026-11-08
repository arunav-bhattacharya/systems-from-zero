-- Lesson sql-07, exercise 1 of 3: a statement for the clearing account (a trap)
--
-- Account 900 is the internal clearing account that funds every deposit. List every ledger
-- entry of account 900, oldest first, with the account's balance just after that entry:
--   balance_minor   the sum of amount_minor over this entry and every entry before it
-- Entries with the same created_at happen in entry_id order: list them, and add them to the
-- balance, one at a time in that order.
--
-- Columns: entry_id, created_at, amount_minor, balance_minor
-- Order:   created_at, entry_id
--
-- The query below prints the rows in the right order, but look at the first four rows: four
-- deposits at 2026-01-02 09:00 all show the same balance. The window's frame decides which
-- rows each running sum adds up; find out what its default does with rows that tie.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l07.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT entry_id,
       created_at,
       amount_minor,
       sum(amount_minor) OVER (ORDER BY created_at) AS balance_minor
FROM ledger_entries
WHERE account_id = 900
ORDER BY created_at, entry_id;
