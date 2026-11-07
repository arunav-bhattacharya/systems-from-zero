-- Lesson sql-04, exercise 1 of 3: one row per merchant, statuses as columns
-- Reference answer.

SELECT m.merchant_id,
       m.name,                                              -- allowed: m.name depends on the key m.merchant_id
       count(p.payment_id) AS payments,                     -- count(*) would count the NULL row of a merchant with no payments as 1
       count(*) FILTER (WHERE p.status = 'succeeded') AS succeeded,
       count(*) FILTER (WHERE p.status = 'failed')    AS failed,   -- a NULL-padded row has status NULL: not counted
       round(100.0 * count(*) FILTER (WHERE p.status = 'failed')    -- 100.0 makes it numeric: 100 * 1 / 8 in integers is 12
             / nullif(count(p.payment_id), 0), 1) AS failed_pct      -- nullif turns 0 into NULL, so no division by zero
FROM merchants m
LEFT JOIN payments p ON p.merchant_id = m.merchant_id      -- LEFT JOIN keeps merchants 6 and 8, which have no payments
GROUP BY m.merchant_id
ORDER BY m.merchant_id;
