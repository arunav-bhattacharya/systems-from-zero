from sfz import *

SAY.insert(0, (r"\bdt\b", "D T"))
SAY.insert(0, (r"\bcreated at\b", "created-at"))


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
    return RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color, a), 1).move_to([x, y, 0])


# ---- the one picture ----
Q_Y = 2.9                                   # the query chip
TBL_Y = 2.25                                # "payments/" label
FY, FHGT = 0.55, 2.5                        # folder row centre and height
F_TOP, F_BOT = FY + FHGT / 2, FY - FHGT / 2
FW, FGAP = 1.66, 0.12
FX = [-(7 * FW + 6 * FGAP) / 2 + FW / 2 + k * (FW + FGAP) for k in range(7)]
FLAB_Y = F_TOP - 0.3
SKIP_Y = F_BOT + 0.28
RES_Y, PLAN_Y, BAR_Y, CAP_Y = -1.3, -2.1, -2.75, -3.3
DAYC = [BLUE_M, TEAL_M, GREEN_M, YELLOW_M, GOLD_M, RED_M, "#B48ED0"]
DAYS = [f"dt=2026-11-0{k + 1}" for k in range(7)]

rng = np.random.default_rng(4)


def dot_grid(k):
    """Six payments of day k, inside its own folder."""
    return [np.array([FX[k] + (c - 0.5) * 0.55, FY + 0.35 - r * 0.45, 0]) for r in range(3) for c in range(2)]


def scattered():
    """The same 42 payments mixed along the one long shelf."""
    xs = rng.uniform(-6.0, 6.0, 42)
    ys = rng.uniform(F_BOT + 0.35, F_TOP - 0.55, 42)
    order = rng.permutation(42)
    return [np.array([xs[i], ys[i], 0]) for i in order]


