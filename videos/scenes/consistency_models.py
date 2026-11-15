from sfz import *

LANE = {"checkout": 2.0, "refunds": 0.85, "ledger": -0.3, "auditor": -1.45}
X0, XS = -4.9, 0.135                 # x of t = 0 ms, units per ms
LX = -6.5                            # lane labels
LEND = 2.45                          # lanes end
AXY = -2.2                           # time axis
BH = 0.28                            # bar height
RC, RW, RH = 4.85, 3.3, 0.9          # ladder rungs
RUNG = [("linearizable", "one copy, real time"), ("sequential", "one order for everyone"),
        ("causal", "causes before effects"), ("eventual", "agree once writes stop")]
RY = [2.0, 0.85, -0.3, -1.45]
STY = -3.2


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


def tx(t):
    return X0 + XS * t


def lane(name):
    y = LANE[name]
    return VGroup(T(name, 20, GREY_B).move_to([LX, y, 0], aligned_edge=LEFT),
                  DashedLine([tx(-3), y, 0], [LEND, y, 0], dash_length=0.06, stroke_width=1.5, color=GREY_D))


def op(name, t0, t1, label, color=BLUE_M):
    y = LANE[name]
    r = RoundedRectangle(corner_radius=0.06, width=XS * (t1 - t0), height=BH, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.3), 1).move_to([tx((t0 + t1) / 2), y, 0])
    return VGroup(r, M(label, 15, color).move_to([tx((t0 + t1) / 2), y + 0.36, 0]))


