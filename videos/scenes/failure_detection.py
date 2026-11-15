import math

from sfz import *

CX0, CXS, CY0, CYS = -5.9, 0.52, -2.5, 1.0        # silence chart: t = 0 s at CX0, silence 0 at CY0
HX0, HXS, HSC = 2.7, 1.0, 1.6                     # histogram of past gaps: x of a 0 s gap, units per s, height scale
NP, MP = np.array([-5.1, 2.7, 0]), np.array([-0.6, 2.7, 0])   # node and monitor
BW, BH = 2.6, 1.0
RP = np.array([4.6, 2.7, 0])                     # suspicion readout
MU, SD = 1.0, 0.33                                # the jittery link's gaps
STY = -3.25

CALM = [k + 0.2 + 0.004 * (k % 3) for k in range(9)]
DELAY = [0.10, 0.70, 0.15, 0.80, 0.06, 0.50, 0.78, 0.09, 0.30, 0.82, 0.12, 0.40]
JIT = [k + d for k, d in enumerate(DELAY)]
LAST = JIT[-1]


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


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def cx(t):
    return CX0 + CXS * t


def cy(s):
    return CY0 + CYS * s


def hx(g):
    return HX0 + HXS * g


def pdf(g):
    return math.exp(-0.5 * ((g - MU) / SD) ** 2) / (SD * math.sqrt(2 * math.pi))


def phi(s):
    p = 0.5 * math.erfc((s - MU) / (SD * math.sqrt(2)))
    return -math.log10(max(p, 1e-300))


def saw(arr, color=BLUE_M):
    pts = [[cx(arr[0]), cy(0), 0]]
    for a, b in zip(arr, arr[1:]):
        pts += [[cx(b), cy(b - a), 0], [cx(b), cy(0), 0]]
    return VMobject(stroke_color=color, stroke_width=3).set_points_as_corners(pts)


