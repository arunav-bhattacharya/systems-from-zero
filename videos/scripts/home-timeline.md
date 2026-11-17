# One post, 31 million writes: building the home timeline in advance

- Slug / scene: `home-timeline`, `videos/scenes/home_timeline.py:HomeTimeline`
- Lesson: `found-04`, section 2, "Building each feed in advance: fan-out on write"
- Audience / level: a complete newcomer. Has used a social app's feed; knows nothing about databases, queues or
  how a feed is built.
- Length: 4:27 (~690 words of narration at Kokoro's ~180 words a minute, plus two pauses and the builds)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- Poster: `POSTER=205` (the singer's 31 million writes at 108 s, the café's post waiting behind)
- The learner's real question: why would one person's post make everyone else's feed late, even a tiny café's?
- Misconception to steelman and break: "plan for the average account". The average (about 200 followers) makes
  fan-out on write look 345 times cheaper, and it is, for nearly everyone. Broken by the singer: one post is 31
  million writes, about 108 seconds of the workers' time, and the queue makes everyone behind it wait.
- Concept chain: reading every sender's pile on each refresh (fan-out on read) is a lot of lookups → sort each
  letter into followers' pigeonholes when it arrives (fan-out on write) → one write per follower, far cheaper when
  reads outnumber posts → bursts wait in a queue for the workers → the cost of a post is its author's follower
  count, and the largest one breaks the deadline (the celebrity problem, hardest last)
- Analogy family: the lesson's mail room. One pile of letters per sender; a clerk who goes through every pile you
  follow; pigeonholes on the wall, sorted the moment a letter arrives; a tray of letters waiting for the clerks; one
  sender who writes to 31 million people; a table by the door for that sender's letters.
- Open loops: "why would one post make everyone late?" planted in scene 1 → answered in scene 6; "the café's post"
  in scene 1 → the check question in scene 8; the table by the door teased in scene 7 → the lesson's next section.
- Assumptions: numbers are the lesson's (the book's model: 10 million users online, refreshing every 5 seconds,
  200 followers, 5,800 posts a second; Twitter 2012: 300,000 reads and 5,000 posts a second, 5-second goal, a
  million followers in about 3.5 seconds, 31 million followers, up to 5 minutes). Ana, Ben, Eli and Cleo are the
  lesson's stepper names. The singer isn't named on screen.

## The one picture

Left: the senders' own piles (blue): Ana's, Ben's and Eli's letters; the singer (gold) appears below them later.
Middle: the queue, a tray of letters waiting, and the clerks (teal), later the fan-out workers. Right: a wall of 12
pigeonholes, later ready-made timelines; the bottom row belongs to Cleo, Ben and Eli. Under Cleo's pigeonhole,
Cleo (purple) comes for her mail. Dots are letters being sorted (blue for Ana's post, gold for the singer's). A gold
progress bar with a clock shows the singer's 31 million writes. A dashed table by the door appears at the end.

## Scene 1 · The symptom · 0:00–0:25 · [QUESTION] [LOOP-PLANT]

VO: Open a social app and pull down to refresh. In under a second, you see the newest posts from the 200 accounts
you follow. Then a pop singer with 31 million followers posts a photo. For the next few minutes, posts arrive late
for everybody. Even the café's post about today's cake, which only 300 people follow. Why would one person's post
make everyone else's late?

SCREEN: "your feed: the newest posts from the 200 accounts you follow", turning red. A gold card "a pop singer, 31
million followers" and a teal card "the café, 300 followers", "late, for minutes". A "?" between them.

## Scene 2 · One pile per sender · 0:25–1:15 · [FAMILIAR] [ANALOGY] [PAIN] [WISH]

VO: Picture the app as the mail room of a big office. The simplest plan keeps one pile of letters for each sender.
One for Ana, one for Ben, one for Eli. When Cleo comes for her mail, a clerk goes through the pile of everyone she follows, and picks
out what's new. Three piles here. On a real app, about 200. That's called fan-out on read: the work happens when
someone reads. And people read a lot. With 2 million refreshes a second, each looking through about 200 piles,
that's 400 million lookups a second. Wouldn't it be nice if Cleo's mail were already sorted when she came for it?

SCREEN: Three blue piles on the left; Cleo below the right side. Purple lines run from Cleo to each pile and dots
come back: "3 lookups per read", then "about 200 lookups per read". Captions "fan-out on read: the work happens when
someone reads", "2 million reads a second × 200 piles = 400 million lookups a second", "already sorted when she
comes?".

## Scene 3 · Pigeonholes · 1:15–2:15 · [ANALOGY] [MAP] [SHOW] [NAME]

VO: So turn it around. Give everyone a pigeonhole, their own small box on the wall. The moment a letter arrives, a
clerk sorts it into the pigeonhole of everyone who follows its sender. Ana posts. Her followers are Cleo, Ben and
Eli, so her post goes into three pigeonholes. Three writes. Now Cleo comes for her mail. One lookup, of a list
that's already sorted, newest first.

In the app, each pigeonhole is a ready-made timeline: a list of post numbers, kept for every user. This design is
called fan-out on write, because the work happens when someone posts. It's a copy, worked out from the posts and
the follows, so it could be thrown away and rebuilt. It exists only to make reads cheap, and you pay for it on
every post: one write per follower.

SCREEN: The read lines go. A wall of 12 pigeonholes draws in (Cleo, Ben, Eli on the bottom row) and the clerks box.
A blue letter "p7" leaves Ana's pile, reaches the clerks, and three blue dots put "p7" into Cleo's, Ben's and Eli's
pigeonholes: "3 writes". An arrow grows from Cleo to her own pigeonhole: "1 lookup". The wall's title becomes
"ready-made timelines". Captions name fan-out on write and its price.

