from sfz import *

SAY.insert(0, (r"\bDataFrame\b", "data frame"))

CODE = ['read("payments")', '.where(CAPTURED)', '.withColumn(euros)', '.groupBy(merchant).sum()', '.collect()']
CODE_Y, STATUS_Y = 3.05, 2.35
YS = [0.45, -0.45, -1.35, -2.25]          # one lane per partition
FX, FW = -5.7, 1.2                         # input files
T1X, T1W = -2.75, 3.3                      # stage 1 tasks
T2X, T2W = 2.35, 2.3                       # stage 2 tasks
DRV = np.array([5.45, -0.9, 0])
TH = 0.6
LAB_Y = 1.25


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


def rbox(x, y, w, label, color=WHITE, size=15, mono=False):
    r = RoundedRectangle(corner_radius=0.1, width=w, height=TH, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK if color == WHITE else fillc(color), 1).move_to([x, y, 0])
    return VGroup(r, (M if mono else T)(label, size, WHITE).move_to([x, y + 0.04, 0]))


def prog(x, w, y, frac, color=BLUE_M):
    ww = max((w - 0.2) * frac, 0.001)
    return Rectangle(width=ww, height=0.07, stroke_width=0).set_fill(color, 1).move_to([x - (w - 0.2) / 2 + ww / 2, y - 0.2, 0])


def status(s, color=GREY_A):
    return T(s, 22, color).move_to([0, STATUS_Y, 0])


