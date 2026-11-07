-- Systems from Zero, SQL track: the small seed (run after schema.sql).
--
-- About 250 rows, small enough to check by hand and fixed: no random(), no now(). Every lab
-- test and every psql Try-it in the track sees exactly this data. All times are UTC.
-- env/postgres/course/seed.sql is an exact copy; SeedFilesInSyncTest checks it.
--
-- Facts the lessons rely on (keep them true if you add rows):
--   customers   13. referred_by is NULL for 1, 2, 7, 9, 11. Referral tree: 1 -> 3 -> 6, 1 -> 5 -> 10,
--               2 -> 4 -> 8 -> 13, 7 -> 12. Customers 6, 9, 10, 11, 12, 13 never referred anyone.
--               11 (Kofi) has no account. 12 (Lena) has an account but no card.
--               9 (Ivy) has two accounts with 5,000 each and no payments (the write-skew fixture).
--   accounts    customer accounts are 100 + customer_id; second accounts are 202 (Ben) and 209 (Ivy);
--               merchant settlement accounts are 300 + merchant_id; 900 is the internal clearing
--               account that funds deposits. 108 is frozen. 112 has no ledger entries.
--   merchants   8. 6 (Paper Lantern Books) and 8 (Sunrise Grocers) have no payments.
--   payments    37, January to June 2026: 30 succeeded, 5 failed, 2 pending.
--               13 is at exactly 2026-03-01 00:00, 22 at 2026-03-31 23:59:59.5, 23 at 2026-04-01 00:00.
--               17, 18 and 19 tie on amount (18999); 18 repeats 17 two minutes later (a duplicate).
--   refunds     6. Payment 5 has two partial refunds. Refunds touch merchants 1, 4 and 5 only.
--   ledger      every succeeded payment, refund and deposit is a two-leg journal that sums to zero,
--               and accounts.balance_minor equals the sum of each account's entries.
--               Journal ids: deposits 1..16, payment p is 1000 + p, refund r is 2000 + r.
--               Deposits 1 to 4 share created_at 2026-01-02 09:00, so account 900's first four
--               entries tie on time (the window-frame lesson); 5 and 6, and 9 and 10, tie as well.
--   logins      27. Customer 5: two successes, then six failures in two minutes from 203.0.113.7,
--               then her own success (events 4, 10 to 17). Customer 10 fails twice and then succeeds,
--               in April and again in June: four failures, never three in a row. Customer 6 fails once.

SET TIME ZONE 'UTC';

INSERT INTO mcc_codes (mcc, description) VALUES
    ('4111', 'Commuter transport'),
    ('5411', 'Grocery stores, supermarkets'),
    ('5732', 'Electronics stores'),
    ('5812', 'Eating places, restaurants'),
    ('5814', 'Fast food restaurants'),
    ('5999', 'Miscellaneous retail'),
    ('7011', 'Hotels, motels, resorts');

INSERT INTO merchants (merchant_id, name, mcc, country_code, onboarded_at) VALUES
    (1, 'Northwind Grocers',   '5411', 'US', '2025-06-01 00:00+00'),
    (2, 'Blue Fern Cafe',      '5812', 'GB', '2025-07-15 00:00+00'),
    (3, 'Metro Transit',       '4111', 'US', '2025-08-01 00:00+00'),
    (4, 'Volt Electronics',    '5732', 'DE', '2025-09-10 00:00+00'),
    (5, 'Harbor Hotel',        '7011', 'SG', '2025-10-01 00:00+00'),
    (6, 'Paper Lantern Books', '5999', 'IN', '2026-01-20 00:00+00'),
    (7, 'Quick Bite',          '5812', 'US', '2026-02-01 00:00+00'),
    (8, 'Sunrise Grocers',     '5411', 'FR', '2026-05-15 00:00+00');

