from sfz import *

# "pay nine" blends into "paid nine"; hyphenated, Kokoro keeps the words apart
SAY.insert(0, (r"\bpay-981\b", "pay-nine-eight-one"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bOpenSearch\b", "Open Search"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
C_C, R_C, I_C, D_C = BLUE_M, GOLD_M, PURPLE_M, WHITE      # capture, refund, index, database
CX = -4.9                                                  # the clients' x
DY, IY = 2.0, -1.6                                         # the database's row and the index's row
SX, SW, SH = 1.7, 5.2, 1.4                                 # the stores' x, width, height
LOG_Y, LOG_W, LOG_H = 0.2, 5.2, 1.0                        # the database's log (the fix)
TL_Y, CAP_Y, TOP_Y, BAR_Y = -2.78, -3.35, 3.2, -2.78
VAL_C = {"AUTHORIZED": GREY_B, "CAPTURED": C_C, "REFUNDED": R_C}


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
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def top(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, TOP_Y, 0])
        old, self.topm = self.topm, new
        return [swap(old, new)]

    def untop(self):
        old, self.topm = self.topm, None
        return [FadeOut(old)] if old is not None else []


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


# ---- the pieces ----
def store_box(y, color):
    return RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=color, stroke_width=3).set_fill(BLACK, 1).move_to([SX, y, 0])


def store_title(s, y, color=GREY_B):
    return T(s, 24, color).move_to([SX, y + 0.36, 0])


def value(v, y, color=None):
    k = M("pay-981", 28, WHITE)
    s = M(v, 28, color or VAL_C[v])
    return VGroup(k, s).arrange(RIGHT, buff=0.45).move_to([SX, y - 0.22, 0])


def client(name, sub, y, color):
    r = RoundedRectangle(corner_radius=0.14, width=3.0, height=1.2, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([CX, y, 0])
    return VGroup(r, T(name, 30).move_to([CX, y + 0.24, 0]), T(sub, 21, GREY_B).move_to([CX, y - 0.26, 0]))


def straight(y, color):
    return Arrow([CX + 1.5, y, 0], [SX - SW / 2, y, 0], buff=0.1, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.08)


def diag(y0, y1, color):
    """A client's arrow to the store on the other row: from its top or bottom edge to the store's left edge."""
    up = y1 > y0
    s = [CX + 0.85, y0 + (0.6 if up else -0.6), 0]
    e = [SX - SW / 2, y1 + (-0.35 if up else 0.35), 0]
    return Arrow(s, e, buff=0.1, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.08)


def tchip(s, color):
    t = M(s, 18, color)
    r = RoundedRectangle(corner_radius=0.08, width=2.55, height=0.44, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r))


def tl_pos(k):
    return [-4.2 + 2.8 * k, TL_Y, 0]


def run(arrow, color=YELLOW_M, rt=0.6):
    return travel(arrow, color, rt)


def order_card(k, seq, db, ix, x, y):
    """One of the six orders: four writes in order, then what each store ends with."""
    r = RoundedRectangle(corner_radius=0.12, width=4.1, height=1.55, stroke_color=GREY_C, stroke_width=2).set_fill("#0b0d10", 1).move_to([x, y, 0])
    toks = VGroup(*[M(s, 20, C_C if s[0] == "C" else R_C) for s in seq]).arrange(RIGHT, buff=0.28).move_to([x, y + 0.35, 0])
    ok = db == ix
    end = VGroup(M("db:", 15, GREY_B), M(db, 15, VAL_C[db]), M("ix:", 15, GREY_B), M(ix, 15, VAL_C[ix])).arrange(RIGHT, buff=0.1)
    end[2:].shift(0.15 * RIGHT)
    end.move_to([x - 0.25, y - 0.32, 0])
    mk = tick(ok, 0.12).move_to([x + 1.7, y - 0.32, 0])
    return VGroup(r, toks, end, mk), ok


