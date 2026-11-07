-- Lesson sql-05, exercise 3 of 3: active, new and returning customers per month
-- Reference answer.

WITH activity AS (                           -- step 1: who was active when, one row per pair
    SELECT DISTINCT a.customer_id, to_char(p.created_at, 'YYYY-MM') AS month
    FROM payments p
    JOIN cards c    ON c.card_id = p.card_id
    JOIN accounts a ON a.account_id = c.account_id
    WHERE p.status = 'succeeded'             -- a failed payment never makes anyone active or new
),
first_month AS (                             -- step 2: each customer's first active month
    SELECT customer_id, min(month) AS month  -- 'YYYY-MM' text sorts in time order
    FROM activity
    GROUP BY customer_id
)
SELECT ac.month,                             -- step 3: count customers, split with FILTER
       count(*) AS active_customers,
       count(*) FILTER (WHERE ac.month = f.month) AS new_customers,
       count(*) FILTER (WHERE ac.month > f.month) AS returning_customers
FROM activity ac
JOIN first_month f ON f.customer_id = ac.customer_id
GROUP BY ac.month
ORDER BY ac.month;
