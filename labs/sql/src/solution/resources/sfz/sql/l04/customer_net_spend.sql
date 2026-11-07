-- Lesson sql-04, exercise 3 of 3: join, then sum, and count something twice (a trap)
-- Reference answer.

SELECT cu.customer_id,
       cu.full_name,
       sum(p.amount_minor) AS paid_minor,
       coalesce(sum(r.refunded_minor), 0) AS refunded_minor,
       sum(p.amount_minor) - coalesce(sum(r.refunded_minor), 0) AS net_minor
FROM customers cu
JOIN accounts a ON a.customer_id = cu.customer_id
JOIN cards c    ON c.account_id = a.account_id
JOIN payments p ON p.card_id = c.card_id
-- Aggregate the refunds first: one row per payment. A plain LEFT JOIN to refunds repeats a
-- payment once per refund, and sum(p.amount_minor) then counts payment 5 twice.
LEFT JOIN (
    SELECT payment_id, sum(amount_minor) AS refunded_minor
    FROM refunds
    GROUP BY payment_id
) AS r ON r.payment_id = p.payment_id       -- at most one r row per payment, so no payment is repeated
WHERE p.status = 'succeeded'
GROUP BY cu.customer_id                    -- full_name depends on the primary key, so it may be selected
ORDER BY cu.customer_id;
