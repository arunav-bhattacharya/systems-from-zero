from sfz import *

SAY.insert(0, (r"\bSDK\b", "S D K"))
SAY.insert(0, (r"\bAWS\b", "A W S"))
SAY.insert(0, (r"\b1 KB\b", "one kilobyte"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_POS = np.array([0.25, 3.05, 0])          # the table chip, top centre
BASEY, MH = -1.55, 2.6                     # meter baseline and the height of 1,000 write units
TOPY = BASEY + MH                          # the ceiling
LBL_Y = BASEY - 0.33
CNT_Y, BAR_Y, CAP_Y = -2.55, -2.95, -3.35
ROWX0, ROWX1 = -6.1, 6.1

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

    # captions, a counter line, and labels that swap in place
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

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

    def count(self, s, color=WHITE, size=24):
        return self.put("cnt", fit(T(s, size, color), 13.0).move_to([0, CNT_Y, 0]))

    def query(self, s, color=YELLOW_M):
        """A query chip; a list of strings stacks into lines so long filters stay readable."""
        lines = s if isinstance(s, list) else [s]
        t = VGroup(*[M(x, 19) for x in lines]).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=t.height + 0.26, stroke_color=color, stroke_width=2.5)
        r.set_fill(color, opacity=0.18)
        return self.put("q", fit(VGroup(r, t.move_to(r)), 3.9).move_to(Q_POS + 0.25 * LEFT))

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


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def u2h(v):
    return MH * v / 1000


def slots(n, x0=ROWX0, x1=ROWX1):
    s = (x1 - x0) / n
    return [x0 + s * (i + 0.5) for i in range(n)], min(1.15, s * 0.6)


def meter(x, w, v, cap=1000, color=BLUE_M, label=None, lcolor=None):
    """A partition: an outline up to the ceiling, a fill for its load or share (red above cap), and a label."""
    out = Rectangle(width=w, height=MH, stroke_color=GREY_C, stroke_width=2).move_to([x, BASEY + MH / 2, 0])
    lo = min(v, cap)
    base = Rectangle(width=w, height=max(u2h(lo), 0.001), stroke_width=0).set_fill(color, 0.55 if lo > 0 else 0)
    base.move_to([x, BASEY + u2h(lo) / 2, 0])
    hi = max(0, v - cap)
    over = Rectangle(width=w, height=max(u2h(hi), 0.001), stroke_width=0).set_fill(RED_M, 0.8 if hi > 0 else 0)
    over.move_to([x, BASEY + u2h(lo) + u2h(hi) / 2, 0])
    lab = T(label if label is not None else f"{v:,}", 22, lcolor or (RED_M if hi > 0 else WHITE)).move_to([x, LBL_Y, 0])
    return VGroup(out, base, over, lab)


def meters(n, v, **kw):
    xs, w = slots(n)
    return VGroup(*[meter(x, w, v, **kw) for x in xs])


class DynamoDBPartitions(Base):
    """shard-08, section 1. The puzzle (40,000 allowed, 6,000 used, 1,500 updates on one shop total, about 500 refused);
    the box office's ten windows and the tour group's queue; partitions and their ceiling (1,000 write units, 3,000
    read units, 10 GB); splits for capacity (3,200 → 4 × 800, 3,600 → 900, 6,000 → 8 × 750, 5,000 → 8 × 625, never
    merge), size (1,000 units and 15 GB → 2 × 500, throughput dilution) and traffic; one item or an in-order range
    can't be split; throttles, HTTP 400, SDK retries and the two throttling reasons; Local never throttles; a check."""

    def table(self, s, color=TEAL_M):
        return self.put("q", chip(s, color, 22).move_to(Q_POS))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Room in the table, a queue at one window", "why DynamoDB refuses a busy key")

        # ---------------- scene 1: the puzzle ----------------
        hook = [T("table: 40,000 writes a second allowed", 28, WHITE), T("used: 6,000", 28, WHITE),
                chip("one shop's running total: 1,500 updates a second", GOLD_M, 26),
                T("about 500 a second refused", 28, RED_M)]
        for k, m in enumerate(hook):
            m.move_to([0, 1.6 - 0.85 * k, 0])
        qm = T("?", 60, YELLOW_M).move_to([4.6, -0.95, 0])
        self.steps("Here's a puzzle. A payments table in DynamoDB, a database that Amazon runs for you, may take 40,000 writes a second. "
                   "It uses 6,000.", [
            "may take",
            (lambda: [FadeIn(hook[0], shift=0.1 * UP)], 0.6),
            "It uses",
            (lambda: [FadeIn(hook[1], shift=0.1 * UP)], 0.5),
        ])
        self.steps("Yet one record, the running total for the busiest shop, gets 1,500 updates a second, and about 500 of them are refused. "
                   "How can a table with so much room say no? Hold that question.", [
            (lambda: [FadeIn(hook[2], shift=0.1 * UP)], 0.6),
            "about 500",
            (lambda: [FadeIn(hook[3], shift=0.1 * UP)], 0.6),
            "How can",
            (lambda: [FadeIn(qm, scale=0.6), *self.cap("how can a table with so much room say no?", YELLOW_M)], 0.6),
        ], after=0.3)

        # ---------------- scene 2: the box office ----------------
        names = ["A–C", "D–F", "G–I", "J–L", "M–O", "P–R", "S–T", "U–V", "W–X", "Y–Z"]
        wx, _ = slots(10)
        WIN_Y = 0.9
        wins = VGroup(*[box(nm, GOLD_M, w=0.95, h=0.7, size=22).move_to([x, WIN_Y, 0]) for nm, x in zip(names, wx)])
        HOT = 4
        queue = VGroup(*[Dot(radius=0.07, color=GOLD_M).move_to([wx[HOT], WIN_Y - 0.6 - 0.24 * k, 0]) for k in range(9)])
        qlab = T("300 guests, one name", 20, GOLD_M).move_to([wx[HOT] + 1.75, WIN_Y - 1.5, 0])
        self.steps("Picture a concert hall's box office. Ten windows hand out booked tickets, each for a range of surnames: "
                   "A to C, D to F, and so on.", [
            (lambda: [FadeOut(VGroup(*hook, qm)), *self.uncap()], 0.6),
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in wins], lag_ratio=0.12)], 1.6),
        ])
        self.steps("Each serves a hundred people a minute, so the office serves a thousand.", [
            (lambda: self.cap("each window: 100 people a minute; the office: 1,000", WHITE), 0.6),
        ])
        self.steps("Tonight a tour company booked 300 seats under one name, and its guests come one by one. "
                   "All of them queue at one window, while nine sit quiet.", [
            "its guests",
            (lambda: [LaggedStart(*[FadeIn(d, shift=0.15 * UP) for d in queue], lag_ratio=0.2), FadeIn(qlab)], 1.6),
            "while nine",
            (lambda: [*[wins[i].animate.set_opacity(0.3) for i in range(10) if i != HOT], glow(wins[HOT][0], RED_M, 1.08)], 0.8),
        ])
        self.steps("The thousand a minute was never one big pool. It was ten windows of a hundred.", [
            (lambda: self.cap("never one big pool: ten windows of 100", YELLOW_M), 0.6),
            "ten windows",
            (lambda: [*[wins[i].animate.set_opacity(1) for i in range(10)]], 0.6),
        ], after=0.3)
        self.steps("DynamoDB cuts each table into pieces like those windows, called partitions. It hashes each item's partition key, "
                   "the part of the key that says whose item it is, into a big random-looking number, and each partition owns one stretch of those numbers.", [
            "called partitions",
            (lambda: [*[w[0].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1) for w in wins],
                      *self.cap("partitions: the pieces of a table", WHITE)], 0.7),
            "It hashes",
            (lambda: self.cap("hash(partition key) → a big number; each partition owns one stretch", WHITE), 0.6),
        ])
        self.steps("The windows are the partitions, a booking name is a partition key, and the office's total is the table's capacity.", [
            (lambda: self.cap("window = partition     booking name = partition key", WHITE), 0.6),
            "the office's total",
            (lambda: [*self.cap("the office's total = the table's capacity", WHITE), *self.table("table: the sum of its partitions")], 0.6),
        ], after=0.3)
        self.stamp("office")

        # ---------------- scene 3: the ceiling ----------------
        ceil = DashedLine([ROWX0, TOPY, 0], [ROWX1, TOPY, 0], dash_length=0.12, stroke_width=2.5, color=RED_M)
        ceil_l = T("ceiling: 1,000 write units a second per partition", 20, RED_M)
        ceil_l.move_to([ROWX1 - ceil_l.width / 2, TOPY + 0.25, 0])
        self.m = meters(4, 0, label="")
        self.steps("Each partition has a ceiling. It serves at most 1,000 write units and 3,000 read units a second, and holds about 10 GB.", [
            (lambda: [FadeOut(VGroup(wins, queue, qlab)), *self.drop("q")], 0.6),
            (lambda: [FadeIn(self.m), Create(ceil)], 0.8),
            "1,000 write units",
            (lambda: [FadeIn(ceil_l)], 0.5),
            "and holds",
            (lambda: self.cap("per partition: 1,000 write units, 3,000 read units, about 10 GB", WHITE), 0.6),
        ])
        self.steps("A write unit pays for one write a second of up to 1 KB. So why doesn't DynamoDB just add partitions when one gets busy? "
                   "It does, for three reasons. Let's take them one at a time.", [
            (lambda: self.cap("1 write unit = one write a second of up to 1 KB", WHITE), 0.6),
            "So why",
            (lambda: self.cap("partitions split, for three reasons", YELLOW_M), 0.6),
        ], after=0.3)

        def remeter(new):
            old, self.m = self.m, new
            return [ReplacementTransform(old, new)] if len(old) == len(new) else [FadeOut(old), FadeIn(new)]

        # ---------------- scene 4: capacity ----------------
        self.steps("Reason one is the capacity you ask for. On a provisioned table, you set the write units yourself, "
                   "and each partition gets an equal share.", [
            (lambda: [*self.cap("reason 1: the capacity you ask for", WHITE), *self.table("provisioned table: you set the write units")], 0.6),
        ])
        self.steps("DynamoDB's design paper gives the example: 3,200 write units need 4 partitions of 800. "
                   "Raise the table to 3,600, and each share becomes 900.", [
            "3,200",
            (lambda: [*self.table("table: 3,200 write units"), *remeter(meters(4, 800))], 0.8),
            (lambda: self.count("4 partitions × 800", WHITE), 0.4),
            "Raise the table",
            (lambda: [*self.table("table: 3,600 write units"), *remeter(meters(4, 900)), *self.count("4 partitions × 900", WHITE)], 0.8),
        ], after=0.3)
        self.steps("Now raise it to 6,000. What happens to the four partitions? Pause and guess.", [
            (lambda: [*self.table("table: 6,000 write units", YELLOW_M), *self.drop("cnt"),
                      *self.cap("6,000 over 4 partitions?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("Each would need 1,500, over the ceiling. So each splits in two: 8 partitions of 750.", [
            (lambda: [*self.uncap(), FadeOut(ceil_l), *remeter(meters(4, 1500))], 0.8),
            "over the ceiling",
            (lambda: [glow(ceil, RED_M, 1.0)], 0.5),
            "So each splits",
            (lambda: [*remeter(meters(8, 750)), *self.count("8 partitions × 750", WHITE)], 1.0),
            (lambda: [FadeIn(ceil_l)], 0.4),
        ], after=0.3)
        self.steps("Now lower it back to 5,000. Back to four? No. You keep 8, at 625 each. Partitions only ever split. They never merge.", [
            (lambda: [*self.table("table: 5,000 write units")], 0.5),
            "Back to four",
            (lambda: self.cap("back to four?", PURPLE_M), 0.5),
            "You keep 8",
            (lambda: [*remeter(meters(8, 625)), *self.count("still 8 partitions × 625", WHITE), *self.uncap()], 0.8),
            "only ever split",
            (lambda: self.cap("partitions only split; they never merge", YELLOW_M), 0.6),
        ])
        self.steps("A cut cake doesn't glue itself back together. So lowering the capacity gives you smaller shares, not fewer partitions.", [
            "So lowering",
            (lambda: self.cap("lower capacity: smaller shares, not fewer partitions", WHITE), 0.6),
        ], after=0.3)
        self.stamp("capacity")

        # ---------------- scene 5: size ----------------
        def share_lines(n, v):
            xs, w = slots(n)
            return VGroup(*[DashedLine([x - w / 2 - 0.15, BASEY + u2h(v), 0], [x + w / 2 + 0.15, BASEY + u2h(v), 0], dash_length=0.08,
                                       stroke_width=2.5, color=YELLOW_M) for x in xs])
        sl = share_lines(2, 500)
        xs2, w2 = slots(2)
        self.steps("Reason two is size. When a partition nears 10 GB, it splits in two. In DynamoDB's original design, "
                   "its share of the units was divided between the halves.", [
            (lambda: [*self.drop("cnt"), *self.cap("reason 2: size (about 10 GB)", WHITE), *self.table("table: 1,000 write units, 15 GB")], 0.6),
            "it splits in two",
            (lambda: remeter(meters(2, 0, label="")), 0.8),
            "its share",
            (lambda: [*remeter(meters(2, 500)), Create(sl), *self.cap("the original design: the share is divided between the halves", WHITE)], 0.8),
        ])
        self.steps("A table with 1,000 write units and 15 GB had two partitions of 500. A key range taking 800 writes a second was refused, "
                   "while the other half sat idle.", [
            (lambda: self.count("2 partitions × 500", WHITE), 0.5),
            "A key range",
            (lambda: remeter(VGroup(meter(xs2[0], w2, 800, cap=500, label="asks 800, share 500"), meter(xs2[1], w2, 0, label="idle", lcolor=GREY_B))), 0.9),
            "was refused",
            (lambda: [glow(self.m[0][0], RED_M, 1.03)], 0.6),
            "sat idle",
            (lambda: [glow(self.m[1][0], GREY_B, 1.03)], 0.6),
        ])
        self.steps("The paper calls this throughput dilution, throughput being the work done per second.", [
            "throughput dilution",
            (lambda: self.cap("throughput dilution: each split thins the share (original design)", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 6: traffic, and what no split can fix ----------------
        one = VGroup(meter(0, 1.15, 950, label="busy"))
        self.steps("Reason three is traffic. When a partition stays busy, DynamoDB splits it for consumption.", [
            (lambda: [FadeOut(sl), *self.drop("cnt"), *self.cap("reason 3: traffic", WHITE), *self.table("one busy partition")], 0.6),
            (lambda: remeter(one), 0.8),
        ])
        cut = DashedLine([-0.25, BASEY - 0.05, 0], [-0.25, BASEY + u2h(950) + 0.1, 0], dash_length=0.08, stroke_width=3, color=YELLOW_M)
        halves = VGroup(meter(-1.2, 1.15, 520, label="part"), meter(1.2, 1.15, 430, label="part"))
        self.steps("It cuts at a point chosen from the keys it has seen used, not the middle, so the busy keys land on both sides. That takes minutes.", [
            "It cuts",
            (lambda: [Create(cut)], 0.5),
            "so the busy keys",
            (lambda: [FadeOut(cut), *remeter(halves), *self.cap("cut where the keys are used: busy keys on both sides", WHITE)], 1.0),
            "That takes minutes",
            (lambda: self.count("a split for traffic takes minutes", WHITE), 0.5),
        ])
        item = chip("one item", GOLD_M, 22).move_to([3.4, 0.2, 0])
        cut2 = DashedLine([0, BASEY - 0.05, 0], [0, BASEY + u2h(1000) + 0.1, 0], dash_length=0.08, stroke_width=3, color=YELLOW_M)
        no = tick(False, 0.3).move_to([0.9, BASEY + u2h(500), 0]).set_z_index(5)
        self.steps("But two patterns can't be helped. One is a single item that takes all the traffic.", [
            (lambda: [*self.drop("cnt"), *self.cap("can't be helped 1: one item takes all the traffic", RED_M), *self.drop("q"),
                      FadeOut(ceil_l), *remeter(VGroup(meter(0, 1.15, 1000, label="")))], 0.8),
            "a single item",
            (lambda: [FadeIn(item, shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("The other is a key range written in order, such as one partition key with a time as its sort key, "
                   "so every new write lands at the same end. In the box office, a new window can't split one booking name.", [
            (lambda: self.cap("can't be helped 2: keys written in order; every new write at the same end", RED_M), 0.6),
            "a new window",
            (lambda: [Create(cut2)], 0.5),
            (lambda: [Create(no)], 0.5),
            (lambda: self.cap("a new window can't split one booking name", WHITE), 0.6),
        ], after=0.3)
        self.steps("And there's our puzzle. The shop's running total is one item, so it lives in one partition.", [
            (lambda: [FadeOut(cut2), FadeOut(no), *self.uncap(),
                      Transform(item, chip("the shop's running total: one item", GOLD_M, 22).move_to(item))], 0.7),
        ])
        self.steps("1,500 updates a second against a ceiling of 1,000: about 500 a second are refused, however much room the table has.", [
            (lambda: remeter(VGroup(meter(0, 1.15, 1500, label="1,500 asked"))), 1.0),
            "about 500",
            (lambda: [*self.count("1,500 asked − 1,000 ceiling = about 500 refused a second", RED_M)], 0.6),
            "however much room",
            (lambda: self.cap("the table's 40,000 can't lift one partition's ceiling", WHITE), 0.6),
        ], after=0.3)
        self.stamp("puzzle")

        # ---------------- scene 7: throttled, and the reason ----------------
        HX = -4.3
        hot = VGroup(meter(HX, 1.15, 1500, label="shop total: 1,500"))
        topp = np.array([HX, BASEY + u2h(1500) + 0.05, 0])
        self.steps("Refused has a name: DynamoDB throttles the request. It answers with HTTP 400, the web's code for a request it won't carry out, "
                   "and changes nothing.", [
            (lambda: [*self.drop("cnt"), *remeter(hot), FadeOut(item),
                      Transform(ceil, DashedLine([HX - 1.0, TOPY, 0], [HX + 1.0, TOPY, 0], dash_length=0.12, stroke_width=2.5, color=RED_M)),
                      *self.cap("throttled: refused, nothing changed", WHITE)], 0.8),
            "HTTP 400",
            (lambda: [Succession(dot_run([HX - 2.0, topp[1] + 0.3, 0], topp + 0.1 * LEFT, YELLOW_M, 0.5),
                                 dot_run(topp + 0.1 * LEFT, [HX + 2.0, topp[1] + 0.3, 0], RED_M, 0.5)),
                      *self.count("HTTP 400", RED_M)], 1.2),
        ])
        self.steps("Amazon's library for your code, the AWS SDK, retries a few times, waiting longer before each try. "
                   "So first you see slower answers, then an exception.", [
            "retries",
            (lambda: [Succession(*[Succession(Wait(g), dot_run([HX - 2.0, topp[1] + 0.3, 0], topp + 0.1 * LEFT, YELLOW_M, 0.4),
                                              dot_run(topp + 0.1 * LEFT, [HX + 2.0, topp[1] + 0.3, 0], RED_M, 0.4))
                                   for g in (0.1, 0.4, 0.9)])], 3.2),
            "slower answers",
            (lambda: self.count("the SDK retries, waiting longer each time: slow, then an exception", WHITE), 0.6),
        ])
        RX = 2.9
        r1 = M("TableWriteKeyRangeThroughputExceeded", 20, RED_M).move_to([RX, 1.1, 0])
        r1m = T("a hot partition", 22, WHITE).move_to([RX, 0.6, 0])
        r2 = M("TableWriteProvisionedThroughputExceeded", 20, GOLD_M).move_to([RX, -0.3, 0])
        r2m = T("the whole table used up its units", 22, WHITE).move_to([RX, -0.8, 0])
        x1 = tick(False, 0.22).next_to(r1m, RIGHT, buff=0.35)
        t2 = tick(True, 0.25).next_to(r2m, RIGHT, buff=0.35)
        self.steps("The exception carries throttling reasons, which name the limit. Table write key range throughput exceeded means a hot partition. "
                   "Table write provisioned throughput exceeded means the whole table used up its units.", [
            (lambda: [*self.drop("cnt"), *self.cap(M("ThrottlingReasons", 22, WHITE))], 0.6),
            "Table write key range",
            (lambda: [FadeIn(r1, shift=0.1 * UP)], 0.5),
            "means a hot",
            (lambda: [FadeIn(r1m)], 0.4),
            "Table write provisioned",
            (lambda: [FadeIn(r2, shift=0.1 * UP)], 0.5),
            "means the whole",
            (lambda: [FadeIn(r2m)], 0.4),
        ])
        self.steps("More capacity fixes the second. It does nothing for the first. Adding windows to the box office doesn't shorten the tour group's queue.", [
            (lambda: [*self.cap("more capacity?", WHITE)], 0.4),
            "fixes the second",
            (lambda: [Create(t2)], 0.5),
            "nothing for the first",
            (lambda: [Create(x1)], 0.5),
            "Adding windows",
            (lambda: [glow(self.m[0][0], RED_M, 1.03)], 0.7),
        ])
        self.steps("So read the reason before you raise the capacity.", [
            (lambda: self.cap("read the reason before you raise the capacity", YELLOW_M, 26), 0.6),
        ], after=0.4)
        self.stamp("reasons")

        # ---------------- scene 8: Local never throttles ----------------
        panel_r = RoundedRectangle(corner_radius=0.14, width=8.6, height=3.0, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        panel_r.move_to([0, 0.35, 0])
        ptitle = T("DynamoDB Local: one Java program, no partitions", 22, GREY_B).move_to([0, 1.5, 0])
        lines = [M(s, 22, c) for s, c in [("provisioned: 1 RCU, 1 WCU", WHITE), ("write units consumed: 1,000.0", WHITE),
                                           ("throttled: 0", GREEN_M)]]
        for k, l in enumerate(lines):
            l.move_to([-3.8 + l.width / 2, 0.8 - 0.6 * k, 0])
        self.steps("One more trap. DynamoDB Local is a single Java program for testing on your laptop. It has no partitions and ignores capacity.", [
            (lambda: [FadeOut(VGroup(r1, r1m, r2, r2m, x1, t2, self.m, ceil)), *self.uncap()], 0.7),
            "DynamoDB Local",
            (lambda: [FadeIn(panel_r), FadeIn(ptitle)], 0.6),
        ])
        self.steps("In the lesson's lab, a table of 1 write unit gets 1,000 writes from eight threads. How many are throttled? Pause and guess.", [
            (lambda: [FadeIn(lines[0])], 0.5),
            "1,000 writes",
            (lambda: [self.table("1,000 writes, 8 threads, no SDK retries", YELLOW_M)[0]], 0.5),
            "Pause and guess",
            (lambda: self.cap("how many throttled?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Zero. Local can't throttle. So to test how your code handles a throttle, use the lab's model or a real table.", [
            (lambda: [*self.uncap(), FadeIn(lines[1]), FadeIn(lines[2])], 0.6),
            "Local can't",
            (lambda: [Indicate(lines[2], color=GREEN_M, scale_factor=1.1)], 0.6),
            "So to test",
            (lambda: self.cap("to test throttle handling: the lab's model or a real table", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.m = meters(4, 800)
        ceil2 = DashedLine([ROWX0, TOPY, 0], [ROWX1, TOPY, 0], dash_length=0.12, stroke_width=2.5, color=RED_M)
        self.steps("So the moral of the story: a table's capacity is a sum of partition ceilings, and one record lives behind one of them.", [
            (lambda: [FadeOut(VGroup(panel_r, ptitle, *lines)), *self.drop("q"), FadeIn(self.m), Create(ceil2), FadeIn(ceil_l),
                      *self.cap("a table's capacity is a sum of partition ceilings", YELLOW_M, 26)], 0.8),
            "one record lives",
            (lambda: [glow(self.m[1][0], YELLOW_M, 1.04), *self.cap("and one record lives behind one of them", YELLOW_M, 26)], 0.7),
        ], after=0.3)
        chk = M("TableWriteProvisionedThroughputExceeded", 22, GOLD_M)
        self.steps("One quick check. Your exception says table write provisioned throughput exceeded. Will raising the table's capacity help? Pause and think.", [
            (lambda: [*self.uncap(), *self.put("q", chk.move_to(Q_POS))], 0.6),
            "Pause and think",
            (lambda: self.cap("raise the capacity?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        ok = tick(True, 0.3).next_to(chk, RIGHT, buff=0.35)
        self.steps("Yes. That reason is the table's own budget, not one hot partition, so more units are the fix.", [
            (lambda: [*self.uncap(), Create(ok)], 0.5),
            "the table's own budget",
            (lambda: [*[glow(mm[0], GREEN_M, 1.03) for mm in self.m], *self.cap("the table's budget ran out: more units are the fix", WHITE)], 0.8),
        ], after=0.3)
        self.steps("Next, we'll see how DynamoDB lends a busy partition the table's spare units, and where that help stops.", [
            (lambda: self.cap("read the reason before you raise the capacity", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.wait(2.0)
