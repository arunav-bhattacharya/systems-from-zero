# The concept rewrite: read this after BRIEF.md

`BRIEF.md` still holds: the learner, first principles, voice, accuracy, the lesson schema, diagrams,
steppers, sims, labs, the lab box and the checks. This file says what changed when the course moved
from product tracks (SQL, NoSQL, Kafka, Redis...) to concept tracks. Where the two disagree, this
file wins.

## What changed

- The course now has 4 parts, 17 tracks and 158 lessons. `content/course.json` is the source of truth
  for every id, title and the order. `brief/CONCEPT_MAP.md` lists each lesson with the old lesson it
  was built from (or `NEW`) and the lab module it uses.
- 105 lessons moved from the product tracks. Their files are already in place under their new ids:
  ids, titles, lab folders, package names, `lab.run` commands and lesson-id references were rewritten
  by script. The prose was not. Old copies are in `build/migrate-backup/lessons/<old id>.json`.
- 53 lessons are new.

| Part | Tracks (id: title) |
|---|---|
| I. Foundations | found: What data systems are for · net: Computer networking · os: Operating systems |
| II. Data on one machine | sql: The relational model and SQL · model: Data models beyond tables · store: Storage engines and query execution · cache: Caching and in-memory data · enc: Encoding, APIs and workflows |
| III. Data across machines | repl: Replication · shard: Partitioning · txn: Transactions · dist: Faults, time and truth · cons: Consistency and consensus |
| IV. Moving and deriving data | msg: Messaging and logs · stream: Stream processing · batch: Batch processing and analytics · derive: Derived data and doing right |

## The teaching shape: the concept first, products as the worked examples

Every lesson teaches one concept from first principles (the rules in `BRIEF.md`): the problem, the
simplest thing that could work, where it breaks with a real number, the next version. Products come in
as the concrete answer to a question the concept raised: "so how does PostgreSQL do it, and why does
Cassandra do the opposite?" Where a concept applies to more than one real system, compare at least
two, with the versions current in November 2026 (the research notes have them). A lesson is never a
product tour, and a product section never stands without the question it answers.

Case-study lessons ("Inside a Cassandra cluster", "Running PostgreSQL", "DynamoDB under the hood")
open by naming the concepts they put together, and point to the lessons that taught each one.

## Sources

- This round's research: `research_notes/Concept curriculum for data systems/*.md` and the synthesis
  `reports/Concept curriculum for data systems.md`. Read the notes for your area before you write.
  The earlier product notes in `research_notes/Systems course curriculum research/` still hold for
  product details.
- *Designing Data-Intensive Applications*, 2nd edition (Kleppmann and Riccomini), is one source among
  many. The PDF is at
  `/Users/arunav/Documents/learn/books & pdfs/architecture and software design/Designing Data-Intensive Applications The Big Ideas Behind Reliable, Scalable, and Maintainable Systems (Martin Kleppmann, Chris Riccomini).pdf`
  and its outline with PDF page numbers is in
  `/private/tmp/claude-501/-Users-arunav-Library-Application-Support-Claude-scratch-workspaces-433d709e-8728-4258-b10c-98909f71fe68-5c806f8d-0769-4e35-ac24-a3ea18081c67-scratch-2026-11-07-647cf0/9899906b-a1e7-4ac7-ab32-bdd63a66df04/scratchpad/ddia/outline.txt`.
  Read pages with `pypdf` if you want the book's framing. Rules: never the only source for a lesson;
  never copy its wording, examples, figures or chapter structure; paraphrase; at most one quote per
  lesson and under 15 words. Cite it in `sources` or `deeper` as "Designing Data-Intensive
  Applications, 2nd edition, chapter N" with `https://dataintensive.net/`. Prefer the primary
  sources it cites (papers, docs, post-mortems) and the research notes' verified URLs.

## Cross-references

- Lesson numbers changed in the move. Every "lesson N", "the X track", "earlier in this track" and
  "next lesson" in a moved lesson must be checked against `course.json`, in the prose, `in_your_world`,
  `mistake`, `deeper`, quiz, flashcards, `explain_back`, lab steps and hints.
