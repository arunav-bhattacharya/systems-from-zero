from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz"; spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bX100's\b", "X one hundred's"))
SAY.insert(0, (r"\bX100\b", "X one hundred"))
SAY.insert(0, (r"\bMySQL\b", "my sequel"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TX, CX = -4.6, -2.0                 # the plan, and the column where a row or a crate rides beside it
YS, YF, YN = 2.0, 0.35, -1.3        # sum, filter, scan
BW, BH = 3.4, 0.95
QY = 3.4
SY = -2.35                          # example amounts under the scan
PX = -0.7                           # right panel, left edge
CY_L, CY_V = 3.0, 2.45              # counter label and value
BX, SC = 2.3, 4.0 / 13.93           # bar start, units per nanosecond a row
BY = [1.45, 0.45, -0.55]            # bars: one row at a time, batches, plain loop
AXY = -2.1                          # batch-size axis
CAP_Y, BAR_Y = -3.35, -2.95
AMT = ["4,200", "9,700", "1,100", "9,900", "9,300"]


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def bar(ns, y, color):
    w = max(0.06, ns * SC)
    return Rectangle(width=w, height=0.4, stroke_width=0).set_fill(color, 0.9).move_to([BX + w / 2, y, 0])


def bar_label(name, sub, y, color=WHITE):
    return VGroup(left_at(T(name, 21, color), PX, y + 0.16), left_at(T(sub, 17, GREY_B), PX, y - 0.19))


def ax_x(n):
    return -0.1 + 1.45 * np.log10(n)


def opbox(name, sub, color):
    r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    return VGroup(r, T(name, 21).move_to([0, 0.15, 0]), T(sub, 16, GREY_B).move_to([0, -0.22, 0]))


class VolcanoVsVector(Base):
    """store-09, section 3. sum(amount) WHERE amount > 9000 over 10 million payments: a plain loop 3.3 ms, one row at
    a time 139 ms. The bookshop: one book per "one more, please". The plan (scan, filter, sum) pulls one row per next()
    call; every row costs a call at every level (the iterator model). The machinery, not the comparison, is the cost
    (X100 2005: MySQL 26.6 s, arithmetic under a tenth, hand-written 0.22 s). A crate per trip: next() returns 1,024
    amounts, one tight loop, under 10,000 calls: 18.8 ms, about 7 times faster (X100 0.50 s). Batch size: 1 brings the
    overhead back, about 1,000 is fastest, above about 8,000 out of the cache. DuckDB 2,048; PostgreSQL one row at a
    time for index lookups. The moral and a check (10 rows through an index)."""

    def cap(self, s, color=GREY_B, size=22):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b, rate_func=linear), run_time=secs)

    def construct(self):
        self.capm = None
        self.title_card("A crate per trip", "why passing rows in batches is faster")

        # ---------------- scene 1: where does the time go? ----------------
        q = M("sum(amount) WHERE amount > 9000", 20).move_to([-4.0, QY, 0])
        b_v = VGroup(bar(0.33, BY[0], BLUE_M), bar(13.93 - 0.33, BY[0], BLUE_M).shift(0.33 * SC * RIGHT))
        l_v = bar_label("one row at a time", "139 ms, 13.9 ns a row", BY[0])
        b_h = bar(0.33, BY[2], YELLOW_M)
        l_h = bar_label("a plain loop", "3.3 ms, 0.33 ns a row", BY[2])
        self.steps("A report adds up every payment above 9,000 cents, out of 10 million payments.", [
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.8),
        ])
        self.steps("Checking one amount takes the processor well under a nanosecond, a billionth of a second. "
                   "Written as one plain loop, the whole job takes 3.3 milliseconds.", [
            "Checking one",
            (lambda: [q.animate(rate_func=there_and_back).set_color(YELLOW_M)], 1.0),
            "Written as",
            (lambda: [FadeIn(l_h), GrowFromEdge(b_h, LEFT)], 0.8),
        ])
        self.steps("Run the usual way, one row at a time through a database's plan, it takes 139. "
                   "So where do the other 136 milliseconds go? Hold that question.", [
            "Run the usual",
            (lambda: [FadeIn(l_v), GrowFromEdge(b_v, LEFT)], 1.2),
            "So where",
            (lambda: [*self.cap("where do the other 136 ms go?", WHITE, 24), glow(b_v[1], RED_M, 1.0)], 0.8),
        ], after=0.3)

        # ---------------- scene 2: one more, please ----------------
        sumb = opbox("Sum", "you, at the counter", BLUE_M).move_to([TX, YS, 0])
        filt = opbox("Filter: amount > 9000", "your friend checks the price", GOLD_M).move_to([TX, YF, 0])
        scan = opbox("Scan payments", "the walk along the shelves", TEAL_M).move_to([TX, YN, 0])
        subs = [sumb[2], filt[2], scan[2]]
        for s in subs:
            s.set_opacity(0)
        strip = VGroup(*[mbox(a, GREY_B, w=0.66, h=0.44, size=13) for a in AMT], T("...", 22, GREY_B)).arrange(RIGHT, buff=0.06)
        strip.move_to([TX, SY, 0])
        # the bookshop: a shelf of books, a friend, and you at the counter
        SH = np.array([-5.4, 0.6, 0])
        shelf = VGroup(*[Line(SH + [-1.05, y, 0], SH + [1.05, y, 0], stroke_width=3, color=GREY_B) for y in (-1.0, 0.0, 1.0)])
        cols = [BLUE_M, TEAL_M, GOLD_M, PURPLE_M, GREEN_M, RED_M]
        books = VGroup(*[Rectangle(width=0.16, height=0.7 + 0.12 * ((k * 7) % 3), stroke_width=0).set_fill(cols[k % 6], 0.75)
                         for k in range(24)])
        for k, bk in enumerate(books):
            row, i = divmod(k, 12)
            bk.move_to(SH + [-0.95 + 0.172 * i, -1.0 + row * 1.0 + bk.height / 2 + 0.03, 0])
        shelf_t = T("the shelves", 18, GREY_B).move_to(SH + [0, -1.4, 0])
        counter = RoundedRectangle(corner_radius=0.06, width=2.0, height=0.45, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M), 1).move_to([-2.2, -0.9, 0])
        you_t = T("you, at the counter", 18, BLUE_M).next_to(counter, DOWN, buff=0.15)
        friend = Dot(radius=0.14, color=GOLD_M).move_to(SH + [0.3, 1.35, 0])
        fr_t = T("your friend", 18, GOLD_M).next_to(friend, UP, buff=0.12)
        shop = VGroup(shelf, books, shelf_t, counter, you_t)

        def fetch(k):
            bk = books[k]
            seq = Succession(friend.animate(run_time=0.4).move_to(bk.get_top() + 0.2 * UP),
                             bk.animate(run_time=0.2, rate_func=there_and_back).set_fill(YELLOW_M, 1),
                             AnimationGroup(friend.animate(run_time=0.6).move_to(counter.get_top() + [0.3 + 0.25 * (k % 3), 0.45, 0]),
                                            bk.animate(run_time=0.6).rotate(PI / 2).move_to(counter.get_top() + [-0.5 + 0.25 * (k % 4), 0.12, 0])))
            return [seq, FadeOut(fr_t)]

        self.steps("Start in a second-hand bookshop. You're at the counter, and a friend fetches novels priced over 5 for you to add up.", [
            (lambda: [*self.uncap(), b_v.animate.set_opacity(0.35), b_h.animate.set_opacity(0.35),
                      l_v.animate.set_opacity(0.4), l_h.animate.set_opacity(0.4), FadeIn(shop)], 0.8),
            "and a friend",
            (lambda: [FadeIn(friend, scale=0.5), FadeIn(fr_t)], 0.5),
            (lambda: self.cap("a bookshop: you at the counter, a friend fetching novels priced over 5", WHITE), 0.6),
        ])
        self.steps("You say: one more, please. Your friend walks along the shelves, checks a price, and brings back one book. "
                   "Then you ask again.", [
            (lambda: self.cap("“one more, please”: one trip, one book", YELLOW_M, 24), 0.6),
            "Your friend walks",
            (lambda: fetch(14), 1.2),
            "Then you ask",
            (lambda: [*self.cap("“one more, please” … and again … and again", YELLOW_M, 24)], 0.5),
            (lambda: fetch(3)[:1], 1.2),
        ])
        self.steps("A database runs our report the same way. Before it runs, the query becomes a plan, a tree of small steps called operators. "
                   "A scan reads the payments, a filter keeps amounts over 9,000, and a sum adds them up.", [
            (lambda: [FadeOut(shop), FadeOut(friend)], 0.6),
            "the query becomes",
            (lambda: self.cap("a plan: a tree of small steps called operators", WHITE), 0.6),
            "A scan reads",
            (lambda: [FadeIn(scan, shift=0.15 * UP), LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in strip], lag_ratio=0.12)], 0.9),
            "a filter keeps",
            (lambda: [FadeIn(filt, shift=0.15 * UP)], 0.7),
            "and a sum",
            (lambda: [FadeIn(sumb, shift=0.15 * UP)], 0.7),
        ])
        a1 = Arrow([TX, YS - BH / 2 - 0.05, 0], [TX, YF + BH / 2 + 0.05, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.25)
        a2 = Arrow([TX, YF - BH / 2 - 0.05, 0], [TX, YN + BH / 2 + 0.05, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.25)
        n1 = left_at(M("next()", 18, GREY_B), TX + 0.22, (YS + YF) / 2)
        n2 = left_at(M("next()", 18, GREY_B), TX + 0.22, (YF + YN) / 2)
        self.steps("Each operator gets its input by asking the one below it for the next row. That ask is a function call, named next.", [
            "Each operator",
            (lambda: [*self.uncap(), GrowArrow(a1), GrowArrow(a2)], 0.7),
            (lambda: [travel(a1, YELLOW_M, 0.45)], 0.5),
            (lambda: [travel(a2, YELLOW_M, 0.45)], 0.5),
            "That ask",
            (lambda: [FadeIn(n1), FadeIn(n2), *self.cap("next(): “one more, please”", YELLOW_M, 24)], 0.6),
        ])
        self.steps("So the sum is you at the counter, the filter is your friend checking the price, and the scan is the walk along the shelves.", [
            (lambda: [*self.uncap(), sumb[1].animate.set_opacity(1), sumb[2].animate.set_opacity(1)], 0.6),
            "the filter is",
            (lambda: [filt[2].animate.set_opacity(1)], 0.6),
            "the scan is",
            (lambda: [scan[2].animate.set_opacity(1)], 0.6),
        ])

        c_lab = left_at(T("calls to next() on the scan", 21, GREY_B), PX, CY_L)
        cnt = left_at(M("0", 30), PX, CY_V)
        rows = {}
        state = {"n": 0}

        def down(a, rt=0.35):
            return (lambda: [travel(a, YELLOW_M, rt)], rt)

        def read(i, rt=0.45):
            def f():
                state["n"] += 1
                rows[i] = mbox(AMT[i], WHITE, w=1.1, h=0.45, size=18).move_to([CX, YN, 0])
                return [glow(strip[i][0], WHITE, 1.08), FadeIn(rows[i], shift=0.25 * RIGHT),
                        Transform(cnt, left_at(M(f"{state['n']:,}", 30), PX, CY_V))]
            return (f, rt)

        def up(i, y, rt=0.4):
            return (lambda: [rows[i].animate.move_to([CX, y, 0])], rt)

        def verdict(i, ok, rt=0.35):
            c = GREEN_M if ok else RED_M
            return (lambda: [rows[i][0].animate.set_stroke(c).set_fill(fillc(c), 1), strip[i].animate.set_opacity(0.35)], rt)

        def drop(i, rt=0.3):
            return (lambda: [FadeOut(rows[i])], rt)

        def add(i, total, rt=0.35):
            return (lambda: [FadeOut(rows[i]), Transform(sumb[1], T(f"Sum: {total}", 21).move_to(sumb[1].get_center())),
                             glow(sumb[0], BLUE_M, 1.03)], rt)

        self.steps("Watch one row. The scan reads 4,200 and hands it up. It fails, so the filter asks again. "
                   "9,700 passes, and the sum adds it.", [
            (lambda: [FadeIn(c_lab), FadeIn(cnt)], 0.4),
            down(a1), down(a2),
            "The scan reads",
            read(0),
            "and hands it up",
            up(0, YF),
            "It fails",
            verdict(0, False), drop(0),
            "so the filter asks",
            down(a2), read(1), up(1, YF),
            "9,700 passes",
            verdict(1, True),
            "and the sum adds",
            up(1, YS), add(1, "9,700"),
        ])
        self.steps("Then the whole chain runs again for the next row. Every row costs a call at every level.", [
            down(a1, 0.2), down(a2, 0.2), read(2, 0.25), up(2, YF, 0.25), verdict(2, False, 0.2), drop(2, 0.15),
            down(a2, 0.2), read(3, 0.25), up(3, YF, 0.25), verdict(3, True, 0.2), up(3, YS, 0.25), add(3, "19,600", 0.25),
            down(a1, 0.2), down(a2, 0.2), read(4, 0.25), up(4, YF, 0.25), verdict(4, True, 0.2), up(4, YS, 0.25),
            add(4, "28,900", 0.25),
            "Every row costs",
            (lambda: [a1.animate(rate_func=there_and_back).set_color(YELLOW_M), a2.animate(rate_func=there_and_back).set_color(YELLOW_M),
                      n1.animate(rate_func=there_and_back).set_color(YELLOW_M), n2.animate(rate_func=there_and_back).set_color(YELLOW_M),
                      *self.cap("every row: a call at every level", WHITE)], 0.9),
        ])
        lv = ValueTracker(np.log10(5))
        cnt2 = always_redraw(lambda: left_at(M(f"{int(round(10 ** lv.get_value())):,}", 30,
                                               RED_M if lv.get_value() > 6.99 else WHITE), PX, CY_V))
        self.steps("This is the iterator model, and PostgreSQL runs queries this way. "
                   "For our report, the scan alone is called 10 million times. The query takes 139 milliseconds, about 14 nanoseconds a row.", [
            (lambda: self.cap("the iterator model: each operator pulls one row per next() call", WHITE), 0.6),
            "the scan alone",
            (lambda: [FadeOut(cnt), FadeIn(cnt2)], 0.1),
            (lambda: [lv.animate(rate_func=linear).set_value(7)], 1.8),
            "The query takes",
            (lambda: [b_v.animate.set_opacity(1), l_v.animate.set_opacity(1), glow(b_v[1], BLUE_M, 1.0)], 0.8),
        ], after=0.3)
        cnt2.clear_updaters()

        # ---------------- scene 3: the machinery ----------------
        ov = T("overhead", 19, RED_M).move_to([BX + 0.33 * SC + (13.93 - 0.33) * SC / 2, BY[0], 0]).set_z_index(3)
        wk = left_at(T("the work itself", 17, YELLOW_M), BX, BY[0] - 0.36)
        self.steps("So, the other 136 milliseconds. You might think the comparison is the slow part. It isn't. "
                   "The plain loop needs a third of a nanosecond a row. The rest is machinery.", [
            "You might think",
            (lambda: self.cap("is the comparison the slow part?", PURPLE_M, 24), 0.6),
            "The plain loop",
            (lambda: [b_h.animate.set_opacity(1), l_h.animate.set_opacity(1), glow(b_h, YELLOW_M, 1.0)], 0.7),
            "The rest is",
            (lambda: [b_v[0].animate.set_fill(YELLOW_M, 0.9), b_v[1].animate.set_fill(RED_M, 0.75), FadeIn(ov), FadeIn(wk),
                      *self.cap("a third of a nanosecond of work; the rest is machinery", WHITE)], 0.9),
        ])
        self.steps("Every call goes through the same door, so the chip can't guess which code comes next. "
                   "And the condition is worked out by walking a little tree, one node for each part of amount over 9,000.", [
            (lambda: [glow(sumb[0], RED_M, 1.03), glow(filt[0], RED_M, 1.03), glow(scan[0], RED_M, 1.03),
                      *self.cap("every next() goes through one door: the chip can't guess what runs next", WHITE)], 1.0),
            "And the condition",
            (lambda: [glow(filt[0], RED_M, 1.05), *self.cap("the condition: worked out by walking a tree of expressions, per row", WHITE)], 1.0),
        ])
        self.steps("Researchers in Amsterdam measured this in 2005, on MySQL, a popular free database program. "
                   "A standard report over 6 million order lines took 26.6 seconds.", [
            (lambda: self.cap("2005, Amsterdam: MySQL, a popular free database program", WHITE), 0.6),
            "A standard report",
            (lambda: self.cap("a report over 6 million order lines: 26.6 seconds", WHITE), 0.6),
        ])
        self.steps("The additions and multiplications were under a tenth of it. A program written by hand took 0.22 seconds.", [
            (lambda: self.cap("the additions and multiplications: under a tenth of that", YELLOW_M), 0.6),
            "A program written",
            (lambda: self.cap("written by hand: 0.22 seconds", WHITE), 0.6),
        ])
        self.steps("Your friend spends the afternoon walking, and about a minute reading prices. "
                   "Wouldn't it be nice if every trip brought back more than one book?", [
            (lambda: [glow(scan[0], TEAL_M, 1.04)], 0.8),
            "Wouldn't it",
            (lambda: self.cap("wanted: more than one book per trip", YELLOW_M, 24), 0.6),
        ], after=0.3)

        # ---------------- scene 4: a crate per trip ----------------
        cells = VGroup(*[mbox(a, WHITE, w=1.1, h=0.34, size=14) for a in AMT + ["2,800"]]).arrange(DOWN, buff=0.05)
        crate_box = SurroundingRectangle(cells, color=GOLD_M, buff=0.08, stroke_width=2.5, corner_radius=0.06)
        b_top = VGroup(T("a crate:", 16, GREY_B), T("1,024 amounts", 16, GREY_B)).arrange(DOWN, buff=0.05).next_to(crate_box, UP, buff=0.1)
        b_dots = T("...", 20, GREY_B).next_to(crate_box, DOWN, buff=0.06)
        batch = VGroup(b_top, cells, b_dots, crate_box)
        batch.move_to([CX, YN + 0.1, 0])
        self.steps("So send your friend with a crate. Vectorized execution changes what next returns: "
                   "a batch of 1,024 amounts, all from one column, in one plain array.", [
            (lambda: [*self.uncap(), strip.animate.set_opacity(1), Transform(sumb[1], T("Sum", 21).move_to(sumb[1].get_center())),
                      cnt2.animate.set_color(GREY_B), b_v.animate.set_opacity(0.45), b_h.animate.set_opacity(0.45),
                      FadeOut(ov), FadeOut(wk), b_v[0].animate.set_fill(BLUE_M, 0.9), b_v[1].animate.set_fill(BLUE_M, 0.9)], 0.7),
            "Vectorized execution",
            (lambda: [*self.cap("vectorized execution: next() returns a batch of values", WHITE), travel(a1, YELLOW_M, 0.35)], 0.6),
            (lambda: [travel(a2, YELLOW_M, 0.35)], 0.4),
            "a batch of",
            (lambda: [*[glow(c[0], WHITE, 1.08) for c in strip[:5]], FadeIn(batch, shift=0.25 * RIGHT),
                      Transform(cnt2, left_at(M("1", 30), PX, CY_V))], 0.9),
        ])
        hl = SurroundingRectangle(cells[0], color=YELLOW_M, buff=0.04, stroke_width=3)
        code = VGroup(M("for (i in 0 until 1024)", 18), M("if (a[i] > 9000) sum += a[i]", 18)).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        code[1].shift(0.45 * RIGHT)
        left_at(code, -0.5, -2.0)
        hl_ok = [False, True, False, True, True, False]

        def sweep():
            seq = []
            for k, ok in enumerate(hl_ok):
                c = GREEN_M if ok else GREY_D
                seq.append(AnimationGroup(hl.animate(run_time=0.15).move_to(cells[k]),
                                          cells[k][0].animate(run_time=0.15).set_stroke(c).set_fill(fillc(c), 1)))
            return [Succession(*seq)]

        quad = SurroundingRectangle(VGroup(*cells[:4]), color=PURPLE_M, buff=0.05, stroke_width=4)
        self.steps("The filter runs one tight loop over the array, with no calls inside. "
                   "The chip can overlap many rows at once, and the compiler can even compare several amounts in one instruction.", [
            (lambda: [batch.animate.move_to([CX, YF + 0.05, 0])], 0.6),
            "one tight loop",
            (lambda: [Create(hl), FadeIn(code), *self.cap("one tight loop over a plain array: no calls inside", WHITE)], 0.5),
            (sweep, 1.6),
            (lambda: [FadeOut(hl)], 0.3),
            "compare several",
            (lambda: [Create(quad), *self.cap("several amounts compared in one instruction", PURPLE_M)], 0.6),
            (lambda: [quad.animate(rate_func=there_and_back).set_stroke(width=7)], 0.8),
            (lambda: [FadeOut(quad)], 0.4),
        ])
        cnt3 = left_at(M("9,766", 30, GREEN_M), PX, CY_V)
        was = T("instead of 10,000,000", 19, GREY_B).next_to(cnt3, RIGHT, buff=0.3)
        self.steps("A call is now paid once per crate. That's under 10,000 calls for 10 million rows.", [
            (lambda: [Transform(sumb[1], T("Sum: 28,900", 21).move_to(sumb[1].get_center())), glow(sumb[0], BLUE_M, 1.03),
                      *self.cap("one call per crate, not per row", WHITE)], 0.7),
            "under 10,000",
            (lambda: [Transform(cnt2, cnt3), FadeIn(was, shift=0.1 * LEFT)], 1.0),
        ], after=0.3)

        # ---------------- scene 5: predict, then show ----------------
        self.steps("So how much faster is the report now? Pause and guess.", [
            (lambda: self.cap("how much faster than 139 ms?  pause and guess", YELLOW_M, 24), 0.6),
        ], after=0)
        self.countdown(3.0)
        b_b = bar(1.88, BY[1], GREEN_M)
        l_b = bar_label("batches of 1,024", "18.8 ms, 1.9 ns a row", BY[1], GREEN_M)
        x7 = left_at(T("about 7 times faster", 20, GREEN_M), BX + 1.88 * SC + 0.3, BY[1])
        self.steps("18.8 milliseconds, about 7 times faster than 139.", [
            (lambda: [*self.uncap(), b_v.animate.set_opacity(1), b_h.animate.set_opacity(1), FadeIn(l_b), GrowFromEdge(b_b, LEFT)], 1.0),
            "about 7",
            (lambda: [FadeIn(x7, shift=0.1 * LEFT)], 0.7),
        ])
        self.steps("In 2005, the Amsterdam team's system, X100, ran its report in half a second, over 50 times faster than MySQL. "
                   "Same books, far fewer trips.", [
            (lambda: self.cap("X100 (2005): 0.50 seconds, over 50 times faster than MySQL's 26.6", WHITE), 0.6),
            "Same books",
            (lambda: [glow(crate_box, GOLD_M, 1.05)], 0.8),
        ], after=0.3)

        # ---------------- scene 6: bigger crates? ----------------
        axis = Line([ax_x(1) - 0.2, AXY, 0], [ax_x(10000) + 0.3, AXY, 0], stroke_width=2.5, color=GREY_B)
        tks = VGroup(*[Line([ax_x(n), AXY - 0.08, 0], [ax_x(n), AXY + 0.08, 0], stroke_width=2, color=GREY_B)
                       for n in (1, 10, 100, 1000, 10000)])
        tls = VGroup(*[T(s, 17, GREY_B).move_to([ax_x(n), AXY - 0.32, 0])
                       for n, s in ((1, "1"), (10, "10"), (100, "100"), (1000, "1,000"), (10000, "10,000"))])
        ax_l = left_at(T("values per batch", 17, GREY_B), ax_x(1) - 0.2, AXY + 0.32)
        mk = Dot(radius=0.11, color=RED_M).move_to([ax_x(1), AXY, 0])

        def note(s, c):
            return T(s, 19, c).move_to([3.0, AXY + 0.62, 0])

        nt = note("1 value per batch: the overhead is back", RED_M)
        self.steps("So, bigger crates, always better? Let's be fair and try. One value per batch brings the call overhead right back.", [
            (lambda: [FadeOut(code), *self.cap("bigger crates, always better?", PURPLE_M, 24), Create(axis), FadeIn(tks), FadeIn(tls), FadeIn(ax_l)], 0.8),
            "One value",
            (lambda: [FadeIn(mk, scale=0.5), FadeIn(nt)], 0.6),
        ])
        self.steps("Around 1,000 was fastest in X100's tests. Above about 8,000, the batch no longer fits in the CPU cache, "
                   "the small, fast memory on the chip, and it slows down again.", [
            (lambda: [FadeOut(ax_l), mk.animate.set_color(GREEN_M).move_to([ax_x(1024), AXY, 0]),
                      Transform(nt, note("about 1,000: fastest", GREEN_M))], 1.0),
            "Above about",
            (lambda: [mk.animate.set_color(GOLD_M).move_to([ax_x(8000), AXY, 0]),
                      Transform(nt, note("above about 8,000: out of the cache, slower", GOLD_M))], 1.0),
            "the small, fast",
            (lambda: self.cap("CPU cache: the small, fast memory on the chip", WHITE), 0.6),
        ])
        self.steps("The crate no longer fits on the counter, so the books go on the floor.", [
            (lambda: [*self.cap("a crate too big for the counter: books on the floor", GOLD_M, 24), glow(sumb[0], GOLD_M, 1.04)], 0.8),
        ], after=0.3)

        # ---------------- scene 7: which databases do which ----------------
        duck = left_at(fit(chip("DuckDB: batches of 2,048, for reports over millions of rows", TEAL_M, 19), 7.1), PX, -1.75)
        pg = left_at(fit(chip("PostgreSQL: one row at a time, for a few rows through an index", BLUE_M, 19), 7.1), PX, -2.5)
        self.steps("DuckDB, a free database program built for reports, runs every query in batches of 2,048.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(axis, tks, tls, mk, nt))], 0.6),
            "runs every",
            (lambda: [FadeIn(duck, shift=0.15 * UP)], 0.7),
        ])
        self.steps("PostgreSQL keeps one row at a time. Its typical query finds a few rows through an index, "
                   "where the cost per row is noise, and small operators are easy to combine.", [
            (lambda: [FadeIn(pg, shift=0.15 * UP)], 0.7),
            "where the cost",
            (lambda: self.cap("a few rows: the cost per row is noise", WHITE), 0.6),
            "and small operators",
            (lambda: [glow(sumb[0], BLUE_M, 1.03), glow(filt[0], GOLD_M, 1.03), glow(scan[0], TEAL_M, 1.03),
                      *self.cap("and small operators are easy to combine", WHITE)], 0.9),
        ], after=0.3)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: passing rows costs a call each time. "
                   "Pass one row per call when there are few rows, and a crate per call when there are millions, so the time goes to the amounts.", [
            (lambda: self.cap("passing rows costs a call each time", YELLOW_M, 26), 0.6),
            "Pass one row",
            (lambda: [*self.cap("few rows: one per call.  millions: a crate per call", YELLOW_M, 26), glow(pg[0], BLUE_M, 1.03)], 0.7),
            "a crate per call",
            (lambda: [glow(duck[0], TEAL_M, 1.03), glow(crate_box, GOLD_M, 1.05)], 0.8),
            "so the time",
            (lambda: [glow(b_h, YELLOW_M, 1.0)], 0.8),
        ], after=0.3)
        q2 = M("10 rows through an index", 20, YELLOW_M).move_to(q.get_center())
        self.steps("One quick check. A support screen finds 10 rows through an index. "
                   "Would batches of 1,024 make it noticeably faster? Pause and think.", [
            (lambda: [*self.uncap(), Transform(q, q2)], 0.7),
            "Would batches",
            (lambda: [glow(b_b, GREEN_M, 1.0)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M, 24), 0.4),
        ], after=0)
        self.countdown(3.0)
        no = tick(False, 0.22).next_to(l_b, LEFT, buff=0.15)
        self.steps("Hardly. Ten rows of overhead is too little to notice. Batches pay off when a query reads millions of rows.", [
            (lambda: [*self.uncap(), Create(no)], 0.5),
            "Ten rows",
            (lambda: self.cap("10 rows: too little overhead to notice", WHITE), 0.6),
            "Batches pay off",
            (lambda: self.cap("batches pay off when a query reads millions of rows", YELLOW_M, 26), 0.7),
        ], after=0.5)
        self.wait(2.0)
