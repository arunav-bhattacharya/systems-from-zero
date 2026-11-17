from common import *

L = load("found-04")
old = json.loads(json.dumps(L))
S = L["sections"]
assert len(S) == 4

SQL = FENCE.findall(old["sections"][1]["body"])
assert len(SQL) == 1 and SQL[0].startswith("```sql")
SQL = SQL[0]
STATS = FENCE.findall(old["sections"][0]["body"])
assert len(STATS) == 1
STATS = STATS[0]

L["goal"] = ("By the end, you can describe a system's load with the few numbers that drive its cost, work out what building "
             "a feed when it's read and building it in advance each cost when a few accounts are huge, and explain why real "
             "feeds treat very popular accounts and very busy followers separately.")

L["opening"] = """Picture yourself opening a social app on your phone and pulling down to refresh. In under a second you see the newest posts from the 200 accounts you follow, newest first. For almost everyone, that's easy work for the app.

Then a pop singer with 31 million followers posts a photo. For the next few minutes, posts arrive late for everybody, even the café's post about today's cake, which only 300 people follow.

The app's team had measured the load carefully, and the average account has only about 200 followers. Averages are what every report shows first, and for most accounts they're the honest picture. They hide the one account that breaks the design.

Lesson 3, Faults, failures and the people who run systems, ended on programs pushed past what they can carry. That leaves a question: how do you describe how much they have to carry? In this lesson, we'll name the few numbers that decide a system's cost, and price two ways to build a feed. Then we'll handle the extremes that break each one. Before we start, make a guess, and keep it in mind."""

L["warmup"] = {
    "q": "A small social app has 100,000 users, and each follows 50 accounts, so the average account has about 50 followers. The app keeps a ready-made feed for every user: each new post is copied into the feed of each of its author's followers. Which number decides whether every post can reach all of its followers within 5 seconds?",
    "options": [
        "The average number of followers, about 50",
        "The total number of follows, about 5 million",
        "The number of followers of the most-followed account",
        "How many users are using the app at once"
    ],
    "answer": 2,
    "why": "An average post costs 50 copies, which nobody notices. The deadline is broken by the account with the most followers. In this lesson's pretend network it has 67,725, so each of its posts needs 67,725 copies. At 5,000 copies a second, that's 13.5 seconds for one post. The average and the total describe the overall load well, and hide this case completely."
}

