#!/bin/bash
# Point-in-time recovery (env/postgres-ha.yml, --profile pitr). Runs as root.
# Needs a base backup in /archive/base (lesson sql-16 takes one with pg_basebackup on the primary)
# and the WAL segments the primary archived next to it in /archive. On the first start it:
#   1. copies the base backup into an empty data directory,
#   2. tells PostgreSQL where the archived WAL is (restore_command) and where to stop (recovery_target_time),
#   3. creates recovery.signal, so the server starts in targeted recovery instead of as a primary.
# PostgreSQL then replays the archived WAL up to TARGET_TIME, stops, and promotes itself.
set -e
if [ -z "$TARGET_TIME" ]; then
    echo "restore: set TARGET_TIME, for example TARGET_TIME='2026-11-08 02:30:00+00'" >&2
    exit 1
fi
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    if [ ! -s /archive/base/PG_VERSION ]; then
        echo "restore: no base backup in /archive/base; take one on the primary first" >&2
        exit 1
    fi
    echo "restore: copying the base backup, recovering to $TARGET_TIME"
    mkdir -p "$PGDATA"
    cp -a /archive/base/. "$PGDATA"/
    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    cat >> "$PGDATA/postgresql.auto.conf" <<CONF
restore_command = 'cp /archive/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
CONF
    gosu postgres touch "$PGDATA/recovery.signal"
fi

exec gosu postgres postgres -c shared_buffers=64MB
