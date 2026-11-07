-- Lesson sql-03, exercise 2 of 3: keep the merchants with nothing to show (a trap)
-- Reference answer.

SELECT m.merchant_id, m.name, p.payment_id, p.amount_minor
FROM merchants m
LEFT JOIN payments p
       ON p.merchant_id = m.merchant_id
      AND p.status = 'failed'      -- in ON, it decides which payments match; unmatched merchants stay
-- in WHERE, the same test would run after the join and drop the NULL-extended rows,
-- because NULL = 'failed' is not true
ORDER BY m.merchant_id, p.payment_id;
