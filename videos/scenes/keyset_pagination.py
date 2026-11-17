from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    # Kokoro said "one hundred thousand first"; Whisper heard it the same way in isolation.
    (r"\b100,001st\b", "one hundred thousand and first"),
    (r"\bORDER BY\b", "order by"),
    (r"\bOFFSET\b", "offset"),
    (r"\bLIMIT\b", "limit"),
    (r"\bWHERE\b", "where"),
    (r"\bDESC\b", "descending"),
    (r"\bcreated_at\b", "created at"),
    (r"\bpayment_id\b", "payment I D"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_Y = [3.35, 2.95]
DX0, DX1, DY, DH = -6.2, 6.2, 1.75, 0.55       # the index: one long drawer, newest on the left
LBL_Y, UNDER_Y = 2.35, 1.12
N = 1_000_478


def dx(k):
    """x along the drawer of the k-th entry from the newest."""
    return DX0 + (DX1 - DX0) * k / N


CX0, CPITCH, CW, CH, CY = -5.6, 1.15, 0.95, 0.85, -1.0   # the small example's receipt cards
BR_Y = -0.3
TB_HDR, TB_Y = 0.45, [-0.05, -0.55, -1.05]               # the costs table
TB_X0, TB_RE, TB_RT = -5.6, 0.6, 3.6
CAP_Y, BAR_Y = -3.3, -2.85
DATES = {38: "1 Jul", 37: "30 Jun", 36: "19 Jun", 35: "12 Jun", 34: "4 Jun", 33: "28 May", 32: "21 May", 31: "16 May",
         30: "9 May", 29: "2 May", 28: "27 Apr", 27: "19 Apr"}


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
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


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
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def drawer():
    r = Rectangle(width=DX1 - DX0, height=DH, stroke_color=GREY_B, stroke_width=2.5).set_fill("#101214", 1).move_to([0, DY, 0])
    ticks = VGroup(*[Line([x, DY - DH / 2 + 0.08, 0], [x, DY + DH / 2 - 0.08, 0], stroke_width=1.2, color=GREY_D)
                     for x in np.linspace(DX0 + 0.06, DX1 - 0.06, 160)])
    return VGroup(r, ticks)


def span(k0, k1, color, minw=0.0):
    x0, x1 = dx(k0), max(dx(k1), dx(k0) + minw)
    return Rectangle(width=x1 - x0, height=DH - 0.04, stroke_width=0).set_fill(color, 0.55).move_to([(x0 + x1) / 2, DY, 0])


def finger(x):
    return Line([x, DY - DH / 2 - 0.12, 0], [x, DY + DH / 2 + 0.12, 0], stroke_width=5, color=YELLOW_M)


def cx(k):
    return CX0 + CPITCH * k


def card(p, k, color=GREY_C):
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=color, stroke_width=2.5).set_fill("#101214", 1)
    r.move_to([cx(k), CY, 0])
    return VGroup(r, M(str(p), 26).move_to([cx(k), CY + 0.14, 0]), T(DATES[p], 15, GREY_B).move_to([cx(k), CY - 0.23, 0]))


def bracket(k0, k1, label, color):
    x0, x1 = cx(k0) - CW / 2 + 0.05, cx(k1) + CW / 2 - 0.05
    ln = VGroup(Line([x0, BR_Y, 0], [x1, BR_Y, 0]), Line([x0, BR_Y, 0], [x0, BR_Y - 0.13, 0]),
                Line([x1, BR_Y, 0], [x1, BR_Y - 0.13, 0])).set_stroke(color, 3)
    return VGroup(ln, T(label, 20, color).move_to([(x0 + x1) / 2, BR_Y + 0.27, 0]))


def tab_for(c):
    r = c[0]
    t = RoundedRectangle(corner_radius=0.04, width=0.22, height=0.32, stroke_width=0).set_fill(YELLOW_M, 1)
    return t.move_to(r.get_corner(UR) + np.array([-0.12, 0.08, 0]))


