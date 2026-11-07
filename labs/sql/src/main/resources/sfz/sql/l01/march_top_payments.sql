-- Lesson sql-01, exercise 3 of 3: the five largest March payments
--
-- Find the five largest SUCCEEDED payments created in March 2026 (UTC: the session time zone
-- in the tests and in the Try-it database). Largest first. Several payments have the same
-- amount, so break ties by payment_id, smallest first.
--
-- Add a column band that labels the amount:
--   'large'   amount_minor is 50000 or more
--   'medium'  amount_minor is 10000 or more
--   'small'   anything else
--
-- Columns: payment_id, merchant_id, amount_minor, band
-- Order:   amount_minor descending, then payment_id ascending
--
-- Watch the edges of the month: one payment lands at exactly midnight on 1 March,
-- one half a second before midnight on 31 March, and one at exactly midnight on 1 April.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l01.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT NULL::bigint AS payment_id,
       NULL::bigint AS merchant_id,
       NULL::bigint AS amount_minor,
       NULL::text   AS band
WHERE false;
