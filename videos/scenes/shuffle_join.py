from sfz import *

# Kokoro runs "reduce task" together into "reduced task"; this spelling keeps the two words apart
SAY.insert(0, (r"\breduce task", "ree-duce task"))

MX, RX, FX = -5.0, 4.8, -1.75                     # map column, reduce column, shuffle files
YS = [2.1, 0.9, -0.3, -1.5]                        # rows 0..3 (map tasks, files, reduce tasks)
BW, BH = 2.7, 0.9
BLK = 0.46                                         # one block of a shuffle file
PC = [BLUE_M, TEAL_M, PURPLE_M, GOLD_M]            # reduce task k's colour; merchant 42 hashes to 3
MER_Y, TOP, BOT = -2.95, 3.3, -2.95
GOLD_AT = [2, 5, 1, 4]                             # where merchant 42's dot sits in each map task


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn, so it can sit inside a LaggedStart."""
    d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_opacity(0)
    line = Line(path.get_start(), path.get_end())
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def frame(x, y, color, w=BW, h=BH):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    return r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14), opacity=1).move_to([x, y, 0])


def dots(x, y, gold, n=7):
    g = VGroup(*[Dot(radius=0.065, color=GOLD_M if j == gold else GREY_C) for j in range(n)]).arrange(RIGHT, buff=0.17)
    return g.move_to([x, y, 0])


def map_task(i):
    y = YS[i]
    return VGroup(frame(MX, y, WHITE).set_fill(BLACK, 1), T(f"map task {i}", 24).move_to([MX, y + 0.19, 0]),
                  dots(MX, y - 0.2, GOLD_AT[i]))


def red_status(k, s, color=GREY_B):
    return fit(T(s, 19, color), BW - 0.35).move_to([RX, YS[k] - 0.2, 0])


def reduce_task(k):
    y = YS[k]
    return VGroup(frame(RX, y, PC[k]), T(f"reduce task {k}", 24).move_to([RX, y + 0.19, 0]), red_status(k, "waiting", GREY_C))


def shuffle_file(y):
    sq = VGroup()
    for k in range(4):
        r = Square(BLK, stroke_color=PC[k], stroke_width=2.5)
        r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(PC[k]), 0.3), opacity=1)
        r.move_to([FX + (k - 1.5) * BLK, y, 0])
        sq.add(VGroup(r, M(str(k), 18).move_to(r)))
    return sq


def fetch(y0, k, i, color=None):
    """From a shuffle file's right edge at height y0 to reduce task k's left edge."""
    s = [FX + 2 * BLK + 0.08, y0 + (1.5 - k) * 0.07, 0]
    e = [RX - BW / 2 - 0.06, YS[k] + (1.5 - i) * 0.08, 0]
    return Arrow(s, e, buff=0, stroke_width=2.5, color=color or PC[k], max_tip_length_to_length_ratio=0.045)


def write_arrow(y, x0=MX + BW / 2):
    return Arrow([x0 + 0.06, y, 0], [FX - 2 * BLK - 0.06, y, 0], buff=0, stroke_width=2.5, color=GREY_B,
                 max_tip_length_to_length_ratio=0.3)


class ShuffleJoin(Base):
    """batch-07, section 4: equal keys must meet in one task, so each map task writes one shuffle file with a block per
    reduce task and every reduce task fetches its block from every file (4 x 4 = 16, 1,000 x 1,000 = a million); then
    payments JOIN merchants (500 rows) as a sort-merge join (shuffle both sides) and as a broadcast hash join."""

    def construct(self):
        self.title_card("The shuffle", "and two ways to join")

        maps = [map_task(i) for i in range(4)]
        self.steps("A payments job adds up each merchant's payments. A million payments sit in four partitions, "
                   "and one map task reads each one.", [
            "A million payments",
            (lambda: [LaggedStart(*[FadeIn(m[0]) for m in maps], lag_ratio=0.2)], 1.0),
            (lambda: [LaggedStart(*[FadeIn(m[2]) for m in maps], lag_ratio=0.2)], 0.8),
            "and one map task",
            (lambda: [LaggedStart(*[FadeIn(m[1]) for m in maps], lag_ratio=0.2)], 0.9),
        ])

        leg = VGroup(Dot(radius=0.07, color=GOLD_M), T("merchant 42's payments", 20, GREY_B)).arrange(RIGHT, buff=0.15)
        leg.move_to([MX, TOP, 0])
        reds = [reduce_task(k) for k in range(4)]
        self.steps("Merchant 42 has payments in all four, and they must meet in one task: "
                   "a reduce task, which owns a share of the merchants.", [
            (lambda: [FadeIn(leg)], 0.6),
            (lambda: [*[m[2][GOLD_AT[i]].animate(rate_func=there_and_back).scale(1.8) for i, m in enumerate(maps)]], 1.0),
            "a reduce task",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.2 * LEFT) for r in reds], lag_ratio=0.2)], 1.3),
        ])

        rule = mbox("owner = hash(merchant_id) mod 4", GREY_B, size=22, h=0.62).move_to([1.3, TOP, 0])
        self.steps("A map task finds each row's owner: hash the merchant id, divide by four, and keep the remainder. "
                   "Merchant 42 gets 3.", [
            (lambda: [FadeIn(rule, shift=0.15 * DOWN)], 0.8),
            "Merchant 42 gets 3",
            (lambda: [glow(reds[3][0], GOLD_M, 1.04)], 1.0),
        ])

        direct = [DashedLine([MX + BW / 2 + 0.08, YS[0] - 0.12 * k, 0], [RX - BW / 2 - 0.08, YS[k] + 0.1, 0], dash_length=0.1,
                             stroke_width=2, color=GREY_B) for k in range(4)]
        not_yet = red_status(3, "not started yet", RED_M)
        died = red_status(1, "died, rows lost", RED_M)
        self.steps("Streaming rows straight to their owners breaks. An owner may not be running yet, "
                   "or it may die and lose what it got.", [
            (lambda: [LaggedStart(*[Create(d) for d in direct], lag_ratio=0.15)], 1.2),
            "An owner may not",
            (lambda: [Transform(reds[3][2], not_yet), reds[3][0].animate.set_stroke(GREY_D)], 0.8),
            "or it may die",
            (lambda: [Transform(reds[1][2], died), reds[1][0].animate.set_stroke(RED_M)], 0.8),
        ])

        files = [shuffle_file(y) for y in YS]
        warrs = [write_arrow(y) for y in YS]
        disk = T("each map task's local disk", 20, GREY_B).move_to([FX, YS[0] + 0.55, 0])
        golds = [m[2][GOLD_AT[i]].copy() for i, m in enumerate(maps)]
        self.steps("So each map task writes first: one file on its own disk, sorted by owner, with one block per reduce task.", [
            (lambda: [*[FadeOut(d) for d in direct], *[Transform(r[2], red_status(k, "waiting", GREY_C)) for k, r in enumerate(reds)],
                      reds[3][0].animate.set_stroke(PC[3]), reds[1][0].animate.set_stroke(PC[1])], 0.6),
            "one file",
            (lambda: [*[GrowArrow(a) for a in warrs]], 0.5),
            (lambda: [*[LaggedStart(*[FadeIn(b) for b in f], lag_ratio=0.25) for f in files], FadeIn(disk)], 1.0),
            "with one block",
            (lambda: [*[g.animate.move_to(files[i][3]).scale(1.3) for i, g in enumerate(golds)]], 0.8),
            (lambda: [*[FadeOut(g) for g in golds], *[glow(f[3][0], GOLD_M, 1.1) for f in files]], 0.6),
        ])

        f3 = [fetch(YS[i], 3, i) for i in range(4)]
        all42 = red_status(3, "all of merchant 42", GOLD_M)
        self.steps("Then each reduce task fetches its block from every file. Reduce task 3 now holds all of merchant 42.", [
            (lambda: [*[GrowArrow(a) for a in f3]], 0.8),
            (lambda: [LaggedStart(*[flow(a, GOLD_M, 0.9) for a in f3], lag_ratio=0.15)], 1.4),
            "Reduce task 3",
            (lambda: [Transform(reds[3][2], all42)], 0.7),
        ])

        rest = [fetch(YS[i], k, i) for k in range(3) for i in range(4)]
        cnt = chip("4 map tasks × 4 reduce tasks = 16 fetches", GREY_B, 22).move_to([3.2, BOT, 0])
        cnt2 = chip("1,000 × 1,000 = a million fetches", RED_M, 22).move_to([3.2, BOT, 0])
        self.steps("Four map tasks and four reduce tasks make 16 fetches. A thousand of each make a million.", [
            (lambda: [LaggedStart(*[GrowArrow(a) for a in rest], lag_ratio=0.06),
                      *[Transform(reds[k][2], red_status(k, "has its merchants", GREY_B)) for k in range(3)]], 1.4),
            (lambda: [FadeIn(cnt, shift=0.15 * UP)], 0.7),
            "A thousand",
            (lambda: [FadeTransform(cnt, cnt2)], 0.8),
        ])

        allf = f3 + rest
        self.steps("Every row is written to disk, read back and sent over the network. "
                   "That's the shuffle, the most expensive step in most Spark jobs.", [
            (lambda: [*[glow(f[k][0], PC[k], 1.1) for f in files for k in range(4)]], 1.0),
            "sent over",
            (lambda: [LaggedStart(*[flow(a, a.get_color(), 0.9) for a in allf], lag_ratio=0.04)], 1.6),
        ])

        # ---- the join -----------------------------------------------------------------------------------------------
        mer = VGroup(frame(MX, MER_Y, GREEN_M), T("merchants", 24).move_to([MX, MER_Y + 0.19, 0]), dots(MX, MER_Y - 0.2, 3))
        leg2 = VGroup(Dot(radius=0.07, color=GOLD_M), T("merchant 42", 20, GREY_B)).arrange(RIGHT, buff=0.15).move_to(leg)
        self.steps("Now join each payment to its merchant. The merchants table has 500 rows.", [
            (lambda: [*[FadeOut(a) for a in allf], FadeOut(cnt2), *[Transform(r[2], red_status(k, "waiting", GREY_C)) for k, r in enumerate(reds)],
                      FadeTransform(leg, leg2)], 0.8),
            "The merchants table",
            (lambda: [FadeIn(mer, shift=0.2 * UP)], 0.8),
        ])

        mfile, mwarr = shuffle_file(MER_Y), write_arrow(MER_Y)
        mf = fetch(MER_Y, 3, 4, GREEN_M)
        both = red_status(3, "both sides of 42", GOLD_M)
        self.steps("One way: shuffle the merchants too, with the same rule. Merchant 42's row lands in reduce task 3, beside its payments.", [
            (lambda: [*[FadeIn(a) for a in f3]], 0.5),
            (lambda: [GrowArrow(mwarr), LaggedStart(*[FadeIn(b) for b in mfile], lag_ratio=0.25)], 0.9),
            "Merchant 42's row",
            (lambda: [GrowArrow(mf)], 0.6),
            (lambda: [flow(mf, GOLD_M, 0.9)], 0.9),
            (lambda: [Transform(reds[3][2], both)], 0.6),
        ])

        smj = chip("sort-merge join: 1,000,500 rows shuffled", GREEN_M, 21)
        smj.move_to([RX + BW / 2 - smj.width / 2, -3.2, 0])
        self.steps("Each reduce task sorts both sides and walks them together: a sort-merge join. "
                   "It works at any size, but it moves every payment.", [
            (lambda: [*[Transform(r[2], red_status(k, "sort, then merge", PC[k])) for k, r in enumerate(reds)]], 0.8),
            "a sort-merge",
            (lambda: [*[glow(r[0], PC[k], 1.03) for k, r in enumerate(reds)]], 1.0),
            "but it moves",
            (lambda: [FadeIn(smj, shift=0.15 * UP)], 0.8),
        ])

        drv = VGroup(frame(RX, 0.3, GREEN_M, h=1.1), T("driver", 24).move_to([RX, 0.52, 0]),
                     T("all 500 merchants", 19, GREY_B).move_to([RX, 0.08, 0]))
        copies = [chip("copy of merchants", GREEN_M, 20).move_to([FX, y, 0]) for y in YS]
        carrs = [Arrow([RX - BW / 2 - 0.08, 0.3 + 0.12 * (1.5 - i), 0], [copies[i].get_right()[0] + 0.1, YS[i], 0], buff=0,
                       stroke_width=2.5, color=GREEN_M, max_tip_length_to_length_ratio=0.05) for i in range(4)]
        self.steps("The other way leaves the payments in place. The driver, the process running the job, "
                   "sends a copy of the small table to every map task.", [
            (lambda: [*[FadeOut(a) for a in f3], FadeOut(mf), FadeOut(mwarr), FadeOut(mfile), *[FadeOut(f) for f in files],
                      *[FadeOut(a) for a in warrs], FadeOut(disk), *[FadeOut(r) for r in reds],
                      smj.animate.shift(0.65 * UP)], 0.9),
            "The driver",
            (lambda: [ReplacementTransform(mer, drv)], 1.0),
            "sends a copy",
            (lambda: [*[GrowArrow(a) for a in carrs]], 0.7),
            (lambda: [*[FadeIn(c) for c in copies], *[flow(a, GREEN_M, 0.8) for a in carrs]], 0.9),
        ])

        tabs = [chip("hash table: 500 merchants", GREEN_M, 20).move_to([FX, y, 0]) for y in YS]
        joined = [T("joined in place", 19, GREEN_M).move_to([MX, y - 0.2, 0]) for y in YS]
        bhj = chip("broadcast hash join: 0 payments shuffled", GREEN_M, 21)
        bhj.move_to([RX + BW / 2 - bhj.width / 2, -3.2, 0])
        self.steps("Each task builds a hash table from it and joins its payments right there. "
                   "That's a broadcast hash join, and no payment is shuffled.", [
            (lambda: [*[FadeOut(a) for a in carrs], *[FadeTransform(c, t) for c, t in zip(copies, tabs)]], 0.8),
            "and joins",
            (lambda: [*[Transform(m[2], j) for m, j in zip(maps, joined)]], 1.0),
            "That's a broadcast",
            (lambda: [FadeIn(bhj, shift=0.15 * UP)], 0.8),
        ])

        cap = T("Spark broadcasts by itself\nwhen a side looks under 10 MB", 20, GREY_B).move_to([RX - 0.3, -1.0, 0])
        smj2 = chip("sort-merge join: 165 ms", GREEN_M, 21)
        smj2.move_to([RX + BW / 2 - smj2.width / 2, -2.55, 0])
        bhj2 = chip("broadcast hash join: 91 ms", GREEN_M, 21)
        bhj2.move_to([RX + BW / 2 - bhj2.width / 2, -3.2, 0])
        self.steps("It ran in about half the time. But every machine holds a copy, so Spark only does this by itself below 10 MB.", [
            (lambda: [FadeTransform(smj, smj2), FadeTransform(bhj, bhj2)], 1.0),
            "But every machine",
            (lambda: [*[glow(t[0], GREEN_M, 1.06) for t in tabs]], 1.0),
            "so Spark only",
            (lambda: [FadeIn(cap, shift=0.15 * UP)], 0.8),
        ])

        self.steps("Shuffle both sides when both are big. When one side is small, send it to the data.", [
            (lambda: [glow(smj2[0], GREEN_M, 1.04)], 1.0),
            "When one side",
            (lambda: [glow(drv[0], GREEN_M, 1.04), LaggedStart(*[glow(t[0], GREEN_M, 1.06) for t in tabs], lag_ratio=0.15)], 1.2),
        ])
        self.wait(0.6)
