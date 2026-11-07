-- Lesson sql-05, exercise 2 of 3: the average of what? (a trap)
--
-- A customer's spend is the sum of their SUCCEEDED payments. List the customers whose spend
-- is above the average spend of the customers who have any spend at all.
--
-- Columns: customer_id, full_name, spend_minor
-- Order:   customer_id
--
-- The query below compares each customer's spend with the average PAYMENT, which is a
-- much smaller number. Compute spend per customer once, in a CTE, and use it twice: once
-- for the average and once for the rows you return.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l05.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT cu.customer_id,
       cu.full_name,
       sum(p.amount_minor) AS spend_minor
FROM payments p
JOIN cards c      ON c.card_id = p.card_id
JOIN accounts a   ON a.account_id = c.account_id
JOIN customers cu ON cu.customer_id = a.customer_id
WHERE p.status = 'succeeded'
GROUP BY cu.customer_id, cu.full_name
HAVING sum(p.amount_minor) > (SELECT avg(amount_minor) FROM payments WHERE status = 'succeeded')
ORDER BY cu.customer_id;
