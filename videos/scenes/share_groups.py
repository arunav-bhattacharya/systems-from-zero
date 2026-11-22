from sfz import *

SAY.insert(0, (r"\bSPSO\b", "S P S O"))
SAY.insert(0, (r"\bc([123])\b", r"C \1"))
SAY.insert(0, (r"\b10:00:30\b", "ten o'clock and thirty seconds"))
SAY.insert(0, (r"\b10:00:00\b", "ten o'clock"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
REC_Y, CW, CH = 2.3, 1.1, 0.9          # the partition's eight records
CNT_Y = 1.6                            # delivery counts, under each record
SP_Y = 1.15                            # the share-partition start offset marker
MEM_Y, MEM_X = -0.95, [-4.3, 0.0, 4.3]  # the three members
ACK_Y = 0.25                           # answers, above each member
LEG_Y = -2.45                          # the legend of record states
CAP_Y, BAR_Y = -3.35, -2.98
ST = {"available": GREY_B, "acquired": GOLD_M, "acknowledged": GREEN_M, "archived": RED_M}


def rx(k):
    return -4.9 + 1.4 * k


def bx(k):
    """The boundary just before record k (where the start offset sits)."""
    return rx(k) - 0.7


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    # labels that get replaced: one key, one thing on screen
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

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.05):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])




def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.3, height=5.0, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.15, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.9, 2.25)
    rows = VGroup()
    cw = M("x" * 40, 14).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 2.9 + ind, 1.75 - 0.31 * k))
    if rows.width > 5.6:
        rows.scale(5.6 / rows.width, about_point=rows.get_corner(UL))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["// explicit mode; AcknowledgeType.* imported",
        "for (var r : consumer.poll(Duration.ofMillis(500))) {",
        "    try {",
        "        sms.send(r.value());",
        "        consumer.acknowledge(r, ACCEPT);    // done",
        "    } catch (ProviderTimeout e) {",
        "        consumer.acknowledge(r, RELEASE);   // try again",
        "    } catch (InvalidPhoneNumber e) {",
        "        consumer.acknowledge(r, REJECT);    // give up",
        "    }",
        "}",
        "consumer.commitSync();   // send the answers"]
KOTLIN = ["// explicit mode; AcknowledgeType.* imported",
          "for (r in consumer.poll(Duration.ofMillis(500))) {",
          "    val ack = try {",
          "        sms.send(r.value())",
          "        ACCEPT                     // done",
          "    } catch (e: ProviderTimeout) {",
          "        RELEASE                    // try again",
          "    } catch (e: InvalidPhoneNumber) {",
          "        REJECT                     // give up",
          "    }",
          "    consumer.acknowledge(r, ack)",
          "}",
          "consumer.commitSync()    // send the answers"]


def dot_to(a, b, color=GOLD_M, rt=0.5):
    d = Dot(radius=0.07, color=color).move_to(a).set_z_index(8)
    return Succession(FadeIn(d, run_time=0.03), d.animate(run_time=rt, rate_func=smooth).move_to(b), FadeOut(d, run_time=0.08))


