# One question, three servers: who does the asking in DNS?

- Slug / scene: `dns-resolution`, `videos/scenes/dns_resolution.py:DnsResolution`
- Lesson: `net-09`, section 1, "Who does the asking: your program, a resolver and three servers"
- Audience / level: a complete newcomer who has read section 0 (names read from the right, zones, the phone books,
  authoritative servers, TTL). Knows nothing about resolvers.
- Length: 4:36 (~700 words of narration at the Kokoro voice's ~180 words a minute, plus the guesses and the
  silent walks)
- Poster: `POSTER=183` (the whole walk done: three rows of notes, the ms on each line, the answer by the program,
  "recursive resolver" named)
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: my program asked one question and got one answer. Who actually found it, and why
  doesn't my program just ask the right server?
- Misconception to steelman and break: "the program should walk the tree itself, every time". It works (`dig +trace`
  does it: three trips, about 110 ms), but it costs a tenth of a second per lookup and would send every lookup on the
  internet to the root.
- Concept chain: a name needs a number → the books from section 0 → directory enquiries does the reading for you →
  the stub makes one call (RD) → the resolver walks: root (referral + glue), com (referral), hera (the answer, AA,
  TTL 300) → hands on a copy → it keeps notes (two days, five minutes) → so the root is rarely asked → the catch:
  every note is a copy (hardest last: the check combines the two TTLs)
- Analogy family: the phone books from section 0 (a first book that says which book covers each ending, the com
  book, the company's own book) and directory enquiries, the service that reads the books for you; a senior manager
  who doesn't know the answer but knows who to ask (the root's referral)
- Open loops: "who did the asking?" planted in scene 1 → answered in scene 8; "so the resolver does the walking, and
  remembers" planted in scene 3 → paid off in scene 6
- Assumptions: the names, addresses, TTLs and times are the lesson's Try it and stepper (example.com, root, com,
  `hera`/`elliott` at Cloudflare, 104.20.23.154 and 172.66.147.243, TTLs 172,800 and 300, 46/48/16 ms, Docker's
  resolver at 127.0.0.11, the 200-seconds-later lookup with 100 left).

## The one picture

Left: your program (blue) with the stub inside. Middle: the resolver (teal), and under it its notes (the cache), a
card with one row per thing it learned and how long it may keep it. Right: the three books, stacked as a tree: the
root, com, example.com's own servers (white, gold where the original lives). Blue dots are questions, green dots
answers, gold dots referrals. Same places and colours throughout; ms labels sit on the lines as each trip happens.

## Scene 1 · The question · 0:00–0:24 · [QUESTION] [LOOP-PLANT]

VO: Your program wants to talk to example.com. But a packet needs a numeric address, not a name. So the program
asks: what's the address of example.com? A moment later, it has two. One question, one answer. But behind it, three
different organisations were asked, and your program spoke to none of them. Who did the asking?

SCREEN: The program box with "example.com ?" above it; a dot leaves and comes back; "104.20.23.154,
172.66.147.243" appears. The three books on the right light up one by one, then a "?".

## Scene 2 · The books, and directory enquiries · 0:24–1:09 · [FAMILIAR] [ANALOGY] [MAP] [JOKE:pivot]

VO: In the last section, the names were phone books. The first book only says which book covers each ending, like
com. The com book only says which book each company keeps. Only the company's own book has the numbers. You could read
all three yourself. Most people don't. They ring directory enquiries: one call, and somebody else reads the books.

Your program is the caller. Inside it is a small piece of code called the stub resolver; Java's getByName calls it.
It makes one call, to the address in a small settings file. That address belongs to a recursive resolver: directory
enquiries. And the books are servers: the root, the com servers, and example.com's own servers, the authoritative
ones.

SCREEN: The books appear as a stack with their analogy labels, then the caller and the enquiries desk. On the map
line, each label swaps to its technical name: stub resolver, recursive resolver (127.0.0.11 in the lab),
"who runs com", "who runs example.com", "authoritative" (later "hera and elliott"). Caption:
`/etc/resolv.conf: nameserver 127.0.0.11`.

## Scene 3 · Why not walk it yourself? · 1:09–1:38 · [BREAK] [LOOP-PLANT]

VO: Why the middleman? To be fair, your program could walk the books itself. A tool called dig can do exactly that,
and it works. It takes three trips: 46, 48 and 16 milliseconds, about a tenth of a second, for every lookup. Now
multiply. If every program on the internet started at the root for every lookup, a few root servers would answer for
the whole world, all the time. So the resolver does the walking, and it remembers. Watch how.

SCREEN: A dashed path from the program straight to the root, com, example.com; ms labels 46, 48, 16; "about 110 ms,
every lookup". Then many grey dots pour into the root from the left: "every lookup on the internet". Cleared.

## Scene 4 · The walk · 1:38–3:01 · [SHRINK] [PREDICT] [PAUSE] [SHOW] [JOKE:is-the-explanation]

