from sfz import *

# Kokoro says "uh-synchronous" (heard as "a synchronous"); "eh-" gives the long "ay" in context.
SAY.insert(0, (r"\basynchronous\b", "eh-synchronous"))
# The followers' names, said as letters and numbers.
SAY.insert(0, (r"\br1\b", "R one"))
SAY.insert(0, (r"\br2\b", "R two"))


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


NX = 4.3                                        # the database column
HW = 1.85                                       # half the width of a node box
NY = {"leader": 2.3, "r1": 0.0, "r2": -2.3}
UX = -4.9                                       # the users' column
MY, OY = 1.9, -1.2                              # merchant and operator rows


def node_rect(key, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=2 * HW, height=1.1, stroke_color=color, stroke_width=3)
    return r.set_fill(BLACK, opacity=1).move_to([NX, NY[key], 0])


def node_name(key):
    return T(key, 28).move_to([0, NY[key] + 0.2, 0]).align_to([NX - HW + 0.2, 0, 0], LEFT)


def node_pos(key, p, color=YELLOW_M):
    return M(f"position {p}", 22, color).move_to([0, NY[key] + 0.2, 0]).align_to([NX + HW - 0.2, 0, 0], RIGHT)


def node_lag(key, s, color=GREY_B):
    return T(s, 20, color).move_to([0, NY[key] - 0.26, 0]).align_to([NX - HW + 0.2, 0, 0], LEFT)


def token(y, p, color):
    return chip(f"token: {p}", color, 22, mono=True).move_to([UX, y, 0])


def check(s, color=WHITE):
    return M(s, 22, color).move_to([0, -0.78, 0])


