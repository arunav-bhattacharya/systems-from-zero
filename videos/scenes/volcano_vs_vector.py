from sfz import *

TX, CX = -4.6, -2.0                 # the plan tree, and the column where a row or a batch sits beside its operator
YS, YF, YN = 1.9, 0.3, -1.3         # sum, filter, scan
BW, BH = 3.4, 0.8
QY = 3.35
SY = -2.5                           # the payments strip under the scan
PX = -0.7                           # right panel, left edge
CY_L, CY_V = 2.95, 2.4              # counter label and value
BX, SC = 2.2, 4.2 / 13.9            # bar start, units per nanosecond
BY = [1.25, 0.05, -1.15]            # bars: one row at a time, batches, hand-written loop
AXY = -2.75                         # batch size axis
AMT = ["4,200", "9,700", "1,100", "9,900", "9,300", "2,800"]


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


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


def bar(ns, y, color):
    return Rectangle(width=max(0.06, ns * SC), height=0.42, stroke_width=0).set_fill(color, 0.9).move_to(
        [BX + max(0.06, ns * SC) / 2, y, 0])


def bar_label(name, sub, y, color=WHITE):
    return VGroup(left_at(T(name, 22, color), PX, y + 0.17), left_at(T(sub, 18, GREY_B), PX, y - 0.2))


def ax_x(n):
    return -0.2 + 1.5 * np.log10(n)


