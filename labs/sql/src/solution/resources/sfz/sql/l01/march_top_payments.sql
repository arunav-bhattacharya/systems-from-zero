-- Lesson sql-01, exercise 3 of 3: the five largest March payments
-- Reference answer.

SELECT payment_id,
       merchant_id,
       amount_minor,
       CASE                                   -- the first true branch wins
           WHEN amount_minor >= 50000 THEN 'large'
           WHEN amount_minor >= 10000 THEN 'medium'
           ELSE 'small'
       END AS band
FROM payments
WHERE status = 'succeeded'
  AND created_at >= '2026-03-01'              -- half-open range: includes midnight on 1 March
  AND created_at <  '2026-04-01'              -- excludes midnight on 1 April, keeps 23:59:59.5
ORDER BY amount_minor DESC, payment_id        -- payment_id makes the order of ties fixed
FETCH FIRST 5 ROWS ONLY;                      -- standard SQL; LIMIT 5 does the same
