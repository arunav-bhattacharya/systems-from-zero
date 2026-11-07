-- Lesson sql-03, exercise 3 of 3: merchants that issued a refund, each once
-- Reference answer.

SELECT m.merchant_id, m.name
FROM merchants m
-- a semi join: keep m once if at least one refunded payment exists. A plain JOIN returns
-- m once per matching refund (three times for merchant 4), and DISTINCT only hides that.
WHERE EXISTS (
    SELECT 1
    FROM payments p
    JOIN refunds r ON r.payment_id = p.payment_id
    WHERE p.merchant_id = m.merchant_id
)
ORDER BY m.merchant_id;
