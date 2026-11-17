from sfz import *

SAY.insert(0, (r"\bA-1001's\b", "A ten oh one's"))
SAY.insert(0, (r"\bA-1001\b", "A ten oh one"))
SAY.insert(0, (r"\bpay-81723\b", "pay eight one seven two three"))
SAY.insert(0, (r"\bALLOW FILTERING\b", "allow filtering"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RC, RR = np.array([-4.2, 0.35, 0]), 1.75          # the ring of nodes (left)
NODE_DEG = [90, 30, -30, -90, -150, 150]
TOKEN_DEG = 8
REPLICAS = [2, 3, 4]                              # the next three nodes clockwise from the token
DX0, DX1 = -1.3, 6.5                              # the drawer (right)
DCX = (DX0 + DX1) / 2
D_T, D_B = 2.45, -1.05
HEAD_Y = 2.05
SLOT = [1.5, 0.95, 0.4, -0.15, -0.7]
TOP_Y, CAP_Y, BAR_Y, QY = 3.3, -2.45, -2.8, -3.2
READ_X = -1.72                                    # the read arrow, between the ring and the drawer

ROWS = [("2026-11-07 10:30:12", "pay-81730", "SETTLED"), ("2026-11-07 09:40:27", "pay-81720", "FAILED"),
        ("2026-11-07 08:15:03", "pay-81701", "SETTLED"), ("2026-11-06 23:59:58", "pay-81655", "SETTLED")]
NEW = ("2026-11-07 09:00:00", "pay-81723", "AUTHORIZED")


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

    def steps(self, text, items, after=0.2):
        """Speak one line and play steps one after another inside it. A step is (fn, run_time), built just before
        it plays; a number waits that long; a string waits until about where that phrase is spoken."""
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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def on_ring(deg, r=RR):
    return RC + r * np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg)), 0])


# ---- the pieces ----
def node(k):
    b = RoundedRectangle(corner_radius=0.08, width=1.0, height=0.42, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
    return VGroup(b, T(f"node {k + 1}", 17)).move_to(on_ring(NODE_DEG[k]))


def row(slot, data, color=WHITE):
    tm, pid, st = data
    y = SLOT[slot]
    r = RoundedRectangle(corner_radius=0.08, width=DX1 - DX0 - 0.3, height=0.42, stroke_color=GREY_C, stroke_width=1.5).set_fill(BLACK, 1)
    r.move_to([DCX, y, 0])
    return VGroup(r, left_at(M(tm, 19, color), DX0 + 0.35, y), left_at(M(pid, 19, color), DX0 + 3.85, y),
                  left_at(M(st, 19, color), DX0 + 5.55, y))


def lit(r, color):
    return [r[0].animate.set_stroke(color, 3).set_fill(fillc(color, 0.3), 1), *[t.animate.set_color(color) for t in r[1:]]]


def unlit(r):
    return [r[0].animate.set_stroke(GREY_C, 1.5).set_fill(BLACK, 1).set_opacity(1), *[t.animate.set_color(WHITE).set_opacity(1) for t in r[1:]]]


def drawer_front(k, label):
    y = [1.85, 0.85, -0.15, -1.15][k]
    b = RoundedRectangle(corner_radius=0.1, width=DX1 - DX0, height=0.8, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M, 0.1), 1)
    b.move_to([DCX, y, 0])
    h = RoundedRectangle(corner_radius=0.06, width=1.1, height=0.16, stroke_color=GREY_B, stroke_width=2).set_fill(GREY_D, 1).move_to([DCX + 1.6, y, 0])
    return VGroup(b, h, left_at(T(label, 22, GOLD_M if k < 3 else GREY_B), DX0 + 0.35, y))


def drawer_box():
    b = RoundedRectangle(corner_radius=0.14, width=DX1 - DX0, height=D_T - D_B, stroke_color=BLUE_M, stroke_width=3).set_fill(
        fillc(BLUE_M, 0.08), 1).move_to([DCX, (D_T + D_B) / 2, 0])
    h = RoundedRectangle(corner_radius=0.06, width=1.1, height=0.16, stroke_color=GREY_B, stroke_width=2).set_fill(GREY_D, 1).move_to(
        [DCX, D_T + 0.17, 0])
    return VGroup(b, h)


def key_chip(s, color, size=20):
    t = T(s, size, color)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.4, height=0.48, stroke_color=color, stroke_width=2).set_fill(fillc(color), 1)
    return VGroup(r, t.move_to(r))