class SparkStages(Base):
    """batch-06, sections 0 to 3: the settlement report (read 4 files, where CAPTURED, euros, groupBy merchant, sum,
    collect). Transformations only build a plan; collect runs it. Narrow steps chain in one task per file (stage 1, 4
    tasks); groupBy needs a shuffle (Exchange), which starts stage 2 (4 shuffle partitions in the lesson's demos, 200 by
    default): one job, two stages, eight tasks. Task 2 dies mid-file and is rerun from its lineage: file 2."""

    def construct(self):
        self.title_card("Spark jobs, stages and tasks", "a lazy plan, cut into stages at every shuffle")

        code = VGroup(*[chip(c, GREY_B, 15, mono=True) for c in CODE]).arrange(RIGHT, buff=0.18).move_to([0, CODE_Y, 0])
        self.steps("The nightly settlement report sums each merchant's captured payments. In Spark it's a chain of steps "
                   "on a DataFrame, a table split into partitions.", [
            (lambda: [FadeIn(code[0], shift=0.1 * DOWN)], 0.7),
            "In Spark",
            (lambda: [glow(code[0][0], BLUE_M, 1.05)], 0.9),
        ])

        st = status("plan only: nothing has run yet")
        self.steps("Keep captured payments, convert cents to euros, group by merchant, sum. Each line returns at once, "
                   "because Spark only writes down a plan.", [
            (lambda: [FadeIn(code[1], shift=0.1 * DOWN)], 0.6),
            "convert cents",
            (lambda: [FadeIn(code[2], shift=0.1 * DOWN)], 0.6),
            "group by",
            (lambda: [FadeIn(code[3], shift=0.1 * DOWN)], 0.6),
            "Each line returns",
            (lambda: [FadeIn(st)], 0.7),
        ])

        drv = box("driver", BLUE_M, w=1.9, h=0.8, size=24).move_to(DRV)
        self.steps("An action, like collect, makes it run. The driver, the process running your program, "
                   "turns the plan into tasks.", [
            (lambda: [FadeIn(code[4], shift=0.1 * DOWN)], 0.6),
            (lambda: [code[4][0].animate.set_stroke(GOLD_M).set_fill(GOLD_M, 0.25),
                      Transform(st, status("collect() is an action: now Spark runs the plan", GOLD_M))], 0.8),
            "The driver",
            (lambda: [FadeIn(drv, shift=0.1 * LEFT)], 0.7),
            "turns the plan",
            (lambda: [glow(drv[0], BLUE_M, 1.06)], 0.8),
        ])

        files = [rbox(FX, y, FW, f"file {i}", GREY_B, 15, mono=True) for i, y in enumerate(YS)]
        t1 = [rbox(T1X, y, T1W, f"task {i}: filter, euros, sums") for i, y in enumerate(YS)]
        fa = [Arrow([FX + FW / 2, y, 0], [T1X - T1W / 2, y, 0], buff=0.08, stroke_width=2.5, color=GREY_B,
                    max_tip_length_to_length_ratio=0.25) for y in YS]
        self.steps("Four files make four partitions. Filtering and converting are narrow: "
                   "each output row needs only its own partition.", [
            (lambda: [Transform(st, status("narrow steps: one partition in, one partition out")),
                      LaggedStart(*[FadeIn(f, shift=0.1 * RIGHT) for f in files], lag_ratio=0.15)], 1.0),
            "Filtering and",
            (lambda: [*[glow(code[i][0], TEAL_M, 1.05) for i in (1, 2)]], 0.8),
            "each output row",
            (lambda: [*[GrowArrow(a) for a in fa]], 0.6),
        ])

        self.steps("So Spark chains them in one task per partition: read a file, filter, convert, add to a sum per "
                   "merchant, with nothing written in between.", [
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.1 * RIGHT) for t in t1], lag_ratio=0.15)], 1.0),
            "read a file",
            (lambda: [*[travel(a, BLUE_M, 0.6) for a in fa]], 0.6),
            (lambda: [*[glow(t[0], BLUE_M, 1.03) for t in t1]], 0.9),
        ])

        m42 = [M("m-42: partial", 13, GOLD_M).move_to([0.05, y, 0]) for y in YS]
        self.steps("Grouping is different. Merchant 42's total needs rows from all four files. That's a wide step.", [
            (lambda: [glow(code[3][0], GOLD_M, 1.05)], 0.7),
            "Merchant 42's",
            (lambda: [LaggedStart(*[FadeIn(m) for m in m42], lag_ratio=0.15), *[t[0].animate.set_stroke(GOLD_M) for t in t1]], 1.0),
            "That's a wide",
            (lambda: [Transform(st, status("wide step: needs rows from every partition", GOLD_M))], 0.7),
        ])

        t2 = [rbox(T2X, y, T2W, f"task {4 + i}: totals, part {i}") for i, y in enumerate(YS)]
        shuf = VGroup(*[Line([T1X + T1W / 2 + 0.05, a, 0], [T2X - T2W / 2 - 0.05, b, 0], stroke_width=1.5, color=GREY_D)
                        for a in YS for b in YS])
        da = [Arrow([T2X + T2W / 2, y, 0], DRV + (y - DRV[1]) * 0.25 * UP + 0.95 * LEFT, buff=0.08, stroke_width=2,
                    color=GREY_B, max_tip_length_to_length_ratio=0.12) for y in YS]
        self.steps("So each task writes its sums to disk in four parts, by merchant, and each task on the other side "
                   "fetches one part from all four. That's the shuffle.", [
            (lambda: [FadeOut(VGroup(*m42)), *[t[0].animate.set_stroke(WHITE) for t in t1]], 0.5),
            "So each task writes",
            (lambda: [Create(shuf)], 1.0),
            "and each task on",
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.1 * LEFT) for t in t2], lag_ratio=0.15),
                      *[GrowArrow(a) for a in da]], 1.0),
            "That's the shuffle",
            (lambda: [shuf.animate.set_stroke(PURPLE_M, 2), Transform(st, status("the shuffle", PURPLE_M))], 0.7),
        ])

        s1 = DashedVMobject(Rectangle(width=5.7, height=3.75).move_to([-3.65, -0.9, 0]), num_dashes=60).set_stroke(TEAL_M, 2)
        s2 = DashedVMobject(Rectangle(width=2.75, height=3.75).move_to([T2X, -0.9, 0]), num_dashes=36).set_stroke(TEAL_M, 2)
        l1 = left_at(T("stage 1", 22, TEAL_M), -6.5, LAB_Y)
        l2 = left_at(T("stage 2", 22, TEAL_M), T2X - 1.375, LAB_Y)
        ls = T("shuffle", 20, PURPLE_M).move_to([(-0.8 + T2X - 1.375) / 2, LAB_Y, 0])
        self.steps("No total can finish until all of that is written, so the shuffle cuts the job into two stages.", [
            (lambda: [*[glow(t[0], PURPLE_M, 1.03) for t in t1]], 0.9),
            "so the shuffle cuts",
            (lambda: [Create(s1), Create(s2), FadeIn(l1), FadeIn(l2), FadeIn(ls)], 1.2),
        ])

        cnt = status("1 job, 2 stages, 8 tasks", TEAL_M)
        self.steps("Each stage runs one task per partition: four for the files, and four for the shuffle, set to four "
                   "here instead of the default 200. One job, two stages, eight tasks.", [
            (lambda: [Transform(l1, left_at(T("stage 1: 4 tasks", 22, TEAL_M), -6.5, LAB_Y))], 0.7),
            "and four for",
            (lambda: [Transform(l2, left_at(T("stage 2: 4 tasks", 22, TEAL_M), T2X - 1.375, LAB_Y))], 0.7),
            "One job",
            (lambda: [Transform(st, cnt)], 0.7),
        ])

        pg = [prog(T1X, T1W, y, 0.001) for y in YS]
        self.steps("Stage 1 starts. Halfway through, task 2's machine dies, and its partial sums are lost.", [
            (lambda: [*[FadeIn(p) for p in pg], Transform(st, status("stage 1 running"))], 0.3),
            (lambda: [*[Transform(pg[i], prog(T1X, T1W, YS[i], f)) for i, f in enumerate((0.55, 0.5, 0.45, 0.6))],
                      *[travel(a, BLUE_M, 1.2) for a in fa]], 1.4),
            "task 2's machine",
            (lambda: [t1[2][0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1),
                      Transform(t1[2][1], T("task 2: its machine died", 15, RED_M).move_to([T1X, YS[2] + 0.04, 0]))], 0.6),
            "and its partial",
            (lambda: [Transform(pg[2], prog(T1X, T1W, YS[2], 0.001, RED_M))], 0.6),
        ])

        lin = status("lineage: file 2 → filter → euros → sums", GOLD_M)
        self.steps("Spark kept no copy. It knows how that partition was made, read file 2, filter, convert, sum, "
                   "and runs exactly that again elsewhere.", [
            (lambda: [Transform(st, lin)], 0.8),
            "read file 2",
            (lambda: [glow(files[2][0], GOLD_M, 1.06)], 0.7),
            (lambda: [glow(t1[2][0], GOLD_M, 1.03)], 0.7),
            "and runs exactly",
            (lambda: [t1[2][0].animate.set_stroke(GOLD_M).set_fill(BLACK, 1),
                      Transform(t1[2][1], T("task 2, attempt 2", 15, WHITE).move_to([T1X, YS[2] + 0.04, 0]))], 0.6),
            (lambda: [travel(fa[2], GOLD_M, 1.0), Transform(pg[2], prog(T1X, T1W, YS[2], 0.5, GOLD_M)),
                      *[Transform(pg[i], prog(T1X, T1W, YS[i], 0.85)) for i in (0, 1, 3)]], 1.2),
        ])

        self.steps("No other task is touched. That's safe because a task's output depends only on its input.", [
            (lambda: [*[Transform(pg[i], prog(T1X, T1W, YS[i], 1, GREEN_M)) for i in (0, 1, 3)],
                      *[t1[i][0].animate.set_stroke(GREEN_M) for i in (0, 1, 3)]], 1.0),
            "That's safe",
            (lambda: [Transform(pg[2], prog(T1X, T1W, YS[2], 1, GREEN_M)), t1[2][0].animate.set_stroke(GREEN_M)], 1.0),
        ])

        pg2 = [prog(T2X, T2W, y, 0.001) for y in YS]
        self.steps("Then stage 2 fetches its parts, adds them up, and the driver gets the totals.", [
            (lambda: [Transform(st, status("stage 2 running")), *[FadeIn(p) for p in pg2]], 0.4),
            (lambda: [LaggedStart(*[travel(l, PURPLE_M, 0.7) for l in shuf], lag_ratio=0.04)], 1.4),
            "adds them up",
            (lambda: [*[Transform(pg2[i], prog(T2X, T2W, YS[i], 1, GREEN_M)) for i in range(4)],
                      *[t[0].animate.set_stroke(GREEN_M) for t in t2]], 0.9),
            "and the driver",
            (lambda: [*[travel(a, GREEN_M, 0.7) for a in da]], 0.7),
            (lambda: [glow(drv[0], GREEN_M, 1.06), Transform(st, status("500 merchant totals, back at the driver", GREEN_M))], 0.8),
        ])

        self.steps("Spark plans lazily, chains narrow steps in one task per partition, and cuts a stage at every "
                   "shuffle. A lost task just runs again from its inputs.", [
            (lambda: [glow(code[4][0], GOLD_M, 1.05)], 0.8),
            "chains narrow",
            (lambda: [*[glow(t[0], BLUE_M, 1.03) for t in t1]], 0.9),
            "and cuts a stage",
            (lambda: [shuf.animate(rate_func=there_and_back).set_stroke(PURPLE_M, 4)], 0.9),
            "A lost task",
            (lambda: [glow(t1[2][0], GOLD_M, 1.04), glow(files[2][0], GOLD_M, 1.06)], 0.9),
        ])
        self.wait(0.6)
