from sfz import *

# Category codes are said in pairs, the way people read them; captions keep the digits.
SAY.insert(0, (r"\bmcc\b", "M C C"))
SAY.insert(0, (r"\b5732\b", "fifty-seven thirty-two"))
SAY.insert(0, (r"\b5814\b", "fifty-eight fourteen"))
SAY.insert(0, (r"\b5812\b", "fifty-eight twelve"))
SAY.insert(0, (r"\b7011\b", "seventy eleven"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
FS, HS = 18, 14                                   # cell and header text sizes
ROW_Y = [2.05 - 0.42 * i for i in range(10)]
TTL_Y, HDR_Y, RULE_Y = 2.95, 2.5, 2.3
PF_X0, PF_X1, PF_X1_MID, PF_X1_SPLIT, PF_TOP, PF_BOT = -6.6, 5.45, 0.9, 0.0, 3.22, -1.98   # the file's table
X_PID, X_NAME, X_MER, X_MCC, X_DESC = -5.8, -4.95, -2.7, 0.15, 1.1
# the two tables of their own (the café's card box), drawn only once the cells have left
MF_X0, MF_X1, MF_TOP, MF_BOT = 1.05, 5.0, 3.22, 0.55          # merchants: one row per shop
XM_NAME, XM_MCC = 1.3, 4.15
CF_X0, CF_X1, CF_TOP, CF_BOT = 1.05, 6.52, 0.02, -2.85          # mcc_codes: one row per category
CTTL_Y, CHDR_Y, CRULE_Y = -0.22, -0.62, -0.8
CROW_Y = [-1.04 - 0.38 * i for i in range(5)]
XC_MCC, XC_DESC = 1.3, 2.2
GHOST_Y = -2.42
CAP_Y = -3.25

ROWS = [(13, "Ben Carter", "Harbor Hotel", "7011", "Hotels, motels, resorts"),
        (14, "Asha Rao", "Northwind Grocers", "5411", "Grocery stores, supermarkets"),
        (15, "Elena Petrova", "Volt Electronics", "5732", "Electronics stores"),
        (16, "Jonas Weber", "Harbor Hotel", "7011", "Hotels, motels, resorts"),
        (17, "Farid Hadad", "Volt Electronics", "5732", "Electronics stores"),
        (18, "Farid Haddad", "Volt Electronics", "5732", "Electronic stores"),
        (19, "Chloe Martin", "Volt Electronics", "5732", "Electronics stores"),
        (20, "Ben Carter", "Northwind Grocers", "5411", "Grocery stores, supermarkets"),
        (21, "Mateo Ruiz", "Quick Bite", "5812", "Eating places, restaurants"),
        (22, "Jonas Weber", "Harbor Hotel", "7011", "Hotels, motels, resorts")]
CODES = ["7011", "5411", "5732", "5812"]                       # first appearance in the file
DESC = {"7011": "Hotels, motels, resorts", "5411": "Grocery stores, supermarkets", "5732": "Electronics stores",
        "5812": "Eating places, restaurants"}
SHOPS = ["Harbor Hotel", "Northwind Grocers", "Volt Electronics", "Quick Bite"]
SHOP_MCC = {"Harbor Hotel": "7011", "Northwind Grocers": "5411", "Volt Electronics": "5732", "Quick Bite": "5812"}
VOLT = [2, 4, 5, 6]

# the café's order book (made up for the picture)
BK_X0, BK_X1, BK_TOP, BK_BOT = -4.3, 4.3, 2.6, -1.75
BK_Y = [1.15 - 0.6 * i for i in range(5)]
BOOK = [("Ana", "555-0142", "latte", "3.50"), ("Tom", "555-0187", "tea", "2.80"), ("Ana", "555-0142", "flat white", "3.80"),
        ("Ana", "555-0142", "latte", "3.50"), ("Ana", "555-0142", "mocha", "3.90")]


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

    def countdown(self, c=(0, -2.6), secs=3.0):
        bar = Line([c[0] - 1.0, c[1], 0], [c[0] + 1.0, c[1], 0], stroke_width=5, color=YELLOW_M)
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
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def frame(x0, x1, top, bot, color):
    return RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=3)\
        .set_fill(fillc(color, 0.1), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0]).set_z_index(-1)


def around(m, color, buff=0.07):
    return SurroundingRectangle(m, buff=buff, corner_radius=0.05, stroke_color=color, stroke_width=3)


def row_box(x0, x1, y, color=YELLOW_M):
    return RoundedRectangle(corner_radius=0.06, width=x1 - x0, height=0.38, stroke_color=color, stroke_width=3).move_to(
        [(x0 + x1) / 2, y, 0])


