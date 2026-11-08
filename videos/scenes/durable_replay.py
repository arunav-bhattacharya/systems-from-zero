from sfz import *

# The charge id from the history, said as letters and a number.
SAY.insert(0, (r"\bch_1\b", "C H one"))
# Kokoro says "IDE-mpotency" (no vowel after the d); spell out "eye-dem-potency".
SAY.insert(0, (r"\bidempotency\b", "eye-dem-potency"))


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
    """A dot that runs along a line, invisible until its turn, so it can sit inside a Succession."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start()).set_opacity(0)
    line = Line(path.get_start(), path.get_end())
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


CODE = ["charge(...)", "reserve(...)", "sleep(24 h)", "ship(...)", "return SHIPPED"]
CODE_X, CODE_Y = -5.85, [1.8, 1.25, 0.7, 0.15, -0.4]
EVENTS = ["1  Charge scheduled", "2  Charge done: ch_1", "3  Reserve scheduled", "4  Reserve done: res_1",
          "5  Timer started: 24 h", "6  Timer fired", "7  Ship scheduled", "8  Ship done: trk_1"]
EV_X, EV_Y = -2.5, [1.9 - 0.42 * k for k in range(8)]
WX = 4.75
W1Y, W2Y, BKY = 1.8, 0.35, -1.25


def code_line(i, color=WHITE):
    return M(CODE[i], 20, color).move_to([0, CODE_Y[i], 0]).align_to([CODE_X, 0, 0], LEFT)


def event(k, color=WHITE):
    return M(EVENTS[k], 20, color).move_to([0, EV_Y[k], 0]).align_to([EV_X, 0, 0], LEFT)


def wbox(y, label, color):
    r = RoundedRectangle(corner_radius=0.14, width=2.6, height=1.0, stroke_color=color, stroke_width=3)
    return r.set_fill(BLACK, opacity=1).move_to([WX, y, 0])


def wname(y, s, color=WHITE):
    return T(s, 26, color).move_to([WX, y + 0.2, 0])


def wstat(y, s, color=GREY_B):
    return T(s, 20, color).move_to([WX, y - 0.24, 0])


def cursor(i, color=YELLOW_M):
    return Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.09).rotate(-PI / 2).move_to([CODE_X - 0.28, CODE_Y[i], 0])


class DurableReplay(Layered):
    """enc-05: a durable workflow records each step in the server's event history, its worker dies during the
    24-hour sleep, and another worker replays the code against the history without charging the card again;
    then why the charge activity still needs an idempotency key. Events and ids follow the lesson's stepper."""

    def construct(self):
        self.title_card("Durable execution", "record every step, then replay")

        code_r = RoundedRectangle(corner_radius=0.14, width=3.35, height=3.0, stroke_color=GREY_D, stroke_width=2)
        code_r.set_fill(BLACK, 1).move_to([-4.78, 0.7, 0])
        code_t = T("workflow code", 22, GREY_B).move_to([-4.78, 2.58, 0])
        code = VGroup(*[code_line(i) for i in range(5)])

        self.beat("An order takes three calls: charge the card, reserve the item, and ship it. "
                  "If the process dies in between, the card is charged and nothing else happens.",
                  Succession(AnimationGroup(FadeIn(code_r), FadeIn(code_t), run_time=0.6),
                             LaggedStart(*[FadeIn(c, shift=0.15 * RIGHT) for c in code], lag_ratio=0.3, run_time=2.4), Wait(1.6),
                             AnimationGroup(Indicate(code[0], color=RED_M), code[1:].animate.set_opacity(0.35), run_time=1.2)),
                  run_time=7.4)

        hist_r = RoundedRectangle(corner_radius=0.14, width=4.15, height=3.65, stroke_color=GREY_D, stroke_width=2)
        hist_r.set_fill(BLACK, 1).move_to([-0.675, 0.425, 0])
        hist_t = T("event history (server)", 22, GREY_B).move_to([-0.675, 2.58, 0])
        w1, w2 = wbox(W1Y, "worker-1", BLUE_M), wbox(W2Y, "worker-2", GREY_D)
        w1n, w2n = wname(W1Y, "worker-1"), wname(W2Y, "worker-2", GREY_B)
        w1s, w2s = wstat(W1Y, "running the order"), wstat(W2Y, "not started")
        bank = wbox(BKY, "bank", GOLD_M)
        bank_n = wname(BKY, "bank")
        bank_c = wstat(BKY, "cards charged: 0", GREY_B)
        l1 = DashedLine([1.45, W1Y, 0], [WX - 1.35, W1Y, 0], dash_length=0.08, stroke_width=2, color=GREY_D)
        l2 = DashedLine([1.45, W2Y, 0], [WX - 1.35, W2Y, 0], dash_length=0.08, stroke_width=2, color=GREY_D)
        lb = Arrow([1.45, BKY, 0], [WX - 1.38, BKY, 0], buff=0, stroke_width=3, color=GREY_D, max_tip_length_to_length_ratio=0.12)
        cur = cursor(0)
        self.beat("Durable execution keeps this code and makes it survive the crash. "
                  "A server keeps an event history for every run.",
                  Succession(AnimationGroup(code[1:].animate.set_opacity(1), run_time=0.6),
                             AnimationGroup(FadeIn(VGroup(w1, w1n, w1s)), FadeIn(VGroup(w2, w2n, w2s)), FadeIn(VGroup(bank, bank_n, bank_c)),
                                            run_time=1.0), Wait(1.4),
                             AnimationGroup(FadeIn(hist_r), FadeIn(hist_t), run_time=0.8),
                             AnimationGroup(Create(l1), Create(l2), GrowArrow(lb), run_time=0.8)), run_time=6.6)

        ev = [event(k) for k in range(8)]
        cmd = Line([WX - 1.35, W1Y, 0], [1.45, W1Y, 0])
        self.beat("When worker 1 reaches charge, it doesn't call the bank itself. The server records that the charge is scheduled, "
                  "and an activity worker calls the bank.",
                  Succession(FadeIn(cur, run_time=0.4), Indicate(code[0], color=YELLOW_M, run_time=0.9), Wait(1.4),
                             flow(cmd, BLUE_M, 0.7), FadeIn(ev[0], shift=0.15 * RIGHT, run_time=0.5), Wait(1.0),
                             flow(lb, GOLD_M, 0.6),
                             AnimationGroup(Transform(bank_c, wstat(BKY, "cards charged: 1", GOLD_M)), flash(bank, GOLD_M), run_time=0.7)),
                  run_time=8.6)

        self.beat("The result, charge ch_1, goes into the history. Reserve works the same way.",
                  Succession(FadeIn(ev[1], shift=0.15 * RIGHT, run_time=0.6), Wait(1.4),
                             AnimationGroup(cur.animate.move_to(cursor(1)), run_time=0.4), flow(cmd, BLUE_M, 0.5),
                             FadeIn(ev[2], shift=0.15 * RIGHT, run_time=0.4), FadeIn(ev[3], shift=0.15 * RIGHT, run_time=0.4)),
                  run_time=5.4)

        self.beat("The workflow then sleeps for 24 hours. That becomes a timer in the server, so no thread waits for a day.",
                  Succession(AnimationGroup(cur.animate.move_to(cursor(2)), run_time=0.4), Wait(1.4), flow(cmd, BLUE_M, 0.5),
                             FadeIn(ev[4], shift=0.15 * RIGHT, run_time=0.5), Wait(0.8),
                             Transform(w1s, wstat(W1Y, "idle"), run_time=0.5)), run_time=6.0)

        self.beat("Now a deploy kills worker 1. Everything it held in memory is gone, but the history is safe in the server.",
                  Succession(AnimationGroup(w1.animate.set_stroke(RED_M), Transform(w1s, wstat(W1Y, "killed", RED_M)), FadeOut(cur),
                                            run_time=0.8),
                             Wait(2.4), AnimationGroup(flash(hist_r, GREEN_M, 1.02), run_time=1.2)), run_time=6.2)

        cur2 = cursor(0, TEAL_M)
        cmd2 = Line([WX - 1.35, W2Y, 0], [1.45, W2Y, 0])
        self.beat("A day later the timer fires, and worker 2 gets the task. "
                  "It has never seen this order, so it runs the workflow from the first line.",
                  Succession(FadeIn(ev[5], shift=0.15 * RIGHT, run_time=0.5), Wait(0.8),
                             AnimationGroup(w2.animate.set_stroke(TEAL_M), w2n.animate.set_color(WHITE),
                                            Transform(w2s, wstat(W2Y, "replaying", TEAL_M)), Transform(w1s, wstat(W1Y, "gone", RED_M)),
                                            run_time=0.8), Wait(2.4), FadeIn(cur2, run_time=0.5)), run_time=7.4)

        hl = lambda k: SurroundingRectangle(ev[k], color=TEAL_M, buff=0.07, corner_radius=0.06, stroke_width=2.5)
        h2 = hl(1)
        self.beat("At charge, the history already holds the result. So it returns ch_1 at once, and the bank is not called again.",
                  Succession(Indicate(code[0], color=TEAL_M, run_time=0.8), Create(h2, run_time=0.6), Wait(1.6),
                             AnimationGroup(code[0].animate.set_color(TEAL_M), run_time=0.5), Wait(0.8),
                             Indicate(bank_c, color=GOLD_M, run_time=1.0)), run_time=6.8)

        h4, h6 = hl(3), hl(5)
        self.beat("Reserve and sleep replay the same way. This is replay: run the code again, "
                  "and answer each finished step from the history.",
                  Succession(AnimationGroup(cur2.animate.move_to(cursor(1, TEAL_M)), ReplacementTransform(h2, h4),
                                            code[1].animate.set_color(TEAL_M), run_time=0.8), Wait(0.5),
                             AnimationGroup(cur2.animate.move_to(cursor(2, TEAL_M)), ReplacementTransform(h4, h6),
                                            code[2].animate.set_color(TEAL_M), run_time=0.8), Wait(1.0),
                             FadeOut(h6, run_time=0.4)), run_time=7.4)

        self.beat("At ship, the history runs out, so this time the activity really runs. "
                  "One charge, one reservation, one parcel.",
                  Succession(AnimationGroup(cur2.animate.move_to(cursor(3, TEAL_M)), run_time=0.4), Wait(1.4),
                             flow(cmd2, TEAL_M, 0.5), FadeIn(ev[6], shift=0.15 * RIGHT, run_time=0.4),
                             FadeIn(ev[7], shift=0.15 * RIGHT, run_time=0.4),
                             AnimationGroup(cur2.animate.move_to(cursor(4, TEAL_M)), Transform(w2s, wstat(W2Y, "done", GREEN_M)),
                                            run_time=0.5), Wait(0.6), code[4].animate(run_time=0.9).set_color(GREEN_M)), run_time=7.0)

        # ---- the gap: a charge whose result never got recorded ---------------------------------------------
        a1n, a2n = wname(W1Y, "attempt 1"), wname(W2Y, "attempt 2")
        self.beat("One gap is left. Suppose the worker charges the card, then dies before it reports back. "
                  "The server never records the result.",
                  Succession(AnimationGroup(FadeOut(VGroup(*ev[1:])), FadeOut(cur2), code.animate.set_color(WHITE).set_opacity(0.35),
                                            Transform(w1n, a1n), Transform(w1s, wstat(W1Y, "running charge")), w1.animate.set_stroke(BLUE_M),
                                            Transform(w2n, a2n), Transform(w2s, wstat(W2Y, "not started")), w2.animate.set_stroke(GREY_D),
                                            Transform(bank_c, wstat(BKY, "cards charged: 0", GREY_B)), run_time=1.0),
                             Wait(0.8), flow(lb, GOLD_M, 0.6),
                             AnimationGroup(Transform(bank_c, wstat(BKY, "cards charged: 1", GOLD_M)), flash(bank, GOLD_M), run_time=0.6),
                             Wait(0.4), AnimationGroup(w1.animate.set_stroke(RED_M), Transform(w1s, wstat(W1Y, "died, no report", RED_M)),
                                                       run_time=0.6), Wait(1.0), Indicate(ev[0], color=RED_M, run_time=1.0)),
                  run_time=8.0)

        alo = T("activities run at least once", 24, GOLD_M).move_to([-2.4, -2.6, 0])
        self.beat("After a timeout, the server runs the charge again, and the bank charges the card a second time. "
                  "Activities run at least once.",
                  Succession(Wait(0.8), AnimationGroup(w2.animate.set_stroke(BLUE_M), w2n.animate.set_color(WHITE),
                                                       Transform(w2s, wstat(W2Y, "running charge")), run_time=0.6),
                             flow(lb, GOLD_M, 0.6),
                             AnimationGroup(Transform(bank_c, wstat(BKY, "cards charged: 2", RED_M)), flash(bank, RED_M), run_time=0.7),
                             Wait(1.6), FadeIn(alo, shift=0.15 * UP, run_time=0.7)), run_time=8.0)

        key = chip("key: order-42/charge", YELLOW_M, 20, mono=True).move_to([WX - 0.35, -2.6, 0])
        kl = T("the key turns a retry into a replay", 24, GREEN_M).move_to([-2.4, -3.2, 0])
        self.beat("Give the charge an idempotency key built from the workflow id: order-42 slash charge. Every retry sends the same key, so the bank returns the first charge.",
                  Succession(AnimationGroup(Transform(bank_c, wstat(BKY, "cards charged: 1", GOLD_M)), run_time=0.5), Wait(0.6),
                             FadeIn(key, shift=0.2 * UP, run_time=0.7), Wait(2.6), flow(lb, GOLD_M, 0.6),
                             AnimationGroup(flash(bank, GREEN_M), Transform(bank_c, wstat(BKY, "cards charged: 1", GREEN_M)),
                                            Transform(w2s, wstat(W2Y, "got ch_1", GREEN_M)), run_time=0.7),
                             AnimationGroup(FadeIn(ev[1], shift=0.15 * RIGHT), FadeIn(kl, shift=0.15 * UP), run_time=0.7)),
                  run_time=9.4)

        self.beat("The engine records each step once. The bank still needs the key.",
                  Succession(Wait(0.4), flash(hist_r, TEAL_M, 1.02), Wait(0.4), Circumscribe(key, color=YELLOW_M, buff=0.08)),
                  run_time=3.6)
        self.wait(0.6)
