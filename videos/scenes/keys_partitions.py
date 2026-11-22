from sfz import *

SAY.insert(0, (r"\b[Mm]urmur2\b", "murmur two"))
SAY.insert(0, (r"\bacct-(\d+)\b", r"account \1"))
SAY.insert(0, (r"\bcard-1\b", "card one"))
SAY.insert(0, (r"\bMath.abs\b", "math dot abbs"))
SAY.insert(0, (r"\blibrdkafka\b", "lib R D kafka"))
SAY.insert(0, (r"\bCRC32\b", "C R C thirty-two"))
SAY.insert(0, (r"\b32-bit\b", "thirty-two bit"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
APP_X, APP_W, APP_H = -5.0, 2.7, 1.3
APP_Y = [1.3, -0.4]                                   # the app, and later a second copy
LN_X0, LN_X1 = 0.6, 5.4                               # the six partitions (pigeonholes)
LN_Y = [2.5 - 0.66 * i for i in range(8)]
LN_H = 0.52
SLOT_X = [0.95 + 1.5 * k for k in range(3)]
RD_X = 6.05
PIPE_Y, PIPE_LAB_Y, BAR_Y, CAP_Y = -1.75, -2.3, -2.78, -3.27
PW = [1.7, 1.6, 2.45, 2.35, 1.9]
PGAP = 0.55
_x = -(sum(PW) + PGAP * 4) / 2
PX = []
for w in PW:
    PX.append(_x + w / 2)
    _x += w + PGAP
PLAB = ["the key", "1. its bytes", "2. murmur2", "3. clear the sign bit", "4. remainder"]


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
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def rbox(w, h, color, c):
    return RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)


def app_box(k, sub="producer inside"):
    c = np.array([APP_X, APP_Y[k], 0])
    r = rbox(APP_W, APP_H, GOLD_M, c)
    return VGroup(r, T("payments app", 24).move_to(c + 0.22 * UP), T(sub, 17, GOLD_M).move_to(c + 0.27 * DOWN))


def lane(i, color=BLUE_M):
    y = LN_Y[i]
    r = Rectangle(width=LN_X1 - LN_X0, height=LN_H, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.1), 1)
    r.move_to([(LN_X0 + LN_X1) / 2, y, 0])
    return VGroup(r, T(str(i), 22, GREY_B).move_to([LN_X0 - 0.3, y, 0]))


def rec(text, color=WHITE, w=None):
    t = M(text, 17, color)
    r = RoundedRectangle(corner_radius=0.08, width=w or t.width + 0.3, height=0.38, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).set_z_index(4)


def slot(i, k, m):
    return np.array([SLOT_X[k] + m.width / 2, LN_Y[i], 0])


def at(i, x0, m):
    return np.array([x0 + m.width / 2, LN_Y[i], 0])


def stage(k, text, color=WHITE):
    t = M(text, 20, color)
    r = RoundedRectangle(corner_radius=0.1, width=PW[k], height=0.5, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.12), 1)
    r.move_to([PX[k], PIPE_Y, 0])
    return VGroup(r, fit(t, PW[k] - 0.2).move_to(r))


def plab(k, text=None, color=GREY_B):
    return fit(T(text or PLAB[k], 17, color), PW[k] + 0.4).move_to([PX[k], PIPE_LAB_Y, 0])