# ---- the file's table ----
def cell(col, s, y, color=WHITE):
    m = M(s, FS, color)
    if col == "pid":
        return m.move_to([X_PID, y, 0])
    return left_at(m, {"name": X_NAME, "mer": X_MER, "mcc": X_MCC, "desc": X_DESC}[col], y)


def hdr(s, x, y=HDR_Y, center=False, color=GREY_B):
    m = M(s, HS, color)
    return m.move_to([x, y, 0]) if center else left_at(m, x, y)


def mer_cell(k, col, color=WHITE):
    s = SHOPS[k] if col == "name" else SHOP_MCC[SHOPS[k]]
    return left_at(M(s, FS, color), XM_NAME if col == "name" else XM_MCC, ROW_Y[k])


def cod_cell(k, col, code=None, color=WHITE):
    code = code or CODES[k]
    s = code if col == "mcc" else (DESC.get(code) or "Fast food restaurants")
    return left_at(M(s, FS, color), XC_MCC if col == "mcc" else XC_DESC, CROW_Y[k])


class Normalization(Base):
    """sql-02, section 0. The café's order book repeats a regular's phone number on 200 lines, and a change reaches only
    199. The partner bank's file, payments_export, does the same: Volt's category 5732 four times in ten rows, Farid's
    surname spelled two ways (17, 18), 5732 called "Electronic stores" on 18. Being careful is steelmanned and broken:
    the update anomaly, plus an insert anomaly (5814 has nowhere to go) and a delete anomaly (deleting 21 loses Quick
    Bite's category). The café's card box is the fix: the categories and the shops move to tables of their own, keyed by
    what decides them. The price is a join. Check: renaming 7011 touches three rows before, one after."""

    def construct(self):
        self.capm = None
        self.title_card("One fact, many copies", "why a table should say things once")

        # ---------------- scene 1: the order book ----------------
        bk = frame(BK_X0, BK_X1, BK_TOP, BK_BOT, BLUE_M)
        rings = VGroup(*[Circle(radius=0.08, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLACK, 1).move_to([BK_X0, y, 0])
                         for y in np.arange(BK_TOP - 0.45, BK_BOT + 0.3, -0.55)])
        bk_t = left_at(T("order book", 26), BK_X0 + 0.45, BK_TOP - 0.38)
        bx = [BK_X0 + 0.5, BK_X0 + 1.7, BK_X0 + 4.0, BK_X1 - 0.45]
        bk_h = VGroup(left_at(T("name", 18, GREY_B), bx[0], 1.68), left_at(T("phone", 18, GREY_B), bx[1], 1.68),
                      left_at(T("drink", 18, GREY_B), bx[2], 1.68), right_at(T("price", 18, GREY_B), bx[3], 1.68))
        bk_r = Line([BK_X0 + 0.35, 1.45, 0], [BK_X1 - 0.3, 1.45, 0], stroke_width=1.5, color=GREY_C)

        def bline(i, phone=None, pcolor=WHITE):
            n, p, d, pr = BOOK[i]
            y = BK_Y[i]
            return VGroup(left_at(M(n, 26), bx[0], y), left_at(M(phone or p, 26, pcolor), bx[1], y),
                          left_at(M(d, 26), bx[2], y), right_at(M(pr, 26), bx[3], y))

        lines = [bline(i) for i in range(5)]
        book = VGroup(bk, rings, bk_t, bk_h, bk_r)
        self.steps("Picture a café's old order book. For every order, the barista writes the customer's name, phone number, "
                   "drink and price on one line.", [
            (lambda: [FadeIn(book, shift=0.15 * UP)], 1.0),
            "For every order",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in lines], lag_ratio=0.3)], 2.0),
        ])
        self.steps("It's quick, and on the first day it works perfectly.", [
            "it works perfectly",
            (lambda: [glow(bk, BLUE_M, 1.01)], 0.9),
        ])
        ana = [0, 2, 3, 4]
        her = T("her number is on 200 lines", 22, GREY_B).move_to([0, -2.3, 0])
        cur = row_box(BK_X0 + 0.3, BK_X1 - 0.25, BK_Y[0])
        miss = around(lines[3][1], RED_M)
        new_p = {}

        def change(i):
            new_p[i] = bline(i, "555-0199", GREEN_M)[1]
            return [Transform(lines[i][1], new_p[i])]

        self.steps("Then a regular changes her phone number. Her number sits on 200 lines, and someone has to change all of them. "
                   "They change 199.", [
            "Then a regular",
            (lambda: [*[Indicate(lines[i][1], color=YELLOW_M, scale_factor=1.08) for i in ana]], 0.9),
            "Her number sits",
            (lambda: [FadeIn(her, shift=0.1 * UP)], 0.5),
            "someone has to",
            (lambda: [Create(cur)], 0.3),
            (lambda: change(0), 0.35),
            (lambda: [cur.animate.move_to([cur.get_x(), BK_Y[2], 0])], 0.35),
            (lambda: change(2), 0.35),
            (lambda: [cur.animate.move_to([cur.get_x(), BK_Y[3], 0])], 0.35),
            0.15,
            (lambda: [cur.animate.move_to([cur.get_x(), BK_Y[4], 0])], 0.35),
            (lambda: change(4), 0.35),
            "They change",
            (lambda: [FadeOut(cur), *self.cap("changed: 199 of 200", WHITE)], 0.5),
            (lambda: [lines[3][1].animate.set_color(RED_M), Create(miss)], 0.6),
        ])
        self.steps("In an exam, 199 out of 200 is a great score. In a book of facts, it means the book now says two different things. "
                   "Which number is right? Nobody can tell.", [
            (lambda: self.cap("199 out of 200: a great exam score", GOLD_M), 0.5),
            "In a book of facts",
            (lambda: self.cap("one person, two phone numbers", RED_M), 0.5),
            "Which number",
            (lambda: [Indicate(lines[2][1], color=GREEN_M, scale_factor=1.1), Indicate(lines[3][1], color=RED_M, scale_factor=1.1)], 1.0),
            "Nobody can tell",
            (lambda: self.cap("which one is right? nobody can tell", RED_M), 0.5),
        ], after=0.3)

        # ---------------- scene 2: the same book, as a table ----------------
        pf = frame(PF_X0, PF_X1, PF_TOP, PF_BOT, BLUE_M)
        p_ttl = left_at(M("payments_export", 18, GREY_B), PF_X0 + 0.25, TTL_Y)
        p_sub = right_at(T("the partner bank's file, as it arrived", 18, GREY_C), PF_X1 - 0.25, TTL_Y)
        H = {"pid": hdr("payment_id", X_PID, center=True), "name": hdr("customer_name", X_NAME), "mer": hdr("merchant_name", X_MER),
             "mcc": hdr("mcc", X_MCC), "desc": hdr("mcc_description", X_DESC)}
        p_rule = Line([PF_X0 + 0.15, RULE_Y, 0], [PF_X1 - 0.15, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        C = {c: [cell(c, str(r[k]), ROW_Y[i]) for i, r in enumerate(ROWS)] for k, c in enumerate(["pid", "name", "mer", "mcc", "desc"])}

        def row(i):
            return VGroup(*[C[c][i] for c in ("pid", "name", "mer", "mcc", "desc")])

        self.steps("A database table can fall into the same trap. A table is like a spreadsheet: each row is one record, "
                   "and each column one fact about it.", [
            (lambda: [FadeOut(VGroup(book, *lines, her, miss)), *self.uncap()], 0.8),
            "A table is like",
            (lambda: [FadeIn(pf), FadeIn(VGroup(*H.values())), Create(p_rule)], 0.9),
            "each row",
            (lambda: [FadeIn(row(0), shift=0.1 * DOWN)], 0.6),
            "each column",
            (lambda: [*[Indicate(C[c][0], color=BLUE_M, scale_factor=1.1) for c in C]], 0.9),
        ])
        self.steps("A partner bank, another company that handles card payments for some of the same shops, sends a file of payments "
                   "every night. The quickest way to load it is to keep it as it arrives, with every detail on every row.", [
            (lambda: [FadeIn(p_ttl), FadeIn(p_sub)], 0.7),
            "The quickest",
            (lambda: [LaggedStart(*[FadeIn(row(i), shift=0.1 * DOWN) for i in range(1, 10)], lag_ratio=0.2)], 2.2),
        ])
        self.steps("The mcc is the merchant category code: four digits the card "
                   "companies give each shop, to say what kind of business it is.", [
            (lambda: [Transform(H["mcc"], hdr("mcc", X_MCC, color=GOLD_M)), *self.cap("mcc: merchant category code, four digits per shop")], 0.6),
            "four digits",
            (lambda: [*[Indicate(C["mcc"][i], color=GOLD_M, scale_factor=1.12) for i in range(10)]], 1.0),
        ])
        gold = [around(C["mcc"][i], GOLD_M, 0.05) for i in VOLT]
        self.steps("Volt Electronics is in category 5732, electronics shops. This file says so four times in ten rows. "
                   "A year of files would say it about 50,000 times.", [
            (lambda: [*[C["mer"][i].animate.set_color(GOLD_M) for i in VOLT]], 0.6),
            "This file says",
            (lambda: [LaggedStart(*[Create(g) for g in gold], lag_ratio=0.3), *[C["mcc"][i].animate.set_color(GOLD_M) for i in VOLT]], 1.2),
            "A year of files",
            (lambda: self.cap("a year of files: about 50,000 copies of one fact", GOLD_M), 0.5),
        ])
        self.steps("So the table is the order book, a row is a line, and Volt's category is her phone number: "
                   "one fact, copied onto many rows.", [
            (lambda: [*self.cap("the table = the order book"), glow(pf, BLUE_M, 1.0)], 0.7),
            "a row is a line",
            (lambda: [*self.cap("a row = a line"), *[Indicate(m, color=WHITE, scale_factor=1.06) for m in row(1)]], 0.8),
            "and Volt's",
            (lambda: [*self.cap("Volt's category = her phone number", GOLD_M), *[glow(g, GOLD_M, 1.1) for g in gold]], 0.9),
        ])

        # ---------------- scene 3: spot the disagreements ----------------
        self.steps("Every copy is a chance to disagree, and this small file already disagrees with itself twice. "
                   "Can you spot where? Pause and look.", [
            (lambda: [*self.uncap(), *[FadeOut(g) for g in gold], *[C["mer"][i].animate.set_color(WHITE) for i in VOLT],
                      *[C["mcc"][i].animate.set_color(WHITE) for i in VOLT], Transform(H["mcc"], hdr("mcc", X_MCC))], 0.8),
            "Pause and look",
            (lambda: self.cap("pause and look", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        o17 = around(C["name"][4], RED_M)
        o18 = around(C["name"][5], RED_M)
        o18d = around(C["desc"][5], RED_M)
        self.steps("Payment 17 spells Farid's surname with one d. Payment 18 spells it with two, and calls category 5732 "
                   "Electronic stores, without the s.", [
            (lambda: [*self.uncap(), Create(o17), C["name"][4].animate.set_color(RED_M)], 0.6),
            "Payment 18",
            (lambda: [Create(o18)], 0.5),
            "and calls",
            (lambda: [Create(o18d), C["desc"][5].animate.set_color(RED_M)], 0.6),
            "without the s",
            (lambda: [*[Indicate(C["desc"][i], color=WHITE, scale_factor=1.06) for i in (2, 4, 6)]], 0.8),
        ])
        self.steps("So which spelling is right? The table can't tell you, because nothing keeps the copies equal.", [
            (lambda: self.cap("which spelling is right? the table can't tell you", RED_M), 0.5),
            "because nothing",
            (lambda: [*[glow(g, RED_M, 1.06) for g in (o17, o18, o18d)]], 0.9),
        ])

        # ---------------- scene 4: be careful? ----------------
        self.steps("You might be thinking: so be careful. Fix the bad rows, and next time, change every copy. "
                   "To be fair, that does fix today's mistake.", [
            (lambda: self.cap("be careful: fix the bad rows, change every copy", PURPLE_M), 0.5),
            "To be fair",
            (lambda: [*[Indicate(m, color=PURPLE_M, scale_factor=1.06) for m in (C["name"][4], C["desc"][5])]], 0.9),
        ])
        self.steps("But careful is what the barista was, 199 times. A fact stored on many rows must be changed on all of them, "
                   "and missing one leaves the table contradicting itself. That's called an update anomaly. "
                   "An anomaly is something wrong that the design allows.", [
            (lambda: self.cap("careful: 199 of 200", WHITE), 0.5),
            "A fact stored",
            (lambda: [*[Indicate(C["mcc"][i], color=GOLD_M, scale_factor=1.15) for i in VOLT]], 1.0),
            "and missing one",
            (lambda: [*[glow(g, RED_M, 1.06) for g in (o17, o18, o18d)]], 0.9),
            "That's called",
            (lambda: self.cap("update anomaly: copies that no longer agree", RED_M), 0.5),
            "An anomaly is",
            (lambda: self.cap("anomaly: something wrong that the design allows", RED_M), 0.5),
        ])
        gb = DashedVMobject(RoundedRectangle(corner_radius=0.06, width=PF_X1 - PF_X0 - 0.2, height=0.4, stroke_color=GREY_B,
                                             stroke_width=2.5).move_to([(PF_X0 + PF_X1) / 2, GHOST_Y, 0]), num_dashes=70)
        ghost = VGroup(cell("pid", "?", GHOST_Y, RED_M), cell("name", "?", GHOST_Y, RED_M), cell("mer", "?", GHOST_Y, RED_M),
                       cell("mcc", "5814", GHOST_Y, GREY_A), cell("desc", "Fast food restaurants", GHOST_Y, GREY_A))
        self.steps("And care can't help with the other two. Category 5814 means fast food restaurants. Where would you write that down? "
                   "Every row is a payment, and no fast food payment has arrived yet. That's an insert anomaly.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(o17, o18, o18d))], 0.5),
            "Category 5814",
            (lambda: [Create(gb), FadeIn(ghost[3:], shift=0.1 * UP)], 0.8),
            "Every row is a payment",
            (lambda: [LaggedStart(*[FadeIn(m, scale=1.4) for m in ghost[:3]], lag_ratio=0.3)], 0.9),
            "That's an insert",
            (lambda: self.cap("insert anomaly: a fact with nowhere to live", RED_M), 0.5),
        ])
        strike = Line([PF_X0 + 0.25, ROW_Y[8], 0], [PF_X1 - 0.25, ROW_Y[8], 0], stroke_width=3, color=RED_M)
        qb = row_box(PF_X0 + 0.15, PF_X1 - 0.15, ROW_Y[8], GOLD_M)
        self.steps("Now payment 21, the only Quick Bite row. Say it turns out to be fraud, and you delete it. "
                   "The fact that Quick Bite is a restaurant goes with it.", [
            (lambda: [FadeOut(VGroup(gb, ghost)), *self.uncap(), Create(qb)], 0.6),
            "Say it turns out",
            (lambda: [Create(strike)], 0.5),
            "you delete it",
            (lambda: [row(8).animate.set_opacity(0.12), strike.animate.set_opacity(0.4)], 0.6),
            "The fact that",
            (lambda: self.cap("deleted with it: Quick Bite is a restaurant (5812)", RED_M), 0.5),
        ])
        self.steps("You came to remove one bad payment, and lost a restaurant. That's a delete anomaly.", [
            "That's a delete",
            (lambda: self.cap("delete anomaly: one fact deleted with another", RED_M), 0.5),
        ], after=0.3)
        self.steps("Three kinds of damage, and one cause: the same fact, stored on many rows.", [
            (lambda: [FadeOut(strike), FadeOut(qb), row(8).animate.set_opacity(1)], 0.6),
            "one cause",
            (lambda: [*self.cap("one cause: the same fact, stored on many rows", GOLD_M),
                      *[C["mcc"][i].animate.set_color(GOLD_M) for i in VOLT], *[C["desc"][i].animate.set_color(GOLD_M) for i in VOLT]], 0.8),
        ], after=0.3)

        # ---------------- scene 5: one home per fact ----------------
        self.steps("So what would the café do? Wouldn't it be nice to write her number down only once?", [
            (lambda: [*[C["mcc"][i].animate.set_color(WHITE) for i in VOLT],
                      *[C["desc"][i].animate.set_color(RED_M if i == 5 else WHITE) for i in VOLT],
                      C["name"][4].animate.set_color(WHITE), *self.cap("write her number down only once?", WHITE)], 0.7),
        ])
        sy = -2.6
        bl_t = M("customer 17 · latte · 3.50", FS)
        bl = VGroup(RoundedRectangle(corner_radius=0.1, width=bl_t.width + 0.4, height=0.5, stroke_color=BLUE_M, stroke_width=2.5)
                    .set_fill(fillc(BLUE_M), 1), bl_t).move_to([-3.6, sy, 0])
        cd_t = M("customer 17 · Ana · 555-0142", FS)
        cd_r = RoundedRectangle(corner_radius=0.1, width=cd_t.width + 0.4, height=0.5, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M), 1)
        card = VGroup(cd_r, cd_t).move_to([2.7, sy, 0])
        bl_lab = T("a line in the book", 16, GREY_B).next_to(bl, DOWN, buff=0.12)
        cd_lab = T("one card per customer", 16, TEAL_M).next_to(card, DOWN, buff=0.12)
        a_bc = Arrow(bl.get_right() + 0.1 * RIGHT, card.get_left() + 0.1 * LEFT, buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.15)
        ok_card = tick(True, 0.16).next_to(card, RIGHT, buff=0.25)
        cd_new = M("customer 17 · Ana · 555-0199", FS, t2c={"555-0199": GREEN_M}).move_to(cd_t)
        self.steps("Keep one card per customer, in a little box, with her name and number. Each line in the book then says customer 17. "
                   "When her number changes, you change one card, and there's nothing to miss.", [
            (lambda: [*self.uncap(), FadeIn(card, shift=0.1 * UP), FadeIn(cd_lab)], 0.7),
            "Each line in the book",
            (lambda: [FadeIn(bl, shift=0.1 * UP), FadeIn(bl_lab), GrowArrow(a_bc)], 0.8),
            "you change one card",
            (lambda: [Transform(cd_t, cd_new), glow(cd_r, TEAL_M, 1.04)], 0.8),
            (lambda: [Create(ok_card)], 0.5),
        ])
        o18d2 = around(C["desc"][5], RED_M)
        self.steps("Let's do the same with the table, starting with the categories. Someone still has to decide which spelling is true, "
                   "but only once. The card companies' list says Electronics stores.", [
            (lambda: [FadeOut(VGroup(bl, bl_lab, a_bc, card, cd_lab, ok_card))], 0.6),
            "Someone still",
            (lambda: [Create(o18d2)], 0.5),
            "The card companies",
            (lambda: [*self.cap("decided once, from the card companies' list"),
                      Transform(C["desc"][5], cell("desc", "Electronics stores", ROW_Y[5], GREEN_M)), FadeOut(o18d2)], 0.8),
        ])

        # move the categories out: every copy of a code and its description lands on that code's one row
        cf = frame(CF_X0, CF_X1, CF_TOP, CF_BOT, TEAL_M)
        c_ttl = left_at(M("mcc_codes", 18, GREY_B), XC_MCC, CTTL_Y)
        c_sub = right_at(T("one row per category", 18, TEAL_M), CF_X1 - 0.25, CTTL_Y)
        c_hm = left_at(M("mcc", HS, GREY_B), XC_MCC, CHDR_Y)
        c_hd = left_at(M("description", HS, GREY_B), XC_DESC, CHDR_Y)
        c_rule = Line([CF_X0 + 0.15, CRULE_Y, 0], [CF_X1 - 0.15, CRULE_Y, 0], stroke_width=1.5, color=GREY_D)
        CM = [cod_cell(k, "mcc") for k in range(4)]
        CD = [cod_cell(k, "desc") for k in range(4)]

        def move_codes():
            an, seen = [], set()
            for i, r in enumerate(ROWS):
                k = CODES.index(r[3])
                if k not in seen:
                    an += [ReplacementTransform(C["mcc"][i].copy(), CM[k]), ReplacementTransform(C["desc"][i], CD[k])]
                    seen.add(k)
                else:
                    an += [Transform(C["mcc"][i].copy(), CM[k].copy(), remover=True), Transform(C["desc"][i], CD[k].copy(), remover=True)]
            return an

        pf_m = frame(PF_X0, PF_X1_MID, PF_TOP, PF_BOT, BLUE_M)
        p_rule_m = Line([PF_X0 + 0.15, RULE_Y, 0], [PF_X1_MID - 0.15, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        self.steps("Then each code and its description move to a table of their own. Ten rows of copies become four.", [
            (lambda: [*self.uncap(), FadeOut(p_sub), *move_codes(), ReplacementTransform(H["desc"], c_hd),
                      Transform(pf, pf_m), Transform(p_rule, p_rule_m)], 1.6),
            (lambda: [FadeIn(cf), FadeIn(c_ttl), FadeIn(c_sub), FadeIn(c_hm), Create(c_rule)], 0.7),
            "Ten rows",
            (lambda: self.cap("ten rows of copies, four rows of facts", TEAL_M), 0.5),
        ])
        # the moved descriptions on the right were removed from the file's table; keep its rule short of them
        o5732 = row_box(CF_X0 + 0.12, CF_X1 - 0.12, CROW_Y[2], TEAL_M)
        self.steps("From now on, there's one place to fix, and nowhere for a second spelling to live.", [
            "one place",
            (lambda: [Create(o5732)], 0.6),
            "nowhere for",
            (lambda: [glow(o5732, TEAL_M, 1.03)], 0.8),
        ])

        # move the shops out: each shop and its code, once; the payments keep the shop's name
        mf = frame(MF_X0, MF_X1, MF_TOP, MF_BOT, TEAL_M)
        m_ttl = left_at(M("merchants", 18, GREY_B), XM_NAME, TTL_Y)
        m_sub = right_at(T("one row per shop", 18, TEAL_M), MF_X1 - 0.25, TTL_Y)
        m_hn = left_at(M("name", HS, GREY_B), XM_NAME, HDR_Y)
        m_hm = left_at(M("mcc", HS, GREY_B), XM_MCC, HDR_Y)
        m_rule = Line([MF_X0 + 0.15, RULE_Y, 0], [MF_X1 - 0.15, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        MN = [mer_cell(k, "name") for k in range(4)]
        MM = [mer_cell(k, "mcc") for k in range(4)]

        def move_shops():
            an, seen = [], set()
            for i, r in enumerate(ROWS):
                k = SHOPS.index(r[2])
                if k not in seen:
                    an += [ReplacementTransform(C["mer"][i].copy(), MN[k]), ReplacementTransform(C["mcc"][i], MM[k])]
                    seen.add(k)
                else:
                    an += [Transform(C["mer"][i].copy(), MN[k].copy(), remover=True), Transform(C["mcc"][i], MM[k].copy(), remover=True)]
            return an

        pf_s = frame(PF_X0, PF_X1_SPLIT, PF_TOP, PF_BOT, BLUE_M)
        p_rule_s = Line([PF_X0 + 0.15, RULE_Y, 0], [PF_X1_SPLIT - 0.15, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        p_sub_s = right_at(T("the payments", 18, GREY_C), PF_X1_SPLIT - 0.25, TTL_Y)
        a_pm = Arrow([PF_X1_SPLIT + 0.06, 1.42, 0], [MF_X0 - 0.06, 1.42, 0], buff=0, stroke_width=3, color=GOLD_M,
                     max_tip_length_to_length_ratio=0.3)
        a_mc = Arrow([2.5, MF_BOT - 0.05, 0], [2.5, CF_TOP + 0.05, 0], buff=0, stroke_width=3, color=TEAL_M,
                     max_tip_length_to_length_ratio=0.35)
        self.steps("The shops get their own table too: each shop and its code, once. The payments keep only the shop's name, "
                   "which points at its row.", [
            (lambda: [*self.uncap(), FadeOut(o5732), *move_shops(), ReplacementTransform(H["mcc"], m_hm),
                      Transform(pf, pf_s), Transform(p_rule, p_rule_s)], 1.6),
            (lambda: [FadeIn(mf), FadeIn(m_ttl), FadeIn(m_sub), FadeIn(m_hn), Create(m_rule), FadeIn(p_sub_s)], 0.7),
            "The payments keep",
            (lambda: [*[Indicate(C["mer"][i], color=GOLD_M, scale_factor=1.06) for i in range(10)]], 0.9),
            "which points",
            (lambda: [GrowArrow(a_pm), GrowArrow(a_mc)], 0.7),
        ])
        ul_m = Line([XM_NAME, HDR_Y - 0.16, 0], [XM_NAME + m_hn.width, HDR_Y - 0.16, 0], stroke_width=3, color=GOLD_M)
        ul_c = Line([XC_MCC, CHDR_Y - 0.16, 0], [XC_MCC + c_hm.width, CHDR_Y - 0.16, 0], stroke_width=3, color=GOLD_M)
        self.steps("Each shop's name now appears once in its table, and so does each code. "
                   "A column like that is called a key: its value names exactly one row, so other rows can point at it.", [
            (lambda: [Transform(m_hn, left_at(M("name", HS, GOLD_M), XM_NAME, HDR_Y)), Create(ul_m)], 0.6),
            (lambda: [LaggedStart(*[Indicate(m, color=GOLD_M, scale_factor=1.06) for m in MN], lag_ratio=0.25)], 1.2),
            "and so does",
            (lambda: [Transform(c_hm, left_at(M("mcc", HS, GOLD_M), XC_MCC, CHDR_Y)), Create(ul_c)], 0.6),
            (lambda: [LaggedStart(*[Indicate(m, color=GOLD_M, scale_factor=1.1) for m in CM], lag_ratio=0.25)], 1.2),
            "called a key",
            (lambda: self.cap("a key: its value names exactly one row", GOLD_M), 0.5),
            "so other rows",
            (lambda: [glow(a_pm, GOLD_M, 1.0), glow(a_mc, TEAL_M, 1.0)], 0.9),
        ])
        c5814 = VGroup(cod_cell(4, "mcc", "5814", GREEN_M), cod_cell(4, "desc", "5814", GREEN_M))
        qbm = row_box(MF_X0 + 0.12, MF_X1 - 0.12, ROW_Y[3], GREEN_M)
        strike2 = Line([PF_X0 + 0.25, ROW_Y[8], 0], [PF_X1_SPLIT - 0.25, ROW_Y[8], 0], stroke_width=3, color=RED_M)
        prow8 = VGroup(C["pid"][8], C["name"][8], C["mer"][8])
        self.steps("And the other two problems are gone. 5814 gets its row today, with no payment needed. "
                   "Delete payment 21, and Quick Bite keeps its category.", [
            (lambda: self.uncap(), 0.3),
            "5814 gets",
            (lambda: [FadeIn(c5814, shift=0.1 * UP)], 0.7),
            "Delete payment 21",
            (lambda: [Create(strike2)], 0.4),
            (lambda: [prow8.animate.set_opacity(0.12), strike2.animate.set_opacity(0.4)], 0.5),
            "Quick Bite keeps",
            (lambda: [Create(qbm)], 0.5),
            (lambda: [glow(qbm, GREEN_M, 1.03)], 0.7),
        ])
        self.steps("Deciding which facts get a table of their own is called normalization. Farid's name needs the same cure: "
                   "one row per customer.", [
            (lambda: [FadeOut(strike2), FadeOut(qbm), prow8.animate.set_opacity(1), *[m.animate.set_color(WHITE) for m in c5814]], 0.6),
            "called normalization",
            (lambda: self.cap("normalization: deciding which facts get a table of their own", WHITE), 0.5),
            "Farid's name",
            (lambda: [Create(o17), Create(o18)], 0.6),
            1.0,
            (lambda: [FadeOut(o17), FadeOut(o18)], 0.5),
        ])

        # ---------------- scene 6: the price ----------------
        r15 = row_box(PF_X0 + 0.15, PF_X1_SPLIT - 0.15, ROW_Y[2], YELLOW_M)
        rv = row_box(MF_X0 + 0.12, MF_X1 - 0.12, ROW_Y[2], YELLOW_M)
        rc = row_box(CF_X0 + 0.12, CF_X1 - 0.12, CROW_Y[2], YELLOW_M)
        self.steps("Splitting has a price. To print a payment with its category's description, the database now has to put "
                   "three tables back together. That's called a join, and it's the next lesson.", [
            (lambda: self.cap("the price: putting the tables back together", WHITE), 0.5),
            "To print a payment",
            (lambda: [Create(r15)], 0.5),
            (lambda: [travel(a_pm, YELLOW_M, 0.6)], 0.7),
            (lambda: [Create(rv)], 0.4),
            (lambda: [travel(a_mc, YELLOW_M, 0.5)], 0.6),
            (lambda: [Create(rc)], 0.4),
            "That's called a join",
            (lambda: self.cap("a join: the next lesson", WHITE), 0.5),
        ])
        self.steps("So split out the facts that belong to something else, like a shop or a category. Facts about the payment "
                   "itself stay on its row.", [
            (lambda: [FadeOut(VGroup(r15, rv, rc)), *self.cap("split out facts about something else: a shop, a category")], 0.6),
            "Facts about the payment",
            (lambda: [glow(pf, BLUE_M, 1.0), *self.cap("facts about the payment itself stay on its row")], 0.8),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, which spelling was right? Now the question can't come up again, because each fact has one home. "
                   "Store each fact once, keyed by what decides it, and point at it from everywhere else.", [
            (lambda: self.cap("which spelling was right?", WHITE), 0.5),
            "because each fact",
            (lambda: [glow(cf, TEAL_M, 1.0), glow(mf, TEAL_M, 1.0)], 0.9),
            "Store each fact",
            (lambda: self.cap("store each fact once, keyed by what decides it", YELLOW_M, 28), 0.6),
            "and point at it",
            (lambda: [travel(a_pm, YELLOW_M, 0.6), travel(a_mc, YELLOW_M, 0.6)], 0.9),
        ], after=0.5)
        o7011 = row_box(CF_X0 + 0.12, CF_X1 - 0.12, CROW_Y[0], YELLOW_M)
        self.steps("One quick check. The card companies rename category 7011, hotels, motels, resorts. "
                   "In the old file, how many rows had to change? And now? Pause and think.", [
            (lambda: [*self.uncap(), Create(o7011)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(c=(-3.3, -2.6))
        hh = [around(C["mer"][i], GOLD_M, 0.05) for i in (0, 3, 9)]
        self.steps("Three in that file: payments 13, 16 and 22, and more every night. Now, one row in the categories table.", [
            (lambda: [*self.uncap(), LaggedStart(*[Create(h) for h in hh], lag_ratio=0.3)], 1.0),
            "Now, one row",
            (lambda: [o7011.animate.set_stroke(GREEN_M), Create(tick(True, 0.15).move_to([6.05, CROW_Y[0], 0]))], 0.7),
        ], after=0.3)
        self.play(FadeOut(VGroup(*hh)), *self.cap("store each fact once, keyed by what decides it", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
