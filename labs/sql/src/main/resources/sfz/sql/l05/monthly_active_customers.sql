-- Lesson sql-05, exercise 3 of 3: active, new and returning customers per month
--
-- A customer is ACTIVE in a month (to_char(created_at, 'YYYY-MM')) if they made at least one
-- SUCCEEDED payment in it. An active customer is NEW in a month if they had no succeeded
-- payment in any earlier month, and RETURNING otherwise.
--
-- Columns: month, active_customers, new_customers, returning_customers
-- Order:   month
--
-- Build it in steps with WITH: first (customer, month) pairs, then each customer's first
-- month, then count. The query below counts payments, not customers, and knows nothing
-- about earlier months.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l05.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT to_char(p.created_at, 'YYYY-MM') AS month,
       count(*) AS active_customers,
       count(*) AS new_customers,
       0::bigint AS returning_customers
FROM payments p
WHERE p.status = 'succeeded'
GROUP BY to_char(p.created_at, 'YYYY-MM')
ORDER BY month;
