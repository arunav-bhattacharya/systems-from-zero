# Writing brief for Systems from Zero lessons

Read this whole file before you write a lesson. Then read the reference lesson from the sister
course, JVM Workbench, at
`/private/tmp/claude-501/-Users-arunav-Library-Application-Support-Claude-scratch-workspaces-433d709e-8728-4258-b10c-98909f71fe68-5c806f8d-0769-4e35-ac24-a3ea18081c67-scratch-2026-11-07-647cf0/9899906b-a1e7-4ac7-ab32-bdd63a66df04/scratchpad/refs/jvm-workbench/content/lessons/conc-03.json`
and its lab files under `.../refs/jvm-workbench/labs/concurrency/src/*/java/workbench/concurrency/l03/`.
Match its depth, tone and shape. This course uses the same lesson schema with a few additions
(listed under "What differs from JVM Workbench").

The repo root is the folder that holds this `brief/` folder. All paths below are relative to it.

## Research notes (read the ones for your track first)

Fact-checked notes for every track are in `research_notes/Systems course curriculum research/`
(`networking.md`, `operating_systems.md`, `rdbms_sql.md`, `nosql.md`, `database_internals.md`,
`kafka.md`, `redis.md`, `big_data.md`). Treat them as your source of truth for versions, API
shapes, misconceptions, lab ideas and verified URLs. Each file has a proposed lesson outline,
"Teaching notes" and "Verified URLs". Claims marked unverified in the notes need a check
(WebFetch or WebSearch on the primary source) before they go into a lesson. If the notes and your
memory disagree, trust the notes or check the primary source.

## Who the learner is

One person: a senior backend engineer. They write Kotlin and Java every day, on services built with
Quarkus, Temporal, Oracle and Kafka, mostly in payments. They use databases, Kafka and Redis as a
user of the client libraries. They do not yet have a deep, lasting model of what happens underneath:
packets and sockets, the kernel, query planners and storage engines, replication, partitions and
logs. This course builds that model from zero.

Write every lesson so that a reader who knows how to program but knows NOTHING about this topic can
start from scratch and leave with a detailed intuition. The senior-engineer profile tells you which
examples will land (payments, Kafka consumers, connection pools); it never licenses skipping a step.

They study about 40 focused minutes a day, one lesson per sitting:

1. about 10 minutes of flashcard review (the site does this),
2. about 15 minutes reading the sections and doing the small "Try it" steps,
3. about 15 minutes on the lab or drill, then the 5-question quiz.

So a lesson has about 1,200 to 2,200 words of section prose (not counting code), plus the
callouts, worked example, lab and quiz. Building from first principles takes a few more words than
listing facts; spend them on the "why" and the step-by-step build-up, not on breadth. If a topic is
still too big, cut breadth and move it to "Go deeper".

## First principles: teach it as if the reader is meeting it for the first time

This is the most important section of the brief. Every lesson and every section follows it.

1. Start from the problem, not the solution. Before you name a mechanism, show the need it answers:
   what would go wrong, or what would you have to do by hand, if it did not exist? "Two machines on
   the same wire only know each other's IP address, but the network card only sends to MAC
   addresses. How does the sender find the MAC?" Then the answer (ARP) feels inevitable.
2. Build it up in small steps. Begin with the simplest version that could work, show exactly where
   it breaks (with a concrete case and numbers), then add the next piece. Repeat until you reach the
   real design. A reader should be able to say "I could have invented this".
