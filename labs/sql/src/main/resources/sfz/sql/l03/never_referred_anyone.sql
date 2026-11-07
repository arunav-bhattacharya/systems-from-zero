-- Lesson sql-03, exercise 1 of 3: customers who never referred anyone (a trap)
--
-- A customer "referred someone" when another customer's referred_by holds their id.
-- List the customers who never referred anyone.
--
-- Columns: customer_id, full_name
-- Order:   customer_id
--
-- The query below reads well and returns nothing. Find out why, then rewrite it as an anti join.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l03.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT customer_id, full_name
FROM customers
WHERE customer_id NOT IN (SELECT referred_by FROM customers)
ORDER BY customer_id;
