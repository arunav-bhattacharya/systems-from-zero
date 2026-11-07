-- Lesson sql-02, exercise 3 of 3: find drift in a denormalized balance (a trap)
-- Reference answer.

SELECT account_id, cached, ledger
FROM (
    SELECT a.account_id,
           a.balance_minor AS cached,
           -- sum() over zero rows is NULL, not 0, and "700 <> NULL" is NULL, so WHERE drops it
           coalesce((SELECT sum(e.amount_minor)
                     FROM ledger_entries e
                     WHERE e.account_id = a.account_id), 0) AS ledger
    FROM accounts a
) AS t
WHERE cached <> ledger
ORDER BY account_id;
