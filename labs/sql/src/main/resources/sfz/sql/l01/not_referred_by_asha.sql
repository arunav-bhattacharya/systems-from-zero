-- Lesson sql-01, exercise 1 of 3: customers not referred by Asha (a trap)
--
-- customers.referred_by holds the id of the customer who referred them, or NULL when
-- nobody did. List every customer who was NOT referred by customer 1 (Asha Rao). Customers
-- that nobody referred were not referred by Asha either, so they belong in the answer.
--
-- Columns: customer_id
-- Order:   customer_id, ascending
--
-- The query below looks right and returns rows, but the tests say it is wrong.
-- Run it in psql with \pset null '∅' and compare it with SELECT customer_id, referred_by FROM customers.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l01.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT customer_id
FROM customers
WHERE referred_by <> 1
ORDER BY customer_id;
