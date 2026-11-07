from sfz import *

SAY.insert(0, (r"\bA-1001\b", "A ten oh one"))
SAY.insert(0, (r"\bM-0042\b", "M zero zero four two"))

NC = [BLUE_M, GREEN_M, GOLD_M, PURPLE_M, TEAL_M]   # node 0..4
C = np.array([-2.5, -0.1, 0])                       # ring centre
R = 2.5                                             # ring radius
KR = R - 0.42                                       # keys sit just inside the ring
SPAN = 20                                           # hash values 0..19 go once round

# Virtual nodes: four points per node, (position, node).
TOKENS = [(0.6, 2), (1.5, 0), (2.4, 3), (3.5, 1), (4.3, 4), (5.4, 0), (6.2, 2), (7.3, 4), (8.4, 1), (9.2, 3),
          (10.3, 0), (11.4, 4), (12.2, 2), (13.1, 1), (14.2, 3), (15.0, 4), (16.1, 0), (17.5, 3), (18.2, 1), (19.3, 2)]
HOT = 4.6
SPLIT = [1.1, 3.0, 4.9, 6.8, 8.9, 11.8, 13.7, 15.6, 17.8, 19.6]


def ang(h):
    return np.radians(90 - 360 * h / SPAN)


def at(h, r):
    a = ang(h)
    return C + r * np.array([np.cos(a), np.sin(a), 0])


def owner(h, points):
    """First point clockwise from h (points: list of (pos, node))."""
    return min(points, key=lambda p: (p[0] - h) % SPAN)


def arcs(points, sw=7, op=0.85):
    pts = sorted(points)
    g = VGroup()
    for i, (p, n) in enumerate(pts):
        prev = pts[i - 1][0]
        length = (p - prev) % SPAN or SPAN
        g.add(Arc(radius=R, start_angle=ang(prev), angle=-np.radians(360 * length / SPAN), arc_center=C,
                  stroke_width=sw, stroke_color=NC[n], stroke_opacity=op))
    return g


def shares(points):
    pts = sorted(points)
    s = [0.0] * 5
    for i, (p, n) in enumerate(pts):
        s[n] += (p - pts[i - 1][0]) % SPAN
    return [round(100 * x / SPAN) for x in s]


def place_out(m, h, r):
    """Put m just outside radius r at hash h, its nearest edge on that radius."""
    a = ang(h)
    d = np.array([np.cos(a), np.sin(a), 0])
    m.move_to(C + r * d + d * (abs(d[0]) * m.width / 2 + abs(d[1]) * m.height / 2))
    return m