3. No term before its meaning. Define every term in plain words the first time it appears in a
   lesson, ideally with a concrete example before the general definition. Never rely on a term from
   another lesson without a one-line reminder and the lesson title ("the page cache, the kernel's
   in-memory copy of file data from lesson 9 of the OS track").
4. Concrete before abstract. Show one real packet, one row, one record, one command and its output,
   then generalise. Use real sizes and timings so the reader builds physical intuition (a page is 8
   KB, a disk seek is about 0.1 ms on SSD, a cross-region round trip is about 70 ms).
5. One mental model per lesson, stated early and reused. The first section sets up the picture (a
   diagram or stepper helps); later sections add to the same picture rather than starting new ones.
6. Why before how, how before configuration. Settings and API flags come last, once the reader
   knows what they control.
7. Check yourself against the cold reader. Before you finish, reread each section as someone who
   has never heard of the topic. Mark every place where they would have to guess, look something up,
   or accept a claim without seeing why. Fix each one with a sentence, an example or a frame in the
   stepper.

The first lesson of each track carries the most weight: it sets up the track's base model (what the
thing is, the problem it solves, the parts and how they talk) for a reader starting from nothing.

## Voice: blog mode, human, simple

Write like a strong engineer's personal blog post that teaches one idea well. Follow the
human-writing skill at
`/Users/arunav/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/5c806f8d-0769-4e35-ac24-a3ea18081c67/433d709e-8728-4258-b10c-98909f71fe68/skills/human-writing/SKILL.md`
(read it once, and use it in write mode). The parts that matter most here:

- Very simple English. Short sentences. One idea per sentence. A non-native reader should never
  have to read a sentence twice.
- Open each section with information: a claim, a failure, a number, a command and its output.
  Never open with scene-setting ("In today's world", "Have you ever wondered").
- Take positions. "Use keyset pagination here. OFFSET reads and throws away every skipped row."
  Say when something is just worse.
- Show, don't grade. Replace "this is crucial" with the thing that breaks.
- Name the actor: "the kernel copies the page on the first write", not "the page is copied".
- No em dashes or en dashes anywhere in prose. Use a period, comma, colon or parentheses.
  (The validator rejects them.)
- No "not X but Y" staging, no one-line dramatic closers, no "Let's dive in", no "Here's the
  thing", no "In conclusion", no forced triads.
- Avoid these words: delve, crucial, pivotal, robust (unless it is a technical term), leverage,
  seamless, tapestry, landscape, game-changer, unlock, empower, elevate, vibrant, meticulous,
  testament, foster, showcase, underscore, additionally, moreover, furthermore, enhance, valuable.
- Sentence case for every heading. No emojis. No bold labels at the start of list items. Bold at
  most one or two key phrases per section.
- Lists only when the content is a real list. Prose otherwise.
- Use "you". Contractions are fine.
- Never refer to the schedule with calendar dates or weekdays. Refer to other lessons by title or
  as "lesson N of this track".
- Concrete, made-up examples from the learner's world: payment authorizations, a ledger table,
  idempotency keys, a card-issuer API that takes 120 ms, a settlement batch, a Kafka consumer, a
  connection pool with 20 connections, a fraud check. All company names, people and numbers in
  examples are invented.

## Accuracy rules

- Facts must be right. When a claim depends on a version, say the version: "PostgreSQL 18 added
  asynchronous I/O (`io_method`)", "Kafka 4.0 removed ZooKeeper". Use the research notes. If you are
  not sure of a detail, check it with WebSearch or WebFetch on the primary source. If you still
  can't confirm it, write around it rather than guess.
- Current state (November 2026) the course assumes, from the research notes:
  - JDK 25 is the current LTS. Labs compile with `release 21` and run on JDK 21 or newer.
  - Linux: 6.18 is the newest long-term kernel; the scheduler is EEVDF (completed in 6.12, which
    also merged sched_ext); cgroup v2 is the default.
  - PostgreSQL 18 is the current major (19 is at release candidate). Link versioned docs pages
    (`https://www.postgresql.org/docs/18/...`), not `/docs/current/`.
  - MongoDB 9.0, Cassandra 5.0 (6.0 with Accord is alpha), Neo4j calendar versions (2026.x),
    DuckDB 2.0, Spark 4.3 is newest but the labs pin Spark 4.1 (Iceberg and Delta support it).
  - Kafka and Redis versions: see `kafka.md` and `redis.md`.