-- inserted in id order, so every referred_by points at a row that already exists
INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at) VALUES
    (1,  'asha.rao@example.com',      'Asha Rao',      'IN', NULL, '2025-11-02 09:15+00'),
    (2,  'ben.carter@example.com',    'Ben Carter',    'US', NULL, '2025-11-05 14:40+00'),
    (3,  'chloe.martin@example.com',  'Chloe Martin',  'FR', 1,    '2025-12-01 10:00+00'),
    (4,  'daniel.kim@example.com',    'Daniel Kim',    'US', 2,    '2025-12-03 18:20+00'),
    (5,  'elena.petrova@example.com', 'Elena Petrova', 'DE', 1,    '2025-12-10 08:05+00'),
    (6,  'farid.haddad@example.com',  'Farid Haddad',  'GB', 3,    '2026-01-04 12:30+00'),
    (7,  'grace.lee@example.com',     'Grace Lee',     'SG', NULL, '2026-01-08 03:45+00'),
    (8,  'hugo.silva@example.com',    'Hugo Silva',    'US', 4,    '2026-01-15 16:10+00'),
    (9,  'ivy.chen@example.com',      'Ivy Chen',      'US', NULL, '2026-01-20 11:00+00'),
    (10, 'jonas.weber@example.com',   'Jonas Weber',   'DE', 5,    '2026-02-02 07:50+00'),
    (11, 'kofi.mensah@example.com',   'Kofi Mensah',   'GB', NULL, '2026-02-14 19:25+00'),
    (12, 'lena.novak@example.com',    'Lena Novak',    'DE', 7,    '2026-03-01 09:00+00'),
    (13, 'mateo.ruiz@example.com',    'Mateo Ruiz',    'US', 8,    '2026-03-18 13:35+00');

INSERT INTO accounts (account_id, kind, customer_id, merchant_id, status, opened_at) VALUES
    (101, 'customer', 1,    NULL, 'active', '2025-11-02 09:20+00'),
    (102, 'customer', 2,    NULL, 'active', '2025-11-05 14:45+00'),
    (202, 'customer', 2,    NULL, 'active', '2026-01-31 10:00+00'),
    (103, 'customer', 3,    NULL, 'active', '2025-12-01 10:05+00'),
    (104, 'customer', 4,    NULL, 'active', '2025-12-03 18:25+00'),
    (105, 'customer', 5,    NULL, 'active', '2025-12-10 08:10+00'),
    (106, 'customer', 6,    NULL, 'active', '2026-01-04 12:35+00'),
    (107, 'customer', 7,    NULL, 'active', '2026-01-08 03:50+00'),
    (108, 'customer', 8,    NULL, 'frozen', '2026-01-15 16:15+00'),
    (109, 'customer', 9,    NULL, 'active', '2026-01-20 11:05+00'),
    (209, 'customer', 9,    NULL, 'active', '2026-01-20 11:06+00'),
    (110, 'customer', 10,   NULL, 'active', '2026-02-02 07:55+00'),
    (112, 'customer', 12,   NULL, 'active', '2026-03-01 09:05+00'),
    (113, 'customer', 13,   NULL, 'active', '2026-03-18 13:40+00'),
    (301, 'merchant', NULL, 1,    'active', '2025-06-01 00:00+00'),
    (302, 'merchant', NULL, 2,    'active', '2025-07-15 00:00+00'),
    (303, 'merchant', NULL, 3,    'active', '2025-08-01 00:00+00'),
    (304, 'merchant', NULL, 4,    'active', '2025-09-10 00:00+00'),
    (305, 'merchant', NULL, 5,    'active', '2025-10-01 00:00+00'),
    (306, 'merchant', NULL, 6,    'active', '2026-01-20 00:00+00'),
    (307, 'merchant', NULL, 7,    'active', '2026-02-01 00:00+00'),
    (308, 'merchant', NULL, 8,    'active', '2026-05-15 00:00+00'),
    (900, 'internal', NULL, NULL, 'active', '2025-06-01 00:00+00');

INSERT INTO cards (card_id, account_id, brand, pan_last4, expires_on, status, is_primary) VALUES
    (1,  101, 'visa',       '4242', '2028-09-30', 'active',  true),
    (2,  102, 'mastercard', '5454', '2027-12-31', 'active',  true),
    (3,  202, 'visa',       '1881', '2029-03-31', 'active',  true),
    (4,  103, 'amex',       '0005', '2028-06-30', 'active',  true),
    (5,  104, 'visa',       '3333', '2027-05-31', 'active',  true),
    (6,  104, 'mastercard', '7777', '2026-02-28', 'expired', false),
    (7,  105, 'visa',       '8888', '2029-01-31', 'active',  true),
    (8,  106, 'mastercard', '9999', '2028-11-30', 'active',  true),
    (9,  107, 'visa',       '1234', '2028-04-30', 'active',  true),
    (10, 108, 'amex',       '4321', '2027-08-31', 'blocked', false),
    (11, 109, 'visa',       '2468', '2029-07-31', 'active',  true),
    (12, 110, 'mastercard', '1357', '2028-02-29', 'active',  true),
    (13, 113, 'visa',       '5150', '2029-12-31', 'active',  true),
    (14, 209, 'mastercard', '3690', '2029-09-30', 'active',  true);

