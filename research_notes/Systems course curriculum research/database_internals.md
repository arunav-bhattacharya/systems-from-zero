# Database Internals: research notes for a 10-12 lesson build-it-yourself track (Kotlin/Java)

Research date: 2026-11-07. Every URL cited below was fetched in this session unless marked otherwise. Facts that come from general textbook knowledge and were NOT re-verified this session are labelled "(unverified)" and sit under Inferences or Gaps, never under Cited Findings.

---

## Q1. Teaching order and scope: canonical concepts, and how PostgreSQL, InnoDB, RocksDB and SQLite implement them

### Takeaway
The CMU 15-445 Fall 2026 order (storage, then buffer pool, then indexes, then execution and optimization, then concurrency control, then logging and recovery, then distribution) is the canonical sequence. For a builder's track, move WAL/recovery earlier so it sits next to LSM trees (the memtable needs a WAL), and teach every concept through one or two real systems: PostgreSQL (heap + append-only MVCC + WAL + OS-cache-reliant buffer pool), InnoDB (clustered B+tree + undo-log MVCC + doublewrite), RocksDB (LSM + Bloom filters + leveled compaction) and SQLite (single-file B-tree, rollback journal or WAL).

### Cited Findings

#### Reference syllabus (CMU 15-445/645, Fall 2026)
- Fall 2026 is taught by Jignesh Patel. The topic overview runs: data models, storage models and query languages, storage architectures (heaps, log-structured), indexes and filters (trees, hash tables, vector), transaction processing, recovery, query processing, parallel/distributed. — [CMU 15-445 home](https://15445.courses.cs.cmu.edu/)
- Lecture order, Fall 2026: #03 Database Storage I, #04 Memory Management, #05 Database Storage II, #06 Storage Models & Compression, #07 Hash Tables, #08-#09 Indexes & Filters, #10 Index Concurrency Control, #11 Sorting & Aggregation, #13 Join Algorithms, #14-#15 Query Execution I/II, #16-#17 Query Planning & Optimization I/II, #18 CC Theory, #19 2PL, #20 Timestamp Ordering, #21 MVCC, #22 Database Logging, #23 Database Recovery, #24 Distributed Databases. Videos are on Panopto, not YouTube; #01-#18 were posted when fetched. — [CMU 15-445 Fall 2026 schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html)
- Fall 2026 projects: C++ Primer, Buffer Pool Manager, Database Index, Query Execution, Concurrency Control. Per the home page, "P1-P2 prohibit coding agents; P3-P4 permit them and require a one-page reflection." — [Assignments](https://15445.courses.cs.cmu.edu/fall2026/assignments.html); [CMU 15-445 home](https://15445.courses.cs.cmu.edu/)
- BusTub is CMU's MIT-licensed educational RDBMS for the course and "should not be used in production environments." — [cmu-db/bustub](https://github.com/cmu-db/bustub)

#### 1. Disk/SSD basics: pages, sequential vs random I/O, fsync, write amplification
- Measured on an NVMe SSD (Samsung PM1733, rated 7000 MB/s read): fio with O_DIRECT reached close to 900K random reads/s with 100 threads, which the authors tie to 100 outstanding I/Os at roughly 100 µs NVMe latency. — [Crotty, Leis, Pavlo, CIDR 2022](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- WAL is cheap to sync because it is sequential: "The WAL file is written sequentially, and so the cost of syncing the WAL is much less than the cost of flushing the data pages." — [PostgreSQL WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)
- SQLite lists "more sequential disk I/O" and "far fewer fsync() calls" among WAL mode's advantages. — [SQLite WAL](https://www.sqlite.org/wal.html)
- fsync semantics can fail you ("fsyncgate", 2018). Linux before 4.13 could lose fsync() errors and mark buffers clean after a write-back error, so a retried fsync() could report success for data that was never written. PostgreSQL now PANICs on fsync failure. The fix landed in v12 and was backpatched to 11, 10, 9.6, 9.5 and 9.4. NetBSD, OpenBSD and macOS also invalidate buffers after errors; FreeBSD keeps them dirty. — [PostgreSQL wiki: Fsync Errors](https://wiki.postgresql.org/wiki/Fsync_Errors)
- Write amplification in LSMs: RocksDB's wiki calls leveled compaction's write amplification "often larger than 10". Per-level write amp under leveled is up to the fanout; under tiered it is 1. — [RocksDB Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction); [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- InnoDB writes pages twice (doublewrite buffer, then data file) to survive torn page writes, but "the doublewrite buffer does not require twice the I/O overhead or twice as many I/O operations": data goes to the doublewrite area "in a large sequential chunk, with a single fsync() call". — [MySQL 8.4 doublewrite buffer](https://dev.mysql.com/doc/refman/8.4/en/innodb-doublewrite-buffer.html)

#### 2. File and page layout: slotted pages, tuples, heap files, TOAST
- PostgreSQL tables and indexes are arrays of fixed-size pages, usually 8 kB (a compile-time choice). Page layout: 24-byte PageHeaderData, then an array of 4-byte ItemIdData line pointers (offset, length), free space, items (tuples), and special space (empty for heaps; B-tree pages keep sibling links there). — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- Slotted-page mechanics: line pointers grow forward from the start (pd_lower) and tuples grow backward from the end (pd_upper). "An identifier never moves until freed," so (page, item index) = CTID stays valid when the page is compacted. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- Page header fields: pd_lsn (8 bytes; LSN of the latest WAL record touching this page), pd_checksum, pd_flags, pd_lower, pd_upper, pd_special, pd_pagesize_version, pd_prune_xid. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- Heap tuple header is 23 bytes on most machines: t_xmin (insert XID), t_xmax (delete XID), t_cid/t_xvac (overlaid), t_ctid (6 bytes: TID of this or a newer version), t_infomask2, t_infomask, t_hoff. An optional null bitmap (1 = not null) follows. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- TOAST exists because tuples cannot span pages. It kicks in when a row exceeds TOAST_TUPLE_THRESHOLD (normally 2 kB) and compresses or moves values out of line until the row is under TOAST_TUPLE_TARGET (normally 2 kB; per-table `toast_tuple_target`). Out-of-line values are split into chunks of about 2000 bytes (4 per page) in a TOAST table keyed by (chunk_id, chunk_seq). The on-disk TOAST pointer is always 18 bytes. Maximum logical value size is 1 GB. Strategies: PLAIN, EXTENDED (default), EXTERNAL, MAIN. — [PG TOAST](https://www.postgresql.org/docs/current/storage-toast.html)
- SQLite uses the same slotted design: a b-tree page holds a header, a cell pointer array of 2-byte offsets "arranged in key order", unallocated space, then the cell content area. Free space inside the content area is tracked as freeblocks (4-byte header) and fragments of 1-3 bytes (at most 60 fragment bytes per page). Large payloads spill to linked overflow pages. — [SQLite file format](https://www.sqlite.org/fileformat2.html)
- SQLite page size must be a power of two from 512 to 65536. The file starts with a 100-byte header ("SQLite format 3\000"). Pages are numbered from 1. — [SQLite file format](https://www.sqlite.org/fileformat2.html)

#### 3. Buffer pool: page table, pinning, eviction, OS page cache, O_DIRECT, mmap
- PostgreSQL's buffer manager separates pins (reference counts: "An unpinned buffer is subject to being reclaimed and reused for a different page at any instant") from short-term content locks (shared, share-exclusive, exclusive). Pruning or compacting a page needs an exclusive lock plus being the only pinner ("cleanup lock"). — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
- PostgreSQL eviction is clock-sweep. Each buffer has a usage counter, incremented up to a small cap on each pin. The clock hand (nextVictimBuffer) decrements nonzero counts and skips pinned buffers, and the first unpinned buffer with usage count 0 is the victim. — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
- Scan resistance comes from ring buffers. Sequential scans use a 256 KB ring, VACUUM's ring is sized by `vacuum_buffer_usage_limit`, and bulk writes (COPY, CTAS) use 16 MB (at most 1/8 of shared_buffers). — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
- PostgreSQL deliberately double-caches through the OS. `shared_buffers` defaults to 128 MB and the docs suggest ~25% of RAM, noting that "because PostgreSQL also relies on the operating system cache, it is unlikely that an allocation of more than 40% of RAM to shared_buffers will work better." — [PG resource config (v18)](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- Pavlo writes that PostgreSQL is the only major DBMS still relying on the OS page cache, and that PG 18's AIO "will finally put PostgreSQL on the path to dropping its reliance on the OS page cache." — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- The mmap paper ("Are You Sure You Want to Use MMAP in Your Database Management System?", Crotty, Leis, Pavlo, CIDR 2022) names four problems: (1) transactional safety (the OS can flush dirty pages at any time, and mlock does not stop it); (2) I/O stalls (no async reads, any access can page-fault); (3) error handling (checksums must be re-validated on every access, and I/O errors arrive as SIGBUS); (4) performance: page-table contention, single-threaded eviction (kswapd) and TLB shootdowns. — [CIDR 2022 paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- Results from the same paper: on random reads, mmap matched fio for ~27 s, then dropped to near zero once the page cache filled, then recovered to about half of fio. On sequential scans across 10 SSDs the gap was ~20x. Summary: "mmap is 2-20x worse than fio" once eviction starts. — [CIDR 2022 paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- Case studies in the same paper. MongoDB's MMAPv1 was deprecated in 2015 and removed in 2019. InfluxDB replaced mmap after I/O spikes past a few GB. SingleStore saw mmap calls take 10-20 ms per query, about half of runtime. RocksDB began as a LevelDB fork partly because of LevelDB's mmap read bottlenecks. LMDB uses mmap with shadow paging and a single writer. The paper's advice: use mmap only if the working set fits in memory and is read-only, or "You need to rush a product to the market..." — [CIDR 2022 paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)

#### 4. B+trees
- PostgreSQL B-tree pages keep left/right sibling links in the page's special space. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- pageinspect shows the first item on a non-rightmost B-tree page is the "high key", and that on internal pages `ctid` holds a downlink block number. — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
- SQLite table b-trees "use a 64-bit signed integer key and store all data in the leaves" (B+tree shape). Index b-trees "use arbitrary keys and store no data at all". The page type byte is 2/5/10/13 for interior index, interior table, leaf index and leaf table. WITHOUT ROWID tables are stored as index b-trees keyed on the PK. Overflow thresholds guarantee "a minimum fanout of 4 for index b-trees". — [SQLite file format](https://www.sqlite.org/fileformat2.html)
- Multicolumn rule: "equality constraints on leading columns, plus any inequality constraints on the first column that does not have an equality constraint, will always be used to limit the portion of the index that is scanned." — [PG 18 multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- PG 18 skip scan: "Skip scan works by generating a dynamic equality constraint internally, that matches every possible value in an index column." Example: an index on (x, y) with `WHERE y = 7700` becomes repeated `x = N AND y = 7700` probes. The planner only does this when there are "so few distinct x values" that most leaf pages can be skipped. — [PG 18 multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- Pavlo notes that Oracle has supported skip scans since 9i (2002). — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- InnoDB tables are clustered indexes. Secondary index records "do not contain hidden system columns nor are they updated in-place," and InnoDB goes back to the clustered index to resolve versions. — [MySQL 8.4 multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)

#### 5. Hash indexes and log-structured hash tables (Bitcask)
- Bitcask (Sheehy and Smith, Basho, 2010) is a directory of append-only data files, exactly one of them active for writes. Closed files are immutable. — [Bitcask paper](https://riak.com/assets/bitcask-intro.pdf)
- Entry format: `crc | tstamp | ksz | value_sz | key | value`, with the CRC covering the rest of the entry. Delete appends a tombstone value. — [Bitcask paper](https://riak.com/assets/bitcask-intro.pdf)
- The in-memory "keydir" hash table maps each key to `file_id, value_sz, value_pos, tstamp` for its newest entry, so a read "doesn't ever require more than a single disk seek". — [Bitcask paper](https://riak.com/assets/bitcask-intro.pdf)
- Merge compacts immutable files down to live keys and writes "hint files" (key plus position, no values) for fast startup. Recovery needs no replay because "the data files and the commit log are the same thing." The keydir "must fit entirely in RAM." Early tests: 5000-6000 writes/s on a laptop with slow disks. Bitcask relies on the OS filesystem cache for reads. — [Bitcask paper](https://riak.com/assets/bitcask-intro.pdf)
- CMU gives hash tables their own lecture (#07) in the indexes block. — [CMU schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html)

#### 6. LSM trees: memtable, WAL, SSTables, Bloom filters, compaction, amplification, RUM
- RocksDB compaction styles: Leveled (default, `kCompactionStyleLevel`; really a tiered+leveled hybrid because L0 is tiered), Universal (tiered: lowest write amp, but higher read and space amp) and FIFO (drops the oldest files; cache-like data). — [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- Defaults and invariants: `level0_file_num_compaction_trigger` is 4, `target_file_size_base` is 64 MB, and a key's version in L0 must be newer than its versions in all lower levels. — [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- In leveled compaction, L0 files may overlap. Each level below is one sorted run, range-partitioned across SSTs, with exponentially growing targets. `level_compaction_dynamic_level_bytes` is "Recommended, default since version 8.4" and puts ~90% of data in the last level. — [RocksDB Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction)
- RocksDB Bloom filters: one per SST (full filter, the default), loaded at file open. 9.9 bits/key gives 1% FP, 4.9 gives 10%, 15.5 gives 0.1%. The Ribbon filter (since 6.15.0) saves "about 30%" space for 3-4x the CPU. Whole-key filters serve point lookups only; prefix Bloom can serve Seek with `check_filter`. — [RocksDB Bloom Filter](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter)
- RUM conjecture (Athanassoulis, Kester, Maas, Stoica, Idreos, Ailamaki, Callaghan, EDBT 2016): "designing access methods that set an upper bound for two of the RUM overheads, leads to a hard lower bound for the third overhead which cannot be further reduced." R = read, U = update, M = memory/space. — [RUM paper, EDBT 2016](https://openproceedings.org/2016/conf/edbt/paper-12.pdf)

#### 7. Write-ahead logging and recovery (ARIES)
- WAL rule: "changes to data files ... must be written only after those changes have been logged, that is, after WAL records describing the changes have been flushed to permanent storage." So "we do not need to flush data pages to disk on every transaction commit ... any changes that have not been applied to the data pages can be redone from the WAL records. (This is roll-forward recovery, also known as REDO.)" — [PG WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)
- Every PG page header carries pd_lsn, the LSN just past the last WAL record that changed the page. This is how redo stays idempotent. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- ARIES (Mohan, Haderle, Lindsay, Pirahesh, Schwarz; ACM TODS 17(1), March 1992, pp. 94-162) introduces "the paradigm of *repeating history* to redo all missing updates *before* performing the rollbacks of the loser transactions." It uses "a log sequence number in each page", logs updates made during rollbacks with chaining that bounds logging "even in the face of repeated failures during restart", and supports fuzzy checkpoints. — [ARIES paper (scan)](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)
- SQLite's two models. In rollback-journal mode (the default), original content is copied to a journal, changes go into the db file, and "COMMIT occurs when the rollback journal is deleted." In WAL mode (since 3.7.0, 2010-07-21), changes are appended to a -wal file, a commit is a commit record, and the auto-checkpoint copies pages back at 1000 pages (~4 MB). — [SQLite WAL](https://www.sqlite.org/wal.html)
- InnoDB's doublewrite modes: ON = DETECT_AND_RECOVER, DETECT_ONLY (metadata only) and OFF. Files are `#ib_<page_size>_<n>.dblwr` (the docs' example uses 16 KB pages), with `innodb_doublewrite_files` defaulting to 2. Atomic-write devices (Fusion-io NVMFS) disable it automatically. — [MySQL doublewrite](https://dev.mysql.com/doc/refman/8.4/en/innodb-doublewrite-buffer.html)

#### 8. MVCC: Postgres versions + VACUUM vs InnoDB undo vs append-only
- PostgreSQL stamps every tuple with t_xmin and t_xmax (see section 2). — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- Pavlo's critique: PostgreSQL stores versions append-only and oldest-to-newest (O2N), and copies every column on update. Oracle and MySQL store "a compact delta" newest-to-oldest. — [Pavlo, "The Part of PostgreSQL We Hate the Most"](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)
- Consequences (same post): dead tuples share pages with live ones (example: 10M live + 40M dead tuples gives a 50 GB table holding 10 GB of live data). Indexes store physical locations, so non-HOT updates touch every index; the authors estimate ~46% of updates are HOT. Autovacuum is hard to tune (default `autovacuum_vacuum_scale_factor` is 20%), and long-running transactions block it. — [Pavlo, "The Part of PostgreSQL We Hate the Most"](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)
- InnoDB hidden columns: 6-byte DB_TRX_ID (last inserter/updater; a delete is an update with a deleted bit), 7-byte DB_ROLL_PTR pointing to an undo record in a rollback segment, and 6-byte DB_ROW_ID. Insert undo can be discarded at commit. Update undo serves consistent reads until no snapshot needs it. Physical removal is "purge". Long transactions, even read-only ones, stop undo discard. — [MySQL 8.4 multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)
- VACUUM has four jobs: reclaim space from dead rows, update planner statistics, update the visibility map (enables index-only scans), and "protect against loss of very old data due to transaction ID wraparound or multixact ID wraparound." — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- Wraparound mechanics: XIDs are 32-bit and compared modulo 2^32 ("two billion XIDs that are 'older' and two billion that are 'newer'"), so every table must be vacuumed at least once per two billion transactions. `autovacuum_freeze_max_age` defaults to 200 million. Warnings start 40M XIDs from wraparound. Below 3M left the server refuses new XIDs ("database is not accepting commands that assign new transaction IDs to avoid wraparound data loss"). Plain VACUUM does not return space to the OS except for trailing empty pages; VACUUM FULL rewrites the table under ACCESS EXCLUSIVE. — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- SQLite WAL gives snapshot reads without MVCC tuples. Each reader records an "end mark" in the WAL and sees the database as of that commit, readers and writers don't block each other, and there is one writer at a time. — [SQLite WAL](https://www.sqlite.org/wal.html)

#### 9. Concurrency control: 2PL, deadlocks, OCC, SSI
- PostgreSQL default isolation is Read Committed, and Read Uncommitted behaves like Read Committed. Repeatable Read is Snapshot Isolation and does not allow phantoms. Serializable is "Serializable Snapshot Isolation, which builds on Snapshot Isolation by adding checks for serialization anomalies." — [PG transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- SSI predicate locks (SIReadLock) "do not cause any blocking and therefore can not play any part in causing a deadlock". Failures carry SQLSTATE 40001 and apps "must be prepared to retry". Before 9.1, SERIALIZABLE meant what is now Repeatable Read. — [PG transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- Multixact IDs exist "to support row locking by multiple transactions", which is evidence that MVCC systems still take row locks. — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- CMU covers CC theory, 2PL, timestamp ordering and MVCC as four separate lectures (#18-#21). — [CMU schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html)

#### 10. Query processing: plans, Volcano vs vectorized vs compiled, joins, cost-based optimization
- DuckDB uses a "columnar-vectorized query execution engine" that processes "a large batch of values" per operation, which it contrasts with row-by-row systems such as PostgreSQL, MySQL and SQLite. — [Why DuckDB](https://duckdb.org/why_duckdb)
- Leis et al., "How Good Are Query Optimizers, Really?" (PVLDB 9(3), 2015) introduces the Join Order Benchmark (JOB): IMDB data (21 tables, 3.6 GB CSV) and 113 queries from 33 structures, with 3-16 joins (average 8). Findings: "all estimators routinely produce large errors"; the cost model "has much less influence on query performance than the cardinality estimates"; exhaustive enumeration beats heuristics "despite the sub-optimal cardinality estimates"; and real data is full of correlations that break uniformity and independence assumptions (PostgreSQL's estimator "works unrealistically well for TPC-H"). — [Leis et al. 2015](https://www.vldb.org/pvldb/vol9/p204-leis.pdf)
- PG 18 removes superfluous self-joins in the optimizer. — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- PG 19 (beta and RC) adds the `pg_plan_advice` extension that "lets users stabilize and control planner decisions", along with anti-join optimizations, eager aggregation and broader incremental sort. JIT is now off by default. — [PG 19 Beta 1 news](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)

#### 11. Columnar storage and compression
- CMU has a lecture on storage models and compression (#06). — [CMU schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html)
- New open columnar formats in 2025: FastLanes (CWI), F3 (CMU and Tsinghua; embeds WASM decoders per column next to native Rust ones and hands data over as Arrow buffers), Vortex (SpiralDB, donated to the Linux Foundation), AnyBlox (VLDB 2025 best paper) and Amudai (Microsoft, apparently discontinued). Pavlo found 94% of Parquet files in the wild use only v1 (2013) features. — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)

#### 12. Replication and consensus (Raft)
- Raft: "In Search of an Understandable Consensus Algorithm (Extended Version)", Ongaro and Ousterhout. A shorter version won Best Paper at USENIX ATC 2014. The site hosts the RaftScope visualization and links to "The Secret Lives of Data". — [raft.github.io](https://raft.github.io/)
- etcd-io/raft (Go) implements only the algorithm: "both network and disk IO are left to the user". It is a deterministic state machine driven by a Ready/Advance loop. Features include leader election, log replication, log compaction, membership changes, leadership transfer, and linearizable reads via quorum check or leases. Its README lists CockroachDB, Dgraph, etcd and TiKV as notable users. — [etcd-io/raft](https://github.com/etcd-io/raft)
- CockroachDB runs one Raft group per range. Writes become Raft commands, and "a quorum of replicas agrees on any changes to a range before those changes are committed". Leader leases keep the Raft leader and the leaseholder co-located. Snapshots plus log replay bring new replicas up to date. — [CockroachDB replication layer](https://docs.cockroachlabs.com/docs/stable/architecture/replication-layer)

### Inferences
- **Recommended teaching order for builders** (deviates from CMU in one place): (1) disk + durability + log-structured hash KV, (2) pages/tuples, (3) buffer pool, (4) B+tree, (5) LSM (memtable, SSTable, Bloom, compaction), (6) WAL and recovery, (7) MVCC, (8) concurrency control, (9) execution and joins, (10) optimizer and cardinality, (11) columnar/vectorized, (12) Raft. WAL comes before MVCC/CC (CMU has it after) because the learner has already built a memtable and a buffer pool and can see why both need a log. CMU's later placement suits a theory-first course.
- **Two families to keep contrasting:** in-place update (B+tree + buffer pool + WAL + undo: InnoDB, SQLite rollback journal) vs out-of-place/append (Bitcask, LSM, PostgreSQL heap versions, SQLite WAL). The RUM conjecture is the unifying frame.
- **Standard textbook material the lessons need, not re-verified this session; cross-check against CMU slides or Petrov:**
  - B+tree: all values in leaves, leaves linked for range scans, internal nodes hold separators only. That is why B+ beats B for range scans and gives higher fanout per page. A split moves half the keys to a new node. A leaf split copies the separator up; an internal split pushes it up.
  - Latch crabbing: take the child latch, release the parent latch once the child is "safe" (cannot split or merge). Optimistic variant: read-latch down the tree and retry with write latches if a split is needed.
  - Eviction policies: LRU-K (O'Neil et al., 1993) and 2Q (Johnson and Shasha, 1994) resist sequential flooding.
  - Joins: hash join is O(|R|+|S|) for equi-joins. Sort-merge suits pre-sorted inputs and range joins. Nested loop or index nested loop works for small or indexed inners.
  - Iterator (Volcano/Graefe) model: open/next/close, one tuple per next(). Compiled execution (HyPer-style) fuses operators into tight loops.
  - Concurrency control: strict 2PL holds locks to commit, deadlock detection runs on a waits-for graph, and OCC is read/validate/write.
- **Cost-based optimization lesson** should lean on JOB's message: estimates, not cost formulas, are the weak link. The PG lab is `EXPLAIN (ANALYZE)` comparing estimated vs actual rows on correlated columns.

### Gaps
- Primary sources for LRU-K, 2Q, the Volcano paper (Graefe 1994), the SSI paper (Ports and Grittner, VLDB 2012; the PG docs cite it only as `[ports12]`) and the hash join and latch crabbing descriptions were not fetched this session.
- "Architecture of a Database System" (Hellerstein, Stonebraker, Hamilton) at dsf.berkeley.edu failed with a TLS certificate error. Its content and URL are not verified.
- SSD internals (flash erase blocks, FTL garbage collection, device-level write amplification) were not sourced. If the lesson needs specifics, find a vendor or academic primary source.
- Default InnoDB page size (16 KB) is implied by the doublewrite docs' example, not stated there.
- Whether TiKV uses etcd-io/raft directly or the Rust port raft-rs was not verified (etcd-io/raft's README lists TiKV as a user).

---

## Q2. Current facts as of November 2026 (versions, new features, books, courses)

### Takeaway
PostgreSQL 18 (Sep 2025, now 18.6) is the current stable release, with async I/O (`io_method` = worker | io_uring | sync) and B-tree skip scan. PostgreSQL 19 was at RC1 (2026-10-15) when fetched and may reach GA during course production. SQLite is at 3.54.1, RocksDB at 11.13.2, DuckDB at 2.0.0 (Oct 2026). DDIA 2nd edition shipped March 2026. CMU 15-445 Fall 2026 is taught by Jignesh Patel with lecture videos on Panopto.

### Cited Findings

#### PostgreSQL 18 (current stable)
- PG 18.0 was released 2025-09-25. The current minor is 18.6, and support runs to November 14, 2030. PG 14 reaches end of life on November 12, 2026. — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/); [PG versioning](https://www.postgresql.org/support/versioning/)
- AIO: "Add an asynchronous I/O subsystem ... allows backends to queue multiple read requests, which allows for more efficient sequential scans, bitmap heap scans, vacuums, etc." It adds `io_method`, `io_combine_limit`, `io_max_combine_limit` and the `pg_aios` view. Default `effective_io_concurrency` and `maintenance_io_concurrency` rise to 16. — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/)
- `io_method` values (start-only):
  - `worker`: the default; uses I/O worker processes.
  - `io_uring`: requires building with `--with-liburing` / `-Dliburing`.
  - `sync`.

  Related settings: `io_workers` defaults to 3 (worker mode only), and `io_combine_limit` defaults to 128 kB. `io_max_concurrency` defaults to -1 (auto, capped at 64). `effective_io_concurrency` defaults to 16, with range 1-1000 and 0 disabling async requests. — [PG 18 resource config](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- Skip scan: "Allow skip scans of btree indexes ... when there are no restrictions on the first or early indexed columns (or there are non-equality ones), and there are useful restrictions on later indexed columns." — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/)
- Other PG 18 changes relevant to internals:
  - initdb now enables data checksums by default (`--no-data-checksums` opts out).
  - pg_upgrade preserves optimizer statistics.
  - Virtual generated columns are the new default.
  - `uuidv7()` is added.
  - `WITHOUT OVERLAPS` temporal constraints.
  - Normal vacuums may eagerly freeze all-visible pages (`vacuum_max_eager_freeze_failure_rate`).
  - OAuth authentication.

  — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/)

#### PostgreSQL 19 (release candidate when fetched)
- The PG versioning page announced "PostgreSQL 19 RC 1 Released!" (2026-10-15). PG 19 was not yet in the supported-versions table. — [PG versioning](https://www.postgresql.org/support/versioning/)
- PG 19 Beta 1 was announced 2026-06-04 (date per search-result summary). Features:
  - `io_method=worker` now auto-scales between `io_min_workers` and `io_max_workers`.
  - `EXPLAIN ANALYZE` gains an `IO` option that surfaces AIO statistics.
  - Data checksums can be enabled or disabled online.
  - Autovacuum can use parallel workers (`autovacuum_max_parallel_workers`) and gets a new scoring system.
  - Vacuum gains a strategy that marks pages all-visible "while they're being queried."
  - New `REPACK` command (with `CONCURRENTLY`).
  - `default_toast_compression` now defaults to `lz4`.
  - JIT off by default.
  - `pg_plan_advice` and `pg_stash_advice`.
  - Up to 2x faster inserts with FK checks.
  - SQL/PGQ property graph queries.

  The announcement warns that "minor changes ... are still possible." — [PG 19 Beta 1 news](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)

#### SQLite
- SQLite 3.54.1 (2026-10-16) is the latest, following 3.54.0 (2026-10-09) and 3.53.4 (2026-07-24). The chronology page's "last updated" stamp (2026-03-20) is stale relative to its own entries. — [SQLite chronology](https://www.sqlite.org/chronology.html)
- WAL mode arrived in 3.7.0 (2010-07-21), and rollback journal remains the default. `PRAGMA journal_mode=WAL` persists across connections. WAL requires all processes on the same host (no network filesystems) because the wal-index (-shm) is memory-mapped shared memory. — [SQLite WAL](https://www.sqlite.org/wal.html)

#### RocksDB
- RocksDB 11.13.2 (released Nov 4, 2026; changelog dated 10/28/2026) is the latest.
  - 11.12 (Oct 26) added full-mode external table APIs.
  - 11.8.0 added callback-based `DB::GetAsync()` / `MultiGetAsync()`.
  - 11.1.0 added `open_files_async`.
  - 11.0.0 (Feb 2026) added blob storage for wide-column values and dropped SST `format_version` below 2.

  — [RocksDB releases](https://github.com/facebook/rocksdb/releases)
- Repo location may have changed. Wiki navigation and login links now point to `github.com/meta/rocksdb/wiki/...`, while the `github.com/facebook/rocksdb/...` URLs used here still loaded. — [RocksDB Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction)

#### InnoDB (MySQL 8.4 LTS docs)
- Doublewrite modes, file naming and the sequential-chunk-plus-single-fsync design are as described in Q1. — [MySQL doublewrite](https://dev.mysql.com/doc/refman/8.4/en/innodb-doublewrite-buffer.html)

#### DuckDB and other engines
- DuckDB v2.0.0 "Cyanoptera" was released 2026-10-21. Before it came 1.5.6 (Sep 28) and 1.5.5 (Jul 22). — [DuckDB releases](https://github.com/duckdb/duckdb/releases)
- DuckDB's site describes the engine as "columnar-vectorized", in-process by default and a "single-file database". It mentions DuckLake and the "Quack protocol" for moving beyond purely in-process use. — [Why DuckDB](https://duckdb.org/why_duckdb)
- 2025 industry events per Pavlo:
  - Databricks acquired Neon (~$1B; Aurora-style separation of compute and storage, rebranded Lakebase).
  - Snowflake acquired CrunchyData (~$250M).
  - Microsoft launched HorizonDB.
  - Sharding middlewares Multigres (Supabase), Neki (PlanetScale) and PgDog.
  - Neon reported in July 2025 that agents create 80% of its databases.
  - SurrealDB benchmarks were reported while it was not flushing writes to disk.

  — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- CockroachDB stable docs reference releases up to v26.3. — [CockroachDB replication layer](https://docs.cockroachlabs.com/docs/stable/architecture/replication-layer)

#### Books and courses
- DDIA 2nd edition (Martin Kleppmann and Chris Riccomini, O'Reilly), March 2026, about 670 pages. Kleppmann's page says it builds on the first edition by "integrating new technologies and emerging trends" (cloud services among them) but does not list chapter changes. — [Kleppmann blog](https://martin.kleppmann.com/2026/03/24/designing-data-intensive-applications-2e.html)
- Other sources conflict on the date and length. O'Reilly's listing showed February 2026 and 672 pages, and one retailer listed 650 pages (ISBN 9781098119065). These came from search results only; the O'Reilly page was not fetched. — [O'Reilly listing (search result)](https://www.oreilly.com/library/view/designing-data-intensive/9781098119058/)
- "Database Internals" (Alex Petrov) has two parts. Storage Engines covers B-tree variants, file formats, WAL and page cache, and log-structured storage. Distributed Systems covers failure detection, leader election, consistency, broadcast and consensus. databass.dev mentions no new edition, only a Chinese translation under review. — [databass.dev](https://www.databass.dev/)
- CMU 15-445 Fall 2026: Jignesh Patel teaches it. Lectures #01-#18 are posted on Panopto (not YouTube); the projects are C++ (BusTub). — [CMU schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html); [Assignments](https://15445.courses.cs.cmu.edu/fall2026/assignments.html)
- Pavlo's latest yearly retrospective is "Databases in 2025: A Year in Review" (2026-01-04). The 2026 edition would normally appear around January 2027. — [Pavlo blog index](https://www.cs.cmu.edu/~pavlo/blog/)

### Inferences
- **Pin doc links to versioned URLs.** Once PG 19 goes GA, `postgresql.org/docs/current/...` will start serving v19 pages. Course text that names v18 behaviour should link `/docs/18/`. Re-check `io_method` defaults and worker settings against v19 before publishing.
- **Postgres observation labs** can use the `worker` default. Whether `io_uring` is available in the official Docker image or under Docker Desktop's Linux VM on macOS was not checked, so treat it as optional.
- **CMU 15-445 videos.** The Fall 2026 recordings are on Panopto and may not be public. For free videos, point learners to earlier semesters on the CMU DB YouTube channel (not verified this session).
- **Version numbers move quickly.** RocksDB ships 11.x releases roughly monthly and DuckDB just cut 2.0. The course should say "as of Nov 2026" next to each version number.

### Gaps
- PG 19 GA date was not confirmed. Re-check postgresql.org/about/news before publishing.
- Whether PG 18 `EXPLAIN ANALYZE` includes BUFFERS by default was not verified.
- SQLite's default page size of 4096 bytes (since 3.12.0) was not verified this session; the fileformat page fetched does not state the default.
- InnoDB "doublewrite moved to separate files in 8.0.20": the 8.4 doublewrite page doesn't give the version.
- Petrov's book publication year (2019) and any second edition could not be confirmed: O'Reilly returned 403 and databass.dev gives no date.
- No search was run for notable new papers in 2026 beyond Pavlo's 2025 retrospective. VLDB/SIGMOD 2026 highlights are a gap.
- The current JDK GA version was not verified. The Oracle docs redirect landed on a JDK 26 docs home, which suggests JDK 26 docs are current there; JDK 21 and 25 are LTS (unverified this session).

---

## Q3. Misconceptions, with corrective evidence

### Takeaway
Each misconception on the list can be corrected with a primary source: PostgreSQL's WAL docs, the mmap paper plus fsyncgate, the RUM conjecture and RocksDB's write-amp numbers, PG's row-lock multixacts and buffer content locks, PG's four VACUUM purposes including wraparound, and the JOB paper.

### Cited Findings
- **"Databases write data pages on commit."**
  - False for WAL systems: "we do not need to flush data pages to disk on every transaction commit," because only the WAL must be flushed. — [PG WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)
  - SQLite in WAL mode: "A COMMIT occurs when a special commit record is appended to the WAL. The database file is not written." — [SQLite WAL](https://www.sqlite.org/wal.html)
  - InnoDB flushes pages from the buffer pool later, through the doublewrite buffer. — [MySQL doublewrite](https://dev.mysql.com/doc/refman/8.4/en/innodb-doublewrite-buffer.html)
- **"The OS page cache is enough."**
  - mmap/OS paging breaks transactional safety, because the OS can write dirty pages at any time. It blocks on page faults, turns I/O errors into SIGBUS, and is 2-20x slower than direct I/O once eviction starts. — [CIDR 2022 mmap paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
  - After a failed fsync, Linux before 4.13 could mark pages clean, so a retry "succeeds" while data is lost. — [PG wiki Fsync Errors](https://wiki.postgresql.org/wiki/Fsync_Errors)
  - Nuance worth teaching: PostgreSQL and Bitcask do lean on the OS cache for reads. — [PG resource config](https://www.postgresql.org/docs/current/runtime-config-resource.html); [Bitcask](https://riak.com/assets/bitcask-intro.pdf)
  - Pavlo frames PG 18's AIO as the start of moving off that reliance. — [Pavlo 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- **"B-trees are slow for writes, so always use LSM."**
  - Optimizing two of read, update and memory overhead forces a lower bound on the third. — [RUM conjecture](https://openproceedings.org/2016/conf/edbt/paper-12.pdf)
  - Leveled LSM write amplification is "often larger than 10". Tiered compaction lowers it but raises read and space amplification. — [RocksDB Leveled](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction); [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
  - Whole-key Bloom filters help point lookups, not range scans. — [RocksDB Bloom](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter)
- **"MVCC means no locks."**
  - PostgreSQL uses multixact IDs "to support row locking by multiple transactions". — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
  - Every page access takes a pin plus a shared or exclusive content lock. — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
  - SSI's SIReadLocks don't block, but serialization failures (40001) force retries. — [PG transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
  - SQLite WAL still allows only one writer at a time. — [SQLite WAL](https://www.sqlite.org/wal.html)
- **"VACUUM is only about disk space."**
  - VACUUM also refreshes statistics, maintains the visibility map for index-only scans, and prevents XID and multixact wraparound. Below 3M remaining XIDs the cluster refuses writes. — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
  - Plain VACUUM usually does not return space to the OS at all. — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
  - InnoDB's equivalent, purge, is held back by long transactions too, even read-only ones. — [MySQL multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)
- **"The optimizer always picks the best plan."**
  - Industrial cardinality estimators "routinely produce large errors", and those errors, more than the cost model, drive bad plans. — [Leis et al. 2015](https://www.vldb.org/pvldb/vol9/p204-leis.pdf)
  - PG 19 ships `pg_plan_advice` precisely "to stabilize and control planner decisions". — [PG 19 Beta 1](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)
  - PG docs describe index choices as what "the query planner expects". — [PG 18 multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- **Bonus: "fsync returned 0, so my data is safe."** Not on every OS or kernel version. — [PG wiki Fsync Errors](https://wiki.postgresql.org/wiki/Fsync_Errors)
- **Bonus: "Repeatable Read allows phantoms (per the SQL standard), so Postgres RR does too."** PG's RR is snapshot isolation and does not allow phantoms. It does allow other anomalies, which is why SSI exists. — [PG transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- **Bonus: "Benchmarks prove durability."** SurrealDB posted strong numbers while not flushing writes to disk, and lost data. — [Pavlo 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)

### Inferences
- The most memorable lab-based refutations:
  - (a) In the WAL lab, show that data files can lag behind the log and recovery still works.
  - (b) In the pageinspect lab, show that an UPDATE leaves the old tuple in place with t_xmax set, and that plain VACUUM marks it reusable without shrinking the file.
  - (c) In the LSM lab, count bytes written vs bytes put to compute write amplification.
- A misconception the learner may bring from JVM work: "a write() to FileChannel is durable." It is not until `force()`, and even that depends on the OS and device. Tie this to fsyncgate.

### Gaps
- No primary source fetched for SSD-level write amplification (FTL/GC), so the "SSDs make random writes free" misconception is unsourced.

---

## Q4. Lab ideas in Kotlin/Java (Gradle + JUnit, 15-30 min each) and Postgres observation labs

### Takeaway
Eight build labs map one-to-one to the requested components. Each has a small API, an in-memory or tmp-dir file backend, and deterministic JUnit tests (including crash simulation by file truncation and randomized comparison against `java.util.TreeMap`). Three Postgres-in-Docker observation labs (pageinspect, pg_buffercache, VACUUM/wraparound) use documented functions.

### Cited Findings (facts the labs are built on)
- **Bitcask lab spec source.**
  - Entry format crc/tstamp/ksz/value_sz/key/value. — [Bitcask](https://riak.com/assets/bitcask-intro.pdf)
  - keydir → (file_id, value_sz, value_pos, tstamp). — [Bitcask](https://riak.com/assets/bitcask-intro.pdf)
  - Tombstone deletes, merge, hint files. — [Bitcask](https://riak.com/assets/bitcask-intro.pdf)
  - Startup scans data files (or hint files) to rebuild the keydir. — [Bitcask](https://riak.com/assets/bitcask-intro.pdf)
- **Slotted page lab spec source.**
  - pd_lower/pd_upper, 4-byte line pointers, tuples from the end. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
  - Identifiers stable across compaction. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
  - SQLite freeblocks/fragments and defragmentation. — [SQLite file format](https://www.sqlite.org/fileformat2.html)
- **Buffer pool lab spec source.**
  - Pin counts and clock-sweep with usage counts. — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
  - Ring buffers for scans. — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
- **SSTable/Bloom lab spec source.** 10 bits/key ≈ 1% FP. Per-file filter. — [RocksDB Bloom](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter)
- **Compaction lab spec source.** L0 newer-than-lower-levels invariant, compaction trigger at 4 L0 files. — [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- **WAL lab spec source.**
  - Log-before-data rule, redo. — [PG WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)
  - pd_lsn per page. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
  - Repeating history, per-page LSN. — [ARIES](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)
  - CRC per record. — [Bitcask](https://riak.com/assets/bitcask-intro.pdf)
- **MVCC lab spec source.**
  - xmin/xmax. — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
  - Snapshot "end mark" idea. — [SQLite WAL](https://www.sqlite.org/wal.html)
  - InnoDB undo-chain alternative. — [MySQL multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)
- **pageinspect (superuser only).**
  - `get_raw_page(rel, blkno)`, `page_header(...)`, `heap_page_items(...)` (shows every line pointer "regardless of MVCC visibility"). — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
  - `heap_tuple_infomask_flags(t_infomask, t_infomask2)` decodes flags. — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
  - `bt_metap`, `bt_page_stats`, `bt_page_items`. — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
  - Doc example: `SELECT t_ctid, raw_flags, combined_flags FROM heap_page_items(get_raw_page('pg_class', 0)), LATERAL heap_tuple_infomask_flags(t_infomask, t_infomask2) WHERE t_infomask IS NOT NULL OR t_infomask2 IS NOT NULL;` — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
- **pg_buffercache.**
  - View columns: bufferid, relfilenode, reltablespace, reldatabase, relforknumber, relblocknumber, isdirty, usagecount ("Clock-sweep access count"), pinning_backends. — [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
  - Functions: `pg_buffercache_summary()`, `pg_buffercache_usage_counts()`. — [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
  - Developer-testing functions: `pg_buffercache_evict(buffer_id)`, `pg_buffercache_evict_relation(relid)`, `pg_buffercache_evict_all()` (superuser). — [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
  - Also `pg_buffercache_numa`. — [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
  - The docs include a "top relations by buffers" query that joins on `pg_relation_filenode(c.oid)` and `reldatabase IN (0, current db)`. — [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
- **VACUUM/wraparound observation.**
  - `SELECT datname, age(datfrozenxid) FROM pg_database;` — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
  - autovacuum_freeze_max_age default 200M. — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
  - 40M warning, 3M refusal. — [PG routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- **Skip scan observation.** Index (x, y), query `WHERE y = 7700`, few distinct x values. — [PG 18 multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- **SQLite observation (optional, no Docker).** `PRAGMA journal_mode=WAL;` returns "wal" and creates -wal and -shm files. A checkpoint fires at 1000 pages. — [SQLite WAL](https://www.sqlite.org/wal.html)

### Inferences: the lab catalogue
All labs are proposals. Each assumes a starter repo with interfaces, `@TempDir` JUnit 5 fixtures and a failing test suite; the learner fills in TODOs. Target JDK 21+ (25 fine), Kotlin or Java, Gradle. Keep each lab to 1-3 classes.

**L-A. Log-structured hash KV (Bitcask style).**
- API: `put(k: ByteArray, v: ByteArray)`, `get(k): ByteArray?`, `delete(k)`, `merge()`, `close()`, `open(dir)`.
- Record: `[crc32 int][tstamp long][ksz int][vsz int][key][value]`, tombstone = vsz -1. Use `java.util.zip.CRC32C`.
- Tests:
  - (1) put/get/overwrite returns the latest value.
  - (2) delete returns null after reopen.
  - (3) reopen rebuilds the keydir from files.
  - (4) torn tail: truncate the active file by N bytes (N in 1..recordLen-1); reopen must ignore the partial record and keep all earlier ones.
  - (5) merge: after 1000 overwrites of 10 keys, total file bytes shrink and all 10 latest values survive.
  - (6) the keydir offset points to the exact value bytes. Read via `FileChannel.read(buf, pos)` and count calls (one positional read per get).
- Stretch: rotate the active file at a size threshold, and add hint files.

**L-B. Slotted page.**
- API over a 4096-byte `ByteBuffer`: `insert(record): Int?` (slot id, or null if full), `get(slot): ByteArray?`, `delete(slot)`, `compact()`, `freeSpace()`.
- Header: slotCount, freeStart (lower), freeEnd (upper). Slots are 4 bytes (offset short, length short); length 0 means a dead slot.
- Tests:
  - (1) inserting until full returns null exactly when `freeSpace() < len + 4`.
  - (2) delete then get returns null, and the slot id is not reused unless the slot-reuse policy is enabled.
  - (3) compaction preserves every live record's bytes and slot id while increasing contiguous free space by the sum of deleted lengths.
  - (4) a record larger than the page/4 threshold throws `RecordTooLarge`, which leads into the TOAST discussion.
  - (5) round-trip the page through bytes: serialize, reload, same contents.

**L-C. Buffer pool with CLOCK and pins.**
- API: `fetch(pageId): Frame` (pins), `unpin(pageId, dirty)`, `newPage()`, `flushAll()`. A `DiskManager` interface gets an in-memory fake that counts reads and writes.
- Tests:
  - (1) a hit does not touch the disk (read count unchanged).
  - (2) a pinned page is never evicted; with all frames pinned, `fetch` throws `NoFreeFrame`.
  - (3) a dirty victim is written exactly once before reuse, and a clean victim is not written.
  - (4) CLOCK second chance: with 3 frames, access pattern 1,2,3,1,4 evicts page 2 (deterministic hand position).
  - (5) pin count is per caller: two fetches need two unpins.
  - (6) sequential flooding: compare hit ratios of LRU vs CLOCK vs CLOCK+ring buffer on a hot set interleaved with a big scan. The assertion is that the ring variant keeps the hot-set hit ratio above X.
- Stretch: LRU-K (K=2).

**L-D. B+tree (order 4) insert + range scan.**
- In memory. Order 4 means at most 4 children and 3 keys per node; state the definition explicitly because texts differ. Leaves are linked.
- Tests:
  - (1) insert 1..N in random order (seeded) and every key is findable.
  - (2) invariants checker: all leaves at the same depth, keys sorted within and across nodes, every non-root node has ≥ ceil(4/2)-1 = 1 key and ≤ 3 keys, parent separators bound child ranges.
  - (3) height grows only by root split, and height for N=1000 is within [log4(1000), log2(1000)].
  - (4) `range(lo, hi)` equals `TreeMap.subMap(lo, true, hi, true)` for 200 random ranges.
  - (5) the leaf chain visits all keys in order.
- Stretch: page-backed nodes on L-C, and a fill-factor bulk loader.

**L-E. Memtable → SSTable flush → Bloom filter.**
- Memtable is a `TreeMap` or `ConcurrentSkipListMap` with tombstones. Flush writes sorted `[klen][k][vlen][v]` blocks, a sparse index (every 16th key) and a Bloom filter (k = round(0.69 × bits/key)). Reads go memtable → newest SST → oldest.
- Tests:
  - (1) get after flush.
  - (2) a newer SST shadows an older one.
  - (3) a tombstone hides an older value.
  - (4) the Bloom filter has no false negatives over 10k inserted keys.
  - (5) the FP rate over 100k absent keys is < 2% at 10 bits/key, which ties to RocksDB's 9.9 bits ≈ 1%.
  - (6) a counting file reader shows an absent key reads zero data blocks when the Bloom filter says no.
  - (7) a scan merges memtable and SSTs in order.
- Stretch (compaction): k-way merge of N SSTs into one. The output is sorted and deduplicated (newest wins); tombstones are dropped only when compacting into the bottom level; a `bytesWritten / bytesPut` counter reports write amplification.

**L-F. WAL + crash recovery.**
- Records: `[lsn long][txId int][type BEGIN|PUT|COMMIT|ABORT][key][value][crc]`. The store is a map (or the L-C pages) with a per-page LSN.
- Protocol: append the record and `force()` the log on COMMIT. Data pages may be written lazily and must never be written ahead of their log records (assert `pageLSN ≤ flushedLSN` before any data write).
- Recovery is redo-only for committed transactions (no-steal simplification). The ARIES undo discussion stays conceptual.
- Tests:
  - (1) committed txns survive "crash" (drop in-memory state, reopen).
  - (2) an uncommitted txn is invisible after recovery.
  - (3) crash simulation: for every truncation point inside the last record, recovery yields exactly the state as of the last complete COMMIT.
  - (4) idempotence: running recovery twice equals running it once (pageLSN check).
  - (5) a checkpoint (flush pages + checkpoint record with redo-start LSN) cuts the records replayed (count them).
  - (6) a corrupted CRC mid-log stops replay at that record.

**L-G. Tiny MVCC store with snapshot reads.**
- Each key holds a version chain of `(value, xmin, xmax)`. `begin()` returns a snapshot of (xid, set of active xids). Visibility: xmin committed and not in the snapshot's active set and < snapshot xid, and xmax empty or not visible.
- Tests:
  - (1) a reader's snapshot is stable while a writer commits.
  - (2) read-your-own-writes.
  - (3) aborted versions are never visible.
  - (4) first-committer-wins on a write-write conflict (the second committer fails).
  - (5) a write-skew test that passes under SI (documents the anomaly; leads into SSI).
  - (6) `vacuum(oldestActiveXid)` removes only versions invisible to every live snapshot, and a long-running reader prevents reclamation (assert version count).
- Stretch: an InnoDB-style variant with newest-in-place plus an undo chain, comparing version-chain lengths read.

**L-H. Volcano iterator executor.**
- `interface Operator { open(); next(): Row?; close() }`. Implement Scan(List), Filter(pred), Project(cols), NestedLoopJoin and HashJoin (build left, probe right).
- Tests:
  - (1) Scan→Filter→Project matches a Kotlin collection pipeline.
  - (2) HashJoin result as a multiset equals NestedLoopJoin's on random data with duplicate keys and nulls (null keys never match).
  - (3) laziness: `next()` on the root pulls at most k rows from the child for LIMIT k (count calls).
  - (4) `close()` propagates.
  - (5) the hash join builds only once (count build-side `next()` calls = |R|).
- Stretch: a vectorized variant with `nextBatch(): IntArray[1024]`, timing filter throughput (informal, not asserted).

**Extra labs for the outline below (not in the original list):**
- **L-I. Lock manager with deadlock detection.** S/X locks, a FIFO wait queue and a waits-for graph with cycle detection that aborts the youngest. Tests: S/S compatible, S/X conflict, upgrade, cycle detected within one detector pass, no false positives on chains.
- **L-J. Cardinality estimator.** Equi-depth histogram plus the independence assumption. Tests: single-predicate estimate within ±10% on uniform data; on correlated columns (city→country) the AND estimate is underestimated by > 5x (asserted, which makes the point); a 3-table DP join order picks the lowest-cost plan for given cardinalities.
- **L-K. Column chunk with compression.** Dictionary, RLE and bit-packing, plus min/max zone maps. Tests: round-trip, compression ratio > 10x on a sorted low-cardinality column, and a predicate scan skipping chunks via zone maps (count chunks read).
- **L-L. Raft log replication core.** Pure functions, no network: an `AppendEntries` handler on followers and commit-index advancement on the leader.
  - Tests: (1) prevLogIndex/term mismatch is rejected; (2) a conflicting suffix is truncated and replaced; (3) the leader commits index N only when a majority matchIndex ≥ N and log[N].term == currentTerm (the paper's Figure 8 scenario); (4) a stale-term request is rejected; (5) a deterministic 5-node simulation with a dropped-message schedule ends with all logs agreeing on the committed prefix.
  - Raft details are from the Raft paper (linked from raft.github.io) and were not re-read this session.

**Postgres observation labs** (Docker `postgres:18` image; tag existence not verified this session):
- **O-1 pageinspect, tuple versions.**
  1. `CREATE EXTENSION pageinspect; CREATE TABLE t(id int, v text); INSERT ...3 rows; UPDATE t SET v='x' WHERE id=1; DELETE FROM t WHERE id=2;`
  2. `SELECT lp, lp_flags, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('t',0));` The old version of id=1 has t_xmax set and t_ctid pointing to the new tuple; the deleted row has t_xmax set.
  3. Run `VACUUM t`, re-inspect, and see line pointers become unused or redirected while the file size stays the same.
  4. Compare with `SELECT txid_current();` and `page_header(get_raw_page('t',0))` (pd_lower/pd_upper).
- **O-2 pg_buffercache.**
  1. Run the docs' top-relations query.
  2. Call `pg_buffercache_evict_relation('t'::regclass)`, then run `EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM t` twice and compare "shared read" vs "hit".
  3. Look at `pg_buffercache_usage_counts()` before and after a big seq scan to show the 256 KB ring (the big scan does not flush the hot set).
- **O-3 VACUUM and wraparound.** Watch `n_dead_tup` in `pg_stat_user_tables` and `age(datfrozenxid)`; run `VACUUM (VERBOSE)` and `VACUUM FREEZE` on a test table and re-check. Optionally use pg_visibility to see all-visible bits (extension not verified this session).
- **O-4 (optional) skip scan.** Build an index on (x, y) with 5 distinct x values over 1M rows; `EXPLAIN ANALYZE ... WHERE y = 7700` on PG 18 vs PG 17 shows the scan type and buffers.
- **O-5 (optional) planner misestimate.** Correlated columns; compare EXPLAIN ANALYZE estimated vs actual rows before and after `CREATE STATISTICS (dependencies)` (extended statistics syntax not re-verified this session).

### Gaps
- `heap_page_items` output column names (lp, lp_flags, t_xmin, t_xmax, t_ctid, ...) are standard but were not listed on the fetched doc page; cross-check in a running instance.
- The `ExtendedOpenOption.DIRECT` (O_DIRECT from Java) docs could not be fetched (the Oracle link redirected to the docs home). If a lesson shows direct I/O from the JVM, verify its `@since`, alignment rules and `ByteBuffer.alignedSlice` usage. `FileChannel.force(boolean)` as the fsync equivalent was also not re-verified.
- Whether `pageinspect`, `pg_buffercache` and `pg_visibility` ship in the official Docker image's contrib was not verified (they normally do).

---

## Q5. Proposed lesson outline (12 lessons) with lab mapping and what tests verify

### Takeaway
Twelve lessons, each 1 concept block + 1 build lab (15-30 min) + optional Postgres/SQLite observation. The order follows the data's path: bytes on disk → pages → memory → indexes → logs → versions → transactions → queries → analytics → replicas.

### Cited Findings
- The sequence mirrors CMU 15-445's lecture order, with logging and recovery pulled earlier. — [CMU schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html)
- Per-lesson real-system anchors are cited in Q1. Key anchors:
  - [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
  - [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
  - [SQLite file format](https://www.sqlite.org/fileformat2.html)
  - [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
  - [PG WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)
  - [MySQL multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)
  - [PG transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
  - [Leis et al.](https://www.vldb.org/pvldb/vol9/p204-leis.pdf)
  - [Why DuckDB](https://duckdb.org/why_duckdb)
  - [Raft](https://raft.github.io/)

### Inferences (the outline)

| # | Lesson | Core concepts | Real-system anchors | Lab | Tests verify |
|---|---|---|---|---|---|
| 1 | Bytes, pages and durability | Pages; sequential vs random I/O; fsync and fsyncgate; write amplification; append-only logs; hash index in RAM | Bitcask, SQLite WAL, PG WAL | L-A Bitcask KV | latest-value reads, tombstones survive reopen, torn-tail truncation tolerated via CRC, merge shrinks files, one positional read per get |
| 2 | Pages, tuples and heap files | Slotted page; line pointers; tuple header (xmin/xmax preview); heap files and free space; TOAST | PG page layout + TOAST; SQLite cell pointers/freeblocks | L-B slotted page; O-1 part 1 (page_header, heap_page_items) | full-page detection, stable slot ids across compaction, byte-exact round trip, oversize rejection |
| 3 | Buffer pool | Page table; pin/unpin; dirty flag; CLOCK vs LRU vs LRU-K/2Q; sequential flooding and ring buffers; OS page cache, double caching, O_DIRECT; mmap paper; PG 18 AIO | PG clock-sweep + rings; shared_buffers guidance; CIDR'22 | L-C buffer pool; O-2 pg_buffercache | no eviction of pinned pages, write-back exactly once, deterministic CLOCK victim, scan-resistant hit ratio |
| 4 | B+trees | Search, insert, split (copy-up vs push-up); fill factor; why B+ not B; latch crabbing (concept); clustered (InnoDB) vs heap + secondary (PG); skip scan | PG nbtree (high key, sibling links); SQLite table/index b-trees; InnoDB clustered index; PG 18 skip scan | L-D B+tree order 4; O-4 skip scan, `bt_page_items` | structural invariants, equivalence with TreeMap, range scan via leaf chain |
| 5 | LSM trees | Memtable; WAL (preview); SSTables; sparse index; Bloom filters (FP math); compaction leveled vs tiered vs FIFO; read/write/space amplification; RUM conjecture | RocksDB leveled defaults, Bloom bits/key table, Ribbon | L-E memtable + SSTable + Bloom (+ compaction stretch) | shadowing and tombstones, no false negatives, FP < 2% at 10 bits/key, Bloom skips I/O, WA counter |
| 6 | Write-ahead logging and recovery | WAL rule; LSNs; pageLSN; force/no-force and steal/no-steal; checkpoints; ARIES analysis/redo/undo and CLRs (concept); torn pages (InnoDB doublewrite; PG full-page writes, unverified); SQLite rollback journal vs WAL | PG WAL intro; ARIES; InnoDB doublewrite; SQLite WAL | L-F WAL + crash recovery | committed durable, uncommitted invisible, every truncation point recovers, idempotent replay, checkpoint shortens replay |
| 7 | MVCC | Versions, snapshots, visibility rules; PG append-only O2N vs InnoDB undo N2O deltas; VACUUM/purge; HOT; XID wraparound and freezing | PG tuple header, routine vacuuming, Pavlo critique; InnoDB DB_TRX_ID/DB_ROLL_PTR | L-G MVCC store; O-1 part 2 and O-3 VACUUM/wraparound | snapshot stability, first-committer-wins, write skew present under SI, GC blocked by a long reader |
| 8 | Concurrency control | Serializability; 2PL and strict 2PL; deadlock detection vs prevention; OCC; timestamp ordering (brief); SI anomalies; SSI | PG isolation levels and SSI (40001, SIReadLock); multixacts | L-I lock manager + waits-for deadlock detection; demo: two psql sessions hitting 40001 | lock compatibility, upgrades, cycle detection and victim choice |
| 9 | Query execution | Parse → logical plan → physical plan; iterator (Volcano) vs vectorized vs compiled; joins (NLJ, INLJ, hash, sort-merge); external sort and hash aggregation (brief) | DuckDB vectorized; PG row-at-a-time | L-H Volcano executor | operator equivalence, hash join = NLJ (multiset), laziness under LIMIT, build-once |
| 10 | Query optimization | Cost model; cardinality estimation (histograms, independence, uniformity); join ordering by DP; why estimates go wrong (JOB); plan stability (PG 19 pg_plan_advice) | Leis et al. 2015; PG EXPLAIN | L-J estimator + 3-way DP join order; O-5 misestimate | single-column accuracy, correlated underestimate shown, DP picks the min-cost order |
| 11 | Columnar storage and analytics | Row (NSM) vs column (DSM) vs PAX; dictionary/RLE/bit-packing; zone maps; vectorized scans; Parquet and newer formats | DuckDB; Pavlo 2025 on new file formats | L-K column chunk + zone maps | round trip, compression ratio, chunk skipping |
| 12 | Replication and consensus | Leader-follower replication; Raft terms, elections, log matching, commit rule; per-range Raft (CockroachDB), etcd/raft library; leases (concept) | Raft paper/site; etcd-io/raft; CockroachDB replication layer | L-L Raft AppendEntries + commit rule | log-matching repair, majority + current-term commit rule, deterministic simulation convergence |

- **Sizing.** Labs D (B+tree), F (WAL) and L (Raft) are the hardest to fit in 30 minutes. Ship them with the node/record classes, serializers and invariant checkers pre-written so the learner writes only split/replay/commit logic.
- **Optional 13th lesson or appendix.** Hash tables in depth (extendible and linear hashing, PG hash indexes) if the track needs 13. Otherwise fold it into lesson 1 (keydir) and lesson 9 (hash join build table).

### Gaps
- None of these lab timings were tested by building the labs. The 15-30 minute estimates are judgement calls and should be validated with a dry run.

---

## Verified URLs

### Takeaway
All of the following were fetched in this session and returned content (PDFs were downloaded and read). Failures are listed separately.

### Cited Findings
- [PostgreSQL 18 release notes](https://www.postgresql.org/docs/release/18.0/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [PostgreSQL 19 Beta 1 announcement](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)
- [PG docs: resource consumption (io_method, shared_buffers)](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- [PG docs: database page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- [PG docs: TOAST](https://www.postgresql.org/docs/current/storage-toast.html)
- [PG docs: routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [PG docs: WAL introduction](https://www.postgresql.org/docs/current/wal-intro.html)
- [PG docs: transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PG docs: pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
- [PG docs: pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
- [PG 18 docs: multicolumn indexes / skip scan](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- [PG source: buffer manager README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
- [PG wiki: Fsync Errors](https://wiki.postgresql.org/wiki/Fsync_Errors)
- [MySQL 8.4: InnoDB doublewrite buffer](https://dev.mysql.com/doc/refman/8.4/en/innodb-doublewrite-buffer.html)
- [MySQL 8.4: InnoDB multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)
- [SQLite release chronology](https://www.sqlite.org/chronology.html)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [SQLite database file format](https://www.sqlite.org/fileformat2.html)
- [RocksDB releases](https://github.com/facebook/rocksdb/releases)
- [RocksDB wiki: Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- [RocksDB wiki: Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction)
- [RocksDB wiki: Bloom Filter](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter)
- [DuckDB releases](https://github.com/duckdb/duckdb/releases)
- [Why DuckDB](https://duckdb.org/why_duckdb)
- [CMU 15-445/645 home (Fall 2026)](https://15445.courses.cs.cmu.edu/)
- [CMU 15-445 Fall 2026 schedule](https://15445.courses.cs.cmu.edu/fall2026/schedule.html)
- [CMU 15-445 Fall 2026 assignments](https://15445.courses.cs.cmu.edu/fall2026/assignments.html)
- [BusTub](https://github.com/cmu-db/bustub)
- [Pavlo blog index](https://www.cs.cmu.edu/~pavlo/blog/)
- [Pavlo: Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- [Pavlo: The Part of PostgreSQL We Hate the Most](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)
- [Crotty, Leis, Pavlo: mmap paper (CIDR 2022, PDF)](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- [Leis et al.: How Good Are Query Optimizers, Really? (PVLDB 2015, PDF)](https://www.vldb.org/pvldb/vol9/p204-leis.pdf)
- [Athanassoulis et al.: RUM Conjecture (EDBT 2016, PDF)](https://openproceedings.org/2016/conf/edbt/paper-12.pdf)
- [Mohan et al.: ARIES (TODS 1992, scanned PDF)](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)
- [Sheehy and Smith: Bitcask (2010, PDF)](https://riak.com/assets/bitcask-intro.pdf)
- [Raft site](https://raft.github.io/)
- [etcd-io/raft](https://github.com/etcd-io/raft)
- [CockroachDB replication layer](https://docs.cockroachlabs.com/docs/stable/architecture/replication-layer) (www.cockroachlabs.com/docs/... 301-redirects here)
- [Kleppmann: DDIA 2nd edition post](https://martin.kleppmann.com/2026/03/24/designing-data-intensive-applications-2e.html)
- [Alex Petrov: Database Internals site](https://www.databass.dev/)

### Inferences
- Use `/docs/18/` instead of `/docs/current/` in the published course wherever the text describes v18 behaviour.
- RocksDB wiki links may migrate to `github.com/meta/rocksdb/wiki/...`. Re-check before publishing.

### Gaps
Failed or unverified URLs:
- `https://www.oreilly.com/library/view/database-internals/9781492040330/` returned HTTP 403.
- `https://stratos.seas.harvard.edu/files/stratos/files/rum.pdf` returned HTTP 403. Use the OpenProceedings URL above instead.
- `https://dsf.berkeley.edu/papers/fntdb07-architecture.pdf` (Hellerstein et al., Architecture of a Database System) failed with a TLS certificate error. Not verified.
- `https://docs.oracle.com/en/java/javase/{21,25}/docs/api/jdk.unsupported/com/sun/nio/file/ExtendedOpenOption.html` redirected to the JDK 26 docs home. The class page itself was not verified.
- The O'Reilly DDIA 2e listing (`oreilly.com/library/view/designing-data-intensive/9781098119058/`) was seen only as a search result, not fetched.
- The Raft paper PDF is linked from raft.github.io but was not fetched separately.

---

## Teaching notes (misconceptions, analogies, what to cut)

### Takeaway
Teach one rule per lesson that the learner can break in their own code and then watch fail: log before data, never evict a pinned page, Bloom filters have no false negatives, a reader's snapshot must not change. Ground each rule in a Postgres or SQLite observation, and cut the theory that does not change what they build.

### Cited Findings
- Pavlo uses a "git diff" analogy for delta-based version storage (Oracle and MySQL) vs PostgreSQL's full-tuple copies. It works well for a JVM/Git-fluent audience. — [Pavlo, "The Part of PostgreSQL We Hate the Most"](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)
- The mmap paper's conclusion is a ready-made checklist slide ("When you should not use mmap ..."). — [CIDR 2022 paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- RaftScope and "The Secret Lives of Data" are the recommended visualizations for Raft. — [raft.github.io](https://raft.github.io/)
- CMU 15-445 Fall 2026 bans coding agents for P1-P2 and permits them for P3-P4 with a reflection. Worth echoing for the first labs, so learners write buffer pool and index code by hand. — [CMU 15-445 home](https://15445.courses.cs.cmu.edu/)
- `heap_page_items` shows tuples "regardless of MVCC visibility", which is what makes dead tuples visible to learners. — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html)
- pg_buffercache views take no buffer manager locks, so results are not a consistent snapshot. Tell learners not to expect exact repeatability. — [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)

### Inferences

**Misconceptions to address explicitly, with the lab that breaks each:**
- "Commit writes pages" → L-F: assert that data files lag the log after commit.
- "OS cache is enough" → L-C plus the mmap paper: control over eviction, pinning and write ordering is what the OS cannot give.
- "LSM always beats B-tree for writes" → L-E stretch: measured WA counter; and range scans can't use whole-key Bloom filters.
- "MVCC = no locks" → L-G (write-write conflict still aborts) plus L-I.
- "VACUUM = disk space" → O-3, with the `age(datfrozenxid)` query.
- "Optimizer is always right" → L-J and O-5.

**Analogies that work for this audience** (judgement calls, not sourced):
- WAL ≈ an append-only event log feeding a materialized view (Kafka-minded backend engineers get this at once). Checkpoint ≈ snapshot plus offset commit.
- Buffer pool ≈ a bounded cache like Caffeine/Guava where entries can be "pinned" (non-evictable while referenced). CLOCK ≈ the second-chance approximation of LRU that avoids a linked-list update on every hit.
- Slotted page ≈ an indirection table, like object handles vs raw pointers in a GC. Slot ids are stable handles; tuples can move during compaction.
- LSM ≈ write to a sorted in-memory TreeMap, then periodically dump immutable sorted files and merge them like merge sort. Bloom filter ≈ a "definitely not here" fast path.
- MVCC ≈ persistent/immutable collections with structural sharing. A snapshot is a pointer to a version. Vacuum/purge ≈ GC of versions that no live snapshot can reach, so a long-running read is like a leaked root.
- Volcano ≈ `Iterator<Row>`/Kotlin `Sequence` pull pipelines. Vectorized ≈ processing `IntArray` batches (like Java Vector API or primitive streams). Compiled ≈ JIT-fused loops.
- Raft ≈ a replicated append-only log with a single writer elected by term. Commit = majority acked.

**What to cut or keep conceptual:**
- ARIES beyond analysis/redo/undo + LSN + CLR intuition. Cut nested top actions, logical undo and media recovery. Labs use no-steal/redo-only.
- Latch crabbing implementation (concept and diagram only). CMU spends a full lecture on it (#10); a 30-minute lab cannot.
- Hash index variants (extendible/linear hashing). Mention only, unless adding the optional lesson.
- Timestamp-ordering CC. One slide.
- Full SQL parsing. Give learners a pre-built logical plan or AST; spend the time on operators.
- Distributed transactions/2PC, Paxos, Byzantine anything. Out of scope; Raft log replication only, with elections at concept level.
- io_uring internals. Show `io_method` settings and `pg_aios`, not kernel ring mechanics.
- New file formats (Vortex, F3, FastLanes). One paragraph in lesson 11.

**Gotchas for lesson writers:**
- "Order 4" B+tree is ambiguous across textbooks (max children vs min degree). Define it in the lab README.
- Bloom FP math: k ≈ 0.69 × bits/key. Lab tests should allow slack (e.g., < 2% for a 1% target) to avoid flaky tests; seed all RNGs.
- Crash-simulation tests: truncate at every byte offset of the last record (cheap for small logs) rather than random offsets, so failures are deterministic.
- Docker on macOS: Postgres runs in a Linux VM. Fine for pageinspect/pg_buffercache, but don't promise io_uring.

**Flags for the November 2026 snapshot** (things likely to change soon):
- PG 19 GA (RC1 was 2026-10-15).
- The default `io_method` and the I/O worker settings in v19.
- RocksDB's monthly 11.x releases and its possible repo move to the `meta` org.
- DuckDB 2.0 just released.
- SQLite 3.54.x.
- DDIA 2e's chapter list (not verified).
- Pavlo's 2026 retrospective (expected around January 2027).

### Gaps
- None of the analogies were tested on learners.
- No source was fetched for PostgreSQL full_page_writes (PG's torn-page defence). Add the PG docs page `wal-reliability` or `runtime-config-wal` if lesson 6 compares it with InnoDB doublewrite.
