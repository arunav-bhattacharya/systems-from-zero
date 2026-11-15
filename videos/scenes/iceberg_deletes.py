from sfz import *

SAY.insert(0, (r"\bParquet\b", "parkay"))

FX, FY, FW, FH = [-5.3, -3.0, -0.7], 1.4, 2.0, 2.2      # the three daily data files
BY = -1.75                                             # the row below: rewritten or new files
NX, NY = 1.0, [2.2, 1.65, 1.1, 0.55]                   # notes, right
RX, RY = 4.2, BY                                       # the reader
SFX, SFS, SFY = -5.85, 0.835, 1.2                      # small files: first x, step, y


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


def marks(x, y, color=RED_M, seed=0):
    rng = np.random.default_rng(seed)
    ys = np.sort(rng.uniform(y - 0.45, y + 0.35, 10))
    return VGroup(*[Line([x + dx - 0.22, yy, 0], [x + dx + 0.22, yy, 0], stroke_width=3, color=color)
                    for yy, dx in zip(ys, rng.uniform(-0.35, 0.35, 10))])


def dfile(k, y, color=WHITE, tag=""):
    x = FX[k]
    r = RoundedRectangle(corner_radius=0.1, width=FW, height=FH, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK if ManimColor(color).to_hex().upper() == "#FFFFFF" else fillc(color), 1).move_to([x, y, 0])
    foot = Rectangle(width=FW - 0.2, height=0.22, stroke_width=0).set_fill(GREY_D, 1).move_to([x, y - FH / 2 + 0.2, 0])
    name = T(f"day {k + 1}" + tag, 20, color).move_to([x, y + FH / 2 - 0.25, 0])
    return VGroup(r, foot, name)


def note(s, k, color=GREY_B, size=20):
    return left_at(T(s, size, color), NX, NY[k])


def small(k, color=WHITE):
    r = RoundedRectangle(corner_radius=0.07, width=0.62, height=0.8, stroke_color=color, stroke_width=2)
    return r.set_fill(BLACK, 1).move_to([SFX + k * SFS, SFY, 0])


def dsmall(k):
    r = RoundedRectangle(corner_radius=0.06, width=0.5, height=0.4, stroke_color=RED_M, stroke_width=2)
    return r.set_fill(fillc(RED_M), 1).move_to([SFX + (k + 3) * SFS, SFY - 0.95, 0])


