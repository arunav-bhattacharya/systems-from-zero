-- Lesson sql-04, exercise 2 of 3: subtotals with ROLLUP (a trap)
-- Reference answer.

SELECT CASE WHEN GROUPING(quarter) = 1 THEN 'all' ELSE quarter END AS quarter,
       CASE WHEN GROUPING(channel) = 1 THEN 'all' ELSE channel END AS channel,   -- a real NULL channel stays NULL
       count(*) AS payments,
       sum(amount_minor) AS volume_minor
FROM (
    -- name the two grouping expressions once, so GROUP BY, GROUPING() and ORDER BY can share them
    SELECT to_char(created_at, 'YYYY-"Q"Q') AS quarter,
           metadata->>'channel' AS channel,
           amount_minor
    FROM payments
    WHERE status = 'succeeded'
) AS s
-- ROLLUP (quarter, channel) = GROUPING SETS ((quarter, channel), (quarter), ())
GROUP BY ROLLUP (quarter, channel)          -- in GROUP BY, a bare name means the input column s.quarter
ORDER BY GROUPING(quarter), s.quarter,      -- grand total (GROUPING = 1) after both quarters
         GROUPING(channel), s.channel;      -- subtotal after its channels; a NULL channel sorts last among them
