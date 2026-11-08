# Data Models and Query Languages (concept curriculum, state as of 7 November 2026)

Conventions used throughout:
- "DDIA 2e p.N (bk M)" means Kleppmann and Riccomini, *Designing Data-Intensive Applications*, 2nd ed., chapter 3, from the local PDF at `/Users/arunav/Documents/learn/books & pdfs/architecture and software design/Designing Data-Intensive Applications ... .pdf`. N is the 1-based PDF page and M is the printed page (PDF page minus 24). All DDIA content is paraphrased.
- "Prior notes" means the earlier product-organized research in `research_notes/Systems course curriculum research/` (mainly `rdbms_sql.md` and `nosql.md`). I reused their version checks and cite the primary URLs they used. Read `rdbms_sql.md` for PostgreSQL 18 syntax and exercises. These notes add concept framing, history, the graph, event and dataframe models, and the 2026 status of standards.
- **Changed since the brief was written.** MongoDB's current release is **9.0** (GA 28 Sep 2026), not 8.x. DuckDB is now **2.0** (21 Oct 2026). Polars is **2.x** (2.0.0 on 6 Oct 2026). pandas is **3.x**. EventStoreDB is now **KurrentDB 26.x**. Axon Framework is **5.x**. PostgreSQL 19 is not GA yet (RC1; GA planned 19 Nov 2026), and its SQL/PGQ support was **reverted** before release.

## 1. The relational model from first principles, relational algebra, declarative SQL, normalization vs denormalization, the object-relational mismatch and ORMs

### Takeaway
Codd's 1970 relational model was a fix for *data dependence*. Programs written against 1960s hierarchical and network databases broke whenever the stored order, the indexes or the access paths changed. Relations, which are unordered sets of tuples, plus a high-level language let an optimizer choose access paths, and that is why SQL is declarative. Normalization is a trade between write cost and read cost, not a virtue in itself. ORMs remove boilerplate, but they hide round-trips (N+1) and cached object identity (identity map) that learners need to measure.

### Cited Findings
**Codd 1970 and why the relational model exists**
- Codd, "A Relational Model of Data for Large Shared Data Banks," *CACM* 13(6):377–387, June 1970. The abstract names three dependencies that systems of the day failed to remove: *ordering dependence*, *indexing dependence* and *access path dependence*. The goal was data independence, meaning programs keep working when the internal representation changes. Programs that relied on a file's stored order, on named index chains, or on tree or network structure broke when those changed. — [ACM DOI](https://doi.org/10.1145/362384.362685); text copy: [UMich EECS 584 PDF](https://web.eecs.umich.edu/~michjc/eecs584/Papers/codd_1970.pdf) (wording synthesized from search results; the Penn copy I fetched is a scanned image with no text layer)
- In the relational model, data is organized into relations (tables), and each relation is an *unordered* collection of tuples (rows). Many people doubted it could be implemented efficiently. By the mid-1980s RDBMSs and SQL were the default tools. — DDIA 2e p.91 (bk 67)
- Competing models came and went: network and hierarchical (1970s to early 1980s), object databases (late 1980s to early 1990s), XML databases (early 2000s), then NoSQL in the 2010s. SQL instead absorbed XML, JSON and graph data. — DDIA 2e p.91 (bk 67); the book cites Stonebraker and Hellerstein, "What Goes Around Comes Around" (2005), in *Readings in Database Systems* 4th ed.
- Codd's original paper allowed "nonsimple domains", where a value can itself be a nested relation. DDIA compares this to the JSON/XML support SQL added more than 30 years later. — DDIA 2e p.108 (bk 84)
- The 2024 sequel (Stonebraker and Pavlo, *SIGMOD Record* 53(2):21–37, June 2024) concludes that non-SQL, non-relational systems are either niche or turning into SQL/relational systems. By the end of the 2010s almost every NoSQL DBMS had added a SQL-like interface: DynamoDB PartiQL, Cassandra CQL, Aerospike AQL, Couchbase SQL++. MongoDB added SQL for Atlas in 2021. — [Stonebraker & Pavlo 2024 PDF](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf); [SIGMOD Record page](https://sigmodrecord.org/2024/06/30/what-goes-around-comes-around-and-around)

**Declarative querying**
- A declarative language states the pattern of the result (conditions, sorting, grouping, aggregation) and not the algorithm. The optimizer picks indexes, join algorithms and order. This lets the engine get faster, or run the query in parallel across cores and machines, without anyone changing the query. — DDIA 2e p.90 (bk 66)
- Stonebraker and Pavlo argue that high-level languages are almost always preferred to record-at-a-time notations, because they need less code and give more data independence. Early optimizers were poor and have since improved a great deal, but the optimizer is still the hardest part of a DBMS to build. They suspect that difficulty is why early NoSQL systems skipped SQL. — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.3

**Normalization vs denormalization**
- Running example: a résumé stores `region_id` rather than the text "Washington, DC". Benefits: consistent spelling, no ambiguity, one place to update, localization, and better search (the region list can encode "East Coast"). An ID has no human meaning, so it never needs to change. Duplicating human-meaningful text means every copy must be updated, which costs more code, more writes and more disk, and risks inconsistency. — DDIA 2e p.96 (bk 72)
- Rule of thumb: normalized data is faster to write and slower to read (joins). Denormalized data is faster to read and costlier to write. Denormalization is a form of *derived data* and needs a process to keep the copies in sync. A crash halfway through updating the copies leaves them inconsistent unless multi-object atomic transactions are available. OLTP tends to suit normalization; analytics tends to suit denormalization. At small or moderate scale, normalized is usually best. — DDIA 2e p.98 (bk 74)
- Concrete counter-example to "joins don't scale": X (Twitter) materialized timelines store only post IDs, sender IDs and reply/repost markers. Every read still *hydrates* IDs into content and profiles, which is an application-side join. Like counts and profile photos change too fast to denormalize. Hydration parallelizes well, and its cost does not depend on follower counts. — DDIA 2e p.98–99 (bk 74–75), citing Krikorian, "Timelines at Scale," QCon 2012
- Stonebraker and Pavlo restate the 1970s case against pre-joining: (1) it duplicates data unless the join is one-to-many, (2) pre-joins are not necessarily faster, and (3) you lose data independence. — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.3

**Object-relational mismatch, ORMs, N+1, identity map**
- "Impedance mismatch" is borrowed from electronics. It names the translation layer between objects and tables, rows and columns. — DDIA 2e p.92 (bk 68)
- Criticisms of ORMs, using ActiveRecord and Hibernate as examples:
  - They cannot fully hide either model.
  - Analytics teams still work on the relational schema.
  - Most ORMs support only relational OLTP databases.
  - Generated schemas can be awkward.
  - They make inefficient queries easy to write.
  
  Benefits: less boilerplate, query-result caching, and migration tooling. — DDIA 2e p.92–93 (bk 68–69), citing Fowler "OrmHate" (2012) and Mihalcea on N+1 with JPA/Hibernate (2023)
- N+1, defined: one query returns N comments with author IDs, and the ORM then issues one query per comment to fetch each author. That is N+1 round-trips where one join would do. The fix is to tell the ORM to fetch the association eagerly or in batches. — DDIA 2e p.92–93 (bk 68–69)
- Document-database advocates claim that nesting removes N+1. Stonebraker and Pavlo answer that object and XML databases made the same claim. — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.3
- Identity Map (Fowler, *Patterns of Enterprise Application Architecture*): each object is loaded only once per session or unit of work, and a map from ID to object keeps lookups consistent. This is what Hibernate's persistence context (first-level cache) implements. — [Fowler PoEAA catalog: Identity Map](https://martinfowler.com/eaaCatalog/identityMap.html) (not fetched this session; standard reference)

**Where SQL departs from the pure model (misconception: "SQL is the relational model")**
- UNIQUE treats NULLs as distinct unless `NULLS NOT DISTINCT` is set (PostgreSQL 15+). SQL:2023 made this behavior an explicit option (feature F292) and left the default implementation-defined. — [PG 18 CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html) (via prior notes); [Eisentraut, SQL:2023](https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new)
- `NOT IN` yields NULL, not true, when the subquery contains a NULL and no row matches. — [PG 18 Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html) (via prior notes)
- Without `ORDER BY`, rows come back in whatever order is fastest, so `LIMIT` without `ORDER BY` returns an unpredictable subset. — [PG 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html) (via prior notes)

### Inferences
- **Teaching arc (problem → simplest version → break → improvement):**
  1. *Problem.* The 1960s IMS/CODASYL programs navigated pointers, so changing storage broke code.
  2. *Simplest version.* A relation is a set of tuples over named domains, with no order and no pointers.
  3. *Break.* Without a declarative language and an optimizer it would be slow, which is why many doubted it in the 1970s.
  4. *Improvement.* Declarative SQL plus cost-based optimizers. Fifty years of optimizer engineering is the moat.
- **Relational algebra to teach** (background knowledge, not re-verified this session): selection σ, projection π, Cartesian product ×, union ∪, difference −, and rename ρ are the primitive set. Join ⋈, intersection and division are derived. Codd's 1970 paper itself defines permutation, projection, join, composition and restriction. It also introduces "normal form" as removing nonsimple domains, which later became 1NF, and discusses redundancy and consistency. Codd 1971–72 and Boyce–Codd 1974 added 2NF, 3NF and BCNF. Check these details against the UMich copy before quoting.
- **SQL is not set-relational.** It uses bags (duplicates unless DISTINCT), three-valued logic with NULL, and ORDER BY on results. These deviations are the source of the classic NULL and ordering bugs listed above. This is a good misconception slide.
- **Normalization misconceptions:**
  - "Normalize everything." DDIA shows that denormalized derived views are fine when you own the update path.
  - "Joins don't scale." The X timeline example disproves it.
  - "Denormalization is always faster to read." Stonebraker and Pavlo point (2) disproves it.
  - The useful framing is that a denormalized copy is a cache with an invalidation problem.
- **Normalization break, with a concrete number to stage in a lab.** Copy an organization name into 100,000 résumé rows. Renaming it becomes 100,000 row writes instead of 1. Kill the process halfway and count the rows left inconsistent.
- **N+1 numbers.** With N = 1,000 and roughly 0.3–1 ms per localhost round-trip, N+1 costs about 0.3–1 s, against one join of a few ms. Learners should measure this rather than take the figure on trust (see the labs).
- **Identity-map anomaly.** Inside one session, loading the same ID twice returns the same object instance. Another transaction's update is invisible to that session until refresh. This is a stale-read anomaly the learner can reproduce.

### Gaps
- I could not machine-read Codd's 1970 paper in this session; the Penn PDF has no text layer. The operation list and normal-form claims above come from background knowledge.
- I did not fetch Fowler's Identity Map page or Hibernate 7 / JPA 3.2 docs. I did not verify current Hibernate or Exposed defaults for lazy loading or batch fetching. Prior notes list Exposed 1.6.1 and jOOQ 3.21.9.

## 2. The document model (MongoDB, PostgreSQL JSONB, SQL/JSON in SQL:2016/2023), schema-on-read vs schema-on-write, data locality, many-to-one and many-to-many relationships and joins

### Takeaway
The document model suits trees of one-to-many ("one-to-few") data that are loaded whole. It gives locality and a closer match to application objects. It struggles with many-to-one and many-to-many relationships, which need references and joins, with references to nested items, and with large or frequently updated documents. "Schemaless" really means schema-on-read. By 2026 the two worlds have largely converged: MongoDB 9.0 can enforce validation on every document, PostgreSQL has JSONB with `JSON_TABLE`, and SQL:2023 has a native JSON type.

### Cited Findings
**Model and motivation**
- Running example: a LinkedIn-style résumé. In relational form it is a `users` table plus `positions`, `education` and `contact_info` tables with foreign keys. In document form it is one JSON tree. Fetching the relational version takes several queries or a messy multi-way join. The JSON version keeps everything in one place, which is faster and simpler for this access pattern. — DDIA 2e p.93–95 (bk 69–71)
- One-to-many relationships that are small ("one-to-few") embed well. A celebrity post with many thousands of comments should not embed them all in one document. — DDIA 2e p.95 (bk 71)
- Shredding a document-like structure into many tables can produce cumbersome schemas and code. Document limits:
  - You cannot refer directly to a nested item; you have to say "the second position of user 251".
  - Many-to-one and many-to-many relationships need references.
  
  Reorderable lists are easy as a JSON array. Relational designs need integer renumbering, linked lists or fractional indexing. — DDIA 2e p.100, 104 (bk 76, 80)
- Many-to-many relationships are often queried in both directions. Storing ID references on both sides is denormalized and can drift. The normalized approach stores the relationship once and indexes both directions; document stores index fields inside arrays such as `positions[].org_id`. — DDIA 2e p.100–101 (bk 76–77)
- Joins in documents: some document DBs have none, so joins happen in application code. MongoDB has `$lookup` in its aggregation pipeline. — DDIA 2e p.97 (bk 73)
- The aggregation pipeline is about as expressive as a subset of SQL, with JSON syntax. DDIA's example counts shark sightings per month. — DDIA 2e p.107 (bk 83)

**Schema-on-read vs schema-on-write**
- "Schemaless" is misleading. The reading code assumes a structure, so there is an implicit schema that the database does not enforce. Schema-on-read is like dynamic type checking and schema-on-write like static type checking, and neither wins in general. — DDIA 2e p.104–105 (bk 80–81), citing Fowler "Schemaless Data Structures" (2013) and Awadallah (2009)
- Migration example: split `name` into `first_name`. With documents, write new documents in the new shape and handle old ones in code. With SQL, `ALTER TABLE ... ADD COLUMN ... DEFAULT NULL` is fast, but the `UPDATE` that rewrites every row is slow on large tables, and type changes usually copy the whole table. Online migration tools exist but are still hard to operate. You can mix the two: add the nullable column and fill it lazily at read time. — DDIA 2e p.105 (bk 81)
- Schema-on-read wins when data is heterogeneous: many object types, or structure dictated by external systems that may change. When all records share one structure, a schema documents and enforces it. — DDIA 2e p.105–106 (bk 81–82)
- **MongoDB 9.0 (GA 28 Sep 2026)** added a `constraint` validation level. Rules apply to all inserts and updates, and *every* document in the collection is guaranteed to satisfy them. MongoDB now also validates all ingested BSON by default (`net.wireObjectCheck` is deprecated). — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)
- MongoDB release index: 9.0 is the current stable release, 9.1 is upcoming, and 8.3, 8.0 and 7.0 are previous. — [MongoDB release notes index](https://www.mongodb.com/docs/manual/release-notes/) (via prior notes)

**Locality**
- A document is stored as one contiguous string (JSON, XML or BSON). That helps only if you need most of it at once. The DB usually loads the whole document and rewrites it on update, so keep documents small and avoid frequent small updates. — DDIA 2e p.106 (bk 82)
- Locality is not unique to documents. Spanner lets child rows be interleaved within a parent table. Oracle has multi-table index cluster tables. Bigtable/HBase column families serve the same purpose. — DDIA 2e p.106 (bk 82)
- MongoDB's own guidance: embedding makes operations on one document atomic. In most cases a distributed transaction costs more than single-document writes, so the denormalized embedded model stays optimal. — [MongoDB: embedding vs references](https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/) (via prior notes)
- MongoDB 9.0 query limits: a single query operation is capped at 1 GB or 20% of server memory, whichever is greater. The 100 MB per-stage limit and spill-to-disk behavior are unchanged. `$lookup`/`$graphLookup` now report peak expression memory in explain. Multi-document transactions are capped at 10,000 concurrent by default (`maxConcurrentMultiDocumentTransactions`). — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)

