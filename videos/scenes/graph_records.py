from sfz import *


def _acct(m):
    a, b = m.group(1), m.group(2)
    return f"A-{a} " + (f"oh {b[1]}" if b[0] == "0" else b)


# "A-3101" as people say it: "A thirty-one oh one"
SAY.insert(0, (r"\bA-(\d\d)(\d\d)\b", _acct))
SAY.insert(0, (r"\bD-(\d+)\b", r"dee \1"))
SAY.insert(0, (r"\bP-0(\d)(\d\d)\b", r"pee oh \1 \2"))
SAY.insert(0, (r"\bNeo4j's\b", "nee-oh four jay's"))
SAY.insert(0, (r"\bNeo4j\b", "nee-oh four jay"))
SAY.insert(0, (r"\bTRANSFERRED_TO\b", "transferred to"))
SAY.insert(0, (r"\bUSES\b", "uses"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
X0, PITCH, CW, CH = -6.45, 1.25, 1.12, 0.8         # file cells, left
NODE_Y, REL_Y = 2.2, 0.6
PAN_Y, CNT_Y = -0.95, -1.95                         # the record being read; the read counter
PAN_X1 = 1.0
NODES = [0, 1, 2, 3, None, 24]
RELS = [4, 5, 7, 26, 28, None]
G = {"A-3104": (3.15, 2.35), "A-3103": (6.05, 2.35), "A-3101": (4.6, 1.0), "D-77": (3.15, -0.4),
     "P-0177": (6.05, -0.4), "A-3102": (6.05, -1.75)}
EDGES = {28: ("A-3104", "A-3101", GOLD_M), 26: ("A-3101", "A-3103", GOLD_M), 5: ("A-3101", "P-0177", GREY_B),
         4: ("A-3101", "D-77", GREY_B), 7: ("A-3102", "P-0177", GREY_B)}
BAR_Y, CAP_Y = -2.75, -3.25


def cx(i):
    return X0 + CW / 2 + PITCH * i


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
            if callable(it):
                it()
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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.07, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))




def small_box(c, w, h, label, color, size=17):
    r = RoundedRectangle(corner_radius=0.08, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(label, size, color).move_to(c)) if label else VGroup(r)


def arc_run(a, b, color=YELLOW_M, rt=0.7, angle=-PI / 2.2):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    path = ArcBetweenPoints(a, b, angle=angle) if np.linalg.norm(b - a) > 0.01 else Line(a, b)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))


def fcell(i, y, top, bot, color):
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1) \
        .move_to([cx(i), y, 0])
    if top is None:
        return VGroup(r, T("...", 22, GREY_B).move_to([cx(i), y, 0]))
    return VGroup(r, M(top, 16).move_to([cx(i), y + 0.15, 0]), T(bot, 15, GREY_B).move_to([cx(i), y - 0.18, 0]))


