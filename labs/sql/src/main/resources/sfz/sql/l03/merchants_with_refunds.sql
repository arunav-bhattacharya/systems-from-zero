-- Lesson sql-03, exercise 3 of 3: merchants that issued a refund, each once
--
-- List the merchants that have at least one refunded payment. A merchant appears once,
-- however many refunds it has.
--
-- Columns: merchant_id, name
-- Order:   merchant_id
--
-- The query below repeats some merchants. Rewrite it as a semi join (EXISTS), without DISTINCT.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l03.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT m.merchant_id, m.name
FROM merchants m
JOIN payments p ON p.merchant_id = m.merchant_id
JOIN refunds r ON r.payment_id = p.payment_id
ORDER BY m.merchant_id;
