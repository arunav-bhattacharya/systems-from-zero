-- Lesson sql-06, exercise 3 of 3: each merchant's volume, month by month, and so far this year
--
-- One row per merchant and month that has SUCCEEDED payments:
--   month                 the first day of the month (a date, UTC), e.g. 2026-03-01
--   volume_minor          that merchant's succeeded amount_minor in that month
--   running_volume_minor  that merchant's succeeded amount_minor from January up to and
--                         including that month
--
-- Columns: merchant_id, month, volume_minor, running_volume_minor
-- Order:   merchant_id, month
--
-- The query below groups by merchant and month correctly, but its last column is only the
-- month's own volume. Make it a running total that starts again for every merchant. A window
-- function can sit on top of a GROUP BY: it runs after the groups are folded.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l06.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT merchant_id,
       date_trunc('month', created_at)::date AS month,
       sum(amount_minor) AS volume_minor,
       sum(amount_minor) AS running_volume_minor
FROM payments
WHERE status = 'succeeded'
GROUP BY merchant_id, date_trunc('month', created_at)
ORDER BY merchant_id, month;