VO: The stub sends one question to the resolver, with a flag that means: do the whole job for me. It's called RD,
recursion desired. The resolver's notes are empty. So it starts at the top. A root server's address is built into its
software, because nothing can be looked up before it. It asks the same question, without that flag: just tell me
what you know. Does the root know example.com's address? Pause and guess.

(three seconds)

No. The root is like a very senior manager. It doesn't know the answer, but it knows who to ask. It replies: ask the
com servers, here are 13 of them, and here are their addresses. That reply is a referral. The addresses that come
with it are called glue. Without them, the resolver would have to look up the com servers' names before it could ask
them anything.

The resolver asks a com server. Another referral, one level down: example.com lives on two servers run by
Cloudflare, hera and elliott, with their addresses. Third question, to hera. This time, an answer: two addresses,
marked authoritative, the original. Each may be kept for 300 seconds, its time to live. The resolver passes them to
the stub, marked as a copy. Three trips for the resolver; one question from your program.

SCREEN: Each trip is a blue dot out and a gold (referral) or green (answer) dot back, with its ms label on the line
and a new row in the resolver's notes: "com: 13 servers + addresses, 2 days", "example.com: ask hera or elliott,
2 days", "example.com: 104.20.23.154, 172.66.147.243, 300 s". The root shows "?" during the pause, then a referral
arrow points down the tree to com. A green dot returns to the program.

## Scene 5 · The names · 3:01–3:10 · [NAME]

VO: Now the names. The resolver that walks for you is a recursive resolver. The just-tell-me-what-you-know questions
it sends are iterative queries.

SCREEN: Captions; the program line glows ("one recursive question"), the three server lines glow ("iterative
queries").

## Scene 6 · The notes · 3:10–3:44 · [SHOW] [LOOP-PAYOFF] [JOKE:release]

VO: And it remembered everything. The referrals came with a time to live of 172,800 seconds: two days. The answer,
300 seconds: five minutes. 200 seconds later, another program asks for example.com. The resolver answers from its
notes in one short trip, and says the copy has 100 seconds left. That's why a few root servers can serve the whole
internet. A busy resolver answers almost every question from its notes, and asks the root again only every two days.
Lucky root.

SCREEN: The notes' keep-for column glows; the 300 s counter ticks down to 100; a dot goes program → resolver → program
without touching the tree, which dims. The root wiggles on "lucky root".

## Scene 7 · The catch · 3:44–3:58 · [GUARDRAIL]

VO: The catch: every note is a copy. For up to five minutes, the resolver hands out its copy without asking anyone.
If the owner changes the address, the copies don't hear about it. Fast answers and old answers come together.

SCREEN: The third row turns from green to "copy" grey; caption "a copy can be up to 5 minutes old".

## Scene 8 · The moral, and a check · 3:58–4:36 · [MORAL] [RECAP] [PREDICT] [PAUSE]

VO: So, who did the asking? Your program asked one helper. The helper walked the tree, one referral at a time, and
wrote down everything it learned, each note with its own expiry. One quick check. Ten minutes later, someone asks for
example.com again. Which servers does the resolver have to ask? Pause and think.

(three seconds)

Only example.com's own servers, hera or elliott. The five-minute answer has run out, but the referrals last two days.
The root and com get a rest.

SCREEN: The walk glows in order. For the check, the third row fades out ("expired"), a countdown, then a dot runs
only to example.com's box; the root and com stay dim with "2 days" glowing in their rows.

---

### Beat check

- Opens with the QUESTION (scene 1) and plants "who did the asking?".
- FAMILIAR (the books from section 0) and the ANALOGY (directory enquiries), MAP said out loud (scene 2).
- BREAK: the do-it-yourself walk, steelmanned then run to its cost (scene 3).
- PREDICT with PAUSE (scene 4, and the check in scene 8); SHOW right after each.
- NAME after the walk: referral, glue (scene 4, after each is seen), recursive resolver, iterative queries (scene 5).
  "Stub resolver" and "recursive resolver" are first used as labels in the map; the walk then shows what they do.
- GUARDRAIL (scene 7): every note is a copy. MORAL and RECAP (scene 8).
- Light moments: the senior manager (~2:10), lucky root (~3:40).

### Accuracy notes for the producer

- The stub reads `/etc/hosts` before `/etc/resolv.conf`; the video skips `/etc/hosts`.
- Java's `InetAddress.getByName` calls the C library's `getaddrinfo()`, which is the stub; Java also keeps its own
  copy for 30 seconds (section 4 of the lesson). The video says the stub keeps no notes and leaves Java's cache out.
- The root's reply names 13 com servers with their addresses (glue); the video shows it as one row.
- The resolver asks one of hera or elliott; the video shows hera, as the Try it did.
- "Marked as a copy": the resolver's reply has RA set and AA clear.
- The ms figures are one run of the Try it (46, 48, 16 ms); `dig +trace` picks root and com servers at random.
- The messages travel as UDP to port 53, with TCP for answers too big for one datagram (the TC flag). Left to the
  lesson, as are the message format and negative caching.
