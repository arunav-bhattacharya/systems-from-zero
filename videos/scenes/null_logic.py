from sfz import *

SAY.insert(0, (r"\b(WHERE|NOT|IN|IS|NULL|OR|COALESCE|EXISTS|SELECT)\b", lambda m: m.group(1).lower()))
SAY.insert(0, (r"\breferred_by\b", "referred by"))
SAY.insert(0, (r"\bcustomer_id\b", "customer I D"))
SAY.insert(0, (r"\bAsha\b", "ah sha"))   # plain "Asha" runs into the word before it

QX, QY = -6.3, [3.2, 2.78, 2.36]          # the query, top left
COLX = [-5.75, -3.55, -1.3, 0.95]         # customer_id, referred_by, test, WHERE (centres)
HEAD_Y = 1.75
ROW_Y = [1.15, 0.57, -0.01, -0.59, -1.17, -1.75]
PX, PW, PY, PH = 4.43, 4.25, -0.1, 4.1    # right panel
PL_Y = [1.25, 0.7, 0.15, -0.4, -0.95, -1.5]
ST_Y = -2.6
REF = [None, None, 1, 2, 1, 3]
VCOL = {"unknown": PURPLE_M, "false": RED_M, "true": GREEN_M}


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
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


def q(s, k, color=WHITE):
    return left_at(M(s, 22, color), QX, QY[k])


def cell(s, col, k, color=WHITE, mono=True, size=26):
    return (M(s, size, color) if mono else T(s, size + 2, color)).move_to([COLX[col], ROW_Y[k], 0])


def test(v, k):
    return cell(v, 2, k, VCOL[v], mono=False)


def where(kept, k):
    return cell("kept" if kept else "dropped", 3, k, GREEN_M if kept else GREY_C, mono=False)


def pl(s, k, color=WHITE, size=20):
    return left_at(M(s, size, color), PX - PW / 2 + 0.25, PL_Y[k])


def ptitle(s):
    return T(s, 22, GREY_B).move_to([PX, PY + PH / 2 - 0.32, 0])


def status(s, color=GREY_B):
    return T(s, 28, color).move_to([0, ST_Y, 0])


