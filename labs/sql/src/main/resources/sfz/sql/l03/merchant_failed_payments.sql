-- Lesson sql-03, exercise 2 of 3: keep the merchants with nothing to show (a trap)
--
-- Support wants every merchant with each of its FAILED payments: one row per failed payment,
-- and one row with NULL payment_id and NULL amount_minor for a merchant that has no failed
-- payment (including merchants with no payments at all).
--
-- Columns: merchant_id, name, payment_id, amount_minor
-- Order:   merchant_id, then payment_id
--
-- The query below uses a LEFT JOIN, yet half the merchants are missing. Fix it.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l03.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT m.merchant_id, m.name, p.payment_id, p.amount_minor
FROM merchants m
LEFT JOIN payments p ON p.merchant_id = m.merchant_id
WHERE p.status = 'failed'
ORDER BY m.merchant_id, p.payment_id;
