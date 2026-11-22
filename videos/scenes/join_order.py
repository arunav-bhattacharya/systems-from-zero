from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz"; spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bEXPLAIN ANALYZE\b", "explain analyze"))
SAY.insert(0, (r"\bANALYZE\b", "analyze"))
SAY.insert(0, (r"\bCREATE STATISTICS\b", "create statistics"))
SAY.insert(0, (r"\bIBM's\b", "I B M's"))
# "chargebacks" comes out as "charge-ih-backs"; join the two words without the extra vowel
SAY.insert(0, (r"\bchargebacks\b", "charge-backs"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BOT_Y, MID_Y, TOP_Y = -1.45, 0.4, 2.2
XM, XP, XC = -5.15, -2.15, 0.85        # tables: merchants (shops), payments, chargebacks
XMP, XPC, XALL = -3.65, -0.65, -2.15   # pairs and the full set
BW, BH = 2.7, 0.9
RX = 4.65                              # right panel centre (2.8 .. 6.5)
QY, CAP_Y, BAR_Y = 3.4, -3.35, -2.9


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


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
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def lbox(name, val, color, x, y, w=BW):
    r = RoundedRectangle(corner_radius=0.12, width=w, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    v = T(val or "guess", 18, GREY_B).move_to([0, -0.2, 0])
    if not val:
        v.set_opacity(0)
    g = VGroup(r, fit(T(name, 19), w - 0.3).move_to([0, 0.17, 0]), v)
    return g.move_to([x, y, 0])


def edge(a, b, color=GREY_C):
    return Line(a[0].get_top(), b[0].get_bottom(), stroke_width=2.5, color=color)


class JoinOrder(Base):
    """store-10, section 3. The map app picks the fastest route for the traffic it guesses, and sends you past the
    stadium. A report joins shops (three conditions), payments and chargebacks; join orders explode (6, 720, 3.6
    million); dynamic programming builds the best plan for each group from smaller ones (System R 1979; 1,023 groups
    for 10 tables; PostgreSQL up to 12). The lesson's stepper: est 10 shops, pairs 1,000 and 20,000; plan A 1,020 vs B
    20,020. Really 1,000 shops: A does 102,000, B would do 22,000 (4.6 times). CREATE STATISTICS: est 1,000, B chosen,
    103,172 pages down to 6,542. Check the guesses first; the map re-routes, PostgreSQL doesn't. A check."""

    def cap(self, s, color=GREY_B, size=22):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b, rate_func=linear), run_time=secs)

    def val(self, box, s, color=GREY_B):
        new = fit(T(s, 18, color), BW - 0.25).move_to(box[2].get_center())
        return [Transform(box[2], new)]

    def tint(self, box, color):
        return [box[0].animate.set_stroke(color).set_fill(fillc(color), 1)]

    def rp(self, key, mob):
        """Put one item in the right panel under a key, replacing what was there."""
        old = self.panel.get(key)
        self.panel[key] = mob
        return [swap(old, mob)]

    def rp_clear(self):
        out = [FadeOut(m) for m in self.panel.values()]
        self.panel = {}
        return out

    def card(self, title, sumline, color, y):
        r = RoundedRectangle(corner_radius=0.1, width=3.7, height=1.15, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.1), 1)
        g = VGroup(r, fit(T(title, 18, color), 3.45).move_to([0, 0.24, 0]), fit(M(sumline, 18, WHITE), 3.45).move_to([0, -0.22, 0]))
        return g.move_to([RX, y, 0])

    def construct(self):
        self.capm = None
        self.panel = {}
        self.title_card("The right route for the wrong traffic", "how a planner picks the order of joins")

        # ---------------- scene 1: the map app ----------------
        home, dinner = np.array([-5.3, -0.2, 0]), np.array([5.1, -0.2, 0])
        top = CubicBezier(home, [-2.2, 2.3, 0], [2.2, 2.3, 0], dinner).set_stroke(GREY_B, 5)
        low = CubicBezier(home, [-2.2, -2.6, 0], [2.2, -2.6, 0], dinner).set_stroke(GREY_B, 5)
        dots = VGroup(Dot(home, radius=0.16, color=BLUE_M), Dot(dinner, radius=0.16, color=GREEN_M))
        labs = VGroup(T("you", 22, BLUE_M).next_to(dots[0], LEFT, buff=0.2), T("dinner", 22, GREEN_M).next_to(dots[1], RIGHT, buff=0.2))
        stad = VGroup(Ellipse(width=1.9, height=0.75, stroke_color=GREY_B, stroke_width=3).set_fill(fillc(GREY_B, 0.2), 1),
                      T("stadium", 20, GREY_B)).move_to([0, 2.55, 0])
        q_top = T("expected: quiet", 20, YELLOW_M).move_to([-3.4, 1.75, 0])
        q_low = T("the ring road", 20, GREY_B).move_to([0, -2.4, 0])
        mapg = VGroup(top, low, dots, labs, stad, q_low)
        crowd = VGroup(*[Dot(top.point_from_proportion(p) + 0.08 * np.array([np.sin(17 * p), np.cos(23 * p), 0]), radius=0.07, color=RED_M)
                         for p in np.linspace(0.32, 0.68, 22)])
        car = Dot(home, radius=0.13, color=YELLOW_M).set_z_index(3)
        self.steps("Your phone's map app picks the fastest way to a friend's birthday dinner in a second, out of hundreds of routes, "
                   "without driving any of them.", [
            (lambda: [FadeIn(dots), FadeIn(labs)], 0.6),
            "out of hundreds",
            (lambda: [Create(top), Create(low), FadeIn(stad), FadeIn(q_low)], 1.2),
        ])
        self.steps("It knows how long each road is, and it guesses how busy each one will be.", [
            (lambda: [top.animate(rate_func=there_and_back).set_stroke(WHITE, 7), low.animate(rate_func=there_and_back).set_stroke(WHITE, 7)], 0.9),
            "it guesses",
            (lambda: [FadeIn(q_top)], 0.6),
        ])
        self.steps("Tonight it sends you past the football stadium an hour before a match. Forty minutes in traffic.", [
            (lambda: [top.animate.set_stroke(YELLOW_M, 6), FadeIn(car)], 0.5),
            (lambda: [MoveAlongPath(car, top.copy().pointwise_become_partial(top, 0, 0.33), rate_func=smooth)], 1.2),
            "an hour before",
            (lambda: [LaggedStart(*[FadeIn(d, scale=0.4) for d in crowd], lag_ratio=0.05), top.animate.set_stroke(RED_M, 6),
                      Transform(q_top, T("a match crowd", 20, RED_M).move_to(q_top.get_center()))], 1.2),
            "Forty minutes",
            (lambda: self.cap("forty minutes in traffic", RED_M, 24), 0.6),
        ])
        self.steps("So, was the search broken? Hold that thought. A database has the same job every time you ask it a question.", [
            (lambda: self.cap("was the search broken?", WHITE, 24), 0.6),
            "A database",
            (lambda: [*self.uncap(), FadeOut(VGroup(mapg, crowd, car, q_top))], 0.8),
        ], after=0.3)

        # ---------------- scene 2: three tables, many orders ----------------
        M_ = lbox("shops, 3 conditions", "10,000 shops", BLUE_M, XM, BOT_Y)
        P_ = lbox("payments", "1,000,000 rows", TEAL_M, XP, BOT_Y)
        C_ = lbox("chargebacks", "20,000 rows", GOLD_M, XC, BOT_Y)
        q = fit(M("city = 'Amsterdam' AND country = 'NL' AND currency = 'EUR'", 16, YELLOW_M), 7.6).move_to([XALL, QY, 0])
        self.steps("Every night, a report counts chargebacks, payments that customers disputed, at shops in Amsterdam.", [
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.7),
            "payments that customers",
            (lambda: self.cap("a chargeback: a payment the customer disputed", WHITE), 0.6),
        ])
        self.steps("It joins three tables: 10,000 shops, a million payments, and 20,000 chargebacks. "
                   "A join pairs the rows of two tables that belong together.", [
            "10,000 shops",
            (lambda: [FadeIn(M_, shift=0.15 * UP)], 0.6),
            "a million",
            (lambda: [FadeIn(P_, shift=0.15 * UP)], 0.6),
            "and 20,000",
            (lambda: [FadeIn(C_, shift=0.15 * UP)], 0.6),
            "A join pairs",
            (lambda: self.cap("a join: pair the rows of two tables that belong together", WHITE), 0.6),
        ])
        self.steps("Before anything runs, the planner, the part of the database that picks how to run a query, "
                   "has to choose which two tables to join first. The order changes how many rows pile up in the middle.", [
            (lambda: self.cap("the planner: picks how to run a query, before it runs", WHITE), 0.6),
            "which two tables",
            (lambda: [glow(M_[0], WHITE, 1.05), glow(P_[0], WHITE, 1.05)], 0.8),
            (lambda: [glow(P_[0], WHITE, 1.05), glow(C_[0], WHITE, 1.05)], 0.8),
            "The order changes",
            (lambda: self.cap("the order decides how many rows pile up in the middle", WHITE), 0.6),
        ])
        oc = [VGroup(T(a, 20, GREY_B), T(b, 26, c)).arrange(DOWN, buff=0.1).move_to([RX, y, 0])
              for a, b, c, y in [("3 tables", "6 orders", WHITE, 2.35), ("6 tables", "720 orders", GOLD_M, 1.05),
                                 ("10 tables", "3.6 million orders", RED_M, -0.25)]]
        self.steps("And the number of orders explodes. Adding one table at a time, 3 tables can be joined in 6 orders, "
                   "6 tables in 720, and 10 tables in 3.6 million.", [
            (lambda: [*self.uncap()], 0.4),
            "3 tables can",
            (lambda: self.rp("o3", oc[0]), 0.6),
            "6 tables in",
            (lambda: self.rp("o6", oc[1]), 0.6),
            "10 tables in",
            (lambda: self.rp("o10", oc[2]), 0.7),
        ])
        self.steps("Pricing every one works for 3 tables and is hopeless for 12.", [
            (lambda: self.cap("price every order? fine for 3 tables, hopeless for 12", RED_M), 0.6),
        ], after=0.3)

        # ---------------- scene 3: small groups first ----------------
        MP = lbox("shops + payments", "", GREY_B, XMP, MID_Y)
        PC = lbox("payments + chargebacks", "", GREY_B, XPC, MID_Y)
        AL = lbox("all three tables", "", GREY_B, XALL, TOP_Y)
        e_mp = VGroup(edge(M_, MP), edge(P_, MP))
        e_pc = VGroup(edge(P_, PC), edge(C_, PC))
        e_a = edge(MP, AL)
        e_b = edge(PC, AL)
        self.steps("But orders share parts. Think of the map again. The fastest way to the bridge is still the fastest way to the bridge, "
                   "whatever road you take after it.", [
            (lambda: self.cap("orders share parts", WHITE, 24), 0.6),
            "The fastest way",
            (lambda: self.cap("the fastest way to the bridge stays the fastest, whatever comes after", YELLOW_M), 0.6),
        ])
        self.steps("So the planner finds the best plan for each small group of tables once, and builds bigger groups only from those. "
                   "Single tables first, then every pair that a join condition connects, then all three.", [
            "Single tables",
            (lambda: [*self.uncap(), glow(M_[0], WHITE, 1.05), glow(P_[0], WHITE, 1.05), glow(C_[0], WHITE, 1.05)], 0.8),
            "then every pair",
            (lambda: [FadeIn(MP), FadeIn(PC), Create(e_mp), Create(e_pc),
                      *self.cap("shops + chargebacks: no join condition, so it's skipped", GREY_B)], 0.9),
            "then all three",
            (lambda: [FadeIn(AL), Create(e_a), Create(e_b)], 0.8),
        ])
        self.steps("That's dynamic programming: solve each small problem once, keep the answer, and build the big one from it.", [
            (lambda: self.cap("dynamic programming: solve each small problem once, keep the answer, build up", YELLOW_M), 0.6),
            "keep the answer",
            (lambda: [glow(MP[0], WHITE, 1.04), glow(PC[0], WHITE, 1.04)], 0.8),
            "build the big",
            (lambda: [glow(AL[0], WHITE, 1.04)], 0.7),
        ])
        g10 = VGroup(T("10 tables", 20, GREY_B), T("about 1,000 groups", 26, GREEN_M),
                     T("instead of 3.6 million orders", 18, GREY_B)).arrange(DOWN, buff=0.1).move_to([RX, -0.35, 0])
        self.steps("IBM's System R, one of the first SQL databases, introduced it in 1979. It visits about 1,000 groups for 10 tables, "
                   "instead of 3.6 million orders, and PostgreSQL searches this way up to 12 tables.", [
            (lambda: self.cap("IBM's System R, 1979: one of the first SQL databases", WHITE), 0.6),
            "It visits",
            (lambda: self.rp("o10", g10), 0.8),
            "and PostgreSQL",
            (lambda: self.cap("PostgreSQL searches this way up to 12 tables", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 4: pricing with guesses ----------------
        cA = self.card("plan A: shops + payments first", "1,000 + 20 = 1,020", GOLD_M, 1.55)
        cB = self.card("plan B: payments + chargebacks first", "20,000 + 20 = 20,020", TEAL_M, 0.0)
        okA = tick(True, 0.2).next_to(cA, LEFT, buff=0.12)
        self.steps("Now each box gets a guess. The shops have three conditions, and each keeps a tenth, so the planner multiplies: 10 shops.", [
            (lambda: [*self.uncap(), *self.rp_clear()], 0.5),
            "each keeps a tenth",
            (lambda: self.cap("10,000 × 0.1 × 0.1 × 0.1 = 10 shops", YELLOW_M), 0.6),
            "10 shops",
            (lambda: [*self.val(M_, "guess: 10 shops", YELLOW_M), *self.tint(M_, YELLOW_M)], 0.7),
        ])
        self.steps("Shops with their payments: about 1,000 rows. Payments with chargebacks: 20,000.", [
            (lambda: [*self.val(MP, "guess: 1,000 rows", YELLOW_M)], 0.6),
            "Payments with",
            (lambda: [*self.val(PC, "guess: 20,000 rows", YELLOW_M)], 0.6),
            (lambda: [*self.val(AL, "guess: 20 rows", YELLOW_M)], 0.6),
        ])
        self.steps("The lab's price is the rows the joins produce along the way. Plan A, shops with payments first: 1,000, then 20, so 1,020.", [
            (lambda: self.cap("price: the rows the joins produce along the way", WHITE), 0.6),
            "Plan A",
            (lambda: [FadeIn(cA, shift=0.1 * LEFT), e_mp.animate.set_stroke(GOLD_M, 5), e_a.animate.set_stroke(GOLD_M, 5),
                      *self.tint(MP, GOLD_M)], 0.8),
        ])
        self.steps("Plan B, payments with chargebacks first: 20,020. Plan A wins by a mile.", [
            (lambda: [FadeIn(cB, shift=0.1 * LEFT)], 0.7),
            "Plan A wins",
            (lambda: [Create(okA), glow(cA[0], GOLD_M, 1.04), *self.cap("the planner picks plan A", GOLD_M, 24)], 0.7),
        ], after=0.3)

        # ---------------- scene 5: predict, then run ----------------
        self.steps("Here's the catch. Every shop in Amsterdam is in the Netherlands and takes euros. "
                   "So how many shops really pass the three conditions? Pause and guess.", [
            (lambda: self.cap("every Amsterdam shop is in NL and takes EUR", WHITE), 0.6),
            "So how many",
            (lambda: [glow(M_[0], YELLOW_M, 1.06)], 0.7),
            "Pause and guess",
            (lambda: self.cap("how many shops really pass?  pause and guess", YELLOW_M, 24), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("1,000, not 10. The second and third conditions removed nobody.", [
            (lambda: [*self.uncap(), *self.val(M_, "guess 10, actual 1,000", RED_M), *self.tint(M_, RED_M)], 0.7),
            "removed nobody",
            (lambda: self.cap("Amsterdam already means NL and EUR: conditions two and three remove nobody", WHITE), 0.6),
        ])
        self.steps("And the error climbs: the first join makes 100,000 rows, not 1,000, and the answer is 2,000, not 20.", [
            "the error climbs",
            (lambda: [e_mp.animate.set_stroke(RED_M, 5)], 0.5),
            "the first join",
            (lambda: [*self.val(MP, "guess 1,000, actual 100,000", RED_M), *self.tint(MP, RED_M)], 0.7),
            "and the answer",
            (lambda: [e_a.animate.set_stroke(RED_M, 5), *self.val(AL, "guess 20, actual 2,000", RED_M)], 0.7),
        ])
        cA2 = self.card("A, as it really ran", "100,000 + 2,000 = 102,000", RED_M, 1.55)
        cB2 = self.card("B, had it been chosen", "20,000 + 2,000 = 22,000", GREEN_M, 0.0)
        x46 = VGroup(T("4.6 times", 30, RED_M), T("the work", 20, RED_M)).arrange(DOWN, buff=0.08).move_to([RX, -1.35, 0])
        self.steps("Priced with the real counts, plan A does 102,000 rows of work, and plan B would have done 22,000. "
                   "The chosen plan did 4.6 times the work. Well, that's the stadium.", [
            (lambda: [*self.uncap(), FadeOut(okA), Transform(cA, cA2)], 0.8),
            "and plan B",
            (lambda: [Transform(cB, cB2)], 0.8),
            "The chosen plan",
            (lambda: [FadeIn(x46, scale=0.8)], 0.6),
            "Well, that's",
            (lambda: self.cap("well, that's the stadium", RED_M, 24), 0.5),
        ], after=0.3)

        # ---------------- scene 6: fix the guess ----------------
        self.steps("So, was the search broken? No. It found the cheapest plan for the numbers it was given.", [
            (lambda: self.cap("was the search broken? no: it was right for the numbers it was given", WHITE), 0.6),
        ])
        self.steps("In PostgreSQL itself, the same wrong guess picked a loop that looked up the payments a thousand separate times: "
                   "103,172 pages touched.", [
            (lambda: [*self.cap("PostgreSQL: 1,000 separate lookups into payments", WHITE), FadeOut(x46)], 0.6),
            "103,172",
            (lambda: [*self.rp("pg", VGroup(T("nested loop", 18, RED_M), T("103,172 pages", 26, RED_M)).arrange(DOWN, buff=0.08).move_to([RX, -1.35, 0]))], 0.7),
        ])
        cA3 = self.card("plan A", "100,000 + 2,000 = 102,000", GREY_B, 1.55)
        cB3 = self.card("plan B: chosen", "20,000 + 2,000 = 22,000", GREEN_M, 0.0)
        okB = tick(True, 0.2).next_to(cB, LEFT, buff=0.12)
        self.steps("Tell it that the city decides the country and the currency, with CREATE STATISTICS, and it guesses 1,000 shops.", [
            (lambda: self.cap("CREATE STATISTICS: the city decides the country and the currency", GREEN_M), 0.6),
            "it guesses",
            (lambda: [*self.val(M_, "guess: 1,000 shops", GREEN_M), *self.tint(M_, GREEN_M),
                      *self.val(MP, "guess: 100,000 rows", GREY_B), *self.tint(MP, GREY_B),
                      *self.val(AL, "guess: 2,000 rows", GREY_B), e_mp.animate.set_stroke(GREY_C, 2.5), e_a.animate.set_stroke(GREY_C, 2.5)], 0.9),
        ])
        self.steps("The same search picks plan B, reads the payments once, and touches 6,542 pages, 16 times fewer.", [
            (lambda: [Transform(cA, cA3), Transform(cB, cB3), e_pc.animate.set_stroke(GREEN_M, 5), e_b.animate.set_stroke(GREEN_M, 5),
                      *self.tint(PC, GREEN_M)], 0.8),
            (lambda: [Create(okB)], 0.4),
            "and touches",
            (lambda: [*self.rp("pg", VGroup(T("one pass over payments", 18, GREEN_M), T("6,542 pages", 26, GREEN_M),
                                            T("16 times fewer", 18, GREEN_M)).arrange(DOWN, buff=0.08).move_to([RX, -1.45, 0]))], 0.8),
            "16 times",
            (lambda: self.cap("same search, better guess, other plan", GREEN_M, 24), 0.6),
        ], after=0.3)

        # ---------------- scene 7: check the guesses first ----------------
        self.steps("It's tempting to force the order yourself. Don't start there. When a plan is slow, check the guesses first.", [
            (lambda: self.cap("tempting: force the join order yourself", PURPLE_M, 24), 0.6),
            "check the guesses",
            (lambda: self.cap("when a plan is slow, check the guesses first", YELLOW_M, 26), 0.6),
        ])
        self.steps("Run EXPLAIN ANALYZE, which prints each step's guessed and actual rows, read it from the bottom up, "
                   "and fix the first step that's off by 10 times or more.", [
            (lambda: self.cap("EXPLAIN ANALYZE: each step's guessed and actual rows", WHITE), 0.6),
            "from the bottom up",
            (lambda: [LaggedStart(glow(M_[0], WHITE, 1.05), glow(MP[0], WHITE, 1.05), glow(AL[0], WHITE, 1.05), lag_ratio=0.5)], 1.2),
            "fix the first",
            (lambda: [*self.cap("read bottom up; fix the first step off by 10 times or more", WHITE), glow(M_[0], GREEN_M, 1.08)], 0.7),
        ])
        self.steps("Often a plain ANALYZE, which refreshes the statistics, is enough. "
                   "In one benchmark, about 1 in 10 queries ran more than 10 times slower on PostgreSQL's own guesses.", [
            (lambda: self.cap("often a plain ANALYZE is enough: it refreshes the statistics", WHITE), 0.6),
            "In one benchmark",
            (lambda: self.cap("a benchmark: about 1 in 10 queries ran over 10 times slower on PostgreSQL's own guesses", RED_M), 0.6),
        ])
        self.steps("And here the map app is ahead: it re-routes you on the way. PostgreSQL never changes a plan once it starts.", [
            (lambda: self.cap("the map app re-routes you on the way", WHITE), 0.6),
            "PostgreSQL never",
            (lambda: self.cap("PostgreSQL settles on a plan before the first row, and runs it to the end", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: the planner picks the best plan for its guesses. A wrong plan usually means a wrong guess.", [
            (lambda: self.cap("the planner picks the best plan for its guesses", YELLOW_M, 26), 0.6),
            "A wrong plan",
            (lambda: self.cap("a wrong plan usually means a wrong guess", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.steps("One quick check. The shops step says 10 guessed, 1,000 actual. The join above it says 1,000 guessed, 100,000 actual. "
                   "Which one do you fix? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(okB), *self.rp_clear(), e_pc.animate.set_stroke(GREY_C, 2.5), e_b.animate.set_stroke(GREY_C, 2.5),
                      *self.tint(PC, GREY_B), cA.animate.set_opacity(0.3), cB.animate.set_opacity(0.3)], 0.6),
            "The shops step",
            (lambda: [*self.val(M_, "guess 10, actual 1,000", RED_M), *self.tint(M_, RED_M)], 0.6),
            "The join above",
            (lambda: [*self.val(MP, "guess 1,000, actual 100,000", RED_M), *self.tint(MP, RED_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("which one do you fix?  pause and think", YELLOW_M, 24), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("The shops. The join above is only passing the same error up.", [
            (lambda: [*self.uncap(), glow(M_[0], YELLOW_M, 1.08), e_mp.animate.set_stroke(RED_M, 5)], 0.7),
            "passing the same",
            (lambda: [*self.cap("fix the lowest wrong guess: the steps above only pass it up", YELLOW_M, 26),
                      *[travel(e, RED_M, 0.6) for e in e_mp]], 0.8),
        ], after=0.5)
        self.wait(2.0)