- Every URL in `refs` and `sources` must be a real page you are confident exists. Prefer URLs
  listed under "Verified URLs" in the notes. Fetch a URL if unsure. Never invent one. Fewer real
  links beats more fake ones.
- Never invent output. Every "What you should see" (`expect`) and every output block in prose
  comes from actually running the command in the lab box, a Compose service or a demo, or is
  clearly marked as abbreviated ("output trimmed"). Numbers that vary by machine say "about" and
  say what drives the variation.
- Code must compile and do what the prose says. Lab code is compiled and tested by Gradle.
  Code shown only in prose must still be correct.

## Languages

- Kafka and Redis tracks: every Java or Kotlin sample appears in BOTH languages, exactly as in
  JVM Workbench (a ```java fence immediately followed by the ```kotlin twin, `alt` on Try-it code
  and drill answers, `alt_code`/`alt_lang` on worked steps, a Java/Kotlin `compare` in every
  lesson; at most 3 `solo` samples per lesson). `site/validate.py` enforces this for those tracks.
- Every other track: write lab code and JVM samples in Kotlin by default, Java where it teaches the
  point better (NIO, `FileChannel`, `MappedByteBuffer`). Pairs are welcome but not required.
  Use the language the mechanism lives in: SQL for SQL, CQL, Cypher and MongoDB shell syntax for
  NoSQL, bash and real tool output for networking and OS, C only where the JVM hides the mechanism
  (fork, copy-on-write, malloc). Fence languages the site highlights: java, kotlin, sql, postgresql
  (psql sessions), c, python, bash, text, json, yaml, xml, properties, http, javascript (mongosh),
  cypher, ini, docker.
- `compare` (a side-by-side block) is optional outside Kafka and Redis. When you use it, use the
  generic shape (`a` and `b`, see the schema): Postgres vs Oracle, HTTP/1.1 vs HTTP/2 framing,
  blocking vs NIO server, a SQL query vs its MongoDB aggregation, row vs column layout. The learner
  works with Oracle, so a Postgres vs Oracle compare is welcome in the SQL track.

## What makes it stick (use these on purpose)

- Warm-up question: one prediction question before reading. Make the wrong options tempting.
- Try it boxes: 2 to 6 minute steps at the end of a section that make the mechanism visible on the
  laptop: a command in the lab box, a query against the Compose service, a demo in `src/demo`.
  Tell the learner what to change and what they should see. Prefer "predict, run, explain".
- One interactive visual per lesson at least: a `figure` (static SVG), a `sim` (the interleaving
  simulator: ideal for races, transactions and isolation anomalies), or a `stepper` (new, see
  below). Prefer a `stepper` wherever a mechanism unfolds over time: a TCP handshake, DNS
  resolution, a page fault, a B+tree split, a consumer group rebalance, a Raft election, an LSM
  compaction, a Spark shuffle. Most lessons should have one stepper and may also have a figure.
- The lab: build a small, testable model or client of the mechanism with real tests. This builds
  intuition by construction. Examples: a TCP state machine, a DNS message parser, a page
  replacement simulator, a slotted page, a B+tree, a consistent-hash ring, a quorum simulator, a
  Kafka consumer that survives a crash, a Redis rate limiter in Lua, a SQL query that the tests
  check against a seeded database.
- The drill: a short "write it from memory" task (3 to 6 minutes). Then the answer.
- Quiz: 5 questions that apply the idea to new cases, not recall of wording. One of the five must
  revisit an earlier lesson of the same track (`"from": "<that lesson id>"`); the first lesson of
  each track is exempt. Distractors come from real misconceptions, never tricks. The `why`
  explains the right answer and why the most tempting wrong option fails.
- Flashcards: 5 to 7 cards, one atomic fact or one "what happens if" each. Front is a question,
  back is one to three sentences or a tiny fragment.
