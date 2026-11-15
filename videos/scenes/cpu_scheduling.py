from sfz import *

SAY.insert(0, (r"\bcpu\.max\b", "C P U dot max"))

ROWY = {"api": 2.35, "batch": 1.05}
LBX, LBW = -4.6, 3.0
BX0, VS = -2.75, 0.18                  # bars: start x, units per virtual ms
PTR_X = -6.45
COLR = {"api": BLUE_M, "batch": GOLD_M}
SHY, SHX0, SHW = -0.55, -4.0, 8.0     # share bar
NOTE_Y = -3.2
# quota timeline
QX0, QMS = -4.4, 0.05                 # x of 0 ms, units per ms
LANES = [1.15, 0.45, -0.25, -0.95]
LH = 0.46


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=sw)
    return r.set_fill(fill if fill is not None else fillc(color), 1).move_to(c)


def label_box(k, nice):
    name = {"api": "API thread", "batch": "batch thread"}[k]
    y = ROWY[k]
    r = rrect(LBW, 1.0, [LBX, y, 0], COLR[k], 2.5)
    return VGroup(r, T(name, 26).move_to([LBX, y + 0.18, 0]), T(f"nice {nice}", 20, GREY_B).move_to([LBX, y - 0.24, 0]))


def bar(k, v):
    w = max(v * VS, 0.02)
    r = Rectangle(width=w, height=0.6, stroke_width=0).set_fill(COLR[k], 0.85)
    return r.move_to([BX0 + w / 2, ROWY[k], 0])


def val(k, v):
    s = f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"
    m = T(s, 24, GREY_A)
    return m.move_to([BX0 + max(v * VS, 0.02) + 0.18 + m.width / 2, ROWY[k], 0])


def pointer(k):
    return Triangle(color=GREEN_M, fill_opacity=1, stroke_width=0).rotate(-PI / 2).scale(0.17).move_to([PTR_X, ROWY[k], 0])


def share(api_frac, l1, l2):
    wa = SHW * api_frac
    a = Rectangle(width=wa, height=0.5, stroke_width=0).set_fill(BLUE_M, 0.85).move_to([SHX0 + wa / 2, SHY, 0])
    b = Rectangle(width=SHW - wa, height=0.5, stroke_width=0).set_fill(GOLD_M, 0.85).move_to([SHX0 + wa + (SHW - wa) / 2, SHY, 0])
    ta = T(l1, 20, BLUE_M)
    ta.move_to([SHX0 + ta.width / 2, SHY - 0.5, 0])
    tb = T(l2, 20, GOLD_M)
    tb.move_to([SHX0 + SHW - tb.width / 2, SHY - 0.5, 0])
    return VGroup(a, b, ta, tb)


def note(s, color=GREY_B, y=NOTE_Y):
    return chip(s, color, 21).move_to([0, y, 0])


def qx(ms):
    return QX0 + ms * QMS


def run_block(lane, t0, t1, color=TEAL_M):
    w = (t1 - t0) * QMS
    return Rectangle(width=w, height=LH, stroke_width=0).set_fill(color, 0.9).move_to([qx(t0) + w / 2, LANES[lane], 0])


