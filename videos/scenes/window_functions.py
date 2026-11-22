from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz" (Whisper hears "posters"); spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\b189\.99\b", "one eighty-nine ninety-nine"),
    # Kokoro drops the possessive after a digit ("shop 4's" comes out as "shop four"); say the digit as a word.
    (r"\b([1-9])'s\b", lambda m: "one two three four five six seven eight nine".split()[int(m.group(1)) - 1] + "'s"),
    (r"\bpayment_id\b", "payment I D"),
    (r"\bmerchant_id\b", "merchant I D"),
    (r"\bPARTITION BY\b", "partition by"),
    (r"\bGROUP BY\b", "group by"),
    (r"\bOVER\b", "over"),
]

# ---- the data: the eight succeeded March payments (the lesson's stepper and Try it) ----
ID_ORDER = [13, 14, 16, 17, 18, 19, 21, 22]
SHOP = {13: 5, 14: 1, 16: 5, 17: 4, 18: 4, 19: 4, 21: 7, 22: 5}
AMT = {13: 64000, 14: 5310, 16: 31500, 17: 18999, 18: 18999, 19: 18999, 21: 1325, 22: 52000}
TOTAL = {1: 5310, 4: 56997, 5: 147500, 7: 1325}
PCT = {13: "43.4", 14: "100.0", 16: "21.4", 17: "33.3", 18: "33.3", 19: "33.3", 21: "100.0", 22: "35.3"}
BLOCKS = [(1, [14]), (4, [17, 18, 19]), (5, [13, 16, 22]), (7, [21])]
SHOP_ORDER = [p for _, ps in BLOCKS for p in ps]
COL = {1: BLUE_M, 4: GOLD_M, 5: TEAL_M, 7: PURPLE_M}

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_Y = [3.35, 2.95]
HDR_Y = 2.32
ROW_H, PITCH, GAP = 0.42, 0.5, 0.16
Y_ID = {p: 1.8 - PITCH * i for i, p in enumerate(ID_ORDER)}
Y_SHOP = {}
_y = 1.8
for _k, (_, _ps) in enumerate(BLOCKS):
    for _p in _ps:
        Y_SHOP[_p] = _y
        _y -= PITCH
    _y -= GAP
PX0, PX1 = -6.05, 0.05                    # a slip (one row, drawn as a paper)
C_PID, C_SHOP, R_AMT, R_TOT, R_PCT = -5.5, -4.45, -2.85, -0.4, 1.25
BAR_X, MARK_X = -6.25, -6.36
RP_X = 1.0                                # the right panel's left edge
TALK_Y = [2.0, 1.45, 0.9, 0.35]        # the right panel's upper lines
GB_Y = [-0.6, -1.1, -1.6, -2.1]           # the GROUP BY lines (lower right)
GB_CX, GB_W = 3.8, 4.5
CAP_Y, BAR_Y = -3.25, -2.78


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

    def cap(self, s, color=GREY_B, size=24, mono=False):
        new = fit((M if mono else T)(s, size, color), 12.6).move_to([0, CAP_Y, 0])
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
def slip(p, y):
    r = RoundedRectangle(corner_radius=0.08, width=PX1 - PX0, height=ROW_H, stroke_color=GREY_C, stroke_width=2)
    r.set_fill("#101214", 1).move_to([(PX0 + PX1) / 2, y, 0])
    return VGroup(r, M(str(p), 22).move_to([C_PID, y, 0]), M(f"m{SHOP[p]}", 22, COL[SHOP[p]]).move_to([C_SHOP, y, 0]),
                  right_at(M(str(AMT[p]), 22), R_AMT, y))


def corner(y):
    """The folded corner that turns a slip into an exam paper."""
    f = 0.16
    x, t = PX1, y + ROW_H / 2
    return Polygon([x - f, t, 0], [x, t - f, 0], [x - f, t - f, 0], stroke_color=GREY_C, stroke_width=1.5).set_fill(GREY_D, 1)


def headers():
    return VGroup(T("payment", 18, GREY_B).move_to([C_PID, HDR_Y, 0]), T("shop", 18, GREY_B).move_to([C_SHOP, HDR_Y, 0]),
                  right_at(T("amount", 18, GREY_B), R_AMT, HDR_Y), right_at(M("merchant_total", 16, GREY_B), R_TOT, HDR_Y))