# ---------------- section 0 ----------------
S[0]["h"] = "Describing load: the few numbers that decide the cost"
S[0]["body"] = """Let's start back at the café's payments program. Say it handles 2,000 requests a second. That sounds like a description of its load, the amount of work coming in, but it can't tell you what will break first. If those are 2,000 card payments, each a message of about 2 KB (about 2,000 characters), that's 4 MB a second of small, separate jobs. Each needs one quick trip to the database. If they're 2,000 shop owners a second downloading a month of payments, 50 MB each, that's 100 GB a second. That needs different machines, a different way of storing data and a different design. Same rate, different systems.

So describing load means picking the few numbers that drive your system's cost. They're called its **load parameters**, and they come in a few kinds:

- rates: requests per second, posts per day, payments per hour at the busiest time of year;
- sizes: bytes per request, records touched per question;
- ratios: reads per write, or the share of questions a cache answers;
- counts per key, where a key is one account, one shop or one order: followers per account, payments per shop, items per order.

Report the peak, not only the average. In 2012, Twitter (the social network now called X) received about 5,000 posts a second on an average day, and over 12,000 during big events. Its record, in August 2013, was 143,199 posts in one second, during a Japanese TV showing of the film *Castle in the Sky*.

With the parameters in hand, you can ask the two questions that growing a system is about. If one parameter doubles and the machines stay the same, what happens to response time, the percentiles from Latency, percentiles and the tail? And if response time must stay the same, how many more machines do you need? When twice the machines carry twice the load at the same response time, the system has **linear scalability**. Usually the cost grows faster than that, and later lessons show why.

The last kind, counts per key, is the one people forget, because its average looks harmless. This lesson follows one system to show why: a social network's **home timeline**, the feed of recent posts by everyone a user follows. It's the best-documented load problem in public, because Twitter, X and Bluesky (a newer social network) have published their numbers. Its shape turns up in payments too, as the last section shows.

The lab builds a pretend network of 100,000 users who each follow 50 accounts. It picks them the way real networks grow, where a few accounts attract most of the follows. Here's how many followers each account ends up with:

""" + STATS + """

The median account has 21 followers. The most popular one is followed by two thirds of all users, over 1,300 times the average. Every design in this lesson costs about the same for the median account. They differ on that last number.

**Describe a count per key as a spread, up to its maximum.**

Next, we'll try the simplest way to build a timeline, and price it."""
t = S[0]["try"]
t["steps"] = [
    "From the `labs` folder, run the demo below. It builds the lab's pretend network (100,000 users, from the fixed random seed 42, so it's the same every time) and prints its load parameters first.",
    "Before you look at the second line of numbers, predict the most accounts that one user follows. Ordinary users follow exactly 50.",
    "Compare the two lines. Which one is skewed, with a few very large values, and where does the skew come from?"
]
t["expect"] = keep_blocks(old["sections"][0]["try"]["expect"], """The first block of output:

{B0}

A follow edge is one "this user follows that account" pair. The counts are exact on every machine, because the network comes from a fixed seed. Both means are 50.8, since every follow has one follower and one account being followed. Followers are skewed, because each user picks popular accounts more often. Follows are flat except for the 20 heavy users the generator adds, who follow 4,000 accounts each. Those 20 are the second extreme this lesson deals with.""")
S[0]["figure"]["caption"] = "The same network seen through five numbers, on a log scale (each step along the bottom is ten times the one before). The mean says 50, but one account has 67,725 followers, and that account decides the design."

# ---------------- section 1 ----------------
S[1]["h"] = "Building each feed when it's read: fan-out on read"
S[1]["body"] = """Start with the simplest design. Store each post once, next to its author, and build a timeline when someone asks for it. A mail room shows the idea. It keeps one pile of letters per sender. When you come for your mail, a clerk goes through the pile of everyone you know and picks out what's new.

In a database, the piles are tables, which hold data in rows like a spreadsheet. A `posts` table holds one row per post, and a `follows` table holds one row for each "this user follows that account" pair. The query below is in SQL, the language most databases understand, and you don't need to read SQL yet:

""" + SQL + """

In plain words: find every account that `:me` follows, read the recent posts of each one, put them in order with the newest first, and keep 50. Posting is as cheap as it gets, one row. A read costs one lookup for every account followed, 50 in the lab's network. When one request causes many requests behind it, that's **fan-out**, and the number it causes is the fan-out factor. Here the fan-out happens when someone reads, so this design is called **fan-out on read**.

Now put in realistic load. The book *Designing Data-Intensive Applications* uses a model with round numbers. There are 500 million posts a day, about 5,800 a second, and users follow 200 accounts on average. And 10 million users are online, each refreshing their timeline every 5 seconds. That's 2 million timeline reads a second, each looking up about 200 piles: **400 million lookups a second**. And that's for the average user. A user who follows 4,000 accounts makes every one of their reads cost 4,000 lookups.

The cost isn't only work. A read that fans out to 200 lookups has to wait for the slowest of them, and Latency, percentiles and the tail showed that fan-out makes the slow tail the normal case. If each lookup is slow 1% of the time, a read is fast only if all 200 are fast. 0.99^200 is about 0.13, so about 87% of reads hit at least one slow lookup.

Fan-out on read is still the right design when reads are rare or can't be predicted. Twitter's search worked this way. A post was written once into one index computer, and a search asked every index computer and merged the answers. Nobody can prepare the answer to a search that nobody has typed yet. A home timeline is different. It's the same question, asked again and again, by every user, every few seconds.

**Prepare answers in advance only for questions that keep coming back.**

So why not prepare the timeline in advance? Next, we'll do exactly that."""
t = S[1]["try"]
t["steps"] = [
    "Run the demo again (or scroll up to your last run) and find the `fan-out on read` row.",
    "Predict before you look: the mean and the largest number of lookups per read. Which user is behind the largest?",
    "The `work per post` column adds one post's writes to the lookups of 60 reads, about Twitter's 2012 ratio of reads to posts. Note it down for the next section."
]
t["expect"] = keep_blocks(old["sections"][1]["try"]["expect"], """{B0}

Every post costs exactly 1 write. The average read costs 50.8 lookups, one per account followed. The largest, 4,000, is one of the heavy users. `work per post` is 1 + 60 × 50.8 = 3,048. Delivery is instant, because a new post shows up on the next read with no extra work.""")

