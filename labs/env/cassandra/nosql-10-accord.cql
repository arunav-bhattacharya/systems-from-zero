-- Lesson txn-08: two Accord tables for a transfer across partitions (Cassandra 6.0-alpha2 only).
-- ALPHA: the BEGIN TRANSACTION syntax may change before 6.0 is released. Safe to run again.
-- Load it with: cqlsh -f /sfz/nosql-10-accord.cql
CREATE KEYSPACE IF NOT EXISTS payments
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- transactional_mode = 'full' hands every read and write of the table to Accord
CREATE TABLE IF NOT EXISTS payments.balances (
    account_id    text PRIMARY KEY,
    balance_minor bigint
) WITH transactional_mode = 'full';

CREATE TABLE IF NOT EXISTS payments.ledger (
    account_id   text,
    transfer_id  text,
    amount_minor bigint,
    PRIMARY KEY ((account_id), transfer_id)
) WITH transactional_mode = 'full';

INSERT INTO payments.balances (account_id, balance_minor) VALUES ('A-1001', 10000);
INSERT INTO payments.balances (account_id, balance_minor) VALUES ('A-2002', 5000);
