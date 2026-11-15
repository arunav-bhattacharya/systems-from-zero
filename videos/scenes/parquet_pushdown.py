from sfz import *

SAY.insert(0, (r"\bParquet\b", "parkay"))

COLS = ["payment_id", "merchant_id", "day", "status", "amount_cents"]
NEED = {1, 2, 4}                          # merchant_id, day, amount_cents
CXS = [-4.3 + 1.6 * i for i in range(5)]
CW, CH = 1.45, 0.55
RYS = [1.65, 0.95, 0.25, -0.45]           # row groups 0..3
HEAD_Y = 2.3
GX0, GX1 = CXS[0] - CW / 2, CXS[-1] + CW / 2
FOOT_Y = -1.25
DAY_X, MER_X, MARK_X = 3.95, 5.6, 6.38    # the footer's min and max, shown beside each row group
STATS = [("11-06", "0 to 249"), ("11-06", "250 to 499"), ("11-07", "0 to 249"), ("11-07", "250 to 499")]
BAR_Y, BX0, PER_MB = -2.6, -4.0, 2.0      # bytes read: 2 units per MB
FILE_MB = 3.97                            # 4 row groups of 993 KB, plus a 2 KB footer
AFTER_KB = 483                            # footer 2 + merchant_id 4 + day 1 + amount_cents 476


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


def chunk(r, c, color=GREY_B):
    return RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=color, stroke_width=2.5).set_fill(
        fillc(color), 1).move_to([CXS[c], RYS[r], 0])


def stat(r, k, s, color=GREY_A):
    return T(s, 18, color).move_to([DAY_X if k == 0 else MER_X, RYS[r], 0])


def bar_fill(mb, color=BLUE_M):
    w = max(mb * PER_MB, 0.02)
    return Rectangle(width=w, height=0.34, stroke_width=0).set_fill(color, 0.8).move_to([BX0 + w / 2, BAR_Y, 0])


def bar_text(s, color=GREY_A):
    return left_at(T(s, 18, color), BX0 + FILE_MB * PER_MB + 0.25, BAR_Y)


