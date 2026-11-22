# A new board without repainting: Iceberg's tree of files

- Slug / scene: `iceberg-snapshots`, `videos/scenes/iceberg_snapshots.py:IcebergSnapshots`
- Lesson: `batch-11`, section 1, "Inside the list: a tree of files that are never edited"
- Audience / level: a complete newcomer. Knows a table can be a folder of files; nothing about Iceberg.
- Length: about 4.5 min (~740 words)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the full tree after the third append (pointer 4, v4, three snapshots sharing manifests)
- The learner's real question: if every change writes a new list and old versions are kept, isn't that a mountain
  of copies? And how does a reader find the right files without looking in the folder?
- Misconception to steelman and break: "the folder is the table". Broken at the end: a file copied in by hand is
  invisible, a file deleted by hand breaks every snapshot that lists it.
- Concept chain: change by writing new files and moving one pointer (section 0, recalled) → one big list is too
  costly to rewrite → split it into a tree, rewrite only the top → snapshots share what didn't change → readers walk
  the tree and skip by statistics → the snapshot is the table (hardest last)
- Analogy family: the lesson's café menu board. A board hung in one move (a snapshot), the nail it hangs on (the
  pointer), price cards (data files). Panels of cards (manifests) are an extension of the lesson's picture, made so
  that the tree's sharing can be acted out.
- Open loops: "a mountain of copies?" planted in scene 2 → paid off in scene 6
- Assumptions: numbers are the lesson's demo (create + three appends of 1,000 payments, three days each: v1 to v4,
  three manifest lists, three manifests, nine data files; the newest manifest's amounts 149 to 250,067 cents).

## The one picture

Left to right, one column per level: the pointer (yellow), the table metadata file (white), the manifest lists (one
per snapshot, S1 blue, S2 teal, S3 gold), the manifests (M1, M2, M3 in the colour of the append that wrote them), and
the data files (three small squares per manifest). Thin lines show which list names which manifest. Notes on the
right, counts below, caption at the bottom.

## Scene 1 · The half-changed menu · [QUESTION] [FAMILIAR] [ANALOGY]

VO: Picture a café changing its menu. The owner swaps the price cards on the wall one at a time. A customer who reads
the wall halfway through sees new prices for coffee and old ones for cake, a menu that never existed. A table kept as
a folder of files has the same problem. A job adding 200 files drops them in one by one, and a report that reads the
folder halfway counts part of the job. A careful owner fills a new board in the back room, and hangs it in one move.
A table can do that too. Write every new file first, then a new list of the table's files, then move one pointer to
the new list. A reader sees the old table or the new one, never a mix.

SCREEN: A menu board with six cards; three turn gold, three stay grey; "a menu that never existed". Then a new gold
board slides in whole over the old one, onto a nail labelled "pointer".

## Scene 2 · One big list · [PAIN] [WISH] [LOOP-PLANT]

VO: But here's the catch. If the list is one file, every change rewrites all of it. A table of a million files gets
a new million-line list, for a change that adds ten. That's repainting the whole board to change one price. And if
we keep the old versions too, isn't that a mountain of copies? What we want is to rewrite only what changed. Hold that
question.

SCREEN: A long list strip "1,000,000 lines" rewritten for "+10 files"; caption "rewrite only what changed?".

## Scene 3 · Panels · [ANALOGY] [NAME:Iceberg]

VO: Apache Iceberg is a set of free rules and code for tables made of plain files. Its trick is to build the board
from panels. A new board reuses the old panels as they are, and adds one new panel for the new cards.

## Scene 4 · The tree, from the top · [SHOW] [NAME] [MAP]

VO: Here's a table after two appends. From the top. The pointer says which version is current. Here, it's a tiny
file that says 3. It points to the table metadata file. Metadata means data about the data. This file holds the
columns, the rule for grouping files by day, and the list of the table's versions, called snapshots. One of them is
current. Each snapshot has a manifest list: one row per manifest, with the range of days inside it. Each manifest has
one row per data file: where it is, its day, its row count, and the smallest and largest value of every column. And
at the bottom, the data files: plain Parquet, a common file format for tables. In café terms, a snapshot is a whole
board, a manifest is a panel, and the data files are the price cards.

