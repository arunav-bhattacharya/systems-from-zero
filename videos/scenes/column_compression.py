from sfz import *

FIELDS = ["id", "merchant", "currency", "amount", "created"]
FW = [0.62, 0.8, 0.8, 0.95, 0.85]
ROWS = [["p1", "m42", "EUR", "1,250", "10:00"], ["p2", "m7", "EUR", "300", "10:00"],
        ["p3", "m42", "GBP", "8,900", "10:01"], ["p4", "m19", "EUR", "450", "10:01"]]
X0, GAP, CH = -5.0, 0.07, 0.42
YR = [2.95, 2.45, 1.75, 1.25]                 # row store: two pages of two rows
YC = [3.1, 2.55, 2.0, 1.45, 0.9]             # column store: one strip per field
MX, MSC = 0.6, 4.8 / 66                      # meter: left edge, units per MB
CUR = ["EUR", "EUR", "EUR", "GBP", "EUR", "USD", "EUR", "EUR", "SEK", "EUR", "GBP", "EUR"]
CODE = {"EUR": 0, "GBP": 1, "SEK": 2, "USD": 3}
KX, KS, KW = -6.3, 0.76, 0.7                 # chunk cells: first x, step, width
YK, YCODE, YDICT, YRLE = -0.85, -1.55, -2.25, -2.95
SX = 3.3                                     # size labels in the lower band
ZX, ZS, ZW, ZY = -6.3, 1.78, 1.65, -1.3      # zone map chunks
ZONES = [("Oct 1", "5"), ("Oct 6", "10"), ("Oct 11", "15"), ("Oct 16", "20"), ("Oct 21", "25"), ("Oct 26", "31")]


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


def cell_x(j):
    return X0 + sum(FW[:j]) + GAP * j + FW[j] / 2


def col_x(j, i):
    return X0 + i * (FW[j] + GAP) + FW[j] / 2


def kx(i):
    return KX + i * KS + KW / 2


def meter(label, mb, y, color, val):
    lab = left_at(T(label, 18, GREY_B), MX, y + 0.33)
    bar = Rectangle(width=max(0.05, mb * MSC), height=0.32, stroke_width=0).set_fill(color, 0.9)
    bar.move_to([MX + bar.width / 2, y, 0])
    v = left_at(T(val, 20, color), MX + bar.width + 0.15, y)
    return lab, bar, v


def zone(k, lo, hi, color=WHITE):
    x = ZX + k * ZS + ZW / 2
    r = RoundedRectangle(corner_radius=0.1, width=ZW, height=0.85, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK, 1).move_to([x, ZY, 0])
    return VGroup(r, T(f"chunk {k + 1}", 16, GREY_B).move_to([x, ZY + 0.2, 0]),
                  T(f"{lo} to {hi}", 18, color).move_to([x, ZY - 0.17, 0]))


def verdict(k, s, color):
    return T(s, 18, color).move_to([ZX + k * ZS + ZW / 2, ZY - 0.72, 0])