def node_box(status, scolor=GREY_B, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to(NP)
    return VGroup(r, T("payments node", 22).move_to(NP + 0.2 * UP), T(status, 17, scolor).move_to(NP + 0.24 * DOWN))


def mon_box(status, scolor=GREY_B, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=2.3, height=BH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to(MP)
    return VGroup(r, T("monitor", 22).move_to(MP + 0.2 * UP), T(status, 17, scolor).move_to(MP + 0.24 * DOWN))


def readout(v, color=None):
    if color is None:
        color = GREEN_M if v < 1 else (GOLD_M if v < 8 else RED_M)
    return M(f"phi {v:4.1f}", 26, color).move_to(RP + 0.17 * DOWN)


def status(s, color=GREY_B):
    return T(s, 21, color).move_to([-2.2, STY, 0])


def threshold(T_, color=GOLD_M):
    ln = DashedLine([cx(0), cy(T_), 0], [cx(14.6), cy(T_), 0], dash_length=0.1, stroke_width=2.5, color=color)
    lab = T(f"timeout {T_:g} s", 18, color).move_to([cx(14.6), cy(T_) + 0.22, 0], aligned_edge=RIGHT)
    return VGroup(ln, lab)


class FailureDetection(Base):
    """dist-02, sections 0, 1 and 3: heartbeats every second; the monitor's silence climbs and resets. A 1.5 s timeout
    is quiet on a calm link and raises false alarms when each heartbeat takes 30 to 830 ms; 3 s stops them but takes
    3 s to notice a crash. Phi accrual fits a bell curve (mean 1 s, deviation 330 ms) to past gaps and turns the
    silence into phi = -log10(chance a healthy node is this quiet): phi 8 at about 2.8 s here, 1.6 s on a calm link.
    Then a gray failure: the pool's 20 connections stick, heartbeats still arrive, phi stays low, payments fail."""

    def construct(self):
        self.title_card("Failure detection", "heartbeats, timeouts, phi and gray failure")

        nd = node_box("database pool: ok")
        mo = mon_box("says: alive", GREEN_M)
        hb = Arrow([NP[0] + BW / 2 + 0.08, NP[1] + 0.2, 0], [MP[0] - 1.15 - 0.08, MP[1] + 0.2, 0], buff=0, stroke_width=3,
                   color=GREY_B, max_tip_length_to_length_ratio=0.12)
        hbl = T("heartbeats", 16, GREY_B).move_to([(NP[0] + BW / 2 + MP[0] - 1.15) / 2, NP[1] + 0.42, 0])

        def beat_dots(n=2, color=TEAL_M):
            return [LaggedStart(*[travel(hb, color, 0.6) for _ in range(n)], lag_ratio=0.7)]

        self.steps("A monitor watches a payments node, which sends a heartbeat every second: a tiny message saying it's alive.", [
            (lambda: [FadeIn(nd), FadeIn(mo)], 0.7),
            "which sends",
            (lambda: [GrowArrow(hb), FadeIn(hbl)], 0.6),
            (lambda: beat_dots(3), 1.8),
        ])

        xax = Line([cx(0), cy(0), 0], [cx(14.8), cy(0), 0], stroke_width=2, color=GREY_B)
        yax = Line([cx(0), cy(0), 0], [cx(0), cy(3.3), 0], stroke_width=2, color=GREY_B)
        yl = VGroup(*[T(f"{s} s", 15, GREY_B).move_to([cx(0) - 0.3, cy(s), 0]) for s in (1, 2, 3)])
        xl = VGroup(*[T(f"{t} s", 15, GREY_B).move_to([cx(t), cy(0) - 0.25, 0]) for t in range(0, 15, 2)])
        ctitle = T("silence since the last heartbeat", 19, GREY_B).move_to([cx(0), cy(3.3) + 0.3, 0], aligned_edge=LEFT)
        calm = saw(CALM, BLUE_M)
        self.steps("The monitor measures silence, the time since the last heartbeat. It climbs, and drops to zero "
                   "when one arrives.", [
            (lambda: [Create(xax), Create(yax), FadeIn(yl), FadeIn(xl), FadeIn(ctitle)], 0.8),
            "It climbs",
            (lambda: [Create(calm, rate_func=linear)], 3.2),
        ])

        th = threshold(1.5)
        st0 = status("calm network: gaps near 1 second, no alarms", GREEN_M)
        self.steps("The simplest detector is a fixed timeout: silence past 1.5 seconds means dead. On a calm network "
                   "the gaps stay near one second, and it never fires.", [
            (lambda: [Create(th[0]), FadeIn(th[1])], 0.8),
            "On a calm",
            (lambda: [FadeIn(st0, shift=0.1 * UP)], 0.6),
            (lambda: [glow(calm, GREEN_M, 1.0)], 0.9),
        ])

        jit = saw(JIT, BLUE_M)
        alarms = [i for i in range(len(JIT) - 1) if JIT[i + 1] - JIT[i] > 1.5]
        dots = VGroup(*[Dot([cx(JIT[i] + 1.5), cy(1.5), 0], radius=0.08, color=RED_M) for i in alarms])
        fal = T("false alarm", 17, RED_M).next_to(dots[0], UP, buff=0.42)
        st1 = status("across regions: 30 to 830 ms a heartbeat", RED_M)
        self.steps("Across regions, each heartbeat takes 30 to 830 milliseconds. The gaps spread out, some pass "
                   "1.5 seconds, and each is a false alarm about a live node.", [
            (lambda: [FadeOut(calm), Transform(st0, st1)], 0.6),
            (lambda: [Create(jit, rate_func=linear)], 2.6),
            "some pass",
            (lambda: [LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.3)], 0.8),
            "and each is",
            (lambda: [FadeIn(fal, shift=0.1 * UP), Transform(mo, mon_box("says: dead!", RED_M, RED_M))], 0.6),
            (lambda: [Transform(mo, mon_box("says: alive", GREEN_M))], 0.4),
        ])

        th3 = threshold(3)
        tk = ValueTracker(0.001)

        def climb():
            s = tk.get_value()
            return Line([cx(LAST), cy(0), 0], [cx(LAST + s), cy(s), 0], stroke_width=3.5, color=RED_M)

        cl = always_redraw(climb)
        crash = T("crash", 17, RED_M).move_to([cx(LAST) + 0.5, cy(0) + 0.22, 0], aligned_edge=LEFT)
        late = T("noticed after 3 s", 17, RED_M).move_to([cx(LAST + 3.0) - 0.3, cy(3.0) - 0.32, 0], aligned_edge=RIGHT)
        self.steps("Raise the timeout to 3 seconds and the alarms stop. But a real crash now takes 3 seconds to notice, "
                   "twice what the calm network needs.", [
            (lambda: [FadeOut(dots), FadeOut(fal), FadeOut(st0), Transform(th, th3)], 0.8),
            "But a real crash",
            (lambda: [FadeIn(crash), Transform(nd, node_box("crashed", RED_M, RED_M))], 0.5),
            (lambda: [FadeIn(cl)], 0.05),
            (lambda: [tk.animate(rate_func=linear).set_value(3.0)], 2.0),
            (lambda: [FadeIn(late), Transform(mo, mon_box("says: dead", RED_M, RED_M))], 0.6),
        ])
        # ---- phi accrual -------------------------------------------------------------------------------------------
        bins = []
        for i in range(18):
            g0, g1 = 0.2 * i, 0.2 * (i + 1)
            # the jittery link's gaps: triangular from 0.2 to 1.8 s (1 s plus the difference of two 30 to 830 ms delays)
            mid = (g0 + g1) / 2
            dens = max(0.0, 0.8 - abs(mid - 1.0)) / 0.64
            if dens > 0:
                b = Rectangle(width=0.2 * HXS - 0.03, height=dens * HSC, stroke_width=1.5, stroke_color=BLUE_M)
                b.set_fill(BLUE_M, 0.25).move_to([hx(mid), CY0 + dens * HSC / 2, 0])
                bins.append(b)
        bins = VGroup(*bins)
        hax = Line([hx(0), CY0, 0], [hx(3.6), CY0, 0], stroke_width=2, color=GREY_B)
        hxl = VGroup(*[T(f"{g} s", 15, GREY_B).move_to([hx(g), CY0 - 0.25, 0]) for g in (0, 1, 2, 3)])
        htitle = T("the last 1,000 gaps", 19, GREY_B).move_to([hx(1.8), 0.75, 0])
        curve = VMobject(stroke_color=GOLD_M, stroke_width=3).set_points_smoothly(
            [[hx(g), CY0 + pdf(g) * HSC, 0] for g in np.linspace(0, 3.6, 73)])
        rd_box = RoundedRectangle(corner_radius=0.14, width=3.0, height=BH, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        rd_box.move_to(RP)
        rd_t = T("suspicion", 17, GREY_B).move_to(RP + 0.24 * UP)
        self.steps("The phi accrual detector lets history choose. It fits a bell curve to the last thousand gaps, "
                   "and asks how likely a healthy node is to stay this quiet.", [
            (lambda: [FadeOut(th), FadeOut(late), FadeOut(crash), FadeOut(cl), Transform(nd, node_box("database pool: ok")),
                      Transform(mo, mon_box("says: alive", GREEN_M)), FadeIn(hax), FadeIn(hxl), FadeIn(htitle)], 0.8),
            (lambda: [LaggedStart(*[GrowFromEdge(b, DOWN) for b in bins], lag_ratio=0.08)], 1.2),
            "fits a bell curve",
            (lambda: [Create(curve)], 1.0),
            "and asks",
            (lambda: [FadeIn(rd_box), FadeIn(rd_t)], 0.5),
        ])
        self.remove(cl)
        tk.set_value(0.001)

        def tail():
            s = max(tk.get_value(), 0.0)
            gs = np.linspace(min(s, 3.6), 3.6, 40)
            pts = [[hx(gs[0]), CY0, 0]] + [[hx(g), CY0 + pdf(g) * HSC, 0] for g in gs] + [[hx(3.6), CY0, 0]]
            return Polygon(*pts, stroke_width=0).set_fill(RED_M, 0.55)

        def marker():
            s = tk.get_value()
            x = hx(min(s, 3.6))
            return Line([x, CY0, 0], [x, CY0 + 2.3, 0], stroke_width=2.5, color=YELLOW_M)

        def rv():
            return readout(phi(tk.get_value()))

        tl, mk, ro = always_redraw(tail), always_redraw(marker), always_redraw(rv)
        cl2 = always_redraw(climb)
        lo, hi = 1.0, 4.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if phi(mid) < 8.0 else (lo, mid)
        p8 = hi
        self.steps("Phi is that chance on a log scale: phi 8 means one in a hundred million. On this link it passes 8 "
                   "after about 2.8 seconds.", [
            (lambda: [FadeIn(tl), FadeIn(mk), FadeIn(ro), FadeIn(cl2), FadeIn(crash), Transform(nd, node_box("crashed", RED_M, RED_M))], 0.6),
            (lambda: [tk.animate(rate_func=linear).set_value(1.6)], 2.0),
            "On this link",
            (lambda: [tk.animate(rate_func=linear).set_value(p8)], 1.8),
            (lambda: [Transform(mo, mon_box("suspects: phi 8", RED_M, RED_M)), glow(rd_box, RED_M, 1.04)], 0.6),
        ])

        p8l = T("phi 8 at 2.8 s", 17, RED_M).move_to([cx(LAST + p8) - 0.3, cy(p8) - 0.32, 0], aligned_edge=RIGHT)
        st2 = status("calm network: phi 8 after about 1.6 s", GREEN_M)
        self.steps("On the calm network it passes 8 after about 1.6. Each link gets its own timeout, from its own history.", [
            (lambda: [FadeIn(p8l)], 0.5),
            "On the calm",
            (lambda: [FadeIn(st2, shift=0.1 * UP)], 0.6),
            "Each link",
            (lambda: [glow(bins[len(bins) // 2], GOLD_M, 1.05), Indicate(curve, color=YELLOW_M, scale_factor=1.03)], 1.0),
        ])
        for m in (tl, mk, ro, cl2):
            m.clear_updaters()

        # ---- gray failure ------------------------------------------------------------------------------------------
        reqs = VGroup(*[Dot(radius=0.13, color=GREEN_M) for _ in range(12)]).arrange_in_grid(3, 4, buff=0.42)
        reqs.move_to([hx(1.8), -0.95, 0])
        rtitle = T("payments from checkout", 19, GREY_B).move_to([hx(1.8), 0.75, 0])
        rlab = T("timed out: 0 of 12", 18, GREY_B).move_to([hx(1.8), -2.35, 0])
        rlab2 = T("timed out: 12 of 12", 18, RED_M).move_to([hx(1.8), -2.35, 0])
        self.steps("Every detector so far asks whether the node answers. Now its database pool jams: all 20 connections "
                   "are stuck, and every payment times out.", [
            (lambda: [FadeOut(VGroup(bins, hax, hxl, htitle, curve, tl, mk, cl2, crash, p8l, st2)),
                      Transform(nd, node_box("database pool: ok")), Transform(mo, mon_box("says: alive", GREEN_M)),
                      Transform(ro, readout(0.2))], 0.8),
            (lambda: [FadeIn(rtitle), FadeIn(reqs), FadeIn(rlab)], 0.6),
            "Now its database",
            (lambda: [Transform(nd, node_box("pool: 20 of 20 stuck", RED_M, GOLD_M))], 0.7),
            "and every payment",
            (lambda: [LaggedStart(*[d.animate.set_color(RED_M) for d in reqs], lag_ratio=0.12), Transform(rlab, rlab2)], 1.4),
        ])

        st3 = status("monitor: healthy. users: every payment fails.", RED_M)
        self.steps("The heartbeats come from a thread that never touches the database, so phi stays low. "
                   "The monitor sees a healthy node, and users see errors. That's a gray failure.", [
            (lambda: beat_dots(2, TEAL_M), 1.4),
            "so phi stays low",
            (lambda: [glow(rd_box, GREEN_M, 1.04)], 0.8),
            "The monitor sees",
            (lambda: [glow(mo[0], GREEN_M), FadeIn(st3, shift=0.1 * UP)], 0.8),
            "and users see",
            (lambda: [*[Indicate(d, color=RED_M, scale_factor=1.3) for d in reqs]], 0.8),
        ])

        syn = Arrow([MP[0] - 1.15 - 0.08, MP[1] - 0.25, 0], [NP[0] + BW / 2 + 0.08, NP[1] - 0.25, 0], buff=0, stroke_width=3,
                    color=GOLD_M, max_tip_length_to_length_ratio=0.12)
        synl = T("synthetic payment", 16, GOLD_M).move_to([(NP[0] + BW / 2 + MP[0] - 1.15) / 2, NP[1] - 0.47, 0])
        self.steps("So test health with real work: a synthetic payment through the whole path, or a proxy that stops "
                   "routing to an instance whose requests fail.", [
            (lambda: [GrowArrow(syn), FadeIn(synl)], 0.6),
            (lambda: [travel(syn, GOLD_M, 0.8)], 0.8),
            (lambda: [Transform(mo, mon_box("says: unhealthy", RED_M, RED_M)), Transform(st3, status("the synthetic payment failed: route around it", GOLD_M))], 0.7),
        ])

        self.steps("A detector can only suspect. Let history set the timeout, and let real requests decide what healthy means.", [
            (lambda: [glow(mo[0], YELLOW_M)], 0.9),
            "Let history",
            (lambda: [glow(rd_box, YELLOW_M, 1.04)], 0.9),
            "let real requests",
            (lambda: [glow(syn, GOLD_M, 1.0), *[Indicate(d, color=RED_M, scale_factor=1.2) for d in reqs]], 1.0),
        ])
        self.wait(0.6)
