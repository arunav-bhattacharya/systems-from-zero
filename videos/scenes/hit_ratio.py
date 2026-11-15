from sfz import *

PY = 2.5                               # the request path: fraud check, Redis, database
SX, CX, DX = -5.0, -0.3, 4.7
ROWS = [-0.3, -1.2, -2.1]              # 90%, 99%, 99.9%
LB0, LS = -4.6, 3.0                    # latency bars: left edge, units per ms
QB0, QS = 1.8, 3.0                     # database bars: left edge, units per 10,000 queries a second
BH = 0.42
KX0, KW = -4.6, 10.0                   # keys and lookups bars: left edge, width for 100%
KY, RY = 0.85, -1.65

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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def arr(a, b, color=GREY_B, sw=2.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = np.linalg.norm(b - a)
    return Arrow(a, b, buff=0.04, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2 / n,
                 max_stroke_width_to_length_ratio=20)




def node(x, title, sub, color=WHITE, w=2.8):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=0.95, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, PY, 0])
    return VGroup(r, T(title, 24).move_to([x, PY + 0.18, 0]), T(sub, 16, GREY_B).move_to([x, PY - 0.22, 0]))


def lat_row(k, h, label):
    y = ROWS[k]
    hw, mw = h * 0.5 * LS, (1 - h) * 10 * LS
    g = Rectangle(width=hw, height=BH, stroke_width=0).set_fill(GREEN_M, 0.55).move_to([LB0 + hw / 2, y, 0])
    m = Rectangle(width=max(mw, 0.02), height=BH, stroke_width=0).set_fill(RED_M, 0.7).move_to([LB0 + hw + max(mw, 0.02) / 2, y, 0])
    n = left_at(T(label, 20), LB0 + hw + max(mw, 0.02) + 0.15, y)
    return g, m, n


def q_row(k, q, label):
    y = ROWS[k]
    w = max(QS * q / 10000, 0.02)
    b = Rectangle(width=w, height=BH, stroke_width=0).set_fill(RED_M, 0.7).move_to([QB0 + w / 2, y, 0])
    return b, right_at(T(label, 20), 6.5, y)


def band(kfrac, rfrac, color=GOLD_M):
    """The share of keys a cache holds (top bar) and the share of lookups they get (bottom bar)."""
    kw, rw = max(KW * kfrac, 0.06), KW * rfrac
    sk = Rectangle(width=kw, height=0.5, stroke_width=0).set_fill(color, 0.8).move_to([KX0 + kw / 2, KY, 0])
    sr = Rectangle(width=rw, height=0.5, stroke_width=0).set_fill(color, 0.8).move_to([KX0 + rw / 2, RY, 0])
    fan = Polygon([KX0, KY - 0.25, 0], [KX0 + kw, KY - 0.25, 0], [KX0 + rw, RY + 0.25, 0], [KX0, RY + 0.25, 0],
                  stroke_width=0).set_fill(color, 0.22)
    return VGroup(fan, sk, sr)


