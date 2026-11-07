-- Lesson sql-05, exercise 1 of 3: bigger than usual for this merchant (a trap)
--
-- List the SUCCEEDED payments whose amount is larger than the average succeeded amount of
-- THEIR OWN merchant, with that average rounded to whole cents.
--
-- Columns: payment_id, merchant_id, amount_minor, merchant_avg
-- Order:   payment_id
--
-- The query below looks correlated, but it is not: it compares every payment with the
-- average of all merchants together. Find out which table each merchant_id in the subquery
-- refers to, then fix it. A correlated subquery or a join to per-merchant averages both work.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l05.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT p.payment_id,
       p.merchant_id,
       p.amount_minor,
       round((SELECT avg(amount_minor) FROM payments
              WHERE status = 'succeeded' AND merchant_id = merchant_id)) AS merchant_avg
FROM payments p
WHERE p.status = 'succeeded'
  AND p.amount_minor > (SELECT avg(amount_minor) FROM payments
                        WHERE status = 'succeeded' AND merchant_id = merchant_id)
ORDER BY p.payment_id;
