# Book voice for Systems from Zero lessons (the newcomer rewrite)

Every lesson is being rewritten in the voice described by the **venkat-voice** skill, the way the sister
course JVM Workbench rewrote its first tracks. Read the skill first:

    /Users/arunav/Library/Application Support/Claude/local-agent-mode-sessions/433d709e-8728-4258-b10c-98909f71fe68/5c806f8d-0769-4e35-ac24-a3ea18081c67/rpm/plugin_01RBJ25sgvudUTwxgSg1gwLb/skills/venkat-voice/SKILL.md

(It may not load with the Skill tool; read the file.) This file says what is specific to this course: who the
reader is now, how the skill's moves map onto the lesson JSON, the house rules that win over the skill, and the
running examples. Where this file and `brief/BRIEF.md` or `brief/CONCEPTS.md` disagree, this file wins.

A finished example of the voice, from JVM Workbench, is at `brief/refs/jvm-workbench-conc-03.json`
(read `opening`, the first two sections and `closing`). Match its warmth and pace, not its topic.

## The reader is a complete newcomer

The old brief wrote for a senior backend engineer in payments. That reader is gone. Write for someone who can
read a little code (a loop, a function, a class) and knows nothing else: not networks, not operating systems,
not databases or SQL, not Kafka, Redis or any other product, not cloud tools, not servers, not any industry's
jargon. They have never run a service in production. They should be able to open any lesson, including one in
the middle of a track, and follow it from the first sentence.

- Openings and running examples use everyday situations everyone has lived: paying for coffee with a card, a
  queue at a counter, a library, a notebook, a group chat, a parcel in the post, a shop's till. Set each one up
  in plain words before it carries any weight.
- Every technical term is defined in one plain sentence the first time it appears in a lesson, even if an
  earlier lesson defined it. Prefer the picture first, then the name: show what the thing does, then say what
  it's called. A reminder of an earlier lesson names that lesson by title.
