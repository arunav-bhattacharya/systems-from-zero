-- Lesson sql-10, exercise 2 of 3: ingest payment messages exactly once (a trap)
--
-- The card network delivers each payment message at least once: the same message can arrive
-- twice, and two copies can arrive at the same moment on two consumers. payment_uid is the
-- network's idempotency key, and payments has a UNIQUE index on it.
--
-- The tests put the messages in a temporary table, one row per message:
--   inbound (payment_uid uuid, card_id bigint, merchant_id bigint, amount_minor bigint,
--            status text, created_at timestamptz)
-- (In psql, create it with CREATE TEMP TABLE inbound AS SELECT ...; the lesson shows how.)
--
-- Write ONE statement that, for each message:
--   * inserts the payment when no payment has its payment_uid yet;
--   * when the payment exists and is still 'pending', and the message carries a final status
--     ('succeeded' or 'failed'), sets that status;
--   * otherwise changes nothing: a repeated message, or a late 'pending' after the final status.
-- It must never fail with a duplicate key error (23505), even when another session ingests the
-- same message at the same moment.
-- Return one row for each payment it inserted or changed, and none for the other messages:
--
-- Columns: payment_id, old_status, new_status      (old_status is NULL for an insert)
-- Order:   any
--
-- The statement below checks first and inserts only if it found nothing. It never updates a
-- pending payment, and when two sessions run it at once, both checks find nothing.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l10.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

INSERT INTO payments (payment_uid, card_id, merchant_id, amount_minor, status, created_at)
SELECT i.payment_uid, i.card_id, i.merchant_id, i.amount_minor, i.status, i.created_at
FROM inbound i
WHERE NOT EXISTS (SELECT 1 FROM payments p WHERE p.payment_uid = i.payment_uid)
RETURNING payment_id, NULL::text AS old_status, status AS new_status;
