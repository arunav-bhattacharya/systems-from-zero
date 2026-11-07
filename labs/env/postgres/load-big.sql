-- Systems from Zero, SQL track: the large data set for the index and EXPLAIN lessons.
--
-- Builds schema "big" in database course, with the same tables as the course schema
-- (course/schema.sql), and fills them with generate_series. The small seed in schema public
-- is not touched.
-- Default size: 1,000,000 payments, 50,000 customers, 2,500 merchants, 100,000 cards,
-- about 3.4 million ledger rows and 500,000 logins.
--
-- Run it from the labs folder, with the service up:
--   docker compose -f env/postgres.yml exec db psql -U sfz -d course -f /seed/load-big.sql
-- Change the size with -v payments=2000000 (customers, merchants and cards scale with it).
-- Query it with:  SET search_path = big, public;
-- Remove it with: DROP SCHEMA big CASCADE;   (down -v also deletes it, with everything else)
--
-- random() is seeded with setseed(), so a run in a fresh session builds the same rows.
-- Account ids: customer accounts 1..C, second accounts C+1..C+C/2 (even customers),
-- merchant accounts M0+1..M0+merchants where M0 = C+C/2, then one internal clearing account.

\set ON_ERROR_STOP on
\if :{?payments}
\else
    \set payments 1000000
\endif
SELECT :payments / 20 AS customers, :payments / 400 AS merchants, :payments / 10 AS cards \gset
SELECT :customers + :customers / 2 AS merchant_base,
       :customers + :customers / 2 + :merchants + 1 AS clearing \gset
\echo building schema big: :payments payments, :customers customers, :merchants merchants, :cards cards
\timing on

DROP SCHEMA IF EXISTS big CASCADE;
CREATE SCHEMA big;
SET search_path = big, public;
SET client_min_messages = warning;
\i /seed/course/schema.sql
RESET client_min_messages;

SELECT setseed(0.42);

INSERT INTO mcc_codes (mcc, description) VALUES
    ('4111', 'Commuter transport'),
    ('5411', 'Grocery stores, supermarkets'),
    ('5732', 'Electronics stores'),
    ('5812', 'Eating places, restaurants'),
    ('5814', 'Fast food restaurants'),
    ('5999', 'Miscellaneous retail'),
    ('7011', 'Hotels, motels, resorts');

INSERT INTO merchants (merchant_id, name, mcc, country_code, onboarded_at)
SELECT g, 'Merchant ' || g,
       (ARRAY['5411', '5812', '5999', '4111', '5732', '7011'])[1 + floor(random() * 6)::int],
       (ARRAY['US', 'GB', 'IN', 'DE', 'FR', 'SG'])[1 + floor(random() * 6)::int],
       timestamptz '2022-01-01 00:00+00' + random() * interval '4 years'
FROM generate_series(1, :merchants) AS g;

-- referred_by points only to lower ids, so the referral graph is a forest; about 30% are referred
INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at)
SELECT g, 'user' || g || '@example.com', 'Customer ' || g,
       (ARRAY['US', 'GB', 'IN', 'DE', 'FR', 'SG', 'CA', 'AU'])[1 + floor(random() * 8)::int],
       CASE WHEN g > 100 AND random() < 0.3 THEN 1 + floor(random() * (g - 1))::bigint END,
       timestamptz '2023-01-01 00:00+00' + g * interval '15 minutes'
FROM generate_series(1, :customers) AS g;

INSERT INTO accounts (account_id, kind, customer_id, status, opened_at)
SELECT customer_id, 'customer', customer_id,
       CASE WHEN random() < 0.97 THEN 'active' ELSE 'frozen' END, created_at
FROM customers;
INSERT INTO accounts (account_id, kind, customer_id, opened_at)
SELECT :customers + customer_id / 2, 'customer', customer_id, created_at + interval '90 days'
FROM customers WHERE customer_id % 2 = 0;
INSERT INTO accounts (account_id, kind, merchant_id, opened_at)
SELECT :merchant_base + merchant_id, 'merchant', merchant_id, onboarded_at FROM merchants;
INSERT INTO accounts (account_id, kind, opened_at) VALUES (:clearing, 'internal', '2022-01-01 00:00+00');

