from sfz import *

# Kokoro drops the possessive after a digit ("shop 5's" came out as "shop five"); say the number as a word.
SAY.insert(0, (r"\b([1-9])'s\b", lambda m: "one two three four five six seven eight nine".split()[int(m.group(1)) - 1] + "'s"))

SAY.insert(0, (r"\bGROUP BY\b", "group by"))
SAY.insert(0, (r"\bsubqueries\b", "sub queries"))   # Kokoro said "subgears"
SAY.insert(0, (r"\bNOT EXISTS\b", "not exists"))
SAY.insert(0, (r"\bEXISTS\b", "exists"))
SAY.insert(0, (r"\bIN\b", "in"))
SAY.insert(0, (r"\bEXPLAIN\b", "explain"))
SAY.insert(0, (r"\bSubPlan\b", "sub plan"))
SAY.insert(0, (r"\bmerchant_id\b", "merchant I D"))
SAY.insert(0, (r"\b5\.50\b", "five fifty"))
SAY.insert(0, (r"\b2\.75\b", "two seventy-five"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_Y = [3.33, 3.0]
TITLE_Y = 2.55
OX, OW, OH = -5.05, 2.8, 0.44                     # the outer rows: the guests
OY = [2.0, 1.45, 0.9, 0.35, -0.2]
POT_X0, POT_X1, POT_TOP, POT_BOT = -2.95, -0.75, 2.2, -2.0   # the pot: payments p2, one stripe per payment
SY = [2.05 - 0.11 * i for i in range(37)]
PX = 0.25                                         # the panel: what this run did
PY = [2.0, 1.45, 0.9, 0.35]
CY = [-0.6, -1.15]
CAP_Y = -3.25

OUTER = [(1, 1, 4250), (2, 2, 1890), (3, 4, 129900), (4, 3, 275), (5, 5, 48000)]
# the real succeeded payments of each shop in the seed (payment_id - 1 = stripe)
KEPT = {1: [0, 6, 10, 13, 23, 28, 33], 2: [1, 24, 29], 4: [2, 7, 16, 17, 18, 27, 30]}
AVGS = [("m1", "4705"), ("m2", "1935"), ("m3", "344"), ("m4", "48621"), ("m5", "55917"), ("m7", "1498")]
CARD_OF = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 7: 5}


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
        new = VGroup(*[M(s, 16, color, t2c={"p.merchant_id": YELLOW_M}).move_to([0, Q_Y[i], 0]) for i, s in enumerate(lines)])
        old, self.qm = self.qm, new
        return [swap(old, new)]

    def panel(self, k, s, color=WHITE, mono=True, size=20):
        new = left_at((M if mono else T)(s, size if mono else size + 2, color), PX, PY[k])
        old, self.pm[k] = self.pm[k], new
        return [swap(old, new, RIGHT)]

    def clear_lines(self, ks):
        an = []
        for k in ks:
            if self.pm[k] is not None:
                an.append(FadeOut(self.pm[k]))
                self.pm[k] = None
        return an

    def clear_panel(self):
        olds = [m for m in self.pm if m is not None]
        self.pm = [None] * 4
        return [FadeOut(m) for m in olds]

    def counter(self, k, s, color=WHITE):
        new = left_at(T(s, 24, color), PX, CY[k])
        old, self.cm[k] = self.cm[k], new
        return [swap(old, new)]

    def countdown(self, c=(0, -2.65), secs=3.0):
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
def outer_row(p, m, a, y, color=BLUE_M):
    x0 = OX - OW / 2 + 0.2
    t = VGroup(left_at(M(str(p), 18), x0, y), left_at(M(f"m{m}", 18, GOLD_M), x0 + 0.55, y), right_at(M(str(a), 18), OX + OW / 2 - 0.2, y))
    r = RoundedRectangle(corner_radius=0.08, width=OW, height=OH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1).move_to([OX, y, 0])
    return VGroup(r, t)


def pot():
    body = RoundedRectangle(corner_radius=0.14, width=POT_X1 - POT_X0, height=POT_TOP - POT_BOT, stroke_color=GREY_B, stroke_width=3)
    body.set_fill("#101010", 1).move_to([(POT_X0 + POT_X1) / 2, (POT_TOP + POT_BOT) / 2, 0]).set_z_index(-1)
    stripes = VGroup(*[Line([POT_X0 + 0.2, y, 0], [POT_X1 - 0.2, y, 0], stroke_width=3, color=GREY_D) for y in SY])
    return body, stripes


def sweep_line():
    return Line([POT_X0 + 0.08, POT_TOP - 0.08, 0], [POT_X1 - 0.08, POT_TOP - 0.08, 0], stroke_width=5, color=YELLOW_M)


def walk(k):
    y = OY[k]
    return Arrow([OX + OW / 2 + 0.06, y, 0], [POT_X0 - 0.06, y, 0], buff=0, stroke_width=3, color=YELLOW_M, max_tip_length_to_length_ratio=0.3)


def card(i, color=TEAL_M):
    key, v = AVGS[i]
    t = VGroup(M(key, 20, GOLD_M), M(v, 20)).arrange(RIGHT, buff=0.25)
    r = RoundedRectangle(corner_radius=0.1, width=1.95, height=0.58, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    g = VGroup(r, t.move_to(r))
    col, row = i % 3, i // 3
    return g.move_to([PX + 1.0 + col * 2.1, 1.55 - row * 0.8, 0])


class CorrelatedSubquery(Base):
    """sql-05, section 1. Which payments are bigger than their own shop's average? The query reads like the question and
    would take about 13 hours on a million payments. The subquery needs the outer row's shop, so it runs once per row:
    the kitchen's cook who walks to the pot for every guest. Rows 1, 2, 3 (the stepper), then 30 runs and 1,110 rows read
    for 6 answers; 51 ms a run on the large data set. Correlated, SubPlan. The fix: every shop's average once (GROUP BY,
    a hash table), then one lookup per payment: 74 rows, 282 ms. When it's fine, the alias trap, the moral, a check."""

    def construct(self):
        self.capm = self.qm = None
        self.pm = [None] * 4
        self.cm = [None, None]
        self.title_card("Thirteen hours for one question", "a subquery that runs once per row")

        # ---------------- scene 1: the question ----------------
        c1 = T("5.50 at Volt Electronics, which sells laptops: tiny", 30).move_to([0, 1.0, 0])
        c2 = T("5.50 at Metro Transit, where a ride costs 2.75: twice the fare", 30).move_to([0, 0.1, 0])
        self.steps("Picture a team asked a simple question: which payments were bigger than their own shop's usual payment? "
                   "A 5.50 payment is tiny for Volt Electronics, which sells laptops. At Metro Transit, where a ride costs 2.75, "
                   "it's twice the usual fare. So each payment has to be compared with its own shop's average.", [
            (lambda: self.cap("which payments are bigger than their own shop's usual payment?", WHITE, 28), 0.7),
            "A 5.50",
            (lambda: [FadeIn(c1, shift=0.1 * UP)], 0.6),
            "At Metro",
            (lambda: [FadeIn(c2, shift=0.1 * UP)], 0.6),
            "So each payment",
            (lambda: self.cap("compare each payment with its own shop's average", YELLOW_M, 28), 0.6),
        ])
        q_c = ["WHERE p.amount_minor > (SELECT avg(p2.amount_minor) FROM payments p2",
               "WHERE p2.merchant_id = p.merchant_id AND ...)"]
        s37 = T("37 payments: an answer at once", 30, GREEN_M).move_to([0, 1.0, 0])
        s1m = T("1,000,000 payments: about 13 hours", 30, RED_M).move_to([0, 0.1, 0])
        self.steps("The team writes the query the way they'd say it, and tests it on 37 payments. It answers at once. "
                   "On the full data, a million payments, it doesn't come back. At that pace, it would need about 13 hours. Why?", [
            (lambda: [FadeOut(VGroup(c1, c2)), *self.uncap(), *self.query(q_c)], 0.8),
            "It answers",
            (lambda: [FadeIn(s37, shift=0.1 * UP)], 0.5),
            "about 13 hours",
            (lambda: [FadeIn(s1m, shift=0.1 * UP)], 0.5),
            "Why?",
            (lambda: self.cap("why?", YELLOW_M, 30), 0.4),
        ], after=0.4)

        # ---------------- scene 2: the value from outside ----------------
        o_t = T("outer rows (p)", 22, BLUE_M).move_to([OX, TITLE_Y, 0])
        ov = VGroup(T("one overall average: 24015.17", 30), T("worked out once, before anything else, then reused", 24, GREY_B)).arrange(DOWN, buff=0.3)
        ov.move_to([0, 0.6, 0])
        O = [outer_row(*OUTER[k], OY[k]) for k in range(5)]
        more = T("... 30 succeeded rows", 20, GREY_B).move_to([OX, -0.75, 0])
        self.steps("Comparing every payment with one overall average is easy. The subquery, the query in parentheses, "
                   "runs once, before anything else, and its answer is reused.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(s37, s1m))], 0.5),
            "The subquery",
            (lambda: [FadeIn(ov, shift=0.1 * UP)], 0.7),
            "runs once",
            (lambda: [Indicate(ov[0], color=WHITE, scale_factor=1.05)], 0.8),
        ])
        self.steps("This subquery asks for the average of this payment's shop. That shop number comes from outside, "
                   "from the row being tested, the outer row. So the subquery can't run until there is an outer row.", [
            (lambda: [FadeOut(ov)], 0.4),
            "That shop number",
            (lambda: [Indicate(self.qm[1], color=YELLOW_M, scale_factor=1.06)], 0.9),
            "the outer row",
            (lambda: [FadeIn(o_t), LaggedStart(*[FadeIn(o, shift=0.1 * RIGHT) for o in O], lag_ratio=0.15), FadeIn(more)], 1.2),
            "can't run until",
            (lambda: self.cap("the subquery needs a value from the outer row", YELLOW_M), 0.5),
        ])

        # ---------------- scene 3: the kitchen ----------------
        body, stripes = pot()
        walks = [walk(k) for k in range(3)]
        pot_t = T("the pot (p2)", 22, GREY_B).move_to([(POT_X0 + POT_X1) / 2 + 0.2, TITLE_Y, 0])
        pot_n = T("37 payments", 20, GREY_B).move_to([(POT_X0 + POT_X1) / 2, POT_BOT - 0.28, 0])
        self.steps("A kitchen helps. The easy subquery is a cook who makes one pot of sauce before dinner starts. "
                   "This one is a cook told: for each guest, go and taste the sauce. One walk to the pot per guest, "
                   "even when two guests ordered the same dish.", [
            (lambda: [*self.uncap(), FadeIn(body), Create(stripes, lag_ratio=0.02), FadeIn(pot_t), FadeIn(pot_n)], 1.2),
            "before dinner",
            (lambda: self.cap("easy subquery: one pot of sauce, made before dinner"), 0.5),
            "for each guest",
            (lambda: self.cap("this one: for each guest, walk to the pot and taste", YELLOW_M), 0.5),
            "One walk",
            (lambda: [LaggedStart(*[GrowArrow(w) for w in walks], lag_ratio=0.3)], 1.0),
        ])
        self.steps("So the guest is the outer row, a payment. The pot is the payments table. And each walk is one run of the subquery.", [
            (lambda: [FadeOut(VGroup(*walks)), *self.cap("a guest = an outer row", BLUE_M)], 0.5),
            (lambda: [LaggedStart(*[glow(o[0], BLUE_M, 1.04) for o in O], lag_ratio=0.1)], 0.8),
            "The pot is",
            (lambda: [*self.cap("the pot = the payments table"), glow(body, GREY_B, 1.02)], 0.7),
            "each walk",
            (lambda: self.cap("one walk = one run of the subquery", YELLOW_M), 0.5),
        ])

        # ---------------- scene 4: watch it run ----------------
        run_t = T("this run", 22, WHITE).move_to([PX + 1.6, TITLE_Y, 0])

        def run(k, shop, kept, avg, verdict, vcolor, n, rows):
            ar = walk(k)
            sw = sweep_line()
            return ar, [
                (lambda: [GrowArrow(ar), glow(O[k][0], YELLOW_M, 1.05), *self.clear_lines([2, 3]), *self.panel(0, f"p2.merchant_id = {shop}", YELLOW_M)], 0.6),
                (lambda: [Create(sw)], 0.2),
                (lambda: [sw.animate.move_to([sw.get_x(), POT_BOT + 0.08, 0]), *self.panel(1, f"reads all 37 payments, keeps {len(kept)}", mono=False)], 0.8),
                (lambda: [FadeOut(sw), *[stripes[i].animate.set_color(GOLD_M).set_stroke(width=5) for i in kept],
                          *self.counter(0, f"subquery runs: {n}"), *self.counter(1, f"payment rows read: {rows}")], 0.5),
                (lambda: self.panel(2, f"avg = {avg}"), 0.4),
                (lambda: self.panel(3, verdict, vcolor), 0.4),
            ]

        def reset_stripes():
            return [s.animate.set_color(GREY_D).set_stroke(width=3) for s in stripes]

        a1, r1 = run(0, 1, KEPT[1], "4704.86", "4250 > 4704.86 ?  no: drop", RED_M, 1, 37)
        self.steps("Let's watch. Row 1 belongs to shop 1. PostgreSQL plugs in 1 and runs the subquery. It reads all 37 payments, "
                   "keeps shop 1's seven succeeded ones, and averages them: 4704.86. 4250 isn't bigger, so row 1 is dropped.", [
            (lambda: [*self.uncap(), FadeIn(run_t)], 0.5),
            "Row 1 belongs",
            *r1[:2],
            "It reads all",
            r1[2],
            "keeps shop 1's",
            r1[3],
            "and averages",
            r1[4],
            "4250 isn't",
            r1[5],
        ])
        a2, r2 = run(1, 2, KEPT[2], "1935.00", "1890 > 1935.00 ?  no: drop", RED_M, 2, 74)
        self.steps("Row 2, shop 2. The subquery runs again from the start: another 37 rows, average 1935. 1890 is below it. Dropped.", [
            (lambda: [FadeOut(a1), *reset_stripes()], 0.4),
            *r2[:3],
            "another 37",
            r2[3],
            "average 1935",
            r2[4],
            "1890 is below",
            r2[5],
        ])
        a3, r3 = run(2, 4, KEPT[4], "48620.86", "129900 > 48620.86 ?  yes: keep", GREEN_M, 3, 111)
        self.steps("Row 3, shop 4: a third run, average 48620.86. 129900 is above it, so payment 3 is kept.", [
            (lambda: [FadeOut(a2), *reset_stripes()], 0.4),
            *r3[:4],
            "average",
            r3[4],
            "129900 is above",
            r3[5],
            "so payment 3",
            (lambda: [O[2][0].animate.set_stroke(GREEN_M, width=4)], 0.4),
        ])
        self.steps("There are 30 succeeded payments. How many runs, and how many rows read? Pause and guess.", [
            (lambda: [FadeOut(a3), *reset_stripes(), Indicate(more, color=WHITE, scale_factor=1.1)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        self.steps("30 runs, and 1,110 rows read, for only 6 different answers. Payment 17 also belongs to shop 4, "
                   "and the subquery works out the same average for it all over again.", [
            (lambda: [*self.uncap(), *self.counter(0, "subquery runs: 30", RED_M), *self.counter(1, "payment rows read: 1,110", RED_M)], 0.7),
            "for only 6",
            (lambda: [*self.clear_panel(), *self.panel(0, "6 different answers", mono=False)], 0.6),
            "Payment 17",
            (lambda: [*self.panel(1, "payment 17, shop 4: 48620.86 again", GOLD_M)], 0.6),
            "all over again",
            (lambda: [*[stripes[i].animate.set_color(GOLD_M).set_stroke(width=5) for i in KEPT[4]]], 0.6),
        ])

        # ---------------- scene 5: thirteen hours ----------------
        self.steps("On the large data set, each run reads all million payments to find one shop's rows. "
                   "That's about 51 milliseconds a run. For the first 20 payments, 1.1 seconds. "
                   "For all 930,826 succeeded payments, about 13 hours. An overnight answer to an afternoon question.", [
            (lambda: [*self.clear_panel(), *reset_stripes(), *self.panel(0, "large data set: 1,000,000 payments", mono=False)], 0.7),
            "That's about 51",
            (lambda: self.panel(1, "51 ms per run", WHITE), 0.5),
            "For the first 20",
            (lambda: self.panel(2, "first 20 payments: 1.1 s", WHITE), 0.5),
            "For all 930,826",
            (lambda: self.panel(3, "930,826 runs: about 13 hours", RED_M), 0.5),
            "An overnight",
            (lambda: self.cap("an overnight answer to an afternoon question"), 0.5),
        ])
        self.steps("So reading like the question doesn't make a query cheap. Here PostgreSQL does exactly what the words say, "
                   "once for every payment. A subquery that refers to the outer row is called correlated. "
                   "EXPLAIN, the command that shows the plan, calls it a SubPlan, and counts its runs as loops.", [
            (lambda: self.cap("PostgreSQL does what the words say: once per payment", WHITE), 0.6),
            "called correlated",
            (lambda: [*self.cap("correlated: the subquery refers to the outer row", YELLOW_M), Indicate(self.qm[1], color=YELLOW_M, scale_factor=1.06)], 0.8),
            "EXPLAIN",
            (lambda: self.cap("EXPLAIN shows a SubPlan, with loops = how many times it ran", WHITE), 0.6),
        ])

        # ---------------- scene 6: taste each dish once ----------------
        q_j = ["FROM payments p JOIN (SELECT merchant_id, avg(amount_minor) AS avg_minor",
               "... GROUP BY merchant_id) a ON a.merchant_id = p.merchant_id"]
        ht_t = T("hash table: one average per shop", 22, TEAL_M).move_to([PX + 3.1, TITLE_Y, 0])
        C = [card(i) for i in range(6)]
        sw = sweep_line()
        self.steps("The fix turns the work around. Taste each dish once. One pass over the payments with GROUP BY works out "
                   "all six shop averages, and keeps them in a hash table, a lookup table in memory.", [
            (lambda: [*self.uncap(), *self.clear_panel(), *self.query(q_j), swap(run_t, ht_t), O[2][0].animate.set_stroke(BLUE_M, width=2.5),
                      *self.counter(0, "averages computed: 0"), *self.counter(1, "payment rows read: 0")], 0.8),
            "One pass",
            (lambda: [Create(sw)], 0.2),
            (lambda: [sw.animate.move_to([sw.get_x(), POT_BOT + 0.08, 0]), *[s.animate.set_color(TEAL_M) for s in stripes]], 1.2),
            (lambda: [FadeOut(sw), LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in C], lag_ratio=0.15),
                      *self.counter(0, "averages computed: once", TEAL_M), *self.counter(1, "payment rows read: 37")], 1.0),
            "a hash table",
            (lambda: self.cap("hash table: finds an entry by its key in one step", TEAL_M), 0.5),
        ])

        def probe(k):
            m = OUTER[k][1]
            return [glow(O[k][0], YELLOW_M, 1.05), glow(C[CARD_OF[m]][0], YELLOW_M, 1.06)]

        self.steps("Then a second pass reads each payment once, and looks up its shop's average in one step. "
                   "Two passes, 74 rows read here. Written as a join, on the large data set, it answers for all "
                   "930,826 payments in 282 milliseconds.", [
            (lambda: [*self.uncap(), *[s.animate.set_color(GREY_D) for s in stripes]], 0.4),
            "looks up",
            *[(lambda k=k: probe(k), 0.45) for k in range(5)],
            "Two passes",
            (lambda: self.counter(1, "payment rows read: 74 (37 + 37)", TEAL_M), 0.5),
            "Written as a join",
            (lambda: self.cap("large data set: 282 ms, against about 13 hours", GREEN_M, 28), 0.6),
        ])

        # ---------------- scene 7: when it's fine, and a trap ----------------
        self.steps("Correlated subqueries are not always slow. PostgreSQL rewrites EXISTS, NOT EXISTS and IN into joins on its own, "
                   "but not a subquery that works out an average, like this one.", [
            (lambda: self.cap("EXISTS, NOT EXISTS, IN: rewritten into joins for you", WHITE), 0.6),
            "but not",
            (lambda: self.cap("an average or a sum inside: not rewritten", RED_M), 0.5),
        ])
        self.steps("And one that finds its rows through an index, a sorted catalogue, is cheap when the outer query has few rows. "
                   "So read the plan: a SubPlan that loops as many times as a big table has rows is the one to rewrite.", [
            (lambda: self.cap("an index and few outer rows: cheap enough", WHITE), 0.5),
            "So read the plan",
            (lambda: self.cap("read the plan: a SubPlan with loops = a big table's rows is the one to rewrite", YELLOW_M), 0.6),
        ])
        q_bad = ["WHERE p.amount_minor > (SELECT avg(p2.amount_minor) FROM payments p2",
                 "WHERE merchant_id = merchant_id AND ...)"]
        self.steps("One trap: name every column. Write merchant_id equals merchant_id without the short names, "
                   "and both find the inner table. The condition is always true, and you're back to the overall average, with no error.", [
            (lambda: [*self.uncap(), *self.query(q_bad, GREY_A)], 0.6),
            (lambda: [self.qm[1].animate.set_color(RED_M)], 0.4),
            "both find",
            (lambda: [glow(body, RED_M, 1.02)], 0.8),
            "always true",
            (lambda: [*self.cap("always true: the overall average again, and no error", RED_M), *[s.animate.set_color(RED_M) for s in stripes]], 0.7),
            "with no error",
            (lambda: [*[s.animate.set_color(GREY_D) for s in stripes], *self.query(q_j)], 0.7),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, why 13 hours? A subquery that depends on the outer row runs once per row. Work it out once for every key, and join.", [
            (lambda: self.cap("why 13 hours?", WHITE), 0.5),
            "runs once per row",
            (lambda: [*self.cap("depends on the outer row: runs once per row", YELLOW_M, 28),
                      LaggedStart(*[glow(o[0], YELLOW_M, 1.04) for o in O], lag_ratio=0.12)], 1.0),
            "Work it out once",
            (lambda: [*self.cap("work it out once per key, and join", TEAL_M, 28), LaggedStart(*[glow(c[0], TEAL_M, 1.05) for c in C], lag_ratio=0.12)], 1.0),
        ], after=0.5)
        o17 = outer_row(17, 4, 18999, -1.35, YELLOW_M)
        self.steps("One quick check. In the join version, payment 17 comes along. Is shop 4's average worked out again? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "payment 17",
            (lambda: [FadeIn(o17, shift=0.15 * UP)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(c=(3.4, -2.0))
        self.steps("No. It's already on its card, 48621. One look, and one comparison.", [
            (lambda: [*self.uncap(), glow(o17[0], YELLOW_M, 1.05), glow(C[3][0], YELLOW_M, 1.08)], 0.8),
            "One look",
            (lambda: [C[3][0].animate.set_stroke(GREEN_M, width=4)], 0.5),
        ], after=0.3)
        self.play(*self.cap("depends on the outer row: once per row. work it out once per key, and join.", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
