from sfz import *

SAY.insert(0, (r"\bDAG\b", "dag"))
SAY.insert(0, (r"\bINSERT INTO\b", "insert into"))
SAY.insert(0, (r"\b6 November\b", "the sixth of November"))

DY, DW, DH = 2.4, 2.8, 1.05                 # the DAG
DX = {"extract": -4.3, "load": 0.0, "report": 4.3}
PY, PW, PH = -1.0, 6.2, 3.1                 # the two tables
PXL, PXR = -3.4, 3.4
ROW_Y = [-0.7, -1.15, -1.6]
ST_Y = -3.1
VALUE = "5,974,657"


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def run(a, b, color=YELLOW_M, run_time=0.7):
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.12))


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


def task(name, state="waiting", color=GREY_B):
    x = DX[name]
    idle = ManimColor(color).to_hex() == ManimColor(GREY_B).to_hex()
    r = RoundedRectangle(corner_radius=0.14, width=DW, height=DH, stroke_color=color, stroke_width=3)
    r.set_fill(BLACK if idle else fillc(color), 1).move_to([x, DY, 0])
    return VGroup(r, T(name, 28).move_to([x, DY + 0.2, 0]), T(state, 20, color).move_to([x, DY - 0.24, 0]))


def tstate(name, state, color):
    return T(state, 20, color).move_to([DX[name], DY - 0.24, 0])


def panel(x, title, sub, color):
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([x, PY, 0])
    return VGroup(r, T(title, 28, color).move_to([x, PY + PH / 2 - 0.36, 0]), M(sub, 18, GREY_B).move_to([x, PY + PH / 2 - 0.78, 0]))


def trow(x, k, color=WHITE):
    return M(f"2026-11-06   {VALUE}", 22, color).move_to([x, ROW_Y[k], 0])


def report(x, s, color):
    return T(s, 26, color).move_to([x, PY - PH / 2 + 0.38, 0])


def status(s, color=GREY_B):
    return T(s, 28, color).move_to([0, ST_Y, 0])


def clock(s):
    return T(s, 24, GOLD_M).move_to([5.4, 3.3, 0])


