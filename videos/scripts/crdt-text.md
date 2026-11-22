# Name every character: how two people's typing merges with no one in charge

- Slug / scene: `crdt-text`, `videos/scenes/crdt_text.py:CrdtText`
- Lesson: `repl-06`, section 3, "A text CRDT names every character, and keeps the names"
- Audience / level: a complete newcomer. Has typed in a shared document; doesn't know OT, CRDTs, Lamport clocks or
  tombstones.
- Length: about 5 minutes (~800 words of narration, two pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: both sites showing `pay $40!` with every id under its letter
- The learner's real question: two people type into the same note at the same moment, with no server deciding.
  How do both copies end up the same, with both edits kept?
- Misconception to steelman and break: "an edit is a position": `insert '!' at 6` lands inside the 40 on the other
  site (`pay $4!0`). Then the analogy's own break: on paper you'd rub a letter out, but a delete has to keep the
  letter's name.
- Concept chain: positions shift under each other → name every character and insert after a name → ids from a
  counter plus a site (bigger means later) → both sites converge in any order → ties: bigger id first → deletes
  leave tombstones → the cost grows, and "agree" isn't "what anyone meant" (hardest last)
- Analogy family: a printed page with a small serial number under every letter; notes that say "put this after
  letter 4a".
- Open loops: "how, with no one in charge?" planted in scene 1 → answered in scene 5 and named in scene 8.
- Assumptions: the two edits, the ids and the cost figures are the lesson's (`pay 40`, `1a` to `6a`, `$` named `7a`
  after `4a`, `!` named `7b` after `6a`, `pay $40!`; 10,000 edits: 2,136 visible, 6,068 nodes, 3,932 tombstones, 17
  bytes per visible character; Automerge 2's 700 MB and Automerge 3's 1.3 MB). The second round (a deletes the 0
  while b types a 5 after it, `8b`) is made up for the picture, using the lesson's rules.

## The one picture

Two rows of letter tiles: site a (agent a's laptop, blue) on top, site b (agent b's, teal) below. Each tile has its
letter and, once names arrive, its id underneath. Edits travel between the rows as chips. Red marks a wrong result;
gold a new letter; grey with a cross a tombstone.

## Scene 1 · No one in charge · 0:00–0:20 · [QUESTION] [LOOP-PLANT]

VO: Two support agents are typing into the same note at the same moment. Each one's typing shows up at once on
their own laptop, and there's no server in the middle deciding who went first. At the end, both laptops must show
the same note, with both people's typing kept. How, with no one in charge?

SCREEN: Title card. Two rows "site a" and "site b", both `pay 40`. A "?".

## Scene 2 · Positions shift · 0:20–1:15 · [FAMILIAR] [PAIN] [BREAK] [JOKE:is-the-explanation] [WISH]

VO: Start with the simplest way to send an edit: insert a character at a position, counting from 0. Agent a types a
dollar sign before the 4: insert dollar at 4. Agent b types an exclamation mark at the end: insert it at 6. Each
sends the edit to the other. b's copy becomes pay $40!. a's copy becomes pay $4!0. Position 6 meant "after the 0" in
b's text. In a's text, it's in the middle of the 40. Same number, two different places. One fix moves the positions
before applying them, and it usually needs a server to agree the order. What if an edit never mentioned a position
at all?

SCREEN: Position numbers 0 to 5 under row a. Gold `$` slides into a at 4; gold `!` into b at the end. Chips
"insert '$' at 4" and "insert '!' at 6" cross. b: `pay $40!`; a: `pay $4!0`, red. Caption "positions shift under
each other".

## Scene 3 · A serial number under every letter · 1:15–1:50 · [ANALOGY] [MAP]

VO: Picture a printed page with a small serial number under every letter. Instead of "put this at position 5", each
person writes "put this after letter 4a". Anyone can apply the notes in any order, and get the same page. The serial
number is the character's id, and it never changes. The note is the edit.

SCREEN: Rows reset to `pay 40`; the position numbers fade; ids `1a` to `6a` appear under each letter. Caption
"put this after letter 4a"; the space tile glows.

## Scene 4 · Where the names come from · 1:50–2:25 · [NAME] [SHRINK]

VO: This is a CRDT, a conflict-free replicated data type: a data type whose copies can take edits apart, and still
merge to the same result. In the lesson's version, an id is a counter plus a site name. Site a typed pay 40, so its
letters are 1a to 6a. Each site's next counter is one more than the highest it has seen from anyone. So a letter
typed after another always has a bigger counter.

SCREEN: Caption "CRDT: copies that take edits apart, and merge to the same result". Under one id, "6 + a: counter +
site". Caption "next counter = 1 + the highest seen".

