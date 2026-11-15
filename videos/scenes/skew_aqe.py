from sfz import *

Y0, SC = -2.55, 3.4 / 346023               # bar baseline, units per record
XL, XR = -6.1, 2.0                         # chart left and right
HOT = 5
# records each join task fetches from merchants other than merchant 7 (median about 43,593)
BASE = [43100, 44200, 42800, 43593, 44900, 46023, 43000, 44500, 42500, 43900, 50793, 44800, 42900, 43593, 44100, 43700]
RED7 = 300000                              # merchant 7's payments, all in partition HOT
PIECES = [86635, 86500, 86450, 86438]      # AQE's four pieces of the hot partition (346,023 in all)
SALTS = [1, 3, 3, 8, 10, 10, 12, 14]       # where the 8 salted keys of merchant 7 hash to
NX, NY = 2.4, [0.2, -0.35, -0.9, -1.45]    # notes, right of the chart
PAY = np.array([-3.6, 3.0, 0])
MER = np.array([1.0, 3.0, 0])


def fillc(color, a=0.14):
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
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def slot(i, n=16):
    step = (XR - XL - 0.2) / n
    return XL + 0.1 + step * (i + 0.5), step * 0.68


def bar(i, grey, red, n=16, red_c=RED_M):
    x, w = slot(i, n)
    g = Rectangle(width=w, height=max(0.01, grey * SC), stroke_width=0).set_fill(GREY_B, 0.85)
    g.move_to([x, Y0 + g.height / 2, 0])
    r = Rectangle(width=w, height=max(0.001, red * SC), stroke_width=0).set_fill(red_c, 0.9 if red else 0)
    r.move_to([x, Y0 + g.height + r.height / 2, 0])
    return VGroup(g, r)


def ytop(n):
    return Y0 + n * SC


def note(s, k, color=GREY_B, size=19):
    return left_at(T(s, size, color), NX, NY[k])


def hline(n, color, dash=True):
    y = ytop(n)
    return DashedLine([XL, y, 0], [XR, y, 0], dash_length=0.1, stroke_width=2, color=color) if dash else \
        Line([XL, y, 0], [XR, y, 0], stroke_width=2, color=color)


def flow(a, b, color, rt=0.8):
    d = Dot(radius=0.085, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.15))


