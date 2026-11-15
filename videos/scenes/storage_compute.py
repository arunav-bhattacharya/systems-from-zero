from sfz import *

XS = {1: -4.8, 2: -1.6, 3: 1.6, 4: 4.8}
X3 = {1: -3.2, 2: 0.0, 3: 3.2}
NW = 2.8
N1Y, N1H = 0.45, 3.4                 # phase one: a node with its own disk
N2Y, N2H = 2.35, 1.5                 # phase two: compute only
BANDY, BANDH, BANDW = -1.45, 1.9, 12.8
NOTE_Y = -3.2
ZX = {"a": -4.3, "b": 0.0, "c": 4.3}
CPY_Y = -1.3
DBY = 2.45


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along a line (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def rrect(w, h, c, color=WHITE, sw=3, fill=None):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=sw)
    return r.set_fill(fill if fill is not None else fillc(color), 1).move_to(c)


class Node:
    """A shared-nothing node: its own CPU and memory, and its own disk with partitions on it."""

    def __init__(self, i, x, parts):
        self.i, self.x = i, x
        self.outer = rrect(NW, N1H, [x, N1Y, 0], WHITE, fill=BLACK)
        self.title = T(f"node {i}", 24).move_to([x, N1Y + N1H / 2 - 0.35, 0])
        self.cpu = VGroup(rrect(2.3, 0.6, [x, N1Y + 0.85, 0], BLUE_M, 2.5), T("CPU, memory", 20).move_to([x, N1Y + 0.85, 0]))
        self.disk = VGroup(rrect(2.3, 1.45, [x, N1Y - 0.75, 0], GREY_B, 2.5),
                           T("disk", 18, GREY_B).move_to([x, N1Y - 0.25, 0]))
        self.parts = {}
        for k, p in enumerate(parts):
            self.parts[p] = part(p).move_to(self.slot(k, len(parts)))

    def slot(self, k, n):
        dx = 0 if n == 1 else (-0.5 if k == 0 else 0.5)
        return np.array([self.x + dx, N1Y - 0.9, 0])

    def body(self):
        return VGroup(self.outer, self.title, self.cpu, self.disk)


def part(p, color=GOLD_M):
    return chip(p, color, 22).set_z_index(5)


def band_slot(k):
    return np.array([-3.75 + 1.5 * k, BANDY - 0.2, 0])


def compute(i, x, color=WHITE, label=None):
    o = rrect(NW, N2H, [x, N2Y, 0], color, fill=BLACK)
    t = T(label or f"node {i}", 24).move_to([x, N2Y + 0.38, 0])
    c = VGroup(rrect(2.4, 0.55, [x, N2Y - 0.25, 0], BLUE_M, 2.5), fit(T("CPU, memory, cache", 18), 2.1).move_to([x, N2Y - 0.25, 0]))
    return VGroup(o, t, c)


def note(s, color=GREY_B):
    return chip(s, color, 21).move_to([0, NOTE_Y, 0])


def copy_box(name, color=WHITE):
    x = ZX[name[0]] + (-0.85 if name[1] == "1" else 0.85)
    if name == "c3":
        x = ZX["c"] + 0.85
    r = rrect(1.45, 0.85, [x, CPY_Y, 0], color, 2.5)
    return VGroup(r, M(name, 22).move_to([x, CPY_Y, 0]))


