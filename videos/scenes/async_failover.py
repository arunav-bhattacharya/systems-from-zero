from sfz import *

# Kokoro says "uh-synchronous" (heard as "a synchronous"); "eh-" gives the long "ay" in context.
SAY.insert(0, (r"\basynchronous\b", "eh-synchronous"))
# The followers' names, said as letters and numbers.
SAY.insert(0, (r"\bf1\b", "F one"))
SAY.insert(0, (r"\bf2\b", "F two"))


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


def flash(m, color=YELLOW_M, s=1.08):
    """Pulse an opaque box and recolour its outline, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


ROW = {"leader": 2.1, "f1": 0.8, "f2": -0.5}
FIRST, LAST = 239, 250                  # the log positions on screen
CW, CH, STEP, X0 = 0.64, 0.58, 0.72, -3.38
LX = -6.5                               # left edge of the row labels
RX = 5.2                                # left edge of the position readouts
TY = [-1.5, -2.15, -2.65, -3.15]        # table: header and three rows
C2, C3 = 1.9, 4.95                      # table: centres of columns 2 and 3


def cx(p):
    return X0 + (p - FIRST) * STEP


def cell(p, row, color=WHITE):
    return mbox(str(p), color, w=CW, h=CH, size=18).move_to([cx(p), ROW[row], 0])


def slot(p, row):
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=GREY_D, stroke_width=2)
    return DashedVMobject(r, num_dashes=18).move_to([cx(p), ROW[row], 0])


def name(row, s):
    return T(s, 28).move_to([0, ROW[row] + 0.17, 0]).align_to([LX, 0, 0], LEFT)


def sub(row, s, color=GREY_B):
    return T(s, 20, color).move_to([0, ROW[row] - 0.21, 0]).align_to([LX, 0, 0], LEFT)


def at(row, p, color=GREY_B):
    return M(f"at {p}", 22, color).move_to([0, ROW[row], 0]).align_to([RX, 0, 0], LEFT)


def col1(i, s, color=WHITE):
    return T(s, 24 if i else 22, color).move_to([0, TY[i], 0]).align_to([-6.15, 0, 0], LEFT)


def colc(i, x, s, color=WHITE):
    return T(s, 24 if i else 22, color).move_to([x, TY[i], 0])


class AsyncFailover(Layered):
    """repl-01: asynchronous replication, a leader crash, a promoted follower and four acknowledged payments lost;
    then fully synchronous and semi-synchronous replication. Numbers from the lesson's lab: f1 20 ms away, f2 50 ms
    away, a payment every 4 ms, the leader at 250, f1 at 246 and f2 at 238 when it dies."""

    def construct(self):
        self.title_card("Asynchronous replication and failover", "what the leader's OK promises")

        P = range(FIRST, LAST + 1)
        L = {p: cell(p, "leader") for p in P}
        F1 = {p: cell(p, "f1") for p in P if p <= 246}
        F2 = {p: cell(p, "f2") for p in P if p <= 246}
        slots = VGroup(*[slot(p, r) for r in ("f1", "f2") for p in P])
        dots = VGroup(*[T("...", 24, GREY_B).move_to([cx(FIRST) - 0.66, ROW[r], 0]) for r in ROW])

        n_l, n_1, n_2 = name("leader", "leader"), name("f1", "f1"), name("f2", "f2")
        s_l, s_1, s_2 = sub("leader", "takes the writes"), sub("f1", "20 ms away"), sub("f2", "50 ms away")
        a_l, a_1, a_2 = at("leader", 250), at("f1", 246), at("f2", 238)

        # ---- the setup -------------------------------------------------------------------------------------
        self.beat("A card processor keeps its ledger on a leader and two followers, f1 and f2.",
                  LaggedStart(*[FadeIn(VGroup(n, s), shift=0.2 * RIGHT) for n, s in ((n_l, s_l), (n_1, s_1), (n_2, s_2))],
                              lag_ratio=0.3), FadeIn(slots), run_time=2.6)

        lead = [FadeIn(L[p], shift=0.25 * DOWN) for p in P]
        copy = [TransformFromCopy(L[p], F1[p]) for p in P if p <= 246]
        self.beat("Every payment goes to the leader, which adds it to its log at the next position. "
                  "Each follower replays that log in order.",
                  FadeIn(dots), Succession(LaggedStart(*lead, lag_ratio=0.35, run_time=3.0),
                                           LaggedStart(*copy, lag_ratio=0.3, run_time=2.4)), run_time=5.6)

        self.beat("f1 is 20 milliseconds away, and f2 is 50. "
                  "At one second, the leader is at 250, f1 at 246, and f2 at 238.",
                  Succession(AnimationGroup(Indicate(s_1, color=TEAL_M), Indicate(s_2, color=TEAL_M), run_time=1.4), Wait(1.4),
                             LaggedStart(FadeIn(a_l), FadeIn(a_1), FadeIn(a_2), lag_ratio=0.8, run_time=4.0)), run_time=6.8)

        # ---- asynchronous: OK from the leader's disk --------------------------------------------------------
        hdr = VGroup(col1(0, "the leader says OK when", GREY_B), colc(0, C2, "each commit waits", GREY_B),
                     colc(0, C3, "lost at failover", GREY_B))
        rule = Line([-6.3, TY[0] - 0.27, 0], [6.3, TY[0] - 0.27, 0], stroke_width=1.5, color=GREY_D)
        r1 = col1(1, "its own disk has it")
        mark = Triangle(fill_color=YELLOW_M, fill_opacity=1, stroke_width=0).scale(0.09).rotate(-PI / 2).move_to([-6.42, TY[1], 0])
        ok_all = Brace(VGroup(*L.values()), UP, buff=0.08, color=GREEN_M)
        ok_all_l = T("clients heard OK", 22, GREEN_M).next_to(ok_all, UP, buff=0.08)
        self.beat("The question is when the leader says OK. The fastest choice is asynchronous: as soon as the payment is on its own disk.",
                  Succession(AnimationGroup(FadeIn(hdr), Create(rule), run_time=1.0), Wait(1.4),
                             AnimationGroup(FadeIn(r1, shift=0.2 * RIGHT), FadeIn(mark), run_time=0.8),
                             AnimationGroup(GrowFromCenter(ok_all), FadeIn(ok_all_l), run_time=0.9)), run_time=4.8)

        # ---- the crash --------------------------------------------------------------------------------------
        late = VGroup(*[L[p] for p in range(247, 251)])
        early = VGroup(*[L[p] for p in range(FIRST, 247)])
        self.beat("Now the leader dies. Entries 247 to 250 were still on their way to f1, and they die with it.",
                  Succession(AnimationGroup(Transform(s_l, sub("leader", "crashed", RED_M)), n_l.animate.set_color(RED_M),
                                            early.animate.set_opacity(0.3), dots[0].animate.set_opacity(0.3),
                                            a_l.animate.set_opacity(0.3), run_time=1.0),
                             Wait(1.2), AnimationGroup(*[flash(L[p][0], RED_M, 1.12) for p in range(247, 251)], run_time=1.0)),
                  run_time=3.2)

        ok_8 = Brace(early, UP, buff=0.08, color=GREEN_M)
        ok_8_l = T("clients heard OK", 22, GREEN_M).next_to(ok_8, UP, buff=0.08)
        lost = Brace(late, UP, buff=0.08, color=RED_M)
        lost_l = T("heard OK, then lost", 22, RED_M).next_to(lost, UP, buff=0.08)
        self.beat("Their clients already heard OK. Four acknowledged payments are on no machine that's still running.",
                  Succession(Wait(0.6), AnimationGroup(ReplacementTransform(ok_all, ok_8), ReplacementTransform(ok_all_l, ok_8_l),
                                                       GrowFromCenter(lost), FadeIn(lost_l), late.animate.set_stroke(color=RED_M),
                                                       run_time=1.2)), run_time=2.8)

        # ---- promotion --------------------------------------------------------------------------------------
        catch = [TransformFromCopy(F1[p], F2[p]) for p in range(FIRST, 247)]
        self.beat("After a timeout, f1 takes over. It has the highest position, so it loses the least. f2 now follows f1.",
                  Succession(Wait(0.6), AnimationGroup(Transform(s_1, sub("f1", "new leader", BLUE_M)), run_time=0.8),
                             AnimationGroup(Indicate(a_1, color=YELLOW_M, scale_factor=1.25), run_time=1.0), Wait(1.6),
                             AnimationGroup(Transform(s_2, sub("f2", "follows f1")), LaggedStart(*catch, lag_ratio=0.15),
                                            Transform(a_2, at("f2", 246)), run_time=1.6)), run_time=5.6)

        r1b, r1c = colc(1, C2, "0 ms"), colc(1, C3, "4", RED_M)
        self.beat("Those four payments never come back. That's the price of asynchronous replication.",
                  Succession(AnimationGroup(FadeIn(r1b), FadeIn(r1c, scale=1.4), run_time=0.9), Wait(0.8),
                             AnimationGroup(Indicate(lost_l, color=RED_M), run_time=1.2)), run_time=3.2)

        # ---- rewind: fully synchronous ----------------------------------------------------------------------
        r2 = col1(2, "both followers have it")
        r2b, r2c = colc(2, C2, "100 ms", GOLD_M), colc(2, C3, "0", GREEN_M)
        f2cells = VGroup(*F2.values())
        # parts of f2's row that no Transform touches (an .animate target is copied when the beat is built,
        # so it must not include a mobject that an earlier step of the same beat changes)
        f2rest = VGroup(n_2, *[s for s in slots[12:]], dots[2])
        self.beat("Rewind, and make the leader wait for both followers. Now nothing acknowledged can be lost. "
                  "But every commit waits 100 milliseconds, and if f2 pauses, every payment waits.",
                  Succession(AnimationGroup(FadeOut(ok_8), FadeOut(ok_8_l), FadeOut(lost), FadeOut(lost_l),
                                            Transform(s_l, sub("leader", "takes the writes")), n_l.animate.set_color(WHITE),
                                            early.animate.set_opacity(1), dots[0].animate.set_opacity(1), a_l.animate.set_opacity(1),
                                            late.animate.set_stroke(color=WHITE),
                                            Transform(s_1, sub("f1", "20 ms away")), Transform(s_2, sub("f2", "50 ms away")),
                                            FadeOut(f2cells), Transform(a_2, at("f2", 238)), run_time=1.2),
                             AnimationGroup(FadeIn(r2, shift=0.2 * RIGHT), mark.animate.move_to([-6.42, TY[2], 0]), run_time=0.8),
                             Wait(1.0), AnimationGroup(FadeIn(r2c, scale=1.4), run_time=0.7), Wait(1.0),
                             AnimationGroup(FadeIn(r2b), run_time=0.7), Wait(0.8),
                             AnimationGroup(Transform(s_2, sub("f2", "paused", RED_M)), f2rest.animate.set_opacity(0.45),
                                            Transform(a_2, at("f2", 238).set_opacity(0.45)),
                                            Transform(s_l, sub("leader", "waiting for f2", GOLD_M)), run_time=1.0)),
                  run_time=8.8)

        # ---- semi-synchronous -------------------------------------------------------------------------------
        r3 = col1(3, "one follower has it")
        self.beat("Most systems wait for just one follower, here f1. That's semi-synchronous replication.",
                  Succession(AnimationGroup(Transform(s_2, sub("f2", "50 ms away")), f2rest.animate.set_opacity(1),
                                            Transform(a_2, at("f2", 238)),
                                            Transform(s_l, sub("leader", "takes the writes")), run_time=0.9),
                             Wait(0.4), AnimationGroup(FadeIn(r3, shift=0.2 * RIGHT), mark.animate.move_to([-6.42, TY[3], 0]),
                                                       run_time=0.8)), run_time=3.6)

        heard = VGroup(*[L[p] for p in range(FIRST, 242)])
        ok_3 = Brace(heard, UP, buff=0.08, color=GREEN_M)
        ok_3_l = T("heard OK", 22, GREEN_M).next_to(ok_3, UP, buff=0.08)
        f1cells = VGroup(*F1.values())
        r3b = colc(3, C2, "40 ms", GOLD_M)
        self.beat("f1 confirms each payment 40 milliseconds later. "
                  "So clients have heard OK up to 241, and f1 has all of them.",
                  Succession(AnimationGroup(FadeIn(r3b), run_time=0.8), Wait(1.4),
                             AnimationGroup(GrowFromCenter(ok_3), FadeIn(ok_3_l), run_time=0.9), Wait(1.0),
                             AnimationGroup(*[flash(c[0], TEAL_M, 1.1) for c in f1cells], run_time=1.2)), run_time=5.6)

        never = Brace(late, UP, buff=0.08, color=GREY_B)
        never_l = T("never acknowledged", 22, GREY_B).next_to(never, UP, buff=0.08)
        r3c = colc(3, C3, "0", GREEN_M)
        self.beat("Crash the leader again. Payments 247 to 250 die with it, but nobody heard OK for them. "
                  "f1 takes over with every acknowledged payment.",
                  Succession(AnimationGroup(Transform(s_l, sub("leader", "crashed", RED_M)), n_l.animate.set_color(RED_M),
                                            VGroup(*L.values()).animate.set_opacity(0.3), dots[0].animate.set_opacity(0.3),
                                            a_l.animate.set_opacity(0.3), run_time=1.0),
                             Wait(0.8), AnimationGroup(late.animate.set_opacity(1).set_stroke(color=GREY_B), GrowFromCenter(never),
                                                       FadeIn(never_l), run_time=0.9),
                             Wait(1.0), AnimationGroup(Transform(s_1, sub("f1", "new leader", BLUE_M)),
                                                       FadeIn(r3c, scale=1.4), run_time=0.9)), run_time=6.0)

        self.beat("So the choice is when the leader says OK. Before a follower has the payment, a failover can lose it. After that, it can't.",
                  Succession(Wait(1.6), Circumscribe(VGroup(r1, r1c), color=RED_M, buff=0.1, run_time=1.4), Wait(0.8),
                             Circumscribe(VGroup(r3, r3c), color=GREEN_M, buff=0.1, run_time=1.4)), run_time=5.6)
        self.wait(0.6)