class SkewAqe(Base):
    """batch-08, section 2: merchant 7 has 30% of a million payments; a sort-merge join into 16 partitions sends all of
    them to one task: 346,023 records against a median of 43,593. AQE's skew join (over 5x the median and over 256 MB)
    splits the hot partition along map-task blocks: 4 map tasks, 4 pieces, 19 tasks, hottest 86,635. Salting with
    pmod(payment_id, 8) and 8 copies of each merchant row: hottest 125,793, since 8 salts in 16 partitions collide."""

    def construct(self):
        self.title_card("Skew: one hot key", "adaptive query execution and salting")

        pay = VGroup(RoundedRectangle(corner_radius=0.12, width=3.6, height=0.9, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1),
                     T("payments: 1,000,000", 22).shift(0.17 * UP), T("merchant 7: 30%", 18, RED_M).shift(0.2 * DOWN)).move_to(PAY)
        mer = VGroup(RoundedRectangle(corner_radius=0.12, width=3.0, height=0.9, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M), 1),
                     T("merchants", 22).shift(0.17 * UP), T("merchant 7: one row", 18, BLUE_M).shift(0.2 * DOWN)).move_to(MER)
        axis = Line([XL, Y0, 0], [XR, Y0, 0], stroke_width=2.5, color=GREY_B)
        alab = T("16 join tasks: records each one fetches", 17, GREY_B).move_to([(XL + XR) / 2, Y0 - 0.35, 0])
        top = PAY + 0.5 * DOWN

        def spread(n=32):
            return [LaggedStart(*[flow(top, [slot(i % 16)[0], Y0 + 0.1, 0], GREY_B, 0.8) for i in range(n)], lag_ratio=0.04)]

        self.steps("One marketplace merchant, merchant 7, has 30 percent of a million payments. "
                   "To join payments with merchants, Spark shuffles both into 16 partitions by merchant id.", [
            (lambda: [FadeIn(pay, shift=0.1 * DOWN)], 0.7),
            "To join",
            (lambda: [FadeIn(mer, shift=0.1 * DOWN), Create(axis), FadeIn(alab)], 0.8),
            "Spark shuffles",
            (lambda: spread(), 2.0),
        ])

        bars = [bar(i, BASE[i], RED7 if i == HOT else 0) for i in range(16)]
        self.steps("Every row with the same key goes to the same partition. "
                   "So all of merchant 7's payments land in one task.", [
            (lambda: [LaggedStart(*[flow(top, [slot(i)[0], Y0 + 0.1, 0], GREY_B, 0.7) for i in (0, 3, 9, 12, 15)], lag_ratio=0.15)], 1.0),
            "So all of",
            (lambda: [LaggedStart(*[flow(top, [slot(HOT)[0], Y0 + 0.1, 0], RED_M, 0.7) for _ in range(12)], lag_ratio=0.08)], 1.6),
        ])

        med = hline(43593, GREY_C)
        medl = left_at(T("median 43,593", 17, GREY_C), XR + 0.08, ytop(43593))
        hotl = T("346,023", 20, RED_M).move_to([slot(HOT)[0], ytop(346023) + 0.22, 0])
        self.steps("The median task fetches about 44 thousand records. That one fetches 346 thousand, eight times as many.", [
            (lambda: [LaggedStart(*[GrowFromEdge(VGroup(b[0]), DOWN) for b in bars], lag_ratio=0.03)], 1.0),
            (lambda: [Create(med), FadeIn(medl)], 0.6),
            "That one",
            (lambda: [GrowFromEdge(bars[HOT][1], DOWN)], 1.0),
            (lambda: [FadeIn(hotl, shift=0.1 * UP)], 0.5),
        ])

        self.add(*bars)
        end = hline(346023, RED_M)
        endl = left_at(T("the stage ends here", 17, RED_M), XR + 0.08, ytop(346023))

        def idle(n=16, tops=None, hottest=346023):
            g = VGroup()
            for i in range(n):
                t = tops[i]
                if t < hottest - 1:
                    x, w = slot(i, n)
                    r = Rectangle(width=w, height=(hottest - t) * SC, stroke_width=0).set_fill(GREY_D, 0.35)
                    g.add(r.move_to([x, ytop(t) + r.height / 2, 0]))
            return g

        tops0 = [BASE[i] + (RED7 if i == HOT else 0) for i in range(16)]
        idl = idle(16, tops0)
        n1, n2 = note("15 cores finish early", 0, GREY_B), note("and wait for one", 1, GREY_B)
        sk = note("this is skew", 2, RED_M, 22)
        self.steps("A stage ends when its slowest task ends. Fifteen cores finish early and wait for one. This is skew.", [
            (lambda: [Create(end), FadeIn(endl)], 0.8),
            "Fifteen cores",
            (lambda: [LaggedStart(*[GrowFromEdge(r, DOWN) for r in idl], lag_ratio=0.04), FadeIn(n1), FadeIn(n2)], 1.2),
            "This is skew",
            (lambda: [FadeIn(sk, shift=0.1 * UP)], 0.6),
        ])

        n3 = note("16 or 2,000 partitions:", 0)
        n4 = note("merchant 7 is still one key,", 1)
        n5 = note("in one partition", 2, RED_M)
        self.steps("More partitions don't help. Merchant 7 is one key, and one key lands in one partition, "
                   "out of 16 or out of 2,000.", [
            (lambda: [FadeOut(VGroup(n1, n2, sk))], 0.35), (lambda: [FadeIn(n3)], 0.35),
            "Merchant 7 is",
            (lambda: [FadeIn(n4)], 0.5),
            "lands in one",
            (lambda: [FadeIn(n5), bars[HOT][1].animate(rate_func=there_and_back).set_fill(YELLOW_M, 1)], 0.9),
        ])

        # ---- AQE skew join -----------------------------------------------------------------------------------------
        thr = hline(5 * 43593, GOLD_M)
        thrl = left_at(T("5 x median", 17, GOLD_M), XL + 0.1, ytop(5 * 43593) + 0.2)
        a1 = note("AQE, after the map stage:", 0, GOLD_M)
        a2 = note("every partition's size is known", 1, GOLD_M)
        self.steps("Adaptive query execution waits for the shuffle. "
                   "When the map tasks finish, Spark knows the size of every partition.", [
            (lambda: [FadeOut(VGroup(n3, n4, n5, idl))], 0.4), (lambda: [FadeIn(a1)], 0.4),
            "When the map tasks",
            (lambda: [LaggedStart(*[b.animate(rate_func=there_and_back).set_opacity(0.4) for b in bars], lag_ratio=0.05)], 1.2),
            (lambda: [FadeIn(a2)], 0.5),
        ])

        a3 = note("skewed: over 5 x median", 0, GOLD_M)
        a4 = note("and over 256 MB", 1, GOLD_M)
        a5 = note("SortMergeJoin(skew=true)", 2, TEAL_M)
        tops1 = [BASE[i] for i in range(16)]
        new_bars = []
        for k, i in enumerate([i for i in range(16) if i != HOT]):
            new_bars.append((bars[i], bar(i if i < HOT else i + 3, BASE[i], 0, 19)))
        pieces = [bar(HOT + p, 46023 / 4, PIECES[p] - 46023 / 4, 19) for p in range(4)]
        pg = VGroup(*pieces)
        copies = VGroup(*[Square(0.16, stroke_width=0).set_fill(BLUE_M, 1).move_to([slot(HOT + p, 19)[0], ytop(PIECES[p]) + 0.2, 0])
                          for p in range(4)])
        self.steps("A partition more than five times the median, and over 256 megabytes, counts as skewed. "
                   "AQE splits it, and gives each piece its own copy of merchant 7's row.", [
            (lambda: [FadeOut(VGroup(a1, a2))], 0.35), (lambda: [Create(thr), FadeIn(thrl), FadeIn(a3)], 0.6),
            "and over 256",
            (lambda: [FadeIn(a4)], 0.5),
            "AQE splits it",
            (lambda: [FadeOut(hotl), FadeOut(end), FadeOut(endl), *[Transform(o, n) for o, n in new_bars],
                      *[TransformFromCopy(bars[HOT], p) for p in pieces], FadeOut(bars[HOT]), FadeIn(a5),
                      Transform(alab, T("19 join tasks: records each one fetches", 17, GREY_B).move_to(alab))], 1.2),
            "its own copy",
            (lambda: [LaggedStart(*[FadeIn(c, target_position=MER + 0.55 * DOWN, scale=0.5) for c in copies], lag_ratio=0.2), glow(mer[0], BLUE_M)], 1.2),
        ])

        end2 = hline(86635, GREEN_M)
        e2l = left_at(T("hottest: 86,635", 17, GREEN_M), XL + 0.1, ytop(86635) + 0.22)
        b1 = note("cuts only between map blocks:", 0, GOLD_M)
        b2 = note("4 map tasks, at most 4 pieces", 1, GOLD_M)
        b3 = note("16 tasks became 19", 2, GOLD_M)
        self.steps("It can only cut between the blocks the map tasks wrote. Four map tasks make at most four pieces: "
                   "16 tasks become 19, and the hottest fetches a quarter of before.", [
            (lambda: [FadeOut(VGroup(a3, a4)), a5.animate.move_to(note("SortMergeJoin(skew=true)", 3, TEAL_M))], 0.4), (lambda: [FadeIn(b1)], 0.4),
            "Four map tasks",
            (lambda: [FadeIn(b2), *[glow(VGroup(p[1]), GOLD_M, 1.05) for p in pieces]], 0.9),
            "16 tasks become",
            (lambda: [FadeIn(b3)], 0.5),
            "and the hottest",
            (lambda: [Create(end2), FadeIn(e2l)], 0.8),
        ])

        # ---- salting -------------------------------------------------------------------------------------------------
        back = [bar(i, BASE[i], RED7 if i == HOT else 0) for i in range(16)]
        s1 = left_at(M("salt = pmod(payment_id, 8)", 17, PURPLE_M), NX, NY[0])
        s2 = note("merchant rows copied 8 times", 1, PURPLE_M)
        s3 = left_at(M("join on (merchant_id, salt)", 17, PURPLE_M), NX, NY[2])
        olds = [o for o, _ in new_bars]
        self.steps("Salting splits the key by hand. Each payment gets a salt from 0 to 7, taken from its payment id, "
                   "and each merchant row is copied eight times, once per salt.", [
            (lambda: [FadeOut(VGroup(b1, b2, b3, a5, end2, e2l, copies, thr, thrl)),
                      *[Transform(o, back[i if i < HOT else i]) for o, i in zip(olds, [i for i in range(16) if i != HOT])],
                      FadeOut(pg), FadeIn(back[HOT]),
                      Transform(alab, T("16 join tasks: records each one fetches", 17, GREY_B).move_to(alab))], 1.0),
            "Each payment gets",
            (lambda: [FadeIn(s1, shift=0.1 * UP), Transform(pay[2], T("merchant 7: salts 0 to 7", 18, PURPLE_M).move_to(pay[2]))], 0.8),
            "and each merchant row",
            (lambda: [FadeIn(s2, shift=0.1 * UP), Transform(mer[2], T("merchant 7: 8 copies", 18, PURPLE_M).move_to(mer[2])),
                      glow(mer[0], PURPLE_M)], 0.8),
        ])

        cnt = [SALTS.count(i) for i in range(16)]
        salted = [bar(i, BASE[i], 37500 * cnt[i], 16, PURPLE_M) for i in range(16)]
        end3 = hline(125793, PURPLE_M)
        e3l = left_at(T("hottest: 125,793", 17, PURPLE_M), XL + 0.1, ytop(125793) + 0.25)
        s4 = note("two salts can share a partition", 3, GREY_B)
        self.steps("Joined on merchant and salt, merchant 7 becomes eight keys that hash to different tasks. "
                   "The hottest task drops to 126 thousand records. Some salts still share a partition.", [
            (lambda: [FadeIn(s3, shift=0.1 * UP)], 0.6),
            "becomes eight keys",
            (lambda: [*[Transform(o, salted[i]) for o, i in zip(olds, [i for i in range(16) if i != HOT])],
                      Transform(back[HOT], salted[HOT])], 1.4),
            "The hottest task",
            (lambda: [Create(end3), FadeIn(e3l)], 0.8),
            "Some salts",
            (lambda: [FadeIn(s4), glow(VGroup(olds[3][1]), YELLOW_M, 1.1), glow(VGroup(olds[9][1]), YELLOW_M, 1.1)], 0.9),
        ])

        r1 = note("never rand(): a retried task", 0, RED_M)
        r2 = note("must send each row to the same place", 1, RED_M)
        self.steps("Take the salt from the data, never at random. "
                   "A retried task must send every row where the first attempt sent it.", [
            (lambda: [s1.animate(rate_func=there_and_back).scale(1.1)], 0.9),
            "A retried task",
            (lambda: [FadeOut(VGroup(s1, s2, s3, s4))], 0.35), (lambda: [FadeIn(r1), FadeIn(r2)], 0.45),
        ])

        self.steps("One hot key makes one task do the work of many. Split the key, and the work spreads.", [
            (lambda: [FadeOut(VGroup(r1, r2)), end3.animate.set_color(GREEN_M), e3l.animate.set_color(GREEN_M)], 0.8),
            "Split the key",
            (lambda: [LaggedStart(*[o.animate(rate_func=there_and_back).set_opacity(0.5) for o in olds + [back[HOT]]], lag_ratio=0.04)], 1.2),
        ])
        self.wait(0.6)
