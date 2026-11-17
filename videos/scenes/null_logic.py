from sfz import *

SAY.insert(0, (r"\b(WHERE|NOT|IN|IS|NULL|OR|AND|DISTINCT|FROM|SELECT|TRUE|FALSE)\b", lambda m: m.group(1).lower()))
SAY.insert(0, (r"\breferred_by\b", "referred by"))
SAY.insert(0, (r"\bAsha\b", "ah sha"))   # plain "Asha" runs into the word before it
SAY.insert(0, (r"count\(\*\)", "count star"))
SAY.insert(0, (r"count\(referred_by\)", "count of referred by"))
SAY.insert(0, (r"(?<![\w-])-1\b", "minus one"))

# the lesson's 13 customers (labs/env/postgres/course/seed.sql): id, name, referred_by (None is NULL)
ROWS = [(1, "Asha Rao", None), (2, "Ben Carter", None), (3, "Chloe Martin", 1), (4, "Daniel Kim", 2), (5, "Elena Petrova", 1),
        (6, "Farid Haddad", 3), (7, "Grace Lee", None), (8, "Hugo Silva", 4), (9, "Ivy Chen", None), (10, "Jonas Weber", 5),
        (11, "Kofi Mensah", None), (12, "Lena Novak", 7), (13, "Mateo Ruiz", 8)]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_Y, H_Y = 3.2, 2.42                       # the query bar, the table's header
RY = [2.0 - 0.355 * k for k in range(13)]  # row centres
ID_X, NAME_X, RB_X = -6.15, -5.7, -2.85    # columns: id, name, referred_by
TEST_X, KEEP_X = 0.35, 2.75                # the test's answer, and what WHERE does
ROW_X0, ROW_X1 = -6.55, 3.75
WS_X = 2.6                                 # centre of the workspace on the right
CAP_Y, BAR_Y = -3.2, -2.78
ANS = {"true": GREEN_M, "false": RED_M, "unknown": YELLOW_M}


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

    def steps(self, text, items, after=0.3):
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


def envelope(c, w=0.44, h=0.27, sw=2.2):
    """A sealed envelope: SQL's NULL. Something may be inside; nobody can see it."""
    c = np.array(c, dtype=float)
    body = Rectangle(width=w, height=h, stroke_color=GOLD_M, stroke_width=sw).set_fill("#2a2112", 1).move_to(c)
    tl, tr = c + np.array([-w / 2, h / 2, 0]), c + np.array([w / 2, h / 2, 0])
    tip = c + np.array([0, -h * 0.12, 0])
    flap = VMobject(stroke_color=GOLD_M, stroke_width=sw).set_points_as_corners([tl, tip, tr])
    seal = Dot(tip, radius=h * 0.2, color=RED_M)
    return VGroup(body, flap, seal)


def cell_value(k):
    v = ROWS[k][2]
    return M(str(v), 19).move_to([RB_X, RY[k], 0]) if v is not None else None