# ---------------- section 2 ----------------
S[2]["h"] = "Building each feed in advance: fan-out on write"
S[2]["body"] = """Turn it around. Keep a ready-made timeline for every user: a list of post numbers, newest first. When Ana posts, the program looks up her followers and adds the new post's number to each follower's timeline. A read is now one lookup of one list that is already merged and in order. This design is called **fan-out on write**. In the mail room, it's a clerk who sorts every letter into each person's pigeonhole the moment it arrives, so collecting your mail takes a second.

The ready-made timeline is a materialized view, the derived data from What a data system is: a stored answer that you could throw away and rebuild from the posts and the follows. It exists only to make reads cheap, and you pay for it on every write. A post costs one write per follower of its author.

In the book's model, that's 5,800 posts a second × 200 followers, about **1.16 million timeline writes a second**. Fan-out on read needed 400 million lookups, so this is roughly 345 times less work. Why such a gap? Look at one author. Fan-out on write charges one write per follower each time the author posts. Fan-out on read charges one lookup per follower each time a follower reads. The follower count is the same on both sides. So for each author, the question is which happens more often, posting or reading. People read their timelines far more often than their friends post, so fan-out on write wins for nearly everyone.

It copes with bursts well, too. If 150,000 posts arrive in one second, the writes go into a queue, a list of jobs waiting to be done, and get done over the next few minutes. Posts appear a little late, and reads stay fast.

Twitter ran this design in 2012, as Raffi Krikorian, one of its engineers, described in a talk that year. Home timelines lived in Redis, a program that keeps data in memory so it can answer fast. Each timeline was capped at 800 entries and kept in 3 copies. Twitter served about 300,000 timeline reads a second, against about 5,000 new posts. The goal was to deliver each post to every follower within 5 seconds, and reaching 1 million followers took about 3.5 seconds.

Now take one author with 31 million followers, as the singer Lady Gaga had then. One of her posts is **31 million writes**. At the rate that reached 1 million followers in 3.5 seconds, that's about 108 seconds, even with the fan-out workers to itself. (The workers are the programs that do the copying.) The talk reported deliveries taking up to 5 minutes. The workers take posts from the queue in order, so the posts behind hers wait as well. A post from an account with 200 followers can't start until the 31 million writes ahead of it are done. That's the **celebrity problem**: one key with so many followers that its work holds up everyone else's.

**The cost of a post is its author's follower count. Find the largest one.**

The mail room has the same trouble: one sender mails 31 million people at once, and the clerks do nothing else all morning. Next, we'll handle that sender, and the reader at the other extreme."""
st = S[2]["stepper"]
st["intro"] = "Watch where the work goes. Count the writes when a post arrives, and the lookups when Cleo reads."
says = [
    "**Fan-out on read, writing.** Ana posts `p7`. The program adds it to Ana's own list and is done: **1 write**, whether Ana has 3 followers or 3 million.",
    "**Fan-out on read, reading.** Cleo opens the app. The program fetches the list of every account she follows (Ana, Ben and Eli), merges them newest first and returns `p7 p6 p5`: **3 lookups**. With 200 follows, it's 200 lookups on every read.",
    "**Fan-out on write, writing.** Now every user has a ready-made timeline. Ana has 3 followers, so her post is added to 3 timelines: **3 writes**. The work moved from the reader to the writer.",
    "**Fan-out on write, reading.** Cleo's read fetches one list that is already merged and in order: **1 lookup**. Timelines are read far more often than posts are written, so this trade usually wins by a wide margin.",
    "**The celebrity.** One post from an account with 31 million followers is **31 million writes**. Twitter's fan-out reached 1 million followers in about 3.5 s, so this one post needs about 108 s even with the workers to itself, far past a 5 s target. Every ordinary post in the queue behind it waits too.",
    "**The hybrid.** Accounts above a follower threshold aren't fanned out. Star's post is stored once (**1 write**). Cleo's read fetches her ready-made timeline plus the list of each celebrity she follows, and merges them: **2 lookups** instead of 1."
]
assert len(st["frames"]) == len(says)
for f, s in zip(st["frames"], says):
    f["say"] = s
