from sfz import *

SAY.insert(0, (r"\bpay-(\d+)\b", r"pay \1"))
SAY.insert(0, (r"\be-(\d+)\b", r"E \1"))
SAY.insert(0, (r"\bCOMMIT\b", "commit"))
SAY.insert(0, (r"\bPaymentAuthorized\b", "payment authorized"))

SVC = np.array([-4.0, 3.15, 0])
PGC, PGW, PGH = np.array([-4.0, 0.05, 0]), 5.2, 3.5
PAY_C, OUT_C, CARD_W, CARD_H = np.array([-5.3, 0.62, 0]), np.array([-2.75, 0.62, 0]), 2.3, 1.2
WX0, WW, WG, WAL_Y = -6.4, 0.92, 0.06, -1.0
DBZ = np.array([0.65, -1.0, 0])
TX0, TW, TOP_Y = 1.75, 1.2, 2.2
LED = np.array([4.15, 0.45, 0])
ST_X, ST_Y = 3.6, [-2.25, -2.8]


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


def card(c, title):
    r = RoundedRectangle(corner_radius=0.1, width=CARD_W, height=CARD_H, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
    r.move_to(c)
    return VGroup(r, left_at(T(title, 19, GREY_B), c[0] - CARD_W / 2 + 0.18, c[1] + CARD_H / 2 - 0.22))


def body(c, lines):
    """Rows inside a table card: [(text, colour), ...]."""
    g = VGroup()
    for i, (s, col) in enumerate(lines):
        g.add(left_at(M(s, 16, col), c[0] - CARD_W / 2 + 0.2, c[1] + 0.1 - 0.32 * i))
    return g


def wal(i, s, color=GREY_B):
    x = WX0 + i * (WW + WG) + WW / 2
    r = RoundedRectangle(corner_radius=0.06, width=WW, height=0.5, stroke_color=color, stroke_width=2.2)
    r.set_fill(fillc(color), 1).move_to([x, WAL_Y, 0])
    return VGroup(r, M(s, 15, WHITE).move_to(r))


def tcell(i, ev, color=GOLD_M):
    x = TX0 + i * TW + TW / 2
    r = Rectangle(width=TW, height=0.78, stroke_color=color, stroke_width=2.2).set_fill(fillc(color), 1).move_to([x, TOP_Y, 0])
    return VGroup(r, M(ev, 16, WHITE).move_to([x, TOP_Y + 0.15, 0]), M("acct-17", 13, GREY_B).move_to([x, TOP_Y - 0.17, 0]))


def tslot(i):
    x = TX0 + i * TW + TW / 2
    return Rectangle(width=TW, height=0.78, stroke_color=GREY_D, stroke_width=1.5).move_to([x, TOP_Y, 0])


def status(s, k, color=GREY_B, size=20):
    return T(s, size, color).move_to([ST_X, ST_Y[k], 0])


def dot(a, b, color=GOLD_M, rt=0.6):
    return travel(Line(a, b), color, rt)


class CdcOutbox(Base):
    """stream-02, section 3: pay-31 written then sent loses its event on a crash; sent first, a rollback leaves an event
    for nothing. With an outbox, pay-31 and e-66 commit in one transaction; Debezium reads the WAL through a slot and
    publishes e-66 keyed by acct-17. e-67 and e-68 overlap and reach Kafka in commit order (68, then 67). A transaction
    that never commits (e-69) is never decoded, so no event goes out."""

    def construct(self):
        self.title_card("The transactional outbox", "an event for every payment, and none for a rollback")

        svc = mbox("payment service", WHITE, w=2.7, h=0.6, size=19).move_to(SVC)
        pg = RoundedRectangle(corner_radius=0.16, width=PGW, height=PGH, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLACK, 1)
        pg.move_to(PGC)
        pgt = left_at(T("PostgreSQL", 21, BLUE_M), PGC[0] - PGW / 2 + 0.25, PGC[1] + PGH / 2 - 0.3)
        pay = card(PAY_C, "payment")
        tlab = T("Kafka topic: outbox.event.payment", 18, GREY_B).move_to([TX0 + 2 * TW, TOP_Y + 0.65, 0])
        slots = VGroup(*[tslot(i) for i in range(4)])
        led = mbox("ledger consumer", WHITE, w=2.7, h=0.6, size=19).move_to(LED)
        tl = Arrow([LED[0], TOP_Y - 0.43, 0], [LED[0], LED[1] + 0.34, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.2)
        self.steps("The payment service authorizes payment pay-31, and the ledger must hear about it through Kafka. "
                   "The row and the event must both happen, or neither.", [
            (lambda: [FadeIn(svc), FadeIn(pg), FadeIn(pgt), FadeIn(pay)], 0.9),
            "through Kafka",
            (lambda: [FadeIn(tlab), FadeIn(slots), FadeIn(led), GrowArrow(tl)], 0.9),
            "both happen",
            (lambda: [glow(pay[0], GREY_A, 1.04), glow(led[0], GREY_A, 1.04)], 0.8),
        ])

        down = (SVC + 0.32 * DOWN, PAY_C + np.array([0, CARD_H / 2 + 0.05, 0]))
        send = DashedLine(SVC + np.array([1.38, 0, 0]), [TX0 - 0.08, TOP_Y + 0.1, 0], dash_length=0.1, stroke_width=2.5, color=GREY_B)
        crash = tick(False, 0.22).next_to(svc, LEFT, buff=0.2)
        p31 = body(PAY_C, [("pay-31  ok", GREEN_M)])
        lost = status("payment committed, event lost", 0, RED_M)
        self.steps("Write the row, then send the event, and a crash in between loses the event. "
                   "The ledger never hears about a real payment.", [
            (lambda: [dot(*down, WHITE)], 0.6),
            (lambda: [FadeIn(p31)], 0.4),
            "then send",
            (lambda: [Create(send)], 0.6),
            "and a crash",
            (lambda: [Create(crash), svc[0].animate.set_stroke(RED_M), send.animate.set_color(RED_M)], 0.6),
            "The ledger never",
            (lambda: [FadeIn(lost, shift=0.1 * UP)], 0.6),
        ])

        ghost = tcell(0, "pay-31", RED_M)
        ghost[2].become(M("?", 13, RED_M).move_to(ghost[2]))
        rb = body(PAY_C, [("pay-31", RED_M), ("rolled back", RED_M)])
        none = status("an event for a payment that never existed", 0, RED_M)
        self.steps("Send first instead, and a rollback leaves the ledger holding an event for a payment that never existed.", [
            (lambda: [FadeOut(crash), FadeOut(p31), FadeOut(lost), svc[0].animate.set_stroke(WHITE), send.animate.set_color(GREY_B)], 0.6),
            (lambda: [dot(send.get_start(), send.get_end(), WHITE, 0.7)], 0.7),
            (lambda: [FadeIn(ghost), dot(tl.get_start(), tl.get_end(), WHITE, 0.5)], 0.6),
            "and a rollback",
            (lambda: [dot(*down, WHITE)], 0.5),
            (lambda: [FadeIn(rb)], 0.5),
            "holding an event",
            (lambda: [FadeIn(none, shift=0.1 * UP), glow(ghost[0], RED_M, 1.06)], 0.8),
        ])

        out = card(OUT_C, "outbox")
        txb = DashedVMobject(RoundedRectangle(corner_radius=0.14, width=5.0, height=CARD_H + 0.2), num_dashes=70).set_stroke(GOLD_M, 2)
        txb.move_to((PAY_C + OUT_C) / 2)
        txl = T("one transaction", 17, GOLD_M).move_to([(PAY_C[0] + OUT_C[0]) / 2, PAY_C[1] - CARD_H / 2 - 0.36, 0])
        b1 = body(PAY_C, [("pay-31", GOLD_M)])
        b2 = body(OUT_C, [("e-66 acct-17", GOLD_M)])
        self.steps("The outbox fixes both. In one local transaction, the service inserts the payment row "
                   "and an event row into an outbox table. Both commit, or neither does.", [
            (lambda: [FadeOut(ghost), FadeOut(rb), FadeOut(none), FadeOut(send)], 0.6),
            "In one local",
            (lambda: [FadeIn(out), Create(txb), FadeIn(txl)], 0.8),
            "the service inserts",
            (lambda: [dot(*down, GOLD_M)], 0.5),
            (lambda: [FadeIn(b1)], 0.4),
            "and an event row",
            (lambda: [FadeIn(b2)], 0.5),
            "Both commit",
            (lambda: [b1.animate.set_color(GREEN_M), b2.animate.set_color(GREEN_M), txb.animate.set_stroke(GREEN_M),
                      txl.animate.set_color(GREEN_M)], 0.7),
        ])

        wl = left_at(T("write-ahead log", 18, GREY_B), WX0, WAL_Y + 0.5)
        w = [wal(0, "pay-31"), wal(1, "e-66", GOLD_M), wal(2, "commit", GREEN_M)]
        self.steps("PostgreSQL writes both inserts, then the commit, to its write-ahead log.", [
            (lambda: [FadeIn(wl), FadeOut(txb), FadeOut(txl)], 0.5),
            "both inserts",
            (lambda: [FadeIn(w[0], shift=0.1 * RIGHT)], 0.4),
            (lambda: [FadeIn(w[1], shift=0.1 * RIGHT)], 0.4),
            "then the commit",
            (lambda: [FadeIn(w[2], shift=0.1 * RIGHT)], 0.5),
        ])

        dbz = mbox("Debezium", TEAL_M, w=1.9, h=0.62, size=20).move_to(DBZ)
        dsub = T("outbox table only", 16, TEAL_M).move_to(DBZ + 0.55 * DOWN)
        wa = Arrow([PGC[0] + PGW / 2 - 0.02, WAL_Y, 0], [DBZ[0] - 0.97, WAL_Y, 0], buff=0, stroke_width=3, color=TEAL_M,
                   max_tip_length_to_length_ratio=0.2)
        sl = T("slot", 17, TEAL_M).next_to(wa, UP, buff=0.1)
        self.steps("Debezium reads that log through a replication slot, a bookmark PostgreSQL keeps for it. "
                   "It's handed each transaction only after the commit.", [
            (lambda: [FadeIn(dbz), FadeIn(dsub)], 0.6),
            "through a replication slot",
            (lambda: [GrowArrow(wa), FadeIn(sl)], 0.6),
            "only after the commit",
            (lambda: [glow(w[2][0], GREEN_M, 1.1)], 0.6),
            (lambda: [dot(w[0].get_left(), wa.get_end(), GOLD_M, 0.9)], 0.9),
        ])

        da = Arrow(DBZ + np.array([0.55, 0.33, 0]), [TX0 + TW / 2, TOP_Y - 0.43, 0], buff=0, stroke_width=3, color=TEAL_M,
                   max_tip_length_to_length_ratio=0.12)
        c66 = tcell(0, "e-66")
        app = T("applied: e-66", 17, GREEN_M).move_to(LED + 0.55 * DOWN)
        self.steps("It skips the payment row, turns the outbox row into a Kafka record keyed by account 17, "
                   "and the ledger reads PaymentAuthorized.", [
            (lambda: [GrowArrow(da)], 0.5),
            "turns the outbox row",
            (lambda: [dot(da.get_start(), da.get_end(), GOLD_M, 0.7)], 0.7),
            (lambda: [FadeIn(c66)], 0.4),
            "keyed by",
            (lambda: [glow(c66[0], GOLD_M, 1.06)], 0.6),
            "and the ledger",
            (lambda: [dot(tl.get_start(), tl.get_end(), GOLD_M, 0.5), FadeIn(app)], 0.7),
        ])

        w2 = [wal(0, "e-67", PURPLE_M), wal(1, "e-68", TEAL_M), wal(2, "commit", TEAL_M), wal(3, "commit", PURPLE_M)]
        b3 = body(OUT_C, [("e-67", PURPLE_M), ("e-68", TEAL_M)])
        self.steps("Now two payments overlap. The first takes event e-67, but the second, with e-68, commits first.", [
            (lambda: [FadeOut(VGroup(*w)), FadeOut(b1), FadeOut(b2)], 0.5),
            "The first takes",
            (lambda: [FadeIn(w2[0], shift=0.1 * RIGHT), FadeIn(b3[0])], 0.5),
            "but the second",
            (lambda: [FadeIn(w2[1], shift=0.1 * RIGHT), FadeIn(b3[1])], 0.5),
            "commits first",
            (lambda: [FadeIn(w2[2], shift=0.1 * RIGHT)], 0.4),
            (lambda: [FadeIn(w2[3], shift=0.1 * RIGHT)], 0.4),
        ])

        c68, c67 = tcell(1, "e-68", TEAL_M), tcell(2, "e-67", PURPLE_M)
        order = status("commit order: e-68, then e-67", 0, GREEN_M)
        poll = status("a poller paging by id: reads 68, skips 67", 1, RED_M)
        self.steps("The log hands out whole transactions in commit order, so Kafka gets e-68, then e-67, and neither is lost. "
                   "A poller paging through the table by id could read 68 and move past 67 for good.", [
            (lambda: [glow(w2[2][0], TEAL_M, 1.1)], 0.5),
            "so Kafka gets",
            (lambda: [dot(wa.get_start(), wa.get_end(), TEAL_M, 0.5)], 0.5),
            (lambda: [dot(da.get_start(), da.get_end(), TEAL_M, 0.5)], 0.5),
            (lambda: [FadeIn(c68)], 0.3),
            "then e-67",
            (lambda: [dot(wa.get_start(), wa.get_end(), PURPLE_M, 0.5)], 0.5),
            (lambda: [dot(da.get_start(), da.get_end(), PURPLE_M, 0.5)], 0.5),
            (lambda: [FadeIn(c67), FadeIn(order, shift=0.1 * UP), Transform(app, T("applied: e-66, e-68, e-67", 17, GREEN_M).move_to(app))], 0.6),
            "A poller",
            (lambda: [FadeIn(poll, shift=0.1 * UP)], 0.6),
        ])

        w3 = [wal(0, "pay-34", RED_M), wal(1, "e-69", RED_M)]
        b4 = body(PAY_C, [("pay-34", RED_M)])
        b5 = body(OUT_C, [("e-69", RED_M)])
        crash2 = tick(False, 0.22).next_to(svc, LEFT, buff=0.2)
        nx = WX0 + 2 * (WW + WG) + WW / 2
        nocm = VGroup(DashedVMobject(Rectangle(width=WW, height=0.5), num_dashes=24).set_stroke(GREY_C, 2).move_to([nx, WAL_Y, 0]),
                      T("no commit", 12, GREY_B).move_to([nx, WAL_Y, 0]))
        self.steps("Last, a payment whose transaction never commits: the service crashes before COMMIT. "
                   "Its inserts are in the log, with no commit after them.", [
            (lambda: [FadeOut(VGroup(*w2)), FadeOut(b3), FadeOut(order), FadeOut(poll)], 0.5),
            (lambda: [dot(*down, RED_M)], 0.5),
            (lambda: [FadeIn(b4), FadeIn(b5), FadeIn(w3[0], shift=0.1 * RIGHT), FadeIn(w3[1], shift=0.1 * RIGHT)], 0.6),
            "the service crashes",
            (lambda: [Create(crash2), svc[0].animate.set_stroke(RED_M)], 0.6),
            "with no commit",
            (lambda: [FadeIn(nocm)], 0.5),
            (lambda: [glow(w3[1][0], RED_M, 1.1)], 0.6),
        ])

        rbk = status("rolled back: no event", 0, GREEN_M)
        self.steps("Decoding emits only committed transactions, so Debezium never sees these rows. "
                   "No event goes out for a payment that didn't happen.", [
            (lambda: [w3[0].animate.set_opacity(0.3), w3[1].animate.set_opacity(0.3), b4.animate.set_opacity(0.3),
                      b5.animate.set_opacity(0.3)], 0.8),
            "so Debezium never",
            (lambda: [glow(dbz[0], TEAL_M, 1.06)], 0.7),
            "No event goes out",
            (lambda: [FadeIn(rbk, shift=0.1 * UP), glow(slots[3], GREEN_M, 1.0)], 0.8),
        ])

        self.steps("Put the event in the same transaction as the change, and let the log publish it. "
                   "Every committed payment gets its event, in commit order, and a rollback gets none.", [
            (lambda: [FadeOut(crash2), svc[0].animate.set_stroke(WHITE), glow(out[0], GOLD_M, 1.05), glow(pay[0], GOLD_M, 1.05)], 0.9),
            "and let the log",
            (lambda: [glow(wa, TEAL_M, 1.0), glow(dbz[0], TEAL_M, 1.06)], 0.8),
            "Every committed",
            (lambda: [*[glow(c[0], GREEN_M, 1.06) for c in (c66, c68, c67)]], 0.9),
        ])
        self.wait(0.6)
