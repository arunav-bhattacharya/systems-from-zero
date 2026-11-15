from sfz import *

SAY.insert(0, (r"\b12x50\b", "twelve x fifty"))

LY, LX0, LP = 2.55, -5.55, 1.25            # main partition: row, x of pay-0, pitch
MKY = 1.82                                  # committed-offset marker
CX, CY = -4.6, 0.45                         # the consumer
IX, IY = -4.6, -1.75                        # the card issuer
SXL = -1.6                                  # left edge of the side topics
SROWS = {"10s": 0.45, "1m": -1.05, "dlt": -2.55}
AMTS = ["25.00", "8.40", "112.00", "12x50", "60.00", "19.99", "45.00", "7.50", "230.00", "14.20"]


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def lx(k):
    return LX0 + LP * k


def pay(k, x, y, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.08, width=1.15, height=0.8, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.2), 1).move_to([x, y, 0])
    amt = M(AMTS[k], 14, RED_M if k == 3 else GREY_B).move_to([x, y - 0.17, 0])
    return VGroup(r, T(f"pay-{k}", 18).move_to([x, y + 0.15, 0]), amt).set_z_index(3)


def recolor(c, color):
    return [c[0].animate.set_stroke(color).set_fill(fillc(color, 0.2), 1)]


def marker(k):
    tri = Triangle(color=GOLD_M, fill_opacity=1, stroke_width=0).scale(0.1).move_to([lx(k), MKY, 0])
    return VGroup(tri, T(f"committed {k}", 17, GOLD_M).next_to(tri, LEFT if k >= 7 else RIGHT, buff=0.1))


def sx(k):
    return SXL + 0.6 + 1.25 * k


def side(key, name, note=None):
    y = SROWS[key]
    lab = M(name, 17, RED_M if key == "dlt" else GOLD_M).move_to([SXL, y + 0.6, 0], aligned_edge=LEFT)
    g = VGroup(lab)
    if note:
        g.add(T(note, 17, GREY_B).move_to([6.2, y + 0.6, 0], aligned_edge=RIGHT))
    return g


def cstat(s, color=GREY_B):
    return T(s, 18, color).move_to([CX, CY - 0.3, 0])


def istat(s, color=GREEN_M):
    return T(s, 18, color).move_to([IX, IY - 0.2, 0])


