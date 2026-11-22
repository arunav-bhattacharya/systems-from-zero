from sfz import *

SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\breq-7f3a\b", "rek seven F three A"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BX = [-5.4, -2.7, 0.0, 2.7, 5.4]
BY, BW, BH = 0.95, 2.05, 0.9
GY, GW, GH = -0.3, 2.45, 0.76                 # the guards, under the hops
GX = [(BX[0] + BX[1]) / 2, (BX[1] + BX[2]) / 2, (BX[2] + BX[3]) / 2, BX[4] - 0.1]
ROW_Y = [1.82, 2.48, 3.14]
TAB_X, TAB_Y = -4.6, [-1.12, -1.52, -1.92, -2.32, -2.72]
CAP_Y, BAR_Y = -3.2, -2.86
NAMES = [("phone", ""), ("API server", "the bank's program"), ("broker", "the Kafka log"), ("consumer", "reads the log"),
         ("ledger", "PostgreSQL")]
GUARDS = [("TCP", "numbers the bytes"), ("idempotent producer", "same number: dropped"),
          ("exactly-once mode", "offsets + Kafka writes"), ("one transaction", "all or nothing")]


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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


def glow(m, color=YELLOW_M, s=1.05):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def pulse(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.1)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def node(i, color=WHITE):
    name, sub = NAMES[i]
    r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([BX[i], BY, 0])
    g = VGroup(r, T(name, 24).move_to([BX[i], BY + (0.13 if sub else 0), 0]))
    if sub:
        g.add(T(sub, 16, GREY_B).move_to([BX[i], BY - 0.22, 0]))
    return g


def hop(i):
    return Arrow([BX[i] + BW / 2 + 0.04, BY, 0], [BX[i + 1] - BW / 2 - 0.04, BY, 0], buff=0, stroke_width=3, color=GREY_B,
                 max_tip_length_to_length_ratio=0.3)


def guard(k, color=GREY_B, name=None, sub=None):
    n, s = GUARDS[k]
    n, s = name or n, sub or s
    r = RoundedRectangle(corner_radius=0.1, width=GW, height=GH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.1), 1)
    r.move_to([GX[k], GY, 0])
    return VGroup(r, fit(T(n, 18, color if color is not GREY_B else WHITE), GW - 0.2).move_to([GX[k], GY + 0.14, 0]),
                  fit(T(s, 14, GREY_B), GW - 0.2).move_to([GX[k], GY - 0.17, 0]))


def lrow(k, color=WHITE):
    c = chip("row: -45.00", color, 18, mono=True)
    return c.move_to([BX[4], ROW_Y[k], 0])


def spark(x, y=BY):
    return Star(n=6, outer_radius=0.17, inner_radius=0.08, color=RED_M, fill_opacity=1, stroke_width=0).move_to([x, y + 0.42, 0])