class ConsistentHashing(VoiceScene):
    """nosql-05: hash mod N moves most keys; the ring moves few; virtual nodes even the load; hot keys."""

    def construct(self):
        self.title_card("Consistent hashing", "why adding a node moves few keys")

        # ---- hash mod N -------------------------------------------------------------------------------
        def nbox(k):
            return box(f"node {k}", NC[k], w=1.9, h=0.72, size=26)

        nodes = VGroup(*[nbox(k) for k in range(4)])
        for k, b in enumerate(nodes):
            b.move_to([-3.3 + 2.2 * k, 2.45, 0])
        self.beat("Your accounts don't fit on one machine, so you spread them over four nodes. "
                  "Every client must work out on its own where a key lives.",
                  LaggedStart(*[FadeIn(b, shift=0.2 * DOWN) for b in nodes], lag_ratio=0.2), run_time=2.0)

        def example(n):
            parts = VGroup(chip("A-1001", WHITE, 24, mono=True), M("hash 13", 26), M(f"13 mod {n} = {13 % n}", 26),
                           T(f"node {13 % n}", 30, NC[13 % n]))
            parts.arrange(RIGHT, buff=0.95).move_to([0, -2.45, 0])
            arrs = VGroup(*[arrow(parts[i].get_right(), parts[i + 1].get_left(), GREY_B, buff=0.15) for i in range(3)])
            return VGroup(parts, arrs)

        ex = example(4)
        self.beat("The simplest rule: hash the key to a number, and divide by the number of nodes. "
                  "The remainder is the node. A-1001 hashes to 13, and 13 mod 4 is 1: node 1.",
                  Succession(FadeIn(ex[0][0]), GrowArrow(ex[1][0]), FadeIn(ex[0][1]), GrowArrow(ex[1][1]),
                             FadeIn(ex[0][2]), GrowArrow(ex[1][2]), FadeIn(ex[0][3]), Indicate(nodes[1], color=NC[1])),
                  run_time=5.5)

        CW, CG, CY = 0.56, 0.065, 0.75

        def cell(i, n, extra=None):
            col = NC[i % n]
            r = RoundedRectangle(corner_radius=0.06, width=CW, height=CW, stroke_color=col, stroke_width=2.5)
            r.set_fill(col, opacity=0.25)
            g = VGroup(r, M(str(i), 20))
            g.move_to([-(20 * CW + 19 * CG) / 2 + CW / 2 + i * (CW + CG), CY, 0])
            return g

        strip = VGroup(*[cell(i, 4) for i in range(20)])
        rule = M("node = hash mod 4", 28).move_to([-3.2, -0.75, 0])
        self.beat("Here are twenty keys, hashes zero to nineteen, tinted to match their node.",
                  LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in strip], lag_ratio=0.06), FadeIn(rule), run_time=2.4)

        new = nbox(4)
        xs5 = [-4.4 + 2.2 * k for k in range(5)]
        new.move_to([xs5[4], 2.45, 0])
        strip5 = VGroup(*[cell(i, 5) for i in range(20)])
        rule5 = M("node = hash mod 5", 28).move_to(rule)
        self.beat("Now add a fifth node. The rule becomes hash mod 5.",
                  *[nodes[k].animate.move_to([xs5[k], 2.45, 0]) for k in range(4)], FadeIn(new, shift=0.2 * LEFT),
                  Transform(rule, rule5), run_time=1.6)
        nodes.add(new)

        moved = [i for i in range(20) if i % 4 != i % 5]
        marks = VGroup(*[Line(LEFT * 0.22, RIGHT * 0.22, stroke_width=5, color=RED_M).next_to(strip[i], DOWN, buff=0.12)
                         for i in moved])
        tally = chip("16 of 20 keys move", RED_M, 28).move_to([3.3, -0.75, 0])
        ex5 = example(5)
        self.beat("Only keys zero to three stay put. Sixteen of twenty move, 80% of your data at once.",
                  LaggedStart(*[Transform(strip[i], strip5[i]) for i in range(20)], lag_ratio=0.04),
                  LaggedStart(*[Create(m) for m in marks], lag_ratio=0.04), FadeIn(tally),
                  Transform(ex, ex5), run_time=3.2)

        # ---- the ring --------------------------------------------------------------------------------
        ring = Circle(radius=R, stroke_color=GREY_D, stroke_width=2).move_to(C)
        keys = VGroup(*[Dot(at(h, KR), radius=0.075, color=WHITE) for h in range(20)])
        mod_h = T("hash mod 5", 26, GREY_B)
        self.play(FadeOut(nodes), FadeOut(rule), FadeOut(ex), FadeOut(marks), run_time=0.6)
        cmp_mod = VGroup(mod_h, tally.copy()).arrange(DOWN, buff=0.22)
        cmp_mod.move_to([4.15, 1.3, 0])
        self.beat("Consistent hashing avoids this. Bend the hash values into a circle, called the ring.",
                  Create(ring), *[ReplacementTransform(strip[i], keys[i]) for i in range(20)],
                  Transform(tally, cmp_mod[1]), FadeIn(mod_h), run_time=2.6)

        POS = {0: 2.5, 1: 9.5, 2: 12.5, 3: 16.5}

        def marker(h, n):
            return Dot(at(h, R), radius=0.15, color=NC[n]).set_stroke(BLACK, 3)

        def label(h, n):
            return place_out(T(f"node {n}", 24, NC[n]), h, R + 0.28)

        pts4 = [(POS[n], n) for n in range(4)]
        arc4 = arcs(pts4)
        marks4 = VGroup(*[marker(POS[n], n) for n in range(4)])
        labs4 = VGroup(*[label(POS[n], n) for n in range(4)])
        key_cols = [owner(h, pts4)[1] for h in range(20)]
        walk = Arc(radius=R - 0.2, start_angle=ang(13), angle=-np.radians(360 * 3.5 / SPAN), arc_center=C,
                   stroke_color=YELLOW_M, stroke_width=4).add_tip(tip_length=0.18, tip_width=0.18)
        a1001 = M("A-1001", 22, YELLOW_M).move_to(at(13, KR - 0.75))
        self.beat("Each node sits on the ring at the hash of its name. That point is its token. A key belongs to the first node clockwise from it. "
                  "A-1001 belongs to node 3.",
                  Succession(AnimationGroup(FadeIn(marks4, scale=0.5), FadeIn(labs4), Create(arc4), run_time=2.0),
                             AnimationGroup(*[keys[h].animate.set_color(NC[key_cols[h]]) for h in range(20)], run_time=1.2),
                             AnimationGroup(FadeIn(a1001), Indicate(keys[13], color=YELLOW_M, scale_factor=2.0), run_time=0.8),
                             Create(walk, run_time=1.4)),
                  run_time=6.0)

        pts5 = pts4 + [(6.5, 4)]
        arc5 = arcs(pts5)
        m4, l4 = marker(6.5, 4), label(6.5, 4)
        took = [3, 4, 5, 6]
        ring_h = T("ring", 26, GREY_B)
        ring_c = chip("4 of 20 keys move", GREEN_M, 28)
        cmp_ring = VGroup(ring_h, ring_c).arrange(DOWN, buff=0.22).move_to([4.15, -1.0, 0])
        self.play(FadeOut(walk), FadeOut(a1001), run_time=0.5)
        self.beat("A fifth node, node 4, now lands between node 0 and node 1. It takes only the keys on its arc, all from node 1. "
                  "Four keys move instead of sixteen.",
                  Succession(AnimationGroup(FadeIn(m4, scale=0.5), FadeIn(l4), run_time=1.0),
                             AnimationGroup(Transform(arc4, arc5), *[keys[h].animate.set_color(NC[4]) for h in took], run_time=1.2),
                             AnimationGroup(*[Indicate(keys[h], color=NC[4], scale_factor=2.2) for h in took], FadeIn(cmp_ring), run_time=1.4)),
                  run_time=5.0)
        marks4.add(m4)
        labs4.add(l4)

        # ---- uneven shares, then virtual nodes ---------------------------------------------------------
        def bars(sh, header):
            rows = VGroup()
            for n in range(5):
                lab = T(f"node {n}", 24, NC[n])
                bar = Rectangle(width=max(0.05, sh[n] * 0.08), height=0.34, stroke_width=0).set_fill(NC[n], 0.85)
                pct = T(f"{sh[n]}%", 24, WHITE)
                lab.move_to([2.15, 1.25 - 0.72 * n, 0])
                bar.move_to([2.95 + bar.width / 2, lab.get_y(), 0])
                pct.next_to(bar, RIGHT, buff=0.15)
                rows.add(VGroup(lab, bar, pct))
            hd = T(header, 26, GREY_B).move_to([3.9, 2.15, 0])
            return VGroup(hd, rows)

        sh5 = shares(pts5)
        panel = bars(sh5, "share of the ring")
        self.beat("But a few random points cut the ring unevenly. Node 0 holds 30% of the keys, node 1 only fifteen.",
                  Succession(AnimationGroup(FadeOut(mod_h), FadeOut(tally), FadeOut(cmp_ring), run_time=0.6),
                             AnimationGroup(FadeIn(panel[0]), LaggedStart(*[FadeIn(r, shift=0.2 * RIGHT) for r in panel[1]], lag_ratio=0.15), run_time=1.6),
                             AnimationGroup(Indicate(panel[1][0], color=NC[0], scale_factor=1.1),
                                            Indicate(panel[1][1], color=NC[1], scale_factor=1.1), run_time=1.4)),
                  run_time=4.4)

        toks = VGroup(*[Dot(at(p, R), radius=0.11, color=NC[n]).set_stroke(BLACK, 2.5) for p, n in TOKENS])
        arc_v = arcs(TOKENS)
        shv = shares(TOKENS)
        panel_v = bars(shv, "share of the ring")
        vcols = [owner(h, TOKENS)[1] for h in range(20)]
        self.beat("So each node takes many tokens, called virtual nodes. Here it's four each, and Cassandra uses sixteen. "
                  "The short arcs average out, and every node holds close to a fifth.",
                  Succession(AnimationGroup(FadeOut(labs4), ReplacementTransform(marks4, toks), Transform(arc4, arc_v), run_time=2.4),
                             AnimationGroup(*[keys[h].animate.set_color(NC[vcols[h]]) for h in range(20)], run_time=1.0),
                             AnimationGroup(*[panel[1][n][2].animate.set_opacity(0) for n in range(5)], run_time=0.4),
                             AnimationGroup(*[Transform(panel[1][n][1], panel_v[1][n][1]) for n in range(5)], run_time=1.0),
                             AnimationGroup(*[FadeIn(panel_v[1][n][2]) for n in range(5)], run_time=0.5)),
                  run_time=6.6)

        # ---- the hot key -----------------------------------------------------------------------------
        hot_dot = Dot(at(HOT, KR), radius=0.13, color=RED_M)
        hot_chip = chip("M-0042", RED_M, 26, mono=True)
        hot_txt = T("4,000 payments a second", 26, RED_M)
        hot_card = VGroup(hot_chip, hot_txt).arrange(DOWN, buff=0.25).move_to([4.1, 1.2, 0])
        feed = Arrow(hot_card.get_left() + 0.1 * LEFT, at(HOT, R + 0.18), buff=0.08, stroke_width=4, color=RED_M,
                     max_tip_length_to_length_ratio=0.08)
        self.beat("One problem no ring can fix: a hot key. On Black Friday, merchant M-0042 takes 4,000 payments a second, all on one key.",
                  Succession(AnimationGroup(FadeOut(panel), *[FadeOut(panel_v[1][n][2]) for n in range(5)], keys.animate.set_opacity(0.3), run_time=0.8),
                             AnimationGroup(FadeIn(hot_card, shift=0.2 * LEFT), FadeIn(hot_dot, scale=0.4), run_time=1.0),
                             GrowArrow(feed, run_time=1.0)),
                  run_time=3.6)

        own_i = TOKENS.index(owner(HOT, TOKENS))
        burst = [travel(feed, RED_M, run_time=0.7) for _ in range(5)]
        self.beat("A key hashes to a single point, so all of that traffic lands on one node.",
                  Succession(LaggedStart(*burst, lag_ratio=0.35),
                             AnimationGroup(toks[own_i].animate.scale(1.9).set_color(RED_M), run_time=0.8)),
                  run_time=3.2)

        split_dots = VGroup(*[Dot(at(h, KR), radius=0.1, color=RED_M) for h in SPLIT])
        split_own = sorted({TOKENS.index(owner(h, TOKENS)) for h in SPLIT})
        split_chip = chip("MERCH#M-0042#0 … #9", RED_M, 24, mono=True).move_to(hot_chip)
        split_txt = T("ten keys, ten points", 26, RED_M).move_to(hot_txt)
        self.beat("To spread it, change the key. Add a suffix from zero to nine, and the writes land on ten points. Reads ask all ten.",
                  Succession(AnimationGroup(FadeOut(feed), toks[own_i].animate.scale(1 / 1.9).set_color(NC[TOKENS[own_i][1]]),
                                            Transform(hot_chip, split_chip), Transform(hot_txt, split_txt), run_time=1.2),
                             AnimationGroup(ReplacementTransform(VGroup(*[hot_dot.copy() for _ in SPLIT]), split_dots), FadeOut(hot_dot), run_time=1.6),
                             LaggedStart(*[Indicate(toks[i], color=WHITE, scale_factor=1.8) for i in split_own], lag_ratio=0.15, run_time=1.6)),
                  run_time=5.0)

        self.beat("The ring moves few keys when nodes change, and virtual nodes keep the shares even. A hot key is yours to split.",
                  Succession(AnimationGroup(keys.animate.set_opacity(1), FadeOut(split_dots), FadeOut(hot_chip), FadeOut(hot_txt), run_time=1.0),
                             AnimationGroup(FadeIn(panel_final := bars(shv, "share of the ring")), run_time=1.0),
                             Indicate(VGroup(ring, arc4), color=WHITE, scale_factor=1.03, run_time=1.4)),
                  run_time=3.8)
        self.wait(0.6)
