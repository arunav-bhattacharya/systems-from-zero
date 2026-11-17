from sfz import *

SAY.insert(0, (r"\bwork_mem\b", "work mem"))
SAY.insert(0, (r"\bEXPLAIN\b", "explain"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ROW_Y = [1.75, 0.85, -0.05, -0.95]
TITLE_Y = 2.65
TX, TW, TH = -4.35, 4.0, 0.62            # the tickets: the shops, the smaller input
GX, GW, GH = 4.85, 2.75, 0.62            # the guests: the payments
RX0, RX1 = -1.5, 1.75                    # the rack of pigeonholes, one per row
RCX = (RX0 + RX1) / 2
FILE_X, CMP_X = -1.4, 1.1              # inside a pigeonhole: the filed ticket, then the comparison
OUT_Y = -1.95
OUT_X = [-4.3, 0.0, 4.3]
CAP_Y = -3.25

SHOPS = [(1, "Northwind Grocers", "Northwind"), (2, "Blue Fern Cafe", "Blue"), (3, "Metro Transit", "Metro"), (4, "Volt Electronics", "Volt")]
GUESTS = [(1, 1), (2, 2), (3, 4), (5, 5)]            # payment, its shop (the lesson's stepper)
BUCKETS = [1, 2, 3, 0]                                  # top to bottom, as in the stepper


def brow(b):
    return BUCKETS.index(b)


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
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, c=(0, -2.55), secs=3.0):
        bar = Line([c[0] - 1.0, c[1], 0], [c[0] + 1.0, c[1], 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def ticket(k):
    n, name, _ = SHOPS[k]
    y = ROW_Y[k]
    r = RoundedRectangle(corner_radius=0.12, width=TW, height=TH, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1).move_to([TX, y, 0])
    hole = Circle(radius=0.07, stroke_color=GOLD_M, stroke_width=2).set_fill(BLACK, 1).move_to([TX - TW / 2 + 0.22, y, 0])
    num = M(str(n), 20, GOLD_M).move_to([TX - TW / 2 + 0.55, y, 0])
    nm = left_at(M(name, 20), TX - TW / 2 + 0.85, y)
    return VGroup(r, hole, num, nm)


def guest(k, label=None, mer=None, color=BLUE_M, y=None):
    p, m = GUESTS[k] if k is not None else (None, mer)
    y = ROW_Y[k] if y is None else y
    a = M(label or f"payment {p} · ", 20)
    b = M(f"m{m}", 20, YELLOW_M)
    t = VGroup(a, b).arrange(RIGHT, buff=0.16)
    r = RoundedRectangle(corner_radius=0.12, width=GW, height=GH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    g = VGroup(r, t.move_to(r))
    return g.move_to([GX, y, 0])


def rack():
    top, bot = ROW_Y[0] + 0.45, ROW_Y[3] - 0.45
    body = Rectangle(width=RX1 - RX0, height=top - bot, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M, 0.08), 1)
    body.move_to([RCX, (top + bot) / 2, 0]).set_z_index(-1)
    seps = VGroup(*[Line([RX0, (ROW_Y[i] + ROW_Y[i + 1]) / 2, 0], [RX1, (ROW_Y[i] + ROW_Y[i + 1]) / 2, 0], stroke_width=2.5, color=TEAL_M)
                    for i in range(3)])
    nums = VGroup(*[M(str(b), 24, TEAL_M).move_to([RX0 - 0.3, ROW_Y[i], 0]) for i, b in enumerate(BUCKETS)])
    return body, seps, nums


def filed(k):
    n, _, short = SHOPS[k]
    t = M(f"{n} {short}", 16)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.28, height=0.44, stroke_color=GOLD_M, stroke_width=2).set_fill(fillc(GOLD_M), 1)
    g = VGroup(r, t.move_to(r))
    return left_at(g, FILE_X, ROW_Y[brow(n % 4)])


def cmp_label(row, s, color):
    return M(s, 18, color).move_to([CMP_X, ROW_Y[row], 0])


def out_chip(k, s):
    t = M(s, 18, GREEN_M)
    r = RoundedRectangle(corner_radius=0.1, width=t.width + 0.35, height=0.5, stroke_color=GREEN_M, stroke_width=2).set_fill(fillc(GREEN_M), 1)
    return VGroup(r, t.move_to(r)).move_to([OUT_X[k], OUT_Y, 0])


def probe_arrow(gy, row, color=YELLOW_M):
    return Arrow([GX - GW / 2 - 0.08, gy, 0], [RX1 + 0.08, ROW_Y[row], 0], buff=0, stroke_width=3, color=color,
                 max_tip_length_to_length_ratio=0.12)


class HashJoin(Base):
    """sql-03, section 3. The loop is what a join means: payment 3 checks shops 1 to 4. On the large data set that's 0.44 s
    and 6.3 million comparisons for 10,000 payments, about 40 s for all. The party's cloakroom: a smart clerk files the
    tickets (the shops) into four pigeonholes by the remainder after dividing by 4, then sends each guest (a payment) to
    one pigeonhole. Payments 1, 2, 3 match; payment 5 lands in pigeonhole 1 beside Northwind and only the number check
    stops a wrong pair. Names, the real cost (174 ms, 67 ms), limits, the moral, and a check (shop 8)."""

    def construct(self):
        self.capm = None
        self.title_card("Does the database run the loop?", "how a hash join finds the pairs")

        # ---------------- scene 1: the loop, and its bill ----------------
        T_ = [ticket(k) for k in range(4)]
        G_ = [guest(k) for k in range(4)]
        t_l = T("merchants", 24, GREY_B).move_to([TX, TITLE_Y, 0])
        t_r = T("payments", 24, GREY_B).move_to([GX, TITLE_Y, 0])
        cw = M("0", 16).width
        code = VGroup(*[left_at(M(s, 16), -1.9 + ind * cw, 1.4 - 0.42 * i) for i, (ind, s) in enumerate(
            [(0, "for (p in payments)"), (2, "for (m in merchants)"), (4, "if (p.merchantId == m.merchantId)"), (6, "emit(p, m)")])])
        self.steps("A join pairs rows that match. Its meaning is a loop: for each payment, look at the shops, "
                   "and keep the pairs whose shop numbers are equal.", [
            (lambda: [FadeIn(t_l), LaggedStart(*[FadeIn(t, shift=0.1 * RIGHT) for t in T_], lag_ratio=0.2)], 1.0),
            (lambda: [FadeIn(t_r), LaggedStart(*[FadeIn(g, shift=0.1 * LEFT) for g in G_], lag_ratio=0.2)], 1.0),
            "Its meaning",
            (lambda: [FadeIn(code, shift=0.1 * UP)], 0.8),
            "keep the pairs",
            (lambda: [Indicate(code[2], color=YELLOW_M, scale_factor=1.05)], 0.9),
        ])
        out = [None, None, None]
        lines = []

        def check(k, ok):
            ln = Line([GX - GW / 2 - 0.08, ROW_Y[2], 0], [TX + TW / 2 + 0.08, ROW_Y[k], 0], stroke_width=3, color=YELLOW_M)
            lines.append(ln)
            return [
                (lambda: [Create(ln), *self.cap(f"comparisons: {k + 1}", WHITE)], 0.35),
                (lambda: [ln.animate.set_color(GREEN_M if ok else RED_M), glow(T_[k][0], GREEN_M if ok else RED_M, 1.03)], 0.45),
            ]

        def first_out():
            out[0] = out_chip(0, "(3, Volt Electronics)")
            return [FadeIn(out[0], shift=0.1 * DOWN)]

        self.steps("Payment 3 has shop 4. So it checks shop 1, shop 2, shop 3, and finds its match at the fourth. "
                   "Four comparisons, for one payment.", [
            (lambda: [FadeOut(code), glow(G_[2][0], YELLOW_M, 1.04)], 0.6),
            "So it checks",
            *check(0, False), *check(1, False), *check(2, False),
            "finds its match",
            *check(3, True),
            (lambda: first_out(), 0.5),
            "Four comparisons",
            (lambda: self.cap("4 comparisons for 1 payment", WHITE), 0.4),
        ])
        stats = VGroup(T("large data set: 1,000,000 payments, 2,500 shops", 24),
                       T("first 10,000 payments: 0.44 s, 6.3 million comparisons", 24),
                       T("all 1,000,000 payments: about 40 s", 24, RED_M)).arrange(DOWN, buff=0.16)
        stats.move_to([0, -2.2, 0])
        self.steps("With four shops, that's nothing. The course's large data set has a million payments and 2,500 shops. "
                   "With the faster methods switched off, PostgreSQL joined only the first 10,000 payments this way. "
                   "That took 0.44 seconds and 6.3 million comparisons. All million payments would take about 40 seconds.", [
            (lambda: [FadeOut(VGroup(*lines)), FadeOut(out[0]), *self.uncap()], 0.6),
            "The course's",
            (lambda: [FadeIn(stats[0], shift=0.1 * UP)], 0.6),
            "With the faster",
            (lambda: self.cap("faster methods switched off: brute force only"), 0.5),
            "That took",
            (lambda: [FadeIn(stats[1], shift=0.1 * UP)], 0.6),
            "All million",
            (lambda: [FadeIn(stats[2], shift=0.1 * UP), *self.uncap()], 0.6),
        ])
        self.steps("The answer must be what the loop produces. But does the database have to do all that work to get it?", [
            (lambda: self.cap("same answer as the loop, without all that work?", YELLOW_M), 0.5),
        ], after=0.4)

        # ---------------- scene 2: the cloakroom ----------------
        sweep = RoundedRectangle(corner_radius=0.1, width=TW + 0.2, height=TH + 0.16, stroke_color=YELLOW_M, stroke_width=4).move_to([TX, ROW_Y[0], 0])
        self.steps("Go back to the party's cloakroom. At the end of the night, a queue of guests wants their coats, "
                   "and the clerk has a box of tickets.", [
            (lambda: [FadeOut(stats), *self.cap("the party's cloakroom")], 0.6),
            "a queue of guests",
            (lambda: [LaggedStart(*[glow(g[0], BLUE_M, 1.04) for g in G_], lag_ratio=0.2)], 1.0),
            "a box of tickets",
            (lambda: [LaggedStart(*[glow(t[0], GOLD_M, 1.03) for t in T_], lag_ratio=0.2)], 1.0),
        ])

        def sweep_box():
            seq = [(lambda: [Create(sweep)], 0.25)]
            for i in range(1, 4):
                seq.append((lambda i=i: [sweep.animate.move_to([TX, ROW_Y[i], 0])], 0.22))
            seq.append((lambda: [FadeOut(sweep), sweep.animate.move_to([TX, ROW_Y[0], 0])], 0.2))
            return seq

        self.steps("A slow clerk reads the whole box for every guest. By the hundredth guest, the queue reaches the car park.", [
            (lambda: self.cap("the slow clerk: the whole box, for every guest"), 0.4),
            (lambda: [glow(G_[0][0], YELLOW_M, 1.04)], 0.4),
            *sweep_box(),
            (lambda: [glow(G_[1][0], YELLOW_M, 1.04)], 0.4),
            *sweep_box(),
            "By the hundredth",
            (lambda: self.cap("guest 100: the queue reaches the car park"), 0.4),
        ])
        body, seps, nums = rack()
        t_m = T("pigeonholes", 24, TEAL_M).move_to([RCX, TITLE_Y, 0])
        self.steps("A smart clerk does some work before the doors open. She files each ticket into one of four pigeonholes, "
                   "by one rule: the remainder when you divide its number by 4.", [
            (lambda: self.uncap(), 0.3),
            "She files",
            (lambda: [FadeIn(body), Create(seps), FadeIn(t_m)], 0.9),
            (lambda: [LaggedStart(*[FadeIn(n, scale=0.6) for n in nums], lag_ratio=0.2)], 0.8),
            "by one rule",
            (lambda: self.cap("the rule: the remainder after dividing the number by 4", TEAL_M), 0.5),
        ])
        self.steps("Then each guest's number points to one pigeonhole, and she looks only there.", [
            "points to one",
            (lambda: [Indicate(nums[1], color=YELLOW_M, scale_factor=1.5)], 0.8),
        ])
        t_l2 = T("merchants: the tickets", 24, GOLD_M).move_to([TX, TITLE_Y, 0])
        t_r2 = T("payments: the guests", 24, BLUE_M).move_to([GX, TITLE_Y, 0])
        self.steps("Let's map it. The tickets are the shops, the smaller input. The guests in the queue are the payments. "
                   "And the number each one holds is the shop number.", [
            (lambda: self.uncap(), 0.3),
            "The tickets are",
            (lambda: [swap(t_l, t_l2)], 0.6),
            "The guests in",
            (lambda: [swap(t_r, t_r2)], 0.6),
            "And the number",
            (lambda: [*[Indicate(t[2], color=GOLD_M, scale_factor=1.4) for t in T_], *[Indicate(g[1][1], color=YELLOW_M, scale_factor=1.3) for g in G_],
                      *self.cap("the number each one holds: the shop number", WHITE)], 1.0),
        ])

        # ---------------- scene 3: filing the tickets ----------------
        F_ = [filed(k) for k in range(4)]

        def file(k):
            n = SHOPS[k][0]
            r = n % 4
            rem = "nothing" if r == 0 else str(r)
            return [(lambda: [*self.cap(f"shop {n}: {n} divided by 4 leaves {rem}, so pigeonhole {r}", WHITE),
                              ReplacementTransform(T_[k].copy(), F_[k])], 0.8)]

        self.steps("Let's file our four shops. Shop 1: 1 divided by 4 leaves 1, so pigeonhole 1. Shop 2 goes in 2, and shop 3 in 3. "
                   "And shop 4? 4 divided by 4 leaves nothing, so pigeonhole 0.", [
            "Shop 1",
            *file(0),
            "Shop 2",
            *file(1),
            "and shop 3",
            *file(2),
            "And shop 4",
            (lambda: [glow(T_[3][0], GOLD_M, 1.03)], 0.5),
            "4 divided",
            *file(3),
        ])
        self.steps("That's the first phase. The shops are read once, and never again.", [
            (lambda: self.cap("phase one: file the shops, once"), 0.5),
            "never again",
            (lambda: [*[t.animate.set_opacity(0.3) for t in T_], t_l2.animate.set_opacity(0.5)], 0.8),
        ])

        # ---------------- scene 4: one look per guest ----------------
        def probe(k, ok_text, keep=False):
            p, m = GUESTS[k]
            row = brow(m % 4)
            ar = probe_arrow(ROW_Y[k], row)
            lab = cmp_label(row, ok_text, GREEN_M)
            return ar, lab

        a1, l1 = probe(0, "1 = 1")
        o1 = out_chip(0, "(1, Northwind Grocers)")
        self.steps("Now the payments, one at a time. Payment 1 has shop 1: pigeonhole 1, compare the number, a match. "
                   "Out comes one row, and it never looked at shops 2, 3 or 4.", [
            (lambda: self.cap("phase two: each payment, one at a time"), 0.5),
            "Payment 1 has",
            (lambda: [glow(G_[0][0], YELLOW_M, 1.04)], 0.5),
            "pigeonhole 1",
            (lambda: [GrowArrow(a1)], 0.5),
            "compare the number",
            (lambda: [FadeIn(l1, scale=0.7)], 0.4),
            "Out comes",
            (lambda: [FadeIn(o1, shift=0.1 * DOWN)], 0.5),
            "it never looked",
            (lambda: [*[Indicate(f, color=GREY_B, scale_factor=1.0) for f in F_[1:]], *self.cap("shops 2, 3 and 4: never looked at")], 0.8),
        ])
        a2, l2 = probe(1, "2 = 2")
        o2 = out_chip(1, "(2, Blue Fern Cafe)")
        self.steps("Payment 2 goes to pigeonhole 2, the same way.", [
            (lambda: [FadeOut(a1), FadeOut(l1), *self.uncap(), glow(G_[1][0], YELLOW_M, 1.04)], 0.4),
            (lambda: [GrowArrow(a2)], 0.4),
            (lambda: [FadeIn(l2, scale=0.7)], 0.3),
            (lambda: [FadeIn(o2, shift=0.1 * DOWN)], 0.4),
        ])
        self.steps("Payment 3 has shop 4. Which pigeonhole? Pause and guess.", [
            (lambda: [FadeOut(a2), FadeOut(l2), glow(G_[2][0], YELLOW_M, 1.04)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        a3, l3 = probe(2, "4 = 4")
        o3 = out_chip(2, "(3, Volt Electronics)")
        self.steps("Pigeonhole 0. One look, one comparison, and there's Volt Electronics.", [
            (lambda: [*self.uncap(), GrowArrow(a3)], 0.5),
            (lambda: [Indicate(nums[3], color=YELLOW_M, scale_factor=1.5)], 0.6),
            "one comparison",
            (lambda: [FadeIn(l3, scale=0.7)], 0.4),
            "and there's",
            (lambda: [FadeIn(o3, shift=0.1 * DOWN)], 0.5),
        ])

        # ---------------- scene 5: the pigeonhole is a shortlist ----------------
        a5 = probe_arrow(ROW_Y[3], brow(1))
        self.steps("Now payment 5. It has shop 5, which isn't among our four. 5 divided by 4 leaves 1, "
                   "so it lands in pigeonhole 1, next to Northwind Grocers.", [
            (lambda: [FadeOut(a3), FadeOut(l3), glow(G_[3][0], YELLOW_M, 1.04)], 0.5),
            "which isn't among",
            (lambda: [*[glow(t[0], GREY_B, 1.02) for t in T_]], 0.7),
            "5 divided by 4",
            (lambda: self.cap("5 divided by 4 leaves 1: pigeonhole 1", WHITE), 0.5),
            "so it lands",
            (lambda: [GrowArrow(a5)], 0.6),
            "next to Northwind",
            (lambda: [glow(F_[0][0], GOLD_M, 1.06)], 0.7),
        ])
        l5 = cmp_label(0, "1 ≠ 5", RED_M)
        self.steps("If the pigeonhole were enough, payment 5 would be paired with Northwind. Wrong shop.", [
            (lambda: self.cap("(5, Northwind Grocers)? the wrong shop", PURPLE_M), 0.5),
            "Wrong shop",
            (lambda: [glow(F_[0][0], PURPLE_M, 1.08)], 0.6),
        ])
        self.steps("So the clerk always checks the number on the ticket: 1 isn't 5, no match, and an inner join puts out nothing. "
                   "The pigeonhole gives a shortlist. The number on the ticket decides.", [
            (lambda: self.uncap(), 0.3),
            "1 isn't 5",
            (lambda: [FadeIn(l5, scale=0.7), a5.animate.set_color(RED_M)], 0.5),
            (lambda: [Indicate(l5, color=RED_M, scale_factor=1.3)], 0.5),
            "puts out nothing",
            (lambda: self.cap("no match: an inner join puts out no row"), 0.5),
            "The pigeonhole gives",
            (lambda: self.cap("the pigeonhole gives a shortlist; the number on the ticket decides", GOLD_M), 0.5),
        ], after=0.4)

        # ---------------- scene 6: names ----------------
        t_m2 = T("hash table: id mod 4", 24, TEAL_M).move_to([RCX, TITLE_Y, 0])
        t_l3 = T("merchants (build)", 24, GOLD_M).move_to([TX, TITLE_Y, 0])
        t_r3 = T("payments (probe)", 24, BLUE_M).move_to([GX, TITLE_Y, 0])
        self.steps("Now the names. The filing rule is a hash function: it turns a key into a bucket number. "
                   "The rack is a hash table, and each pigeonhole is a bucket. Filing the smaller input is the build. "
                   "Looking up each payment is the probe. Together, that's a hash join.", [
            (lambda: [FadeOut(VGroup(a5, l5)), *self.uncap(), *[t.animate.set_opacity(1) for t in T_], t_l2.animate.set_opacity(1)], 0.6),
            "a hash function",
            (lambda: self.cap("hash function: turns a key into a bucket number", TEAL_M), 0.5),
            "The rack is",
            (lambda: [swap(t_m, t_m2), glow(body, TEAL_M, 1.0)], 0.7),
            "each pigeonhole",
            (lambda: [LaggedStart(*[Indicate(n, color=TEAL_M, scale_factor=1.4) for n in nums], lag_ratio=0.2), *self.cap("each pigeonhole: a bucket", TEAL_M)], 0.9),
            "Filing the smaller",
            (lambda: [swap(t_l2, t_l3)], 0.6),
            "Looking up",
            (lambda: [swap(t_r2, t_r3)], 0.6),
            "Together",
            (lambda: self.cap("build once, probe once per row: a hash join", WHITE, 28), 0.5),
        ])

        # ---------------- scene 7: what it costs ----------------
        BX0, BY1, BY2 = -3.9, -1.85, -2.5
        unit = 8.4 / 40.0
        lab1 = T("the loop", 22, GREY_B).move_to([-5.3, BY1, 0])
        lab2 = T("hash join", 22, GREY_B).move_to([-5.3, BY2, 0])
        bar1 = Rectangle(width=40 * unit, height=0.36, stroke_width=0).set_fill(RED_M, 0.85)
        left_at(bar1, BX0, BY1)
        bar2 = Rectangle(width=max(0.05, 0.174 * unit), height=0.36, stroke_width=0).set_fill(GREEN_M, 1)
        left_at(bar2, BX0, BY2)
        v1 = T("about 40 s", 22, RED_M).next_to(bar1, RIGHT, buff=0.15)
        v2 = T("0.174 s on one core, 0.067 s with two workers", 22, GREEN_M).next_to(bar2, RIGHT, buff=0.15)
        self.steps("On the large data set, the hash table held all 2,500 shops in about 130 kilobytes. "
                   "Then one pass over the million payments: 174 milliseconds on one core, and 67 with two workers sharing it. "
                   "The loop needed about 40 seconds.", [
            (lambda: [FadeOut(VGroup(o1, o2, o3)), *self.cap("2,500 shops in the hash table: about 130 kB", TEAL_M), glow(body, TEAL_M, 1.0)], 0.8),
            "Then one pass",
            (lambda: [*self.uncap(), LaggedStart(*[glow(g[0], BLUE_M, 1.04) for g in G_], lag_ratio=0.15)], 0.9),
            "174 milliseconds",
            (lambda: [FadeIn(lab2), GrowFromEdge(bar2, LEFT), FadeIn(v2, shift=0.1 * LEFT)], 0.7),
            "The loop needed",
            (lambda: [FadeIn(lab1), GrowFromEdge(bar1, LEFT)], 1.2),
            (lambda: [FadeIn(v1, shift=0.1 * LEFT)], 0.4),
        ], after=0.4)

        # ---------------- scene 8: limits ----------------
        self.steps("Three limits. Pigeonholes can only answer one question: is it equal? So a hash join needs an equals sign "
                   "in the join condition.", [
            (lambda: [FadeOut(VGroup(lab1, lab2, bar1, bar2, v1, v2)), *self.cap("1. only for =  (shop number = shop number)", WHITE)], 0.7),
            "is it equal",
            (lambda: [LaggedStart(*[Indicate(n, color=WHITE, scale_factor=1.4) for n in nums], lag_ratio=0.15)], 0.9),
        ])
        self.steps("The rack has to fit in the memory the work_mem setting allows, 4 megabytes by default, "
                   "or PostgreSQL splits the work into batches on disk.", [
            (lambda: [*self.cap("2. the hash table must fit in work_mem (4 MB by default), or it works in batches on disk", WHITE),
                      glow(body, TEAL_M, 1.0)], 0.8),
        ])
        self.steps("And there are other fast ways, such as looking each shop up in an index, a sorted catalogue. "
                   "The planner, the part of PostgreSQL that decides how to run a query, estimates the cost of each, "
                   "and EXPLAIN shows its choice.", [
            (lambda: self.cap("3. other ways: a nested loop with an index, a merge join", WHITE), 0.6),
            "The planner",
            (lambda: self.cap("the planner estimates each cost and picks; EXPLAIN shows the plan", WHITE), 0.6),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, does the database run the loop? The loop says what a join means. The planner decides how to run it. "
                   "File the small side once, and send each row of the big side to one bucket.", [
            (lambda: self.cap("does the database run the loop?", WHITE), 0.5),
            "The loop says",
            (lambda: self.cap("the loop says what a join means; the planner decides how to run it", YELLOW_M, 28), 0.6),
            "File the small",
            (lambda: [LaggedStart(*[glow(t[0], GOLD_M, 1.03) for t in T_], lag_ratio=0.15)], 0.8),
            "and send each",
            (lambda: [LaggedStart(*[glow(g[0], BLUE_M, 1.04) for g in G_], lag_ratio=0.15)], 0.8),
        ], after=0.5)
        g8 = guest(None, "a payment · ", 8, YELLOW_M, OUT_Y)
        self.steps("One quick check. A payment for shop 8 arrives. Which pigeonhole, and what comes out? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "A payment for",
            (lambda: [FadeIn(g8, shift=0.15 * UP)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(c=(-1.5, -2.55))
        a8 = Arrow([GX - GW / 2 - 0.08, OUT_Y, 0], [RX1 + 0.08, ROW_Y[brow(0)], 0], buff=0, stroke_width=3, color=YELLOW_M,
                   max_tip_length_to_length_ratio=0.12)
        l8 = cmp_label(brow(0), "4 ≠ 8", RED_M)
        self.steps("8 divided by 4 leaves 0: pigeonhole 0, where Volt sits. 4 isn't 8, so nothing comes out.", [
            (lambda: [*self.uncap(), GrowArrow(a8)], 0.6),
            (lambda: [Indicate(nums[3], color=YELLOW_M, scale_factor=1.5)], 0.6),
            "4 isn't 8",
            (lambda: [FadeIn(l8, scale=0.7), a8.animate.set_color(RED_M)], 0.5),
            (lambda: [Indicate(l8, color=RED_M, scale_factor=1.3)], 0.5),
        ], after=0.3)
        self.play(*self.cap("the loop says what a join means; the planner decides how to run it", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
