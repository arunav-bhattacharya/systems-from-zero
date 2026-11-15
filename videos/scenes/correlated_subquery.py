from sfz import *

SAY.insert(0, (r"\b(GROUP BY|EXISTS|IN)\b", lambda m: m.group(1).lower()))

QX, QY = -6.3, [3.25, 2.87]                  # the query
HEAD_Y = 2.2
ROW_Y = [1.65, 1.1, 0.55, 0.0, -0.55, -1.1]
CX_ID, CX_M, AMT_R, CX_V = -5.95, -4.0, -1.05, 0.1
PX, PW, PY, PH = 3.8, 5.5, 0.2, 4.2          # right panel
PL_Y = [1.25, 0.72, 0.19, -0.34]
CNT_Y = [-1.0, -1.45]
ST_Y = -2.35
ROWS = [(3, "Volt Electronics", 129900, 48621), (4, "Metro Transit", 275, 344), (9, "Metro Transit", 275, 344),
        (17, "Volt Electronics", 18999, 48621), (31, "Volt Electronics", 75000, 48621), (32, "Metro Transit", 550, 344)]
GLOBAL = 24015


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
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


def q(s, k, color=WHITE):
    return left_at(M(s, 20, color), QX, QY[k])


def fmt(n):
    return f"{n:,}"


def verdict(s, k, color):
    return T(s, 24, color).move_to([CX_V, ROW_Y[k], 0])


def pline(s, k, color=WHITE, mono=False, size=24):
    return left_at((M(s, size - 2, color) if mono else T(s, size, color)), PX - PW / 2 + 0.3, PL_Y[k])


def ptitle(s, color=GREY_B):
    return T(s, 24, color).move_to([PX, PY + PH / 2 - 0.38, 0])


def counter(s, k, color=GREY_B):
    return left_at(M(s, 21, color), PX - PW / 2 + 0.3, CNT_Y[k])


def status(s, color=GREY_B):
    return T(s, 28, color).move_to([0, ST_Y, 0])


def hl(k, color=YELLOW_M):
    return Rectangle(width=6.95, height=0.5, stroke_color=color, stroke_width=2.5).move_to([-2.85, ROW_Y[k], 0])


