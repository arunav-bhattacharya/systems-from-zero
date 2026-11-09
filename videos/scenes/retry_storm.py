from sfz import *

# "Goodput" at the start of a sentence came out as "output".
SAY.insert(0, (r"\b[Gg]oodput\b", lambda m: m.group(0)[0] + "ood put"))

# the pipeline: clients, a queue, the service
PY = 1.85
CX, QX, SX = -5.3, -0.85, 3.55
CWD, QW, SWD, BH, QH = 2.2, 3.6, 2.5, 1.15, 0.75
# the chart: 0 to 40 s across, 0 to 3,200 a second up
X0, X1, Y0, YH, TMAX = -5.0, 4.4, -3.0, 2.9, 40.0

# the lab's simulation (found-03, RetryStormDemo): capacity, attempts offered, goodput and queue, by time
CAP = [(0, 1000), (10, 1000), (10, 400), (15, 400), (15, 1000), (40, 1000)]
RUNS = {
    "retry": dict(att=[(0, 800), (10.3, 800), (11, 3200), (40, 3200)],
                  good=[(0, 800), (10, 800), (10, 400), (10.4, 400), (11, 0), (40, 0)],
                  que=[(0, 0), (10, 0), (10.2, 80), (11, 4157), (15, 14757), (40, 69757)]),
    "budget": dict(att=[(0, 800), (10.3, 800), (11, 880), (33.5, 880), (34, 800), (40, 800)],
                   good=[(0, 800), (10, 800), (10, 400), (10.4, 400), (11, 0), (33.5, 0), (34, 800), (40, 800)],
                   que=[(0, 0), (10, 0), (10.2, 80), (11, 937), (15, 2257), (30, 457), (33.8, 0), (40, 0)]),
}


def X(t):
    return X0 + (X1 - X0) * t / TMAX


def Y(v):
    return Y0 + YH * v / 3200


