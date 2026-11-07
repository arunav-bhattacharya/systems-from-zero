-- Lesson sql-07, exercise 1 of 3: the leaderboard of the largest payments (a trap)
--
-- Every SUCCEEDED payment that places in the top 12 by amount_minor, largest first. Tied
-- amounts share a place, and the place after a tie skips: two payments tied for 2nd place are
-- followed by 4th place (that is how a race is scored). So the answer can have more than 12 rows.
--
-- Columns: place, payment_id, amount_minor
-- Order:   place, payment_id
--
-- The query below numbers the rows one by one and stops after 12. Payments 17, 18 and 19 all
-- have 18999: it gives them different places and cuts one of them off, and which one it cuts
-- can change from run to run. Use the ranking function that lets ties share a place, and
-- filter on the place in an outer query (a window function is not allowed in WHERE).
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l07.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT row_number() OVER (ORDER BY amount_minor DESC) AS place,
       payment_id,
       amount_minor
FROM payments
WHERE status = 'succeeded'
ORDER BY place
LIMIT 12;
