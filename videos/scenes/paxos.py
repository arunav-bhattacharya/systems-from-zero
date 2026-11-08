from sfz import *

SAY.insert(0, (r"\bpay-(\d+)\b", lambda m: "pay " + " ".join(m.group(1))))
SAY.insert(0, (r"\bP([12])\b", r"P \1"))

P1_C, P2_C = BLUE_M, GOLD_M
PX = 5.1                                 # proposers at (-PX, 0) and (PX, 0)
AY = [2.0, 0.0, -2.0]                    # acceptors' centres, x = 0
AW, AH = 4.4, 1.45
TOP, BOT = 3.3, -3.25                    # caption rows


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


def acceptor(i, prom="-", acc="-", stroke=WHITE, dim=False):
    c = np.array([0, AY[i], 0])
    r = RoundedRectangle(corner_radius=0.14, width=AW, height=AH, stroke_color=stroke, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    n = T(f"A{i + 1}", 32, GREY_C if dim else WHITE).move_to(c + LEFT * (AW / 2 - 0.5))
    kx = -AW / 2 + 0.95
    k1 = T("promised", 24, GREY_B)
    k1.move_to(c + np.array([kx + k1.width / 2, 0.27, 0]))
    k2 = T("accepted", 24, GREY_B)
    k2.move_to(c + np.array([kx + k2.width / 2, -0.27, 0]))
    vx = kx + max(k1.width, k2.width) + 0.3
    v1 = T(prom, 24, WHITE)
    v1.move_to(c + np.array([vx + v1.width / 2, 0.27, 0]))
    v2 = T(acc, 24, GREEN_M if "capture" in acc else WHITE)
    v2.move_to(c + np.array([vx + v2.width / 2, -0.27, 0]))
    return VGroup(r, n, k1, v1, k2, v2)


def proposer(name, want, color, x, dim=False):
    r = RoundedRectangle(corner_radius=0.14, width=2.8, height=1.2, stroke_color=GREY_D if dim else color, stroke_width=3)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.0 if dim else 0.14), opacity=1).move_to([x, 0, 0])
    n = T(name, 32, GREY_C if dim else WHITE).move_to([x, 0.22, 0])
    w = T(want, 22, GREY_D if dim else GREY_B).move_to([x, -0.26, 0])
    return VGroup(r, n, w)


def status(s, x, color):
    return fit(T(s, 24, color), 2.8).move_to([x, -1.0, 0])


def msg(a, b, color):
    """Arrow from proposer box a to acceptor box b."""
    return edge_arrow(a[0], b[0], color, buff=0.1)


def go(ar, color, rt=0.7):
    return travel(ar, color, rt)


def ret(ar, color, rt=0.7):
    return travel(Line(ar.get_end(), ar.get_start()), color, rt)


def lost(ar, color):
    """A message that dies halfway."""
    d = Dot(radius=0.08, color=color).move_to(ar.get_start())
    mid = ar.get_start() + 0.55 * (ar.get_end() - ar.get_start())
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(ar.get_start(), mid), run_time=0.6), FadeOut(d, run_time=0.25))