ORDERS = [  # C = capture, R = refund; each writes its db first, then its index
    (["C db", "C ix", "R db", "R ix"], "REFUNDED", "REFUNDED"),
    (["C db", "R db", "C ix", "R ix"], "REFUNDED", "REFUNDED"),
    (["C db", "R db", "R ix", "C ix"], "REFUNDED", "CAPTURED"),
    (["R db", "C db", "C ix", "R ix"], "CAPTURED", "REFUNDED"),
    (["R db", "C db", "R ix", "C ix"], "CAPTURED", "CAPTURED"),
    (["R db", "R ix", "C db", "C ix"], "CAPTURED", "CAPTURED"),
]


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.7, height=3.6, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.4, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.1, 1.85)
    rows = VGroup()
    cw = M("x" * 40, 16).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 16, col), x - 3.1 + ind, 1.3 - 0.4 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["void setStatus(String id, String status) {",
        "    db.update(\"UPDATE payment SET status = ?",
        "               WHERE id = ?\", status, id);",
        "    // the gap: a pause here, and the",
        "    // other request slips in",
        "    index.update(id, Map.of(\"status\", status));",
        "}"]
KOTLIN = ["fun setStatus(id: String, status: String) {",
          "    db.update(\"UPDATE payment SET status = ?",
          "               WHERE id = ?\", status, id)",
          "    // the gap: a pause here, and the",
          "    // other request slips in",
          "    index.update(id, mapOf(\"status\" to status))",
          "}"]


class DualWrites(Base):
    """stream-01, section 0. Support sees CAPTURED for a refunded coffee: the search copy is rebuilt every night.
    The café's book and board: a batch job (the owner after closing) versus stream processing (a helper copying each
    receipt). The team's two-line version: each request writes PostgreSQL, then the index. The lesson's race on
    pay-981 (t1 to t4) leaves the index at CAPTURED with every call successful; two of the six orders break it; retries
    can't help and a crash between the lines loses the second write. Named a dual write, shown in Java and Kotlin.
    The way out from section 1: one writer, the database settles the race, and a follower applies its log in order
    with a bookmark. The price is lag. Moral and a check."""