- Explain it back: one prompt plus a model answer.
- Worked examples carry subgoal labels: short comments that name what each chunk does.

## Lesson JSON schema

One file per lesson: `content/lessons/<id>.json`. All prose fields are Markdown (inline code with
backticks, fenced code blocks with a language tag). Tables are allowed. Write the file with a small
Python script (json.dump, ensure_ascii=False, indent=2) rather than by hand.

```json
{
  "id": "net-03",
  "title": "must equal the title in content/course.json",
  "minutes": 40,
  "goal": "By the end you can ... (one sentence)",
  "warmup": { "q": "...", "options": ["...", "...", "..."], "answer": 1, "why": "..." },
  "sections": [
    {
      "h": "Sentence-case heading that states the idea",
      "body": "Markdown, about 200 to 450 words",
      "figure": { "svg": "<svg ...>...</svg>", "caption": "One sentence." },
      "sim": { "...": "see Interleaving simulator" },
      "stepper": { "...": "see Stepper" },
      "try": {
        "title": "Short title",
        "minutes": 4,
        "steps": ["Markdown step", "..."],
        "code": { "lang": "bash", "title": "in the lab box", "src": "commands or full source", "run": "optional command", "file": "optional labs/<lab>/src/demo/... path" },
        "expect": "What they should see (real output, trimmed if long), and why"
      },
      "refs": [ { "title": "...", "url": "https://...", "kind": "docs|read|watch" } ]
    }
  ],
  "analogy": "One paragraph. End by saying where the analogy breaks.",
  "in_your_world": "One paragraph tying the idea to the learner's services (payments, Kafka, Quarkus, Temporal, Oracle).",
  "mistake": "The most common real mistake, why people make it, and the fix.",
  "compare": {
    "title": "...",
    "a": { "label": "HTTP/1.1", "lang": "text", "src": "...", "title": "optional box title" },
    "b": { "label": "HTTP/2", "lang": "text", "src": "..." },
    "note": "What really differs, in prose"
  },
  "worked": { "title": "...", "steps": [ { "say": "Markdown", "code": "...", "lang": "kotlin" } ] },
  "lab": {
    "title": "...",
    "minutes": 15,
    "needs": ["Docker"],
    "files": ["labs/net/src/main/kotlin/sfz/net/l03/HandshakeTracker.kt"],
    "run": "./gradlew :net:test --tests 'sfz.net.l03.*'",
    "steps": ["Markdown", "..."],
    "hints": ["Markdown", "..."],
    "done_when": "All tests in ... pass."
  },
  "drill": { "title": "...", "minutes": 5, "prompt": "Markdown", "answer": { "lang": "kotlin", "src": "..." } },
  "recap": ["4 to 6 short Markdown bullets"],
  "quiz": [ { "q": "...", "options": ["...", "...", "...", "..."], "answer": 0, "why": "...", "from": "optional earlier lesson id" } ],
  "flashcards": [ { "front": "...", "back": "..." } ],
  "terms": [ { "term": "...", "plain": "..." } ],
  "explain_back": { "prompt": "...", "answer": "..." },
  "deeper": { "minutes": 10, "body": "Markdown: optional extra depth for curious days" },
  "sources": [ { "title": "...", "url": "https://..." } ]
}
```

Kafka and Redis lessons use the Java/Kotlin `compare` shape instead of `a`/`b`:
`"compare": { "title", "java": { "title", "src" }, "kotlin": { "title", "src" }, "note" }`.

Counts: 3 to 5 sections (each with a `try`, except at most one), at least 1 figure, sim or stepper
per lesson, 4 to 6 recap bullets, exactly 5 quiz questions with 4 options each (3 is fine when a
4th would be silly), 5 to 7 flashcards, 4 to 8 terms, 2 to 6 worked steps, 2 to 5 sources.
`lab.needs` is a list drawn from `"Docker"`, `"the lab box"`, `"JDK 21"`; leave it empty or out
when the lab needs only the JDK. Vary the correct answer index across quiz questions.

