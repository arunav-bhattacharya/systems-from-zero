# Transactions: ACID, isolation anomalies, serializability, distributed transactions (state as of November 2026)

Legend for source tags. **[read]** means I fetched the page or PDF this session and read the passage the claim rests on. **[prior]** means the fact comes from the earlier product-organized research round (`research_notes/Systems course curriculum research/*.md`, written 2026-11-07), which carries its own primary links; I did not re-fetch it. **[not re-read]** marks canonical papers or docs cited from background knowledge with their canonical URL; check the wording before quoting. "DDIA" means *Designing Data-Intensive Applications*, 2nd ed. (Kleppmann and Riccomini), chapter 8, from the local PDF (`/Users/arunav/Documents/learn/books & pdfs/architecture and software design/Designing Data-Intensive Applications ... .pdf`). DDIA page refs give the printed page first, then the 1-based PDF page; printed = PDF − 24. All DDIA content is paraphrased, and quotes stay under 15 words.

---

## 1. What ACID really means (and how loosely vendors use it); single-object vs multi-object operations; why retries after aborts are subtle

### Takeaway
ACID is four separate promises. Vendors use the label loosely: "ACID compliant" usually means atomic, durable commits at a default isolation level well below serializable. Atomicity really means *abortability*, consistency belongs to the application, isolation is the hard part, and durability is risk reduction. Aborting so the client can retry is what makes transactions useful. But a retry is only safe when the client knows the first attempt did not commit, and a lost commit acknowledgement makes that unknowable without idempotency keys.

### Cited Findings

