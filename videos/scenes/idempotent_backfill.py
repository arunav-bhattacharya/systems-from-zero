from sfz import *

SAY.insert(0, (r"\b6 November\b", "the sixth of November"))
SAY.insert(0, (r"\bidempotent\b", "eye-dem-potent"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
DY, DW, DH = 2.35, 2.8, 1.05                 # the night's three tasks
DX = {"extract": -4.3, "load": 0.0, "report": 4.3}
PY, PW, PH = -1.0, 6.2, 3.1                  # the two tables (and the kitchen, on the right)
PXL, PXR = -3.4, 3.4
ROW_Y = [-0.7, -1.15, -1.6]
TOP_Y, CAP_Y, BAR_Y = 3.35, -3.2, -2.86
VALUE = "5,974,657"
STEAK = "#8B4A2B"


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

    def steps(self, text, items, after=0.3):
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


def glow(m, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def pulse(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.08)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def run(a, b, color=YELLOW_M, run_time=0.7):
    d = Dot(radius=0.08, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.12))


# ---- the pieces ----
def task(name, state="waiting", color=GREY_B):
    x = DX[name]
    idle = ManimColor(color).to_hex() == ManimColor(GREY_B).to_hex()
    r = RoundedRectangle(corner_radius=0.14, width=DW, height=DH, stroke_color=color, stroke_width=3)
    r.set_fill(BLACK if idle else fillc(color), 1).move_to([x, DY, 0])
    return VGroup(r, T(name, 28).move_to([x, DY + 0.2, 0]), T(state, 20, color).move_to([x, DY - 0.24, 0]))


def panel(x, sub, color):
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([x, PY, 0])
    return VGroup(r, M("daily_totals", 24, color).move_to([x, PY + PH / 2 - 0.36, 0]),
                  T(sub, 20, GREY_B).move_to([x, PY + PH / 2 - 0.76, 0]))


def trow(x, k, color=WHITE, val=VALUE):
    return M(f"2026-11-06   {val}", 22, color).move_to([x, ROW_Y[k], 0])


def report(x, s, color, size=24):
    return fit(T(s, size, color), PW - 0.4).move_to([x, PY - PH / 2 + 0.38, 0])


def plate(c):
    outer = Circle(radius=0.66, stroke_color=GREY_A, stroke_width=3).set_fill("#1c1c1c", 1).move_to(c)
    inner = Circle(radius=0.46, stroke_color=GREY_D, stroke_width=1.5).move_to(c)
    return VGroup(outer, inner)


def steak(c):
    e = Ellipse(width=0.62, height=0.36, stroke_color="#B06A43", stroke_width=2).set_fill(STEAK, 1).move_to(c)
    fat = Arc(radius=0.14, start_angle=0.3, angle=2.2, stroke_color="#E8D3B5", stroke_width=2).move_to(c + [0.06, 0.02, 0])
    return VGroup(e, fat)


KC = np.array([PXR, PY, 0])                   # the kitchen fills the right panel's place
PLATE_C = KC + [0.25, -0.2, 0]


class IdempotentBackfill(Base):
    """batch-13, section 1. The night of 6 November: extract (235 payments), load and report. Load's attempt 1 writes
    5,974,657 cents and its machine dies before it says done; the orchestrator retries; an appending load leaves two
    rows and a report of 11,949,314. The kitchen (a second cook adds a steak to the plate, or replaces the plate) gives
    the fix: replace the day's partition. Idempotent, three rules, a backfill as one more rerun (17,923,971 vs
    5,974,657), the 90-night demo (28% too high), the email limit, and a check question about reading the newest data."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_clock(self, s):
        new = right_at(T(s, 24, GOLD_M), 6.4, TOP_Y)
        old, self.clk = self.clk, new
        return [swap(old, new)]

    def set_top(self, s, color=GREY_B):
        new = left_at(T(s, 24, color), -6.4, TOP_Y)
        old, self.top = self.top, new
        return [swap(old, new)]

    def st(self, name, state, color):
        return Transform(self.tk[name], task(name, state, color))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.clk = self.top = None
        self.title_card("Every job said fine, and the total doubled", "retries, and tasks that replace their day")

        # ---------------- scene 1: the doubled total ----------------
        self.tk = tk = {n: task(n) for n in DX}
        arr = VGroup(*[Arrow([DX[a] + DW / 2 + 0.08, DY, 0], [DX[b] - DW / 2 - 0.08, DY, 0], buff=0, stroke_width=3,
                             color=GREY_B, max_tip_length_to_length_ratio=0.12) for a, b in (("extract", "load"), ("load", "report"))])
        qm = T("?", 72, YELLOW_M).move_to([0, -0.7, 0])
        self.steps("Picture the payments company's night shift, run by programs instead of people. "
                   "After the shops close, three jobs run, one after another.", [
            "three jobs",
            (lambda: [LaggedStart(*[FadeIn(tk[n], shift=0.1 * RIGHT) for n in DX], lag_ratio=0.3)], 1.1),
            "one after another",
            (lambda: [GrowArrow(arr[0]), GrowArrow(arr[1])], 0.7),
        ])
        self.steps("One morning, the accountants open the report for 6 November. The total is twice what the shops took. "
                   "And every job says it finished fine.", [
            "the accountants",
            (lambda: self.cap("the report for 6 November: twice what the shops took", RED_M), 0.6),
            "And every job",
            (lambda: [LaggedStart(*[self.st(n, "done", GREEN_M) for n in DX], lag_ratio=0.3)], 1.0),
        ])
        self.steps("How does a job that succeeded double the money? Hold that question.", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the night, and the program in charge ----------------
        pa = panel(PXL, "load appends a row", GOLD_M)
        stg = chip("staging: 235 payments", TEAL_M, 20).move_to([DX["extract"], 1.15, 0])
        self.steps("Here's the night. Extract copies the day's card payments into a work table. "
                   "Load adds them up and writes one total into a table called daily totals. Report reads that total.", [
            (lambda: [FadeOut(qm), *self.uncap(), *[self.st(n, "waiting", GREY_B) for n in DX]], 0.6),
            "Extract copies",
            (lambda: [glow(tk["extract"][0], BLUE_M)], 0.8),
            "Load adds",
            (lambda: [glow(tk["load"][0], BLUE_M)], 0.8),
            "a table called",
            (lambda: [FadeIn(pa, shift=0.1 * DOWN)], 0.7),
            "Report reads",
            (lambda: [glow(tk["report"][0], BLUE_M)], 0.8),
        ])
        self.steps("A program is in charge of the night. It starts each job when the one before it is done, "
                   "and if a job fails, it runs it again.", [
            (lambda: self.set_top("the program in charge: the run for 6 November"), 0.6),
            "It starts each",
            (lambda: [LaggedStart(*[glow(a, YELLOW_M, 1.0) for a in arr], lag_ratio=0.5)], 1.0),
            "and if a job",
            (lambda: self.cap("if a job fails, run it again"), 0.5),
        ])
        self.steps("That program is called an orchestrator, and running a job again is called a retry. "
                   "A retry feels careful. Something went wrong, so try again.", [
            "called an orchestrator",
            (lambda: self.set_top("orchestrator: the run for 6 November"), 0.6),
            "called a retry",
            (lambda: self.cap("retry: run a failed task again"), 0.5),
        ])

        # ---------------- scene 3: one night, one crash ----------------
        lo = np.array([DX["load"], DY - DH / 2, 0])
        top_l = np.array([PXL, PY + PH / 2, 0])
        top_r = np.array([PXR, PY + PH / 2, 0])
        ra = [trow(PXL, 0, GOLD_M)]
        self.steps("At minute 5, extract copies 235 payments for 6 November.", [
            (lambda: [*self.uncap(), *self.set_clock("minute 5"), self.st("extract", "running", BLUE_M)], 0.6),
            "copies 235",
            (lambda: [FadeIn(stg, shift=0.1 * DOWN)], 0.6),
            (lambda: [self.st("extract", "done", GREEN_M)], 0.5),
        ])
        self.steps(f"At minute 15, load's first attempt adds them up and writes the total: {VALUE} cents.", [
            (lambda: [*self.set_clock("minute 15"), self.st("load", "attempt 1", BLUE_M)], 0.6),
            "writes the total",
            (lambda: [run(lo, top_l, GOLD_M)], 0.7),
            (lambda: [FadeIn(ra[0], shift=0.1 * DOWN)], 0.5),
        ])
        x = tick(False, 0.2).move_to([DX["load"] + DW / 2 - 0.3, DY + DH / 2 - 0.25, 0])
        self.steps("And then its machine dies, before it can tell the orchestrator it's done. "
                   "The total is already saved.", [
            "its machine dies",
            (lambda: [Create(x)], 0.5),
            "The total is",
            (lambda: [pulse(ra[0], GOLD_M), *self.cap("the write is saved; the 'done' never arrives", RED_M)], 0.9),
        ])
        self.steps("The orchestrator only knows one thing: this attempt never said done. "
                   "So it marks it failed, waits five minutes, and runs load again.", [
            "So it marks",
            (lambda: [self.st("load", "failed: retry", RED_M)], 0.6),
            "waits five",
            (lambda: [*self.set_clock("minute 20")], 0.5),
            "runs load again",
            (lambda: [FadeOut(x), self.st("load", "attempt 2", BLUE_M)], 0.6),
        ])
        self.steps("At minute 30, the second attempt writes its total too, and this time it says done.", [
            (lambda: [*self.uncap(), *self.set_clock("minute 30")], 0.5),
            "writes its total",
            (lambda: [run(lo, top_l, GOLD_M)], 0.7),
            "it says done",
            (lambda: [self.st("load", "done", GREEN_M)], 0.6),
        ])

        # ---------------- scene 4: guess, then the break ----------------
        self.steps("So what does daily totals hold for 6 November now? Pause and guess.", [
            (lambda: [glow(pa[0], GOLD_M, 1.02)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ra.append(trow(PXL, 1, GOLD_M))
        rep_a = report(PXL, "report: 11,949,314 cents", RED_M)
        self.steps("Two rows. The first attempt's row never went away, and the retry added another.", [
            (lambda: [*self.uncap(), FadeIn(ra[1], shift=0.1 * DOWN)], 0.6),
            "The first attempt's",
            (lambda: [pulse(ra[0], GOLD_M)], 0.7),
            "the retry added",
            (lambda: [pulse(ra[1], GOLD_M)], 0.7),
        ])
        self.steps("At minute 35, report adds up the day: 11,949,314 cents. Twice the truth.", [
            (lambda: [*self.set_clock("minute 35"), self.st("report", "running", BLUE_M)], 0.6),
            "adds up the day",
            (lambda: [FadeIn(rep_a, shift=0.1 * UP)], 0.6),
            "Twice the truth",
            (lambda: [self.st("report", "done", GREEN_M), glow(pa[0], RED_M, 1.02)], 0.8),
        ])
        self.steps("And look at the tasks. Every one is green. The dashboard is happy. The accountants are not.", [
            "Every one",
            (lambda: [LaggedStart(*[glow(tk[n][0], GREEN_M) for n in DX], lag_ratio=0.3)], 1.0),
            "The accountants",
            (lambda: [pulse(rep_a, RED_M)], 0.7),
        ])
        self.steps("A green night only says each task said done in the end. It doesn't say how many times it wrote.", [
            (lambda: self.cap("green means: each task said done, in the end"), 0.5),
            "how many times",
            (lambda: [*self.cap("not how many times it wrote"), pulse(ra[0], GOLD_M), pulse(ra[1], GOLD_M)], 0.8),
        ])
        wh = DashedVMobject(RoundedRectangle(corner_radius=0.2, width=PW + 0.3, height=PH + 0.3, stroke_color=PURPLE_M,
                                             stroke_width=2.5).move_to([PXL, PY, 0]), num_dashes=70)
        self.steps("You might be thinking: surely the orchestrator cleans up a failed attempt before it retries. "
                   "Let's be fair to it. It started the job, and it watched for done. That's all.", [
            (lambda: self.cap("undo the failed attempt, then retry?", PURPLE_M), 0.5),
            "It started the job",
            (lambda: [glow(tk["load"][0], BLUE_M)], 0.8),
            "watched for done",
            (lambda: [pulse(self.top, YELLOW_M)], 0.8),
        ])
        self.steps("The row went into the warehouse, a database built for questions over years of data. "
                   "The orchestrator can't see in there, so it can't undo anything. It can only run the job again.", [
            "The row went",
            (lambda: [Create(wh)], 0.8),
            "a database built",
            (lambda: self.cap("the warehouse: a database for questions over years of data", PURPLE_M), 0.5),
            "can't see in there",
            (lambda: self.cap("the orchestrator can't see in, so it can't undo", PURPLE_M), 0.5),
        ])
        self.steps("Then turn retries off? Then a network hiccup at three in the morning leaves the day missing, "
                   "and someone reruns it by hand. That's the same second run, with the same second row.", [
            (lambda: self.cap("retries off?", PURPLE_M), 0.4),
            "leaves the day",
            (lambda: self.cap("retries off: a missing day, then a rerun by hand", PURPLE_M), 0.5),
            "the same second run",
            (lambda: [*self.cap("a rerun by hand is the same second row", PURPLE_M), pulse(ra[1], RED_M)], 0.8),
        ])

        # ---------------- scene 5: the kitchen ----------------
        kbox = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=GREY_C, stroke_width=2).move_to(KC)
        ktitle = T("a kitchen", 24, GREY_B).move_to(KC + [0, PH / 2 - 0.36, 0])
        expd = T("expediter", 22, GOLD_M).move_to(KC + [-2.05, 0.45, 0])
        call1 = T("“steak!”", 22, YELLOW_M).move_to(KC + [-2.05, 0.0, 0])
        pl = plate(PLATE_C)
        s1 = steak(PLATE_C + [-0.12, 0.05, 0])
        cook1 = T("cook 1", 22).move_to(KC + [2.2, 0.3, 0])
        nodone = T("no “done!”", 20, RED_M).move_to(KC + [2.2, -0.15, 0])
        self.steps("Picture a restaurant kitchen. A cook puts a steak on a plate, and gets called away before shouting done.", [
            (lambda: [*self.uncap(), FadeOut(wh), FadeIn(kbox), FadeIn(ktitle)], 0.6),
            "A cook puts",
            (lambda: [FadeIn(cook1), FadeIn(pl)], 0.5),
            "a steak",
            (lambda: [FadeIn(s1, shift=0.4 * DOWN)], 0.5),
            "gets called away",
            (lambda: [cook1.animate.shift(0.4 * RIGHT).set_opacity(0.25), FadeIn(nodone)], 0.6),
        ])
        call2 = T("“steak, again!”", 22, YELLOW_M).move_to(call1)
        cook2 = T("cook 2", 22).move_to(KC + [2.2, -0.75, 0])
        s2 = steak(PLATE_C + [0.16, -0.17, 0])
        two = T("two steaks", 22, RED_M).move_to(KC + [0.25, -1.25, 0])
        self.steps("The person calling out the orders, the expediter, hears nothing, so she calls the steak again. "
                   "A second cook adds another steak to the same plate. The table gets two steaks.", [
            (lambda: [FadeIn(expd)], 0.5),
            "hears nothing",
            (lambda: [pulse(nodone, RED_M)], 0.6),
            "calls the steak",
            (lambda: [FadeIn(call2, scale=0.8)], 0.5),
            "A second cook",
            (lambda: [FadeIn(cook2)], 0.4),
            "another steak",
            (lambda: [FadeIn(s2, shift=0.4 * DOWN)], 0.5),
            "The table gets",
            (lambda: [FadeIn(two, shift=0.1 * UP)], 0.5),
        ])
        self.steps("Map it. The expediter is the orchestrator. Each cook is one attempt. "
                   "Shouting done is the success report. And the plate is the day's row in daily totals.", [
            "The expediter is",
            (lambda: [*self.cap("expediter = the orchestrator", GOLD_M), pulse(expd, GOLD_M), pulse(self.top, GOLD_M)], 0.8),
            "Each cook",
            (lambda: [*self.cap("each cook = one attempt", WHITE), pulse(cook2), glow(tk["load"][0], BLUE_M)], 0.8),
            "Shouting done",
            (lambda: [*self.cap("shouting “done!” = the success report", WHITE), pulse(nodone, RED_M), pulse(tk["load"][2], GREEN_M)], 0.8),
            "And the plate",
            (lambda: [*self.cap("the plate = the day's row in daily_totals", WHITE), glow(pl[0], YELLOW_M, 1.05),
                      pulse(ra[0], GOLD_M), pulse(ra[1], GOLD_M)], 0.9),
        ])
        newpl = VGroup(plate(PLATE_C), steak(PLATE_C + [0.0, -0.02, 0]))
        one = T("one plate, one steak", 22, GREEN_M).move_to(two)
        self.steps("Now the fix is easy to see. The second cook shouldn't add to the plate. She should replace it. "
                   "One plate, one steak, however many cooks.", [
            (lambda: self.uncap(), 0.4),
            "She should replace",
            (lambda: [FadeOut(VGroup(pl, s1, s2), shift=0.5 * UP), FadeOut(two)], 0.6),
            (lambda: [FadeIn(newpl, shift=0.3 * DOWN)], 0.6),
            "One plate",
            (lambda: [FadeIn(one, shift=0.1 * UP)], 0.6),
        ])

        # ---------------- scene 6: replace the day ----------------
        po = panel(PXR, "load replaces the day", BLUE_M)
        part = T("one slice per day: 2026-11-06", 18, BLUE_M).move_to([PXR, ROW_Y[2] - 0.05, 0])
        self.steps("In the warehouse, that means giving the table one slice per day, called a partition, "
                   "and letting load replace its day's slice instead of adding a row.", [
            (lambda: [FadeOut(VGroup(kbox, ktitle, expd, call2, cook1, cook2, nodone, newpl, one))], 0.6),
            (lambda: [FadeIn(po, shift=0.1 * DOWN)], 0.6),
            "one slice per day",
            (lambda: [FadeIn(part)], 0.5),
            "called a partition",
            (lambda: self.cap("partition: one slice of a table, here one day, read or replaced alone", BLUE_M), 0.5),
        ])
        ro = trow(PXR, 0, BLUE_M)
        x2 = tick(False, 0.2).move_to(x)
        self.steps("Run the same night again, crash and all. Attempt 1 writes the day. The machine dies.", [
            (lambda: [*self.uncap(), FadeOut(part), *self.set_clock("minute 15"),
                      *[self.st(n, "waiting", GREY_B) for n in ("load", "report")]], 0.6),
            "Attempt 1",
            (lambda: [self.st("load", "attempt 1", BLUE_M)], 0.4),
            (lambda: [run(lo, top_r, BLUE_M)], 0.7),
            (lambda: [FadeIn(ro, shift=0.1 * DOWN)], 0.4),
            "The machine dies",
            (lambda: [Create(x2), self.st("load", "failed: retry", RED_M)], 0.6),
        ])
        ro2 = trow(PXR, 0, BLUE_M)
        rep_o = report(PXR, f"report: {VALUE} cents", GREEN_M)
        self.steps(f"Attempt 2 replaces the day with the same total. One row. Report says {VALUE} cents, which is right.", [
            (lambda: [FadeOut(x2), *self.set_clock("minute 30"), self.st("load", "attempt 2", BLUE_M)], 0.5),
            (lambda: [run(lo, top_r, BLUE_M)], 0.6),
            (lambda: [swap(ro, ro2)], 0.6),
            "One row",
            (lambda: [self.st("load", "done", GREEN_M), pulse(ro2, BLUE_M)], 0.6),
            "Report says",
            (lambda: [*self.set_clock("minute 35"), self.st("report", "done", GREEN_M), FadeIn(rep_o, shift=0.1 * UP)], 0.6),
        ])
        ro = ro2
        self.steps("Same tasks, same crash, same retry. Only the write changed: add became replace.", [
            (lambda: [glow(pa[0], GOLD_M, 1.02), glow(po[0], BLUE_M, 1.02)], 0.9),
            "add became",
            (lambda: [*self.cap("add a row   →   replace the day", WHITE), pulse(pa[2], GOLD_M), pulse(po[2], BLUE_M)], 0.8),
        ])

        # ---------------- scene 7: the name and three rules ----------------
        self.steps("A task like that is called idempotent. Running it twice leaves the same result as running it once.", [
            "called idempotent",
            (lambda: self.cap("idempotent: running it twice leaves what running it once does", GREEN_M, 26), 0.6),
            "Running it twice",
            (lambda: [glow(po[0], GREEN_M, 1.02)], 0.8),
        ])
        self.steps("Three rules get you there. One: read a fixed input, the run's own day. Never the latest data, "
                   "and never the current time, because a rerun next month would read something else.", [
            "One: read",
            (lambda: [*self.cap("1. read a fixed input: the run's own day", TEAL_M), glow(stg[0], TEAL_M, 1.05)], 0.8),
            "Never the latest",
            (lambda: self.cap("1. never the latest data, never the current time", TEAL_M), 0.5),
        ])
        self.steps("Two: write by replacing that day, never by adding. Three: make the new result appear in one step, "
                   "old day or new, never half.", [
            (lambda: [*self.cap("2. write by replacing that day, never by adding", BLUE_M), glow(po[0], BLUE_M, 1.02)], 0.8),
            "Three: make",
            (lambda: [*self.cap("3. the new result appears in one step: old day or new, never half", BLUE_M), pulse(ro, BLUE_M)], 0.8),
        ])

        # ---------------- scene 8: a backfill is one more rerun ----------------
        self.steps("Rerunning past days, to fix a bug or fill a gap, is called a backfill.", [
            (lambda: self.uncap(), 0.4),
            "is called a backfill",
            (lambda: self.cap("backfill: running the tasks again for past days", GOLD_M), 0.6),
        ])
        ra.append(trow(PXL, 2, GOLD_M))
        ro3 = trow(PXR, 0, BLUE_M)
        self.steps("A week later, a backfill reruns 6 November. The appending table gains a third row: 17,923,971 cents. "
                   "The replacing table doesn't change.", [
            (lambda: [*self.set_top("a week later: a backfill reruns 6 November", GOLD_M), FadeOut(self.clk),
                      *[self.st(n, "rerun", BLUE_M) for n in DX]], 0.8),
            "The appending table",
            (lambda: [run(lo, top_l, GOLD_M), run(lo, top_r, BLUE_M)], 0.7),
            (lambda: [FadeIn(ra[2], shift=0.1 * DOWN), Transform(rep_a, report(PXL, "report: 17,923,971 cents", RED_M))], 0.6),
            "The replacing table",
            (lambda: [swap(ro, ro3), pulse(rep_o, GREEN_M), *[self.st(n, "done", GREEN_M) for n in DX]], 0.8),
        ])
        self.clk = None
        ro = ro3
        self.steps("A retry and a backfill are the same thing: running a task again.", [
            (lambda: self.cap("a retry and a backfill: both run the task again", WHITE), 0.6),
        ])

        # ---------------- scene 9: how bad, and the limit ----------------
        self.steps("How bad does this get? A demo runs 90 nights, where each load has a one in five chance "
                   "of crashing right after its write. 21 nights are hit.", [
            (lambda: [*self.set_top("the demo: 90 nights, a crash after the write 1 night in 5"), *self.uncap()], 0.6),
            "21 nights",
            (lambda: self.cap("21 nights hit", RED_M), 0.5),
        ])
        self.steps("The appending table ends 28 percent too high, and every run shows success.", [
            (lambda: [Transform(rep_a, report(PXL, "90 nights: 28% too high, 21 wrong days", RED_M)),
                      Transform(rep_o, report(PXR, "90 nights: 0 wrong days", GREEN_M))], 0.7),
            "every run",
            (lambda: [LaggedStart(*[glow(tk[n][0], GREEN_M) for n in DX], lag_ratio=0.3)], 1.0),
        ])
        self.steps("So turning retries on, by itself, made the numbers worse. Make the task safe first, then turn retries on.", [
            "Make the task",
            (lambda: self.cap("make the task safe first, then turn retries on", YELLOW_M), 0.6),
        ])
        self.steps("One limit. Some things can't be replaced, like an email to a shop. Once it's sent, it's sent. "
                   "Put a step like that in its own task, and keep a note of what it already did.", [
            "like an email",
            (lambda: self.cap("an email can't be replaced: once it's sent, it's sent", RED_M), 0.5),
            "Put a step",
            (lambda: self.cap("give it its own task, with a note of what it already sent", WHITE), 0.5),
        ])

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, how did a job that succeeded double the money? It succeeded twice, and it added both times.", [
            (lambda: [*self.set_top("orchestrator: the run for 6 November"), *self.uncap(),
                      Transform(rep_a, report(PXL, "report: 17,923,971 cents", RED_M)),
                      Transform(rep_o, report(PXR, f"report: {VALUE} cents", GREEN_M))], 0.7),
            "It succeeded twice",
            (lambda: [pulse(ra[0], GOLD_M), pulse(ra[1], GOLD_M)], 0.8),
        ])
        self.steps("A task that runs twice must leave what one run leaves. Replace the day; never add to it.", [
            (lambda: [glow(po[0], GREEN_M, 1.02)], 0.8),
            "Replace the day",
            (lambda: self.cap("replace the day; never add to it", YELLOW_M, 32), 0.6),
        ], after=0.6)
        bad = trow(PXR, 0, RED_M, "today's total")
        self.steps("One quick check. A load reads the newest payments, whatever day they're from, and replaces the run's own day. "
                   "You backfill 6 November. Is that safe? Pause and think.", [
            (lambda: self.cap("reads the newest payments, replaces the run's own day", WHITE), 0.5),
            "You backfill",
            (lambda: [*self.set_top("a backfill reruns 6 November", GOLD_M), glow(po[0], BLUE_M, 1.02)], 0.8),
            "Pause and think",
            (lambda: self.cap("safe? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. It replaces the right day, but with the wrong payments: today's. The input has to be the run's own day too.", [
            (lambda: [*self.uncap(), swap(ro, bad), Transform(rep_o, report(PXR, "6 November now holds today's money", RED_M)),
                      po[0].animate.set_stroke(RED_M)], 0.8),
            "The input has",
            (lambda: [*self.cap("a fixed input and a replaced output: then it's safe to run again", YELLOW_M), glow(stg[0], TEAL_M, 1.05)], 0.8),
        ], after=0.4)
        self.wait(2.0)
