from sfz import *

SAY.insert(0, (r"\bParquet\b", "par-kay"))


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
Q_Y = 3.2
HEAD_Y = 2.5
ROW_Y = [1.85, 0.97, 0.09, -0.79]
CW, CH, CG = 1.15, 0.72, 0.06
GX0 = -4.95
CX = [GX0 + CW / 2 + j * (CW + CG) for j in range(5)]
G_X1 = CX[-1] + CW / 2
LBL_X, LBL_W = 3.15, 3.4                      # the label beside each row (min..max of amount)
MARK_X = LBL_X + LBL_W / 2 + 0.45
FOOT_Y = -1.6
C1_Y, C2_Y, BAR_Y, CAP_Y = -2.2, -2.62, -2.98, -3.35
COLS = ["payment", "merchant", "country", "status", "amount"]
SORTED = ["100..63,031", "63,033..125,677", "125,677..188,240", "188,241..250,099"]
BOXES = ["books, A to F", "books, G to L", "books, M to R", "books, S to Z"]


class ParquetPushdown(Base):
    """batch-05, section 2. Moving boxes with narrow labels vs boxes all labelled "books". A Parquet file: 4 row groups
    of 5 column chunks, and a footer with each chunk's min and max. amount > 150,000 on the sorted file skips row
    groups 0 and 1 (788,725 of 3,631,674 bytes; 199,296 rows unpacked, 160,308 match): predicate pushdown. On the
    random file every range is 100..~250,000, so > 240,000 reads all 400,000 rows (96% thrown away) against 98,944 on
    the sorted file, the same 16,200 matches. Sort by the column you filter on; a file can't be repacked."""

    def query(self, s, color=YELLOW_M):
        return self.put("q", fit(chip(s, color, 20, mono=True), 12.8).move_to([0, Q_Y, 0]))

    def c1(self, s, color=WHITE):
        return self.put("c1", fit(T(s, 24, color), 12.8).move_to([0, C1_Y, 0]))

    def c2(self, s, color=WHITE):
        return self.put("c2", fit(T(s, 24, color), 12.8).move_to([0, C2_Y, 0]))

    def set_label(self, r, s, color=GOLD_M):
        return self.put(f"l{r}", fit(M(s, 17, color), LBL_W - 0.3).move_to([LBL_X, ROW_Y[r], 0]))

    def fname(self, s):
        return self.put("f", M(s, 20, BLUE_M).move_to([LBL_X, HEAD_Y, 0]))

    def mark(self, r, ok):
        m = tick(ok, 0.15).move_to([MARK_X, ROW_Y[r], 0])
        return self.put(f"m{r}", m)

    def clear_marks(self):
        return self.drop(*[f"m{r}" for r in range(4)])

    def read_row(self, r, cols=range(5)):
        return [self.cells[r][j].animate.set_fill(fillc(YELLOW_M, 0.45), 1).set_stroke(YELLOW_M) for j in cols]

    def skip_row(self, r):
        return [self.cells[r][j].animate.set_opacity(0.2) for j in range(5)] + [self.rgl[r].animate.set_opacity(0.35)] + \
               self.mark(r, False)

    def reset_cells(self, pruned=()):
        out = [h.animate.set_opacity(0.35 if j in pruned else 1) for j, h in enumerate(self.heads)]
        for r in range(4):
            out.append(self.rgl[r].animate.set_opacity(1))
            for j in range(5):
                c = self.cells[r][j]
                op = 0.25 if j in pruned else 1
                out.append(c.animate.set_fill(fillc(BLUE_M), 1).set_stroke(BLUE_M, 2.5).set_opacity(op))
        return out

    def construct(self):
        self.lab = {}
        self.title_card("A label on every box", "how a Parquet reader skips rows")

        # ---------------- scene 1: moving house ----------------
        boxes = []
        for r in range(4):
            b = frame_box((GX0 + G_X1) / 2, ROW_Y[r], G_X1 - GX0, CH, GOLD_M, 0.22)
            tape = Line([(GX0 + G_X1) / 2, ROW_Y[r] + CH / 2, 0], [(GX0 + G_X1) / 2, ROW_Y[r] - CH / 2, 0], stroke_width=6,
                        color=interpolate_color(ManimColor(GOLD_M), ManimColor("#000000"), 0.4))
            boxes.append(VGroup(b, tape))
        papers = [frame_box(LBL_X, ROW_Y[r], LBL_W, CH, WHITE, 0.0).set_stroke(GREY_B, 2) for r in range(4)]
        self.steps("Picture moving house. You pack your books into twenty boxes, and label each one: books, authors A to C.", [
            "You pack",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.2 * DOWN) for b in boxes], lag_ratio=0.2),
                      *self.cap("four of the twenty boxes")], 1.0),
            "and label",
            (lambda: [*[FadeIn(p) for p in papers], *[x for r in range(4) for x in self.set_label(r, BOXES[r], WHITE)]], 0.8),
        ])
        self.steps("To find a cookbook by Moreno, you open one box. A friend packed hers in any order, and labelled every box: "
                   "books. She opens all twenty.", [
            "To find",
            (lambda: self.cap("a cookbook by Moreno", WHITE), 0.5),
            "you open one box",
            (lambda: [glow(boxes[2][0], YELLOW_M, 1.02), Indicate(self.lab["l2"], color=YELLOW_M, scale_factor=1.15)], 0.9),
            "A friend",
            (lambda: [*[x for r in range(4) for x in self.set_label(r, "books", WHITE)], *self.cap("the friend's boxes", WHITE)], 0.7),
            "She opens all",
            (lambda: [LaggedStart(*[glow(b[0], YELLOW_M, 1.02) for b in boxes], lag_ratio=0.2)], 1.2),
        ])
        self.steps("Data files have the same problem. Two files hold the same 400,000 payments. Ask both for every payment above "
                   "2,400 euros.", [
            (lambda: [*self.cap("two files, the same 400,000 payments", WHITE), *[x for r in range(4) for x in self.drop(f"l{r}")]], 0.6),
            "Ask both",
            (lambda: self.query("WHERE amount_cents > 240000      (above 2,400 euros)"), 0.6),
        ])
        self.steps("From one, the reader fetches 383 kilobytes. From the other, 2.3 megabytes. The same 16,200 rows come back. "
                   "Only the order of the rows differs. So what is the reader looking at?", [
            "From one",
            (lambda: self.c1("one file: 383 kB read", GREEN_M), 0.5),
            "From the other",
            (lambda: self.c2("the other: 2.3 MB read", RED_M), 0.5),
            "The same 16,200",
            (lambda: self.cap("the same 16,200 rows back from both", WHITE), 0.5),
            "Only the order",
            (lambda: self.cap("only the order of the rows differs", YELLOW_M), 0.5),
        ])
        self.stamp("s2")

        # ---------------- scene 2: inside a Parquet file ----------------
        self.cells = [[Rectangle(width=CW, height=CH, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M), 1)
                       .move_to([CX[j], ROW_Y[r], 0]) for j in range(5)] for r in range(4)]
        allc = VGroup(*[c for row in self.cells for c in row])
        heads = self.heads = [fit(T(COLS[j], 18, GREY_B), CW - 0.05).move_to([CX[j], HEAD_Y, 0]) for j in range(5)]
        self.rgl = [T(f"row group {r}", 18, GREY_B).move_to([(-6.55 + GX0) / 2 - 0.05, ROW_Y[r], 0]) for r in range(4)]
        self.steps("These are Parquet files. Parquet is a file format that stores a table column by column.", [
            (lambda: [*self.drop("q", "c1", "c2"), *self.cap("Parquet: a file format that stores a table column by column", WHITE)], 0.5),
            (lambda: [*[FadeOut(b) for b in boxes], FadeIn(allc), *[FadeIn(h) for h in heads]], 1.0),
        ])
        self.steps("The rows are cut into blocks called row groups, here four of about 100,000 rows. Inside a row group, each "
                   "column sits together, as one chunk.", [
            "row groups",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * RIGHT) for l in self.rgl], lag_ratio=0.2),
                      *self.cap("row groups: here 4, of about 100,000 rows each")], 1.0),
            "as one chunk",
            (lambda: [*self.cap("each column of a row group: one chunk"), glow(self.cells[1][4], YELLOW_M, 1.08)], 0.8),
        ])
        self.steps("A fraud analyst, someone who hunts for stolen cards, asks for three columns of every payment above 1,500 euros.", [
            (lambda: self.cap("a fraud analyst: someone who hunts for stolen cards", WHITE), 0.5),
            "asks for three",
            (lambda: [*self.query("SELECT merchant_id, status, amount_cents ... WHERE amount_cents > 150000"),
                      *self.fname("sorted.parquet")], 0.7),
        ])
        self.steps("The reader skips the two columns she didn't name. That's column pruning. But can it skip rows too, before "
                   "reading them?", [
            "skips the two",
            (lambda: [*[self.cells[r][j].animate.set_opacity(0.25) for r in range(4) for j in (0, 2)],
                      heads[0].animate.set_opacity(0.35), heads[2].animate.set_opacity(0.35)], 0.7),
            "column pruning",
            (lambda: self.cap("column pruning: 2 of 5 columns not needed, in any row group", WHITE), 0.5),
            "But can it skip rows",
            (lambda: self.cap("can it skip rows too, before reading them?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 3: the footer is the label sheet ----------------
        foot = frame_box((-6.45 + LBL_X + LBL_W / 2) / 2, FOOT_Y, LBL_X + LBL_W / 2 + 6.45, 0.55, GOLD_M)
        foot_t = T("footer: every chunk's offset, size, min and max", 20, GOLD_M).move_to(foot)
        self.steps("It can, with the footer. At the end of the file, the footer lists every chunk: where it starts, how big it is, "
                   "and its smallest and largest value, its min and max.", [
            (lambda: [*self.drop("cap"), FadeIn(foot, shift=0.1 * UP), FadeIn(foot_t)], 0.7),
            "where it starts",
            (lambda: self.cap("where it starts (offset), how big it is (size)"), 0.5),
            "its smallest",
            (lambda: self.cap("its smallest and largest value: min and max", WHITE), 0.5),
        ])
        self.steps("Remember the moving boxes? The footer is the label from every box, copied onto one sheet.", [
            (lambda: [glow(foot, GOLD_M, 1.02), *[glow(p, GOLD_M, 1.03) for p in papers]], 1.0),
            "copied onto",
            (lambda: self.cap("the footer = every box's label, on one sheet", WHITE), 0.5),
        ])

        def label_from_footer(r, s):
            dot = Dot(radius=0.07, color=GOLD_M).move_to(foot.get_top())
            return [Succession(FadeIn(dot, run_time=0.05), dot.animate(run_time=0.5).move_to([LBL_X, ROW_Y[r], 0]),
                               FadeOut(dot, run_time=0.1)), *self.set_label(r, "amount " + s)]

        self.steps("So the reader reads the footer first. In this file, sorted by amount, row group zero holds amounts from 100 "
                   "to 63,031 cents. Row group one, up to 125,677. Two, up to 188,240. And three, up to 250,099.", [
            (lambda: self.cap("the reader reads the footer first", WHITE), 0.5),
            "row group zero",
            (lambda: label_from_footer(0, SORTED[0]), 0.7),
            "Row group one",
            (lambda: label_from_footer(1, SORTED[1]), 0.7),
            "Two,",
            (lambda: label_from_footer(2, SORTED[2]), 0.7),
            "And three",
            (lambda: label_from_footer(3, SORTED[3]), 0.7),
        ])

        # ---------------- scene 4: skip by the label ----------------
        self.steps("The analyst wants amounts above 150,000 cents. Which row groups can the reader skip, without reading a byte "
                   "of them? Pause and guess.", [
            (lambda: self.cap("amount above 150,000 cents", WHITE), 0.5),
            "Which row groups",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"l{r}"], color=YELLOW_M, scale_factor=1.1) for r in range(4)], lag_ratio=0.2)], 1.2),
            "Pause and guess",
            (lambda: self.cap("which row groups can it skip? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Zero and one. Their largest amounts are below 150,000, so no row in them can match. Two and three might, so "
                   "the reader fetches them.", [
            (lambda: [*self.skip_row(0), *self.skip_row(1), *self.cap("max below 150,000: no row can match, skip it", WHITE)], 0.8),
            "Two and three",
            (lambda: [*self.mark(2, True), *self.mark(3, True), *self.cap("might match: fetch")], 0.6),
            "fetches them",
            (lambda: [*self.read_row(2, (1, 3, 4)), *self.read_row(3, (1, 3, 4))], 0.7),
        ])
        self.steps("Six chunks, 788,725 bytes of the file's 3.6 million. About a fifth.", [
            (lambda: self.c1("read: 6 chunks, 788,725 of 3,631,674 bytes (22%)", GREEN_M), 0.6),
        ])
        self.stamp("poster")
        self.steps("Min and max work on whole row groups, though. Row group two starts at 125,677, below the line. So the reader "
                   "unpacks all 199,296 rows of groups two and three, and a filter keeps the 160,308 that match.", [
            (lambda: self.cap("min and max work on whole row groups", WHITE), 0.5),
            "Row group two starts",
            (lambda: [Indicate(self.lab["l2"], color=RED_M, scale_factor=1.12)], 0.8),
            "So the reader unpacks",
            (lambda: self.c2("199,296 rows unpacked, 160,308 match"), 0.6),
        ])

        # ---------------- scene 5: the name ----------------
        self.steps("Checking a filter against these numbers, inside the file reader, is called predicate pushdown. A predicate is "
                   "a condition, like amount above 150,000. Pushing it down means handing it from the query to the reader.", [
            "is called predicate",
            (lambda: self.cap("predicate pushdown", YELLOW_M, 30), 0.6),
            "A predicate is",
            (lambda: self.cap("predicate: a condition, like amount_cents > 150000", WHITE), 0.5),
            "Pushing it down",
            (lambda: [*self.cap("pushing it down: handing it from the query to the reader", WHITE), glow(foot, YELLOW_M, 1.02)], 0.7),
        ])
        self.stamp("s6")

        # ---------------- scene 6: the other file ----------------
        self.steps("Now the other file. Same payments, written in the order they happened. Every row group holds amounts from 100 "
                   "to about 250,000.", [
            (lambda: [*self.reset_cells(pruned=(0, 2, 3)), *self.clear_marks(), *self.drop("c1", "c2"), *self.fname("random.parquet"),
                      *self.query("SELECT merchant_id, amount_cents ... WHERE amount_cents > 240000"),
                      *self.cap("same payments, in the order they happened")], 0.8),
            "Every row group",
            (lambda: [*[x for r in range(4) for x in self.set_label(r, "amount 100..~250,000")]], 0.7),
        ])
        self.steps("Ask for amounts above 240,000. How many row groups can the reader skip? Pause and guess.", [
            (lambda: self.cap("amount above 240,000", WHITE), 0.5),
            "Pause and guess",
            (lambda: self.cap("how many row groups can it skip? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("None. Every label says: maybe. That's the friend's boxes, every one labelled books.", [
            (lambda: [*[x for r in range(4) for x in self.mark(r, True)], *self.cap("none: every label says maybe", RED_M)], 0.7),
            "the friend's",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"l{r}"], color=WHITE, scale_factor=1.1) for r in range(4)], lag_ratio=0.15)], 1.0),
        ])
        self.steps("The reader unpacks all 400,000 rows, and the filter throws away 96% of them.", [
            (lambda: [*[a for r in range(4) for a in self.read_row(r, (1, 4))]], 0.8),
            (lambda: [*self.c1("random: 400,000 rows unpacked, 16,200 match (96% thrown away), 2.3 MB", RED_M)], 0.6),
        ])
        self.steps("On the sorted file, it reads one row group of four, 98,944 rows. Same 16,200 answers.", [
            (lambda: [*self.reset_cells(pruned=(0, 2, 3)), *self.clear_marks(), *self.fname("sorted.parquet"),
                      *[x for r in range(4) for x in self.set_label(r, "amount " + SORTED[r])]], 0.8),
            (lambda: [*self.skip_row(0), *self.skip_row(1), *self.skip_row(2), *self.mark(3, True), *self.read_row(3, (1, 4))], 0.8),
            "98,944",
            (lambda: self.c2("sorted: 98,944 rows unpacked, 16,200 match, 383 kB", GREEN_M), 0.6),
        ])
        self.steps("Pushdown was on both times. It just had nothing to push against.", [
            (lambda: self.cap("pushdown was on both times", WHITE), 0.5),
            "It just had",
            (lambda: self.cap("on the random file, it had nothing to push against", WHITE), 0.5),
        ])

        # ---------------- scene 7: guardrails ----------------
        self.steps("So, min and max skip only what sorting made tidy. Sort each file by the column you filter on most.", [
            (lambda: [*self.drop("c1", "c2"), *self.cap("min and max skip only what sorting made tidy", WHITE)], 0.6),
            "Sort each file",
            (lambda: self.cap("sort each file by the column you filter on most", YELLOW_M), 0.5),
        ])
        self.steps("But one sort tidies one column. In the sorted file, the merchant column still runs from 0 to 499 in every row group.", [
            (lambda: self.cap("one sort tidies one column", WHITE), 0.5),
            "the merchant column",
            (lambda: [*self.reset_cells(pruned=()), *self.clear_marks(),
                      *[x for r in range(4) for x in self.set_label(r, "merchant 0..499", TEAL_M)]], 0.8),
            (lambda: [LaggedStart(*[self.cells[r][1].animate.set_stroke(TEAL_M, 5) for r in range(4)], lag_ratio=0.15)], 0.8),
        ])
        self.steps("And here the moving boxes break. You can repack a box when you notice the mess. A Parquet file is never "
                   "changed once it's written. To tidy one, you write a new file.", [
            (lambda: self.cap("where the moving boxes break", WHITE), 0.5),
            "A Parquet file",
            (lambda: self.cap("a Parquet file is never changed once written", RED_M), 0.5),
            "To tidy one",
            (lambda: self.cap("to tidy one, write a new file", WHITE), 0.5),
        ])

        # ---------------- scene 8: moral and check ----------------
        self.steps("The moral: a label only helps if it's narrow, and the order of the rows decides how narrow.", [
            (lambda: [*self.reset_cells(pruned=()), *[x for r in range(4) for x in self.set_label(r, "amount " + SORTED[r])],
                      *[s.animate.set_stroke(BLUE_M, 2.5) for s in [self.cells[r][1] for r in range(4)]],
                      *self.cap("a label only helps if it's narrow", WHITE)], 0.7),
            "the order of the rows",
            (lambda: self.cap("the order of the rows decides how narrow", YELLOW_M), 0.5),
        ], after=0.5)
        self.steps("One quick check, on the sorted file. Amounts below 50,000 cents. How many row groups does the reader open? "
                   "Pause and think.", [
            (lambda: self.cap("one quick check, on the sorted file", WHITE), 0.5),
            "Amounts below",
            (lambda: self.query("SELECT ... WHERE amount_cents < 50000"), 0.6),
            "Pause and think",
            (lambda: self.cap("how many row groups? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("One. Row group zero. Row group one starts at 63,033.", [
            (lambda: [*self.mark(0, True), *self.read_row(0), *self.skip_row(1), *self.skip_row(2), *self.skip_row(3),
                      *self.cap("one: row group 0", GREEN_M)], 0.8),
            "Row group one",
            (lambda: [Indicate(self.lab["l1"], color=YELLOW_M, scale_factor=1.12)], 0.8),
        ], after=0.3)
        self.wait(2.0)
