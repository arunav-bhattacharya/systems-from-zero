-- Lesson sql-07, exercise 1 of 3: the leaderboard of the largest payments (a trap)
-- Reference answer.

SELECT place, payment_id, amount_minor
FROM (
    SELECT payment_id,
           amount_minor,
           rank() OVER (ORDER BY amount_minor DESC) AS place   -- ties share a place; the next place skips
    FROM payments
    WHERE status = 'succeeded'           -- WHERE runs first, so failed payments never get a place
) AS ranked
WHERE place <= 12                        -- a window result can only be filtered one level up
ORDER BY place, payment_id;              -- payment_id fixes the order inside a tie

-- row_number() would give 17, 18 and 19 places 11, 12 and 13 in no fixed order, and LIMIT 12
-- would drop one of them. dense_rank() would not skip: the payment after the tie would be 12th.
-- FETCH FIRST 12 ROWS WITH TIES (lesson 1) returns the same rows, but cannot print the place.