def mini(k):
    """A small copy of the drawer beside a replica, inside the ring."""
    c = key_chip("A-1001", GOLD_M, 14)
    return c.move_to(on_ring(NODE_DEG[k], RR - 0.75))


class WideColumn(Base):
    """model-05, section 0. A-1001's 20 newest payments out of 50 million, in Cassandra. A drawer of slips per account,
    newest at the front: the partition (partition key: account) and its order (clustering columns: created_at newest
    first, then payment_id). The coordinator hashes A-1001 to the token -4994511478997274402; its place on the ring picks
    the replicas. A payment from 09:00 written last lands between 09:40 and 08:15; a window 08:00 to 10:00 is one slice
    (3 read, 3 returned), oldest first is the same slice from the other end. FAILED with no account: no token, refused
    without ALLOW FILTERING. Partition size: 100,000 rows and 100 MB; by shop alone forever; by day 40,000; the busiest
    day 432,000; by hour 18,000; a week is 168 partitions. The name wide-column, the PRIMARY KEY line, and a check."""

    def cap(self, s, color=GREY_B, size=22):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def query(self, q, v="", vcolor=GREY_B):
        out = []
        nq = left_at(T(q, 21), -6.25, QY) if q else None
        nv = right_at(T(v, 21, vcolor), 6.25, QY) if v else None
        for old, new in ((self.qm, nq), (self.vm, nv)):
            if old is not None and new is not None:
                out.append(swap(old, new))
            elif old is not None:
                out.append(FadeOut(old))
            elif new is not None:
                out.append(FadeIn(new, shift=0.1 * UP))
        self.qm, self.vm = nq, nv
        return out

    def verdict(self, v, vcolor):
        nv = right_at(T(v, 21, vcolor), 6.25, QY)
        old, self.vm = self.vm, nv
        return [swap(old, nv)]

    def center(self, *lines):
        g = VGroup(*[M(s, 17, c) for s, c in lines]).arrange(DOWN, buff=0.18).move_to(RC + 0.1 * UP)
        old, self.cm = self.cm, g
        return [swap(old, g)] if old is not None else [FadeIn(g)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar, rate_func=linear), run_time=secs)

    def construct(self):
        self.capm = self.qm = self.vm = self.cm = None
        self.title_card("One drawer per account", "how Cassandra finds 20 rows in 50 million")

        # ---------------- scene 1: twenty out of fifty million ----------------
        qbox = RoundedRectangle(corner_radius=0.1, width=13.0, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([0, QY, 0])
        big = VGroup(T("50,000,000", 60, WHITE), T("payments", 30, GREY_B)).arrange(DOWN, buff=0.2).move_to([DCX, 0.7, 0])
        self.steps("Account A-1001 wants its 20 newest payments. The payments company keeps 50 million.", [
            (lambda: [FadeIn(qbox), *self.query("A-1001: the 20 newest", "?", YELLOW_M)], 0.8),
            "keeps 50 million",
            (lambda: [FadeIn(big, shift=0.1 * UP)], 0.8),
        ])
        ring = Circle(radius=RR, stroke_color=GREY_D, stroke_width=2).move_to(RC)
        nodes = [node(k) for k in range(6)]
        clus = T("one cluster", 20, GREY_B).move_to(RC + 0.1 * UP)
        self.steps("They live in Cassandra, a free database program that spreads its data over many computers. "
                   "Each computer is called a node, and together they work as one database, called a cluster.", [
            "spreads its data",
            (lambda: [Create(ring), LaggedStart(*[FadeIn(n, scale=0.8) for n in nodes], lag_ratio=0.15)], 1.6),
            "called a cluster",
            (lambda: [FadeIn(clus), glow(ring, BLUE_M, 1.02)], 0.8),
        ])
        refuse = T("and some questions: refused", 22, RED_M).move_to([DCX, -0.6, 0])
        self.steps("So how does it hand back 20 rows without touching the other 50 million? And why does it flatly refuse some questions?", [
            (lambda: [Indicate(big[0], color=WHITE, scale_factor=1.06)], 0.9),
            "And why",
            (lambda: [FadeIn(refuse, shift=0.1 * UP)], 0.6),
        ])

        # ---------------- scene 2: a drawer per account ----------------
        fronts = [drawer_front(0, "A-1001"), drawer_front(1, "A-2002"), drawer_front(2, "A-3003"), drawer_front(3, "... one drawer per account")]
        self.steps("Picture an office with a drawer of payment slips for each account, filed by date, newest at the front.", [
            (lambda: [FadeOut(big), FadeOut(refuse), *self.query("", "")], 0.6),
            "a drawer",
            (lambda: [LaggedStart(*[FadeIn(f, shift=0.1 * UP) for f in fronts], lag_ratio=0.2)], 1.2),
        ])
        box = drawer_box()
        head = left_at(T("partition A-1001, newest first", 21, GOLD_M), DX0 + 0.3, HEAD_Y)
        self.rows = [row(i, ROWS[i]) for i in range(4)]
        self.steps("To find A-1001's newest slips, you open one drawer and lift the front few out. The other drawers stay shut.", [
            "you open one drawer",
            (lambda: [glow(fronts[0][0], YELLOW_M, 1.02)], 0.6),
            (lambda: [*[FadeOut(f) for f in fronts[1:]], ReplacementTransform(fronts[0][0], box[0]), ReplacementTransform(fronts[0][1], box[1]),
                      ReplacementTransform(fronts[0][2], head)], 1.0),
            "lift the front few",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in self.rows], lag_ratio=0.2)], 1.0),
            "The other drawers",
            (lambda: [*self.cap("the other drawers stay shut", GREY_B)], 0.5),
        ])
        pk = key_chip("partition key: account_id", GOLD_M)
        ck = key_chip("clustering columns: created_at, newest first, then payment_id", GREEN_M)
        VGroup(pk, ck).arrange(RIGHT, buff=0.3).move_to([0, TOP_Y, 0])
        self.steps("Cassandra keeps rows the same way. The drawer is called a partition. Every row with the same account goes into it, "
                   "so the account is the partition key.", [
            "The drawer is called",
            (lambda: [*self.cap("drawer = partition", BLUE_M, 24), glow(box[0], BLUE_M, 1.01)], 0.7),
            "so the account",
            (lambda: [*self.cap("the account = partition key", GOLD_M, 24), FadeIn(pk, shift=0.1 * DOWN), Indicate(head, color=GOLD_M)], 0.8),
        ])
        self.steps("The order inside comes from the clustering columns: the time it was created, newest first, then the payment id, "
                   "to break ties.", [
            "The order inside",
            (lambda: [*self.cap("date order inside = clustering columns", GREEN_M, 24), FadeIn(ck, shift=0.1 * DOWN)], 0.8),
            "the time it was created",
            (lambda: [LaggedStart(*[r[1].animate(rate_func=there_and_back).set_color(GREEN_M) for r in self.rows], lag_ratio=0.25)], 1.2),
            "then the payment id",
            (lambda: [LaggedStart(*[r[2].animate(rate_func=there_and_back).set_color(GREEN_M) for r in self.rows], lag_ratio=0.25)], 1.0),
        ])

        # ---------------- scene 3: which node holds the drawer? ----------------
        self.steps("But which node holds the drawer? The node that takes your request, called the coordinator, hashes the partition key.", [
            (lambda: [*self.uncap(), FadeOut(clus)], 0.5),
            "called the coordinator",
            (lambda: [nodes[0][0].animate.set_stroke(WHITE, 4), *self.cap("coordinator: the node that takes your request", WHITE)], 0.7),
            "hashes",
            (lambda: self.center(("hash('A-1001')", GOLD_M)), 0.6),
        ])
        tok = Dot(radius=0.11, color=YELLOW_M).move_to(RC)
        self.steps("It turns A-1001 into a big whole number called a token, always the same for the same key.", [
            "a big whole number",
            (lambda: self.center(("hash('A-1001')", GOLD_M), ("-4994511478997274402", YELLOW_M)), 0.7),
            "called a token",
            (lambda: [*self.cap("token: a number worked out from the partition key", YELLOW_M)], 0.6),
        ])
        ticks = VGroup(*[Line(on_ring(d, RR - 0.08), on_ring(d, RR + 0.08), stroke_width=2, color=GREY_C) for d in range(0, 360, 15)])
        self.steps("Picture every possible token around a circle, with each node in charge of some stretches of it.", [
            (lambda: [Create(ticks), ring.animate.set_stroke(GREY_B, 2.5)], 1.0),
            "with each node",
            (lambda: [LaggedStart(*[glow(n[0], BLUE_M, 1.08) for n in nodes], lag_ratio=0.15)], 1.4),
        ])
        minis = [mini(k) for k in REPLICAS]
        self.steps("The token's place picks the nodes that keep a copy of the drawer, usually three, called replicas. Only they get asked.", [
            (lambda: [FadeIn(tok)], 0.2),
            (lambda: [tok.animate.move_to(on_ring(TOKEN_DEG))], 0.9),
            "usually three",
            (lambda: [*self.center(), LaggedStart(*[n[0].animate.set_stroke(GOLD_M, 3.5).set_fill(fillc(GOLD_M, 0.3), 1) for n in
                                                     (nodes[k] for k in REPLICAS)], lag_ratio=0.3)], 1.0),
            "called replicas",
            (lambda: self.cap("replicas: the nodes that keep a copy of the partition", GOLD_M), 0.6),
            "Only they",
            (lambda: [*[n.animate.set_opacity(0.35) for k, n in enumerate(nodes) if k not in REPLICAS and k != 0]], 0.6),
        ])
        self.steps("Where the office picture breaks: paper has one copy, and each replica holds the whole drawer.", [
            "paper has one copy",
            (lambda: self.cap("paper: one copy.  Cassandra: the whole drawer on each replica", WHITE), 0.6),
            "each replica holds",
            (lambda: [LaggedStart(*[FadeIn(m, scale=0.6) for m in minis], lag_ratio=0.3)], 1.0),
        ])

        # ---------------- scene 4: where does a late slip go? ----------------
        r = self.rows
        self.steps("Now open the drawer. Four payments, newest first. The 20 newest are the first 20 rows; here, all four.", [
            (lambda: [*self.uncap(), *[n.animate.set_opacity(1) for n in nodes], nodes[0][0].animate.set_stroke(GREY_B, 2.5),
                      *self.query("A-1001: the 20 newest")], 0.7),
            "Four payments",
            (lambda: [glow(box[0], BLUE_M, 1.01)], 0.7),
            "the first 20 rows",
            (lambda: [LaggedStart(*[AnimationGroup(*lit(x, GREEN_M)) for x in r], lag_ratio=0.25)], 1.0),
            "all four",
            (lambda: self.verdict("reads the first rows: all 4 here", GREEN_M), 0.5),
        ])
        newc = row(2, NEW, YELLOW_M)
        newc[0].set_stroke(YELLOW_M, 3).set_fill(fillc(YELLOW_M, 0.25), 1)
        newc.move_to([DCX, TOP_Y - 0.0, 0])
        self.steps("A new payment arrives, timed nine o'clock, and written last. Where does it go? Pause and guess.", [
            (lambda: [*[a for x in r for a in unlit(x)], *self.query("a new payment, timed 09:00, written last")], 0.6),
            "A new payment",
            (lambda: [FadeOut(VGroup(pk, ck)), FadeIn(newc, shift=0.2 * DOWN)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Between nine forty and eight fifteen. Only the account was hashed. The time says where inside the drawer it goes, "
                   "and no other row is rewritten.", [
            (lambda: [*self.uncap(), r[2].animate.move_to([DCX, SLOT[3], 0]), r[3].animate.move_to([DCX, SLOT[4], 0])], 0.7),
            (lambda: [newc.animate.move_to([DCX, SLOT[2], 0])], 0.8),
            "Only the account",
            (lambda: [Indicate(head, color=GOLD_M), *self.cap("only the account is hashed; the time picks the place", WHITE)], 0.8),
            "no other row",
            (lambda: self.verdict("lands in its sorted place · rows rewritten: none", GREEN_M), 0.6),
        ])
        self.rows = r = [r[0], r[1], newc, r[2], r[3]]
        ghost = row(4, NEW, GREY_C)
        ghost.move_to([DCX, SLOT[4] - 0.85, 0])
        gx = Line(ghost.get_left() + 0.2 * RIGHT, ghost.get_right() + 0.2 * LEFT, stroke_width=3, color=RED_M)
        self.steps("If you guessed the bottom, that's the spreadsheet habit: add at the end, sort when you read. "
                   "Here the order is how rows sit, in memory and on disk.", [
            (lambda: [*unlit(newc), *self.cap("the spreadsheet habit: add at the end, sort when you read", GREY_B)], 0.5),
            "add at the end",
            (lambda: [FadeIn(ghost, shift=0.1 * UP)], 0.5),
            "Here the order",
            (lambda: [Create(gx), *self.cap("the order is how rows sit, in memory and on disk", WHITE)], 0.6),
            (lambda: [FadeOut(VGroup(ghost, gx))], 0.5),
        ])

        # ---------------- scene 5: this morning is one slice ----------------
        down = Arrow([READ_X, SLOT[1] + 0.2, 0], [READ_X, SLOT[3] - 0.2, 0], buff=0, stroke_width=4, color=GREEN_M,
                     max_tip_length_to_length_ratio=0.12, max_stroke_width_to_length_ratio=12)
        self.steps("So ask for this morning, from eight to ten. The node jumps to the first row before ten, reads on while rows are inside "
                   "the window, and stops at the first row before eight.", [
            (lambda: [*self.uncap(), *self.query("A-1001, from 08:00 to 10:00"), FadeIn(VGroup(pk, ck))], 0.6),
            "jumps to",
            (lambda: [*lit(r[1], GREEN_M)], 0.5),
            "reads on",
            (lambda: [GrowArrow(down), *lit(r[2], GREEN_M)], 0.6),
            (lambda: [*lit(r[3], GREEN_M)], 0.4),
            "stops at",
            (lambda: [glow(r[4][0], RED_M, 1.02)], 0.7),
        ])
        self.steps("Three rows read, three returned. The ten thirty row and yesterday's row are never touched.", [
            (lambda: self.verdict("one slice: 3 read, 3 returned", GREEN_M), 0.6),
            "never touched",
            (lambda: [r[0].animate.set_opacity(0.3), r[4].animate.set_opacity(0.3)], 0.6),
        ])
        up = Arrow([READ_X, SLOT[3] - 0.2, 0], [READ_X, SLOT[1] + 0.2, 0], buff=0, stroke_width=4, color=GREEN_M,
                   max_tip_length_to_length_ratio=0.12, max_stroke_width_to_length_ratio=12)
        self.steps("Oldest first? Same three rows, read from the other end. Still no sort.", [
            (lambda: [*self.query("same window, oldest first")], 0.5),
            "read from the other end",
            (lambda: [ReplacementTransform(down, up)], 0.7),
            "Still no sort",
            (lambda: self.verdict("same slice, other end · sort step: none", GREEN_M), 0.6),
        ])

        # ---------------- scene 6: the question it refuses ----------------
        self.steps("Now the question it refuses. Every failed payment, without naming an account. No account, no token, no drawer.", [
            (lambda: [FadeOut(up), *[a for x in r for a in unlit(x)], *self.query("every FAILED payment, any account")], 0.7),
            "No account",
            (lambda: [*self.center(("no account:", RED_M), ("no token", RED_M)), FadeOut(tok)], 0.6),
            "no drawer",
            (lambda: [*[n[0].animate.set_stroke(GREY_B, 2.5).set_fill(BLACK, 1) for n in nodes], FadeOut(VGroup(*minis))], 0.6),
        ])
        self.steps("The only plan is to open every drawer on every node. So CQL, the language you query Cassandra in, refuses, "
                   "unless you add two words: ALLOW FILTERING.", [
            "open every drawer",
            (lambda: [LaggedStart(*[n[0].animate(rate_func=there_and_back).set_stroke(RED_M, 5).set_fill(fillc(RED_M, 0.4), 1) for n in nodes],
                                  lag_ratio=0.15), LaggedStart(*[x[0].animate(rate_func=there_and_back).set_stroke(RED_M, 4) for x in r], lag_ratio=0.15)], 1.6),
            "So CQL",
            (lambda: self.cap("CQL: the language you query Cassandra in", GREY_B), 0.5),
            "unless you add",
            (lambda: self.verdict("refused, unless ALLOW FILTERING", RED_M), 0.6),
        ])
        self.steps("That's the database asking: are you sure? You're about to open every drawer in the building.", [
            (lambda: self.cap("ALLOW FILTERING: “are you sure? every drawer, every node”", WHITE), 0.6),
        ])
        self.steps("So the rules follow from the picture. The partition key needs an equals, or there's no token. "
                   "Clustering columns can be limited only from the left. And a different question gets a different table.", [
            "The partition key needs",
            (lambda: [*self.cap("partition key: needs =, or there's no token", GOLD_M), glow(pk[0], GOLD_M, 1.03)], 0.7),
            "Clustering columns",
            (lambda: [*self.cap("clustering columns: limited only from the left", GREEN_M), glow(ck[0], GREEN_M, 1.02)], 0.7),
            "And a different",
            (lambda: self.cap("a different question gets a different table", WHITE), 0.6),
        ])

        # ---------------- scene 7: how big can a drawer get? ----------------
        BASE, SC = -1.0, 3.0 / 432000
        xs = [-6.0, -4.75, -3.5, -2.25]

        def bar(k, n, color):
            h = n * SC
            return Rectangle(width=0.55, height=h, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.6), 1).move_to(
                [xs[k], BASE + h / 2, 0])

        axis = Line([-6.5, BASE, 0], [-1.7, BASE, 0], stroke_width=2, color=GREY_B)
        lim_y = BASE + 100000 * SC
        lim = DashedLine([-6.5, lim_y, 0], [-1.7, lim_y, 0], dash_length=0.1, stroke_width=2.5, color=YELLOW_M)
        lim_t = T("100,000 rows", 17, YELLOW_M).move_to([xs[1], lim_y + 0.24, 0])

        def lab(k, a, b, color):
            return VGroup(T(a, 16, GREY_B), T(b, 16, color)).arrange(DOWN, buff=0.1).move_to([xs[k], BASE - 0.45, 0])

        forever = VGroup(Rectangle(width=0.55, height=2.9, stroke_color=RED_M, stroke_width=2).set_fill(fillc(RED_M, 0.6), 1).move_to(
            [xs[0], BASE + 1.45, 0]), Arrow([xs[0], BASE + 2.6, 0], [xs[0], BASE + 3.3, 0], buff=0, stroke_width=4, color=RED_M,
                                             max_tip_length_to_length_ratio=0.35))
        b_day, b_peak, b_hour = bar(1, 40000, GREEN_M), bar(2, 432000, RED_M), bar(3, 18000, GREEN_M)
        labs = [lab(0, "shop alone", "forever", RED_M), lab(1, "shop + day", "40,000", GREEN_M), lab(2, "busiest day", "432,000", RED_M),
                lab(3, "shop + hour", "18,000", GREEN_M)]
        self.steps("One more catch. A drawer never splits across nodes, and the Cassandra docs advise under 100,000 rows and 100 megabytes.", [
            (lambda: [*self.uncap(), *self.query("", ""), FadeOut(VGroup(ring, ticks, *nodes)), *([FadeOut(self.cm)] if self.cm else [])], 0.8),
            "A drawer never splits",
            (lambda: [*self.cap("a partition never splits across nodes", WHITE), glow(box[0], BLUE_M, 1.01)], 0.7),
            "advise under",
            (lambda: [Create(axis), Create(lim), FadeIn(lim_t), *self.cap("the docs: under 100,000 rows and 100 MB", YELLOW_M)], 0.8),
        ])
        self.cm = None
        self.steps("Its size is the write rate times how long the key stays the same. Key a shop's payments by shop alone, "
                   "and the drawer grows forever.", [
            (lambda: self.cap("rows in a partition = write rate × how long the key stays the same", WHITE), 0.6),
            "by shop alone",
            (lambda: [GrowFromEdge(forever[0], DOWN), FadeIn(labs[0])], 1.0),
            (lambda: [GrowArrow(forever[1])], 0.5),
        ])
        self.steps("Add the day: 40,000 payments a day, about 6 megabytes. Fine.", [
            "Add the day",
            (lambda: [GrowFromEdge(b_day, DOWN), FadeIn(labs[1])], 0.8),
            "about 6",
            (lambda: self.cap("shop + day: 40,000 rows, about 6 MB at 150 bytes a row", GREEN_M), 0.6),
        ])
        self.steps("But on the busiest day of the year, the biggest shop takes 5 a second: 432,000 rows. One drawer per hour gives 18,000.", [
            "the biggest shop",
            (lambda: [GrowFromEdge(b_peak, DOWN), FadeIn(labs[2])], 1.0),
            "432,000",
            (lambda: self.cap("5 a second × 86,400 seconds = 432,000 rows", RED_M), 0.6),
            "One drawer per hour",
            (lambda: [GrowFromEdge(b_hour, DOWN), FadeIn(labs[3]), *self.cap("one partition per hour: 18,000 rows", GREEN_M)], 0.8),
        ])
        self.steps("The price: a week of history is now 168 drawers, read in parallel and merged. Size it for your busiest key.", [
            (lambda: self.cap("the price: a week = 7 day partitions, or 168 hour partitions, merged", WHITE), 0.6),
            "Size it",
            (lambda: [*self.cap("size it for your busiest key, not your average one", YELLOW_M, 24), glow(b_peak, RED_M, 1.05)], 0.8),
        ])

        # ---------------- scene 8: the name, the key, and a check ----------------
        chart = VGroup(axis, lim, lim_t, forever, b_day, b_peak, b_hour, *labs)
        self.steps("This shape gives the family its name, wide-column, because one partition can hold a great many rows.", [
            (lambda: [FadeOut(chart), *self.cap("wide-column: one partition can hold a great many rows", WHITE)], 0.8),
            "a great many rows",
            (lambda: [glow(box[0], BLUE_M, 1.01)], 0.8),
        ])
        self.steps("It has nothing to do with a column store, which keeps each column's values together. Deep drawer would have been a better name.", [
            (lambda: self.cap("not a column store, which keeps each column's values together", GREY_B), 0.6),
            "Deep drawer",
            (lambda: [*self.cap("“deep drawer” would have been a better name", WHITE)], 0.6),
        ])
        code = VGroup(M("PRIMARY KEY ((", 24), M("account_id", 24, GOLD_M), M("), ", 24), M("created_at, payment_id", 24, GREEN_M), M(")", 24))
        code.arrange(RIGHT, buff=0.06).move_to([0, TOP_Y, 0])
        for part in code:
            part.align_to(code[0], DOWN)
        self.steps("Here's the key, read from the inside out. Inside the double brackets, which drawer. After it, the order inside.", [
            (lambda: [*self.uncap(), Succession(FadeOut(VGroup(pk, ck), shift=0.1 * UP), FadeIn(code, shift=0.1 * UP))], 1.0),
            "Inside the double",
            (lambda: [Indicate(code[1], color=GOLD_M), Indicate(head, color=GOLD_M)], 0.8),
            "After it",
            (lambda: [Indicate(code[3], color=GREEN_M)], 0.8),
        ])
        ring2 = VGroup(ring, ticks, *nodes)
        for n in nodes:
            n[0].set_stroke(GREY_B, 2.5).set_fill(BLACK, 1)
            n.set_opacity(0.5)
        ring.set_stroke(opacity=0.5)
        ticks.set_stroke(opacity=0.5)
        self.steps("So the partition key picks the drawer, the clustering columns pick the place in it, and a good question opens one drawer "
                   "and lifts out one run.", [
            (lambda: [FadeIn(ring2)], 0.6),
            "picks the drawer",
            (lambda: [glow(box[0], GOLD_M, 1.01)], 0.7),
            "pick the place",
            (lambda: [LaggedStart(*[x[1].animate(rate_func=there_and_back).set_color(GREEN_M) for x in r], lag_ratio=0.2)], 1.0),
            "lifts out one run",
            (lambda: [*self.cap("one drawer, one run", YELLOW_M, 28), *[a for x in r[1:4] for a in lit(x, GREEN_M)]], 0.8),
        ])
        self.steps("One quick check. A query names A-1001 and payment pay-81723, but no time. One run, or refused? Pause and think.", [
            (lambda: [*self.uncap(), *[a for x in r[1:4] for a in unlit(x)]], 0.4),
            "A query names",
            (lambda: [*self.query("A-1001 and pay-81723, no time", "?", YELLOW_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Refused. The rows are in time order, so an id with no time isn't one run. Without ALLOW FILTERING, CQL says no.", [
            (lambda: [*self.uncap(), *self.verdict("refused, unless ALLOW FILTERING", RED_M)], 0.5),
            "The rows are in time order",
            (lambda: [LaggedStart(*[x[1].animate(rate_func=there_and_back).set_color(GREEN_M) for x in r], lag_ratio=0.2)], 1.0),
            "an id with no time",
            (lambda: [LaggedStart(*[x[0].animate(rate_func=there_and_back).set_stroke(RED_M, 4) for x in r], lag_ratio=0.15),
                      *self.cap("payment_id without created_at: not one run", RED_M)], 1.2),
        ], after=0.5)
        self.play(*self.cap("the partition key picks the drawer; the clustering columns pick the place", YELLOW_M, 24), run_time=0.7)
        self.wait(2.0)
