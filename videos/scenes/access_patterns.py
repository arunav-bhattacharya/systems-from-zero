from sfz import *

SAY.insert(0, (r"\bAP([1-6])\b", r"A P \1"))
SAY.insert(0, (r"\bA-1001\b", "A ten oh one"))
SAY.insert(0, (r"\bM-0042\b", "M forty-two"))
SAY.insert(0, (r"\bpay-81741\b", "pay eight one seven four one"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TX0, TX1 = -6.5, -0.95                      # left: the table, filed by account then time
TCX = (TX0 + TX1) / 2
PARTS = [(2.5, 0.0), (-0.25, -1.85)]        # the two partitions (top, bottom)
HEAD_Y = [2.2, -0.55]
TROW_Y = [[1.72, 1.24, 0.76, 0.28], [-1.03, -1.51]]
RX0, RX1 = -0.3, 6.5                        # right: the list, later the two copies
RCX = (RX0 + RX1) / 2
SH_T, SH_B = 2.5, -0.5                      # the copy filed by shop
SROW_Y = [1.72, 1.24, 0.76, 0.28, -0.2]
PY_T, PY_B = -1.1, -1.85                    # the copy filed by payment id
GAP_X = (TX1 + RX0) / 2                     # the narrow column between the two sides
STRIP_Y, TITLE_Y, CAP_Y, BAR_Y, QY = 3.3, 2.8, -2.4, -2.76, -3.2

TABLE = [[("11-06 23:59", "pay-81655"), ("11-07 08:15", "pay-81701"), ("11-07 09:40", "pay-81720"), ("11-07 10:30", "pay-81730")],
         [("11-07 09:55", "pay-81724"), ("11-07 11:05", "pay-81741")]]
SHOP = [("FAILED", "11-07 09:40", "pay-81720"), ("FAILED", "11-07 09:55", "pay-81724"), ("SETTLED", "11-06 23:59", "pay-81655"),
        ("SETTLED", "11-07 08:15", "pay-81701"), ("SETTLED", "11-07 11:05", "pay-81741")]
SHOP_FROM = [(0, 2), (1, 0), (0, 0), (0, 1), (1, 1)]   # where each shop-copy row comes from in the table
APS = [("AP1", "an account's payments, newest first", "very often"), ("AP2", "one payment, by its id", "very often"),
       ("AP3", "one shop, one status, a time window", "often"), ("AP4", "has this request come before?", "every payment"),
       ("AP5", "a transfer between two accounts", "often"), ("AP6", "the refunds of a payment", "rarely")]
STRIP = ["AP1  account, newest first", "AP2  one payment, by id", "AP3  shop, status, time"]


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


def dot_to(a, b, color=YELLOW_M, rt=0.8):
    d = Dot(radius=0.08, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


# ---- the pieces ----
def part_box(p, color=GREY_B):
    top, bot = PARTS[p]
    return RoundedRectangle(corner_radius=0.12, width=TX1 - TX0, height=top - bot, stroke_color=color, stroke_width=2.5).set_fill(
        fillc(color, 0.08), 1).move_to([TCX, (top + bot) / 2, 0])


def head(s, x, y, color=GREY_B, size=19):
    return left_at(T(s, size, color), x, y)


def row_rect(x0, x1, y):
    return RoundedRectangle(corner_radius=0.08, width=x1 - x0, height=0.4, stroke_color=GREY_C, stroke_width=1.5).set_fill(BLACK, 1).move_to(
        [(x0 + x1) / 2, y, 0])


def trow(p, i):
    tm, pid = TABLE[p][i]
    y = TROW_Y[p][i]
    return VGroup(row_rect(TX0 + 0.15, TX1 - 0.15, y), left_at(M(tm, 20), TX0 + 0.45, y), left_at(M(pid, 20), TX0 + 2.75, y))


def srow(i):
    st, tm, pid = SHOP[i]
    y = SROW_Y[i]
    return VGroup(row_rect(RX0 + 0.15, RX1 - 0.15, y), left_at(M(st, 20), RX0 + 0.4, y), left_at(M(tm, 20), RX0 + 1.95, y),
                  left_at(M(pid, 20), RX0 + 4.3, y))


def prow(s):
    y = (PY_T + PY_B) / 2
    return VGroup(row_rect(RX0 + 0.15, RX1 - 0.15, y), left_at(M(s, 20), RX0 + 0.4, y))


def lit(r, color):
    return [r[0].animate.set_stroke(color, 3).set_fill(fillc(color, 0.3), 1), *[t.animate.set_color(color) for t in r[1:]]]


def unlit(r):
    return [r[0].animate.set_stroke(GREY_C, 1.5).set_fill(BLACK, 1), *[t.animate.set_color(WHITE) for t in r[1:]]]


def flash(rows, color=RED_M, lag=0.15):
    return LaggedStart(*[r[0].animate(rate_func=there_and_back).set_stroke(color, 4).set_fill(fillc(color, 0.35), 1) for r in rows],
                       lag_ratio=lag)


def keep(rows, color, lag=0.3):
    return LaggedStart(*[AnimationGroup(*lit(r, color)) for r in rows], lag_ratio=lag)


def product(x, y_plank, color, tin=False):
    if tin:
        b = RoundedRectangle(corner_radius=0.16, width=0.42, height=0.5, stroke_color=color, stroke_width=2)
    else:
        b = RoundedRectangle(corner_radius=0.05, width=0.42, height=0.58, stroke_color=color, stroke_width=2)
    b.set_fill(fillc(color, 0.45), 1)
    return b.move_to([x, y_plank + b.height / 2 + 0.02, 0])


def tag(p):
    c = Circle(radius=0.13, stroke_color=RED_M, stroke_width=2).set_fill(fillc(RED_M, 0.6), 1)
    return VGroup(c, T("%", 14, WHITE).move_to(c)).move_to(p.get_corner(UR) + np.array([-0.02, -0.02, 0]))


def aisle(p):
    plank_y = [1.0, -1.4][p]
    plank = Line([TX0 + 0.25, plank_y, 0], [TX1 - 0.25, plank_y, 0], stroke_width=3, color=GREY_B)
    cols = [GOLD_M, YELLOW_M, GOLD_M, TEAL_M, YELLOW_M, GOLD_M, TEAL_M] if p == 0 else [BLUE_M, PURPLE_M, GREY_B, BLUE_M, PURPLE_M, GREY_B, BLUE_M]
    prods = VGroup(*[product(TX0 + 0.55 + k * 0.7, plank_y, cols[k], tin=(p == 1)) for k in range(7)])
    tags = VGroup(*[tag(prods[k]) for k in ([2, 5] if p == 0 else [4])])
    return plank, prods, tags


def mark(ok, at):
    if ok is None:
        return T("?", 26, YELLOW_M).move_to(at)
    return tick(ok, 0.13).move_to(at)


def strip_chip(k):
    x = [-4.45, 0.0, 4.45][k]
    r = RoundedRectangle(corner_radius=0.08, width=4.1, height=0.46, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1).move_to([x, STRIP_Y, 0])
    return VGroup(r, left_at(T(STRIP[k], 19), x - 1.85, STRIP_Y))


def strip_mark_at(k):
    return np.array([[-4.45, 0.0, 4.45][k] + 1.75, STRIP_Y, 0])


class AccessPatterns(Base):
    """model-02, section 1. A café owner's question ("my failed payments from this morning") is refused by a store on
    40 machines. A supermarket: aisles by kind (partitions), the sign (partition key: account), the order along the
    shelf (sort key: time); key lookup, range read, scan. Write the questions down (access patterns AP1 to AP6) and hold
    each to "lookup or range read". AP1 is a range read (read 2, return 2); AP2 and AP3 are scans (read 6, return 1).
    A stand by the door: a second copy filed by payment id (read 1) and one filed by shop, status, time (AP3: read 2,
    return 2). The no-gaps rule ("any status since 09:00" reads all five), filters cost what they read, one payment is
    three item writes, the price of rigidity, the moral, and a check (all FAILED payments: a scan of everything)."""

    def cap(self, s, color=GREY_B, size=22):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        fit(new, 13.0)
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

    def set_mark(self, k, ok):
        new = mark(ok, strip_mark_at(k))
        old, self.marks[k] = self.marks[k], new
        if old is None:
            return [Create(new) if ok is not None else FadeIn(new)]
        return [FadeOut(old), Create(new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar, rate_func=linear), run_time=secs)

    def all_rows(self):
        return [r for p in self.rows for r in p]

    def construct(self):
        self.capm = self.qm = self.vm = None
        self.marks = [None, None, None]
        self.title_card("Why did the bigger store say no?", "write the questions down, then choose the keys")

        # ---------------- scene 1: the refused question ----------------
        who = T("a café owner, on the phone", 22, GREY_B).move_to([0, 3.15, 0])
        bub = RoundedRectangle(corner_radius=0.2, width=10.2, height=1.0, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1)
        bub.move_to([0, 2.3, 0])
        bub_t = T("“Show me my failed payments from this morning.”", 30).move_to(bub)
        self.steps("A café owner phones support. “Show me my failed payments from this morning.”", [
            (lambda: [FadeIn(who)], 0.5),
            "Show me",
            (lambda: [FadeIn(VGroup(bub, bub_t), shift=0.15 * DOWN)], 0.8),
        ])
        lw = T("last week", 24, GREY_B).move_to([-3.6, 1.15, 0])
        one = VGroup(RoundedRectangle(corner_radius=0.1, width=1.9, height=1.2, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1),
                     T("one machine", 20)).move_to([-3.6, -0.05, 0])
        one[1].move_to(one[0])
        fast = T("a few milliseconds", 24, GREEN_M).move_to([-3.6, -1.3, 0])
        self.steps("Last week, on a database on one machine, the same question came back in a few milliseconds.", [
            (lambda: [FadeIn(lw), FadeIn(one, shift=0.1 * UP)], 0.8),
            "came back",
            (lambda: [dot_to(bub.get_bottom() + np.array([-3.0, -0.05, 0]), one.get_top() + 0.08 * UP, YELLOW_M, 0.6)], 0.85),
            (lambda: [FadeIn(fast, shift=0.1 * UP)], 0.5),
        ])
        tw = T("this week: a store on 40 machines", 24, GREY_B).move_to([3.3, 1.15, 0])
        grid = VGroup(*[Square(0.26, stroke_color=GREY_B, stroke_width=1.8).set_fill(fillc(GREY_B, 0.15), 1).move_to(
            [3.3 + (c - 3.5) * 0.37, 0.55 - r * 0.37, 0]) for r in range(5) for c in range(8)])
        err = VGroup(RoundedRectangle(corner_radius=0.1, width=6.2, height=0.7, stroke_color=RED_M, stroke_width=3).set_fill(fillc(RED_M), 1),
                     fit(T("error: this query “might involve data filtering”", 20, RED_M), 5.8)).move_to([3.3, -1.55, 0])
        err[1].move_to(err[0])
        self.steps("This week the data lives in a new store spread over 40 machines, and the screen shows an error: "
                   "this query “might involve data filtering”.", [
            (lambda: [FadeIn(tw), LaggedStart(*[FadeIn(s, scale=0.7) for s in grid], lag_ratio=0.02)], 1.4),
            "shows an error",
            (lambda: [FadeIn(err, shift=0.1 * UP)], 0.7),
        ])
        qm = T("?", 72, YELLOW_M).move_to([0, -0.2, 0])
        self.steps("That's the store's polite way of saying: I'd have to read everything, and I'd rather not. "
                   "So why would a bigger store refuse a small question?", [
            "I'd have to",
            (lambda: [flash(list(grid), RED_M, 0.02)], 1.4),
            "So why",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the supermarket ----------------
        boxes = [part_box(0), part_box(1)]
        signs = [head("aisle: pasta", TX0 + 0.25, HEAD_Y[0], WHITE, 20), head("aisle: tins", TX0 + 0.25, HEAD_Y[1], WHITE, 20)]
        a1, a2 = aisle(0), aisle(1)
        self.steps("Think of a supermarket. Its shelves are arranged by kind, so all the pasta is in one aisle, and all the tins in another.", [
            (lambda: [FadeOut(VGroup(who, bub, bub_t, lw, one, fast, tw, grid, err, qm))], 0.7),
            "Its shelves",
            (lambda: [FadeIn(boxes[0]), FadeIn(signs[0]), Create(a1[0]), LaggedStart(*[FadeIn(p, shift=0.1 * DOWN) for p in a1[1]], lag_ratio=0.1)], 1.2),
            "and all the tins",
            (lambda: [FadeIn(boxes[1]), FadeIn(signs[1]), Create(a2[0]), LaggedStart(*[FadeIn(p, shift=0.1 * DOWN) for p in a2[1]], lag_ratio=0.1)], 1.2),
        ])
        walker = Dot(radius=0.1, color=YELLOW_M).move_to([TX0 + 0.3, 0.45, 0])
        path = VMobject().set_points_as_corners([[TX0 + 0.3, 0.45, 0], [TX1 - 0.45, 0.45, 0], [TX1 - 0.45, -1.68, 0], [TX0 + 0.3, -1.68, 0]])
        offer = T("everything on special offer?", 24, RED_M).move_to([RCX, 1.0, 0])
        self.steps("Ask for pasta, and you walk to one aisle. Ask for everything on special offer, and you walk every aisle, "
                   "because the shelves aren't arranged by offer.", [
            (lambda: [glow(boxes[0], YELLOW_M, 1.02)], 0.9),
            "Ask for everything",
            (lambda: [FadeIn(offer), LaggedStart(*[FadeIn(t, scale=0.4) for t in [*a1[2], *a2[2]]], lag_ratio=0.3)], 1.0),
            "and you walk every",
            (lambda: [FadeIn(walker)], 0.2),
            (lambda: [MoveAlongPath(walker, path, rate_func=linear)], 3.2),
            (lambda: [FadeOut(walker)], 0.3),
        ])
        maps = [T("aisle  =  partition: one machine's slice", 22, BLUE_M), T("sign over the aisle  =  partition key: the account", 22, GOLD_M),
                T("order along the shelf  =  sort key: the time", 22, GREEN_M)]
        for k, m in enumerate(maps):
            fit(m, RX1 - RX0 - 0.2).move_to([RCX, 1.6 - k * 0.85, 0])
        self.steps("The new store keeps payments the same way. Each machine holds one slice of the data, called a partition. That's an aisle.", [
            (lambda: [FadeOut(offer), *[FadeOut(t) for t in [*a1[2], *a2[2]]]], 0.6),
            "called a partition",
            (lambda: [FadeIn(maps[0], shift=0.1 * LEFT), *[b.animate.set_stroke(BLUE_M) for b in boxes]], 0.8),
            "That's an aisle",
            (lambda: [glow(boxes[0], BLUE_M, 1.02), glow(boxes[1], BLUE_M, 1.02)], 0.8),
        ])
        heads = [head("partition A-1001", TX0 + 0.25, HEAD_Y[0], GOLD_M), head("partition A-2002", TX0 + 0.25, HEAD_Y[1], GOLD_M)]
        self.steps("Every payment has an address in two parts. The partition key says which partition, like the sign over the aisle. "
                   "Here, it's the account.", [
            "The partition key",
            (lambda: [FadeIn(maps[1], shift=0.1 * LEFT), Indicate(signs[0], color=GOLD_M), Indicate(signs[1], color=GOLD_M)], 1.0),
            "Here, it's the account",
            (lambda: [swap(signs[0], heads[0]), swap(signs[1], heads[1])], 0.9),
        ])
        self.rows = [[trow(0, i) for i in range(4)], [trow(1, i) for i in range(2)]]
        ttl = VGroup(T("partition key: account", 20, GOLD_M), T("sort key: time", 20, GREEN_M)).arrange(RIGHT, buff=0.45)
        left_at(ttl, TX0 + 0.05, TITLE_Y)
        self.steps("The sort key says where inside it, like the order along the shelf. Here, it's the time.", [
            (lambda: [FadeIn(maps[2], shift=0.1 * LEFT)], 0.7),
            "Here, it's the time",
            (lambda: [FadeOut(VGroup(a1[0], a1[1], a2[0], a2[1])), LaggedStart(*[FadeIn(r, shift=0.1 * UP) for r in self.all_rows()], lag_ratio=0.12),
                      FadeIn(ttl)], 1.3),
        ])
        r = self.rows
        self.steps("So a question can go three ways. Give the whole address, and the store finds one item: a key lookup.", [
            (lambda: [FadeOut(VGroup(*maps))], 0.6),
            "Give the whole",
            (lambda: [*lit(r[0][2], GREEN_M), *self.cap("key lookup: the whole address, one item", GREEN_M)], 0.8),
        ])
        self.steps("Give the account and a range of times: one run of neighbours, a range read. Anything else is a scan: read everything, keep a few.", [
            (lambda: [*unlit(r[0][2])], 0.3),
            "and a range",
            (lambda: [keep([r[0][1], r[0][2]], GREEN_M, 0.4), *self.cap("range read: one run of neighbours", GREEN_M)], 0.8),
            "Anything else",
            (lambda: [*unlit(r[0][1]), *unlit(r[0][2]), *self.cap("scan: read everything, keep a few", RED_M)], 0.5),
            (lambda: [flash(self.all_rows(), RED_M, 0.12)], 1.6),
        ])

        # ---------------- scene 3: write the questions down ----------------
        qbox = RoundedRectangle(corner_radius=0.1, width=13.0, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([0, QY, 0])
        self.steps("Now the café owner's question. It names a shop, but the address starts with the account. "
                   "So the store has to read every partition.", [
            (lambda: [*self.uncap(), FadeIn(qbox)], 0.5),
            (lambda: self.query("the café owner: shop M-0042, FAILED, since 09:00", "?", YELLOW_M), 0.6),
            "starts with the account",
            (lambda: [Indicate(heads[0], color=GOLD_M), Indicate(heads[1], color=GOLD_M), Indicate(ttl[0], color=GOLD_M)], 0.9),
            "has to read",
            (lambda: [flash(self.all_rows(), RED_M, 0.12)], 1.3),
            (lambda: self.verdict("scan: every partition", RED_M), 0.4),
        ])
        card = RoundedRectangle(corner_radius=0.14, width=RX1 - RX0, height=4.55, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        card.move_to([RCX, 0.27, 0])
        card_t = head("the app's questions, written down first", RX0 + 0.3, 2.2, WHITE, 21)
        lines = VGroup()
        for k, (ap, q, rate) in enumerate(APS):
            y = 1.62 - k * 0.55
            lines.add(VGroup(left_at(M(ap, 19, GREY_B), RX0 + 0.3, y), left_at(fit(T(q, 19), 4.1), RX0 + 0.95, y),
                             right_at(T(rate, 17, GREY_B), RX1 - 0.3, y)))
        self.steps("So, before you choose any key, write down every question the app will ask, and how often.", [
            (lambda: self.query("", ""), 0.4),
            "write down",
            (lambda: [FadeIn(card), FadeIn(card_t)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(VGroup(l[0], l[1]), shift=0.1 * RIGHT) for l in lines], lag_ratio=0.25)], 1.6),
            "and how often",
            (lambda: [LaggedStart(*[FadeIn(l[2]) for l in lines], lag_ratio=0.15)], 0.9),
        ])
        self.steps("Each line is called an access pattern. The app has six. We'll check the first three.", [
            (lambda: self.cap("each line: an access pattern", WHITE, 24), 0.6),
            "We'll check",
            (lambda: [*[l.animate.set_opacity(0.3) for l in lines[3:]]], 0.7),
        ])

        def hl(k, color=YELLOW_M):
            return [lines[k][1].animate(rate_func=there_and_back).set_color(color)]

        self.steps("AP1: an account's payments, newest first. AP2: one payment, by its id. AP3: a shop's payments with one status, "
                   "in a time window. That's the café owner's.", [
            (lambda: self.uncap(), 0.3),
            (lambda: hl(0), 0.9),
            "AP2",
            (lambda: hl(1), 0.9),
            "AP3",
            (lambda: hl(2), 0.9),
            "That's the café",
            (lambda: [lines[2][1].animate.set_color(GOLD_M)], 0.6),
        ])
        rule = T("the rule: a key lookup or a range read, never a scan", 21, YELLOW_M)
        fit(rule, RX1 - RX0 - 0.4).move_to([RCX, -1.62, 0])
        self.steps("The rule: every pattern must be a key lookup or a range read. Never a scan.", [
            "The rule",
            (lambda: [FadeIn(rule, shift=0.1 * UP)], 0.6),
            "Never a scan",
            (lambda: [Indicate(rule, color=YELLOW_M, scale_factor=1.05)], 0.8),
        ])

        # ---------------- scene 4: check the three ----------------
        chips = [strip_chip(k) for k in range(3)]
        self.steps("Check them against our table, filed by account, then time. Which can it answer without a scan? "
                   "Pause and guess.", [
            (lambda: [*[ReplacementTransform(lines[k][1].copy(), chips[k]) for k in range(3)], FadeOut(VGroup(card, card_t, lines, rule))], 1.0),
            "filed by account",
            (lambda: [glow(boxes[0], BLUE_M, 1.02), glow(boxes[1], BLUE_M, 1.02)], 0.8),
            "Which can it",
            (lambda: [*self.set_mark(0, None), *self.set_mark(1, None), *self.set_mark(2, None)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        up = Arrow([GAP_X, TROW_Y[0][3] - 0.1, 0], [GAP_X, TROW_Y[0][2] + 0.15, 0], buff=0, stroke_width=4, color=GREEN_M,
                   max_tip_length_to_length_ratio=0.3, max_stroke_width_to_length_ratio=12)
        self.steps("AP1, account A-1001, newest first. Go to its partition, start at the end, and step back two. "
                   "A range read: read two, return two.", [
            (lambda: [*self.uncap(), *self.query("AP1: account A-1001, newest first, limit 2"), glow(chips[0][0], YELLOW_M, 1.02)], 0.6),
            "Go to its partition",
            (lambda: [glow(boxes[0], GOLD_M, 1.02), Indicate(heads[0], color=GOLD_M)], 0.8),
            "start at the end",
            (lambda: [*lit(r[0][3], GREEN_M)], 0.5),
            "step back two",
            (lambda: [GrowArrow(up), *lit(r[0][2], GREEN_M)], 0.6),
            "A range read",
            (lambda: [*self.verdict("range read: read 2, return 2", GREEN_M), *self.set_mark(0, True)], 0.6),
        ])
        self.steps("AP2 gives a payment id, which isn't in the address. So the store reads every item: read six, return one. "
                   "In a real table, that's all of them.", [
            (lambda: [FadeOut(up), *unlit(r[0][3]), *unlit(r[0][2]), *self.query("AP2: payment pay-81724"), glow(chips[1][0], YELLOW_M, 1.02)], 0.6),
            "So the store reads",
            (lambda: [LaggedStart(*[AnimationGroup(*lit(x, GREEN_M if x is r[1][0] else RED_M)) for x in self.all_rows()], lag_ratio=0.3)], 1.8),
            "read six",
            (lambda: [*self.verdict("scan: read 6, return 1", RED_M), *self.set_mark(1, False)], 0.6),
            "In a real table",
            (lambda: self.cap("in a real table: every item", RED_M), 0.5),
        ])
        self.steps("AP3 names a shop: also a scan.", [
            (lambda: [*self.uncap(), *[a for x in self.all_rows() for a in unlit(x)], *self.query("AP3: shop M-0042, FAILED, since 09:00"),
                      glow(chips[2][0], YELLOW_M, 1.02)], 0.6),
            (lambda: [flash(self.all_rows(), RED_M, 0.1)], 1.0),
            (lambda: [*self.verdict("scan", RED_M), *self.set_mark(2, False)], 0.5),
        ])

        # ---------------- scene 5: the stand by the door ----------------
        stand = RoundedRectangle(corner_radius=0.12, width=3.4, height=1.7, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1)
        stand.move_to([RCX, 1.1, 0])
        stand_t = T("the stand by the door", 20, TEAL_M).next_to(stand, UP, buff=0.15)
        sp = VGroup(*[product(RCX - 0.8 + k * 0.8, 0.55, c) for k, c in enumerate([GOLD_M, TEAL_M, BLUE_M])])
        stags = VGroup(*[tag(p) for p in sp])
        self.steps("Back to the supermarket. Shoppers keep asking for offers, so the shop adds a stand by the door: "
                   "the same products, arranged a second way. Now every delivery stocks two places.", [
            (lambda: [*self.query("", "")], 0.4),
            "so the shop adds",
            (lambda: [FadeIn(stand), FadeIn(stand_t)], 0.7),
            "the same products",
            (lambda: [LaggedStart(*[FadeIn(VGroup(p, t), shift=0.1 * DOWN) for p, t in zip(sp, stags)], lag_ratio=0.3)], 0.9),
            "Now every delivery",
            (lambda: [*self.cap("every delivery now stocks two places", TEAL_M),
                      dot_to(np.array([GAP_X, -2.0, 0]), boxes[1].get_right() + np.array([-0.4, -0.3, 0])),
                      dot_to(np.array([GAP_X, -2.0, 0]), stand.get_bottom() + 0.1 * UP)], 1.0),
        ])
        pay_t = head("copy 2: partition key payment id", RX0 + 0.05, PY_T + 0.3, PURPLE_M, 20)
        pay_b = RoundedRectangle(corner_radius=0.12, width=RX1 - RX0, height=PY_T - PY_B, stroke_color=PURPLE_M, stroke_width=2.5).set_fill(
            fillc(PURPLE_M, 0.08), 1).move_to([RCX, (PY_T + PY_B) / 2, 0])
        self.prow = prow("pay-81724: A-2002, 11-07 09:55")
        self.steps("Do the same with the data. Add a second copy, filed by payment id. AP2 now gives that copy's whole address: "
                   "a key lookup, read one.", [
            (lambda: [FadeOut(VGroup(stand, stand_t, sp, stags)), *self.uncap()], 0.6),
            "Add a second copy",
            (lambda: [FadeIn(pay_b), FadeIn(pay_t)], 0.7),
            (lambda: [ReplacementTransform(r[1][0].copy(), self.prow)], 0.8),
            "AP2 now",
            (lambda: [*self.query("AP2: payment pay-81724"), glow(chips[1][0], YELLOW_M, 1.02)], 0.6),
            "a key lookup",
            (lambda: [*lit(self.prow, GREEN_M), *self.verdict("key lookup on the copy: read 1", GREEN_M), *self.set_mark(1, True)], 0.7),
        ])
        sh_t = VGroup(T("copy 1: partition key shop", 20, TEAL_M), T("sort key: status, time", 20, GREEN_M)).arrange(RIGHT, buff=0.4)
        left_at(sh_t, RX0 + 0.05, TITLE_Y)
        sh_b = RoundedRectangle(corner_radius=0.12, width=RX1 - RX0, height=SH_T - SH_B, stroke_color=TEAL_M, stroke_width=2.5).set_fill(
            fillc(TEAL_M, 0.08), 1).move_to([RCX, (SH_T + SH_B) / 2, 0])
        sh_h = head("partition M-0042", RX0 + 0.25, HEAD_Y[0], TEAL_M)
        self.srows = [srow(i) for i in range(5)]
        ghosts = [r[p][i].copy() for p, i in SHOP_FROM]
        self.steps("And a copy for the café owner, filed by shop, then status, then time.", [
            (lambda: [*unlit(self.prow), *self.query("", ""), FadeIn(sh_b), FadeIn(sh_t), FadeIn(sh_h)], 0.8),
            "filed by shop",
            (lambda: [LaggedStart(*[ReplacementTransform(g, s) for g, s in zip(ghosts, self.srows)], lag_ratio=0.2)], 2.0),
        ])
        s = self.srows
        self.steps("Her question picks shop M-0042, jumps to the failed run, and trims it to this morning: read two, return two. "
                   "Her answer arrives before her coffee gets cold.", [
            (lambda: [*self.query("AP3: shop M-0042, FAILED, since 09:00"), glow(chips[2][0], YELLOW_M, 1.02)], 0.6),
            "picks shop",
            (lambda: [glow(sh_b, TEAL_M, 1.02), Indicate(sh_h, color=TEAL_M)], 0.8),
            "jumps to",
            (lambda: [keep([s[0], s[1]], GREEN_M, 0.4)], 0.8),
            "read two",
            (lambda: [*self.verdict("range read: read 2, return 2", GREEN_M), *self.set_mark(2, True)], 0.6),
            "Her answer",
            (lambda: [Indicate(chips[2][1], color=GOLD_M, scale_factor=1.06)], 0.9),
        ])
        self.steps("Here the supermarket picture breaks. A tin can only sit in one place. Data can be copied as often as you like.", [
            (lambda: self.cap("where the supermarket breaks", GREY_B), 0.5),
            "A tin can only",
            (lambda: self.cap("a tin sits in one place; data can be copied as often as you like", WHITE), 0.6),
            "Data can be copied",
            (lambda: [glow(sh_b, TEAL_M, 1.02), glow(pay_b, PURPLE_M, 1.02)], 0.9),
        ])
        self.steps("DynamoDB, a database Amazon runs for its customers, calls this copy a global secondary index, "
                   "and keeps it up to date for you.", [
            (lambda: self.cap("DynamoDB, a database Amazon runs for its customers", GREY_B), 0.5),
            "calls this copy",
            (lambda: self.cap("DynamoDB: a global secondary index, kept up to date for you", WHITE), 0.6),
        ])
        self.steps("In Cassandra, a free database companies run on their own machines, it's another table, and your code writes it.", [
            (lambda: self.cap("Cassandra, a free database companies run on their own machines", GREY_B), 0.5),
            "it's another table",
            (lambda: self.cap("Cassandra: another table, and your code writes it", WHITE), 0.6),
        ])

        # ---------------- scene 6: any status since nine ----------------
        late = [s[0], s[1], s[4]]
        early = [s[2], s[3]]
        b1 = Brace(VGroup(s[0][0], s[1][0]), direction=LEFT, buff=0.25, color=YELLOW_M)
        b2 = Brace(s[4][0], direction=LEFT, buff=0.25, color=YELLOW_M)
        self.steps("So the shop copy holds shop, status and time. Any question about those three is fast now, right? "
                   "Try shop M-0042, any status, since nine.", [
            (lambda: [*self.uncap(), *unlit(s[0]), *unlit(s[1]), *self.query("", "")], 0.5),
            "holds shop",
            (lambda: [Indicate(sh_t[0], color=TEAL_M), Indicate(sh_t[1], color=GREEN_M)], 1.0),
            "Try shop",
            (lambda: self.query("shop M-0042, any status, since 09:00", "?", YELLOW_M), 0.6),
        ])
        self.steps("Items are sorted by status first, then time, so the ones after nine sit in two runs, with older ones in between.", [
            "sorted by status",
            (lambda: [Indicate(sh_t[1], color=GREEN_M)], 0.8),
            "the ones after nine",
            (lambda: [keep(late, YELLOW_M, 0.3)], 0.9),
            "two runs",
            (lambda: [GrowFromCenter(b1), GrowFromCenter(b2)], 0.6),
            "older ones",
            (lambda: [*[x.animate.set_opacity(0.35) for x in early]], 0.6),
        ])
        self.steps("Not one run, so not one read: the store reads all five items to keep three.", [
            (lambda: [*[x.animate.set_opacity(1) for x in early]], 0.4),
            "the store reads",
            (lambda: [LaggedStart(*[x[0].animate(rate_func=there_and_back).set_stroke(RED_M, 5) for x in s], lag_ratio=0.25)], 1.4),
            (lambda: self.verdict("scan of the shop's partition: read 5, keep 3", RED_M), 0.5),
        ])
        self.steps("That's the no-gaps rule: the sort key is used from left to right.", [
            (lambda: self.cap("no gaps: the sort key is used from left to right", YELLOW_M, 24), 0.6),
            "from left to right",
            (lambda: [Indicate(sh_t[1], color=GREEN_M, scale_factor=1.08)], 0.8),
        ])
        self.steps("And a filter won't rescue it. It runs after the read, and you pay for every item read, not every item returned.", [
            "It runs after",
            (lambda: self.cap("a filter runs after the read", WHITE), 0.5),
            "and you pay",
            (lambda: [*self.cap("you pay for every item read, not every item returned", RED_M),
                      LaggedStart(*[x[0].animate(rate_func=there_and_back).set_stroke(RED_M, 5) for x in s], lag_ratio=0.2)], 1.2),
        ])

        # ---------------- scene 7: the bill ----------------
        newp = VGroup(RoundedRectangle(corner_radius=0.08, width=1.9, height=0.46, stroke_color=YELLOW_M, stroke_width=2.5).set_fill(BLACK, 1),
                      M("pay-81741", 20, YELLOW_M)).move_to([GAP_X, CAP_Y, 0])
        newp[1].move_to(newp[0])
        prow2 = prow("pay-81741: A-2002, 11-07 11:05")
        src = newp.get_top()
        self.steps("Now the bill. When payment pay-81741 arrived, it went into the table and into both copies. One payment, three item writes.", [
            (lambda: [*self.uncap(), FadeOut(b1), FadeOut(b2), *[a for x in late for a in unlit(x)], *self.query("a new payment arrives: pay-81741")], 0.6),
            "When payment",
            (lambda: [FadeIn(newp, shift=0.1 * UP)], 0.5),
            "into the table",
            (lambda: [dot_to(src, r[1][1][0].get_right() + 0.05 * RIGHT), *lit(r[1][1], YELLOW_M)], 0.8),
            "both copies",
            (lambda: [dot_to(src, s[4][0].get_left() + 0.05 * LEFT), dot_to(src, self.prow[0].get_left() + 0.05 * LEFT),
                      *lit(s[4], YELLOW_M), swap(self.prow, prow2)], 0.9),
            (lambda: [*lit(prow2, YELLOW_M)], 0.3),
            "One payment",
            (lambda: self.verdict("1 write = 3 item writes", GOLD_M), 0.6),
        ])
        self.prow = prow2
        self.steps("A copy nobody asks for is a shelf you stock at every delivery, for nobody. So add a copy only for a question on your list.", [
            (lambda: [FadeOut(newp), *self.cap("a copy nobody asks for: a shelf stocked for nobody", GREY_B)], 0.6),
            "So add a copy",
            (lambda: [*self.cap("add a copy only for a question on your list", WHITE), glow(chips[1][0], YELLOW_M, 1.02),
                      glow(chips[2][0], YELLOW_M, 1.02)], 0.8),
        ])
        self.steps("And the list has a price: a new question next quarter can mean a new copy, or rewriting old items. "
                   "In exchange, the questions on your list stay fast at any size.", [
            (lambda: [*[a for x in (r[1][1], s[4], self.prow) for a in unlit(x)], *self.query("", "")], 0.5),
            "a new question",
            (lambda: self.cap("the price: a new question can mean a new copy, or rewriting old items", WHITE), 0.6),
            "In exchange",
            (lambda: self.cap("in exchange: the questions on your list stay fast at any size", GREEN_M), 0.6),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So why did the bigger store say no? Its address started with the account, and the question named a shop.", [
            (lambda: self.cap("why did the bigger store say no?", WHITE), 0.5),
            "Its address",
            (lambda: [Indicate(heads[0], color=GOLD_M), Indicate(heads[1], color=GOLD_M), Indicate(ttl[0], color=GOLD_M)], 0.9),
            "named a shop",
            (lambda: [Indicate(chips[2][1], color=GOLD_M, scale_factor=1.06)], 0.8),
        ])
        self.steps("The fix was a second copy, filed by shop, planned before the first payment arrived. "
                   "Write the questions down, then choose the keys.", [
            "The fix was",
            (lambda: [glow(sh_b, TEAL_M, 1.02), Indicate(sh_h, color=TEAL_M)], 0.9),
            "Write the questions",
            (lambda: [*self.cap("write the questions down, then choose the keys", YELLOW_M, 30),
                      LaggedStart(*[glow(c[0], GREEN_M, 1.02) for c in chips], lag_ratio=0.3)], 1.0),
        ], after=0.6)
        self.steps("One quick check. All failed payments, at any shop. Key lookup, range read, or scan? Pause and think.", [
            (lambda: self.uncap(), 0.4),
            "All failed",
            (lambda: self.query("all FAILED payments, any shop", "?", YELLOW_M), 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        everything = [*self.all_rows(), *s, self.prow]
        self.steps("A scan of everything. Status is never a partition key, so the store can't pick a partition.", [
            (lambda: [*self.uncap(), flash(everything, RED_M, 0.08)], 1.6),
            (lambda: self.verdict("scan of everything", RED_M), 0.4),
            "Status is never",
            (lambda: self.cap("status is never a partition key", RED_M, 24), 0.6),
        ], after=0.5)
        self.play(*self.cap("write the questions down, then choose the keys", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
