from sfz import *

# The letter A naming a consumer: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))

QY = 2.0                                   # the queue's row
QL, QR = -6.6, 0.5                         # the queue's box, left and right
SP = 1.4
SLOT = [-0.25 - SP * j for j in range(5)]  # slot 0 is the head, at the right
CX, AY, BY = 4.6, 2.55, 0.65               # consumers A and B
HX = 2.1                                   # where a consumer's held message sits
LY = -2.4                                  # the ledger's row
LX = [-5.5 + 1.42 * j for j in range(5)]
A_C, B_C = TEAL_M, PURPLE_M
KIND = {"auth": BLUE_M, "capture": GREEN_M, "refund": GOLD_M}
MSGS = [("m1", "auth 40"), ("m2", "capture 40"), ("m3", "auth 25"), ("m4", "capture 25"), ("m5", "refund 10")]


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn, so it can sit inside a Succession."""
    d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_opacity(0)
    line = Line(path.get_start(), path.get_end())
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def msg(i, stroke=None):
    name, what = MSGS[i]
    c = KIND[what.split()[0]]
    r = RoundedRectangle(corner_radius=0.1, width=1.3, height=0.78, stroke_color=stroke or c, stroke_width=2.5).set_fill(fill(c, 0.22), 1)
    return VGroup(r, M(name, 20).move_to([0, 0.15, 0]), T(what, 15, GREY_A).move_to([0, -0.17, 0]))


def slot_status(j, s, color=GREY_B):
    return T(s, 16, color).move_to([SLOT[j], QY - 0.5, 0])


def consumer(name, y, color):
    r = RoundedRectangle(corner_radius=0.14, width=3.0, height=1.1, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to([CX, y, 0])
    return VGroup(r, T(name, 24).move_to([CX, y + 0.22, 0]), T("idle", 18, GREY_B).move_to([CX, y - 0.2, 0]))


def c_status(y, s, color=GREY_B):
    return T(s, 18, color).move_to([CX, y - 0.2, 0])


def box(label, sub, x, y, color, w=2.6, h=0.95, size=24):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to([x, y, 0])
    if not sub:
        return VGroup(r, T(label, size).move_to([x, y, 0]))
    return VGroup(r, T(label, size).move_to([x, y + 0.18, 0]), T(sub, 17, GREY_B).move_to([x, y - 0.2, 0]))


class QueueRedelivery(Base):
    """msg-01, section 2: five events of acct-17 in one queue, two competing consumers with prefetch 1, manual acks.
    B crashes holding m3; m3 goes back to the head but m4 has left, so the ledger books m1 m2 m4 m3 m5. Then prefetch,
    one consumer per queue, and fan-out through an exchange to one queue per service."""

    def construct(self):
        self.title_card("Acks and redelivery", "and the reordering they cause")

        qbox = RoundedRectangle(corner_radius=0.16, width=QR - QL, height=1.5, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        qbox.move_to([(QL + QR) / 2, QY, 0])
        qlab = T("queue on the broker, account acct-17", 22, GREY_B)
        qlab.move_to([QL + qlab.width / 2 + 0.05, QY + 1.05, 0])
        head = T("head", 18, GREY_C).move_to([SLOT[0], QY + 1.05, 0])
        q = [msg(i).move_to([SLOT[i], QY + 0.12, 0]) for i in range(5)]
        st = [slot_status(i, "ready") for i in range(5)]
        self.steps("A broker holds messages in a queue until a consumer takes them. "
                   "Five payment events for account 17 wait here, in the order they were published.", [
            (lambda: [FadeIn(qbox), FadeIn(qlab)], 0.8),
            "Five payment",
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.3 * RIGHT) for m in reversed(q)], lag_ratio=0.2), FadeIn(head)], 1.4),
            (lambda: [*[FadeIn(s) for s in st]], 0.5),
        ])

        ca, cb = consumer("consumer A", AY, A_C), consumer("consumer B", BY, B_C)
        self.steps("The ledger service runs two copies, A and B, on this one queue. "
                   "The broker gives each message to only one of them.", [
            (lambda: [FadeIn(ca, shift=0.2 * LEFT), FadeIn(cb, shift=0.2 * LEFT)], 0.9),
        ])

        pre = chip("prefetch 1: at most one unfinished message each", GREY_B, 20).move_to([CX - 1.0, -0.55, 0])
        pre.move_to([CX + 1.5 - pre.width / 2, -0.55, 0])
        self.steps("Each may hold one unfinished message at a time. That cap is called the prefetch.", [
            (lambda: [Transform(ca[2], c_status(AY, "prefetch 1, idle")), Transform(cb[2], c_status(BY, "prefetch 1, idle"))], 0.8),
            "That cap",
            (lambda: [FadeIn(pre, shift=0.15 * UP)], 0.8),
        ])

        lbox = RoundedRectangle(corner_radius=0.16, width=12.6, height=1.5, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        lbox.move_to([-0.1, LY, 0])
        llab = T("the ledger books, in this order:", 20, GREY_B)
        llab.move_to([-6.2 + llab.width / 2, LY + 0.48, 0])
        ackn = chip("ack: the work is done, delete it", GREEN_M, 20).move_to(pre)
        ackn.move_to([CX + 1.5 - ackn.width / 2, -0.55, 0])
        self.steps("The broker doesn't delete a message when it sends it, because the consumer might crash halfway. "
                   "It waits for an acknowledgement that the work is done.", [
            (lambda: [FadeIn(lbox), FadeIn(llab)], 0.8),
            "It waits",
            (lambda: [FadeTransform(pre, ackn)], 0.8),
        ])

        h1, h2 = q[0].copy(), q[1].copy()
        acks = [chip("ack", GREEN_M, 18, mono=True).move_to([HX, y, 0]) for y in (AY, BY)]
        self.steps("m1 goes to A and m2 to B. Each books its payment and acknowledges it, and the broker deletes the message.", [
            (lambda: [h1.animate.move_to([HX, AY, 0]), h2.animate.move_to([HX, BY, 0]),
                      q[0].animate.set_opacity(0.3), q[1].animate.set_opacity(0.3),
                      Transform(st[0], slot_status(0, "unacked, A")), Transform(st[1], slot_status(1, "unacked, B")),
                      Transform(ca[2], c_status(AY, "booking m1")), Transform(cb[2], c_status(BY, "booking m2"))], 1.0),
            "Each books",
            (lambda: [h1.animate.move_to([LX[0], LY - 0.15, 0]), h2.animate.move_to([LX[1], LY - 0.15, 0])], 1.0),
            "and acknowledges",
            (lambda: [FadeIn(acks[0]), FadeIn(acks[1])], 0.3),
            (lambda: [acks[0].animate.move_to([QR + 0.5, QY + 0.3, 0]), acks[1].animate.move_to([QR + 0.5, QY - 0.3, 0])], 0.8),
            "and the broker deletes",
            (lambda: [FadeOut(acks[0]), FadeOut(acks[1]), FadeOut(q[0]), FadeOut(q[1]), FadeOut(st[0]), FadeOut(st[1]),
                      Transform(ca[2], c_status(AY, "prefetch 1, idle")), Transform(cb[2], c_status(BY, "prefetch 1, idle"))], 0.7),
        ])

        h3, h4 = q[2].copy().move_to([SLOT[0], QY + 0.12, 0]), q[3].copy().move_to([SLOT[1], QY + 0.12, 0])
        self.steps("Next, B takes m3, an authorization for 25, and A takes m4, its capture. "
                   "Both are unacknowledged: sent, but still reserved in the queue.", [
            (lambda: [*[m.animate.shift(2 * SP * RIGHT) for m in q[2:]], *[s.animate.shift(2 * SP * RIGHT) for s in st[2:]],
                      FadeOut(ackn)], 0.8),
            (lambda: [FadeIn(h3), FadeIn(h4)], 0.05),
            (lambda: [h3.animate.move_to([HX, BY, 0]), q[2].animate.set_opacity(0.3), Transform(st[2], slot_status(0, "unacked, B")),
                      Transform(cb[2], c_status(BY, "booking m3"))], 0.9),
            "and A takes",
            (lambda: [h4.animate.move_to([HX, AY, 0]), q[3].animate.set_opacity(0.3), Transform(st[3], slot_status(1, "unacked, A")),
                      Transform(ca[2], c_status(AY, "booking m4"))], 0.9),
            "Both are",
            (lambda: [Indicate(st[2], color=YELLOW_M), Indicate(st[3], color=YELLOW_M)], 1.0),
        ])

        cross = tick(False, 0.17).move_to([CX + 1.22, BY, 0])
        self.steps("B crashes before it acknowledges m3. The broker puts m3 back at the head of the queue.", [
            (lambda: [cb[0].animate.set_stroke(RED_M), Transform(cb[2], c_status(BY, "crashed", RED_M)), Create(cross)], 0.8),
            "The broker puts",
            (lambda: [h3.animate.move_to(q[2])], 1.0),
            (lambda: [FadeOut(h3), q[2].animate.set_opacity(1), Transform(st[2], slot_status(0, "ready again"))], 0.5),
        ])

        bad = T("a capture before its authorization", 20, RED_M).move_to([3.4, LY - 0.15, 0])
        self.steps("But m4 has already left it. Consumer A books the capture of 25, for an authorization the ledger has never seen.", [
            (lambda: [Indicate(st[3], color=RED_M)], 0.9),
            "Consumer A books",
            (lambda: [h4.animate.move_to([LX[2], LY - 0.15, 0])], 1.0),
            (lambda: [h4[0].animate.set_stroke(RED_M, width=4), FadeIn(bad), FadeOut(q[3]), FadeOut(st[3]),
                      Transform(ca[2], c_status(AY, "prefetch 1, idle"))], 0.8),
        ])

        h3b, h5 = q[2].copy(), q[4].copy()
        self.steps("Then A gets m3, marked as redelivered, and books it. m5 follows.", [
            (lambda: [h3b.animate.move_to([HX, AY, 0]), q[2].animate.set_opacity(0.3), Transform(st[2], slot_status(0, "unacked, A")),
                      Transform(ca[2], c_status(AY, "m3, redelivered", GOLD_M))], 1.0),
            "and books it",
            (lambda: [h3b.animate.move_to([LX[3], LY - 0.15, 0]), FadeOut(q[2]), FadeOut(st[2])], 1.0),
            "m5 follows",
            (lambda: [h5.animate.move_to([LX[4], LY - 0.15, 0]), FadeOut(q[4]), FadeOut(st[4]),
                      Transform(ca[2], c_status(AY, "prefetch 1, idle"))], 1.0),
        ])

        self.steps("Nothing was lost, and nothing was booked twice. The queue kept its order, yet the ledger saw m4 before m3.", [
            (lambda: [cb[0].animate.set_stroke(B_C), Transform(cb[2], c_status(BY, "back, idle")), FadeOut(cross)], 0.8),
            "The queue kept",
            (lambda: [glow(qbox, GREY_B, 1.01)], 0.9),
            "yet the ledger",
            (lambda: [glow(h4[0], RED_M, 1.1), glow(h3b[0], GOLD_M, 1.1)], 1.0),
        ])

        big = chip("prefetch 100: more come back, more get overtaken", RED_M, 20)
        big.move_to([CX + 1.5 - big.width / 2, -0.55, 0])
        self.steps("A bigger prefetch makes this worse: more messages come back after a crash, and more get overtaken.", [
            (lambda: [Transform(ca[2], c_status(AY, "prefetch 100")), Transform(cb[2], c_status(BY, "prefetch 100"))], 0.8),
            "more messages",
            (lambda: [FadeIn(big, shift=0.15 * UP)], 0.8),
        ])

        one = chip("one consumer per queue: order kept, one machine works", GREY_B, 20)
        one.move_to([CX + 1.5 - one.width / 2, -0.55, 0])
        self.steps("One consumer per queue keeps the order, but then only one machine does the work.", [
            (lambda: [FadeTransform(big, one), cb.animate.set_opacity(0.3), Transform(ca[2], c_status(AY, "the only consumer"))], 1.0),
        ])

        # ---- fan-out ------------------------------------------------------------------------------------------------
        QX = 1.3
        prod = box("payment service", None, -5.3, 0.0, WHITE, w=2.5, size=22)
        prod[0].set_fill(BLACK, 1)
        exch = box("exchange", "stores nothing", -2.2, 0.0, GOLD_M, w=2.3)
        qs = [box(n, None, QX, y, GREY_B, w=2.9, h=0.8, size=22) for n, y in
              (("ledger queue", 2.0), ("fraud check queue", 0.0), ("notifications queue", -2.0))]
        for b in qs:
            b[0].set_fill(BLACK, 1)
        binds = [Arrow(exch[0].get_right() + 0.08 * RIGHT, b[0].get_left() + 0.08 * LEFT, buff=0, stroke_width=2.5, color=GOLD_M,
                       max_tip_length_to_length_ratio=0.08) for b in qs]
        pa = Arrow(prod[0].get_right() + 0.08 * RIGHT, exch[0].get_left() + 0.08 * LEFT, buff=0, stroke_width=2.5, color=GREY_B,
                   max_tip_length_to_length_ratio=0.15)
        self.steps("Other services need these payments too. The payment service sends each one to an exchange, "
                   "which stores nothing and puts a copy in every queue bound to it.", [
            (lambda: [FadeOut(lbox), FadeOut(llab), *[FadeOut(h) for h in (h1, h2, h3b, h4, h5)], FadeOut(bad), FadeOut(one),
                      FadeOut(head), FadeOut(qlab), FadeOut(cb), ca.animate.set_opacity(0.0), ReplacementTransform(qbox, qs[0][0])], 1.0),
            (lambda: [FadeIn(qs[0][1]), FadeIn(prod), FadeOut(ca)], 0.6),
            "to an exchange",
            (lambda: [GrowArrow(pa), FadeIn(exch)], 0.8),
            "and puts a copy",
            (lambda: [*[GrowArrow(b) for b in binds], FadeIn(qs[1]), FadeIn(qs[2])], 0.8),
            (lambda: [Succession(flow(pa, WHITE, 0.6), AnimationGroup(*[flow(b, GOLD_M, 0.7) for b in binds]))], 1.4),
        ])

        SX = 5.2
        la = box("ledger A", None, SX, 2.45, A_C, w=2.3, h=0.7, size=20)
        lb = box("ledger B", None, SX, 1.55, B_C, w=2.3, h=0.7, size=20)
        fr = box("fraud check", None, SX, 0.0, BLUE_M, w=2.3, h=0.8, size=20)
        nt = box("notifications", None, SX, -2.0, GREEN_M, w=2.3, h=0.8, size=20)
        outs = [edge_arrow(qs[0][0], la[0], A_C), edge_arrow(qs[0][0], lb[0], B_C), edge_arrow(qs[1][0], fr[0], BLUE_M),
                edge_arrow(qs[2][0], nt[0], GREEN_M)]
        self.steps("The ledger, the fraud check and the notification service each read their own queue, "
                   "so every one of them sees every payment. That's fan-out.", [
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.2 * LEFT) for b in (la, lb, fr, nt)], lag_ratio=0.15),
                      LaggedStart(*[GrowArrow(a) for a in outs], lag_ratio=0.15)], 1.2),
            "so every one",
            (lambda: [Succession(flow(pa, WHITE, 0.5), AnimationGroup(*[flow(b, GOLD_M, 0.6) for b in binds]),
                                 AnimationGroup(*[flow(a, a.get_color(), 0.6) for a in (outs[0], outs[2], outs[3])]))], 2.0),
            "That's fan-out",
            (lambda: [glow(qs[0][0], GOLD_M, 1.03), glow(qs[1][0], GOLD_M, 1.03), glow(qs[2][0], GOLD_M, 1.03)], 1.0),
        ])

        keep = chip("a queue keeps its order only where it hands messages out", YELLOW_M, 21).move_to([0, -3.2, 0])
        self.steps("Fan-out between services, competing consumers within one. "
                   "And a queue keeps its order only at the moment it hands a message out.", [
            (lambda: [glow(la[0], A_C, 1.05), glow(lb[0], B_C, 1.05)], 1.0),
            "And a queue",
            (lambda: [FadeIn(keep, shift=0.15 * UP)], 0.9),
        ])
        self.wait(0.6)