class HivePartitions(Base):
    """batch-04, section 1. A year of payments in one folder: a question about yesterday reads everything (1,095 days
    after three years). The library's long shelf, then one shelf per year with a label. One folder per day,
    dt=2026-11-01..07; the value lives only in the name. WHERE dt = '2026-11-03' opens 1/8 files (partition pruning);
    the same day by created_at opens all 8. The plan shows it. Put dt in the query; pick a column with few values."""

    def query(self, s, color=YELLOW_M):
        return self.put("q", fit(chip(s, color, 22, mono=True), 13.0).move_to([0, Q_Y, 0]))

    def result(self, s, color=WHITE):
        return self.put("res", fit(T(s, 26, color), 12.0).move_to([0, RES_Y, 0]))

    def construct(self):
        self.lab = {}
        self.title_card("One shelf per day", "how a folder name lets a query skip the rest")

        # ---------------- scene 1: twenty minutes for one day ----------------
        shelf = frame_box(0, FY, 12.9, FHGT, BLUE_M)
        tbl = left_at(M("payments/", 22, BLUE_M), FX[0] - FW / 2, TBL_Y)
        spots = scattered()
        dots = VGroup(*[Dot(radius=0.075, color=DAYC[i % 7]).move_to(spots[i]).set_z_index(2) for i in range(42)])
        self.steps("Picture a small company that records card payments for cafés and shops. Every night, a program saves the "
                   "day's payments as files in one shared folder. By now, it holds a whole year.", [
            "Every night",
            (lambda: [FadeIn(shelf), FadeIn(tbl)], 0.6),
            (lambda: [LaggedStart(*[LaggedStart(*[FadeIn(dots[i], shift=0.3 * DOWN) for i in range(42) if i % 7 == k], lag_ratio=0.1)
                                    for k in range(7)], lag_ratio=0.5)], 3.0),
            "By now",
            (lambda: self.cap("one folder, a whole year of payments"), 0.5),
        ])
        self.steps("A colleague in finance asks how much the shops took yesterday. The answer arrives twenty minutes later. "
                   "Why so slow, for one day?", [
            (lambda: self.query("how much did the shops take yesterday?", WHITE), 0.6),
            "twenty minutes",
            (lambda: self.cap("the answer: twenty minutes later", RED_M), 0.5),
            "Why so slow",
            (lambda: self.cap("why so slow, for one day?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 2: one folder reads everything ----------------
        sweep = Rectangle(width=0.5, height=FHGT - 0.15, stroke_color=YELLOW_M, stroke_width=4).move_to([-6.1, FY, 0]).set_z_index(3)
        self.steps("Because the program read the whole year to find one day. With one folder for the whole table, every question "
                   "reads every file.", [
            (lambda: [Create(sweep)], 0.3),
            (lambda: [sweep.animate.move_to([6.1, FY, 0])], 2.2),
            (lambda: [FadeOut(sweep)], 0.3),
            "every question",
            (lambda: self.cap("one folder: every question reads every file", WHITE), 0.5),
        ])
        self.steps("And the table grows by a day, every day. After three years, a question about yesterday reads 1,095 days of "
                   "data, to use one of them.", [
            "After three years",
            (lambda: self.result("3 years: reads 1,095 days of data, to use 1", RED_M), 0.6),
        ])

        # ---------------- scene 3: the long shelf ----------------
        self.steps("A library with every book on one long shelf has the same problem. Ask for one year's books, and somebody walks "
                   "the whole shelf. Usually the new person.", [
            (lambda: [*self.drop("res", "q"), *self.cap("a library: every book on one long shelf")], 0.6),
            "somebody walks",
            (lambda: [glow(shelf, YELLOW_M, 1.01)], 1.0),
            "Usually the new",
            (lambda: self.cap("somebody walks the whole shelf (usually the new person)"), 0.5),
        ])
        self.steps("The library's old fix: one shelf per year, with the year on a label. A question about one year never visits "
                   "the other shelves.", [
            (lambda: self.cap("the old fix: one shelf per year, a label on each", WHITE), 0.6),
        ])
        folders = [frame_box(FX[k], FY, FW, FHGT, BLUE_M) for k in range(7)]
        labels = [fit(M(DAYS[k], 16, WHITE), FW - 0.15).move_to([FX[k], FLAB_Y, 0]).set_z_index(3) for k in range(7)]
        homes = [dot_grid(k) for k in range(7)]

        def to_home():
            anims = []
            for i in range(42):
                k, j = i % 7, i // 7
                anims.append(dots[i].animate.move_to(homes[k][j]))
            return anims

        self.steps("Let's do the same with the table. Split the folder into smaller folders, one per day, and name each one after "
                   "its day.", [
            "Split the folder",
            (lambda: [FadeOut(shelf), *[FadeIn(f) for f in folders], *to_home()], 1.4),
            "name each one",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in labels], lag_ratio=0.12),
                      *self.cap("the lesson's demo: one week, one folder per day")], 1.2),
        ])
        self.steps("The shelf is a folder. The label is the folder's name. And the books are the payments.", [
            "The shelf",
            (lambda: [*self.cap("shelf = folder"), *[glow(f, BLUE_M, 1.02) for f in folders]], 0.7),
            "The label",
            (lambda: [*self.cap("label = the folder's name"), *[Indicate(l, color=YELLOW_M, scale_factor=1.1) for l in labels]], 0.7),
            "And the books",
            (lambda: [*self.cap("book = payment"), Indicate(dots, color=WHITE, scale_factor=1.3)], 0.7),
        ])
        self.stamp("s4")

        # ---------------- scene 4: the value lives in the name ----------------
        self.steps("Each of these folders is called a partition, and dt, short for date, is the partition column. The name holds "
                   "the column and its value together, so any program can rebuild the column from the path alone.", [
            "called a partition",
            (lambda: [*self.cap("each folder: a partition", WHITE), glow(folders[2], YELLOW_M, 1.04)], 0.8),
            "and dt",
            (lambda: self.cap("dt (short for date): the partition column", WHITE), 0.5),
            "The name holds",
            (lambda: [*self.result("dt=2026-11-03  :  column dt, value 2026-11-03"), Indicate(labels[2], color=YELLOW_M, scale_factor=1.25)], 0.8),
        ])
        cells = VGroup(*[mbox(s, GREY_B, h=0.6, size=20) for s in ("dt", "created_at", "amount_cents")]).arrange(RIGHT, buff=0)
        cells.move_to([0, RES_Y, 0])
        card_lab = T("one row, as Spark writes it", 20, GREY_B).next_to(cells, DOWN, buff=0.2)
        self.steps("In fact, the value lives only there. Spark, the engine this course uses to run jobs over many machines, takes the "
                   "dt column out of the rows when it writes, and puts it in the folder name instead.", [
            (lambda: [*self.drop("res"), *self.cap("Spark: the engine that runs the jobs, over many machines")], 0.5),
            "takes the",
            (lambda: [FadeIn(cells, shift=0.1 * UP), FadeIn(card_lab)], 0.6),
            "column out",
            (lambda: [cells[0].animate.move_to(labels[2].get_center()).set_opacity(0),
                      cells[1:].animate.shift(0.5 * cells[0].width * LEFT)], 1.0),
            "puts it in",
            (lambda: [Indicate(labels[2], color=YELLOW_M, scale_factor=1.3), *self.cap("the value lives only in the folder name", WHITE)], 0.8),
        ])
        back = mbox("dt", YELLOW_M, h=0.6, size=20)
        back.move_to(labels[2].get_center())
        self.steps("When a program reads the table, it turns the name back into a column.", [
            (lambda: [FadeIn(back, run_time=0.01), back.animate.next_to(cells[1], LEFT, buff=0)], 1.0),
            (lambda: self.cap("reading: the name becomes a column again"), 0.5),
        ])

        # ---------------- scene 5: pruning ----------------
        def reset_folders():
            return [*[f.animate.set_stroke(BLUE_M, 3).set_opacity(1) for f in folders], *[l.animate.set_opacity(1) for l in labels],
                    dots.animate.set_opacity(1)]

        def read_labels(hit):
            """A cursor visits each label; folders in hit light up, the others dim with "skipped"."""
            cur = SurroundingRectangle(labels[0], color=YELLOW_M, buff=0.06, stroke_width=3).set_z_index(4)
            seq = [Create(cur, run_time=0.2)]
            for k in range(7):
                if k:
                    seq.append(cur.animate(run_time=0.22).move_to(labels[k]))
                if k in hit:
                    seq.append(AnimationGroup(folders[k].animate.set_stroke(YELLOW_M, 5), run_time=0.2))
                else:
                    sk = T("skipped", 16, GREY_B).move_to([FX[k], SKIP_Y, 0]).set_z_index(3)
                    self.skips.append(sk)
                    seq.append(AnimationGroup(folders[k].animate.set_opacity(0.3), labels[k].animate.set_opacity(0.35),
                                              *[dots[i].animate.set_opacity(0.2) for i in range(42) if i % 7 == k],
                                              FadeIn(sk), run_time=0.2))
            seq.append(FadeOut(cur, run_time=0.2))
            return [Succession(*seq)]

        def open_all():
            return [LaggedStart(*[f.animate.set_stroke(YELLOW_M, 5) for f in folders], lag_ratio=0.15)]

        def unskip():
            s, self.skips = self.skips, []
            return [FadeOut(x) for x in s]

        self.skips = []
        self.steps("Now ask for one day. Where dt is the third of November. The program reads the labels first, and skips every "
                   "folder that can't match, before opening a single file.", [
            (lambda: [FadeOut(cells[1:]), FadeOut(back), FadeOut(card_lab), *self.drop("cap")], 0.5),
            "Where dt",
            (lambda: self.query("WHERE dt = '2026-11-03'"), 0.6),
            "reads the labels",
            (lambda: read_labels({2}), 2.4),
        ])
        self.steps("That's called partition pruning. In the lesson's week of payments, DuckDB, a small database that runs inside a "
                   "program, opens one file out of eight. Over three years, one day out of about a thousand.", [
            (lambda: self.cap("partition pruning: skip what can't match, before opening a file", WHITE), 0.6),
            "opens one file",
            (lambda: self.result("DuckDB: opens 1/8 files", GREEN_M), 0.6),
            "Over three years",
            (lambda: self.cap("over 3 years: 1 day out of about 1,000"), 0.5),
        ])
        self.stamp("poster")

        # ---------------- scene 6: the same day, another column ----------------
        self.steps("Now a different filter. Every payment inside the files also has its exact time, in a column called created at.", [
            (lambda: [*reset_folders(), *unskip(), *self.drop("res"), *self.cap("inside the files: created at, the exact time")], 0.7),
            "its exact time",
            (lambda: [Indicate(dots, color=WHITE, scale_factor=1.3)], 0.8),
        ])
        self.steps("Ask for the payments whose created at is on the third of November. The very same day. How many files does it "
                   "open? Pause and guess.", [
            "Ask for",
            (lambda: self.query("WHERE created_at::DATE = DATE '2026-11-03'"), 0.6),
            "The very same day",
            (lambda: [Indicate(labels[2], color=YELLOW_M, scale_factor=1.25)], 0.7),
            "Pause and guess",
            (lambda: self.cap("same day: how many files? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("All eight. The answer is right, nothing fails, and nobody notices the extra reading.", [
            (lambda: [*open_all(), *self.result("DuckDB: opens all 8 files", RED_M), *self.drop("cap")], 1.0),
            "The answer is right",
            (lambda: self.cap("the right answer, nothing fails, and all the reading", RED_M), 0.5),
        ])
        self.steps("The program only reads labels, and the labels say dt. It can't know that created at and dt agree. Only you know "
                   "that. The program would need to be a mind reader, and it's a file reader.", [
            "only reads labels",
            (lambda: [LaggedStart(*[Indicate(l, color=YELLOW_M, scale_factor=1.15) for l in labels], lag_ratio=0.1)], 1.2),
            "It can't know",
            (lambda: self.cap("created at and dt agree, but only you know that"), 0.5),
            "mind reader",
            (lambda: self.cap("it's not a mind reader; it's a file reader", WHITE), 0.5),
        ])

        # ---------------- scene 7: how to see it ----------------
        p1 = chip("Scanning Files: 1/8", GREEN_M, 22, mono=True)
        p2 = chip("PartitionFilters: []", RED_M, 22, mono=True)
        plans = VGroup(p1, p2).arrange(RIGHT, buff=0.8).move_to([0, PLAN_Y, 0])
        self.steps("The plan, the program's own description of how it will run a query, tells you. In DuckDB, a line like scanning "
                   "files, one of eight, means it skipped files by their path. No such line means it reads them all.", [
            (lambda: self.cap("the plan: the program's own description of how it will run a query", WHITE), 0.6),
            "In DuckDB",
            (lambda: [FadeIn(p1, shift=0.1 * UP), *self.cap("DuckDB: 'Scanning Files: 1/8' means files were skipped")], 0.6),
            "No such line",
            (lambda: self.cap("no such line: it reads them all"), 0.5),
        ])
        self.steps("In Spark, an empty list of partition filters means nothing was skipped.", [
            (lambda: [FadeIn(p2, shift=0.1 * UP), *self.cap("Spark: an empty PartitionFilters list means nothing was skipped")], 0.6),
        ])

        # ---------------- scene 8: guardrails ----------------
        self.steps("So, the rule: a filter on the partition column skips folders, and any other filter reads them all. Put dt in the "
                   "query. Keep the created at filter too, for the exact hours.", [
            (lambda: [FadeOut(plans), *reset_folders(), *self.drop("res"),
                      *self.cap("a filter on the partition column skips folders; any other reads them all", WHITE)], 0.7),
            "Put dt",
            (lambda: self.query("WHERE dt = '2026-11-03' AND created_at ..."), 0.6),
            (lambda: read_labels({2}), 2.4),
            "Keep the created",
            (lambda: self.cap("keep the created at filter too, for the exact hours"), 0.5),
        ])
        strike = Line(LEFT, RIGHT, stroke_width=4, color=RED_M)
        self.steps("And pick a partition column that questions filter on, with few different values. A day is the classic: three "
                   "years is about a thousand folders.", [
            (lambda: [*reset_folders(), *unskip(), *self.drop("q"), *self.cap("pick a column questions filter on, with few values", WHITE)], 0.6),
            "A day is",
            (lambda: self.result("by day: 3 years is about 1,000 folders", GREEN_M), 0.6),
        ])
        self.steps("Split by shop as well, with 500,000 shops, and you get 500 million folders, most holding one tiny file. "
                   "Strike that one.", [
            "Split by shop",
            (lambda: self.put("plan", T("by day and shop: 500,000 shops, 500 million folders of tiny files", 24, RED_M).move_to([0, PLAN_Y, 0])), 0.6),
            "Strike that",
            (lambda: [Create(strike.set_width(self.lab["plan"].width + 0.3).move_to(self.lab["plan"]).set_z_index(5))], 0.5),
        ])

        # ---------------- scene 9: moral and check ----------------
        self.steps("The moral: the program skips by the label, never by what's inside. Name the folders by what you ask about, and "
                   "ask by that name.", [
            (lambda: [FadeOut(strike), *self.drop("plan", "res"), *self.cap("it skips by the label, never by what's inside", WHITE)], 0.6),
            (lambda: [LaggedStart(*[Indicate(l, color=YELLOW_M, scale_factor=1.15) for l in labels], lag_ratio=0.1)], 1.2),
            "Name the folders",
            (lambda: self.cap("name the folders by what you ask about, and ask by that name", YELLOW_M), 0.6),
        ], after=0.5)
        self.steps("One quick check. Thirty folders, one per day of November. You ask for dt on or after the twenty ninth. How many "
                   "folders does it open? Pause and think.", [
            (lambda: [*self.cap("30 folders: dt=2026-11-01 to dt=2026-11-30", WHITE), *[f.animate.set_opacity(0.25) for f in folders], *[l.animate.set_opacity(0.3) for l in labels], dots.animate.set_opacity(0.2)], 0.6),
            "You ask for",
            (lambda: self.query("WHERE dt >= '2026-11-29'"), 0.6),
            "Pause and think",
            (lambda: self.result("how many folders? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Two. The twenty ninth and the thirtieth. Ask by created at instead, and it opens all thirty.", [
            (lambda: self.result("2: dt=2026-11-29 and dt=2026-11-30", GREEN_M), 0.6),
            "Ask by created",
            (lambda: self.cap("by created at instead: all 30", RED_M), 0.5),
        ], after=0.3)
        self.wait(2.0)
