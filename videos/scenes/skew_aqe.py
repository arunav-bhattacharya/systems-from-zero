from sfz import *

SAY.insert(0, (r"\bgroupBy\b", "group by"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Y0, SC = -2.45, 3.3 / 346023              # bar baseline, units per row
XL, XR = -6.1, 2.0                         # chart left and right
HOT = 15                                   # shop 7's partition: the last till
# rows each join task fetches from shops other than shop 7 (hand-picked around the demo's median of 43,593)
BASE = [43100, 44200, 42800, 43593, 44900, 43700, 43000, 44500, 42500, 43900, 50793, 44800, 42900, 43593, 44100, 46023]
RED7 = 300000                              # shop 7's payments
SLICE = RED7 // 8                          # one salt's share: 37,500
SALTS = [1, 3, 3, 8, 10, 10, 12, 14]       # where the 8 salted keys of shop 7 land (two pairs share)
NX = 2.45
NY = [0.75, 0.25, -0.25, -0.75, -1.25]
PAY = np.array([-3.9, 2.65, 0])
MER = np.array([0.2, 2.65, 0])
CAP_Y, BAR_Y = -3.33, 1.6


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

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

    def note(self, k, s, color=GREY_B, size=20):
        m = T(s, size, color)
        fit(m, 6.6 - NX)
        return self.put(f"n{k}", m.move_to([NX + m.width / 2, NY[k], 0]))

    def notes_off(self):
        return self.drop(*[f"n{k}" for k in range(len(NY))])

    def countdown(self, secs=3.0):
        bar = Line([NX + 0.2, BAR_Y, 0], [NX + 2.2, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def slot(i, n=16):
    step = (XR - XL - 0.2) / n
    return XL + 0.1 + step * (i + 0.5), step * 0.68


def ytop(v):
    return Y0 + v * SC


def seg(i, lo, hi, color, n=16, op=0.88):
    x, w = slot(i, n)
    r = Rectangle(width=w, height=max(0.004, (hi - lo) * SC), stroke_width=0).set_fill(color, op)
    return r.move_to([x, ytop(lo) + r.height / 2, 0])


def chart(parts, n=16):
    """parts[i] = list of (rows, colour) stacked from the bottom."""
    g = VGroup()
    for i, p in enumerate(parts):
        col, lo = VGroup(), 0
        for v, c in p:
            col.add(seg(i, lo, lo + v, c, n))
            lo += v
        g.add(col)
    return g


def hline(v, color):
    y = ytop(v)
    return DashedLine([XL, y, 0], [XR, y, 0], dash_length=0.1, stroke_width=2, color=color)


def flow(a, b, color, rt=0.8):
    d = Dot(radius=0.075, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.15))


def table_box(c, title, sub, color, w=3.4):
    return VGroup(RoundedRectangle(corner_radius=0.12, width=w, height=0.9, stroke_color=color, stroke_width=2.5)
                  .set_fill(fillc(color) if color is not WHITE else BLACK, 1).move_to(c),
                  T(title, 22).move_to(c + 0.17 * UP), T(sub, 18, color if color is not WHITE else RED_M).move_to(c + 0.2 * DOWN))


class SkewAqe(Base):
    """batch-08, section 2. The supermarket: 16 tills and one restaurant's trolley. Shop 7 has 30% of a million payments,
    so a sort-merge join into 16 partitions gives one task 346,023 rows against a median of 43,593. More partitions and
    backup tasks don't split a key. AQE's skew join (over 5x the median and over 256 MB) cuts along map blocks: 4 pieces,
    19 tasks, busiest 86,635. Salting with pmod(payment_id, 8) and 8 copies of each shop row: busiest 125,793, because
    8 salts in 16 partitions share. Salt from the data; try a broadcast first. A check: 32 partitions."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("One trolley holds up the shop", "skew, AQE's split and salting")

        axis = Line([XL, Y0, 0], [XR, Y0, 0], stroke_width=2.5, color=GREY_B)
        alab = T("16 tills: how much shopping each one scans", 18, GOLD_M).move_to([(XL + XR) / 2, Y0 - 0.33, 0])
        tops0 = [BASE[i] + (RED7 if i == HOT else 0) for i in range(16)]
        tills = chart([[(v, GOLD_M)] for v in tops0])
        trolley = T("a restaurant's trolley", 19, GOLD_M).move_to([slot(HOT)[0] - 0.9, ytop(346023) + 0.25, 0])

        # ---------------- scene 1: Saturday morning ----------------
        self.steps("Picture a supermarket on a Saturday morning, with 16 tills open. Fifteen queues move quickly.", [
            (lambda: [Create(axis), FadeIn(alab)], 0.6),
            "Fifteen queues",
            (lambda: [LaggedStart(*[GrowFromEdge(tills[i], DOWN) for i in range(15)], lag_ratio=0.05)], 1.2),
        ])
        self.steps("At the last till, one customer is buying a restaurant's shopping for the week, and everyone behind them waits. "
                   "One till got the work of eight.", [
            "At the last till",
            (lambda: [GrowFromEdge(tills[HOT], DOWN)], 1.2),
            (lambda: [FadeIn(trolley, shift=0.1 * UP)], 0.5),
            "One till got",
            (lambda: [*self.note(0, "one till: the work of eight", GOLD_M)], 0.6),
        ])
        self.steps("The obvious fix is to open more tills. Hold that thought.", [
            (lambda: self.cap("open more tills?", YELLOW_M), 0.5),
        ], after=0.3)

        # ---------------- scene 2: the join ----------------
        pay = table_box(PAY, "payments: 1,000,000", "shop 7: 30%", WHITE)
        mer = table_box(MER, "shops: 500 rows", "shop 7: one row", BLUE_M, 3.0)
        alab2 = T("16 join tasks: rows each one fetches", 18, GREY_B).move_to(alab)
        src = PAY + 0.5 * DOWN
        self.steps("Spark, the program that spreads a big job over many computers, meets the same thing. "
                   "Our million payments are joined with the shops in a sort-merge join, into 16 partitions. "
                   "Each partition is one task, on one processor core.", [
            (lambda: [FadeOut(tills), FadeOut(trolley), *self.notes_off(), *self.uncap()], 0.6),
            "Our million",
            (lambda: [FadeIn(pay, shift=0.1 * DOWN)], 0.6),
            "joined with the shops",
            (lambda: [FadeIn(mer, shift=0.1 * DOWN)], 0.6),
            "into 16 partitions",
            (lambda: [FadeTransform(alab, alab2)], 0.6),
            "Each partition",
            (lambda: [LaggedStart(*[flow(src, [slot(i)[0], Y0 + 0.1, 0], GREY_B, 0.6) for i in range(16)], lag_ratio=0.05)], 1.4),
        ])
        self.steps("Spark picks each row's partition from its shop number, so every payment of one shop goes to the same task. "
                   "Now, shop 7 is a marketplace, one website through which thousands of small sellers take payments. "
                   "It has 30 percent of all the payments.", [
            "so every payment",
            (lambda: self.cap("same shop number, same partition, same task", WHITE), 0.6),
            "shop 7 is a marketplace",
            (lambda: [Indicate(pay[2], color=RED_M, scale_factor=1.15)], 0.8),
            "It has 30 percent",
            (lambda: [LaggedStart(*[flow(src, [slot(HOT)[0], Y0 + 0.1, 0], RED_M, 0.6) for _ in range(14)], lag_ratio=0.07)], 1.6),
        ])
        self.steps("The tills are the tasks, and shop 7 is the restaurant's trolley.", [
            (lambda: self.cap("tills = tasks      the trolley = shop 7's payments", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 3: predict, then count ----------------
        bars = chart([[(BASE[i], GREY_B)] + ([(RED7, RED_M)] if i == HOT else []) for i in range(16)])
        med = hline(43593, GREY_C)
        medl = T("median 43,593", 17, GREY_C).next_to(med, RIGHT, buff=0.1)
        self.steps("The median task fetches 43,593 rows. How many does shop 7's task fetch? Pause and guess.", [
            (lambda: [*self.uncap(), LaggedStart(*[GrowFromEdge(b[0], DOWN) for b in bars], lag_ratio=0.03)], 1.0),
            (lambda: [Create(med), FadeIn(medl)], 0.6),
            "Pause and guess",
            (lambda: self.cap("how many rows for shop 7's task?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        hotl = T("346,023", 22, RED_M).move_to([slot(HOT)[0] - 0.2, ytop(346023) + 0.25, 0])
        self.steps("346,023. Eight times as many.", [
            (lambda: [*self.uncap(), GrowFromEdge(bars[HOT][1], DOWN)], 1.0),
            (lambda: [FadeIn(hotl, shift=0.1 * UP), *self.note(0, "8 times the median", RED_M)], 0.5),
        ])
        end = hline(346023, RED_M)
        endl = T("the stage ends here", 17, RED_M).move_to([(XL + slot(HOT)[0]) / 2 - 0.6, ytop(346023) + 0.2, 0])
        idle = VGroup(*[seg(i, BASE[i], 346023, GREY_D, op=0.35) for i in range(15)])
        self.steps("And a stage ends when its slowest task ends. So fifteen cores finish early and wait for one.", [
            "a stage ends",
            (lambda: [Create(end), FadeIn(endl)], 0.8),
            "fifteen cores",
            (lambda: [LaggedStart(*[GrowFromEdge(r, DOWN) for r in idle], lag_ratio=0.04),
                      *self.note(1, "15 cores finish early and wait")], 1.2),
        ])
        self.steps("This is skew: a few keys with far more rows than the rest. The busy key is called a hot key. "
                   "Spark's web page for a running job gives it away: the longest task runs far longer than the median.", [
            (lambda: [*self.note(2, "skew: a few keys, far more rows", WHITE)], 0.6),
            "a hot key",
            (lambda: [*self.note(3, "the busy key: a hot key", RED_M), Indicate(hotl, color=RED_M)], 0.7),
            "Spark's web page",
            (lambda: self.cap("on Spark's job page: longest task far above the median", WHITE), 0.6),
        ], after=0.3)
        self.stamp("skew")

        # ---------------- scene 4: more tills ----------------
        self.steps("So, open more tills? Shop 7 is one key, and one key lands in one partition, out of 16 or out of 2,000. "
                   "More tills, same trolley.", [
            (lambda: [*self.notes_off(), *self.cap("open more tills?", YELLOW_M)], 0.5),
            "Shop 7 is one key",
            (lambda: [*self.note(0, "16 or 2,000 partitions:"), *self.note(1, "shop 7 is still one key,"),
                      *self.note(2, "in one partition", RED_M)], 0.8),
            "More tills",
            (lambda: [*self.cap("more tills, same trolley", WHITE), glow(bars[HOT][1], RED_M, 1.03)], 0.7),
        ])
        self.steps("A backup copy of the slow task doesn't help either. It reads the same hot partition, so it's just as slow. "
                   "Two cashiers, still one trolley.", [
            (lambda: [*self.note(3, "a backup task reads the same partition")], 0.6),
            "Two cashiers",
            (lambda: self.cap("two cashiers, still one trolley", WHITE), 0.6),
        ])
        self.steps("A groupBy mostly survives skew, because each task adds up its own rows before the shuffle. "
                   "A join can't add anything up early. Every payment must meet its shop's row. So the fix has to split the key itself.", [
            (lambda: [*self.notes_off(), *self.note(0, "groupBy: adds up before the shuffle"),
                      *self.note(1, "join: every row must travel", RED_M)], 0.7),
            "So the fix",
            (lambda: self.cap("the fix: split the key itself", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 5: AQE's skew join ----------------
        self.steps("The first fix is built in. AQE, short for adaptive query execution, is the part of Spark that changes the plan "
                   "once a shuffle shows the real sizes.", [
            (lambda: [*self.notes_off(), *self.cap("fix 1: AQE, adaptive query execution", WHITE)], 0.6),
            "changes the plan",
            (lambda: [*self.note(0, "it sees every partition's real size", TEAL_M)], 0.6),
        ])
        self.steps("It calls a partition skewed when it's more than 5 times the median and also bigger than 256 MB. "
                   "Then it cuts that partition into pieces and runs each piece as its own task, with a copy of shop 7's row.", [
            "more than 5 times",
            (lambda: [*self.note(1, "skewed: over 5 × the median", TEAL_M)], 0.5),
            "also bigger",
            (lambda: [*self.note(2, "and over 256 MB", TEAL_M)], 0.5),
            "cuts that partition",
            (lambda: [glow(bars[HOT][1], TEAL_M, 1.03)], 0.7),
            "with a copy",
            (lambda: [Indicate(mer[2], color=BLUE_M, scale_factor=1.15)], 0.7),
        ])
        bags = VGroup(*[seg(HOT, BASE[HOT] + k * RED7 / 4, BASE[HOT] + (k + 1) * RED7 / 4, RED_M) for k in range(4)])
        cuts = VGroup(*[Line([slot(HOT)[0] - 0.22, ytop(BASE[HOT] + k * RED7 / 4), 0], [slot(HOT)[0] + 0.22, ytop(BASE[HOT] + k * RED7 / 4), 0],
                             stroke_width=3, color=BLACK) for k in range(1, 4)]).set_z_index(4)
        self.steps("But it can only cut along the blocks the map tasks wrote. Picture the trolley packed in four bags: "
                   "the manager can send a whole bag to another till, but won't unpack one.", [
            "the blocks",
            (lambda: [*self.notes_off(), *self.cap("AQE cuts only along the blocks the map tasks wrote", WHITE)], 0.6),
            "four bags",
            (lambda: [Create(cuts)], 0.7),
            "a whole bag",
            (lambda: [*self.note(0, "4 map tasks wrote 4 blocks: 4 bags", GOLD_M)], 0.6),
        ])
        aqe = chart([[(BASE[i], GREY_B)] for i in range(15)] +
                    [[(BASE[HOT] / 4, GREY_B), (v - BASE[HOT] / 4, RED_M)] for v in (86635, 86463, 86463, 86462)], n=19)
        alab3 = T("19 join tasks: rows each one fetches", 18, GREY_B).move_to(alab)
        busy = T("busiest: 86,635", 20, TEAL_M).move_to([slot(17, 19)[0] - 0.5, ytop(86635) + 0.6, 0])
        self.steps("Our payments came from 4 map tasks, so the hot partition becomes at most 4 pieces. "
                   "In the demo, with the thresholds scaled down, 16 tasks became 19, and the busiest fetched 86,635 rows: a quarter of before.", [
            "at most 4 pieces",
            (lambda: [FadeOut(cuts), FadeOut(idle), FadeOut(end), FadeOut(endl), FadeOut(hotl), ReplacementTransform(bars, aqe),
                      FadeOut(med), FadeOut(medl)], 1.2),
            "16 tasks became 19",
            (lambda: [FadeTransform(alab2, alab3), *self.note(1, "16 tasks became 19", TEAL_M)], 0.6),
            "the busiest",
            (lambda: [FadeIn(busy, shift=0.1 * UP), *self.cap(M("SortMergeJoin(skew=true)", 22, TEAL_M))], 0.6),
            "a quarter",
            (lambda: [*self.note(2, "346,023 → 86,635: a quarter", TEAL_M)], 0.6),
        ])
        self.steps("With the default settings, nothing happened, because the demo's hot partition is only a few megabytes.", [
            (lambda: [*self.note(3, "default settings: no change", RED_M), *self.note(4, "(the demo's partition: a few MB)")], 0.7),
        ], after=0.3)
        self.stamp("aqe")

        # ---------------- scene 6: salting ----------------
        bars2 = chart([[(BASE[i], GREY_B)] + ([(RED7, RED_M)] if i == HOT else []) for i in range(16)])
        salt = VGroup(T("Kotlin", 18, GREY_B), M('payments.withColumn("salt", pmod(col("payment_id"), lit(8)))', 19, GOLD_M)).arrange(RIGHT, buff=0.3)
        self.steps("The second fix is by hand, and it's called salting. On the payments side, add a salt: a number from 0 to 7 "
                   "worked out from the data, here the payment number's remainder after dividing by 8.", [
            (lambda: [*self.notes_off(), FadeOut(busy), ReplacementTransform(aqe, bars2), FadeTransform(alab3, alab2),
                      *self.cap("fix 2: salting", WHITE)], 1.0),
            "add a salt",
            (lambda: [Transform(pay[2], T("+ salt: 0 to 7", 18, GOLD_M).move_to(pay[2]))], 0.6),
            "the payment number's",
            (lambda: self.cap(salt), 0.6),
        ])
        self.steps("On the shops side, copy each shop row 8 times, once per salt. Then join on the shop and the salt together.", [
            (lambda: [Transform(mer[2], T("each row × 8 copies", 18, BLUE_M).move_to(mer[2]))], 0.6),
            "Then join",
            (lambda: self.cap("join on shop number and salt", WHITE), 0.6),
        ])
        slices = VGroup(*[seg(HOT, BASE[HOT] + k * SLICE, BASE[HOT] + (k + 1) * SLICE, RED_M) for k in range(8)]).set_z_index(2)
        lines8 = VGroup(*[Line([slot(HOT)[0] - 0.2, ytop(BASE[HOT] + k * SLICE), 0], [slot(HOT)[0] + 0.2, ytop(BASE[HOT] + k * SLICE), 0],
                               stroke_width=2, color=BLACK) for k in range(1, 8)]).set_z_index(4)
        home = [sl.copy() for sl in slices]
        seen = {}
        targets = []
        for k, p in enumerate(SALTS):
            lo = BASE[p] + seen.get(p, 0) * SLICE
            seen[p] = seen.get(p, 0) + 1
            targets.append(seg(p, lo, lo + SLICE, RED_M))
        self.steps("Now shop 7 is 8 keys, and they hash to different tasks, like one trolley unpacked over 8 tills.", [
            "8 keys",
            (lambda: [Create(lines8)], 0.6),
            (lambda: [FadeIn(slices), FadeOut(bars2[HOT][1]), FadeOut(lines8)], 0.2),
            "they hash",
            (lambda: [LaggedStart(*[Transform(s, t) for s, t in zip(slices, targets)], lag_ratio=0.12)], 2.0),
        ])
        busy2 = T("busiest: 125,793", 20, GOLD_M).move_to([slot(10)[0], ytop(125793) + 0.3, 0])
        self.steps("The busiest task drops to 125,793. Why not an eighth? 8 salts in 16 partitions don't land on 8 different ones. A few share.", [
            (lambda: [FadeIn(busy2, shift=0.1 * UP), *self.note(0, "346,023 → 125,793", GOLD_M)], 0.6),
            "Why not an eighth",
            (lambda: self.cap("why not an eighth?", YELLOW_M), 0.5),
            "A few share",
            (lambda: [*self.note(1, "8 salts in 16 partitions: a few share"),
                      *[glow(VGroup(slices[a], slices[b]), GOLD_M, 1.08) for a, b in ((1, 2), (4, 5))]], 0.8),
        ])
        self.steps("The price is 8 copies of the small side and a few lines of code.", [
            (lambda: [*self.note(2, "price: 8 copies of the shops", BLUE_M), Indicate(mer[2], color=BLUE_M, scale_factor=1.15)], 0.8),
        ], after=0.3)
        self.stamp("salted")

        # ---------------- scene 7: the guardrail ----------------
        a = [slot(HOT)[0], ytop(BASE[HOT]) + 0.4, 0]
        self.steps("One rule here matters more than the rest. Salt from the data, never from a random number. "
                   "When a task fails, Spark runs it again, and the new attempt must send every row where the first one did.", [
            (lambda: [*self.notes_off(), *self.cap("salt from the data, never from a random number", YELLOW_M)], 0.6),
            "When a task fails",
            (lambda: [*self.note(0, "a failed task runs again")], 0.5),
            "the new attempt",
            (lambda: [flow(a, [slot(8)[0], ytop(BASE[8] + SLICE) + 0.1, 0], GREEN_M, 0.8), *self.note(1, "first try: row → task 8", GREEN_M)], 0.9),
            (lambda: [flow(a, [slot(8)[0], ytop(BASE[8] + SLICE) + 0.1, 0], GREEN_M, 0.8), *self.note(2, "retry: same row → task 8", GREEN_M)], 0.9),
        ])
        self.steps("Roll dice instead, and rows get lost or counted twice.", [
            (lambda: [flow(a, [slot(2)[0], ytop(BASE[2]) + 0.1, 0], RED_M, 0.8), *self.note(2, "random salt: retry → task 2", RED_M)], 0.9),
            (lambda: [*self.note(3, "lost from one task, twice in another", RED_M)], 0.5),
        ])
        self.steps("And before either fix, ask whether the shops fit in a broadcast. Then the payments never move, and no partition can be hot.", [
            (lambda: [*self.notes_off(), *self.cap("first: can the small side be broadcast?", WHITE)], 0.6),
            "Then the payments",
            (lambda: [*self.note(0, "broadcast: no shuffle of payments,", BLUE_M), *self.note(1, "so no hot partition", BLUE_M),
                      glow(mer[0], BLUE_M, 1.04)], 0.8),
        ], after=0.3)

        # ---------------- scene 8: moral and check ----------------
        self.steps("So the moral of the story. A stage is as slow as its busiest task, and one hot key makes one busy task. "
                   "More partitions only open more tills. Split the key: let AQE cut the partition, or salt it by hand.", [
            (lambda: [*self.notes_off(), *self.cap("a stage is as slow as its busiest task", WHITE)], 0.6),
            "More partitions",
            (lambda: self.cap("more partitions only open more tills", WHITE), 0.5),
            "Split the key",
            (lambda: [*self.cap("split the key: AQE cuts the partition, or salt it by hand", YELLOW_M), glow(busy2, GOLD_M, 1.05)], 0.7),
        ], after=0.3)
        self.steps("One quick check. Shop 7 grows to 60 percent of the payments, and you double the partitions to 32. "
                   "Does the hot task get much smaller? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(busy2), *[Transform(sl, o) for sl, o in zip(slices, home)], Transform(pay[2], T("shop 7: 60%", 18, RED_M).move_to(pay[2])), Transform(mer[2], T("shop 7: one row", 18, BLUE_M).move_to(mer[2])),
                      *self.note(0, "60% of payments, 32 partitions", WHITE)], 0.6),
            "Pause and think",
            (lambda: self.cap("does the hot task get much smaller?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. Shop 7 is still one key in one partition. Same trolley, more tills.", [
            (lambda: [*self.note(1, "no: one key, one partition", RED_M)], 0.6),
            "Same trolley",
            (lambda: self.cap("same trolley, more tills: split the key", YELLOW_M), 0.6),
        ], after=0.3)
        self.wait(2.0)
