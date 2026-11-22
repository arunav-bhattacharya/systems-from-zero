from sfz import *

# Amounts are said the way people say them ("seventy"); captions keep "70.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CAP_Y, BAR_Y = -3.1, -2.55
LAD_X0, LAD_X1 = -6.4, -2.45                 # the ladder's rails
LAD_CX = (LAD_X0 + LAD_X1) / 2
RUNG_Y = [2.35, 1.35, 0.35, -0.65, -1.65]
RUNG_W, RUNG_H = 3.5, 0.62
H_NAME_X, H_X0, H_SCALE = -1.55, 0.05, 0.059  # history: names, time zero, units per tick
ROW_Y = [1.9, 0.9, -0.1, -1.1]
H_TTL_Y = 2.95
MODELS = ["linearizable", "sequential", "causal", "read your writes", "monotonic reads", "eventual"]


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

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0, y=BAR_Y):
        bar = Line([-1.0, y, 0], [1.0, y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def relabel(b, s, size=22):
    old, new = b[1], T(s, size).move_to(b[1])
    b.submobjects[1] = new
    return Succession(FadeOut(old, shift=0.1 * UP), FadeIn(new, shift=0.1 * UP))


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def glow(m, color=YELLOW_M, s=1.05):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


# ---- the ladder ----
def rung_box(i):
    """Rung boxes in MODELS order; the session rung holds two half boxes side by side."""
    if i < 3:
        x, y, w = LAD_CX, RUNG_Y[i], RUNG_W
    elif i == 5:
        x, y, w = LAD_CX, RUNG_Y[4], RUNG_W
    else:
        w = RUNG_W / 2 - 0.06
        x = LAD_CX + (-1 if i == 3 else 1) * (RUNG_W / 4 + 0.03)
        y = RUNG_Y[3]
    r = RoundedRectangle(corner_radius=0.1, width=w, height=RUNG_H, stroke_color=GREY_B, stroke_width=2.5)
    r.set_fill("#111111", 1).move_to([x, y, 0])
    t = fit(T(MODELS[i], 22 if i < 3 or i == 5 else 18), w - 0.2).move_to(r)
    return VGroup(r, t)


def ladder():
    rails = VGroup(*[Line([x, RUNG_Y[0] + 0.6, 0], [x, RUNG_Y[4] - 0.55, 0], stroke_width=4, color=GREY_C)
                     for x in (LAD_X0 + 0.05, LAD_X1 - 0.05)])
    rungs = [rung_box(i) for i in range(6)]
    top = T("stronger", 18, GREY_B).move_to([LAD_CX, RUNG_Y[0] + 0.78, 0])
    return rails, rungs, top


# ---- histories ----
def tx(t):
    return H_X0 + t * H_SCALE


def bar(row, t0, t1, label, color=BLUE_M):
    y = ROW_Y[row]
    w = (t1 - t0) * H_SCALE
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.46, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.22), 1).move_to([tx(t0) + w / 2, y, 0])
    return VGroup(r, fit(M(label, 18), w - 0.12).move_to(r))


def history(title, names, bars):
    """names: one per row; bars: (row, t0, t1, label, color)."""
    g = VGroup(T(title, 24, WHITE).move_to([2.4, H_TTL_Y, 0]))
    for k, n in enumerate(names):
        g.add(left_at(T(n, 20, GREY_B), H_NAME_X, ROW_Y[k]))
        g.add(Line([tx(0) - 0.1, ROW_Y[k], 0], [tx(106) + 0.1, ROW_Y[k], 0], stroke_width=1.2, color=GREY_D))
    for b in bars:
        g.add(bar(*b))
    return g


