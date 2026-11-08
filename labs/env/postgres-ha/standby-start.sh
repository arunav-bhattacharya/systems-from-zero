#!/bin/bash
# The standby (env/postgres-ha.yml). Runs as root. On the first start its data directory is empty,
# so it clones the primary with pg_basebackup:
#   -X stream   copy the WAL written during the backup too, over a second connection
#   -S standby1 through the replication slot the primary created, so no WAL it needs is removed
#   -R          write standby.signal and primary_conninfo, so the clone starts as a standby
# Every later start finds the data directory and just runs PostgreSQL in standby mode.
set -e
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "standby: cloning the primary with pg_basebackup"
    mkdir -p "$PGDATA"
    chown postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    for attempt in $(seq 1 30); do
        gosu postgres pg_basebackup -h primary -U replicator -D "$PGDATA" -X stream -S standby1 -R -c fast && break
        echo "standby: primary not ready (attempt $attempt), retrying in 2 s"
        rm -rf "${PGDATA:?}"/*
        sleep 2
    done
    [ -s "$PGDATA/PG_VERSION" ] || { echo "standby: pg_basebackup kept failing" >&2; exit 1; }
fi

# cluster_name names this server in pg_stat_replication (application_name) and synchronous_standby_names.
# max_standby_streaming_delay is 30s by default; 5s makes the replay conflict quick to see.
exec gosu postgres postgres \
    -c shared_buffers=64MB \
    -c cluster_name=standby1 \
    -c max_standby_streaming_delay=5s
