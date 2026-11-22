from sfz import *

SAY.insert(0, (r"\bpay-(\d+)", r"pay \1"))
SAY.insert(0, (r"\bTimeoutException\b", "timeout exception"))
SAY.insert(0, (r"\backs=all\b", "acks equals all"))
SAY.insert(0, (r"\backs=1\b", "acks equals one"))
SAY.insert(0, (r"\benable\.idempotence\b", "enable dot idempotence"))
SAY.insert(0, (r"\bsend\(\)", "send"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
P_C = np.array([-4.9, 1.75, 0])
L_C = np.array([4.9, 1.75, 0])
BW, BH = 3.2, 1.9
REQ_Y, ANS_Y = 2.15, 1.3
X0, X1 = P_C[0] + BW / 2, L_C[0] - BW / 2
LOG_Y, OFF_Y, LOGLAB_Y, NOTE_Y, BAR_Y, CAP_Y = -0.6, 0.0, -1.25, -1.85, -2.78, -3.27
OFFS = list(range(14, 22))
CW = 1.45
CX = {o: -5.8 + CW / 2 + CW * k for k, o in enumerate(OFFS)}


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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
        for key in keys:
            old = self.lab.pop(key, None)
            if old is not None:
                out.append(FadeOut(old))
        return out


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def rbox(w, h, color, c):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)


def rec(text, color=WHITE, size=17):
    t = M(text, size, color)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.42, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).set_z_index(5)


def harrow(x0, x1, y, color=GREY_C):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=2.5, color=color, max_tip_length_to_length_ratio=0.03)


