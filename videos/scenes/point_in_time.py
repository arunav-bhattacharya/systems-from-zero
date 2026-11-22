from sfz import *

SAY.insert(0, (r"\bASOF JOIN\b", "as-of join"))
# Kokoro puts a vowel inside "chargeback" ("charge-a-back")
SAY.insert(0, (r"\bchargeback(s?)\b", r"charge back\1"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bFeast\b", "feast"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
AX_Y, CHIP_Y = 0.0, 0.75                     # the timeline, and the nightly rows above it
VALUES = {10: 0, 11: 0, 12: 0, 13: 1, 14: 1, 15: 1, 16: 1}
TR_Y = -1.45                                 # the training row
CAP_Y, BAR_Y = -3.2, -2.86
TOP_Y, SUB_Y = 3.25, 2.75


def X(day, hour=0.0):
    """x on the timeline for `hour` o'clock on `day` October."""
    return -5.6 + (day - 10 + hour / 24) * 1.85


XE = X(10, 14)                               # the fraud, 10 October 14:00


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.08):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def pulse(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.1)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def frow(day, color=None, y=CHIP_Y, v=None):
    """The row the nightly job writes at 02:00 for `day`, counted as of midnight."""
    v = VALUES[day] if v is None else v
    color = color or (GOLD_M if v else GREY_B)
    x = X(day, 2)
    r = RoundedRectangle(corner_radius=0.08, width=0.6, height=0.54, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    return VGroup(r, M(str(v), 26).move_to([x, y, 0]))


def stem(day):
    x = X(day, 2)
    return VGroup(Dot([x, AX_Y, 0], radius=0.055, color=GREY_B),
                  Line([x, AX_Y + 0.07, 0], [x, CHIP_Y - 0.28, 0], stroke_width=1.5, color=GREY_D))


def arc_to(x0, y0, day, color, angle, y=CHIP_Y):
    return ArcBetweenPoints([x0, y0, 0], [X(day, 2), y + 0.32, 0], angle=angle, color=color,
                            stroke_width=3).add_tip(tip_length=0.16)


class PointInTime(Base):
    """batch-14, section 1. A fraud model: 98% on last month's payments, 62% live. One card's nightly feature
    (chargebacks in 30 days, written 02:00 as of midnight); fraud on 10 October 14:00, its chargeback on the 12th, so 1
    from the 13th. The newest-row join gives the fraud's training row a 1 (label leakage); the timetable; the
    point-in-time join gives 0. Two times per row: a 13 October 01:00 payment skips the 13 October row (written 02:00)
    and the 12 October correction written on the 15th. The rule, the demo's 98/62/62, tools and their default, and a
    check question."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_tr(self, when, v="?", color=GREY_B):
        new = VGroup(T("training row:", 22, GREY_B), M(f"{when}  →  chargebacks_30d =", 22), M(v, 24, color)).arrange(RIGHT, buff=0.25)
        left_at(new, -6.3, TR_Y)
        old, self.tr = self.tr, new
        return [swap(old, new)]

    def set_v(self, v, color):
        new = M(v, 24, color).move_to(self.tr[2])
        old = self.tr[2]
        self.tr.remove(old)
        self.tr.add(new)
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.tr = None
        self.title_card("98% on paper, 62% at the till", "training data that can't see the future")

        # ---------------- scene 1: 98 and 62 ----------------
        bub_t = VGroup(T("your bank", 18, GREY_B), T("Was this you? 300.00 at a shop in Lisbon.", 26)).arrange(DOWN, buff=0.15).move_to([0, 1.4, 0])
        bub = RoundedRectangle(corner_radius=0.3, width=bub_t.width + 0.8, height=1.5, stroke_color=WHITE, stroke_width=2.5).set_fill("#15191d", 1)
        bub.move_to([0, 1.4, 0])
        p98 = VGroup(T("on last month's payments", 22, GREY_B), T("98%", 60, GOLD_M)).arrange(DOWN, buff=0.2).move_to([-3, -1.3, 0])
        p62 = VGroup(T("live", 22, GREY_B), T("62%", 60, RED_M)).arrange(DOWN, buff=0.2).move_to([3, -1.3, 0])
        qm = T("?", 64, YELLOW_M).move_to([0, -1.25, 0])
        self.steps("Your bank sends you a text: \"Was this you? 300.00 at a shop in Lisbon.\" Behind it is a program that learned "
                   "from past payments which ones turned out to be fraud.", [
            (lambda: [FadeIn(VGroup(bub, bub_t), shift=0.2 * UP)], 0.8),
            "Behind it",
            (lambda: [glow(bub, BLUE_M, 1.03)], 0.9),
        ])
        self.steps("Picture the team that built one. Tested on last month's payments, it caught 98 percent of the fraud. "
                   "Then they switched it on, and it caught 62.", [
            "Tested on",
            (lambda: [FadeIn(p98, shift=0.1 * UP)], 0.7),
            "Then they switched",
            (lambda: [FadeIn(p62, shift=0.1 * UP)], 0.7),
        ])
        self.steps("Nothing in the code was wrong. So where did the difference go? Hold that question.", [
            "So where",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: labels and features ----------------
        label = left_at(T("label: a payment on 10 Oct, 14:00", 24), -6.3, TOP_Y)
        lab_f = left_at(T("fraud", 24, RED_M), label.get_right()[0] + 0.2, TOP_Y)
        weeks = left_at(T("(known weeks later)", 20, GREY_B), lab_f.get_right()[0] + 0.25, TOP_Y)
        self.steps("A model like this learns from labels: past payments, each marked fraud or not. "
                   "The mark comes weeks later, when a chargeback arrives or doesn't.", [
            (lambda: [FadeOut(VGroup(bub, bub_t, p98, p62, qm))], 0.6),
            "past payments",
            (lambda: [FadeIn(label, shift=0.1 * DOWN)], 0.6),
            "each marked",
            (lambda: [FadeIn(lab_f)], 0.5),
            "The mark comes",
            (lambda: [FadeIn(weeks)], 0.5),
        ])
        self.steps("A chargeback is the bank taking the money back from the shop, after the cardholder says, "
                   "I didn't make this payment.", [
            (lambda: self.cap("chargeback: the bank takes the money back from the shop", RED_M), 0.6),
            "I didn't",
            (lambda: [pulse(lab_f, RED_M)], 0.7),
        ])
        axis = Arrow([-6.3, AX_Y, 0], [6.4, AX_Y, 0], buff=0, stroke_width=2.5, color=GREY_B, max_tip_length_to_length_ratio=0.015)
        ticks = VGroup(*[Line([X(d), AX_Y - 0.1, 0], [X(d), AX_Y + 0.1, 0], stroke_width=2, color=GREY_B) for d in range(10, 17)])
        days = VGroup(*[T(f"{d} Oct", 20, GREY_B).move_to([X(d) + 0.45, AX_Y - 0.36, 0]) for d in range(10, 17)])
        feat = left_at(T("feature: chargebacks on this card in the last 30 days", 22, GOLD_M), -6.3, SUB_Y)
        self.steps("It also learns from features: numbers about the card, like how many chargebacks it had in the last 30 days.", [
            (lambda: [*self.uncap(), Create(axis), FadeIn(ticks), FadeIn(days)], 1.0),
            "like how many",
            (lambda: [FadeIn(feat, shift=0.1 * DOWN)], 0.6),
        ])
        rows = {d: frow(d) for d in VALUES}
        stems = {d: stem(d) for d in VALUES}
        self.steps("Every night at two, a job writes one row for the card, counted as of midnight. For now, the count is 0.", [
            "a job writes",
            (lambda: [*self.cap("one row a night: written at 02:00, counted as of midnight"),
                      LaggedStart(*[FadeIn(VGroup(stems[d], rows[d]), shift=0.1 * DOWN) for d in (10, 11, 12)], lag_ratio=0.3)], 1.2),
            "For now",
            (lambda: [*[glow(rows[d][0], GREY_B) for d in (10, 11, 12)]], 0.8),
        ])

        # ---------------- scene 3: the easy join ----------------
        ev = DashedLine([XE, AX_Y - 0.1, 0], [XE, 1.3, 0], dash_length=0.08, stroke_width=3, color=RED_M)
        evl = T("fraud, 14:00", 20, RED_M).move_to([XE, 1.55, 0])
        cb = Triangle(color=RED_M, fill_opacity=1).scale(0.1).move_to([X(12, 12), AX_Y + 0.02, 0])
        cbl = T("its chargeback arrives", 20, RED_M).move_to([X(12, 12), AX_Y - 0.8, 0])
        self.steps("On 10 October at two in the afternoon, someone uses the card for fraud. Its chargeback arrives on the twelfth.", [
            (lambda: [*self.uncap(), Create(ev), FadeIn(evl)], 0.8),
            "Its chargeback",
            (lambda: [FadeIn(cb, scale=0.5), FadeIn(cbl, shift=0.1 * UP)], 0.7),
        ])
        self.steps("So from the thirteenth on, the nightly count is 1.", [
            "from the thirteenth",
            (lambda: [LaggedStart(*[FadeIn(VGroup(stems[d], rows[d]), shift=0.1 * DOWN) for d in (13, 14, 15, 16)], lag_ratio=0.25)], 1.2),
        ])
        self.steps("Now build the training row for that fraud. The easy join takes the card's newest row, the one that's there today. "
                   "What number does the training row get? Pause and guess.", [
            (lambda: self.set_tr("10 Oct 14:00"), 0.6),
            "The easy join",
            (lambda: self.cap("the easy join: the card's newest row, as it is today", WHITE), 0.5),
            "the one that's",
            (lambda: [glow(rows[16][0], GOLD_M)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        red_arc = arc_to(XE + 0.08, 1.05, 16, RED_M, -0.3)
        fut = Rectangle(width=6.4 - XE - 0.05, height=1.6, stroke_width=0).set_fill(RED_M, 0.09)
        fut.move_to([(XE + 0.05 + 6.4) / 2, 0.45, 0])
        futl = T("written after the payment", 20, RED_M).move_to([X(15, 2), AX_Y - 0.8, 0])
        self.steps("1. And that 1 is the chargeback this very fraud caused.", [
            (lambda: [*self.uncap(), Create(red_arc)], 0.6),
            (lambda: self.set_v("1", RED_M), 0.4),
            "And that 1",
            (lambda: [glow(rows[13][0], RED_M), cb.animate(rate_func=there_and_back).scale(2)], 0.9),
        ])
        self.steps("So the model learns that fraud comes with a chargeback already on file. "
                   "That's like learning to spot a fire by the fire engine parked outside.", [
            (lambda: [FadeIn(fut), FadeIn(futl)], 0.8),
            "fire engine",
            (lambda: self.cap("spotting a fire by the fire engine parked outside", RED_M), 0.5),
        ])
        self.steps("It works great on old photos. It's no help while the fire is starting.", [
            "while the fire",
            (lambda: [ev.animate(rate_func=there_and_back).set_stroke(width=6)], 0.8),
        ])
        self.steps("This has a name: label leakage. Facts from after the decision reach the data the model learns from.", [
            "label leakage",
            (lambda: self.cap("label leakage: facts from after the decision reach the training data", RED_M), 0.6),
            "Facts from after",
            (lambda: [fut.animate(rate_func=there_and_back).set_fill(RED_M, 0.22)], 0.9),
        ])

        # ---------------- scene 4: the timetable ----------------
        def board(title, line, color, x):
            r = RoundedRectangle(corner_radius=0.1, width=4.6, height=1.05, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.1), 1)
            r.move_to([x, -2.4, 0])
            return VGroup(r, T(title, 22, color).move_to([x, -2.2, 0]), T(line, 18, GREY_B).move_to([x, -2.6, 0]))

        b_tue = board("the board on Tuesday", "what she could see at 14:00", GREEN_M, -3.2)
        b_now = board("today's board", "with changes made since", RED_M, 3.2)
        self.steps("A railway makes the rule easy to see. A passenger says she missed her connection at 14:00 last Tuesday.", [
            (lambda: self.uncap(), 0.4),
            "A passenger",
            (lambda: self.cap("missed her connection at 14:00, last Tuesday", WHITE), 0.5),
        ])
        self.steps("To judge whether she picked a sensible train, you'd look at the timetable that was on the board that Tuesday, "
                   "not today's. Today's board knows about changes she couldn't have seen.", [
            "on the board that Tuesday",
            (lambda: [FadeIn(b_tue, shift=0.1 * UP)], 0.6),
            "not today's",
            (lambda: [FadeIn(b_now, shift=0.1 * UP)], 0.6),
            "Today's board knows",
            (lambda: [glow(b_now[0], RED_M, 1.03)], 0.8),
        ])
        self.steps("Map it. The passenger's Tuesday is the moment of the payment. Each night's row is the board on that day. "
                   "And the newest row is today's board.", [
            "The passenger's Tuesday",
            (lambda: [*self.cap("her Tuesday = the moment of the payment", WHITE), ev.animate(rate_func=there_and_back).set_stroke(width=6)], 0.8),
            "Each night's row",
            (lambda: [*self.cap("each night's row = the board on that day", WHITE),
                      LaggedStart(*[glow(rows[d][0], GREY_B) for d in (10, 11, 12)], lag_ratio=0.3)], 1.0),
            "And the newest",
            (lambda: [*self.cap("the newest row = today's board", RED_M), glow(rows[16][0], RED_M), glow(b_now[0], RED_M, 1.03)], 0.9),
        ])

        # ---------------- scene 5: look back from the payment ----------------
        green_arc = arc_to(XE - 0.08, 1.05, 10, GREEN_M, 1.2)
        self.steps("So, look back from each label instead. Take the newest row that was there at the moment of the payment.", [
            (lambda: [FadeOut(b_now), FadeOut(b_tue), *self.uncap(), FadeOut(red_arc), *self.set_v("?", GREY_B)], 0.7),
            "Take the newest",
            (lambda: [Create(green_arc)], 0.8),
        ])
        self.steps("For this fraud, that's the 10 October row: 0. That's what the model would have read at the till. "
                   "This is called a point in time join.", [
            (lambda: [Transform(rows[10], frow(10, GREEN_M))], 0.5),
            (lambda: self.set_v("0", GREEN_M), 0.4),
            "That's what",
            (lambda: [glow(rows[10][0], GREEN_M, 1.15)], 0.8),
            "This is called",
            (lambda: self.cap("point-in-time join: the newest row that existed at the payment's moment", GREEN_M), 0.6),
        ])

        # ---------------- scene 6: two times on every row ----------------
        self.steps("So far so good. But each row carries two times. One is the moment it's about: midnight. "
                   "The other is when it was written: two in the morning.", [
            (lambda: [*self.uncap(), FadeOut(green_arc), Transform(rows[10], frow(10))], 0.6),
            "One is the moment",
            (lambda: self.cap("1. the moment it's about: midnight", WHITE), 0.5),
            "The other",
            (lambda: self.cap("1. the moment it's about: midnight      2. when it was written: 02:00", WHITE), 0.5),
        ])
        # a close-up strip of the night of 13 October
        ZX0, ZX1, ZY = -4.5, 4.5, -2.35

        def zx(h):
            return ZX0 + (ZX1 - ZX0) * h / 3

        zline = Line([ZX0, ZY, 0], [ZX1, ZY, 0], stroke_width=2.5, color=GREY_B)
        zt = VGroup(*[Line([zx(h), ZY - 0.08, 0], [zx(h), ZY + 0.08, 0], stroke_width=2, color=GREY_B) for h in range(4)])
        zl = VGroup(*[T(f"0{h}:00", 18, GREY_B).move_to([zx(h), ZY - 0.3, 0]) for h in range(4)])
        ztitle = T("close up: the night of 13 October", 20, GREY_B).move_to([0, ZY - 0.68, 0])
        za = T("the row is about", 18, GOLD_M).move_to([zx(0), ZY + 0.42, 0]).shift(RIGHT * 0.0)
        zw = T("the row is written", 18, GOLD_M).move_to([zx(2), ZY + 0.42, 0])
        zp = VGroup(Dot([zx(1), ZY, 0], radius=0.09, color=RED_M), T("payment", 18, RED_M).move_to([zx(1), ZY + 0.42, 0]))
        frame13 = SurroundingRectangle(VGroup(rows[13], stems[13]), color=YELLOW_M, buff=0.08, stroke_width=2)
        self.steps("Take a payment at one in the morning on 13 October. The 13 October row is about midnight, which is earlier. "
                   "But it wasn't written until two. At one, it didn't exist.", [
            (lambda: [*self.uncap(), FadeIn(VGroup(zline, zt, zl)), Create(frame13), *self.set_tr("13 Oct 01:00")], 0.8),
            (lambda: [FadeIn(ztitle), FadeIn(zp)], 0.5),
            "is about midnight",
            (lambda: [FadeIn(za, shift=0.1 * DOWN)], 0.5),
            "But it wasn't",
            (lambda: [FadeIn(zw, shift=0.1 * DOWN)], 0.5),
            "At one",
            (lambda: [rows[13].animate.set_opacity(0.25), pulse(zp[1], RED_M)], 0.6),
        ])
        arc12 = arc_to(X(13, 2) - 0.15, 1.1, 12, GREEN_M, 0.8)
        ev13 = DashedLine([X(13, 1), AX_Y - 0.1, 0], [X(13, 1), 1.25, 0], dash_length=0.06, stroke_width=2.5, color=RED_M)
        self.steps("So the join skips it, and takes the 12 October row: 0.", [
                        "takes the 12",
            (lambda: [Create(arc12), Transform(rows[12], frow(12, GREEN_M))], 0.7),
            (lambda: self.set_v("0", GREEN_M), 0.4),
        ])
        corr = frow(12, PURPLE_M, y=CHIP_Y + 1.05, v=1)
        corr_l = left_at(T("12 Oct again, written 15 Oct", 18, PURPLE_M), corr.get_right()[0] + 0.15, CHIP_Y + 1.05)
        self.steps("It gets worse. On 15 October, a late chargeback report comes in, and the team works out 12 October again: now 1.", [
            (lambda: [FadeOut(VGroup(zline, zt, zl, za, zw, zp, ztitle)), FadeOut(evl), FadeOut(futl)], 0.5),
            "works out 12 October",
            (lambda: [FadeIn(corr, shift=0.1 * UP), FadeIn(corr_l)], 0.7),
        ])
        cx = tick(False, 0.14).move_to(corr.get_center() + [-0.48, 0, 0])
        self.steps("The correction is about the twelfth, but it was written on the fifteenth. Our one o'clock payment still gets 0.", [
            "about the twelfth",
            (lambda: [glow(corr[0], PURPLE_M)], 0.7),
            "written on the fifteenth",
            (lambda: [pulse(corr_l, PURPLE_M)], 0.6),
            "still gets 0",
            (lambda: [Create(cx), pulse(self.tr[2], GREEN_M)], 0.6),
        ])
        self.steps("It's a notice pinned to the board on Friday, dated Tuesday. The passenger never saw it.", [
            (lambda: self.cap("a notice pinned up on Friday, dated Tuesday", PURPLE_M), 0.6),
        ])

        # ---------------- scene 7: the rule ----------------
        self.steps("So the rule has three parts. Take the newest row that's about a time at or before the payment.", [
            (lambda: self.cap("1. about a time at or before the payment", WHITE), 0.5),
            "the newest row",
            (lambda: [glow(rows[12][0], GREEN_M)], 0.8),
        ])
        self.steps("And that was written at or before the payment, too.", [
            (lambda: [*self.cap("1. about a time at or before the payment   2. written at or before it, too", WHITE),
                      pulse(cx, RED_M)], 0.7),
        ])
        self.steps("And ignore rows older than a time limit, after which a value counts as missing.", [
            (lambda: self.cap("3. a row older than the time limit counts as missing", WHITE), 0.6),
        ])

        # ---------------- scene 8: the numbers ----------------
        res = VGroup(T("trained on the newest rows: catches 98% of fraud", 24, RED_M),
                     T("trained point in time: catches 62%", 24, GREEN_M),
                     T("live, at the till: catches 62%", 24, WHITE)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        left_at(res, -3.8, -2.45)
        self.steps("The lesson's demo runs this on a month of payments: 150,000 of them, on 5,000 cards, 2,378 of them fraud.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(arc12, cx, frame13)), Transform(rows[12], frow(12)),
                      rows[13].animate.set_opacity(1), *self.set_tr("each of 150,000 payments")], 0.7),
            "150,000",
            (lambda: self.cap("one month: 150,000 payments, 5,000 cards, 2,378 fraud"), 0.5),
        ])
        self.steps("With the newest row, every single payment got a value written after it.", [
            "every single",
            (lambda: [fut.animate(rate_func=there_and_back).set_fill(RED_M, 0.22), glow(rows[16][0], RED_M)], 0.9),
        ])
        self.steps("The rule, flag the payment if the card has had a chargeback, catches 98 percent of the fraud on that data.", [
            (lambda: [*self.uncap()], 0.3),
            "catches 98",
            (lambda: [FadeIn(res[0], shift=0.1 * UP)], 0.6),
        ])
        self.steps("On the point in time data, it catches 62. And live, at the till, 62.", [
            (lambda: [FadeIn(res[1], shift=0.1 * UP)], 0.6),
            "And live",
            (lambda: [FadeIn(res[2], shift=0.1 * UP)], 0.6),
        ])
        self.steps("That's where the difference went. It was never there.", [
            (lambda: [pulse(res[0], RED_M)], 0.8),
        ], after=0.5)

        # ---------------- scene 9: tools, and the default ----------------
        self.steps("You rarely write this join by hand. Feature stores, programs that keep features for models, like Feast, "
                   "do it for you, and DuckDB, a small database, has an ASOF JOIN.", [
            (lambda: [FadeOut(res)], 0.5),
            "Feature stores",
            (lambda: self.cap("feature stores (Feast) and DuckDB's ASOF JOIN: the lookup, done for you", WHITE), 0.6),
        ])
        self.steps("But check what time they look at. By default, Feast looks at the time a row is about. "
                   "Keeping out values written later, like our correction, is a setting you turn on.", [
            "By default",
            (lambda: self.cap("by default: the time a row is about", YELLOW_M), 0.5),
            "Keeping out",
            (lambda: [*self.cap("'written by then' is a setting you turn on", YELLOW_M), glow(corr[0], PURPLE_M)], 0.8),
        ])

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So: train only on what the model could have read at that moment. Anything written later doesn't count. "
                   "No fire engines in the training data.", [
            (lambda: [*self.cap("train only on what the model could have read at that moment", YELLOW_M, 28), *self.set_tr("10 Oct 14:00", "0", GREEN_M)], 0.6),
            "Anything written later",
            (lambda: [fut.animate(rate_func=there_and_back).set_fill(RED_M, 0.22)], 0.9),
            "No fire engines",
            (lambda: [glow(rows[10][0], GREEN_M, 1.15)], 0.8),
        ], after=0.5)
        self.steps("One quick check. A payment at half past one in the morning on 14 October. Which row does it get, and what value? "
                   "Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(corr, corr_l)), *self.set_tr("14 Oct 01:30")], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ev14 = DashedLine([X(14, 1.5), AX_Y - 0.1, 0], [X(14, 1.5), 1.25, 0], dash_length=0.06, stroke_width=2.5, color=RED_M)
        arc13 = arc_to(X(14, 2) - 0.15, 1.1, 13, GREEN_M, 0.8)
        x14 = tick(False, 0.16).move_to(rows[14].get_center() + [0, 0.5, 0])
        self.steps("The 13 October row: 1. The 14 October row is about midnight, but it isn't written until two.", [
            (lambda: [*self.uncap()], 0.3),
            (lambda: [Create(arc13), Transform(rows[13], frow(13, GREEN_M))], 0.7),
            (lambda: self.set_v("1", GREEN_M), 0.4),
            "The 14 October",
            (lambda: [Create(x14), rows[14].animate.set_opacity(0.3), *self.cap("the 14 October row: written at 02:00, not there yet", GREY_B)], 0.7),
        ], after=0.4)
        self.play(*self.cap("train only on what the model could have read at that moment", YELLOW_M, 28), run_time=0.6)
        self.wait(2.0)