t = S[2]["try"]
t["steps"] = [
    "Find the `fan-out on write` row in the demo's output.",
    "Predict the slowest delivery. The demo's fan-out workers do 5,000 timeline writes a second, and you know the most-followed account from the first Try it.",
    "Compare `work per post` with the fan-out on read row."
]
t["expect"] = keep_blocks(old["sections"][2]["try"]["expect"], """{B0}

Writes per post average 50.8, the mean follower count, but one account's posts cost 67,725 writes. At 5,000 writes a second, that post takes 67,725 / 5,000 = 13.5 s to reach its last follower, even with an empty queue. Total work per post drops from 3,048 to 111 (50.8 + 60 × 1). So fan-out on write is 27 times cheaper overall, and still misses a 5-second target because of one account.""")

# ---------------- section 3 ----------------
S[3]["h"] = "Handling the extremes: celebrities, heavy followers and the hybrid"
S[3]["body"] = """The averages say fan-out on write. The extremes say it can't be the whole answer. There are two extremes, one on each side, and each gets its own fix.

The first is the celebrity. Don't fan out accounts with more than some number of followers. Store their posts once, in their own list, as fan-out on read does, and merge them into a follower's timeline when the follower reads. In the mail room, that sender's letters go on a table by the door, and each follower picks up a copy on the way out. A read then costs one lookup for the ready-made timeline, plus one for each celebrity the reader follows. Mixing the two designs like this is called a **hybrid**. Twitter's 2012 talk described this plan: stop fanning out the very largest accounts, and merge them in at read time.

Where should the line go? Work it out from the deadline. Say the fan-out workers do W writes a second, and a post must reach everyone within d seconds. Then no account with more than W × d followers can be fanned out in time. The demo's workers do 5,000 writes a second and the target is 5 seconds, so the threshold is 25,000 followers. Five accounts in the network are above it. Merging them makes the slowest delivery 4.7 s, and a read now costs 3.1 lookups on average instead of 1. Total work per post goes up, from 111 to 235. In this model the hybrid does more work in total, and buys a deadline it can meet. (The model charges for every follower's reads. In a real network, many of a celebrity's followers won't open the app before a post has scrolled out of their 800 entries. The copies written for them are wasted work, which the hybrid avoids.)

The second extreme is the **heavy follower**, who follows thousands of accounts and so receives a write for every post any of them makes. Bluesky described its fix in February 2025. Its timelines lived in ScyllaDB, a database spread over many computers, with each user's timeline kept together in one piece, for about 32 million users. One timeline write took about 600 µs (microseconds, millionths of a second). Users who followed hundreds of thousands of accounts overloaded the computers that held their timelines. So Bluesky drops writes on purpose: a user receives a share of their timeline writes equal to `min(2000 / follows, 1)`. Follow 4,000 accounts, and half the writes are skipped. Follow 8,000, and three quarters are. Nobody reads 8,000 accounts' posts anyway, so they see a fair sample. Fan-out for large accounts went from 5 to 10 minutes to under 10 seconds. The p99 time to fan out a whole post fell by over 96%.

Here the mail room picture breaks. No mail room throws away three quarters of someone's letters, but a skipped post costs its reader almost nothing.

The product can change the load as well. In 2023, X published the code behind its For You timeline, which is no longer "everyone I follow, newest first". Each request gathers about 1,500 candidate posts, roughly half from followed accounts and half from others. A machine-learning model, a program trained on past behaviour to guess what you'll like, ranks them, and a service called Home Mixer puts the timeline together. Much of that work happens when the user reads, because the ranking depends on the user and the moment.

So here is the method. Name the load parameters. Find the extreme that dominates the cost. Prepare answers in advance where reads dominate. Handle each extreme on its own, and accept a little imperfection where users can't see it.

**Size a design for its largest key, not its average one.**

This lesson counted work and left out machines. Next, we'll ask what to do when one computer can't carry the load."""
S[3]["aside"] = {
    "title": "Does this happen with payments too?",
    "body": "Yes, with shops in place of celebrities. Say the payments app keeps a running balance for each shop and updates it with every payment, which is fan-out on write to one place. That's right for almost every shop. Then a concert ticket shop opens its sales and takes 3,000 payments a second, and every one of them waits its turn to update the same balance. The fixes are the ones from this section: treat the extreme key on its own, for example by splitting its balance into several parts that a read adds up. And describe the load per key, as payments per shop at the median, the p99 and the maximum, as well as payments per second."
}
t = S[3]["try"]
t["steps"] = [
    "Run the demo with a threshold of 2,000 followers by adding `-Pargs='2000 60'` to the command. Predict first: what happens to the slowest delivery, and to lookups per read?",
    "Run it with `-Pargs='25000 0.5'`: the same hybrid, but users read only half as often as they post. Which design is cheapest now, and why?",
    "Find the hybrid's mean writes per post with a threshold of 1,000,000 (`-Pargs='1000000 60'`), where nobody counts as a celebrity. It's below fan-out on write's 50.8. What removed those writes?"
]
t["expect"] = keep_blocks(old["sections"][3]["try"]["expect"], """Threshold 2,000:

{B0}

Delivery drops to 0.4 s, but 157 accounts are now merged at read time, so a read costs 10.4 lookups on average and up to 157. A lower threshold buys faster delivery with more expensive reads.

At 0.5 reads per post, `work per post` is 26 for fan-out on read, against 51 for fan-out on write and 50 for the hybrid. When users read less often than they post, fan-out on read is cheaper. At a threshold of 1,000,000 the hybrid's mean is 50.4 writes, not 50.8. The 20 heavy users follow 4,000 accounts each, so Bluesky's rule keeps only half of their writes.""")

