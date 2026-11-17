from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\brow_number\b", "row number"),
    (r"\bGROUP BY\b", "group by"),
    (r"\b(\d\d):(\d\d)\b", r"\1 \2"),
]

# ---- the data (seed: customers 5 and 10; the lesson's figure and Try it output) ----
ELENA = [True, True, False, False, False, False, False, False, True]
JONAS = [False, False, True, False, False, True]


def counters(seq):
    """Every login numbered, numbered again within its outcome, and the difference (the island id)."""
    a, b, d, seen = [], [], [], {True: 0, False: 0}
    for i, ok in enumerate(seq):
        seen[ok] += 1
        a.append(i + 1)
        b.append(seen[ok])
        d.append(i + 1 - seen[ok])
    return a, b, d


EA, EB, ED = counters(ELENA)      # 1..9 / 1 2 1..6 3 / 0 0 2 2 2 2 2 2 6
JA, JB, JD = counters(JONAS)      # 1..6 / 1 2 1 3 4 2 / 0 0 2 1 1 4

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
X0, PITCH = -3.6, 1.2
SW, SH = 0.8, 0.55
LBL_R = -4.2                          # right edge of the row labels
E = dict(A=2.9, S=2.35, B=1.8, D=1.3, BR=0.64)
J = dict(A=-0.05, S=-0.6, B=-1.15, D=-1.65, BR=-2.33)
CAP_Y, BAR_Y = -3.3, -2.85
CODE_Y = [-2.8, -3.25]


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def xs(i):
    return X0 + PITCH * i


def slip(ok, i, y):
    c = GREEN_M if ok else RED_M
    r = RoundedRectangle(corner_radius=0.08, width=SW, height=SH, stroke_color=c, stroke_width=3).set_fill(fillc(c, 0.22), 1)
    r.move_to([xs(i), y, 0])
    return VGroup(r, tick(ok, 0.14).move_to(r))


def num(v, i, y, color, size=24):
    return M(str(v), size, color).move_to([xs(i), y, 0])


def under(nums, text, y, color=WHITE, size=20):
    br = Brace(VGroup(*nums), DOWN, buff=0.08, color=color).stretch_to_fit_height(0.16)
    lab = T(text, size, color).move_to([br.get_center()[0], y, 0])
    return br, lab


