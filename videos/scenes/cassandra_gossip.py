from sfz import *

SAY.insert(0, (r"\bAck2\b", "ack two"))
SAY.insert(0, (r"\bSyn\b", "sin"))
SAY.insert(0, (r"\bPhi\b", "Fye"))
SAY.insert(0, (r"\bphi\b", "fye"))

RC = np.array([-4.1, -0.25, 0])   # centre of the six nodes
RR = 2.15                         # their circle
NR = 0.42                         # node radius
TA, TB = 0.65, 4.65               # table centres
COLS = [-1.3, 0.0, 1.35]          # node, generation, version
HY, RY0, RDY = 1.75, 1.2, 0.47    # header y, first row y, row step
U, BASE, BX = 0.33, -1.3, 4.25    # phi meter: units per phi, base y, bar x


def npos(i):
    a = np.radians(90 - 60 * (i - 1))
    return RC + RR * np.array([np.cos(a), np.sin(a), 0])


def node(i, col=BLUE_M, txt=WHITE, at=None):
    c = Circle(radius=NR, stroke_color=col, stroke_width=3)
    c.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(col), 0.14), opacity=1)
    return VGroup(c, T(str(i), 30, txt)).move_to(npos(i) if at is None else at)


def nlink(a, b, color=YELLOW_M, sw=3):
    pa, pb = npos(a), npos(b)
    d = (pb - pa) / np.linalg.norm(pb - pa)
    return Line(pa + d * (NR + 0.06), pb - d * (NR + 0.06), stroke_width=sw, color=color)


def cell(cx, row, col, txt, color=WHITE):
    return M(txt, 22, color).move_to([cx + COLS[col], RY0 - RDY * row, 0])


def table(cx, title, vers):
    ttl = T(title, 24, GREY_B).move_to([cx, 2.4, 0])
    hdr = VGroup(*[T(h, 20, GREY_B).move_to([cx + COLS[k], HY, 0]) for k, h in enumerate(("node", "generation", "version"))])
    rule = Line([cx - 1.75, 1.49, 0], [cx + 1.85, 1.49, 0], stroke_width=1.5, color=GREY_D)
    rows = VGroup(*[VGroup(cell(cx, r, 0, str(r + 1), GREY_A), cell(cx, r, 1, "9:00"), cell(cx, r, 2, str(v)))
                    for r, v in enumerate(vers)])
    return VGroup(ttl, hdr, rule, rows)


def solid_chip(text, color, size=22, mono=True):
    t = (M if mono else T)(text, size)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=max(0.5, t.height + 0.26), stroke_color=color, stroke_width=2.5)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.22), opacity=1)
    return VGroup(r, t)


def log_line(k, d, name, desc):
    y = -2.05 - 0.5 * k
    a = T(d, 22, GREY_B)
    a.move_to([-0.95 + a.width / 2, y, 0])
    b = M(name, 22, YELLOW_M)
    b.move_to([0.3 + b.width / 2, y, 0])
    c = T(desc, 22)
    c.move_to([1.3 + c.width / 2, y, 0])
    return VGroup(a, b, c)


def flash(m, color, s=1.08):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


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