class GraphRecords(Base):
    """store-13, section 0. The station lockers (locker 2: "open 28"; 28: "open 26"). The fraud team's graph: will a
    thousand times bigger mean a thousand times slower? Nodes, relationships, hops. A link table searched through a
    B+tree (3 levels at 100,000 rows, 4 at 10 million). Neo4j's fixed-size records: node N at byte N x 15,
    relationship N at byte N x 34. Predict, then walk A-3101's chain: node 2 (30), rels 28, 26, 5, 4: five reads.
    Newest first, doubly linked, two chains per relationship (5 goes on to 7); node 24 at 360: index-free adjacency.
    Where the lockers break (tired legs), fixed sizes only, one search at the start. The moral, and a check (rel 7)."""

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

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b), run_time=secs, rate_func=linear)

    def panel(self, head, body, color=YELLOW_M):
        g = VGroup(left_at(T(head, 21, color), X0, PAN_Y + 0.25), left_at(T(body, 19), X0, PAN_Y - 0.22))
        fit(g, PAN_X1 - X0)
        left_at(g, X0, PAN_Y)
        return self.put("pan", g)

    def reads(self, n):
        return self.put("cnt", left_at(T(f"record reads: {n}", 22, GREEN_M if n else WHITE), X0, CNT_Y))

    def lit(self, c, color):
        return [c[0].animate.set_stroke(color, width=4).set_fill(fillc(color, 0.3), 1)]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("A thousand times bigger, no slower", "how Neo4j follows a link by multiplying")

        # ---------------- scene 1: the lockers ----------------
        LN = ["0", "1", "2", "3", "...", "26", "27", "28"]
        LX = [-5.1 + 1.46 * k for k in range(8)]
        lockers = [VGroup(RoundedRectangle(corner_radius=0.06, width=1.25, height=2.1, stroke_color=GREY_B, stroke_width=2.5)
                          .set_fill("#161616", 1).move_to([x, 0.5, 0]), T(n, 24, WHITE if n != "..." else GREY_B).move_to([x, 1.25, 0]))
                   for n, x in zip(LN, LX)]
        for k, lk in enumerate(lockers):
            if LN[k] != "...":
                lk.add(Circle(radius=0.06, stroke_width=0).set_fill(GREY_B, 1).move_to([LX[k] + 0.42, 0.35, 0]))

        def note(k, s):
            return VGroup(Rectangle(width=1.0, height=0.5, stroke_width=0).set_fill(YELLOW_M, 0.9).move_to([LX[k], 0.25, 0]),
                          T(s, 19, BLACK).move_to([LX[k], 0.25, 0])).set_z_index(4)
        n2, n28 = note(2, "open 28"), note(7, "open 26")
        you = Dot(radius=0.11, color=YELLOW_M).move_to([LX[2], -0.8, 0]).set_z_index(5)
        self.steps("Picture a wall of lockers at a train station, all the same width, numbered from 0.", [
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * UP) for l in lockers], lag_ratio=0.1)], 1.4),
        ])
        self.steps("Locker 2 holds a note from a friend: open 28. Locker 28 says: open 26.", [
            (lambda: [FadeIn(you), glow(lockers[2][0], YELLOW_M, 1.03)], 0.5),
            "open 28",
            (lambda: [FadeIn(n2, scale=0.8)], 0.4),
            "Locker 28",
            (lambda: [you.animate.move_to([LX[7], -0.8, 0])], 0.8),
            (lambda: [FadeIn(n28, scale=0.8)], 0.4),
            "open 26",
            (lambda: [you.animate.move_to([LX[5], -0.8, 0])], 0.6),
        ])
        self.steps("You never need a map. Every locker is the same width, so you can count your way to any one of them.", [
            "same width",
            (lambda: [LaggedStart(*[glow(l[0], WHITE, 1.02) for l in lockers], lag_ratio=0.06),
                      *self.cap("same width, numbered from 0: count your way to any locker", WHITE)], 1.0),
        ], after=0.3)

        # ---------------- scene 2: the question ----------------
        gnode = {k: VGroup(RoundedRectangle(corner_radius=0.22, width=1.2, height=0.52, stroke_color=TEAL_M if k[0] == "A" else BLUE_M,
                                            stroke_width=2.5).set_fill(fillc(TEAL_M if k[0] == "A" else BLUE_M), 1).move_to([x, y, 0]),
                           M(k, 16).move_to([x, y, 0])) for k, (x, y) in G.items()}
        gedge = {}
        gtag = {}
        for rid, (a, b, col) in EDGES.items():
            ar = edge_arrow(gnode[a], gnode[b], col, buff=0.06)
            gedge[rid] = ar
            mid = ar.get_center()
            d = ar.get_end() - ar.get_start()
            nrm = np.array([-d[1], d[0], 0]) / (np.linalg.norm(d) or 1)
            gtag[rid] = T(str(rid), 17, col).move_to(mid + 0.24 * nrm)
        legend = VGroup(T("gold: TRANSFERRED_TO", 15, GOLD_M), T("grey: USES", 15, GREY_B)).arrange(RIGHT, buff=0.4).move_to([4.6, 3.3, 0])
        self.steps("Now picture a payments company's fraud team. Their map shows who is linked to whom: accounts, the phones and "
                   "devices they log in from, and the money they send each other.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*lockers, n2, n28, you))], 0.6),
            "Their map",
            (lambda: [FadeIn(gnode["A-3101"], scale=0.8)], 0.4),
            "accounts",
            (lambda: [LaggedStart(*[FadeIn(gnode[k], scale=0.8) for k in G if k != "A-3101"], lag_ratio=0.15)], 0.9),
            "the money",
            (lambda: [LaggedStart(*[GrowArrow(gedge[r]) for r in (28, 26, 5, 4, 7)], lag_ratio=0.15)], 1.0),
        ])
        self.steps("It finds the close links of a suspicious account in a millisecond. Next year the map will be a thousand times "
                   "bigger. Will the same question take a thousand times longer? Most people guess yes. Hold that guess.", [
            (lambda: [glow(gnode["A-3101"][0], YELLOW_M, 1.08)], 0.6),
            "a thousand times longer",
            (lambda: self.cap("a thousand times bigger: a thousand times longer?", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 3: nodes, relationships, hops ----------------
        self.steps("A map like this is called a graph. Each thing is a node: 13 accounts, 9 devices and 6 phone numbers.", [
            (lambda: self.cap("a graph: things and the links between them", WHITE), 0.5),
            "Each thing",
            (lambda: [LaggedStart(*[glow(gnode[k][0], TEAL_M, 1.08) for k in G], lag_ratio=0.1),
                      *self.cap("a node: one thing (13 accounts, 9 devices, 6 phone numbers)", TEAL_M)], 1.0),
        ])
        self.steps("Each link is a relationship, with a type. USES, when an account logs in from a phone or a device. "
                   "TRANSFERRED_TO, when one account sends money to another.", [
            (lambda: [*self.cap("a relationship: one link, with a type", WHITE), *[Indicate(gedge[r], color=YELLOW_M) for r in EDGES]], 0.8),
            "USES",
            (lambda: [FadeIn(legend[1]), *[Indicate(gedge[r], color=WHITE) for r in (5, 4, 7)]], 0.7),
            "TRANSFERRED_TO",
            (lambda: [FadeIn(legend[0]), *[Indicate(gedge[r], color=GOLD_M) for r in (28, 26)]], 0.7),
        ])
        self.steps("The fraud team's question is a walk: start at account A-3101, follow its relationships to its neighbours, then "
                   "theirs. Each step along one relationship is a hop.", [
            "start at account",
            (lambda: [glow(gnode["A-3101"][0], YELLOW_M, 1.1)], 0.6),
            "follow its relationships",
            (lambda: [dot_run(gnode["A-3101"].get_center(), gnode["P-0177"].get_center(), YELLOW_M, 0.7)], 0.8),
            "then theirs",
            (lambda: [dot_run(gnode["P-0177"].get_center(), gnode["A-3102"].get_center(), YELLOW_M, 0.6)], 0.7),
            "a hop",
            (lambda: self.cap("a hop: one step along one relationship", YELLOW_M), 0.5),
        ], after=0.3)

        # ---------------- scene 4: the link table ----------------
        TC = np.array([-2.9, 0, 0])
        tchip = chip("links (from, to): one row per relationship", RED_M, 20).move_to([-2.9, 2.75, 0])
        root = small_box(TC + [0, 1.8, 0], 1.2, 0.45, "root", RED_M)
        inn = [small_box(TC + [dx, 0.85, 0], 1.0, 0.42, "inner", RED_M, 15) for dx in (-1.4, 1.4)]
        lvs = [small_box(TC + [dx, -0.1, 0], 0.7, 0.38, "", RED_M) for dx in (-2.1, -0.7, 0.7, 2.1)]
        e1 = VGroup(*[Line(root.get_bottom(), i.get_top(), stroke_width=1.8, color=GREY_C) for i in inn])
        e2 = VGroup(*[Line(inn[k // 2].get_bottom(), l.get_top(), stroke_width=1.5, color=GREY_C) for k, l in enumerate(lvs)])
        lv4 = VGroup(*[small_box(TC + [dx, -1.0, 0], 0.32, 0.3, "", RED_M) for dx in np.linspace(-2.4, 2.4, 9)])
        e3 = VGroup(*[Line(lvs[min(3, k * 4 // 9)].get_bottom(), b.get_top(), stroke_width=1.2, color=GREY_D) for k, b in enumerate(lv4)])
        tree = VGroup(e1, e2, root, *inn, *lvs)
        lev = T("3 levels at 100,000 rows", 20, RED_M).move_to(TC + [0, -1.7, 0])
        lev4 = T("4 levels at 10 million", 20, RED_M).move_to(TC + [0, -1.7, 0])
        self.steps("The obvious way to store this is a table of links, one row per relationship, with the ids of its two ends.", [
            (lambda: [*self.uncap(), FadeIn(tchip, shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("To find A-3101's links, the database searches that table with an index: a sorted tree of pages, walked from "
                   "the top down, one page per level.", [
            "with an index",
            (lambda: [FadeIn(tree)], 0.8),
            "from the top down",
            (lambda: [Succession(dot_run(root.get_center(), inn[0].get_center(), RED_M, 0.4),
                                 dot_run(inn[0].get_center(), lvs[1].get_center(), RED_M, 0.4))], 1.0),
        ])
        self.steps("At 100,000 rows the tree is 3 levels deep. At 10 million, 4. So every hop costs a search, and the search "
                   "grows, slowly, with the whole graph.", [
            (lambda: [FadeIn(lev)], 0.5),
            "At 10 million",
            (lambda: [Create(e3), FadeIn(lv4), swap(lev, lev4)], 0.8),
            "every hop costs",
            (lambda: [*self.cap("every hop: a search that grows with the whole graph", RED_M),
                      Succession(dot_run(root.get_center(), inn[1].get_center(), RED_M, 0.3), dot_run(inn[1].get_center(), lvs[2].get_center(), RED_M, 0.3),
                                 dot_run(lvs[2].get_center(), lv4[5].get_center(), RED_M, 0.3)),
                      dot_run(gnode["A-3101"].get_center(), gnode["D-77"].get_center(), RED_M, 0.9)], 1.0),
        ])
        self.steps("What we'd like is the lockers: go straight to the next link, without searching.", [
            (lambda: self.cap("wanted: the lockers, straight to the next link, no searching", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("linktable")

        # ---------------- scene 5: fixed-size records ----------------
        ncells = [fcell(i, NODE_Y, None if n is None else f"node {n}", None if n is None else f"byte {n * 15}", BLUE_M) for i, n in enumerate(NODES)]
        rcells = [fcell(i, REL_Y, None if r is None else f"rel {r}", None if r is None else f"byte {r * 34}", GOLD_M) for i, r in enumerate(RELS)]
        nlab = left_at(T("node file: node N at byte N x 15", 19, BLUE_M), X0, NODE_Y + 0.62)
        rlab = left_at(T("relationship file: rel N at byte N x 34", 19, GOLD_M), X0, REL_Y + 0.62)
        self.steps("Neo4j, a database program built to store graphs, does exactly that. Every record in a file is the same size, "
                   "and has a number, its id.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(tchip, tree, lev4, lv4, e3))], 0.6),
            "Every record",
            (lambda: [*self.cap("Neo4j: every record in a file is the same size, and has an id", WHITE)], 0.5),
        ])
        self.steps("A node record is 15 bytes, so node N starts at byte N times 15. A relationship record is 34 bytes, so "
                   "relationship N starts at byte N times 34. Finding a record is arithmetic.", [
            (lambda: [FadeIn(nlab), LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in ncells], lag_ratio=0.12)], 1.0),
            "A relationship record",
            (lambda: [FadeIn(rlab), LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in rcells], lag_ratio=0.12)], 1.0),
            "Finding a record",
            (lambda: self.cap("finding a record: one multiplication", WHITE), 0.5),
        ])
        self.steps("Let's map it: the files are the wall of lockers, a record's id is the locker's number, and the pointer "
                   "inside a record is the note.", [
            "the files are",
            (lambda: [*self.cap("the file = the wall of lockers", WHITE), LaggedStart(*[glow(c[0], WHITE, 1.04) for c in rcells[:5]], lag_ratio=0.1)], 0.8),
            "a record's id",
            (lambda: [*self.cap("a record's id = the locker number", WHITE), Indicate(rcells[4][1], color=YELLOW_M)], 0.7),
            "the pointer",
            (lambda: self.cap("a pointer (another record's id) = the note", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 6: predict, then walk ----------------
        self.steps("A-3101 is node 2. How many records must Neo4j read to find all of its relationships? Pause and guess.", [
            (lambda: [glow(ncells[2][0], YELLOW_M, 1.06), glow(gnode["A-3101"][0], YELLOW_M, 1.08)], 0.6),
            "How many",
            (lambda: self.cap("how many record reads for all of A-3101's relationships?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        top = lambda c: c[0].get_top() + [0, 0.02, 0]
        self.steps("Start at byte 2 times 15: 30. The node record says: first relationship, 28.", [
            (lambda: [*self.uncap(), *self.lit(ncells[2], YELLOW_M), *self.reads(1),
                      *self.panel("node 2 at byte 2 x 15 = 30", "in use;  first relationship 28;  first property 10;  label Account")], 0.6),
            "first relationship",
            (lambda: [Indicate(self.lab["pan"][1], color=YELLOW_M, scale_factor=1.03)], 0.7),
        ])
        self.steps("Byte 28 times 34, 952: A-3104 sent money to A-3101, and its note for A-3101 says next, 26.", [
            (lambda: [dot_run(ncells[2][0].get_bottom(), rcells[4][0].get_top(), YELLOW_M, 0.6), *self.lit(ncells[2], GREEN_M)], 0.7),
            (lambda: [*self.lit(rcells[4], YELLOW_M), *self.reads(2),
                      *self.panel("rel 28 at byte 28 x 34 = 952", "A-3104 TRANSFERRED_TO A-3101;  for A-3101: next 26")], 0.5),
            "A-3104 sent",
            (lambda: [gedge[28].animate.set_color(YELLOW_M), gtag[28].animate.set_color(YELLOW_M)], 0.5),
            (lambda: [FadeIn(gtag[28])], 0.3),
        ])
        self.steps("Byte 884: A-3101 sent money to A-3103. Next, 5.", [
            (lambda: [arc_run(top(rcells[4]), top(rcells[3])), *self.lit(rcells[4], GREEN_M), gedge[28].animate.set_color(GREEN_M)], 0.6),
            (lambda: [*self.lit(rcells[3], YELLOW_M), *self.reads(3), gedge[26].animate.set_color(YELLOW_M), FadeIn(gtag[26]),
                      *self.panel("rel 26 at byte 26 x 34 = 884", "A-3101 TRANSFERRED_TO A-3103;  next 5;  back 28")], 0.6),
        ])
        self.steps("Byte 170: A-3101 uses the phone P-0177. Next, 4.", [
            (lambda: [arc_run(top(rcells[3]), top(rcells[1])), *self.lit(rcells[3], GREEN_M), gedge[26].animate.set_color(GREEN_M)], 0.6),
            (lambda: [*self.lit(rcells[1], YELLOW_M), *self.reads(4), gedge[5].animate.set_color(YELLOW_M), FadeIn(gtag[5]),
                      *self.panel("rel 5 at byte 5 x 34 = 170", "A-3101 USES P-0177;  next 4")], 0.6),
        ])
        self.steps("Byte 136: A-3101 uses the device D-77, and its next says minus one: the end.", [
            (lambda: [arc_run(top(rcells[1]), top(rcells[0])), *self.lit(rcells[1], GREEN_M), gedge[5].animate.set_color(GREEN_M)], 0.6),
            (lambda: [*self.lit(rcells[0], YELLOW_M), *self.reads(5), gedge[4].animate.set_color(YELLOW_M), FadeIn(gtag[4]),
                      *self.panel("rel 4 at byte 4 x 34 = 136", "A-3101 USES D-77;  next -1: the end of the chain")], 0.6),
            "the end",
            (lambda: [*self.lit(rcells[0], GREEN_M), gedge[4].animate.set_color(GREEN_M)], 0.5),
        ])
        self.steps("Five reads, four relationships, and nothing was searched. The count depends on how many links A-3101 has, and "
                   "on nothing else.", [
            (lambda: [*self.cap("5 record reads for 4 relationships: no search", GREEN_M), Indicate(self.lab["cnt"], color=GREEN_M)], 0.7),
            "The count depends",
            (lambda: [*self.cap("the reads depend on A-3101's own links, not on the size of the graph", WHITE),
                      LaggedStart(*[Indicate(gedge[r], color=GREEN_M) for r in (28, 26, 5, 4)], lag_ratio=0.2)], 1.0),
        ], after=0.3)
        self.stamp("walk")

        # ---------------- scene 7: two chains per relationship ----------------
        back = ArcBetweenPoints(rcells[3][0].get_bottom() - [0, 0.02, 0], rcells[4][0].get_bottom() - [0, 0.02, 0], angle=PI / 2.2) \
            .set_stroke(TEAL_M, 3).add_tip(tip_length=0.15)
        self.steps("Notice the order: newest first. Each new relationship goes in at the front of its chain, like a new note on top.", [
            (lambda: self.cap("newest first: a new relationship goes in at the front of the chain", WHITE), 0.6),
        ])
        self.steps("And each one points back as well as forward, so the chain is doubly linked. A relationship belongs to two "
                   "chains, one for each end.", [
            "points back",
            (lambda: [Create(back), *self.panel("rel 26: next 5, back 28", "every relationship points forward and back", TEAL_M)], 0.7),
            "doubly linked",
            (lambda: self.cap("forward and back: a doubly linked chain", TEAL_M), 0.5),
            "two chains",
            (lambda: [*self.cap("one chain for each end of the relationship", WHITE), glow(gnode["A-3101"][0], YELLOW_M, 1.08),
                      glow(gnode["P-0177"][0], YELLOW_M, 1.08)], 0.7),
        ])
        self.steps("Relationship 5 also carries on along P-0177's chain, to relationship 7: A-3102 uses the same phone.", [
            (lambda: [glow(rcells[1][0], YELLOW_M, 1.06), Indicate(gedge[5], color=YELLOW_M)], 0.6),
            "to relationship 7",
            (lambda: [arc_run(top(rcells[1]), top(rcells[2]), TEAL_M), *self.lit(rcells[2], TEAL_M),
                      *self.panel("rel 5, for P-0177: next 7", "rel 7: A-3102 USES P-0177", TEAL_M)], 0.7),
            "A-3102 uses",
            (lambda: [gedge[7].animate.set_color(TEAL_M), FadeIn(gtag[7].set_color(TEAL_M))], 0.5),
        ])
        self.steps("Crossing to a neighbour is the same move: P-0177 is node 24, at byte 360. One multiplication, one read.", [
            "P-0177 is node 24",
            (lambda: [dot_run(rcells[1][0].get_top(), ncells[5][0].get_bottom(), TEAL_M, 0.6), *self.lit(ncells[5], TEAL_M),
                      glow(gnode["P-0177"][0], TEAL_M, 1.08), *self.panel("node 24 (P-0177) at byte 24 x 15 = 360", "its chain starts at rel 7", TEAL_M)], 0.8),
            "One multiplication",
            (lambda: self.cap("a hop: one multiplication and one read", WHITE), 0.5),
        ])
        self.steps("Neo4j calls this index-free adjacency: finding a node's neighbours without an index.", [
            "index-free adjacency",
            (lambda: self.cap("index-free adjacency: finding a node's neighbours without an index", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("chains")

        # ---------------- scene 8: where the lockers stop, and the price ----------------
        self.steps("Here's where the lockers stop working. Walking to locker 30,000 takes longer than walking to locker 3. But "
                   "30,000 times 34 is no slower to work out than 3 times 34.", [
            (lambda: [*self.cap("where the lockers stop working", WHITE), FadeOut(back)], 0.5),
            "But 30,000",
            (lambda: self.panel("30,000 x 34 = 1,020,000", "no slower to work out than 3 x 34 = 102", WHITE), 0.6),
        ])
        self.steps("The lockers give you tired legs. The multiplication doesn't. What takes time is reading the record, and "
                   "that's the next section.", [
            "What takes time",
            (lambda: self.cap("what takes time: reading the record (next section)", WHITE), 0.6),
        ])
        self.steps("And why doesn't every database do this? It only works when every record is the same size. A shop's name may "
                   "be 3 letters or 300. In Neo4j, a long string spills into more records and costs more reads.", [
            (lambda: self.cap("why doesn't every database do this?", WHITE), 0.5),
            "It only works",
            (lambda: [*self.cap("it only works when every record is the same size", YELLOW_M),
                      LaggedStart(*[glow(c[0], YELLOW_M, 1.04) for c in rcells[:5]], lag_ratio=0.08)], 0.9),
            "a long string",
            (lambda: self.panel("a long string doesn't fit in one record", "it spills into more records, and costs more reads", RED_M), 0.6),
        ])
        mini = VGroup(root.copy(), *[i.copy() for i in inn], e1.copy()).scale(0.7).move_to([-4.4, PAN_Y, 0])
        self.steps("And an id says nothing about what's inside: to find the account called A-3101 in the first place, Neo4j "
                   "still searches a tree, once, at the start of the walk.", [
            "to find the account",
            (lambda: [*self.drop("pan"), FadeIn(mini)], 0.6),
            (lambda: [dot_run(mini[0].get_center(), mini[1].get_center(), RED_M, 0.4)], 0.5),
            "once, at the start",
            (lambda: [*self.cap("finding A-3101 by name: one tree search, once, at the start", RED_M), glow(ncells[2][0], RED_M, 1.06)], 0.7),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, a thousand times bigger, a thousand times slower? Not for the hops.", [
            (lambda: [FadeOut(mini), *self.cap("a thousand times bigger: a thousand times slower?", WHITE)], 0.6),
            "Not for the hops",
            (lambda: [*self.cap("not for the hops", GREEN_M, 26), LaggedStart(*[Indicate(gedge[r], color=GREEN_M) for r in (28, 26, 5, 4)], lag_ratio=0.15)], 0.8),
        ])
        self.steps("Record N lives at byte N times its size. Find the first node once, then multiply.", [
            (lambda: self.cap("record N lives at byte N x size", YELLOW_M, 26), 0.6),
            "Find the first node",
            (lambda: [*self.cap("find the first node once, then multiply", YELLOW_M, 26), glow(ncells[2][0], YELLOW_M, 1.06)], 0.6),
        ], after=0.3)
        self.steps("One quick check. Where does relationship 7 start? Pause and think.", [
            (lambda: [*self.uncap(), *self.lit(rcells[2], WHITE), Indicate(rcells[2][1], color=YELLOW_M), FadeOut(rcells[2][2])], 0.6),
            "Pause and think",
            (lambda: self.cap("rel 7: which byte?  pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("7 times 34: byte 238. No search, at any size.", [
            (lambda: [*self.uncap(), FadeIn(rcells[2][2]), *self.lit(rcells[2], GREEN_M), *self.panel("rel 7 at byte 7 x 34 = 238", "no search, at any size", GREEN_M)], 0.6),
        ], after=0.3)
        self.play(*self.cap("record N lives at byte N x size: find the first node once, then multiply", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
