from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz" (Whisper hears "posters"); spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bM-0042('s)?", lambda m: "M forty-two" + (m.group(1) or "")))
SAY.insert(0, (r"\bM-0007('s)?", lambda m: "M seven" + (m.group(1) or "")))
SAY.insert(0, (r"\bpg_ivm\b", "P G I V M"))
SAY.insert(0, (r"\b1\.20\b", "one twenty"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TB_X0, TB_X1, TB_TOP, TB_BOT = -6.45, -1.55, 2.1, -1.15          # the payments table
TCX = [-5.95, -4.45, -1.95]                                        # id, shop (centres); amount (right edge)
TH_Y = 1.7
TY = [1.2, 0.7, 0.2, -0.3, -0.8]
VW_X0, VW_X1, VW_TOP, VW_BOT = 0.25, 6.45, 2.1, 0.25               # the view
VCX = (VW_X0 + VW_X1) / 2
VX = [1.15, 2.85, 4.35, 5.8]                                       # shop, count, sum, min
VH_Y = 1.7
VRY = [1.15, 0.6]
CHIP_Y, DELTA_Y, CNT_Y, TRAY_Y = 3.2, -0.2, -0.85, -1.65
BAR1_Y, BAR2_Y = -1.65, -2.2
BAR_Y, CAP_Y = -2.75, -3.25
PAY = [("1", "M-0042", "1,250"), ("2", "M-0042", "300"), ("3", "M-0042", "8,900"), ("4", "M-0007", "4,000"), ("9", "M-0042", "150")]


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




def bar(x0, y, length, color, h=0.3):
    return Rectangle(width=max(length, 0.04), height=h, stroke_width=0).set_fill(color, 0.85).move_to([x0 + max(length, 0.04) / 2, y, 0])


class ViewMaintenance(Base):
    """store-12, section 2. The café whiteboard: takings kept sale by sale, and "cheapest sale today: 1.20", a tea that
    comes back. A materialized view and a refresh (a million payments read to change one number). The stepper: insert
    payment 9 (count + 1, sum + 150, min 150: no table row read: a delta rule); delete 8,900 (min stays); delete 150,
    the minimum (the view can't know the next one); two ways out (rescan one shop through an index: 300; or keep every
    amount sorted); delete M-0007's only payment (its row leaves). 2 rows read, 4 written: incremental view
    maintenance. Deltas lose on a batch deleting 90% (35,994 against 2,200). The moral, and a check (delete 1,250)."""

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

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b), run_time=secs, rate_func=linear)

    # ---- the view's cells ----
    def vtext(self, r, c, s, color=WHITE):
        return M(s, 21, color).move_to([VX[c], VRY[r], 0])

    def vset(self, r, c, s, color=YELLOW_M):
        old = self.v[(r, c)]
        new = self.vtext(r, c, s, color)
        self.v[(r, c)] = new
        return [swap(old, new)]

    def whiten(self):
        return [m.animate.set_color(WHITE) for (r, c), m in self.v.items() if c > 0 and r in self.live]

    def change(self, s):
        return self.put("chip", chip(s, YELLOW_M, 22, mono=True).move_to([0, CHIP_Y, 0]))

    def delta(self, s, color=YELLOW_M):
        return self.put("delta", fit(T(s, 22, color), VW_X1 - VW_X0 - 0.2).move_to([VCX, DELTA_Y, 0]))

    def count(self, r, w):
        self.work = (r, w)
        return self.put("cnt", T(f"table rows read: {r}      view rows written: {w}", 22).move_to([VCX, CNT_Y, 0]))

    def strike(self, k):
        row = self.trows[k]
        ln = Line([TB_X0 + 0.2, TY[k], 0], [TB_X1 - 0.2, TY[k], 0], stroke_width=3, color=RED_M).set_z_index(4)
        self.strikes[k] = ln
        return [Create(ln), row.animate.set_opacity(0.4)]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.strikes = {}
        self.live = {0, 1}
        self.title_card("The refunded tea", "keeping a stored answer right, one change at a time")

        # ---------------- scene 1: the whiteboard ----------------
        WB = np.array([0, 0.75, 0])
        wb = RoundedRectangle(corner_radius=0.16, width=8.8, height=2.9, stroke_color=WHITE, stroke_width=3).set_fill("#141414", 1).move_to(WB)
        wbt = T("the whiteboard by the till", 20, GREY_B).move_to(WB + [0, 1.08, 0])
        l1 = left_at(T("takings today:  add each sale, take off each refund", 26), -4.0, WB[1] + 0.35)
        l2 = left_at(T("cheapest sale today:  1.20  (a small tea)", 26), -4.0, WB[1] - 0.5)
        l1b = left_at(T("takings today:  take off 1.20", 26, GREEN_M), -4.0, WB[1] + 0.35)
        l2b = left_at(T("cheapest sale today:", 26), -4.0, WB[1] - 0.5)
        q2 = T("?", 40, YELLOW_M).next_to(l2b, RIGHT, buff=0.35)
        ok1 = tick(True, 0.22).next_to(l1b, RIGHT, buff=0.35)
        refund = chip("refund: the tea, 1.20", GOLD_M, 24).move_to([0, -1.35, 0])
        self.steps("Picture a busy café. On a whiteboard by the till, the owner keeps today's takings. Each sale, she adds the "
                   "amount. Each refund, she takes it off.", [
            "On a whiteboard",
            (lambda: [FadeIn(wb), FadeIn(wbt)], 0.7),
            "Each sale",
            (lambda: [FadeIn(l1, shift=0.05 * RIGHT)], 0.7),
        ])
        self.steps("When a regular asks how the day is going, she reads the board instead of counting the till.", [
            "she reads the board",
            (lambda: [glow(wb, YELLOW_M, 1.02)], 0.8),
        ])
        self.steps("One afternoon she adds a second line: cheapest sale today, 1.20, a small tea. Then the customer brings the tea "
                   "back for a refund.", [
            "a second line",
            (lambda: [FadeIn(l2, shift=0.05 * RIGHT)], 0.7),
            "Then the customer",
            (lambda: [FadeIn(refund, shift=0.15 * UP)], 0.6),
        ])
        self.steps("The takings are easy: take off 1.20. But what should the second line say now? Hold that question.", [
            (lambda: [swap(l1, l1b)], 0.6),
            (lambda: [Create(ok1)], 0.4),
            "But what",
            (lambda: [swap(l2, l2b), FadeIn(q2, scale=0.6)], 0.7),
            "Hold that",
            (lambda: self.cap("what should the second line say now?", WHITE), 0.5),
        ], after=0.3)

        # ---------------- scene 2: a stored answer, and a refresh ----------------
        tbox = RoundedRectangle(corner_radius=0.14, width=TB_X1 - TB_X0, height=TB_TOP - TB_BOT, stroke_color=BLUE_M, stroke_width=3) \
            .set_fill(fillc(BLUE_M), 1).move_to([(TB_X0 + TB_X1) / 2, (TB_TOP + TB_BOT) / 2, 0])
        ttl = T("payments: the table", 22, BLUE_M).move_to([(TB_X0 + TB_X1) / 2, 2.5, 0])
        thead = VGroup(T("id", 18, GREY_B).move_to([TCX[0], TH_Y, 0]), T("shop", 18, GREY_B).move_to([TCX[1], TH_Y, 0]),
                       right_at(T("amount", 18, GREY_B), TCX[2], TH_Y))
        self.trows = [VGroup(M(i, 20).move_to([TCX[0], TY[k], 0]), M(s, 20).move_to([TCX[1], TY[k], 0]), right_at(M(a, 20), TCX[2], TY[k]))
                      for k, (i, s, a) in enumerate(PAY)]
        vbox = RoundedRectangle(corner_radius=0.14, width=VW_X1 - VW_X0, height=VW_TOP - VW_BOT, stroke_color=TEAL_M, stroke_width=3) \
            .set_fill(fillc(TEAL_M), 1).move_to([VCX, (VW_TOP + VW_BOT) / 2, 0])
        vttl = T("the view: per shop", 22, TEAL_M).move_to([VCX, 2.5, 0])
        vhead = VGroup(*[T(h, 18, GREY_B).move_to([x, VH_Y, 0]) for h, x in zip(["shop", "count", "sum", "min"], VX)])
        self.v = {}
        for r, vals in enumerate([("M-0042", "3", "10,450", "300"), ("M-0007", "1", "4,000", "4,000")]):
            for c, s in enumerate(vals):
                self.v[(r, c)] = self.vtext(r, c, s)
        vrow = lambda r: VGroup(*[self.v[(r, c)] for c in range(4)])
        self.steps("A database can keep the same board. The receipts are a table of payments, in PostgreSQL, a free database "
                   "program.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(wbt, l1b, l2b, q2, ok1, refund)), ReplacementTransform(wb, vbox)], 0.9),
            "The receipts",
            (lambda: [FadeIn(tbox), FadeIn(ttl), FadeIn(thead), LaggedStart(*[FadeIn(r) for r in self.trows[:4]], lag_ratio=0.15),
                      *self.cap("the receipts = a table of payments", BLUE_M)], 1.0),
        ])
        self.steps("The board is a stored answer to a question people keep asking: for each shop, how many payments, their total, "
                   "and the smallest. A stored answer like that is called a materialized view.", [
            "The board is",
            (lambda: [FadeIn(vttl), FadeIn(vhead)], 0.5),
            "for each shop",
            (lambda: [FadeIn(vrow(0)), FadeIn(vrow(1))], 0.6),
            "how many payments",
            (lambda: [glow(vbox, TEAL_M, 1.02)], 0.6),
            "a materialized view",
            (lambda: self.cap("the whiteboard = a stored answer, called a materialized view", TEAL_M), 0.6),
        ])
        sweep = Rectangle(width=TB_X1 - TB_X0 - 0.2, height=0.42, stroke_color=YELLOW_M, stroke_width=3).move_to([(TB_X0 + TB_X1) / 2, TY[0], 0]).set_z_index(4)
        self.steps("The plain way to keep it right is a refresh: work the whole answer out again. In the lesson, that read a million "
                   "payments to change one number.", [
            "a refresh",
            (lambda: [Create(sweep)], 0.3),
            (lambda: [Succession(*[sweep.animate(run_time=0.3).move_to([(TB_X0 + TB_X1) / 2, TY[k], 0]) for k in range(1, 4)])], 0.9),
            (lambda: [FadeOut(sweep), *[Indicate(m, color=YELLOW_M) for m in self.v.values()]], 0.7),
            "In the lesson",
            (lambda: self.cap("a refresh: a million payments read, to change one number", WHITE), 0.6),
        ])
        self.steps("It's counting the whole till after every sale. What we want is to change only what the new payment changes.", [
            "What we want",
            (lambda: self.cap("wanted: change only what the new payment changes", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("view")

        # ---------------- scene 3: an insert ----------------
        self.steps("Let's shrink it. Four payments, two shops. Shop M-0042 has 3 payments, 10,450 cents in all, and the smallest is 300.", [
            (lambda: [*self.uncap(), *self.count(0, 0)], 0.5),
            "Four payments",
            (lambda: [LaggedStart(*[Indicate(r, color=BLUE_M, scale_factor=1.05) for r in self.trows[:4]], lag_ratio=0.15)], 0.9),
            "Shop M-0042 has",
            (lambda: [*[Indicate(self.trows[k], color=YELLOW_M, scale_factor=1.05) for k in range(3)], Indicate(vrow(0), color=YELLOW_M, scale_factor=1.05)], 1.0),
        ])
        self.steps("Now a payment arrives: shop M-0042, 150.", [
            (lambda: self.change("INSERT payment 9: M-0042, 150"), 0.5),
            (lambda: [FadeIn(self.trows[4], shift=0.3 * DOWN)], 0.6),
        ])
        src = [TB_X1 - 0.1, TY[4], 0]
        self.steps("Watch the view. Count, plus 1. Sum, plus 150. Minimum, the smaller of 300 and 150: now 150.", [
            (lambda: [dot_run(src, [VW_X0 + 0.1, VRY[0], 0], YELLOW_M, 0.7)], 0.8),
            "Count, plus 1",
            (lambda: self.vset(0, 1, "4"), 0.5),
            "Sum, plus 150",
            (lambda: self.vset(0, 2, "10,600"), 0.5),
            "Minimum",
            (lambda: [*self.vset(0, 3, "150"), *self.delta("count + 1,   sum + 150,   min(300, 150) = 150")], 0.6),
        ])
        self.steps("All of it came from the new payment and the old view row. Not one row of the table was read.", [
            "Not one row",
            (lambda: [*self.count(0, 1), glow(tbox, GREY_B, 1.01)], 0.6),
        ])
        self.steps("A change to the input is called a delta, and the rule that turns it into a change to the answer is a delta rule. "
                   "It's the owner adding each sale to the board as it rings up.", [
            (lambda: self.cap("a delta: a change to the input", WHITE), 0.5),
            "a delta rule",
            (lambda: [*self.cap("a delta rule: how a delta changes the answer", YELLOW_M), Indicate(self.lab["delta"], color=YELLOW_M)], 0.7),
            "It's the owner",
            (lambda: self.cap("the owner adding each sale to the board as it rings up", WHITE), 0.6),
        ], after=0.3)
        self.stamp("insert")

        # ---------------- scene 4: a delete above the minimum ----------------
        self.steps("Now a refund deletes the 8,900. Deletes mirror inserts: count minus 1, sum minus 8,900.", [
            (lambda: [*self.uncap(), *self.whiten(), *self.change("DELETE payment 3: M-0042, 8,900")], 0.5),
            (lambda: self.strike(2), 0.6),
            "count minus 1",
            (lambda: self.vset(0, 1, "3"), 0.5),
            "sum minus",
            (lambda: self.vset(0, 2, "1,700"), 0.5),
        ])
        self.steps("And 8,900 was above the minimum, so the minimum can't have changed. Still nothing read.", [
            (lambda: [*self.delta("count - 1,   sum - 8,900;   8,900 > 150: min stays"), Indicate(self.v[(0, 3)], color=GREEN_M)], 0.7),
            "Still nothing",
            (lambda: self.count(0, 2), 0.5),
        ], after=0.3)

        # ---------------- scene 5: delete the minimum ----------------
        self.steps("So far so good. Now delete payment 9, the 150. That was the minimum. Count and sum are easy: 2 payments, 1,550.", [
            (lambda: [*self.whiten(), *self.change("DELETE payment 9: M-0042, 150")], 0.5),
            "Now delete",
            (lambda: self.strike(4), 0.6),
            "That was the minimum",
            (lambda: [Indicate(self.v[(0, 3)], color=RED_M, scale_factor=1.3)], 0.6),
            "Count and sum",
            (lambda: [*self.vset(0, 1, "2"), *self.vset(0, 2, "1,550"), *self.delta("count - 1,   sum - 150,   but 150 was the min", RED_M)], 0.6),
        ])
        self.steps("What's the new minimum? Pause and guess.", [
            (lambda: [*self.vset(0, 3, "?", RED_M), *self.cap("what's the new minimum?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("You can see it's 300, because the table is on screen. The view can't. It kept one number per shop, and the next "
                   "smallest was never in it.", [
            (lambda: [*self.uncap(), *[Indicate(self.trows[k], color=YELLOW_M, scale_factor=1.06) for k in (0, 1)]], 0.8),
            "The view can't",
            (lambda: [glow(vbox, RED_M, 1.02)], 0.7),
            "It kept one number",
            (lambda: self.cap("the view kept one number per shop; the next smallest was never in it", WHITE), 0.6),
        ])
        self.steps("That's the refunded tea. The board said 1.20, and nothing on it says what came second.", [
            (lambda: self.cap("the refunded tea: the board said 1.20, and nothing says what came second", GOLD_M), 0.6),
        ], after=0.3)
        self.stamp("break")

        # ---------------- scene 6: two ways out ----------------
        self.steps("There are two ways out. One: go back to the receipts, but only this shop's.", [
            (lambda: self.cap("way out 1: go back to the receipts, but only this shop's", GREEN_M), 0.6),
        ])
        self.steps("Through an index on the shop, a lookup that finds rows by shop, the view reads M-0042's two remaining payments "
                   "and takes the smaller: 300.", [
            "the view reads",
            (lambda: [*[Indicate(self.trows[k], color=GREEN_M, scale_factor=1.06) for k in (0, 1)],
                      LaggedStart(*[dot_run([TB_X1 - 0.1, TY[k], 0], [VX[3], VRY[0] - 0.05, 0], GREEN_M, 0.7) for k in (0, 1)], lag_ratio=0.4)], 1.1),
            "takes the smaller",
            (lambda: [*self.vset(0, 3, "300", GREEN_M), *self.delta("min(1,250, 300) = 300, read through an index", GREEN_M),
                      *self.count(2, 3)], 0.6),
        ])
        self.steps("That costs one shop's rows, not the whole table. pg_ivm, an add-on for PostgreSQL, works this way.", [
            (lambda: [Indicate(self.lab["cnt"], color=GREEN_M)], 0.7),
            "pg_ivm",
            (lambda: self.cap("pg_ivm, an add-on for PostgreSQL, rescans the one shop", WHITE), 0.6),
        ])
        tray = RoundedRectangle(corner_radius=0.12, width=VW_X1 - VW_X0, height=0.7, stroke_color=PURPLE_M, stroke_width=3) \
            .set_fill(fillc(PURPLE_M), 1).move_to([VCX, TRAY_Y, 0])
        trl = left_at(T("kept sorted:", 18, PURPLE_M), VW_X0 + 0.2, TRAY_Y)
        TRX = [2.35, 3.3, 4.4, 5.6]
        trv = [M(s, 20).move_to([x, TRAY_Y, 0]) for s, x in zip(["150", "300", "1,250", "8,900"], TRX)]
        trs = [Line([TRX[k] - trv[k].width / 2 - 0.06, TRAY_Y, 0], [TRX[k] + trv[k].width / 2 + 0.06, TRAY_Y, 0], stroke_width=3, color=RED_M) for k in (0, 3)]
        self.steps("The other way: store more. Keep every amount, sorted, for every shop, like a tray of receipts in order beside "
                   "the board.", [
            (lambda: [*self.whiten(), *self.cap("way out 2: store more", PURPLE_M)], 0.5),
            "Keep every amount",
            (lambda: [FadeIn(tray), FadeIn(trl), LaggedStart(*[FadeIn(t, shift=0.1 * RIGHT) for t in trv], lag_ratio=0.2)], 1.0),
            "like a tray",
            (lambda: [Create(trs[0]), Create(trs[1]), trv[0].animate.set_opacity(0.4), trv[3].animate.set_opacity(0.4)], 0.7),
        ])
        self.steps("The next smallest is always at hand, and you pay in memory instead. Streaming databases, which keep answers "
                   "updated as data flows in, take that road.", [
            (lambda: [Indicate(trv[1], color=PURPLE_M, scale_factor=1.4)], 0.8),
            "you pay in memory",
            (lambda: self.cap("the next smallest is at hand; the cost is memory for every shop", WHITE), 0.6),
            "Streaming databases",
            (lambda: self.cap("streaming databases keep answers updated as data flows in, and store more", WHITE), 0.6),
        ], after=0.3)
        self.stamp("waysout")

        # ---------------- scene 7: the last change, and the name ----------------
        self.steps("Last change: delete shop M-0007's only payment. Its count drops to 0, so its row leaves the view.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(tray, trl, *trv, *trs)), *self.change("DELETE payment 4: M-0007, 4,000")], 0.6),
            (lambda: self.strike(3), 0.6),
            "Its count drops",
            (lambda: [*self.vset(1, 1, "0", RED_M), *self.delta("count reaches 0: delete the view row")], 0.6),
            "its row leaves",
            (lambda: [FadeOut(vrow(1), shift=0.2 * RIGHT), *self.count(2, 4)], 0.7),
        ])
        self.live = {0}
        self.steps("Four changes cost 2 table rows read and 4 view rows written. A refresh after each would have read the whole "
                   "table four times.", [
            (lambda: [Indicate(self.lab["cnt"], color=YELLOW_M)], 0.8),
            "A refresh after each",
            (lambda: self.cap("a refresh after each change: the whole table read, four times", WHITE), 0.6),
        ])
        self.steps("Keeping a stored answer right one change at a time is called incremental view maintenance.", [
            "incremental view maintenance",
            (lambda: self.cap("incremental view maintenance: keep the stored answer right, one change at a time", YELLOW_M), 0.7),
        ], after=0.3)
        self.stamp("ivm")

        # ---------------- scene 8: when deltas lose ----------------
        LBX, B0, BMAX = -0.95, -0.75, 5.6

        def pair(a, b, la, lb, ca, cb):
            ya, yb = BAR1_Y, BAR2_Y
            return VGroup(right_at(T(la, 20), LBX, ya), bar(B0, ya, BMAX * a, ca), right_at(T(lb, 20), LBX, yb), bar(B0, yb, BMAX * b, cb))

        p1 = pair(1402 / 20_200_500, 1.0, "by deltas: 1,402 rows", "a refresh after each: 20 million rows", GREEN_M, RED_M)
        p2 = pair(1.0, 2200 / 35994, "by deltas: 35,994 rows", "one refresh at the end: 2,200 rows", RED_M, GREEN_M)
        self.steps("So should every view work by deltas? Not always. In the lesson's lab, 1,000 small changes to 20,000 payments "
                   "cost 1,402 rows of work as deltas, against 20 million for a refresh after each one.", [
            (lambda: [*self.cap("should every view work by deltas?", WHITE), *self.drop("delta", "chip")], 0.6),
            "1,000 small changes",
            (lambda: [*self.cap("1,000 small changes to 20,000 payments", WHITE), FadeIn(p1[0]), GrowFromEdge(p1[1], LEFT)], 0.8),
            "against 20 million",
            (lambda: [FadeIn(p1[2]), GrowFromEdge(p1[3], LEFT)], 0.8),
        ])
        self.steps("But a batch that deleted 90% of the table cost 35,994 rows as deltas, against 2,200 for one refresh at the end.", [
            (lambda: [*self.cap("a batch that deletes 90% of the table", WHITE), FadeOut(p1)], 0.4),
            "cost 35,994",
            (lambda: [FadeIn(p2[0]), GrowFromEdge(p2[1], LEFT)], 0.7),
            "against 2,200",
            (lambda: [FadeIn(p2[2]), GrowFromEdge(p2[3], LEFT)], 0.6),
        ])
        self.steps("Most of it went on rescanning shops whose minimum had just been deleted. Deltas are good with small change. "
                   "When a batch rewrites most of the data, work it out again.", [
            (lambda: [glow(p2[1], RED_M, 1.03), *self.cap("most of it: rescans of shops whose minimum was just deleted", WHITE)], 0.7),
            "Deltas are good",
            (lambda: self.cap("deltas win when changes are few; when a batch rewrites most of the data, work it out again", YELLOW_M), 0.7),
        ], after=0.3)
        self.stamp("guardrail")

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, what should the second line say? The board can't tell without the receipts.", [
            (lambda: [FadeOut(p2), *self.cap("what should the second line say?", WHITE)], 0.6),
            "can't tell",
            (lambda: self.cap("the board can't tell without the receipts", GOLD_M), 0.6),
        ])
        self.steps("Counts and sums can be added and taken back, one change at a time. The smallest can be added to, but not taken "
                   "back, unless you look again or kept more.", [
            (lambda: [*self.cap("counts and sums: add, and take back", GREEN_M), Indicate(self.v[(0, 1)], color=GREEN_M),
                      Indicate(self.v[(0, 2)], color=GREEN_M)], 0.7),
            "The smallest",
            (lambda: [*self.cap("the smallest: add to, but not take back, unless you look again or kept more", YELLOW_M),
                      Indicate(self.v[(0, 3)], color=YELLOW_M)], 0.7),
        ], after=0.3)
        self.steps("One quick check. Shop M-0042 has two payments left, 1,250 and 300. A refund deletes the 1,250. Does the view "
                   "need to read the table? Pause and think.", [
            (lambda: [*self.uncap(), *self.whiten()], 0.4),
            "two payments left",
            (lambda: [*[Indicate(self.trows[k], color=YELLOW_M, scale_factor=1.06) for k in (0, 1)]], 0.7),
            "A refund deletes",
            (lambda: self.change("DELETE payment 1: M-0042, 1,250"), 0.5),
            "Pause and think",
            (lambda: self.cap("does the view need to read the table?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. 1,250 is above the minimum, so the minimum stays 300. Only deleting the minimum sends you back to the receipts.", [
            (lambda: [*self.uncap(), *self.strike(0)], 0.5),
            (lambda: [*self.vset(0, 1, "1"), *self.vset(0, 2, "300"), *self.delta("count - 1,   sum - 1,250;   1,250 > 300: min stays", GREEN_M),
                      *self.count(2, 5)], 0.6),
            "Only deleting",
            (lambda: self.cap("only deleting the minimum sends you back to the receipts", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("counts and sums take back a change; the smallest needs the receipts", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