- A product is never assumed known. The first time a lesson names one, say in one plain sentence what it is
  ("PostgreSQL, a free database program that many companies run"; "Kafka, a program that keeps a log of
  messages and lets other programs read it"). Many tracks are about a product; that's fine, introduce it.
- No Quarkus, Temporal, Oracle, Kubernetes, pods, JPA, Hibernate, ORMs, microservices, "your services" or
  similar assumed context. A tool from the working world may appear late in a section as a short aside, once
  the idea is clear and only with a plain explanation ("Big companies split one program into many small ones
  that talk over the network; each one meets this problem.").
- No industry jargon in openings or running examples: settlement, reconciliation, acquirer, authorization
  hold, chargeback, outbox, SLA, p99 (until the lesson explains percentiles), on-call, pager. If the lesson's
  topic needs one, build it from the everyday picture first.
- Never write "as you know", "as usual", "obviously", "simply", "just" (in the sense of "this is easy") or
  "you've seen this in production".

## House rules that win over the skill

From the user and `brief/BRIEF.md`:

- Very simple English: average sentence about 15 words, rarely over 30, short paragraphs (three to five
  sentences). A reader whose first language isn't English should never read a sentence twice.
- No em dashes or en dashes anywhere (the validator rejects them). No banned words from `brief/BRIEF.md`.
- Facts correct for November 2026 (see "Accuracy rules" in `brief/BRIEF.md` and the research notes). Say the
  version when a fact depends on it. Never invent output: keep the output blocks and `expect` texts that came
  from real runs, or re-run them. Numbers that are made up for teaching are labelled as such.
- No invented biography: "I" for opinions, expectations and reactions only ("I'd expect about twice the
  speed"). For stories, put the reader or a plausible team in the scene.
- Humor: subtle and rare, at most one light touch per section, aimed at tools or situations, never at the
  reader, never inside the sentence that carries the key fact. Many sections have none.
- Kafka and Redis tracks (`msg`, `stream`, `cache`, and any lesson in `PAIR_LESSONS` of `site/validate.py`):
  every Java or Kotlin sample still comes as a pair, Java first, then Kotlin as a direct translation.

## What must not change (videos, quizzes and labs depend on it)

- Lesson `id`, `title`, the number and order of `sections` (videos are attached to sections by index), every
  quiz question's `from`, `lab.files`, `lab.run`, anything under `labs/`, sims (`sim`) and their `ops`.
- Steppers and figures: keep their structure and SVG. You may reword captions and step text (plain words), and
  fix an SVG label only if it uses jargon the prose no longer defines.
- Try-it `code`, commands and `file` paths stay; reword the steps and `expect` prose around them.
- Section headings may change wording (sentence case, name the step of the journey, and say plainly what the
  section covers so a reader scanning the contents sees the topic).

## Mapping the skill's moves onto the lesson JSON

- `opening` (new, 90 to 180 words): an everyday scene a newcomer understands, then the surprise or problem in
  it, the easy trap and why smart people fall into it, a one-sentence link to the previous lesson (skip it
  for the first lesson of the course), and the plan ("In this lesson, we'll..."). Its last line can lead into
  the warm-up: "Before we start, make a guess, and keep it in mind."
- `warmup`: same contract; word it in the same voice, with no jargon. Every option must make sense to a
  newcomer who has read only the opening.
- `sections` (keep the count): one idea each, problem first, the naive version failing in public, one running
  example that evolves version by version, honest numbers, at most one short bold rule, and a bridge sentence
  at the end that leads into the next section. Keep each section's existing substance: the mechanism, the
  real numbers, the commands. What changes is the order (picture before name), the definitions, the scene
  and the flow. Section prose in total: 1,400 to 2,700 words (the validator warns above 2,800).
- `aside` (new, optional, at most one per lesson): on a section, `{"title": "the reader's question", "body":
  "3 to 6 sentences"}`, for the question a careful newcomer asks at exactly that point.
- `analogy`, `in_your_world`, `mistake`: optional once `opening` exists. Weave the analogy into the prose
  where it helps (map every part out loud, say where it breaks). Drop `in_your_world` (it was titled "In your
  services" and assumed a working engineer). Keep `mistake` only if it adds something the prose doesn't, and
  rewrite it for a newcomer.
- `recap`: 4 to 6 bullets, one of them stating the limit of today's idea.
- `closing` (new, 60 to 120 words): look back at the opening scene in one or two sentences, give the reader
  one concrete thing to try or look for (a command to run, a setting to find, a question to ask of an app they
  use), then "Next, we'll..." and the question the next lesson answers. The last lesson of a track hands off to
  the next track.
- Try-it steps, worked example (`worked`), lab steps and hints, drill prompt, quiz questions and `why`,
  flashcards, terms, explain-back, deeper: same calm voice, no jargon, every term defined. Their contracts in
  `brief/BRIEF.md` are unchanged. Quiz `answer` indexes and option counts may change only if you rewrite the
  whole question.
- `goal`: one sentence a newcomer understands ("By the end, you can explain why...").

## Running examples

The course keeps one world so text, labs and videos tell one story, but it is now set up for a newcomer:

- **The coffee-shop payments app** (most data lessons). People pay for coffee, books and groceries with a
  card. A small company runs the program that records each payment: who paid (the card), which shop was paid
  (the labs call shops `merchants`; say "the shop" in prose and mention the table name once), how much, and
  when. It keeps a running balance for each account. Introduce this in plain words the first time a lesson
  uses it. The lab tables (`payments`, `merchants`, `cards`, `accounts`) stay as they are.
- Everyday pictures for mechanisms, set up fresh in each lesson that uses them: a parcel and its address
  labels (packets, routing), a phone call versus a postcard (TCP versus UDP), a library with a catalogue
  (indexes), a notebook you only ever append to (logs), a kitchen rail of order slips (queues), a group chat
  and its read receipts (consumers and offsets), photocopies of a notebook kept in other towns (replication),
  a shared whiteboard (shared state), a referee who decides (leader election).
- One analogy family per lesson. Map each part to the technical thing out loud ("the slip is the message, the
  rail is the queue"), and say where it breaks.

## How to work on a lesson

1. Read the current lesson, its research notes (`research_notes/Systems course curriculum research/`) and the
   previous lesson's `closing` (or its last section, if it has no closing yet), so the link is right.
2. Rewrite with a small Python script (`json.load`, edit, `json.dump(..., ensure_ascii=False, indent=2)`),
   matching the file's current format. Never hand-edit the JSON text.
3. `/usr/local/bin/python3 site/validate.py content/lessons/<id>.json` must give 0 errors. (Use that
   interpreter: it has markdown and pygments.)
4. Read the lesson from the top as the newcomer. Mark every place where they would guess, look something up,
   or meet a word nobody defined. Fix each one. Then run the skill's "Before you hand it in" checklist.
5. No git commands; the coordinator commits and deploys. Don't touch `videos/`, `web/`, `labs/` or
   `content/videos.json`.