class ParquetPushdown(Base):
    """batch-05, sections 0 and 2: 400,000 payments over two days in one Parquet file (4.0 MB), written sorted by day
    then merchant: 4 row groups x 5 column chunks, footer with min and max. Query: merchant 42 on 11-07. The reader
    reads the tail, the footer, skips row groups 0, 1 (wrong day) and 3 (merchants 250 to 499), and reads 3 of 5 chunks
    of row group 2: 483 KB instead of 4.0 MB."""

    def construct(self):
        self.title_card("Parquet and predicate pushdown", "how a reader skips most of a file")

        q = chip("SELECT sum(amount_cents) WHERE merchant_id = 42 AND day = '2026-11-07'", GOLD_M, 16, mono=True)
        q.move_to([0, 3.2, 0])
        blk = RoundedRectangle(corner_radius=0.12, width=GX1 - GX0, height=RYS[0] - RYS[3] + CH, stroke_color=GREY_B,
                               stroke_width=2.5).set_fill(fillc(GREY_B), 1).move_to([(GX0 + GX1) / 2, (RYS[0] + RYS[3]) / 2, 0])
        blk_t = T("payments.parquet: 400,000 rows, 4 MB", 22, GREY_A).move_to(blk)
        self.steps("A query wants merchant 42's total for November 7th. Two days of payments sit in one Parquet file: "
                   "400,000 rows, about 4 megabytes. How much must the reader touch?", [
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.8),
            "Two days",
            (lambda: [FadeIn(blk), FadeIn(blk_t)], 0.9),
            "How much",
            (lambda: [glow(blk, GOLD_M, 1.02)], 0.9),
        ])

        blab = left_at(T("bytes read", 20, GREY_B), -6.5, BAR_Y)
        bout = Rectangle(width=FILE_MB * PER_MB, height=0.34, stroke_color=GREY_B, stroke_width=2).move_to(
            [BX0 + FILE_MB * PER_MB / 2, BAR_Y, 0])
        bf = bar_fill(0.001)
        bt = bar_text("0 MB")
        self.steps("The simplest reader reads all of it, and throws almost everything away.", [
            (lambda: [FadeIn(blab), Create(bout), FadeIn(bt)], 0.6),
            (lambda: [Transform(bf, bar_fill(FILE_MB, RED_M)), Transform(bt, bar_text("4.0 MB, all of it", RED_M)),
                      blk.animate.set_stroke(RED_M)], 1.6),
            "and throws",
            (lambda: [glow(blk, RED_M, 1.02)], 0.9),
        ])

        heads = VGroup(*[M(c, 14, GREY_B).move_to([CXS[i], HEAD_Y, 0]) for i, c in enumerate(COLS)])
        rgl = VGroup(*[right_at(T(f"row group {r}", 18, GREY_B), GX0 - 0.15, RYS[r]) for r in range(4)])
        ch = [[chunk(r, c) for c in range(5)] for r in range(4)]
        allch = VGroup(*[x for row in ch for x in row])
        self.steps("But Parquet cuts the rows into row groups of 100,000, and inside each group it stores every column "
                   "on its own, as a column chunk.", [
            (lambda: [Transform(bf, bar_fill(0.001)), Transform(bt, bar_text("0 MB")), FadeOut(blk_t)], 0.6),
            "But Parquet cuts",
            (lambda: [FadeOut(blk), *[FadeIn(VGroup(*ch[r])) for r in range(4)], FadeIn(rgl)], 1.0),
            "and inside each",
            (lambda: [FadeIn(heads), LaggedStart(*[glow(ch[r][2], BLUE_M, 1.06) for r in range(4)], lag_ratio=0.2)], 1.2),
        ])

        foot = RoundedRectangle(corner_radius=0.08, width=GX1 - GX0 - 1.6, height=CH, stroke_color=TEAL_M, stroke_width=2.5)
        foot.set_fill(fillc(TEAL_M), 1).move_to([GX0 + (GX1 - GX0 - 1.6) / 2, FOOT_Y, 0])
        foot_t = T("footer: where each chunk starts, its size, its min and max", 17, WHITE).move_to(foot)
        tail = RoundedRectangle(corner_radius=0.08, width=1.45, height=CH, stroke_color=TEAL_M, stroke_width=2.5)
        tail.set_fill(fillc(TEAL_M), 1).move_to([GX1 - 0.725, FOOT_Y, 0])
        tail_t = M("length+PAR1", 13, WHITE).move_to(tail)
        self.steps("Last, the writer adds the footer: where every chunk starts, how big it is, and the smallest and "
                   "largest value in it.", [
            (lambda: [FadeIn(foot, shift=0.1 * UP), FadeIn(foot_t, shift=0.1 * UP)], 0.8),
            (lambda: [FadeIn(tail), FadeIn(tail_t)], 0.5),
            "and the smallest",
            (lambda: [glow(foot, TEAL_M, 1.03)], 0.9),
        ])

        self.steps("So a reader starts at the back. It reads the last 8 bytes to learn the footer's length, "
                   "then the footer itself, about 2 kilobytes.", [
            (lambda: [glow(tail, BLUE_M, 1.08)], 0.8),
            "It reads the last",
            (lambda: [tail.animate.set_stroke(BLUE_M)], 0.5),
            "then the footer",
            (lambda: [foot.animate.set_stroke(BLUE_M), Transform(bf, bar_fill(0.002)), Transform(bt, bar_text("2 KB"))], 0.8),
        ])

        sh = VGroup(T("day", 16, GREY_B).move_to([DAY_X, HEAD_Y, 0]), T("merchant", 16, GREY_B).move_to([MER_X, HEAD_Y, 0]))
        st_title = T("in the footer: min to max", 16, TEAL_M).move_to([(DAY_X + MER_X) / 2, HEAD_Y + 0.38, 0])
        stats = [[stat(r, k, STATS[r][k]) for k in range(2)] for r in range(4)]
        self.steps("This file was written sorted by day, then by merchant. So the footer says row groups 0 and 1 hold "
                   "only November 6th, and 2 and 3 only November 7th.", [
            (lambda: [FadeIn(st_title), FadeIn(sh)], 0.6),
            "So the footer",
            (lambda: [LaggedStart(*[FadeIn(VGroup(*stats[r]), shift=0.1 * LEFT) for r in range(4)], lag_ratio=0.25)], 1.4),
            "only November 6th",
            (lambda: [*[stats[r][0].animate.set_color(GOLD_M) for r in range(4)]], 0.6),
        ])

        marks = {}

        def skip(r):
            marks[r] = tick(False, 0.14).move_to([MARK_X, RYS[r], 0])
            return [*[c.animate.set_opacity(0.18) for c in ch[r]], rgl[r].animate.set_opacity(0.3), Create(marks[r])]

        self.steps("Row groups 0 and 1 can't hold November 7th, so the reader skips them without reading a byte.", [
            (lambda: [stats[0][0].animate.set_color(RED_M), stats[1][0].animate.set_color(RED_M)], 0.6),
            "so the reader skips",
            (lambda: [*skip(0), *skip(1)], 0.9),
        ])

        self.steps("Row group 3 holds merchants 250 to 499. Merchant 42 can't be there, so it's skipped too.", [
            (lambda: [stats[3][1].animate.set_color(RED_M), stats[2][0].animate.set_color(GREY_A),
                      stats[3][0].animate.set_color(GREY_A)], 0.7),
            "so it's skipped",
            (lambda: skip(3), 0.8),
        ])

        ok2 = tick(True, 0.15).move_to([MARK_X, RYS[2], 0])
        frame2 = SurroundingRectangle(VGroup(*ch[2]), buff=0.06, color=GOLD_M, stroke_width=3, corner_radius=0.1)
        pd = left_at(T("predicate pushdown: skip by min and max", 20, GOLD_M), -6.5, -1.95)
        self.steps("Checking the filter against min and max like this is called predicate pushdown. "
                   "Only row group 2 might match.", [
            (lambda: [FadeIn(pd, shift=0.1 * UP)], 0.7),
            "Only row group 2",
            (lambda: [Create(frame2), Create(ok2), stats[2][0].animate.set_color(GREEN_M),
                      stats[2][1].animate.set_color(GREEN_M)], 0.9),
        ])

        self.steps("Inside it, the query needs three columns: merchant, day and amount. "
                   "It never touches payment id or status.", [
            (lambda: [*[heads[c].animate.set_color(GOLD_M) for c in NEED]], 0.7),
            "It never touches",
            (lambda: [*[ch[2][c].animate.set_opacity(0.18) for c in (0, 3)],
                      *[heads[c].animate.set_opacity(0.35) for c in (0, 3)]], 0.8),
        ])

        self.steps("So the reader fetches three chunks, as three byte ranges, and filters the rows in them.", [
            (lambda: [LaggedStart(*[ch[2][c].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M, 0.35), 1) for c in (1, 2, 4)],
                                  lag_ratio=0.3)], 1.2),
            (lambda: [Transform(bf, bar_fill(AFTER_KB / 1000)), Transform(bt, bar_text("483 KB"))], 0.9),
        ])

        ghost = DashedLine([BX0 + FILE_MB * PER_MB, BAR_Y - 0.3, 0], [BX0 + FILE_MB * PER_MB, BAR_Y + 0.3, 0],
                           dash_length=0.06, stroke_width=2, color=RED_M)
        cmp_t = T("483 KB instead of 4.0 MB: about an eighth", 20, GREEN_M).move_to([0, -3.25, 0])
        self.steps("That's about 480 kilobytes instead of 4 megabytes, an eighth of the file, for the same answer.", [
            (lambda: [Create(ghost), bf.animate.set_fill(GREEN_M, 0.85)], 0.7),
            (lambda: [FadeIn(cmp_t, shift=0.1 * UP)], 0.7),
        ])

        rnd = [[stat(r, 0, "11-06 to 11-07", RED_M), stat(r, 1, "0 to 499", RED_M)] for r in range(4)]
        self.steps("It works because the file is sorted. Written in random order, every row group would span both days "
                   "and every merchant. Nothing could be skipped, and the read grows to 2.4 megabytes.", [
            (lambda: [glow(foot, TEAL_M, 1.03)], 0.8),
            "Written in random",
            (lambda: [*[Transform(stats[r][k], rnd[r][k]) for r in range(4) for k in range(2)],
                      *[FadeOut(m) for m in marks.values()], FadeOut(ok2), FadeOut(frame2)], 1.0),
            "Nothing could",
            (lambda: [*[ch[r][c].animate.set_stroke(RED_M).set_fill(fillc(BLUE_M, 0.35), 1).set_opacity(1)
                        for r in range(4) for c in (1, 2, 4)],
                      *[l.animate.set_opacity(1) for l in rgl]], 0.9),
            (lambda: [Transform(bf, bar_fill(2.4, RED_M)), Transform(bt, bar_text("2.4 MB", RED_M)),
                      Transform(cmp_t, T("random order: 2.4 MB, every row group read", 20, RED_M).move_to(cmp_t))], 0.9),
        ])

        back = [[stat(r, k, STATS[r][k], GREEN_M if r == 2 else GREY_D) for k in range(2)] for r in range(4)]
        self.steps("The footer's min and max let a reader skip row groups, and storing by column lets it skip columns. "
                   "Sort the file by what you filter on.", [
            (lambda: [*[Transform(stats[r][k], back[r][k]) for r in range(4) for k in range(2)],
                      *[c.animate.set_stroke(GREY_B).set_opacity(0.18) for r in (0, 1, 3) for c in ch[r]],
                      *[l.animate.set_opacity(0.3) for i, l in enumerate(rgl) if i != 2],
                      *[ch[2][c].animate.set_stroke(BLUE_M).set_opacity(1) for c in (1, 2, 4)],
                      *[ch[2][c].animate.set_stroke(GREY_B).set_opacity(0.18) for c in (0, 3)]], 1.0),
            "and storing by column",
            (lambda: [*[glow(ch[2][c], BLUE_M, 1.08) for c in (1, 2, 4)]], 0.9),
            "Sort the file",
            (lambda: [glow(foot, TEAL_M, 1.03), Transform(bf, bar_fill(AFTER_KB / 1000, GREEN_M)),
                      Transform(bt, bar_text("483 KB")),
                      Transform(cmp_t, T("483 KB instead of 4.0 MB: about an eighth", 20, GREEN_M).move_to(cmp_t))], 0.9),
        ])
        self.wait(0.6)
