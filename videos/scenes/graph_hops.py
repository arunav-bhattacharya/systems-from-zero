from sfz import *


def _acct(m):
    a, b = m.group(1), m.group(2)
    return f"A-{a} " + (f"oh {b[1]}" if b[0] == "0" else b)


# "A-3101" as people say it: "A thirty-one oh one" (the hyphen keeps Kokoro on the letter, not "uh" or "eye").
SAY.insert(0, (r"\bA-(\d\d)(\d\d)\b", _acct))
SAY.insert(0, (r"\bD-(\d+)\b", r"dee \1"))
SAY.insert(0, (r"\bP-0(\d)(\d\d)\b", r"pee oh \1 \2"))
SAY.insert(0, (r"\baccount_identifier\b", "account identifier"))
SAY.insert(0, (r"\bNeo4j\b", "nee-oh four jay"))
SAY.insert(0, (r"\b9:12\b", "nine twelve"))

GY = 2.05                                  # the fraud graph across the top
NODES = {"A-3101": (-5.5, GY), "D-77": (-3.5, GY + 0.5), "P-0177": (-3.5, GY - 0.5), "A-3102": (-1.5, GY),
         "P-0199": (0.5, GY), "A-3103": (2.5, GY)}
EDGES = [("A-3101", "D-77"), ("A-3101", "P-0177"), ("A-3102", "D-77"), ("A-3102", "P-0177"), ("A-3102", "P-0199"),
         ("A-3103", "P-0199")]
LX, RX = -3.45, 3.45                       # centres of the two panels
TCOL = [-4.1, -1.95]                      # link table columns
TROW = [-0.38 * (i + 1) for i in range(6)]
ROWS = [("A-3101", "D-77"), ("A-3101", "P-0177"), ("A-3102", "D-77"), ("A-3102", "P-0177"), ("A-3102", "P-0199"),
        ("A-3103", "P-0199")]
CAP1, CAP2 = -2.85, -3.25                  # caption rows under each panel
FAN_X = 3.85                               # rows-reached list, top right


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
            fn, rt = it
            self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def fillc(color):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def glow(rect, color=YELLOW_M, s=1.05):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def node(name, color=None):
    color = color or (GREY_B if name[0] in "DP" else WHITE)
    x, y = NODES[name]
    r = RoundedRectangle(corner_radius=0.1, width=1.55, height=0.6, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    return VGroup(r, M(name, 20, GREY_A if name[0] in "DP" else WHITE).move_to([x, y, 0]))


def fl(e, rev=False, color=BLUE_M, rt=0.6):
    s, t = e.get_start(), e.get_end()
    if rev:
        s, t = t, s
    return travel(Line(s, t), color, rt)


def tree(x, y, color, h=0.9, w=0.74):
    tri = Polygon([x, y + h / 2, 0], [x - w / 2, y - h / 2, 0], [x + w / 2, y - h / 2, 0], stroke_color=color, stroke_width=2.5)
    tri.set_fill(fillc(color), 1)
    lv = VGroup(*[Line([x - w / 2 * f, y + h / 2 - h * f, 0], [x + w / 2 * f, y + h / 2 - h * f, 0], stroke_width=1.5,
                       color=GREY_D) for f in (1 / 3, 2 / 3)])
    return VGroup(tri, lv)


def descend(tr):
    """A dot walking from the root of a tree icon down to a leaf, one level at a time."""
    top, bot, x = tr.get_top()[1], tr.get_bottom()[1], tr.get_center()[0]
    h = top - bot
    p = VMobject().set_points_as_corners([[x, top - 0.1, 0], [x - 0.1, top - h / 3, 0], [x + 0.08, top - 2 * h / 3, 0],
                                          [x - 0.04, bot + 0.08, 0]])
    d = Dot(radius=0.06, color=YELLOW_M).move_to(p.get_start())
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, p, rate_func=linear, run_time=1.0), FadeOut(d, run_time=0.15))


def card(name, entries, top, x, color=WHITE):
    h = 0.62 + 0.32 * len(entries)
    r = RoundedRectangle(corner_radius=0.12, width=1.6, height=h, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, top - h / 2, 0])
    n = M(name, 20, WHITE).move_to([x, top - 0.25, 0])
    sep = Line([x - 0.62, top - 0.47, 0], [x + 0.62, top - 0.47, 0], stroke_width=1.5, color=GREY_D)
    es = VGroup(*[M(e, 18, GREY_B).move_to([x, top - 0.68 - 0.32 * i, 0]) for i, e in enumerate(entries)])
    return VGroup(r, n, sep, es)