class HitRatio(Base):
    """cache-01, section 2 (with sections 0 and 1): a fraud check does 100,000 merchant lookups a second; Redis answers
    in 0.5 ms, the database in 10 ms. Average = h × 0.5 + (1 − h) × 10: 1.45 ms and 10,000 queries a second at 90%,
    0.595 ms and 1,000 at 99%, 0.51 ms and 100 at 99.9%. Uniform popularity: 10% of a million merchants catch 10%.
    Zipf with α = 1: the top 1,000 (0.1%) get 52% of lookups and the top 10% get 84%."""

    def construct(self):
        self.title_card("Hit ratios", "why 90% to 99% hits is ten times better, and why a small cache can get there")

        # ---- 1. fast and slow --------------------------------------------------------------------------------------
        svc = node(SX, "fraud check", "100,000 lookups a second", w=3.2)
        db = node(DX, "database", "10 ms a lookup", BLUE_M)
        red = node(CX, "Redis", "0.5 ms a lookup", GREEN_M, w=3.0)
        direct = arr([SX + 1.65, PY, 0], [DX - 1.45, PY, 0])
        a1 = arr([SX + 1.65, PY, 0], [CX - 1.55, PY, 0])
        a2 = arr([CX + 1.55, PY, 0], [DX - 1.45, PY, 0])
        self.steps("A fraud check looks up the merchant on every card payment, 100,000 times a second. The database "
                   "answers in 10 milliseconds. Redis, a cache in memory one hop away, answers in half a millisecond.", [
            (lambda: [FadeIn(svc, shift=0.1 * UP)], 0.7),
            "The database",
            (lambda: [FadeIn(db, shift=0.1 * UP), GrowArrow(direct)], 0.8),
            (lambda: [travel(direct, BLUE_M, 1.2)], 1.2),
            "Redis",
            (lambda: [FadeIn(red, scale=0.95)], 0.7),
            (lambda: [ReplacementTransform(direct, VGroup(a1, a2))], 0.5),
            "answers in half",
            (lambda: [travel(a1, GREEN_M, 0.5)], 0.5),
            (lambda: [travel(Line(a1.get_end(), a1.get_start()), GREEN_M, 0.5)], 0.5),
        ])

        # ---- 2. hits and misses ------------------------------------------------------------------------------------
        hit_l = T("hit", 19, GREEN_M).move_to([(SX + CX) / 2 + 0.2, PY + 0.4, 0])
        miss_l = T("miss", 19, RED_M).move_to([(CX + DX) / 2 + 0.1, PY + 0.4, 0])

        def hit(d=0.0):
            return Succession(Wait(d), travel(a1, GREEN_M, 0.45), travel(Line(a1.get_end(), a1.get_start()), GREEN_M, 0.45))

        def miss(d=0.0):
            return Succession(Wait(d), travel(a1, RED_M, 0.4), travel(a2, RED_M, 0.45),
                              travel(Line(a2.get_end(), a2.get_start()), RED_M, 0.45),
                              travel(Line(a1.get_end(), a1.get_start()), RED_M, 0.4))

        self.steps("But Redis holds only some merchants. If it has the one you ask for, that's a hit. "
                   "If not, it's a miss, and the lookup goes on to the database.", [
            (lambda: [glow(red[0], GREEN_M)], 0.8),
            "that's a hit",
            (lambda: [FadeIn(hit_l), hit(), hit(0.35)], 1.3),
            "If not",
            (lambda: [FadeIn(miss_l), miss()], 1.8),
        ])

        # ---- 3. the formula -----------------------------------------------------------------------------------------
        f = VGroup(T("average  =", 26), T("hit ratio × 0.5 ms", 26, GREEN_M), T("+", 26), T("miss ratio × 10 ms", 26, RED_M))
        f.arrange(RIGHT, buff=0.25).move_to([0, 1.3, 0])
        self.steps("So the average lookup costs the hit ratio times half a millisecond, plus the miss ratio times 10.", [
            (lambda: [FadeIn(f[0])], 0.5),
            "the hit ratio",
            (lambda: [FadeIn(f[1], shift=0.1 * UP)], 0.6),
            "plus the miss",
            (lambda: [FadeIn(f[2]), FadeIn(f[3], shift=0.1 * UP)], 0.6),
        ])

        # ---- 4. 90% -------------------------------------------------------------------------------------------------
        hl = T("average latency", 19, GREY_B).move_to([LB0 + 2.2, 0.42, 0])
        hq = T("database queries a second", 19, GREY_B).move_to([QB0 + 2.35, 0.42, 0])
        labs = [left_at(T(t, 22), -6.45, ROWS[k]) for k, t in enumerate(["90%", "99%", "99.9%"])]
        g1, m1, n1 = lat_row(0, 0.9, "1.45 ms")
        gt = T("0.45", 17).move_to(g1)
        mt = T("1.0 ms from the misses", 17).move_to(m1)
        self.steps("At 90% hits, the hits add 0.45 milliseconds, and the misses add a whole millisecond. "
                   "One lookup in ten costs more than the other nine together.", [
            (lambda: [FadeIn(hl), FadeIn(labs[0])], 0.5),
            (lambda: [GrowFromEdge(g1, LEFT), FadeIn(gt)], 0.7),
            "and the misses",
            (lambda: [GrowFromEdge(m1, LEFT), FadeIn(mt)], 0.9),
            (lambda: [FadeIn(n1)], 0.4),
            "One lookup",
            (lambda: [Indicate(mt, color=RED_M, scale_factor=1.1)], 0.9),
        ])

        qb1, qn1 = q_row(0, 10000, "10,000")
        self.steps("And every miss is a query, so the database gets 10,000 a second.", [
            (lambda: [FadeIn(hq)], 0.5),
            "so the database",
            (lambda: [GrowFromEdge(qb1, LEFT), FadeIn(qn1), miss()], 1.6),
        ])

        # ---- 5. 99% -----------------------------------------------------------------------------------------------------
        g2, m2, n2 = lat_row(1, 0.99, "0.595 ms")
        qb2, qn2 = q_row(1, 1000, "1,000")
        self.steps("Now 99%. It looks like nine points more, but it's ten times fewer misses: 1,000 queries a second, "
                   "and the average falls to 0.6 milliseconds.", [
            (lambda: [FadeIn(labs[1]), FadeOut(gt), FadeOut(mt)], 0.5),
            "ten times fewer",
            (lambda: [GrowFromEdge(qb2, LEFT), FadeIn(qn2)], 0.8),
            "and the average",
            (lambda: [GrowFromEdge(g2, LEFT)], 0.5),
            (lambda: [GrowFromEdge(m2, LEFT), FadeIn(n2)], 0.5),
        ])

        # ---- 6. 99.9% ---------------------------------------------------------------------------------------------------
        g3, m3, n3 = lat_row(2, 0.999, "0.51 ms")
        qb3, qn3 = q_row(2, 100, "100")
        rule = T("judge a cache by its misses", 22, GOLD_M).move_to([0, -2.95, 0])
        self.steps("At 99.9%, the average barely moves: it's already close to Redis's own half millisecond. "
                   "But the database load drops tenfold again. So judge a cache by its misses.", [
            (lambda: [FadeIn(labs[2]), GrowFromEdge(g3, LEFT)], 0.6),
            (lambda: [GrowFromEdge(m3, LEFT), FadeIn(n3)], 0.4),
            "But the database",
            (lambda: [GrowFromEdge(qb3, LEFT), FadeIn(qn3)], 0.6),
            (lambda: [Indicate(qn1, color=RED_M), Indicate(qn2, color=RED_M), Indicate(qn3, color=RED_M)], 1.0),
            "So judge",
            (lambda: [FadeIn(rule, shift=0.1 * UP)], 0.6),
        ])

        # ---- 7. what if every key were equally popular -------------------------------------------------------------------
        phaseA = VGroup(f, hl, hq, *labs, g1, m1, n1, g2, m2, n2, g3, m3, n3, qb1, qn1, qb2, qn2, qb3, qn3, rule)
        kbar = Rectangle(width=KW, height=0.5, stroke_color=GREY_B, stroke_width=2).move_to([KX0 + KW / 2, KY, 0])
        rbar = Rectangle(width=KW, height=0.5, stroke_color=GREY_B, stroke_width=2).move_to([KX0 + KW / 2, RY, 0])
        kl = right_at(T("merchants", 20, GREY_B), KX0 - 0.2, KY)
        rl = right_at(T("lookups", 20, GREY_B), KX0 - 0.2, RY)
        kin = T("1,000,000 merchants", 17, GREY_B).move_to([KX0 + 7.0, KY, 0])
        rin = right_at(T("all lookups", 17, GREY_B), KX0 + KW - 0.12, RY)
        uni = band(0.1, 0.1)
        ukl = left_at(T("the cache holds 10%", 20, GOLD_M), KX0, KY + 0.5)
        url = left_at(T("10% of lookups hit", 20, GOLD_M), KX0, RY - 0.5)
        self.steps("How does a small cache reach 99%? If all million merchants were equally popular, a cache holding "
                   "a tenth of them would hit a tenth of the time.", [
            (lambda: [FadeOut(phaseA)], 0.7),
            (lambda: [Create(kbar), Create(rbar), FadeIn(kl), FadeIn(rl), FadeIn(kin), FadeIn(rin)], 0.9),
            "a cache holding",
            (lambda: [FadeIn(uni[1]), FadeIn(ukl), Transform(red[2], T("holds 100,000 merchants", 16, GREY_B).move_to(red[2]))], 0.6),
            "would hit",
            (lambda: [FadeIn(uni[0]), FadeIn(uni[2]), FadeIn(url)], 0.8),
        ])

        # ---- 8. skew ----------------------------------------------------------------------------------------------------
        c1 = chip("a supermarket chain: thousands of payments a minute", GOLD_M, 18).move_to([-1.9, (KY + RY) / 2, 0])
        c2 = chip("a bike repair shop: 2 a day", GREY_B, 18).move_to([3.6, (KY + RY) / 2, 0])
        self.steps("But real traffic is skewed. A supermarket chain pays thousands of times a minute. "
                   "A bike repair shop, twice a day.", [
            (lambda: [uni.animate.set_opacity(0), FadeOut(ukl), FadeOut(url)], 0.6),
            "A supermarket",
            (lambda: [FadeIn(c1, shift=0.1 * DOWN)], 0.6),
            "A bike repair",
            (lambda: [FadeIn(c2, shift=0.1 * DOWN)], 0.6),
        ])

        # ---- 9. a few hot keys get most lookups -------------------------------------------------------------------------
        tkl = left_at(T("the top 1,000 merchants: 0.1%", 20, GOLD_M), KX0, KY + 0.5)
        trl = right_at(T("52% of lookups", 20, GOLD_M), KX0 + 5.2, RY - 0.5)
        tkl2 = left_at(T("the top 10% of merchants", 20, GOLD_M), KX0, KY + 0.5)
        trl2 = right_at(T("84% of lookups", 20, GOLD_M), KX0 + 8.4, RY - 0.5)
        self.steps("With a common amount of skew, the top 1,000 merchants, a tenth of a percent, get half of all lookups. "
                   "The top 10% get 84%.", [
            (lambda: [FadeOut(c1), FadeOut(c2), Transform(red[2], T("holds 1,000 merchants", 16, GREY_B).move_to(red[2]))], 0.6),
            "the top 1,000",
            (lambda: [Transform(uni[1], band(0.001, 0.52)[1]), FadeIn(tkl)], 0.6),
            "get half",
            (lambda: [Transform(uni[0], band(0.001, 0.52)[0]), Transform(uni[2], band(0.001, 0.52)[2]), FadeIn(trl)], 1.0),
            "The top 10%",
            (lambda: [Transform(uni, band(0.1, 0.84)), Transform(tkl, tkl2), Transform(trl, trl2)], 1.0),
        ])

        # ---- 10. the sentence to keep -------------------------------------------------------------------------------------
        self.steps("A small cache works because a few keys are hot. Then count its misses: from 90 to 99% hits, "
                   "the slow trips fall tenfold.", [
            (lambda: [glow(red[0], GREEN_M)], 0.8),
            "Then count",
            (lambda: [miss(), hit(0.2), hit(0.6), hit(1.0)], 1.9),
        ])
        self.wait(0.6)
