from sfz import *

SAY.insert(0, (r"(\d)%", r"\1 percent"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
FX, FW, FLOW_Y = [-4.6, 0.0, 4.6], 3.2, 2.85        # program -> cache (the jug) -> database (the storeroom)
GX0, GY0, GP = -6.1, 1.4, 0.36                      # 100 lookups: a 10 x 10 grid of dots
TCOL, THEAD, TROW = [-0.9, 2.0, 5.0], 1.55, [0.95, 0.35, -0.25]   # the results table
MATH_X, MATH_Y1, MATH_Y2 = -1.7, -1.05, -1.6
PAYY = [1.2, 0.5, -0.2, -0.9]                       # four payments of 30 lookups
CODE_Y = -1.45
BAR_Y, CAP_Y = -2.75, -3.25
MISS = sorted(np.random.default_rng(11).choice(100, 10, replace=False).tolist(), key=lambda i: (i * 37) % 100)


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
            if callable(it):
                it()
                continue
            fn, rt = it
            self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.07, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))




class HitRatio(Base):
    """cache-01, section 2. The barista's jug and the storeroom. A cache that goes from 90 to 99 lookups in 100: nine
    points? Map: jug = cache, storeroom = database, hit and miss; Redis 0.5 ms, database 10 ms, 100,000 lookups a
    second. 90%: 1.45 ms and 10,000 a second. Predict 99%: 1,000 a second, 0.595 ms. Count the misses: hit ratio and
    miss ratio; 99.9%: 0.5095 ms and 100. Thirty lookups a payment: 0.99^30 = 74%. The formulas in Java and Kotlin.
    The moral, and a check (95% to 99%: five times fewer)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
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

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b), run_time=secs, rate_func=linear)

    def flab(self, k, title, sub, color=WHITE):
        g = VGroup(T(title, 20, color), T(sub, 17, GREY_B)).arrange(DOWN, buff=0.08).move_to([FX[k], FLOW_Y, 0])
        fit(g, FW - 0.25)
        return self.put(f"f{k}", g)

    def math(self, a, b=None, color=WHITE):
        out = self.put("m1", left_at(T(a, 22, color), MATH_X, MATH_Y1))
        if b is not None:
            out += self.put("m2", left_at(T(b, 22, color), MATH_X, MATH_Y2))
        return out

    def trow(self, r, vals, color=WHITE):
        g = VGroup(*[T(v, 22, color).move_to([x, TROW[r], 0]) for v, x in zip(vals, TCOL)])
        return self.put(f"r{r}", g)

    def paint(self, idx, color, op=1.0):
        return [self.dots[i].animate.set_fill(color, op) for i in idx]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Nine points, or ten times?", "why 99% hits is ten times better than 90%")

        boxes = [RoundedRectangle(corner_radius=0.14, width=FW, height=0.8, stroke_color=c, stroke_width=3).set_fill(fillc(c), 1)
                 .move_to([x, FLOW_Y, 0]) for x, c in zip(FX, [GREY_B, TEAL_M, RED_M])]
        a1 = Arrow([FX[0] + FW / 2, FLOW_Y, 0], [FX[1] - FW / 2, FLOW_Y, 0], buff=0.08, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.15)
        a2 = Arrow([FX[1] + FW / 2, FLOW_Y, 0], [FX[2] - FW / 2, FLOW_Y, 0], buff=0.08, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.15)
        P0, P1, P2 = [np.array([x, FLOW_Y - 0.55, 0]) for x in FX]

        def hit_run(rt=0.5):
            return Succession(dot_run(P0, P1, GREEN_M, rt), dot_run(P1, P0, GREEN_M, rt))

        def miss_run(rt=0.6):
            return Succession(dot_run(P0, P1, RED_M, rt * 0.6), dot_run(P1, P2, RED_M, rt * 1.6), dot_run(P2, P0, RED_M, rt * 2.2))

        # ---------------- scene 1: the jug, and the question ----------------
        self.steps("Picture a busy café. The barista makes a latte every thirty seconds, and never walks to the storeroom for milk.", [
            (lambda: [FadeIn(boxes[0]), *self.flab(0, "the barista", "a latte every 30 seconds")], 0.7),
            "never walks",
            (lambda: [FadeIn(boxes[2]), GrowArrow(a2), *self.flab(2, "the storeroom", "at the back")], 0.7),
        ])
        self.steps("A jug sits on the counter, and she goes to the back only when it runs out. Walking takes far longer than pouring.", [
            (lambda: [FadeIn(boxes[1]), GrowArrow(a1), *self.flab(1, "the jug of milk", "on the counter")], 0.7),
            "only when it runs out",
            (lambda: [hit_run(0.35)], 0.8),
            "Walking takes",
            (lambda: [miss_run(0.7)], 3.1),
        ])
        self.steps("The payments program behind the card reader has the same choice. For every tap, it needs the shop's details "
                   "from a database on another computer. So it keeps a copy close by.", [
            (lambda: self.flab(0, "payments program", "every card tap"), 0.6),
            "from a database",
            (lambda: self.flab(2, "database", "on another computer"), 0.6),
            "a copy close by",
            (lambda: self.flab(1, "a copy close by", "the shop's details"), 0.6),
        ])
        self.steps("Say that copy answers 90 lookups in 100, and someone tunes it to 99. Nine points better. Is that a small win, "
                   "or a big one? Hold that thought.", [
            (lambda: self.cap("the copy answers 90 lookups in 100 ... then 99 in 100", WHITE), 0.6),
            "Nine points",
            (lambda: self.cap("nine points better: a small win, or a big one?", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 2: map it ----------------
        self.steps("Let's map the café. The jug is the cache: a small, fast store of copies. The storeroom is the database.", [
            (lambda: [*self.uncap(), glow(boxes[1], TEAL_M, 1.03), *self.cap("the jug = the cache: a small, fast store of copies", TEAL_M)], 0.7),
            "The storeroom",
            (lambda: [glow(boxes[2], RED_M, 1.03), *self.cap("the storeroom = the database", RED_M)], 0.6),
        ])
        self.steps("A lookup the jug can answer is a hit. One that sends you to the back is a miss.", [
            (lambda: [hit_run(0.4), *self.cap("a hit: answered by the cache", GREEN_M)], 0.9),
            "a miss",
            (lambda: [miss_run(0.5), *self.cap("a miss: on to the database", RED_M)], 2.2),
        ])
        self.steps("Here the cache is Redis, a program that holds data in memory and hands it out over the network.", [
            (lambda: self.flab(1, "Redis, the cache", "data in memory, over the network"), 0.7),
        ])
        self.steps("Round numbers, made up for teaching: a lookup takes half a millisecond from Redis, and 10 milliseconds from a "
                   "busy database. At the busiest hour, there are 100,000 lookups a second.", [
            (lambda: self.cap("round numbers, made up for teaching", GREY_B), 0.5),
            "half a millisecond",
            (lambda: self.flab(1, "Redis cache", "0.5 ms a lookup", TEAL_M), 0.6),
            "10 milliseconds",
            (lambda: self.flab(2, "database", "10 ms a lookup", RED_M), 0.6),
            "100,000 lookups",
            (lambda: self.flab(0, "payments program", "100,000 lookups a second"), 0.6),
        ], after=0.3)

        # ---------------- scene 3: ninety in a hundred ----------------
        self.dots = [Dot(radius=0.11, color=GREEN_M).move_to([GX0 + GP * (i % 10), GY0 - GP * (i // 10), 0]) for i in range(100)]
        glab = T("100 lookups", 20, GREY_B).move_to([GX0 + GP * 4.5, GY0 + 0.42, 0])
        head = VGroup(*[T(h, 19, GREY_B).move_to([x, THEAD, 0]) for h, x in zip(["hit ratio", "average lookup", "database load"], TCOL)])
        hline = Line([TCOL[0] - 0.9, THEAD - 0.28, 0], [6.45, THEAD - 0.28, 0], stroke_width=1.5, color=GREY_C)
        self.steps("Take 100 lookups at 90% hits. Ninety pour from the jug. Ten walk to the storeroom.", [
            (lambda: [*self.uncap(), FadeIn(glab), FadeIn(head), Create(hline)], 0.5),
            "Ninety pour",
            (lambda: [LaggedStart(*[FadeIn(d, scale=0.5) for d in self.dots], lag_ratio=0.01)], 1.0),
            "Ten walk",
            (lambda: self.paint(MISS, RED_M), 0.6),
            (lambda: [LaggedStart(*[Indicate(self.dots[i], color=RED_M, scale_factor=1.6) for i in MISS], lag_ratio=0.1)], 0.8),
        ])
        self.steps("The average lookup is 0.9 times 0.5, plus 0.1 times 10: 1.45 milliseconds.", [
            (lambda: self.math("average: 0.9 x 0.5 + 0.1 x 10 = 1.45 ms"), 0.6),
        ])
        self.steps("And the database gets the misses: 10% of 100,000, so 10,000 queries a second.", [
            (lambda: [*self.math("average: 0.9 x 0.5 + 0.1 x 10 = 1.45 ms", "database: 0.1 x 100,000 = 10,000 a second"),
                      *[Indicate(self.dots[i], color=RED_M, scale_factor=1.5) for i in MISS]], 0.7),
            "10,000 queries",
            (lambda: self.trow(0, ["90%", "1.45 ms", "10,000 a second"]), 0.6),
        ], after=0.3)

        # ---------------- scene 4: predict 99% ----------------
        self.steps("Now 99% hits. Before we count, how many queries reach the database each second? Pause and guess.", [
            (lambda: [*self.drop("m1", "m2"), *self.cap("99% hits: how many database queries a second?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("1,000. Ten times fewer: one red dot in a hundred, instead of ten.", [
            (lambda: [*self.uncap(), *self.paint(MISS[1:], GREEN_M)], 0.8),
            (lambda: [*self.math("database: 0.01 x 100,000 = 1,000 a second", None, WHITE), Indicate(self.dots[MISS[0]], color=RED_M, scale_factor=1.8)], 0.6),
            "Ten times fewer",
            (lambda: self.cap("ten times fewer: 1 miss in 100, instead of 10", WHITE), 0.6),
        ])
        self.steps("And the average drops to 0.595 milliseconds, more than twice as fast.", [
            (lambda: [*self.math("average: 0.99 x 0.5 + 0.01 x 10 = 0.595 ms", "database: 0.01 x 100,000 = 1,000 a second"),
                      *self.trow(1, ["99%", "0.595 ms", "1,000 a second"])], 0.7),
        ], after=0.3)

        # ---------------- scene 5: count the misses ----------------
        self.steps("So where did nine points come from? We counted the hits, and 90 and 99 look close.", [
            (lambda: [*self.drop("m1", "m2"), *self.cap("nine points: that's counting the hits", PURPLE_M)], 0.6),
            "We counted the hits",
            (lambda: [LaggedStart(*[Indicate(self.dots[i], color=GREEN_M, scale_factor=1.3) for i in range(100) if i not in MISS[:1]], lag_ratio=0.005)], 1.0),
        ])
        self.steps("But the database never sees a hit. It sees only the misses, and 10 misses against 1 is ten times the load.", [
            "never sees a hit",
            (lambda: [*[self.dots[i].animate.set_fill(GREEN_M, 0.25) for i in range(100) if i != MISS[0]], glow(boxes[2], RED_M, 1.03)], 0.7),
            "10 misses against 1",
            (lambda: [*self.cap("10 misses against 1: ten times the load", RED_M),
                      Indicate(self.lab["r0"][2], color=RED_M), Indicate(self.lab["r1"][2], color=RED_M)], 0.8),
        ])
        self.steps("The share of hits is the hit ratio, and what's left is the miss ratio. 98% hits and 2% misses describe the same "
                   "cache. Only the second tells you what the database sees.", [
            (lambda: self.math("hit ratio h = hits / all lookups", "miss ratio = 1 - h", WHITE), 0.6),
            "98% hits",
            (lambda: self.cap("98% hits = 2% misses: the same cache", WHITE), 0.6),
            "Only the second",
            (lambda: self.cap("only the misses reach the database", RED_M), 0.6),
        ])
        self.steps("Ninety-nine percent sounds like top marks, but the database only marks the one percent.", [
            (lambda: [Indicate(self.dots[MISS[0]], color=RED_M, scale_factor=2.0)], 0.9),
        ], after=0.2)
        tiny = T("99.9%: 1 miss in 1,000", 19, RED_M).move_to([GX0 + GP * 4.5, GY0 - GP * 9 - 0.45, 0])
        self.steps("Push on to 99.9%. The average hardly moves, 0.5095 milliseconds, because it's already close to the cache's own "
                   "half a millisecond.", [
            (lambda: [*self.uncap(), self.dots[MISS[0]].animate.scale(0.4), FadeIn(tiny), *[d.animate.set_fill(GREEN_M, 1) for d in self.dots if d is not self.dots[MISS[0]]],
                      *self.math("average: 0.999 x 0.5 + 0.001 x 10 = 0.5095 ms", "database: 0.001 x 100,000 = 100 a second")], 0.8),
            "The average hardly",
            (lambda: [*self.trow(2, ["99.9%", "0.5095 ms", "100 a second"]), *self.cap("the average: close to the cache's own 0.5 ms", WHITE)], 0.6),
            (lambda: [LaggedStart(*[Indicate(self.lab[f"r{r}"][1], color=YELLOW_M) for r in range(3)], lag_ratio=0.3)], 0.9),
        ])
        self.steps("But the database load falls tenfold again: 100 a second.", [
            (lambda: [*self.cap("the database: 10,000, then 1,000, then 100 a second", RED_M),
                      LaggedStart(*[Indicate(self.lab[f"r{r}"][2], color=RED_M) for r in range(3)], lag_ratio=0.3)], 1.0),
        ], after=0.4)
        self.stamp("table")

        # ---------------- scene 6: thirty lookups ----------------
        sq = [[Rectangle(width=0.1, height=0.3, stroke_width=0).set_fill(GREEN_M, 1).move_to([GX0 - 0.05 + 0.118 * k, PAYY[p], 0]) for k in range(30)] for p in range(4)]
        sq[2][17].set_fill(RED_M, 1)
        plabs = [T(f"payment {p + 1}", 16, GREY_B).move_to([GX0 + 1.7, PAYY[p] + 0.3, 0]) for p in range(4)]
        self.steps("One more trap. A card payment doesn't make one lookup. Say it makes 30, each with 99% hits.", [
            (lambda: [*self.uncap(), *self.drop("m1", "m2"), FadeOut(VGroup(*self.dots, tiny, glab))], 0.6),
            "Say it makes 30",
            (lambda: [LaggedStart(*[FadeIn(VGroup(plabs[p], *sq[p])) for p in range(4)], lag_ratio=0.25),
                      *self.cap("one payment: 30 lookups, each 99% hits", WHITE)], 1.0),
        ])
        self.steps("All 30 hit only 74% of the time: 0.99 multiplied by itself 30 times.", [
            (lambda: self.math("all 30 hit:  0.99^30 = 0.74", None, WHITE), 0.6),
        ])
        self.steps("So about one payment in four waits for at least one slow read. A cache with a great average still leaves many "
                   "requests slow.", [
            (lambda: [Indicate(sq[2][17], color=RED_M, scale_factor=2.5), *self.math("all 30 hit:  0.99^30 = 0.74", "about 1 payment in 4 meets a miss", WHITE)], 0.8),
            "A cache with",
            (lambda: self.cap("a great average still leaves many requests slow", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 7: the formulas as code ----------------
        JAVA = ["double avgMs = h * hitMs + (1 - h) * missMs;", "double dbPerSec = (1 - h) * lookupsPerSec;"]
        KOT = ["val avgMs = h * hitMs + (1 - h) * missMs", "val dbPerSec = (1 - h) * lookupsPerSec"]

        def panel(x0, x1, title, lines):
            r = RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=1.45, stroke_color=GREY_B, stroke_width=2).set_fill("#111111", 1) \
                .move_to([(x0 + x1) / 2, CODE_Y, 0])
            t = left_at(T(title, 17, GREY_B), x0 + 0.2, CODE_Y + 0.48)
            ls = [left_at(M(s, 15), x0 + 0.2, CODE_Y + 0.05 - 0.42 * k) for k, s in enumerate(lines)]
            for l in ls:
                fit(l, x1 - x0 - 0.35)
                left_at(l, x0 + 0.2, l.get_center()[1])
            return VGroup(r, t, *ls)
        pj = panel(-6.45, -0.12, "Java", JAVA)
        pk = panel(0.12, 6.45, "Kotlin", KOT)
        self.steps("Here are the two formulas as code, in Java and Kotlin.", [
            (lambda: [*self.uncap(), *self.drop("m1", "m2"), FadeOut(VGroup(*plabs, *[s for row in sq for s in row]))], 0.5),
            (lambda: [FadeIn(pj, shift=0.1 * UP), FadeIn(pk, shift=0.1 * UP)], 0.7),
        ])
        self.steps("The average is h times the hit time, plus one minus h, times the miss time. The database's load is one minus h, "
                   "times the lookups.", [
            (lambda: [Indicate(pj[2], color=YELLOW_M, scale_factor=1.04), Indicate(pk[2], color=YELLOW_M, scale_factor=1.04),
                      LaggedStart(*[Indicate(self.lab[f"r{r}"][1], color=YELLOW_M) for r in range(3)], lag_ratio=0.2)], 1.2),
            "The database's load",
            (lambda: [Indicate(pj[3], color=RED_M, scale_factor=1.04), Indicate(pk[3], color=RED_M, scale_factor=1.04),
                      LaggedStart(*[Indicate(self.lab[f"r{r}"][2], color=RED_M) for r in range(3)], lag_ratio=0.2)], 1.2),
        ], after=0.3)
        self.stamp("code")

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, nine points: small win or big? Big. Ninety to ninety-nine is ten times fewer misses, and the misses are what "
                   "the database pays for. Count the misses, not the hits.", [
            (lambda: [FadeOut(pj), FadeOut(pk), *self.cap("nine points: small win or big?", WHITE)], 0.6),
            "Big.",
            (lambda: [*self.cap("big: ten times fewer misses", GREEN_M, 26), Indicate(self.lab["r0"][2], color=RED_M), Indicate(self.lab["r1"][2], color=RED_M)], 0.8),
            "Count the misses",
            (lambda: self.cap("count the misses, not the hits", YELLOW_M, 26), 0.6),
        ], after=0.3)
        CHK = MISS[:5]
        for d in self.dots:
            d.set_fill(GREEN_M, 1).scale_to_fit_width(0.22)
        for i in CHK:
            self.dots[i].set_fill(RED_M, 1)
        glab2 = T("95% hits: 100 lookups", 20, GREY_B).move_to(glab)
        self.steps("One quick check. A cache goes from 95% hits to 99%. How many times fewer requests reach the database? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(glab2), LaggedStart(*[FadeIn(d, scale=0.5) for d in self.dots], lag_ratio=0.008)], 1.0),
            "Pause and think",
            (lambda: self.cap("95% → 99%: how many times fewer database requests?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Misses drop from 5 in 100 to 1 in 100: five times fewer.", [
            (lambda: [*self.uncap(), *self.paint(CHK[1:], GREEN_M), *self.math("misses: 5 in 100 → 1 in 100", "five times fewer requests reach the database", GREEN_M)], 0.8),
        ], after=0.3)
        self.play(*self.cap("the database feels only the misses: count them", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