class CpuScheduling(Base):
    """os-04, section 1 (with section 3's quota): two busy threads on one CPU; the one with the smallest virtual runtime
    runs next, 3 ms slices, so they split it (lab: 4.99 s each of 10). The batch at nice 10: weight 110 against 1024, its
    clock runs 9.3 times faster, a slice adds 28; the API runs nine slices in a row; 90% against 10% (lab: 9.01 s, 0.98 s).
    Then --cpus=0.5: cpu.max 50000 100000; four busy threads spend 50 ms in 12.5 ms and stall about 87 ms each period
    (lab: 40 of 41 periods throttled, longest stall 94 ms)."""

    def construct(self):
        self.title_card("CPU scheduling: fair shares and quotas", "who runs next, and when a container must stop")

        lb = {"api": label_box("api", 0), "batch": label_box("batch", 0)}
        v = {"api": 0.0, "batch": 0.0}
        bars = {k: bar(k, 0) for k in v}
        vals = {k: val(k, 0) for k in v}
        ax = T("virtual runtime, in ms", 22, GREY_B)
        ax.move_to([BX0 + ax.width / 2, 3.15, 0])
        base = Line([BX0, 0.55, 0], [BX0, 2.85, 0], stroke_width=2, color=GREY_D)
        self.steps("Two busy threads share one CPU: the API that approves card payments, and the nightly settlement batch. "
                   "Which one runs?", [
            (lambda: [FadeIn(lb["api"], shift=0.1 * RIGHT)], 0.6),
            "and the nightly",
            (lambda: [FadeIn(lb["batch"], shift=0.1 * RIGHT)], 0.6),
            "Which one runs",
            (lambda: [glow(lb["api"][0], BLUE_M, 1.03), glow(lb["batch"][0], GOLD_M, 1.03)], 0.9),
        ])

        ptr = pointer("api")
        cfs = T("the rule at the heart of CFS; today's EEVDF keeps it and adds deadlines", 19, GREY_C)
        cfs.move_to([0, NOTE_Y, 0])
        self.steps("Linux tracks each thread's virtual runtime, the CPU time it has had so far, "
                   "and runs whichever has had the least.", [
            (lambda: [FadeIn(ax), Create(base), FadeIn(bars["api"]), FadeIn(bars["batch"]), FadeIn(vals["api"]),
                      FadeIn(vals["batch"])], 0.8),
            "and runs whichever",
            (lambda: [FadeIn(ptr, shift=0.2 * RIGHT), FadeIn(cfs)], 0.6),
        ])

        def run(k, dv, rt=0.45):
            def f():
                v[k] += dv
                out = [Transform(bars[k], bar(k, v[k])), Transform(vals[k], val(k, v[k]))]
                return out
            return (f, rt)

        def to(k, rt=0.25):
            return (lambda: [ptr.animate.move_to([PTR_X, ROWY[k], 0])], rt)

        self.steps("The API runs a 3 millisecond slice, so now the batch is behind, and it goes next.", [
            run("api", 3, 0.7),
            "so now the batch",
            to("batch"), run("batch", 3, 0.7),
            to("api"), run("api", 3, 0.4), to("batch"), run("batch", 3, 0.4),
            to("api"), run("api", 3, 0.4), to("batch"), run("batch", 3, 0.4),
        ])

        sh = share(0.5, "API: 4.99 s", "batch: 4.99 s")
        stitle = T("share of the CPU, lab run of 10 s", 20, GREY_B).move_to([0, SHY + 0.5, 0])
        self.steps("They take turns and split it evenly: in the lab, 4.99 seconds each, out of 10.", [
            (lambda: [FadeIn(stitle), FadeIn(sh[0]), FadeIn(sh[1])], 0.8),
            "in the lab",
            (lambda: [FadeIn(sh[2]), FadeIn(sh[3])], 0.6),
        ])

        self.steps("But the batch matters less, so give it nice 10. "
                   "Nice runs from minus 20 to 19, and higher is nicer to the others.", [
            (lambda: [glow(lb["batch"][0], GOLD_M, 1.03)], 0.8),
            (lambda: [Transform(lb["batch"][2], T("nice 10", 20, GOLD_M).move_to(lb["batch"][2]))], 0.6),
        ])

        formula = note("virtual runtime grows by real time × 1024 / weight", GREY_A, -1.95)
        self.steps("Each nice value has a weight: 1024 for nice 0, 110 for nice 10. "
                   "Virtual runtime grows by real time, times 1024 over the weight.", [
            (lambda: [FadeOut(sh), FadeOut(stitle)], 0.5),
            "1024 for nice 0",
            (lambda: [Transform(lb["api"][2], T("nice 0, weight 1024", 20, GREY_B).move_to(lb["api"][2]))], 0.6),
            "110 for nice 10",
            (lambda: [Transform(lb["batch"][2], T("nice 10, weight 110", 20, GOLD_M).move_to(lb["batch"][2]))], 0.6),
            "Virtual runtime grows",
            (lambda: [FadeIn(formula, shift=0.1 * UP)], 0.7),
        ])

        self.steps("So the batch's clock runs 9.3 times faster: one 3 millisecond slice adds 28.", [
            run("api", 3, 0.5),
            to("batch"),
            "one 3",
            run("batch", 27.9, 1.4),
        ])

        def api_burst():
            out = [to("api")]
            for _ in range(9):
                out.append(run("api", 3, 0.3))
            return out

        self.steps("The API is now far behind, so it runs nine slices in a row before the batch is lowest again.", [
            *api_burst(),
            (lambda: [ptr.animate.move_to([PTR_X, ROWY["batch"], 0])], 0.3),
        ])

        sh2 = share(0.903, "API: 90%, lab 9.01 s", "batch: 10%, lab 0.98 s")
        self.steps("That's 90 percent against 10: less CPU for the batch, never none. "
                   "The lab box measured 9.01 seconds against 0.98.", [
            (lambda: [FadeOut(formula), FadeIn(stitle), FadeIn(sh2[0]), FadeIn(sh2[1])], 0.8),
            "The lab box",
            (lambda: [FadeIn(sh2[2]), FadeIn(sh2[3])], 0.6),
        ])

        # ---- a CPU quota ---------------------------------------------------------------------------------------------
        top = VGroup(*lb.values(), *bars.values(), *vals.values(), ax, base, ptr, sh2, stitle, cfs)
        cmax = M("cpu.max: 50000 100000", 24, TEAL_M).move_to([-2.6, 3.3, 0])
        meaning = T("50 ms of CPU time in every 100 ms period", 22, GREY_A).move_to([2.9, 3.3, 0])
        lanes = VGroup(*[Line([qx(0), y - LH / 2 - 0.02, 0], [qx(200), y - LH / 2 - 0.02, 0], stroke_width=1.5, color=GREY_D)
                         for y in LANES])
        llab = VGroup(*[T(f"CPU {i + 1}", 20, GREY_B).move_to([qx(0) - 0.75, y, 0]) for i, y in enumerate(LANES)])
        per = VGroup(*[DashedLine([qx(m), LANES[0] + 0.4, 0], [qx(m), LANES[-1] - 0.4, 0], dash_length=0.08, stroke_width=2,
                                  color=GREY_B) for m in (0, 100, 200)])
        plab = VGroup(*[T(s, 18, GREY_B).move_to([qx(m), LANES[-1] - 0.65, 0]) for m, s in ((0, "0"), (100, "100 ms"), (200, "200 ms"))])
        bud_lab = T("budget left", 20, GREY_B).move_to([qx(0) - 0.95, 2.5, 0])
        bud_bg = Rectangle(width=50 * QMS * 2, height=0.3, stroke_color=TEAL_M, stroke_width=1.5).set_fill(BLACK, 1)
        bud_bg.move_to([qx(0) + bud_bg.width / 2, 2.5, 0])

        def budget(ms, color=TEAL_M):
            w = max(ms * QMS * 2, 0.01)
            return Rectangle(width=w, height=0.3, stroke_width=0).set_fill(color, 0.9).move_to([qx(0) + w / 2, 2.5, 0])

        bud = budget(50)
        bud_v = T("50 ms", 20, TEAL_M).next_to(bud_bg, RIGHT, buff=0.2)
        self.steps("A container needs a ceiling instead. Half a CPU becomes a budget in cpu.max: "
                   "50 milliseconds of CPU time in every 100.", [
            (lambda: [FadeOut(top)], 0.7),
            "Half a CPU",
            (lambda: [FadeIn(cmax)], 0.6),
            "50 milliseconds",
            (lambda: [FadeIn(meaning), FadeIn(bud_lab), FadeIn(bud_bg), FadeIn(bud), FadeIn(bud_v)], 0.7),
            "every 100",
            (lambda: [FadeIn(lanes), FadeIn(llab), Create(per), FadeIn(plab)], 0.8),
        ])

        blocks1 = [run_block(i, 0, 12.5) for i in range(4)]
        self.steps("The budget is CPU time. Four busy threads, on four CPUs, spend it all in 12 and a half milliseconds.", [
            "Four busy threads",
            (lambda: [*[GrowFromEdge(b, LEFT) for b in blocks1], Transform(bud, budget(0)),
                      Transform(bud_v, T("0 ms", 20, RED_M).next_to(bud_bg, RIGHT, buff=0.2))], 1.6),
        ])

        def throttle(t0, t1):
            w = (t1 - t0) * QMS
            return Rectangle(width=w, height=LANES[0] - LANES[-1] + LH + 0.1, stroke_width=0).set_fill(RED_M, 0.22).move_to(
                [qx(t0) + w / 2, (LANES[0] + LANES[-1]) / 2, 0])

        th1 = throttle(12.5, 100)
        thl = T("throttled: about 87 ms", 22, RED_M).move_to([qx(56), (LANES[1] + LANES[2]) / 2, 0])
        self.steps("Then the kernel stops every thread in the container until the next period: "
                   "about 87 milliseconds of nothing. That's throttling.", [
            (lambda: [GrowFromEdge(th1, LEFT)], 1.4),
            "about 87",
            (lambda: [FadeIn(thl)], 0.6),
        ])

        req = Arrow([qx(30), 1.95, 0], [qx(30), LANES[0] + LH / 2 + 0.05, 0], buff=0, stroke_width=3, color=WHITE,
                    max_tip_length_to_length_ratio=0.3)
        rlab = T("a request arrives", 18, WHITE).move_to([qx(30), 2.05, 0]).shift(1.1 * RIGHT)
        blocks2 = [run_block(i, 100, 112.5) for i in range(4)]
        th2 = throttle(112.5, 200)
        lab = note("lab: throttled in 40 of 41 periods, longest stall 94 ms", RED_M, -2.55)
        self.steps("A request arriving in the gap just waits. In the lab, 40 of 41 periods were throttled, "
                   "and the longest stall was 94 milliseconds.", [
            (lambda: [GrowArrow(req), FadeIn(rlab)], 0.6),
            (lambda: [Transform(bud, budget(50)), Transform(bud_v, T("50 ms", 20, TEAL_M).next_to(bud_bg, RIGHT, buff=0.2))], 0.4),
            (lambda: [*[GrowFromEdge(b, LEFT) for b in blocks2], Transform(bud, budget(0)),
                      Transform(bud_v, T("0 ms", 20, RED_M).next_to(bud_bg, RIGHT, buff=0.2))], 0.6),
            (lambda: [GrowFromEdge(th2, LEFT)], 0.9),
            "In the lab",
            (lambda: [FadeIn(lab, shift=0.1 * UP)], 0.6),
        ])

        self.steps("The thread with the least weighted runtime runs next, "
                   "and a container that spends its quota early waits for the next period.", [
            (lambda: [*[Indicate(b, color=WHITE, scale_factor=1.15) for b in blocks1 + blocks2]], 1.0),
            "and a container",
            (lambda: [Indicate(th1, color=RED_M, scale_factor=1.02), Indicate(th2, color=RED_M, scale_factor=1.02)], 1.0),
        ])
        self.wait(0.6)
