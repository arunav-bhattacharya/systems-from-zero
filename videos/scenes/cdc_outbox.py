from sfz import *

SAY.insert(0, (r"\bpay-(\d+)\b", r"pay \1"))
SAY.insert(0, (r"\be-(\d+)\b", r"E \1"))
SAY.insert(0, (r"\bacct-(\d+)\b", r"account \1"))
SAY.insert(0, (r"\bBEGIN\b", "begin"))
SAY.insert(0, (r"\bCOMMIT\b", "commit"))
SAY.insert(0, (r"\bPaymentAuthorized\b", "payment authorized"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bDebezium\b", "dee-bee-zee-um"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
P_C, P_W, P_H = np.array([-4.6, 3.0, 0]), 3.6, 0.7              # the payments program
DB_C, DB_W, DB_H = np.array([-3.4, 0.5, 0]), 6.0, 3.0            # the database
PAY_C, OUT_C, CW, CH = np.array([-4.85, 0.2, 0]), np.array([-1.95, 0.2, 0]), 2.7, 1.9
LOG_Y, LOG_X = -1.85, [-5.45, -3.65, -1.85, -0.05]               # the database's log
DZ_C, DZ_W, DZ_H = np.array([4.7, -1.85, 0]), 3.6, 0.8           # Debezium
TP_C, TP_W, TP_H = np.array([4.7, 0.45, 0]), 3.8, 2.4            # the Kafka topic
LD_C, LD_W, LD_H = np.array([4.7, 2.85, 0]), 3.4, 1.0            # the ledger
REC_Y = [0.55, 0.08, -0.39]
CAP_Y, TOP_Y, BAR_Y = -3.3, 3.3, -2.72
P_COL, DB_COL, OB_COL, DZ_COL, TP_COL, LD_COL = GOLD_M, WHITE, YELLOW_M, TEAL_M, BLUE_M, GREEN_M


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




def rbox(c, w, h, color, fill=True):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    return r.set_fill(fillc(color) if fill else BLACK, 1).move_to(c)


def card(c, name, color):
    r = RoundedRectangle(corner_radius=0.1, width=CW, height=CH, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1).move_to(c)
    return VGroup(r, M(name, 22, color).move_to(c + [0, CH / 2 - 0.3, 0]))


def lchip(s, color=GREY_B, k=0):
    t = M(s, 14, color)
    r = RoundedRectangle(corner_radius=0.07, width=1.72, height=0.46, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).move_to([LOG_X[k], LOG_Y, 0])


def record(s, k, color=TP_COL):
    t = M(s, 16, color)
    r = RoundedRectangle(corner_radius=0.07, width=3.3, height=0.42, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).move_to([TP_C[0], REC_Y[k], 0])


def run(arrow, color=YELLOW_M, rt=0.6):
    return travel(arrow, color, rt)


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.7, height=3.0, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.5, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.1, 1.65)
    rows = VGroup()
    cw = M("x" * 40, 16).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if "//" in s else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 16, col), x - 3.1 + ind, 1.1 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["conn.setAutoCommit(false);",
        "insertPayment(conn, \"pay-3\", \"acct-17\");",
        "insertOutbox(conn, \"e-66\", \"payment\",",
        "    \"acct-17\", \"PaymentAuthorized\", payload);",
        "conn.commit();  // both rows, or neither"]
KOTLIN = ["conn.autoCommit = false",
          "insertPayment(conn, \"pay-3\", \"acct-17\")",
          "insertOutbox(conn, \"e-66\", \"payment\",",
          "    \"acct-17\", \"PaymentAuthorized\", payload)",
          "conn.commit()  // both rows, or neither"]


