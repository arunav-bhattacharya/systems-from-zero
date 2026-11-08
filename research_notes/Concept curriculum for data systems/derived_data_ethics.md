# Derived-data architecture, end-to-end correctness, and the ethics and law of data systems (state as of 7 Nov 2026)

Conventions used below:
- "DDIA2" means *Designing Data-Intensive Applications*, 2nd ed. (Kleppmann and Riccomini, O'Reilly). Page references give the **printed page** and then the **PDF page** in brackets. The offset is +24, so printed p.539 is [PDF 563]. Chapter 13 ("A Philosophy of Streaming Systems") runs printed pp.539-584 [PDF 563-608]. Chapter 14 ("Doing the Right Thing") runs printed pp.585-602 [PDF 609-626]. The PDF is the local copy named in the brief. DDIA2's framing is paraphrased; the very few quotes are under 15 words.
- The earlier product-organized research (`research_notes/Systems course curriculum research/`) already covers Kafka 4.4 internals, the idempotent producer, Kafka Streams EOS, Debezium 3.7, Iceberg/Delta/Hudi versions and the lab pin set. Those facts are only cross-referenced here. This file adds the concept framing that research lacked: derived data as a philosophy, end-to-end correctness, ethics and law, and erasure in immutable systems.
- Each key question ends with "concept cards" (problem, simplest version, where it breaks, improvement, misconceptions). They sit under **Inferences** because they are syntheses built from the cited findings.

---

## 1. Data integration: systems of record vs derived data, why one database is never enough, total ordering and its limits, derivation via batch and stream

### Takeaway
Real applications need several specialized stores (OLTP database, search index, cache, warehouse, ML features). The way to keep them consistent without distributed transactions is to name one **system of record**, funnel every write through a single **totally ordered log** (CDC or event sourcing), and **derive** every other representation from that log with deterministic, idempotent consumers. A total order stops scaling at the single-leader throughput limit, across regions, across microservices and on offline clients. Past that point you can only order what is causally related, typically by keying on an entity ID or by carrying event IDs.

### Cited Findings
- DDIA2 frames Chapter 13 as more opinionated than earlier chapters: it develops one philosophy (streaming and derived data) and does not survey alternatives. — DDIA2 p.539 [PDF 563]
- Every tool, even a "general-purpose" database, is designed for some usage pattern. Complex applications use data in several ways, so they end up stitching several tools together. The canonical example is an OLTP database plus a full-text search index. PostgreSQL's built-in full-text search may be enough for simple cases, but search indexes make a poor durable system of record. — DDIA2 pp.540 [PDF 564]
- The number of derived representations grows quickly: warehouses, batch and stream outputs, caches, denormalized objects, ML, ranking and recommendation outputs, notifications. — DDIA2 p.540 [PDF 564]
- Rule for reasoning about dataflows: be explicit about where data is written first and which representation derives from which. If CDC is the **only** path that updates the index, the index is derived from the system of record and therefore consistent with it, bugs excepted. — DDIA2 p.541 [PDF 565]
- Dual writes fail. If the application writes to both the database and the index, two concurrent clients can have their writes applied in different orders by the two systems. Neither system is in charge of ordering, so they can diverge **permanently** (DDIA2 Figure 12-4). — DDIA2 p.541 [PDF 565]
- Pushing all input through one system that decides a single order is an application of state machine replication. Whether that system is CDC or an event-sourcing log matters less than having a total order. Derivation from an event log can usually be made deterministic and idempotent, which makes fault recovery easy. — DDIA2 p.541 [PDF 565]
- Derived data vs distributed transactions: both keep systems consistent. 2PC/XA uses atomic commit. Log-based derivation uses deterministic retry plus idempotence. The main practical difference is that transactions usually give read-your-writes, while derived systems update asynchronously. XA has poor fault tolerance and performance. With no good, widely adopted distributed-transaction protocol available, DDIA2 judges log-based derived data the most promising way to integrate heterogeneous systems. — DDIA2 pp.541-542 [PDF 565-566]
- Asynchrony is what makes log-based systems robust. A fault stays local, whereas a distributed transaction aborts when any participant fails and so **amplifies** failures. Secondary indexes that span shards are also most reliable and scalable when maintained asynchronously. — DDIA2 pp.544-545 [PDF 568-569]
- Limits of total ordering, per DDIA2:
  1. A total order normally needs a single leader. Once throughput exceeds one machine, the log must be sharded and order across shards becomes ambiguous.
  2. Multi-region deployments typically run a leader per region, so events from different regions have no defined order.
  3. Microservices that each own their state have no defined order between their events.
  4. Offline-capable clients that update local state immediately see events in a different order from the server.
  - Formally, total order broadcast is equivalent to consensus, and most consensus algorithms cannot split the ordering work across nodes. — DDIA2 pp.542-543 [PDF 566-567]
- Causality example (unfriend, then message): a user removes their ex as a friend and then posts a rude message to the remaining friends. If friendships and messages live in different systems, the notification service can process the message before the unfriend event and notify the ex. The notification is effectively a join of messages with the friend list. DDIA2 says this problem has no simple answer. Starting points it gives: logical timestamps, which still need out-of-order handling; logging an event that records what the user saw, with a unique ID that later events reference; and conflict resolution, which does not help when actions have external side effects. — DDIA2 pp.543-544 [PDF 567-568], citing Helland & Campbell "Building on Quicksand" (CIDR 2009) and Kerr "Provenance and Causality in Distributed Systems" (2016)
- Batch and stream processing are the tools of data integration. Their outputs are derived datasets: indexes, materialized views, recommendations, aggregates. The fundamental difference is unbounded vs bounded input. Batch has a functional flavor (pure functions, immutable inputs, append-only outputs). Stream processing adds managed, fault-tolerant state. — DDIA2 p.544 [PDF 568]
- Reprocessing for evolution: without it, schema evolution is limited to simple changes such as adding an optional field. With it, a dataset can be restructured into a completely different model. Old and new schemas can run side by side as two derived views of the same data, with a small share of users moved to the new view and the share increased gradually. Every stage is reversible. — DDIA2 pp.545-546 [PDF 569-570]
- DDIA2's railway analogy for gradual migration: England settled on a standard gauge in 1846 and converted lines via dual or mixed gauge, a third rail that let both kinds of train run until the old rail could be removed. The cost of conversion is why non-standard gauges survive, e.g. San Francisco's BART. — DDIA2 p.545 [PDF 569]
- Jay Kreps's 2013 essay "The Log" underlies the claim that an organization's dataflow looks like one huge database. — DDIA2 ref [5], ch.13 references [PDF 604]

### Inferences
**Concept card: system of record vs derived data**
- *Problem:* several stores must agree, each optimized for a different access pattern.
- *Simplest version:* the application writes to every store (dual writes).
- *Where it breaks:* two concurrent writers get applied in different orders and the stores diverge permanently (DDIA2 Fig. 12-4). Partial failure is worse still: one write lands and the other does not, and nothing retries.
- *Improvement:* one system of record, CDC or outbox into a log, deterministic idempotent consumers, and a rebuild-from-log capability.
- *Misconceptions:* "a cache or search index can be a source of truth" (it should be rebuildable); "derived means eventually wrong" (derived means asynchronous; integrity can still be exact, see Q4); "distributed transactions are the principled answer" (XA is fragile and amplifies faults).

**Concept card: total order and its limits**
- *Problem:* derived views must apply changes in the same order.
- *Simplest version:* a single-leader log (any single-leader database's replication log is one).
- *Where it breaks:* the four limits above. Once you shard or go multi-region, you lose a global order.
- *Improvement:* order per entity (route by key so all updates to one object share a shard). Capture causal links explicitly with event IDs and "what the user saw" events. Accept that cross-entity causality, as in the unfriend example, needs application-level design.
- *Misconception:* "Kafka gives you ordering." It gives order per partition only (see the earlier Kafka notes).

- Teaching hook: CREATE INDEX on a live table (snapshot, then backlog catch-up, then ongoing maintenance) is the same algorithm as bootstrapping a follower and as CDC's initial snapshot (DDIA2 p.548 [PDF 572]). This one idea links replication, CDC and derived data. Use it in Q3.

### Gaps
- DDIA2 gives no quantitative failure rates for dual writes. No public incident report was found that quantifies index/database divergence caused by dual writes. A lab measurement (Q7) is the practical way to get a number.
- No authoritative 2026 survey of how many organizations use CDC/outbox versus dual writes was found.

---

## 2. Lambda (Marz 2011), its problems, kappa (Kreps 2014), the Dataflow/Beam model, and reprocessing for schema migration

### Takeaway
Lambda ran the same logic twice, once in a batch layer (exact, recomputed from the immutable master dataset) and once in a speed layer (fast, approximate), and merged the two at query time. It worked, but every transformation had to be written and operated in two distributed systems. Kreps's 2014 kappa alternative keeps the input log long enough to replay it, runs a **second copy** of the stream job from offset 0 into a new output table, and switches readers once the copy catches up. Unification then needs three properties: replayable input, exactly-once (effectively-once) state, and **event-time** windowing. The Dataflow model (Google, VLDB 2015) and Apache Beam formalized these. DDIA2 reports that lambda "has fallen out of use".

### Cited Findings
- DDIA2: lambda was an early attempt to unify batch and stream, had a number of problems, and has fallen out of use. Newer systems run batch (reprocessing history) and stream in **one** system, sometimes called kappa architecture. — DDIA2 p.546 [PDF 570], refs [11] Marz, [12] Kreps, [13] Fernandez et al. "Liquid" (CIDR 2015)
- DDIA2's three requirements for unifying batch and stream in one engine:
  1. Replay historical events through the same engine that handles recent events, from a log-based broker or from a filesystem or object store.
  2. Exactly-once semantics, meaning output as if no fault had occurred, which requires discarding partial outputs of failed tasks.
  3. Windowing by **event time**, since processing time is meaningless during reprocessing.
  - Apache Beam is the API example, run on Flink or Google Cloud Dataflow. — DDIA2 p.546 [PDF 570]
- Kreps, "Questioning the Lambda Architecture", O'Reilly Radar, **2 July 2014**. Lambda feeds an immutable record stream into a batch system and a stream system in parallel, implements the logic in both, and merges results at query time. Kreps credits it with keeping inputs immutable and putting reprocessing up front. He rejects the claims that real-time processing is inherently lossier and that lambda "beats" CAP. The core problem is keeping identical logic in two complex distributed systems, which he considers not fixable. — [O'Reilly](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
- Kreps on Summingbird, Twitter's framework that compiles one codebase to both batch and streaming: it helps but still carries the operational burden of two systems, is limited to their common features, and is cut off from the wider Hadoop ecosystem. — [O'Reilly](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
- Kreps's reprocessing recipe (kappa):
  1. Keep the full input log in Kafka, with retention sized to the reprocessing window (e.g. 30 days).
  2. Start a second instance of the job from the beginning, writing to a new table.
  3. When it catches up, switch the application to the new table.
  4. Stop the old job and delete the old table.
  - Keeping both tables briefly gives instant rollback. The cutover can be gated by an A/B test. — [O'Reilly](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
- Apache Beam is at **2.77.0** (released 7 Oct 2026); 2.78.0-RC2 was cut on 2 Nov 2026. — [GitHub releases API: apache/beam](https://github.com/apache/beam/releases)
- Earlier research notes in this folder: Flink 2.0.0 (24 Mar 2025) is the first 2.x release, with disaggregated state. Spark 4.3 Real-Time Mode reports ~100 ms end-to-end latency for stateful queries. Kafka 4.4.0 (22 Oct 2026) is current. — `research_notes/Systems course curriculum research/big_data.md`, `kafka.md` (sources cited there)

### Inferences
**Concept card: lambda**
- *Problem:* in 2011, Hadoop gave correct results hours late and Storm gave fast results that were fragile and hard to correct. Marz's "How to beat the CAP theorem" (Oct 2011) proposed query = function(all data): a batch layer recomputes views from an immutable master dataset, a speed layer covers the last few hours, and a serving layer merges the two. Marz's original post was not re-fetched in this session; the framing comes via Kreps and DDIA2 ref [11].
- *Simplest version:* two codebases plus a merge at read time.
- *Where it breaks:* identical semantics must be maintained in two engines. Every bug fix and schema change happens twice. Results disagree at the seam, and two clusters must be operated (Kreps).
- *Improvement:* kappa. One engine, a replayable log, versioned output tables and a reader switch.
- *Misconceptions:*
  - "Kappa means no batch." It means one engine; replay is the batch.
  - "Kappa needs infinite Kafka retention." Retention only has to cover the replay window, and Kafka tiered storage or a lakehouse table can hold the long tail. Latter is an inference.
  - "Lambda beats CAP." Kreps rejects this.

**Concept card: the Dataflow model / Beam**
- Treat bounded data as a special case of unbounded data. Separate *what* is computed (transforms), *where* in event time (windows), *when* in processing time results are emitted (watermarks and triggers), and *how* refinements relate (accumulation modes). Source: Akidau et al., "The Dataflow Model", PVLDB 8(12), 2015, https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf; not re-fetched in this session, framing from training knowledge.
- Lesson anomaly to reproduce: replaying a month of events with **processing-time** windows puts everything in one window. Event-time windows give the correct per-day counts. DDIA2's point that processing time is meaningless during replay becomes a measurable bug.

**Concept card: reprocessing for schema migration**
- *Problem:* you need a new data model, not just an added field.
- *Simplest version:* a big-bang migration script.
- *Where it breaks:* long locks, no rollback, a single risky cutover.
- *Improvement:* derive view v2 next to v1 from the same log, shift traffic gradually, then retire v1. This is the railway third rail.
- *Misconception:* "schema evolution = Avro compatibility rules." Compatibility rules only cover additive change. Reprocessing covers restructuring.

### Gaps
- Marz's 2011 post and the Akidau 2015 paper were not fetched in this session. Their content above is standard and matches DDIA2's references, but lesson writers should quote from the originals.
- No 2025-2026 industry survey quantifying "lambda in decline" was found. DDIA2's statement is the strongest available source.

---

## 3. Unbundling databases: "Turning the database inside-out" (2014), "Online Event Processing" (CACM 2019), federation vs unbundling, designing around dataflow, observing derived state, pushing changes to clients, and streaming databases / IVM (Materialize, RisingWave, Feldera/DBSP) as the 2020s form of the idea

### Takeaway
A database already contains a derived-data engine: indexes, materialized views and replication are all derived from its write-ahead log. "Unbundling" moves that machinery outside the database so many specialized stores can be kept in sync. The pieces are logs (Kafka), CDC (Debezium) and stream processors running application code as derivation functions. Federation unifies **reads**; unbundling unifies **writes**, the harder problem. Taken to its end, the write path reaches the user's screen: subscriptions, sync engines, local-first apps. Streaming databases and IVM engines repackage the idea in SQL: you declare a view and the engine maintains it incrementally. In Nov 2026 the main options are Materialize (differential dataflow, BSL), RisingWave (Apache 2.0) and Feldera (DBSP).

### Cited Findings
**DDIA2's framing**
- Databases, batch/stream processors and operating systems all store, process and query data. Unix offers low-level abstractions (bytes, pipes); relational databases offer high-level ones (SQL, transactions). DDIA2 reads NoSQL as applying the Unix approach to distributed OLTP, and the unbundling section as an attempt to combine the two. — DDIA2 pp.546-547 [PDF 570-571]
- Database features that resemble derived-data pipelines: secondary indexes, materialized views, replication logs and full-text indexes. — DDIA2 p.547 [PDF 571]
- CREATE INDEX snapshots the table, sorts, writes the index, processes the backlog of writes made since the snapshot, then keeps the index current. This is the same as setting up a follower and bootstrapping CDC, so every CREATE INDEX reprocesses existing data into a new view. — DDIA2 p.548 [PDF 572]
- "Meta-database of everything": batch, stream and ETL jobs act like the database subsystem that maintains indexes and views, i.e. elaborate triggers, stored procedures and view maintenance. Derived systems are like index types run by different teams on different machines. — DDIA2 p.548 [PDF 572]
- **Federated databases (unifying reads):** one query interface over many engines (a polystore). Examples: PostgreSQL foreign data wrappers, Trino, Hoptimator, Xorq. **Unbundled databases (unifying writes):** CDC and event logs keep writes in sync across technologies, in the Unix tradition of small tools joined by a uniform low-level API. Keeping writes in sync is the harder engineering problem. — DDIA2 pp.548-549 [PDF 572-573]
- Across heterogeneous technologies, an ordered event log with idempotent consumers is far more practical than distributed transactions. Transactions inside one system (e.g. a stream processor's internal exactly-once) work well, but no standard transaction protocol spans systems built by different groups. — DDIA2 p.549 [PDF 573]
- Loose coupling works at two levels. At the system level, the log buffers for a slow or failed consumer, which catches up later, so the fault is contained. At the human level, teams can work independently behind well-defined interfaces. — DDIA2 p.550 [PDF 574]
- Caveat DDIA2 states plainly: unbundling is about breadth, not depth. If one product does everything you need, use it. Running many pieces of infrastructure has learning-curve and operational costs, and building for scale you don't need is premature optimization. — DDIA2 pp.550-551 [PDF 574-575]
- Composition tools are improving: Debezium extracts change streams from many databases, Kafka's protocol is becoming a de facto standard, and IVM engines precompute and update caches of complex queries. — DDIA2 p.551 [PDF 575] (IVM is covered in ch.12 at p.516 [PDF 540])

**Designing applications around dataflow**
- Spreadsheets (VisiCalc, 1979) already had dataflow: change an input cell and dependent formulas recompute. Data systems need the same thing at scale, with fault tolerance and durability, across technologies. — DDIA2 p.551 [PDF 575]
- Application code as a derivation function: a secondary index (pick and sort fields), a full-text index (language detection, stemming, synonyms, inverted index), an ML model (feature extraction plus training), and a UI cache all derive one dataset from another. Databases handle custom derivation code poorly. Triggers, stored procedures and UDFs were an afterthought, and in-database code fits badly with package management, version control, rolling upgrades and monitoring. — DDIA2 pp.551-552 [PDF 575-576]
- With stateless services the database is a mutable shared variable that you can read but not subscribe to, so you poll. Dataflow thinking makes application code respond to state changes in one place by producing state changes in another. — DDIA2 pp.552-553 [PDF 576-577]
- Maintaining derived data needs stable ordering and fault-tolerant processing; losing a single message desynchronizes a view permanently. These demands are much cheaper than distributed transactions. — DDIA2 p.554 [PDF 578]
- Microservices vs dataflow, the currency-conversion example: a microservice queries an exchange-rate service at purchase time. A dataflow purchase processor subscribes to rate updates and keeps a local table, so the RPC becomes a stream-table join. This is faster and more robust, since the fastest network request is none at all. The join is time-dependent, though: reprocessing needs historical rates. — DDIA2 pp.554-555 [PDF 578-579], citing Stopford "Microservices in a Streaming World" (QCon 2016)

**Observing derived state; pushing to clients**
- **Write path** (eager, precomputed) vs **read path** (lazy, on request). The derived dataset is where they meet. Caches, indexes and materialized views move that boundary. Example spectrum: no index (grep everything) → inverted index → precomputed results for common queries. Precomputing every possible query is impossible because the query space is exponential. — DDIA2 pp.555-557 [PDF 579-581]
- On-device state is a cache of server state. Pixels on the screen are a materialized view of client model objects, which in turn replicate datacenter state. — DDIA2 p.558 [PDF 582], citing Kleppmann "Turning the Database Inside-out with Apache Samza", Strange Loop, Sept 2014 (ref [31])
- SSE (EventSource) and WebSockets let the server push changes. That extends the write path to the end user. Offline devices resume from an offset, like a log consumer. — DDIA2 pp.558-559 [PDF 582-583]
- End-to-end event streams: React and Elm already re-render on state change; extending this to server-pushed events gives sub-second propagation from one device to another. The obstacle is that databases, frameworks and protocols assume request/response, and few datastores let a request return a *stream* of responses (subscriptions). — DDIA2 p.559 [PDF 583]
- "Reads are events too": route read requests through the stream processor. A read becomes a stream-table join, and a subscription is a persistent join. Logging reads records what the user saw, e.g. the shipping estimate and stock level shown before a purchase, which helps provenance at an I/O cost. Multi-shard queries over streams include Storm DRPC, which counted the users who had seen a URL as the union of follower sets, and fraud scoring that joins differently sharded reputation databases. — DDIA2 pp.559-561 [PDF 583-585], citing McSherry "Dataflow as Database" (2016)
- Sync engines and local-first software are covered in DDIA2 ch.6. — DDIA2 p.220 [PDF 244]

**The two Kleppmann pieces named in the brief**
- "Turning the Database Inside-out with Apache Samza", Strange Loop, September 2014 (DDIA2 ref [31]). It re-examines replication, secondary indexes, caching and materialized views as stream-derived structures. The transcript was published at martin.kleppmann.com in March 2015 (not re-fetched here). — DDIA2 ch.13 ref [31] [PDF 605]
- Kleppmann, Beresford, Svingen, "Online Event Processing: Achieving Consistency Where Distributed Transactions Have Failed", *CACM* 62(5):43-49, May 2019, doi:10.1145/3312527. It is the source of DDIA2's multi-shard payment design (Fig. 13-2; see Q4). — DDIA2 ch.13 ref [47] [PDF 607]

**Streaming databases / IVM in Nov 2026 (versions from GitHub release APIs, fetched 7 Nov 2026)**
- **Materialize v26.49.1** (6 Nov 2026); v26.50.0-rc.1 is tagged. Versions now follow a year-based "26.x" scheme with roughly weekly releases. — [GitHub: MaterializeInc/materialize](https://github.com/MaterializeInc/materialize/releases)
- **RisingWave v3.1.1** (5 Nov 2026); v3.1.0 was released 21 Sep 2026, and the 3.0.x line is still patched (3.0.5, 12 Oct 2026). — [GitHub: risingwavelabs/risingwave](https://github.com/risingwavelabs/risingwave/releases)
- **Feldera v0.379.0** (7 Nov 2026). Feldera releases almost daily and is still pre-1.0. — [GitHub: feldera/feldera](https://github.com/feldera/feldera/releases)
- Feldera implements DBSP directly; Materialize is built on differential dataflow. A third-party comparison lists RisingWave as Apache 2.0 and Materialize as BSL. — [Tinybird: Materialize alternatives](https://www.tinybird.co/blog/md/materialize-alternatives)
- RisingWave's own description: every materialized view is a continuously running streaming pipeline, and only the change is propagated through the plan. This is vendor material, verified against RisingWave 2.8.0. — [RisingWave blog: IVM explained](https://risingwave.com/blog/incremental-materialized-views-explained/), [What is IVM](https://risingwave.com/blog/what-is-incremental-view-maintenance)

**Sync engines (npm registry "latest" dist-tags, fetched 7 Nov 2026)**
- `@rocicorp/zero` 1.11.4 (4 Nov 2026); `@electric-sql/client` 1.5.28 (9 Sep 2026); `convex` 1.49.0 (30 Oct 2026); `@powersync/web` 2.6.0 (2 Nov 2026); `@instantdb/core` 1.0.67 (31 Aug 2026); `@livestore/livestore` 0.5.0 (15 Oct 2026). — [npm registry](https://registry.npmjs.org/) (e.g. https://registry.npmjs.org/@rocicorp/zero)

### Inferences
**Concept card: unbundling**
- *Problem:* no single database serves search, analytics, caching and OLTP well, but you want database-like guarantees across all of them.
- *Simplest version:* a nightly ETL dump plus cron rebuilds.
- *Where it breaks:* staleness of hours. Rebuilds at scale take hours. Deletes are missed: a full dump does not notice a deleted row unless you diff.
- *Improvement:* CDC into a log, then incremental consumers. Rebuild = replay from offset 0, or from a snapshot plus offset.
- *Misconceptions:*
  - "Unbundling replaces databases." DDIA2 says the opposite: databases still hold state and serve queries.
  - "Federation solves sync." It only unifies reads.
  - "More components = more scalable." The goal is breadth, not depth, and DDIA2 advises using one product if it suffices.

**Concept card: observing derived state / pushing to clients**
- *Problem:* clients see stale data until they reload or poll.
- *Simplest version:* polling.
- *Where it breaks:* cost and latency trade off directly. Polling every second across N clients is N requests per second whether or not anything changed.
- *Improvement:* subscriptions (SSE/WebSocket) carrying offsets, or sync engines that keep a local replica plus a server-ordered change stream (Zero, Electric, PowerSync, Convex, InstantDB, LiveStore).
- *Misconception:* "real-time UI is a front-end concern." It is the write path extended to the client, and it inherits all the ordering and idempotence problems of the server-side log.

**Concept card: streaming databases / IVM**
- *Problem:* custom stream code for each derived view is hard to get right: joins, retractions, late data.
- *Simplest version:* `REFRESH MATERIALIZED VIEW` on a timer, i.e. full recomputation.
- *Where it breaks:* cost is proportional to input size, not change size, and freshness equals the refresh interval.
- *Improvement:* IVM. Represent changes as weighted deltas (+1/-1), Z-sets in DBSP, and compute the view's delta from the input delta. Work becomes proportional to the change, and joins and aggregates update incrementally.
- *Misconception:* "a streaming DB removes the consistency question." The engine is still a derived system that receives CDC asynchronously. Read-your-writes across the OLTP database and the view still needs offset or LSN waiting (Q4).

- First-principles teaching order (inference): spreadsheet cell → CREATE INDEX → follower replica → CDC to search → stream processor with app code → SQL IVM engine → client subscription. Each step changes one thing: who runs the derivation, and where the result lives.
- The 2014 talk and DDIA2 present ideas; the 2026 products embody them. Present Materialize, RisingWave and Feldera as implementations of "a materialized view maintained from a log", not as a separate topic.

### Gaps
- The DBSP paper (Budiu et al., PVLDB 16, VLDB 2023) and Feldera's licence were not fetched in this session. Verify title, venue, award and licence before quoting.
- Materialize's current licence terms (BSL change date, community edition limits) were not checked against Materialize's own pages. The BSL label comes from a third party.
- Benchmarks comparing IVM engines (latency, throughput, memory) are vendor-produced. No independent 2026 benchmark was found.
- Sync engine semantics (Zero's query-driven sync vs Electric's shape streams, conflict handling) were not researched here beyond version numbers.

---

## 4. Correctness without global coordination: end-to-end argument, request IDs, uniqueness via a partitioned log, timeliness vs integrity, coordination avoidance, apologies, auditing ("trust, but verify"), ledgers and transparency logs, silent data corruption

### Takeaway
Strong guarantees in one component (TCP, a serializable database, Kafka EOS) do not make the application correct end to end. Duplicate suppression, integrity checks and encryption must also be done at the endpoints, using a **client-generated request ID carried all the way to the final write**. Uniqueness and other conflicting-write constraints can be enforced without distributed transactions by routing all potentially conflicting writes to the **same log partition** and processing them sequentially. Multi-shard operations then decompose into idempotent steps whose atomicity comes from a single log append.

This design separates **timeliness**, which may lag, from **integrity**, which must never be violated. Many business constraints can be checked after the fact and repaired with compensations ("apologies"). Bailis et al. formalize when coordination is avoidable (invariant confluence) and report a 25x TPC-C New-Order speedup. Hardware and software do lie: hyperscalers report about 1 in 1,000 CPUs producing silent data corruptions. So systems must audit themselves, by recomputing derived views, checking hash chains and Merkle trees, and using transparency logs. AWS discontinued its managed ledger database, QLDB, on 31 July 2025.

### Cited Findings
**Why "correct" is hard**
- Stateless read-only services recover from bugs by restarting. Stateful systems remember mistakes, potentially forever. ACID's foundations are weaker than they look (weak isolation confusion), and it is hard to know whether a given isolation or replication configuration is safe for an application. Kyle Kingsbury's Jepsen tests showed gaps between products' claimed and actual safety under network faults. — DDIA2 pp.561-562 [PDF 585-586]
- Serializable transactions do not protect against application bugs that write bad data. That argues for immutable, append-only data, because faulty code can then not destroy good data. — DDIA2 p.562 [PDF 586]

**End-to-end argument and request IDs**
- Exactly-once means arranging the computation so the final effect is as if no fault had occurred, even with retries. Processing twice is a form of corruption: double billing, an overstated counter. Idempotence is the main tool. Operations that are not naturally idempotent need extra metadata (the set of applied operation IDs) and fencing on failover. — DDIA2 pp.562-563 [PDF 586-587]
- TCP sequence numbers suppress duplicates **within one connection** only. If a client loses the connection after sending COMMIT, it cannot tell whether the transaction committed. Retrying DDIA2's Example 13-1 (credit +$11.00, debit -$11.00) can move $22. DDIA2 says real banks do not work this way. — DDIA2 p.563 [PDF 587], citing Helland & Campbell (CIDR 2009)
- 2PC lets a coordinator reconnect and resolve an in-doubt transaction. It still does not cover the hop from the browser to the app server: a POST times out on a weak mobile link, the user resubmits, and the database sees a new transaction. Post/Redirect/Get does not help if the POST times out. — DDIA2 pp.563-564 [PDF 587-588]
- Fix (Example 13-2): generate a request ID on the client, either a UUID in a hidden form field or a hash of the form fields. Pass it through every hop and record it under a UNIQUE constraint in the same transaction as the effect. Databases maintain uniqueness correctly even at weak isolation, whereas application-level check-then-insert fails under non-serializable isolation. The requests table doubles as an event log, so the balance updates could be derived downstream. — DDIA2 pp.564-565 [PDF 588-589]
- Saltzer, Reed and Clark (1984): a function can be implemented completely and correctly only with knowledge held by the application at the endpoints. A lower-level partial version is useful only as a performance enhancement. DDIA2 applies this to duplicate suppression, to integrity (Ethernet, TCP and TLS checksums miss software bugs and disk corruption, so end-to-end checksums are needed) and to encryption (WiFi passwords and TLS each protect only one segment). — DDIA2 pp.565-566 [PDF 589-590]; original: Saltzer, Reed, Clark, "End-to-End Arguments in System Design", *ACM TOCS* 2(4):277-288, Nov 1984 (DDIA2 ref [44]), https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf
- DDIA2: transactions collapse many failure modes (concurrent writes, constraint violations, crashes, network interruptions, disk failures) into commit or abort, but they are expensive across heterogeneous systems. Rejecting them pushes fault tolerance into application code, which usually gets it wrong. Better end-to-end abstractions are an open need. — DDIA2 p.566 [PDF 590]
- Industry practice, Stripe API v1:
  - Clients send an `Idempotency-Key` header of up to **255 characters**. Stripe suggests V4 UUIDs and warns against putting personal data in keys.
  - Stripe saves the status code and body of the first request once endpoint execution begins, including 500 errors. Keys may be pruned after they are at least **24 hours** old, and a reused key after pruning creates a new request.
  - Stripe compares parameters and returns an error on mismatch. Results are not saved if validation fails or the request conflicts with a concurrent one.
  - All POSTs accept keys; GET and DELETE are idempotent by definition.
  - API v2 instead drives failed or partial work to completion on retry. — [Stripe docs: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- The Kafka idempotent producer dedupes only producer-to-broker retries, using producer ID plus sequence number. An application-level resend (a new `send()` after an HTTP retry) is a new record. This is the end-to-end argument inside Kafka. — `research_notes/Systems course curriculum research/kafka.md` (Kafka 4.4 design doc cited there)

**Enforcing constraints through a partitioned log**
- Uniqueness covers usernames, email addresses, file names and seats, and is close to "balance never negative", "don't oversell stock" and "no overlapping room bookings". In a distributed setting uniqueness needs consensus, usually via a single leader per value. It scales by sharding on the unique value, e.g. a hash of the username. Asynchronous multi-leader replication is ruled out. Rejecting violations **immediately** requires synchronous coordination. — DDIA2 pp.566-567 [PDF 590-591], citing Bailis et al. VLDB 2014 (ref [45])
- Log-based uniqueness (username claims):
  1. Append each claim to the shard chosen by hash(username).
  2. A single-threaded processor per shard keeps a local table of taken names and emits success or rejection to an output stream.
  3. The client waits for the response matching its request.
  - This is consensus via a shared log. It scales by adding shards. The rule generalizes: route any writes that may conflict to the same shard. — DDIA2 pp.567-568 [PDF 591-592], citing Yarmula "Strong Consistency in Manhattan" (Twitter, 2016, ref [46])
- Multi-shard payment without atomic commit (Fig. 13-2, from the OEP paper):
  1. The client assigns a request ID and appends the request to the source account's shard.
  2. The source processor, whose state is derived entirely from the log, checks funds, reserves them, and emits outgoing, incoming and fee events carrying the request ID.
  3. The source processor sees its own outgoing event, executes it, and drops duplicates by request ID.
  4. Destination and fee shards apply incoming events, deduped by request ID.
  - Requirements: per-account log order, at-least-once delivery, deterministic processors. After a crash the processor reprocesses, makes the same decision, and emits the same events with the same IDs, which downstream consumers ignore as duplicates.
  - Atomicity comes from the single append of the initial request.
  - The user learns the outcome by subscribing to the source shard; a "declined" event handles insufficient funds. — DDIA2 pp.568-570 [PDF 592-594], ref [47] Kleppmann, Beresford, Svingen CACM 2019

**Timeliness vs integrity**
- **Timeliness** means users see up-to-date state; violations are temporary. Linearizability is the strong form; read-after-write is weaker. **Integrity** means no loss, no contradictory or false data, and correct derivations; violations are permanent and need explicit checking and repair. In slogan form: eventual consistency tolerates timeliness violations, while integrity violations produce perpetual inconsistency. — DDIA2 pp.571-572 [PDF 595-596]
- Credit card statement example: a transaction from the last 24 hours missing from the statement is normal lag. A balance that does not equal the previous balance plus transactions, or a charge never paid to the merchant, is an integrity failure. In most applications integrity matters far more than timeliness. — DDIA2 p.572 [PDF 596], citing Helland & Campbell
- ACID gives both, so the distinction rarely matters there. Event-based dataflow **decouples** them. Integrity in DDIA2's design rests on four mechanisms:
  1. A single atomic write message, which fits event sourcing.
  2. Deterministic derivation of all other state from it.
  3. A client request ID passed through every stage.
  4. Immutable messages plus occasional reprocessing to recover from bugs. — DDIA2 pp.572-573 [PDF 596-597]

**Loosely interpreted constraints and apologies**
- Examples of apologies: over-ordering stock (reorder, apologize, discount; the same process as a forklift destroying inventory), airline and hotel overbooking, overdrafts bounded by daily withdrawal limits, and inter-organization settlement. A compensating transaction corrects the mistake. The cost of the apology is a business decision. If it is acceptable, write optimistically and validate afterwards, but validate before irreversible, expensive actions. These systems need integrity (never lose a reservation) but not timeliness of constraint enforcement. — DDIA2 pp.573-574 [PDF 597-598], refs [3] Helland & Campbell "Building on Quicksand" (CIDR 2009), [48] Gray "The Transaction Concept" (VLDB 1981), [49] Garcia-Molina & Salem "Sagas" (SIGMOD 1987)
- Coordination-avoiding systems: dataflow keeps integrity on derived data without atomic commit, linearizability or cross-shard synchronization. Combined with loose constraints, a system can run multi-leader across regions with weak timeliness but strong integrity. Serializable transactions stay useful at small scope, and synchronous coordination is used only where recovery is impossible. Coordination trades apologies for inconsistency against apologies for outages; neither count reaches zero. — DDIA2 pp.574-575 [PDF 598-599]
- Bailis, Fekete, Franklin, Ghodsi, Hellerstein, Stoica, "Coordination Avoidance in Database Systems", PVLDB 8(3):185-196, Nov 2014:
  - **Invariant confluence** is a necessary and sufficient condition for safe coordination-free execution of an application's invariants.
  - Many common invariants and operations from real applications are I-confluent.
  - A prototype achieved a **25-fold** improvement over prior TPC-C New-Order performance on a **200-server** cluster. — [arXiv 1402.2237](https://arxiv.org/abs/1402.2237)
- Bailis et al., "Feral Concurrency Control" (SIGMOD 2015) studied **67** open-source Rails apps (about 27 kLOC on average):
  - Apps declare validations in the ORM, averaging 1.80 validations per model, vs 0.13 transactions and 0.01 locks.
  - Uniqueness is not I-confluent. Under concurrency, Rails' uniqueness validation still allowed about **700 duplicates** in an experiment, roughly an order of magnitude fewer than no validation, but not zero.
  - Rails does not set isolation, and most databases default to READ COMMITTED. — [Paper PDF](https://amplab.cs.berkeley.edu/wp-content/uploads/2015/06/feral-sigmod2015.pdf); [Colyer summary](https://blog.acolyer.org/2015/09/04/feral-concurrency-control-an-empirical-investigation-of-modern-application-integrity/); [Burke slides](https://kevin.burke.dev/slides/feral-concurrency/)

**Trust, but verify**
- System models usually treat faults as binary (can or cannot happen). Reality is probabilistic, and at scale unlikely events occur. Memory, disk and network corruption are all documented. — DDIA2 p.575 [PDF 599]
- Database bugs that broke integrity: MySQL failed to maintain uniqueness, with duplicates in a unique secondary index (Bug #73170, 2014). PostgreSQL's serializable level once showed write skew (Gary Fredericks, 2015). Application code gets far less testing and often doesn't even use FK or unique constraints. ACID "consistency" assumes bug-free transactions. — DDIA2 p.576 [PDF 600], refs [50], [51]
- HDFS and S3 do not fully trust disks. Background scrubbers re-read files, compare replicas and move data. You must read data back to know it is still there, and you must test-restore backups. — DDIA2 pp.576-577 [PDF 600-601], refs [52], [53]
- Event sourcing aids auditability: one immutable input event plus deterministic derivation makes state reproducible. Hash the event log to detect storage corruption. Rerun or redundantly run derivations to check derived state. This also enables time-travel debugging. — DDIA2 p.577 [PDF 601], refs [4], [55]
- End-to-end integrity checks cover every disk, network, service and algorithm on the path. Continuous checks, like automated tests, let teams move faster. — DDIA2 pp.577-578 [PDF 601-602], ref [56] Stokes "Move Fast with Confidence" (2016)
- Tools: audit tables are hard to make trustworthy. Signing a log with an HSM proves the log wasn't altered, not that the right transactions went in. Blockchains are Byzantine-fault-tolerant append-only logs, too costly for most uses, but their pieces carry over. Merkle trees give efficient inclusion proofs. Certificate Transparency uses verified append-only logs plus Merkle trees with a single leader per log and no consensus. — DDIA2 p.578 [PDF 602], refs [57] Merkle (CRYPTO '87), [58] Laurie "Certificate Transparency" (ACM Queue, Aug 2014)

**Silent data corruption (SDC) in CPUs**
- Dixit et al. (Meta), "Silent Data Corruptions at Scale", arXiv:2102.11245, **22 Feb 2021**. Silent-error test suites ran across **hundreds of thousands** of machines and found **hundreds of CPUs** with SDCs, monitored for more than **18 months**. The authors conclude SDCs are systemic across CPU generations. — [arXiv abstract](https://arxiv.org/abs/2102.11245)
- Dixit et al. case study, from the paper's full text:
  - In Spark-based decompression, `Int(1.1^53)` computed through Scala `math.pow` **always returned 0 on Core 59** of one CPU. The correct value is 156; `Int(1.1^52) = 142` was computed correctly.
  - The file-size computation therefore returned 0 for non-zero files, decompression was skipped, and the **database had missing files** that propagated to the application.
  - The paper notes fault-injection studies put CPU SDCs at about one in a million, while observed rates were orders of magnitude higher. — [arXiv PDF 2102.11245](https://arxiv.org/pdf/2102.11245)
- Hochschild et al. (Google), "Cores that don't count", HotOS 2021: exact rates are withheld, but they observe "a few mercurial cores per several thousand machines", similar to Facebook's rate. — [The Register, 4 Jun 2021](https://www.theregister.com/2021/06/04/google_chip_flaws/); [DSHR blog, 8 Jun 2021](https://blog.dshr.org/2021/06/unreliability-at-scale.html)
- Meta's 2022 follow-up ("Detecting silent data corruptions in the wild") reports hundreds of unique SDC instances, with detection running in the fleet since 2019. — [arXiv 2203.08989](https://arxiv.org/pdf/2203.08989.pdf)
- HPCA 2025 (Chatzopoulos et al.): hyperscalers (Meta, Google, Alibaba) have disclosed roughly **1 in 1,000** CPUs producing SDCs. — [HPCA 2025 paper](https://tcal.ceid.upatras.gr/papers/hpca2025_chatzopoulos.pdf)

**Ledger databases and transparency logs (state Nov 2026)**
- **Amazon QLDB** was discontinued on **31 July 2025**. AWS gave no formal announcement and instead updated docs and emailed customers in July 2024. It recommends migrating to **Aurora PostgreSQL**, with ledger-like behavior via extensions. InfoQ notes Aurora PostgreSQL has no permanent immutable change record, so audit history must be generated and stored outside it. AWS's migration path is S3 export, then Glue (revisions to CSV), then DMS full load plus ongoing replication (`aws-samples/example-qldb-ledger-migration`). — [InfoQ, Jul 2024](https://www.infoq.com/news/2024/07/aws-kill-qldb); [Tutorials Dojo (retired)](https://tutorialsdojo.com/amazon-quantum-ledger-database-qldb/); [Classmethod](https://dev.classmethod.jp/articles/amazon-qldb-eos-announcement/)
- **immudb** latest release: v1.11.2 (3 Sep 2026); v1.11.0 was 28 Apr 2026. — [GitHub: codenotary/immudb](https://github.com/codenotary/immudb/releases)
- **Sigstore Rekor v2**, a tile-based transparency log (`rekor-tiles`), is at v2.4.1 (30 Oct 2026). **Tessera**, the transparency-dev tiled-log library behind newer logs, is at v1.0.4 (16 Jul 2026). — [GitHub: sigstore/rekor-tiles](https://github.com/sigstore/rekor-tiles/releases); [GitHub: transparency-dev/tessera](https://github.com/transparency-dev/tessera/releases)
- DDIA2 also points to TigerBeetle, a database specialized for double-entry ledgers. — DDIA2 ch.3 [PDF 132]

### Inferences
**Concept card: end-to-end idempotency**
- *Problem:* retries happen at every hop: browser, load balancer, app, producer, consumer.
- *Simplest version:* "the database is ACID, so we're fine," or "Kafka EOS is on."
- *Where it breaks:* a timeout after commit followed by a resubmit gives a double charge ($11 becomes $22). Kafka EOS covers read-process-write inside Kafka, not the HTTP hop or an external side effect.
- *Improvement:* a client-generated request ID stored under a UNIQUE constraint at the final effect, plus dedupe at every consumer (Stripe's key with parameter fingerprinting is the production model).
- *Misconceptions:*
  - "Exactly-once delivery exists." Effects can be exactly-once; delivery is at-least-once plus dedupe.
  - "Idempotency keys can be server-generated." They must come from the endpoint that retries.
  - "Keys last forever." Stripe prunes after 24 hours or more, and dedupe-table retention must exceed the maximum retry horizon.

**Concept card: uniqueness via a partitioned log**
- *Problem:* enforce a unique username at scale without a global lock.
- *Simplest version:* check-then-insert in the application, or ORM validation.
- *Where it breaks:* write skew under READ COMMITTED (the Feral study's ~700 duplicates). Multi-leader replication accepts both claims.
- *Improvement:* hash(username) to a partition, a single-threaded deterministic processor, and a reply stream.
- *Where that breaks:* the client must wait (timeliness). Partitioning on the wrong key (userId instead of username) silently reintroduces duplicates. Hot keys cap throughput at one partition.
- *Misconception:* "logs can't do constraints." A log shard is a consensus decision for every key routed to it.

**Concept card: timeliness vs integrity**
- *Problem:* "consistency" bundles two properties with very different costs.
- *Simplest version:* make everything linearizable.
- *Where it breaks:* cross-region latency and outages, plus the extra apologies for unavailability.
- *Improvement:* guarantee integrity everywhere and buy timeliness only where users need it (wait for the output offset).
- *Misconception:* "eventual consistency = maybe wrong forever." That describes an integrity failure, which is a bug.

**Concept card: apologies / coordination avoidance**
- *Problem:* coordination costs latency and availability.
- *Simplest version:* enforce every invariant synchronously.
- *Where it breaks:* throughput collapses on hot invariants. Bailis measured a 25x gap on TPC-C New-Order.
- *Improvement:* classify invariants as I-confluent (run free) or not (coordinate, or relax plus compensate).
- *Misconception:* "overbooking is a bug." Often it is a business choice with a compensation process.

**Concept card: auditing**
- *Problem:* you can't trust hardware (around 1 in 1,000 CPUs), databases (MySQL #73170) or your own code.
- *Simplest version:* trust the components.
- *Where it breaks:* corruption is discovered months later downstream (Meta's missing files).
- *Improvement:* hash-chain the log, recompute derived views and diff them, compare Merkle roots across replicas, test-restore backups, and publish commitments to transparency logs when third parties must verify.
- *Misconceptions:*
  - "Checksums in TCP/TLS/disk are enough." They miss endpoint bugs.
  - "A ledger DB guarantees the right data went in." It only proves no later tampering.
  - "Blockchain is needed for auditability." Certificate Transparency shows a single-writer Merkle log suffices for most cases.

- The QLDB shutdown is itself a lesson in data-as-liability and vendor risk: an "immutable" managed ledger had a 2025 end date. Auditability should rest on portable mechanisms (hash chains, Merkle proofs, exportable logs), not on one product.

### Gaps
- Helland's "Memories, Guesses, and Apologies" (believed to be a 2007 MSDN blog post) could not be located in this session. The concept is taught via DDIA2 and Helland & Campbell "Building on Quicksand" (CIDR 2009, DDIA2 ref [3]). Lesson writers should verify the blog's URL and date before citing it.
- The full I-confluence table from Bailis et al. (which invariants are or aren't I-confluent, e.g. foreign-key insertions vs uniqueness) was not fetched; only the abstract was read.
- The 2021 Google paper's exact failure modes (e.g. corrupted AES, wrong results in specific instructions) were not re-read here; only secondary coverage was used.
- Data quality checks and data contracts (dbt tests and model contracts, Great Expectations/GX, Soda, the Open Data Contract Standard from Bitol/LF AI & Data) were not researched in this session. Current versions and the ODCS spec version are unverified.
- The IETF `Idempotency-Key` HTTP header draft's 2026 status (RFC or not) was not checked.
- Certificate Transparency specifics (RFC 6962 / RFC 9162, Chrome CT policy, the static CT API) were not re-verified here beyond DDIA2's reference.

---

## 5. Ethics: predictive analytics and automated decisions, bias and accountability (named cases), feedback loops, privacy and tracking, surveillance, consent and choice, data as asset vs liability (breaches and fines), the engineer's responsibility

### Takeaway
DDIA2's last chapter argues that data systems are mostly about people. Engineers own the consequences, and an ethics checklist is no substitute for ongoing reflection with the people affected. Predictive systems learn from biased history and amplify it through proxies. COMPAS false-positive rates were 44.9% for Black vs 23.5% for white defendants. Optum's cost-as-proxy algorithm under-referred Black patients; fixing it would raise their share of extra-care referrals from 17.7% to 46.5%. Automated decisions at scale can lock people out of society ("algorithmic prison") with no appeal. In 2026 this became a record enforcement action: the Dutch DPA fined Uber €824.99M for fully automated driver deactivations. Tracking turns users from customers into surveillance subjects. Consent is often neither informed nor free. Data is a liability as well as an asset: 23andMe's genetic data was sold in bankruptcy for $305M after a breach. The practical stance: minimize, set purposes, purge, and design for appeal and correction.

### Cited Findings
**DDIA2 framing (ch.14)**
- Every system has intended and unintended consequences, and engineers must consider them. Datasets are often about people, so human dignity comes first. Guidelines such as the ACM Code of Ethics exist but are rarely applied or enforced, and engineers can be cavalier about privacy. A technology is not good or bad in itself; what matters is how it is used. — DDIA2 p.585 [PDF 609]
- Ethics is not a compliance checklist. It is participatory, iterative reflection in dialog with those affected, with accountability for results. — DDIA2 p.586 [PDF 610]
- Predictive analytics on weather or epidemics differs from predicting reoffending, loan default or insurance claims, because the latter directly affect individuals. Organizations rationally say "no" when in doubt, but someone wrongly labeled risky accumulates many "no"s. Davidow called this "algorithmic prison" (2014). Unlike criminal justice, there is no presumption of innocence and little chance of appeal. — DDIA2 p.586 [PDF 610], ref [10]
- On bias: the rules are inferred from data and the patterns are opaque. Biased input is learned and amplified. Proxies such as postal code or IP address can stand in for race in segregated areas. Cegłowski's line: machine learning as money laundering for bias (2016). Prediction extrapolates the past, so a better future takes moral imagination that only humans can supply. — DDIA2 pp.586-587 [PDF 610-611], ref [15]
- On accountability: who is responsible when an algorithm errs, e.g. a self-driving crash or a discriminatory credit model? Can you explain the decision to a judge? A credit score reflects how *you* behaved; predictive analytics asks how people *similar to you* behaved, which amounts to stereotyping. Errors from bad data are nearly impossible to contest. A statistically correct distribution can still be wrong for an individual (life expectancy 80 does not mean dying at 80). The same analytics can direct aid or target vulnerable people for predatory products. — DDIA2 pp.587-588 [PDF 611-612]
- Feedback loops:
  - Recommendation systems create echo chambers.
  - An employer using credit scores can trap someone in a downward spiral of joblessness, missed payments and a lower score.
  - Algorithmic pricing at German gas stations reduced competition and raised prices.
  - DDIA2's remedy is systems thinking that models the people around the software. — DDIA2 pp.588-589 [PDF 612-613], ref [21]
- The German gasoline study (Assad, Clark, Ershov, Xu): in the 2020 working paper, duopoly market margins do not change when one station adopts algorithmic pricing but rise **28%** when both do. The published *JPE* 132(3) (2024) version says margins rise only when all stations in duopoly or triopoly markets adopt. Treat 28% as the working-paper estimate. — [CESifo WP 8521](https://cesifo.org/en/publications/2020/working-paper/algorithmic-pricing-and-competition-empirical-evidence-german); [IDEAS/JPE](https://ideas.repec.org/a/ucp/jpolec/doi10.1086-726906.html)
- Privacy and tracking: if a system stores only what the user entered for their own purpose, the user is the customer. Once activity is tracked as a side effect, especially in ad-funded businesses, advertisers become the customer and the relationship becomes surveillance. Thought experiment (Bernstein 2015): replace "data" with "surveillance" and see how the phrases sound. DDIA2 jokes about "Designing Surveillance-Intensive Applications". — DDIA2 pp.589-590 [PDF 613-614], ref [23]
- Surveillance examples:
  - Microphones in every room via phones, TVs, assistants and toys.
  - Car driving data used for insurance without consent: FTC action against General Motors, January 2025 (DDIA2 ref [28]).
  - Smartwatch motion sensors inferring typed passwords (Beltramelli 2015).
  - "Nothing to hide" only holds for people aligned with existing power. — DDIA2 pp.590-591 [PDF 614-615]
- Problems with consent: it is unclear why tracking is necessary. Privacy policies obscure. Data about one user reveals things about non-users. Derived datasets combining the whole user base with external data are exactly what users cannot understand. There is no negotiation. Opting out of near-mandatory services (smartphones, social networks, search) carries a social cost, and engagement-maximizing designs borrow from gambling. — DDIA2 pp.591-592 [PDF 615-616], refs [30] Zuboff 2015, [34]
- GDPR consent must be freely given, specific, informed and unambiguous, and withdrawable without detriment; pre-ticked boxes don't count. Consent is one lawful basis among several (legal obligation, vital interests, legitimate interest such as fraud prevention), but it is the most common online. — DDIA2 p.592 [PDF 616], ref [32]
- Privacy is a **decision right** (choosing what to reveal to whom), not secrecy, so "privacy is dead" is a misunderstanding. Surveillance **transfers** that right to the collector, which exercises it for profit (e.g. ad targeting by illness). Systems should expect data to be wrong or inappropriate and build mechanisms to handle that, e.g. memories that resurface painful events. Privacy settings control what other users see, not what the company does. — DDIA2 pp.592-594 [PDF 616-618], refs [30], [35]
- Data as assets and power:
  - "Data exhaust" is the wrong frame; under ad funding, user activity is closer to labor.
  - Data brokers trade personal data.
  - Governments obtain data by deals, coercion, legal compulsion or theft.
  - Personal data is sold in bankruptcies.
  - Breaches happen disconcertingly often.
  - Hence "toxic asset" (Schneier 2016), "hazardous material" (Cory Scott 2016), "the new uranium" (Pesce 2024).
  - Collectors should consider all future governments, not just today's. Schneier: installing technology that could enable a police state is "poor civic hygiene". — DDIA2 pp.594-595 [PDF 618-619], refs [36]-[40]
- Industrial Revolution analogy: pollution, child labor and unsafe factories were eventually regulated, regulation raised the cost of business, and society benefited. Schneier: data is the pollution problem of the information age. — DDIA2 pp.595-596 [PDF 619-620], ref [26]
- Legislation and self-regulation: GDPR purpose limitation and data minimization directly contradict "big data" maximal collection and exploratory reuse. GDPR affected ad tech (Wang et al., JMR 2023) but, per DDIA2, has been weakly enforced (Ryan, *The Economist*, May 2023) without much cultural change. Medical data shows the trade-off: sharing creates privacy risk and could also save lives. DDIA2 calls for a culture shift: treat users as humans, not metrics; self-regulate; educate users; purge data when no longer needed; minimize collection. "Data you don't have" cannot leak or be compelled. Librarians purging patron records is a model (Guardian 2016). — DDIA2 pp.596-597 [PDF 620-621], refs [45]-[49]
- DDIA2's ch.1 already raises the law: GDPR erasure versus append-only logs, and data minimization (*Datensparsamkeit*) versus speculative retention. — DDIA2 pp.24-25 [PDF 48-49], refs [60] Shastri et al. VLDB 2020, [61] Fowler 2013

**Named cases (verified this session)**
- **COMPAS (ProPublica, "Machine Bias", 23 May 2016):**
  - More than 7,000 people arrested in Broward County, FL in 2013-14 were followed for two years.
  - Only **20%** of those predicted to commit violent crimes did so. About **61%** of those labeled likely to reoffend were rearrested for any crime.
  - False positives: **44.9%** of Black vs **23.5%** of white defendants. False negatives: **47.7%** white vs **28.0%** Black.
  - After controlling for criminal history, age and gender, Black defendants were **77%** more likely to be scored higher risk for violent crime and **45%** for any crime. — [ProPublica](https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing)
- **Optum care-management algorithm (Obermeyer et al., *Science*, Oct 2019):** the model predicted cost as a proxy for need. Because less is spent on Black patients with the same illness, they were under-flagged. Fixing the label would raise the share of Black patients receiving extra help from **17.7% to 46.5%**. — [Techxplore summary of Science paper](https://techxplore.com/news/2019-10-algorithms-racial-bias-healthcare.pdf); [Nature news PDF](https://media.nature.com/original/magazine-assets/d41586-019-03228-6/d41586-019-03228-6.pdf); [Vice](https://vice.com/en/article/significant-racial-bias-found-in-national-healthcare-algorithm-affecting-millions-of-people)
- **Uber automated deactivations (Dutch AP, 21 Aug 2026), the record ADM fine:**
  - Fine: **€824,990,000** for breaching the GDPR ban on fully automated decision-making and failing to inform drivers about automated decisions and profiling.
  - Conduct, 2018-2022: accounts were deactivated automatically on suspected fraud or low ratings, without human review. Uber has since stopped.
  - The case began with complaints from **171 French drivers** via the Ligue des droits de l'Homme to CNIL, and was handled by the AP under one-stop-shop.
  - Uber is appealing. This is the AP's fourth Uber fine, after €600k (2018), €10M (2023) and €290M (2024). — [EDPB news](https://edpb.europa.eu/news/dutch-dpa-fines-uber-eur-824-990-000-for-unlawful-automated-decision-making-and-insufficient_en); [Pearl Cohen](https://www.pearlcohen.com/dutch-data-protection-authority-fines-uber-e825-million-for-fully-automated-deactivation-of-drivers/); [Dutch IT Channel](https://www.dutchitchannel.nl/news/758232/ap-heeft-uber-een-boete-van-bijna-825-miljoen-euro)
- ***Mobley v. Workday* (N.D. Cal. 3:23-cv-00770):** the plaintiff alleges Workday's AI applicant screening discriminated by race, age and disability, reproducing historical disparities through proxy variables. Rulings so far:
  - May 2025: ADEA claims allowed to proceed as a collective action (Judge Rita Lin).
  - Early March 2026: the argument that age law doesn't protect applicants was rejected.
  - 9 Mar 2026: the disability claim was dismissed for insufficient facts.
  - Mid/late June 2026: state-law claims largely survived; dates conflict between 16 and 22 June.
  - 1 Jul 2026: a Fourth Amended Complaint was ordered.
  - **No merits liability finding** as of Nov 2026. Secondary sources conflict on some dates, so check the docket. — [Holland & Knight, May 2025](https://www.hklaw.com/en/insights/publications/2025/05/federal-court-allows-collective-action-lawsuit-over-alleged); [Fisher Phillips](https://www.fisherphillips.com/en/news-insights/discrimination-lawsuit-over-workdays-ai-hiring-tools-can-proceed-as-class-action-6-things); [Akin](https://www.akingump.com/en/insights/ai-law-and-regulation-tracker/court-allows-discrimination-claims-against-ai-hiring-tool-to-proceed-or-mobley-v-workday-inc); [Pulse/HR Dive](https://www.pulse.bot/human-resources/news/workday-takes-partial-loss-as-judge-refuses-to-dismiss-claims-in-ai-bias-lawsuit-f7ca8be8-ab5a-4b87-97b2-f5a66ef5e2f9)
- **23andMe (data as asset and liability):**
  - A 2023 credential-stuffing breach followed.
  - The UK ICO issued a notice of intent for £4.59M on the day 23andMe filed Chapter 11 (Mar 2025), then fined **£2.31M** (5 Jun 2025, 155,592 UK users).
  - The bankruptcy court approved the sale to TTAM Research Institute (led by co-founder Anne Wojcicki) for **$305M**, over Regeneron's $256M. The assets include genetic data of more than **13 million** customers.
  - TTAM promised not to transfer the genetic data in a later bankruptcy except to a qualified entity adopting its privacy policy.
  - 27 states plus DC sued to require opt-in consent. The sale closed around 14 Jul 2025. — [Bloomberg Law](https://news.bloomberglaw.com/litigation/23andme-wins-approval-of-305-million-genetic-data-asset-sale); [GovInfoSecurity](https://www.govinfosecurity.com/court-approves-23andme-sale-to-ttam-research-institute-a-28885); [Enterprise Times](https://www.enterprisetimes.co.uk/2025/06/18/ico-fines-23andme-2-31-million/); [Freevacy](https://www.freevacy.com/news/ico/ico-announces-ps459m-23andme-fine-same-day-company-files-for-bankruptcy/6226)

### Inferences
**Concept card: automated decisions**
- *Problem:* decisions at scale need consistency and speed.
- *Simplest version:* a model score with a threshold and an automatic action.
- *Where it breaks:* a proxy label (Optum's cost-for-need gives 17.7% vs 46.5%), disparate error rates (COMPAS 44.9% vs 23.5% false positives), no human review or appeal (Uber's €824.99M).
- *Improvement:* human-in-the-loop review for significant decisions, recorded reasons, contestation channels, per-group error monitoring and audits of label choice.
- *Engineering link:* "reads are events too" (Q3) lets you log what the model saw and decided, which an explanation or appeal needs.
- *Misconceptions:*
  - "Removing the race column removes bias." Proxies remain.
  - "Accurate on average means fair to individuals." DDIA2's life-expectancy point says otherwise.
  - "The vendor is responsible, not us." The deployer is accountable too; Workday shows vendors can also be pulled in.

**Concept card: feedback loops**
- *Problem:* predictions change the world that generates the next training data.
- *Simplest version:* retrain on logged outcomes.
- *Where it breaks:* self-reinforcement (credit-score hiring spirals, algorithmic price coordination of +28% margins in duopolies per the working paper).
- *Improvement:* systems thinking, counterfactual or holdout data, and monitoring of distribution shift across groups.

**Concept card: data as liability**
- *Problem:* data has option value, so teams keep everything.
- *Simplest version:* keep it forever "in case".
- *Where it breaks:* breach costs and fines (23andMe's £2.31M ICO fine plus a $305M asset sale of DNA data), compelled disclosure, and erasure obligations that are expensive in immutable systems (Q6).
- *Improvement:* purpose-tagged collection, TTL by default, per-subject keys for crypto-shredding, aggregation or anonymization at ingest where possible.
- *Misconception:* "anonymized = hashed identifiers." That is pseudonymization, which is still personal data; EDPB issue 7 in Q6 shows controllers get this wrong.

- **The engineer's responsibility** maps onto the ACM Code of Ethics (2018). Principles 1.1 (contribute to society and human well-being), 1.2 (avoid harm), 1.6 (respect privacy) and 2.5 (thorough evaluations of systems and their impacts, including risks) are those most relevant to data systems. Code at https://www.acm.org/code-of-ethics; DDIA2 ref [2]. Principle numbering is from training knowledge and was not re-fetched; verify the wording before quoting.

### Gaps
- Several canonical cases were **not re-verified this session** and need sources before use:
  - Amazon's scrapped recruiting model (Reuters, Oct 2018).
  - The Dutch childcare-benefits scandal (toeslagenaffaire): government resignation Jan 2021, and the AP's €2.75M fine on the Tax Administration for nationality-based processing.
  - Australia's Robodebt (A$1.8B settlement 2020; Royal Commission report July 2023).
  - Michigan's MiDAS unemployment-fraud system.
  - The UK 2020 A-level grading algorithm.
  - SyRI (Hague court, Feb 2020).
  - The FTC's Rite Aid facial-recognition order (Dec 2023).
  - Predictive policing feedback loops (Lum & Isaac 2016; Ensign et al. 2018).
- Breach examples beyond 23andMe were not re-verified: Equifax 2017, Change Healthcare 2024, National Public Data 2024, Snowflake-customer breaches 2024. Nor were other big GDPR fines: Meta €251M (Dec 2024), LinkedIn €310M (Oct 2024), Clearview €30.5M (Sep 2024).
- The FTC GM final order (2025/2026 status) was not checked beyond DDIA2's Jan 2025 reference. A **$12.75M** California action against GM over driving data (reported ~May 2026) appeared in only one low-quality source and is **unverified**.

---

## 6. Law as of November 2026 (GDPR, CCPA/CPRA, EU AI Act, EU Data Act, other regimes) and how erasure collides with immutable logs, backups, Kafka, event sourcing and Iceberg snapshots; techniques (crypto-shredding, tombstones plus compaction, retention, row-level deletes plus snapshot expiry)

### Takeaway
Enforcement in 2025-2026 moved toward **automated decisions and transparency**:
- Uber's €824.99M ADM fine (Aug 2026) is the second-largest GDPR fine ever, after Meta's €1.2B (2023).
- Courts can also undo fines: Amazon's €746M was annulled in March 2026 and remitted to the regulator.
- The EDPB's 2025 coordinated action found erasure handled at only an "average" level. **Back-ups** and fake **anonymization** were named problem areas.
- The **EU AI Act** high-risk deadlines were pushed back by the Digital AI Omnibus, in force 27 Jul 2026: Annex III to 2 Dec 2027, Annex I to 2 Aug 2028. Article 50 transparency still applied from 2 Aug 2026.
- The **EU Data Act** has applied since 12 Sep 2025, with access-by-design from 12 Sep 2026 and cloud switching charges abolished from 12 Jan 2027.
- California's new CCPA regulations took effect 1 Jan 2026, with ADMT duties from 1 Jan 2027, and DROP bulk deletion has bound data brokers since 1 Aug 2026.
- India's DPDP core duties start 13 May 2027.

For engineers, "erase without undue delay" collides with every append-only structure: logs, LSM tombstones, compacted topics, lakehouse snapshots, backups and derived views. The techniques are tombstones plus *bounded* compaction, time retention, per-subject encryption keys (crypto-shredding), row-level deletes *plus* data-file rewrite *plus* snapshot expiry, and tracked re-application of deletions on backup restore. Each removes data on its own clock, so the system needs an erasure SLA and a way to verify it.

### Cited Findings
**GDPR enforcement and fines (2025-2026)**
- Largest GDPR fine is still **Meta €1.2B** (Irish DPC, May 2023, EU-US transfers). Largest 2025 fine: **TikTok €530M** (DPC, May 2025). Estimated 2025 totals range €1.15B-€1.4B. Cumulative totals: about €6.1B (CMS report, March 2026 cutoff) to about €7.56B (CMS tracker, Oct 2026). Totals vary with scope and date. — [CMS Enforcement Tracker: numbers and figures](https://cms.law/en/int/publication/gdpr-enforcement-tracker-report/numbers-and-figures); [Privacyterms top 50](https://privacyterms.io/biggest-gdpr-fines-all-time)
- **Uber €824,990,000**, Dutch AP, 21 Aug 2026: the second-largest GDPR fine, for fully automated deactivations and lack of information; under appeal. — [EDPB news](https://edpb.europa.eu/news/dutch-dpa-fines-uber-eur-824-990-000-for-unlawful-automated-decision-making-and-insufficient_en)
- **Amazon €746M** (CNPD Luxembourg, July 2021) was **annulled** by the Luxembourg Administrative Court on 12/13 Mar 2026. The court held that the CNPD had not determined intent vs negligence and had not adequately considered a more lenient measure. It **upheld the substance** of the breaches and sent the case back to the CNPD, which may set a new penalty. — [Paperjam](https://en.paperjam.lu/article/eu746m-fine-cnpd-decision-against-amazon-overturned); [Chronicle.lu](https://chronicle.lu/category/legal-ip/60106-luxembourg-court-annuls-cnpd-ruling-in-amazon-data-protection-case); [Freevacy/Reuters](https://www.freevacy.com/news/reuters/luxembourg-court-upholds-amazons-appeal-annuls-eur746m-gdpr-fine/7210); [CMS Luxembourg](https://cms.law/en/int/publication/gdpr-enforcement-tracker-report/luxembourg)
- One tracker lists a Madrid court's €479M "Meta, Spain" award. It is unfair-competition damages, not a GDPR fine, and should be excluded from GDPR rankings. — noted in [CMS/aggregator comparison via search](https://cms.law/en/int/publication/gdpr-enforcement-tracker-report/numbers-and-figures)

**EDPB Coordinated Enforcement Framework 2025: right to erasure (Art. 17)**
- The report was adopted **10 Feb 2026** and published **18 Feb 2026**. **32** supervisory authorities took part. **7,943** controllers were contacted and **764** responded. Overall compliance was assessed as "average". The CEF 2026 topic is transparency (Arts. 12-14). — [EDPB CEF report PDF](https://www.edpb.europa.eu/system/files/2026-02/edpb_cef-report_2025_right-to-erasure_en.pdf); [EDPB page](https://www.edpb.europa.eu/documents/coordinated-enforcement-framework/coordinated-enforcement-action-implementation-of-the-0_en); [Reed Smith](https://www.reedsmith.com/our-insights/blogs/viewpoints/102mm9l/edpb-report-on-the-right-to-erasure-key-takeaways-from-the-2025-coordinated-enfo/)
- The seven recurring issues:
  1. No documented, current erasure procedure.
  2. Inadequate training.
  3. and 4. Information and decision-making problems: privacy notices and refusals or postponements made without legal input.
  5. Difficulty defining and implementing retention periods.
  6. **Deletion in back-ups.**
  7. **Anonymization used inefficiently as a substitute for deletion.** — [EDPB CEF report PDF](https://www.edpb.europa.eu/system/files/2026-02/edpb_cef-report_2025_right-to-erasure_en.pdf)
- On backups (issue 6):
  - **Half** of responding SAs raised concerns.
  - Many controllers had no specific procedure and relied on generic automatic deletion or backup retention periods.
  - Some said a backup must be preserved whole, so parts cannot be changed.
  - Long, incremental deletion cycles made "without undue delay" hard to show.
  - Where modifying backups is inadvisable (integrity, e.g. ransomware recovery), controllers should track erasure requests and re-apply them to restored systems.
  - Recommendations: follow established erasure standards, verify erasure and be able to demonstrate it.
  - Best practices seen: overwriting the personal data with random strings; tooling that moves a subject's data, on reaching retention end, into an isolated system and permanently erases it one month later. — [EDPB CEF report PDF, §4.2.6](https://www.edpb.europa.eu/system/files/2026-02/edpb_cef-report_2025_right-to-erasure_en.pdf)
- On anonymization (issue 7): controllers commonly substitute anonymization for deletion, often to keep analytics, and are unsure what legally and technically counts as anonymous (Recital 26). The EDPB is drafting guidelines. The report also references EDPB **Guidelines 02/2025 on blockchain** processing. — [EDPB CEF report PDF, §4.2.7 and fn.14](https://www.edpb.europa.eu/system/files/2026-02/edpb_cef-report_2025_right-to-erasure_en.pdf)

**GDPR reform: Digital Omnibus (data/GDPR part)**
- The Commission's Digital Omnibus (Nov 2025) proposed changing the Art. 4(1) definition of personal data to depend on whether the processing entity can identify the person (a relative definition). EDPB-EDPS **Joint Opinion 2/2026** (Feb 2026) urged co-legislators not to adopt it. A Council compromise (Feb-Mar 2026) **dropped** the definition change, per an EDRi analysis of 17 Mar 2026. **Final adoption status was not found.** — [Inside Privacy](https://www.insideprivacy.com/eu-data-protection/eu-regulators-issue-opinion-on-revisions-of-gdpr-and-other-data-laws/); [Matheson](https://www.matheson.com/insights/edpb-edps-publish-opinion-on-digital-omnibus-proposal/); [EU Perspectives, May 2026](https://euperspectives.eu/2026/05/how-the-eu-nearly-weakened-the-worlds-toughest-data-protection-law/)

**EU AI Act (Regulation (EU) 2024/1689) and the Digital AI Omnibus**
- The Digital Omnibus on AI was endorsed by Parliament on 16 Jun 2026 and by the Council on 29 Jun 2026. It was published in the OJ on **24 Jul 2026** and has been **in force since 27 Jul 2026**. Secondary sources give its number as Regulation (EU) 2026/1744.
- Changes:
  - **Annex III** (stand-alone high-risk systems such as recruitment and credit scoring) moves from 2 Aug 2026 to **2 Dec 2027**.
  - **Annex I** (AI in regulated products: medical devices, machinery, vehicles) moves to **2 Aug 2028**.
  - **Art. 50** transparency obligations stay at **2 Aug 2026**, except a grace period to **2 Dec 2026** for watermarking systems already on the market. — [Sidley, 22 Jun 2026](https://datamatters.sidley.com/2026/06/22/eu-lawmakers-reach-provisional-agreement-to-delay-key-eu-ai-act-obligations/); [Orrick, Jul 2026](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes); [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/); [AI Act Explorer: Digital Omnibus](https://artificialintelligenceact.eu/ai-act-explorer/digital-omnibus/); [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-omnibus-vii-deadline-delay-20260/)

**EU Data Act (Regulation (EU) 2023/2854)**
- In force **11 Jan 2024**, with most obligations applicable from **12 Sep 2025**: B2B data sharing, and model contract terms for contracts concluded after that date.
- Access-by-design duty (Art. 3(1)) for connected products and related services placed on the market after **12 Sep 2026**.
- Switching charges between data processing (cloud) providers are fully abolished from **12 Jan 2027**.
- Chapter IV unfair-terms rules extend to certain older contracts (concluded on or before 12 Sep 2025, of indefinite duration or expiring at least 10 years after 11 Jan 2024) from **12 Sep 2027**.
- Sources conflict on some Chapter IV details; Art. 50 of the Regulation is authoritative. — [BIPT (Belgian regulator)](https://bipt.be/operators/digital/the-data-act/application-of-the-data-act); [Bird & Bird](https://www.twobirds.com/en/insights/2024/global/whats-next-for-the-eu-data-act); [McCann FitzGerald](https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/data-act-developments-2026-and-beyond); [Travers Smith](https://www.traverssmith.com/knowledge/knowledge-container/the-eu-data-act-compliance-countdown-for-connected-products/)

**California (CCPA/CPRA, Delete Act)**
- The CPPA regulations on risk assessments, ADMT and cybersecurity audits were approved in Sept 2025 and took effect **1 Jan 2026**.
  - Risk assessments are required from 1 Jan 2026. Assessments for processing that began before 2026 and continues are due by 31 Dec 2027, and attestations and summaries by **1 Apr 2028**.
  - **ADMT** obligations for significant decisions start **1 Jan 2027**.
  - Cybersecurity audit submissions are staggered, the first (revenue over $100M) reportedly due 1 Apr 2028; verify against the CPPA text. — [Thompson Coburn / JD Supra, Jan 2026](https://www.jdsupra.com/legalnews/california-s-2026-ccpa-regulations-7815698/); [National Law Review](https://natlawreview.com/article/newly-approved-ccpa-regulations-have-staggered-deadlines-compliance); [FPF issue brief](https://fpf.org/wp-content/uploads/2025/10/FPF_CCPA-Regulations-Issue-Brief.pdf)
- CPPA enforcement: **Tractor Supply $1.35M** (Sept 2025), which the CPPA called the largest in its history. PlayOn Sports $1.1M (Mar 2026). The AG's Disney settlement was $2.75M. — [Orrick InfoBytes](https://infobytes.orrick.com/2025-10-10/california-privacy-protection-agency-issues-record-1-35m-fine-to-retailer-over-consumer-privacy-violations/); [Mondaq (PlayOn)](https://www.mondaq.com/unitedstates/sport/1763082/youth-sports-media-company-to-pay-%24110-million-fine-in-cppa-enforcement-action); [National Law Review](https://natlawreview.com/article/escalated-ccpa-enforcement-delivers-record-275m-settlement-and-expanded-focus)
- **Delete Act / DROP:**
  - From **1 Aug 2026**, registered data brokers must access the DROP platform and process consumer deletion requests at least every **45 days**.
  - Penalty: **$200 per request per day** of non-compliance.
  - Reportedly more than 325,000 consumers had filed requests to more than 600 brokers by July 2026 (single source). — [CPPA: DROP for data brokers](https://privacy.ca.gov/drop-for-data-brokers/); [Fenwick](https://www.fenwick.com/insights/publication/dont-drop-ball-upcoming-changes-california-delete-act-five-key-steps-companies); [Alston & Bird](https://www.alstonprivacy.com/drop-is-coming-due-what-californias-delete-act-means-for-data-brokers-in-august/)

**Other regimes**
- **India DPDP Act 2023 + DPDP Rules 2025:**
  - Rules notified **13 Nov 2025**; the Data Protection Board and some rules took effect immediately.
  - Consent-manager registration from **13 Nov 2026**.
  - Core consent and data-fiduciary obligations from **13 May 2027**; one source says 12 May.
  - The old SPDI Rules 2011 apply in the interim. — [Hogan Lovells](https://ca.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-); [AZB Partners](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/); [YourStory](https://yourstory.com/2025/11/digital-personal-data-protection-dpdp-rules-2025-rollout-over-18-months)
- **Colorado AI Act (SB 24-205):** the effective date was moved from 1 Feb 2026 to **30 Jun 2026** by SB25B-004, signed 28 Aug 2025. Whether the 2026 session changed it again was **not found**. — [Greenberg Traurig](https://www.gtlaw.com/en/insights/2025/9/colorado-delays-comprehensive-ai-law-with-further-changes-anticipated); [Loeb & Loeb](https://www.loeb.com/en/insights/passle/2025/08/colorado-presses-pause-on-its-ai-act)

**Erasure versus immutability: what DDIA2 says**
- Event sourcing's immutability conflicts with GDPR deletion. A per-user log can be dropped whole, but multi-user logs cannot. Options are to store personal data outside events, or encrypt it with a deletable key (**crypto-shredding**). Both make recomputing derived state harder. — DDIA2 ch.3 p.104 [PDF 128], ref [68] Robinson 2019
- Limits of immutability (ch.12): privacy rules and leaks require true deletion, and appending a "deleted" event is not enough. Crypto-shredding keeps the ciphertext but makes it unusable; in DDIA2's words this partly just moves the problem to key management. Kreps: data loss is easy, but deleting data is "surprisingly hard". — DDIA2 ch.12 p.512 [PDF 536], refs [49] Kreps 2015, [50] Robinson 2019
- In LSM engines a deleted record can persist in higher levels until its tombstone has compacted through every level, which can take a long time. Specialist designs propagate deletions faster. — DDIA2 ch.4 p.132 [PDF 156]
- Sharding per tenant or person turns GDPR/CCPA access and deletion into simple per-shard export and delete operations. — DDIA2 ch.7 p.255 [PDF 279]
- Shastri et al., "Understanding and Benchmarking the Impact of GDPR on Database Systems", PVLDB 13(7), 2020, is DDIA2's reference for GDPR's effect on database design. — DDIA2 ch.1 ref [60] [PDF 55]

**Erasure mechanics in current tools (Kafka 4.4, Iceberg 1.12)**
- Kafka topic defaults (4.4):
  - `retention.ms` = 7 d, `segment.ms` = 7 d, `segment.bytes` = 1 GiB.
  - `delete.retention.ms` = 1 d, the time a tombstone itself is kept.
  - `min.compaction.lag.ms` = 0, `max.compaction.lag.ms` = Long.MAX, `min.cleanable.dirty.ratio` = 0.5.
  - Retention and cleaning are "always done a file at a time" (whole segments).
  - Compaction keeps at least the last value per key. A key with a null value is a tombstone, removed after `delete.retention.ms`.
  - **The active segment is never compacted.** `max.compaction.lag.ms` is a non-binding deadline. — earlier notes citing [Kafka 4.4 topic configs](https://kafka.apache.org/44/configuration/topic-configs/) and [design doc](https://kafka.apache.org/44/design/design/)
- Iceberg maintenance:
  - Expiring snapshots removes them from metadata and time travel. Data files are deleted only once no retained snapshot references them; the docs say regular expiration "deletes unused data files".
  - Orphan file deletion defaults to a **3-day** interval, and the docs warn that shorter intervals can corrupt tables with in-flight writes.
  - Compaction (`rewriteDataFiles`) merges small files.
  - Rewriting position delete files merges them and drops deletes that point at dead data files.
  - "Remove dangling delete files" is metadata-only. — [Iceberg docs: Maintenance](https://iceberg.apache.org/docs/latest/maintenance/)
- Iceberg format v2 introduced row-level deletes via delete files; v3 adds binary **deletion vectors** and table encryption keys. Iceberg 1.12.0 (29 Sep 2026) is current. Delta Lake 4.4.1 (Oct 2026) has had deletion vectors since 2.x/3.x. — earlier notes citing [Iceberg spec](https://iceberg.apache.org/spec/) and [Iceberg releases](https://iceberg.apache.org/releases/)

### Inferences
**Concept card: erasure in an append-only world**
- *Problem:* Art. 17 requires erasure "without undue delay". Data lives in a log, its derived views, caches, a lakehouse with time travel, and backups.
- *Simplest version:* `DELETE FROM users WHERE id = ?` in the system of record.
- *Where it breaks:*
  1. **Kafka:** the user's PII still sits in topic segments. Under the default delete policy it stays up to `retention.ms` (7 d) plus segment roll time. On compacted topics a tombstone only removes earlier values *for the same key*. PII embedded in other keys' values (an `OrderPlaced` keyed by orderId containing the name) is never removed. On a low-traffic topic the active segment may not roll for `segment.ms` (7 d), and `max.compaction.lag.ms` defaults to never.
  2. **Event sourcing:** events are meant to be immutable and replayable, and deleting them breaks replay and audit.
  3. **Iceberg/Delta:** a merge-on-read DELETE writes a delete file or deletion vector, and the original Parquet still holds the bytes. They go only after `rewrite_data_files`, then `expire_snapshots` past every snapshot that references the old file, plus orphan cleanup (≥3 d default). The time-travel window equals the legal exposure window.
  4. **Backups:** the EDPB found half of SAs concerned, and many controllers just wait for rotation.
  5. **Derived stores:** search indexes, caches and ML features each need the delete propagated; the tombstone must reach them before `delete.retention.ms` (1 d) expires for slow consumers.
- *Improvements:*
  - **Crypto-shredding:** a per-subject data key, PII fields encrypted, and the key deleted on request. Ciphertext anywhere (topics, backups, lakehouse) becomes unreadable at once, but keys must be kept out of long-lived backups. Whether GDPR treats ciphertext as personal data after key destruction is unsettled (see Gaps).
  - **PII out of events:** store a reference and keep PII in a deletable store (sometimes called the "forgettable payload" pattern).
  - **Per-subject keying** of PII topics, so tombstones work, with `max.compaction.lag.ms` set to the erasure SLA and a smaller `segment.ms`.
  - **Short retention by default.**
  - **Lakehouse deletes followed by scheduled rewrite and expiry** with a documented SLA.
  - **Backup erasure ledger:** a list of erased IDs that is re-applied on restore (the EDPB's recommendation).
  - **Verification:** scan for the subject's identifiers after the SLA to demonstrate erasure, as the EDPB asks.
- *Misconceptions:*
  - "Kafka compaction deletes immediately."
  - "Iceberg DELETE deletes bytes."
  - "Erasure is absolute." Art. 17(3) has exceptions and the EDPB notes the right is not absolute.
  - "Hashing an email anonymizes it."
  - "Backups are exempt."

- The AI Act delay matters for lesson framing. A course published in late 2026 should say that high-risk obligations for stand-alone systems such as hiring and credit **apply from 2 Dec 2027**, not Aug 2026, as many 2024-2025 materials state. Art. 50 transparency (chatbot disclosure, labeling of synthetic content) already applies.
- The 2026 GDPR fine pattern (Uber ADM, Amazon's annulment, CEF findings) supports teaching GDPR Art. 22 (automated decisions) and Art. 17 (erasure) as **engineering requirements**: human review queues, reason codes, deletion pipelines with SLAs.
- The Data Act's cloud-switching and access-by-design rules make **export of derived and raw data in machine-readable formats** a legal requirement for IoT and cloud providers, which ties to the "derived views are rebuildable" principle. This is an inference; the detailed format requirements were not fetched.

### Gaps
- **Status of crypto-shredding under GDPR:** no EDPB statement in the 2025 CEF report or elsewhere was found that explicitly accepts key destruction as erasure. EDPB Guidelines 02/2025 on blockchain were referenced but not read; they may address it. Treat the legal status as open.
- The final legislative outcome of the Digital Omnibus GDPR amendments (personal-data definition, breach notification, cookie rules) as of Nov 2026 was not found.
- Exact AI Act baseline dates (prohibitions from 2 Feb 2025, GPAI obligations from 2 Aug 2025, penalties up to €35M or 7% of turnover) come from training knowledge of Art. 113 and Art. 99 and were not re-fetched. The Omnibus's regulation number (2026/1744) comes only from secondary sources.
- UK Data (Use and Access) Act 2025, US state privacy laws in force in 2026 (count and dates), China PIPL and Brazil LGPD updates were not researched.
- Delta Lake's VACUUM default retention (believed 7 days) and its `REORG TABLE ... APPLY (PURGE)` requirement for deletion vectors were not re-verified.
- The quantitative findings of Shastri et al. (VLDB 2020), e.g. slowdown factors from GDPR features in Redis and PostgreSQL, were not read.
- GDPR article wording (Art. 5(1)(b),(c),(e); Art. 17; Art. 22; Art. 25; Art. 83 limits of €20M or 4%) is from training knowledge; link EUR-Lex (https://eur-lex.europa.eu/eli/reg/2016/679/oj) and quote carefully.

---

## 7. Hands-on lab ideas (Kotlin on JVM 21+, Gradle, Testcontainers, Docker Compose, or pure-Kotlin simulation), each with a measurable number or reproducible anomaly

### Takeaway
Seven labs make the chapter's claims observable:
- Labs 1-4 are required: duplicates under check-then-insert vs zero duplicates via a partitioned log; a $22 transfer and duplicate rows until a request ID is carried end to end; plaintext gone and decryption failing after crypto-shredding while aggregates survive replay; an audit job that finds injected drift and pinpoints it with a Merkle diff.
- Labs 5-7 are optional extensions: kappa reprocessing with an event-time vs processing-time anomaly, read-your-writes staleness measured and then eliminated, and an erasure-SLA stopwatch across Kafka and Iceberg.
- All reuse the earlier pin set: JDK 25 toolchain (target ≥21), Gradle 9.9.0, Kotlin 2.4.21, kotlinx-coroutines 1.11.0, kafka-clients/streams 4.4.0, Testcontainers 2.0.5 (`org.testcontainers.kafka.KafkaContainer` with `apache/kafka:4.4.0`), JUnit 6.1.3.

### Cited Findings
- Lab pin set (Nov 2026) and Testcontainers Kafka module coordinates, from the earlier research. — `research_notes/Systems course curriculum research/kafka.md` (sources cited there)
- The username-claim algorithm, the multi-shard payment design and Example 13-1/13-2 are specified in DDIA2 pp.563-570 [PDF 587-594]. Kreps's 2014 reprocessing recipe is in [O'Reilly](https://www.oreilly.com/radar/questioning-the-lambda-architecture/). Kafka compaction parameters and defaults come from the Kafka 4.4 docs via the earlier notes. Iceberg expiry and orphan semantics come from [Iceberg maintenance](https://iceberg.apache.org/docs/latest/maintenance/). EDPB's "verify erasure and be able to demonstrate it" comes from the [EDPB CEF report](https://www.edpb.europa.eu/system/files/2026-02/edpb_cef-report_2025_right-to-erasure_en.pdf). Feral duplicates under default isolation come from [Bailis et al. 2015](https://amplab.cs.berkeley.edu/wp-content/uploads/2015/06/feral-sigmod2015.pdf).

### Inferences
**Lab 1: Username claims through a partitioned log (pure Kotlin first, then Kafka)**
- *Part A, anomaly:* two "replicas", each a coroutine with its own `HashMap`, accept claims with async replication (multi-leader). Alternatively, one shared store with check-then-insert across `Dispatchers.Default`, without a lock or with READ COMMITTED Postgres via Testcontainers. Fire 10,000 claims over 1,000 names from 64 concurrent clients. *Measure:* the count of names granted to more than one requester. Expect >0, mirroring Feral's ~700 duplicates.
- *Part B, the fix:* N partitions, each a single-consumer `Channel` with a deterministic processor keeping `taken: MutableMap<String, RequestId>`. Route by `abs(username.hashCode()) % N`. Reply on a per-request `CompletableDeferred`. *Measure:* duplicates = 0. Throughput at N = 1, 2, 4, 8 should be near-linear until CPU-bound. Record p50/p99 wait-for-reply latency; that is the timeliness cost.
- *Part C, Kafka:* topic `username-claims` with 8 partitions, keyed by username, read by a consumer group. State lives in a compacted changelog topic. Results go to `claim-results`, keyed by requestId. Kill the processor container mid-run (`docker stop`). It restarts, replays at-least-once, rebuilds state from the changelog and emits the same decisions; clients dedupe by requestId. *Assert:* zero duplicate grants, plus the number of duplicate result messages each client ignored, which shows at-least-once in action.
- *Part D, reproducible bug:* key by `userId` instead of `username`. Duplicates reappear, which shows the key choice *is* the constraint.

**Lab 2: End-to-end idempotency with a request ID**
- Pipeline: Ktor HTTP endpoint → Kafka `transfers` (idempotent producer on by default in 4.4) → consumer → Postgres `accounts` and `ledger` (Testcontainers).
- Fault injection:
  - (i) A proxy that drops the HTTP response after the server commits, so the client times out and retries. Toxiproxy via Testcontainers, or an in-process interceptor.
  - (ii) Kill the consumer after the DB write and before the offset commit.
- *Variants and the expected count of extra ledger rows per 1,000 transfers:*
  - (a) No request ID: >0. Reproduces DDIA2's $11 → $22.
  - (b) Idempotent producer only: still >0, because app-level retries are new records.
  - (c) Kafka EOS read-process-write into an output topic: still >0 for the external DB.
  - (d) A client UUIDv7 `Idempotency-Key` carried through the HTTP header, the Kafka header and a `UNIQUE (request_id)` row inserted in the same DB transaction as the balance update (or `INSERT ... ON CONFLICT DO NOTHING` gating the update): exactly 0.
- Extra measurement: the dedupe-table retention needed. Set it below the client's max retry horizon and show a late retry becomes a duplicate again, the same as Stripe's 24 h pruning.

**Lab 3: Crypto-shredding a user's events in a Kafka-backed event store**
- Setup:
  - Event topic `account-events` (delete policy, long retention).
  - Key store: a compacted topic `subject-keys` (key = subjectId, value = DEK wrapped by a KEK held in the app or in a Vault dev container), or a Postgres table.
  - PII fields (name, email, address) are encrypted per subject with AES-256-GCM (`javax.crypto`). A marker string such as `ZZ-PLAINTEXT-<uuid>` is embedded so plaintext is easy to grep.
  - A projection `account_summary` holds per-user PII plus aggregate counts and amounts.
- Erasure: delete the DEK (tombstone `subject-keys`, and drop any cached copy).
- *Proofs and measurements:*
  - (1) Scan raw segment files (`kafka-dump-log.sh --print-data-log` inside the container) or consume the whole topic. Count plaintext marker hits: 0 before and after, because the data was always encrypted. Count successful decrypts for the subject: N before, 0 after (`AEADBadTagException` or missing key).
  - (2) Rebuild the projection from offset 0. The subject's PII renders `[erased]` while global aggregates are unchanged (sum of amounts identical), which shows replay survives erasure.
  - (3) Time how long the DEK bytes linger in `subject-keys` segments: defaults (active segment never compacted, `segment.ms`=7 d) vs tuned (`segment.ms`=10 s, `min.cleanable.dirty.ratio`=0.01, `max.compaction.lag.ms`=30 s, `delete.retention.ms`=1 s). Use Awaitility with generous timeouts, since cleaner timing is flaky (noted in the earlier Kafka notes).
  - (4) **Pitfall:** snapshot the key store into a "backup" before erasure, restore it, and show the data decrypts again. The lesson is that keys need a shorter, separately governed backup policy, or an "erased IDs" list re-applied on restore (EDPB issue 6).
- Contrast run without encryption: tombstone a keyed PII topic and show plaintext persists in the active segment until it rolls. PII embedded under other keys is never removed.

**Lab 4: Audit job, recompute a derived view and diff it against the live one**
- A live streaming consumer maintains `balances` (Postgres or RocksDB) from `transfers`. A batch auditor replays the topic from offset 0 into an in-memory map and diffs it per key.
- Bugs to inject, one at a time:
  - (a) A consumer that drops 0.1% of records.
  - (b) A non-idempotent `balance += amount` with redelivery after a kill.
  - (c) A "bit-flip" UPDATE on 3 random rows, simulating SDC or a bad migration.
  - (d) A schema bug that truncates amounts to integers.
- *Measure:* mismatched keys and total absolute drift for each bug.
- Add a **Merkle tree** over key ranges (e.g. 2^10 leaves) in both live and recomputed views. Find mismatched ranges by descending only into differing subtrees, and count hash comparisons against a full scan, e.g. ~10·k vs 1,000,000 for k bad keys.
- Add a **hash chain** over the event log (each record stores `H(prev ‖ payload)`). Tamper with one historical event and show verification fails at exactly that offset.

**Lab 5 (optional): Kappa reprocessing and the event-time anomaly**
- Change the derivation, e.g. per-day revenue v2 with currency conversion. Start a second consumer group from offset 0 writing `revenue_v2`, track lag to zero, switch reads with a flag, and roll back.
- *Measure:* catch-up time per million events.
- *Anomaly:* implement v2 with processing-time windows first. Replaying 30 days puts all revenue into "today". Then fix with event-time windows (Kafka Streams `TimestampExtractor`, or Beam).

**Lab 6 (optional): Timeliness vs integrity**
- After `POST /transfer`, immediately `GET /balance` from the projection. *Measure:* the fraction of stale reads and the p99 staleness (ms) under load.
- Then implement "wait for my offset": the POST returns the Kafka offset, and the GET blocks until the projection's applied offset ≥ that value. Stale reads go to 0% at the cost of latency.
- Throughout, a background auditor (Lab 4) confirms integrity was never violated, even while timeliness was.

**Lab 7 (optional): Erasure SLA stopwatch across stores**
- For one subject, issue an erasure and record time-to-unreadable in each store. Use a docker-compose Iceberg REST catalog plus object store from the earlier big-data notes for the lakehouse part.
- Stores and expected timings:
  - Postgres row: immediate.
  - Kafka keyed PII topic: depends on segment roll plus cleaner.
  - Kafka event topic with crypto-shredding: immediate on key deletion.
  - Iceberg table: DELETE (MoR deletion vector), then the bytes remain until `rewrite_data_files` plus `expire_snapshots`. Time travel to the pre-delete snapshot still shows the row until expiry.
- Output: a table of seconds-to-erasure per store, compared with a declared SLA.

### Gaps
- Exact Kafka cleaner timings in Testcontainers were not measured. Labs 3 and 7 need empirical calibration and generous timeouts.
- Whether Toxiproxy's Testcontainers module works with Testcontainers 2.0.5 was not checked.
- An Iceberg Kotlin/Java client path without Spark, i.e. calling `expireSnapshots()` and `rewriteDataFiles` from the Iceberg Java API in a pure-JVM lab, was not verified. Spark may be needed for `rewrite_data_files`.
- No existing open-source Kotlin implementation of these labs was found to reuse.
