# Redis for Java/Kotlin backend engineers: research notes for a 9 to 11 lesson track

Research date: 2026-11-07. Versions below were pulled live that day from GitHub release APIs, Maven Central metadata, Docker Hub and redis.io / valkey.io. Anything I could not confirm is listed under Gaps. "(verify)" marks a claim from background knowledge that a writer should check before publishing.

---

## 1. Teaching order and scope: canonical concepts with the facts behind them

### Takeaway
Teach Redis as an in-memory data-structure server with one main command-execution thread. Correctness (atomicity, ordering, TTL semantics) follows from that model, and so do the costs (a single O(N) command stalls everyone). Then go through data types and encodings, expiry and eviction, atomicity tools (MULTI/WATCH, Lua, Functions, pipelining), messaging (pub/sub vs Streams), application patterns (caching, rate limiting, locks, idempotency, leaderboards), durability and HA (RDB/AOF, replication, Sentinel, Cluster), and latency debugging last. Redis 8.x has added primitives that change the "textbook" answers: `DELEX IFEQ` / `SET IFEQ` (8.4) for lock release and CAS, `INCREX` (8.8) for rate limiting, `XADD IDMP` (8.6) for stream idempotency, LRM eviction (8.6), `HOTKEYS` (8.6). Teach the classic technique first, then the new command.

### Cited Findings

