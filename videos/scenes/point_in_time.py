from sfz import *

SAY.insert(0, (r"\bASOF JOIN\b", "as-of join"))
SAY.insert(0, (r"\bp-1\b", "P one"))
# Kokoro puts a vowel inside "chargeback" ("charge-a-back")
SAY.insert(0, (r"\bchargeback(s?)\b", r"charge back\1"))

AX_Y = 0.0                                   # the timeline
CHIP_Y = 0.75                                # feature rows above it
VALUES = {10: 0, 11: 0, 12: 0, 13: 1, 14: 1, 15: 1}
TR_Y = -1.95                                 # the training row
NOTE_Y = [-2.65, -3.2]


def X(day, hour=0.0):
    """x on the timeline for `hour` o'clock on `day` October."""
    return -5.4 + (day - 10 + hour / 24) * 1.95


XE = X(10, 14)                               # the fraud payment, 10 October 14:00


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
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def frow(day, color=None):
    """The feature row the nightly job writes at 02:00 for `day`, as of midnight."""
    v = VALUES[day]
    color = color or (GOLD_M if v else GREY_B)
    x = X(day, 2)
    r = RoundedRectangle(corner_radius=0.08, width=0.62, height=0.56, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([x, CHIP_Y, 0])
    return VGroup(r, M(str(v), 26).move_to([x, CHIP_Y, 0]), Dot([x, AX_Y, 0], radius=0.06, color=color),
                  Line([x, AX_Y + 0.08, 0], [x, CHIP_Y - 0.3, 0], stroke_width=1.5, color=GREY_D))


def note(s, color=GREY_B, k=0):
    return T(s, 22, color).move_to([0, NOTE_Y[k], 0])


class PointInTime(Base):
    """batch-14, section 1: a fraud label on card c-7, 10 October 14:00; the nightly feature (chargebacks in 30 days,
    written 02:00 as of midnight) turns 1 from 13 October because of this fraud's own chargeback. The newest-row join
    gives the label a 1 (leakage; recall 98% on paper, 62% live); the point-in-time join takes the newest row that
    existed at 14:00 on the 10th, value 0 (62% offline and live)."""

    def construct(self):
        self.title_card("Point-in-time joins", "training data that never sees the future")

        lab = left_at(M("label: payment p-1, card c-7, 10 Oct 14:00, fraud", 20), -6.3, 3.1)
        lnote = left_at(T("known only weeks later, when the chargeback came in", 20, GREY_B), -6.3, 2.62)
        self.steps("A fraud model learns from past payments. Each one is labelled fraud or not once its chargeback "
                   "arrives, weeks later.", [
            (lambda: [FadeIn(lab, shift=0.1 * DOWN)], 0.8),
            "Each one",
            (lambda: [lab[-5:].animate.set_color(RED_M)], 0.6),
            "weeks later",
            (lambda: [FadeIn(lnote)], 0.6),
        ])

        axis = Arrow([-6.3, AX_Y, 0], [6.4, AX_Y, 0], buff=0, stroke_width=2.5, color=GREY_B, max_tip_length_to_length_ratio=0.015)
        ticks = VGroup(*[Line([X(d), AX_Y - 0.1, 0], [X(d), AX_Y + 0.1, 0], stroke_width=2, color=GREY_B) for d in range(10, 17)])
        days = VGroup(*[T(f"{d} Oct", 20, GREY_B).move_to([X(d), AX_Y - 0.38, 0]) for d in range(10, 17)])
        ttl = left_at(T("feature: the card's chargebacks in the last 30 days", 22, WHITE), -6.3, 1.95)
        self.steps("It also learns from features: numbers about the card, like how many chargebacks it had in the last "
                   "30 days.", [
            (lambda: [FadeOut(lnote), Create(axis), FadeIn(ticks), FadeIn(days)], 1.0),
            "like how many",
            (lambda: [FadeIn(ttl, shift=0.1 * DOWN)], 0.7),
        ])

        rows = {d: frow(d) for d in VALUES}
        sub = left_at(T("one row a night, written at 02:00, as of midnight", 20, GREY_B), -6.3, 1.5)
        self.steps("Every night at two, a job writes one row for the card, as of midnight. For now the count is 0.", [
            (lambda: [FadeIn(sub)], 0.6),
            "a job writes",
            (lambda: [LaggedStart(*[FadeIn(rows[d], shift=0.1 * DOWN) for d in (10, 11, 12)], lag_ratio=0.3)], 1.2),
            "For now",
            (lambda: [*[glow(rows[d][0], GREY_B, 1.1) for d in (10, 11, 12)]], 0.8),
        ])

        ev = DashedLine([XE, AX_Y - 0.12, 0], [XE, 1.25, 0], dash_length=0.08, stroke_width=3, color=RED_M)
        evl = T("payment p-1, 14:00", 20, RED_M).move_to([XE, 1.5, 0])
        cb = Triangle(color=RED_M, fill_opacity=1).scale(0.1).move_to([X(12, 12), AX_Y + 0.02, 0])
        cbl = T("its chargeback arrives", 20, RED_M).move_to([X(12, 12), AX_Y - 0.85, 0])
        self.steps("On 10 October at two in the afternoon, the card is used for fraud. Its chargeback arrives on the "
                   "twelfth, so from the thirteenth on, the count is 1.", [
            (lambda: [FadeOut(sub), Create(ev), FadeIn(evl)], 0.8),
            "Its chargeback",
            (lambda: [FadeIn(cb, scale=0.5), FadeIn(cbl, shift=0.1 * UP)], 0.7),
            "so from the thirteenth",
            (lambda: [LaggedStart(*[FadeIn(rows[d], shift=0.1 * DOWN) for d in (13, 14, 15)], lag_ratio=0.3)], 1.1),
        ])

        trl = left_at(T("training row:", 22, GREY_B), -6.3, TR_Y)
        tr = left_at(M("p-1 | chargebacks_30d:", 20), trl.get_right()[0] + 0.25, TR_Y)
        cell = left_at(M("?", 22, GREY_B), tr.get_right()[0] + 0.2, TR_Y)
        tr2 = left_at(M("| fraud", 20), cell.get_right()[0] + 0.45, TR_Y)
        arc = ArcBetweenPoints([XE + 0.05, 1.05, 0], [X(15, 2) - 0.1, CHIP_Y + 0.33, 0], angle=-0.42, color=RED_M,
                               stroke_width=3).add_tip(tip_length=0.18)
        arcl = T("the card's newest row", 20, RED_M).move_to([X(13, 2), 1.95, 0])
        self.steps("The easy join takes the card's newest row: 1. That 1 is the chargeback this very fraud caused.", [
            (lambda: [FadeIn(trl), FadeIn(tr), FadeIn(cell), FadeIn(tr2), FadeOut(ttl)], 0.7),
            "takes the card's",
            (lambda: [Create(arc), FadeIn(arcl), glow(rows[15][0], RED_M, 1.12)], 0.9),
            (lambda: [Transform(cell, left_at(M("1", 22, RED_M), cell.get_left()[0], TR_Y))], 0.6),
            "That 1",
            (lambda: [glow(rows[13][0], RED_M, 1.12), cb.animate(rate_func=there_and_back).scale(2)], 0.9),
        ])

        fut = Rectangle(width=6.4 - XE - 0.02, height=1.4, stroke_width=0).set_fill(RED_M, 0.10)
        fut.move_to([(XE + 6.4) / 2, 0.45, 0])
        futl = T("written after the payment", 20, RED_M).move_to([3.3, -0.85, 0])
        leak = note("label leakage: the future reaches the training data", RED_M)
        self.steps("The model learns that fraud comes with a chargeback already on file, which it can never see when it "
                   "decides. This is label leakage: the future reaching the training data.", [
            (lambda: [FadeOut(arcl), FadeIn(fut), FadeIn(futl)], 0.9),
            "This is label",
            (lambda: [FadeIn(leak, shift=0.1 * UP)], 0.8),
        ])

        r98 = note("newest-row join: the rule catches 98% of fraud on paper", RED_M)
        r62 = note("in production it catches 62%", WHITE, 1)
        self.steps("Across 150,000 labels, every one got a value from after its payment. On that data, the rule "
                   "\"flag a card with a chargeback\" catches 98 percent of fraud. Live, it catches 62.", [
            (lambda: [FadeOut(leak)], 0.4),
            "On that data",
            (lambda: [FadeIn(r98, shift=0.1 * UP)], 0.8),
            "Live",
            (lambda: [FadeIn(r62, shift=0.1 * UP)], 0.7),
        ])

        back = ArcBetweenPoints([XE - 0.05, 1.0, 0], [X(10, 2), CHIP_Y + 0.34, 0], angle=1.6, color=GREEN_M,
                                stroke_width=3).add_tip(tip_length=0.16)
        self.steps("A point in time join looks back from each label instead. It takes the newest row that already "
                   "existed when the payment happened.", [
            (lambda: [FadeOut(arc), FadeOut(r98), FadeOut(r62), Transform(cell, left_at(M("?", 22, GREY_B), cell.get_left()[0], TR_Y)),
                      *[rows[d].animate.set_opacity(0.3) for d in (11, 12, 13, 14, 15)]], 0.9),
            "It takes the newest",
            (lambda: [Create(back)], 0.8),
            (lambda: [Transform(rows[10], frow(10, GREEN_M))], 0.6),
        ])

        self.steps("For this payment, that's the 10 October row: 0. Exactly what the model could have read at that moment.", [
            (lambda: [glow(rows[10][0], GREEN_M, 1.15)], 0.8),
            (lambda: [Transform(cell, left_at(M("0", 22, GREEN_M), cell.get_left()[0], TR_Y))], 0.6),
            "Exactly what",
            (lambda: [ev.animate(rate_func=there_and_back).set_stroke(width=6)], 0.9),
        ])

        p62 = note("point-in-time join: 62% offline, and 62% in production", GREEN_M)
        tools = note("DuckDB's ASOF JOIN and feature stores like Feast do this lookup", GREY_B, 1)
        self.steps("Trained on these rows, the same rule catches 62 percent, which is what production gets. Feature "
                   "stores like Feast, and DuckDB's ASOF JOIN, do this lookup for you.", [
            (lambda: [FadeIn(p62, shift=0.1 * UP)], 0.8),
            "Feature",
            (lambda: [FadeIn(tools, shift=0.1 * UP)], 0.8),
        ])

        self.steps("Join each label to its features as they were at that moment, never as they are now.", [
            (lambda: [FadeOut(tools), glow(rows[10][0], GREEN_M, 1.15), back.animate(rate_func=there_and_back).set_stroke(width=6)], 1.0),
            "never as they are now",
            (lambda: [fut.animate(rate_func=there_and_back).set_fill(RED_M, 0.25)], 1.0),
        ])
        self.wait(0.6)
