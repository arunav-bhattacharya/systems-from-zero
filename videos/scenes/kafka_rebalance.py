from sfz import *

SAY.insert(0, (r"\bonPartitionsRevoked\b", "on partitions revoked"))
SAY.insert(0, (r"\bonPartitionsAssigned\b", "on partitions assigned"))
SAY.insert(0, (r"\bonPartitionsLost\b", "on partitions lost"))
SAY.insert(0, (r"\bConsumerRebalanceListener\b", "consumer rebalance listener"))
SAY.insert(0, (r"\bc([123])\b", r"C \1"))
SAY.insert(0, (r"\b79,200\b", "seventy-nine thousand two hundred"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TB_Y, TB_W, TB_H, OWN_Y, TITLE_Y = 2.55, 1.3, 0.75, 1.92, 3.32
TB_X = [-4.0 + 1.6 * i for i in range(6)]
MEM = {"c1": np.array([-5.4, 0.75, 0]), "c2": np.array([5.4, 0.75, 0]), "c3": np.array([5.4, -0.45, 0])}
MCOL = {"c1": GOLD_M, "c2": TEAL_M, "c3": PURPLE_M}
BAR_X0, BAR_X1, BAR_YC, BAR_H = -3.4, 3.4, -1.0, 0.5
O0, O1 = 280, 360
TICK_Y, PROG_Y, BAR2_Y, CAP_Y = -1.45, -1.92, -2.78, -3.27


def ox(o):
    return BAR_X0 + (o - O0) / (O1 - O0) * (BAR_X1 - BAR_X0)


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
        bar = Line([-1.0, BAR2_Y, 0], [1.0, BAR2_Y, 0], stroke_width=5, color=YELLOW_M)
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
    return RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)


def table(i, color=GREY_B):
    c = np.array([TB_X[i], TB_Y, 0])
    return VGroup(rbox(TB_W, TB_H, color, c), T(str(i), 26).move_to(c))


def member(name):
    c = MEM[name]
    return VGroup(rbox(1.9, 0.85, MCOL[name], c), T(name, 26).move_to(c))


def bookmark(o, text=None, color=BLUE_M):
    x = ox(o)
    y0, y1 = BAR_YC + BAR_H / 2 + 0.05, BAR_YC + BAR_H / 2 + 0.6
    post = Line([x, y0, 0], [x, y1, 0], stroke_width=4, color=color)
    flag = Polygon([x, y1, 0], [x + 0.3, y1 - 0.12, 0], [x, y1 - 0.24, 0], stroke_width=0).set_fill(color, 1)
    lab = left_at(T(text or f"committed: {o}", 19, color), x + 0.4, y1 - 0.12)
    return VGroup(post, flag, lab).set_z_index(4)


def progress(o, label=None, color=GOLD_M):
    x = ox(o)
    tri = Triangle(stroke_width=0).set_fill(color, 1).scale(0.12).move_to([x, PROG_Y, 0])
    lab = left_at(T(label or f"c1 has processed everything before {o}", 18, color), x + 0.25, PROG_Y)
    return VGroup(tri, lab)


def span(o0, o1, color, op=0.55):
    return Rectangle(width=ox(o1) - ox(o0), height=BAR_H - 0.06, stroke_width=0).set_fill(color, op).move_to(
        [(ox(o0) + ox(o1)) / 2, BAR_YC, 0])


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.6, height=4.3, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.15, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.05, 2.0)
    rows = VGroup()
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * M("x" * 40, 15).width / 40
        rows.add(left_at(M(s.strip() if s.strip() else " ", 15, col), x - 3.05 + ind, 1.5 - 0.4 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["consumer.subscribe(List.of(\"payments\"),",
        " new ConsumerRebalanceListener() {",
        "  public void onPartitionsRevoked(var ps) {",
        "   consumer.commitSync(processedOffsets(ps));",
        "  }",
        "  public void onPartitionsAssigned(var ps) {}",
        "  public void onPartitionsLost(var ps) {",
        "   forget(ps);   // no commit",
        "  }});"]
KOTLIN = ["consumer.subscribe(listOf(\"payments\"),",
          " object : ConsumerRebalanceListener {",
          "  override fun onPartitionsRevoked(ps) {",
          "   consumer.commitSync(processedOffsets(ps))",
          "  }",
          "  override fun onPartitionsAssigned(ps) {}",
          "  override fun onPartitionsLost(ps) {",
          "   forget(ps)    // no commit",
          "  }})"]


class KafkaRebalance(Base):
    """msg-08, section 1. Month-end: one ledger handles 8 payments a second, 30 arrive, 79,200 behind after an hour.
    Two more copies join, and payments are added twice. A group gives each partition one owner (the restaurant, one
    waiter per table). c2 and c3 join, partitions move: a rebalance. Partition 3: c1 has processed everything before
    340, but committed 300; predict where c2 starts (300; 300 to 339 again). The lab without handovers: 200 processed
    for 120. The waiter's note before the table moves. ConsumerRebalanceListener: revoked (commit 340), assigned,
    lost (don't commit). The order rule; the tempting commit in onPartitionsLost broken. Code in Java and Kotlin,
    the moral, a check."""

    def own(self, i, who):
        """Partition i gets owner who: its table takes the owner's colour and a small tag."""
        col = MCOL.get(who, GREY_B)
        tag = T(who, 18, col).move_to([TB_X[i], OWN_Y, 0])
        return [self.tables[i][0].animate.set_stroke(col), *self.put(f"own{i}", tag)]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Who reads partition 3 now?", "a rebalance, and the handover that keeps its bookmark")

        self.tables = [table(i) for i in range(6)]
        ttl = T("the payments topic: six partitions", 20, GREY_B).move_to([0, TITLE_Y, 0])
        mem = {k: member(k) for k in MEM}

        # ---------------- scene 1: month-end ----------------
        self.steps("Picture the last day of the month. Card payments pour into Kafka, a program that keeps logs of messages "
                   "and lets other programs read them.", [
            "Card payments",
            (lambda: [FadeIn(ttl), LaggedStart(*[FadeIn(t, shift=0.1 * DOWN) for t in self.tables], lag_ratio=0.15)], 1.3),
        ])
        self.steps("The ledger, the program that keeps each account's balance, reads them. It handles 8 payments a second, "
                   "and 30 arrive. After an hour, it's 79,200 payments behind.", [
            (lambda: [FadeIn(mem["c1"]), *[a for i in range(6) for a in self.own(i, "c1")]], 0.9),
            "8 payments",
            (lambda: self.cap("handles 8 a second.   30 arrive a second."), 0.5),
            "After an hour",
            (lambda: self.cap("after an hour: 79,200 payments behind", RED_M), 0.5),
        ])
        self.steps("So the team starts two more copies. A few seconds later, the logs show payments added twice. "
                   "Where did the doubles come from? Hold that question.", [
            "two more copies",
            (lambda: [FadeIn(mem["c2"], shift=0.1 * LEFT), FadeIn(mem["c3"], shift=0.1 * LEFT)], 0.7),
            "added twice",
            (lambda: self.cap("payments added twice", RED_M), 0.5),
            "Where did",
            (lambda: self.cap("where did the doubles come from?", WHITE), 0.5),
        ])

        # ---------------- scene 2: one owner per partition ----------------
        self.steps("First, how copies share the work. A restaurant gives each table to one waiter, and a waiter looks after "
                   "several tables. Nobody gets three desserts, and courses come in order.", [
            (lambda: self.uncap(), 0.3),
            "each table",
            (lambda: [LaggedStart(*[glow(t[0], GOLD_M, 1.05) for t in self.tables], lag_ratio=0.12)], 1.2),
            "Nobody gets",
            (lambda: self.cap("one waiter per table: no triple desserts, courses in order"), 0.5),
        ])
        self.steps("Kafka does the same. The three copies form a consumer group, and the group gives each partition to exactly "
                   "one member. When members join or leave, partitions change owner. That's called a rebalance.", [
            (lambda: self.cap("a consumer group: each partition has exactly one owner", WHITE), 0.5),
            "partitions change owner",
            (lambda: [*self.own(3, "c2"), *self.own(4, "c2"), *self.own(5, "c2")], 0.7),
            (lambda: [*self.own(2, "c3"), *self.own(5, "c3")], 0.7),
            "called a rebalance",
            (lambda: self.cap("partitions changing owner: a rebalance", YELLOW_M), 0.5),
        ])
        self.steps("The partition moves. But what happens to its bookmark?", [
            (lambda: self.cap("the partition moves. what about its bookmark?", WHITE), 0.5),
        ])

        # ---------------- scene 3: partition 3 up close ----------------
        bar = Rectangle(width=BAR_X1 - BAR_X0, height=BAR_H, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to(
            [(BAR_X0 + BAR_X1) / 2, BAR_YC, 0])
        ticks = VGroup(*[VGroup(Line([ox(o), BAR_YC - BAR_H / 2, 0], [ox(o), BAR_YC - BAR_H / 2 - 0.1, 0], stroke_width=2, color=GREY_C),
                                T(str(o), 17, GREY_B).move_to([ox(o), TICK_Y, 0])) for o in range(O0, O1 + 1, 20)])
        p3lab = T("partition 3", 20, GREY_B).move_to([BAR_X0 - 0.85, BAR_YC, 0])
        zoom = DashedLine(self.tables[3][0].get_bottom() + 0.4 * DOWN, [ox(320), BAR_YC + BAR_H / 2 + 0.75, 0], dash_length=0.08,
                          stroke_width=1.5, color=GREY_D)
        self.steps("Take partition 3, before the move. c1 owns it, and has processed everything before offset 340. "
                   "It commits after every batch of 100, so the group's bookmark says 300.", [
            (lambda: [*self.uncap(), *self.own(2, "c1"), *self.own(3, "c1"), *self.own(4, "c1"), *self.own(5, "c1"),
                      FadeOut(mem["c2"]), FadeOut(mem["c3"])], 0.7),
            "Take partition 3",
            (lambda: [FadeIn(bar), FadeIn(ticks), FadeIn(p3lab), Create(zoom), glow(self.tables[3][0], GOLD_M, 1.05)], 0.9),
            "processed everything",
            (lambda: [FadeIn(self.lab.setdefault("done", span(O0, 340, GOLD_M, 0.35))), *self.put("prog", progress(340))], 0.7),
            "the group's bookmark",
            (lambda: self.put("bm", bookmark(300)), 0.6),
        ])
        self.steps("Now c2 joins, and the group gives partition 3 to c2. Where does c2 start? Pause and guess.", [
            (lambda: [FadeIn(mem["c2"], shift=0.1 * LEFT)], 0.5),
            "gives partition 3",
            (lambda: [*self.own(3, "c2"), *self.own(4, "c2"), *self.own(5, "c2")], 0.7),
            "Pause and guess",
            (lambda: self.cap("where does c2 start? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("At 300, where the bookmark says. c2 knows nothing else. So it processes 300 to 339 a second time.", [
            (lambda: [*self.uncap(), glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.6),
            "So it processes",
            (lambda: [*self.put("rep", span(300, 340, RED_M, 0.35)), *self.put("prog2", T("c2 again: 300 to 339", 17, WHITE).move_to(
                [ox(320), BAR_YC, 0]).set_z_index(5))], 0.7),
            (lambda: self.cap("forty payments, processed twice", RED_M), 0.5),
        ])
        self.steps("And if c1 is still busy with that batch when c2 starts, both apply the same payments at the same moment.", [
            (lambda: [glow(mem["c1"][0], RED_M, 1.06), glow(mem["c2"][0], RED_M, 1.06)], 0.9),
        ])
        self.steps("The lesson's lab takes the handover away. Three consumers, 120 payments in the topic, and the group "
                   "processes 200. Eighty of them twice, just from adding two consumers.", [
            (lambda: self.cap("no handover: 200 processed, for 120 in the topic", RED_M), 0.6),
            "Eighty of them",
            (lambda: self.cap("80 payments processed twice, from adding two consumers", RED_M), 0.5),
        ])

        # ---------------- scene 4: the waiter's note ----------------
        self.steps("Back to the restaurant. A good waiter doesn't walk away from a table in the middle of a meal. "
                   "Before the table moves, they tell the next waiter what's been served.", [
            (lambda: [*self.uncap(), *self.drop("rep", "prog2"), *self.own(3, "c1"), *self.own(4, "c1"), *self.own(5, "c1")], 0.6),
            "Before the table moves",
            (lambda: [glow(self.tables[3][0], GOLD_M, 1.05), *self.cap("before the table moves: \"here's what's been served\"", WHITE)], 0.7),
        ])
        self.steps("Let's map it. The table is the partition, the waiter is the consumer, and the note is the committed offset. "
                   "The moment just before leaving is the handover.", [
            "The table",
            (lambda: [glow(self.tables[3][0], GOLD_M, 1.05)], 0.5),
            "the waiter",
            (lambda: [glow(mem["c1"][0], GOLD_M, 1.06)], 0.5),
            "the note",
            (lambda: [glow(self.lab["bm"][0], BLUE_M, 1.0), *self.cap("the note: the committed offset", BLUE_M)], 0.6),
        ])

        # ---------------- scene 5: the listener ----------------
        self.steps("Kafka gives the consumer that moment. You register a ConsumerRebalanceListener: three functions the consumer "
                   "calls, from inside poll, when its partitions change.", [
            (lambda: self.cap("ConsumerRebalanceListener: three functions, called from inside poll", WHITE), 0.6),
        ])
        self.steps("onPartitionsRevoked: these are leaving, and they're still yours. Finish or drop the current work, and "
                   "commit how far you got.", [
            (lambda: self.cap("onPartitionsRevoked: still yours. commit how far you got", GOLD_M), 0.6),
            "commit how far",
            (lambda: [*self.put("bm", bookmark(340, "committed: 340")), *self.drop("prog")], 0.7),
        ])
        self.steps("onPartitionsAssigned: these are new to you, and you start at their committed offsets.", [
            (lambda: [*self.cap("onPartitionsAssigned: new to you. start at the committed offset", TEAL_M),
                      *self.own(3, "c2"), *self.own(4, "c2"), *self.own(5, "c2")], 0.7),
            "you start",
            (lambda: [*self.put("prog", progress(340, "c2 starts at 340", TEAL_M)), glow(mem["c2"][0], TEAL_M, 1.06)], 0.6),
        ])
        self.steps("Replay the move with that commit, and c2 starts at 340. Nothing is processed twice.", [
            "c2 starts",
            (lambda: [*self.put("ok", T("nothing repeated", 18, GREEN_M).move_to([ox(320), BAR_YC, 0]).set_z_index(5))], 0.6),
            "Nothing is processed",
            (lambda: [self.lab["done"].animate.set_fill(GREEN_M, 0.35), *self.cap("commit in onPartitionsRevoked: the next owner starts exactly there", GREEN_M)], 0.7),
        ])
        self.stamp("poster")
        self.steps("And onPartitionsLost: the group has already given these to someone else, usually because this member was "
                   "thrown out. Don't commit. That bookmark isn't yours to move any more.", [
            (lambda: [*self.drop("ok"), *self.cap("onPartitionsLost: already someone else's. don't commit", RED_M)], 0.6),
        ])

        # ---------------- scene 6: why it's safe, and a tempting mistake ----------------
        self.steps("Why is this safe? One rule about order. The group never gives a partition to its new owner until the old "
                   "owner has revoked it. So c1's commit always lands before c2 reads the bookmark.", [
            (lambda: self.cap("the rule: revoke first, then assign", WHITE), 0.5),
            "So c1's commit",
            (lambda: [glow(mem["c1"][0], GOLD_M, 1.06)], 0.5),
            (lambda: [glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.5),
            (lambda: [glow(mem["c2"][0], TEAL_M, 1.06)], 0.5),
        ])
        self.steps("Now a tempting idea: commit in onPartitionsLost too, just to be safe. Follow it through. c1 was thrown out "
                   "while stuck at 300. c2 already owns partition 3 and has moved the bookmark to 360.", [
            (lambda: self.cap("tempting: commit in onPartitionsLost too", PURPLE_M), 0.5),
            "c1 was thrown out",
            (lambda: [mem["c1"][0].animate.set_stroke(RED_M), *self.put("prog", progress(300, "c1, stuck: done only before 300", GOLD_M))], 0.6),
            "moved the bookmark",
            (lambda: [*self.put("bm", bookmark(360, "committed: 360")), self.lab["done"].animate.stretch_to_fit_width(ox(360) - ox(O0)).move_to(
                [(ox(O0) + ox(360)) / 2, BAR_YC, 0])], 0.7),
        ])
        self.steps("Then c1's late commit drags it back to 300, and the next owner repeats sixty payments. "
                   "It's a waiter who was sent home, phoning in to change the bill of a table someone else now serves.", [
            (lambda: [*self.put("bm", bookmark(300, "committed: 300 (by c1, late)", RED_M)), *self.put("rep", span(300, 360, RED_M, 0.35))], 0.7),
            "It's a waiter",
            (lambda: self.cap("lost means lost: no commit", RED_M), 0.5),
        ])
        self.steps("One more note. A member that dies without revoking can't commit anything, so repeats can still happen. "
                   "That's why the ledger still checks each payment's idempotency key. But a planned rebalance repeats nothing.", [
            (lambda: [*self.drop("rep"), mem["c1"][0].animate.set_stroke(GOLD_M), *self.put("bm", bookmark(360, "committed: 360")),
                      *self.drop("prog"), *self.cap("a crash still repeats: keep the idempotency key")], 0.7),
            "But a planned",
            (lambda: self.cap("a planned rebalance with a handover repeats nothing", GREEN_M), 0.5),
        ])

        # ---------------- scene 7: the code ----------------
        diagram = VGroup(ttl, *self.tables, mem["c1"], mem["c2"], bar, ticks, p3lab, zoom, *self.lab.values())
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.4)
        kp = code_panel("Kotlin", KOTLIN, 3.4)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, you pass the listener to subscribe. Commit in onPartitionsRevoked, "
                   "and in onPartitionsLost, just forget the partitions.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "Commit in",
            (lambda: hl((2, 3), GOLD_M), 1.2),
            "just forget",
            (lambda: hl((6, 7), RED_M), 1.2),
        ], after=0.8)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So where did the doubles come from? Partitions that moved without a commit. The new owner started at an "
                   "old bookmark. A partition that moves without a commit gets processed twice.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            "Partitions that moved",
            (lambda: [glow(self.tables[3][0], TEAL_M, 1.05), glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.7),
            "A partition that moves",
            (lambda: self.cap("hand over the note before the table moves: commit in onPartitionsRevoked", YELLOW_M, 26), 0.6),
        ], after=0.6)
        self.steps("One quick check, with numbers made up for it. c1 owns partition 4, has processed everything before 520, "
                   "and last committed 500. It commits in onPartitionsRevoked. Where does the new owner start? Pause and think.", [
            (lambda: [*self.uncap(), glow(self.tables[4][0], GOLD_M, 1.05),
                      *self.cap("partition 4: done before 520, committed 500, then a handover. pause and think", YELLOW_M)], 0.7),
        ], after=0)
        self.countdown(3.0)
        self.steps("At 520. The handover commit moves the bookmark to the next record to read, so nothing repeats.", [
            (lambda: self.cap("at 520: the handover moved the bookmark first", GREEN_M), 0.6),
        ])
        self.wait(2.0)
