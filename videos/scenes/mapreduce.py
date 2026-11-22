from sfz import *

# The letter A naming a node: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bMapReduce\b", "map reduce"))
SAY.insert(0, (r"\bGhemawat\b", "Gemma-watt"))
SAY.insert(0, (r"\bHadoop\b", "Hah-doop"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
X = [-4.5, 0.0, 4.5]                       # node and counter columns
NW, NH, NCY = 4.0, 1.9, 1.8                # node boxes (top row)
N_TOP, N_BOT = NCY + NH / 2, NCY - NH / 2
LAB_Y, LINE_Y, TAG_Y = N_TOP - 0.32, NCY - 0.05, NCY - 0.58
RW, RH, RCY = 3.6, 1.4, -1.75              # counters / reducers (bottom row)
R_TOP, R_BOT = RCY + RH / 2, RCY - RH / 2
RLAB_Y, RC_Y, PART_Y = R_TOP - 0.3, RCY - 0.22, R_BOT - 0.3
MID_Y = (N_BOT + R_TOP) / 2                # the strip between the rows
CAP_Y, BAR_Y = -3.38, -2.98

PURP = "#B48ED0"                           # a lighter purple, readable as text
KC = {"declined": GOLD_M, "approved": GREEN_M, "refunded": PURP}
OWNER = {"declined": 0, "approved": 1, "refunded": 2}       # (hashCode & MAX_VALUE) % 3, checked
BLOCKS = [["approved", "declined", "approved"], ["approved", "refunded", "approved"], ["declined", "approved", "refunded"]]
BOOKC = [BLUE_M, GOLD_M, GREEN_M, PURPLE_M, RED_M, TEAL_M]


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Never re-add a group whose parts are already on screen (that would draw filled shapes over their labels)."""
        curr = self.get_mobject_family_members()

        def visit(a):
            if isinstance(a, AnimationGroup):
                for s in a.animations:
                    visit(s)
                return
            if a.is_introducer() or a.mobject is None or a.mobject in curr:
                return
            fam = a.mobject.get_family()
            if len(fam) > 1 and all(m in curr for m in fam[1:]):
                return
            self.add(a.mobject)
            curr.extend(fam)

        for a in animations:
            visit(a)

    def remove(self, *mobjects):
        fam = []
        for m in mobjects:
            fam.extend(m.get_family())
        return super().remove(*fam)

    def steps(self, text, items, after=0.25):
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        t = 0.0
        for it in items:
            if isinstance(it, str):
                target = dur * text.index(it) / len(text)
                if target - t > 0.02:
                    self.wait(target - t)
                    t = target
                continue
            if isinstance(it, (int, float)):
                self.wait(it)
                t += it
                continue
            fn, rt = it
            self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    # labelled slots: put() swaps whatever sat in a slot for a new mobject
    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0]))

    def mid(self, mob, x=0.0, y=MID_Y):
        return self.put("mid", mob.move_to([x, y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def frame_box(x, y, w, h, color):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to([x, y, 0])


def nlabel(s, i, color=GREY_B):
    return left_at(T(s, 20, color), X[i] - NW / 2 + 0.25, LAB_Y)


def word_line(i):
    return fit(VGroup(*[T(w, 22) for w in BLOCKS[i]]).arrange(RIGHT, buff=0.28), NW - 0.5).move_to([X[i], LINE_Y, 0])


def pair(w):
    return chip(f"{w}, 1", KC[w], 17)


def pair_row(i, x=None, y=LINE_Y):
    row = VGroup(*[pair(w) for w in BLOCKS[i]]).arrange(RIGHT, buff=0.1)
    return fit(row, NW - 0.3).move_to([X[i] if x is None else x, y, 0])


def tags(row, words):
    return VGroup(*[M(f"-> {OWNER[w]}", 16, GREY_B).next_to(c, DOWN, buff=0.12) for c, w in zip(row, words)])


def books(i):
    g = VGroup(*[Rectangle(width=0.22, height=0.6, stroke_width=1.5, stroke_color=BOOKC[(i + k) % 6])
                 .set_fill(fillc(BOOKC[(i + k) % 6], 0.5), 1) for k in range(8)]).arrange(RIGHT, buff=0.06)
    return g.move_to([X[i], LINE_Y - 0.05, 0])


def rcontent(s, r, color=WHITE, size=20):
    return fit(T(s, size, color), RW - 0.3).move_to([X[r], RC_Y, 0])


class MapReduce(Base):
    """batch-03, section 1. The library's forty branches count books by author. A payment log on three nodes:
    one counter (1 TB through 125 MB/s, a billion counters in 2 to 4 GB) fails; "whoever is free" splits approved;
    one owner per key by hashCode % 3 (declined 0, approved 1, refunded 2). Map, tag, shuffle, reduce: declined 2,
    approved 5, refunded 2. Node B dies after its map: map 2 runs again on C. Guardrails (4 reducers move keys; one
    key never splits), the moral, and a check (declined: one reducer, 0)."""

    def construct(self):
        self.lab = {}
        self.title_card("One owner per key", "how MapReduce counts across machines")

        # ---------------- scene 1: the library ----------------
        boxes = [frame_box(X[i], NCY, NW, NH, BLUE_M) for i in range(3)]
        bks = [books(i) for i in range(3)]
        for i in range(3):
            self.lab[f"n{i}"] = nlabel(f"branch {i + 1} of 40", i).set_z_index(3)
        self.steps("Picture a city library on the night of its yearly count. By morning, the council wants to know how many books "
                   "it owns by each author. And the books sit in forty branches across town.", [
            "By morning",
            (lambda: self.cap("by morning: how many books by each author?", WHITE), 0.6),
            "And the books",
            (lambda: [LaggedStart(*[FadeIn(VGroup(boxes[i], self.lab[f"n{i}"], bks[i]), shift=0.15 * DOWN) for i in range(3)],
                                  lag_ratio=0.3)], 1.4),
        ])
        central = frame_box(0, RCY - 0.1, 2.2, 1.0, GREY_B)
        c_lab = T("central library", 20, GREY_B).next_to(central, RIGHT, buff=0.3)
        pile = VGroup()
        for i in range(3):
            for k, b in enumerate(bks[i]):
                c = b.copy()
                row, col = divmod(i * 8 + k, 8)
                c.target_pos = np.array([-0.98 + 0.28 * col, RCY - 0.45 + 0.74 * row, 0])
                pile.add(c)
        self.steps("The obvious plan: bring every book to the central library and count them there. With forty branches, that's a "
                   "building too small for the books, and a count still going next week.", [
            (lambda: [*self.drop("cap"), FadeIn(central), FadeIn(c_lab)], 0.6),
            "bring every book",
            (lambda: [LaggedStart(*[p.animate.move_to(p.target_pos) for p in pile], lag_ratio=0.06)], 2.0),
            "building too small",
            (lambda: [central.animate.set_stroke(RED_M)], 0.5),
            "a count still going",
            (lambda: self.cap("a count still going next week", RED_M), 0.6),
        ])
        notes = [chip("note", YELLOW_M, 18).move_to([X[i], 1.2, 0]) for i in range(3)]
        for b in bks:
            b.generate_target()
            b.target.shift(0.2 * UP)
        self.steps("The better plan sends the counting to the books. Each branch counts its own shelves, and sends on short notes, "
                   "never books.", [
            (lambda: [FadeOut(pile), FadeOut(central), FadeOut(c_lab), *self.drop("cap")], 0.6),
            "Each branch counts",
            (lambda: [MoveToTarget(b) for b in bks], 0.4),
            (lambda: [LaggedStart(*[Indicate(b, color=YELLOW_M, scale_factor=1.05) for b in bks], lag_ratio=0.3)], 1.0),
            "sends on short notes",
            (lambda: [FadeIn(n, scale=0.6) for n in notes], 0.4),
            (lambda: [n.animate.shift(1.3 * DOWN).set_opacity(0) for n in notes], 0.8),
            "never books",
            (lambda: self.cap("count where the books are; send notes, never books", WHITE), 0.6),
        ])
        self.stamp("s2")

        # ---------------- scene 2: the same problem on computers ----------------
        lines = [word_line(i) for i in range(3)]
        self.steps("Computers have the same problem. A payment company keeps a log of payment events, and it's too big for one "
                   "machine. So it's cut into blocks, spread over three machines. Each machine in the group is called a node.", [
            (lambda: [*self.drop("cap"), *[FadeOut(b) for b in bks]], 0.6),
            "So it's cut",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in lines], lag_ratio=0.3)], 1.0),
            "called a node",
            (lambda: [*[x for i in range(3) for x in self.put(f"n{i}", nlabel(f"node {'ABC'[i]}, block {i + 1}", i))],
                      *self.cap("node: one machine in the group")], 0.7),
        ])

        def words_of(key):
            return [w for i in range(3) for w, s in zip(lines[i], BLOCKS[i]) if s == key]

        self.steps("The question: how many times does each status appear? Approved, declined, refunded.", [
            (lambda: self.cap("how many times does each status appear?", WHITE), 0.5),
            "Approved,",
            (lambda: [w.animate.set_color(GREEN_M) for w in words_of("approved")], 0.4),
            "declined,",
            (lambda: [w.animate.set_color(GOLD_M) for w in words_of("declined")], 0.4),
            "refunded",
            (lambda: [w.animate.set_color(PURP) for w in words_of("refunded")], 0.4),
        ])
        self.steps("Say three machines do the counting. The word approved appears on all three nodes. How many of the counters end "
                   "up counting approved? Pause and guess.", [
            "The word approved",
            (lambda: [LaggedStart(*[Indicate(w, color=GREEN_M, scale_factor=1.25) for w in words_of("approved")], lag_ratio=0.15)], 1.2),
            "Pause and guess",
            (lambda: self.cap("how many counters count approved? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Hold on to your guess. Let's build the answer.", [
            (lambda: self.drop("cap"), 0.4),
        ])

        # ---------------- scene 3: version one, one counter ----------------
        one = frame_box(0, RCY, 4.6, RH, TEAL_M)
        one_lab = T("one counting machine", 20).move_to([0, RLAB_Y, 0])
        feeds = [Arrow([X[i] * 0.85, N_BOT - 0.08, 0], [X[i] * 0.25, R_TOP + 0.08, 0], buff=0, stroke_width=3, color=GREY_B,
                       max_tip_length_to_length_ratio=0.12) for i in range(3)]

        def flow(color=YELLOW_M, n=3):
            return [LaggedStart(*[dot_run(a.get_start(), a.get_end(), color, 0.5) for a in feeds for _ in range(n)], lag_ratio=0.1)]

        self.steps("Version one: every node sends every status it reads to one counting machine. For nine words, that's fine.", [
            (lambda: [FadeIn(one), FadeIn(one_lab), *self.cap("version 1: one counting machine", WHITE)], 0.6),
            "every status",
            (lambda: [GrowArrow(a) for a in feeds], 0.5),
            (lambda: flow(), 1.6),
            "For nine words",
            (lambda: self.put("one", rcontent("approved 5  ·  declined 2  ·  refunded 2", 1).move_to([0, RC_Y, 0])), 0.6),
        ])
        self.steps("Now ask a bigger question: how many payments per card, over a billion cards. The counter now receives the whole "
                   "input through one network link. One terabyte, through a link that moves 125 megabytes a second, takes over two hours.", [
            (lambda: [*self.cap("how many payments per card? a billion cards", WHITE), *self.drop("one")], 0.6),
            "The counter now receives",
            (lambda: [*[a.animate.set_color(RED_M).set_stroke(width=6) for a in feeds]], 0.6),
            (lambda: flow(RED_M, 4), 2.0),
            "One terabyte",
            (lambda: self.cap("1 TB through one 125 MB/s link: over 2 hours", RED_M), 0.6),
        ])
        self.steps("And it has to keep a billion counters in memory, on a machine with two to four gigabytes. That's the central "
                   "library again.", [
            "a billion counters",
            (lambda: [*self.cap("a billion counters, in 2 to 4 GB of memory", RED_M), one.animate.set_stroke(RED_M)], 0.6),
            "central",
            (lambda: [glow(one, RED_M, 1.03)], 0.8),
        ])
        rboxes = [frame_box(X[r], RCY, RW, RH, TEAL_M) for r in range(3)]
        for r in range(3):
            rboxes[r].set_z_index(1)
        self.steps("What we want is many counters, each with a share of the work. But then every node must know where to send "
                   "each note, without asking anyone.", [
            (lambda: [*[FadeOut(a) for a in feeds], FadeOut(one), FadeOut(one_lab), *self.drop("cap")], 0.6),
            "many counters",
            (lambda: [*[FadeIn(b, shift=0.1 * UP) for b in rboxes],
                      *[x for r in range(3) for x in self.put(f"r{r}", T(f"counter {r}", 20).move_to([X[r], RLAB_Y, 0]))]], 0.8),
            "But then",
            (lambda: self.cap("where does each note go?", YELLOW_M), 0.6),
        ])
        self.stamp("s4")

        # ---------------- scene 4: the easy rule, broken ----------------
        spread = [0, 2, 1, 0, 2]            # a made-up spread for "whoever is free"
        self.steps("Let's try the easy rule first. Send each note to whichever counter is free.", [
            (lambda: self.cap("the easy rule: send each note to whichever counter is free", WHITE), 0.6),
        ])
        qm = [T("?", 30, RED_M).move_to([X[r] + RW / 2 - 0.35, RLAB_Y, 0]) for r in range(3)]
        self.steps("Watch approved. Its notes land on all three counters. Each one has part of the count, and nobody has the total. "
                   "So now we need one more step to add the parts up. Well... we just built the central library again, only smaller.", [
            "Watch approved",
            (lambda: [LaggedStart(*[dot_run(w.get_bottom(), [X[r], R_TOP + 0.05, 0], GREEN_M, 0.8)
                                    for w, r in zip(words_of("approved"), spread)], lag_ratio=0.25)], 1.6),
            (lambda: [*[x for r in range(3) for x in self.put(f"c{r}", rcontent("part of approved", r, GREEN_M))]], 0.5),
            "nobody has the total",
            (lambda: [*[FadeIn(q, scale=0.5) for q in qm], *self.cap("three part answers; nobody has the total", RED_M)], 0.6),
            "Well...",
            (lambda: self.cap("one more step to add them up: the central library again, only smaller", RED_M), 0.6),
        ])

        # ---------------- scene 5: one owner per key ----------------
        self.steps("Back to the library. There, every author has one owner branch. Every branch sends its notes for that author "
                   "to the owner, and works out the owner by itself, from the name alone.", [
            (lambda: [*[FadeOut(q) for q in qm], *self.drop("c0", "c1", "c2"), *self.cap("in the library: every author has one owner branch", WHITE)], 0.6),
            "works out the owner",
            (lambda: self.cap("each branch works out the owner by itself, from the name alone", WHITE), 0.6),
        ])
        ex = pair("approved")
        self.steps("Let's map that. The branches are the nodes. The books are the log lines. A note is a pair: a word, and the number "
                   "one. The word is the key, whatever you group by. And the owner branch is a counter.", [
            "The branches",
            (lambda: [*self.cap("branch = node"), *[glow(b, BLUE_M) for b in boxes]], 0.7),
            "The books",
            (lambda: [*self.cap("book = log line"), *[Indicate(l, color=WHITE, scale_factor=1.06) for l in lines]], 0.7),
            "A note is a pair",
            (lambda: [*self.cap("note = a pair: (word, 1)"), *self.mid(ex.scale(1.25))], 0.6),
            "The word is the key",
            (lambda: [*self.cap("the word is the key: whatever you group by")], 0.5),
            "And the owner branch",
            (lambda: [*self.cap("owner branch = counter"), *[glow(b, TEAL_M) for b in rboxes]], 0.7),
        ])
        self.steps("The rule that picks the owner is a hash function. It turns a value into a number, and the same value always "
                   "gives the same number, on every machine.", [
            (lambda: self.cap("hash function: same value in, same number out, on every machine", WHITE), 0.6),
            "It turns a value",
            (lambda: self.mid(M('"approved".hashCode() = 1185244855', 22)), 0.7),
        ])
        self.steps("Divide that number by three and keep the remainder. That's a counter from zero to two. Approved gives one. "
                   "Declined gives zero. Refunded gives two.", [
            (lambda: self.mid(M("1185244855 % 3 = 1", 24, GREEN_M)), 0.6),
            "That's a counter",
            (lambda: self.cap("% 3: the remainder after dividing by 3, a counter from 0 to 2"), 0.5),
            "Approved gives",
            (lambda: self.put("c1", rcontent("owns approved", 1, GREEN_M)), 0.5),
            "Declined gives",
            (lambda: self.put("c0", rcontent("owns declined", 0, GOLD_M)), 0.5),
            "Refunded gives",
            (lambda: self.put("c2", rcontent("owns refunded", 2, PURP)), 0.5),
        ])
        self.steps("Hadoop, the free copy of Google's design, writes the rule like this. A hash code can be negative, so the first "
                   "part clears the sign, to keep the remainder a real counter number.", [
            (lambda: [*self.mid(M("(key.hashCode() & Integer.MAX_VALUE) % 3", 22, YELLOW_M)),
                      *self.cap("Hadoop: a free copy of Google's design")], 0.7),
            "A hash code can be",
            (lambda: self.cap("the & part clears the sign, so the remainder is 0, 1 or 2"), 0.6),
        ])
        self.stamp("s6")

        # ---------------- scene 6: map, shuffle, reduce ----------------
        rows = [pair_row(i) for i in range(3)]
        tg = [tags(rows[i], BLOCKS[i]) for i in range(3)]
        self.steps("Now run it. Map: each node reads its own block, and turns every word into a pair. Nine pairs in all. "
                   "No node knows what the others found.", [
            (lambda: [*self.drop("mid"), *self.cap("map: every word becomes (word, 1)", WHITE)], 0.5),
            "turns every word",
            (lambda: [LaggedStart(*[ReplacementTransform(lines[i], rows[i]) for i in range(3)], lag_ratio=0.3)], 1.4),
            "Nine pairs",
            (lambda: self.cap("9 pairs; no node knows what the others found", WHITE), 0.5),
        ])
        self.steps("Each node tags every pair with its owner, and writes them to its own disk. Approved is tagged one, on every node.", [
            "tags every pair",
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.05 * DOWN) for t in tg], lag_ratio=0.3)], 1.0),
            "writes them",
            (lambda: self.cap("tagged with the owner, written to the node's own disk", WHITE), 0.5),
            "Approved is tagged",
            (lambda: [LaggedStart(*[Indicate(tg[i][k], color=GREEN_M, scale_factor=1.4) for i in range(3) for k in range(3)
                                    if BLOCKS[i][k] == "approved"], lag_ratio=0.15)], 1.2),
        ])

        def shuffle(srcs, rt=1.8):
            """srcs: list of (chip, word). Copies fly to their owner's box and fade there."""
            anims = []
            for c, w in srcs:
                cp = c.copy().set_z_index(5)
                r = OWNER[w]
                anims.append(Succession(FadeIn(cp, run_time=0.01),
                                        cp.animate(run_time=0.9).move_to([X[r] + (np.random.rand() - 0.5) * 1.2, RC_Y, 0]),
                                        FadeOut(cp, run_time=0.2)))
            return [LaggedStart(*anims, lag_ratio=0.08, run_time=rt)]

        all_src = [(rows[i][k], BLOCKS[i][k]) for i in range(3) for k in range(3)]
        np.random.seed(3)
        self.steps("The shuffle: each counter fetches its pairs from every node, over the network. Then it sorts them by key, so "
                   "equal keys sit together. With millions of keys, that lets it finish one key and move on.", [
            (lambda: [*self.cap("the shuffle: each counter fetches its pairs from every node", WHITE), *self.drop("c0", "c1", "c2")], 0.5),
            (lambda: shuffle(all_src), 2.0),
            (lambda: [*self.put("c0", rcontent("declined: 1, 1", 0)), *self.put("c1", rcontent("approved: 1, 1, 1, 1, 1", 1)),
                      *self.put("c2", rcontent("refunded: 1, 1", 2))], 0.5),
            "Then it sorts",
            (lambda: self.cap("then it sorts by key, so equal keys sit together"), 0.5),
            "With millions",
            (lambda: self.cap("with millions of keys: finish one key, write it, move on"), 0.5),
        ])
        parts = [M(f"part-0000{r}", 16, GREY_B).move_to([X[r], PART_Y, 0]) for r in range(3)]
        res = [("declined = 2", GOLD_M), ("approved = 5", GREEN_M), ("refunded = 2", PURP)]
        self.steps("Reduce: each counter adds up each key, and writes one output file. Declined, two. Approved, five. Refunded, two.", [
            (lambda: self.cap("reduce: add up each key, write one output file", WHITE), 0.5),
            "Declined, two",
            (lambda: [*self.put("c0", rcontent(res[0][0], 0, res[0][1], 24)), FadeIn(parts[0])], 0.5),
            "Approved, five",
            (lambda: [*self.put("c1", rcontent(res[1][0], 1, res[1][1], 24)), FadeIn(parts[1])], 0.5),
            "Refunded, two",
            (lambda: [*self.put("c2", rcontent(res[2][0], 2, res[2][1], 24)), FadeIn(parts[2])], 0.5),
        ])
        self.stamp("poster")
        self.steps("So, your guess? Exactly one counter counts approved. No last step adds anything up, because every key lives "
                   "in one place.", [
            (lambda: self.cap("so, your guess?", YELLOW_M), 0.4),
            "Exactly one",
            (lambda: [*self.cap("exactly one counter counts approved", GREEN_M), glow(rboxes[1], GREEN_M)], 0.8),
            "because every key",
            (lambda: self.cap("every key lives in one place: nothing left to add up", WHITE), 0.5),
        ])
        self.steps("This is MapReduce, published by Jeff Dean and Sanjay Ghemawat of Google in 2004. You write two small "
                   "functions. Map turns one record into pairs. Reduce turns one key and all its values into a result. "
                   "Everything between them is the shuffle. And the counters are called reducers.", [
            (lambda: self.cap("MapReduce: Jeff Dean and Sanjay Ghemawat, Google, 2004", BLUE_M), 0.6),
            "Map turns",
            (lambda: [*self.cap("map: one record in, pairs out"), *[Indicate(r, color=WHITE, scale_factor=1.05) for r in rows]], 0.8),
            "Reduce turns",
            (lambda: self.cap("reduce: one key and all its values in, a result out"), 0.5),
            "Everything between",
            (lambda: self.cap("the shuffle: everything between them"), 0.5),
            (lambda: shuffle(all_src, 1.4), 1.4),
            "called reducers",
            (lambda: [*self.cap("the counters: reducers"),
                      *[x for r in range(3) for x in self.put(f"r{r}", T(f"reducer {r}", 20).move_to([X[r], RLAB_Y, 0]))]], 0.7),
        ])
        self.stamp("s7")

        # ---------------- scene 7: lose a machine ----------------
        self.steps("Now let's lose a machine on purpose. Node B finishes its map, and then dies, before the reducers fetch its pairs.", [
            (lambda: [*self.drop("c0", "c1", "c2"), *[FadeOut(p) for p in parts], *self.cap("run it again, and lose a machine", WHITE)], 0.6),
            "and then dies",
            (lambda: [boxes[1].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1), *self.put("n1", nlabel("node B: crashed", 1, RED_M)),
                      FadeOut(rows[1]), FadeOut(tg[1])], 0.8),
            "before the reducers",
            (lambda: [*[x for r in range(3) for x in self.put(f"c{r}", rcontent("waiting for map 2", r, GREY_B))]], 0.6),
        ])
        self.steps("Its map task already finished. Does it have to run again? Pause and guess.", [
            "Pause and guess",
            (lambda: self.cap("B's map had finished. run it again? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        rerun_row = pair_row(1, x=X[2], y=MID_Y - 0.2)
        rerun_lab = T("map 2, run again on C", 18, BLUE_M).move_to([X[2], MID_Y + 0.33, 0])
        self.steps("Yes. Those pairs sat on B's own disk, so they died with it. The master, the program that hands out the tasks, "
                   "runs map two again on node C, which keeps a copy of block two.", [
            (lambda: self.cap("yes: its pairs sat on B's own disk, and died with it", RED_M), 0.5),
            "The master",
            (lambda: self.cap("the master: the program that hands out the tasks", WHITE), 0.5),
            "runs map two",
            (lambda: [FadeIn(rerun_lab, shift=0.1 * DOWN)], 0.5),
            "which keeps a copy",
            (lambda: [FadeIn(rerun_row, shift=0.1 * DOWN), *self.cap("node C keeps a copy of block 2")], 0.6),
        ])
        src2 = [(rows[0][k], BLOCKS[0][k]) for k in range(3)] + [(rerun_row[k], BLOCKS[1][k]) for k in range(3)] + \
               [(rows[2][k], BLOCKS[2][k]) for k in range(3)]
        self.steps("The reducers fetch from C instead, and the totals come out the same. That only works because map is "
                   "deterministic: same input, same pairs, every time.", [
            (lambda: [*self.drop("c0", "c1", "c2")], 0.3),
            (lambda: shuffle(src2, 1.8), 1.8),
            (lambda: [*[x for r in range(3) for x in self.put(f"c{r}", rcontent(res[r][0], r, res[r][1], 24))],
                      *[FadeIn(p) for p in parts]], 0.5),
            "deterministic",
            (lambda: self.cap("deterministic: same input, same pairs, every time", WHITE), 0.5),
        ])
        oks = [tick(True, 0.14).next_to(parts[r], RIGHT, buff=0.15) for r in range(3)]
        self.steps("Finished reducers never run again. Their files are already in the file system, in three copies. In the "
                   "library, a lost note is just written again from the books.", [
            (lambda: [*self.cap("finished reducers: their files are in the file system, 3 copies"), *[Create(o) for o in oks]], 0.7),
            "In the library",
            (lambda: self.cap("a lost note is written again from the books", WHITE), 0.5),
        ])
        self.steps("How much does a failure cost? In the paper's one terabyte sort, the authors killed 200 of the 1,746 workers "
                   "a few minutes in. The job took 933 seconds instead of 891. Five percent slower.", [
            (lambda: self.cap("how much does a failure cost?", WHITE), 0.5),
            "the authors killed",
            (lambda: self.cap("the paper's 1 TB sort: 200 of 1,746 workers killed", WHITE), 0.5),
            "The job took",
            (lambda: self.cap("933 seconds instead of 891: 5% slower", GREEN_M), 0.5),
        ])
        self.stamp("s8")

        # ---------------- scene 8: two guardrails ----------------
        self.steps("Two things to watch. Change the number of reducers, and keys move. With four, approved goes to reducer three, not one.", [
            (lambda: [FadeOut(rerun_row), FadeOut(rerun_lab), *[FadeOut(o) for o in oks],
                      boxes[1].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1), *self.put("n1", nlabel("node B, block 2", 1)),
                      FadeIn(rows[1]), FadeIn(tg[1]), *self.cap("two things to watch", WHITE)], 0.7),
            "Change the number",
            (lambda: [*self.mid(M("1185244855 % 4 = 3", 24, RED_M)), *self.cap("change the number of reducers, and keys move")], 0.6),
            "With four",
            (lambda: [*self.cap("4 reducers: approved moves from 1 to 3", RED_M), glow(rboxes[1], RED_M)], 0.7),
        ])
        self.steps("And one key never splits. If most of the log is approved, one reducer gets most of the work, and the whole job "
                   "waits for it.", [
            (lambda: [*self.drop("mid"), *self.cap("one key never splits", WHITE)], 0.5),
            "If most of the log",
            (lambda: [LaggedStart(*[dot_run([X[i] + (k - 1) * 1.1, N_BOT - 0.05, 0], [X[1], R_TOP + 0.05, 0], GREEN_M, 0.6)
                                    for _ in range(3) for i in range(3) for k in range(3)], lag_ratio=0.05)], 2.0),
            "and the whole job",
            (lambda: [*self.cap("a busy key: one busy reducer, and the whole job waits", RED_M), glow(rboxes[1], RED_M)], 0.7),
        ])

        # ---------------- scene 9: moral and check ----------------
        self.steps("So, the moral: count where the data sits. Send each key to one owner, picked by a rule every machine works out "
                   "alone. And if a machine dies, just do its work again.", [
            (lambda: [*self.cap("count where the data sits", WHITE), *[glow(b, BLUE_M) for b in boxes]], 0.7),
            "Send each key",
            (lambda: [*self.cap("one owner per key, by a rule every machine works out alone", WHITE), *[glow(b, TEAL_M) for b in rboxes]], 0.7),
            "And if a machine",
            (lambda: self.cap("a machine dies? do its work again", WHITE), 0.5),
        ], after=0.5)
        dec = [rows[i][k] for i in range(3) for k in range(3) if BLOCKS[i][k] == "declined"]
        self.steps("One quick check. Declined appears on nodes A and C. How many reducers count it, and which one? Pause and think.", [
            (lambda: [*self.drop("c0", "c1", "c2"), *[FadeOut(p) for p in parts], *self.cap("one quick check", WHITE)], 0.5),
            "Declined appears",
            (lambda: [LaggedStart(*[Indicate(d, color=GOLD_M, scale_factor=1.2) for d in dec], lag_ratio=0.3)], 1.0),
            "Pause and think",
            (lambda: self.cap("declined: how many reducers, and which? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("One. Reducer zero, every time.", [
            (lambda: [*shuffle([(d, "declined") for d in dec], 0.9)], 0.9),
            (lambda: [*self.put("c0", rcontent(res[0][0], 0, res[0][1], 24)), glow(rboxes[0], GOLD_M),
                      *self.cap("one owner per key: declined goes to reducer 0, every time", WHITE)], 0.7),
        ], after=0.3)
        self.wait(2.0)