def tot_text(v, y, color=WHITE):
    return right_at(M(str(v), 22, color), R_TOT, y)


def query(l1, l2, c1=None, c2=None):
    a = M(l1, 22, t2c=c1 or {})
    b = M(l2, 22, t2c=c2 or {})
    return VGroup(a.move_to([0, Q_Y[0], 0]), b.move_to([0, Q_Y[1], 0]))


def win_frame(ys, color=YELLOW_M):
    top, bot = max(ys) + ROW_H / 2 + 0.07, min(ys) - ROW_H / 2 - 0.07
    return Rectangle(width=PX1 - PX0 + 0.16, height=top - bot, stroke_color=color, stroke_width=4).move_to(
        [(PX0 + PX1) / 2, (top + bot) / 2, 0])


def marker(y):
    return Triangle(stroke_width=0).set_fill(YELLOW_M, 1).rotate(-PI / 2).scale(0.13).move_to([MARK_X - 0.08, y, 0])


def talk(s, k, color=WHITE, size=24, mono=False):
    return left_at((M if mono else T)(s, size, color), RP_X, TALK_Y[k])


def gb_line(k):
    shop, y = BLOCKS[k][0], GB_Y[k]
    r = RoundedRectangle(corner_radius=0.08, width=GB_W, height=ROW_H, stroke_color=COL[shop], stroke_width=2.5)
    r.set_fill(fillc(COL[shop]), 1).move_to([GB_CX, y, 0])
    return VGroup(r, M(f"m{shop}", 20, COL[shop]).move_to([GB_CX - GB_W / 2 + 0.4, y, 0]),
                  right_at(M(str(TOTAL[shop]), 20), GB_CX - 0.1, y))


