from sfz import *

SAY.insert(0, (r"\bGROUP BY\b", "group by"))
SAY.insert(0, (r"\brow_number\b", "row number"))

QF = 15
X_L = -6.55
Q_Y = [3.28, 2.9]
DAYS = list(range(3, 17))                       # 3 to 16 June
SOLD = [3, 4, 5, 7, 8, 11, 12, 13, 14, 16]
ISL = [(0, [3, 4, 5], BLUE_M), (1, [7, 8], GOLD_M), (2, [11, 12, 13, 14], PURPLE_M), (3, [16], GREEN_M)]
X0, PITCH, BW = -4.2, 0.76, 0.68                # strip: left edge, pitch, box width
Y_DAY, Y_RN, Y_DIF = 1.6, 0.55, -0.45
LAB_Y_TOP = 2.35
RES_HDR, RES_Y = -1.25, [-1.7 - 0.45 * i for i in range(4)]
RX = [-2.4, -0.7, 1.0, 2.6]                     # result columns: streak, first_day, last_day, days


def dx(day):
    return X0 + BW / 2 + (day - DAYS[0]) * PITCH


def rn(day):
    return SOLD.index(day) + 1


def isl(day):
    for k, ds, c in ISL:
        if day in ds:
            return k, c
    return None, GREY_B


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def qline(s, k, hl=None):
    return left_at(M(s, QF, t2c=hl or {}), X_L, Q_Y[k])


def daybox(day, color=None):
    sold = day in SOLD
    c = color or (WHITE if sold else GREY_D)
    r = RoundedRectangle(corner_radius=0.08, width=BW, height=BW, stroke_color=c, stroke_width=2.5 if sold else 1.5)
    r.set_fill(fillc(c, 0.2) if sold else BLACK, 1).move_to([dx(day), Y_DAY, 0])
    return VGroup(r, T(str(day), 22, WHITE if sold else GREY_D).move_to([dx(day), Y_DAY, 0]))


def cell(text, day, y, color=WHITE, framed=False, size=16):
    t = M(text, size, WHITE if framed else color).move_to([dx(day), y, 0])
    if not framed:
        return t
    r = RoundedRectangle(corner_radius=0.06, width=BW, height=0.5, stroke_color=color, stroke_width=2)
    r.set_fill(fillc(color, 0.18), 1).move_to([dx(day), y, 0])
    return VGroup(r, t)


def label(s, y, color=GREY_B, mono=True):
    return left_at((M(s, 14, color) if mono else T(s, 20, color)), X_L, y)


