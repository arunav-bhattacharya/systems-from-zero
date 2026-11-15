from sfz import *

SAY.insert(0, (r"\b3\.0\b", "three point oh"))

PX, PY, PW, PH = -4.6, 1.1, 3.4, 2.4        # the producer
LX, LY, LW, LH = 4.2, 1.1, 3.8, 2.4         # the partition leader
REQ, ANS = PY + 0.55, PY - 0.55                      # request lane and answer lane
XL, XR = PX + PW / 2 + 0.15, LX - LW / 2 - 0.15
GY, GX0, GP = -1.8, -4.9, 1.4              # the log: row, x of offset 13, pitch
VY = -3.0                                 # verdicts


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


def gx(k):
    return GX0 + GP * (k - 13)


def cell(k, name, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.08, width=1.25, height=0.6, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.2), 1).move_to([gx(k), GY, 0])
    return VGroup(r, T(name, 19).move_to([gx(k), GY, 0]))


def empty(k):
    return DashedVMobject(RoundedRectangle(corner_radius=0.08, width=1.25, height=0.6, stroke_color=GREY_D, stroke_width=2),
                          num_dashes=24).move_to([gx(k), GY, 0])


def msg(text, color, x, y):
    t = T(text, 19)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.36, height=0.48, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.25), 1)
    return VGroup(r, t).move_to([x, y, 0]).set_z_index(4)


def req(text, color=GOLD_M):
    m = msg(text, color, 0, REQ)
    return m.move_to([XL + m.width / 2 + 0.05, REQ, 0])


def ans(text, color=GREEN_M):
    m = msg(text, color, 0, ANS)
    return m.move_to([XR - m.width / 2 - 0.05, ANS, 0])


def pline(s, y, color=GREY_B, size=19):
    return T(s, size, color).move_to([PX, y, 0])


def lline(s, y, color=GREY_B, size=19):
    return T(s, size, color).move_to([LX, y, 0])


def cross(p):
    return tick(False, 0.22).move_to(p)