class EndToEnd(Base):
    """derive-03, section 2. A transfer's path: phone, API server, broker, consumer, ledger, with one guard per hop (TCP,
    the idempotent producer, Kafka's exactly-once mode, a transaction). A repeated packet and a lost broker ack are
    caught; the phone's retry after a lost answer and a consumer crash before its offset pass every guard. The lab:
    103, 78, 47 duplicate rows, then 0 with one request id (req-7f3a) checked at the ledger. A posted present as the
    analogy, the guardrail, the moral and a check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        line = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(line), run_time=0.25)
        self.play(Uncreate(line), run_time=secs, rate_func=linear)

    def tok(self, i, color=GOLD_M, rt=0.45):
        """A request token running along hop i."""
        a, b = self.hops[i].get_start(), self.hops[i].get_end()
        d = Dot(radius=0.09, color=color).move_to(a)
        return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.08))

    def path(self, frm=0, to=4, color=GOLD_M):
        return [(lambda i=i: [self.tok(i, color)], 0.5) for i in range(frm, to)]

    def add_row(self, color=WHITE):
        r = lrow(len(self.rows), color)
        self.rows.append(r)
        return [FadeIn(r, shift=0.15 * DOWN)]

    def set_guard(self, k, color, **kw):
        new = guard(k, color, **kw)
        old, self.gd[k] = self.gd[k], new
        return [swap(old, new)]

    def construct(self):
        self.capm = None
        self.rows = []
        self.title_card("Four careful guards, and the money moved twice", "every layer's exactly-once stops at its own edge")

        nodes = [node(i) for i in range(5)]
        self.hops = [hop(i) for i in range(4)]
        self.gd = [None] * 4

        # ---------------- scene 1: one tap, 90.00 ----------------
        tunnel = Rectangle(width=0.6, height=1.5, stroke_width=0).set_fill(GREY_D, 0.45).move_to([GX[0], BY, 0])
        tun_l = T("tunnel", 18, GREY_B).move_to([GX[0], BY + 0.98, 0])
        qm = T("?", 64, YELLOW_M).move_to([0, -1.6, 0])
        self.steps("You're on a train, sending 45.00 to a friend from your banking app. You tap send, and the train enters a tunnel.", [
            "sending 45.00",
            (lambda: [FadeIn(nodes[0], shift=0.1 * RIGHT), FadeIn(nodes[4], shift=0.1 * LEFT)], 0.7),
            "You tap send",
            (lambda: [self.tok_free(0)], 0.6),
            "enters a tunnel",
            (lambda: [FadeIn(tunnel), FadeIn(tun_l)], 0.6),
        ])
        self.steps("Ten seconds later, the app sends the request again. Out of the tunnel, your balance is 90.00 lower.", [
            "sends the request again",
            (lambda: [self.tok_free(0)], 0.6),
            "Out of the tunnel",
            (lambda: [*self.add_row(RED_M)], 0.4),
            (lambda: [*self.add_row(RED_M), *self.cap("-90.00 for one tap", RED_M)], 0.5),
        ])
        self.steps("And here's the odd part. Every layer on the way promises to handle each thing exactly once. "
                   "So how did one tap move the money twice? Hold that question.", [
            "Every layer",
            (lambda: self.cap("every layer on the way: \"exactly once\"", WHITE), 0.5),
            "So how did",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the path ----------------
        self.steps("Here's the path. The phone sends the request over TCP, the rules that carry bytes between two machines, "
                   "to the API server, the bank's program that takes requests from apps.", [
            (lambda: [FadeOut(qm), *self.uncap(), FadeOut(VGroup(*self.rows)), FadeOut(tunnel), FadeOut(tun_l)], 0.5),
            "over TCP",
            (lambda: [GrowArrow(self.hops[0])], 0.5),
            "to the API server",
            (lambda: [FadeIn(nodes[1], shift=0.1 * DOWN)], 0.6),
        ])
        self.rows = []
        self.steps("The server writes a record to Kafka, a log that the next program reads. The program that keeps that log is called the broker.", [
            "writes a record",
            (lambda: [GrowArrow(self.hops[1]), FadeIn(nodes[2], shift=0.1 * DOWN)], 0.7),
            "called the broker",
            (lambda: [glow(nodes[2][0], BLUE_M)], 0.7),
        ])
        self.steps("Then a consumer reads the record, and adds a row to the ledger, the bank's list of every movement of money, "
                   "kept in PostgreSQL, a database.", [
            "Then a consumer",
            (lambda: [GrowArrow(self.hops[2]), FadeIn(nodes[3], shift=0.1 * DOWN)], 0.7),
            "adds a row",
            (lambda: [GrowArrow(self.hops[3])], 0.5),
            *self.path(0, 4),
            (lambda: self.add_row(), 0.4),
        ])

        # ---------------- scene 3: a posted present ----------------
        self.steps("Picture posting a present to a friend. Every depot on the way scans each parcel, so nothing goes through twice.", [
            (lambda: self.cap("posting a present: every depot scans each parcel", WHITE), 0.5),
            "Every depot",
            (lambda: [LaggedStart(*[glow(nodes[i][0], GREY_B) for i in (1, 2, 3)], lag_ratio=0.3)], 1.0),
        ])
        self.steps("A week passes, no word, so you post a second one, the same present. Every depot scans it happily. New parcel, new label.", [
            "you post a second",
            (lambda: self.cap("no word for a week: post the same present again", WHITE), 0.5),
            "Every depot scans",
            (lambda: [LaggedStart(*[glow(nodes[i][0], GREEN_M) for i in (1, 2, 3)], lag_ratio=0.3)], 1.0),
            "New parcel",
            (lambda: self.cap("new parcel, new label: nothing to drop", WHITE), 0.5),
        ])
        self.steps("Only you and your friend know they're the same gift.", [
            (lambda: [glow(nodes[0][0], GOLD_M), glow(nodes[4][0], GOLD_M)], 0.9),
        ])
        self.steps("Map it. You're the phone. The parcel is the request. The depots are the layers, and each scan is a guard. "
                   "Keep the second parcel in mind.", [
            "You're the phone",
            (lambda: [*self.cap("you = the phone", WHITE), glow(nodes[0][0], GOLD_M)], 0.6),
            "The parcel is",
            (lambda: [*self.cap("the parcel = the request", WHITE), self.tok(0)], 0.6),
            "The depots",
            (lambda: [*self.cap("depots = the layers;  each scan = a guard", WHITE),
                      LaggedStart(*[FadeIn(self._g(k)) for k in range(4)], lag_ratio=0.25)], 1.1),
        ])

        # ---------------- scene 4: each guard, and its edge ----------------
        s1 = spark(GX[0])
        self.steps("Now the faults, one per hop, and the guard that lives there. One: a packet is sent again although the first copy arrived.", [
            (lambda: self.cap("fault 1: a packet sent again, though the first copy arrived", RED_M), 0.5),
            "One: a packet",
            (lambda: [FadeIn(s1, scale=0.5), self.tok(0), self.tok(0)], 0.6),
        ])
        self.steps("TCP numbers every byte on a connection and drops bytes it has already delivered. That one is caught.", [
            "drops bytes",
            (lambda: self.set_guard(0, GREEN_M), 0.5),
            "That one",
            (lambda: [FadeOut(s1), glow(self.gd[0][0], GREEN_M)], 0.6),
        ])
        s2 = spark(GX[1])
        self.steps("Two: the broker adds the record, but its \"got it\" is lost, so the server sends it again, with the same sequence number.", [
            (lambda: self.cap("fault 2: the broker's \"got it\" is lost; the server resends", RED_M), 0.5),
            "but its",
            (lambda: [FadeIn(s2, scale=0.5)], 0.4),
            "sends it again",
            (lambda: [self.tok(1)], 0.5),
        ])
        self.steps("The idempotent producer lets the broker spot the repeat and add nothing. That one is caught too. Idempotent means safe to repeat.", [
            "spot the repeat",
            (lambda: self.set_guard(1, GREEN_M), 0.5),
            "That one",
            (lambda: [FadeOut(s2), glow(self.gd[1][0], GREEN_M)], 0.6),
            "Idempotent means",
            (lambda: self.cap("idempotent: safe to repeat", GREEN_M), 0.5),
        ])
        tunnel2 = tunnel.copy()
        self.steps("Now the train. The server saved the transfer, 80 milliseconds after the tap, and the answer died in the tunnel.", [
            (lambda: [*self.cap("fault 3: the answer is lost", RED_M), FadeIn(tunnel2)], 0.5),
            "The server saved",
            (lambda: [glow(self.rows[0][0], WHITE)], 0.6),
            "the answer died",
            (lambda: [self.back_tok()], 0.8),
        ])
        self.steps("Ten seconds later, the phone sends again. Which guard catches this one? Pause and guess.", [
            "the phone sends",
            (lambda: [glow(nodes[0][0], GOLD_M)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("None of them. The retry comes on a new connection, and TCP's numbers start fresh.", [
            (lambda: self.uncap(), 0.3),
            "The retry comes",
            (lambda: [self.tok(0)], 0.5),
            "TCP's numbers",
            (lambda: [*self.set_guard(0, RED_M, sub="new connection, new numbers")], 0.6),
        ])
        self.steps("The server sends a new record, which gets a new sequence number. Every guard sees a new, perfectly good transfer. "
                   "Second row. 90.00 gone.", [
            "The server sends",
            (lambda: [self.tok(1)], 0.5),
            "a new sequence",
            (lambda: self.set_guard(1, RED_M, sub="new request, new number"), 0.6),
            "Every guard",
            (lambda: [self.tok(2), self.tok_ledger()], 0.6),
            "Second row",
            (lambda: [*self.add_row(RED_M)], 0.5),
            "90.00 gone",
            (lambda: self.cap("-90.00", RED_M), 0.4),
        ])
        crash = tick(False, 0.16).move_to([BX[3], BY + BH / 2 + 0.3, 0])
        self.steps("One more. The consumer writes the row, then dies before it saves how far it has read, its offset. "
                   "On restart, it gets the record again.", [
            (lambda: [*self.cap("fault 4: the consumer dies after the insert, before its offset", RED_M), FadeOut(tunnel2)], 0.5),
            "then dies",
            (lambda: [Create(crash)], 0.5),
            "its offset",
            (lambda: self.cap("offset: how far it has read", WHITE), 0.5),
            "it gets the record",
            (lambda: [FadeOut(crash), self.tok(2)], 0.6),
        ])
        self.steps("Kafka's exactly-once mode saves offsets and Kafka writes together, but the ledger lives in PostgreSQL, outside it.", [
            "saves offsets",
            (lambda: [glow(self.gd[2][0], GREY_B)], 0.7),
            "but the ledger",
            (lambda: [*self.set_guard(2, RED_M, sub="the ledger is outside it"), self.tok_ledger()], 0.7),
            (lambda: self.add_row(RED_M), 0.5),
        ])
        self.steps("And the database runs each insert as a fine new transaction.", [
            "runs each insert",
            (lambda: self.set_guard(3, RED_M, sub="each insert: a fine new one"), 0.6),
        ])
        self.steps("So each guard is right, but only inside its own layer. Each one's exactly-once stops at its own edge.", [
            "only inside",
            (lambda: [LaggedStart(*[glow(self.gd[k][0], YELLOW_M) for k in range(4)], lag_ratio=0.2)], 1.0),
            "Each one's",
            (lambda: self.cap("each layer's exactly-once stops at its own edge", YELLOW_M, 28), 0.6),
        ], after=0.5)

        # ---------------- scene 5: the lab's count ----------------
        head = left_at(T("the lab: 1,000 transfers, the same faults", 20, GREY_B), TAB_X, TAB_Y[0])
        lines = [("no guards", "103 extra rows, 53,025.23 moved", RED_M), ("+ TCP", "78", RED_M),
                 ("+ idempotent producer", "47", RED_M), ("+ request id at the ledger", "0", GREEN_M)]
        tab = []
        for k, (a, b, c) in enumerate(lines):
            la = left_at(T(a, 20, WHITE), TAB_X, TAB_Y[k + 1])
            lb = left_at(T(b, 20, c), TAB_X + 3.6, TAB_Y[k + 1])
            tab.append(VGroup(la, lb))
        self.steps("The lab measures it. 1,000 transfers, the same faults, each guard switched on in turn.", [
            (lambda: [*self.uncap(), FadeIn(head)], 0.5),
        ])
        self.steps("With none, the ledger gets 103 extra rows, and 53,025.23 moves that nobody asked to move.", [
            "With none",
            (lambda: [FadeIn(tab[0], shift=0.1 * UP)], 0.6),
        ])
        self.steps("TCP's guard brings it to 78. The idempotent producer, to 47.", [
            (lambda: [FadeIn(tab[1], shift=0.1 * UP), glow(self.gd[0][0], GREEN_M)], 0.6),
            "The idempotent",
            (lambda: [FadeIn(tab[2], shift=0.1 * UP), glow(self.gd[1][0], GREEN_M)], 0.6),
        ])
        ring = SurroundingRectangle(tab[2][1], color=RED_M, buff=0.08, stroke_width=2.5)
        self.steps("Four careful guards, and every one of them would pass an audit.", [
            (lambda: [Create(ring)], 0.6),
        ])
        self.steps("The 47 left are lost answers and consumer crashes. They happen above every layer: "
                   "one in the phone's retry, one in the gap between two systems.", [
            "The 47",
            (lambda: [pulse(tab[2][1], RED_M)], 0.6),
            "one in the phone's",
            (lambda: [glow(nodes[0][0], GOLD_M)], 0.6),
            "one in the gap",
            (lambda: [glow(nodes[3][0], GOLD_M), glow(nodes[4][0], GOLD_M)], 0.7),
        ])

        # ---------------- scene 6: one id, from the tap ----------------
        idc = chip("req-7f3a", GOLD_M, 18, mono=True).move_to([BX[0], BY + 0.85, 0])
        self.steps("Back to the present. You write a reference number on it, and your friend keeps a list. "
                   "Here, only the phone knows that two requests are one transfer.", [
            (lambda: [FadeOut(ring), *self.cap("write a reference number on it; your friend keeps a list", GOLD_M)], 0.5),
            "only the phone",
            (lambda: [glow(nodes[0][0], GOLD_M)], 0.7),
        ])
        self.steps("So it makes an id when you tap, req-7f3a, and sends the same id on every attempt.", [
            "it makes an id",
            (lambda: [FadeIn(idc, shift=0.1 * DOWN)], 0.6),
            "the same id",
            (lambda: [pulse(idc[1], GOLD_M)], 0.6),
        ])
        self.steps("It rides in a header on the request, then a header on the Kafka record, all the way to the ledger.", [
            (lambda: self.cap("a header on the request, then on the Kafka record, then a column in the ledger", WHITE), 0.5),
            *[(lambda i=i: [idc.animate.move_to([BX[i], BY + 0.85, 0])], 0.45) for i in range(1, 4)],
            "all the way",
            (lambda: [idc.animate.move_to([BX[4] - 1.7, ROW_Y[0], 0])], 0.5),
        ])
        self.steps("There, the insert says: if this id is already here, do nothing. And the money moves only if a row went in.", [
            "the insert says",
            (lambda: [*self.set_guard(3, GREEN_M, name="request id: unique", sub="already here? do nothing"),
                      *self.cap("if this id is already here, do nothing", GREEN_M)], 0.7),
            "the money moves",
            (lambda: [glow(self.rows[0][0], GREEN_M)], 0.7),
        ])
        bounce = T("already here", 18, GREEN_M).move_to([BX[4], ROW_Y[1], 0])
        self.steps("The retry: nothing. The redelivery: nothing. And the lab's last line: 0.", [
            (lambda: [FadeOut(self.rows[1]), FadeOut(self.rows[2]), *self.uncap()], 0.5),
            "The retry",
            (lambda: [self.tok(0), self.tok_ledger()], 0.5),
            (lambda: [FadeIn(bounce)], 0.3),
            "The redelivery",
            (lambda: [FadeOut(bounce), self.tok_ledger()], 0.5),
            (lambda: [FadeIn(bounce)], 0.3),
            "the lab's last",
            (lambda: [FadeOut(bounce), FadeIn(tab[3], shift=0.1 * UP)], 0.6),
        ])
        self.rows = self.rows[:1]

        # ---------------- scene 7: the guardrail and the moral ----------------
        self.steps("So are the lower guards useless? No. TCP's resending saves you from redoing a whole transfer for every lost packet.", [
            (lambda: [*self.set_guard(0, GREY_B), *self.set_guard(1, GREY_B), *self.set_guard(2, GREY_B)], 0.6),
            "TCP's resending",
            (lambda: [glow(self.gd[0][0], GREEN_M)], 0.7),
        ])
        self.steps("Lower layers make the common case fast. Correctness is checked at the ends.", [
            (lambda: self.cap("lower layers make the common case fast", WHITE), 0.5),
            "Correctness",
            (lambda: [*self.cap("lower layers make the common case fast. correctness is checked at the ends.", YELLOW_M, 26),
                      glow(nodes[0][0], GOLD_M), glow(nodes[4][0], GOLD_M)], 0.8),
        ], after=0.4)
        self.steps("And make the id once per tap. A fresh id on every attempt is a fresh transfer every time.", [
            (lambda: [*self.cap("one id per tap, not per attempt", GOLD_M), pulse(idc[1], GOLD_M)], 0.6),
        ])
        self.steps("One quick check. Kafka's exactly-once mode is on, and there's no request id. "
                   "The consumer dies after the insert, before saving its offset. One row, or two? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(idc), FadeOut(VGroup(*tab, head)),
                      *self.set_guard(3, GREY_B), *self.set_guard(2, GREEN_M)], 0.6),
            "The consumer dies",
            (lambda: [Create(crash)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Two. The ledger's save happened outside Kafka, so only an id checked at the ledger stops it.", [
            (lambda: [*self.uncap(), FadeOut(crash), self.tok(2)], 0.5),
            (lambda: [self.tok_ledger()], 0.4),
            (lambda: self.add_row(RED_M), 0.4),
            "The ledger's save",
            (lambda: [*self.set_guard(2, RED_M, sub="the ledger is outside it")], 0.5),
            "only an id",
            (lambda: [*self.set_guard(3, GREEN_M, name="request id: unique", sub="already here? do nothing"),
                      *self.cap("only an id checked at the ledger stops it", YELLOW_M)], 0.6),
        ], after=0.4)
        self.wait(2.0)

    # tokens that don't need the hop arrows yet, and the last hop
    def tok_free(self, i):
        a = np.array([BX[0] + BW / 2 + 0.04, BY, 0])
        b = np.array([BX[4] - BW / 2 - 0.04, BY, 0])
        d = Dot(radius=0.09, color=GOLD_M).move_to(a)
        return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=0.5), FadeOut(d, run_time=0.08))

    def tok_ledger(self):
        return self.tok(3)

    def back_tok(self):
        a = np.array([BX[1] - BW / 2 - 0.04, BY - 0.2, 0])
        b = np.array([GX[0], BY - 0.2, 0])
        d = Dot(radius=0.09, color=GREEN_M).move_to(a)
        return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, Line(a, b), run_time=0.5), FadeOut(d, scale=2, run_time=0.25))

    def _g(self, k):
        self.gd[k] = guard(k)
        return self.gd[k]
