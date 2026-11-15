from sfz import *

SAY.insert(0, (r"\bM-0042\b", "merchant 42"))

TCX = [-6.0, -4.45, -2.55]                  # payments: id, merchant, amount
TRY = [1.85, 1.3, 0.75, 0.2, -0.35]         # payment rows
VCX = [1.5, 3.0, 4.4, 5.8]                  # view: merchant, count, sum, min
VRY = [1.85, 1.3]
YH, YT = 2.45, 3.15                          # header, title
CLX, CVX = -6.4, -3.4                       # counters: label, value
CY = [-1.75, -2.35]
NX, NY = 0.7, [-1.75, -2.3, -2.85]         # notes, bottom right
DX, DY = 0.7, [0.35, -0.2]                 # delta lines, under the view
PAY = [("1", "M-0042", "1,250"), ("2", "M-0042", "300"), ("3", "M-0042", "8,900"), ("4", "M-0007", "4,000"),
       ("9", "M-0042", "150")]


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


def prow(k, color=WHITE):
    return VGroup(*[M(PAY[k][j], 20, color).move_to([TCX[j], TRY[k], 0]) for j in range(3)])


def vcell(s, j, r=0, color=WHITE):
    return M(s, 20, color).move_to([VCX[j], VRY[r], 0])


def counter(s, k, color=WHITE):
    return left_at(M(s, 24, color), CVX, CY[k])


def note(s, k, color=GREY_B):
    return left_at(T(s, 20, color), NX, NY[k])


def delta(s, k, color=TEAL_M):
    return left_at(M(s, 19, color), DX, DY[k])


def rowbox(k, color):
    return Rectangle(width=4.7, height=0.46, stroke_width=0).set_fill(color, 0.25).move_to([-4.2, TRY[k], 0])