## Scene 4 · Count it · 2:15–3:05 · [SHRINK] [SHOW]

VO: Let's count it with the same round numbers. 5,800 posts a second, each to 200 followers, is about 1.16 million
writes a second. Against 400 million lookups, that's about 345 times less work. Why such a gap? Look at one author.
The follower count is on both sides. So the question is which happens more often: posting, or reading. People
refresh their feeds far more often than their friends post.

Bursts are fine too. If 150,000 posts land in one second, the letters wait in a queue, and the clerks, called
fan-out workers, catch up over the next few minutes. Posts appear a little late, and reads stay fast.

SCREEN: Captions "5,800 posts a second × 200 followers = 1.16 million writes a second", then "on read: 400 million
lookups / on write: 1.16 million writes / about 345 times less". Then "one author: a write per follower, per post vs
a lookup per follower, per read" and "reads happen far more often than posts". A tray of four slots ("the queue")
fills with letters; the clerks become "fan-out workers"; the letters go in and white dots fill the wall; Cleo's
pigeonhole glows.

## Scene 5 · Twitter's numbers · 3:05–3:25 · [SHOW]

VO: Twitter ran this design in 2012. It served about 300,000 timeline reads a second, against about 5,000 new posts.
The goal: every post in every follower's timeline within 5 seconds. Reaching a million followers took about 3.5
seconds.

SCREEN: Captions with the numbers.

## Scene 6 · The singer · 3:25–4:25 · [PREDICT] [PAUSE] [BREAK] [NAME] [JOKE:release] [LOOP-PAYOFF]

VO: Now the singer posts. She had 31 million followers. So one post is 31 million writes. At a million every 3.5
seconds, how long does it take? Pause and guess.

(three seconds)

About 108 seconds. In practice, deliveries took up to 5 minutes. And the clerks take letters from the queue in
order. So the café's post, with only 300 followers, waits behind 31 million writes. That's the celebrity problem:
one account with so many followers that its work holds up everyone else's. In the mail room, one sender writes to
31 million people at once, and the clerks do nothing else all morning.

SCREEN: The gold singer card appears bottom left; her letter moves to the front of the queue; "× 31 million" by the
wall. A gold progress bar "the singer's post: 31 million writes" with a clock. Countdown. The bar fills and the
clock runs to 108 s while gold dots stream into the wall. A teal "café" letter, "300 followers", joins behind the
singer's and turns red. Captions name the celebrity problem.

NOTE: The clerks doing nothing else all morning is the light moment, and it restates the mechanism.

## Scene 7 · The moral · 4:25–4:55 · [GUARDRAIL] [MORAL] [PRINCIPLE]

VO: So the average told the wrong story. The average account has about 200 followers, and looks harmless. The
design is decided by the largest one. The cost of a post is its author's follower count. Find the largest one.

The fix comes next in the lesson: don't sort the giant's letters at all. Leave them on a table by the door, and let
each follower pick one up on the way out.

SCREEN: "the average account: about 200 followers", "the design is decided by the largest one", then the moral in
yellow. The bar fades; a dashed "table by the door" appears under the singer and her letter moves onto it; a gold
dot goes from the table to Cleo.

## Scene 8 · A check · 4:55–5:15 · [PREDICT] [PAUSE] [LOOP-PAYOFF]

VO: One quick check. The café posts about today's cake. It has 300 followers. How many timeline writes is that?
Pause and think.

(three seconds)

300, one per follower. That's cheap. It was late only because it waited behind the singer's 31 million.

SCREEN: The café letter glows; countdown; "300: one per follower" and the café letter goes through the clerks; the
singer glows. The moral returns for the last frame.

---

### Beat check

- Opens with QUESTION (scene 1) from a felt symptom (everyone's feed is late).
- FAMILIAR + ANALOGY (scene 2) before the design names; PAIN (400 million lookups) and WISH before the cure.
- MAP said out loud (scene 3: pigeonhole = ready-made timeline, clerk's sorting = one write per follower; scene 4:
  the tray = the queue, clerks = fan-out workers).
- PREDICT with PAUSE twice (the singer's 108 seconds; the café's 300 writes); SHOW right after each.
- BREAK: planning for the average, broken by the singer (scene 6).
- NAME after the SHOW: fan-out on read (scene 2), fan-out on write (scene 3), fan-out workers (scene 4), the
  celebrity problem (scene 6).
- GUARDRAIL and MORAL (scene 7) come last, then the check. Light moment: the clerks doing nothing else all morning.

### Accuracy notes for the producer

- 2 million reads a second comes from the book's model: 10 million users online, each refreshing every 5 seconds.
  400 million / 1.16 million is 344.8, "about 345".
- Twitter 2012 (Raffi Krikorian's QCon talk, as quoted in the lesson): about 300,000 timeline reads and 5,000 posts
  a second, a 5-second delivery goal, a million followers in about 3.5 seconds, the 31-million-follower account
  (Lady Gaga) and deliveries of up to 5 minutes. 31 × 3.5 = 108.5 seconds.
- The progress bar shows the arithmetic (108 s at that rate), not a measured delivery.
- The lesson also says timelines lived in Redis, in memory, capped at 800 entries, in 3 copies, and calls the
  ready-made timeline a materialized view; the video leaves those to the lesson.
- The table by the door (the hybrid: merge the largest accounts at read time) is section 3 of the lesson; the video
  only teases it.
- The wall shows 12 pigeonholes for millions of users.
