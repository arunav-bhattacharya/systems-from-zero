# Relational databases and SQL (PostgreSQL lab track): research notes, as of 2026-11-07

Audience: a senior Java/Kotlin backend engineer whose employer runs Oracle. Lab database: PostgreSQL 18 in Docker on Apple Silicon. These notes are the source of truth for a 12 to 14 lesson track.

Provenance conventions used below:
- "[read]" means I fetched the page during this session and read the content the claim depends on.
- "[loads]" means I confirmed the URL returns HTTP 200 but did not re-read the specific passage; the claim is standard documented behaviour and the lesson writer should spot-check the wording before quoting.
- All SQL in these notes was written for PostgreSQL 18 but **was not executed** during research: the research machine had no Docker or psql. Run everything once before publishing.

---

## 1. Teaching order and scope: canonical concepts in sequence

### Takeaway
Teach in this order: relational model and NULL/3VL, then schema design and constraints, single-table queries, joins (including semi/anti joins), aggregation, subqueries/CTEs/recursion, window functions, the advanced query patterns (LATERAL, gaps-and-islands, pagination, pivot), writing data (upsert/MERGE/RETURNING/JSONB), transactions and isolation, locking patterns, indexes plus EXPLAIN, and calling SQL from the JVM. Each concept below has the specific PostgreSQL behaviour the lesson must get right.

### Cited Findings

