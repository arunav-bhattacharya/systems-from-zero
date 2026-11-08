-- Lesson model-07, exercise 3 of 3: every day of March, including the quiet ones
-- Reference answer.

WITH RECURSIVE days AS (
    SELECT date '2026-03-01' AS day          -- anchor: the first day
  UNION ALL
    SELECT day + 1                           -- date + integer is the next date
    FROM days
    WHERE day < date '2026-03-31'            -- the stop condition: the round after 31 March adds nothing
)
SELECT d.day,
       count(p.payment_id) AS payments,      -- count(*) would say 1 on a day with no payment
       coalesce(sum(p.amount_minor), 0) AS volume_minor   -- sum over no rows is NULL
FROM days d
LEFT JOIN payments p
       ON p.status = 'succeeded'             -- in ON, not WHERE: days with only failed payments stay
      AND p.created_at >= d.day              -- a date compared with timestamptz means midnight in the
      AND p.created_at <  d.day + 1          -- session time zone (UTC here): a half-open day
GROUP BY d.day
ORDER BY d.day;

-- With PostgreSQL's set-returning function instead of recursion:
--   SELECT g::date AS day FROM generate_series(timestamp '2026-03-01', timestamp '2026-03-31', interval '1 day') AS g
