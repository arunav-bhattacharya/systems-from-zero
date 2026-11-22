from sfz import *

SAY.insert(0, (r"\bKreps\b", "kreps"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
N = 31                                         # days 0..30 in the log
LX0, LW, LY = -6.2, 0.36, 2.55                 # the log tape
JY = 1.15                                      # the jobs
PCX = {"v1": 3.4, "v2": -3.4}                  # the two tables
PY0, PY1 = -2.65, 0.15
PW = 6.0
BASE = -2.2                                    # bars' baseline
SCALE = 1.45 / 20000                           # bar height per unit of takings
CAP_Y, BAR_Y = -3.2, -2.86

# event-time takings by day: the named ones are the demo's; the rest are illustrative heights only
_r = np.random.default_rng(3)
EV = [float(v) for v in _r.uniform(17600, 20300, N)]
EV[0], EV[1], EV[2], EV[28], EV[29], EV[30] = 19684.20, 19139.78, 19609.06, 17678.19, 19785.49, 6846.18
V1 = [v * f for v, f in zip(EV, _r.uniform(1.03, 1.08, N))]   # gross, before refunds (illustrative)
V1[30] = EV[30] * 1.05


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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

    def steps(self, text, items, after=0.3):
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
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def pulse(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.1)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def cell_x(i):
    return LX0 + LW * (i + 0.5)


def log_tape():
    cells = VGroup(*[Square(side_length=LW - 0.04, stroke_color=BLUE_M, stroke_width=1.5).set_fill(fillc(BLUE_M, 0.22), 1)
                     .move_to([cell_x(i), LY, 0]) for i in range(N)])
    title = left_at(T("the log: every payment, in the order it arrived", 22, BLUE_M), LX0, LY + 0.55)
    d0 = T("day 0", 18, GREY_B).move_to([cell_x(0) + 0.15, LY - 0.4, 0])
    d30 = T("day 30, today", 18, GREY_B).move_to([cell_x(30) - 0.45, LY + 0.4, 0])
    new = Arrow([6.4, LY, 0], [cell_x(30) + 0.25, LY, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.25)
    newl = T("new", 18, GREY_B).move_to([5.85, LY + 0.32, 0])
    return cells, VGroup(title, d0, d30), VGroup(new, newl)


def job(name, color):
    r = RoundedRectangle(corner_radius=0.12, width=1.9, height=0.7, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([PCX[name], JY, 0])
    return VGroup(r, T(f"job {name}", 24).move_to(r))


def panel(name, color, sub):
    cx = PCX[name]
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=PY1 - PY0, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([cx, (PY0 + PY1) / 2, 0])
    t = T(f"table {name}: takings by day", 22, color).move_to([cx, PY1 - 0.3, 0])
    s = T(sub, 16, GREY_B).move_to([cx, PY1 - 0.62, 0])
    axis = Line([cx - PW / 2 + 0.25, BASE, 0], [cx + PW / 2 - 0.25, BASE, 0], stroke_width=1.5, color=GREY_C)
    d0 = T("day 0", 16, GREY_B).move_to([bar_x(name, 0) + 0.1, BASE - 0.22, 0])
    d30 = T("day 30", 16, GREY_B).move_to([bar_x(name, 30) - 0.1, BASE - 0.22, 0])
    return VGroup(r, t, s, axis, d0, d30)


def bar_x(name, i):
    return PCX[name] - PW / 2 + 0.35 + (PW - 0.7) * (i + 0.5) / N


def bar(name, i, v, color):
    h = max(v * SCALE, 0.001)
    return Rectangle(width=0.11, height=h, stroke_width=0).set_fill(color, 0.9).move_to([bar_x(name, i), BASE + h / 2, 0])


def bars(name, vals, color):
    return VGroup(*[bar(name, i, v, color) for i, v in enumerate(vals)])


def tag(name):
    c = chip("owners read this", GREEN_M, 18)
    return c.move_to([PCX[name] + 2.05, 0.6, 0])


def cursor(i):
    return Square(side_length=LW + 0.06, stroke_color=YELLOW_M, stroke_width=4).move_to([cell_x(i), LY, 0])


class KappaReprocessing(Base):
    """derive-01, section 3. Finance changes the takings rule; a month must be worked out again while owners keep
    reading. Log → job v1 → table v1. Emptying and refilling leaves holes; the clerk starts a fresh sheet instead.
    v2 replays the log into a new table: by processing time it puts 554,322.25 on day 30 and zero before; by event
    time it rebuilds each day (19,684.20 ...). 400 a minute, 5 new, 16 minutes. Switch the owners, delete v1: kappa.
    Conditions and costs (7-day default, 130 billion a month), moral, and a check (100 a minute: 64 minutes, same
    numbers)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        line = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(line), run_time=0.25)
        self.play(Uncreate(line), run_time=secs, rate_func=linear)

    def dot(self, a, b, color=YELLOW_M, rt=0.6):
        d = Dot(radius=0.07, color=color).move_to(a)
        return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))

    def construct(self):
        self.capm = None
        self.title_card("Redo a month without a hole", "keep the log, replay it into a second table")

        cells, labels, newin = log_tape()
        j1 = job("v1", BLUE_M)
        p1 = panel("v1", BLUE_M, "the old code")
        b1 = bars("v1", V1, BLUE_M)
        a1 = Arrow([cell_x(30), LY - 0.2, 0], [PCX["v1"] + 0.3, JY + 0.38, 0], buff=0, stroke_width=2.5, color=GREY_B,
                   max_tip_length_to_length_ratio=0.15)
        a1b = Arrow([PCX["v1"], JY - 0.37, 0], [PCX["v1"], PY1 + 0.03, 0], buff=0, stroke_width=2.5, color=GREY_B,
                    max_tip_length_to_length_ratio=0.2)
        own = tag("v1")
        qm = T("?", 64, YELLOW_M).move_to([-3.4, -1.1, 0])

        # ---------------- scene 1: the request ----------------
        self.steps("Picture the café where this course began. Each card payment becomes one line in the payments app, "
                   "and a program turns those lines into the owner's takings: the money her shop took each day.", [
            "one line",
            (lambda: [LaggedStart(*[FadeIn(c) for c in cells], lag_ratio=0.04), FadeIn(labels)], 1.3),
            "a program",
            (lambda: [GrowArrow(a1), FadeIn(j1)], 0.6),
            "the owner's takings",
            (lambda: [GrowArrow(a1b), FadeIn(p1)], 0.6),
            (lambda: [LaggedStart(*[GrowFromEdge(b, DOWN) for b in b1], lag_ratio=0.05)], 1.0),
        ])
        self.steps("Now finance asks for one change. Takings should subtract refunds, and count each payment on the day it happened.", [
            "subtract refunds",
            (lambda: self.cap("1. subtract refunds", GOLD_M), 0.5),
            "and count each",
            (lambda: self.cap("1. subtract refunds     2. count each payment on the day it happened", GOLD_M), 0.5),
        ])
        self.steps("A month of numbers must be worked out again, while two thousand owners keep looking at theirs. "
                   "How do you redo a month without anybody seeing a hole?", [
            "two thousand owners",
            (lambda: [FadeIn(own, shift=0.1 * DOWN)], 0.6),
            "How do you",
            (lambda: [*self.uncap(), FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the log, the job, the table ----------------
        self.steps("Here's the setup. The log is every payment, one after another, in the order they arrived. "
                   "Nothing in it is ever changed.", [
            (lambda: [FadeOut(qm)], 0.4),
            "The log is",
            (lambda: [LaggedStart(*[c.animate(rate_func=there_and_back).set_fill(BLUE_M, 0.7) for c in cells], lag_ratio=0.05)], 1.4),
            "Nothing in it",
            (lambda: self.cap("the log: lines are only ever added at the end", BLUE_M), 0.5),
        ])
        self.steps("A job called v1 reads each new line as it lands, and adds it to a table: takings, by day. "
                   "The owners' dashboards read that table.", [
            (lambda: [*self.uncap(), FadeIn(newin)], 0.5),
            "reads each new",
            (lambda: [self.dot(newin[0].get_start(), [cell_x(30), LY, 0], GREY_B, 0.5)], 0.5),
            (lambda: [self.dot([cell_x(30), LY - 0.2, 0], a1.get_end(), YELLOW_M, 0.5)], 0.5),
            "adds it",
            (lambda: [self.dot(a1b.get_start(), a1b.get_end(), YELLOW_M, 0.4),
                      b1[30].animate.stretch(1.25, 1, about_edge=DOWN)], 0.6),
            "The owners'",
            (lambda: [glow(own[0], GREEN_M, 1.06)], 0.7),
        ])

        # ---------------- scene 3: the tempting plan ----------------
        self.steps("The tempting plan: change v1's code, empty the table, and let it fill up again. One program, one table. Feels tidy.", [
            (lambda: self.cap("the tempting plan: new code, empty the table, refill it", PURPLE_M), 0.5),
            "empty the table",
            (lambda: [b1.animate.stretch(0.01, 1, about_edge=DOWN)], 0.8),
        ])
        self.steps("But until it refills, every owner sees a month with holes in it. "
                   "That's not a fix. That's an outage with good intentions.", [
            "every owner sees",
            (lambda: [*self.cap("until it refills: a month with holes", RED_M), glow(own[0], RED_M, 1.06), p1[0].animate.set_stroke(RED_M)], 0.7),
            "an outage",
            (lambda: [b1.animate.stretch(100, 1, about_edge=DOWN), p1[0].animate.set_stroke(BLUE_M), *self.cap("let's not")], 0.9),
        ])

        # ---------------- scene 4: a fresh sheet ----------------
        self.steps("The café already knows better. Picture the clerk who keeps the takings sheet from the notebook. "
                   "When her method changes, she doesn't rub out the sheet the owner is reading.", [
            (lambda: self.cap("a clerk, a notebook, and the takings sheet the owner reads", WHITE), 0.5),
            "she doesn't rub out",
            (lambda: [glow(p1[0], BLUE_M, 1.02), glow(own[0], GREEN_M, 1.06)], 0.8),
        ])
        self.steps("She takes a fresh sheet, starts from the notebook's first page, and works forward. "
                   "When she's caught up, she hands it over, and bins the old one.", [
            "a fresh sheet",
            (lambda: self.cap("a fresh sheet, from the first page; hand it over when caught up; bin the old one", WHITE), 0.5),
            "the notebook's first page",
            (lambda: [glow(cells[0], YELLOW_M, 1.3)], 0.6),
            "and works forward",
            (lambda: [LaggedStart(*[c.animate(rate_func=there_and_back).set_fill(YELLOW_M, 0.6) for c in cells], lag_ratio=0.05)], 1.3),
        ])
        self.steps("Map it. The notebook is the log. The sheet is the table. Her method is the job's code.", [
            "The notebook is",
            (lambda: [*self.cap("notebook = the log", BLUE_M), LaggedStart(*[glow(c, BLUE_M, 1.15) for c in cells[::3]], lag_ratio=0.1)], 0.8),
            "The sheet is",
            (lambda: [*self.cap("sheet = the table", WHITE), glow(p1[0], BLUE_M, 1.02)], 0.7),
            "Her method",
            (lambda: [*self.cap("her method = the job's code", WHITE), glow(j1[0], BLUE_M, 1.06)], 0.7),
        ])
        self.steps("And here the picture breaks in our favour: a program rereads a month in minutes, and can do it again tomorrow.", [
            "rereads a month",
            (lambda: self.cap("where the picture breaks: a program rereads a month in minutes", GREEN_M), 0.5),
        ])

        # ---------------- scene 5: replay, and a guess ----------------
        j2 = job("v2", GREEN_M)
        p2 = panel("v2", GREEN_M, "the new code")
        a2b = Arrow([PCX["v2"], JY - 0.37, 0], [PCX["v2"], PY1 + 0.03, 0], buff=0, stroke_width=2.5, color=GREY_B,
                    max_tip_length_to_length_ratio=0.2)
        cur = cursor(0)
        self.steps("So start a second job, v2, with the new code. It reads the log from the very first line and writes to a new table. "
                   "Nobody reads that table yet.", [
            (lambda: self.uncap(), 0.3),
            "a second job",
            (lambda: [FadeIn(j2, shift=0.1 * DOWN)], 0.6),
            "from the very first",
            (lambda: [Create(cur)], 0.5),
            "writes to a new",
            (lambda: [GrowArrow(a2b), FadeIn(p2)], 0.7),
            "Nobody reads",
            (lambda: [glow(own[0], GREEN_M, 1.06)], 0.7),
        ])
        self.steps("Now suppose v2 kept one habit from v1: it puts each payment on the day it handled it. For a year, that looked right.", [
            "it puts each",
            (lambda: self.cap("v2 keeps v1's habit: each payment goes on the day it was handled", PURPLE_M), 0.6),
        ])
        self.steps("Where will this replay put the month's takings? Pause and guess.", [
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        top = PY1 - 0.85
        tall = Rectangle(width=0.11, height=top - BASE, stroke_width=0).set_fill(RED_M, 0.9).move_to([bar_x("v2", 30), (top + BASE) / 2, 0])
        zz = VGroup(Line([bar_x("v2", 30) - 0.12, top + 0.04, 0], [bar_x("v2", 30) + 0.12, top + 0.1, 0], stroke_width=3, color=RED_M),
                    Line([bar_x("v2", 30) - 0.12, top + 0.13, 0], [bar_x("v2", 30) + 0.12, top + 0.19, 0], stroke_width=3, color=RED_M))
        big = T("554,322.25 on day 30", 20, RED_M)
        big.move_to([bar_x("v2", 30) - 0.2 - big.width / 2, top - 0.05, 0])
        zeros = T("0 on every day before", 18, RED_M).move_to([PCX["v2"] - 0.9, BASE + 0.3, 0])
        grow = bar("v2", 30, 1, RED_M)

        def sweep(steps_, extra):
            out = []
            for k, i in enumerate(steps_):
                out.append((lambda i=i, k=k: [cur.animate.move_to([cell_x(i), LY, 0]), *extra(i, k)], 0.16))
            return out

        def proc(i, k):
            h = (top - BASE) * (k + 1) / 16
            return [Transform(grow, Rectangle(width=0.11, height=h, stroke_width=0).set_fill(RED_M, 0.9).move_to([bar_x("v2", 30), BASE + h / 2, 0]))]

        self.steps("All of it on today. 554,322.25 on day 30, and zero on every day before.", [
            (lambda: [*self.uncap(), FadeIn(grow)], 0.2),
            *sweep(list(range(1, 31, 2)) + [30], proc),
            (lambda: [Transform(grow, tall), FadeIn(zz), FadeIn(big)], 0.5),
            "and zero",
            (lambda: [FadeIn(zeros)], 0.5),
        ])
        self.steps("According to this table, the café sold a month of coffee this morning. Busy morning.", [
            (lambda: [pulse(big, RED_M)], 0.8),
        ])
        self.steps("The habit was wrong all along. Live, a payment is handled within a second of happening, so the two days "
                   "almost always matched. A replay handles every line today, so the hidden mistake becomes the whole answer.", [
            "Live, a payment",
            (lambda: [self.dot(newin[0].get_start(), [cell_x(30), LY, 0], GREY_B, 0.4)], 0.4),
            (lambda: [self.dot([cell_x(30), LY - 0.2, 0], a1.get_end(), YELLOW_M, 0.4)], 0.4),
            "A replay handles",
            (lambda: [glow(tall, RED_M, 1.0), *self.cap("live: handled a second after it happened.   replay: every line handled today", WHITE)], 0.8),
        ])
        self.steps("The day the job handles a line is called processing time. The day written inside the line, when the payment happened, "
                   "is called event time. A replay must use event time.", [
            "called processing time",
            (lambda: self.cap("processing time: when the job handles the line", RED_M), 0.5),
            "The day written",
            (lambda: [*self.cap("event time: written inside the line, when the payment happened", GREEN_M),
                      LaggedStart(*[glow(c, GREEN_M, 1.15) for c in cells[::3]], lag_ratio=0.1)], 0.9),
        ])

        # ---------------- scene 6: by event time, and how long ----------------
        b2 = bars("v2", EV, GREEN_M)
        lab0 = T("19,684.20", 16, GREEN_M).move_to([bar_x("v2", 0) + 0.35, BASE + EV[0] * SCALE + 0.2, 0])
        lab1 = T("19,139.78", 16, GREEN_M).move_to([bar_x("v2", 4) + 0.35, BASE + 1.85, 0])

        def ev(i, k):
            j0 = 0 if k == 0 else list(range(1, 31, 2))[k - 1] + 1 if k <= 15 else 30
            return [GrowFromEdge(b2[j], DOWN) for j in range(j0, i + 1)]

        self.steps("Replay again, by event time. Day 0: 19,684.20. Day 1: 19,139.78.", [
            (lambda: [FadeOut(VGroup(grow, zz, big, zeros)), cur.animate.move_to([cell_x(0), LY, 0]), *self.uncap()], 0.5),
            (lambda: [GrowFromEdge(b2[0], DOWN)], 0.3),
            "Day 0",
            (lambda: [FadeIn(lab0)], 0.4),
            "Day 1",
            (lambda: [cur.animate.move_to([cell_x(1), LY, 0]), GrowFromEdge(b2[1], DOWN)], 0.3),
            (lambda: [Transform(lab0, T("day 1: 19,139.78", 16, GREEN_M).move_to(lab0).shift(0.35 * RIGHT))], 0.4),
        ])
        self.remove(grow, tall, zz, big, zeros)
        rest = list(range(3, 31, 2)) + [30]
        prev = [1]

        def ev2(i, k):
            j0 = prev[0] + 1
            prev[0] = i
            return [GrowFromEdge(b2[j], DOWN) for j in range(j0, i + 1)]

        self.steps("And so on, up to today, which has only just begun.", [
            (lambda: [FadeOut(lab0)], 0.2),
            *[(lambda i=i: [cur.animate.move_to([cell_x(i), LY, 0]), *ev2(i, 0)], 0.15) for i in rest],
            "which has only",
            (lambda: [pulse(b2[30], YELLOW_M)], 0.6),
        ])
        self.steps("How long does it take? v2 reads 400 lines a minute while 5 new ones arrive, so it gains 395 a minute. "
                   "Six thousand lines of history take 16 minutes.", [
            "v2 reads 400",
            (lambda: self.cap("400 read a minute, 5 new arrive: 395 gained a minute", WHITE), 0.5),
            "Six thousand",
            (lambda: self.cap("6,000 lines of history ÷ 395 a minute: 16 minutes", WHITE), 0.5),
        ])
        self.steps("Until then, v2's table is missing the recent days, so nobody moves to it.", [
            (lambda: [glow(own[0], GREEN_M, 1.06)], 0.8),
        ])

        # ---------------- scene 7: switch, then delete ----------------
        self.steps("When v2 reaches the end of the log, both tables follow the same lines, each with its own code.", [
            (lambda: [*self.uncap(), glow(cur, YELLOW_M, 1.2)], 0.6),
            "both tables",
            (lambda: [self.dot(newin[0].get_start(), [cell_x(30), LY, 0], GREY_B, 0.4)], 0.4),
            (lambda: [self.dot([cell_x(30), LY - 0.2, 0], a1.get_end(), YELLOW_M, 0.5),
                      self.dot([cell_x(30), LY - 0.2, 0], [PCX["v2"] + 0.3, JY + 0.38, 0], YELLOW_M, 0.5)], 0.5),
        ])
        self.steps("Now switch the owners to v2. Nobody saw a hole, because the old table kept serving the whole time.", [
            "switch the owners",
            (lambda: [own.animate.move_to(tag("v2"))], 0.9),
            "Nobody saw",
            (lambda: [glow(p2[0], GREEN_M, 1.02)], 0.8),
        ])
        self.steps("Later, stop v1 and delete its table.", [
            "stop v1",
            (lambda: [FadeOut(VGroup(j1, a1, a1b, p1, b1))], 0.9),
        ])
        self.steps("That's the whole recipe. Jay Kreps, who helped build Kafka, a program that keeps logs like this one, suggested it in 2014, "
                   "and half joking, called it the kappa architecture.", [
            (lambda: self.cap("keep the log, replay into a second copy, switch the readers", WHITE), 0.5),
            "called it the kappa",
            (lambda: self.cap("the kappa architecture: keep the log, replay into a second copy, switch the readers", GREEN_M), 0.5),
        ])
        self.steps("One engine, one codebase. Replaying the oldest part of the log is the batch job.", [
            "Replaying the oldest",
            (lambda: [LaggedStart(*[glow(c, GREEN_M, 1.15) for c in cells[:12]], lag_ratio=0.08)], 1.0),
        ])

        # ---------------- scene 8: three conditions, and the bill ----------------
        self.steps("It works under three conditions. The replay runs through the same code as live lines. "
                   "A crash halfway must not count anything twice. And every grouping by time uses event time.", [
            "The replay runs",
            (lambda: self.cap("1. the same code for old lines and new", WHITE), 0.5),
            "A crash halfway",
            (lambda: self.cap("2. a crash halfway counts nothing twice", WHITE), 0.5),
            "And every grouping",
            (lambda: self.cap("3. group by event time", GREEN_M), 0.5),
        ])
        gone = T("deleted after 7 days, by default", 20, RED_M).move_to([cell_x(11), LY - 0.4, 0])
        self.steps("Then the bill. The log must still hold the month. Kafka deletes lines older than 7 days unless you tell it otherwise, "
                   "so keep 30 days on purpose.", [
            (lambda: self.cap("the log must still hold the month", WHITE), 0.5),
            "Kafka deletes",
            (lambda: [*[c.animate.set_opacity(0.15) for c in cells[:24]], FadeIn(gone), labels[1].animate.set_opacity(0)], 0.8),
            "so keep 30",
            (lambda: [*[c.animate.set_opacity(1) for c in cells[:24]], FadeOut(gone), labels[1].animate.set_opacity(1),
                      *self.cap("keep 30 days, on purpose", GREEN_M)], 0.8),
        ])
        self.steps("A busy log holds 130 billion lines after a month. And while both versions run, you pay for two jobs and two tables.", [
            (lambda: self.cap("a busy log: 50,000 lines a second, 130 billion after a month", GOLD_M), 0.5),
            "two jobs",
            (lambda: self.cap("while both run: two jobs, two tables", GOLD_M), 0.5),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So: keep the log, replay it into a second table by event time, and switch the readers when it has caught up. "
                   "Never rebuild the table they're reading.", [
            (lambda: self.cap("keep the log, replay by event time into a second table, then switch", YELLOW_M, 28), 0.6),
            "Never rebuild",
            (lambda: [glow(p2[0], GREEN_M, 1.02)], 0.8),
        ], after=0.5)
        self.steps("One quick check. You replay at 100 lines a minute instead of 400. What changes, and what doesn't? Pause and think.", [
            (lambda: self.cap("100 lines a minute instead of 400: what changes?", WHITE), 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It takes 64 minutes instead of 16. And the daily takings don't change by a cent. "
                   "The answer depends on the log, not on how fast you read it.", [
            (lambda: [*self.cap("100 a minute: 64 minutes", WHITE), cur.animate.move_to([cell_x(0), LY, 0])], 0.4),
            (lambda: [cur.animate.move_to([cell_x(30), LY, 0])], 2.2),
            "And the daily",
            (lambda: [*self.cap("the same takings, to the cent", GREEN_M), LaggedStart(*[pulse(b, GREEN_M) for b in b2[:30]], lag_ratio=0.04)], 1.2),
            "The answer depends",
            (lambda: self.cap("the answer depends on the log, not on how fast you read it", YELLOW_M), 0.5),
        ], after=0.4)
        self.wait(2.0)
