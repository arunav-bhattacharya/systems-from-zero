from sfz import *

# a capital A naming a reader is read as the article "uh"
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\b([Rr])eader A\b", r"\1eader eh"))
SAY.insert(0, (r"\bR([123])\b", r"R \1"))

W_C, RD_C = GOLD_M, BLUE_M
X0, X1 = -3.9, 5.7                  # the time axis, left and right ends
LX = -4.35                          # row labels end here
RY1 = {"capture": 1.75, "ledger": 0.85, "fraud": -0.05, "email": -0.95}
AX1 = -1.85                         # part 1 axis (0 to 60 ms)
RY2 = [2.4, 1.5, 0.6, -0.3, -1.2, -2.1]
AX2 = -2.8                          # part 2 axis (0 to 90 ms)
BH = 0.6                            # bar height
REG = np.array([0, 2.95, 0])


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


def tx(ms, span):
    return X0 + (X1 - X0) * ms / span


def seg(t0, t1, y, span, color, label="", lcol=WHITE, size=20, fill=0.16):
    """One bar on the timeline, from t0 to t1 ms, with its label in the middle."""
    w = tx(t1, span) - tx(t0, span)
    r = RoundedRectangle(corner_radius=min(0.1, w / 2.01), width=w, height=BH, stroke_color=color, stroke_width=2.5)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), fill), opacity=1)
    r.move_to([(tx(t0, span) + tx(t1, span)) / 2, y, 0])
    t = T(label, size, lcol).move_to(r.get_center()) if label else VMobject()
    return VGroup(r, t)


def rlabel(s, y, color=GREY_B):
    t = T(s, 24, color)
    return t.move_to([LX - t.width / 2, y, 0])


def axis(span, y, step):
    line = Line([X0, y, 0], [X1, y, 0], stroke_width=2, color=GREY_B)
    ticks = VGroup(*[Line([tx(m, span), y - 0.07, 0], [tx(m, span), y + 0.07, 0], stroke_width=2, color=GREY_B)
                     for m in range(0, span + 1, step)])
    nums = VGroup(*[M(str(m), 18, GREY_B).move_to([tx(m, span), y - 0.3, 0]) for m in range(0, span + 1, step)])
    unit = T("ms", 20, GREY_B).move_to([X1 + 0.5, y - 0.3, 0])
    return VGroup(line, ticks, nums, unit)


