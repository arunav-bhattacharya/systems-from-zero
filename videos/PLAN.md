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

## Progress log

- Round 1 shipped so far (2026-11-15): repl-02, repl-08, msg-07, cons-05, cons-01, dist-02; store-01, store-03,
  store-07, os-09, txn-02, txn-03; net-08, cache-05, shard-01, shard-04, batch-05, batch-06 (74 videos live).
  Still running: streams/derived/encoding maker (stream-03, stream-05, derive-01, derive-05, enc-03, dist-04).
- Round 2 started (usage 11%): maker E net-10 tls-handshake, net-11 http-versions, net-03 nat, net-12 lb-retries,
  os-02 fork-exec, os-11 epoll; maker F os-07 cow-oom, os-12 namespaces-cgroups, cache-01 hit-ratio,
  model-02 access-patterns, model-05 wide-column, model-06 embed-vs-reference; maker G sql-02 normalization,
  sql-04 group-by-rollup, sql-07 gaps-islands, sql-08 keyset-pagination, sql-09 upsert-race, store-08 hnsw.
  Maker H (start when the round 1 maker finishes): store-09 volcano-vs-vector, store-10 join-order,
  store-11 column-compression, store-12 view-maintenance, batch-08 skew-aqe, batch-12 iceberg-deletes.
- Round 1 complete (2026-11-15): stream-03, stream-05, derive-01, derive-05, enc-03, dist-04 shipped; 80 videos live. Maker H started.
- Maker H shipped (store-09, store-10, store-11, store-12, batch-08, batch-12); 86 videos live.
- Round 3 maker I started (usage 17%): msg-03 segments-compaction, msg-05 keys-partitions, msg-06 idempotent-producer, msg-09 retry-topics, msg-12 redis-streams, cache-04 hyperloglog.
- Round 3 still to assign: cache-08 token bucket, cache-09 RDB fork and AOF, cache-10 Redis Cluster slots, shard-08 DynamoDB partitions, shard-09 query then fetch, txn-06 WATCH and MULTI, txn-08 DynamoDB transactions, repl-06 CRDT text, found-05 storage and compute, os-03 threads, os-04 scheduling, os-05 futexes, os-10 inodes, net-02 ARP, net-04 routing, sql-01 NULL logic, sql-05 correlated subqueries, batch-13 idempotent backfills.
- Maker E shipped (net-10, net-11, net-03, net-12, os-02, os-11); 92 videos live. Maker J started: cache-08 token-bucket, cache-09 rdb-aof, cache-10 cluster-slots, shard-08 dynamodb-partitions, shard-09 query-then-fetch, txn-06 watch-multi.
- Maker F shipped (os-07, os-12, cache-01, model-02, model-05, model-06); 98 videos live. Maker K started: txn-08 dynamodb-transactions, repl-06 crdt-text, found-05 storage-compute, os-03 threads, os-04 scheduling, os-05 futex-deadlock. Left for maker L: os-10, net-02, net-04, sql-01, sql-05, batch-13.
- Maker G shipped (sql-02, sql-04, sql-07, sql-08, sql-09, store-08); round 2 complete; 104 videos live. Maker L started: os-10 inodes, net-02 arp, net-04 routing, sql-01 null-logic, sql-05 correlated-subquery, batch-13 backfills.
- Maker J shipped (cache-08, cache-09, cache-10, shard-08, shard-09, txn-06); 110 videos live. Posters set by hand: token-bucket POSTER=64, rdb-aof POSTER=49.
- Maker I shipped (msg-03, msg-05, msg-06, msg-09, msg-12, cache-04); 116 videos live. Posters: segments-compaction 108, retry-topics 101.5, redis-streams 74.8, hyperloglog 117.
- Maker L shipped (os-10, net-02, net-04, sql-01, sql-05, batch-13); 122 videos live. Only maker K (txn-08, repl-06, found-05, os-03, os-04, os-05) left in round 3.
