from sfz import *

SAY.insert(0, (r"\b8 KB\b", "8 kilobytes"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TOP_Y, MID_Y, LEAF_Y = 2.3, 0.9, -0.6     # the new root's band, the root (later the middle level), the leaves
CELL, NH = 0.72, 0.68                        # a key cell, a node's height
LX = [-5.0, -2.5, 0.0, 2.5, 5.0]            # leaf centres after the split
REQ = (-5.0, 2.55)
BAND = [-1.65, -2.15, -2.65]
CAP_Y = -3.25


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
        if t > dur + 0.1:
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, c=(0, -2.55), secs=3.0):
        bar = Line([c[0] - 1.0, c[1], 0], [c[0] + 1.0, c[1], 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def node(keys, x, y, color=TEAL_M, key_colors=None):
    """One page of the tree: a row of key cells."""
    g = VGroup()
    g.cells, g.labels = VGroup(), VGroup()
    n = len(keys)
    x0 = x - n * CELL / 2
    for i, k in enumerate(keys):
        c = Rectangle(width=CELL, height=NH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
        c.move_to([x0 + (i + 0.5) * CELL, y, 0])
        kc = (key_colors or {}).get(k, WHITE)
        g.cells.add(c)
        g.labels.add(M(str(k), 24, kc).move_to(c))
    g.add(g.cells, g.labels)
    g.keys = list(keys)
    return g


def anchor(nd, i):
    """Where the pointer to child i leaves a node: the cell boundaries along its bottom edge."""
    left = nd.cells[0].get_left()[0]
    return np.array([left + i * CELL, nd.cells[0].get_bottom()[1] - 0.02, 0])


def edges(parent, children, color=GREY_B):
    return VGroup(*[Line(anchor(parent, i), ch.get_top() + 0.02 * UP, stroke_width=2.5, color=color) for i, ch in enumerate(children)])


def links(leaves):
    out = VGroup()
    for a, b in zip(leaves, leaves[1:]):
        out.add(Arrow(a.get_right() + 0.12 * RIGHT, b.get_left() + 0.12 * LEFT, buff=0, stroke_width=2, color=GREY_D,
                      max_tip_length_to_length_ratio=0.2, max_stroke_width_to_length_ratio=10))
    return out


def req(s, color=YELLOW_M):
    return chip(s, color, 24, mono=True).move_to([REQ[0], REQ[1], 0])


def band(s, k, color=WHITE, size=24):
    return fit(T(s, size, color), 12.6).move_to([0, BAND[k], 0])


class BTreeSplit(Base):
    """store-04, section 2. The order-4 tree (root 30 50 70; leaves 10 20, 30 40, 50 60, 70 80 90). insert(100) is a
    search to the rightmost leaf, which overflows. A bigger page and an overflow chain both fail. The library: a full
    shelf gets a new shelf beside it. The leaf splits into 70 80 and 90 100, and 90 is copied up; the root overflows
    (30 50 70 90), splits, and pushes 70 up into a new root. get(60) reads three pages. PostgreSQL: 407 entries per leaf,
    key 408 splits into 367 and 42; rightmost splits keep 90%; 767 vs 1,038 leaf pages for time-ordered vs random ids.
    The moral, and a check: insert(85) splits nothing."""

    def construct(self):
        self.capm = None
        self.title_card("A full page splits", "and the tree grows at the top")

        # ---------------- scene 1: an insert is a search ----------------
        root = node([30, 50, 70], 0, MID_Y, GOLD_M)
        L = [node([10, 20], LX[0], LEAF_Y), node([30, 40], LX[1], LEAF_Y), node([50, 60], LX[2], LEAF_Y), node([70, 80, 90], 2.8, LEAF_Y)]
        E = edges(root, L)
        K = links(L)
        self.steps("Here's a small B+tree. Each node is one page, and in this toy a page holds at most three keys. "
                   "The root's signposts send each search to one leaf, and the leaves hold every key, in order.", [
            (lambda: [FadeIn(root, shift=0.1 * DOWN)], 0.7),
            (lambda: [Create(E), LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in L], lag_ratio=0.15)], 1.2),
            (lambda: [FadeIn(K)], 0.4),
            "at most three keys",
            (lambda: [glow(L[3].cells, TEAL_M, 1.04), *self.cap("this toy: a node holds at most 3 keys")], 0.7),
            "The root's signposts",
            (lambda: [glow(root.cells, GOLD_M, 1.04), *self.cap("root: signposts", GOLD_M)], 0.6),
            "and the leaves hold",
            (lambda: [LaggedStart(*[glow(l.cells, TEAL_M, 1.04) for l in L], lag_ratio=0.15), *self.cap("leaves: every key, in order", TEAL_M)], 0.9),
        ])
        q = req("insert(100)")
        self.steps("Let's insert 100. An insert starts as a search. At the root, 100 isn't below 30, 50 or 70, "
                   "so we follow the last pointer, to the leaf 70, 80, 90.", [
            (lambda: [*self.uncap(), FadeIn(q, shift=0.1 * DOWN)], 0.5),
            "An insert starts",
            (lambda: self.cap("an insert starts as a search", WHITE), 0.5),
            "100 isn't below",
            (lambda: [LaggedStart(*[Indicate(root.labels[i], color=YELLOW_M, scale_factor=1.4) for i in range(3)], lag_ratio=0.4)], 1.4),
            "so we follow",
            (lambda: [E[3].animate.set_color(YELLOW_M).set_stroke(width=4)], 0.5),
            "to the leaf",
            (lambda: [glow(L[3].cells, YELLOW_M, 1.04)], 0.6),
        ])
        top_band = DashedVMobject(Rectangle(width=4.2, height=0.85, stroke_color=GREY_B, stroke_width=2), num_dashes=56).move_to([0.6, TOP_Y, 0])
        self.steps("But that leaf is full. Where does 100 go? And while we're at it: this tree has two levels. "
                   "How would it ever get a third?", [
            (lambda: self.cap("the leaf is full: where does 100 go?", YELLOW_M), 0.5),
            "this tree has two",
            (lambda: self.cap("two levels today: how would it ever get a third?", WHITE), 0.5),
            "How would it",
            (lambda: [Create(top_band)], 0.7),
        ], after=0.4)

        # ---------------- scene 2: more room? ----------------
        L3b = node([70, 80, 90, 100], 2.8, LEAF_Y, RED_M, {100: YELLOW_M})
        E3b = Line(anchor(root, 3), L3b.get_top() + 0.02 * UP, stroke_width=4, color=YELLOW_M)
        self.steps("100 goes into the leaf in key order. Now the leaf has four keys, and a node may hold three. "
                   "On a real page, the new entry doesn't fit in 8 KB.", [
            (lambda: [*self.uncap(), FadeOut(top_band), FadeOut(K[2]), Transform(L[3], L3b), Transform(E[3], E3b)], 0.8),
            "Now the leaf has",
            (lambda: self.cap("4 keys: one more than a node can hold", RED_M), 0.5),
            "On a real page",
            (lambda: self.cap("on a real page: the new entry doesn't fit in 8 KB", RED_M), 0.5),
        ])
        x1 = tick(False, 0.3).move_to([2.8, LEAF_Y - 0.75, 0])
        self.steps("The first idea: make the page bigger. But pages have a fixed size. That's the whole point of pages.", [
            (lambda: self.cap("idea 1: a bigger page"), 0.5),
            (lambda: [L[3].animate.stretch(1.25, 0)], 0.6),
            "But pages have",
            (lambda: [L[3].animate.stretch(1 / 1.25, 0), FadeIn(x1), *self.cap("a page has a fixed size", RED_M)], 0.6),
        ])
        ov1 = DashedVMobject(Rectangle(width=CELL * 2, height=0.56, stroke_color=GREY_B, stroke_width=2.5), num_dashes=20)
        ov1.move_to([2.8, -1.7, 0])
        ov2 = ov1.copy().move_to([2.8, -2.5, 0])
        o1 = M("110 120", 20, GREY_B).move_to(ov1)
        o2 = M("…", 22, GREY_B).move_to(ov2)
        c1 = DashedLine(L[3].get_bottom() + 0.02 * DOWN, ov1.get_top(), dash_length=0.06, stroke_width=2, color=GREY_B)
        c2 = DashedLine(ov1.get_bottom(), ov2.get_top(), dash_length=0.06, stroke_width=2, color=GREY_B)
        x2 = tick(False, 0.3).move_to([4.2, -2.15, 0])
        self.steps("The second idea: hang an extra page off the full leaf, an overflow page. Every key that lands there piles "
                   "into the chain, which has to be read page by page. That's the slow search we built the tree to escape. "
                   "It's a full shelf with a cardboard box next to it, then another box next to that.", [
            (lambda: [FadeOut(x1), *self.cap("idea 2: an overflow page, chained to the leaf")], 0.5),
            "an overflow page",
            (lambda: [Create(c1), Create(ov1), FadeIn(o1)], 0.7),
            "Every key that lands",
            (lambda: [Create(c2), Create(ov2), FadeIn(o2)], 0.7),
            "which has to be read",
            (lambda: [*self.cap("a chain, read page by page: the slow search again", RED_M)], 0.5),
            "That's the slow",
            (lambda: [FadeIn(x2)], 0.4),
            "It's a full shelf",
            (lambda: self.cap("a full shelf, a cardboard box, then another box", GREY_B), 0.5),
        ], after=0.4)

        # ---------------- scene 3: the library ----------------
        self.steps("Think of the library from the last section. The board by the door says which floor, a sign on each floor "
                   "says which shelf, and each shelf keeps its books in order.", [
            (lambda: [FadeOut(VGroup(ov1, ov2, o1, o2, c1, c2, x2)), *self.cap("the library", WHITE)], 0.6),
            "The board by the door",
            (lambda: [glow(root.cells, GOLD_M, 1.04)], 0.6),
            "and each shelf",
            (lambda: [LaggedStart(*[glow(l.cells, TEAL_M, 1.04) for l in L[:3]], lag_ratio=0.15)], 0.8),
        ])
        self.steps("When a shelf is full, the librarian puts a new shelf right next to it, moves the upper half of the books "
                   "onto it, and adds one line to the floor sign: from here on, the new shelf.", [
            (lambda: self.cap("a full shelf: a new shelf beside it, half the books move, one new line on the sign", WHITE), 0.6),
            "puts a new shelf",
            (lambda: [glow(L[3].cells, RED_M, 1.04)], 0.6),
            "adds one line",
            (lambda: [glow(root.cells, GOLD_M, 1.04)], 0.6),
        ])
        self.steps("So the shelves are the leaves, the floor signs are the internal nodes, and the board by the door is the root.", [
            "the shelves are",
            (lambda: [*self.cap("shelves: leaves", TEAL_M), LaggedStart(*[glow(l.cells, TEAL_M, 1.04) for l in L[:3]], lag_ratio=0.1)], 0.6),
            "the floor signs",
            (lambda: self.cap("floor signs: internal nodes (signposts between root and leaves)", GOLD_M), 0.5),
            "and the board",
            (lambda: [*self.cap("the board by the door: the root", GOLD_M), glow(root.cells, GOLD_M, 1.04)], 0.6),
        ], after=0.4)

        # ---------------- scene 4: split the leaf ----------------
        L3 = node([70, 80], LX[3], LEAF_Y)
        L4 = node([90, 100], LX[4], LEAF_Y, TEAL_M, {100: YELLOW_M})
        lk = links([L3, L4])[0]
        k2 = links([L[2], L3])[0]
        self.steps("Let's do that to our leaf. A new leaf appears on its right, and the upper half, 90 and 100, moves into it. "
                   "The two leaves are linked, side by side.", [
            (lambda: [*self.uncap(), E[3].animate.set_color(GREY_B).set_stroke(width=2.5)], 0.4),
            "A new leaf appears",
            (lambda: [Transform(L[3], L3), FadeIn(L4, shift=0.3 * RIGHT), E[3].animate.put_start_and_end_on(anchor(root, 3), L3.get_top() + 0.02 * UP)], 1.0),
            "The two leaves are",
            (lambda: [GrowArrow(lk), GrowArrow(k2)], 0.5),
        ])
        self.steps("Now the parent needs a pointer to the new leaf, and a signpost that says where it starts. "
                   "Which key goes up, and does it leave the leaf? Pause and guess.", [
            "Now the parent",
            (lambda: [glow(root.cells, GOLD_M, 1.04)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        root2 = node([30, 50, 70, 90], 0, MID_Y, RED_M, {90: GREEN_M})
        up90 = L4.labels[0].copy()
        E4 = Line(anchor(root2, 4), L4.get_top() + 0.02 * UP, stroke_width=2.5, color=GREEN_M)
        self.steps("90, the new leaf's first key. And it's copied, not moved: 90 stays in the leaf, because the leaves must hold "
                   "every key. This is a split.", [
            (lambda: [*self.uncap(), L4.labels[0].animate.set_color(GREEN_M)], 0.4),
            "And it's copied",
            (lambda: [up90.animate.move_to(root2.labels[3]).set_color(GREEN_M)], 0.8),
            (lambda: [FadeOut(up90), ReplacementTransform(root, root2), *[E[i].animate.put_start_and_end_on(anchor(root2, i), E[i].get_end()) for i in range(4)],
                      Create(E4)], 0.7),
            "90 stays in the leaf",
            (lambda: [Indicate(L4.labels[0], color=GREEN_M, scale_factor=1.4), *self.cap("leaf split: 90 is copied up, and stays in the leaf", GREEN_M)], 0.7),
            "This is a split",
            (lambda: [glow(L[3].cells, TEAL_M, 1.04), glow(L4.cells, TEAL_M, 1.04)], 0.6),
        ], after=0.4)

        # ---------------- scene 5: the root overflows ----------------
        root = root2
        left = node([30, 50], -2.5, MID_Y, GOLD_M)
        right = node([90], 3.75, MID_Y, GOLD_M)
        top = node([70], 0.6, TOP_Y, GOLD_M, {70: PURPLE_M})
        leaves = [L[0], L[1], L[2], L[3], L4]
        self.edges_l = edges(left, leaves[:3])
        self.edges_r = edges(right, leaves[3:])
        self.steps("But now the root has four keys, one too many. So it splits too, with one difference. "
                   "Its keys are only signposts, so the middle key, 70, doesn't need to stay below. "
                   "It's pushed up, and it leaves both halves. 30 and 50 keep three children. 90 keeps two.", [
            (lambda: [*self.uncap(), glow(root.cells, RED_M, 1.04), root.labels[3].animate.set_color(WHITE)], 0.6),
            "one too many",
            (lambda: self.cap("the root: 4 keys, one too many", RED_M), 0.4),
            "So it splits too",
            (lambda: self.cap("it splits too, with one difference", WHITE), 0.4),
            "the middle key, 70",
            (lambda: [root.labels[2].animate.set_color(PURPLE_M), Indicate(root.labels[2], color=PURPLE_M, scale_factor=1.4)], 0.7),
            "It's pushed up",
            (lambda: [FadeOut(VGroup(*E, E4)), root.labels[2].animate.move_to([0.6, TOP_Y, 0]),
                      root.cells[2].animate.set_opacity(0)], 0.9),
            (lambda: [FadeIn(left), FadeIn(right), FadeOut(VGroup(root.cells[0], root.cells[1], root.cells[3], root.labels[0], root.labels[1], root.labels[3])),
                      *self.cap("internal split: 70 is pushed up, and stays in neither half", PURPLE_M)], 0.8),
            "30 and 50 keep",
            (lambda: [Create(self.edges_l)], 0.7),
            "90 keeps two",
            (lambda: [Create(self.edges_r)], 0.6),
        ])
        e_top = edges(top, [left, right])
        self.steps("And the node that split was the root, so 70 has nowhere to go. A new root is made above it, with one key "
                   "and two children.", [
            "so 70 has nowhere",
            (lambda: [Indicate(root.labels[2], color=PURPLE_M, scale_factor=1.3)], 0.6),
            "A new root is made",
            (lambda: [FadeIn(top.cells), FadeOut(root.labels[2]), FadeIn(top.labels), *self.cap("a new root, with one key and two children", GOLD_M)], 0.7),
            (lambda: [Create(e_top)], 0.6),
        ], after=0.4)

        # ---------------- scene 6: growing at the top ----------------
        path = VGroup(e_top[0].copy(), self.edges_l[2].copy()).set_color(YELLOW_M).set_stroke(width=4)
        self.steps("That's the only way a B+tree gets taller: at the top, never at the bottom. So every leaf is always at the same "
                   "depth, and every search reads the same number of pages.", [
            (lambda: self.cap("a B+tree grows only at the top", WHITE), 0.5),
            "So every leaf",
            (lambda: [LaggedStart(*[glow(l.cells, TEAL_M, 1.04) for l in leaves], lag_ratio=0.1), *self.cap("every leaf at the same depth", TEAL_M)], 1.0),
        ])
        g60 = req("get(60)")
        self.steps("A search for 60 now reads three: the root says below 70, the next node says at least 50, and the leaf holds it.", [
            (lambda: [*self.uncap(), Transform(q, g60)], 0.5),
            "the root says",
            (lambda: [glow(top.cells, YELLOW_M, 1.05), Create(path[0])], 0.6),
            "the next node",
            (lambda: [glow(left.cells, YELLOW_M, 1.04), Create(path[1])], 0.6),
            "and the leaf",
            (lambda: [glow(L[2].cells, YELLOW_M, 1.05), L[2].labels[1].animate.set_color(YELLOW_M), *self.cap("get(60): 3 page reads", YELLOW_M)], 0.6),
        ])
        self.steps("Here the library picture breaks. A library grows at its edges, with a new wing. This tree grows by putting a new "
                   "sign above the board at the door, so every shelf stays the same number of signs from the entrance.", [
            (lambda: [FadeOut(path), L[2].labels[1].animate.set_color(WHITE), *self.cap("where the library picture breaks", WHITE)], 0.5),
            "This tree grows",
            (lambda: [glow(top.cells, GOLD_M, 1.06), *self.cap("a library adds a wing; a B+tree adds a sign above the door", GOLD_M)], 0.7),
        ], after=0.4)

        # ---------------- scene 7: real pages ----------------
        r1 = band("PostgreSQL: 407 entries fit in one leaf page", 0)
        r2 = band("key 408: a new root above two leaves, of 367 and 42 entries", 1)
        r3 = band("the rightmost leaf split: the left page stays 90% full", 2, GREEN_M)
        self.steps("On a real PostgreSQL page, a leaf holds 407 of these entries. In the Try it, keys 1 to 407 fit in one leaf, "
                   "which is also the root. Key 408 splits it, and the tree grows a level: a new root on top, one leaf with "
                   "367 entries, and a new leaf with 42.", [
            (lambda: [*self.uncap(), FadeOut(q), FadeIn(r1, shift=0.1 * UP)], 0.6),
            "Key 408 splits",
            (lambda: [FadeIn(r2, shift=0.1 * UP)], 0.6),
        ])
        self.steps("Why so uneven? The leaf that split was the rightmost one. When every new key is bigger than the last, "
                   "PostgreSQL keeps the left page 90% full, because nothing will land there again.", [
            "The leaf that split",
            (lambda: [glow(L4.cells, TEAL_M, 1.05)], 0.6),
            "PostgreSQL keeps",
            (lambda: [FadeIn(r3, shift=0.1 * UP)], 0.6),
        ], after=0.4)

        # ---------------- scene 8: what your keys cost ----------------
        unit = 5.6 / 1038
        bx = -6.0
        b1 = Rectangle(width=767 * unit, height=0.34, stroke_width=0).set_fill(GREEN_M, 0.9)
        b1.move_to([bx + b1.width / 2, BAND[0], 0])
        b2 = Rectangle(width=1038 * unit, height=0.34, stroke_width=0).set_fill(RED_M, 0.85)
        b2.move_to([bx + b2.width / 2, BAND[1] - 0.15, 0])
        v1 = T("time-ordered ids: 767 leaf pages, about 90% full", 22, GREEN_M).next_to(b1, RIGHT, buff=0.2)
        v2 = T("random ids: 1,038 leaf pages, about 67% full", 22, RED_M).next_to(b2, RIGHT, buff=0.2)
        self.steps("So the kind of key decides how full your pages are. Random keys split pages in the middle, and pages settle "
                   "about two-thirds full. In the Try it, 200,000 random ids took 1,038 leaf pages. 200,000 time-ordered ids, "
                   "each bigger than the last, took 767. That's a third more pages for the same rows.", [
            (lambda: [FadeOut(VGroup(r1, r2, r3)), *self.cap("the kind of key decides how full the pages are", WHITE)], 0.6),
            "Random keys split",
            (lambda: [LaggedStart(*[glow(l.cells, RED_M, 1.04) for l in leaves[:3]], lag_ratio=0.15)], 0.8),
            "In the Try it",
            (lambda: [*self.cap("the Try it: 200,000 ids each way", WHITE), GrowFromEdge(b2, LEFT), FadeIn(v2)], 0.8),
            "200,000 time-ordered",
            (lambda: [GrowFromEdge(b1, LEFT), FadeIn(v1)], 0.8),
            "That's a third more",
            (lambda: self.cap("a third more pages for the same rows", RED_M), 0.5),
        ])
        self.steps("And each split writes three pages, the old leaf, the new leaf and the parent, and logs every change first.", [
            (lambda: [glow(L[3].cells, YELLOW_M, 1.05), glow(L4.cells, YELLOW_M, 1.05), glow(right.cells, YELLOW_M, 1.05),
                      *self.cap("a split writes 3 pages, and logs each change first", WHITE)], 1.0),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So: a full leaf splits and copies its first key up. A full internal node splits and pushes its middle key up. "
                   "And when the root splits, the tree grows at the top.", [
            (lambda: [FadeOut(VGroup(b1, b2, v1, v2)), *self.cap("leaf: copy the first key up; internal node: push the middle key up", YELLOW_M, 26)], 0.7),
            "And when the root",
            (lambda: [*self.cap("the root splits: the tree grows at the top", YELLOW_M, 26), glow(top.cells, GOLD_M, 1.06)], 0.6),
        ], after=0.5)
        q85 = req("insert(85)")
        self.steps("One quick check. Insert 85 into the new tree. Does anything split? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(q85, shift=0.1 * DOWN)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(c=(0, -1.9))
        p85 = VGroup(e_top[1].copy(), self.edges_r[0].copy()).set_color(YELLOW_M).set_stroke(width=4)
        L3c = node([70, 80, 85], LX[3], LEAF_Y, GREEN_M, {85: YELLOW_M})
        self.steps("No. The root sends 85 right, the node 90 sends it left, and the leaf 70, 80 has room. One page changes.", [
            (lambda: [*self.uncap(), glow(top.cells, YELLOW_M, 1.05), Create(p85[0])], 0.6),
            "the node 90",
            (lambda: [glow(right.cells, YELLOW_M, 1.06), Create(p85[1])], 0.6),
            "and the leaf",
            (lambda: [Transform(L[3], L3c), self.edges_r[0].animate.put_start_and_end_on(self.edges_r[0].get_start(), L3c.get_top() + 0.02 * UP),
                      p85[1].animate.put_start_and_end_on(p85[1].get_start(), L3c.get_top() + 0.02 * UP),
                      lk.animate.put_start_and_end_on(L3c.get_right() + 0.12 * RIGHT, lk.get_end()),
                      k2.animate.put_start_and_end_on(k2.get_start(), L3c.get_left() + 0.12 * LEFT)], 0.7),
            "One page changes",
            (lambda: self.cap("insert(85): no split, one page changes", GREEN_M), 0.5),
        ], after=0.3)
        self.play(FadeOut(p85), *self.cap("leaf: copy the first key up; internal node: push the middle key up", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
