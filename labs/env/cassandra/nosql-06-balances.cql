-- Lessons nosql-05 and nosql-06: one small table, three copies of every row.
-- Load it on the three-node cluster with: cqlsh -f /sfz/nosql-06-balances.cql   (safe to run again)

-- NetworkTopologyStrategy: 3 copies in datacenter dc1. With three nodes, every node holds every row.
CREATE KEYSPACE IF NOT EXISTS payments
  WITH replication = {'class': 'NetworkTopologyStrategy', 'dc1': 3};

CREATE TABLE IF NOT EXISTS payments.balances (
    account_id    text PRIMARY KEY,
    balance_minor bigint
);

-- write the starting balances to all three copies
CONSISTENCY ALL;
INSERT INTO payments.balances (account_id, balance_minor) VALUES ('A-1001', 10000);
INSERT INTO payments.balances (account_id, balance_minor) VALUES ('A-2002', 5000);
INSERT INTO payments.balances (account_id, balance_minor) VALUES ('M-0042', 0);