Escape carefully: newlines in code are `\n` and quotes are `\"` in JSON. Use 4-space indentation
in Java and Kotlin code.

## Diagrams (SVG), used by `figure` and by every `stepper` frame

Figures render on a black stage in both themes. Rules:

- `viewBox="0 0 W H"` with W between 520 and 720. No width/height attributes.
- Never set colors inline. Use only these classes:
  - boxes: `box` (neutral), `box-a` (accent blue), `box-b` (second accent yellow), `box-ok` (green), `box-bad` (red), `box-dim` (faded)
  - text: `t` (normal 14px), `t-s` (small 12px), `t-m` (muted), `t-a` (accent colored), `t-b`, `t-ok`, `t-bad`, `t-code` (monospace)
  - lines: `ln` (solid), `ln-d` (dashed), `ln-a` (accent solid), `ln-bad`
  - arrows: add `marker-end="url(#arr)"` to a line or path, and define the marker in the SVG:
    `<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="ln"/></marker></defs>`
    (the path uses a class, never a fill attribute).
- Text uses `text-anchor="middle"` (or start for left-aligned labels) and fits inside its box with
  at least 14 px padding (about 7.5 px per character at 14px, 6.5 px at 12px). Keep labels short.
  Never let text overlap a line or another label; put an edge label on its own clear space.
- Add `role="img"` and an `aria-label` that says what the picture shows.
- Simple shapes only: rect (rx="8"), line, path, circle, text, marker. No filters, no gradients, no
  foreignObject, no scripts, no style attributes.

## Stepper (new): a mechanism, one frame at a time

A `stepper` sits in a section like a `figure`. The learner clicks Next and Back (or uses the arrow
keys) through 3 to 10 frames. Each frame is a complete SVG (same rules as figures) plus a short
Markdown caption that says what just happened and why. Keep every frame the same size and layout,
change only what moved, and highlight the change with `box-a`/`t-a` (or `box-bad` for a failure),
so the eye catches the difference between frames.

```json
"stepper": {
  "title": "The three-way handshake",
  "intro": "Optional one-line Markdown intro.",
  "frames": [
    { "svg": "<svg viewBox=\"0 0 640 260\" role=\"img\" aria-label=\"...\">...</svg>", "say": "The client sends **SYN** with a random initial sequence number, 1000. Its socket moves to SYN-SENT." },
    { "svg": "...", "say": "..." }
  ]
}
```

## Interleaving simulator (`sim`)

An interactive widget where the learner picks which thread (or transaction) runs its next step. It
shows shared variables, each thread's local registers and who holds each lock. Use it for races,
lost updates, write skew, check-then-act, lock ordering and deadlock. Name the threads `T1`, `T2`
(or `Tx A`, `Tx B` for transactions).

```json
"sim": {
  "title": "Two transactions withdraw from one account",
  "intro": "Pick which transaction runs next. Try to end with balance = 50.",
  "vars": { "balance": 100 },
  "locks": ["row"],
  "threads": [
    { "name": "Tx A", "steps": [
      { "op": "read", "var": "balance", "reg": "b", "code": "SELECT balance ... -- reads 100" },
      { "op": "add", "reg": "b", "n": -50, "code": "b = b - 50" },
      { "op": "write", "var": "balance", "reg": "b", "code": "UPDATE ... SET balance = :b" }
    ]},
    { "name": "Tx B", "steps": [ "..." ] }
  ],
  "goal": { "var": "balance", "eq": 50, "say": "Lost update: two withdrawals, one recorded." }
}
```

