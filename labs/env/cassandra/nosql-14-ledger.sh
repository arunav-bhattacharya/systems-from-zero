#!/usr/bin/env bash
# Lesson shard-06: give the three-node cluster enough data that streaming, cleanup, repair and
# snapshots have something to move. Run it inside a node, from the labs folder:
#   docker compose -f env/cassandra-cluster.yml exec cass1 bash /sfz/nosql-14-ledger.sh
# It creates payments.ledger (three copies in dc1) and writes 50,000 ledger entries for 5,000
# accounts with cqlsh COPY, at about 2,000 rows a second so three small nodes keep up (about
# 30 seconds). Safe to run again: the same rows are written again.
set -euo pipefail

cqlsh -e "
CREATE KEYSPACE IF NOT EXISTS payments
  WITH replication = {'class': 'NetworkTopologyStrategy', 'dc1': 3};
CREATE TABLE IF NOT EXISTS payments.ledger (
    account_id   text,
    entry_id     int,
    amount_minor bigint,
    memo         text,
    PRIMARY KEY ((account_id), entry_id)
);"

# 50,000 rows: accounts A-00000 .. A-04999, ten entries each, a settlement memo on every row
awk 'BEGIN { for (i = 0; i < 50000; i++)
               printf "A-%05d,%d,%d,settlement batch %d for merchant M-0042\n", i % 5000, i, (i * 37) % 100000, i / 1000 }' \
  > /tmp/ledger.csv

cqlsh -e "COPY payments.ledger (account_id, entry_id, amount_minor, memo) FROM '/tmp/ledger.csv'
          WITH NUMPROCESSES = 1 AND INGESTRATE = 2000 AND CHUNKSIZE = 200"
rm -f /tmp/ledger.csv
# The rows sit in each node's memtable now. `nodetool flush payments` on each node writes them
# to SSTables, and only then does `nodetool status` count them as Load.
