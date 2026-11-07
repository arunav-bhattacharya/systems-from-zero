-- Lesson sql-09, exercise 1 of 3: every merchant's three largest payments (a trap)
-- Reference answer.

SELECT m.merchant_id, t.place, t.payment_id, t.amount_minor
FROM merchants m
LEFT JOIN LATERAL (                      -- LEFT: a merchant whose subquery returns nothing keeps one row of NULLs
    SELECT p.payment_id,
           p.amount_minor,
           row_number() OVER (ORDER BY p.amount_minor DESC, p.payment_id) AS place   -- sees only this merchant's rows
    FROM payments p
    WHERE p.merchant_id = m.merchant_id  -- LATERAL lets the subquery use the current merchant row
      AND p.status = 'succeeded'
    ORDER BY p.amount_minor DESC, p.payment_id
    LIMIT 3                              -- runs once per merchant, so this is 3 per merchant
) AS t ON true                           -- the subquery already did the matching
ORDER BY m.merchant_id, t.place;

-- The window version gives the same rows (it reads every payment once and sorts them all):
--   SELECT m.merchant_id, r.place, r.payment_id, r.amount_minor
--   FROM merchants m
--   LEFT JOIN (SELECT merchant_id, payment_id, amount_minor,
--                     row_number() OVER (PARTITION BY merchant_id ORDER BY amount_minor DESC, payment_id) AS place
--              FROM payments WHERE status = 'succeeded') r
--          ON r.merchant_id = m.merchant_id AND r.place <= 3
--   ORDER BY m.merchant_id, r.place;