- Refer to a lesson in another track by track title and topic ("the Replication track's lesson on
  lag"), and within a track by number ("lesson 3").
- A lesson may build only on lessons that come before it in course order. For anything later, write a
  forward pointer ("the Consensus track builds this properly") and explain what this lesson needs in
  place.
- Quiz `from` must be an earlier lesson in course order; the validator checks it.
- The old product track names (the NoSQL track, the Kafka track, the database internals track, the
  Redis track, the big data track) no longer exist. Replace every mention.

## Moved lessons: the reframe pass

1. Open the moved lesson at its new id. Read its neighbours in the new track (the lesson before and
   after, from the map) so the transitions work.
2. Reframe it for the new track. The goal, the warm-up and the opening of the first section say which
   concept this lesson teaches and how it follows the lesson before it in this track. Product-only
   claims become the concept plus the product as the example.
3. Add the missing pieces listed in your assignment. Stay within 1,200 to 2,800 words of section
   prose; trim elsewhere if you add.
4. Keep the lab, figures, steppers and sims unless the assignment says otherwise. Lessons with a video
   keep that section's topic and position: batch-03§1, batch-11§1, cache-02§1, dist-05§3, msg-02§0,
   msg-04§0, msg-08§1, repl-04§0, repl-07§1, shard-02§0, shard-05§2, shard-06§2, shard-07§2, sql-03§3,
   store-04§2, store-05§1, txn-01§3, txn-04§0 (§ is the 0-based section index).
5. Fix every cross-reference and quiz `from`. Check any version or "as of" claim against the research
   notes.
6. Don't move or rename lab files. Fix lesson numbers in lab step text and in code comments of that
   lesson's lab files if they mention the old numbering.

## New lessons

- The full schema from `BRIEF.md`, held to the same bar as the best existing lesson in your track
  (read one first).
- The lab goes in package `sfz.<track>.l<NN>` of the module named in `CONCEPT_MAP.md`, with `main`,
  `solution` and `test` source sets (and `demo` if a Try it runs code). The tests must fail on the
  stubs and pass on the solutions. Modules:
  - `sim`: plain Kotlin simulations on a seeded, deterministic scheduler; no Docker. jqwik is available
    for property-based tests.
  - `flow`: protobuf-java 4.36.2 (CodedOutputStream, DynamicMessage, no code generation), Avro 1.12.2
    (GenericRecord), Jackson 2.23 with CBOR and MessagePack, gRPC 1.85.1 (in-process transport,
    hand-written method descriptors), Temporal SDK 1.40.0 with temporal-testing's in-process server,
    PostgreSQL JDBC with Testcontainers.
  - `sql`, `nosql`, `internals`, `kafka`, `redis`, `bigdata`, `net`, `os`: the libraries they already
    have.
- Don't edit any `build.gradle.kts`. If you need a library a module lacks, use a plainer approach or
  stop and say so in your report.
- Lessons in the `cache` and `msg` tracks, and lessons marked `"pairs": true` in `course.json`, show
  Java and Kotlin side by side (the `compare` block and paired fences in `BRIEF.md`).

## Track files

The writer named as track owner writes `content/tracks/<track>.json` (intro, cheat sheet, 6 to 10
recap bullets, 10 quiz questions) after its lessons, covering the whole track. Read the other
writer's lessons if they exist; otherwise work from the map and the notes. Existing track files for
`sql`, `store`, `model`, `cache`, `msg` and `batch` were carried over from the old tracks and must be
rewritten for the new lesson set.

## Check your work

- `python3 site/validate.py content/lessons/<id>.json`: 0 errors, and fix the warnings.
- From `labs/`: `./gradlew :<module>:test --tests 'sfz.<track>.l<NN>.*'` fails on the stubs and
  `./gradlew :<module>:solutionTest --tests 'sfz.<track>.l<NN>.*'` passes.
- Track owners: `python3 site/validate.py --track <track>`.
- Don't run `site/build.py`, don't commit, and don't edit files outside your assignment (other lessons,
  `site/`, `course.json`, build files). If a title in `course.json` should change, say so in your report.

## Your final report

Under 250 words: lessons written or reframed, the missing pieces you added, validator and test
results (tests failing on stubs, passing on solutions), and anything unverified or needing a decision.