**Relational JSON and SQL/JSON standards**
- PostgreSQL has `json` (text) and `jsonb` (binary, decomposed), the containment operator `@>`, jsonpath, and GIN indexing with the `jsonb_ops` (default) and `jsonb_path_ops` operator classes. — [PG 18 JSON types](https://www.postgresql.org/docs/18/datatype-json.html) (via prior notes)
- PostgreSQL 17 added the SQL/JSON features `JSON_TABLE()` (in FROM), `JSON()`, `JSON_SCALAR()`, `JSON_SERIALIZE()`, `JSON_EXISTS()`, `JSON_QUERY()` and `JSON_VALUE()`. — [PG 17 release notes](https://www.postgresql.org/docs/17/release-17.html) (via prior notes)
- In SQL:2016, JSON was stored in character strings; this is now called T803 "String-based JSON". SQL:2023 added:
  - a native JSON data type (T801), with `WITH UNIQUE KEYS` (T802);
  - a *simplified accessor*, dot and array syntax defined in terms of `JSON_QUERY`/`JSON_VALUE` (T860–T864);
  - item methods such as `.integer()` and `.date()` (T865–T878);
  - JSON comparison, sorting and grouping (T879–T882).
  
  — [Eisentraut, "SQL:2023 is finished" (4 Apr 2023)](https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new)
- Stonebraker and Pavlo:
  - Document DBMSs are essentially the 1980s object-oriented DBMSs and late-1990s XML DBMSs again.
  - Once NoSQL systems added SQL and ACID, the remaining differences are JSON support and "schema later".
  - They predict the two kinds of system will become effectively identical.
  
  — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.3. *Minor conflict:* they say the SQL standard added a JSON *data type* in 2016. Per Eisentraut, 2016 added JSON *functions over strings*, and the type came in SQL:2023.
- DuckDB 2.0 (21 Oct 2026) fully integrates a `VARIANT` type. It "shreds" common structure automatically, reads and writes shredded Parquet, and adds `variant_*` functions. — [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200.html). Spark 4.x also ships VARIANT. — prior notes `big_data.md`

### Inferences
- **Arc:**
  1. *Problem.* Objects are trees, and shredding them into many tables costs joins and code.
  2. *Simplest version.* One JSON blob per aggregate, fetched by key.
  3. *Break 1.* Many-to-one data (organization names, regions) gets duplicated, and a rename or new logo means touching every document.
  4. *Break 2.* Unbounded arrays (comments) grow until updates rewrite huge documents and hit the size limit.
  5. *Break 3.* There is no join, so the application does N+1.
  6. *Improvement.* References plus `$lookup` or application joins; bucket or outlier patterns; the hybrid relational model with JSONB columns, GIN indexes and JSON_TABLE.
- **Misconceptions:**
  - "No schema." It is schema-on-read, and since 9.0 MongoDB can even enforce validation on every document.
  - "Documents are always faster." True only for whole-document reads.
  - "JSONB is always better than json." jsonb drops key order and duplicate keys and costs parse time on write.
  - "Document DBs can't join." `$lookup` exists, but it is not a cost-based multi-way join optimizer.
- **Where the hybrid breaks.** JSONB statistics are coarse, so the planner misestimates selectivity of predicates inside JSONB. Learners can observe this in `EXPLAIN ANALYZE` as an estimated-vs-actual row gap. This is background knowledge; measure it in the lab rather than asserting it.
- DDIA does not cover MongoDB's 16 MB BSON document limit or validation levels. Both are worth adding for a "where it breaks" number.

### Gaps
- MongoDB's 16 MB maximum BSON document size is well known but I did not re-fetch the [MongoDB limits page](https://www.mongodb.com/docs/manual/reference/limits/) this session. The 9.0 notes do not mention any size change.
- I did not confirm whether PostgreSQL 18 or 19 implements the SQL:2023 JSON type (T801) or the simplified accessor. Prior notes found neither in the PG18/19 release notes, so assume no.
- I did not verify MongoDB 9.0's vector search changes or the Atlas SQL interface status in 2026.

## 3. Wide-column and key-value as data models (Cassandra CQL partition/clustering keys, DynamoDB single-table design), time-series models, vectors as a data type

### Takeaway
Key-value is the simplest model: a binary relation (key, opaque value). Wide-column ("column-family") is a document model limited to one level of nesting and organized around a partition key. It is not columnar storage. Both make the *access path the schema*, so you model queries first. The breaks are concrete numbers: per-partition throughput ceilings (DynamoDB 1,000 WCU / 3,000 RCU), item and partition size limits (400 KB, about 100 MB guidance), and queries that cannot use the key. Time-series and vectors are mostly *specialized partitioning plus indexes* inside existing models, not new models.

### Cited Findings
**Key-value**
- The KV model represents a binary relation (key, value). The value is usually an opaque blob the DBMS cannot see, and most KV stores offer only get/set/delete. Examples:
  - Distributed: Memcached, Redis, Dynamo (2007).
  - Embedded: BerkeleyDB, LevelDB, and RocksDB (Meta's fork of LevelDB).
  
  — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.2
- KV becomes risky once records have several fields. The application must parse values, there are no secondary indexes, and joins or multi-gets happen in application code. Several KV stores grew into record stores with semi-structured values (DynamoDB, Aerospike). An RDBMS can emulate KV with no changes, but turning a KV store into something richer is hard. — same, §2.2
- DDIA 2e chapter 3 does not treat key-value or wide-column as separate data models. Bigtable-style column families appear only as a locality mechanism. — DDIA 2e p.106 (bk 82). (Partitioning and sharding of KV data are in DDIA ch. 7, p.279ff.)

**Wide-column / column-family**
- "Column-family is not a columnar data model." It reduces the document model to one level of nesting: relation-like, with optional attributes per record and cells that can hold arrays. Lineage: Bigtable (Google), then Cassandra and HBase, which copied Bigtable's lack of joins and secondary indexes. Cassandra replaced its Thrift API with CQL. HBase recommends Phoenix for SQL. The authors call the category a niche that exists mostly because of Google. — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.4, §2.9
- Cassandra modeling is query-first: design one table per query.
  - Partition key columns support only equality.
  - Range predicates are allowed only on clustering columns, which also set the sort order within a partition.
  - Avoid unbounded partitions by adding a time bucket to the partition key. At 100 writes/s, hourly buckets reach about 18 MB per partition.
  - Community guidance is to keep partitions roughly 10–100 MB and below 100 MB.
  
  — [AxonOps Cassandra data modeling](https://docs.axonops.com/data-platforms/cassandra/data-modeling); [opensource.com (2020)](https://opensource.com/article/20/5/apache-cassandra) (community guidance, not Apache docs)
- Cassandra versions: 5.0.9 GA (7 Aug 2026), maintained until 8.0. Cassandra 5.0 added Storage-Attached Indexes (SAI) and a vector type with similarity functions. 6.0 is in alpha (`6.0-alpha2` image) with Accord multi-partition transactions, opted into per table. — [Cassandra downloads](https://cassandra.apache.org/_/download.html); [Cassandra What's New](https://cassandra.apache.org/doc/latest/cassandra/new/index.html); [Instaclustr on Accord (2026-04-24)](https://www.instaclustr.com/blog/apache-cassandra-6-accord-transactions-what-you-need-to-know/) (via prior notes)
- Secondary indexes, in Kleppmann's terms: local (document-partitioned) indexes such as Cassandra SAI and DynamoDB LSIs mean scatter-gather reads. Global (term-partitioned) indexes such as DynamoDB GSIs mean asynchronous updates and possibly stale index reads. — DDIA 2e ch.7 p.292–294 (via prior notes)

**DynamoDB and single-table design**
- Each partition delivers at most 3,000 RCU and 1,000 WCU. A single hot item key cannot exceed that ceiling, so load must be spread across key values, for example with write sharding by suffix. — [AWS: partition key design](https://docs.amazonaws.cn/en_us/amazondynamodb/latest/developerguide/bp-partition-key-design.html); [AWS: warm throughput scenarios](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/warm-throughput-scenarios.html); [re:Post (community)](https://repost.aws/questions/QUefwDuOu_TGyHK8vFxyykFA/how-to-increase-the-maximum-ddb-table-throughput-setting-per-partition)
- Capacity units: 1 WCU is one write per second of up to 1 KB, and 1 RCU is one strongly consistent read per second of up to 4 KB. The maximum item size is 400 KB. — [AWS docs via search summary](https://docs.amazonaws.cn/en_us/amazondynamodb/latest/developerguide/bp-partition-key-design.html); item size from [community wiki](https://github.com/utkaln/dynamodb-helloworld/wiki/Dynamo-DB-Best-Practices) (official quota page not fetched)
- Single-table design (DeBrie, 5 Feb 2020): put heterogeneous entities in one table with generic `PK`/`SK` attributes, so that one `Query` returns pre-joined item collections (for example an account and its recent payments). DeBrie remained a strong proponent for most DynamoDB use cases. — [Alex DeBrie](https://www.alexdebrie.com/posts/dynamodb-single-table/) (via prior notes)
- Since 19 Nov 2025, GSIs accept multi-attribute composite keys: up to 4 partition-key and 4 sort-key attributes, with sort-key attributes filtered left to right. Hand-concatenated keys such as `STATUS#DATE` are no longer needed. DynamoDB native vector search went GA on 5 Aug 2026. — [AWS What's New 2025-11](https://aws.amazon.com/about-aws/whats-new/2025/11/amazon-dynamodb-multi-attribute-composite-keys-global-secondary-indexes/); [AWS What's New 2026-08](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-dynamodb-vector-search/) (via prior notes)

**Time-series**
- InfluxDB 3:
  - A database holds tables, and each table has *tags*, which are string metadata identifying the source, and *fields*, which are measured values.
  - A row's primary key is the timestamp plus the tag set.
  - The first write fixes column order permanently.
  - Wide, sparse schemas are discouraged because the engine must evaluate many null columns.
  
  — [InfluxDB 3 Core schema design](https://docs.influxdata.com/influxdb3/core/write-data/best-practices/schema-design)
- A TimescaleDB hypertable looks like an ordinary PostgreSQL table but partitions automatically into time-based chunks, optionally also by space. Each chunk has its own copy of every index. Smaller chunks suit high ingest and larger ones suit long retention. Distributed hypertables were sunset (around 2.14). — [OneUptime blog, Jan 2026](https://oneuptime.com/blog/post/2026-01-26-timescaledb-hypertables/view) (third-party; verify on Tiger Data docs)
- MongoDB 9.0 stores time-series collections as a single namespace with compressed buckets; they are no longer writable non-materialized views. Clusters with more than 5,000 time-series collections in one database may upgrade slowly. — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)

**Vectors as a data type**
- Stonebraker and Pavlo:
  - Vector DBMSs are essentially document DBMSs with specialized ANN indexes. Their words: "a feature, not the foundation of a new system architecture."
  - Within a year of ChatGPT (late 2022), major RDBMSs added vector indexes, for example Oracle, SingleStore, Rockset and ClickHouse in 2023. Most integrated libraries (pgvector, DiskANN, FAISS) rather than writing their own.
  - They predict vector DBMSs will turn relational, as document DBMSs did.
  
  — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.7
- SQL Server 2025 has a native `VECTOR` type stored as float32, with a maximum of 1,998 dimensions. Search uses `VECTOR_DISTANCE('cosine'|'euclidean'|'dot', ...)`. `CREATE VECTOR INDEX` (DiskANN) was in preview behind `PREVIEW_FEATURES`. — [DbVisualizer: SQL Server VECTOR](https://www.dbvis.com/thetable/sql-server-vector-data-type-search-and-indexing/)
- pgvector is an extension, not a built-in type. It offers HNSW and IVFFlat indexes. The latest tag is v0.8.7, which supports PostgreSQL 13–18. — [pgvector GitHub](https://github.com/pgvector/pgvector) (tags checked via `gh` this session); [SQLServerCentral comparison](https://www.sqlservercentral.com/blogs/ai-in-sql-server-vs-postgresql-vector-search-embeddings-and-rag-compared)
- DDIA covers vector embeddings as an index type in ch. 4 ("Vector Embeddings", p.171 / bk 147), not in the data-model chapter. — DDIA 2e outline

### Inferences
- **KV arc:**
  1. *Problem.* A cache or session store needs predictable sub-millisecond access at scale.
  2. *Simplest version.* A hash map from key to blob.
  3. *Break.* The second access pattern ("all sessions for user X") forces a scan or a hand-maintained index. Partial updates require read-modify-write.
  4. *Improvement.* Structured values, sort keys and secondary indexes. At that point the KV store is a document or wide-column store.
- **Wide-column arc:**
  1. *Simplest version.* `PRIMARY KEY ((sensor_id), ts)`.
  2. *Break.* One busy sensor grows a partition without bound. Cassandra's guidance is about 100 MB, and at 100 writes/s a day-long partition is about 430 MB by the 18 MB/hour arithmetic.
  3. *Improvement.* `PRIMARY KEY ((sensor_id, day), ts)`.
  4. *Second break.* Now "last 7 days" means 7 partition reads. Cross-partition queries need SAI (scatter-gather) or a second table.
- **DynamoDB arithmetic.** A 400 KB item costs 400 WCU per write, so a single partition can absorb only about 2.5 such writes per second. Large items amplify hot partitions. This is my own arithmetic from the cited unit sizes.
- **Misconceptions:**
  - "Wide-column = columnar." False (Stonebraker and Pavlo).
  - "NoSQL has no schema." DynamoDB's key schema and Cassandra's typed columns are schemas.
  - "Single-table design is mandatory." It optimizes known access patterns at the cost of ad-hoc queries and evolvability. Multi-attribute GSI keys (2025) remove one of its old hacks.
  - "Vector DB is a new model." It is a column type plus an approximate index, and approximate means recall below 1.0, which is measurable.
- Time-series is best taught as a *workload shape*: append-mostly, time-ordered, aged out. The answers are time partitioning, compression and retention, available in a relational extension (Timescale), a document store (MongoDB time-series) or a dedicated engine (InfluxDB 3).

### Gaps
- I did not fetch the official DynamoDB quotas page for the 400 KB limit (only a community wiki), nor the official Apache Cassandra partition-size guidance (only community docs).
- MySQL 9.0's `VECTOR` type and Oracle's `VECTOR` type (introduced in 23ai) came up in search snippets, but I did not reach a primary page for either.
- I did not verify TimescaleDB's current version or the Tiger Data rename specifics from official docs.

## 4. Analytics schemas: star and snowflake schemas, fact and dimension tables, slowly changing dimensions, one-big-table

### Takeaway
Dimensional modeling (Kimball) exists because analysts query events: one narrow, very long fact table of "what happened", joined many-to-one to wide dimension tables of "who, what, where, when". Snowflaking normalizes dimensions. One-big-table pre-joins everything, which is cheap in columnar engines. Slowly changing dimensions (SCD types 0–7) are the answer when dimension attributes change and history matters. Type 2 (add a new row with a surrogate key) is the one to teach deeply.

### Cited Findings
- Warehouses are usually relational. The conventions are the star schema, the snowflake schema, dimensional modeling (Kimball and Ross, *The Data Warehouse Toolkit*, 3rd ed., 2013) and one big table (OBT). ETL translates operational data into them. — DDIA 2e p.101 (bk 77)
- A fact table row is an event (a purchase, a page view). Some columns are attributes such as price and cost. Others are foreign keys to dimension tables, which answer who, what, where, when, how and why. Dates are often a dimension too, to encode holidays. Facts are kept as individual events for maximum flexibility, so fact tables become huge: many petabytes at large enterprises. — DDIA 2e p.101–103 (bk 77–79)
- A snowflake schema breaks dimensions into sub-dimensions (brand, category) and is more normalized. Analysts often prefer the simpler star. Tables are wide: fact tables often exceed 100 columns, sometimes several hundred. — DDIA 2e p.103 (bk 79)
- Star schemas are mostly many-to-one. A multi-item basket is not modeled explicitly; it shows up as separate fact rows that share customer, store and timestamp. — DDIA 2e p.103 (bk 79)
- OBT folds dimension attributes into the fact table, precomputing the join. It uses more storage and sometimes queries faster. Denormalization is harmless here because the data is a mostly immutable historical log. — DDIA 2e p.103 (bk 79), citing Kaminsky, Fivetran (2022)
- Kimball's technique catalog lists:
  - the four-step dimensional design process and grain declaration;
  - additive, semi-additive and non-additive facts;
  - fact table types: transaction, periodic snapshot, accumulating snapshot and factless;
  - conformed dimensions;
  - surrogate keys and degenerate, junk, snowflaked and outrigger dimensions;
  - multivalued dimensions with bridge tables;
  - SCD types 0 (retain original), 1 (overwrite), 2 (add new row) and 3 (add new attribute).
  
  — [Kimball Group: Dimensional Modeling Techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- Kimball Design Tip #152 (Margy Ross, 5 Feb 2013) covers the advanced types:
  - **Type 0.** The attribute never changes (original values, durable IDs, most date attributes).
  - **Type 4.** Volatile attributes move to a mini-dimension with its own surrogate key, and the fact table carries both keys.
  - **Type 5.** Type 4 plus a type-1 "current profile" key overwritten on the base dimension.
  - **Type 6.** Type 2 rows plus current-value columns overwritten on all rows of the durable key, so facts can be grouped "as was" or "as is".
  - **Type 7.** The fact table carries both the type-2 surrogate key and the durable key, which gives type-6 behavior without overwriting.
  
  — [Kimball DT #152](https://www.kimballgroup.com/2013/02/design-tip-152-slowly-changing-dimension-types-0-4-5-6-7/)
- Event sourcing compared with a fact table: both collect past events. Fact rows share one set of columns and form an *unordered* collection. Event logs have many event types and their *order matters*. — DDIA 2e p.127 (bk 103)
- Spark 4.3.0 (30 Oct 2026) Declarative Pipelines support SCD Type 2 through "Auto CDC" (`CREATE FLOW ... AS AUTO CDC INTO`). The target must support DSv2 row-level operations, for example Iceberg. — [Spark 4.3.0 release](https://spark.apache.org/releases/spark-release-4-3-0.html) (via prior notes `big_data.md`)
- DDIA covers materialized views and data cubes as precomputed aggregates in ch. 4 ("Materialized Views and Data Cubes", p.167 / bk 143). — DDIA 2e outline

### Inferences
- **Arc:**
  1. *Problem.* Analysts ask "sales by brand by holiday week". OLTP schemas need 8-way joins and lock contention against production.
  2. *Simplest version.* A star: `fact_sales` plus `dim_product`, `dim_store`, `dim_date`, `dim_customer`.
  3. *Break.* A customer moves from Boston to Denver. Type 1 (overwrite) silently moves all their *past* sales to Denver.
  4. *Improvement.* Type 2 adds a row with `valid_from`/`valid_to`/`is_current` and a new surrogate key, and facts reference the surrogate key in effect at load time.
  5. *Next break.* "Show history under the current region" now needs type 6/7 (current-value columns or durable keys).
- **SCD2 in modern SQL.** PostgreSQL 18 temporal primary keys (`PRIMARY KEY (customer_id, valid_during WITHOUT OVERLAPS)`) can enforce that a customer's versions never overlap. MERGE with `RETURNING merge_action()` makes the close-old/insert-new step observable. This is my inference combining the PG18 and PG17 features in §8.
- **OBT vs star in columnar engines.** Columnar storage plus dictionary and run-length compression make repeated dimension strings cheap. OBT therefore often wins on scan speed, but it costs a rebuild whenever a dimension attribute is corrected. A lab can measure both with DuckDB 2.0.
- **Misconceptions:**
  - "Star schemas are denormalized OLTP." They are an analytic serving layer.
  - "Snowflake (the schema) relates to Snowflake (the company)." It doesn't.
  - "SCD2 = audit log." SCD2 keeps the history of dimension attributes, not every change event.

### Gaps
- I did not fetch Kimball's full definitions of SCD types 1–3 (the catalog page lists only titles). The behaviors given are the standard ones: overwrite, add a row, add a "prior value" column.
- No 2026 vendor-neutral data on OBT vs star performance was found beyond the 2022 Fivetran post that DDIA cites.

## 5. Graph models: property graphs and Cypher (Neo4j), ISO GQL (2024), SQL/PGQ in SQL:2023 and who ships it as of 2026, recursive CTEs, RDF/SPARQL, Datalog (Datomic, Soufflé, CodeQL), GraphQL

### Takeaway
Graphs win when many-to-many relationships dominate and queries traverse a *variable* number of hops. SQL needs a recursive CTE for that, about 31 lines where Cypher takes 4. ISO GQL (April 2024) standardized a Cypher-like language, and SQL/PGQ (SQL:2023 Part 16) puts the same pattern syntax inside SQL through `GRAPH_TABLE`. As of November 2026, SQL/PGQ ships in Oracle (23ai/26ai), Google Spanner Graph, and DuckDB via the community `duckpgq` extension. PostgreSQL does **not** ship it: it was reverted from PG19 Beta 4. GQL is implemented by Neo4j (Cypher 25, most mandatory features), Spanner Graph and Microsoft Fabric Graph. GraphQL is not a graph database language.

### Cited Findings
**Property graph model and Cypher**
- A graph has vertices and edges. Representations:
  - *Adjacency list*: good for traversal.
  - *Adjacency matrix*: good for ML.
  
  Graphs also unify heterogeneous data, as in Facebook's single typed graph and search-engine knowledge graphs. — DDIA 2e p.108–109 (bk 84–85)
- Property graph definition:
  - A vertex has an ID, a label, outgoing and incoming edges, and properties.
  - An edge has an ID, a tail vertex, a head vertex, a label and properties.
  - It can be modeled as two relational tables (vertices, edges) with jsonb properties and indexes on both `tail_vertex` and `head_vertex`.
  
  The edges table generalizes a many-to-many join table to many relationship types. — DDIA 2e p.110–111 (bk 86–87), Example 3-3
- Limitation: an edge joins only two vertices. N-ary relationships need an intermediate vertex or a hypergraph. Strength: evolvability, for example adding allergen and food vertices without migrating anything. — DDIA 2e p.112 (bk 88)
- Cypher originated at Neo4j and became openCypher. It is supported by Memgraph, KùzuDB, Amazon Neptune and Apache AGE (on PostgreSQL). The canonical query is "people born in the US who live in Europe", using `-[:WITHIN*0..]->`. A planner can run it from either end. — DDIA 2e p.112–114 (bk 88–90)
- Neo4j uses calendar versioning (YYYY.MM.PATCH) since January 2025. 2026.10.0 shipped on 20 Oct 2026 and 2026.10.1 on 23 Oct. 5.26 is the LTS. Cypher 5 has been frozen since 2025.06; new features go to Cypher 25, and from 2026.02 the default config sets `db.query.default_language=CYPHER_25`. — [Neo4j 2026.10 release notes](https://neo4j.com/release-notes/database/neo4j-2026-10/); [Neo4j versioning blog](https://neo4j.com/blog/developer/neo4j-graph-database-versioning/) (via prior notes, from search results)
- Cypher 25 covers most mandatory GQL features and a substantial part of the optional ones.
  - Mandatory gaps: session management, transaction commands, graph expressions, schema reference, and reserved-word rules.
  - Behavioral differences: `sum()` over an empty table returns null in GQL but 0 in Cypher; `trim()` removes any whitespace in Cypher but only spaces in GQL.
  
  — [Neo4j Cypher 25: GQL conformance](https://neo4j.com/docs/cypher-manual/25/appendix/gql-conformance/); [unsupported mandatory features](https://neo4j.com/docs/cypher-manual/25/appendix/gql-conformance/unsupported-mandatory/)
- Cypher 25's GQL-style *quantified path patterns* repeat a path pattern within a range. The pattern must contain at least one relationship, and nesting is disallowed. The older variable-length `[*..]` syntax used in DDIA's examples still works but is not GQL-conformant. `REPEATABLE ELEMENTS` arrived in 2025.06 and `ACYCLIC` in 2026.03, both Cypher 25 only. — [Neo4j Cypher 25: variable-length paths](https://neo4j.com/docs/cypher-manual/25/patterns/reference/variable-length-paths/)

**GQL and SQL/PGQ: status in November 2026**
- ISO/IEC 39075:2024 (GQL) was published on 12 April 2024. It is the first new ISO database query language since SQL, and its core MATCH…RETURN syntax is largely Cypher-like. — [Wikipedia: GQL](https://en.wikipedia.org/wiki/Graph_Query_Language) (via prior notes). DDIA says GQL is not yet widely adopted. — DDIA 2e p.116 (bk 92)
- SQL:2023 (ISO/IEC 9075:2023) added Part 16 SQL/PGQ: `CREATE PROPERTY GRAPH` over existing tables, plus `GRAPH_TABLE(... MATCH ... COLUMNS ...)`. — [Eisentraut, SQL:2023](https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new)
- **Oracle.** Oracle AI Database 26ai supports SQL property graphs and SQL/PGQ through `GRAPH_TABLE`. The graph is only metadata over tables or views; no data is materialized. PGQL can also run against a SQL property graph, and SQL/PGQ works on graphs stored in a JSON column. A 2025 survey calls Oracle 23ai the first commercial system with SQL/PGQ. — [Oracle 26ai new features: graph](https://docs.oracle.com/en/database/oracle/oracle-database/26/nfcoa/graph.html); [Oracle-Base: SQL property graphs](https://oracle-base.com/articles/23/sql-property-graphs-and-sql-pgq-23); [Oracle Property Graph guide 26.1](https://docs.oracle.com/en/database/oracle/property-graph/26.1/spgdg/sql-property-graphs.html); [Graph DB survey, arXiv 2505.24758](https://arxiv.org/pdf/2505.24758)
- **Google Spanner Graph** implements both SQL/PGQ (9075-16:2023) and GQL (39075:2024). It supports GPML pattern matching and `GRAPH_TABLE` (feature G900), with schema defined by `CREATE PROPERTY GRAPH` over tables. It does not support GQL's `CREATE GRAPH TYPE` or GQL graph DML; only table DML is available. Repeatable-elements matching is the default. — [Spanner Graph ISO standards](https://docs.cloud.google.com/spanner/docs/graph/iso-standards)
- **Microsoft Fabric Graph** implements ISO/IEC 39075:2024 GQL, but not GQL `INSERT`; data is loaded through data management. — [Microsoft Learn: Fabric GQL conformance](https://learn.microsoft.com/fabric/graph/gql-conformance)
- **DuckDB.** SQL/PGQ comes from the *community* extension DuckPGQ (CWI), described as a research project under active development. Latest tag v0.10.1, last commit 26 Oct 2026.
  - Setup in DuckDB 2.0: `INSTALL duckpgq FROM community; LOAD duckpgq; SET active_grammar_extensions = ['duckpgq'];`.
  - Syntax: `CREATE PROPERTY GRAPH`, `GRAPH_TABLE` with `MATCH`, `ANY SHORTEST`, `path_length()`, and quantifiers `{1,3}` and `+`.
  - Built-in algorithms: pagerank, local clustering coefficient, weakly connected components.
  
  — [DuckDB 2.0 docs: graph queries](https://duckdb.org/docs/2.0/guides/sql_features/graph_queries); [duckpgq-extension GitHub](https://github.com/cwida/duckpgq-extension); [DuckDB blog, Oct 2025: financial crime with DuckPGQ](https://duckdb.org/2025/10/22/duckdb-graph-queries-duckpgq)
- **PostgreSQL.** PG19 Beta 1 (4 Jun 2026) announced SQL/PGQ. Beta 4 *reverted* it, along with `FOR PORTION OF` and several other features, so they could be included in a later release. PG19 RC1 shipped on 15 Oct 2026, and GA is planned for 19 Nov 2026. — prior notes `rdbms_sql.md` (PG19 beta announcements); [Jam SQL blog on GRAPH_TABLE in Oracle and PostgreSQL](https://jamsql.com/blog/2026-07-11-sql-pgq-graph-table-oracle-postgresql/) (single, non-authoritative source; it dates the revert to 24 Sep 2026). Graph on PostgreSQL today means Apache AGE, which offers openCypher. AGE has 1.8.0-rc0 for PG18 (9 Jul 2026). — [Apache AGE releases](https://github.com/apache/age/releases)
- **Others.** MySQL, SQL Server and SQLite have no SQL/PGQ, per a single blog. — [Jam SQL blog](https://jamsql.com/blog/2026-07-11-sql-pgq-graph-table-oracle-postgresql/). SQL Server and Oracle had proprietary graph SQL extensions before PGQ. Amazon Neptune began as a graph veneer over Aurora MySQL, according to Stonebraker and Pavlo. — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.8
- Stonebraker and Pavlo on graph databases:
  - OLTP graph engines such as Neo4j chase pointers, as CODASYL did. Their market depends on how many "long chain" traversal workloads justify leaving an RDBMS.
  - Graph analytics (shortest path, cliques) depends on algorithms and representation. Distributed graph algorithms rarely beat a single node, so compress the graph into memory on one machine.
  - Graphs can always be simulated as Node and Edge tables. SQL/PGQ narrows the gap.
  - Studies show graph simulation on an RDBMS outperforming graph DBMSs. SQL/PGQ in DuckDB beat a leading graph DBMS by up to 10×. Worst-case-optimal joins and factorized execution will widen that.
  
  — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.8

**Recursive CTEs**
- In a graph query, every edge traversed is a join with the edges table, and the number of joins is not known in advance. `WITH RECURSIVE` expresses it, but clumsily: the 4-line Cypher query becomes 31 lines of SQL. You also need to handle cycles and choose BFS or DFS. Oracle has its own hierarchical syntax (`CONNECT BY`). Other languages in this space: TigerGraph GSQL and Oracle PGQL. — DDIA 2e p.114–116 (bk 90–92), Examples 3-5 and 3-6
- PostgreSQL `WITH RECURSIVE` supports UNION vs UNION ALL, `SEARCH DEPTH|BREADTH FIRST BY`, and `CYCLE ... SET ... USING` cycle detection. Non-recursive CTEs referenced once are inlined by default since PG12, and `MATERIALIZED`/`NOT MATERIALIZED` override that. — [PG 18 WITH queries](https://www.postgresql.org/docs/18/queries-with.html) (via prior notes). SQL:2023 lets cycle marks be boolean (T133). — [Eisentraut](https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new)
- DuckDB's `USING KEY` recursive CTEs (v1.3.0, May 2025; SIGMOD 2025 paper by Bamberg, Hirn and Grust) treat the working table as a keyed dictionary that can be overwritten, instead of an ever-growing union. That produces much smaller intermediate results. An August 2026 follow-up reports median recursive-CTE runtime falling from 4.051 s (v1.5.5) to 0.095 s (v2.0 preview), 42.6×, with unchanged SQL. — [DuckDB blog: USING KEY](https://duckdb.org/2025/05/23/using-key.html); [DuckDB science page](https://duckdb.org/science/bamberg-using-key-sigmod); [DuckDB blog, 25 Aug 2026](https://duckdb.org/2026/08/25/how-duckdb-runs-recursive-ctes-faster)

**RDF triple stores and SPARQL**
- A triple store holds (subject, predicate, object) statements. The object is either a literal, making it a property, or another vertex, making it an edge. Variants add metadata: Amazon Neptune stores quads (adding a graph ID), and Datomic stores 5-tuples (adding a transaction ID and a retraction flag). Encodings include Turtle/N3 and RDF/XML. RDF uses URIs as namespaces so that datasets from different sources can merge. The Semantic Web did not succeed as envisioned, but its legacy lives on in JSON-LD, biomedical ontologies, Open Graph, Wikidata and Schema.org. — DDIA 2e p.116–119 (bk 92–95)
- SPARQL predates Cypher, and Cypher borrowed its pattern matching. Property paths such as `:bornIn / :within*` mirror Cypher's `*0..`. Supported by Neptune, AllegroGraph, Blazegraph, Virtuoso and Apache Jena. — DDIA 2e p.119–120 (bk 95–96)
- **Standards status.** RDF 1.2 Concepts and RDF 1.2 Semantics became W3C *Candidate Recommendations* on 7 Apr 2026. Exit requires two independent implementations per test. SPARQL 1.2 Query and Update were still Working Drafts as of June 2026. Neither is a Recommendation yet in the sources found. RDF 1.2 grew out of the RDF-star work (triple terms). — [W3C RDF 1.2 Concepts CR](https://www.w3.org/TR/2026/CR-rdf12-concepts-20260407/); [W3C CR notice](https://lists.w3.org/Archives/Public/public-review-announce/2026Apr/0001.html); [W3C SPARQL 1.2 Query](https://www.w3.org/TR/sparql12-query/)
- Stonebraker and Pavlo treat property graphs as a superset of RDF. — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.8

**Datalog**
- Datalog comes from 1980s research, is a subset of Prolog, and rests on a relational model.
  - Facts are rows; for example, `born_in(100, 3)` is a row in a two-column join table.
  - Rules derive virtual tables, which act like views.
  - Rules can be recursive (`within_recursive`), which makes graph traversal natural, and queries are built up rule by rule like functions.
  
  Users include Datomic, LogicBlox, CozoDB and LinkedIn's LIquid. — DDIA 2e p.120–122 (bk 96–98)
- **Datomic.** On 27 Apr 2023 Nubank made all Datomic editions free, with binaries under Apache 2.0 on Maven Central. Datomic Cloud followed on 16 Jun 2023 and Datomic Local in Aug 2023. Datomic's FAQ says it is still *not* open source, because the license covers binaries only. — [Datomic blog: "Datomic is Free"](https://blog.datomic.com/2023/04/datomic-is-free.html); [Datomic Cloud FAQ](https://www.datomic.com/cloud-faq.html)
- **Soufflé** compiles Datalog to parallel C++ and targets static program analysis, without DBMS features. It is described as the most-used, highest-performance open-source Datalog engine. Latest release 2.5 (24 Mar 2025). — [Soufflé GitHub releases](https://github.com/souffle-lang/souffle/releases); [Desyan paper, arXiv 2508.00508](https://arxiv.org/html/2508.00508v1); [JavaCodeGeeks on Soufflé](https://www.javacodegeeks.com/?p=138579)
- **CodeQL** (GitHub) analyzes code with a Datalog-derived query language (QL), and static analysis is Datalog's most successful industrial use. — [JavaCodeGeeks (secondary)](https://www.javacodegeeks.com/?p=138579). The claim that CodeQL compiles to Soufflé is anecdotal and unverified.
- **Google Mangle** is an open-source deductive database language that extends Datalog with aggregations and function calls, implemented as a Go library. Latest v0.4.0 (1 Nov 2025). — [google/mangle releases](https://github.com/google/mangle/releases); [Medium overview](https://medium.com/render-beyond/meet-google-mangle-a-smarter-programming-language-for-databases-dependencies-and-data-chaos-b7f6181f5afa)

**GraphQL: what it is and is not**
- GraphQL is deliberately restrictive and aimed at OLTP. A client (a mobile or web frontend) asks for a JSON document shaped for its UI.
  - Queries come from untrusted clients, so there is no recursion and no arbitrary search unless the service exposes it.
  - The response mirrors the query, accepting duplication (sender repeated per message) to simplify rendering.
  - It can sit on top of any database (relational, document or graph), but only joins declared in the schema are available.
  - Costs: translation to internal REST/gRPC services, authorization, rate limiting, and performance.
  
  — DDIA 2e p.122–125 (bk 98–101), citing Bessey, "Why, after 6 years, I'm over GraphQL" (2024)
- The GraphQL spec's September 2025 edition (announced 8 Sep 2025) is the first since October 2021. It adds OneOf input objects, schema coordinates, descriptions on executable documents, broader deprecation and full Unicode grammar. `@defer`/`@stream` are not included. — [GraphQL blog](https://graphql.org/blog/2025-09-08-september-edition/); [graphql-spec release tag](https://github.com/graphql/graphql-spec/releases/tag/September2025)

### Inferences
- **Graph arc:**
  1. *Problem.* Location hierarchies of uneven depth (city→region→state→country; France has départements and régions), and fraud rings that share identifiers.
  2. *Simplest version.* vertices and edges tables in PostgreSQL with indexes on both ends.
  3. *Break.* Variable-depth traversal needs recursive CTEs. UNION ALL on cyclic data loops forever, and frontier blow-up on high-degree nodes is exponential in depth.
  4. *Improvement.* Native pattern languages (Cypher, GQL, SQL/PGQ) with path semantics (ACYCLIC/TRAIL/SHORTEST), engine-level path algorithms, and keyed recursion (`USING KEY`).
- **Bug to fix in lab or slide material.** DDIA Example 3-6 (p.114–115) is inconsistent in case. `in_usa` filters `label = 'Location'` but `in_europe` filters `'location'`, and the edge labels are lowercase `'within'` while the Cypher data uses `WITHIN`. Taken literally on PostgreSQL, which compares case-sensitively, part of the query returns nothing. Normalize the case before copying it into a lab.
- **Syntax currency.** DDIA's `[:WITHIN*0..]` is non-GQL legacy syntax in Cypher 25. Teach the quantified form (for example `-[:WITHIN]->{0,}`) with the legacy form as a footnote. I inferred the exact quantifier spelling from GQL/Cypher 25 conventions; verify against the Neo4j manual.
- **Misconceptions:**
  - "GraphQL is a graph database query language." False: it is an API query language over any backend.
  - "SQL can't do graphs." It can, through recursive CTEs, and now SQL/PGQ in Oracle, Spanner and DuckDB.
  - "PostgreSQL 19 has SQL/PGQ." It was reverted.
  - "GQL replaced Cypher." Cypher 25 is converging toward GQL with documented gaps.
  - "Graph DBs are always faster for joins." Stonebraker and Pavlo cite RDBMS and DuckPGQ results showing otherwise.
- **Datalog teaching hook.** Semi-naive evaluation (only new facts feed each iteration) is the same idea as `USING KEY` and incremental view maintenance. A 200-line pure-Kotlin Datalog engine makes recursion, fixpoints and stratified negation tangible.
- **GraphQL's N+1.** A naive per-field resolver issues one SQL query per parent row, which is the ORM N+1 again at the API layer. The standard fix is batching per request (the DataLoader pattern). That is background knowledge; DataLoader was not fetched this session.

### Gaps
- I could not confirm SQL/PGQ or GQL support in SAP HANA, BigQuery, Amazon Neptune (which uses openCypher and Gremlin, not GQL), TigerGraph or Ultipa from current primary sources. A 2022 article claimed GQL support for Ultipa, TigerGraph and Spanner, but it predates the standard.
- I did not fetch Neo4j's SHORTEST-path GQL syntax page.
- The PG19 revert date (24 Sep 2026) comes from a single blog. Prior notes confirm the revert happened in Beta 4 but not the exact date. Confirm against the PG19 release notes after GA on 19 Nov 2026.
- I did not verify CodeQL's internals from GitHub's own documentation, or XTDB 2.x's query-language status. XTDB v2.2.0 was released on 21 Oct 2026 per GitHub; my background understanding is that v2 is SQL-first and bitemporal, but I did not verify it.

## 6. Event sourcing and CQRS: commands vs events, projections, snapshots, schema evolution of events, products (Kurrent/EventStoreDB, Axon), when it hurts

### Takeaway
Event sourcing makes an append-only log of immutable, past-tense *events* the system of record. Current state and query models (projections or read models) are derived by replay. CQRS is the broader idea of separate write and read models, and the two are often used together but are distinct. The benefits are intent, audit, rebuildable views and new views over old history. The costs are determinism with external data, GDPR erasure, replay side effects, versioning events forever, and complexity. Fowler reports that most CQRS projects he saw failed.

### Cited Findings
**Model**
- Earlier models are queried in the same form they are written. Event sourcing instead writes the simplest, fastest form, an append-only log of timestamped self-contained events, and derives read-optimized materialized views (projections or read models) from it. The running example is a conference booking system, where even "available seats" is a hard query. — DDIA 2e p.125–126 (bk 101–102)
- A *command* is a user request. It must be validated, for example by checking that enough seats remain. Only a valid command becomes an *event*, which is a fact. Consumers building views may not reject events. Name events in the past tense ("seats were booked"); a cancellation is a separate later event. The terms come from the DDD community, and the idea relates to state machine replication. — DDIA 2e p.126–127 (bk 102–103)
- Advantages:
  - Events convey intent; compare "booking cancelled" with a set of row diffs.
  - Views can be deleted and recomputed deterministically, which makes bugs fixable by replay.
  - You can keep several denormalized views in any data model, including in-memory views.
  - New views can be built over old history.
  - Mistakes are corrected with compensating events.
  - The log doubles as an audit log.
  - Sequential append absorbs write bursts.
  
  — DDIA 2e p.127–128 (bk 103–104)
- Downsides:
  - External data must be captured in the event, or queried as of the event time, so replay stays deterministic. Example: exchange rates.
  - Immutable events conflict with GDPR erasure. Options are per-user logs or crypto-shredding (encrypt personal data and delete the key), and both complicate recomputation.
  - Replays must not repeat external side effects such as emails.
  
  — DDIA 2e p.128 (bk 104)
- The only hard requirement is that every view processes events in exactly the same order as the log, which is hard in distributed systems. Products named in DDIA: EventStoreDB, MartenDB (on PostgreSQL) and Axon Framework, or Kafka plus stream processors. — DDIA 2e p.129 (bk 105). *Changed:* EventStoreDB is now KurrentDB (see below).
- Fowler, "Event Sourcing" (12 Dec 2005):
  - Capabilities: complete rebuild, temporal query (state as of time T), and event replay to fix a wrong or out-of-order event.
  - **Snapshots.** Replaying from empty is slow for large logs, so systems cache state (for example an overnight snapshot) and replay only later events. Either the state or the log can be the system of record.
  - External updates should go through gateways that are disabled during replay. External queries should be recorded or answered with historical values.
  - Time-dependent rules belong in the domain model.
  - Fit: audit, retroactive or parallel models (decide early), event-driven integration and accounting. He warns about added complexity.
  
  — [Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- Fowler, "CQRS" (14 Jul 2011):
  - CQRS (from Greg Young) separates the update model from the read model. It fits event-based systems and event sourcing.
  - He advises being very cautious. Most cases he saw were not successful and became a major source of difficulty.
  - Use it only in specific bounded contexts and a minority of complex domains. Where the read and write sides overlap heavily, a shared model is simpler.
  - The benefits are independent scaling and optimization of each side. A reporting database is a lighter alternative.
  
  — [Fowler, CQRS](https://martinfowler.com/bliki/CQRS.html)

**Schema evolution of events**
- Greg Young, *Versioning in an Event Sourced System* (Leanpub; DDD eXchange talk 2017):
  - Events stored years ago must remain readable.
  - Strategies: simple type-based versioning, weak schema or hybrid schema, negotiation, handling mistaken events, and copy-and-replace.
  - He prefers weak schemas (JSON/XML, with mapping that tolerates missing or extra fields), so old code can read new events and only the latest version is needed. In the hybrid form, essential fields are required and the rest optional.
  
  — [Leanpub: Versioning in an Event Sourced System](https://leanpub.com/esversioning/read); [InfoQ, Jul 2017](https://www.infoq.com/news/2017/07/versioning-event-sourcing)
- Arkency describes the main strategies for changing a published event as a weaker schema, upcasting (transforming old events as they are read) and copy-and-replace, and calls upcasting a good default once events are in production. — [Arkency: strategies to change a published event](https://blog.arkency.com/4-strategies-when-you-need-to-change-a-published-event/)
- **Dynamic Consistency Boundary (DCB)** enforces consistency without fixed aggregate or stream boundaries. A boundary is a predicate over event tags and types rather than a stream revision. It was introduced in Sara Pellegrini's "Killing the Aggregate". Getting stream granularity wrong otherwise means re-streaming history. — [dcb.events](https://dcb.events/); [denbeke.be on DCB](https://denbeke.be/blog/?p=2376)

**Products, versions as of November 2026**
- **KurrentDB (formerly EventStoreDB).** The company and the product rebranded to Kurrent, and the first KurrentDB release was 25.0. You can roll-upgrade directly to it from EventStoreDB 24.10, 23.10 or 22.10. KurrentDB 26.0 is LTS, supported for at least two years. Breaking changes in 26.0: the Linux service is now `kurrentdb`, and the environment-variable prefix is `KURRENTDB_`. EventStoreDB 24.10 was supported until October 2026. Clients were renamed, for example `EventStoreDBClient` to `KurrentDBClient`. — [Kurrent press release](https://kurrentdb.kurrent.io/press/event-store-announces-eventstoredb-name-change/); [KurrentDB 26.0 upgrade guide](https://docs.kurrent.io/server/v26.0/quick-start/upgrade-guide); [KurrentDB 25.0 upgrade guide](https://docs.kurrent.io/server/v25.0/quick-start/upgrade-guide.html)
- KurrentDB GitHub releases checked this session: v26.2.3 (19 Oct 2026, the 26.2 STS line), v26.1.3 (2 Oct 2026), and v26.0.4 (27 Oct 2026, the 26.0 LTS line). — [KurrentDB releases](https://github.com/kurrent-io/KurrentDB/releases)
- **Axon Framework 5.** 5.0.0 was released on 18 Nov 2025, and the latest is 5.4.1 (21 Oct 2026). The headline is DCB: the aggregate is no longer the only unit of consistency. DCB needs an event store that supports it, and Axon Server 2025.1 introduced that support. — [AxonFramework GitHub releases](https://github.com/AxonFramework/AxonFramework/releases); [Maven metadata](https://repo1.maven.org/maven2/org/axonframework/axon-messaging/maven-metadata.xml); [Axon 5 "Why upgrade"](https://docs.axoniq.io/axon-framework-reference/5.0/migration/why-upgrade/); [Axon Server 2025.1 DCB](https://www.axoniq.io/blog/axon-server-future-proof-event-store); [AxonIQ: DCB in AF5](https://www.axoniq.io/blog/dcb-in-af-5)

### Inferences
- **Arc:**
  1. *Problem.* "Why is seat 14 unavailable?" A mutable `bookings` table answers "what is", but not "why" or "what was".
  2. *Simplest version.* An append-only `events(stream_id, version, type, payload jsonb, ts)` table, with state computed by folding over the events.
  3. *Break 1.* Load time grows linearly with stream length. 100k events per account at about 2 µs per fold step is about 0.2 s per command; this is an estimate to measure, not a sourced figure.
  4. *Fix 1.* Snapshots every N events.
  5. *Break 2.* Two concurrent commands both see one seat left. Fix with optimistic concurrency on the expected stream version (or a DCB condition).
  6. *Break 3.* Version 1 events lack a field. Fix with upcasters or a weak schema.
  7. *Break 4.* Projections lag behind writes, so a user's own write is not visible yet. Fix with read-your-writes through position tokens.
- **Commands vs events vs messages.** A command can be rejected and is imperative. An event cannot be rejected and is in the past tense. Many teams confuse event sourcing with event-driven integration (publishing events to other services). The two are independent choices.
- **Misconceptions:**
  - "Event sourcing requires Kafka." Any ordered append-only store works, including a PostgreSQL table.
  - "CQRS requires event sourcing." It does not (Fowler).
  - "Events are immutable, so GDPR is impossible." Crypto-shredding and per-subject streams exist, with trade-offs.
  - "Replay is free." Side effects and external lookups break determinism.
  - "Snapshots are the source of truth." They are a cache.
- **When it hurts:**
  - CRUD-shaped domains.
  - Ad-hoc queries across many aggregates, which need projections for everything.
  - Teams new to DDD.
  - Long-lived systems that never planned event versioning.
  - Strong cross-aggregate invariants, which is what DCB tries to address.

### Gaps
- I did not verify the KurrentDB Docker image name or tag for a Testcontainers lab, or whether a ready-made KurrentDB Testcontainers module exists.
- No independent production data was found on projection rebuild times or snapshot frequencies. Treat the numbers above as lab-measurable estimates.
- I did not fetch Marten's current version or Greg Young's original "CQRS Documents" (2010) that DDIA cites.

## 7. DataFrames, matrices and arrays (pandas, Polars, Spark DataFrames) as a model

### Takeaway
A DataFrame looks like a table but is a different model. Rows are *ordered* and labeled, columns are labels that can turn into data (pivot, transpose), schemas are inferred, and the API is a sequence of imperative transformations on a private copy. It bridges relational data and the numeric matrices that ML needs. In 2026 the field has moved toward lazy, query-optimized and columnar engines (Polars 2.x, DuckDB 2.0, Spark 4.3), while pandas 3.0 made copy-on-write and a real string dtype the defaults.

### Cited Findings
- DataFrames appear in R, pandas, Spark, ArcticDB, Dask and others. They offer relational-like bulk operators: apply, filter, group/aggregate, and "merge" (join). They are manipulated through a series of commands rather than a declarative query, which matches the incremental "wrangling" workflow, usually on a private local copy. — DDIA 2e p.129 (bk 105)
- Common use: transform relational data into a matrix or multidimensional array for ML. Example: movie ratings pivot into a sparse user × movie matrix with possibly thousands of columns, which fits poorly in an RDBMS but suits NumPy sparse arrays. Matrices hold only numbers, so dates are scaled and categoricals one-hot encoded. — DDIA 2e p.129–130 (bk 105–106)
- Array databases (TileDB) store large multidimensional numeric arrays: geospatial rasters, medical imaging, astronomy. DataFrames are also used for financial time-series. Spark and Flink added DataFrames. — DDIA 2e p.131 (bk 107)
- Petersohn et al., "Towards Scalable Dataframe Systems" (arXiv 2001.00888, 2020; authors include Hellerstein and Parameswaran) propose a simple data model and algebra for dataframes. Its distinguishing features are flexible schemas, ordering, row/column equivalence, and data/metadata fluidity. — [arXiv 2001.00888](https://arxiv.org/abs/2001.00888) (abstract only fetched); cited by DDIA as ref [69]
- Stonebraker and Pavlo on arrays: array DBMSs (SciDB, kdb+, TileDB; earliest PICDMS in the 1980s) remain niche. Most ML datasets are arrays. They say SQL:2023 includes true multi-dimensional arrays (SQL/MDA). — [Stonebraker & Pavlo 2024](https://db.cs.cmu.edu/papers/2024/whatgoesaround-sigmodrec2024.pdf) §2.6
- **pandas 3.0.0** (21 Jan 2026):
  - A dedicated string dtype is the default, instead of object.
  - Copy-on-Write is the default and only mode.
  - Requires Python 3.11 or later.
  - Recommended path: upgrade to 2.3 first and clear warnings.
  
  The latest release is 3.1.1 (4 Nov 2026). — [pandas 3.0 release blog](https://pandas.pydata.org/community/blog/pandas-3.0.html); [pandas 3.0 RC post](https://pandas.pydata.org/community/blog/pandas-3.0-release-candidate.html); [PyPI pandas](https://pypi.org/project/pandas/) (dates checked via the PyPI JSON API this session)
- **Polars 2.0.0** (6 Oct 2026); latest 2.1.0 (25 Oct 2026). Breaking changes in 2.0:
  - SQL window functions over grouped rows now run on the aggregated rows, and `QUALIFY` is evaluated before projection.
  - Exact SQL numeric literals are typed as Decimal.
  - `cut`/`qcut` are deprecated.
  - It adds a streaming out-of-core sort, among many performance changes.
  
  — [PyPI polars](https://pypi.org/project/polars/); [Polars py-2.0.0 release notes](https://github.com/pola-rs/polars/releases/tag/py-2.0.0)
- **Spark 4.3.0** (30 Oct 2026) is the first release under a quarterly schedule. It runs on Java 17, 21 or 25. — [Spark 4.3.0 release](https://spark.apache.org/releases/spark-release-4-3-0.html) (via prior notes); [PyPI pyspark](https://pypi.org/project/pyspark/)
- **DuckDB 2.0.0 LTS** (21 Oct 2026), supported until at least Oct 2027:
  - A PEG parser is now the default, and extensions can add grammar.
  - Adds the VARIANT type, triggers, data-modifying CTEs, `NEAREST` joins and `FETCH FIRST`.
  - MERGE and `UPDATE ... FROM` semantics are now well-defined when multiple rows match.
  - The single-arrow lambda syntax is disabled in favor of `lambda x: ...`.
  - DuckDB versions before 2.0 cannot read 2.0 database files.
  - DuckDB 1.4 LTS support ends on 17 Nov 2026.
  
  — [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200.html); [DuckDB v2.0.0 GitHub release](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)

### Inferences
- **Arc:**
  1. *Problem.* Exploratory analysis and ML feature prep need fast iteration and reshaping (pivot, one-hot, rolling windows) that SQL makes awkward.
  2. *Simplest version.* pandas, in memory, eager, with one operation per line.
  3. *Break 1.* Memory. A 10 GB CSV in pandas often needs several times that in RAM (background rule of thumb; measure it). The ratings pivot also explodes as a dense matrix: 100k users × 50k movies × 8 bytes is about 40 GB dense, against megabytes sparse (my arithmetic).
  4. *Break 2.* No optimizer, because eager steps cannot be reordered or pushed down.
  5. *Break 3.* Chained-assignment ambiguity, which CoW resolves in pandas 3.
  6. *Improvement.* Lazy dataframes (Polars `LazyFrame`, Spark DataFrame), where the plan is optimized like SQL with predicate and projection pushdown. This is DDIA's declarative argument coming back inside the dataframe world.
- **Relation vs DataFrame differences to teach:**
  - Order is semantic; a relation has none.
  - Row labels (the pandas index) take part in alignment, so adding two Series aligns by label and produces NaNs where labels mismatch. This is a classic misconception and bug.
  - Columns can become data and data can become columns (pivot/melt/transpose).
  - Types are inferred on read (schema-on-read again).
- **Misconceptions:**
  - "Spark DataFrame = pandas at scale." Spark is lazy, unordered unless sorted, and has no row index.
  - "Polars is just faster pandas." It has a different, expression-based and lazy-first model.
  - "SQL/MDA arrived in SQL:2023." My background knowledge is that ISO/IEC 9075-15 (SQL/MDA) was first published in 2019. Stonebraker and Pavlo attribute it to SQL:2023, which may refer to its inclusion in the 2023 edition. Unverified; flag it if teaching standards history.
- **JVM angle for the Kotlin course.** Spark 4.3 DataFrames run natively on JVM 21. DuckDB 2.0 runs from Kotlin through JDBC. JetBrains' Kotlin DataFrame library exists, but its version was not checked.

### Gaps
- I did not fetch the Petersohn et al. full text for its formal algebra (the abstract only).
- I did not check the version or 2026 status of Kotlin DataFrame (`org.jetbrains.kotlinx:dataframe`) or Kotlin Notebook support.
- I did not verify the SQL/MDA publication year.

## 8. Modern SQL worth teaching (window functions, CTEs, LATERAL, MERGE, GROUPING SETS/CUBE, JSON_TABLE) and what PostgreSQL 18 added

### Takeaway
The SQL that separates beginners from practitioners is post-1999 SQL:
- window functions with explicit frames;
- CTEs, including recursive ones with SEARCH/CYCLE;
- LATERAL ("for each row, run this subquery");
- GROUPING SETS/ROLLUP/CUBE;
- MERGE (PG15+, with `RETURNING merge_action()` in PG17);
- the SQL/JSON functions, including `JSON_TABLE` (PG17).

PostgreSQL 18 (25 Sep 2025, current minor 18.6) adds `uuidv7()`, virtual generated columns as the default, OLD/NEW in RETURNING, temporal keys (`WITHOUT OVERLAPS`, `PERIOD`), B-tree skip scan, BUFFERS in EXPLAIN ANALYZE by default, and asynchronous I/O. PostgreSQL 19 is not GA as of 7 Nov 2026.

### Cited Findings
**Processing model and core features**
- PostgreSQL's logical SELECT order is WITH, FROM/joins, WHERE, GROUP BY/HAVING, select list (where window functions are computed), DISTINCT, set operations, ORDER BY, then LIMIT/OFFSET. — [PG 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html) (via prior notes)
- Window functions: frame modes are `RANGE | ROWS | GROUPS`, with `EXCLUDE CURRENT ROW | GROUP | TIES | NO OTHERS`. With `ORDER BY`, the default frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which includes peers. The catalogue: row_number, rank, dense_rank, percent_rank, cume_dist, ntile, lag, lead, first_value, last_value, nth_value. — [PG 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html); [PG 18 window functions](https://www.postgresql.org/docs/18/functions-window.html) (via prior notes)
- LATERAL lets a FROM-clause subquery refer to columns of earlier FROM items. `LEFT JOIN LATERAL ... ON true` keeps outer rows with no match. — [PG 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html) (via prior notes)
- GROUPING SETS, ROLLUP, CUBE and LATERAL are documented under table expressions. Aggregate `FILTER (WHERE ...)` is documented separately. — [PG 18 table expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html) (via prior notes)
- CTEs: since PG12, side-effect-free non-recursive CTEs referenced once are inlined, so they are no longer an "optimization fence". `WITH RECURSIVE` offers SEARCH and CYCLE clauses. — [PG 18 WITH](https://www.postgresql.org/docs/18/queries-with.html) (via prior notes)
- MERGE: available since PG15. PG17 added `RETURNING`, `merge_action()`, `WHEN NOT MATCHED BY SOURCE`, and MERGE into updatable views. The PG docs point to `INSERT ... ON CONFLICT` as the concurrency-safe alternative when concurrent inserts are possible. A target row matching several source rows raises a cardinality violation. — [PG 17 release notes](https://www.postgresql.org/docs/17/release-17.html); [PG 18 MERGE](https://www.postgresql.org/docs/18/sql-merge.html) (via prior notes)
- PG17 added SQL/JSON `JSON_TABLE` and the related query functions (see §2). — [PG 17 release notes](https://www.postgresql.org/docs/17/release-17.html)
- Large OFFSET values still compute the skipped rows, so keyset ("seek") pagination is the alternative. — [PG 18 LIMIT/OFFSET](https://www.postgresql.org/docs/18/queries-limit.html); [Use The Index, Luke: No Offset](https://use-the-index-luke.com/no-offset) (via prior notes)

**PostgreSQL 18 (released 25 Sep 2025; supported until 14 Nov 2030; current minor 18.6)**
- `uuidv7()`, which is time-ordered, plus a `uuidv4()` alias.
- Virtual generated columns, now the default kind: computed on read with no storage, and limited to immutable built-in functions.
- `OLD`/`NEW` in `RETURNING` for INSERT, UPDATE, DELETE and MERGE, e.g. `RETURNING old.balance, new.balance`.
- Temporal `PRIMARY KEY`/`UNIQUE ... WITHOUT OVERLAPS` on range or multirange columns (`btree_gist` is the expected companion) and temporal foreign keys with `PERIOD`.
- B-tree skip scan, so multicolumn indexes work without a predicate on the leading column.
- `EXPLAIN ANALYZE` includes BUFFERS by default.
- Planner: OR-to-ANY transformation and self-join elimination.
- Asynchronous I/O (`io_method` = `worker` by default, `io_uring`, or `sync`).
- Data checksums on by default.
- Docker `PGDATA` path changed to `/var/lib/postgresql/18/docker`.

— [PG 18 release notes](https://www.postgresql.org/docs/18/release-18.html); [PG versioning policy](https://www.postgresql.org/support/versioning/); [PG 18 CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html) (all via prior notes `rdbms_sql.md`)

**What's next and what's elsewhere**
- PostgreSQL 19: RC1 on 15 Oct 2026, with GA planned for 19 Nov 2026.
  - Beta 1 announced SQL/PGQ, `UPDATE/DELETE ... FOR PORTION OF`, `GROUP BY ALL`, `INSERT ... ON CONFLICT DO SELECT ... RETURNING`, jsonpath string functions, and `MERGE/SPLIT PARTITIONS`.
  - Beta 4 reverted SQL/PGQ, `FOR PORTION OF` and `MERGE/SPLIT PARTITIONS`, among others.
  - Teach `GROUP BY ALL` and `ON CONFLICT DO SELECT` only as "PG19 sidebars", confirmed at GA.
  
  PostgreSQL 14 reaches end of life on 12 Nov 2026. — prior notes `rdbms_sql.md` (PG19 beta announcements); [PG versioning](https://www.postgresql.org/support/versioning/)
- SQL:2023 additions worth a slide:
  - `UNIQUE NULLS [NOT] DISTINCT` (F292)
  - `ORDER BY` in grouped tables (F868)
  - `GREATEST`/`LEAST` (T054)
  - `ANY_VALUE` (T626)
  - hex/octal/binary literals (T661) and `_` digit separators (T662)
  - the JSON type and simplified accessor (T801, T860–T864)
  - SQL/PGQ (Part 16)
  
  — [Eisentraut](https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new)
- DuckDB 2.0 adds data-modifying CTEs, `NEAREST` joins, `FETCH FIRST`, `UNNEST` in `GROUP BY`, and well-defined MERGE semantics when multiple source rows match. DuckDB's `USING KEY` recursive CTEs (v1.3, 2025) are a non-standard extension worth showing. — [DuckDB 2.0 announcement](https://duckdb.org/2026/10/21/announcing-duckdb-200.html); [DuckDB USING KEY](https://duckdb.org/2025/05/23/using-key.html)
- Polars 2.0's SQL interface now evaluates `QUALIFY` before projection, which shows QUALIFY (window-function filtering) spreading beyond Snowflake, BigQuery and DuckDB. — [Polars py-2.0.0 release](https://github.com/pola-rs/polars/releases/tag/py-2.0.0)

### Inferences
- **Arc for each feature (problem, then the version that breaks, then the fix):**
  - *Top-N per group.* A correlated subquery is O(n²) and unreadable. `row_number() OVER (PARTITION BY ...)` filtered in an outer query is better. `LATERAL ... ORDER BY ... LIMIT k` with an index is often best (index-backed).
  - *Running totals.* A self-join blows up quadratically. Fix with `sum() OVER (ORDER BY ts ROWS UNBOUNDED PRECEDING)`. The trap is the default RANGE frame with ties, or `last_value` returning the current row.
  - *Upsert.* SELECT-then-INSERT races. `INSERT ... ON CONFLICT` is atomic. MERGE is more general but not a concurrency primitive.
  - *Subtotals.* `UNION ALL` of several GROUP BYs scans repeatedly. Use `GROUPING SETS/ROLLUP/CUBE` plus `GROUPING()` to tell subtotal NULLs from data NULLs.
  - *Hierarchies.* A fixed number of self-joins handles only fixed depth. `WITH RECURSIVE` plus `CYCLE` handles any depth.
  - *JSON arrays to rows.* Ad-hoc `jsonb_array_elements` chains give way to `JSON_TABLE`.
- **Approximate standard lineage** (background knowledge, not verified this session; check modern-sql.com before quoting):

  | Feature | Standard |
  | --- | --- |
  | CTE/recursive, LATERAL, GROUPING SETS/ROLLUP/CUBE | SQL:1999 |
  | window functions and MERGE | SQL:2003 |
  | SQL/JSON functions incl. `JSON_TABLE` | SQL:2016 |
  | JSON type and PGQ | SQL:2023 |

- **Misconceptions:**
  - "CTEs are always materialized." Not since PG12.
  - "MERGE is race-free." The docs recommend ON CONFLICT for concurrent inserts.
  - "Multicolumn index needs the leading column." Relaxed by PG18 skip scan when the leading column has low cardinality.
  - "A window function can go in WHERE." Not according to the processing order; use QUALIFY where available, or a subquery.

### Gaps
- I did not verify whether PG18 virtual generated columns can be indexed. Prior notes recall they cannot; test before teaching.
- PG19 feature list is final only at GA (19 Nov 2026), after this research date.
- Not checked: Oracle 26ai's or SQL Server 2025's support for `JSON_TABLE`, the SQL:2023 JSON type and `QUALIFY`. Oracle matters because prior notes say the learner's employer runs Oracle.

## 9. Hands-on lab ideas for each model (Kotlin on JVM 21+, Gradle, Testcontainers / Docker Compose / pure-Kotlin; each makes a number or anomaly observable)

### Takeaway
Give each model one lab built around a single measurement: a count of queries, a latency ratio, a size limit hit, a wrong answer reproduced, or a recall below 1.0. Learners should see the "where it breaks" moment themselves. Pin images to the versions verified above and in prior notes.

### Cited Findings
- Verified images and versions to pin (prior notes plus this session):
  - `postgres:18.6`, with pgJDBC 42.7.14, HikariCP 7.1.0, Flyway 13.12.1, jOOQ 3.21.9 and Exposed 1.6.1.
  - `mongodb/mongodb-community-server:9.0-ubi9-slim`, started as a single-node replica set with `--replSet`, with Java driver 5.14.0.
  - `cassandra:5.0.9` (also `6.0-alpha2`; multi-arch including arm64).
  - `neo4j:2026.10.2` (Community), with `NEO4J_AUTH`, ports 7474/7687, a 512 MB default heap and page cache, and Java driver 6.3.0.
  - pgvector 0.8.7.
  - DuckDB 2.0.0.
  - Spark 4.3.0.
  - KurrentDB 26.0.4 LTS.
  - Axon Framework 5.4.1.
  
  — [Systems course report](../../reports/Systems%20course%20curriculum%20research.md) and prior notes (`rdbms_sql.md`, `nosql.md`); [Docker Hub cassandra](https://hub.docker.com/_/cassandra); [Neo4j Docker docs](https://neo4j.com/docs/operations-manual/current/docker/introduction/); [MongoDB Docker install](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/); [KurrentDB releases](https://github.com/kurrent-io/KurrentDB/releases); [Axon releases](https://github.com/AxonFramework/AxonFramework/releases)
- On a Mac, Cassandra defaults to 40–50% of memory. Set `MAX_HEAP_SIZE`/`HEAP_NEWSIZE` and stagger node joins, or the seed node is OOM-killed (exit 137). Docker's 64 MB `/dev/shm` breaks PostgreSQL parallel hash joins, so add `--shm-size=1g` (community experience). — prior report (docker-library/cassandra#144; not re-verified)
- PG18 `EXPLAIN ANALYZE` shows buffers by default, which is useful for "count the pages" labs. — [PG 18 release notes](https://www.postgresql.org/docs/18/release-18.html)
- MongoDB 9.0 explain reports `$lookup` peak memory, and `$queryStats` is on by default at 1% sampling. — [MongoDB 9.0 release notes](https://www.mongodb.com/docs/manual/release-notes/9.0/)

### Inferences
The lab designs below are my own. Each names the observable result.

1. **N+1 and identity map (relational/ORM).** Testcontainers `postgres:18.6`, plus Hibernate 7 or Exposed, plus `pg_stat_statements`. Load 1,000 comments with authors in three ways: lazy (N+1), join fetch, and batch fetch (size 50).
   - *Measure:* statements executed (1,001 vs 1 vs 21) and wall time.
   - *Anomaly:* inside one session, `find(1) === find(1)` is true. A concurrent transaction updates the author, and the session still sees the old name until `refresh()`.
2. **Normalization anomaly.** Copy an organization name into 100,000 JSONB résumés. "Rename" it with a Kotlin loop and kill the process at 50%.
   - *Measure:* rows with the old name (about 50,000), against a normalized `organizations` table where the rename is 1 row and atomic.
3. **Document locality vs joins.** Same résumé dataset in `mongo:9.0` (embedded) and PG18 (4 tables, and also a JSONB column).
   - *Measure:* p50/p99 latency of "load full profile" for embedded find, a 4-way join and JSONB fetch. Then of "all users who worked at org X", comparing a multikey index, `$lookup`, an indexed join table and a JSONB GIN `@>`.
   - *Break:* append comments to one document until the insert fails at the 16 MB BSON limit. Record the count, and the update latency as the document grows.
4. **Schema-on-read vs schema-on-write.** Split `name` into `first_name` on 5M rows.
   - *Measure:* `ALTER TABLE ADD COLUMN ... DEFAULT NULL` (milliseconds, metadata-only) vs `UPDATE` of all rows (seconds to minutes, plus table bloat in `pg_relation_size`), vs lazy fill at read time.
   - *Then:* in MongoDB 9.0, switch validation from `moderate` to `constraint` and watch the existing invalid documents block the change or get reported. Verify the exact behavior in the docs.
5. **Wide-column partition design.** `cassandra:5.0.9`, a sensor table with `PRIMARY KEY ((sensor_id), ts)`. Write 100 rows/s for a simulated week through a pure-Kotlin generator with explicit timestamps.
   - *Measure:* partition size from `nodetool tablestats` or `sstablepartitions`, and read latency.
   - *Then:* re-key to `((sensor_id, day), ts)` and compare. Run `WHERE ts > ?` without a partition key and see the error or `ALLOW FILTERING`.
6. **DynamoDB single-table and hot partitions.** DynamoDB Local (verify the image name), with `PK=ACCT#id`, `SK=PAY#ts`. One `Query` returns an account plus its last 20 payments; *measure* `ReturnConsumedCapacity`.
   - Hot partitions can't be reproduced on DynamoDB Local, so write a **pure-Kotlin token-bucket simulation**: 1,000 WCU per partition and 400 KB items.
   - *Measure:* throttled writes per second (about 2.5 allowed), then the effect of write sharding with a suffix.
7. **Vectors.** PG18 plus pgvector 0.8.7, with 100k random or embedding vectors.
   - *Measure:* recall@10 of HNSW vs exact search, and latency, while varying `ef_search`. The learner sees approximate search give recall below 1.0.
8. **Star schema, OBT and SCD2.** DuckDB 2.0 over JDBC from Kotlin, with a generated retail star (facts at 10–50M rows).
   - *Measure:* the same query on the star vs OBT (time and file size).
   - *SCD:* in PG18, move a customer from Boston to Denver. Type 1 overwrite shifts last year's Boston revenue to Denver; measure the delta. Type 2 with a `WITHOUT OVERLAPS` temporal key and MERGE `RETURNING merge_action()` keeps it right. A deliberately overlapping version is rejected.
9. **Graph traversal three ways.** A location hierarchy plus a fraud graph (accounts sharing devices and cards), run in:
   - `neo4j:2026.10.2` with Cypher 25 quantified path patterns;
   - PG18 `WITH RECURSIVE` (with and without `CYCLE`);
   - DuckDB 2.0 with duckpgq `GRAPH_TABLE`.
   
   *Measure:* lines of query code (DDIA's 4 vs 31), runtime by hop depth 2–6, and result-set growth on high-degree nodes. *Anomaly:* `UNION ALL` on a cyclic graph never terminates (use a statement timeout), and `UNION` or `CYCLE` fixes it.
10. **Datalog from scratch (pure Kotlin).** About 200 lines: facts as `Set<List<Any>>`, rules, and naive vs semi-naive fixpoint evaluation.
    - *Measure:* iterations and rule firings for transitive closure on a 1,000-node chain (naive re-derives all facts each round; semi-naive only new ones).
    - *Extension:* stratified negation ("locations with no residents").
11. **GraphQL N+1.** Spring for GraphQL or graphql-kotlin over PG18, using DDIA's chat query (channels → 50 messages → sender → replyTo).
    - *Measure:* SQL statements per GraphQL request with naive resolvers vs batched (DataLoader/`@BatchMapping`).
    - *Then:* add a max-depth/complexity limit and send a deeply nested query to see it rejected.
12. **Event sourcing.** Pure-Kotlin event store on a PG18 table, or KurrentDB 26.0 LTS (verify the image).
    - *Measure:* aggregate load time vs stream length (1k to 1M events), with and without snapshots every 100 events.
    - *Anomaly:* two concurrent "book last seat" commands both succeed without an expected-version check; with the check, one gets a conflict.
    - *Evolution:* change `SeatsBooked v1 {count}` to `v2 {count, seatClass}` with an upcaster, and rebuild a projection from scratch to time it.
    - *GDPR:* crypto-shred one user's key, then rebuild and observe which projections degrade.
13. **DataFrames vs SQL.** Pivot MovieLens-style ratings into a user × movie matrix.
    - *Measure:* memory of a dense vs a sparse representation in Kotlin (e.g. a `DoubleArray` vs a map-based CSR), and the same group-by/pivot in DuckDB SQL, Spark 4.3 DataFrame (local[*], JVM 21) and Kotlin DataFrame.
    - *Anomaly:* reproduce label-alignment NaNs. Or show that Spark without `orderBy` returns rows in a different order across runs.

### Gaps
- Not verified this session: DynamoDB Local and KurrentDB image names and tags, Testcontainers module availability for KurrentDB and DynamoDB Local, current Hibernate 7 / Spring for GraphQL / graphql-kotlin / Kotlin DataFrame versions, and MongoDB's exact behavior when switching an existing collection to the `constraint` validation level.
- Lab numbers in parentheses (1,001 statements, about 2.5 writes/s, about 18 MB/hour) are expected values from cited limits or simple arithmetic. They have not been measured on hardware.
