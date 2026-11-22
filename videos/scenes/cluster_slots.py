from sfz import *

SAY.insert(0, (r"\bpayment:(\d+)", r"payment \1"))
SAY.insert(0, (r"\bMOVED\b", "moved"))
SAY.insert(0, (r"\bGET\b", "get"))
SAY.insert(0, (r"\b127\.0\.0\.1\b", "one two seven, dot zero, dot zero, dot one"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BAR_Y, BAR_H, BX0, BX1 = 2.85, 0.5, -3.9, 6.0      # the hooks: 16,384 hash slots
NX, NW, NH = 4.75, 3.1, 1.25                       # the attendants: three nodes in a column on the right
NY = {1: 1.15, 2: -0.55, 3: -2.25}
NC = {1: BLUE_M, 2: TEAL_M, 3: PURPLE_M}
CX, CY, CW, CH = -5.35, -0.55, 2.0, 1.0            # the client
TB_C = np.array([-5.0, -2.15, 0])                 # the client's own slot table
RANGES = {1: (0, 5460), 2: (5461, 10922), 3: (10923, 16383)}
CAP_Y, BAR2_Y = -3.36, -2.95


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def sx(slot):
    return BX0 + (slot + 0.5) / 16384 * (BX1 - BX0)


def c_out():
    return np.array([CX + CW / 2 + 0.08, CY, 0])


def n_in(k):
    return np.array([NX - NW / 2 - 0.08, NY[k], 0])


def to_node(k, color=GREY_B):
    return Arrow(c_out(), n_in(k), buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.03)


def flow(a, b, color=YELLOW_M, rt=0.7, frac=1.0):
    """A dot that runs from a towards b (part of the way if frac < 1); invisible until its turn."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0).set_z_index(8)
    return Succession(d.animate(run_time=0.04).set_opacity(1),
                      MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))


def go(k, color=YELLOW_M, rt=0.7, frac=1.0):
    return flow(c_out(), n_in(k), color, rt, frac)


def back(k, color=RED_M, rt=0.7):
    return flow(n_in(k), c_out(), color, rt)


def along(k, mob, side=1, off=0.3, t=0.5):
    """Put a label along the arrow from the client to node k, rotated with it, on one side."""
    a, b = c_out(), n_in(k)
    d = b - a
    ang = np.arctan2(d[1], d[0])
    n = np.array([-np.sin(ang), np.cos(ang), 0])
    mob.rotate(ang)
    return mob.move_to(a + t * d + side * off * n)


def node_name(k, s):
    return T(s, 22).move_to([NX, NY[k] + 0.36, 0])


def node_addr(k, s=None, color=GREY_B):
    return M(s or f"127.0.0.1:700{k}", 16, color).move_to([NX, NY[k], 0])


def node_range(k, s=None, color=None):
    a, b = RANGES[k]
    return fit(M(s or f"{a} to {b}", 16, color or NC[k]).move_to([NX, NY[k] - 0.36, 0]), NW - 0.3)


def node_box(k):
    r = RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=NC[k], stroke_width=3)
    return r.set_fill(fillc(NC[k]), 1).move_to([NX, NY[k], 0])


def marker(slot, color=WHITE, label=None):
    x = sx(slot)
    tk = Rectangle(width=0.1, height=BAR_H + 0.16, stroke_width=0).set_fill(color, 1).move_to([x, BAR_Y, 0])
    g = VGroup(tk)
    if label:
        g.add(T(label, 18, color).move_to([x, BAR_Y - BAR_H / 2 - 0.32, 0]))
    return g


def table_rows(extra=None):
    rows = [M(f"{a} to {b} → :700{k}", 14, NC[k]) for k, (a, b) in RANGES.items()]
    if extra:
        rows.append(M(extra, 14, PURPLE_M))
    return rows


def ctable(extra=None):
    title = T("its slot table", 16, GREY_B)
    rows = table_rows(extra)
    g = VGroup(title, *rows).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
    r = RoundedRectangle(corner_radius=0.1, width=g.width + 0.3, height=g.height + 0.24, stroke_color=GREY_B, stroke_width=2)
    r.set_fill(BLACK, 1)
    top = TB_C[1] + 0.7
    r.move_to([TB_C[0], top - r.height / 2, 0])
    g.move_to(r)
    g.align_to(r.get_left() + 0.15 * RIGHT, LEFT)
    return VGroup(r, g)


JAVA = ["var seed = new HostAndPort(\"127.0.0.1\", 7001);",
        "try (RedisClusterClient cluster =",
        "        RedisClusterClient.builder()",
        "            .nodes(Set.of(seed)).build()) {",
        "    cluster.set(\"payment:42\", \"approved\");",
        "}"]
KOTLIN = ["val client = RedisClusterClient",
          "    .create(\"redis://127.0.0.1:7001\")",
          "client.connect().use { conn ->",
          "    val redis = conn.coroutines()",
          "    runBlocking {",
          "        redis.set(\"payment:42\", \"approved\")",
          "    }",
          "}"]


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.6, height=4.3, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.55, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 2.35)
    rows = VGroup()
    cw = M("x" * 40, 15).width / 40
    for k, s in enumerate(lines):
        body, _, com = s.partition("  //")
        ind = (len(body) - len(body.lstrip())) * cw
        row = VGroup(M(body.strip() or " ", 15, WHITE))
        if com:
            row.add(M("// " + com.strip(), 15, GREY_B))
            row.arrange(RIGHT, buff=0.2)
        rows.add(left_at(row, x - 3.0 + ind, 1.8 - 0.42 * k))
    fit(rows, 6.2)
    return VGroup(r, head, rows).set_z_index(10)


class ClusterSlots(Base):
    """cache-10, section 1. 40 GB and 300,000 commands a second outgrow one Redis; the keys go to three nodes. The
    cloakroom: 16,384 hooks (hash slots), three attendants (nodes), a board (the slot table); payment:42 is slot 9055 on
    node 2. A plain client that knows node 1 gets MOVED 9055 127.0.0.1:7002: a node never fetches for you. About two keys
    in three cost an extra trip. A cluster-aware client keeps its own table and goes straight to the owner. Slot 9055
    moves to node 3: one MOVED, the table reloads. The announced address must work from the client (Docker); a batch
    splits per node, a transaction can't. Java and Kotlin, the moral, and a check (GET payment:43: MOVED 13182)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_req(self, s, color=GOLD_M):
        new = M(s, 18, color).move_to([CX, CY + CH / 2 + 0.4, 0])
        old, self.req = self.req, new
        return [swap(old, new)]

    def set_client(self, s, sub=None):
        g = VGroup(T(s, 22))
        if sub:
            g.add(T(sub, 16, GREY_B))
        g.arrange(DOWN, buff=0.08).move_to([CX, CY, 0])
        fit(g, CW - 0.2)
        old, self.clab = self.clab, g
        return [swap(old, g)]

    def set_name(self, k, s):
        new = node_name(k, s)
        old, self.names[k] = self.names[k], new
        return [swap(old, new)]

    def set_addr(self, k, s=None, color=GREY_B):
        new = node_addr(k, s, color)
        old, self.addrs[k] = self.addrs[k], new
        return [swap(old, new)]

    def set_range(self, k, s=None, color=None):
        new = node_range(k, s, color)
        old, self.ranges[k] = self.ranges[k], new
        return [swap(old, new)]

    def set_mark(self, slot, color, label):
        new = marker(slot, color, label)
        old, self.mk = self.mk, new
        return [swap(old, new, DOWN)]

    def set_reply(self, k, s, color=RED_M, side=-1):
        new = along(k, M(s, 18, color), side=side)
        old, self.reply = self.reply, new
        return [swap(old, new)]

    def clear_reply(self):
        old, self.reply = self.reply, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.4, BAR2_Y, 0], [0.6, BAR2_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.req = self.clab = self.mk = self.reply = None
        self.names = {}
        self.addrs = {1: None, 2: None, 3: None}
        self.ranges = {1: None, 2: None, 3: None}
        self.title_card("Ask the wrong server", "and it tells you where to go")

        # ---------------- scene 1: the question ----------------
        cbox = RoundedRectangle(corner_radius=0.14, width=CW, height=CH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
        cbox.move_to([CX, CY, 0])
        self.clab = T("your program", 22).move_to([CX, CY, 0])
        one = RoundedRectangle(corner_radius=0.14, width=NW, height=NH * 2.4, stroke_color=RED_M, stroke_width=3)
        one.set_fill(fillc(RED_M), 1).move_to([NX, NY[2], 0])
        one_t = VGroup(T("Redis", 26), T("40 GB", 20, RED_M), T("300,000 commands", 20, RED_M), T("a second", 20, RED_M),
                       T("one at a time", 20, RED_M)).arrange(DOWN, buff=0.14).move_to(one)
        self.steps("The payments program keeps its notes and counters in Redis, a program that holds data in memory and answers "
                   "very fast. It has grown to 40 GB and 300,000 commands a second, and one Redis runs every command one at a time.", [
            (lambda: [FadeIn(cbox), FadeIn(self.clab)], 0.6),
            "in Redis",
            (lambda: [FadeIn(one), FadeIn(one_t[0])], 0.7),
            "It has grown",
            (lambda: [FadeIn(one_t[1], shift=0.1 * UP)], 0.4),
            "300,000",
            (lambda: [FadeIn(one_t[2:4], shift=0.1 * UP)], 0.4),
            "one at a time",
            (lambda: [FadeIn(one_t[4], shift=0.1 * UP), glow(one, RED_M, 1.03)], 0.8),
        ])
        boxes = {k: node_box(k) for k in (1, 2, 3)}
        for k in (1, 2, 3):
            self.names[k] = node_name(k, f"server {k}")
        qm = T("?", 34, GOLD_M)
        self.steps("So the keys get split over three servers, and each one owns a part. Now your program wants payment:42. "
                   "Which server do you ask? And what happens if you ask the wrong one?", [
            "So the keys",
            (lambda: [FadeOut(one), FadeOut(one_t),
                      LaggedStart(*[AnimationGroup(FadeIn(boxes[k]), FadeIn(self.names[k])) for k in (1, 2, 3)], lag_ratio=0.3)], 1.2),
            "Now your program",
            (lambda: self.set_req("GET payment:42"), 0.6),
            "Which server",
            (lambda: [FadeIn(qm.next_to(self.req, RIGHT, buff=0.15))], 0.4),
            (lambda: [LaggedStart(*[glow(boxes[k], NC[k], 1.03) for k in (1, 2, 3)], lag_ratio=0.3)], 1.2),
        ])

        # ---------------- scene 2: the cloakroom ----------------
        bar = Rectangle(width=BX1 - BX0, height=BAR_H, stroke_color=GREY_B, stroke_width=2).move_to([(BX0 + BX1) / 2, BAR_Y, 0])
        ticks = VGroup(*[Line([BX0 + i * (BX1 - BX0) / 64, BAR_Y - BAR_H / 2, 0], [BX0 + i * (BX1 - BX0) / 64, BAR_Y - BAR_H / 2 + 0.12, 0],
                              stroke_width=1, color=GREY_C) for i in range(1, 64)])
        btitle = VGroup(T("16,384", 24), T("hooks", 19, GREY_B)).arrange(DOWN, buff=0.08).move_to([-5.35, BAR_Y, 0])
        segs, slabs = {}, {}
        for k, (a, b) in RANGES.items():
            x0, x1 = sx(a) - 0.5 * (BX1 - BX0) / 16384, sx(b) + 0.5 * (BX1 - BX0) / 16384
            segs[k] = Rectangle(width=x1 - x0, height=BAR_H, stroke_color=NC[k], stroke_width=2).set_fill(fillc(NC[k], 0.35), 1)
            segs[k].move_to([(x0 + x1) / 2, BAR_Y, 0])
            slabs[k] = M(f"{a} to {b}", 16, NC[k]).move_to([segs[k].get_x(), BAR_Y + BAR_H / 2 + 0.22, 0])
        self.steps("Picture a cloakroom with 16,384 numbered hooks and three attendants. Your ticket always picks the same hook. "
                   "And a board by the door says which attendant looks after which hooks.", [
            (lambda: [FadeOut(qm), Create(bar), FadeIn(ticks), FadeIn(btitle)], 0.9),
            "and three attendants",
            (lambda: [*self.set_name(1, "attendant 1"), *self.set_name(2, "attendant 2"), *self.set_name(3, "attendant 3")], 0.7),
            "Your ticket",
            (lambda: self.set_mark(9055, GOLD_M, "one hook"), 0.6),
            "And a board",
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(segs[k]), FadeIn(slabs[k]), glow(boxes[k], NC[k], 1.03))
                                    for k in (1, 2, 3)], lag_ratio=0.45)], 1.8),
        ])
        btitle2 = VGroup(T("16,384", 24), T("hash slots", 19, GREY_B)).arrange(DOWN, buff=0.08).move_to(btitle)
        calc = M("CRC16(payment:42) mod 16384 = 9055", 18).move_to([-1.1, 1.45, 0])
        self.steps("Redis Cluster works the same way. The hooks are called hash slots. A key's slot is a checksum of the key, "
                   "mod 16,384, so payment:42 always lands in slot 9055.", [
            "The hooks are",
            (lambda: [swap(btitle, btitle2)], 0.6),
            "A key's slot",
            (lambda: [FadeIn(calc, shift=0.1 * UP)], 0.6),
            "always lands",
            (lambda: self.set_mark(9055, GOLD_M, "slot 9055"), 0.6),
        ])
        pick = Arrow([sx(9055), BAR_Y - BAR_H / 2 - 0.55, 0], [NX - NW / 2 + 0.1, NY[2] + NH / 2 + 0.06, 0], buff=0,
                     stroke_width=2.5, color=TEAL_M, max_tip_length_to_length_ratio=0.08)
        self.steps("The attendants are the servers, called nodes, each with its own address. And the board is the slot table. "
                   "Node two looks after slots 5461 to 10922, so payment:42 lives on node two.", [
            (lambda: [FadeOut(calc), *[a for k in (1, 2, 3) for a in self.set_name(k, f"node {k}")]], 0.7),
            "each with its own",
            (lambda: [*[a for k in (1, 2, 3) for a in self.set_addr(k)]], 0.6),
            "And the board",
            (lambda: [*self.cap("hooks: hash slots.   attendants: nodes.   the board: the slot table"),
                      *[glow(segs[k], NC[k], 1.0) for k in (1, 2, 3)]], 0.8),
            "Node two looks",
            (lambda: [*[a for k in (1, 2, 3) for a in self.set_range(k)], Indicate(slabs[2], color=TEAL_M)], 0.8),
            "so payment:42 lives",
            (lambda: [GrowArrow(pick), glow(boxes[2], TEAL_M, 1.03)], 0.8),
        ])

        # ---------------- scene 3: ask the wrong node ----------------
        a1 = to_node(1)
        self.steps("Now take the simplest client, a program that knows one address and treats it as one Redis. Ours knows node one. "
                   "It sends GET payment:42 to node one, and node one doesn't own slot 9055. What does node one do? Pause and guess.", [
            (lambda: [FadeOut(pick), *self.uncap()], 0.5),
            "Now take",
            (lambda: self.set_client("plain client", "knows node 1"), 0.6),
            "Ours knows",
            (lambda: [GrowArrow(a1)], 0.6),
            "It sends",
            (lambda: [go(1, GOLD_M, 0.8)], 0.8),
            "doesn't own",
            (lambda: [Indicate(self.ranges[1], color=BLUE_M)], 0.8),
            "Pause and guess",
            (lambda: self.cap("what does node 1 do? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        fwd = DashedLine([NX - 1.0, NY[1] - NH / 2 - 0.05, 0], [NX - 1.0, NY[2] + NH / 2 + 0.05, 0], dash_length=0.08,
                         stroke_width=2.5, color=GREY_B)
        fwd_x = tick(False, 0.14).move_to(fwd.get_center() + 0.32 * LEFT)
        self.steps("A kind attendant would walk to the next counter and fetch your coat. A Redis node never does. "
                   "Node one answers with an error: MOVED, slot 9055, and node two's address. It lives over there, so ask there.", [
            (lambda: self.uncap(), 0.3),
            "A kind attendant",
            (lambda: [Create(fwd)], 0.6),
            "never does",
            (lambda: [Create(fwd_x), *self.cap("a node never passes a command on")], 0.6),
            "Node one answers",
            (lambda: [back(1, RED_M, 0.8)], 0.8),
            (lambda: self.set_reply(1, "MOVED 9055 127.0.0.1:7002"), 0.5),
            "slot 9055, and",
            (lambda: [Indicate(self.mk[0], color=RED_M, scale_factor=1.4)], 0.6),
            "node two's address",
            (lambda: [Indicate(self.addrs[2], color=RED_M)], 0.7),
        ])
        a2 = to_node(2)
        ans = M("\"approved\"", 18, GREEN_M)
        self.steps("The client asks again, at node two, and gets its answer. Rude? A little. But that rudeness is why the cluster "
                   "can grow. Each node only ever works on its own slots, never on errands for the others.", [
            (lambda: [GrowArrow(a2)], 0.5),
            (lambda: [go(2, GOLD_M, 0.7)], 0.7),
            (lambda: [back(2, GREEN_M, 0.7)], 0.7),
            (lambda: [FadeIn(along(2, ans, side=-1, off=0.3))], 0.4),
            "Rude?",
            (lambda: [glow(boxes[1], BLUE_M, 1.03)], 0.7),
            "Each node only",
            (lambda: [*self.cap("each node works only on its own slots"),
                      LaggedStart(*[glow(segs[k], NC[k], 1.0) for k in (1, 2, 3)], lag_ratio=0.3)], 1.2),
        ])
        self.stamp("moved")

        # ---------------- scene 4: the extra trip ----------------
        a3 = to_node(3)
        self.steps("Following every MOVED works, but each one costs an extra round trip: a message there, and an answer back. "
                   "So if the plain client sends all its commands to node one, how many come back MOVED? Pause and guess.", [
            (lambda: [FadeOut(ans), FadeOut(fwd), FadeOut(fwd_x), *self.clear_reply(), *self.uncap()], 0.5),
            "an extra round trip",
            (lambda: self.cap("a round trip: a message there, and an answer back"), 0.5),
            (lambda: [go(1, GOLD_M, 0.6)], 0.6),
            (lambda: [back(1, GREY_B, 0.6)], 0.6),
            "So if the plain",
            (lambda: [GrowArrow(a3)], 0.5),
            "Pause and guess",
            (lambda: self.cap("all commands to node 1: how many come back MOVED? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        def six():
            ok = [True, False, False, True, False, False]
            dest = [None, 2, 3, None, 3, 2]
            seq = []
            for i in range(6):
                parts = [go(1, GOLD_M, 0.45), back(1, GREEN_M if ok[i] else RED_M, 0.45)]
                if not ok[i]:
                    parts += [go(dest[i], GOLD_M, 0.45), back(dest[i], GREEN_M, 0.45)]
                seq.append(Succession(*parts))
            return [LaggedStart(*seq, lag_ratio=0.28)]

        self.steps("About two in three. Node one owns a third of the slots, so two keys in three belong to someone else, "
                   "and each of those makes two trips instead of one. Wouldn't it be nice if the client could read the board before it asked?", [
            (lambda: self.cap("about 2 in 3: MOVED, then a second trip", RED_M), 0.5),
            "Node one owns",
            (lambda: [glow(segs[1], BLUE_M, 1.0)], 0.6),
            "so two keys",
            (lambda: six(), 3.6),
            "Wouldn't it be nice",
            (lambda: [*self.cap("wish: read the board before asking", WHITE),
                      LaggedStart(*[glow(segs[k], NC[k], 1.0) for k in (1, 2, 3)], lag_ratio=0.3)], 1.0),
        ])

        # ---------------- scene 5: a photo of the board ----------------
        tb = ctable()
        photo = VGroup(*[segs[k].copy() for k in (1, 2, 3)], *[slabs[k].copy() for k in (1, 2, 3)])
        self.steps("That's exactly what a cluster-aware client does. When it starts, it asks any node for the whole slot table, "
                   "its own photo of the board. And it opens a connection to every node.", [
            (lambda: [*self.uncap(), *self.set_client("cluster-aware", "client")], 0.6),
            "When it starts",
            (lambda: [go(1, GOLD_M, 0.6)], 0.6),
            (lambda: [back(1, WHITE, 0.6)], 0.6),
            "its own photo",
            (lambda: [photo.animate.scale(0.25).move_to(tb.get_center()).set_opacity(0)], 0.7),
            (lambda: [FadeIn(tb)], 0.4),
            "And it opens",
            (lambda: [a1.animate.set_color(BLUE_M), a2.animate.set_color(TEAL_M), a3.animate.set_color(PURPLE_M)], 0.6),
            (lambda: [go(1, WHITE, 0.5), go(2, WHITE, 0.5), go(3, WHITE, 0.5)], 0.5),
        ])
        self.remove(photo)
        rows = tb[1]
        self.steps("Then it works out each key's slot itself. payment:42 is slot 9055: straight to node two. "
                   "payment:43 is slot 13182: straight to node three. One round trip each, and no MOVED.", [
            "payment:42 is",
            (lambda: [Indicate(rows[2], color=TEAL_M, scale_factor=1.08)], 0.7),
            "straight to node two",
            (lambda: [go(2, GOLD_M, 0.55)], 0.55),
            (lambda: [back(2, GREEN_M, 0.55)], 0.55),
            "payment:43 is",
            (lambda: [*self.set_req("GET payment:43"), *self.set_mark(13182, GOLD_M, "slot 13182"),
                      Indicate(rows[3], color=PURPLE_M, scale_factor=1.08)], 0.7),
            "straight to node three",
            (lambda: [go(3, GOLD_M, 0.55)], 0.55),
            (lambda: [back(3, GREEN_M, 0.55)], 0.55),
            "One round trip",
            (lambda: self.cap("one round trip each, no MOVED", GREEN_M), 0.5),
        ])

        # ---------------- scene 6: the photo goes stale ----------------
        mig = Arrow([NX - 1.1, NY[2] - NH / 2 - 0.04, 0], [NX - 1.1, NY[3] + NH / 2 + 0.04, 0], buff=0, stroke_width=3,
                    color=GOLD_M, max_tip_length_to_length_ratio=0.3)
        self.steps("So far so good. But a photo can go out of date. Say someone running the cluster moves slot 9055 to node three. "
                   "The client's table still says node two.", [
            (lambda: [*self.uncap(), *self.set_req("GET payment:42"), *self.set_mark(9055, GOLD_M, "slot 9055")], 0.6),
            "Say someone",
            (lambda: [GrowArrow(mig)], 0.5),
            (lambda: [*self.set_mark(9055, PURPLE_M, "slot 9055"), *self.set_range(2, "5461 to 10922, not 9055", TEAL_M),
                      *self.set_range(3, "10923 to 16383 + 9055", PURPLE_M)], 0.8),
            "still says",
            (lambda: [FadeOut(mig), Indicate(rows[2], color=RED_M, scale_factor=1.08),
                      *self.cap("the client's photo: slot 9055 is on :7002 (out of date)", RED_M)], 0.8),
        ])
        tb2 = ctable("9055 → :7003")
        self.steps("So its next GET goes to node two, which answers MOVED, slot 9055, with node three's address. The client fixes "
                   "its table, usually by loading all of it again, because slots rarely move alone. Then it asks node three, "
                   "and from then on, it goes straight there.", [
            (lambda: self.uncap(), 0.3),
            (lambda: [go(2, GOLD_M, 0.6)], 0.6),
            "which answers",
            (lambda: [back(2, RED_M, 0.6)], 0.6),
            (lambda: self.set_reply(2, "MOVED 9055 127.0.0.1:7003", side=1), 0.5),
            "The client fixes",
            (lambda: [go(1, GOLD_M, 0.5)], 0.5),
            (lambda: [back(1, WHITE, 0.5)], 0.5),
            (lambda: [swap(tb, tb2)], 0.6),
            "Then it asks",
            (lambda: [*self.clear_reply(), go(3, GOLD_M, 0.55)], 0.55),
            (lambda: [back(3, GREEN_M, 0.55)], 0.55),
            "from then on",
            (lambda: [go(3, GOLD_M, 0.5)], 0.5),
            (lambda: [back(3, GREEN_M, 0.5)], 0.5),
        ])
        tb = tb2
        self.steps("With a cluster-aware client, a MOVED is rare, and it means one thing: the table changed. "
                   "A slot moved, or a replica took over from a dead primary.", [
            (lambda: self.cap("MOVED means: the table changed", WHITE), 0.5),
            "A slot moved",
            (lambda: self.cap("MOVED means: a slot moved, or a replica took over from a dead primary", WHITE), 0.5),
        ])
        self.stamp("stale")

        # ---------------- scene 7: the address, and a rule to keep ----------------
        self.steps("One trap. The client does the routing, so the address inside a MOVED must work from wherever the client runs. "
                   "Each node announces just one address.", [
            (lambda: self.cap("the address in a MOVED must work from where the client runs"), 0.5),
            "Each node announces",
            (lambda: [LaggedStart(*[Indicate(self.addrs[k], color=YELLOW_M) for k in (1, 2, 3)], lag_ratio=0.3)], 1.0),
        ])
        stop = tick(False, 0.15).move_to(c_out() + 0.5 * (n_in(2) - c_out()))
        self.steps("Run the cluster in Docker, a tool that runs each server as a small separate machine on your laptop, "
                   "and the nodes may announce addresses that only exist inside Docker. That's a board that sends guests down "
                   "the staff corridor. The lab makes every node announce 127.0.0.1, which works from both sides.", [
            "and the nodes may",
            (lambda: [*[a for k in (1, 2, 3) for a in self.set_addr(k, "inside Docker only", RED_M)]], 0.6),
            (lambda: [go(2, GOLD_M, 0.6, frac=0.5)], 0.6),
            (lambda: [Create(stop)], 0.4),
            "That's a board",
            (lambda: self.cap("a board that sends guests down the staff corridor"), 0.5),
            "The lab makes",
            (lambda: [FadeOut(stop), *[a for k in (1, 2, 3) for a in self.set_addr(k, None, GREEN_M)],
                      *self.cap("the lab: cluster-announce-ip 127.0.0.1", GREEN_M)], 0.7),
            (lambda: [go(2, GOLD_M, 0.55)], 0.55),
            (lambda: [back(2, GREEN_M, 0.55)], 0.55),
        ])
        ok_b = tick(True, 0.16).move_to([-2.9, 1.05, 0])
        pair = VGroup(Dot(radius=0.09, color=GOLD_M), Dot(radius=0.09, color=GOLD_M)).arrange(RIGHT, buff=0.12)
        brace = SurroundingRectangle(pair, buff=0.1, corner_radius=0.1, stroke_color=GOLD_M, stroke_width=2)
        txn = VGroup(brace, pair).move_to(c_out() + 0.3 * (n_in(2) - c_out()) + 0.0 * UP)
        no_t = tick(False, 0.15).next_to(txn, RIGHT, buff=0.25)
        self.steps("And one rule to carry into the next section. A cluster client splits a batch of commands into one batch per node. "
                   "But a transaction, a group of commands that runs as one step, can't be split across nodes. Keep that in your pocket.", [
            (lambda: [*self.uncap(), *[a for k in (1, 2, 3) for a in self.set_addr(k)]], 0.5),
            "splits a batch",
            (lambda: [*self.cap("a batch: split into one per node"), go(1, GOLD_M, 0.6), go(2, GOLD_M, 0.6), go(3, GOLD_M, 0.6)], 0.6),
            (lambda: [Create(ok_b.next_to(self.capm, RIGHT, buff=0.3))], 0.4),
            "But a transaction",
            (lambda: [FadeOut(ok_b), FadeIn(txn, shift=0.2 * RIGHT), *self.cap("a transaction: one step, can't be split", RED_M)], 0.7),
            "can't be split",
            (lambda: [Create(no_t)], 0.4),
            "Keep that",
            (lambda: [glow(brace, RED_M, 1.1)], 0.6),
        ])

        # ---------------- scene 8: the code ----------------
        self.play(FadeOut(txn), FadeOut(no_t), *self.uncap(), run_time=0.4)
        diagram = VGroup(*[m for m in self.mobjects if isinstance(m, VMobject)])
        diagram.save_state()
        jp = code_panel("Java (Jedis)", JAVA, -3.4)
        kp = code_panel("Kotlin (Lettuce)", KOTLIN, 3.4)
        outp = M("both print:  payment:42  slot 9055  on 127.0.0.1:7002", 18, GREEN_M).move_to([0, -2.35, 0]).set_z_index(10)

        def hl(rj, rk, color):
            return [jp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rj] + \
                   [kp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rk]

        self.steps("In Java and Kotlin, you give the cluster client one address, the seed. It loads the table from there and sends "
                   "each command to its owner. Both print the same line: payment:42, slot 9055, on node two.", [
            (lambda: [diagram.animate.set_opacity(0.06)], 0.5),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.6),
            "one address",
            (lambda: hl((0, 3), (0, 1), GOLD_M), 1.2),
            "sends each command",
            (lambda: hl((4,), (5,), TEAL_M), 1.0),
            "Both print",
            (lambda: [FadeIn(outp, shift=0.1 * UP)], 0.5),
        ], after=0.8)
        self.stamp("code")

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, which server do you ask? The one the table names. A key hashes to a slot, the table names the slot's node, "
                   "and a node never fetches for you. It tells you where to go.", [
            (lambda: [FadeOut(jp), FadeOut(kp), FadeOut(outp), Restore(diagram)], 0.7),
            "A key hashes",
            (lambda: [*self.cap("key → slot → the table's node", WHITE), Indicate(self.mk[0], color=YELLOW_M, scale_factor=1.4)], 0.6),
            "the table names",
            (lambda: [Indicate(tb[1][2], color=TEAL_M, scale_factor=1.08)], 0.6),
            "and a node never",
            (lambda: self.cap("a node never fetches for you: it tells you where to go", YELLOW_M), 0.5),
        ])
        self.steps("Ask the wrong one, and it costs you one extra trip, and a fresh copy of the board.", [
            (lambda: [go(2, GOLD_M, 0.5)], 0.5),
            (lambda: [back(2, RED_M, 0.5)], 0.5),
            "and a fresh copy",
            (lambda: [glow(tb[0], WHITE, 1.04)], 0.7),
        ], after=0.5)
        self.steps("One quick check. A plain client sends GET payment:43 to node one. What comes back? Pause and think.", [
            (lambda: [*self.uncap(), tb.animate.set_opacity(0.15), *self.set_client("plain client", "knows node 1"),
                      *self.set_req("GET payment:43"), *self.set_mark(13182, GOLD_M, "slot 13182")], 0.7),
            "sends GET",
            (lambda: [go(1, GOLD_M, 0.7)], 0.7),
            "Pause and think",
            (lambda: self.cap("GET payment:43 to node 1: what comes back? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("MOVED, slot 13182, with node three's address. Slot 13182 is in node three's range, so the client asks again there.", [
            (lambda: [*self.uncap(), back(1, RED_M, 0.6)], 0.6),
            (lambda: self.set_reply(1, "MOVED 13182 127.0.0.1:7003"), 0.5),
            "Slot 13182 is in",
            (lambda: [glow(segs[3], PURPLE_M, 1.0), Indicate(self.ranges[3], color=PURPLE_M)], 0.8),
            "so the client",
            (lambda: [go(3, GOLD_M, 0.55)], 0.55),
            (lambda: [back(3, GREEN_M, 0.55)], 0.55),
        ], after=0.3)
        self.play(*self.cap("a node never fetches for you: it tells you where to go", YELLOW_M), run_time=0.6)
        self.wait(2.0)