-- payment_uid is a UUIDv7 built from created_at (milliseconds) and payment_id, so it is the
-- same on every load and uuid_extract_timestamp(payment_uid) gives back created_at.
INSERT INTO payments (payment_id, payment_uid, card_id, merchant_id, amount_minor, status, created_at, metadata)
SELECT id,
       (lpad(to_hex((extract(epoch FROM ts) * 1000)::bigint), 12, '0')
            || '7' || lpad(to_hex(id), 3, '0') || '8' || lpad(to_hex(id), 15, '0'))::uuid,
       card, merchant, amount, status, ts,
       jsonb_build_object('channel', channel, 'risk', jsonb_build_object('score', score, 'rules', rules::jsonb))
FROM (VALUES
    (1,  1,  1, 4250,   'succeeded', timestamptz '2026-01-03 10:12:00+00',   'web',     12, '[]'),
    (2,  2,  2, 1890,   'succeeded', timestamptz '2026-01-05 08:30:00+00',   'ios',      8, '[]'),
    (3,  6,  4, 129900, 'succeeded', timestamptz '2026-01-09 17:45:00+00',   'web',     91, '["velocity"]'),
    (4,  4,  3, 275,    'succeeded', timestamptz '2026-01-12 07:55:00+00',   'pos',      3, '[]'),
    (5,  7,  5, 48000,  'succeeded', timestamptz '2026-01-20 22:10:00+00',   'web',     35, '[]'),
    (6,  8,  2, 2150,   'failed',    timestamptz '2026-01-22 12:05:00+00',   'android', 22, '[]'),
    (7,  1,  1, 6120,   'succeeded', timestamptz '2026-02-02 18:40:00+00',   'pos',      5, '[]'),
    (8,  3,  4, 54999,  'succeeded', timestamptz '2026-02-07 15:20:00+00',   'web',     67, '["geo_mismatch"]'),
    (9,  9,  3, 275,    'succeeded', timestamptz '2026-02-10 08:01:00+00',   'pos',      2, '[]'),
    (10, 10, 2, 3400,   'failed',    timestamptz '2026-02-11 13:15:00+00',   'ios',     48, '[]'),
    (11, 12, 1, 2500,   'succeeded', timestamptz '2026-02-14 11:11:00+00',   'android', 10, '[]'),
    (12, 5,  7, 1450,   'succeeded', timestamptz '2026-02-20 12:45:00+00',   'ios',      7, '[]'),
    (13, 2,  5, 64000,  'succeeded', timestamptz '2026-03-01 00:00:00+00',   'web',     41, '[]'),
    (14, 1,  1, 5310,   'succeeded', timestamptz '2026-03-04 09:30:00+00',   'pos',      6, '[]'),
    (15, 7,  4, 89900,  'failed',    timestamptz '2026-03-06 20:00:00+00',   'web',     88, '["velocity"]'),
    (16, 12, 5, 31500,  'succeeded', timestamptz '2026-03-08 19:20:00+00',   'web',     30, '[]'),
    (17, 8,  4, 18999,  'succeeded', timestamptz '2026-03-12 16:40:00+00',   'android', 25, '[]'),
    (18, 8,  4, 18999,  'succeeded', timestamptz '2026-03-12 16:42:10+00',   'android', 79, '["velocity"]'),
    (19, 4,  4, 18999,  'succeeded', timestamptz '2026-03-15 21:00:00+00',   'ios',     18, '[]'),
    (20, 3,  1, 7425,   'pending',   timestamptz '2026-03-20 10:10:00+00',   'web',     14, '[]'),
    (21, 13, 7, 1325,   'succeeded', timestamptz '2026-03-25 12:30:00+00',   'ios',      9, '[]'),
    (22, 12, 5, 52000,  'succeeded', timestamptz '2026-03-31 23:59:59.5+00', 'web',     44, '[]'),
    (23, 1,  5, 99000,  'succeeded', timestamptz '2026-04-01 00:00:00+00',   'web',     52, '[]'),
    (24, 2,  1, 3880,   'succeeded', timestamptz '2026-04-03 09:45:00+00',   'pos',      4, '[]'),
    (25, 5,  2, 2275,   'succeeded', timestamptz '2026-04-08 13:05:00+00',   'ios',      6, '[]'),
    (26, 9,  3, 275,    'succeeded', timestamptz '2026-04-14 08:03:00+00',   'pos',      2, '[]'),
    (27, 12, 7, 1980,   'failed',    timestamptz '2026-04-19 12:15:00+00',   'android', 57, '[]'),
    (28, 7,  4, 23450,  'succeeded', timestamptz '2026-04-27 17:30:00+00',   'web',     33, '[]'),
    (29, 3,  1, 4999,   'succeeded', timestamptz '2026-05-02 10:00:00+00',   'web',     11, '[]'),
    (30, 4,  2, 1640,   'succeeded', timestamptz '2026-05-09 08:20:00+00',   'ios',      5, '[]'),
    (31, 13, 4, 75000,  'succeeded', timestamptz '2026-05-16 15:55:00+00',   'web',     72, '["geo_mismatch"]'),
    (32, 9,  3, 550,    'succeeded', timestamptz '2026-05-21 07:45:00+00',   'pos',      3, '[]'),
    (33, 8,  7, 1720,   'succeeded', timestamptz '2026-05-28 12:40:00+00',   'android', 15, '[]'),
    (34, 1,  1, 5875,   'succeeded', timestamptz '2026-06-04 18:05:00+00',   'pos',      7, '[]'),
    (35, 2,  5, 41000,  'succeeded', timestamptz '2026-06-12 21:30:00+00',   'web',     38, '[]'),
    (36, 9,  2, 2090,   'failed',    timestamptz '2026-06-19 09:10:00+00',   'ios',     61, '[]'),
    (37, 5,  3, 275,    'pending',   timestamptz '2026-06-30 23:59:00+00',   'pos',      4, '[]')
) AS v (id, card, merchant, amount, status, ts, channel, score, rules);