**Framing and history (DDIA's angle)**
- DDIA opens chapter 8 with the Spanner paper's argument for 2PC. It is better to let developers handle performance problems from overusing transactions than to "always" code around their absence. — DDIA p.277 / PDF 301 [read]
- DDIA frames transactions as a deliberate abstraction, "not a law of nature", built to simplify the programming model. The Post Office Horizon scandal "was probably" caused by an accounting system lacking ACID transactions. — DDIA p.278 / PDF 302 [read]
- Most transactional databases follow the style of IBM System R (1975). Transaction support in MySQL, PostgreSQL, Oracle and SQL Server is "uncannily similar" to it 50 years later. — DDIA p.278 / PDF 302 [read]
- On NoSQL: the late-2000s NoSQL wave either dropped transactions or redefined the word. The belief that transactions can't scale "turned out to be wrong", and DDIA names CockroachDB, TiDB, Spanner, FoundationDB and YugabyteDB as the counterexamples. — DDIA p.279 / PDF 303 [read]
- Härder and Reuter coined ACID in 1983. DDIA says "ACID" has become "mostly a marketing term", and BASE is even vaguer: in effect it just means "not ACID". — DDIA p.279 / PDF 303 [read]

**Atomicity (A)**
- *Problem:* a client makes several writes and something fails partway through (crash, network cut, full disk, constraint violation). *Guarantee:* the database discards every write from the aborted transaction. DDIA suggests "abortability" would have been a better name. ACID atomicity is not about concurrency; in multithreaded programming "atomic" means something else, and that meaning belongs under I. — DDIA p.280 / PDF 304 [read]
- *Simplest single-node implementation:* write the data, then a commit record, to the WAL. The transaction is committed once the disk finishes writing the commit record, so a single disk controller makes the commit atomic. — DDIA p.323 / PDF 347 [read]

**Consistency (C)**
- The word has at least five meanings: replica consistency, consistent snapshots, consistent hashing, CAP's consistency (linearizability), and ACID's application-defined invariants. ACID's C is an application property. The database enforces only the invariants you declare (FK, UNIQUE, CHECK, triggers, materialized views). — DDIA p.280–281 / PDF 304–305 [read]

**Isolation (I)**
- Textbooks define isolation as serializability. In practice many databases ship weaker levels, and Oracle's "serializable" is actually snapshot isolation. — DDIA p.282 / PDF 306 [read]
- Default isolation levels: Read Committed in Oracle, PostgreSQL and SQL Server — DDIA p.292 / PDF 316 [read]. MySQL/InnoDB defaults to "repeatable read", which Hermitage classifies as only *monotonic atomic view*, and CockroachDB defaults to serializable. — [Hermitage](https://github.com/ept/hermitage) [read]

**Durability (D)**
- On one node, durability means fsync plus a WAL with checksums. With replication it means "copied to N nodes". Neither is perfect, for several reasons:
  - correlated faults;
  - asynchronous failover losing recent writes;
  - SSDs violating fsync guarantees on power loss;
  - a firmware bug that fails drives after exactly 32,768 hours;
  - PostgreSQL using fsync incorrectly "for over 20 years";
  - 30–80% of SSDs developing at least one bad block within four years;
  - worn SSDs losing data within weeks to months while unpowered.

  DDIA concludes that you should combine disk, replication and backups. — DDIA p.282–284 / PDF 306–308 [read]
- Real 2026 example: Jepsen found that MariaDB Galera lost acknowledged commits when all nodes crashed in quick succession under `innodb_flush_log_at_trx_commit=0`, a setting MariaDB's docs present as "a safer, recommended option". Even with `=1`, committed writes were occasionally lost under crashes plus partitions (MDEV-38974/38976). — [Jepsen: MariaDB Galera 12.1.2, 2026-03-16](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) [read]
- MySQL 8.0.34: with `innodb_flush_log_at_trx_commit=1` (the default), LazyFS crash tests lost no committed transactions; with `0`, data was lost. — [Jepsen: MySQL 8.0.34, 2023-12-19](https://jepsen.io/analyses/mysql-8.0.34) [read]

**Single-object vs multi-object operations**
- Storage engines almost always make single-object writes atomic and isolated. DDIA's example: a 20 kB JSON write should never leave a 10 kB fragment, a spliced old/new value, or a torn value visible to a reader. A log gives atomicity and a per-object lock gives isolation. — DDIA p.286 / PDF 310 [read]
- An atomic increment or compare-and-set is *isolated* in ACID terms, even though everyone calls it atomic. Such single-object operations "are not transactions in the usual sense". Aerospike's strong-consistency mode and the lightweight transactions in Cassandra and ScyllaDB give linearizable single-object conditional writes but no multi-object guarantee. — DDIA p.286 / PDF 310 [read]
- Multi-object transactions are needed in three cases: keeping foreign keys or graph edges valid, keeping denormalized copies in sync, and keeping secondary indexes consistent with the base data. DDIA's example is an email unread counter that disagrees with the mailbox (Fig. 8-2 dirty read; Fig. 8-3 atomicity). — DDIA p.284–287 / PDF 308–311 [read]
- Relational databases group a transaction's statements by TCP connection, between BEGIN and COMMIT. A key-value multi-put "doesn't necessarily" have transaction semantics: some keys can succeed while others fail. — DDIA p.285–286 / PDF 309–310 [read]
- NoSQL caveat in 2026: DynamoDB, MongoDB and Cassandra all offer multi-item transactions now, but the scopes differ:
  - DynamoDB: 100 items / 4 MB, single Region;
  - MongoDB: multi-document snapshot transactions with a default lifetime under one minute;
  - Cassandra 5.0: single-partition Paxos LWT only;
  - Cassandra 6.0: Accord, still alpha.

  — [prior: nosql.md §4] ([DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html), [MongoDB production considerations](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/), [Instaclustr on Cassandra 6 Accord](https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/))

**Aborts and retries: why they are subtle**
- Leaderless or best-effort stores won't undo work that partially succeeded, so the application has to clean up. ORMs such as Rails ActiveRecord and Django don't retry aborted transactions: the exception bubbles up and the user's input is lost. — DDIA p.287–288 / PDF 311–312 [read]
- DDIA's five retry caveats. — DDIA p.288 / PDF 312 [read]
  1. Commit succeeded but the acknowledgement was lost, so a retry applies it twice unless the app deduplicates.
  2. Retrying overload or contention aborts makes things worse. Cap retries and use exponential backoff.
  3. Retry only transient errors (deadlock, serialization failure, failover). Retrying a constraint violation is pointless.
  4. Side effects outside the database (such as email) happen even when the transaction aborts.
  5. If the client crashes mid-retry, its data is lost.
- Concrete forms of caveat 1:
  - CockroachDB returns SQLSTATE **40003, an "ambiguous" error**: the transaction may or may not have committed. Retryable conflicts return 40001. — [CockroachDB transactions](https://docs.cockroachlabs.com/docs/stable/transactions) [read]
  - Aurora DSQL tells developers to make transactions idempotent so that a retry can be the "first recourse". Its OCC returns SQLSTATE 40001 (OC000 for a data conflict, OC001 for a schema conflict) more often than lock-based PostgreSQL does. — [Aurora DSQL concurrency control](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html) [read]
- Named incident where internal retries broke isolation: Jepsen's MongoDB 4.2.6 analysis found read skew, G1c cycles and duplicated writes even at the strongest settings. MongoDB attributed them to a retry bug (SERVER-48307), with a fix planned for 4.2.8. — [prior: nosql.md] ([Jepsen: MongoDB 4.2.6, 2020-05-15](https://jepsen.io/analyses/mongodb-4.2.6))
- DynamoDB `TransactWriteItems` is idempotent through a client token that stays valid for **10 minutes**. A retry after 10 minutes is a new transaction. — [prior] ([DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html))
- PostgreSQL's docs say serialization failures (SQLSTATE 40001) should be retried, and deadlocks (40P01) generally too. — [prior: rdbms_sql.md] ([PostgreSQL 18: Serialization Failure Handling](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html))
- CockroachDB retries automatically on the server only while results stay under the 16 KiB result buffer (`sql.defaults.results_buffer.size`). Beyond that the client must retry (savepoint `cockroach_restart` protocol or app retry loop with exponential backoff). — [CockroachDB transactions](https://docs.cockroachlabs.com/docs/stable/transactions) [read]

### Inferences
- Teaching order: start with the failure list (crash mid-write, network cut, concurrent clients). Then teach A as "undo log + commit record", C as "your invariants", I as "pretend you're alone", and D as "survive power loss, with fine print". Then pivot to the retry loop: the retry loop is the programming model that ACID buys you, and its sharp edge (ambiguous commit) motivates idempotency keys. This later reappears as exactly-once processing (Q5).
- "ACID compliant" tells you almost nothing about isolation. In practice the default is RC (PostgreSQL, Oracle, SQL Server, CockroachDB optional), MAV-ish "RR" (MySQL) or SI (Aurora DSQL, TiDB). A course should teach learners to ask which anomalies the default allows.
- Misconceptions to address:
  1. "Atomic means concurrent-safe." It is about faults; I is about concurrency.
  2. "The DB guarantees consistency." Only declared constraints.
  3. "A multi-put is a transaction."
  4. "Retries are always safe." Not with lost acknowledgements, non-transactional side effects, or overload.
  5. "NoSQL has no transactions." Outdated since 2018, with scoped caveats.

### Gaps
- DDIA 2e's text for this section closely follows the 1st edition. New in 2e: the Post Office Horizon mention, the "NewSQL disproved unscalability" paragraph, and Aurora DSQL/TiDB as SI-only systems. I did not diff against the 1st edition, so treat this as an impression.
- No primary source found this session that quantifies how often commit acknowledgements are lost in practice.

---

## 2. Isolation anomalies as interleavings; ANSI levels and their problems (Berenson 1995, Adya 1999); the vendor naming mess (Hermitage); Jepsen/Elle findings 2020–2026

### Takeaway
Every anomaly is a specific interleaving of reads and writes. The SQL standard's four levels are defined by three English-language "phenomena" that are ambiguous and miss dirty writes, lost updates and write skew. Berenson et al. (1995) exposed this, and Adya (1999) replaced it with dependency-graph cycles (G0…G2), which Elle now checks automatically. Vendor level names don't line up: PostgreSQL RR and Oracle "serializable" are snapshot isolation, and MySQL RR is weaker still. From 2020 to 2026 Jepsen kept finding real violations: PostgreSQL SSI (fixed 2020), MySQL RR (2023), RDS Multi-AZ PostgreSQL Long Fork (2025), MariaDB Galera lost updates (2026), and ParticleDB (2026).

### Cited Findings

**Anomaly catalogue as concrete interleavings** (notation: `w1(x=3)` = T1 writes x=3; `r2(x)→3` = T2 reads 3; `c1`/`a1` = commit/abort). Codes follow Hermitage/Adya.

- **Dirty write (P0 / G0, "write cycles")**
  - *Problem:* two transactions overwrite each other's uncommitted writes on several rows.
  - *Interleaving* (DDIA Fig. 8-5, used-car sale): `w1(listing=Aaliyah) w2(listing=Bryce) w2(invoice=Bryce) c2 w1(invoice=Aaliyah) c1` → Bryce gets the car and Aaliyah gets the invoice.
  - *Fix:* row write locks held until commit. Every level above RU does this. — DDIA p.291–292 / PDF 315–316 [read]
- **Dirty read (P1 / G1a aborted read, G1b intermediate read)**
  - *Interleaving:* `w1(x=3) r2(x)→3 a1`. T2 acted on a value that never existed, so it needs a cascading abort.
  - DDIA's version: the mailbox shows a new email but the unread counter still says 0 (Fig. 8-2).
  - *Fix:* readers see the last committed version. Storing two versions works much better than read locks, which let one long writer stall every reader. Db2, and SQL Server with `read_committed_snapshot=off`, still use read locks. — DDIA p.290–293 / PDF 314–317 [read]
- **Lost update (P4)**
  - *Interleaving* (DDIA Fig. 8-1): counter = 42: `r1(c)→42 r2(c)→42 w1(c=43) c1 w2(c=43) c2` → 43, should be 44.
  - RC allows it because neither write is dirty. — DDIA p.281, 291, 299 / PDF 305, 315, 323 [read]
- **Read skew / non-repeatable read (A5A, Adya G-single)**
  - *Interleaving* (DDIA Fig. 8-6): Aaliyah has $500 in each of two accounts; a $100 transfer runs between them. `r2(acct1)→500 w1(acct1=600) w1(acct2=400) c1 r2(acct2)→400` → she sees $900 total.
  - RC allows it. It is fatal for backups, analytics and integrity checks. — DDIA p.293–294 / PDF 317–318 [read]
- **Write skew (A5B, Adya G2-item)**
  - *Interleaving* (DDIA Fig. 8-8, on-call doctors, invariant ≥1 on call): `r1(count on-call)→2 r2(count)→2 w1(Aaliyah.on_call=false) w2(Bryce.on_call=false) c1 c2` → 0 doctors on call.
  - It is neither a dirty write nor a lost update because the two writes hit different rows. — DDIA p.303–304 / PDF 327–328 [read]
- **Phantom causing write skew (Adya G2, predicate anti-dependency)**
  - *Interleaving* (DDIA Example 8-2, meeting rooms): `r1(COUNT bookings room 123 noon–1pm)→0 r2(...)→0 w1(INSERT booking) w2(INSERT booking) c1 c2` → double booking.
  - The same shape appears in claiming a username, double-spending and multiplayer games.
  - `SELECT FOR UPDATE` cannot help when the check is for the *absence* of rows: there is nothing to lock. — DDIA p.305–307 / PDF 329–331 [read]
- **Read-only transaction anomaly under SI** (three transactions, Fekete et al.'s batch example)
  - *Setup:* `control.current_batch = x`. NEW-RECEIPT (T2) reads the batch and inserts a receipt tagged with it. CLOSE-BATCH (T3) increments the batch. REPORT (T1) sums receipts for batch x−1.
  - *Interleaving:* T2 reads batch x; T3 increments to x+1 and commits; T1 reads x+1 and sums batch x without seeing T2's insert, then commits; T2 inserts into batch x and commits → a "closed" batch's report is wrong.
  - Without the read-only T1 the history is serializable as ⟨T2, T3⟩. — [Ports & Grittner, VLDB 2012, Fig. 2](https://arxiv.org/abs/1208.4179) [read]
- **PostgreSQL Read Committed re-evaluation anomaly**
  - When UPDATE or DELETE meets a row changed by a concurrent transaction, PostgreSQL waits, then re-evaluates the WHERE clause on the new version.
  - The docs' example: `website.hits` = 9 and 10. T1 runs `UPDATE ... hits = hits + 1`; a concurrent `DELETE ... WHERE hits = 10` deletes nothing, although a row with hits = 10 exists both before and after.
  - [prior: rdbms_sql.md] ([PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html))

**ANSI levels and their critiques**
- The SQL standard's isolation levels come from System R's 1975 definitions, from before snapshot isolation was invented. The standard is "ambiguous, imprecise", and DDIA concludes nobody really knows what repeatable read means. — DDIA p.298–299 / PDF 322–323 [read]
- Berenson, Bernstein, Gray, Melton, O'Neil and O'Neil, "A Critique of ANSI SQL Isolation Levels" (SIGMOD 1995):
  - They split the ANSI phenomena into strict "anomaly" readings (A1–A3) and broad "phenomenon" readings (P1–P3), and showed that the strict readings admit non-serializable histories.
  - They added P0 dirty write, which ANSI never forbade, P4 lost update (and P4C cursor lost update), and A5A read skew / A5B write skew.
  - They defined snapshot isolation and showed it is incomparable with ANSI REPEATABLE READ: SI forbids phantoms of the A3 kind but allows write skew.
  - Source: [arXiv cs/0701157](https://arxiv.org/abs/cs/0701157) [not re-read]
- Jepsen's PostgreSQL report confirms the practical upshot. Under Berenson's broad interpretation SI and RR are incomparable; under the strict one PostgreSQL's RR (SI) allowing G2-item is defensible. Jepsen recommended that PostgreSQL document its RR as SI. — [Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3) [read]
- Adya, "Weak Consistency: A Generalized Theory and Optimistic Implementations for Distributed Transactions" (MIT PhD, 1999):
  - Defines levels by forbidden cycles in a direct serialization graph with ww, wr and rw (anti-dependency) edges, independent of locking.
  - PL-1 forbids G0. PL-2 forbids G1 (G1a, G1b, G1c). PL-2.99 (repeatable read) also forbids G2-item. PL-3 (serializable) forbids G2. G-single is a cycle with exactly one anti-dependency edge (read skew). Adya also defined PL-SI.
  - Source: [Adya thesis](https://pmg.csail.mit.edu/papers/adya-phd.pdf) [not re-read]
- Hermitage defines each code in one line. G0 write cycles (dirty writes); G1a aborted reads; G1b intermediate reads; G1c circular information flow; OTV observed transaction vanishes; PMP predicate-many-preceders; P4 lost update; G-single single anti-dependency cycles (read skew); G2-item item anti-dependency cycles (write skew on disjoint read); G2 anti-dependency cycles (write skew on predicate read). — [Hermitage](https://github.com/ept/hermitage) [read]

**The naming mess: Hermitage results** — [Hermitage](https://github.com/ept/hermitage) [read]. The README lists no versions or dates. The tests date from 2014, and CockroachDB, YugabyteDB and Memgraph rows were added later.

| Vendor's "so-called" level | Actual level (Hermitage) | Notable gaps |
|---|---|---|
| PostgreSQL "read committed" ★ | monotonic atomic view | allows PMP, P4, G-single, G2 |
| PostgreSQL "repeatable read" | snapshot isolation | allows G2-item, G2 |
| PostgreSQL "serializable" | serializable | none |
| MySQL/InnoDB "repeatable read" ★ | monotonic atomic view | **P4 lost update allowed**; PMP and G-single prevented only for read-only transactions |
| MySQL "serializable" | serializable | none |
| Oracle "read committed" ★ | monotonic atomic view | like PostgreSQL RC |
| Oracle "serializable" | **snapshot isolation** | G2-item allowed; G2 prevented only "some" cases |
| SQL Server "read committed" (locking ★ or RCSI) | monotonic atomic view | |
| SQL Server "repeatable read" | repeatable read | prevents P4, G2-item; G-single only "some"; allows G2 |
| SQL Server "snapshot" | snapshot isolation | G2-item, G2 |
| SQL Server "serializable" | serializable | none |
| CockroachDB "read committed" / "repeatable read" / "serializable" ★ | MAV / SI / serializable | |
| YugabyteDB "read committed" ★ / "repeatable read" / "serializable" | MAV / SI / serializable | |
| Memgraph "snapshot isolation" ★ | SI | |

- DDIA's summary: PostgreSQL calls SI "repeatable read", Oracle calls it "serializable", MySQL's "repeatable read" is MVCC that is weaker than SI, and IBM Db2's "repeatable read" is serializable. — DDIA p.298 / PDF 322 [read]
- DDIA Table 8-1 marks lost updates under SI as "? Depends" because detection varies by vendor. — DDIA p.335 / PDF 359 [read]

**Jepsen/Elle findings, 2020–2026** (the full list is at [jepsen.io/analyses](https://jepsen.io/analyses) [read]. Analyses since 2020: etcd 3.4.3, Dgraph 1.1.1, MongoDB 4.2.6, PostgreSQL 12.3, Redis-Raft, Scylla 4.2-rc3, Radix DLT, Redpanda, MySQL 8.0.34, RavenDB 6.0.2, Datomic 1.0.7075, jetcd, Bufstream 0.1.0, Amazon RDS for PostgreSQL 17.4, TigerBeetle 0.16.11, Capela, NATS 2.12.1, MariaDB Galera 12.1.2, Orkes Conductor 5.3.2, ParticleDB 1.1.4.)
- **Elle** (Kingsbury and Alvaro, VLDB 2020) records list-append histories, infers a dependency graph and searches it for Adya cycles (G0, G1a/b/c, G-single, G2-item…) without hand-written test cases. — [Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3) [read]; paper [arXiv 2003.10554](https://arxiv.org/abs/2003.10554) [not re-read]
- **PostgreSQL 12.3** (2020-06-12):
  - Found 6 G2-item cases in a 2-minute run under SERIALIZABLE on a healthy node. Each involved a read-write conflict on a freshly inserted row.
  - Cause: with three concurrent transactions, SSI conflict detection could attribute the updater's XID to both tuple versions. The code was essentially untouched since SSI shipped in 2011.
  - Confirmed in 9.5.22, 10.13, 11.8, 12.3 and 13. Fixed in the 2020-08-13 minor releases.
  - RR showed about 140 G2-item cycles per minute, which is expected for SI.
  - Source: [Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3) [read]
- **MySQL 8.0.34** (2023-12-19, Alvaro and Kingsbury), on a healthy single node at default **REPEATABLE READ**:
  - 214 G2-item cycles in 40 s; 244 G-single plus 305 G2-item in 60 s; 198 lost updates among 446 transactions.
  - Non-repeatable reads inside one transaction: 126 of 9,048 committed transactions.
  - MAV violations. Example: a transaction read a name as "pebble", updated a *different* column, then read "moss".
  - Cause: InnoDB's snapshot covers plain SELECTs only. The transaction's own UPDATEs and DELETEs act on the latest committed versions and pull them into its view.
  - RU and RC behaved as PL-1 and PL-2. Single-node SERIALIZABLE looked sound.
  - **AWS RDS MySQL "serializable"** showed G2-item and G-single, because `replica_preserve_commit_order` (`slave_preserve_commit_order`) defaults to OFF there.
  - Source: [Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34) [read]
- **Amazon RDS for PostgreSQL 17.4 Multi-AZ clusters** (2025-04-29):
  - Healthy clusters occasionally showed **Long Fork** and other G-nonadjacent cycles, so they do not provide SI. Short Fork (write skew) was not seen, which suggests parallel SI.
  - Present in every version tested, 13.15 to 17.4. Seen in a 2-minute run at about 150 write and 1,600 read transactions per second.
  - Cause (added 2025-05-03): the primary makes transactions visible in the order of an in-memory lock, while replicas follow WAL order, so the two can disagree about transaction order.
  - Mitigations: use only the writer endpoint, or include a write in safety-critical transactions.
  - Source: [Jepsen: RDS PostgreSQL 17.4](https://jepsen.io/analyses/amazon-rds-for-postgresql-17.4) [read]
- **MariaDB Galera Cluster 12.1.2–12.2.2** (2026-03-16):
  - P4 lost update and G-single in **healthy** clusters (MDEV-38977), violating SI and RR.
  - Stale reads of acknowledged commits every few minutes (MDEV-38999).
  - Data loss under crashes (MDEV-38974/38976).
  - Galera's docs claim an isolation level "between Serializable and Repeatable Read". All four issues were unresolved at publication.
  - Source: [Jepsen: MariaDB Galera 12.1.2](https://jepsen.io/analyses/mariadb-galera-cluster-12.1.2) [read]
- **ParticleDB 1.1.4–1.1.18** (2026-10-31, Orkes):
  - The home page advertised "Full ACID" while the text below it said snapshot isolation.
  - 96 issues. On healthy single nodes: write loss, G1a/G1b, lost update; later G-single and read skew even in the `table-2pl` "strong serializable" mode, and stale reads in strict-serializable mode.
  - Jepsen recommends that users stop deploying it. The vendor says 1.1.19-rc.13 fixes the remaining issues; Jepsen did not test that release.
  - Source: [Jepsen: ParticleDB 1.1.4](https://jepsen.io/analyses/particledb-1.1.4) [read]
- **Kafka transactions** (found in the Bufstream analysis, 2024-11-12): aborted reads, lost writes and torn transactions (KAFKA-17754), because `EndTxn` carried no sequence number. — [prior: kafka.md] ([Jepsen: Bufstream 0.1.0](https://jepsen.io/analyses/bufstream-0.1.0))
- Jepsen's standing caveat: it "can demonstrate the presence of bugs" but cannot prove their absence. — [Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34) [read]
- DDIA (p.308 / PDF 332) says there are "no good tools" to detect race conditions and that static analysis is still research. This understates black-box checkers such as Elle and Hermitage-style scripted interleavings. — DDIA [read]; Jepsen analyses above [read]

**Real-world cost of weak isolation**
- Weak-isolation bugs have bankrupted a Bitcoin exchange, triggered a financial audit and corrupted customer data. Saying "use an ACID database" misses the point, because ACID databases default to weak levels. Attackers can deliberately fire concurrent request bursts at an API. — DDIA p.289 / PDF 313 [read]
- ACIDRain (Warszawski and Bailis, SIGMOD 2017) found 22 concurrency vulnerabilities in 12 popular e-commerce applications (for example, overspending gift cards). — [ACIDRain paper](http://www.bailis.org/papers/acidrain-sigmod2017.pdf) [not re-read]

### Inferences
- Teach anomalies as interleavings first (two terminal sessions, step by step), name them second (Berenson codes), and only then show the graph view (Adya edges ww, wr, rw). The graph view explains why write skew is "one rw edge each way" and why SSI looks for two adjacent rw edges (Q4).
- Teach the vendor table as a map from names to levels: "the label tells you the vendor, not the guarantee". The MySQL row (lost updates at the default level) and the Oracle row (no true serializable) are the most surprising for working engineers.
- The 2023–2026 Jepsen results show a pattern for a "replication breaks isolation" lesson: the anomalies sat in replication or ordering layers (RDS Multi-AZ, RDS MySQL commit order, Galera), not in single-node engines. A single node can be serializable while the managed cluster built on it is not even SI.
- Misconceptions:
  1. "Repeatable Read prevents phantoms/all anomalies." It varies by vendor; PostgreSQL's prevents phantoms but not write skew.
  2. "Snapshot isolation always prevents lost updates." Not MySQL RR or Galera.
  3. "My cloud database behaves like the engine it's built on."
  4. "Jepsen passed means correct."
  5. "Read-only transactions can't cause anomalies." See the batch-receipts example.

### Gaps
- Hermitage doesn't give the database versions or dates it tested, so its results may be stale for recent releases (for example SQL Server 2025, Oracle 23ai/26ai). I found no 2025–2026 re-run.
- I found no evidence that MySQL changed InnoDB RR semantics after Jepsen's 2023 report, nor whether 8.4 LTS or 9.7 LTS docs now describe RR more precisely. Check the 8.4/9.7 "Consistent Nonlocking Reads" page.
- I did not read the Datomic, TigerBeetle, NATS, RavenDB or Capela analyses. Only their titles and dates were collected.
- I didn't fetch the Berenson or Adya PDFs. Phenomenon definitions above are from background knowledge and match Hermitage's codes.

---

## 3. Implementations: read committed; snapshot isolation and MVCC (PostgreSQL vs InnoDB vs Oracle); preventing lost updates; write skew and phantoms; materializing conflicts; predicate, index-range, next-key and gap locks

### Takeaway
Read committed needs only row write locks plus "read the last committed version". Snapshot isolation generalizes that to many versions (MVCC). PostgreSQL keeps old versions in the heap and cleans them up with VACUUM. InnoDB and Oracle update in place and rebuild old versions from undo logs. Lost updates have five fixes: atomic UPDATE, SELECT FOR UPDATE, compare-and-set/version column, automatic detection under SI (not in MySQL), and serializable. Write skew and phantoms need either serializable isolation or locks on something that exists. That can be the rows read, a materialized lock table, a constraint (UNIQUE or EXCLUDE), or index-range, next-key or gap locks.

### Cited Findings

**Read committed**
- *Problem:* dirty reads and dirty writes. *Simplest version:* row-level exclusive locks for writes, held to commit, plus a second copy of each locked row (the old committed value) for readers. — DDIA p.292–293 / PDF 316–317 [read]
- *Where it breaks:* read skew (the $900 example), lost updates (counter 42→43), write skew. — DDIA p.291, 293 / PDF 315, 317 [read]
- PostgreSQL RC takes a fresh snapshot per statement and re-evaluates UPDATE/DELETE WHERE clauses on concurrently updated rows (the hits = 9/10 example). — [prior: rdbms_sql.md] ([PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html))
- InnoDB RC: gap locking is disabled for searches and index scans; gap locks are used only for FK and duplicate-key checks. Record locks on non-matching rows are released after the WHERE is evaluated. — [MySQL 8.4: InnoDB Locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html) [read]
- CockroachDB RC is enabled by `sql.txn.read_committed_isolation.enabled`. When it is false, RC is upgraded to SERIALIZABLE. RC needs no client-side retry handling, and 40001 is rare. — [CockroachDB transactions](https://docs.cockroachlabs.com/docs/stable/transactions) [read]

**Snapshot isolation and MVCC: the generic model**
- Each transaction reads from a consistent snapshot as of its start. Writers still take write locks, but reads take none: readers never block writers, and writers never block readers. — DDIA p.294–295 / PDF 318–319 [read]
- PostgreSQL-style visibility (DDIA Fig. 8-7). Each row version carries `inserted_by` and `deleted_by` (PostgreSQL `xmin`/`xmax`); an update is a delete plus an insert. A version is visible if its inserter had committed at snapshot time and its deleter had not. Writes from transactions in progress at snapshot start, from later transactions, and from aborted transactions are ignored. — DDIA p.295–297 / PDF 319–321 [read]
- PostgreSQL transaction IDs are 32-bit and wrap after about 4 billion, which vacuum handles. — DDIA p.295 / PDF 319 [read]
- Every table must be vacuumed at least once per ~2 billion XIDs. `autovacuum_freeze_max_age` defaults to 200 M, warnings start 40 M XIDs before wraparound, and with fewer than 3 M left the cluster refuses writes. — [prior: database_internals.md] ([PostgreSQL routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html))
- Indexes and MVCC: index entries point at one version and queries walk the version chain. PostgreSQL avoids index updates when the new version fits on the same page (HOT). CouchDB, Datomic and LMDB use copy-on-write B-trees, where each root is a snapshot. — DDIA p.298 / PDF 322 [read]
- Some systems make SI their *highest* level: Oracle, TiDB and Aurora DSQL. BigQuery also uses SI. — DDIA p.295 / PDF 319 [read]

**PostgreSQL vs InnoDB vs Oracle MVCC storage**
- *PostgreSQL* (old-to-new versions in the heap):
  - Dead tuples share pages with live ones. Example from the source post: 10 M live + 40 M dead tuples gives a 50 GB table holding 10 GB of data. Non-HOT updates touch every index.
  - VACUUM has four jobs: reclaim space, refresh statistics, maintain the visibility map, and prevent XID/multixact wraparound.
  - [prior: database_internals.md] ([PostgreSQL routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html))
  - Long-open transactions, including **prepared 2PC transactions**, stop VACUUM from reclaiming storage and can in extreme cases force a shutdown to prevent wraparound. — [PostgreSQL 18: PREPARE TRANSACTION](https://www.postgresql.org/docs/18/sql-prepare-transaction.html) [read]
- *InnoDB* (in-place update, new-to-old via undo):
  - Hidden columns: 6-byte DB_TRX_ID, 7-byte DB_ROLL_PTR pointing to an undo record, 6-byte DB_ROW_ID. Insert undo can be dropped at commit; update undo lives until no snapshot needs it, then purge removes it.
  - Secondary index records have no hidden system columns and are not updated in place, so InnoDB goes back to the clustered index to resolve versions.
  - [prior: database_internals.md] ([MySQL 8.4: InnoDB multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html))
- *InnoDB "repeatable read" semantics:* "consistent reads ... read the snapshot established by the first read". That covers only plain SELECTs. DML and locking reads act on the latest committed row, which is why RR loses updates and shows non-repeatable reads after a write. — [Jepsen: MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34) [read]
- *Oracle:* undo-based read consistency, like InnoDB. Its "serializable" is SI, which prevents P4 and G-single but not G2-item. — [Hermitage](https://github.com/ept/hermitage) [read]. Oracle raises ORA-08177 ("can't serialize access for this transaction") on a write-write conflict. [not re-read; Oracle Database Concepts, "Data Concurrency and Consistency"](https://docs.oracle.com/en/database/oracle/oracle-database/23/cncpt/data-concurrency-and-consistency.html)
- *SQL Server:* default RC is lock-based on-premises, with RCSI available. Its SNAPSHOT level is true SI with update-conflict detection. Both versioned modes keep row versions in a version store (tempdb, or the persistent version store with Accelerated Database Recovery). — Hermitage rows [read]; version-store and error-3960 details [not re-read: Microsoft "Transaction locking and row versioning guide"](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide)
- "MVCC means no locks" is wrong. PostgreSQL has multixact IDs "to support row locking by multiple transactions", and SI still uses write locks. — [prior: database_internals.md]; DDIA p.295 / PDF 319 [read]

**Preventing lost updates** (problem: concurrent read-modify-write cycles; DDIA p.299–303 / PDF 323–327 [read])
1. *Atomic write operations:* `UPDATE counters SET value = value + 1 WHERE key='foo'`, MongoDB partial-document operators, Redis data-structure ops. Usually the best fix. ORMs make it easy to write unsafe read-modify-write code instead.
2. *Explicit locking:* `SELECT ... FOR UPDATE` (DDIA Example 8-1, game pieces). It's easy to forget, and it introduces deadlock risk.
3. *Automatic lost-update detection under SI:* PostgreSQL RR, Oracle serializable and SQL Server SNAPSHOT abort the second writer; **MySQL/InnoDB RR does not**. Some authors argue that this means MySQL RR is not SI at all. PostgreSQL's error is `could not serialize access due to concurrent update` — [prior: rdbms_sql.md]
4. *Compare-and-set / optimistic locking:* `UPDATE wiki_pages SET content=... WHERE id=1234 AND content='old'`, or a version column. The caveat: under MVCC the WHERE may be evaluated against a snapshot. Many implementations make concurrent committed writes visible to UPDATE/DELETE WHERE evaluation, but "this may or may not be safe" depending on the DB.
5. *Replicated or multi-leader stores:* locks and CAS assume one up-to-date copy. Use commutative merges (CRDTs) or siblings instead. Last-write-wins loses updates.
- Aurora DSQL turns `SELECT ... FOR UPDATE` into an optimistic check: the selected rows are adjudicated at commit as if written, and whichever transaction commits second fails with OC000. It never blocks. `FOR SHARE` and `NO KEY UPDATE` are unsupported. — [Aurora DSQL concurrency control](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html) [read]
- Spanner's REPEATABLE READ (snapshot isolation) checks only write-write conflicts. Under pessimistic concurrency, rows read with `FOR UPDATE` or the `lock_scanned_ranges=exclusive` hint get exclusive locks. — [Spanner: Use repeatable read isolation](https://docs.cloud.google.com/spanner/docs/use-repeatable-read-isolation) [read]

**Write skew and phantoms**
- Write skew generalizes lost update: two transactions read the same objects and then update *different* ones. Atomic single-object ops don't help, and neither does SI's lost-update detection: PostgreSQL RR, MySQL RR, Oracle serializable and SQL Server SNAPSHOT all allow it. Multi-row constraints usually can't be declared. The second-best fix is `FOR UPDATE` on the rows the decision depends on. — DDIA p.304–305 / PDF 328–329 [read]
- The general pattern: (1) a SELECT checks a precondition, (2) the app decides, (3) a write changes the precondition. If the check looks for the *absence* of rows, there is nothing to lock. That is a phantom. SI avoids phantoms for read-only queries but not in read/write transactions. — DDIA p.307 / PDF 331 [read]
- A search result about Aurora DSQL explained write skew with the on-call doctors example: both commit because they modify different rows, and SI checks only write-write conflicts. The search summary didn't make clear whether this came from AWS or a third-party post. The AWS page I read confirms that only write-write conflicts (plus FOR UPDATE rows) are adjudicated. — [Aurora DSQL concurrency control](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html) [read for OCC/FOR UPDATE; doctor example from search snippet only]

**Materializing conflicts**
- Create a lock table in advance (for example room × 15-minute slot for six months) and `SELECT FOR UPDATE` the relevant slots before checking and inserting. This turns a phantom into a lock conflict on real rows. DDIA calls it a last resort: error-prone, and it leaks concurrency control into the data model. — DDIA p.307–308 / PDF 331–332 [read]
- A declarative alternative in PostgreSQL: exclusion constraints (`EXCLUDE USING gist`, which needs `btree_gist` for scalar equality), and in PostgreSQL 18 temporal keys with `WITHOUT OVERLAPS` on a range column. These make "no overlapping bookings" a constraint, so the second insert fails. — [prior: rdbms_sql.md] ([PostgreSQL 18: Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html), [CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html))

**Predicate locks, index-range / next-key / gap locks**
- A predicate lock covers every object matching a search condition, including objects that don't exist yet. Readers take shared predicate locks; writers check the old and new values against existing predicate locks. With predicate locks, 2PL becomes serializable. — DDIA p.316 / PDF 340 [read]
- Predicate locks are slow to check, so most 2PL engines use index-range (next-key) locking, which locks a superset of the predicate. For example, lock all of room 123's index entries, or a time range in a time index. With no usable index the engine falls back to a table lock. — DDIA p.317 / PDF 341 [read]
- InnoDB specifics — [MySQL 8.4: InnoDB Locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html) [read]:
  - A record lock is a lock on an index record (a hidden clustered index if there is none).
  - A gap lock locks the gap between index records. Gap locks are "purely inhibitive": they only stop inserts. Shared and exclusive gap locks are equivalent and don't conflict with each other. A unique-index equality lookup on a unique row needs no gap lock.
  - A next-key lock is a record lock plus the gap before it, used at default RR for searches and index scans to prevent phantoms. With index values 10, 11, 13, 20 the intervals are (−∞,10], (10,11], (11,13], (13,20], (20,+∞) (supremum).
  - An insert-intention lock is a gap lock taken by INSERT. Example: client A holds `SELECT * FROM child WHERE id > 100 FOR UPDATE` over rows 90 and 102, and client B's `INSERT ... VALUES (101)` waits.
  - Under RC, gap locking is disabled except for FK and duplicate checks.
  - AUTO-INC locks are table-level, tuned by `innodb_autoinc_lock_mode`.
- PostgreSQL SSI's SIREAD "locks" also use the index gap idea. Reads take SIREAD locks on tuples, and B-tree index access takes them on "gaps" at **page** granularity; the 2012 paper planned next-key refinement. Locks can be promoted (tuple → page → relation) to bound memory. — [Ports & Grittner 2012](https://arxiv.org/abs/1208.4179) [read]
- PostgreSQL docs: a sequential scan takes a relation-level predicate lock, so index-friendly plans reduce false-positive aborts. — [prior: rdbms_sql.md] ([PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html))

### Inferences
- A clean teaching ladder for one invariant ("≥1 doctor on call" / "no double booking"):
  1. Naive check-then-write under RC, then SI: the anomaly reproduces.
  2. FOR UPDATE on rows read: fixes doctors, fails for bookings, which is the phantom case.
  3. Materialized slot table: works but is ugly.
  4. Constraint (UNIQUE / EXCLUDE / WITHOUT OVERLAPS): best when expressible.
  5. SERIALIZABLE (SSI on PostgreSQL, 2PL with next-key locks on InnoDB): general but needs retries.

  Each rung is a lab assertion (Q6).
- The PostgreSQL vs InnoDB MVCC contrast is easiest to teach through operational symptoms. PostgreSQL: table bloat and VACUUM falling behind. InnoDB: history list length growing and undo tablespace growth (the InnoDB symptom names are background knowledge). In both, a long-lived snapshot pins old versions. Prepared 2PC transactions are a sneaky long-lived snapshot in PostgreSQL.
- Aurora DSQL's "FOR UPDATE becomes a commit-time write-set check" is the cleanest bridge from pessimistic to optimistic thinking. The same SQL gives different behavior: no blocking, and a later abort instead.
- Misconceptions:
  1. "SELECT FOR UPDATE prevents phantoms." Only if the rows exist, or if the engine takes gap/next-key locks (InnoDB RR does; PostgreSQL does not).
  2. "MVCC means readers and writers never conflict." Writers still conflict with writers, and SI may abort.
  3. "CAS in SQL is always safe." It depends on MVCC WHERE-clause visibility.
  4. "Gap locks are a bug." They are how InnoDB stops phantoms at RR, and they cause surprising lock waits and deadlocks on inserts.

### Gaps
- I didn't fetch MySQL's "Consistent Nonlocking Reads" or "Locks Set by Different SQL Statements" pages. The claim that MySQL SERIALIZABLE turns plain SELECTs into `FOR SHARE` when autocommit is off is background knowledge.
- I didn't verify the SQL Server version-store and error-3960 details, or whether SQL Server 2025 changed defaults (Azure SQL Database enables RCSI by default; background knowledge).
- Oracle 23ai/26ai features such as "lock-free reservations" for hot counters could be a modern atomic-update example, but I did not research them.
- No primary benchmark gives PostgreSQL bloat versus InnoDB purge costs under the same workload.

---

## 4. Serializability: actual serial execution (H-Store/VoltDB, Redis, stored procedures, partitioning), two-phase locking and deadlocks, serializable snapshot isolation (Cahill 2008; Ports and Grittner 2012), deterministic databases (Calvin 2012)

### Takeaway
There are three main ways to get serializability:
- **Serial execution** is simplest and fast when transactions are short, in memory and single-shard. It collapses on cross-shard work (VoltDB reports about 1,000 cross-shard writes/s).
- **2PL** was the only mainstream option for about 30 years. Readers block writers and vice versa, deadlocks are routine, and tail latency is unstable.
- **SSI** keeps SI's non-blocking reads and aborts only on "dangerous structures" (two adjacent rw anti-dependencies). PostgreSQL's implementation cost under 7% versus SI and ran RUBiS at twice the throughput of S2PL.

Deterministic databases (Calvin) agree on transaction order before executing and need no distributed commit protocol: about 500K TPC-C New Order/s on 100 EC2 nodes in 2012. The price is that every transaction must declare its read/write sets up front, with no interactive transactions.

### Cited Findings

**Actual serial execution**
- *Problem:* concurrency control is hard to get right. *Simplest version:* one thread runs one transaction at a time. Two changes made this viable in the 2000s: RAM became cheap enough to hold the active data set, and OLTP transactions turned out to be short. Used in VoltDB/H-Store, Redis and Datomic. — DDIA p.309 / PDF 333 [read]
- *Where it breaks:* interactive client/server transactions spend most of their time on network round trips, so serial systems require **stored procedures**, or single-statement transactions (DDIA Fig. 8-9). Modern stored procedures use general-purpose languages: VoltDB Java/Groovy, Datomic Java/Clojure, Redis Lua, MongoDB JavaScript. VoltDB also replicates by re-executing deterministic procedures on each replica (state machine replication). — DDIA p.310–312 / PDF 334–336 [read]
- *Scaling:* shard the data so each transaction touches one shard, with one thread per core. Cross-shard transactions run in lockstep: VoltDB reports about **1,000 cross-shard writes/s**, orders of magnitude below single-shard, and adding machines doesn't raise it. — DDIA p.312–313 / PDF 336–337 [read]
- DDIA's constraints: transactions must be small and fast, because one slow transaction stalls everything. The active data should fit in memory, write throughput must fit on one core per shard, and cross-shard transactions are hard to scale. — DDIA p.313 / PDF 337 [read]

**Two-phase locking (2PL / SS2PL)**
- Readers take shared locks and writers take exclusive locks, all held to commit or abort: a growing phase, then a shrinking phase. Writers block readers and readers block writers. Used by SERIALIZABLE in MySQL/InnoDB and SQL Server, and by Db2's "repeatable read". "2PL is not 2PC." — DDIA p.313–315 / PDF 337–339 [read]
- *Where it breaks:* reduced concurrency and unstable latency. A full-table read for a backup or analytics must wait for every writer and then blocks all writers until it commits, making the database effectively read-only for that time. Deadlocks are far more frequent than under RC, and aborted work is redone. — DDIA p.315–316 / PDF 339–340 [read]
- Deadlock handling: the database detects the cycle and aborts one transaction, and the application retries. — DDIA p.301, 315 / PDF 325, 339 [read]
- CockroachDB keeps a `TxnWaitQueue` on the range holding the blocker's record, and when transactions block each other it randomly aborts one. — [CockroachDB transaction layer](https://docs.cockroachlabs.com/docs/stable/architecture/transaction-layer) [read]
- PostgreSQL waits `deadlock_timeout` (default 1 s) before running deadlock detection and reports SQLSTATE 40P01. InnoDB detects immediately when `innodb_deadlock_detect=ON` (default), reports error 1213, and otherwise relies on `innodb_lock_wait_timeout` (default 50 s). [not re-read: [PostgreSQL lock management config](https://www.postgresql.org/docs/18/runtime-config-locks.html), [MySQL InnoDB deadlock detection](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-detection.html)]

**Serializable snapshot isolation (SSI)**
- *Idea:* optimistic. Run on SI, track reads and writes, and abort at commit if the transaction may have acted on an "outdated premise". It has to catch two cases: (1) a read that skipped an uncommitted write which later committed (a stale MVCC read), and (2) a write that hits data another transaction has already read. — DDIA p.318–322 / PDF 342–346 [read]
- SSI waits until commit to abort because a read-only reader needn't abort, and the other writer may still abort. — DDIA p.320 / PDF 344 [read]
- Origins: Cahill, Röhm and Fekete, "Serializable Isolation for Snapshot Databases" (SIGMOD 2008), building on Fekete et al. 2005's theory that every SI anomaly contains two consecutive rw anti-dependency edges. — [Cahill et al. 2008](https://dl.acm.org/doi/10.1145/1376616.1376690) [not re-read]; DDIA p.318 / PDF 342 [read]
- The rule as Ports and Grittner state it: SSI checks for a "dangerous structure" of two adjacent rw-antidependency edges and aborts one transaction if any transaction has both an incoming and an outgoing rw edge. It needs no ww or wr tracking. It can give false positives, because not every dangerous structure lies on a cycle. — [Ports & Grittner, "Serializable Snapshot Isolation in PostgreSQL", PVLDB 5(12), 2012](https://arxiv.org/abs/1208.4179) [read]
- PostgreSQL implementation (shipped in **9.1**, 2011; the first SSI in a production release):
  - SIREAD locks never block, and they must persist after commit because conflicts can surface later.
  - Multigranularity tuple/page/relation locks without intention locks.
  - Summarization of committed transactions keeps memory bounded without limiting concurrency, at the cost of more false positives.
  - Integration with 2PC, replication and savepoints.
  - Read-only optimizations: "safe snapshots", and `BEGIN TRANSACTION READ ONLY, DEFERRABLE`, which blocks until a safe snapshot is available and then runs with no SSI overhead or abort risk. A safe snapshot is not guaranteed in bounded time.
  - Wisconsin's court system was a motivating user.
  - Source: [Ports & Grittner 2012](https://arxiv.org/abs/1208.4179) [read]
- **Numbers** — [Ports & Grittner 2012](https://arxiv.org/abs/1208.4179) [read]:
  - Overall: serializable mode costs "less than 7%" relative to SI.
  - DBT-2++ in-memory: about a 5% slowdown from CPU overhead.
  - RUBiS: SI 435 req/s with 0.004% serialization failures; SSI 422 req/s with 0.03%; S2PL 208 req/s with 0.76%.
- PostgreSQL 18 docs: SSI predicate locks never block and can't cause deadlocks; failures carry 40001 `could not serialize access due to read/write dependencies among transactions`. Advice: use READ ONLY, use a connection pool, keep transactions short, avoid idle-in-transaction, drop explicit FOR UPDATE/SHARE, and tune `max_pred_locks_*`. Before 9.1, SERIALIZABLE meant what RR is now. — [prior: rdbms_sql.md, database_internals.md] ([PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html))
- Bug history: Jepsen found a G2-item bug in PostgreSQL's SSI that had existed since 2011. It was fixed in August 2020. — [Jepsen: PostgreSQL 12.3](https://jepsen.io/analyses/postgresql-12.3) [read]
- Other SSI-style or OCC-serializable systems: SQL Server In-Memory OLTP (Hekaton), HyPer, CockroachDB, FoundationDB and BadgerDB. FoundationDB spreads conflict detection across machines. — DDIA p.318, 322 / PDF 342, 346 [read]
- SSI's weakness: long read/write transactions are likely to abort, so read/write transactions must stay short. Long read-only ones are fine. — DDIA p.322 / PDF 346 [read]
- OCC in general performs badly under high contention and near saturation, because retries add load. Commutative operations reduce contention. — DDIA p.318–319 / PDF 342–343 [read]
- Aurora DSQL's guidance against hot keys: use random primary keys and avoid single-key contention. — [Aurora DSQL concurrency control](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html) [read]
- Marc Brooker's view: serializability also has to detect read-write conflicts, which are more common than write-write conflicts because reads outnumber writes. That is why DSQL chose SI. — [Brooker, "DSQL Vignette: Transactions and Durability", 2024-12-05](https://brooker.co.za/blog/2024/12/05/inside-dsql-writes/) [read]

**Deterministic databases (Calvin)**
- Thomson, Diamond, Weng, Ren, Shao and Abadi, "Calvin: Fast Distributed Transactions for Partitioned Database Systems" (SIGMOD 2012):
  - A sequencing layer agrees on a global order of transaction *inputs* (batched, replicated). Each partition then executes deterministically in that order with locks acquired in order. Because all nodes agree in advance on what to run and in what order, Calvin "eschew[s]" distributed commit protocols.
  - Claimed about **500,000 TPC-C (New Order) transactions/s on 100 commodity EC2 nodes**.
  - Sources: [Calvin paper PDF](https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/calvin.pdf) [search result, abstract only]; [Abadi blog, May 2012](https://dbmsmusings.blogspot.com/2012/05/if-all-these-new-dbms-technologies-are.html) [search result]
- DDIA's mentions are brief: VoltDB's deterministic procedures as state machine replication, and "more recent research" on scaling multi-shard transactions (ref [65]). — DDIA p.312–313 / PDF 336–337 [read]

### Inferences
- Present the three techniques as points on a pessimism axis:
  - Serial execution: one global lock, held very briefly.
  - 2PL: fine-grained locks, held to commit.
  - SSI/OCC: no blocking; check at commit.
  - Calvin: removes nondeterminism, so no coordination is needed at commit time.

  Every technique pays somewhere: throughput ceiling, blocking and deadlocks, aborts and retries, or no interactive transactions.
- The Ports and Grittner numbers (under 7%; RUBiS 422 vs 208 req/s) counter "serializable is too slow". They come from 2012 hardware and PostgreSQL 9.1. The course should say so and have learners measure on PostgreSQL 18.
- Redis MULTI/EXEC and Lua scripts make the "serial execution" idea concrete on a laptop. The Redis track can link here.
- Misconceptions:
  1. "Serializable means transactions ran one at a time." It means equivalent to some serial order.
  2. "SSI predicate locks block like 2PL locks."
  3. "Optimistic is always faster." Not under contention.
  4. "Serializable = strict serializable." Serializable allows a serial order that disagrees with real time; Spanner, FoundationDB and CockroachDB-style systems add real-time ordering (Q5).
  5. "2PL = 2PC."

### Gaps
- I didn't read the Calvin paper body (only abstract-level search results). Its constraints, such as the reconnaissance queries needed for dependent transactions (OLLP), are background knowledge and should be checked.
- I didn't fetch Cahill 2008 or Fekete 2005. The theorem attribution follows Ports and Grittner's description.
- I found no current (2024–2026) benchmark of PostgreSQL SSI overhead on modern hardware, and the prior research round found none either.
- VoltDB's current product status (it rebranded as Volt Active Data) was not checked.

---

## 5. Distributed transactions: 2PC, coordinator failure and in-doubt transactions, XA, 3PC; Percolator, Spanner, CockroachDB, FoundationDB, TiDB, YugabyteDB, Aurora DSQL; DynamoDB, MongoDB, Cassandra LWT/Accord; sagas; exactly-once processing

### Takeaway
Atomic commit across nodes needs a protocol. 2PC works through two "points of no return" (a participant votes yes; the coordinator logs its decision). It blocks if the coordinator dies, and in-doubt participants hold their locks for as long as that lasts. XA adds the lowest-common-denominator problems of heterogeneous systems. 3PC is safe only with bounded delays. Modern distributed databases keep 2PC but replicate the coordinator and participants with consensus, and pair it with MVCC timestamps:
- **Percolator:** a timestamp oracle plus a primary lock.
- **Spanner:** TrueTime plus commit wait.
- **CockroachDB:** hybrid logical clocks, uncertainty intervals, parallel commits.
- **FoundationDB:** a sequencer plus OCC resolvers.
- **Aurora DSQL:** OCC adjudicators plus a journal, at snapshot isolation.

NoSQL stores now expose scoped transactions. Sagas give up isolation for long workflows. Exactly-once processing usually comes from idempotence plus a local transaction, not from cross-system 2PC.

### Cited Findings

**Why naive multi-node commit fails**
- If you just send "commit" to every node, some commit and others abort: a constraint violation on one node, a lost request, or a crash before the commit record. Once committed and visible under RC or stronger, a node's commit can't be retracted. — DDIA p.323–324 / PDF 347–348 [read]

**Two-phase commit**
- Participants: a coordinator (transaction manager), often a library inside the app process (Narayana, JOTM, BTM, MSDTC). Flow:
  1. The app gets a global transaction ID and runs local transactions tagged with it.
  2. Prepare: each participant makes the transaction durable, checks constraints and votes yes, giving up its right to abort.
  3. The coordinator writes its decision to its log. That write is the commit point.
  4. The coordinator sends commit/abort and retries "forever".

  DDIA's analogy is a wedding ceremony. — DDIA p.324–327 / PDF 348–351 [read]
- *Where it breaks: coordinator failure.* A participant that voted yes and hears nothing is **in doubt**. Committing or aborting on a timeout could both diverge from the other participants. If the coordinator's log is lost, an administrator must resolve by hand, and losing only the tail of the log can make the coordinator abort transactions it already committed. — DDIA p.327–328 / PDF 351–352 [read]
- *Holding locks while in doubt:* the participant keeps its row locks (and, under 2PL, read locks) until the outcome is known. A 20-minute coordinator restart means 20 minutes of locks; a lost log means locks forever. Rebooting the database doesn't help, because a correct 2PC keeps in-doubt locks across restarts. Orphaned in-doubt transactions occur in practice. XA "heuristic decisions" are an escape hatch that "probably" breaks atomicity. — DDIA p.331–332 / PDF 355–356 [read]
- PostgreSQL's participant side: `PREPARE TRANSACTION 'gid'` stores the transaction state on disk so it can commit even after a crash. The transaction "continues to hold whatever locks it held". It is resolved later from any session with `COMMIT PREPARED` / `ROLLBACK PREPARED` and listed in `pg_prepared_xacts`. The docs warn that long-lived prepared transactions block VACUUM and can in extreme cases force a wraparound-protection shutdown. The feature is "not intended for use in applications". — [PostgreSQL 18: PREPARE TRANSACTION](https://www.postgresql.org/docs/18/sql-prepare-transaction.html) [read]
- `max_prepared_transactions` defaults to 0 (feature disabled), and changing it requires a server restart. — [PostgreSQL 18: Resource Consumption](https://www.postgresql.org/docs/18/runtime-config-resource.html) [not re-read; the PREPARE page confirms the restart requirement and advises 0 if unused]
- *Three-phase commit:* it is non-blocking only if network delay and response times are bounded. Real systems have unbounded delays and process pauses, so 3PC can't guarantee atomicity. In practice the fix is to replace the single coordinator with consensus (DDIA ch. 10). — DDIA p.328 / PDF 352 [read]
- Gray and Lamport's "Paxos Commit" (2006) is the classic consensus-based replacement for the coordinator. [not re-read: [Consensus on Transaction Commit](https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/)]

**Heterogeneous transactions and XA**
- X/Open XA (1991) is a **C API**, not a network protocol. In Java it surfaces as JTA over JDBC and JMS. Supporters include PostgreSQL, MySQL, Db2, SQL Server, Oracle, ActiveMQ, HornetQ, MSMQ and IBM MQ. — DDIA p.330 / PDF 354 [read]
- The coordinator's log lives on the app server's local disk, and participants can't contact the coordinator directly. So the application process is a single point of failure even if the coordinator is replicated. XA can't detect cross-system deadlocks and can't work with SSI. — DDIA p.331–333 / PDF 355–357 [read]
- Many cloud services deliberately don't implement distributed transactions, and much of 2PC's cost is the extra fsyncs and round trips. — DDIA p.329 / PDF 353 [read]
- Kafka's KIP-939, which would let Kafka take part in 2PC, is "Accepted" but its APIs were pulled from the 4.1 and 4.2 branches, so it had not shipped by Nov 2026. — [prior: kafka.md] ([KIP-939](https://cwiki.apache.org/confluence/display/KAFKA/KIP-939%3A+Support+Participation+in+2PC))

**Database-internal distributed transactions**
- Same-software participants can fix XA's problems: replicate the coordinator with automatic failover, let the coordinator and shards talk directly, replicate the shards, and couple commit with distributed concurrency control (deadlock detection, consistent cross-shard reads). Both SI and SSI work across shards. Examples: YugabyteDB, TiDB, FoundationDB, Spanner, VoltDB, Cassandra, MySQL NDB, plus Kafka's internal transactions. — DDIA p.329, 333 / PDF 353, 357 [read]

**Percolator** (Peng and Dabek, OSDI 2010) — [paper](https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Peng.pdf) [read]
- Snapshot isolation on Bigtable, which has only single-row transactions. Each cell has `data`, `lock` and `write` columns.
- A **timestamp oracle** issues strictly increasing timestamps, about **2 million/s from one machine** with batching.
- Client-coordinated 2PC. In *prewrite*, the client locks every written cell and designates one lock as the **primary**; secondaries point to it. At commit it writes the primary's `write` record, which is the commit point, then the secondaries.
- Locks stranded by crashed clients are cleaned up lazily: a reader checks the primary and either rolls forward or rolls back. This can delay commits by "tens of seconds", which is acceptable for batch indexing but not OLTP.
- SI is explicitly subject to write skew.
- Result: same documents/day as the batch MapReduce indexer, with **50% lower average age of documents** in search results.
- TiDB/TiKV's transaction model is Percolator-derived (DDIA cites TiDB in [6]; Percolator lineage is background knowledge, [not re-read]).

**Spanner** (Corbett et al., OSDI 2012)
- External consistency (strict serializability) for read-write transactions using 2PL, 2PC over Paxos groups, and TrueTime. TrueTime returns an interval [earliest, latest]. A commit takes a timestamp at the interval's upper edge, then **commit-waits** until that time is definitely past before releasing locks and making writes visible. — [InfoQ on the Spanner paper](https://www.infoq.com/news/2012/10/google-spanner) [search]; [U. Toronto ECE1724 2026 lecture slides](https://www.eecg.toronto.edu/~ashvin/courses/ece1724/2026w/lectures/5-spanner.pdf) [search]
- Magnitudes conflict across secondary sources. The expected wait is about 2ε, where ε (the uncertainty) is "typically between 1 and 7 ms" in one source and about 10 ms with a long tail in another. — [search results above]. Background knowledge says the 2012 paper reported ε as a sawtooth of roughly 1–7 ms averaging about 4 ms, but I did not re-read it: [Spanner OSDI 2012](https://research.google/pubs/spanner-googles-globally-distributed-database-2/) [not re-read]
- Google's docs: TrueTime uncertainty adds no commit latency as long as it is smaller than the Paxos round-trip. Spanner Omni (self-managed) uses a software TrueTime; managed Spanner uses GPS and atomic clocks. — [Spanner Omni: TrueTime and external consistency](https://docs.cloud.google.com/spanner-omni/true-time-external-consistency) [search snippet]
- **Changed since the 2012 paper:** Spanner now offers **REPEATABLE READ (snapshot isolation)** for read-write transactions, checking only write-write conflicts. It can be set per client or per transaction. **SERIALIZABLE stays the default.** It can't be used with partitioned DML or to modify tables with full-text search indexes. — [Spanner: Use repeatable read isolation](https://docs.cloud.google.com/spanner/docs/use-repeatable-read-isolation) [read]

**CockroachDB** (Taft et al., SIGMOD 2020, [paper](https://dl.acm.org/doi/10.1145/3318464.3386134) [not re-read]; docs [read])
- Isolation: **SERIALIZABLE (default)** and **READ COMMITTED**. The stable docs list no REPEATABLE READ, but Hermitage has a CockroachDB "repeatable read" row classified as SI. Retry error 40001; ambiguous result 40003. — [CockroachDB transactions](https://docs.cockroachlabs.com/docs/stable/transactions) [read]; [Hermitage](https://github.com/ept/hermitage) [read]
- **HLC:** a physical component near wall time plus a logical component. The gateway picks the transaction timestamp, and nodes merge incoming timestamps into their clocks. A node whose clock is off from at least half the other nodes by 80% of the max offset crashes itself. — [CockroachDB transaction layer](https://docs.cockroachlabs.com/docs/stable/architecture/transaction-layer) [read]
- **Uncertainty interval:** [read timestamp, read timestamp + max-offset], with a default max offset of **500 ms** (`--max-offset`). A read that meets a value inside the window can't tell past from future. It refreshes, pushing its timestamp above the value, or restarts (`ReadWithinUncertaintyIntervalError`). — [Cockroach Labs: clock management](https://www.cockroachlabs.com/blog/clock-management-cockroachdb/) [search]; [transaction layer](https://docs.cockroachlabs.com/docs/stable/architecture/transaction-layer) [read]
- **Write intents** are Raft-replicated provisional values that also act as exclusive locks and point to a transaction record (PENDING, STAGING, COMMITTED, ABORTED). The timestamp cache holds read high-water marks, so a write below a cached read gets pushed. Under SERIALIZABLE the push is validated at commit by **read refreshing**; RC skips read refresh. — [transaction layer](https://docs.cockroachlabs.com/docs/stable/architecture/transaction-layer) [read]
- **Parallel commits:** the record is set to STAGING together with the in-flight writes, and the client gets success as soon as they are replicated. A STAGING transaction counts as implicitly committed once all its writes reach consensus. This cuts commit latency "from two rounds of consensus down to one". Intent resolution is asynchronous and still takes two rounds. — [transaction layer](https://docs.cockroachlabs.com/docs/stable/architecture/transaction-layer) [read]
- Docs reference v26.3/v26.4 releases. — [prior: database_internals.md]; [read: link targets on transaction-layer page]

**FoundationDB** (Zhou et al., SIGMOD 2021) — [paper](https://www.foundationdb.org/files/fdb-paper.pdf) [read]
- An "unbundled" design. The transaction system has a Sequencer, Proxies and Resolvers, all stateless. LogServers hold the WAL and StorageServers serve reads. **Strict serializability via OCC + MVCC**, and lock-free.
- Flow: the client gets a read version from a proxy, reads from storage servers, and buffers writes. At commit, the proxy gets a commit version from the Sequencer, which advances versions at **1 million per second**. Range-partitioned **Resolvers** check read-write conflicts against recently committed key ranges, then the logs make the transaction durable.
- **5-second MVCC window:** multiversion data lives in the memory of resolvers and storage servers. Longer transactions are rejected. The team says hitting the limit usually means an inefficient client, such as serial reads. Transaction size limit is 10 MB; keys are limited to 10 KB and values to 100 KB.
- Recovery handles all failures through fast restart rather than quorums. MTTR is usually under 5 s. Deterministic simulation testing is a core feature.
- Production numbers: storage lag behind logs p99.9 average 3.96 ms / max 208.6 ms. In a multi-region configuration, average and 99.9th-percentile latencies are about 22 ms and 281 ms; commit latency is below the 60.6 ms WAN RTT because replication to the remote region is asynchronous.
- Atomic ops such as add and set-versionstamp avoid conflicts on hot keys.

**TiDB** (PingCAP)
- Default transaction mode is **pessimistic**. Supported levels are READ COMMITTED and REPEATABLE READ. RR is **snapshot isolation** (named RR for MySQL compatibility, and unlike both ANSI and MySQL RR). RC takes effect only in pessimistic mode. READ UNCOMMITTED and SERIALIZABLE error unless `tidb_skip_isolation_level_check=1`. — [TiDB dev guide: transaction overview](https://docs.pingcap.com/tidb/dev/dev-guide-transaction-overview) [search]; [isolation-levels doc (GitHub mirror)](https://github.com/niubell/docs/blob/master/transaction-isolation-levels.md) [search]

**YugabyteDB**
- Hermitage classifies RC (default ★) as MAV, RR as SI and Serializable as serializable. — [Hermitage](https://github.com/ept/hermitage) [read]

**Amazon Aurora DSQL** (announced re:Invent Dec 2024; **GA 2025-05-27** in eight Regions)
- GA announcement: [AWS What's New](https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-aurora-dsql-generally-available) [search]
- **Snapshot isolation only** (equivalent to PostgreSQL RR), lock-free OCC with commit-time adjudication, SQLSTATE 40001 with OC000 (data) or OC001 (schema). "Eliminates the risk of deadlocks." `FOR UPDATE` is adjudicated as a write. — [DSQL concurrency control](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html) [read]
- Limits: **3,000 modified rows per transaction** (table and index rows; SQLSTATE 54000, not configurable), **10 MiB** of modified data, **5-minute** maximum transaction time. A 10,000-row figure seen in third-party posts is a preview-era number. — [DSQL quotas](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/CHAP_quotas.html) [search]
- Design:
  - Reads run at τ_start against MVCC storage with no coordination. Storage waits until it has seen every commit ≤ τ_start, because adjudicators promise never to commit below their advancing, clock-locked points.
  - Writes are buffered in the query processor until commit.
  - The adjudicator checks for writes to the same keys between τ_start and τ_commit. A cross-adjudicator protocol handles transactions spanning adjudicators.
  - The **Journal** stores *committed* transactions, and that write is the commit point. Storage applies them asynchronously, with no 2PC or Raft in the storage path.
  - Coordination happens once per transaction at commit. Brooker calls this "the provably minimal amount of coordination" for strong consistency with SI.
  - Source: [Brooker, 2024-12-05](https://brooker.co.za/blog/2024/12/05/inside-dsql-writes/) [read]
- DDIA lists DSQL with Oracle and TiDB as systems whose top level is SI. — DDIA p.295 / PDF 319 [read]

**NoSQL transactions (2026 status)** — all [prior: nosql.md §4], links there
- *DynamoDB:*
  - `TransactWriteItems` takes up to 100 actions over distinct items, ≤ 4 MB, within one account and Region.
  - Serializable against single-item operations, but read-committed against BatchGetItem, Query and Scan.
  - Every item costs two underlying reads or writes (prepare and commit), even when cancelled. Conflicts raise `TransactionCanceledException`.
  - Global tables keep ACID only in the Region where the write was made. Streams don't preserve transaction atomicity. The idempotency token lasts 10 min.
- *MongoDB:*
  - Multi-document snapshot transactions since 4.0 (replica sets) and 4.2 (sharded).
  - Default lifetime under 60 s. The 16 MB total size limit is gone, but each oplog entry is still ≤ 16 MB. Cache pressure aborts with `TransactionTooLargeForCache`.
  - MongoDB 9.0 (GA 2026-09-28) caps concurrent open transactions at 10,000 (`TooManyOpenTransactions`).
  - Jepsen 2020: use `snapshot` + `majority` explicitly.
- *Cassandra:*
  - 5.0 has single-partition LWT (`IF NOT EXISTS`, `IF`) over Paxos, with a "non-negligible performance cost".
  - **Accord (CEP-15)** is in **6.0-alpha** (Docker tag `6.0-alpha2`; no GA as of Nov 2026). It offers strict serializability across partitions and tables, is leaderless, and usually needs one consensus round trip. Syntax: `BEGIN TRANSACTION … LET … IF … COMMIT TRANSACTION`, which "may evolve".
  - It needs the Cluster Metadata Service (`nodetool cms initialize`, not easily reversible), and is enabled per table with `transactional_mode='full'`.
  - LOCAL/TWO/THREE consistency levels are unsupported for Accord.

**Sagas and compensation**
- Garcia-Molina and Salem, "Sagas" (SIGMOD 1987, pp. 249–259; Princeton TR-070-87):
  - Problem: long-lived transactions hold resources and delay short ones.
  - Fix: split them into a sequence of short transactions T1..Tn, each with a compensating transaction Ci. Either all Ti complete, or a prefix completes and its compensations run.
  - Compensation undoes the work *semantically*. It need not restore the prior state, and compensations must be reliable.
  - Source: [Princeton TR 598 / TR-070-87](https://www.cs.princeton.edu/research/techreps/598) [search]
- DDIA's take: humans are too slow to sit inside a database transaction. Almost all OLTP apps commit within one HTTP request, and multi-step flows such as airline booking span several transactions. — DDIA p.310 / PDF 334 [read]

**Exactly-once message processing**
- Heterogeneous 2PC can atomically commit "message ack + DB writes", but only if every side effect speaks the same atomic commit protocol. An email server doesn't. — DDIA p.329–330 / PDF 353–354 [read]
- Simpler, database-only recipe — DDIA p.334–335 / PDF 358–359 [read]:
  1. Keep a table of processed message IDs with a unique constraint.
  2. In one DB transaction, check or insert the ID and apply the effects, then commit.
  3. Acknowledge the broker only after the commit.
  4. Delete the ID later, after the ack.

  Every crash point is safe: before commit (aborted, redelivered); after commit but before ack (redelivered, deduped); after ack (a leftover ID). Kafka Streams uses a similar idea, and internal distributed transactions let the ID table and the data live on different shards.
- Kafka EOS covers Kafka Streams and transactional producers with `read_committed` consumers. It does not extend to external side effects; the outbox pattern fixes dual writes. — [prior: kafka.md]

### Inferences
- A unifying frame across modern systems: "2PC + consensus-replicated participants + an MVCC timestamp source". The timestamp source differs:
  - Percolator: one oracle (≈2 M/s).
  - Spanner: TrueTime with commit wait.
  - CockroachDB: HLC with uncertainty restarts, no special hardware, max offset 500 ms.
  - FoundationDB: a sequencer (1 M versions/s).
  - DSQL: adjudicator commit points locked to physical clocks.

  Concurrency control also differs: Spanner uses 2PL plus SI option; CockroachDB uses SSI-like read refresh; FDB and DSQL use OCC; TiDB uses Percolator-style SI with pessimistic locks.
- **Changes learners should be told about** (vs older courses and DDIA 1st ed.):
  1. Spanner is no longer serializable-only (RR/SI option).
  2. CockroachDB added READ COMMITTED; a REPEATABLE READ level appears in Hermitage but not in the stable docs I read.
  3. Aurora DSQL (GA 2025) is a major SI-only distributed SQL system.
  4. Cassandra is gaining general transactions (Accord), still alpha.
  5. MongoDB 9.0 added a concurrent-transaction cap.
  6. Kafka 2PC (KIP-939) is still unshipped.
- The in-doubt lab should make lock holding visible: a blocked UPDATE and a growing count of dead tuples that VACUUM can't remove. These are the two costs DDIA and the PostgreSQL docs warn about.
- Sagas are the opposite trade from 2PC: no locks held across steps, no blocking, no isolation. Other sagas can see intermediate states, a business-level dirty read. Teach that through the same anomaly vocabulary from Q2.
- Misconceptions:
  1. "3PC fixes 2PC." Not with unbounded delays.
  2. "Distributed SQL = serializable." DSQL and TiDB top out at SI; Spanner and CockroachDB let you choose weaker levels.
  3. "Exactly-once delivery." It is effectively-once processing, through idempotence.
  4. "Compensation = rollback."
  5. "Clock-based systems need atomic clocks." HLC with bounded skew works, at the cost of uncertainty restarts.
  6. "DynamoDB transactions are serializable against everything." Query and Scan are read-committed.

### Gaps
- I didn't read the Spanner or CockroachDB SIGMOD 2020 papers this session. The TrueTime ε numbers conflict across secondary sources, so check the OSDI 2012 paper (§5) before quoting.
- I couldn't confirm the version history of CockroachDB isolation levels: when READ COMMITTED went GA (24.1 is background knowledge), and whether REPEATABLE READ ever reached the docs as GA.
- I didn't verify current versions of TiDB (8.5 LTS / 9.x?), YugabyteDB (2025.x?) or FoundationDB (7.3/7.4?). YugabyteDB's default level is disputed: Hermitage marks RC as default, while background knowledge says YSQL historically mapped RC to snapshot unless a flag was set. Check the YugabyteDB docs.
- Spanner's REPEATABLE READ release date (preview vs GA) wasn't found.
- No 2026 status beyond "alpha" for Cassandra 6.0/Accord. The prior round found no official 6.0 beta or GA date.
- I didn't research saga isolation countermeasures (semantic locks, commutative updates, reread value). They are background knowledge (Chris Richardson's microservices.io / *Microservices Patterns*) and unverified this session.
- I didn't examine how Aurora DSQL handles multi-Region commit latency (the Brooker post defers it).

---

## 6. Hands-on lab ideas (laptop: Kotlin on JVM 21+, Gradle, Testcontainers, Docker Compose, or pure-Kotlin simulation)

### Takeaway
Every anomaly in Q2 and every fix in Q3–Q5 can be made observable with two or three JDBC connections driven in a fixed step order (Hermitage style: deterministic, not timing-based races) against `postgres:18` and `mysql:8.4`/`mysql:9.7`, plus counters for violated invariants, retries and lock-wait time. 2PC and sagas can use two PostgreSQL containers or pure Kotlin. Each lab below names the number the learner measures.

### Cited Findings
- Toolchain pins from the prior round: Testcontainers 2.0.5, JUnit 6.1.3, Kotlin 2.4.21, JDK 25 toolchain (21 for Spark), pgJDBC 42.7.14. PostgreSQL 18 is the lab DB; PostgreSQL 19 RC1 shipped 2026-10-15, with GA planned for 2026-11-19. — [prior: kafka.md / redis.md / rdbms_sql.md]
- MySQL lines: 8.4 LTS (prior research used 8.4 docs) and **9.7.0 LTS, released 2026-04-21**, which begins the 9.7.x LTS line. — [Oracle MySQL blog: MySQL 9.7 LTS](https://blogs.oracle.com/mysql/mysql-9-7-lts-is-here-upgrade-and-modernize-on-a-stronger-community-edition) [search]
- Hermitage is the reference for scripted two-session tests, with expected results per DB. — [Hermitage](https://github.com/ept/hermitage) [read]
- Expected outcomes the labs can assert:
  - PostgreSQL RR raises "could not serialize access due to concurrent update" on lost updates. PostgreSQL SERIALIZABLE aborts write skew with 40001. — [prior: rdbms_sql.md]
  - MySQL RR silently loses updates (P4) and shows G-single/G2-item. — [Jepsen MySQL 8.0.34](https://jepsen.io/analyses/mysql-8.0.34) [read]
  - InnoDB `SELECT ... WHERE id > 100 FOR UPDATE` blocks `INSERT id=101` at RR, but not at RC (gap locks off). — [MySQL 8.4 InnoDB Locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html) [read]
  - A PostgreSQL prepared transaction keeps its locks and blocks VACUUM. — [PostgreSQL PREPARE TRANSACTION](https://www.postgresql.org/docs/18/sql-prepare-transaction.html) [read]
  - SSI vs SI vs S2PL magnitudes to compare against: RUBiS 422 / 435 / 208 req/s. — [Ports & Grittner](https://arxiv.org/abs/1208.4179) [read]

**Lab catalogue** (design proposals; nothing was executed this session)

| # | Lab | Setup | What the learner measures or reproduces |
|---|---|---|---|
| T1 | Atomicity and the ambiguous commit | `postgres:18` + Testcontainers Toxiproxy between client and DB. Transfer $100 between two accounts. Kill the proxy (a) mid-transaction, (b) right after `COMMIT` is sent. | (a) Balance sum unchanged after abort. (b) Naive retry runs the transfer twice. Count duplicates over 1,000 trials. Then add an idempotency key (`UNIQUE(request_id)`) and show duplicates = 0. |
| T2 | Kotlin Hermitage | Two `Connection`s stepped through scripted schedules for G0, G1a, G1b, G1c, OTV, PMP, P4, G-single, G2-item, G2 × {RC, RR, SER} × {PostgreSQL 18, MySQL 8.4/9.7}. | A generated prevented/allowed matrix diffed against Hermitage's table. Learners explain each "—". |
| T3 | Lost update five ways | 8 coroutines × 10,000 increments on one counter: read-modify-write; `value = value + 1`; `FOR UPDATE`; version-column CAS with retry; PostgreSQL RR auto-detect with retry. Run on PostgreSQL and MySQL RR. | Final value vs expected 80,000. Retries, p99 latency and throughput per strategy. MySQL RR read-modify-write loses updates silently; PostgreSQL RR aborts. |
| T4 | Write skew: doctors and rooms | Doctors on-call and meeting-room schemas. N = 1,000 seeded concurrent pairs. | Invariant violations under RC, RR (both DBs) and SERIALIZABLE. The fix ladder: FOR UPDATE (fixes doctors, not rooms) → materialized slot table → `EXCLUDE USING gist` / PostgreSQL 18 `WITHOUT OVERLAPS` → SERIALIZABLE + retry. Count violations, 40001s and MySQL deadlocks (1213) under 2PL serializable. |
| T5 | Gap and next-key locks | `mysql:8.4`. Client A holds `SELECT … WHERE id > 100 FOR UPDATE`; client B inserts 101 and 99. Inspect `performance_schema.data_locks`. Repeat at RC. | Which inserts block, and for how long (bounded by `innodb_lock_wait_timeout`). The lock rows (record / gap / next-key / insert intention). At RC the phantom insert succeeds. |
| T6 | Deadlock detection | Two transactions lock rows A→B and B→A, on PostgreSQL and MySQL. | Time to abort: PostgreSQL ≈ `deadlock_timeout` (default 1 s), InnoDB near-immediate. Error codes 40P01 vs 1213/40001. Retry success rate. |
| T7 | SSI under load | PostgreSQL SERIALIZABLE vs RR with 4–64 workers on T4's workload, with and without an index (relation vs page SIREAD locks). Then the batch-receipts read-only anomaly, plus `READ ONLY DEFERRABLE`. | Throughput, 40001 rate and false-positive rate vs worker count and index presence. The read-only anomaly reproduces at RR and is prevented at SERIALIZABLE. Compare with the paper's <7% overhead. |
| T8 | MVCC internals and the long snapshot | `pageinspect` to show `xmin`/`xmax` after UPDATE. Hold an RR transaction open while updating 1 M rows. MySQL: `SHOW ENGINE INNODB STATUS` history list length. | `n_dead_tup` and table size before and after VACUUM while the snapshot is open vs closed. InnoDB history list length growth. Visible bloat cost of a forgotten transaction. |
| T9 | 2PC coordinator crash | Two `postgres:18` containers with `max_prepared_transactions=10`. A Kotlin coordinator with a file-based decision log runs `PREPARE TRANSACTION` on both, logs COMMIT, sends `COMMIT PREPARED` to DB1, then is killed (`exitProcess`) before DB2. | `pg_prepared_xacts` on DB2. A concurrent `UPDATE` blocked on the in-doubt row (measure wait, inspect `pg_locks`). Dead tuples that VACUUM can't remove. Recovery: restart the coordinator, replay its log, resolve. Then "lose the log" and resolve manually: the heuristic decision and its risk. |
| T10 | Saga with compensation | Pure Kotlin or three schemas in one PostgreSQL (orders, payments, inventory). An orchestrator runs reserve-stock → charge → ship, failing ship in 20% of runs. | Compensations restore invariants (stock and money conserved). A concurrent reader sees reserved-but-later-released stock (a business-level dirty read). Add a semantic lock (`status='PENDING'`) and count anomalies before and after. |
| T11 | Exactly-once consumer | Simulated broker that redelivers 10% of messages, plus DDIA's processed-ID table. | Side-effect duplicates without vs with dedupe across crash injections at each of the four crash points. Expected: 0 with dedupe, and leftover IDs ≤ acks lost. |
| T12 | Pure-Kotlin schedule explorer | An in-memory MVCC store with pluggable SI, SI + first-updater-wins, SSI (rw-edge tracking with the dangerous-structure rule) and 2PL. Enumerate *all* interleavings of 2–3 tiny transactions. | Count interleavings violating the invariant per level, and SSI false positives (aborts in serializable schedules). Ties Adya graphs to code. |
| T13 (optional) | Distributed SQL taste | `cockroachdb/cockroach` single-node or 3-node Compose (v26.x). Run T4 at SERIALIZABLE vs READ COMMITTED. | 40001 retry rate vs RC anomalies. Optionally widen clock skew with libfaketime in one container to provoke `ReadWithinUncertaintyIntervalError`. Feasibility unverified. |

### Inferences
- Use a deterministic step driver (each connection on its own thread, coordinated with `CyclicBarrier` or a channel per step) rather than "start two threads and hope". Concurrency bugs are timing-dependent (DDIA p.289 / PDF 313), and Hermitage's value is that every run reproduces.
- Keep a randomized stress mode (T3, T4, T7) for counting magnitudes, separate from the deterministic mode used to *explain* each anomaly.
- Pair each lab with its Jepsen counterpart for reading: T3 with the MySQL 8.0.34 lost-update counts; T7 with the PostgreSQL 12.3 SSI bug; T9 with DDIA's in-doubt locks (p.331); a replication lesson with RDS Multi-AZ Long Fork.
- Aurora DSQL, Spanner and DynamoDB can't run locally with real semantics (DynamoDB Local doesn't reproduce distributed behavior; background knowledge). Treat them as reading or optional cloud exercises, and emulate DSQL's OCC with T12's engine.

### Gaps
- None of these labs were run. Testcontainers Toxiproxy module coordinates for 2.0.x, `performance_schema.data_locks` column names, `deadlock_timeout`/`innodb_lock_wait_timeout` defaults, and libfaketime inside CockroachDB containers all need checking during build.
- Whether the `mysql:9.7` Docker image runs natively on arm64 wasn't checked (`mysql:8.4` is known multi-arch from prior work, background knowledge).
- I found no ready-made Kotlin/JVM port of Hermitage. Hermitage's README mentions a VeloxDB port only.
