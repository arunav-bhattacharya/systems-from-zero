from sfz import *

SAY.insert(0, (r"\bParquet\b", "par-kay"))
SAY.insert(0, (r"\bwrite\.merge\.mode\b", "write dot merge dot mode"))
SAY.insert(0, (r"\bMERGE INTO\b", "merge into"))
SAY.insert(0, (r"\bUPDATE\b", "update"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
DX = [-4.6, -1.3, 2.0]                    # the three day files
DY, DW, DH = 1.15, 2.9, 2.3
SY = -0.75                                # small data files and delete slips under each day file
HEAD_Y, CNT_Y, CAP_Y, BAR_Y = 2.85, -1.8, -3.3, -2.5
NOTE_X = 3.75
RED_ROWS = (2, 5)


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

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

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

    def note(self, k, s, color=GREY_B, size=20, y=None):
        m = fit(T(s, size, color), 6.6 - NOTE_X)
        return self.put(f"n{k}", m.move_to([NOTE_X + m.width / 2, y if y is not None else 2.2 - 0.48 * k, 0]))

    def notes_off(self):
        return self.drop(*[f"n{k}" for k in range(8)])

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(c, w, h, color, fill=None):
    return RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(
        fill if fill is not None else fillc(color), 1).move_to(c)


def dot_run(a, b, color=YELLOW_M, rt=0.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.1))


def ink(x, color, red=True):
    g = VGroup()
    for i in range(8):
        y = DY + 0.45 - 0.2 * i
        c = RED_M if (red and i in RED_ROWS) else color
        g.add(Line([x - 1.15, y, 0], [x + 1.15 - 0.35 * (i % 3), y, 0], stroke_width=2.5 if c is RED_M else 2, color=c))
    return g


def day_file(k, kind="file", color=BLUE_M, red=True):
    x = DX[k]
    title = {"file": f"day {k + 1}: 100,000 rows", "page": f"day {k + 1} page", "copy": f"day {k + 1}: new copy"}[kind]
    return VGroup(rbox([x, DY, 0], DW, DH, color, BLACK), T(title, 21, color).move_to([x, DY + 0.85, 0]), ink(x, GREY_C, red))


def small(k, color, s, dx):
    c = np.array([DX[k] + dx, SY, 0])
    return VGroup(rbox(c, 1.35, 0.62, color), T(s, 19, color).move_to(c))


def new_rows(k):
    return small(k, GREEN_M, "new rows", -0.72)


def slip(k):
    return small(k, RED_M, "deletes", 0.72)


class IcebergDeletes(Base):
    """batch-12, section 0. Notebooks in pen and 30 refunds (10 per day). Parquet can't be edited, so MERGE INTO writes
    new files two ways. Copy-on-write: 3 files rewritten, 3.1 MB, 299,970 unchanged rows copied. Merge-on-read: 3 small
    data files (6.4 KB) and 3 position delete files (7.4 KB, e.g. row 1,000 of the day 1 file); a read opens 9 files,
    and after five batches 33. Format v3: one deletion vector per data file (3 in one 1.7 KB file). Rule: rare, large
    changes: copy-on-write; frequent, small: merge-on-read. Check: corrections every 5 minutes, read once a night."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("30 refunds in ink", "copy the page, or pin a slip?")

        # ---------------- scene 1: ink ----------------
        files = [day_file(k, "page", GOLD_M, red=False) for k in range(3)]
        reds = [VGroup(*[l.copy().set_color(RED_M).set_stroke(width=2.5) for i, l in enumerate(f[2]) if i in RED_ROWS]) for f in files]
        self.steps("Picture a shop that keeps its sales in notebooks, in pen, one page per day. "
                   "One evening, 30 refunds come in, 10 from each of the last three days.", [
            (lambda: [LaggedStart(*[FadeIn(f) for f in files], lag_ratio=0.2)], 1.0),
            "30 refunds",
            (lambda: [LaggedStart(*[Create(r) for r in reds], lag_ratio=0.2), *self.cap("30 refunds: 10 on each page", RED_M)], 1.0),
        ])
        ghost = VGroup(rbox([DX[0], DY, 0], DW, DH, GOLD_M, BLACK), T("copied out", 21, GOLD_M).move_to([DX[0], DY + 0.85, 0]),
                       ink(DX[0], GREY_C, False)).set_opacity(0.0)
        pin = small(2, RED_M, "corrections", 0.0)
        self.steps("You can't rub out ink. So what do you do? Copy the three pages out again, with the changes? "
                   "Or leave them alone, and pin a slip of corrections to each? Hold that choice.", [
            "You can't rub out",
            (lambda: self.cap("you can't rub out ink", WHITE), 0.5),
            "Copy the three pages",
            (lambda: [files[0].animate.shift(0.25 * (UP + LEFT)).set_opacity(0.35),
                      *self.cap("copy the pages out again?", GOLD_M)], 0.8),
            "pin a slip",
            (lambda: [FadeIn(pin, shift=0.2 * UP), *self.cap("or pin a slip of corrections to each?", RED_M)], 0.7),
            "Hold that",
            (lambda: [files[0].animate.shift(0.25 * (DOWN + RIGHT)).set_opacity(1), FadeOut(pin)], 0.6),
        ], after=0.3)

        # ---------------- scene 2: the ordinary way ----------------
        dfiles = [day_file(k) for k in range(3)]
        self.steps("A payments company meets exactly this. Every evening, a file of refunds arrives: "
                   "30 payments whose status must change from captured to refunded.", [
            (lambda: [*[FadeOut(r) for r in reds], *[ReplacementTransform(f, d) for f, d in zip(files, dfiles)],
                      *self.put("head", T("payments: one file per day", 22, GREY_B).move_to([-1.3, HEAD_Y, 0]))], 1.0),
            "30 payments",
            (lambda: [*self.cap(M("status: CAPTURED → REFUNDED, for 30 payments", 20, WHITE))], 0.6),
        ])
        self.steps("In an ordinary database, the program that stores tables and answers questions about them, "
                   "one UPDATE command changes the 30 rows in place. Done.", [
            "one UPDATE",
            (lambda: [*self.cap(M("UPDATE payments SET status = 'REFUNDED' WHERE ...", 20, TEAL_M))], 0.6),
            "in place",
            (lambda: [*[Indicate(VGroup(*[l for i, l in enumerate(d[2]) if i in RED_ROWS]), color=TEAL_M, scale_factor=1.05) for d in dfiles]], 0.9),
        ], after=0.3)
        self.stamp("update")

        # ---------------- scene 3: files that can't change ----------------
        self.steps("But our table is an Iceberg table. Apache Iceberg is a free format for tables made of plain files, and those files are never edited. "
                   "The rows sit in Parquet files, a common file format for tables stored by column.", [
            (lambda: self.cap("an Iceberg table: its files are never edited", WHITE), 0.6),
            "The rows sit",
            (lambda: [*self.put("head", T("payments: one Parquet file per day", 22, GREY_B).move_to([-1.3, HEAD_Y, 0]))], 0.6),
        ])
        foot = [Rectangle(width=DW - 0.3, height=0.2, stroke_width=0).set_fill(YELLOW_M, 0.5).move_to([x, DY - 0.95, 0]) for x in DX]
        self.steps("The columns are squeezed, and a summary at the end of the file records where each one sits, and its smallest and largest values. "
                   "Change one value, and all of that is wrong. So the file is the page in ink.", [
            "a summary at the end",
            (lambda: [*[FadeIn(f) for f in foot], *self.note(0, "summary at the end:", YELLOW_M), *self.note(1, "where each column sits,", YELLOW_M),
                      *self.note(2, "smallest and largest values", YELLOW_M)], 0.7),
            "Change one value",
            (lambda: [*[f.animate.set_fill(RED_M, 0.6) for f in foot], *self.cap("change one value, and the summary is wrong", RED_M)], 0.6),
            "the page in ink",
            (lambda: [*self.cap("a Parquet file = a page in ink", WHITE)], 0.5),
        ])
        self.steps("Every change is written as new files, and a commit, a new snapshot of the table, makes them visible. "
                   "The command is MERGE INTO. It matches the refunds to the table on the payment number. "
                   "Under it, there are two ways to write the files.", [
            (lambda: [*[FadeOut(f) for f in foot], *self.notes_off(), *self.cap("every change: new files, then a commit", WHITE)], 0.6),
            "The command is",
            (lambda: [*self.cap(M("MERGE INTO payments USING refunds ON payment_id ...", 20, TEAL_M))], 0.6),
            "two ways",
            (lambda: [*self.note(0, "1. copy the page out", GOLD_M), *self.note(1, "2. pin a slip", RED_M)], 0.6),
        ], after=0.3)

        # ---------------- scene 4: copy the page out ----------------
        copies = [day_file(k, "copy", GOLD_M, red=False) for k in range(3)]
        for c in copies:
            for i, l in enumerate(c[2]):
                if i in RED_ROWS:
                    l.set_color(GREEN_M).set_stroke(width=2.5)
        sweeps = [Line([x - 1.3, DY + 0.6, 0], [x + 1.3, DY + 0.6, 0], stroke_width=4, color=YELLOW_M).set_z_index(5) for x in DX]
        self.steps("Way one: copy the page out. Find every file that holds a row to change, read it whole, and write a new copy with the change made. "
                   "The commit swaps the old files for the new ones.", [
            (lambda: [*self.notes_off(), *self.cap("way one: copy the page out", GOLD_M)], 0.5),
            "read it whole",
            (lambda: [*[FadeIn(s) for s in sweeps]], 0.2),
            (lambda: [*[s.animate.shift(1.45 * DOWN) for s in sweeps]], 1.0),
            (lambda: [*[FadeOut(s) for s in sweeps]], 0.2),
            "write a new copy",
            (lambda: [*[FadeIn(c, shift=0.1 * DOWN) for c in copies]], 0.9),
            "The commit swaps",
            (lambda: [*[FadeOut(d) for d in dfiles], *self.cap("the commit swaps the old files for the new copies", WHITE)], 0.6),
        ])
        self.steps("To change 30 rows, how many unchanged rows did it copy? Pause and guess.", [
            (lambda: self.cap("30 rows changed: how many unchanged rows copied?  pause and guess", YELLOW_M), 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("299,970. Three whole files, 3.1 MB, rewritten for 30 rows.", [
            (lambda: [*self.put("cnt", T("written: 3.1 MB      unchanged rows copied: 299,970", 24, GOLD_M).move_to([0, CNT_Y, 0])),
                      *self.uncap()], 0.7),
            "Three whole files",
            (lambda: [*[glow(c[0], GOLD_M, 1.03) for c in copies]], 0.8),
        ])
        self.steps("This is called copy-on-write, and it's Iceberg's default. Readers notice nothing, because the table is still just plain data files.", [
            (lambda: self.cap("copy-on-write: Iceberg's default", GOLD_M), 0.6),
            "Readers notice nothing",
            (lambda: [*self.note(0, "a read opens 3 files", GREEN_M)], 0.6),
        ])
        self.steps("But it breaks when changes are small and frequent. Corrections every 5 minutes, against files of 512 MB, "
                   "and you're rewriting gigabytes an hour to change a few hundred rows. That's copying out the whole notebook to fix one smudge.", [
            "Corrections every 5 minutes",
            (lambda: [*self.note(1, "every 5 minutes,", RED_M), *self.note(2, "512 MB files:", RED_M)], 0.6),
            "rewriting gigabytes",
            (lambda: [*self.note(3, "gigabytes an hour", RED_M)], 0.5),
            "copying out the whole notebook",
            (lambda: self.cap("copying out the whole notebook to fix one smudge", WHITE), 0.6),
        ], after=0.3)
        self.stamp("cow")

        # ---------------- scene 5: pin a slip ----------------
        dfiles = [day_file(k) for k in range(3)]
        nrs = [new_rows(k) for k in range(3)]
        sls = [slip(k) for k in range(3)]
        self.steps("Way two: pin a slip. Back to the original files, and leave them alone.", [
            (lambda: [*self.notes_off(), *self.drop("cnt"), *[FadeOut(c) for c in copies], *[FadeIn(d) for d in dfiles],
                      *self.cap("way two: pin a slip", RED_M)], 0.8),
        ])
        self.steps("Write the new versions of the 30 rows into small new data files, plus delete files that say which old rows no longer count.", [
            "small new data files",
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.15 * UP) for n in nrs], lag_ratio=0.2)], 0.8),
            "plus delete files",
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.15 * UP) for s in sls], lag_ratio=0.2)], 0.8),
        ])
        pos = VGroup(*[T(s, 19, RED_M) for s in ("day 1 file, row 0", "day 1 file, row 1,000", "day 1 file, row 2,000", "...")]
                     ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        pos.move_to([NOTE_X + pos.width / 2, 1.2, 0])
        self.steps("Each line of a delete file names a data file and a row position in it, such as row 1,000 of the day 1 file. "
                   "That's called a position delete.", [
            "Each line",
            (lambda: [glow(sls[0][0], RED_M, 1.06), FadeIn(pos, shift=0.1 * LEFT)], 0.8),
            "row 1,000",
            (lambda: [Indicate(pos[1], color=RED_M, scale_factor=1.08), Indicate(dfiles[0][2][RED_ROWS[0]], color=RED_M)], 0.8),
            "a position delete",
            (lambda: self.cap("position delete: a file and a row position", WHITE), 0.6),
        ])
        self.steps("The same 30 refunds wrote 6.4 KB of new rows and 7.4 KB of delete files. About 14 KB, instead of 3.1 MB. This is merge-on-read.", [
            "The same 30",
            (lambda: [*self.put("cnt", T("written: 6.4 KB of new rows + 7.4 KB of deletes", 24, GREEN_M).move_to([0, CNT_Y, 0]))], 0.6),
            "About 14 KB",
            (lambda: [*self.put("cnt", T("written: about 14 KB, instead of 3.1 MB", 24, GREEN_M).move_to([0, CNT_Y, 0]))], 0.6),
            "This is merge-on-read",
            (lambda: [FadeOut(pos), *self.cap("merge-on-read: leave the files, write the change and a delete note", RED_M)], 0.6),
        ], after=0.3)
        self.stamp("mor")

        # ---------------- scene 6: the reader's bill ----------------
        rd = np.array([-1.3, CNT_Y - 0.4, 0])
        targets = [d[0].get_bottom() for d in dfiles] + [n.get_bottom() for n in nrs] + [s.get_bottom() for s in sls]
        self.steps("And here's the catch. The cost moved to the reader. Every read of a data file must also read its delete files, "
                   "and skip the rows they list. One batch turned 3 files into 9.", [
            (lambda: [*self.drop("cnt"), *self.cap("the cost moved to the reader", WHITE)], 0.5),
            "Every read",
            (lambda: [LaggedStart(*[dot_run(rd, t, YELLOW_M, 0.5) for t in targets], lag_ratio=0.12)], 1.6),
            "skip the rows",
            (lambda: [*[VGroup(*[l for i, l in enumerate(d[2]) if i in RED_ROWS]).animate.set_opacity(0.25) for d in dfiles]], 0.6),
            "3 files into 9",
            (lambda: [*self.put("cnt", T("a read opens 9 files: 6 data files + 3 delete files", 24, YELLOW_M).move_to([0, CNT_Y, 0]))], 0.6),
        ])
        nstack = VGroup(*[nrs[k][0].copy().set_z_index(-1).shift(0.08 * j * DOWN + 0.03 * j * LEFT) for k in range(3) for j in range(1, 5)])
        sstack = VGroup(*[sls[k][0].copy().set_z_index(-1).shift(0.08 * j * DOWN + 0.03 * j * RIGHT) for k in range(3) for j in range(1, 5)])
        stacks = VGroup(nstack, sstack)
        self.steps("Here the notebook picture breaks. You'd read a slip once and remember it. The table's readers apply every delete file again, on every read.", [
            (lambda: self.cap("where the notebook picture breaks", WHITE), 0.5),
            "The table's readers",
            (lambda: [*self.cap("a person reads a slip once; a reader applies it on every read", WHITE),
                      LaggedStart(*[dot_run(rd, s.get_bottom(), YELLOW_M, 0.4) for s in sls] * 2, lag_ratio=0.15)], 1.4),
        ])
        self.steps("And corrections keep coming. After five batches, each day has 5 small data files and 5 delete files, "
                   "and every read opens 33 files. That's a lot of slips for one page.", [
            "After five batches",
            (lambda: [FadeIn(stacks, lag_ratio=0.05)], 1.0),
            "every read opens 33",
            (lambda: [*self.put("cnt", T("after 5 batches: a read opens 33 files", 24, RED_M).move_to([0, CNT_Y, 0]))], 0.6),
            "a lot of slips",
            (lambda: self.cap("a lot of slips for one page", WHITE), 0.5),
        ], after=0.3)
        self.stamp("bill")

        # ---------------- scene 7: deletion vectors ----------------
        vecs = [VGroup(rbox([DX[k] + 0.72, SY, 0], 1.35, 0.62, PURPLE_M), M("0010010", 18, PURPLE_M).move_to([DX[k] + 0.72, SY, 0])) for k in range(3)]
        self.steps("Iceberg's format version 3 trims part of that bill. It keeps one bitmap per data file, a row of bits with a 1 for each deleted row, "
                   "called a deletion vector.", [
            (lambda: [*self.cap("format version 3", WHITE)], 0.5),
            "one bitmap",
            (lambda: [FadeOut(sstack),
                      *[ReplacementTransform(s, v) for s, v in zip(sls, vecs)]], 0.9),
            "a row of bits",
            (lambda: [*self.note(0, "a 1 for each deleted row", PURPLE_M)], 0.5),
            "called a deletion vector",
            (lambda: self.cap("deletion vector: one bitmap per data file", PURPLE_M), 0.6),
        ])
        self.steps("A later delete in the same file joins the same bitmap, so a reader loads at most one per data file. "
                   "In the demo, all three vectors fit in one 1.7 KB file.", [
            "joins the same bitmap",
            (lambda: [Transform(vecs[0][1], M("0110010", 18, PURPLE_M).move_to(vecs[0][1])), glow(vecs[0][0], PURPLE_M, 1.06)], 0.7),
            "at most one",
            (lambda: [*self.note(1, "at most one per data file", PURPLE_M)], 0.5),
            "In the demo",
            (lambda: [*self.note(2, "demo: 3 vectors, one 1.7 KB file", PURPLE_M)], 0.6),
        ], after=0.3)

        # ---------------- scene 8: which way ----------------
        self.steps("So, copy the page or pin a slip? You choose per table, and per kind of change, with settings such as write.merge.mode.", [
            (lambda: [*self.notes_off(), *self.drop("cnt"), FadeOut(nstack), *self.cap("copy the page, or pin a slip?", YELLOW_M)], 0.6),
            "with settings",
            (lambda: self.cap(M("write.merge.mode = copy-on-write | merge-on-read", 20, TEAL_M)), 0.6),
        ])
        self.steps("Rare, large changes: copy-on-write. Frequent, small ones: merge-on-read. And remember that merge-on-read sends its readers a bill, "
                   "which a cleanup job, called compaction, has to pay later.", [
            (lambda: [*self.note(0, "rare, large changes:", GOLD_M, 20), *self.note(1, "copy-on-write", GOLD_M, 20)], 0.6),
            "Frequent, small",
            (lambda: [*self.note(2, "frequent, small ones:", RED_M, 20), *self.note(3, "merge-on-read", RED_M, 20)], 0.6),
            "a cleanup job",
            (lambda: self.cap("merge-on-read's bill: paid later by compaction", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 9: moral and check ----------------
        self.steps("So the moral of the story. A file that can't be edited leaves two choices. Copy the page, and pay once, when you write. "
                   "Or pin a slip, and pay a little every time you read.", [
            (lambda: self.cap("copy the page: pay once, when you write", GOLD_M), 0.6),
            "Or pin a slip",
            (lambda: self.cap("pin a slip: pay a little every time you read", RED_M), 0.6),
        ], after=0.3)
        self.steps("One quick check. A table gets a batch of corrections every five minutes, and a report reads it once a night. "
                   "Which way? Pause and think.", [
            (lambda: [*self.notes_off(), *self.cap("corrections every 5 minutes; one read a night", WHITE)], 0.6),
            "Pause and think",
            (lambda: self.cap("which way?  pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Merge-on-read. The changes are small and frequent, and the reader comes only once a night. Just tidy the slips away now and then.", [
            (lambda: [*self.cap("merge-on-read", RED_M), *[glow(v[0], PURPLE_M, 1.06) for v in vecs],
                      *[glow(n[0], GREEN_M, 1.06) for n in nrs]], 0.7),
            "Just tidy",
            (lambda: self.cap("small and frequent: pin a slip, and tidy up now and then", YELLOW_M), 0.6),
        ], after=0.3)
        self.wait(2.0)
