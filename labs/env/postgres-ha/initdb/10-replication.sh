#!/bin/bash
# Runs once, as the postgres user, when the primary's data directory is new.
set -e
psql -v ON_ERROR_STOP=1 -U sfz -d sfz <<'SQL'
-- the role a standby logs in as: it may stream WAL and take base backups, nothing else
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator';
-- a physical slot: the primary keeps every WAL record from here on until standby1 has it
SELECT slot_name, lsn FROM pg_create_physical_replication_slot('standby1', true);
SQL

# "all" in the database column never matches a replication connection; only "replication" does.
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