class IdempotentProducer(Base):
    """msg-06, section 3: the leader appends pay-16 at offset 16 and the answer is lost; after request.timeout.ms the
    producer retries and, without idempotence, pay-16 is written again at 17. With idempotence the producer has id 5 and
    numbers records per partition: the leader writes seq 16, remembers next = 17, recognises the retry among its last
    five batches, writes nothing and answers offset 16. With five requests in flight, pay-17 times out and pay-18 arrives
    first: the leader expects 17, refuses 18 (OUT_OF_ORDER_SEQUENCE_NUMBER), and the producer resends 17, then 18."""

    def construct(self):
        self.title_card("The idempotent producer", "a lost answer, a retry, and a leader that spots it")

        pbox = RoundedRectangle(corner_radius=0.16, width=PW, height=PH, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        pbox.move_to([PX, PY, 0])
        lbox = RoundedRectangle(corner_radius=0.16, width=LW, height=LH, stroke_color=BLUE_M, stroke_width=2.5)
        lbox.set_fill(fillc(BLUE_M, 0.1), 1).move_to([LX, LY, 0])
        ptit = T("producer", 24).move_to([PX, PY + 0.82, 0])
        ltit = T("partition leader", 24, BLUE_M).move_to([LX, LY + 0.82, 0])
        rq = Arrow([XL, REQ, 0], [XR, REQ, 0], buff=0, stroke_width=2.5, color=GREY_D, max_tip_length_to_length_ratio=0.04)
        an = Arrow([XR, ANS, 0], [XL, ANS, 0], buff=0, stroke_width=2.5, color=GREY_D, max_tip_length_to_length_ratio=0.04)
        rql = T("requests", 17, GREY_C).move_to([(XL + XR) / 2, REQ + 0.52, 0])
        anl = T("answers", 17, GREY_C).move_to([(XL + XR) / 2, ANS - 0.52, 0])
        glab = T("partition 0, the log", 19, GREY_B).move_to([gx(13) - 0.62, GY + 0.62, 0], aligned_edge=LEFT)
        cells = {k: cell(k, f"pay-{k}") for k in (13, 14, 15)}
        slots = {k: empty(k) for k in range(16, 21)}
        offs = VGroup(*[M(str(k), 16, GREY_C).move_to([gx(k), GY - 0.5, 0]) for k in range(13, 21)])
        p16 = req("pay-16")
        self.steps("The payment service sends pay-16 to the partition's leader, the broker that appends it to the log.", [
            (lambda: [FadeIn(pbox), FadeIn(ptit), FadeIn(lbox), FadeIn(ltit)], 0.8),
            (lambda: [GrowArrow(rq), GrowArrow(an), FadeIn(rql), FadeIn(anl)], 0.6),
            "the broker",
            (lambda: [FadeIn(glab), *[FadeIn(c) for c in cells.values()], *[FadeIn(s) for s in slots.values()], FadeIn(offs)], 0.8),
            (lambda: [FadeIn(p16)], 0.3),
            (lambda: [p16.animate.move_to([XR - p16.width / 2 - 0.05, REQ, 0])], 1.0),
        ])

        c16 = cell(16, "pay-16")
        a16 = ans("ok: offset 16")
        x1 = cross([(XL + XR) / 2 + 0.2, ANS, 0])
        pst = pline("no answer after 30 s", PY - 0.5, RED_M)
        self.steps("The leader writes it at offset 16. But its answer is lost on the way. "
                   "After 30 seconds, the producer only knows it heard nothing.", [
            (lambda: [FadeOut(p16, scale=0.6), FadeIn(c16, shift=0.15 * DOWN), FadeOut(slots[16])], 0.8),
            "But its answer",
            (lambda: [FadeIn(a16)], 0.3),
            (lambda: [a16.animate.move_to([(XL + XR) / 2 + 0.2, ANS, 0])], 0.8),
            (lambda: [a16[0].animate.set_stroke(RED_M), FadeIn(x1)], 0.4),
            (lambda: [FadeOut(a16), FadeOut(x1)], 0.4),
            "After 30 seconds",
            (lambda: [FadeIn(pst)], 0.6),
        ])

        r16 = req("pay-16, retry")
        d17 = cell(17, "pay-16", RED_M)
        twice = chip("pay-16 is in the log twice", RED_M, 19).move_to([0, VY, 0])
        self.steps("So it retries. The leader can't tell a retry from a new record, so it writes pay-16 again, at offset 17. "
                   "Every consumer will see the payment twice.", [
            (lambda: [Transform(pst, pline("retry", PY - 0.5, GOLD_M))], 0.4),
            (lambda: [FadeIn(r16)], 0.3),
            (lambda: [r16.animate.move_to([XR - r16.width / 2 - 0.05, REQ, 0])], 1.0),
            "so it writes",
            (lambda: [FadeOut(r16, scale=0.6), FadeIn(d17, shift=0.15 * DOWN), FadeOut(slots[17])], 0.8),
            "Every consumer",
            (lambda: [FadeIn(twice, shift=0.1 * UP), glow(c16[0], RED_M, 1.08)], 0.9),
        ])

        pid = pline("producer id: 5", PY + 0.25, WHITE)
        seq = pline("next sequence: 16", PY - 0.2, GOLD_M)
        slots[16], slots[17] = empty(16), empty(17)
        self.steps("Rewind, and switch on the idempotent producer, the default since Kafka 3.0. "
                   "At start-up the producer gets an id from the broker, 5, and numbers its records for each partition.", [
            (lambda: [FadeOut(VGroup(c16, d17, twice, pst)), FadeIn(slots[16]), FadeIn(slots[17])], 0.8),
            "At start-up",
            (lambda: [FadeIn(pid, shift=0.1 * DOWN), glow(lbox, BLUE_M, 1.02)], 0.8),
            "and numbers",
            (lambda: [FadeIn(seq, shift=0.1 * DOWN)], 0.7),
        ])

        s16 = req("pay-16 · producer 5 · seq 16")
        mem = lline("producer 5: next seq 17", LY + 0.1, WHITE)
        mem2 = lline("and its last 5 batches", LY - 0.35, GREY_B, 17)
        c16 = cell(16, "pay-16", GREEN_M)
        b16 = ans("ok: offset 16")
        x2 = cross([(XL + XR) / 2 + 0.2, ANS, 0])
        self.steps("pay-16 now carries producer 5 and sequence 16. The leader writes it and remembers that producer 5 sends 17 next. "
                   "Again, the answer is lost.", [
            (lambda: [FadeIn(s16)], 0.3),
            (lambda: [s16.animate.move_to([XR - s16.width / 2 - 0.05, REQ, 0]), Transform(seq, pline("next sequence: 17", PY - 0.2, GOLD_M))], 1.0),
            "The leader writes",
            (lambda: [FadeOut(s16, scale=0.6), FadeIn(c16, shift=0.15 * DOWN), FadeOut(slots[16])], 0.7),
            "and remembers",
            (lambda: [FadeIn(mem), FadeIn(mem2)], 0.7),
            "Again",
            (lambda: [FadeIn(b16)], 0.3),
            (lambda: [b16.animate.move_to([(XL + XR) / 2 + 0.2, ANS, 0])], 0.7),
            (lambda: [b16[0].animate.set_stroke(RED_M), FadeIn(x2)], 0.3),
            (lambda: [FadeOut(b16), FadeOut(x2)], 0.3),
        ])

        t16 = req("pay-16 · producer 5 · seq 16")
        o16 = ans("ok: offset 16")
        done = pline("pay-16: done", PY - 0.65, GREEN_M)
        self.steps("The retry carries the same id and sequence. The leader finds sequence 16 among the batches it remembers, "
                   "writes nothing, and answers with offset 16 again.", [
            (lambda: [FadeIn(t16)], 0.3),
            (lambda: [t16.animate.move_to([XR - t16.width / 2 - 0.05, REQ, 0])], 1.0),
            "The leader finds",
            (lambda: [glow(lbox, GOLD_M, 1.02), Indicate(mem2, color=GOLD_M), glow(c16[0], GOLD_M, 1.1)], 1.0),
            "writes nothing",
            (lambda: [FadeOut(t16, scale=0.6)], 0.5),
            "and answers",
            (lambda: [FadeIn(o16)], 0.3),
            (lambda: [o16.animate.move_to([XL + o16.width / 2 + 0.05, ANS, 0])], 1.0),
            (lambda: [FadeOut(o16, scale=0.6), FadeIn(done)], 0.5),
        ])

        f17 = req("pay-17 · seq 17")
        f18 = req("pay-18 · seq 18")
        mid = (XL + XR) / 2
        x3 = cross([mid + 0.4, REQ, 0])
        infl = pline("up to 5 requests in flight", PY - 0.65, GREY_B)
        self.steps("Now order. The producer keeps up to five requests in flight. "
                   "pay-17's request times out, and pay-18 reaches the leader first.", [
            (lambda: [Transform(done, infl), Transform(seq, pline("next sequence: 19", PY - 0.2, GOLD_M))], 0.7),
            "pay-17's",
            (lambda: [FadeIn(f17)], 0.3),
            (lambda: [f17.animate.move_to([mid + 0.4, REQ, 0])], 0.8),
            (lambda: [FadeIn(f18), f17[0].animate.set_stroke(RED_M), FadeIn(x3)], 0.4),
            (lambda: [FadeOut(f17), FadeOut(x3)], 0.3),
            "and pay-18",
            (lambda: [f18.animate.move_to([XR - f18.width / 2 - 0.05, REQ, 0])], 1.0),
        ])

        ghost = cell(17, "pay-18", RED_M)
        refuse = lline("expects 17, got 18: refused", LY - 0.75, RED_M, 18)
        nack = ans("out of order sequence", RED_M)
        self.steps("Without idempotence, pay-18 would be written ahead of pay-17. "
                   "With idempotence, the leader expects 17, sees 18, and refuses it.", [
            (lambda: [FadeIn(ghost, shift=0.15 * DOWN)], 0.6),
            (lambda: [glow(ghost[0], RED_M, 1.08)], 0.7),
            "With idempotence, the",
            (lambda: [FadeOut(ghost), FadeOut(f18, scale=0.6), Indicate(mem, color=GOLD_M)], 0.8),
            "and refuses",
            (lambda: [FadeIn(refuse), FadeIn(nack)], 0.4),
            (lambda: [nack.animate.move_to([XL + nack.width / 2 + 0.05, ANS, 0])], 0.9),
        ])

        g17 = req("pay-17 · seq 17")
        g18 = req("pay-18 · seq 18")
        c17 = cell(17, "pay-17", GREEN_M)
        c18 = cell(18, "pay-18", GREEN_M)
        ok = chip("each record once, in send order", GREEN_M, 19).move_to([0, VY, 0])
        self.steps("The producer resends pay-17, then pay-18, and both are written once, in the order they were sent.", [
            (lambda: [FadeOut(nack, scale=0.6), FadeOut(refuse), FadeIn(g17)], 0.4),
            (lambda: [g17.animate.move_to([XR - g17.width / 2 - 0.05, REQ, 0])], 0.8),
            (lambda: [FadeOut(g17, scale=0.6), FadeIn(c17, shift=0.15 * DOWN), FadeOut(slots[17]),
                      Transform(mem, lline("producer 5: next seq 18", LY + 0.1, WHITE)), FadeIn(g18)], 0.6),
            (lambda: [g18.animate.move_to([XR - g18.width / 2 - 0.05, REQ, 0])], 0.8),
            (lambda: [FadeOut(g18, scale=0.6), FadeIn(c18, shift=0.15 * DOWN), FadeOut(slots[18]),
                      Transform(mem, lline("producer 5: next seq 19", LY + 0.1, WHITE))], 0.6),
            "both are written",
            (lambda: [FadeIn(ok, shift=0.1 * UP)], 0.6),
        ])

        again = chip("send() called twice by your code: a new record, new sequence", GREY_B, 18).move_to([0, VY, 0])
        self.steps("It only covers the producer's own retries. If your code catches a timeout and calls send again, "
                   "that's a new record with a new sequence, and it can be written twice.", [
            (lambda: [glow(pbox, WHITE, 1.02)], 0.8),
            "If your code",
            (lambda: [FadeOut(ok)], 0.4),
            (lambda: [FadeIn(again, shift=0.1 * UP)], 0.6),
        ])

        self.steps("A producer id and a sequence number let the leader spot a retry. "
                   "Then retries can't duplicate or reorder a partition.", [
            (lambda: [Indicate(pid, color=WHITE), Indicate(seq, color=GOLD_M)], 1.0),
            "spot a retry",
            (lambda: [glow(lbox, BLUE_M, 1.02), Indicate(mem, color=GOLD_M)], 0.9),
            "Then retries",
            (lambda: [*[glow(c[0], GREEN_M, 1.1) for c in (c16, c17, c18)]], 1.0),
        ])
        self.wait(0.6)
