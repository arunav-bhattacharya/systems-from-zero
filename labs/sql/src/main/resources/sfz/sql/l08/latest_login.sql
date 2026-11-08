-- Lesson sql-08, exercise 2 of 3: each customer's latest login attempt (a trap)
--
-- For each customer who has logged in at least once: their most recent login attempt,
-- whatever its outcome. "Most recent" is the largest occurred_at; if two attempts of one
-- customer share an occurred_at, the one with the larger event_id is the later one.
-- All four columns must come from that one row of login_events.
--
-- Columns: customer_id, event_id, occurred_at, success, ip
-- Order:   customer_id
--
-- The query below takes max() of every column separately. Each max is right on its own, but
-- they come from different rows: Elena's (customer 5) latest login came from 192.0.2.15, and
-- the query says 203.0.113.7, the attacker's address, which only "wins" because it sorts last.
-- Keep the whole first row of each customer instead (DISTINCT ON is the short way).
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l08.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT customer_id,
       max(event_id) AS event_id,
       max(occurred_at) AS occurred_at,
       bool_or(success) AS success,
       max(ip) AS ip
FROM login_events
GROUP BY customer_id
ORDER BY customer_id;