## Scene 5 · Predict the merge · 2:25–3:15 · [PREDICT] [PAUSE] [SHOW] [LOOP-PAYOFF]

VO: Now the same two edits, by name. a sends: insert dollar, named 7a, after 4a, the space. b sends: insert
exclamation mark, named 7b, after 6a, the 0. Neither mentions a position. What will each copy show? Pause and guess.

(three seconds)

Both say pay $40!. The dollar finds the space wherever the space has moved to, and the exclamation mark finds the 0.
Nobody had to be in charge. Each edit carries the name it hangs on.

SCREEN: `$ 7a` joins row a after the space, `! 7b` joins row b after the 0. Chips "'$' 7a after 4a" and "'!' 7b after
6a" cross. Countdown. Both rows become `pay $40!` with ids `1a 2a 3a 4a 7a 5a 6a 7b`; green ticks.

## Scene 6 · Ties, and the letter that stays · 3:15–4:05 · [BREAK] [NAME] [JOKE:is-the-explanation]

VO: Two more rules. When two inserts name the same letter, the bigger id goes first, on every site. And deletes. On
paper you'd rub the letter out. Here that breaks. Say a deletes the 0, while b types a 5 right after it, named 8b.
b's note says after 6a. If 6a were gone, b's 5 would have nowhere to go. So a delete only marks its letter as gone,
and keeps the name. That mark is called a tombstone. The letter is dead, but it still gets mail. Both sites end with
pay $45!.

SCREEN: Caption "same letter named twice: the bigger id goes first". On a, the 0 greys with a cross ("tombstone");
on b, `5 8b` goes in after `6a`, before `7b` (8b is bigger). Chips cross; both rows `pay $45!`, the 0 kept as a
grey tombstone.

## Scene 7 · What it costs, and what it promises · 4:05–4:55 · [GUARDRAIL] [JOKE:soften]

VO: The price is extra data, and it only grows. In the lesson's test, 10,000 random edits leave 2,136 letters you can
see, and 6,068 kept, one for every letter ever typed. That's 17 bytes of names and marks for each visible letter. A
plain string needs none. Real libraries carry more: in Automerge 2, a CRDT library, pasting a long novel took 700 MB
of memory. Automerge 3 takes 1.3 MB for the same paste. And one more limit. A CRDT promises that the copies agree,
not that the result is what anyone meant. Two agents who fix the same typo at once can end up with the fix typed
twice. Agreed, and wrong together.

SCREEN: The rows dim. A panel: "10,000 edits: 2,136 visible, 6,068 kept, 3,932 tombstones", "17 bytes per visible
letter (plain text: 0)", "Automerge 2: 700 MB; Automerge 3: 1.3 MB". Caption "the copies agree; that's not the same as
right", and an example: "both add the missing 0: pay 4 -> pay 400".

## Scene 8 · The moral, and a check · 4:55–5:30 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, how do two copies merge with no one in charge? Name every letter when it's typed. Insert after a name, never
at a position. Keep the names, even of deleted letters. One quick check. Site b receives: insert x, named 9a, after
8a. But b has never seen 8a. Should it apply the insert now? Pause and think.

(three seconds)

No. It waits until 8a arrives. An edit can only hang on a name the site already has.

SCREEN: Three captions for the recap. For the check, a chip "'x' 9a after 8a" waits beside row b; a dashed "8a?"
slot; countdown; caption "wait until 8a arrives".

---

### Beat check

- QUESTION (scene 1). FAMILIAR + PAIN + BREAK of positions, and the WISH (scene 2). ANALOGY + MAP (scene 3).
- NAME after the analogy (scene 4). PREDICT + PAUSE + SHOW (scene 5). The analogy's break on deletes, NAME tombstone
  (scene 6). GUARDRAIL (scene 7). MORAL and a check (scene 8). Light moments: "same number, two different places"
  (0:55), "it still gets mail" (3:55), "agreed, and wrong together" (4:50).

### Accuracy notes for the producer

- The second round (a deletes `6a` while b inserts `5` named `8b` after `6a`) isn't in the lesson's lab. It follows
  the lesson's rules: the next counter after seeing `7b` is 8, the bigger id goes first among inserts after the same
  character, and a delete leaves a tombstone.
- OT is named only as "one fix moves the positions"; the lesson's previous section covers it and Google Docs.
- The lesson's figures for the cost come from its `RgaDemo.kt` (6 bytes per node); real libraries keep more.
- The novel is *Moby Dick* in the lesson; Eg-walker, Yjs, Riak, Redis Enterprise and Cosmos DB are left to the lesson.
- "Waits until the character it names has arrived" is the lesson's condition for any delivery order.
- The on-screen typo example (both agents add the missing 0 to `pay 4`, giving `pay 400`) is made up to picture the
  lesson's "fix typed twice".