SCREEN: Columns appear left to right with headers; S2's list names M1 and M2; S1's names M1.

## Scene 5 · Predict the third append · [PREDICT] [PAUSE]

VO: In the lesson's demo, the table was created, then got three appends of 1,000 payments, three days each. Now the
third append. When it's done, how many metadata files will there be? And how many manifests will the new snapshot
name? Pause and guess.

## Scene 6 · The commit · [SHOW] [LOOP-PAYOFF]

VO: Watch. It writes three data files, and nobody reads them yet. Then one new manifest that lists them. Then one new
manifest list, naming the new manifest plus the two old ones. Then one new metadata file, version 4. And last, one
move of the pointer, from 3 to 4. So four metadata files: one for creating the table, one per append. And the new
snapshot names all three manifests. Two of them are reused, not copied. That's why snapshots are cheap. Two snapshots
share every manifest that didn't change. Here the café picture breaks, in a useful place. A café throws its old board
away. Iceberg keeps the old snapshots, and they share most of their cards with the new one.

SCREEN: Files, M3, S3's list, v4, then the pointer 3 → 4; counts "metadata files: 4, manifest lists: 3, manifests: 3,
data files: 9"; the lines from S3 to M1 and M2 glow ("reused").

## Scene 7 · A reader walks down · [SHOW]

VO: A reader walks the tree from the top: the pointer, the metadata, the current snapshot, and its manifest list.
Then it opens only the manifests whose days can match, and only the files whose smallest and largest values can
match. In the newest manifest, amounts run from 149 to 250,067 cents. Ask for amounts above that, and all three of its
files are skipped without opening one. And notice: the reader never lists the folder.

## Scene 8 · The folder is not the table · [BREAK] [GUARDRAIL] [JOKE:is-the-explanation]

VO: That cuts both ways. Copy a file into the folder by hand, and no reader ever sees it. It's a card pinned to the
wall behind the board. Delete a file by hand, and every snapshot that lists it breaks. The snapshot is the table, not
the folder. Change the table through Iceberg.

## Scene 9 · Moral and check · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So the moral of the story. Files are written once and never edited. The tree reuses everything below what
changed. And one pointer move makes a new version appear whole. One quick check. Someone deletes, by hand, a data file
that the first append wrote. Which snapshots break? Pause and think. (three seconds) All three. Manifest 1 is shared
by every snapshot, so every board loses that card.

---

### Beat check

- QUESTION + FAMILIAR + ANALOGY (1) → PAIN + WISH (2) → NAME Iceberg, panels (3) → SHOW, NAME, MAP the tree (4) →
  PREDICT + PAUSE (5) → SHOW the commit, LOOP-PAYOFF, the analogy's break (6) → SHOW the reader (7) → BREAK the
  folder model, GUARDRAIL (8) → MORAL, check (9).
- Light moments: repainting the whole board (2), the card pinned behind the board (8), every board loses that card (9).

### Accuracy notes for the producer

- Demo (lesson): `v1.metadata.json` to `v4.metadata.json`, `version-hint.text` says 4 (the Hadoop catalog's pointer),
  three `snap-*.avro` manifest lists, three `*-m0.avro` manifests, the current list names three manifests (newest
  first), each manifest lists three files (one per day, 333 or 334 rows), amounts in the newest manifest 149 to 250,067.
- The metadata file also holds settings, schema field ids and snapshot summaries; the video names columns, the
  partition rule and the snapshots.
- In the demo every append covers all three days, so no manifest could be skipped by day; the video says only that
  manifests "whose days can match" are opened.
- Manifests and manifest lists are Avro files; the video doesn't name Avro. Panels are the video's extension of the
  lesson's board picture.
- The `.snapshots`, `.manifests`, `.files` and `.history` metadata tables are left to the lesson.
