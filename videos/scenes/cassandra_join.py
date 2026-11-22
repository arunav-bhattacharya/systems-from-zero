from sfz import *

SAY.insert(0, (r"\bcass(\d)\b", r"cass \1"))
SAY.insert(0, (r"\bnodetool\b", "node tool"))
SAY.insert(0, (r"\bUJ\b", "U J"))
SAY.insert(0, (r"\bUN\b", "U N"))
SAY.insert(0, (r"\bNORMAL\b", "normal"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RC, RR = np.array([-4.65, 0.6, 0]), 1.6                 # the token ring
NX = [-1.6, 0.7, 3.0, 5.3]                             # node boxes
NY, NW, NH = 0.6, 2.0, 2.8
DISK_Y, DISK_W, DISK_H = 0.2, 1.2, 1.1
MID_Y, LOW_Y, BAR_Y, CAP_Y = -1.55, -2.2, -2.75, -3.27
NC = [BLUE_M, TEAL_M, PURPLE_M, GREEN_M]


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0]))

    def line(self, key, s, y, color=WHITE, size=22, x=1.85, w=8.6):
        return self.put(key, fit(T(s, size, color), w).move_to([x, y, 0]))

    def put(self, key, mob, d=UP):
        old = self.slots.get(key)
        self.slots[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.slots.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0, x=0.0):
        bar = Line([x - 1.0, BAR_Y, 0], [x + 1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(w, h, color, at, a=0.14):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(
        fillc(color, a), 1).move_to(at)


def node(k):
    x = NX[k]
    return VGroup(rbox(NW, NH, NC[k], [x, NY, 0]), T(f"cass{k + 1}", 24).move_to([x, NY + 1.1, 0]))


def disk_outline(k):
    return Rectangle(width=DISK_W, height=DISK_H, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1).move_to([NX[k], DISK_Y, 0])


def disk_fill(k, frac, color=None):
    h = max(0.001, DISK_H * frac)
    r = Rectangle(width=DISK_W - 0.08, height=h, stroke_width=0).set_fill(fillc(color or NC[k], 0.6), 1)
    return r.move_to([NX[k], DISK_Y - DISK_H / 2 + 0.04 + h / 2 - 0.04 * frac, 0]).set_z_index(1)


def load_lbl(k, s, color=WHITE):
    return M(s, 16, color).move_to([NX[k], DISK_Y, 0]).set_z_index(3)


def status(k, s, color):
    t = M(s, 18, color)
    r = RoundedRectangle(corner_radius=0.06, width=0.7, height=0.38, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.25), 1)
    return VGroup(r, t).move_to([NX[k], NY + 0.68, 0])


def owns(k, s, color=GREY_B):
    return T(s, 18, color).move_to([NX[k], NY - 1.15, 0])


def tick_at(deg, color, long=False):
    a = np.radians(deg)
    u = np.array([np.cos(a), np.sin(a), 0])
    r0, r1 = (RR - 0.22, RR + 0.22) if long else (RR - 0.13, RR + 0.13)
    return Line(RC + r0 * u, RC + r1 * u, stroke_width=4 if long else 3, color=color).set_z_index(2)


def arc_to4(k, color=YELLOW_M):
    a = np.array([NX[k], NY + NH / 2 + 0.08, 0])
    b = np.array([NX[3] - 0.25 + 0.15 * k, NY + NH / 2 + 0.08, 0])
    return ArcBetweenPoints(a, b, angle=-0.9 + 0.15 * k)


def ride(path, color=YELLOW_M, rt=0.9, n=1, lag=0.25):
    ds = []
    for i in range(n):
        d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_z_index(6)
        ds.append(Succession(Wait(i * lag), FadeIn(d, run_time=0.05), MoveAlongPath(d, path.copy(), run_time=rt), FadeOut(d, run_time=0.1)))
    return AnimationGroup(*ds)


class CassandraJoin(Base):
    """shard-06, section 2. The office whose cabinets fill because nobody shreds. Three nodes, three copies, 1.16 MiB
    each. cass4 bootstraps: learns the map from its seed, picks 16 tokens, shows UJ, gets copies of new writes, waits
    ring_delay. It streams each of 47 ranges from the replica it replaces (16, 16, 15), because copying from another
    replica can lose a write held by two of three. NORMAL (UN, 73.2%), but the old disks stay full until nodetool
    cleanup (cass1: 5,000 partitions to 3,729). Guardrails, moral, and a check."""

    def construct(self):
        self.slots = {}
        self.title_card("A new node joins, and nobody shreds", "bootstrap, streaming and cleanup in Cassandra")

        nodes = [node(k) for k in range(4)]
        disks = [disk_outline(k) for k in range(4)]
        fills = [disk_fill(k, 1.0) for k in range(3)] + [disk_fill(3, 0.0)]
        loads = [load_lbl(k, "1.16 MiB") for k in range(3)]

        # ---------------- scene 1: the office that ran out of cabinets ----------------
        self.steps("Picture an office with three clerks, each with a full copy of the account files.", [
            (lambda: [LaggedStart(*[FadeIn(VGroup(nodes[k], disks[k], fills[k])) for k in range(3)], lag_ratio=0.2),
                      *self.cap("three clerks, each with a full copy of the files", WHITE, 26)], 1.2),
        ])
        dash4 = DashedVMobject(RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=GREEN_M, stroke_width=3), num_dashes=50).move_to([NX[3], NY, 0])
        self.steps("For the busy season, a fourth clerk is hired. She takes over a share of the alphabet, "
                   "and copies those files from the colleagues handing them over.", [
            "a fourth clerk",
            (lambda: [FadeIn(dash4), *self.cap("a fourth clerk takes over a share", WHITE, 26)], 0.6),
            "and copies",
            (lambda: [*[ride(arc_to4(k), YELLOW_M, 0.9, 2) for k in range(3)]], 1.4),
            (lambda: [Transform(fills[3], disk_fill(3, 0.73)), FadeIn(disks[3])], 0.6),
        ])
        full = T("cabinets full", 22, RED_M).move_to([NX[1], MID_Y, 0])
        self.steps("Soon the office runs out of cabinet space. Nobody told the old clerks to shred the files they gave away.", [
            "runs out",
            (lambda: [FadeIn(full), *[glow(disks[k], RED_M, 1.06) for k in range(3)]], 0.9),
            "Nobody told",
            (lambda: self.cap("nobody told the old clerks to shred", RED_M, 26), 0.5),
        ])
        self.steps("Cassandra, the database where no machine is in charge, does the same. "
                   "When a new node joins, the old ones keep every row they handed over.", [
            (lambda: [FadeOut(full), FadeOut(dash4), Transform(fills[3], disk_fill(3, 0.0)), FadeOut(disks[3]),
                      *self.cap("Cassandra: the database where no machine is in charge", WHITE, 26)], 0.8),
            "the old ones keep",
            (lambda: [*[glow(disks[k], RED_M, 1.06) for k in range(3)]], 0.9),
        ])
        logc = chip("cass4: NORMAL", GREEN_M, 22, mono=True).move_to([NX[3], NY, 0])
        qm = T("?", 40, YELLOW_M).next_to(logc, DOWN, buff=0.2)
        self.steps("And the join ends with a log line saying the new node is NORMAL, which sounds like the end. "
                   "So what actually moves, from where, and what's left behind?", [
            "a log line",
            (lambda: [FadeIn(logc, shift=0.1 * UP)], 0.5),
            "So what",
            (lambda: [FadeIn(qm), *self.cap("what moves, from where, and what's left behind?", YELLOW_M, 26)], 0.6),
        ], after=0.5)

        # ---------------- scene 2: three nodes, three copies ----------------
        rng = np.random.default_rng(4)
        degs = rng.permutation(np.linspace(0, 360, 48, endpoint=False) + rng.uniform(-2.5, 2.5, 48))
        owner = [i % 3 for i in range(48)]
        ticks = [tick_at(d, NC[o]) for d, o in zip(degs, owner)]
        ring = Circle(radius=RR, stroke_color=GREY_C, stroke_width=2).move_to(RC)
        rlab = T("token ring", 22, GREY_B).move_to(RC + np.array([0, RR + 0.45, 0]))
        sts = [status(k, "UN", GREEN_M) for k in range(3)]
        ows = [owns(k, "owns 100%") for k in range(3)]
        self.steps("Here's the lab cluster. Three nodes, and three copies of every row, so each node holds all of it: "
                   "50,000 ledger entries, 1.16 megabytes on each disk.", [
            (lambda: [FadeOut(logc), FadeOut(qm), *self.cap("clerk = node,   files = rows,   cabinet = disk", WHITE, 26)], 0.6),
            "three copies",
            (lambda: [*[FadeIn(s) for s in sts]], 0.5),
            "50,000",
            (lambda: [*[FadeIn(l) for l in loads], *self.line("mid", "50,000 ledger entries, 3 copies: every node holds every row", MID_Y, WHITE)], 0.6),
        ])
        self.steps("Each node has 16 tokens, its places on the ring, and a range is the stretch of ring between two tokens.", [
            (lambda: [Create(ring), FadeIn(rlab)], 0.6),
            "Each node has",
            (lambda: [LaggedStart(*[Create(t) for t in ticks], lag_ratio=0.02), *self.cap("token: a node's place on the ring", WHITE, 26)], 1.3),
            "a range is",
            (lambda: self.cap("range: the stretch of ring between two tokens", WHITE, 26), 0.5),
        ])
        self.steps("Every node owns all of it: a hundred percent.", [
            (lambda: [*[FadeIn(o) for o in ows]], 0.6),
        ])

        # ---------------- scene 3: cass4 gets ready ----------------
        self.steps("cass4 starts with the same cluster name, cass1 as its seed, empty data folders, and its own address not in the seed list.", [
            (lambda: [*self.drop("mid"), FadeIn(nodes[3]), FadeIn(disks[3]), *self.cap("cass4: same cluster name, seed cass1, empty folders", WHITE, 26)], 0.8),
            "not in the seed",
            (lambda: self.cap("its own address not in the seed list", WHITE, 26), 0.5),
        ])
        self.steps("That last part means it will bootstrap: copy its share of the data on its first start.", [
            "bootstrap",
            (lambda: self.cap("bootstrap: copy its share of the data on its first start", YELLOW_M, 26), 0.6),
        ])
        seed = T("seed", 18, GOLD_M).move_to([NX[0], NY + NH / 2 + 0.25, 0])
        mapc = arc_to4(0)
        self.steps("It asks the seed for the map, and learns all 48 tokens.", [
            (lambda: [FadeIn(seed)], 0.4),
            "asks the seed",
            (lambda: [ride(mapc, GOLD_M, 1.0)], 1.1),
            (lambda: [*self.line("mid", "map from the seed: 48 tokens, and the schema", MID_Y, GOLD_M),
                      LaggedStart(*[t.animate(rate_func=there_and_back).scale(1.4) for t in ticks], lag_ratio=0.01)], 1.0),
        ])
        new_degs = [d + 3.75 for d in degs[::3][:16]]
        nticks = [tick_at(d, GREEN_M, long=True) for d in new_degs]
        s4 = status(3, "UJ", YELLOW_M)
        self.steps("It picks 16 tokens of its own and announces them by gossip. Everyone now shows it as UJ: up, and joining.", [
            "It picks",
            (lambda: [LaggedStart(*[Create(t) for t in nticks], lag_ratio=0.05), *self.line("mid", "16 new tokens: each cuts a slice off an existing range", MID_Y, GREEN_M)], 1.2),
            "Everyone now",
            (lambda: [FadeIn(s4), *self.cap("UJ: up, and joining", YELLOW_M, 26)], 0.6),
        ])
        coord = np.array([NX[1], 3.3, 0])
        cw = T("a new write", 18, YELLOW_M).move_to(coord + 0.0 * UP)
        self.steps("From this moment, every new write for the ranges it's about to own gets a copy sent to cass4 too, "
                   "so nothing written during the copy is missed.", [
            (lambda: [FadeIn(cw)], 0.4),
            "every new write",
            (lambda: [ride(Line(coord + 0.25 * DOWN, np.array([NX[0], NY + NH / 2 + 0.1, 0])), YELLOW_M, 0.8),
                      ride(Line(coord + 0.25 * DOWN, np.array([NX[3], NY + NH / 2 + 0.1, 0])), YELLOW_M, 1.1)], 1.2),
            "so nothing",
            (lambda: [FadeOut(cw), *self.cap("new writes reach cass4 during the copy", WHITE, 26)], 0.5),
        ])
        bar = Line([NX[3] - 0.9, LOW_Y, 0], [NX[3] + 0.9, LOW_Y, 0], stroke_width=5, color=GREY_B)
        self.steps("Then it waits 30 seconds, so the whole cluster has heard.", [
            (lambda: [*self.line("mid", "ring delay: wait 30 seconds, so everyone has heard", MID_Y, WHITE), Create(bar)], 0.5),
            (lambda: [Uncreate(bar)], 1.8),
        ], after=0.4)

        # ---------------- scene 4: from the replica it replaces ----------------
        qs = [T("?", 34, YELLOW_M).move_to([NX[k], DISK_Y, 0]).set_z_index(5) for k in range(3)]
        self.steps("Now the copy. cass4 takes over 47 ranges. For each one, three nodes have a copy. "
                   "Which one should it copy from? Does any copy do? Pause and guess.", [
            (lambda: [*self.drop("mid"), *self.cap("47 ranges to take over", WHITE, 26)], 0.5),
            "three nodes have",
            (lambda: [*[glow(disks[k], YELLOW_M, 1.06) for k in range(3)]], 0.8),
            "Which one",
            (lambda: [*[FadeIn(q, scale=0.6) for q in qs]], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Cassandra insists on one: the replica it replaces, the node that held that range before and won't afterwards.", [
            (lambda: [*[FadeOut(q) for q in qs], *self.cap("copy from the replica it replaces: held it before, won't after", GREEN_M, 26)], 0.6),
        ])
        wch = chip("write", GOLD_M, 18).move_to([NX[1], 3.3, 0])
        wm = [Square(0.22, stroke_width=0).set_fill(GOLD_M, 1).move_to([NX[k] + 0.4, DISK_Y + 0.35, 0]).set_z_index(4) for k in range(2)]
        gap = DashedVMobject(Square(0.22, stroke_color=GREY_B, stroke_width=2), num_dashes=12).move_to([NX[2] + 0.4, DISK_Y + 0.35, 0]).set_z_index(4)
        self.steps("Here's why. Say a write was confirmed by cass1 and cass2 only: two of three, a majority, so the app was told it's safe.", [
            "Say a write",
            (lambda: [FadeIn(wch, shift=0.1 * DOWN)], 0.4),
            (lambda: [*[FadeIn(w, shift=0.6 * DOWN) for w in wm], Create(gap)], 0.8),
            "two of three",
            (lambda: [*self.line("mid", "confirmed by 2 of 3: the app was told it's safe", MID_Y, GOLD_M)], 0.5),
        ])
        bad = DashedLine(np.array([NX[2] + 0.2, NY - NH / 2 - 0.1, 0]), np.array([NX[3] - 0.2, NY - NH / 2 - 0.1, 0]), color=RED_M, stroke_width=3)
        self.steps("cass4 is taking cass1's place for that range. If it copied from cass3, which missed the write, only cass2 would still have it.", [
            "taking cass1's place",
            (lambda: [glow(nodes[0][0], BLUE_M, 1.03), glow(nodes[3][0], GREEN_M, 1.03)], 0.8),
            "If it copied",
            (lambda: [Create(bad)], 0.6),
            "only cass2",
            (lambda: [nodes[0].animate.set_opacity(0.3), wm[0].animate.set_opacity(0.3), *self.line("mid", "copied from cass3: only cass2 still has the write", MID_Y, RED_M)], 0.7),
        ])
        xx = tick(False, 0.18).move_to(bad.get_center() + 0.0 * UP).set_z_index(6)
        self.steps("A later read that asks cass3 and cass4 would miss a write the app was promised.", [
            (lambda: [glow(nodes[2][0], RED_M, 1.03), glow(nodes[3][0], RED_M, 1.03)], 0.9),
            "would miss",
            (lambda: [Create(xx)], 0.5),
        ], after=0.4)
        arcs = [arc_to4(k) for k in range(3)]
        sent = [T(s, 18, NC[k]).move_to([NX[k], NY - 1.15, 0]) for k, s in enumerate(["sends 16 ranges", "sends 16 ranges", "sends 15 ranges"])]
        self.steps("So it copies 16 ranges from cass1, 16 from cass2 and 15 from cass3, about 280 kilobytes from each, all at the same time.", [
            (lambda: [FadeOut(VGroup(xx, bad, wch, gap, *wm)), nodes[0].animate.set_opacity(1), *self.drop("mid", "cap")], 0.5),
            "16 ranges",
            (lambda: [*[Transform(ows[k], sent[k]) for k in range(3)]], 0.6),
            "about 280",
            (lambda: [*[ride(arcs[k], NC[k], 1.0, 4, 0.3) for k in range(3)], Transform(fills[3], disk_fill(3, 0.73)),
                      *self.line("mid", "276, 300 and 280 KiB, all at the same time", MID_Y, WHITE)], 2.2),
        ])
        self.steps("This is called streaming.", [
            (lambda: [*[ride(arcs[k], NC[k], 0.8, 2, 0.3) for k in range(3)], *self.cap("streaming: copying ranges over the network to the new node", YELLOW_M, 26)], 1.2),
        ], after=0.4)

        # ---------------- scene 5: NORMAL is not the end ----------------
        un4 = status(3, "UN", GREEN_M)
        own4 = owns(3, "owns 73.2%", GREEN_M)
        l4 = load_lbl(3, "3/4")
        self.steps("cass4 switches to NORMAL, and shows UN. It owns 73.2 percent of the data, and the old nodes about 75 percent each.", [
            (lambda: [*self.drop("mid", "cap"), swap(s4, un4), FadeIn(l4)], 0.6),
            "It owns",
            (lambda: [FadeIn(own4)], 0.5),
            "and the old",
            (lambda: [*[Transform(ows[k], owns(k, "owns about 75%")) for k in range(3)]], 0.6),
        ])
        self.steps("But look at their disks. Still 1.16 megabytes. Cassandra never deletes data just because a node stopped owning it.", [
            "But look",
            (lambda: [*[glow(disks[k], RED_M, 1.06) for k in range(3)]], 0.9),
            "Still",
            (lambda: [*[Indicate(l, color=RED_M) for l in loads]], 0.8),
            "Cassandra never",
            (lambda: self.cap("Cassandra never deletes data a node stopped owning", RED_M, 26), 0.5),
        ])
        self.steps("So three quarters of the rows now sit on four disks, and only three of those copies count. The office's cabinets, exactly.", [
            (lambda: self.line("mid", "data on 4 disks; only 3 copies count", MID_Y, RED_M, 24), 0.6),
            "The office's",
            (lambda: [*[glow(disks[k], RED_M, 1.06) for k in range(4)]], 0.9),
        ], after=0.5)

        # ---------------- scene 6: cleanup, and the guardrails ----------------
        cl = chip("nodetool cleanup", YELLOW_M, 20, mono=True).move_to([NX[1] + 1.15, 3.2, 0])
        self.steps("The shredding is one command, nodetool cleanup. On each old node, it rewrites its files without the ranges it gave away.", [
            (lambda: [FadeIn(cl, shift=0.1 * DOWN), *self.drop("cap")], 0.6),
            "On each old node",
            (lambda: [Transform(fills[0], disk_fill(0, 0.75)), Transform(loads[0], load_lbl(0, "3/4"))], 0.8),
            (lambda: [Transform(fills[1], disk_fill(1, 0.75)), Transform(loads[1], load_lbl(1, "3/4"))], 0.8),
            (lambda: [Transform(fills[2], disk_fill(2, 0.75)), Transform(loads[2], load_lbl(2, "3/4"))], 0.8),
        ])
        self.steps("cass1 went from 5,000 partitions to 3,729. What each node streamed to cass4 is exactly what its cleanup deleted.", [
            (lambda: self.line("mid", "cass1: 5,000 partitions → 3,729", MID_Y, GREEN_M, 24), 0.6),
            "What each node",
            (lambda: [*[ride(arcs[k], NC[k], 0.9) for k in range(3)], *self.cap("streamed to cass4  =  deleted by cleanup", GREEN_M, 26)], 1.0),
        ])
        self.steps("Here the office picture breaks: a clerk would notice the full cabinet. A node never does.", [
            "Here the office",
            (lambda: self.cap("where the office picture breaks: a node never notices", GREY_B, 26), 0.5),
        ], after=0.4)
        self.steps("A few rules. Run cleanup after the last new node has joined, on one old node at a time, because rewriting files costs disk work.", [
            (lambda: self.cap("cleanup: after the last join, one old node at a time", WHITE, 26), 0.6),
            "one old node",
            (lambda: [Succession(*[glow(disks[k], YELLOW_M, 1.06) for k in range(3)])], 1.5),
        ])
        self.steps("Join one node at a time, and wait for UN, because two joins at once would each plan against a ring that's about to change.", [
            (lambda: self.cap("join one node at a time, and wait for UN", WHITE, 26), 0.6),
            "a ring",
            (lambda: [Rotate(VGroup(ring, *ticks, *nticks), angle=0.25, about_point=RC, rate_func=there_and_back)], 1.0),
        ])
        self.steps("And expect hours, not seconds: the lab join took 90 seconds, a real node takes hours. "
                   "Removing a node is a join in reverse: it streams its ranges to the new owners, then leaves.", [
            (lambda: self.cap("the lab: 90 seconds.   a real node: hours", WHITE, 26), 0.6),
            "Removing a node",
            (lambda: [*self.cap("removing a node: a join in reverse", WHITE, 26),
                      *[ride(ArcBetweenPoints(arcs[k].get_end(), arcs[k].get_start(), angle=0.9 - 0.15 * k), GREEN_M, 1.0, 2) for k in range(3)]], 1.3),
        ], after=0.5)

        # ---------------- scene 7: the moral, and a check ----------------
        steps_g = VGroup(*[chip(s, GREY_B, 18) for s in ["map", "tokens", "new writes", "stream", "NORMAL", "cleanup"]]).arrange(RIGHT, buff=0.25)
        steps_g.move_to([0, MID_Y, 0])
        self.steps("So a join is not one step. Learn the map, pick tokens, take new writes, copy each range from the node it replaces, "
                   "and only then switch to NORMAL.", [
            (lambda: [*self.drop("mid", "cap"), FadeIn(steps_g)], 0.6),
            "Learn the map",
            (lambda: [glow(steps_g[0][0], YELLOW_M, 1.1)], 0.6),
            "pick tokens",
            (lambda: [glow(steps_g[1][0], YELLOW_M, 1.1)], 0.6),
            "take new writes",
            (lambda: [glow(steps_g[2][0], YELLOW_M, 1.1)], 0.6),
            "copy each range",
            (lambda: [glow(steps_g[3][0], YELLOW_M, 1.1)], 0.6),
            "switch to NORMAL",
            (lambda: [glow(steps_g[4][0], GREEN_M, 1.1)], 0.6),
        ])
        self.steps("And the old copies stay until someone runs cleanup. Nothing tidies itself.", [
            (lambda: [glow(steps_g[5][0], RED_M, 1.1)], 0.7),
            "Nothing tidies",
            (lambda: self.cap("nothing tidies itself: someone runs cleanup", YELLOW_M, 28), 0.6),
        ], after=0.6)
        self.steps("One quick check. Next week you add cass5. When do you run cleanup, and on which nodes? Pause and think.", [
            (lambda: self.cap("you add cass5: when do you run cleanup, and on which nodes?", WHITE, 26), 0.6),
            "Pause and think",
            (lambda: [FadeOut(steps_g), *self.line("mid", "pause and think", MID_Y, YELLOW_M, 24, x=0)], 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("After cass5 shows UN, on every old node, one at a time.", [
            (lambda: [*self.drop("mid"), *self.cap("after cass5 shows UN: every old node, one at a time", GREEN_M, 28)], 0.6),
            (lambda: [Succession(*[glow(disks[k], GREEN_M, 1.06) for k in range(4)])], 1.6),
        ], after=0.3)
        self.wait(2.0)
