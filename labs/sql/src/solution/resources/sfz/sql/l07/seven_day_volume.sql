-- Lesson sql-07, exercise 2 of 3: a 7-day volume line for March (a trap)
-- Reference answer.

WITH daily AS (
    SELECT (created_at AT TIME ZONE 'UTC')::date AS day,
           sum(amount_minor) AS volume_minor
    FROM payments
    WHERE status = 'succeeded'
      AND created_at >= '2026-02-23' AND created_at < '2026-04-01'   -- six days of February too, for 1 March
    GROUP BY day
),
windowed AS (
    SELECT day,
           volume_minor,
           -- RANGE measures the frame in values of the ORDER BY column: rows whose day is at most
           -- 6 days before this row's day. ROWS would count 6 rows, whatever days they are.
           sum(volume_minor) OVER (ORDER BY day
                                   RANGE BETWEEN interval '6 days' PRECEDING AND CURRENT ROW) AS volume_7d_minor
    FROM daily
)
SELECT day, volume_minor, volume_7d_minor
FROM windowed
WHERE day >= date '2026-03-01'           -- drop the February rows only after the window has used them
ORDER BY day;

-- Another way: build a calendar with one row per day (generate_series), LEFT JOIN the volumes to it,
-- and then ROWS BETWEEN 6 PRECEDING AND CURRENT ROW counts days, because every day is a row.
