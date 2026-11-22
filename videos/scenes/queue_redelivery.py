from sfz import *

# The letter A naming a consumer: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bm([1-5])\b", lambda m: "M " + "zero one two three four five".split()[int(m.group(1))]))
SAY.insert(0, (r"\bRabbitMQ's\b", "Rabbit M Q's"))
SAY.insert(0, (r"\bRabbitMQ\b", "Rabbit M Q"))
SAY.insert(0, (r"\bauto-ack\b", "auto ack"))
SAY.insert(0, (r"\bunacked\b", "un-acked"))
SAY.insert(0, (r"\bFIFO\b", "fye-foe"))
SAY.insert(0, (r"\bbasicAck\b", "basic ack"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
QY = 2.0                                   # the queue's row
QL, QR = -6.6, 0.5                         # the queue's box, left and right
SP = 1.4
SLOT = [-0.25 - SP * j for j in range(5)]  # slot 0 is the front, at the right
CX, AY, BY = 4.6, 2.55, 0.65               # consumers A and B
HX = 2.1                                   # where a consumer's held message sits
LY = -2.45                                 # the ledger's row
LX = [-5.4 + 1.42 * j for j in range(6)]
CAP_Y, BAR_Y = -0.72, -1.22
A_C, B_C = TEAL_M, PURPLE_M
KIND = {"auth": BLUE_M, "capture": GREEN_M, "refund": GOLD_M}
MSGS = [("m1", "auth 40"), ("m2", "capture 40"), ("m3", "auth 25"), ("m4", "capture 25"), ("m5", "refund 10")]


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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def msg(i):
    name, what = MSGS[i]
    c = KIND[what.split()[0]]
    r = RoundedRectangle(corner_radius=0.1, width=1.3, height=0.78, stroke_color=c, stroke_width=2.5).set_fill(fillc(c, 0.22), 1)
    return VGroup(r, M(name, 20).move_to([0, 0.15, 0]), T(what, 15, GREY_A).move_to([0, -0.17, 0])).move_to([SLOT[i], QY + 0.12, 0])


def slip(i):
    r = RoundedRectangle(corner_radius=0.06, width=1.0, height=0.78, stroke_color=GREY_A, stroke_width=2.5).set_fill("#1c1c1c", 1)
    lines = VGroup(*[Line([-0.3, y, 0], [0.3 - 0.12 * (k % 2), y, 0], stroke_width=2, color=GREY_C) for k, y in enumerate((0.15, 0, -0.15))])
    return VGroup(r, lines).move_to([SLOT[i], QY + 0.12, 0])


def consumer(color, y):
    r = RoundedRectangle(corner_radius=0.14, width=3.0, height=1.1, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    return r.move_to([CX, y, 0])


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.3, height=3.6, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.6, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.9, 2.05)
    rows = VGroup()
    cw = M("x" * 40, 13).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 13, col), x - 2.9 + ind, 1.5 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["channel.basicConsume(\"ledger\", false,   // manual acks",
        "    (consumerTag, d) -> {",
        "        book(d.getBody());",
        "        long tag = d.getEnvelope().getDeliveryTag();",
        "        channel.basicAck(tag, false);  // last",
        "    }, consumerTag -> {});"]
KOTLIN = ["channel.basicConsume(\"ledger\", false,   // manual acks",
          "    DeliverCallback { _, d ->",
          "        book(d.body)",
          "        val tag = d.envelope.deliveryTag",
          "        channel.basicAck(tag, false)   // last",
          "    }, CancelCallback { })"]


class QueueRedelivery(Base):
    """msg-01, section 2. The café rail: a slip stays above the cook's station until the dish goes out. A broker's
    queue, one consumer (the ledger). Auto-ack loses m1 in a crash; manual acks: unacked until the ack; a crash
    after booking and before the ack brings the message back, booked twice (at-least-once). Two competing
    consumers, five messages for account 17 (auth 40, capture 40, auth 25, capture 25, refund 10), prefetch 1:
    B crashes holding m3, m3 goes back to the front but m4 has left, so the ledger books m1 m2 m4 m3 m5. FIFO only
    where it hands messages out. Java and Kotlin consumer, single active consumer, the receipt email, a check."""

    # --- small state helpers: each returns animations and records what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            old = self.lab.pop(k, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def status(self, i, s, color=GREY_B):
        return self.put(f"st{i}", T(s, 16, color).move_to([SLOT[i], QY - 0.5, 0]))

    def cstat(self, who, s, color=GREY_B):
        y = AY if who == "A" else BY
        return self.put(f"cs{who}", T(s, 18, color).move_to([CX, y - 0.22, 0]))

    def cname(self, who, s):
        y = AY if who == "A" else BY
        return self.put(f"cn{who}", T(s, 22).move_to([CX, y + 0.2, 0]))

    def give(self, i, who, auto=False):
        """The broker hands q[i] to a consumer: a copy goes to the consumer, the queue keeps it set aside (or deletes it)."""
        y = AY if who == "A" else BY
        h = self.q[i].copy()
        self.held[who] = (i, h)
        an = [h.animate.move_to([HX, y, 0])]
        if auto:
            an += [FadeOut(self.q[i]), *self.drop(f"st{i}")]
        else:
            an += [self.q[i].animate.set_opacity(0.3), *self.status(i, f"unacked, {who}", YELLOW_M)]
        return an

    def book(self, who, color=None):
        i, h = self.held[who]
        self.booked.append(h)
        h.generate_target()
        h.target.move_to([LX[len(self.booked) - 1], LY - 0.15, 0])
        if color:
            h.target[0].set_stroke(color, width=4)
        return [MoveToTarget(h)]

    def ack_fly(self, who):
        y = AY if who == "A" else BY
        c = chip("ack", GREEN_M, 18, mono=True).move_to([HX, y, 0])
        i = self.held[who][0]
        self._ackc = c
        return [Succession(FadeIn(c, run_time=0.15), c.animate(run_time=0.75).move_to([SLOT[i], QY + 0.12, 0]))]

    def ack_land(self, who):
        i = self.held[who][0]
        return [FadeOut(self._ackc), FadeOut(self.q[i]), *self.drop(f"st{i}")]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.held = {}
        self.booked = []
        self.title_card("When does a message leave the queue?", "acknowledgements, redelivery, and the order of the work")

        # ---------------- scene 1: the question ----------------
        qbox = RoundedRectangle(corner_radius=0.16, width=QR - QL, height=1.5, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        qbox.move_to([(QL + QR) / 2, QY, 0])
        front = T("front", 18, GREY_C).move_to([SLOT[0], QY + 1.02, 0])
        slips = [slip(i) for i in range(3)]
        ra = consumer(A_C, AY)
        self.steps("Picture the rail above a café kitchen. The cashier clips each order slip to it, and the cooks take them from the front.", [
            (lambda: [FadeIn(qbox), *self.put("qlab", left_at(T("the rail, above the kitchen hatch", 22, GREY_B), QL + 0.05, QY + 1.02))], 0.8),
            "The cashier",
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.3 * RIGHT) for s in reversed(slips)], lag_ratio=0.25)], 1.2),
            "and the cooks",
            (lambda: [FadeIn(ra, shift=0.2 * LEFT), *self.cname("A", "cook"), *self.cstat("A", "free"), FadeIn(front)], 0.8),
        ])
        s0 = slips[0]
        qm = T("?", 48, YELLOW_M).move_to([HX, AY - 1.15, 0])
        self.steps("A cook takes a slip. When can it go in the bin? When she takes it, or when the dish goes out? "
                   "And what if she walks out halfway? Hold that thought.", [
            (lambda: [s0.animate.move_to([HX, AY, 0]), *self.cstat("A", "cooking")], 0.9),
            "When can",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "And what if",
            (lambda: [glow(ra, RED_M, 1.03)], 0.9),
        ])

        # ---------------- scene 2: the kitchen's rule ----------------
        self.steps("The kitchen has a rule. The slip stays clipped above the cook's station until the dish goes out. Only then is it thrown away.", [
            (lambda: [FadeOut(qm), *self.cap("the slip stays above the station until the dish goes out")], 0.6),
            "Only then",
            (lambda: [FadeOut(s0, shift=0.6 * DOWN), *self.cstat("A", "dish out: slip in the bin", GREEN_M)], 0.9),
        ])
        s1 = slips[1]
        self.steps("If the cook walks out halfway, her slip goes back on the rail, and the next free cook picks it up.", [
            (lambda: [s1.animate.move_to([HX, AY, 0]), *self.cstat("A", "cooking")], 0.8),
            "walks out",
            (lambda: [ra.animate.set_stroke(RED_M), *self.cstat("A", "walked out", RED_M)], 0.6),
            "goes back",
            (lambda: [s1.animate.move_to([SLOT[1], QY + 0.12, 0])], 0.9),
            "and the next",
            (lambda: [ra.animate.set_stroke(A_C), *self.cstat("A", "free")], 0.5),
            (lambda: [s1.animate.move_to([HX, AY, 0]), *self.cstat("A", "cooking")], 0.8),
            (lambda: [FadeOut(s1, shift=0.6 * DOWN), *self.cstat("A", "dish out: slip in the bin", GREEN_M)], 0.8),
        ])

        # ---------------- scene 3: the map ----------------
        self.q = [msg(i) for i in range(5)]
        self.steps("Programs pass messages the same way. A message is a small piece of data, such as: an account asks to pay 40 euros.", [
            (lambda: [*self.uncap(), FadeOut(slips[2]), *self.cstat("A", "free")], 0.5),
            "A message is",
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.3 * RIGHT) for m in reversed(self.q)], lag_ratio=0.2),
                      *self.cap("slip = message")], 1.4),
            "such as",
            (lambda: [glow(self.q[0][0], BLUE_M, 1.08)], 0.8),
        ])
        self.steps("A broker is a program in the middle that holds messages. Its queue is the rail. "
                   "The program that sends is the cashier, and each program that reads is a cook, called a consumer.", [
            "Its queue",
            (lambda: [*self.put("qlab", left_at(T("queue, inside the broker: account 17", 22, GREY_B), QL + 0.05, QY + 1.02)),
                      *self.cap("rail = queue, in a broker that holds messages"), glow(qbox, GREY_A, 1.01)], 0.9),
            "The program that sends",
            (lambda: self.cap("cashier = the program that sends"), 0.5),
            "called a consumer",
            (lambda: [*self.cname("A", "consumer A"), *self.cap("cook = consumer, a program that reads")], 0.7),
        ])
        lbox = RoundedRectangle(corner_radius=0.16, width=12.8, height=1.5, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        lbox.move_to([0, LY, 0])
        llab = left_at(T("the ledger books, in this order:", 20, GREY_B), -6.2, LY + 0.5)
        self.steps("We'll use RabbitMQ, a free broker program that many companies run. Our consumer is the ledger, "
                   "the program that keeps each account's balance.", [
            (lambda: self.cap("RabbitMQ: a free broker program"), 0.5),
            "Our consumer",
            (lambda: [FadeIn(lbox), FadeIn(llab), *self.cstat("A", "the ledger, free")], 0.9),
        ])

        # ---------------- scene 4: the tempting shortcut ----------------
        self.steps("Now, the tempting shortcut: delete each message the moment the broker sends it.", [
            (lambda: self.cap("shortcut: delete it the moment it's sent", PURPLE_M), 0.6),
        ])
        cross = tick(False, 0.17).move_to([HX, AY, 0])
        self.steps("Watch the ledger take m1 and crash halfway. The broker already deleted it. The payment is gone.", [
            "take m1",
            (lambda: [*self.give(0, "A", auto=True), *self.cstat("A", "booking m1")], 0.9),
            "and crash",
            (lambda: [ra.animate.set_stroke(RED_M), *self.cstat("A", "crashed", RED_M)], 0.5),
            "already deleted",
            (lambda: [glow(qbox, RED_M, 1.01)], 0.8),
            "The payment is gone",
            (lambda: [self.held["A"][1].animate.set_opacity(0.2), Create(cross)], 0.6),
        ])
        self.steps("That's a kitchen that bins each slip as soon as a cook glances at it. Very tidy. "
                   "Until the cook goes home with your lunch in her head.", [
            "Until the cook",
            (lambda: [self.held["A"][1].animate.shift(0.5 * RIGHT).set_opacity(0)], 1.2),
        ])
        self.steps("RabbitMQ calls this auto-ack, and its own guide calls it unsafe. "
                   "Nothing twice, and some never: that's at-most-once delivery.", [
            "calls this",
            (lambda: self.cap("auto-ack: deleted when sent.  RabbitMQ's guide: unsafe", RED_M), 0.6),
            "that's at-most-once",
            (lambda: self.cap("at-most-once: never twice, some never", RED_M), 0.6),
        ])

        # ---------------- scene 5: the ack ----------------
        q0 = msg(0)
        def back():
            self.q[0] = q0
            return [FadeOut(cross), FadeOut(self.held["A"][1]), ra.animate.set_stroke(A_C), *self.cstat("A", "the ledger, free"),
                    *self.uncap(), FadeIn(q0)]

        self.steps("Let's put m1 back, and do it the kitchen's way. The broker sends m1, and keeps it. Until the consumer is done, "
                   "m1 is unacked: still in the queue, set aside for that consumer. The slip above the station.", [
            (back, 0.8),
            "The broker sends",
            (lambda: [*self.give(0, "A"), *self.cstat("A", "booking m1")], 0.9),
            "m1 is unacked",
            (lambda: [Indicate(self.lab["st0"], color=YELLOW_M, scale_factor=1.2), *self.cap("unacked: sent, still in the queue, set aside")], 0.9),
            "The slip above",
            (lambda: [glow(self.held["A"][1][0], YELLOW_M, 1.08)], 0.8),
        ])
        self.steps("After it books the payment, the consumer sends a short note: done, delete it. "
                   "That note is an acknowledgement, or ack.", [
            (lambda: self.book("A"), 0.9),
            "a short note",
            (lambda: self.ack_fly("A"), 0.9),
            (lambda: [*self.ack_land("A"), *self.cstat("A", "the ledger, free")], 0.5),
            "That note is",
            (lambda: self.cap("ack: the work is done, delete it", GREEN_M), 0.6),
        ])
        self.steps("If the connection closes before the ack, the broker puts the message back and sends it again, "
                   "flagged as redelivered. That's redelivery.", [
            (lambda: self.cap("no ack and the connection closes: back in the queue, flagged redelivered", GOLD_M), 0.6),
        ])

        # ---------------- scene 6: predict a crash after the work ----------------
        self.steps("Here's a puzzle. The ledger books m2, adding it to the balance, and crashes just before its ack leaves. "
                   "What happens next? Pause and guess.", [
            (lambda: [*self.uncap(), *self.give(1, "A"), *self.cstat("A", "booking m2")], 0.9),
            "adding it",
            (lambda: self.book("A"), 0.9),
            "and crashes",
            (lambda: [ra.animate.set_stroke(RED_M), *self.cstat("A", "crashed before the ack", RED_M)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The broker can't tell this crash from one before the work started. So m2 comes back, "
                   "and the ledger books it a second time.", [
            (lambda: [*self.uncap(), self.q[1].animate.set_opacity(1), *self.status(1, "redelivered", GOLD_M)], 0.7),
            "So m2 comes back",
            (lambda: [ra.animate.set_stroke(A_C), *self.give(1, "A"), *self.cstat("A", "m2, redelivered", GOLD_M)], 0.9),
            "a second time",
            (lambda: self.book("A", RED_M), 0.9),
            (lambda: [self.booked[1][0].animate.set_stroke(RED_M, width=4)], 0.3),
            (lambda: self.ack_fly("A"), 0.9),
            (lambda: [*self.ack_land("A"), *self.cstat("A", "the ledger, free")], 0.4),
        ])
        self.steps("Nothing is lost, and some messages are handled twice: that's at-least-once delivery. "
                   "The ledger must spot the repeat itself, and the lesson's worked example shows how.", [
            (lambda: self.cap("at-least-once: nothing lost, some twice", GOLD_M), 0.6),
            "spot the repeat",
            (lambda: [glow(self.booked[1][0], RED_M, 1.1), glow(self.booked[2][0], RED_M, 1.1)], 0.9),
        ])

        # ---------------- scene 7: two consumers and the order ----------------
        rb = consumer(B_C, BY)
        fresh = [msg(i) for i in range(5)]
        self.steps("One ledger is slow. So we run two copies, A and B, on one queue, and the broker gives each message to only one. "
                   "They're called competing consumers.", [
            (lambda: [*self.uncap(), *[FadeOut(b) for b in self.booked], *[FadeIn(m) for m in fresh[:2]],
                      *[m.animate.set_opacity(1) for m in self.q[2:]]], 0.8),
            "So we run two",
            (lambda: [FadeIn(rb, shift=0.2 * LEFT), *self.cname("B", "consumer B"), *self.cstat("B", "the ledger, free")], 0.8),
            "They're called",
            (lambda: self.cap("competing consumers: copies of one program on one queue"), 0.6),
        ])
        self.q[0], self.q[1] = fresh[0], fresh[1]
        self.booked = []
        self.held = {}
        self.steps("Five messages for account 17 wait in order. Each card payment takes two. When you tap your card, "
                   "the bank first sets the money aside: that's the auth. Later the money really moves to the shop: that's the capture.", [
            (lambda: [LaggedStart(*[glow(m[0], GREY_A, 1.06) for m in reversed(self.q)], lag_ratio=0.15)], 1.2),
            "that's the auth",
            (lambda: [*self.cap("auth: the money is set aside", BLUE_M), glow(self.q[0][0], BLUE_M, 1.08), glow(self.q[2][0], BLUE_M, 1.08)], 0.8),
            "that's the capture",
            (lambda: [*self.cap("capture: the money really moves", GREEN_M), glow(self.q[1][0], GREEN_M, 1.08), glow(self.q[3][0], GREEN_M, 1.08)], 0.8),
        ])
        self.steps("The ledger must book each auth before its capture. And this is a queue: first in, first out. So the order is safe. Right?", [
            (lambda: self.cap("each auth before its capture"), 0.5),
            "first in, first out",
            (lambda: [*self.cap("first in, first out... so the order is safe?", PURPLE_M), glow(qbox, PURPLE_M, 1.01)], 0.8),
        ])
        self.steps("Each holds one message at a time. m1 goes to A, and m2 to B. Both book, and ack. So far so good.", [
            (lambda: [*self.uncap(), *self.cstat("A", "holds one at a time"), *self.cstat("B", "holds one at a time")], 0.6),
            "m1 goes",
            (lambda: [*self.give(0, "A"), *self.give(1, "B")], 0.9),
            "Both book",
            (lambda: [*self.book("A"), *self.book("B")], 0.9),
            (lambda: [*self.ack_fly("A")], 0.8),
            (lambda: [*self.ack_land("A")], 0.3),
            (lambda: [*self.ack_fly("B")], 0.8),
            (lambda: [*self.ack_land("B")], 0.3),
        ])
        self.steps("Next, B takes m3, the auth of 25, and A takes m4, its capture.", [
            (lambda: [*self.give(2, "B"), *self.cstat("B", "booking m3")], 0.9),
            "and A takes",
            (lambda: [*self.give(3, "A"), *self.cstat("A", "booking m4")], 0.9),
        ])
        crossb = tick(False, 0.17).move_to([CX + 1.22, BY, 0])
        self.steps("Now B crashes before its ack. The broker puts m3 back at its old place, the front of the queue. "
                   "In what order does the ledger book the rest? Pause and guess.", [
            (lambda: [rb.animate.set_stroke(RED_M), *self.cstat("B", "crashed", RED_M), Create(crossb)], 0.7),
            "The broker puts",
            (lambda: [self.held["B"][1].animate.move_to(self.q[2])], 0.9),
            (lambda: [FadeOut(self.held["B"][1]), self.q[2].animate.set_opacity(1), *self.status(2, "back", GOLD_M)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        bad = T("a capture before its auth", 20, RED_M)
        self.steps("Consumer A was still busy with m4. It finishes, and books the capture of 25, for money the ledger never saw set aside.", [
            (lambda: [*self.uncap(), Indicate(self.lab["st3"], color=YELLOW_M, scale_factor=1.2)], 0.8),
            "It finishes",
            (lambda: self.book("A", RED_M), 0.9),
            (lambda: [*self.ack_fly("A")], 0.7),
            (lambda: [*self.ack_land("A"), *self.cstat("A", "free")], 0.3),
            "for money",
            (lambda: [FadeIn(left_at(bad, LX[4] - 0.4, LY - 0.15))], 0.6),
        ])
        self.steps("Then A gets m3, marked redelivered, and books it. Then m5. The ledger's order: m1, m2, m4, m3, m5.", [
            (lambda: [*self.give(2, "A"), *self.cstat("A", "m3, redelivered", GOLD_M)], 0.8),
            "and books it",
            (lambda: [*self.book("A"), FadeOut(bad)], 0.8),
            (lambda: self.ack_fly("A"), 0.6),
            (lambda: [*self.ack_land("A")], 0.3),
            "Then m5",
            (lambda: [*self.give(4, "A"), *self.cstat("A", "booking m5")], 0.6),
            (lambda: self.book("A"), 0.6),
            (lambda: self.ack_fly("A"), 0.6),
            (lambda: [*self.ack_land("A"), *self.cstat("A", "free")], 0.3),
            "The ledger's order",
            (lambda: [LaggedStart(*[glow(b[0], RED_M if k in (2, 3) else GREY_A, 1.08) for k, b in enumerate(self.booked)], lag_ratio=0.3)], 1.6),
        ])
        self.steps("Well... that's a capture before its auth.", [
            (lambda: [glow(self.booked[2][0], RED_M, 1.1), *self.cap("capture 25 (m4) booked before auth 25 (m3)", RED_M)], 0.6),
        ], after=0.5)

        # ---------------- scene 8: the real rule ----------------
        self.steps("Nothing was lost, and nothing was booked twice. The queue even kept its order: it handed out m3 before m4. "
                   "The work didn't, because two machines finish at their own pace.", [
            (lambda: [rb.animate.set_stroke(B_C), *self.cstat("B", "back, free"), FadeOut(crossb)], 0.7),
            "The queue even",
            (lambda: [glow(qbox, GREEN_M, 1.01), *self.cap("the queue handed out m3, then m4: in order", GREEN_M)], 0.9),
            "The work didn't",
            (lambda: [*self.cap("two machines finish at their own pace", RED_M), glow(ra, A_C, 1.03), glow(rb, B_C, 1.03)], 0.9),
        ])
        self.steps("A queue is first in, first out, FIFO for short, only at the moment it hands messages out. "
                   "It can't make two consumers finish in order.", [
            (lambda: self.cap("FIFO: in order where it hands messages out, and only there", YELLOW_M), 0.7),
            "It can't make",
            (lambda: self.cap("a FIFO queue can't make two consumers finish in order", YELLOW_M), 0.7),
        ])
        self.steps("Here the café picture stops working. A broker writes each message to disk on several machines first. "
                   "And it never knows if a dish was cooked, only whether a cook said so.", [
            (lambda: self.cap("where the café picture stops working"), 0.5),
            "A broker writes",
            (lambda: self.cap("each message is written to disk on several machines first"), 0.5),
            "And it never knows",
            (lambda: self.cap("the broker knows only whether a consumer said so: the ack"), 0.5),
        ])

        # ---------------- scene 9: the code ----------------
        diagram = VGroup(qbox, front, ra, rb, lbox, llab, *self.booked, *[v for v in self.lab.values()])
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(panel, rows, color):
            return [panel[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows]

        self.steps("Here's that consumer in Java and Kotlin. false turns auto-ack off, the middle books the payment, "
                   "and basicAck comes last.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
            "false turns",
            (lambda: [*hl(jp, (0,), GOLD_M), *hl(kp, (0,), GOLD_M)], 1.2),
            "the middle",
            (lambda: [*hl(jp, (2,), BLUE_M), *hl(kp, (2,), BLUE_M)], 1.0),
            "and basicAck",
            (lambda: [*hl(jp, (3, 4), GREEN_M), *hl(kp, (3, 4), GREEN_M)], 1.4),
        ], after=0.5)

        # ---------------- scene 10: the guardrail ----------------
        self.steps("The fix for order, inside a broker, is one consumer per queue, which RabbitMQ calls single active consumer. "
                   "You keep the order, and give up sharing the work. The next two lessons show a log that keeps both.", [
            (lambda: [FadeOut(jp), FadeOut(kp), diagram.animate.set_opacity(1)], 0.8),
            "one consumer per queue",
            (lambda: [rb.animate.set_opacity(0.2), self.lab["cnB"].animate.set_opacity(0.2), self.lab["csB"].animate.set_opacity(0.2),
                      *self.cap("one consumer per queue: single active consumer")], 0.8),
            "give up sharing",
            (lambda: [*self.cap("order kept; one machine does all the work", GOLD_M), glow(ra, A_C, 1.03)], 0.7),
            "The next two",
            (lambda: [rb.animate.set_opacity(1), self.lab["cnB"].animate.set_opacity(1), self.lab["csB"].animate.set_opacity(1),
                      *self.cap("next: a log keeps the order and shares the work")], 0.8),
        ])

        # ---------------- scene 11: the moral, and a check ----------------
        self.steps("Ever had the same receipt email twice? Now you know: somewhere, a consumer crashed before its ack.", [
            (lambda: self.cap("the same receipt email, twice?", WHITE), 0.5),
            "Now you know",
            (lambda: self.cap("a consumer crashed before its ack: at-least-once", GOLD_M), 0.6),
        ])
        self.steps("So: the slip stays above the station until the dish goes out. A crash brings it back. "
                   "And two cooks can finish in the wrong order.", [
            (lambda: self.cap("unacked until the ack", YELLOW_M, 28), 0.5),
            "A crash brings",
            (lambda: self.cap("a crash brings it back", GOLD_M, 28), 0.5),
            "And two cooks",
            (lambda: self.cap("two consumers can finish out of order", RED_M, 28), 0.5),
        ], after=0.5)

        # the check: auto-ack this time, from the moment m1 and m2 are done
        def reset():
            out = [FadeOut(b) for b in self.booked[2:]]
            self.q = [None, None] + [msg(i) for i in range(2, 5)]
            out += [FadeIn(m) for m in self.q[2:]]
            self.booked = self.booked[:2]
            return out

        self.steps("One quick check. Turn auto-ack back on, and let B crash holding m3 again. What does the ledger book? Pause and think.", [
            (lambda: [*self.uncap(), *reset(), *self.cstat("A", "auto-ack", RED_M), *self.cstat("B", "auto-ack", RED_M)], 0.8),
            "and let B crash",
            (lambda: [*self.give(2, "B", auto=True), *self.give(3, "A", auto=True)], 0.9),
            (lambda: [rb.animate.set_stroke(RED_M), Create(crossb)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("m1, m2, m4, m5. m3 was deleted when it was sent, so it never comes back, and the capture of 25 has no auth at all.", [
            (lambda: [*self.uncap(), *self.book("A", RED_M)], 0.7),
            (lambda: [*self.give(4, "A", auto=True)], 0.5),
            (lambda: self.book("A"), 0.6),
            "m3 was deleted",
            (lambda: [self.held["B"][1].animate.set_opacity(0.15)], 0.6),
            "never comes back",
            (lambda: [*self.cap("auto-ack: m3 is lost, not late", RED_M, 28)], 0.6),
        ], after=0.3)
        self.wait(2.0)
