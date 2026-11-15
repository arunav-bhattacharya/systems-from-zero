from sfz import *

LX0, LX1, LY = -6.2, 5.0, 2.65          # the log bar
JX, TX, R1, R2 = -5.0, -0.85, 0.75, -1.65  # job and table centres, row heights
TW, TH = 4.0, 1.2
RX, RY = 4.5, -0.45                      # dashboard readers
N = 6000


def lx(pos, total=6000):
    return LX0 + (LX1 - LX0) * pos / total


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


def fill(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    a, b = path.get_start(), path.get_end()
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])




def table(name, color, line, lcolor=WHITE, y=R1):
    r = RoundedRectangle(corner_radius=0.12, width=TW, height=TH, stroke_color=color, stroke_width=3)
    r.set_fill(fill(color), 1).move_to([TX, y, 0])
    return VGroup(r, M(name, 21, color).move_to([TX, y + 0.26, 0]), M(line, 20, lcolor).move_to([TX, y - 0.24, 0]))


def tline(s, color=WHITE, y=R1):
    return M(s, 20, color).move_to([TX, y - 0.24, 0])


def status(s, y, color=GREY_B):
    return T(s, 20, color).move_to([TX, y - TH / 2 - 0.28, 0])


def marker(pos, color, above, label):
    x = lx(pos)
    if above:
        tri = Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.11).rotate(PI).move_to([x, LY + 0.38, 0])
        lab = T(label, 20, color).move_to([x, LY + 0.66, 0])
    else:
        tri = Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.11).move_to([x, LY - 0.38, 0])
        lab = T(label, 20, color).move_to([x, LY - 0.66, 0])
    return VGroup(tri, lab)


def share(s, color=WHITE):
    return T(s, 24, color).move_to([RX, RY - 0.25, 0])