class VolcanoVsVector(Base):
    """store-09, section 3: sum(amount) WHERE amount > 9000 over 10 million payments. The iterator model pulls one row
    per next() call through scan, filter and sum (lesson's demo: 139 ms, 13.9 ns a row; a hand-written loop 0.33 ns).
    Vectorized execution returns 1,024 amounts per call and loops over the array: 18.8 ms, 1.9 ns a row. Batch size:
    1 brings the overhead back, about 1,000 is fastest, above about 8,000 the batch falls out of cache (X100)."""

    def construct(self):
        self.title_card("One row at a time, or a thousand", "the iterator model and vectorized execution")

        q = M("sum(amount) WHERE amount > 9000", 18).move_to([-4.25, QY, 0])
        strip = VGroup(*[mbox(a, GREY_B, w=0.74, h=0.48, size=13) for a in AMT[:5]]).arrange(RIGHT, buff=0.05)
        strip.move_to([-4.6, SY, 0])
        s_lab = T("payments: 10,000,000 rows", 18, GREY_B).move_to([-4.6, SY - 0.6, 0])
        self.steps("A report sums every payment over ninety euros, out of ten million rows. "
                   "One comparison takes under a nanosecond.", [
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.8),
            "out of ten",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in strip], lag_ratio=0.15), FadeIn(s_lab)], 1.0),
            "One comparison",
            (lambda: [q.animate(rate_func=there_and_back).set_color(YELLOW_M)], 1.0),
        ])

        sumb = box("Sum", BLUE_M, w=BW, h=BH, size=21).move_to([TX, YS, 0])
        filt = box("Filter: amount > 9000", GOLD_M, w=BW, h=BH, size=21).move_to([TX, YF, 0])
        scan = box("Scan payments", TEAL_M, w=BW, h=BH, size=21).move_to([TX, YN, 0])
        self.steps("The database runs it as a plan, a tree of small operators. "
                   "A scan reads the table, a filter keeps amounts over 9,000, a sum adds them.", [
            "A scan reads",
            (lambda: [FadeIn(scan, shift=0.15 * UP)], 0.7),
            "a filter keeps",
            (lambda: [FadeIn(filt, shift=0.15 * UP)], 0.7),
            "a sum adds",
            (lambda: [FadeIn(sumb, shift=0.15 * UP)], 0.7),
        ])

        a1 = Arrow([TX, YS - BH / 2 - 0.06, 0], [TX, YF + BH / 2 + 0.06, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.25)
        a2 = Arrow([TX, YF - BH / 2 - 0.06, 0], [TX, YN + BH / 2 + 0.06, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.25)
        n1 = left_at(M("next()", 18, GREY_B), TX + 0.22, (YS + YF) / 2)
        n2 = left_at(M("next()", 18, GREY_B), TX + 0.22, (YF + YN) / 2)
        self.steps("Each operator asks its child for the next row: "
                   "the sum calls next on the filter, the filter calls next on the scan.", [
            "the sum calls",
            (lambda: [GrowArrow(a1), FadeIn(n1)], 0.7),
            (lambda: [travel(a1, YELLOW_M, 0.5)], 0.6),
            "the filter calls",
            (lambda: [GrowArrow(a2), FadeIn(n2)], 0.7),
            (lambda: [travel(a2, YELLOW_M, 0.5)], 0.6),
        ])

        c_lab = left_at(T("calls to next() on the scan", 22, GREY_B), PX, CY_L)
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
            return (lambda: [FadeOut(rows[i]), Transform(sumb[1], T(f"Sum: {total}", 21).move_to([TX, YS, 0])),
                             glow(sumb[0], BLUE_M, 1.03)], rt)

        self.steps("The scan reads one payment and hands it up. 4,200 fails, so the filter asks again. "
                   "9,700 passes, and the sum adds it.", [
            (lambda: [FadeIn(c_lab), FadeIn(cnt)], 0.4),
            down(a1), down(a2), read(0),
            "and hands it up",
            up(0, YF),
            "4,200 fails",
            verdict(0, False), drop(0),
            "so the filter asks",
            down(a2), read(1), up(1, YF),
            "9,700 passes",
            verdict(1, True),
            "and the sum adds",
            up(1, YS), add(1, "9,700"),
        ])

        self.steps("Then the chain runs again for the next row. Every row costs a function call at every level.", [
            down(a1, 0.25), down(a2, 0.25), read(2, 0.3), up(2, YF, 0.3), verdict(2, False, 0.25), drop(2, 0.2),
            down(a2, 0.25), read(3, 0.3), up(3, YF, 0.3), verdict(3, True, 0.25), up(3, YS, 0.3), add(3, "19,600", 0.3),
            down(a1, 0.25), down(a2, 0.25), read(4, 0.3), up(4, YF, 0.3), verdict(4, True, 0.25), up(4, YS, 0.3),
            add(4, "28,900", 0.3),
            "Every row costs",
            (lambda: [a1.animate(rate_func=there_and_back).set_color(YELLOW_M),
                      a2.animate(rate_func=there_and_back).set_color(YELLOW_M),
                      n1.animate(rate_func=there_and_back).set_color(YELLOW_M),
                      n2.animate(rate_func=there_and_back).set_color(YELLOW_M)], 0.9),
        ])

        lv = ValueTracker(np.log10(5))
        cnt2 = always_redraw(lambda: left_at(M(f"{int(round(10 ** lv.get_value())):,}", 30,
                                               RED_M if lv.get_value() > 6.99 else WHITE), PX, CY_V))
        self.remove(cnt)
        self.add(cnt2)
        b_v = VGroup(bar(0.33, BY[0], BLUE_M), bar(13.9 - 0.33, BY[0], BLUE_M).shift(0.33 * SC * RIGHT))
        l_v = bar_label("one row at a time", "13.9 ns a row, 139 ms", BY[0])
        self.steps("For ten million rows, the scan alone is called ten million times. "
                   "The query takes 139 milliseconds, about fourteen nanoseconds a row.", [
            "the scan alone",
            (lambda: [lv.animate(rate_func=linear).set_value(7)], 1.8),
            "The query takes",
            (lambda: [FadeIn(l_v), GrowFromEdge(b_v, LEFT)], 1.2),
        ])
        cnt2.clear_updaters()

        b_h = bar(0.33, BY[2], YELLOW_M)
        l_h = bar_label("hand-written loop", "0.33 ns a row, 3.3 ms", BY[2])
        ov = T("overhead", 20, RED_M).move_to([BX + 0.33 * SC + (13.9 - 0.33) * SC / 2, BY[0] + 0.45, 0])
        wk = left_at(T("the work itself", 18, YELLOW_M), BX, BY[0] - 0.42)
        self.steps("A loop written by hand needs a third of a nanosecond. "
                   "The rest is machinery: calls through an interface, and an expression tree for every amount.", [
            (lambda: [FadeIn(l_h), GrowFromEdge(b_h, LEFT)], 0.9),
            "The rest is",
            (lambda: [b_v[0].animate.set_fill(YELLOW_M, 0.9), b_v[1].animate.set_fill(RED_M, 0.75), FadeIn(ov), FadeIn(wk)], 0.9),
            "calls through",
            (lambda: [glow(sumb[0], RED_M, 1.03), glow(filt[0], RED_M, 1.03), glow(scan[0], RED_M, 1.03)], 1.0),
            "and an expression",
            (lambda: [glow(filt[0], RED_M, 1.05)], 0.9),
        ])

        cells = VGroup(*[mbox(a, WHITE, w=1.1, h=0.34, size=14) for a in AMT]).arrange(DOWN, buff=0.05)
        b_top = T("1,024 amounts", 17, GREY_B).next_to(cells, UP, buff=0.12)
        b_dots = T("...", 22, GREY_B).next_to(cells, DOWN, buff=0.1)
        batch = VGroup(b_top, cells, b_dots)
        batch.move_to([CX, YN + 0.15, 0])
        self.steps("Vectorized execution changes what next returns: a batch of 1,024 amounts in one plain array.", [
            (lambda: [strip.animate.set_opacity(1), Transform(sumb[1], T("Sum", 21).move_to([TX, YS, 0])),
                      cnt2.animate.set_color(GREY_B), b_v.animate.set_opacity(0.5), b_h.animate.set_opacity(0.5),
                      FadeOut(ov), FadeOut(wk)], 0.7),
            down(a1, 0.35), down(a2, 0.35),
            "a batch of",
            (lambda: [*[glow(c[0], WHITE, 1.08) for c in strip], FadeIn(batch, shift=0.25 * RIGHT),
                      Transform(cnt2, left_at(M("1", 30), PX, CY_V))], 0.9),
        ])

        hl = SurroundingRectangle(cells[0], color=YELLOW_M, buff=0.04, stroke_width=3)
        code = VGroup(M("for (i in 0 until 1024)", 17), M("    if (a[i] > 9000) sum += a[i]", 17)).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        code[1].shift(0.45 * RIGHT)
        left_at(code, -0.5, -2.55)
        hl_ok = [False, True, False, True, True, False]

        def sweep():
            seq = []
            for k, ok in enumerate(hl_ok):
                c = GREEN_M if ok else GREY_D
                seq.append(AnimationGroup(hl.animate(run_time=0.15).move_to(cells[k]),
                                          cells[k][0].animate(run_time=0.15).set_stroke(c).set_fill(fillc(c), 1)))
            return [Succession(*seq)]

        quad = SurroundingRectangle(VGroup(*cells[:4]), color=PURPLE_M, buff=0.07, stroke_width=4)
        self.steps("The filter runs one tight loop over the array, with no calls inside. "
                   "The compiler can even make it compare several amounts in one instruction.", [
            (lambda: [batch.animate.move_to([CX, YF + 0.05, 0])], 0.6),
            "one tight loop",
            (lambda: [Create(hl), FadeIn(code)], 0.5),
            (sweep, 1.6),
            (lambda: [FadeOut(hl)], 0.3),
            "compare several",
            (lambda: [Create(quad)], 0.6),
            (lambda: [quad.animate(rate_func=there_and_back).set_stroke(width=7)], 0.8),
            (lambda: [FadeOut(quad)], 0.4),
        ])

        cnt3 = left_at(M("9,766", 30, GREEN_M), PX, CY_V)
        was = T("instead of 10,000,000", 20, GREY_B).next_to(cnt3, RIGHT, buff=0.3)
        self.steps("Now a call is paid once per batch: under ten thousand calls for ten million rows.", [
            (lambda: [batch.animate.move_to([CX, YS - 0.6, 0])], 0.6),
            (lambda: [Transform(sumb[1], T("Sum: 28,900", 21).move_to([TX, YS, 0])), glow(sumb[0], BLUE_M, 1.03)], 0.6),
            "under ten thousand",
            (lambda: [Transform(cnt2, cnt3), FadeIn(was, shift=0.1 * LEFT)], 1.0),
        ])

        b_b = bar(1.88, BY[1], GREEN_M)
        l_b = bar_label("batches of 1,024", "1.9 ns a row, 18.8 ms", BY[1], GREEN_M)
        x7 = T("about 7 times faster", 20, GREEN_M).move_to([BX + 1.88 * SC + 0.35 + 1.05, BY[1], 0])
        self.steps("The query now takes 19 milliseconds, about seven times faster.", [
            (lambda: [b_v.animate.set_opacity(1), b_h.animate.set_opacity(1), FadeIn(l_b), GrowFromEdge(b_b, LEFT)], 1.0),
            "about seven",
            (lambda: [FadeIn(x7, shift=0.1 * LEFT)], 0.7),
        ])

        axis = Line([ax_x(1) - 0.2, AXY, 0], [ax_x(10000) + 0.3, AXY, 0], stroke_width=2.5, color=GREY_B)
        tks = VGroup(*[Line([ax_x(n), AXY - 0.08, 0], [ax_x(n), AXY + 0.08, 0], stroke_width=2, color=GREY_B)
                       for n in (1, 10, 100, 1000, 10000)])
        tls = VGroup(*[T(s, 17, GREY_B).move_to([ax_x(n), AXY - 0.32, 0])
                       for n, s in ((1, "1"), (10, "10"), (100, "100"), (1000, "1,000"), (10000, "10,000"))])
        ax_l = T("values per batch", 17, GREY_B).move_to([(ax_x(1) + ax_x(10)) / 2 + 0.1, AXY + 0.32, 0])
        mk = Dot(radius=0.11, color=RED_M).move_to([ax_x(1), AXY, 0])

        def note(s, c):
            return T(s, 20, c).move_to([2.9, AXY + 0.62, 0])

        nt = note("one value per batch: the overhead is back", RED_M)
        self.steps("Why a thousand? One value per batch brings the overhead back. "
                   "Above about eight thousand, a batch no longer fits in the processor's cache.", [
            (lambda: [FadeOut(code), Create(axis), FadeIn(tks), FadeIn(tls), FadeIn(ax_l)], 0.8),
            "One value",
            (lambda: [FadeIn(mk, scale=0.5), FadeIn(nt)], 0.6),
            1.0,
            (lambda: [FadeOut(ax_l), mk.animate.set_color(GREEN_M).move_to([ax_x(1024), AXY, 0]),
                      Transform(nt, note("about 1,000: fastest", GREEN_M))], 1.0),
            "Above about",
            (lambda: [mk.animate.set_color(GOLD_M).move_to([ax_x(8000), AXY, 0]),
                      Transform(nt, note("above about 8,000: out of the cache, slower", GOLD_M))], 1.0),
        ])

        duck = left_at(chip("DuckDB: batches of 2,048", TEAL_M, 20), -0.5, -2.3)
        pg = left_at(chip("PostgreSQL: one row at a time", BLUE_M, 20), -0.5, -3.05)
        self.steps("DuckDB runs every query in batches of 2,048. "
                   "PostgreSQL keeps one row at a time: its queries mostly fetch a few rows by index.", [
            (lambda: [FadeOut(VGroup(axis, tks, tls, mk, nt))], 0.6),
            (lambda: [FadeIn(duck, shift=0.15 * UP)], 0.7),
            "PostgreSQL keeps",
            (lambda: [FadeIn(pg, shift=0.15 * UP)], 0.7),
        ])

        self.steps("A call per row is fine for ten rows. For ten million, pass a thousand at a time, "
                   "so the time goes to the amounts.", [
            (lambda: [glow(pg[0], BLUE_M, 1.04)], 0.9),
            "For ten million",
            (lambda: [glow(duck[0], TEAL_M, 1.04), *[c[0].animate(rate_func=there_and_back).set_stroke(width=6) for c in cells]], 1.0),
            "to the amounts",
            (lambda: [b_h.animate(rate_func=there_and_back).stretch(1.0, 1).set_fill(WHITE, 1)], 0.8),
        ])
        self.wait(0.6)
