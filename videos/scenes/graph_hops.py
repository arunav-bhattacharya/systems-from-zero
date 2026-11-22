from sfz import *

for n in "12345":
    SAY.insert(0, (rf"\bA-310{n}'s\b", f"A thirty-one oh {n}'s"))
    SAY.insert(0, (rf"\bA-310{n}\b", f"A thirty-one oh {n}"))
SAY.insert(0, (r"\bP-0177\b", "P oh one seven seven"))
SAY.insert(0, (r"\bP-0199\b", "P oh one nine nine"))
SAY.insert(0, (r"\bP-0181\b", "P oh one eight one"))
SAY.insert(0, (r"\bD-77\b", "D seventy-seven"))
SAY.insert(0, (r"\bD-81\b", "D eighty-one"))
SAY.insert(0, (r"\b09:12\b", "nine twelve"))
SAY.insert(0, (r"\bNeo4j\b", "neo four jay"))
SAY.insert(0, (r"\bNeo4j's\b", "neo four jay's"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
LX0, LX1 = -6.6, -1.5                 # left: the link table, later the walk's counts
LCX = (LX0 + LX1) / 2
BX0, BX1 = -1.15, 6.6                 # right: the pinboard
BCX = (BX0 + BX1) / 2
P_T, P_B = 2.85, -2.2
TROW_Y = [1.65, 1.2, 0.75, 0.3, -0.15, -0.6]
CAP_Y, BAR_Y, QY = -2.55, -2.85, -3.25
CORK = "#B07A43"

LINKS = [("A-3101", "D-77"), ("A-3101", "P-0177"), ("A-3102", "D-77"), ("A-3102", "P-0177"), ("A-3102", "P-0199"), ("A-3103", "P-0199")]
POS = {"A-3101": (-0.4, 0.3), "D-77": (0.62, 1.2), "P-0177": (0.62, -0.6), "A-3102": (1.65, 0.3), "P-0199": (2.65, 1.2),
       "A-3103": (3.65, 0.3), "D-81": (4.45, 2.05), "P-0181": (4.75, 0.95), "D-KIOSK": (4.65, -0.75), "A-3104": (5.8, 1.5),
       "A-3105": (5.8, 2.3), "A-1001": (5.8, 0.4), "A-2002": (5.8, -0.3), "A-4002": (5.8, -1.0), "A-4003": (5.8, -1.7)}
USES = [("A-3101", "D-77"), ("A-3101", "P-0177"), ("A-3102", "D-77"), ("A-3102", "P-0177"), ("A-3102", "P-0199"), ("A-3103", "P-0199"),
        ("A-3103", "D-81"), ("A-3103", "P-0181"), ("A-3103", "D-KIOSK"), ("A-3104", "D-81"), ("A-3104", "P-0181"), ("A-3105", "D-81"),
        ("A-1001", "D-KIOSK"), ("A-2002", "D-KIOSK"), ("A-4002", "D-KIOSK"), ("A-4003", "D-KIOSK")]
SHOP = ["A-1001", "A-2002", "A-4002", "A-4003"]


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


def framed(x0, x1, top, bot, color, a=0.08, sw=2.5):
    return RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=sw).set_fill(
        fillc(color, a), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    d = Dot(radius=0.07, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))


# ---- the pieces ----
def card(k):
    """An account photo (a box) or an identifier pin (a pill)."""
    x, y = POS[k]
    acc = k.startswith("A-")
    if acc:
        b = RoundedRectangle(corner_radius=0.06, width=0.95, height=0.48, stroke_color=WHITE, stroke_width=2.5).set_fill("#101010", 1)
    else:
        b = RoundedRectangle(corner_radius=0.18, width=0.9, height=0.36, stroke_color=GREY_B, stroke_width=2).set_fill(fillc(GREY_B, 0.25), 1)
    lab = M("kiosk" if k == "D-KIOSK" else k, 15 if acc else 14, WHITE if acc else GREY_A)
    return VGroup(b.move_to([x, y, 0]), lab.move_to([x, y, 0]))


def tie(a, b, cards):
    pa, pb = ends(cards[a][0], cards[b][0])
    return Line(pa, pb, stroke_width=2, color=CORK)


def trow(i, color=WHITE):
    a, x = LINKS[i]
    y = TROW_Y[i]
    return VGroup(left_at(M(a, 19, color), LX0 + 0.4, y), left_at(M(x, 19, color), LX0 + 2.55, y))


class GraphHops(Base):
    """model-08, section 0. The fraud team flagged A-3101 at 09:12: which accounts share a phone or laptop with it, up to
    three steps out? In a table account_identifier with an index on each column, one step is two lookups and a self join
    (A-3101: D-77, P-0177; then A-3102 twice); two steps is four joins, three is six; with a made-up fan-out of 6, one step
    touches 6 rows, three 216, six about 47,000. A detective's pinboard: photos and strings, followed from one photo.
    Neo4j: nodes, relationships, pointer reads, index-free adjacency. The walk: 2, 2 and 14 paths; 1, 1 and 6 accounts
    (four through a store kiosk). When to use which, what pointers cost, the moral, the Cypher step, and a check."""

    def cap(self, s, color=GREY_B, size=22):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def strip(self, q, v="", vcolor=GREEN_M):
        out = []
        nq = left_at(T(q, 21), -6.3, QY).set_z_index(2) if q else None
        nv = right_at(T(v, 21, vcolor), 6.3, QY).set_z_index(2) if v else None
        for old, new in ((self.qm, nq), (self.vm, nv)):
            if old is not None and new is not None:
                out.append(swap(old, new))
            elif old is not None:
                out.append(FadeOut(old))
            elif new is not None:
                out.append(FadeIn(new, shift=0.1 * UP))
        # the strip's frame shows only while the strip says something
        want = nq is not None or nv is not None
        if want and not self.qbox_on:
            out.insert(0, FadeIn(self.qbox))
        elif not want and self.qbox_on:
            out.insert(0, FadeOut(self.qbox))
        self.qbox_on = want
        self.qm, self.vm = nq, nv
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar, rate_func=linear), run_time=secs)

    def lit_card(self, k, color):
        c = self.cards[k]
        return [c[0].animate.set_stroke(color, 3).set_fill(fillc(color, 0.35), 1)]

    def unlit_card(self, k):
        c = self.cards[k]
        if k.startswith("A-"):
            return [c[0].animate.set_stroke(WHITE, 2.5).set_fill("#101010", 1)]
        return [c[0].animate.set_stroke(GREY_B, 2).set_fill(fillc(GREY_B, 0.25), 1)]

    def lit_tie(self, a, b, color=YELLOW_M):
        return [self.ties[(a, b)].animate.set_stroke(color, 4)]

    def construct(self):
        self.capm = self.qm = self.vm = None
        self.qbox_on = False
        self.qbox = RoundedRectangle(corner_radius=0.1, width=13.2, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([0, QY, 0]).set_z_index(1)
        self.title_card("Follow the strings", "one step in a table, and on a pinboard")

        # ---------------- scene 1: a flagged account ----------------
        flag = VGroup(RoundedRectangle(corner_radius=0.1, width=4.6, height=0.7, stroke_color=RED_M, stroke_width=3).set_fill(fillc(RED_M, 0.2), 1),
                      T("A-3101 · flagged at 09:12", 28, RED_M)).move_to([0, 1.6, 0])
        flag[1].move_to(flag[0])
        q1 = T("which other accounts share a phone or a laptop with it?", 26).move_to([0, 0.5, 0])
        q2 = T("directly, or through up to two other accounts", 24, GREY_B).move_to([0, -0.15, 0])
        self.steps("A Monday morning at the payments company. Overnight, one account, A-3101, made a run of odd payments, and the fraud team, "
                   "the people who look for cheating, flagged it at 09:12.", [
            "one account",
            (lambda: [FadeIn(flag, shift=0.1 * DOWN)], 0.7),
            "flagged it",
            (lambda: [glow(flag[0], RED_M, 1.04)], 0.8),
        ])
        self.steps("Their question: which other accounts share a phone or a laptop with this one, directly or through up to two other accounts? "
                   "People who cheat together often share phones.", [
            "which other accounts",
            (lambda: [FadeIn(q1, shift=0.1 * UP)], 0.7),
            "directly or through",
            (lambda: [FadeIn(q2, shift=0.1 * UP)], 0.6),
        ])
        self.steps("Easy, you'd think. Put the links in a table, index every column, and each lookup takes microseconds. "
                   "Let's see what one step really costs.", [
            "Put the links",
            (lambda: [*self.cap("a table, an index on every column: each lookup takes microseconds", GREY_B)], 0.6),
            "Let's see",
            (lambda: [*self.strip("up to 3 steps out from A-3101", "?", YELLOW_M)], 0.6),
        ])

        # ---------------- scene 2: one step in a table ----------------
        tpanel = framed(LX0, LX1, P_T, P_B, BLUE_M, 0.06)
        ttl = left_at(M("account_identifier", 19, BLUE_M), LX0 + 0.3, 2.5)
        hdr = VGroup(left_at(M("account_id", 16, GREY_B), LX0 + 0.4, 2.08), left_at(M("identifier_id", 16, GREY_B), LX0 + 2.55, 2.08))
        self.rows = [trow(i) for i in range(len(LINKS))]
        more = left_at(T("... one row per link", 17, GREY_C), LX0 + 0.4, -1.05)
        idx = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.08, width=2.2, height=0.44, stroke_color=GOLD_M, stroke_width=2).set_fill(fillc(GOLD_M, 0.2), 1),
                              T(s, 16, GOLD_M)) for s in ("index: account_id", "index: identifier_id")]).arrange(RIGHT, buff=0.2)
        for g in idx:
            g[1].move_to(g[0])
        idx.move_to([LCX, -1.65, 0])
        self.steps("The table has one row per link: this account used this phone or device. Call either one an identifier.", [
            (lambda: [FadeOut(VGroup(flag, q1, q2)), *self.uncap(), FadeIn(tpanel), FadeIn(ttl), FadeIn(hdr)], 0.8),
            "one row per link",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in self.rows], lag_ratio=0.15), FadeIn(more)], 1.2),
            "Call either one",
            (lambda: self.cap("identifier: a phone or a device used to log in", WHITE), 0.6),
        ])
        self.steps("Each column has an index, a sorted list of its values, like the index at the back of a book.", [
            "Each column has an index",
            (lambda: [FadeIn(idx, shift=0.1 * UP)], 0.7),
            "like the index",
            (lambda: self.cap("an index: a sorted list of a column's values, like the back of a book", GOLD_M), 0.6),
        ])
        r = self.rows

        def hl(rs, color):
            return [t.animate.set_color(color) for x in rs for t in x]

        # the query as trips through the table: one small table per trip, joined to the next
        def mini(x, y, color):
            fr = RoundedRectangle(corner_radius=0.06, width=0.62, height=0.44, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.2), 1)
            ln = VGroup(*[Line([-0.22, dy, 0], [0.22, dy, 0], stroke_width=1.5, color=color) for dy in (0.07, -0.07)])
            return VGroup(fr, ln).move_to([x, y, 0])

        TRIP_Y, TX0, TP = [1.5, 0.4, -0.7], 0.75, 0.92
        trips_t = T("the query: one trip through the table per lookup", 19, GREY_B).move_to([BCX, 2.45, 0])
        trip_rows, trip_labs = [], []
        for i, n in enumerate((2, 4, 6)):
            y = TRIP_Y[i]
            icons = [mini(TX0 + TP * k, y, (YELLOW_M if k == 0 else GREEN_M) if i == 0 else BLUE_M) for k in range(n)]
            joins = [Line([TX0 + TP * k + 0.36, y, 0], [TX0 + TP * (k + 1) - 0.36, y, 0], stroke_width=3, color=GOLD_M) for k in range(n - 1)]
            trip_rows.append((icons, joins))
            trip_labs.append(left_at(T(f"{i + 1} step{'s' if i else ''}", 19, GREY_B), BX0 + 0.3, y))
        trip_all = VGroup(trips_t, *trip_labs, *[m for ic, jn in trip_rows for m in ic + jn])
        self.steps("One step crosses the table twice. Look up A-3101's rows through the account index: device D-77 and phone P-0177.", [
            (lambda: [*self.uncap(), *self.strip("step 1, in the table"), FadeIn(trips_t), FadeIn(trip_labs[0])], 0.5),
            "Look up",
            (lambda: [glow(idx[0][0], GOLD_M, 1.05), FadeIn(trip_rows[0][0][0], scale=0.8)], 0.6),
            "device D-77",
            (lambda: hl([r[0], r[1]], YELLOW_M), 0.6),
        ])
        self.steps("Then look up each identifier's other rows: A-3102, twice. That's the table joined with itself.", [
            "Then look up",
            (lambda: [glow(idx[1][0], GOLD_M, 1.05), FadeIn(trip_rows[0][0][1], scale=0.8)], 0.6),
            "A-3102, twice",
            (lambda: hl([r[2], r[3]], GREEN_M), 0.6),
            "joined with itself",
            (lambda: [Create(trip_rows[0][1][0]), *self.cap("a self join: the table joined with itself", WHITE),
                      *self.strip("step 1: two lookups and a join", "A-3102")], 0.6),
        ])
        self.steps("Two steps is four trips through the table, three steps is six. The query grows with every step you allow.", [
            (lambda: [*self.uncap(), *self.strip("2 steps: 4 trips.  3 steps: 6 trips", "", WHITE), FadeIn(trip_labs[1]),
                      LaggedStart(*[FadeIn(m, scale=0.8) for m in trip_rows[1][0]], lag_ratio=0.2), *[Create(j) for j in trip_rows[1][1]]], 0.8),
            "three steps",
            (lambda: [FadeIn(trip_labs[2]), LaggedStart(*[FadeIn(m, scale=0.8) for m in trip_rows[2][0]], lag_ratio=0.15),
                      *[Create(j) for j in trip_rows[2][1]]], 0.8),
            "The query grows",
            (lambda: [LaggedStart(*[glow(m[0], BLUE_M, 1.12) for ic, jn in trip_rows for m in ic], lag_ratio=0.05)], 1.0),
        ])
        fan_t = T("made-up numbers: every step fans out by about 6", 19, GREY_B).move_to([BCX, 2.45, 0])
        fan = [(1, "6", 40), (3, "216", 50), (6, "47,000", 60)]
        base_y = 0.0
        xs = [0.45, 2.45, 4.85]
        bars, blabs = [], []
        for k, (n, s, sz) in enumerate(fan):
            big = T(s, sz, RED_M)
            g = VGroup(big.move_to([xs[k], base_y + 0.2 + big.height / 2, 0]))
            if k == 2:
                g.add(T("about", 22, RED_M).next_to(big, UP, buff=0.12))
            bars.append(g)
            blabs.append(VGroup(T(f"{n} step{'s' if n > 1 else ''}", 19, GREY_B), T("rows touched", 17, GREY_B)).arrange(DOWN, buff=0.08).move_to(
                [xs[k], base_y - 0.5, 0]))
        axis = Line([BX0 + 0.3, base_y, 0], [BX1 - 0.3, base_y, 0], stroke_width=1.5, color=GREY_D)
        self.steps("So does the work. Say each account has 3 identifiers, and each identifier is shared by 2 accounts. "
                   "Those are made-up numbers, to see the shape. Every step fans out by about 6.", [
            (lambda: [*self.uncap(), *hl(r, WHITE), FadeOut(trip_all)], 0.5),
            "Say each account",
            (lambda: [FadeIn(fan_t), Create(axis)], 0.7),
            "made-up numbers",
            (lambda: self.cap("3 identifiers per account × 2 accounts per identifier: about 6 per step (made up)", GREY_B), 0.6),
        ])
        self.steps("One step touches 6 rows. Three steps, 216. Six steps, about 47,000.", [
            (lambda: [FadeIn(bars[0], scale=0.6), FadeIn(blabs[0])], 0.6),
            "Three steps",
            (lambda: [FadeIn(bars[1], scale=0.6), FadeIn(blabs[1])], 0.6),
            "Six steps",
            (lambda: [FadeIn(bars[2], scale=0.5), FadeIn(blabs[2])], 0.8),
        ])
        self.steps("And the database has to guess the size of each join before it runs, and its guesses get worse with every join.", [
            (lambda: self.cap("the database guesses each join's size before it runs; every join makes the guess worse", WHITE), 0.6),
            "get worse",
            (lambda: [Wiggle(bars[2], scale_value=1.03, rotation_angle=0.01 * TAU)], 0.8),
        ])

        # ---------------- scene 3: the pinboard ----------------
        board = framed(BX0, BX1, P_T, P_B, CORK, 0.1)
        btitle = left_at(T("the pinboard", 18, CORK), BX0 + 0.25, 2.55)
        self.cards = {k: card(k) for k in POS}
        self.cards["A-3101"][0].set_stroke(RED_M, 3)
        self.ties = {(a, b): tie(a, b, self.cards) for a, b in USES}
        allties = VGroup(*self.ties.values())
        self.steps("Now store the same links the other way round. Think of a detective's pinboard: a photo for each account and each phone, "
                   "and a string between each account and every phone it used.", [
            (lambda: [*self.uncap(), *self.strip("", ""), FadeOut(VGroup(fan_t, axis, *bars, *blabs))], 0.6),
            "Think of a detective's",
            (lambda: [FadeIn(board), FadeIn(btitle)], 0.6),
            "a photo for each",
            (lambda: [LaggedStart(*[FadeIn(c, scale=0.8) for c in self.cards.values()], lag_ratio=0.06)], 1.4),
            "and a string",
            (lambda: [LaggedStart(*[Create(t) for t in allties], lag_ratio=0.05)], 1.4),
        ])
        fing = Dot(radius=0.12, color=YELLOW_M).move_to(self.cards["A-3101"][0].get_top() + 0.02 * UP)
        c = self.cards
        self.steps("To take one step, put your finger on A-3101's photo. Follow its strings to its phones. "
                   "Then follow each phone's strings to the other photos. You never search the board.", [
            "put your finger",
            (lambda: [FadeIn(fing, scale=0.5)], 0.4),
            "Follow its strings",
            (lambda: [*self.lit_tie("A-3101", "D-77"), *self.lit_tie("A-3101", "P-0177"),
                      dot_run(c["A-3101"][0].get_center(), c["D-77"][0].get_center()),
                      dot_run(c["A-3101"][0].get_center(), c["P-0177"][0].get_center())], 0.7),
            "Then follow",
            (lambda: [*self.lit_tie("A-3102", "D-77"), *self.lit_tie("A-3102", "P-0177"),
                      dot_run(c["D-77"][0].get_center(), c["A-3102"][0].get_center()),
                      dot_run(c["P-0177"][0].get_center(), c["A-3102"][0].get_center()), *self.lit_card("A-3102", GREEN_M)], 0.7),
            "You never search",
            (lambda: self.cap("you never search the board", WHITE), 0.6),
        ])

        # ---------------- scene 4: nodes, strings, pointers ----------------
        self.steps("That's what a graph database stores. Neo4j is a database program built for graphs. Each photo is a node. "
                   "Each string is a relationship.", [
            (lambda: [*self.uncap(), FadeOut(fing)], 0.4),
            "Neo4j is",
            (lambda: self.cap("Neo4j: a database program built for graphs", WHITE), 0.6),
            "Each photo",
            (lambda: [*self.cap("photo = node", WHITE, 24), LaggedStart(*[glow(c[k][0], WHITE, 1.08) for k in ("A-3101", "D-77", "P-0177", "A-3102")], lag_ratio=0.2)], 0.9),
            "Each string",
            (lambda: [*self.cap("string = relationship", CORK, 24), LaggedStart(*[t.animate(rate_func=there_and_back).set_stroke(WHITE, 6) for t in allties], lag_ratio=0.04)], 1.0),
        ])
        self.steps("A node's record leads to its relationships, and each relationship records the nodes at both ends. "
                   "So following one is a pointer read: the record says where the next record is, and Neo4j goes straight there.", [
            "A node's record",
            (lambda: [glow(c["A-3101"][0], YELLOW_M, 1.1), *self.lit_tie("A-3101", "D-77", WHITE), *self.lit_tie("A-3101", "P-0177", WHITE)], 0.8),
            "both ends",
            (lambda: [glow(c["A-3101"][0], YELLOW_M, 1.1), glow(c["D-77"][0], YELLOW_M, 1.1)], 0.8),
            "a pointer read",
            (lambda: [*self.cap("a pointer read: the record says where the next record is", WHITE),
                      dot_run(c["A-3101"][0].get_center(), c["D-77"][0].get_center(), YELLOW_M, 0.5)], 0.7),
            "goes straight there",
            (lambda: [dot_run(c["D-77"][0].get_center(), c["A-3102"][0].get_center(), YELLOW_M, 0.5)], 0.7),
        ])
        self.steps("Neo4j calls this index-free adjacency: finding a node's neighbours needs no index. You use an index once, to find the start photo. "
                   "After that, the cost of a step doesn't depend on how many accounts exist.", [
            "index-free adjacency",
            (lambda: self.cap("index-free adjacency: a node's neighbours, found without an index", YELLOW_M), 0.6),
            "You use an index once",
            (lambda: [glow(idx[0][0], GOLD_M, 1.05), glow(c["A-3101"][0], RED_M, 1.1)], 0.9),
            "After that",
            (lambda: self.cap("the cost of a step doesn't depend on how many accounts exist", WHITE), 0.6),
        ])

        # ---------------- scene 5: walk three steps ----------------
        res_t = left_at(T("the walk, as Neo4j counts it", 19, BLUE_M), LX0 + 0.3, 2.5)
        res_h = VGroup(*[M(s, 18, GREY_B).move_to([LX0 + 0.9 + k * 1.6, 1.9, 0]) for k, s in enumerate(["steps", "paths", "accounts"])])
        res_rows = [VGroup(*[M(s, 22, col).move_to([LX0 + 0.9 + k * 1.6, 1.35 - i * 0.55, 0]) for k, (s, col) in
                             enumerate(zip(vals, (WHITE, YELLOW_M, GREEN_M)))]) for i, vals in enumerate([("1", "2", "1"), ("2", "2", "1"), ("3", "14", "6")])]
        self.steps("So let's walk. Step one: two strings out, to D-77 and P-0177, and both lead to A-3102. Two paths, one account.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(ttl, hdr, *r, more, idx)), *[t.animate.set_stroke(CORK, 2) for t in allties],
                      *self.unlit_card("A-3102")], 0.7),
            (lambda: [FadeIn(res_t), FadeIn(res_h)], 0.5),
            "Step one",
            (lambda: [*self.lit_tie("A-3101", "D-77"), *self.lit_tie("A-3101", "P-0177"), *self.lit_card("D-77", YELLOW_M), *self.lit_card("P-0177", YELLOW_M)], 0.6),
            "both lead to",
            (lambda: [*self.lit_tie("A-3102", "D-77"), *self.lit_tie("A-3102", "P-0177"), *self.lit_card("A-3102", GREEN_M)], 0.6),
            "Two paths",
            (lambda: [FadeIn(res_rows[0], shift=0.1 * RIGHT), *self.strip("step 1", "2 paths, 1 account")], 0.6),
        ])
        self.steps("Step two: from A-3102, phone P-0199 leads to A-3103. Still two paths, because there were two ways to reach A-3102.", [
            "phone P-0199",
            (lambda: [*self.lit_tie("A-3102", "P-0199"), *self.lit_card("P-0199", YELLOW_M)], 0.6),
            "leads to",
            (lambda: [*self.lit_tie("A-3103", "P-0199"), *self.lit_card("A-3103", GREEN_M)], 0.6),
            "Still two paths",
            (lambda: [FadeIn(res_rows[1], shift=0.1 * RIGHT), *self.strip("step 2", "2 paths, 1 account")], 0.6),
            "two ways",
            (lambda: [glow(c["D-77"][0], YELLOW_M, 1.1), glow(c["P-0177"][0], YELLOW_M, 1.1)], 0.8),
        ])
        self.steps("Now step three. How many paths, and how many new accounts? Pause and guess.", [
            (lambda: [*self.strip("step 3", "?", YELLOW_M)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        step3 = [("A-3103", "D-81"), ("A-3103", "P-0181"), ("A-3103", "D-KIOSK")]
        self.steps("Fourteen paths, and six accounts. A-3104 and A-3105 through device D-81 and phone P-0181.", [
            (lambda: [*self.uncap(), FadeIn(res_rows[2], shift=0.1 * RIGHT), *self.strip("step 3", "14 paths, 6 accounts", GREEN_M),
                      *[a for e in step3 for a in self.lit_tie(*e)], *[a for k in ("D-81", "P-0181", "D-KIOSK") for a in self.lit_card(k, YELLOW_M)]], 0.8),
            "A-3104 and",
            (lambda: [*self.lit_tie("A-3104", "D-81"), *self.lit_tie("A-3104", "P-0181"), *self.lit_tie("A-3105", "D-81"),
                      *self.lit_card("A-3104", GREEN_M), *self.lit_card("A-3105", GREEN_M)], 0.7),
        ])
        self.steps("And four customers through a store kiosk, a shared screen in a shop, that A-3103 also used.", [
            "four customers",
            (lambda: [*[a for k in SHOP for a in self.lit_tie(k, "D-KIOSK")], *[a for k in SHOP for a in self.lit_card(k, GREEN_M)]], 0.8),
            "a store kiosk",
            (lambda: [glow(c["D-KIOSK"][0], YELLOW_M, 1.15), *self.cap("a kiosk: a shared screen in a shop where customers sign in", WHITE)], 0.8),
        ])
        self.steps("The kiosk didn't find a fraud ring. It found four people who signed in at a shop.", [
            "It found four people",
            (lambda: [*[a for k in SHOP for a in self.lit_card(k, GREY_B)], *self.cap("the kiosk: four shoppers, not a ring", GREY_B)], 0.7),
        ])
        self.steps("So the fan-out doesn't go away. Both designs pay for every path they explore. "
                   "What changes is the price of each step, and how easily you can say up to three steps.", [
            "Both designs pay",
            (lambda: [*self.cap("both designs pay for every path they explore", RED_M), Indicate(res_rows[2][1], color=RED_M, scale_factor=1.2)], 0.8),
            "What changes",
            (lambda: self.cap("what changes: the price of each step, and how easily you say “up to three steps”", WHITE), 0.6),
        ])

        # ---------------- scene 6: which one, when ----------------
        self.steps("So when should you use which? If your questions are one or two steps of a known shape, stay with tables. "
                   "When they're paths of unknown length, rings or cycles, a graph store fits.", [
            (lambda: [*self.uncap(), *self.strip("", "")], 0.4),
            "If your questions",
            (lambda: self.cap("one or two steps of a known shape: stay with tables", BLUE_M), 0.6),
            "When they're paths",
            (lambda: self.cap("paths of unknown length, rings, cycles: a graph store fits", CORK), 0.6),
        ])
        newpin = VGroup(RoundedRectangle(corner_radius=0.18, width=0.9, height=0.36, stroke_color=WHITE, stroke_width=2).set_fill(fillc(GREY_B, 0.25), 1),
                        M("new", 14, WHITE)).move_to([2.65, -1.3, 0])
        newtie = Line(*ends(c["A-3102"][0], newpin[0]), stroke_width=3, color=WHITE)
        self.steps("And the strings aren't free. Every new one has to be tied into the lists of both its ends, "
                   "and a total over all payments reads records scattered across the board.", [
            "Every new one",
            (lambda: [FadeIn(newpin, scale=0.8), *self.cap("a new relationship is tied into the lists of both its ends", WHITE)], 0.5),
            (lambda: [Create(newtie)], 0.5),
            (lambda: [glow(c["A-3102"][0], WHITE, 1.15), glow(newpin[0], WHITE, 1.15)], 0.7),
            "a total over",
            (lambda: [FadeOut(newtie), FadeOut(newpin), LaggedStart(*[glow(c[k][0], GOLD_M, 1.1) for k in POS if k.startswith("A-")], lag_ratio=0.08),
                      *self.cap("a total over everything reads records scattered across the board", GOLD_M)], 1.2),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, back to the flagged account. In tables, every step through a shared phone cost two lookups and a join. "
                   "On the board, it's strings followed from a photo.", [
            (lambda: [*self.uncap(), *[t.animate.set_stroke(CORK, 2) for t in allties], *[a for k in POS if k != "A-3101" for a in self.unlit_card(k)]], 0.7),
            "In tables",
            (lambda: self.cap("tables: two lookups and a join per step", BLUE_M), 0.6),
            "On the board",
            (lambda: [*self.cap("the board: strings followed from a photo", CORK), *self.lit_tie("A-3101", "D-77"), *self.lit_tie("A-3101", "P-0177"),
                      *self.lit_tie("A-3102", "D-77"), *self.lit_tie("A-3102", "P-0177")], 0.7),
        ])
        self.steps("A graph store answers by walking: find the start node through an index, follow relationships outward, and pay only for what you touch.", [
            (lambda: self.cap("find the start node, follow relationships outward, pay only for what you touch", YELLOW_M, 24), 0.7),
        ], after=0.5)
        cy = VGroup(M("MATCH (f:Account {id: 'A-3101'})", 17), M("  -[:USES]->(x)<-[:USES]-", 17, YELLOW_M), M("  (other:Account)", 17))
        for i, m in enumerate(cy):
            left_at(m, LX0 + 0.3 + (0.25 if i else 0), -0.95 - i * 0.42)
        cyt = left_at(T("in Cypher, Neo4j's query language", 17, GREY_B), LX0 + 0.3, -0.45)
        self.steps("In Neo4j's query language, Cypher, you even draw the step: an account, an arrow to an identifier, and an arrow back from another account.", [
            (lambda: [FadeIn(cyt), FadeIn(cy[0])], 0.6),
            "an arrow to",
            (lambda: [FadeIn(cy[1]), *self.lit_tie("A-3101", "D-77", WHITE)], 0.6),
            "and an arrow back",
            (lambda: [FadeIn(cy[2]), *self.lit_tie("A-3102", "D-77", WHITE)], 0.6),
        ])
        many = T("+ 13 million accounts", 20, GREY_B).move_to([2.9, -1.75, 0])
        self.steps("One quick check. Keep the same strings around A-3101, but put 13 million accounts on the board instead of 13. "
                   "How many paths does step one find? Pause and think.", [
            (lambda: [*self.uncap(), *self.strip("same strings, 13 million accounts: step 1?", "?", YELLOW_M)], 0.6),
            "put 13 million",
            (lambda: [FadeIn(many), *[c[k].animate.set_opacity(0.35) for k in POS if k not in ("A-3101", "D-77", "P-0177", "A-3102")],
                      *[t.animate.set_stroke(opacity=0.35) for (a, b), t in self.ties.items() if a != "A-3101" and a != "A-3102" or b == "P-0199"]], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Still two. A step costs the strings you follow, not the size of the board.", [
            (lambda: [*self.uncap(), *self.strip("same strings, 13 million accounts: step 1", "still 2 paths", GREEN_M),
                      dot_run(c["A-3101"][0].get_center(), c["D-77"][0].get_center()), dot_run(c["A-3101"][0].get_center(), c["P-0177"][0].get_center())], 0.7),
            "A step costs",
            (lambda: self.cap("a step costs the strings you follow, not the size of the board", YELLOW_M, 26), 0.7),
        ], after=0.5)
        self.wait(2.0)
