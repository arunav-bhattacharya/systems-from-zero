from sfz import *

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CON, CON_W, CON_H = np.array([-4.5, 1.95, 0]), 3.2, 1.9          # the console: CPU 0
SLOT = CON + [0, -0.2, 0]
CHIP_W, CHIP_H = 1.95, 1.05
HOME = {"Taps": np.array([-5.55, -0.05, 0]), "Totals": np.array([-3.45, -0.05, 0])}
COL = {"Taps": BLUE_M, "Totals": GOLD_M}
SS_X, SS_TOP = -1.9, 3.05                                         # the score sheet
ROW_Y = {"Taps": 2.42, "Totals": 1.78, "late": 1.14}
BAR_X0, SC, BAR_H = -0.4, 0.1, 0.32
TB_Y, TB_X0, TB_DX = [0.3, -0.18], -0.25, 1.1                     # the weight table
NICE = [("-5", "3121"), ("0", "1024"), ("1", "820"), ("5", "335"), ("10", "110"), ("19", "15")]
STRIP_Y, STRIP_X0, BLK, BPITCH = -1.25, -5.3, 0.24, 0.27          # the strip of turns
SHARE_W = 10.0
SUB_Y, LAB_Y = -1.72, -2.2
CAP_Y, BAR_Y = -2.85, -3.3


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


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def chip_box(name, at):
    r = RoundedRectangle(corner_radius=0.12, width=CHIP_W, height=CHIP_H, stroke_color=COL[name], stroke_width=3)
    r.set_fill(fillc(COL[name], 0.22), 1).move_to(at)
    return VGroup(r, T(name, 22).move_to(at + [0, 0.27, 0]))


def chip_sub(at, s, k):
    return M(s, 15, GREY_B).move_to(at + [0, -0.05 - 0.25 * k, 0])


def bar(name, val, color=None):
    w = max(0.02, val * SC)
    return Rectangle(width=w, height=BAR_H, stroke_width=0).set_fill(color or COL.get(name, GREY_B), 0.85).move_to(
        [BAR_X0 + w / 2, ROW_Y[name], 0])


def bar_val(name, val):
    s = f"{val:.1f}" if abs(val - round(val)) > 1e-6 else f"{int(round(val))}"
    return M(s, 18).move_to([BAR_X0 + max(0.02, val * SC) + 0.15, ROW_Y[name], 0], aligned_edge=LEFT)


def block(k, name):
    return Rectangle(width=BLK, height=0.42, stroke_width=0).set_fill(COL[name], 0.9).move_to([STRIP_X0 + BLK / 2 + k * BPITCH, STRIP_Y, 0])


def share_bar(p, a="Taps", b="Totals"):
    wa = SHARE_W * p
    ra = Rectangle(width=wa, height=0.42, stroke_width=0).set_fill(COL[a], 0.9).move_to([STRIP_X0 + wa / 2, STRIP_Y, 0])
    rb = Rectangle(width=SHARE_W - wa, height=0.42, stroke_width=0).set_fill(COL[b], 0.9).move_to([STRIP_X0 + wa + (SHARE_W - wa) / 2, STRIP_Y, 0])
    la = left_at(T(f"{a} {p * 100:.1f}%", 20, COL[a]), STRIP_X0, SUB_Y)
    lb = right_at(T(f"{b} {(1 - p) * 100:.1f}%", 20, COL[b]), STRIP_X0 + SHARE_W, SUB_Y)
    return VGroup(ra, rb, la, lb)