INSERT INTO cards (card_id, account_id, brand, pan_last4, expires_on, status)
SELECT g, 1 + floor(random() * :merchant_base)::bigint,
       (ARRAY['visa', 'mastercard', 'amex'])[1 + floor(random() * 3)::int],
       lpad(floor(random() * 10000)::int::text, 4, '0'),
       date '2027-01-01' + floor(random() * 1460)::int,
       CASE WHEN random() < 0.9 THEN 'active' ELSE 'blocked' END
FROM generate_series(1, :cards) AS g;
-- one primary card per account: the lowest active card id
UPDATE cards c SET is_primary = true
FROM (SELECT DISTINCT ON (account_id) card_id FROM cards WHERE status = 'active'
      ORDER BY account_id, card_id) AS p
WHERE c.card_id = p.card_id;

-- Payments over 300 days from 2026-01-01. Ids follow time, so created_at is physically ordered.
-- Low merchant ids are hot (power(random(), 3)); amounts are log-uniform, about $0.55 to $220.
-- The subquery has volatile columns, so PostgreSQL does not flatten it: r is drawn once per row.
INSERT INTO payments (payment_id, payment_uid, card_id, merchant_id, amount_minor, status, created_at, metadata)
SELECT g,
       (lpad(to_hex((extract(epoch FROM ts) * 1000)::bigint), 12, '0')
            || '7' || lpad(to_hex(g % 4096), 3, '0') || '8' || lpad(to_hex(g), 15, '0'))::uuid,
       1 + floor(random() * :cards)::bigint,
       1 + floor(:merchants * power(random(), 3))::bigint,
       round(exp(4 + random() * 6))::bigint,
       CASE WHEN r < 0.93 THEN 'succeeded' WHEN r < 0.99 THEN 'failed' ELSE 'pending' END,
       ts,
       jsonb_build_object(
           'channel', (ARRAY['web', 'ios', 'android', 'pos'])[1 + floor(random() * 4)::int],
           'risk', jsonb_build_object(
               'score', floor(random() * 100)::int,
               'rules', CASE WHEN random() < 0.05 THEN '["velocity"]'::jsonb
                             WHEN random() < 0.05 THEN '["geo_mismatch"]'::jsonb
                             ELSE '[]'::jsonb END))
FROM (SELECT g, random() AS r,
             timestamptz '2026-01-01 00:00+00' + g * (interval '300 days' / :payments)
                 + random() * interval '10 seconds' AS ts
      FROM generate_series(1, :payments) AS g) AS s;

-- identity sequences catch up before any insert that uses the default id
SELECT setval(pg_get_serial_sequence('big.merchants', 'merchant_id'), (SELECT max(merchant_id) FROM merchants));
SELECT setval(pg_get_serial_sequence('big.customers', 'customer_id'), (SELECT max(customer_id) FROM customers));
SELECT setval(pg_get_serial_sequence('big.accounts', 'account_id'), (SELECT max(account_id) FROM accounts));
SELECT setval(pg_get_serial_sequence('big.cards', 'card_id'), (SELECT max(card_id) FROM cards));
SELECT setval(pg_get_serial_sequence('big.payments', 'payment_id'), (SELECT max(payment_id) FROM payments));

-- about 0.05% near-duplicates: same card, merchant and amount within 4 minutes, flagged in metadata
INSERT INTO payments (card_id, merchant_id, amount_minor, status, created_at, metadata)
SELECT card_id, merchant_id, amount_minor, status,
       created_at + random() * interval '4 minutes',
       metadata || '{"injected_dup": true}'
FROM payments WHERE status = 'succeeded' AND random() < 0.0005;
UPDATE payments
SET payment_uid = (lpad(to_hex((extract(epoch FROM created_at) * 1000)::bigint), 12, '0')
                   || '7' || lpad(to_hex(payment_id % 4096), 3, '0') || '8' || lpad(to_hex(payment_id), 15, '0'))::uuid
WHERE payment_id > :payments;

-- about 2% of succeeded payments are refunded: 70% in full, 30% in part
INSERT INTO refunds (payment_id, amount_minor, reason, created_at)
SELECT payment_id,
       CASE WHEN random() < 0.7 THEN amount_minor ELSE greatest(1, (amount_minor * random())::bigint) END,
       (ARRAY['customer_request', 'duplicate', 'fraud'])[1 + floor(random() * 3)::int],
       created_at + random() * interval '20 days'
