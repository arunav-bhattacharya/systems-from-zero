-- Lesson sql-03, exercise 1 of 3: customers who never referred anyone (a trap)
-- Reference answer.

SELECT c.customer_id, c.full_name
FROM customers c
-- an anti join: keep c when no row matches. NOT EXISTS only asks "is there a row?",
-- so the NULLs in referred_by cannot turn the answer into unknown the way NOT IN does
WHERE NOT EXISTS (
    SELECT 1
    FROM customers r
    WHERE r.referred_by = c.customer_id
)
ORDER BY c.customer_id;