# ---------------- callouts ----------------
for k in ("analogy", "in_your_world", "mistake"):
    L.pop(k, None)

L["compare"]["note"] = "Both return the 50 newest posts by the accounts `:me` follows. The query on the left does its work every time someone reads, and its cost grows with how many accounts the reader follows. The loop on the right does its work once per post, and its cost grows with how many followers the author has. It uses three Redis commands: `LPUSH` adds a post number to the front of a list, `LTRIM` cuts the list to its first 800 entries, and `LRANGE` reads entries 0 to 49. `LTRIM` is why a ready-made timeline stays a fixed size: old entries fall off the end, and a user who scrolls past them falls back to a slower path."

W = L["worked"]
W["title"] = "Price both designs at the book's numbers, and pick a threshold"
ws = W["steps"]
assert len(ws) == 5
ws[0]["say"] = "Write down the load parameters. The book's model has 500 million posts a day, 200 follows (and so 200 followers) per user on average, and 10 million users online, each refreshing every 5 seconds."
ws[1]["say"] = "Fan-out on read pays on every read: one lookup per account followed."
ws[2]["say"] = "Fan-out on write pays on every post: one write per follower. Each read becomes one lookup."
ws[3]["say"] = "Check the extremes. Suppose the fan-out workers are sized for the average, about 1.2 million writes a second, and a post must reach everyone in 5 seconds. One post from an account with 100 million followers then needs almost a minute and a half, and every post behind it waits."
ws[4]["say"] = "Set the celebrity threshold from the deadline: the lab's `celebrityThreshold` is writes per second times the deadline (`floor` rounds down to a whole number). Accounts above 6 million followers are merged at read time, and everyone else is fanned out."

