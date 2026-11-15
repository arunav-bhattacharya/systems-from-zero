# Video plan for lessons without a video (started 2026-11-15)

The user asked for videos on every lesson still missing one, most important first, built to give intuition.
Their rule: check weekly usage before each round; at 60% ship what is finished and park the rest.
Makers follow `videos/MAKER_BRIEF.md`; four makers run at once, six videos each, and never edit
`content/videos.json`. The coordinator registers each maker's videos and ships after its report.

## Shipping one maker's batch

1. Add each video to `content/videos.json` (slug, scene, lesson, section, title); check the mp4, jpg and vtt
   exist, the section index is in range and not already used by another video.
2. `/usr/local/bin/python3 site/validate.py --all`, then `/usr/local/bin/python3 site/build.py` (that interpreter has markdown and pygments; Homebrew's python3 does not).
3. `git add videos/scenes videos/captions web/video content/videos.json web/index.html web/lessons`, commit, and
   push with `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin main`.
4. `npx wrangler deploy`. New video URLs can 404 for a few seconds; then check each with a range request (206).

## Round 1 (in progress): the 24 most important

- Storage and transactions: store-01 log-store, store-03 buffer-pool, store-07 index-scan, os-09 page-cache-fsync,
  txn-02 lost-update, txn-03 phantoms
- Copies and agreement: repl-02 replication-logs, repl-08 version-vectors, msg-07 consumer-offsets,
  cons-05 leader-election, cons-01 consistency-models, dist-02 failure-detection
- Networks, caches, shards, batch: net-08 tcp-congestion, cache-05 cache-eviction, shard-01 range-vs-hash,
  shard-04 secondary-indexes, batch-05 parquet-pushdown, batch-06 spark-stages
- Streams, derived data, encoding: stream-03 event-sourcing, stream-05 ktable-state, derive-01 kappa-reprocessing,
  derive-05 merkle-audit, enc-03 expand-contract, dist-04 process-pause

## Round 2: networking, OS, data models, SQL (24)

net-10 TLS 1.3 handshake, net-11 HTTP/2 vs HTTP/3 head-of-line blocking, net-03 NAT, net-12 load balancers and
retries, os-02 fork and exec, os-07 copy-on-write and the OOM killer, os-11 blocking vs epoll, os-12 namespaces and
cgroups, cache-01 hit ratio and locality, model-02 access patterns first, model-05 wide-column partitions,
model-06 embed vs reference, sql-02 update anomalies and normalization, sql-04 GROUP BY and ROLLUP,
sql-07 gaps and islands, sql-08 OFFSET vs keyset pagination, sql-09 upsert races and ON CONFLICT,
store-08 HNSW vector search, store-09 Volcano vs vectorized execution, store-10 cardinality estimates and join
order, store-11 column compression and zone maps, store-12 incremental view maintenance, batch-08 skew and AQE,
batch-12 Iceberg deletes and compaction

## Round 3: messaging, NoSQL internals and the rest (24)

msg-03 segments, retention and compaction, msg-05 keys, partitions and ordering, msg-06 batching and the
idempotent producer, msg-09 poison pills and retry topics, msg-12 Redis Streams pending entries, cache-04
HyperLogLog, cache-08 token bucket, cache-09 RDB fork and AOF, cache-10 Redis Cluster slots, shard-08 DynamoDB
partitions and throttling, shard-09 query then fetch, txn-06 WATCH and MULTI, txn-08 DynamoDB transactions,
repl-06 CRDT text editing, found-05 storage and compute separation, os-03 threads and context switches,
os-04 scheduling, os-05 futexes and deadlock, os-10 inodes and links, net-02 ARP, net-04 routing and traceroute,
sql-01 NULL and three-valued logic, sql-05 correlated subqueries, batch-13 idempotent backfills

## Lowest priority (only if usage allows)

found-06, model-01, model-03, model-04, model-07, model-09, store-02, store-13, store-14, cache-03, enc-01,
enc-04, dist-07, dist-08, cons-06, msg-11, stream-02, stream-08, batch-01, batch-04, batch-09, batch-10,
batch-14, batch-15, derive-02, derive-06, sql-10, os-08, net-05, net-06
