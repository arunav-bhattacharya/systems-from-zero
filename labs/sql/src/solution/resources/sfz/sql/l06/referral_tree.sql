-- Lesson sql-06, exercise 1 of 3: the whole referral forest
-- Reference answer.

WITH RECURSIVE tree AS (
    -- anchor: the roots. They fill the first working table.
    SELECT customer_id, customer_id AS root_id, 0 AS depth, ARRAY[customer_id] AS path
    FROM customers
    WHERE referred_by IS NULL
  UNION ALL
    -- recursive term: runs against the rows the previous round added, until it adds none
    SELECT c.customer_id, t.root_id, t.depth + 1, t.path || c.customer_id
    FROM customers c
    JOIN tree t ON c.referred_by = t.customer_id
)
SELECT customer_id, root_id, depth, path
FROM tree
ORDER BY path;                 -- arrays compare element by element, so this is depth-first order