Ops: `read` (reg = var), `add` (reg += n), `write` (var = reg), `set` (var = n), `lock` (blocks
while another thread holds it), `unlock`, `check` (if var != eq the thread jumps to its end: use for
check-then-act), `note` (does nothing, shows `code`). Every step needs `code`. The widget detects
deadlock and shows `goal.say` when the goal state is reached.

## Labs (Gradle, in `labs/`)

One Gradle subproject per track: `net`, `os`, `sql`, `nosql`, `internals`, `kafka`, `redis`,
`bigdata`. Each has:

- `src/main/{kotlin,java,resources}`: the exercises. Stubs with the final signatures, KDoc/javadoc
  saying what to do, and bodies that throw `TODO("...")` in Kotlin or
  `UnsupportedOperationException("TODO: ...")` in Java. Where the lesson is "fix the bug", the stub
  is the buggy code. In the SQL track an exercise is a `.sql` file under
  `src/main/resources/sfz/sql/lNN/` holding a placeholder query the learner replaces.
- `src/solution/{kotlin,java,resources}`: reference answers with the same class names, packages,
  public signatures and resource paths. Comment the important lines.
- `src/test/{kotlin,java,resources}`: tests that fail on the stubs and pass on the solutions. The
  same tests run against both (`test` puts `main` on the classpath, `solutionTest` puts `solution`).
  Shared test helpers (a container singleton, a schema loader) go in `src/test/kotlin/sfz/<lab>/support/`.
- `src/demo/{kotlin,java,resources}`: small runnable programs for the Try-it steps.

Package per lesson: lesson `net-03` uses package `sfz.net.l03` (track lab name, then `l` and the
two-digit lesson number) in main, solution, test and demo (demos may add `.demo`). Lesson
`dbi-04` uses the `internals` lab, so its package is `sfz.internals.l04`; lesson `data-04` uses
`sfz.bigdata.l04`.

Rules for lab code:

- Public signatures and resource paths in `main` and `solution` must match exactly. No Kotlin
  `internal`.
- Tests are deterministic on the solution and fail reliably on the stub. Keep each test under 10
  seconds on the solution, plus container start-up. Use JUnit `@Timeout` for anything that could
  hang.
- Tests read like specs: backtick names in Kotlin or `@DisplayName` in Java.
- Real services in tests come from Testcontainers 2.x (artifacts are named
  `org.testcontainers:testcontainers-postgresql`, `-kafka`, `-mongodb`, `-cassandra`,
  `-junit-jupiter`; classes live in `org.testcontainers.postgresql.PostgreSQLContainer`,
  `org.testcontainers.kafka.KafkaContainer` and so on). Start one container per test JVM through a
  shared support object (lazy singleton), never one per test class. Pin image tags
  (`postgres:18`, `mongo:9.0`, `cassandra:5.0`, `redis:8.x`, `apache/kafka:4.x`; take exact tags
  from your research notes and check they pull).
- Labs that only model a mechanism (simulators, parsers, data structures) must not need Docker.
  Prefer them where they teach as well: they run in a second.
- Library versions live in the root `labs/build.gradle.kts` `versions` map. Your track's module
  `labs/<lab>/build.gradle.kts` declares its dependencies (read the `sql` module for the pattern).
  Only the agent named as owner of a module may edit its build file; anyone else lists the
  dependency they need in their final report. Never edit the root build, `settings.gradle.kts` or
  `gradle.properties`.
- Keep demos fast (under 10 seconds) and quiet.

Commands (run from `labs/`, for your own track only). The Docker CLI is not on PATH in this
environment, so first run `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"`
(Docker Desktop is running).

```bash
./gradlew :<lab>:solutionTest --console=plain            # must pass
./gradlew :<lab>:testClasses --console=plain             # stubs and tests must compile
./gradlew :<lab>:test --console=plain --continue         # should fail on the stubs (that is expected)
./gradlew :<lab>:demo -Pmain=sfz.<lab>.l03.demo.SomeDemoKt --console=plain
```