def register(value, color=WHITE):
    r = RoundedRectangle(corner_radius=0.12, width=4.4, height=0.75, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to(REG)
    k = T("status", 24, GREY_B).move_to(REG + LEFT * 1.25)
    v = T(value, 28, color).move_to(REG + RIGHT * 0.55)
    return VGroup(r, k, v)


def point(ms, y, span, color=YELLOW_M):
    """A linearization point: a dot on the bar's lower edge."""
    return Dot([tx(ms, span), y - BH / 2, 0], radius=0.085, color=color)


def replica(y, switch, span=90):
    """A replica's value over time: 8 until `switch` ms, then 9."""
    if switch >= span:
        return VGroup(seg(0, span, y, span, GREY_B, "8", GREY_B, 22, 0.08), seg(span - 0.5, span, y, span, W_C, "9", WHITE, 22).set_opacity(0))
    a = seg(0, switch, y, span, GREY_B, "8", GREY_B, 22, 0.08)
    b = seg(switch, span, y, span, W_C, "9", WHITE, 22)
    return VGroup(a, b)


class Linearizability(Base):
    """cons-02: the stepper's register history (a 60 ms capture write, reads by ledger, fraud and email), placing
    linearization points, the stale read that breaks it, then the lesson's quorum race (w = 2, r = 2) and ABD's fix."""

    def construct(self):
        self.title_card("Linearizability", "one copy, one timeline")

        reg = register("authorized", GREY_B)
        self.steps("A payment's status is one value that several services read and write. It says authorized.", [
            (lambda: [FadeIn(reg, shift=0.15 * DOWN)], 1.0),
        ])

        ax = axis(60, AX1, 10)
        lab = {k: rlabel(k, y) for k, y in RY1.items()}
        wbar = seg(0, 60, RY1["capture"], 60, W_C, "write captured")
        self.steps("The capture service writes captured. That takes 60 milliseconds, drawn here as a bar on a timeline.", [
            (lambda: [FadeIn(lab["capture"])], 0.6),
            "That takes",
            (lambda: [Create(ax[0]), FadeIn(ax[1:])], 1.0),
            "drawn here",
            (lambda: [GrowFromEdge(wbar, LEFT)], 1.2),
        ])

        led = seg(5, 15, RY1["ledger"], 60, RD_C)
        led_v = T("authorized", 20, GREY_B).move_to(led[0])
        fr = seg(20, 30, RY1["fraud"], 60, RD_C)
        fr_v = T("captured", 20).move_to(fr[0])
        self.steps("Meanwhile, ledger reads from 5 to 15 milliseconds and gets authorized. Fraud reads from 20 to 30 and gets captured.", [
            (lambda: [FadeIn(lab["ledger"]), GrowFromEdge(led, LEFT)], 0.8),
            "and gets authorized",
            (lambda: [FadeIn(led_v)], 0.5),
            "Fraud reads",
            (lambda: [FadeIn(lab["fraud"]), GrowFromEdge(fr, LEFT)], 0.8),
            "and gets captured",
            (lambda: [FadeIn(fr_v)], 0.5),
        ])

        ask = T("pick one instant inside each bar where it took effect", 22, YELLOW_M).move_to([0.6, -2.85, 0])
        self.steps("Is that allowed? Linearizability says yes, if you can pick one instant inside each bar where the operation took effect.", [
            "Linearizability",
            (lambda: [FadeIn(ask, shift=0.15 * UP)], 0.8),
            "inside each bar",
            (lambda: [flash(wbar), flash(led), flash(fr)], 1.0),
        ])

        p_led, p_w, p_fr = point(10, RY1["ledger"], 60), point(18, RY1["capture"], 60), point(25, RY1["fraud"], 60)
        clock = ValueTracker(0)
        cur = always_redraw(lambda: Triangle(fill_color=YELLOW_M, fill_opacity=1, stroke_width=0).scale(0.11).rotate(PI)
                            .move_to([tx(clock.get_value(), 60), AX1 + 0.2, 0]))
        replay = T("replay on one copy", 22, YELLOW_M).move_to([0.6, -2.85, 0])
        self.steps("Ledger at 10, the write at 18, fraud at 25. Replayed in that order on one copy, each read gets the answer it got.", [
            (lambda: [FadeIn(p_led, scale=0.5)], 0.5),
            "the write at 18",
            (lambda: [FadeIn(p_w, scale=0.5)], 0.5),
            "fraud at 25",
            (lambda: [FadeIn(p_fr, scale=0.5)], 0.5),
            "Replayed",
            (lambda: [FadeIn(cur), ReplacementTransform(ask, replay)], 0.5),
            (lambda: [clock.animate(rate_func=linear).set_value(10)], 0.6),
            (lambda: [Indicate(led_v, color=GREEN_M), Indicate(reg[2], color=GREEN_M), led[0].animate.set_stroke(GREEN_M)], 0.8),
            (lambda: [clock.animate(rate_func=linear).set_value(18)], 0.5),
            (lambda: [Transform(reg, register("captured", WHITE))], 0.6),
            (lambda: [clock.animate(rate_func=linear).set_value(25)], 0.5),
            (lambda: [Indicate(fr_v, color=GREEN_M), Indicate(reg[2], color=GREEN_M), fr[0].animate.set_stroke(GREEN_M)], 0.8),
        ])

        em = seg(40, 50, RY1["email"], 60, RD_C)
        em_v = T("authorized", 20, GREY_B).move_to(em[0])
        self.steps("Then email reads from 40 to 50, and gets authorized.", [
            (lambda: [FadeIn(lab["email"]), GrowFromEdge(em, LEFT)], 0.8),
            "and gets",
            (lambda: [FadeIn(em_v)], 0.5),
        ])

        p_em = point(45, RY1["email"], 60, RED_M)
        no = tick(False, 0.22).move_to([tx(53.5, 60), RY1["email"], 0])
        self.steps("Its instant must be after 40, when fraud has already seen captured. One copy would say captured. No choice works.", [
            (lambda: [clock.animate(rate_func=linear).set_value(45), FadeIn(p_em, scale=0.5)], 1.0),
            "when fraud",
            (lambda: [Indicate(fr_v, color=YELLOW_M)], 0.9),
            "One copy",
            (lambda: [Indicate(reg[2], color=YELLOW_M)], 0.9),
            "No choice",
            (lambda: [Create(no), em[0].animate.set_stroke(RED_M), em_v.animate.set_color(RED_M)], 0.8),
        ])

        rule = T("once a read has seen the new value, every read that starts later must too", 22, WHITE).move_to([0.4, -2.85, 0])
        fit(rule, 12.4)
        self.steps("That history isn't linearizable. Once any read has returned the new value, every read that starts later must return it too.", [
            (lambda: [FadeOut(cur), FadeOut(replay)], 0.5),
            "Once any read",
            (lambda: [FadeIn(rule, shift=0.15 * UP)], 0.9),
            "every read that starts later",
            (lambda: [flash(em, RED_M, 1.06)], 1.0),
        ])

        # ---- a quorum store -----------------------------------------------------------------------------------
        part1 = VGroup(wbar, led, led_v, fr, fr_v, em, em_v, p_led, p_w, p_fr, p_em, no, rule, *lab.values())
        ax2 = axis(90, AX2, 10)
        names = ["writer", "R1", "R2", "R3", "reader A", "reader B"]
        lab2 = [rlabel(n, y) for n, y in zip(names, RY2)]
        reps = [replica(RY2[i + 1], 90) for i in range(3)]
        rule2 = T("every write and every read waits for 2 of the 3 copies", 22, GREY_B).move_to([0.6, 3.2, 0])
        self.steps("Now a store with three copies, each holding 8. Every write and every read waits for two of the three.", [
            (lambda: [FadeOut(part1), FadeOut(reg)], 0.8),
            (lambda: [ReplacementTransform(ax[0], ax2[0]), FadeOut(ax[1:]), FadeIn(ax2[1:])], 0.8),
            "three copies",
            (lambda: [*[FadeIn(lab2[i + 1]) for i in range(3)], *[GrowFromEdge(reps[i][0], LEFT) for i in range(3)]], 1.0),
            (lambda: [*[FadeIn(reps[i][1]) for i in range(3)]], 0.05),
            "Every write",
            (lambda: [FadeIn(rule2, shift=0.15 * DOWN)], 0.8),
        ])

        wr = seg(0, 90, RY2[0], 90, W_C, "write 9, waiting for 2 of 3 to confirm")
        self.steps("A writer sends 9. It reaches R1 at 10 milliseconds, but R2 and R3 only at 70 and 75. Until then, the write isn't finished.", [
            (lambda: [FadeIn(lab2[0]), GrowFromEdge(wr, LEFT)], 1.0),
            "It reaches R1",
            (lambda: [Transform(reps[0], replica(RY2[1], 10))], 0.8),
            "R2 and R3",
            (lambda: [Transform(reps[1], replica(RY2[2], 70)), Transform(reps[2], replica(RY2[3], 75))], 0.9),
            "Until then",
            (lambda: [flash(wr)], 1.0),
        ])

        ra = seg(20, 40, RY2[4], 90, RD_C)
        ra_v = T("returns 9", 20).move_to(ra[0])
        da = [point(30, RY2[1], 90, GREEN_M), point(30, RY2[2], 90, GREEN_M)]
        self.steps("Reader A asks from 20 to 40 milliseconds. R1 and R2 answer first, with 9 and 8. It returns the newer one, 9.", [
            (lambda: [FadeIn(lab2[4]), GrowFromEdge(ra, LEFT)], 0.9),
            "R1 and R2",
            (lambda: [FadeIn(da[0], scale=0.5), FadeIn(da[1], scale=0.5)], 0.6),
            "with 9 and 8",
            (lambda: [Indicate(reps[0][1][1], color=GREEN_M), Indicate(reps[1][0][1], color=GREEN_M)], 0.9),
            "It returns",
            (lambda: [FadeIn(ra_v), ra[0].animate.set_stroke(GREEN_M)], 0.6),
        ])

        rb = seg(48, 68, RY2[5], 90, RD_C)
        rb_v = T("returns 8", 20).move_to(rb[0])
        db = [point(58, RY2[2], 90, RED_M), point(58, RY2[3], 90, RED_M)]
        self.steps("Reader B starts at 48, after A has finished. R2 and R3 answer first, both still 8. B returns 8.", [
            (lambda: [FadeIn(lab2[5]), GrowFromEdge(rb, LEFT)], 0.9),
            "R2 and R3",
            (lambda: [FadeIn(db[0], scale=0.5), FadeIn(db[1], scale=0.5)], 0.6),
            "both still 8",
            (lambda: [Indicate(reps[1][0][1], color=RED_M), Indicate(reps[2][0][1], color=RED_M)], 0.9),
            "B returns",
            (lambda: [FadeIn(rb_v), rb[0].animate.set_stroke(RED_M), rb_v.animate.set_color(RED_M)], 0.6),
        ])

        gap = DashedLine([tx(40, 90), RY2[4] - BH / 2, 0], [tx(40, 90), RY2[5] - BH / 2, 0], dash_length=0.06,
                         stroke_width=2.5, color=YELLOW_M)
        back = T("went back in time", 20, RED_M)
        back.move_to([tx(68, 90) + 0.35 + back.width / 2, RY2[5], 0])
        rule3 = T("2 of 3 overlap, but only for writes that have finished", 22, GREY_B).move_to([0.6, 3.2, 0])
        self.steps("B started after A finished, yet saw an older value. Two of three overlap only for writes that have finished.", [
            (lambda: [Create(gap)], 0.7),
            "yet saw",
            (lambda: [FadeIn(back)], 0.7),
            "Two of three",
            (lambda: [ReplacementTransform(rule2, rule3)], 0.8),
            "that have finished",
            (lambda: [flash(wr, RED_M)], 1.0),
        ])

        ra2 = seg(20, 60, RY2[4], 90, GREEN_M, "reads 9, writes it back")
        rb2v = T("returns 9", 20).move_to(rb[0])
        db2 = [point(58, RY2[2], 90, GREEN_M), point(58, RY2[3], 90, GREEN_M)]
        rule4 = T("fix: a read writes what it saw back to 2 of 3 before it answers", 22, GREEN_M).move_to([0.6, 3.2, 0])
        self.steps("The fix: before reader A answers, it writes 9 back to two replicas. Every later read then finds it, at the price of a second round trip.", [
            (lambda: [FadeOut(gap), FadeOut(back), ReplacementTransform(rule3, rule4)], 0.8),
            "before reader A",
            (lambda: [ReplacementTransform(ra, ra2), FadeOut(ra_v)], 1.0),
            "it writes 9 back",
            (lambda: [Transform(reps[1], replica(RY2[2], 50)), Transform(reps[2], replica(RY2[3], 50))], 0.9),
            "Every later read",
            (lambda: [Transform(db[0], db2[0]), Transform(db[1], db2[1]), Transform(rb_v, rb2v), rb[0].animate.set_stroke(GREEN_M)], 0.9),
            "a second round trip",
            (lambda: [flash(ra2, GREEN_M, 1.04)], 1.0),
        ])

        self.steps("Linearizable means one copy, one timeline. Once anyone has seen a value, nobody who asks later sees an older one.", [
            "Once anyone",
            (lambda: [Indicate(ra2[1], color=GREEN_M)], 1.0),
            "nobody who asks later",
            (lambda: [Indicate(rb_v, color=GREEN_M)], 1.0),
        ])
        self.wait(0.6)


def flash(m, color=YELLOW_M, s=1.04):
    """Pulse a bar and recolour its outline, so its label stays readable."""
    return m[0].animate(rate_func=there_and_back).scale(s).set_stroke(color=color)