class NullLogic(Base):
    """sql-01, section 3: customers 1 to 6, referred_by NULL, NULL, 1, 2, 1, 3. WHERE referred_by <> 1 is unknown for
    the NULL rows, and WHERE keeps only true, so it returns 4 and 6 instead of 1, 2, 4, 6. OR IS NULL and COALESCE fix it.
    NOT IN against a list holding NULL is never true, so 'who referred nobody' returns nothing until the NULLs are
    filtered out of the subquery."""

    def construct(self):
        self.title_card("NULL and three-valued logic", "why a WHERE clause quietly drops rows")

        heads = VGroup(M("customer_id", 20, GREY_B).move_to([COLX[0], HEAD_Y, 0]),
                       M("referred_by", 20, GREY_B).move_to([COLX[1], HEAD_Y, 0]),
                       T("the test", 22, GREY_B).move_to([COLX[2], HEAD_Y, 0]),
                       T("WHERE", 22, GREY_B).move_to([COLX[3], HEAD_Y, 0]))
        hline = Line([-6.5, HEAD_Y - 0.27, 0], [1.75, HEAD_Y - 0.27, 0], stroke_width=1.5, color=GREY_D)
        ids = [cell(str(i + 1), 0, i) for i in range(6)]
        refs = [cell("NULL" if r is None else str(r), 1, i, PURPLE_M if r is None else WHITE) for i, r in enumerate(REF)]
        self.steps("Customers 1 and 2 signed up without a referral. Their referred_by column holds NULL, "
                   "a marker that means no value: unknown.", [
            (lambda: [FadeIn(heads), Create(hline)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(VGroup(ids[i], refs[i]), shift=0.08 * RIGHT) for i in range(6)], lag_ratio=0.15)], 1.3),
            "Their referred_by",
            (lambda: [*[r.animate(rate_func=there_and_back).scale(1.2) for r in refs[:2]]], 0.9),
        ])

        q1 = q("SELECT customer_id FROM customers", 0, GREY_B)
        q2 = q("WHERE referred_by <> 1", 1)
        self.steps("Which customers did Asha, customer 1, not refer? Of these six, four. "
                   "The obvious query keeps rows where referred_by is not equal to 1.", [
            (lambda: [ids[0].animate.set_color(GOLD_M)], 0.5),
            "Of these six",
            (lambda: [*[ids[i].animate(rate_func=there_and_back).set_color(GREEN_M).scale(1.2) for i in (0, 1, 3, 5)]], 0.9),
            "The obvious query",
            (lambda: [ids[0].animate.set_color(WHITE), FadeIn(q1), FadeIn(q2, shift=0.1 * DOWN)], 0.8),
        ])

        panel = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=PURPLE_M, stroke_width=2.5)
        panel.set_fill(BLACK, 1).move_to([PX, PY, 0])
        pt = ptitle("comparing with NULL")
        tests = [test(v, i) for i, v in enumerate(["unknown", "unknown", "false", "true", "false", "true"])]
        r1 = pl("NULL <> 1      unknown", 0, PURPLE_M)
        self.steps("Customer 1: is NULL different from 1? Nobody knows, so SQL answers unknown. "
                   "Not true, and not false.", [
            (lambda: [refs[0].animate.scale(1.15), FadeIn(panel), FadeIn(pt)], 0.7),
            "Nobody knows",
            (lambda: [FadeIn(tests[0], shift=0.08 * RIGHT), FadeIn(r1)], 0.7),
            "Not true",
            (lambda: [refs[0].animate.scale(1 / 1.15), glow(panel, PURPLE_M, 1.02)], 0.8),
        ])

        r2 = pl("NULL = NULL    unknown", 1, PURPLE_M)
        r3 = pl("NULL > 5       unknown", 2, PURPLE_M)
        self.steps("Any comparison with NULL is unknown, even NULL equals NULL. "
                   "Two unknown values might or might not match.", [
            (lambda: [FadeIn(r3, shift=0.1 * DOWN)], 0.6),
            "even NULL equals",
            (lambda: [FadeIn(r2, shift=0.1 * DOWN)], 0.6),
        ])

        wh = [where(False, 0), where(False, 1), where(False, 2), where(True, 3), where(False, 4), where(True, 5)]
        r4 = pl("WHERE keeps", 4, WHITE)
        r5 = pl("only true", 5, GREEN_M)
        self.steps("And WHERE keeps a row only when the test is true. False drops it. Unknown drops it too.", [
            (lambda: [FadeIn(r4), FadeIn(r5)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(tests[i], shift=0.08 * RIGHT) for i in range(1, 6)], lag_ratio=0.25)], 1.4),
            "False drops",
            (lambda: [FadeIn(wh[2]), FadeIn(wh[4]), FadeIn(wh[3]), FadeIn(wh[5]),
                      *[m.animate.set_color(GREY_D) for i in (2, 4) for m in (ids[i], refs[i])]], 0.7),
            "Unknown drops",
            (lambda: [FadeIn(wh[0]), FadeIn(wh[1]), *[m.animate.set_color(GREY_D) for i in (0, 1) for m in (ids[i], refs[i])]], 0.7),
        ])

        st1 = status("2 rows, and it should be 4", RED_M)
        self.steps("So the query returns customers 4 and 6. Customers 1 and 2 vanish, with no error and no warning.", [
            (lambda: [*[ids[i].animate(rate_func=there_and_back).scale(1.25).set_color(GREEN_M) for i in (3, 5)]], 0.8),
            "Customers 1 and 2",
            (lambda: [FadeIn(st1, shift=0.1 * UP), *[refs[i].animate.set_color(PURPLE_M) for i in (0, 1)]], 0.7),
        ])

        q2b = q("WHERE referred_by <> 1 OR referred_by IS NULL", 1)
        r6 = pl("NULL IS NULL   true", 3, GREEN_M)
        st2 = status("4 rows: 1, 2, 4 and 6", GREEN_M)
        self.steps("Say what you mean instead: not equal to 1, or IS NULL. IS NULL is always true or false, "
                   "never unknown, so customers 1 and 2 come back.", [
            (lambda: [FadeOut(st1), FadeOut(q2), FadeIn(q2b)], 0.8),
            "IS NULL is always",
            (lambda: [FadeOut(r4), FadeOut(r5), FadeIn(r6, shift=0.1 * DOWN)], 0.7),
            "so customers",
            (lambda: [*[Transform(tests[i], test("true", i)) for i in (0, 1)],
                      *[Transform(wh[i], where(True, i)) for i in (0, 1)],
                      *[m.animate.set_color(WHITE) for i in (0, 1) for m in (ids[i],)],
                      FadeIn(st2, shift=0.1 * UP)], 0.9),
        ])

        q2c = q("WHERE COALESCE(referred_by, 0) <> 1", 1)
        r7 = pl("COALESCE(NULL, 0)  0", 4, GOLD_M)
        r8 = pl("0 <> 1              true", 5, GREEN_M)
        self.steps("COALESCE does the same job another way. It swaps a NULL for a value you pick, here 0, and 0 is not 1.", [
            (lambda: [FadeOut(q2b), FadeIn(q2c)], 0.8),
            "It swaps",
            (lambda: [FadeIn(r7, shift=0.1 * DOWN)], 0.6),
            "and 0 is not 1",
            (lambda: [FadeIn(r8, shift=0.1 * DOWN), *[glow_text(tests[i], GREEN_M) for i in (0, 1)]], 0.8),
        ])

        # ---- NOT IN ------------------------------------------------------------------------------------------------
        q2d = q("WHERE customer_id NOT IN (SELECT referred_by FROM customers)", 1)
        lt = ptitle("the list from the subquery")
        lst = pl("NULL, NULL, 1, 2, 1, 3", 0, WHITE, 19)
        self.steps("NOT IN hides the same trap. Which customers referred nobody? "
                   "Ask for each customer_id NOT IN the list of referred_by values. The answer should be 4, 5 and 6.", [
            (lambda: [FadeOut(st2), FadeOut(VGroup(r1, r2, r3, r6, r7, r8)), FadeOut(VGroup(*tests)), FadeOut(VGroup(*wh)),
                      *[m.animate.set_color(WHITE) for i in range(6) for m in (ids[i],)],
                      *[refs[i].animate.set_color(WHITE) for i in range(2, 6)]], 0.8),
            "Ask for each",
            (lambda: [FadeOut(q2c), FadeIn(q2d), Transform(pt, lt)], 0.8),
            (lambda: [FadeIn(lst, shift=0.1 * DOWN)], 0.6),
            "The answer should be",
            (lambda: [*[ids[i].animate(rate_func=there_and_back).scale(1.25).set_color(GREEN_M) for i in (3, 4, 5)]], 0.9),
        ])

        c41 = pl("4 <> 1      true", 1, GREEN_M)
        c42 = pl("4 <> 2      true", 2, GREEN_M)
        c43 = pl("4 <> 3      true", 3, GREEN_M)
        c4n = pl("4 <> NULL   unknown", 4, PURPLE_M)
        c4 = pl("all of them  unknown", 5, PURPLE_M)
        t4 = test("unknown", 3)
        self.steps("NOT IN means different from every value in the list. Customer 4 differs from 1, 2 and 3, "
                   "but against NULL the answer is unknown, and one unknown makes the whole test unknown.", [
            (lambda: [ids[3].animate.set_color(GOLD_M)], 0.5),
            "Customer 4 differs",
            (lambda: [LaggedStart(FadeIn(c41), FadeIn(c42), FadeIn(c43), lag_ratio=0.4)], 1.2),
            "but against NULL",
            (lambda: [FadeIn(c4n)], 0.6),
            "and one unknown",
            (lambda: [FadeIn(c4), FadeIn(t4, shift=0.08 * RIGHT)], 0.7),
        ])

        tn = [test("false", 0), test("false", 1), test("false", 2), t4, test("unknown", 4), test("unknown", 5)]
        wn = [where(False, i) for i in range(6)]
        st3 = status("0 rows, and it should be 3", RED_M)
        self.steps("Customers 1 to 3 are in the list, so they're false. 4 to 6 are unknown. The query returns nothing at all.", [
            (lambda: [ids[3].animate.set_color(WHITE), *[FadeIn(tn[i]) for i in (0, 1, 2)]], 0.7),
            "4 to 6",
            (lambda: [FadeIn(tn[4]), FadeIn(tn[5])], 0.6),
            "The query returns",
            (lambda: [*[FadeIn(w) for w in wn], *[m.animate.set_color(GREY_D) for i in range(6) for m in (ids[i], refs[i])],
                      FadeIn(st3, shift=0.1 * UP)], 0.8),
        ])

        q3 = left_at(M("WHERE referred_by IS NOT NULL)", 22, GOLD_M), QX + 0.19 * 26, QY[2])
        q2e = q("WHERE customer_id NOT IN (SELECT referred_by FROM customers", 1)
        lst2 = pl("1, 2, 1, 3", 0, WHITE, 19)
        st4 = status("3 rows: 4, 5 and 6", GREEN_M)
        self.steps("The fix keeps NULL out of the list: add WHERE referred_by IS NOT NULL inside it. Now 4, 5 and 6 come back.", [
            (lambda: [FadeOut(st3), FadeOut(VGroup(c41, c42, c43, c4n, c4)), FadeOut(q2d), FadeIn(q2e), FadeIn(q3, shift=0.1 * DOWN)], 0.8),
            (lambda: [Transform(lst, lst2)], 0.6),
            "Now 4, 5",
            (lambda: [*[Transform(tn[i], test("true", i)) for i in (3, 4, 5)], *[Transform(wn[i], where(True, i)) for i in (3, 4, 5)],
                      *[m.animate.set_color(WHITE) for i in (3, 4, 5) for m in (ids[i], refs[i])],
                      FadeIn(st4, shift=0.1 * UP)], 0.9),
        ])

        rule = chip("NULL compared with anything is unknown, and WHERE keeps only true", PURPLE_M, 24).move_to([0, ST_Y - 0.68, 0])
        self.steps("A comparison with NULL is unknown, and WHERE keeps only true. "
                   "At every not equal and every NOT IN, ask which side can be NULL.", [
            (lambda: [FadeIn(rule, shift=0.15 * UP)], 0.8),
            "At every",
            (lambda: [glow_text(q3, GOLD_M), *[r.animate(rate_func=there_and_back).scale(1.2) for r in refs[:2]]], 1.0),
        ])
        self.wait(0.6)


def glow_text(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.06)
