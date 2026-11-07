-- Lesson sql-04, exercise 2 of 3: subtotals with ROLLUP (a trap)
--
-- Finance wants SUCCEEDED payment volume by quarter and by channel (metadata->>'channel'),
-- with a subtotal row for each quarter and one grand total row:
--   quarter       '2026-Q1' style, from to_char(created_at, 'YYYY-"Q"Q'); 'all' on the grand total row
--   channel       the channel; 'all' on subtotal and grand total rows
--   payments      count of payments
--   volume_minor  sum of amount_minor
--
-- Columns: quarter, channel, payments, volume_minor
-- Order:   by quarter, the grand total last; within a quarter by channel, with a payment whose
--          channel is missing (NULL) after the named channels, and the quarter's subtotal last
--
-- Trap: a payment can arrive without a channel. Its row must keep channel NULL. Only rows that
-- ROLLUP added may say 'all'. coalesce cannot tell the two kinds of NULL apart; GROUPING() can.
-- The query below runs but has no subtotal rows at all.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l04.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT to_char(created_at, 'YYYY-"Q"Q') AS quarter,
       coalesce(metadata->>'channel', 'all') AS channel,
       count(*) AS payments,
       sum(amount_minor) AS volume_minor
FROM payments
WHERE status = 'succeeded'
GROUP BY to_char(created_at, 'YYYY-"Q"Q'), metadata->>'channel'
ORDER BY 1, 2;