**Relational model, NULL, three-valued logic**
- Logical processing order of a SELECT is documented step by step on the SELECT reference page: WITH, then FROM (incl. joins), WHERE, GROUP BY/HAVING, the select list (window functions are computed here), DISTINCT, set operations, ORDER BY, LIMIT/OFFSET, and finally locking clauses. Teaching it this way explains why a SELECT alias can't be used in WHERE and why window functions can't go in WHERE. [loads] — [PostgreSQL 18: SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- "If `ORDER BY` is not given, the rows are returned in whatever order the system finds fastest to produce." Without ORDER BY, LIMIT returns an unpredictable subset. [read] — [PostgreSQL 18: SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- For UNIQUE constraints, "null values are not considered equal, unless `NULLS NOT DISTINCT` is specified." By default, multiple NULLs are allowed in a UNIQUE column. [read] — [PostgreSQL 18: CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- `NOT IN` "behaves in unexpected ways if there is a null present": if the subquery yields a NULL, NOT IN can never be true and returns no rows. It also plans poorly, often as a slow subplan. The wiki's advice is to use `NOT EXISTS`. [read] — [PostgreSQL wiki: Don't Do This](https://wiki.postgresql.org/wiki/Don%27t_Do_This)
- Subquery expression semantics (EXISTS, IN, NOT IN, ANY/SOME, ALL), including the rule that NOT IN yields NULL rather than true when the subquery contains NULL and no match. [loads] — [PostgreSQL 18: Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html)
- `count(*)` counts input rows. `count(expr)` counts rows where expr is not NULL. Other aggregates ignore NULLs, and `sum` over zero rows returns NULL, not 0. [loads] — [PostgreSQL 18: Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)

**Schema design, types, constraints**
- Wiki guidance that maps directly to schema lessons: use `timestamptz` rather than `timestamp`; avoid `BETWEEN` on timestamps because both ends are inclusive (use `>=` and `<`); avoid `money` (prefer `numeric`, or integer minor units); avoid `char(n)`; don't use `varchar(n)` by default (use `text` plus a CHECK); use identity columns rather than `serial`; use lower-case unquoted identifiers; avoid rules; use UTF8. [read] — [PostgreSQL wiki: Don't Do This](https://wiki.postgresql.org/wiki/Don%27t_Do_This)
- Declaring a foreign key does not create an index on the referencing columns. The docs say it is often a good idea to add one, because a DELETE or key UPDATE on the referenced table has to scan the referencing table. [loads] — [PostgreSQL 18: Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- Exclusion constraints (`EXCLUDE USING gist (...)`) generalise UNIQUE to any commutative operator, for example "no overlapping ranges". Using `=` on scalar columns inside a GiST exclusion constraint needs the `btree_gist` contrib extension. [loads] — [PostgreSQL 18: Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html); [btree_gist](https://www.postgresql.org/docs/18/btree-gist.html)
- New in PostgreSQL 18: temporal keys. "The `WITHOUT OVERLAPS` column must have a range or multirange type." The other key columns must be GiST-equality-comparable, and "By default, only range types are supported, but you can use other types by adding the btree_gist extension (which is the expected way to use this feature)." `UNIQUE (id, valid_at WITHOUT OVERLAPS)` "behaves like `EXCLUDE USING GIST (id WITH =, valid_at WITH &&)`". A temporal FK uses `PERIOD`, requires the referenced key to be declared `WITHOUT OVERLAPS`, and does not support the CASCADE/SET NULL/SET DEFAULT/RESTRICT actions. [read] — [PostgreSQL 18: CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- PG18 generated columns: "`VIRTUAL` is the default." A virtual column is computed on read and takes no storage. Generation expressions must use immutable functions, can't reference other generated columns or other tables, and for VIRTUAL can only use built-in functions and types. [read] — [PostgreSQL 18: CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html); [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html)

**Querying: aggregation, grouping, subqueries, CTEs**
- GROUP BY, HAVING, GROUPING SETS / ROLLUP / CUBE, and LATERAL in FROM are documented under table expressions. [loads] — [PostgreSQL 18: Table Expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- The aggregate `FILTER (WHERE ...)` clause and window function call syntax are documented in value expressions. When a window has ORDER BY, the default frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which includes all peers of the current row (rows that tie on the ORDER BY). [loads] — [PostgreSQL 18: Value Expressions](https://www.postgresql.org/docs/18/sql-expressions.html)
- Frame modes are `RANGE | ROWS | GROUPS`, with optional exclusion. "In `ROWS` mode, offset counts rows. In `GROUPS` mode, it counts peer groups. In `RANGE` mode, an offset requires exactly one `ORDER BY` column." `EXCLUDE CURRENT ROW | GROUP | TIES | NO OTHERS`. [read] — [PostgreSQL 18: SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- Window function catalogue: row_number, rank, dense_rank, percent_rank, cume_dist, ntile, lag, lead, first_value, last_value, nth_value. [loads] — [PostgreSQL 18: Window Functions](https://www.postgresql.org/docs/18/functions-window.html); tutorial: [Window Functions tutorial](https://www.postgresql.org/docs/18/tutorial-window.html)
- WITH queries: non-recursive, side-effect-free CTEs that are referenced once are inlined by default (since PG12), and `MATERIALIZED` / `NOT MATERIALIZED` override this. `WITH RECURSIVE` covers UNION vs UNION ALL, the `SEARCH DEPTH|BREADTH FIRST BY` clause, and `CYCLE ... SET ... USING` cycle detection. Data-modifying statements are allowed in WITH. [loads] — [PostgreSQL 18: WITH Queries](https://www.postgresql.org/docs/18/queries-with.html)
- LATERAL: "allows the sub-SELECT to refer to columns of FROM items that appear before it in the FROM list." `LEFT JOIN LATERAL ... ON true` keeps outer rows that have no match. [read] — [PostgreSQL 18: SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- OFFSET: rows skipped by OFFSET still have to be computed in the server, so a large OFFSET can be inefficient. [loads] — [PostgreSQL 18: LIMIT and OFFSET](https://www.postgresql.org/docs/18/queries-limit.html). Keyset ("seek method") pagination is the alternative. [loads] — [Use The Index, Luke: No Offset](https://use-the-index-luke.com/no-offset)

**Writing data**
- `INSERT ... ON CONFLICT (target) DO NOTHING | DO UPDATE SET ... = EXCLUDED.col` gives an atomic insert-or-update even under concurrency. A single command cannot affect the same row twice. [loads] — [PostgreSQL 18: INSERT](https://www.postgresql.org/docs/18/sql-insert.html)
- MERGE (PG15+). In PG17: "Allow `MERGE` to use the `RETURNING` clause"; `merge_action()` "reports on the DML that generated the row"; `WHEN NOT MATCHED BY SOURCE` was added; and MERGE can target updatable views. [read] — [PG17 release notes](https://www.postgresql.org/docs/17/release-17.html)
- MERGE concurrency caveat, verbatim: "You may also wish to consider using `INSERT ... ON CONFLICT` as an alternative statement which offers the ability to run an `UPDATE` if a concurrent `INSERT` occurs." If one target row matches more than one source row, a repeated UPDATE/DELETE raises a cardinality violation and a repeated INSERT raises a uniqueness violation. `WHEN NOT MATCHED BY SOURCE` combined with `WHEN NOT MATCHED` makes the command perform a FULL join. [read] — [PostgreSQL 18: MERGE](https://www.postgresql.org/docs/18/sql-merge.html)
- PG18: `OLD`/`NEW` in `RETURNING` for INSERT/UPDATE/DELETE/MERGE, for example `UPDATE accounts SET balance = balance + 10 RETURNING old.balance AS before, new.balance AS after;`. The aliases can be renamed with `RETURNING WITH (OLD AS o, NEW AS n)`. [read] — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html); [PostgreSQL 18: MERGE](https://www.postgresql.org/docs/18/sql-merge.html)
- PG17 SQL/JSON: `JSON_TABLE()` (usable in FROM), the constructors `JSON()`, `JSON_SCALAR()`, `JSON_SERIALIZE()`, and the query functions `JSON_EXISTS()`, `JSON_QUERY()`, `JSON_VALUE()`. [read] — [PG17 release notes](https://www.postgresql.org/docs/17/release-17.html)
- json vs jsonb types, containment (`@>`), jsonpath, and jsonb GIN indexing with the `jsonb_ops` (default) and `jsonb_path_ops` operator classes. [loads] — [PostgreSQL 18: JSON Types](https://www.postgresql.org/docs/18/datatype-json.html); [JSON Functions](https://www.postgresql.org/docs/18/functions-json.html)

**Transactions, isolation, locking**
- PostgreSQL implements three distinct levels: "Read Uncommitted mode behaves like Read Committed." At Repeatable Read, phantom reads are "Allowed, but not in PG", but serialization anomalies are still possible. [read] — [PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- Read Committed: when an UPDATE/DELETE/SELECT FOR UPDATE finds a row that a concurrent transaction has changed, it waits, then "The search condition of the command (the `WHERE` clause) is re-evaluated to see if the updated version of the row still matches." The docs include an example (website.hits 9/10) where a concurrent DELETE silently misses a row. [read] — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- Repeatable Read "is implemented using a technique known ... as Snapshot Isolation". Updating a row that a concurrent transaction changed fails with `ERROR: could not serialize access due to concurrent update`, and the application "should abort the current transaction and retry the whole transaction from the beginning." [read] — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- Serializable uses Serializable Snapshot Isolation (SSI). Its predicate locks "do not cause any blocking and therefore can not play any part in causing a deadlock". Failures always carry SQLSTATE `40001`, with the message `could not serialize access due to read/write dependencies among transactions`. The docs' canonical write-skew example has two transactions sum `value` for class 1 and class 2 and each insert into the other class. [read] — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- The docs' performance advice for Serializable: declare transactions `READ ONLY` where possible; control the number of active connections (use a pool); keep transactions small; avoid sessions left "idle in transaction" (`idle_in_transaction_session_timeout`); drop explicit `FOR UPDATE`/`FOR SHARE` locks once you move to Serializable; tune the `max_pred_locks_*` settings; and note that "A sequential scan will always necessitate a relation-level predicate lock." [read] — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- A dedicated docs page covers handling serialization failures (retry 40001, and in general 40P01 deadlocks too). [loads] — [PostgreSQL 18: Serialization Failure Handling](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html)
- Row lock strengths are `FOR UPDATE | FOR NO KEY UPDATE | FOR SHARE | FOR KEY SHARE`, with `NOWAIT` (error immediately) or `SKIP LOCKED`. "Skipping locked rows provides an inconsistent view of the data, so this is not suitable for general purpose work, but can be used to avoid lock contention with multiple consumers accessing a queue-like table." Rows skipped by OFFSET still get locked. [read] — [PostgreSQL 18: SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- Explicit locking covers table-level and row-level lock modes, deadlocks, and advisory locks. [loads] — [PostgreSQL 18: Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)

**Indexes and EXPLAIN**
- B-tree multicolumn indexes are most efficient with constraints on the leading columns. PG18 adds B-tree skip scan, which "allows multi-column btree indexes to be used in more cases such as when there are no restrictions on the first or early indexed columns." [loads] — [Multicolumn Indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html); [read] — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html)
- Pages for the other index features: index-only scans and the visibility map; covering indexes via `INCLUDE`; partial indexes; expression indexes; GIN; BRIN. [loads] — [Index-Only Scans and Covering Indexes](https://www.postgresql.org/docs/18/indexes-index-only-scans.html); [CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html); [Partial Indexes](https://www.postgresql.org/docs/18/indexes-partial.html); [Indexes on Expressions](https://www.postgresql.org/docs/18/indexes-expressional.html); [GIN](https://www.postgresql.org/docs/18/gin.html); [BRIN](https://www.postgresql.org/docs/18/brin.html); [B-Tree](https://www.postgresql.org/docs/18/btree.html)
- PG18 EXPLAIN changes: "Automatically include `BUFFERS` output in `EXPLAIN ANALYZE`." Also new: fractional row counts, disabled nodes are shown, and the number of index lookups per index scan node is reported. [read] — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html); guide: [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- PG18 planner improvements relevant to "write it naturally" teaching: OR-clauses can be transformed to arrays ("for faster index processing"), some `IN (VALUES ...)` become `= ANY`, and some unnecessary self-joins are removed (`enable_self_join_elimination`). [read] — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html)
- PG17: "Allow btree indexes to more efficiently find a set of values, such as those supplied by `IN` clauses using constants." [read] — [PG17 release notes](https://www.postgresql.org/docs/17/release-17.html)
- Markus Winand's book covers concatenated-key column order. [loads] — [Use The Index, Luke: Concatenated Keys](https://use-the-index-luke.com/sql/where-clause/the-equals-operator/concatenated-keys)
- pg_stat_statements must be loaded via `shared_preload_libraries`. It is the standard tool for spotting N+1 (high `calls`, low per-call time). [loads] — [pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)

**JVM access**
- pgJDBC: `prepareThreshold` defaults to 5 ("start using server side prepared statements on the fifth execution"; -1 means immediately). `reWriteBatchedInserts` defaults to false; it rewrites batches into multi-row VALUES and "provides 2-3x performance improvement". `defaultRowFetchSize` defaults to 0 (fetch all rows at once). `preparedStatementCacheQueries` defaults to 256. `autosave` defaults to `never` (values always/never/conservative). `binaryTransfer` defaults to true. `sslmode` defaults to `prefer`. `ApplicationName` shows up in `pg_stat_activity`. `options` passes server settings such as `-c statement_timeout=5min`. The docs page is internally inconsistent on the `stringtype` default (the header says null, the text says VARCHAR); `stringtype=unspecified` lets the server infer the parameter type. [read] — [pgJDBC: Using the driver](https://jdbc.postgresql.org/documentation/use/)
- HikariCP "About Pool Sizing": "connections = ((core_count * 2) + effective_spindle_count)" is presented as a starting point to load-test around. Core count excludes hyperthreads, and spindle count is 0 for a fully cached data set. Worked example: a 4-core box with one disk gives 10. In the Oracle Real-World Performance demo, shrinking a pool from 2048 to 96 connections cut response time from about 100 ms to about 2 ms (over 50x). Pool-locking minimum: "pool size = Tn x (Cm - 1) + 1". Axiom: "You want a small pool, saturated with threads waiting for connections." [read] — [HikariCP wiki: About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)

### Inferences
- Recommended concept sequence: model → NULL/3VL → design/normalization → constraints/types → single-table SELECT → joins → aggregation → subqueries/CTEs/recursion → windows → patterns (LATERAL, islands, pagination, pivot) → writing data/JSONB → isolation → locking/queues → indexes/EXPLAIN → JVM. Isolation comes after DML so learners can write the anomalies themselves. Indexes come late so learners first run slow queries on a large dataset and then feel the fix.
- Teach semi-joins (EXISTS) and anti-joins (NOT EXISTS) together with joins, not with subqueries. Backend engineers reach for `IN (subquery)` and `LEFT JOIN ... WHERE x IS NULL` by habit, and NOT IN with NULL is the single most damaging trap.
- The logical processing order is the main mental model. Most "why doesn't this work" questions (aliases in WHERE, windows in WHERE, HAVING vs WHERE) are answered by it.

### Gaps
- I did not re-read the exact wording of the default-frame sentence on the Value Expressions page, the FK-index sentence on the Constraints page, or the OFFSET sentence on the LIMIT page. The URLs load and the behaviour is long-standing, but confirm the wording before quoting.
- I did not verify whether PG18 virtual generated columns can be indexed or used in constraints. The CREATE TABLE page I read is silent on this. My recollection is that indexes on virtual generated columns are not supported in 18. Test before teaching it.

---

## 2. Current versions as of November 2026 (PostgreSQL, SQL standard, JVM libraries, Oracle/MySQL deltas)

### Takeaway
Use **PostgreSQL 18 (18.6)** as the lab version. 18.0 was released 2025-09-25 and is supported until 2030-11-14. **PostgreSQL 19 is not GA**: RC1 shipped 2026-10-15 and GA is planned for **2026-11-19**. Beta 4 reverted SQL/PGQ and `FOR PORTION OF`, among other features. The SQL standard is still **SQL:2023**. Latest JVM artifacts on Maven Central: pgJDBC 42.7.14, HikariCP 7.1.0, Flyway 13.12.1, jOOQ 3.21.9, Exposed 1.6.1.

### Cited Findings

**PostgreSQL release status**
- Supported majors with current minors: 18 (18.6, first released Sept 25 2025, EOL Nov 14 2030); 17 (17.11, EOL Nov 8 2029); 16 (16.15, EOL Nov 9 2028); 15 (15.19, EOL Nov 11 2027); 14 (14.24, **EOL Nov 12 2026**, five days from today). 19 is not in the table. [read] — [PostgreSQL Versioning Policy](https://www.postgresql.org/support/versioning/)
- PG18 release date is 2025-09-25. Headline features [read] — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html):
  - Asynchronous I/O subsystem that "can improve performance of sequential scans, bitmap heap scans, vacuums, and other operations". It is controlled by `io_method`, `io_combine_limit` and `io_max_combine_limit`.
  - B-tree skip scan.
  - `uuidv7()`, which is "temporally sortable", plus a `uuidv4()` alias.
  - Virtual generated columns, now the default kind.
  - OAuth authentication: `oauth` method in pg_hba.conf, `oauth_validator_libraries`, built with `--with-libcurl`.
  - OLD/NEW in RETURNING.
  - Temporal PK/UNIQUE `WITHOUT OVERLAPS` and FK `PERIOD`.
  - pg_upgrade keeps optimizer statistics (extended statistics excluded).
  - BUFFERS on by default in EXPLAIN ANALYZE.
  - **Data checksums on by default in initdb** (`--no-data-checksums` turns them off).
  - MD5 passwords deprecated (warnings, `md5_password_warnings`).
  - NOT NULL constraints are stored in pg_constraint, can be named, and can be `NOT VALID`.
  - OR-to-array and self-join elimination planner changes.
  - Breaking: VACUUM/ANALYZE now process inheritance children by default (new `ONLY` option).
  - Breaking: `COPY FROM` no longer treats `\.` as EOF in CSV.
  - Breaking: unlogged partitioned tables are disallowed.
- `io_method` values: `worker` (default), `io_uring` (needs a build with liburing, Linux only), `sync`. Only settable at server start. `io_workers` defaults to 3. [read] — [PostgreSQL 18: Resource Consumption](https://www.postgresql.org/docs/18/runtime-config-resource.html)
- PG19 Beta 1 (2026-06-04) announced these SQL-level features: SQL/PGQ property graph queries; `UPDATE/DELETE ... FOR PORTION OF`; `GROUP BY ALL`; `INSERT ... ON CONFLICT DO SELECT ... RETURNING`; jsonpath string functions (`lower`, `upper`, `initcap`, `replace`, `split_part`, `trim` family); `ALTER TABLE ... MERGE/SPLIT PARTITIONS`; `WAIT FOR LSN`; and DDL-retrieval functions. Performance and ops items: AIO worker autoscaling (`io_min_workers`/`io_max_workers`); the `pg_plan_advice` and `pg_stash_advice` extensions; parallel autovacuum (`autovacuum_max_parallel_workers`) with a new scoring system; `REPACK` with a `CONCURRENTLY` option; up to 2x faster inserts when FK checks are present; anti-join optimizations; eager aggregation (`enable_eager_aggregate`); `EXPLAIN ANALYZE ... IO`; and online checksum toggling. Behaviour changes: **JIT disabled by default**, `default_toast_compression` = `lz4`, RADIUS auth removed. [read] — [PostgreSQL 19 Beta 1 announcement](https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/)
- PG19 Beta 4 **reverted**: SQL/PGQ; online enabling/disabling of data checksums; `FOR PORTION OF`; `MERGE PARTITIONS` / `SPLIT PARTITIONS`; `pg_get_role_ddl()` / `pg_get_tablespace_ddl()` / `pg_get_database_ddl()`; and a change forcing `LC_COLLATE` to C in the postmaster. The stated reason: so these "can be potentially be included in a later major release". [read] — [PostgreSQL 19 Beta 4 announcement](https://www.postgresql.org/about/news/postgresql-19-beta-4-released-3386/)
- PG19 RC 1 was posted 2026-10-15: "The planned date for the general availability of PostgreSQL 19 is November 19, 2026." Changes since Beta 4 are fixes to REPACK (CONCURRENTLY), pg_plan_advice, NULL-ability-based planner optimizations, automatic logical replication enablement, postgres_fdw stats import, and parallel autovacuum. `COPY (query) TO ... (FORMAT json)` now uses the query's column names; this implies **COPY ... FORMAT json is new in 19**. [read] — [PostgreSQL 19 RC 1 announcement](https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/)
- A search-result summary (not the official page) says RC 2 is due 2026-11-12, alongside the scheduled minor releases. [unverified, search snippet only] — [PostgreSQL 19 RC 1 announcement](https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/)
- Docker Hub `library/postgres` tags currently include `18.6`, `18`, `18-trixie`, `18-alpine`, `19rc1`, `19rc1-alpine`, and older `19beta1`..`19beta4`. `latest` is a PG18 tag (inference: the 18.x tags and `latest` appear together and 19 is RC only). [read via Docker Hub API] — [Docker Hub: postgres](https://hub.docker.com/_/postgres)

**SQL standard**
- SQL:2023 (ISO/IEC 9075:2023) "was formally adopted in June 2023". New in it:
  - Part 16 **SQL/PGQ** (property graph queries).
  - JSON: T801 JSON data type, T802 enhanced JSON type, T803 string-based JSON, T840 hex literals in SQL/JSON path, T860–T864 simplified accessor (dot/array syntax), T865–T878 item methods, T879–T882 JSON comparison.
  - Smaller optional features: F292 UNIQUE null treatment, F868 ORDER BY in grouped table, T054 GREATEST/LEAST, T055 string padding (LPAD/RPAD), T056 multi-character TRIM, T081 optional max length for strings, T133 enhanced cycle mark values, T626 ANY_VALUE, T662 underscores in numeric literals.
  - The article mentions no successor version. [read] — [Wikipedia: SQL:2023](https://en.wikipedia.org/wiki/SQL:2023)
- Markus Winand tracks feature support per product (MERGE, etc.) on modern-sql.com. His SQL:2023 page loads but is mostly a stub. [loads] — [modern-sql.com: SQL:2023](https://modern-sql.com/standard/2023); [modern-sql.com: MERGE support](https://modern-sql.com/caniuse/merge)

**JVM library versions (Maven Central `maven-metadata.xml`, fetched 2026-11-07)** — [Maven Central](https://repo1.maven.org/maven2/org/postgresql/postgresql/maven-metadata.xml)
- `org.postgresql:postgresql` (pgJDBC) **42.7.14**, last deployed 2026-10-07. The 42.7.x line continues; there is no 42.8.
- `com.zaxxer:HikariCP` **7.1.0**, last deployed 2026-06-14. The history runs 6.3.3 → 7.0.0 → 7.0.1 → 7.0.2 → 7.1.0.
- `org.flywaydb:flyway-core` **13.12.1**, last deployed 2026-11-05. `org.flywaydb:flyway-database-postgresql` 13.12.1 is a separate module.
- `org.jooq:jooq` **3.21.9**, last deployed 2026-09-25.
- `org.jetbrains.exposed:exposed-core` **1.6.1**, last deployed 2026-11-04.
- Docs: [pgJDBC changelogs](https://jdbc.postgresql.org/changelogs/), [HikariCP](https://github.com/brettwooldridge/HikariCP), [Flyway docs (Redgate)](https://documentation.red-gate.com/flyway), [jOOQ manual](https://www.jooq.org/doc/latest/manual/), [Exposed docs](https://www.jetbrains.com/help/exposed/home.html), [Exposed GitHub](https://github.com/JetBrains/Exposed) [all loads]

**Oracle and MySQL differences the learner will hit**
- Isolation per Hermitage [read] — [Hermitage](https://github.com/ept/hermitage). ★ marks each product's default level.
  - **Oracle** offers only "read committed" ★ and "serializable". Oracle "serializable" is actually **snapshot isolation**: it prevents lost update (P4) and read skew, but **not write skew (G2-item)**; G2 is prevented only in "some" cases.
  - **MySQL/InnoDB** "repeatable read" ★ is classed as monotonic atomic view and **does not prevent lost updates (P4)**. PMP and read skew are prevented only for read-only transactions.
  - **PostgreSQL** "read committed" ★ prevents G0–G1c and OTV. "repeatable read" is snapshot isolation (prevents P4 and G-single, not G2-item or G2). "serializable" prevents everything in the table.
- Oracle treats a zero-length character value as NULL (`'' IS NULL` is true in Oracle, false in PostgreSQL). [loads] — [Oracle SQL Reference: Nulls](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Nulls.html)
- The current Oracle docs set is **"Oracle AI Database 26ai"** (the /23/ URL serves the 26 docs). Its SQL developer features [read] — [Oracle: Application Development – SQL new features](https://docs.oracle.com/en/database/oracle/oracle-database/23/nfcoa/appdev_sql.html):
  - Syntax that converges with PostgreSQL: ISO `BOOLEAN` type, `IF [NOT] EXISTS` DDL, `SELECT` without `FROM` (no DUAL needed), table value constructor `VALUES`, GROUP BY column alias or position (and aliases in HAVING), `GROUP BY ALL`, and aggregate `FILTER`.
  - Analytic features: a `QUALIFY` clause (filter on window results; PostgreSQL has no equivalent, see Gaps), `JOIN TO ONE` (guards against fan-out), and `TIME_BUCKET`.
  - DML: direct joins in UPDATE/DELETE, `INSERT ... SET` / `BY NAME`, RETURNING old and new values for UPDATE/MERGE, and `SELECT ... FOR UPDATE [SKIP LOCKED]` with `FETCH FIRST`.
  - Functions: `UUID()` generation, plus `DATEADD` and `DATEDIFF`.
  - Schema: SQL domains and annotations.

### Inferences
- Lesson writer stance: target PG18 and use the `postgres:18` image. Add "PG19 sidebars" for `GROUP BY ALL` and `ON CONFLICT DO SELECT`. Neither appears in the Beta 4 revert list, but **confirm both in the final PG19 release notes after the 2026-11-19 GA**. Don't teach SQL/PGQ or `FOR PORTION OF` as PostgreSQL features: both were reverted from 19. Mention SQL/PGQ only as "in the SQL:2023 standard; Oracle 23ai/26ai ships a version; PostgreSQL reverted it from 19".
- The PG19 default change "JIT disabled by default" will make EXPLAIN output on 19 differ slightly from 18 (no JIT section on big analytic queries). Worth a footnote.
- Oracle-at-work mapping (author knowledge, not fetched this session; spot-check before publishing):
  - Oracle has no `ON CONFLICT`: use `MERGE`. MySQL uses `INSERT ... ON DUPLICATE KEY UPDATE`.
  - Oracle uses `FETCH FIRST n ROWS ONLY` (12c+; old code uses ROWNUM). PostgreSQL accepts both `LIMIT` and `FETCH FIRST`.
  - Oracle DDL auto-commits. PostgreSQL DDL is transactional, so a failed Flyway migration rolls back cleanly on PG but not on Oracle.
  - Oracle's `DATE` includes a time of day.
  - Oracle's equivalent of `bigint`/`numeric` is `NUMBER`.
  - Oracle `VARCHAR2` columns compared with `NVARCHAR` JDBC binds trigger implicit conversion and can disable index use.
  - MySQL lacks `FULL OUTER JOIN`.
  - Oracle reads never block writes and vice versa (multi-versioning, like PostgreSQL MVCC). The big behavioural differences are the empty-string-is-NULL rule and SERIALIZABLE being SI.
- The PG18 default of checksums-on and the PG18 Docker volume-path change (section 4) are the two operational changes most likely to trip up someone following an older tutorial.

### Gaps
- PG19 GA had not happened as of 2026-11-07. Recheck [the PG19 release notes](https://www.postgresql.org/docs/19/release-19.html) (not fetched) after 2026-11-19 for the final feature list. One blog cited 53 reverts during beta. I could not verify that number, so other features may have been dropped beyond the six listed in Beta 4.
- I did not verify the Java baseline for HikariCP 7.x, Flyway 13, jOOQ 3.21 or Exposed 1.6, or whether jOOQ 3.21 lists PostgreSQL 18/19 support. jOOQ's open source edition historically supports only open-source databases, so Oracle needs a commercial licence. [jOOQ download page](https://www.jooq.org/download/) loads, but I did not read the licence matrix.
- I did not determine whether pgJDBC 42.7.x supports the PG18 `oauth` auth method.
- Not checked: current MySQL GA/LTS versions, and whether PostgreSQL implements the SQL:2023 JSON simplified accessor (dot syntax) or `QUALIFY`. Neither appears in the PG18 or PG19 notes I read, so assume no.
- The `UUID()` detail on the Oracle page (which UUID versions it generates) came back garbled in the fetch summary. Verify before quoting.

---

## 3. Misconceptions to address (with the correct behaviour)

### Takeaway
The highest-value misconceptions: NULL comparisons, NOT IN with NULL, COUNT variants, "RR prevents all anomalies", ORDER BY guarantees, the default window frame with ties, row multiplication when aggregating across two one-to-many joins, DISTINCT as a band-aid, "indexes always help", OFFSET cost, "Serializable is unusable", and "FKs are indexed automatically". Each one maps to a lab exercise that exposes it.

### Cited Findings
- **`NULL = NULL` is true.** Wrong: it yields NULL (unknown), and WHERE keeps only rows that evaluate to true. Even UNIQUE treats NULLs as not equal unless `NULLS NOT DISTINCT` is set. Use `IS [NOT] DISTINCT FROM` for null-safe equality. — [CREATE TABLE (NULLS DISTINCT)](https://www.postgresql.org/docs/18/sql-createtable.html) [read]; [Value Expressions](https://www.postgresql.org/docs/18/sql-expressions.html) [loads]
- **`NOT IN (subquery)` is the same as `NOT EXISTS`.** Wrong when the subquery can yield NULL: NOT IN returns no rows, and it often plans worse. — [Don't Do This](https://wiki.postgresql.org/wiki/Don%27t_Do_This) [read]; [Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html) [loads]
- **`COUNT(*)` and `COUNT(col)` are interchangeable.** Wrong: `count(col)` skips NULLs. `sum()` of no rows is NULL. — [Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html) [loads]
- **Rows come back in insertion/PK order.** Wrong: "whatever order the system finds fastest". LIMIT without ORDER BY is nondeterministic. — [SELECT](https://www.postgresql.org/docs/18/sql-select.html) [read]
- **Repeatable Read prevents all anomalies.** Wrong: PG RR is snapshot isolation and allows write skew (G2-item). Only SERIALIZABLE (SSI) prevents it. — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html) [read]; [Hermitage](https://github.com/ept/hermitage) [read]
- **"Oracle SERIALIZABLE = PostgreSQL SERIALIZABLE."** Wrong: Oracle's is SI, and write skew is still possible. — [Hermitage](https://github.com/ept/hermitage) [read]
- **SERIALIZABLE is too slow to use.** Overstated: SSI predicate locks never block. The costs are tracking overhead and retries, and the docs give mitigation steps (READ ONLY, short transactions, a pool, index-friendly plans because seq scans take relation-level predicate locks). — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html) [read]
- **Read Committed reads are consistent within a transaction.** Wrong: each statement sees a fresh snapshot, and concurrent UPDATE re-evaluation can make statements skip rows (the hits=9/10 example). — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html) [read]
- **OFFSET pagination is free.** Wrong: skipped rows are still computed, and `FOR UPDATE` + OFFSET even locks them. — [LIMIT and OFFSET](https://www.postgresql.org/docs/18/queries-limit.html) [loads]; [SELECT](https://www.postgresql.org/docs/18/sql-select.html) [read]; [No Offset](https://use-the-index-luke.com/no-offset) [loads]
- **`BETWEEN` is fine for time ranges.** Wrong: both ends are inclusive. Use half-open `>= start AND < end`. — [Don't Do This](https://wiki.postgresql.org/wiki/Don%27t_Do_This) [read]
- **Declaring an FK creates an index.** Wrong in PostgreSQL (and Oracle). Add the index on the referencing column yourself. — [Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html) [loads]
- **A running total with `SUM() OVER (ORDER BY ts)` adds one row at a time.** Not when there are ties: the default frame is RANGE, which includes peers. Use `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` or a unique tiebreaker. — [Value Expressions](https://www.postgresql.org/docs/18/sql-expressions.html) [loads]; [SELECT frame clause](https://www.postgresql.org/docs/18/sql-select.html) [read]
- **CTEs are optimization fences.** Outdated: since PG12, single-reference side-effect-free CTEs are inlined, and `MATERIALIZED` forces the old behaviour. — [WITH Queries](https://www.postgresql.org/docs/18/queries-with.html) [loads]
- **A multicolumn index is useless without the leading column.** Mostly true before 18. PG18 skip scan relaxes it when the leading column has few distinct values. Column order still matters. — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html) [read]; [Concatenated Keys](https://use-the-index-luke.com/sql/where-clause/the-equals-operator/concatenated-keys) [loads]
- **A big pool is a fast pool.** Wrong: 2048 → 96 connections cut latency from about 100 ms to about 2 ms in the Oracle demo the HikariCP wiki cites. — [About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing) [read]
- **MERGE is the safe concurrent upsert.** Not in PostgreSQL. The docs point to `INSERT ... ON CONFLICT` for concurrent-insert safety. — [MERGE](https://www.postgresql.org/docs/18/sql-merge.html) [read]

### Inferences
- **Implicit join row multiplication** (author analysis, standard SQL semantics). `customers JOIN payments JOIN refunds` followed by `SUM(payments.amount)` counts each payment once per refund, and each refund once per payment. Fix it by pre-aggregating each child in its own subquery or LATERAL and then joining 1:1. `COUNT(DISTINCT ...)` or `SUM(DISTINCT ...)` "fixes" are wrong too, because two genuinely equal amounts collapse into one.
- **DISTINCT as a band-aid**: duplicates in output usually mean a join is missing a key column or should be a semi-join (`EXISTS`). Teach the habit "if you need DISTINCT, explain why".
- **"Indexes always help"**: a predicate matching about 93% of rows (`status = 'succeeded'` in the lab data) should be a seq scan. Every index also costs on writes and adds vacuum work. The lab exercise has learners create an index, see it ignored, and explain why.
- **Functions or casts on indexed columns**:
  - `WHERE created_at::date = '2026-05-01'` can't use a plain index on `created_at`. Also, the `timestamptz → date` cast depends on the `TimeZone` setting, so it can't be used in an expression index. `(created_at AT TIME ZONE 'UTC')::date` can (author knowledge; verify in the lab).
  - Comparing a `bigint` column with a `numeric` bind (for example a JDBC `setBigDecimal`) makes PostgreSQL cast the column side, so the B-tree on the bigint isn't used (author knowledge; verify with EXPLAIN in the lab).
- **`now()` is constant inside a transaction** (it is the transaction start time). This confuses people in two-session labs. Use `clock_timestamp()` when you need wall time (author knowledge; standard documented behaviour).

### Gaps
- I found no authoritative benchmark quantifying SSI overhead on modern PostgreSQL. Avoid quoting percentages.
- I couldn't load the comparison-operators page (`functions-comparison.html`) during the URL check (timeout). It is the natural citation for `IS DISTINCT FROM`; recheck it.

---

## 4. Lab environment: Docker on Apple Silicon, datasets, psql, payments/ledger schema

### Takeaway
Run `postgres:18` natively on arm64 (the image ships arm64v8). **Mount the volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data`**: the image changed for 18+. Use a home-grown payments/ledger schema, filled with `generate_series`, as the spine of the course. Use the Postgres Pro "Airlines" demo (MIT licence, 3m/6m/1y/2y sizes, PG15+) as an optional large real-world dataset. pagila and Chinook are fine for quick join drills.

### Cited Findings
- Docker image facts [read] — [Docker Hub: postgres](https://hub.docker.com/_/postgres):
  - "the `PGDATA` environment variable of the image was changed to be version specific in PostgreSQL 18 and above"; "For 18 it is `/var/lib/postgresql/18/docker`."
  - "The defined `VOLUME` was changed in 18 and above to `/var/lib/postgresql`." For 17 and below, mount at `/var/lib/postgresql/data`.
  - "The only variable required is `POSTGRES_PASSWORD`."
  - Supported architectures include `arm64v8`.
- Postgres Pro demo database ("Airlines", dated 2025-09-01) [read] — [Postgres Pro demodb](https://postgrespro.com/community/demodb):
  - Files: `demo-20250901-3m.sql.gz` (133 MB download, about 1.3 GB in the DB), `-6m` (276 MB, about 2.7 GB), `-1y` (558 MB, about 5.4 GB), `-2y` (1137 MB, about 11 GB). Downloaded from `https://edu.postgrespro.ru/<file>`.
  - Requires PostgreSQL 15+. MIT licence.
  - Tables: `airplanes_data, airports_data, boarding_passes, bookings, flights, routes, seats, segments, tickets`. Views: `airplanes, airports, timetable`.
  - Load: `gunzip -c demo-20250901-3m.sql.gz | psql -U postgres`. This drops and recreates an existing `demo` DB.
  - The small version has 21,758 flights; the data covers 5,501 airports.
- pagila (PostgreSQL port of Sakila) and Chinook repos. [loads] — [pagila](https://github.com/devrimgunduz/pagila); [Chinook](https://github.com/lerocha/chinook-database)
- psql reference (meta-commands such as `\timing`, `\x`, `\pset null`, `\gset`, `\watch`, `\e`, `\copy`, `\set ON_ERROR_ROLLBACK`). [loads] — [psql](https://www.postgresql.org/docs/18/app-psql.html)
- `generate_series` and other set-returning functions. [loads] — [Set Returning Functions](https://www.postgresql.org/docs/18/functions-srf.html)
- `uuidv7()` is new in PG18. [read] — [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html); [UUID Functions](https://www.postgresql.org/docs/18/functions-uuid.html) [loads]

### Inferences

#### Container setup (macOS, Apple Silicon)
```bash
docker run -d --name pglab \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  --shm-size=1g \
  -v pglab18:/var/lib/postgresql \
  postgres:18 \
  -c shared_preload_libraries=pg_stat_statements \
  -c track_io_timing=on
docker exec -it pglab psql -U postgres
# Two sessions for concurrency labs: open a second terminal and run the same docker exec.
```
- Use `--shm-size`: Docker's default `/dev/shm` is 64 MB, and parallel hash joins on multi-million-row tables can fail with "could not resize shared memory segment". This is a known community issue, not re-verified this session.
- `track_io_timing=on` adds I/O timings to EXPLAIN (ANALYZE, BUFFERS) output.
- Docker Desktop's VM CPU/RAM limits bound everything. Have learners record the VM's core count, since it feeds the HikariCP sizing exercise.
- `io_uring` isn't usable on macOS hosts or with the default build, so `io_method=worker` (the default) is what learners will see. This is an inference from the docs [read] — [Resource Consumption](https://www.postgresql.org/docs/18/runtime-config-resource.html).
- The Postgres Pro download host is a `.ru` domain. Corporate networks may block it, so give pagila as the fallback.

#### psql habits to teach on day 1
`\pset null '∅'` (makes NULLs visible; essential for the 3VL lesson), `\timing on`, `\x auto`, `\d+ table`, `\di+`, `\dt`, `\df`, `\e` (edit in $EDITOR), `\i file.sql`, `\copy`, `\watch 1` (rerun a query, useful for watching a queue drain), `SELECT ... \gset` (store results into psql variables), `\set ON_ERROR_ROLLBACK interactive` (a typo doesn't abort the open transaction), `\set AUTOCOMMIT off` (emulates JDBC `autoCommit=false`), `\errverbose`, `\conninfo`. A `~/.psqlrc` with `\pset null`, `\timing` and `\x auto` saves friction.

#### Proposed lab schema: payments/ledger (author design, untested)
Design choices worth calling out in lessons:
- Money is stored as `bigint` minor units. The wiki says avoid `money` and use numeric or integers.
- `timestamptz` everywhere.
- `text` + CHECK instead of `varchar(n)` or `char(n)`.
- Identity columns, `BY DEFAULT` so the loader can supply explicit ids. Mention that `ALWAYS` is stricter in production.
- A signed double-entry ledger in which every journal sums to zero.
- A denormalized `accounts.balance_minor` cache, used to discuss denormalization and to stage the lost-update lab.
- A temporal PK for fee schedules (PG18).
- A `uuidv7()` idempotency key (PG18).
- A virtual generated column (PG18).
- A partial unique index.
- Only PK/UNIQUE indexes at first. FK and query indexes are added in the index lesson, so learners feel the slowness first.

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;          -- scalar "=" inside GiST (temporal PK / EXCLUDE)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- requires shared_preload_libraries (see docker run)

CREATE TABLE merchants (
  merchant_id   bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name          text NOT NULL,
  mcc           text NOT NULL CHECK (mcc ~ '^[0-9]{4}$'),           -- merchant category code
  country_code  text NOT NULL CHECK (country_code ~ '^[A-Z]{2}$'),
  onboarded_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE customers (
  customer_id   bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  email         text NOT NULL UNIQUE,
  full_name     text NOT NULL,
  country_code  text NOT NULL CHECK (country_code ~ '^[A-Z]{2}$'),
  referred_by   bigint REFERENCES customers (customer_id),           -- referral tree (recursive CTE lesson)
  created_at    timestamptz NOT NULL DEFAULT now(),
  CHECK (referred_by <> customer_id)
);

CREATE TABLE accounts (
  account_id    bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  kind          text NOT NULL CHECK (kind IN ('customer','merchant','internal')),
  customer_id   bigint REFERENCES customers,
  merchant_id   bigint REFERENCES merchants,
  currency      text NOT NULL DEFAULT 'USD' CHECK (currency ~ '^[A-Z]{3}$'),
  status        text NOT NULL DEFAULT 'active' CHECK (status IN ('active','frozen','closed')),
  balance_minor bigint NOT NULL DEFAULT 0,                            -- denormalized cache of SUM(ledger)
  opened_at     timestamptz NOT NULL DEFAULT now(),
  CHECK ((kind = 'customer') = (customer_id IS NOT NULL)),
  CHECK ((kind = 'merchant') = (merchant_id IS NOT NULL))
);

CREATE TABLE cards (
  card_id     bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  account_id  bigint NOT NULL REFERENCES accounts,
  brand       text NOT NULL CHECK (brand IN ('visa','mastercard','amex')),
  pan_last4   text NOT NULL CHECK (pan_last4 ~ '^[0-9]{4}$'),        -- never store full PANs
  expires_on  date NOT NULL,
  status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active','blocked','expired')),
  is_primary  boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX cards_one_primary_per_account ON cards (account_id) WHERE is_primary;  -- partial unique

CREATE TABLE payments (
  payment_id    bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  payment_uid   uuid NOT NULL DEFAULT uuidv7() UNIQUE,                -- PG18; idempotency key, time-ordered
  card_id       bigint NOT NULL REFERENCES cards,
  merchant_id   bigint NOT NULL REFERENCES merchants,
  amount_minor  bigint NOT NULL CHECK (amount_minor > 0),
  currency      text NOT NULL DEFAULT 'USD',
  status        text NOT NULL CHECK (status IN ('pending','succeeded','failed')),
  created_at    timestamptz NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}',
  amount_major  numeric GENERATED ALWAYS AS (amount_minor / 100.0)  -- PG18: VIRTUAL by default
);

CREATE TABLE refunds (
  refund_id     bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  payment_id    bigint NOT NULL REFERENCES payments,
  amount_minor  bigint NOT NULL CHECK (amount_minor > 0),
  reason        text NOT NULL,
  created_at    timestamptz NOT NULL
  -- "sum(refunds) <= payment amount" cannot be a CHECK (cross-row): lesson 3/12 discussion
);

CREATE SEQUENCE journal_id_seq;
CREATE TABLE ledger_entries (
  entry_id      bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  journal_id    bigint NOT NULL,                                      -- all legs of one posting share it
  account_id    bigint NOT NULL REFERENCES accounts,
  payment_id    bigint REFERENCES payments,
  refund_id     bigint REFERENCES refunds,
  entry_type    text NOT NULL CHECK (entry_type IN ('deposit','payment','refund','withdrawal','fee')),
  amount_minor  bigint NOT NULL CHECK (amount_minor <> 0),            -- signed: + credit, - debit
  created_at    timestamptz NOT NULL
);

CREATE TABLE merchant_fee_schedules (                                 -- PG18 temporal primary key
  merchant_id   bigint NOT NULL REFERENCES merchants,
  valid_during  tstzrange NOT NULL,
  fee_bps       int NOT NULL CHECK (fee_bps BETWEEN 0 AND 1000),
  PRIMARY KEY (merchant_id, valid_during WITHOUT OVERLAPS)
  -- pre-18 equivalent: EXCLUDE USING gist (merchant_id WITH =, valid_during WITH &&)
);

CREATE TABLE login_events (                                           -- gaps-and-islands lesson
  event_id     bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  customer_id  bigint NOT NULL REFERENCES customers,
  occurred_at  timestamptz NOT NULL,
  success      boolean NOT NULL,
  ip           inet
);

CREATE TABLE jobs (                                                   -- SKIP LOCKED queue lesson
  job_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kind       text NOT NULL,
  payload    jsonb NOT NULL,
  status     text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),
  run_after  timestamptz NOT NULL DEFAULT now(),
  attempts   int NOT NULL DEFAULT 0,
  locked_by  text,
  locked_at  timestamptz
);
CREATE INDEX jobs_ready_idx ON jobs (run_after) WHERE status = 'queued';
```

#### Volume generator (generate_series; untested; deterministic with setseed)
Target volumes: 5k merchants, 100k customers, 155k accounts, 200k cards, 2M payments plus about 1k injected near-duplicates, about 37k refunds, about 7M ledger rows, 1M+ login events, 10k jobs. The total size is my estimate, not measured: a few GB at most. Scale the payment count down if the Docker VM is small.

```sql
SELECT setseed(0.42);   -- reproducible random() within this session

INSERT INTO merchants (merchant_id, name, mcc, country_code, onboarded_at)
SELECT g, 'Merchant ' || g,
       (ARRAY['5411','5812','5999','4111','5732','7011'])[1 + floor(random()*6)::int],
       (ARRAY['US','GB','IN','DE','FR','SG'])[1 + floor(random()*6)::int],
       timestamptz '2022-01-01 00:00+00' + random() * interval '4 years'
FROM generate_series(1, 5000) AS g;

-- referred_by points only to lower ids => an acyclic random tree; ~30% of customers were referred
INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at)
SELECT g, 'user' || g || '@example.com', 'Customer ' || g,
       (ARRAY['US','GB','IN','DE','FR','SG','CA','AU'])[1 + floor(random()*8)::int],
       CASE WHEN g > 100 AND random() < 0.3 THEN 1 + floor(random() * (g - 1))::bigint END,
       timestamptz '2023-01-01 00:00+00' + g * interval '15 minutes'
FROM generate_series(1, 100000) AS g;

-- account ids: 1..100000 primary customer accounts, 100001..150000 second accounts (even customers),
--              150001..155000 merchant settlement accounts, 155001 = external clearing (internal)
INSERT INTO accounts (account_id, kind, customer_id, status, opened_at)
SELECT customer_id, 'customer', customer_id,
       CASE WHEN random() < 0.97 THEN 'active' ELSE 'frozen' END, created_at
FROM customers;
INSERT INTO accounts (account_id, kind, customer_id, opened_at)
SELECT 100000 + customer_id / 2, 'customer', customer_id, created_at + interval '90 days'
FROM customers WHERE customer_id % 2 = 0;
INSERT INTO accounts (account_id, kind, merchant_id, opened_at)
SELECT 150000 + merchant_id, 'merchant', merchant_id, onboarded_at FROM merchants;
INSERT INTO accounts (account_id, kind) VALUES (155001, 'internal');

INSERT INTO cards (card_id, account_id, brand, pan_last4, expires_on, status)
SELECT g, 1 + floor(random() * 150000)::bigint,
       (ARRAY['visa','mastercard','amex'])[1 + floor(random()*3)::int],
       lpad(floor(random() * 10000)::int::text, 4, '0'),
       date '2027-01-01' + floor(random() * 1460)::int,
       CASE WHEN random() < 0.9 THEN 'active' ELSE 'blocked' END
FROM generate_series(1, 200000) AS g;
-- one primary card per account (DISTINCT ON demo)
UPDATE cards c SET is_primary = true
FROM (SELECT DISTINCT ON (account_id) card_id FROM cards WHERE status = 'active'
      ORDER BY account_id, card_id) p
WHERE c.card_id = p.card_id;

-- 2M payments over 300 days; ids correlate with time (so BRIN works on payments.created_at).
-- Merchant popularity is skewed (low ids hot); amounts are log-uniform ~$0.55..$220.
-- The inner subquery has a volatile target list, so PostgreSQL won't flatten it: r is drawn once per row.
INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at, metadata)
SELECT g,
       1 + floor(random() * 200000)::bigint,
       1 + floor(5000 * power(random(), 3))::bigint,
       round(exp(4 + random() * 6))::bigint,
       CASE WHEN r < 0.93 THEN 'succeeded' WHEN r < 0.99 THEN 'failed' ELSE 'pending' END,
       timestamptz '2026-01-01 00:00+00' + g * interval '12.96 seconds' + random() * interval '10 seconds',
       jsonb_build_object(
         'channel', (ARRAY['web','ios','android','pos'])[1 + floor(random()*4)::int],
         'risk', jsonb_build_object(
                   'score', floor(random() * 100)::int,
                   'rules', CASE WHEN random() < 0.05 THEN '["velocity"]'::jsonb
                                 WHEN random() < 0.05 THEN '["geo_mismatch"]'::jsonb
                                 ELSE '[]'::jsonb END))
FROM (SELECT g, random() AS r FROM generate_series(1, 2000000) AS g) AS s;

-- identity sequences must catch up before any DEFAULT-id insert
SELECT setval(pg_get_serial_sequence('merchants','merchant_id'), (SELECT max(merchant_id) FROM merchants));
SELECT setval(pg_get_serial_sequence('customers','customer_id'), (SELECT max(customer_id) FROM customers));
SELECT setval(pg_get_serial_sequence('accounts','account_id'),   (SELECT max(account_id)  FROM accounts));
SELECT setval(pg_get_serial_sequence('cards','card_id'),         (SELECT max(card_id)     FROM cards));
SELECT setval(pg_get_serial_sequence('payments','payment_id'),   (SELECT max(payment_id)  FROM payments));

-- ~0.05% injected near-duplicates (same card, merchant, amount within 4 minutes), flagged for grading
INSERT INTO payments (card_id, merchant_id, amount_minor, status, created_at, metadata)
SELECT card_id, merchant_id, amount_minor, status,
       created_at + random() * interval '4 minutes',
       metadata || '{"injected_dup": true}'
FROM payments WHERE status = 'succeeded' AND random() < 0.0005;

-- ~2% refunds, 70% full / 30% partial
INSERT INTO refunds (payment_id, amount_minor, reason, created_at)
SELECT payment_id,
       CASE WHEN random() < 0.7 THEN amount_minor ELSE greatest(1, (amount_minor * random())::bigint) END,
       (ARRAY['customer_request','duplicate','fraud'])[1 + floor(random()*3)::int],
       created_at + random() * interval '20 days'
FROM payments WHERE status = 'succeeded' AND random() < 0.02;

-- Ledger: monthly deposits (external clearing -> customer), payments (customer -> merchant),
-- refunds (merchant -> customer). Each CTE is referenced twice, so it is materialized
-- and nextval() runs once per journal.
WITH d AS (
  SELECT a.account_id, (100000 + floor(random() * 400000))::bigint AS amt,
         m + random() * interval '3 days' AS ts, nextval('journal_id_seq') AS journal_id
  FROM accounts a
  CROSS JOIN generate_series(timestamptz '2026-01-01 00:00+00', timestamptz '2026-10-01 00:00+00', interval '1 month') AS m
  WHERE a.kind = 'customer'
)
INSERT INTO ledger_entries (journal_id, account_id, entry_type, amount_minor, created_at)
SELECT journal_id, account_id, 'deposit',  amt, ts FROM d
UNION ALL
SELECT journal_id, 155001,     'deposit', -amt, ts FROM d;

WITH j AS (
  SELECT p.payment_id, p.merchant_id, p.amount_minor, p.created_at, c.account_id AS card_account_id,
         nextval('journal_id_seq') AS journal_id
  FROM payments p JOIN cards c ON c.card_id = p.card_id
  WHERE p.status = 'succeeded'
)
INSERT INTO ledger_entries (journal_id, account_id, payment_id, entry_type, amount_minor, created_at)
SELECT journal_id, card_account_id,       payment_id, 'payment', -amount_minor, created_at FROM j
UNION ALL
SELECT journal_id, 150000 + merchant_id,  payment_id, 'payment',  amount_minor, created_at FROM j;

WITH r AS (
  SELECT f.refund_id, f.payment_id, f.amount_minor, f.created_at,
         c.account_id AS card_account_id, 150000 + p.merchant_id AS merchant_account_id,
         nextval('journal_id_seq') AS journal_id
  FROM refunds f JOIN payments p ON p.payment_id = f.payment_id JOIN cards c ON c.card_id = p.card_id
)
INSERT INTO ledger_entries (journal_id, account_id, payment_id, refund_id, entry_type, amount_minor, created_at)
SELECT journal_id, card_account_id,     payment_id, refund_id, 'refund',  amount_minor, created_at FROM r
UNION ALL
SELECT journal_id, merchant_account_id, payment_id, refund_id, 'refund', -amount_minor, created_at FROM r;

UPDATE accounts a SET balance_minor = s.bal
FROM (SELECT account_id, sum(amount_minor) AS bal FROM ledger_entries GROUP BY account_id) s
WHERE a.account_id = s.account_id;

-- login events: 1M background events (10% failures) + 200 injected brute-force bursts of 8 failures
INSERT INTO login_events (customer_id, occurred_at, success, ip)
SELECT 1 + floor(random() * 100000)::bigint,
       timestamptz '2026-01-01 00:00+00' + random() * interval '300 days',
       random() < 0.9,
       ('10.' || floor(random()*256) || '.' || floor(random()*256) || '.' || floor(random()*256))::inet
FROM generate_series(1, 1000000);
INSERT INTO login_events (customer_id, occurred_at, success, ip)
SELECT s.c, s.t0 + k * interval '20 seconds', false, '203.0.113.7'   -- TEST-NET-3 address
FROM (SELECT 1 + floor(random() * 100000)::bigint AS c,
             timestamptz '2026-03-01 00:00+00' + random() * interval '200 days' AS t0
      FROM generate_series(1, 200)) AS s
CROSS JOIN generate_series(1, 8) AS k;

INSERT INTO jobs (kind, payload, run_after)
SELECT (ARRAY['send_receipt','settle_merchant','fraud_review'])[1 + floor(random()*3)::int],
       jsonb_build_object('payment_id', 1 + floor(random() * 2000000)::bigint),
       now() - random() * interval '1 hour'
FROM generate_series(1, 10000);

VACUUM (ANALYZE);   -- fresh stats + visibility map (needed for index-only scans later)
```

Write-skew fixture: a customer with two accounts, each holding $50. Business rule: the customer's combined balance must stay at or above 0.
```sql
INSERT INTO customers (customer_id, email, full_name, country_code) VALUES (900001, 'skew@example.com', 'Write Skew', 'US');
INSERT INTO accounts (account_id, kind, customer_id) VALUES (900001, 'customer', 900001), (900002, 'customer', 900001);
WITH j AS (SELECT nextval('journal_id_seq') AS id, acct FROM (VALUES (900001), (900002)) AS v(acct))
INSERT INTO ledger_entries (journal_id, account_id, entry_type, amount_minor, created_at)
SELECT id, acct,   'deposit',  5000, now() FROM j
UNION ALL
SELECT id, 155001, 'deposit', -5000, now() FROM j;
```

#### Dataset recommendation
- Primary: the custom payments schema above. It matches the learner's domain and has ground truth built in: injected duplicates, injected login bursts, the double-entry invariant, and the balance cache that can be reconciled against the ledger.
- Optional: the Postgres Pro Airlines `3m` file (about 1.3 GB) for "read a real schema" and extra EXPLAIN practice.
- Quick drills: pagila (films/rentals) if the payments loader isn't ready yet.

### Gaps
- None of the SQL above was executed (no Docker available on the research machine). In particular, check:
  - that the volatile-subquery trick in the payments insert really draws `r` once per row;
  - that `merchant_fee_schedules` creates cleanly on 18.6 with btree_gist;
  - how long the load takes on an M-series laptop with Docker Desktop defaults (unknown).
- The `--shm-size` advice comes from community experience; it is not on the Docker Hub text I read.

---

## 5. Lesson outline (14 lessons, 2 to 3 exercises each, expected result shapes)

### Takeaway
Fourteen lessons build from the model to production JVM practice, all on the same payments dataset. Each lesson has one "trap" exercise that exposes a misconception from section 3. Exercise results are described by shape (columns, approximate row counts, what a correct answer looks like) so the writer can grade without exact numbers.

### Cited Findings
- The patterns used below come from the docs read above:
  - LATERAL with `LEFT JOIN LATERAL ... ON true`: [SELECT](https://www.postgresql.org/docs/18/sql-select.html)
  - Frame modes and EXCLUDE: [SELECT](https://www.postgresql.org/docs/18/sql-select.html)
  - Write-skew sum example: [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
  - SKIP LOCKED for queue-like tables: [SELECT](https://www.postgresql.org/docs/18/sql-select.html)
  - MERGE RETURNING with merge_action() and OLD/NEW: [MERGE](https://www.postgresql.org/docs/18/sql-merge.html)
  - Keyset pagination: [No Offset](https://use-the-index-luke.com/no-offset)
  - Pool sizing: [About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)
  - Batch rewrite: [pgJDBC](https://jdbc.postgresql.org/documentation/use/)
  - Hermitage anomaly names: [Hermitage](https://github.com/ept/hermitage)
  - Skip scan and EXPLAIN BUFFERS default: [PG18 release notes](https://www.postgresql.org/docs/18/release-18.html)

### Inferences (the outline; author design)

**L1. The relational model, the lab, and NULL**
Relations as sets of tuples; SQL tables are bags. Keys (super, candidate, primary, foreign). Logical query processing order. NULL and 3VL. Docker plus psql setup, and loading the generator.
- Ex 1.1: Evaluate `SELECT NULL = NULL, NULL IS NULL, NULL IS DISTINCT FROM NULL, true OR NULL, false AND NULL, NULL AND true;` with `\pset null '∅'`. Expected: `∅ | t | f | t | f | ∅`.
- Ex 1.2 (trap): `count(*) FILTER (WHERE referred_by = 5) + count(*) FILTER (WHERE referred_by <> 5)` vs `count(*)` on customers. Expected: the sum is far below 100,000, because the roughly 70% NULLs fall into neither bucket. Then compare `count(*)`, `count(referred_by)`, `count(DISTINCT referred_by)`: three different numbers, with `count(referred_by)` ≈ 30k.
- Ex 1.3: List the candidate keys of `payments` (payment_id, payment_uid) and explain why `(card_id, created_at)` is not one.

**L2. Schema design and normalization**
Functional dependencies; 1NF, 2NF, 3NF, BCNF; anomalies (update/insert/delete); when to denormalize (read-heavy caches, reporting) and what it costs in correctness.
- Ex 2.1: Given a flat CSV-style `payments_export(payment_id, customer_email, customer_name, card_last4, card_brand, merchant_name, mcc, mcc_description, amount)`, list the FDs and decompose it to BCNF. Expected: separate customers, cards, merchants, `mcc_codes(mcc → description)` and payments relations. `mcc → mcc_description` is the transitive dependency that breaks 3NF.
- Ex 2.2: Reconcile the denormalized cache: find accounts whose `balance_minor` ≠ `SUM(ledger_entries.amount_minor)`. Expected: 0 rows right after the load. Then insert one ledger row by hand and get exactly 1 row. Discuss triggers vs app-maintained caches vs computing on read.
- Ex 2.3: Check the double-entry invariant with `SELECT journal_id FROM ledger_entries GROUP BY journal_id HAVING sum(amount_minor) <> 0`. Expected: 0 rows.

**L3. Constraints, keys and types**
PK/FK (ON DELETE actions), UNIQUE (incl. `NULLS NOT DISTINCT`), CHECK (single-row only), exclusion constraints, PG18 `WITHOUT OVERLAPS`, identity vs serial, `uuidv7()` vs bigint keys, generated columns (VIRTUAL default in 18), `timestamptz`, and integer minor units vs numeric.
- Ex 3.1: Insert two overlapping fee schedules for merchant 1, for example `[2026-01-01,2026-07-01)` and `[2026-06-01,2027-01-01)`. Expected: the second fails with a conflicting-key/exclusion error. Adjacent ranges succeed. Rewrite the table using `EXCLUDE USING gist` and get the same behaviour.
- Ex 3.2 (trap): Try to express "total refunds ≤ payment amount" as a CHECK. Expected: impossible (CHECK can't see other rows). Write a trigger, then note that it is racy without locking; this is revisited in L12.
- Ex 3.3: Insert a payment and inspect `payment_uid`. Use `uuid_extract_timestamp(payment_uid)` (verify the function name on the [UUID functions page](https://www.postgresql.org/docs/18/functions-uuid.html)) to show v7 ids are time-ordered. Compare index size and locality against a `uuidv4()` column in a scratch table.

**L4. Querying one table**
SELECT/WHERE/ORDER BY/LIMIT/FETCH FIRST, CASE, COALESCE/NULLIF, half-open time ranges, `DISTINCT` vs `DISTINCT ON`, ORDER BY with NULLS FIRST/LAST.
- Ex 4.1: Find the 20 largest succeeded payments in March 2026 with `created_at >= '2026-03-01' AND created_at < '2026-04-01'`. Expected: 20 rows, amounts descending.
- Ex 4.2 (trap): Run `SELECT * FROM payments LIMIT 5` twice (once after an `UPDATE` of some rows) and see that order isn't guaranteed. Add a deterministic `ORDER BY created_at, payment_id`.
- Ex 4.3: Latest payment per card using `DISTINCT ON (card_id) ... ORDER BY card_id, created_at DESC`. Expected: one row per card that has payments (≈ 200k).

**L5. Joins, semi-joins and anti-joins**
Inner, left, full, cross, self joins; join vs WHERE predicates on outer joins; EXISTS (semi) and NOT EXISTS (anti); the NOT IN + NULL trap.
- Ex 5.1: Customers with no payments in Q2 2026, written three ways: `NOT EXISTS`, `LEFT JOIN ... IS NULL`, `NOT IN`. Expected: the first two give identical counts. Then make the NOT IN subquery select a nullable column (`SELECT referred_by FROM customers`): 0 rows. Explain with 3VL.
- Ex 5.2 (trap): Moving `p.status = 'succeeded'` from `ON` to `WHERE` in a `LEFT JOIN` silently turns it into an inner join. Expected: the row count drops to the inner-join count.
- Ex 5.3: Self join to find customers referred by someone from a different country. Expected: columns (customer, referrer, both country codes), roughly tens of thousands of rows.

**L6. Aggregation, grouping and pivoting**
GROUP BY/HAVING, aggregate `FILTER`, GROUPING SETS/ROLLUP/CUBE with `GROUPING()`, pivot via `FILTER` (mention the `tablefunc` crosstab), and the row-multiplication trap. Sidebar: PG19 `GROUP BY ALL` (confirm at GA).
- Ex 6.1: Monthly gross volume by MCC with `ROLLUP (month, mcc)`. Expected: about 10 months × 6 MCCs detail rows, plus 10 month subtotals and 1 grand total. Use `GROUPING()` to label the subtotal rows.
- Ex 6.2: Pivot: per merchant, `count(*) FILTER (WHERE metadata->>'channel' = 'web')` and likewise for ios, android and pos, plus a failure rate. Expected: 5,000 rows × (merchant, web, ios, android, pos, failure_rate).
- Ex 6.3 (trap): Per customer, `SUM(payments) - SUM(refunds)` via `customers JOIN accounts JOIN cards JOIN payments LEFT JOIN refunds`. Payment sums come out inflated (wrong). Fix with pre-aggregated subqueries. Expected: the naive and correct totals differ for any customer with a refunded payment (and with two accounts). Show that `SUM(DISTINCT amount)` is also wrong.

**L7. Subqueries, CTEs and recursion**
Scalar, row and table subqueries; correlated vs uncorrelated; CTE inlining and `MATERIALIZED`; data-modifying CTEs; `WITH RECURSIVE` (UNION vs UNION ALL, `SEARCH`, `CYCLE`).
- Ex 7.1: Walk customer 101's referral downline with depth and path (`ARRAY[...] || id`). Expected: (customer_id, depth, path) rows; `GROUP BY depth` gives a histogram that thins out after a handful of levels.
- Ex 7.2: Top 10 referrers by total downline size (recursive from every root, carrying `root_id`). Expected: 10 rows, sizes heavily skewed toward low customer ids, because the generator only references earlier ids.
- Ex 7.3 (trap): `UPDATE customers SET referred_by = <a descendant> WHERE customer_id = 101` to create a cycle. The naive recursive query then never terminates (UNION ALL), so set `statement_timeout` first. Fix with `CYCLE customer_id SET is_cycle USING path`. Expected: it terminates, and exactly one row is flagged `is_cycle = true`.

**L8. Window functions**
`OVER (PARTITION BY ... ORDER BY ...)`; ROW_NUMBER/RANK/DENSE_RANK; LAG/LEAD; running totals; frames: ROWS vs RANGE vs GROUPS, EXCLUDE, the default-frame trap; named `WINDOW` clauses; filtering on window results (PostgreSQL needs a subquery; Oracle 26ai has QUALIFY).
- Ex 8.1: Daily running balance for account 42. First aggregate per day (`(created_at AT TIME ZONE 'UTC')::date`), then `sum(net) OVER (ORDER BY day ROWS UNBOUNDED PRECEDING)`. Add `avg(net) OVER (ORDER BY day RANGE BETWEEN interval '6 days' PRECEDING AND CURRENT ROW)` and the same with `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`. Expected: one row per active day; the last running balance equals `accounts.balance_minor`; RANGE and ROWS averages differ on days that follow gaps.
- Ex 8.2 (trap): Per-entry running sum with `ORDER BY created_at` only, on rows sharing a timestamp. Use a scratch table with deliberate ties: tied rows show the same running total. Fix with `ROWS` or a tiebreaker `entry_id`.
- Ex 8.3: Rank merchants within each MCC by monthly volume with RANK and DENSE_RANK. Expected: they differ only where there are ties; using ROW_NUMBER instead hides the ties arbitrarily.

**L9. Advanced query patterns**
LATERAL top-N per group; duplicate detection with LAG; gaps-and-islands; sessionization; keyset vs OFFSET pagination.
- Ex 9.1: Each merchant's top 3 payments:
  ```sql
  SELECT m.merchant_id, t.payment_id, t.amount_minor
  FROM merchants m
  CROSS JOIN LATERAL (SELECT payment_id, amount_minor FROM payments p
                      WHERE p.merchant_id = m.merchant_id AND p.status = 'succeeded'
                      ORDER BY amount_minor DESC LIMIT 3) t;
  ```
  Expected: ≤ 3 rows per merchant, ≈ 15,000 rows. Compare with a `ROW_NUMBER() ... WHERE rn <= 3` version: same rows, different plan. After L13, the index `payments (merchant_id, amount_minor DESC) WHERE status = 'succeeded'` makes the LATERAL version dramatically faster.
- Ex 9.2: Duplicate payments within 5 minutes:
  ```sql
  SELECT * FROM (
    SELECT payment_id, card_id, merchant_id, amount_minor, created_at, metadata,
           lag(created_at) OVER w AS prev_at, lag(payment_id) OVER w AS prev_id
    FROM payments WHERE status = 'succeeded'
    WINDOW w AS (PARTITION BY card_id, merchant_id, amount_minor ORDER BY created_at)) s
  WHERE created_at - prev_at <= interval '5 minutes';
  ```
  Expected: about 900 rows (the injected count). Grade precision and recall against `metadata ? 'injected_dup'`. Discuss why `PARTITION BY` must include the amount.
- Ex 9.3: Gaps-and-islands for consecutive failed logins, using the row_number difference
  `row_number() OVER (PARTITION BY customer_id ORDER BY occurred_at) - row_number() OVER (PARTITION BY customer_id, success ORDER BY occurred_at)`, then `GROUP BY customer_id, grp HAVING count(*) >= 5` on failures. Expected: about 200 streaks of 8+ failures from 203.0.113.7, plus a few organic streaks. Variant: a time-gap island (a new streak whenever the gap exceeds 10 minutes) using `LAG` plus a running `sum(flag)`.
- Ex 9.4 (optional): Paginate a merchant's payments with `OFFSET 100000` vs keyset `WHERE (created_at, payment_id) < (:last_ts, :last_id) ORDER BY created_at DESC, payment_id DESC LIMIT 50`. Expected after indexing: the buffers touched by OFFSET grow with page number, while keyset stays flat.

**L10. Writing data: upserts, MERGE, RETURNING, JSONB**
`INSERT ... ON CONFLICT DO NOTHING/DO UPDATE ... EXCLUDED`; idempotency keys; MERGE with `WHEN NOT MATCHED BY SOURCE`, `RETURNING merge_action()`; PG18 `RETURNING old.*/new.*`; jsonb operators (`->`, `->>`, `@>`, `?`), jsonpath, `JSON_TABLE` (PG17). PG19 sidebar: `ON CONFLICT DO SELECT ... RETURNING` (confirm at GA).
- Ex 10.1: Idempotent ingest: insert a payment with a fixed `payment_uid` twice using `ON CONFLICT (payment_uid) DO NOTHING RETURNING payment_id`. Expected: one row the first time, zero rows the second. Discuss the pre-19 workaround for returning the existing id: a CTE that falls back to a SELECT, or a no-op DO UPDATE, which writes a new row version.
- Ex 10.2: Nightly settlement with MERGE. Merge a staging table `settlement_batch(merchant_id, day, gross_minor)` into `merchant_daily_settlements` with matched → update, not matched → insert, `NOT MATCHED BY SOURCE AND t.day = :day` → delete, and `RETURNING merge_action(), old.gross_minor, new.gross_minor`. Expected: one output row per affected target row, labelled INSERT/UPDATE/DELETE, with old NULL for inserts and new NULL for deletes. Then add a duplicate source row and get the cardinality-violation error.
- Ex 10.3: JSONB. Count payments that fired the `velocity` rule with `metadata @> '{"risk":{"rules":["velocity"]}}'` (expected ≈ 5% of 2M ≈ 100k). Explode the rules with `JSON_TABLE(metadata, '$.risk.rules[*]' COLUMNS (rule text PATH '$'))` and group by rule. Expected: two rule names with counts ≈ 100k and ≈ 95k.

**L11. Transactions and isolation in PostgreSQL**
ACID; MVCC in one picture (row versions, snapshots, dead tuples, vacuum); Read Committed (per-statement snapshot, re-evaluation on concurrent update); Repeatable Read = snapshot isolation; Serializable = SSI; the anomaly names (lost update P4, read skew, write skew G2-item); SQLSTATE 40001 and retry loops. Mapping to Oracle and MySQL via Hermitage.
- Ex 11.1, lost update. Two psql sessions in READ COMMITTED both `SELECT balance_minor FROM accounts WHERE account_id = 900001` (5000), then each issues `UPDATE ... SET balance_minor = 4000`. Expected: the final value is 4000, so one $10 debit was lost. Repeat in REPEATABLE READ: the second UPDATE fails with `could not serialize access due to concurrent update`. Fix options: atomic `SET balance_minor = balance_minor - 1000`, `SELECT ... FOR UPDATE`, or an optimistic `version` column (JPA `@Version`).
- Ex 11.2, write skew. Both sessions run `BEGIN ISOLATION LEVEL REPEATABLE READ;`, then `SELECT sum(le.amount_minor) FROM ledger_entries le JOIN accounts a USING (account_id) WHERE a.customer_id = 900001;` (both see 10000). Session A withdraws 8000 from 900001 and session B withdraws 8000 from 900002 (use `SELECT nextval('journal_id_seq') AS jid \gset`, then insert both legs with `:jid`). Both COMMIT. Expected: both commits succeed and the combined balance is -6000. Repeat with `SERIALIZABLE`: one session fails (at INSERT or COMMIT) with SQLSTATE 40001 `could not serialize access due to read/write dependencies among transactions`. Retry it and the business rule now rejects the withdrawal.
- Ex 11.3, the Read Committed fix and its subtlety. In READ COMMITTED, first `SELECT 1 FROM customers WHERE customer_id = 900001 FOR UPDATE` (lock a common parent row, "materializing the conflict"), then read the sum in a *separate* statement. Expected: B blocks until A commits, then sees A's withdrawal and refuses. Author reasoning, to verify in the lab: the same lock-then-read in REPEATABLE READ does not fix the skew, because B's snapshot was taken when its first statement started, before it waited. That is a good discussion of why the snapshot timing matters.

**L12. Locking patterns: row locks, queues, deadlocks**
`FOR UPDATE / NO KEY UPDATE / SHARE / KEY SHARE`; `NOWAIT`; `SKIP LOCKED`; advisory locks; deadlock detection (40P01) and consistent lock ordering; lock timeouts (`lock_timeout`, `statement_timeout`); `pg_locks` / `pg_stat_activity`.
- Ex 12.1, job queue. Two sessions each run (after `\set worker w1` in one session and `\set worker w2` in the other):
  ```sql
  BEGIN;
  WITH next AS (SELECT job_id FROM jobs WHERE status = 'queued' AND run_after <= now()
                ORDER BY run_after LIMIT 5 FOR UPDATE SKIP LOCKED)
  UPDATE jobs j SET status = 'running', locked_by = :'worker', locked_at = now(), attempts = attempts + 1
  FROM next WHERE j.job_id = next.job_id RETURNING j.job_id;
  ```
  Expected: two disjoint sets of 5 ids and no blocking. Without SKIP LOCKED, session B blocks. With NOWAIT, B errors immediately. Use `\watch` to drain the queue. Discuss holding the transaction open during work vs commit-then-lease with a reaper for stale `locked_at`.
- Ex 12.2, deadlock. Session A updates account 1 then 2; session B updates 2 then 1. Expected: one session gets `deadlock detected` (40P01) after `deadlock_timeout` (default 1s). Fix by ordering the updates by account_id.
- Ex 12.3, refund race. Two concurrent full refunds of the same payment both pass a "refunds so far + this ≤ amount" check. Expected: both insert (over-refund). Fix with `SELECT ... FROM payments WHERE payment_id = ? FOR UPDATE` before the check, or with SERIALIZABLE.

**L13. Indexes and reading EXPLAIN**
B-tree internals at the level of "a sorted structure plus pointers"; multicolumn column order; PG18 skip scan; covering `INCLUDE` with index-only scans and the visibility map; partial; expression; GIN for jsonb/arrays (and pg_trgm for `LIKE '%x%'`); BRIN for physically-ordered data; reading `EXPLAIN (ANALYZE, BUFFERS)` (actual vs estimated rows, loops, buffers hit/read; BUFFERS is on by default in 18); index costs on writes; traps (function on column, implicit casts, leading wildcard, low selectivity, missing FK index).
- Ex 13.1: Make a slow query fast:
  ```sql
  SELECT payment_id, amount_minor, created_at FROM payments
  WHERE merchant_id = 4321 AND created_at >= '2026-09-01' AND created_at < '2026-10-01'
  ORDER BY created_at DESC LIMIT 20;
  ```
  Before: (Parallel) Seq Scan with a large "Rows Removed by Filter" and thousands of buffers. Add `CREATE INDEX ON payments (merchant_id, created_at)`. After: a backward Index Scan with buffers in the tens. Then try `(created_at, merchant_id)` and explain why it's worse.
- Ex 13.2, traps:
  - `WHERE created_at::date = '2026-05-01'` vs a half-open range;
  - `WHERE lower(email) = 'user42@example.com'`, which needs an expression index;
  - `WHERE payment_id = 42::numeric`: a seq scan despite the PK; compare the cast `42::bigint`;
  - `WHERE status = 'succeeded'` with an index on status: still a seq scan, which is correct at about 93% selectivity;
  - deleting a merchant: the slow FK check on unindexed `payments.merchant_id` and `accounts.merchant_id`.

  Expected: learners can name the plan node and the reason for each.
- Ex 13.3, specialised indexes:
  - Covering: `CREATE INDEX ON ledger_entries (account_id, created_at) INCLUDE (amount_minor)` gives an Index Only Scan with "Heap Fetches: 0" for the L8 running-balance query, after VACUUM.
  - GIN: `USING gin (metadata jsonb_path_ops)` serves the L10 `@>` query.
  - BRIN on `payments(created_at)` is tiny and effective, while BRIN on `ledger_entries(created_at)` is useless. Explain via `pg_stats.correlation`: the ledger was loaded grouped by type, not time.
  - PG18 skip scan: `CREATE INDEX ON payments (status, created_at)`, then a query on `created_at` alone shows an Index Scan whose EXPLAIN reports multiple index searches. Confirm the exact label in 18.6 output.

**L14. SQL from the JVM**
- JDBC basics: try-with-resources, PreparedStatement only (never string concat).
- Server-side prepares (`prepareThreshold=5`).
- Batching: `addBatch` + `reWriteBatchedInserts=true`, and COPY via `CopyManager` for bulk loads.
- Fetch size for large result sets.
- Transactions: `autoCommit=false`, and a retry loop on SQLSTATE 40001/40P01.
- HikariCP sizing: the formula, small pools, and `maximumPoolSize` = `minimumIdle` for fixed pools.
- N+1 from ORMs/DAOs, seen in `pg_stat_statements.calls`.
- jOOQ (typesafe SQL, codegen from a Flyway-migrated schema) vs Exposed (Kotlin DSL/DAO).
- Flyway migrations (versioned `V1__init.sql`; non-transactional migrations for `CREATE INDEX CONCURRENTLY`).
- Testcontainers for integration tests.
- Ex 14.1: Insert 100k payments four ways: row-by-row autocommit, batch, batch + `reWriteBatchedInserts=true`, and `COPY`. Expected ordering: COPY < rewritten batch < plain batch < row-by-row in wall time. The 2-3x figure for rewritten batch is pgJDBC's own claim. Measure on the learner's machine; don't promise numbers.
- Ex 14.2: N+1. Load 100 merchants and, per merchant, its latest payment through Exposed DAO or naive JDBC. Expected: `pg_stat_statements` shows about 101 calls. Rewrite as one LATERAL query (L9) or `WHERE merchant_id = ANY(?)` with a `java.sql.Array`: 1 call, same result.
- Ex 14.3: Pool sizing. Run a virtual-thread load generator (for example 500 concurrent requests running the L13.1 query) with Hikari `maximumPoolSize` = 4, 10, 50, 200 against the Docker VM. Expected: throughput plateaus or falls and p99 latency rises past roughly 2× cores, which matches the wiki's argument. Also wrap the L11.2 withdrawal in a Kotlin retry-on-40001 helper and show it converges.

**Compressing to 12 lessons:** merge L1+L2 (model + design), and merge L12 into L11 (keep the queue exercise, drop the deadlock one).

### Gaps
- Expected counts are derived from the generator's probabilities, not observed. After a real load, the writer should replace "≈" figures with actual numbers (setseed makes them reproducible if the load runs in one session in the same order).
- I didn't verify the exact PG18 EXPLAIN label for skip-scan index searches, or the `uuid_extract_timestamp` name against 18.6 output and docs.

---

## Teaching notes (misconceptions, analogies that work, what to cut)

### Takeaway
This audience learns fastest when SQL is mapped onto Kotlin collection pipelines and JVM concurrency concepts they already know. Then spend the saved time on the places where that mapping breaks: 3VL, bag semantics, snapshot timing, and planner behaviour. Cut theory that doesn't change how they write SQL at work.

### Cited Findings
- The Hermitage names (P4 lost update, G-single read skew, G2-item write skew) give learners precise vocabulary to compare PostgreSQL, Oracle and MySQL behaviour. — [Hermitage](https://github.com/ept/hermitage) [read]; background essay: [Kleppmann, "Hermitage: Testing the 'I' in ACID"](https://martin.kleppmann.com/2014/11/25/hermitage-testing-the-i-in-acid.html) [loads]; formal model map: [Jepsen consistency models](https://jepsen.io/consistency) [loads]
- PostgreSQL's own guidance that retries must restart "the whole transaction from the beginning" supports teaching the retry loop as transaction-scoped, not statement-scoped. — [Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html) [read]
- "You want a small pool, saturated with threads waiting for connections" is a quotable axiom for the JVM lesson. — [About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing) [read]

### Inferences
**Analogies that work for Java/Kotlin engineers**
- Query pipeline = Kotlin sequence: `FROM`/`JOIN` ≈ `flatMap`, `WHERE` ≈ `filter`, `GROUP BY` ≈ `groupBy { }`, aggregates ≈ `mapValues { it.value.sumOf { } }`, `HAVING` ≈ `filter` after groupBy, `SELECT` ≈ `map`, `ORDER BY`/`LIMIT` ≈ `sortedBy`/`take`. Then point out where it breaks: SQL is declarative, and the planner reorders all of it.
- `LEFT JOIN` ≈ `flatMap { children.ifEmpty { listOf(null) } }`.
- `LATERAL` ≈ calling a function per outer row inside `flatMap { m -> payments.filter { it.merchantId == m.id }.sortedByDescending { it.amount }.take(3) }`.
- Window functions ≈ `groupBy` that doesn't collapse rows; running totals ≈ `runningFold`/`scan` per partition.
- Recursive CTE ≈ a BFS worklist loop; `UNION` (not ALL) ≈ a visited set; `CYCLE` ≈ explicit cycle detection.
- NULL ≠ Kotlin `null`: Kotlin's `null == null` is true, while SQL's is unknown. `IS NOT DISTINCT FROM` is the SQL spelling of Kotlin `==`.
- B-tree ≈ a `TreeMap<Key, RowPointer>`. A composite index ≈ a TreeMap with a lexicographic `compareBy(a, b)` comparator: you can range-scan on `a`, or on `a` and `b`, but not on `b` alone. PG18 skip scan ≈ iterating each distinct `a` and seeking `b`. The phone-book analogy (last name, then first name) works too.
- MVCC snapshot ≈ reading an immutable persistent data structure. Repeatable Read ≈ grabbing the root reference at your first statement.
- SSI failure (40001) ≈ `OptimisticLockException` / a CAS failure: catch, back off, rerun the whole unit of work.
- `SELECT ... FOR UPDATE` ≈ `synchronized` on a row; SKIP LOCKED ≈ `tryLock()` and move on; NOWAIT ≈ `tryLock()` that throws.
- Connection pool ≈ a CPU-bound thread pool: more threads than cores means context switching, not throughput.
- EXPLAIN ≈ reading a stack trace inside-out: the most-indented node runs first, and actual rows × loops is the real work.

**Misconception sequencing**
Put each misconception in front of the learner as a "trap" exercise before explaining it: NOT IN (L5), row multiplication (L6), default frame (L8), write skew (L11), "the index is ignored" (L13), N+1 (L14). Seeing a wrong answer you wrote yourself sticks better than a warning box.

**Oracle bridges (one callout per lesson)**
- `''` IS NULL in Oracle.
- Oracle SERIALIZABLE is snapshot isolation.
- MERGE vs ON CONFLICT.
- `FETCH FIRST` / ROWNUM.
- Oracle DDL auto-commits (Flyway rollback behaviour differs).
- 26ai's QUALIFY, BOOLEAN and GROUP BY alias narrow the syntax gap.
- MySQL RR allows lost updates (relevant if any team uses MySQL).

**What to cut or keep brief**
- Cut: 4NF/5NF, formal relational algebra and calculus beyond one slide, hash/SP-GiST/GiST internals, rules, table inheritance, PL/pgSQL beyond one trigger, full-text search, PostGIS, logical replication, partitioning internals (one paragraph at most), vacuum internals (only "MVCC leaves dead rows; autovacuum cleans them; long transactions block cleanup"), SQL/PGQ (standard only; reverted from PG19), `FOR PORTION OF` (reverted from PG19).
- Keep short: CUBE (show once next to ROLLUP), crosstab (mention; FILTER pivots are enough), `money`/`char(n)` (only as "don't").
- Don't skip: 3VL, NOT EXISTS, pre-aggregation before joins, window frames, isolation labs in two terminals, EXPLAIN with BUFFERS, pool sizing, retry loops.

**Practical lab notes**
- Set `statement_timeout = '30s'` in `~/.psqlrc` so runaway recursive CTEs and cartesian products don't hang the laptop.
- Use `\set ON_ERROR_ROLLBACK interactive` in the two-session labs so a typo doesn't force a restart.
- Tell learners to `VACUUM (ANALYZE)` after bulk changes before reading plans; otherwise index-only scans show heap fetches and estimates are stale.
- PG14 hits EOL on 2026-11-12. If anyone's work DB or cloud instance is on 14, that's a real-world upgrade conversation worth one paragraph.

### Gaps
- The analogies are pedagogical judgement, not sourced findings. I found no study comparing analogy effectiveness for this audience.

---

## Verified URLs

[read] = fetched and content read this session. [loads] = HTTP 200 confirmed by curl on 2026-11-07, content not re-read. [WebFetch only] = curl got 403 (bot block) but WebFetch loaded and read it.

**PostgreSQL docs, release info and wiki**
- [read] https://www.postgresql.org/docs/18/release-18.html
- [read] https://www.postgresql.org/docs/17/release-17.html
- [read] https://www.postgresql.org/support/versioning/
- [read] https://www.postgresql.org/about/news/postgresql-19-beta-1-released-3313/
- [read] https://www.postgresql.org/about/news/postgresql-19-beta-4-released-3386/
- [read] https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/
- [read] https://www.postgresql.org/docs/18/transaction-iso.html
- [read] https://www.postgresql.org/docs/18/runtime-config-resource.html
- [read] https://www.postgresql.org/docs/18/sql-select.html
- [read] https://www.postgresql.org/docs/18/sql-merge.html
- [read] https://www.postgresql.org/docs/18/sql-createtable.html
- [read] https://wiki.postgresql.org/wiki/Don%27t_Do_This
- [loads] https://www.postgresql.org/docs/18/queries-with.html
- [loads] https://www.postgresql.org/docs/18/tutorial-window.html
- [loads] https://www.postgresql.org/docs/18/sql-expressions.html
- [loads] https://www.postgresql.org/docs/18/functions-window.html
- [loads] https://www.postgresql.org/docs/18/queries-table-expressions.html
- [loads] https://www.postgresql.org/docs/18/functions-subquery.html
- [loads] https://www.postgresql.org/docs/18/functions-aggregate.html
- [loads] https://www.postgresql.org/docs/18/queries-limit.html
- [loads] https://www.postgresql.org/docs/18/sql-insert.html
- [loads] https://www.postgresql.org/docs/18/datatype-json.html
- [loads] https://www.postgresql.org/docs/18/functions-json.html
- [loads] https://www.postgresql.org/docs/18/ddl-constraints.html
- [loads] https://www.postgresql.org/docs/18/ddl-generated-columns.html
- [loads] https://www.postgresql.org/docs/18/btree-gist.html
- [loads] https://www.postgresql.org/docs/18/functions-uuid.html
- [loads] https://www.postgresql.org/docs/18/functions-srf.html
- [loads] https://www.postgresql.org/docs/18/indexes-multicolumn.html
- [loads] https://www.postgresql.org/docs/18/indexes-index-only-scans.html
- [loads] https://www.postgresql.org/docs/18/indexes-partial.html
- [loads] https://www.postgresql.org/docs/18/indexes-expressional.html
- [loads] https://www.postgresql.org/docs/18/sql-createindex.html
- [loads] https://www.postgresql.org/docs/18/gin.html
- [loads] https://www.postgresql.org/docs/18/brin.html
- [loads] https://www.postgresql.org/docs/18/btree.html
- [loads] https://www.postgresql.org/docs/18/using-explain.html
- [loads] https://www.postgresql.org/docs/18/explicit-locking.html
- [loads] https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html
- [loads] https://www.postgresql.org/docs/18/pgstatstatements.html
- [loads] https://www.postgresql.org/docs/18/app-psql.html
- Not verified (timed out twice): https://www.postgresql.org/docs/18/functions-comparison.html, https://www.postgresql.org/docs/18/datatype-numeric.html
- Not fetched (exists only after PG19 GA): https://www.postgresql.org/docs/19/release-19.html

**Indexing, SQL standard, isolation theory**
- [loads] https://use-the-index-luke.com/
- [loads] https://use-the-index-luke.com/no-offset
- [loads] https://use-the-index-luke.com/sql/where-clause/the-equals-operator/concatenated-keys
- [loads] https://modern-sql.com/
- [loads] https://modern-sql.com/standard/2023
- [loads] https://modern-sql.com/caniuse/merge
- [read] https://en.wikipedia.org/wiki/SQL:2023
- [read] https://github.com/ept/hermitage
- [loads] https://martin.kleppmann.com/2014/11/25/hermitage-testing-the-i-in-acid.html
- [loads] https://jepsen.io/consistency
- Broken: https://modern-sql.com/blog/2023-06/news-sql-2023 returned HTTP 404.

**JVM**
- [read] https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
- [loads] https://github.com/brettwooldridge/HikariCP
- [read] https://jdbc.postgresql.org/documentation/use/
- [loads] https://jdbc.postgresql.org/changelogs/
- [loads] https://documentation.red-gate.com/flyway
- [loads] https://www.jooq.org/doc/latest/manual/
- [loads] https://www.jooq.org/download/
- [loads] https://www.jetbrains.com/help/exposed/home.html
- [loads] https://github.com/JetBrains/Exposed
- [read] https://repo1.maven.org/maven2/org/postgresql/postgresql/maven-metadata.xml. The same metadata path pattern was read for `com/zaxxer/HikariCP`, `org/flywaydb/flyway-core`, `org/flywaydb/flyway-database-postgresql`, `org/jooq/jooq` and `org/jetbrains/exposed/exposed-core`.

**Lab and datasets**
- [read] https://hub.docker.com/_/postgres (also queried the Docker Hub tags API)
- [WebFetch only] https://postgrespro.com/community/demodb
- [loads] https://github.com/devrimgunduz/pagila
- [loads] https://github.com/lerocha/chinook-database

**Oracle and MySQL**
- [read] https://docs.oracle.com/en/database/oracle/oracle-database/23/nfcoa/appdev_sql.html (serves the Oracle AI Database 26ai docs)
- [loads] https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Nulls.html
- Not verified (curl got 403): https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html. MySQL facts in these notes rely on Hermitage instead.
