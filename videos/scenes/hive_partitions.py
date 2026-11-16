from sfz import *

SAY.insert(0, (r"\bdt\b", "D T"))
SAY.insert(0, (r"\bMSCK REPAIR TABLE\b", "M S C K repair table"))
SAY.insert(0, (r"\bALTER TABLE ADD PARTITION\b", "alter table, add partition,"))

LX = -6.35                                   # left edge of the storage tree
LOC_Y = 2.45                                 # s3://lake/payments/
EARLY_Y = 1.65                               # "1,088 earlier days"
ROW_Y = [1.1, 0.55, 0.0, -0.55, -1.1, -1.65, -2.2, -2.75]   # dt=2026-11-01 .. 11-08
FILES = [3, 2, 3, 3, 2, 3, 4]               # files per day
FX0, FDX = -3.75, 0.55                       # first file column, spacing
FW, FH = 0.42, 0.34
EX, EY, EW, EH = 3.8, 1.75, 3.0, 0.85        # the engine
QX, QY = 0.95, [3.15, 2.78]                  # the query, left aligned
CX, CY = 2.5, [0.55, 0.05]                   # counters
MX, MY, MW, MH = 3.8, -1.4, 5.0, 2.5         # the metastore
ML = MX - MW / 2 + 0.25                      # left edge of metastore lines
MLY = [-0.9, -1.3, -1.7, -2.2]


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def pfile(x, y, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.05, width=FW, height=FH, stroke_color=color, stroke_width=2)
    return r.set_fill(fillc(color, 0.2), 1).move_to([x, y, 0])


def fpos(day, k):
    return [FX0 + k * FDX, ROW_Y[day], 0]


def query(lines, color=WHITE):
    return VGroup(*[left_at(M(s, 17, color), QX, QY[k]) for k, s in enumerate(lines)])


def counter(s, k, color=GREY_B, size=22):
    return left_at(T(s, size, color), CX, CY[k])


def bottom(s, color=GREY_B):
    return left_at(T(s, 22, color), MX - MW / 2, -3.15)


def mline(s, k, color=GREY_B, mono=False):
    return left_at((M(s, 17, color) if mono else T(s, 21, color)), ML, MLY[k])


