from sfz import *

SAY.insert(0, (r"\bGROUP BY\b", "group by"))
SAY.insert(0, (r"\bROLLUP\b", "roll up"))
SAY.insert(0, (r"\bWHERE\b", "where"))
SAY.insert(0, (r"\bHAVING\b", "having"))
SAY.insert(0, (r"\bNULL\b", "null"))

F, QF = 16, 15
Q_Y = [3.28, 2.9]
HDR_Y, RULE_Y = 2.2, 1.95
X_L = -6.5
IN_Y = [1.65 - 0.45 * i for i in range(10)]
X_ID, X_MER, X_AMT_R, X_ST = -6.15, -5.25, -3.6, -3.35       # input table columns
GX, GW, GH = 0.45, 3.8, 0.62                                  # group boxes: centre x, width, height
G_Y = [1.25, 0.35, -0.55, -1.45]
X_OM, X_OC, X_OS_R = 3.55, 4.95, 6.45                        # output: merchant, count (centres), sum (right edge)
X_RC, X_RM = 3.45, 4.75                                       # rollup output: country, merchant (centres)
RO_Y = [1.65 - 0.45 * i for i in range(8)]
LOW_Y = -3.05
SET_Y = -2.3

# the ten March payments in the course seed: id, merchant, amount_minor, status
PAY = [(13, 5, 64000, "succeeded"), (14, 1, 5310, "succeeded"), (15, 4, 89900, "failed"), (16, 5, 31500, "succeeded"),
       (17, 4, 18999, "succeeded"), (18, 4, 18999, "succeeded"), (19, 4, 18999, "succeeded"), (20, 1, 7425, "pending"),
       (21, 7, 1325, "succeeded"), (22, 5, 52000, "succeeded")]
GROUPS = {1: [1], 4: [4, 5, 6], 5: [0, 3, 9], 7: [8]}       # merchant -> input row indexes
G_ORDER = [1, 4, 5, 7]
MC = {1: BLUE_M, 4: GOLD_M, 5: TEAL_M, 7: PURPLE_M}
COUNTRY = {4: "DE", 5: "SG", 1: "US", 7: "US"}
R_ORDER = [4, 5, 1, 7]                                        # group boxes sorted by country for ROLLUP


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def qline(s, k, hl=None):
    return left_at(M(s, QF, t2c=hl or {}), X_L, Q_Y[k])


def in_row(i):
    pid, mer, amt, st = PAY[i]
    y = IN_Y[i]
    return VGroup(M(str(pid), F).move_to([X_ID, y, 0]), M(f"m{mer}", F, MC[mer]).move_to([X_MER, y, 0]),
                  right_at(M(str(amt), F), X_AMT_R, y),
                  left_at(M(st, F, GREY_B if st == "succeeded" else RED_M), X_ST, y))


def slot_x(k):
    return GX - GW / 2 + 1.05 + k * 0.9


def gbox(mer, y):
    r = RoundedRectangle(corner_radius=0.1, width=GW, height=GH, stroke_color=MC[mer], stroke_width=2.5)
    r.set_fill(fillc(MC[mer]), 1).move_to([GX, y, 0])
    lab = M(f"m{mer}", F, MC[mer]).move_to([GX - GW / 2 + 0.38, y, 0])
    return VGroup(r, lab)


def gamt(i, k, y):
    return M(str(PAY[i][2]), F).move_to([slot_x(k), y, 0])


def out_row(mer, y, color=WHITE):
    ids = GROUPS[mer]
    return VGroup(M(f"m{mer}", F, MC[mer]).move_to([X_OM, y, 0]), M(str(len(ids)), F, color).move_to([X_OC, y, 0]),
                  right_at(M(str(sum(PAY[i][2] for i in ids)), F, color), X_OS_R, y))


def ro_row(country, mer, total, k, color=WHITE):
    y = RO_Y[k]
    c = M(country or "NULL", F, WHITE if country else GREY_C).move_to([X_RC, y, 0])
    m = M(f"m{mer}" if mer else "NULL", F, MC[mer] if mer else GREY_C).move_to([X_RM, y, 0])
    return VGroup(c, m, right_at(M(str(total), F, color), X_OS_R, y))


def band(y, color, x0=3.05, x1=6.6):
    return Rectangle(width=x1 - x0, height=0.4, stroke_width=0).set_fill(color, 0.16).move_to([(x0 + x1) / 2, y, 0]).set_z_index(-1)