class CorrelatedSubquery(Base):
    """sql-05, section 1: payments larger than their own merchant's average. The global average (24,015) misses Metro
    Transit's 550. The correlated subquery runs once per outer row (37 rows read each time; 30 runs, 1,110 rows, six
    answers); on the large data set 51 ms a run, about 13 hours. GROUP BY once plus a join: 282 ms. PostgreSQL decorrelates
    EXISTS and IN on its own, not an aggregate."""

    def construct(self):
        self.title_card("Correlated subqueries", "a query inside a query, run again for every row")

        heads = VGroup(M("id", 20, GREY_B).move_to([CX_ID, HEAD_Y, 0]), T("merchant", 22, GREY_B).move_to([CX_M, HEAD_Y, 0]),
                       right_at(M("amount", 20, GREY_B), AMT_R, HEAD_Y), T("flag?", 22, GREY_B).move_to([CX_V, HEAD_Y, 0]))
        hline = Line([-6.4, HEAD_Y - 0.28, 0], [0.7, HEAD_Y - 0.28, 0], stroke_width=1.5, color=GREY_D)
        mcol = {"Volt Electronics": BLUE_M, "Metro Transit": TEAL_M}
        rows = [VGroup(M(str(i), 24).move_to([CX_ID, ROW_Y[k], 0]), T(m, 24, mcol[m]).move_to([CX_M, ROW_Y[k], 0]),
                       right_at(M(fmt(a), 24), AMT_R, ROW_Y[k])) for k, (i, m, a, _) in enumerate(ROWS)]
        more = T("and 24 more succeeded payments", 20, GREY_C).move_to([-2.85, -1.6, 0])
        self.steps("Risk wants payments that are large for their own merchant. 550 cents is tiny for Volt Electronics, "
                   "but twice a Metro Transit fare of 275.", [
            (lambda: [FadeIn(heads), Create(hline)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.08 * RIGHT) for r in rows], lag_ratio=0.15), FadeIn(more)], 1.3),
            "550 cents",
            (lambda: [rows[5][2].animate.set_color(GOLD_M).scale(1.15)], 0.6),
            "but twice",
            (lambda: [*[rows[k][2].animate(rate_func=there_and_back).set_color(TEAL_M).scale(1.15) for k in (1, 2)]], 0.9),
        ])

        qg = q(f"WHERE p.amount_minor > (SELECT avg(amount_minor) FROM payments)", 0)
        panel = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=GREY_B, stroke_width=2.5)
        panel.set_fill(BLACK, 1).move_to([PX, PY, 0])
        pt = ptitle("the average of all payments")
        gavg = pline("avg = 24,015", 0, WHITE, mono=True, size=28)
        vg = [verdict("yes" if a > GLOBAL else "no", k, GOLD_M if a > GLOBAL else GREY_C) for k, (_, _, a, _) in enumerate(ROWS)]
        miss = verdict("missed", 5, RED_M)
        st1 = status("Metro's 550 is twice its usual fare, and it isn't flagged", RED_M)
        self.steps("Comparing with the average of all payments, 24,015, misses it. "
                   "Metro's 550 is never flagged.", [
            (lambda: [rows[5][2].animate.set_color(WHITE).scale(1 / 1.15), FadeIn(qg), FadeIn(panel), FadeIn(pt)], 0.7),
            (lambda: [FadeIn(gavg)], 0.5),
            "misses it",
            (lambda: [LaggedStart(*[FadeIn(v) for v in vg], lag_ratio=0.2)], 1.2),
            "Metro's 550",
            (lambda: [Transform(vg[5], miss), FadeIn(st1, shift=0.1 * UP)], 0.7),
        ])

        q1 = q("WHERE p.amount_minor > (SELECT avg(p2.amount_minor) FROM payments p2", 0)
        q2a = left_at(M("WHERE p2.merchant_id =", 20), QX + 24 * 0.172, QY[1])
        q2b = left_at(M("p.merchant_id", 20, GOLD_M), q2a.get_right()[0] + 0.2, QY[1])
        q2c = left_at(M(")", 20), q2b.get_right()[0] + 0.02, QY[1])
        self.steps("So the subquery must use the outer row: average only this row's merchant. "
                   "A subquery that refers to the outer row is correlated.", [
            (lambda: [FadeOut(st1), FadeOut(VGroup(*vg)), FadeOut(gavg), FadeOut(qg), FadeIn(q1)], 0.7),
            "average only",
            (lambda: [FadeIn(q2a), FadeIn(q2b), FadeIn(q2c)], 0.7),
            "is correlated",
            (lambda: [q2b.animate(rate_func=there_and_back).scale(1.2)], 0.8),
        ])

        box = hl(0)
        runs = counter("subquery runs: 0", 0)
        read = counter("payment rows read: 0", 1)
        l1 = pline("merchant = Volt Electronics", 0, BLUE_M)
        l2 = pline("reads all 37 payments, keeps 7", 1, GREY_B)
        l3 = pline("avg = 48,621", 2, WHITE, mono=True, size=28)
        l4 = pline("129,900 > 48,621: flagged", 3, GOLD_M)
        v = [None] * 6
        v[0] = verdict("yes", 0, GOLD_M)
        self.steps("It can't run until there's an outer row, so it runs once per row. For payment 3, it reads all 37 "
                   "payments, keeps Volt's seven, and averages them: 48,621. 129,900 is above, so it's flagged.", [
            (lambda: [Transform(pt, ptitle("the subquery, run for payment 3", YELLOW_M)), FadeIn(runs), FadeIn(read)], 0.7),
            "so it runs once",
            (lambda: [Create(box)], 0.5),
            "For payment 3",
            (lambda: [FadeIn(l1)], 0.5),
            "it reads all 37",
            (lambda: [FadeIn(l2), Transform(runs, counter("subquery runs: 1", 0, YELLOW_M)),
                      Transform(read, counter("payment rows read: 37", 1, YELLOW_M))], 0.7),
            "and averages them",
            (lambda: [FadeIn(l3)], 0.5),
            "129,900 is above",
            (lambda: [FadeIn(l4), FadeIn(v[0])], 0.6),
        ])

        def run_row(k, n, color):
            i, m, a, avg = ROWS[k]
            ok = a > avg
            return [box.animate.move_to([-2.85, ROW_Y[k], 0]),
                    Transform(pt, ptitle(f"the subquery, run for payment {i}", YELLOW_M)),
                    Transform(l1, pline(f"merchant = {m}", 0, mcol[m])),
                    Transform(l2, pline(f"reads all 37 payments, keeps {7 if avg == 48621 else 4}", 1, GREY_B)),
                    Transform(l3, pline(f"avg = {fmt(avg)}", 2, color, mono=True, size=28)),
                    Transform(l4, pline(f"{fmt(a)} {'>' if ok else '<'} {fmt(avg)}: {'flagged' if ok else 'not flagged'}", 3,
                                        GOLD_M if ok else GREY_B)),
                    Transform(runs, counter(f"subquery runs: {n}", 0, YELLOW_M)),
                    Transform(read, counter(f"payment rows read: {37 * n}", 1, YELLOW_M))]

        v[1] = verdict("no", 1, GREY_C)
        self.steps("Payment 4 is Metro's. The subquery runs again from scratch: average 344, and 275 is below.", [
            (lambda: run_row(1, 2, WHITE), 0.9),
            "average 344",
            (lambda: [glow_text(l3, YELLOW_M)], 0.6),
            "and 275",
            (lambda: [FadeIn(v[1])], 0.5),
        ])

        v[2] = verdict("no", 2, GREY_C)
        self.steps("Payment 9 is Metro's too, and it computes the same 344 all over again.", [
            (lambda: run_row(2, 3, RED_M), 0.9),
            "the same 344",
            (lambda: [glow_text(l3, RED_M), FadeIn(v[2])], 0.8),
        ])

        for k in (3, 4, 5):
            ok = ROWS[k][2] > ROWS[k][3]
            v[k] = verdict("yes" if ok else "no", k, GOLD_M if ok else GREY_C)
        st2 = status("30 runs and 1,110 rows read, for 6 different answers", RED_M)
        self.steps("After all 30 payments: 30 runs and 1,110 rows read, for six different answers.", [
            (lambda: run_row(3, 4, WHITE) + [FadeIn(v[3])], 0.5),
            (lambda: run_row(4, 5, WHITE) + [FadeIn(v[4])], 0.5),
            (lambda: run_row(5, 6, WHITE) + [FadeIn(v[5])], 0.5),
            (lambda: [FadeOut(box), Transform(runs, counter("subquery runs: 30", 0, RED_M)),
                      Transform(read, counter("payment rows read: 1,110", 1, RED_M))], 0.7),
            "for six",
            (lambda: [FadeIn(st2, shift=0.1 * UP)], 0.6),
        ])

        big1 = pline("large data set: 51 ms a run", 0, WHITE)
        big2 = pline("930,826 payments", 1, WHITE)
        big3 = pline("about 13 hours", 2, RED_M, size=30)
        self.steps("On the large data set, one run takes 51 milliseconds, and there are 930,826 payments: about 13 hours.", [
            (lambda: [FadeOut(st2), FadeOut(VGroup(l1, l2, l3, l4)), Transform(pt, ptitle("a million payments")),
                      FadeIn(big1)], 0.8),
            "and there are",
            (lambda: [FadeIn(big2), Transform(runs, counter("subquery runs: 930,826", 0, RED_M)),
                      FadeOut(read)], 0.7),
            "about 13 hours",
            (lambda: [FadeIn(big3, scale=1.2)], 0.6),
        ])

        # ---- the join: averages once ---------------------------------------------------------------------------------
        j1 = q("JOIN (SELECT merchant_id, avg(amount_minor) AS avg_minor FROM payments", 0)
        j2 = left_at(M("GROUP BY merchant_id) a ON a.merchant_id = p.merchant_id", 20), QX + 6 * 0.172, QY[1])
        avgs = ["1: 4,705", "2: 1,935", "3 Metro: 344", "4 Volt: 48,621", "5: 55,917", "7: 1,498"]
        acol = {2: TEAL_M, 3: BLUE_M}
        at = VGroup(*[left_at(M(a, 21, acol.get(k, WHITE)), PX - PW / 2 + 0.3 + (2.55 if k >= 3 else 0),
                              PL_Y[1 + k % 3]) for k, a in enumerate(avgs)])
        ahead = pline("merchant: average", 0, GREY_B, size=22)
        self.steps("Turn it around. One pass with GROUP BY computes every merchant's average once.", [
            (lambda: [FadeOut(VGroup(big1, big2, big3)), FadeOut(VGroup(q1, q2a, q2b, q2c)), FadeIn(j1), FadeIn(j2),
                      FadeOut(VGroup(*[x for x in v if x is not None])), FadeOut(runs),
                      Transform(pt, ptitle("averages, computed once", GREEN_M)), panel.animate.set_stroke(GREEN_M)], 0.9),
            "One pass",
            (lambda: [FadeIn(ahead), LaggedStart(*[FadeIn(a, shift=0.08 * DOWN) for a in at], lag_ratio=0.2)], 1.3),
        ])

        vj = [verdict("yes" if a > avg else "no", k, GOLD_M if a > avg else GREY_C) for k, (_, _, a, avg) in enumerate(ROWS)]
        fast = chip("2 passes: 282 ms, not 13 hours", GREEN_M, 24).move_to([PX, CNT_Y[0] - 0.2, 0])
        self.steps("A second pass joins each payment to its merchant's average: 282 milliseconds instead of 13 hours.", [
            (lambda: [*[rows[k][1].animate(rate_func=there_and_back).scale(1.15) for k in (0, 3, 4)],
                      at[3].animate(rate_func=there_and_back).scale(1.15)], 0.8),
            (lambda: [*[rows[k][1].animate(rate_func=there_and_back).scale(1.15) for k in (1, 2, 5)],
                      at[2].animate(rate_func=there_and_back).scale(1.15)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(x) for x in vj], lag_ratio=0.15)], 0.8),
            "282 milliseconds",
            (lambda: [FadeIn(fast, shift=0.1 * UP)], 0.7),
        ])

        st3 = status("PostgreSQL rewrites EXISTS and IN into joins, not an aggregate", GREY_B)
        self.steps("Some planners do this rewrite on their own. PostgreSQL does it for EXISTS and IN, "
                   "but not for an average, so you write the join yourself.", [
            (lambda: [glow(panel, GREEN_M, 1.02)], 0.9),
            "PostgreSQL does it",
            (lambda: [FadeIn(st3, shift=0.1 * UP)], 0.7),
            "so you write",
            (lambda: [glow_text(j2, GOLD_M)], 0.9),
        ])

        rule = chip("compute the per-merchant answer once, then join to it", GREEN_M, 26).move_to([0, ST_Y - 0.7, 0])
        self.steps("A subquery that names the outer row runs once per row. "
                   "Compute the per-merchant answer once, and join to it.", [
            (lambda: [FadeOut(st3), *[r.animate(rate_func=there_and_back).set_color(YELLOW_M) for r in rows]], 1.0),
            "Compute the",
            (lambda: [FadeIn(rule, shift=0.15 * UP)], 0.8),
        ])
        self.wait(0.6)


def glow_text(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.06)
