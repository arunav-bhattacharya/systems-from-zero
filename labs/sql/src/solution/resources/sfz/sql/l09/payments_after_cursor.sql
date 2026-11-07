-- Lesson sql-09, exercise 3 of 3: the next page, with a keyset cursor (a trap)
-- Reference answer.

WITH page_cursor AS (
    SELECT timestamptz '2026-03-12 16:42:10+00' AS created_at,
           18::bigint                           AS payment_id
)
SELECT p.payment_id, p.created_at, p.amount_minor
FROM payments p
CROSS JOIN page_cursor c
WHERE (p.created_at, p.payment_id) < (c.created_at, c.payment_id)   -- a row comparison: created_at first,
                                                                    -- payment_id only when created_at ties
ORDER BY p.created_at DESC, p.payment_id DESC                       -- the same columns, the same direction
LIMIT 5;

-- WHERE p.created_at < c.created_at would lose a payment that ties with the cursor's time and
-- has a smaller id. With an index on (created_at, payment_id) this is a seek to the cursor and
-- 5 index entries read, on page 2 or on page 50,000. OFFSET would read and discard every row before.
