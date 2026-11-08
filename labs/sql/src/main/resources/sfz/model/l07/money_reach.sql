-- Lesson model-07, exercise 2 of 3: where can money from account 106 go? (a trap)
--
-- Every journal in ledger_entries moves money from the account on its negative leg to the
-- account on its positive leg. The CTE transfers below turns that into edges (src -> dst).
-- List every account OTHER THAN 106 that money from account 106 (Farid) can reach by
-- following one or more edges, with the fewest edges needed to get there.
--
-- Columns: account_id, hops
-- Order:   account_id
--
-- The graph has cycles: 106 pays merchant 304, and 304 refunds 106. Without the line marked
-- below, this query never finishes (the tests give up after 10 seconds). With it, it finishes
-- and is wrong. Make the recursion stop on its own and return the complete answer:
-- CYCLE ... SET ... USING (PostgreSQL 14 and later) or a path array both work.
-- Check it: ./gradlew :sql:test --tests 'sfz.model.l07.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

WITH RECURSIVE transfers AS (
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
    WHERE r.hops < 2            -- <- the line: a depth cap that "fixes" the endless loop
)
SELECT account_id, min(hops) AS hops
FROM reach
GROUP BY account_id
ORDER BY account_id;