class IdempotentBackfill(Base):
    """batch-13, section 1 (with section 3's backfill): extract, load and report for 6 November. Load attempt 1 writes the
    day's total, 5,974,657 cents, then its worker dies before reporting success; the retry writes again. Appending with
    INSERT INTO gives two rows and a report of 11,949,314 (17,923,971 after a backfill); replacing the day's partition
    stays at 5,974,657."""

    def construct(self):
        self.title_card("Idempotent tasks: safe to run again", "retries, backfills and the day's partition")

        tk = {n: task(n) for n in DX}
        arr = VGroup(*[Arrow([DX[a] + DW / 2 + 0.08, DY, 0], [DX[b] - DW / 2 - 0.08, DY, 0], buff=0, stroke_width=3,
                             color=GREY_B, max_tip_length_to_length_ratio=0.12) for a, b in (("extract", "load"), ("load", "report"))])
        cap = left_at(T("settlement DAG, the run for 6 November", 24, GREY_B), -6.4, 3.3)
        self.steps("The nightly settlement DAG has three tasks: extract, load and report. Each starts when the one "
                   "before it finishes, and each run is for one day, here 6 November.", [
            (lambda: [LaggedStart(*[FadeIn(tk[n], shift=0.1 * RIGHT) for n in DX], lag_ratio=0.3)], 1.2),
            "Each starts",
            (lambda: [GrowArrow(arr[0]), GrowArrow(arr[1])], 0.7),
            "and each run",
            (lambda: [FadeIn(cap, shift=0.1 * DOWN)], 0.7),
        ])

        stg = chip("staging, 2026-11-06: 235 payments", TEAL_M, 20).move_to([DX["extract"] + 0.45, 1.15, 0])
        clk = clock("minute 5")
        self.steps("At minute 5, extract copies the day's 235 payments into a staging partition.", [
            (lambda: [FadeIn(clk), Transform(tk["extract"], task("extract", "running", BLUE_M))], 0.7),
            "copies the day's",
            (lambda: [FadeIn(stg, shift=0.1 * DOWN)], 0.7),
            (lambda: [Transform(tk["extract"], task("extract", "done", GREEN_M))], 0.5),
        ])

        pa = panel(PXL, "append", "INSERT INTO daily_totals", GOLD_M)
        po = panel(PXR, "overwrite the day", "replace partition 2026-11-06", BLUE_M)
        self.steps("Take two versions of load. One appends a row with INSERT INTO. "
                   "The other replaces the day's whole partition.", [
            "One appends",
            (lambda: [FadeIn(pa)], 0.8),
            "The other replaces",
            (lambda: [FadeIn(po)], 0.8),
        ])

        ra = [trow(PXL, 0)]
        ro = trow(PXR, 0)
        top_l = np.array([PXL, PY + PH / 2, 0])
        top_r = np.array([PXR, PY + PH / 2, 0])
        lo = np.array([DX["load"], DY - DH / 2, 0])
        self.steps(f"At minute 15, attempt 1 writes the day's total, {VALUE} cents. "
                   "So far both tables agree.", [
            (lambda: [Transform(clk, clock("minute 15")), Transform(tk["load"], task("load", "attempt 1", BLUE_M))], 0.7),
            "writes the day's",
            (lambda: [run(lo, top_l, GOLD_M, 0.7), run(lo, top_r, BLUE_M, 0.7)], 0.7),
            (lambda: [FadeIn(ra[0], shift=0.1 * DOWN), FadeIn(ro, shift=0.1 * DOWN)], 0.6),
        ])

        x = tick(False, 0.2).move_to([DX["load"] + DW / 2 - 0.3, DY + DH / 2 - 0.25, 0])
        st1 = status("the write is committed, but nobody heard it succeed", RED_M)
        self.steps("Then the worker dies before it reports success. The write is committed, but the orchestrator "
                   "never heard back, so it marks the attempt failed and retries.", [
            (lambda: [Create(x)], 0.5),
            "The write is",
            (lambda: [glow_text(ra[0], GOLD_M), glow_text(ro, BLUE_M), FadeIn(st1, shift=0.1 * UP)], 0.9),
            "so it marks",
            (lambda: [Transform(tk["load"], task("load", "failed: retry", RED_M))], 0.7),
        ])

        ra.append(trow(PXL, 1, GOLD_M))
        self.steps("Attempt 2 does the same work. The appending table now has two rows. "
                   "The other table just replaces its one row.", [
            (lambda: [FadeOut(x), FadeOut(st1), Transform(clk, clock("minute 30")),
                      Transform(tk["load"], task("load", "attempt 2", BLUE_M))], 0.7),
            (lambda: [run(lo, top_l, GOLD_M, 0.7), run(lo, top_r, BLUE_M, 0.7)], 0.7),
            "The appending table",
            (lambda: [FadeIn(ra[1], shift=0.1 * DOWN)], 0.6),
            "The other table",
            (lambda: [ro.animate(rate_func=there_and_back).set_opacity(0.15)], 0.9),
            (lambda: [Transform(tk["load"], task("load", "done", GREEN_M))], 0.5),
        ])

        rep_a = report(PXL, "report: 11,949,314 cents", RED_M)
        self.steps("Report sums the day. The appending table says 11,949,314 cents, twice the truth, "
                   "and every task shows green.", [
            (lambda: [Transform(clk, clock("minute 35")), Transform(tk["report"], task("report", "running", BLUE_M))], 0.6),
            "The appending table",
            (lambda: [FadeIn(rep_a, shift=0.1 * UP)], 0.7),
            "and every task",
            (lambda: [Transform(tk["report"], task("report", "done", GREEN_M)),
                      *[glow(tk[n][0], GREEN_M, 1.04) for n in ("extract", "load")]], 0.9),
        ])

        rep_o = report(PXR, f"report: {VALUE} cents", GREEN_M)
        self.steps(f"The other table says {VALUE}, which is right.", [
            (lambda: [FadeIn(rep_o, shift=0.1 * UP)], 0.7),
            (lambda: [glow(po[0], GREEN_M, 1.02)], 0.8),
        ])

        ra.append(trow(PXL, 2, GOLD_M))
        cap2 = left_at(T("a backfill reruns 6 November", 24, GOLD_M), -6.4, 3.3)
        self.steps("A week later, a backfill reruns 6 November. The append gains a third row. "
                   "The other table doesn't change.", [
            (lambda: [Transform(cap, cap2), FadeOut(clk), *[Transform(tk[n], task(n, "rerun", BLUE_M)) for n in DX]], 0.8),
            "The append gains",
            (lambda: [run(lo, top_l, GOLD_M, 0.6), run(lo, top_r, BLUE_M, 0.6)], 0.6),
            (lambda: [FadeIn(ra[2], shift=0.1 * DOWN), Transform(rep_a, report(PXL, "report: 17,923,971 cents", RED_M))], 0.7),
            "The other table doesn't",
            (lambda: [glow_text(ro, GREEN_M), glow_text(rep_o, GREEN_M),
                      *[Transform(tk[n], task(n, "done", GREEN_M)) for n in DX]], 0.9),
        ])

        idem = chip("idempotent: running it twice = running it once", GREEN_M, 24).move_to([0, ST_Y, 0])
        self.steps("That task is idempotent: running it twice leaves the same result as running it once.", [
            (lambda: [FadeIn(idem, shift=0.15 * UP)], 0.8),
            "running it twice",
            (lambda: [glow(po[0], GREEN_M, 1.02)], 0.9),
        ])

        r1 = T("read a fixed input: the run's own day", 22, TEAL_M).move_to([DX["extract"] + 0.45, 1.15, 0])
        r2 = T("write by replacing that day, never by adding", 22, BLUE_M)
        r2.move_to([3.3, 1.15, 0])
        self.steps("Two rules get you there. Read a fixed input, the run's own day, never the latest data. "
                   "And write by replacing that day, never by adding to it.", [
            "Read a fixed input",
            (lambda: [FadeOut(stg), FadeIn(r1, shift=0.1 * DOWN)], 0.7),
            "And write by",
            (lambda: [FadeIn(r2, shift=0.1 * DOWN)], 0.7),
            (lambda: [ra[1].animate.set_opacity(0.35), ra[2].animate.set_opacity(0.35)], 0.6),
        ])

        rule = chip("make each task replace its own day, and reruns are safe", GREEN_M, 24).move_to([0, ST_Y, 0])
        self.steps("Retries and backfills both just run a task again. "
                   "Make each task replace its own day, and running it again is safe.", [
            (lambda: [*[glow(tk[n][0], BLUE_M, 1.04) for n in DX]], 0.9),
            "Make each task",
            (lambda: [FadeOut(idem), FadeIn(rule, shift=0.15 * UP)], 0.8),
        ])
        self.wait(0.6)


def glow_text(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.08)