lab = L["lab"]
lab["steps"] = [
    "Run the tests once from the `labs` folder with the command above. All 9 fail with `NotImplementedError`, Kotlin's way of saying a function's body is still a `TODO`. Nothing else needs to be installed or started: everything is counted, not timed.",
    "Read `Timelines.kt`. `Work` counts writes and lookups, and `FanOutOnRead` is the finished design to compare against. The tests check your timelines against it, so read how it merges lists.",
    "In `Designs.kt`, write `FanOutOnWrite`: one `ArrayDeque` (a list you can add to at either end) per user, newest first, cut to `cap` entries. Count one write per follower and one lookup per read.",
    "Write `lossFactor` (Bluesky's `min(2000 / follows, 1)`), then `Hybrid`. Celebrities are stored once. Everyone else is fanned out, except the writes that `sample(postId, follower)` says to drop for heavy followers. A read is one lookup, plus one per celebrity followed.",
    "In `Delivery.kt`, write `deliverySeconds` (one first-in, first-out queue on a simulated clock) and `celebrityThreshold`. Run the tests until all 9 pass. One uses jqwik, a library that checks a rule against many random inputs: it checks that all three designs give every user the same timeline."
]
lab["hints"] = [
    "Post numbers grow with time, so `addFirst` keeps a timeline sorted newest first. `take(limit)` on an `ArrayDeque` gives you the read.",
    "Work out in the `Hybrid` constructor which followed accounts of each user are celebrities. Then a read doesn't have to scan all of a user's follows to find the few lists to merge.",
    "In the hybrid, merge `timeline.take(limit)` with `recent(celebrityPosts, limit)` for each celebrity, then `sortedDescending().take(limit)`. Taking more than `limit` from each list never changes the answer.",
    "For `deliverySeconds`, keep one variable: the time at which the queue is next free. A post starts at `max(arrival, queueFreeAt)`.",
    "If the property test fails, it prints the seed and the user. A celebrity threshold of 0, which makes every author with a follower a celebrity, is a good edge case to think through."
]

L["drill"]["prompt"] = "Without looking, write `homeTimeline` for the hybrid. You have the user's ready-made timeline (newest first, in `timelines[user]`), the celebrities they follow (`celebritiesFollowed[user]`), and each celebrity's posts, oldest first, in `celebrityPosts`. Count the lookups and return the newest `limit` post numbers."

L["recap"] = [
    "Load is described by a few load parameters: rates, sizes, ratios and counts per key. Report peaks and the whole spread, not only averages.",
    "Fan-out on read stores a post once and does the work on every read: one lookup per account followed. It suits rare or unpredictable reads, like search.",
    "Fan-out on write keeps a ready-made timeline per user, a materialized view, and pays one write per follower. For each author, it wins whenever followers read more often than the author posts.",
    "The extremes break each design: a celebrity's post is millions of writes that delay every post behind it, and a heavy follower makes reads, or writes, expensive.",
    "Hybrids handle the extremes separately: merge accounts above W × deadline followers at read time, and sample writes for heavy followers, as Bluesky's `min(2000 / follows, 1)` does.",
    "The limit: this lesson counted work, not machines. It doesn't say how many computers the work needs, or what to do when one computer is no longer enough."
]

L["closing"] = """We started with a pop singer whose one post made everyone's feed late, in a network where the average account looked harmless. The cost of a post is its author's follower count, and one huge count decided the design. The fix was to treat that account, and the heavy followers, on their own.

Look at an app you use that shows counts, such as followers, likes or reviews. Find the largest count you can, and compare it with a typical one. That ratio is the number its designers had to plan for.

Next, we'll ask what to do when one computer can't carry the load: buy a bigger one, or add more."""