class Paxos(Base):
    """cons-03, section 3: the stepper's single-decree Paxos run for pay-77. P1 gets capture chosen with ballot 1.1 and
    crashes; P2's ballot 2.2 hears about it from A2 and must propose capture, not void. Two majorities share A2."""

    def construct(self):
        self.title_card("Paxos, one decision", "prepare and promise, accept and accepted")

        p1 = proposer("P1", "wants capture", P1_C, -PX)
        p2 = proposer("P2", "wants void", P2_C, PX)
        self.steps("Payment pay-77 must end up captured or voided, never both. P1 wants capture. P2 wants void.", [
            "P1 wants",
            (lambda: [FadeIn(p1, shift=0.2 * RIGHT)], 0.8),
            "P2 wants",
            (lambda: [FadeIn(p2, shift=0.2 * LEFT)], 0.8),
        ])

        acc = [acceptor(i) for i in range(3)]
        self.steps("Three nodes, called acceptors, decide. Each one keeps two notes on disk: "
                   "the highest ballot number it has promised, and the last proposal it accepted.", [
            (lambda: [LaggedStart(*[FadeIn(a, shift=0.15 * DOWN) for a in acc], lag_ratio=0.25)], 1.4),
            "the highest ballot",
            (lambda: [*[Indicate(a[2], color=YELLOW_M) for a in acc]], 1.0),
            "and the last",
            (lambda: [*[Indicate(a[4], color=YELLOW_M) for a in acc]], 1.0),
        ])

        cap1 = T("chosen: a majority accepts one value under one ballot", 24, GREY_B).move_to([0, TOP, 0])
        self.steps("A value is chosen once a majority, two of the three, accept it under the same ballot.", [
            (lambda: [FadeIn(cap1, shift=0.15 * DOWN)], 0.9),
        ])

        a1 = [msg(p1, acc[i], P1_C) for i in range(3)]
        s1 = status("sent prepare 1.1", -PX, P1_C)
        self.steps("P1 picks ballot 1.1: round 1, from P1. It sends prepare to every acceptor. "
                   "It means: promise to ignore anything lower, and tell me what you've accepted.", [
            "It sends prepare",
            (lambda: [FadeIn(s1), *[GrowArrow(a) for a in a1]], 0.8),
            (lambda: [go(a1[0], P1_C), go(a1[1], P1_C)], 0.8),
            "promise to ignore",
            (lambda: [Indicate(acc[0][2], color=YELLOW_M), Indicate(acc[1][2], color=YELLOW_M)], 0.9),
            "and tell me",
            (lambda: [Indicate(acc[0][4], color=YELLOW_M), Indicate(acc[1][4], color=YELLOW_M)], 0.9),
        ])

        s1b = status("2 promises: a majority", -PX, P1_C)
        self.steps("A1 and A2 promise. Neither has accepted anything. Two promises are a majority, so P1 doesn't wait for A3.", [
            (lambda: [Transform(acc[0], acceptor(0, "1.1")), Transform(acc[1], acceptor(1, "1.1"))], 0.8),
            "Neither",
            (lambda: [ret(a1[0], WHITE), ret(a1[1], WHITE)], 0.8),
            "Two promises",
            (lambda: [Transform(s1, s1b)], 0.7),
            "doesn't wait",
            (lambda: [a1[2].animate.set_opacity(0.3), acc[2].animate.set_opacity(0.5)], 0.7),
        ])

        s1c = status("sent accept 1.1 capture", -PX, P1_C)
        no3 = tick(False, 0.18).move_to(a1[2].get_start() + 0.55 * (a1[2].get_end() - a1[2].get_start()) + 0.3 * DOWN + 0.1 * LEFT)
        self.steps("No value came back, so P1 may use its own. It sends accept 1.1, capture. A1 and A2 accept it. The copy to A3 is lost.", [
            "It sends accept",
            (lambda: [Transform(s1, s1c), a1[2].animate.set_opacity(1), acc[2].animate.set_opacity(1)], 0.6),
            (lambda: [go(a1[0], P1_C), go(a1[1], P1_C), lost(a1[2], P1_C)], 0.9),
            "A1 and A2 accept",
            (lambda: [Transform(acc[0], acceptor(0, "1.1", "1.1 capture")), Transform(acc[1], acceptor(1, "1.1", "1.1 capture"))], 0.8),
            "The copy to A3",
            (lambda: [Create(no3)], 0.6),
        ])

        chosen = T("capture is chosen, and nobody knows yet", 24, GREEN_M).move_to([0, BOT, 0])
        p1x = tick(False, 0.2).move_to(p1.get_corner(UR) + np.array([-0.25, -0.25, 0]))
        self.steps("Capture is now chosen. Then P1 crashes before any reply reaches it, so nobody knows yet.", [
            (lambda: [FadeIn(chosen, shift=0.15 * UP), Indicate(acc[0][5], color=GREEN_M), Indicate(acc[1][5], color=GREEN_M)], 1.0),
            "Then P1 crashes",
            (lambda: [FadeOut(VGroup(*a1)), FadeOut(no3), Transform(p1, proposer("P1", "wants capture", P1_C, -PX, dim=True)),
                      Transform(s1, status("crashed", -PX, RED_M)), Create(p1x)], 0.9),
        ])

        a2 = [msg(p2, acc[i], P2_C) for i in range(3)]
        s2 = status("sent prepare 2.2", PX, P2_C)
        slow = T("slow", 20, GREY_B).next_to(acc[0], RIGHT, buff=0.25).shift(0.35 * UP)
        self.steps("P2 hears nothing, and its timer fires. It picks a higher ballot, 2.2, and sends prepare. A1 is slow, so only A2 and A3 answer.", [
            "It picks",
            (lambda: [FadeIn(s2), *[GrowArrow(a) for a in a2]], 0.8),
            (lambda: [go(a2[1], P2_C), go(a2[2], P2_C)], 0.8),
            "A1 is slow",
            (lambda: [a2[0].animate.set_opacity(0.3), acc[0].animate.set_opacity(0.5), FadeIn(slow)], 0.7),
        ])

        s2b = status("A2 reports 1.1 capture", PX, P2_C)
        self.steps("A3 promises, with nothing to report. A2 raises its promise to 2.2, and reports what it accepted: ballot 1.1, capture.", [
            (lambda: [Transform(acc[2], acceptor(2, "2.2"))], 0.7),
            (lambda: [ret(a2[2], WHITE)], 0.7),
            "A2 raises",
            (lambda: [Transform(acc[1], acceptor(1, "2.2", "1.1 capture"))], 0.7),
            "and reports",
            (lambda: [ret(a2[1], GREEN_M), Indicate(acc[1][5], color=GREEN_M)], 0.9),
            (lambda: [Transform(s2, s2b)], 0.6),
        ])

        cap2 = T("rule: propose the value from the highest ballot reported", 24, YELLOW_M).move_to([0, TOP, 0])
        s2c = status("proposes capture", PX, GREEN_M)
        self.steps("Here is the rule. P2 must propose the value from the highest ballot it heard about. That's capture, not its own void.", [
            (lambda: [ReplacementTransform(cap1, cap2)], 0.9),
            "That's capture",
            (lambda: [Transform(s2, s2c)], 0.7),
            "not its own void",
            (lambda: [Indicate(p2[2], color=RED_M)], 1.0),
        ])

        s2d = status("learned: capture", PX, GREEN_M)
        self.steps("It sends accept 2.2, capture. A2 and A3 accept, and P2 learns the outcome: capture.", [
            (lambda: [go(a2[1], P2_C), go(a2[2], P2_C)], 0.8),
            "A2 and A3 accept",
            (lambda: [Transform(acc[1], acceptor(1, "2.2", "2.2 capture")), Transform(acc[2], acceptor(2, "2.2", "2.2 capture"))], 0.8),
            (lambda: [ret(a2[1], WHITE), ret(a2[2], WHITE)], 0.7),
            "and P2 learns",
            (lambda: [Transform(s2, s2d)], 0.7),
        ])

        m1 = SurroundingRectangle(VGroup(acc[0], acc[1]), color=P1_C, buff=0.12, corner_radius=0.2, stroke_width=3)
        m2 = SurroundingRectangle(VGroup(acc[1], acc[2]), color=P2_C, buff=0.28, corner_radius=0.26, stroke_width=3)
        m1_l = T("majority for 1.1", 22, P1_C)
        m1_l.move_to([m1.get_left()[0] - 0.3 - m1_l.width / 2, 1.9, 0])
        m2_l = T("majority for 2.2", 22, P2_C)
        m2_l.move_to([m2.get_right()[0] + 0.3 + m2_l.width / 2, -1.9, 0])
        cap3 = T("any two majorities of three share an acceptor", 24, YELLOW_M).move_to([0, TOP, 0])
        self.steps("It had to be capture. Any two majorities of three share an acceptor. "
                   "Here that's A2, which carried the value from the first round into the second.", [
            (lambda: [FadeOut(VGroup(*a2)), FadeOut(slow), FadeOut(chosen), acc[0].animate.set_opacity(1)], 0.7),
            "Any two majorities",
            (lambda: [Create(m1), FadeIn(m1_l), ReplacementTransform(cap2, cap3)], 0.9),
            (lambda: [Create(m2), FadeIn(m2_l)], 0.9),
            "Here that's A2",
            (lambda: [Indicate(acc[1][1], color=YELLOW_M, scale_factor=1.4), Indicate(acc[1][5], color=GREEN_M)], 1.2),
        ])

        self.steps("So once a value is chosen, every later ballot proposes it again. A crash can delay the decision, but it can't change it.", [
            (lambda: [Indicate(acc[0][5], color=GREEN_M), Indicate(acc[1][5], color=GREEN_M), Indicate(acc[2][5], color=GREEN_M)], 1.2),
            "A crash",
            (lambda: [Indicate(s2, color=GREEN_M)], 1.0),
        ])
        self.wait(0.6)
