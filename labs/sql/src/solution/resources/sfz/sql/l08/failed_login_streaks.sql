-- Lesson sql-08, exercise 3 of 3: streaks of failed logins (gaps and islands, a trap)
-- Reference answer.

WITH numbered AS (
    -- Number ALL of a customer's logins, then number them again within each outcome. Inside a
    -- run of one outcome both numbers go up by 1 per row, so their difference stays the same;
    -- a login with the other outcome moves the first number on and starts a new difference.
    SELECT customer_id,
           occurred_at,
           success,
           row_number() OVER (PARTITION BY customer_id ORDER BY occurred_at, event_id)
         - row_number() OVER (PARTITION BY customer_id, success ORDER BY occurred_at, event_id) AS island
    FROM login_events                    -- no WHERE NOT success here: filtering first would make every
)                                        -- failure look consecutive
SELECT customer_id,
       count(*) AS failures,
       min(occurred_at) AS first_at,
       max(occurred_at) AS last_at
FROM numbered
WHERE NOT success                        -- now it is safe to keep only the failure runs
GROUP BY customer_id, island             -- one group per run (island is unique per customer and outcome)
HAVING count(*) >= 3
ORDER BY customer_id, first_at;

-- The other method: flag the rows that start a run, then number the runs with a running sum.
--   flagged AS (SELECT ..., CASE WHEN lag(success) OVER w = success THEN 0 ELSE 1 END AS starts_run ...
--               WINDOW w AS (PARTITION BY customer_id ORDER BY occurred_at, event_id)),
--   runs AS (SELECT ..., sum(starts_run) OVER (PARTITION BY customer_id ORDER BY occurred_at, event_id) AS run ...)
