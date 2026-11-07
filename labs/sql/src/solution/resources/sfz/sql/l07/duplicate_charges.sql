-- Lesson sql-07, exercise 2 of 3: likely double charges (a trap)
-- Reference answer.

SELECT payment_id, duplicate_of, seconds_after
FROM (
    SELECT payment_id,
           created_at,
           lag(payment_id) OVER w AS duplicate_of,             -- the previous charge in the same window
           lag(created_at) OVER w AS previous_at,
           extract(epoch FROM created_at - lag(created_at) OVER w) AS seconds_after
    FROM payments
    WHERE status = 'succeeded'                                 -- before the window: failures never become "the previous one"
    WINDOW w AS (PARTITION BY card_id, merchant_id, amount_minor   -- "the same charge": all three must match
                 ORDER BY created_at, payment_id)
) AS s
WHERE created_at - previous_at <= interval '5 minutes'        -- NULL for the first charge, so it drops out
ORDER BY payment_id;

-- Without card_id in the partition, two customers buying the same 2.75 ride a minute apart
-- would look like one customer charged twice.
