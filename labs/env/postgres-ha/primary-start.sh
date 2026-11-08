#!/bin/bash
# The primary (env/postgres-ha.yml). Runs as root: make the WAL archive writable for the postgres
# user, then hand over to the image's own entrypoint, which runs initdb and initdb/ on first start.
set -e
mkdir -p /archive
chown postgres:postgres /archive
chmod 700 /archive

exec docker-entrypoint.sh postgres \
    -c shared_buffers=64MB \
    -c archive_mode=on \
    -c archive_command='test ! -f /archive/%f && cp %p /archive/%f' \
    -c log_replication_commands=on