class ReplicaLag(Layered):
    """repl-03: read-your-writes and monotonic reads on lagging followers, and the fix: the session carries a log
    position and the router never serves it from a follower below that position. The lesson's numbers: a refund
    for pay-41 committed at position 2 at 1,000 ms, a reload 10 ms later, r1 300 ms behind; r2 900 ms behind."""

    def construct(self):
        self.title_card("When followers lag", "read your writes, monotonic reads")

        rects = {k: node_rect(k) for k in NY}
        names = {k: node_name(k) for k in NY}
        pos = {k: node_pos(k, 0) for k in NY}
        lags = {"leader": node_lag("leader", "takes the writes"), "r1": node_lag("r1", "300 ms behind"),
                "r2": node_lag("r2", "900 ms behind")}
        nodes = {k: VGroup(rects[k], names[k], pos[k], lags[k]) for k in NY}

        self.beat("The merchant dashboard reads from two followers, r1 and r2. They're asynchronous: r1 is 300 milliseconds behind, and r2 is 900.",
                  Succession(LaggedStart(*[FadeIn(VGroup(rects[k], names[k], lags[k]), shift=0.2 * LEFT) for k in NY],
                                         lag_ratio=0.3, run_time=2.0), Wait(3.0),
                             AnimationGroup(Indicate(lags["r1"], color=GOLD_M), Indicate(lags["r2"], color=GOLD_M), run_time=1.4)),
                  run_time=7.0)

        self.beat("A read on a follower shows the data as of its position in the leader's log. Right now, all three are at 0.",
                  Succession(Wait(1.6), LaggedStart(*[FadeIn(pos[k]) for k in NY], lag_ratio=0.3, run_time=1.6)), run_time=5.0)

        # ---- the refund and the empty page ------------------------------------------------------------------
        merchant = box("merchant", BLUE_M, w=2.4, size=26).move_to([UX, MY, 0])
        write = Arrow([UX + 1.28, MY + 0.15, 0], [NX - HW - 0.08, NY["leader"] + 0.25, 0], buff=0, stroke_width=3, color=BLUE_M,
                      max_tip_length_to_length_ratio=0.04)
        write_l = M("refund pay-41", 20, BLUE_M).move_to([-0.7, 2.72, 0])
        self.beat("At one second, the merchant asks for a refund of payment 41. The leader commits it at position 2.",
                  Succession(FadeIn(merchant, shift=0.2 * RIGHT, run_time=0.8), Wait(1.4),
                             AnimationGroup(GrowArrow(write), FadeIn(write_l), run_time=0.9), flow(write, BLUE_M, 0.8),
                             AnimationGroup(Transform(pos["leader"], node_pos("leader", 2)), flash(rects["leader"]), run_time=0.9)),
                  run_time=5.6)

        router = box("router", GREY_B, w=2.0, size=26).move_to([0, 0, 0])
        m2r = Arrow([UX + 1.28, MY - 0.15, 0], [-1.1, 0.22, 0], buff=0, stroke_width=3, color=BLUE_M,
                    max_tip_length_to_length_ratio=0.06)
        to = {"leader": Arrow([1.1, 0.22, 0], [NX - HW - 0.08, NY["leader"] - 0.25, 0], buff=0, stroke_width=3, color=GREY_B,
                              max_tip_length_to_length_ratio=0.1),
              "r1": Arrow([1.1, 0, 0], [NX - HW - 0.08, 0, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.2),
              "r2": Arrow([1.1, -0.22, 0], [NX - HW - 0.08, NY["r2"] + 0.25, 0], buff=0, stroke_width=3, color=GREY_B,
                          max_tip_length_to_length_ratio=0.1)}
        m_res = T("no refund listed", 22, RED_M).move_to([UX, 0.42, 0])
        self.beat("Ten milliseconds later the page reloads. The router sends the read to r1, still at 0. No refund is listed.",
                  Succession(AnimationGroup(FadeOut(write), FadeOut(write_l), FadeIn(router), run_time=0.8), Wait(0.8),
                             GrowArrow(m2r, run_time=0.6), flow(m2r, BLUE_M, 0.6), GrowArrow(to["r1"], run_time=0.5),
                             flow(to["r1"], BLUE_M, 0.5), Indicate(pos["r1"], color=YELLOW_M, run_time=0.8), Wait(0.6),
                             FadeIn(m_res, shift=0.2 * UP, run_time=0.7)), run_time=7.0)

        ryw = T("read your writes", 26, YELLOW_M).move_to([UX, 2.98, 0])
        self.beat("The merchant clicks Refund again. What they needed is read your writes: your own reads always show your own writes.",
                  Succession(Wait(0.4), flash(merchant[0], RED_M, 1.08), Indicate(m_res, color=RED_M), Wait(0.6),
                             Write(ryw, run_time=1.0)), run_time=4.6)

        # ---- the fix: carry the position --------------------------------------------------------------------
        m_tok = token(1.1, 2, BLUE_M)
        self.beat("The fix is to carry the position. The leader returns position 2, and the session keeps it as a token.",
                  Succession(AnimationGroup(FadeOut(m_res), FadeOut(to["r1"]), FadeOut(m2r), run_time=0.6), Wait(1.2),
                             Indicate(pos["leader"], color=YELLOW_M, run_time=0.8),
                             TransformFromCopy(pos["leader"], m_tok, path_arc=0.5, run_time=1.4)), run_time=5.0)

        chk = check("r1: 0 < 2", RED_M)
        m_ok = T("refund listed", 22, GREEN_M).move_to([UX, 0.42, 0])
        self.beat("Before a read, the router checks the follower against the token. r1 is at 0, below 2, so the read goes to the leader.",
                  Succession(GrowArrow(m2r, run_time=0.6), flow(m2r, BLUE_M, 0.6), Wait(1.6),
                             AnimationGroup(Indicate(pos["r1"], color=YELLOW_M), FadeIn(chk, shift=0.15 * UP), run_time=1.0),
                             Wait(1.4), GrowArrow(to["leader"], run_time=0.6), flow(to["leader"], BLUE_M, 0.6), Wait(0.4),
                             FadeIn(m_ok, shift=0.2 * UP, run_time=0.7)), run_time=8.2)

        chk2 = check("r1: 2 ≥ 2", GREEN_M)
        to_r1 = to["r1"].copy()
        self.beat("Once r1 reaches position 2, the merchant's reads go back to r1.",
                  Succession(Wait(0.8), AnimationGroup(Transform(pos["r1"], node_pos("r1", 2)), flash(rects["r1"]), run_time=0.9),
                             Wait(1.2), AnimationGroup(Transform(chk, chk2), FadeOut(to["leader"]), GrowArrow(to_r1), run_time=0.8),
                             flow(to_r1, BLUE_M, 0.5)), run_time=7.0)

        # ---- monotonic reads ------------------------------------------------------------------------------
        operator = box("operator", PURPLE_M, w=2.4, size=26).move_to([UX, OY, 0])
        o_tok = token(-2.0, 0, PURPLE_M)
        merchant_side = VGroup(merchant, m_tok, m_ok, ryw)
        # set_opacity would turn the token chip's tinted fill solid; fade() scales every opacity, and a copy restores them
        bright = merchant_side.copy()
        dimmed = merchant_side.copy().fade(0.7)
        self.beat("Now an operator watches the same payment. The operator wrote nothing, so its token is 0.",
                  Succession(AnimationGroup(FadeOut(chk), FadeOut(to_r1), FadeOut(m2r), Transform(merchant_side, dimmed),
                                            run_time=0.7),
                             FadeIn(operator, shift=0.2 * RIGHT, run_time=0.8), Wait(1.8), FadeIn(o_tok, shift=0.2 * DOWN, run_time=0.7)),
                  run_time=5.4)

        o2r = Arrow([UX + 1.28, OY + 0.15, 0], [-1.1, -0.22, 0], buff=0, stroke_width=3, color=PURPLE_M,
                    max_tip_length_to_length_ratio=0.07)
        res = [chip("r1: refund", GREEN_M, 20, mono=True), chip("r2: none", RED_M, 20, mono=True), chip("r1: refund", GREEN_M, 20, mono=True)]
        for i, c in enumerate(res):
            c.move_to([-5.55 + 1.95 * i, -2.95, 0])
        a1, a2, a3 = to["r1"].copy(), to["r2"].copy(), to["r1"].copy()
        self.beat("The router takes turns. r1 shows the refund. Then r2, still at 0, shows none. Then r1 shows it again.",
                  Succession(GrowArrow(o2r, run_time=0.5), Wait(0.6),
                             GrowArrow(a1, run_time=0.4), flow(a1, PURPLE_M, 0.4), FadeIn(res[0], shift=0.2 * UP, run_time=0.5),
                             Wait(1.0), AnimationGroup(FadeOut(a1), GrowArrow(a2), run_time=0.5), flow(a2, PURPLE_M, 0.4),
                             Indicate(pos["r2"], color=YELLOW_M, run_time=0.7), FadeIn(res[1], shift=0.2 * UP, run_time=0.5),
                             Wait(0.8), AnimationGroup(FadeOut(a2), GrowArrow(a3), run_time=0.5), flow(a3, PURPLE_M, 0.4),
                             FadeIn(res[2], shift=0.2 * UP, run_time=0.5)), run_time=9.4)

        mono = T("monotonic reads", 26, YELLOW_M).move_to([UX, -0.42, 0])
        self.beat("The refund appears, vanishes and comes back. The missing guarantee is monotonic reads: you never see older data than you've already seen.",
                  Succession(Indicate(res[1], color=RED_M, run_time=1.2), Wait(1.4), Write(mono, run_time=1.0)), run_time=5.4)

        o_tok2 = token(-2.0, 2, PURPLE_M)
        chk3 = check("r2: 0 < 2", RED_M)
        a4 = to["r1"].copy()
        self.beat("Same fix, one more rule: the session also keeps the highest position it has read. That makes the operator's token 2, so the router skips r2.",
                  Succession(AnimationGroup(FadeOut(a3), FadeOut(VGroup(*res)), run_time=0.6), Wait(2.6),
                             AnimationGroup(Transform(o_tok, o_tok2), Indicate(pos["r1"], color=YELLOW_M), run_time=1.0), Wait(1.4),
                             FadeIn(chk3, shift=0.15 * UP, run_time=0.6), Wait(0.3), GrowArrow(a4, run_time=0.5),
                             flow(a4, PURPLE_M, 0.5)), run_time=8.4)

        self.beat("Both fixes are the same move. The reader carries a position, and never reads below it.",
                  Succession(AnimationGroup(Transform(merchant_side, bright), run_time=0.8), Wait(0.6),
                             AnimationGroup(Circumscribe(m_tok, color=BLUE_M, buff=0.08), Circumscribe(o_tok, color=PURPLE_M, buff=0.08),
                                            run_time=1.4)), run_time=4.4)
        self.wait(0.6)