**Execution model and threading**
- redis.conf (8.10) says it outright: "Redis is mostly single threaded, however there are certain threaded operations such as UNLINK, slow I/O accesses and other things that are performed on side threads." Socket reads/writes and protocol parsing can be moved to I/O threads; threading is off by default; the advice is to enable it only on machines with 4+ cores and leave one core spare (e.g. 3 I/O threads on 4 cores, 7 on 8). `io-threads 1` = main thread only. — [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- Redis 8.0 shipped "a new I/O threading implementation which enables throughput increase on multi-core environments (set with `io-threads`)". — [Redis 8.0.0 release](https://github.com/redis/redis/releases/tag/8.0.0)
- Redis 8 GA blog: I/O threads have existed since Redis 6 (socket reads/writes and command parsing). Redis 8's new implementation defaults to `io-threads 1`. With 8 threads on a multi-core Intel CPU, Redis measured "up to 112% improvement in throughput", varying by command. Redis 8 also cut replication memory by up to 35% with a new replication mechanism. — [Redis 8 GA blog](https://redis.io/blog/redis-8-ga/)
- Redis 8.4: I/O threading gives ">30% for caching use cases (10% SET, 90% GET), 4 cores"; Query Engine `FT.*` commands also benefit from I/O threading. — [Redis 8.4.0 release](https://github.com/redis/redis/releases/tag/8.4.0)
- The latency guide calls Redis "mostly single threaded", and names `KEYS` in production as a classic source of slow-command latency. — [Diagnosing latency issues](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)
- Lua scripts are atomic: "While executing the script, all server activities are blocked during its entire runtime." `SCRIPT KILL` is the only way to stop a long-running script short of shutdown, and only if the script has not written. — [Scripting with Lua](https://redis.io/docs/latest/develop/programmability/eval-intro/)

**Protocol: RESP2 vs RESP3**
- RESP2 became the standard in Redis 2.0. RESP3 is "mostly a superset of RESP2". Redis 6.0 added opt-in RESP3 via the `HELLO` handshake. From Redis 7 both RESP2 and RESP3 clients can call all core commands. "Future versions of Redis may change the default protocol version", but RESP2 is unlikely to be fully deprecated, and new features may require RESP3. RESP3 adds a Push type for out-of-band data. In RESP2, a connection that subscribes to pub/sub switches into push mode. — [RESP protocol spec](https://redis.io/docs/latest/develop/reference/protocol-spec/)
- Client-side caching: with RESP3, data and invalidation messages share one connection. RESP2 needs a second connection, with `CLIENT TRACKING ... REDIRECT <id>` and a subscription to the `__redis__:invalidate` channel. — [Client-side caching reference](https://redis.io/docs/latest/develop/reference/client-side-caching/)
- Jedis 8.0 now auto-negotiates RESP3 by default (sends `HELLO 3`, falls back to RESP2) for all UnifiedJedis-based clients. — [Jedis v7→v8 migration guide](https://redis.github.io/jedis/migration-guides/v7-to-v8/)

**Core data types and encodings (8.10 defaults)**
- Encoding thresholds in redis.conf 8.10: `hash-max-listpack-entries 512`, `hash-max-listpack-value 64`; `list-max-listpack-size -2`; `set-max-intset-entries 512`, `set-max-listpack-entries 128`, `set-max-listpack-value 64`; `zset-max-listpack-entries 128`, `zset-max-listpack-value 64`; `stream-node-max-bytes 4096`, `stream-node-max-entries 100`. — [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- Sorted-set implementation (source comment): "ZSETs are ordered sets using two data structures to hold the same elements": a hash table mapping members to scores, plus a skip list ordered by score. — [t_zset.c (8.10)](https://github.com/redis/redis/blob/8.10/src/t_zset.c)
- Sorted-set ops are O(log N); range reads are O(log N + M). Members with equal scores are ordered lexicographically. — [Sorted sets docs](https://redis.io/docs/latest/develop/data-types/sorted-sets/)
- The data-types overview lists strings, lists, sets, hashes, sorted sets, streams, geospatial indexes, bitmaps, bitfields, HyperLogLog, JSON, probabilistic types, time series, and vector sets. — [Data types overview](https://redis.io/docs/latest/develop/data-types/)
- Redis 8.6: "Substantial memory reduction for hashes (hashtable-encoded) and sorted sets (skiplist-encoded)". — [Redis 8.6.0 release](https://github.com/redis/redis/releases/tag/8.6.0)
- Redis 8.10: "Compact hashes", a new hash encoding that stores field names once for keys sharing a schema, plus `HIMPORT` for bulk insertion. — [Redis 8.10.0 release](https://github.com/redis/redis/releases/tag/8.10.0)
- Redis 8.12-rc1 (pre-release): compressed (roaring) bitmaps merged into core, `BITRANGEINTARRAY`, per-member set expiration (`SEXPIRE`, `STTL`, ...), and `BLESS` to exempt keys from eviction. — [Redis 8.12-rc1 release](https://github.com/redis/redis/releases/tag/8.12-rc1)

**Redis 8 additions (built-in "Stack" features, vector sets, arrays)**
- Redis 8.0 merged the Redis Query Engine, JSON, time series and five probabilistic structures (Bloom, Cuckoo, Count-min sketch, Top-k, t-digest) into core, plus Vector set [beta]: "These nine components are included in all binary distributions". Standalone RediSearch/RedisJSON/RedisTimeSeries/RedisBloom modules are no longer needed. It also added a `redis-full.conf`, new ACL categories (`@search`, `@json`, `@timeseries`, `@bloom`, ...), and new hash commands `HGETDEL`, `HGETEX`, `HSETEX`. — [Redis 8.0.0 release](https://github.com/redis/redis/releases/tag/8.0.0)
- From Redis 8 on, the bundled modules carry the same version number as Redis Open Source. — [Redis licenses page](https://redis.io/legal/licenses/)
- Redis 8.8 added a general-purpose Array type ("an index-addressable collection of string values", "sparse-friendly", by antirez). The docs mark Array "in preview and may be subject to change". — [Redis 8.8 blog](https://redis.io/blog/announcing-redis-8-8/); [Arrays docs](https://redis.io/docs/latest/develop/data-types/arrays/)
- Redis 8.2 added stream commands `XDELEX`, `XACKDEL`, new `BITOP` operators (`DIFF`, `DIFF1`, `ANDOR`, `ONE`), and the SVS-VAMANA vector index. — [Redis 8.2.0 release](https://github.com/redis/redis/releases/tag/8.2.0)

**Expiry (lazy + active)**
- "Redis keys are expired in two ways: a passive way and an active way". Passive: a key is expired when a client touches it after its timeout. Active: Redis periodically samples random keys that have a TTL and deletes the expired ones. — [EXPIRE docs](https://redis.io/docs/latest/commands/expire/)
- Active cycle details: runs every 100 ms (10×/s), samples `ACTIVE_EXPIRE_CYCLE_LOOKUPS_PER_LOOP` = 20 keys, repeats if more than 25% were expired. Typically ~200 keys/s are actively expired. If many keys expire in the same second and make up ≥25% of keys with a TTL, Redis can block to bring the ratio back under 25%. — [Latency guide, "Latency generated by expires"](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)
- On expiry the master synthesizes a `DEL` into the AOF and to replicas. Replicas do not expire keys on their own; they wait for the master's DEL, but keep TTL metadata so they can take over after promotion. — [EXPIRE docs](https://redis.io/docs/latest/commands/expire/)
- Defaults: `hz 10`, `active-expire-effort 1` (commented default), and all `lazyfree-lazy-*` options `no` (eviction, expire, server-del, user-del, user-flush). — [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- `EXPIRE` accepts `NX | XX | GT | LT` since 7.0.0. — [EXPIRE docs](https://redis.io/docs/latest/commands/expire/)

**Eviction and maxmemory**
- Policies: `noeviction` (writes return an error), `allkeys-lru`, `allkeys-lrm`, `allkeys-lfu`, `allkeys-random`, `volatile-lru`, `volatile-lrm`, `volatile-lfu`, `volatile-random`, `volatile-ttl`. "The volatile-xxx policies behave like noeviction if no keys have an associated expiration." "allkeys-lru is a good default option if you have no reason to prefer any others." — [Key eviction docs](https://redis.io/docs/latest/develop/reference/eviction/)
- LRU is approximate: `maxmemory-samples 5` by default, and 10 samples is very close to true LRU. LFU uses a probabilistic Morris counter with decay (`lfu-log-factor 10`, `lfu-decay-time 1`). `maxmemory 0` (no limit) is the 64-bit default. — [Key eviction docs](https://redis.io/docs/latest/develop/reference/eviction/)
- Default `maxmemory-policy noeviction`. — [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- LRM (least recently modified) policies are new in 8.6. LRU refreshes on reads and writes; LRM refreshes only on writes. Use LRM to evict data that has not been modified recently, however often it is read. — [Redis 8.6 blog](https://redis.io/blog/announcing-redis-86-performance-improvements-streams/); [Redis 8.6.0 release](https://github.com/redis/redis/releases/tag/8.6.0)

**Persistence**
- RDB: the parent forks a child that writes the snapshot, and copy-on-write keeps it consistent. `fork()` on a big dataset can stall clients "for some milliseconds or even for one second". Default save points: 3600 s/1 change, 300 s/100 changes, 60 s/10000 changes. — [Persistence docs](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/); [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- AOF fsync policies: `always` ("Very very slow, very safe"; one fsync per batch of commands from multiple clients or a pipeline, before replying), `everysec` (default, "you may lose 1 second of data"), `no` (OS decides; Linux typically flushes every 30 s). `appendonly no` and `aof-use-rdb-preamble yes` are the defaults. — [Persistence docs](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/); [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- Multi-part AOF since 7.0: one base file (RDB or AOF format), one or more incremental files, and a manifest. A rewrite opens a new incr file and atomically swaps the manifest. — [Persistence docs](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- Redis 8.10 `BACKUP` (START / LIST / SEAL) builds an MP-AOF-compatible backup (BASE + INCR + manifest) without stopping writes. Restore with `preload-file aof:/path/appendonly.aof.manifest`. — [Persistence docs](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

**Replication, Sentinel, Cluster**
- Replication is asynchronous by default. Replicas acknowledge processed data periodically. `WAIT` lowers the chance of losing acknowledged writes but does not turn Redis into a strongly consistent system. Each master has a replication ID plus offset. Replicas reconnect with `PSYNC <replid> <offset>`, which gives a partial resync if the backlog still covers the gap and a full resync otherwise. Replicas can feed sub-replicas in a cascade, and since 4.0 all sub-replicas receive the same stream as the master. — [Replication docs](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)
- Sentinel provides monitoring, notifications, automatic failover and acts as a configuration provider (service discovery). "You need at least three Sentinel instances for a robust deployment." — [Sentinel docs](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/)
- Cluster: `HASH_SLOT = CRC16(key) mod 16384`. The hard limit is 16384 masters; the suggested maximum is about 1000 nodes. No proxies, asynchronous replication, "last failover wins". Acknowledged writes can be lost in small windows, larger on the minority side of a partition. Clients are redirected with `-MOVED` and `-ASK`. — [Cluster spec](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
- Hash tags: if the key contains `{`, a `}` follows it, and at least one character sits between them, only the substring between the first `{` and the next `}` is hashed. So `{user1000}.following` and `{user1000}.followers` land in the same slot. Multi-key operations work only on keys in the same slot, and may be briefly unavailable during resharding. — [Cluster spec](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
- Redis 8.4 adds `CLUSTER MIGRATION` (atomic slot migration) and `CLUSTER SLOT-STATS` (per-slot key count, CPU, network). — [Redis 8.4.0 release](https://github.com/redis/redis/releases/tag/8.4.0)

**Transactions, Lua, Functions, pipelining**
- MULTI/EXEC/DISCARD/WATCH. "Redis does not support rollbacks of transactions since supporting rollbacks would have a significant impact on the simplicity and performance of Redis." A command that fails to queue causes an error before EXEC; otherwise EXEC runs every queued command, including those after one that fails at runtime. WATCH gives check-and-set (optimistic locking): if a watched key changes before EXEC, the whole transaction aborts (null reply). EXEC and connection close UNWATCH everything. — [Transactions docs](https://redis.io/docs/latest/develop/using-commands/transactions/)
- EVAL/EVALSHA: the script cache "can become lost at any time", after `SCRIPT FLUSH`, a restart, or a failover, so apps must reload on `NOSCRIPT`. Redis 7.0 added Functions: libraries loaded with `FUNCTION LOAD`, called with `FCALL`, persisted to AOF and replicated, "as durable as the data itself". — [Functions intro](https://redis.io/docs/latest/develop/programmability/functions-intro/); [Scripting with Lua](https://redis.io/docs/latest/develop/programmability/eval-intro/)
- Pipelining removes per-command RTT. It also cuts `read()`/`write()` syscalls, which raises throughput even on loopback. The server buffers replies in memory, so send large pipelines in batches (e.g. 10k commands). At 250 ms RTT you get at most 4 req/s without pipelining, even if the server can do 100k/s. — [Pipelining docs](https://redis.io/docs/latest/develop/using-commands/pipelining/)

**Pub/sub vs Streams**
- "Redis' Pub/Sub exhibits at-most-once message delivery semantics": a message is "forever lost" if the subscriber cannot handle it. Use Streams for stronger guarantees (persisted; at-most-once or at-least-once). Sharded pub/sub (`SSUBSCRIBE`/`SPUBLISH`, Redis 7.0) assigns channels to slots with the key hashing algorithm. Pub/sub ignores database numbers. — [Pub/Sub docs](https://redis.io/docs/latest/develop/pubsub/)
- `XAUTOCLAIM key group consumer min-idle-time start [COUNT n] [JUSTID]` is "conceptually equivalent to calling XPENDING and then XCLAIM". It returns a cursor-style next-start ID, the claimed entries, and (since 7.0) IDs of entries that were deleted or trimmed, which it also removes from the PEL. — [XAUTOCLAIM docs](https://redis.io/docs/latest/commands/xautoclaim/)
- Redis 8.4 added an `XREADGROUP ... CLAIM` option that reads idle pending entries and new entries in one call. — [Redis 8.4.0 release](https://github.com/redis/redis/releases/tag/8.4.0)
- Redis 8.6 added `XADD` idempotency (at-most-once production) with `IDMP <pid> <iid>` and `IDMPAUTO <pid>` (iid derived from message content). Known 8.6.0 limitation: avoid IDMP with `appendonly yes` + `aof-use-rdb-preamble no`. — [Redis 8.6.0 release](https://github.com/redis/redis/releases/tag/8.6.0); [Redis 8.6 blog](https://redis.io/blog/announcing-redis-86-performance-improvements-streams/)
- Redis 8.8 added `XNACK key group [SILENT|FAIL|FATAL] IDS numids id...`, which lets a consumer release pending messages explicitly for immediate redelivery. Redis 8.10 added `MAXCOUNT`/`MAXSIZE` caps on `XREAD`/`XREADGROUP`. — [Redis 8.8 blog](https://redis.io/blog/announcing-redis-8-8/); [Redis 8.10.0 release](https://github.com/redis/redis/releases/tag/8.10.0)

**Client-side caching**
- Two modes. Default mode: the server remembers which keys each client read (costs server memory, using an Invalidation Table capped by `tracking-table-max-keys`) and sends invalidations. Broadcasting mode (BCAST): clients subscribe to key prefixes and the server keeps no per-client state. Invalidations also fire on expiry and eviction. — [Client-side caching reference](https://redis.io/docs/latest/develop/reference/client-side-caching/); [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- Jedis client-side caching needs RESP3: `.protocol(RedisProtocol.RESP3)` plus `.cacheConfig(CacheConfig.builder().maxSize(1000).build())`. — [Jedis connect docs](https://redis.io/docs/latest/develop/clients/jedis/connect/)

**Locks, CAS and rate limiting primitives**
- Single-instance lock: `SET resource_name my_random_value NX PX 30000`. The value must be unique across all clients and requests (e.g. 20 bytes from /dev/urandom). Release with Lua `if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) else return 0 end`, or on Redis 8.4+ with `DELEX key IFEQ my_random_value`. Redlock uses N=5 independent masters; the lock is acquired if a majority (≥3) succeed within the validity time; it assumes bounded clock drift. The page asks readers to review the "Analysis of Redlock" section. — [Distributed locks docs](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)
- `DELEX key [IFEQ v | IFNE v | IFDEQ digest | IFDNE digest]`, since 8.4.0. O(1) for IFEQ/IFNE, O(N) for digest variants. `SET` gained the same `IFEQ/IFNE/IFDEQ/IFDNE` conditions alongside `NX|XX`, `GET`, `EX/PX/EXAT/PXAT/KEEPTTL`. The digest is a 64-bit xxh3 hash (`DIGEST` command). — [DELEX docs](https://redis.io/docs/latest/commands/delex/); [SET docs](https://redis.io/docs/latest/commands/set/); [Redis 8.4.0 release](https://github.com/redis/redis/releases/tag/8.4.0)
- Lettuce exposes `delex` with "@since 7.1". — [DELEX docs (client signatures)](https://redis.io/docs/latest/commands/delex/)
- `INCREX key [BYFLOAT inc | BYINT inc] [LBOUND lb] [UBOUND ub] [SATURATE] [EX|PX|EXAT|PXAT|PERSIST] [ENX]` (8.8) does an atomic bounded increment with expiry control. It returns `[new_value, applied_increment]`. Out of bounds, it skips and returns `[current, 0]` unless `SATURATE` is set. Redis positions it as a window-counter rate limiter. — [INCREX docs](https://redis.io/docs/latest/commands/increx/); [Redis 8.8.0 release](https://github.com/redis/redis/releases/tag/8.8.0)

**Latency and diagnostics**
- Defaults: `slowlog-log-slower-than 10000` (µs = 10 ms), `slowlog-max-len 128`, `latency-monitor-threshold 0` (disabled). — [redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)
- Latency checklist: disable Transparent Huge Pages, measure the baseline with `redis-cli --intrinsic-latency 100` on the server, avoid slow fork environments (e.g. old Xen), avoid swapping, and watch AOF/disk I/O and expiry storms. — [Latency guide](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)
- `HOTKEYS START | STOP | GET | RESET` (since 8.6.0) tracks keys by CPU-time share and network-byte share, with sampling. — [HOTKEYS docs](https://redis.io/docs/latest/commands/hotkeys/)
- SCAN guarantees: a full iteration returns every element present for the whole iteration and never returns elements absent for the whole iteration. "A given element may be returned multiple times." COUNT is a hint (default 10). — [SCAN docs](https://redis.io/docs/latest/commands/scan/)
- Redis 8.2 added per-slot usage and key-size distribution metrics. 8.6 added key memory histograms (`key-memory-histograms`). — [Redis 8.2.0 release](https://github.com/redis/redis/releases/tag/8.2.0); [Redis 8.6.0 release](https://github.com/redis/redis/releases/tag/8.6.0)

### Inferences
- Recommended concept order: (1) model and protocol; (2) core types and encodings; (3) specialized types and Redis 8 built-ins; (4) expiry, eviction and memory; (5) caching patterns; (6) atomicity (MULTI/WATCH, Lua, Functions, pipelining); (7) rate limiting and idempotency; (8) distributed locks; (9) pub/sub and Streams; (10) persistence, replication, Sentinel; (11) Cluster and latency/ops. Patterns (5, 7, 8) come after atomicity because each depends on "why this has to be one atomic step".
- Lock release can now use `DELEX IFEQ` (8.4+), so Lua is no longer *required* for safe release. Lua is still the general tool for multi-step atomic logic (sliding window, token bucket). Teach Lua first for transferable understanding, then show `DELEX IFEQ` as the modern primitive.
- `INCREX` (8.8) replaces the `INCR` + `EXPIRE` fixed-window race (key without TTL if the client dies between the two commands). It is a good "before/after" moment, but it ties the lab to Redis ≥ 8.8 and probably excludes Valkey (unverified).
- The I/O-threads numbers are vendor benchmarks. Present them as "Redis can now use more cores for network I/O", not as guaranteed speedups.

### Gaps
- HyperLogLog standard error (0.81%) and max size (12 KB), and geo indexes being sorted sets with 52-bit geohash scores: standard facts, not re-fetched this session (verify on redis.io HLL/geo pages).
- The release that replaced ziplist with listpack (7.0) was not re-verified; only the current `*-listpack-*` config names were.
- The exact `CROSSSLOT` error text was not captured from the cluster spec (expected: "CROSSSLOT Keys in request don't hash to the same slot"; verify).
- Hash-field TTL (`HEXPIRE` family) is believed to have shipped in Redis 7.4 (verify). Confirmed for Valkey 9.0 (see §2).
- Whether 8.x script effects replication allows `redis.call('TIME')` inside a writing script (relevant to sliding-window Lua using server time) was not verified; believed true since 7.0 because effects replication is the only mode (verify).

---

## 2. Current state as of November 2026: versions, licensing, Valkey, Docker, Java/Kotlin clients, Testcontainers

### Takeaway
On 2026-11-07, stable Redis Open Source is **8.10.3** (`redis:8` → 8.10.3); **8.12** is at RC2. Older lines (8.8.4, 8.6.8, 8.4.8, 8.2.11, 7.4.12) got patches on 2026-10-26. Redis 8+ is tri-licensed RSALv2 / SSPLv1 / **AGPLv3**. Valkey (Linux Foundation, BSD) is at **9.1.3** stable with 9.2.0-rc2 out. Java clients: **Jedis 8.0.2**, **Lettuce 7.9.0.RELEASE** (8.0 in beta), **Redisson 4.8.0**, **Spring Data Redis 4.1.2** (Spring Boot 4.1.x; 4.2 at RC). Testing: **Testcontainers 2.0.5** (no official Redis module, so use `GenericContainer`) or **com.redis:testcontainers-redis 3.0.1**.

### Cited Findings

**Redis release timeline (GitHub releases)**
- 8.0.0 GA 2025-05-02; 8.2.0 GA 2025-08-04; 8.4.0 GA 2025-11-18; 8.6.0 GA 2026-02-10; 8.8.0 GA 2026-05-25; 8.10.0 GA 2026-07-29. — [redis/redis releases](https://github.com/redis/redis/releases)
- Latest as of 2026-11-07: 8.10.3 (2026-10-26). Same-day patches: 8.8.4, 8.6.8, 8.4.8, 8.2.11, 7.4.12. Pre-releases: 8.12-rc1 (2026-10-29), 8.12-rc2 (2026-11-01). — [redis/redis releases](https://github.com/redis/redis/releases)
- Redis 8.0 renamed "Redis Community Edition" to "Redis Open Source". — [Redis 8.0.0 release](https://github.com/redis/redis/releases/tag/8.0.0)
- Redis 8.8 and 8.10 are tested on macOS 14.8.4, 15.7.4 and 26.3 (Tahoe), "for both Intel and ARM". — [Redis 8.10.0 release](https://github.com/redis/redis/releases/tag/8.10.0)

**Licensing history**
- ≤7.2.x: BSD-3-Clause. 7.4.x–7.8.x: RSALv2 or SSPLv1 (dual). ≥8.0.0: RSALv2 or SSPLv1 or AGPLv3 (user's choice). The bundled modules (RediSearch, RedisJSON, RedisTimeSeries, RedisBloom) are under the same tri-license. Jedis and Lettuce are MIT. Redis says it has "no plans to change or add to the current Redis Open Source license configuration". — [Redis licenses page](https://redis.io/legal/licenses/)
- The AGPLv3 announcement (Rowan Trollope, 2025-05-01) recounts the March 2024 move to SSPL. It states "AWS and Google now maintain their own fork". antirez rejoined Redis in November 2024. AGPL was added "starting with Redis 8". — [Redis AGPLv3 blog](https://redis.io/blog/agplv3/)
- The Docker Hub page confirms: tri-license from 8.0, ≤7.2.4 BSD, 7.4.x–7.8.x RSALv2/SSPLv1. — [Docker Hub redis](https://hub.docker.com/_/redis)

**Valkey**
- "Valkey is an open source (BSD) high-performance key/value datastore ... backed by the Linux Foundation". The homepage lists 9.1.3 and 9.0.7 as current. — [valkey.io](https://valkey.io/)
- Releases: 9.0.0 GA 2025-10-21; 9.1.0 GA 2026-05-19; latest 9.1.3 (2026-10-26) and 9.0.7 (2026-10-27); maintained 8.1.11, 8.0.12, 7.2.15; 9.2.0-rc2 2026-11-04. — [valkey-io/valkey releases](https://github.com/valkey-io/valkey/releases)
- Valkey 9.0 headline features: atomic slot migration (whole slots via the AOF format, not key by key), hash field expiration (`HEXPIRE`, `HGETEX`, `HSETEX`, `HTTL`, ...), numbered databases in cluster mode (a break from Redis, where cluster mode allows only db 0), scaling to 2,000 nodes / >1B req/s, pipeline memory prefetch (up to 40% higher throughput), and un-deprecation of 25 commands. — [Valkey 9.0 blog](https://valkey.io/blog/introducing-valkey-9/)
- Valkey 9.1 (rc1 notes): database-level access control, the Lua engine moved into a Valkey module, `CLUSTERSCAN` (cluster-wide scan), `MSETEX`, `HGETDEL`, NX/XX on `HSETEX`, `CLUSTER KEYSLOT` in standalone mode, availability-zone field in `CLUSTER SHARDS`, and zset memory optimizations. — [Valkey 9.1.0-rc1 release](https://github.com/valkey-io/valkey/releases/tag/9.1.0-rc1)
- 9.1.0 GA security fixes include CVE-2026-23479 (UAF in unblock), CVE-2026-25243 (RESTORE), and CVE-2026-23631. — [Valkey 9.1.0 release](https://github.com/valkey-io/valkey/releases/tag/9.1.0)

**Docker images**
- `redis` official image tags: `8.10.3, 8.10, 8, 8.10.3-trixie, 8.10-trixie, 8-trixie, latest, trixie`, plus alpine variants. Maintained lines 8.0, 8.2 (bookworm), 8.4, 8.6, 8.8 (trixie). Architectures include `arm64v8`, so Apple Silicon runs natively. "Protected mode" is turned off by default in the image, so publishing the port exposes Redis with no password. — [Docker Hub redis](https://hub.docker.com/_/redis)
- `valkey/valkey` tags: `9.1.3, 9.1, 9, latest, ...-trixie`, alpine variants; 9.0.7, 8.1.11, 8.0.12 lines. — [Docker Hub valkey/valkey](https://hub.docker.com/r/valkey/valkey)
- Redis 8 GA notes list "Alpine and Debian Docker images" among the binary distributions that include all nine Redis 8 components. — [Redis 8.0.0 release](https://github.com/redis/redis/releases/tag/8.0.0)

**Jedis**
- Stable 8.0.2 (2026-10-07). 8.0.0 GA 2026-08-10. 8.1.0-beta2 2026-10-26. 7.5.3 (2026-07-01) is the last 7.x seen. — [redis/jedis releases](https://github.com/redis/jedis/releases)
- 8.0 removes `JedisPooled`/`JedisSentineled` in favor of the RedisClient family introduced in 7.0.0, removes deprecated `UnifiedJedis` constructors, makes RESP3 auto-negotiation the default, enforces TLS hostname verification by default, and covers Redis 8.8/8.10 commands (XNACK, INCREX, Array commands, HIMPORT, LMOVEM, SUNIONCARD, ...). — [Jedis 8.0.0 release](https://github.com/redis/jedis/releases/tag/v8.0.0)
- JDK compatibility: Jedis ≥8.0 supports JDK 8, 11, 17, 21, 25 and Redis 7.2 → current. API: `RedisClient jedis = RedisClient.builder().hostAndPort("localhost", 6379).build();` and `RedisClusterClient.builder().nodes(Set<HostAndPort>).build()`. — [Jedis README](https://github.com/redis/jedis)
- RedisClient (from 7.2.0) pools connections automatically. — [Jedis connect docs](https://redis.io/docs/latest/develop/clients/jedis/connect/)
- Pipeline: `try (AbstractPipeline pipe = jedis.pipelined()) { ...; pipe.sync(); }`, with `Response<T>.get()` valid after sync. Transaction: `try (AbstractTransaction trans = jedis.multi()) {...}`. WATCH: `try (AbstractTransaction trans = jedis.transaction(false)) { trans.watch("k"); ... trans.multi(); ... trans.exec(); }` (`transaction(false)` builds a Transaction without sending MULTI). — [Jedis transactions/pipelines docs](https://redis.io/docs/latest/develop/clients/jedis/transpipe/)
- The legacy `Jedis` class "doesn't fully support RESP3" and ignores auto-negotiation. — [Jedis v7→v8 migration](https://redis.github.io/jedis/migration-guides/v7-to-v8/)

**Lettuce**
- Stable 7.9.0.RELEASE (2026-10-14). 8.0.0.BETA1 (2026-10-14). 6.9.0.RELEASE (2026-10-16) on a maintenance line. — [redis/lettuce releases](https://github.com/redis/lettuce/releases)
- 7.9.0: Java 8+, "works with Java 24", tested against Redis 7.2–8.10. — [Lettuce 7.9.0 release](https://github.com/redis/lettuce/releases/tag/7.9.0.RELEASE)
- 7.0.0 (2025-10-23): Netty 4.2, maintenance-events ("hitless upgrades") support, adaptive cluster topology refresh on by default, and `KEYS` made keyless (breaking). — [Lettuce 7.0.0 release](https://github.com/redis/lettuce/releases/tag/7.0.0.RELEASE)
- 8.0 (beta): Project Reactor becomes optional for sync/async APIs. The reactive API and **Kotlin coroutines API still require Reactor**. Adds TimeSeries commands and `BLESS` support (Redis 8.12), and removes Reactor-based APIs deprecated in 7.8/7.9. — [Lettuce 8.0.0.BETA1 release](https://github.com/redis/lettuce/releases/tag/8.0.0.BETA1); [Lettuce new-features.md](https://github.com/redis/lettuce/blob/main/docs/new-features.md)
- Kotlin: coroutines support activates when `kotlinx-coroutines-core` and `kotlinx-coroutines-reactive` are on the classpath. `val api: RedisCoroutinesCommands<String,String> = connection.coroutines()`. Extensions are experimental and need `@ExperimentalLettuceCoroutinesApi` opt-in. — [Lettuce Kotlin API guide](https://redis.github.io/lettuce/user-guide/kotlin-api/)
- Lettuce transactions on a shared connection need care: "either by serializing transactions or by providing a dedicated connection"; `redis.watch(key)` then `multi()`/`exec()`. — [Lettuce transactions guide](https://redis.github.io/lettuce/user-guide/transactions-multi/)
- The redis.io Lettuce reactive examples use `connection.commands(RedisReactiveCommands.factory())` (the newer accessor; `reactive()` is a deprecated default method in 8.0). — [EXPIRE docs (Lettuce example)](https://redis.io/docs/latest/commands/expire/); [Lettuce new-features.md](https://github.com/redis/lettuce/blob/main/docs/new-features.md)

**Redisson**
- Latest 4.8.0 (2026-10-02); 4.7.0 (2026-08-04). — [redisson releases](https://github.com/redisson/redisson/releases)
- Locks: `RLock` follows the Java Lock spec (only the owner thread can unlock, otherwise `IllegalMonitorStateException`). A lock watchdog extends expiry while the holder is alive; the default `lockWatchdogTimeout` is 30 s. `tryLock(100, 10, SECONDS)` waits up to 100 s and auto-releases after 10 s. `RFencedLock` (`redisson.getFencedLock("myLock")`, `tryLockAndGetToken()`) returns a monotonically increasing fencing token. **`RedLock` is deprecated**: "The algorithm's safety guarantees are contested ... superseded by RLock ... and by RFencedLock when a fencing token is required." — [Redisson locks docs](https://redisson.pro/docs/data-and-services/locks-and-synchronizers/)
- Rate limiter: `RRateLimiter limiter = redisson.getRateLimiter("myLimiter"); limiter.trySetRate(RateType.OVERALL, 5, 2, RateIntervalUnit.SECONDS);` with `RateType.OVERALL` vs `PER_CLIENT`; "does not guarantee fairness". — [Redisson objects docs](https://redisson.pro/docs/data-and-services/objects/)

**Spring**
- Spring Data Redis 4.1.2 and 4.0.8 (2026-10-23); 4.2.0-RC1 (2026-10-23). — [spring-data-redis releases](https://github.com/spring-projects/spring-data-redis/releases)
- SDR 4.1.0 added `RedisMessageSendingTemplate`, DIGEST support, a SET API with CAS options (Redis 8.4 IFEQ etc.), and deprecated `TimeUnit`-based template methods. — [SDR 4.1.0 release](https://github.com/spring-projects/spring-data-redis/releases/tag/4.1.0)
- Spring Boot 4.1.2 / 4.0.9 (2026-10-22); 4.2.0-RC2 (2026-11-05). — [spring-boot releases](https://github.com/spring-projects/spring-boot/releases)

**Testing stack**
- Testcontainers Java 2.0.5 (2026-04-20) is the latest per GitHub and Maven Central. The JUnit 5 quickstart uses `testImplementation "org.testcontainers:testcontainers-junit-jupiter:2.0.5"` and `new GenericContainer(DockerImageName.parse("redis:6-alpine")).withExposedPorts(6379)`. — [Testcontainers JUnit 5 quickstart](https://java.testcontainers.org/quickstart/junit_5_quickstart/); [testcontainers-java releases](https://github.com/testcontainers/testcontainers-java/releases)
- No `org.testcontainers:testcontainers-redis` artifact exists on Maven Central (metadata lookup returned not found), i.e. no official Redis module. — [Maven Central path](https://repo1.maven.org/maven2/org/testcontainers/)
- `com.redis:testcontainers-redis` 3.0.1 (2026-10-28): supports Redis Standalone and Cluster, Redis modules, Redis Enterprise. The 3.x line uses Testcontainers 2, JUnit 6 and Spring Boot 4.1 dependency management, with Java 17 minimum. API: `new RedisContainer(RedisContainer.DEFAULT_IMAGE_NAME.withTag(RedisContainer.DEFAULT_TAG))`, `container.getRedisURI()`. — [testcontainers-redis README](https://github.com/redis-field-engineering/testcontainers-redis)
- JUnit Jupiter latest on Maven Central: 6.1.3. kotlinx-coroutines: 1.11.0. — [junit-jupiter metadata](https://repo1.maven.org/maven2/org/junit/jupiter/junit-jupiter/maven-metadata.xml); [kotlinx-coroutines-reactor metadata](https://repo1.maven.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-reactor/maven-metadata.xml)
- Gradle current: 9.9.0 (built 2026-11-06). Kotlin latest stable: 2.4.21 (2026-10-08); 2.5.0-Beta2 in preview. — [Gradle current version](https://services.gradle.org/versions/current); [Kotlin releases](https://github.com/JetBrains/kotlin/releases)

### Inferences
- Pin `redis:8.10` (or `redis:8.10.3`) in labs rather than `redis:8`. `redis:8` will move to 8.12 within weeks of this research (8.12 is at RC2), and floating tags make the "observe encoding/eviction" labs non-reproducible.
- Primary client recommendation for the course: **Lettuce 7.9** for Kotlin (coroutines, async, cluster). **Jedis 8.0** for Java labs where a blocking, explicit API keeps the lesson simple (pipelines, WATCH). **Redisson 4.8** only in the lock and rate-limiter lessons, as "what a production library does". Spring Data Redis appears once, in the caching lesson (`@Cacheable` + `RedisCacheManager`).
- Avoid Lettuce 8.0.0.BETA1 in course material; it is a beta with breaking changes. Revisit when 8.0 GA ships (flag as likely to change soon).
- Redis 8.x-only labs (`DELEX IFEQ`, `INCREX`, `XADD IDMP`, `HOTKEYS`, LRM) should be marked "Redis 8.4+/8.6+/8.8+" with the classic implementation as the main path, so learners who choose Valkey can still finish.
- The SDR API shapes I expect to use (`StringRedisTemplate.opsForValue().setIfAbsent(k, v, Duration)`, `execute(SessionCallback)` for WATCH/MULTI, `DefaultRedisScript<Long>`, `StreamMessageListenerContainer`, `RedisCacheManager.builder(cf).cacheDefaults(RedisCacheConfiguration.defaultCacheConfig().entryTtl(...))`) come from background knowledge and were not re-verified against 4.1 docs (verify; note 4.1 deprecates TimeUnit-based methods, so prefer `Duration`).

### Gaps
- Lettuce 7.9 release notes say "works with Java 24". I found no explicit statement of JDK 25 support (likely fine; verify by running the lab suite on JDK 25).
- Kotlin 2.4.x `jvmTarget = 25` support and the Gradle 9.9 + JDK 25 toolchain combination were not explicitly verified (verify).
- `RedisContainer.DEFAULT_TAG` in testcontainers-redis 3.0.1 was not inspected. Pass an explicit `redis:8.10` image instead.
- Whether Valkey 9.x has equivalents of Redis 8.4+ `DELEX`/`SET IFEQ`, 8.8 `INCREX`, 8.6 `XADD IDMP`/LRM eviction was not verified. Whether the `valkey/valkey` image bundles JSON/Bloom/Search modules was not verified.
- Valkey forked from Redis 7.2.4 in March 2024 under the Linux Foundation. That is widely reported; this session's sources only confirm "Linux Foundation" and "BSD" (valkey.io) and that "AWS and Google now maintain their own fork" (redis.io blog).
- Testcontainers 2.x compatibility with Docker Desktop / OrbStack / Colima on macOS (Docker Engine API version negotiation) was not checked this session.

---

## 3. Misconceptions to address explicitly

### Takeaway
Every misconception on the brief has a direct primary-source rebuttal, and each one can become a failing-then-passing test. Add four more that bite Java engineers: "pipelining is atomic", "SCAN returns each key once", "Lua scripts are stored forever", and "WAIT makes it strongly consistent".

### Cited Findings
- **"Redis is just a cache."** Valkey describes itself as supporting "caching, message queues, and can act as a primary database" ([valkey.io](https://valkey.io/)). Redis offers RDB/AOF durability ([Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)), persisted Streams with at-least-once delivery ([Pub/Sub docs](https://redis.io/docs/latest/develop/pubsub/)), and in 8.x a built-in Query Engine, JSON and vector sets ([Redis 8.0.0 release](https://github.com/redis/redis/releases/tag/8.0.0)).
- **"Single-threaded, so it can't use multiple cores at all."** Redis is "mostly single threaded". `UNLINK`, slow I/O and other operations run on side threads, and `io-threads` moves socket reads/writes and parsing to threads ([redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)). Redis 8 measured up to 112% throughput gains with 8 I/O threads ([Redis 8 GA blog](https://redis.io/blog/redis-8-ga/)). RDB/AOF rewrite run in a forked child process ([Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)). Command execution itself is still serialized, which is why one slow command blocks everyone ([Latency guide](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)).
- **"EXPIRE deletes the key exactly on time."** Expiry is passive (on access) plus active sampling (20 keys, every 100 ms, repeated if >25% expired) ([Latency guide](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/); [EXPIRE](https://redis.io/docs/latest/commands/expire/)). Replicas wait for the master's synthesized DEL ([EXPIRE](https://redis.io/docs/latest/commands/expire/)). An expired-but-unreclaimed key is invisible to reads but still uses memory until reclaimed.
- **"MULTI is a rollback-capable transaction."** "Redis does not support rollbacks." Commands after a runtime error in EXEC still execute ([Transactions](https://redis.io/docs/latest/develop/using-commands/transactions/)).
- **"Pub/sub is durable."** "at-most-once ... the message is forever lost" ([Pub/Sub docs](https://redis.io/docs/latest/develop/pubsub/)).
- **"Redlock gives safe mutual exclusion."** Kleppmann splits locks into those used for efficiency and those used for correctness. For correctness he argues that process pauses (GC), network delay and clock jumps break timing-based leases, and proposes fencing tokens that the storage service checks ([Kleppmann 2016](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)). antirez replies that a large random token can implement check-and-set on the resource. He agrees Redis should use monotonic time, and argues relative time is bounded without clock-altering admins/ntpd jumps ([antirez, "Is Redlock safe?"](https://antirez.com/news/101)). Redis docs now tell readers to review the "Analysis of Redlock" section ([Distributed locks](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)). Redisson has deprecated its RedLock because "the algorithm's safety guarantees are contested" ([Redisson locks](https://redisson.pro/docs/data-and-services/locks-and-synchronizers/)).
- **"AOF always means no data loss."** `everysec` (default) can lose ~1 s; `no` defers to the OS (~30 s on Linux) ([Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)). Even with persistence, asynchronous replication can lose acknowledged writes on failover ([Cluster spec](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/); [Replication](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)).
- **"KEYS * is fine in prod."** The latency guide names `KEYS` in production as the classic slow-command problem. Use `SCAN`, which has weaker guarantees: duplicates are possible, and keys added mid-iteration may or may not appear ([Latency guide](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/); [SCAN](https://redis.io/docs/latest/commands/scan/)).
- **Extra: "pipelining = transaction".** Pipelining only batches round trips; the docs contrast it with scripting for atomic server-side logic ([Pipelining](https://redis.io/docs/latest/develop/using-commands/pipelining/)).
- **Extra: "EVALSHA scripts live forever."** The script cache can be lost on restart/failover. Functions are persisted and replicated ([Functions intro](https://redis.io/docs/latest/develop/programmability/functions-intro/)).
- **Extra: "WAIT gives strong consistency."** WAIT reduces but does not remove the chance of losing writes ([Replication](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)).
- **Extra: "volatile-* policies always evict something."** They "behave like noeviction if no keys have an associated expiration" ([Eviction](https://redis.io/docs/latest/develop/reference/eviction/)). The default policy is `noeviction`, so writes fail at maxmemory ([redis.conf 8.10](https://raw.githubusercontent.com/redis/redis/8.10/redis.conf)).

### Inferences
- Each misconception maps to a lab test: rollback → `ExecDoesNotRollbackTest`; pub/sub durability → `PubSubLosesMessagesWhileDisconnectedTest`; naive DEL lock → `NaiveUnlockDeletesOtherOwnersLockTest`; AOF → `KillNineLosesWritesWithAppendfsyncNo` (optional, slow); KEYS → `KeysBlocksConcurrentGetsTest` measuring p99 of concurrent GETs; expiry → read `INFO stats expired_keys` growth rather than asserting exact deletion time.

### Gaps
- No quantitative source on how often Redlock fails in practice; the debate is theoretical (fine to present it that way).

---

## 4. Lab design: Gradle (Kotlin + Java), JUnit, Testcontainers on Apple Silicon

### Takeaway
One Gradle multi-module repo (`labs/redis-*`) on JDK 25, Kotlin 2.4.21 + Java, JUnit 6, Testcontainers 2.0.5 with `redis:8.10` (arm64-native). Each lab ships a failing test suite the learner makes green. Everything is free and local: Docker Desktop (or OrbStack/Colima) on macOS. The only tricky lab is Redis Cluster, because of host↔container networking on macOS.

### Cited Findings
- Redis official images support `arm64v8` ([Docker Hub redis](https://hub.docker.com/_/redis)). Redis 8.8/8.10 are tested on macOS ARM ([Redis 8.10.0 release](https://github.com/redis/redis/releases/tag/8.10.0)).
- Testcontainers 2 coordinates: `org.testcontainers:testcontainers-junit-jupiter:2.0.5`; `GenericContainer(DockerImageName.parse("redis:..."))`, `.withExposedPorts(6379)` ([Testcontainers quickstart](https://java.testcontainers.org/quickstart/junit_5_quickstart/)).
- `com.redis:testcontainers-redis:3.0.1` supports Standalone **and Cluster** containers on Testcontainers 2 / JUnit 6 / Java 17+ ([testcontainers-redis README](https://github.com/redis-field-engineering/testcontainers-redis)).
- Jedis pipeline/WATCH API shapes ([Jedis transpipe docs](https://redis.io/docs/latest/develop/clients/jedis/transpipe/)). Lettuce Kotlin coroutines dependencies and opt-in ([Lettuce Kotlin guide](https://redis.github.io/lettuce/user-guide/kotlin-api/)). Redisson lock/limiter shapes ([Redisson locks](https://redisson.pro/docs/data-and-services/locks-and-synchronizers/); [Redisson objects](https://redisson.pro/docs/data-and-services/objects/)).
- The safe-release Lua and the `DELEX IFEQ` alternative come from the Redis docs ([Distributed locks](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)).
- Pipelining guidance: batch around 10k commands to bound reply-buffer memory ([Pipelining](https://redis.io/docs/latest/develop/using-commands/pipelining/)).
- `XAUTOCLAIM` returns `[next-start, claimed-entries, deleted-ids]` ([XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/)).
- Docker image has protected mode off, so do not publish lab ports beyond localhost ([Docker Hub redis](https://hub.docker.com/_/redis)).

### Inferences (proposed lab designs; the writer should validate by running them)

**Build skeleton (`build.gradle.kts`, proposed):**
```kotlin
plugins { kotlin("jvm") version "2.4.21" }          // Kotlin + Java sources in one module is fine
kotlin { jvmToolchain(25) }                         // verify Kotlin 2.4 supports target 25; else 21
dependencies {
  implementation("redis.clients:jedis:8.0.2")
  implementation("io.lettuce:lettuce-core:7.9.0.RELEASE")
  implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
  implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactive:1.11.0") // needed by Lettuce coroutines
  implementation("org.redisson:redisson:4.8.0")      // lock/limiter lessons only
  testImplementation(platform("org.junit:junit-bom:6.1.3"))
  testImplementation("org.junit.jupiter:junit-jupiter")
  testRuntimeOnly("org.junit.platform:junit-platform-launcher")
  testImplementation("org.testcontainers:testcontainers-junit-jupiter:2.0.5")
  testImplementation("com.redis:testcontainers-redis:3.0.1") // optional; for cluster lab
  testImplementation("org.awaitility:awaitility-kotlin:<latest>") // for async assertions (version not checked)
}
```
Shared fixture: an abstract `RedisTestBase` with a static `GenericContainer("redis:8.10").withExposedPorts(6379)` and `FLUSHALL` in `@BeforeEach`. For eviction/persistence labs, a per-test container with `withCommand("redis-server", "--maxmemory", "2mb", "--maxmemory-policy", "allkeys-lru")`.

**Lab catalog (testable outcomes):**
1. **Harness + single-thread proof.** PING via Jedis `RedisClient` and Lettuce coroutines. `HELLO 3` shows RESP3 negotiation (Jedis 8 default). Test: run `EVAL` with a ~1.5 s busy loop on one connection; a concurrent `GET` on another connection takes ≥1 s. This proves serialized execution.
2. **Encodings.** Test: `OBJECT ENCODING` of a zset is `listpack` at 128 members and `skiplist` at 129 (default `zset-max-listpack-entries 128`). Same for hash at 512/513 → `hashtable`, and set of ints `intset` → `listpack`/`hashtable`. `MEMORY USAGE` grows sharply at the transition.
3. **Leaderboard.** `ZINCRBY`, `ZREVRANGE 0 9 WITHSCORES` (or `ZRANGE ... REV`), `ZREVRANK`, `ZSCORE`, plus "players around me". Tests: ties order lexicographically by member; rank is 0-based; to break ties by time, use a composite score (score * 1e10 + (MAX_TS - ts)) and test it, showing why double precision limits composite scores (53-bit mantissa).
4. **Eviction.** Container with `maxmemory 2mb`. Tests: (a) `noeviction` → writes fail with an OOM error once full; (b) `allkeys-lru` → keys you keep reading survive while cold keys go (assert hot-set survival rate > X%, not exact); (c) `volatile-ttl` with no TTL keys behaves like noeviction; (d) watch `INFO stats evicted_keys` rise. Optional 8.6+: `allkeys-lrm` keeps frequently read but rarely modified keys alive differently from LRU.
5. **Cache-aside with stampede protection.** `ProductRepository` (fake slow DB with call counter) wrapped by `CachedProductRepository`: TTL with ±10% jitter, negative caching of "not found" with a short TTL, and single-flight via `ConcurrentHashMap<String, CompletableFuture<V>>` (Java) or `Mutex`/`Deferred` (Kotlin). Tests: 200 concurrent misses for one key → DB called once per JVM; TTLs across 1000 keys are not identical (jitter); a missing id hits the DB once within the negative-TTL window. Stretch: a distributed single-flight with `SET lock:{k} token NX PX 3000`, where losers poll or serve stale. Stretch 2: Jedis client-side caching (`CacheConfig`, RESP3); a test shows the second GET needs no network hit and a write from another client invalidates.
6. **WATCH-based optimistic transfer.** `transfer(from, to, amount)` using Jedis `transaction(false)` → `watch` → read → `multi` → `decrby`/`incrby` → `exec`, retrying on null EXEC. Test: 50 threads doing random transfers keep the total balance invariant and never go negative; count retries > 0. Companion test `ExecDoesNotRollback`: `MULTI; SET a 1; INCR a-string-key; SET b 2; EXEC` leaves `b` set.
7. **Pipelining benchmark.** 1000 `SET`s sequential vs one pipeline (Jedis `pipelined()`/`sync()`; Lettuce async with manual flush as the stretch). Assert pipelined time < sequential / 3 (loose, to avoid flakiness on Docker Desktop). Print ops/s. Discussion: why Lettuce async already pipelines across threads.
8. **Rate limiters.** (a) Fixed window `INCR` + `EXPIRE` with a test showing the TTL-less key if the process dies between the two commands (simulate by skipping EXPIRE). Fix with Lua, or `INCREX ... EX ... ENX` on 8.8+. (b) Sliding-window log with ZSET (`ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`, `PEXPIRE`): a non-atomic version over-admits under 32 concurrent callers (assert admitted > limit). (c) The same logic as one Lua script admits exactly `limit`. (d) Token bucket in Lua (hash with `tokens`, `ts`; refill = min(cap, tokens + Δt·rate)), with a test of burst then steady-rate admission using an injectable clock passed as ARGV. (e) Compare with Redisson `RRateLimiter.trySetRate(OVERALL, ...)`.
9. **Idempotency-key store for payments.** `POST /payments` with an `Idempotency-Key` header. `SET idem:{key} "PENDING:<reqHash>" NX EX 86400`: if OK, charge, then store `DONE:<reqHash>:<responseJson>` with `XX KEEPTTL` (or `SET ... IFEQ "PENDING:<hash>"` on 8.4+ so only the owner finalizes). If it exists: PENDING → 409 retry-later; DONE with same hash → replay the stored response; different hash → 422. Tests: 20 concurrent identical requests → exactly one charge; replay returns a byte-identical body; a different body with the same key → 422; crash during PENDING → the key expires (short TTL in test) and a retry succeeds.
10. **Distributed lock.** `SET lock:{r} <uuid> NX PX ttl`; release via Lua compare-and-delete (and `DELEX IFEQ` variant). Unsafe-DEL test: A acquires (ttl 200 ms) and "GC-pauses" (sleep 400 ms); B acquires; A calls naive `DEL` and wipes B's lock; C acquires while B still thinks it holds it. Assert 2 holders. Same scenario with token release → B's lock survives. Fencing: `INCR fence:{r}` on acquire, and a fake storage service rejects writes with a token < max seen. The test shows A's late write is rejected. Compare Redisson `RLock` watchdog and `RFencedLock.tryLockAndGetToken()`.
11. **Streams worker with recovery.** Producer `XADD orders * ...`; `XGROUP CREATE orders workers $ MKSTREAM`; workers `XREADGROUP GROUP workers c1 COUNT 10 BLOCK 2000 STREAMS orders >` then `XACK`. Test: c1 reads 10 and "crashes" without ack; `XPENDING` shows 10; c2 runs `XAUTOCLAIM orders workers c2 100 0-0` after min-idle, processes and acks. The PEL ends empty and the handler (idempotent by message ID) applied each order exactly once. Stretch (8.4+): `XREADGROUP ... CLAIM`; (8.8+) `XNACK`; (8.6+) `XADD IDMP` producer dedupe. Companion: pub/sub test where a message published while the subscriber is disconnected is never received.
12. **Persistence and replication (optional/slow).** Container with `appendonly yes appendfsync everysec`, write a counter in a tight loop, `docker kill` (SIGKILL), restart from the same volume, and assert loss ≤ ~1 s of writes. With `appendonly no` and default save points, the loss is larger. Replication: primary + replica containers on a Testcontainers `Network`; `WAIT 1 100` returns 1; stop the replica, `WAIT` returns 0.
13. **Cluster: MOVED and hash tags.** 3-master cluster (testcontainers-redis cluster container, or docker compose). Tests: a non-cluster-aware connection to node A doing `SET` on a key owned by node B gets a MOVED redirect (Jedis surfaces it as an exception; verify class name, likely `JedisMovedDataException`). `RedisClusterClient` handles it transparently. `MSET {user:42}:a 1 {user:42}:b 2` works while `MSET a 1 b 2` fails with CROSSSLOT. `CLUSTER KEYSLOT` is equal for tagged keys.
14. **Latency hunt (ops).** Load 1M keys (pipelined), run `KEYS *` while a background coroutine measures GET latency, and assert a p99 spike plus a `SLOWLOG GET` entry for KEYS. Replace with `SCAN` + `COUNT 1000` and show no spike. `redis-cli --bigkeys` / `MEMORY USAGE`; on 8.6+ `HOTKEYS START`/`GET`. `UNLINK` vs `DEL` on a 1M-member set (DEL blocks; UNLINK frees in background).

**macOS specifics.** Docker Desktop on Apple Silicon runs `redis:8.10` natively (arm64). Cluster nodes announce container IPs that the macOS host cannot route to. Either (a) use testcontainers-redis's cluster container, (b) run the cluster test client inside the same Docker network, or (c) configure `cluster-announce-ip`/`cluster-announce-port` with fixed host ports. None of these were tested in this session.

### Gaps
- None of the lab code above has been executed in this session. Thresholds (e.g. "pipeline ≥3× faster", "hot-set survival > X%") need calibrating on a real M-series Mac.
- The testcontainers-redis cluster container API (class name, node count, port mapping on macOS) was not inspected beyond the README's "Standalone and Cluster" claim.
- Exact Jedis exception class names for MOVED/CROSSSLOT/OOM in Jedis 8 were not verified.
- Whether `DEBUG` is disabled in the Docker image (`enable-debug-command` default) was not checked. That is why lab 1 uses an EVAL busy loop instead of `DEBUG SLEEP`.
- Awaitility's current version was not checked.

---

## 5. Proposed lesson outline (11 lessons; 10 if L10 and L11 merge)

### Takeaway
Eleven lessons, each 60 to 120 minutes, each with one or two labs from §4. Model and data first, then patterns that rely on atomicity, then distribution and ops. The arc lets every later lesson reuse the Testcontainers harness built in L1.

### Cited Findings
- The ordering follows the dependency of concepts documented in the cited docs: atomic execution ([Scripting](https://redis.io/docs/latest/develop/programmability/eval-intro/)) underpins locks and limiters ([Distributed locks](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)); Cluster constraints such as same-slot multi-key operations ([Cluster spec](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)) affect how Lua scripts and transactions are designed, so Cluster comes after them.

### Inferences
| # | Lesson | Core content | Labs |
|---|---|---|---|
| 1 | What Redis is and how it executes | In-memory data-structure server; one command thread + I/O threads (8.0 rework); event-loop analogy; RESP2 vs RESP3/HELLO; clients (Jedis 8 RedisClient, Lettuce 7.9 sync/async/coroutines); licensing and Valkey in 10 minutes | Lab 1 (harness + single-thread proof) |
| 2 | Core data types and encodings | Strings, lists, hashes, sets, sorted sets; listpack/intset → hashtable/skiplist thresholds; OBJECT ENCODING, MEMORY USAGE; key naming; Big-O table | Lab 2 (encodings), Lab 3 (leaderboard) |
| 3 | Specialized types and Redis 8 built-ins | Bitmaps, HyperLogLog, geo, streams preview; JSON, Query Engine, time series, Bloom/Cuckoo/CMS/Top-k/t-digest, vector sets (now in core); Array (8.8, preview) mention only | Mini-lab: HLL unique visitors vs SET memory; Bloom filter "username taken" (Redis 8 only) |
| 4 | Expiry, eviction and memory | TTL commands (EXPIRE NX/XX/GT/LT), lazy + active expiry, replicas and expiry, maxmemory, policies (LRU/LFU approximations, LRM 8.6), noeviction default; UNLINK/lazyfree | Lab 4 (eviction) |
| 5 | Caching patterns | Cache-aside, read/write-through, write-behind; TTL jitter; negative caching; stampede (single-flight, lock-and-recompute, early probabilistic refresh); client-side caching with tracking; Spring `@Cacheable` + RedisCacheManager | Lab 5 (cache-aside + single-flight) |
| 6 | Atomicity: transactions, scripts, functions, pipelining | MULTI/EXEC (no rollback), WATCH CAS, Lua EVAL/EVALSHA (cache can vanish), Functions (persisted), pipelining vs transactions vs scripts; Lettuce shared-connection caveat | Lab 6 (WATCH transfer), Lab 7 (pipelining benchmark) |
| 7 | Rate limiting and idempotency | Fixed window (INCR+EXPIRE race → Lua/INCREX), sliding window log (ZSET), sliding window counter, token bucket (Lua), Redisson RRateLimiter; idempotency keys (SET NX EX, state machine, SET IFEQ) | Lab 8 (limiters), Lab 9 (payments idempotency) |
| 8 | Distributed locks, honestly | SET NX PX + token; safe release (Lua, DELEX IFEQ 8.4+); lease expiry vs GC pauses; fencing tokens; Redlock and the Kleppmann/antirez debate; Redisson RLock watchdog / RFencedLock; when to use a DB or etcd/ZooKeeper instead | Lab 10 (lock + unsafe DEL + fencing) |
| 9 | Messaging: pub/sub vs Streams | Pub/sub (at-most-once, sharded pub/sub), keyspace notifications; Streams: XADD/XRANGE/XREADGROUP/XACK/XPENDING/XCLAIM/XAUTOCLAIM, trimming; 8.x additions (XREADGROUP CLAIM, XADD IDMP, XNACK); Kafka comparison | Lab 11 (Streams worker + pub/sub loss test) |
| 10 | Durability and high availability | RDB fork/COW and save points, AOF fsync policies, multi-part AOF, RDB preamble, BACKUP (8.10); replication (async, replid/offset, PSYNC partial vs full, backlog, cascading replicas, WAIT); Sentinel (≥3, quorum, client discovery) | Lab 12 (kill -9 + WAIT), optional Sentinel failover |
| 11 | Redis Cluster and production operations | 16384 slots, CRC16, hash tags, MOVED/ASK, CROSSSLOT, cluster-aware clients, resharding/atomic slot migration (Redis 8.4, Valkey 9.0); latency debugging: SLOWLOG, LATENCY DOCTOR, intrinsic latency, big keys, HOTKEYS (8.6), KEYS vs SCAN, O(N) commands, THP/fork/swap; Redis vs Valkey choice | Lab 13 (cluster MOVED + hash tags), Lab 14 (latency hunt) |

- For a 9-lesson cut: fold L3 into L2 (only HLL + bitmap), and merge L10 into L11 (persistence/replication as theory + kill -9 demo).

### Gaps
- No sourced estimate of per-lesson duration; the 60 to 120 minutes figure is a judgment call.

---

## Verified URLs
All fetched on 2026-11-07 with HTTP 200 unless noted.

**redis.io docs**
- https://redis.io/docs/latest/develop/reference/eviction/
- https://redis.io/docs/latest/commands/expire/
- https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
- https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
- https://redis.io/docs/latest/develop/using-commands/transactions/
- https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
- https://redis.io/docs/latest/develop/reference/client-side-caching/
- https://redis.io/docs/latest/develop/using-commands/pipelining/
- https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/
- https://redis.io/docs/latest/develop/data-types/
- https://redis.io/docs/latest/develop/data-types/sorted-sets/
- https://redis.io/docs/latest/develop/data-types/streams/
- https://redis.io/docs/latest/develop/data-types/arrays/
- https://redis.io/docs/latest/develop/data-types/compare-data-types/
- https://redis.io/docs/latest/develop/pubsub/
- https://redis.io/docs/latest/develop/programmability/functions-intro/
- https://redis.io/docs/latest/develop/programmability/eval-intro/
- https://redis.io/docs/latest/operate/oss_and_stack/management/replication/
- https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/
- https://redis.io/docs/latest/operate/oss_and_stack/management/scaling/
- https://redis.io/docs/latest/develop/reference/protocol-spec/
- https://redis.io/docs/latest/commands/scan/
- https://redis.io/docs/latest/commands/set/
- https://redis.io/docs/latest/commands/delex/
- https://redis.io/docs/latest/commands/increx/
- https://redis.io/docs/latest/commands/hotkeys/
- https://redis.io/docs/latest/commands/xautoclaim/
- https://redis.io/docs/latest/commands/xreadgroup/
- https://redis.io/docs/latest/develop/clients/jedis/transpipe/
- https://redis.io/docs/latest/develop/clients/jedis/connect/

**redis.io legal and blog**
- https://redis.io/legal/licenses/
- https://redis.io/blog/agplv3/
- https://redis.io/blog/redis-8-ga/
- https://redis.io/blog/announcing-redis-86-performance-improvements-streams/
- https://redis.io/blog/announcing-redis-8-8/

**Source and releases.** Release data was fetched through the GitHub REST API (`api.github.com/repos/<repo>/releases[/tags/<tag>]`); the human-readable pages below show the same data.
- https://github.com/redis/redis/releases (tags 8.0.0, 8.2.0, 8.4.0, 8.6.0, 8.8.0, 8.10.0, 8.12-rc1 read via API)
- https://raw.githubusercontent.com/redis/redis/8.10/redis.conf
- https://raw.githubusercontent.com/redis/redis/8.10/src/t_zset.c (fetched raw; human URL https://github.com/redis/redis/blob/8.10/src/t_zset.c)
- https://github.com/valkey-io/valkey/releases (tags 9.0.0, 9.1.0, 9.1.0-rc1 via API)
- https://github.com/redis/jedis/releases (tag v8.0.0 via API); https://raw.githubusercontent.com/redis/jedis/master/README.md
- https://redis.github.io/jedis/migration-guides/v7-to-v8/
- https://github.com/redis/lettuce/releases (tags 7.0.0.RELEASE, 7.9.0.RELEASE, 8.0.0.BETA1 via API); https://raw.githubusercontent.com/redis/lettuce/main/docs/new-features.md
- https://redis.github.io/lettuce/ ; https://redis.github.io/lettuce/user-guide/kotlin-api/ ; https://redis.github.io/lettuce/user-guide/transactions-multi/
- https://github.com/redisson/redisson/releases (via API)
- https://redisson.pro/docs/data-and-services/locks-and-synchronizers/ ; https://redisson.pro/docs/data-and-services/objects/
- https://github.com/spring-projects/spring-data-redis/releases (tag 4.1.0 via API); https://github.com/spring-projects/spring-boot/releases (via API)
- https://docs.spring.io/spring-data/redis/reference/ ; https://docs.spring.io/spring-data/redis/reference/redis/redis-cache.html
- https://raw.githubusercontent.com/redis-field-engineering/testcontainers-redis/main/README.adoc (human: https://github.com/redis-field-engineering/testcontainers-redis)
- https://java.testcontainers.org/ ; https://java.testcontainers.org/quickstart/junit_5_quickstart/
- https://github.com/testcontainers/testcontainers-java/releases (via API)
- Maven Central metadata (repo1.maven.org/maven2/.../maven-metadata.xml) for: org.testcontainers:testcontainers, testcontainers-junit-jupiter, com.redis:testcontainers-redis, redis.clients:jedis, io.lettuce:lettuce-core, org.redisson:redisson, org.springframework.data:spring-data-redis, org.junit.jupiter:junit-jupiter, org.jetbrains.kotlinx:kotlinx-coroutines-reactor, org.springframework.boot:spring-boot. `org.testcontainers:testcontainers-redis` returned no metadata (does not exist).
- https://services.gradle.org/versions/current ; https://github.com/JetBrains/kotlin/releases (via API)
- https://github.com/josiahcarlson/redis-in-action (example code for *Redis in Action*, MIT, includes a `java` folder)

**Valkey and Docker**
- https://valkey.io/ ; https://valkey.io/blog/introducing-valkey-9/
- https://hub.docker.com/_/redis ; https://hub.docker.com/r/valkey/valkey

**Distributed-lock debate**
- https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- https://antirez.com/news/101 (http:// redirects to https://)

**Returned 404 (do not use)**
- https://redis.io/ebook/redis-in-action/ and https://redis.io/resources/redis-in-action/. The free online *Redis in Action* book's current URL could not be found; only the GitHub code repo was verified.
- https://valkey.io/blog/valkey-9-1/ (guessed slug; the homepage links a "What's new in Valkey 9.1" post whose URL I did not capture).
- https://redis.io/docs/latest/commands/bless-set/ (8.12 is still RC; command page not published).

---

## Teaching notes

### Takeaway
Use the event-loop model as the main mental model and come back to it in every lesson. Turn each misconception into a red→green test. Present Redlock as an open, well-argued debate, not a settled verdict. Cut anything that is product marketing or only relevant to one vendor.

### Cited Findings
- Kleppmann's efficiency vs correctness split is the cleanest framing for lock lessons: a lock that is only for efficiency can tolerate occasional double work, while a lock needed for correctness needs fencing ([Kleppmann 2016](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)). antirez's reply shows a random unique token can be used for check-and-set on the resource ([antirez](https://antirez.com/news/101)). Redisson's own deprecation of RedLock supports a practical recommendation ([Redisson locks](https://redisson.pro/docs/data-and-services/locks-and-synchronizers/)).
- The docs' own phrases make good callouts: "Redis does not support rollbacks" ([Transactions](https://redis.io/docs/latest/develop/using-commands/transactions/)); pub/sub messages are "forever lost" ([Pub/Sub](https://redis.io/docs/latest/develop/pubsub/)); "you may lose 1 second of data" ([Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)).

### Inferences
**Analogies that work for senior JVM engineers**
- Redis command thread ≈ a single Netty `EventLoop` or one Kotlin `Dispatchers` single-thread context. A slow command is like blocking the event loop: everything queues behind it. I/O threads ≈ Netty worker threads doing (de)serialization while the "business logic" thread stays single.
- WATCH/MULTI/EXEC ≈ JPA `@Version` optimistic locking: read, compute, write-if-unchanged, retry on conflict.
- Lua script ≈ a stored procedure that runs under a global `synchronized` block. Keep it short or you stall the server.
- Hash slots ≈ Kafka partitions; hash tag ≈ partition key. Cross-slot ops ≈ trying to do one atomic write across two partitions.
- Streams consumer group ≈ Kafka consumer group, but with per-message acks. The PEL plus `XAUTOCLAIM` min-idle-time ≈ SQS visibility timeout and redelivery.
- Pub/sub ≈ radio broadcast; Streams ≈ a log you can replay.
- RDB ≈ periodic snapshot backup; AOF ≈ write-ahead/redo log with tunable fsync, same trade-off as Postgres `synchronous_commit`.
- Fencing token ≈ a version column the storage layer checks. Lock service = lease issuer, storage = enforcer.
- Single-flight ≈ Guava `LoadingCache`/Caffeine `AsyncLoadingCache` coalescing loads in one JVM. Redis only helps across JVMs.

**Misconception handling**
- Open L1 by asking learners to predict whether a concurrent GET waits during a 1.5 s Lua loop. Most seniors who "know Redis is single-threaded" still get the I/O-threads nuance wrong.
- For expiry, never assert exact deletion timing in tests. Assert "invisible to GET after TTL" and "reclaimed eventually" (via `expired_keys`), which is the real contract.
- For Redlock, give learners both articles and ask: "is your lock for efficiency or for correctness?" Then show that fencing needs the protected resource to cooperate, which is the bit people miss.

**What to cut or minimize**
- Redis Query Engine, vector search, FT.HYBRID, JSONPath, time series internals: one demo slide at most. They deserve their own track.
- Redis Enterprise/Cloud features (Active-Active, maintenance events/"hitless upgrades", Entra ID auth): mention only.
- The Array type (8.8, preview) and 8.12 RC features (BLESS, set-member TTL, roaring bitmaps): a sidebar marked "new, may change".
- RESP wire format: one hex-dump demo, no parser lab.
- Implementing Redlock: don't build it. Explain it and point to the debate.
- Sentinel hands-on: optional. Most JVM teams use managed Redis or Cluster; teach the concepts and client discovery only.
- Modules API, RedisGears, redis-om-spring: cut.

**Version hygiene for the writer**
- State "tested with Redis 8.10.3, Valkey 9.1.3, Jedis 8.0.2, Lettuce 7.9.0, Redisson 4.8.0, SDR 4.1.2, Testcontainers 2.0.5, JUnit 6.1.3, Gradle 9.9.0, Kotlin 2.4.21 (as of 2026-11-07)" at the top of the track.
- Expect changes soon: Redis 8.12 GA (RC2 on 2026-11-01), Valkey 9.2 GA (RC2 on 2026-11-04), Lettuce 8.0 GA (beta), Jedis 8.1 (beta), SDR 4.2 / Spring Boot 4.2 (RC). Re-check before publishing.
- Tag every Redis-8-only command in lesson text with its minimum version: SET IFEQ/DELEX/DIGEST/MSETEX/XREADGROUP CLAIM 8.4; XADD IDMP, LRM, HOTKEYS 8.6; INCREX, XNACK, Array 8.8; HIMPORT, LMOVEM, SUNIONCARD, BACKUP 8.10.

### Gaps
- I found no source comparing learner outcomes for different Redis teaching orders. The ordering above is reasoned from concept dependencies, not from evidence.
