# Storage engines, indexing and query execution: concept notes for a first-principles course (as of 2026-11-07)

Scope: how a database stores and finds data, from an append-only file to B-trees, LSM trees, column stores, specialized indexes and vectorized execution, with numbers and current product implementations. Written for a course writer whose readers start with zero database knowledge.

Source conventions:
- "DDIA 2e" means Kleppmann and Riccomini, *Designing Data-Intensive Applications*, 2nd edition (O'Reilly, March 2026). Page numbers are given as printed page / 1-based PDF page. In chapter 4, printed page = PDF page minus 24. All DDIA material is paraphrased from the local PDF (extracted this session). Link used: [DDIA 2e](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/).
- Facts marked "(prior round)" were fetched and verified in the earlier product-organized research round (notes in `research_notes/Systems course curriculum research/`, mainly `database_internals.md`, `nosql.md`, `big_data.md`, `operating_systems.md`). They are cited to their original URLs and were not re-fetched.
- Facts marked "(search summary)" come from a search-engine summary of the linked page, not a full fetch. Treat their exact wording and numbers as needing a re-check.
- Paper PDFs for Harizopoulos et al., MonetDB/X100, HyPer and MyRocks were downloaded and their text extracted locally; numbers from them are first-hand.

---

## Q1. From an append-only log to LSM trees and B-trees: Bitcask, SSTables, compaction, Bloom filters, amplification, B-trees, copy-on-write B-trees, and B-tree vs LSM evidence

### Takeaway
Every OLTP storage engine is a choice about where to pay: append-only designs (Bitcask, LSM) make writes cheap and pay later in compaction, read checks and dead space, while update-in-place B-trees make reads predictable and pay with random page writes, WAL plus full-page images, and fragmentation. The RUM conjecture says you cannot bound all three costs at once. The best production evidence for that trade is Facebook's move of its user database from InnoDB to MyRocks: 62.3% smaller and 75% fewer bytes written, for some read cost.

### Cited Findings

**DDIA 2e framing (chapter 4, "Storage and Retrieval", printed pp. 115-150 / PDF pp. 139-174)**
- The chapter opens with the "world's simplest database": two bash functions that append `key,value` lines to a file and `grep`/`tail` for the last match. Appends are fast, but every lookup scans the whole file, so lookup cost is O(n). — [DDIA 2e](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/) printed pp. 116-117 / PDF pp. 140-141
- DDIA defines an index as an extra structure derived from primary data. It changes only performance, not contents, and it costs write overhead and disk space. That is why databases make you choose indexes by hand. — DDIA 2e printed p. 117 / PDF p. 141
- First fix: an in-memory hash map from key to byte offset in the log (Figure 4-1). The book lists four problems: disk space is never reclaimed, the map must be rebuilt by scanning on restart, the map must fit in RAM (on-disk hash maps need random I/O, are costly to grow, and need fiddly collision handling), and range queries are inefficient. — DDIA 2e printed pp. 118-119 / PDF pp. 142-143
- **Changed from the 1st edition:** the 2e chapter body does not name Bitcask (a search of the extracted chapter text finds no "Bitcask"). The hash-index idea is presented generically, so a course that wants a named real system has to supply Bitcask itself. — DDIA 2e chapter 4 text (local extraction)
- SSTable: key-sorted, each key once. Blocks of a few KB, with only each block's first key in a sparse index (which itself can be an immutable B-tree or a trie). Blocks can be compressed. — DDIA 2e printed p. 119 / PDF p. 143
- LSM write path: (1) insert into a memtable (red-black tree, skip list or trie), (2) flush it to a new SSTable segment once it reaches a few MB, (3) read from the memtable, then from segments newest to oldest, (4) merge and compact in the background like mergesort, keeping the newest value. A separate unsorted log protects the memtable from crashes and is discarded after each flush. Deletes are tombstones, which can be dropped once merged into the oldest segment. — DDIA 2e printed pp. 120-121 / PDF pp. 144-145
- DDIA lists RocksDB, Cassandra, ScyllaDB and HBase as using this algorithm, all inspired by Bigtable (which coined "SSTable" and "memtable"). The design was published in 1996 as the Log-Structured Merge-tree (O'Neil et al.). **New in 2e:** segments suit object storage (SlateDB and Delta Lake are the examples). — DDIA 2e printed pp. 121-122 / PDF pp. 145-146
- Bloom filter rule of thumb in DDIA: 10 bits per key gives a 1% false-positive rate, and each extra 5 bits per key cuts it tenfold. — DDIA 2e printed p. 123 / PDF p. 147
- Compaction strategies in DDIA. Size-tiered example: four 256 MB SSTables merge into one 898 MB SSTable, not 1,024 MB, because overwrites, deletes and TTLs drop data. It suits write-heavy workloads but needs lots of temporary disk. Leveled (L0, L1, ...) uses fixed-size, key-range-partitioned SSTables per level. It compacts incrementally, uses less disk and reads fewer SSTables. — DDIA 2e printed p. 124 / PDF p. 148
- Embedded engines (library, no network API) named in DDIA: RocksDB, SQLite, LMDB, DuckDB and KùzuDB, with one embedded DB per tenant as a backend pattern. — DDIA 2e printed p. 125 / PDF p. 149
- B-tree facts in DDIA:
  - Introduced in 1970 and called "ubiquitous" within a decade.
  - Fixed-size pages, traditionally 4 KiB. PostgreSQL uses 8 KiB and MySQL 16 KiB by default.
  - The branching factor is typically several hundred.
  - Splits cascade, and splitting the root adds a level.
  - Depth is O(log n). A four-level tree of 4 KiB pages with branching factor 500 holds up to 250 TB.

  — DDIA 2e printed pp. 125-127 / PDF pp. 149-151
- B-tree reliability in DDIA: a split that overwrites several pages can leave an orphan page after a crash, and hardware may tear a page. Hence a WAL (journaling, in filesystem terms), written before any page change and made durable with fsync. Listed variants:
  - copy-on-write (LMDB);
  - abbreviated keys in interior pages, for higher fanout;
  - laying leaves out sequentially on disk;
  - sibling pointers between leaves.

  — DDIA 2e printed p. 128 / PDF p. 152
- DDIA's B-tree vs LSM comparison:
  - Rule of thumb: LSM for writes, B-tree for reads. Benchmarks are workload-sensitive, so test your own workload.
  - Bloom filters cannot help range queries.
  - RocksDB applies backpressure, suspending reads and writes when the memtable can't flush fast enough.
  - NVMe SSDs serve many parallel reads, which engines must be designed to exploit.

  — DDIA 2e printed p. 129 / PDF p. 153
- SSD sidebar: flash writes 4 KiB pages but erases 512 KiB blocks. Random writes leave blocks with mixed valid and invalid pages, which forces garbage collection that eats bandwidth and wears the drive. — DDIA 2e printed p. 130 / PDF p. 154
- Write amplification in DDIA:
  - Definition: total bytes written to disk divided by the bytes an index-free append-only log would write.
  - A B-tree writes everything at least twice (WAL plus page), and sometimes whole pages for small changes.
  - LSMs typically have lower write amplification because they write no whole pages and can compress SSTable chunks.
  - Benchmarks must run long enough for compaction to compete with writes.

  — DDIA 2e printed pp. 130-131 / PDF pp. 154-155
- Space and deletion in DDIA:
  - B-trees fragment, and free pages in mid-file cannot easily go back to the OS (PostgreSQL's vacuum is the example).
  - LSM dead data is low under leveled compaction but higher under size-tiered.
  - A deleted record lingers until its tombstone reaches the last level, which matters for data-protection deletes.
  - Immutable SSTables make snapshots cheap.

  — DDIA 2e printed pp. 131-132 / PDF pp. 155-156

**Bitcask (the named simplest real system)**
- Bitcask is a directory of append-only files with one active writer file. Each entry is `crc | tstamp | ksz | value_sz | key | value`. The in-memory "keydir" maps each key to `file_id, value_sz, value_pos, tstamp`, so a read needs at most one seek. Merge rewrites immutable files down to live keys and emits hint files for fast startup. The keydir must fit in RAM. Early tests showed 5,000-6,000 writes/s on a laptop with slow disks. Bitcask relies on the OS cache for reads. (prior round) — [Bitcask paper](https://riak.com/assets/bitcask-intro.pdf)

**LSM implementations and numbers**
- RocksDB compaction styles (prior round):
  - Leveled is the default. It is really a hybrid, because L0 is tiered.
  - Universal (tiered) has the lowest write amplification but higher read and space amplification.
  - FIFO drops the oldest files.

  `level0_file_num_compaction_trigger` = 4, `target_file_size_base` = 64 MB, and L0 data must be newer than all lower levels. — [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- The RocksDB wiki says leveled write amplification is "often larger than 10". `level_compaction_dynamic_level_bytes` has been the default since 8.4 and puts about 90% of data in the last level. **Changed:** older tutorials assume static level sizing. (prior round) — [RocksDB Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction)
- RocksDB Bloom filters (prior round): 9.9 bits/key gives 1% FP, 4.9 bits/key 10%, 15.5 bits/key 0.1%. Ribbon filters (since 6.15.0) save about 30% space for 3-4x the CPU. Whole-key filters serve only point lookups. — [RocksDB Bloom Filter](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter)
- RocksDB's latest release is 11.13.2 (Nov 4, 2026). 11.8.0 added async `GetAsync`/`MultiGetAsync`, and 11.0.0 (Feb 2026) added blob storage for wide-column values. Wiki links now point to `github.com/meta/rocksdb` while `facebook/rocksdb` URLs still resolve. (prior round) — [RocksDB releases](https://github.com/facebook/rocksdb/releases)
- **Cassandra Unified Compaction Strategy (UCS):**
  - UCS replaces STCS, LCS and TWCS with one strategy that has a scaling parameter W:
    - W < 0 is leveled: fanout f = 2 − W, threshold t = 2. L10 (W = −8) is equivalent to legacy LCS.
    - W > 0 is tiered: f = 2 + W, t = f. T4 (W = 2) is the default.
    - W = 0 ("N") behaves the same in both modes.
  - Levels can mix modes, and W can change at any time without a full recompaction.
  - UCS uses "density" (SSTable size divided by token range covered) instead of raw size, and splits output at shard boundaries so compactions run in parallel.
  - Amplification relationships given on the page:
    - leveled: write amplification ∝ (f−1) × levels, read amplification ∝ levels;
    - tiered: write amplification ∝ levels, read amplification ∝ (f−1) × levels.
  - Defaults: `target_sstable_size` 1 GiB, `base_shard_count` 4, `min_sstable_size` 100 MiB, `sstable_growth` 0.333.
  - Worked example on the page: 10 TiB at a 1 GiB target would mean over 10K SSTables; growth correction brings it to about 160 SSTables of about 64 GiB.
  - The page calls UCS "recommended for most workloads".

  — [Cassandra UCS docs](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/ucs.html)
- UCS shipped in Cassandra 5.0, alongside SAI, trie memtables and SSTables, and the vector type. Current releases are 5.0.9 (Docker `cassandra:5.0.9`) and 6.0-alpha2. (prior round) — [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html); [Docker Hub cassandra](https://hub.docker.com/_/cassandra)
- **Pebble (CockroachDB):**
  - Introduced as an alternative engine in CockroachDB v20.1 (May 2020) and made the default in v20.2 (Nov 2020).
  - Reasons given: serious RocksDB bugs, the cost of crossing the cgo boundary, and wanting control of the roadmap.
  - It implements only the subset CockroachDB needs (scope cut "by at least 50%").
  - Lineage and compatibility: based on the Go LevelDB port with RocksDB optimizations, and format-compatible with RocksDB 6.2.1 in its default format.
  - It has no column families, and it flushes and compacts only as fast as needed to keep up with writes, which smooths latency spikes.

  (search summary) — [Cockroach Labs: Pebble](https://www.cockroachlabs.com/blog/pebble-rocksdb-kv-store)
- **Key-value separation (WiscKey, FAST 2016):** WiscKey keeps only keys in the LSM and appends values to a separate log, decoupling sorting from garbage collection. Versus LevelDB it reports 2.5x-111x faster loading and 1.6x-14x faster random lookups. The follow-up HashKV paper cites LevelDB write amplification of at least 50x. The journal version concedes WiscKey is not always better; small values and range scans suffer from random value reads. (search summary) — [WiscKey paper](https://usenix.org/system/files/conference/fast16/fast16-papers-lu.pdf); [HashKV, ATC'18](https://webarchive.lib.cuhk.edu.hk/20220904111020mp_/http://www.cse.cuhk.edu.hk/~pclee/www/pubs/atc18.pdf). DDIA 2e mentions the same idea briefly (printed pp. 130-131 / PDF pp. 154-155).

**RUM conjecture (unifying frame)**
- Athanassoulis et al. (EDBT 2016): bounding two of Read, Update and Memory overheads forces a lower bound on the third. (prior round) — [RUM paper](https://openproceedings.org/2016/conf/edbt/paper-12.pdf). DDIA 2e cites it as reference [27] for the B-tree vs LSM rule of thumb.

**B-trees in PostgreSQL and InnoDB**
- PostgreSQL B-trees are multi-level, and each level is a doubly-linked list of pages. Over 99% of pages are leaves. A split happens when a leaf cannot fit an incoming tuple; it inserts a downlink into the parent, cascades upward, and a root split adds a level. — [PG 18 B-tree implementation](https://www.postgresql.org/docs/18/btree.html)
- PG B-tree deduplication merges duplicate keys into "posting list" tuples (key once, then a sorted TID array). It is lazy (runs only when a leaf would otherwise split), on by default and controlled by `deduplicate_items`. It is unsafe for nondeterministic collations, `numeric`, `jsonb`, floats, container types and all `INCLUDE` indexes. The docs say bottom-up deletion arrived in PG 14; before that, only simple deletion existed. It targets "version churn" from non-HOT UPDATEs, where every index gets a new entry even if only one indexed column changed. — [PG 18 B-tree implementation](https://www.postgresql.org/docs/18/btree.html)
- PG pages are 8 kB: a 24-byte header, 4-byte line pointers growing forward, tuples growing backward, and `pd_lsn` in each header. B-tree pages keep sibling links in the special space. (prior round) — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- PG 18 added B-tree skip scan for multicolumn indexes with no condition on the leading column. Oracle has had skip scans since 9i (2002). (prior round) — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/); [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- InnoDB tables are clustered indexes on the primary key. Secondary index records carry no hidden system columns and are not updated in place. Hidden row columns are a 6-byte DB_TRX_ID, a 7-byte DB_ROLL_PTR and a 6-byte DB_ROW_ID. (prior round) — [MySQL 8.4 multi-versioning](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)

**Copy-on-write B-trees (LMDB)**
- LMDB writes modified pages to new locations and builds new parent versions up to a new root (shadow paging) instead of overwriting pages and keeping a WAL. DDIA 2e notes this also gives snapshot reads. — DDIA 2e printed p. 128 / PDF p. 152
- Secondary descriptions (dbdb.io, Wikipedia):
  - Write transactions are serialized by a mutex, while readers proceed lock-free in parallel.
  - There is no WAL. The atomic root update after the new tree is saved gives durability up to the last committed root (with fsync/fdatasync).
  - LMDB keeps two B+trees: user data and free pages.
  - Sources disagree on how many versions are retained.

  (search summary; not primary docs) — [dbdb.io LMDB](https://dbdb.io/db/lmdb); [Wikipedia LMDB](https://Www.Wikipedia.org/wiki/LMDB)
- The mmap paper lists LMDB as an mmap user with shadow paging and a single writer. Its advice is to use mmap only when the working set fits in memory and is read-mostly. (prior round) — [Crotty, Leis, Pavlo, CIDR 2022](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)

**B-tree vs LSM: production and benchmark evidence**
- **MyRocks at Facebook (Matsunobu, Dong, Lee, PVLDB 13(12), 2020):**
  - UDB's goal was to halve the server count, which needed MyRocks to use at most 50% of InnoDB's space.
  - Result: instance size fell 62.3% versus *compressed* InnoDB; in Table 1, MyRocks was 37.7% of InnoDB's size. Bytes written to flash fell 75%, and CPU was "slightly reduced". The migration finished in August 2017.

  — [MyRocks paper](https://www.vldb.org/pvldb/vol13/p3217-matsunobu.pdf)
- Why InnoDB lost on space and writes, from the same paper:
  - About 25-30% of each InnoDB block was wasted to fragmentation, and defragmenting did not stick under random writes.
  - InnoDB compression must pre-pick `key_block_size` (1/2/4/8 KB). A 16 KB page that compresses to 5 KB still occupies 8 KB, which caps savings at 50%.
  - Each row carries 13 bytes of transaction metadata.
  - One row change rewrites a whole 8 KB page, and the doublewrite buffer doubles it.
  - On the RocksDB side, dead data was kept to about 10% by tuning compaction. The 7-byte sequence numbers are zeroed in Lmax and compress to almost nothing.

  — [MyRocks paper](https://www.vldb.org/pvldb/vol13/p3217-matsunobu.pdf)
- Mark Callaghan's Insert Benchmark:
  - 2017 Intel NUC runs: InnoDB wrote about 10x more to storage per insert than MyRocks during load, and over 30x more in one read-write step. The reasons given are read-free secondary index maintenance and lower write amplification in MyRocks.
  - 2024 runs (MyRocks 8.0): the gap shrank to about 2x. Callaghan notes something in MyRocks 8.0 raised write amplification.

  (search summary) — [Small Datum 2017](https://smalldatum.blogspot.com/2017/11/insert-benchmark-in-memory-intel-nuc.html); [Small Datum 2024](https://smalldatum.blogspot.com/2024/06/the-insert-benchmark-vs-myrocks-and_14.html). DDIA 2e cites Callaghan's "Read, Write & Space Amplification—B-Tree vs. LSM" as reference [40].
- The mmap paper shows LevelDB's mmap read path pushed RocksDB to fork, and that MongoDB's MMAPv1 was deprecated in 2015 and removed in 2019. (prior round) — [CIDR 2022 mmap paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)

### Inferences

**Concept ladder (problem → simplest version → where it breaks → improvement)**
1. *Append-only log.*
   - Problem: store and get back data.
   - Simplest: `echo >> file` (DDIA p. 116).
   - Breaks: O(n) reads.
   - Fix: an index.
2. *Hash index over the log (Bitcask).*
   - Problem: O(n) reads.
   - Simplest: keydir in RAM.
   - Breaks: the keydir must fit RAM, the log grows forever, restart needs a full scan, and range queries are impossible (DDIA pp. 118-119; Bitcask paper).
   - Fixes: segments plus merge for space, hint files for restart, sorted files for ranges.
3. *SSTable plus memtable (LSM).*
   - Problem: range queries, and indexes too big for RAM.
   - Simplest: sorted segments with sparse indexes.
   - Breaks: reads check many files, and missing keys are worst.
   - Fixes: Bloom filters (10 bits/key ≈ 1% FP; RocksDB measures 9.9 bits for 1%) and compaction.
4. *Compaction policy.*
   - Problem: too many files and dead data.
   - Simplest: size-tiered.
   - Breaks: up to 2x temporary space and high read amplification.
   - Fix: leveled, which raises write amplification ("often larger than 10" in RocksDB).
   - Unification: Cassandra 5 UCS's single W knob, where L10 equals LCS and T4 roughly equals STCS.
   - Big values: key-value separation (WiscKey, RocksDB BlobDB).
5. *B-tree.*
   - Problem: predictable point and range reads with in-place updates.
   - Simplest: pages plus splits.
   - Breaks: a crash mid-split leaves orphans, pages tear, every page write is random, and pages fragment (25-30% waste at Facebook).
   - Fixes: WAL plus full-page images or doublewrite (Q2), fillfactor, deduplication (PG 13+), bottom-up deletion (PG 14+), or abandoning in-place updates (LMDB copy-on-write, or LSM).
6. *Copy-on-write B-tree (LMDB).*
   - Problem: avoid the WAL and get lock-free readers.
   - Breaks: one writer at a time, every write copies the root-to-leaf path, and mmap pitfalls apply.
   - Fit: read-heavy embedded use.

**Misconceptions to address**
- "LSM is always faster for writes." Write amplification moves to compaction, and once compaction competes with foreground writes, throughput falls and RocksDB stalls writes. DDIA warns that short benchmarks on an empty LSM mislead.
- "LSM is worse for reads, full stop." Bloom filters make point reads cheap. Range scans and recently updated hot keys are the real cost. MyRocks reported *slightly reduced* CPU on Facebook's real workload.
- "B-trees waste no space." InnoDB lost 25-30% to fragmentation, and its compression is capped by fixed block sizes.
- "A delete removes the data." In an LSM, old versions survive until the tombstone reaches the last level; in PostgreSQL, until VACUUM runs.
- "Tiered vs leveled is a binary choice." UCS and RocksDB's L0 show they mix per level.
- "B-tree and B+tree are different things you must distinguish." DDIA deliberately uses "B-tree" for the B+tree shape (p. 126). Tell readers that the textbook distinction exists but production indexes are B+trees.

**Version and "changed since" notes for the writer**
- RocksDB 11.x (Nov 2026). `level_compaction_dynamic_level_bytes` defaults on since 8.4.
- Cassandra 5.0 adds UCS, which makes the old "choose STCS or LCS" advice obsolete.
- Pebble has been CockroachDB's default since v20.2.
- DDIA 2e no longer names Bitcask in its chapter 4 text.

### Gaps
- O'Neil et al. 1996 (the LSM paper) was not fetched. Its original cost model (the five-minute-rule argument and disk-arm savings) is unverified here, and DDIA only cites it.
- No primary LMDB documentation was fetched. Retained-version semantics and the free-list design rest on dbdb.io and Wikipedia.
- PostgreSQL B-tree default fillfactor (believed 90; heap default believed 100), Lehman-Yao high keys and right links, and suffix truncation (PG 12) were not confirmed from a fetched page. The fetched btree.html page omits them, and `src/backend/access/nbtree/README` should be checked.
- InnoDB page-merge threshold (`MERGE_THRESHOLD`, believed 50%) and InnoDB's default 16 KB page size were not fetched. DDIA 2e states MySQL uses 16 KiB pages by default.
- Whether UCS is the *default* compaction strategy in Cassandra 5.0 (as opposed to recommended) was not confirmed. The UCS page does not say.
- Exact WiscKey write-amplification numbers and Callaghan's absolute KB-written-per-insert values were not read from primary tables.
- No 2025-2026 head-to-head B-tree vs LSM benchmark on modern NVMe was found (for example, PG 18 vs RocksDB 11).

---

## Q2. Durability and recovery: WAL, checkpoints, ARIES, torn pages and full-page writes, buffer pool vs OS page cache, O_DIRECT, io_uring and PostgreSQL 18 asynchronous I/O

### Takeaway
Durability rests on one rule: log the change and fsync the log before the changed page reaches disk. Recovery then replays the log, made idempotent by per-page LSNs, and ARIES adds undo of losers after "repeating history". Torn pages need a second defence, PostgreSQL's full-page images or InnoDB's doublewrite. PostgreSQL 18 (Sep 2025) added asynchronous reads, with `worker` the default and `io_uring` optional. That is the first step away from the OS page cache, which PostgreSQL alone among major DBMSs still leans on.

### Cited Findings

**WAL and checkpoints**
- WAL rule in PostgreSQL: data-file changes may be written only after their WAL records are flushed. Data pages need not be flushed at commit, because REDO rebuilds them. WAL syncing is cheap because the log is sequential. (prior round) — [PG WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)
- Each PG page header's `pd_lsn` records the last WAL record that changed the page, which makes redo idempotent. (prior round) — [PG page layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- PostgreSQL 18 WAL settings:
  - `checkpoint_timeout` defaults to 5 min (range 30 s to 1 day).
  - `max_wal_size` defaults to 1 GB and is a soft limit.
  - Raising either "can increase the amount of time needed for crash recovery".
  - `checkpoint_completion_target` defaults to 0.9, spreading checkpoint I/O over the interval. Lowering it is not recommended because it causes I/O bursts.

  — [PG 18 WAL config](https://www.postgresql.org/docs/18/runtime-config-wal.html)
- `synchronous_commit` (default `on`) has levels `remote_apply`, `on`, `remote_write`, `local` and `off`.
  - `off` can lose recent commits on a crash, but unlike `fsync=off` it does not risk inconsistency. The worst-case delay is three times `wal_writer_delay`.
  - It can be set per transaction (`SET LOCAL synchronous_commit TO OFF`).
  - Group commit: `commit_delay` (default 0 µs) waits only if at least `commit_siblings` (default 5) transactions are active.
  - `wal_sync_method` defaults to `fdatasync` on Linux and FreeBSD.

  — [PG 18 WAL config](https://www.postgresql.org/docs/18/runtime-config-wal.html)
- SQLite contrast (prior round):
  - Rollback-journal mode (the default) copies the original pages aside, and a commit happens when the journal is deleted.
  - WAL mode (since 3.7.0, 2010-07-21) appends changes, a commit is a commit record, and an auto-checkpoint runs at 1,000 pages (about 4 MB).
  - There is one writer at a time, readers see a snapshot, and processes must share a host.

  — [SQLite WAL](https://www.sqlite.org/wal.html)
- DDIA 2e: once data is in the WAL and fsynced it is durable, and B-tree pages can stay buffered in memory. Crash recovery is deferred to chapter 8. — DDIA 2e printed p. 128 / PDF p. 152

**ARIES**
- ARIES (Mohan, Haderle, Lindsay, Pirahesh, Schwarz; ACM TODS 17(1), March 1992):
  - It repeats history, redoing all missing updates before rolling back losers.
  - It keeps an LSN in each page and logs the updates made during rollback (compensation records), which bounds logging even across repeated restart failures.
  - It supports fuzzy checkpoints.

  (prior round) — [ARIES paper](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)

**Torn pages: full-page writes vs doublewrite**
- PG `full_page_writes` (default `on`) handles OS crashes mid-write that leave a page holding a mix of old and new data. The server writes the entire page to WAL on the first modification after each checkpoint, because row-level WAL alone cannot repair a torn page. `wal_compression` (default `off`; `pglz`, `lz4`, `zstd`) compresses those full-page images at some CPU cost. — [PG 18 WAL config](https://www.postgresql.org/docs/18/runtime-config-wal.html)
- InnoDB writes pages to a doublewrite area first, sequentially and with a single fsync, then to the data files. Modes are `ON`, `DETECT_ONLY` and `OFF`, and atomic-write devices disable it automatically. (prior round) — [MySQL 8.4 doublewrite](https://dev.mysql.com/doc/refman/8.4/en/innodb-doublewrite-buffer.html)
- Facebook named doublewrite as one cause of InnoDB's high write amplification on flash. — [MyRocks paper](https://www.vldb.org/pvldb/vol13/p3217-matsunobu.pdf)
- DDIA 2e cites Tomas Vondra's "On the Impact of Full-Page Writes" (ref [39]) and Percona's "InnoDB Double Write" (ref [38]) to explain why a B-tree sometimes writes a whole page for a few changed bytes. — DDIA 2e printed p. 131 / PDF p. 155 and its reference list
- PG 18 initdb enables data checksums by default (`--no-data-checksums` opts out). PG 19 (RC1, 2026-10-15) can toggle checksums online. **Changed:** pre-18 guides say checksums are off by default. (prior round) — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/); [PG 19 Beta 1](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)

**fsync semantics**
- "fsyncgate" (2018): Linux before 4.13 could drop fsync errors and mark pages clean, so a retried fsync "succeeded" on lost data. PostgreSQL now PANICs on fsync failure (fixed in v12, backpatched to 9.4). (prior round) — [PG wiki Fsync Errors](https://wiki.postgresql.org/wiki/Fsync_Errors)
- Pavlo reports SurrealDB benchmarks were run while it was not flushing writes to disk. (prior round) — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)

**Buffer pool vs OS page cache, mmap, O_DIRECT**
- PostgreSQL's buffer manager uses pins plus content locks and clock-sweep eviction with usage counts. Ring buffers give scan resistance: 256 KB for sequential scans and 16 MB for bulk writes. (prior round) — [PG buffer README](https://github.com/postgres/postgres/blob/master/src/backend/storage/buffer/README)
- `shared_buffers` defaults to 128 MB, the docs suggest about 25% of RAM, and more than 40% is unlikely to help, because PG double-caches through the OS. (prior round) — [PG resource config](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- Pavlo: PostgreSQL is the only major DBMS still relying on the OS page cache, and PG 18 AIO starts the path off it. (prior round) — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- The mmap paper's case against letting the OS manage pages:
  - Transactional safety: the OS can flush dirty pages anytime.
  - I/O stalls on page faults.
  - SIGBUS on I/O errors.
  - Page-table contention, single-threaded kswapd and TLB shootdowns.

  Once eviction starts, mmap is 2-20x worse than fio. With O_DIRECT, fio reached about 900K random reads/s on one PM1733 NVMe (100 threads, about 100 µs latency). (prior round) — [CIDR 2022 mmap paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- MyRocks used Direct I/O at Facebook, which the paper lists among its techniques. Only the term was confirmed in the extracted text; the details were not read. — [MyRocks paper](https://www.vldb.org/pvldb/vol13/p3217-matsunobu.pdf)

**PostgreSQL 18 asynchronous I/O and io_uring**
- PG 18.0 was released 2025-09-25, and the current minor is 18.6. AIO lets backends queue multiple reads (sequential scans, bitmap heap scans, VACUUM). New settings: `io_method` (`worker` default, `io_uring` if built `--with-liburing`, or `sync`), `io_workers` = 3, `io_combine_limit` = 128 kB, and `effective_io_concurrency` default raised from 1 to 16. There is a new `pg_aios` view. (prior round) — [PG 18 release notes](https://www.postgresql.org/docs/release/18.0/); [PG 18 resource config](https://www.postgresql.org/docs/current/runtime-config-resource.html)
- pganalyze benchmark:
  - Setup: AWS c7i.8xlarge (32 vCPU, 64 GB), io2 EBS at 20,000 IOPS, a 3.5 GB table of 100M rows, cold cache, `SELECT COUNT(*)`, no parallel query.
  - Results: PG 17 took 15,831 ms. PG 18 took 15,071 ms with `sync`, 10,052 ms with `worker` and 5,723 ms with `io_uring`, so about 1.5x and 2.6x faster than PG 18 `sync`.
  - AIO in PG 18 covers reads only; writes stay synchronous.
  - EXPLAIN I/O timings understate effort under AIO (the same 442,478 buffers showed 14,779 ms of I/O on PG 17 vs 7,219 ms under `worker`).

  — [pganalyze, PG 18 async I/O](https://pganalyze.com/blog/postgres-18-async-io)
- Tomas Vondra's benchmark (cited in PGConf.EU 2025 slides) found `worker` about 2x faster than `sync` for sequential scans, with `io_uring` in between. His explanation: under `io_uring` the backend does checksums and memory copies itself, while `worker` spreads that work across processes. This conflicts with pganalyze's cold-cache ranking, so hardware matters. (search summary) — [PGConf.EU 2025 PG18 performance slides](https://www.postgresql.eu/events/pgconfeu2025/sessions/session/7008/slides/754/pg18-performance-talk-present.pdf)
- PG 19 (RC1 2026-10-15) auto-scales `io_method=worker` between `io_min_workers` and `io_max_workers` and adds an `IO` option to EXPLAIN ANALYZE. (prior round) — [PG 19 Beta 1](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/); [PG versioning](https://www.postgresql.org/support/versioning/)
- Docker 25.0.0 began blocking `io_uring_setup`/`io_uring_enter`/`io_uring_register` in the default seccomp profile, citing container-escape risk. Google reported in 2023 that 60% of kCTF submissions exploited io_uring. (prior round) — [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/); [oss-sec mirror of Google post](https://seclists.org/oss-sec/2023/q2/235)

### Inferences

**Concept ladder**
1. *Overwrite pages in place.* Breaks: a crash mid-update or mid-split corrupts the tree (DDIA p. 128). Fix: WAL plus fsync.
2. *WAL with flush-before-page.* Breaks: unbounded replay time and unbounded log. Fix: checkpoints (`checkpoint_timeout` 5 min, `max_wal_size` 1 GB). This trades recovery time against write bursts, and `checkpoint_completion_target` 0.9 spreads the burst.
3. *Redo-only recovery.* Breaks: uncommitted changes already on disk under a steal policy, plus repeated crashes during restart. Fix: ARIES (repeat history, undo losers, compensation records, per-page LSN).
4. *Row-level WAL.* Breaks: torn 8 kB pages, which row deltas cannot repair. Fix: full-page images after each checkpoint (PG) or doublewrite (InnoDB). Both cost write amplification, which ties back to the Q1 MyRocks numbers. A lab can show the FPI share of WAL dropping as checkpoints get rarer.
5. *Fsync per commit.* Breaks: throughput is capped by device flush latency. Fixes: group commit (`commit_delay`) and the per-transaction `synchronous_commit=off` trade.
6. *Rely on the OS page cache or mmap.* Breaks: there is no control over write-back order, eviction is poor, errors surface as SIGBUS, and fsync errors can be lost. Fixes: own buffer pool plus O_DIRECT (InnoDB, RocksDB with direct I/O, LeanStore). PG 18 AIO is PostgreSQL's first step there.

**Misconceptions**
- "Commit writes the data pages." Only the log is flushed at commit.
- "fsync returned 0, so the data is safe." See fsyncgate.
- "io_uring is always faster." The pganalyze and Vondra results disagree, and Docker blocks io_uring by default, so laptop labs will see `worker`.
- "Checksums prevent corruption." They detect it. PG 18 turns them on by default.
- "`synchronous_commit=off` is like `fsync=off`." It is not: `off` loses recent commits but keeps the database consistent, while `fsync=off` can corrupt it.

### Gaps
- `debug_io_direct` (PostgreSQL's developer-only direct I/O switch, believed added in PG 16) does not appear on the PG 18 WAL config page. Its location and status were not verified.
- Vondra's own post (vondra.me/posts/tuning-aio-in-postgresql-18/) was not fetched. His numbers come only through a search summary of slides.
- ARIES's three-pass structure (analysis, redo, undo) and its dirty-page and transaction tables were not re-read beyond the abstract-level quotes from the prior round.
- No source was fetched for `pg_stat_wal` columns (`wal_fpi`, `wal_bytes`), which the torn-page lab depends on. Confirm in the PG 18 monitoring docs.
- Whether PG 19 has reached GA by Nov 7, 2026 is unknown (RC1 was 2026-10-15).

---

## Q3. Indexes: secondary, clustered vs heap, covering, multicolumn, partial and expression; multidimensional (R-tree, GiST, geohash, H3); full-text (inverted index, BM25, Lucene); vector (HNSW, IVF, DiskANN, PQ/SQ, pgvector, recall vs latency)

### Takeaway
Every index is a sorted or clustered copy of some data that answers one access pattern, paid for on every write. Where the row lives (clustered in InnoDB vs heap plus TID in PostgreSQL) decides what a secondary lookup costs and whether an index-only scan is possible. Multidimensional, text and vector indexes extend the same idea when one sort order is not enough. Vector indexes are approximate: recall is a tunable you trade against latency and memory (pgvector `hnsw.ef_search` default 40). DiskANN showed billion-scale search from SSD at 95%+ recall with under 3 ms mean latency.

### Cited Findings

**DDIA 2e framing**
- A secondary index entry is non-unique. Two solutions: a list of row IDs per key (a postings list) or a unique key made by appending the row ID. Both B-trees and LSMs can hold secondary indexes. — DDIA 2e printed p. 132 / PDF p. 156
- Where values live:
  - Clustered index: the row is stored inside the index. InnoDB's primary key always is one; SQL Server allows one per table.
  - Reference to the row, either a primary key (InnoDB secondaries) or a heap location (PostgreSQL).
  - Covering index, or index with included columns.

  Growing a heap row forces either updating all indexes or leaving a forwarding pointer. — DDIA 2e printed p. 133 / PDF p. 157
- Concatenated indexes work like a phone book on (last name, first name): useless for first-name-only queries. A latitude/longitude box needs a true 2-D index. Options: a space-filling curve over a B-tree; R-trees or Bkd-trees; PostGIS R-trees built on GiST; or regular grids of triangles, squares or hexagons. Other examples: an (R, G, B) colour index and a (date, temperature) index. — DDIA 2e printed pp. 145-146 / PDF pp. 169-170
- Full text in DDIA:
  - Each term is a dimension. An inverted index maps a term to a postings list, which can be a sparse bitmap. AND becomes bitwise AND.
  - Lucene stores term-to-postings maps in SSTable-like files merged in the background. PostgreSQL GIN also uses postings lists.
  - Trigram indexes allow substring and regex search but are large.
  - Lucene handles typos with a finite-state automaton over terms, transformed into a Levenshtein automaton.

  — DDIA 2e printed pp. 146-147 / PDF pp. 170-171
- Vectors in DDIA:
  - Embeddings often exceed 1,000 dimensions. Distance is cosine or Euclidean.
  - R-trees fail at high dimensionality.
  - Index types: flat (exact, slow), IVF (partitions around centroids, with "probes" trading accuracy for speed) and HNSW (layered proximity graphs).
  - Faiss and pgvector support both IVF and HNSW.
  - It warns that "vectorized processing" and "vector embeddings" mean different things.

  — DDIA 2e printed pp. 147-149 / PDF pp. 171-173
- **What DDIA 2e omits:** DiskANN, product quantization and scalar quantization are not covered. The course must add them.

**PostgreSQL index features**
- Index-only scans require an index type that supports them (B-tree always; GiST and SP-GiST for some opclasses; GIN never) and a query that references only indexed columns. Visibility comes from the visibility map, which is "four orders of magnitude smaller than the heap". If a page is not all-visible, the heap must be visited anyway. — [PG 18 index-only scans](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- `INCLUDE` (covering) columns:
  - Example: `CREATE INDEX tab_x_y ON tab(x) INCLUDE (y)`.
  - Payload columns need no operator class, and uniqueness applies only to the key columns.
  - Supported by B-tree, GiST and SP-GiST only, and expressions cannot be included.
  - Wide payloads bloat the index and can exceed the tuple size limit, causing insert failures.
  - Payload helps only if the table changes slowly enough for pages to stay all-visible.

  — [PG 18 index-only scans](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- Multicolumn rule: equality on leading columns plus an inequality on the first non-equality column bounds the scan. PG 18 skip scan handles a missing leading condition when that column has few distinct values. (prior round) — [PG 18 multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- Partial indexes:
  - They index only rows matching a predicate.
  - Uses: excluding common values, excluding uninteresting rows (`WHERE billed is not true`), and partial uniqueness (`CREATE UNIQUE INDEX ... ON tests (subject, target) WHERE success`).
  - The planner uses one only if the query's WHERE provably implies the predicate, and only simple implications are recognized. Matching happens at plan time, so parameterized clauses like `x < ?` do not match.
  - The docs call one partial index per category "a bad idea" and recommend a composite index or partitioning instead.

  — [PG 18 partial indexes](https://www.postgresql.org/docs/18/indexes-partial.html)
- GiST:
  - GiST is a balanced-tree template in which "B-trees, R-trees and many other indexing schemes can be implemented". It comes from Berkeley's GiST project and Kornacker's thesis.
  - An opclass supplies five required methods (`same`, `consistent`, `union`, `penalty`, `picksplit`) and up to seven optional ones. The GiST layer handles concurrency, logging and tree search.
  - Built-in opclasses: geometric `box_ops`/`point_ops`/`poly_ops`/`circle_ops`, `inet_ops` (not the default), `range_ops`/`multirange_ops`, and `tsvector_ops`.
  - KNN ordering with `<->` returns the smallest distances first.
  - Index-only scans need a `fetch` method and are impossible with lossy compression.

  — [PG 18 GiST](https://www.postgresql.org/docs/18/gist.html)
- PostgreSQL's MVCC means non-HOT updates create entries in every index. The authors estimate about 46% of updates are HOT (Pavlo's critique). (prior round) — [Pavlo, "The Part of PostgreSQL We Hate the Most"](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)

**Geospatial grids (H3, geohash)**
- H3 has 16 resolutions (0-15). Resolution 0 is 122 base cells (110 hexagons and 12 pentagons). Each cell has 7 children (aperture 7), ids are 64-bit integers, and the finest cells are under 1 m². Hexagons give all six neighbours equal distance. Child cells do not tile the parent exactly, so containment by truncating the id is approximate, though logical containment in the index is exact. (search summary; secondary sources) — [CARTO H3 glossary](https://carto.com/glossary/h3-spatial-index/); [Felt: What is H3](https://felt.com/blog/what-is-h3)

**Full-text: Lucene**
- BM25 replaced TF-IDF as Lucene's default similarity in Lucene 6. (search summary) — [Elastic: BM25 vs Lucene default similarity](https://www.elastic.co/blog/found-bm-vs-lucene-default-similarity)
- `TieredMergePolicy` (Lucene 9.x docs): at most 10 segments merged at once and 10 segments per tier by default. Force-merge-deletes merges a segment only if more than 10% of its docs are deleted. (search summary) — [Lucene 9.7 TieredMergePolicy](https://lucene.apache.org/core/9_7_0/core/org/apache/lucene/index/TieredMergePolicy.html)
- Lucene 10.2.0 raised the default floor segment size of TieredMergePolicy from 2 MB to 16 MB. **Changed:** older merge-tuning advice predates this. (search summary) — [Lucene 10.2.0 release notes mirror](https://newreleases.io/project/github/apache/lucene/release/releases%2Flucene%2F10.2.0)

**Vector indexes**
- HNSW (Malkov and Yashunin; arXiv 2016, IEEE TPAMI 2018):
  - Builds a multi-layer graph in which each element's top layer is drawn from an exponentially decaying distribution.
  - Search starts at the top layer.
  - Separating links by scale gives logarithmic complexity scaling, where NSW's polylogarithmic routing degrades on low-dimensional or clustered data.
  - A neighbour-selection heuristic boosts high-recall and clustered-data performance.

  (search summary) — [HNSW arXiv 1603.09320](https://arxiv.org/abs/1603.09320)
- DiskANN (Subramanya et al., NeurIPS 2019) indexes a billion points on one workstation with 64 GB RAM and a cheap SSD. On SIFT1B it serves more than 5,000 queries/s with under 3 ms mean latency at 95%+ 1-recall@1 on 16 cores. Similar-memory baselines (FAISS, IVFOADC+G+P) plateau near 50% 1-recall@1. At high recall it holds 5-10x more points per node than HNSW or NSG. (search summary) — [DiskANN, NeurIPS 2019](https://papers.nips.cc/paper/2019/hash/09853c7fb1d3f8ee67a61b6bf4a7f8e6-Abstract.html)
- Product quantization (Jégou, Douze, Schmid; IEEE TPAMI 33(1), 2011):
  - Splits a vector into low-dimensional subspaces and quantizes each one separately; the code is the tuple of subspace indices.
  - Distances can be estimated from codes, and the asymmetric variant (raw query vs code) is more precise.
  - The method was validated on two billion vectors, with 64-bit codes discussed.

  (search summary) — [PQ paper (HAL)](https://hal.univ-grenoble-alpes.fr/inria-00514462v1)
- pgvector 0.8.7 (current install tag) supports Postgres 13+:
  - HNSW defaults: `m` = 16, `ef_construction` = 64, `hnsw.ef_search` = 40.
  - IVFFlat: `lists` = rows/1000 up to 1M rows, then sqrt(rows); `ivfflat.probes` defaults to 1, start at sqrt(lists), and probes = lists gives exact search; build the index after loading data.
  - Index dimension limits: `vector` 2,000, `halfvec` 4,000, `bit` 64,000, `sparsevec` 1,000 non-zero elements (HNSW only).
  - Quantization: `halfvec` expression indexes, or binary quantization (`binary_quantize` with `bit_hamming_ops`) followed by re-ranking with the full vectors (fetch 20, re-rank to 5).
  - Iterative scans (since 0.8.0): `hnsw.iterative_scan` = `strict_order`/`relaxed_order`, `hnsw.max_scan_tuples` = 20,000.
  - Filtering caveat: filters run after the ANN scan. At `ef_search` 40, a filter matching 10% of rows returns only about 4 rows on average.
  - Builds are much faster if the graph fits in `maintenance_work_mem`.
  - To measure recall, compare against exact results with `enable_indexscan = off`.

  — [pgvector README](https://github.com/pgvector/pgvector)
- Milvus 2.6 (June 2025) added RaBitQ 1-bit quantization and the Woodpecker WAL. Weak source. (prior round, search result) — [dio.me article](https://www.dio.me/en/articles/vector-database-em-2026-o-que-mudou-nas-releases-aa9ff5545027)
- Cassandra 5.0 added a vector type and similarity functions, and SAI. (prior round) — [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html)
- CMU 15-445 Fall 2026 groups "trees, hash tables, vector" under indexes and filters. (prior round) — [CMU 15-445](https://15445.courses.cs.cmu.edu/)

### Inferences

**Concept ladder**
1. *Primary-key index.* Breaks: queries by any other column. Fix: a secondary index, with posting lists or row-id-suffixed keys.
2. *Secondary index pointing to a heap TID (PostgreSQL).* Breaks: each lookup costs a random heap visit, and every non-HOT update touches every index.
   - InnoDB alternative: point to the primary key. Updates don't move secondary pointers, but each secondary lookup costs two B-tree descents.
   - Clustered vs heap is the "where does the row live" decision.
3. *Covering/INCLUDE index.* Breaks: index-only scans still visit the heap until VACUUM sets visibility-map bits; payload bloats the index.
4. *Partial and expression indexes.* Partial indexes break with parameterized queries (plan-time matching) and when many are used as a substitute for partitioning. Expression indexes are only used if the query's expression matches.
5. *Concatenated index for 2-D data.* Breaks: bounding-box queries (DDIA's lat/long example). Fixes: space-filling curve or geohash over a B-tree; R-tree via GiST; fixed grids such as H3 hexagons for aggregation and joins.
6. *Inverted index.* Breaks: ranking (fixed by TF-IDF, then BM25 as the default since Lucene 6), updates (fixed by immutable segments plus merge policy, which is an LSM again) and typos (fixed by Levenshtein automata).
7. *Flat vector scan.* Breaks: O(n·d) per query. Fixes:
   - IVF: probes trade recall for speed.
   - HNSW: logarithmic routing, but the whole graph must sit in RAM and memory is high.
   - DiskANN: graph on SSD with compressed vectors in RAM, giving billion scale on 64 GB.
   - PQ/SQ/binary quantization: smaller vectors, so lower recall unless you re-rank.
   - Iterative scans: fix the post-filtering shortfall.

**Misconceptions**
- "Adding an index can only help." Every index slows writes and takes space (DDIA p. 117), and in PostgreSQL non-HOT updates hit every index.
- "An index-only scan never touches the table." Not until the visibility map marks the pages all-visible; watch `Heap Fetches`.
- "A composite index on (a, b) serves queries on b." Mostly no. PG 18 skip scan helps only when `a` has few distinct values.
- "Vector search is exact." HNSW and IVF are approximate, so recall must be measured.
- "Filtering with ANN just works." pgvector's 10%-selectivity example returns about 4 of 40 rows at the defaults.
- "R-trees work for embeddings." DDIA explicitly says they don't at high dimensionality.
- "Column store" and "wide-column store" are not the same; see Q5.

### Gaps
- PostgreSQL expression-index docs (indexes-expressional.html) and GIN internals were not fetched. The pending-list and fastupdate details are unverified.
- Geohash has no primary source here (the base-32 Z-order interleaving of lat/long bits is textbook knowledge). Uber's 2018 H3 announcement and h3geo.org were not fetched, so the H3 facts come from secondary sites.
- The current Lucene version as of Nov 2026 (10.x minor) and the current Elasticsearch and OpenSearch versions were not checked.
- HNSW's measured recall and QPS curves, its memory overhead per element (roughly M×2 links at layer 0), and ann-benchmarks numbers were not retrieved.
- Scalar quantization (int8) has no primary source, and RaBitQ's paper (SIGMOD 2024) was not fetched.
- pgvectorscale's StreamingDiskANN and other DiskANN-in-Postgres options were not checked. The pgvector 0.8.7 release date was not checked either.
- Whether pgvector added HNSW in 0.5.0 (believed August 2023) was not verified.

---

## Q4. In-memory databases: why they are fast, anti-caching, persistent memory's rise and fall, and NVMe changing the assumptions

### Takeaway
Harizopoulos et al. (SIGMOD 2008) showed that an in-memory OLTP engine is fast because it drops buffer management, latching, locking and logging, not because it avoids disk reads. In Shore those components took about 35%, 14%, 16% and 12% of New Order instructions, and useful work was about 1/60 of the total. Since then two things happened. Persistent memory (Optane) arrived and was discontinued in 2022. NVMe SSDs reached more than 1M IOPS each, which revived "disk-based but memory-speed" designs (LeanStore) and buffer-managed engines over mmap.

### Cited Findings
- DDIA 2e: in-memory databases are not fast because they skip disk reads, since the OS cache would serve a disk engine from memory anyway. They are fast because they avoid encoding in-memory structures into a disk format. DDIA cites Harizopoulos et al. as reference [49]. It names VoltDB, SingleStore and Oracle TimesTen (relational), RAMCloud (log-structured in memory and on disk), and Redis/Couchbase (asynchronous, weak durability). Durability comes from a log, snapshots or replication. A second benefit is data models that are hard on disk, such as Redis priority queues and sets. — DDIA 2e printed p. 134 / PDF p. 158
- **Changed from the 1st edition:** a search of the extracted 2e chapter 4 text finds no anti-caching or non-volatile/persistent-memory discussion; NVMe appears only as an SSD interface. — DDIA 2e chapter 4 text (local extraction)
- **Harizopoulos, Abadi, Madden, Stonebraker, "OLTP Through the Looking Glass, and What We Found There" (SIGMOD 2008):**
  - Method: they progressively stripped Shore while running a TPC-C subset, from about 640 TPS to a 12,700 TPS single-threaded, lock-free, main-memory kernel without recovery, explaining "about a factor of 20x".
  - New Order cost 1.73 million instructions. Each of logging, locking, latching and buffer management accounts for about 10%-35%.
  - "Useful work" is about 1/60th of the total. The fully stripped Shore still used about 1/15th of the original instructions, about 4x the useful work.
  - The abstract finds no single "high pole in the tent".

  — [Harizopoulos et al. 2008](https://faculty.cc.gatech.edu/~jarulraj/courses/4420-s19/papers/02-inmemory/hstore-lookingglass.pdf)
- Same paper, other numbers:
  - Shore out of the box, data cached, logging on: about 640 TPS (1.6 ms per transaction).
  - Without log flushing: about 1,700 TPS (588 µs).
  - Stripped kernel: about 80 µs per transaction (12,700 TPS).
  - Useful-work kernel: about 22 µs (46,500 TPS).

  — [Harizopoulos et al. 2008](https://faculty.cc.gatech.edu/~jarulraj/courses/4420-s19/papers/02-inmemory/hstore-lookingglass.pdf)
- Figure 1 of the paper carries the segment values 34.6%, 14.2%, 16.3%, 11.9%, 16.2% and 6.8%, with labels buffer manager, latching, locking, logging, hand-coded optimizations and the residual. Text extraction loses the pairing. A course slide deck gives buffer pool 34%, latching 14%, locking 16% and logging 12%, which matches the first four. — [Harizopoulos et al. 2008](https://faculty.cc.gatech.edu/~jarulraj/courses/4420-s19/papers/02-inmemory/hstore-lookingglass.pdf); [SFU lecture slides](https://sfu-db.github.io/dbsystems/Lectures/OLTP_Through_the_Looking_Glass_and_What_We_Found_There.pdf)
- **Anti-caching (DeBrabant, Pavlo, Tu, Stonebraker, Zdonik; PVLDB 6(14), 2013):**
  - It inverts the hierarchy: memory is primary storage, and the coldest tuples are evicted to disk in blocks by the DBMS, not the OS. Indexes for evicted tuples stay in memory.
  - The abstract reports up to 9x better performance than the alternatives for data 8x larger than memory on high-skew workloads.
  - Pavlo's talk gives 4x when data fits in memory and up to 10x at 2x memory. These figures differ by source.

  (search summary) — [Anti-caching paper](https://hstore.cs.brown.edu/papers/hstore-anticaching.pdf); [Pavlo IPP talk](https://cs.brown.edu/about/partners/symposia/ipp45/pavlo/)
- **Persistent memory's fall:**
  - Intel confirmed the end of Optane (3D XPoint) on its Q2 2022 call and took a $559M inventory write-off.
  - Optane PMem modules stop shipping Dec 29, 2023. The PMem 100 series reaches end of interactive support on June 30, 2025.
  - Newer Xeons dropped support, and commentators point to CXL-attached memory as the successor.

  (search summary) — [The Register, July 2022](https://www.theregister.com/2022/07/29/intel_optane_memory_dead/); [Tom's Hardware](https://www.tomshardware.com/news/intel-kills-optane-memory-business-for-good); [Datacenter Dynamics](https://www.datacenterdynamics.com/en/news/intel-kills-off-optane-memory-writes-off-559-million-inventory)
- **NVMe changes the assumptions (Haas and Leis, "What Modern NVMe Storage Can Do, And How To Exploit It", PVLDB 16(9), 2023):**
  - One PCIe 4.0 x4 SSD can exceed 1M random IOPS and 7 GB/s, and several in one server exceed 10M IOPS.
  - The test machine had a 64-core Zen 4 and 8x Samsung PM1733, reaching 8.9M IOPS at 10% writes and 7.0M at 25% writes.
  - Their engine (LeanStore) exceeds 1M TPC-C transactions/s with data 10x larger than memory.

  (search summary) — [Haas and Leis, VLDB 2023](https://vldb.org/pvldb/vol16/p2090-haas.pdf)
- Measured gap for OS-managed paging: mmap is 2-20x worse than direct I/O once eviction starts; fio with O_DIRECT reached about 900K random reads/s on one PM1733. (prior round) — [CIDR 2022 mmap paper](https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf)
- HyPer, a main-memory system, reached 169,491 TPC-C tps single-threaded with LLVM-compiled transactions (12 warehouses, no client wait). — [Neumann, PVLDB 4(9), 2011](https://www.vldb.org/pvldb/vol4/p539-neumann.pdf)

### Inferences

**Concept ladder**
1. *Disk engine with a big cache.* The data sits in memory but you still pay the buffer-pool indirection, latches, the lock manager and log assembly: about 35%, 14%, 16% and 12% of instructions in Shore.
2. *Pure in-memory engine* (H-Store/VoltDB style: partitioned, single-threaded, no buffer pool). Gets about 20x. Breaks: data larger than RAM, and durability still needs a log or replication.
3. *Anti-caching.* Evicts cold tuples while keeping memory primary. Breaks on scans of cold data, and indexes still sit in RAM.
4. *Persistent memory.* Byte-addressable durability seemed to dissolve the problem. Optane's 2022 end left CXL as a speculative successor.
5. *NVMe-era buffer managers* (LeanStore, Umbra): treat SSD as fast, highly parallel storage, about 1M IOPS per device and 10M+ per server, and keep a pointer-swizzling buffer pool. These reach in-memory speeds for hot data without RAM-sized datasets.

**Misconceptions**
- "In-memory means faster because there's no disk." Wrong per DDIA and Harizopoulos; the overhead is architectural.
- "In-memory means not durable." VoltDB and RAMCloud log to disk or replicate, while Redis's default async persistence is weak.
- "Persistent memory is the future of databases." It was announced, adopted by some, and discontinued in 2022.
- "SSDs are just faster disks." They need deep queue depth (100+ outstanding I/Os) to reach rated IOPS, which is why PG 18 AIO and io_uring matter.

### Gaps
- The exact label-to-percentage pairing in Harizopoulos Figure 1 was reconstructed from extracted text order plus slides. The 16.2% (hand-coded optimizations, mostly B-tree) and 6.8% (residual) assignments should be confirmed visually in the PDF.
- The anti-caching abstract's exact wording and the TPC-C/YCSB numbers came from a search summary; the PDF was not opened.
- Haas and Leis's exact per-configuration IOPS tables were not read; figures come from a search summary.
- Current in-memory product versions (VoltDB is now Volt Active Data, SingleStore, TimesTen) and whether Volt Active Data is still marketed were not checked.
- No source on CXL memory adoption by databases in 2025-2026 was found.

---

## Q5. Column storage and query execution: Parquet, ORC, Arrow; compression; sort order and zone maps; vectorized vs compiled execution (MonetDB/X100, HyPer, DuckDB, Velox, DataFusion); query optimization and cardinality errors

### Takeaway
Analytics reads a few columns of many rows, so the layout flips to columns. Sorting and lightweight encodings (dictionary, RLE, bit-packing, bitmaps) then make the data small and skippable via min/max zone maps. Once I/O shrinks, the CPU becomes the bottleneck. MonetDB/X100 showed that tuple-at-a-time interpretation spends under 10% of time on real work (MySQL TPC-H Q1: 26.6 s vs X100 0.50 s). The two fixes, vectorization (batches of about 1,000 values) and compilation (HyPer/LLVM, 2-4x over vectorized engines in 2011), end up close in performance. Optimizers fail mostly on cardinality estimates, not cost models (Leis et al. 2015).

### Cited Findings

**DDIA 2e framing**
- Fact tables are often over 100 columns wide, but queries touch 4-5. Row storage forces loading and parsing every column of each matching row. Column storage keeps all columns in the same row order, so the k-th entries of each column reassemble the k-th row. — DDIA 2e printed pp. 136-138 / PDF pp. 160-162
- In practice tables are split into blocks of thousands to millions of rows, often by timestamp range, with each column stored separately inside a block. Column storage is used by Snowflake, DuckDB, Pinot, Druid, Parquet, ORC, Lance, Nimble, Arrow, Pandas/NumPy, InfluxDB IOx and TimescaleDB. — DDIA 2e printed p. 138 / PDF p. 162
- Bitmap encoding: one bitmap per distinct value (DDIA's example is 100,000 products among billions of sales). Sparse bitmaps are run-length encoded, and roaring bitmaps switch representation adaptively. `IN` becomes OR and multi-column predicates become AND. — DDIA 2e printed pp. 139-140 / PDF pp. 163-164
- DDIA warns that wide-column stores (Bigtable, HBase, Accumulo) are row-oriented despite the name. — DDIA 2e printed p. 140 / PDF p. 164
- Sort order: rows must be sorted whole, by admin-chosen keys (date first, for example). The first sort key compresses to a few KB via RLE even across billions of rows, and later keys compress less. — DDIA 2e printed pp. 140-141 / PDF pp. 164-165
- Writes: a row in the middle of a sorted, compressed column store forces a rewrite of everything after it. So writes go to an in-memory row store and are merged into new immutable column files in bulk (Snowflake, Vertica, Pinot, Druid). This is the LSM pattern again. — DDIA 2e printed p. 141 / PDF p. 165
- Query execution: interpreting the plan per row is too slow. The two alternatives are compilation (generate code and JIT it via LLVM, like the JVM) and vectorization (prebuilt operators over batches, for example equality producing a bitmap and then a bitwise AND). Both win through sequential memory access, tight loops without function calls or branch mispredictions, SIMD and multithreading, and operating on compressed data. DDIA cites Kersten et al. 2018 as ref [77]. — DDIA 2e printed pp. 142-143 / PDF pp. 166-167
- HTAP products (SQL Server, SAP HANA, SingleStore) are increasingly two engines behind one SQL interface. — DDIA 2e printed p. 135 / PDF p. 159

**Formats**
- Parquet layout (prior round):
  - The file starts with "PAR1" and ends with the footer metadata, a 4-byte length and "PAR1". The footer is written last for single-pass writing.
  - Row groups contain one column chunk per column, and chunks contain pages.
  - The spec recommends 512 MB-1 GB row groups and 8 KB pages.

  — [Parquet file format](https://parquet.apache.org/docs/file-format/); [Parquet configurations](https://parquet.apache.org/docs/file-format/configurations/)
- Parquet encodings:
  - PLAIN is always supported and is the fallback.
  - RLE_DICTIONARY uses a per-chunk dictionary page plus RLE/bit-packed indices, and falls back to PLAIN if the dictionary grows too large.
  - The RLE/bit-packing hybrid covers levels, dictionary indices and booleans.
  - DELTA_BINARY_PACKED handles slowly changing integers.
  - DELTA_LENGTH_BYTE_ARRAY is always preferred over PLAIN for byte arrays.
  - DELTA_BYTE_ARRAY uses prefix (front) compression.
  - BYTE_STREAM_SPLIT does no compression itself but helps a codec on floats and ints.
  - PLAIN_DICTIONARY and BIT_PACKED are deprecated.

  — [Parquet encodings](https://parquet.apache.org/docs/file-format/data-pages/encodings/)
- Pavlo found 94% of Parquet files in the wild use only v1 (2013) features. New open columnar formats appeared in 2025: FastLanes, F3, Vortex (donated to the Linux Foundation), AnyBlox (VLDB 2025 best paper) and Amudai. (prior round) — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)
- Apache Arrow releases: 26.0.1 (3 Nov 2026), 26.0.0 (9 Oct 2026), 25.0.1 (10 Aug 2026), 25.0.0 (10 Jul 2026), 24.0.0 (21 Apr 2026). — [Apache Arrow releases](https://arrow.apache.org/release/)
- Iceberg data files may be Parquet, Avro or ORC. Iceberg 1.12.0 shipped 29 Sep 2026. (prior round) — [Iceberg spec](https://iceberg.apache.org/spec/)
- DuckDB v2.0.0 was released 2026-10-21. It adds async I/O for Parquet/CSV reads aimed at object storage, end-to-end VARIANT shredding and the Quack client-server protocol. **Breaking:** 2.0 database files are unreadable by older versions. DuckDB describes itself as a "columnar-vectorized" engine. (prior round) — [DuckDB releases](https://github.com/duckdb/duckdb/releases); [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200); [Why DuckDB](https://duckdb.org/why_duckdb)

**Vectorized execution: MonetDB/X100 (Boncz, Zukowski, Nes, CIDR 2005)**
- On TPC-H 100 GB, X100's raw execution power is "between one and two orders of magnitude higher than previous technology". — [MonetDB/X100 paper](https://www.cidrdb.org/cidr2005/papers/P19.pdf)
- TPC-H Q1 at SF=1, in (sec × #CPU)/SF, on AthlonMP 1533 MHz: DBMS "X" 28.1, MySQL 4.1 26.6, MonetDB/MIL 3.7, X100 0.50, hand-coded 0.22. On Itanium2: MIL 3.4, X100 0.31, hand-coded 0.14. — [MonetDB/X100 paper](https://www.cidrdb.org/cidr2005/papers/P19.pdf)
- MySQL's gprof trace of Q1: the actual arithmetic (+, −, ×, SUM, AVG) takes under 10% of the time, at an IPC around 0.7. One addition costs about 49 cycles because each call computes a single value, which blocks loop pipelining. — [MonetDB/X100 paper](https://www.cidrdb.org/cidr2005/papers/P19.pdf)
- X100's default vector size is 1,024. For Q1, about 1,000 was optimal, and 128-8K all worked well. A vector size of 1 suffers MySQL-like interpretation overhead. Beyond about 8K the roughly 40-byte-wide Q1 vectors overflow the 320 KB L1+L2 cache. At 4M tuples X100 behaves like full materialization (MonetDB/MIL). — [MonetDB/X100 paper](https://www.cidrdb.org/cidr2005/papers/P19.pdf)
- The MonetDB/X100 work became VectorWise. — [Neumann 2011](https://www.vldb.org/pvldb/vol4/p539-neumann.pdf)

**Compiled execution: HyPer (Neumann, PVLDB 4(9), 2011)**
- The iterator (Volcano) model has poor locality and frequent branch mispredictions. HyPer compiles queries data-centrically into LLVM IR, keeping tuples in registers within pipelines up to pipeline breakers. LLVM compiles in milliseconds where C++ needs seconds. — [Neumann 2011](https://www.vldb.org/pvldb/vol4/p539-neumann.pdf)
- TPC-CH, 12 warehouses, single-threaded, warm:
  - Q1: HyPer+LLVM 35 ms, HyPer+C++ 142 ms, VectorWise 98 ms, MonetDB 72 ms, DB X 4,221 ms.
  - Q5: LLVM 1,105 ms, VectorWise 1,107 ms, MonetDB 12,028 ms.
  - Compile time: LLVM 16-41 ms vs C++ 1,556-2,592 ms per query.
  - TPC-C: 169,491 tps with LLVM vs 161,794 with C++, and 0.81 s vs 16.53 s total compile.
  - The paper sums this up as "frequently another factor 2-4 faster" than the other fast systems.

  — [Neumann 2011](https://www.vldb.org/pvldb/vol4/p539-neumann.pdf)

**Vectorized vs compiled, head-to-head**
- Kersten, Leis, Kemper, Neumann, Pavlo, Boncz, PVLDB 11(13), 2018: Typer (compiled, push-based) vs Tectorwise (vectorized primitives). Typer executes fewer instructions and wins on computation-heavy queries. Tectorwise has higher IPC and hides cache misses better. Both are efficient and close, because most OLAP queries are memory-bound. Tectorwise pays to materialize intermediates. (search summary; secondary) — [dblp record](https://dblp.org/rec/journals/pvldb/KerstenLKNPB18); [summary](https://dirtysalt.github.io/html/compiled-and-vectorized-query-comparison.html)
- PG 19 turns JIT off by default. **Changed:** PostgreSQL's LLVM JIT (added in PG 11, believed on by default from PG 12; the version history is unverified) had been on by default. (prior round) — [PG 19 Beta 1](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)

**Modern engines**
- Velox (Pedreira et al., PVLDB 15(12), 2022) is Meta's reusable C++ execution library, integrated into more than a dozen Meta systems.
  - Prestissimo replaces Presto's Java workers. Meta reports close to 10x speedups on some CPU-bound TPC-H queries.
  - Gluten runs Spark SQL on Velox via JNI, Arrow and Substrait.
  - Press reports 2x-8x wall-clock and 2x-6x CPU reductions.

  (search summary) — [Velox paper](https://www.vldb.org/pvldb/vol15/p3372-pedreira.pdf); [Meta Engineering, 2023](https://engineering.fb.com/2023/03/09/open-source/velox-open-source-execution-engine/); [BigDataWire](https://bigdatawire.com/2022/08/31/new-c-acceleration-library-velox-juices-code-execution-up-to-8x)
- DataFusion is named by DDIA 2e as a standalone query engine in the unbundled warehouse. DDIA's split is query engine (Trino, DataFusion, Presto), storage format, table format and catalog. — DDIA 2e printed pp. 135-136 / PDF pp. 159-160
- DataFusion 53.1.0 was on ClickBench by May 2026, and a GitHub issue refers to 54.0.0 (Apr-May 2026). The current version as of Nov 2026 is unconfirmed. InfluxDB 3 is built on Arrow, DataFusion and Parquet. (search summary) — [ClickBench PR](https://github.com/ClickHouse/ClickBench/pull/840/commits); [DataFusion issue](https://github.com/apache/datafusion/issues/21505); [InfluxData blog](https://www.influxdata.com/blog/datafusion-2025-influxdb/)
- Spark's JVM engine is being supplemented by native vectorized engines (Gluten+Velox, DataFusion Comet, Databricks Photon). (prior round, inference) — `big_data.md` prior notes

**Query optimization**
- Leis et al., "How Good Are Query Optimizers, Really?" (PVLDB 9(3), 2015):
  - The Join Order Benchmark uses IMDB (21 tables, 3.6 GB) with 113 queries of 3-16 joins (average 8).
  - All estimators "routinely produce large errors", and the cost model matters much less than cardinality estimates.
  - Exhaustive join enumeration still helps.
  - TPC-H's uniformity makes PostgreSQL's estimator look unrealistically good.

  (prior round) — [Leis et al. 2015](https://www.vldb.org/pvldb/vol9/p204-leis.pdf)
- PG 18 removes redundant self-joins. PG 19 adds `pg_plan_advice` and `pg_stash_advice` to stabilize planner decisions, plus eager aggregation and more anti-join optimizations. (prior round) — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html); [PG 19 Beta 1](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)

### Inferences

**Concept ladder**
1. *Row store for analytics.* Breaks: reads all 100+ columns to use 4. Fix: column-per-file layout (DDIA p. 137).
2. *Naive column files.* Break: inserts and row reconstruction. Fixes: row groups or blocks of about 10^5-10^6 rows, and an in-memory row buffer merged in bulk (an LSM again).
3. *Uncompressed columns.* Break: I/O-bound scans. Fixes: dictionary + RLE + bit-packing, delta encodings, bitmaps, and a general codec on top (zstd/snappy). Sorting first makes RLE devastatingly effective on the first sort key.
4. *Scan everything.* Breaks: selective queries. Fixes: zone maps (min/max per block: Parquet row-group stats, Redshift 1 MB block metadata, Snowflake micro-partition ranges). These help only if data is clustered on the filter column. Random order makes min/max useless.
5. *Volcano iterator per tuple.* Breaks: once data is in memory, more than 90% of time is overhead (MySQL Q1, IPC 0.7). Fixes:
   - Vectorization: X100 and DuckDB, about 1K-value batches that fit the L1/L2 cache. Too small brings interpretation back; too large spills the cache.
   - Compilation: HyPer and Umbra, data-centric LLVM. Compile time becomes the new cost, which is why PG 19 turns its JIT off by default.
6. *Cost-based optimizer.* Breaks: correlated predicates and multi-join cardinality errors. Fixes: extended statistics, adaptive execution and plan hints/advice (`pg_plan_advice`).

**Misconceptions**
- "Columnar means compressed means slow to update." Updates go to a delta store and merge later.
- "Column-family (Cassandra/HBase) = columnar." It does not (DDIA p. 140).
- "Vectorized means SIMD." The batch amortizes interpretation overhead even without SIMD. Kersten et al. found SIMD gains limited because most OLAP is memory-bound.
- "Compiled always beats vectorized." Close in practice. Compiled wins on compute-heavy queries, vectorized on memory-bound ones, and compilation latency matters for short queries.
- "The optimizer picks the best plan." Cardinality estimates are often wrong by orders of magnitude on real data (JOB).
- "Parquet is a fixed format." 94% of files use 2013 features, newer encodings exist, and new formats (Vortex, FastLanes) are competing.

### Gaps
- No ORC spec or current ORC release (Apache ORC 2.x?) was fetched; ORC stripe/index-stride details (e.g., 10,000-row index strides) are unverified.
- Parquet page index (column index and offset index) and Parquet Bloom filters were not fetched.
- The DuckDB papers (CIDR 2020 "Data Management for Data Science", SIGMOD 2019 demo) and DuckDB's vector size (believed 2,048) and morsel-driven parallelism were not fetched.
- The Kersten et al. full text was not read, so its per-query numbers are missing.
- Velox's own benchmark tables were not read.
- The latest DataFusion release (Nov 2026) is unconfirmed; candidates are 5x.
- Umbra and adaptive compilation (Kohn, Leis, Neumann 2018) were not covered.
- The Volcano paper (Graefe 1994) was not fetched.
- The Leis et al. 2015 numeric error distributions (for example, the fraction of estimates off by 10x or more) were not recorded in the prior round.

---

## Q6. Materialized views, data cubes and incremental view maintenance (pg_ivm, Materialize, RisingWave, Snowflake dynamic tables, Databricks materialized views)

### Takeaway
A materialized view is a cached query result, the read-side mirror of an index: faster reads, more write work. A data cube precomputes aggregates along dimensions and loses flexibility for questions on non-dimension attributes. The hard part is keeping views fresh. Plain `REFRESH MATERIALIZED VIEW` recomputes everything. IVM computes only deltas: pg_ivm 1.15 (Jul 2026) inside PostgreSQL, streaming databases (Materialize, RisingWave, Feldera), Snowflake dynamic tables (INCREMENTAL/FULL/AUTO) and Databricks materialized views (Enzyme, serverless only). Each falls back to full recompute for operators it cannot incrementalize.

### Cited Findings
- DDIA 2e defines a materialized view as a stored copy of query results; a virtual view is just expanded at query time. Maintaining one costs write work and pays off for repeated queries. DDIA names Materialize as a specialist. — DDIA 2e printed pp. 143-144 / PDF pp. 167-168
- A data cube (OLAP cube) is a grid of aggregates, for example SUM(net_price) by date × product, which can be summed further along any axis. In a 5-dimension star schema, each cell is one date-product-store-promotion-customer combination. A cube answers "sales per store yesterday" instantly but cannot answer "share of sales from items over $100", because price is not a dimension. So warehouses keep raw data and use cubes only as accelerators. — DDIA 2e printed pp. 144-145 / PDF pp. 168-169
- DDIA chapter 12 says databases usually refresh views by batch or on demand (PostgreSQL's `REFRESH MATERIALIZED VIEW`). That wastes work, because all data is reprocessed, and makes views stale until the next refresh. Triggers work only for naturally incremental cases like per-day revenue. IVM converts queries into incremental operators. DDIA lists Materialize, RisingWave, ClickHouse and Feldera, which buffer recent events in memory, periodically fold them into on-disk views and merge both at read time. — DDIA 2e printed pp. 516-517 / PDF pp. 540-541
- pg_ivm 1.15 (announced 6 July 2026) adds IMMV metadata restore across pg_dump and pg_upgrade (the `pg_ivm_dump_metadata` utility and the `restore_immv()` function). It also fixes multi-modification-by-trigger maintenance and an outer-join segfault introduced in 1.14 (1 April 2026). PGDG packages exist for PG 18, and a third-party page says the README lists compatibility with PG 13-18. (search summary) — [pg_ivm 1.15 announcement](https://www.postgresql.org/about/news/pg_ivm-115-released-3338/); [pg_ivm 1.14 announcement](https://www.postgresql.org/about/news/pg_ivm-114-released-3265); [Pigsty pg_ivm page](https://doc.pigsty.io/ext/e/pg_ivm)
- Snowflake dynamic tables:
  - Refresh mode is fixed at creation; changing it needs CREATE OR REPLACE/ALTER.
  - AUTO (the default) resolves once to INCREMENTAL or FULL and is never re-evaluated, so Snowflake advises setting it explicitly in production.
  - INCREMENTAL merges only changes since the last refresh. FULL re-runs the query. The fetched page also lists ADAPTIVE: incremental by default, but reinitializing when incremental would cost more.
  - INTERSECT/EXCEPT and exact percentile functions block incremental refresh, and EXCEPT fails at compile time in incremental mode.

  — [Snowflake dynamic table refresh](https://docs.snowflake.com/en/user-guide/dynamic-tables-refresh)
- Databricks materialized views:
  - The Enzyme engine chooses between incremental refresh and full recompute.
  - Incremental refresh requires serverless compute, either a SQL warehouse or serverless Lakeflow Spark Declarative Pipelines. Non-serverless views always fully refresh.
  - Supported: GROUP BY, CTEs, UNION ALL, WHERE/HAVING, inner/left/right/full outer joins, deterministic functions and immutable UDFs. Some operations need row tracking.
  - Unsupported expressions trigger a full refresh. Docs conflict on non-deterministic time functions (the newer GCP page allows `current_date()`/`current_timestamp()`/`now()` in WHERE).
  - Marked Public Preview on GCP.

  (search summary) — [Databricks incremental refresh](https://docs.databricks.com/aws/optimizations/incremental-refresh); [Databricks blog](https://www.databricks.com/blog/optimizing-materialized-views-recomputes)
- RisingWave says it maintains every materialized view incrementally by default, uses barrier-based checkpoints for consistent snapshots, and is Apache 2.0 licensed. These are vendor claims. A third-party page says Materialize is built on Timely and Differential Dataflow. (search summary) — [RisingWave docs](https://docs.risingwave.com/reference/what-is-materialized-view); [RisingWave vs Materialize (vendor)](https://risingwave.com/blog/risingwave-vs-materialize-comparison/)

### Inferences

**Concept ladder**
1. *Re-run the query each time.* Breaks on repeated heavy aggregations.
2. *Materialized view with full refresh.* Breaks: cost proportional to all data and stale results between refreshes.
3. *Triggers.* Work for SUM/COUNT by key. Break for joins, DISTINCT, MIN/MAX under deletes and percentiles.
4. *IVM.* Each operator gets a delta rule: joins need deltas from both sides, MIN/MAX under deletes needs retained state, and percentiles and EXCEPT are hard. Snowflake and Databricks lists show exactly where products give up.
5. *Streaming databases.* Make IVM continuous, with consistency via barriers or timestamps.

The data cube is the extreme of precomputation and should be taught as the inflexibility example.

**Misconceptions**
- "A materialized view is always up to date." Only under IVM, and even then with a lag (Snowflake target lag).
- "Incremental refresh is always cheaper." Snowflake's ADAPTIVE mode exists because large deltas make it costlier than a rebuild.
- "AUTO refresh mode adapts over time." In Snowflake it is decided once at creation.

### Gaps
- Materialize's and RisingWave's current versions and release notes (2026) were not found. Their claims rest on DDIA and vendor blogs.
- Snowflake target-lag semantics were not fetched. The ADAPTIVE mode appeared on the fetched page but was not cross-checked against release notes.
- pg_ivm's supported SQL subset (aggregates, outer joins, DISTINCT, subqueries) and its trigger-based immediate maintenance (an IMMV updated in the same transaction) were not verified from the README.
- The academic IVM lineage (DBToaster, differential dataflow, DBSP/Feldera) was not fetched.

---

## Q7. How cloud data warehouses store and execute (Snowflake micro-partitions, BigQuery Dremel/Capacitor, Redshift)

### Takeaway
All three are column stores on separated storage, applying the Q5 ideas at cloud scale. Snowflake splits tables into immutable-file micro-partitions of 50-500 MB uncompressed with per-column min/max and distinct counts for pruning. BigQuery stores Capacitor-encoded columnar data (Dremel-derived, nested-data aware) on Colossus. Redshift stores 1 MB column blocks with in-memory zone maps that only work well on sorted data. DDIA 2e frames the trend as "unbundling" the warehouse into query engine, file format, table format and catalog.

### Cited Findings
- DDIA 2e on cloud warehouses: BigQuery, Redshift and Snowflake decouple compute from storage on object stores. Open-source warehouses have broken into a query engine (Trino, DataFusion, Presto), a storage format (Parquet, ORC, Lance, Nimble), a table format (Iceberg, Delta) and a catalog (Snowflake's Polaris, Databricks' Unity Catalog, Iceberg REST). — DDIA 2e printed pp. 135-136 / PDF pp. 159-160
- Snowflake:
  - Each micro-partition holds 50-500 MB of uncompressed data, always stored compressed, with columns stored independently.
  - Metadata per partition covers each column's value range and distinct-value count.
  - Pruning example: one year of hourly data, queried for one hour, ideally scans 1/8760 of partitions.
  - Clustering depth is the average depth (≥1) of overlapping micro-partitions; lower is better, and an empty table is 0. A "constant" state means no overlap.
  - Some DML is metadata-only (delete-all), and dropping a column does not rewrite partitions.

  — [Snowflake micro-partitions](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions)
- DDIA 2e says Snowflake (with Vertica, Pinot and Druid) buffers writes and merges them into new column files in bulk. — DDIA 2e printed p. 141 / PDF p. 165
- BigQuery:
  - Capacitor (announced April 2016, by Mosha Pasumansky) builds on the 2010 Dremel paper's techniques for nested and repeated fields in a column store.
  - It replaced ColumnIO (which Parquet and ORC are derived from) and can operate on compressed data. Third-party accounts say data is written to Colossus.
  - Capacitor keeps rich metadata that Dremel uses for I/O and parallelization decisions.

  (search summary) — [Google Cloud: Inside Capacitor](https://cloud.google.com/blog/products/bigquery/inside-capacitor-bigquerys-next-generation-columnar-storage-format); [Google Cloud: separation of storage and compute in BigQuery](https://cloud.google.com/blog/products/bigquery/separation-of-storage-and-compute-in-bigquery)
- DDIA 2e: Parquet supports a document model derived from Dremel by "shredding" or striping. — DDIA 2e printed p. 137 / PDF p. 161
- Redshift:
  - Columnar data lives in 1 MB blocks, and each block's min/max is kept as zone maps, cached in memory, so irrelevant blocks are skipped.
  - Sort keys make zone maps effective. Zone maps store only the first 8 bytes of sort-key values, so long strings with common prefixes prune poorly.
  - RA3 separates compute and managed storage. The detail that hot blocks sit on NVMe and cold ones on S3 came only from a study guide and is unverified.

  (search summary) — [AWS Redshift sort keys](https://docs.aws.eu/redshift/latest/dg/t_Sorting_data.html); [AWS News Blog: interleaved sorting](https://aws.amazon.com/blogs/aws/quickly-filter-data-in-amazon-redshift-using-interleaved-sorting)
- Pavlo's 2025 events: Databricks acquired Neon (about $1B, rebranded Lakebase) and Snowflake acquired CrunchyData (about $250M). Both warehouse vendors now own Postgres OLTP. (prior round) — [Pavlo, Databases in 2025](https://www.cs.cmu.edu/~pavlo/blog/2026/01/2025-databases-retrospective.html)

### Inferences
- All three are Q5's zone maps plus columnar plus compression, scaled out. They differ in who controls the sort order:
  - Snowflake: insertion order plus optional automatic clustering, with clustering depth as the health metric.
  - Redshift: explicit sort keys.
  - BigQuery: partitioning and clustering columns. BigQuery was not fetched, so this is unverified.
- Teach the 1/8760 pruning example next to Redshift's 8-byte string caveat. Pruning is only as good as the physical order and the metadata.
- Storage is immutable files and DML rewrites partitions. The Snowflake page does not state this outright (a gap below), but DDIA's description of bulk merging into new column files is consistent with it.
- Misconception: "Serverless warehouses don't need physical design." Clustering depth, sort keys and partitioning still decide bytes scanned and cost.

### Gaps
- Snowflake's "immutable micro-partitions rewritten on DML" is not stated on the fetched page, and the Snowflake SIGMOD 2016 paper was not fetched.
- BigQuery partitioning and clustering limits and current Capacitor details (anything after 2016) were not found. The Dremel paper (VLDB 2010) and "Dremel: A Decade of Interactive SQL Analysis at Web Scale" (VLDB 2020) were not fetched.
- Redshift RA3 managed-storage internals, AQUA status and Redshift's own execution engine (code generation and compilation to C++, believed) were not verified.
- No 2026 product-version facts (for example, the Snowflake Iceberg tables GA timeline) were gathered.

---

## Q8. Hands-on lab ideas (Kotlin on JVM 21+, Gradle, Testcontainers, Docker Compose, or pure-Kotlin simulation)

### Takeaway
Each concept above has a laptop-scale lab that yields a number or reproduces an anomaly:
- write, read and space amplification from a Kotlin LSM vs the UCS and RocksDB formulas;
- Bloom false-positive rate vs bits/key (expect about 1% at 10 bits);
- index-only scans that stop touching the heap after VACUUM;
- HNSW recall vs `ef_search`;
- vectorized vs tuple-at-a-time ns/tuple vs batch size (expect a U-curve, best between 128 and 8K);
- PG 18 `io_method` comparisons.

io_uring is blocked by Docker's default seccomp profile, so laptop Postgres labs will use `worker`.

### Cited Findings (facts the labs rely on)
- Bitcask record format and keydir; merge plus hint files; the keydir must fit RAM. — [Bitcask paper](https://riak.com/assets/bitcask-intro.pdf)
- Bloom: 10 bits/key ≈ 1% FP, 10x better per extra 5 bits (DDIA p. 123); RocksDB measured 9.9 bits for 1%, 4.9 for 10%, 15.5 for 0.1%. — DDIA 2e PDF p. 147; [RocksDB Bloom Filter](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter)
- UCS amplification relationships and the W parameterization. — [Cassandra UCS](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/ucs.html)
- RocksDB leveled write amplification "often larger than 10". — [RocksDB Leveled Compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction)
- DDIA's warning that LSM write benchmarks must run long enough for compaction to compete. — DDIA 2e printed p. 131 / PDF p. 155
- `full_page_writes` writes the whole page on its first modification after a checkpoint; `wal_compression` options. — [PG 18 WAL config](https://www.postgresql.org/docs/18/runtime-config-wal.html)
- Index-only scans depend on the visibility map. `INCLUDE` example. — [PG 18 index-only scans](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- pgvector defaults (`ef_search` 40), the recall measurement method, and the 10%-filter → about 4 rows caveat. Docker image `pgvector/pgvector` (pg13-pg18 tags, prior round). — [pgvector](https://github.com/pgvector/pgvector)
- X100 vector-size curve (1 is bad, about 1,000 optimal, 128-8K fine, beyond cache degrades). — [MonetDB/X100](https://www.cidrdb.org/cidr2005/papers/P19.pdf)
- PG 18 `io_method` values and pganalyze's cold-scan timings. — [pganalyze](https://pganalyze.com/blog/postgres-18-async-io)
- Docker 25+ default seccomp blocks io_uring. (prior round) — [Docker seccomp](https://docs.docker.com/engine/security/seccomp/)
- `pageinspect` functions (`bt_page_stats`, `bt_page_items`, `heap_page_items`) and `pg_buffercache`. (prior round) — [pageinspect](https://www.postgresql.org/docs/current/pageinspect.html); [pg_buffercache](https://www.postgresql.org/docs/current/pgbuffercache.html)
- Leis JOB: estimated vs actual rows on correlated data. (prior round) — [Leis et al. 2015](https://www.vldb.org/pvldb/vol9/p204-leis.pdf)

### Inferences (lab catalogue; author designs, untested)

**L1. Bitcask in Kotlin (pure Kotlin; JUnit 5 `@TempDir`)**
- Build: an append-only `FileChannel` log with a CRC32C per record, an in-memory `HashMap<ByteArray-key, Location>`, a tombstone for delete, segment rollover at N MB, `merge()`, and hint files.
- Measure:
  - (a) writes/s with `force(false)` after every put vs every 1,000 puts. This shows fsync cost and motivates group commit.
  - (b) restart time with and without hint files at 1M keys.
  - (c) space amplification (bytes on disk / live bytes) before and after merge under a 90%-overwrite workload.
- Anomaly: truncate the last record and confirm the CRC check skips the torn tail.

**L2. LSM in Kotlin with measured amplification (pure Kotlin)**
- Build: a `java.util.concurrent.ConcurrentSkipListMap` memtable plus WAL; SSTables with 4 KB blocks, a sparse index and a Bloom filter; pluggable compaction (size-tiered T=4 vs leveled fanout 10).
- Instrument every byte written to disk and every SSTable probed.
- Measure:
  - write amplification = disk bytes written / user bytes;
  - read amplification = SSTables or blocks touched per get, for both hit and miss keys;
  - space amplification = disk bytes / live bytes.
- Compare against UCS's predictions (leveled write amplification ∝ (f−1)×levels; tiered read amplification ∝ (f−1)×levels).
- Sub-lab: plot Bloom FP rate vs bits/key (expect about 1% at 10 bits/key).
- Anomaly: run 30 s vs 10 min. Write throughput drops once compaction starts (DDIA p. 131's warning).

**L3. B-tree vs LSM on the same workload (Testcontainers or in-process)**
- Option A (in-process, no Docker): RocksDB via `rocksdbjni` vs SQLite (B-tree) via `sqlite-jdbc` or H2's MVStore. Run the same 10M random-key and 10M sequential-key inserts plus a point-read phase. Measure bytes written via RocksDB statistics plus OS counters, file size and p99 latency.
- Option B (Testcontainers): PostgreSQL 18 vs Cassandra 5.0.9. Report `pg_stat_wal` and relation sizes vs `nodetool tablestats`.
- Expected shape from MyRocks and Callaghan: the LSM writes fewer bytes per insert and uses less space, the B-tree has more predictable reads. Random keys widen the gap, sequential keys narrow it.
- Teaching point: no universal winner (RUM).

**L4. Page splits and fillfactor in PostgreSQL (Testcontainers `postgres:18`)**
- Use pageinspect: `bt_metap`, `bt_page_stats`.
- Insert monotonically increasing keys vs random UUIDv4 vs `uuidv7()` (new in PG 18). Count leaf pages and average free space.
- Expect random UUIDv4 to give many half-full pages and v7 to pack tightly.
- Repeat with `WITH (fillfactor = 70)` and a dedup-heavy column (`deduplicate_items` on vs off) and compare index size.

**L5. WAL, checkpoints and torn-page defence (PostgreSQL 18)**
- Measure WAL bytes and full-page images per 100K updates right after `CHECKPOINT` vs mid-interval, with `full_page_writes` on/off and `wal_compression` = off/lz4/zstd.
- Crash test: `docker kill -s KILL` mid-load, restart and time recovery as `max_wal_size` and `checkpoint_timeout` vary.
- Verify the `pg_stat_wal` columns first (gap in Q2).

**L6. PG 18 asynchronous I/O**
- Cold sequential scan of a roughly 4 GB table with `io_method` = sync vs worker, restarting and dropping caches between runs.
- Optional `io_uring` run with seccomp unconfined in a Linux VM.
- Compare with pganalyze's 15.1 s / 10.1 s / 5.7 s shape; on a laptop NVMe the gaps may differ.

**L7. Index-only scans, covering and partial indexes (PostgreSQL 18)**
- `CREATE INDEX ... (x) INCLUDE (y)`, then `EXPLAIN (ANALYZE, BUFFERS)`. Watch `Heap Fetches` before VACUUM (≈ rows) and after (≈ 0).
- Partial index: show it is used for `WHERE billed IS NOT TRUE` literals but not for a parameterized prepared statement (generic plan).
- PG 18 skip scan: index (x, y) with few distinct x and `WHERE y = const`.

**L8. Tiny inverted index plus BM25 (pure Kotlin), then Lucene**
- Tokenize a corpus (for example, Wikipedia abstracts), build term → sorted docID postings with delta + varint encoding, AND/OR queries by merge, and BM25 scoring.
- Measure postings bytes before and after compression, and query latency.
- Then index the same corpus with Lucene 10 (pure JVM, callable from Kotlin) and log segment counts and merges via `IndexWriter` info stream as documents arrive. This shows the LSM shape of a search engine.

**L9. HNSW from scratch and recall measurement (pure Kotlin + optional pgvector container)**
- Implement HNSW (M = 16, efConstruction = 64, random levels from an exponential distribution) over 100K-1M vectors (SIFT1M or random 128-d).
- Brute-force ground truth. Plot recall@10 vs ef_search ∈ {10, 20, 40, 80, 160} vs median latency and memory.
- Repeat in `pgvector/pgvector:pg18` using `SET hnsw.ef_search` and `enable_indexscan = off` for ground truth.
- Reproduce the filter anomaly: a WHERE that matches 10% returns about 4 of 10 requested rows at ef_search = 40. Then fix it with `hnsw.iterative_scan = relaxed_order`.
- Add binary quantization plus re-rank and measure the recall recovered.

**L10. Column store and zone maps (pure Kotlin + DuckDB JDBC)**
- Write the same 10M-row table as a row file and as column files with dictionary + RLE + bit-packing. Measure bytes and the time to `SUM(col)` with a filter.
- Add 64K-row blocks with min/max. Measure the fraction of blocks skipped for a range predicate on sorted vs shuffled data (expect near-total skipping when sorted, near zero when shuffled).
- Inspect real Parquet row-group stats via DuckDB's `parquet_metadata()` from Kotlin JDBC (DuckDB 2.0).

**L11. Volcano vs vectorized vs "compiled" (pure Kotlin + JMH)**
- Implement a TPC-H Q1-style filter + group-by + SUM three ways:
  - (a) iterator per tuple with virtual `next()` and boxed values;
  - (b) primitives over `LongArray` batches of size B;
  - (c) one fused hand-written loop, standing in for compiled code.
- Plot ns/tuple vs B ∈ {1, 16, 128, 1K, 8K, 64K, 1M}. Expect X100's U-curve (B = 1 slow, about 1K best, degradation once batches exceed L2).
- Caveat: JIT inlining may blur (a) vs (c). Use JMH and megamorphic call sites to keep the comparison honest.

**L12. Cardinality estimation errors (PostgreSQL 18)**
- Build a table with correlated columns (city, zip).
- Compare `EXPLAIN ANALYZE` estimated vs actual rows for `WHERE city = ... AND zip = ...` before and after `CREATE STATISTICS (dependencies)`.
- Show a join-order flip that follows from the estimate (JOB's lesson). Optional: the PG 19 `pg_plan_advice` once GA.

**L13. Incremental view maintenance (pure Kotlin simulation; optional pg_ivm image)**
- Maintain `SUM(amount) GROUP BY day` and a two-table join view under inserts, updates and deletes using delta rules.
- Measure refresh cost vs delta size against full recompute and find the crossover (motivates Snowflake's ADAPTIVE).
- Show why `MIN` under delete needs extra state.

**L14. "Looking Glass" in miniature (pure Kotlin + JMH)**
- Implement a key-value "transaction" against `HashMap`. Then add, one at a time: a buffer-pool indirection (page table + pin/unpin), a `ReentrantReadWriteLock` latch per page, a lock-manager `ConcurrentHashMap` acquisition, and WAL record assembly.
- Measure ns/op after each step and compare the shares with Harizopoulos's 35/14/16/12%.

### Gaps
- None of these labs has been built or timed. All expected numbers are predictions from the cited sources, not measurements on a laptop.
- `rocksdbjni` and `sqlite-jdbc` current versions, and Apple Silicon support for `rocksdbjni`, were not checked. Testcontainers module names for Cassandra and pgvector were not re-verified.
- The pg_ivm Docker image availability was not checked; the lab may need a custom Dockerfile with `postgresql-18-pg-ivm` from PGDG.
- The SIFT1M dataset licence and download size were not checked.
