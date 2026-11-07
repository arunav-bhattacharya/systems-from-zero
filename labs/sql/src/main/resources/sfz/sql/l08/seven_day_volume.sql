-- Lesson sql-08, exercise 2 of 3: a 7-day volume line for March (a trap)
--
-- For each day of March 2026 that has at least one SUCCEEDED payment:
--   day              the date (UTC)
--   volume_minor     that day's succeeded amount_minor
--   volume_7d_minor  the succeeded amount_minor of that day and the six calendar days before
--                    it. For 8 March that is 2 to 8 March; for 1 March it is 23 February to
--                    1 March, so the seven days can reach back into February.
--
-- Columns: day, volume_minor, volume_7d_minor
-- Order:   day
--
-- The query below adds up the current row and the six rows before it. A row is a day WITH
-- payments, and most days have none, so "six rows back" can mean three weeks back. Measure
-- the frame in days instead. Then check the start of March: a WHERE clause runs before the
-- window, so if it throws February away, the window never sees it.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l08.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

WITH daily AS (
    SELECT (created_at AT TIME ZONE 'UTC')::date AS day,
           sum(amount_minor) AS volume_minor
    FROM payments
    WHERE status = 'succeeded'
      AND created_at >= '2026-03-01' AND created_at < '2026-04-01'
    GROUP BY day
)
SELECT day,
       volume_minor,
       sum(volume_minor) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS volume_7d_minor
FROM daily
ORDER BY day;