def parrow(k):
    x0 = PX[k] + PW[k] / 2 + 0.06
    return Arrow([x0, PIPE_Y, 0], [x0 + PGAP - 0.12, PIPE_Y, 0], buff=0, stroke_width=3, color=GREY_B,
                 max_tip_length_to_length_ratio=0.35)


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.5, height=3.6, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.55, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 2.0)
    rows = VGroup()
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * M("x" * 40, 16).width / 40
        rows.add(left_at(M(s.strip() if s.strip() else " ", 16, col), x - 3.0 + ind, 1.45 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["// the account id is the key",
        "var record = new ProducerRecord<>(",
        "    \"payments\", \"acct-17\", payment);",
        "producer.send(record);   // partition 2",
        "// the same sum, by hand",
        "int p = Utils.toPositive(",
        "    Utils.murmur2(keyBytes)) % 6;"]
KOTLIN = ["// the account id is the key",
          "val record = ProducerRecord(",
          "    \"payments\", \"acct-17\", payment)",
          "producer.send(record)    // partition 2",
          "// the same sum, by hand",
          "val p = Utils.toPositive(",
          "    Utils.murmur2(keyBytes)) % 6"]


class KeysPartitions(Base):
    """msg-05, section 0. A refund shows up before its coffee payment. Kafka's payments topic is six logs side by side;
    the producer, inside the app, picks one for each record. Round robin scatters acct-42's payment and refund over two
    partitions and two readers. The post room: clerks work out the pigeonhole from the account number with the same sum
    (key, partition, hash). The default partitioner in four steps for acct-17: 7 bytes, murmur2 -1871546916, clear the
    sign bit 275936732, % 6 = 2. acct-42 lands both records in 3. Predict acct-18 (212957696, partition 2 by luck).
    Break Math.abs (partition 0). Guardrails: librdkafka's CRC32, growing 6 to 8 moves acct-1 from 2 to 6. Code in Java
    and Kotlin, the moral, a check on card-1."""

    def pipe(self, k, text, color=WHITE, lab=None, lab_color=GREY_B):
        return [*self.put(f"st{k}", stage(k, text, color)), *self.put(f"pl{k}", plab(k, lab, lab_color))]

    def pipe_clear(self):
        return [*self.drop(*[f"st{k}" for k in range(5)], *[f"pl{k}" for k in range(5)]),
                *[FadeOut(a) for a in self.parrows if a in self.mobjects]]

    def new_arrows(self):
        self.parrows = [parrow(k) for k in range(4)]
        return self.parrows

    def send(self, m, i, k=None):
        """A record leaves the app and drops in at the end of partition i (a log adds at its end)."""
        x0 = self.occ.get(i, LN_X0 + 0.2)
        self.occ[i] = x0 + m.width + 0.15
        return [m.animate.move_to(at(i, x0, m))]

    def empty(self, *lanes_):
        for i in lanes_:
            self.occ.pop(i, None)

    def construct(self):
        self.capm = None
        self.lab, self.occ = {}, {}
        self.title_card("Which box gets the payment?", "keys, partitions, and the order you keep")

        # ---------------- scene 1: the refund before the payment ----------------
        e1 = VGroup(T("1", 22, GREY_B), rec("coffee   paid", WHITE, 3.6)).arrange(RIGHT, buff=0.3)
        e2 = VGroup(T("2", 22, GREY_B), rec("refund   a minute later", GOLD_M, 3.6)).arrange(RIGHT, buff=0.3)
        sent = VGroup(T("what happened", 22, GREY_B), e1, e2).arrange(DOWN, buff=0.35, aligned_edge=LEFT).move_to([-3.6, 0.4, 0])
        bank = rbox(4.2, 2.9, WHITE, [3.3, 0.4, 0]).set_fill(BLACK, 1)
        bank_t = T("your bank's app, that evening", 20, GREY_B).move_to([3.3, 1.45, 0])
        b1 = rec("refund   +", GOLD_M, 3.0).move_to([3.3, 0.65, 0])
        b2 = rec("coffee   -", WHITE, 3.0).move_to([3.3, -0.05, 0])
        self.steps("You pay for a coffee. A minute later you ask for a refund, because the order was wrong.", [
            (lambda: [FadeIn(sent[0]), FadeIn(e1, shift=0.1 * RIGHT)], 0.6),
            "A minute later",
            (lambda: [FadeIn(e2, shift=0.1 * RIGHT)], 0.6),
        ])
        self.steps("That evening, your bank's app lists the refund first. For a moment, it looks as if the café paid you.", [
            (lambda: [FadeIn(bank), FadeIn(bank_t)], 0.6),
            "lists the refund first",
            (lambda: [FadeIn(b1, shift=0.1 * DOWN)], 0.4),
            (lambda: [FadeIn(b2, shift=0.1 * DOWN)], 0.4),
            "For a moment",
            (lambda: [bank.animate.set_stroke(RED_M)], 0.5),
        ])
        self.steps("In a program that keeps account balances, it's worse: a refund for a payment it has never seen. "
                   "How did the order get swapped? Hold that question.", [
            "a refund for a payment",
            (lambda: self.cap("a refund for a payment it has never seen", RED_M), 0.5),
            "How did",
            (lambda: self.cap("how did the order get swapped?", WHITE), 0.5),
        ])

        # ---------------- scene 2: the setup ----------------
        app = app_box(0)
        lanes = VGroup(*[lane(i) for i in range(6)])
        ttl = T("the payments topic", 24).move_to([(LN_X0 + LN_X1) / 2, 3.12, 0])
        self.steps("Here's the setup. The payments app sends every payment and every refund to Kafka. "
                   "Kafka is a program that keeps logs of messages and lets other programs read them.", [
            (lambda: [FadeOut(VGroup(sent, bank, bank_t, b1, b2)), *self.uncap()], 0.6),
            "The payments app",
            (lambda: [FadeIn(app, shift=0.1 * RIGHT)], 0.6),
            "Kafka is",
            (lambda: self.cap("Kafka: a program that keeps logs of messages, for other programs to read"), 0.5),
        ])
        r0 = rec("acct-17 | payment").move_to(app.get_center() + 1.15 * DOWN)
        self.steps("Each message is a record: a key, a value, which is the payment itself, and a few extra fields.", [
            (lambda: [FadeIn(r0, shift=0.1 * DOWN), *self.cap("a record: a key, a value, and a few extra fields")], 0.6),
            "a key",
            (lambda: [Indicate(r0[1][:7], color=YELLOW_M)], 0.6),
            "a value",
            (lambda: [Indicate(r0[1][8:], color=YELLOW_M)], 0.6),
        ])
        self.steps("A log only ever adds at its end, so a log keeps its order. That's true. But the payments topic, "
                   "Kafka's name for one stream of records, is six logs side by side. They're called partitions, numbered 0 to 5.", [
            (lambda: [FadeIn(lanes[0]), *self.cap("a log only adds at its end, so a log keeps its order")], 0.7),
            "That's true",
            (lambda: [glow(lanes[0][0], BLUE_M, 1.02)], 0.6),
            "But the payments topic",
            (lambda: [FadeIn(ttl), LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in lanes[1:]], lag_ratio=0.2)], 1.2),
            "called partitions",
            (lambda: self.cap("six logs side by side: partitions 0 to 5", BLUE_M), 0.5),
        ])
        self.steps("When the app sends a record, one of the six has to get it. And the one who chooses is the producer: "
                   "the part of the Kafka library that runs inside the app.", [
            (lambda: self.cap("one of the six has to get it"), 0.5),
            "the producer",
            (lambda: [glow(app[0], GOLD_M, 1.04), Indicate(app[2], color=GOLD_M), *self.cap("the producer chooses, inside the app", GOLD_M)], 0.8),
        ])

        # ---------------- scene 3: round robin, and where it hurts ----------------
        nums = [rec(str(i + 1), GREY_B, 0.42).move_to(app.get_center()) for i in range(6)]
        self.steps("So what rule should the producer use? The simplest is taking turns, called round robin. "
                   "Record one to partition 0, record two to partition 1, and so on. The load spreads perfectly.", [
            (lambda: [FadeOut(r0), *self.cap("taking turns: round robin")], 0.5),
            "Record one",
            *[(lambda i=i: [Succession(FadeIn(nums[i], run_time=0.05), nums[i].animate(run_time=0.5).move_to(slot(i, 0, nums[i])))], 0.55)
              for i in range(6)],
            "The load spreads",
            (lambda: self.cap("the load spreads perfectly", GREEN_M), 0.4),
        ])
        pay = rec("acct-42 pay")
        ref = rec("acct-42 refund", GOLD_M)
        first = T("handled 1st", 16, RED_M).move_to([4.55, LN_Y[1], 0])
        second = T("handled 2nd", 16, GREY_B).move_to([4.55, LN_Y[0], 0])
        readers = [VGroup(rbox(1.0, 0.44, GREY_B, [RD_X, LN_Y[i], 0]), T("reader", 16).move_to([RD_X, LN_Y[i], 0])) for i in (0, 1)]
        self.steps("Now watch account 42. Its payment lands in partition 0. Its refund lands in partition 1.", [
            (lambda: [*[FadeOut(n) for n in nums], *self.uncap()], 0.5),
            "Its payment",
            (lambda: [FadeIn(pay.move_to(app.get_center()))], 0.15),
            (lambda: self.send(pay, 0), 0.7),
            "Its refund",
            (lambda: [FadeIn(ref.move_to(app.get_center()))], 0.15),
            (lambda: self.send(ref, 1), 0.7),
        ])
        self.steps("Each partition has its own reader, and each reads at its own pace. Reader 1 is quick. "
                   "So the balance program gets the refund first, for a payment it has never heard of.", [
            (lambda: [FadeIn(readers[0]), FadeIn(readers[1])], 0.6),
            "Reader 1 is quick",
            (lambda: [glow(readers[1][0], RED_M, 1.08), ref.animate.set_opacity(0.35), FadeIn(first)], 0.8),
            "So the balance",
            (lambda: [*self.cap("refund first: a payment it has never heard of", RED_M)], 0.6),
            "never heard of",
            (lambda: [glow(readers[0][0], GREY_B, 1.08), pay.animate.set_opacity(0.35), FadeIn(second)], 0.9),
        ])
        self.steps("That's a thank-you note for a present nobody has posted yet. So the point really is: "
                   "taking turns spreads the records, and scatters each account.", [
            "So the point",
            (lambda: self.cap("taking turns spreads the records, and scatters each account", WHITE), 0.5),
        ])
        app2 = app_box(1)
        self.steps("What we want is one rule: every record of one account goes to the same partition. And the app runs as "
                   "several copies on several computers, so the rule has to work without them asking each other.", [
            (lambda: [FadeOut(pay), FadeOut(ref), FadeOut(readers[0]), FadeOut(readers[1]), FadeOut(first), FadeOut(second),
                      *self.cap("the wish: one account, one partition", YELLOW_M)], 0.6),
            "several copies",
            (lambda: [FadeIn(app2, shift=0.1 * DOWN)], 0.6),
            "without them asking",
            (lambda: self.cap("and no copy asks another", YELLOW_M), 0.5),
        ])

        # ---------------- scene 4: the post room ----------------
        clerk = [T("clerk", 18, GOLD_M).next_to(a[0], UP, buff=0.1) for a in (app, app2)]
        holes = T("pigeonholes", 20, BLUE_M).next_to(ttl, LEFT, buff=0.35)
        self.steps("A post room solves this exact problem. Picture a wall of pigeonholes, little open boxes where letters "
                   "wait to be collected.", [
            (lambda: self.uncap(), 0.3),
            "a wall of pigeonholes",
            (lambda: [LaggedStart(*[glow(l[0], BLUE_M, 1.02) for l in lanes], lag_ratio=0.15)], 1.3),
        ])
        letters = [rec("acct-42 pay"), rec("acct-42 refund", GOLD_M)]
        self.empty(0, 1)
        self.steps("Every clerk works out the box from the account number on the envelope, with the same sum. "
                   "Letters for one account land in one box, stacked in the order they came. No clerk asks another.", [
            (lambda: [FadeIn(clerk[0]), FadeIn(clerk[1])], 0.5),
            "with the same sum",
            (lambda: [FadeIn(letters[0].move_to(app.get_center()))], 0.15),
            (lambda: self.send(letters[0], 3), 0.7),
            (lambda: [FadeIn(letters[1].move_to(app2.get_center()))], 0.15),
            (lambda: self.send(letters[1], 3), 0.7),
            "stacked in the order",
            (lambda: [glow(lanes[3][0], BLUE_M, 1.02)], 0.7),
        ])
        self.steps("Let's map it. The account number is the record's key. The box is the partition. "
                   "The clerks are the copies of the app, each with a producer. And the sum is called a hash.", [
            "The account number",
            (lambda: [*self.cap("the account number on the envelope: the key", WHITE), Indicate(letters[0][1][:7], color=YELLOW_M)], 0.6),
            "The box",
            (lambda: [*self.cap("a box: a partition", BLUE_M), glow(lanes[3][0], BLUE_M, 1.02)], 0.6),
            "The clerks",
            (lambda: [*self.cap("a clerk: a copy of the app, with its producer", GOLD_M), glow(app[0], GOLD_M, 1.04), glow(app2[0], GOLD_M, 1.04)], 0.7),
            "the sum",
            (lambda: self.cap("the clerk's sum: a hash", YELLOW_M), 0.5),
        ])

        # ---------------- scene 5: the producer's sum, in four steps ----------------
        self.parrows = [parrow(k) for k in range(4)]
        self.steps("A hash function turns any bytes into a number. The same bytes always give the same number. "
                   "Let's follow account 17 through the producer's sum, in four steps.", [
            (lambda: [FadeOut(letters[0]), FadeOut(letters[1]), FadeOut(clerk[0]), FadeOut(clerk[1]),
                      *self.cap("a hash function: any bytes in, a number out. same bytes, same number")], 0.6),
            "Let's follow",
            (lambda: [*self.uncap(), *self.pipe(0, "acct-17", YELLOW_M)], 0.6),
        ])
        self.steps("One: turn the key into bytes. The text acct-17 is seven bytes.", [
            "turn the key",
            (lambda: [GrowArrow(self.parrows[0]), *self.pipe(1, "7 bytes")], 0.6),
        ])
        self.steps("Two: hash the bytes with murmur2, a fast hash function. Out comes a 32-bit number, and here it's negative.", [
            "hash the bytes",
            (lambda: [GrowArrow(self.parrows[1]), *self.pipe(2, "-1871546916")], 0.6),
            "here it's negative",
            (lambda: [Indicate(self.lab["st2"][1][0], color=RED_M, scale_factor=1.6)], 0.7),
        ])
        self.steps("Three: clear the sign bit, the leftmost bit, which says whether a number is negative. "
                   "A partition number can't be negative, so the producer keeps the other 31 bits.", [
            "clear the sign bit",
            (lambda: [GrowArrow(self.parrows[2]), *self.pipe(3, "275936732")], 0.6),
            "keeps the other",
            (lambda: self.cap("-1871546916  becomes  275936732   (2^31 minus 1871546916)"), 0.5),
        ])
        r17a, r17b = rec("acct-17"), rec("acct-17")
        self.lab["r17a"], self.lab["r17b"] = r17a, r17b
        self.steps("Four: divide by the number of partitions and keep the remainder. That's 2. "
                   "So account 17 goes to partition 2, from every copy of the app, every time.", [
            (lambda: [*self.uncap(), GrowArrow(self.parrows[3]), *self.pipe(4, "% 6 = 2", GREEN_M)], 0.6),
            "So account 17",
            (lambda: [FadeIn(r17a.move_to(app.get_center()))], 0.15),
            (lambda: self.send(r17a, 2), 0.7),
            "from every copy",
            (lambda: [FadeIn(r17b.move_to(app2.get_center()))], 0.15),
            (lambda: self.send(r17b, 2), 0.7),
        ])
        self.steps("This is the default partitioner, the code in the Java client library that picks the partition.", [
            (lambda: self.cap("the default partitioner: the producer's four-step sum", GOLD_M), 0.5),
        ])
        p42 = rec("acct-42 pay")
        self.empty(3)
        f42 = rec("acct-42 refund", GOLD_M)
        self.steps("And account 42? Its hash leaves a remainder of 3. Its payment and its refund both land in partition 3, "
                   "in the order they were sent.", [
            (lambda: [*self.uncap(), *self.pipe(0, "acct-42", YELLOW_M), *self.pipe(2, "-1294421753"), *self.pipe(3, "853061895"),
                      *self.pipe(4, "% 6 = 3", GREEN_M)], 0.9),
            "Its payment",
            (lambda: [FadeIn(p42.move_to(app.get_center()))], 0.15),
            (lambda: self.send(p42, 3), 0.7),
            "and its refund",
            (lambda: [FadeIn(f42.move_to(app2.get_center()))], 0.15),
            (lambda: self.send(f42, 3), 0.7),
            "in the order",
            (lambda: [glow(lanes[3][0], GREEN_M, 1.02), *self.cap("one account, one partition, in send order", GREEN_M)], 0.8),
        ])

        # ---------------- scene 6: predict a neighbour ----------------
        self.steps("Now a guess. acct-18 differs from acct-17 by one character. Will its hash be close to 17's? Pause and guess.", [
            (lambda: [*self.uncap(), FadeOut(p42), FadeOut(f42), *self.pipe(0, "acct-18", YELLOW_M), *self.pipe(2, "-1871546916"),
                      *self.pipe(3, "?", GREY_B), *self.pipe(4, "?", GREY_B)], 0.8),
            "Will its hash",
            (lambda: [*self.pipe(2, "close to 17's?", YELLOW_M)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Not even close. A completely different number. That's the job of a good hash: keys that look alike "
                   "spread out evenly.", [
            (lambda: [*self.uncap(), *self.pipe(2, "212957696"), *self.pipe(3, "212957696")], 0.7),
            "keys that look alike",
            (lambda: self.cap("acct-17: -1871546916      acct-18: 212957696"), 0.5),
        ])
        r18 = rec("acct-18")
        self.steps("And it still lands in partition 2, by luck. With six partitions, any two keys share one about one time in six.", [
            (lambda: [*self.pipe(4, "% 6 = 2", GREEN_M), FadeIn(r18.move_to(app.get_center()))], 0.4),
            (lambda: self.send(r18, 2), 0.7),
            "by luck",
            (lambda: self.cap("two keys share a partition about one time in six"), 0.5),
        ])

        # ---------------- scene 7: break the shortcut ----------------
        self.steps("Here's a trap many of us would walk into. Step three looks fussy. Why not make the number positive the "
                   "usual way, with Math.abs?", [
            (lambda: [*self.uncap(), FadeOut(r18), *self.pipe(0, "acct-17", YELLOW_M), *self.pipe(2, "-1871546916"),
                      *self.pipe(3, "275936732"), *self.pipe(4, "% 6 = 2", GREEN_M)], 0.8),
            "Step three",
            (lambda: [glow(self.lab["st3"][0], YELLOW_M, 1.05)], 0.7),
            "the usual way",
            (lambda: self.cap("the shortcut: Math.abs", PURPLE_M), 0.5),
        ])
        self.steps("Let's try it. Math.abs of that negative number, divided by 6, leaves 0. Partition 0. The real producer said 2.", [
            "Let's try it",
            (lambda: self.pipe(3, "1871546916", PURPLE_M, "3. Math.abs", PURPLE_M), 0.6),
            "leaves 0",
            (lambda: self.pipe(4, "% 6 = 0", RED_M), 0.5),
            "The real producer",
            (lambda: [Indicate(self.lab["r17a"], color=GREEN_M), *self.cap("Math.abs: partition 0.   the producer: partition 2", RED_M)], 0.8),
        ])
        self.steps("Clearing the sign bit isn't the same as dropping the minus sign. So a test that predicts partitions with "
                   "Math.abs gets most negative hashes wrong.", [
            "Clearing the sign bit",
            (lambda: self.pipe(3, "275936732", WHITE), 0.6),
            (lambda: self.pipe(4, "% 6 = 2", GREEN_M), 0.5),
            "So a test",
            (lambda: self.cap("clearing the sign bit is not dropping the minus sign", WHITE), 0.5),
        ])
        self.steps("Well... that's one very confident clerk, standing at the wrong box.", [
            0.3,
            (lambda: [Wiggle(app[0], scale_value=1.05, rotation_angle=0.02 * TAU)], 0.9),
        ], after=0.4)

        # ---------------- scene 8: guardrails ----------------
        go = T("Go app, librdkafka", 17, PURPLE_M).move_to(app2.get_center() + 0.27 * DOWN)
        self.steps("Two warnings. First, the sum lives in each client library, not in Kafka. Programs in Python or Go often use "
                   "librdkafka, a library written in C, and by default it hashes with a different function, CRC32.", [
            (lambda: [*self.uncap(), *self.cap("1. the sum lives in each client library, not in Kafka", WHITE)], 0.5),
            "Programs in Python",
            (lambda: [Succession(FadeOut(app2[2], run_time=0.3), FadeIn(go, run_time=0.4)), app2[0].animate.set_stroke(PURPLE_M)], 0.7),
            "a different function",
            (lambda: [*self.pipe(2, "CRC32 ...", PURPLE_M, "2. CRC32, by default", PURPLE_M), *self.pipe(3, "?", GREY_B),
                      *self.pipe(4, "?", GREY_B)], 0.6),
        ])
        q = rec("acct-17 ?", PURPLE_M)
        self.steps("That's a clerk with a different sum. Same key, maybe a different box, unless that program is set to use murmur2 too.", [
            (lambda: [FadeIn(q.move_to(app2.get_center()))], 0.2),
            (lambda: [q.animate.move_to([-1.4, LN_Y[4], 0])], 0.7),
            "unless that program",
            (lambda: self.cap("librdkafka: set partitioner=murmur2_random to match Java", PURPLE_M), 0.5),
        ])
        extra = VGroup(lane(6, TEAL_M), lane(7, TEAL_M))
        a1old = rec("acct-1 old")
        self.empty(2, 6)
        a1new = rec("acct-1 new", TEAL_M)
        self.steps("Second, the sum divides by the number of partitions. Grow the topic from 6 to 8, and acct-1 moves from "
                   "partition 2 to partition 6. Its old records stay behind in 2.", [
            (lambda: [FadeOut(q), *self.pipe_clear(), *self.cap("2. the sum divides by the partition count", WHITE),
                      FadeOut(self.lab.pop("r17a")), FadeOut(self.lab.pop("r17b")), Succession(FadeOut(go, run_time=0.3), FadeIn(app2[2], run_time=0.4)),
                      app2[0].animate.set_stroke(GOLD_M)], 0.7),
            (lambda: [FadeIn(a1old.move_to(app.get_center()))], 0.15),
            (lambda: self.send(a1old, 2), 0.6),
            "Grow the topic",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in extra], lag_ratio=0.3)], 0.8),
            "acct-1 moves",
            (lambda: [FadeIn(a1new.move_to(app.get_center())), *self.cap("294059390 % 6 = 2      294059390 % 8 = 6", TEAL_M)], 0.2),
            (lambda: self.send(a1new, 6), 0.7),
            "Its old records",
            (lambda: [glow(a1old[0], RED_M, 1.08)], 0.7),
        ])
        self.steps("About three keys in four move. So choose the partition count once, with room to grow.", [
            (lambda: self.cap("about three keys in four move", RED_M), 0.5),
            "So choose",
            (lambda: self.cap("choose the partition count once, with room to grow", YELLOW_M), 0.5),
        ])

        # ---------------- scene 9: the code ----------------
        diagram = VGroup(app, app2, lanes, ttl, extra, a1old, a1new)
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, all you choose is the key. Pass the account id as the record's key, and the producer "
                   "does the four steps for you.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "Pass the account id",
            (lambda: hl((1, 2), YELLOW_M), 1.3),
            "the four steps",
            (lambda: hl((5, 6), GOLD_M), 1.3),
        ], after=0.8)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So how did the refund get ahead of its payment? They went into two different logs, and nothing keeps order "
                   "across logs. One key per account puts both in one partition, and inside one partition, order holds.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: [FadeOut(extra), FadeOut(a1old), FadeOut(a1new)], 0.5),
            "two different logs",
            (lambda: [FadeIn(pay.set_opacity(1).move_to(at(0, LN_X0 + 0.2, pay))), FadeIn(ref.set_opacity(1).move_to(at(1, LN_X0 + 0.2, ref)))], 0.6),
            "One key per account",
            (lambda: [pay.animate.move_to(at(3, LN_X0 + 0.2, pay)), ref.animate.move_to(at(3, LN_X0 + 0.35 + pay.width, ref))], 0.9),
            "order holds",
            (lambda: [glow(lanes[3][0], GREEN_M, 1.02), *self.cap("one key per account: one partition, and order inside it", GREEN_M)], 0.8),
        ])
        self.stamp("poster")
        self.steps("Same key, same sum, same box. Choose the key for the order you need.", [
            (lambda: self.cap("same key, same sum, same box", YELLOW_M, 30), 0.6),
        ], after=0.6)
        self.steps("One quick check. card-1 hashes to a positive number. Would a test that uses Math.abs pick the right "
                   "partition for it? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(pay), FadeOut(ref), *self.pipe(0, "card-1", YELLOW_M), GrowArrow(self.new_arrows()[0]),
                      *self.pipe(1, "6 bytes"), GrowArrow(self.parrows[1]), *self.pipe(2, "830907359")], 0.9),
            "Would a test",
            (lambda: [GrowArrow(self.parrows[2]), *self.pipe(3, "?", PURPLE_M, "3. Math.abs", PURPLE_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("right partition, or wrong? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. For a positive number, Math.abs changes nothing, so both give partition 5. "
                   "It only goes wrong when the hash is negative.", [
            (lambda: [*self.uncap(), *self.pipe(3, "830907359", PURPLE_M, "3. Math.abs", PURPLE_M)], 0.5),
            (lambda: [GrowArrow(self.parrows[3]), *self.pipe(4, "% 6 = 5", GREEN_M)], 0.5),
            "It only goes wrong",
            (lambda: self.cap("Math.abs goes wrong only for a negative hash", YELLOW_M, 28), 0.5),
        ])
        self.wait(2.0)
