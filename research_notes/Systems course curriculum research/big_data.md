# Big Data track: Hadoop/Hive heritage, Spark, lakehouse formats, and the 2026 state of the art

Research date: 2026-11-07. Audience: senior Java/Kotlin backend engineer, self-paced, laptop labs (Apple Silicon Mac).
Convention: "Cited Findings" contain only facts confirmed on a fetched page (or, where marked, a search result). Textbook knowledge I did not re-verify this session is in "Inferences", marked *(standard knowledge, not re-verified)*.

---

## 1. Why distributed data processing exists, and what survives from GFS/HDFS/MapReduce

### Takeaway
Distributed processing exists because one disk/one machine could not scan or store web-scale data in useful time. GFS (2003) and MapReduce (2004) solved this with commodity clusters. HDFS/MapReduce clusters are now history, but the ideas survived: split data into blocks, move compute to data, and the map, shuffle, reduce shape that still sits under every Spark stage boundary. Cloud object storage has replaced HDFS as the default storage layer.

### Cited Findings
- GFS paper: "The Google File System", Ghemawat, Gobioff, Leung, SOSP 2003; a scalable distributed file system for data-intensive applications, fault tolerant on inexpensive commodity hardware; largest cluster then was over a thousand machines and hundreds of TB. — [Google Research](https://research.google/pubs/the-google-file-system/)
- MapReduce paper: Dean and Ghemawat, OSDI 2004, pp. 137-150. Users write a map function (key/value in, intermediate key/values out) and a reduce function that merges all values for the same intermediate key; the runtime handles partitioning, scheduling, machine failures and inter-machine communication. — [Google Research](https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/)
- RDD paper: "Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing", Zaharia et al., NSDI 2012 (Best Paper). RDDs give "a restricted form of shared memory" based on coarse-grained transformations. PDF: usenix.org/system/files/conference/nsdi12/nsdi12-final138.pdf — [USENIX](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)
- Lakehouse paper (CIDR 2021, Armbrust, Ghodsi, Xin, Zaharia): describes the history as (1) warehouses, (2) "data lakes" started with the Apache Hadoop movement using HDFS for cheap storage, schema-on-read; and states that "From 2015 onwards, cloud data lakes, such as S3, ADLS and GCS, started replacing HDFS" due to durability, geo-replication and very low cost. Defines a Lakehouse as (i) open direct-access data formats such as Parquet/ORC, (ii) first-class ML/data-science support, (iii) state-of-the-art performance. — [CIDR 2021 PDF](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- Spark 4.0 removed Mesos support and Hive support prior to 2.0.0. — [Spark 4.0.0 release notes](https://spark.apache.org/releases/spark-release-4-0-0.html)
- The PyPI pyspark default distribution is built against Hadoop 3.5 and Hive 2.3 (i.e. Hadoop survives as client libraries such as the S3A filesystem, not as a cluster you must run). — [PySpark install docs](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
- Spark 4.3 Real-Time Mode is "built on native concurrent stage scheduling and pipelined shuffles, so producer and consumer stages run at the same time" (implying the normal batch model materializes shuffle output between stages, a direct MapReduce inheritance). — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)

### Inferences
- Scan-throughput math for Lesson 1 (illustrative assumptions, not sourced; the writer should present them as round numbers): if one disk/node streams ~500 MB/s, scanning 1 TB takes ~2,000 s (~33 min); 100 nodes in parallel take ~20 s. If the same data is columnar, compressed ~5x, and a query reads 3 of 30 columns, bytes read drop ~50x, so a single machine reads the needed ~20 GB in ~40 s. This frames the course: parallelism and reading fewer bytes are the two levers; formats (Parquet, Iceberg stats) shrink the problem before clusters are needed.
- HDFS details for the history lesson *(standard knowledge, not re-verified)*: files split into large blocks (128 MB default in Hadoop 2+, 64 MB in GFS/Hadoop 1), each block replicated 3x across DataNodes, a single NameNode holds metadata. MapReduce: map tasks scheduled near their block (data locality), map output partitioned by key hash and spilled to local disk, reducers pull ("shuffle") and merge-sort, optional combiner pre-aggregates on the map side. Every intermediate job result was written to HDFS, which is why iterative jobs were slow and why Spark's RDDs (keep working sets in memory, recover by lineage) won.
- What survived into 2026: the shuffle (hash-partition by key, write, fetch) is the Spark `Exchange`; data locality became "partition pruning / predicate pushdown / read fewer bytes" on object storage; the Hive Metastore became the first table catalog and its role continues as Iceberg REST/Polaris/Unity Catalog; Hive-style `key=value/` directory partitioning is still the default for plain Parquet datasets. What did not survive for new work: running HDFS/YARN clusters, writing MapReduce jobs, Hive-on-MR.

### Gaps
- No primary source fetched for HDFS default block size/replication (hadoop.apache.org docs not fetched). Writer should cite the HDFS Architecture guide if quoting numbers.
- GFS 64 MB chunk size not confirmed from the fetched abstract page (it is in the paper body).

---

## 2. Hive, the metastore, and Hive 4.x status

### Takeaway
Hive turned "files in HDFS" into SQL tables via a metastore that maps table names to schemas, file locations and partitions. Hive 1.x-3.x are end-of-life (2024). Hive 4.x is actively maintained (4.2.1, Aug 2026, needs JDK 21), with Docker images including a standalone metastore. Teach Hive as the origin of SQL-on-files, partitions and the metastore; do not teach HiveQL-on-MapReduce as a skill.

### Cited Findings
- Hive releases: 4.2.1 on 24 Aug 2026 (security bugfix release, Hadoop 3.4.1, Tez 0.10.5); 4.2.0 on 23 Nov 2025; 4.1.0 on 31 Jul 2025; 4.0.1 on 2 Oct 2024; 4.0.0 on 29 Mar 2024. — [Hive downloads](https://hive.apache.org/general/downloads/)
- Hive 4.2.x requires JDK 21 as the minimum; 4.1.x added JDK 17 support. — [Hive downloads](https://hive.apache.org/general/downloads/)
- The Hive community voted to end-of-life 1.x (11 Apr 2024), 2.x (20 May 2024) and 3.x (8 Oct 2024): "no further updates or releases will be made for this series." — [Hive downloads](https://hive.apache.org/general/downloads/)
- Docker Hub `apache/hive` has tags `4.2.1` and `standalone-metastore-4.2.1` (both amd64 and arm64, updated 2026-08-21), plus nightly tags; older 3.1.3 is amd64 only. — [Docker Hub API, apache/hive tags](https://hub.docker.com/v2/repositories/apache/hive/tags?page_size=15)
- Spark's own default build still embeds Hive 2.3 client classes. — [PySpark install docs](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
- Iceberg's Spark quickstart config uses `spark.sql.catalog.spark_catalog = org.apache.iceberg.spark.SparkSessionCatalog` with `type = hive`, i.e. the Hive-metastore-backed session catalog is still a supported Iceberg catalog type. — [Iceberg Spark quickstart](https://iceberg.apache.org/spark-quickstart/)

### Inferences
- Concepts to teach from Hive *(standard knowledge)*: schema-on-read; external vs managed tables; partitioned tables as `dt=2026-11-01/` directories; partition pruning; MSCK REPAIR / "the metastore and the filesystem disagree" problem; why listing directories on object storage is slow; why the metastore cannot give atomic multi-file commits. These problems are exactly what Iceberg/Delta/Hudi fix, so Hive is the "before" picture for the lakehouse lessons.
- "Is Hive still used?" Answer for learners: the Hive *engine* (HiveServer2 on Tez) persists mainly in legacy on-prem estates; the Hive *Metastore* (HMS) is still widely deployed as a catalog for Spark, Trino and Iceberg, though new builds favor Iceberg REST catalogs (see section 8). The standalone-metastore Docker image makes HMS easy to demo locally.

### Gaps
- No usage statistics found for Hive engine adoption in 2026; the "legacy estates" claim is an inference.
- Did not verify Hive 4's built-in Iceberg table support from a primary page (it exists in Hive 4.0 per my training data, not re-checked).

---

## 3. Columnar file formats: Parquet, ORC, Avro

### Takeaway
Parquet is the lingua franca: a file is row groups, each with one column chunk per column, each chunk made of pages, and a footer with metadata (offsets, and statistics) written last. Readers fetch the footer first and then only the columns and row groups they need. That is column pruning and predicate pushdown, the biggest single performance lever in the course. ORC is the Hive-era columnar sibling; Avro is the row-oriented format used for streaming/Kafka and inside Iceberg manifests.

### Cited Findings
- Parquet layout: file starts with 4-byte magic "PAR1"; data stored as column chunks; N columns x M row groups means each row group has one chunk per column; file ends with File Metadata, a 4-byte little-endian length, and "PAR1". "File metadata is written after the data to allow for single pass writing"; readers read metadata first to locate needed column chunks. — [Parquet file format](https://parquet.apache.org/docs/file-format/)
- Parquet recommendations: "We recommend large row groups (512MB - 1GB)" because larger column chunks allow larger sequential IO; "We recommend 8KB for page sizes" because pages are indivisible and smaller pages allow finer-grained reads. — [Parquet configurations](https://parquet.apache.org/docs/file-format/configurations/)
- Iceberg data files may be Parquet, Avro or ORC (v1 spec: "large analytic tables built on immutable files in Parquet, Avro, or ORC"). — [Iceberg spec](https://iceberg.apache.org/spec/)
- Spark 4.1 added shredding schema inference in the Parquet writer and read support for the Parquet Variant logical type. — [Spark 4.1.0 release notes](https://spark.apache.org/releases/spark-release-4.1.0.html)
- DuckDB 2.0 performs VARIANT shredding end to end for Parquet reads and writes, and added asynchronous I/O for Parquet/CSV reads aimed at object storage. — [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200)
- Hudi 1.2 added Lance file format support and VECTOR, VARIANT, BLOB types. — [Hudi 1.2 release](https://hudi.apache.org/releases/release-1.2)
- Spark 4.3 can read CSV/JSON/XML/text/Avro/Parquet/ORC from tar and zip archives (opt-in). — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)

### Inferences
- Teach *(standard knowledge)*: encodings (dictionary, RLE/bit-packing, delta), compression codecs (Snappy, Zstd), column-chunk and page min/max/null-count statistics, optional page index and bloom filters; predicate pushdown = skip row groups whose min/max cannot match; column pruning = read only projected column chunks. Show in Spark `explain()` as `PushedFilters: [...]` and `ReadSchema: struct<...>`; in DuckDB with `parquet_metadata('file.parquet')` and `EXPLAIN ANALYZE`.
- Note the gap between the spec's 512 MB-1 GB row group advice and common writer defaults (parquet-java defaults to 128 MB row groups, DuckDB writes ~122,880-row groups) *(not re-verified)*. Good discussion point: sorted data makes min/max stats useful; random order makes them useless.
- Avro: row-oriented, schema travels with the file, good for append-heavy streams and schema evolution in Kafka; Iceberg uses Avro for manifest files (v1-v3) *(standard knowledge)*.
- Emerging: Lance and "Parquet v3/new formats" (Vortex, Nimble) are trends to mention in one line only; not core curriculum.

### Gaps
- Did not fetch the Parquet "Data Pages", "Page Index" or encoding pages; statistics/page-index specifics above are from training knowledge.
- ORC spec not fetched.

---

## 4. Spark core concepts (execution model, shuffle, joins, AQE, caching, streaming)

### Takeaway
Spark = a driver that builds a lazy logical plan, Catalyst that optimizes it, and executors that run tasks; wide transformations (groupBy, join, repartition) insert a shuffle (`Exchange`) that splits the job into stages. Most performance work is about shuffles: their count, partition sizes, skew, and choosing broadcast joins. AQE (on by default since 3.2) fixes much of this at runtime. Structured Streaming runs the same DataFrame plans incrementally, with watermarks bounding state.

### Cited Findings
- AQE is enabled by default since Spark 3.2.0 (`spark.sql.adaptive.enabled=true`). It coalesces post-shuffle partitions (`spark.sql.adaptive.coalescePartitions.enabled=true`, `advisoryPartitionSizeInBytes` default 64 MB), converts sort-merge joins to broadcast hash joins at runtime, converts SMJ to shuffled hash join (`spark.sql.adaptive.convertSortMergeJoinToShuffledHashJoin.enabled`, default true since 4.3.0), and optimizes skew joins (`spark.sql.adaptive.skewJoin.enabled=true`; a partition is skewed if > `skewedPartitionFactor` 5.0 x median AND > `skewedPartitionThresholdInBytes` 256 MB). — [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- Defaults: `spark.sql.autoBroadcastJoinThreshold` = 10 MB (`-1` disables); `spark.sql.shuffle.partitions` = 200. Join hints: `BROADCAST`, `MERGE`, `SHUFFLE_HASH`, `SHUFFLE_REPLICATE_NL` (priority in that order); Spark does not guarantee the hinted strategy. — [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- Caching: `spark.catalog.cacheTable` / `df.cache()`, `uncacheTable` / `unpersist()`; in-memory columnar cache scans only required columns (`spark.sql.inMemoryColumnarStorage.compressed=true`, `batchSize=10000`). — [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- Storage Partition Join (SPJ): avoids the shuffle using the storage layout of compatible V2 sources such as Iceberg; when SPJ applies, there are no `Exchange` nodes before the join (`spark.sql.sources.v2.bucketing.enabled=true`). — [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- Spark 4.3 adds opt-in `spark.sql.optimizer.singleTaskExecution.enabled` (shuffle-free single-task execution for small queries) and an Arrow-native cache serializer. — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)
- Spark 4.2 shipped a modernized Spark Web UI. — [Spark 4.2.0 release notes](https://spark.apache.org/releases/spark-release-4-2-0.html)
- Structured Streaming guide was split into subpages as of Spark 4.0: getting-started, apis-on-dataframes-and-datasets, real-time-mode, performance-tips, additional-information. Micro-batch: end-to-end latency "as low as 100 milliseconds" with exactly-once via checkpointing and write-ahead logs; Continuous Processing (since 2.3): "as low as 1 millisecond", at-least-once. — [Structured Streaming overview](https://spark.apache.org/docs/latest/streaming/index.html)
- Watermark semantics: `withWatermark("timestamp", "10 minutes")`; state for a window ending at T is kept until max event time seen minus threshold > T. Quote: a 2-hour watermark "guarantees that the engine will never drop any data that is less than 2 hours delayed"; later data "may or may not get aggregated." State cleanup works only in Append or Update mode (not Complete), the aggregation must include the event-time column or a window on it, and `withWatermark` must be called on that same column before the aggregation. — [Structured Streaming APIs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- Output modes: Append (default; only new rows, for queries whose rows never change), Complete (whole result table each trigger; aggregations), Update (changed rows only). Kafka source works with brokers 0.10.0+. — [Structured Streaming APIs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)
- Real-time Mode: introduced in Spark 4.1.0; stateful support (dropDuplicates, aggregations including windowed, JVM transformWithState, withWatermark) in 4.3.0. Enable with `.outputMode("update").trigger(Trigger.RealTime("5 minutes"))` (Python `trigger(realTime="5 minutes")`); checkpointLocation required; min duration 5 s; the duration "is primarily a checkpoint interval, not a latency target." Claims millisecond-scale latency via long-running tasks, one per input partition. Only Kafka source; sinks Kafka, foreach, console, memory; no foreachBatch, no stream-stream joins, no AQE; requires RocksDB state store with checkpoint format v2; Kafka sink is at-least-once. — [Real-time Mode docs](https://spark.apache.org/docs/latest/streaming/real-time-mode.html)

### Inferences
- Core vocabulary to teach in order *(standard knowledge)*: driver, executors, cores/slots, `local[*]`; transformations vs actions; lazy evaluation; job -> stages (split at shuffle boundaries) -> tasks (one per partition); narrow (map, filter, union) vs wide (groupBy, join, distinct, repartition); RDD lineage for fault tolerance; DataFrame/Dataset as schema-aware plans; Catalyst phases (analysis, logical optimization incl. predicate pushdown and column pruning, physical planning, codegen); Tungsten (off-heap binary rows, whole-stage codegen visible as `*(n)` in plans); `explain("formatted")` and the `Exchange hashpartitioning(...)`, `BroadcastExchange`, `BroadcastHashJoin`, `SortMergeJoin`, `AQEShuffleRead` nodes.
- Spark UI teaching map: Jobs -> Stages (task duration distribution: max >> median signals skew) -> SQL/DataFrame tab (plan graph with rows per node) -> Storage (cached data) -> Executors (spill, GC). Local UI at http://localhost:4040 *(standard default port; not re-verified)*.
- Skew lab: AQE handles skew only for sort-merge joins and only beyond 5x median and 256 MB, so a laptop-sized skew demo must lower `skewedPartitionThresholdInBytes` (e.g. to a few MB) and disable broadcast (`autoBroadcastJoinThreshold=-1`) to make the effect visible. Compare with manual salting (append random 0..N-1 to the hot key on the big side, explode the small side N times).
- "200 shuffle partitions" is a historical default that AQE now coalesces; set a large initial value and let AQE shrink it.

### Gaps
- Did not fetch the Spark "Web UI" docs page or Catalyst/Tungsten primary sources (Databricks blog posts 2015-2016); concept descriptions above are from training knowledge.
- No primary source fetched for default UI port 4040.

---

## 5. Spark 4.x: release timeline and headline features (as of Nov 2026)

### Takeaway
Spark is on a fast cadence: 4.0 (May 2025), 4.1 (Dec 2025), 4.2 (Jul 2026), 4.3 (30 Oct 2026, first under a quarterly feature-release cadence). The 4.x themes are Spark Connect (thin clients), ANSI SQL by default, VARIANT for semi-structured data, SQL pipe syntax and SQL scripting, Python data sources, Declarative Pipelines, and Real-time Mode streaming. Supported JDKs in current docs: 17, 21, 25.

### Cited Findings
- Release dates (news page): 4.0.0 May 23 2025; 4.0.1 Sep 6 2025; 4.1.0 Dec 16 2025; 4.1.1 Jan 9 2026; 4.0.2 Feb 5 2026; 4.2.0 previews Jan-May 2026; 4.1.2 May 21 2026; 4.0.3 Jun 11 2026; 4.2.0 Jul 14 2026; 4.1.3 and 4.0.4 Jul 15 2026; 3.5.9 Jul 16 2026; 4.0.5, 4.1.4, 4.2.1 Oct 27 2026; 4.3.0 Oct 30 2026. — [Spark news](https://spark.apache.org/news/index.html)
- 4.3.0 is "the first under a quarterly feature-release cadence", >1,100 JIRA tickets, >210 contributors. — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)
- Current docs (4.3.0): "Spark runs on Java 17/21/25, Scala 2.13, Python 3.11+, and R 4.0+ (Deprecated)." Also: "Java 25 prior to version 25.0.3 support is deprecated as of Spark 4.2.0." Runs on x86_64 and ARM64 JVMs. — [Spark docs overview](https://spark.apache.org/docs/latest/)
- Spark 4.0.0: ANSI SQL mode on by default (SPARK-44444); Spark Connect with a 1.5 MB `pyspark-client`, "full API compatibility for the Java client", Scala client parity, `spark.api.mode` switch, ML on Connect, Swift client; VARIANT type (SPARK-45827); SQL pipe syntax (SPARK-49555); Python Data Source API (SPARK-44076); string collations; Arbitrary State API v2 (`transformWithState`) and State Data Source; Java 17 default and Java 21 supported; Scala 2.13 default (2.12 dropped); removed Mesos, Hive < 2.0, JDK 8/11, Python 3.8; SparkR deprecated. — [Spark 4.0.0 release notes](https://spark.apache.org/releases/spark-release-4-0-0.html)
- Spark 4.1.0: Spark Declarative Pipelines (SDP; SPARK-51727); Structured Streaming Real-Time Mode first official support (stateless, single-digit ms); Spark Connect JDBC driver; VARIANT shredding GA and VARIANT enabled by default; recursive CTEs; KLL and Theta sketches; SQL Scripting GA and on by default; Arrow-native Python UDFs/UDTFs; Python data source filter pushdown; min Python 3.10, PyArrow 15. — [Spark 4.1.0 release notes](https://spark.apache.org/releases/spark-release-4.1.0.html)
- Spark 4.2.0: builds and runs on Java 25 (SPARK-51167); native GEOMETRY/GEOGRAPHY types; CDC `CHANGES` clause; Arrow-optimized Python UDFs on by default; NEAREST BY top-K joins; DSv2 transaction management; metric views; SQL path; modernized Web UI; Auto CDC (SCD Type 1) in Declarative Pipelines; pipe syntax gains aggregates in `|> SELECT` and `|` as alias of `|>`; SQL scripting cursors; RTM trigger in PySpark; Python streaming data source gets admission control and `Trigger.AvailableNow`; R 3.x dropped. — [Spark 4.2.0 release notes](https://spark.apache.org/releases/spark-release-4-2-0.html)
- Spark 4.3.0: Real-Time Mode stateful queries (~100 ms end-to-end for stateful; streaming aggregation, dropDuplicates, transformWithState) and RTM no longer `@Experimental`; Declarative Pipelines SCD Type 2 Auto CDC (target must support DSv2 row-level ops, e.g. Iceberg); `CREATE FLOW ... AS AUTO CDC INTO`; Spark Connect session REST API, operation IDs, Connect JDBC driver complex types; SQL `JSON_TABLE`, ANSI `UNNEST`, `ASOF JOIN` (off by default), `@` time-travel syntax on table names, `BIN BY` (off by default); VARIANT mutation functions (`variant_set`, `variant_insert`, ...); TIME(p) to nanoseconds; preview nanosecond timestamps; Python 3.10 dropped; Docker images default to eclipse-temurin on Ubuntu 26.04 with Python 3.14; `spark.rdd.compress` now on by default. — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)

### Inferences
- For a course, Spark 4.x features to *teach* (in order of value to a backend engineer): ANSI mode (casts and overflows now throw instead of returning NULL; a correctness change that breaks old notebooks); Spark Connect (client/server split, the future of how apps talk to Spark); VARIANT (semi-structured JSON without string parsing); pipe syntax (readability); Real-time Mode (positions Spark against Flink for sub-second streaming). Declarative Pipelines and SQL scripting are worth one demo each. Geospatial, metric views, ASOF/BIN BY are "know they exist".
- Version pinning for labs: Iceberg 1.12 runtime jars exist only for Spark 3.5, 4.0, 4.1 (see section 7) and Delta 4.4.x supports Spark 4.0.1/4.1/4.2 (not 4.3). So a single pinned Spark 4.1.x (latest 4.1.4) works with both lakehouse formats; 4.3.0 is fine for non-lakehouse lessons. Spark 4.1 runs on Java 17/21 (Java 25 support arrived in 4.2), so pin JDK 21.

### Gaps
- Spark 4.1.0 release page does not state Java versions; "4.1 supports JDK 17/21 but not 25" is inferred from 4.2 adding Java 25.
- The hyphenated URL `spark-release-4-1-0.html` returned 404; the dotted form `spark-release-4.1.0.html` loads. The 4.2/4.3 pages use hyphens.

---

## 6. Using Spark from Java and Kotlin

### Takeaway
Java is a first-class Spark language: the Dataset/DataFrame API, `Encoders`, and Spark SQL work from Java, and Spark Connect has a JVM client (`spark-connect-client-jvm`). Kotlin should call the Java API directly; the JetBrains `kotlin-spark-api` wrapper stops at Spark 3.3.2 and its README says Spark 4 support is "near impossible" with the current design. For a Kotlin learner in 2026, use Kotlin + Java Dataset API (classic, `local[*]`) or Kotlin + Spark Connect JVM client.

### Cited Findings
- kotlin-spark-api README: latest supported Spark is 3.3.2 (Scala 2.12/2.13); Spark 4.0.0+ support "proved to be near impossible using the current library design" and maintainers "simply don't have the time" for a rewrite. Not archived (no archive banner) but effectively unmaintained. Points to a community "Kotlin Spark API for Spark Connect" (github.com/eveliinavesala/spark-connect-kotlin, a Bachelor's thesis project). — [kotlin-spark-api](https://github.com/Kotlin/kotlin-spark-api)
- Spark Connect JVM client: `"org.apache.spark" %% "spark-connect-client-jvm" % "4.3.0"`; start server with `./sbin/start-connect-server.sh`; connect `SparkSession.builder().remote("sc://localhost").getOrCreate()`; default port 15002. Supported: Dataset, functions, Column, Catalog, KeyValueGroupedDataset, most streaming APIs. Unsupported: SparkContext and RDD. UDFs/map/filter lambdas need `registerClassFinder(...)` so class files are uploaded; jars via `addArtifact`. — [Spark Connect overview](https://spark.apache.org/docs/latest/spark-connect-overview.html)
- Spark 4.0 claims "full API compatibility for the Java client" in Spark Connect. — [Spark 4.0.0 release notes](https://spark.apache.org/releases/spark-release-4-0-0.html)
- Spark 4.1 added a JDBC driver for Spark Connect; 4.3 extended it with complex types and SQLSTATE error mapping. — [Spark 4.1.0](https://spark.apache.org/releases/spark-release-4.1.0.html), [Spark 4.3.0](https://spark.apache.org/releases/spark-release-4-3-0.html)
- Scala/Java users include Spark via Maven coordinates; Scala API users must match Scala 2.13. — [Spark docs overview](https://spark.apache.org/docs/latest/)

### Inferences
- Gradle (Kotlin DSL) for classic local Spark: `implementation("org.apache.spark:spark-sql_2.13:4.1.4")` and run with `SparkSession.builder().master("local[*]")`. From Kotlin, use `Dataset<Row>` with `functions.col(...)`; typed `Dataset<T>` needs `Encoders.bean(JavaBeanClass::class.java)` (Kotlin data classes are not Java beans by default; use `Encoders.bean` with a mutable class with no-arg constructor, or stay with `Row`/SQL). *(standard knowledge, not re-verified)*
- When embedding Spark 4 in your own JVM process on JDK 17+, you typically need `--add-opens` JVM flags (e.g. `java.base/sun.nio.ch`, `java.base/java.nio`, `java.base/java.lang`, `java.base/java.util`) that `spark-submit` adds automatically; put them in Gradle `application { applicationDefaultJvmArgs = [...] }`. *(not re-verified; writer must test on the pinned version)*
- Spark Connect is the cleaner story for a backend engineer: the client jar is small, no Hadoop/Scala classpath conflicts with the app, the server can run in Docker (`apache/spark` image). Trade-off: no RDD API and lambdas require class upload, so teach RDDs with classic local mode.
- Scala knowledge is not required for the course; reading Scala snippets in docs is enough.

### Gaps
- Did not verify the exact `--add-opens` list for Spark 4.1/4.3 (Spark's `JavaModuleOptions` source not fetched).
- No fetch of a Kotlin+Spark 4 sample project; the Kotlin approach above is inference.
- spark-connect-kotlin project status/quality not checked.

---

## 7. Lakehouse table formats: Iceberg, Delta Lake, Hudi (plus DuckLake)

### Takeaway
A table format is a metadata layer over immutable Parquet files that gives ACID commits, snapshots/time travel, schema and partition evolution on object storage. Iceberg is the de facto interoperability standard (format v3 adopted: deletion vectors, VARIANT, geo types, row lineage, default values; v4 in development; latest 1.12.0, Sep 2026). Delta Lake 4.x (latest 4.4.1, Oct 2026) is Databricks-led and converging on catalog-managed tables and Iceberg compatibility (UniForm). Hudi 1.2 targets incremental/upsert-heavy pipelines. DuckLake 1.0 (Apr 2026) stores metadata in a SQL database instead of files.

### Cited Findings
- Iceberg format versions: v1, v2, v3 complete and adopted; v4 under active development. v1 = analytic tables on immutable Parquet/Avro/ORC files; v2 = row-level deletes via delete files; v3 = nanosecond timestamps (with/without zone), `unknown`, `variant`, `geometry`, `geography` types, column default values, multi-argument transforms, row lineage, binary deletion vectors, table encryption keys; v4 (draft) = adaptive metadata tree with a root manifest replacing the manifest list, data files and DVs in a combined entry, relative locations, table constraints, and no new equality deletes. — [Iceberg spec](https://iceberg.apache.org/spec/)
- Iceberg structure: table metadata file (schema, partition spec, properties, snapshots; every change writes a new one); snapshot = full set of data files at a point in time; one manifest list per snapshot (v1-v3) with partition stats for skipping; manifests track data/delete files with partition values and metrics and are reused across snapshots. Commits = optimistic: write new metadata, atomically swap the table's metadata pointer from base to new; if the base changed, retry, giving serializable isolation; readers stay on the snapshot they loaded. — [Iceberg spec](https://iceberg.apache.org/spec/)
- Iceberg releases: 1.10.0 (11 Sep 2025: Spark 4.0 support, Flink 2.0, v3 row lineage in Spark, nanosecond timestamps, variant reads); 1.11.0 (19 May 2026: Spark 4.1 support, MERGE INTO schema evolution, row lineage readers `_row_id`/`_last_updated_sequence_number`, shredded variant writing in Spark, REST scan planning; dropped Java 11); 1.12.0 (29 Sep 2026: geo read/write in Avro/Parquet, v4 manifest work, Hilbert-curve clustering in `rewrite_data_files`, REST idempotency keys; dropped Spark 3.4 and Flink 2.0, removed position deletes with row data). — [Iceberg releases](https://iceberg.apache.org/releases/)
- Iceberg 1.12 engine support: Spark 3.5 (`iceberg-spark-runtime-3.5_2.12/_2.13`), 4.0 (`iceberg-spark-runtime-4.0_2.13`), 4.1 (`iceberg-spark-runtime-4.1_2.13`) maintained; Spark 4.2/4.3 not listed. Flink 1.20, 2.2, 2.3 maintained; 2.0/2.1 EOL. Lists Trino, DuckDB, ClickHouse, Presto, Dremio, StarRocks, Athena, EMR, Impala, Doris as other engines. — [Iceberg multi-engine support](https://iceberg.apache.org/multi-engine-support/)
- Delta Lake releases: 4.0.0 (09 Jun; Spark 4.0; catalog-managed tables preview, Delta Connect preview, Variant, DROP FEATURE without truncating history), 4.0.1 (16 Jan), 4.1.0 (26 Feb; conflict-free enabling of deletion vectors and column mapping; Kernel-based DSv2 connector; UniForm re-enabled for Spark 4.0), 4.2.0 (16 Apr; Kernel geospatial and Variant GA; experimental Kernel-based Flink connector), 4.3.0 (18 Jun; Unity Catalog Delta REST API; atomic incremental UniForm-Iceberg conversion), 4.4.0 (20 Aug; Spark 4.2 support; identity columns in SQL DDL), 4.4.1 (05 Oct; latest; supports Spark 4.2.0, 4.1.0, 4.0.1). Note: `delta-iceberg` (UniForm) does not support Spark 4.2. — [Delta releases](https://github.com/delta-io/delta/releases), [v4.0.0](https://github.com/delta-io/delta/releases/tag/v4.0.0)
- Hudi: latest listed 1.2.1 (after 1.1.2, 1.0.2); 1.2.1 bundles for Spark 4.1/4.0/3.5/3.4/3.3 and Flink 2.1/2.0/1.20-1.17. 1.2 headline: VECTOR, VARIANT, BLOB types, Lance file format, Flink Source V2 (FLIP-27), Flink record-level index; keeps table version 9. — [Hudi downloads](https://hudi.apache.org/releases/download), [Hudi 1.2](https://hudi.apache.org/releases/release-1.2)
- DuckLake: v1.0 announced 13 Apr 2026 ("The Lakehouse Format Built on SQL Reaches Production-Readiness"); DuckLake 1.1 spec and implementation ship with DuckDB 2.0 (Oct 2026). — [DuckDB news](https://duckdb.org/news/), [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200)
- DuckLake 1.0 features per search-result summaries: guaranteed backward compatibility, data inlining, sorted tables, bucket partitioning, deletion buffers stored as Iceberg-compatible Puffin files; inlining of updates/deletes on by default (threshold 10 rows). — search results citing [ducklake.select](https://www.ducklake.select/) and [MotherDuck newsletter Apr 2026](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2026/) (not fetched; treat as secondary)
- Spark 4.3 Declarative Pipelines SCD2 requires a target catalog with DSv2 row-level operations "such as Apache Iceberg"; Spark 4.3 adds `@` time-travel syntax on table names. — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)

### Inferences
- Teaching model for all three formats: "Git for tables". Data files are immutable blobs; metadata files are commits; the catalog holds the branch pointer; a commit is a compare-and-swap of that pointer. Time travel = read an older snapshot; rollback = move the pointer; expire_snapshots = garbage collection; compaction (`rewrite_data_files`) = rewrite many small files into fewer large ones and commit.
- Copy-on-write vs merge-on-read *(standard knowledge)*: CoW rewrites affected data files on update/delete (fast reads, slow writes); MoR writes delete files or deletion vectors and merges at read time (fast writes, reads pay until compaction). Iceberg v2 position/equality deletes -> v3 deletion vectors (one bitmap per data file, Puffin-stored); Delta has had deletion vectors since 2.x/3.x; Hudi names the table types COPY_ON_WRITE and MERGE_ON_READ explicitly.
- Hidden partitioning (Iceberg) *(standard knowledge)*: partition by transform (`days(ts)`, `bucket(16, id)`, `truncate`), queries filter on the source column and Iceberg prunes automatically; partition spec can evolve without rewriting old data. Contrast with Hive where users must filter on the `dt` string column.
- Schema evolution: Iceberg tracks columns by ID, so rename/drop/reorder are metadata-only and safe; Hive/plain Parquet track by name/position.
- Positioning statement for the course (Nov 2026): Iceberg is the cross-engine default and what Spark, Trino, DuckDB, Flink, Snowflake etc. read/write; Delta is the default inside Databricks and increasingly exposes Iceberg via UniForm/Unity Catalog; Hudi is a niche for streaming upserts/CDC-heavy ingestion; DuckLake is an interesting simpler design for small-to-mid teams. Teach Iceberg hands-on, Delta/Hudi by comparison table.

### Gaps
- Delta and Unity Catalog release pages show day/month only; years (Delta 4.0.0 = Jun 2025, 4.0.1 = Jan 2026 ... 4.4.1 = Oct 2026) are inferred from Spark version support order. Writer should confirm on delta.io if quoting years.
- Hudi 1.2.x release dates not found on fetched pages.
- No fetched primary source on Iceberg 1.12 Spark 4.2/4.3 support plans; check iceberg.apache.org/releases before publishing.
- DuckLake 1.0 announcement page itself not fetched.

---

## 8. Catalogs: Hive Metastore, Iceberg REST, Apache Polaris, Unity Catalog OSS

### Takeaway
The catalog is the thing that makes commits atomic (it holds the current-metadata pointer) and lets many engines find the same tables. The industry moved from Hive Metastore to the Iceberg REST catalog protocol. Apache Polaris (Iceberg REST, now an ASF top-level project, 2026) and Unity Catalog OSS (LF AI & Data sandbox; Delta + Iceberg REST) are the two open implementations to name.

### Cited Findings
- Apache Polaris: "open-source, fully-featured catalog for Apache Iceberg" implementing Iceberg's REST API; interoperates with Doris, Flink, Spark, Dremio OSS, StarRocks, Trino; site version list shows 1.8.0 as newest. — [polaris.apache.org](https://polaris.apache.org/)
- Polaris graduated to an ASF top-level project; sources differ on date: Polaris blog 19 Feb 2026, Dremio press release 18 Feb 2026, ASF announcement dated 5 Mar 2026 (Polaris and Apache Gluten both became TLPs). Entered incubation Aug 2024. — search results: [Polaris blog](https://polaris.apache.org/blog/2026/02/19/apache-polaris-graduates-to-top-level-project/), [ASF news](https://news.apache.org/?p=7401), [Fivetran](https://www.fivetran.com/blog/the-impact-of-apache-polaris-graduating-to-top-level-apache-project), [OpenSourceForU](https://www.opensourceforu.com/2026/03/apache-elevates-open-source-projects-gluten-and-polaris-to-top-level-status/) (these were not fetched individually)
- Unity Catalog OSS releases: 0.3.0 (Jul 2025; Spark 4.0/Delta 4.0), 0.4.0 (Feb 2026; Spark 4.1), 0.5.0 (Jun 2026; UC Delta API for managed Delta tables), 0.6.0 (Aug 2026; Spark 4.2 connector, metric views), 0.7.0 (13 Oct 2026; Iceberg REST catalog support for create/write/read/rename/drop of Iceberg tables, native Iceberg tables enabled by default). Years inferred from in-page references. — [Unity Catalog releases](https://github.com/unitycatalog/unitycatalog/releases)
- unitycatalog.io: LF AI & Data Sandbox Project badge; formats Delta Lake, Iceberg (via UniForm and Iceberg REST APIs), Parquet, CSV, JSON; governs tabular, non-tabular and AI assets. — [unitycatalog.io](https://www.unitycatalog.io/)
- Delta 4.3 integrated the Unity Catalog Delta REST API; Delta's "catalog-managed tables" make the catalog, not the filesystem log, the commit coordinator. — [Delta releases](https://github.com/delta-io/delta/releases)
- The Iceberg quickstart runs `apache/iceberg-rest-fixture` on port 8181 with `CATALOG_WAREHOUSE=s3://warehouse/`, `CATALOG_IO__IMPL=org.apache.iceberg.aws.s3.S3FileIO`, `CATALOG_S3_ENDPOINT`, path-style access. — [Iceberg Spark quickstart](https://iceberg.apache.org/spark-quickstart/)
- DuckDB can `ATTACH` an Iceberg REST catalog (`TYPE iceberg`, `URI`, secret with OAuth client credentials) and then INSERT/UPDATE/DELETE/MERGE/ALTER catalog-managed tables; direct `iceberg_scan` of a path is read-only. — [DuckDB Iceberg extension](https://duckdb.org/docs/2.0/core_extensions/iceberg/overview.html)

### Inferences
- Teach catalogs as three generations: (1) Hive Metastore (Thrift service over an RDBMS, Hive-specific), (2) format-specific catalogs (Iceberg Hadoop/filesystem catalog, Glue, JDBC), (3) REST catalog protocol (engine-neutral HTTP spec; server can vend short-lived storage credentials and do server-side scan planning). The Iceberg REST spec is the interop contract; Polaris, Unity Catalog, Gravitino, Nessie, Lakekeeper and cloud services implement it *(the last three names not re-verified this session)*.
- For laptop labs, the `apache/iceberg-rest-fixture` image is the simplest REST catalog (it is a test fixture, not production); a filesystem "hadoop" catalog needs no container at all.

### Gaps
- Polaris latest release date not confirmed (1.8.0 from nav only).
- Did not verify whether Polaris now supports Delta "generic tables"/federation in 1.x (training data says generic tables were added in 1.0; not re-checked).
- Apache Gravitino, Project Nessie, Lakekeeper status not researched.

---

## 9. Query engines and the "big data is dead / single node is enough" debate

### Takeaway
For 2026 laptop-scale and most company-scale analytics, a single-node engine (DuckDB 2.0) reading Parquet/Iceberg is often enough; Spark remains the default for large batch ETL, ML feature pipelines and streaming; Trino is the distributed interactive SQL engine over many sources/catalogs; ClickHouse is a real-time OLAP database (owns its storage, also reads Iceberg). Jordan Tigani's "Big Data is Dead" provides the numbers for the debate; Spark itself now has opt-in single-task execution for small queries.

### Cited Findings
- MotherDuck "Big Data is Dead" (Jordan Tigani, ex-BigQuery founding engineer; written in 2023): most BigQuery customers had under 1 TB total storage; ~90% of queries (customers spending > $1k/yr) processed under 100 MB; storage grows faster than compute; most processing touches data < 24 hours old, a week-old record is ~20x less likely to be queried; a standard AWS instance has 64 cores/256 GB RAM vs 1 core/2 GB in 2006; five "Big Data One-Percenter" questions (Are you generating a huge amount of data? Do you need to use a huge amount at once? Too big for one machine? Data hoarder? Would summarizing be better?). Thesis quote: "the era of Big Data is over". The author notes his figures are approximate. — [MotherDuck](https://motherduck.com/blog/big-data-is-dead/)
- DuckDB release calendar: 1.4.0 LTS (16 Sep 2025, EOL 17 Nov 2026), 1.5.0 (9 Mar 2026, last patch 1.5.6, EOL 1 Mar 2027), 2.0.0 LTS (21 Oct 2026, EOL 22 Oct 2027); 2.0.1 planned 18 Nov 2026; 2.1 planned 2027 H1. — [DuckDB release calendar](https://duckdb.org/release_calendar)
- DuckDB 2.0 "Cinnamon Teal": Quack client-server protocol (`CONNECT`, CLI `-serve`/`-connect`; server listens on localhost by default), async I/O for Parquet/CSV/native reads (aimed at object storage), first-class shredded VARIANT, CLI agent mode, triggers, PEG parser by default; breaking: 2.0 database files unreadable by older versions, single-arrow lambdas disabled, C++17 required, macOS x86_64 support ends in 2.1. — [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200)
- DuckDB blog post "Big Data on the Cheapest MacBook" dated 2026-03-11 (title only seen). — [DuckDB news](https://duckdb.org/news/)
- DuckDB Iceberg writes post "Writes in DuckDB-Iceberg" dated 2025-11-28. — [DuckDB news](https://duckdb.org/news/)
- Trino: latest release 484 (15 Oct 2026); 483 (17 Jul 2026), 482 (25 Jun 2026), 481 (11 May 2026), 480 (24 Mar 2026). — [Trino release notes](https://trino.io/docs/current/release.html)
- Trino requires 64-bit Java 25, minimum 25.0.1 (8/11/17/21/24 unsupported); Docker image `trinodb/trino` uses Eclipse Temurin. — [Trino deployment](https://trino.io/docs/current/installation/deployment.html)
- Spark 4.3 opt-in `spark.sql.optimizer.singleTaskExecution.enabled` for shuffle-free execution of small queries. — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)
- Apache Gluten (native vectorized execution for Spark) became an ASF TLP alongside Polaris in 2026. — search result: [OpenSourceForU](https://www.opensourceforu.com/2026/03/apache-elevates-open-source-projects-gluten-and-polaris-to-top-level-status/) (not fetched)

### Inferences
- Decision rubric for the course (synthesis): single node (DuckDB, Polars) when the working set of a query after pruning fits comfortably on one machine's disk/RAM (laptop: up to roughly hundreds of GB of Parquet, out-of-core spilling helps); Spark when data or job concurrency outgrows one machine, when you need fault-tolerant long batch jobs, streaming with state, or the platform team already runs it; Trino when many users run interactive SQL across many catalogs/sources; ClickHouse when you need sub-second dashboards on fresh event data with its own storage; Flink when streaming is the primary product (event-time, large state, low latency).
- Counterpoints to teach (fairness): Tigani's numbers are from BigQuery customers and are approximate; data engineering (joins of large fact tables, backfills, ML feature generation over years of data, multi-TB daily ingest) still needs distributed engines; the lakehouse makes engine choice per workload possible because the data lives once in open format.
- Native execution trend: Spark's JVM row-at-a-time heritage is being supplemented by vectorized native engines (Gluten+Velox, DataFusion Comet, Databricks Photon). Mention in one paragraph.

### Gaps
- ClickHouse current version/status and Iceberg support not fetched.
- DuckDB "Big Data on the Cheapest MacBook" content not read (title only); a good lab reference if the writer fetches it.
- Polars / DataFusion not researched.

---

## 10. Stream processing (Flink 2.x, Kafka to lakehouse) and orchestration (Airflow 3)

### Takeaway
Flink 2.x (2.0 Mar 2025; latest 2.3.0 Jun 2026) is the streaming-first engine: disaggregated state on object storage, Java 17 default, legacy DataSet/Scala APIs removed. Spark Structured Streaming plus Real-time Mode now covers many low-latency cases. Kafka -> Iceberg is the standard ingestion path. Airflow 3 (Apr 2025; latest 3.4.0 on 6 Nov 2026) is the orchestration default, with assets, DAG versioning and event-driven scheduling.

### Cited Findings
- Flink 2.0.0 released 24 Mar 2025, first 2.x release: disaggregated state management with the ForSt state backend and asynchronous execution; Materialized Tables for stream/batch unification; adaptive batch execution (adaptive broadcast join, skew handling); deeper Apache Paimon integration; removed DataSet API, Scala DataStream/DataSet APIs, SourceFunction/SinkFunction/Sink V1, per-job mode; Java 8 removed, Java 17 default, Java 21 supported; no state compatibility 1.x -> 2.x. — [Flink 2.0 announcement](https://flink.apache.org/2025/03/24/apache-flink-2.0.0-a-new-era-of-real-time-data-processing/)
- Flink stable releases: 2.3.0 (25 Jun 2026, latest), 2.2.1 (15 May 2026), 2.1.3 (14 Jun 2026), 2.0.2 (11 May 2026). Kafka connector 5.0.0 (2 Jun 2026) for Flink 2.1.x/2.2.x; Flink CDC 3.7.0 for Flink 1.20.x/2.2.x. — [Flink downloads](https://flink.apache.org/downloads/)
- Iceberg Flink runtime maintained for Flink 1.20, 2.2, 2.3. — [Iceberg multi-engine support](https://iceberg.apache.org/multi-engine-support/)
- Spark Real-time Mode: Kafka is the only supported source; sinks Kafka/foreach/console/memory (so Kafka -> Iceberg in Spark uses micro-batch, not RTM). — [Real-time Mode docs](https://spark.apache.org/docs/latest/streaming/real-time-mode.html)
- Airflow releases: 3.0.0 (22 Apr 2025), 3.1.0 (25 Sep 2025), 3.2.0 (7 Apr 2026), 3.3.0 (6 Jul 2026), 3.4.0 (6 Nov 2026); latest 2.x listed is 2.11.2 (14 Mar 2026). — [Airflow announcements](https://airflow.apache.org/announcements/)
- Airflow 3.0 headline features: DAG versioning (runs finish on the version they started with), scheduler-managed backfills, Task Execution Interface and Task SDK (client-server task execution), Datasets renamed/evolved into Assets with decorator syntax, event-driven scheduling (e.g. AWS SQS trigger), new React UI on FastAPI, Edge Executor, non-data-interval DAG runs. — [Airflow 3.0 blog](https://airflow.apache.org/blog/airflow-three-point-oh-is-here/)

### Inferences
- Course scope: one lesson on Structured Streaming hands-on (Kafka -> windowed aggregation with watermark -> Iceberg), with Flink covered conceptually (when to pick it: very large keyed state, event-time-centric pipelines, CDC with Flink CDC, sub-second end-to-end). Orchestration gets a short section in the capstone (Airflow 3 assets triggering a Spark job / dbt), not a lesson of its own.
- Kafka -> lakehouse options to name *(not re-verified)*: Spark Structured Streaming micro-batch to Iceberg/Delta; Flink Iceberg sink; Iceberg Kafka Connect sink (part of the Iceberg project); vendor features (Confluent Tableflow, Redpanda Iceberg topics). Teach the small-file problem: frequent commits create many small files and snapshots, requiring compaction and snapshot expiry.

### Gaps
- Flink 2.1/2.2/2.3 headline features not researched.
- Airflow 2.x EOL date not found on the announcements page.
- Iceberg Kafka Connect sink status not verified.

---

## 11. Current versions snapshot (as of 7 Nov 2026)

### Takeaway
Pin these for the course; most projects ship quarterly or faster, so the writer should re-check before publishing.

### Cited Findings
| Project | Latest (date) | Notes | Source |
|---|---|---|---|
| Apache Spark | 4.3.0 (30 Oct 2026); maintenance 4.2.1, 4.1.4, 4.0.5 (27 Oct 2026); 3.5.9 (16 Jul 2026) | Java 17/21/25, Scala 2.13, Python 3.11+ | [news](https://spark.apache.org/news/index.html), [docs](https://spark.apache.org/docs/latest/) |
| Apache Iceberg | 1.12.0 (29 Sep 2026) | Spark 3.5/4.0/4.1; Flink 1.20/2.2/2.3; spec v3 adopted, v4 in progress | [releases](https://iceberg.apache.org/releases/), [multi-engine](https://iceberg.apache.org/multi-engine-support/) |
| Delta Lake | 4.4.1 (05 Oct, year inferred 2026) | Spark 4.2.0/4.1.0/4.0.1 | [releases](https://github.com/delta-io/delta/releases) |
| Apache Hudi | 1.2.1 (date not found) | Spark 3.3-4.1, Flink 1.17-2.1 | [downloads](https://hudi.apache.org/releases/download) |
| Apache Hive | 4.2.1 (24 Aug 2026) | JDK 21 minimum for 4.2.x; 1.x-3.x EOL | [downloads](https://hive.apache.org/general/downloads/) |
| Trino | 484 (15 Oct 2026) | Java 25.0.1+ | [releases](https://trino.io/docs/current/release.html) |
| DuckDB | 2.0.0 LTS (21 Oct 2026); 2.0.1 due 18 Nov 2026 | 1.4 LTS EOL 17 Nov 2026 | [calendar](https://duckdb.org/release_calendar) |
| DuckLake | 1.0 (13 Apr 2026); 1.1 ships with DuckDB 2.0 | | [news](https://duckdb.org/news/), [2.0 post](https://duckdb.org/2026/10/21/announcing-duckdb-200) |
| Apache Flink | 2.3.0 (25 Jun 2026) | 2.0 released 24 Mar 2025 | [downloads](https://flink.apache.org/downloads/) |
| Apache Airflow | 3.4.0 (6 Nov 2026) | 3.0 released 22 Apr 2025 | [announcements](https://airflow.apache.org/announcements/) |
| Apache Polaris | 1.8.0 (date not confirmed); TLP Feb/Mar 2026 | Iceberg REST catalog | [site](https://polaris.apache.org/), [blog](https://polaris.apache.org/blog/2026/02/19/apache-polaris-graduates-to-top-level-project/) |
| Unity Catalog OSS | 0.7.0 (13 Oct 2026, year inferred) | LF AI & Data sandbox; Iceberg REST support | [releases](https://github.com/unitycatalog/unitycatalog/releases) |
| apache/spark Docker | 4.3.0 tags incl. `-java17/-java21/-java25`, `-python3`, `-scala`; all amd64+arm64 (updated 5-6 Nov 2026) | | [Docker Hub API](https://hub.docker.com/v2/repositories/apache/spark/tags?page_size=30) |

### Inferences
- Things likely to change soon after Nov 2026: DuckDB 2.0.1 (18 Nov), Iceberg support for Spark 4.2/4.3, Delta support for Spark 4.3, Spark 4.4 (quarterly cadence implies ~Jan-Feb 2027), Airflow 3.4.x patches.

### Gaps
- Release dates missing for Hudi 1.2.x and Polaris 1.8.0.
- ClickHouse version not checked.

---

## 12. Misconceptions to address (with evidence)

### Takeaway
Most misconceptions come from 2015-era Spark/Hadoop marketing. Each one maps to a lab that disproves it.

### Cited Findings
- "Spark is in-memory so it never touches disk": batch shuffles are materialized between stages; Spark 4.3's Real-Time Mode had to add "pipelined shuffles" so producer and consumer stages run concurrently; 4.3 also turns on `spark.rdd.compress` by default. — [Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html)
- "More partitions = faster": AQE exists to *coalesce* post-shuffle partitions toward a 64 MB advisory size; `spark.sql.shuffle.partitions` default 200 is a starting point. — [Spark tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- "Hadoop is how you do big data today": Hive 1.x-3.x EOL (2024); Spark 4 removed Mesos and pre-2.0 Hive support; cloud object stores have been replacing HDFS since ~2015 per the Lakehouse paper. — [Hive downloads](https://hive.apache.org/general/downloads/), [Spark 4.0.0](https://spark.apache.org/releases/spark-release-4-0-0.html), [Lakehouse paper](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- "A data lake is just a folder of CSVs": Lakehouse paper lists reliability and staleness problems of two-tier lake+warehouse; Iceberg spec defines metadata files, snapshots, manifests and atomic pointer-swap commits on top of Parquet/ORC/Avro. — [Lakehouse paper](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf), [Iceberg spec](https://iceberg.apache.org/spec/)
- "Iceberg is a database/engine": Iceberg is a spec plus libraries; many engines (Spark, Flink, Trino, DuckDB, ClickHouse, Dremio, StarRocks, Athena, ...) read/write it. — [Iceberg multi-engine support](https://iceberg.apache.org/multi-engine-support/)
- "Cache everything": cache is opt-in per DataFrame/table and must be `unpersist`ed; Spark's columnar cache reads only needed columns. — [Spark tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- "You need a cluster for 100 GB": MotherDuck data (90% of BigQuery queries < 100 MB; most customers < 1 TB); DuckDB TPC-H SF100 database is 26 GB on disk; Spark 4.3 even adds single-task execution for small queries. — [MotherDuck](https://motherduck.com/blog/big-data-is-dead/), [DuckDB TPC-H](https://duckdb.org/docs/2.0/core_extensions/tpch.html), [Spark 4.3.0](https://spark.apache.org/releases/spark-release-4-3-0.html)
- "Watermarks drop all late data exactly at the threshold": the docs guarantee data within the threshold is kept, but later data "may or may not get aggregated." — [Structured Streaming APIs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html)

### Inferences
- "collect() is fine": `collect()` ships every row to the driver JVM heap; use `show`, `take`, `limit`, aggregate first, or write to storage. Lab: collect a 50M-row DataFrame with default driver memory and watch it fail or GC-thrash *(standard knowledge)*.
- "Spark Connect is just remote JDBC": it ships unresolved logical plans (protobuf) and streams Arrow results; DataFrame API, not only SQL.
- "Lakehouse table = faster by itself": the format gives correctness (ACID, snapshots); speed still comes from file sizes, sort order/clustering, stats and compaction.
- "Partition by everything (user_id)": over-partitioning creates millions of tiny files; prefer Iceberg transforms (`bucket`, `days`) and sort order.
- "Exactly-once means my side effects happen once": only with replayable source + checkpoint + idempotent/transactional sink; RTM Kafka sink is at-least-once.

### Gaps
- No measured numbers yet for the collect() failure or CSV-vs-Parquet speedups on an M-series Mac; labs should generate them.

---

## 13. Lab environment on a Mac (Apple Silicon)

### Takeaway
Simplest reliable setup: JDK 21 (Temurin) + Python 3.12 venv with `pip install pyspark==4.1.4 duckdb` for most labs; a Gradle Kotlin project with `spark-sql_2.13` for JVM labs; Docker only for the REST catalog, Kafka and Trino. Use a filesystem ("hadoop") Iceberg catalog first, a REST catalog second. Avoid MinIO (community edition is source-only now); use RustFS as the Iceberg quickstart does, or skip object storage. Datasets: NYC TLC Parquet and DuckDB-generated TPC-H.

### Cited Findings
- PySpark via pip: Python 3.11+ and Java 17+ with `JAVA_HOME` (current docs, 4.3); extras `pyspark[sql]`, `pyspark[connect]`, `pyspark[pipelines]`; `pyspark-connect` makes Connect the default; `pyspark-client` is pure Python with no JARs/JRE and only supports `spark.remote`. — [PySpark install](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
- Spark 4.1 minimum Python is 3.10, and it supports Python 3.14. — [Spark 4.1.0](https://spark.apache.org/releases/spark-release-4.1.0.html)
- Spark runs on ARM64 JVMs; local shell: `./bin/pyspark --master "local[2]"`. — [Spark docs](https://spark.apache.org/docs/latest/)
- `apache/spark` Docker images: 4.3.0 tags with java17/java21/java25 and python3/r/scala variants, all published for amd64 and arm64. — [Docker Hub API](https://hub.docker.com/v2/repositories/apache/spark/tags?page_size=30)
- Iceberg Spark quickstart (current): docker compose with `tabulario/spark-iceberg` (Spark + Jupyter on 8888, Spark UI 8080, Thrift 10000/10001), `apache/iceberg-rest-fixture` (8181), and `rustfs/rustfs:1.0.0` as S3 (9000 API, 9001 console; network-aliased as `minio` because the spark image expects that host), plus a bucket-creation helper. Non-Docker config: `spark.jars.packages org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.12.0`, `spark.sql.extensions org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions`, `spark.sql.catalog.local org.apache.iceberg.spark.SparkCatalog`, `spark.sql.catalog.local.type hadoop`, `spark.sql.catalog.local.warehouse $PWD/warehouse`. — [Iceberg Spark quickstart](https://iceberg.apache.org/spark-quickstart/)
- MinIO: community edition is now source-only (no pre-built binaries), Docker Hub `minio/minio` images reportedly removed, and the GitHub repo says it is no longer maintained, pointing to paid AIStor; dates reported differently (maintenance mode ~3 Dec 2025; "no longer maintained" ~12 Feb 2026). Some teams moved to RustFS. — search results: [github.com/minio/minio](https://github.com/minio/MinIO), [DEV Community](https://dev.to/alexandrev/minio-in-maintenance-mode-what-it-means-for-the-community-edition-oem-users-and-open-source-3o4j), [vonng blog](https://blog.vonng.com/en/db/minio-resurrect/index.md) (not fetched; secondary)
- Hive standalone metastore image `apache/hive:standalone-metastore-4.2.1` is multi-arch (amd64/arm64). — [Docker Hub API](https://hub.docker.com/v2/repositories/apache/hive/tags?page_size=15)
- Trino needs Java 25.0.1+ if run outside Docker; use `trinodb/trino` image. — [Trino deployment](https://trino.io/docs/current/installation/deployment.html)
- NYC TLC trip records are Parquet; datasets yellow, green, fhv, fhvhv; latest month listed September 2026; URL pattern `https://d37ci6vzurychx.cloudfront.net/trip-data/{type}_tripdata_{YYYY-MM}.parquet` (e.g. `yellow_tripdata_2024-01.parquet`); 2025+ data adds `cbd_congestion_fee`; TLC warns of possible schema standardization changes. — [NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- DuckDB TPC-H: `INSTALL tpch; LOAD tpch;` (or autoload), `CALL dbgen(sf = 1);`, `PRAGMA tpch(4);`, `FROM tpch_queries();`, `FROM tpch_answers();` (answers for SF 0.01/0.1/1); `dbgen(sf, children, step)` for chunked generation; DuckDB DB sizes: SF1 250 MB, SF10 2.5 GB, SF100 26 GB, SF1000 265 GB. Data differs slightly from the official spec (use `tpchgen-cli` for compliant data). — [DuckDB TPC-H](https://duckdb.org/docs/2.0/core_extensions/tpch.html)
- DuckDB Iceberg: `iceberg_scan('path', allow_moved_paths = true)`, `iceberg_snapshots(...)`, `iceberg_metadata(...)`, time travel via `snapshot_from_id`/`snapshot_from_timestamp` or `AT (VERSION => ...)`; REST `ATTACH ... (TYPE iceberg, URI ...)` with writes. — [DuckDB Iceberg](https://duckdb.org/docs/2.0/core_extensions/iceberg/overview.html)

### Inferences
- Recommended baseline (synthesis):
  1. `brew install --cask temurin@21` (or SDKMAN) and set `JAVA_HOME` to JDK 21. JDK 25 works for Spark 4.2+/4.3 (needs 25.0.3+ to avoid the deprecated range), but Spark 4.1 (needed for Iceberg 1.12 / Delta UniForm) is safest on 21.
  2. `uv venv --python 3.12 && uv pip install "pyspark[sql]==4.1.4" duckdb pyarrow` (Spark 4.1 supports 3.10+, 4.3 needs 3.11+).
  3. Gradle Kotlin DSL project: `org.apache.spark:spark-sql_2.13:4.1.4` (+ `org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.12.0` for lakehouse lessons); add `--add-opens` JVM args (verify list).
  4. DuckDB CLI 2.0 (`brew install duckdb`).
  5. Docker Desktop/OrbStack/Colima for: `apache/iceberg-rest-fixture` + RustFS (Lesson 10), Kafka (Lesson 11), `trinodb/trino` (Lesson 12), `apache/spark:4.3.0-java21-python3` for a Spark Connect server.
- Data: download 3-12 months of yellow taxi Parquet (each month roughly tens of MB; size not verified) for realistic-but-small labs; DuckDB `dbgen` SF10 (~10 GB raw text equivalent; 2.5 GB as DuckDB DB) exported with `COPY lineitem TO 'lineitem.parquet'` for Spark-vs-DuckDB comparisons; SF100 for the "laptop can still do it" demo if disk allows.
- Spark UI: classic local mode serves it on http://localhost:4040; in the `tabulario/spark-iceberg` compose the UI is mapped to 8080.
- Memory: give the local driver `spark.driver.memory=6g` or more on 16 GB Macs; Docker VM 8 GB for the compose stacks.

### Gaps
- Not verified: `tabulario/spark-iceberg` image's Spark version and arm64 availability; `apache/iceberg-rest-fixture` arm64 availability; official Apache Kafka image tag (`apache/kafka`) and KRaft single-node config; `trinodb/trino` arm64.
- Not verified: per-month NYC taxi file sizes.
- The exact `--add-opens` flags for embedding Spark 4.1 in a Gradle app.

---

## 14. Proposed lesson outline (12 lessons) with labs

### Takeaway
Order: why -> history -> files -> Spark engine -> Spark performance -> Spark 4/JVM -> tables -> catalogs/interop -> streaming -> engines and the single-node debate. Each lesson has 1-2 laptop labs; every lab produces a number or a plan the learner can inspect.

### Cited Findings
- Configs, commands and features referenced in the labs are sourced in sections 3-13 (AQE/skew configs: [Spark tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html); Iceberg config/compose: [Iceberg quickstart](https://iceberg.apache.org/spark-quickstart/); DuckDB TPC-H/Iceberg: [TPC-H](https://duckdb.org/docs/2.0/core_extensions/tpch.html), [Iceberg ext](https://duckdb.org/docs/2.0/core_extensions/iceberg/overview.html); watermark/RTM: [Streaming APIs](https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html), [RTM](https://spark.apache.org/docs/latest/streaming/real-time-mode.html); Connect: [Spark Connect](https://spark.apache.org/docs/latest/spark-connect-overview.html)).

### Inferences
Proposed outline (synthesis, not sourced as a whole):

1. **Why big data systems exist (and when they don't)**: bytes, disks, scan math; scale-up vs scale-out; storage vs compute growth; the "one-percenter" questions.
   - Lab 1a: DuckDB CLI on 1 month, then 12 months of NYC yellow taxi Parquet: `SELECT count(*), avg(fare_amount) ... GROUP BY ...`; record wall time and bytes; extrapolate to 1 TB/10 TB with the scan formula.
   - Lab 1b: same query on a CSV copy (`COPY ... TO 'x.csv'`) to show the format effect before explaining it.
2. **GFS/HDFS and MapReduce: the ideas that survived**: blocks, replication, NameNode, data locality; map, shuffle (partition, sort, fetch), reduce; combiners; why every job writing to HDFS was slow.
   - Lab 2a: word count "MapReduce by hand" in Kotlin: split input into N chunks, map in parallel (coroutines/threads) to (word,1), hash-partition into R buckets written to temp files (the shuffle), sort/merge each bucket, reduce. Add a combiner and measure shuffle bytes before/after.
   - Lab 2b (optional): count the same in `sort | uniq -c` to show the single-machine baseline.
3. **Hive: SQL on files, partitions and the metastore**: schema-on-read, external tables, `dt=` partitions, pruning, metastore as catalog, its limits (no atomic multi-file commits, directory listing, small files).
   - Lab 3a: DuckDB `COPY (FROM taxi) TO 'lake/' (FORMAT parquet, PARTITION_BY (year, month))`; query with `hive_partitioning`; compare `EXPLAIN ANALYZE` for filtered vs unfiltered queries.
   - Lab 3b (optional): `apache/hive:standalone-metastore-4.2.1` container; register the directory as an external table from Spark (`enableHiveSupport`, `hive.metastore.uris`); then manually add a file mid-query to show there is no isolation.
4. **Columnar formats: Parquet internals, pushdown, ORC, Avro**: row groups/column chunks/pages/footer; encodings and compression; min/max stats; predicate pushdown and column pruning; sort order matters.
   - Lab 4a: `SELECT * FROM parquet_metadata('yellow_2024-01.parquet')` and `parquet_schema(...)`; find row groups, stats, encodings.
   - Lab 4b: write the same data unsorted vs sorted by `tpep_pickup_datetime`; run a time-range filter in Spark and DuckDB; compare files/row groups skipped and bytes read (Spark SQL tab "number of files read", "size of files read"; `explain()` `PushedFilters`).
5. **Spark execution model**: driver/executors, `local[*]`, lazy evaluation, DAG, jobs/stages/tasks, narrow vs wide, RDD lineage vs DataFrame plans.
   - Lab 5a: word count three ways in a Gradle Kotlin project (RDD `flatMap/mapToPair/reduceByKey`, DataFrame `split/explode/groupBy`, SQL); open the Spark UI, count jobs/stages/tasks, relate the stage boundary to the shuffle in Lab 2a.
   - Lab 5b: show laziness: build a long chain, nothing runs until `count()`; `explain(true)` shows parsed/analyzed/optimized/physical plans.
6. **The shuffle, partitioning and joins**: `Exchange`, hash vs range partitioning, `repartition` vs `coalesce`, `spark.sql.shuffle.partitions`, broadcast hash join vs sort-merge vs shuffled hash; hints.
   - Lab 6a: join taxi trips with the zone lookup table; `explain("formatted")` and find `BroadcastExchange`/`BroadcastHashJoin`; set `spark.sql.autoBroadcastJoinThreshold=-1` and find two `Exchange hashpartitioning` + `SortMergeJoin`; compare stage counts and time.
   - Lab 6b: vary `spark.sql.shuffle.partitions` (8, 200, 2000) with AQE off, then on; observe task counts and `AQEShuffleRead coalesced`.
7. **Optimizer, AQE, skew and caching**: Catalyst phases, whole-stage codegen (Tungsten), AQE features and thresholds, skew detection in the UI, salting, caching trade-offs.
   - Lab 7a: synthetic skew (one key with 30% of rows) joined to a medium table; AQE off: one straggler task in the Stages tab; AQE on with `skewJoin.skewedPartitionThresholdInBytes` lowered to fit laptop data: task split visible; then manual salting; compare.
   - Lab 7b: cache vs no-cache for a reused DataFrame; Storage tab; then show the cost of caching something used once.
8. **Spark 4.x for JVM engineers: Spark Connect, ANSI, VARIANT, pipe syntax**: client/server split; JVM client from Kotlin; what Connect cannot do (RDDs); ANSI behavior changes; VARIANT for JSON; Declarative Pipelines (demo).
   - Lab 8a: run `apache/spark:4.3.0-java21-python3` with `start-connect-server.sh`, port 15002; Kotlin app using `spark-connect-client-jvm` runs the Lab 6 query remotely.
   - Lab 8b: ANSI demo (`SELECT CAST('abc' AS INT)` errors; `try_cast` returns NULL); load raw JSON events with `parse_json` into VARIANT and query `variant_get`; rewrite a query in `|>` pipe syntax.
9. **Lakehouse tables with Iceberg**: why (atomic commits, snapshots, schema/partition evolution, hidden partitioning); metadata tree (metadata.json -> manifest list -> manifests -> data files); optimistic concurrency.
   - Lab 9a: Spark 4.1.4 + `iceberg-spark-runtime-4.1_2.13:1.12.0` with a local `hadoop` catalog; create `taxis` partitioned by `days(pickup_ts)`; insert 3 batches; `SELECT * FROM t.snapshots`, `t.files`, `t.manifests`, `t.history`; time travel `VERSION AS OF`/`TIMESTAMP AS OF`; `ALTER TABLE ADD COLUMN`, rename a column, change partition spec to `hours(...)`; `cat` the `metadata/*.metadata.json` and decode a manifest Avro.
   - Lab 9b: read the same table from DuckDB with `iceberg_scan` and `iceberg_snapshots`; confirm engine independence.
10. **Row-level changes, compaction and catalogs**: CoW vs MoR, delete files vs deletion vectors (v3), MERGE INTO, small files, `rewrite_data_files`, `expire_snapshots`; Delta Lake and Hudi comparison; DuckLake's SQL-metadata design; catalogs: HMS -> REST -> Polaris/Unity Catalog.
   - Lab 10a: docker compose from the Iceberg quickstart (REST fixture + RustFS); `MERGE INTO` with `write.merge.mode=merge-on-read` and format-version 3; inspect delete files/DVs in `t.files`; run `CALL system.rewrite_data_files(...)` and `expire_snapshots`; count files before/after.
   - Lab 10b: attach the same REST catalog from DuckDB (`ATTACH ... TYPE iceberg`) and insert a row; read it back in Spark; discuss what the catalog guarantees.
11. **Streaming: Structured Streaming, watermarks, Kafka to lakehouse (Flink in context)**: event vs processing time, windows, watermarks, output modes, checkpoints, exactly-once requirements, Real-time Mode; Flink 2.x positioning.
    - Lab 11a: Kafka (Docker, single-node KRaft) + a Kotlin producer replaying taxi trips with event timestamps (including deliberately late events); Spark job: `withWatermark("pickup_ts","10 minutes")` + 5-minute windows, `update` mode to console, then `append` to an Iceberg table; observe late-event handling and checkpoint restart.
    - Lab 11b (stretch): same stateless filter with `Trigger.RealTime(...)` Kafka -> Kafka, compare latency with micro-batch.
12. **Engines and architecture: DuckDB vs Spark vs Trino, and orchestration**: single-node vs distributed rubric; Trino over the Iceberg REST catalog; ClickHouse/Flink positioning; Airflow 3 assets; capstone architecture.
    - Lab 12a: TPC-H SF10 (DuckDB `dbgen`, export Parquet); run Q1/Q3/Q9 in DuckDB and in Spark `local[*]`; compare time and memory; discuss why Spark is slower on one machine and where the crossover is.
    - Lab 12b: `trinodb/trino` with an Iceberg catalog pointing at the Lesson 10 REST catalog; query the same table; optional Airflow 3 DAG (asset-triggered) that runs the compaction job.

### Gaps
- Lab timings are untested; the writer should run each lab on an M-series Mac with 16 GB RAM before publishing.
- Kafka image/config and Airflow local setup not researched.

---

## 15. Teaching notes (misconceptions, analogies that work, what to cut)

### Takeaway
Anchor everything to two levers (read fewer bytes; spread work across cores/machines) and one villain (the shuffle). Use backend-engineer analogies (Git, B-trees vs column stores, CAS commits, Kafka partitions). Cut Hadoop operations, Pig, Oozie, HBase, YARN tuning, RDD-level optimizations, Spark MLlib, and Scala.

### Cited Findings
- Iceberg commits are optimistic compare-and-swap of the metadata pointer with retry, giving serializable isolation; readers keep the snapshot they loaded (supports the "Git/CAS" analogy). — [Iceberg spec](https://iceberg.apache.org/spec/)
- Real-time Mode's trigger duration "is primarily a checkpoint interval, not a latency target" (a good "read the docs carefully" example). — [Real-time Mode docs](https://spark.apache.org/docs/latest/streaming/real-time-mode.html)
- The "one-percenter" questions give a ready-made discussion prompt for when a cluster is warranted. — [MotherDuck](https://motherduck.com/blog/big-data-is-dead/)

### Inferences
- Analogies that work for a Java/Kotlin backend engineer:
  - Spark DataFrame = a lazy `java.util.stream` pipeline whose terminal operation (`count`, `write`) triggers a distributed query plan; `explain()` = the SQL `EXPLAIN` they already know.
  - Shuffle = `groupingBy` across machines: every row moves over the network to the node that owns its key (like Kafka partitioning by key).
  - Broadcast join = loading a small lookup table into a `HashMap` on every worker.
  - Skew = one hot partition in Kafka or one hot shard in a sharded DB.
  - Iceberg = Git for tables: data files are blobs, metadata.json is a commit, the catalog is the branch ref, a commit is CAS on the ref; compaction = `git gc`-ish rewrite; expire_snapshots = pruning history.
  - Parquet footer = an index at the end of the file; row-group stats = a sparse min/max index (like BRIN in Postgres).
  - Spark Connect = gRPC client to a query server (like a JDBC driver, but sending DataFrame plans).
  - Watermark = a timeout on how long you hold state for a key/window, same trade-off as a session cache TTL.
- Misconceptions to name explicitly in-lesson (each has a lab): in-memory never spills; more partitions faster; collect() is safe; cache everything; Hadoop is required; lake = folder of files; Iceberg is an engine; you need a cluster for 100 GB; exactly-once is automatic; partition by high-cardinality keys.
- What to cut or compress: HDFS/YARN administration, MapReduce Java API (show 10 lines only), Pig, Oozie, Sqoop, Flume, HBase, Impala, Hive LLAP/Tez internals, Spark Streaming DStreams (legacy), MLlib, GraphX, SparkR (deprecated), Scala language, detailed Hudi internals, Kubernetes deployment of Spark (mention only), cloud-vendor products (Databricks/Snowflake/EMR) beyond one comparison slide.
- What to keep even though it's "old": the shuffle, data locality as "move compute to data / read less", Hive-style partitions, the metastore idea, RDD lineage as the fault-tolerance model.
- Pacing: Lessons 5-7 (Spark engine and performance) are the core value for a backend engineer and deserve the most lab time; Lessons 1-3 can be shorter reading lessons with one lab each.
- Version hygiene: state "as of Nov 2026" in every version table; Spark is now quarterly, DuckDB has a fixed calendar, Iceberg ships ~2-3 minors/year.

### Gaps
- Analogies and cut-list are editorial judgments, not sourced.

---

## Verified URLs

### Fetched this session and loaded (content confirmed)
- https://spark.apache.org/news/index.html
- https://spark.apache.org/releases/spark-release-4-3-0.html
- https://spark.apache.org/releases/spark-release-4-2-0.html
- https://spark.apache.org/releases/spark-release-4.1.0.html (note: `spark-release-4-1-0.html` returns 404)
- https://spark.apache.org/releases/spark-release-4-0-0.html
- https://spark.apache.org/docs/latest/ (shows 4.3.0 docs)
- https://spark.apache.org/docs/latest/spark-connect-overview.html
- https://spark.apache.org/docs/latest/sql-performance-tuning.html
- https://spark.apache.org/docs/latest/api/python/getting_started/install.html
- https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html (stub that points to the split guide)
- https://spark.apache.org/docs/latest/streaming/index.html
- https://spark.apache.org/docs/latest/streaming/apis-on-dataframes-and-datasets.html
- https://spark.apache.org/docs/latest/streaming/real-time-mode.html
- https://hub.docker.com/v2/repositories/apache/spark/tags?page_size=30 (Docker Hub API JSON; human page is hub.docker.com/r/apache/spark, not fetched)
- https://hub.docker.com/v2/repositories/apache/hive/tags?page_size=15 (Docker Hub API JSON)
- https://iceberg.apache.org/releases/
- https://iceberg.apache.org/spec/
- https://iceberg.apache.org/spark-quickstart/
- https://iceberg.apache.org/multi-engine-support/
- https://github.com/delta-io/delta/releases
- https://github.com/delta-io/delta/releases/tag/v4.0.0
- https://hudi.apache.org/releases/download
- https://hudi.apache.org/releases/release-1.2
- https://hive.apache.org/general/downloads/
- https://duckdb.org/release_calendar
- https://duckdb.org/news/
- https://duckdb.org/2026/10/21/announcing-duckdb-200
- https://duckdb.org/docs/2.0/core_extensions/iceberg/overview.html (the `/docs/stable/...` URL is a redirect stub to this)
- https://duckdb.org/docs/2.0/core_extensions/tpch.html (the `/docs/stable/...` URL is a redirect stub to this)
- https://flink.apache.org/downloads/
- https://flink.apache.org/2025/03/24/apache-flink-2.0.0-a-new-era-of-real-time-data-processing/
- https://airflow.apache.org/announcements/
- https://airflow.apache.org/blog/airflow-three-point-oh-is-here/
- https://polaris.apache.org/
- https://github.com/unitycatalog/unitycatalog/releases
- https://www.unitycatalog.io/
- https://github.com/Kotlin/kotlin-spark-api
- https://trino.io/docs/current/release.html
- https://trino.io/docs/current/installation/deployment.html
- https://motherduck.com/blog/big-data-is-dead/
- https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- https://parquet.apache.org/docs/file-format/
- https://parquet.apache.org/docs/file-format/configurations/
- https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf (Lakehouse paper; page 1 read)
- https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia (RDD paper page; PDF link nsdi12-final138.pdf listed, not fetched)
- https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/
- https://research.google/pubs/the-google-file-system/

### Seen only in search results (not fetched; verify before linking)
- https://polaris.apache.org/blog/2026/02/19/apache-polaris-graduates-to-top-level-project/
- https://news.apache.org/?p=7401 (ASF: Polaris and Gluten graduate)
- https://www.ducklake.select/ (and announcement at ducklake.select/2026/04/13/ducklake-10/)
- https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2026/
- https://github.com/minio/MinIO ; https://dev.to/alexandrev/minio-in-maintenance-mode-what-it-means-for-the-community-edition-oem-users-and-open-source-3o4j
- https://www.opensourceforu.com/2026/03/apache-elevates-open-source-projects-gluten-and-polaris-to-top-level-status/
- https://duckdb.org/2026/04/13/announcing-duckdb-152
