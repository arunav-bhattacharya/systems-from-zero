-- Lesson sql-07, exercise 3 of 3: streaks of failed logins (gaps and islands, a trap)
--
-- Security locks an account after 3 failed logins IN A ROW. List every run of 3 or more
-- consecutive failed logins by one customer: failures with no successful login by that
-- customer between them. Logins by other customers do not break a run.
--   failures   how many failed logins the run has
--   first_at   occurred_at of its first failure
--   last_at    occurred_at of its last failure
-- If two logins of one customer share an occurred_at, event_id decides which came first.
--
-- Columns: customer_id, failures, first_at, last_at
-- Order:   customer_id, first_at
--
-- The query below counts each customer's failures in total. Jonas (customer 10) failed twice
-- in April and twice in June, with a success after each pair: 4 failures, never 3 in a row,
-- yet he is listed. GROUP BY does not know about order. Number the logins so that each run
-- gets its own group, then fold the groups.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l07.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT customer_id,
       count(*) AS failures,
       min(occurred_at) AS first_at,
       max(occurred_at) AS last_at
FROM login_events
WHERE NOT success
GROUP BY customer_id
HAVING count(*) >= 3
ORDER BY customer_id, first_at;
