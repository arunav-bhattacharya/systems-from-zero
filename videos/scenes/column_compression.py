from sfz import *

# Currency codes are said as the money they stand for; captions keep the codes.
SAY.insert(0, (r"\bEUR\b", "euro"))
SAY.insert(0, (r"\bGBP\b", "pound"))
SAY.insert(0, (r"\bSEK\b", "krona"))
SAY.insert(0, (r"\bUSD\b", "dollar"))
SAY.insert(0, (r"\bgzip\b", "G zip"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
FIELDS = ["id", "shop", "currency", "status", "amount", "time"]
SHELF_Y, BW, BH = 3.22, 1.22, 0.56
SHELF_X = [-3.4 + 1.36 * i for i in range(6)]
TAG_Y = SHELF_Y - BH / 2 - 0.2
X0, PITCH, CW, CH = -6.35, 0.93, 0.85, 0.5         # the chunk: twelve cells per row
YA, YB = 1.75, 0.45                                # top row: plain; bottom row: encoded
SZ_X = 4.98                                        # each row's size, at its right end
CARD_C, CARD_W, CARD_H = np.array([4.95, -1.2, 0]), 3.2, 2.0   # the key on the cover, lower right
YL, YL2 = -0.85, -1.45                             # the lower band, left of the card
BAR_Y, CAP_Y = -2.75, -3.25

CUR = ["EUR", "EUR", "EUR", "GBP", "EUR", "USD", "EUR", "EUR", "SEK", "EUR", "GBP", "EUR"]
KEY = ["EUR", "GBP", "SEK", "USD"]
CODE = [KEY.index(c) for c in CUR]
BITS = [format(c, "02b") for c in CODE]
AMT = [1250, 300, 8900, 450, 2100, 760, 300, 5400, 990, 3300, 610, 1800]
BASE = min(AMT)
FIRST = {v: CUR.index(v) for v in KEY}             # where each distinct value first appears


def cx(i):
    return X0 + CW / 2 + PITCH * i


def n(v):
    return f"{v:,}"


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
            if callable(it):
                it()
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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.07, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))


def cell(x, y, txt, color, w=CW, size=17):
    r = RoundedRectangle(corner_radius=0.07, width=w, height=CH, stroke_color=color, stroke_width=2.2).set_fill(fillc(color), 1).move_to([x, y, 0])
    return VGroup(r, M(txt, size).move_to([x, y, 0]))


def retext(c, txt, size=17, color=WHITE):
    return Transform(c[1], M(txt, size, color).move_to(c[0]))


def recolor(c, color):
    return c[0].animate.set_stroke(color).set_fill(fillc(color), 1)


def bar(x0, y, length, color, h=0.3):
    return Rectangle(width=max(length, 0.04), height=h, stroke_width=0).set_fill(color, 0.85).move_to([x0 + max(length, 0.04) / 2, y, 0])


