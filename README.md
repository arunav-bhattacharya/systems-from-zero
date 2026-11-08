# Systems from Zero

A 158-lesson course on the systems under a backend service, organized by concept rather than by product. It starts with what we ask of a data system and the network and operating system underneath, then works up from one machine (data models, SQL, storage engines, caches, encodings) to many (replication, partitioning, transactions, faults and clocks, consensus) and to data in motion (logs, streams, batch, derived data and the ethics of it). Products such as PostgreSQL, Cassandra, DynamoDB, MongoDB, Redis, Kafka, Spark and Iceberg appear inside the concept they illustrate, with a few lessons that take one system apart end to end. One lesson a day, about 40 minutes each, with a lab you run on your laptop and tests that tell you when it works.

| # | Part | Track | Lessons | Lab modules |
|---|---|---|---|---|
| 1 | Foundations | What data systems are for | 6 | `sim` |
| 2 | Foundations | Computer networking | 12 | `net` |
| 3 | Foundations | Operating systems | 12 | `os` |
| 4 | Data on one machine | The relational model and SQL | 10 | `sql` |
| 5 | Data on one machine | Data models beyond tables | 9 | `nosql`, `sql` |
| 6 | Data on one machine | Storage engines and query execution | 14 | `internals`, `sql`, `nosql` |
| 7 | Data on one machine | Caching and in-memory data | 10 | `redis` |
| 8 | Data on one machine | Encoding, APIs and workflows | 5 | `flow` |
| 9 | Data across machines | Replication | 8 | `sim`, `sql`, `nosql` |
| 10 | Data across machines | Partitioning | 9 | `sim`, `nosql` |
| 11 | Data across machines | Transactions | 8 | `sql`, `internals`, `redis`, `nosql` |
| 12 | Data across machines | Faults, time and truth | 8 | `sim`, `redis` |
| 13 | Data across machines | Consistency and consensus | 6 | `sim`, `internals` |
| 14 | Moving and deriving data | Messaging and logs | 12 | `kafka`, `redis` |
| 15 | Moving and deriving data | Stream processing | 8 | `sql`, `kafka`, `sim`, `bigdata` |
| 16 | Moving and deriving data | Batch processing and analytics | 15 | `bigdata`, `sim` |
| 17 | Moving and deriving data | Derived data and doing right | 6 | `sim` |

Each lesson has a warm-up question to answer before reading, 3 to 5 short sections that each end in a "Try it" you run on your own machine, at least one interactive diagram (a step-through of the mechanism, or a scheduler you drive by hand), a worked example, a lab with tests, a from-memory drill, and a 5-question quiz. One quiz question always comes from an earlier lesson.

The site also has:

- **Narrated animations**: 23 short videos (2560x1440, about two minutes each) on the hardest mechanisms, from the TCP handshake and page faults to B+tree splits, consumer rebalancing, Cassandra gossip, MongoDB sharding, PostgreSQL failover and Iceberg snapshots. Each sits at the top of the section it explains, with captions.
- **Review**: spaced-repetition flashcards (FSRS-4.5 scheduler). Each finished lesson adds 5 to 7 cards, and every quiz question you miss joins them.
- **Mixed practice**: quiz questions drawn from all finished lessons.
- **Plan**: lessons laid out as Week N, Day N at 3 to 7 study days a week, and copy/paste sync between devices.
- **Cheat sheets** and a **glossary**.
- A **40-minute focus timer**: 10 minutes review, 15 learning, 15 practice.

There is no sign-in. Progress is saved in the browser (`localStorage`); to move it between devices, use "Copy my progress" and "Import" on the Plan page.

## Do the labs

You need JDK 25 (plus JDK 21 for the big data labs, which run Spark 4.1) and Docker.

```bash
cd labs
./gradlew :os:solutionTest                                  # proves the setup works (no Docker needed)
./gradlew :sql:test --tests 'sfz.sql.l03.*'                 # lesson sql-03's lab, against your code
./gradlew :kafka:solutionTest --tests 'sfz.msg.l07.*'     # the same tests against the reference answers
docker compose -f env/labbox.yml run --rm box               # a Linux shell with strace, tcpdump, ss, tc, dig
docker compose -f env/postgres.yml up -d                    # Postgres 18 for the SQL Try-its
```

Each lab module is one toolchain (`sim` is plain-Kotlin simulations, `flow` is encodings, gRPC and Temporal, the others are named for what they run), and a lesson's code lives in package `sfz.<track>.l<NN>` of the module it needs. Every module has `src/main` (exercises), `src/test` (the tests), `src/demo` (Try-it programs) and `src/solution` (reference answers with the same names). `test` runs the tests against your code; `solutionTest` runs the same tests against the answers. Labs that need a real Postgres, Kafka, Redis, MongoDB or Cassandra start it with Testcontainers. `labs/env/` holds the Compose files the Try-it steps use.

## Build the site

```bash
pip install markdown pygments
python3 site/validate.py --all    # checks every lesson against the writing brief
python3 site/build.py             # writes web/index.html and web/lessons/*.json
```

`web/` is committed, so deploying needs no build step.

## Deploy to Cloudflare

Step-by-step instructions are in [DEPLOY.md](DEPLOY.md). In short, the site is a Cloudflare Worker that serves `web/` as static assets (`wrangler.jsonc`); a small script, `site/worker.js`, runs only for `/video/*` to answer the byte-range requests video players send (Safari needs them to play MP4). Either connect this repo in the Cloudflare dashboard with deploy command `npx wrangler deploy`, add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` as repository secrets so the `ci` workflow deploys after the checks pass, or run `npx wrangler deploy` from the repo root.

## What is in this repo

| Folder | What it holds |
|---|---|
| `content/course.json` | Parts, tracks, lesson order and redirects from the old lesson ids |
| `content/lessons/` | One JSON file per lesson |
| `content/tracks/` | Track intro, cheat sheet, recap and track quiz |
| `labs/` | The Gradle project with every exercise, test, demo and solution, plus `env/` Compose files and the lab box image |
| `site/` | `build.py`, `validate.py`, `app.js`, `style.css` |
| `web/` | The built site that Cloudflare serves |
| `videos/` | Manim scenes, the narration kit (Kokoro voice) and the render and audio-check scripts; see `videos/README.md` |
| `content/videos.json` | Which video sits in which lesson section |
| `brief/` | The writing brief every lesson follows, the concept-rewrite addendum and the concept map (where each lesson came from) |
| `research_notes/`, `reports/` | Fact-checked research behind the lessons (versions as of November 2026) |

All company names, people and numbers in examples are made up.
