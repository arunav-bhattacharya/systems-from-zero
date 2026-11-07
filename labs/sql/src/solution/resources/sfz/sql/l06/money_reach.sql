-- Lesson sql-06, exercise 2 of 3: where can money from account 106 go? (a trap)
-- Reference answer.

WITH RECURSIVE transfers AS (                -- a plain CTE may sit in a WITH RECURSIVE list
    SELECT DISTINCT d.account_id AS src, c.account_id AS dst
    FROM ledger_entries d
    JOIN ledger_entries c ON c.journal_id = d.journal_id AND c.amount_minor > 0
    WHERE d.amount_minor < 0
),
reach AS (
    SELECT t.dst AS account_id, 1 AS hops
    FROM transfers t
    WHERE t.src = 106
  UNION ALL
    SELECT t.dst, r.hops + 1
    FROM reach r
    JOIN transfers t ON t.src = r.account_id
) CYCLE account_id SET is_cycle USING path   -- a row whose account is already on its path is marked and not followed
SELECT account_id, min(hops) AS hops         -- several paths reach some accounts: keep the shortest
FROM reach
WHERE NOT is_cycle                           -- the marked rows repeat an account; drop them
  AND account_id <> 106                      -- money comes back to 106 through refunds; the start is not an answer
GROUP BY account_id
ORDER BY account_id;

-- The same stop condition by hand (works on any PostgreSQL, and in Oracle):
--   reach (account_id, hops, path) AS (
--       SELECT t.dst, 1, ARRAY[106, t.dst] FROM transfers t WHERE t.src = 106
--     UNION ALL
--       SELECT t.dst, r.hops + 1, r.path || t.dst
--       FROM reach r JOIN transfers t ON t.src = r.account_id
--       WHERE t.dst <> ALL (r.path)          -- never step onto an account already on this path
--   )
