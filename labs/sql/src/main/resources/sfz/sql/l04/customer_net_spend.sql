-- Lesson sql-04, exercise 3 of 3: join, then sum, and count something twice (a trap)
--
-- For every customer with at least one SUCCEEDED payment:
--   paid_minor      the sum of their succeeded payments (each payment once)
--   refunded_minor  the sum of the refunds on those payments (0 if none)
--   net_minor       paid_minor - refunded_minor
--
-- Columns: customer_id, full_name, paid_minor, refunded_minor, net_minor
-- Order:   customer_id
--
-- The query below joins everything and then sums. Most customers come out right. One does
-- not: payment 5 has two refunds. Find out why the total moves, then fix it. sum(DISTINCT ...)
-- is not a fix: some customers have two payments with the same amount.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l04.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT cu.customer_id,
       cu.full_name,
       sum(p.amount_minor) AS paid_minor,
       coalesce(sum(r.amount_minor), 0) AS refunded_minor,
       sum(p.amount_minor) - coalesce(sum(r.amount_minor), 0) AS net_minor
FROM customers cu
JOIN accounts a ON a.customer_id = cu.customer_id
JOIN cards c    ON c.account_id = a.account_id
JOIN payments p ON p.card_id = c.card_id
LEFT JOIN refunds r ON r.payment_id = p.payment_id
WHERE p.status = 'succeeded'
GROUP BY cu.customer_id, cu.full_name
ORDER BY cu.customer_id;