class CdcOutbox(Base):
    """stream-02, section 3. The payments program saves pay-3 and must tell the ledger with PaymentAuthorized.
    Save-then-send is a dual write (a crash loses the event; send-first announces a payment that never saved).
    Plain CDC on the payment table leaks the table's shape and can't say why. The carbon-copy form: one stroke writes
    the sale and the courier's note. The outbox: payment row and outbox row in one transaction (BEGIN 771 ... COMMIT 771),
    Debezium reads only the outbox; pay-4/e-77 rolls back and never leaves. The outbox router: topic
    outbox.event.payment, key acct-17, id e-66 in a header. Poller's trap; at-least-once (e-88 twice) and dedupe on the
    id. Java and Kotlin, the moral, a check."""

    def construct(self):
        self.capm = self.topm = None
        self.title_card("Save it and say it, together", "the transactional outbox")

        prog = rbox(P_C, P_W, P_H, P_COL)
        prog_t = T("payments program", 26).move_to(P_C)
        dbb = rbox(DB_C, DB_W, DB_H, DB_COL, fill=False)
        db_t = left_at(T("database: PostgreSQL", 22, GREY_B), DB_C[0] - DB_W / 2 + 0.25, DB_C[1] + DB_H / 2 - 0.3)
        payc = card(PAY_C, "payment", DB_COL)
        outc = card(OUT_C, "outbox", OB_COL)
        led = rbox(LD_C, LD_W, LD_H, LD_COL)
        led_t = T("the ledger", 26).move_to(LD_C + [0, 0.2, 0])
        tp = rbox(TP_C, TP_W, TP_H, TP_COL, fill=False)
        tp_t = T("Kafka topic", 24).move_to(TP_C + [0, TP_H / 2 - 0.32, 0])
        dz = rbox(DZ_C, DZ_W, DZ_H, DZ_COL)
        dz_t = T("Debezium", 26).move_to(DZ_C)
        save_a = Arrow(P_C + [0, -P_H / 2, 0], [P_C[0], DB_C[1] + DB_H / 2, 0], buff=0.05, stroke_width=3, color=P_COL, max_tip_length_to_length_ratio=0.35)
        send_a = Arrow(P_C + [P_W / 2, 0, 0], TP_C + [-TP_W / 2, 0.75, 0], buff=0.1, stroke_width=3, color=P_COL, max_tip_length_to_length_ratio=0.05)
        to_led = Arrow(TP_C + [0, TP_H / 2, 0], LD_C + [0, -LD_H / 2, 0], buff=0.06, stroke_width=3, color=TP_COL, max_tip_length_to_length_ratio=0.3)
        log_l = left_at(T("the database's log", 18, GREY_B), -6.3, LOG_Y + 0.5)
        log_a = Arrow([0.85, LOG_Y, 0], DZ_C + [-DZ_W / 2, 0, 0], buff=0.08, stroke_width=3, color=DZ_COL, max_tip_length_to_length_ratio=0.05)
        dz_a = Arrow(DZ_C + [0, DZ_H / 2, 0], TP_C + [0, -TP_H / 2, 0], buff=0.06, stroke_width=3, color=DZ_COL, max_tip_length_to_length_ratio=0.3)

        self.rows = {}
        self.recs = [None, None, None]
        self.logc = [None] * 4
        self.ls = None

        def row(card_c, k, s, color=WHITE):
            return M(s, 17, color).move_to(card_c + [0, 0.25 - 0.5 * k, 0])

        def set_row(key, card_c, k, s, color=WHITE):
            new = row(card_c, k, s, color)
            old = self.rows.get(key)
            self.rows[key] = new
            return [swap(old, new, RIGHT)]

        def drop_row(key):
            old = self.rows.pop(key, None)
            return [FadeOut(old)] if old is not None else []

        def set_rec(k, s, color=TP_COL):
            new = record(s, k, color)
            old, self.recs[k] = self.recs[k], new
            return [swap(old, new, DOWN)]

        def clear_recs():
            olds = [r for r in self.recs if r is not None]
            self.recs = [None, None, None]
            return [FadeOut(r) for r in olds]

        def set_log(k, s, color=GREY_B):
            new = lchip(s, color, k)
            old, self.logc[k] = self.logc[k], new
            return [swap(old, new, DOWN)]

        def clear_log():
            olds = [c for c in self.logc if c is not None]
            self.logc = [None] * 4
            return [FadeOut(c) for c in olds]

        def set_ls(s, color=GREY_B):
            new = T(s, 20, color).move_to(LD_C + [0, -0.22, 0])
            old, self.ls = self.ls, new
            return [swap(old, new)]

        # ---------------- scene 1: the question ----------------
        self.steps("The payments program has just authorized a payment, pay-3: the bank has set the money aside. "
                   "It saves the payment's row in its database, PostgreSQL.", [
            (lambda: [FadeIn(prog), FadeIn(prog_t)], 0.7),
            "It saves",
            (lambda: [FadeIn(dbb), FadeIn(db_t), FadeIn(payc), GrowArrow(save_a)], 0.8),
            (lambda: [run(save_a, P_COL, 0.5)], 0.5),
            (lambda: set_row("p1", PAY_C, 0, "pay-3  AUTHORIZED"), 0.5),
        ])
        self.steps("Now the ledger, the program that books every movement of money, needs to hear about it.", [
            "Now the ledger",
            (lambda: [FadeIn(led), FadeIn(led_t)], 0.7),
            (lambda: set_ls("waiting to hear", GREY_B), 0.4),
        ])
        self.steps("The message is an event called PaymentAuthorized. It travels through Kafka, a program that keeps streams of messages "
                   "in order, for other programs to read.", [
            "an event called",
            (lambda: self.cap("PaymentAuthorized: an event, a record of one thing that happened", WHITE), 0.6),
            "It travels",
            (lambda: [FadeIn(tp), FadeIn(tp_t), GrowArrow(to_led)], 0.8),
        ])
        self.steps("So how do we get the event out exactly when the row is saved, and never when it isn't?", [
            (lambda: self.cap("the event when the row is saved, and never when it isn't", YELLOW_M, 26), 0.6),
        ], after=0.5)

        # ---------------- scene 2: save, then send ----------------
        crash = VGroup(tick(False, 0.18), T("crash", 22, RED_M)).arrange(RIGHT, buff=0.12).move_to(send_a.get_center() + 0.4 * UP)
        self.steps("The obvious way: save the row, then send the event. But that's a dual write, two writes to two systems "
                   "with nothing tying them together.", [
            (lambda: [*self.uncap(), *drop_row("p1")], 0.4),
            "save the row",
            (lambda: [run(save_a, P_COL, 0.5)], 0.5),
            (lambda: set_row("p1", PAY_C, 0, "pay-3  AUTHORIZED"), 0.4),
            "then send",
            (lambda: [GrowArrow(send_a)], 0.6),
            "a dual write",
            (lambda: self.cap("a dual write: two systems, nothing tying them together"), 0.5),
        ])
        self.steps("Crash between the lines, and the payment is saved, but the ledger never hears.", [
            "Crash between",
            (lambda: [FadeIn(crash, scale=0.6)], 0.5),
            "but the ledger",
            (lambda: [*set_ls("never heard of pay-3", RED_M), led.animate.set_stroke(RED_M)], 0.6),
        ])
        ghost = T("no such payment", 20, RED_M).move_to(PAY_C + [0, -0.55, 0])
        self.steps("Swap the lines, and it's worse. Send first, then crash before the save, and the ledger books a payment "
                   "that doesn't exist.", [
            (lambda: [FadeOut(crash), *drop_row("p1"), *set_ls("waiting to hear"), led.animate.set_stroke(LD_COL)], 0.5),
            "Send first",
            (lambda: [run(send_a, P_COL, 0.6)], 0.6),
            (lambda: set_rec(0, "PaymentAuthorized pay-3"), 0.4),
            (lambda: [run(to_led, TP_COL, 0.5)], 0.5),
            (lambda: set_ls("booked pay-3"), 0.4),
            "then crash",
            (lambda: [FadeIn(crash.move_to(save_a.get_center() + 1.1 * RIGHT), scale=0.6)], 0.5),
            "that doesn't exist",
            (lambda: [FadeIn(ghost), *set_ls("booked pay-3: a ghost", RED_M), led.animate.set_stroke(RED_M)], 0.6),
        ])
        self.steps("So one order loses news, and the other spreads rumours. Neither is what a ledger wants. "
                   "Two systems, and no all or nothing between them.", [
            "Two systems",
            (lambda: self.cap("two systems, and no all-or-nothing between them", RED_M), 0.5),
        ], after=0.4)

        # ---------------- scene 3: follow the table instead ----------------
        self.steps("Second try: don't send at all. Let Debezium, a program that reads a database's log and turns each change into a message, "
                   "follow the payment table.", [
            (lambda: [*self.uncap(), FadeOut(crash), FadeOut(ghost), FadeOut(send_a), *clear_recs(), *set_ls("waiting to hear"),
                      led.animate.set_stroke(LD_COL)], 0.6),
            "Let Debezium",
            (lambda: [FadeIn(dz), FadeIn(dz_t), FadeIn(log_l), GrowArrow(log_a), GrowArrow(dz_a)], 0.9),
            "follow the payment",
            (lambda: [*set_row("p1", PAY_C, 0, "pay-3  CAPTURED"), *set_log(0, "UPDATE pay-3")], 0.5),
            (lambda: [run(log_a, DZ_COL, 0.7)], 0.7),
            (lambda: [run(dz_a, DZ_COL, 0.4)], 0.4),
            (lambda: set_rec(0, "pay-3 status=CAPTURED"), 0.4),
        ])
        why = T("why?", 24, RED_M).move_to(TP_C + [0, -0.55, 0])
        self.steps("No dual write now. But every reader gets your table's columns, so renaming one breaks them. "
                   "And the message says only what the row became. Captured? Or someone fixing a mistake? It can't say why.", [
            "But every reader",
            (lambda: self.cap("readers get your table's shape: rename a column, break them", RED_M), 0.5),
            "And the message",
            (lambda: [Indicate(self.recs[0], color=TP_COL, scale_factor=1.05)], 0.7),
            "It can't say",
            (lambda: [FadeIn(why)], 0.5),
        ])
        self.steps("What we want is an event we designed, saved together with the row, so both happen or neither does.", [
            (lambda: self.cap("wanted: a designed event, saved with the row, both or neither", YELLOW_M, 26), 0.6),
        ], after=0.4)

        # ---------------- scene 4: the carbon-copy form ----------------
        diagram = VGroup(prog, prog_t, dbb, db_t, payc, led, led_t, tp, tp_t, dz, dz_t, save_a, to_led, log_l, log_a, dz_a,
                         self.rows["p1"], self.logc[0], self.recs[0], self.ls, why)
        top_s = RoundedRectangle(corner_radius=0.06, width=4.2, height=2.4, stroke_color=WHITE, stroke_width=2.5).set_fill("#101214", 1).move_to([-0.6, 0.6, 0])
        bot_s = RoundedRectangle(corner_radius=0.06, width=4.2, height=2.4, stroke_color=OB_COL, stroke_width=2.5).set_fill("#141208", 1).move_to([0.0, 0.0, 0])
        top_l = T("sale: pay-3", 26).move_to(top_s.get_center() + [0, 0.25, 0])
        bot_l = T("courier's note", 24, OB_COL).move_to(bot_s.get_center() + [0.6, -0.8, 0])
        pen = Line(top_s.get_center() + [-1.2, -0.25, 0], top_s.get_center() + [1.2, -0.25, 0], stroke_width=4, color=WHITE)
        pen2 = pen.copy().set_color(OB_COL).shift([0.6, -0.6, 0])
        self.steps("Think of an old carbon-copy form at a shop. You write the sale on the top sheet, and the same stroke of the pen "
                   "writes the courier's note on the sheet underneath.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            "an old carbon",
            (lambda: [FadeIn(bot_s), FadeIn(top_s)], 0.7),
            "You write",
            (lambda: [FadeIn(top_l)], 0.5),
            "the same stroke",
            (lambda: [Create(pen), Create(pen2)], 1.0),
            "courier's note",
            (lambda: [FadeIn(bot_l)], 0.5),
        ])
        self.steps("One can't exist without the other. And the courier takes only the bottom sheet, the one written for the courier.", [
            "One can't",
            (lambda: [glow(top_s, WHITE, 1.02), glow(bot_s, OB_COL, 1.02)], 0.9),
            "the courier takes",
            (lambda: [VGroup(bot_s, bot_l, pen2).animate.shift(2.6 * RIGHT + 0.6 * DOWN)], 1.0),
        ], after=0.3)
        bracket = DashedVMobject(RoundedRectangle(corner_radius=0.14, width=5.9, height=CH + 0.3, stroke_color=OB_COL, stroke_width=2.5)
                                 .move_to((PAY_C + OUT_C) / 2), num_dashes=60)
        br_l = T("one transaction", 20, OB_COL).move_to([1.2, PAY_C[1], 0])
        self.steps("Map it. The top sheet is the payment row. The bottom sheet is a second row, in a table called outbox, "
                   "written for the readers.", [
            (lambda: [FadeOut(VGroup(top_s, top_l, pen, bot_s, bot_l, pen2)), diagram.animate.set_opacity(1), FadeOut(why), *clear_recs(),
                      *clear_log(), *drop_row("p1")], 0.8),
            "The top sheet",
            (lambda: [glow(payc[0], WHITE, 1.04)], 0.7),
            "The bottom sheet",
            (lambda: [FadeIn(outc, shift=0.1 * LEFT)], 0.7),
        ])
        self.steps("The one stroke is a single database transaction, a group of changes saved all together, or not at all. "
                   "And the courier is Debezium, reading only the outbox.", [
            "The one stroke",
            (lambda: [Create(bracket), FadeIn(br_l)], 0.9),
            "And the courier",
            (lambda: [glow(dz[0], DZ_COL, 1.05)], 0.8),
        ])

        # ---------------- scene 5: watch the log ----------------
        self.steps("Watch the log. BEGIN, transaction 771. Insert the payment row. Insert the outbox row, event e-66 for account acct-17. COMMIT.", [
            (lambda: [FadeOut(br_l)], 0.3),
            "BEGIN",
            (lambda: set_log(0, "BEGIN 771"), 0.4),
            "Insert the payment",
            (lambda: [*set_log(1, "payment pay-3"), *set_row("p1", PAY_C, 0, "pay-3  AUTHORIZED")], 0.5),
            "Insert the outbox",
            (lambda: [*set_log(2, "outbox e-66", OB_COL), *set_row("o1", OUT_C, 0, "e-66  acct-17", OB_COL)], 0.5),
            "COMMIT",
            (lambda: [*set_log(3, "COMMIT 771", GREEN_M)], 0.4),
        ])
        self.steps("Debezium reads the committed transaction and picks up only the outbox insert.", [
            (lambda: [run(log_a, DZ_COL, 0.8)], 0.8),
            "only the outbox",
            (lambda: [glow(self.logc[2][0], OB_COL, 1.08), run(dz_a, OB_COL, 0.5)], 0.7),
            (lambda: set_rec(0, "PaymentAuthorized e-66"), 0.4),
            (lambda: [run(to_led, TP_COL, 0.5)], 0.5),
            (lambda: set_ls("applied e-66", GREEN_M), 0.4),
        ])
        self.stamp("poster")
        self.steps("Now a second payment, pay-4, with its outbox row e-77. The program crashes before commit, "
                   "so the database rolls it back. Does e-77 reach Kafka? Pause and guess.", [
            (lambda: clear_log(), 0.3),
            "Now a second",
            (lambda: [*set_log(0, "BEGIN 772"), *set_log(1, "payment pay-4"), *set_log(2, "outbox e-77", OB_COL),
                      *set_row("p2", PAY_C, 1, "pay-4  AUTHORIZED"), *set_row("o2", OUT_C, 1, "e-77  acct-42", OB_COL)], 0.7),
            "The program crashes",
            (lambda: [*set_log(3, "ROLLBACK 772", RED_M)], 0.4),
            "rolls it back",
            (lambda: [*drop_row("p2"), *drop_row("o2")], 0.5),
            "Pause and guess",
            (lambda: self.cap("does e-77 reach Kafka? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        nothing = T("sees nothing", 20, GREY_B).move_to(DZ_C + [0, -0.62, 0])
        self.steps("No. Its rows were in the log, but the log reader hands out only committed transactions. "
                   "No event without a payment, and no payment without an event.", [
            (lambda: [*self.uncap(), FadeIn(nothing)], 0.5),
            "only committed",
            (lambda: [glow(self.logc[3][0], RED_M, 1.08)], 0.7),
            "No event without",
            (lambda: self.cap("no event without a payment, no payment without an event", GREEN_M, 26), 0.6),
        ], after=0.4)

        # ---------------- scene 6: the name, and the router ----------------
        sub = M("outbox.event.payment", 17, GREY_B).move_to(TP_C + [0, TP_H / 2 - 0.68, 0])
        self.steps("This is called the transactional outbox. Debezium's outbox router turns each outbox row into a Kafka record.", [
            (lambda: [*self.uncap(), FadeOut(nothing), *clear_log(), *self.cap("the transactional outbox", WHITE, 30)], 0.6),
            "outbox router",
            (lambda: [Transform(dz_t, T("Debezium + outbox router", 19).move_to(DZ_C))], 0.6),
        ])
        self.steps("The topic comes from the row's kind, payment. The key is the account, acct-17, so each account's events stay in order. "
                   "And the event's id, e-66, travels along in a header.", [
            "The topic",
            (lambda: [FadeIn(sub)], 0.5),
            "The key is",
            (lambda: set_rec(0, "key acct-17 | id e-66"), 0.5),
            "stay in order",
            (lambda: [Indicate(self.recs[0], color=TP_COL, scale_factor=1.05)], 0.7),
            "travels along",
            (lambda: self.cap("topic from the kind, key from the account, id in a header"), 0.5),
        ])
        self.steps("The program can even delete the outbox row in the same transaction. The router ignores deletes, so the table stays empty.", [
            "delete the outbox",
            (lambda: [*drop_row("o1"), *self.cap("deleted in the same transaction: the outbox stays empty")], 0.6),
        ])

        # ---------------- scene 7: guardrails ----------------
        self.steps("Why not a small program that checks the outbox table every second? It costs a query every second, and it can "
                   "skip a row whose transaction commits late. The log hands out transactions in commit order, so nothing slips past.", [
            (lambda: [*self.cap("a poller? a query every second, and it can skip a late commit")], 0.6),
            "The log hands",
            (lambda: [*self.cap("the log: in commit order, nothing slips past", WHITE), run(log_a, DZ_COL, 0.8)], 0.8),
        ])
        bm = T("saved place: after e-66", 18, GREY_B).move_to(DZ_C + [0, -0.62, 0])
        self.steps("One thing the outbox doesn't fix. Debezium saves its place in the log only about once a minute. "
                   "Say e-88 reaches Kafka, and Debezium dies before the next save.", [
            (lambda: [*self.uncap(), FadeIn(bm)], 0.5),
            "Say e-88",
            (lambda: [*set_log(2, "outbox e-88", OB_COL), run(log_a, DZ_COL, 0.6)], 0.7),
            (lambda: [run(dz_a, OB_COL, 0.4)], 0.4),
            (lambda: set_rec(1, "key acct-17 | id e-88"), 0.4),
            (lambda: [run(to_led, TP_COL, 0.5)], 0.5),
            (lambda: set_ls("applied e-66, e-88", GREEN_M), 0.4),
            "Debezium dies",
            (lambda: [dz[0].animate.set_stroke(RED_M), *self.cap("dies before saving its place", RED_M)], 0.5),
        ])
        self.steps("After a restart, it reads from the old place and sends e-88 again, with the same id.", [
            (lambda: [dz[0].animate.set_stroke(DZ_COL)], 0.4),
            "reads from the old",
            (lambda: [glow(bm, YELLOW_M, 1.05), run(log_a, DZ_COL, 0.6)], 0.7),
            "sends e-88 again",
            (lambda: [run(dz_a, OB_COL, 0.4)], 0.4),
            (lambda: set_rec(2, "key acct-17 | id e-88", RED_M), 0.4),
        ])
        self.steps("So the ledger keeps the ids it has applied, and drops repeats. Delivery is at least once, never exactly once for free.", [
            "keeps the ids",
            (lambda: [run(to_led, RED_M, 0.5)], 0.5),
            (lambda: set_ls("e-88 again: dropped", YELLOW_M), 0.5),
            "Delivery is",
            (lambda: self.cap("at least once: readers drop repeats by id", WHITE), 0.5),
        ])

        # ---------------- scene 8: the code, the moral, a check ----------------
        diag2 = VGroup(prog, prog_t, dbb, db_t, payc, outc, led, led_t, tp, tp_t, sub, dz, dz_t, bm, save_a, to_led, log_l, log_a, dz_a,
                       *[v for v in self.rows.values()], *[c for c in self.logc if c is not None], *[r for r in self.recs if r is not None], self.ls)
        jp, kp = code_panel("Java", JAVA, -3.45), code_panel("Kotlin", KOTLIN, 3.45)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, it's one transaction with two inserts, and one commit.", [
            (lambda: [*self.uncap(), diag2.animate.set_opacity(0.06)], 0.5),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.6),
            "two inserts",
            (lambda: [*hl((1,), WHITE), *hl((2, 3), OB_COL)], 1.0),
            "one commit",
            (lambda: hl((4,), GREEN_M), 0.9),
        ], after=1.0)
        self.steps("Publish what you meant, not what your table looks like, and write it in the same transaction.", [
            (lambda: [FadeOut(jp), FadeOut(kp), diag2.animate.set_opacity(1)], 0.7),
            (lambda: self.cap("publish what you meant; write it in the same transaction", YELLOW_M, 28), 0.6),
        ], after=0.5)
        crash2 = VGroup(tick(False, 0.18), T("crash", 22, RED_M)).arrange(RIGHT, buff=0.12).move_to(P_C + [P_W / 2 + 0.9, 0, 0])
        self.steps("One quick check. A payment and its outbox row commit, and the program crashes a moment later. "
                   "Does the ledger hear about it? Pause and think.", [
            (lambda: [*self.uncap(), *clear_log(), *clear_recs(), *set_ls("waiting to hear"), FadeOut(bm)], 0.5),
            "commit",
            (lambda: [*set_log(0, "BEGIN 773"), *set_log(1, "payment pay-5"), *set_log(2, "outbox e-99", OB_COL), *set_log(3, "COMMIT 773", GREEN_M)], 0.6),
            "the program crashes",
            (lambda: [FadeIn(crash2, scale=0.6), prog[0].animate.set_stroke(RED_M)], 0.5),
            "Pause and think",
            (lambda: self.cap("does the ledger hear about it? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. The commit is in the log, and Debezium reads it, whether the program is alive or not.", [
            (lambda: [*self.uncap(), run(log_a, DZ_COL, 0.7)], 0.7),
            (lambda: [run(dz_a, OB_COL, 0.4)], 0.4),
            (lambda: set_rec(0, "key acct-17 | id e-99"), 0.4),
            (lambda: [run(to_led, TP_COL, 0.5)], 0.5),
            (lambda: set_ls("applied e-99", GREEN_M), 0.4),
            "whether the program",
            (lambda: self.cap("publish what you meant; write it in the same transaction", YELLOW_M, 28), 0.6),
        ], after=0.3)
        self.play(Create(tick(True, 0.2).move_to(LD_C + [LD_W / 2 + 0.4, 0, 0])), run_time=0.6)
        self.wait(2.0)