class StorageCompute(Base):
    """found-05, section 2 (with section 1's shared nothing): three nodes each own a disk and two of six partitions; adding
    node 4 means copying two partitions (400 GB, invented) onto it. Separating storage from compute puts the partitions in
    a storage service and lets compute come and go. Aurora: 10 GB segments, six copies, two per zone in three zones; a
    write counts at 4 copies, a read needs 3 (3 + 4 > 6). Lose zone a: writes go on; lose c2 as well: writes stop, reads
    work, nothing committed is lost; a new copy takes about 10 s on a 10 Gbit/s link."""

    def construct(self):
        self.title_card("Separating storage from compute", "data in a shared service, compute that comes and goes")

        layout = {1: ["P1", "P2"], 2: ["P3", "P4"], 3: ["P5", "P6"]}
        nd = {i: Node(i, X3[i], layout[i]) for i in (1, 2, 3)}
        self.steps("The payments database runs on three nodes. Each has its own CPUs, memory and disk, "
                   "and its disk holds two of six partitions. They share nothing but the network.", [
            (lambda: [LaggedStart(*[FadeIn(nd[i].body(), shift=0.1 * UP) for i in nd], lag_ratio=0.25)], 1.2),
            "and its disk",
            (lambda: [LaggedStart(*[FadeIn(p, scale=0.8) for i in nd for p in nd[i].parts.values()], lag_ratio=0.12)], 1.0),
            "They share nothing",
            (lambda: [*[glow(nd[i].outer, WHITE, 1.02) for i in nd]], 0.9),
        ])

        n4 = Node(4, XS[4], [])
        move = note("before node 4 can help: copy 2 partitions, 400 GB", RED_M)

        def spread():
            out = []
            for i in (1, 2, 3):
                g = VGroup(nd[i].body(), *nd[i].parts.values())
                out.append(g.animate.shift((XS[i] - X3[i]) * RIGHT))
                nd[i].x = XS[i]
            return out

        self.steps("Month end needs more CPU. Add node 4, and before it can help, "
                   "two partitions, 400 gigabytes, must be copied onto it.", [
            (lambda: spread(), 0.8),
            "Add node 4",
            (lambda: [FadeIn(n4.body(), shift=0.1 * UP)], 0.6),
            "two partitions",
            (lambda: [nd[2].parts["P4"].animate(path_arc=-0.9).move_to(n4.slot(0, 2)),
                      nd[3].parts["P6"].animate(path_arc=-0.9).move_to(n4.slot(1, 2))], 1.4),
            (lambda: [FadeIn(move, shift=0.1 * UP)], 0.6),
        ])
        n4.parts = {"P4": nd[2].parts.pop("P4"), "P6": nd[3].parts.pop("P6")}

        back = note("compute and data grow and shrink together", GREY_A)
        self.steps("Removing it later moves them back. Compute and data grow and shrink together.", [
            (lambda: [n4.parts["P4"].animate(path_arc=0.9).move_to(nd[2].slot(1, 2)),
                      n4.parts["P6"].animate(path_arc=0.9).move_to(nd[3].slot(1, 2))], 1.4),
            (lambda: [FadeOut(n4.body()), FadeOut(move)], 0.6),
            "Compute and data",
            (lambda: [FadeIn(back, shift=0.1 * UP)], 0.6),
        ])
        nd[2].parts["P4"] = n4.parts.pop("P4")
        nd[3].parts["P6"] = n4.parts.pop("P6")

        band = rrect(BANDW, BANDH, [0, BANDY, 0], TEAL_M)
        blab = T("storage service", 22, TEAL_M)
        blab.move_to([BANDW / 2 - 0.25 - blab.width / 2, BANDY - BANDH / 2 + 0.3, 0])
        parts = {p: nd[i].parts[p] for i in nd for p in nd[i].parts}
        order = ["P1", "P2", "P3", "P4", "P5", "P6"]
        cmp = {i: compute(i, XS[i]) for i in (1, 2, 3)}
        links = {i: DashedLine([XS[i], N2Y - N2H / 2 - 0.05, 0], [XS[i], BANDY + BANDH / 2 + 0.05, 0], dash_length=0.1,
                               stroke_width=2, color=GREY_B) for i in (1, 2, 3, 4)}
        self.steps("Now split them. The data moves to a storage service on its own machines. "
                   "Compute nodes read it over the network, and keep only a cache.", [
            (lambda: [FadeOut(back)], 0.5),
            "The data moves",
            (lambda: [FadeIn(band), FadeIn(blab), *[parts[p].animate.move_to(band_slot(k)) for k, p in enumerate(order)],
                      *[FadeOut(nd[i].disk) for i in nd],
                      *[ReplacementTransform(a, b) for i in nd for a, b in zip((nd[i].outer, nd[i].title, nd[i].cpu), cmp[i])]], 1.3),
            "Compute nodes",
            (lambda: [*[glow(cmp[i][0], BLUE_M, 1.03) for i in nd]], 0.8),
            "over the network",
            (lambda: [*[Create(links[i]) for i in (1, 2, 3)]], 0.7),
        ])

        c4 = compute(4, XS[4], GREEN_M)
        free = note("adding compute moves no data", GREEN_M)
        self.steps("Now adding compute moves no data. A new node reads what it needs and helps at once, "
                   "and later it just stops.", [
            (lambda: [FadeIn(c4, shift=0.1 * DOWN)], 0.6),
            (lambda: [Create(links[4])], 0.4),
            "reads what it needs",
            (lambda: [flow(links[4], GOLD_M, 0.7, back=True)], 0.7),
            (lambda: [FadeIn(free, shift=0.1 * UP)], 0.5),
            "and later",
            (lambda: [FadeOut(c4), FadeOut(links[4])], 0.7),
        ])

        dur_note = note("now the storage service holds the only durable copy", GOLD_M)
        self.steps("Now the storage service holds the only durable copy. It must survive a dead disk, "
                   "even a lost availability zone: a separate site with its own power.", [
            (lambda: [FadeOut(free), FadeIn(dur_note, shift=0.1 * UP)], 0.7),
            (lambda: [glow(band, GOLD_M, 1.02)], 0.9),
        ])

        db = VGroup(rrect(3.6, 1.1, [0, DBY, 0], BLUE_M), T("database instance", 24).move_to([0, DBY + 0.19, 0]),
                    T("its memory: only a cache", 18, GREY_B).move_to([0, DBY - 0.24, 0]))
        zones = {z: rrect(3.95, 2.1, [ZX[z], BANDY + 0.05, 0], GREY_B, 2, fill=BLACK) for z in ZX}
        zlab = {z: T(f"zone {z}", 22, GREY_B).move_to([ZX[z], BANDY - 0.75, 0]) for z in ZX}
        names = ["a1", "a2", "b1", "b2", "c1", "c2"]
        cp = {n: copy_box(n) for n in names}
        seg = T("one 10 GB segment, six copies", 22, TEAL_M).move_to([0, 0.35, 0])
        self.steps("Amazon's Aurora does this. It cuts the data into 10 gigabyte segments, "
                   "and keeps six copies of each, two in each of three zones.", [
            (lambda: [FadeOut(dur_note), *[FadeOut(links[i]) for i in (1, 2, 3)], FadeOut(cmp[2]), FadeOut(cmp[3]),
                      *[ReplacementTransform(a, b) for a, b in zip(cmp[1], db)]], 0.9),
            "It cuts",
            (lambda: [*[FadeOut(parts[p]) for p in order], FadeOut(blab), ReplacementTransform(band, VGroup(*zones.values())),
                      FadeIn(seg)], 1.0),
            "and keeps six",
            (lambda: [LaggedStart(*[FadeIn(cp[n], scale=0.9) for n in names], lag_ratio=0.15)], 1.1),
            "two in each",
            (lambda: [*[FadeIn(zlab[z]) for z in ZX]], 0.6),
        ])

        lines = {n: Line([cp[n][0].get_center()[0] * 0.18, DBY - 0.6, 0], cp[n][0].get_top() + 0.08 * UP, stroke_width=2,
                         color=GREY_D) for n in names}
        wst = T("write: 0 of 6", 26).move_to([-3.0, NOTE_Y, 0])
        fast = ["b1", "a1", "c1", "b2"]
        self.steps("On a commit, the database sends only a short log record, never whole pages. "
                   "The write counts once four copies have it, and the slow two catch up later.", [
            (lambda: [FadeOut(seg), *[Create(lines[n]) for n in names]], 0.6),
            "sends only",
            (lambda: [*[flow(lines[n], BLUE_M, 0.8) for n in fast]], 0.8),
            "The write counts",
            (lambda: [FadeIn(wst)], 0.3),
            *[(lambda n=n, k=k: [cp[n][0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M), 1),
                                Transform(wst, T(f"write: {k + 1} of 6", 26, GREEN_M if k == 3 else WHITE).move_to(wst))], 0.35)
              for k, n in enumerate(fast)],
            (lambda: [Transform(wst, T("write: 4 of 6, committed", 26, GREEN_M).move_to([-3.0, NOTE_Y, 0]))], 0.4),
            "and the slow two",
            (lambda: [*[flow(lines[n], BLUE_M, 0.8) for n in ("a2", "c2")]], 0.8),
            (lambda: [*[cp[n][0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M), 1) for n in ("a2", "c2")]], 0.5),
        ])

        rst = T("read: 3 of 6", 26, BLUE_M).move_to([3.3, NOTE_Y, 0])
        reads = ["a2", "c2", "c1"]
        self.steps("A read asks three copies. Any three overlap any four, since three plus four is more than six, "
                   "so a read always finds the newest write.", [
            (lambda: [FadeIn(rst)], 0.4),
            (lambda: [*[flow(lines[n], BLUE_M, 0.7, back=True) for n in reads]], 0.7),
            "Any three",
            (lambda: [*[cp[n][0].animate.set_stroke(BLUE_M, width=6) for n in reads]], 0.5),
            "so a read",
            (lambda: [glow(cp["c1"][0], GOLD_M, 1.12)], 0.9),
        ])

        def kill(n):
            x = tick(False, 0.28).move_to(cp[n][0].get_center()).set_z_index(6)
            return [cp[n][0].animate.set_stroke(RED_M, width=3).set_fill(fillc(RED_M), 1), cp[n][1].animate.set_color(GREY_D),
                    lines[n].animate.set_color(RED_M).set_opacity(0.3), Create(x)], x

        def plain():
            return [cp[n][0].animate.set_stroke(WHITE, width=2.5).set_fill(BLACK, 1) for n in names]

        xa = {}
        alive = ["b1", "b2", "c1", "c2"]

        def zone_a():
            out = []
            for n in ("a1", "a2"):
                an, x = kill(n)
                xa[n] = x
                out += an
            return out + [zones["a"].animate.set_stroke(RED_M), zlab["a"].animate.set_color(RED_M)]

        self.steps("Now a whole zone fails. Two copies are gone, four are left, and writes carry on.", [
            (lambda: [FadeOut(rst), *plain(), Transform(wst, T("write: needs 4", 26).move_to([-3.0, NOTE_Y, 0]))], 0.5),
            "Now a whole zone",
            (lambda: zone_a(), 0.8),
            "and writes carry on",
            (lambda: [*[flow(lines[n], BLUE_M, 0.7) for n in alive]], 0.7),
            (lambda: [*[cp[n][0].animate.set_stroke(GREEN_M) for n in alive],
                      Transform(wst, T("write: 4 of 6, committed", 26, GREEN_M).move_to([-3.0, NOTE_Y, 0]))], 0.5),
        ])

        xc = {}

        def c2_dies():
            an, x = kill("c2")
            xc["c2"] = x
            return an

        rst2 = T("read: 3 of 6", 26, GREEN_M).move_to([3.3, NOTE_Y, 0])
        self.steps("Then the disk under c2 dies. With three left, writes stop, "
                   "but reads still work, and nothing committed is lost.", [
            (lambda: [*[cp[n][0].animate.set_stroke(WHITE) for n in ("b1", "b2", "c1")]], 0.4),
            "under c2",
            (lambda: c2_dies(), 0.8),
            "writes stop",
            (lambda: [Transform(wst, T("write: 3 of 6, stopped", 26, RED_M).move_to([-3.0, NOTE_Y, 0]))], 0.6),
            "but reads",
            (lambda: [FadeIn(rst2), *[flow(lines[n], GREEN_M, 0.7, back=True) for n in ("b1", "b2", "c1")]], 0.7),
            "and nothing committed",
            (lambda: [*[glow(cp[n][0], GREEN_M, 1.08) for n in ("b1", "b2", "c1")]], 0.9),
        ])

        c3 = copy_box("c3", GREEN_M)
        rep = ArcBetweenPoints(cp["c1"][0].get_top() + 0.05 * UP, c3[0].get_top() + 0.05 * UP, angle=-PI / 2, stroke_width=3,
                               color=GREEN_M)
        rlab = T("new copy: 10 GB, about 10 s", 26, GREEN_M).move_to([3.3, NOTE_Y, 0])
        lines["c3"] = Line([c3[0].get_center()[0] * 0.18, DBY - 0.6, 0], c3[0].get_top() + 0.08 * UP, stroke_width=2, color=GREY_D)

        def arc_flow():
            d = Dot(radius=0.08, color=GREEN_M).move_to(rep.get_start()).set_opacity(0).set_z_index(6)
            return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, rep, run_time=0.9), FadeOut(d, run_time=0.15))
        self.steps("A new copy of the 10 gigabyte segment takes about ten seconds, "
                   "and with four copies again, writes resume.", [
            (lambda: [FadeOut(cp["c2"]), FadeOut(xc["c2"]), FadeOut(lines["c2"])], 0.5),
            (lambda: [FadeIn(c3, scale=0.9)], 0.5),
            (lambda: [Create(rep), ReplacementTransform(rst2, rlab)], 0.5),
            (lambda: [arc_flow()], 1.1),
            "and with four",
            (lambda: [FadeOut(rep), Create(lines["c3"]), c3[0].animate.set_stroke(WHITE).set_fill(BLACK, 1),
                      Transform(wst, T("write: 4 of 6, committed", 26, GREEN_M).move_to([-3.0, NOTE_Y, 0]))], 0.6),
        ])

        self.steps("Put the durable copy in a storage service, and compute can come and go. "
                   "Always ask where the durable copy lives, and what is only a cache.", [
            (lambda: [*[glow(zones[z], TEAL_M, 1.02) for z in ZX]], 1.0),
            "and compute",
            (lambda: [glow(db[0], BLUE_M)], 0.9),
            "and what is only",
            (lambda: [Indicate(db[2], color=BLUE_M)], 0.9),
        ])
        self.wait(0.6)