def swap(old, new):
    """Cross-fade one query line into another (a Transform between different texts scrambles the letters)."""
    return [FadeOut(old), FadeIn(new)]


GX2 = GX - 1.6                                                # group boxes' centre x once ROLLUP starts


class GroupByRollup(Base):
    """sql-04, section 0 (with section 1's WHERE and HAVING and section 3's ROLLUP): the ten March payments. WHERE drops the
    failed and the pending one, GROUP BY merchant_id sorts the other eight into four groups and count and sum fold each into
    one row. sum() in WHERE is refused; HAVING sum > 10000 drops merchants 1 and 7. ROLLUP (country_code, merchant_id) adds a
    subtotal per country and a grand total, 211132, as extra rows."""

    def construct(self):
        self.title_card("GROUP BY, HAVING and ROLLUP", "sort rows into groups, fold each group into one row")

        hdr = VGroup(M("id", F, GREY_B).move_to([X_ID, HDR_Y, 0]), M("merchant", F, GREY_B).move_to([X_MER + 0.15, HDR_Y, 0]),
                     right_at(M("amount", F, GREY_B), X_AMT_R, HDR_Y), left_at(M("status", F, GREY_B), X_ST, HDR_Y))
        hdr[1].move_to([X_MER, HDR_Y, 0])
        rule = Line([X_L, RULE_Y, 0], [X_ST + 1.25, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        R = [in_row(i) for i in range(10)]
        self.steps("Finance wants each merchant's volume for March. Here are March's ten payments, at four merchants.", [
            (lambda: [FadeIn(hdr), Create(rule)], 0.6),
            "Here are",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in R], lag_ratio=0.12)], 1.8),
            "at four merchants",
            (lambda: [*[Indicate(r[1], color=MC[PAY[i][1]]) for i, r in enumerate(R)]], 0.8),
        ])

        kt = mbox("Kotlin service", GREY_B, w=2.6, h=0.8, size=F).move_to([4.6, 0.2, 0])
        pipe = Arrow([X_ST + 1.4, 0.2, 0], kt.get_left() + 0.1 * LEFT, buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.05)
        big = chip("large data set: 1,000,000 rows shipped to make 2,500 sums", RED_M, 20).move_to([2.1, -1.3, 0])
        self.steps("You could send every row to Kotlin and add them up there. "
                   "On the large data set, that ships a million rows to compute 2,500 numbers.", [
            (lambda: [FadeIn(kt), GrowArrow(pipe)], 0.7),
            (lambda: [LaggedStart(*[travel(pipe, GREY_A, 0.6) for _ in range(6)], lag_ratio=0.25)], 1.6),
            "On the large",
            (lambda: [FadeIn(big, shift=0.1 * UP)], 0.7),
            (lambda: [LaggedStart(*[travel(pipe, RED_M, 0.5) for _ in range(10)], lag_ratio=0.15)], 1.6),
        ])

        q1 = qline("SELECT merchant_id, count(*), sum(amount_minor) FROM payments", 0)
        q2 = qline("WHERE <March> AND status = 'succeeded' GROUP BY merchant_id", 1,
                   {"WHERE <March> AND status = 'succeeded'": YELLOW_M})
        drop = [2, 7]
        self.steps("Let the database add them up where the data lives. "
                   "First, WHERE looks at one row at a time, and drops the failed and the pending payment.", [
            (lambda: [FadeOut(VGroup(kt, pipe, big)), FadeIn(q1, shift=0.1 * DOWN), FadeIn(q2, shift=0.1 * DOWN)], 0.9),
            "First, WHERE",
            (lambda: [LaggedStart(*[Indicate(r[3], color=YELLOW_M) for r in R], lag_ratio=0.08)], 1.4),
            "and drops",
            (lambda: [*[R[i].animate.set_opacity(0.25) for i in drop]], 0.7),
        ])

        gb = {m: gbox(m, G_Y[k]) for k, m in enumerate(G_ORDER)}
        gtitle = T("groups", 20, GREY_B).move_to([GX, HDR_Y, 0])
        gtitle2 = T("groups", 20, GREY_B).move_to([GX2, HDR_Y, 0])
        GA = {}
        for k, m in enumerate(G_ORDER):
            for j, i in enumerate(GROUPS[m]):
                GA[i] = gamt(i, j, G_Y[k])
        q2b = qline("WHERE <March> AND status = 'succeeded' GROUP BY merchant_id", 1, {"GROUP BY merchant_id": YELLOW_M})
        live = [i for i in range(10) if i not in drop]
        self.steps("GROUP BY merchant sorts the rest into piles, one for each merchant. Eight rows make four groups.", [
            (lambda: [Transform(q2, q2b), FadeIn(gtitle), LaggedStart(*[FadeIn(gb[m], shift=0.1 * RIGHT) for m in G_ORDER],
                                                                        lag_ratio=0.15)], 1.0),
            (lambda: [LaggedStart(*[ReplacementTransform(R[i][2].copy(), GA[i]) for i in live], lag_ratio=0.12)], 2.0),
            "Eight rows make",
            (lambda: [*[glow(gb[m][0], MC[m], 1.03) for m in G_ORDER]], 0.9),
        ])

        ohdr = VGroup(M("merchant_id", F, GREY_B).move_to([X_OM, HDR_Y, 0]), M("count", F, GREY_B).move_to([X_OC, HDR_Y, 0]),
                      right_at(M("sum", F, GREY_B), X_OS_R, HDR_Y))
        orule = Line([2.75, RULE_Y, 0], [X_OS_R, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        OUT = {m: out_row(m, G_Y[k]) for k, m in enumerate(G_ORDER)}

        def fold(m):
            o = OUT[m]
            return [FadeIn(o[0]), FadeIn(o[1], shift=0.1 * RIGHT),
                    *[Transform(GA[i].copy(), o[2].copy(), remover=True) for i in GROUPS[m]], FadeIn(o[2], run_time=1.0,
                                                                                                   rate_func=squish_rate_func(smooth, 0.6, 1))]
        q1b = qline("SELECT merchant_id, count(*), sum(amount_minor) FROM payments", 0,
                    {"count(*)": YELLOW_M, "sum(amount_minor)": YELLOW_M})
        self.steps("Then each aggregate folds a pile into one value. Count counts its rows, and sum adds them up. "
                   "Four groups give four output rows.", [
            (lambda: [Transform(q1, q1b), Transform(q2, qline("WHERE <March> AND status = 'succeeded' GROUP BY merchant_id", 1)),
                      FadeIn(ohdr), Create(orule)], 0.8),
            "Count counts",
            (lambda: [*fold(4)], 1.0),
            (lambda: [*fold(5)], 0.9),
            "Four groups",
            (lambda: [*fold(1), *fold(7)], 0.9),
        ])

        qbad = qline("WHERE <March> AND sum(amount_minor) > 10000 GROUP BY merchant_id", 1, {"sum(amount_minor) > 10000": RED_M})
        err = chip("ERROR: aggregate functions are not allowed in WHERE", RED_M, 20).move_to([2.2, LOW_Y, 0])
        self.steps("Risk only wants merchants whose sum passes 10,000. Put the sum in the WHERE, and PostgreSQL refuses. "
                   "WHERE runs before any group exists, so there's nothing to add up yet.", [
            (lambda: [Transform(q1, qline("SELECT merchant_id, count(*), sum(amount_minor) FROM payments", 0))], 0.4),
            "Put the sum",
            (lambda: swap(q2, qbad), 0.7),
            "and PostgreSQL refuses",
            (lambda: [FadeIn(err, shift=0.1 * UP)], 0.6),
            "WHERE runs before",
            (lambda: [*[glow(gb[m][0], GREY_B, 1.02) for m in G_ORDER]], 0.9),
        ])

        qhav = qline("WHERE <March> AND status = 'succeeded' GROUP BY merchant_id HAVING sum(amount_minor) > 10000", 1,
                     {"HAVING sum(amount_minor) > 10000": GREEN_M})
        xs = {m: tick(False, 0.13).move_to([X_OS_R + 0.0, G_Y[G_ORDER.index(m)] - 0.3, 0]) for m in (1, 7)}
        for m in xs:
            xs[m].move_to([2.62, G_Y[G_ORDER.index(m)], 0])
        oks = {m: tick(True, 0.13).move_to([2.62, G_Y[G_ORDER.index(m)], 0]) for m in (4, 5)}
        self.steps("HAVING is the same kind of filter, one step later. It tests the folded rows, so merchants 1 and 7 drop out.", [
            (lambda: [FadeOut(err), *swap(qbad, qhav)], 0.8),
            "It tests",
            (lambda: [*[Indicate(OUT[m][2], color=GREEN_M) for m in G_ORDER]], 0.9),
            "so merchants 1 and 7",
            (lambda: [*[Create(x) for x in xs.values()], *[Create(o) for o in oks.values()]], 0.5),
            (lambda: [OUT[1].animate.set_opacity(0.25), OUT[7].animate.set_opacity(0.25)], 0.6),
        ])

        cw = chip("WHERE: rows, before grouping", YELLOW_M, 20).move_to([-4.3, LOW_Y, 0])
        ch = chip("HAVING: groups, after folding", GREEN_M, 20).move_to([4.5, LOW_Y, 0])
        self.steps("So WHERE decides which rows go into the piles, and HAVING decides which piles come out.", [
            (lambda: [FadeIn(cw, shift=0.1 * UP), *[Indicate(R[i][3], color=RED_M) for i in drop]], 1.0),
            "and HAVING",
            (lambda: [FadeIn(ch, shift=0.1 * UP), glow(gb[1][0], RED_M, 1.03), glow(gb[7][0], RED_M, 1.03)], 1.0),
        ])

        # ---- ROLLUP --------------------------------------------------------------------------------------------------
        q2plain = qline("WHERE <March> AND status = 'succeeded' GROUP BY merchant_id", 1)
        three = chip("3 queries glued with UNION ALL: payments read 3 times", RED_M, 20).move_to([0, LOW_Y, 0])
        self.steps("Finance also wants a total per country, and a grand total. "
                   "Three GROUP BY queries glued together would read the payments three times.", [
            (lambda: [FadeOut(VGroup(cw, ch, *xs.values(), *oks.values())), FadeOut(VGroup(*OUT.values())),
                      FadeOut(VGroup(*R, hdr, rule)),
                      *swap(qhav, q2plain)], 1.0),
            "Three GROUP BY",
            (lambda: [FadeIn(three, shift=0.1 * UP)], 0.7),
        ])

        r1 = qline("SELECT country_code, merchant_id, sum(amount_minor) FROM payments JOIN merchants ...", 0)
        r2 = qline("WHERE <March> AND status = 'succeeded' GROUP BY ROLLUP (country_code, merchant_id)", 1,
                   {"ROLLUP (country_code, merchant_id)": GOLD_M})
        sets_t = left_at(T("grouping sets:", 20, GREY_B), X_L, SET_Y)
        sets = [left_at(M(s, F, GREY_B), x, SET_Y) for x, s in
                zip([-4.7, -0.6, 1.8], ["(country_code, merchant_id)", "(country_code)", "()"])]
        rhdr = VGroup(M("country", F, GREY_B).move_to([X_RC, HDR_Y, 0]), M("merchant", F, GREY_B).move_to([X_RM, HDR_Y, 0]),
                      right_at(M("sum", F, GREY_B), X_OS_R, HDR_Y))
        flags = {}
        for k, m in enumerate(R_ORDER):
            flags[m] = M(COUNTRY[m], F, WHITE).move_to([GX2 - GW / 2 - 0.4, G_Y[k], 0])
        tot = {m: sum(PAY[i][2] for i in GROUPS[m]) for m in G_ORDER}
        RO = [ro_row(COUNTRY[m], m, tot[m], k) for k, m in enumerate(R_ORDER)]

        def reorder():
            an = []
            for k, m in enumerate(R_ORDER):
                d = (G_Y[k] - G_Y[G_ORDER.index(m)]) * UP + (GX2 - GX) * RIGHT
                an.append(gb[m].animate.shift(d))
                an += [GA[i].animate.shift(d) for i in GROUPS[m]]
            return an

        self.steps("ROLLUP of country and merchant lists three groupings in one GROUP BY. "
                   "The first is country and merchant: the same four groups, now sorted by country.", [
            (lambda: [FadeOut(three), *swap(q1, r1), *swap(q2plain, r2)], 0.9),
            "lists three",
            (lambda: [FadeIn(sets_t), LaggedStart(*[FadeIn(s, shift=0.1 * RIGHT) for s in sets], lag_ratio=0.3)], 1.0),
            "The first is",
            (lambda: [sets[0].animate.set_color(WHITE), *reorder(), gtitle.animate.move_to(gtitle2)], 1.0),
            (lambda: [*[FadeIn(f, shift=0.1 * RIGHT) for f in flags.values()], Transform(ohdr, rhdr)], 0.6),
            "now sorted",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in RO], lag_ratio=0.2)], 1.0),
        ])

        def brace_for(ks, color):
            top, bot = G_Y[ks[0]] + GH / 2, G_Y[ks[-1]] - GH / 2
            x = GX2 + GW / 2 + 0.15
            return VGroup(Line([x, top, 0], [x + 0.12, top, 0]), Line([x + 0.12, top, 0], [x + 0.12, bot, 0]),
                          Line([x, bot, 0], [x + 0.12, bot, 0])).set_stroke(color, 2.5)

        subs = [("DE", 56997, [0]), ("SG", 147500, [1]), ("US", 6635, [2, 3])]
        SUB = [ro_row(c, None, v, 4 + j, GOLD_M) for j, (c, v, _) in enumerate(subs)]
        bands = [band(RO_Y[4 + j], GOLD_M) for j in range(3)]
        braces = [brace_for(ks, GOLD_M) for _, _, ks in subs]
        self.steps("The second set is country alone. Each country's groups fold into one subtotal row, "
                   "with NULL where the merchant was.", [
            (lambda: [sets[0].animate.set_color(GREY_B), sets[1].animate.set_color(GOLD_M)], 0.6),
            "Each country's",
            (lambda: [*[Create(b) for b in braces]], 0.7),
            (lambda: [*[FadeIn(b) for b in bands],
                      *[Transform(RO[k][2].copy(), SUB[j][2].copy(), remover=True) for j, (_, _, ks) in enumerate(subs) for k in ks],
                      *[FadeIn(s, rate_func=squish_rate_func(smooth, 0.5, 1)) for s in SUB]], 1.2),
            "with NULL",
            (lambda: [*[Indicate(s[1], color=GREY_A) for s in SUB]], 0.8),
        ])

        x = GX2 + GW / 2 + 0.45
        allb = VGroup(Line([x, G_Y[0] + GH / 2, 0], [x + 0.12, G_Y[0] + GH / 2, 0]),
                      Line([x + 0.12, G_Y[0] + GH / 2, 0], [x + 0.12, G_Y[3] - GH / 2, 0]),
                      Line([x, G_Y[3] - GH / 2, 0], [x + 0.12, G_Y[3] - GH / 2, 0])).set_stroke(PURPLE_M, 2.5)
        GT = ro_row(None, None, 211132, 7, PURPLE_M)
        gband = band(RO_Y[7], PURPLE_M)
        self.steps("The last set is empty: one group that holds every row. That's the grand total.", [
            (lambda: [sets[1].animate.set_color(GREY_B), sets[2].animate.set_color(PURPLE_M)], 0.6),
            "one group",
            (lambda: [Create(allb)], 0.7),
            "That's the grand",
            (lambda: [FadeIn(gband), *[Transform(s[2].copy(), GT[2].copy(), remover=True) for s in SUB],
                      FadeIn(GT, rate_func=squish_rate_func(smooth, 0.5, 1))], 1.1),
        ])

        cnt = chip("4 merchant rows + 3 subtotals + 1 grand total", GOLD_M, 20).move_to([0.8, LOW_Y, 0])
        self.steps("Eight rows in all: four merchants, three subtotals and one grand total, from one query.", [
            (lambda: [LaggedStart(*[Indicate(r, color=WHITE, scale_factor=1.0) for r in RO], lag_ratio=0.1)], 0.9),
            "three subtotals",
            (lambda: [*[glow(b, GOLD_M, 1.0) for b in bands]], 0.7),
            "one grand total",
            (lambda: [glow(gband, PURPLE_M, 1.0), FadeIn(cnt, shift=0.1 * UP)], 0.8),
        ])

        self.steps("Sort the rows into groups by key, and fold each group into one row. "
                   "WHERE filters rows before the grouping, and HAVING filters groups after it.", [
            (lambda: [FadeOut(cnt), *[glow(gb[m][0], MC[m], 1.03) for m in G_ORDER]], 1.0),
            "and fold",
            (lambda: [*[Indicate(r[2], color=YELLOW_M) for r in RO]], 0.9),
            "WHERE filters",
            (lambda: [Indicate(r2, color=YELLOW_M, scale_factor=1.0)], 1.0),
        ])
        self.wait(0.6)
