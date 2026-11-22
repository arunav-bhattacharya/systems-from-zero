# Which list should the shop keep? Bookmarks that say who saw what

- Slug / scene: `version-vectors`, `videos/scenes/version_vectors.py:VersionVectors`
- Lesson: `repl-08`, section 2, "Version vectors notice the clash that last write wins hides"
- Audience / level: a complete newcomer. Knows a shop, a till and Wi-Fi; nothing about replicas, clocks or Dynamo.
- Length: 4:47 (~800 words of narration, two 3-second pauses)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: the clash compared, "eu 3 > 2 / us 0 < 1", both boxes with their bookmarks (`POSTER=168`)
- The learner's real question: two copies changed while they couldn't talk. Which one should win, and how could a
  computer even tell whether one change knew about the other?
- Misconceptions to steelman and break: (1) "keep the later one", broken by the stolen card working again and a fast
  clock; (2) "merge by keeping every card on either list", broken by card-4417 coming back.
- Concept chain: last write wins drops a write → each list carries what its writer had seen (bookmarks) → the easy
  case replaces → the clash is concurrent → version vector, siblings → the union merge resurrects a removed card →
  limits (your code merges; vectors grow) → the merged write replaces both siblings (the check)
- Analogy family: the lesson's opening tills and their list of cards to refuse; bookmarks, one per till, saying how far
  into that till's numbered changes a copy has read.
- Open loops: "which list should the shop keep?" planted in scene 1 → answered in scene 8.
- Assumptions: cards, vectors and times are the lesson stepper's (card-4417, card-9921, card-5310; [(eu, 2)] →
  [(eu, 3)] and [(eu, 2), (us, 1)]; 10:00:05 and 10:00:03). The two tills become the stepper's two regions.

## The one picture

Two list boxes, left (till 1, later "EU copy", teal bookmark) and right (till 2, later "US copy", gold bookmark).
Each holds a row of two bookmarks (eu n, us n) and the cards. A dashed Wi-Fi line joins them (red with a cross when
down). Stamps and later the written vectors sit under each box. The middle holds the comparison, then the merged
list. Captions at the bottom.

## Scene 1 · Two tills · [QUESTION] [FAMILIAR] [LOOP-PLANT]

VO: Picture a shop with two tills, and a list of cards to refuse, such as cards reported stolen. Each till keeps its
own copy, and the copies sync over the shop's Wi-Fi. One morning the Wi-Fi drops. At the first till, a customer's lost
card has turned up, so the cashier takes card 4417 off the list. At the second till, the bank phones about a stolen
card, and the cashier adds card 5310. When the Wi-Fi comes back, the two lists disagree. Which one should the shop
keep?

SCREEN: Both boxes with card-4417 and card-9921; a dot crosses the Wi-Fi line. The line turns red; 4417 struck out
on the left; card-5310 appears in gold on the right.

## Scene 2 · Keep the later one · [PAIN] [BREAK] [JOKE:release] [WISH]

VO: The common answer is: keep the later one. On one computer, the later write is the newer decision. This rule is
called last write wins. The first till's list says 10:00:05. The second says 10:00:03. So the first list wins, the
whole of it, and the second list is thrown away. And with it, the stolen card. Card 5310 works again. No error, no
warning. Well... the thief is having a better morning than the shop.

Notice what went wrong. Neither cashier knew about the other's change. Later on the clock doesn't mean the writer had
seen the other list. And if the first till's clock ran a few seconds fast, it wasn't even later. What we want is for
each list to carry what its writer had already seen. Then the shop could tell a list that replaces another from two
lists that clash.

SCREEN: Stamps under each box; the right box dims; card-5310 turns red, "stolen card works again". The left stamp
wiggles on "a few seconds fast".

## Scene 3 · Bookmarks · [ANALOGY] [MAP]

VO: Here's an idea from everyday reading: bookmarks. Each till numbers its own changes, one, two, three. And every copy
of the list carries one bookmark per till, saying how far into that till's changes it has read. In the app, the two
tills are two copies of the list in two regions, Europe and the US. Before the Wi-Fi dropped, both copies had read EU's
first two changes, and none from the US. When a copy takes a change, it moves its own bookmark forward by one. EU
removes card 4417, so its EU bookmark goes from 2 to 3. US adds card 5310, so its US bookmark goes from 0 to 1.

SCREEN: Bookmark tags "eu 2" and "us 0" in both boxes; titles become "EU copy" and "US copy"; the left eu tag becomes 3,
the right us tag becomes 1, each highlighted as it moves.