class ViewMaintenance(Base):
    """store-12, sections 1 and 2: a view of count, sum and min per merchant for today over a 1,000,000-row payments
    table. A refresh reads every payment and rewrites 24,000 view rows; nightly is a day stale, every minute is 1,440
    full queries. Incremental: insert 150 (count +1, sum +150, min 150), delete 8,900 (min stays), delete the min 150
    (next smallest unknown: rescan M-0042's 2 rows through an index, min 300). Lab: 1,402 rows against 20 million."""

    def construct(self):
        self.title_card("Keeping a view up to date", "recompute everything, or apply each change")

        tt = T("payments: 1,000,000 rows", 22).move_to([-4.2, YT, 0])
        tbox = RoundedRectangle(corner_radius=0.12, width=4.8, height=3.4, stroke_color=GREY_B, stroke_width=2)
        tbox.move_to([-4.2, 1.05, 0])
        th = VGroup(*[T(h, 19, GREY_B).move_to([TCX[j], YH, 0]) for j, h in enumerate(["id", "merchant", "amount"])])
        rows = [prow(k) for k in range(5)]
        vt = T("view: today, per merchant", 22).move_to([3.6, YT, 0])
        vbox = RoundedRectangle(corner_radius=0.12, width=5.95, height=1.7, stroke_color=BLUE_M, stroke_width=2.5)
        vbox.move_to([3.6, 1.88, 0])
        vh = VGroup(*[T(h, 19, GREY_B).move_to([VCX[j], YH, 0]) for j, h in enumerate(["merchant", "count", "sum", "min"])])
        vr = [VGroup(vcell("M-0042", 0), vcell("3", 1), vcell("10,450", 2), vcell("300", 3)),
              VGroup(vcell("M-0007", 0, 1), vcell("1", 1, 1), vcell("4,000", 2, 1), vcell("4,000", 3, 1))]
        arr = Arrow([-1.6, 1.6, 0], [0.5, 1.6, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.1)
        alab = T("the query", 18, GREY_B).move_to([-0.6, 1.95, 0])
        self.steps("The settlement dashboard shows each merchant's payments today: how many and how much. "
                   "A materialized view stores that answer, one row per merchant.", [
            (lambda: [FadeIn(tt), Create(tbox), FadeIn(th), LaggedStart(*[FadeIn(r) for r in rows[:4]], lag_ratio=0.2)], 1.4),
            "A materialized view",
            (lambda: [GrowArrow(arr), FadeIn(alab)], 0.6),
            (lambda: [FadeIn(vt), Create(vbox), FadeIn(vh), FadeIn(vr[0]), FadeIn(vr[1])], 1.0),
        ])

        mode = left_at(T("refresh: run the whole query again", 21, GOLD_M), CLX, -1.15)
        rl = left_at(T("payments read", 20, GREY_B), CLX, CY[0])
        wl = left_at(T("view rows written", 20, GREY_B), CLX, CY[1])
        rd = ValueTracker(0)
        rv = always_redraw(lambda: counter(f"{int(round(rd.get_value())):,}", 0, GOLD_M))
        wv = counter("0", 1, GOLD_M)
        sweep = Rectangle(width=4.7, height=0.46, stroke_width=0).set_fill(GOLD_M, 0.25).move_to([-4.2, TRY[0], 0])
        self.steps("The simple way to keep it right is to run the query again. A refresh reads all million payments "
                   "and rewrites twenty-four thousand view rows, to change one number.", [
            (lambda: [FadeIn(mode), FadeIn(rl), FadeIn(wl), FadeIn(rv), FadeIn(wv),
                      Transform(alab, T("refresh", 18, GOLD_M).move_to([-0.6, 1.95, 0])), arr.animate.set_color(GOLD_M)], 0.8),
            "A refresh reads",
            (lambda: [FadeIn(sweep)], 0.2),
            (lambda: [Succession(*[sweep.animate(run_time=0.4).move_to([-4.2, TRY[k], 0]) for k in (1, 2, 3)]),
                      rd.animate(rate_func=linear).set_value(1000000)], 1.6),
            (lambda: [FadeOut(sweep), travel(arr, GOLD_M, 0.6)], 0.7),
            "and rewrites",
            (lambda: [Transform(wv, counter("24,000", 1, GOLD_M)), glow(vbox, GOLD_M, 1.02)], 0.9),
        ])
        rv.clear_updaters()

        nb = rowbox(4, GREEN_M)
        stale = note("refreshed nightly: missing until tomorrow", 0, RED_M)
        self.steps("Refresh once a night, and a payment that arrives now is missing until tomorrow.", [
            "a payment that",
            (lambda: [FadeIn(nb), FadeIn(rows[4], shift=0.2 * DOWN)], 0.7),
            "is missing",
            (lambda: [*[c.animate.set_color(RED_M) for c in vr[0][1:]], FadeIn(stale)], 0.8),
        ])

        often = note("every minute: 1,440 refreshes a day,", 1, GOLD_M)
        often2 = note("each reading 1,000,000 payments", 2, GOLD_M)
        self.steps("Refresh every minute instead, and the database reads the whole table 1,440 times a day.", [
            (lambda: [FadeIn(often)], 0.7),
            "reads the whole",
            (lambda: [FadeIn(often2), glow(tbox, GOLD_M, 1.02)], 0.9),
        ])

        # ---- incremental maintenance -----------------------------------------------------------------------------
        mode2 = left_at(T("incremental: apply each change", 21, TEAL_M), CLX, -1.15)
        d1 = delta("count + 1, sum + 150", 0)
        d2 = delta("min(300, 150) = 150", 1)
        self.steps("Incremental maintenance works from the change instead. Merchant 42 gets a new payment of 150. "
                   "Its count goes up by one, its sum by 150, and its minimum becomes the smaller of 300 and 150.", [
            (lambda: [FadeOut(VGroup(stale, often, often2)), Transform(mode, mode2), Transform(rv, counter("0", 0, TEAL_M)),
                      Transform(wv, counter("0", 1, TEAL_M)), Transform(alab, T("the change", 18, TEAL_M).move_to([-0.6, 1.95, 0])),
                      arr.animate.set_color(TEAL_M), *[c.animate.set_color(WHITE) for c in vr[0][1:]]], 0.9),
            "Merchant 42 gets",
            (lambda: [glow(nb, TEAL_M, 1.03), travel(arr, TEAL_M, 0.7)], 0.8),
            "Its count",
            (lambda: [FadeIn(d1, shift=0.1 * DOWN), Transform(vr[0][1], vcell("4", 1, 0, TEAL_M)),
                      Transform(vr[0][2], vcell("10,600", 2, 0, TEAL_M))], 0.8),
            "and its minimum",
            (lambda: [FadeIn(d2, shift=0.1 * DOWN), Transform(vr[0][3], vcell("150", 3, 0, TEAL_M)),
                      Transform(wv, counter("1", 1, TEAL_M))], 0.8),
        ])

        self.steps("No payment was read from the table. One view row changed, however big the table is.", [
            (lambda: [glow(rv, TEAL_M, 1.2)], 0.8),
            "One view row",
            (lambda: [glow(vbox, TEAL_M, 1.02), FadeOut(nb)], 0.9),
        ])

        x3 = Line([TCX[0] - 0.3, TRY[2], 0], [TCX[2] + 0.55, TRY[2], 0], stroke_width=3, color=RED_M)
        self.steps("A delete is the mirror image. Remove the 8,900: count down by one, sum down by 8,900. "
                   "It was above the minimum, so the minimum stays.", [
            "Remove the",
            (lambda: [rows[2].animate.set_color(RED_M), Create(x3)], 0.7),
            (lambda: [travel(arr, RED_M, 0.6)], 0.6),
            "count down",
            (lambda: [Transform(d1, delta("count - 1, sum - 8,900", 0, RED_M)), Transform(vr[0][1], vcell("3", 1, 0, RED_M)),
                      Transform(vr[0][2], vcell("1,700", 2, 0, RED_M)), Transform(wv, counter("2", 1, TEAL_M))], 0.8),
            "It was above",
            (lambda: [Transform(d2, delta("8,900 > 150: min stays", 1, TEAL_M)), glow(vr[0][3], TEAL_M, 1.3)], 0.8),
            (lambda: [rows[2].animate.set_opacity(0.3), x3.animate.set_opacity(0.3)], 0.4),
        ])

        x9 = Line([TCX[0] - 0.3, TRY[4], 0], [TCX[2] + 0.55, TRY[4], 0], stroke_width=3, color=RED_M)
        q = vcell("?", 3, 0, RED_M).scale(1.4)
        self.steps("Now delete the 150, the minimum itself. Count and sum still work. "
                   "But the view kept one number per merchant, and the next smallest was never stored.", [
            (lambda: [rows[4].animate.set_color(RED_M), Create(x9)], 0.7),
            (lambda: [travel(arr, RED_M, 0.6)], 0.6),
            "Count and sum",
            (lambda: [Transform(d1, delta("count - 1, sum - 150", 0, RED_M)), Transform(vr[0][1], vcell("2", 1, 0, RED_M)),
                      Transform(vr[0][2], vcell("1,550", 2, 0, RED_M))], 0.8),
            "But the view",
            (lambda: [Transform(vr[0][3], q), Transform(d2, delta("150 was the min. Next one?", 1, RED_M))], 0.8),
            "never stored",
            (lambda: [glow(vbox, RED_M, 1.02)], 0.9),
        ])

        ix = Arrow([0.5, 1.15, 0], [-1.6, 0.95, 0], buff=0, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.1)
        ixl = T("index on merchant", 17, GOLD_M).move_to([-0.55, 0.62, 0])
        hb = [rowbox(0, GOLD_M), rowbox(1, GOLD_M)]
        self.steps("So the delete goes back to the table. Through an index on the merchant, it reads merchant 42's "
                   "two remaining payments and finds 300.", [
            (lambda: [rows[4].animate.set_opacity(0.3), x9.animate.set_opacity(0.3), GrowArrow(ix), FadeIn(ixl)], 0.8),
            "it reads",
            (lambda: [FadeIn(hb[0]), FadeIn(hb[1]), Transform(rv, counter("2", 0, GOLD_M))], 0.8),
            "and finds 300",
            (lambda: [Transform(vr[0][3], vcell("300", 3, 0, GOLD_M)), Transform(d2, delta("min(1,250, 300) = 300", 1, GOLD_M)),
                      Transform(wv, counter("3", 1, TEAL_M))], 0.8),
        ])

        mem = left_at(T("or keep every amount per merchant, sorted:", 18, GREY_B), NX, NY[0])
        mem2 = left_at(M("M-0042: 300, 1,250", 18, PURPLE_M), NX, NY[1])
        self.steps("That costs one merchant's rows, not the table. "
                   "The other way out is to keep every amount, sorted, and pay in memory instead.", [
            (lambda: [glow(hb[0], GOLD_M, 1.04), glow(hb[1], GOLD_M, 1.04)], 0.9),
            "The other way",
            (lambda: [FadeOut(hb[0]), FadeOut(hb[1]), FadeOut(ix), FadeOut(ixl), FadeIn(mem)], 0.7),
            "keep every amount",
            (lambda: [FadeIn(mem2, shift=0.1 * UP)], 0.7),
        ])

        lab1 = note("lab, 1,000 changes to 20,000 payments:", 0, GREY_B)
        lab2 = note("incremental: 1,402 rows of work", 1, TEAL_M)
        lab3 = note("refresh after each: 20,000,000 rows", 2, GOLD_M)
        self.steps("In the lab, a thousand changes to twenty thousand payments cost 1,402 rows of work this way. "
                   "A full refresh after each change would read twenty million.", [
            (lambda: [FadeOut(mem), FadeOut(mem2)], 0.35), (lambda: [FadeIn(lab1)], 0.35),
            "cost 1,402",
            (lambda: [FadeIn(lab2, shift=0.1 * UP)], 0.7),
            "A full refresh",
            (lambda: [FadeIn(lab3, shift=0.1 * UP)], 0.7),
        ])

        self.steps("Count and sum follow from the change alone. "
                   "A minimum needs the next value, so deleting it sends you back to the table.", [
            (lambda: [glow(vr[0][1], TEAL_M, 1.3), glow(vr[0][2], TEAL_M, 1.2)], 0.9),
            "A minimum needs",
            (lambda: [glow(vr[0][3], GOLD_M, 1.4)], 0.8),
            "back to the table",
            (lambda: [glow(tbox, GOLD_M, 1.02)], 0.9),
        ])
        self.wait(0.6)
