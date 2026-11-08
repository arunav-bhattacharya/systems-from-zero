# Systems from Zero

A 105-lesson course on the systems under a backend service: networks, operating systems, SQL databases, how a database works inside, NoSQL databases, Kafka, Redis and big data. One lesson a day, about 40 minutes each, with a lab you run on your laptop and tests that tell you when it works.

| # | Track | Lessons | Lab project |
|---|---|---|---|
| 1 | Computer networking | 12 | `labs/net` |
| 2 | Operating systems | 12 | `labs/os` |
| 3 | Relational databases and SQL (including running PostgreSQL: configuration, roles, replication, backups) | 16 | `labs/sql` |
| 4 | Database internals | 12 | `labs/internals` |
| 5 | NoSQL databases (then inside each store: Cassandra's ring and gossip, MongoDB sharding, DynamoDB, Neo4j, OpenSearch, and how to set each up) | 18 | `labs/nosql` |
| 6 | Kafka with Java and Kotlin | 12 | `labs/kafka` |
| 7 | Redis with Java and Kotlin | 11 | `labs/redis` |
| 8 | Big data: Spark and the lakehouse | 12 | `labs/bigdata` |

Each lesson has a warm-up question to answer before reading, 3 to 5 short sections that each end in a "Try it" you run on your own machine, at least one interactive diagram (a step-through of the mechanism, or a scheduler you drive by hand), a worked example, a lab with tests, a from-memory drill, and a 5-question quiz. One quiz question always comes from an earlier lesson of the same track.

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
./gradlew :kafka:solutionTest --tests 'sfz.kafka.l06.*'     # the same tests against the reference answers
docker compose -f env/labbox.yml run --rm box               # a Linux shell with strace, tcpdump, ss, tc, dig
docker compose -f env/postgres.yml up -d                    # Postgres 18 for the SQL Try-its
```

Every track module has `src/main` (exercises), `src/test` (the tests), `src/demo` (Try-it programs) and `src/solution` (reference answers with the same names). `test` runs the tests against your code; `solutionTest` runs the same tests against the answers. Labs that need a real Postgres, Kafka, Redis, MongoDB or Cassandra start it with Testcontainers. `labs/env/` holds the Compose files the Try-it steps use.

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
| `content/course.json` | Tracks and lesson order |
| `content/lessons/` | One JSON file per lesson |
| `content/tracks/` | Track intro, cheat sheet, recap and track quiz |
| `labs/` | The Gradle project with every exercise, test, demo and solution, plus `env/` Compose files and the lab box image |
| `site/` | `build.py`, `validate.py`, `app.js`, `style.css` |
| `web/` | The built site that Cloudflare serves |
| `videos/` | Manim scenes, the narration kit (Kokoro voice) and the render and audio-check scripts; see `videos/README.md` |
| `content/videos.json` | Which video sits in which lesson section |
| `brief/` | The writing brief every lesson follows |
| `research_notes/`, `reports/` | Fact-checked research behind the lessons (versions as of November 2026) |

All company names, people and numbers in examples are made up.
