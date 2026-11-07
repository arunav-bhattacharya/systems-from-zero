-- Lesson sql-05, exercise 2 of 3: the average of what? (a trap)
-- Reference answer.

WITH spend AS (                              -- one row per customer: the grain the question is about
    SELECT a.customer_id, sum(p.amount_minor) AS spend_minor
    FROM payments p
    JOIN cards c    ON c.card_id = p.card_id
    JOIN accounts a ON a.account_id = c.account_id
    WHERE p.status = 'succeeded'
    GROUP BY a.customer_id
)
SELECT s.customer_id, cu.full_name, s.spend_minor
FROM spend s
JOIN customers cu ON cu.customer_id = s.customer_id
WHERE s.spend_minor > (SELECT avg(spend_minor) FROM spend)   -- average over customers, not payments
ORDER BY s.customer_id;
-- spend is referenced twice, so PostgreSQL computes it once and reads the stored result twice