Q = L["quiz"]
Q[0].update({
    "q": "An account posts 20 times a day. Each of its 10,000 followers opens the app 3 times a day. Counting only this account's posts, which design does less work?",
    "why": "Fan-out on write pays 10,000 writes for each of 20 posts: 200,000 a day. Fan-out on read pays one lookup of this account's list each time a follower reads: 10,000 × 3 = 30,000. The follower count appears on both sides and cancels, so what decides is posts per day against reads per day per follower. This author posts more often than the followers read. The first option counts only one post."
})
assert Q[1]["from"] == "found-02"
Q[1].update({
    "q": "With fan-out on read, a timeline read looks up the lists of 200 followed accounts at once and waits for all of them. Each lookup is slow 1% of the time, independently of the others. About what share of reads are slow?",
    "why": "A read is fast only if all 200 lookups are fast: 0.99^200 ≈ 0.13. So about 87% of reads wait for at least one slow lookup. This is the fan-out effect from Latency, percentiles and the tail: a rare slow case for each lookup becomes the normal case for each read. 1% would be right for a read that makes one lookup, and \"every read\" ignores the 13% of reads that still get lucky."
})
Q[2].update({
    "q": "Your fan-out workers do 400,000 timeline writes a second in total, and a post must reach every follower within 5 seconds. Above what follower count should the hybrid stop fanning out an account?",
    "why": "The threshold is writes per second times the deadline: 400,000 × 5 = 2,000,000 writes, the most one post can need and still finish in time with the workers to itself. 80,000 divides instead of multiplying. Merging everyone above the average would turn most reads into expensive merges, and throw away the reason for preparing timelines in advance."
})
Q[3].update({
    "q": "Bluesky's rule gives each user `min(2000 / follows, 1)` of their timeline writes. A user follows 10,000 accounts. What happens to the posts of the accounts they follow?",
    "why": "2,000 / 10,000 = 0.2, so each post lands in this user's timeline with a chance of 0.2, and the other 80% of the writes never happen. The sample is spread over all 10,000 accounts, not cut off at the most popular 2,000. Nothing is delayed: the writes are dropped on purpose, because nobody reads 10,000 accounts' posts."
})
Q[4].update({
    "q": "One first-in, first-out fan-out queue does 100,000 writes a second. A celebrity post needing 3,000,000 writes enters at t = 0 s. A post with 300 followers enters at t = 1 s. How long after it arrives does the small post reach all its followers?",
    "why": "The celebrity post holds the queue until 3,000,000 / 100,000 = 30 s. The small post arrives at 1 s, starts at 30 s and needs 300 / 100,000 = 3 ms, so it finishes at 30.003 s, about 29 s after it arrived. 3 ms is its own fan-out time with an empty queue, and 30 s measures from t = 0 instead of from its arrival. This wait behind the job at the front of the queue is why one celebrity hurts everyone's delivery."
})
assert [q["answer"] for q in Q] == [1, 2, 0, 1, 2]

L["flashcards"] = [
    {"front": "What is a load parameter?",
     "back": "One of the few numbers that drive a system's cost: a rate (requests a second), a size, a ratio (reads per write) or a count per key (followers per account, payments per shop)."},
    {"front": "Fan-out on read: what does a post cost, and what does a read cost?",
     "back": "A post is 1 write, to the author's own list. A read is one lookup per account the reader follows, plus a merge."},
    {"front": "Fan-out on write: what does a post cost, and what does a read cost?",
     "back": "A post is one write per follower of the author. A read is one lookup of a ready-made timeline."},
    {"front": "For one author, when is fan-out on write cheaper than fan-out on read?",
     "back": "When the author's followers read more often than the author posts. The follower count appears on both sides and cancels."},
    {"front": "How do you pick a hybrid's celebrity threshold?",
     "back": "From the deadline: fan-out writes per second × seconds allowed. Accounts with more followers than that can't be fanned out in time, so merge them in at read time."},
    {"front": "What is Bluesky's lossy fan-out rule (2025)?",
     "back": "A user gets `min(2000 / follows, 1)` of their timeline writes. Follow 8,000 accounts, and three quarters of the writes are dropped on purpose."},
    {"front": "Why does a celebrity's post hurt posts by ordinary accounts?",
     "back": "Fan-out workers take posts from a queue in order. Every post that arrives behind a 31-million-write job waits for it to finish."}
]

