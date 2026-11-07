-- Lesson sql-04, exercise 1 of 3: one row per merchant, statuses as columns
--
-- Risk wants a status report with one row for EVERY merchant, including merchants that
-- have no payments yet:
--   payments    how many payments the merchant has (any status)
--   succeeded   how many of them succeeded
--   failed      how many of them failed
--   failed_pct  failed as a percentage of payments, rounded to one decimal place
--               (3 of 8 is 37.5); NULL for a merchant with no payments
--
-- Columns: merchant_id, name, payments, succeeded, failed, failed_pct
-- Order:   merchant_id
--
-- The query below runs and has the right shape, but every number in it is wrong.
-- Use FILTER for the per-status counts. Then check the merchants with no payments, and
-- check that 1 failure out of 8 comes out as 12.5.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l04.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT m.merchant_id,
       m.name,
       count(*) AS payments,
       count(*) AS succeeded,
       count(*) AS failed,
       round(100 * count(*) / count(*), 1) AS failed_pct
FROM merchants m
LEFT JOIN payments p ON p.merchant_id = m.merchant_id
GROUP BY m.merchant_id, m.name
ORDER BY m.merchant_id;
