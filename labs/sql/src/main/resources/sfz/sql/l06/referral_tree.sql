-- Lesson sql-06, exercise 1 of 3: the whole referral forest
--
-- customers.referred_by points at the customer who referred them (NULL: nobody did). List
-- EVERY customer with:
--   root_id  the customer at the top of their chain (a root is their own root)
--   depth    0 for a root, 1 for someone a root referred, and so on
--   path     bigint[] of customer ids from the root down to this customer, e.g. {2,4,8}
--
-- Columns: customer_id, root_id, depth, path
-- Order:   path (that prints each tree depth first: a parent, then everyone below it)
--
-- The query below only climbs one level with a self join, so anyone deeper is missing.
-- Replace it with WITH RECURSIVE. The chains have no fixed length: your query must not assume one.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l06.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT customer_id, customer_id AS root_id, 0 AS depth, ARRAY[customer_id] AS path
FROM customers
WHERE referred_by IS NULL
UNION ALL
SELECT c.customer_id, r.customer_id, 1, ARRAY[r.customer_id, c.customer_id]
FROM customers c
JOIN customers r ON r.customer_id = c.referred_by
WHERE r.referred_by IS NULL
ORDER BY path;
