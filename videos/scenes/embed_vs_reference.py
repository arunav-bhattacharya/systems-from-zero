from sfz import *

# Amounts are said the way people say them; captions keep the digits.
SAY.insert(0, (r"\b68\.37\b", "sixty-eight thirty-seven"))
SAY.insert(0, (r"\b8\.37\b", "eight thirty-seven"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bversion 4\.0\b", "version four point oh"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TILL_X, TILL_Y = -5.35, [1.35, -1.05]
DX0, DX1 = -3.5, 6.5
DCX = (DX0 + DX1) / 2
TOP_Y, CAP_Y, BAR_Y, QY = 3.3, -2.45, -2.8, -3.2
DOC_Y = [2.25, 1.8, 1.35, 0.9]                     # the version-2 document's four lines
DOC_T, DOC_B = 2.65, 0.5
CARD_Y = [-0.55, -1.0, -1.45]                      # the one-update card's three lines


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

    def steps(self, text, items, after=0.2):
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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def dot_to(a, b, color=YELLOW_M, rt=0.7):
    d = Dot(radius=0.08, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


def framed(x0, x1, top, bot, color, a=0.08, sw=2.5):
    return RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=sw).set_fill(
        fillc(color, a), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


# ---- the pieces ----
def till(k):
    y = TILL_Y[k]
    b = RoundedRectangle(corner_radius=0.12, width=2.3, height=1.25, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1).move_to([TILL_X, y, 0])
    lab = T(f"till {k + 1}", 22).move_to([TILL_X, y + 0.3, 0])
    t = T("refund 60.00", 19, GOLD_M)
    btn = VGroup(RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.42, stroke_color=GOLD_M, stroke_width=2).set_fill(
        fillc(GOLD_M, 0.25), 1), t).move_to([TILL_X, y - 0.27, 0])
    btn[1].move_to(btn[0])
    return VGroup(b, lab, btn)


def under(k):
    return np.array([TILL_X, TILL_Y[k] - 0.92, 0])


def doc_line(i, s, color=WHITE):
    """One line of the document; leading spaces become an indent (Text drops them)."""
    ind = len(s) - len(s.lstrip(" "))
    m = fit(M(s.lstrip(" "), 20, color), DX1 - DX0 - 0.8 - ind * 0.155)
    return left_at(m, DX0 + 0.35 + ind * 0.155, DOC_Y[i])


class EmbedVsReference(Base):
    """model-06, section 0. A bakery payment of 68.37 (pay-81002) and two tills pressing refund 60.00 in the same second;
    the rule: refunds never add up to more than the payment. Version 1 references: a refunds collection; both tills check
    "none yet" and write, so 120.00 is refunded. The paper receipt you must hold to write on, with a running total.
    Version 2 embeds the refunds and refundedMinor in the payment's document; a write to one document is atomic, so one
    guarded update gives modifiedCount 1, then 0. Embed what's read and changed together and stays small, reference what
    grows; 16 MB; transactions since 4.0 cost more. The moral, and a check (a third refund of 8.37 fits exactly)."""

    def cap(self, s, color=GREY_B, size=22):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def total(self, s, color=WHITE):
        new = right_at(T(f"refunded so far: {s}", 22, color), 6.25, QY)
        old, self.tm = self.tm, new
        return [swap(old, new)]

    def note(self, k, s, color=GREY_B, mono=False):
        new = (M(s, 17, color) if mono else T(s, 18, color)).move_to(under(k))
        old, self.notes[k] = self.notes[k], new
        return [swap(old, new)]

    def clear_notes(self):
        out = [FadeOut(n) for n in self.notes if n is not None]
        self.notes = [None, None]
        return out

    def set_line(self, i, s, color=WHITE):
        new = doc_line(i, s, color)
        old, self.doc[i] = self.doc[i], new
        return [swap(old, new, RIGHT)]

    def set_card(self, i, s, color=WHITE):
        new = left_at(T(s, 20, color), DX0 + 0.35, CARD_Y[i])
        fit(new, DX1 - DX0 - 0.6)
        left_at(new, DX0 + 0.35, CARD_Y[i])
        old, self.card[i] = self.card[i], new
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar, rate_func=linear), run_time=secs)

    def construct(self):
        self.capm = self.tm = None
        self.notes = [None, None]
        self.title_card("Two tills, one receipt", "embed what must change together")

        # ---------------- scene 1: two tills, one payment ----------------
        tills = [till(0), till(1)]
        pay = VGroup(T("a party order", 22, GREY_B), M("pay-81002", 26), T("68.37", 44, WHITE)).arrange(DOWN, buff=0.2).move_to([DCX, 0.4, 0])
        qbox = RoundedRectangle(corner_radius=0.1, width=13.0, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([0, QY, 0])
        strip_l = left_at(T("pay-81002: a payment of 68.37", 22), -6.25, QY)
        self.steps("A bakery customer paid 68.37 for a party order, then brought most of it back.", [
            (lambda: [FadeIn(pay, shift=0.1 * UP)], 0.8),
            "brought most",
            (lambda: [FadeIn(qbox), FadeIn(strip_l), *self.total("0.00")], 0.7),
        ])
        self.steps("Two staff members, at two tills, each press refund 60.00, in the same second.", [
            "at two tills",
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.15 * RIGHT) for t in tills], lag_ratio=0.3)], 0.9),
            "each press",
            (lambda: [glow(tills[0][2][0], YELLOW_M, 1.1), glow(tills[1][2][0], YELLOW_M, 1.1)], 0.8),
        ])
        rule = VGroup(RoundedRectangle(corner_radius=0.08, width=9.2, height=0.5, stroke_color=WHITE, stroke_width=2).set_fill(BLACK, 1),
                      T("the rule: refunds never add up to more than the payment", 22)).move_to([0, TOP_Y, 0])
        rule[1].move_to(rule[0])
        q = T("only one should go through. How?", 26, YELLOW_M).move_to([DCX, -1.3, 0])
        self.steps("The rule is that refunds never add up to more than the payment. So only one of these should go through. "
                   "How does the database make sure?", [
            (lambda: [FadeIn(rule, shift=0.1 * DOWN)], 0.7),
            "So only one",
            (lambda: [FadeIn(q, shift=0.1 * UP)], 0.6),
        ])

        # ---------------- scene 2: separate records ----------------
        rows = VGroup(*[framed(DX0 + 0.8, DX0 + 4.6, 1.9 - k * 0.6, 1.45 - k * 0.6, c) for k, c in enumerate([BLUE_M, GOLD_M, GOLD_M])])
        rlab = VGroup(T("payment row", 18), T("refund row", 18, GOLD_M), T("refund row", 18, GOLD_M))
        for r, l in zip(rows, rlab):
            l.move_to(r)
        tbl = VGroup(T("table: payments", 17, GREY_B).next_to(rows[0], RIGHT, buff=0.3), T("table: refunds", 17, GREY_B).next_to(rows[1], RIGHT, buff=0.3))
        self.steps("The habit from SQL databases is separate records. A payment is one row, each refund is a row in another table, "
                   "and the screen joins them back together.", [
            (lambda: [FadeOut(pay), FadeOut(q)], 0.6),
            "A payment is one row",
            (lambda: [FadeIn(rows[0]), FadeIn(rlab[0]), FadeIn(tbl[0])], 0.6),
            "each refund",
            (lambda: [FadeIn(VGroup(rows[1:], rlab[1:])), FadeIn(tbl[1])], 0.6),
            "joins them",
            (lambda: [rows[1].animate.next_to(rows[0], DOWN, buff=0.04), rlab[1].animate.move_to(rows[0].get_center() + 0.49 * DOWN),
                      rows[2].animate.next_to(rows[0], DOWN, buff=0.53), rlab[2].animate.move_to(rows[0].get_center() + 0.98 * DOWN)], 0.8),
        ])
        pbox = framed(DX0, DX1, 2.65, 1.35, BLUE_M).set_z_index(-1)
        plab = left_at(T("payments collection", 19, BLUE_M), DX0 + 0.3, 2.35)
        pdoc = left_at(M('{ _id: "pay-81002", status: "SETTLED", amountMinor: 6837 }', 19), DX0 + 0.35, 1.75)
        rbox = framed(DX0, DX1, 0.95, -1.75, GOLD_M).set_z_index(-1)
        rlab2 = left_at(T("refunds collection", 19, GOLD_M), DX0 + 0.3, 0.65)
        empty = left_at(T("no refunds yet", 19, GREY_C), DX0 + 0.35, 0.05)
        self.steps("MongoDB, a free database program, can do the same. It stores each record as a document: names and values inside "
                   "curly braces, shaped like JSON, a common text format. A set of documents is a collection.", [
            (lambda: [FadeOut(VGroup(rows, rlab, tbl))], 0.5),
            "It stores each record",
            (lambda: [FadeIn(pdoc, shift=0.1 * UP)], 0.7),
            "curly braces",
            (lambda: [*self.cap("a document: names and values inside curly braces", WHITE)], 0.5),
            "A set of documents",
            (lambda: [FadeIn(pbox), FadeIn(plab), *self.cap("a collection: a set of documents", BLUE_M)], 0.7),
        ])
        self.steps("So version one: a payments collection, and a refunds collection where each refund holds its payment's id. "
                   "That's called referencing. The screen now needs two reads.", [
            "and a refunds collection",
            (lambda: [FadeIn(rbox), FadeIn(rlab2), FadeIn(empty)], 0.7),
            "That's called referencing",
            (lambda: self.cap("version 1, referencing: each refund holds its payment's id", GOLD_M), 0.6),
            "two reads",
            (lambda: [dot_to(np.array([DCX, -2.0, 0]), pbox.get_bottom() + 0.1 * UP, WHITE), dot_to(np.array([DCX + 2.5, -2.0, 0]), rbox.get_bottom() + 0.1 * UP, WHITE)], 0.9),
        ])

        # ---------------- scene 3: check, then write ----------------
        rd = [left_at(M('{ paymentId: "pay-81002", amountMinor: 6000 }', 19, GOLD_M), DX0 + 0.35, y) for y in (0.05, -0.6)]
        self.steps("Each till checks the rule, then writes. Till one reads the refunds: none yet, so 60.00 fits. "
                   "Till two reads at the same moment: none yet, 60.00 fits.", [
            (lambda: self.uncap(), 0.4),
            "Till one reads",
            (lambda: [dot_to(tills[0].get_right(), empty.get_left() + 0.1 * LEFT), dot_to(tills[1].get_right(), empty.get_left() + 0.1 * LEFT)], 0.8),
            "none yet, so",
            (lambda: self.note(0, "none yet: 60.00 fits", GREEN_M), 0.5),
            "Till two reads",
            (lambda: self.note(1, "none yet: 60.00 fits", GREEN_M), 0.5),
        ])
        self.steps("Both write. What does the bakery refund in total? Pause and guess.", [
            (lambda: [FadeOut(empty), FadeIn(rd[0], shift=0.2 * RIGHT), FadeIn(rd[1], shift=0.2 * RIGHT)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        rx = tick(False, 0.16).move_to(rule[0].get_right() + 0.35 * RIGHT)
        self.steps("120.00, on a payment of 68.37. The bakery's accountant would like a word.", [
            (lambda: [*self.uncap(), *self.total("120.00", RED_M), Create(rx), rule[0].animate.set_stroke(RED_M)], 0.8),
            "The bakery's accountant",
            (lambda: [Indicate(self.tm, color=RED_M, scale_factor=1.08)], 0.8),
        ])
        self.steps("The check and the write were two steps, on two documents, and the other till slipped in between. "
                   "The usual cure is a lock around everything, or a multi-document transaction: "
                   "a group of writes that happen together, or not at all.", [
            "two steps",
            (lambda: self.cap("check, then write: two steps, and the other till slipped in between", RED_M), 0.6),
            "The usual cure",
            (lambda: self.cap("the usual cure: a lock around everything, or a multi-document transaction", WHITE), 0.6),
            "a group of writes",
            (lambda: self.cap("a transaction: a group of writes that happen together, or not at all", GREY_B), 0.6),
        ])

        # ---------------- scene 4: the receipt ----------------
        RX, RW = 0.4, 3.8
        paper = RoundedRectangle(corner_radius=0.06, width=RW, height=4.4, stroke_color=GREY_A, stroke_width=2.5).set_fill("#141414", 1)
        paper.move_to([RX, 0.4, 0])
        rc = [T("bakery receipt", 22).move_to([RX, 2.25, 0]),
              VGroup(left_at(T("party order", 19), RX - RW / 2 + 0.3, 1.65), right_at(M("68.37", 20), RX + RW / 2 - 0.3, 1.65)),
              DashedLine([RX - RW / 2 + 0.25, 1.3, 0], [RX + RW / 2 - 0.25, 1.3, 0], dash_length=0.08, stroke_width=1.5, color=GREY_C),
              left_at(T("refunds:", 18, GREY_B), RX - RW / 2 + 0.3, 0.95),
              DashedLine([RX - RW / 2 + 0.25, -0.55, 0], [RX + RW / 2 - 0.25, -0.55, 0], dash_length=0.08, stroke_width=1.5, color=GREY_C)]
        rtot = VGroup(left_at(T("refunded so far", 19), RX - RW / 2 + 0.3, -0.95), right_at(M("0.00", 20), RX + RW / 2 - 0.3, -0.95))
        receipt = VGroup(paper, *rc, rtot)
        sbox = framed(4.2, 6.4, 0.6, -1.75, GOLD_M, 0.06)
        slab = T("box of loose slips", 17, GOLD_M).move_to([5.3, 0.3, 0])
        self.steps("Think of the paper receipt instead. Write each refund on the receipt itself, with a running total at the bottom.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(pbox, plab, pdoc, rbox, rlab2, *rd, rx)), rule[0].animate.set_stroke(WHITE),
                      *self.clear_notes(), *self.total("0.00")], 0.8),
            "Think of the paper",
            (lambda: [FadeIn(receipt, shift=0.1 * UP)], 0.8),
            "with a running total",
            (lambda: [Indicate(rtot, color=YELLOW_M)], 0.8),
        ])
        hold = Line(tills[0].get_right(), paper.get_left(), stroke_width=4, color=YELLOW_M)
        self.steps("To write on it, you have to hold it, and only one person can hold it at a time.", [
            "you have to hold it",
            (lambda: [receipt.animate.shift(1.3 * LEFT)], 0.7),
            "only one person",
            (lambda: [*self.cap("only one hand on the receipt at a time", WHITE)], 0.5),
        ])
        hold1 = Line(tills[0].get_right() + 0.05 * RIGHT, [RX - 1.3 - RW / 2 - 0.05, TILL_Y[0], 0], stroke_width=4, color=YELLOW_M)
        hold2 = Line(tills[1].get_right() + 0.05 * RIGHT, [RX - 1.3 - RW / 2 - 0.05, TILL_Y[1], 0], stroke_width=4, color=YELLOW_M)
        line1 = VGroup(left_at(T("refund", 19, GREEN_M), RX - 1.3 - RW / 2 + 0.5, 0.45), right_at(M("60.00", 20, GREEN_M), RX - 1.3 + RW / 2 - 0.3, 0.45))
        tot60 = right_at(M("60.00", 20, GREEN_M), RX - 1.3 + RW / 2 - 0.3, -0.95)
        self.steps("Till one takes the receipt, sees nothing refunded, writes 60.00, and the total becomes 60.00.", [
            (lambda: [*self.uncap(), Create(hold1), paper.animate.set_stroke(YELLOW_M, 3)], 0.6),
            "sees nothing",
            (lambda: [Indicate(rtot[1], color=YELLOW_M)], 0.6),
            "writes 60.00",
            (lambda: [FadeIn(line1, shift=0.1 * RIGHT)], 0.6),
            "and the total",
            (lambda: [swap(rtot[1], tot60)], 0.6),
        ])
        self.steps("Till two gets it next, and 60 more on top of 60 is more than 68.37. Nothing to write.", [
            (lambda: [FadeOut(hold1), Create(hold2)], 0.6),
            "and 60 more",
            (lambda: self.cap("60.00 + 60.00 = 120.00, more than 68.37", RED_M), 0.6),
            "Nothing to write",
            (lambda: [*self.note(1, "nothing to write", GREY_B)], 0.5),
        ])
        slips = VGroup(*[RoundedRectangle(corner_radius=0.04, width=1.3, height=0.32, stroke_color=GOLD_M, stroke_width=1.8).set_fill(
            fillc(GOLD_M, 0.3), 1).move_to([5.3, -0.5 - k * 0.5, 0]).rotate((k - 0.5) * 0.12) for k in range(2)])
        self.steps("The refunds collection was a box of loose slips: anyone can check the box, and anyone can drop a slip in.", [
            (lambda: [FadeOut(hold2), paper.animate.set_stroke(GREY_A, 2.5), *self.uncap(), *self.clear_notes(), FadeIn(sbox), FadeIn(slab)], 0.7),
            "anyone can check",
            (lambda: [dot_to(tills[0].get_right(), sbox.get_left()), dot_to(tills[1].get_right(), sbox.get_left())], 0.8),
            "anyone can drop",
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.3 * DOWN) for s in slips], lag_ratio=0.3)], 0.8),
        ])

        # ---------------- scene 5: one document, one write ----------------
        dbox = framed(DX0, DX1, DOC_T, DOC_B, BLUE_M).set_z_index(-1)
        self.doc = [doc_line(0, '{ _id: "pay-81002", status: "SETTLED",'), doc_line(1, "  amountMinor: 6837,"),
                    doc_line(2, "  refundedMinor: 0,", YELLOW_M), doc_line(3, "  refunds: [ ] }", YELLOW_M)]
        dlab = right_at(T("one document", 19, BLUE_M), DX1 - 0.3, DOC_Y[0])
        self.steps("Version two does what the receipt does. The refunds go inside the payment's document, in a list, next to a running total. "
                   "That's called embedding.", [
            (lambda: [FadeOut(VGroup(sbox, slab, slips, line1, tot60)), receipt.animate.set_opacity(0.0), FadeIn(dbox), FadeIn(self.doc[0]),
                      FadeIn(self.doc[1]), FadeIn(dlab)], 1.0),
            "in a list",
            (lambda: [FadeIn(self.doc[3], shift=0.1 * RIGHT)], 0.6),
            "next to a running total",
            (lambda: [FadeIn(self.doc[2], shift=0.1 * RIGHT)], 0.6),
            "That's called embedding",
            (lambda: [*self.cap("version 2, embedding: the refunds live inside the payment", BLUE_M)], 0.6),
        ])
        self.remove(receipt)
        self.steps("And in MongoDB, a write to one document is atomic: it happens completely or not at all, and no other write slips in halfway.", [
            "is atomic",
            (lambda: [*self.cap("atomic: completely or not at all, and nothing slips in halfway", WHITE), glow(dbox, BLUE_M, 1.01)], 0.8),
        ])
        cbox = framed(DX0, DX1, -0.15, -1.8, GREEN_M, 0.06).set_z_index(-1)
        self.card = [left_at(T("one update, on one document", 20, GREEN_M), DX0 + 0.35, CARD_Y[0]), None, None]
        self.steps("So one update does the check and the change together. It changes the payment only if the total plus this refund "
                   "is at most the amount. Then it adds the refund and raises the total.", [
            (lambda: [*self.uncap(), FadeIn(cbox), FadeIn(self.card[0])], 0.7),
            "only if",
            (lambda: self.set_card(1, "filter: only if refundedMinor + 6000 ≤ amountMinor"), 0.6),
            "Then it adds",
            (lambda: self.set_card(2, "change: add the refund to refunds, and 6000 to refundedMinor"), 0.6),
        ])
        self.steps("Two refunds of 60.00. How many documents does each one change? Pause and guess.", [
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("One, then zero.", [
            (lambda: [*self.uncap(), dot_to(tills[0].get_right(), dbox.get_left() + 0.1 * LEFT), *self.set_card(1, "filter: 0 + 6000 ≤ 6837, yes", GREEN_M)], 0.8),
            (lambda: [*self.set_line(2, "  refundedMinor: 6000,", GREEN_M),
                      *self.set_line(3, '  refunds: [ { refundId: "ref-1", amountMinor: 6000 } ] }', GREEN_M),
                      *self.note(0, "modifiedCount: 1", GREEN_M, mono=True), *self.total("60.00", GREEN_M)], 0.8),
        ], after=0)
        self.steps("The second's filter no longer matches, so it changes nothing. No error, and no lock you had to take.", [
            (lambda: [dot_to(tills[1].get_right(), dbox.get_left() + 0.1 * LEFT), *self.set_card(1, "filter: 6000 + 6000 ≤ 6837? no", RED_M)], 0.8),
            "so it changes nothing",
            (lambda: [*self.note(1, "modifiedCount: 0", GREY_B, mono=True)], 0.6),
            "No error",
            (lambda: [*self.cap("no error, and no lock you had to take", WHITE)], 0.6),
        ])
        self.steps("And the screen gets everything in one read.", [
            (lambda: [dot_to(np.array([DCX, -2.05, 0]), dbox.get_bottom() + 0.1 * UP, WHITE)], 0.9),
        ])

        # ---------------- scene 6: what goes inside? ----------------
        emb = VGroup(T("embed", 22, GREEN_M), T("read together, changed together,", 18), T("stays small: a payment's refunds", 18)).arrange(DOWN, buff=0.12)
        ref = VGroup(T("reference", 22, BLUE_M), T("grows without limit:", 18), T("an account's payments over years", 18)).arrange(DOWN, buff=0.12)
        emb.move_to([DX0 + 2.6, -0.95, 0])
        ref.move_to([DX1 - 2.6, -0.95, 0])
        self.steps("So should everything go inside? No. Embed what's read together, changed together, and stays small. "
                   "A payment has a handful of refunds at most.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(cbox, *[c for c in self.card if c is not None])), *self.clear_notes()], 0.6),
            "Embed what's",
            (lambda: [FadeIn(emb, shift=0.1 * UP)], 0.7),
            "a handful",
            (lambda: [Indicate(self.doc[3], color=GREEN_M, scale_factor=1.03)], 0.8),
        ])
        self.card = [None, None, None]
        self.steps("Reference what grows without limit, like an account's payments over the years. A document can be at most 16 megabytes, "
                   "and a receipt can't be a mile long.", [
            (lambda: [FadeIn(ref, shift=0.1 * UP)], 0.7),
            "at most 16",
            (lambda: self.cap("a document: at most 16 MB", WHITE), 0.6),
            "a mile long",
            (lambda: [Wiggle(ref, scale_value=1.04, rotation_angle=0.02 * TAU)], 0.8),
        ])
        self.steps("And when two things truly can't share a document, like a transfer between two accounts, MongoDB has multi-document "
                   "transactions, since version 4.0. Its own docs say they usually cost more than a one-document write.", [
            "like a transfer",
            (lambda: self.cap("can't share a document? a transfer between two accounts", GREY_B), 0.6),
            "MongoDB has",
            (lambda: self.cap("multi-document transactions, since MongoDB 4.0", WHITE), 0.6),
            "usually cost more",
            (lambda: self.cap("usually cost more than a one-document write", WHITE), 0.6),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, two tills, one payment. Put what must change together inside one document, and one guarded write settles the race.", [
            (lambda: [FadeOut(VGroup(emb, ref)), *self.cap("two tills, one payment", GREY_B)], 0.7),
            "Put what must",
            (lambda: [*self.cap("what must change together lives in one document", YELLOW_M, 28), glow(dbox, BLUE_M, 1.01)], 0.8),
            "one guarded write",
            (lambda: [FadeIn(cbox), *self.set_card(0, "one update, on one document", GREEN_M),
                      *self.set_card(1, "filter: only if refundedMinor + amount ≤ amountMinor")], 0.7),
        ], after=0.5)
        till3 = VGroup(RoundedRectangle(corner_radius=0.08, width=2.6, height=0.46, stroke_color=GOLD_M, stroke_width=2).set_fill(fillc(GOLD_M, 0.25), 1),
                       T("till 3: refund 8.37", 19, GOLD_M)).move_to([TILL_X, -2.25, 0])
        till3[1].move_to(till3[0])
        self.steps("One quick check. After the first refund, a third till tries a refund of 8.37. Does it go through? Pause and think.", [
            (lambda: self.uncap(), 0.4),
            "a third till",
            (lambda: [FadeIn(till3, shift=0.1 * UP)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. 60.00 plus 8.37 is exactly 68.37, and the rule says at most. One document changed, and the payment is fully refunded.", [
            (lambda: [*self.uncap(), *self.set_card(1, "filter: 6000 + 837 ≤ 6837, yes: equal is allowed", GREEN_M)], 0.7),
            "and the rule says",
            (lambda: [Indicate(rule[1], color=YELLOW_M, scale_factor=1.04)], 0.8),
            "One document changed",
            (lambda: [*self.set_line(2, "  refundedMinor: 6837,", GREEN_M),
                      *self.set_line(3, '  refunds: [ { ...6000 }, { amountMinor: 837, ... } ] }', GREEN_M),
                      *self.total("68.37", GREEN_M)], 0.8),
        ], after=0.5)
        self.play(*self.cap("what must change together lives in one document", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
