# Concept map: lesson ids, where each came from, and its lab module

`NEW` lessons were written for the concept rewrite; the rest moved from the product tracks. The lab module is the toolchain a lesson's lab lives in (labs/<module>/), read from the lesson's lab files.

| New id | Title | Built from | Lab module |
|---|---|---|---|
| found-01 | What a data system is: records, derived data and two kinds of work | NEW | sim |
| found-02 | Latency, percentiles and the tail | NEW | sim |
| found-03 | Faults, failures and the people who run systems | NEW | sim |
| found-04 | Describing load: the home timeline | NEW | sim |
| found-05 | Growing past one machine: shared-nothing, shared-disk and the cloud | NEW | sim |
| found-06 | Systems people can live with: operability, simplicity and change | NEW | sim |
| net-01 | What happens when you curl a URL | net-01 | net |
| net-02 | The link layer: Ethernet, MAC addresses and ARP | net-02 | net |
| net-03 | IP addresses, subnets and NAT | net-03 | net |
| net-04 | Routing, ICMP and traceroute | net-04 | net |
| net-05 | IPv6 for application engineers | net-05 | net |
| net-06 | UDP and the sockets API | net-06 | net |
| net-07 | TCP connections: handshake, states and TIME_WAIT | net-07 | net |
| net-08 | TCP performance: windows, congestion control and Nagle | net-08 | net |
| net-09 | DNS: how a name becomes an address | net-09 | net |
| net-10 | TLS 1.3, certificates and mTLS | net-10 | net |
| net-11 | HTTP/1.1, HTTP/2 and HTTP/3 over QUIC | net-11 | net |
| net-12 | Production networking: load balancers, timeouts, retries and pools | net-12 | net |
| os-01 | What a kernel does: system calls and user mode | os-01 | os |
| os-02 | Processes: fork, exec, wait and signals | os-02 | os |
| os-03 | Threads, and how the JVM maps them to the OS | os-03 | os |
| os-04 | CPU scheduling: EEVDF, nice and CPU quotas | os-04 | os |
| os-05 | Locks at the OS level: futexes and deadlock | os-05 | os |
| os-06 | Virtual memory: page tables, the TLB and page faults | os-06 | os |
| os-07 | Copy-on-write, mmap and the OOM killer | os-07 | os |
| os-08 | Memory allocation: malloc, arenas and why RSS grows | os-08 | os |
| os-09 | The page cache, writeback and fsync | os-09 | os |
| os-10 | File systems: inodes, links and file descriptors | os-10 | os |
| os-11 | I/O models: blocking, epoll and io_uring | os-11 | os |
| os-12 | Containers are processes: namespaces and cgroups | os-12 | os |
| sql-01 | The relational model, keys and NULL | sql-01 | sql |
| sql-02 | Designing a schema: normalization and constraints | sql-02 | sql |
| sql-03 | Joins, including semi and anti joins | sql-03 | sql |
| sql-04 | Aggregation: GROUP BY, FILTER, ROLLUP and GROUPING SETS | sql-04 | sql |
| sql-05 | Subqueries and common table expressions | sql-05 | sql |
| sql-06 | Window functions: ranking, LAG and running totals | sql-07 | sql |
| sql-07 | Window frames and gaps-and-islands | sql-08 | sql |
| sql-08 | LATERAL joins, top-N per group and keyset pagination | sql-09 | sql |
| sql-09 | JSONB, upserts and MERGE | sql-10 | sql |
| sql-10 | SQL from the JVM: JDBC, pools, batching and migrations | sql-14 | sql |
| model-01 | Why other data models exist: Bigtable, Dynamo and the families | nosql-01 | nosql |
| model-02 | Model the access patterns first | nosql-02 | nosql |
| model-03 | Key-value stores and DynamoDB basics | nosql-03 | nosql |
| model-04 | DynamoDB single-table design and transactions | nosql-04 | nosql |
| model-05 | Wide-column stores with Cassandra | nosql-07 | nosql |
| model-06 | Document stores with MongoDB | nosql-08 | nosql |
| model-07 | Recursive CTEs: trees and graphs in SQL | sql-06 | sql |
| model-08 | Graph databases with Neo4j and Cypher | nosql-11 | nosql |
| model-09 | Triples, Datalog and GraphQL | NEW | nosql |
| store-01 | Bytes, pages and durability: a log-structured store | dbi-01 | internals |
| store-02 | Pages, tuples and heap files | dbi-02 | internals |
| store-03 | The buffer pool | dbi-03 | internals |
| store-04 | B+trees | dbi-04 | internals |
| store-05 | LSM trees, SSTables and Bloom filters | dbi-05 | internals |
| store-06 | Write-ahead logging and crash recovery | dbi-06 | internals |
| store-07 | Indexes and reading EXPLAIN | sql-11 | sql |
| store-08 | Indexes for text, time and vectors | nosql-12 | nosql |
| store-09 | Query execution: iterators, joins and vectors | dbi-09 | internals |
| store-10 | Query optimization and cardinality estimates | dbi-10 | internals |
| store-11 | Column stores and compression | dbi-11 | internals |
| store-12 | Materialized views and data cubes | NEW | internals |
| store-13 | Inside Neo4j: native graph storage, memory and clustering | nosql-17 | nosql |
| store-14 | Running PostgreSQL: processes, configuration, roles and connections | sql-15 | sql |
| cache-01 | Why caches work: latency, locality and hit ratios | NEW | redis |
| cache-02 | Inside an in-memory store: how Redis executes commands | redis-01 | redis |
| cache-03 | Core data types and their encodings | redis-02 | redis |
| cache-04 | Bitmaps, HyperLogLog, geo and the Redis 8 built-ins | redis-03 | redis |
| cache-05 | Expiry, eviction and memory | redis-04 | redis |
| cache-06 | Caching patterns and stampedes | redis-05 | redis |
| cache-07 | Keeping a cache honest: invalidation, leases and consistency | NEW | redis |
| cache-08 | Rate limiting and idempotency keys | redis-07 | redis |
| cache-09 | Persistence and replication | redis-10 | redis |
| cache-10 | Redis Cluster and production operations | redis-11 | redis |
| enc-01 | From objects to bytes: JSON, binary formats and serializers | NEW | flow |
| enc-02 | Schemas that evolve: Protobuf, Avro and compatibility | NEW | flow |
| enc-03 | Data outlives code: rolling upgrades and migrations | NEW | flow |
| enc-04 | Calling other services: REST, RPC and gRPC | NEW | flow |
| enc-05 | Durable execution: workflows that survive crashes | NEW | flow |
| repl-01 | One leader, many followers: sync, async and failover | NEW | sim |
| repl-02 | Replication logs: statements, WAL and logical rows | NEW | sim |
| repl-03 | When followers lag: read-your-writes, monotonic reads and consistent prefix | NEW | sim |
| repl-04 | PostgreSQL replication, backups and failover | sql-16 | sql |
| repl-05 | Many leaders: geo-distribution and write conflicts | NEW | sim |
| repl-06 | Local-first software and sync engines | NEW | sim |
| repl-07 | Leaderless replication: quorums, hinted handoff and read repair | nosql-06 | nosql |
| repl-08 | Concurrent writes: last write wins, version vectors and CRDTs | nosql-09 | nosql |
| shard-01 | Splitting data: key ranges, hashes and tenants | NEW | sim |
| shard-02 | Partitioning: consistent hashing and hot keys | nosql-05 | nosql |
| shard-03 | Rebalancing and request routing | NEW | sim |
| shard-04 | Secondary indexes across shards: local and global | NEW | sim |
| shard-05 | Inside a Cassandra cluster: the token ring, gossip and failure detection | nosql-13 | nosql |
| shard-06 | Setting up and running a Cassandra cluster | nosql-14 | nosql |
| shard-07 | Running MongoDB: replica sets, sharding and the balancer | nosql-15 | nosql |
| shard-08 | DynamoDB under the hood: partitions, routers and capacity | nosql-16 | nosql |
| shard-09 | Inside a search cluster: OpenSearch nodes, shards and replicas | nosql-18 | nosql |
| txn-01 | What a transaction promises: ACID and isolation levels | sql-12 | sql |
| txn-02 | Lost updates: row locks, SKIP LOCKED and job queues | sql-13 | sql |
| txn-03 | Write skew and phantoms: when there is no row to lock | NEW | sql |
| txn-04 | MVCC: versions, snapshots and VACUUM | dbi-07 | internals |
| txn-05 | Concurrency control: locks, deadlocks and SSI | dbi-08 | internals |
| txn-06 | Serial execution: Redis MULTI, WATCH and Lua | redis-06 | redis |
| txn-07 | Atomic commit across machines: two-phase commit and XA | NEW | sql |
| txn-08 | Transactions in NoSQL | nosql-10 | nosql |
| dist-01 | Partial failure: networks that lose, delay and duplicate | NEW | sim |
| dist-02 | Detecting failure: timeouts, heartbeats and gray failure | NEW | sim |
| dist-03 | Clocks you can't trust: wall clocks, monotonic clocks and NTP | NEW | sim |
| dist-04 | Process pauses: when your own program stops the world | NEW | sim |
| dist-05 | Leases, locks and fencing tokens | redis-08 | redis |
| dist-06 | Ordering without a shared clock: logical clocks and IDs | NEW | sim |
| dist-07 | System models: crashes, lies, safety and liveness | NEW | sim |
| dist-08 | Testing distributed systems: Jepsen, TLA+ and simulation | NEW | sim |
| cons-01 | Consistency models: what a read may return | NEW | sim |
| cons-02 | Linearizability: one copy, one timeline | NEW | sim |
| cons-03 | Total order broadcast and the many faces of consensus | NEW | sim |
| cons-04 | Consensus with Raft | dbi-12 | internals |
| cons-05 | Coordination services: ZooKeeper, etcd and KRaft | NEW | sim |
| cons-06 | Distributed SQL: Spanner, CockroachDB and Aurora DSQL | NEW | sim |
| msg-01 | Queues and brokers: acknowledgements, redelivery and fan-out | NEW | kafka |
| msg-02 | The log: Kafka's one big idea | kafka-01 | kafka |
| msg-03 | Partitions and segments on disk: retention and compaction | kafka-02 | kafka |
| msg-04 | The cluster: KRaft, replicas and the ISR | kafka-03 | kafka |
| msg-05 | Producers I: keys, partitions and ordering | kafka-04 | kafka |
| msg-06 | Producers II: batching, acks and idempotence | kafka-05 | kafka |
| msg-07 | Consumers: the poll loop, offsets and delivery guarantees | kafka-06 | kafka |
| msg-08 | Consumer groups and rebalancing | kafka-07 | kafka |
| msg-09 | Failure handling: poison pills, retries and dead letters | kafka-08 | kafka |
| msg-10 | Transactions and exactly-once | kafka-09 | kafka |
| msg-11 | Share groups and running Kafka in production | kafka-12 | kafka |
| msg-12 | A lighter log: Redis pub/sub and Streams | redis-09 | redis |
| stream-01 | Two systems, one truth: dual writes and change data capture | NEW | sql |
| stream-02 | Schemas, Connect and change data capture | kafka-11 | kafka |
| stream-03 | Event sourcing and CQRS: the log as the source of truth | NEW | kafka |
| stream-04 | Time in streams: event time, windows and watermarks | NEW | sim |
| stream-05 | Kafka Streams: tables, state and windows | kafka-10 | kafka |
| stream-06 | Stream joins and complex event processing | NEW | kafka |
| stream-07 | Fault tolerance in stream processing: checkpoints and exactly-once | NEW | sim |
| stream-08 | Streaming in Spark: Structured Streaming and watermarks | data-11 | bigdata |
| batch-01 | Why big data systems exist, and when you don't need one | data-01 | bigdata |
| batch-02 | Batch on one machine: pipes, sorting and hashing | NEW | sim |
| batch-03 | HDFS and MapReduce: the ideas that survived | data-02 | bigdata |
| batch-04 | Hive: SQL on files, partitions and the metastore | data-03 | bigdata |
| batch-05 | Columnar files: Parquet internals and pushdown | data-04 | bigdata |
| batch-06 | The Spark execution model | data-05 | bigdata |
| batch-07 | The shuffle, partitioning and joins | data-06 | bigdata |
| batch-08 | The optimizer, AQE, skew and caching | data-07 | bigdata |
| batch-09 | Spark 4 for JVM engineers: Connect, ANSI and VARIANT | data-08 | bigdata |
| batch-10 | Warehouses and dimensional models: OLAP and star schemas | NEW | bigdata |
| batch-11 | Lakehouse tables with Apache Iceberg | data-09 | bigdata |
| batch-12 | Row-level changes, compaction and catalogs | data-10 | bigdata |
| batch-13 | Orchestrating batch work: DAGs, retries and backfills | NEW | sim |
| batch-14 | What batch output is for: ETL, ML features and serving data | NEW | sim |
| batch-15 | Choosing an engine: DuckDB, Spark, Trino and friends | data-12 | bigdata |
| derive-01 | Data integration: systems of record, lambda and kappa | NEW | sim |
| derive-02 | Unbundling the database: dataflow apps and streaming databases | NEW | sim |
| derive-03 | The end-to-end argument: idempotence from client to storage | NEW | sim |
| derive-04 | Constraints without coordination: timeliness and integrity | NEW | sim |
| derive-05 | Trust, but verify: audits, checksums and silent corruption | NEW | sim |
| derive-06 | Doing the right thing: bias, privacy, consent and the law | NEW | sim |
