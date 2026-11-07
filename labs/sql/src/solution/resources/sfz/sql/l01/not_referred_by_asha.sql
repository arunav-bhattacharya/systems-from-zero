-- Lesson sql-01, exercise 1 of 3: customers not referred by Asha (a trap)
-- Reference answer.

SELECT customer_id
FROM customers
-- NULL <> 1 is NULL, and WHERE keeps only rows where the condition is true.
-- IS DISTINCT FROM treats NULL as a value: NULL IS DISTINCT FROM 1 is true.
WHERE referred_by IS DISTINCT FROM 1
ORDER BY customer_id;

-- Also correct: WHERE referred_by <> 1 OR referred_by IS NULL