Other agents are building other lessons in the same Gradle build at the same time, so you may see
a short wait for a lock. That is normal. Never touch another lesson's packages or another track's
folders.

The lesson's `lab.run` uses the learner command, `./gradlew :<lab>:test --tests 'sfz.<lab>.lNN.*'`.
Try-it code that lives in `src/demo` sets `code.file` to its repo path and `code.run` to the demo
command (from the `labs` folder).

## The lab box and Compose services (`labs/env/`)

- The lab box is a Linux shell for the networking and OS tracks: Ubuntu 24.04 with JDK 25,
  strace, tcpdump, tshark, iproute2 (ip, ss, tc), dig, curl, nc, socat, openssl, gcc, python3,
  sysstat, stress-ng, fio, bpftrace. Start it from the `labs` folder with
  `docker compose -f env/labbox.yml run --rm box` (or `box-priv`, privileged and without seccomp,
  for unshare, io_uring and mounts). `labs/` is mounted at `/labs`. To run a command in it
  non-interactively while you write: `docker compose -f env/labbox.yml run --rm -T box bash -lc '...'`.
  Use it to capture the real output for your Try-its. If a tool is missing, say so in your report
  instead of editing the image.
- Services for Try-its live in `labs/env/<name>.yml` (one Compose file per service set, owned by
  one track: `postgres.yml` by sql, `kafka.yml` and `kafka-cluster.yml` by kafka, `redis.yml` and
  `redis-cluster.yml` by redis, `mongo.yml`, `cassandra.yml`, `neo4j.yml`, `dynamodb.yml` by
  nosql). Mount seed files from `labs/env/<name>/`. Set memory limits so a three-node cluster fits
  in 6 GB. Verify each file: `up -d`, run the Try-it, `down -v`. Tell the learner the exact start
  and stop commands in the Try-it steps (run from the `labs` folder).
- Every Compose file starts with a top-level `name: sfz-<file name>` (for example `name: sfz-postgres`),
  so its containers never share a project with another file. Never run `down --remove-orphans`.
- Docker etiquette: up to eight writers share one Docker VM with 8 GB of memory. Give every service a
  memory limit (`mem_limit`, or the database's own heap settings), keep test containers single-node
  unless the lesson is about clusters, bring clusters up only while you capture output, and run
  `down -v` as soon as you are done. If a container dies with exit 137 or fails to start because the
  VM is busy, wait a minute and retry rather than raising limits.
- Stop every container you start before you finish.

## Track file

One per track: `content/tracks/<track id>.json`, written by the agent that writes the track's last
lessons:

```json
{
  "id": "net",
  "intro": "Markdown, 2 or 3 short paragraphs: what you will be able to do at the end, what you need first, how the labs for this track work.",
  "cheatsheet": "Markdown: a one-page reference for the whole track (tables welcome). This is what the learner will come back to in six months.",
  "recap": ["6 to 10 bullets for the whole track"],
  "quiz": [ "10 MCQs across the whole track, same shape as lesson quiz items" ]
}
```

## Check your work

```bash
python3 site/validate.py content/lessons/net-03.json     # one lesson
python3 site/validate.py --track net                      # a whole track, including its track file
```

The validator checks the schema, counts, dashes and banned words, SVG classes, lab file paths and
quiz `from` ids. Fix every error. Read warnings and fix the ones that are real. Do not run
`site/build.py`, do not start the site, do not edit `content/course.json`, `site/` or `brief/`, and
do not commit. The coordinator owns those.

Before you finish a lesson, reread it once as the learner: does each section open with
information, does every claim hold up, does every Try it say what they should see (real output),
and could the learner do the lab in about 15 minutes?

## Your final report

Keep it short: files written (lessons with section word counts, lab files, env files), what you ran
and the result (solutionTest pass, test fails on stubs, Try-its executed), anything from the outline
you cut or moved, dependencies or tools you needed but could not add, and open questions.