class CassandraGossip(Base):
    """nosql-13: per-node state tables, Syn/Ack/Ack2, spread in about log2 N rounds, phi accrual, generations, seeds."""

    def construct(self):
        self.title_card("Gossip", "how a leaderless cluster learns who is alive")

        nodes = VGroup(*[node(i) for i in range(1, 7)])
        head = T("six nodes, no leader", 26, GREY_B).move_to([RC[0], 3.1, 0])
        self.steps("Six Cassandra nodes, none in charge. Each one must still know which others are alive.", [
            (lambda: [LaggedStart(*[FadeIn(n, scale=0.6) for n in nodes], lag_ratio=0.15), FadeIn(head)], 2.2),
        ])

        # ---- everyone pings everyone ---------------------------------------------------------------------
        mesh = VGroup(*[nlink(a, b, GREY_C, 1.5) for a in range(1, 7) for b in range(a + 1, 7)])
        six = T("6 nodes: 30 messages a second", 28).move_to([2.6, 0.6, 0])
        big = T("1,000 nodes: 999,000 a second", 28, RED_M).move_to([2.6, -0.3, 0])
        self.steps("Every node could ping every other node each second: 30 messages for six nodes, a million for a thousand.", [
            (lambda: [LaggedStart(*[Create(l) for l in mesh], lag_ratio=0.08)], 1.8),
            "30 messages", (lambda: [FadeIn(six, shift=0.2 * UP)], 0.6),
            "a million", (lambda: [FadeIn(big, shift=0.2 * UP)], 0.6),
        ])

        # ---- the table -----------------------------------------------------------------------------------
        A = table(TA, "what node 1 knows", [52, 47, 50, 44, 49, 38])
        gen_col = VGroup(A[1][1], *[r[1] for r in A[3]])
        ver_col = VGroup(A[1][2], *[r[2] for r in A[3]])
        hl = SurroundingRectangle(gen_col, color=YELLOW_M, buff=0.12, corner_radius=0.08)
        self.steps("Cassandra gossips instead. Each node keeps a row per node: a generation, when that node started, "
                   "and a version, a heartbeat it bumps every second.", [
            (lambda: [FadeOut(mesh), FadeOut(six), FadeOut(big)], 0.6),
            (lambda: [FadeIn(A, shift=0.2 * LEFT)], 1.0),
            "a generation", (lambda: [Create(hl)], 0.6),
            "and a version", (lambda: [Transform(hl, SurroundingRectangle(ver_col, color=YELLOW_M, buff=0.12, corner_radius=0.08))], 0.6),
            (lambda: [Transform(A[3][0][2], cell(TA, 0, 2, "53", YELLOW_M))], 0.4), 0.3,
            (lambda: [Transform(A[3][0][2], cell(TA, 0, 2, "52"))], 0.3),
        ])

        # ---- one exchange: Syn, Ack, Ack2 -----------------------------------------------------------------
        B = table(TB, "what node 4 knows", [45, 47, 48, 51, 49, 46])
        l14 = nlink(1, 4, YELLOW_M, 2.5)
        logs = VGroup(log_line(0, "1 → 4", "Syn", "generation and version for each node"),
                      log_line(1, "4 → 1", "Ack", "rows 4 and 6, and asks for 1 and 3"),
                      log_line(2, "1 → 4", "Ack2", "rows 1 and 3"))

        def send(name, a, b):
            ch = solid_chip(name, YELLOW_M)
            ln = nlink(a, b)
            ch.move_to(ln.get_start())
            return [(lambda: [FadeIn(ch, scale=0.6)], 0.2), (lambda: [MoveAlongPath(ch, ln, rate_func=smooth)], 1.1),
                    (lambda: [FadeOut(ch, scale=0.6)], 0.2)]

        self.steps("Each second, a node picks a random peer. Node 1 picks node 4 and sends a Syn: "
                   "its generation and version for each node.", [
            (lambda: [FadeOut(hl)], 0.3),
            "Node 1 picks", (lambda: [Create(l14), FadeIn(B, shift=0.2 * LEFT), flash(nodes[0], YELLOW_M, 1.15), flash(nodes[3], YELLOW_M, 1.15)], 1.0),
            "sends a Syn", *send("Syn", 1, 4),
            (lambda: [FadeIn(logs[0], shift=0.15 * UP)], 0.5),
            (lambda: [Indicate(gen_col, color=YELLOW_M, scale_factor=1.06), Indicate(ver_col, color=YELLOW_M, scale_factor=1.06)], 1.0),
        ])

        self.steps("Node 4 is ahead on nodes 4 and 6, so its Ack carries those rows, and asks for 1 and 3, where it's behind.", [
            (lambda: [B[3][3][2].animate.set_color(YELLOW_M), B[3][5][2].animate.set_color(YELLOW_M),
                      A[3][0][2].animate.set_color(GOLD_M), A[3][2][2].animate.set_color(GOLD_M)], 0.8),
            *send("Ack", 4, 1),
            (lambda: [Transform(A[3][3][2], cell(TA, 3, 2, "51", YELLOW_M)), Transform(A[3][5][2], cell(TA, 5, 2, "46", YELLOW_M)),
                      FadeIn(logs[1], shift=0.15 * UP)], 0.8),
        ])

        self.steps("Node 1 sends those in an Ack2. Three messages, and both now hold the newest of every row.", [
            *send("Ack2", 1, 4),
            (lambda: [Transform(B[3][0][2], cell(TB, 0, 2, "52", GOLD_M)), Transform(B[3][2][2], cell(TB, 2, 2, "50", GOLD_M)),
                      FadeIn(logs[2], shift=0.15 * UP)], 0.8),
            "Three messages",
            (lambda: [*[A[3][r][2].animate.set_color(WHITE) for r in range(6)], *[B[3][r][2].animate.set_color(WHITE) for r in range(6)]], 0.6),
            (lambda: [Indicate(VGroup(*[r[2] for r in A[3]]), color=YELLOW_M, scale_factor=1.08),
                      Indicate(VGroup(*[r[2] for r in B[3]]), color=YELLOW_M, scale_factor=1.08)], 1.0),
        ])

        # ---- one change spreads, round by round ---------------------------------------------------------------
        rnd = T("round 1: 2 of 6 have it", 26, YELLOW_M).move_to([TA, -2.35, 0])
        law = M("rounds ≈ log2(N)", 24, GREY_A).move_to([TA, -3.0, 0])

        def tell(pairs):
            ls = [nlink(a, b, YELLOW_M, 3) for a, b in pairs]
            dots = [Dot(l.get_start(), radius=0.09, color=YELLOW_M) for l in ls]
            return [(lambda: [*[Create(l) for l in ls]], 0.5),
                    (lambda: [*[MoveAlongPath(d, l, rate_func=smooth) for d, l in zip(dots, ls)]], 0.8),
                    (lambda: [*[FadeOut(d) for d in dots], *[Transform(nodes[b - 1], node(b, YELLOW_M)) for _, b in pairs]], 0.4),
                    ], ls

        r1, ls1 = tell([(1, 4)])
        self.steps("Follow one change: node 1 bumps its version to 53. Each round, every node that has it tells a random peer.", [
            (lambda: [FadeOut(B), FadeOut(logs), FadeOut(l14)], 0.6),
            (lambda: [Transform(A[3][0][2], cell(TA, 0, 2, "53", YELLOW_M)), Transform(nodes[0], node(1, YELLOW_M))], 0.8),
            "Each round", *r1, (lambda: [FadeIn(rnd, shift=0.15 * UP)], 0.5),
        ])

        r2, ls2 = tell([(1, 3), (4, 6)])
        r3, ls3 = tell([(3, 2), (6, 5)])
        self.steps("It spreads to two, then four, then all six. The count doubles, so it takes about log two of N rounds, "
                   "ten for 1,000 nodes.", [
            (lambda: [*[FadeOut(l) for l in ls1]], 0.3), *r2,
            (lambda: [Transform(rnd, T("round 2: 4 of 6 have it", 26, YELLOW_M).move_to(rnd))], 0.4),
            "then all six", (lambda: [*[FadeOut(l) for l in ls2]], 0.3), *r3,
            (lambda: [Transform(rnd, T("round 3: 6 of 6 have it", 26, YELLOW_M).move_to(rnd))], 0.4),
            "The count doubles", (lambda: [FadeIn(law, shift=0.15 * UP)], 0.6),
        ])

        # ---- node 5 stops ------------------------------------------------------------------------------------
        cross = tick(False, 0.24).move_to(npos(5) + np.array([0, -0.72, 0]))
        vers = [53, 47, 50, 51, 49, 46]

        def count():
            for r in range(6):
                if r != 4:
                    vers[r] += 1
            return [Transform(A[3][r][2], cell(TA, r, 2, str(vers[r]), RED_M if r == 4 else WHITE)) for r in range(6)]

        self.steps("Now node 5 stops. Its version freezes, while the other rows keep counting.", [
            (lambda: [*[FadeOut(l) for l in ls3], FadeOut(rnd), FadeOut(law), *[Transform(nodes[k], node(k + 1)) for k in range(6)],
                      Transform(A[3][0][2], cell(TA, 0, 2, "53"))], 0.6),
            (lambda: [Transform(nodes[4], node(5, GREY_C, GREY_C)), FadeIn(cross, scale=0.5)], 0.6),
            "Its version", (count, 0.45), 0.15, (count, 0.45), 0.15, (count, 0.45), 0.15, (count, 0.45),
        ])

        # ---- the phi accrual detector ---------------------------------------------------------------------------
        pt = ValueTracker(0.0)
        m_title = T("node 1's phi for node 5", 24, GREY_B).move_to([TB, 2.4, 0])
        axis = Line([BX - 0.5, BASE, 0], [BX - 0.5, BASE + 10 * U, 0], stroke_width=2, color=GREY_D)
        floor = Line([BX - 0.5, BASE, 0], [BX + 0.55, BASE, 0], stroke_width=2, color=GREY_D)
        thr = DashedLine([BX - 0.5, BASE + 8 * U, 0], [6.35, BASE + 8 * U, 0], dash_length=0.1, stroke_width=2.5, color=RED_M)
        t1 = M("1", 20, GREY_B).move_to([BX - 0.75, BASE + 1 * U, 0])
        t8 = M("8", 20, RED_M).move_to([BX - 0.75, BASE + 8 * U, 0])
        thr_l = T("threshold", 22, RED_M)
        thr_l.move_to([BX + 0.42 + thr_l.width / 2, BASE + 8 * U + 0.27, 0])
        odds8 = T("1 in 100 million", 20, GREY_A)
        odds8.move_to([BX + 0.42 + odds8.width / 2, BASE + 8 * U - 0.3, 0])
        odds1 = T("1 in 10", 20, GREY_A)
        odds1.move_to([BX + 0.42 + odds1.width / 2, BASE + 1 * U, 0])
        bar = always_redraw(lambda: Rectangle(width=0.5, height=max(0.002, pt.get_value() * U), stroke_width=0)
                            .set_fill(RED_M if pt.get_value() > 8 else GOLD_M, 0.9)
                            .move_to([BX, BASE + max(0.002, pt.get_value() * U) / 2, 0]))
        val = always_redraw(lambda: M(f"phi = {pt.get_value():.1f}", 24, RED_M if pt.get_value() > 8 else GOLD_M)
                            .move_to([BX, BASE - 0.45, 0]))
        meter = VGroup(m_title, axis, floor, thr, t1, t8, thr_l)

        self.steps("A fixed timeout fires too early on a slow network. So each node runs a phi accrual detector, "
                   "which learns how often heartbeats arrive and scores the silence as phi.", [
            "So each node", (lambda: [FadeIn(meter), FadeIn(bar), FadeIn(val)], 1.0),
            "scores the silence", (lambda: [pt.animate.set_value(0.6)], 1.2),
        ])

        down = T("down", 22, RED_M).move_to([2.75, RY0 - RDY * 4, 0])
        self.steps("A phi of 1 means a live node goes this quiet one time in ten. Phi 8, the default threshold, "
                   "means one in 100 million. Past it, node 1 marks node 5 down.", [
            (lambda: [pt.animate.set_value(1.0)], 0.8), (lambda: [FadeIn(odds1, shift=0.15 * LEFT)], 0.5),
            "Phi 8", (lambda: [pt.animate(rate_func=linear).set_value(8.0)], 2.6),
            (lambda: [FadeIn(odds8, shift=0.15 * LEFT)], 0.5),
            "Past it", (lambda: [pt.animate.set_value(8.7)], 0.7),
            (lambda: [FadeIn(down, shift=0.15 * LEFT), A[3][4][0].animate.set_color(RED_M), A[3][4][1].animate.set_color(RED_M)], 0.6),
        ])

        # ---- node 5 comes back --------------------------------------------------------------------------------
        up = T("up", 22, GREEN_M).move_to(down)
        self.steps("Node 5 restarts with a later generation, 9:20. Its version starts low, but the later generation wins, "
                   "so the others mark it up.", [
            (lambda: [Transform(nodes[4], node(5)), FadeOut(cross)], 0.6),
            "9:20", (lambda: [Transform(A[3][4][1], cell(TA, 4, 1, "9:20", GREEN_M)), Transform(A[3][4][2], cell(TA, 4, 2, "1", GREEN_M))], 0.8),
            "Its version", (lambda: [Indicate(A[3][4][2], color=GREEN_M, scale_factor=1.4)], 0.8),
            "so the others", (lambda: [pt.animate.set_value(0.0), Transform(down, up), A[3][4][0].animate.set_color(GREY_A)], 1.0),
            (lambda: [Transform(A[3][4][2], cell(TA, 4, 2, "2", GREEN_M))], 0.4),
        ])

        # ---- seeds ---------------------------------------------------------------------------------------------
        yaml = VGroup(T("a new node's cassandra.yaml", 22, GREY_B), M('seeds: "node1,node2"', 22))
        yaml.arrange(DOWN, buff=0.25).move_to([TA + 0.6, -2.4, 0])
        frame = SurroundingRectangle(yaml, color=GREY_D, buff=0.3, corner_radius=0.12)
        s1 = solid_chip("seed", GREEN_M, 20, mono=False).move_to(RC + 0.57 * (npos(1) - RC))
        s2 = solid_chip("seed", GREEN_M, 20, mono=False).move_to(RC + 0.6 * (npos(2) - RC))
        newn = node("new", GREY_B, GREY_B, at=np.array([-6.1, 2.7, 0]))
        newn[1].scale(0.75)
        call = edge_arrow(newn, nodes[0], GREEN_M)
        self.steps("A new node finds the cluster through seeds, a few addresses in its config. "
                   "A seed is only the first node it calls, never a master.", [
            (lambda: [FadeOut(meter), FadeOut(bar), FadeOut(val), FadeOut(down), FadeOut(odds1), FadeOut(odds8), FadeOut(head),
                      *[A[3][4][k].animate.set_color(WHITE if k else GREY_A) for k in (0, 1, 2)]], 0.6),
            (lambda: [FadeIn(frame), FadeIn(yaml)], 0.8),
            (lambda: [FadeIn(s1, scale=0.6), FadeIn(s2, scale=0.6)], 0.6),
            "A seed", (lambda: [FadeIn(newn, scale=0.6)], 0.5), (lambda: [GrowArrow(call)], 0.6),
        ])

        self.steps("One random peer a second, three short messages, and news reaches every node in a few rounds.", [
            (lambda: [LaggedStart(*[flash(n, YELLOW_M, 1.15) for n in nodes], lag_ratio=0.2)], 2.2),
        ])
        self.wait(0.6)
