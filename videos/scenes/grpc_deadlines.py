from sfz import *

SAY.insert(0, (r"\bDEADLINE_EXCEEDED\b", "deadline exceeded"))
SAY.insert(0, (r"\bgRPC\b", "G R P C"))
SAY.insert(0, (r"\bk-7f\b", "K seven F"))
SAY.insert(0, (r"\bch_1\b", "charge one"))

BOX_Y = 2.45
BX = {"A": -5.0, "B": 0.0, "C": 5.0}
BW, BH = 2.6, 0.66
LANE_Y = {"A": 1.15, "B": 0.4, "C": -0.35}
AX_Y = -1.0
TL0 = -4.1                                   # x of t = 0 ms
TPU = 0.0155                                 # units per ms


def tx(t):
    return TL0 + t * TPU


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


def glow(rect, color=YELLOW_M, s=1.05):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def svc(k, name, color=WHITE):
    return mbox(name, color, w=BW, h=BH, size=20).move_to([BX[k], BOX_Y, 0])


def hop(a, b):
    return Arrow([BX[a] + BW / 2 + 0.08, BOX_Y, 0], [BX[b] - BW / 2 - 0.08, BOX_Y, 0], buff=0, stroke_width=3, color=GREY_B,
                 max_tip_length_to_length_ratio=0.1)


def hop_label(a, b, s, color=GREY_B):
    return T(s, 18, color).move_to([(BX[a] + BX[b]) / 2, BOX_Y + 0.38, 0])


def seg(k, t0, t1, color, label="", lcolor=WHITE):
    r = Rectangle(width=(t1 - t0) * TPU, height=0.4, stroke_width=0).set_fill(color, 0.5)
    r.move_to([(tx(t0) + tx(t1)) / 2, LANE_Y[k], 0])
    g = VGroup(r)
    if label:
        t = T(label, 15, lcolor)
        if t.width + 0.15 < r.width:
            g.add(t.move_to(r))
    return g


def status(s, k, color=GREY_B, size=20):
    return T(s, size, color).move_to([0, [-2.15, -2.75][k], 0])


def dot_hop(a, b, color=YELLOW_M, rt=0.6, frac=1.0):
    s = np.array([BX[a] + (BW / 2 + 0.1) * np.sign(BX[b] - BX[a]), BOX_Y, 0])
    e = np.array([BX[b] - (BW / 2 + 0.1) * np.sign(BX[b] - BX[a]), BOX_Y, 0])
    e = s + frac * (e - s)
    d = Dot(radius=0.08, color=color).move_to(s)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(s, e), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


