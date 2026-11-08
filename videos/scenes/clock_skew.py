from sfz import *

# "pod A": Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bNTP\b", "N T P"))
# "charj-i-back" otherwise.
SAY.insert(0, (r"\bchargeback\b", "charge-back"))


def _layer(m):
    """Text above chips above arrows above boxes, so an opaque box never hides its own label."""
    for x in m.get_family():
        if isinstance(x, Text):
            x.set_z_index(4)
        elif isinstance(x, Arrow):
            x.set_z_index(1)
        elif isinstance(x, RoundedRectangle) and 0 < x.get_fill_opacity() < 0.5:
            x.set_z_index(2)


def _defer_add(anim):
    """Make each step that is not an introducer add its mobject when the step starts."""
    if isinstance(anim, AnimationGroup):
        for a in anim.animations:
            _defer_add(a)
        return
    if anim.is_introducer() or anim.mobject is None:
        return
    orig = anim._setup_scene

    def setup(scene, orig=orig, anim=anim):
        orig(scene)
        if scene is not None and anim.mobject not in scene.get_mobject_family_members():
            scene.add(anim.mobject)
    anim._setup_scene = setup


class Layered(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Manim adds every mobject of a Succession when the Succession starts, so a later step that moves or
        transforms a mobject not yet on screen would show it too early. Add the first step's mobjects now and
        each later step's when that step starts."""
        curr = self.get_mobject_family_members()

        def visit(a, first):
            if isinstance(a, Succession):
                for i, s in enumerate(a.animations):
                    if first and i == 0:
                        visit(s, True)
                    else:
                        _defer_add(s)
                return
            if isinstance(a, AnimationGroup):
                for s in a.animations:
                    visit(s, first)
                return
            if a.is_introducer() or a.mobject is None:
                return
            if a.mobject not in curr:
                self.add(a.mobject)
                curr.extend(a.mobject.get_family())

        for a in animations:
            visit(a, True)

    def play(self, *anims, **kw):
        for a in anims:
            _layer(a.mobject)
            if getattr(a, "target_mobject", None) is not None:
                _layer(a.target_mobject)
        for m in self.mobjects:
            _layer(m)
        super().play(*anims, **kw)
        for m in self.mobjects:
            _layer(m)


def flash(m, color=YELLOW_M, s=1.06):
    """Pulse an opaque box and recolour its outline, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow, invisible until its turn, so it can sit inside a Succession."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start()).set_opacity(0)
    line = Line(path.get_start(), path.get_end())
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


A_C, B_C = BLUE_M, GOLD_M
PX, PY = 4.9, 2.5                    # pods at (-PX, PY) and (PX, PY); the record between them
COLS = [-5.2, -3.2, -1.3, 1.1, 4.0]  # table: true time, writer, value, stamp, result
HY = 0.45                            # table header row
ROWS = [-0.1, -0.65, -1.2, -1.75]
AX_Y = -2.35                         # the true-time axis
BAR_Y = {"a": -0.35, "b": -1.25}


def tx(ms):
    """x on the true-time axis for ms after 10:00."""
    return -4.9 + (ms + 30) * 0.15


def pod(x, label, color):
    return box(label, color, w=2.6, h=0.9, size=28).move_to([x, PY, 0])


def pod_sub(x, s, color=GREY_B):
    return T(s, 20, color).move_to([x, PY - 0.78, 0])


def record(value, stamp, vcol=WHITE):
    v = M(value, 24, vcol).move_to([0, PY + (0.2 if stamp else 0), 0])
    s = (M(f"stamp {stamp}", 20, GREY_B) if stamp else M(".", 20).set_opacity(0)).move_to([0, PY - 0.24, 0])
    return VGroup(v, s)


def row(i, true, who, value, stamp, result, rcol):
    return VGroup(M(true, 20, GREY_B).move_to([COLS[0], ROWS[i], 0]), M(who, 20, A_C if who == "pod-a" else B_C).move_to([COLS[1], ROWS[i], 0]),
                  M(value, 20).move_to([COLS[2], ROWS[i], 0]), M(stamp, 20).move_to([COLS[3], ROWS[i], 0]),
                  T(result, 22, rcol).move_to([COLS[4], ROWS[i], 0]))


class ClockSkew(Layered):
    """dist-03: last write wins with pod-b's clock 15 ms behind drops the refund and the chargeback (the lesson's
    LwwDemo trace), then a clock that reports an error bound and Spanner-style commit wait keeps the refund."""

    def construct(self):
        self.title_card("Clocks you can't trust", "last write wins, then commit wait")

        pa, pb = pod(-PX, "pod-a", A_C), pod(PX, "pod-b", B_C)
        sa, sb = pod_sub(-PX, "clock exact"), pod_sub(PX, "clock 15 ms behind", GOLD_M)
        rec = RoundedRectangle(corner_radius=0.14, width=3.4, height=1.1, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
        rec.move_to([0, PY, 0])
        rec_h = T("payment status", 22, GREY_B).next_to(rec, UP, buff=0.12)
        val = record("(empty)", None, GREY_B)
        rule = T("keeps the highest stamp", 20, GREY_B).move_to([0, PY - 0.82, 0])
        wa = Arrow([-PX + 1.38, PY, 0], [-1.82, PY, 0], buff=0, stroke_width=3, color=A_C, max_tip_length_to_length_ratio=0.15)
        wb = Arrow([PX - 1.38, PY, 0], [1.82, PY, 0], buff=0, stroke_width=3, color=B_C, max_tip_length_to_length_ratio=0.15)
        rb = Arrow([1.82, PY, 0], [PX - 1.38, PY, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.15)

        self.beat("Two pods of the payment service write one payment's status to the same record. It keeps the write with the highest timestamp: last write wins.",
                  Succession(AnimationGroup(FadeIn(pa, shift=0.2 * RIGHT), FadeIn(pb, shift=0.2 * LEFT), run_time=0.9),
                             AnimationGroup(FadeIn(rec), FadeIn(rec_h), FadeIn(val), run_time=0.8), Wait(2.4),
                             FadeIn(rule, shift=0.15 * UP, run_time=0.7)), run_time=8.0)

        self.beat("Each pod stamps its writes with its own clock. pod A's is exact. pod B's is 15 milliseconds behind, and nobody knows.",
                  Succession(Wait(1.6), FadeIn(sa, run_time=0.6), Wait(0.8), FadeIn(sb, run_time=0.6)), run_time=6.0)

        hdr = VGroup(*[T(s, 20, GREY_B).move_to([x, HY, 0]) for s, x in zip(["true time", "writer", "value", "stamp", "result"], COLS)])
        r1 = row(0, "10:00:00.002", "pod-a", "captured", "10:00:00.002", "kept", GREEN_M)
        r2 = row(1, "10:00:00.008", "pod-b", "refunded", "09:59:59.993", "dropped, still OK", RED_M)
        self.beat("At two milliseconds past ten, pod A writes captured. The record is empty, so it keeps it.",
                  Succession(FadeIn(hdr, run_time=0.6), Wait(0.8), GrowArrow(wa, run_time=0.5), flow(wa, A_C, 0.5),
                             AnimationGroup(Transform(val, record("captured", "10:00:00.002")), FadeIn(r1[:4]), run_time=0.8),
                             Wait(0.8), FadeIn(r1[4], run_time=0.5)), run_time=5.4)

        self.beat("pod B reads captured, then writes refunded 6 milliseconds later. Its write really came second.",
                  Succession(AnimationGroup(FadeOut(wa), GrowArrow(rb), run_time=0.5), flow(rb, GREY_B, 0.6), Wait(1.0),
                             AnimationGroup(FadeOut(rb), GrowArrow(wb), run_time=0.5), flow(wb, B_C, 0.5),
                             FadeIn(r2[:3], run_time=0.6)), run_time=7.0)

        self.beat("But pod B's clock says 7 milliseconds before ten. That stamp is lower, "
                  "so the record drops the refund, and still says OK.",
                  Succession(FadeIn(r2[3], run_time=0.6), Indicate(r2[3], color=RED_M, run_time=1.0), Wait(1.2),
                             AnimationGroup(flash(rec, RED_M), Indicate(val[1], color=RED_M), run_time=1.0), Wait(0.6),
                             FadeIn(r2[4], run_time=0.5)), run_time=6.6)

        r3 = row(2, "10:00:00.014", "pod-a", "settled", "10:00:00.014", "kept", GREEN_M)
        r4 = row(3, "10:00:00.020", "pod-b", "chargeback", "10:00:00.005", "dropped, still OK", RED_M)
        self.beat("It keeps happening. pod A's settled is kept, and pod B's chargeback is dropped. "
                  "Four OKs, two writes gone, and no error anywhere.",
                  Succession(AnimationGroup(FadeOut(wb), GrowArrow(wa), run_time=0.5), flow(wa, A_C, 0.4),
                             AnimationGroup(Transform(val, record("settled", "10:00:00.014")), FadeIn(r3), run_time=0.7), Wait(0.6),
                             AnimationGroup(FadeOut(wa), GrowArrow(wb), run_time=0.5), flow(wb, B_C, 0.4),
                             AnimationGroup(FadeIn(r4), flash(rec, RED_M), run_time=0.8), Wait(1.4),
                             AnimationGroup(Indicate(r2[2], color=RED_M), Indicate(r4[2], color=RED_M), run_time=1.0)),
                  run_time=8.4)

        stats = M("skew 5 ms: 0%   10 ms: 4%   20 ms: 14%   100 ms: 50% lost", 20, GREY_B).move_to([0, -2.95, 0])
        gap = T("gap between dependent writes: 6 ms", 22, YELLOW_M).move_to([0, -2.45, 0])
        self.beat("The skew only has to beat the 6 milliseconds between dependent writes. With 100 milliseconds of skew, half of all writes are lost.",
                  Succession(AnimationGroup(FadeOut(wb), FadeIn(gap, shift=0.15 * UP), run_time=0.8), Wait(3.6),
                             FadeIn(stats, shift=0.15 * UP, run_time=0.8)), run_time=8.6)

        # ---- a clock that admits its error ------------------------------------------------------------------
        table = VGroup(hdr, r1, r2, r3, r4, gap, stats)
        self.beat("Better NTP shrinks the skew, but never to zero. Google's Spanner uses a clock that admits its error instead.",
                  Succession(Wait(2.6), AnimationGroup(FadeOut(table), Transform(val, record("(empty)", None, GREY_B)), run_time=0.9)),
                  run_time=6.4)

        axis = Line([tx(-30), AX_Y, 0], [tx(45), AX_Y, 0], stroke_width=2, color=GREY_B)
        ticks = VGroup(*[Line([tx(m), AX_Y - 0.08, 0], [tx(m), AX_Y + 0.08, 0], stroke_width=2, color=GREY_B) for m in range(-30, 41, 10)])
        nums = VGroup(*[M(str(m), 18, GREY_B).move_to([tx(m), AX_Y - 0.33, 0]) for m in range(-30, 41, 10)])
        cap = T("true time, ms after 10:00", 20, GREY_B).move_to([tx(10), AX_Y - 0.78, 0])
        t = ValueTracker(2)

        def bar(key, offset, bound, color):
            def make():
                now = t.get_value() + offset
                lo, hi = now - bound, now + bound
                r = Line([tx(lo), BAR_Y[key], 0], [tx(hi), BAR_Y[key], 0], stroke_width=12, color=color)
                r.set_stroke(opacity=0.55)
                d = Dot([tx(now), BAR_Y[key], 0], radius=0.07, color=WHITE)
                return VGroup(r, d)
            return always_redraw(make)

        bar_a, bar_b = bar("a", 0, 1, A_C), bar("b", -15, 16, B_C)
        lab_a = M("pod-a", 20, A_C).move_to([-6.05, BAR_Y["a"], 0])
        lab_b = M("pod-b", 20, B_C).move_to([-6.05, BAR_Y["b"], 0])
        truth = always_redraw(lambda: DashedLine([tx(t.get_value()), AX_Y + 0.12, 0], [tx(t.get_value()), 0.15, 0],
                                                 dash_length=0.07, stroke_width=2, color=YELLOW_M))
        e_l = T("earliest", 20, B_C).move_to([tx(-13 - 16), BAR_Y["b"] - 0.38, 0])
        l_l = T("latest", 20, B_C).next_to([tx(-13 + 16), BAR_Y["b"], 0], RIGHT, buff=0.22)
        self.beat("It returns an interval, earliest to latest, that contains the true time. "
                  "pod A's error bound is 1 millisecond. pod B's is 16.",
                  Succession(AnimationGroup(Create(axis), FadeIn(ticks), FadeIn(nums), FadeIn(cap), FadeIn(truth), run_time=1.0),
                             AnimationGroup(FadeIn(lab_a), FadeIn(bar_a), FadeIn(lab_b), FadeIn(bar_b), run_time=0.8),
                             FadeIn(e_l, run_time=0.4), FadeIn(l_l, run_time=0.4), Wait(1.6),
                             AnimationGroup(Transform(sa, pod_sub(-PX, "clock exact, bound 1 ms")), Transform(sb, pod_sub(PX, "15 ms behind, bound 16 ms", GOLD_M)),
                                            run_time=0.8)), run_time=7.6)

        st_a = DashedLine([tx(3), AX_Y + 0.12, 0], [tx(3), 0.15, 0], dash_length=0.07, stroke_width=3, color=A_C)
        st_a_l = M("stamp 3", 18, A_C).move_to([tx(3), 0.42, 0])
        ok_a = T("OK after 2 ms", 22, GREEN_M).move_to([-PX, PY - 1.25, 0])
        self.beat("To commit, pod A stamps captured with latest: 3 milliseconds past ten. "
                  "Then it waits until earliest passes the stamp, and only then says OK. That's commit wait.",
                  Succession(AnimationGroup(FadeOut(e_l), FadeOut(l_l), run_time=0.4), Wait(1.0),
                             AnimationGroup(Create(st_a), FadeIn(st_a_l), Transform(val, record("captured", "10:00:00.003")), run_time=0.8),
                             Wait(1.8), t.animate(rate_func=linear, run_time=1.8).set_value(4.2), FadeIn(ok_a, shift=0.15 * UP, run_time=0.5)),
                  run_time=9.0)

        st_b = DashedLine([tx(11), AX_Y + 0.12, 0], [tx(11), 0.5, 0], dash_length=0.07, stroke_width=3, color=B_C)
        st_b_l = M("stamp 11", 18, B_C).move_to([tx(11), 0.77, 0])
        self.beat("Now the stamp is in the past on every honest clock. pod B writes refunded at 10 past ten, "
                  "and its latest is 11, higher than 3. The refund is kept.",
                  Succession(Indicate(st_a_l, color=A_C, run_time=0.9), Wait(0.8), t.animate(rate_func=linear, run_time=1.6).set_value(10),
                             Wait(0.6), AnimationGroup(Create(st_b), FadeIn(st_b_l), run_time=0.8), Wait(0.8),
                             AnimationGroup(Transform(val, record("refunded", "10:00:00.011")), flash(rec, GREEN_M), run_time=0.9)),
                  run_time=8.4)

        ok_b = T("OK after 32 ms", 22, GREEN_M).move_to([PX, PY - 1.25, 0])
        self.beat("The price is the wait: about twice the bound, on every commit. pod B waits 32 milliseconds before its OK.",
                  Succession(t.animate(rate_func=linear, run_time=3.0).set_value(42.2), FadeIn(ok_b, shift=0.15 * UP, run_time=0.5),
                             Wait(0.5), Indicate(ok_b, color=GOLD_M, run_time=1.0)), run_time=6.6)

        self.beat("Last write wins trusts two machines' clocks to agree. To order writes safely, don't compare them, "
                  "or wait out their error.",
                  Succession(Wait(1.6), AnimationGroup(flash(pa, A_C), flash(pb, B_C), run_time=1.2), Wait(1.0),
                             AnimationGroup(Indicate(ok_a, color=GREEN_M), Indicate(ok_b, color=GREEN_M), run_time=1.2)), run_time=6.6)
        self.wait(0.6)
