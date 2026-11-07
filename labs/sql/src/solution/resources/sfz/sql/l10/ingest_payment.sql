-- Lesson sql-10, exercise 2 of 3: ingest payment messages exactly once (a trap)
-- Reference answer.

INSERT INTO payments AS p (payment_uid, card_id, merchant_id, amount_minor, status, created_at)
SELECT payment_uid, card_id, merchant_id, amount_minor, status, created_at
FROM inbound
ON CONFLICT (payment_uid) DO UPDATE                -- the unique index decides, even mid-race:
SET status = EXCLUDED.status                       -- EXCLUDED is the row the message proposed
WHERE p.status = 'pending'                         -- only a pending payment moves,
  AND EXCLUDED.status <> 'pending'                 -- and only to a final status
RETURNING p.payment_id,
          old.status AS old_status,                -- PostgreSQL 18: NULL when the row was inserted
          new.status AS new_status;

-- A conflicting row whose DO UPDATE ... WHERE is false is left alone and returns nothing, which
-- is what makes a repeated message invisible. When a second session ingests the same new uid
-- at the same moment, its INSERT waits for the first session's transaction, then takes the
-- DO UPDATE branch instead of failing with 23505.
-- Two copies of one uid in the same batch fail with "ON CONFLICT DO UPDATE command cannot affect
-- row a second time": deduplicate the batch first (SELECT DISTINCT ON (payment_uid) ...).