INSERT INTO refunds (refund_id, payment_id, amount_minor, reason, created_at) VALUES
    (1, 3,  129900, 'fraud',            '2026-01-12 09:00+00'),
    (2, 18, 18999,  'duplicate',        '2026-03-13 10:00+00'),
    (3, 5,  12000,  'customer_request', '2026-01-25 14:00+00'),
    (4, 5,  6000,   'customer_request', '2026-02-03 11:30+00'),
    (5, 31, 25000,  'customer_request', '2026-05-20 16:00+00'),
    (6, 24, 3880,   'customer_request', '2026-04-05 10:00+00');

-- Ledger. Deposits move money from internal clearing (900) into a customer account.
CREATE TEMP TABLE seed_deposits (journal_id bigint, account_id bigint, amount bigint, ts timestamptz);
INSERT INTO seed_deposits VALUES
    (1,  101, 100000, '2026-01-02 09:00+00'),
    (2,  102, 80000,  '2026-01-02 09:00+00'),
    (3,  103, 30000,  '2026-01-02 09:00+00'),
    (4,  104, 140000, '2026-01-02 09:00+00'),
    (5,  106, 50000,  '2026-01-10 09:00+00'),
    (6,  107, 5000,   '2026-01-10 09:00+00'),
    (7,  105, 60000,  '2026-01-15 09:00+00'),
    (8,  108, 20000,  '2026-01-20 09:00+00'),
    (9,  109, 5000,   '2026-01-21 09:00+00'),
    (10, 209, 5000,   '2026-01-21 09:00+00'),
    (11, 202, 75000,  '2026-02-01 09:00+00'),
    (12, 110, 90000,  '2026-02-03 09:00+00'),
    (13, 113, 80000,  '2026-03-18 14:00+00'),
    (14, 101, 50000,  '2026-03-30 09:00+00'),
    (15, 105, 20000,  '2026-04-15 09:00+00'),
    (16, 102, 50000,  '2026-06-01 09:00+00');

