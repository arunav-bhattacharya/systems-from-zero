-- Lesson sql-08, exercise 2 of 3: each customer's latest login attempt (a trap)
-- Reference answer.

SELECT DISTINCT ON (customer_id)         -- keep the first row of each customer...
       customer_id, event_id, occurred_at, success, ip
FROM login_events
ORDER BY customer_id,                    -- ...where "first" is decided by this ORDER BY, which must
         occurred_at DESC,               -- start with the DISTINCT ON column
         event_id DESC;                  -- the tiebreaker for two attempts at the same instant

-- The same with a window, portable to Oracle and others:
--   SELECT customer_id, event_id, occurred_at, success, ip
--   FROM (SELECT l.*, row_number() OVER (PARTITION BY customer_id ORDER BY occurred_at DESC, event_id DESC) AS rn
--         FROM login_events l) s
--   WHERE rn = 1
--   ORDER BY customer_id;