class KappaReprocessing(Base):
    """derive-01, section 3 (with section 4's stepper): daily_gross (v1) serves the dashboard from a log of 30 days, 6,000
    records, 5 new a minute. v1 never subtracted refunds, so v2 (daily_net) replays from offset 0 at 400 a minute while v1
    keeps serving; readers stay on v1 while v2 lags, v2 catches up after 6,000 / 395 = 16 minutes, a stable 25% of merchants
    moves, then 100%, and v1 is stopped and its table dropped. m-7's day 12 (1,250.00 gross, 1,130.00 net) is invented."""

    def construct(self):
        self.title_card("Reprocessing with a log", "build the new table next to the old one, then switch")

        bar = Rectangle(width=LX1 - LX0, height=0.42, stroke_color=GREY_B, stroke_width=2.5).set_fill(fill(GREY_B, 0.12), 1)
        bar.move_to([(LX0 + LX1) / 2, LY, 0])
        ticks = VGroup(*[Line([lx(i * 150), LY - 0.15, 0], [lx(i * 150), LY + 0.15, 0], stroke_width=1.5, color=GREY_C)
                         for i in range(1, 40)])
        ltl = left_at(T("payments log: 30 days, 6,000 records", 22, GREY_B), LX0, LY + 0.6)
        newl = left_at(T("+5 a minute", 19, GREEN_M), LX1 + 0.15, LY)
        j1 = box("v1 job", BLUE_M, w=2.4, size=28).move_to([JX, R1, 0])
        t1 = table("daily_gross (v1)", BLUE_M, "m-7, day 12: 1,250.00", y=R1)
        a1 = Arrow([JX + 1.25, R1, 0], [TX - TW / 2 - 0.08, R1, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.2)
        m1 = marker(N, BLUE_M, True, "v1")
        s1 = status("position 6,000 of 6,000", R1)
        rd = RoundedRectangle(corner_radius=0.14, width=3.2, height=1.6, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
        rd.move_to([RX, RY, 0])
        rdt = T("dashboard readers", 22).move_to([RX, RY + 0.32, 0])
        sh = share("100% on v1", BLUE_M)
        r1 = Arrow([TX + TW / 2 + 0.08, R1, 0], [RX - 1.68, RY + 0.35, 0], buff=0, stroke_width=3, color=BLUE_M,
                   max_tip_length_to_length_ratio=0.1)
        feed1 = Line([lx(N), LY - 0.25, 0], [JX, R1 + 0.45, 0])

        self.steps("A merchant dashboard reads a table of revenue per day. A job called v1 keeps that table current "
                   "by reading the payments log.", [
            (lambda: [FadeIn(rd), FadeIn(rdt), FadeIn(sh)], 0.7),
            "a table of revenue",
            (lambda: [FadeIn(t1), GrowArrow(r1)], 0.7),
            "A job called v1",
            (lambda: [FadeIn(j1), GrowArrow(a1)], 0.6),
            "by reading",
            (lambda: [FadeIn(bar), FadeIn(ticks), FadeIn(ltl), FadeIn(m1), FadeIn(s1)], 0.8),
            (lambda: [FadeIn(newl), flow(feed1, YELLOW_M, 0.6), flow(r1, BLUE_M, 0.6)], 0.7),
        ])

        bug = chip("v1 never subtracts refunds", RED_M, 21).move_to([0, -3.15, 0])
        self.steps("Then finance finds a bug: v1 never subtracts refunds, so revenue is too high. "
                   "The fix needs the refunds, and v1 never stored them, so its table can't be patched.", [
            "v1 never subtracts",
            (lambda: [FadeIn(bug, shift=0.1 * UP), Transform(t1[2], tline("m-7, day 12: 1,250.00", RED_M))], 0.8),
            "and v1 never stored",
            (lambda: [glow(t1[0], RED_M, 1.03)], 0.9),
        ])

        half = tline("only days 1 to 15", RED_M)
        nogo = T("no table to go back to", 19, RED_M).move_to(s1)
        self.steps("The obvious fix is to stop v1, deploy the new code, and rebuild the table in place. "
                   "For sixteen minutes every merchant sees a half built table, and if the new code is wrong, "
                   "there's nothing to go back to.", [
            "and rebuild",
            (lambda: [t1[2].animate.become(half), m1.animate.move_to(marker(3000, BLUE_M, True, "v1")), FadeOut(s1)], 1.0),
            "every merchant",
            (lambda: [rd.animate.set_stroke(RED_M), glow(rd, RED_M, 1.04)], 0.9),
            "nothing to go back",
            (lambda: [FadeIn(nogo)], 0.6),
        ])

        j2 = box("v2 job", GOLD_M, w=2.4, size=28).move_to([JX, R2, 0])
        t2 = table("daily_net (v2)", GOLD_M, "empty", GREY_C, y=R2)
        a2 = Arrow([JX + 1.25, R2, 0], [TX - TW / 2 - 0.08, R2, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.2)
        m2 = marker(0, GOLD_M, False, "v2")
        s2 = status("position 0 of 6,005", R2)
        self.steps("The log still holds all thirty days, so there's a safer way. Start a second job, v2, with the fixed code. "
                   "It reads from offset zero and writes a new table.", [
            (lambda: [FadeOut(nogo), FadeOut(bug), rd.animate.set_stroke(WHITE), m1.animate.move_to(marker(N, BLUE_M, True, "v1")),
                      Transform(t1[2], tline("m-7, day 12: 1,250.00")), FadeIn(s1)], 0.9),
            "Start a second",
            (lambda: [FadeIn(j2), GrowArrow(a2), FadeIn(t2)], 0.8),
            "from offset zero",
            (lambda: [FadeIn(m2, shift=0.1 * RIGHT), FadeIn(s2)], 0.6),
            "writes a new table",
            (lambda: [glow(t2[0], GOLD_M, 1.03)], 0.8),
        ])

        def feed2(pos):
            return a2

        self.steps("v1 keeps running the whole time, so readers notice nothing.", [
            (lambda: [flow(feed1, YELLOW_M, 0.6), flow(r1, BLUE_M, 0.6)], 0.7),
            (lambda: [flow(feed1, YELLOW_M, 0.6), flow(r1, BLUE_M, 0.6), Indicate(sh, color=BLUE_M)], 0.8),
        ])

        self.steps("v2 reads four hundred records a minute while five new ones arrive. "
                   "Halfway through, its table has the first two weeks and nothing after.", [
            (lambda: [m2.animate.move_to(marker(3200 * 6000 / 6040, GOLD_M, False, "v2")),
                      Transform(s2, status("position 3,200 of 6,040", R2)),
                      Transform(s1, status("position 6,040 of 6,040", R1)),
                      Succession(*[flow(feed2(p), GOLD_M, 0.35) for p in (600, 1500, 2400)])], 2.2),
            "Halfway through",
            (lambda: [Transform(t2[2], tline("days 1 to 15 only", GOLD_M, R2))], 0.7),
        ])

        try2 = DashedLine([TX + TW / 2 + 0.08, R2, 0], [RX - 1.68, RY - 0.4, 0], stroke_width=3, color=RED_M, dash_length=0.1)
        no = tick(False, 0.16).move_to(try2.get_center())
        refused = T("not yet: v2 is behind", 20, RED_M).move_to([RX, RY - 1.15, 0])
        self.steps("So nobody reads v2 yet. A merchant moved now would see the last two weeks as zero.", [
            (lambda: [Create(try2)], 0.6),
            (lambda: [Create(no), FadeIn(refused)], 0.6),
            "the last two weeks",
            (lambda: [glow(t2[0], RED_M, 1.03)], 0.9),
        ])

        cu = chip("6,000 records at 395 a minute: 16 minutes", GOLD_M, 21).move_to([0, -3.15, 0])
        self.steps("Six thousand records, gaining three hundred and ninety five a minute, take sixteen minutes. "
                   "Then v2 reads the last record, and both tables follow the same log, each with its own code.", [
            (lambda: [FadeOut(try2), FadeOut(no), FadeOut(refused), FadeIn(cu, shift=0.1 * UP)], 0.7),
            (lambda: [m2.animate.move_to(marker(N, GOLD_M, False, "v2")), Transform(s2, status("position 6,080 of 6,080", R2)),
                      Transform(s1, status("position 6,080 of 6,080", R1)),
                      Succession(*[flow(feed2(p), GOLD_M, 0.35) for p in (3600, 4500, 5400)])], 1.6),
            "Then v2 reads",
            (lambda: [Transform(t2[2], tline("m-7, day 12: 1,130.00", GREEN_M, R2))], 0.7),
            "and both tables",
            (lambda: [flow(feed1, YELLOW_M, 0.6), flow(feed2(N), YELLOW_M, 0.6)], 0.8),
        ])

        r2 = Arrow([TX + TW / 2 + 0.08, R2, 0], [RX - 1.68, RY - 0.4, 0], buff=0, stroke_width=3, color=GOLD_M,
                   max_tip_length_to_length_ratio=0.1)
        self.steps("Now move readers over, a stable share at a time: a quarter of the merchants first, always the same ones. "
                   "Their numbers should differ from v1 by the refunds, and nothing else.", [
            (lambda: [FadeOut(cu), GrowArrow(r2)], 0.7),
            "a quarter",
            (lambda: [Transform(sh, share("75% v1, 25% v2"))], 0.7),
            "Their numbers",
            (lambda: [glow(t1[0], BLUE_M, 1.03), glow(t2[0], GOLD_M, 1.03)], 1.0),
        ])

        back = chip("until then, going back is one switch", GREEN_M, 21).move_to([0, -3.15, 0])
        self.steps("If v2 shows a wrong number, send everyone back to v1 with one switch. "
                   "That works because v1 never stopped, so its table is just as current.", [
            "send everyone back",
            (lambda: [Transform(sh, share("100% on v1", BLUE_M)), r2.animate.set_opacity(0.3)], 0.8),
            "because v1 never stopped",
            (lambda: [flow(feed1, YELLOW_M, 0.6), flow(r1, BLUE_M, 0.6), FadeIn(back, shift=0.1 * UP)], 0.8),
        ])

        x1 = tick(False, 0.3).move_to([JX + 0.85, R1 + 0.25, 0])
        self.steps("Once every merchant is on v2 and it has run quietly for a while, stop v1 and drop its table. "
                   "Only this last step is one way.", [
            (lambda: [r2.animate.set_opacity(1), Transform(sh, share("100% on v2", GOLD_M)), FadeOut(back)], 0.9),
            "stop v1",
            (lambda: [FadeOut(r1), Create(x1), VGroup(j1, a1, t1, m1).animate.set_opacity(0.25),
                      Transform(s1, status("stopped, table dropped", R1, RED_M))], 1.0),
            "Only this last step",
            (lambda: [glow(rd, GOLD_M, 1.04)], 0.9),
        ])

        self.steps("Keep the log long enough, and changing a derived table is a replay into a new one, "
                   "while the old one serves until you switch.", [
            "Keep the log",
            (lambda: [glow(bar, YELLOW_M, 1.01)], 1.0),
            "a replay into",
            (lambda: [flow(feed2(N), YELLOW_M, 0.6), glow(t2[0], GOLD_M, 1.03)], 1.0),
            "until you switch",
            (lambda: [flow(r2, GOLD_M, 0.6)], 0.8),
        ])
        self.wait(0.6)
