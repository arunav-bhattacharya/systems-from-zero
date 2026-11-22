import hashlib

from sfz import *

SAY.insert(0, (r"\bA-1001\b", "A ten oh one"))
# the machine called A is said "eh", not "uh"
SAY.insert(0, (r"\bA, B and C\b", "eh, B and C"))
SAY.insert(0, (r"\bnode A\b", "node eh"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RC = np.array([-3.0, 0.0, 0])            # the ring
RR = 2.45
PX0, PX1 = 1.7, 6.6                      # the shares panel
ROW_Y = [1.85 - 0.55 * k for k in range(6)]
BAR_X0, BAR_FULL = 2.45, 2.4             # a bar of length BAR_FULL is 50% of the ring
PCT_X1 = PX1 - 0.1
TAB_Y = [-1.68 - 0.3 * k for k in range(5)]
CAP_Y, BAR_Y = -3.3, -2.85
NODES = "ABCDEF"
NCOL = {"A": BLUE_M, "B": TEAL_M, "C": GREEN_M, "D": YELLOW_M, "E": GOLD_M, "F": PURPLE_M}


def h(s):
    """Where a name or key sits on the ring, as a fraction of the way round (MD5, as in the lesson's demos)."""
    return int.from_bytes(hashlib.md5(s.encode()).digest(), "big") / 2 ** 128


def tokens(nodes, T=1):
    return sorted((h(f"node-{n}#{i}"), n) for n in nodes for i in range(T))


def shares(nodes, T=1):
    tk = tokens(nodes, T)
    sh = {n: 0.0 for n in nodes}
    for i, (t, n) in enumerate(tk):
        sh[n] += t - (tk[i - 1][0] - (1 if i == 0 else 0))
    return sh


def ang(p):
    """Fraction of the way round, clockwise from the top, as an angle."""
    return np.pi / 2 - 2 * np.pi * p


def on_ring(p, r=RR):
    return RC + r * np.array([np.cos(ang(p)), np.sin(ang(p)), 0])


KEY_P = h("A-1001")
LABEL_NUDGE = {"C": 0.022, "D": -0.022}   # C and D sit close together; keep their letters apart


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

    def steps(self, text, items, after=0.3):
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays;
        a number waits that long; a string waits until about where that phrase is spoken."""
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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


# ---- the pieces ----
def arcs(nodes, T=1, width=12):
    """The ring coloured by owner: each token owns the arc that ends at it."""
    tk = tokens(nodes, T)
    g = VGroup()
    for i, (t, n) in enumerate(tk):
        prev = tk[i - 1][0] - (1 if i == 0 else 0)
        g.add(Arc(radius=RR, start_angle=ang(t), angle=2 * np.pi * (t - prev), arc_center=RC, stroke_width=width, color=NCOL[n]))
    return g


def token_marks(nodes):
    """One token per node: a dot on the ring and the node's letter outside it."""
    g = VGroup()
    for t, n in tokens(nodes):
        g.add(VGroup(Dot(on_ring(t), radius=0.11, color=WHITE).set_stroke(NCOL[n], 3),
                     T(n, 28, NCOL[n]).move_to(on_ring(t + LABEL_NUDGE.get(n, 0), RR + 0.45))))
    return g


def share_row(k, n, frac, color=None):
    y = ROW_Y[k]
    c = color or NCOL[n]
    bar = Rectangle(width=max(0.02, BAR_FULL * frac / 0.5), height=0.3, stroke_width=0).set_fill(c, 0.8)
    left_at(bar, BAR_X0, y)
    return VGroup(T(n, 26, c).move_to([PX0 + 0.3, y, 0]), bar, right_at(M(f"{100 * frac:.1f}%", 22, c), PCT_X1, y))


class ConsistentHashing(Base):
    """shard-02, section 0. Six friends cut a pizza at random: unequal slices. hash mod S moves 80% of keys going from
    4 machines to 5 (only 4 of any 20 hash values keep their remainder). The ring: tokens at the hash of each node's
    name, a key belongs to the first token clockwise, so a node owns the arc ending at its token. E joins and takes keys
    from D only (A-1001 moves). With one token each, six nodes get 44.0% down to 1.6%. Many tokens per node (virtual
    nodes): 16, 64, 256 tokens give 24.3%, 18.6%, 17.4%, not smoothly (4 gave 23.4%). Moral, and a check."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_ring(self, nodes, T=1, marks=True):
        new_a = arcs(nodes, T)
        new_m = token_marks(nodes) if marks else VGroup()
        old = VGroup(*[m for m in (self.ring_a, self.ring_m) if m is not None])
        self.ring_a, self.ring_m = new_a, new_m
        return ([FadeOut(old)] if len(old) else []) + [FadeIn(new_a)] + ([FadeIn(new_m)] if len(new_m) else [])

    def set_shares(self, nodes, T=1, order=None):
        sh = shares(nodes, T)
        order = order or list(nodes)
        new = VGroup(*[share_row(k, n, sh[n]) for k, n in enumerate(order)])
        old, self.rows = self.rows, new
        return [swap(old, new, RIGHT)]

    def construct(self):
        self.capm = self.ring_a = self.ring_m = self.rows = None
        self.title_card("Who gets the biggest slice?", "a ring of hash values, and why each machine needs many places on it")

        # ---------------- scene 1: the pizza ----------------
        pc = np.array([0, 0.2, 0])
        pizza = Circle(radius=2.2, stroke_color=GOLD_M, stroke_width=4).set_fill(fillc(GOLD_M, 0.25), 1).move_to(pc)
        cuts_p = sorted([0.04, 0.11, 0.16, 0.47, 0.55, 0.62])   # six cuts made at random: hand-picked for the picture
        cuts = VGroup(*[Line(pc, pc + 2.2 * np.array([np.cos(ang(p)), np.sin(ang(p)), 0]), stroke_width=4, color=WHITE) for p in cuts_p])
        friends = VGroup(*[Dot(pc + 2.6 * np.array([np.cos(ang(p)), np.sin(ang(p)), 0]), radius=0.12, color=WHITE) for p in cuts_p])
        self.steps("Six friends share a round pizza. Each one makes a single cut wherever they like, and takes the slice that ends at their own cut.", [
            (lambda: [FadeIn(pizza)], 0.7),
            "Each one makes",
            (lambda: [LaggedStart(*[AnimationGroup(Create(c), FadeIn(f)) for c, f in zip(cuts, friends)], lag_ratio=0.3)], 1.8),
        ])
        big = AnnularSector(inner_radius=0, outer_radius=2.2, angle=2 * np.pi * (cuts_p[3] - cuts_p[2]), start_angle=ang(cuts_p[3]),
                            arc_center=pc, color=GOLD_M, fill_opacity=0.55, stroke_width=0)
        tiny = AnnularSector(inner_radius=0, outer_radius=2.2, angle=2 * np.pi * (cuts_p[2] - cuts_p[1]), start_angle=ang(cuts_p[2]),
                             arc_center=pc, color=RED_M, fill_opacity=0.6, stroke_width=0)
        self.steps("Random cuts sound fair, since nobody chose where anyone else would cut. Then the slices come out, "
                   "and they're nothing like equal. Keep that pizza in mind.", [
            "Then the slices",
            (lambda: [FadeIn(big), FadeIn(tiny)], 0.8),
            "nothing like equal",
            (lambda: self.cap("random cuts: slices nothing like equal", YELLOW_M), 0.6),
        ])

        # ---------------- scene 2: hash mod S ----------------
        self.steps("Now the payments company. It spreads payments over its machines with a hash: a formula that turns a key into a big "
                   "random-looking number. It divides that number by the number of machines, and keeps the remainder.", [
            (lambda: [FadeOut(VGroup(pizza, cuts, friends, big, tiny)), *self.uncap()], 0.7),
            "with a hash",
            (lambda: self.cap("hash: a key turned into a big random-looking number"), 0.5),
            "It divides",
            (lambda: self.cap("machine = hash mod (number of machines): the remainder", WHITE), 0.5),
        ])
        xs = [-4.95 + 0.58 * k for k in range(20)]
        cells = VGroup(*[VGroup(Square(0.5, stroke_color=GREY_B, stroke_width=2).move_to([x, 1.3, 0]), M(str(k), 20).move_to([x, 1.3, 0]))
                         for k, x in enumerate(xs)])
        lab_h = T("hash", 20, GREY_B).move_to([-6.05, 1.3, 0])
        lab4 = M("mod 4", 20, BLUE_M).move_to([-6.05, 0.45, 0])
        lab5 = M("mod 5", 20, GOLD_M).move_to([-6.05, -0.25, 0])
        r4 = VGroup(*[M(str(k % 4), 24, BLUE_M).move_to([x, 0.45, 0]) for k, x in enumerate(xs)])
        r5 = VGroup(*[M(str(k % 5), 24, GOLD_M).move_to([x, -0.25, 0]) for k, x in enumerate(xs)])
        self.steps("With four machines, the remainder picks machine 0, 1, 2 or 3. That spreads keys evenly. Until the day a fifth machine arrives.", [
            (lambda: [*self.uncap(), FadeIn(cells), FadeIn(lab_h)], 0.7),
            "the remainder picks",
            (lambda: [FadeIn(lab4), LaggedStart(*[FadeIn(d) for d in r4], lag_ratio=0.05)], 1.2),
            "a fifth machine",
            (lambda: [FadeIn(lab5), LaggedStart(*[FadeIn(d) for d in r5], lag_ratio=0.05)], 1.2),
        ])
        self.steps("Here are twenty hash values in a row, with their remainder for four machines and for five. "
                   "How many keep the same machine? Pause and guess.", [
            "How many keep",
            (lambda: self.cap("how many keep the same machine?", YELLOW_M), 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        keep = VGroup(*[SurroundingRectangle(VGroup(cells[k], r5[k]), color=GREEN_M, buff=0.06, stroke_width=3) for k in range(4)])
        self.steps("Only four. Zero, one, two and three. Every other key moves, so going from four machines to five moves 80% of the keys.", [
            (lambda: [*self.uncap(), Create(keep)], 0.8),
            "Every other key",
            (lambda: [*[c[0].animate.set_stroke(RED_M) for c in cells[4:]], *self.cap("4 of 20 stay; 16 of 20 move: 80%", RED_M)], 0.8),
        ])
        self.steps("That's 80% of the data copied across the network, while the machines are still taking card payments. "
                   "All that, to add one machine.", [
            "All that",
            (lambda: self.cap("80% of the data moves, to add one machine", RED_M), 0.5),
        ])
        self.steps("What we'd like is for the new machine to take its fair share, and for every other key to stay put.", [
            (lambda: self.cap("wanted: the new machine takes a fair share; nothing else moves", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 3: the ring ----------------
        base = Circle(radius=RR, stroke_color=GREY_D, stroke_width=12).move_to(RC)
        zero = VGroup(Line(on_ring(0, RR - 0.25), on_ring(0, RR + 0.25), stroke_width=3, color=GREY_B))
        self.steps("Here's the idea. Lay every possible hash value around a circle, like the edge of the pizza. That circle is the ring.", [
            (lambda: [FadeOut(VGroup(cells, lab_h, lab4, lab5, r4, r5, keep)), *self.uncap()], 0.6),
            "around a circle",
            (lambda: [Create(base), FadeIn(zero)], 1.0),
            "the ring",
            (lambda: self.cap("the ring: every hash value, round a circle", WHITE), 0.5),
        ])
        four = "ABCD"
        self.steps("Each machine sits at the hash of its own name. That place is its token: the machine's cut in the pizza.", [
            "Each machine",
            (lambda: self.set_ring(four), 0.9),
            "its token",
            (lambda: self.cap("token: where a machine sits on the ring (its cut)", WHITE), 0.5),
        ])
        key = VGroup(Dot(on_ring(KEY_P, RR - 0.45), radius=0.09, color=WHITE),
                     M("A-1001", 20).move_to(on_ring(KEY_P, RR - 0.45) + np.array([-0.15, -0.42, 0])))
        d_tok = dict((n, t) for t, n in tokens("ABCDEF"))
        walk = Arc(radius=RR - 0.45, start_angle=ang(d_tok["D"]), angle=2 * np.pi * (d_tok["D"] - KEY_P), arc_center=RC,
                   stroke_width=4, color=WHITE).reverse_direction()
        self.steps("A key sits at the hash of the key, and belongs to the first machine you meet walking clockwise. "
                   "Take key A-1001. Walk clockwise, and the first token is D's.", [
            "A key sits",
            (lambda: [*self.cap("a key belongs to the first token clockwise")], 0.5),
            "Take key",
            (lambda: [FadeIn(key, scale=0.6)], 0.5),
            "Walk clockwise",
            (lambda: [Create(walk)], 1.4),
            "D's",
            (lambda: [Indicate(self.ring_m[0], color=YELLOW_M, scale_factor=1.4)], 0.7),
        ])
        self.steps("So each machine owns the arc that ends at its token. That arc is its slice.", [
            (lambda: [FadeOut(walk), *self.cap("each machine owns the arc ending at its token: its slice", WHITE)], 0.5),
            "owns the arc",
            (lambda: [*self.set_ring(four), *self.set_shares(four)], 0.9),
        ])

        # ---------------- scene 4: a machine joins ----------------
        moved = Arc(radius=RR + 0.0, start_angle=ang(d_tok["E"]), angle=2 * np.pi * (d_tok["E"] - (d_tok["B"] - 1)), arc_center=RC,
                    stroke_width=20, color=GOLD_M)
        etok = VGroup(Dot(on_ring(d_tok["E"]), radius=0.11, color=WHITE).set_stroke(GOLD_M, 3),
                      T("E", 28, GOLD_M).move_to(on_ring(d_tok["E"], RR + 0.45)))
        self.steps("Now a fifth machine joins, E. Its token lands inside D's arc. Which keys move? "
                   "Only the ones on the arc just before E's token, and all of them come from D.", [
            "a fifth machine",
            (lambda: [FadeIn(etok, scale=0.5)], 0.6),
            "Its token lands",
            (lambda: [Indicate(etok, color=GOLD_M, scale_factor=1.3)], 0.7),
            "Only the ones",
            (lambda: [Create(moved)], 1.0),
            "all of them come from D",
            (lambda: [*self.set_ring("ABCDE"), *self.set_shares("ABCDE"), FadeOut(moved), FadeOut(etok)], 0.9),
        ])
        self.steps("A-1001 is one of them, so it moves to E. A, B and C don't lose a single key.", [
            (lambda: [Indicate(key, color=GOLD_M, scale_factor=1.3)], 0.8),
            "A, B and C",
            (lambda: [*[Indicate(self.rows[k], color=NCOL[n], scale_factor=1.05) for k, n in enumerate("ABC")],
                      *self.cap("only D gave keys to E; nothing else moved", GREEN_M)], 0.9),
        ])
        self.steps("That's consistent hashing. Consistent here means most keys stay where they were when the machines change. "
                   "It has nothing to do with consistent data. Cassandra, a free database built to spread over many machines, is built on it.", [
            (lambda: self.cap("consistent hashing: most keys stay put when machines change", WHITE), 0.6),
            "nothing to do",
            (lambda: self.cap("(not about consistent data)"), 0.4),
            "Cassandra",
            (lambda: self.cap("Cassandra is built on it"), 0.4),
        ])

        # ---------------- scene 5: break "a hash is fair" ----------------
        six_order = list("ABCDEF")
        self.steps("So far so good. Now add a sixth machine, F, and look at the slices.", [
            (lambda: [*self.uncap(), FadeOut(key)], 0.4),
            "add a sixth",
            (lambda: [*self.set_ring("ABCDEF"), *self.set_shares("ABCDEF", order=six_order)], 1.0),
        ])
        fair = DashedLine([BAR_X0 + BAR_FULL * (1 / 6) / 0.5, ROW_Y[0] + 0.35, 0], [BAR_X0 + BAR_FULL * (1 / 6) / 0.5, ROW_Y[5] - 0.22, 0],
                          dash_length=0.08, stroke_width=2, color=WHITE)
        fair_l = T("fair: 16.7%", 18).next_to(fair, UP, buff=0.08)
        self.steps("E owns 44% of the ring. C owns 1.6%. A fair share for six is 16.7%. Well... E got the pizza, and C got a crumb.", [
            "E owns",
            (lambda: [Indicate(self.rows[4], color=GOLD_M, scale_factor=1.08)], 0.7),
            "C owns",
            (lambda: [Indicate(self.rows[2], color=GREEN_M, scale_factor=1.08)], 0.7),
            "A fair share",
            (lambda: [Create(fair), FadeIn(fair_l)], 0.6),
            "Well...",
            (lambda: self.cap("one token each: 44.0% down to 1.6%", RED_M), 0.5),
        ], after=0.4)
        self.steps("And it wasn't bad luck. A good hash is as good as random, and random points on a circle clump. "
                   "For six machines, the biggest gap averages about 41%. Thousands of keys average out. Six places don't.", [
            "random points",
            (lambda: [*[Indicate(m[0], color=WHITE, scale_factor=1.6) for m in self.ring_m]], 0.9),
            "the biggest gap",
            (lambda: self.cap("six random places: the biggest gap averages about 41%"), 0.5),
            "Six places don't",
            (lambda: self.cap("thousands of keys average out; six places don't", YELLOW_M), 0.5),
        ])
        self.steps("The machine with 44% stores 44% of the data and answers 44% of the requests, while its neighbour sits nearly idle. "
                   "And buying a seventh machine doesn't fix it, because its token lands at random too.", [
            "stores 44%",
            (lambda: [Indicate(self.rows[4], color=GOLD_M, scale_factor=1.08)], 0.7),
            "a seventh machine",
            (lambda: self.cap("a seventh machine's token lands at random too", RED_M), 0.5),
        ])

        # ---------------- scene 6: many tokens ----------------
        self.steps("The fix comes straight from the pizza. Instead of one cut each, every friend makes sixteen thin cuts. "
                   "Each machine gets sixteen tokens, at the hashes of node A number 0, node A number 1, and so on.", [
            (lambda: self.uncap(), 0.3),
            "sixteen thin cuts",
            (lambda: self.cap("sixteen thin cuts each", WHITE), 0.4),
            "sixteen tokens",
            (lambda: [*self.set_ring("ABCDEF", 16, marks=False), *self.cap("node-A#0, node-A#1, ... node-A#15", WHITE)], 1.0),
        ])
        tab = VGroup(*[VGroup(left_at(M(f"{t:>3} each", 20, GREY_B), PX0 + 0.1, TAB_Y[k]), right_at(M(f"biggest {v}", 20, c), PCT_X1, TAB_Y[k]))
                       for k, (t, v, c) in enumerate([(1, "44.0%", RED_M), (4, "23.4%", WHITE), (16, "24.3%", WHITE),
                                                      (64, "18.6%", WHITE), (256, "17.4%", GREEN_M)])])
        tab_h = T("tokens per machine", 18, GREY_B).move_to([(PX0 + PX1) / 2, TAB_Y[0] + 0.32, 0])
        self.steps("Now a machine's share is the sum of many small arcs, and a sum of many random pieces lands much closer to its average "
                   "than one piece does. These extra tokens are called virtual nodes.", [
            "the sum of many",
            (lambda: [*self.set_shares("ABCDEF", 16, order=six_order), *self.uncap()], 0.9),
            "called virtual nodes",
            (lambda: self.cap("virtual nodes: many tokens for each machine", WHITE), 0.5),
        ])
        self.steps("With sixteen each, the biggest share drops from 44% to 24.3%. With 64, it's 18.6%, and with 256, 17.4%.", [
            (lambda: [FadeIn(tab_h), FadeIn(tab[0])], 0.5),
            "With sixteen",
            (lambda: [FadeIn(tab[2], shift=0.1 * UP)], 0.5),
            "With 64",
            (lambda: [*self.set_ring("ABCDEF", 64, marks=False), *self.set_shares("ABCDEF", 64, order=six_order), FadeIn(tab[3], shift=0.1 * UP)], 0.8),
            "with 256",
            (lambda: [FadeIn(tab[4], shift=0.1 * UP)], 0.5),
        ])

        # ---------------- scene 7: guardrail ----------------
        self.steps("But notice, it isn't smooth. Four tokens each gave 23.4%, a little better than sixteen. With only a few random tokens, "
                   "luck still matters. That's why Cassandra doesn't place its sixteen tokens at random. It uses a token allocator, "
                   "which this lesson comes back to.", [
            "Four tokens",
            (lambda: [FadeIn(tab[1], shift=0.1 * UP)], 0.5),
            (lambda: [Indicate(tab[1], color=YELLOW_M, scale_factor=1.08), Indicate(tab[2], color=YELLOW_M, scale_factor=1.08)], 0.8),
            "luck still matters",
            (lambda: self.cap("few random tokens: luck still matters", YELLOW_M), 0.5),
            "Cassandra doesn't",
            (lambda: self.cap("Cassandra: 16 tokens each, placed by a token allocator", WHITE), 0.5),
        ])
        self.steps("And tokens fix one more thing. A machine twice as big can take twice as many tokens.", [
            "twice as big",
            (lambda: self.cap("a machine twice as big: twice the tokens", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 8: moral and a check ----------------
        self.steps("So, the pizza. One random cut each gives slices nothing like equal. Many thin cuts each, and everyone gets about a fair slice. "
                   "And whenever a machine joins, only the keys just before its tokens move.", [
            (lambda: [*self.set_ring("ABCDEF", 1), *self.set_shares("ABCDEF", 1, order=six_order), *self.cap("one cut each: nothing like equal", RED_M)], 0.9),
            "Many thin cuts",
            (lambda: [*self.set_ring("ABCDEF", 64, marks=False), *self.set_shares("ABCDEF", 64, order=six_order),
                      *self.cap("many thin cuts each: about a fair slice", GREEN_M)], 0.9),
            "whenever a machine joins",
            (lambda: self.cap("a machine joins: only the keys just before its tokens move", YELLOW_M), 0.5),
        ], after=0.5)
        g_p = 0.75   # a made-up place inside B's arc, for the check
        gtok = VGroup(Dot(on_ring(g_p), radius=0.11, color=WHITE).set_stroke(RED_M, 3), T("G", 28, RED_M).move_to(on_ring(g_p, RR + 0.45)))
        self.steps("One quick check. Back to one token each. A seventh machine, G, joins, and its token lands inside B's arc. "
                   "Which machines give it keys? Pause and think.", [
            (lambda: [*self.uncap(), *self.set_ring("ABCDEF", 1), *self.set_shares("ABCDEF", 1, order=six_order)], 0.8),
            "its token lands",
            (lambda: [FadeIn(gtok, scale=0.5)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        g_arc = Arc(radius=RR, start_angle=ang(g_p), angle=2 * np.pi * (g_p - d_tok["A"]), arc_center=RC, stroke_width=20, color=RED_M)
        self.steps("Only B. The new machine takes the arc just before its token, and that arc belonged to B. Every other key stays put.", [
            (lambda: [*self.uncap(), Indicate(self.rows[1], color=TEAL_M, scale_factor=1.08)], 0.6),
            "the arc just before",
            (lambda: [Create(g_arc)], 0.9),
            "Every other key",
            (lambda: self.cap("only B gives keys to G; every other key stays put", GREEN_M), 0.5),
        ], after=0.3)
        self.play(*self.cap("many small arcs per machine; only the arcs before a new token move", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