class IcebergDeletes(Base):
    """batch-12, sections 0 to 2: 30 refunds across three daily files of 100,000 rows. Copy-on-write rewrites all three
    (3.1 MB written, 299,970 unchanged rows copied); merge-on-read writes 6.4 KB of new rows and 7.4 KB of position
    deletes, and every reader applies them. A stream day piles up 15 data files of about 44 KB and 12 delete files;
    compaction makes one file of about 630 KB, and expiring snapshots deletes the old files."""

    def construct(self):
        self.title_card("Corrections in a table of files", "copy on write, merge on read, and compaction")

        cb = chip("chargeback file: 30 payments now refunded", RED_M, 20).move_to([-3.2, 3.2, 0])
        files = [dfile(k, FY) for k in range(3)]
        mk = [marks(FX[k], FY, RED_M, k + 1) for k in range(3)]
        rows = VGroup(*[T("100,000 rows", 16, GREY_B).move_to([FX[k], FY - FH / 2 - 0.25, 0]) for k in range(3)])
        self.steps("Every evening the card network sends 30 refunds. "
                   "In a lakehouse table, those rows sit inside Parquet files that are never changed.", [
            (lambda: [FadeIn(cb, shift=0.1 * DOWN)], 0.7),
            "In a lakehouse",
            (lambda: [LaggedStart(*[FadeIn(f, shift=0.1 * UP) for f in files], lag_ratio=0.2), FadeIn(rows)], 1.0),
            "those rows sit",
            (lambda: [LaggedStart(*[Create(m) for m in mk], lag_ratio=0.2)], 0.9),
            "never changed",
            (lambda: [*[glow(f[0], GREY_B, 1.03) for f in files]], 0.8),
        ])

        n1 = note("footer: sizes, offsets, min and max", 0, GREY_B)
        n2 = note("change one value: all of it is wrong", 1, RED_M)
        self.steps("A file's columns are compressed, and its footer records their sizes and min and max values. "
                   "Change one value and all of that is wrong. So every correction is written as new files.", [
            "and its footer",
            (lambda: [*[f[1].animate.set_fill(GOLD_M, 1) for f in files], FadeIn(n1)], 0.8),
            "Change one value",
            (lambda: [FadeIn(n2), *[f[1].animate.set_fill(RED_M, 1) for f in files]], 0.8),
            "So every correction",
            (lambda: [*[f[1].animate.set_fill(GREY_D, 1) for f in files]], 0.6),
        ])

        # ---- copy on write ---------------------------------------------------------------------------------------
        new = [dfile(k, BY, GREEN_M, ", new") for k in range(3)]
        nmk = [marks(FX[k], BY, GREEN_M, k + 1) for k in range(3)]
        downs = [Arrow([FX[k], FY - FH / 2 - 0.45, 0], [FX[k], BY + FH / 2 + 0.08, 0], buff=0, stroke_width=3, color=GREEN_M,
                       max_tip_length_to_length_ratio=0.25) for k in range(3)]
        cw = note("copy on write", 0, GREEN_M, 24)
        self.steps("Copy on write finds every file that holds a refunded row, reads it whole, "
                   "and writes a new copy with the change applied.", [
            (lambda: [FadeOut(n1), FadeOut(n2)], 0.4),
            (lambda: [FadeIn(cw)], 0.5),
            "finds every file",
            (lambda: [*[glow(f[0], GREEN_M, 1.03) for f in files]], 0.8),
            "and writes",
            (lambda: [*[GrowArrow(a) for a in downs]], 0.5),
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(new[k], shift=0.2 * DOWN), FadeIn(nmk[k])) for k in range(3)],
                                  lag_ratio=0.25)], 1.2),
        ])

        w1 = note("written: 3.1 MB", 1, WHITE)
        w2 = note("unchanged rows copied: 299,970", 2, GOLD_M)
        w3 = note("rows changed: 30", 3, RED_M)
        self.steps("The 30 refunds touched all three files: 3.1 megabytes written, "
                   "and 299,970 unchanged rows copied to change 30.", [
            (lambda: [*[f.animate.set_opacity(0.3) for f in files], *[m.animate.set_opacity(0.3) for m in mk]], 0.6),
            "3.1 megabytes",
            (lambda: [FadeIn(w1)], 0.5),
            "and 299,970",
            (lambda: [FadeIn(w2)], 0.5),
            "to change 30",
            (lambda: [FadeIn(w3), *[glow(n[0], GOLD_M, 1.03) for n in new]], 0.8),
        ])

        rd = box("reader", BLUE_M, w=1.9, h=0.8, size=22).move_to([RX, RY, 0])
        ra = Arrow([RX - 0.95 - 0.1, RY, 0], [FX[2] + FW / 2 + 0.1, RY, 0], buff=0, stroke_width=3, color=BLUE_M,
                   max_tip_length_to_length_ratio=0.1)
        self.steps("Readers still see plain data files, so reads stay fast. "
                   "It suits a table read far more often than it changes.", [
            (lambda: [FadeIn(rd), GrowArrow(ra)], 0.7),
            (lambda: [travel(Line(ra.get_start(), ra.get_end()), BLUE_M, 0.7)], 0.8),
            "It suits",
            (lambda: [glow(rd[0], BLUE_M)], 0.8),
        ])

        # ---- merge on read ---------------------------------------------------------------------------------------
        mr = note("merge on read", 0, TEAL_M, 24)
        nf = VGroup(RoundedRectangle(corner_radius=0.1, width=1.7, height=1.0, stroke_color=TEAL_M, stroke_width=2.5)
                    .set_fill(fillc(TEAL_M), 1), T("30 new rows", 18, TEAL_M)).move_to([FX[0], BY + 0.3, 0])
        df = VGroup(RoundedRectangle(corner_radius=0.1, width=3.7, height=1.5, stroke_color=RED_M, stroke_width=2.5)
                    .set_fill(fillc(RED_M), 1),
                    T("delete file", 18, RED_M).shift(0.5 * UP),
                    M("day 1 file, row 1,000", 15).shift(0.1 * UP),
                    M("day 2 file, row 41,207", 15).shift(0.22 * DOWN),
                    T("... 30 positions", 15, GREY_B).shift(0.52 * DOWN)).move_to([(FX[1] + FX[2]) / 2 + 0.05, BY, 0])
        self.steps("Merge on read leaves the data files alone. It writes the 30 new rows into one small file, "
                   "and a delete file that lists the old rows by position.", [
            (lambda: [FadeOut(VGroup(cw, w1, w2, w3, *new, *nmk, *downs, rd, ra))], 0.5),
            (lambda: [FadeIn(mr), *[f.animate.set_opacity(1) for f in files], *[m.animate.set_opacity(1) for m in mk]], 0.6),
            "It writes",
            (lambda: [FadeIn(nf, shift=0.2 * DOWN)], 0.7),
            "and a delete file",
            (lambda: [FadeIn(df, shift=0.2 * DOWN)], 0.8),
        ])

        s1 = note("new rows: 6.4 KB", 1, TEAL_M)
        s2 = note("delete files: 7.4 KB", 2, RED_M)
        s3 = note("copy on write wrote 3.1 MB", 3, GREY_B)
        rd2 = box("reader", BLUE_M, w=1.9, h=0.8, size=22).move_to([RX, RY, 0])
        ra2 = Arrow([RX - 0.95 - 0.1, RY, 0], [df.get_right()[0] + 0.1, RY, 0], buff=0, stroke_width=3, color=BLUE_M,
                    max_tip_length_to_length_ratio=0.15)
        xs = VGroup(*[Line(l.get_start() + 0.05 * UP, l.get_end() + 0.05 * UP, stroke_width=3, color=GREY_B) for m in mk for l in m])
        self.steps("That's 6.4 kilobytes of rows and 7.4 of deletes. "
                   "The cost moves to readers: every scan reads the delete files and skips the rows they list.", [
            (lambda: [FadeIn(s1)], 0.5),
            "and 7.4",
            (lambda: [FadeIn(s2), FadeIn(s3)], 0.6),
            "The cost moves",
            (lambda: [FadeIn(rd2), GrowArrow(ra2)], 0.7),
            "every scan reads",
            (lambda: [travel(Line(ra2.get_start(), ra2.get_end()), BLUE_M, 0.6), glow(df[0], RED_M, 1.03)], 0.8),
            "and skips",
            (lambda: [*[m.animate.set_color(GREY_D) for m in mk]], 0.7),
        ])

        # ---- small files and compaction ----------------------------------------------------------------------------
        sf = [small(k, WHITE if k < 12 else TEAL_M) for k in range(15)]
        ds = [dsmall(k) for k in range(12)]
        lab1 = left_at(T("one day: 15 data files, about 44 KB each", 19, GREY_B), SFX - 0.3, SFY + 0.75)
        lab2 = right_at(T("12 delete files", 19, RED_M), SFX + 3 * SFS - 0.45, SFY - 0.95)
        self.steps("Corrections every few minutes pile up small files. One day in the lab ends up in 15 data files of "
                   "about 44 kilobytes, plus 12 delete files that every scan must apply.", [
            (lambda: [FadeOut(VGroup(mr, s1, s2, s3, rd2, ra2, nf, df, cb, *files, *mk, rows))], 0.6),
            "One day",
            (lambda: [LaggedStart(*[FadeIn(f, shift=0.15 * DOWN) for f in sf], lag_ratio=0.08), FadeIn(lab1)], 1.4),
            "plus 12",
            (lambda: [LaggedStart(*[FadeIn(d, shift=0.15 * DOWN) for d in ds], lag_ratio=0.08), FadeIn(lab2)], 1.2),
        ])

        big = VGroup(RoundedRectangle(corner_radius=0.12, width=3.6, height=1.3, stroke_color=GREEN_M, stroke_width=3)
                     .set_fill(fillc(GREEN_M), 1),
                     T("1 data file, about 630 KB", 20).shift(0.2 * UP), T("deletes applied", 17, GREEN_M).shift(0.25 * DOWN))
        big.move_to([0, -2.05, 0])
        call = M("CALL lake.system.rewrite_data_files(...)", 16, GOLD_M).move_to([0, -3.15, 0])
        conv = VGroup(*[Line([f.get_x(), SFY - 1.3, 0], big.get_top() + 0.05 * UP, stroke_width=1.5, color=GREY_C) for f in sf[::2]])
        self.steps("Compaction rewrites them into one file of about 630 kilobytes, applying the deletes on the way. "
                   "The rows stay the same; only the layout changes.", [
            (lambda: [FadeIn(call)], 0.5),
            (lambda: [LaggedStart(*[Create(c) for c in conv], lag_ratio=0.05)], 0.8),
            (lambda: [FadeIn(big, shift=0.2 * DOWN)], 0.8),
            "The rows stay",
            (lambda: [FadeOut(conv), *[f.animate.set_opacity(0.35) for f in sf], *[d.animate.set_opacity(0.35) for d in ds]], 0.8),
        ])

        old = left_at(T("still on disk: older snapshots list them", 19, GOLD_M), SFX - 0.3, SFY + 0.75)
        ex = M("CALL lake.system.expire_snapshots(...)", 16, RED_M).move_to([0, -3.15, 0])
        self.steps("The 15 small files stay on disk, because older snapshots still list them. "
                   "Expiring old snapshots deletes the files only they used, and time travel to those snapshots ends.", [
            (lambda: [Transform(lab1, old), FadeOut(lab2)], 0.8),
            "Expiring old",
            (lambda: [Transform(call, ex)], 0.6),
            (lambda: [LaggedStart(*[f.animate.set_stroke(RED_M).set_opacity(0.5) for f in sf + ds], lag_ratio=0.02)], 0.8),
            (lambda: [LaggedStart(*[FadeOut(f, scale=0.6) for f in sf + ds], lag_ratio=0.02)], 0.9),
            "and time travel",
            (lambda: [Transform(lab1, left_at(T("time travel to them: snapshot not found", 19, RED_M), SFX - 0.3, SFY + 0.75))], 0.7),
        ])

        c1 = chip("copy on write: the writer pays", GREEN_M, 20).move_to([-3.1, 1.2, 0])
        c2 = chip("merge on read: every reader pays", TEAL_M, 20).move_to([3.1, 1.2, 0])
        self.steps("Files never change, so every correction is paid for: by the writer with copy on write, "
                   "or by every reader with merge on read, until compaction clears the debt.", [
            (lambda: [FadeOut(lab1), FadeOut(call)], 0.6),
            "by the writer",
            (lambda: [FadeIn(c1, shift=0.1 * DOWN)], 0.6),
            "or by every reader",
            (lambda: [FadeIn(c2, shift=0.1 * DOWN)], 0.6),
            "until compaction",
            (lambda: [glow(big[0], GREEN_M, 1.04)], 0.9),
        ])
        self.wait(0.6)