class ColumnCompression(Base):
    """store-11, sections 0 to 2: sum(amount) on a million payments reads 8,404 pages (66 MB) in a row store and one
    8 MB array in a column store. A 12-value currency chunk: 84 bytes plain; dictionary (28 bytes) plus 2-bit codes
    (3 bytes) = 31; sorted, 4 runs. DuckDB keeps the whole table in 5.5 MB. Zone maps: six created_at chunks, a query
    for Oct 15 decodes 1; shuffled, every chunk spans Oct 1 to 31 and nothing is skipped."""

    def construct(self):
        self.title_card("Column stores and compression", "read one field, small, and only where it can match")

        cells = [[mbox(ROWS[i][j], GREY_B, w=FW[j], h=CH, size=15).move_to([cell_x(j), YR[i], 0]) for j in range(5)]
                 for i in range(4)]
        rowg = [VGroup(*cells[i]) for i in range(4)]
        pages = [SurroundingRectangle(VGroup(rowg[0], rowg[1]), color=WHITE, buff=0.12, corner_radius=0.1, stroke_width=2),
                 SurroundingRectangle(VGroup(rowg[2], rowg[3]), color=WHITE, buff=0.12, corner_radius=0.1, stroke_width=2)]
        plab = [right_at(T(f"page {k + 1}", 17, GREY_B), pages[k].get_left()[0] - 0.15, pages[k].get_center()[1]) for k in range(2)]
        self.steps("A finance query sums the amounts of a million payments. "
                   "In a row store, each page holds whole rows, one after another.", [
            "In a row store",
            (lambda: [Create(pages[0]), Create(pages[1]), FadeIn(plab[0]), FadeIn(plab[1])], 0.7),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.15 * RIGHT) for r in rowg], lag_ratio=0.3)], 1.4),
        ])

        l1, b1, v1 = meter("row store: sum(amount) reads every page", 66, 2.7, RED_M, "66 MB")
        self.steps("The amounts are spread through every page, so the scan reads all of them: "
                   "8,404 pages, 66 megabytes, for one field.", [
            (lambda: [*[cells[i][3][0].animate.set_stroke(GOLD_M, width=4) for i in range(4)],
                      *[cells[i][3][1].animate.set_color(GOLD_M) for i in range(4)]], 0.8),
            "so the scan reads",
            (lambda: [glow(pages[0], RED_M, 1.02)], 0.6),
            (lambda: [glow(pages[1], RED_M, 1.02)], 0.6),
            "8,404 pages",
            (lambda: [FadeIn(l1), GrowFromEdge(b1, LEFT), FadeIn(v1)], 1.0),
        ])

        flab = [right_at(T(FIELDS[j], 18, GREY_B), X0 - 0.15, YC[j]) for j in range(5)]
        self.steps("A column store turns the table on its side. Each field gets its own array, in row order, "
                   "so row three is position three in every array.", [
            (lambda: [FadeOut(pages[0]), FadeOut(pages[1]), FadeOut(plab[0]), FadeOut(plab[1])], 0.5),
            (lambda: [LaggedStart(*[cells[i][j].animate.move_to([col_x(j, i), YC[j], 0]) for j in range(5) for i in range(4)],
                                  lag_ratio=0.04)], 2.2),
            "Each field",
            (lambda: [*[FadeIn(f, shift=0.1 * RIGHT) for f in flab]], 0.6),
            "so row three",
            (lambda: [*[glow(cells[2][j][0], YELLOW_M, 1.08) for j in range(5)]], 1.0),
        ])

        l2, b2, v2 = meter("column store: one array", 8, 1.85, GREEN_M, "8 MB")
        amt = SurroundingRectangle(VGroup(*[cells[i][3] for i in range(4)]), color=GOLD_M, buff=0.08, corner_radius=0.08,
                                   stroke_width=3)
        self.steps("Now the sum reads one array: a million amounts, 8 megabytes.", [
            (lambda: [Create(amt), *[cells[i][j].animate.set_opacity(0.45) for i in range(4) for j in (0, 1, 2, 4)]], 0.8),
            "a million",
            (lambda: [FadeIn(l2), GrowFromEdge(b2, LEFT), FadeIn(v2)], 0.9),
        ])

        # ---- compression: one chunk of the currency column --------------------------------------------------------
        cur_box = SurroundingRectangle(VGroup(*[cells[i][2] for i in range(4)]), color=BLUE_M, buff=0.08, corner_radius=0.08,
                                       stroke_width=3)
        ktitle = left_at(T("currency: one chunk of 12 values", 18, GREY_B), KX, -0.3)
        kc = [mbox(c, BLUE_M, w=KW, h=0.44, size=15).move_to([kx(i), YK, 0]) for i, c in enumerate(CUR)]
        s1 = left_at(T("plain: 84 bytes", 20, WHITE), SX, YK)
        self.steps("And neighbours in a column look alike. Here are twelve currencies: four different strings, "
                   "stored in full, 84 bytes.", [
            (lambda: [FadeOut(amt), *[cells[i][j].animate.set_opacity(1) for i in range(4) for j in (0, 1, 4)],
                      *[cells[i][3].animate.set_opacity(0.45) for i in range(4)], Create(cur_box)], 0.8),
            "Here are twelve",
            (lambda: [FadeIn(ktitle), LaggedStart(*[FadeIn(c, shift=0.2 * DOWN) for c in kc], lag_ratio=0.06)], 1.3),
            "stored in full",
            (lambda: [FadeIn(s1, shift=0.1 * LEFT)], 0.6),
        ])

        dlab = left_at(T("dictionary:", 18, GREY_B), KX, YDICT)
        dct = VGroup(*[chip(f"{v} = {k}", TEAL_M, 17, mono=True) for k, v in CODE.items()]).arrange(RIGHT, buff=0.2)
        left_at(dct, dlab.get_right()[0] + 0.25, YDICT)
        codes = [mbox(str(CODE[c]), TEAL_M, w=KW, h=0.44, size=17).move_to([kx(i), YCODE, 0]) for i, c in enumerate(CUR)]
        self.steps("Dictionary encoding stores each string once, and replaces every value by its number in the list.", [
            (lambda: [FadeIn(dlab), LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in dct], lag_ratio=0.2)], 1.2),
            "and replaces",
            (lambda: [LaggedStart(*[TransformFromCopy(kc[i], codes[i]) for i in range(12)], lag_ratio=0.06)], 1.6),
        ])

        bits = [M(f"{CODE[c]:02b}", 17, TEAL_M).move_to([kx(i), YCODE, 0]) for i, c in enumerate(CUR)]
        s2 = left_at(T("codes, 2 bits each: 3 bytes", 20, TEAL_M), SX, YCODE)
        s3 = left_at(T("dictionary: 28 bytes", 20, TEAL_M), SX, YDICT)
        tot = left_at(T("together 31 bytes, was 84", 20, GREEN_M), SX, YRLE)
        self.steps("The numbers only go up to three, so two bits hold each one. "
                   "The whole chunk shrinks from 84 bytes to 31.", [
            "so two bits",
            (lambda: [*[Transform(codes[i][1], bits[i]) for i in range(12)]], 0.9),
            (lambda: [FadeIn(s2, shift=0.1 * LEFT)], 0.6),
            "The whole chunk",
            (lambda: [FadeIn(s3, shift=0.1 * LEFT)], 0.5),
            (lambda: [FadeIn(tot, shift=0.1 * LEFT), s1.animate.set_color(GREY_B)], 0.7),
        ])

        rlab = left_at(T("sorted:", 18, GREY_B), KX, YRLE)
        runs = VGroup(*[chip(f"{k} x {n}", PURPLE_M, 17, mono=True) for k, n in (("EUR", 8), ("GBP", 2), ("SEK", 1), ("USD", 1))])
        runs.arrange(RIGHT, buff=0.2)
        left_at(runs, rlab.get_right()[0] + 0.25, YRLE)
        rn = left_at(T("4 runs", 20, PURPLE_M), runs.get_right()[0] + 0.3, YRLE)
        self.steps("When equal values sit together, run-length encoding does even better. "
                   "Sorted by currency, the twelve values are four runs.", [
            (lambda: [*[glow(kc[i][0], PURPLE_M, 1.1) for i in (0, 1, 2)]], 0.9),
            "Sorted by currency",
            (lambda: [FadeIn(rlab), LaggedStart(*[FadeIn(r, shift=0.1 * UP) for r in runs], lag_ratio=0.25)], 1.2),
            (lambda: [FadeIn(rn)], 0.5),
        ])

        l3, b3, v3 = meter("DuckDB, the whole table, compressed", 5.5, 1.0, TEAL_M, "5.5 MB")
        self.steps("No encoding wins everywhere, so the engine tries several on each chunk and keeps the smallest. "
                   "DuckDB stores the whole table in 5.5 megabytes.", [
            (lambda: [glow(s2, YELLOW_M, 1.05)], 0.8),
            "and keeps the smallest",
            (lambda: [tot.animate(rate_func=there_and_back).scale(1.12)], 0.8),
            "DuckDB stores",
            (lambda: [FadeIn(l3), GrowFromEdge(b3, LEFT), FadeIn(v3)], 1.0),
        ])

        # ---- zone maps on created_at ------------------------------------------------------------------------------
        cre_box = SurroundingRectangle(VGroup(*[cells[i][4] for i in range(4)]), color=GOLD_M, buff=0.08, corner_radius=0.08,
                                       stroke_width=3)
        ztitle = left_at(T("created_at: six chunks, each with its min and max", 18, GREY_B), ZX, -0.3)
        zs = [zone(k, *ZONES[k]) for k in range(6)]
        comp = VGroup(ktitle, *kc, *codes, s1, s2, s3, tot, dlab, dct, rlab, runs, rn)
        self.steps("Skipping is cheaper still. When the engine writes a chunk, it notes the smallest and largest value. "
                   "That pair is a zone map.", [
            (lambda: [FadeOut(comp), FadeOut(cur_box), *[cells[i][2].animate.set_opacity(0.45) for i in range(4)],
                      *[cells[i][4].animate.set_opacity(1) for i in range(4)], Create(cre_box)], 0.9),
            "When the engine",
            (lambda: [FadeIn(ztitle), LaggedStart(*[FadeIn(z, shift=0.15 * DOWN) for z in zs], lag_ratio=0.15)], 1.4),
            "That pair",
            (lambda: [*[z[2].animate(rate_func=there_and_back).set_color(GOLD_M) for z in zs]], 1.0),
        ])

        q = chip("WHERE day = Oct 15", GOLD_M, 18).move_to([4.95, -0.3, 0])
        vs = [verdict(k, "decode" if k == 2 else "skip", GOLD_M if k == 2 else GREY_B) for k in range(6)]
        res = left_at(T("decoded: 1 chunk of 6", 20, GREEN_M), ZX, -2.75)
        demo = left_at(T("in the DuckDB demo: 2 row groups of 9", 18, GREY_B), ZX, -3.2)
        self.steps("A query wants October fifteenth. Five chunks can't hold that day, so the scan skips them unread, "
                   "and decodes one.", [
            (lambda: [FadeIn(q, shift=0.1 * LEFT)], 0.6),
            "Five chunks",
            (lambda: [*[zs[k].animate.set_opacity(0.3) for k in (0, 1, 3, 4, 5)], *[FadeIn(vs[k]) for k in (0, 1, 3, 4, 5)]], 1.0),
            "and decodes one",
            (lambda: [zs[2][0].animate.set_stroke(GOLD_M, width=4), FadeIn(vs[2]), FadeIn(res), FadeIn(demo)], 0.8),
        ])

        zs2 = [zone(k, "Oct 1", "31", RED_M) for k in range(6)]
        vs2 = [verdict(k, "decode", RED_M) for k in range(6)]
        res2 = left_at(T("decoded: 6 chunks of 6", 20, RED_M), ZX, -2.75)
        self.steps("That only works because payments arrive in time order. "
                   "Shuffle the rows, and every chunk spans the whole month: nothing is skipped.", [
            (lambda: [glow(cre_box, GOLD_M, 1.03)], 0.9),
            "Shuffle the rows",
            (lambda: [*[Transform(zs[k], zs2[k]) for k in range(6)]], 1.2),
            "nothing is skipped",
            (lambda: [*[Transform(vs[k], vs2[k]) for k in range(6)], Transform(res, res2), FadeOut(demo)], 0.9),
        ])

        self.steps("A column store reads one field, compressed, and only from the chunks that can match.", [
            (lambda: [*[Transform(zs[k], zone(k, *ZONES[k])) for k in range(6)],
                      *[Transform(vs[k], verdict(k, "decode" if k == 2 else "skip", GOLD_M if k == 2 else GREY_B)) for k in range(6)],
                      Transform(res, left_at(T("decoded: 1 chunk of 6", 20, GREEN_M), ZX, -2.75))], 1.0),
            "compressed",
            (lambda: [glow(b3, TEAL_M, 1.1)], 0.8),
            "only from",
            (lambda: [*[zs[k].animate.set_opacity(0.3) for k in (0, 1, 3, 4, 5)], zs[2][0].animate.set_stroke(GOLD_M, width=4)], 0.8),
        ])
        self.wait(0.6)