def at(pts, t):
    """Value of a piecewise-linear series at t (the later value where it jumps)."""
    v = pts[0][1] if t <= pts[0][0] else pts[-1][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            v = v1 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return v


def upto(pts, t):
    out = [(0, pts[0][1])] + [(a, b) for a, b in pts if 0 < a <= t] + [(t, at(pts, t))]
    return [[X(a), Y(b), 0] for a, b in out]


def num(v):
    return f"{int(round(v)):,}"


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fillc(color):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


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


class RetryStorm(Base):
    """found-03, section 3: a service that finishes 1,000 a second gets 800. A dependency slows it to 400 a second
    for five seconds; clients time out after 200 ms and retry up to 4 attempts, so 3,200 attempts a second arrive
    and goodput stays at zero after capacity returns (a metastable failure). A 10% retry budget caps the load at
    880 a second, so the backlog drains and the service is back at 34 s."""

    def construct(self):
        self.title_card("Retry storms", "a five-second slowdown that never ends")

        self.mode = "retry"
        tr = {"retry": ValueTracker(0), "budget": ValueTracker(10)}

        def now():
            return tr[self.mode].get_value()

        def run():
            return RUNS[self.mode]

        # ---- the pipeline ---------------------------------------------------------------------------------------
        cl_r = RoundedRectangle(corner_radius=0.14, width=CWD, height=BH, stroke_color=WHITE, stroke_width=3)
        cl_r.set_fill(BLACK, 1).move_to([CX, PY, 0])
        clients = VGroup(cl_r, T("clients", 24).move_to([CX, PY + 0.24, 0]),
                         T("800 new a second", 18, GREY_B).move_to([CX, PY - 0.2, 0]))
        a_in = Arrow([CX + CWD / 2 + 0.05, PY, 0], [QX - QW / 2 - 0.05, PY, 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.15)
        q_r = Rectangle(width=QW, height=QH, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1).move_to([QX, PY, 0])
        a_out = Arrow([QX + QW / 2 + 0.05, PY, 0], [SX - SWD / 2 - 0.05, PY, 0], buff=0, stroke_width=3, color=GREY_B,
                      max_tip_length_to_length_ratio=0.15)
        sv_r = RoundedRectangle(corner_radius=0.14, width=SWD, height=BH, stroke_color=WHITE, stroke_width=3)
        sv_r.set_fill(BLACK, 1).move_to([SX, PY, 0])

        def sv_color(m):
            bad = at(CAP, now()) < 1000
            m.set_stroke(RED_M if bad else WHITE).set_fill(fillc(RED_M) if bad else BLACK, 1)

        sv_r.add_updater(sv_color)
        sv_t = T("payment service", 22).move_to([SX, PY + 0.24, 0])
        sv_sub = always_redraw(lambda: T(f"capacity {num(at(CAP, now()))}/s", 18,
                                         RED_M if at(CAP, now()) < 1000 else GREY_B).move_to([SX, PY - 0.2, 0]))
        a_lab = always_redraw(lambda: T(f"{num(at(run()['att'], now()))}/s", 18,
                                        RED_M if at(run()['att'], now()) > 1000 else GREY_B).next_to(a_in, UP, buff=0.12))

        def qfill():
            q = at(run()["que"], now())
            f = min(1.0, (q / 25000) ** 0.5)
            w = max(0.001, f * (QW - 0.12))
            return Rectangle(width=w, height=QH - 0.12, stroke_width=0).set_fill(RED_M, 0.45).move_to(
                [QX - QW / 2 + 0.06 + w / 2, PY, 0])

        q_fill = always_redraw(qfill)
        q_lab = always_redraw(lambda: T(f"queue: {num(at(run()['que'], now()))}", 18, GREY_B).move_to([QX, PY - 0.62, 0]))
        g_lab = always_redraw(lambda: T(f"goodput: {num(at(run()['good'], now()))}/s", 18,
                                        GREEN_M if at(run()['good'], now()) > 0 else RED_M).move_to([SX, PY - 0.86, 0]))
        clock = always_redraw(lambda: left_at(T(f"t = {int(now() + 1e-6)} s", 24, GREY_A), 5.15, 3.3))

        # the retry loop: from the queue back to the clients
        LY = 2.95
        loop_pts = [[QX, PY + QH / 2 + 0.05, 0], [QX, LY, 0], [CX, LY, 0], [CX, PY + BH / 2 + 0.06, 0]]
        loop_l = VGroup(Line(loop_pts[0], loop_pts[1]), Line(loop_pts[1], loop_pts[2]),
                        Arrow(loop_pts[2], loop_pts[3], buff=0, max_tip_length_to_length_ratio=0.5,
                              max_stroke_width_to_length_ratio=10)).set_stroke(GREY_C, 3).set_color(GREY_C)
        loop_path = VMobject().set_points_as_corners(loop_pts)
        loop_t = T("no answer in 200 ms: try again, up to 4 attempts", 18, GREY_B).move_to([(QX + CX) / 2, LY + 0.3, 0])

        def loop_dots(n, color=RED_M, rt=1.0):
            return LaggedStart(*[travel(loop_path, color, rt) for _ in range(n)], lag_ratio=0.35)

        # ---- the chart ------------------------------------------------------------------------------------------
        axes = VGroup(Line([X0, Y0, 0], [X1 + 0.15, Y0, 0]), Line([X0, Y0, 0], [X0, Y0 + YH + 0.1, 0])).set_stroke(GREY_B, 2)
        xt = VGroup(*[VGroup(Line([X(t), Y0 - 0.07, 0], [X(t), Y0 + 0.07, 0], stroke_width=2, color=GREY_B),
                             T(f"{t} s" if t else "0", 16, GREY_B).move_to([X(t), Y0 - 0.3, 0])) for t in (0, 10, 15, 20, 30, 40)])
        yt = VGroup(*[T(s, 16, GREY_B).move_to([X0 - 0.42, Y(v), 0]) for s, v in (("1,000", 1000), ("3,200", 3200))])
        shade = Rectangle(width=X(15) - X(10), height=YH, stroke_width=0).set_fill(RED_M, 0.13)
        shade.move_to([(X(10) + X(15)) / 2, Y0 + YH / 2, 0])
        shade_t = T("slowdown", 15, RED_M).move_to([X(13.35), -1.3, 0])

        def entry(color, s):
            return VGroup(Line(ORIGIN, 0.45 * RIGHT, stroke_width=4, color=color), T(s, 18, GREY_B)).arrange(RIGHT, buff=0.14)

        legend = VGroup(entry(RED_M, "attempts sent"), entry(GREEN_M, "goodput (useful answers)"),
                        entry(GREY_B, "capacity")).arrange(RIGHT, buff=0.55).move_to([-0.3, 0.35, 0])

        def curve(pts, key, color, w, mode):
            def make():
                p = upto(pts if key is None else RUNS[mode][key], tr[mode].get_value())
                return VMobject(stroke_color=color, stroke_width=w).set_points_as_corners(p)
            return always_redraw(make)

        cap_c = curve(CAP, None, GREY_B, 2.5, "retry")
        good_c = curve(None, "good", GREEN_M, 6, "retry")
        att_c = curve(None, "att", RED_M, 3.5, "retry")

        # ---- the story ------------------------------------------------------------------------------------------
        flow_in = lambda n, c=GREY_A: LaggedStart(*[travel(a_in, c, 0.5) for _ in range(n)], lag_ratio=0.4)
        flow_out = lambda n, c=GREEN_M: LaggedStart(*[travel(a_out, c, 0.5) for _ in range(n)], lag_ratio=0.4)

        self.steps("Take a payment service that can finish 1,000 requests a second. "
                   "Its clients send 800, so it's 80 percent busy and answers in about a millisecond.", [
            (lambda: [FadeIn(sv_r), FadeIn(sv_t), FadeIn(sv_sub)], 0.8),
            "Its clients",
            (lambda: [FadeIn(clients), GrowArrow(a_in), FadeIn(a_lab), FadeIn(q_r), FadeIn(q_fill), FadeIn(q_lab),
                      GrowArrow(a_out)], 0.9),
            "so it's 80",
            (lambda: [flow_in(4), flow_out(4)], 1.4),
            (lambda: [FadeIn(g_lab)], 0.5),
        ])

        self.steps("Each client waits 200 milliseconds for an answer. If none comes, it tries again at once, "
                   "up to four attempts in all.", [
            (lambda: [glow(cl_r, GREY_A)], 0.8),
            "If none comes",
            (lambda: [Create(loop_l), FadeIn(loop_t)], 1.2),
        ])

        self.steps("For ten seconds, all 800 attempts a second get a useful answer. "
                   "The rate of useful answers is called goodput.", [
            (lambda: [Create(axes), FadeIn(xt), FadeIn(yt), FadeIn(legend), FadeIn(clock)], 0.9),
            (lambda: [FadeIn(cap_c), FadeIn(good_c), FadeIn(att_c)], 0.1),
            (lambda: [tr["retry"].animate(rate_func=linear).set_value(10), flow_in(5), flow_out(5)], 3.0),
            "The rate",
            (lambda: [glow(legend[1][0], GREEN_M, 1.2), Indicate(g_lab, color=GREEN_M)], 1.0),
        ])

        self.steps("At ten seconds, a service it depends on slows down. "
                   "For five seconds, it can finish only 400 a second.", [
            (lambda: [FadeIn(shade), FadeIn(shade_t), tr["retry"].animate(rate_func=linear).set_value(10.05)], 0.8),
            "For five seconds",
            (lambda: [glow(sv_r, RED_M)], 0.9),
        ])

        self.steps("Now 800 arrive each second and 400 leave, so a queue builds. "
                   "Soon a new request waits longer than its client will, and the client sends it again.", [
            (lambda: [tr["retry"].animate(rate_func=linear).set_value(10.2), flow_in(3), flow_out(1, GREY_A)], 1.6),
            "Soon a new",
            (lambda: [glow(q_r, RED_M, 1.03)], 0.8),
            "and the client",
            (lambda: [loop_l.animate.set_color(RED_M), loop_t.animate.set_color(RED_M),
                      tr["retry"].animate(rate_func=linear).set_value(10.4), loop_dots(3)], 1.6),
        ])

        self.steps("Every attempt now times out, so each request is sent four times: 3,200 attempts a second.", [
            (lambda: [tr["retry"].animate(rate_func=linear).set_value(11), loop_dots(6), flow_in(6, RED_M)], 2.4),
            "3,200",
            (lambda: [Indicate(a_lab, color=RED_M)], 0.8),
        ])

        self.steps("The service answers in order, and each answer goes to a client that gave up long ago. "
                   "Goodput falls to zero.", [
            (lambda: [flow_out(4, RED_M)], 1.6),
            "Goodput falls",
            (lambda: [Indicate(g_lab, color=RED_M), glow(legend[1][0], RED_M, 1.2)], 1.0),
        ])

        self.steps("At fifteen seconds the slow service recovers, and capacity is back to 1,000. It makes no difference.", [
            (lambda: [tr["retry"].animate(rate_func=linear).set_value(15), loop_dots(5)], 2.0),
            "It makes",
            (lambda: [Indicate(g_lab, color=RED_M)], 0.8),
        ])

        self.steps("3,200 attempts a second is more than three times what it can finish. "
                   "The queue keeps growing, and goodput stays at zero.", [
            (lambda: [tr["retry"].animate(rate_func=linear).set_value(40), loop_dots(9), flow_in(9, RED_M)], 4.0),
        ])

        meta = chip("metastable failure: the retries keep it down", RED_M, 18).move_to([X(27), -1.15, 0])
        self.steps("The trigger is gone, but the retries keep the service down. "
                   "That's a metastable failure: its own behaviour holds it there.", [
            (lambda: [glow(shade_t, RED_M, 1.1), loop_dots(4)], 1.4),
            "That's a",
            (lambda: [FadeIn(meta, shift=0.15 * UP)], 0.8),
            "own behaviour",
            (lambda: [loop_l.animate(rate_func=there_and_back).set_stroke(width=7)], 1.0),
        ])

        # the rerun with a budget: old lines dimmed, new ones drawn from t = 10
        old = VGroup(cap_c, good_c, att_c)
        for m in old:
            m.clear_updaters()
        nb = T("no budget", 16, GREY_C).move_to([X(36), Y(3200) - 0.25, 0])
        cap_b = curve(CAP, None, GREY_B, 2.5, "budget")
        good_b = curve(None, "good", GREEN_M, 6, "budget")
        att_b = curve(None, "att", RED_M, 3.5, "budget")
        loop_t2 = T("retries capped at 10% of requests", 18, GOLD_M).move_to(loop_t)

        def to_budget():
            self.mode = "budget"
            return [old.animate.set_stroke(opacity=0.28), FadeIn(nb)]

        self.steps("A retry budget breaks the loop. Retries may add at most 10 percent to the load, "
                   "so the service never sees more than 880 a second.", [
            (lambda: [FadeOut(meta), Transform(loop_t, loop_t2), loop_l.animate.set_color(GOLD_M)], 0.9),
            "Retries may",
            (lambda: to_budget(), 0.7),
            (lambda: [FadeIn(cap_b), FadeIn(good_b), FadeIn(att_b)], 0.1),
            "so the service",
            (lambda: [tr["budget"].animate(rate_func=linear).set_value(11), loop_dots(2, GOLD_M), flow_in(3, GOLD_M)], 1.6),
        ])

        self.steps("Run the same slowdown again. Goodput still drops to zero, but once capacity is back, "
                   "880 is less than 1,000, so the queue drains.", [
            (lambda: [tr["budget"].animate(rate_func=linear).set_value(15), loop_dots(2, GOLD_M)], 2.2),
            "so the queue",
            (lambda: [tr["budget"].animate(rate_func=linear).set_value(28)], 2.2),
        ])

        back = T("back to normal at 34 s", 18, GREEN_M).move_to([X(32.5), -1.55, 0])
        self.steps("Slowly, because the server still works through attempts nobody is waiting for. "
                   "At 34 seconds it's back to normal.", [
            (lambda: [tr["budget"].animate(rate_func=linear).set_value(33), flow_out(3, RED_M)], 2.4),
            "At 34",
            (lambda: [tr["budget"].animate(rate_func=linear).set_value(40), flow_out(4, GREEN_M)], 1.6),
            (lambda: [FadeIn(back, shift=0.1 * UP)], 0.6),
        ])

        self.steps("Retries add load just when a service is slowest. A budget keeps a short slowdown short.", [
            (lambda: [glow(sv_r, GREY_A), Indicate(a_lab, color=GOLD_M)], 1.0),
            "A budget",
            (lambda: [loop_l.animate(rate_func=there_and_back).set_stroke(width=7),
                      good_b.clear_updaters().animate(rate_func=there_and_back).set_stroke(width=10)], 1.2),
        ])
        self.wait(0.6)