class GapsIslands(Base):
    """sql-07, section 3 (with section 4's date version of the trick): a merchant's days with sales, 3 to 16 June, with gaps
    on the 6th, 9th, 10th and 15th. GROUP BY can't see neighbours. Number the sales days with row_number() and subtract
    the number from the date: 3, 4 and 5 June all give 2 June; a missing day bumps the difference. GROUP BY that difference
    folds each streak into one row; the longest is 11 to 14 June. Closes with merchant 1000 on the large data set."""

    def construct(self):
        self.title_card("Gaps and islands", "find every streak of days in a row")

        boxes = {d: daybox(d) for d in DAYS}
        jun = left_at(T("June", 20, GREY_B), X0, LAB_Y_TOP)
        l_day = label("days with sales", Y_DAY, mono=False)
        self.steps("A merchant earns a badge for selling on many days in a row. "
                   "Here are its first two weeks of June. White days had sales, grey days had none.", [
            (lambda: [FadeIn(jun), FadeIn(l_day)], 0.6),
            "Here are",
            (lambda: [LaggedStart(*[FadeIn(boxes[d], shift=0.1 * DOWN) for d in DAYS], lag_ratio=0.08)], 1.8),
            "White days",
            (lambda: [*[glow(boxes[d][0], WHITE, 1.06) for d in SOLD]], 0.8),
        ])

        q = left_at(T("Where does each streak start, and how long is it?", 26, YELLOW_M), -2.6, RES_HDR)
        q.move_to([0.6, RES_HDR, 0])
        self.steps("A run of days with no gap between them is a streak, also called an island. "
                   "Where does each one start, and how long is it?", [
            (lambda: [*[glow(boxes[d][0], GREY_B, 1.06) for d in (3, 4, 5)]], 0.8),
            (lambda: [*[glow(boxes[d][0], GREY_B, 1.06) for d in (11, 12, 13, 14)]], 0.8),
            "Where does",
            (lambda: [FadeIn(q, shift=0.1 * UP)], 0.7),
        ])

        q1 = qline("SELECT day, count(*) FROM active_days GROUP BY day", 0, {"GROUP BY day": YELLOW_M})
        ones = VGroup(*[cell("1", d, Y_RN, RED_M) for d in SOLD])
        bad = chip("GROUP BY day: 10 groups of one day", RED_M, 20).move_to([0.6, RES_HDR, 0])
        self.steps("GROUP BY needs a value that every day of a streak shares. Grouping by the day gives ten groups of one, "
                   "and a query has no counter that carries from one row to the next.", [
            (lambda: [FadeOut(q), FadeIn(q1, shift=0.1 * DOWN)], 0.7),
            "Grouping by the day",
            (lambda: [LaggedStart(*[FadeIn(o, shift=0.1 * DOWN) for o in ones], lag_ratio=0.08), FadeIn(bad, shift=0.1 * UP)], 1.2),
            "and a query",
            (lambda: [glow(bad[0], RED_M, 1.02)], 0.8),
        ])

        q2 = qline("SELECT day, row_number() OVER (ORDER BY day) AS n FROM active_days", 0,
                   {"row_number() OVER (ORDER BY day)": YELLOW_M})
        l_rn = label("row_number()", Y_RN)
        RN = {d: cell(str(rn(d)), d, Y_RN, YELLOW_M) for d in SOLD}
        self.steps("Here's the trick. Number the sales days in order with row number: one, two, three, and so on.", [
            (lambda: [FadeOut(bad), FadeOut(ones), *[FadeOut(x) for x in [q1]], FadeIn(q2, shift=0.1 * DOWN), FadeIn(l_rn)], 0.8),
            "one, two",
            (lambda: [LaggedStart(*[FadeIn(RN[d], shift=0.15 * DOWN) for d in SOLD], lag_ratio=0.18)], 2.0),
        ])

        q3 = qline("SELECT day, day - row_number() OVER (ORDER BY day)::int AS streak FROM active_days", 0,
                   {"day - row_number() OVER (ORDER BY day)::int": YELLOW_M})
        l_dif = label("day - row_number()", Y_DIF)
        DF = {d: cell(f"Jun {d - rn(d)}", d, Y_DIF, WHITE, framed=True, size=14) for d in SOLD}
        mark = {d: SurroundingRectangle(VGroup(boxes[d], RN[d]), buff=0.06, color=YELLOW_M, stroke_width=2.5) for d in SOLD}
        self.steps("Now subtract each row's number from its date. June 3 minus 1 is June 2. June 4 minus 2 is June 2 again.", [
            (lambda: [FadeOut(q2), FadeIn(q3, shift=0.1 * DOWN), FadeIn(l_dif)], 0.7),
            "June 3 minus",
            (lambda: [Create(mark[3])], 0.5),
            "is June 2.",
            (lambda: [FadeIn(DF[3], shift=0.15 * DOWN)], 0.6),
            "June 4 minus",
            (lambda: [ReplacementTransform(mark[3], mark[4])], 0.5),
            "is June 2 again",
            (lambda: [FadeIn(DF[4], shift=0.15 * DOWN)], 0.6),
        ])

        self.steps("Inside a streak, the date and the number both go up by one, so the difference stays the same.", [
            (lambda: [ReplacementTransform(mark[4], mark[5])], 0.5),
            "both go up",
            (lambda: [Indicate(boxes[5][1], color=YELLOW_M), Indicate(RN[5], color=YELLOW_M)], 0.8),
            "so the difference",
            (lambda: [FadeIn(DF[5], shift=0.15 * DOWN)], 0.6),
            (lambda: [*[glow(DF[d][0], WHITE, 1.08) for d in (3, 4, 5)]], 0.8),
        ])

        gapm = SurroundingRectangle(boxes[6], buff=0.06, color=RED_M, stroke_width=2.5)
        jump = left_at(T("+2", 22, RED_M), dx(6) - 0.2, LAB_Y_TOP)
        self.steps("Then comes a missing day. The date jumps by two, but the number only by one, "
                   "so the difference moves up. June 7 minus 4 is June 3.", [
            (lambda: [FadeOut(mark[5]), Create(gapm)], 0.6),
            "The date jumps",
            (lambda: [FadeIn(jump, shift=0.1 * DOWN), Indicate(boxes[7][1], color=RED_M)], 0.7),
            "but the number",
            (lambda: [Indicate(RN[7], color=YELLOW_M)], 0.6),
            "June 7 minus",
            (lambda: [FadeOut(gapm), FadeOut(jump), Create(mark[7])], 0.5),
            "is June 3",
            (lambda: [FadeIn(DF[7], shift=0.15 * DOWN)], 0.6),
        ])

        rest = [8, 11, 12, 13, 14, 16]
        self.steps("Every gap bumps it again, so every streak gets a value of its own.", [
            (lambda: [FadeOut(mark[7]), LaggedStart(*[FadeIn(DF[d], shift=0.15 * DOWN) for d in rest], lag_ratio=0.25)], 1.8),
            "so every streak",
            (lambda: [*[Transform(DF[d], cell(f"Jun {d - rn(d)}", d, Y_DIF, isl(d)[1], framed=True, size=14)) for d in SOLD],
                      *[Transform(boxes[d], daybox(d, isl(d)[1])) for d in SOLD]], 1.0),
        ])

        q4a = qline("WITH s AS (SELECT day, day - row_number() OVER (ORDER BY day)::int AS streak FROM active_days)", 0)
        q4b = qline("SELECT streak, min(day) AS first_day, max(day) AS last_day, count(*) AS days FROM s GROUP BY streak", 1,
                    {"GROUP BY streak": YELLOW_M})
        hdr = VGroup(*[M(s, 15, GREY_B).move_to([x, RES_HDR, 0]) for s, x in
                       zip(["streak", "first_day", "last_day", "days"], RX)])
        rule = Line([RX[0] - 0.8, RES_HDR - 0.24, 0], [RX[3] + 0.6, RES_HDR - 0.24, 0], stroke_width=1.5, color=GREY_D)
        RES = []
        for k, ds, c in ISL:
            y = RES_Y[k]
            RES.append(VGroup(M(f"Jun {ds[0] - rn(ds[0])}", 16, c).move_to([RX[0], y, 0]),
                              M(f"Jun {ds[0]}", 16).move_to([RX[1], y, 0]), M(f"Jun {ds[-1]}", 16).move_to([RX[2], y, 0]),
                              M(str(len(ds)), 16, c).move_to([RX[3], y, 0])))
        self.steps("That value is an island id. Group by it, and each streak folds into one row: "
                   "its first day, its last day, and how many days it lasted.", [
            (lambda: [FadeOut(q3), FadeIn(q4a, shift=0.1 * DOWN), FadeIn(q4b, shift=0.1 * DOWN)], 0.8),
            "Group by it",
            (lambda: [FadeIn(hdr), Create(rule)], 0.5),
            (lambda: [*[FadeOut(DF[d].copy(), target_position=RES[k][0].get_center(), scale=0.6) for k, ds, _ in ISL for d in ds],
                      *[FadeIn(RES[k], rate_func=squish_rate_func(smooth, 0.55, 1)) for k, _, _ in ISL]], 1.4),
            "its first day",
            (lambda: [*[Indicate(r[1], color=WHITE) for r in RES]], 0.6),
            "its last day",
            (lambda: [*[Indicate(r[2], color=WHITE) for r in RES]], 0.6),
            "and how many",
            (lambda: [*[Indicate(r[3]) for r in RES]], 0.6),
        ])

        best = SurroundingRectangle(RES[2], buff=0.1, color=PURPLE_M, stroke_width=3)
        bestd = SurroundingRectangle(VGroup(*[boxes[d] for d in (11, 12, 13, 14)]), buff=0.08, color=PURPLE_M, stroke_width=3)
        self.steps("The longest streak is four days, from the 11th to the 14th of June. "
                   "The gaps never had to be found one by one.", [
            (lambda: [Create(best)], 0.7),
            (lambda: [Create(bestd)], 0.7),
            "The gaps",
            (lambda: [*[glow(boxes[d][0], RED_M, 1.06) for d in (6, 9, 10, 15)]], 1.0),
        ])

        big = chip("large data set: merchant 1000 sold on 160 of 300 days; longest streak 6 days, 6 to 11 May",
                   GREY_B, 20).move_to([0, 3.1, 0])
        self.steps("On the course's large data set, merchant 1000 sold on 160 of 300 days. "
                   "The same query finds its longest streak: six days, from the 6th to the 11th of May.", [
            (lambda: [FadeOut(q4a), FadeOut(q4b), FadeIn(big, shift=0.1 * DOWN)], 0.8),
            "The same query",
            (lambda: [glow(big[0], WHITE, 1.02)], 0.9),
        ])

        self.steps("In a streak, the date and the row number climb together, so their difference stays put. "
                   "A gap makes it jump, and the difference names the island.", [
            (lambda: [FadeOut(big), *[Indicate(boxes[d][1], color=isl(d)[1]) for d in SOLD]], 0.9),
            (lambda: [*[Indicate(RN[d], color=isl(d)[1]) for d in SOLD]], 0.9),
            "A gap makes",
            (lambda: [*[glow(boxes[d][0], RED_M, 1.06) for d in (6, 9, 10, 15)]], 0.9),
            "names the island",
            (lambda: [*[glow(DF[d][0], isl(d)[1], 1.08) for d in SOLD]], 1.0),
        ])
        self.wait(0.6)
