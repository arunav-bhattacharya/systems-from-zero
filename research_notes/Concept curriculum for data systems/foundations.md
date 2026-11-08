# Foundations of data-intensive systems: workloads, latency, reliability, scalability, maintainability and cloud-native architecture

Snapshot date: 2026-11-07. DDIA 2nd edition (Kleppmann and Riccomini) was first released 2026-02-18 ([DDIA 2e copyright page][ddia]). DDIA citations below give the printed page with the PDF page in brackets (PDF page = printed page + 24). `[ddia]` is the local PDF. DDIA is one source among many here. The product-organized round of research ([earlier report][prev]) already pinned versions for PostgreSQL 18.6, Kafka 4.4.0, Redis 8.10.3, Spark 4.x, Iceberg 1.12, DuckDB 2.0, JDK 25/27, Kotlin 2.4.21, Gradle 9.9.0 and Testcontainers 2.0.5. Those pins are not repeated here; this file covers concept framing.

Each concept below follows the same template: **Problem**, **Simplest version**, **Where it breaks** (with numbers), **Improvement**, **Misconceptions**.

## 1. What a data system is: OLTP vs analytical workloads, systems of record vs derived data, warehouses, lakes and lakehouses

### Takeaway
Two splits frame every later lesson. The first is operational (OLTP: point reads and writes of current state, gigabytes to terabytes) versus analytical (OLAP: scans and aggregates over history, terabytes to petabytes). The second is the system of record versus everything derived from it (caches, indexes, materialized views, warehouses, ML models). Warehouses, lakes and lakehouses are successive answers to one question: where should the analytical copy live, and in what format? DDIA 2e chapters 1 and 2 never use the word "lakehouse", so the course has to add that layer itself.

### Cited Findings

**DDIA's framing (chapter 1, "Trade-Offs in Data Systems Architecture")**
- DDIA calls an application *data-intensive* when data management is one of its main challenges: storing large volumes, managing change, staying consistent under failure and concurrency, and staying available. A *compute-intensive* system's main challenge is parallelizing a large computation. — [DDIA 2e p.1 (PDF 25)][ddia]
- Applications are assembled from standard building blocks: databases, caches, search indexes, stream processing and batch processing. — [DDIA 2e p.2 (PDF 26)][ddia]
- Operational systems are where data is created, and application code both reads and modifies them. Analytical systems hold a read-only copy that is optimized for analysts and data scientists. Data engineers and analytics engineers emerged as roles at the boundary between the two. — [DDIA 2e p.4 (PDF 28)][ddia]
- Table 1-1 contrasts the two along several dimensions:

  | | OLTP | OLAP |
  |---|---|---|
  | Reads | point queries by key | aggregates over many records |
  | Writes | create, update and delete individual records | bulk ETL or event streams |
  | Queries | fixed, built into the application | ad hoc |
  | Volume | many small queries | few complex ones |
  | Data represents | latest state | history of events |
  | Dataset size | GB–TB | TB–PB |

  The book notes that the meaning of "online" in OLAP is unclear, and probably just means interactive. — [DDIA 2e p.5–6 (PDF 29–30)][ddia]
- Product or real-time analytics (Pinot, Druid, ClickHouse) is a third category. These systems run analytical aggregations embedded in user-facing products, ingesting in real time and answering with low latency, while traditional OLAP ingests in batches and optimizes for throughput. — [DDIA 2e p.6 (PDF 30)][ddia]
- Data warehouses arose in the late 1980s and early 1990s, for four reasons: data was siloed across dozens to hundreds of OLTP systems, OLTP schemas suit analytics poorly, analytical queries hurt OLTP performance, and OLTP systems often sit on restricted networks. Data reaches the warehouse by ETL, or by ELT when the transform runs inside the warehouse. SaaS sources go through connectors such as Fivetran, Singer and Airbyte. — [DDIA 2e p.7–8 (PDF 31–32)][ddia]
- HTAP systems often combine an OLTP engine with a separate analytical engine behind one interface. DDIA argues HTAP does not replace the warehouse, because an enterprise has many operational databases but usually one warehouse. Fraud detection is its example of a genuine HTAP workload. — [DDIA 2e p.8–9 (PDF 32–33)][ddia]
- A data lake holds files in any format with no imposed schema, usually on cheap object storage. It often becomes a stop on the way to the warehouse, under the "sushi principle" that raw data is better. Beyond the lake, DDIA covers DataOps, governance under GDPR and CCPA, streams as an analytics input, and reverse ETL that pushes analytical outputs (such as ML models) back into operational systems. — [DDIA 2e p.9–10 (PDF 33–34)][ddia]
- A system of record (the source of truth) represents each fact exactly once, usually normalized, and wins any disagreement. Derived data (caches, denormalized values, indexes, materialized views, trained models) is redundant by design and can be recomputed from the source. Whether a database is one or the other depends on how it is used, not on the tool. — [DDIA 2e p.10–11 (PDF 34–35)][ddia]
- DDIA cites Stonebraker and Çetintemel's ICDE 2005 paper "One Size Fits All: An Idea Whose Time Has Come and Gone" for the trend toward specialized systems as scale grows. — [DDIA 2e p.9 and ref. 11 (PDF 33, 49+)][ddia]
- Checked for this file: the extracted text of chapters 1 and 2 contains no occurrence of "lakehouse". — [DDIA 2e chs. 1–2][ddia]

