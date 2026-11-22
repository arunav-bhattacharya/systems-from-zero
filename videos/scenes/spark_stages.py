from sfz import *

SAY.insert(0, (r"\bMapReduce\b", "map reduce"))


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    # labelled slots: put() swaps whatever sat in a slot for a new mobject
    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0]))

    def mid(self, mob, x=0.0, y=0.0):
        return self.put("mid", mob.move_to([x, y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def frame_box(x, y, w, h, color, a=0.14):
    return RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color, a), 1).move_to([x, y, 0])


# ---- the one picture ----
Q_Y = 3.3
SLAB_Y = 2.6                                  # stage labels
YS = [1.75, 0.65, -0.45, -1.55]
FX, FWD = -5.75, 1.3                          # files
T1X, T1W = -3.0, 2.6                         # stage 1 tasks
T2X, T2W = 2.65, 2.4                          # stage 2 tasks
DX, DW, DH = 5.65, 1.35, 1.4                  # driver
BH = 0.78
CNT_Y, BAR_Y, CAP_Y = -2.55, -2.95, -3.35
OWN42 = 1                                     # the stage 2 task drawn as owning shop 42 (a picture, not computed)


class SparkStages(Base):
    """batch-06, section 2. The report: 4 files, keep CAPTURED, sum per shop, collect(). One stage 1 task per file;
    narrow steps chain inside a task. Shop 42 is in every file: a wide step. The kitchen's pass: hash(merchant_id)
    mod 4, written to local disk, 4 x 4 = 16 blocks fetched; nothing after the pass starts until all before it finish.
    Job, stage, task: 1 job, 2 stages, 8 tasks. The plan's Exchange. 200 by default; AQE: 2 jobs, 5 tasks. Check."""

    def cnt(self, s, color=WHITE):
        return self.put("cnt", fit(T(s, 26, color), 12.0).move_to([0, CNT_Y, 0]))

    def construct(self):
        self.lab = {}
        self.title_card("Everything meets at the pass", "Spark jobs, stages and tasks")

        files = [VGroup(frame_box(FX, y, FWD, BH, GREY_B), T(f"file {i + 1}", 20).move_to([FX, y, 0])) for i, y in enumerate(YS)]
        driver = VGroup(frame_box(DX, 0.1, DW, DH, WHITE, 0.0).set_fill(BLACK, 1), T("driver", 22).move_to([DX, 0.3, 0]),
                        M("collect()", 16, GREY_B).move_to([DX, -0.15, 0]))
        t1 = [frame_box(T1X, y, T1W, BH, BLUE_M) for y in YS]
        t1l = [left_at(T(f"task {i + 1}", 20), T1X - T1W / 2 + 0.2, y) for i, y in enumerate(YS)]
        t2 = [frame_box(T2X, y, T2W, BH, TEAL_M) for y in YS]
        t2l = [left_at(T(f"task {i + 5}", 20), T2X - T2W / 2 + 0.2, y) for i, y in enumerate(YS)]
        f2t = [Arrow([FX + FWD / 2 + 0.05, y, 0], [T1X - T1W / 2 - 0.05, y, 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.25) for y in YS]

        # ---------------- scene 1: how many tasks? ----------------
        self.steps("Spark, a program that runs data jobs across many machines, splits its work into pieces called tasks. Here's a "
                   "nightly report.", [
            (lambda: self.cap("Spark: a program that runs data jobs across many machines", WHITE), 0.6),
            "splits its work",
            (lambda: self.cap("its pieces of work: tasks"), 0.5),
            "Here's a",
            (lambda: self.put("q", fit(chip("read 4 files, keep CAPTURED, sum per shop, collect()", YELLOW_M, 22), 13.0).move_to([0, Q_Y, 0])), 0.7),
        ])
        self.steps("Read four files of payments, keep the captured ones, add up the amounts for each shop, and collect the result.", [
            "Read four files",
            (lambda: [LaggedStart(*[FadeIn(f, shift=0.1 * RIGHT) for f in files], lag_ratio=0.2)], 1.0),
            "and collect",
            (lambda: [FadeIn(driver, shift=0.1 * LEFT)], 0.6),
        ])
        self.steps("Spark gives each file its own task. After the grouping, it's set to make four pieces. How many tasks run in "
                   "total? Pause and guess.", [
            "each file its own",
            (lambda: self.cap("one task per file; after the grouping: 4 pieces"), 0.5),
            "Pause and guess",
            (lambda: self.cap("how many tasks in total? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Hold on to your guess. Let's cook it.", [(lambda: self.drop("cap"), 0.4)])

        # ---------------- scene 2: each cook at their own station ----------------
        self.steps("Start with the files. Four files, four tasks, one per file. Each task reads its file, keeps the captured "
                   "payments, and adds up the amounts per shop.", [
            "four tasks",
            (lambda: [LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(b), FadeIn(l)) for a, b, l in zip(f2t, t1, t1l)], lag_ratio=0.2)], 1.2),
            "Each task reads",
            (lambda: self.cap("each task: read its file, keep CAPTURED, sum per shop", WHITE), 0.5),
        ])
        steps_txt = [T(s, 16, GREY_B) for s in ("read", "filter", "sum")]
        chain = VGroup(*steps_txt).arrange(RIGHT, buff=0.16)
        left_at(chain, T1X + T1W / 2 + 0.25, YS[1])
        self.steps("Task two can filter file two without looking at anything else.", [
            (lambda: [glow(t1[1], YELLOW_M), glow(files[1][0], YELLOW_M)], 0.9),
            (lambda: [*[f.animate.set_opacity(0.3) for k, f in enumerate(files) if k != 1]], 0.5),
        ])
        self.steps("So the steps run back to back inside one task. Read a batch of rows, filter it, add it to a running sum per "
                   "shop, then the next batch. Nothing in between gets written down.", [
            (lambda: [*[f.animate.set_opacity(1) for f in files], FadeIn(chain)], 0.6),
            "Read a batch",
            (lambda: [Indicate(steps_txt[0], color=YELLOW_M, scale_factor=1.3)], 0.5),
            "filter it",
            (lambda: [Indicate(steps_txt[1], color=YELLOW_M, scale_factor=1.3)], 0.5),
            "add it to",
            (lambda: [Indicate(steps_txt[2], color=YELLOW_M, scale_factor=1.3)], 0.5),
            "then the next",
            (lambda: [LaggedStart(*[Indicate(s, color=YELLOW_M, scale_factor=1.3) for s in steps_txt], lag_ratio=0.3)], 1.0),
            "Nothing in between",
            (lambda: self.cap("one task, back to back: nothing in between written down"), 0.5),
        ])
        self.steps("Steps like these, where each piece needs only its own input, are called narrow.", [
            (lambda: [FadeOut(chain), *self.cap("narrow: each piece needs only its own input", BLUE_M)], 0.6),
        ])

        # ---------------- scene 3: shop 42 is everywhere ----------------
        tok = [chip("42", YELLOW_M, 18).move_to([T1X - 0.05, y, 0]) for y in YS]
        qms = [T("?", 28, RED_M).move_to([T1X + T1W / 2 - 0.25, y, 0]) for y in YS]
        self.steps("But here's the catch. Shop 42 sold things in all four files. So each task ends up with its own part of shop "
                   "42's total.", [
            "Shop 42",
            (lambda: [LaggedStart(*[FadeIn(t, scale=0.5) for t in tok], lag_ratio=0.2), *self.cap("shop 42 sold things in all four files", WHITE)], 1.0),
            "its own part",
            (lambda: self.cap("each task: its own part of shop 42's total"), 0.5),
        ])
        self.steps("Four part totals, in four places, and nobody has the real one. Adding up per shop is a wide step: the answer "
                   "for one shop needs rows from every piece.", [
            (lambda: [*[FadeIn(q) for q in qms], *self.cap("four part totals; nobody has the real one", RED_M)], 0.6),
            "wide step",
            (lambda: [*[FadeOut(q) for q in qms], *self.cap("wide: one shop's answer needs rows from every piece", GOLD_M)], 0.6),
        ])

        # ---------------- scene 4: the pass ----------------
        passz = DashedLine([-0.2, YS[0] + 0.6, 0], [-0.2, YS[-1] - 0.6, 0], dash_length=0.12, color=GREY_B, stroke_width=2)
        pass_l = T("the pass", 22, YELLOW_M).move_to([-0.2, SLAB_Y, 0])
        self.steps("A restaurant kitchen has the same problem. The steak comes off the grill. The fries come out of the fryer. Each "
                   "cook works their own station, and that's the narrow part.", [
            (lambda: self.cap("a restaurant kitchen: grill, fryer, each cook at a station", WHITE), 0.6),
            "Each cook",
            (lambda: [*[glow(b, BLUE_M, 1.03) for b in t1], *self.cap("each cook at their own station: the narrow part", BLUE_M)], 0.8),
        ])
        self.steps("But a plate can't go out until its steak and its fries meet at the pass, the counter where each order comes "
                   "together. Nobody wants the fries delivered to table nine while the steak is still on the grill.", [
            "meet at the pass",
            (lambda: [Create(passz), FadeIn(pass_l), *self.cap("the pass: the counter where each order comes together", YELLOW_M)], 0.8),
            "Nobody wants",
            (lambda: self.cap("fries at table nine, steak still on the grill: nobody wants that"), 0.5),
        ])
        self.steps("Let's map that. The stations are the tasks. The pass is the shuffle. And a finished plate is one shop's total.", [
            "The stations",
            (lambda: [*self.cap("station = task"), *[glow(b, BLUE_M, 1.03) for b in t1]], 0.6),
            "The pass is",
            (lambda: [*self.cap("the pass = the shuffle"), swap(pass_l, T("the shuffle", 22, YELLOW_M).move_to(pass_l))], 0.6),
            "And a finished",
            (lambda: [*self.cap("a finished plate = one shop's total"),
                      LaggedStart(*[AnimationGroup(FadeIn(b), FadeIn(l)) for b, l in zip(t2, t2l)], lag_ratio=0.15)], 1.0),
        ])
        self.stamp("s5")

        # ---------------- scene 5: how the pass works ----------------
        parts = [VGroup(*[Square(0.16, stroke_color=TEAL_M, stroke_width=2).set_fill(fillc(TEAL_M, 0.5), 1) for _ in range(4)])
                 .arrange(RIGHT, buff=0.04).move_to([T1X + T1W / 2 - 0.55, y, 0]) for y in YS]
        lines = VGroup(*[Line([T1X + T1W / 2 + 0.05, YS[i], 0], [T2X - T2W / 2 - 0.05, YS[j], 0], stroke_width=1.6, color=GREY_C)
                         for i in range(4) for j in range(4)])
        self.steps("Here's how the pass works. Each task splits its part totals into four parts, one for each task of the next step.", [
            "splits",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.05 * RIGHT) for p in parts], lag_ratio=0.2), passz.animate.set_opacity(0.3)], 1.0),
        ])
        self.steps("It picks the part by hashing the shop number and keeping the remainder after dividing by four, the same trick "
                   "MapReduce used. It writes the parts to its own machine's disk.", [
            (lambda: self.cap("which part: hash(merchant_id) mod 4", WHITE), 0.6),
            "It writes",
            (lambda: [*self.cap("written to the task's own machine's disk"), *[Indicate(p, color=TEAL_M, scale_factor=1.15) for p in parts]], 0.8),
        ])
        self.steps("Then each next-step task fetches its part from every earlier task. Four times four, sixteen blocks.", [
            "fetches",
            (lambda: [Create(lines, lag_ratio=0.05)], 1.6),
            "sixteen",
            (lambda: self.cap("4 × 4 = 16 blocks", WHITE), 0.5),
        ])
        total = chip("42: total", YELLOW_M, 18).move_to([T2X + 0.5, YS[OWN42], 0])
        self.steps("All four pieces of shop 42 now meet in one task, which adds them up.", [
            (lambda: [LaggedStart(*[t.animate.move_to([T2X + 0.5, YS[OWN42], 0]) for t in tok], lag_ratio=0.15)], 1.2),
            (lambda: [*[FadeOut(t) for t in tok], FadeIn(total)], 0.4),
            (lambda: self.cap("shop 42: four pieces, one task", YELLOW_M), 0.4),
        ])
        cut = DashedLine([-0.2, SLAB_Y - 0.3, 0], [-0.2, YS[-1] - 0.6, 0], dash_length=0.12, color=RED_M, stroke_width=3)
        self.steps("And notice the wait. No task after the pass can start until every task before it has finished writing. A plate "
                   "waits for its slowest dish. So the shuffle cuts the work in two.", [
            "No task after",
            (lambda: [*[b.animate.set_opacity(0.3) for b in t2], *self.cap("nothing after the pass starts until everything before it is done")], 0.6),
            "A plate waits",
            (lambda: [glow(t1[3], RED_M, 1.04)], 0.9),
            "So the shuffle",
            (lambda: [*[b.animate.set_opacity(1) for b in t2], Create(cut), *self.cap("the shuffle cuts the work in two", WHITE)], 0.7),
        ])

        # ---------------- scene 6: job, stage, task ----------------
        fr1 = DashedVMobject(RoundedRectangle(corner_radius=0.15, width=(T1X + T1W / 2 + 0.15) - (FX - FWD / 2 - 0.15),
                                              height=YS[0] - YS[-1] + BH + 0.35, stroke_color=BLUE_M, stroke_width=2),
                             num_dashes=70).move_to([((T1X + T1W / 2 + 0.15) + (FX - FWD / 2 - 0.15)) / 2, (YS[0] + YS[-1]) / 2, 0])
        fr2 = DashedVMobject(RoundedRectangle(corner_radius=0.15, width=T2W + 0.3, height=YS[0] - YS[-1] + BH + 0.35,
                                              stroke_color=TEAL_M, stroke_width=2), num_dashes=50).move_to([T2X, (YS[0] + YS[-1]) / 2, 0])
        s1l = T("stage 1", 22, BLUE_M).move_to([fr1.get_center()[0], SLAB_Y, 0])
        s2l = T("stage 2", 22, TEAL_M).move_to([T2X, SLAB_Y, 0])
        to_drv = [Arrow([T2X + T2W / 2 + 0.05, y, 0], [DX - DW / 2 - 0.05, 0.1 + (y - 0.1) * 0.25, 0], buff=0, stroke_width=2.5,
                        color=GREY_B, max_tip_length_to_length_ratio=0.2) for y in YS]
        self.steps("Now the three words. A job is everything one action runs; here, collect.", [
            (lambda: [FadeOut(cut), *self.cap("job: everything one action runs (here, collect)", WHITE)], 0.6),
            "here, collect",
            (lambda: [glow(driver[0], WHITE, 1.05)], 0.8),
        ])
        self.steps("A stage is a stretch of narrow steps between shuffles. And a task is one piece of data going through one stage.", [
            "A stage",
            (lambda: [Create(fr1), Create(fr2), FadeIn(s1l), FadeIn(s2l), *self.cap("stage: narrow steps between shuffles", WHITE)], 1.0),
            "And a task",
            (lambda: [*self.cap("task: one piece of data through one stage", WHITE), glow(t1[2], YELLOW_M), glow(t2[2], YELLOW_M)], 0.8),
        ])
        self.steps("Count them. One job. Two stages. Four tasks, plus four tasks. Eight. Did you guess eight?", [
            "One job",
            (lambda: self.cnt("1 job"), 0.4),
            "Two stages",
            (lambda: self.cnt("1 job  ·  2 stages"), 0.4),
            "Four tasks,",
            (lambda: [LaggedStart(*[Indicate(l, color=BLUE_M, scale_factor=1.2) for l in t1l], lag_ratio=0.15)], 0.8),
            "plus four",
            (lambda: [LaggedStart(*[Indicate(l, color=TEAL_M, scale_factor=1.2) for l in t2l], lag_ratio=0.15)], 0.8),
            "Eight",
            (lambda: [*self.cnt("1 job  ·  2 stages  ·  4 + 4 = 8 tasks", GREEN_M), *[GrowArrow(a) for a in to_drv]], 0.6),
            "Did you guess",
            (lambda: self.cap("did you guess 8?", YELLOW_M), 0.4),
        ])
        self.stamp("poster")
        self.steps("So the rule: stages are the number of shuffles plus one. Tasks are the input pieces plus the pieces of each shuffle.", [
            (lambda: self.cap("stages = shuffles + 1", WHITE), 0.5),
            "Tasks are",
            (lambda: self.cap("tasks = input pieces + the pieces of each shuffle", WHITE), 0.5),
        ])

        # ---------------- scene 7: read it in the plan ----------------
        shade = Rectangle(width=15, height=6.2, stroke_width=0).set_fill(BLACK, 0.85).move_to([0, 0.5, 0]).set_z_index(6)
        code = VGroup(
            M('payments.where(col("status").equalTo("CAPTURED"))', 19, WHITE),
            M('    .groupBy("merchant_id").agg(sum("amount_cents"))', 19, WHITE),
            M('    .collectAsList()', 19, WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        plan = VGroup(
            M("*(2) HashAggregate(keys=[merchant_id], functions=[sum(amount_cents)])", 17, TEAL_M),
            M("+- Exchange hashpartitioning(merchant_id, 4)", 17, YELLOW_M),
            M("   +- *(1) HashAggregate(keys=[merchant_id], functions=[partial_sum(amount_cents)])", 17, BLUE_M),
            M("      +- *(1) Filter (isnotnull(status) AND (status = CAPTURED))", 17, BLUE_M),
            M("         +- FileScan parquet [merchant_id,status,amount_cents]", 17, GREY_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        for k in range(1, 5):
            plan[k].shift(RIGHT * 0.3 * (k - 1))
        for k in (1, 2):
            code[k].shift(RIGHT * 0.45)
        panel = VGroup(T("Kotlin", 18, GREY_B), code, T("the plan it prints (trimmed), read from the bottom", 18, GREY_B), plan)
        panel.arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        fit(panel, 12.6).move_to([0, 0.35, 0])
        bg = RoundedRectangle(corner_radius=0.15, width=panel.width + 0.5, height=panel.height + 0.45, stroke_color=GREY_C,
                              stroke_width=2).set_fill("#0b0d10", 1).move_to(panel).set_z_index(7)
        panel.set_z_index(8)
        self.steps("Spark's plan shows the same thing. Here's the report in Kotlin, and the plan it prints, read from the bottom.", [
            (lambda: [FadeIn(shade), *self.drop("cnt"), *self.cap("Spark's plan shows the same thing", WHITE)], 0.6),
            "Here's the report",
            (lambda: [FadeIn(bg), FadeIn(panel[0]), FadeIn(panel[1])], 0.6),
            "and the plan",
            (lambda: [FadeIn(panel[2]), FadeIn(panel[3])], 0.6),
        ])
        self.steps("Everything marked one runs in stage one. Everything marked two runs in stage two. And between them sits the shuffle, "
                   "which the plan calls Exchange. Count the Exchanges, and add one.", [
            "Everything marked one",
            (lambda: [Indicate(plan[2], color=BLUE_M, scale_factor=1.04), Indicate(plan[3], color=BLUE_M, scale_factor=1.04),
                      *self.cap("*(1): stage 1", BLUE_M)], 0.9),
            "Everything marked two",
            (lambda: [Indicate(plan[0], color=TEAL_M, scale_factor=1.04), *self.cap("*(2): stage 2", TEAL_M)], 0.9),
            "And between",
            (lambda: [Indicate(plan[1], color=YELLOW_M, scale_factor=1.06), *self.cap("Exchange: the shuffle", YELLOW_M)], 0.9),
            "Count the",
            (lambda: self.cap("count the Exchanges, add one: 1 + 1 = 2 stages", WHITE), 0.5),
        ])

        # ---------------- scene 8: what changes the count ----------------
        self.steps("Two things change the count. The number of pieces after a shuffle is a setting, shuffle partitions. It's 200 by "
                   "default. The lesson's demo sets it to four.", [
            (lambda: [FadeOut(bg), FadeOut(panel), FadeOut(shade), *self.cap("two things change the count", WHITE)], 0.8),
            "a setting",
            (lambda: [*self.cap("spark.sql.shuffle.partitions: 200 by default (the demo: 4)", WHITE),
                      *[glow(b, TEAL_M, 1.03) for b in t2]], 0.8),
        ])
        merged = frame_box(T2X, (YS[0] + YS[-1]) / 2, T2W, YS[0] - YS[-1] + BH, TEAL_M).set_z_index(1)
        merged_l = T("one task", 22).move_to(merged).set_z_index(3)
        self.steps("And since Spark 3.2, a feature called adaptive query execution is on by default. It runs each stage that ends in "
                   "a shuffle as a job of its own, sees how small the shuffle really was, and plans the rest again.", [
            (lambda: self.cap("adaptive query execution (AQE): on by default since Spark 3.2", WHITE), 0.6),
            "runs each stage",
            (lambda: [glow(fr1, BLUE_M, 1.01), *self.cap("each stage that ends in a shuffle: a job of its own")], 0.8),
            "and plans the rest",
            (lambda: self.cap("then it sees how small the shuffle was, and plans the rest again"), 0.5),
        ])
        self.steps("In the demo, it merges the four tiny pieces into one: two jobs, and five tasks.", [
            "merges",
            (lambda: [*[FadeOut(b) for b in t2], *[FadeOut(l) for l in t2l], FadeOut(total), FadeIn(merged), FadeIn(merged_l)], 0.8),
            "two jobs",
            (lambda: self.cnt("AQE on: 2 jobs  ·  4 + 1 = 5 tasks", GREEN_M), 0.5),
        ])
        disk = SurroundingRectangle(parts[2], color=RED_M, buff=0.08, stroke_width=3)
        self.steps("One more thing. The shuffle files sit on one machine's disk, in one copy. So what happens when that machine dies? "
                   "That's the next section.", [
            (lambda: [FadeOut(merged), FadeOut(merged_l), *[FadeIn(b) for b in t2], *[FadeIn(l) for l in t2l], *self.drop("cnt"),
                      *self.cap("shuffle files: on one machine's disk, in one copy", WHITE)], 0.7),
            "in one copy",
            (lambda: [Create(disk)], 0.5),
            "So what happens",
            (lambda: [*self.cap("what if that machine dies? the next section", YELLOW_M), glow(t1[2], RED_M, 1.04)], 0.8),
        ])

        # ---------------- scene 9: moral and check ----------------
        self.steps("The moral: narrow steps stay at their own station. A wide step sends everything to the pass, and the pass cuts "
                   "the job into stages.", [
            (lambda: [FadeOut(disk), *self.cap("narrow steps stay at their own station", BLUE_M), *[glow(b, BLUE_M, 1.03) for b in t1]], 0.7),
            "A wide step",
            (lambda: [*self.cap("a wide step goes to the pass, and the pass cuts the job into stages", YELLOW_M), Indicate(lines, color=YELLOW_M)], 0.8),
        ], after=0.5)
        self.steps("One quick check. A plan reads four files and has two Exchanges, each making four pieces. How many stages, and how "
                   "many tasks? Pause and think.", [
            (lambda: self.cap("one quick check", WHITE), 0.4),
            "A plan reads",
            (lambda: self.cnt("4 files, 2 Exchanges, 4 pieces each: stages? tasks?", YELLOW_M), 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Three stages. Four, plus four, plus four: twelve tasks.", [
            (lambda: [*self.cnt("3 stages  ·  4 + 4 + 4 = 12 tasks", GREEN_M), *self.cap("stages = Exchanges + 1", WHITE)], 0.7),
        ], after=0.3)
        self.wait(2.0)