class HivePartitions(Base):
    """batch-04, section 1 (with section 2's metastore and section 3's listing cost): the payments table is a folder of
    Parquet files on S3; a query for one day reads all 1,095 days. Split into dt=... folders, the query reads one (partition
    pruning). Listing 30,000 folders on S3 takes 30 requests, so the metastore keeps the partition list; a late folder is
    invisible until ADD PARTITION or MSCK REPAIR; a day of 50,000 small files still costs 50 listing requests."""

    def construct(self):
        self.title_card("Hive partitions", "a table is a folder, and a filter can skip folders")

        loc = left_at(M("s3://lake/payments/", 20, GREY_B), LX, LOC_Y)
        big = RoundedRectangle(corner_radius=0.14, width=5.0, height=3.9, stroke_color=GREY_B, stroke_width=2.5)
        big.set_fill(BLACK, 1).move_to([-3.9, -0.2, 0])
        grid = [[-5.4 + c * 0.75, 1.0 - r * 0.8] for r in range(4) for c in range(5)]
        files = [pfile(x, y) for x, y in grid]
        cap = T("every night's files land in one folder", 18, GREY_C).move_to([-3.9, -2.6, 0])
        self.steps("The payments table is a folder of Parquet files on S3. Every night, the batch job adds a few more.", [
            (lambda: [FadeIn(loc), FadeIn(big)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(f, scale=0.8) for f in files[:8]], lag_ratio=0.1)], 0.9),
            "Every night",
            (lambda: [LaggedStart(*[FadeIn(f, scale=0.8) for f in files[8:]], lag_ratio=0.08), FadeIn(cap)], 1.3),
        ])

        eng = VGroup(RoundedRectangle(corner_radius=0.12, width=EW, height=EH, stroke_color=BLUE_M, stroke_width=3)
                     .set_fill(fillc(BLUE_M), 1).move_to([EX, EY, 0]),
                     T("engine", 24).move_to([EX, EY + 0.15, 0]), T("Spark or Trino", 17, GREY_B).move_to([EX, EY - 0.21, 0]))
        q1 = query(["SELECT sum(amount_cents) FROM payments", "WHERE dt = '2026-11-07'"])
        a_all = Arrow([EX - EW / 2 - 0.05, EY - 0.1, 0], [-1.3, 0.55, 0], buff=0, stroke_width=3, color=GOLD_M,
                      max_tip_length_to_length_ratio=0.06)
        self.steps("A query wants one day's total. With every day mixed in one folder, the engine can't tell which files "
                   "hold that day, so it opens all of them.", [
            (lambda: [FadeIn(q1), FadeIn(eng)], 0.8),
            "so it opens",
            (lambda: [GrowArrow(a_all)], 0.5),
            (lambda: [LaggedStart(*[f.animate.set_stroke(GOLD_M, 3).set_fill(fillc(GOLD_M, 0.3), 1) for f in files],
                                  lag_ratio=0.06)], 1.4),
        ])

        c1 = counter("days of data read: 1,095", 0, RED_M)
        c2 = counter("days the query needs: 1", 1, GREY_B)
        self.steps("Three years in, that's 1,095 days of files read, to answer a question about one.", [
            (lambda: [FadeIn(c1, shift=0.1 * UP)], 0.6),
            "to answer",
            (lambda: [FadeIn(c2, shift=0.1 * UP), glow(big, RED_M, 1.02)], 0.9),
        ])

        # ---- one folder per day --------------------------------------------------------------------------------------
        labels = [left_at(M(f"dt=2026-11-0{d + 1}/", 18), LX, ROW_Y[d]) for d in range(7)]
        early = left_at(T("and 1,088 earlier days, one folder each", 18, GREY_C), LX, EARLY_Y)
        slots = [(d, k) for d in range(7) for k in range(FILES[d])]
        self.steps("So split the folder. Each day gets its own subfolder, named after the column and its value: "
                   "dt equals the date.", [
            (lambda: [FadeOut(c1), FadeOut(c2), FadeOut(a_all), FadeOut(cap),
                      *[f.animate.set_stroke(GREY_B, 2).set_fill(fillc(GREY_B, 0.2), 1) for f in files]], 0.6),
            "Each day",
            (lambda: [FadeOut(big), *[f.animate.move_to(fpos(d, k)) for f, (d, k) in zip(files, slots)]], 1.3),
            "named after",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * RIGHT) for l in labels], lag_ratio=0.1)], 1.0),
            (lambda: [FadeIn(early)], 0.5),
        ])
        rows = [VGroup(labels[d], *[files[i] for i, (dd, _) in enumerate(slots) if dd == d]) for d in range(7)]

        a7 = Arrow([EX - EW / 2 - 0.05, EY - 0.15, 0], [-1.65, ROW_Y[6] + 0.05, 0], buff=0, stroke_width=3, color=GOLD_M,
                   max_tip_length_to_length_ratio=0.05)
        c3 = counter("folders read: 1 of 1,095", 0, GOLD_M)
        prune = chip("partition pruning", GOLD_M, 22).move_to([CX + 1.5, CY[1] - 0.15, 0])
        self.steps("Now the query for the seventh of November reads one folder and skips every other one, without opening "
                   "a file. That's partition pruning.", [
            (lambda: [*[rows[d].animate.set_opacity(0.25) for d in range(6)], early.animate.set_opacity(0.3)], 0.8),
            (lambda: [GrowArrow(a7)], 0.6),
            (lambda: [*[f.animate.set_stroke(GOLD_M, 3).set_fill(fillc(GOLD_M, 0.3), 1) for f in rows[6][1:]],
                      FadeIn(c3, shift=0.1 * UP)], 0.7),
            "That's partition",
            (lambda: [FadeIn(prune, shift=0.1 * UP)], 0.6),
        ])

        # ---- where does the list of folders come from? ---------------------------------------------------------------
        a_loc = Arrow([EX - EW / 2 - 0.05, EY + 0.15, 0], [loc.get_right()[0] + 0.15, LOC_Y - 0.05, 0], buff=0,
                      stroke_width=3, color=TEAL_M, max_tip_length_to_length_ratio=0.06)
        lst = M("LIST", 16, TEAL_M).next_to(a_loc.point_from_proportion(0.5), DOWN, buff=0.12)
        n = ValueTracker(0)
        req = always_redraw(lambda: counter(f"LIST requests: {int(round(n.get_value()))}", 0, TEAL_M))
        c4 = counter("1,000 names per request", 1, GREY_B)
        c5 = left_at(T("30,000 folders, by day and hour", 22, GREY_B), CX, -0.45)
        self.steps("To skip folders, the engine first needs their list. S3 lists at most 1,000 names per request, so a "
                   "table split by day and hour into 30,000 folders costs 30 requests before any data is read.", [
            (lambda: [FadeOut(a7), FadeOut(c3), FadeOut(prune), *[r.animate.set_opacity(1) for r in rows[:6]],
                      early.animate.set_opacity(1),
                      *[f.animate.set_stroke(GREY_B, 2).set_fill(fillc(GREY_B, 0.2), 1) for f in rows[6][1:]]], 0.7),
            (lambda: [GrowArrow(a_loc), FadeIn(lst)], 0.6),
            "S3 lists",
            (lambda: [FadeIn(c4, shift=0.1 * UP)], 0.5),
            "so a",
            (lambda: [FadeIn(c5, shift=0.1 * UP)], 0.5),
            "costs 30",
            (lambda: [FadeIn(req)], 0.2),
            (lambda: [n.animate(rate_func=linear).set_value(30),
                      LaggedStart(*[flow(a_loc, TEAL_M, 0.35) for _ in range(8)], lag_ratio=0.35)], 2.4),
        ])
        req.clear_updaters()

        # ---- the metastore ---------------------------------------------------------------------------------------------
        ms = RoundedRectangle(corner_radius=0.14, width=MW, height=MH, stroke_color=PURPLE_M, stroke_width=3)
        ms.set_fill(fillc(PURPLE_M), 1).move_to([MX, MY, 0])
        mt = T("metastore", 24).move_to([MX, MY + MH / 2 - 0.27, 0])
        m1 = mline("payments: 8 columns, Parquet", 0)
        m2 = mline("location: s3://lake/payments/", 1)
        m3 = mline("partitions: one row per folder", 2)
        self.steps("Hive keeps that list in the metastore: a database that maps each table name to its columns, its "
                   "location, and one row per partition.", [
            (lambda: [FadeOut(req), FadeOut(c4), FadeOut(c5), FadeOut(a_loc), FadeOut(lst)], 0.6),
            (lambda: [FadeIn(ms), FadeIn(mt)], 0.7),
            "maps each table",
            (lambda: [FadeIn(m1, shift=0.1 * RIGHT)], 0.6),
            "its location",
            (lambda: [FadeIn(m2, shift=0.1 * RIGHT)], 0.5),
            "and one row",
            (lambda: [FadeIn(m3, shift=0.1 * RIGHT)], 0.6),
        ])

        a_ms = Arrow([MX, EY - EH / 2 - 0.05, 0], [MX, MY + MH / 2 + 0.05, 0], buff=0, stroke_width=3, color=PURPLE_M,
                     max_tip_length_to_length_ratio=0.15)
        flab = right_at(M("dt = '2026-11-07'", 16, PURPLE_M), MX - 0.2, (EY - EH / 2 + MY + MH / 2) / 2)
        m4 = mline("→ dt=2026-11-07/", 3, GOLD_M, mono=True)
        m4b = left_at(T("one partition", 18, GOLD_M), m4.get_right()[0] + 0.25, MLY[3])
        req1 = bottom("LIST requests: 1", TEAL_M)
        self.steps("The engine sends its filter along, and the metastore answers from its own table: one partition, with "
                   "its folder. Then the engine lists only that folder.", [
            (lambda: [GrowArrow(a_ms), FadeIn(flab)], 0.6),
            (lambda: [flow(a_ms, PURPLE_M, 0.6)], 0.6),
            "one partition",
            (lambda: [FadeIn(m4, shift=0.1 * RIGHT), FadeIn(m4b)], 0.6),
            (lambda: [flow(a_ms, GOLD_M, 0.6, back=True)], 0.6),
            "Then the engine",
            (lambda: [FadeOut(flab), GrowArrow(a7), *[r.animate.set_opacity(0.25) for r in rows[:6]],
                      early.animate.set_opacity(0.3)], 0.7),
            (lambda: [*[f.animate.set_stroke(GOLD_M, 3).set_fill(fillc(GOLD_M, 0.3), 1) for f in rows[6][1:]],
                      FadeIn(req1)], 0.6),
        ])

        lab8 = left_at(M("dt=2026-11-08/", 18, GREEN_M), LX, ROW_Y[7])
        f8 = [pfile(*fpos(7, k)[:2], GREEN_M) for k in range(3)]
        row8 = VGroup(lab8, *f8)
        late = left_at(T("late job, straight to S3", 17, GREEN_M), FX0 + 3 * FDX - 0.1, ROW_Y[7])
        q8 = query(["SELECT sum(amount_cents) FROM payments", "WHERE dt = '2026-11-08'"])
        m5 = mline("no partition for 2026-11-08", 3, RED_M)
        zero = bottom("0 rows", RED_M)
        self.steps("Now the metastore holds the truth. A late job writes the eighth of November straight to S3 and never "
                   "tells it. A query for that day gets zero rows, though the files are right there.", [
            (lambda: [FadeOut(a7), FadeOut(req1), FadeOut(m4b), *[r.animate.set_opacity(1) for r in rows[:6]],
                      early.animate.set_opacity(1),
                      *[f.animate.set_stroke(GREY_B, 2).set_fill(fillc(GREY_B, 0.2), 1) for f in rows[6][1:]]], 0.6),
            (lambda: [glow(ms, PURPLE_M, 1.02)], 0.8),
            "A late job",
            (lambda: [FadeIn(lab8, shift=0.1 * RIGHT), LaggedStart(*[FadeIn(f, scale=0.8) for f in f8], lag_ratio=0.2),
                      FadeIn(late)], 1.0),
            "A query for",
            (lambda: [Transform(q1, q8), flow(a_ms, PURPLE_M, 0.6)], 0.7),
            (lambda: [Transform(m4, m5)], 0.5),
            (lambda: [flow(a_ms, RED_M, 0.5, back=True), FadeIn(zero, shift=0.1 * UP)], 0.6),
            "though the files",
            (lambda: [*[glow(f, GREEN_M, 1.15) for f in f8]], 0.9),
        ])

        qa = query(["ALTER TABLE payments ADD PARTITION", "(dt = '2026-11-08');"], GREEN_M)
        m6 = mline("→ dt=2026-11-08/", 3, GREEN_M, mono=True)
        qm = query(["MSCK REPAIR TABLE payments;"], TEAL_M)
        a_loc2 = Arrow([EX - EW / 2 - 0.05, EY + 0.15, 0], [loc.get_right()[0] + 0.15, LOC_Y - 0.05, 0], buff=0,
                       stroke_width=3, color=TEAL_M, max_tip_length_to_length_ratio=0.06)
        slow = bottom("lists all 30,000 folders again", TEAL_M)
        self.steps("ALTER TABLE ADD PARTITION registers it. MSCK REPAIR TABLE finds it by listing the whole location: "
                   "slow again.", [
            (lambda: [FadeOut(zero), FadeOut(late), Transform(q1, qa)], 0.7),
            (lambda: [Transform(m4, m6), flow(a_ms, GREEN_M, 0.6)], 0.7),
            "MSCK REPAIR",
            (lambda: [Transform(q1, qm)], 0.6),
            "by listing",
            (lambda: [GrowArrow(a_loc2)], 0.5),
            (lambda: [FadeIn(slow, shift=0.1 * UP), LaggedStart(*[flow(a_loc2, TEAL_M, 0.35) for _ in range(5)],
                                                                 lag_ratio=0.35)], 1.5),
        ])

        q7 = query(["SELECT sum(amount_cents) FROM payments", "WHERE dt = '2026-11-07'"])
        tiny = VGroup(*[pfile(0, 0, GOLD_M).scale(0.42).move_to([FX0 - 0.2 + c * 0.2, ROW_Y[6] + 0.12 - r * 0.24, 0])
                        for r in range(2) for c in range(10)])
        n2 = ValueTracker(0)
        req2 = always_redraw(lambda: bottom(f"50,000 files, LIST requests: {int(round(n2.get_value()))}", TEAL_M))
        self.steps("And the metastore knows folders, not files. The engine still lists each folder it reads, so a day of "
                   "50,000 small files costs 50 requests before the first byte.", [
            (lambda: [FadeOut(slow), FadeOut(a_loc2), Transform(q1, q7), Transform(m4, mline("→ dt=2026-11-07/", 3, GOLD_M, mono=True))], 0.8),
            "The engine still",
            (lambda: [GrowArrow(a7), FadeOut(VGroup(*rows[6][1:])), FadeIn(tiny)], 0.8),
            "so a day",
            (lambda: [FadeIn(req2)], 0.3),
            (lambda: [n2.animate(rate_func=linear).set_value(50),
                      LaggedStart(*[flow(a7, TEAL_M, 0.35) for _ in range(7)], lag_ratio=0.35)], 2.4),
        ])
        req2.clear_updaters()

        self.steps("Partitions let a filter skip whole folders. Listing them is what stays slow, which is why the folder "
                   "list lives in the metastore.", [
            (lambda: [*[l.animate(rate_func=there_and_back).set_color(GOLD_M).scale(1.08) for l in labels]], 1.0),
            "Listing them",
            (lambda: [glow(eng[0], TEAL_M)], 0.9),
            "which is why",
            (lambda: [glow(ms, PURPLE_M, 1.03)], 1.0),
        ])
        self.wait(0.6)