-- One row per leg, numbered in time order so entry_id is the same on every load.
INSERT INTO ledger_entries (entry_id, journal_id, account_id, payment_id, refund_id, entry_type, amount_minor, created_at)
SELECT row_number() OVER (ORDER BY ts, journal_id, leg), journal_id, account_id, payment_id, refund_id, entry_type, amount, ts
FROM (
    SELECT d.journal_id, 1 AS leg, d.account_id, NULL::bigint AS payment_id, NULL::bigint AS refund_id,
           'deposit' AS entry_type, d.amount, d.ts
    FROM seed_deposits d
    UNION ALL
    SELECT d.journal_id, 2, 900, NULL, NULL, 'deposit', -d.amount, d.ts
    FROM seed_deposits d
    UNION ALL   -- a succeeded payment debits the card's account and credits the merchant's
    SELECT 1000 + p.payment_id, 1, c.account_id, p.payment_id, NULL, 'payment', -p.amount_minor, p.created_at
    FROM payments p JOIN cards c ON c.card_id = p.card_id
    WHERE p.status = 'succeeded'
    UNION ALL
    SELECT 1000 + p.payment_id, 2, 300 + p.merchant_id, p.payment_id, NULL, 'payment', p.amount_minor, p.created_at
    FROM payments p
    WHERE p.status = 'succeeded'
    UNION ALL   -- a refund does the reverse
    SELECT 2000 + r.refund_id, 1, 300 + p.merchant_id, p.payment_id, r.refund_id, 'refund', -r.amount_minor, r.created_at
    FROM refunds r JOIN payments p ON p.payment_id = r.payment_id
    UNION ALL
    SELECT 2000 + r.refund_id, 2, c.account_id, p.payment_id, r.refund_id, 'refund', r.amount_minor, r.created_at
    FROM refunds r JOIN payments p ON p.payment_id = r.payment_id JOIN cards c ON c.card_id = p.card_id
) AS legs (journal_id, leg, account_id, payment_id, refund_id, entry_type, amount, ts);

DROP TABLE seed_deposits;

-- the cached balance starts out equal to the ledger
UPDATE accounts a
SET balance_minor = s.total
FROM (SELECT account_id, sum(amount_minor) AS total FROM ledger_entries GROUP BY account_id) AS s
WHERE a.account_id = s.account_id;

INSERT INTO merchant_fee_schedules (merchant_id, valid_during, fee_bps) VALUES
    (1, '[2025-06-01 00:00+00, 2026-07-01 00:00+00)', 290),
    (1, '[2026-07-01 00:00+00,)',                     250),
    (2, '[2025-07-15 00:00+00,)',                     300),
    (3, '[2025-08-01 00:00+00,)',                     150),
    (4, '[2025-09-10 00:00+00, 2026-03-01 00:00+00)', 320),
    (4, '[2026-03-01 00:00+00,)',                     280),
    (5, '[2025-10-01 00:00+00,)',                     275),
    (7, '[2026-02-01 00:00+00,)',                     310);

-- Logins. Customer 5 gets six failures in two minutes from 203.0.113.7, then her own success.
-- Customer 10 mistypes his password twice in April and twice again in June (events 25 to 27).
INSERT INTO login_events (event_id, customer_id, occurred_at, success, ip) VALUES
    (1,  1, '2026-01-03 10:05:00+00', true,  '198.51.100.21'),
    (2,  2, '2026-01-05 08:25:00+00', true,  '198.51.100.40'),
    (3,  4, '2026-01-09 17:40:00+00', true,  '198.51.100.77'),
    (4,  5, '2026-01-20 22:00:00+00', true,  '192.0.2.15'),
    (5,  6, '2026-01-22 11:58:00+00', false, '198.51.100.90'),
    (6,  6, '2026-01-22 11:59:00+00', true,  '198.51.100.90'),
    (7,  9, '2026-01-21 08:55:00+00', true,  '192.0.2.60'),
    (8,  1, '2026-02-02 18:35:00+00', true,  '198.51.100.21'),
    (9,  2, '2026-03-01 00:00:00+00', true,  '198.51.100.40'),
    (10, 5, '2026-03-06 19:40:00+00', true,  '192.0.2.15'),
    (11, 5, '2026-03-06 19:52:00+00', false, '203.0.113.7'),
    (12, 5, '2026-03-06 19:52:20+00', false, '203.0.113.7'),
    (13, 5, '2026-03-06 19:52:40+00', false, '203.0.113.7'),
    (14, 5, '2026-03-06 19:53:00+00', false, '203.0.113.7'),
    (15, 5, '2026-03-06 19:53:20+00', false, '203.0.113.7'),
    (16, 5, '2026-03-06 19:53:40+00', false, '203.0.113.7'),
    (17, 5, '2026-03-06 19:58:00+00', true,  '192.0.2.15'),
    (18, 6, '2026-03-12 16:35:00+00', true,  '198.51.100.90'),
    (19, 12, '2026-03-01 09:10:00+00', true, '192.0.2.88'),
    (20, 10, '2026-04-19 12:10:00+00', false, '198.51.100.12'),
    (21, 10, '2026-04-19 12:11:00+00', false, '198.51.100.12'),
    (22, 10, '2026-04-19 12:12:00+00', true,  '198.51.100.12'),
    (23, 13, '2026-05-16 15:50:00+00', true,  '192.0.2.33'),
    (24, 1, '2026-06-04 18:00:00+00', true,  '198.51.100.21'),
    (25, 10, '2026-06-08 07:30:00+00', false, '198.51.100.12'),
    (26, 10, '2026-06-08 07:30:40+00', false, '198.51.100.12'),
    (27, 10, '2026-06-08 07:31:30+00', true,  '198.51.100.12');

