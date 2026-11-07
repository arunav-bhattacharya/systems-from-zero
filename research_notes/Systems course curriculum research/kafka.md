# Apache Kafka for Java/Kotlin engineers: research notes for a 10-12 lesson track (state as of 2026-11-07)

Research date: 2026-11-07. All "verified" facts below come from pages fetched on that date. Things recalled from background knowledge but not re-checked are kept out of Cited Findings and appear in Inferences (marked "unverified") or Gaps.

---

## 1. Teaching order and scope: canonical concepts

### Takeaway
Teach from the log outward: log, offsets, segments, retention and compaction, then the cluster (KRaft, replication, ISR/HW/min ISR/ELR), then the producer, the consumer, rebalancing, failure handling, transactions, Streams, schemas/Connect/CDC, and last share groups and operations. Several "classic" defaults changed in 4.x and have to be taught as they stand now: linger.ms is 5, ZooKeeper is gone, the KIP-848 protocol is GA but the client still defaults to `group.protocol=classic`, share groups have been production-ready since 4.2, and ELR is on by default for new clusters since 4.1.

### Cited Findings

**The log abstraction (lesson 1)**
- Jay Kreps' essay "The Log: What every software engineer should know about real-time data's unifying abstraction" appeared on the LinkedIn Engineering blog on Dec 16, 2013. It defines a log as an append-only, totally ordered sequence of records ordered by time, and argues that deterministic consumers of the same log end up in the same state. — [LinkedIn Engineering (search result; direct fetch returned 404)](https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying)
- The consumer position is "just a single integer, the offset of the next message to consume" per partition. That makes acknowledgment cheap and lets consumers rewind and reprocess. — [Kafka 4.4 design doc](https://kafka.apache.org/44/design/design/)
- Kafka relies on the OS page cache rather than an in-JVM cache. The design doc cites about 600 MB/s for linear disk writes against about 100 kB/s for random writes. Appends and reads are O(1). Zero-copy `sendfile` moves data from page cache to the NIC, but it is not used when SSL is enabled. — [Kafka 4.4 design doc](https://kafka.apache.org/44/design/design/)

**Topics, partitions, segments, index files, retention, compaction (lesson 2)**
- Topic config defaults (4.4): `cleanup.policy=delete`, `retention.ms=604800000` (7 d), `retention.bytes=-1`, `segment.bytes=1073741824` (1 GiB), `segment.ms=604800000` (7 d), `segment.index.bytes=10485760` (10 MiB), `index.interval.bytes=4096`, `min.insync.replicas=1`, `unclean.leader.election.enable=false`, `delete.retention.ms=86400000` (1 d), `min.compaction.lag.ms=0`, `max.compaction.lag.ms=Long.MAX`, `min.cleanable.dirty.ratio=0.5`, `message.timestamp.type=CreateTime`, `compression.type=producer`, `max.message.bytes=1048588`, `remote.storage.enable=false`, `local.retention.ms/bytes=-2` (meaning "use retention.ms/bytes"). — [Kafka 4.4 topic configs](https://kafka.apache.org/44/configuration/topic-configs/)
- The `segment.bytes` doc says retention and cleaning are "always done a file at a time", so whole segments are deleted, never single messages. — [Kafka 4.4 topic configs](https://kafka.apache.org/44/configuration/topic-configs/)
- Compaction guarantees that Kafka "will always retain at least the last known value for each message key" per partition. A record with a key and null value is a tombstone and is removed after `delete.retention.ms`, so a consumer lagging beyond that window can miss deletes. The active segment is never compacted. Offsets never change and order is preserved. `max.compaction.lag.ms` is a non-binding deadline. — [Kafka 4.4 design doc](https://kafka.apache.org/44/design/design/)
- Kafka 4.0 raised the minimum `segment.bytes` from 14 bytes to 1 MB. That matters for labs that shrink segments to demo retention. — [Kafka 4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- Tiered storage (KIP-405) became "production-ready in Kafka 3.9". 3.9 also added per-topic dynamic disabling of tiered storage (KIP-950). The source says "production-ready", not "GA". — [Kafka 3.9.0 announcement](https://kafka.apache.org/blog/2024/11/06/apache-kafka-3.9.0-release-announcement/)
- Tiered storage additions in 4.x: KIP-1023 `follower.fetch.last.tiered.offset.enable` (default false) and KIP-1235 `remote.log.metadata.topic.min.isr` in 4.3, then KIP-1241 `remote.copy.lag.bytes` / `remote.copy.lag.ms` (delayed upload) in 4.4. — [4.3.0 announcement](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/); [4.4.0 announcement](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/)

**Brokers, KRaft, replication (lesson 3)**
- Kafka 4.0 (Mar 18, 2025) is "the first major release to operate entirely without Apache ZooKeeper", with KRaft as the only mode. — [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/)
- 3.9 was "the final major release to feature the deprecated Apache ZooKeeper mode". KIP-853 (3.9) made KRaft quorum membership dynamic, with the limitation that static quorums couldn't be converted to dynamic ones in 3.9. — [3.9.0 announcement](https://kafka.apache.org/blog/2024/11/06/apache-kafka-3.9.0-release-announcement/)
- 4.4 adds controller unregistration (KIP-1312) through `kafka-cluster.sh unregister-controller` and a `--unregister` flag on `kafka-metadata-quorum.sh remove-controller`. It also deprecates the `broker.id` config (KIP-1232). — [4.4.0 announcement](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/); [Confluent 4.4 blog (search result)](https://www.confluent.io/blog/introducing-apache-kafka-4-4-0/)
- ISR: the leader tracks in-sync replicas. Followers that fail to catch up to the log end within `replica.lag.time.max.ms` are dropped. A message is committed once all ISR members have it, and only committed messages reach consumers. `acks=all` waits for the current ISR, not the full replica set. `min.insync.replicas` adds a durability floor and only applies with `acks=all`. Since 0.11 Kafka by default waits for a consistent replica instead of electing an unclean one. — [Kafka 4.4 design doc](https://kafka.apache.org/44/design/design/)
- Eligible Leader Replicas (KIP-966 part 1) has been available since 4.0. Under "strict min ISR" the high watermark can't advance while ISR < `min.insync.replicas`. ELR records replicas outside the ISR that are still safe to lead. Election order is ISR, then unfenced ELR member, then last known leader if unfenced. ELR "is enabled by default on new clusters starting 4.1". On 4.0 you enable it with `eligible.leader.replicas.version=1` (0 downgrades). Once enabled, `min.insync.replicas` must be set at cluster level and can't be set at broker level, and changing it clears ELR state. ELR fields show up only via the DescribeTopicPartitions API. — [Kafka 4.4 ELR doc](https://kafka.apache.org/44/operations/eligible-leader-replicas/)
- KIP-966 fixes the "Last Replica Standing" problem. With it, `min.insync.replicas` effectively becomes "the minimum replication factor of committed log records", barring broker failures. Jack Vanlightly verified it formally in TLA+. — [Vanlightly kafka-tlaplus KIP-966 description](https://github.com/Vanlightly/kafka-tlaplus/blob/main/kafka_data_replication/kraft/kip-966/description/0_kafka_replication_protocol.md)

**Producer (lessons 4-5)**
- Producer defaults (4.4): `acks=all`, `enable.idempotence=true`, `linger.ms=5`, `batch.size=16384`, `compression.type=none`, `delivery.timeout.ms=120000`, `request.timeout.ms=30000`, `max.in.flight.requests.per.connection=5`, `retries=2147483647`, `retry.backoff.ms=100` (exponential up to `retry.backoff.max.ms`), `partitioner.class=null`, `partitioner.ignore.keys=false`, `partitioner.adaptive.partitioning.enable=true`, `transaction.timeout.ms=60000`, `buffer.memory=33554432`, `max.block.ms=60000`. — [Kafka 4.4 producer configs](https://kafka.apache.org/44/configuration/producer-configs/)
- Idempotence "is enabled by default if no conflicting configurations are set". It requires `retries>0`, `acks=all`, `max.in.flight<=5`. With conflicting configs it is silently disabled, unless you set it explicitly, in which case you get a `ConfigException`. `linger.ms` "changed from 0 to 5 in Apache Kafka 4.0". — [Kafka 4.4 producer configs](https://kafka.apache.org/44/configuration/producer-configs/)
- The KafkaProducer javadoc says `enable.idempotence` defaults to true from Kafka 3.0. Setting `transactional.id` implies idempotence. Transactional topics should use RF>=3 and `min.insync.replicas=2`. The producer "is thread safe" and sharing one instance across threads "will generally be faster". — [KafkaProducer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)
- Idempotent producer: "guarantees that resending will not result in duplicate entries in the log". The broker dedupes on producer ID plus sequence number. — [Kafka 4.4 design doc](https://kafka.apache.org/44/design/design/)
- Sticky partitioning (KIP-794, which replaced KIP-480's sticky partitioner): KIP-480's version wasn't uniform because slower brokers drained batches more slowly and got more records, a runaway effect. The new default switches partitions after `batch.size` bytes, adaptively avoids partitions with long queues, and adds `partitioner.ignore.keys`, `partitioner.adaptive.partitioning.enable` and `partitioner.availability.timeout.ms` (default 0). `DefaultPartitioner`, `UniformStickyPartitioner` and `Partitioner.onNewBatch` are deprecated. Keyed records are unaffected. — [KIP-794](https://cwiki.apache.org/confluence/display/KAFKA/KIP-794%3A+Strictly+Uniform+Sticky+Partitioner)

**Consumer, groups, commits (lessons 6-7)**
- Consumer defaults (4.4): `group.protocol=classic` (or `consumer`), `partition.assignment.strategy=[RangeAssignor, CooperativeStickyAssignor]`, `enable.auto.commit=true`, `auto.commit.interval.ms=5000`, `auto.offset.reset=latest` (also `earliest`, `none`, `by_duration:<ISO-8601>`), `max.poll.interval.ms=300000`, `max.poll.records=500`, `session.timeout.ms=45000`, `heartbeat.interval.ms=3000`, `isolation.level=read_uncommitted`, `fetch.min.bytes=1`, `fetch.max.wait.ms=500`. With `group.protocol=consumer`, `session.timeout.ms` and `heartbeat.interval.ms` are not supported; the broker's `group.consumer.*` settings control them instead. `group.remote.assignor` selects the server-side assignor. — [Kafka 4.4 consumer configs](https://kafka.apache.org/44/configuration/consumer-configs/)
- Group-level (dynamic) config defaults: `consumer.session.timeout.ms=45000`, `consumer.heartbeat.interval.ms=5000`, `consumer.assignment.interval.ms=1000`. — [Kafka 4.4 group configs](https://kafka.apache.org/44/configuration/group-configs/)
- KafkaConsumer "is NOT thread-safe". `wakeup()` is the only method safe to call from another thread, and it makes the blocked call throw `WakeupException`. Recommended models are one consumer per thread, or a consumer thread handing records to a worker pool, which makes ordering and commits harder. — [KafkaConsumer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)
- Manual commit after a DB insert gives at-least-once, since a crash between insert and commit causes a repeat. Auto-commit is at-least-once only if every record from a poll is consumed before the next poll or `close()`; otherwise records can be lost. "The committed offset should always be the offset of the next message that your application will read." — [KafkaConsumer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)
- If `poll` isn't called within `max.poll.interval.ms`, the client "will proactively leave the group", and a later `commitSync()` may throw `CommitFailedException`. The fixes are a higher `max.poll.interval.ms` or a lower `max.poll.records`. `ConsumerRebalanceListener.onPartitionsRevoked`/`onPartitionsAssigned` run only inside `poll`. — [KafkaConsumer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)
- With `read_committed`, the end offset is the Last Stable Offset (LSO), and lag metrics are measured against the LSO. Transaction markers and aborted records take up offsets but are never returned, so consumed offsets can have gaps. — [KafkaConsumer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)
- `subscribe(SubscriptionPattern)` (RE2/J regex evaluated broker-side) works only under the CONSUMER protocol. — [KafkaConsumer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)
- KIP-848 GA in 4.0: enabled by default on the server, but consumers opt in with `group.protocol=consumer`. — [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/). After groups use it, the cluster can only be downgraded to 3.4.1+. — [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- KIP-848 design: the classic protocol "relies on a group-wide synchronization barrier", with thick clients and fake rebalances. The new protocol uses a `ConsumerGroupHeartbeat` API and server-side assignors (`uniform`, `range`, both sticky). It tracks a group epoch, an assignment epoch and member epochs (stale members get `FENCED_MEMBER_EPOCH`). Members revoke first and are then assigned, and unaffected members are untouched. Regex runs on the server with RE2/J. Offsets use topic IDs (4.2). Migration from classic is an online rolling upgrade. Client-side assignors are still not implemented. — [KIP-848](https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+of+the+Consumer+Rebalance+Protocol)
- Classic deprecation path: 4.3 (KIP-1274) makes classic-protocol consumers log a recommendation to switch, and the classic protocol "will be deprecated in a future release". KIP-1237 deprecates broker `group.coordinator.rebalance.protocols` (removed in 5.0, when all protocols are always enabled and gated by feature versions). — [4.3.0 announcement](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/); [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- Delivery semantics: at-least-once is Kafka's default. At-most-once means disabling producer retries and committing before processing. Exactly-once is supported within Kafka Streams and via transactional producers plus `read_committed` consumers. — [Kafka 4.4 design doc](https://kafka.apache.org/44/design/design/)

**Transactions and EOS (lesson 9)**
- Transaction API (4.4): `initTransactions()`, `beginTransaction()`, `sendOffsetsToTransaction(Map<TopicPartition,OffsetAndMetadata>, ConsumerGroupMetadata)`, `commitTransaction()`, `abortTransaction()`. The javadoc pattern: on `ProducerFencedException`, `OutOfOrderSequenceException` or `AuthorizationException`, close the producer. On any other `KafkaException`, call `abortTransaction()` and retry. Offsets sent in a transaction count only if it commits. Pass `consumer.groupMetadata()` for fencing. The consumer must use `enable.auto.commit=false` and must not commit manually. — [KafkaProducer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)
- KIP-890 (Transactions Server-Side Defense) targets hanging transactions, where a stuck LSO stalls read_committed consumers and blocks compaction, and zombie or late writes landing in the wrong transaction. Part 1 is broker-side verification for old clients. Part 2 bumps the producer epoch on every commit/abort and adds partitions implicitly, gated by a transaction feature version (v2 = part 2). — [KIP-890](https://cwiki.apache.org/confluence/display/KAFKA/KIP-890%3A+Transactions+Server-Side+Defense)
- 4.0 finished KIP-890's second phase. The new protocol is enabled when the 4.0 upgrade is finalized, and 4.0 producers bump the epoch on every transaction. Apps should abort on both `TimeoutException` and `TransactionAbortableException`. — [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/); [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- KIP-939 (2PC participation for dual writes and Flink) is "Accepted". It would add `transaction.two.phase.commit.enable` (client and broker), `initTransactions(boolean keepPreparedTxn)`, `prepareTransaction()`, `completeTransaction(PreparedTxnState)`, a `TWO_PHASE_COMMIT` ACL, and requires `transaction.version` 3. — [KIP-939](https://cwiki.apache.org/confluence/display/KAFKA/KIP-939%3A+Support+Participation+in+2PC)
- **KIP-939 has not shipped to users.** Commit KAFKA-19414 (#21159, Dec 16, 2025) removed the 2PC public APIs from the 4.2 branch "until KIP-939 is ready to use". A June 2025 commit had done the same on 4.1. — [commits@kafka mail archive](https://www.mail-archive.com/commits@kafka.apache.org/msg31756.html); [search result for 4.1 removal](https://mail-archive.com/commits@kafka.apache.org/msg30357.html). The 4.4 KafkaProducer javadoc lists only the no-argument `initTransactions()` and no `prepareTransaction`/`completeTransaction`. — [KafkaProducer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)
- Jepsen (Nov 12, 2024, in the Bufstream analysis) found aborted reads, lost writes and torn transactions in Kafka's own transaction protocol (KAFKA-17754). The cause was `EndTxn` carrying no sequence number, so a delayed commit or abort could apply to a later transaction. Jepsen also found that consumers don't reliably rewind after an aborted transaction (KAFKA-17582), that `Consumer.close()` can block indefinitely (KAFKA-17734), and that transaction semantics are underdocumented (KAFKA-17671). Kafka engineers expected KIP-890 to fix KAFKA-17754. — [Jepsen Bufstream 0.1.0](https://jepsen.io/analyses/bufstream-0.1.0)
- KAFKA-17754 now shows "Resolved / Fixed" (resolved 12 Aug 2026, awaiting reporter verification), with no Fix Version listed. It is marked duplicated by KAFKA-20547 ("Streams produces duplicates with EOS_v2"). — [KAFKA-17754](https://issues.apache.org/jira/browse/KAFKA-17754)
- 4.2 added KIP-1228 (TransactionVersion field in WriteTxnMarkersRequest for stricter epoch validation). 4.4 added KIP-1319 (`TxnOffsetCommit` v6, topic IDs). — [4.2.0 announcement](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/); [4.4.0 announcement](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/)

**Share groups / Queues for Kafka (lesson 12)**
- Status timeline for KIP-932: early access in 4.0 → [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/). Preview in 4.1, "still not ready for production" and enabled by upgrading `share.version` to 1 → [4.1.0 announcement](https://kafka.apache.org/blog/2025/09/04/apache-kafka-4.1.0-release-announcement/), [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/). "Production-ready in Apache Kafka 4.2", with RENEW ack (KIP-1222) → [4.2.0 announcement](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/). Clusters with fewer than 3 brokers must lower the share coordinator state topic's RF and min ISR to 1 → [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/). 4.3 added KIP-1240 configs → [4.3.0 announcement](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/). 4.4 added share-group DLQs (KIP-1191), active when `share.version` is upgraded to 2, plus KIP-1323 (initialize share-group offsets from a file or a consumer group's committed offsets) → [4.4.0 announcement](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/). Confluent says the DLQ feature "may change in a minor release" → [Confluent 4.4 blog (search result)](https://www.confluent.io/blog/introducing-apache-kafka-4-4-0/).
- `KafkaShareConsumer` semantics: many consumers cooperatively read the same partitions and each record goes to one member, giving up ordering across members. Records are acquired under a time-limited lock (default 30 s), and an expired lock makes the record available again. `share.acknowledgement.mode` is `implicit` by default (the next poll or commit accepts everything) or `explicit` (every record must be acknowledged before the next poll, otherwise `IllegalStateException`). `AcknowledgeType` is ACCEPT, RELEASE (retry, for transient errors), REJECT (permanent, no redelivery) or RENEW (extend the lock; explicit mode only). Acks are local until `commitSync`/`commitAsync`/next poll. Within one `ConsumerRecords`, records of a partition come in increasing offset order. — [KafkaShareConsumer 4.4 javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html)
- Share group config defaults: `share.delivery.count.limit=5` (min 2), `share.record.lock.duration.ms=30000` (min 1000), `share.auto.offset.reset=latest`, `share.isolation.level=read_uncommitted` (read_committed allowed), `share.partition.max.record.locks=2000`, `share.renew.acknowledge.enable=true`, `share.session.timeout.ms=45000`, `share.heartbeat.interval.ms=5000`. DLQ: `errors.deadletterqueue.topic.name=""`, `errors.deadletterqueue.copy.record.enable=false`. — [Kafka 4.4 group configs](https://kafka.apache.org/44/configuration/group-configs/)

**Kafka Streams (lesson 10)**
- `processing.guarantee` is `at_least_once` (default) or `exactly_once_v2`. `exactly_once` is listed only as deprecated. `commit.interval.ms` is 30 s, dropping to 100 ms under EOS. `num.standby.replicas=0` (1 recommended). `state.dir=${java.io.tmpdir}/kafka-streams`. Internal `replication.factor=-1` (broker default; 3 recommended). `statestore.cache.max.bytes=10 MiB`. `default.dsl.store` (default ROCKS_DB) is deprecated in favor of `dsl.store.suppliers.class`. EOS needs 3 brokers by default; for dev, lower `transaction.state.log.replication.factor` and `transaction.state.log.min.isr`. Streams `group.protocol` defaults to `classic`, and `streams` needs broker enablement. Static membership with `streams` needs 4.4 clients and brokers. — [Kafka 4.4 Streams config](https://kafka.apache.org/44/streams/developer-guide/config-streams/)
- KIP-1071 Streams rebalance protocol: early access in 4.1 ("not for production"), production-ready for its core feature set in 4.2 (migration bug KAFKA-20254 fixed in 4.2.1), static membership in 4.4. — [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- 4.2 added Streams DLQ support in exception handlers (KIP-1034). 4.3 added `state.cleanup.dir.max.age.ms` (KIP-1259), headers in state stores (KIP-1271/1285), and deprecated `streams-scala` (KIP-1244, removed in 5.0). 4.4 deprecated the `ValueJoinerWithKey` KStream-GlobalKTable join overloads (KIP-1340) and the `StreamPartitioner` method without headers (KIP-1321). — [4.2.0](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/); [4.3.0](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/); [4.4.0](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/)
- TopologyTestDriver: artifact `org.apache.kafka:kafka-streams-test-utils:4.4.0` (test scope). API: `new TopologyTestDriver(topology[, props])`, `createInputTopic(name, keySer, valSer)`, `pipeInput(k, v)`, `createOutputTopic(name, keyDe, valDe)`, `readKeyValue()`, `isEmpty()`, `advanceWallClockTime(Duration)`, `getKeyValueStore("store-name")`, `close()`. — [Kafka 4.4 Streams testing](https://kafka.apache.org/44/streams/developer-guide/testing/)

**Schema Registry, Connect, CDC (lesson 11)**
- Schema Registry compatibility: BACKWARD is the default and is non-transitive. BACKWARD/BACKWARD_TRANSITIVE allow adding optional fields and removing fields that are optional or have defaults; upgrade consumers first. FORWARD/FORWARD_TRANSITIVE allow adding fields and removing optional ones; upgrade producers first. FULL/FULL_TRANSITIVE allow only adding or removing optional fields, in any upgrade order. NONE does no checks. The TRANSITIVE variants check all previous versions, the others only the last. For Protobuf, BACKWARD_TRANSITIVE is best practice, and adding new message types isn't forward compatible. For JSON Schema, the rules depend on `compatibilityPolicy` (LENIENT/STRICT) and on whether the content model is open or closed. Doc version: CP 8.4. — [Confluent schema evolution](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- Connect 4.4: KIP-1209 `internal.topics.automatic.creation.enable` (default true) and a new `connect-internal-topics.sh`. 4.3 added the `ConnectPlugin` interface (KIP-1273). 4.2 added external schema support in JsonConverter and an allowlist connector client config override policy. — [4.4.0](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/); [4.3.0](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/); [4.2 search summary](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/)
- Debezium: latest stable series is 3.7 (3.7.1.Final), and 3.8.0.Alpha1 is in development. It is tested with Kafka Connect 3.1+. Connectors need Java 17+; Debezium Server, Operator, Outbox and the Quarkus extension need Java 21+. The page's date for the 3.7 series (Nov 6, 2026) looks inconsistent with the 3.8 alpha date. — [Debezium releases](https://debezium.io/releases/)

**Partition sizing (lesson 12)**
- Jun Rao's (Confluent, 2015-era, ZooKeeper-based) guidance: size by target throughput, measured rather than formula-based, and over-partition for 1-2 years of growth, because adding partitions later breaks key-to-partition mapping. Costs of too many partitions are latency (rule of thumb: at most 100 x brokers x RF partitions per broker for latency-sensitive workloads), recovery time, file handles, and producer memory (tens of KB per partition). — [Confluent blog (search result)](https://www.confluent.io/blog/how-choose-number-topics-partitions-kafka-cluster/)
- 4.3 added metrics showing how much of the max retention each partition uses (KIP-1257) and `cordoned.log.dirs` (KIP-1066). — [4.3.0 announcement](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/)

**Framework choice and Kotlin (lessons 6, 8, 12)**
- Spring for Apache Kafka 4.1 (what's-new for 4.1.2): share consumers via `ShareKafkaMessageListenerContainer` with `ShareAckMode` (EXPLICIT/MANUAL/IMPLICIT), `ShareAcknowledgment.renew()` (KIP-1222), `ShareConsumerRecordRecoverer` (default REJECTING), and `syncShareCommits` (default true). Also Streams DLQ handlers (KIP-1034), `StreamsBuilderFactoryBean.groupProtocol` (classic/streams, KIP-1071), a per-listener `@KafkaListener(ackMode=...)`, and the `RetryTopicConfigurationBuilder` default `sameIntervalTopicReuseStrategy` changed to SINGLE_TOPIC. — [Spring Kafka what's new](https://docs.spring.io/spring-kafka/reference/whats-new.html)
- Spring Kafka 4.1.2's POM depends on kafka-clients/kafka-streams **4.2.2** and Spring Framework 7.0.10, with an optional `kotlinx-coroutines-reactor` 1.10.2. — [spring-kafka-4.1.2.pom](https://repo1.maven.org/maven2/org/springframework/kafka/spring-kafka/4.1.2/spring-kafka-4.1.2.pom)
- Quarkus (guide for 3.40, "latest"): the `quarkus-messaging-kafka` extension bundles kafka-clients 4.1.1. It offers `@Incoming`/`@Outgoing`/`@Channel`/`Emitter`, `@Blocking` for blocking work, commit strategies `throttled` (default unless auto-commit), `latest`, `checkpoint` (experimental) and `ignore`, and failure strategies `fail` (default), `ignore`, `dead-letter-queue` and `delayed-retry-topic`. — [Quarkus Kafka guide](https://quarkus.io/guides/kafka)

### Inferences
- Teaching order: log, storage, cluster/replication, producer (two lessons), consumer, rebalancing, failure handling/DLT, transactions, Streams, schemas/Connect/CDC, share groups plus operations. Each step only needs what came before. Replication goes before the producer so that `acks` and `min.insync.replicas` mean something when the producer lesson reaches them.
- Teach KIP-848 as the target state: set `group.protocol=consumer` explicitly in every lab. The client default is still `classic` in 4.4 and that will surprise learners. Show classic only once, as a contrast in the rebalance lab.
- Teach `acks=all` + idempotence as defaults the learner inherits for free, then show what disables idempotence silently: for example `acks=1` without an explicit `enable.idempotence`.
- Index files: segments appear on disk as `<baseOffset>.log`, `.index` (offset index) and `.timeindex` (time index), with `index.interval.bytes` controlling index density. File extensions are background knowledge (unverified this session) and are easy to confirm in Lab 1 with `ls` inside the container. `kafka-dump-log.sh` for inspecting segments is likewise unverified but standard.
- Payments angle: ordering is per partition, so key by account ID. Idempotent producer dedupes only producer retries within one producer session. Business-level dedupe (idempotency key stored with the side effect in one DB transaction) stays the consumer's job. This follows from the design doc and KafkaConsumer javadoc above.
- Kotlin coroutines: because KafkaConsumer isn't thread-safe and `wakeup()` is the only cross-thread method, confine the consumer to one dedicated thread (e.g. `Executors.newSingleThreadExecutor().asCoroutineDispatcher()`), run the blocking poll loop there, expose records as a `Flow`, and call `consumer.wakeup()` from the cancellation path. The producer is thread-safe and can be shared; bridge `send()`'s callback into `suspendCancellableCoroutine`. This idiom is derived from the javadoc and not from an official Kotlin guide.
- Spring Kafka 4.1.2 pins kafka-clients 4.2.2 and Quarkus 3.40 bundles 4.1.1. In a multi-module Gradle build mixing plain-client modules on 4.4.0 with a Spring module, align versions with a platform/BOM or keep the Spring module on its managed version. Mixed client versions against a 4.4 broker are fine per KIP-896 (clients and brokers must be 2.1+).

### Gaps
- No official Kafka 4.4 operations page for share groups was found (`/44/operations/share-groups/` returned 404). The exact enablement steps on a fresh 4.4 cluster (is `share.version` enabled by default on new 4.2+ clusters?) and the exact broker config names for the share-coordinator state topic RF/min-ISR are unverified. Background recollection, unverified: `share.coordinator.state.topic.replication.factor` / `share.coordinator.state.topic.min.isr`, and `kafka-features.sh --bootstrap-server ... upgrade --feature share.version=1`.
- The KIP number behind the 4.0 default changes (linger.ms 0→5 etc.) is believed to be KIP-1030 but wasn't verified.
- No authoritative Kotlin-coroutines Kafka guide was fetched. Whether Spring Kafka 4.1 supports `suspend fun` `@KafkaListener` methods directly wasn't confirmed; only the optional coroutines-reactor dependency in the POM was.
- Quarkus Dev Services' default Kafka image (Redpanda vs apache/kafka-native) wasn't confirmed (page truncated).
- Apache Kafka ships the tiered-storage framework, but whether it includes a production RemoteStorageManager plugin (vs third-party plugins) wasn't verified this session.

---

## 2. Current versions as of November 2026

### Takeaway
Apache Kafka 4.4.0 (Oct 22, 2026) is the newest release. Supported lines are 4.4.0, 4.3.2 and 4.2.2. Clients need Java 11+, brokers/Connect/tools Java 17+, and Java 25 has been supported since 4.2. For the labs, pin `apache/kafka:4.4.0` / `apache/kafka-native:4.4.0` (arm64 available; the `latest` tag lags), Testcontainers 2.0.5 (`testcontainers-kafka`, class `org.testcontainers.kafka.KafkaContainer`), `confluentinc/cp-schema-registry:8.4.0` (CP 8.4 = Kafka 4.4), JUnit 6.1.3, and Gradle 9.9.0. Spring Kafka stable is 4.1.2, built on kafka-clients 4.2.2; 4.2.0-RC1 is out.

### Cited Findings
- Release table from the official downloads page:

| Version | Date | Status |
|---|---|---|
| 4.4.0 | Oct 22, 2026 | Supported |
| 4.3.2 | Oct 23, 2026 | Supported |
| 4.3.1 | Jun 25, 2026 | Archived |
| 4.3.0 | May 22, 2026 | Archived |
| 4.2.2 | Sep 29, 2026 | Supported |
| 4.2.1 | May 30, 2026 | Archived |
| 4.2.0 | Feb 17, 2026 | Archived |
| 4.1.2 | Mar 17, 2026 | Archived |
| 4.1.1 | Nov 12, 2025 | Archived |
| 4.1.0 | Sep 2, 2025 | Archived |
| 4.0.2 | Mar 16, 2026 | Archived |
| 4.0.1 | Oct 13, 2025 | Archived |
| 4.0.0 | Mar 18, 2025 | Archived |
| 3.9.2 | Feb 21, 2026 | Archived |

All 4.x binaries are Scala 2.13 only. "Bugfix releases are made as needed for supported releases only." — [Kafka downloads](https://kafka.apache.org/community/downloads/)
- Date discrepancies: the 4.1.0 blog post is dated Sep 4, 2025 while the downloads page says Sep 2. Search also surfaced a 4.2.0 announcement URL dated 2026-01-14, but the canonical post and the downloads page say Feb 17, 2026. — [4.1.0 blog](https://kafka.apache.org/blog/2025/09/04/apache-kafka-4.1.0-release-announcement/); [4.2.0 blog](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/)
- Docs root `/documentation/` redirects, and the release menu lists 4.4 first, at `/44/`. — [kafka.apache.org/documentation](https://kafka.apache.org/documentation/)
- Maven Central `org.apache.kafka:kafka-clients`: latest/release = **4.4.0**; versions include 4.1.0-4.1.2, 4.2.0-4.2.2, 4.3.0-4.3.2, 4.4.0. — [maven-metadata.xml](https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/maven-metadata.xml). (The search.maven.org Solr API returned a stale list topping out at 4.3.0, so don't rely on it.) — [search.maven.org](https://search.maven.org/solrsearch/select?q=g:org.apache.kafka+AND+a:kafka-clients&core=gav&rows=12&wt=json)
- Coordinates: `org.apache.kafka:kafka-clients:4.4.0`, `org.apache.kafka:kafka-streams:4.4.0`, `org.apache.kafka:kafka-streams-test-utils:4.4.0` (test). — [maven-metadata](https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/maven-metadata.xml); [Streams testing doc](https://kafka.apache.org/44/streams/developer-guide/testing/)
- Java: "Kafka Clients and Kafka Streams require Java 11, while Kafka Brokers, Connect and Tools now require Java 17" (4.0; KIP-750 dropped Java 8, KIP-1013 dropped Java 11 for brokers/tools). — [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/). The upgrade notes list no Java requirement changes in 4.1-4.4 and none planned for 5.0. — [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/). Java 25 support was added in 4.2. — [4.2.0 announcement](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/)
- Confluent Platform mapping: CP 8.4.x = AK 4.4.x (Oct 27, 2026), 8.3.x = 4.3.x (Jun 17, 2026), 8.2.x = 4.2.x (Mar 4, 2026), 8.1.x = 4.1.x (Oct 15, 2025), 8.0.x = 4.0.x (Jun 11, 2025). Java 21 is recommended and 25/21/17 are supported for 8.3/8.4. Java 11 is supported only for clients/Streams. — [Confluent versions & interoperability](https://docs.confluent.io/platform/current/installation/versions-interoperability.html)
- Docker `apache/kafka`: tags `4.4.0` (2026-10-22), `4.3.2`, `4.2.2`, all built for amd64 **and arm64**. `latest` was last updated 2026-06-24, so it does **not** point to 4.4.0. — [Docker Hub tags API](https://hub.docker.com/v2/repositories/apache/kafka/tags?page_size=25). `apache/kafka-native` has the same tag set, also amd64/arm64. — [kafka-native tags API](https://hub.docker.com/v2/repositories/apache/kafka-native/tags?page_size=25)
- Official Docker docs: JVM image since 3.7.0, `docker run -p 9092:9092 apache/kafka:4.4.0` starts a single node with default configs. The native (GraalVM) image (since 3.8.0) is "experimental and intended for local development and testing purposes only", and SASL in the native image arrived only in 4.4.0. — [Kafka 4.4 Docker doc](https://kafka.apache.org/44/getting-started/docker/)
- Docker env-var convention: prefix `KAFKA_`, dots become underscores (e.g. `KAFKA_NUM_PARTITIONS=3`, `KAFKA_NODE_ID=1`, `KAFKA_PROCESS_ROLES=broker,controller`, `KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093`, `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092`, `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1`). Overriding any setting disables all defaults, so you then have to supply the rest yourself. — [Docker Hub apache/kafka](https://hub.docker.com/r/apache/kafka)
- Multi-node compose examples live in the Kafka repo under `docker/examples/docker-compose-files/cluster/{combined|isolated}/{plaintext|ssl|sasl_plaintext}/docker-compose.yml`. The combined plaintext example exposes brokers on host ports 29092/39092/49092 and uses a `PLAINTEXT` (inter-broker) plus `PLAINTEXT_HOST` (client) listener. If `KAFKA_LISTENERS` is omitted it is derived from the advertised listeners. `CLUSTER_ID` is optional. — [docker/examples README](https://github.com/apache/kafka/blob/trunk/docker/examples/README.md)
- Testcontainers Kafka: `testImplementation "org.testcontainers:testcontainers-kafka:2.0.5"`. Use `org.testcontainers.kafka.KafkaContainer` for `apache/kafka` and `apache/kafka-native`, and `org.testcontainers.kafka.ConfluentKafkaContainer` for `confluentinc/cp-kafka` 7.4.0+. `org.testcontainers.containers.KafkaContainer` is deprecated. — [Testcontainers Kafka module](https://java.testcontainers.org/modules/kafka/). Latest `testcontainers-kafka` = 2.0.5 (2.0.0-2.0.5 exist; lastUpdated 2026-04-20). — [maven-metadata](https://repo1.maven.org/maven2/org/testcontainers/testcontainers-kafka/maven-metadata.xml)
- Schema Registry image `confluentinc/cp-schema-registry:8.4.0` (and `8.4.0-1-ubi9`), pushed 2026-10-26, amd64 + arm64. The 7.9.x line is still patched (7.9.10). — [Docker Hub tags API](https://hub.docker.com/v2/repositories/confluentinc/cp-schema-registry/tags?page_size=15)
- Spring for Apache Kafka: latest GA in Maven metadata is **4.1.2**, and `4.2.0-RC1` is published (metadata updated 2026-10-22). — [spring-kafka maven-metadata](https://repo1.maven.org/maven2/org/springframework/kafka/spring-kafka/maven-metadata.xml). 4.1.2 depends on kafka-clients 4.2.2. — [spring-kafka 4.1.2 POM](https://repo1.maven.org/maven2/org/springframework/kafka/spring-kafka/4.1.2/spring-kafka-4.1.2.pom). Spring Kafka 4.0.0 went GA Nov 18, 2025 on kafka-clients 4.1.1. — [spring.io blog (search result)](https://spring.io/blog/2025/11/18/spring-kafka-4/)
- Build tooling: Gradle current = **9.9.0** (built 2026-11-06). — [services.gradle.org](https://services.gradle.org/versions/current). JUnit BOM latest = **6.1.3**. — [junit-bom metadata](https://repo1.maven.org/maven2/org/junit/junit-bom/maven-metadata.xml). Kotlin stdlib: latest stable is 2.4.21 (2.5.0-Beta2 is preview). — [kotlin-stdlib metadata](https://repo1.maven.org/maven2/org/jetbrains/kotlin/kotlin-stdlib/maven-metadata.xml). kotlinx-coroutines-core = **1.11.0**. — [coroutines metadata](https://repo1.maven.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-core/maven-metadata.xml)
- Quarkus guide version 3.40 ("latest"), with `quarkus-messaging-kafka` on kafka-clients 4.1.1. — [Quarkus Kafka guide](https://quarkus.io/guides/kafka)
- Debezium 3.7.1.Final stable, 3.8.0.Alpha1 in development. — [Debezium releases](https://debezium.io/releases/)
- Compatibility floor (KIP-896): brokers must be 2.1+ before upgrading Java clients to 4.0, and clients must be 2.1+ before upgrading brokers to 4.0. 4.0 removed message formats v0/v1 (KIP-724) and moved to Log4j2 (KIP-653). — [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/)

### Inferences
- Recommended lab pin set (Nov 2026): JDK 25 toolchain; Gradle 9.9.0 wrapper; Kotlin 2.4.21; kotlinx-coroutines 1.11.0; kafka-clients/kafka-streams/kafka-streams-test-utils 4.4.0; Testcontainers 2.0.5; JUnit 6.1.3; images `apache/kafka:4.4.0`, `apache/kafka-native:4.4.0`, `confluentinc/cp-schema-registry:8.4.0`. Spring module: Spring Kafka 4.1.2, or 4.2.0 if it reaches GA before publication, since 4.2.0-RC1 suggests GA is imminent.
- Use `apache/kafka-native:4.4.0` for the Testcontainers labs (it's built for local dev and testing) and `apache/kafka:4.4.0` (JVM) for the compose clusters and the CLI tools. Background, unverified this session: the native image doesn't contain the `/opt/kafka/bin` scripts. Lessons that need `kafka-topics.sh` etc. should `docker exec` into a JVM-image container.
- Never use `:latest` in course material. As of this research it lags 4.4.0 by four months.
- Upcoming: Kafka 5.0 will remove items deprecated across 4.2-4.4 (MX4j, `streams-scala`, `group.coordinator.rebalance.protocols`, `kafka-broker-api-versions.sh`, MirrorMaker old metrics). Flag in the course that 5.0 may change the classic protocol's status.

### Gaps
- Whether `apache/kafka:latest` currently resolves to 4.3.1 or another version couldn't be determined from tag metadata alone. Inference only.
- Whether Testcontainers' `KafkaContainer` sets `transaction.state.log.replication.factor=1` / `min.isr=1` (needed for single-node transactions and EOS) and share-coordinator overrides out of the box wasn't confirmed on the module page. Recollection (unverified) is that the transaction settings are set. Lab authors should test it, or pass `withEnv(...)` explicitly.
- JUnit 6's Java baseline (believed Java 17) and whether JUnit 6 supports Kotlin `suspend` test functions natively weren't verified.
- Confluent Schema Registry serializer artifact coordinates and the Confluent Maven repo URL weren't verified this session.
- The O'Reilly page for "Kafka: The Definitive Guide" returned 403. Book details came from search results only (see section 1/Verified URLs).

---

## 3. Misconceptions to confront

### Takeaway
Most of the misconceptions come from mixing up a narrower guarantee with a broader one: per-partition ordering taken for global ordering, the log's exactly-once taken for exactly-once side effects, ISR acks taken for a replication guarantee, commit taken for processed, record-level deletion assumed where the unit is the segment. Each one has a cheap lab that disproves it.

### Cited Findings
- **"Kafka guarantees global ordering."** A consumer group assigns each partition to one member, which preserves per-partition ordering only. Share groups give up even that across members. — [KafkaShareConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html). Keyed records keep key-based partitioning, and unkeyed records are sprayed by the sticky partitioner. — [KIP-794](https://cwiki.apache.org/confluence/display/KAFKA/KIP-794%3A+Strictly+Uniform+Sticky+Partitioner)
- **"Exactly-once means my side effects happen once."** Kafka's EOS covers Kafka Streams, and transactional producers plus read_committed consumers. — [design doc](https://kafka.apache.org/44/design/design/). Offsets sent via `sendOffsetsToTransaction` count only if the Kafka transaction commits. — [KafkaProducer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html). The 2PC feature that would let Kafka take part in a DB transaction (KIP-939) was pulled from 4.1/4.2 and isn't in the 4.4 API. — [commit](https://www.mail-archive.com/commits@kafka.apache.org/msg31756.html). Jepsen found aborted reads and lost writes in Kafka transactions (2024). — [Jepsen](https://jepsen.io/analyses/bufstream-0.1.0)
- **"More partitions is always faster."** Adding partitions has costs: end-to-end latency, recovery time, file handles, producer memory. Adding partitions later remaps keys. — [Confluent/Jun Rao (search result)](https://www.confluent.io/blog/how-choose-number-topics-partitions-kafka-cluster/). Within a group, consumer parallelism is capped at the partition count. — [KafkaConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)
- **"acks=all alone means no data loss."** `acks=all` waits for the *current ISR*, which can shrink to just the leader. `min.insync.replicas` defaults to **1**. — [design doc](https://kafka.apache.org/44/design/design/); [topic configs](https://kafka.apache.org/44/configuration/topic-configs/). Kafka's own advice for transactional topics is RF>=3 and min ISR 2. — [KafkaProducer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html). Pre-ELR, the "last replica standing" case could lose committed data even with these settings. — [Vanlightly TLA+ doc](https://github.com/Vanlightly/kafka-tlaplus/blob/main/kafka_data_replication/kraft/kip-966/description/0_kafka_replication_protocol.md)
- **"Consumer commit = processed."** Auto-commit can commit offsets of records your code hasn't finished, which loses data if you hand records to another thread or don't drain the poll. Manual commit after processing is at-least-once, so duplicates remain possible. — [KafkaConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html). Jepsen found Kafka's "committed offset" semantics inconsistently documented. — [Jepsen](https://jepsen.io/analyses/bufstream-0.1.0)
- **"Retention deletes messages one at a time."** Retention and cleaning are "always done a file at a time" (segment granularity). The active segment is never compacted. — [topic configs](https://kafka.apache.org/44/configuration/topic-configs/); [design doc](https://kafka.apache.org/44/design/design/)
- **"Kafka is a queue."** Consumer groups give exclusive partition ownership, not per-message acks. Share groups (KIP-932, production-ready in 4.2) add queue semantics on top of topics: per-record acquisition locks, ACCEPT/RELEASE/REJECT/RENEW, and delivery count limits. — [4.2.0 announcement](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/); [KafkaShareConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html)
- **"Rebalances are rare."** Any slow batch past `max.poll.interval.ms` (default 5 min) makes the consumer leave the group. — [KafkaConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html). Deploys, scaling and crashes also trigger rebalances, and the classic protocol uses a group-wide barrier. — [KIP-848](https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+of+the+Consumer+Rebalance+Protocol)
- **"KIP-848 is on by default now."** Only server-side. The client `group.protocol` still defaults to `classic` in 4.4. — [consumer configs](https://kafka.apache.org/44/configuration/consumer-configs/)
- **"linger.ms=0 is the default; batching costs latency."** The default has been 5 since 4.0, because larger batches usually give similar or lower latency. — [producer configs](https://kafka.apache.org/44/configuration/producer-configs/)
- **"The idempotent producer dedupes everything."** It guarantees that *resending* won't duplicate entries in the log, using producer ID + sequence. — [design doc](https://kafka.apache.org/44/design/design/). It is also silently disabled by conflicting configs unless set explicitly. — [producer configs](https://kafka.apache.org/44/configuration/producer-configs/)
- **"read_committed lag is measured to the log end."** It is measured to the LSO, and offsets have gaps from markers and aborted records. — [KafkaConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

### Inferences
- An app-level resend (e.g. an HTTP retry that calls `send()` again with a new record) isn't deduped by the idempotent producer. Only the client's internal retries are. Payments need an idempotency key, deduplicated at the consumer in the same DB transaction as the side effect.
- "Increasing `max.poll.interval.ms` fixes poison pills" is a related misconception. A poison pill fails deterministically, so retrying in place just blocks the partition. The fix is bounded retries, then DLT.
- Another: "a DLT preserves ordering". Sending record N to a DLT and continuing with N+1 breaks per-key order. For payments, either park the whole key, i.e. hold later records for that account until the failed one resolves, or accept and document the reordering.

### Gaps
- No primary-source quote was found for the exact ordering behavior of the idempotent producer with `max.in.flight` 2-5 (ordering preserved with idempotence). This is well known but wasn't re-verified this session.

---

## 4. Lab design (Gradle multi-module, Kotlin + Java, tests)

### Takeaway
Use one Gradle 9.9 multi-module repo on a JDK 25 toolchain. Fast tests use Testcontainers (`apache/kafka-native:4.4.0`). Replication labs use a 3-broker compose copied from the official `cluster/combined/plaintext` example. Streams labs need no broker thanks to TopologyTestDriver. Every lab ends in a JUnit 6 assertion, so "done" is a green test.

### Cited Findings
- Testcontainers class and artifact: `org.testcontainers.kafka.KafkaContainer("apache/kafka-native:<ver>")` with `getBootstrapServers()`, artifact `org.testcontainers:testcontainers-kafka:2.0.5`. — [Testcontainers Kafka](https://java.testcontainers.org/modules/kafka/)
- The native image is intended for local dev/testing, and the JVM image runs with `docker run -p 9092:9092 apache/kafka:4.4.0`. — [Kafka Docker doc](https://kafka.apache.org/44/getting-started/docker/)
- Both images and cp-schema-registry 8.4.0 have arm64 builds (Apple Silicon). — [apache/kafka tags](https://hub.docker.com/v2/repositories/apache/kafka/tags?page_size=25); [kafka-native tags](https://hub.docker.com/v2/repositories/apache/kafka-native/tags?page_size=25); [cp-schema-registry tags](https://hub.docker.com/v2/repositories/confluentinc/cp-schema-registry/tags?page_size=15)
- 3-broker compose: `docker/examples/docker-compose-files/cluster/combined/plaintext/docker-compose.yml`, host ports 29092/39092/49092. — [docker/examples README](https://github.com/apache/kafka/blob/trunk/docker/examples/README.md)
- EOS needs 3 brokers by default. For dev, lower `transaction.state.log.replication.factor` / `transaction.state.log.min.isr`. — [Streams config](https://kafka.apache.org/44/streams/developer-guide/config-streams/). Share groups on <3 brokers need the share-state topic RF/min-ISR set to 1. — [upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- `segment.bytes` minimum is 1 MB since 4.0, so retention demos must use `segment.ms` or about 1 MB segments. — [upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/)
- TopologyTestDriver API as listed in section 1. — [Streams testing](https://kafka.apache.org/44/streams/developer-guide/testing/)
- Share consumer explicit-ack pattern: `share.acknowledgement.mode=explicit`, `acknowledge(record, AcknowledgeType.REJECT)`, `commitSync()`. — [KafkaShareConsumer javadoc](https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html)

### Inferences (proposed design; not sourced, but every API used is cited above)

**Repo layout**
```
kafka-course/
  settings.gradle.kts         // include(":common", ":lab01-log", ... )
  gradle/libs.versions.toml   // kafka=4.4.0, testcontainers=2.0.5, junit=6.1.3, kotlin=2.4.21, coroutines=1.11.0
  build-logic/                // convention plugin: JDK 25 toolchain, JUnit Platform, Kotlin JVM
  common/                     // KafkaTestSupport (shared KafkaContainer, AdminClient helpers, record collectors)
  labs/lab01-log ... lab12-share-groups   // each lab: src/main (starter), src/test (acceptance tests), solution branch
  spring-lab/                 // optional Spring Kafka module on Spring Kafka's managed kafka-clients
  docker/single-node.yml      // apache/kafka:4.4.0, one node
  docker/cluster-3.yml        // copied from official combined/plaintext example
  docker/schema-registry.yml  // + confluentinc/cp-schema-registry:8.4.0
```
- Shared container: one `KafkaContainer` per test JVM (singleton pattern) to keep startup cost low. Each test uses unique topic names (UUID suffix).
- Mix languages on purpose. Java for the "raw client" labs (to match the javadoc). Kotlin for the coroutine wrapper, the Streams topology, and the payments domain.

**Concrete labs with testable outcomes**
1. **L1 Log basics.** Produce 100 records and read them back from offset 0 and from offset 50 (`seek`). *Assert:* offsets are contiguous and start at 0, and the second read starts at 50. *Explore:* `docker exec` into the JVM broker, `ls` the partition dir, and identify the `.log/.index/.timeindex` files.
2. **L2a Retention by segment.** Topic with `segment.ms=10000`, `retention.ms=20000`. Produce, wait, and poll `AdminClient.listOffsets(earliest)`. *Assert:* the earliest offset jumps in segment-sized steps, never by one. **L2b Compaction.** `cleanup.policy=compact`, small `segment.ms`, `min.cleanable.dirty.ratio=0.01`, write k1=v1,v2,v3 and k2=v1 plus a tombstone for k2. *Assert:* after compaction, a full read yields k1=v3 and eventually no k2 once `delete.retention.ms` passes. Original offsets are retained (gaps appear).
3. **L3 Kill a broker (3-node compose).** Topic with RF=3, `min.insync.replicas=2`. `docker stop` one broker. *Assert (AdminClient describeTopics):* ISR size goes from 3 to 2 and `acks=all` sends still succeed. Stop a second broker. *Assert:* sends fail with a not-enough-replicas error (exception class name unverified; expect `NotEnoughReplicasException`) once `delivery.timeout.ms` expires. Restart and watch the ISR recover. Bonus: compare with `acks=1`.
4. **L4 Keys and ordering.** Produce 1,000 records across 10 account keys with sequence numbers into a 6-partition topic. *Assert:* for each key, consumed sequence numbers are strictly increasing and all records of a key share one partition. The unkeyed variant: *assert* records spread over more than one partition. Variant: `partitioner.ignore.keys=true` breaks per-key co-location.
5. **L5 Batching.** Send 50k small records with `linger.ms` = 0, 5 and 50 and `compression.type` = none and lz4. Read the producer metrics (`producer.metrics()`; metric names such as `batch-size-avg` and `records-per-request-avg` are unverified). *Assert:* avg batch size rises with linger.ms. Report throughput and p99 send latency in a table (an observation, not a hard assertion). Then a test showing `acks=1` without explicit idempotence disables idempotence, and that explicit `enable.idempotence=true` + `acks=1` throws `ConfigException`.
6. **L6 At-least-once consumer that survives a crash + idempotent sink.** Payments consumer with `enable.auto.commit=false`. It processes into a Postgres or H2 table `payments(idempotency_key PK, ...)` and calls `commitSync()` after the DB commit. Inject a crash (throw after the DB write, before the commit) and restart the consumer. *Assert:* the record is redelivered (at-least-once) but the table holds exactly one row per idempotency key (dedupe via the unique constraint / `INSERT ... ON CONFLICT DO NOTHING`).
7. **L7 Rebalance observation, 3 consumers × 6 partitions.** Start consumers one by one with a `ConsumerRebalanceListener` recording revoked/assigned sets. *Assert:* the final assignment covers all 6 partitions with 2 per consumer and no overlap. Run under `group.protocol=consumer` and, for contrast, `classic` with `CooperativeStickyAssignor`. Measure how many partitions were revoked from untouched members (expect 0 under KIP-848). Also force `max.poll.interval.ms` exceedance (sleep in the handler) and *assert* `CommitFailedException` / reassignment. Show lag with `kafka-consumer-groups.sh --describe`.
8. **L8 Poison pill → DLT.** Topic with one malformed record among valid ones. Plain-client version: bounded in-memory retries, then produce to `<topic>.DLT` with headers (original topic/partition/offset/exception), then commit. *Assert:* valid records are processed, the DLT holds exactly the poison record, and the consumer isn't stuck. Spring variant: `DefaultErrorHandler` + `DeadLetterPublishingRecoverer`, or `@RetryableTopic` (Spring APIs named from background knowledge, not verified this session apart from `@RetryableTopic`, which appears in the 4.1 notes).
9. **L9 Transactional consume-transform-produce.** Read `payments`, write `ledger-entries`, `sendOffsetsToTransaction(offsets, consumer.groupMetadata())`. Inject failure before commit and call `abortTransaction()`. *Assert:* a `read_committed` consumer sees no aborted output and a `read_uncommitted` consumer does. After restart, output has no duplicates. Bonus: a second producer with the same `transactional.id` fences the first (`ProducerFencedException`).
10. **L10 Streams running balance (no broker).** Kotlin topology: `stream("transactions").groupByKey().aggregate(...)`, materialized as `"balances"`, `toStream().to("balances")`. *Assert with TopologyTestDriver:* after piping +100, -30, +5 for `acct-1`, `getKeyValueStore("balances")["acct-1"] == 75` and the output topic's last value is 75. Extension: a windowed count over 1-minute windows to flag more than 3 debits/min, using `pipeInput` with explicit timestamps.
11. **L11 Schema evolution (Schema Registry container).** Register Avro v1 of `Payment`. Try v2 adding an optional field with a default (*assert* compatible under BACKWARD) and v3 adding a required field with no default (*assert* the registry rejects it with 409). Compatibility check via the REST API, so no Confluent serializer dependency is needed. Optional stretch: Debezium outbox.
12. **L12 Share group.** On a single node with share state topic RF/min-ISR set to 1 and `share.version` enabled, run 3 `KafkaShareConsumer`s on a **1-partition** topic. *Assert:* all three receive records, which is impossible with a consumer group. With explicit ack, RELEASE a record every time. *Assert:* it is redelivered until `share.delivery.count.limit` (5) and then archived. On 4.4 with `share.version=2` and `errors.deadletterqueue.topic.name` set, *assert* it lands in the DLQ. Kotlin stretch: wrap a `KafkaConsumer` in a single-thread dispatcher and expose a `Flow<ConsumerRecord>`. *Assert* that cancelling the coroutine scope calls `wakeup()` and closes cleanly within N seconds.

### Gaps
- The exact env vars Testcontainers sets on `apache/kafka-native` (transaction state log, share coordinator) need a smoke test before lesson writing.
- How long it takes for a compacted topic to visibly compact in a test (cleaner backoff) wasn't measured. Expect flakiness; use Awaitility with generous timeouts.
- The share-group enablement command and broker config names need confirming against a running 4.4.0 broker. See section 1 Gaps.

---

## 5. Proposed lesson outline (12 lessons)

### Takeaway
Twelve lessons, each 60-120 minutes, with one or two labs. The first three build the storage and cluster model. Lessons 4-9 cover the client contract (produce, consume, rebalance, fail, transact). Lessons 10-12 cover higher-level systems (Streams, schemas/CDC, queues and operations).

### Cited Findings
- The current-state facts each lesson depends on are cited in sections 1-4: linger.ms 5, KIP-848 opt-in, share groups production-ready in 4.2 with DLQ in 4.4, ELR default on new 4.1+ clusters, tiered storage production-ready in 3.9, KIP-939 not shipped, Streams `exactly_once_v2`. — see [4.4 upgrade notes](https://kafka.apache.org/44/getting-started/upgrade/) and the per-section sources.

### Inferences (proposed outline)
| # | Lesson | Core concepts | Labs |
|---|---|---|---|
| 1 | The log | Kreps' log essay; append-only, offsets, consumer position as one integer; page cache and sequential IO; why Kafka ≠ broker-with-queues | L1 log basics + repo/Testcontainers smoke test |
| 2 | Storage on disk | topics/partitions/segments, `.log/.index/.timeindex`, retention by time/size (whole segments), compaction + tombstones, tiered storage (KIP-405, `remote.storage.enable`, `local.retention.*`) | L2a retention, L2b compaction |
| 3 | The cluster | KRaft controllers (ZK gone in 4.0, dynamic quorum 3.9), leaders/followers, ISR, HW, `min.insync.replicas`, unclean election (default false), ELR (KIP-966) | L3 kill-a-broker on 3-node compose |
| 4 | Producer I: where records go | keys, murmur hash (unverified), KIP-794 sticky/adaptive partitioning, per-key ordering, `partitioner.ignore.keys`, choosing keys for payments (account ID) | L4 key ordering |
| 5 | Producer II: how records get there | accumulator, `batch.size`, `linger.ms` (5 since 4.0), compression, `acks`, retries, `delivery.timeout.ms`, `max.in.flight`, idempotence default and silent disabling | L5 batching + idempotence-config tests |
| 6 | Consumer fundamentals | poll loop, thread confinement, `wakeup()`, offsets vs position, auto vs manual commit, at-most/at-least/effectively-once, idempotency keys | L6 crash-surviving consumer + dedupe |
| 7 | Groups and rebalancing | classic eager vs cooperative vs KIP-848 (epochs, server assignors, revoke-then-assign), static membership, `max.poll.interval.ms`, lag | L7 3×6 rebalance observation (+ classic contrast) |
| 8 | Failure handling | poison pills, deserialization errors, bounded retries, retry topics, DLT, ordering-preserving retries for payments, Spring `@RetryableTopic` vs plain | L8 DLT (plain + Spring variant) |
| 9 | Transactions and EOS | `transactional.id`, fencing, `sendOffsetsToTransaction`, `read_committed`/LSO, KIP-890 epoch bump (4.0), Jepsen findings, KIP-939 not shipped, EOS ≠ external side effects; outbox as the fix for dual writes | L9 consume-transform-produce |
| 10 | Kafka Streams | KStream/KTable duality, state stores (RocksDB), changelogs, standbys, windowing, joins, `exactly_once_v2`, KIP-1071 protocol, Streams DLQ (KIP-1034) | L10 running balance + windowed rule via TopologyTestDriver |
| 11 | Schemas, Connect, CDC | Schema Registry modes (BACKWARD default), Avro vs Protobuf vs JSON Schema, Connect workers/converters, Debezium 3.7, transactional outbox + outbox event router | L11 schema evolution test (+ optional Debezium outbox) |
| 12 | Queues and operations | share groups (locks, ack types, delivery count, DLQ in 4.4), partition sizing, lag monitoring, tiered storage ops, Spring Kafka vs Quarkus vs plain + coroutines | L12 share group + Kotlin Flow wrapper |

- Could be compressed to 10 by merging 4+5 (producer) and 11+12 (data integration and operations), at the cost of lab time.

### Gaps
- No existing course with this exact sequence was found to compare against. The outline is the researcher's proposal.

---

## 6. Verified URLs

### Takeaway
The URLs below were fetched on 2026-11-07 and returned real content. URLs that failed, or that appeared only in search results, are listed separately and shouldn't be treated as verified.

### Cited Findings
Fetched and loaded:
- https://kafka.apache.org/community/downloads/
- https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/
- https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/
- https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/
- https://kafka.apache.org/blog/2025/09/04/apache-kafka-4.1.0-release-announcement/
- https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/
- https://kafka.apache.org/blog/2024/11/06/apache-kafka-3.9.0-release-announcement/
- https://kafka.apache.org/44/getting-started/upgrade/
- https://kafka.apache.org/44/getting-started/docker/
- https://kafka.apache.org/44/design/design/
- https://kafka.apache.org/44/configuration/producer-configs/
- https://kafka.apache.org/44/configuration/consumer-configs/
- https://kafka.apache.org/44/configuration/topic-configs/
- https://kafka.apache.org/44/configuration/group-configs/
- https://kafka.apache.org/44/operations/eligible-leader-replicas/
- https://kafka.apache.org/44/streams/developer-guide/testing/
- https://kafka.apache.org/44/streams/developer-guide/config-streams/
- https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html
- https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html
- https://kafka.apache.org/44/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html
- https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+of+the+Consumer+Rebalance+Protocol
- https://cwiki.apache.org/confluence/display/KAFKA/KIP-890%3A+Transactions+Server-Side+Defense
- https://cwiki.apache.org/confluence/display/KAFKA/KIP-939%3A+Support+Participation+in+2PC
- https://cwiki.apache.org/confluence/display/KAFKA/KIP-794%3A+Strictly+Uniform+Sticky+Partitioner
- https://www.mail-archive.com/commits@kafka.apache.org/msg31756.html
- https://issues.apache.org/jira/browse/KAFKA-17754
- https://jepsen.io/analyses/bufstream-0.1.0
- https://github.com/Vanlightly/kafka-tlaplus/blob/main/kafka_data_replication/kraft/kip-966/description/0_kafka_replication_protocol.md
- https://github.com/apache/kafka/blob/trunk/docker/examples/README.md
- https://hub.docker.com/r/apache/kafka
- https://hub.docker.com/v2/repositories/apache/kafka/tags?page_size=25
- https://hub.docker.com/v2/repositories/apache/kafka-native/tags?page_size=25
- https://hub.docker.com/v2/repositories/confluentinc/cp-schema-registry/tags?page_size=15
- https://java.testcontainers.org/modules/kafka/
- https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/maven-metadata.xml
- https://repo1.maven.org/maven2/org/springframework/kafka/spring-kafka/maven-metadata.xml
- https://repo1.maven.org/maven2/org/springframework/kafka/spring-kafka/4.1.2/spring-kafka-4.1.2.pom
- https://repo1.maven.org/maven2/org/testcontainers/testcontainers-kafka/maven-metadata.xml
- https://repo1.maven.org/maven2/org/junit/junit-bom/maven-metadata.xml
- https://repo1.maven.org/maven2/org/jetbrains/kotlin/kotlin-stdlib/maven-metadata.xml
- https://repo1.maven.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-core/maven-metadata.xml
- https://services.gradle.org/versions/current
- https://docs.spring.io/spring-kafka/reference/whats-new.html
- https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html
- https://docs.confluent.io/platform/current/installation/versions-interoperability.html
- https://debezium.io/releases/
- https://quarkus.io/guides/kafka

### Inferences
- For learners, link the human-readable pages (release blog posts, `/44/` docs, javadoc, Testcontainers module page) rather than Maven metadata or Docker Hub API URLs.

### Gaps
Not verified (failed or search-only):
- https://kafka.apache.org/downloads and https://kafka.apache.org/documentation/ return redirect shells. Use `/community/downloads/` and `/44/...`.
- https://kafka.apache.org/44/operations/share-groups/ returned 404.
- https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying returned 404 to the fetcher, though search results list it as canonical (Dec 16, 2013). Check it in a browser before linking.
- https://www.oreilly.com/library/view/kafka-the-definitive-guide/9781492043072/ returned 403. Search results give: *Kafka: The Definitive Guide*, 2nd ed., Gwen Shapira, Todd Palino, Rajini Sivaram, Krit Petty, O'Reilly, Nov 2021, ISBN 9781492043072 ([O'Reilly preface page, search result](https://www.oreilly.com/library/view/kafka-the-definitive/9781492043072/preface01.html)). It predates KRaft-only, KIP-848 and share groups, so recommend it for fundamentals only.
- Search-only (not fetched): https://spring.io/blog/2025/11/18/spring-kafka-4/ , https://www.confluent.io/blog/introducing-apache-kafka-4-4-0/ , https://www.confluent.io/blog/how-choose-number-topics-partitions-kafka-cluster/ , https://mail-archive.com/commits@kafka.apache.org/msg30357.html , https://issues.apache.org/jira/browse/KAFKA-17582
- No Jack Vanlightly blog post was fetched. Only his TLA+ repo doc was.

---

## 7. Teaching notes (misconceptions, analogies, what to cut)

### Takeaway
Anchor everything on "a partition is an append-only file with a bookmark per reader". Use the payments domain throughout, since it makes ordering, idempotency and EOS limits concrete. Cut the ZooKeeper-era and legacy material that 4.x has removed or deprecated.

### Cited Findings
- ZooKeeper mode is gone in 4.0. — [4.0.0 announcement](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/)
- `exactly_once` (EOS v1) is deprecated in Streams; use `exactly_once_v2`. — [Streams config](https://kafka.apache.org/44/streams/developer-guide/config-streams/)
- `streams-scala` is deprecated (4.3, KIP-1244). — [4.3.0 announcement](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/)
- `DefaultPartitioner`/`UniformStickyPartitioner` are deprecated (KIP-794). — [KIP-794](https://cwiki.apache.org/confluence/display/KAFKA/KIP-794%3A+Strictly+Uniform+Sticky+Partitioner)
- The classic consumer protocol is on a deprecation path (KIP-1274 in 4.3). — [4.3.0 announcement](https://kafka.apache.org/blog/2026/05/22/apache-kafka-4.3.0-release-announcement/)
- KIP-939 2PC isn't released. — [commit removing APIs](https://www.mail-archive.com/commits@kafka.apache.org/msg31756.html)
- Jepsen's 2024 findings and the open or recently resolved JIRAs give real-world grounding for "transactions are subtle". — [Jepsen](https://jepsen.io/analyses/bufstream-0.1.0); [KAFKA-17754](https://issues.apache.org/jira/browse/KAFKA-17754)

### Inferences
**Analogies that work**
- **Partition = bank ledger page; offset = line number; consumer offset = bookmark.** Reading doesn't erase anything. Many teams keep their own bookmark. Retention tears out whole old pages (segments), never single lines.
- **Compaction = keeping only the latest balance per account.** A tombstone is "account closed".
- **Consumer group = checkout lanes with assigned aisles.** Each lane (consumer) owns some aisles (partitions) and keeps their order. A **share group** is a deli counter with numbered tickets: anyone can take the next ticket, a ticket left unattended goes back in the pile after 30 s (acquisition lock), and after 5 tries it gets thrown out (delivery count / DLQ).
- **ISR = the copies that were in the room when the decision was made. HW = "the ink is dry" line:** consumers only read below it. `min.insync.replicas` = how many people must sign before it counts.
- **Rebalance, classic vs KIP-848:** classic is "everyone stop, put down your work, and wait for the new seating chart". KIP-848 is "only the people whose seats change get up".
- **Transactions = an all-or-nothing envelope across topics plus the consumer bookmark.** It does not cover the DB row you wrote along the way. That's what the outbox and idempotency keys are for.

**Misconception drills.** Each misconception in section 3 maps to a lab that falsifies it: ordering → L4; acks/min ISR → L3; commit ≠ processed → L6; retention granularity → L2a; rebalances → L7; EOS limits → L9; Kafka-as-queue → L12.

**What to cut or minimize**
- ZooKeeper internals and migration (dead in 4.0). MirrorMaker 2 (an operations topic). Deep SASL/SSL/ACL setup (one slide). JMX/Yammer metric internals (4.4 deprecates the classic-group Yammer metrics). EOS v1. Eager rebalancing internals beyond one contrast slide. The Scala Streams DSL. KIP-939 2PC (mention as "not yet shipped"). Writing custom partitioners or assignors (client-side KIP-848 assignors aren't implemented).
- The Definitive Guide (2021) is still good for internals, but flag that its config defaults (e.g. linger.ms 0) and ZooKeeper chapters are out of date.

**Senior-engineer framing.** These learners already "use Kafka at work". Open each lesson with a production incident or a question ("why did we double-charge?", "why did the group rebalance every 5 min?") and answer it with the model. Keep the code close to the raw client API, since that is what Spring and Quarkus wrap.

**Volatility flags for lesson writers.** Share group DLQ (4.4, "may change in a minor release"). KIP-1071 Streams protocol (GA with a limited feature set). The default `group.protocol` might flip, or classic might be deprecated, in 5.0. KIP-939. Spring Kafka 4.2 GA timing. The `apache/kafka:latest` tag lag.

### Gaps
- None of the analogies were tested with learners. They are the researcher's suggestions.