W_C, R_C = GOLD_M, BLUE_M
HIST = [
    ("1. one copy", ["checkout", "ledger"],
     [(0, 0, 32, "w b=70", W_C), (1, 46, 78, "r b:70", R_C)],
     [1, 1, 1, 1, 1, 1]),
    ("2. stale", ["checkout", "ledger"],
     [(0, 0, 32, "w b=70", W_C), (1, 46, 78, "r b:-", R_C)],
     [0, 1, 1, 1, 1, 1]),
    ("3. opposite orders", ["eu", "us", "ledger", "fraud"],
     [(0, 0, 26, "w s=2", W_C), (1, 0, 26, "w s=3", W_C), (2, 36, 60, "r s:2", R_C), (2, 70, 94, "r s:3", R_C),
      (3, 36, 60, "r s:3", R_C), (3, 70, 94, "r s:2", R_C)],
     [0, 0, 1, 1, 1, 1]),
    ("4. answer before question", ["agent", "merchant", "auditor"],
     [(0, 0, 18, "w q=1", W_C), (1, 22, 40, "r q:1", R_C), (1, 44, 62, "w a=2", W_C), (2, 66, 84, "r a:2", R_C),
      (2, 88, 106, "r q:-", R_C)],
     [0, 0, 0, 1, 1, 1]),
    ("5. own write missing", ["checkout"],
     [(0, 0, 36, "w b=70", W_C), (0, 50, 86, "r b:-", R_C)],
     [0, 0, 0, 0, 1, 1]),
    ("6. balance goes back", ["checkout", "ledger"],
     [(0, 0, 30, "w b=70", W_C), (1, 40, 66, "r b:70", R_C), (1, 76, 102, "r b:-", R_C)],
     [0, 0, 0, 1, 0, 1]),
]


