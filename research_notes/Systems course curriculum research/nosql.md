# NoSQL Databases: types, distributed-systems concepts, current state (Nov 2026), and a 12-lesson hands-on track

Audience: senior Java/Kotlin backend engineer. Redis has its own track and appears here only as the key-value example. Research date: 2026-11-07. Every fact below has an inline source. Items from background knowledge that I could not re-verify this session are in **Gaps** and flagged "verify".

---

## 1. Teaching order and scope: why NoSQL appeared and the data-model families

### Takeaway
NoSQL grew out of two industrial papers. Google's Bigtable (OSDI 2006) became the wide-column/LSM lineage. Amazon's Dynamo (SOSP 2007) became the leaderless, consistent-hashing, tunable-quorum lineage. Both were built for scale-out and availability rather than SQL features. Teach the families as data models with one lead product each (DynamoDB, MongoDB, Cassandra/ScyllaDB, Neo4j, plus time-series, search and vector), and teach the distributed-systems ideas as a shared layer underneath them.

### Cited Findings
- **Bigtable**: "Bigtable: A Distributed Storage System for Structured Data", Chang, Dean, Ghemawat, Hsieh, Wallach, Burrows, Chandra, Fikes, Gruber. 7th USENIX OSDI, 2006, pp. 205–218. The abstract describes a "simple data model ... which gives clients dynamic control over data layout and format." — [Google Research](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/)
- The Dynamo paper describes Bigtable as maintaining "a sparse, multi-dimensional sorted map." — [Dynamo paper, SOSP 2007, p.208](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- **Dynamo** was built for an "always writeable" data store "where no updates are rejected due to failures or concurrent writes", for example the shopping cart where "Add to Cart" must never be lost. It targeted latency SLAs at the 99.9th percentile. — [Dynamo paper §3.3, §4.4](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Dynamo's Table 1 maps problems to techniques:
  - Partitioning → consistent hashing (incremental scalability)
  - High availability for writes → vector clocks with reconciliation during reads
  - Temporary failures → sloppy quorum and hinted handoff
  - Permanent failures → anti-entropy using Merkle trees
  - Membership and failure detection → gossip-based protocol

  — [Dynamo paper p.209](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Abadi names the two forces behind distributed DBs: (1) "modern applications require increased data and transactional throughput, which has led to a desire for elastically scalable database systems", and (2) globalization, which requires "data near clients who are spread across the world". He lists Dynamo/DynamoDB, Cassandra, Voldemort, PNUTS, Riak, HBase/BigTable, MongoDB, VoltDB/H-Store and Megastore as examples. — [Abadi, IEEE Computer Feb 2012, p.37](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- Origin stories that work in class: "Amazon originally designed Dynamo to serve data to the core services in its e-commerce platform (for example, the shopping cart). Facebook constructed Cassandra to power its Inbox Search feature. LinkedIn created Voldemort... Yahoo built PNUTS..." — [Abadi p.38](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- Cassandra takes Dynamo's partitioning (consistent hashing), "multi-master replication with versioned data and tunable consistency", and gossip membership and failure detection. Its storage engine is LSM-based, which is the Bigtable lineage. — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- **Graph standard**: ISO/IEC 39075:2024 "Information technology — Database languages — GQL" was published 12 April 2024. It is the first new ISO database query language since SQL in 1987, and its core MATCH…RETURN syntax is largely Cypher-like. — [Wikipedia: Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language) (search result; not fetched)
- **Families and lead products** (current state is in section 5):
  - Key-value: DynamoDB. Redis is covered in its own track.
  - Document: MongoDB 9.0. — [MongoDB release notes](https://www.mongodb.com/docs/manual/release-notes/)
  - Wide-column: Apache Cassandra 5.0.x GA, 6.0 in alpha. — [Cassandra downloads](https://cassandra.apache.org/_/download.html), [Docker Hub cassandra](https://hub.docker.com/_/cassandra)
  - Graph: Neo4j 2026.10 with Cypher 25 / Cypher 5. — [Neo4j Docker docs](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
  - Time-series: TimescaleDB (Tiger Data), InfluxDB 3 Core.
  - Search: OpenSearch / Elasticsearch.
  - Vector: pgvector, Qdrant, Milvus. DynamoDB, Cassandra 5.0 and MongoDB now also ship native vector features.

### Inferences
- Recommended order: motivation and families → access-pattern modeling → KV/DynamoDB → partitioning → replication and quorums (via Cassandra) → wide-column modeling and storage → document/MongoDB → consistency models, CAP/PACELC and conflicts → transactions → graph → specialized stores (time-series, search, vector) → choosing a store. The core concepts land best when each one has a store where you can watch it happen: partitioning in DynamoDB, leaderless quorums in Cassandra, leader-follower failover in MongoDB.
- Teach "NoSQL" as "non-relational data models plus scale-out architectures". Many families (MongoDB, Cassandra CQL) now have schemas, transactions and query languages, so the label describes history more than capability.
- Time-series, search and vector each deserve one combined lesson, not three. They are specialized indexes and storage layouts, and most of the course's distributed concepts carry over unchanged.

### Gaps
- I did not fetch the ISO catalogue page for 39075 (iso.org pages are often paywalled or blocked). The publication date comes from Wikipedia via search.
- I did not verify how closely Neo4j's Cypher 25 conforms to GQL.

---

## 2. Core distributed-systems concepts (partitioning, replication, quorums, repair, CAP/PACELC, consistency models, conflicts, secondary indexes, TTL/tombstones)

### Takeaway
Cassandra's architecture page and the Dynamo paper are a single, verifiable script for consistent hashing, vnodes, N/R/W quorums, hinted handoff, read repair and Merkle-tree anti-entropy. Abadi's PACELC paper is the primary source for correcting the "pick two" reading of CAP. Jepsen's models page supplies the consistency hierarchy and which models can stay available during a partition.

### Cited Findings

**Partitioning and consistent hashing**
- On the ring, "each node owns one or more tokens"; a key is hashed to a token and replicas are found by walking the ring clockwise. Adding a node moves only a small fraction of keys, unlike modulo hashing. — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- Dynamo hashes the key with MD5 to a 128-bit identifier. "The principle advantage of consistent hashing is that departure or arrival of a node only affects its immediate neighbors." Basic consistent hashing gives "non-uniform data and load distribution" and ignores heterogeneity. Virtual nodes (multiple tokens per node) fix both: a failed node's load "is evenly dispersed across the remaining available nodes", and token count can follow capacity. — [Dynamo paper §4.1–4.2](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Cassandra vnodes:
  - Cassandra 2.x used 256 random tokens per node. 3.x+ uses a deterministic allocator that needs "a much lower number of tokens per physical node".
  - Downsides: more neighbors per token (up to 2×(RF−1)), slower cluster-wide maintenance, and possible effects on range scans.

  — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- **Hot partitions (DynamoDB)**: "Every partition in a DynamoDB table is designed to deliver a maximum capacity of 3,000 read units per second and 1,000 write units per second." One RCU is one strongly consistent read per second (or two eventually consistent reads) of up to 4 KB. One WCU is one write per second of up to 1 KB. Example: with a 20 KB item you get about 600 consistent reads/s on that single item. AWS recommends uniform activity across partition keys, write sharding, and notes that "adaptive capacity applies to on-demand mode and provisioned capacity". — [DynamoDB partition key best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- Cassandra partition key goals: "distribute data evenly across the cluster" and keep "the number of partitions read for a query to a minimum". Guideline: "keep number of values per partition to below 100,000 and disk space per partition to below 100MB." — [Cassandra data modeling intro](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html)

**Replication: leader-follower vs leaderless**
- Abadi's three replication options:
  1. Send updates to all replicas at the same time.
  2. Send updates to an agreed-upon master first (synchronous, asynchronous, or mixed).
  3. Send updates to an arbitrary node first.

  "As soon as a DDBS replicates data, a tradeoff between consistency and latency arises." Dynamo, Cassandra and Riak use a mix of options (2)(c) and (3). PNUTS uses (2)(b)(ii). — [Abadi pp.39–40](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- Cassandra: "Writes are always sent to all replicas"; the consistency level only sets how many acknowledgements the coordinator waits for. — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- Replication strategies: `NetworkTopologyStrategy` sets RF per datacenter and is rack-aware; production should use it. `SimpleStrategy` is "useful only for testing". — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)

**Quorums (N, R, W) and tunable consistency**
- Dynamo: "R is the minimum number of nodes that must participate in a successful read... W is the minimum number of nodes that must participate in a successful write. Setting R and W such that R + W > N yields a quorum-like system... R and W are usually configured to be less than N, to provide better latency." "A typical value of N used by Dynamo's users is 3." Setting W=1 means a write is rejected only if every node is down, but low R and W "increase the risk of inconsistency". — [Dynamo paper §4.5, §6](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Dynamo's sloppy quorum: "all read and write operations are performed on the first N healthy nodes from the preference list, which may not always be the first N nodes encountered while walking the consistent hashing ring." — [Dynamo §4.6](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Cassandra consistency levels:
  - ONE, TWO, THREE
  - QUORUM: majority, n/2+1 (2 of 3 at RF=3)
  - ALL
  - LOCAL_QUORUM: majority in the coordinator's DC
  - EACH_QUORUM: majority in each DC
  - LOCAL_ONE
  - ANY: writes only; a stored hint counts

  "W + R > RF" gives read-your-acknowledged-writes overlap. LOCAL_QUORUM only guarantees that within a DC. — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- Abadi's caveat: "simply using a quorum protocol is not sufficient to guarantee consistency to the level defined by Gilbert and Lynch" (linearizability). Even with R + W > N, Dynamo-style systems "cannot achieve full consistency". — [Abadi pp.40, 42](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)

**Hinted handoff, read repair, anti-entropy (Merkle trees), gossip**
- Dynamo hinted handoff: if node A is down, the replica goes to D "with a hint in its metadata" naming A as the intended recipient. D keeps it in a separate local database and delivers it when A recovers. — [Dynamo §4.6](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Read repair: after a read, the coordinator "updates those nodes [that returned stale versions] with the latest version. This process is called read repair." — [Dynamo §5](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Merkle trees: "leaves are hashes of the values of individual keys. Parent nodes higher in the tree are hashes of their respective children... each branch of the tree can be checked independently without requiring nodes to download the entire tree." Dynamo keeps one tree per key range. — [Dynamo §4.7](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Cassandra:
  - Hinted handoff is best-effort, on the write path.
  - Read repair is best-effort, on the read path.
  - Anti-entropy repair compares Merkle trees and comes in full, sub-range and incremental forms.
  - Gossip runs about once per second with a random peer, with (generation, version) tuples.
  - Failure detection is "a variant of the Phi Accrual failure detector". UP/DOWN is a local decision that gossip does not propagate.

  — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)

**CAP and PACELC (and the common misreading)**
- Abadi: "CAP basically states that in building a DDBS, designers can choose two of three desirable properties... However... CAP has become increasingly misunderstood and misapplied... many designers incorrectly conclude that the theorem imposes certain restrictions on a DDBS during normal system operation... In reality, CAP only posits limitations in the face of certain types of failures." — [Abadi p.37](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- "It is wrong to assume that DDBSs that reduce consistency in the absence of any partitions are doing so due to CAP-based decision-making." The trade-off comes from "the combination of partition tolerance and the existence of a network partition itself." — [Abadi p.38](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- PACELC (pronounced "pass-elk"): "if there is a partition (P), how does the system trade off availability and consistency (A and C); else (E), when the system is running normally in the absence of partitions, how does the system trade off latency (L) and consistency (C)?" ELC applies only to systems that replicate. — [Abadi p.41](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- Classifications in the paper (default configs, 2012):
  - PA/EL: Dynamo, Cassandra, Riak
  - PC/EC: VoltDB/H-Store, Megastore, BigTable/HBase
  - PA/EC: MongoDB of 2012, because its asynchronous replication plus a "rollback directory" on failover put it in that class
  - PC/EL: PNUTS

  — [Abadi p.42](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- PACELC was first described in a 2010 blog post and formalized in the 2012 paper. Wikipedia says it was formally proved in 2018 (SIGACT News). — [Wikipedia PACELC](https://en.wikipedia.org/wiki/PACELC_theorem) (search result; not fetched)

**Consistency models**
- Jepsen: "A consistency model is a safety property which declares what a system can do." — [Jepsen consistency](https://jepsen.io/consistency)
- Availability limits from Jepsen's hierarchy:
  - Strict serializable, serializable, repeatable read, snapshot isolation, cursor stability, linearizable and sequential cannot be totally available.
  - Linearizable and sequential are "at most sticky available"; so are causal, PRAM and read-your-writes.
  - Read committed and read uncommitted can be totally available.
  - "Linearizable implies sequential"; "PRAM implies monotonic reads".

  — [Jepsen consistency models](https://jepsen.io/consistency/models)
- MongoDB causally consistent sessions guarantee causal consistency "only if the associated reads use 'majority' read concern and the associated writes use 'majority' write concern". The default read concern is `local`, which "can return data that may be rolled back". — [MongoDB defaults](https://www.mongodb.com/docs/manual/reference/mongodb-defaults/)
- Abadi notes that systems reading from any replica can still offer bounded models such as "sequential/timeline consistency or read-your-writes consistency" by tracking update sequence numbers. — [Abadi p.40](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- Dynamo coordinator optimization: for a write, it picks the node that replied fastest to the preceding read, "thereby increasing the chances of getting 'read-your-writes' consistency". — [Dynamo §5](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)

**Conflict resolution: LWW, vector clocks, CRDT-like merges**
- Dynamo says the store "can only use simple policies, such as 'last write wins'". Application-level reconciliation, such as merging carts, is more flexible. Merging means "an 'add to cart' operation is never lost. However, deleted items can resurface." — [Dynamo §2.3, §4.4](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Vector clocks: "a list of (node, counter) pairs." If one clock's counters are all ≤ another's, the first is an ancestor; otherwise the versions conflict. The paper's Figure 3 walks D1→D5 with Sx, Sy, Sz. Clocks are truncated at about 10 entries. — [Dynamo §4.4](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Dynamo also ran timestamp-based LWW for its session-info service. — [Dynamo §6](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Cassandra: every mutation, deletes included, carries a timestamp and "last write wins". Correctness depends on synchronized clocks (NTP). — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
- CQL `USING TIMESTAMP` sets the write timestamp, by default the coordinator's time in microseconds. Unless each statement has its own timestamp, statements in a batch share one, so apply order may differ from listed order. — [CQL DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html)

**TTLs and tombstones**
- A delete in Cassandra is an insert of a timestamped tombstone. "This approach is used instead of removing values because of the distributed nature of Cassandra." TTL expiry also creates tombstones. `gc_grace_seconds` defaults to 864000 (10 days), after which compaction can purge the tombstone. If a node stays down longer than that and is repaired back in, deleted data can return as "zombies". — [Cassandra tombstones](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html)
- CQL TTL is in seconds and applies to values, not columns. An update resets that column's TTL. "A TTL of 0 is equivalent to no TTL." — [CQL DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html)
- Cassandra 5.0 added the `sstablepartitions` offline tool for finding large partitions, TTL/writetime functions on collections and UDTs, and an extended maximum TTL date. — [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html)

**Secondary indexes in distributed stores**
- Cassandra 5.0 added Storage-Attached Indexes (SAI) and a vector type with similarity functions. — [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html)
- DynamoDB transactions "cannot be performed using indexes". After a transaction, changes propagate gradually to GSIs, streams and backups. — [DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- DynamoDB GSIs accept multi-attribute composite keys since 2025-11-19: up to 4 partition-key and 4 sort-key attributes, so you no longer need hand-concatenated synthetic keys. Sort-key attributes filter left to right. — [AWS What's New](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-dynamodb-multi-attribute-composite-keys-global-secondary-indexes/)

### Inferences
- Frame secondary indexes with Kleppmann's split. Local (document-partitioned) indexes, such as Cassandra SAI and DynamoDB LSIs, mean scatter-gather reads. Global (term-partitioned) indexes, such as DynamoDB GSIs, mean asynchronous index updates and stale index reads. That is the trade-off students need, and it explains why Cassandra still pushes query-first tables.
- "R + W > N" deserves a deliberate counterexample. With sloppy quorum and hinted handoff, the W writes may land outside the R home replicas, so overlap is not guaranteed. Dynamo §4.6 plus Abadi p.40 support teaching this.
- Abadi's 2012 MongoDB "PA/EC" label is a period piece. MongoDB now defaults to `w: "majority"` (see §4), which narrows the rollback window. Use it to show that PACELC labels describe configurations and change over time.

### Gaps
- Cassandra's current default `num_tokens` (I believe 16 since 4.0, with the allocator), `tombstone_warn_threshold` (1000) and `tombstone_failure_threshold` (100000) defaults: background knowledge, not on the pages I fetched. Verify in cassandra.yaml docs.
- I did not fetch a primary source for CRDTs (Shapiro et al. 2011, crdt.tech) or for Kleppmann's local/global index terminology. The DDIA O'Reilly page returned 403.
- DynamoDB GSI vs LSI specifics (GSIs eventually consistent only; LSIs defined at table creation; 10 GB item-collection limit with LSIs): background knowledge. Verify in the DynamoDB Developer Guide.
- The (N,R,W) = (3,2,2) "common configuration" is widely quoted from Dynamo §6. I verified only "typical value of N ... is 3" on p.214.

---

## 3. Access-pattern-first data modeling (DynamoDB single-table, Cassandra query-first, MongoDB embed vs reference)

### Takeaway
All three lead stores tell you to start from queries, not entities. DynamoDB pre-joins item collections under a shared partition key. Cassandra builds one denormalized table per query. MongoDB embeds what is read and updated together and references what is unbounded or independent. The skill to teach is turning an access-pattern list into keys.

### Cited Findings
- **DynamoDB single-table (DeBrie, 2020-02-05)**:
  - DynamoDB has no joins, so related heterogeneous items are "pre-joined" into item collections, meaning items sharing a partition key, and fetched with one `Query`. The main benefit is retrieving multiple item types in one request; operational and cost benefits are "marginal".
  - Downsides: a steep learning curve, inflexibility for new access patterns (may need an ETL to rewrite items), and analytics pain. A single table looks "more like machine code than a simple spreadsheet".
  - Exceptions: new apps that value flexibility, and GraphQL, because resolvers issue separate calls anyway.

  — [Alex DeBrie: single-table design](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- DynamoDB Enhanced Client (AWS SDK for Java 2.x) is "the successor to the `DynamoDBMapper` class" of SDK v1. It includes an Enhanced Document API for schemaless items, async usage, extensions and annotations. — [AWS SDK for Java 2.x: Enhanced Client](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/dynamodb-enhanced-client.html)
- **Cassandra query-first**:
  - "In Cassandra, data modeling is query-driven."
  - "Queries are best designed to access a single table."
  - "joins are not supported in Cassandra so all required fields (columns) must be grouped together in a single table."
  - "Data duplication and a high write throughput are used to achieve a high read performance."
  - "Using clustering keys to sort data makes retrieval of adjacent data more efficient."
  - "queries using LWT should be kept to the minimum."
  - Materialized views are "experimental" as of 4.0.

  — [Cassandra data modeling intro](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html)
- **ALLOW FILTERING**: "By default, CQL only allows select queries that don't involve a full scan of all partitions." Filtering queries have performance that "can be unpredictable". The example `SELECT * FROM users WHERE birth_year = 1981 AND country = 'FR'` needs `ALLOW FILTERING`, which the docs advise only for datasets known to be small. — [CQL DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html)
- **MongoDB embed vs reference**:
  - Embed when there is a "'has-a' or 'contains' relationship", when the app "queries pieces of information together", or when data is "often updated together".
  - Reference when "the child side of the relationship has high cardinality", when "embedded data grows without bounds", when data is "written at different times in a write-heavy workload", or when the child "can exist by itself".
  - Embedding "allows atomic operations". "In most cases, a distributed transaction incurs a greater performance cost over single document writes... the denormalized data model (embedded documents and arrays) will continue to be optimal."

  — [MongoDB: embedding vs references](https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/)
- MongoDB 9.0 adds a `constraint` schema-validation level: rules apply to inserts and updates, and every document must satisfy them. — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)

### Inferences
- **Payments domain** to reuse across all stores (concrete lab spec):
  - Entities: Customer, Account, Payment, Merchant, Refund, IdempotencyKey, LedgerEntry.
  - Access patterns:
    - AP1: get account with recent payments, newest first.
    - AP2: get payment by id.
    - AP3: list a merchant's payments by status and time.
    - AP4: idempotent payment create.
    - AP5: atomic transfer between two accounts with ledger entries.
    - AP6: refunds for a payment.
  - DynamoDB single table:
    - `PK=ACCT#<id>`, `SK=META` / `SK=PAY#<ts>#<payId>` (AP1).
    - GSI1 `PK=PAY#<id>` (AP2).
    - GSI2 on merchantId and status+createdAt for AP3, now possible with multi-attribute GSI keys and no synthetic key.
    - `PK=IDEMP#<key>` written with `attribute_not_exists(PK)` plus a TTL attribute (AP4).
    - `TransactWriteItems` for AP5.
  - Cassandra: three tables: `payments_by_account`, `payments_by_merchant_status`, `payment_by_id`.
  - MongoDB: `accounts` with embedded recent-payment summary (bounded), `payments` referenced. Use a transaction or a single-document ledger pattern for transfers.
- For Kotlin users the Enhanced Client's bean-style annotations clash with data classes. The immutable-class/builder route (`@DynamoDbImmutable`) or a hand-written `TableSchema` is the practical choice. Verify the current annotation set in the linked docs before writing lesson code.

### Gaps
- DeBrie has newer writing (The DynamoDB Book, later posts) that may soften the single-table stance. I verified only the 2020 post, which says he remains "a strong proponent of single-table design in DynamoDB in most use cases".
- I did not verify Kotlin-specific guidance for the Enhanced Client.

---

## 4. Transactions in NoSQL (MongoDB, DynamoDB, Cassandra LWT/Paxos and Accord)

### Takeaway
All four lead stores now have transactions, with different scopes:
- DynamoDB: up to 100 items / 4 MB, serializable, single Region.
- MongoDB: multi-document snapshot transactions, 60 s default lifetime, best with snapshot/majority.
- Cassandra 5.0: single-partition LWT (Paxos) only.
- Cassandra 6.0 (alpha): Accord, which adds multi-partition, multi-table strict-serializable transactions behind `BEGIN TRANSACTION … COMMIT TRANSACTION`, opted into per table.

Jepsen's 2020 MongoDB report is the cautionary tale.

### Cited Findings
- **DynamoDB**:
  - `TransactWriteItems` groups "up to 100 write actions" over up to 100 distinct items in one or more tables, same account and Region. The aggregate size is ≤ 4 MB. Actions are Put, Update, Delete and ConditionCheck, and two actions cannot target the same item.
  - Idempotent via a client token, valid for 10 minutes after the request finishes. A different payload with the same token raises `IdempotentParameterMismatch`.
  - Serializable against single-item ops. Read-committed against `BatchGetItem`, `Query` and `Scan`.
  - Every item costs two underlying reads or writes (prepare and commit), even when the transaction is cancelled.
  - Conflicts raise `TransactionCanceledException` with `CancellationReasons`.
  - In global tables, ACID holds "only within the AWS Region where the write API was invoked".
  - Stream consumers "shouldn't assume transaction atomicity or ordering guarantees".

  — [DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- **MongoDB**:
  - Default transaction runtime is under one minute (`transactionLifetimeLimitSeconds`). The 16 MB total-size limit is gone, but each oplog entry is still ≤ 16 MB.
  - Cache pressure aborts with a write conflict or `TransactionTooLargeForCache`.
  - Minimum FCV is 4.0 for replica sets and 4.2 for sharded clusters.

  — [MongoDB transactions production considerations](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/)
- MongoDB 9.0 caps concurrently open multi-document transactions from external clients at 10,000 (`maxConcurrentMultiDocumentTransactions`). Beyond that you get `TooManyOpenTransactions`. — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)
- MongoDB's implicit default write concern is `w: "majority"`. The exception is `{w:1}` when arbiters exist and non-arbiters ≤ voting majority, e.g. a PSA set. Inside a transaction, the transaction's write concern applies to the commit. — [MongoDB defaults](https://www.mongodb.com/docs/manual/reference/mongodb-defaults/)
- **Jepsen MongoDB 4.2.6** (2020-05-15):
  - Transactions ignored DB/collection-level concerns and fell back to `local`/`w:1`, losing acknowledged writes under partitions.
  - `snapshot` read concern did not give snapshot reads unless paired with `w: majority`.
  - Read skew (G-single), G1c cycles and duplicated writes appeared even at the strongest settings.
  - Recommendation: set read and write concern explicitly per transaction (`snapshot` + `majority`).
  - MongoDB attributed the anomalies to a retry bug (SERVER-48307), with a fix scheduled for 4.2.8.

  — [Jepsen: MongoDB 4.2.6](https://jepsen.io/analyses/mongodb-4.2.6)
- **Cassandra LWT**: `INSERT … IF NOT EXISTS` and `UPDATE/DELETE … IF` "incur a non-negligible performance cost, because Paxos is used". — [CQL DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html)
- **Cassandra 6 / Accord** (Instaclustr, 2026-04-24):
  - 6.0-alpha1 is out and GA is pending. "Strict serializable isolation across multiple partitions and tables." Leaderless: any node can coordinate.
  - Usually one consensus round trip.
  - Syntax is `BEGIN TRANSACTION` … `LET` … `IF … THEN … END IF` … `COMMIT TRANSACTION`, and "may evolve before general availability".
  - Requires the Cluster Metadata Service (CEP-21 / TCM). On upgrade you run `nodetool cms initialize`, which is "not easily reversible". CMS needs at least 3 nodes for quorum, and mixed-version clusters are not supported.
  - Existing LWT syntax keeps working.

  — [Instaclustr: Cassandra 6 Accord](https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/)
- **Accord opt-in per table** (draft Cassandra 6 docs, "Preview"):
  - Set `accord.enabled: true` in cassandra.yaml, then `ALTER TABLE … WITH transactional_mode = 'full'`.
  - Modes: `off` (Paxos; transaction statements rejected), `mixed_reads`, `full`.
  - Migration runs in two phases via `nodetool consensus_admin` and repairs.
  - LOCAL, TWO and THREE consistency levels are unsupported, and hints are not written for Accord writes.

  — [Cassandra 6 docs preview: Onboarding to Accord](https://pmcfadin.github.io/cassandra6-docs-workzone/operators/draft/upgrade/onboarding-to-accord.html)
- Docker Hub has a `cassandra:6.0-alpha2` tag. — [Docker Hub cassandra](https://hub.docker.com/_/cassandra)
- A July 2026 secondary source said only alpha1 was on the download page then. My fetch of the download page (Nov 2026) lists only 5.0/4.1/4.0 as GA lines. — [Cassandra downloads](https://cassandra.apache.org/_/download.html); [search result: The New Stack / youngju.dev](https://thenewstack.io/apache-cassandra-6-features/)

### Inferences
- Teach Accord as "the direction of travel, runnable in an optional lab on the 6.0-alpha2 image". Do not make it core, because the syntax may change before GA. Core Cassandra transactions content stays LWT/Paxos on 5.0.x.
- The DynamoDB per-item prepare+commit cost, plus Jepsen's MongoDB findings, makes a strong "transactions exist, but they cost something and have fine print" lesson.

### Gaps
- Paxos v2 for LWT (Cassandra 4.1+): background knowledge, not verified this session.
- Whether MongoDB fixed every Jepsen 4.2.6 finding: the report only records the planned 4.2.8 patch.
- An official Apache announcement and date for 6.0-alpha2, and any 6.0 beta/GA timeline: not found. theconsensus.dev's Aug 2026 article returned 403.

---

## 5. Current versions and ecosystem status (as of November 2026) and Java/Kotlin drivers

### Takeaway
Course-relevant versions:
- MongoDB: 9.0 (GA 2026-09-28).
- Cassandra: 5.0.9 GA; 6.0 alpha (Docker tag 6.0-alpha2).
- Neo4j: 2026.10.x on calendar versioning; 5.26 is LTS.
- DynamoDB: native vector search (GA Aug 2026), multi-Region strong consistency (GA Jun 2025), multi-attribute GSI keys (Nov 2025).
- LocalStack now needs an auth token (2026.03.0). DynamoDB Local v3.x is the friction-free lab choice.
- Elasticsearch: AGPLv3 source option since 2024.
- ScyllaDB: source-available from 2025.1.
- InfluxDB 3 Core: GA (MIT/Apache).

### Cited Findings

**MongoDB**
- Release notes list 9.0 as "Current Stable Release", 9.1 as "Upcoming", and 8.3 / 8.0 / 7.0 as previous stable releases. — [MongoDB release notes](https://www.mongodb.com/docs/manual/release-notes/)
- 9.0.0 is dated 2026-09-28, with patch 9.0.4 on 2026-10-13. Highlights:
  - Per-operation memory limit (≥ 1 GB or 20% of RAM).
  - Server-side JavaScript un-deprecated and running on a WASM engine.
  - BSON validated on ingest by default.
  - `constraint` validation level.
  - `$queryStats` on by default (1% sampling).
  - Time-series collections stored as a single namespace.
  - Queryable Encryption prefix/suffix/substring queries GA.
  - `mongocryptd` deprecated.

  — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)
- MongoDB marketing claims "up to 2x higher throughput" for 9.0. This is a vendor claim with no independent benchmark found. — [MongoDB version-release page (search result)](https://www.mongodb.com/products/updates/version-release)
- 8.2 is a minor release (Atlas plus on-prem) that includes 8.1's changes. Its notes warn that MongoDB is incompatible with Linux kernels 6.19 through 7.0.13. — [MongoDB 8.2 release notes (search result)](https://www.mongodb.com/docs/manual/release-notes/8.2/)
- Docker install docs use `mongodb/mongodb-community-server:9.0-ubi9-slim`. A single-node replica set is started with `--replSet myReplicaSet`. MongoDB 5.0+ images need AVX on x86. — [MongoDB Community with Docker](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/)
- **Java driver 5.14.0** (2026-10-28) raises the max wire version to 29 for MongoDB 9.0. 5.12.0 added support for 9.0's Intelligent Workload Management. It also sends `afterClusterTime` on writes in causally consistent sessions (JAVA-6179). — [mongo-java-driver releases](https://github.com/mongodb/mongo-java-driver/releases)
- The Kotlin coroutine driver artifact is `org.mongodb:mongodb-driver-kotlin-coroutine`. Sonatype showed a 5.7.0-alpha0 pre-release and dependency trackers showed 5.6.0. Sources conflicted and were stale. — [Sonatype (search result)](https://central.sonatype.com/artifact/org.mongodb/mongodb-driver-kotlin-coroutine)

**Apache Cassandra**
- Downloads page (Nov 2026):
  - 5.0.9 (2026-08-07) is "Latest GA", maintained until 8.0.
  - 4.1.12, maintained until 7.0.
  - 4.0.21, maintained until 6.0.
  - Java Driver 4.x is 4.19.4 (2026-10-14).

  — [Cassandra downloads](https://cassandra.apache.org/_/download.html)
- Docker Hub tags: `6.0`, `6.0-alpha2`; `5.0.9`, `5.0`, `5`, `latest`; `4.1.12`; `4.0.21`. Architectures include arm64v8. — [Docker Hub cassandra](https://hub.docker.com/_/cassandra)
- 5.0 features:
  - SAI
  - Trie memtables and SSTables
  - JDK 17
  - Vector type and similarity functions
  - Unified Compaction Strategy
  - Dynamic Data Masking
  - Math functions
  - More guardrails
  - `sstablepartitions`

  The docs site's "latest" now links to 6.0-alpha2 docs, and its version labels are confusing. — [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html)
- Cassandra 6: Accord and TCM/CMS. 6.0-alpha1 shipped April 2026. — [Instaclustr](https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/); [The New Stack (search result)](https://thenewstack.io/apache-cassandra-6-features/)
- **Java driver** is now Apache-hosted (github.com/apache/cassandra-java-driver, Apache-2.0, "© The Apache Software Foundation").
  - Maven: `org.apache.cassandra:java-driver-core`, plus `java-driver-query-builder` (now a separate artifact) and `java-driver-mapper-runtime`.
  - Supports Cassandra 2.1+ and requires Java 8+.
  - The README still references 4.17.0 docs and lags the 4.19.4 release.

  — [apache/cassandra-java-driver](https://github.com/apache/cassandra-java-driver)

**ScyllaDB**
- "ScyllaDB OSS AGPL 6.2 will stand as the final OSS AGPL release". Enterprise moves from closed source to source-available from 2025.1. It is free with a 10 TB total-storage limit. Scylla Manager moves to AGPL. — [ScyllaDB licensing FAQ (search result)](https://www.scylladb.com/source-available-faq); [ScyllaDB blog 2024-12-18 (search result)](https://www.scylladb.com/2024/12/18/license/)
- Jepsen tested Scylla 4.2-rc3 (2020-12-23). — [Jepsen analyses](https://jepsen.io/analyses)

**Neo4j**
- Calendar versioning (YYYY.MM.PATCH) since January 2025. Cypher is versioned separately: Cypher 5 has been frozen since 2025.06, and new features go only to Cypher 25. From 2026.02 the distributed `neo4j.conf` sets `db.query.default_language=CYPHER_25`. — [Neo4j versioning blog (search result)](https://neo4j.com/blog/developer/neo4j-graph-database-versioning/); [Neo4j Ops Manual intro (search result)](https://neo4j.com/docs/operations-manual/current/introduction/)
- 2026.10.0 was released 2026-10-20 and 2026.10.1 on 2026-10-23. Notice: the legacy Browser is removed in 2026.11.0, and after the next LTS the minimum password length rises from 8 to 16. — [Neo4j 2026.10 release notes (search result)](https://neo4j.com/release-notes/database/neo4j-2026-10/)
- Docker:
  - Community is the unsuffixed tag, e.g. `neo4j:2026.10.2`. Enterprise is `-enterprise` and needs `NEO4J_ACCEPT_LICENSE_AGREEMENT=yes`.
  - `NEO4J_AUTH=neo4j/<pw>` or `none`. Ports 7474 (HTTP/Browser) and 7687 (Bolt).
  - Docs mark 2026.10 as "Current", with 5.26 LTS and 4.4 also listed.

  — [Neo4j Docker introduction](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
- Docker defaults: heap max and page cache are deliberately small (512M each). The env-var rule turns `.` into `_` and `_` into `__`, e.g. `NEO4J_server_memory_heap_max__size`. — [Neo4j Docker configuration 2026.06 (search result)](https://neo4j.com/docs/operations-manual/2026.06/docker/configuration/)
- **Neo4j Java driver**: latest 6.3.0 (released 24 Sep, year not shown; almost certainly 2026), on the 6.x line. Adds driver-side property encryption. 6.2.0 added Bolt 6.1 and UUID handling; 6.1.0 added automatic retries for auto-commit queries. — [neo4j-java-driver releases](https://github.com/neo4j/neo4j-java-driver/releases)

**DynamoDB, DynamoDB Local, LocalStack**
- Multi-Region strong consistency (MRSC) global tables went GA 2025-06-30. The consistency mode is fixed at creation, and MRSC gives zero RPO. — [AWS What's New 2025-06 (search result)](https://aws.amazon.com/about-aws/whats-new/2025/06/amazon-dynamo-db-global-tables-multi-region-strong-consistency-generally-available/)
- Multi-attribute composite GSI keys: 2025-11-19. — [AWS What's New](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-dynamodb-multi-attribute-composite-keys-global-secondary-indexes/)
- 2026 additions (search results): MRSC fault-injection testing (Jan), multi-account global tables (Feb), Resource Control Policies (Feb). — [AWS What's New 2026-02 (search result)](https://aws.amazon.com/about-aws/whats-new/2026/02/dynamodb-gt-multi-account)
- **DynamoDB vector search GA 2026-08-05**: index and search embeddings stored as attributes with approximate nearest neighbour search, "single-digit millisecond latency at 99%+ recall". Available in all commercial and GovCloud Regions. — [AWS What's New](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-dynamodb-vector-search/)
- **DynamoDB Local**:
  - Versions: v3.x (Current), v2.x (Legacy), v1.x (Deprecated). v3 changes imports to `software.amazon.dynamodb`.
  - Maven: `software.amazon.dynamodb:DynamoDBLocal:3.3.2`. Needs JRE 17+ from v2.6.0.
  - Docker image `amazon/dynamodb-local:latest` on port 8000, with dummy credentials and `--endpoint-url http://localhost:8000`.

  — [DynamoDB Local docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html)
- **LocalStack 2026.03.0** (2026-03-23): "an auth token or CI auth token is required to start LocalStack for AWS". `localstack/localstack` and `localstack/localstack-pro` are now the same image. A free Hobby plan exists for non-commercial use. The temporary bypass expired 2026-04-06. — [LocalStack blog](https://blog.localstack.cloud/localstack-for-aws-release-2026-03-0/)

**Search: Elasticsearch / OpenSearch**
- On 2024-08-29 Elastic added AGPLv3 as a source-license option alongside SSPL 1.0 and ELv2, expected "before the 8.16 release is generally available". The "default distribution continues to be open source under the Elastic License 2.0". — [Elastic licensing FAQ](https://www.elastic.co/pricing/faq/licensing); [Business Wire 2024-08-29 (search result)](https://www.businesswire.com/news/home/20240829537786/en)
- OpenSearch joined the Linux Foundation (OpenSearch Software Foundation) in Sept 2024. OpenSearch 3.3 shipped 2025-10-14. — [OpenSearch blog 3.3 (search result)](https://opensearch.org/blog/explore-opensearch-3-3/)
- Latest versions are uncertain. Elasticsearch 9.4.3 per isitpatched.com (synced 2026-07-29). OpenSearch 3.9.0 (2026-09-29) per a single Japanese article, which also names 3.6 and 2.19 as LTS lines. — [isitpatched (search result)](https://isitpatched.com/elasticsearch); [issoh.co.jp (search result)](https://www.issoh.co.jp/md/tech/6592)

**Time-series**
- InfluxDB 3 Core and Enterprise went GA 2025-04-15. Core is MIT/Apache 2. Built in Rust on Apache Arrow, DataFusion, Parquet and Flight, with an embedded Python processing engine. — [InfluxData blog (search result)](https://www.influxdata.com/blog/influxdb-3-OSS-GA/)
- Timescale renamed itself Tiger Data on 2025-06-17. The extension is still TimescaleDB. Core is Apache 2.0, and extra features are source-available under the Timescale License. — [Tiger Data blog (search result)](https://www.tigerdata.com/blog/timescale-becomes-tigerdata)

**Vector**
- pgvector v0.8.7 supports Postgres 13+ (Docker tags pg13–pg18) and both HNSW and IVFFlat.
  - HNSW parameters: `m`=16, `ef_construction`=64, `hnsw.ef_search`=40.
  - IVFFlat: `lists` ≈ rows/1000 up to 1M rows; `probes`=1 by default.
  - Operators: `<->` L2, `<#>` negative inner product, `<=>` cosine, `<+>` L1.
  - Iterative index scans since 0.8.0.
  - `vector` indexes up to 2,000 dims and `halfvec` up to 4,000.
  - Docker image: `pgvector/pgvector`.

  — [pgvector GitHub](https://github.com/pgvector/pgvector)
- Milvus 2.6 (June 2025) added the Woodpecker WAL, which removes the Kafka/Pulsar dependency, plus RaBitQ 1-bit quantization. Qdrant's current version is unclear (1.17 vs 1.18 claims). — [dio.me (search result)](https://www.dio.me/en/articles/vector-database-em-2026-o-que-mudou-nas-releases-aa9ff5545027)

**Books**
- *Designing Data-Intensive Applications*, 2nd ed., Kleppmann & Chris Riccomini (O'Reilly). Published Feb 2026 per O'Reilly's listing month; retailer dates range from 2026-02-27 to 2026-03-31. Print ISBN 9781098119065. — [Readings (search result)](https://www.readings.com.au/product/9781098119065/designing-data-intensive-applications--martin-kleppmann-chris-riccomini--2026--9781098119065); the O'Reilly page returned 403.

### Inferences
- **Pin versions in labs**: `cassandra:5.0.9`, `mongodb/mongodb-community-server:9.0-ubi9-slim` (or `mongo:9.0` if multi-arch is confirmed), `neo4j:2026.10.2`, `amazon/dynamodb-local:latest` (v3.x), `pgvector/pgvector:pg17` or `pg18`, `cassandra:6.0-alpha2` for the optional Accord lab only.
- **Recommended driver set**:
  - MongoDB: Java/Kotlin coroutine driver 5.14.x, same repo and version line (verify the Kotlin artifact version).
  - Cassandra: `org.apache.cassandra:java-driver-core:4.19.4`.
  - Neo4j: Java driver 6.3.x.
  - DynamoDB: AWS SDK for Java 2.x `dynamodb-enhanced`.
- Drop LocalStack from required labs. DynamoDB Local covers the DynamoDB API with no account. Mention LocalStack Hobby as optional.
- DynamoDB's 2026 vector search and Cassandra 5.0's vector type support a useful teaching point: vector search is turning into a feature of general-purpose stores rather than a separate product category.

### Gaps
- The exact current Kotlin coroutine driver version; whether `mongodb/mongodb-community-server:9.0-ubi9-slim` publishes arm64. The `mongo` official image is believed multi-arch: verify with `docker manifest inspect`.
- Whether MongoDB 9.0 Community includes Search/Vector Search (MongoDB announced a Community preview in 2025, per background knowledge): not verified.
- Whether DynamoDB Local supports vector search, MRSC or multi-attribute GSI keys: not stated. Assume not until tested.
- ScyllaDB's current release number (2025.x/2026.x) was not verified.
- Exact latest OpenSearch/Elasticsearch, Qdrant and Milvus versions: only secondary or conflicting sources.
- InfluxDB 3 Core's limits for long-range queries: not verified.
- I did not verify which Docker Desktop VM kernel versions fall inside MongoDB's 6.19–7.0.13 incompatibility window.

---

## 6. Misconceptions to address (with evidence)

### Takeaway
Each common misconception has a primary source that refutes it. Assign the source as reading so students see the evidence themselves rather than taking the instructor's word.

### Cited Findings
- **"NoSQL means no schema."**
  - DynamoDB requires a key schema.
  - Cassandra tables have typed columns, and its modeling docs are all about primary-key design. — [Cassandra data modeling](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html)
  - MongoDB 9.0 adds a `constraint` validation level and validates BSON on ingest by default. — [MongoDB 9.0](https://www.mongodb.com/docs/manual/release-notes/9.0/)
- **"NoSQL doesn't support transactions."**
  - DynamoDB: 100-item ACID transactions. — [DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
  - MongoDB: multi-document transactions. — [MongoDB transactions](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/)
  - Cassandra: Paxos LWT, with Accord in 6.0. — [Instaclustr](https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/)
- **"CAP means pick any two."** Abadi says CAP "only posits limitations in the face of certain types of failures, and does not constrain any system capabilities during normal system operation". The latency/consistency trade-off "is present at all times during system operation". — [Abadi](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- **"Eventual consistency means data is lost."** Eventual consistency concerns visibility and convergence. Hinted handoff, read repair and Merkle anti-entropy exist to converge replicas. — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
  - Loss does happen through specific mechanisms: LWW discarding concurrent writes, and clock skew. — [Cassandra docs: Dynamo](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)
  - Merges can resurrect deleted items. — [Dynamo §4.4](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
  - With weak write concern, acknowledged writes were lost under partitions in Jepsen's test. — [Jepsen MongoDB 4.2.6](https://jepsen.io/analyses/mongodb-4.2.6)
  - Tombstones expiring before repair produce zombies. — [Cassandra tombstones](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html)
- **"MongoDB is always faster than Postgres."** MongoDB's own docs say "a distributed transaction incurs a greater performance cost over single document writes". Speed depends on the data model fitting the access pattern. — [MongoDB embedding vs references](https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/)
  - Vendor throughput claims (e.g. "2x" for 9.0) are not independent benchmarks. — [MongoDB version-release (search result)](https://www.mongodb.com/products/updates/version-release)
- **Treating Cassandra like an RDBMS (ALLOW FILTERING, secondary-index-everything, joins).** CQL rejects full-partition scans by default because the performance "can be unpredictable". — [CQL DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html)
- **Large partitions and tombstone storms.**
  - Keep partitions under 100k values and 100 MB. — [Cassandra data modeling](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html)
  - Deletes and TTLs write tombstones that live at least `gc_grace_seconds` (10 days). — [Cassandra tombstones](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html)
  - Cassandra 5.0's `sstablepartitions` finds large partitions. — [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html)
- **"Quorum = strong consistency."** "Simply using a quorum protocol is not sufficient to guarantee consistency to the level defined by Gilbert and Lynch." — [Abadi p.40](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- **"Single-table design is always right."** DeBrie himself lists exceptions: flexibility-first new apps and GraphQL. — [DeBrie](https://www.alexdebrie.com/posts/dynamodb-single-table/)

### Inferences
- **"DynamoDB is Dynamo."** This is a misconception worth a sidebar. DynamoDB keeps Dynamo's name and partitioning ideas but offers strongly consistent reads and transactions, so it does not behave like the leaderless Dynamo paper system. Cite the 2022 USENIX ATC DynamoDB paper (see Gaps).
- Queue-like workloads in Cassandra (insert then delete) are the classic way to create a tombstone storm. They make a good "what not to do" lab.

### Gaps
- I did not fetch the 2022 USENIX ATC paper "Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service" (Elhemali et al.). Verify the Multi-Paxos-per-partition description before teaching it.
- I found no neutral, current MongoDB vs Postgres benchmark. Leave that claim as "it depends on fit" rather than quoting numbers.

---

## 7. Lab environment: Docker on macOS (Apple Silicon)

### Takeaway
Everything runs locally for free:
- 3-node Cassandra 5.0.9 with explicit small heaps and staggered start.
- 3-member MongoDB 9.0 replica set.
- Neo4j 2026.10 Community.
- DynamoDB Local v3.

Budget about 8–10 GB for Docker Desktop and run one stack at a time, using compose profiles. The main Mac pitfalls are Cassandra OOMs (exit 137) when heaps are left at default, nodes joining simultaneously, and MongoDB replica-set hostnames not resolving from the host.

### Cited Findings
- **Cassandra image**:
  - Official `cassandra` image supports arm64v8.
  - Environment variables: `CASSANDRA_SEEDS`, `CASSANDRA_CLUSTER_NAME` (must match), `CASSANDRA_NUM_TOKENS`, `CASSANDRA_DC`, `CASSANDRA_RACK`. DC and rack only apply when `CASSANDRA_ENDPOINT_SNITCH=GossipingPropertyFileSnitch`.
  - A node with an empty data dir won't accept connections until initialization finishes, which can break Compose setups that start all containers at once.

  — [Docker Hub cassandra](https://hub.docker.com/_/cassandra)
- **Cassandra memory on Mac**:
  - The docker-library maintainers diagnosed a 3-node cluster on a Mac where the seed exited when node 3 joined: "By default Cassandra will use 40-50% of total memory. You'll want to set MAX_HEAP_SIZE and HEAP_NEWSIZE." The reporter fixed it with a 512m heap.
  - Example compose files use `MAX_HEAP_SIZE=256M`/`HEAP_NEWSIZE=24M` or 400M/48M. Exit code 137 means the OOM killer ran.
  - Nodes must not join simultaneously (`cassandra.consistent.rangemovement`).
  - Setting `JVM_OPTS` with -Xms/-Xmx can break `nodetool`.

  — [docker-library/cassandra#144 (search result)](https://github.com/docker-library/cassandra/issues/144); [docker-library/cassandra#172 (search result)](https://github.com/docker-library/cassandra/issues/172); [gist 3-node compose (search result)](https://gist.github.com/glenux/0d6663ee377c128334d5309e89bf6c1b)
- **MongoDB image**: `mongodb/mongodb-community-server:9.0-ubi9-slim`, with `--replSet <name>` appended to the command. — [MongoDB Docker install](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/)
- **Neo4j image**: `neo4j:2026.10.2` (Community), `NEO4J_AUTH`, ports 7474/7687. Default heap and page cache are 512M each. Config env vars follow the double-underscore rule, and APOC is enabled with `NEO4J_PLUGINS='["apoc"]'`. — [Neo4j Docker intro](https://neo4j.com/docs/operations-manual/current/docker/introduction/); [Neo4j Docker config (search result)](https://neo4j.com/docs/operations-manual/2026.06/docker/configuration/)
- **DynamoDB Local**: `amazon/dynamodb-local:latest`, `command: "-jar DynamoDBLocal.jar -sharedDb -dbPath ./data"` (or `-inMemory`), port 8000, fake credentials. — [DynamoDB Local docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html)
- **LocalStack** now needs an auth token, even on the free Hobby tier. — [LocalStack 2026.03.0](https://blog.localstack.cloud/localstack-for-aws-release-2026-03-0/)
- **pgvector**: `pgvector/pgvector:pg17` or `pg18`. — [pgvector](https://github.com/pgvector/pgvector)

### Inferences (proposed lab configs; untested, so the lesson writer should run them once)

**Cassandra 3-node (`compose.cassandra.yml`)**, about 1.5 GB per node, roughly 4.5 GB total:
```yaml
x-cass: &cass
  image: cassandra:5.0.9
  mem_limit: 1536m
  environment: &cass-env
    CASSANDRA_CLUSTER_NAME: nosql-lab
    CASSANDRA_SEEDS: cass1
    CASSANDRA_ENDPOINT_SNITCH: GossipingPropertyFileSnitch
    CASSANDRA_DC: dc1
    CASSANDRA_RACK: rack1
    CASSANDRA_NUM_TOKENS: 16        # verify default; 16 is the modern recommendation
    MAX_HEAP_SIZE: 768M
    HEAP_NEWSIZE: 128M
  healthcheck:
    test: ["CMD-SHELL", "cqlsh -e 'describe keyspaces' >/dev/null 2>&1"]
    interval: 15s
    timeout: 10s
    retries: 20
    start_period: 60s
services:
  cass1: { <<: *cass, hostname: cass1, ports: ["9042:9042"] }
  cass2: { <<: *cass, hostname: cass2, depends_on: { cass1: { condition: service_healthy } } }
  cass3: { <<: *cass, hostname: cass3, depends_on: { cass2: { condition: service_healthy } } }
```
- Create the keyspace with `NetworkTopologyStrategy {'dc1': 3}`.
- Use `docker compose stop cass3` or `docker compose pause cass3` to simulate failure. `pause` freezes the process, which is closer to a partition or GC pause.

**MongoDB 3-member replica set**, about 0.75 GB each:
- Three services `mongo1..3`, each running `--replSet rs0 --bind_ip_all --port 2701X --wiredTigerCacheSizeGB 0.25`, with distinct host ports 27017/27018/27019 and `mem_limit: 768m`.
- Initiate from inside the network:
  ```js
  rs.initiate({_id:"rs0",members:[{_id:0,host:"mongo1:27017"},{_id:1,host:"mongo2:27018"},{_id:2,host:"mongo3:27019"}]})
  ```
- Mac gotcha: the driver discovers members by the hostnames in the replica-set config, so `mongo1` must resolve from the host. Fix it with either:
  - (a) running the JVM app or tests inside the compose network, or
  - (b) adding `127.0.0.1 mongo1 mongo2 mongo3` to `/etc/hosts`.

  Use `directConnection=true` only for single-node work.
- Check the Docker VM kernel (`docker run --rm alpine uname -r`) against MongoDB's 6.19–7.0.13 incompatibility warning.

**Neo4j**, about 1.5 GB:
- `neo4j:2026.10.2` with `NEO4J_AUTH=neo4j/<test-password>`.
- `NEO4J_server_memory_heap_max__size=1G`, `NEO4J_server_memory_pagecache_size=512M`, `NEO4J_PLUGINS='["apoc"]'`.
- `mem_limit: 2g`.

**DynamoDB Local**, about 0.5 GB:
- `amazon/dynamodb-local:latest` with `-jar DynamoDBLocal.jar -sharedDb -inMemory`.
- Java SDK v2: `DynamoDbClient.builder().endpointOverride(URI.create("http://localhost:8000")).region(Region.US_EAST_1)` with static dummy credentials.
- For unit tests, embed the `DynamoDBLocal:3.3.2` Maven artifact or use Testcontainers.

**Docker Desktop**: set memory to 8–10 GB. Use compose `profiles` (`cassandra`, `mongo`, `neo4j`, `dynamo`, `search`, `vector`) so only one heavy stack runs at a time.

### Gaps
- None of the compose snippets above were executed this session. Healthcheck commands, `MAX_HEAP_SIZE` handling in the 5.0 image's `cassandra-env.sh`, and `pause` vs `stop` behaviour need a dry run.
- arm64 availability for the `mongodb/mongodb-community-server` UBI image and the `neo4j` image was not confirmed on the fetched pages.
- `nodetool` subcommands for hints (`listpendinghints`) and the exact `tablestats` tombstone fields were not verified this session.

---

## 8. Proposed lesson outline (12 lessons, 1–2 labs each)

### Takeaway
Twelve lessons. Each core concept is paired with the store where it is most visible, and one payments domain runs through every lab so that students compare models rather than relearn a domain.

### Cited Findings (anchors per lesson)

| # | Lesson | Primary sources | Labs |
|---|---|---|---|
| 1 | Why NoSQL: Bigtable and Dynamo; the families map; NoSQL vs relational | [Bigtable](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/), [Dynamo](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf), [Abadi](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf) | (a) Bring up the polyglot compose with profiles and store one Payment in DynamoDB Local, MongoDB, Cassandra and Neo4j from a Kotlin CLI. (b) Write the payments access-pattern list (AP1–AP6). |
| 2 | Access-pattern-first modeling (cross-store) | [DeBrie](https://www.alexdebrie.com/posts/dynamodb-single-table/), [Cassandra modeling](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html), [Mongo embed/ref](https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/) | Paper exercise: turn AP1–AP6 into a DynamoDB key table, three Cassandra tables and a MongoDB schema. Peer-review for unbounded arrays and hot keys. |
| 3 | Key-value and DynamoDB fundamentals: PK/SK, item collections, GSIs/LSIs, RCU/WCU, conditional writes, TTL | [Partition-key BP](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html), [Enhanced Client](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/dynamodb-enhanced-client.html), [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html) | (a) Enhanced Client CRUD on DynamoDB Local. (b) Idempotent payment create with `attribute_not_exists` and an expiry attribute. |
| 4 | DynamoDB single-table design and transactions | [DeBrie](https://www.alexdebrie.com/posts/dynamodb-single-table/), [Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html), [Multi-attr GSI](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-dynamodb-multi-attribute-composite-keys-global-secondary-indexes/) | (a) Payments single-table: one `Query` returns the account plus its last 20 payments, and a GSI serves merchant-by-status. (b) `TransactWriteItems` transfer (debit with `balance >= :amt` condition, credit, two ledger entries, idempotency item). Replay with the same `ClientRequestToken` and read the `CancellationReasons` on conflict. |
| 5 | Partitioning: hash vs range, consistent hashing, vnodes, hot partitions, rebalancing | [Dynamo §4.2](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf), [Cassandra Dynamo arch](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html), [DynamoDB 3000/1000 limits](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html) | (a) Kotlin consistent-hash ring: compare keys moved when adding a node under `hash mod N`, 1 token per node and 16 vnodes per node; plot the skew. (b) Hot-merchant simulation: write-shard `MERCH#id#<0..9>` and scatter-gather the read. |
| 6 | Replication and quorums: leader-follower vs leaderless, N/R/W, sloppy quorum, hinted handoff, read repair, Merkle trees, gossip | [Dynamo §4.5–4.8](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf), [Cassandra Dynamo arch](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html) | (a) 3-node Cassandra at RF=3. `CONSISTENCY ONE` write; `docker compose stop cass3`; read at ONE vs QUORUM vs ALL (ALL fails). Stop a second node: QUORUM now fails with Unavailable, ONE still works. Restart and watch hints replay, then `TRACING ON` to see digest mismatch and read repair. (b) `nodetool repair` and its Merkle-tree validation in the logs. |
| 7 | Wide-column with Cassandra/ScyllaDB: CQL model, clustering, LSM and compaction (UCS), TTL and tombstones, SAI, ALLOW FILTERING | [CQL DML](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html), [Tombstones](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html), [5.0 What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html) | (a) Tombstone storm: a queue-style table (insert, then delete 50k rows in one partition); `nodetool flush`; `nodetool tablestats` for tombstones per slice; hit the warn/fail thresholds; `sstabledump` to see the markers. (b) Query that needs `ALLOW FILTERING`, rebuilt as a query table and as an SAI index; compare tracing output. Optional: `sstablepartitions` on a deliberately oversized partition. |
| 8 | Document stores with MongoDB: documents, validation, indexes, aggregation, replica sets, read/write concern | [Mongo defaults](https://www.mongodb.com/docs/manual/reference/mongodb-defaults/), [Mongo 9.0](https://www.mongodb.com/docs/manual/release-notes/9.0/), [embed/ref](https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/) | (a) Replica-set failover. A Kotlin coroutine writer inserts with `w:1` in a loop; `docker compose pause mongo1` (primary); watch the election in `rs.status()`. Unpause and find rolled-back `w:1` writes in the rollback directory. Repeat with `w:"majority"` and see none lost. (b) `$jsonSchema` validator with the `constraint` level. |
| 9 | Consistency models, CAP vs PACELC, conflict resolution (LWW, vector clocks, CRDTs) | [Abadi](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf), [Jepsen models](https://jepsen.io/consistency/models), [Dynamo §4.4](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) | (a) LWW clock skew in Cassandra: two writers use `USING TIMESTAMP` with one clock "5 s ahead"; the later real-time write loses. (b) Kotlin version vectors plus a G-Counter/OR-Set CRDT; replay the Dynamo D1→D5 cart example. Optional: causal session in MongoDB (majority/majority) vs default `local`. |
| 10 | Transactions in NoSQL and Jepsen literacy | [DynamoDB txn](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html), [Mongo txn](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/), [Jepsen Mongo 4.2.6](https://jepsen.io/analyses/mongodb-4.2.6), [Accord](https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/) | (a) Cassandra LWT seat booking: 50 concurrent `INSERT … IF NOT EXISTS` from coroutines; exactly one wins. Compare latency with plain inserts. (b) MongoDB transfer transaction with explicit `snapshot` + `majority` and the driver's retry helper. Optional: `cassandra:6.0-alpha2` Accord `BEGIN TRANSACTION` across two tables (marked "alpha, syntax may change"). |
| 11 | Graph with Neo4j and Cypher; GQL | [Neo4j Docker](https://neo4j.com/docs/operations-manual/current/docker/introduction/), [GQL (Wikipedia)](https://en.wikipedia.org/wiki/Graph_Query_Language) | (a) Fraud rings. Load Accounts, Devices, Phones, Addresses and TRANSFERS_TO edges. Find (1) accounts sharing at least 2 identifiers, `MATCH (a1:Account)-[:USES]->(x)<-[:USES]-(a2:Account) WITH a1,a2,count(x) AS shared WHERE shared>=2`, and (2) money cycles, `MATCH p=(a:Account)-[:TRANSFERS_TO*3..6]->(a)`. (b) The same "friends-of-friends within 3 hops" query in SQL (recursive CTE) vs Cypher; compare plans with `PROFILE`. Java driver 6.x `executableQuery`. |
| 12 | Specialized stores and choosing: time-series, search (inverted index), vector (HNSW), decision framework, polyglot persistence | [pgvector](https://github.com/pgvector/pgvector), [Elastic licensing](https://www.elastic.co/pricing/faq/licensing), [DynamoDB vector search](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-dynamodb-vector-search/) | (a) pgvector: 100k embeddings; exact scan vs HNSW at `ef_search` 10/40/200 (recall@10 against latency). (b) OpenSearch single node: `_analyze` API and a term query to show the inverted index; or TimescaleDB hypertable plus `time_bucket`. Close with a decision matrix exercise for five scenarios. |

### Inferences
- If cutting to 10 lessons: merge 3+4 (DynamoDB) and 5+6 (partitioning and replication), and keep the rest.
- The Cassandra CL lab (lesson 6) and MongoDB failover lab (lesson 8) are the two "aha" labs. Protect their time.
- ScyllaDB fits as a drop-in run of the lesson 7 labs (CQL-compatible). Mention its 2024 licence change rather than giving it a separate lab.

### Gaps
- The Cypher queries above are sketches written from Cypher knowledge, not taken from Neo4j docs. Validate them against Cypher 25 / Cypher 5 syntax (e.g. quantified path patterns in Cypher 25).
- OpenSearch and TimescaleDB image tags and memory settings were not researched. Note that OpenSearch's demo config needs `OPENSEARCH_INITIAL_ADMIN_PASSWORD` (background knowledge; verify).

---

## 9. Teaching notes (misconceptions, analogies that work, what to cut)

### Takeaway
Ground each abstraction in a failure students can cause on their laptop. Use the papers' own examples (the shopping cart, the D1→D5 vector clock, the PNUTS "PC/EL" oddity). Cut ops-heavy and legacy material.

### Cited Findings
- Abadi admits PC/EL is "admittedly somewhat confusing... PC does not indicate that the system is fully consistent". Use PNUTS to check whether students have understood PACELC rather than memorized it. — [Abadi p.42](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- DeBrie's line that a single table looks "more like machine code than a simple spreadsheet" helps set expectations. — [DeBrie](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- The Dynamo cart example: "an 'add to cart' operation is never lost. However, deleted items can resurface." — [Dynamo §4.4](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- Jepsen's MongoDB report: defaults matter, and per-transaction settings matter even more. — [Jepsen MongoDB 4.2.6](https://jepsen.io/analyses/mongodb-4.2.6)

### Inferences
**Analogies that work**
- *Consistent hashing*: seats around a round table. A new guest only takes chairs from their immediate neighbours. Vnodes give each guest many raffle tickets spread around the table, so departures spread load evenly.
- *Quorum overlap*: two committees drawn from 3 people. If the write committee has 2 and the read committee has 2, at least one person is on both (pigeonhole). Sloppy quorum is when a temp worker signs for an absent member.
- *Hinted handoff*: a neighbour accepts your parcel and leaves a note. *Read repair*: fixing a typo you notice while reading. *Merkle repair*: comparing table-of-contents hashes chapter by chapter instead of re-reading the book.
- *Tombstones*: "deleted" sticky notes that every replica must see before anyone throws them away. `gc_grace_seconds` is how long the note must stay up.
- *LWW*: whoever's wristwatch reads later wins, even if it's wrong. *Vector clocks*: each writer keeps its own odometer.
- *PACELC*: CAP is the storm plan; ELC is the trade you make every sunny day.
- *Single-table design*: a materialized view of your joins, designed before you have data.
- For Java/Kotlin engineers: a Cassandra partition is like a `TreeMap` keyed by clustering columns, living on one node; a DynamoDB item collection works the same way.

**Misconceptions to address explicitly** (section 6)
- No schema; no transactions; CAP "pick two"; eventual means lossy; quorum means linearizable; Mongo always faster; ALLOW FILTERING; giant partitions; tombstone storms; DynamoDB = Dynamo.

**What to cut or compress**
- Bigtable internals beyond LSM and SSTable basics; HBase; Riak, Voldemort and PNUTS except as history.
- Couchbase, CouchDB, Aerospike, FaunaDB: a mention at most.
- Cassandra materialized views (experimental since 4.0) and Cassandra ops depth (compaction tuning, multi-DC ops, beyond one UCS paragraph).
- Accord internals: show the syntax only, as alpha.
- Neo4j clustering (Enterprise) and most of GDS: show one community-detection call at most.
- Elasticsearch cluster operations, shard allocation tuning and ILM.
- Milvus distributed deployment (heavy dependencies); use pgvector or Qdrant single-node.
- Formal Paxos and Raft proofs: link instead.
- InfluxDB line-protocol detail.

**Pacing**
- Hold back CAP/PACELC until students have seen QUORUM fail with two nodes down (lesson 6). The theory then explains something they watched happen.
- Say up front that Redis is the canonical key-value store and has its own track.

### Gaps
- None of the analogies has been classroom-tested here. They are pedagogical suggestions.

---

## 10. Verified URLs

### Takeaway
The URLs below were fetched this session and loaded, either as HTML or as PDFs read directly. Search-only URLs are listed separately and should be re-checked before publishing.

### Cited Findings (fetched and confirmed loading)
- https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/
- https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf (PDF; pp. 208–214 read)
- https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf (PDF; all 6 pages read)
- https://www.alexdebrie.com/posts/dynamodb-single-table/
- https://jepsen.io/analyses
- https://jepsen.io/analyses/mongodb-4.2.6
- https://jepsen.io/consistency
- https://jepsen.io/consistency/models
- https://cassandra.apache.org/_/download.html
- https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html
- https://cassandra.apache.org/doc/latest/cassandra/new/index.html
- https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html
- https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html
- https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html
- https://hub.docker.com/_/cassandra
- https://github.com/apache/cassandra-java-driver
- https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/
- https://pmcfadin.github.io/cassandra6-docs-workzone/operators/draft/upgrade/onboarding-to-accord.html (draft or preview docs, not official)
- https://www.mongodb.com/docs/manual/release-notes/
- https://www.mongodb.com/docs/manual/release-notes/9.0/
- https://www.mongodb.com/docs/manual/reference/mongodb-defaults/
- https://www.mongodb.com/docs/manual/core/transactions-production-consideration/
- https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/
- https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
- https://github.com/mongodb/mongo-java-driver/releases
- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html
- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html
- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/dynamodb-enhanced-client.html
- https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-dynamodb-vector-search/
- https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-dynamodb-multi-attribute-composite-keys-global-secondary-indexes/
- https://blog.localstack.cloud/localstack-for-aws-release-2026-03-0/
- https://neo4j.com/docs/operations-manual/current/docker/introduction/
- https://github.com/neo4j/neo4j-java-driver/releases
- https://www.elastic.co/pricing/faq/licensing
- https://github.com/pgvector/pgvector

### Inferences
- **Seen only in search results, not fetched; re-verify before use**:
  - https://www.mongodb.com/docs/manual/release-notes/8.2/
  - https://neo4j.com/blog/developer/neo4j-graph-database-versioning/
  - https://neo4j.com/release-notes/database/neo4j-2026-10/
  - https://neo4j.com/docs/operations-manual/2026.06/docker/configuration/
  - https://aws.amazon.com/about-aws/whats-new/2025/06/amazon-dynamo-db-global-tables-multi-region-strong-consistency-generally-available/
  - https://aws.amazon.com/about-aws/whats-new/2026/02/dynamodb-gt-multi-account
  - https://www.scylladb.com/source-available-faq
  - https://www.scylladb.com/2024/12/18/license/
  - https://www.businesswire.com/news/home/20240829537786/en
  - https://opensearch.org/blog/explore-opensearch-3-3/
  - https://www.influxdata.com/blog/influxdb-3-OSS-GA/
  - https://www.tigerdata.com/blog/timescale-becomes-tigerdata
  - https://en.wikipedia.org/wiki/Graph_Query_Language
  - https://en.wikipedia.org/wiki/PACELC_theorem
  - https://thenewstack.io/apache-cassandra-6-features/
  - https://github.com/docker-library/cassandra/issues/144
  - https://github.com/docker-library/cassandra/issues/172
  - https://central.sonatype.com/artifact/org.mongodb/mongodb-driver-kotlin-coroutine
- **Fetch failed (HTTP 403)**:
  - https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/
  - https://theconsensus.dev/p/2026/08/16/transactions-in-cassandra.html

### Gaps
- No verified URL yet for: the 2022 DynamoDB USENIX ATC paper; the official Cassandra 6.0-alpha2 release announcement; ISO's GQL catalogue page; Qdrant/Milvus release notes; OpenSearch's current release page; CRDT primary sources.
