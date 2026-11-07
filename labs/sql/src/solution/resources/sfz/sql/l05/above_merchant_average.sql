-- Lesson sql-05, exercise 1 of 3: bigger than usual for this merchant (a trap)
-- Reference answer.
--
-- In the original, "merchant_id = merchant_id" names the inner payments table on both sides:
-- a name resolves in the nearest query that has such a column. So the test was always true
-- and every payment was compared with the average over all merchants.

-- One pass for the averages, one pass for the payments, joined on merchant_id.
WITH merchant_avg AS (
    SELECT merchant_id, avg(amount_minor) AS avg_minor
    FROM payments
    WHERE status = 'succeeded'
    GROUP BY merchant_id
)
SELECT p.payment_id,
       p.merchant_id,
       p.amount_minor,
       round(a.avg_minor) AS merchant_avg
FROM payments p
JOIN merchant_avg a ON a.merchant_id = p.merchant_id
WHERE p.status = 'succeeded'
  AND p.amount_minor > a.avg_minor          -- compare with the exact average, round only for display
ORDER BY p.payment_id;

-- The correlated version is also correct. Qualify both sides so the subquery is tied to p:
--   AND p.amount_minor > (SELECT avg(p2.amount_minor) FROM payments p2
--                         WHERE p2.status = 'succeeded' AND p2.merchant_id = p.merchant_id)
