-- Lesson sql-09, exercise 1 of 3: every merchant's three largest payments (a trap)
--
-- For EVERY merchant (all 8 of them), its three largest SUCCEEDED payments, largest first.
-- When two payments have the same amount, the lower payment_id comes first.
--   place   1, 2 or 3
-- A merchant with no succeeded payment still appears, once, with NULL place, payment_id and
-- amount_minor: the dashboard shows it as "no sales yet".
--
-- Columns: merchant_id, place, payment_id, amount_minor
-- Order:   merchant_id, place
--
-- The query below takes the three largest payments overall and then joins them to merchants,
-- so it returns three rows in total. The subquery needs to run once per merchant, with that
-- merchant's id: that is what LATERAL is for. Then make sure merchants 6 and 8 survive the join.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l09.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT m.merchant_id,
       row_number() OVER (ORDER BY t.amount_minor DESC, t.payment_id) AS place,
       t.payment_id,
       t.amount_minor
FROM merchants m
JOIN (SELECT merchant_id, payment_id, amount_minor
      FROM payments
      WHERE status = 'succeeded'
      ORDER BY amount_minor DESC, payment_id
      LIMIT 3) AS t ON t.merchant_id = m.merchant_id
ORDER BY m.merchant_id, place;
