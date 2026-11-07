-- Lesson sql-01, exercise 2 of 3: four counts in one row (count(*) or count(column)?)
-- Reference answer.

SELECT count(*)                    AS customers,   -- counts rows
       count(referred_by)          AS referred,    -- counts rows where referred_by is not NULL
       count(DISTINCT referred_by) AS referrers,   -- counts different non-NULL values
       count(*) - count(referred_by) AS organic    -- the rows the second count skipped
FROM customers;

-- Also correct for organic: count(*) FILTER (WHERE referred_by IS NULL), which lesson 4 covers.