INSERT INTO jobs (job_id, kind, payload, status, run_after, attempts, locked_by, locked_at) VALUES
    (1, 'fraud_review',    '{"payment_id": 18}',                       'done',   '2026-03-12 16:43+00', 1, NULL, NULL),
    (2, 'fraud_review',    '{"payment_id": 31}',                       'queued', '2026-05-16 16:00+00', 0, NULL, NULL),
    (3, 'send_receipt',    '{"payment_id": 34}',                       'queued', '2026-06-04 18:06+00', 0, NULL, NULL),
    (4, 'send_receipt',    '{"payment_id": 35}',                       'done',   '2026-06-12 21:31+00', 1, NULL, NULL),
    (5, 'settle_merchant', '{"merchant_id": 1, "day": "2026-06-12"}',  'queued', '2026-06-13 02:00+00', 0, NULL, NULL),
    (6, 'settle_merchant', '{"merchant_id": 4, "day": "2026-06-12"}',  'failed', '2026-06-13 02:00+00', 3, NULL, NULL),
    (7, 'settle_merchant', '{"merchant_id": 5, "day": "2026-06-12"}',  'queued', '2026-06-13 02:00+00', 0, NULL, NULL),
    (8, 'send_receipt',    '{"payment_id": 37}',                       'queued', '2026-06-30 23:59+00', 0, NULL, NULL);

-- The partner's flat export of the March payments. It repeats customer, card and merchant facts
-- on every row, and two rows disagree with the others: payment 18 spells the MCC description
-- differently, and payment 17 spells Farid's surname with one d.
INSERT INTO payments_export (payment_id, customer_email, customer_name, card_brand, card_last4,
                             merchant_name, mcc, mcc_description, amount_minor, created_at)
SELECT p.payment_id, cu.email,
       CASE WHEN p.payment_id = 17 THEN 'Farid Hadad' ELSE cu.full_name END,
       c.brand, c.pan_last4, m.name, m.mcc,
       CASE WHEN p.payment_id = 18 THEN 'Electronic stores' ELSE mc.description END,
       p.amount_minor, p.created_at
FROM payments p
JOIN cards c      ON c.card_id = p.card_id
JOIN accounts a   ON a.account_id = c.account_id
JOIN customers cu ON cu.customer_id = a.customer_id
JOIN merchants m  ON m.merchant_id = p.merchant_id
JOIN mcc_codes mc ON mc.mcc = m.mcc
WHERE p.created_at >= '2026-03-01 00:00+00' AND p.created_at < '2026-04-01 00:00+00'
ORDER BY p.payment_id;

-- identity sequences and the journal sequence carry on after the explicit ids
SELECT setval(pg_get_serial_sequence('merchants', 'merchant_id'), (SELECT max(merchant_id) FROM merchants));
SELECT setval(pg_get_serial_sequence('customers', 'customer_id'), (SELECT max(customer_id) FROM customers));
SELECT setval(pg_get_serial_sequence('accounts', 'account_id'), (SELECT max(account_id) FROM accounts));
SELECT setval(pg_get_serial_sequence('cards', 'card_id'), (SELECT max(card_id) FROM cards));
SELECT setval(pg_get_serial_sequence('payments', 'payment_id'), (SELECT max(payment_id) FROM payments));
SELECT setval(pg_get_serial_sequence('refunds', 'refund_id'), (SELECT max(refund_id) FROM refunds));
SELECT setval(pg_get_serial_sequence('ledger_entries', 'entry_id'), (SELECT max(entry_id) FROM ledger_entries));
SELECT setval(pg_get_serial_sequence('login_events', 'event_id'), (SELECT max(event_id) FROM login_events));
SELECT setval(pg_get_serial_sequence('jobs', 'job_id'), (SELECT max(job_id) FROM jobs));
SELECT setval('journal_id_seq', 3000);   -- new journals start at 3001

ANALYZE;
