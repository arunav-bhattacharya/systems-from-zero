from sfz import *

# Kokoro drops the possessive after a digit ("shop 5's" came out as "shop five"); say the number as a word.
SAY.insert(0, (r"\b([1-9])'s\b", lambda m: "one two three four five six seven eight nine".split()[int(m.group(1)) - 1] + "'s"))

SAY.insert(0, (r"\bGROUP BY\b", "group by"))
SAY.insert(0, (r"\bWHERE\b", "where"))
SAY.insert(0, (r"\bHAVING\b", "having"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TITLE_Y = 2.62
Q_Y = [3.33, 3.0]
BOX_X0, BOX_X1, BOX_TOP, BOX_BOT = -6.55, -3.25, 2.35, -2.0       # the shoebox: the payments table
RCX, RW, RH = -4.9, 3.0, 0.34
RY = [2.0 - 0.41 * i for i in range(10)]
EX, EW, EH = -0.6, 3.4, 0.82                                      # the envelopes: the groups
EY = [1.65, 0.6, -0.45, -1.5]
KEY_X = -2.68
OX_M, OX_C, OX_S = 2.35, 3.95, 5.95                               # the lines out: merchant_id, count, sum
OH_Y, ORULE_Y = 2.15, 1.95
CAP_Y = -3.25

# the ten March payments (the lesson's stepper): payment, shop, amount in cents, status
PAY = [(13, 5, 64000, ""), (14, 1, 5310, ""), (15, 4, 89900, "failed"), (16, 5, 31500, ""), (17, 4, 18999, ""),
       (18, 4, 18999, ""), (19, 4, 18999, ""), (20, 1, 7425, "pending"), (21, 7, 1325, ""), (22, 5, 52000, "")]
SHOPS = [1, 4, 5, 7]                                              # envelope order, top to bottom
LINES = {1: (1, 5310), 4: (3, 56997), 5: (3, 147500), 7: (1, 1325)}   # count, sum (the stepper's output)


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

    def query(self, lines, color=GREY_A):
        new = VGroup(*[M(s, 16, color).move_to([0, Q_Y[i], 0]) for i, s in enumerate(lines)])
        old, self.qm = self.qm, new
        return [swap(old, new)]

    def countdown(self, c=(0, -2.6), secs=3.0):
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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def shoebox():
    r = RoundedRectangle(corner_radius=0.12, width=BOX_X1 - BOX_X0, height=BOX_TOP - BOX_BOT, stroke_color=GREY_B,
                         stroke_width=3).set_fill("#111111", 1).move_to([(BOX_X0 + BOX_X1) / 2, (BOX_TOP + BOX_BOT) / 2, 0])
    return r.set_z_index(-1)


def receipt(i):
    p, m, a, st = PAY[i]
    color = RED_M if st == "failed" else (GREY_B if st else WHITE)
    x0 = RCX - RW / 2 + 0.15
    parts = VGroup(left_at(M(str(p), 17, color), x0, RY[i]), left_at(M(f"m{m}", 17, GOLD_M if not st else color), x0 + 0.5, RY[i]),
                   right_at(M(str(a), 17, color), x0 + 1.75, RY[i]))
    if st:
        parts.add(left_at(M(st, 14, color), x0 + 1.88, RY[i]))
    r = RoundedRectangle(corner_radius=0.06, width=RW, height=RH, stroke_color=GREY_D, stroke_width=1.5).set_fill(BLACK, 1).move_to([RCX, RY[i], 0])
    return VGroup(r, parts)


def envelope(k):
    y = EY[k]
    x0, x1, top = EX - EW / 2, EX + EW / 2, y + EH / 2
    body = Rectangle(width=EW, height=EH, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.1), 1).move_to([EX, y, 0]).set_z_index(-1)
    flap = VMobject(stroke_color=GOLD_M, stroke_width=2).set_points_as_corners([[x0, top, 0], [EX, top - 0.28, 0], [x1, top, 0]])
    return VGroup(body, flap)


def key_label(k, color=GOLD_M):
    return M(f"m{SHOPS[k]}", 22, color).move_to([KEY_X, EY[k], 0])


def env_amounts(k):
    """Where each receipt's amount sits inside its envelope (left to right, in arrival order)."""
    m = SHOPS[k]
    amts = [a for p, mm, a, st in PAY if mm == m and not st]
    g = VGroup(*[M(str(a), 17) for a in amts]).arrange(RIGHT, buff=0.22)
    return g.move_to([EX, EY[k] - 0.13, 0]).set_z_index(1)


def out_line(k, color=WHITE):
    m = SHOPS[k]
    c, s = LINES[m]
    y = EY[k]
    return VGroup(M(str(m), 22, color).move_to([OX_M, y, 0]), M(str(c), 22, color).move_to([OX_C, y, 0]),
                  right_at(M(str(s), 22, color), OX_S, y))


class GroupByRollup(Base):
    """sql-04, section 0. How do you get one line per shop? Not eight trips, not a million rows shipped out. An aggregate
    folds many values into one (all 37 payments: 30 succeeded, 720455). The shoebox of receipts: one envelope per shop is
    a group, its key is the shop number, the total on the front is the aggregate. On March's ten payments, WHERE drops 15
    and 20, eight rows make four envelopes, and each folds into one line. Showing amount_minor breaks on shop 5's three
    amounts: the key or an aggregate only. HAVING is next. Check: shop 6 gets no line."""

    def construct(self):
        self.capm = self.qm = None
        self.title_card("One line per shop", "sort the receipts into envelopes, then fold each one")

        # ---------------- scene 1: the question ----------------
        box = shoebox()
        box_t = T("payments", 24, GREY_B).move_to([RCX, TITLE_Y, 0])
        R = [receipt(i) for i in range(10)]
        self.steps("A small company's app records card payments. Each payment is one row in a table: which shop was paid, "
                   "the amount in cents, and whether it succeeded. Here are the ten from March.", [
            (lambda: [FadeIn(box), FadeIn(box_t)], 0.8),
            "Each payment is one row",
            (lambda: [FadeIn(R[0], shift=0.1 * DOWN)], 0.5),
            "which shop",
            (lambda: [Indicate(R[0][1][1], color=GOLD_M, scale_factor=1.3)], 0.6),
            "the amount",
            (lambda: [Indicate(R[0][1][2], color=WHITE, scale_factor=1.2)], 0.6),
            "Here are the ten",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in R[1:]], lag_ratio=0.15)], 1.6),
        ])
        self.steps("Every shop wants to know what it took. So how do you turn many rows into one line per shop?", [
            "Every shop",
            (lambda: [LaggedStart(*[Indicate(r[1][1], color=GOLD_M, scale_factor=1.3) for r in R], lag_ratio=0.08)], 1.2),
            "So how do you",
            (lambda: self.cap("many rows in, one line per shop out?", YELLOW_M, 28), 0.6),
        ])
        self.steps("You could ask once per shop: the rows for shop 1, then shop 2, and so on. Eight trips, "
                   "and you need the list of shops first. Or you could fetch every payment into your own program "
                   "and add them up there.", [
            (lambda: [*self.query(["SELECT ... FROM payments WHERE merchant_id = 1;"]), *self.cap("ask once per shop?")], 0.6),
            (lambda: [*[Indicate(R[i][1][1], color=GOLD_M, scale_factor=1.3) for i in (1, 7)]], 0.6),
            "then shop 2",
            (lambda: self.query(["SELECT ... FROM payments WHERE merchant_id = 2;"]), 0.5),
            "Eight trips",
            (lambda: self.cap("8 shops: 8 trips, and the list of shops first"), 0.5),
            "Or you could fetch",
            (lambda: [*self.query(["SELECT * FROM payments;"]), *self.cap("or fetch every row and add them up in your program")], 0.6),
        ])
        self.steps("With ten rows, fine. With a million, you'd ship a million rows out to work out 2,500 numbers. "
                   "That's like posting a whole filing cabinet to someone, to ask for one total. "
                   "Better to do the adding where the data lives.", [
            "With a million",
            (lambda: self.cap("1,000,000 rows out, to work out 2,500 numbers", RED_M), 0.6),
            "Better to do",
            (lambda: [*self.cap("do the adding where the data lives", WHITE), glow(box, GREY_B, 1.0)], 0.8),
        ])

        # ---------------- scene 2: many rows in, one row out ----------------
        allq = ["SELECT count(*), sum(amount_minor) FROM payments WHERE status = 'succeeded';"]
        res = VGroup(T("all 37 payments, succeeded only", 20, GREY_B),
                     VGroup(M("count", 18, GREY_B), M("sum", 18, GREY_B)).arrange(RIGHT, buff=1.2),
                     VGroup(M("30", 26), M("720455", 26)).arrange(RIGHT, buff=0.9)).arrange(DOWN, buff=0.3)
        res[2][0].align_to(res[1][0], RIGHT)
        res[2][1].align_to(res[1][1], RIGHT)
        res.move_to([2.6, 0.55, 0])
        self.steps("The database starts with an aggregate function: one that takes many values and returns one. "
                   "count counts rows, and sum adds up a column.", [
            (lambda: [*self.uncap(), *self.query(allq)], 0.6),
            "an aggregate function",
            (lambda: self.cap("aggregate function: many values in, one value out", TEAL_M), 0.6),
            "count counts",
            (lambda: [Indicate(self.qm[0], color=TEAL_M, scale_factor=1.03)], 0.8),
        ])
        self.steps("Used alone, an aggregate folds every row it sees into one. Over all 37 payments in the course database, "
                   "the succeeded ones fold into a single line: 30 payments, 720,455 cents.", [
            "Over all 37",
            (lambda: [FadeIn(res[0]), FadeIn(res[1])], 0.6),
            "a single line",
            (lambda: [FadeIn(res[2], shift=0.1 * LEFT)], 0.6),
        ])
        self.steps("Many rows in, one row out. But that's one total for everyone, and we want one per shop.", [
            (lambda: self.cap("many rows in, one row out"), 0.5),
            "one per shop",
            (lambda: [*self.cap("one total for everyone; we want one per shop", YELLOW_M),
                      LaggedStart(*[Indicate(r[1][1], color=GOLD_M, scale_factor=1.3) for r in R], lag_ratio=0.06)], 1.0),
        ])

        # ---------------- scene 3: the shoebox ----------------
        box_t2 = T("the shoebox: payments", 24, GREY_B).move_to([RCX, TITLE_Y, 0])
        E = [envelope(k) for k in range(4)]
        K = [key_label(k) for k in range(4)]
        env_t = T("envelopes", 24, GOLD_M).move_to([EX, TITLE_Y, 0])
        self.steps("Picture a shoebox of paper receipts at the end of the day. You'd sort them into one envelope per shop. "
                   "Then you'd count the receipts in each envelope, and write the total on the front.", [
            (lambda: [FadeOut(res), *self.uncap(), FadeOut(self.qm), swap(box_t, box_t2)], 0.7),
            "You'd sort them",
            (lambda: [FadeIn(env_t), LaggedStart(*[FadeIn(e, shift=0.1 * RIGHT) for e in E], lag_ratio=0.2)], 1.2),
            "count the receipts",
            (lambda: self.cap("count the receipts in each, write the total on the front"), 0.6),
        ])
        self.qm = None
        self.steps("That's what GROUP BY does. Each receipt is a row. Each envelope is a group, one for each different "
                   "shop number, and that number is the group's key. The total on the front is the aggregate.", [
            (lambda: self.cap("GROUP BY: one group per different key", WHITE), 0.5),
            "Each receipt",
            (lambda: [*self.cap("a receipt = a row"), glow(R[0][0], WHITE, 1.05)], 0.6),
            "Each envelope",
            (lambda: [*self.cap("an envelope = a group"), *[glow(e[0], GOLD_M, 1.03) for e in E]], 0.7),
            "that number",
            (lambda: [*self.cap("the shop number = the group's key", GOLD_M), LaggedStart(*[FadeIn(k, scale=0.6) for k in K], lag_ratio=0.2)], 0.9),
            "The total on",
            (lambda: self.cap("the total on the front = the aggregate", TEAL_M), 0.6),
        ])

        # ---------------- scene 4: run it on March ----------------
        q_m = ["SELECT merchant_id, count(*), sum(amount_minor) FROM payments",
               "WHERE <March> AND status = 'succeeded' GROUP BY merchant_id"]
        strikes = {i: Line([RCX - RW / 2 + 0.1, RY[i], 0], [RCX + RW / 2 - 0.1, RY[i], 0], stroke_width=3, color=RED_M) for i in (2, 7)}
        self.steps("Let's run it on March, for succeeded payments only. WHERE goes first, and it looks at one row at a time. "
                   "Payment 15 failed, and payment 20 is still pending, so both are gone before any envelope exists.", [
            (lambda: [*self.uncap(), *self.query(q_m)], 0.7),
            "WHERE goes first",
            (lambda: [*self.cap("WHERE: one row at a time, before any grouping", WHITE),
                      LaggedStart(*[glow(r[0], WHITE, 1.04) for r in R], lag_ratio=0.08)], 1.2),
            "Payment 15",
            (lambda: [Create(strikes[2])], 0.4),
            "payment 20",
            (lambda: [Create(strikes[7])], 0.4),
            "so both are gone",
            (lambda: [FadeOut(VGroup(R[2], R[7], strikes[2], strikes[7]))], 0.7),
        ])
        self.steps("Eight rows are left. How many lines will come out? Pause and guess.", [
            (lambda: self.cap("8 rows left", WHITE), 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        A = [env_amounts(k) for k in range(4)]

        def sort_into(m):
            k = SHOPS.index(m)
            idx = [i for i, (p, mm, a, st) in enumerate(PAY) if mm == m and not st]
            an = []
            for j, i in enumerate(idx):
                an += [ReplacementTransform(R[i][1][2], A[k][j]), FadeOut(R[i][0]), FadeOut(R[i][1][0]), FadeOut(R[i][1][1])]
            return an + [glow(E[k][0], GOLD_M, 1.04)]

        self.steps("Four. GROUP BY makes one envelope per shop it finds: shop 5's three receipts in one, shop 4's three "
                   "in another, and one each for shops 1 and 7.", [
            (lambda: [*self.cap("4 envelopes: one per shop number found", GOLD_M)], 0.5),
            "shop 5's",
            (lambda: sort_into(5), 1.0),
            "shop 4's",
            (lambda: sort_into(4), 1.0),
            "and one each",
            (lambda: [*sort_into(1), *sort_into(7)], 1.0),
        ])
        out_t = T("lines out", 24, WHITE).move_to([4.15, TITLE_Y, 0])
        oh = VGroup(M("merchant_id", 16, GREY_B).move_to([OX_M, OH_Y, 0]), M("count", 16, GREY_B).move_to([OX_C, OH_Y, 0]),
                    right_at(M("sum", 16, GREY_B), OX_S, OH_Y))
        orule = Line([1.5, ORULE_Y, 0], [6.25, ORULE_Y, 0], stroke_width=1.5, color=GREY_D)
        L = [out_line(k) for k in range(4)]

        def fold(m):
            k = SHOPS.index(m)
            return [TransformFromCopy(A[k], L[k][2]), FadeIn(L[k][0]), FadeIn(L[k][1])]

        self.steps("Now each aggregate folds its envelope. count counts the receipts, and sum adds them up. "
                   "Shop 5: three payments, 147,500 cents. Shop 4: three, 56,997. Shop 1 and shop 7: one each.", [
            (lambda: [*self.cap("fold each envelope: count and sum", TEAL_M), FadeIn(out_t), FadeIn(oh), Create(orule)], 0.8),
            "Shop 5",
            (lambda: fold(5), 0.9),
            "Shop 4",
            (lambda: fold(4), 0.9),
            "Shop 1 and",
            (lambda: [*fold(1), *fold(7)], 0.9),
        ], after=0.4)

        # ---------------- scene 5: show the amount too? ----------------
        which = T("which amount? 64000, 31500 or 52000", 18, RED_M).move_to([4.15, (EY[2] + EY[3]) / 2, 0])
        self.steps("Now a tempting idea. Why not show each shop's amount on its line too? "
                   "For shops 1 and 7, there's only one amount, so it looks harmless.", [
            (lambda: self.cap("show each shop's amount on its line too?", PURPLE_M), 0.6),
            "For shops 1 and 7",
            (lambda: [Indicate(A[0], color=PURPLE_M, scale_factor=1.25), Indicate(A[3], color=PURPLE_M, scale_factor=1.25)], 1.0),
        ])
        self.steps("But shop 5's line stands for three receipts, with three amounts. Which one goes on the front? "
                   "PostgreSQL won't play favourites. It stops with an error: the column must appear in the GROUP BY clause, "
                   "or be used in an aggregate function.", [
            "But shop 5's",
            (lambda: [A[2].animate.set_color(RED_M), glow(E[2][0], RED_M, 1.04)], 0.7),
            "Which one",
            (lambda: [FadeIn(which, shift=0.1 * UP)], 0.5),
            (lambda: [LaggedStart(*[Indicate(a, color=RED_M, scale_factor=1.25) for a in A[2]], lag_ratio=0.3)], 1.0),
            "It stops",
            (lambda: self.cap("error: the column must appear in GROUP BY, or be used in an aggregate", RED_M), 0.6),
        ])
        self.steps("That's the rule that trips up everyone at first. After grouping, one line stands for a whole envelope. "
                   "So a column can appear there only if it has one value per envelope: the key you grouped by, or an aggregate.", [
            (lambda: [FadeOut(which), A[2].animate.set_color(WHITE)], 0.6),
            "one line stands",
            (lambda: [glow(E[2][0], GOLD_M, 1.04), Indicate(L[2], color=WHITE, scale_factor=1.06)], 0.9),
            "the key you",
            (lambda: [Transform(oh[0], M("merchant_id", 16, GOLD_M).move_to(oh[0])), *self.cap("one value per envelope: the key, or an aggregate", WHITE)], 0.6),
            "or an aggregate",
            (lambda: [Transform(oh[1], M("count", 16, TEAL_M).move_to(oh[1])), Transform(oh[2], right_at(M("sum", 16, TEAL_M), OX_S, OH_Y))], 0.6),
        ])

        # ---------------- scene 6: before the fold and after it ----------------
        dim = VGroup(*[Rectangle(width=OX_S + 0.35 - (KEY_X - 0.35), height=0.8, stroke_width=0).set_fill(BLACK, 0.78)
                       .move_to([(OX_S + 0.35 + KEY_X - 0.35) / 2, EY[k], 0]).set_z_index(5) for k in (0, 3)])
        self.steps("One more limit. WHERE ran before the envelopes existed, so it can only judge single rows. "
                   "To drop whole envelopes, say shops that took 100.00 or less, you need a second filter that runs after the fold. "
                   "It's called HAVING, and it's the next section.", [
            (lambda: self.cap("WHERE: single rows, before the envelopes exist", WHITE), 0.5),
            "To drop whole",
            (lambda: [*self.query(q_m[:1] + ["WHERE <March> AND status = 'succeeded' GROUP BY merchant_id HAVING sum(amount_minor) > 10000"]),
                      *self.cap("HAVING: whole envelopes, after the fold")], 0.7),
            "a second filter",
            (lambda: [FadeIn(dim)], 0.8),
            "It's called",
            (lambda: [glow(E[1][0], GOLD_M, 1.04), glow(E[2][0], GOLD_M, 1.04)], 0.8),
            "the next section",
            (lambda: [FadeOut(dim), *self.query(q_m)], 0.7),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, one line per shop? Sort the rows into groups by a key, then fold each group into one row. "
                   "And the adding happens where the data lives.", [
            (lambda: self.cap("one line per shop?", WHITE), 0.5),
            "Sort the rows",
            (lambda: [*self.cap("sort into groups by a key, then fold each group into one row", YELLOW_M, 28),
                      LaggedStart(*[glow(e[0], GOLD_M, 1.03) for e in E], lag_ratio=0.15)], 1.0),
            "then fold",
            (lambda: [LaggedStart(*[Indicate(l, color=TEAL_M, scale_factor=1.05) for l in L], lag_ratio=0.15)], 1.0),
        ], after=0.5)
        e6 = DashedVMobject(Rectangle(width=EW, height=0.56, stroke_color=RED_M, stroke_width=2.5), num_dashes=40).move_to([EX, -2.3, 0])
        k6 = M("m6", 22, RED_M).move_to([KEY_X, -2.3, 0])
        e6t = T("no receipts", 18, RED_M).move_to(e6)
        self.steps("One quick check. Shop 6, Paper Lantern Books, took no payments at all. Does it get a line with a zero? "
                   "Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "Shop 6",
            (lambda: self.cap("shop 6, Paper Lantern Books: no payments. a line with 0?", WHITE), 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(c=(4.15, -2.3))
        self.steps("No. No receipts, no envelope, and no line. A group exists only if at least one row has its key.", [
            (lambda: [*self.uncap(), Create(e6), FadeIn(k6), FadeIn(e6t)], 0.6),
            "no envelope",
            (lambda: [Create(tick(False, 0.2).move_to([EX + EW / 2 + 0.45, -2.3, 0]))], 0.4),
            "A group exists",
            (lambda: self.cap("a group exists only if at least one row has its key", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("sort into groups by a key, then fold each group into one row", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
