-- Lesson nosql-02: the payments access patterns as Cassandra tables, one table per query.
-- Load it with: cqlsh -f /sfz/nosql-02-payments.cql   (safe to run again)

CREATE KEYSPACE IF NOT EXISTS payments
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};  -- one node, one copy
USE payments;

-- AP1: an account's payments, newest first.
-- Partition key: account_id. Clustering columns: created_at (newest first), then payment_id.
CREATE TABLE IF NOT EXISTS payments_by_account (
    account_id   text,
    created_at   timestamp,
    payment_id   text,
    merchant_id  text,
    status       text,
    amount_minor bigint,
    currency     text,
    PRIMARY KEY ((account_id), created_at, payment_id)
) WITH CLUSTERING ORDER BY (created_at DESC, payment_id ASC);

-- AP3: a merchant's payments with one status in a time window.
-- One partition per merchant per day, so a busy merchant never grows one endless partition.
CREATE TABLE IF NOT EXISTS payments_by_merchant_day (
    merchant_id  text,
    day          date,
    status       text,
    created_at   timestamp,
    payment_id   text,
    account_id   text,
    amount_minor bigint,
    PRIMARY KEY ((merchant_id, day), status, created_at, payment_id)
);

-- The same six payments, written once per table. Duplication is the price of one-read queries.
INSERT INTO payments_by_account (account_id, created_at, payment_id, merchant_id, status, amount_minor, currency) VALUES ('A-1001', '2026-11-07 08:15:03+0000', 'pay-81701', 'M-0042', 'SETTLED', 18000, 'EUR');
INSERT INTO payments_by_account (account_id, created_at, payment_id, merchant_id, status, amount_minor, currency) VALUES ('A-1001', '2026-11-07 09:40:27+0000', 'pay-81720', 'M-0042', 'FAILED', 7300, 'EUR');
INSERT INTO payments_by_account (account_id, created_at, payment_id, merchant_id, status, amount_minor, currency) VALUES ('A-1001', '2026-11-07 10:30:12+0000', 'pay-81730', 'M-0043', 'SETTLED', 4250, 'EUR');
INSERT INTO payments_by_account (account_id, created_at, payment_id, merchant_id, status, amount_minor, currency) VALUES ('A-1001', '2026-11-06 23:59:58+0000', 'pay-81655', 'M-0042', 'SETTLED', 999, 'EUR');
INSERT INTO payments_by_account (account_id, created_at, payment_id, merchant_id, status, amount_minor, currency) VALUES ('A-2002', '2026-11-07 09:55:00+0000', 'pay-81724', 'M-0042', 'FAILED', 1200, 'EUR');
INSERT INTO payments_by_account (account_id, created_at, payment_id, merchant_id, status, amount_minor, currency) VALUES ('A-2002', '2026-11-07 11:05:41+0000', 'pay-81741', 'M-0042', 'SETTLED', 6400, 'EUR');

INSERT INTO payments_by_merchant_day (merchant_id, day, status, created_at, payment_id, account_id, amount_minor) VALUES ('M-0042', '2026-11-07', 'SETTLED', '2026-11-07 08:15:03+0000', 'pay-81701', 'A-1001', 18000);
INSERT INTO payments_by_merchant_day (merchant_id, day, status, created_at, payment_id, account_id, amount_minor) VALUES ('M-0042', '2026-11-07', 'FAILED', '2026-11-07 09:40:27+0000', 'pay-81720', 'A-1001', 7300);
INSERT INTO payments_by_merchant_day (merchant_id, day, status, created_at, payment_id, account_id, amount_minor) VALUES ('M-0043', '2026-11-07', 'SETTLED', '2026-11-07 10:30:12+0000', 'pay-81730', 'A-1001', 4250);
INSERT INTO payments_by_merchant_day (merchant_id, day, status, created_at, payment_id, account_id, amount_minor) VALUES ('M-0042', '2026-11-06', 'SETTLED', '2026-11-06 23:59:58+0000', 'pay-81655', 'A-1001', 999);
INSERT INTO payments_by_merchant_day (merchant_id, day, status, created_at, payment_id, account_id, amount_minor) VALUES ('M-0042', '2026-11-07', 'FAILED', '2026-11-07 09:55:00+0000', 'pay-81724', 'A-2002', 1200);
INSERT INTO payments_by_merchant_day (merchant_id, day, status, created_at, payment_id, account_id, amount_minor) VALUES ('M-0042', '2026-11-07', 'SETTLED', '2026-11-07 11:05:41+0000', 'pay-81741', 'A-2002', 6400);