**Lakehouse (the layer DDIA's early chapters omit)**
- The Lakehouse paper (Armbrust, Ghodsi, Xin and Zaharia, CIDR 2021) tells the history as warehouses, then Hadoop/HDFS data lakes with schema-on-read, then cloud object stores replacing HDFS "from 2015 onwards". It defines a lakehouse by three properties: open direct-access formats (Parquet/ORC), first-class support for ML and data science, and state-of-the-art performance. It argues that the two-tier lake-plus-warehouse design suffers from reliability and staleness problems. — [Lakehouse, CIDR 2021](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- As of November 2026, Iceberg spec v1, v2 and v3 are complete, and v4 is in development. v3 adds deletion vectors, `variant`, geo types, row lineage and default values. An Iceberg commit is an optimistic swap of the metadata pointer. — [Iceberg spec](https://iceberg.apache.org/spec/); summarized in the [earlier report][prev]

**Concept card: operational vs analytical**
- **Problem:** the same business data serves two incompatible access patterns. — [DDIA 2e p.5–6][ddia]
- **Simplest version:** run reports directly on the production OLTP database (this was the original practice). — [DDIA 2e p.7 (PDF 31)][ddia]
- **Where it breaks:** expensive scans degrade OLTP response times for other users, data is spread across hundreds of databases, and schemas suited to transactions are poor for analysis. — [DDIA 2e p.7 (PDF 31)][ddia]
- **Improvement:** a separate warehouse fed by ETL, then a lake for raw and unstructured data, then a lakehouse with transactional open table formats on object storage. — [DDIA 2e p.7–10][ddia]; [Lakehouse paper](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- **Misconceptions:**
  - "HTAP makes the warehouse obsolete." DDIA says it does not. — [DDIA 2e p.9][ddia]
  - "A data lake is just a folder of files." The Lakehouse paper and the Iceberg spec define metadata, snapshots and atomic commits on top of the files. — [Lakehouse paper](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf); [Iceberg spec](https://iceberg.apache.org/spec/)
  - "PostgreSQL is a system of record." Systems of record are defined by usage, not by product. — [DDIA 2e p.11][ddia]
  - "Derived data is wasteful duplication." It exists to make reads fast. — [DDIA 2e p.11][ddia]

### Inferences
- Lesson spine: one source of truth and many derived views. The home-timeline cache in section 4 is a derived materialized view, which ties the workload lesson to the scalability lesson. The warehouse, the search index and the Redis cache are the same idea at different latencies.
- A good first-principles definition for beginners: an **operational** system answers "what is true now for this one key?" and an **analytical** system answers "what happened across all keys over time?". Every storage-layout choice later in the course (B-trees versus columnar storage) follows from that difference.
- Teach the lakehouse as warehouse semantics (ACID tables, schema, time travel) on lake storage (object store plus open files). A single copy of the data can then serve several engines.

### Gaps
- No 2025–2026 survey with measured OLTP and OLAP dataset sizes was found. Table 1-1's ranges are DDIA's qualitative ones.
- The 2026 state of HTAP products (SingleStore, TiDB, AlloyDB's columnar engine and others) was not checked this round.

## 2. Describing performance: response time, latency, queueing, percentiles, coordinated omission, tail amplification, hedging, SLOs

### Takeaway
Response time is a distribution, not a number, and queueing dominates it as utilization rises. Report percentiles, and aggregate them by merging histograms, never by averaging quantiles. Measure from the client at an open (fixed) arrival rate, or coordinated omission hides the stalls. With fan-out, a rare per-server tail becomes the common case for users: at a 1% slow rate per server and a fan-out of 100, 63% of requests are slow. Hedged and tied requests buy most of that tail back for a few percent of extra load. SLOs and error budgets turn all of this into an engineering contract.

### Cited Findings

**Concept card: response time vs service time vs latency vs queueing delay**
- DDIA's definitions:
  - *Response time* is what the client sees, including every delay.
  - *Service time* is the time the service spends actively processing.
  - *Queueing delay* can occur at several points.
  - *Latency* is a catch-all for time a request is not being processed (it is latent). Network latency is time spent in transit.
  — [DDIA 2e p.38–39 (PDF 62–63)][ddia]
- Queueing delay causes much of the variability. A few slow requests hold up fast ones behind them (head-of-line blocking). Queueing delay is not part of service time, so response time has to be measured on the client. — [DDIA 2e p.39 (PDF 63)][ddia]
- Random added delays include context switches, packet loss and TCP retransmission, GC pauses, page faults and even mechanical vibration in the rack. — [DDIA 2e p.39 (PDF 63)][ddia]
- Dean and Barroso list these sources of variability: daemons that cause millisecond hiccups when scheduled, global resource sharing (network switches, shared file systems), maintenance activities (BigTable compactions, GC), layered queueing, CPU power limits and thermal throttling, SSD garbage collection (which can raise read latency 100x under modest write load) and power-saving modes. — [Dean and Barroso, "The Tail at Scale", CACM 56(2), Feb 2013](https://www.barroso.org/publications/TheTailAtScale.pdf)
- **Misconception:** "latency" and "response time" are interchangeable. DDIA deliberately separates them. — [DDIA 2e p.38][ddia]

**Concept card: throughput vs response time, and the utilization curve**
- **Problem:** how much load can a server take before users notice?
- **Simplest version:** assume response time stays flat until 100% CPU.
- **Where it breaks:** response time rises sharply as throughput approaches capacity, because requests wait behind earlier ones (DDIA Figure 2-3). — [DDIA 2e p.37 (PDF 61)][ddia]
- In an M/M/1 queue with utilization ρ = λ/μ, the mean number of jobs in the system is ρ/(1−ρ). That is 1 at ρ = 0.5 and 99 at ρ = 0.99. Brooker argues that high-percentile latency is a poor measure of efficiency, because queueing dominates it and it rises with load, but a good leading indicator of overload. He recommends mean latency if latency must measure efficiency. — [Brooker, "Latency sneaks up on you", Aug 2021](https://brooker.co.za/blog/2021/08/05/utilization.html)
- Little's law: the average number in a system L equals arrival rate λ times average time in system W, for any stable system regardless of distribution. — [Little's law (Wikipedia)](https://en.wikipedia.org/wiki/Little%27s_law)
- DDIA notes the mean is useful for estimating throughput limits, citing Brooker's "Is the Mean Really Useless?". — [DDIA 2e p.40 and ref. 19 (PDF 64)][ddia]
- **Metastable failure / retry storm:** near overload, timeouts trigger client retries, which add load. The system can stay overloaded after the trigger has gone, until it is reset. DDIA lists the mitigations: exponential backoff with randomization, circuit breakers, token buckets, load shedding, backpressure, and the choice of queueing and load-balancing algorithm. — [DDIA 2e p.38 (PDF 62)][ddia]
- **Misconception:** running at 90% utilization is pure efficiency. From the M/M/1 formula, 90% means 9 jobs in the system on average, against 1 at 50% (see Inferences).

**Concept card: mean, median, percentiles**
- **Simplest version:** report the average. **Where it breaks:** the mean does not say how many users actually waited that long. — [DDIA 2e p.40 (PDF 64)][ddia]
- The median (p50) is the typical wait. p95, p99 and p999 describe the tail. Amazon sets internal service targets at p99.9 because the slowest requests often belong to the customers with the most data, who are the most valuable. Amazon judged optimizing p99.99 not worth the cost. — [DDIA 2e p.40–41 (PDF 64–65)][ddia], citing the [Dynamo paper, SOSP 2007](https://dl.acm.org/doi/10.1145/1294261.1294281)
- Google SRE's example: median latency around 50 ms while 5% of requests are about 20 times slower. Alerting on the average would miss changes in that tail. Latency distributions are skewed, so mean and median can differ a lot. — [Google SRE book ch. 4, "Service Level Objectives"](https://sre.google/sre-book/service-level-objectives/)
- DDIA warns that latency-to-revenue statistics are unreliable:
  - Google 2006 reported a 20% traffic drop for 400→900 ms.
  - Google 2009 reported only 0.6% fewer searches for +400 ms.
  - Bing found 2 s of extra load time cut ad revenue 4.3%.
  - Akamai's "100 ms = up to 7% conversion" is confounded, because the fastest pages are often 404s.
  - Yahoo, controlling for result quality, found 20–30% more clicks when fast and slow differ by 1.25 s or more.
  — [DDIA 2e p.41 (PDF 65)][ddia]
- **Misconception:** "p99 affects only 1% of users." A user whose page triggers many backend calls hits the tail far more often (see the fan-out card).

**Concept card: computing and aggregating percentiles**
- **Simplest version:** keep every response time in a rolling window (for example, 10 minutes) and sort it every minute. — [DDIA 2e p.42 (PDF 66)][ddia]
- **Where it breaks:** memory and CPU cost at high request rates. Averaging percentiles, whether across time buckets or machines, is mathematically meaningless. The right way to aggregate is to add histograms. — [DDIA 2e p.42 (PDF 66)][ddia]
- **HdrHistogram** (Gil Tene):
  - Range and precision are configurable, with precision set in significant digits. Three digits tracking 1 µs to 1 hour keeps quantization error within 0.1%.
  - A histogram with a highest trackable value of 3,600,000,000 at 3 significant digits uses a fixed footprint of about 185 KB.
  - Recording takes constant time.
  - Histograms are additive, so per-thread histograms can be merged.
  - `Recorder` and `SingleWriterRecorder` support interval sampling while recording continues.
  — [HdrHistogram README](https://github.com/HdrHistogram/HdrHistogram)
- **DDSketch** (Masson, Rim and Lee, PVLDB 12(12), 2019): rank-error sketches (the GK family, t-digest-style) do not prevent arbitrarily large *relative* errors on heavily skewed data, which latency data usually is. DDSketch claims to be the first fully mergeable, relative-error quantile sketch with formal guarantees. It is in wide use at Datadog. — [DDSketch, arXiv:1908.10693](https://arxiv.org/abs/1908.10693)
- **t-digest:** Dunning, "The t-digest: Efficient Estimates of Distributions", *Software Impacts* 7, 2021. — [DDIA 2e ref. 32 (PDF 82+)][ddia]
- **Prometheus:**
  - Summaries compute quantiles in the client and are not aggregatable. The docs say averaging summary quantiles yields statistically nonsensical values.
  - Classic histograms aggregate (`histogram_quantile(0.95, sum by (le) (rate(...)))`), but error is bounded by bucket width. In the docs' example, the true p95 is near 220 ms and interpolation estimates 295 ms. After a 100 ms shift, the estimate is 443 ms against a true value near 320 ms.
  - The docs recommend native histograms over both classic histograms and summaries.
  — [Prometheus, "Histograms and summaries"](https://prometheus.io/docs/practices/histograms/)
- Status as of November 2026 (secondary sources; check against the changelog):
  - Native histograms became stable in Prometheus v3.8.0, released 2 December 2025 per GitHub; the CHANGELOG header says 28 November.
  - v3.13 (1 July 2026) is the LTS release, supported to 2027-07-31.
  - Native histograms remain opt-in through `scrape_native_histograms`, and need the protobuf exposition format.
  — [youngju.dev, 2026-07-16](https://www.youngju.dev/blog/2026-07-16-prometheus-native-histograms-stable-lts); [logz.io](https://logz.io/blog/prometheus-metrics-native-histograms)
- Library versions on Maven Central, checked 2026-11-07:
  - `org.hdrhistogram:HdrHistogram` 2.2.2 (May 2024)
  - `com.datadoghq:sketches-java` 0.8.3 (May 2024)
  - `com.tdunning:t-digest` 3.3 (May 2021)
  - `io.micrometer:micrometer-core`: the latest artifact is 1.18.0-RC2 (Nov 2026), a release candidate
  — [HdrHistogram metadata](https://repo1.maven.org/maven2/org/hdrhistogram/HdrHistogram/maven-metadata.xml); [sketches-java metadata](https://repo1.maven.org/maven2/com/datadoghq/sketches-java/maven-metadata.xml); [t-digest metadata](https://repo1.maven.org/maven2/com/tdunning/t-digest/maven-metadata.xml); [micrometer-core metadata](https://repo1.maven.org/maven2/io/micrometer/micrometer-core/maven-metadata.xml)
- **Misconceptions:**
  - "Average the p99 of each pod to get the service p99." This is wrong; merge histograms instead. — [DDIA 2e p.42][ddia]; [Prometheus docs](https://prometheus.io/docs/practices/histograms/)
  - "A Prometheus classic histogram p99 is exact." Its error is bounded only by bucket width. — [Prometheus docs](https://prometheus.io/docs/practices/histograms/)

**Concept card: coordinated omission (CO)**
- **Problem:** load generators that wait for each response before sending the next request stop sending while the server stalls. The stall then appears in only a handful of samples, which hides it. The wrk2 README names this Coordinated Omission. — [wrk2 README](https://github.com/giltene/wrk2)
- **Simplest version (closed model):** N threads loop over send, wait and record, timing from the actual send. k6 calls this the closed model: the next iteration does not start until the previous one finishes, so the arrival rate drops when the system slows. k6 notes that the testing literature calls this coordinated omission. — [k6 docs, open vs closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)
- **Where it breaks (numbers):** wrk2 runs `-t2 -c100 -d30s -R2000`.
  - Quiet run, corrected vs uncorrected: p50 6.21 vs 2.68 ms, p99 10.52 vs 5.43 ms.
  - One 1.4 s server pause (induced with ^Z): corrected p99 is 1.27 s, uncorrected 6.04 ms, about 200x. Corrected p90 is 11.77 ms vs 4.87 ms.
  — [wrk2 README](https://github.com/giltene/wrk2)
- In k6's example, against an endpoint with a 6 s delay over 1 minute, the closed model (1 VU) completes about 10 iterations. The open `constant-arrival-rate` model at 1/s completes 60, using up to 11 VUs. — [k6 docs](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)
- **Improvement:**
  - Use an open model at a constant arrival rate, and time each request from when it *should* have been sent (wrk2 `-R`; k6 `constant-arrival-rate` and `ramping-arrival-rate`). — [wrk2 README](https://github.com/giltene/wrk2); [k6 docs](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)
  - Or correct after the fact with HdrHistogram's `recordValueWithExpectedInterval()`, which back-fills synthetic samples when a measurement exceeds the expected interval. — [HdrHistogram README](https://github.com/HdrHistogram/HdrHistogram)
  - wrk2 warns that runs under 10–20 s give unreliable results, and that its latencies are only accurate to about ±1 ms because of OS sleep behaviour. — [wrk2 README](https://github.com/giltene/wrk2)
- DDIA 2e's performance section (pp. 37–42) tells readers to measure on the client but does not name coordinated omission (checked for this file). The course should add it. — [DDIA 2e p.37–42][ddia]
- **Misconception:** "My JMH or JUnit loop with 50 threads measures user latency." It measures a closed system's service time.

**Concept card: tail-latency amplification under fan-out (Dean and Barroso 2013)**
- **Problem:** to answer fast over a big dataset, a root fans out to many leaves and must wait for all of them. — [The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf)
- **Simplest version:** fan out and wait for every leaf.
- **Where it breaks (numbers):**
  - Each server responds in 10 ms typically, with a p99 of 1 s. A request that touches one server is slow 1 time in 100. Touching 100 servers in parallel makes 63% of user requests take over 1 s.
  - Even at 1 in 10,000 slow per server, a 2,000-server fan-out makes almost 1 in 5 user requests (0.18) exceed 1 s.
  - In a real Google service, measured at the root: one random leaf finishes at p50/p95/p99 = 1/5/10 ms; 95% of leaves at 12/32/70 ms; all leaves at 40/87/140 ms. Waiting for the slowest 5% accounts for half of the p99.
  — [The Tail at Scale, Table 1 and figure](https://www.barroso.org/publications/TheTailAtScale.pdf)
- DDIA names this tail latency amplification and illustrates it with its Figure 2-6. — [DDIA 2e p.41–42 (PDF 65–66)][ddia]
- **Improvements (within a request):**
  - **Hedged requests:** send to one replica, and send a second after a short delay. Deferring the hedge until the p95 expected latency caps extra load at about 5%. In a Google benchmark reading 1,000 keys from BigTable across 100 servers, hedging after 10 ms cut p99.9 from 1,800 ms to 74 ms while sending only 2% more requests. Hedges can be tagged low-priority.
  - **Tied requests:** enqueue on two servers, each told about the other, and cancel the twin when one starts. The client waits about 2x the average network delay (1 ms or less) before sending the second.
    - BigTable reads with a tied request after 1 ms, mostly idle cluster: p50 19→16 ms (−16%), p90 38→29 (−24%), p99 67→42 (−37%), p99.9 98→61 (−38%).
    - With a concurrent terasort: p50 24→19 (−21%), p99 108→67 (−38%), p99.9 159→108 (−32%).
    - Disk overhead stayed under 1%, and tied requests let the batch and interactive workloads share one cluster.
  - Probing queues and picking the least loaded server is less effective, because load changes between probe and send and clients herd onto the same server.
  — [The Tail at Scale, Table 2](https://www.barroso.org/publications/TheTailAtScale.pdf)
- **Improvements (across requests):**
  - **Micro-partitions:** about 20 per machine, so load moves in roughly 5% increments.
  - **Selective replication** of hot micro-partitions.
  - **Latency-induced probation:** pull slow machines out, keep sending them shadow requests, and readmit them on recovery. Removing capacity under load can improve latency.
  - **Good-enough results:** the chance that a particular leaf holds the best result is under 1 in 1,000.
  - **Canary requests:** send to one or two leaves first, so a request that crashes servers cannot take down thousands at once.
  — [The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf)
- **Caveat:** these techniques work only when the cause of slowness does not hit several replicas at once. — [The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf)
- **Current product support:** gRPC has a per-method `hedgingPolicy` in its service config. `maxAttempts` is required and capped at 5; `hedgingDelay` is optional (if omitted, all attempts go at once); `nonFatalStatusCodes` is defined in the A6 proposal. Deadlines cover the whole hedged chain, `retryThrottling` limits overload, and hedging is unsuitable for non-idempotent methods. — [gRPC request hedging guide](https://grpc.io/docs/guides/request-hedging); [gRFC A6](https://github.com/jdcormie/proposal/blob/master/A6-client-retries.md)
- **Misconceptions:**
  - "Hedging doubles load." At a p95 delay it adds about 5%, and 2% in the BigTable test.
  - "Retries and hedges are the same." Retries fire after failure; hedges fire on slowness and cancel the loser.
  - "Hedging is safe for any call." It is only safe for idempotent calls. — [The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf); [gRPC guide](https://grpc.io/docs/guides/request-hedging)

**Concept card: SLIs, SLOs, SLAs and error budgets (Google SRE)**
- **Definitions:** an SLI is a precisely defined measurement (latency, error rate, throughput, availability). An SLO is a target value or range for an SLI. An SLA is a contract that attaches consequences to missing the SLO; without consequences, it is really an SLO. 99.95% is "three and a half nines". — [SRE book ch. 4](https://sre.google/sre-book/service-level-objectives/)
- **Example SLOs:**
  - 99% of Get calls under 100 ms.
  - Several thresholds to describe the curve's shape: 90% under 1 ms, 99% under 10 ms, 99.9% under 100 ms.
  - Separate targets per workload class (bulk vs interactive).
  - Standard SLI templates fix the aggregation interval, the requests included and the measurement point (for example, time to last byte).
  - A rate example: 200 req/s on even seconds and 0 on odd seconds averages the same as a steady 100 req/s.
  — [SRE book ch. 4](https://sre.google/sre-book/service-level-objectives/)
- **Practices:** start from what users need; don't set targets from current performance; keep SLOs few; avoid absolutes; start loose and tighten; keep internal targets stricter than public ones; don't overachieve. Google's Chubby lock service ran a planned outage in any quarter where it had not fallen below its SLO, to flush out services that wrongly assumed it never fails. — [SRE book ch. 4](https://sre.google/sre-book/service-level-objectives/)
- **Burn rate** is how fast the service consumes error budget relative to the SLO; a burn rate of 1 uses exactly the whole budget by the end of the window. For a 99.9% SLO over 30 days, the recommended alerts are:

  | Action | Long window | Short window | Burn rate | Budget consumed |
  |---|---|---|---|---|
  | Page | 1 h | 5 min | 14.4 | 2% |
  | Page | 6 h | 30 min | 6 | 5% |
  | Ticket | 3 days | 6 h | 1 | 10% |

  Other numbers from the same chapter:
  - A total outage (burn rate 1,000) exhausts the budget in about 43 minutes. At 99.999% a total outage takes 26 seconds.
  - A 0.1% error rate for 10 minutes uses only about 0.02% of the monthly budget.
  - In a service with 10 requests per hour, one failure is a 1,000x burn and uses 13.9% of the budget.
  - Alerting on the instantaneous error rate can page up to 144 times a day while the service still meets its SLO.
  — [SRE Workbook, "Alerting on SLOs"](https://sre.google/workbook/alerting-on-slos/)
- DDIA's SLO example: median under 200 ms, p99 under 1 s, and at least 99.9% of valid requests non-error. DDIA notes that defining good availability metrics is hard, citing Mogul and Wilkes, "Nines Are Not Enough" (HotOS 2019) and Hidalgo's *Implementing Service Level Objectives* (2020). — [DDIA 2e p.42 and refs 28–29 (PDF 66)][ddia]
- **Misconceptions:**
  - "Higher availability than promised is free goodwill." Users come to depend on it (the Chubby case).
  - "Page on any error spike." That gives poor precision.
  — [SRE book ch. 4](https://sre.google/sre-book/service-level-objectives/); [SRE Workbook](https://sre.google/workbook/alerting-on-slos/)

### Inferences
- **M/M/1 response times.** Little's law (W = L/λ) applied to Brooker's E[N] gives mean response time W = S/(1−ρ), where S is mean service time. For S = 10 ms: ρ = 0.5 → 20 ms; 0.8 → 50 ms; 0.9 → 100 ms; 0.95 → 200 ms; 0.99 → 1 s. This table is the core numeric intuition for the utilization lesson (computed, not taken from a source).
- **Little's law as a sizing tool** (computed): at 2,000 req/s and a 50 ms mean response time, about 100 requests are in flight. That number sizes a thread pool, connection pool or virtual-thread budget. It also sanity-checks dashboards: if measured concurrency, rate and latency disagree, a metric is wrong.
- **Fan-out math** (computed): P(at least one slow) = 1 − (1−p)^N reproduces the paper's 0.634 (p = 0.01, N = 100) and 0.181 (p = 0.0001, N = 2,000). To keep only 1% of user requests slow at N = 100, each leaf must be slow no more than about 0.01% of the time. The leaf SLO has to sit at p99.99 for the user-facing p99.
- **Error-budget minutes per 30 days** (computed): 99% = 432 min; 99.9% = 43.2 min; 99.95% = 21.6 min; 99.99% = 4.32 min; 99.999% ≈ 26 s. The last matches the Workbook's 26 s.
- **Coordinated-omission sample counts** (computed): in a closed test with 100 connections, a 1.4 s stall corrupts only about 100 samples. In a 30 s, 2,000 req/s open test, about 2,800 requests (1.4 × 2,000), roughly 4.7% of 60,000, should have been sent during the stall. That is why the corrected p99, not just the max, moves to the stall length, matching wrk2's 1.27 s.
- **Teaching order:** response time vs service time → queueing curve and Little's law → percentiles → aggregation → coordinated omission → fan-out → hedging → SLOs. Each step fixes a measurement error introduced by the step before.

### Gaps
- Gil Tene's talk "How NOT to Measure Latency" (the canonical coordinated-omission talk) was not fetched. This file relies on the wrk2 and HdrHistogram docs he wrote.
- DDSketch's quantitative accuracy and size figures (for example, its relative-error parameter and bucket counts) were not extracted. Only the abstract was read.
- The OpenTelemetry exponential-histogram spec and its status were not verified this round.
- The Prometheus 3.8 stability date and the opt-in details come from secondary blogs, not the Prometheus changelog.
- No 2024–2026 public study replacing the old latency-to-revenue numbers was found. DDIA notes that newer company data appears not to be public.

## 3. Reliability: faults vs failures, hardware fault rates, software faults, human error and operations, gray failure, metastability, chaos engineering

### Takeaway
Reliability means continuing to provide the required service (meeting the SLO) while components are faulty. Hardware faults are frequent but mostly independent: about 1.4–1.7% of HDDs fail per year in Backblaze's 2025–2026 fleet, more than 1% of machines hit uncorrectable DRAM errors per year, and about 1 in 1,000 CPUs silently miscomputes. Software and operational faults are correlated and cause the big outages. Among the named incidents are S3 in 2017, Google Cloud in June 2025, AWS us-east-1 in October 2025 and Cloudflare in November 2025. The two hardest patterns to teach, and the most important, are gray failure (the failure detector sees "healthy" while users see "broken") and metastable failure (retries keep a system down after its trigger has gone).

### Cited Findings

**Concept card: fault vs failure, fault tolerance, SPOF**
- A *fault* is one component stopping working correctly (a disk, a machine, a dependency). A *failure* is the whole system no longer providing the required service, meaning it misses the SLO. They are the same event seen at different levels. A part whose fault becomes a failure of the whole system is a single point of failure. — [DDIA 2e p.43 (PDF 67)][ddia]
- Fault tolerance is always limited to a certain number and type of faults. Deliberately injecting faults exercises the recovery machinery, which matters because many critical bugs live in error handling. DDIA's chaos-engineering reference is Rosenthal and Jones, *Chaos Engineering* (O'Reilly, 2020). Prevention beats tolerance for security faults, because a breach cannot be undone. — [DDIA 2e p.44 (PDF 68)][ddia]
- A temporary outage of minutes or hours is often tolerable; permanent loss or corruption of data is catastrophic. DDIA's example is the UK Post Office Horizon scandal (1999–2019): sub-postmasters were convicted on the strength of buggy accounting software, under a legal presumption that computers work correctly. — [DDIA 2e p.48–49 (PDF 72–73)][ddia]

**Concept card: hardware faults (with 2025–2026 numbers)**
- DDIA 2e figures:
  - 2–5% of HDDs fail per year, from 2007 FAST studies, so a 10,000-disk cluster loses about 1 disk a day.
  - 0.5–1% of SSDs fail per year, and uncorrectable errors occur about once per drive-year even in new drives.
  - About 1 in 1,000 machines has a CPU core that sometimes computes wrong results.
  - Even with ECC, more than 1% of machines hit an uncorrectable memory error per year.
  - Rowhammer-style access patterns can flip bits.
  - Whole datacenters can be lost (power, misconfiguration, fire, flood, solar storms).
  — [DDIA 2e p.44–45 (PDF 68–69)][ddia]
- **Updated HDD data (Backblaze):**
  - 2025 annual AFR 1.36% (344,196 drives, 30 models), down from 1.55% in 2024. Q4 2025 AFR 1.13% on 337,192 drives. — [Backblaze Drive Stats for 2025 (Feb 2026)](https://www.backblaze.com/blog/backblaze-drive-stats-for-2025/); [StorageReview](https://www.storagereview.com/news/backblaze-2025-year-end-drive-stats-annual-afr-falls-to-1-36-as-high-capacity-drives-dominate-fleet)
  - Q2 2026 (April–June) AFR 1.73%, up from 1.24% in Q1 2026 and the highest "in quite a while": 354,415 drives, 1,498 failures, 31,553,350 drive-days. Lifetime AFR 1.41%. The high-AFR outliers (threshold 6.95%) were ageing models: HGST 12 TB at 7.63% (nearly 7 years old), Seagate 10 TB at 9.33% (about 8.5 years old) and Seagate 14 TB at 8.26%. Drives of 20 TB and above are over 25% of the fleet. The report gives no SSD numbers (boot drives are excluded). — [Backblaze Drive Stats for Q2 2026 (29 Sep 2026)](https://www.backblaze.com/blog/backblaze-drive-stats-for-q2-2026/)
  - Conflict: one summary of the 2025 report gives lifetime AFR as 1.30%, while the Q2 2026 report says 1.41% "after a slight uptick". The inclusion criteria differ. — [StorageReview](https://www.storagereview.com/news/backblaze-2025-year-end-drive-stats-annual-afr-falls-to-1-36-as-high-capacity-drives-dominate-fleet); [Backblaze Q2 2026](https://www.backblaze.com/blog/backblaze-drive-stats-for-q2-2026/)
- **DRAM (Google fleet, 2.5 years, SIGMETRICS 2009):** about a third of machines and over 8% of DIMMs see at least one correctable error per year. Uncorrectable errors affect 1.3% of machines per year. FIT rates are 25,000–70,000 per Mbit, orders of magnitude above earlier lab estimates. Hard errors dominate soft ones, and newer DIMM generations were no worse. — [Schroeder, Pinheiro and Weber, "DRAM Errors in the Wild"](https://research.google/pubs/dram-errors-in-the-wild-a-large-scale-field-study/); [The Register summary](https://www.theregister.com/2009/10/12/google_server_memory/)
- **CPU silent data corruption (SDC):** over the past four years Meta, Google and Alibaba have disclosed about 1 in 1,000 CPUs producing SDCs. SIGARCH cautions that this means 1 chip in 1,000 was *identified* as defective in a way that can generate SDCs. — [SIGARCH, "SDCs A-B-C"](https://www.sigarch.org/sdcs-a-b-c/). The underlying papers are Hochschild et al., "Cores That Don't Count" (HotOS 2021), and Dixit et al., "Silent Data Corruptions at Scale" (arXiv 2021). — [DDIA 2e refs 51–52][ddia]; [arXiv:2102.11245](https://ar5iv.labs.arxiv.org/html/2102.11245)
- **Correlation:**
  - Redundancy (RAID, dual power supplies, generators) works best when faults are independent, but component failures are significantly correlated. Rack and datacenter outages happen more often than people expect. Cloud systems therefore tolerate the loss of whole machines, racks and availability zones in software, which also allows rolling upgrades. — [DDIA 2e p.45–46 (PDF 69–70)][ddia]
  - Aurora is the canonical design response. To survive an AZ plus one more node (AZ+1) without data loss, it keeps 6 copies across 3 AZs, 2 per AZ, with V = 6, write quorum 4 and read quorum 3. To make a double fault unlikely it shrinks MTTR: storage is cut into 10 GB segments, and one repairs in about 10 s on a 10 Gbps link. — [Verbitski et al., "Amazon Aurora", SIGMOD 2017](https://web.stanford.edu/class/cs245/readings/aurora.pdf)
- **Misconceptions:**
  - "MTTF on the datasheet predicts failures." DDIA cites Schroeder and Gibson (FAST 2007), "What Does an MTTF of 1,000,000 Hours Mean to You?". — [DDIA 2e ref. 43][ddia]
  - "ECC means memory is safe."
  - "CPUs don't make arithmetic mistakes."
  - "Redundant parts fail independently."

**Concept card: software faults, error handling, cascading and metastable failures**
- Software faults are highly correlated, because every node runs the same code. Examples:
  - The 30 June 2012 leap second hung many Java applications through a Linux kernel bug.
  - An HPE SSD firmware bug made certain models fail after exactly 32,768 hours of operation.
  - Runaway resource consumption, slow or corrupt dependencies, emergent interactions and cascading failures.
  Such bugs lie dormant until an assumption about the environment stops being true. — [DDIA 2e p.46–47 (PDF 70–71)][ddia]
- Yuan et al. (OSDI 2014) studied 198 user-reported failures in production distributed data-intensive systems. 92% of catastrophic failures came from incorrect handling of non-fatal errors, many of them trivial (empty handlers, TODO/FIXME). In 58%, simple tests of the error-handling code would have caught the bug. Their Aspirator checker found 143 new bugs. — [Yuan et al., OSDI 2014](https://www.eecg.utoronto.ca/~stumm/Papers/Yuan-OSDI-14.pdf); [Morning Paper summary](https://blog.acolyer.org/2016/10/06/simple-testing-can-prevent-most-critical-failures/)
- **Metastable failures:** Bronson et al. framed them at HotOS 2021. Huang et al. (OSDI 2022) studied 22 metastable failures from 11 organizations, drawn from a survey of over 600 public post-mortems:
  - At least 4 of 15 major AWS outages in the past decade were metastable.
  - Retry policy is the most common sustaining effect, present in over 50% of incidents.
  - 45% had more than one trigger.
  — [Huang et al., "Metastable Failures in the Wild", OSDI 2022](https://www.usenix.org/conference/osdi22/presentation/huang-lexiang)
- Google SRE's chapter on cascading failures says synchronized retries amplify overload. — [SRE book ch. 22](https://sre.google/sre-book/addressing-cascading-failures/) (as summarized in the [earlier report][prev])
- **Named incidents (software or configuration, correlated):**
  - **Google Cloud, 12 June 2025 (10:51–18:18 PT):**
    - A policy change with blank fields was written to regional Spanner tables and replicated globally within seconds.
    - It hit a quota-check code path in Service Control, added on 29 May, that had no error handling and no feature flag. A null pointer crashed the binary everywhere.
    - A kill switch mitigated it. The status dashboard ran on the affected infrastructure and could not be updated at first.
    - Google committed to feature-flag all critical binary changes and to audit consumers of globally replicated data.
    — [Google Cloud incident report](https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW); [Simon Willison's notes](https://www.simonwillison.net/2025/Jun/14/google-cloud-outage-incident-report)
  - **AWS us-east-1, 19–20 October 2025 (11:48 PM PDT to 2:20 PM PDT):**
    - A latent race condition in DynamoDB's automated DNS management left an empty DNS record for `dynamodb.us-east-1.amazonaws.com`.
    - DynamoDB errors lasted until 2:40 AM. EC2 API and launch failures continued to 1:50 PM, and NLB connection errors ran 5:30 AM–2:09 PM.
    - Global features that depend on us-east-1, such as IAM updates and DynamoDB Global Tables, were affected, and some services had backlogs for hours afterwards.
    — [AWS post-event summary](https://aws.amazon.com/message/101925); [InfoQ](https://www.infoq.com/news/2025/11/aws-dynamodb-outage-postmortem); [ThousandEyes](https://www.thousandeyes.com/blog/aws-outage-analysis-october-20-2025)
  - **Cloudflare, 18 November 2025:**
    - A ClickHouse permissions change made the query that builds the Bot Management "feature file" return duplicate rows, because it did not filter by database name. The file roughly doubled.
    - The proxy had a lower size limit on that file, so FL2 proxies failed as the file propagated, regenerated every 5 minutes, which produced flapping.
    - Automatic deployment stopped at 14:24 UTC and the previous file was redeployed at 14:30. It was not an attack.
    - Secondary write-ups disagree on feature counts and end times.
    — [Cloudflare postmortem](https://blog.cloudflare.com/18-november-2025-outage/) (URL from search results, not opened); [CircleID](https://circleid.com/posts/cloudflare-explains-major-outage-in-detailed-post-mortem); [ilert postmortem library](https://www.ilert.com/postmortems/cloudflare-global-outage-nov-2025)
- **Misconceptions:**
  - "More retries mean more reliability."
  - "If each component passed its tests, the system works." That ignores emergent interactions and dormant assumptions. — [DDIA 2e p.46–47][ddia]

**Concept card: humans and operations**
- Oppenheimer, Ganapathi and Patterson (USITS 2003) found configuration changes by operators to be the leading cause of outages, with hardware involved in only 10–25%. DDIA argues that "human error" is a symptom of the sociotechnical system rather than a root cause. It recommends testing (including property testing), fast config rollback, gradual rollouts, monitoring and observability, well-designed interfaces, and blameless postmortems. It warns against simplistic fixes, from "Bob should be more careful" to "rewrite it in Haskell". — [DDIA 2e p.47–48 (PDF 71–72)][ddia]
- The SRE book's introduction says roughly 70% of outages are due to changes in a live system, and pairs that with progressive rollouts, fast detection and safe rollback. The SRE Workbook's postmortem appendix reportedly attributes 37% of outage triggers to binary pushes and 31% to configuration pushes. — [secondary: datainterview summary](https://www.datainterview.com/courses/site-reliability-engineering/safe-changes); [SRE Workbook Appendix C](https://sre.google/workbook/postmortem-analysis)
- **AWS S3, 28 February 2017:**
  - An authorized engineer following an established playbook mistyped one input to a capacity-removal command at 9:37 AM PST, removing far more servers than intended.
  - That took out the index subsystem (all object metadata) and the placement subsystem, both of which had to fully restart. Neither had been fully restarted in large regions for many years, and the restarts were slow.
  - Index was back for GET, LIST and DELETE at 12:26 PM, and placement recovered at 1:54 PM, about 4 h 17 min after the command. EC2 launches, EBS snapshot restores and Lambda were affected.
  - AWS's fixes: the tool now removes capacity more slowly, refuses to go below minimum capacity, other tools were audited, and work to split the index into cells was reprioritized.
  — [AWS S3 post-event summary](https://aws.amazon.com/message/41926/)
- Automation is double-edged. The cases it cannot handle are the hardest ones, so more automation needs more skilled operators (Bainbridge, "Ironies of Automation", 1983). DDIA quotes Jay Kreps's 2012 point that good operations can work around bad software, but not the reverse. — [DDIA 2e p.53–54 (PDF 77–78)][ddia]

**Concept card: gray failure (Huang et al., HotOS 2017, Microsoft Research and Azure)**
- **Definition:** a subtle component failure that defies quick detection, such as performance degradation, random packet loss, flaky I/O, memory thrashing, capacity pressure or non-fatal exceptions. The authors' experience is that gray failure, not fail-stop failure, is behind most incidents in their cloud. — [Gray Failure, HotOS 2017](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/06/paper-1.pdf)
- **Differential observability:** a system has a gray failure when at least one app observes it as unhealthy while the system's own observer sees it as healthy. Of the four observer-versus-app cases, this is the one where users suffer and the reactor does nothing. Example: the request-handling module is stuck, but the heartbeat module still answers. — [Gray Failure](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/06/paper-1.pdf)
- **Azure cases:**
  1. *High redundancy hurts.* In a Clos network with n core switches and fan-out m, the probability that a request crosses a given core switch is 1 − ((n−1)/n)^m, which approaches 1 as m grows. More switches therefore raise the chance that some switch is silently dropping packets on nearly every request.
  2. *Under the radar.* A VM's external network was broken by a driver bug, but its heartbeats travelled through the host agent over local RPC, so no recovery happened until a user complained.
  3. *Recovery that kills.* A capacity-constrained storage server with a resource-reporting bug kept receiving writes, crashed, rebooted and was eventually removed. That shifted load onto healthy servers and caused a cascade.
  4. *The blame game.* Storage or network faults crashed VMs, and the compute stack was blamed.
  — [Gray Failure](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/06/paper-1.pdf)
- **Temporal evolution:** latent failure (absorbed), then gray failure (visible to apps, not to the observer), then complete failure (visible to both). Memory leaks are the typical example. — [Gray Failure](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/06/paper-1.pdf)
- **Misconceptions:**
  - "Health check green means healthy."
  - "Add more redundancy to fix availability."
  - "Reboot fixes it."

### Inferences
- **Expected HDD failures** (computed): a 10,000-disk cluster at Backblaze's 2025 AFR of 1.36% loses about 136 disks a year, or 1 every 2.7 days. That is a third of DDIA's "about 1 a day", which rests on 2007-era 2–5% rates. Backblaze's own fleet saw about 16.5 failures a day in Q2 2026 (1,498 over 91 days). Present both numbers and say the rate is lower than in 2007 but still routine. Old drives (7 years and up) can run 7–9% AFR, which illustrates the bathtub curve. The report itself does not use the term.
- **Correlation is the course's through-line.** Hardware faults are mostly independent, so redundancy works. Software and configuration faults are correlated, so redundancy multiplies them. Every 2025 named incident was a correlated, globally propagated configuration or data change (Google, Cloudflare) or a latent race in automation (AWS).
- **The incidents share a defense pattern:** staged propagation of configuration and data (canary requests, as in Tail at Scale), validation of inputs at the consumer (size limits, null checks), feature flags, and cells.
- **Gray failure and Tail at Scale fit together.** Latency-induced probation is a gray-failure detector built from the app's own view. Teach them together.

### Gaps
- CrowdStrike's July 2024 incident (Microsoft's 8.5-million-device estimate) could not be verified: the session's web-search budget ran out. Re-verify before use.
- The history of Netflix Chaos Monkey and the Simian Army (2011) and the current tooling (AWS FIS, Chaos Mesh, Jepsen) were not verified this round, for the same reason.
- No 2025–2026 field study of SSD failure rates was found. The Q2 2026 Backblaze report excludes boot SSDs. The 2026 CACM "Revisiting CPU Silent Data Corruptions in Modern Datacenters" (DOI 10.1145/3799406) was found but not read.
- A July 16, 2026 AWS incident (VPC-origin routing capacity) and several 2026 GCP and Kubernetes incidents appeared only in low-confidence secondary sources, so they are excluded.
- The full text of the Cloudflare postmortem was not opened, so its figures rest on secondary summaries that conflict on details.

## 4. Scalability: describing load, the home-timeline fan-out case, vertical vs horizontal, shared-memory/disk/nothing, storage–compute separation, serverless, microservices, when one node is enough

### Takeaway
"Scalable" is meaningless without naming the load parameter and the growth path. The home-timeline case shows the core trade-off: fan-out on read costs about 400 million lookups per second at Twitter scale, fan-out on write about 1 million writes per second plus a celebrity problem, and production systems use hybrids. Twitter (2012) merged celebrity posts at read time. Bluesky (2025) drops timeline writes for accounts that follow tens of thousands of others. Cloud-native systems revived shared storage through database-specific storage services: Aurora, Snowflake, Neon, Kafka tiered storage and the accepted KIP-1150 diskless topics, and S3 Express One Zone. Meanwhile a single machine (up to 1,920 vCPUs and 32 TiB of RAM on EC2) and a competent single thread beat many clusters, which is the COST paper's point.

### Cited Findings

**Concept card: describing load**
- Load is described by parameters such as requests per second, gigabytes ingested per day, peak concurrent users, read/write ratio, cache hit rate and items per user (followers). Sometimes the average matters; sometimes a few extreme cases dominate. Two questions follow. If load grows and resources stay fixed, what happens to performance? How much must resources grow to keep performance fixed? Linear scalability means 2x the resources handle 2x the load. Cost usually grows faster. — [DDIA 2e p.50 (PDF 74)][ddia]
- There is no generic "magic scaling sauce". 100,000 req/s of 1 kB and 3 req/min of 2 GB are both 100 MB/s, but they need very different architectures. Expect to rethink the architecture at each order of magnitude, and don't plan more than one order ahead. — [DDIA 2e p.52 (PDF 76)][ddia]
- At a startup, scaling for hypothetical load is premature optimization and can lock in an inflexible design. "X is scalable" is a one-dimensional label and therefore meaningless. — [DDIA 2e p.49 (PDF 73)][ddia]

**Concept card: the home-timeline case study**
- **DDIA's hypothetical:**
  - 500 million posts a day, about 5,800 per second on average, with spikes to 150,000 per second. The average user follows 200 accounts and has 200 followers, with a very skewed distribution (celebrities above 100 million followers).
  - Pull: a SQL join over `follows` and `posts` sorted by time, limit 1,000. With 10 million online users polling every 5 s, that is 2 million queries per second, and at 200 follows each, 400 million lookups per second.
  - Push: fan-out on write into per-user timeline caches (a materialized view) costs about 5,800 × 200 ≈ 1.16 million timeline writes per second. Writes can be queued during spikes while reads stay fast.
  - Two extremes. Users who follow many prolific accounts get *sampled*: some writes are dropped (citing Bluesky). Celebrity posts are stored separately and merged at read time. DDIA also cites the 2010 report that 3% of Twitter's servers served Justin Bieber.
  — [DDIA 2e p.34–36 and refs 1–6 (PDF 58–60, 81)][ddia]
- **Twitter, 2012 (Raffi Krikorian, "Timelines at Scale", QCon SF, Nov 2012):**
  - About 150M active users. Timeline reads at 300K QPS. Writes about 6,000 req/s, with tweets averaging 5K/s, peaking at 7K/s and over 12K/s during big events. 400M tweets a day.
  - About 30B timeline deliveries a day. The 22 MB/s firehose served about 1M open push sockets.
  - Home timelines lived in Redis, capped at 800 entries, with 3 replicas per tweet, a couple of terabytes of RAM in total, and fan-out pipelined in 4K-destination batches.
  - Target delivery within 5 s. Delivering to 1M followers took about 3.5 s at p50, but a tweet from a 31M-follower account (Lady Gaga) could take up to 5 minutes at p99.
  - Timeline Service reads took about 5 ms at the median and 100 ms at p99.
  - A planned hybrid stopped fanning out very-high-follower accounts and merged them at read time, saving tens of percent of compute.
  - Search (Earlybird) is the opposite pattern: O(1) writes and scatter-gather O(n) reads.
  - The source page is dated July 2013 and its write figures are internally inconsistent.
  — [High Scalability summary of Krikorian's talk](http://highscalability.com/blog/2013/7/8/the-architecture-twitter-uses-to-deal-with-150m-active-users.html)
- **Peak load record:** 143,199 tweets per second on 2–3 August 2013, during a Japanese TV airing of *Castle in the Sky*. The previous record was 25,088 in 2011 from the same film. Twitter said the site didn't "blip". — [SlashGear](https://www.slashgear.com/twitter-scores-new-tweets-per-second-record-with-143000-peak-16294065); [TechCrunch, 2011 record](https://techcrunch.com/?p=468379). DDIA's "150,000/s" spike comes from this source (Krikorian, "New Tweets per Second Record, and How!", Aug 2013). — [DDIA 2e ref. 4][ddia]
- **Twitter/X, 2023 (open-sourced recommendation algorithm):** the For You timeline draws about 1,500 candidates per request, on average 50% in-network (followed accounts) and 50% out-of-network. Graph-based heuristics serve about 15% of home timeline tweets, and embedding approaches are the larger out-of-network source. Home Mixer assembles the final timeline. The timeline became a ranked, candidate-generation pipeline rather than a pure chronological fan-out. — [Twitter Engineering, "Twitter's Recommendation Algorithm", Mar 2023](https://blog.Twitter.com/engineering/en_us/topics/open-source/2023/twitter-recommendation-algorithm); [twitter/the-algorithm](https://github.com/twitter/the-algorithm)
- **Bluesky, February 2025 (Jaz Volpert, "Bluesky's Lossy Timelines"):**
  - Timelines live in ScyllaDB, one partition per user, across hundreds of shards, for about 32M users.
  - A timeline write averages about 600 µs. Sequential fan-out to a 2,000,000-follower account would take about 20 minutes.
  - Writing 1,000 timelines concurrently takes about 1.2 s, with p99 writes up to 15 ms. With 10,000 followers per page, a worst-case page takes about 1.5 s, so a 2M-follower fan-out could take up to 5 minutes, and tens of minutes at p99.9.
  - Users who follow hundreds of thousands of accounts created hot shards.
  - The fix: `loss_factor = min(reasonable_limit/num_follows, 1)`, with `reasonable_limit` = 2,000. Following 4,000 accounts drops about half of writes; following 8,000 drops 75%.
  - Follow counts for heavy followers are cached in a Redis sorted set and reloaded every 30 s. Without that cache, lookups would add over 1M reads per second to the primary database.
  - Results: hot shards disappeared, single-page fan-out p99 fell over 90%, full-post fan-out p99 fell over 96%, and large-account fan-out went from 5–10 min to under 10 s.
  — [jazco.dev, 19 Feb 2025](https://jazco.dev/2025/02/19/imperfection/)
- **Misconceptions:**
  - "Push is always better than pull" or the reverse. DDIA's numbers and the celebrity case show each fails at an extreme.
  - "Timelines must be complete and exact." Bluesky drops writes on purpose.
  - "Scaling problems come from the average user." The extremes dominate. — [DDIA 2e p.36][ddia]; [jazco.dev](https://jazco.dev/2025/02/19/imperfection/)

**Concept card: vertical vs horizontal; shared-memory vs shared-disk vs shared-nothing**
- **Shared-memory (vertical, scale-up):** threads share RAM. Cost grows faster than linearly, and a 2x machine rarely handles 2x the load because of bottlenecks. **Shared-disk:** independent CPUs and RAM over a NAS or SAN, traditionally used for on-premises warehousing, but limited by contention and lock overhead. **Shared-nothing (horizontal, scale-out):** each node has its own CPU, RAM and disk and coordinates over the network. It can scale linearly, use the best price/performance hardware, resize elastically and span datacenters, at the cost of explicit sharding and distributed-systems complexity. Cloud-native databases with separate storage services resemble shared-disk, but the storage offers a database-specific API instead of a filesystem or block device (citing Microsoft's Socrates). — [DDIA 2e p.51 (PDF 75)][ddia], citing Stonebraker, "The Case for Shared Nothing", IEEE Database Engineering Bulletin 9(1), 1986 (DDIA ref. 84; the original was not fetched)
- **Today's vertical ceiling:** EC2 `u7inh-32tb.480xlarge` has 1,920 vCPUs and 32,768 GiB of DDR5 on a 16-socket HPE Compute Scale-up Server 3200, with 200 Gbps networking. It became generally available on 16 December 2024, only in us-east-1 and us-west-2 and only through 3-year Savings Plans. — [AWS What's New, Dec 2024](https://aws.amazon.com/about-aws/whats-new/2024/12/amazon-ec2-high-memory-u7inh-instance); [AWS News Blog](https://aws.amazon.com/blogs/aws/new-amazon-ec2-high-memory-u7inh-instance-on-hpe-server-for-large-in-memory-databases)
- **Principles:** break the system into components that operate largely independently (microservices, sharding, stream processing, shared-nothing), and don't make it more complicated than necessary. A single-machine database beats a complex distributed setup if it does the job. Predictable load may suit manual scaling better than autoscaling, and 5 services are simpler than 50. — [DDIA 2e p.52 (PDF 76)][ddia]

**Concept card: separating storage from compute (cloud-native)**
- **Problem:** on a local disk, data is lost or stranded when the instance fails or is resized. Virtual block devices (EBS) make every I/O a network call, so network glitches hurt. — [DDIA 2e p.16 (PDF 40)][ddia], citing PlanetScale, "The Real Failure Rate of EBS" (Mar 2025)
- **Simplest version:** run a traditional database on a network block device (EBS) and mirror it.
- **Where it breaks (Aurora's numbers):**
  - In a 30-minute SysBench write-only test on r3.8xlarge, mirrored MySQL on EBS completed 780,000 transactions at 7.4 I/Os each. Aurora completed 27,378,000 at 0.95 I/Os each: 35x the transactions and 7.7x fewer I/Os per transaction, despite writing six copies.
  - Storage nodes saw 46x fewer I/Os.
  — [Aurora, SIGMOD 2017, Table 1](https://web.stanford.edu/class/cs245/readings/aurora.pdf)
- **Improvement 1, "the log is the database" (Aurora):**
  - Only redo log records cross the network. Storage nodes apply redo continuously in the background.
  - Crash recovery generally takes under 10 s, even after a crash at over 100,000 writes per second, because nothing needs replaying at startup.
  - Volumes grow to 64 TB (at the time of the paper).
  — [Aurora paper](https://web.stanford.edu/class/cs245/readings/aurora.pdf)
- **Improvement 2, multi-cluster shared data (Snowflake, SIGMOD 2016):**
  - Snowflake rejected pure shared-nothing because coupling compute and storage breaks three things in the cloud: *heterogeneous workloads* (bulk load and complex queries want different hardware), *membership changes* (resizing reshuffles data on the same nodes that run queries) and *online upgrades*.
  - Design:
    - Storage lives on S3, and independent virtual warehouses of EC2 workers do the compute.
    - Each worker caches file headers and columns on local disk (SSD suggested) with LRU eviction. Lazy consistent hashing over file names means resizing reshuffles nothing.
    - *File stealing* handles stragglers.
  - Snowflake upgraded all services weekly and ran several million queries a day over multiple petabytes.
  — [Dageville et al., "The Snowflake Elastic Data Warehouse", SIGMOD 2016](https://www.cs.purdue.edu/homes/csjgwang/CloudNativeDB/SnowflakeSIGMOD16.pdf)
- **Improvement 3, Postgres with separate storage (Neon):**
  - Stateless Postgres compute nodes stream WAL to *safekeepers*, which replicate it with Paxos; a commit succeeds at quorum.
  - A *pageserver* builds page versions on demand from base pages plus WAL.
  - Object storage holds long-term history. Only the pageserver reads it, at up to hundreds of ms, never on the hot query path.
  - Compute caches in RAM and local NVMe. Branches are copy-on-write. Compute can scale to zero.
  - The page says Neon and Databricks run the same "Lakebase Postgres" on shared infrastructure.
  — [Neon architecture overview](https://neon.com/docs/introduction/architecture-overview)
- **Improvement 4, logs on object storage (Kafka):**
  - Tiered storage (KIP-405) was declared production-ready in Kafka 3.9 (6 November 2024). Kafka 4.3 and 4.4 (May and October 2026) added tiered-storage settings. — [Kafka 3.9.0 announcement](https://kafka.apache.org/blog/2024/11/06/apache-kafka-3.9.0-release-announcement/); [Kafka 4.4.0 announcement](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/) (both via the [earlier research round][prev])
  - **KIP-1150 Diskless Topics** has status "Accepted". These topics write through to object storage, use local disk only as cache, and run beside classic topics. The motivation is cross-AZ replication traffic: AWS charges $0.02/GiB, GCP $0.01/GiB, Azure nothing. Produce latency will be higher, with cost against latency chosen per topic. Implementation is split into KIP-1163 (Diskless Core) and KIP-1164 (Diskless Coordinator). — [KIP-1150 (cwiki)](https://cwiki.apache.org/confluence/display/KAFKA/KIP-1150:+Diskless+Topics)
  - The vote was restarted on 9 January 2026, and Slack withdrew the competing KIP-1176 to back KIP-1150. — [dev@kafka mail archive](https://mail-archive.com/dev@kafka.apache.org/msg153702.html)
- **Improvement 5, low-latency object storage (S3 Express One Zone):** AWS positions it for consistent single-digit-millisecond access, in a single AZ. Prices fell from 10 April 2025: storage −31% (us-east-1 from $0.16 to $0.11 per GB-month), PUT −55%, GET −85%. — [AWS News Blog, Apr 2025](https://aws.amazon.com/blogs/aws/up-to-85-price-reductions-for-amazon-s3-express-one-zone); [AWS What's New](https://aws.amazon.com/about-aws/whats-new/2025/04/amazon-s3-express-one-zone-reduces-storage-request-prices/)
- DDIA frames all of this as *disaggregation*. Object stores hold large blocks, from hundreds of KB to GB, so cloud databases keep small values in a separate service. Multitenancy improves utilization but needs isolation engineering. — [DDIA 2e p.16–17 (PDF 40–41)][ddia]
- **Misconceptions:**
  - "Shared-disk is a dead 1990s architecture." Its cloud-native form is the dominant design.
  - "Object storage is too slow to be a primary store." Neon hides object-store latency behind a pageserver, S3 Express is single-digit ms, and Kafka is moving to diskless.
  - "Cloud disks are durable local disks." They are network services. — [DDIA 2e p.16][ddia]

**Concept card: serverless**
- Serverless (FaaS) brings metered billing to code execution, as cloud storage did to disks. Its costs are execution time limits, restricted runtimes and cold starts. The name misleads, because functions still run on servers. "Serverless" has also become a marketing word for autoscaled, usage-billed services (BigQuery, various Kafka offerings). DDIA cites Hellerstein et al., "Serverless Computing: One Step Forward, Two Steps Back" (2018), and Shahrad et al., "Serverless in the Wild" (Azure Functions workload, 2020). — [DDIA 2e p.22 and refs 44, 53 (PDF 46)][ddia]
- **AWS Lambda change:** from 1 August 2025, the INIT phase (cold start) is billed at the standard duration rate for all configurations. AWS says cold starts occur in under 1% of invocations and suggests SnapStart to cut INIT cost. — [AWS Compute Blog](https://aws.amazon.com/blogs/compute/aws-lambda-standardizes-billing-for-init-phase/)
- **Misconception:** "Serverless is always cheaper." The Prime Video case below shows steady high-volume work moving off it.

**Concept card: microservices**
- **Benefits:** independent deploys, per-service resources, and freedom to change the implementation behind an API. Each service owns its database, because a shared database makes its schema part of the API. **Costs:** testing needs the services' dependencies running; every service needs deploy, scaling, logging, monitoring and on-call infrastructure (hence Kubernetes); API evolution breaks clients late; and cross-service consistency becomes the application's problem, since distributed transactions are rarely used. DDIA calls microservices mainly a technical solution to a people problem, valuable in large organizations and likely overhead in small ones. — [DDIA 2e p.21–22 and p.20–21 (PDF 44–46)][ddia]
- **Prime Video, March 2023:** the audio/video quality-monitoring service moved from a distributed design (reportedly Step Functions orchestration) to a single process, cutting infrastructure cost by over 90% and improving scaling. Commentators note that this was one service among many and that the savings came largely from dropping per-step serverless orchestration. — [DevClass, May 2023](https://devclass.com/2023/05/05/reduce-costs-by-90-by-moving-from-microservices-to-monolith-amazon-internal-case-study-raises-eyebrows/); the original post is on primevideotech.com (not opened)
- **Misconception:** "Microservices are how you scale." DDIA frames them as organizational. The scaling principle is independence, which sharding also provides. — [DDIA 2e p.22, p.52][ddia]

**Concept card: when one node is enough (COST, "Big Data is Dead", DuckDB)**
- DDIA's positions:
  - A network call is far slower than an in-process call, and moving computation to the data can beat moving data.
  - More nodes are not always faster. A single-threaded program can beat a cluster with more than 100 cores.
  - CPUs, memory and disks have grown, so single-node databases (DuckDB, SQLite, KùzuDB) cover many workloads.
  — [DDIA 2e p.20–21 (PDF 44–45)][ddia]
- **COST definition:** the Configuration that Outperforms a Single Thread, meaning the hardware a platform needs before it beats a competent single-threaded implementation. McSherry, Isard and Murray found that many published systems have a COST of hundreds of cores, or are unbounded (never beat one thread). They also show that removing parallelizable overhead can make a system's speed-up curve look *worse* while every configuration gets faster. — [McSherry, Isard, Murray, HotOS 2015](https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf)
- **COST numbers.** Graphs: twitter_rv has 41.7M nodes, 1.47B edges, 5.76 GB; uk-2007-05 has 105.9M nodes, 3.74B edges, 14.72 GB. The single thread ran on a high-end 2014 laptop. Times are twitter_rv / uk-2007-05.

  | System (cores) | PageRank, 20 iterations | Label-propagation connectivity |
  |---|---|---|
  | Spark (128) | 857 s / 1,759 s | 1,784 s / ≥8,000 s |
  | Giraph (128) | 596 / 1,235 | 200 / ≥8,000 |
  | GraphLab (128) | 249 / 833 | 242 / 714 |
  | GraphX (128) | 419 / 462 | 251 / 800 |
  | Single thread from SSD (1) | 300 / 651 | 153 / 417 |
  | Single thread from RAM (1) | 275 | – |
  | Hilbert-curve edge order, SSD (1) | 242 / 256 | – |
  | Hilbert-curve edge order, RAM (1) | 110 | – |
  | Union-find (1) | – | **15 s / 30 s** |

  Converting twitter_rv to Hilbert order took 179 s on one thread. Union-find wins because label propagation "fits" the vertex-centric model but does more work. — [COST paper, Tables 1–5](https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf)
- **"Big Data is Dead" (Jordan Tigani, MotherDuck, Feb 2023):** from his BigQuery experience, most customers had under 1 TB, and about 90% of queries processed under 100 MB. He calls the figures approximate. — [MotherDuck](https://motherduck.com/blog/big-data-is-dead/) (as cited in the [earlier report][prev])
- DuckDB 2.0.0 is an LTS release, end of life October 2027. Spark 4.3 added opt-in single-task execution for small queries. — [DuckDB release calendar](https://duckdb.org/release_calendar); [Spark 4.3.0](https://spark.apache.org/releases/spark-release-4-3-0.html) (via the [earlier report][prev])
- **Counterpoint:** backfills, multi-TB daily ingest and joins over years of fact data still need distributed engines. — [earlier report][prev]
- **Misconceptions:**
  - "Good scaling curves mean a good system." COST's system A vs system B shows otherwise.
  - "You need a cluster at 100 GB." Tigani's figures, COST and a 32 TiB instance all argue against.
  - "Distribution is free." It adds network calls, partial failure and observability cost. — [DDIA 2e p.20][ddia]

### Inferences
- **Timeline arithmetic** (computed from cited inputs):
  - Twitter 2012: 30B deliveries a day ≈ 347K timeline writes per second, against 300K read QPS. Writes and reads were already about equal, which is why fan-out-on-write was affordable for most accounts.
  - Bluesky: 2M followers × 600 µs ≈ 20 min sequential, which explains why fan-out must be parallel *and* why tail latency per write (15 ms p99) then dominates.
  - DDIA: pull costs 400M lookups/s and push costs 1.16M writes/s, about a 345x difference in favor of push for the average user. The crossover comes at extreme follower counts.
- **One model for scale:** pick the load parameter (posts/s, follows per user, followers per user), find which extreme dominates the cost, materialize where reads dominate, and handle the extremes separately (celebrity merge on read, lossy writes for heavy followers). That is the general lesson. The specific numbers are history (2012–2013) or single-company reports (2025).
- **The architecture stack as of November 2026** (inference from the cited pieces): object storage is the durable bottom layer (S3, S3 Express); a database-specific log or page service sits above it (Aurora storage, Neon safekeepers and pageserver, Kafka diskless); stateless compute with local SSD caches sits on top (Snowflake warehouses, Neon compute). Teach "where is the durable copy, and what is only a cache?" as the question to ask of any product.
- **COST as a classroom exercise:** implement union-find in Kotlin on a graph that fits in RAM and compare it with a label-propagation implementation. The 15 s versus 153–1,784 s spread shows that algorithm choice beats parallelism.

### Gaps
- The content of Mike Cvet's 2016 QCon talk ("How We Learned to Stop Worrying and Love Fan-in at Twitter") was not fetched, so Twitter's 2013–2016 move toward read-time fan-in is undocumented here.
- X's post-2023 in-network retrieval layer (reportedly "Thunder") is unverified. Bluesky's 2026 user count and any later timeline changes were not checked.
- KIP-1150's target Kafka release was not found. No shipped Kafka version includes diskless topics as far as these sources show. The status of WarpStream, AutoMQ and Confluent Freight was not checked.
- The launch date of S3 Express One Zone (believed to be re:Invent 2023), Aurora DSQL, Aurora Limitless, and the terms of the Databricks acquisition of Neon were not verified this round.
- The Prime Video original post was not opened; its figures come from DevClass.

## 5. Maintainability (operability, simplicity, evolvability) and cloud vs self-hosting trade-offs, including cost

### Takeaway
Most of a system's cost comes after launch. DDIA splits maintainability into operability (easy to run), simplicity (easy to understand, through good abstractions) and evolvability (easy to change, through minimal irreversibility). The cloud moves operations work from managing machines to managing cost, quotas and integration; it does not remove it. Whether self-hosting is cheaper depends on load predictability and in-house skill. 37signals is the most-cited 2024–2025 case: it moved about 5 PB off S3 to on-prem flash and reports about $1.3M a year in savings, with caveats about costs left out.

### Cited Findings

**Concept card: maintainability overall**
- Most software cost is in maintenance: fixing bugs, keeping systems running, investigating failures, porting, new features and repaying debt. Legacy systems lose institutional knowledge, and maintenance is as much a people problem as a technical one. Every valuable system eventually becomes legacy. — [DDIA 2e p.52–53 (PDF 76–77)][ddia]
- **Definitions:** *operability* makes it easy to keep the system running; *simplicity* makes it easy for new engineers to understand; *evolvability* makes it easy to change for unanticipated needs. — [DDIA 2e p.53 (PDF 77)][ddia]

**Concept card: operability**
- Data systems help operations when they:
  - expose metrics and support observability tools;
  - avoid dependence on any single machine;
  - document a clear operational model ("if I do X, Y happens");
  - ship good defaults that can be overridden;
  - self-heal while allowing manual control;
  - behave predictably.
  More automation is not always better: automated systems that go wrong are harder to debug, and the leftover cases need more skilled operators. — [DDIA 2e p.53–54 (PDF 77–78)][ddia]
- **Operations in the cloud era:** DevOps and SRE emphasize automation, ephemeral VMs, frequent deploys, learning from incidents and preserving organizational knowledge. Capacity planning becomes financial planning, and performance optimization becomes cost optimization. Teams must also know quotas and limits before they hit them, and integrate services that lack common standards. Security, service interaction, load monitoring and debugging cannot be outsourced. — [DDIA 2e p.17–18 (PDF 41–42)][ddia]
- Operability lessons from the named incidents: rate-limited destructive tools and minimum-capacity guards (S3 2017), feature flags and validation of globally replicated data (GCP 2025), and staged propagation of configuration files (Cloudflare 2025). — [AWS S3 summary](https://aws.amazon.com/message/41926/); [Google Cloud incident](https://status.cloud.google.com/incidents/ow5i3PPK96RduMcb1SsW); [CircleID on Cloudflare](https://circleid.com/posts/cloudflare-explains-major-outage-in-detailed-post-mortem)

**Concept card: simplicity (essential vs accidental complexity)**
- Complexity slows everyone and raises the risk of bugs on change; the extreme is the "big ball of mud". Simplicity is subjective: is a complex implementation behind a simple interface simpler than a simple implementation that exposes internals? Brooks split complexity into *essential* (inherent in the problem) and *accidental* (caused by tooling). DDIA notes the boundary moves as tools improve, citing Dan Luu's "Against Essential and Accidental Complexity" (2020). Abstraction is the main tool: SQL hides on-disk structures, concurrency and crash inconsistency. DDIA concentrates on general-purpose abstractions (transactions, indexes, event logs) rather than on application-level design such as patterns or DDD. — [DDIA 2e p.54–55 (PDF 78–79)][ddia]

**Concept card: evolvability**
- Evolvability is agility at the level of a whole data system. It depends on simplicity and loose coupling. A major obstacle is *irreversibility*: a database migration you cannot roll back raises the stakes, so minimize irreversible steps. — [DDIA 2e p.55–56 (PDF 79–80)][ddia]
- Microservice APIs are hard to evolve: removing fields breaks clients, and breakage often surfaces only in staging or production. OpenAPI and gRPC schemas help. — [DDIA 2e p.22 (PDF 46)][ddia]
- **Legal evolvability:** GDPR's right to erasure conflicts with immutable append-only logs and with derived data such as ML training sets. The regulation deliberately does not prescribe technologies. — [DDIA 2e p.24 (PDF 48)][ddia]

**Concept card: cloud vs self-hosting**
- **The spectrum:** bespoke in-house software → self-hosted off-the-shelf software (on-premises or on IaaS VMs) → SaaS and cloud services. The rule of thumb is to build core competencies in-house and buy what is commodity. — [DDIA 2e p.12 (PDF 36)][ddia]
- **The trade-off:**
  - Self-hosting is often cheaper with existing expertise and predictable load. DDIA cites DHH, "Why We're Leaving the Cloud" (2022), and Badizadegan, "Use One Big Server" (2022).
  - The cloud wins on variable load. Analytics is the archetype: queries need large parallel bursts and then sit idle.
  - Cloud downsides: you cannot add features yourself, you wait out outages, debugging internals is hard, vendors deprecate or reprice (lock-in, no standard APIs), sanctions can cut access, and you must trust the provider with the data.
  - Very latency-sensitive workloads such as HFT need control of the hardware.
  — [DDIA 2e p.13–14 (PDF 37–38)][ddia]
- **Cloud-native systems** have been shown to perform better on the same hardware, recover faster, scale faster and handle larger datasets. Examples: Aurora, Azure SQL Hyperscale (Socrates), Spanner, Snowflake, BigQuery and Synapse. Their self-hosted counterparts include MySQL, PostgreSQL, MongoDB, Teradata, ClickHouse and Spark. Cloud services build on lower-level ones, as Snowflake builds on S3. — [DDIA 2e p.14–15, Table 1-2 (PDF 38–39)][ddia]
- **37signals' cloud exit:**
  - The remaining S3 footprint cost just under $1.5M a year.
  - The company bought about $1.5M of Pure Storage hardware (18 PB) that it expects to cost under $200K a year to run, for about $1.3M a year in savings.
  - The S3 contract ended 30 June 2025, and the 4-year term had been the condition for the low price.
  - Engineering moved 5 PB (5 billion files) to Pure FlashBlade with no downtime, in under 10 days.
  - Earlier claims: about $2M saved in 2024, and $10M over 5 years.
  - Critics note that hardware refreshes and extra operations roles are excluded.
  - Sources conflict on the size: 10 PB on S3 versus roughly 5–6 PB transferred.
  — [The Register, May 2025](https://www.theregister.com/2025/05/09/37signals_cloud_repatriation_storage_savings); [37signals dev blog](https://dev.37signals.com/moving-mountains-of-data-off-s3/); [DHH, "It's five grand a day to miss our S3 exit"](https://world.hey.com/dhh/it-s-five-grand-a-day-to-miss-our-s3-exit-b8293563); [ITPro](https://www.itpro.com/cloud/cloud-computing/this-software-company-says-ditching-the-cloud-was-worth-usd10-million-in-savings-and-theres-still-more-to-come)
- **Hidden cloud cost that shapes architecture:** cross-AZ transfer costs $0.02/GiB on AWS and $0.01 on GCP, and is free on Azure. This alone motivates Kafka's diskless topics. — [KIP-1150](https://cwiki.apache.org/confluence/display/KAFKA/KIP-1150:+Diskless+Topics)
- **Misconceptions:**
  - "The cloud means no ops." — [DDIA 2e p.18][ddia]
  - "The cloud is always cheaper", or always dearer. It depends on load variability, skills and contract terms. — [DDIA 2e p.13][ddia]; [The Register](https://www.theregister.com/2025/05/09/37signals_cloud_repatriation_storage_savings)
  - "More automation always helps."
  - "Essential complexity is fixed." — [DDIA 2e p.53–55][ddia]

### Inferences
- **Teach cloud cost as a unit-economics exercise** (inference): $/GB-month for storage (S3 Express is $0.11 in us-east-1; 37signals' on-prem works out to about $0.001 per GB-month in operating cost, from $200K a year over 18 PB, before hardware amortization and staff), plus $/GiB for cross-AZ traffic. Then ask which architecture each price makes cheapest. This is computed from cited figures and approximate.
- **Operability ties back to reliability:** most of the 2017–2025 incidents above were operability failures (unsafe tools, unflagged changes, global propagation without a canary), not hardware failures.
- **Simplicity cuts both ways:** the COST and "one node" material is the simplicity argument applied to scale. "If a single-machine database will do the job" is both a scalability principle and a maintainability principle. — [DDIA 2e p.52][ddia]

### Gaps
- No independent, audited TCO comparison of cloud versus self-hosted data systems for 2025–2026 was found. The 37signals figures are self-reported.
- Changes to the major clouds' egress fees for customers leaving (2024) and the effect of the EU Data Act were not verified this round.
- No source gave survey data on how much of a team's time maintenance takes in 2025–2026. DDIA's claim cites older literature (refs 87–88).

## 6. Hands-on lab ideas: measuring percentiles and coordinated omission, simulating fan-out tail amplification, comparing fan-out on write vs read

### Takeaway
Every concept above can be made visible on a laptop with Kotlin on JDK 21+ (JDK 25 is the LTS baseline per the earlier report), Gradle, HdrHistogram 2.2.2, and Testcontainers 2.0.5 for PostgreSQL and Redis. Each lab should end in a number the learner predicts first and then measures, and the cited papers supply the reference values: wrk2's 200x p99 error under coordinated omission, Tail at Scale's 63% and 1,800→74 ms, the M/M/1 1/(1−ρ) curve, Twitter's 800-entry timelines and Bluesky's `loss_factor`.

### Cited Findings
- Load-generation facts the labs rely on:
  - Open-model generation (constant arrival rate, latency timed from the intended send time) is the correction for coordinated omission. — [wrk2 README](https://github.com/giltene/wrk2); [k6 open vs closed](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)
  - `recordValueWithExpectedInterval()` corrects closed-loop data, histograms are additive, and recording takes constant time and memory (about 185 KB for 1 µs–1 h at 3 significant digits). — [HdrHistogram README](https://github.com/HdrHistogram/HdrHistogram)
  - wrk2's example: a 1.4 s stall gives a corrected p99 of 1.27 s against 6.04 ms uncorrected. — [wrk2 README](https://github.com/giltene/wrk2)
- Reference numbers for the fan-out labs: P(slow) = 63% at a 1% slow rate and fan-out 100; 18% at 0.01% and 2,000; hedging at 10 ms gave 1,800→74 ms p99.9 for 2% extra requests; Table 1 and Table 2 values. — [The Tail at Scale](https://www.barroso.org/publications/TheTailAtScale.pdf)
- Reference numbers for the timeline lab:
  - Twitter: 800-entry Redis timelines, 3 replicas, 4K-batch fan-out, 5 s delivery target, up to 5 min to deliver for 31M followers at p99. — [High Scalability](http://highscalability.com/blog/2013/7/8/the-architecture-twitter-uses-to-deal-with-150m-active-users.html)
  - Bluesky: `loss_factor = min(2000/num_follows, 1)`, 600 µs per write, 10,000-follower pages. — [jazco.dev](https://jazco.dev/2025/02/19/imperfection/)
  - DDIA's pull SQL and the 400M vs 1.16M per second figures. — [DDIA 2e p.34–36][ddia]
- Reference numbers for the queueing lab: E[N] = ρ/(1−ρ). — [Brooker](https://brooker.co.za/blog/2021/08/05/utilization.html); L = λW — [Little's law](https://en.wikipedia.org/wiki/Little%27s_law)
- Reference numbers for the metastability lab: retries are the sustaining effect in over 50% of studied metastable incidents. — [Huang et al., OSDI 2022](https://www.usenix.org/conference/osdi22/presentation/huang-lexiang). DDIA's mitigation list (exponential backoff with jitter, circuit breaker, token bucket, load shedding, backpressure). — [DDIA 2e p.38][ddia]. gRPC `retryThrottling` and `hedgingPolicy`. — [gRPC hedging guide](https://grpc.io/docs/guides/request-hedging)
- Reference numbers for the SLO lab: the burn-rate table (14.4/6/1; 1 h/6 h/3 d; 2%/5%/10%) and its edge cases (26 s at 99.999%; 13.9% per failure at 10 req/h). — [SRE Workbook](https://sre.google/workbook/alerting-on-slos/)
- Reference numbers for the COST lab: union-find at 15 s versus label propagation at 153 s single-threaded and 200–1,784 s on 128-core systems, on twitter_rv. — [COST paper](https://www.usenix.org/system/files/conference/hotos15/hotos15-paper-mcsherry.pdf)
- Build pins from the earlier round: Gradle 9.9.0, Kotlin 2.4.21, kotlinx-coroutines 1.11.0, JUnit 6.1.3, Testcontainers 2.0.5; images `postgres:18.6` and `redis:8.10.3`. The earlier research machine had no Docker, so no container lab has been executed. — [earlier report][prev]
- Library versions checked on Maven Central for this file: HdrHistogram 2.2.2, sketches-java (DDSketch) 0.8.3, t-digest 3.3. Micrometer's newest artifact is a release candidate, 1.18.0-RC2, so pin the latest GA release instead (which version that is was not checked). — [Maven Central metadata](https://repo1.maven.org/maven2/org/hdrhistogram/HdrHistogram/maven-metadata.xml); [sketches-java](https://repo1.maven.org/maven2/com/datadoghq/sketches-java/maven-metadata.xml); [t-digest](https://repo1.maven.org/maven2/com/tdunning/t-digest/maven-metadata.xml); [micrometer-core](https://repo1.maven.org/maven2/io/micrometer/micrometer-core/maven-metadata.xml)

### Inferences
These are designs, not yet run. The expected values are predictions derived from the cited figures.

- **Lab 1, "The lying load test" (percentiles and coordinated omission; pure Kotlin plus the JDK `HttpServer` or Ktor):**
  - Build a service with about 2 ms service time and a `/stall?ms=1400` admin endpoint that holds a global lock, simulating a GC pause.
  - Build two generators that record into HdrHistogram: (a) closed, 100 virtual threads looping send/receive and timing from the actual send; (b) open, a scheduler issuing 2,000 req/s and timing from the *intended* send.
  - Learners predict, then compare, mean, p50, p99, p99.9 and max.
  - Expected: the closed p99 barely moves, because only about 100 samples see the stall. The open p99 jumps to roughly 1 s, as in wrk2.
  - Extension 1: correct the closed data with `recordValueWithExpectedInterval` and show it approaches the open result.
  - Extension 2: run two "pods" (one healthy, one with 2% slow requests). Compute the average of the per-pod p99s versus the p99 of the merged histograms, and see that the two disagree. Repeat with DDSketch and t-digest to compare relative error at p99.9.
- **Lab 2, "The hockey stick" (queueing, Little's law; pure Kotlin):**
  - One worker thread, exponential service times with a 10 ms mean, Poisson arrivals. Sweep ρ = 0.5, 0.7, 0.8, 0.9, 0.95.
  - Measure mean and p99 response time, and sample the queue length.
  - Assert the mean is within about 10% of S/(1−ρ) (20, 33, 50, 100, 200 ms), and that queue length ≈ λ × W (Little's law).
  - Extension: set service time to a constant to see that variance, not only the mean, drives queueing. Then add a second worker (M/M/2) to show pooling.
- **Lab 3, "Fan-out makes the tail the common case" (coroutines simulation):**
  - Each leaf takes 10 ms with probability 0.99 and 1 s with probability 0.01, implemented with `delay`. The root awaits N leaves with `awaitAll`.
  - Sweep N = 1, 10, 100, 1,000 and plot P(root > 1 s) against 1 − 0.99^N (expect about 63% at N = 100).
  - Then hedge each leaf at its p95 using `select` and cancel the loser. Measure root p99/p99.9 and the extra-request percentage, targeting single-digit percent, as in the paper's 2%.
  - Break it: make the slowness *correlated* (one shared "GC pause" stalls all replicas at once) and show that hedging stops helping, matching the paper's caveat.
- **Lab 4, "Timelines: push, pull, hybrid, lossy" (Testcontainers PostgreSQL 18 + Redis 8):**
  - Generate a Zipf-distributed follow graph: 100K users, mean follows about 200, a few accounts with 50K+ followers, and a few users following 20K+ accounts.
  - Implement four strategies:
    - (a) pull, using DDIA's SQL join with `LIMIT 1000`;
    - (b) push into Redis lists capped at 800 (`LPUSH` + `LTRIM`, pipelined in batches);
    - (c) hybrid, skipping fan-out above a follower threshold and merging those accounts at read time;
    - (d) Bluesky's lossy rule for heavy followers.
  - Measure timeline-read p50/p99, writes per post, time to deliver a celebrity post to all followers, and Redis memory.
  - Predictions: push wins reads by orders of magnitude, celebrity delivery time grows linearly with followers, and the hybrid caps it.
  - Have learners find the follower threshold where (c) beats (b) on total work.
- **Lab 5, "Retry storm" (metastability; pure Kotlin simulation):**
  - A server with fixed capacity and a queue. Clients time out at 200 ms and retry immediately up to 3 times.
  - Inject a 10 s capacity drop. Show that goodput stays near zero after capacity returns, which is the metastable state.
  - Add exponential backoff with full jitter, a retry budget (token bucket) and server-side load shedding. Show that recovery happens within seconds.
- **Lab 6, "Green health check, broken service" (gray failure):** the service has a separate heartbeat thread that keeps answering `/health` while a deadlocked worker pool times out every real request. A simple round-robin load balancer, written in Kotlin, keeps routing to it. Fix it by deriving health from the request path's own outcomes (latency-induced probation) and measure the error rate before and after.
- **Lab 7, "Error budget calculator and burn-rate alerts" (pure Kotlin):** replay synthetic error streams (a total outage, a 2% elevation, a slow 0.2% leak) against 99.9%/30-day budgets. Learners implement the multiwindow, multi-burn-rate rules and check detection and reset times against the Workbook's numbers (for example, 2% budget in 1 h at 14.4x).
- **Lab 8, "COST" (pure Kotlin):** on a graph that fits in RAM (synthetic or a public SNAP dataset; the download needs learner approval), implement label propagation, union-find and Hilbert-ordered PageRank on a single thread. Optionally compare with Spark `local[*]` from the earlier round's stack. Ask learners to compute their system's COST.
- **Common harness:** each lab ends in a JUnit 6 assertion on the measured number, for example `assertTrue(openP99 > 50 * closedP99)` or `assertEquals(0.63, pSlow, 0.03)`, following the earlier round's predict-run-break pattern. — [earlier report][prev]

### Gaps
- None of these labs has been run. Timings on Apple Silicon under Docker Desktop or OrbStack (timer resolution, virtual-thread scheduling noise in the 1–2 ms range) could blur Lab 1's quiet-run numbers. wrk2 itself warns of about ±1 ms accuracy. — [wrk2 README](https://github.com/giltene/wrk2)
- Kotlin- or JVM-native open-model load generators (Gatling's open injection profiles, or a hand-rolled scheduler on virtual threads) were not evaluated for accuracy. k6 and wrk2 are the referenced tools, and neither is JVM-based.
- No dataset licence check was done for the SNAP graphs or for the Zipf parameters that best match real follower distributions.

[ddia]: file:///Users/arunav/Documents/learn/books%20%26%20pdfs/architecture%20and%20software%20design/Designing%20Data-Intensive%20Applications%20The%20Big%20Ideas%20Behind%20Reliable%2C%20Scalable%2C%20and%20Maintainable%20Systems%20%28Martin%20Kleppmann%2C%20Chris%20Riccomini%29.pdf
[prev]: file:///Users/arunav/Library/Application%20Support/Claude/scratch-workspaces/433d709e-8728-4258-b10c-98909f71fe68/5c806f8d-0769-4e35-ac24-a3ea18081c67/scratch-2026-11-07-647cf0/reports/Systems%20course%20curriculum%20research.md