class RetryTopics(Base):
    """msg-09, sections 0 to 2: pay-3's amount 12x50 throws every time; the consumer crashes before its commit,
    restarts at 0 and crashes again, so its partition stops (30 a second, 108,000 an hour). Classify: permanent goes to
    payments.DLT with headers, acked before the commit; transient is retried in place with backoff (100, 200 ms, capped at
    3). A one-minute issuer outage beats short waits and long ones, so the consumer writes pay-6 to 8 to
    payments.retry-10s, commits and moves on; a retry consumer pauses until each is due, then the 1-minute step, then
    the DLT."""

    def construct(self):
        self.title_card("Poison pills and retry topics", "one record that always fails, and how the partition keeps moving")

        title = T("payments topic, partition 0", 20, GREY_B).move_to([LX0 - 0.57, 3.35, 0], aligned_edge=LEFT)
        cells = [pay(k, lx(k), LY) for k in range(10)]
        cbox = RoundedRectangle(corner_radius=0.14, width=3.2, height=1.4, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        cbox.move_to([CX, CY, 0])
        ctit = T("payments consumer", 21).move_to([CX, CY + 0.28, 0])
        cst = cstat("reads in order")
        mk = marker(0)
        self.steps("pay-3 arrives with the amount 12x50. Somebody's form let a letter through, and parsing it throws, every time.", [
            (lambda: [FadeIn(title), LaggedStart(*[FadeIn(c, shift=0.1 * LEFT) for c in cells[:8]], lag_ratio=0.08)], 1.2),
            (lambda: [FadeIn(cbox), FadeIn(ctit), FadeIn(cst), FadeIn(mk)], 0.6),
            "pay-3 arrives",
            (lambda: [glow(cells[3][0], RED_M, 1.08), Indicate(cells[3][2], color=RED_M, scale_factor=1.4)], 1.0),
            "and parsing it",
            (lambda: [*recolor(cells[3], RED_M)], 0.6),
        ])

        def run(color):
            return [LaggedStart(*[AnimationGroup(*recolor(cells[k], color)) for k in range(3)], lag_ratio=0.4)]

        crash = cstat("crashed before the commit", RED_M)
        self.steps("The consumer applies pay-0 to pay-2, hits pay-3 and crashes before it commits. "
                   "It restarts at the committed offset, 0, and crashes again. Forever.", [
            (lambda: run(GREEN_M), 1.2),
            "hits pay-3",
            (lambda: [glow(cells[3][0], RED_M, 1.08), Transform(cst, crash), cbox.animate.set_stroke(RED_M)], 0.8),
            "It restarts",
            (lambda: [Transform(cst, cstat("restart at 0")), cbox.animate.set_stroke(WHITE), glow(mk[0], GOLD_M, 1.6),
                      *[c[0].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B, 0.2), 1) for c in cells[:3]]], 0.7),
            (lambda: run(YELLOW_M), 1.0),
            "and crashes again",
            (lambda: [glow(cells[3][0], RED_M, 1.08), Transform(cst, cstat("crashed again: 2 restarts", RED_M)),
                      cbox.animate.set_stroke(RED_M)], 0.8),
            "Forever",
            (lambda: [Transform(cst, cstat("crashed again: 3 restarts", RED_M))], 0.5),
        ])

        pile = chip("behind pay-3: 30 a second, 108,000 an hour", RED_M, 18).move_to([2.6, MKY, 0])
        self.steps("The bookmark can't move past pay-3, so everything behind it waits. "
                   "At 30 payments a second, that's 108,000 in an hour. A record like this is a poison pill.", [
            (lambda: [glow(mk[0], GOLD_M, 1.6)], 0.7),
            "so everything",
            (lambda: [FadeIn(cells[8], shift=0.1 * LEFT), FadeIn(cells[9], shift=0.1 * LEFT)], 0.6),
            (lambda: [*[c.animate.set_opacity(0.45) for c in cells[4:]]], 0.6),
            "At 30",
            (lambda: [FadeIn(pile, shift=0.1 * UP)], 0.7),
            "poison pill",
            (lambda: [glow(cells[3][0], RED_M, 1.08)], 0.8),
        ])

        ibox = RoundedRectangle(corner_radius=0.14, width=3.2, height=1.1, stroke_color=BLUE_M, stroke_width=2.5)
        ibox.set_fill(fillc(BLUE_M, 0.1), 1).move_to([IX, IY, 0])
        itit = T("card issuer", 21, BLUE_M).move_to([IX, IY + 0.2, 0])
        ist = istat("answering")
        call = Arrow([CX, CY - 0.78, 0], [IX, IY + 0.62, 0], buff=0, stroke_width=2.5, color=GREY_C, max_tip_length_to_length_ratio=0.15)
        tr = chip("issuer timed out: transient, retry", GOLD_M, 18).move_to([2.3, 0.75, 0])
        pm = chip("12x50: permanent, retrying never helps", RED_M, 18).move_to([2.3, -0.1, 0])
        self.steps("First ask why it failed. A timeout at the card issuer is transient: the same call can work a second later. "
                   "A bad amount is permanent: it fails the same way every time.", [
            (lambda: [FadeOut(pile), Transform(cst, cstat("why did it fail?")), cbox.animate.set_stroke(WHITE)], 0.6),
            "A timeout",
            (lambda: [FadeIn(ibox), FadeIn(itit), FadeIn(ist), GrowArrow(call)], 0.8),
            (lambda: [FadeIn(tr, shift=0.1 * UP)], 0.6),
            "A bad amount",
            (lambda: [FadeIn(pm, shift=0.1 * UP)], 0.6),
        ])

        dlt = side("dlt", "payments.DLT", "for a person to look at")
        d3 = pay(3, sx(0), SROWS["dlt"], RED_M)
        hdr = T("headers: payments, partition 0, offset 3, NumberFormatException", 16, GREY_B)
        hdr.move_to([SXL, SROWS["dlt"] - 0.62, 0], aligned_edge=LEFT)
        self.steps("pay-3 is permanent, so the consumer copies it to a dead-letter topic, with headers saying where it came from "
                   "and why. It waits for the broker's acknowledgement, then commits past it.", [
            (lambda: [FadeOut(tr), FadeOut(pm), FadeIn(dlt)], 0.7),
            (lambda: [TransformFromCopy(cells[3], d3)], 1.0),
            "with headers",
            (lambda: [FadeIn(hdr, shift=0.1 * UP)], 0.7),
            "It waits",
            (lambda: [glow(d3[0], RED_M, 1.08)], 0.7),
            "then commits",
            (lambda: [Transform(mk, marker(4)), *[c.animate.set_opacity(1) for c in cells[4:]], cells[3].animate.set_opacity(0.4),
                      *[AnimationGroup(*recolor(cells[k], GREEN_M)) for k in range(3)], Transform(cst, cstat("moving again", GREEN_M))], 0.9),
        ])

        att = [T(s, 17, c).move_to([CX + 1.75, y, 0], aligned_edge=LEFT) for s, c, y in
               (("try 1: timeout", RED_M, -0.5), ("wait 100 ms, try 2: timeout", RED_M, -0.83), ("wait 200 ms, try 3: ok", GREEN_M, -1.16))]
        self.steps("For a transient failure, retry in place a few times. pay-5's call times out, "
                   "the consumer waits 100 milliseconds, then 200, and the third attempt works.", [
            (lambda: [Transform(ist, istat("slow", GOLD_M)), *recolor(cells[4], GREEN_M)], 0.7),
            "pay-5's call",
            (lambda: [glow(cells[5][0], GOLD_M, 1.08), FadeIn(att[0])], 0.7),
            "waits 100",
            (lambda: [FadeIn(att[1])], 0.6),
            "then 200",
            (lambda: [FadeIn(att[2])], 0.6),
            (lambda: [*recolor(cells[5], GREEN_M), Transform(mk, marker(6))], 0.7),
        ])

        o1 = chip("short waits: give up in under a second", RED_M, 18).move_to([2.3, 0.75, 0])
        o2 = chip("30-second waits: partition held for the minute", RED_M, 18).move_to([2.3, -0.1, 0])
        self.steps("But if the issuer is down for a whole minute, short waits give up in under a second, "
                   "and long ones hold the partition for that minute.", [
            (lambda: [FadeOut(VGroup(*att)), Transform(ist, istat("down for a minute", RED_M)), ibox.animate.set_stroke(RED_M)], 0.8),
            "short waits",
            (lambda: [FadeIn(o1, shift=0.1 * UP), glow(cells[6][0], RED_M, 1.08)], 0.8),
            "and long ones",
            (lambda: [FadeIn(o2, shift=0.1 * UP)], 0.8),
        ])

        r10 = side("10s", "payments.retry-10s", "read by a retry consumer")
        rr = {k: pay(k, sx(k - 6), SROWS["10s"], GOLD_M) for k in (6, 7, 8)}
        self.steps("So wait somewhere else. The consumer writes pay-6 to a retry topic with a ten-second delay, "
                   "commits, and moves on at full speed.", [
            (lambda: [FadeOut(o1), FadeOut(o2), FadeIn(r10)], 0.7),
            "The consumer writes",
            (lambda: [TransformFromCopy(cells[6], rr[6]), cells[6].animate.set_opacity(0.4)], 0.9),
            "commits",
            (lambda: [Transform(mk, marker(7))], 0.5),
            "and moves on",
            (lambda: [TransformFromCopy(cells[7], rr[7]), cells[7].animate.set_opacity(0.4)], 0.5),
            (lambda: [TransformFromCopy(cells[8], rr[8]), cells[8].animate.set_opacity(0.4), Transform(mk, marker(9)),
                      Transform(cst, cstat("full speed", GREEN_M))], 0.6),
        ])

        due = T("due 10 s after it was written", 17, GOLD_M).move_to([sx(0) + 2.4, SROWS["10s"] - 0.62, 0])
        self.steps("A second consumer reads the retry topic. It pauses until each record is ten seconds old, then tries again.", [
            (lambda: [Indicate(r10[1], color=GOLD_M)], 0.8),
            "It pauses",
            (lambda: [FadeIn(due), glow(rr[6][0], GOLD_M, 1.08)], 0.9),
            "then tries again",
            (lambda: [glow(ibox, RED_M, 1.03), *recolor(rr[6], RED_M)], 0.8),
        ])

        r1m = side("1m", "payments.retry-1m")
        m6 = pay(6, sx(0), SROWS["1m"], GOLD_M)
        last = chip("the last step", RED_M, 17).move_to([sx(2) + 0.6, SROWS["dlt"], 0])
        self.steps("Still failing, pay-6 moves one step down, to a one-minute topic. By then the issuer is back, and it goes through. "
                   "The last step is the dead-letter topic.", [
            (lambda: [FadeOut(due)], 0.3),
            (lambda: [FadeIn(r1m)], 0.4),
            (lambda: [TransformFromCopy(rr[6], m6), rr[6].animate.set_opacity(0.4)], 0.9),
            "By then",
            (lambda: [Transform(ist, istat("answering again", GREEN_M)), ibox.animate.set_stroke(BLUE_M)], 0.7),
            "and it goes through",
            (lambda: [*recolor(m6, GREEN_M)], 0.6),
            "The last step",
            (lambda: [FadeIn(last, shift=0.1 * LEFT), glow(d3[0], RED_M, 1.08)], 0.8),
        ])

        self.steps("Never let one record hold a partition. Retry briefly in place, wait in retry topics, "
                   "and park what still fails in a dead-letter topic.", [
            (lambda: [glow(mk[0], GOLD_M, 1.6), *[glow(c[0], GREEN_M, 1.05) for c in cells[:3]]], 1.0),
            "Retry briefly",
            (lambda: [glow(cbox, GOLD_M, 1.03)], 0.7),
            "wait in retry",
            (lambda: [Indicate(r10[0], color=GOLD_M), Indicate(r1m[0], color=GOLD_M)], 0.8),
            "and park",
            (lambda: [Indicate(dlt[0], color=RED_M)], 0.8),
        ])
        self.wait(0.6)
