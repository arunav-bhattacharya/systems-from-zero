from sfz import *

# Amounts are said the way people say them; captions keep "500.00". Header fields are said as letters.
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bx-min\b", "ex min"))
SAY.insert(0, (r"\bx-max\b", "ex max"))
SAY.insert(0, (r"\bVACUUM\b", "vacuum"))
SAY.insert(0, (r"\b18:00\b", "six p m"))
SAY.insert(0, (r"\b8 KB\b", "8 kilobytes"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
STRIP_Y, CELL_W, CELL_H = 2.4, 1.9, 0.95
WALLETS = ["wallet 1", "wallet 2", "wallet 7", "...", "wallet 1,800,000", "wallet 2,000,000"]
CELL_X = [-5.25 + i * 2.1 for i in range(6)]
SLOT_X, SLOT_Y, SLOT_W, SLOT_H = 3.0, 0.45, 4.6, 1.55     # the two versions of wallet 7, left and right
RD_Y = -1.75                                             # the readers
CAP_Y, BAR_Y = -3.25, -2.85


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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

    def steps(self, text, items, after=0.3):
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


# ---- the pieces ----
def cell(i):
    r = RoundedRectangle(corner_radius=0.1, width=CELL_W, height=CELL_H, stroke_color=BLUE_M, stroke_width=2.5)
    r.set_fill(fillc(BLUE_M), 1).move_to([CELL_X[i], STRIP_Y, 0])
    if WALLETS[i] == "...":
        r.set_stroke(opacity=0).set_fill(opacity=0)
        return VGroup(r, T("...", 26, GREY_B).move_to(r))
    return VGroup(r, fit(T(WALLETS[i], 18), CELL_W - 0.3).move_to(r.get_center() + [0, 0.2, 0]))


def cell_val(i, s, color=WHITE):
    return M(s, 20, color).move_to([CELL_X[i], STRIP_Y - 0.2, 0])


def cursor(i):
    return RoundedRectangle(corner_radius=0.12, width=CELL_W + 0.16, height=CELL_H + 0.16, stroke_color=YELLOW_M,
                            stroke_width=4).move_to([CELL_X[i], STRIP_Y, 0])


def padlock(color, at, s=1.0):
    body = RoundedRectangle(corner_radius=0.06, width=0.46, height=0.36, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.5), 1)
    shackle = Arc(radius=0.15, start_angle=0, angle=PI, stroke_color=color, stroke_width=4)
    shackle.next_to(body, UP, buff=0)
    legs = VGroup(Line(shackle.get_start(), shackle.get_start() + 0.04 * DOWN), Line(shackle.get_end(), shackle.get_end() + 0.04 * DOWN)).set_stroke(color, 4)
    return VGroup(shackle, legs, body).scale(s).move_to(at)


def slot_box(x, color, title, mid, low):
    r = RoundedRectangle(corner_radius=0.14, width=SLOT_W, height=SLOT_H, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, SLOT_Y, 0])
    a = T(title, 24, color).move_to(r.get_center() + [0, 0.45, 0])
    b = M(mid, 20).move_to(r.get_center() + [0, -0.05, 0])
    c = T(low, 18, GREY_B).move_to(r.get_center() + [0, -0.48, 0])
    return VGroup(r, a, b, c)


def reader(x, l1, l2, color):
    t = VGroup(T(l1, 20, color), T(l2, 18, GREY_B)).arrange(DOWN, buff=0.1)
    r = RoundedRectangle(corner_radius=0.12, width=max(4.2, t.width + 0.5), height=t.height + 0.35, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.1), 1)
    return VGroup(r, t.move_to(r)).move_to([x, RD_Y, 0])


def up_arrow(x, color):
    return Arrow([x, RD_Y + 0.5, 0], [x, SLOT_Y - SLOT_H / 2 - 0.08, 0], buff=0, stroke_width=3, color=color,
                 max_tip_length_to_length_ratio=0.2)


