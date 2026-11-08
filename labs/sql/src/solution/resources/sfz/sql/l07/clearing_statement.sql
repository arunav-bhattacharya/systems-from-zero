-- Lesson sql-07, exercise 1 of 3: a statement for the clearing account (a trap)
-- Reference answer.

SELECT entry_id,
       created_at,
       amount_minor,
       sum(amount_minor) OVER (ORDER BY created_at, entry_id) AS balance_minor
FROM ledger_entries
WHERE account_id = 900
ORDER BY created_at, entry_id;

-- With ORDER BY created_at alone, the default frame is RANGE BETWEEN UNBOUNDED PRECEDING AND
-- CURRENT ROW, and in RANGE mode "current row" means the current row and all its peers: every
-- row with the same created_at. So the four deposits at 09:00 each added all four.
-- The tiebreaker makes every row its own peer group. ROWS BETWEEN UNBOUNDED PRECEDING AND
-- CURRENT ROW also stops the jump, but without entry_id in the ORDER BY the order of the tied
-- rows, and so their balances, would be up to PostgreSQL. Writing both is clearest:
--   sum(amount_minor) OVER (ORDER BY created_at, entry_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