## Scene 4 · The test · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Now the test. Take the easy case first. EU's list before the change had bookmarks 2 and 0. After, 3 and 0. Every
bookmark is at least as far along, so the newer list has read everything the old one had. It can replace it. Now the
clash. EU's bookmarks: 3 and 0. US's: 2 and 1. Did either one see the other's change? Pause and guess.

(three seconds)

Compare them one at a time. On EU's changes, EU is ahead, 3 against 2. On US's changes, US is ahead, 1 against 0. Each
has read something the other hasn't. So neither saw the other.

SCREEN: "EU, before" bookmarks in the middle, "3 ≥ 2, 0 ≥ 0" in green. Countdown. Then "eu 3 > 2, EU ahead" and
"us 0 < 1, US ahead", each column's tags lit in turn.

## Scene 5 · The names · [NAME]

VO: That's the test. If every entry of one is at most the other's, the second saw the first, and the first can go. If
each is ahead somewhere, the writes are concurrent: neither knew about the other. The bookmarks have a name: a version
vector, one counter per copy. Dynamo, Amazon's design for a store with many copies, called it a vector clock. And when
two versions are concurrent, Dynamo doesn't pick one. It keeps both, side by side, as siblings, and hands both to the
program on the next read.

SCREEN: The vectors written as the lesson writes them under each box, [(eu, 3)] and [(eu, 2), (us, 1)]; "sibling"
above both boxes.

## Scene 6 · The obvious merge · [BREAK] [JOKE:soften]

VO: So the program has to merge them. The obvious merge: keep every card that's on either list. That keeps the stolen
card 5310. So far so good. But look. Card 4417 is back. EU removed it, but the US list still had it, and a missing card
could mean removed, or never added. The union can't tell which. So the customer whose lost card turned up gets refused
again. Version vectors noticed the clash. They didn't settle it.

SCREEN: A green "merged" box between the two, fed by arrows: card-9921, card-5310, then card-4417 in red.

## Scene 7 · Limits · [GUARDRAIL]

VO: Two more limits. Your code gets the siblings and has to merge them well, and the Dynamo paper warns about exactly
this: a deleted item can come back. And the vector grows with every copy that takes writes. Dynamo cut its vectors at
about ten entries. Next, we'll meet data types that merge themselves, with no code from you.

## Scene 8 · Moral and a check · [MORAL] [LOOP-PAYOFF] [PREDICT] [PAUSE] [RECAP]

VO: So, which list should the shop keep? Not the later one. Keep a version only if it saw the other. If neither saw the
other, keep both. One quick check. The program merges the siblings and writes the result through EU, with bookmarks 4
and 1. Does it replace both siblings? Pause and think.

(three seconds)

Yes. Against EU's 3 and 0, it's ahead or equal on both. Against US's 2 and 1, the same. It has read everything both
siblings had.

SCREEN: New bookmarks "eu 4, us 1" in the middle ("merged write, through EU"); "4 ≥ 3, 1 ≥ 0" and "4 ≥ 2, 1 ≥ 1";
the sibling tags go; last caption "keep a version only if the new one saw it".

---

### Beat check

- QUESTION (which list?) from a felt situation; FAMILIAR (later = newer on one computer) steelmanned, then BREAK.
- ANALOGY + MAP (bookmarks per till; tills = regions; moving your own bookmark = counting your writes).
- PREDICT + PAUSE twice (did either see the other; does the merged write replace both), each with SHOW.
- NAME after SHOW: last write wins, concurrent, version vector, vector clock, siblings.
- Second BREAK (the union merge), then GUARDRAIL (your code merges; vectors grow), MORAL and the check.
- Light moments: the thief's better morning; the customer refused again.

### Accuracy notes for the producer

- The lesson's opening has two tills; its stepper has two regions. The video maps one to the other out loud.
- Bookmarks are the lesson's counters: [(eu, 2)] means "has seen eu's first 2 writes"; a missing node counts as 0, shown
  as "us 0".
- LWW drops the whole US version (the stepper's frame 3), so card-5310 is unblocked. The fast-clock point is the
  stepper's "if EU's clock was a few seconds fast".
- The merged write's vector [eu 4, us 1] follows the lesson's rule: the client sends the merged context
  [(eu, 3), (us, 1)] and the node it writes through (EU) adds 1 to its own entry, as D5 does in the Dynamo example.
- Strictly, a version vector tracks versions of one piece of data, while a vector clock orders events in general (the
  lesson's note); the video gives Dynamo's name only.
- The OR-Set that keeps card-4417 removed is the next section's (CRDTs); the video only points to it.
- SAY rules: card numbers as people read them, EU/US as letters, 10:00:05 as "ten o'clock and five seconds".