def phone():
    c, w, h = np.array([0, 0.1, 0]), 3.8, 5.3
    body = RoundedRectangle(corner_radius=0.3, width=w, height=h, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    screen = RoundedRectangle(corner_radius=0.14, width=w - 0.3, height=h - 0.7, stroke_width=0).set_fill("#15191d", 1).move_to(c)
    slot = Line(c + [-0.3, h / 2 - 0.18, 0], c + [0.3, h / 2 - 0.18, 0], stroke_width=3, color=GREY_C)
    return VGroup(body, screen, slot, T("your payments, newest first", 18, GREY_B).move_to(c + [0, 1.95, 0]))


PH_ROWS = [1.25, 0.6, -0.05, -0.7, -1.35]


def ph_row(y, coffee=False):
    if coffee:
        return VGroup(left_at(T("coffee", 22), -1.45, y), right_at(M("17.20", 22), 1.45, y))
    bar = RoundedRectangle(corner_radius=0.06, width=1.5, height=0.18, stroke_width=0).set_fill(GREY_D, 1)
    return VGroup(left_at(bar, -1.45, y), right_at(RoundedRectangle(corner_radius=0.06, width=0.6, height=0.18, stroke_width=0)
                                                  .set_fill(GREY_D, 1), 1.45, y))


def ph_page(rows_coffee_at=None):
    return VGroup(*[ph_row(y, coffee=(i == rows_coffee_at)) for i, y in enumerate(PH_ROWS)])


class KeysetPagination(Base):
    """sql-08, section 3 (and the fix it points to). A list of payments, newest first, 20 a page: far pages are slow
    and a coffee shows up twice. LIMIT 20 OFFSET 100000 reads 100,020 index entries to return 20, because the index is
    a drawer of receipts with no positions written on them. Five per page on the seed: a new payment pushes 33 onto
    page 2 again. A tab behind the last receipt shown (the cursor) and a row comparison: one trip down, no shift.
    The price, the moral, and a check with a deleted row."""

    def counter(self, vt, x_of):
        return always_redraw(lambda: M(f"{int(vt.get_value()):,}", 22, WHITE).move_to([x_of(), UNDER_Y, 0]))

    def set_plab(self, s):
        new = T(s, 20, GREY_B).move_to([0, -2.0, 0])
        old, self.plab = self.plab, new
        return [swap(old, new)]

    def set_seen(self, p, s, color=GREY_B):
        new = T(s, 16, color).move_to(self.cards[p][0].get_bottom() + 0.22 * DOWN)
        old, self.seen[p] = self.seen.get(p), new
        return [swap(old, new)]

    def drop_seen(self, *ps):
        out = [FadeOut(self.seen.pop(p)) for p in ps if p in self.seen]
        return out

    def shift_cards(self, ps, d):
        out = []
        for p in ps:
            out.append(self.cards[p].animate.shift(d))
            if p in self.seen:
                out.append(self.seen[p].animate.shift(d))
        return out

    def construct(self):
        self.capm = self.plab = None
        self.seen = {}
        self.title_card("Why is page 5,001 slow?", "OFFSET counts its way there; a cursor opens at the tab")

        # ---------------- scene 1: the list on your phone ----------------
        ph = phone()
        pg = ph_page()
        spin = Arc(radius=0.35, start_angle=0, angle=1.5 * PI, stroke_width=5, color=YELLOW_M).move_to([0, 0.0, 0])
        self.steps("Picture scrolling back through your card payments on your phone, newest first, 20 at a time. "
                   "The first pages appear at once. Far back in the list, each new page takes a little longer.", [
            (lambda: [FadeIn(ph, shift=0.2 * UP)], 0.8),
            "newest first",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * UP) for r in pg], lag_ratio=0.15), *self.set_plab("page 1")], 0.9),
            "The first pages",
            (lambda: self.set_plab("page 2"), 0.4),
            (lambda: self.set_plab("page 3"), 0.4),
            "Far back",
            (lambda: [*self.set_plab("page 5,001"), FadeOut(pg)], 0.5),
            (lambda: [FadeIn(spin)], 0.2),
            (lambda: [Rotate(spin, -2 * TAU, rate_func=linear)], 1.6),
        ])
        pg2 = ph_page(rows_coffee_at=4)
        pg3 = ph_page(rows_coffee_at=0)
        self.steps("And once, a coffee you saw a moment ago turns up again at the top of the next page.", [
            (lambda: [FadeOut(spin), LaggedStart(*[FadeIn(r, shift=0.1 * UP) for r in pg2], lag_ratio=0.1)], 0.8),
            "turns up again",
            (lambda: [FadeOut(pg2, shift=0.6 * UP), FadeIn(pg3, shift=0.6 * UP)], 0.7),
            (lambda: [pg3[0].animate.set_color(RED_M)], 0.5),
        ])
        self.steps("So why does page 5,001 cost more than page 1? And where did that second coffee come from?", [
            (lambda: self.cap("why does page 5,001 cost more than page 1?", WHITE), 0.5),
            "And where",
            (lambda: self.cap("and where did the second coffee come from?", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 2: the obvious query ----------------
        q1 = M("SELECT payment_id, created_at, amount_minor FROM payments", 22).move_to([0, Q_Y[0], 0])
        parts = VGroup(M("ORDER BY created_at DESC, payment_id DESC", 22), M("LIMIT 20", 22), M("OFFSET 100000", 22))
        parts.arrange(RIGHT, buff=0.22).move_to([0, Q_Y[1], 0])
        self.q = VGroup(q1, parts)
        self.steps("Behind a list like that, the app asks the database for one page at a time. "
                   "The obvious way: sort newest first, skip the pages before this one, and keep 20.", [
            (lambda: [FadeOut(VGroup(ph, pg3, self.plab)), *self.uncap()], 0.8),
            "The obvious way",
            (lambda: [FadeIn(q1, shift=0.1 * DOWN)], 0.6),
            "sort newest",
            (lambda: [*self.cap("sort newest first", WHITE)], 0.4),
            "skip the pages",
            (lambda: self.cap("skip the pages before this one", WHITE), 0.4),
            "and keep 20",
            (lambda: self.cap("keep 20", WHITE), 0.4),
        ])
        self.steps("In SQL, ORDER BY created_at DESC sorts newest first, and payment_id breaks ties. "
                   "LIMIT 20 keeps 20 rows. And OFFSET 100,000 skips the first 100,000. That's page 5,001.", [
            (lambda: [FadeIn(parts[0], shift=0.1 * DOWN), *self.cap("newest first; payment_id breaks ties")], 0.6),
            "LIMIT 20",
            (lambda: [FadeIn(parts[1], shift=0.1 * DOWN), *self.cap("keep 20 rows")], 0.5),
            "And OFFSET",
            (lambda: [FadeIn(parts[2], shift=0.1 * DOWN), *self.cap("skip the first 100,000 rows")], 0.5),
            "That's page",
            (lambda: [Indicate(parts[2], color=YELLOW_M, scale_factor=1.08), *self.cap("page 5,001", WHITE)], 0.7),
        ])

        # ---------------- scene 3: a million rows, and a guess ----------------
        dr = drawer()
        dlab = right_at(T("the index: 1,000,478 entries, newest first", 20, GREY_B), DX1, LBL_Y)
        thd = VGroup(left_at(T("page", 18, GREY_B), TB_X0, TB_HDR), right_at(T("entries read", 18, GREY_B), TB_RE, TB_HDR),
                     right_at(T("time", 18, GREY_B), TB_RT, TB_HDR))

        def trow(k, label, read, tm, color=WHITE):
            y = TB_Y[k]
            return VGroup(left_at(T(label, 24), TB_X0, y), right_at(M(read, 24, color), TB_RE, y), right_at(M(tm, 24, color), TB_RT, y))

        r1 = trow(0, "page 1", "20", "0.15 ms", GREEN_M)
        g1 = span(0, 20, GREEN_M, 0.12)
        self.steps("Let's run it on a table of a million payments, with an index: a separate list of each payment's time and number, "
                   "kept in order, each pointing to its row.", [
            (lambda: self.uncap(), 0.3),
            "with an index",
            (lambda: [FadeIn(dr), FadeIn(dlab)], 0.9),
            "kept in order",
            (lambda: [*self.cap("each entry: a time, a payment number, and where its row lives")], 0.5),
        ])
        self.steps("Page 1 reads the newest 20 entries and stops. A fraction of a millisecond.", [
            (lambda: [*self.uncap(), FadeIn(g1), FadeIn(thd)], 0.6),
            "A fraction",
            (lambda: [FadeIn(r1, shift=0.1 * UP)], 0.6),
        ])
        q_read = M("?", 26, YELLOW_M).move_to([TB_RE - 0.2, TB_Y[1], 0])
        r2 = trow(1, "page 5,001", "100,020", "about 50 ms", RED_M)
        r2l = r2[0]
        self.steps("Page 5,001 also returns 20 rows. So how many entries does it read? Pause and guess.", [
            (lambda: [FadeIn(r2l)], 0.5),
            "how many",
            (lambda: [FadeIn(q_read, scale=0.6)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        vt = ValueTracker(0)
        fx = lambda: dx(vt.get_value())
        fing = always_redraw(lambda: finger(fx()))
        cnt = self.counter(vt, lambda: max(fx(), DX0 + 0.6))
        red = always_redraw(lambda: span(0, max(vt.get_value(), 1), RED_M))
        g2 = span(100000, 100020, GREEN_M, 0.12)
        kept = left_at(T("20 kept", 20, GREEN_M), dx(100000) + 0.25, LBL_Y)
        self.steps("100,020. It starts at the newest entry, walks through 100,000 of them, fetches each row, and throws them all away. "
                   "Then it keeps the next 20. About 50 milliseconds.", [
            (lambda: [*self.uncap(), FadeOut(q_read), FadeOut(g1), FadeOut(dlab)], 0.4),
            "It starts",
            (lambda: [FadeIn(fing), FadeIn(cnt), FadeIn(red)], 0.3),
            "walks through",
            (lambda: [vt.animate.set_value(100000)], 2.2),
            "throws them all away",
            (lambda: [*self.cap("100,000 read, and thrown away", RED_M)], 0.5),
            "Then it keeps",
            (lambda: [FadeIn(g2), FadeIn(kept)], 0.5),
            "About 50",
            (lambda: [FadeIn(r2[1:])], 0.6),
        ])
        r3 = trow(2, "page 45,001", "900,020", "1.2 s", RED_M)
        self.steps("Page 45,001 reads 900,020 rows, and takes 1.2 seconds. Same 20 rows out, every time. The cost grows with the page number.", [
            (lambda: [FadeOut(g2), FadeOut(kept), FadeIn(r3[0]), *self.uncap()], 0.4),
            (lambda: [vt.animate.set_value(900000)], 2.0),
            (lambda: [FadeIn(r3[1:])], 0.5),
            "The cost grows",
            (lambda: [*self.cap("same 20 rows out; the cost grows with the page number", WHITE)], 0.5),
        ], after=0.4)

        # ---------------- scene 4: the drawer ----------------
        dlab2 = right_at(T("a drawer of receipts, filed by time", 20, GREY_B), DX1, LBL_Y)
        rc_t = VGroup(T("a time", 18), T("a payment number", 18), T("→ its row", 18)).arrange(RIGHT, buff=0.3)
        rc = RoundedRectangle(corner_radius=0.08, width=rc_t.width + 0.5, height=0.5, stroke_color=GREY_B, stroke_width=2).set_fill("#101214", 1)
        receipt = VGroup(rc, rc_t.move_to(rc)).move_to([-2.5, LBL_Y, 0])
        nopos = T("no position written on it", 20, RED_M).next_to(receipt, RIGHT, buff=0.35)
        self.steps("Why can't it jump? Picture the payments as receipts, filed in one long drawer by time. "
                   "Someone asks for the 100,001st receipt.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(thd, r1, r2, r3)), vt.animate.set_value(0)], 0.8),
            "Picture the payments",
            (lambda: [FadeIn(dlab2), LaggedStart(*[t.animate(rate_func=there_and_back).set_color(WHITE) for t in dr[1][:40]], lag_ratio=0.02)], 1.2),
            "Someone asks",
            (lambda: self.cap("hand me receipt 100,001", WHITE), 0.5),
        ])
        self.steps("No receipt has its position written on it, so you count from the front. One, two, three... and you're still counting at lunch.", [
            (lambda: [FadeOut(dlab2), FadeIn(receipt, shift=0.1 * DOWN)], 0.5),
            "No receipt",
            (lambda: [FadeIn(nopos)], 0.5),
            "you count",
            (lambda: [vt.animate.set_value(3)], 0.6),
            "still counting",
            (lambda: [vt.animate(rate_func=linear).set_value(60000)], 2.0),
        ])
        self.steps("The index is that drawer. Each entry holds a time, a payment number, and where its row lives. Not a position. "
                   "So to skip 100,000 entries, PostgreSQL reads them.", [
            (lambda: [*self.cap("a receipt = an index entry; the drawer = the index", WHITE)], 0.5),
            "Each entry",
            (lambda: [glow(rc, WHITE, 1.04)], 0.7),
            "Not a position",
            (lambda: [Indicate(nopos, color=RED_M)], 0.6),
            "So to skip",
            (lambda: [vt.animate.set_value(100000)], 1.0),
        ])
        self.steps("Its manual says so: rows skipped by OFFSET still have to be worked out.", [
            (lambda: self.cap("PostgreSQL's manual: rows skipped by OFFSET still have to be worked out"), 0.6),
            (lambda: [Indicate(parts[2], color=RED_M, scale_factor=1.08)], 0.8),
        ])
        self.steps("The drawer picture breaks here. A person could at least open the drawer near the middle, by feel. "
                   "An index can't even guess.", [
            (lambda: self.cap("where the drawer picture breaks"), 0.5),
            "A person",
            (lambda: [*self.cap("a person: opens near the middle, by feel"), FadeOut(receipt), FadeOut(nopos)], 0.5),
            "An index",
            (lambda: [*self.cap("an index: can't even guess", WHITE)], 0.5),
        ], after=0.4)

        # ---------------- scene 5: the second coffee ----------------
        order = [37, 36, 35, 34, 33, 32, 31, 30, 29, 28]
        cards = self.cards = {p: card(p, k) for k, p in enumerate(order)}
        b1 = bracket(0, 4, "page 1", WHITE)
        self.steps("OFFSET has a second problem. Let's shrink it to five per page, on the course's small table. Page 1 shows payments 37 down to 33.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(fing, cnt, red)), FadeIn(dlab)], 0.6),
            "Let's shrink",
            (lambda: [LaggedStart(*[FadeIn(cards[p], shift=0.1 * DOWN) for p in order], lag_ratio=0.08)], 1.2),
            "Page 1 shows",
            (lambda: [FadeIn(b1), *[a for p in order[:5] for a in self.set_seen(p, "seen")]], 0.8),
        ])
        self.remove(fing, cnt, red)
        c38 = card(38, 0, YELLOW_M)
        b2 = bracket(5, 9, "page 2: OFFSET 5", RED_M)
        bsk = bracket(0, 4, "skipped", GREY_B)
        self.steps("While you read it, a new payment arrives: 38. Everything slides back one place.", [
            "a new payment",
            (lambda: [*self.shift_cards(order, RIGHT * CPITCH), FadeIn(c38, shift=0.6 * RIGHT)], 0.9),
        ])
        self.steps("Page 2 skips the first five rows, which are now 38 down to 34, so it starts at 33. Payment 33, a second time. That's the coffee.", [
            (lambda: [FadeOut(b1)], 0.4),
            "Page 2 skips",
            (lambda: [FadeIn(bsk)], 0.5),
            "so it starts",
            (lambda: [FadeIn(b2)], 0.5),
            "a second time",
            (lambda: [cards[33][0].animate.set_stroke(RED_M, 4), *self.set_seen(33, "again", RED_M)], 0.6),
        ])
        self.steps("A deleted row does the opposite: the next page skips a row nobody saw. "
                   "A nightly copy, page by page, can copy a payment twice or miss one, with no error.", [
            (lambda: self.cap("a deleted row: the next page skips a row nobody saw"), 0.5),
            "A nightly copy",
            (lambda: self.cap("a nightly copy, page by page: a payment twice, or one missed, and no error", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 6: the tab ----------------
        tab = tab_for(cards[33])
        self.steps("So here's the wish. The screen already knows where the last page ended: the last row it showed. "
                   "In the drawer, clip a tab behind the last receipt you handed over. Next time, open the drawer at the tab.", [
            (lambda: [*self.uncap(), FadeOut(b2), FadeOut(bsk)], 0.5),
            "the last row it showed",
            (lambda: [glow(cards[33][0], YELLOW_M, 1.05)], 0.8),
            "clip a tab",
            (lambda: [FadeIn(tab, shift=0.2 * DOWN), *self.cap("a tab behind the last receipt you handed over", YELLOW_M)], 0.6),
            "Next time",
            (lambda: self.cap("next time: open the drawer at the tab", YELLOW_M), 0.5),
        ])

        # ---------------- scene 7: the cursor, and the seek ----------------
        k1 = M("WHERE (created_at, payment_id) < (:last_created_at, :last_payment_id)", 20, YELLOW_M).move_to([0, Q_Y[0], 0])
        k2 = M("ORDER BY created_at DESC, payment_id DESC LIMIT 20", 20).move_to([0, Q_Y[1], 0])
        self.steps("In SQL, the tab is called a cursor: the last row's sort values, its created_at and its payment_id. "
                   "The next page asks for the rows after it: WHERE the pair is less than the cursor's two values.", [
            (lambda: [*self.cap("the tab: a cursor, the sort values of the last row shown", YELLOW_M)], 0.6),
            "its created_at",
            (lambda: [Indicate(cards[33][2], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "its payment_id",
            (lambda: [Indicate(cards[33][1], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "The next page",
            (lambda: [Succession(FadeOut(self.q), FadeIn(VGroup(k1, k2)))], 1.0),
        ])
        self.steps("PostgreSQL compares the pairs left to right, the way you'd compare two dates: the year first, and the day only if the years match. "
                   "Because the list is newest first, less means further down.", [
            (lambda: self.cap("compare left to right: created_at first, payment_id only on a tie", WHITE), 0.5),
            "Because the list",
            (lambda: self.cap("newest first: less means further down the list"), 0.5),
        ])
        b3 = bracket(6, 10, "page 2: after the tab", GREEN_M)
        self.steps("Back to our five. Page 2 is 32 down to 28. No repeat. And the new payment sorts before the tab, so it shows up on page 1.", [
            (lambda: self.uncap(), 0.3),
            "Page 2 is",
            (lambda: [FadeIn(b3), *[cards[p][0].animate.set_stroke(GREEN_M, 3) for p in (32, 31, 30, 29, 28)]], 0.8),
            "No repeat",
            (lambda: [cards[33][0].animate.set_stroke(GREY_C, 2.5), *self.set_seen(33, "seen")], 0.6),
            "And the new",
            (lambda: [glow(c38[0], YELLOW_M, 1.05), *self.cap("payment 38 sorts before the tab: it's on page 1")], 0.8),
        ])
        tx = dx(100000)
        dtab = RoundedRectangle(corner_radius=0.04, width=0.16, height=0.3, stroke_width=0).set_fill(YELLOW_M, 1).move_to([tx, DY + DH / 2 + 0.08, 0])
        seek = Arrow([tx, 2.85, 0], [tx, DY + DH / 2 + 0.28, 0], buff=0, stroke_width=4, color=YELLOW_M, max_tip_length_to_length_ratio=0.35)
        seek_lab = left_at(T("one trip down, to the tab", 20, YELLOW_M), tx + 0.3, LBL_Y)
        g3 = span(100000, 100020, GREEN_M, 0.12)
        kstat = left_at(T("tab, page 5,001: 20 entries read, 0.7 ms", 22, GREEN_M), tx + 0.3, UNDER_Y)
        self.steps("On the million rows, PostgreSQL goes down the index once, straight to the tab, and reads the next 20 entries. "
                   "Under a millisecond, on page 2 or on page 5,001. This is called keyset pagination.", [
            (lambda: [*self.uncap(), FadeOut(dlab), FadeIn(dtab, shift=0.2 * DOWN)], 0.5),
            "goes down the index once",
            (lambda: [GrowArrow(seek), FadeIn(seek_lab)], 0.7),
            "reads the next 20",
            (lambda: [FadeIn(g3)], 0.5),
            "Under a millisecond",
            (lambda: [FadeIn(kstat, shift=0.1 * UP)], 0.6),
            "This is called",
            (lambda: self.cap("keyset pagination: find the page by its key", YELLOW_M), 0.5),
        ], after=0.4)

        # ---------------- scene 8: the price ----------------
        self.steps("It has a price. You give up page numbers: a cursor moves one page at a time, so no jumping to page 4,000. "
                   "For an endless scroll, or a nightly export, that costs nothing.", [
            (lambda: self.cap("the price: no page numbers, one page at a time", WHITE), 0.5),
            "For an endless",
            (lambda: self.cap("an endless scroll, a nightly export: no loss"), 0.5),
        ])
        self.steps("Two details decide whether it's right. The sort must be unique, which is why payment_id is in it. "
                   "And the WHERE must compare both values. Compare created_at alone, and payments at the tab's exact time are skipped, with no error.", [
            "The sort must",
            (lambda: [*self.cap("1. a unique sort: payment_id breaks ties", WHITE), Indicate(k2, color=WHITE, scale_factor=1.04)], 0.7),
            "And the WHERE must",
            (lambda: [*self.cap("2. compare both values, not created_at alone", WHITE), Indicate(k1, color=YELLOW_M, scale_factor=1.04)], 0.7),
            "Compare created_at alone",
            (lambda: self.cap("created_at alone: every payment at the tab's exact time is skipped", RED_M), 0.5),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, why was page 5,001 slow, and where did the second coffee come from? OFFSET counts its way to a page, through every row before it. "
                   "That gets slower, and it shifts when rows come and go. Find the page by a key instead.", [
            (lambda: self.cap("why slow? where did the second coffee come from?", WHITE), 0.5),
            "OFFSET counts",
            (lambda: [*self.cap("OFFSET counts its way there, through every row before it", WHITE), Indicate(kstat, color=GREEN_M, scale_factor=1.03)], 0.6),
            "Find the page",
            (lambda: self.cap("counting gets slower and shifts; find the page by a key", YELLOW_M), 0.5),
        ])
        c27 = card(27, 9)
        self.steps("One quick check. Start again: page 1 shows 37 down to 33. This time, payment 35 is deleted.", [
            (lambda: [*self.uncap(), FadeOut(b3), FadeOut(c38), FadeOut(tab),
                      *[cards[p][0].animate.set_stroke(GREY_C, 2.5) for p in order]], 0.5),
            (lambda: self.shift_cards(order, LEFT * CPITCH), 0.8),
            "This time",
            (lambda: [cards[35][0].animate.set_stroke(RED_M, 3)], 0.4),
            (lambda: [FadeOut(cards[35]), *self.drop_seen(35), *self.shift_cards(order[3:], LEFT * CPITCH), FadeIn(c27, shift=0.6 * LEFT)], 0.9),
        ])
        b4 = bracket(5, 9, "page 2: OFFSET 5", RED_M)
        self.steps("With OFFSET 5, which payment does nobody ever see? Pause and think.", [
            (lambda: [FadeIn(b4)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        b5 = bracket(4, 8, "page 2: after the tab", GREEN_M)
        tab2 = tab_for(cards[33])
        self.steps("32. Page 2 skips five rows, and 32 is now the fifth. With the tab behind 33, page 2 starts at 32 anyway.", [
            (lambda: [*self.uncap(), cards[32][0].animate.set_stroke(RED_M, 4), *self.set_seen(32, "never shown", RED_M)], 0.6),
            "With the tab",
            (lambda: [FadeOut(b4), FadeIn(tab2, shift=0.2 * DOWN)], 0.5),
            "page 2 starts",
            (lambda: [FadeIn(b5), cards[32][0].animate.set_stroke(GREEN_M, 4), *self.set_seen(32, "page 2", GREEN_M)], 0.7),
        ], after=0.3)
        self.play(*self.cap("find the page by a key, not by counting", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