class ShareGroups(Base):
    """msg-11, section 1. Six rails, six cooks, four idle cooks: a consumer group stops at one owner per partition. A share
    group lets any free cook take any slip; so what stops two cooks taking the same one? The broker keeps a state for
    every record: available, acquired (locked to one member for 30 s), acknowledged, archived. The lesson's stepper:
    eight records, members c1 to c3, two records per poll. ACCEPT, RELEASE (5 times out), predict c2's next poll (5 and 6),
    c1 freezes and its locks run out at 10:00:30 with nobody noticing, c3 finishes 0 and 1 and the start offset moves to 5,
    record 5 is archived on its fifth delivery (a dead-letter copy in 4.4). The price is order. Java and Kotlin, the
    moral, and a check (a member takes record 9 and dies)."""

    def construct(self):
        self.lab = {}
        self.title_card("A lock on every slip", "share groups: how many readers share one partition without doubling up")

        # ---------------- scene 1: the idle cooks ----------------
        rails = VGroup()
        cooks = VGroup()
        for i in range(6):
            y = 2.3 - 0.62 * i
            rails.add(Line([-4.6, y, 0], [1.2, y, 0], stroke_width=3, color=GREY_B))
            rails.add(VGroup(*[Rectangle(width=0.34, height=0.26, stroke_color=GREY_B, stroke_width=1.5).set_fill(BLACK, 1).move_to([-4.0 + 0.55 * j, y - 0.2, 0])
                               for j in range(9)]))
            cooks.add(Circle(radius=0.2, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1).move_to([-5.2, y - 0.1, 0]))
        idle = VGroup(*[Circle(radius=0.2, stroke_color=GREY_B, stroke_width=3).set_fill(BLACK, 1).move_to([3.4 + 0.6 * (j % 2), 1.5 - 0.6 * (j // 2), 0])
                        for j in range(4)])
        door = VGroup(Rectangle(width=1.4, height=2.1, stroke_color=GREY_C, stroke_width=2).move_to([5.6, 1.0, 0]),
                      T("door", 18, GREY_B).move_to([5.6, 2.3, 0]))
        self.steps("Picture a café kitchen on a Saturday morning. Order slips hang on six rails, and each rail belongs to one cook, "
                   "who works its slips in order.", [
            "Order slips",
            (lambda: [LaggedStart(*[Create(m) for m in rails], lag_ratio=0.1)], 1.4),
            "one cook",
            (lambda: [LaggedStart(*[FadeIn(c, scale=0.5) for c in cooks], lag_ratio=0.1)], 0.9),
        ])
        self.steps("Orders pour in, so the owner calls in four more cooks. They stand by the door with nothing to do, "
                   "because every rail already has its cook. Paid to admire the rails.", [
            "four more cooks",
            (lambda: [FadeIn(door), LaggedStart(*[FadeIn(c, shift=0.2 * LEFT) for c in idle], lag_ratio=0.2)], 1.0),
            "nothing to do",
            (lambda: [*self.cap("one rail, one cook: the other four wait", WHITE)], 0.5),
            "Paid to admire",
            (lambda: [Wiggle(idle, scale_value=1.05, rotation_angle=0.02 * TAU)], 0.8),
        ])
        self.steps("That's a Kafka consumer group. Kafka keeps a log of records, split into partitions, and in a consumer group each "
                   "partition has exactly one reader. The texting program reads six partitions, so a seventh reader sits idle.", [
            "a Kafka consumer group",
            (lambda: [*self.cap("rail = partition, cook = a reader in a consumer group", WHITE)], 0.5),
            "a seventh reader",
            (lambda: [glow(idle[0], GREY_B, 1.2)], 0.7),
        ])
        self.steps("Six readers send 30 texts a second. On a sale day, payments reach 300 a second. Wouldn't it be nice if any free "
                   "cook could take any slip?", [
            (lambda: [*self.cap("6 readers x 5 texts a second = 30.   sale day: 300 a second", RED_M)], 0.5),
            "Wouldn't it be nice",
            (lambda: [*self.cap("the wish: any free cook takes any slip", WHITE),
                      LaggedStart(*[c.animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1) for c in idle], lag_ratio=0.2)], 1.0),
        ])
        self.steps("Kafka 4.2 can do that. It's called a share group. Its readers don't own partitions. They all read from all of them, "
                   "and the broker, the server that runs Kafka, hands out records one by one.", [
            "a share group",
            (lambda: [*self.cap("a share group: every reader reads every partition", GOLD_M)], 0.5),
        ])
        self.steps("But then, what stops two cooks from making the same order? Hold that question.", [
            "two cooks",
            (lambda: [glow(cooks[0], RED_M, 1.3), glow(idle[0], RED_M, 1.3)], 0.8),
        ], after=0.4)

        # ---------------- scene 2: one partition, three members ----------------
        cells = []
        for k in range(8):
            r = RoundedRectangle(corner_radius=0.1, width=CW, height=CH, stroke_color=GREY_B, stroke_width=2.5).set_fill(fillc(GREY_B, 0.2), 1)
            cells.append(VGroup(r.move_to([rx(k), REC_Y, 0]), T(str(k), 24).move_to([rx(k), REC_Y + 0.17, 0])).set_z_index(3))
        mems = []
        for i, x in enumerate(MEM_X):
            b = RoundedRectangle(corner_radius=0.14, width=3.1, height=1.25, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1)
            mems.append(VGroup(b.move_to([x, MEM_Y, 0]), T(f"c{i + 1}", 24).move_to([x, MEM_Y + 0.27, 0])))
        self.steps("Let's shrink it to one partition with eight text messages, and three readers, c1, c2 and c3, in the share group notify.", [
            (lambda: [FadeOut(VGroup(rails, cooks, idle, door)), *self.drop("cap")], 0.7),
            "one partition",
            (lambda: [*self.put("rail_t", left_at(T("notifications, partition 0, kept by the broker", 20, GREY_B), rx(0) - 0.55, 3.3)),
                      LaggedStart(*[FadeIn(c, shift=0.1 * DOWN) for c in cells], lag_ratio=0.1)], 1.3),
            "three readers",
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.1 * UP) for m in mems], lag_ratio=0.25)], 1.0),
        ])
        leg = VGroup(*[VGroup(Square(0.22, stroke_color=c, stroke_width=2.5).set_fill(fillc(c, 0.3), 1), T(n, 17, c)).arrange(RIGHT, buff=0.12)
                       for n, c in ST.items()]).arrange(RIGHT, buff=0.55).move_to([0, LEG_Y, 0])
        self.steps("The broker keeps a state for every record. Each one starts out available, waiting for a reader.", [
            "a state for every record",
            (lambda: [FadeIn(leg[0])], 0.5),
            (lambda: [*[self.cnt(k, 0) for k in range(8)]], 0.7),
        ])

        # helpers for one record
        self.n = [0] * 8

        def setr(k, state, owner=None):
            c = ST[state]
            out = [cells[k][0].animate.set_stroke(c).set_fill(fillc(c, 0.2), 1)]
            if owner:
                out += self.put(f"own{k}", T(owner, 16, c).move_to([rx(k), REC_Y - 0.22, 0]).set_z_index(5))
            else:
                out += self.drop(f"own{k}")
            return out

        def acquire(k, m, lock=True):
            self.n[k] += 1
            return [dot_to([rx(k), REC_Y - 0.45, 0], [MEM_X[m], MEM_Y + 0.62, 0], GOLD_M, 0.5),
                    *setr(k, "acquired", f"c{m + 1}"), self.cnt(k, self.n[k])]

        def mstat(m, s, color=GREY_B):
            return self.put(f"ms{m}", T(s, 16, color).move_to([MEM_X[m], MEM_Y - 0.22, 0]))

        def ack(m, s, color):
            return self.put(f"ack{m}", M(s, 16, color).move_to([MEM_X[m], ACK_Y, 0]))

        def clock(s):
            return self.put("clock", M(s, 22, GREY_B).move_to([5.55, 3.3, 0]))

        tri = Triangle(color=GOLD_M, fill_opacity=1, stroke_width=0).scale(0.1).move_to([bx(0), SP_Y, 0])

        def sp(k):
            t = T(f"start offset: {k}", 17, GOLD_M)
            t = left_at(t, bx(k) + 0.18, SP_Y - 0.02) if k < 7 else t.move_to([bx(k) - 0.18 - t.width / 2, SP_Y - 0.02, 0])
            return [tri.animate.move_to([bx(k), SP_Y, 0]), *self.put("sp_t", t)]

        self.steps("And it keeps a start offset: every record before it is finished. Right now that's 0. Nothing is finished.", [
            "a start offset",
            (lambda: [FadeIn(tri, shift=0.1 * UP), *self.put("sp_t", left_at(T("start offset: 0", 17, GOLD_M), bx(0) + 0.18, SP_Y - 0.02))], 0.7),
        ])

        # ---------------- scene 3: the lock ----------------
        self.steps("At ten o'clock, each reader asks for two records. Each one it gets is acquired: locked to that reader for 30 seconds. "
                   "And its delivery count goes from 0 to 1.", [
            (lambda: [*clock("10:00:00")], 0.4),
            "each reader asks",
            (lambda: [LaggedStart(*[AnimationGroup(*acquire(k, k // 2)) for k in range(6)], lag_ratio=0.25), FadeIn(leg[1])], 1.8),
            "locked to that reader",
            (lambda: [*[mstat(m, f"has {2 * m}, {2 * m + 1}: locked 30 s", GOLD_M)[0] for m in range(3)]], 0.6),
            "delivery count",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"cnt{k}"], color=GOLD_M, scale_factor=1.5) for k in range(6)], lag_ratio=0.1)], 0.9),
        ])
        self.steps("In the kitchen, a cook who takes a slip has 30 seconds to say how it went. That's the answer to our question: "
                   "a locked slip can't be taken by anyone else. Records 6 and 7 stay available.", [
            "30 seconds",
            (lambda: [*self.cap("a slip taken = locked to one cook for 30 seconds", GOLD_M)], 0.5),
            "can't be taken",
            (lambda: [LaggedStart(*[glow(cells[k][0], GOLD_M, 1.06) for k in range(6)], lag_ratio=0.1)], 1.0),
            "Records 6 and 7",
            (lambda: [glow(cells[6][0], GREY_B, 1.08), glow(cells[7][0], GREY_B, 1.08)], 0.7),
        ])

        # ---------------- scene 4: the answers ----------------
        self.steps("Each reader answers for each record. ACCEPT means done. c2's texts went out, so 2 and 3 are acknowledged.", [
            (lambda: self.drop("cap"), 0.3),
            "ACCEPT",
            (lambda: [*ack(1, "ACCEPT 2, 3", GREEN_M)], 0.5),
            "so 2 and 3",
            (lambda: [*setr(2, "acknowledged"), *setr(3, "acknowledged"), *mstat(1, "free", GREY_B), FadeIn(leg[2])], 0.7),
        ])
        self.steps("c3 sent 4. But the texting company timed out on 5, which may pass. RELEASE gives it back: available again, "
                   "with its count still 1. REJECT would give up on it for good.", [
            (lambda: [*ack(2, "ACCEPT 4", GREEN_M), *setr(4, "acknowledged")], 0.6),
            "RELEASE",
            (lambda: [*ack(2, "RELEASE 5", BLUE_M), *setr(5, "available"), *mstat(2, "free", GREY_B)], 0.7),
            "REJECT",
            (lambda: [*self.cap("RELEASE: give it back.   REJECT: give up for good.   RENEW: keep the lock longer", WHITE)], 0.6),
        ])
        self.steps("The start offset stays at 0, because records 0 and 1 aren't finished.", [
            (lambda: [Indicate(tri, color=GOLD_M, scale_factor=1.8), glow(cells[0][0], GOLD_M, 1.06), glow(cells[1][0], GOLD_M, 1.06)], 0.9),
        ])

        # ---------------- scene 5: predict the next poll ----------------
        self.steps("Now c2 asks again, for two records. Which two does it get? Pause and guess.", [
            (lambda: [*self.drop("ack1", "ack2", "cap"), glow(mems[1][0], TEAL_M, 1.04)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("5 and 6. Record 5 again, now on its second delivery, and on a different reader. And 6 started before 5 finished. "
                   "Order is gone.", [
            (lambda: [*acquire(5, 1), *acquire(6, 1), *mstat(1, "has 5, 6", GOLD_M), *self.drop("cap")], 0.9),
            "second delivery",
            (lambda: [Indicate(self.lab["cnt5"], color=GOLD_M, scale_factor=1.6)], 0.7),
            "Order is gone",
            (lambda: [*self.cap("5 is handled after 6 started, on another reader: no order", PURPLE_M)], 0.6),
        ])

        # ---------------- scene 6: a reader freezes ----------------
        self.steps("Now c1 freezes. The Java runtime stops it to clean up memory, and it says nothing. You might think the group "
                   "has to notice c1 is gone first. It doesn't.", [
            (lambda: [mems[0][0].animate.set_stroke(GREY_D).set_fill(BLACK, 1), *mstat(0, "frozen, silent", GREY_B), *self.drop("cap")], 0.7),
            "You might think",
            (lambda: [*self.cap("wait for the group to notice?", PURPLE_M)], 0.5),
            "It doesn't",
            (lambda: [*self.cap("no: the lock has a clock", GOLD_M)], 0.5),
        ])
        self.steps("At 10:00:30 the locks on 0 and 1 run out, and the broker makes them available again, for anyone. "
                   "Nobody had to notice anything.", [
            (lambda: clock("10:00:30"), 0.5),
            "run out",
            (lambda: [*setr(0, "available"), *setr(1, "available"), *mstat(0, "frozen: lost 0, 1", RED_M)], 0.8),
            "Nobody had to",
            (lambda: [glow(cells[0][0], GREY_B, 1.08), glow(cells[1][0], GREY_B, 1.08)], 0.7),
        ])
        self.steps("When c1 wakes up and answers, its answers are refused. Like coming back from a nap to find your orders "
                   "cooked by someone else. So the point is: a lock that runs out frees the work without a meeting.", [
            "wakes up",
            (lambda: [mems[0][0].animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1), *ack(0, "ACCEPT 0, 1: refused", RED_M)], 0.7),
            "So the point",
            (lambda: [*self.cap("a lock that runs out hands the work back by itself", GOLD_M), *mstat(0, "free", GREY_B)], 0.6),
        ])

        # ---------------- scene 7: start offset, and the limit ----------------
        self.steps("c3 picks up 0 and 1, their second delivery, and accepts both. Now 0 to 4 are all done, so the start offset moves to 5.", [
            (lambda: [*self.drop("ack0", "cap"), *acquire(0, 2), *acquire(1, 2)], 0.8),
            "accepts both",
            (lambda: [*setr(0, "acknowledged"), *setr(1, "acknowledged"), *ack(2, "ACCEPT 0, 1", GREEN_M)], 0.6),
            "moves to 5",
            (lambda: sp(5), 0.7),
        ])
        self.steps("The share group forgets what's before it, but the records stay in the log for any other reader.", [
            (lambda: [*self.drop("ack2"), *[cells[k].animate.set_opacity(0.55) for k in range(5)]], 0.6),
            "stay in the log",
            (lambda: [*[cells[k].animate.set_opacity(1) for k in range(5)], *self.cap("finished for this group, still in the log", WHITE)], 0.7),
        ])

        def bounce(d):
            self.n[5] = d - 1
            return [*acquire(5, (d % 3)), *ack(d % 3, "RELEASE 5", BLUE_M)]

        self.steps("Record 5 keeps timing out. Released, taken, released, taken. Its count climbs: 3, 4, 5.", [
            (lambda: [*self.drop("cap"), *setr(5, "available"), *mstat(1, "has 6", GOLD_M)], 0.4),
            "Its count climbs",
            (lambda: bounce(3), 0.6), (lambda: [*setr(5, "available")], 0.25),
            (lambda: [*self.drop("ack0"), *bounce(4)], 0.6), (lambda: [*setr(5, "available")], 0.25),
            (lambda: [*self.drop("ack1"), *bounce(5)], 0.6),
        ])
        self.steps("On its fifth delivery, a release no longer makes it available. The limit is five by default, so the broker "
                   "archives it: given up on, never delivered again.", [
            "archives it",
            (lambda: [*setr(5, "archived", "archived"), FadeIn(leg[3]), *self.drop("ack2")], 0.7),
            "never delivered",
            (lambda: [*self.cap("share.delivery.count.limit = 5", RED_M)], 0.5),
        ])
        self.steps("Since Kafka 4.4, the broker can also copy it to a dead-letter topic, with a header that says it was offset 5. "
                   "Then 6 and 7 are accepted, and the start offset moves to 8.", [
            "dead-letter topic",
            (lambda: [*self.cap("Kafka 4.4: a dead-letter copy, header __dlq.errors.offset=5", RED_M)], 0.5),
            "6 and 7",
            (lambda: [*acquire(7, 2), *setr(6, "acknowledged"), *mstat(1, "free", GREY_B)], 0.6),
            (lambda: [*setr(7, "acknowledged"), *mstat(2, "free", GREY_B)], 0.4),
            "moves to 8",
            (lambda: sp(8), 0.7),
        ])

        # ---------------- scene 8: the price ----------------
        self.steps("Here's the price. Readers work side by side, and released records come back late. So a share group keeps no order, "
                   "not per key, not per partition.", [
            (lambda: [*self.cap("the price: no order, not per key, not per partition", PURPLE_M)], 0.6),
            "come back late",
            (lambda: [glow(cells[5][0], RED_M, 1.06)], 0.7),
        ])
        self.steps("For text messages, that's fine. Two receipts can go out either way round. For a ledger, where a refund must "
                   "follow its payment, never.", [
            "For text messages",
            (lambda: [*self.cap("texts: any order is fine.   a ledger: never", WHITE)], 0.5),
        ])
        self.steps("And the broker keeps the knobs in bounds: the lock between 15 and 60 seconds, the delivery limit between 2 and 10.", [
            (lambda: [*self.cap("lock: 15 to 60 seconds (30 by default).   delivery limit: 2 to 10 (5 by default)", GREY_B)], 0.6),
        ])

        # ---------------- scene 9: the code ----------------
        diagram = VGroup(*[m for m in self.mobjects if isinstance(m, VMobject)])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(rows_j, rows_k, color):
            return [jp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows_j] + \
                   [kp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows_k]

        self.steps("Here's a reader that answers for every record, in Java and in Kotlin. It reads with KafkaShareConsumer, "
                   "which has the same poll as before.", [
            (lambda: [diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
        ])
        self.steps("Sent: ACCEPT. Timed out: RELEASE. A bad phone number: REJECT. Then commitSync sends the answers to the broker.", [
            (lambda: hl((4,), (4,), GREEN_M), 0.9),
            "Timed out",
            (lambda: hl((6,), (6,), BLUE_M), 0.9),
            "A bad phone",
            (lambda: hl((8,), (8,), RED_M), 0.9),
            "Then commitSync",
            (lambda: hl((11,), (12,), GOLD_M), 0.9),
        ], after=0.6)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, what stops two cooks from making the same order? A lock on every slip. Any free reader takes any record, "
                   "the lock runs out by itself, and the count stops a record that never works.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: self.cap("what stops two cooks making the same order?", WHITE), 0.4),
            "A lock on every slip",
            (lambda: [*self.cap("a lock on every slip", GOLD_M, 32), LaggedStart(*[glow(m[0], TEAL_M, 1.04) for m in mems], lag_ratio=0.2)], 0.9),
            "the count stops",
            (lambda: [glow(cells[5][0], RED_M, 1.06)], 0.7),
        ])
        self.steps("One quick check. A reader takes record 9 and then crashes, silently. When can another reader get record 9? "
                   "Pause and think.", [
            (lambda: [*self.cap("a reader takes record 9, then crashes", WHITE)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("When its 30-second lock runs out. Then it's available again, and the next reader to take it makes its count 2.", [
            (lambda: [*self.cap("when the 30-second lock runs out; next delivery: count 2", GOLD_M)], 0.6),
            "available again",
            (lambda: [glow(leg[0][0], GREY_B, 1.3)], 0.6),
        ], after=0.4)
        self.wait(2.0)

    def cnt(self, k, n):
        new = T(f"count {n}", 15, GOLD_M if n else GREY_B).move_to([rx(k), CNT_Y, 0])
        old = self.lab.get(f"cnt{k}")
        self.lab[f"cnt{k}"] = new
        return swap(old, new)