def tiny_slot(k, wallet, val, xmin, xmax, color=WHITE, dim=False):
    x = -4.8 + k * 3.2
    r = RoundedRectangle(corner_radius=0.1, width=2.9, height=1.6, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.1), 1)
    r.move_to([x, 0.35, 0])
    g = VGroup(T(f"slot {k + 1}: {wallet}", 20, color), M(val, 20), M(f"xmin {xmin}  xmax {xmax}", 15, GREY_B)).arrange(DOWN, buff=0.14)
    out = VGroup(r, g.move_to(r))
    if dim:
        out.set_opacity(0.55)
    return out


class Mvcc(Base):
    """txn-04, section 0. A month-end report adds up 2 million wallets in 30 seconds while 300 transfers a second move
    money. One copy per row: lock (9,000 transfers queue) or no lock (250.00 moved from wallet 7 to wallet 1,800,000
    counted twice). The notebook where nothing is rubbed out, a reader who started at 18:00. In PostgreSQL: tuples with
    t_xmin and t_xmax; transaction 860 stamps slot 1 (500.00) and writes slot 2 (250.00); the report's snapshot reads
    slot 1. MVCC; an UPDATE is a delete plus an insert (the Try it: four tuples for three rows). Costs, where the
    notebook breaks, moral, and a check (860 rolls back)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
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

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Counting while people pay", "keep the old row, and nobody has to wait")

        # ---------------- scene 1: the question ----------------
        cells = VGroup(*[cell(i) for i in range(6)])
        cur = cursor(0)
        rep_lab = T("the report", 22, YELLOW_M).move_to([CELL_X[0], STRIP_Y + 0.82, 0])
        self.steps("Picture the coffee-shop payments app at the end of the month. A report adds up all 2 million customers' balances. "
                   "That takes 30 seconds.", [
            "A report",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * DOWN) for c in cells], lag_ratio=0.12)], 1.0),
            "adds up",
            (lambda: [Create(cur), FadeIn(rep_lab)], 0.5),
            "That takes",
            (lambda: [*self.put("sum", T("report: 2 million balances, 30 seconds", 24, YELLOW_M).move_to([0, 0.9, 0]))], 0.5),
        ])

        def flows(n=6):
            pairs = [(0, 1), (2, 4), (1, 5), (5, 0), (4, 2), (1, 2)][:n]
            out = []
            for a, b in pairs:
                p0 = np.array([CELL_X[a], STRIP_Y - CELL_H / 2 - 0.05, 0])
                p1 = np.array([CELL_X[b], STRIP_Y - CELL_H / 2 - 0.05, 0])
                path = ArcBetweenPoints(p0, p1, angle=0.9 if a < b else -0.9)
                d = Dot(radius=0.07, color=GOLD_M).move_to(p0)
                out.append(Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, run_time=0.8), FadeOut(d, run_time=0.1)))
            return [LaggedStart(*out, lag_ratio=0.25)]

        self.steps("Meanwhile, 300 times a second, a payment moves money from one balance to another. "
                   "No payment creates or destroys money, so the total must come out exact.", [
            (lambda: [*self.put("tx", T("payments: 300 transfers a second", 24, GOLD_M).move_to([0, 0.35, 0]))], 0.5),
            (lambda: flows(), 2.0),
            "so the total",
            (lambda: [*self.cap("the total must come out exact", WHITE)], 0.5),
        ])
        self.steps("It does. And not one payment waited for the report. Yet the report read rows that were changing under it. How?", [
            (lambda: [cur.animate.move_to(cursor(5)), rep_lab.animate.move_to([CELL_X[5], STRIP_Y + 0.82, 0])], 2.2),
            "Yet the report",
            (lambda: flows(4), 1.4),
            "How?",
            (lambda: self.cap("exact, and nobody waited. How?", YELLOW_M, 28), 0.5),
        ])

        # ---------------- scene 2: one copy per row ----------------
        self.steps("Let's start where most of us start. The balances sit in a table called wallets, one row per customer. "
                   "And we picture each row as one copy, which an update overwrites, like a variable.", [
            (lambda: [*self.uncap(), *self.drop("sum", "tx"), cur.animate.move_to(cursor(0)), rep_lab.animate.move_to([CELL_X[0], STRIP_Y + 0.82, 0])], 0.8),
            "one row per",
            (lambda: [*self.put("tbl", T("the wallets table: one row per customer", 22, BLUE_M).move_to([0, 1.25, 0]))], 0.5),
            "one copy",
            (lambda: [*self.put("v7", cell_val(2, "500.00"))], 0.4),
            "overwrites",
            (lambda: [*self.put("v7", cell_val(2, "250.00"))], 0.4),
            (lambda: [*self.put("v7", cell_val(2, "500.00"))], 0.4),
        ])
        big = padlock(YELLOW_M, [0, 0.35, 0], 1.6)
        queue = VGroup(*[Dot(radius=0.07, color=GOLD_M) for _ in range(24)]).arrange(RIGHT, buff=0.18).move_to([0, -0.75, 0])
        self.steps("With one copy, there are two choices. Choice one: the report locks the table, a mark that says wait until I'm done.", [
            "Choice one",
            (lambda: [FadeIn(big, scale=0.6), *self.cap("choice 1: lock the table", WHITE)], 0.6),
        ])
        self.steps("The total is right, and about 9,000 transfers queue for up to 30 seconds. Card readers give up long before that.", [
            (lambda: [LaggedStart(*[FadeIn(d, shift=0.3 * LEFT) for d in queue], lag_ratio=0.08)], 1.6),
            "about 9,000",
            (lambda: [*self.put("q", T("about 9,000 transfers waiting, up to 30 seconds", 22, RED_M).move_to([0, -1.35, 0]))], 0.5),
            "Card readers",
            (lambda: [queue.animate.set_color(RED_M)], 0.5),
        ])
        self.steps("Choice two: no lock. The report reads whatever each row holds when it gets there. "
                   "Watch wallet 7. The report has already counted its 500.00.", [
            (lambda: [FadeOut(big), FadeOut(queue), *self.drop("q", "tbl"), *self.cap("choice 2: no lock", WHITE)], 0.6),
            "Watch wallet 7",
            (lambda: [cur.animate.move_to(cursor(2)), rep_lab.animate.move_to([CELL_X[2], STRIP_Y + 0.82, 0])], 0.8),
            "already counted",
            (lambda: [*self.put("c1", T("counted: wallet 7, 500.00", 22, YELLOW_M).move_to([-3.2, 0.3, 0]))], 0.5),
        ])
        p0 = np.array([CELL_X[2], STRIP_Y - CELL_H / 2 - 0.05, 0])
        p1 = np.array([CELL_X[4], STRIP_Y - CELL_H / 2 - 0.05, 0])
        mv = ArcBetweenPoints(p0, p1, angle=0.8)
        coin = chip("250.00", GOLD_M, 20, mono=True)
        self.steps("Halfway through, a transfer moves 250.00 from wallet 7 to wallet 1,800,000. Then the report reaches wallet 1,800,000. "
                   "What goes wrong? Pause and guess.", [
            "a transfer moves",
            (lambda: [FadeIn(coin.move_to(p0 + 0.3 * DOWN))], 0.4),
            (lambda: [MoveAlongPath(coin, mv.copy().shift(0.3 * DOWN)), *self.put("v7", cell_val(2, "250.00"))], 1.2),
            (lambda: [FadeOut(coin), *self.put("v18", cell_val(4, "+250.00", GOLD_M))], 0.4),
            "Then the report",
            (lambda: [cur.animate.move_to(cursor(4)), rep_lab.animate.move_to([CELL_X[4], STRIP_Y + 0.82, 0])], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("That 250.00 is counted twice. Once in wallet 7, before it left, and once in wallet 1,800,000, after it arrived. "
                   "And the next run is wrong by a different amount.", [
            (lambda: [*self.uncap(), *self.put("c2", T("counted: wallet 1,800,000, with the 250.00", 22, YELLOW_M).move_to([3.0, -0.3, 0]))], 0.6),
            "counted twice",
            (lambda: [*self.cap("250.00 counted twice", RED_M, 30)], 0.5),
            "Once in wallet 7",
            (lambda: [Indicate(self.lab["c1"], color=RED_M)], 0.7),
            "and once in",
            (lambda: [Indicate(self.lab["c2"], color=RED_M)], 0.7),
        ])
        self.steps("Well... the report just invented 250.00. The auditors won't be impressed.", [
            0.4,
            (lambda: [Indicate(self.lab["v18"], color=GOLD_M)], 0.8),
        ], after=0.4)
        self.steps("So, wait and be right, or don't wait and be wrong. Neither is great. What we want is both: the report sees one moment, and nobody waits.", [
            "Neither is great",
            (lambda: [*self.drop("c1", "c2")], 0.5),
            "What we want",
            (lambda: self.cap("the wish: the report sees one moment, and nobody waits", GREEN_M, 26), 0.6),
        ])

        # ---------------- scene 3: the notebook ----------------
        nb = RoundedRectangle(corner_radius=0.14, width=8.4, height=2.9, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1)
        nb.move_to([0, -0.2, 0])
        nb_t = T("a notebook: nothing is ever rubbed out", 22, BLUE_M).move_to(nb.get_center() + [0, 1.05, 0])
        l1 = VGroup(M("17:50", 20, GREY_B), M("wallet 7: 500.00", 22), T("signed 850", 20, BLUE_M)).arrange(RIGHT, buff=0.6)
        l1.move_to(nb.get_center() + [0, 0.3, 0])
        l2 = VGroup(M("18:05", 20, GREY_B), M("wallet 7: 250.00", 22), T("signed 860", 20, GOLD_M)).arrange(RIGHT, buff=0.6)
        l2.move_to(nb.get_center() + [0, -0.45, 0])
        strike = Line(l1[1].get_left() + 0.1 * LEFT, l1[1].get_right() + 0.1 * RIGHT, stroke_width=3, color=GREY_B)
        rep_by = T("crossed out by 860", 18, GOLD_M).next_to(l1, DOWN, buff=0.08).align_to(l1[2], LEFT)
        self.steps("Picture a notebook where nothing is ever rubbed out. To change a balance, you cross out the old line, "
                   "write the new balance on a fresh line, and sign both.", [
            (lambda: [*self.uncap(), *self.drop("v7", "v18"), *[c.animate.set_opacity(0.25) for i, c in enumerate(cells) if i != 3], cells[3][1].animate.set_opacity(0.25), FadeOut(cur), FadeOut(rep_lab)], 0.6),
            "Picture a notebook",
            (lambda: [FadeIn(VGroup(nb, nb_t)), FadeIn(l1)], 0.7),
            "cross out",
            (lambda: [Create(strike)], 0.5),
            "write the new",
            (lambda: [FadeIn(l2, shift=0.1 * DOWN)], 0.6),
            "sign both",
            (lambda: [FadeIn(rep_by), Indicate(l2[2], color=GOLD_M)], 0.7),
        ])
        rd = chip("reader started at 18:00", YELLOW_M, 22).move_to([0, -2.25, 0])
        self.steps("Someone who started reading at 18:00 can skip every change made after 18:00. "
                   "They read the notebook as it stood when they began, while you keep writing.", [
            (lambda: [FadeIn(rd, shift=0.1 * UP)], 0.6),
            "can skip",
            (lambda: [l2.animate.set_opacity(0.25), rep_by.animate.set_opacity(0.25), strike.animate.set_opacity(0.25)], 0.6),
            "as it stood",
            (lambda: [Indicate(l1[1], color=YELLOW_M)], 0.8),
            "while you keep",
            (lambda: [l2.animate.set_opacity(1), rep_by.animate.set_opacity(1), strike.animate.set_opacity(1)], 0.5),
        ])
        self.steps("Map it. Each line is a version of the row. The signatures are transaction numbers. "
                   "And the reader's 18:00 is called a snapshot: a note of which transactions had finished when it started.", [
            "Each line",
            (lambda: [*self.cap("each line = a version of the row", WHITE)], 0.5),
            "The signatures",
            (lambda: [*self.cap("signatures = transaction numbers", WHITE), Indicate(l1[2], color=BLUE_M), Indicate(l2[2], color=GOLD_M)], 0.8),
            "called a snapshot",
            (lambda: [*self.cap("snapshot: which transactions had finished when the reader started", YELLOW_M), glow(rd[0], YELLOW_M, 1.04)], 0.8),
        ])

        # ---------------- scene 4: the real thing ----------------
        page_t = T("heap page 0 of the wallets table", 22, GREY_B).move_to([0, 1.75, 0])
        s1 = slot_box(-SLOT_X, WHITE, "slot 1: wallet 7", "balance 500.00", "t_xmin 850    t_xmax 0")
        self.steps("Now the real thing. PostgreSQL, a free database program, keeps a table in pages of 8 KB, "
                   "and each page holds stored row versions, called tuples, in numbered slots.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(nb, nb_t, l1, l2, strike, rep_by, rd)), FadeOut(cells)], 0.6),
            "keeps a table",
            (lambda: [FadeIn(page_t)], 0.5),
            "called tuples",
            (lambda: [FadeIn(s1[0]), FadeIn(s1[1])], 0.6),
        ])
        self.steps("Every tuple has a header with two numbers. x-min is the transaction that created this version. "
                   "x-max is the one that replaced it, or zero while nobody has.", [
            "two numbers",
            (lambda: [FadeIn(s1[3])], 0.5),
            "x-min is",
            (lambda: [*self.cap("t_xmin: who created this version", WHITE)], 0.5),
            "x-max is",
            (lambda: [*self.cap("t_xmax: who replaced it (0: nobody yet)", WHITE)], 0.5),
        ])
        s2 = slot_box(SLOT_X, GOLD_M, "slot 2: wallet 7", "balance 250.00", "t_xmin 860    t_xmax 0")
        s1b = T("t_xmin 850    t_xmax 860", 18, GOLD_M).move_to(s1[3])
        ptr = Arrow([-SLOT_X + SLOT_W / 2 + 0.08, SLOT_Y, 0], [SLOT_X - SLOT_W / 2 - 0.08, SLOT_Y, 0], buff=0, stroke_width=3,
                    color=GREY_B, max_tip_length_to_length_ratio=0.15)
        ptr_t = M("t_ctid", 18, GREY_B).next_to(ptr, UP, buff=0.1)
        self.steps("Wallet 7 sits in slot 1: 500.00, created by transaction 850. Then transaction 860 moves the 250.00. "
                   "It doesn't touch the 500. It stamps slot 1 with x-max 860, and writes a whole new version in slot 2: 250.00, x-min 860. "
                   "A pointer joins the two, oldest first.", [
            (lambda: [*self.uncap(), FadeIn(s1[2])], 0.5),
            "Then transaction 860",
            (lambda: [*self.cap("transaction 860: move 250.00 out of wallet 7", GOLD_M)], 0.5),
            "It stamps",
            (lambda: [Transform(s1[3], s1b)], 0.6),
            "writes a whole",
            (lambda: [FadeIn(s2, shift=0.2 * LEFT)], 0.8),
            "A pointer",
            (lambda: [GrowArrow(ptr), FadeIn(ptr_t)], 0.6),
        ])
        rA = reader(-SLOT_X, "the report", "snapshot taken while 860 was running", YELLOW_M)
        self.steps("The report's snapshot was taken while 860 was still running. Which version does it read? Pause and guess.", [
            (lambda: [*self.uncap(), FadeIn(rA, shift=0.1 * UP)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        aA = up_arrow(-SLOT_X, YELLOW_M)
        rB = reader(SLOT_X, "a query", "started after 860 committed", GREEN_M)
        aB = up_arrow(SLOT_X, GREEN_M)
        self.steps("Slot 1: 500.00. To its snapshot, 860 hasn't finished, so its stamp doesn't count yet. "
                   "A query that starts after 860 commits reads slot 2: 250.00. Same row, two readers, two answers, and nobody waited.", [
            (lambda: [*self.uncap(), GrowArrow(aA)], 0.5),
            (lambda: [glow(s1[0], YELLOW_M, 1.02)], 0.7),
            "so its stamp",
            (lambda: [Indicate(s1[3], color=YELLOW_M)], 0.8),
            "A query that",
            (lambda: [FadeIn(rB, shift=0.1 * UP)], 0.5),
            "reads slot 2",
            (lambda: [GrowArrow(aB), glow(s2[0], GREEN_M, 1.02)], 0.7),
            "nobody waited",
            (lambda: self.cap("same row, two readers, two answers, and nobody waited", WHITE), 0.5),
        ])
        self.steps("That's why the report's total is exact. Every wallet is read as it stood at one moment.", [
            (lambda: [*self.cap("every wallet as it stood at one moment: the total is exact", GREEN_M)], 0.6),
            "Every wallet",
            (lambda: [glow(rA[0], YELLOW_M, 1.03)], 0.8),
        ])

        # ---------------- scene 5: the name, and an update is not an overwrite ----------------
        self.steps("This design is called multi-version concurrency control, MVCC for short: keep several versions of each row, "
                   "so readers and writers can work at the same time.", [
            (lambda: [*self.cap("MVCC: multi-version concurrency control", BLUE_M, 30)], 0.6),
            "keep several",
            (lambda: [glow(s1[0], WHITE, 1.02), glow(s2[0], GOLD_M, 1.02)], 0.8),
            "so readers",
            (lambda: [glow(rA[0], YELLOW_M, 1.03), glow(rB[0], GREEN_M, 1.03)], 0.8),
        ])
        self.steps("MySQL and Oracle's database do it too, and keep their old versions in different places.", [
            (lambda: [*self.cap("also MySQL and Oracle's database (old versions kept elsewhere)", GREY_B)], 0.6),
        ])
        tbl = VGroup(M("3 rows: wallets 1, 2, 3, each 50000 cents", 20), M("UPDATE wallet 2: balance - 2500", 20, GOLD_M)).arrange(DOWN, buff=0.2)
        tbl.move_to([0, 0.5, 0])
        self.steps("So an update isn't an overwrite. It's a delete plus an insert. Try it on a small table: three wallets, then update wallet 2. "
                   "How many tuples does the page hold now? Pause and guess.", [
            (lambda: [*self.cap("an UPDATE = a delete plus an insert", WHITE)], 0.5),
            "Try it on",
            (lambda: [FadeOut(VGroup(s1, s2, ptr, ptr_t, rA, rB, aA, aB, page_t)), FadeIn(tbl[0])], 0.7),
            "then update",
            (lambda: [FadeIn(tbl[1])], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ts = [tiny_slot(0, "wallet 1", "50000", 857, 0), tiny_slot(1, "wallet 2", "50000", 857, 858, GREY_B, dim=False),
              tiny_slot(2, "wallet 3", "50000", 857, 0), tiny_slot(3, "wallet 2", "47500", 858, 0, GOLD_M)]
        pg0 = T("page 0: four tuples for three rows", 22, YELLOW_M).move_to([0, 1.6, 0])
        self.steps("Four tuples for three rows. Slot 2 is still there, stamped with x-max 858, and wallet 2's new balance sits in slot 4.", [
            (lambda: [*self.uncap(), FadeOut(tbl), LaggedStart(*[FadeIn(t, shift=0.1 * UP) for t in ts], lag_ratio=0.2), FadeIn(pg0)], 1.0),
            "Slot 2 is",
            (lambda: [glow(ts[1][0], GREY_B, 1.04)], 0.7),
            "sits in slot 4",
            (lambda: [glow(ts[3][0], GOLD_M, 1.04)], 0.7),
        ])

        # ---------------- scene 6: the costs, and where the notebook breaks ----------------
        old_tag = T("no reader needs it: VACUUM throws it away", 20, GREY_B).move_to([-1.6, -0.9, 0])
        stuck = chip("one transaction, open since the morning", RED_M, 20).move_to([0, -1.75, 0])
        self.steps("Of course, nothing is free. Old versions pile up, so a cleanup called VACUUM throws away the ones no reader can see any more.", [
            "Old versions",
            (lambda: [Indicate(ts[1], color=GREY_B)], 0.7),
            "a cleanup called",
            (lambda: [FadeIn(old_tag, shift=0.1 * UP)], 0.5),
            "throws away",
            (lambda: [ts[1].animate.set_opacity(0.2)], 0.6),
        ])
        self.steps("And one forgotten open transaction can hold that cleanup back for the whole database.", [
            (lambda: [ts[1].animate.set_opacity(1)], 0.5),
            "one forgotten",
            (lambda: [FadeIn(stuck, shift=0.1 * UP)], 0.6),
            "hold that cleanup",
            (lambda: [*self.cap("an old snapshot might still need the old versions", RED_M)], 0.5),
        ])
        self.steps("Two writers on the same row still take turns. Versions free the readers, not the writers.", [
            (lambda: [FadeOut(VGroup(old_tag, stuck)), *self.cap("versions free the readers, not the writers", WHITE, 28)], 0.6),
        ])
        self.steps("And here the notebook breaks. Its reader goes by the clock: skip anything after 18:00. "
                   "A database can't simply go by the clock. How it picks the right version is the next part of the lesson.", [
            "Its reader",
            (lambda: [*self.cap("the notebook's reader goes by the clock", YELLOW_M)], 0.5),
            "A database",
            (lambda: [*self.cap("a database can't simply go by the clock: next, the snapshot's rule", WHITE)], 0.6),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        s1n = slot_box(-SLOT_X, WHITE, "slot 1: wallet 7", "balance 500.00", "t_xmin 850    t_xmax 860")
        s2n = slot_box(SLOT_X, GOLD_M, "slot 2: wallet 7", "balance 250.00", "t_xmin 860    t_xmax 0")
        self.steps("So the moral: an update leaves the old version behind and stamps it. Each reader picks the one version its snapshot can see. "
                   "Keep the old row, and nobody has to wait.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*ts, pg0)), FadeIn(VGroup(s1n, s2n, ptr, ptr_t, page_t))], 0.8),
            "Each reader",
            (lambda: [FadeIn(VGroup(rA, aA)), FadeIn(VGroup(rB, aB))], 0.7),
            "Keep the old",
            (lambda: [*self.cap("keep the old row, and nobody has to wait", YELLOW_M, 30)], 0.6),
        ], after=0.6)
        xr = tick(False, 0.2).move_to([SLOT_X + SLOT_W / 2 - 0.35, SLOT_Y + 0.45, 0])
        self.steps("One quick check. Say 860 rolled back instead of committing. A query starts afterwards. "
                   "Which version of wallet 7 does it read? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(rA, aA, aB)), Transform(rB, reader(SLOT_X, "a query", "started after 860 rolled back", GREEN_M))], 0.7),
            "rolled back",
            (lambda: [*self.cap("860: rolled back", RED_M)], 0.4),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        aC = Arrow([SLOT_X - 0.6, RD_Y + 0.5, 0], [-SLOT_X + 0.6, SLOT_Y - SLOT_H / 2 - 0.08, 0], buff=0, stroke_width=3,
                   color=GREEN_M, max_tip_length_to_length_ratio=0.12)
        self.steps("Slot 1: 500.00. 860's stamp only counts if 860 committed, so slot 2 never counts for anyone.", [
            (lambda: [*self.uncap(), Create(xr), s2n.animate.set_opacity(0.35)], 0.6),
            (lambda: [GrowArrow(aC), glow(s1n[0], GREEN_M, 1.02)], 0.7),
            "never counts",
            (lambda: [*self.cap("a stamp counts only if its transaction committed", WHITE)], 0.5),
        ], after=0.3)
        self.play(*self.cap("keep the old row, and nobody has to wait", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