class NullLogic(Base):
    """sql-01, section 3. A free coffee for every customer Asha didn't invite: 11 expected, WHERE referred_by <> 1 returns 6.
    Why not 0 or -1; NULL as a sealed envelope; unknown and three-valued logic; WHERE keeps only true, run row by row
    over the lesson's 13 customers. The rules (NULL = NULL, IS NULL, OR and AND with unknown, NOT). IS DISTINCT FROM 1
    returns 11; NOT NULL columns. Kotlin's null == null, grouping as the envelope's break, count(*) 13 vs
    count(referred_by) 8. Moral and a check: how many rows does a careless "not equal" lose?"""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def query(self, s, color=WHITE):
        t = M(s, 21, color)
        r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.5, height=0.55, stroke_color=GREY_C, stroke_width=2).set_fill("#111111", 1)
        new = VGroup(r, t.move_to(r)).move_to([-1.1, Q_Y, 0])
        left_at(new, ROW_X0, Q_Y)
        old, self.qm = self.qm, new
        return [swap(old, new)]

    def result(self, s, color=WHITE):
        new = T(s, 26, color).move_to([5.65, Q_Y, 0])
        old, self.resm = self.resm, new
        return [swap(old, new)]

    def answer(self, k, word):
        new = T(word, 20, ANS[word]).move_to([TEST_X, RY[k], 0])
        old, self.tst[k] = self.tst[k], new
        return [swap(old, new, RIGHT)]

    def verdict(self, k, keep):
        new = T("kept" if keep else "dropped", 20, GREEN_M if keep else RED_M).move_to([KEEP_X, RY[k], 0])
        old, self.kp[k] = self.kp[k], new
        out = [swap(old, new, RIGHT)]
        box = self.rowbox[k]
        if keep:
            out.append(box.animate.set_stroke(GREEN_M, 2, opacity=1))
            out.append(self.rowtxt[k].animate.set_opacity(1))
        else:
            out.append(box.animate.set_stroke(RED_M, 1.5, opacity=0.6))
            out.append(self.rowtxt[k].animate.set_opacity(0.3))
        return out

    def reset_row(self, k):
        out = [self.rowbox[k].animate.set_stroke(GREY_D, 0, opacity=0), self.rowtxt[k].animate.set_opacity(1)]
        for lst in (self.tst, self.kp):
            if lst[k] is not None:
                out.append(FadeOut(lst[k]))
                lst[k] = None
        return out

    def evaluate(self, k, test, keep):
        return [*self.answer(k, test), *self.verdict(k, keep)]

    def construct(self):
        self.capm = self.qm = self.resm = None
        self.tst = [None] * 13
        self.kp = [None] * 13
        self.title_card("NULL is a sealed envelope", "and WHERE keeps only what is true")

        hdr = VGroup(T("id", 19, GREY_B).move_to([ID_X, H_Y, 0]), left_at(T("name", 19, GREY_B), NAME_X, H_Y),
                     M("referred_by", 18, GREY_B).move_to([RB_X, H_Y, 0]))
        hline = Line([ROW_X0, H_Y - 0.22, 0], [RB_X + 1.0, H_Y - 0.22, 0], stroke_width=1.5, color=GREY_D)
        self.rowbox = [RoundedRectangle(corner_radius=0.06, width=ROW_X1 - ROW_X0, height=0.31, stroke_width=0)
                       .set_fill(BLACK, 0).move_to([(ROW_X0 + ROW_X1) / 2, RY[k], 0]) for k in range(13)]
        self.rowtxt = [VGroup(M(str(i), 19, GREY_B).move_to([ID_X, RY[k], 0]), left_at(T(n, 19), NAME_X, RY[k]))
                       for k, (i, n, _) in enumerate(ROWS)]
        vals = [cell_value(k) for k in range(13)]
        blanks = [Line([RB_X - 0.15, RY[k], 0], [RB_X + 0.15, RY[k], 0], stroke_width=2, color=GREY_C) if ROWS[k][2] is None else None
                  for k in range(13)]
        nulls = [k for k in range(13) if ROWS[k][2] is None]
        asha = [k for k in range(13) if ROWS[k][2] == 1]
        others = [k for k in range(13) if ROWS[k][2] not in (None, 1)]

        # ---------------- scene 1: a free coffee ----------------
        self.steps("A small company's app records card payments, and it lists its 13 customers, noting who invited each one.", [
            (lambda: [FadeIn(hdr), Create(hline)], 0.6),
            "13 customers",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.05 * DOWN) for r in self.rowtxt], lag_ratio=0.08)], 1.4),
            "who invited",
            (lambda: [LaggedStart(*[FadeIn(v if v is not None else b) for v, b in zip(vals, blanks)], lag_ratio=0.06)], 1.2),
        ])
        self.steps("Asha's two friends got a free coffee when they joined with her invitation. "
                   "Now the company wants to send one to everybody else: every customer Asha didn't invite.", [
            (lambda: [Indicate(self.rowtxt[0][1], color=YELLOW_M)], 0.7),
            "two friends",
            (lambda: [*[vals[k].animate.set_color(YELLOW_M) for k in asha], *[self.rowtxt[k][1].animate.set_color(YELLOW_M) for k in asha]], 0.6),
            "everybody else",
            (lambda: self.cap("a free coffee for every customer Asha didn't invite", WHITE), 0.5),
        ])
        self.steps("That should be 11 people. You ask the database, and it answers at once, with no error: 6. Where did the other 5 go?", [
            (lambda: self.result("expected: 11", GREEN_M), 0.5),
            "You ask",
            (lambda: [*self.query("SELECT * FROM customers WHERE referred_by <> 1")], 0.6),
            "with no error",
            (lambda: [*self.result("got: 6", RED_M)], 0.6),
            "Where did",
            (lambda: [*self.cap("expected 11, got 6: where did 5 go?", RED_M)], 0.5),
        ], after=0.4)

        # ---------------- scene 2: what goes in an empty cell? ----------------
        self.steps("Look at the column. referred_by holds the id of the customer who invited this one. Asha is customer 1, so Chloe and Elena hold 1.", [
            (lambda: [*self.uncap(), *[v.animate.set_color(WHITE) for k, v in enumerate(vals) if v is not None],
                      *[self.rowtxt[k][1].animate.set_color(WHITE) for k in asha]], 0.5),
            "Look at the column",
            (lambda: [Indicate(hdr[2], color=YELLOW_M)], 0.6),
            "Chloe and Elena",
            (lambda: [*[Indicate(vals[k], color=YELLOW_M, scale_factor=1.3) for k in asha]], 0.8),
        ])
        k11 = 10
        q11 = T("?", 26, YELLOW_M).move_to([RB_X, RY[k11], 0])
        kc = VGroup(T("Kofi Mensah, customer 11", 26), M("referred_by = ?", 26, YELLOW_M)).arrange(DOWN, buff=0.25)
        kc.move_to([WS_X, 1.45, 0])
        tries = [VGroup(left_at(M(c, 26, col), -0.4, y), left_at(fit(T(t, 21, col), 5.45), 0.85, y))
                 for c, t, col, y in [("0", "no customer 0; a count would count Kofi", RED_M, 0.05),
                                      ("-1", "the same, and every query must remember it", RED_M, -0.75),
                                      ("NULL", "a marker for: no value here", GOLD_M, -1.55)]]
        x0 = tick(False, 0.13).move_to([-0.75, 0.05, 0])
        x1 = tick(False, 0.13).move_to([-0.75, -0.75, 0])
        self.steps("But Kofi, customer 11, signed up without an invitation. What should his referred_by hold?", [
            "But Kofi",
            (lambda: [Indicate(self.rowtxt[k11], color=YELLOW_M), FadeIn(kc[0], shift=0.1 * UP)], 0.7),
            "What should",
            (lambda: [swap(blanks[k11], q11), FadeIn(kc[1], shift=0.1 * UP)], 0.5),
        ])
        zero = M("0", 19, RED_M).move_to(q11)
        minus = M("-1", 19, RED_M).move_to(q11)
        self.steps("Try 0. There's no customer 0, and the table's rule that referred_by must name a real customer rejects it. "
                   "And a count of invited customers would count Kofi.", [
            (lambda: [swap(q11, zero), FadeIn(tries[0][0])], 0.4),
            "There's no customer 0",
            (lambda: [FadeIn(tries[0][1], shift=0.1 * RIGHT)], 0.5),
            "And a count",
            (lambda: [Create(x0)], 0.4),
        ])
        self.steps("Try -1: the same problems, and every query must remember what -1 means. "
                   "SQL's answer is a marker that means no value here: NULL.", [
            (lambda: [swap(zero, minus), FadeIn(tries[1], shift=0.1 * RIGHT)], 0.5),
            (lambda: [Create(x1)], 0.4),
            "SQL's answer",
            (lambda: [FadeIn(tries[2], shift=0.1 * RIGHT)], 0.5),
            "NULL",
            (lambda: [FadeOut(minus), *[FadeOut(blanks[k]) for k in nulls if k != k11],
                      *[FadeIn(M("NULL", 18, GOLD_M).move_to([RB_X, RY[k], 0])) for k in nulls]], 0.7),
        ], after=0.3)
        null_txt = [m for m in self.mobjects if isinstance(m, Text) and m.text == "NULL" and abs(m.get_x() - RB_X) < 0.01]

        # ---------------- scene 3: a sealed envelope ----------------
        envs = [envelope([RB_X, RY[k], 0]) for k in nulls]
        big = envelope([WS_X - 0.9, 0.6, 0], w=2.2, h=1.35, sw=4)
        eq1 = M("= 1 ?", 40).next_to(big, RIGHT, buff=0.45)
        self.steps("Picture NULL as a sealed envelope. There may be a number inside, but nobody can see it.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(kc, *tries, x0, x1)), *[ReplacementTransform(t, e) for t, e in zip(null_txt, envs)]], 0.9),
            "There may be",
            (lambda: [FadeIn(big, shift=0.1 * UP)], 0.7),
            "nobody can see",
            (lambda: [Wiggle(big, scale_value=1.05, rotation_angle=0.03 * TAU)], 0.9),
        ])
        unk = T("can't tell", 34, YELLOW_M).next_to(VGroup(big, eq1), DOWN, buff=0.45)
        self.steps("Is the envelope equal to 1? The honest answer is: can't tell. And that's what SQL says.", [
            "equal to 1",
            (lambda: [FadeIn(eq1, shift=0.1 * LEFT)], 0.5),
            "can't tell",
            (lambda: [FadeIn(unk, shift=0.1 * UP)], 0.6),
        ])
        unk2 = T("NULL, which here means unknown", 30, YELLOW_M).move_to(unk)
        self.steps("Ask whether NULL equals 1, and SQL doesn't say false. It says NULL again, which here means unknown.", [
            "doesn't say false",
            (lambda: [*self.cap("NULL = 1 is not false", GREY_B)], 0.5),
            "It says NULL",
            (lambda: [swap(unk, unk2)], 0.6),
        ])
        self.steps("Honestly, NULL should have been called don't know. Every rule makes sense once you read it that way.", [
            (lambda: [*self.cap("read NULL as: don't know", YELLOW_M, 28)], 0.6),
            "Every rule",
            (lambda: [glow(big[0], GOLD_M, 1.04)], 0.8),
        ])
        tvl = VGroup(T("true", 30, GREEN_M), T("false", 30, RED_M), T("unknown", 30, YELLOW_M)).arrange(RIGHT, buff=0.6)
        tvl.move_to([WS_X - 0.3, -1.4, 0])
        self.steps("So SQL has three answers: true, false and unknown. That's called three-valued logic.", [
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.1 * UP) for t in tvl], lag_ratio=0.4)], 1.2),
            "That's called",
            (lambda: [*self.cap("three-valued logic: true, false, unknown", WHITE)], 0.6),
        ], after=0.4)

        # ---------------- scene 4: WHERE keeps only true ----------------
        th = VGroup(M("referred_by <> 1", 18, GREY_B).move_to([TEST_X, H_Y, 0]), M("WHERE", 18, GREY_B).move_to([KEEP_X, H_Y, 0]))
        hline2 = Line([RB_X + 1.0, H_Y - 0.22, 0], [ROW_X1, H_Y - 0.22, 0], stroke_width=1.5, color=GREY_D)
        self.steps("Now the query. WHERE runs its test once for each row. Does a row with a sealed envelope stay or go? Pause and guess.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(big, eq1, unk2, tvl)), *self.result("")], 0.6),
            "WHERE runs",
            (lambda: [FadeIn(th), Create(hline2), *self.rowbox_show()], 0.7),
            "Does a row",
            (lambda: [*[glow(e[0], YELLOW_M, 1.2) for e in envs]], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Asha, customer 1: NULL not equal to 1 is unknown.", [
            (lambda: [*self.uncap(), self.rowbox[0].animate.set_stroke(BLUE_M, 2.5, opacity=1)], 0.4),
            "is unknown",
            (lambda: self.answer(0, "unknown"), 0.5),
        ])
        rule = T("WHERE keeps a row only when its test is true", 26, WHITE).move_to([0, CAP_Y, 0])
        self.steps("And here's the rule that bites: WHERE keeps a row only when its test is true. False drops it, and unknown drops it too.", [
            "WHERE keeps",
            (lambda: [swap(self.capm, rule)], 0.6),
            "unknown drops it",
            (lambda: self.verdict(0, False), 0.6),
        ])
        self.capm = rule
        self.steps("So Asha goes, though she certainly didn't invite herself. Chloe: 1 not equal to 1 is false, so she goes, correctly. "
                   "Daniel: 2 not equal to 1 is true, so he stays.", [
            "Chloe",
            (lambda: [self.rowbox[2].animate.set_stroke(BLUE_M, 2.5, opacity=1), *self.answer(1, "unknown"), *self.verdict(1, False)], 0.6),
            (lambda: self.evaluate(2, "false", False), 0.6),
            "Daniel",
            (lambda: [self.rowbox[3].animate.set_stroke(BLUE_M, 2.5, opacity=1)], 0.3),
            (lambda: self.evaluate(3, "true", True), 0.6),
        ])
        rest = list(range(4, 13))
        self.steps("And so on, down the table. Five envelopes, five rows gone, with no error and no warning. 6 of 13.", [
            (lambda: [LaggedStart(*[AnimationGroup(*self.evaluate(k, "unknown" if ROWS[k][2] is None else ("false" if ROWS[k][2] == 1 else "true"),
                                                                  ROWS[k][2] not in (None, 1))) for k in rest], lag_ratio=0.35)], 2.6),
            "Five envelopes",
            (lambda: [*[glow(self.rowbox[k], RED_M, 1.0) for k in nulls]], 0.8),
            "6 of 13",
            (lambda: [*self.result("got: 6 of 13", RED_M)], 0.5),
        ], after=0.4)

        # ---------------- scene 5: the rules ----------------
        rules = [("NULL = NULL", "unknown"), ("NULL IS NULL", "true"), ("true OR unknown", "true"), ("false AND unknown", "false"),
                 ("NOT unknown", "unknown")]
        rl = VGroup(*[VGroup(left_at(M(a, 21), -0.45, 1.7 - 0.72 * i), left_at(M("→", 21, GREY_B), 3.2, 1.7 - 0.72 * i),
                             left_at(T(b, 24, ANS[b]), 3.75, 1.7 - 0.72 * i)) for i, (a, b) in enumerate(rules)])
        panel = RoundedRectangle(corner_radius=0.14, width=7.1, height=4.75, stroke_color=GREY_C, stroke_width=2).set_fill("#0b0b0b", 1)
        panel.move_to([2.85, -0.1, 0])
        cols = VGroup(th, hline2, *[m for m in self.tst + self.kp if m is not None])
        self.steps("A few rules follow from the envelope. Any comparison with NULL is unknown, even NULL equals NULL: "
                   "two sealed envelopes may or may not hold the same number.", [
            (lambda: [*self.uncap(), cols.animate.set_opacity(0.0), FadeIn(panel)], 0.6),
            "even NULL equals",
            (lambda: [FadeIn(rl[0], shift=0.1 * RIGHT)], 0.6),
        ])
        self.steps("IS NULL asks a different question: is this a sealed envelope? That always has an answer.", [
            (lambda: [FadeIn(rl[1], shift=0.1 * RIGHT)], 0.6),
            "That always",
            (lambda: [*[Indicate(e, color=GOLD_M, scale_factor=1.3) for e in envs]], 0.8),
        ])
        self.steps("When tests are joined with OR, or with AND, a side we already know can decide on its own. true OR unknown is true, whatever the envelope holds. "
                   "false AND unknown is false. And NOT unknown is still unknown.", [
            "true OR unknown",
            (lambda: [FadeIn(rl[2], shift=0.1 * RIGHT)], 0.6),
            "false AND unknown",
            (lambda: [FadeIn(rl[3], shift=0.1 * RIGHT)], 0.6),
            "And NOT unknown",
            (lambda: [FadeIn(rl[4], shift=0.1 * RIGHT)], 0.6),
        ], after=0.4)

        # ---------------- scene 6: say what you mean ----------------
        th2 = M("IS DISTINCT FROM 1", 18, GREY_B).move_to([TEST_X, H_Y, 0])
        self.steps("So say what you mean. referred_by IS DISTINCT FROM 1 treats NULL as an ordinary value.", [
            (lambda: [FadeOut(VGroup(panel, rl)), *self.query("SELECT * FROM customers WHERE referred_by IS DISTINCT FROM 1"),
                      *self.result("")], 0.8),
            (lambda: [th[1].animate.set_opacity(1), hline2.animate.set_opacity(1), FadeIn(th2),
                      *[m.animate.set_opacity(1) for m in self.tst + self.kp if m is not None]], 0.6),
            "treats NULL",
            (lambda: [*self.cap("IS DISTINCT FROM: NULL is an ordinary value here", WHITE)], 0.5),
        ])
        self.remove(th[0])
        self.steps("An envelope is distinct from 1, so the test is true, and the five come back: 11 rows, everyone Asha didn't invite.", [
            "so the test is true",
            (lambda: [LaggedStart(*[AnimationGroup(*self.evaluate(k, "true", True)) for k in nulls], lag_ratio=0.3)], 1.5),
            "11 rows",
            (lambda: [*self.result("got: 11", GREEN_M)], 0.5),
        ])
        self.steps("Writing not equal to 1, OR referred_by IS NULL, does the same. "
                   "And if a column should never be empty, declare it NOT NULL, and the question never comes up.", [
            (lambda: [*self.cap("same: referred_by <> 1 OR referred_by IS NULL", WHITE)], 0.5),
            "And if a column",
            (lambda: [*self.cap("never empty? declare the column NOT NULL", WHITE)], 0.5),
        ], after=0.4)

        # ---------------- scene 7: two warnings, and counting ----------------
        self.steps("Two warnings. If you write Kotlin or Java, this feels wrong, because there, null equals null is true. "
                   "SQL spells that kind of equal: IS NOT DISTINCT FROM.", [
            (lambda: [*self.cap("Kotlin, Java: null == null is true", GREY_B)], 0.5),
            "SQL spells",
            (lambda: [*self.cap("SQL: NULL IS NOT DISTINCT FROM NULL is true", WHITE)], 0.5),
        ])
        self.steps("And the envelope picture breaks in one place: when SQL groups or sorts rows, it puts all the NULLs together, as if they were equal.", [
            (lambda: [*self.cap("where the envelope breaks: grouping and sorting put NULLs together", GOLD_M)], 0.6),
            "puts all the NULLs",
            (lambda: [LaggedStart(*[e.animate.shift(0.12 * RIGHT) for e in envs], lag_ratio=0.15)], 0.8),
            (lambda: [LaggedStart(*[e.animate.shift(0.12 * LEFT) for e in envs], lag_ratio=0.15)], 0.6),
        ])
        cnt = VGroup(*[VGroup(left_at(M(a, 22), -0.45, y), left_at(M("→", 22, GREY_B), 3.3, y), left_at(M(b, 24, c), 3.85, y))
                       for a, b, c, y in [("count(*)", "13", WHITE, 1.3), ("count(referred_by)", "8", WHITE, 0.4),
                                          ("sum over no rows", "NULL", GOLD_M, -0.5)]])
        panel2 = RoundedRectangle(corner_radius=0.14, width=7.1, height=4.75, stroke_color=GREY_C, stroke_width=2).set_fill("#0b0b0b", 1)
        panel2.move_to([2.85, -0.1, 0])
        self.steps("Counting has its own rules. count(*) counts rows: 13. count(referred_by) counts the filled-in values: 8. "
                   "And sum over no rows at all is NULL, not 0.", [
            (lambda: [*self.uncap(), FadeIn(panel2), th[1].animate.set_opacity(0), th2.animate.set_opacity(0), hline2.animate.set_opacity(0),
                      *[m.animate.set_opacity(0) for m in self.tst + self.kp if m is not None]], 0.5),
            "count(*) counts",
            (lambda: [FadeIn(cnt[0], shift=0.1 * RIGHT)], 0.5),
            "count(referred_by) counts",
            (lambda: [FadeIn(cnt[1], shift=0.1 * RIGHT)], 0.5),
            "And sum",
            (lambda: [FadeIn(cnt[2], shift=0.1 * RIGHT)], 0.5),
        ], after=0.4)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So: NULL is a sealed envelope, any comparison with it is unknown, and WHERE keeps only true. "
                   "Next time a filter says not, ask which side can be empty.", [
            (lambda: [*self.cap("NULL: a sealed envelope.   comparisons: unknown.   WHERE: only true", WHITE)], 0.6),
            "Next time",
            (lambda: [*self.cap("a filter that says \"not\": which side can be empty?", YELLOW_M)], 0.6),
        ], after=0.4)
        self.steps("One quick check. count(*) says 13, and count(referred_by) says 8. How many customers would a careless not equal lose? "
                   "Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(cnt[2])], 0.4),
            "count(*) says",
            (lambda: [Indicate(cnt[0][2], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "count(referred_by) says",
            (lambda: [Indicate(cnt[1][2], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        gap = left_at(M("13 - 8 = 5", 26, YELLOW_M), -0.45, -0.5)
        self.steps("5. The gap between the counts is the number of sealed envelopes, and every one of them falls out.", [
            (lambda: [*self.uncap(), FadeIn(gap, shift=0.1 * UP)], 0.6),
            "sealed envelopes",
            (lambda: [*[glow(e[0], GOLD_M, 1.25) for e in envs], *[glow(self.rowbox[k], YELLOW_M, 1.0) for k in nulls]], 0.9),
            "falls out",
            (lambda: [*self.cap("5 sealed envelopes: 5 rows a careless \"not equal\" loses", GOLD_M)], 0.6),
        ], after=0.4)
        self.wait(2.0)

    def rowbox_show(self):
        return [b.animate.set_stroke(GREY_D, 1, opacity=0.5) for b in self.rowbox]