class GapsIslands(Base):
    """sql-07, section 3. Lock an account after three failed logins in a row. Elena's nine logins and Jonas's six;
    GROUP BY counts Jonas's four failures and locks him out. Two clickers walk down the pile of receipts: one counts
    every receipt, one counts its own colour; the difference is the same along a run (the island id). Fold the
    islands, break the filter-first idea on Jonas, name the limits, and check Jonas's last island id."""

    def construct(self):
        self.capm = None
        self.title_card("Three failures in a row?", "gaps and islands: number twice, subtract")

        # ---------------- scene 1: in a row ----------------
        es = [slip(ok, i, E["S"]) for i, ok in enumerate(ELENA)]
        js = [slip(ok, i, J["S"]) for i, ok in enumerate(JONAS)]
        en = right_at(T("Elena", 26), LBL_R, E["S"])
        jn = right_at(T("Jonas", 26), LBL_R, J["S"])
        self.steps("A payments app records every attempt to log in: who tried, when, and whether the password was right.", [
            "every attempt",
            (lambda: [FadeIn(es[0], shift=0.15 * DOWN)], 0.5),
            "whether the password",
            (lambda: [*self.cap("one row per attempt: who, when, and right or wrong")], 0.5),
        ])
        self.steps("The security team wants a rule: three failed logins in a row, and the account gets locked. "
                   "First, they want to see every run of failures, with its length.", [
            "three failed",
            (lambda: self.cap("three failures in a row: lock the account", WHITE), 0.5),
            "First, they want",
            (lambda: self.cap("first: every run of failures, and its length"), 0.5),
        ])
        self.steps("Here's Elena's history, oldest first. Two successes. Then six failures in two minutes, from an address she had never used. "
                   "Then her own success. It looks like someone guessing her password.", [
            (lambda: [FadeIn(en), *self.cap("oldest first, left to right")], 0.5),
            "Two successes",
            (lambda: [FadeIn(es[1], shift=0.15 * DOWN)], 0.4),
            "Then six",
            (lambda: [LaggedStart(*[FadeIn(es[i], shift=0.15 * DOWN) for i in range(2, 8)], lag_ratio=0.2)], 1.2),
            (lambda: self.cap("6 failures in 2 minutes, from an address she had never used", RED_M), 0.5),
            "Then her own",
            (lambda: [FadeIn(es[8], shift=0.15 * DOWN)], 0.4),
            "It looks like",
            (lambda: [LaggedStart(*[Indicate(es[i], color=RED_M, scale_factor=1.12) for i in range(2, 8)], lag_ratio=0.1)], 1.0),
        ])
        inrow = T("in a row?", 34, YELLOW_M).move_to([4.6, J["S"], 0])
        self.steps("A database compares values. So how does it see in a row?", [
            (lambda: self.cap("a database compares values", WHITE), 0.5),
            "So how",
            (lambda: [FadeIn(inrow, scale=0.7)], 0.6),
        ], after=0.4)

        # ---------------- scene 2: GROUP BY counts, but can't see neighbours ----------------
        g_ok = chip("successes: 3", GREEN_M, 22).move_to([-1.0, E["BR"] + 0.35, 0])
        g_no = chip("failures: 6", RED_M, 22).move_to([2.2, E["BR"] + 0.35, 0])

        def pile(idx, target):
            cps = [es[i].copy() for i in idx]
            return [AnimationGroup(*[c.animate.move_to(target.get_center()).scale(0.4).set_opacity(0) for c in cps],
                                   FadeIn(target, scale=0.8), lag_ratio=0.4)], cps

        p_ok, c_ok = pile([0, 1, 8], g_ok)
        p_no, c_no = pile(list(range(2, 8)), g_no)
        self.steps("The first thing to try is GROUP BY: one pile per customer and outcome, then count each pile. "
                   "For Elena, that's three successes and six failures.", [
            (lambda: [FadeOut(inrow), *self.cap("GROUP BY customer, outcome: one pile each, then count", WHITE)], 0.6),
            "For Elena",
            (lambda: p_ok[0:1], 0.9),
            (lambda: p_no[0:1], 0.9),
        ])
        self.remove(*c_ok, *c_no)
        self.steps("But her three successes came from two separate runs, and the count can't tell.", [
            "two separate runs",
            (lambda: [Indicate(VGroup(es[0], es[1]), color=GREEN_M, scale_factor=1.08)], 0.7),
            (lambda: [Indicate(es[8], color=GREEN_M, scale_factor=1.15)], 0.7),
            "the count can't",
            (lambda: [Indicate(g_ok, color=GREEN_M)], 0.7),
        ])
        j4 = chip("failures: 4", RED_M, 22).move_to([4.6, J["S"], 0])
        lock = T("locked out?", 24, RED_M).move_to([4.6, J["B"], 0])
        self.steps("Jonas is worse off. He failed twice in April and twice in June, with a success after each pair.", [
            (lambda: [FadeIn(jn)], 0.4),
            "failed twice in April",
            (lambda: [FadeIn(js[0], shift=0.15 * DOWN), FadeIn(js[1], shift=0.15 * DOWN)], 0.6),
            "twice in June",
            (lambda: [FadeIn(js[3], shift=0.15 * DOWN), FadeIn(js[4], shift=0.15 * DOWN)], 0.6),
            "with a success",
            (lambda: [FadeIn(js[2], shift=0.15 * DOWN), FadeIn(js[5], shift=0.15 * DOWN)], 0.6),
        ])
        self.steps("GROUP BY counts four failures, and locks him out. He never failed three times in a row. "
                   "He forgets his password now and then, like the rest of us.", [
            (lambda: [FadeIn(j4, shift=0.1 * LEFT)], 0.6),
            "and locks him",
            (lambda: [FadeIn(lock, shift=0.1 * UP)], 0.5),
            "He never failed",
            (lambda: [Indicate(VGroup(js[0], js[1]), color=RED_M, scale_factor=1.08)], 0.7),
            (lambda: [Indicate(VGroup(js[3], js[4]), color=RED_M, scale_factor=1.08)], 0.7),
        ])
        self.steps("GROUP BY sees which rows share a value. It can't see whether they sit next to each other. "
                   "We need a label that stays the same along a run, and changes when a new run starts.", [
            (lambda: self.cap("GROUP BY sees equal values, not neighbours"), 0.5),
            "We need a label",
            (lambda: [FadeOut(VGroup(g_ok, g_no, j4, lock)),
                      *self.cap("wanted: a label that stays the same along a run, and changes at the next run", WHITE)], 0.8),
        ], after=0.4)

        # ---------------- scene 3: two clickers ----------------
        la = right_at(T("clicker 1: every one", 18, BLUE_M), LBL_R, E["A"])
        lb = right_at(T("clicker 2: same colour", 18, GOLD_M), LBL_R, E["B"])
        ld = right_at(T("the gap", 18), LBL_R, E["D"])
        run_red = SurroundingRectangle(VGroup(*es[2:8]), color=RED_M, buff=0.1, corner_radius=0.1, stroke_width=2.5)
        self.steps("Picture each login as a paper receipt, in a pile sorted by time: green for a success, red for a failure. "
                   "A run is a stretch of receipts of one colour.", [
            (lambda: self.cap("each login: a receipt, in a pile sorted by time"), 0.5),
            "green for",
            (lambda: [LaggedStart(*[Indicate(es[i], color=GREEN_M, scale_factor=1.12) for i in (0, 1, 8)], lag_ratio=0.2)], 0.8),
            "red for",
            (lambda: [LaggedStart(*[Indicate(es[i], color=RED_M, scale_factor=1.12) for i in range(2, 8)], lag_ratio=0.1)], 0.8),
            "A run is",
            (lambda: [Create(run_red)], 0.7),
        ])
        self.steps("Now walk down the pile with two hand clickers, the kind people use to count visitors at a door. "
                   "The first clicks on every receipt. The second clicks only for the receipt's own colour: "
                   "it keeps one count for reds, and one for greens.", [
            (lambda: [FadeOut(run_red), *self.uncap()], 0.4),
            "The first clicks",
            (lambda: [FadeIn(la, shift=0.1 * RIGHT)], 0.5),
            "The second clicks",
            (lambda: [FadeIn(lb, shift=0.1 * RIGHT)], 0.5),
            "one count for reds",
            (lambda: self.cap("clicker 2: one count for reds, one for greens", GOLD_M), 0.5),
        ])
        self.steps("Along a red run, both clickers move together, so the gap between them stays the same. "
                   "Pass a green receipt, and only the first one moves. So the next red run gets a bigger gap.", [
            (lambda: [FadeIn(ld, shift=0.1 * RIGHT), *self.cap("along a run: both move, the gap stays", WHITE)], 0.6),
            "Pass a green",
            (lambda: self.cap("across another colour: only clicker 1 moves, the gap grows", WHITE), 0.6),
        ])
        self.steps("Let's map it. A receipt is a row. The pile's order is the time order. The first clicker numbers every row. "
                   "The second numbers rows with the same outcome. And the gap is the label we wanted.", [
            (lambda: self.cap("a receipt = a row", WHITE), 0.4),
            "The pile's order",
            (lambda: self.cap("the pile's order = time order", WHITE), 0.4),
            "The first clicker",
            (lambda: [*self.cap("clicker 1 = a number for every row", BLUE_M), Indicate(la, color=BLUE_M)], 0.6),
            "The second numbers",
            (lambda: [*self.cap("clicker 2 = a number within the same outcome", GOLD_M), Indicate(lb, color=GOLD_M)], 0.6),
            "And the gap",
            (lambda: [*self.cap("the gap = the label for the run", WHITE), Indicate(ld, color=WHITE)], 0.6),
        ], after=0.4)

        # ---------------- scene 4: try it on Elena ----------------
        ea = [num(v, i, E["A"], BLUE_M) for i, v in enumerate(EA)]
        eb = [num(v, i, E["B"], GOLD_M) for i, v in enumerate(EB)]
        ed = [num(v, i, E["D"], WHITE, 26) for i, v in enumerate(ED)]
        self.steps("Let's try it on Elena. The first clicker numbers her logins 1 to 9.", [
            (lambda: self.uncap(), 0.3),
            "The first clicker",
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.15 * DOWN) for n in ea], lag_ratio=0.25)], 1.8),
        ])
        self.steps("The colour clicker gives her successes 1 and 2, her failures 1 to 6, and her last success 3.", [
            "her successes",
            (lambda: [LaggedStart(*[FadeIn(eb[i], shift=0.15 * UP) for i in (0, 1)], lag_ratio=0.4)], 0.6),
            "her failures",
            (lambda: [LaggedStart(*[FadeIn(eb[i], shift=0.15 * UP) for i in range(2, 8)], lag_ratio=0.3)], 1.3),
            "her last success",
            (lambda: [FadeIn(eb[8], shift=0.15 * UP)], 0.4),
        ])
        qs = [num("?", i, E["D"], YELLOW_M, 26) for i in range(2, 8)]
        self.steps("Now subtract. On her six failures, what's the first number minus the second? Pause and guess.", [
            "On her six",
            (lambda: [LaggedStart(*[FadeIn(q, scale=0.6) for q in qs], lag_ratio=0.15)], 0.9),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("2, on all six. 3 minus 1, 4 minus 2, all the way to 8 minus 6.", [
            (lambda: [*self.uncap(), *[swap(qs[k], ed[k + 2]) for k in range(6)]], 0.7),
            "3 minus 1",
            (lambda: [*self.cap("3 - 1 = 2,   4 - 2 = 2,   ...   8 - 6 = 2", WHITE), Indicate(ea[2], color=BLUE_M), Indicate(eb[2], color=GOLD_M)], 0.6),
            "4 minus 2",
            (lambda: [Indicate(ea[3], color=BLUE_M), Indicate(eb[3], color=GOLD_M)], 0.5),
            "8 minus 6",
            (lambda: [Indicate(ea[7], color=BLUE_M), Indicate(eb[7], color=GOLD_M)], 0.5),
        ])
        br_e, lab_e = under(ed[2:8], "one run, one number: 2", E["BR"], YELLOW_M)
        self.steps("Her first two successes get 0, and her last success, 9 minus 3, gets 6. Same difference, same run.", [
            (lambda: [FadeIn(ed[0], shift=0.1 * UP), FadeIn(ed[1], shift=0.1 * UP)], 0.5),
            "9 minus 3",
            (lambda: [FadeIn(ed[8], shift=0.1 * UP), *self.cap("9 - 3 = 6", WHITE)], 0.5),
            "Same difference",
            (lambda: [GrowFromCenter(br_e), FadeIn(lab_e), *self.uncap()], 0.7),
        ])
        self.steps("Subtraction: the hardest maths you'll do today. And it's enough.", [
            1.0,
            (lambda: [LaggedStart(*[Indicate(n, color=YELLOW_M, scale_factor=1.25) for n in ed], lag_ratio=0.08)], 1.2),
        ], after=0.4)

        # ---------------- scene 5: now the names ----------------
        isl = [SurroundingRectangle(VGroup(*es[a:b]), color=c, buff=0.08, corner_radius=0.1, stroke_width=2.5)
               for a, b, c in ((0, 2, GREEN_M), (2, 8, RED_M), (8, 9, GREEN_M))]
        gaps = [DashedLine([(xs(i) + xs(i + 1)) / 2, E["S"] + 0.4, 0], [(xs(i) + xs(i + 1)) / 2, E["S"] - 0.4, 0],
                           dash_length=0.07, stroke_width=3, color=YELLOW_M) for i in (1, 7)]
        la2 = right_at(T("all logins", 18, BLUE_M), LBL_R, E["A"])
        lb2 = right_at(T("same outcome", 18, GOLD_M), LBL_R, E["B"])
        ld2 = right_at(T("island id", 18, YELLOW_M), LBL_R, E["D"])
        lab_e2 = T("island 2", 20, YELLOW_M).move_to(lab_e)
        self.steps("Now the names. A run of equal values with nothing else between them is called an island. "
                   "The places where the value changes are the gaps. The difference is the island id.", [
            "is called an island",
            (lambda: [*[Create(r) for r in isl], *self.cap("island: a run of equal values, nothing else between", WHITE)], 0.8),
            "are the gaps",
            (lambda: [*[Create(g) for g in gaps], *self.cap("gap: where the value changes", YELLOW_M)], 0.7),
            "The difference",
            (lambda: [swap(ld, ld2), swap(lab_e, lab_e2)], 0.6),
        ])
        code = VGroup(M("  row_number() OVER (PARTITION BY customer_id ORDER BY occurred_at)", 18, BLUE_M),
                      M("- row_number() OVER (PARTITION BY customer_id, success ORDER BY occurred_at)", 18, GOLD_M))
        code.arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to([0, (CODE_Y[0] + CODE_Y[1]) / 2, 0])
        self.steps("In SQL, each clicker is row_number, a window function that numbers rows 1, 2, 3 in order. "
                   "Number every login by time, number them again within the same outcome, and subtract.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*isl, *gaps))], 0.5),
            "each clicker is",
            (lambda: [swap(la, la2), swap(lb, lb2)], 0.6),
            "Number every login",
            (lambda: [FadeIn(code[0], shift=0.1 * UP), Indicate(la2, color=BLUE_M)], 0.6),
            "number them again",
            (lambda: [FadeIn(code[1], shift=0.1 * UP), Indicate(lb2, color=GOLD_M)], 0.6),
        ], after=0.4)

        # ---------------- scene 6: fold the islands ----------------
        ja = [num(v, i, J["A"], BLUE_M) for i, v in enumerate(JA)]
        jb = [num(v, i, J["B"], GOLD_M) for i, v in enumerate(JB)]
        jd = [num(v, i, J["D"], WHITE, 26) for i, v in enumerate(JD)]
        jq = num("?", 5, J["D"], YELLOW_M, 26)
        self.steps("Jonas, the same way. Every login: 1 to 6. Failures: 1 and 2, then 3 and 4. "
                   "His April pair gets 0, and his June pair gets 1.", [
            (lambda: [FadeOut(code)], 0.4),
            "Every login",
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.15 * DOWN) for n in ja], lag_ratio=0.2)], 1.0),
            "Failures",
            (lambda: [LaggedStart(*[FadeIn(jb[i], shift=0.15 * UP) for i in (0, 1, 3, 4)], lag_ratio=0.3),
                      FadeIn(jb[2]), FadeIn(jb[5])], 1.0),
            "His April",
            (lambda: [FadeIn(jd[0], shift=0.1 * UP), FadeIn(jd[1], shift=0.1 * UP), FadeIn(jd[2], shift=0.1 * UP)], 0.5),
            "his June",
            (lambda: [FadeIn(jd[3], shift=0.1 * UP), FadeIn(jd[4], shift=0.1 * UP), FadeIn(jq)], 0.5),
        ])
        lab_e3 = T("island 2: 6 failures, 19:52:00 to 19:53:40", 20, WHITE).move_to(lab_e)
        br_j0, lab_j0 = under(jd[0:2], "island 0: 2 failures", J["BR"])
        br_j1, lab_j1 = under(jd[3:5], "island 1: 2 failures", J["BR"])
        self.steps("Now group by customer, outcome and island id, and each island folds into one row with a count. "
                   "Elena: one island of six failures, all inside two minutes. Jonas: two islands of two.", [
            (lambda: self.cap("group by customer, outcome and island id", WHITE), 0.5),
            "Elena: one",
            (lambda: [swap(lab_e2, lab_e3), br_e.animate.set_color(WHITE)], 0.7),
            "Jonas: two",
            (lambda: [GrowFromCenter(br_j0), FadeIn(lab_j0), GrowFromCenter(br_j1), FadeIn(lab_j1)], 0.8),
        ])
        self.steps("A rule of three in a row locks Elena's account, and leaves Jonas alone.", [
            (lambda: [*self.cap("3 or more in a row: lock"), lab_e3.animate.set_color(RED_M), br_e.animate.set_color(RED_M)], 0.6),
            "leaves Jonas",
            (lambda: [*[m.animate.set_color(GREEN_M) for m in (br_j0, lab_j0, br_j1, lab_j1)]], 0.6),
        ], after=0.4)

        # ---------------- scene 7: filter first? ----------------
        jold = VGroup(*ja, *jb, *jd[:5], jq, br_j0, lab_j0, br_j1, lab_j1)
        fa = [num(v, i, J["A"], BLUE_M) for i, v in enumerate([1, 2, 3, 4])]
        fb = [num(v, i, J["B"], GOLD_M) for i, v in enumerate([1, 2, 3, 4])]
        fd = [num(0, i, J["D"], RED_M, 26) for i in range(4)]
        br_f, lab_f = under(fd, "one island of four: locked out", J["BR"], RED_M)
        self.steps("You might think: why number the successes at all? Keep only the failures, then number those. "
                   "To be fair, it's less work.", [
            (lambda: [*self.cap("filter first: keep only the failures, then number them?", PURPLE_M)], 0.6),
            "Keep only",
            (lambda: [FadeOut(jold), js[2].animate.set_opacity(0.12), js[5].animate.set_opacity(0.12)], 0.8),
        ])
        self.steps("But look at Jonas. With the successes gone, his four failures sit next to each other. "
                   "Both clickers count 1 to 4, every difference is 0, and he's one island of four again. Locked out.", [
            "With the successes",
            (lambda: [FadeOut(js[2]), FadeOut(js[5]), js[3].animate.move_to([xs(2), J["S"], 0]), js[4].animate.move_to([xs(3), J["S"], 0])], 0.9),
            "Both clickers",
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.1 * DOWN) for n in fa], lag_ratio=0.2),
                      LaggedStart(*[FadeIn(n, shift=0.1 * UP) for n in fb], lag_ratio=0.2)], 0.9),
            "every difference",
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.1 * UP) for n in fd], lag_ratio=0.2)], 0.7),
            "one island of four",
            (lambda: [GrowFromCenter(br_f), FadeIn(lab_f)], 0.6),
        ])
        js[2], js[5] = slip(True, 2, J["S"]), slip(True, 5, J["S"])     # fresh slips: the faded ones lost their look
        self.steps("So number every login first. Only then keep the failures.", [
            (lambda: self.cap("number every login first; keep the failures after", WHITE), 0.5),
            (lambda: [FadeOut(VGroup(*fa, *fb, *fd, br_f, lab_f)),
                      js[3].animate.move_to([xs(3), J["S"], 0]), js[4].animate.move_to([xs(4), J["S"], 0])], 0.8),
            (lambda: [FadeIn(js[2]), FadeIn(js[5]), FadeIn(jold)], 0.7),
        ], after=0.4)

        # ---------------- scene 8: two limits ----------------
        self.steps("One more trap. An island id only means something inside one customer and one outcome. "
                   "Elena's first success run is island 0, and so is Jonas's April failure run. So group by customer and outcome too.", [
            (lambda: self.uncap(), 0.3),
            "Elena's first",
            (lambda: [Indicate(VGroup(ed[0], ed[1]), color=YELLOW_M, scale_factor=1.3)], 0.8),
            "and so is Jonas",
            (lambda: [Indicate(VGroup(jd[0], jd[1]), color=YELLOW_M, scale_factor=1.3)], 0.8),
            "So group by",
            (lambda: self.cap("island 0 and island 0: group by customer and outcome too", WHITE), 0.5),
        ])
        self.steps("And in a row here means the next row. Sometimes it means soon after, like failures a minute apart. "
                   "That needs gaps measured in time, which the next section draws.", [
            (lambda: self.cap("in a row here: the next row", WHITE), 0.5),
            "Sometimes it means",
            (lambda: self.cap("soon after: gaps measured in time (the next section)"), 0.5),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So how does a database see in a row? Count every row, count again within the colour, and subtract. "
                   "Same difference, same island.", [
            (lambda: self.cap("so how does it see in a row?", WHITE), 0.5),
            "Count every row",
            (lambda: [*self.cap("count all, count within the colour, subtract", WHITE),
                      LaggedStart(*[Indicate(n, color=BLUE_M) for n in ea], lag_ratio=0.05)], 0.9),
            "count again",
            (lambda: [LaggedStart(*[Indicate(n, color=GOLD_M) for n in eb], lag_ratio=0.05)], 0.9),
            "and subtract",
            (lambda: [LaggedStart(*[Indicate(n, color=YELLOW_M) for n in ed], lag_ratio=0.05)], 0.9),
        ])
        ring = SurroundingRectangle(VGroup(ja[5], js[5], jb[5], jq), color=YELLOW_M, buff=0.1, corner_radius=0.1)
        self.steps("One quick check. Jonas's last login is number 6 overall, and his second success. What's its island id? "
                   "Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "Jonas's last",
            (lambda: [Create(ring)], 0.6),
            "number 6",
            (lambda: [Indicate(ja[5], color=BLUE_M, scale_factor=1.3)], 0.6),
            "his second success",
            (lambda: [Indicate(jb[5], color=GOLD_M, scale_factor=1.3)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        four = num(4, 5, J["D"], YELLOW_M, 26)
        self.steps("4. 6 minus 2. A new success island, not his first one, island 2.", [
            (lambda: [swap(jq, four), *self.cap("6 - 2 = 4: a new success island", YELLOW_M)], 0.6),
            "not his first",
            (lambda: [Indicate(jd[2], color=GREEN_M, scale_factor=1.4)], 0.8),
        ], after=0.3)
        self.play(FadeOut(ring), *self.cap("same difference, same island", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