class ColumnCompression(Base):
    """store-11, section 1. The shoebox of receipts cut into strips, one binder per detail. The currency binder:
    four values, a million strips. Plain: 84 bytes for twelve, 7 MB for a million. Zip it? Unzip 256 KB to read one
    value. A key on the cover (dictionary: 0 EUR, 1 GBP, 2 SEK, 3 USD; code < 1 means before GBP). Paper doesn't shrink,
    bits do: 2 bits a code, 3 bytes, 31 with the key, 250 KB a million (bit-packing). Amounts minus 300: 8,600 in 14
    bits, 40 bytes against 96 (frame of reference). Sorted: four runs (run-length). Runs on unsorted amounts: 144 bytes,
    so try each and keep the smallest; DuckDB 5.5 MB against PostgreSQL's 66. Why squeeze: 28 times fewer bytes to
    move. The moral, and a check (status sorted by status: runs)."""

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

    def rowlab(self, key, s, y, color=GREY_B):
        return self.put(key, left_at(T(s, 19, color), X0, y + 0.52))

    def size(self, key, s, y, color=WHITE):
        return self.put(key, left_at(T(s, 22, color), SZ_X, y))

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b), run_time=secs, rate_func=linear)

    def row(self, y, texts, color, size=17):
        return VGroup(*[cell(cx(i), y, t, color, size=size) for i, t in enumerate(texts)])

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Four currencies, a million rows", "how one column squeezes small")

        # ---- the pieces ----
        shelf = [VGroup(RoundedRectangle(corner_radius=0.1, width=BW, height=BH, stroke_color=BLUE_M, stroke_width=2.5)
                        .set_fill(fillc(BLUE_M), 1).move_to([x, SHELF_Y, 0]), T(f, 18).move_to([x, SHELF_Y, 0]))
                 for f, x in zip(FIELDS, SHELF_X)]
        RC = np.array([0, 0.05, 0])
        rcard = RoundedRectangle(corner_radius=0.12, width=4.3, height=3.5, stroke_color=GREY_B, stroke_width=2.5).set_fill("#141414", 1).move_to(RC)
        stack = VGroup(*[rcard.copy().set_stroke(GREY_D).set_fill("#0c0c0c", 1).shift([0.14 * k, 0.14 * k, 0]) for k in (3, 2, 1)])
        rtitle = T("receipt", 20, GREY_B).move_to(RC + [0, 1.42, 0])
        RV = ["p1", "m42", "EUR", "settled", "1,250", "10:00:02"]
        RY = [0.95 - 0.47 * i for i in range(6)]
        rlines = [VGroup(left_at(T(f, 20, GREY_B), -1.85, y), right_at(M(v, 20), 1.85, y)) for f, v, y in zip(FIELDS, RV, RY)]
        strips = [RoundedRectangle(corner_radius=0.08, width=3.95, height=0.4, stroke_color=BLUE_M, stroke_width=2).move_to([0, y, 0])
                  for y in RY]
        box_lab = T("a shoebox: one receipt per payment", 20, GREY_B).move_to([0, -2.2, 0])

        # ---------------- scene 1: the binders ----------------
        self.steps("Picture a café owner with a shoebox of paper receipts, one for every card payment. "
                   "Each receipt has an id, the shop, the currency, a status, the amount and the time.", [
            (lambda: [FadeIn(stack, lag_ratio=0.2), FadeIn(rcard), FadeIn(rtitle), FadeIn(box_lab)], 0.9),
            "Each receipt",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.05 * RIGHT) for l in rlines], lag_ratio=0.25)], 1.6),
        ])
        pieces = [VGroup(s, l) for s, l in zip(strips, rlines)]
        self.steps("To add up the amounts, she used to read every receipt. So she cut each one into strips, one per detail, "
                   "and filed them in six binders, in the same order. Now the total needs one binder.", [
            "read every receipt",
            (lambda: [LaggedStart(*[glow(c, YELLOW_M, 1.02) for c in [*stack, rcard]], lag_ratio=0.2)], 1.0),
            "cut each one",
            (lambda: [LaggedStart(*[Create(s) for s in strips], lag_ratio=0.12)], 0.9),
            "filed them",
            (lambda: [FadeOut(VGroup(stack, rcard, rtitle, box_lab)),
                      LaggedStart(*[Succession(p.animate(run_time=0.55).scale(0.3).move_to([SHELF_X[i], SHELF_Y, 0]),
                                               FadeOut(p, run_time=0.1)) for i, p in enumerate(pieces)], lag_ratio=0.15),
                      LaggedStart(*[FadeIn(b, run_time=0.3) for b in shelf], lag_ratio=0.17)], 1.5),
            "the total needs",
            (lambda: [glow(shelf[4][0], YELLOW_M, 1.08)], 0.7),
        ])
        rowA = self.row(YA, CUR, BLUE_M)
        qm = T("?", 44, YELLOW_M).move_to([SZ_X + 0.4, YA, 0])
        self.steps("But open the currency binder, and look. EUR, EUR, EUR, GBP, EUR. A million strips, and only four "
                   "different values on them. So how small can a column like this get? Hold that question.", [
            (lambda: [glow(shelf[2][0], YELLOW_M, 1.08)], 0.6),
            "EUR, EUR",
            (lambda: [LaggedStart(*[AnimationGroup(dot_run([SHELF_X[2], SHELF_Y - BH / 2, 0], [cx(i), YA + CH / 2, 0], BLUE_M, 0.4),
                                                   FadeIn(c, run_time=0.4)) for i, c in enumerate(rowA)], lag_ratio=0.12),
                      *self.rowlab("lA", "currency: one chunk, 12 values in row order", YA)], 1.8),
            "only four",
            (lambda: [LaggedStart(*[glow(rowA[FIRST[v]][0], YELLOW_M, 1.15) for v in KEY], lag_ratio=0.25)], 1.0),
            "how small",
            (lambda: [FadeIn(qm, scale=0.6), *self.cap("how small can a column like this get?", WHITE)], 0.6),
        ], after=0.3)
        self.stamp("binders")

        # ---------------- scene 2: the plain way ----------------
        BX = [X0 + 0.21 + 0.46 * k for k in range(7)]
        bytes7 = VGroup(*[VGroup(Square(0.42, stroke_color=GREY_B if k < 4 else WHITE, stroke_width=2).set_fill(fillc(GREY_B if k < 4 else BLUE_M), 1)
                                 .move_to([BX[k], YL, 0]), M(["", "", "", "3", "E", "U", "R"][k], 18).move_to([BX[k], YL, 0])) for k in range(7)])
        lenlab = T("4-byte length", 17, GREY_B).move_to([(BX[0] + BX[3]) / 2, YL2, 0])
        txtlab = T("3 bytes of text", 17, WHITE).move_to([(BX[4] + BX[6]) / 2, YL2, 0])
        eq7 = left_at(T("= 7 bytes", 22), BX[6] + 0.45, YL)
        self.steps("Take twelve strips, one chunk of the column. Space is counted in bytes, and a byte holds about one letter. "
                   "Stored plainly, each value is a 4-byte length, then 3 bytes of text: 84 bytes for twelve.", [
            (lambda: [FadeOut(qm), *self.uncap()], 0.4),
            "Stored plainly",
            (lambda: [glow(rowA[0][0], YELLOW_M, 1.15), TransformFromCopy(rowA[0], bytes7)], 0.9),
            "a 4-byte length",
            (lambda: [FadeIn(lenlab)], 0.4),
            "3 bytes of text",
            (lambda: [FadeIn(txtlab), FadeIn(eq7)], 0.5),
            "84 bytes",
            (lambda: [*self.size("szA", "84 bytes", YA), *self.cap("12 values x 7 bytes = 84 bytes", WHITE)], 0.5),
        ])
        self.steps("A million take 7 MB, for four different values. Write E U R by hand a million times, and by strip four "
                   "hundred you'd invent a shorthand. That's the wish: a shorthand that's quick to read back.", [
            (lambda: self.cap("a million rows: 7 MB, for 4 different values", WHITE), 0.6),
            "Write E U R",
            (lambda: [LaggedStart(*[glow(rowA[i][0], RED_M, 1.1) for i in range(12) if CUR[i] == "EUR"], lag_ratio=0.1)], 1.2),
            "That's the wish",
            (lambda: [FadeOut(VGroup(bytes7, lenlab, txtlab, eq7)), *self.cap("wanted: a shorthand that's quick to read back", YELLOW_M)], 0.6),
        ], after=0.3)

        # ---------------- scene 3: zip it? ----------------
        bag = RoundedRectangle(corner_radius=0.2, width=12 * PITCH + 0.2, height=CH + 0.16, stroke_color=PURPLE_M, stroke_width=3) \
            .set_fill(interpolate_color(ManimColor("#000000"), ManimColor(PURPLE_M), 0.45), 1).move_to([(cx(0) + cx(11)) / 2, YA, 0]).set_z_index(4)
        bagt = T("zipped", 22, WHITE).move_to(bag).set_z_index(5)
        ptr = Arrow([cx(5), YL + 0.2, 0], [cx(5), YA - CH / 2 - 0.25, 0], buff=0, stroke_width=4, color=YELLOW_M,
                    max_tip_length_to_length_ratio=0.12)
        ptrl = T("read one value", 19, YELLOW_M).move_to([cx(5), YL - 0.15, 0])
        nozip = tick(False, 0.3).move_to([SZ_X + 0.75, YA, 0]).set_z_index(6)
        self.steps("The first idea most of us have: zip it, the way you zip files before you email them. It does shrink.", [
            (lambda: [*self.cap("the first idea: zip it", PURPLE_M)], 0.5),
            "zip it",
            (lambda: [FadeIn(bag, scale=1.05), FadeIn(bagt), *self.drop("szA")], 0.8),
            "It does shrink",
            (lambda: self.size("szA", "smaller", YA, PURPLE_M), 0.5),
        ])
        self.steps("But every scan then pays to unzip whatever it touches, and to read one value, you unzip the whole block "
                   "around it, about 256 KB.", [
            "to read one value",
            (lambda: [GrowArrow(ptr), FadeIn(ptrl)], 0.6),
            "the whole block",
            (lambda: [glow(bag, YELLOW_M, 1.02)], 0.8),
            "about 256 KB",
            (lambda: self.cap("to read one value: unzip the whole block, about 256 KB", WHITE), 0.6),
        ])
        self.steps("It's a vacuum-packed binder: small on the shelf, but you cut open the bag to read one strip.", [
            "you cut open",
            (lambda: [*self.drop("szA"), Create(nozip)], 0.5),
            (lambda: [FadeOut(VGroup(bag, bagt, ptr, ptrl, nozip)), *self.size("szA", "84 bytes", YA)], 0.7),
        ], after=0.3)
        self.stamp("zip")

        # ---------------- scene 4: a key on the cover ----------------
        card = RoundedRectangle(corner_radius=0.14, width=CARD_W, height=CARD_H, stroke_color=GOLD_M, stroke_width=3) \
            .set_fill(fillc(GOLD_M), 1).move_to(CARD_C)
        card_t = T("the key on the cover", 18, GOLD_M).move_to(CARD_C + [0, 0.66, 0])
        entries = [M(f"{k} = {v}", 20).move_to(CARD_C + [0.8 * (1 if k % 2 else -1), 0.05 - 0.55 * (k // 2), 0]) for k, v in enumerate(KEY)]
        rowB = self.row(YB, [str(c) for c in CODE], GOLD_M)
        self.steps("So back to the shorthand. On the binder's cover, the owner writes a key, in alphabetical order: "
                   "0 is EUR, 1 is GBP, 2 is SEK, and 3 is USD.", [
            (lambda: [*self.uncap(), FadeIn(card), FadeIn(card_t)], 0.7),
            "0 is EUR",
            *[x for k, v in enumerate(KEY) for x in (f"{k} is {v}", (lambda v=v, k=k: [TransformFromCopy(rowA[FIRST[v]], entries[k])], 0.5))],
        ])
        self.steps("Now each strip holds one small number instead of a word.", [
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.15 * DOWN) for c in rowB], lag_ratio=0.1),
                      *self.rowlab("lB", "codes: each value's place in the key", YB, GOLD_M)], 1.5),
        ])
        self.steps("Let's map it. The key on the cover is the dictionary. The number on a strip is a code: its value's place "
                   "in the key. This is called dictionary encoding.", [
            "The key on the cover",
            (lambda: [glow(card, GOLD_M, 1.03), *self.cap("the key on the cover = the dictionary", GOLD_M)], 0.7),
            "The number on a strip",
            (lambda: [LaggedStart(*[glow(c[0], GOLD_M, 1.12) for c in rowB], lag_ratio=0.05),
                      *self.cap("the number on a strip = a code", GOLD_M)], 1.0),
            "dictionary encoding",
            (lambda: self.cap("dictionary encoding: each value once, in a sorted key; a small code per row", WHITE), 0.6),
        ])
        self.steps("And since the key is sorted, a test like currency before GBP becomes code below 1, right on the codes.", [
            "currency before GBP",
            (lambda: [*self.cap(M("currency < 'GBP'   is   code < 1", 22, YELLOW_M))], 0.5),
            "code below 1",
            (lambda: [*[glow(rowA[i][0], YELLOW_M, 1.12) for i in range(12) if CODE[i] == 0],
                      *[glow(rowB[i][0], YELLOW_M, 1.12) for i in range(12) if CODE[i] == 0], glow(card, YELLOW_M, 1.02)], 0.9),
        ], after=0.3)
        self.stamp("dictionary")

        # ---------------- scene 5: paper doesn't shrink ----------------
        bitnote = left_at(T("a bit: a single 0 or 1.   8 bits = 1 byte", 21), X0, YL)
        twobits = left_at(M("0 to 3 fits in 2 bits:   00  01  10  11", 20, GOLD_M), X0, YL2)
        BXS = [X0 + 0.11 + 0.22 * k for k in range(24)]
        bitsq = [Square(0.22, stroke_color=GREEN_M, stroke_width=1.5).set_fill(fillc(GREEN_M, 0.25), 1).move_to([BXS[k], YL, 0]) for k in range(24)]
        bitd = [M(BITS[k // 2][k % 2], 14).move_to([BXS[k], YL, 0]) for k in range(24)]
        braces = VGroup(*[Brace(VGroup(*bitsq[8 * b:8 * b + 8]), DOWN, buff=0.08, color=GREY_B) for b in range(3)])
        blabs = VGroup(*[T(f"byte {b + 1}", 16, GREY_B).next_to(braces[b], DOWN, buff=0.08) for b in range(3)])
        packed = left_at(T("24 bits = 3 bytes", 22, GREEN_M), BXS[-1] + 0.4, YL)
        self.steps("Here the binders stop being a good picture. A paper strip with a 0 on it is just as thick as one that "
                   "says EUR. Paper doesn't shrink, but bits do.", [
            (lambda: self.cap("where the binders stop working: paper doesn't shrink, bits do", WHITE), 0.6),
            "just as thick",
            (lambda: [glow(rowB[0][0], RED_M, 1.15), glow(rowA[0][0], RED_M, 1.15)], 0.8),
        ])
        self.steps("A bit is a single 0 or 1, and 8 bits make a byte. Our codes only go up to 3, and 3 fits in 2 bits.", [
            (lambda: [FadeIn(bitnote)], 0.5),
            "Our codes",
            (lambda: [glow(rowB[5][0], GOLD_M, 1.15)], 0.6),
            "fits in 2 bits",
            (lambda: [FadeIn(twobits)], 0.5),
        ])
        self.steps("So how many bytes do the twelve codes take now? Pause and guess.", [
            (lambda: self.cap("how many bytes for the twelve codes?  pause and guess", YELLOW_M), 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("Two bits each, written back to back: 24 bits, which is 3 bytes.", [
            (lambda: [*self.uncap(), FadeOut(bitnote), FadeOut(twobits), *[retext(c, b) for c, b in zip(rowB, BITS)]], 0.6),
            "written back to back",
            (lambda: [LaggedStart(*[TransformFromCopy(rowB[i], VGroup(bitsq[2 * i], bitsq[2 * i + 1], bitd[2 * i], bitd[2 * i + 1]))
                                    for i in range(12)], lag_ratio=0.08)], 1.4),
            "which is 3 bytes",
            (lambda: [FadeIn(braces), FadeIn(blabs), FadeIn(packed)], 0.6),
        ])
        self.steps("With the key, the chunk takes 31 bytes instead of 84. A million currencies take 250 KB instead of 7 MB. "
                   "Storing each number in the fewest bits that hold the largest one is called bit-packing.", [
            "With the key",
            (lambda: [glow(card, GOLD_M, 1.03), *self.size("szB", "31 bytes", YB, GREEN_M),
                      *self.cap("key 28 bytes + codes 3 bytes = 31 bytes, against 84", GREEN_M)], 0.7),
            "A million currencies",
            (lambda: self.cap("a million currencies: 250 KB instead of 7 MB", WHITE), 0.6),
            "is called bit-packing",
            (lambda: self.cap("bit-packing: each number in the fewest bits that hold the largest", GREEN_M), 0.6),
        ], after=0.4)
        self.stamp("bitpacked")
        bitsbar = VGroup(*bitsq, *bitd, braces, blabs, packed)

        # ---------------- scene 6: numbers too ----------------
        hdr_t = T("the chunk's header", 18, GOLD_M).move_to(CARD_C + [0, 0.66, 0])
        base_e = M(f"base = {BASE}", 24).move_to(CARD_C + [0, -0.2, 0])
        SEGW = 0.44
        SX = [X0 + SEGW / 2 + SEGW * k for k in range(12)]
        segs = [VGroup(Rectangle(width=SEGW, height=0.32, stroke_color=GREEN_M, stroke_width=1.5).set_fill(fillc(GREEN_M, 0.25), 1)
                       .move_to([SX[k], YL, 0]), M("14", 14).move_to([SX[k], YL, 0])) for k in range(12)]
        seg_t = left_at(T("12 x 14 bits = 168 bits", 22, GREEN_M), SX[-1] + SEGW / 2 + 0.3, YL)
        words = left_at(T("in 3 words of 8 bytes, plus a 16-byte header: 40 bytes", 20, GREEN_M), X0, YL2)
        self.steps("Numbers get the same trick. Twelve amounts, in cents, each in an 8-byte slot built for numbers with "
                   "nineteen digits: 96 bytes.", [
            (lambda: [*self.uncap(), FadeOut(bitsbar), *self.drop("szB", "lB"), FadeOut(rowB), glow(shelf[4][0], YELLOW_M, 1.08),
                      FadeOut(VGroup(card, card_t, *entries))], 0.7),
            "Twelve amounts",
            (lambda: [*[retext(c, n(a)) for c, a in zip(rowA, AMT)], *self.rowlab("lA", "amount, in cents: 12 values, 8 bytes each", YA),
                      *self.size("szA", "96 bytes", YA)], 0.8),
            "an 8-byte slot",
            (lambda: self.cap("each 8-byte slot is built for numbers with 19 digits", WHITE), 0.6),
        ])
        rowB2 = self.row(YB, [n(a - BASE) for a in AMT], GOLD_M)
        big = AMT.index(max(AMT))
        self.steps("First, subtract the chunk's smallest amount, 300, from every value. Now the largest left is 8,600, "
                   "and that fits in 14 bits.", [
            "the chunk's smallest",
            (lambda: [*[glow(rowA[i][0], YELLOW_M, 1.15) for i in range(12) if AMT[i] == BASE], FadeIn(card), FadeIn(hdr_t), FadeIn(base_e)], 0.7),
            "from every value",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.15 * DOWN) for c in rowB2], lag_ratio=0.08),
                      *self.rowlab("lB", "minus the smallest, 300", YB, GOLD_M)], 1.3),
            "the largest left",
            (lambda: [glow(rowB2[big][0], YELLOW_M, 1.2)], 0.6),
            "fits in 14 bits",
            (lambda: self.cap("8,600 fits in 14 bits (14 bits hold up to 16,383)", WHITE), 0.6),
        ])
        self.steps("Twelve values take 168 bits. In three 8-byte words, plus a small header that remembers the 300, "
                   "that's 40 bytes instead of 96. Taking off a base like this is called a frame of reference.", [
            (lambda: [LaggedStart(*[TransformFromCopy(rowB2[i], segs[i]) for i in range(12)], lag_ratio=0.07)], 1.2),
            (lambda: [FadeIn(seg_t)], 0.4),
            "In three 8-byte words",
            (lambda: [FadeIn(words), glow(card, GOLD_M, 1.03)], 0.6),
            "40 bytes",
            (lambda: self.size("szB", "40 bytes", YB, GREEN_M), 0.5),
            "a frame of reference",
            (lambda: self.cap("frame of reference: subtract the chunk's smallest value first", GREEN_M), 0.6),
        ], after=0.3)
        self.stamp("frame")

        # ---------------- scene 7: runs ----------------
        rowA3 = self.row(YA, CUR, BLUE_M)
        rowB3 = self.row(YB, [str(c) for c in CODE], GOLD_M)
        order = sorted(range(12), key=lambda i: CODE[i])          # stable: row order inside each currency
        pos = {i: p for p, i in enumerate(order)}
        runs = [(k, [p for p in range(12) if CODE[order[p]] == k]) for k in range(4)]
        runcells = [cell((cx(ps[0]) + cx(ps[-1])) / 2, YB, f"{k} x {len(ps)}", GOLD_M, w=cx(ps[-1]) - cx(ps[0]) + CW, size=16) for k, ps in runs]
        self.steps("One more shorthand. If the table were sorted by currency, equal codes would sit together: eight zeros, "
                   "two ones, one two and one three.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*segs, seg_t, words, rowB2, hdr_t, base_e, rowA)), *self.drop("szB", "szA", "lA", "lB")], 0.5),
            (lambda: [FadeIn(rowA3), FadeIn(rowB3), FadeIn(card_t), *[FadeIn(e) for e in entries],
                      *self.rowlab("lA", "currency: 12 values in row order", YA), *self.rowlab("lB", "codes", YB, GOLD_M),
                      *self.size("szA", "84 bytes", YA)], 0.5),
            "If the table were sorted",
            (lambda: [*[rowA3[i].animate.move_to([cx(pos[i]), YA, 0]) for i in range(12)],
                      *[rowB3[i].animate.move_to([cx(pos[i]), YB, 0]) for i in range(12)],
                      *self.rowlab("lA", "currency: the same 12, sorted", YA)], 1.4),
            "eight zeros",
            (lambda: [*[glow(rowB3[order[p]][0], YELLOW_M, 1.12) for p in runs[0][1]]], 0.6),
        ])
        self.steps("Write each run once, with its length. Four runs. That's run-length encoding. It shines on sorted columns.", [
            (lambda: [LaggedStart(*[Transform(VGroup(*[rowB3[order[p]] for p in ps]), runcells[k].copy()) for k, ps in runs],
                                  lag_ratio=0.3), *self.rowlab("lB", "runs: (code, how many in a row)", YB, GOLD_M)], 1.4),
            lambda: (self.remove(rowB3), self.add(*runcells)),
            "Four runs",
            (lambda: self.size("szB", "4 runs", YB, GREEN_M), 0.5),
            "run-length encoding",
            (lambda: self.cap("run-length encoding: each run once, with its length", GREEN_M), 0.6),
        ])
        self.stamp("runs")

        # ---------------- scene 8: none wins everywhere ----------------
        rowA4 = self.row(YA, [n(a) for a in AMT], BLUE_M)
        rowB4 = self.row(YB, [n(a) for a in AMT], RED_M)
        self.steps("So should every column use runs? Try it on our twelve amounts, which aren't sorted. Smaller than plain, "
                   "or bigger? Pause and guess.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(rowA3, *runcells, card_t, *entries)), *self.drop("szB", "szA", "lA", "lB")], 0.5),
            (lambda: [FadeIn(rowA4), FadeIn(hdr_t), FadeIn(base_e),
                      *self.rowlab("lA", "plain: 12 amounts in cents, in row order", YA), *self.size("szA", "96 bytes", YA)], 0.5),
            "Try it",
            (lambda: [FadeIn(rowB4), *self.rowlab("lB", "run-length: 12 runs, each of length 1", YB, RED_M)], 0.6),
            "Pause and guess",
            (lambda: self.cap("smaller than plain, or bigger?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        chips = VGroup(chip("run-length: 144 bytes", RED_M, 22), chip("plain: 96 bytes", WHITE, 22),
                       chip("bit-packed: 40 bytes", GREEN_M, 22)).arrange(RIGHT, buff=0.45).move_to([0, YL, 0])
        self.steps("Bigger. Twelve runs of length one, at 12 bytes each: 144 bytes, against 96 plain. Not much of a run.", [
            (lambda: [*self.uncap(), *self.size("szB", "144 bytes", YB, RED_M), FadeOut(VGroup(card, hdr_t, base_e))], 0.5),
            "144 bytes",
            (lambda: [FadeIn(chips[0], shift=0.1 * UP), *self.cap("12 runs x (8-byte value + 4-byte length) = 144 bytes", WHITE)], 0.4),
            "against 96",
            (lambda: [FadeIn(chips[1], shift=0.1 * UP)], 0.4),
            "Not much",
            (lambda: [LaggedStart(*[glow(c[0], RED_M, 1.1) for c in rowB4], lag_ratio=0.05)], 0.9),
        ])
        self.steps("So no encoding wins everywhere. For each chunk, the engine tries them all and keeps the smallest: here, "
                   "bit-packing, at 40 bytes.", [
            (lambda: self.cap("no encoding wins everywhere", WHITE), 0.5),
            "the engine tries",
            (lambda: [FadeIn(chips[2], shift=0.1 * UP)], 0.4),
            "keeps the smallest",
            (lambda: [chips[0].animate.fade(0.65), chips[1].animate.fade(0.65), glow(chips[2][0], GREEN_M, 1.06),
                      *self.cap("for each chunk: try every encoding, keep the smallest", GREEN_M)], 0.7),
        ])
        tags = [T("bit-packed" if f in ("id", "shop", "amount", "time") else "dictionary", 15,
                  GREEN_M if f in ("id", "shop", "amount", "time") else GOLD_M).move_to([x, TAG_Y, 0]) for f, x in zip(FIELDS, SHELF_X)]
        PGL, PGX = -2.1, -1.9
        pgb, ddb = bar(PGX, YL, 7.0, RED_M), bar(PGX, YL2, 7.0 * 5.5 / 66, GREEN_M)
        pgl, ddl = right_at(T("PostgreSQL, whole rows", 20), PGL, YL), right_at(T("DuckDB, by column", 20), PGL, YL2)
        pgv = left_at(T("66 MB", 20, RED_M), PGX + 7.15, YL)
        ddv = left_at(T("5.5 MB", 20, GREEN_M), PGX + 7.0 * 5.5 / 66 + 0.15, YL2)
        self.steps("DuckDB, a free database built for reports, does this chunk by chunk. On the lesson's million payments, it "
                   "bit-packed the numbers and gave the text a dictionary: 5.5 MB in all.", [
            (lambda: [*self.uncap(), FadeOut(chips)], 0.4),
            "bit-packed the numbers",
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.05 * DOWN) for t in tags], lag_ratio=0.12)], 1.0),
            "5.5 MB",
            (lambda: [FadeIn(ddl), GrowFromEdge(ddb, LEFT), FadeIn(ddv)], 0.6),
        ])
        self.steps("PostgreSQL, a free database that keeps whole rows together, needs 66.", [
            (lambda: [FadeIn(pgl), GrowFromEdge(pgb, LEFT), FadeIn(pgv)], 0.9),
        ], after=0.3)
        self.stamp("choose")

        # ---------------- scene 9: why squeeze at all? ----------------
        pl, cl = right_at(T("currency, plain", 20), PGL, YL), right_at(T("currency, codes", 20), PGL, YL2)
        plb, clb = bar(PGX, YL, 7.0, RED_M), bar(PGX, YL2, 7.0 * 0.25 / 7, GREEN_M)
        plv = left_at(T("7 MB", 20, RED_M), PGX + 7.15, YL)
        clv = left_at(T("250 KB", 20, GREEN_M), PGX + 0.4, YL2)
        self.steps("Disks are cheap, so why squeeze at all? Because a scan spends most of its time moving bytes, from the disk "
                   "to memory and on to the processor.", [
            (lambda: [*self.cap("disks are cheap: why squeeze at all?", WHITE), FadeOut(VGroup(rowA4, rowB4)),
                      *self.drop("szA", "szB", "lA", "lB")], 0.5),
            "moving bytes",
            (lambda: [ReplacementTransform(pgl, pl), ReplacementTransform(ddl, cl), ReplacementTransform(pgb, plb),
                      ReplacementTransform(ddb, clb), ReplacementTransform(pgv, plv), ReplacementTransform(ddv, clv),
                      *self.cap("a scan's time goes on moving bytes: disk to memory to processor", WHITE)], 0.8),
            "to memory",
            (lambda: [dot_run([PGX, YL, 0], [PGX + 7.0, YL, 0], YELLOW_M, 2.0),
                      Succession(Wait(0.1), dot_run([PGX, YL2, 0], [PGX + 0.25, YL2, 0], YELLOW_M, 0.2))], 2.1),
        ])
        self.steps("250 KB is about 28 times less to move than 7 MB, and undoing a 2-bit code takes a few simple steps.", [
            (lambda: [glow(clb, GREEN_M, 1.2), *self.cap("250 KB instead of 7 MB: about 28 times fewer bytes to move", GREEN_M)], 0.7),
            "undoing a 2-bit code",
            (lambda: self.cap("undoing a 2-bit code: a few simple steps", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, how small can a column get? As small as its values are alike.", [
            (lambda: [FadeOut(VGroup(pl, cl, plb, clb, plv, clv)), *self.cap("how small can a column get?", WHITE)], 0.6),
            "As small as",
            (lambda: self.cap("as small as its values are alike", YELLOW_M, 26), 0.6),
        ])
        m1 = chip("each value once, in a key", GOLD_M, 20)
        m2 = chip("each number in the fewest bits", GREEN_M, 20)
        m3 = chip("a run once, with its length", GOLD_M, 20)
        moral = VGroup(m1, m2, m3).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        left_at(moral, X0, 0.35)
        self.steps("Write each different value once, in a key. Store each number in the fewest bits. Write a run once, with "
                   "its length. Then try them all and keep the smallest.", [
            (lambda: [FadeIn(m1, shift=0.1 * UP), FadeIn(card), FadeIn(card_t), *[FadeIn(e) for e in entries]], 0.5),
            (lambda: [glow(card, GOLD_M, 1.03)], 0.6),
            "Store each number",
            (lambda: [FadeIn(m2, shift=0.1 * UP)], 0.5),
            "Write a run",
            (lambda: [FadeIn(m3, shift=0.1 * UP)], 0.5),
            "Then try them all",
            (lambda: self.cap("then try them all, and keep the smallest", YELLOW_M, 26), 0.6),
        ], after=0.3)
        run1 = cell((cx(0) + cx(11)) / 2, YB, "0 x 12", GOLD_M, w=cx(11) - cx(0) + CW, size=20)
        rowS = self.row(YA, ["0"] * 12, GOLD_M)
        self.steps("One quick check. Ten million payments, sorted by status, which has three values. Which shorthand stores "
                   "the status column smallest? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(moral), FadeOut(VGroup(card, card_t, *entries)), glow(shelf[3][0], YELLOW_M, 1.08),
                      *self.rowlab("lA", "status codes: one chunk of 10 million payments sorted by status (3 values)", YA, WHITE)], 0.8),
            "Which shorthand",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * DOWN) for c in rowS], lag_ratio=0.06)], 0.8),
            "Pause and think",
            (lambda: self.cap("which shorthand stores it smallest?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Runs. Sorted by status, almost every chunk holds one status: a single run, one value and one count. "
                   "Bit-packed codes would still cost 2 bits a row, 2.5 MB.", [
            (lambda: [*self.uncap(), FadeIn(run1, shift=0.1 * DOWN), *self.rowlab("lB", "run-length: one run per chunk", YB, GREEN_M)], 0.6),
            "a single run",
            (lambda: [glow(run1[0], GREEN_M, 1.03), *self.size("szB", "1 run", YB, GREEN_M),
                      *self.cap("a run: one value + one count, however long the chunk", GREEN_M)], 0.7),
            "Bit-packed codes",
            (lambda: self.cap("bit-packed codes: 2 bits a row = 2.5 MB for 10 million rows", WHITE), 0.6),
        ])
        self.steps("Each chunk also notes its smallest and largest value, so a scan can skip it unread. That's next.", [
            (lambda: self.cap("next: each chunk's smallest and largest value lets a scan skip it", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("values that look alike squeeze small: try each shorthand, keep the smallest", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