FROM payments WHERE status = 'succeeded' AND random() < 0.02;

-- Ledger, loaded by kind (deposits, then payments, then refunds), so entry_id does not follow
-- created_at. Each CTE is used twice, so it is materialized and nextval() runs once per journal.
WITH d AS (
    SELECT a.account_id, (100000 + floor(random() * 400000))::bigint AS amt,
           m + random() * interval '3 days' AS ts, nextval('journal_id_seq') AS journal_id
    FROM accounts a
    CROSS JOIN generate_series(timestamptz '2026-01-01 00:00+00', timestamptz '2026-10-01 00:00+00', interval '1 month') AS m
    WHERE a.kind = 'customer'
)
INSERT INTO ledger_entries (journal_id, account_id, entry_type, amount_minor, created_at)
SELECT journal_id, account_id, 'deposit',  amt, ts FROM d
UNION ALL
SELECT journal_id, :clearing,  'deposit', -amt, ts FROM d;

WITH j AS (
    SELECT p.payment_id, p.merchant_id, p.amount_minor, p.created_at, c.account_id AS card_account_id,
           nextval('journal_id_seq') AS journal_id
    FROM payments p JOIN cards c ON c.card_id = p.card_id
    WHERE p.status = 'succeeded'
)
INSERT INTO ledger_entries (journal_id, account_id, payment_id, entry_type, amount_minor, created_at)
SELECT journal_id, card_account_id,               payment_id, 'payment', -amount_minor, created_at FROM j
UNION ALL
SELECT journal_id, :merchant_base + merchant_id,  payment_id, 'payment',  amount_minor, created_at FROM j;

WITH r AS (
    SELECT f.refund_id, f.payment_id, f.amount_minor, f.created_at,
           c.account_id AS card_account_id, :merchant_base + p.merchant_id AS merchant_account_id,
           nextval('journal_id_seq') AS journal_id
    FROM refunds f JOIN payments p ON p.payment_id = f.payment_id JOIN cards c ON c.card_id = p.card_id
)
INSERT INTO ledger_entries (journal_id, account_id, payment_id, refund_id, entry_type, amount_minor, created_at)
SELECT journal_id, card_account_id,     payment_id, refund_id, 'refund',  amount_minor, created_at FROM r
UNION ALL
SELECT journal_id, merchant_account_id, payment_id, refund_id, 'refund', -amount_minor, created_at FROM r;

UPDATE accounts a SET balance_minor = s.bal
FROM (SELECT account_id, sum(amount_minor) AS bal FROM ledger_entries GROUP BY account_id) AS s
WHERE a.account_id = s.account_id;

-- logins: background noise with 10% failures, plus 200 bursts of 8 failures from one address
INSERT INTO login_events (customer_id, occurred_at, success, ip)
SELECT 1 + floor(random() * :customers)::bigint,
       timestamptz '2026-01-01 00:00+00' + random() * interval '300 days',
       random() < 0.9,
       ('10.' || floor(random() * 256) || '.' || floor(random() * 256) || '.' || floor(random() * 256))::inet
FROM generate_series(1, :payments / 2);
INSERT INTO login_events (customer_id, occurred_at, success, ip)
SELECT s.c, s.t0 + k * interval '20 seconds', false, '203.0.113.7'
FROM (SELECT 1 + floor(random() * :customers)::bigint AS c,
             timestamptz '2026-03-01 00:00+00' + random() * interval '200 days' AS t0
      FROM generate_series(1, 200)) AS s
CROSS JOIN generate_series(1, 8) AS k;

INSERT INTO jobs (kind, payload, run_after)
SELECT (ARRAY['send_receipt', 'settle_merchant', 'fraud_review'])[1 + floor(random() * 3)::int],
       jsonb_build_object('payment_id', 1 + floor(random() * :payments)::bigint),
       timestamptz '2026-10-27 00:00+00' + random() * interval '1 hour'
FROM generate_series(1, 10000);

\timing off
VACUUM (ANALYZE);   -- fresh statistics and a visibility map, so plans and index-only scans are realistic

SELECT c.relname AS "table", c.reltuples::bigint AS "rows (estimate)",
       pg_size_pretty(pg_total_relation_size(c.oid)) AS "size with indexes"
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'big' AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;