class ConsistencyModels(Base):
    """cons-01, section 1. A shared card shows 70.00 on one phone and 100.00 on another: with three copies, what may a
    read return? Three noticeboards (the copies) and a ladder of house rules. The lesson's six stepper histories,
    each knocking out one more rung: linearizable, sequential (Lamport 1979), causal, read your writes, monotonic
    reads; eventual holds throughout. The name, the cost (availability when the network splits), the moral, and a
    check: the sister's 100.00 breaks only the top rung."""

    def construct(self):
        self.capm = None
        self.rungs = None
        self.title_card("What may a read return?", "a ladder of promises, from one copy down to eventual")

        # ---------------- scene 1: the shared card ----------------
        you = box("your phone", BLUE_M, w=3.0, h=1.5, size=24).move_to([-3.2, 0.3, 0])
        sis = box("sister's phone", PURPLE_M, w=3.0, h=1.5, size=24).move_to([3.2, 0.3, 0])
        for p in (you, sis):
            p[1].move_to(p[0].get_center() + 0.4 * UP)
        yv = M("70.00", 34).move_to(you[0].get_center() + 0.25 * DOWN)
        sv = M("100.00", 34, RED_M).move_to(sis[0].get_center() + 0.25 * DOWN)
        pay = chip("coffee: -30.00", GOLD_M, 22, mono=True).move_to([-3.2, 2.1, 0])
        self.steps("You share a card with your sister. You pay 30.00 for coffee, and your app shows 70.00 left.", [
            (lambda: [FadeIn(you, shift=0.1 * UP), FadeIn(sis, shift=0.1 * UP)], 0.8),
            "You pay",
            (lambda: [FadeIn(pay, shift=0.2 * DOWN)], 0.5),
            "your app shows",
            (lambda: [FadeIn(yv)], 0.5),
        ])
        sv2 = M("70.00", 34).move_to(sv)
        sv3 = sv.copy()
        self.steps("A moment later, her app shows 100.00, as if you'd never paid. She refreshes: 70.00.", [
            "her app shows",
            (lambda: [FadeIn(sv)], 0.5),
            (lambda: [Indicate(sv, color=RED_M, scale_factor=1.15)], 0.7),
            "She refreshes",
            (lambda: [swap(sv, sv2)], 0.6),
        ])
        cps = [box("copy", GREY_B, w=1.9, h=1.1, size=22).move_to([x, -2.0, 0]) for x in (-2.6, 0, 2.6)]
        for c in cps:
            c[1].move_to(c[0].get_center() + 0.25 * UP)
        cv = [M(s, 24, c).move_to(cps[i][0].get_center() + 0.2 * DOWN) for i, (s, c) in enumerate([("70.00", WHITE), ("100.00", GREY_B), ("100.00", GREY_B)])]
        a1 = edge_arrow(you, cps[0])
        a2 = edge_arrow(sis, cps[2])
        self.steps("Nothing is broken. The company keeps each balance on three computers, so losing one loses nothing. "
                   "Your payment reached one copy first, and her phone asked a copy that hadn't heard yet.", [
            (lambda: [FadeOut(pay), swap(sv2, sv3)], 0.5),
            "three computers",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in cps], lag_ratio=0.2)], 0.9),
            (lambda: [FadeIn(cv[1]), FadeIn(cv[2])], 0.4),
            "Your payment reached",
            (lambda: [GrowArrow(a1), FadeIn(cv[0])], 0.6),
            "her phone asked",
            (lambda: [GrowArrow(a2), Indicate(cv[2], color=RED_M, scale_factor=1.2)], 0.7),
        ])
        self.steps("So here's the real question. With three copies, what is a read allowed to return? Was that 100.00 a bug?", [
            (lambda: self.cap("with three copies, what may a read return?", WHITE), 0.6),
        ])

        # ---------------- scene 2: one copy, then noticeboards ----------------
        self.steps("On one computer the answer is easy. A read returns the last value written, like a variable in a program. "
                   "With three copies, the last value depends on which copy you ask, and when.", [
            (lambda: self.cap("one computer: a read returns the last value written"), 0.5),
            "With three copies",
            (lambda: self.cap("three copies: the last value depends on which copy, and when", WHITE), 0.5),
        ])
        walk = Line(cps[0][0].get_right(), cps[1][0].get_left())
        walk2 = Line(cps[1][0].get_right(), cps[2][0].get_left())
        self.steps("Picture three noticeboards in three rooms of a house. You write the new balance on the nearest board, "
                   "and somebody carries it to the other two, sooner or later. A read is a glance at the board in the room you're in.", [
            (lambda: [*self.uncap(), *[relabel(c, "board") for c in cps]], 0.7),
            "You write",
            (lambda: [Indicate(cv[0], color=GOLD_M, scale_factor=1.2)], 0.6),
            "somebody carries it",
            (lambda: [travel(walk, YELLOW_M, 0.7)], 0.8),
            (lambda: [Transform(cv[1], M("70.00", 24).move_to(cv[1]))], 0.3),
            "A read is a glance",
            (lambda: [glow(cps[2][0], PURPLE_M)], 0.7),
        ])
        self.steps("The boards are the copies, the walk between rooms is the delay, and the glance is a read. "
                   "What we need is a set of house rules. What may a glance show?", [
            (lambda: self.cap("board  =  copy"), 0.4),
            "the walk",
            (lambda: self.cap("the walk between rooms  =  the delay"), 0.4),
            "the glance",
            (lambda: self.cap("a glance  =  a read"), 0.4),
            "house rules",
            (lambda: self.cap("house rules: what may a glance show?", WHITE), 0.4),
        ])

        # ---------------- scene 3: a history, and the ladder ----------------
        rails, rungs, top = ladder()
        self.rungs = rungs
        h = [None]

        def show_hist(k):
            title, names, bars, _ = HIST[k]
            new = history(title, names, bars)
            old, h[0] = h[0], new
            anims = [FadeOut(old)] if old is not None else []
            return anims + [FadeIn(new[:1 + 2 * len(names)], shift=0.1 * UP)], new

        def show_bars(new, names_n):
            return [LaggedStart(*[FadeIn(b, shift=0.1 * RIGHT) for b in new[1 + 2 * names_n:]], lag_ratio=0.35)]

        def judge(k, upto=6):
            res = HIST[k][3]
            anims = []
            for i in range(upto):
                ok = res[i]
                anims.append(rungs[i][0].animate.set_stroke(GREEN_M if ok else RED_M).set_fill(fillc(GREEN_M if ok else RED_M, 0.18), 1))
            return anims

        def reset():
            return [r[0].animate.set_stroke(GREY_B).set_fill("#111111", 1) for r in rungs]

        a0, h0 = show_hist(0)
        self.steps("To check a rule, we draw a history. Each program gets a line. Each request is a bar, from when it's sent "
                   "to when the answer comes back.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(you, sis, yv, sv3, *cps, *cv, a1, a2))], 0.6),
            "we draw a history",
            (lambda: a0, 0.7),
            "Each request",
            (lambda: [FadeIn(h0[5], shift=0.1 * RIGHT)], 0.5),
        ])
        self.steps("Checkout writes the balance, 70. The ledger, starting later, reads 70.", [
            (lambda: [Indicate(h0[5], color=GOLD_M, scale_factor=1.08)], 0.6),
            "The ledger",
            (lambda: [FadeIn(h0[6], shift=0.1 * RIGHT)], 0.5),
        ])
        self.steps("The house rules form a ladder. Each rung down drops one demand, so a history that passes a rung "
                   "passes every rung below it.", [
            (lambda: [Create(rails), FadeIn(top)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in rungs], lag_ratio=0.15)], 1.2),
            "Each rung down",
            (lambda: self.cap("each rung down drops one demand", WHITE), 0.5),
        ])
        self.steps("This history passes every rung. One copy could have done exactly this.", [
            (lambda: [*self.uncap(), *judge(0)], 0.8),
        ])

        # ---------------- scene 4: linearizable, and the stale read ----------------
        pts = [Line(UP * 0.36, DOWN * 0.36, stroke_width=4, color=YELLOW_M).move_to(h0[k][0].get_center()) for k in (5, 6)]
        self.steps("The top rung is linearizable. The store behaves as if there were one copy, and each operation took effect "
                   "at one instant inside its bar. So a read that starts after a write has finished must see it.", [
            (lambda: [*reset(), glow(rungs[0][0], WHITE)], 0.7),
            "one instant",
            (lambda: [Create(pts[0]), Create(pts[1])], 0.6),
            "So a read",
            (lambda: self.cap("linearizable: as if one copy, each operation at one instant inside its bar", WHITE), 0.5),
        ])
        a1h, h1 = show_hist(1)
        self.steps("Now the ledger starts after the write has finished, and still reads the old value. The dash means the value "
                   "before the write. Which rungs survive? Pause and guess.", [
            (lambda: [*self.uncap(), *[FadeOut(p) for p in pts], *reset(), *a1h], 0.6),
            (lambda: [FadeIn(h1[5]), FadeIn(h1[6])], 0.5),
            "The dash",
            (lambda: [Indicate(h1[6], color=RED_M, scale_factor=1.08), *self.cap("-  :  the value before the write")], 0.6),
            "Pause and guess",
            (lambda: self.cap("which rungs survive?   pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Only the top one breaks. Real time says the write came first. But the rung below doesn't care about real time.", [
            (lambda: [*self.uncap(), *judge(1)], 0.8),
            "the rung below",
            (lambda: [glow(rungs[1][0], GREEN_M)], 0.7),
        ])

        # ---------------- scene 5: sequential, and opposite orders ----------------
        self.steps("That's sequential consistency, which Leslie Lamport defined in 1979. It keeps one order that everybody agrees on, "
                   "with each program's own steps in the order it ran them. Put the ledger's read before the write, and nobody's order breaks.", [
            (lambda: self.cap("sequential (Lamport, 1979): one order everybody agrees on; real time dropped", WHITE), 0.6),
            "Put the ledger's",
            (lambda: [h1[6].animate.shift(0.15 * UP), ], 0.4),
            (lambda: [h1[6].animate.shift(0.15 * DOWN)], 0.4),
        ])
        a2h, h2 = show_hist(2)
        self.steps("To break it, two copies, one in Europe and one in the United States, accept two writes to a payment's status "
                   "at the same moment: 2 for captured, and 3 for refunded.", [
            (lambda: [*self.uncap(), *reset(), *a2h], 0.7),
            "accept two writes",
            (lambda: [FadeIn(h2[9]), FadeIn(h2[10])], 0.6),
            "2 for captured",
            (lambda: self.cap("status: 2 = captured,  3 = refunded"), 0.5),
        ])
        self.steps("The ledger sees 2, then 3. The fraud checker sees 3, then 2. No single order explains both.", [
            (lambda: [FadeIn(h2[11]), FadeIn(h2[12])], 0.6),
            "The fraud checker",
            (lambda: [FadeIn(h2[13]), FadeIn(h2[14])], 0.6),
            "No single order",
            (lambda: [*judge(2), *self.cap("no single order explains both", RED_M)], 0.8),
        ])

        # ---------------- scene 6: causal, and the answer before its question ----------------
        self.steps("One rung down, causal consistency drops the single order. Two writes that couldn't have known about each other "
                   "may show up in any order. What it keeps is: never an effect before its cause.", [
            (lambda: [glow(rungs[2][0], GREEN_M), *self.cap("causal: concurrent writes in any order")], 0.7),
            "What it keeps",
            (lambda: self.cap("causal keeps: never an effect before its cause", WHITE), 0.5),
        ])
        a3h, h3 = show_hist(3)
        self.steps("A support agent asks a shop a question. The shop reads it and answers. An auditor reads the answer, "
                   "then finds no question.", [
            (lambda: [*self.uncap(), *reset(), *a3h], 0.7),
            "A support agent",
            (lambda: [FadeIn(h3[7])], 0.4),
            "The shop reads",
            (lambda: [FadeIn(h3[8])], 0.4),
            (lambda: [FadeIn(h3[9])], 0.4),
            "An auditor reads",
            (lambda: [FadeIn(h3[10])], 0.4),
            "then finds",
            (lambda: [FadeIn(h3[11])], 0.35),
            (lambda: [Indicate(h3[11], color=RED_M, scale_factor=1.1)], 0.6),
        ])
        self.steps("The answer was caused by the question, so causal breaks. It's a reply that says yes, see you there, "
                   "with no invitation anywhere.", [
            (lambda: [*judge(3), *self.cap("an effect without its cause: causal breaks", RED_M)], 0.8),
        ])

        # ---------------- scene 7: the session promises ----------------
        a4h, h4 = show_hist(4)
        self.steps("Below causal sit promises to one client about its own run of requests, its session. "
                   "Read your writes: after you write, your reads see it.", [
            (lambda: [*self.uncap(), *reset(), glow(rungs[3][0], WHITE), glow(rungs[4][0], WHITE)], 0.7),
            "Read your writes",
            (lambda: self.cap("read your writes: after you write, your reads see it", WHITE), 0.5),
        ])
        self.steps("Checkout writes 70, and its very next read gets the old value. That breaks it.", [
            (lambda: a4h, 0.6),
            (lambda: [FadeIn(h4[3])], 0.4),
            "its very next read",
            (lambda: [FadeIn(h4[4])], 0.35),
            (lambda: [Indicate(h4[4], color=RED_M, scale_factor=1.1)], 0.6),
            "That breaks",
            (lambda: judge(4), 0.7),
        ])
        a5h, h5 = show_hist(5)
        self.steps("Monotonic reads: once you've seen a value, you never see an older one. The ledger reads 70, then the old value "
                   "from a copy further behind. Its balance went back in time.", [
            (lambda: [*reset(), *self.cap("monotonic reads: never an older value than one you've seen", WHITE), *a5h], 0.7),
            "The ledger reads",
            (lambda: [FadeIn(h5[5]), FadeIn(h5[6])], 0.5),
            "then the old",
            (lambda: [FadeIn(h5[7])], 0.35),
            (lambda: [Indicate(h5[7], color=RED_M, scale_factor=1.1)], 0.6),
            "went back",
            (lambda: judge(5), 0.7),
        ])

        # ---------------- scene 8: eventual ----------------
        self.steps("The bottom rung is eventual consistency. If the writes stop, all copies end up the same. "
                   "It says nothing about what a read returns before then.", [
            (lambda: [glow(rungs[5][0], GREEN_M), *self.cap("eventual: once the writes stop, the copies end up the same", WHITE)], 0.7),
            "It says nothing",
            (lambda: self.cap("before then: no promise at all"), 0.5),
        ])
        self.steps("That's why it held in every history we drew. No history that stops can break a promise with no deadline. "
                   "It's the friend who'll pay you back eventually: never technically wrong.", [
            (lambda: [Indicate(rungs[5], color=GREEN_M, scale_factor=1.05)], 0.8),
            "It's the friend",
            (lambda: self.cap("a promise with no deadline: never technically wrong", GREY_B), 0.5),
        ])

        # ---------------- scene 9: name, cost, moral ----------------
        self.steps("Each rung has a name: a consistency model, a rule for which histories are right.", [
            (lambda: [*reset(), FadeOut(h[0]), *self.cap("consistency model: a rule for which histories are right", WHITE, 26)], 0.7),
            (lambda: [LaggedStart(*[glow(r[0], WHITE, 1.03) for r in rungs], lag_ratio=0.15)], 1.2),
        ])
        h[0] = None
        cut = VGroup(*[box("copy", GREY_B, w=1.5, h=0.8, size=22).move_to([x, 0.6, 0]) for x in (0.6, 2.4, 4.6)])
        wall = DashedLine([3.5, 1.8, 0], [3.5, -0.6, 0], dash_length=0.15, stroke_width=4, color=RED_M)
        self.steps("So why not always take the top? Because each rung up costs availability: the ability to keep answering "
                   "while part of the network is cut off.", [
            (lambda: [FadeIn(cut, shift=0.1 * UP), *self.cap("each rung up costs availability", GOLD_M)], 0.7),
            "is cut off",
            (lambda: [Create(wall)], 0.6),
        ])
        refuse = T("must refuse", 20, RED_M).move_to([4.6, -0.2, 0])
        self.steps("When the network splits the copies, no model at sequential or above lets every copy keep answering. "
                   "Some must refuse. Causal and the session promises can keep working, if a client keeps talking to the same copy.", [
            (lambda: [*[r[0].animate.set_stroke(RED_M) for r in rungs[:2]]], 0.6),
            "Some must refuse",
            (lambda: [FadeIn(refuse), cut[2][0].animate.set_stroke(RED_M)], 0.5),
            "Causal and",
            (lambda: [*[r[0].animate.set_stroke(GREEN_M) for r in rungs[2:5]],
                      *self.cap("causal and session: keep working, if a client sticks to one copy")], 0.7),
        ])
        self.steps("A stronger model is a promise someone pays for. Pick the loosest rung your data can live with.", [
            (lambda: [FadeOut(VGroup(cut, wall, refuse)), *reset(), *self.cap("a stronger model is a promise someone pays for", WHITE)], 0.7),
            "Pick the loosest",
            (lambda: self.cap("pick the loosest rung your data can live with", YELLOW_M, 30), 0.6),
        ], after=0.5)

        # ---------------- scene 10: the check ----------------
        sh = history("your sister's 100.00", ["you", "sister"],
                     [(0, 0, 30, "w b=70", W_C), (1, 40, 70, "r b:100", R_C), (1, 76, 106, "r b:70", R_C)])
        self.steps("One quick check. Your sister read 100.00 after you had already paid, then 70.00. Which rungs did that break? "
                   "Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(sh, shift=0.1 * UP)], 0.8),
            "Pause and think",
            (lambda: self.cap("which rungs broke?   pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Only the top one. She didn't write anything, her balance never went back, and one order explains it all. "
                   "Nothing was broken: the store just promised less than one copy.", [
            (lambda: [*self.uncap(), rungs[0][0].animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.18), 1),
                      *[r[0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M, 0.18), 1) for r in rungs[1:]]], 0.8),
            "Nothing was broken",
            (lambda: self.cap("only linearizable broke: the store promised less than one copy", WHITE), 0.5),
        ], after=0.3)
        self.wait(2.0)
