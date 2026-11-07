-- Lesson sql-06, exercise 3 of 3: every day of March, including the quiet ones
--
-- One row for EVERY day of March 2026 (31 rows), with that day's SUCCEEDED payments:
--   day           date
--   payments      how many succeeded payments were created that day (UTC)
--   volume_minor  their total amount_minor; 0 on a day without any
--
-- Columns: day, payments, volume_minor
-- Order:   day
--
-- The query below only returns days that have payments: a GROUP BY cannot invent a group
-- for a day with no rows. Generate the 31 days first (WITH RECURSIVE, or generate_series),
-- then attach the payments to them. Watch the edges: a payment at 23:59:59.5 on 31 March
-- belongs to 31 March, and one at 00:00 on 1 April does not belong to March at all.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l06.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT (created_at AT TIME ZONE 'UTC')::date AS day,
       count(*) AS payments,
       sum(amount_minor) AS volume_minor
FROM payments
WHERE status = 'succeeded'
  AND created_at >= '2026-03-01' AND created_at < '2026-04-01'
GROUP BY day
ORDER BY day;
