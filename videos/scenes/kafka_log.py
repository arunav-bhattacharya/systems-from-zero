from sfz import *

# Amounts are said the way people say them; captions keep the digits.
SAY.insert(0, (r"\b(\d+)\.50\b", r"\1 fifty"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bacct-(\d+)\b", r"account \1"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
LOG_Y = 1.3                                   # the row of records
CW, CH, PITCH = 1.9, 1.0, 2.08
CXS = [-5.2 + PITCH * i for i in range(6)]    # record i sits at CXS[i]; 5 is the end
TAG_Y = {"ledger": 0.3, "fraud": -0.45, "report": -1.2}
TAG_C = {"ledger": GOLD_M, "fraud": GREEN_M, "report": PURPLE_M}
TAG_N = {"ledger": "ledger", "fraud": "fraud check", "report": "weekly report"}
PROD = np.array([CXS[4], 2.95, 0])
CAP_Y, BAR_Y = -3.25, -2.7
RECS = [("acct-17", "auth 40.00"), ("acct-42", "auth 12.50"), ("acct-17", "capture 40.00"),
        ("acct-99", "auth 300.00"), ("acct-42", "refund 12.50")]


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


def record(i):
    key, val = RECS[i]
    c = GOLD_M if val.startswith("refund") else (GREEN_M if val.startswith("capture") else BLUE_M)
    r = RoundedRectangle(corner_radius=0.12, width=CW, height=CH, stroke_color=c, stroke_width=2.5).set_fill(fillc(c, 0.2), 1)
    r.move_to([CXS[i], LOG_Y, 0])
    body = VGroup(M(key, 18), fit(T(val, 16, GREY_A), 1.25)).arrange(DOWN, buff=0.1).move_to([CXS[i] + 0.24, LOG_Y, 0])
    return VGroup(r, body)


def offset(i):
    return M(str(i), 26, YELLOW_M).move_to([CXS[i] - 0.66, LOG_Y, 0])


def end_slot(i):
    return DashedVMobject(RoundedRectangle(corner_radius=0.12, width=CW, height=CH, stroke_color=GREY_C, stroke_width=2)
                          .move_to([CXS[i], LOG_Y, 0]), num_dashes=36)


def tag(who, n, x=None):
    """A reader's bookmark: a small flag under the record it will read next, carrying the number."""
    c = TAG_C[who]
    t = T(TAG_N[who] if n is None else f"{TAG_N[who]}: {n}", 18)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.35, height=0.44, stroke_color=c, stroke_width=2.5).set_fill(fillc(c, 0.3), 1)
    x = (CXS[n] if n is not None else CXS[0]) if x is None else x
    y = TAG_Y[who]
    tip = Triangle(stroke_width=0).set_fill(c, 1).scale(0.09).move_to([x, y + 0.3, 0])
    return VGroup(r.move_to([x, y, 0]), t.move_to([x, y, 0]), tip)


def phone(x, stop, side):
    body = RoundedRectangle(corner_radius=0.25, width=2.5, height=4.2, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
    body.move_to([x, 0.1, 0])
    posts = ["aunt: a photo", "cousin: ha!", "dad: who's coming?", "aunt: another photo"]
    bub = VGroup()
    for k, p in enumerate(posts):
        t = T(p, 15)
        b = RoundedRectangle(corner_radius=0.12, width=t.width + 0.3, height=0.46, stroke_color=GREY_B, stroke_width=1.5).set_fill("#1a1d22", 1)
        g = VGroup(b, t.move_to(b))
        left_at(g, x - 1.05, 1.55 - 0.72 * k)
        bub.add(g)
    y = 1.55 - 0.72 * stop + 0.36
    x0, x1 = (x - 2.0, x + 1.1) if side < 0 else (x - 1.1, x + 2.0)
    lab = T("you stopped here", 18, YELLOW_M)
    lab.next_to([x0 if side < 0 else x1, y, 0], LEFT if side < 0 else RIGHT, buff=0.12)
    mark = VGroup(DashedLine([x0, y, 0], [x1, y, 0], dash_length=0.07, stroke_width=2, color=YELLOW_M), lab)
    return VGroup(body, bub, mark)


class KafkaLog(Base):
    """msg-02, section 0. The family chat: reading deletes nothing, and each phone keeps its own place. The broker's
    queue deletes a payment once it's read: four queues for four programs, nothing for a new program, no second
    reading. A log keeps every payment in a file that only grows, numbered 0, 1, 2, and each reader keeps one number.
    The fraud check reads two: only its number moves. A refund is added at the end; the weekly report starts at 0;
    a bug fix moves the ledger's number back. Where the chat breaks; the names (log, Kafka, record, producer,
    consumer, topic); retention and what not to write; the moral; a check."""

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
        return [FadeOut(self.lab.pop(k)) for k in keys if k in self.lab]

    def move_tag(self, who, n, x=None):
        """Slide a reader's bookmark to record n and change its number (n=None: a plain name tag at x)."""
        old = self.tags.get(who)
        new = tag(who, n, x)
        self.tags[who] = new
        if old is None:
            return [FadeIn(new, shift=0.15 * UP)]
        return [ReplacementTransform(old, new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.tags = {}
        self.title_card("Reading deletes nothing", "the log, and a bookmark for each reader")

        # ---------------- scene 1: the chat, and the question ----------------
        p1, p2 = phone(-1.6, 2, -1), phone(1.6, 4, 1)
        self.steps("Picture a family group chat. Your aunt posts a photo, and everyone reads it in their own time.", [
            (lambda: [FadeIn(p1[0]), FadeIn(p2[0])], 0.6),
            "Your aunt",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in p1[1]], lag_ratio=0.2),
                      LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in p2[1]], lag_ratio=0.2)], 1.4),
        ])
        self.steps("Each phone remembers where its owner stopped. And your reading deletes nothing for anyone else.", [
            (lambda: [FadeIn(p1[2]), FadeIn(p2[2])], 0.7),
            "your reading",
            (lambda: [glow(p1[1][3][0], GREY_A, 1.05), glow(p2[1][3][0], GREY_A, 1.05)], 0.9),
        ])
        self.steps("Now a payments company wants a new program to study last week's payments. With the broker from the last lesson, "
                   "it gets nothing. Why? And what would a chat do differently?", [
            "With the broker",
            (lambda: [FadeOut(p1, shift=0.2 * LEFT), FadeOut(p2, shift=0.2 * RIGHT)], 0.8),
            (lambda: self.cap("a new program wants last week's payments", WHITE), 0.5),
            "it gets nothing",
            (lambda: self.cap("from the broker: nothing", RED_M), 0.5),
        ])

        # ---------------- scene 2: the queue we know, and its cost ----------------
        recs = [record(i) for i in range(4)]
        qbox = RoundedRectangle(corner_radius=0.16, width=CXS[3] - CXS[0] + CW + 0.4, height=1.5, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        qbox.move_to([(CXS[0] + CXS[3]) / 2, LOG_Y, 0])
        self.steps("Here's the broker's queue, with four payments. The ledger reads one, says done, and the broker deletes it. "
                   "A message is used up once it's read.", [
            (lambda: [*self.uncap(), FadeIn(qbox), *self.put("head", left_at(T("the broker's queue", 22, GREY_B), qbox.get_left()[0], LOG_Y + 1.05))], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.2 * RIGHT) for r in recs], lag_ratio=0.15)], 1.0),
            "The ledger reads",
            (lambda: self.move_tag("ledger", None, CXS[0]), 0.5),
            "says done",
            (lambda: [FadeOut(recs[0], shift=0.3 * DOWN)], 0.5),
            "A message is used up",
            (lambda: [Succession(*[AnimationGroup(*self.move_tag("ledger", None, CXS[k]), FadeOut(recs[k], shift=0.3 * DOWN)) for k in (1, 2, 3)],
                                 run_time=1.6)], 1.6),
        ])
        self.steps("Letters work that way, and so do to-do lists. It's a library that shreds each book "
                   "as soon as the first reader brings it back. Very tidy shelves. A very unhappy second reader.", [
            "A very unhappy",
            (lambda: [*self.move_tag("report", None, CXS[0]), *self.cap("the weekly report: nothing left to read", RED_M)], 0.6),
            (lambda: [glow(qbox, RED_M, 1.01)], 0.8),
        ])
        self.steps("It costs three things. To feed four programs, the broker keeps four queues, with a copy of every payment in each. "
                   "A new program starts with nothing. And if a bug means yesterday's payments must be worked through again, "
                   "the queue can't give them back.", [
            (lambda: self.cap("1. four programs: four queues, four copies of every payment", RED_M), 0.5),
            "A new program",
            (lambda: [*self.cap("2. a new program starts with nothing", RED_M), glow(self.tags["report"][0], RED_M, 1.08)], 0.7),
            "And if a bug",
            (lambda: self.cap("3. no second reading", RED_M), 0.5),
        ])
        self.steps("Wouldn't it be nice if every payment stayed, and each reader kept only its own place? That's the chat.", [
            (lambda: self.cap("every payment stays; each reader keeps its own place", YELLOW_M), 0.6),
        ])

        # ---------------- scene 3: the log ----------------
        recs = [record(i) for i in range(5)]
        offs = [offset(i) for i in range(5)]
        endslot = end_slot(4)
        self.steps("So, keep every payment. The payments program adds each one to the end of a file that only grows.", [
            (lambda: [*self.uncap(), FadeOut(qbox), *[FadeOut(t) for t in self.tags.values()],
                      *self.put("head", left_at(T("the payments file: it only grows at the end", 22, GREY_B), CXS[0] - CW / 2, LOG_Y + 1.05))], 0.6),
            "adds each one",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.2 * DOWN) for r in recs[:4]], lag_ratio=0.25), Create(endslot)], 1.3),
        ])
        self.tags = {}
        self.steps("Every payment gets a number, its place in the file: 0, 1, 2, 3. The number never changes.", [
            ": 0",
            (lambda: [LaggedStart(*[FadeIn(o, scale=0.6) for o in offs[:4]], lag_ratio=0.35)], 1.6),
            "never changes",
            (lambda: [LaggedStart(*[Indicate(o, color=YELLOW_M, scale_factor=1.3) for o in offs[:4]], lag_ratio=0.1)], 0.9),
        ])
        self.steps("Each reader remembers one thing: the number of the next payment it wants. The ledger has read everything, so it's at 4. "
                   "The fraud check is slower. It's at 2.", [
            "The ledger has",
            (lambda: self.move_tag("ledger", 4), 0.6),
            "The fraud check",
            (lambda: self.move_tag("fraud", 2), 0.6),
        ])
        self.steps("Map it out. The chat is the file. Each post is a payment. And each phone's place is one number for each reader.", [
            (lambda: [*self.cap("chat = the file"), glow(self.lab["head"], GREY_A, 1.02)], 0.5),
            "Each post",
            (lambda: [*self.cap("post = payment"), LaggedStart(*[glow(r[0], GREY_A, 1.04) for r in recs[:4]], lag_ratio=0.15)], 0.8),
            "And each phone's",
            (lambda: [*self.cap("\"you stopped here\" = one number per reader"),
                      glow(self.tags["ledger"][0], GOLD_M, 1.1), glow(self.tags["fraud"][0], GREEN_M, 1.1)], 0.8),
        ])

        # ---------------- scene 4: predict, then show ----------------
        self.steps("Now the fraud check reads two payments. What changes in the file? Pause and guess.", [
            (lambda: [*self.cap("the fraud check reads 2 and 3"), glow(recs[2][0], GREEN_M, 1.05), glow(recs[3][0], GREEN_M, 1.05)], 0.9),
            "Pause and guess",
            (lambda: self.cap("what changes in the file?", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Nothing. Its number moves from 2 to 4, and that's all. The records are still there for anyone else.", [
            (lambda: self.uncap(), 0.3),
            "Its number",
            (lambda: self.move_tag("fraud", 3), 0.5),
            (lambda: self.move_tag("fraud", 4), 0.5),
            "still there",
            (lambda: [LaggedStart(*[glow(r[0], GREY_A, 1.04) for r in recs[:4]], lag_ratio=0.15)], 1.0),
        ])
        arr = Arrow(PROD + 0.4 * DOWN, [CXS[4], LOG_Y + CH / 2 + 0.05, 0], buff=0.05, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.15)
        prod = VGroup(RoundedRectangle(corner_radius=0.12, width=2.7, height=0.62, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1),
                      T("payments program", 20)).move_to(PROD + 0.2 * UP)
        prod[1].move_to(prod[0])
        self.steps("A new payment arrives. Account 42 gets a refund of 12.50. It goes at the end, as number 4. "
                   "No reader moves. Both now have one more to read.", [
            (lambda: [FadeIn(prod, shift=0.1 * DOWN), GrowArrow(arr)], 0.7),
            "It goes at the end",
            (lambda: [FadeOut(endslot), FadeIn(recs[4], shift=0.4 * DOWN), FadeIn(offs[4], scale=0.6)], 0.8),
            "No reader moves",
            (lambda: [glow(self.tags["ledger"][0], GOLD_M, 1.1), glow(self.tags["fraud"][0], GREEN_M, 1.1)], 0.8),
        ])
        self.steps("The ledger reads it, and moves to 5, the end.", [
            (lambda: [glow(recs[4][0], GOLD_M, 1.04), FadeIn(end_slot(5))], 0.6),
            "moves to 5",
            (lambda: self.move_tag("ledger", 5), 0.6),
        ])

        # ---------------- scene 5: break the wrong model ----------------
        self.steps("So, is a payment used up once it's read? The new program, the weekly report, starts at 0, "
                   "the first payment of all. Nobody else noticed.", [
            (lambda: [*self.cap("used up once it's read?", PURPLE_M), FadeOut(prod), FadeOut(arr)], 0.5),
            "The new program",
            (lambda: self.move_tag("report", 0), 0.7),
            "Nobody else",
            (lambda: [*self.cap("one file; each reader at its own pace"), glow(self.tags["ledger"][0], GOLD_M, 1.1),
                      glow(self.tags["fraud"][0], GREEN_M, 1.1)], 0.8),
        ])
        self.steps("And the bug in yesterday's sums? Fix it, move the ledger's number back, and read again. One number moved. Nothing copied.", [
            (lambda: self.cap("a second reading: move one number back"), 0.5),
            "move the ledger's",
            (lambda: self.move_tag("ledger", 0), 1.0),
            "and read again",
            *[(lambda k=k: self.move_tag("ledger", k), 0.35) for k in range(1, 6)],
        ])

        # ---------------- scene 6: where the chat breaks ----------------
        self.steps("The chat picture breaks in two places. A chat may hide old posts from a new member. A log shows them to anyone.", [
            (lambda: self.cap("where the chat picture breaks"), 0.5),
            "A log shows",
            (lambda: [*self.cap("a log shows old records to any new reader"), glow(self.tags["report"][0], PURPLE_M, 1.1)], 0.7),
        ])
        fix = VGroup(Line(recs[3][0].get_corner(UL) + [0.15, -0.15, 0], recs[3][0].get_corner(DR) + [-0.15, 0.15, 0]),
                     Line(recs[3][0].get_corner(DL) + [0.15, 0.15, 0], recs[3][0].get_corner(UR) + [-0.15, -0.15, 0])).set_stroke(RED_M, 4)
        self.steps("And a chat lets you edit or delete a post, while a log never changes a record once it's written. "
                   "To correct something, you add a new record at the end.", [
            "never changes",
            (lambda: [*self.cap("a record never changes once written", RED_M), Create(fix)], 0.7),
            (lambda: [FadeOut(fix)], 0.4),
            "you add a new",
            (lambda: [*self.cap("to correct something, add a new record"), glow(recs[4][0], GOLD_M, 1.04)], 0.7),
        ])

        # ---------------- scene 7: the names ----------------
        self.steps("This is called a log: an ordered list of records that only grows at the end. "
                   "Each reader's number is its position, the next record it will read.", [
            (lambda: [*self.cap("log: an ordered list of records that only grows at the end", YELLOW_M),
                      *self.put("head", left_at(T("a log", 22, YELLOW_M), CXS[0] - CW / 2, LOG_Y + 1.05))], 0.7),
            "Each reader's number",
            (lambda: [*self.cap("position: the next record a reader will read", YELLOW_M),
                      *[glow(t[0], TAG_C[w], 1.1) for w, t in self.tags.items()]], 0.8),
        ])
        self.steps("Kafka is a program that keeps logs like this on disk, and lets many programs read them. "
                   "In Kafka, each payment is a record. The program that adds them is a producer, and the readers are consumers.", [
            (lambda: [*self.cap("Kafka: a program that keeps logs on disk for many readers")], 0.6),
            "each payment is a record",
            (lambda: [*self.cap("record"), LaggedStart(*[glow(r[0], GREY_A, 1.04) for r in recs], lag_ratio=0.1)], 0.8),
            "The program that adds",
            (lambda: [*self.cap("producer: adds records"), FadeIn(prod), GrowArrow(arr)], 0.7),
            "the readers are",
            (lambda: [*self.cap("consumers: read them"), *[glow(t[0], TAG_C[w], 1.1) for w, t in self.tags.items()]], 0.7),
        ])
        self.steps("And the log's name, payments, is a topic. Here a topic is one log; the next lesson splits it into many.", [
            (lambda: [*self.cap("topic: the log's name, payments"),
                      *self.put("head", left_at(T("topic: payments", 22, YELLOW_M), CXS[0] - CW / 2, LOG_Y + 1.05))], 0.7),
        ])

        # ---------------- scene 8: the guardrails ----------------
        self.steps("Two cautions. If reading deletes nothing, what does? Only a limit you set on each topic: how old, or how big, it may get. "
                   "By default, Kafka keeps seven days.", [
            (lambda: [*self.cap("if reading deletes nothing, what does?", WHITE), FadeOut(prod), FadeOut(arr)], 0.6),
            "Only a limit",
            (lambda: self.cap("only a limit per topic: how old, or how big"), 0.6),
            "By default",
            (lambda: self.cap("default: seven days"), 0.5),
        ])
        self.steps("And since every record stays, readable by any program allowed to read the topic, never write anything "
                   "you aren't allowed to keep for days, such as full card numbers.", [
            (lambda: [LaggedStart(*[glow(r[0], RED_M, 1.04) for r in recs], lag_ratio=0.1)], 1.0),
            "never write",
            (lambda: self.cap("never write what you can't keep for days: no full card numbers", RED_M), 0.6),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("Leave a busy chat unread for a day, and the app still knows where you stopped. It saved one number for you.", [
            (lambda: self.cap("one number per reader", WHITE), 0.6),
        ])
        self.steps("So: one file you only add to, and a bookmark for each reader. Reading moves a bookmark. It never deletes.", [
            (lambda: [*self.cap("one file you only add to, a bookmark for each reader", YELLOW_M)], 0.6),
            "Reading moves",
            (lambda: [*self.cap("reading moves a bookmark; it never deletes", YELLOW_M, 30)], 0.6),
        ], after=0.5)
        self.steps("One quick check. The weekly report reads three payments. Where is its number now, "
                   "and what happened to the ledger's? Pause and think.", [
            (lambda: [*self.uncap(), glow(self.tags["report"][0], PURPLE_M, 1.1)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The report is at 3. The ledger hasn't moved. It's still at 5. Readers never touch each other.", [
            (lambda: self.uncap(), 0.3),
            *[(lambda k=k: self.move_tag("report", k), 0.4) for k in (1, 2, 3)],
            "The ledger hasn't",
            (lambda: [glow(self.tags["ledger"][0], GOLD_M, 1.1)], 0.8),
            "Readers never",
            (lambda: self.cap("reading moves a bookmark; it never deletes", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.wait(2.0)