def phone():
    c, w, h = np.array([0, 0.15, 0]), 4.6, 5.2
    body = RoundedRectangle(corner_radius=0.3, width=w, height=h, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    screen = RoundedRectangle(corner_radius=0.14, width=w - 0.3, height=h - 0.7, stroke_width=0).set_fill("#15191d", 1).move_to(c)
    slot = Line(c + [-0.3, h / 2 - 0.18, 0], c + [0.3, h / 2 - 0.18, 0], stroke_width=3, color=GREY_C)
    title = T("your bank app", 20, GREY_B).move_to(c + [0, 1.75, 0])
    return VGroup(body, screen, slot, title)


def charge(y, when):
    x0, x1 = -1.95, 1.95
    g = VGroup(left_at(T("Volt Electronics", 22), x0, y + 0.18), right_at(M("-189.99", 24), x1, y + 0.18),
               left_at(T(f"12 March, {when}", 17, GREY_B), x0, y - 0.22))
    return g


class WindowFunctions(Base):
    """sql-06, section 0. A double charge in a bank app sets the question: how do you put a number worked out from many
    rows onto every row? The eight succeeded March payments; GROUP BY folds them into four lines and refuses
    payment_id. The teacher marking exam papers; OVER (PARTITION BY merchant_id) keeps every row and writes the shop's
    total on each. Names, the share, the cost of the sort, the moral, and a check with OVER ()."""

    def rowparts(self, p):
        return [m for m in (self.rows[p], self.tot.get(p), self.pct.get(p)) if m is not None]

    def move_rows(self, ymap):
        anims = []
        for p, y in ymap.items():
            dy = y - self.y[p]
            anims += [m.animate.shift(dy * UP) for m in self.rowparts(p)]
            self.y[p] = y
        return anims

    def set_talk(self, k, s, color=WHITE, size=24, mono=False):
        new = talk(s, k, color, size, mono)
        old, self.tk[k] = self.tk[k], new
        return [swap(old, new)]

    def drop_talk(self, *ks):
        out = [FadeOut(self.tk[k]) for k in ks if self.tk[k] is not None]
        for k in ks:
            self.tk[k] = None
        return out

    def clear_talk(self):
        olds = [m for m in self.tk if m is not None]
        self.tk = [None] * 4
        return [FadeOut(m) for m in olds]

    def set_tot(self, p, v, color=WHITE):
        new = tot_text(v, self.y[p], color)
        old, self.tot[p] = self.tot.get(p), new
        return [swap(old, new, RIGHT)]

    def set_query(self, q):
        old, self.q = self.q, q
        if old is None:
            return [FadeIn(q)]
        return [Succession(FadeOut(old), FadeIn(q))]

    def construct(self):
        self.capm = self.q = None
        self.tk = [None] * 4
        self.tot, self.pct = {}, {}
        self.title_card("Every row keeps its place", "window functions: a window instead of a group")

        # ---------------- scene 1: the double charge ----------------
        ph = phone()
        c1, c2 = charge(0.75, "16:40"), charge(-0.45, "16:42")
        self.steps("Picture yourself scrolling through your bank app, and stopping. The same 189.99, at the same electronics shop, "
                   "twice, two minutes apart. You were charged twice.", [
            (lambda: [FadeIn(ph, shift=0.2 * UP)], 0.8),
            "The same",
            (lambda: [FadeIn(c1, shift=0.1 * DOWN)], 0.6),
            "twice",
            (lambda: [FadeIn(c2, shift=0.1 * DOWN)], 0.6),
            "You were charged",
            (lambda: [c1[1].animate.set_color(RED_M), c2[1].animate.set_color(RED_M)], 0.6),
        ])
        qm = T("?", 72, YELLOW_M).move_to([3.6, 0.2, 0])
        self.steps("Support promises a refund, and to find every other customer it happened to. "
                   "For that, the database must keep every payment, and write something next to each one.", [
            "every other customer",
            (lambda: self.cap("find every other customer this happened to"), 0.5),
            "keep every payment",
            (lambda: self.cap("keep every payment, and write something next to each one"), 0.5),
        ])
        self.steps("So how do you put a number worked out from many rows onto every row, and lose none of them? "
                   "Keep that double charge in mind.", [
            (lambda: [FadeIn(qm, scale=0.6), *self.cap("a number from many rows, on every row?", WHITE)], 0.6),
            "Keep that",
            (lambda: [Indicate(c1, color=GOLD_M, scale_factor=1.05), Indicate(c2, color=GOLD_M, scale_factor=1.05)], 1.0),
        ])

        # ---------------- scene 2: meet the rows ----------------
        hd = headers()
        self.rows = {p: slip(p, Y_ID[p]) for p in ID_ORDER}
        self.y = dict(Y_ID)
        tname = T("payments, March, succeeded", 20, GREY_B).move_to([(PX0 + PX1) / 2, Q_Y[1], 0])
        self.steps("Let's start smaller. The company's app keeps each payment as one row in a table called payments, "
                   "like one line in a spreadsheet. Here are the eight that succeeded in March.", [
            (lambda: [FadeOut(VGroup(ph, c1, c2, qm)), *self.uncap()], 0.8),
            "one row",
            (lambda: [FadeIn(self.rows[13], shift=0.15 * DOWN)], 0.6),
            "Here are",
            (lambda: [FadeIn(tname), FadeIn(hd[:3]),
                      LaggedStart(*[FadeIn(self.rows[p], shift=0.15 * DOWN) for p in ID_ORDER[1:]], lag_ratio=0.15)], 1.4),
        ])
        self.steps("Each row has the payment's number, the shop that was paid, and the amount in cents. So 18999 means 189.99. "
                   "And there's our double charge: payments 17 and 18, at shop 4, Volt Electronics.", [
            (lambda: [Indicate(hd[0], color=WHITE)], 0.6),
            "the shop",
            (lambda: [Indicate(hd[1], color=WHITE)], 0.6),
            "the amount",
            (lambda: [Indicate(hd[2], color=WHITE)], 0.6),
            "So 18999",
            (lambda: self.cap("18999 cents = 189.99"), 0.5),
            "there's our",
            (lambda: [glow(self.rows[17][0], GOLD_M, 1.02), glow(self.rows[18][0], GOLD_M, 1.02),
                      *self.cap("payments 17 and 18: the double charge, at shop 4, Volt Electronics", GOLD_M)], 1.0),
        ])
        slots = VGroup(*[DashedVMobject(Rectangle(width=1.35, height=0.3, stroke_color=GREY_C, stroke_width=1.5)
                                        .move_to([R_TOT - 0.68, Y_ID[p], 0]), num_dashes=24) for p in ID_ORDER])
        self.steps("Today's request: show every March payment, each one next to its shop's March total.", [
            (lambda: self.cap("every row stays, and gets its shop's March total", WHITE), 0.5),
            "each one next to",
            (lambda: [FadeIn(hd[3]), FadeIn(slots)], 0.8),
        ])

        # ---------------- scene 3: the tool we know folds ----------------
        gq = query("SELECT merchant_id, sum(amount_minor) FROM payments", "WHERE <March, succeeded> GROUP BY merchant_id",
                   c2={"GROUP BY merchant_id": YELLOW_M})
        gbs = [gb_line(k) for k in range(4)]
        gb_head = left_at(T("GROUP BY: one line per shop", 20, GREY_B), RP_X, -0.2)

        def fold(k):
            shop, ps = BLOCKS[k]
            cps = [self.rows[p].copy() for p in ps]
            return [AnimationGroup(*[c.animate.move_to(gbs[k][0].get_center()).scale(0.5).set_opacity(0) for c in cps],
                                   FadeIn(gbs[k], scale=0.8), lag_ratio=0.5)], cps

        folds = [fold(k) for k in range(4)]
        self.steps("An earlier lesson's tool for one number from many rows is GROUP BY. It folds each shop's rows into one line. "
                   "Eight rows in, four lines out.", [
            (lambda: [*self.uncap(), FadeOut(tname), *self.set_query(gq)], 0.8),
            "It folds",
            (lambda: [FadeIn(gb_head)], 0.4),
            *[(lambda k=k: folds[k][0], 0.8) for k in range(4)],
            "Eight rows in",
            (lambda: self.cap("8 rows in, 4 lines out"), 0.5),
        ])
        for _, cps in folds:
            self.remove(*cps)
        gq2 = query("SELECT payment_id, merchant_id, sum(amount_minor) FROM payments", "WHERE <March, succeeded> GROUP BY merchant_id",
                    c1={"payment_id": RED_M}, c2={"GROUP BY merchant_id": YELLOW_M})
        err = VGroup(M('ERROR:  column "payments.payment_id"', 17, RED_M), M("must appear in the GROUP BY clause", 17, RED_M),
                     M("or be used in an aggregate function", 17, RED_M)).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        left_at(err, RP_X, 1.15)
        self.steps("Ask for the payment number as well, and PostgreSQL, the database program here, refuses with an error.", [
            (lambda: [*self.uncap(), *self.set_query(gq2)], 0.7),
            "refuses",
            (lambda: [FadeIn(err, shift=0.1 * UP)], 0.7),
        ])
        which = M("17? 18? 19?", 18, RED_M).move_to([GB_CX + 1.2, GB_Y[1], 0])
        self.steps("And that's fair. After folding, a line stands for a whole shop. Shop 4's line holds three payments. "
                   "Which one should it print?", [
            "a line stands",
            (lambda: [LaggedStart(*[glow(g[0], COL[BLOCKS[k][0]], 1.02) for k, g in enumerate(gbs)], lag_ratio=0.2)], 1.0),
            "Shop 4's line",
            (lambda: [FadeIn(which, shift=0.1 * LEFT)], 0.6),
            "Which one",
            (lambda: [Indicate(which, color=RED_M)], 0.7),
        ])
        back = DashedLine([GB_CX - GB_W / 2 - 0.1, -1.35, 0], [PX1 + 0.12, -1.35, 0], dash_length=0.1, stroke_width=3, color=GREY_B)
        back.add_tip(tip_length=0.18, tip_width=0.18)
        back_lab = T("join back", 18, GREY_B).move_to([(GB_CX - GB_W / 2 + PX1) / 2, -0.98, 0])
        self.steps("You could work out the totals separately, then join them back onto the payments. "
                   "It works, but it's folding the laundry, then unfolding it all again to find one sock.", [
            (lambda: [FadeOut(err), FadeOut(which)], 0.5),
            "join them back",
            (lambda: [Create(back), FadeIn(back_lab)], 0.8),
            "It works",
            (lambda: self.cap("the grouping, written twice: once to fold, once to unfold"), 0.5),
        ])
        self.steps("What we want is to keep every row, and write the total beside it.", [
            (lambda: [FadeOut(back), FadeOut(back_lab), *self.cap("keep every row, and write the total beside it", WHITE),
                      *[g.animate.set_opacity(0.3) for g in gbs], gb_head.animate.set_opacity(0.3)], 0.8),
            (lambda: [LaggedStart(*[Indicate(s, color=WHITE, scale_factor=1.06) for s in slots], lag_ratio=0.1)], 1.2),
        ])

        # ---------------- scene 4: the teacher ----------------
        corners = {p: corner(self.y[p]) for p in ID_ORDER}
        self.steps("Picture a teacher marking a pile of exam papers. For each paper, she looks through the papers from the same class, "
                   "writes the class average on this paper, and puts it back on the pile.", [
            (lambda: [*self.uncap(), LaggedStart(*[FadeIn(corners[p]) for p in ID_ORDER], lag_ratio=0.1)], 1.0),
            "For each paper",
            (lambda: [glow(self.rows[17][0], YELLOW_M, 1.02)], 0.8),
            "the same class",
            (lambda: [glow(self.rows[18][0], YELLOW_M, 1.02), glow(self.rows[19][0], YELLOW_M, 1.02)], 0.8),
            "writes the class",
            (lambda: [Indicate(slots[ID_ORDER.index(17)], color=YELLOW_M, scale_factor=1.1)], 0.7),
        ])
        for p in ID_ORDER:
            self.remove(corners[p])
            self.rows[p].add(corners[p])
        self.steps("Every paper comes back with one more number, and none goes missing. Ours writes a total, not an average.", [
            (lambda: [LaggedStart(*[Indicate(s, color=WHITE, scale_factor=1.06) for s in slots], lag_ratio=0.08)], 1.2),
            "Ours writes",
            (lambda: self.cap("here: the shop's total, not an average"), 0.5),
        ])
        self.steps("Let's map it. A row is a paper. The class is the shop. "
                   "The papers she reads are the rows of that shop. And the number she writes is a new column.", [
            (lambda: self.uncap(), 0.3),
            "A row is",
            (lambda: self.set_talk(0, "a paper = a row", size=22), 0.5),
            "The class",
            (lambda: [*self.set_talk(1, "the class = the shop", size=22),
                      LaggedStart(*[Indicate(self.rows[p][2], color=COL[SHOP[p]], scale_factor=1.2) for p in ID_ORDER], lag_ratio=0.05)], 0.8),
            "The papers she",
            (lambda: self.set_talk(2, "papers she reads = rows of that shop", size=22), 0.5),
            "And the number",
            (lambda: [*self.set_talk(3, "the number she writes = a new column", size=22), Indicate(hd[3], color=WHITE)], 0.7),
        ])
        ht = left_at(T("the head teacher: one line per class", 20, GOLD_M), RP_X, -0.2)
        self.steps("GROUP BY is the head teacher. She wants one line per class, and never sees a single paper again.", [
            (lambda: [*[g.animate.set_opacity(1) for g in gbs], swap(gb_head, ht)], 0.7),
            "never sees",
            (lambda: [LaggedStart(*[glow(g[0], GOLD_M, 1.02) for g in gbs], lag_ratio=0.15)], 1.0),
        ], after=0.4)

        # ---------------- scene 5: one word, and a guess ----------------
        wq = query("SELECT payment_id, merchant_id, amount_minor,", "sum(amount_minor) OVER (PARTITION BY merchant_id)",
                   c2={"OVER (PARTITION BY merchant_id)": YELLOW_M})
        self.steps("In SQL, the teacher is one word. Write OVER after sum, then say which rows belong together: "
                   "PARTITION BY merchant_id, the same shop.", [
            (lambda: [*self.clear_talk(), FadeOut(VGroup(*gbs)), FadeOut(ht)], 0.6),
            "Write OVER",
            (lambda: self.set_query(wq), 0.8),
            "PARTITION BY",
            (lambda: [Indicate(wq[1], color=YELLOW_M, scale_factor=1.04),
                      *self.cap("PARTITION BY merchant_id: the rows with the same shop belong together", WHITE)], 0.9),
        ])
        chips = [chip(s, GREY_B, 24).move_to([RP_X + 1.5, y, 0]) for s, y in (("4 rows", 1.55), ("8 rows", 0.85), ("the same error", 0.15))]
        for c in chips:
            left_at(c, RP_X, c.get_center()[1])
        self.steps("Before we run it, a guess. sum folds many values into one. So do we get four rows, eight rows, or the same error? "
                   "Pause and guess.", [
            (lambda: self.uncap(), 0.3),
            "So do we get",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in chips], lag_ratio=0.35)], 1.2),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ok = tick(True, 0.2).next_to(chips[1], RIGHT, buff=0.25)
        self.steps("Eight. Let's watch why.", [
            (lambda: [*self.uncap(), chips[1][0].animate.set_stroke(GREEN_M).set_fill(GREEN_M, 0.18), Create(ok),
                      chips[0].animate.set_opacity(0.3), chips[2].animate.set_opacity(0.3)], 0.7),
        ], after=0.4)

        # ---------------- scene 6: watch it run ----------------
        bars = {}
        for shop, ps in BLOCKS:
            ys = [Y_SHOP[p] for p in ps]
            bars[shop] = Line([BAR_X, max(ys) + ROW_H / 2, 0], [BAR_X, min(ys) - ROW_H / 2, 0], stroke_width=7, color=COL[shop])
        self.steps("First, PostgreSQL sorts the rows, so each shop's payments sit together. Nothing is folded.", [
            (lambda: [FadeOut(VGroup(*chips, ok)), FadeOut(slots)], 0.5),
            "sorts the rows",
            (lambda: self.move_rows(Y_SHOP), 1.2),
            (lambda: [Create(bars[s]) for s, _ in BLOCKS], 0.6),
            "Nothing is folded",
            (lambda: self.cap("sorted into shop blocks: nothing folded, all 8 rows still here"), 0.5),
        ])
        self.mk = marker(self.y[14])
        self.win = win_frame([self.y[14]])

        def at(p):
            return [self.mk.animate.move_to([self.mk.get_center()[0], self.y[p], 0])]

        def window(ps):
            return [Transform(self.win, win_frame([self.y[p] for p in ps]))]

        self.steps("Then it walks down the rows. Payment 14 is the only one at shop 1, so it reads this row alone: 5310.", [
            (lambda: [*self.uncap(), FadeIn(self.mk, shift=0.2 * RIGHT), *self.set_talk(0, "current row: 14", YELLOW_M)], 0.6),
            "so it reads",
            (lambda: [Create(self.win), *self.set_talk(1, "reads rows: 14")], 0.7),
            ": 5310",
            (lambda: [*self.set_talk(2, "sum = 5310", mono=False), *self.set_tot(14, 5310)], 0.6),
        ])
        self.steps("Payment 17 is at shop 4. It reads 17, 18 and 19. Three times 18999 is 56997, written on row 17.", [
            (lambda: [*at(17), *self.set_talk(0, "current row: 17", YELLOW_M), *self.drop_talk(1, 2)], 0.6),
            "It reads",
            (lambda: [*window([17, 18, 19]), *self.set_talk(1, "reads rows: 17, 18, 19")], 0.7),
            "Three times",
            (lambda: self.set_talk(2, "sum = 3 × 18999 = 56997"), 0.6),
            "written on",
            (lambda: self.set_tot(17, 56997), 0.6),
        ])
        self.steps("Payment 18 reads the same rows, so it gets the same total. And row 17 is still there. "
                   "A column was added, and no row was taken away.", [
            (lambda: [*at(18), *self.set_talk(0, "current row: 18", YELLOW_M)], 0.6),
            "so it gets",
            (lambda: [*self.set_tot(18, 56997), *self.set_talk(2, "sum = 56997")], 0.6),
            "And row 17",
            (lambda: [glow(self.rows[17][0], WHITE, 1.02)], 0.8),
            "A column was added",
            (lambda: self.cap("a column was added; no row was taken away"), 0.5),
        ])
        self.steps("Row 19 gets the same. Then 13 starts shop 5, so the set changes to 13, 16 and 22: 147500.", [
            (lambda: [*self.uncap(), *at(19), *self.set_talk(0, "current row: 19", YELLOW_M)], 0.5),
            (lambda: self.set_tot(19, 56997), 0.5),
            "Then 13",
            (lambda: [*at(13), *self.set_talk(0, "current row: 13", YELLOW_M), *self.drop_talk(1, 2)], 0.6),
            "the set changes",
            (lambda: [*window([13, 16, 22]), *self.set_talk(1, "reads rows: 13, 16, 22")], 0.7),
            ": 147500",
            (lambda: [*self.set_talk(2, "sum = 147500"), *self.set_tot(13, 147500)], 0.6),
        ])
        self.steps("The rest fill in the same way. Eight rows in, eight rows out.", [
            (lambda: [*at(16), *self.set_talk(0, "current row: 16", YELLOW_M), *self.set_tot(16, 147500)], 0.45),
            (lambda: [*at(22), *self.set_talk(0, "current row: 22", YELLOW_M), *self.set_tot(22, 147500)], 0.45),
            (lambda: [*at(21), *window([21]), *self.set_talk(0, "current row: 21", YELLOW_M),
                      *self.set_talk(1, "reads rows: 21"), *self.set_talk(2, "sum = 1325"), *self.set_tot(21, 1325)], 0.6),
            "Eight rows in",
            (lambda: [*self.cap("8 rows in, 8 rows out", WHITE), FadeOut(self.mk), *self.clear_talk()], 0.6),
        ], after=0.4)

        # ---------------- scene 7: now the names ----------------
        self.steps("Now the names. The class is called a partition. The rows read for the current row are its window. "
                   "And a function that reads a window, and keeps the row, is a window function.", [
            (lambda: [*self.uncap(), Transform(self.win, win_frame([self.y[p] for p in (13, 16, 22)]).set_stroke(opacity=0))], 0.4),
            "a partition",
            (lambda: [*self.set_talk(0, "the class: a partition"),
                      LaggedStart(*[bars[s].animate(rate_func=there_and_back).set_stroke(width=14) for s, _ in BLOCKS], lag_ratio=0.2)], 1.0),
            "its window",
            (lambda: [*self.set_talk(1, "the rows it reads: the window", YELLOW_M), self.win.animate.set_stroke(opacity=1)], 0.8),
            "And a function",
            (lambda: [*self.set_talk(2, "reads a window, keeps the row:"), Indicate(wq[1], color=YELLOW_M, scale_factor=1.04)], 0.8),
            "is a window function",
            (lambda: self.set_talk(3, "a window function", YELLOW_M), 0.5),
        ])
        self.steps("For every row, a window of related rows. The function reads the window. The row stays.", [
            (lambda: self.cap("for every row, a window of related rows", WHITE), 0.5),
            "The function reads",
            (lambda: self.cap("the function reads the window", WHITE), 0.5),
            "The row stays",
            (lambda: self.cap("the row stays", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 8: do something with it ----------------
        pct_h = right_at(M("pct", 16, GREY_B), R_PCT, HDR_Y)

        def show_pct():
            out = [FadeIn(pct_h)]
            for p in SHOP_ORDER:
                self.pct[p] = right_at(M(PCT[p], 22, GREEN_M), R_PCT, self.y[p])
                out.append(FadeIn(self.pct[p], shift=0.1 * RIGHT))
            return [LaggedStart(*out, lag_ratio=0.1)]

        self.steps("Now the total sits on the row, you can divide by it. Each of Volt's three payments is 33.3 percent of its March.", [
            (lambda: [*self.uncap(), *self.clear_talk(), FadeOut(self.win),
                      *self.cap("100.0 * amount_minor / merchant_total", WHITE, 24, mono=True)], 0.5),
            (lambda: show_pct(), 1.4),
            "Each of Volt",
            (lambda: [*self.cap("Volt Electronics (shop 4): 33.3 percent each", GOLD_M),
                      *[Indicate(self.pct[p], color=GOLD_M, scale_factor=1.2) for p in (17, 18, 19)]], 0.9),
        ], after=0.4)

        # ---------------- scene 9: where the teacher breaks ----------------
        def drop_pct():
            olds = list(self.pct.values())
            self.pct = {}
            return [FadeOut(VGroup(*olds, pct_h))]

        self.steps("Here the teacher picture breaks. She looks things up paper by paper. PostgreSQL first sorts the whole pile into shop order, "
                   "and on a big table, that sort is most of the work.", [
            (lambda: [*drop_pct(), *self.cap("where the teacher picture breaks")], 0.6),
            "PostgreSQL first sorts",
            (lambda: [*self.cap("first: sort the whole pile into shop order"), FadeOut(VGroup(*bars.values()))], 0.6),
            (lambda: self.move_rows(Y_ID), 0.9),
            (lambda: self.move_rows(Y_SHOP), 0.9),
            (lambda: [Create(bars[s]) for s, _ in BLOCKS], 0.5),
            "on a big table",
            (lambda: self.cap("on a big table, the sort is most of the work", WHITE), 0.5),
        ])
        r1 = talk("one line per group: GROUP BY", 0, size=22)
        r2 = talk("every row, plus a number: a window", 1, size=22)
        self.steps("So pick by what you want back. One line per group: GROUP BY. Every row, with a number beside it: a window.", [
            (lambda: self.uncap(), 0.3),
            "One line per group",
            (lambda: [FadeIn(r1, shift=0.1 * UP)], 0.6),
            "Every row",
            (lambda: [FadeIn(r2, shift=0.1 * UP)], 0.6),
            ": a window",
            (lambda: [Indicate(r2, color=YELLOW_M, scale_factor=1.05)], 0.7),
        ], after=0.4)

        # ---------------- scene 10: the moral, the double charge, and a check ----------------
        self.steps("So, a number from many rows, on every row? Give each row a window. "
                   "GROUP BY folds the rows. A window adds a column, and never takes a row away.", [
            (lambda: [FadeOut(r1), FadeOut(r2), *self.cap("a number from many rows, on every row?", WHITE)], 0.5),
            "Give each row",
            (lambda: [Create(self.win.become(win_frame([self.y[p] for p in (17, 18, 19)])))], 0.6),
            "A window adds",
            (lambda: [*self.cap("a window adds a column; it never takes a row away", YELLOW_M),
                      LaggedStart(*[Indicate(self.tot[p], color=WHITE, scale_factor=1.15) for p in SHOP_ORDER], lag_ratio=0.08)], 1.2),
        ])
        dc = talk("partition by card, shop and amount,", 0, GOLD_M, 21)
        dc2 = talk("in time order: 18 right after 17", 1, GOLD_M, 21)
        self.steps("And the double charge? Partition by card, shop and amount, in time order, and payment 18 sits right after 17. "
                   "Later in this lesson, a window function compares the two.", [
            (lambda: [FadeOut(self.win), *self.uncap()], 0.4),
            "And the double",
            (lambda: [glow(self.rows[17][0], GOLD_M, 1.02), glow(self.rows[18][0], GOLD_M, 1.02)], 0.9),
            "Partition by card",
            (lambda: [FadeIn(dc, shift=0.1 * UP)], 0.6),
            "and payment 18",
            (lambda: [FadeIn(dc2, shift=0.1 * UP)], 0.6),
        ])
        cq = query("SELECT payment_id, merchant_id, amount_minor,", "sum(amount_minor) OVER ()", c2={"OVER ()": YELLOW_M})
        q21 = M("?", 26, YELLOW_M)
        self.steps("One quick check. Leave the brackets after OVER empty: no partition rule at all. What lands on row 21? Pause and think.", [
            (lambda: [FadeOut(dc), FadeOut(dc2)], 0.4),
            "Leave the brackets",
            (lambda: self.set_query(cq), 0.8),
            "What lands",
            (lambda: [FadeOut(self.tot[21]), FadeIn(right_at(q21, R_TOT, self.y[21]))], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        allw = win_frame(list(Y_SHOP.values()))
        self.tot[21] = q21

        def all_month():
            out = []
            for p in SHOP_ORDER:
                out += self.set_tot(p, 211132, GREEN_M)
            return [LaggedStart(*out, lag_ratio=0.06)]

        self.steps("The whole month's total, 211132. With no rule, every row is related, so the whole result is one window.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*bars.values())), Create(allw)], 0.7),
            (lambda: all_month(), 1.4),
            "With no rule",
            (lambda: self.cap("no partition rule: one window, the whole result", WHITE), 0.5),
        ], after=0.3)
        self.play(*self.cap("a window adds a column; it never takes a row away", YELLOW_M), run_time=0.7)
        self.wait(2.0)