class GrpcDeadlines(Base):
    """enc-04, section 2 (with sections 0 and 4): checkout -> payments -> issuer. Checkout sets a 300 ms deadline;
    payments works 120 ms, then calls the issuer, which needs 500 ms. Without the deadline the issuer works until
    620 ms for nobody; with it, the call arrives with 180 ms left and everyone stops at 300. Then the charge whose
    reply was lost: a plain retry charges twice; an idempotency key k-7f claimed before the work returns ch_1 again."""

    def construct(self):
        self.title_card("Deadlines and retries", "a remote call can end in a way a local call can't")

        A, B, C = svc("A", "checkout"), svc("B", "payments"), svc("C", "card issuer")
        ab, bc = hop("A", "B"), hop("B", "C")
        self.steps("Checkout charges 40 euros through the payment service, which asks the card issuer. "
                   "Each arrow is a call to another machine.", [
            (lambda: [FadeIn(A)], 0.5),
            "through the payment",
            (lambda: [GrowArrow(ab), FadeIn(B)], 0.7),
            "which asks",
            (lambda: [GrowArrow(bc), FadeIn(C)], 0.7),
            "Each arrow",
            (lambda: [dot_hop("A", "B", WHITE, 0.5)], 0.6),
            (lambda: [dot_hop("B", "C", WHITE, 0.5)], 0.6),
        ])

        loc = status("local call: about 1 ns, then it returns or throws", 0, GREY_A)
        rem = status("remote call: 0.3 ms in one datacenter, 70 ms across regions, or no reply at all", 1, GOLD_M)
        self.steps("A local function call takes about a nanosecond, and it either returns or throws. "
                   "A call to another machine takes hundreds of microseconds or more, and it can also end in silence.", [
            (lambda: [FadeIn(loc, shift=0.1 * UP)], 0.7),
            "A call to another",
            (lambda: [FadeIn(rem, shift=0.1 * UP)], 0.7),
            "end in silence",
            (lambda: [dot_hop("A", "B", WHITE, 0.6, 0.55)], 0.7),
        ])

        lanes = VGroup(*[left_at(T(n, 18, GREY_B), -6.6, LANE_Y[k]) for k, n in (("A", "checkout"), ("B", "payments"), ("C", "issuer"))])
        axis = Line([tx(0), AX_Y, 0], [tx(650), AX_Y, 0], stroke_width=2, color=GREY_C)
        ticks = VGroup(*[VGroup(Line([tx(t), AX_Y - 0.08, 0], [tx(t), AX_Y + 0.08, 0], stroke_width=2, color=GREY_C),
                                T(f"{t}" + (" ms" if t == 600 else ""), 15, GREY_C).move_to([tx(t) + (0.17 if t == 600 else 0), AX_Y - 0.3, 0]))
                         for t in range(0, 700, 100)])
        dl = DashedLine([tx(300), AX_Y - 0.05, 0], [tx(300), LANE_Y["A"] + 0.38, 0], dash_length=0.08, stroke_width=2.5, color=RED_M)
        dll = T("deadline", 16, RED_M).move_to([tx(300), LANE_Y["A"] + 0.55, 0])
        abl = hop_label("A", "B", "300 ms left", GOLD_M)
        self.steps("So checkout gives the call a deadline, 300 milliseconds, and gRPC sends it along as time remaining.", [
            (lambda: [FadeOut(loc), FadeOut(rem), FadeIn(lanes), Create(axis), FadeIn(ticks)], 0.9),
            "a deadline",
            (lambda: [Create(dl), FadeIn(dll)], 0.6),
            "and gRPC sends",
            (lambda: [FadeIn(abl, shift=0.1 * DOWN), dot_hop("A", "B", GOLD_M, 0.6)], 0.7),
        ])

        a1, b1 = seg("A", 0, 120, GREY_B, "waiting"), seg("B", 0, 120, BLUE_M, "own work")
        self.steps("Payments spends 120 milliseconds on its own work, then calls the issuer, which needs 500 milliseconds today.", [
            (lambda: [GrowFromEdge(a1, LEFT), GrowFromEdge(b1, LEFT)], 1.4),
            "then calls",
            (lambda: [dot_hop("B", "C", GOLD_M, 0.5)], 0.6),
        ])

        a2, b2, c1 = seg("A", 120, 300, GREY_B), seg("B", 120, 300, GREY_B, "waiting"), seg("C", 120, 300, GOLD_M, "working")
        dx = T("DEADLINE_EXCEEDED", 16, RED_M)
        dx = left_at(dx, tx(300) + 0.12, LANE_Y["A"])
        self.steps("At 300, checkout's deadline runs out, and it gets DEADLINE_EXCEEDED.", [
            (lambda: [GrowFromEdge(a2, LEFT), GrowFromEdge(b2, LEFT), GrowFromEdge(c1, LEFT)], 1.6),
            "and it gets",
            (lambda: [FadeIn(dx), A[0].animate.set_stroke(RED_M), dl.animate.set_stroke(width=4)], 0.7),
        ])

        bcl = hop_label("B", "C", "no deadline", RED_M)
        c2 = seg("C", 300, 620, RED_M, "320 ms for nobody")
        self.steps("If the issuer's call carried no deadline, it would work on for another 320 milliseconds, "
                   "for an answer nobody is waiting for.", [
            (lambda: [FadeIn(bcl, shift=0.1 * DOWN)], 0.6),
            "it would work on",
            (lambda: [GrowFromEdge(c2, LEFT)], 1.8),
            "for an answer",
            (lambda: [glow(c2[0], RED_M, 1.0)], 0.7),
        ])

        bcl2 = hop_label("B", "C", "180 ms left", GOLD_M)
        c1b = seg("C", 120, 300, GOLD_M, "180 ms left")
        cut = VGroup(tick(False, 0.14).move_to([tx(300) + 0.22, LANE_Y["C"], 0]), tick(False, 0.14).move_to([tx(300) + 0.22, LANE_Y["B"], 0]))
        stop = left_at(T("cancelled, stops", 16, GOLD_M), tx(300) + 0.45, LANE_Y["C"])
        self.steps("In Java and Go, gRPC passes the deadline on instead. The issuer's call arrives with 180 milliseconds left, "
                   "so at 300 everyone gives up together, and the issuer stops.", [
            (lambda: [FadeOut(c2), Transform(bcl, bcl2)], 0.8),
            "The issuer's call",
            (lambda: [dot_hop("B", "C", GOLD_M, 0.5), Transform(c1, c1b)], 0.7),
            "so at 300",
            (lambda: [glow(dl, RED_M, 1.0)], 0.6),
            (lambda: [Create(cut), FadeIn(stop)], 0.6),
        ])

        # ---- the retry -------------------------------------------------------------------------------------------------
        tline = VGroup(lanes, axis, ticks, dl, dll, a1, a2, b1, b2, c1, dx, cut, stop)
        q = T("?", 40, GOLD_M).next_to(A, DOWN, buff=0.25)
        endings = status("a lost request, a lost reply, a slow server: all look like a timeout", 0, GREY_A)
        self.steps("But was the card charged? From checkout, a lost request, a lost reply and a slow server all look the same.", [
            (lambda: [FadeOut(tline), FadeOut(abl), FadeOut(bcl), A[0].animate.set_stroke(WHITE)], 0.8),
            (lambda: [FadeIn(q, scale=0.8)], 0.5),
            "From checkout",
            (lambda: [FadeIn(endings, shift=0.1 * UP)], 0.7),
        ])

        charges = VGroup(T("issuer's charges", 18, GREY_B).move_to([BX["C"], 1.55, 0]))
        ch1 = M("ch_1  40.00 EUR", 18, GREEN_M).move_to([BX["C"], 0.95, 0])
        ch2 = M("ch_2  40.00 EUR", 18, RED_M).move_to([BX["C"], 0.4, 0])
        att = VGroup(left_at(M("attempt 1: timeout", 17, GREY_A), BX["A"] - 1.3, 0.95))
        att2 = left_at(M("attempt 2: OK", 17, GREY_A), BX["A"] - 1.3, 0.4)
        lost = tick(False, 0.15).move_to([(BX["A"] + BX["B"]) / 2 - 0.1, BOX_Y - 0.3, 0])
        twice = status("1,000 payments, 30% of replies lost: retrying charged 313 cards twice", 1, RED_M, 19)
        self.steps("Say the card was charged and only the reply was lost. Checkout retries, payments sees a brand new request, "
                   "and the card is charged twice.", [
            (lambda: [FadeOut(q), FadeIn(charges), FadeIn(att)], 0.6),
            "the card was charged",
            (lambda: [dot_hop("B", "C", WHITE, 0.4)], 0.5),
            (lambda: [FadeIn(ch1)], 0.4),
            "only the reply",
            (lambda: [dot_hop("B", "A", GREEN_M, 0.5, 0.45), FadeIn(lost)], 0.7),
            "Checkout retries",
            (lambda: [FadeIn(att2), dot_hop("A", "B", WHITE, 0.5)], 0.6),
            (lambda: [dot_hop("B", "C", WHITE, 0.4)], 0.5),
            "and the card",
            (lambda: [FadeIn(ch2), FadeIn(twice, shift=0.1 * UP)], 0.7),
        ])

        key = chip("key k-7f", GOLD_M, 18).next_to(A, DOWN, buff=0.2)
        abk = hop_label("A", "B", "Charge(pay-1, k-7f)", GOLD_M)
        self.steps("The fix is an idempotency key. Checkout makes one, k-7f, before the first attempt, and sends the same key "
                   "with every retry.", [
            (lambda: [FadeOut(ch2), FadeOut(twice), FadeOut(att), FadeOut(att2), FadeOut(lost), FadeOut(endings)], 0.7),
            "Checkout makes one",
            (lambda: [FadeIn(key, shift=0.1 * DOWN)], 0.6),
            "and sends",
            (lambda: [FadeIn(abk), dot_hop("A", "B", GOLD_M, 0.6)], 0.7),
        ])

        store = VGroup(T("payments' key store", 18, GREY_B).move_to([BX["B"], 1.55, 0]))
        row1 = M("k-7f  claimed", 18, GOLD_M).move_to([BX["B"], 0.95, 0])
        row2 = M("k-7f  → ch_1", 18, GREEN_M).move_to([BX["B"], 0.95, 0])
        once = status("the retry gets ch_1 back: one charge", 1, GREEN_M)
        self.steps("Payments claims the key before doing any work, and stores the result under it. "
                   "The retry finds k-7f already done, and gets ch_1 back. The card is charged once.", [
            (lambda: [FadeIn(store), FadeIn(row1)], 0.7),
            "and stores",
            (lambda: [dot_hop("B", "C", GOLD_M, 0.4)], 0.5),
            (lambda: [Transform(row1, row2)], 0.6),
            "The retry finds",
            (lambda: [dot_hop("A", "B", GOLD_M, 0.5)], 0.6),
            (lambda: [glow(row1, GREEN_M, 1.1)], 0.5),
            "and gets ch_1",
            (lambda: [dot_hop("B", "A", GREEN_M, 0.5), FadeIn(once, shift=0.1 * UP)], 0.7),
        ])

        self.steps("A remote call can end in silence. Bound it with a deadline that travels down the chain, "
                   "and make asking again safe with an idempotency key.", [
            (lambda: [glow(A[0], GREY_A, 1.05), glow(B[0], GREY_A, 1.05), glow(C[0], GREY_A, 1.05)], 0.9),
            "Bound it",
            (lambda: [dot_hop("A", "B", GOLD_M, 0.5)], 0.6),
            (lambda: [dot_hop("B", "C", GOLD_M, 0.5)], 0.6),
            "and make asking",
            (lambda: [glow(key[0], GOLD_M, 1.08)], 0.8),
        ])
        self.wait(0.6)