def rung(i, color=WHITE):
    name, rule = RUNG[i]
    c = np.array([RC, RY[i], 0])
    r = RoundedRectangle(corner_radius=0.12, width=RW, height=RH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to(c)
    n = T(name, 22).move_to(c + [-RW / 2 + 0.2, 0.17, 0], aligned_edge=LEFT)
    ru = T(rule, 16, GREY_B).move_to(c + [-RW / 2 + 0.2, -0.2, 0], aligned_edge=LEFT)
    return VGroup(r, n, ru)


def verdict(i, ok):
    return tick(ok, 0.17).move_to([RC + RW / 2 - 0.32, RY[i], 0])


def status(s, color=GREY_B):
    return T(s, 21, color).move_to([-2.0, STY, 0])


class ConsistencyModels(Base):
    """cons-01, section 1: one account, checkout writes 70 over 0 to 10 ms. A ledger read at 20 to 30 ms that returns
    100 breaks linearizability but is sequential (read first, then write). Two concurrent writes, 70 and 50, read in
    opposite orders by the ledger and the auditor break sequential but are causal. A fee written after reading 70,
    seen by the auditor, who then reads 100, breaks causal; eventual still holds."""

    def construct(self):
        self.title_card("Consistency models", "which values a read may return")

        lanes = {k: lane(k) for k in LANE}
        axis = Line([tx(0), AXY, 0], [tx(52), AXY, 0], stroke_width=2, color=GREY_B)
        ticks = VGroup(*[VGroup(Line([tx(t), AXY - 0.08, 0], [tx(t), AXY + 0.08, 0], stroke_width=2, color=GREY_B),
                                T(f"{t} ms", 15, GREY_B).move_to([tx(t), AXY - 0.3, 0])) for t in range(0, 51, 10)])
        w70 = op("checkout", 0, 10, "write 70", BLUE_M)
        rd = op("ledger", 20, 30, "read ?", GREY_B)
        bal = T("one account, balance 100", 20, GREY_B).move_to([LX, 3.1, 0], aligned_edge=LEFT)
        self.steps("One account holds 100. Checkout writes 70, and a moment later the ledger service reads the balance. "
                   "Which values may that read return?", [
            (lambda: [FadeIn(bal), FadeIn(lanes["checkout"]), FadeIn(lanes["ledger"]), Create(axis), FadeIn(ticks)], 0.9),
            "Checkout writes",
            (lambda: [FadeIn(w70, shift=0.1 * RIGHT)], 0.6),
            "the ledger service",
            (lambda: [FadeIn(rd, shift=0.1 * RIGHT)], 0.6),
            "Which values",
            (lambda: [glow(rd[0], YELLOW_M, 1.1)], 0.8),
        ])

        dot = Dot(radius=0.07, color=YELLOW_M).move_to(w70[0].get_left() + 0.12 * RIGHT)
        self.steps("Each operation is a bar, from when the request leaves to when the answer comes back. "
                   "The store did the work at some instant inside it.", [
            (lambda: [glow(w70[0], BLUE_M, 1.1)], 0.8),
            "The store did",
            (lambda: [FadeIn(dot)], 0.3),
            (lambda: [dot.animate(rate_func=there_and_back).move_to(w70[0].get_right() + 0.12 * LEFT)], 2.0),
            (lambda: [FadeOut(dot)], 0.3),
        ])

        rungs = [rung(i) for i in range(4)]
        ltitle = T("strongest first", 18, GREY_B).move_to([RC, 2.85, 0])
        self.steps("A consistency model says which values a read may return. Each one asks: could a single copy have "
                   "produced these results, in some order? Only the rule for that order changes.", [
            "Each one asks",
            (lambda: [FadeIn(ltitle), LaggedStart(*[FadeIn(r, shift=0.1 * LEFT) for r in rungs], lag_ratio=0.25)], 1.6),
            "Only the rule",
            (lambda: [*[Indicate(r[2], color=YELLOW_M, scale_factor=1.08) for r in rungs]], 1.0),
        ])

        vt = [verdict(i, True) for i in range(4)]
        self.steps("Linearizable is the strictest: one copy, in real time. The write ended at 10 milliseconds and the read "
                   "began at 20, so the read must return 70.", [
            (lambda: [rungs[0][0].animate.set_stroke(YELLOW_M)], 0.5),
            "The write ended",
            (lambda: [Indicate(ticks[1], color=YELLOW_M)], 0.6),
            "the read began",
            (lambda: [Indicate(ticks[2], color=YELLOW_M)], 0.6),
            "must return 70",
            (lambda: [Transform(rd, op("ledger", 20, 30, "read 70", GREEN_M)), *[Create(v) for v in vt]], 0.8),
        ])

        st1 = status("after the write in real time, and it missed it", RED_M)
        self.steps("Say the read hit a lagging follower and returned 100. It started after the write had finished, "
                   "and still missed it. That's not linearizable.", [
            (lambda: [Transform(rd, op("ledger", 20, 30, "read 100", RED_M))], 0.7),
            "It started after",
            (lambda: [FadeIn(st1, shift=0.1 * UP)], 0.6),
            "That's not",
            (lambda: [Transform(vt[0], verdict(0, False)), rungs[0][0].animate.set_stroke(RED_M)], 0.6),
        ])

        st2 = status("one order: read 100, then write 70", GREEN_M)
        self.steps("Sequential consistency drops real time. Put the read first, then the write. Each process still sees "
                   "its own operations in order, so one rung down, it's legal.", [
            (lambda: [rungs[1][0].animate.set_stroke(YELLOW_M), FadeOut(st1)], 0.6),
            "Put the read first",
            (lambda: [rd.animate.shift(XS * 22 * LEFT)], 0.9),
            (lambda: [FadeIn(st2, shift=0.1 * UP)], 0.6),
            "so one rung down",
            (lambda: [rd.animate.shift(XS * 22 * RIGHT), rungs[1][0].animate.set_stroke(GREEN_M)], 0.8),
        ])

        w50 = op("refunds", 2, 12, "write 50", PURPLE_M)
        ra = {"l1": op("ledger", 16, 24, "read 70", BLUE_M), "l2": op("ledger", 28, 36, "read 50", PURPLE_M),
              "a1": op("auditor", 16, 24, "read 50", PURPLE_M), "a2": op("auditor", 28, 36, "read 70", BLUE_M)}
        self.steps("To break sequential, add a refund that writes 50 at the same moment as checkout's 70. "
                   "The ledger reads 70, then 50. The auditor reads 50, then 70.", [
            (lambda: [FadeOut(st2), FadeOut(rd), rungs[0][0].animate.set_stroke(WHITE), rungs[1][0].animate.set_stroke(WHITE),
                      *[FadeOut(v) for v in vt]], 0.6),
            (lambda: [FadeIn(lanes["refunds"]), FadeIn(w50, shift=0.1 * RIGHT)], 0.7),
            "The ledger reads",
            (lambda: [FadeIn(ra["l1"], shift=0.1 * RIGHT)], 0.5),
            (lambda: [FadeIn(ra["l2"], shift=0.1 * RIGHT)], 0.5),
            "The auditor reads",
            (lambda: [FadeIn(lanes["auditor"]), FadeIn(ra["a1"], shift=0.1 * RIGHT)], 0.5),
            (lambda: [FadeIn(ra["a2"], shift=0.1 * RIGHT)], 0.5),
        ])

        vt = [verdict(0, False), verdict(1, False), verdict(2, True), verdict(3, True)]
        st3 = status("ledger: 70 came first. auditor: 50 came first.", RED_M)
        self.steps("The ledger's reads say 70 came first. The auditor's say 50 did. No single order fits both, "
                   "so it isn't sequential.", [
            (lambda: [glow(ra["l1"][0], BLUE_M, 1.1), glow(ra["l2"][0], PURPLE_M, 1.1)], 0.8),
            "The auditor's",
            (lambda: [glow(ra["a1"][0], PURPLE_M, 1.1), glow(ra["a2"][0], BLUE_M, 1.1), FadeIn(st3, shift=0.1 * UP)], 0.8),
            "No single order",
            (lambda: [Create(vt[0]), Create(vt[1]), rungs[1][0].animate.set_stroke(RED_M)], 0.7),
        ])

        self.steps("Causal consistency allows it. Neither write caused the other, so each reader may put them "
                   "in its own order.", [
            (lambda: [rungs[2][0].animate.set_stroke(GREEN_M), Create(vt[2]), Create(vt[3])], 0.7),
            "Neither write",
            (lambda: [glow(w70[0], BLUE_M, 1.1), glow(w50[0], PURPLE_M, 1.1)], 0.9),
        ])

        r70 = op("ledger", 14, 20, "read 70", BLUE_M)
        wfee = op("ledger", 26, 32, "write fee", GOLD_M)
        rfee = op("auditor", 36, 42, "read fee", GOLD_M)
        r100 = op("auditor", 46, 52, "read 100", RED_M)
        chain = VGroup(
            Arrow(w70[0].get_bottom() + 0.05 * DOWN + 0.3 * RIGHT, r70[0].get_top() + 0.4 * UP, buff=0.05, stroke_width=2.5,
                  color=GOLD_M, max_tip_length_to_length_ratio=0.08),
            Arrow(r70[0].get_right(), wfee[0].get_left(), buff=0.08, stroke_width=2.5, color=GOLD_M,
                  max_tip_length_to_length_ratio=0.3),
            Arrow(wfee[0].get_bottom() + 0.3 * RIGHT, rfee[0].get_top() + 0.4 * UP, buff=0.05, stroke_width=2.5,
                  color=GOLD_M, max_tip_length_to_length_ratio=0.1),
        )
        self.steps("To break causal, chain the writes. The ledger reads 70, then writes a fee based on it. "
                   "The auditor reads that fee, then reads the balance and gets 100.", [
            (lambda: [FadeOut(st3), FadeOut(w50), FadeOut(lanes["refunds"]), *[FadeOut(v) for v in ra.values()],
                      *[FadeOut(v) for v in vt], *[r[0].animate.set_stroke(WHITE) for r in rungs]], 0.7),
            "The ledger reads",
            (lambda: [FadeIn(r70, shift=0.1 * RIGHT), GrowArrow(chain[0])], 0.6),
            "then writes a fee",
            (lambda: [FadeIn(wfee, shift=0.1 * RIGHT), GrowArrow(chain[1])], 0.6),
            "The auditor reads",
            (lambda: [FadeIn(rfee, shift=0.1 * RIGHT), GrowArrow(chain[2])], 0.6),
            "and gets 100",
            (lambda: [FadeIn(r100, shift=0.1 * RIGHT)], 0.6),
        ])

        vt = [verdict(0, False), verdict(1, False), verdict(2, False), verdict(3, True)]
        st4 = status("saw the effect, then missed its cause", RED_M)
        self.steps("The fee exists because of the 70. The auditor saw the effect, then missed its cause, "
                   "so this isn't even causal.", [
            (lambda: [*[glow(a, GOLD_M, 1.0) for a in chain]], 0.9),
            "The auditor saw",
            (lambda: [glow(rfee[0], GOLD_M, 1.1)], 0.5),
            (lambda: [glow(r100[0], RED_M, 1.1), FadeIn(st4, shift=0.1 * UP)], 0.6),
            "so this isn't",
            (lambda: [*[Create(v) for v in vt[:3]], rungs[2][0].animate.set_stroke(RED_M)], 0.7),
        ])

        self.steps("Eventual consistency still holds. It only promises that the copies agree once writes stop.", [
            (lambda: [Create(vt[3]), rungs[3][0].animate.set_stroke(GREEN_M)], 0.7),
            "It only promises",
            (lambda: [glow(rungs[3][0], GREEN_M, 1.04)], 0.9),
        ])

        st5 = status("pick the weakest model your code can live with", GREY_A)
        self.steps("Each rung down drops one demand. Pick the weakest model your code can live with.", [
            (lambda: [FadeOut(st4), LaggedStart(*[glow(r[0], YELLOW_M, 1.03) for r in rungs], lag_ratio=0.3)], 1.6),
            "Pick the weakest",
            (lambda: [FadeIn(st5, shift=0.1 * UP)], 0.7),
        ])
        self.wait(0.6)
