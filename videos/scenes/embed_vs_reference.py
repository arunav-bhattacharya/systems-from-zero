from sfz import *

SAY.insert(0, (r"\bM-0042's\b", "M 42's"))
SAY.insert(0, (r"\bM-0042\b", "M 42"))
SAY.insert(0, (r"\b6,837\b", "68 37"))

DT = 2.1                               # top of every document box
LX0, LW = -4.5, 5.8                    # the payment document: left edge, width
RX0, RW = 2.1, 4.45                    # the right column: refunds, then the merchant
SCR = np.array([0.4, 3.0, 0])          # the payment screen

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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def arr(a, b, color=GREY_B, sw=2.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = np.linalg.norm(b - a)
    return Arrow(a, b, buff=0.04, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2 / n,
                 max_stroke_width_to_length_ratio=20)




def ly(i, top=DT):
    return top - 0.33 - i * 0.37


def dl(x0, i, text, indent=1, color=WHITE, top=DT):
    return left_at(M(text, 15, color), x0 + 0.25 + indent * 0.35, ly(i, top))


def dbox(x0, w, n, color=GREY_B, top=DT):
    h = 0.66 + (n - 1) * 0.37
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1)
    return r.move_to([x0 + w / 2, top - h / 2, 0])


class EmbedVsReference(Base):
    """model-06, section 0 (with model-02's embed-or-reference rule): pay-81002 for 6,837. Refunds in their own collection
    need two reads, and two refunds of 6,000 can both get in (12,000). Embedded with a running total, one guarded updateOne
    is atomic: the first refund wins, the second changes nothing. The shared merchant is referenced by id: no copies, one
    more read. Embedding every payment in the merchant grows without end (40,000 a day, 16 MB in under three days), so
    reference it and keep a capped summary of three."""

    def construct(self):
        self.title_card("Embed or reference", "what goes inside a document, and what stays outside")

        # ---- 1. the payment document -------------------------------------------------------------------------------
        scr = mbox("payment screen", WHITE, h=0.55, size=17).move_to(SCR)
        P = [dl(LX0, 0, '{ _id: "pay-81002",', 0), dl(LX0, 1, "amountMinor: 6837,"), dl(LX0, 2, 'status: "SETTLED",'),
             dl(LX0, 3, 'merchantId: "M-0042" }')]
        pb = dbox(LX0, LW, 4)
        pl = left_at(T("payments collection", 16, GREY_B), LX0, 2.35)
        ra1 = arr([SCR[0] - 0.4, SCR[1] - 0.29, 0], [-0.9, DT + 0.03, 0], GREY_B)
        reads = ValueTracker(1)
        rc = always_redraw(lambda: right_at(T(f"reads per screen: {int(round(reads.get_value()))}", 18,
                                              GREY_B if reads.get_value() < 1.5 else GOLD_M), -1.2, SCR[1]))
        self.steps("A payment screen shows a payment, its refunds and its merchant. In MongoDB one record, a document, "
                   "can hold a whole tree. So what goes inside the payment, and what stays outside?", [
            (lambda: [FadeIn(scr)], 0.5),
            "In MongoDB",
            (lambda: [FadeIn(pb), FadeIn(pl), LaggedStart(*[FadeIn(x, shift=0.1 * RIGHT) for x in P], lag_ratio=0.2)], 1.2),
            (lambda: [GrowArrow(ra1), FadeIn(rc)], 0.6),
            "So what goes",
            (lambda: [glow(pb, GOLD_M, 1.01)], 0.9),
        ])

        # ---- 2. version 1: refunds in their own collection ----------------------------------------------------------
        def refdoc(rid, top):
            ls = [dl(RX0, 0, f'{{ _id: "{rid}",', 0, top=top), dl(RX0, 1, 'paymentId: "pay-81002",', top=top),
                  dl(RX0, 2, "amountMinor: 6000 }", top=top)]
            return VGroup(dbox(RX0, RW, 3, top=top), *ls)

        r1 = refdoc("ref-1", DT)
        r2 = refdoc("ref-2", 0.45)
        rl = right_at(T("refunds collection", 16, GREY_B), RX0 + RW, 2.35)
        ra2 = arr([SCR[0] + 0.5, SCR[1] - 0.29, 0], [RX0 + 0.8, DT + 0.03, 0], GREY_B)
        self.steps("Version one copies the tables. Refunds get their own collection, so the screen needs two reads.", [
            (lambda: [FadeIn(rl), FadeIn(r1[0])], 0.6),
            "so the screen",
            (lambda: [GrowArrow(ra2), reads.animate.set_value(2)], 0.7),
            (lambda: [travel(ra1, YELLOW_M, 0.5), travel(ra2, YELLOW_M, 0.5)], 0.6),
        ])

        # ---- 3. the race across two documents ---------------------------------------------------------------------------
        bad = T("refunded: 12,000 of 6,837", 20, RED_M).move_to([RX0 + RW / 2, -1.45, 0])
        self.steps("Worse, two refunds of 6,000 arrive at once for this payment of 6,837. Each one checks the refunds, "
                   "finds none, and inserts. Now 12,000 is refunded.", [
            "Each one checks",
            (lambda: [*[FadeIn(x) for x in r1[1:]]], 0.6),
            (lambda: [FadeIn(r2)], 0.6),
            "Now 12,000",
            (lambda: [FadeIn(bad, shift=0.1 * UP), r1[0].animate.set_stroke(RED_M), r2[0].animate.set_stroke(RED_M)], 0.7),
        ])

        # ---- 4. version 2: embed --------------------------------------------------------------------------------------
        P3 = dl(LX0, 3, 'merchantId: "M-0042",')
        P4 = dl(LX0, 4, "refundedMinor: 0,", color=GREEN_M)
        P5 = dl(LX0, 5, "refunds: [ ] }", color=GREEN_M)
        pb2 = dbox(LX0, LW, 6, GREEN_M)
        self.steps("Stopping that takes a transaction across two documents. Version two puts the refunds inside the "
                   "payment, next to a running total.", [
            (lambda: [glow(bad, RED_M, 1.0)], 0.7),
            "Version two",
            (lambda: [FadeOut(r1), FadeOut(r2), FadeOut(bad), FadeOut(rl), FadeOut(ra2), reads.animate.set_value(1)], 0.7),
            (lambda: [Transform(pb, pb2), ReplacementTransform(P[3], P3)], 0.6),
            "next to",
            (lambda: [FadeIn(P4, shift=0.1 * RIGHT), FadeIn(P5, shift=0.1 * RIGHT)], 0.7),
        ])

        # ---- 5. one atomic update ------------------------------------------------------------------------------------------
        u = VGroup(left_at(M("filter: refundedMinor + 6000 <= amountMinor", 15, GOLD_M), LX0, -1.95),
                   left_at(M("update: push the refund, add 6000", 15, GOLD_M), LX0, -2.33))
        ul = left_at(T("one updateOne, atomic for one document", 18, GREY_B), LX0, -1.55)
        self.steps("One read returns everything. And a write to one document is atomic: one update checks that the total "
                   "plus 6,000 stays within the amount, pushes the refund, and adds to the total.", [
            (lambda: [travel(ra1, YELLOW_M, 0.6)], 0.7),
            "And a write",
            (lambda: [FadeIn(ul)], 0.6),
            "one update checks",
            (lambda: [FadeIn(u[0], shift=0.1 * UP)], 0.6),
            "pushes the refund",
            (lambda: [FadeIn(u[1], shift=0.1 * UP)], 0.6),
        ])

        # ---- 6. the race again ----------------------------------------------------------------------------------------------
        ca = chip("refund 6,000", GOLD_M, 17).move_to([-5.55, 0.95, 0])
        cb = chip("refund 6,000", GOLD_M, 17).move_to([-5.55, -0.15, 0])
        P4b = dl(LX0, 4, "refundedMinor: 6000,", color=GREEN_M)
        P5b = dl(LX0, 5, "refunds: [", color=GREEN_M)
        P6 = VGroup(dl(LX0, 6, '{ id: "ref-1", amountMinor: 6000 }', 2, GREEN_M), dl(LX0, 7, "] }", 1, GREEN_M))
        pb3 = dbox(LX0, LW, 8, GREEN_M)
        ok1 = left_at(T("first: modified 1", 18, GREEN_M), LX0, -2.8)
        no2 = left_at(T("second: 6000 + 6000 > 6837, modified 0", 18, RED_M), LX0, -3.2)
        ga = arr(ca.get_right() + 0.04 * RIGHT, [LX0 - 0.05, ca.get_y(), 0], GOLD_M)
        gb = arr(cb.get_right() + 0.04 * RIGHT, [LX0 - 0.05, cb.get_y(), 0], GOLD_M)
        self.steps("Two refunds race again. The first matches and applies. The second's check now fails, "
                   "12,000 is over 6,837, so it changes nothing.", [
            (lambda: [FadeIn(ca), FadeIn(cb), GrowArrow(ga), GrowArrow(gb)], 0.8),
            "The first",
            (lambda: [travel(ga, GOLD_M, 0.5)], 0.5),
            (lambda: [Transform(pb, pb3), ReplacementTransform(P4, P4b), ReplacementTransform(P5, P5b), FadeIn(P6), FadeIn(ok1)], 0.8),
            "The second's",
            (lambda: [travel(gb, RED_M, 0.5)], 0.5),
            (lambda: [FadeIn(no2), cb[0].animate.set_stroke(RED_M), gb.animate.set_color(RED_M)], 0.6),
        ])

        # ---- 7. the merchant is shared: reference it ---------------------------------------------------------------------
        M_ = [dl(RX0, 0, '{ _id: "M-0042",', 0), dl(RX0, 1, 'name: "Harbour Coffee",'), dl(RX0, 2, 'city: "Utrecht" }')]
        mb = dbox(RX0, RW, 3, BLUE_M)
        ml = right_at(T("merchants collection", 16, GREY_B), RX0 + RW, 2.35)
        refl = DashedLine([-1.15, ly(3), 0], [RX0 - 0.05, ly(0) - 0.1, 0], dash_length=0.08, stroke_width=2, color=BLUE_M)
        sh = left_at(T("shared by 40,000 payments a day", 17, BLUE_M), RX0, 0.2)
        self.steps("The merchant is different. Thousands of payments share it, so the payment holds only its id: "
                   "a reference. A new address is one write, to one document.", [
            (lambda: [FadeOut(VGroup(ca, cb, ga, gb, ok1, no2, u, ul))], 0.6),
            (lambda: [FadeIn(mb), FadeIn(ml), *[FadeIn(x) for x in M_]], 0.7),
            "Thousands of",
            (lambda: [FadeIn(sh)], 0.5),
            "only its id",
            (lambda: [Indicate(P3, color=BLUE_M, scale_factor=1.05), Create(refl)], 0.8),
            "A new address",
            (lambda: [Indicate(M_[2], color=BLUE_M, scale_factor=1.08)], 0.8),
        ])

        # ---- 8. the price: a second read ------------------------------------------------------------------------------------
        ra3 = arr([SCR[0] + 0.5, SCR[1] - 0.29, 0], [RX0 + 0.8, DT + 0.03, 0], BLUE_M)
        self.steps("The price is a second read whenever the screen shows the merchant's name.", [
            (lambda: [GrowArrow(ra3), reads.animate.set_value(2)], 0.7),
            (lambda: [travel(ra1, YELLOW_M, 0.5), travel(ra3, BLUE_M, 0.5)], 0.6),
        ])

        # ---- 9. embedding with no end -----------------------------------------------------------------------------------------
        M2 = dl(RX0, 2, 'city: "Utrecht",')
        M3 = dl(RX0, 3, "payments: [", color=RED_M)
        items = [dl(RX0, 4 + j, f'{{ _id: "pay-8{1002 + j * 7}", ... }},', 1.25, GREY_B) for j in range(5)]
        more = dl(RX0, 9, "... 40,000 more every day", 1.25, RED_M)
        mb2 = dbox(RX0, RW, 10, RED_M)
        self.steps("Embedding goes wrong when an array has no end. Put every payment inside its merchant, "
                   "and M-0042 adds 40,000 a day.", [
            (lambda: [FadeOut(ra3), FadeOut(refl), FadeOut(sh), reads.animate.set_value(1),
                      VGroup(pb, P[0], P[1], P[2], P3, P4b, P5b, P6).animate.set_opacity(0.3)], 0.7),
            "Put every payment",
            (lambda: [Transform(mb, mb2), Transform(M_[2], M2), FadeIn(M3)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(x, shift=0.1 * DOWN) for x in items], lag_ratio=0.25)], 1.2),
            "and M-0042 adds",
            (lambda: [FadeIn(more)], 0.5),
        ])

        # ---- 10. the 16 MB limit -----------------------------------------------------------------------------------------------
        sz = ValueTracker(0.1)
        szt = always_redraw(lambda: left_at(T(f"document size: {sz.get_value():.1f} MB" + ("  (the limit)" if sz.get_value() > 15.9 else ""),
                                              19, RED_M if sz.get_value() > 8 else GOLD_M), RX0, -2.75))
        rd = arr([SCR[0] + 0.5, SCR[1] - 0.29, 0], [RX0 + 0.8, DT + 0.03, 0], RED_M, 5)
        self.steps("In under three days the document hits MongoDB's 16 MB limit. Long before that, every read of the "
                   "merchant drags the whole history along.", [
            (lambda: [FadeIn(szt)], 0.3),
            (lambda: [sz.animate(rate_func=linear).set_value(16.0)], 2.0),
            "Long before",
            (lambda: [GrowArrow(rd)], 0.5),
            "drags the whole",
            (lambda: [travel(Line(rd.get_end(), rd.get_start()), RED_M, 1.0), glow(mb, RED_M, 1.0)], 1.1),
        ])
        szt.clear_updaters()

        # ---- 11. reference it, keep a capped summary --------------------------------------------------------------------------
        M3b = dl(RX0, 3, "recentPayments: [", color=GREEN_M)
        keep = [dl(RX0, 4 + j, f'{{ _id: "pay-8{1030 - j * 7}", ... }}' + ("" if j == 2 else ","), 1.25, GREEN_M) for j in range(3)]
        keep.append(dl(RX0, 7, "] }", 1, GREEN_M))
        mb3 = dbox(RX0, RW, 8, GREEN_M)
        szt2 = left_at(T("document size: about 1 KB, and it stays there", 19, GREEN_M), RX0, -2.75)
        cap = left_at(M("$push with $slice: -3", 15, GREEN_M), RX0, -2.2)
        self.steps("So reference what grows without limit: payments stay their own documents. If a screen needs recent "
                   "payments, keep a summary capped at three.", [
            (lambda: [FadeOut(rd), VGroup(pb, P[0], P[1], P[2], P3, P4b, P5b, P6).animate.set_opacity(1), *[FadeOut(x) for x in items], FadeOut(more),
                      Transform(mb, dbox(RX0, RW, 4, BLUE_M)), FadeOut(M3), Transform(szt, szt2)], 0.9),
            "If a screen",
            (lambda: [Transform(mb, mb3), FadeIn(M3b), *[FadeIn(k, shift=0.1 * DOWN) for k in keep]], 0.8),
            "capped at three",
            (lambda: [FadeIn(cap)], 0.6),
        ])

        # ---- 12. the sentence to keep -------------------------------------------------------------------------------------------
        self.steps("Embed what you read and change together, and what stays small. Reference what's shared, "
                   "or what grows without end.", [
            (lambda: [glow(pb, GREEN_M, 1.01)], 0.9),
            "Reference what's",
            (lambda: [glow(mb, BLUE_M, 1.01), Indicate(P3, color=BLUE_M, scale_factor=1.05)], 0.9),
        ])
        self.wait(0.6)
