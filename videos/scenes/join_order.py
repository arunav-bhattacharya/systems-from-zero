from sfz import *

SAY.insert(0, (r"\bCREATE STATISTICS\b", "create statistics"))
SAY.insert(0, (r"\bchargebacks\b", "charge backs"))

LX, RX = -3.3, 3.3                  # the two plan trees: merchants first, chargebacks first
YJ2, YJ1, YL = 1.2, -0.15, -1.5     # top join, lower join, bottom leaves
YRES = 2.0                          # the final count above each tree
YCH, YFM = 3.15, 2.55               # statistics chips, the estimate formula
YTI, YBAR = -2.45, -3.05            # plan name, rows-of-work bar
BSC = 5.0 / 102000                  # bar units per row
LW, LH = 1.95, 0.9


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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


def leaf(name, sub, x, y, color=WHITE, scolor=GREY_B):
    r = RoundedRectangle(corner_radius=0.12, width=LW, height=LH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color) if color != WHITE else BLACK, 1).move_to([x, y, 0])
    return VGroup(r, T(name, 20).move_to([x, y + 0.17, 0]), T(sub, 16, scolor).move_to([x, y - 0.2, 0]))


def sub(s, x, y, color=GREY_B):
    return T(s, 16, color).move_to([x, y - 0.2, 0])


def join(x, y):
    return box("join", GOLD_M, w=1.2, h=0.6, size=22).move_to([x, y, 0])


def edge(a, b):
    return Line(a.get_top() + 0.05 * UP, b.get_bottom() + 0.05 * DOWN, stroke_width=2.5, color=GREY_B) \
        if abs(a.get_center()[0] - b.get_center()[0]) < 0.01 else link(a, b, GREY_B, dashed=False, sw=2.5)


def wbar(rows, x, color):
    w = max(0.05, rows * BSC)
    return Rectangle(width=w, height=0.36, stroke_width=0).set_fill(color, 0.9).move_to([x + w / 2, YBAR, 0])


def wlab(s, rows, x, color=GREY_B):
    return left_at(T(s, 20, color), x + max(0.05, rows * BSC) + 0.18, YBAR)