class CpuScheduling(Base):
    """os-04, section 1. One console, two children: Taps (answers card taps) and Totals (the nightly totals job), two
    loops on one CPU. Round robin splits evenly; strict priority starves. nice values become weights (1024 and 110:
    90.3% and 9.7%). How: a score sheet, virtual runtime = CPU time x 1024 / weight, smallest runs next (Totals'
    3 ms adds 27.9). The lab: 9.01 s against 0.98 s. Limits: late arrivals, only the ratio, contested time only."""

    def chip_to(self, name, where):
        return self.chips[name].animate.move_to(where)

    def set_score(self, name, val):
        self.vals[name] = val
        new_l = bar_val(name, val)
        old_l, self.vlabs[name] = self.vlabs[name], new_l
        return [Transform(self.bars[name], bar(name, val)), swap(old_l, new_l)]

    def add_block(self, name):
        b = block(len(self.blocks), name)
        self.blocks.append(b)
        return FadeIn(b, shift=0.1 * DOWN)

    def clear_blocks(self):
        olds, self.blocks = self.blocks, []
        return [FadeOut(VGroup(*olds))] if olds else []

    def construct(self):
        self.capm = None
        self.blocks = []
        self.vals, self.vlabs = {}, {}
        self.title_card("Less, never none", "how a nice value shares a CPU")

        # ---------------- scene 1: one console, two children ----------------
        con = VGroup(RoundedRectangle(corner_radius=0.14, width=CON_W, height=CON_H, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(CON),
                     T("CPU 0", 22).move_to(CON + [0, CON_H / 2 - 0.27, 0]),
                     DashedVMobject(RoundedRectangle(corner_radius=0.1, width=CHIP_W + 0.2, height=CHIP_H + 0.15, stroke_color=GREY_D, stroke_width=2).move_to(SLOT), num_dashes=40))
        con_tag = left_at(T("the console", 18, GREY_B), CON[0] + CON_W / 2 + 0.25, CON[1] + 0.55)
        self.con_tag = left_at(T("the console: a CPU", 18, GREY_B), CON[0] + CON_W / 2 + 0.25, CON[1] + 0.55)
        self.chips = {n: chip_box(n, HOME[n]) for n in ("Taps", "Totals")}
        kids = T("two children: two tasks", 18, GREY_B).move_to([(HOME["Taps"][0] + HOME["Totals"][0]) / 2, -0.85, 0])
        strip_t = right_at(T("turns", 18, GREY_B), STRIP_X0 - 0.25, STRIP_Y)
        self.steps("Picture one game console at home, and two children who both want to play. Somebody has to decide whose turn it is.", [
            (lambda: [FadeIn(con), FadeIn(con_tag)], 0.8),
            "two children",
            (lambda: [FadeIn(self.chips["Taps"], shift=0.1 * UP), FadeIn(self.chips["Totals"], shift=0.1 * UP)], 0.7),
            "Somebody has to",
            (lambda: [glow(con[0], YELLOW_M, 1.03)], 0.7),
        ])
        self.steps("In a computer, the children are tasks, the console is a CPU, and the one deciding is the kernel's scheduler.", [
            "the children are",
            (lambda: [FadeIn(kids)], 0.5),
            "the console is",
            (lambda: [swap(con_tag, self.con_tag)], 0.6),
            "the one deciding",
            (lambda: self.cap("who plays next: the kernel's scheduler"), 0.5),
        ])
        self.steps("Our two tasks are loops that never stop to wait. One answers taps at the café's card readers. The other adds up the night's payments.", [
            (lambda: [*self.uncap(), FadeOut(kids)], 0.4),
            "One answers taps",
            (lambda: [glow(self.chips["Taps"][0], BLUE_M, 1.06), *self.cap("Taps: answers taps at the card readers", BLUE_M)], 0.7),
            "The other adds",
            (lambda: [glow(self.chips["Totals"][0], GOLD_M, 1.06), *self.cap("Totals: adds up the night's payments", GOLD_M)], 0.7),
        ])

        def rr(name, other):
            return [(lambda: [self.chip_to(name, SLOT), self.chip_to(other, HOME[other])], 0.4), (lambda: [self.add_block(name)], 0.25)]

        self.steps("With a kitchen timer, each plays 3 milliseconds, then passes the controller. "
                   "In the lab box, that split one CPU evenly: about 5 seconds each, out of 10.", [
            (lambda: [*self.cap("a kitchen timer: 3 ms each, then pass the controller"), FadeIn(strip_t)], 0.5),
            *rr("Taps", "Totals"), *rr("Totals", "Taps"), *rr("Taps", "Totals"), *rr("Totals", "Taps"),
            "In the lab box",
            (lambda: [Succession(*[self.add_block(n) for n in ["Taps", "Totals"] * 6], run_time=1.4),
                      *self.cap("round robin, in the lab box: 4.99 s each, out of 10")], 1.4),
        ])

        # ---------------- scene 2: strict priority, followed to its end ----------------
        zero = T("0%", 22, RED_M)
        zero.move_to(HOME["Totals"] + [CHIP_W / 2 + 0.2 + zero.width / 2, 0, 0])
        self.steps("But the totals job can wait till morning, and the card readers can't. We'd like it to step aside.", [
            (lambda: [*self.uncap(), *self.clear_blocks(), self.chip_to("Totals", HOME["Totals"]), self.chip_to("Taps", HOME["Taps"])], 0.6),
            "We'd like",
            (lambda: [self.chips["Totals"].animate.set_opacity(0.6)], 0.5),
        ])
        self.steps("The obvious rule is strict priority: always run the important one first. Let's follow it. "
                   "The tap loop never stops, so the totals job never gets a turn.", [
            (lambda: [self.chips["Totals"].animate.set_opacity(1), *self.cap("strict priority: always run the important one first", WHITE)], 0.6),
            "Let's follow it",
            (lambda: [self.chip_to("Taps", SLOT)], 0.5),
            (lambda: [Succession(*[self.add_block("Taps") for _ in range(20)], run_time=2.4)], 2.4),
            "never gets a turn",
            (lambda: [FadeIn(zero), glow(self.chips["Totals"][0], RED_M, 1.06)], 0.6),
        ])
        self.steps("Ask any younger sibling how that feels. Linux wants a less important task to get less CPU, never none.", [
            "Linux wants",
            (lambda: self.cap("less CPU, never none", YELLOW_M, 30), 0.6),
        ], after=0.4)

        # ---------------- scene 3: nice ----------------
        subs = {"Taps": [chip_sub(HOME["Taps"], "nice 0", 0)], "Totals": [chip_sub(HOME["Totals"], "nice 10", 0)]}
        self.steps("To say that a task matters less, Linux gives it a nice value, a number from minus 20 to 19. Higher means nicer to the others.", [
            (lambda: [*self.uncap(), *self.clear_blocks(), FadeOut(zero), self.chip_to("Taps", HOME["Taps"])], 0.6),
            "a nice value",
            (lambda: self.cap("nice: from -20 to 19. Higher is nicer to the others.", WHITE), 0.5),
        ])
        self.steps("Every process starts at 0, and the command nice can start one at 10.", [
            (lambda: [FadeIn(subs["Taps"][0])], 0.5),
            "start one at 10",
            (lambda: [FadeIn(subs["Totals"][0]), *self.cap("nice -n 10 <command>: start a program at nice 10")], 0.5),
        ])
        self.chips["Taps"].add(subs["Taps"][0])
        self.chips["Totals"].add(subs["Totals"][0])
        self.steps("Anyone may make their own program nicer. Making one less nice needs administrator rights. "
                   "Kindness is free; cutting in line takes permission.", [
            (lambda: self.cap("nicer: anyone.   less nice: administrator rights."), 0.5),
            "Kindness is free",
            (lambda: self.cap("kindness is free; cutting in line takes permission", YELLOW_M), 0.5),
        ], after=0.4)

        # ---------------- scene 4: weights, and a prediction ----------------
        thead = VGroup(left_at(T("nice", 20, GREY_B), SS_X, TB_Y[0]), left_at(T("weight", 20, GREY_B), SS_X, TB_Y[1]))
        tcols = VGroup(*[VGroup(M(n, 20).move_to([TB_X0 + 0.55 + k * TB_DX, TB_Y[0], 0]), M(w, 20).move_to([TB_X0 + 0.55 + k * TB_DX, TB_Y[1], 0]))
                         for k, (n, w) in enumerate(NICE)])
        trule = Line([SS_X, (TB_Y[0] + TB_Y[1]) / 2, 0], [TB_X0 + 0.55 + 5 * TB_DX + 0.45, (TB_Y[0] + TB_Y[1]) / 2, 0], stroke_width=1.2, color=GREY_D)

        def colbox(k, color):
            return SurroundingRectangle(tcols[k], color=color, buff=0.1, corner_radius=0.06)

        bx0, bx10 = colbox(1, BLUE_M), colbox(4, GOLD_M)
        w_t, w_o = chip_sub(HOME["Taps"], "weight 1024", 1), chip_sub(HOME["Totals"], "weight 110", 1)
        self.steps("Then the kernel turns each nice value into a weight, from a fixed table in its code.", [
            (lambda: self.uncap(), 0.3),
            "into a weight",
            (lambda: [FadeIn(thead), Create(trule), LaggedStart(*[FadeIn(c, shift=0.1 * DOWN) for c in tcols], lag_ratio=0.15)], 1.2),
        ])
        self.steps("Nice 0 weighs 1024. Nice 10 weighs 110. When tasks compete for one CPU, each gets its weight divided by the total.", [
            (lambda: [Create(bx0), FadeIn(w_t)], 0.6),
            "Nice 10 weighs",
            (lambda: [Create(bx10), FadeIn(w_o)], 0.6),
            "each gets its weight",
            (lambda: self.cap("share = its weight / the total of the weights", WHITE), 0.5),
        ])
        self.chips["Taps"].add(w_t)
        self.chips["Totals"].add(w_o)
        self.steps("So, 1024 against 110. What share does the totals job get? Pause and guess.", [
            "What share",
            (lambda: [glow(self.chips["Totals"][0], GOLD_M, 1.06)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        sb = share_bar(1024 / 1134)
        self.steps("About a tenth: 110 out of 1,134 is 9.7 percent. The tap loop gets 90.3. Less, but never none.", [
            (lambda: [*self.uncap(), FadeOut(strip_t), FadeIn(sb[0]), FadeIn(sb[1])], 0.6),
            "is 9.7",
            (lambda: [FadeIn(sb[3]), *self.cap("110 / 1,134 = 9.7%", GOLD_M)], 0.5),
            "The tap loop",
            (lambda: [FadeIn(sb[2]), *self.cap("1024 / 1,134 = 90.3%", BLUE_M)], 0.5),
            "Less, but never none",
            (lambda: self.cap("less, never none", YELLOW_M, 30), 0.5),
        ], after=0.4)

        # ---------------- scene 5: the score sheet ----------------
        ss_t = left_at(T("score sheet", 20, GREY_B), SS_X, SS_TOP)
        rlab = {n: left_at(T(n, 20, COL[n]), SS_X, ROW_Y[n]) for n in ("Taps", "Totals")}
        axis = Line([BAR_X0, ROW_Y["Taps"] + 0.3, 0], [BAR_X0, ROW_Y["Totals"] - 0.3, 0], stroke_width=1.5, color=GREY_C)
        self.bars = {n: bar(n, 0) for n in ("Taps", "Totals")}
        for n in ("Taps", "Totals"):
            self.vals[n] = 0
            self.vlabs[n] = bar_val(n, 0)
        self.steps("But how does the kernel hand out time by weight, turn after turn? Back to the console.", [
            (lambda: [*self.uncap(), FadeOut(bx0), FadeOut(bx10), FadeOut(sb), FadeOut(self.con_tag)], 0.5),
            "Back to the console",
            (lambda: [glow(con[0], WHITE, 1.03)], 0.6),
        ])
        self.steps("Keep a score sheet next to it that adds up each child's minutes, and let whoever has the smallest total play next.", [
            "a score sheet",
            (lambda: [FadeIn(ss_t), FadeIn(rlab["Taps"]), FadeIn(rlab["Totals"]), Create(axis),
                      FadeIn(self.bars["Taps"]), FadeIn(self.bars["Totals"]), FadeIn(self.vlabs["Taps"]), FadeIn(self.vlabs["Totals"])], 0.8),
            "the smallest total",
            (lambda: self.cap("the smallest total plays next", WHITE), 0.5),
        ])
        self.steps("Now say one child's minutes count about nine times over. Their total climbs fast, so their turns come round far less often.", [
            "count about nine",
            (lambda: [*self.cap("one child's minutes count about nine times over", GOLD_M), glow(self.chips["Totals"][0], GOLD_M, 1.06)], 0.6),
            "Their total climbs",
            (lambda: [Indicate(rlab["Totals"], color=GOLD_M, scale_factor=1.15)], 0.6),
        ])
        ss_t2 = left_at(T("score sheet: virtual runtime", 20, GREY_B), SS_X, SS_TOP)
        self.steps("Map it. The score is the task's virtual runtime: the CPU time it has really had, times 1024 divided by its weight.", [
            "virtual runtime",
            (lambda: [swap(ss_t, ss_t2), *self.cap("virtual runtime = CPU time × 1024 / weight", WHITE)], 0.6),
        ])
        self.steps("For nice 0, the clock runs at real speed. For nice 10, it runs 9.3 times faster. "
                   "And the rule fits in one line: run the task with the smallest virtual runtime.", [
            (lambda: [*self.cap("nice 0: × 1  (1024 / 1024)", BLUE_M), Indicate(rlab["Taps"], color=BLUE_M, scale_factor=1.15)], 0.5),
            "For nice 10",
            (lambda: [*self.cap("nice 10: × 9.3  (1024 / 110)", GOLD_M), Indicate(rlab["Totals"], color=GOLD_M, scale_factor=1.15)], 0.5),
            "the rule fits",
            (lambda: self.cap("the rule: run the task with the smallest virtual runtime", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 6: watch the scores ----------------
        def nine(start, dt=0.22):
            seq = []
            for i in range(9):
                v = start + 3 * (i + 1)
                seq.append(AnimationGroup(Transform(self.bars["Taps"], bar("Taps", v)), self.add_block("Taps"), run_time=dt))
            self.vals["Taps"] = start + 27
            return seq

        self.steps("Watch it. Taps plays 3 milliseconds: its score goes up by 3.", [
            (lambda: [*self.uncap(), FadeIn(strip_t)], 0.3),
            "Taps plays",
            (lambda: [self.chip_to("Taps", SLOT)], 0.5),
            "its score",
            (lambda: [*self.set_score("Taps", 3), self.add_block("Taps")], 0.6),
        ])
        self.steps("Now Totals has the smallest score, so it plays. Its 3 milliseconds add almost 28.", [
            (lambda: [Indicate(self.vlabs["Totals"], color=GOLD_M, scale_factor=1.3)], 0.5),
            "so it plays",
            (lambda: [self.chip_to("Taps", HOME["Taps"]), self.chip_to("Totals", SLOT)], 0.5),
            "Its 3 milliseconds",
            (lambda: [*self.set_score("Totals", 3 * 1024 / 110), self.add_block("Totals")], 0.8),
        ])
        self.steps("Now Taps is far behind, so it gets picked again, and again, until it passes 28. That's about nine turns for every one.", [
            (lambda: [self.chip_to("Totals", HOME["Totals"]), self.chip_to("Taps", SLOT)], 0.5),
            "gets picked again",
            (lambda: [FadeOut(self.vlabs["Taps"]), Succession(*nine(3))], 2.0),
            (lambda: [FadeIn(self.vlabs.__setitem__("Taps", bar_val("Taps", 30)) or self.vlabs["Taps"])], 0.3),
            "about nine turns",
            (lambda: self.cap("about nine turns for every one", WHITE), 0.5),
        ])
        counts = left_at(T("Taps: 19 turns    Totals: 2 turns", 20, GREY_B), STRIP_X0, SUB_Y)
        self.steps("Run it longer, and the shares settle at 90 and 10.", [
            (lambda: [self.chip_to("Taps", HOME["Taps"]), self.chip_to("Totals", SLOT)], 0.3),
            (lambda: [*self.set_score("Totals", 6 * 1024 / 110), self.add_block("Totals")], 0.4),
            (lambda: [self.chip_to("Totals", HOME["Totals"]), self.chip_to("Taps", SLOT), FadeOut(self.vlabs["Taps"])], 0.35),
            (lambda: [Succession(*nine(30, 0.17))], 1.53),
            (lambda: [FadeIn(self.vlabs.__setitem__("Taps", bar_val("Taps", 57)) or self.vlabs["Taps"]), FadeIn(counts)], 0.4),
        ], after=0.4)
        print(f"POSTER {self.renderer.time:.1f}")

        # ---------------- scene 7: the lab, and the name ----------------
        lab = left_at(T("lab box, 10 s on one CPU:  nice 0 got 9.01 s (90%),  nice 10 got 0.98 s (10%)", 20, WHITE), STRIP_X0, LAB_Y)
        self.steps("The lab box agrees with the arithmetic. Two loops on one CPU for 10 seconds, at nice 0 and nice 10: 9.01 seconds against 0.98.", [
            "Two loops",
            (lambda: [FadeIn(lab, shift=0.1 * UP)], 0.6),
            "9.01 seconds",
            (lambda: [Indicate(lab, color=GREEN_M, scale_factor=1.03)], 0.8),
        ])
        self.steps("That rule, smallest virtual runtime first, was the heart of the Completely Fair Scheduler, which Linux used from 2007 until 2023.", [
            "the heart of",
            (lambda: self.cap("CFS, the Completely Fair Scheduler: Linux 2.6.23 (2007) to 6.6 (2023)"), 0.6),
        ], after=0.4)

        # ---------------- scene 8: where the console breaks, and two rules ----------------
        late_l = left_at(T("late arrival", 20, GREY_B), SS_X, ROW_Y["late"])
        late_b = bar("late", 0, GREY_B)
        late_v = bar_val("late", 0)
        ages = left_at(T("would play for ages", 18, RED_M), BAR_X0 + 0.6, ROW_Y["late"])
        late_b2 = bar("late", 52, GREY_B)
        late_v2 = T("near the others", 17, GREY_B).move_to([BAR_X0 + 5.2 + 0.15, ROW_Y["late"], 0], aligned_edge=LEFT)
        self.steps("Here the console picture breaks. A child who shows up late starts at zero, and would play for an hour to catch up.", [
            (lambda: [*self.cap("where the console picture breaks"), FadeOut(lab), FadeOut(counts), *self.clear_blocks()], 0.6),
            "shows up late",
            (lambda: [FadeIn(late_l), FadeIn(late_b), FadeIn(late_v)], 0.6),
            "would play",
            (lambda: [FadeIn(ages, shift=0.1 * RIGHT), Indicate(late_v, color=RED_M, scale_factor=1.4)], 0.7),
        ])
        self.steps("The kernel never allows that. A task that starts late, or wakes from a long sleep, gets a score close to the others'.", [
            "A task that starts",
            (lambda: [FadeOut(ages), FadeOut(late_v)], 0.4),
            "gets a score",
            (lambda: [Transform(late_b, late_b2), FadeIn(late_v2), *self.cap("a late or waking task starts near the others' score", WHITE)], 0.9),
        ])
        self.steps("Two more things to keep. Only the ratio matters: nice 10 against nice 15 splits a CPU the same way as 0 against 5.", [
            (lambda: [FadeOut(VGroup(late_l, late_b, late_v2)), *self.cap("two more things to keep")], 0.6),
            "Only the ratio",
            (lambda: self.cap("only the ratio matters: nice 10 vs 15 splits like nice 0 vs 5", WHITE), 0.6),
        ])
        alone = VGroup(Rectangle(width=SHARE_W, height=0.42, stroke_width=0).set_fill(GOLD_M, 0.9).move_to([STRIP_X0 + SHARE_W / 2, STRIP_Y, 0]),
                       left_at(T("one task at nice 19, alone on an idle CPU: 100%", 20, GOLD_M), STRIP_X0, SUB_Y))
        self.steps("And weights only divide time among tasks that want it at the same moment. A nice 19 task alone on an idle CPU still gets all of it.", [
            (lambda: self.cap("weights only divide time among tasks that want it at once", WHITE), 0.6),
            "A nice 19 task",
            (lambda: [FadeIn(alone[0]), FadeIn(alone[1])], 0.7),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So how do you tell the kernel a task matters less, without starving it? Give it a lighter weight. "
                   "Its clock runs faster, the smallest score plays next, and shares follow the weights.", [
            (lambda: [*self.uncap(), FadeOut(alone)], 0.5),
            "a lighter weight",
            (lambda: [Create(bx10)], 0.5),
            "Its clock runs",
            (lambda: [Indicate(self.bars["Totals"], color=GOLD_M), Indicate(rlab["Totals"], color=GOLD_M, scale_factor=1.15)], 0.7),
            "the smallest score",
            (lambda: [Indicate(self.bars["Taps"], color=BLUE_M), Indicate(rlab["Taps"], color=BLUE_M, scale_factor=1.15)], 0.7),
            "shares follow",
            (lambda: self.cap("lighter weight, faster clock, smallest score plays", YELLOW_M), 0.6),
        ], after=0.5)
        bx5 = colbox(3, YELLOW_M)
        self.steps("One quick check. From the table, nice 5 weighs 335. Nice 0 against nice 5: what's the split? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(bx10)], 0.4),
            "nice 5 weighs",
            (lambda: [Create(bx5)], 0.5),
            "Nice 0 against",
            (lambda: [Create(bx0)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        sb5 = share_bar(1024 / 1359, "Taps", "Totals")
        sb5.remove(sb5[2], sb5[3])
        l5a = left_at(T("nice 0: 75.3%", 20, BLUE_M), STRIP_X0, SUB_Y)
        l5b = right_at(T("nice 5: 24.7%", 20, GOLD_M), STRIP_X0 + SHARE_W, SUB_Y)
        lab5 = left_at(T("lab box: 7.53 s against 2.47 s", 20, WHITE), STRIP_X0, LAB_Y)
        self.steps("About 75 against 25: 1024 out of 1,359. The lab box gave 7.53 seconds against 2.47.", [
            (lambda: [*self.uncap(), FadeIn(sb5), FadeIn(l5a), FadeIn(l5b)], 0.6),
            "1024 out of",
            (lambda: self.cap("1024 / 1,359 = 75.3%", BLUE_M), 0.5),
            "The lab box gave",
            (lambda: [FadeIn(lab5, shift=0.1 * UP)], 0.5),
        ], after=0.3)
        self.play(*self.cap("less CPU, never none", YELLOW_M, 30), run_time=0.6)
        self.wait(2.0)