class DualWrites(Base):
    """stream-01, section 0. Support sees CAPTURED for a refunded coffee: the search copy is rebuilt every night.
    The café's book and board: a batch job (the owner after closing) versus stream processing (a helper copying each
    receipt). The team's two-line version: each request writes PostgreSQL, then the index. The lesson's race on
    pay-981 (t1 to t4) leaves the index at CAPTURED with every call successful; two of the six orders break it; retries
    can't help and a crash between the lines loses the second write. Named a dual write, shown in Java and Kotlin.
    The way out from section 1: one writer, the database settles the race, and a follower applies its log in order
    with a bookmark. The price is lag. Moral and a check."""

    def construct(self):
        self.capm = self.topm = None
        self.title_card("Two writes, both succeed, still wrong", "why a database and its search copy drift apart")

        dbox, ibox = store_box(DY, D_C), store_box(IY, I_C)
        self.dt, self.it = store_title("payment records", DY), store_title("search copy: support's screen", IY)
        self.dv, self.iv = value("AUTHORIZED", DY), value("CAPTURED", IY)

        def set_dt(s, color=GREY_B):
            new = store_title(s, DY, color)
            old, self.dt = self.dt, new
            return [swap(old, new)]

        def set_it(s, color=GREY_B):
            new = store_title(s, IY, color)
            old, self.it = self.it, new
            return [swap(old, new)]

        def set_dv(v, color=None):
            new = value(v, DY, color)
            old, self.dv = self.dv, new
            return [swap(old, new, RIGHT)]

        def set_iv(v, color=None):
            new = value(v, IY, color)
            old, self.iv = self.iv, new
            return [swap(old, new, RIGHT)]

        # ---------------- scene 1: the support desk ----------------
        ref_chip = VGroup(T("customer", 24, GREY_B), T("refunded yesterday", 26, R_C)).arrange(DOWN, buff=0.15).move_to([CX, IY, 0])
        self.steps("Picture the support desk at a café payments company. A customer's coffee was refunded yesterday, "
                   "but support's screen still says captured.", [
            "A customer's",
            (lambda: [FadeIn(ref_chip, shift=0.2 * RIGHT)], 0.7),
            "but support's",
            (lambda: [FadeIn(ibox), FadeIn(self.it)], 0.6),
            "still says",
            (lambda: [FadeIn(self.iv)], 0.5),
            (lambda: [Indicate(self.iv[1], color=C_C, scale_factor=1.15)], 0.7),
        ])
        self.steps("That screen reads a copy, rebuilt every night, so it's a day behind.", [
            "rebuilt every night",
            (lambda: self.cap("the copy: rebuilt every night at 2:00, so a day behind"), 0.6),
        ])
        rule = T("whenever a payment changes: update the records, then the copy", 26, GREY_B).move_to([0, TOP_Y, 0])
        self.steps("So the team stops waiting for the night. Whenever a payment changes, the program updates the records, "
                   "then the copy. Two lines of code, and every test passes.", [
            (lambda: [FadeOut(ref_chip), *self.uncap()], 0.5),
            "Whenever a payment",
            (lambda: [FadeIn(dbox), FadeIn(self.dt), FadeIn(self.dv), FadeIn(rule, shift=0.1 * DOWN)], 0.9),
            "every test passes",
            (lambda: self.cap("every test passes", GREEN_M, 28), 0.5),
        ])
        qm = T("?", 72, YELLOW_M).move_to([CX, 0.2, 0])
        self.steps("A month later, one payment says refunded in the records and captured on the screen, for good, with no error anywhere. "
                   "How can two writes that both succeed disagree?", [
            (lambda: self.uncap(), 0.3),
            "says refunded",
            (lambda: [*set_dv("REFUNDED"), *set_iv("CAPTURED", RED_M), ibox.animate.set_stroke(RED_M)], 0.8),
            "for good",
            (lambda: self.cap("no error, no retry, no line in any log", RED_M, 28), 0.5),
            "How can",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.6)

        # ---------------- scene 2: the café, a batch and a stream ----------------
        down = Arrow([SX, DY - SH / 2, 0], [SX, IY + SH / 2, 0], buff=0.1, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.12)
        self.steps("Picture the café itself. By the till, a book where every sale is written down. In the back, a board the staff read from.", [
            (lambda: [FadeOut(qm), FadeOut(rule), *self.uncap(), FadeOut(self.dv), FadeOut(self.iv), ibox.animate.set_stroke(I_C)], 0.7),
            "By the till",
            (lambda: set_dt("the book by the till", WHITE), 0.7),
            "In the back",
            (lambda: set_it("the board in the back", I_C), 0.7),
        ])
        self.dv = self.iv = None
        self.steps("One way to fill the board: after closing, the owner rewrites it from the day's receipts. Right, but only once a day. "
                   "A program that works through a whole pile in one run like that is a batch job.", [
            "after closing",
            (lambda: [GrowArrow(down), *self.cap("after closing: the whole pile at once")], 0.7),
            (lambda: [LaggedStart(*[run(down, GREY_B, 0.7) for _ in range(6)], lag_ratio=0.08)], 1.2),
            "Right, but",
            (lambda: self.cap("right, but only once a day"), 0.5),
            "A program",
            (lambda: self.cap("a batch job: a whole pile, in one run", WHITE, 28), 0.6),
        ])
        self.steps("The other way: a helper copies each receipt onto the board as the till prints it. "
                   "Each receipt is an event, a record of one thing that happened, and handling each event as it arrives is stream processing.", [
            "a helper copies",
            (lambda: [*self.cap("a helper: one receipt at a time, as it's printed"), run(down, YELLOW_M, 0.8)], 0.9),
            (lambda: [run(down, YELLOW_M, 0.8)], 0.9),
            "Each receipt is",
            (lambda: [*self.cap("an event: a record of one thing that happened"), run(down, YELLOW_M, 0.8)], 0.9),
            "and handling",
            (lambda: [run(down, YELLOW_M, 0.8)], 0.9),
            "stream processing",
            (lambda: self.cap("stream processing: handle each event as it arrives", WHITE, 28), 0.6),
        ])

        # ---------------- scene 3: the program ----------------
        self.steps("In the program, the book is the database, where each payment is stored. Here it's PostgreSQL, a free database many companies run.", [
            (lambda: [FadeOut(down), *self.uncap()], 0.5),
            "the book is",
            (lambda: set_dt("the database: PostgreSQL", WHITE), 0.7),
            (lambda: set_dv("AUTHORIZED"), 0.5),
        ])
        self.steps("The board is a search index, a copy built for fast searching, like the index at the back of a book. "
                   "It lives in OpenSearch, a free program for such indexes.", [
            "The board is",
            (lambda: set_it("the search index: OpenSearch", I_C), 0.7),
            (lambda: set_iv("AUTHORIZED"), 0.5),
        ])
        legend = VGroup(*[VGroup(M(a, 22, c), T(b, 22, GREY_B)).arrange(RIGHT, buff=0.18) for a, c, b in
                          [("AUTHORIZED", GREY_B, "money set aside"), ("CAPTURED", C_C, "money moved"), ("REFUNDED", R_C, "money back")]])
        legend.arrange(RIGHT, buff=0.6).move_to([0, CAP_Y, 0])
        self.steps("A payment's status goes from authorized, money set aside, to captured, money moved, and maybe refunded.", [
            "from authorized",
            (lambda: [FadeIn(legend[0])], 0.5),
            "to captured",
            (lambda: [FadeIn(legend[1])], 0.5),
            "and maybe",
            (lambda: [FadeIn(legend[2])], 0.5),
        ])
        cap_c = client("capture", "sets CAPTURED", DY, C_C)
        ref_c = client("refund", "sets REFUNDED", IY, R_C)
        self.steps("And there's no helper. Each request is a cashier who writes the book, then walks to the board and writes it there too.", [
            (lambda: [FadeOut(legend)], 0.4),
            "Each request",
            (lambda: [FadeIn(cap_c, shift=0.2 * RIGHT), FadeIn(ref_c, shift=0.2 * RIGHT)], 0.8),
            "writes the book",
            (lambda: [glow(dbox, WHITE, 1.03)], 0.7),
            "walks to the board",
            (lambda: [glow(ibox, I_C, 1.03)], 0.7),
        ])

        # ---------------- scene 4: the race ----------------
        self.stamp("race")
        self.steps("Two requests for pay-981 arrive a millisecond apart, each on its own thread, a line of work running at the same time: "
                   "a capture, and the shop's refund.", [
            "each on its own",
            (lambda: self.cap("two threads: two lines of work at the same time"), 0.5),
            "a capture",
            (lambda: [glow(cap_c[0], C_C, 1.05)], 0.6),
            "the shop's refund",
            (lambda: [glow(ref_c[0], R_C, 1.05)], 0.6),
        ])
        c_db, r_ix = straight(DY, C_C), straight(IY, R_C)
        c_ix, r_db = diag(DY, IY, C_C), diag(IY, DY, R_C)
        tl = [tchip("t1  db: CAPTURED", C_C), tchip("t2  db: REFUNDED", R_C), tchip("t3  ix: REFUNDED", R_C), tchip("t4  ix: CAPTURED", RED_M)]
        for k, c in enumerate(tl):
            c.move_to(tl_pos(k))
        paused = T("paused", 24, RED_M).move_to([CX - 0.6, DY - 0.9, 0])
        self.steps("The capture writes the database: captured. Then it stalls for a couple of milliseconds, say while the program "
                   "clears out unused memory. A cashier stopped on the way to the board.", [
            (lambda: [*self.uncap(), GrowArrow(c_db)], 0.5),
            (lambda: [run(c_db, C_C)], 0.6),
            (lambda: [*set_dv("CAPTURED"), FadeIn(tl[0], shift=0.1 * UP)], 0.6),
            "Then it stalls",
            (lambda: [FadeOut(c_db), cap_c[0].animate.set_stroke(GREY_D), cap_c[1].animate.set_color(GREY_C), FadeIn(paused)], 0.7),
        ])
        self.steps("The refund writes the database: refunded. Right, the refund came second.", [
            (lambda: [GrowArrow(r_db)], 0.5),
            (lambda: [run(r_db, R_C)], 0.6),
            (lambda: [*set_dv("REFUNDED"), FadeIn(tl[1], shift=0.1 * UP)], 0.6),
            "Right, the",
            (lambda: [Indicate(self.dv[1], color=GREEN_M)], 0.8),
        ])
        self.steps("It writes the index too: refunded.", [
            (lambda: [FadeOut(r_db), GrowArrow(r_ix)], 0.5),
            (lambda: [run(r_ix, R_C)], 0.6),
            (lambda: [*set_iv("REFUNDED"), FadeIn(tl[2], shift=0.1 * UP)], 0.6),
        ])
        self.steps("Then the capture wakes up and makes its second write. The index now says captured.", [
            (lambda: [FadeOut(r_ix), FadeOut(paused), cap_c[0].animate.set_stroke(C_C), cap_c[1].animate.set_color(WHITE)], 0.6),
            "makes its second",
            (lambda: [GrowArrow(c_ix)], 0.5),
            (lambda: [run(c_ix, C_C, 0.7)], 0.7),
            "The index now",
            (lambda: [*set_iv("CAPTURED", RED_M), FadeIn(tl[3], shift=0.1 * UP), ibox.animate.set_stroke(RED_M)], 0.7),
        ])
        oks = VGroup(*[tick(True, 0.12).next_to(c, DOWN, buff=0.14) for c in tl])
        self.steps("Every call returned success. No error, no retry, no log line. "
                   "And the index stays wrong until pay-981 changes again, which may be never.", [
            (lambda: [FadeOut(c_ix), LaggedStart(*[Create(o) for o in oks], lag_ratio=0.25)], 1.0),
            "And the index stays",
            (lambda: [glow(ibox, RED_M, 1.03)], 0.8),
        ])
        self.stamp("poster")
        self.steps("Both cashiers did exactly what they were told, and the board is wrong anyway. Nobody to blame, which is somehow worse. "
                   "The bug lives in the gap between the two writes.", [
            "The bug lives",
            (lambda: [FadeOut(oks), *self.cap("each line is right on its own; the trouble is between them", YELLOW_M)], 0.6),
        ], after=0.5)

        # ---------------- scene 5: predict how many orders break it ----------------
        diagram = VGroup(dbox, ibox, self.dt, self.it, self.dv, self.iv, cap_c, ref_c, *tl)
        cards = []
        for k, (seq, db, ix) in enumerate(ORDERS):
            x, y = [-4.35, 0, 4.35][k % 3], [1.15, -0.75][k // 3]
            cards.append(order_card(k, seq, db, ix, x, y))
        legend2 = T("C = capture, R = refund; db = the database, ix = the index", 24, GREY_B).move_to([0, 2.75, 0])
        self.steps("Was that bad luck? Each request writes the database, then the index, so the four writes can mix in six ways. "
                   "How many of the six leave the stores different? Pause and guess.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.02)], 0.6),
            "Each request",
            (lambda: [FadeIn(legend2)], 0.5),
            "can mix in six",
            (lambda: [LaggedStart(*[FadeIn(VGroup(c[0][0], c[0][1])) for c in cards], lag_ratio=0.15)], 1.4),
            "Pause and guess",
            (lambda: self.cap("how many of the six? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Two. The one we saw, and its mirror, where the database ends captured and the index refunded.", [
            (lambda: [*self.uncap(), LaggedStart(*[FadeIn(VGroup(c[0][2], c[0][3])) for c in cards], lag_ratio=0.12)], 1.2),
            "The one we saw",
            (lambda: [cards[2][0][0].animate.set_stroke(RED_M, 4)], 0.5),
            "its mirror",
            (lambda: [cards[3][0][0].animate.set_stroke(RED_M, 4)], 0.5),
        ])
        self.steps("In the other four, whoever wrote the database last also wrote the index last. Nothing in the code makes that true. "
                   "The timing usually does, and that's why every test passed.", [
            "In the other four",
            (lambda: [*[cards[k][0][0].animate.set_stroke(GREEN_M, 3) for k in (0, 1, 4, 5)]], 0.6),
            "Nothing in the code",
            (lambda: self.cap("nothing in the code keeps the two orders the same", WHITE), 0.5),
            "The timing",
            (lambda: self.cap("the timing usually does, so every test passes"), 0.5),
        ])
        self.steps("Four out of six is a fine score on a test. For payments, not so much.", [], after=0.4)

        # ---------------- scene 6: retries, and the second door ----------------
        self.steps("You might think: we retry on errors. But nothing failed here, so there was nothing to retry.", [
            (lambda: [*self.uncap(), FadeOut(legend2), *[FadeOut(c[0]) for c in cards], diagram.animate.set_opacity(1)], 0.8),
            "we retry",
            (lambda: self.cap("retry on errors?"), 0.5),
            "But nothing",
            (lambda: [*self.cap("no error, so no retry", RED_M, 28), LaggedStart(*[glow(c[0], GREEN_M, 1.05) for c in tl], lag_ratio=0.2)], 1.0),
        ])
        crash = VGroup(tick(False, 0.2), T("crash", 24, RED_M)).arrange(RIGHT, buff=0.15).move_to([CX - 0.4, 0.2, 0])
        self.steps("And a real failure opens a second door. If the program crashes between the two lines, after a restart "
                   "it doesn't know a second write was owed. One store has the change, and the other never will.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*tl)), *set_dv("AUTHORIZED"), *set_iv("AUTHORIZED"), ibox.animate.set_stroke(I_C)], 0.7),
            "If the program",
            (lambda: [GrowArrow(c_db)], 0.4),
            (lambda: [run(c_db, C_C)], 0.6),
            (lambda: set_dv("CAPTURED"), 0.4),
            "between the two",
            (lambda: [FadeIn(crash, scale=0.6), *self.cap("a crash between the two lines", RED_M)], 0.6),
            "after a restart",
            (lambda: self.cap("after a restart, nobody knows a second write was owed", RED_M), 0.5),
            "One store has",
            (lambda: [glow(dbox, WHITE, 1.03), glow(ibox, RED_M, 1.03)], 0.9),
        ])

        # ---------------- scene 7: the name, and the code ----------------
        self.steps("This pattern is called a dual write: one change sent to two systems, one after the other, "
                   "with nothing tying them together.", [
            (lambda: [FadeOut(crash), FadeOut(c_db), *self.uncap()], 0.5),
            "a dual write",
            (lambda: self.top("a dual write: one change, sent to two systems, one after the other", WHITE, 26), 0.7),
        ])
        jp, kp = code_panel("Java", JAVA, -3.45), code_panel("Kotlin", KOTLIN, 3.45)
        diag2 = VGroup(dbox, ibox, self.dt, self.it, self.dv, self.iv, cap_c, ref_c)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, it's these two lines, and the gap sits between them.", [
            (lambda: [diag2.animate.set_opacity(0.06), *self.untop()], 0.5),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.6),
            "these two lines",
            (lambda: [*hl((1, 2), WHITE), *hl((5,), I_C)], 1.0),
            "the gap",
            (lambda: hl((3, 4), YELLOW_M), 1.0),
        ], after=1.2)
        self.steps("Both problems have one root: two writers, each deciding the order.", [
            (lambda: [FadeOut(jp), FadeOut(kp), diag2.animate.set_opacity(1)], 0.7),
            "two writers",
            (lambda: [glow(cap_c[0], C_C, 1.05), glow(ref_c[0], R_C, 1.05), *self.top("two writers, each picking its own order", RED_M, 26)], 0.9),
        ])

        # ---------------- scene 8: one writer, and its price ----------------
        logb = RoundedRectangle(corner_radius=0.12, width=LOG_W, height=LOG_H, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        logb.move_to([SX, LOG_Y, 0])
        log_t = T("numbered receipts, in order", 20, GREY_B).move_to([SX, LOG_Y + 0.27, 0])
        to_log = Arrow([SX, DY - SH / 2, 0], [SX, LOG_Y + LOG_H / 2, 0], buff=0.06, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.3)
        fol = Arrow([SX, LOG_Y - LOG_H / 2, 0], [SX, IY + SH / 2, 0], buff=0.06, stroke_width=3, color=I_C, max_tip_length_to_length_ratio=0.3)
        fol_y = (LOG_Y - LOG_H / 2 + IY + SH / 2) / 2
        fol_l = left_at(T("helper", 20, I_C), SX + 0.25, fol_y)
        self.steps("Back to the café. Let only the till decide the order. It numbers each receipt, and the helper copies them "
                   "in number order, noting the last number so it can carry on after a break.", [
            (lambda: [*self.untop(), *set_dv("AUTHORIZED"), *set_iv("AUTHORIZED"), ibox.animate.set_stroke(I_C)], 0.7),
            "only the till",
            (lambda: [GrowArrow(to_log), FadeIn(logb), FadeIn(log_t)], 0.8),
            "and the helper",
            (lambda: [GrowArrow(fol), FadeIn(fol_l)], 0.7),
        ])
        r_db2 = diag(IY, DY, R_C)
        c_db2 = straight(DY, C_C)
        waits = T("waits its turn", 24, R_C).move_to([CX + 0.2, IY - 0.95, 0])
        e1 = VGroup(M("768", 18, GREY_B), M("CAPTURED", 18, C_C)).arrange(RIGHT, buff=0.2)
        e2 = VGroup(M("769", 18, GREY_B), M("REFUNDED", 18, R_C)).arrange(RIGHT, buff=0.2)
        VGroup(e1, e2).arrange(RIGHT, buff=0.8).move_to([SX, LOG_Y - 0.2, 0])
        self.steps("In the program, requests write only the database, and the database settles the race. The capture holds the row, "
                   "so the refund waits its turn. Its log records the capture first, then the refund.", [
            (lambda: [*set_dt("the database: the only writer", WHITE), *set_it("the search index: a follower", I_C),
                      Transform(log_t, T("the database's log, in commit order", 20, GREY_B).move_to(log_t)),
                      Transform(fol_l, left_at(T("follower", 20, I_C), SX + 0.25, fol_y))], 0.8),
            "the database settles",
            (lambda: [GrowArrow(c_db2), GrowArrow(r_db2)], 0.6),
            "The capture holds",
            (lambda: [run(c_db2, C_C)], 0.6),
            (lambda: set_dv("CAPTURED"), 0.4),
            "so the refund waits",
            (lambda: [FadeIn(waits)], 0.5),
            "Its log records",
            (lambda: [FadeIn(e1, shift=0.1 * DOWN)], 0.5),
            "then the refund",
            (lambda: [FadeOut(waits), run(r_db2, R_C)], 0.6),
            (lambda: [*set_dv("REFUNDED"), FadeIn(e2, shift=0.1 * DOWN)], 0.5),
        ])
        bm = T("bookmark: 768", 20, GREY_B)
        bm.move_to([SX - 0.25 - bm.width / 2, fol_y, 0])
        self.bm = None

        def set_bm(n):
            new = T(f"bookmark: {n}", 20, GREY_B).move_to(bm)
            old, self.bm = self.bm, new
            return [swap(old, new)]

        self.steps("A follower applies that log to the index in order, keeping a bookmark of how far it got. Both stores end at refunded.", [
            (lambda: [FadeOut(c_db2), FadeOut(r_db2)], 0.4),
            "applies that log",
            (lambda: [Indicate(e1, color=C_C, scale_factor=1.08), run(fol, C_C, 0.6)], 0.7),
            (lambda: [*set_iv("CAPTURED"), *set_bm(768)], 0.5),
            (lambda: [Indicate(e2, color=R_C, scale_factor=1.08), run(fol, R_C, 0.6)], 0.7),
            (lambda: [*set_iv("REFUNDED"), *set_bm(769)], 0.5),
            "Both stores",
            (lambda: [Indicate(self.dv[1], color=GREEN_M), Indicate(self.iv[1], color=GREEN_M)], 0.9),
        ])
        self.steps("The price is lag: the index hears each change a few milliseconds late. "
                   "But it can't get the order wrong, because it no longer picks one.", [
            (lambda: self.cap("the price: lag, a few milliseconds behind"), 0.5),
            "But it can't",
            (lambda: [*self.cap("but no order of its own to get wrong", WHITE), Indicate(e1, color=C_C, scale_factor=1.06),
                      Indicate(e2, color=R_C, scale_factor=1.06)], 1.0),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, two writers pick two orders. Give the data one writer, and let every copy follow its log. "
                   "Now the customer's refund shows on support's screen.", [
            (lambda: self.cap("two writers, two orders", RED_M, 28), 0.5),
            "Give the data",
            (lambda: self.cap("one writer; every copy follows its log", YELLOW_M, 32), 0.6),
            "Now the customer's",
            (lambda: [glow(ibox, GREEN_M, 1.03)], 0.9),
        ], after=0.5)
        r_db3 = diag(IY, DY, R_C)
        crash2 = VGroup(tick(False, 0.2), T("crash", 24, RED_M)).arrange(RIGHT, buff=0.15).move_to([CX - 0.4, 0.2, 0])
        self.steps("One quick check. With the follower in place, the program crashes right after the refund's database write. "
                   "What does the index end up saying? Pause and think.", [
            (lambda: [*self.uncap(), *set_iv("CAPTURED"), FadeOut(e2), *set_bm(768), *set_dv("CAPTURED")], 0.6),
            "the program crashes",
            (lambda: [GrowArrow(r_db3)], 0.4),
            (lambda: [run(r_db3, R_C)], 0.6),
            (lambda: [*set_dv("REFUNDED"), FadeIn(e2, shift=0.1 * DOWN), FadeOut(r_db3), FadeIn(crash2, scale=0.6)], 0.6),
            "Pause and think",
            (lambda: self.cap("what does the index end up saying? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Refunded. The change is already in the log, and the follower picks it up from its bookmark. "
                   "Nobody had to remember a second write.", [
            (lambda: [*self.uncap(), Indicate(e2, color=R_C, scale_factor=1.08), run(fol, R_C, 0.7)], 0.8),
            (lambda: [*set_iv("REFUNDED"), *set_bm(769)], 0.5),
            "Nobody had",
            (lambda: self.cap("one writer; every copy follows its log", YELLOW_M, 32), 0.6),
        ], after=0.3)
        self.play(Create(tick(True, 0.2).move_to([SX + SW / 2 + 0.45, IY, 0])), run_time=0.6)
        self.wait(2.0)
