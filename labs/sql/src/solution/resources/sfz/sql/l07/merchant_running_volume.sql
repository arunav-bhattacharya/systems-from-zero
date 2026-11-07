-- Lesson sql-07, exercise 3 of 3: each merchant's volume, month by month, and so far this year
-- Reference answer.

SELECT merchant_id,
       date_trunc('month', created_at)::date AS month,
       sum(amount_minor) AS volume_minor,
       -- the inner sum is the GROUP BY aggregate (one value per merchant and month); the outer
       -- sum is a window over those grouped rows, restarted for each merchant, in month order
       sum(sum(amount_minor)) OVER (PARTITION BY merchant_id
                                    ORDER BY date_trunc('month', created_at)) AS running_volume_minor
FROM payments
WHERE status = 'succeeded'
GROUP BY merchant_id, date_trunc('month', created_at)
ORDER BY merchant_id, month;

-- The same in two steps, which some people find easier to read:
--   WITH monthly AS (
--       SELECT merchant_id, date_trunc('month', created_at)::date AS month, sum(amount_minor) AS volume_minor
--       FROM payments WHERE status = 'succeeded' GROUP BY 1, 2
--   )
--   SELECT merchant_id, month, volume_minor,
--          sum(volume_minor) OVER (PARTITION BY merchant_id ORDER BY month) AS running_volume_minor
--   FROM monthly ORDER BY merchant_id, month;