def cell(o):
    return Rectangle(width=CW - 0.1, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([CX[o], LOG_Y, 0])


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.5, height=3.4, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.55, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 1.9)
    rows = VGroup()
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * M("x" * 40, 16).width / 40
        rows.add(left_at(M(s.strip() if s.strip() else " ", 16, col), x - 3.0 + ind, 1.35 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["var props = new Properties();",
        "// say it by name",
        "props.put(\"enable.idempotence\", \"true\");",
        "props.put(\"acks\", \"all\");",
        "var producer =",
        "    new KafkaProducer<String, String>(props);"]
KOTLIN = ["val props = Properties().apply {",
          "    // say it by name",
          "    put(\"enable.idempotence\", \"true\")",
          "    put(\"acks\", \"all\")",
          "}",
          "val producer =",
          "    KafkaProducer<String, String>(props)"]


class IdempotentProducer(Base):
    """msg-06, section 3. The train-tunnel message sent twice. The producer sends pay-16, the leader writes it at
    offset 16, the answer is lost, the retry is written again at 17. With five requests in flight a retried pay-17
    lands after pay-18. The friend who keeps a note per sender: a name and a number on every message. The idempotent
    producer: producer id 5, sequence numbers, the leader remembers the last five batches; a retry of 16 writes
    nothing and answers offset 16; 18 before 17 is refused (OUT_OF_ORDER_SEQUENCE_NUMBER). Requirements and the silent
    trap; the limit (your own second send()). Code in Java and Kotlin, the moral, a check."""

    # --- state helpers ---
    def ptext(self, title, alias=None, state=None, scolor=GREY_B):
        out = self.put("pt", T(title, 26).move_to(P_C + 0.45 * UP))
        out += self.put("pa", T(alias, 16, GREY_B).move_to(P_C + 0.08 * UP)) if alias else self.drop("pa")
        out += self.put("ps", fit(M(state, 17, scolor), BW - 0.3).move_to(P_C + 0.42 * DOWN)) if state else self.drop("ps")
        return out

    def ltext(self, title, alias=None, state=None, scolor=GREY_B):
        out = self.put("lt", T(title, 26).move_to(L_C + 0.45 * UP))
        out += self.put("la", T(alias, 16, GREY_B).move_to(L_C + 0.08 * UP)) if alias else self.drop("la")
        out += self.put("ls", fit(M(state, 17, scolor), BW - 0.3).move_to(L_C + 0.42 * DOWN)) if state else self.drop("ls")
        return out

    def lstate(self, state, color=GREY_B):
        return self.put("ls", fit(M(state, 17, color), BW - 0.3).move_to(L_C + 0.42 * DOWN))

    def pstate(self, state, color=GREY_B):
        return self.put("ps", fit(M(state, 17, color), BW - 0.3).move_to(P_C + 0.42 * DOWN))

    def write(self, o, text, color=WHITE):
        m = rec(text, color, 16).move_to([CX[o], LOG_Y, 0])
        return self.put(f"c{o}", m, DOWN)

    def clear_log(self, frm=14):
        return self.drop(*[f"c{o}" for o in OFFS if o >= frm])

    def req(self, text, color=WHITE, to_log=None, frac=1.0, lost=False, log_text=None):
        """A request chip travels producer to leader (part way if frac < 1); if to_log, the leader writes log_text
        (default: the chip's first word) at that offset."""
        m = rec(text, color).move_to([X0 + 0.2 + rec(text).width / 2, REQ_Y, 0])
        end = [X1 - 0.2 - m.width / 2 if frac >= 1 else 0, REQ_Y, 0]
        seq = [FadeIn(m, run_time=0.1), m.animate(run_time=0.7, rate_func=smooth).move_to(end)]
        if lost:
            seq += [FadeOut(m, scale=1.6, run_time=0.25)]
        elif to_log is not None:
            key = f"c{to_log}"
            old = self.lab.get(key)
            new = rec(log_text or text.split()[0], color, 16).move_to([CX[to_log], LOG_Y, 0])
            self.lab[key] = new
            land = [FadeOut(m, target_position=new.get_center(), run_time=0.5), FadeIn(new, run_time=0.5)]
            if old is not None:
                land.append(FadeOut(old, run_time=0.3))
            seq += [AnimationGroup(*land)]
        else:
            seq += [FadeOut(m, run_time=0.15)]
        return [Succession(*seq)]

    def ans(self, text, color=GREEN_M, lost=False):
        m = rec(text, color).move_to([X1 - 0.7, ANS_Y, 0])
        frac = 0.5 if lost else 1.0
        end = [X1 - 0.7 - frac * (X1 - X0 - 1.4), ANS_Y, 0]
        seq = [FadeIn(m, run_time=0.1), m.animate(run_time=0.7, rate_func=smooth).move_to(end),
               FadeOut(m, scale=1.6 if lost else 1.0, run_time=0.25)]
        return [Succession(*seq)]

    def lost_mark(self, y=ANS_Y, text="answer lost"):
        x = tick(False, 0.15).move_to([0, y, 0])
        lab = T(text, 18, RED_M).move_to([0, y - 0.38, 0])
        return self.put("lost", VGroup(x, lab))

    def settle(self):
        """Hand chips that landed in the log over to the log's labels (they were added by req())."""
        for m in self.flying:
            if m in self.mobjects:
                self.remove(m)
        self.flying = []

    def construct(self):
        self.capm = None
        self.lab, self.flying = {}, []
        self.title_card("Did that payment go twice?", "retries, duplicates, and the idempotent producer")

        pbox = rbox(BW, BH, GOLD_M, P_C)
        lbox = rbox(BW, BH, BLUE_M, L_C)
        a_req = harrow(X0 + 0.1, X1 - 0.1, REQ_Y)
        a_ans = harrow(X1 - 0.1, X0 + 0.1, ANS_Y)
        cells = VGroup(*[cell(o) for o in OFFS])
        offs = VGroup(*[T(str(o), 18, GREY_B).move_to([CX[o], OFF_Y, 0]) for o in OFFS])

        # ---------------- scene 1: the tunnel ----------------
        self.steps("You're on a train, sending a message to a friend, just as it goes into a tunnel. "
                   "The message turns red: not sent. So you tap Retry.", [
            (lambda: [FadeIn(pbox), FadeIn(lbox), *self.ptext("your phone"), *self.ltext("your friend"), GrowArrow(a_req), GrowArrow(a_ans)], 0.9),
            (lambda: self.put("loglab", left_at(T("your friend's chat", 18, GREY_B), -5.8, LOGLAB_Y)), 0.3),
            (lambda: [FadeIn(cells[:3])], 0.4),
            "into a tunnel",
            (lambda: self.req("see you at 7?", WHITE, to_log=14, log_text="at 7?"), 1.3),
            "turns red",
            (lambda: [*self.pstate("not sent", RED_M), glow(pbox, RED_M, 1.03)], 0.6),
            "you tap Retry",
            (lambda: self.req("see you at 7?", WHITE, to_log=15, log_text="at 7?"), 1.3),
        ])
        self.steps("Out of the tunnel, your friend writes back: why did you send that twice?", [
            "why did you",
            (lambda: [*self.cap("why did you send that twice?", WHITE), glow(cells[0], RED_M, 1.05), glow(cells[1], RED_M, 1.05)], 0.8),
        ])
        self.steps("The red mark looked like a fact about the message. It was only a fact about your phone: it had stopped waiting. "
                   "The first copy got through.", [
            "It was only",
            (lambda: [*self.pstate("stopped waiting", RED_M), *self.cap("not sent?  no: stopped waiting")], 0.6),
            "The first copy",
            (lambda: [glow(cells[0], GREEN_M, 1.05)], 0.7),
        ])

        # ---------------- scene 2: the same trap in Kafka ----------------
        self.steps("Kafka, a program that keeps logs of messages and lets other programs read them, sets the same trap.", [
            (lambda: [*self.uncap(), *self.clear_log(), *self.cap("Kafka: keeps logs of messages, for other programs to read")], 0.6),
        ])
        self.steps("The program that writes is the producer, inside the payments app. It sends each payment to the leader, "
                   "the server that adds it to the partition's log, and waits for an answer: the offset, the payment's place in the log.", [
            (lambda: self.ptext("producer", "inside the payments app"), 0.6),
            "the leader",
            (lambda: [*self.ltext("leader", "adds to the log"), *self.put("loglab", left_at(T("one partition's log", 18, GREY_B), -5.8, LOGLAB_Y)),
                      FadeIn(cells[3:]), FadeIn(offs)], 0.8),
            (lambda: [*self.write(14, "pay-14"), *self.write(15, "pay-15")], 0.5),
            "waits for an answer",
            (lambda: [*self.ans("offset 15")], 1.0),
        ])

        # ---------------- scene 3: a lost answer, a retry ----------------
        self.steps("Watch pay-16. It reaches the leader, and the leader writes it at offset 16. Then the answer is lost.", [
            (lambda: [*self.uncap(), *self.ptext("producer", "inside the payments app", "idempotence off"),
                      *self.ltext("leader", "adds to the log", "remembers nothing")], 0.6),
            "It reaches",
            (lambda: self.req("pay-16", YELLOW_M, to_log=16), 1.3),
            "Then the answer",
            (lambda: self.ans("offset 16", GREEN_M, lost=True), 0.9),
            (lambda: self.lost_mark(), 0.4),
        ])
        self.steps("After a while, all the producer knows is that it heard nothing. So it retries, on its own. "
                   "The leader can't tell a retry from a new record, so pay-16 goes in again, at offset 17.", [
            "it heard nothing",
            (lambda: self.pstate("heard nothing", RED_M), 0.5),
            "So it retries",
            (lambda: [*self.drop("lost"), *self.req("pay-16", YELLOW_M, to_log=17)], 1.3),
            "again, at offset 17",
            (lambda: [glow(cells[2], RED_M, 1.05), glow(cells[3], RED_M, 1.05)], 0.8),
        ])
        self.steps("Every reader of this log now sees the payment twice. One coffee, charged twice. Customers have a gift for "
                   "noticing exactly that. So the point really is: a retry is only safe if the leader can recognise it.", [
            (lambda: [*self.write(17, "pay-16", RED_M), *self.write(16, "pay-16", RED_M)], 0.4),
            (lambda: self.cap("every reader sees pay-16 twice", RED_M), 0.4),
            "So the point",
            (lambda: self.cap("a retry is safe only if the leader can recognise it", WHITE), 0.5),
        ])

        # ---------------- scene 4: reordering ----------------
        self.steps("There's a second problem. The producer keeps up to five requests in flight at once. "
                   "Say pay-17's request times out, while pay-18 gets through.", [
            (lambda: [*self.uncap(), *self.clear_log(17), *self.write(16, "pay-16"), *self.cap("up to 5 requests in flight at once")], 0.6),
            "Say pay-17",
            (lambda: [*self.req("pay-17", WHITE, frac=0.5, lost=True)], 1.0),
            (lambda: self.lost_mark(REQ_Y + 0.0, "timed out"), 0.3),
            "while pay-18",
            (lambda: self.req("pay-18", GOLD_M, to_log=17), 1.3),
        ])
        self.steps("The retry of pay-17 lands after pay-18. If pay-18 were a refund, it would now overtake its payment, "
                   "inside one partition.", [
            (lambda: self.drop("lost"), 0.1),
            "The retry",
            (lambda: self.req("pay-17", WHITE, to_log=18), 1.3),
            "overtake",
            (lambda: [*self.cap("a refund ahead of its payment, inside one partition", RED_M), glow(cells[3], RED_M, 1.05)], 0.7),
        ])
        self.steps("You could send one request at a time. That keeps the order, but each connection then waits a round trip "
                   "for every batch, and the lost answer still gives you a duplicate.", [
            (lambda: [*self.cap("one request at a time: order kept, speed lost, duplicates still there")], 0.6),
        ])
        self.steps("What we'd love is for the leader to say: oh, it's you again, I already have that one.", [
            (lambda: self.cap("the wish: \"oh, it's you again. I already have that one.\"", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 5: the friend's note ----------------
        self.steps("Back to the train. Suppose every message carries your name and a number: Sam, message 16. "
                   "And your friend keeps a little note for each sender: the next number she expects, and the last five she got.", [
            (lambda: [*self.uncap(), *self.clear_log(), *self.ptext("your phone", None, "Sam, message 16", YELLOW_M),
                      *self.ltext("your friend")], 0.8),
            "your friend keeps",
            (lambda: self.lstate("Sam: next 17", GREEN_M), 0.6),
            "the last five",
            (lambda: self.put("lnote", T("and the last five she got", 16, GREY_B).move_to(L_C + 0.7 * DOWN)), 0.5),
        ])
        self.steps("Resent 16? She already has it. No second copy; she just replies again. "
                   "18 before 17? She says: wait, send me 17 first.", [
            "Resent 16",
            (lambda: self.req("Sam 16", YELLOW_M), 1.0),
            (lambda: self.cap("16 again: already have it, reply again", GREEN_M), 0.4),
            "18 before 17",
            (lambda: self.req("Sam 18", GOLD_M), 1.0),
            (lambda: self.cap("18 before 17: \"send me 17 first\"", GOLD_M), 0.4),
        ])
        self.steps("Let's map it. Your name is the producer id. The number is the sequence number. "
                   "Your friend is the leader, and her note is what the leader remembers for each producer.", [
            "Your name",
            (lambda: self.cap("your name: the producer id", WHITE), 0.5),
            "The number",
            (lambda: self.cap("the message number: the sequence number", WHITE), 0.5),
            "Your friend",
            (lambda: [*self.cap("your friend: the leader.   her note: what it remembers per producer", WHITE), glow(lbox, BLUE_M, 1.03)], 0.7),
        ])

        # ---------------- scene 6: the idempotent producer ----------------
        self.steps("Here's the real thing. At start-up, the producer gets a producer id from the broker: 5. "
                   "It numbers its records for each partition, so pay-16 has sequence number 16.", [
            (lambda: [*self.uncap(), *self.drop("lnote"), *self.ptext("producer", "producer id 5"), *self.ltext("leader", "adds to the log", "remembers nothing"),
                      *self.write(14, "pay-14"), *self.write(15, "pay-15")], 0.7),
            "pay-16 has",
            (lambda: self.pstate("pay-16: seq 16", YELLOW_M), 0.5),
        ])
        self.steps("The leader writes it at offset 16, and notes: producer 5, next 17. Then the answer is lost again.", [
            (lambda: self.req("id 5 | seq 16", YELLOW_M, to_log=16, log_text="pay-16"), 1.3),
            "and notes",
            (lambda: self.lstate("producer 5: next 17", GREEN_M), 0.5),
            "the answer is lost",
            (lambda: self.ans("offset 16", GREEN_M, lost=True), 0.9),
            (lambda: self.lost_mark(), 0.3),
        ])
        self.steps("The retry carries the same id and the same number. The leader finds 16 among the last five it remembers, "
                   "writes nothing, and answers with the offset it gave the first time: 16.", [
            "The retry",
            (lambda: [*self.drop("lost"), *self.req("id 5 | seq 16", YELLOW_M)], 1.0),
            "writes nothing",
            (lambda: [glow(cells[3], GREY_B, 1.05), *self.put("nothing", T("nothing written", 18, GREY_B).move_to([CX[17], NOTE_Y + 0.25, 0]))], 0.6),
            "answers with",
            (lambda: self.ans("offset 16", GREEN_M), 1.0),
            (lambda: self.pstate("pay-16: offset 16", GREEN_M), 0.4),
        ])
        self.stamp("poster")
        self.steps("This is the idempotent producer. Idempotent means doing something twice has the same effect as doing it once. "
                   "It has been on by default since Kafka 3.0.", [
            (lambda: [*self.drop("nothing"), *self.cap("the idempotent producer", YELLOW_M, 30)], 0.6),
            "Idempotent means",
            (lambda: self.cap("idempotent: twice has the same effect as once", WHITE), 0.5),
            "on by default",
            (lambda: self.cap("on by default since Kafka 3.0"), 0.5),
        ])

        # ---------------- scene 7: predict the gap ----------------
        self.steps("Now the reordering case, with idempotence on. pay-17 times out, and pay-18 arrives first. "
                   "The leader expects 17. What does it do with 18? Pause and guess.", [
            (lambda: [*self.uncap(), *self.ptext("producer", "producer id 5")], 0.5),
            "pay-17 times out",
            (lambda: self.req("seq 17", WHITE, frac=0.5, lost=True), 1.0),
            (lambda: self.lost_mark(REQ_Y, "timed out"), 0.3),
            "and pay-18",
            (lambda: self.req("seq 18", GOLD_M, frac=1.0), 1.0),
            "The leader expects",
            (lambda: [glow(lbox, YELLOW_M, 1.03)], 0.6),
            "Pause and guess",
            (lambda: self.cap("what does the leader do with 18? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It refuses it, with an error called out of order sequence number. Then the producer resends 17, then 18, "
                   "and both are written once, in send order.", [
            (lambda: [*self.uncap(), *self.drop("lost"), *self.ans("refused: out of order", RED_M)], 1.0),
            (lambda: self.cap("OUT_OF_ORDER_SEQUENCE_NUMBER: expected 17, got 18", RED_M), 0.4),
            "the producer resends",
            (lambda: self.req("seq 17", WHITE, to_log=17, log_text="pay-17"), 1.2),
            (lambda: self.req("seq 18", GOLD_M, to_log=18, log_text="pay-18"), 1.2),
            "in send order",
            (lambda: [*self.lstate("producer 5: next 19", GREEN_M), *self.cap("17, then 18: once each, in send order", GREEN_M)], 0.6),
        ])

        # ---------------- scene 8: requirements, the trap, the limit ----------------
        self.steps("It needs three settings: acks=all, retries above zero, and at most five requests in flight. "
                   "Five is exactly how many batches the leader can recognise.", [
            (lambda: self.cap("needs: acks=all,  retries > 0,  at most 5 in flight", WHITE), 0.6),
            "Five is exactly",
            (lambda: [*self.cap("5: the batches the leader remembers per producer"), glow(lbox, BLUE_M, 1.03)], 0.6),
        ])
        self.steps("And here's the trap. Set acks=1 for speed, without mentioning idempotence, and the producer quietly turns it off. "
                   "No warning. Polite of it, and terrible manners for a payment.", [
            (lambda: [*self.cap("acks=1 alone: idempotence silently off", RED_M), *self.ptext("producer", "acks=1", "idempotence off?!", RED_M)], 0.7),
        ])
        self.steps("So set enable.idempotence to true by name. Then the same conflict stops the producer at start-up, "
                   "where you'll see it.", [
            (lambda: [*self.cap("enable.idempotence=true: a conflict fails at start-up, loudly", GREEN_M),
                      *self.ptext("producer", "producer id 5", "enable.idempotence=true", GREEN_M)], 0.7),
        ])
        self.steps("And know where it stops. It covers this producer's own retries. If your code catches a TimeoutException and "
                   "calls send() again, that's a new record, with a new number. That's you, tapping Retry in the tunnel.", [
            (lambda: self.cap("it covers the producer's own retries, nothing more"), 0.5),
            "calls send() again",
            (lambda: self.req("id 5 | seq 19", PURPLE_M, to_log=19, log_text="again?"), 1.3),
            "That's you",
            (lambda: [*self.cap("your own second send: a new number, a new record", PURPLE_M), *self.lstate("producer 5: next 20", GREEN_M)], 0.5),
        ])
        self.steps("A restarted program gets a new producer id, too. Copies across those lines need the payment's own "
                   "idempotency key, checked by the consumer.", [
                        "A restarted",
            (lambda: self.ptext("producer", "producer id 6 (restarted)"), 0.6),
            "the payment's own",
            (lambda: self.cap("beyond that: the payment's own idempotency key, checked by the consumer", YELLOW_M), 0.5),
        ])

        # ---------------- scene 9: the code ----------------
        diagram = VGroup(pbox, lbox, a_req, a_ans, cells, offs, *self.lab.values())
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, it's two lines in the producer's settings. Turn idempotence on by name, and keep acks at all.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "Turn idempotence",
            (lambda: hl((2,), YELLOW_M), 1.1),
            "keep acks",
            (lambda: hl((3,), GOLD_M), 1.1),
        ], after=0.8)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So why did your friend get two copies? Your phone retried a message that had already arrived. "
                   "With a name and a number on every message, the receiver spots the copy.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: [*self.clear_log(), *self.ptext("producer", "producer id 5"), *self.ltext("leader", "adds to the log", "producer 5: next 17", GREEN_M),
                      *self.write(14, "pay-14"), *self.write(15, "pay-15"), *self.write(16, "pay-16", YELLOW_M)], 0.7),
            "With a name",
            (lambda: self.req("id 5 | seq 16", YELLOW_M), 1.0),
            (lambda: self.ans("offset 16", GREEN_M), 1.0),
        ])
        self.steps("Retries are safe only when the receiver can recognise them. Turn idempotence on by name.", [
            (lambda: self.cap("retries are safe only when the receiver can recognise them", YELLOW_M, 28), 0.6),
        ], after=0.6)
        self.steps("One quick check. Your code catches a TimeoutException for pay-20 and sends it again. Idempotence is on. "
                   "Can pay-20 end up in the log twice? Pause and think.", [
            (lambda: [*self.uncap(), *self.clear_log(), *self.ltext("leader", "adds to the log", "producer 5: next 20", GREEN_M)], 0.5),
            "catches a",
            (lambda: self.req("pay-20 | seq 20", WHITE, to_log=14, log_text="pay-20"), 1.2),
            (lambda: self.ans("offset", GREEN_M, lost=True), 0.9),
            "sends it again",
            (lambda: self.pstate("TimeoutException", RED_M), 0.4),
            "Pause and think",
            (lambda: self.cap("twice, or once? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. Your second send gets a new sequence number, 21, so the leader sees a new record. "
                   "Only the payment's own idempotency key can catch that one.", [
            (lambda: self.uncap(), 0.3),
            (lambda: self.req("pay-20 | seq 21", PURPLE_M, to_log=15, log_text="pay-20"), 1.3),
            "Only the payment's",
            (lambda: [*self.cap("a new send is a new number: only the app's own key catches it", YELLOW_M, 26),
                      *self.lstate("producer 5: next 22", GREEN_M)], 0.6),
        ])
        self.wait(2.0)