class JoinOrder(Base):
    """store-10, section 3: merchants (10,000), payments (1,000,000), chargebacks (20,000); three filters on merchants,
    each 10%, multiplied as if independent: estimate 10, actual 1,000. Merchants first is priced at 1,000 + 20 = 1,020
    rows of join output and really makes 100,000 + 2,000 = 102,000, a hundred times its estimate; chargebacks first
    makes 20,000 + 2,000 = 22,000. CREATE STATISTICS (dependencies) fixes the estimate and the plan."""

    def construct(self):
        self.title_card("Join order and row estimates", "one wrong guess at the bottom picks the slow plan")

        mL, pL, cL = leaf("merchants", "10,000 rows", LX - 2.3, YL), leaf("payments", "1,000,000 rows", LX - 0.05, YL), \
            leaf("chargebacks", "20,000 rows", LX + 1.2, YJ1)
        mR, pR, cR = leaf("merchants", "10,000 rows", RX - 1.2, YJ1), leaf("payments", "1,000,000 rows", RX + 0.05, YL), \
            leaf("chargebacks", "20,000 rows", RX + 2.3, YL)
        starts = [leaf("merchants", "10,000 rows", -2.6, 0.3), leaf("payments", "1,000,000 rows", 0, 0.3),
                  leaf("chargebacks", "20,000 rows", 2.6, 0.3)]
        self.steps("Every night a report counts chargebacks at merchants in Amsterdam. It joins three tables: "
                   "ten thousand merchants, a million payments and twenty thousand chargebacks.", [
            "It joins",
            (lambda: [FadeIn(starts[0], shift=0.15 * UP)], 0.6),
            "a million",
            (lambda: [FadeIn(starts[1], shift=0.15 * UP)], 0.6),
            "and twenty",
            (lambda: [FadeIn(starts[2], shift=0.15 * UP)], 0.6),
        ])

        j1L, j2L = join(LX - 1.175, YJ1), join(LX, YJ2)
        eL = VGroup(edge(mL, j1L), edge(pL, j1L), edge(j1L, j2L), edge(cL, j2L))
        resL = T("count", 20, GREY_B).move_to([LX, YRES, 0])
        rL = Line(j2L.get_top() + 0.05 * UP, resL.get_bottom() + 0.1 * DOWN, stroke_width=2.5, color=GREY_B)
        tL = left_at(T("merchants first", 24), -6.4, YTI)
        self.steps("One order joins merchants with payments first, then adds the chargebacks.", [
            (lambda: [ReplacementTransform(starts[0], mL), ReplacementTransform(starts[1], pL),
                      ReplacementTransform(starts[2], cL)], 1.0),
            "with payments",
            (lambda: [FadeIn(j1L), Create(eL[0]), Create(eL[1])], 0.6),
            "then adds",
            (lambda: [FadeIn(j2L), Create(eL[2]), Create(eL[3]), Create(rL), FadeIn(resL), FadeIn(tL)], 0.8),
        ])

        j1R, j2R = join(RX + 1.175, YJ1), join(RX, YJ2)
        eR = VGroup(edge(pR, j1R), edge(cR, j1R), edge(j1R, j2R), edge(mR, j2R))
        resR = T("count", 20, GREY_B).move_to([RX, YRES, 0])
        rR = Line(j2R.get_top() + 0.05 * UP, resR.get_bottom() + 0.1 * DOWN, stroke_width=2.5, color=GREY_B)
        tR = left_at(T("chargebacks first", 24), 0.9, YTI)
        self.steps("The other joins payments with chargebacks first, then adds the merchants. Both give the same count.", [
            (lambda: [FadeIn(pR, shift=0.15 * UP), FadeIn(cR, shift=0.15 * UP)], 0.6),
            (lambda: [FadeIn(j1R), Create(eR[0]), Create(eR[1])], 0.6),
            "then adds",
            (lambda: [FadeIn(mR, shift=0.15 * UP), FadeIn(j2R), Create(eR[2]), Create(eR[3]), Create(rR), FadeIn(resR),
                      FadeIn(tR)], 0.8),
            "Both give",
            (lambda: [resL.animate(rate_func=there_and_back).set_color(YELLOW_M),
                      resR.animate(rate_func=there_and_back).set_color(YELLOW_M)], 0.9),
        ])

        self.steps("What differs is the result in the middle: the rows the first join hands to the second. "
                   "The planner can't count them without running the query, so it estimates.", [
            (lambda: [eL[2].animate.set_stroke(YELLOW_M, width=6), eR[2].animate.set_stroke(YELLOW_M, width=6)], 0.8),
            "the rows the first",
            (lambda: [travel(eL[2], YELLOW_M, 0.8), travel(eR[2], YELLOW_M, 0.8)], 1.0),
            "so it estimates",
            (lambda: [eL[2].animate.set_stroke(GREY_B, width=2.5), eR[2].animate.set_stroke(GREY_B, width=2.5)], 0.6),
        ])

        chips = VGroup(chip("city = Amsterdam: 10%", BLUE_M, 20), chip("country = NL: 10%", BLUE_M, 20),
                       chip("currency = EUR: 10%", BLUE_M, 20)).arrange(RIGHT, buff=0.35).move_to([0, YCH, 0])
        self.steps("The merchants have three conditions: city, country and currency. "
                   "The statistics say each one keeps one merchant in ten.", [
            "three conditions",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * DOWN) for c in chips], lag_ratio=0.3)], 1.2),
            "The statistics say",
            (lambda: [*[glow(c[0], BLUE_M, 1.05) for c in chips]], 1.0),
        ])

        fm = M("10,000 × 0.1 × 0.1 × 0.1 = 10", 22, GOLD_M).move_to([0, YFM, 0])
        self.steps("The planner treats them as independent and multiplies: "
                   "ten thousand times a tenth, three times, is ten merchants.", [
            "and multiplies",
            (lambda: [FadeIn(fm, shift=0.1 * DOWN)], 0.8),
            "is ten merchants",
            (lambda: [Transform(mL[2], sub("est 10 rows", mL.get_x(), YL, GOLD_M)),
                      Transform(mR[2], sub("est 10 rows", mR.get_x(), YJ1, GOLD_M)),
                      glow(mL[0], GOLD_M), glow(mR[0], GOLD_M)], 0.9),
        ])

        mid = (j1L.get_center() + j2L.get_center()) / 2
        midR = (j1R.get_center() + j2R.get_center()) / 2
        iL = right_at(T("est 1,000", 20, GOLD_M), mid[0] - 0.25, mid[1] + 0.12)
        iR = left_at(T("est 20,000", 20, GOLD_M), midR[0] + 0.25, midR[1] + 0.12)
        oL = T("est 20 rows", 20, GOLD_M).move_to([LX, YRES, 0])
        oR = T("est 20 rows", 20, GOLD_M).move_to([RX, YRES, 0])
        self.steps("Ten merchants have about a thousand payments. So merchants first makes a thousand rows in the middle, "
                   "and the other order twenty thousand.", [
            "So merchants first",
            (lambda: [FadeIn(iL, shift=0.1 * UP), eL[2].animate.set_stroke(GOLD_M)], 0.8),
            "and the other order",
            (lambda: [FadeIn(iR, shift=0.1 * UP), eR[2].animate.set_stroke(GOLD_M)], 0.8),
            (lambda: [Transform(resL, oL), Transform(resR, oR)], 0.6),
        ])

        bL, bR = wbar(1020, -6.4, GOLD_M), wbar(20020, 0.9, GOLD_M)
        lL, lR = wlab("est 1,020 rows of work", 1020, -6.4, GOLD_M), wlab("est 20,020", 20020, 0.9, GOLD_M)
        pick = left_at(T("the planner's pick", 20, GREEN_M), tL.get_right()[0] + 0.35, YTI)
        self.steps("Counting the rows each join makes, the planner picks merchants first: "
                   "about a thousand rows of work against twenty thousand.", [
            (lambda: [GrowFromEdge(bL, LEFT), FadeIn(lL), GrowFromEdge(bR, LEFT), FadeIn(lR)], 1.0),
            "the planner picks",
            (lambda: [FadeIn(pick, shift=0.1 * LEFT), j1L[0].animate.set_stroke(GREEN_M), j2L[0].animate.set_stroke(GREEN_M)], 0.8),
        ])

        fm2 = M("10,000 × 0.1 = 1,000", 22, RED_M).move_to([0, YFM, 0])
        chips2 = VGroup(chip("city = Amsterdam: 10%", BLUE_M, 20), chip("country = NL: keeps all", RED_M, 20),
                        chip("currency = EUR: keeps all", RED_M, 20)).arrange(RIGHT, buff=0.35).move_to([0, YCH, 0])
        self.steps("But every merchant in Amsterdam is in the Netherlands and takes euros. "
                   "The second and third conditions remove nobody. The filter keeps a thousand merchants.", [
            "is in the Netherlands",
            (lambda: [glow(chips[1][0], RED_M, 1.05), glow(chips[2][0], RED_M, 1.05)], 1.0),
            "The second and third",
            (lambda: [*[Transform(chips[i], chips2[i]) for i in range(3)]], 0.8),
            "The filter keeps",
            (lambda: [Transform(fm, fm2),
                      Transform(mL[2], sub("actual 1,000", mL.get_x(), YL, RED_M)),
                      Transform(mR[2], sub("actual 1,000", mR.get_x(), YJ1, RED_M)),
                      mL[0].animate.set_stroke(RED_M), mR[0].animate.set_stroke(RED_M)], 0.9),
        ])

        iL2 = right_at(T("actual 100,000", 20, RED_M), mid[0] - 0.25, mid[1] + 0.12)
        self.steps("The error climbs the tree. The first join makes a hundred thousand rows where the planner expected a thousand.", [
            (lambda: [travel(eL[0], RED_M, 0.7)], 0.8),
            "The first join",
            (lambda: [Transform(iL, iL2), eL[2].animate.set_stroke(RED_M, width=9), j1L[0].animate.set_stroke(RED_M)], 1.0),
            (lambda: [travel(eL[2], RED_M, 0.7)], 0.8),
        ])

        lL2 = wlab("actual 102,000", 102000, -6.4, RED_M)
        lR2 = wlab("actual 22,000", 22000, 0.9, GREEN_M)
        self.steps("The plan priced at about a thousand rows does a hundred and two thousand: "
                   "a hundred times what it expected, and almost five times the other order.", [
            (lambda: [Transform(resL, T("actual 2,000 rows", 20, RED_M).move_to([LX, YRES, 0])),
                      Transform(resR, T("actual 2,000 rows", 20, GREY_B).move_to([RX, YRES, 0])),
                      bL.animate.stretch_to_fit_width(102000 * BSC).set_fill(RED_M, 0.9).move_to([-6.4 + 51000 * BSC, YBAR, 0]),
                      Transform(lL, lL2)], 1.4),
            "a hundred times",
            (lambda: [glow(lL, RED_M, 1.06)], 0.8),
            "and almost five",
            (lambda: [bR.animate.stretch_to_fit_width(22000 * BSC).set_fill(GREEN_M, 0.9).move_to([0.9 + 11000 * BSC, YBAR, 0]),
                      Transform(lR, lR2)], 1.0),
        ])

        cs = M("CREATE STATISTICS merchants_geo (dependencies) ON city, country, currency FROM merchants", 16, TEAL_M)
        cs.move_to([0, YCH, 0])
        fm3 = M("city decides country and currency: est 1,000", 20, GREEN_M).move_to([0, YFM, 0])
        pick2 = left_at(T("the planner's pick", 20, GREEN_M), tR.get_right()[0] + 0.35, YTI)
        self.steps("Tell the planner that these columns move together, with CREATE STATISTICS. "
                   "It now estimates a thousand merchants and picks the other order.", [
            (lambda: [FadeOut(chips), FadeIn(cs, shift=0.1 * DOWN)], 0.9),
            "It now estimates",
            (lambda: [Transform(fm, fm3),
                      Transform(mL[2], sub("est 1,000 rows", mL.get_x(), YL, GREEN_M)),
                      Transform(mR[2], sub("est 1,000 rows", mR.get_x(), YJ1, GREEN_M)),
                      mL[0].animate.set_stroke(GREEN_M), mR[0].animate.set_stroke(GREEN_M)], 0.9),
            "and picks",
            (lambda: [FadeOut(pick), FadeIn(pick2, shift=0.1 * LEFT), j1L[0].animate.set_stroke(GOLD_M),
                      j2L[0].animate.set_stroke(GOLD_M), j1R[0].animate.set_stroke(GREEN_M), j2R[0].animate.set_stroke(GREEN_M)], 0.9),
        ])

        self.steps("The planner picks the cheapest plan for its estimates. When a plan is slow, "
                   "find the first step whose estimate is off by ten times or more.", [
            (lambda: [glow(j2R[0], GREEN_M, 1.06), glow(j1R[0], GREEN_M, 1.06)], 1.0),
            "find the first step",
            (lambda: [glow(mL[0], YELLOW_M, 1.06), glow(mR[0], YELLOW_M, 1.06)], 1.0),
        ])
        self.wait(0.6)