L["terms"] = [
    {"term": "Load parameter", "plain": "A number that describes how much work a system gets and drives its cost, such as requests per second or followers per account."},
    {"term": "Linear scalability", "plain": "Twice the machines carry twice the load at the same response time."},
    {"term": "Fan-out", "plain": "One request causing many requests behind it; the fan-out factor is how many."},
    {"term": "Fan-out on read", "plain": "Store each item once, and put the answer together when someone reads it."},
    {"term": "Fan-out on write", "plain": "Copy each new item into every place that will read it, so a read is one lookup."},
    {"term": "Home timeline", "plain": "The feed of recent posts by everyone a user follows."},
    {"term": "Celebrity problem", "plain": "One key with so many followers, or so much traffic, that work that grows with it breaks the design."},
    {"term": "Lossy fan-out", "plain": "Skipping some fan-out writes on purpose, for readers who could never read them all anyway."}
]

L["explain_back"] = {
    "prompt": "A friend asks why a social network that prepares every user's timeline in advance would still merge some posts in when the user reads. Explain it with numbers.",
    "answer": "Preparing in advance means every post is copied into each follower's timeline, so a post costs one write per follower and a read costs one lookup. For the average account that's a great deal, because people read far more often than their friends post. But the cost of a post is its author's follower count, and some counts are enormous. An account with 31 million followers needs 31 million writes per post. If the fan-out workers do about 285,000 writes a second, that's well over a minute and a half per post, and every ordinary post queued behind it waits too. So accounts above a threshold, the workers' writes per second times the delivery deadline, are stored once and merged into a follower's timeline at read time. That makes reads a bit more expensive, one extra lookup per celebrity followed, and keeps delivery within the deadline for everyone else."
}

L["deeper"]["body"] = """**Weighted costs.** This lesson counted a write and a lookup as one unit each. They aren't equal in practice. Twitter sent timeline writes in batches of thousands, while a fan-out-on-read lookup is a separate read that the reader waits for. Give them weights, `c_w` per write and `c_l` per lookup, and the rule for each author becomes: fan out on write when `posts × c_w < reads × c_l`. The follower count still cancels. What doesn't cancel is *who waits*. Fan-out on read puts the cost on the reader's response time. Fan-out on write puts it on delivery time, which a queue can absorb.

**How Bluesky stored its timelines.** Each user's timeline was one partition, a piece of the data kept together on one computer, spread over hundreds of shards. Writing a post to 1,000 timelines at once took about 1.2 s, and some single writes took 15 ms at the p99. One sequential fan-out to an account with 2,000,000 followers would have taken about 20 minutes.

**Caching the extremes.** Bluesky's rule needs each user's follow count on every fan-out. Its post says the counts for users who follow many accounts are kept in a Redis sorted set, reloaded every 30 seconds. Without that cache, the lookups would add over a million reads a second to the main database. Even the fix for one extreme had to be designed around another load parameter.

**Why the lab samples with a hash.** `sample(postId, follower)` turns the pair into a fixed number between 0 and 1, so the same post is kept or dropped for the same follower every time you run the code, and the tests can be exact. A real system could use a random number. A fixed one also means that a fan-out job that runs again drops the same writes, instead of filling in some it skipped the first time.

**The opposite pattern, on purpose.** Twitter's search index, Earlybird, was built on Lucene, a free library for search indexes, and held in memory. It stored each post on one machine and asked every machine at query time: fan-out on read, because nobody can prepare the answer to a search that hasn't been typed. Most large systems use both patterns, chosen for each feature from that feature's load parameters."""

for i, s in enumerate(S):
    S[i] = reorder(s, ["h", "body", "aside", "figure", "stepper", "sim", "try", "refs"])

L = reorder(L, ORDER)
save("found-04", L)
print("saved")
