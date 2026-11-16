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

CW, CH = 0.8, 0.52                       # one record cell in a store strip
X0 = -6.5
NODE_Y, REL_Y = 2.75, 1.25               # the two store files
CARD_X0, CARD_Y = -6.5, -0.85            # the record being read: field boxes at this height
FW, FG = 1.0, 0.1                        # field box width and gap
G = {"A-3101": (4.4, -1.7), "A-3104": (2.85, -0.45), "A-3103": (5.95, -0.45), "D-77": (2.85, -2.8),
     "P-0177": (5.95, -2.8), "A-3102": (4.4, -3.2)}


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.06):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def strip(ids, y, word):
    """A store file as a row of equal cells; returns (group, {id: cell}, {id: x})."""
    cells, xs, g = {}, {}, VGroup()
    x = X0
    for i in ids:
        if i == "...":
            g.add(T("...", 24, GREY_C).move_to([x + 0.3, y, 0]))
            x += 0.6
            continue
        r = Rectangle(width=CW, height=CH, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
        r.move_to([x + CW / 2, y, 0])
        c = VGroup(r, T(f"{word} {i}", 16, GREY_A).move_to(r))
        cells[i], xs[i] = c, x + CW / 2
        g.add(c)
        x += CW
    return g, cells, xs


def blab(x, y, s, color=GREY_B):
    return T(s, 16, color).move_to([x, y - CH / 2 - 0.2, 0])


def lit(cell, color):
    return [cell[0].animate.set_stroke(color, 3).set_fill(fillc(color), 1), cell[1].animate.set_color(WHITE)]


def field(i, label, value, color=GREY_B, vcolor=WHITE, w=FW, x0=CARD_X0, mono=True):
    x = x0 + i * (w + FG) + w / 2
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.6, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([x, CARD_Y, 0])
    v = M(value, 17, vcolor) if mono else T(value, 16, vcolor)
    return VGroup(r, v.move_to(r), T(label, 15, GREY_B).move_to([x, CARD_Y + 0.5, 0]))


def node_card(nid, name, first_rel, prop, label, hi=None, hc=GOLD_M):
    title = left_at(T(f"node {nid} ({name}), at byte {nid} × 15 = {nid * 15}", 20, WHITE), CARD_X0, CARD_Y + 1.05)
    vals = [("in use", "yes"), ("first rel", first_rel), ("first prop", prop), ("labels", label)]
    fs = [field(i, l, v, hc if hi == i else GREY_B, w=1.6) for i, (l, v) in enumerate(vals)]
    return VGroup(title, *fs)


def rel_card(rid, a, b, typ, pa, pb, hi="b"):
    """A relationship record: both nodes, its type, and a (prev, next) pair for each node. hi: which pair the walk uses."""
    title = left_at(T(f"relationship {rid}, at byte {rid} × 34 = {rid * 34}", 20, WHITE), CARD_X0, CARD_Y + 1.05)
    ca = GOLD_M if hi == "a" else GREY_D
    cb = GOLD_M if hi == "b" else GREY_D
    fs = [field(0, "first node", a, GREY_B), field(1, "second node", b, GREY_B), field(2, "type", typ, GREY_B, mono=False),
          field(3, "prev", pa[0], ca, WHITE if hi == "a" else GREY_C), field(4, "next", pa[1], ca, WHITE if hi == "a" else GREY_C),
          field(5, "prev", pb[0], cb, WHITE if hi == "b" else GREY_C), field(6, "next", pb[1], cb, WHITE if hi == "b" else GREY_C)]
    def pair_lab(i, s, c):
        x = CARD_X0 + i * (FW + FG) + FW + FG / 2
        return T(s, 16, c).move_to([x, CARD_Y - 0.52, 0])
    def name_lab(i, s):
        return T(s, 16, GREY_B).move_to([CARD_X0 + i * (FW + FG) + FW / 2, CARD_Y - 0.52, 0])
    return VGroup(title, *fs, pair_lab(3, f"{NAMES[a]}'s chain", ca if hi == "a" else GREY_C),
                  pair_lab(5, f"{NAMES[b]}'s chain", cb if hi == "b" else GREY_C), name_lab(0, NAMES[a]), name_lab(1, NAMES[b]))


NAMES = {"2": "A-3101", "5": "A-3104", "4": "A-3103", "24": "P-0177", "15": "D-77"}


def gnode(name, color=GREY_B):
    b = RoundedRectangle(corner_radius=0.1, width=1.2, height=0.48, stroke_color=color, stroke_width=2.5)
    b.set_fill(fillc(color), 1).move_to([*G[name], 0])
    return VGroup(b, M(name, 16, WHITE).move_to(b))


def gedge(a, b, rid, color=GOLD_M):
    pa, pb = np.array([*G[a], 0]), np.array([*G[b], 0])
    ra, rb = Rectangle(width=1.2, height=0.48).move_to(pa), Rectangle(width=1.2, height=0.48).move_to(pb)
    ar = edge_arrow(ra, rb, color, buff=0.06)
    mid = (pa + pb) / 2
    d = pb - pa
    n = np.array([-d[1], d[0], 0]) / (np.linalg.norm(d) or 1)
    lab = T(rid, 17, color).move_to(mid + 0.24 * n)
    return VGroup(ar, lab)


def counter(n):
    return left_at(T(f"records read: {n}    indexes searched: 0", 20, GREY_B), CARD_X0, -3.2)


class GraphRecords(Base):
    """store-13, section 0: A-3101 is node 2 at byte 2 x 15 = 30; its first relationship is 28 (byte 952); the chain
    28 -> 26 -> 5 -> 4 -> end, newest first, with the head's prev field holding the degree 4; relationship 5 sits in
    P-0177's chain too; crossing to P-0177 is node 24 at byte 360, whose chain starts at relationship 7 (A-3102)."""

    def construct(self):
        self.title_card("Graph records", "fixed-size records, and hops that search nothing")

        a3101 = gnode("A-3101", GOLD_M)
        q = T("linked to what?", 20, GREY_B).next_to(a3101, UP, buff=0.25)
        self.steps("The fraud team flags account A-3101. Neo4j finds all its links in five small reads, and searches nothing. How?", [
            (lambda: [FadeIn(a3101, scale=0.9)], 0.6),
            (lambda: [FadeIn(q, shift=0.1 * UP)], 0.6),
            "Neo4j finds",
            (lambda: [glow(a3101[0], GOLD_M, 1.1)], 0.9),
        ])

        # ---- the table way: a B+tree descent per lookup -----------------------------------------------------------------
        def tnode(x, y, w=1.3, color=GREY_B):
            return RoundedRectangle(corner_radius=0.08, width=w, height=0.42, stroke_color=color, stroke_width=2).set_fill(BLACK, 1).move_to([x, y, 0])
        root = tnode(-3.2, 1.9)
        inner = [tnode(-4.8, 0.8), tnode(-1.6, 0.8)]
        leaves = [tnode(x, -0.3, 1.1) for x in (-5.6, -4.0, -2.4, -0.8)]
        lines = VGroup(*[link(root, i, GREY_C, dashed=False) for i in inner],
                       *[link(inner[k // 2], leaves[k], GREY_C, dashed=False) for k in range(4)])
        tree = VGroup(lines, root, *inner, *leaves)
        tlab = T("link table (account, identifier), B+tree index", 20, GREY_B).move_to([-3.2, 2.65, 0])
        path = [root, inner[0], leaves[1]]
        tcost = T("one lookup: 3 page reads at 100,000 rows, 4 at 10 million", 20, RED_M).move_to([-3.2, -1.2, 0])
        self.steps("In tables, every link lookup walks down a B+tree: three or four page reads, and more as the table grows.", [
            (lambda: [FadeIn(tlab), Create(lines), *[FadeIn(m) for m in [root, *inner, *leaves]]], 1.2),
            "walks down",
            (lambda: [path[0].animate.set_stroke(RED_M, 3)], 0.4),
            (lambda: [path[1].animate.set_stroke(RED_M, 3)], 0.4),
            (lambda: [path[2].animate.set_stroke(RED_M, 3)], 0.4),
            "three or four",
            (lambda: [FadeIn(tcost, shift=0.1 * UP)], 0.6),
        ])

        # ---- fixed-size node records --------------------------------------------------------------------------------------
        nstrip, ncell, nx = strip([0, 1, 2, 3, 4, 5, "...", 15, "...", 24, "..."], NODE_Y, "node")
        nlab = left_at(T("node store: every record 15 bytes", 20, GREY_B), X0, NODE_Y + 0.52)
        nb = VGroup(*[blab(nx[i], NODE_Y, str(i * 15)) for i in range(4)])
        self.steps("Neo4j gives every node record the same 15 bytes, so node n starts at byte n times 15.", [
            (lambda: [FadeOut(VGroup(tree, tlab, tcost)), FadeOut(q)], 0.7),
            (lambda: [FadeIn(nlab), LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in nstrip], lag_ratio=0.08)], 1.4),
            "so node n",
            (lambda: [LaggedStart(*[FadeIn(b) for b in nb], lag_ratio=0.25)], 1.0),
        ])

        card = node_card(2, "A-3101", "28", "10", "Account")
        cnt = counter(1)
        self.steps("A-3101 is node 2, so its record is at byte 30, found without a search. Its first relationship is 28.", [
            (lambda: [*lit(ncell[2], GOLD_M), nb[2].animate.set_color(GOLD_M), FadeOut(VGroup(nb[0], nb[1], nb[3]))], 0.7),
            "found without",
            (lambda: [travel(Line(ncell[2][0].get_bottom(), card[0].get_top() + 0.1 * UP), GOLD_M, 0.7)], 0.8),
            (lambda: [FadeIn(card[0]), FadeIn(cnt)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(f) for f in card[1:]], lag_ratio=0.3)], 1.0),
            "Its first relationship",
            (lambda: [glow(card[2][0], GOLD_M, 1.1)], 0.7),
        ])

        # ---- relationship records ------------------------------------------------------------------------------------------
        rstrip, rcell, rx = strip([0, 1, 2, 3, 4, 5, 6, 7, 8, "...", 26, 27, 28, "..."], REL_Y, "rel")
        rlab = left_at(T("relationship store: every record 34 bytes", 20, GREY_B), X0, REL_Y + 0.52)
        b952 = blab(rx[28], REL_Y, "952", GOLD_M)
        self.steps("Relationship records are 34 bytes, so relationship 28 is at byte 952.", [
            (lambda: [FadeIn(rlab), LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in rstrip], lag_ratio=0.05)], 1.3),
            "so relationship 28",
            (lambda: [travel(Line(card[2][0].get_top(), rcell[28][0].get_bottom()), GOLD_M, 0.8)], 0.9),
            (lambda: [*lit(rcell[28], GOLD_M), FadeIn(b952)], 0.6),
        ])

        c28 = rel_card(28, "5", "2", "transfer", ("...", "..."), ("4", "26"), hi=None)
        e28 = gedge("A-3104", "A-3101", "28")
        n3104 = gnode("A-3104")
        self.steps("It's A-3104's transfer to A-3101. It holds both nodes, and for each one, the previous and next relationship.", [
            (lambda: [FadeOut(card), Transform(cnt, counter(2)), FadeIn(c28[0]), *[FadeIn(f) for f in c28[1:4]]], 0.8),
            (lambda: [FadeIn(n3104), GrowArrow(e28[0]), FadeIn(e28[1])], 0.7),
            "and for each one",
            (lambda: [*[FadeIn(f) for f in c28[4:]]], 0.9),
        ])

        c28b = rel_card(28, "5", "2", "transfer", ("...", "..."), ("4", "26"), hi="b")
        deg = T("head of the chain: prev holds the length, 4", 18, TEAL_M).move_to([CARD_X0 + 5 * (FW + FG) + FW, CARD_Y - 0.95, 0])
        self.steps("A-3101 is the second node, so the walk takes the second pair: next is 26.", [
            (lambda: [Transform(c28, c28b)], 0.8),
            "next is 26",
            (lambda: [glow(c28[7][0], GOLD_M, 1.1)], 0.7),
            (lambda: [glow(c28[6][0], TEAL_M, 1.1), FadeIn(deg, shift=0.1 * UP)], 0.9),
        ])

        c26 = rel_card(26, "2", "4", "transfer", ("28", "5"), ("...", "..."), hi="a")
        e26 = gedge("A-3101", "A-3103", "26")
        n3103 = gnode("A-3103")
        self.steps("Relationship 26, a transfer to A-3103. Previous leads back to 28, and next is 5.", [
            (lambda: [FadeOut(deg), travel(Line(c28[7][0].get_top(), rcell[26][0].get_bottom()), GOLD_M, 0.7)], 0.8),
            (lambda: [*lit(rcell[26], GOLD_M), FadeIn(blab(rx[26], REL_Y, "884", GOLD_M)), rcell[28][0].animate.set_stroke(GREY_B, 2),
                      Transform(c28, c26), Transform(cnt, counter(3))], 0.8),
            (lambda: [FadeIn(n3103), GrowArrow(e26[0]), FadeIn(e26[1])], 0.6),
            "Previous leads",
            (lambda: [glow(c28[4][0], TEAL_M, 1.1)], 0.7),
            "and next is 5",
            (lambda: [glow(c28[5][0], GOLD_M, 1.1)], 0.6),
        ])

        c5 = rel_card(5, "2", "24", "uses", ("26", "4"), ("...", "..."), hi="a")
        e5 = gedge("A-3101", "P-0177", "5")
        n0177 = gnode("P-0177")
        other = T("the other pair: P-0177's own chain", 18, TEAL_M).move_to([CARD_X0 + 5 * (FW + FG) + FW, CARD_Y - 0.95, 0])
        self.steps("Relationship 5: A-3101 uses phone P-0177. Its other pair is in P-0177's chain: one record, two chains. Next is 4.", [
            (lambda: [travel(Line(c28[5][0].get_top(), rcell[5][0].get_bottom()), GOLD_M, 0.8)], 0.9),
            (lambda: [*lit(rcell[5], GOLD_M), FadeIn(blab(rx[5], REL_Y, "170", GOLD_M)), rcell[26][0].animate.set_stroke(GREY_B, 2),
                      Transform(c28, c5), Transform(cnt, counter(4))], 0.8),
            (lambda: [FadeIn(n0177), GrowArrow(e5[0]), FadeIn(e5[1])], 0.6),
            "Its other pair",
            (lambda: [c28[6][0].animate.set_stroke(TEAL_M), c28[7][0].animate.set_stroke(TEAL_M), FadeIn(other, shift=0.1 * UP)], 0.8),
            "Next is 4",
            (lambda: [glow(c28[5][0], GOLD_M, 1.1)], 0.6),
        ])

        c4 = rel_card(4, "2", "15", "uses", ("5", "-1"), ("...", "..."), hi="a")
        e4 = gedge("A-3101", "D-77", "4")
        nd77 = gnode("D-77")
        found = T("4 relationships, newest first", 20, GREEN_M).move_to([G["A-3101"][0], 0.35, 0])
        self.steps("Relationship 4: device D-77. Next is minus one, the end. Five reads found four relationships, newest first.", [
            (lambda: [FadeOut(other), travel(Line(c28[5][0].get_top(), rcell[4][0].get_bottom()), GOLD_M, 0.8)], 0.9),
            (lambda: [*lit(rcell[4], GOLD_M), FadeIn(blab(rx[4], REL_Y, "136", GOLD_M)), rcell[5][0].animate.set_stroke(GREY_B, 2),
                      Transform(c28, c4), Transform(cnt, counter(5))], 0.8),
            (lambda: [FadeIn(nd77), GrowArrow(e4[0]), FadeIn(e4[1])], 0.6),
            "Next is minus one",
            (lambda: [glow(c28[5][0], RED_M, 1.1)], 0.7),
            "Five reads",
            (lambda: [Transform(cnt, counter(5).set_color(GREEN_M)), FadeIn(found, shift=0.1 * UP)], 0.8),
        ])

        n24 = node_card(24, "P-0177", "7", "...", "...", hi=1, hc=TEAL_M)
        e7 = gedge("A-3102", "P-0177", "7", TEAL_M)
        n3102 = gnode("A-3102")
        self.steps("Crossing to a neighbour is the same move: P-0177 is node 24, at byte 360, and its chain starts at relationship 7.", [
            (lambda: [FadeOut(found), *lit(rcell[5], TEAL_M), rcell[4][0].animate.set_stroke(GREY_B, 2)], 0.6),
            "P-0177 is node",
            (lambda: [travel(Line(rcell[5][0].get_top(), ncell[24][0].get_bottom()), TEAL_M, 0.8)], 0.9),
            (lambda: [*lit(ncell[24], TEAL_M), FadeIn(blab(nx[24], NODE_Y, "360", TEAL_M)), ncell[2][0].animate.set_stroke(GREY_B, 2),
                      FadeOut(c28), FadeIn(n24), Transform(cnt, counter(6))], 0.8),
            "and its chain starts",
            (lambda: [travel(Line(n24[2][0].get_top(), rcell[7][0].get_bottom()), TEAL_M, 0.8)], 0.9),
            (lambda: [*lit(rcell[7], TEAL_M), Transform(cnt, counter(7)), FadeIn(n3102), GrowArrow(e7[0]), FadeIn(e7[1])], 0.8),
        ])

        rule = T("reads grow with A-3101's relationships, not with the graph", 20, GREEN_M).move_to([CARD_X0 + 3.9, CARD_Y - 1.35, 0])
        self.steps("The reads grow with A-3101's relationships, never with the graph: 37 relationships or 37 billion.", [
            (lambda: [*[glow(e[0], GOLD_M, 1.0) for e in (e28, e26, e5, e4)]], 1.0),
            "never with",
            (lambda: [FadeIn(rule, shift=0.1 * UP)], 0.7),
            "37 relationships or",
            (lambda: [glow(rstrip, GREY_A, 1.0)], 0.8),
        ])

        self.steps("Neo4j searches an index once, to find where the walk starts. "
                   "After that, a hop is a multiplication and a read.", [
            (lambda: [glow(ncell[2][0], GOLD_M, 1.15), glow(a3101[0], GOLD_M, 1.1)], 1.0),
            "After that",
            (lambda: [*[glow(rcell[i][0], GOLD_M, 1.15) for i in (28, 26, 5, 4)]], 1.0),
        ])
        self.wait(0.6)