def ptr(a, b, color=TEAL_M):
    return Arrow(a, b, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.2, max_stroke_width_to_length_ratio=8)


def cap(s, y, x, color=GREY_B, size=22):
    return T(s, size, color).move_to([x, y, 0])


class GraphHops(Base):
    """model-08, section 0: the ring question from A-3101. In tables a hop is a self-join through two indexes (two more
    joins per hop, each lookup a B+tree descent); in a graph store a hop reads a list and follows pointers. Both pay
    the fan-out of 6 per hop (6, 36, 216, about 47,000); only the price of a hop differs."""

    def construct(self):
        self.title_card("Following links, hop by hop", "joins in tables, pointers in a graph store")

        nd = {k: node(k, RED_M if k == "A-3101" else None) for k in NODES}
        E = {k: link(nd[k[0]][0], nd[k[1]][0], GREY_C, dashed=False, sw=2) for k in EDGES}
        flag = T("flagged at 9:12", 20, RED_M).move_to([NODES["A-3101"][0], GY - 0.63, 0])
        self.steps("At 9:12 the fraud team flags account A-3101. Which accounts share a device or a phone number "
                   "with it, directly or through other accounts?", [
            (lambda: [FadeIn(nd["A-3101"]), FadeIn(flag, shift=0.1 * UP)], 0.8),
            "share a device",
            (lambda: [FadeIn(nd["D-77"]), FadeIn(nd["P-0177"]), Create(E[("A-3101", "D-77")]),
                      Create(E[("A-3101", "P-0177")])], 0.9),
            "through other",
            (lambda: [FadeIn(nd["A-3102"]), FadeIn(nd["P-0199"]), FadeIn(nd["A-3103"]),
                      *[Create(E[k]) for k in EDGES[2:]]], 1.0),
        ])

        hop1 = T("hop 1", 22, BLUE_M).move_to([-3.5, 3.22, 0])
        hop2 = T("hop 2", 22, BLUE_M).move_to([0.5, 3.22, 0])
        self.steps("One hop goes account, identifier, account. A-3102 is one hop away. A-3103 is two.", [
            0.4,
            (lambda: [Succession(fl(E[("A-3101", "D-77")]), fl(E[("A-3102", "D-77")], rev=True))], 1.6),
            "A-3102 is",
            (lambda: [Transform(nd["A-3102"], node("A-3102", BLUE_M)), FadeIn(hop1, shift=0.1 * DOWN)], 0.7),
            "A-3103 is",
            (lambda: [Succession(fl(E[("A-3102", "P-0199")], rt=0.4), fl(E[("A-3103", "P-0199")], rev=True, rt=0.4)),
                      FadeIn(hop2, shift=0.1 * DOWN)], 0.9),
            (lambda: [Transform(nd["A-3103"], node("A-3103", BLUE_M))], 0.5),
        ])

        # ---- tables ---------------------------------------------------------------------------------------
        div = DashedLine([0, 0.85, 0], [0, -3.4, 0], dash_length=0.08, stroke_width=1.5, color=GREY_D)
        lt = T("in tables", 26, BLUE_M).move_to([LX, 0.55, 0])
        hdr = VGroup(M("account_id", 18, BLUE_M).move_to([TCOL[0], 0, 0]), M("identifier_id", 18, GOLD_M).move_to([TCOL[1], 0, 0]),
                     Line([-4.95, -0.18, 0], [-0.9, -0.18, 0], stroke_width=1.5, color=GREY_D))
        rows = VGroup(*[VGroup(M(a, 20).move_to([TCOL[0], y, 0]), M(b, 20, GREY_A).move_to([TCOL[1], y, 0]))
                        for (a, b), y in zip(ROWS, TROW)])
        t1, t2 = tree(-5.85, -0.75, BLUE_M), tree(-5.85, -2.0, GOLD_M)
        idx_l = T("indexes", 18, GREY_B).move_to([-5.85, 0.0, 0])
        self.steps("In tables, each link is a row: an account, and an identifier it uses. There's an index on each column.", [
            (lambda: [Create(div), FadeIn(lt)], 0.6),
            "a row",
            (lambda: [FadeIn(hdr), LaggedStart(*[FadeIn(r) for r in rows], lag_ratio=0.15)], 1.3),
            "There's an index",
            (lambda: [FadeIn(t1), FadeIn(t2), FadeIn(idx_l)], 0.8),
        ])

        def hl(i, color):
            r = Rectangle(width=4.1, height=0.34, stroke_width=0).set_fill(color, 0.22).move_to([-2.93, TROW[i], 0])
            return r.set_z_index(-1)

        h12, h34 = VGroup(hl(0, BLUE_M), hl(1, BLUE_M)), VGroup(hl(2, GOLD_M), hl(3, GOLD_M))
        self.steps("One hop crosses the table twice. One index finds A-3101's identifiers. "
                   "The other finds who else uses them: A-3102.", [
            "One index finds",
            (lambda: [glow(t1[0], BLUE_M), FadeIn(h12)], 0.9),
            "The other finds",
            (lambda: [glow(t2[0], GOLD_M), FadeIn(h34)], 0.9),
            "uses them",
            0.5,
            (lambda: [glow(nd["A-3102"][0], BLUE_M), Indicate(rows[2][0], color=BLUE_M), Indicate(rows[3][0], color=BLUE_M)], 0.9),
        ])

        lc1 = cap("one hop: a self-join, 2 lookups", CAP1, LX)
        lc2 = cap("each lookup: 3 or 4 pages", CAP2, LX)
        self.steps("That's a self-join. Each lookup walks down a B+tree: 3 or 4 pages.", [
            (lambda: [FadeIn(lc1, shift=0.1 * UP)], 0.7),
            "walks down",
            (lambda: [descend(t1), descend(t2)], 1.3),
            "3 or 4",
            (lambda: [FadeIn(lc2, shift=0.1 * UP)], 0.7),
        ])

        lc1b = cap("hops 1, 2, 3: joins 2, 4, 6", CAP1, LX, GOLD_M)
        lc2b = cap("the planner guesses every size in between", CAP2, LX)
        self.steps("Every hop you allow adds two more joins, and the planner has to guess the size of each one.", [
            (lambda: [FadeOut(h12), FadeOut(h34)], 0.5),
            "two more joins",
            (lambda: [FadeOut(lc1), FadeIn(lc1b, shift=0.1 * UP)], 0.8),
            "the planner",
            (lambda: [FadeOut(lc2), FadeIn(lc2b, shift=0.1 * UP)], 0.8),
        ])

        fan_h = T("rows reached", 20, GREY_B)
        fan_h.move_to([FAN_X + fan_h.width / 2, 3.2, 0])
        fan = VGroup(*[M(s, 20, WHITE) for s in ["1 hop: 6", "2 hops: 36", "3 hops: 216", "6 hops: ~47,000"]])
        for i, f in enumerate(fan):
            f.move_to([FAN_X + f.width / 2, 2.76 - 0.4 * i, 0])
        self.steps("And every hop fans out, about 6 times here: 6 rows, then 36, then 216. Six hops: about 47,000.", [
            (lambda: [FadeIn(fan_h)], 0.7),
            "6 rows",
            (lambda: [FadeIn(fan[0], shift=0.1 * DOWN)], 0.5),
            "then 36",
            (lambda: [FadeIn(fan[1], shift=0.1 * DOWN)], 0.5),
            "then 216",
            (lambda: [FadeIn(fan[2], shift=0.1 * DOWN)], 0.5),
            "Six hops",
            (lambda: [FadeIn(fan[3], shift=0.1 * DOWN)], 0.6),
        ])

        # ---- graph store ----------------------------------------------------------------------------------
        left = VGroup(lt, hdr, rows, t1, t2, idx_l, lc1b, lc2b)
        rt = T("in a graph store", 26, TEAL_M).move_to([RX, 0.55, 0])
        ca = card("A-3101", ["D-77", "P-0177"], 0.15, 1.3, RED_M)
        cd = card("D-77", ["A-3101", "A-3102"], -1.25, 3.5, GREY_B)
        cb = card("A-3102", ["D-77", "P-0177", "P-0199"], 0.15, 5.7, BLUE_M)
        self.steps("A graph store keeps the links the other way round. Next to each account, a list of what it uses. "
                   "Next to each identifier, the accounts that use it.", [
            (lambda: [left.animate.set_opacity(0.3), FadeIn(rt)], 0.9),
            "Next to each account",
            (lambda: [FadeIn(ca, shift=0.1 * DOWN), FadeIn(cb, shift=0.1 * DOWN)], 0.9),
            "Next to each identifier",
            (lambda: [FadeIn(cd, shift=0.1 * DOWN)], 0.8),
        ])

        p1 = ptr([2.12, ca[3][0].get_y(), 0], [3.0, cd[0].get_top()[1] + 0.02, 0])
        p2 = ptr([4.32, cd[3][1].get_y(), 0], [5.15, cb[0].get_bottom()[1] - 0.02, 0])
        rc2 = cap("no search: the same cost at any size", CAP2, RX)
        self.steps("A hop reads a list and jumps straight to the record it names. No search, "
                   "so it costs the same with a thousand accounts or a hundred million.", [
            "reads a list",
            (lambda: [Indicate(ca[3][0], color=TEAL_M)], 0.6),
            "jumps straight",
            (lambda: [GrowArrow(p1)], 0.5),
            (lambda: [travel(p1, TEAL_M, 0.6)], 0.6),
            (lambda: [Indicate(cd[3][1], color=TEAL_M), GrowArrow(p2)], 0.6),
            (lambda: [travel(p2, TEAL_M, 0.6), glow(cb[0], BLUE_M)], 0.7),
            "No search",
            (lambda: [FadeIn(rc2, shift=0.1 * UP)], 0.7),
        ])

        rt2 = T("in a graph store: Neo4j", 26, TEAL_M).move_to([RX, 0.55, 0])
        back = ptr([2.68, cd[3][0].get_y(), 0], [1.85, ca[0].get_bottom()[1] - 0.02, 0], GREY_B)
        rc2b = cap("index-free adjacency", CAP2, RX, YELLOW_M)
        self.steps("Neo4j stores each relationship with both its nodes, so following one is a pointer read: "
                   "index-free adjacency.", [
            (lambda: [Transform(rt, rt2)], 0.7),
            "with both",
            (lambda: [GrowArrow(back), Indicate(cd[3][0], color=TEAL_M), Indicate(ca[3][0], color=TEAL_M)], 1.0),
            "index-free",
            (lambda: [FadeOut(rc2), FadeIn(rc2b, shift=0.1 * UP)], 0.8),
        ])

        st = tree(1.3, -1.95, GREY_B, h=0.7, w=0.6)
        st_a = ptr([1.3, -1.57, 0], [1.3, ca[0].get_bottom()[1] - 0.04, 0], GREY_B)
        rc1 = cap("one index lookup, at the start", CAP1, RX)
        self.steps("It needs an index only once, to find where the walk starts.", [
            (lambda: [FadeIn(st), FadeIn(rc1, shift=0.1 * UP)], 0.8),
            (lambda: [GrowArrow(st_a)], 0.5),
            (lambda: [Succession(travel(p1, TEAL_M, 0.6), travel(p2, TEAL_M, 0.6))], 1.4),
        ])

        self.steps("Both designs still pay for every path they explore. What differs is the price of each hop.", [
            (lambda: [left.animate.set_opacity(1)], 0.8),
            0.6,
            (lambda: [*[Indicate(f, color=YELLOW_M) for f in fan]], 1.2),
        ])

        lc1c = cap("per row, per hop: 2 tree descents", CAP1, LX, BLUE_M)
        lc2c = cap("deeper as the table grows", CAP2, LX)
        rc1c = cap("per row, per hop: 2 pointer reads", CAP1, RX, TEAL_M)
        rc2c = cap("the same at any size", CAP2, RX)
        self.steps("In tables, it's two tree descents per row, and the trees get deeper as the table grows. "
                   "In a graph store, it's two pointer reads, at any size.", [
            (lambda: [FadeOut(lc1b), FadeOut(lc2b), FadeIn(lc1c, shift=0.1 * UP)], 0.8),
            "the trees get deeper",
            (lambda: [t1.animate.stretch(1.25, 1), t2.animate.stretch(1.25, 1), FadeIn(lc2c, shift=0.1 * UP)], 1.0),
            "In a graph store",
            (lambda: [FadeOut(rc1), FadeOut(rc2b), FadeIn(rc1c, shift=0.1 * UP)], 0.8),
            "at any size",
            (lambda: [FadeIn(rc2c, shift=0.1 * UP)], 0.6),
        ])

        self.steps("So keep one or two hops of a known shape in Postgres or Oracle. For paths of unknown length, rings "
                   "and cycles, a graph store walks them, and you pay for what you touch.", [
            (lambda: [Indicate(lt, color=BLUE_M)], 1.0),
            "For paths",
            (lambda: [Indicate(rt, color=TEAL_M)], 1.0),
            (lambda: [Succession(fl(E[("A-3101", "D-77")], rt=0.4), fl(E[("A-3102", "D-77")], rev=True, rt=0.4),
                                 fl(E[("A-3102", "P-0199")], rt=0.4), fl(E[("A-3103", "P-0199")], rev=True, rt=0.4))], 1.8),
        ])
        self.wait(0.6)
