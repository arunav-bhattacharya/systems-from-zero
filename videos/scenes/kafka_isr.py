from sfz import *

SAY.insert(0, (r"\backs=all\b", "acks equals all"))
SAY.insert(0, (r"\backs=1\b", "acks equals one"))
SAY.insert(0, (r"\bpayments-0\b", "payments zero"))
SAY.insert(0, (r"\bKafka 3\.0\b", "Kafka three point oh"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ROWS_Y = [1.55, 0.25, -1.05]                 # broker 1 (leader), broker 2, broker 3
LAB_X = -5.1                                 # centre of each row's name box
C0, CW, CP = -3.1, 0.7, 0.8                  # first cell's centre, cell width, pitch
NCELL = 10
HW_TOP, HW_BOT = 2.55, -1.75
PROD_C = np.array([-5.1, 3.0, 0])
CAP_Y, BAR_Y = -3.25, -2.65
ROLE_C = [GOLD_M, TEAL_M, TEAL_M]


def cx(i):
    return C0 + CP * i


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
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def cell(r, i, color=BLUE_M):
    b = RoundedRectangle(corner_radius=0.08, width=CW, height=0.72, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.22), 1)
    return VGroup(b, M(str(i), 22).move_to(b)).move_to([cx(i), ROWS_Y[r], 0])


def name_box(r, title, sub, color):
    b = RoundedRectangle(corner_radius=0.12, width=2.5, height=0.95, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    b.move_to([LAB_X, ROWS_Y[r], 0])
    return VGroup(b, T(title, 22).move_to([LAB_X, ROWS_Y[r] + 0.17, 0]), T(sub, 17, GREY_B).move_to([LAB_X, ROWS_Y[r] - 0.2, 0]))


def leo_tag(r, n, color=GREY_A):
    return T(f"end: {n}", 20, color).move_to([cx(n) + 0.28, ROWS_Y[r], 0])


def hw_line(n):
    x = cx(n) - CP / 2
    ln = DashedLine([x, 2.1, 0], [x, HW_BOT, 0], dash_length=0.1, stroke_width=3, color=YELLOW_M)
    lab = T(f"high watermark: {n}", 20, YELLOW_M).move_to([x, HW_BOT - 0.28, 0])
    return VGroup(ln, lab)


def room(rows, label="ISR: in the room"):
    top, bot = ROWS_Y[rows[0]] + 0.62, ROWS_Y[rows[-1]] - 0.62
    r = DashedVMobject(RoundedRectangle(corner_radius=0.2, width=13.1, height=top - bot, stroke_color=GOLD_M, stroke_width=2.5),
                       num_dashes=90).move_to([-0.35, (top + bot) / 2, 0])
    lab = T(label, 18, GOLD_M)
    lab.move_to([6.25 - lab.width / 2, top + 0.22, 0])
    return VGroup(r, lab)


class KafkaISR(Base):
    """msg-04, section 0. A partition on one disk dies with it. The shop with three sales books: the owner writes,
    two assistants copy; a sale counts once everyone in the room has copied it. Leader, followers, replicas; only the
    leader gives offsets; followers fetch. Every copy holds 0 to 4 (end offset 5). Three payments at 5, 6, 7: answer
    now (lost with the disk) or wait for all (one slow follower). The ISR and the high watermark, the smallest end
    offset in the ISR: broker 3 at 5 holds it at 5 (predict), then catches up to 8. acks=1 and acks=all; committed
    records; unclean leader election refused; the room of one; the moral; a check (9, 7, 9: HW 7)."""

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

    def add_cells(self, r, idx, color=BLUE_M):
        new = [cell(r, i, color) for i in idx]
        self.cells[r].extend(new)
        return [LaggedStart(*[FadeIn(c, shift=0.15 * RIGHT) for c in new], lag_ratio=0.2)]

    def leo(self, r, n, color=GREY_A):
        return self.put(f"leo{r}", leo_tag(r, n, color), RIGHT)

    def hw(self, n):
        return self.put("hw", hw_line(n), RIGHT)

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.cells = [[], [], []]
        self.title_card("When is a payment safe?", "three copies, one leader, and the high watermark")

        # ---------------- scene 1: one disk ----------------
        self.steps("A coffee-shop app sends every card payment to Kafka, a program that keeps logs of records and lets other programs read them.", [
            (lambda: self.cap("Kafka: keeps logs of records for other programs"), 0.6),
        ])
        self.steps("The payments live in a log called payments-0, stored as files on one computer's disk. "
                   "The program running Kafka there is a broker.", [
            "The payments live",
            (lambda: [*self.add_cells(0, range(5))], 1.2),
            "The program running",
            (lambda: [*self.put("n0", name_box(0, "broker 1", "payments-0", BLUE_M), LEFT)], 0.6),
        ])
        crash = tick(False, 0.3).move_to([cx(2), ROWS_Y[0], 0])
        self.steps("Now that disk dies. Nobody can write to payments-0 or read it. And if the disk is gone for good, so are the payments. "
                   "How do we keep them, and when is a payment really safe?", [
            (lambda: [*[c.animate.set_opacity(0.2) for c in self.cells[0]], Create(crash), self.lab["n0"][0].animate.set_stroke(RED_M)], 0.8),
            "How do we keep",
            (lambda: self.cap("how do we keep them? when is a payment safe?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 2: the shop ----------------
        self.steps("Picture a small shop that keeps three copies of its sales book. The owner writes each sale in her book, "
                   "and two assistants copy it into theirs, line by line, in the same order.", [
            (lambda: [*self.uncap(), FadeOut(crash), *[c.animate.set_opacity(1) for c in self.cells[0]],
                      *self.put("n0", name_box(0, "owner", "writes each sale", GOLD_M), LEFT)], 0.8),
            "and two assistants",
            (lambda: [*self.put("n1", name_box(1, "assistant", "copies", TEAL_M), LEFT),
                      *self.put("n2", name_box(2, "assistant", "copies", TEAL_M), LEFT)], 0.7),
            "line by line",
            (lambda: [*self.add_cells(1, range(5)), *self.add_cells(2, range(5))], 1.4),
        ])
        rm = room([0, 1, 2], "in the room")
        self.steps("The house rule: a sale counts once everyone in the room has copied it. Keep that rule in mind.", [
            (lambda: [Create(rm[0]), FadeIn(rm[1]), *self.cap("a sale counts once everyone in the room has copied it", GOLD_M)], 1.0),
        ])
        self.lab["room"] = rm

        # ---------------- scene 3: the map ----------------
        self.steps("Kafka does the same, once per partition. Each copy is a replica, and three is the usual number. "
                   "The owner's copy is the leader: every write goes to it, and it decides the order. The assistants are followers.", [
            (lambda: self.cap("each copy: a replica. three is the usual number"), 0.6),
            "The owner's copy",
            (lambda: [*self.put("n0", name_box(0, "broker 1", "leader", GOLD_M), LEFT), *self.cap("owner = leader: every write, and the order", GOLD_M)], 0.7),
            "The assistants are",
            (lambda: [*self.put("n1", name_box(1, "broker 2", "follower", TEAL_M), LEFT),
                      *self.put("n2", name_box(2, "broker 3", "follower", TEAL_M), LEFT),
                      *self.cap("assistants = followers", TEAL_M)], 0.7),
        ])
        self.steps("Only the leader gives out offsets, so offset 4 means the same payment on every broker. Each follower keeps asking the leader: "
                   "anything after my last record? It appends what comes back, at the same offsets.", [
            "so offset 4",
            (lambda: [*[glow(self.cells[r][4][0], YELLOW_M, 1.1) for r in range(3)]], 0.9),
            "Each follower",
            (lambda: [*self.cap("a follower fetches: anything after my last record?", TEAL_M)], 0.5),
        ])
        self.steps("Each replica has its own end offset: the offset its next record will get. Here, every copy holds 0 to 4, so each one's is 5.", [
            "its own end offset",
            (lambda: [*self.leo(0, 5), *self.leo(1, 5), *self.leo(2, 5)], 0.8),
            "so each one's",
            (lambda: [*self.cap("end offset (LEO): where the next record goes"), *[Indicate(self.lab[f"leo{r}"], color=YELLOW_M) for r in range(3)]], 0.8),
        ])

        # ---------------- scene 4: when is it safe? ----------------
        prod = VGroup(RoundedRectangle(corner_radius=0.12, width=2.5, height=0.62, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1),
                      T("producer", 22)).move_to(PROD_C)
        prod[1].move_to(prod[0])
        parr = Arrow(PROD_C + [1.3, 0, 0], [cx(5), ROWS_Y[0] + 0.72, 0], buff=0.05, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.1)
        self.steps("Now a producer, the program that writes, sends three payments. The leader adds them at 5, 6 and 7. "
                   "Its end offset is 8. When should it tell the producer they're safe?", [
            (lambda: [*self.uncap(), FadeIn(prod), GrowArrow(parr)], 0.7),
            "The leader adds",
            (lambda: [*self.add_cells(0, range(5, 8), GOLD_M), *self.drop("leo0")], 1.0),
            "Its end offset",
            (lambda: self.leo(0, 8), 0.5),
            "When should",
            (lambda: self.cap("when is it safe to answer?", YELLOW_M), 0.5),
        ])
        dead = tick(False, 0.3).move_to([cx(6), ROWS_Y[0], 0])
        self.steps("Answer right away, and the producer may hear safe a moment before the leader's disk dies. Those three are lost. "
                   "Wait for every follower, and one slow follower holds up every write.", [
            (lambda: self.cap("answer right away?", PURPLE_M), 0.5),
            "before the leader's disk",
            (lambda: [Create(dead), *[c.animate.set_opacity(0.2) for c in self.cells[0][5:]]], 0.7),
            "Those three",
            (lambda: self.cap("5, 6 and 7: lost with the disk", RED_M), 0.5),
            "Wait for every",
            (lambda: [FadeOut(dead), *[c.animate.set_opacity(1) for c in self.cells[0][5:]],
                      *self.cap("wait for every follower? one slow one holds up every write", PURPLE_M)], 0.6),
        ])

        # ---------------- scene 5: ISR and high watermark ----------------
        self.steps("Kafka takes a middle path. The leader keeps a list of the replicas keeping up with it: the in-sync replicas, ISR for short. "
                   "That's the people in the room.", [
            "The leader keeps",
            (lambda: [*self.put("room", room([0, 1, 2]))], 0.8),
            "That's the people",
            (lambda: [glow(self.lab["room"][0], GOLD_M, 1.01), *self.cap("ISR: the replicas keeping up. The room.", GOLD_M)], 0.8),
        ])
        self.steps("From them it works out the high watermark: the smallest end offset in the ISR. "
                   "It's the line up to which everyone in the room has copied.", [
            "the high watermark",
            (lambda: [*self.hw(5)], 0.8),
            "the smallest end offset",
            (lambda: [*self.cap("high watermark: the smallest end offset in the ISR", YELLOW_M),
                      *[Indicate(self.lab[f"leo{r}"], color=YELLOW_M) for r in (1, 2)]], 0.8),
        ])
        self.steps("Records below it are on every in-sync copy. They're called committed.", [
            (lambda: [*self.cap("below the line: committed, on every in-sync copy", GREEN_M),
                      *[c[0].animate.set_stroke(GREEN_M) for r in range(3) for c in self.cells[r][:5]]], 0.9),
        ])

        # ---------------- scene 6: predict ----------------
        self.steps("Broker 2 fetches 5 to 7. Its end offset is 8. Broker 3 is slow. It's still at 5. "
                   "Where is the high watermark? Pause and guess.", [
            (lambda: [*self.uncap(), *self.drop("leo1", "hw")], 0.3),
            (lambda: [*self.add_cells(1, range(5, 8), TEAL_M)], 0.9),
            (lambda: self.leo(1, 8), 0.4),
            "Broker 3 is slow",
            (lambda: [glow(self.lab["n2"][0], RED_M, 1.04), *self.leo(2, 5, RED_M)], 0.8),
            "Pause and guess",
            (lambda: self.cap("where is the high watermark?", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("5. The smallest end offset in the room is broker 3's. So consumers still can't see 5, 6 or 7, "
                   "and the producer is still waiting.", [
            (lambda: [*self.uncap(), *self.hw(5), Indicate(self.lab["leo2"], color=RED_M, scale_factor=1.3)], 0.8),
            "So consumers",
            (lambda: [*self.cap("consumers read only below the line; the producer waits", YELLOW_M), glow(prod[0], YELLOW_M, 1.05)], 0.8),
        ])
        self.steps("Then broker 3 catches up to 8. The high watermark jumps to 8, and the producer gets its answer.", [
            (lambda: [*self.drop("leo2"), *self.add_cells(2, range(5, 8), TEAL_M)], 0.9),
            (lambda: self.leo(2, 8), 0.4),
            "The high watermark jumps",
            (lambda: [*self.hw(8), *[c[0].animate.set_stroke(GREEN_M) for r in range(3) for c in self.cells[r][5:8]]], 0.8),
            "the producer gets",
            (lambda: [*self.cap("5, 6 and 7 committed: the producer hears safe", GREEN_M), glow(prod[0], GREEN_M, 1.05)], 0.7),
        ])

        # ---------------- scene 7: acks ----------------
        self.steps("The producer picks how long to wait with a setting called acks. acks=1: answer once your own copy has it. "
                   "acks=all: answer once every in-sync replica has it, the moment the high watermark passes the record.", [
            "acks=1",
            (lambda: [*self.cap("acks=1: answer once the leader's copy has it", PURPLE_M), glow(self.lab["n0"][0], GOLD_M, 1.04)], 0.7),
            "acks=all",
            (lambda: [*self.cap("acks=all: answer once every in-sync replica has it", GREEN_M), glow(self.lab["room"][0], GOLD_M, 1.01)], 0.7),
            "the moment",
            (lambda: [glow(self.lab["hw"][0], YELLOW_M, 1.02)], 0.8),
        ])
        self.steps("acks=all has been the default since Kafka 3.0. And because consumers read only below the high watermark, "
                   "they never see a record that could vanish.", [
            (lambda: self.cap("acks=all: the default since Kafka 3.0"), 0.5),
            "And because consumers",
            (lambda: self.cap("consumers never see a record that could vanish", GREEN_M), 0.5),
        ])

        # ---------------- scene 8: the guardrails ----------------
        self.steps("When the leader's broker fails, a follower takes over, but only one that has every committed record.", [
            (lambda: [*self.uncap(), self.lab["n0"][0].animate.set_stroke(RED_M), *[c.animate.set_opacity(0.2) for c in self.cells[0]]], 0.8),
            "a follower takes over",
            (lambda: [*self.put("n1", name_box(1, "broker 2", "new leader", GOLD_M), LEFT), *self.cap("a new leader must have every committed record")], 0.8),
        ])
        self.steps("Electing one that missed some would make them disappear without any error, because its shorter log becomes the truth. "
                   "That's an unclean leader election, and Kafka forbids it by default. "
                   "The partition stops taking writes instead of losing data.", [
            "Electing one",
            (lambda: [*[c.animate.set_opacity(0.25) for c in self.cells[2][5:8]], *self.drop("leo2")], 0.8),
            "That's an unclean",
            (lambda: self.cap("unclean leader election: forbidden by default", RED_M), 0.6),
            "The partition stops",
            (lambda: [*self.cap("no writes, rather than lost payments", RED_M)], 0.6),
        ])
        self.steps("And one gap in the house rule. If both assistants go home, the room is the owner alone. "
                   "Everyone in the room has copied every sale. It's a very small room.", [
            (lambda: [*self.uncap(), *[c.animate.set_opacity(1) for c in self.cells[0] + self.cells[2]],
                      self.lab["n0"][0].animate.set_stroke(GOLD_M), *self.put("n1", name_box(1, "broker 2", "follower", TEAL_M), LEFT),
                      *self.leo(2, 8)], 0.8),
            "If both assistants",
            (lambda: [*[VGroup(*self.cells[r], self.lab[f"n{r}"], self.lab[f"leo{r}"]).animate.set_opacity(0.2) for r in (1, 2)],
                      *self.put("room", room([0], "ISR: the leader alone"))], 1.0),
            "It's a very small",
            (lambda: [*self.cap("acks=all is met with one copy. The lesson's last section closes this gap.", RED_M)], 0.6),
        ])

        # ---------------- scene 9: moral, and a check ----------------
        self.steps("So: one leader decides the order, followers copy it, and a record counts once everyone in the room has it. "
                   "The room is the ISR, and the line is the high watermark.", [
            (lambda: [*[VGroup(*self.cells[r], self.lab[f"n{r}"], self.lab[f"leo{r}"]).animate.set_opacity(1) for r in (1, 2)],
                      *self.put("room", room([0, 1, 2])), *self.cap("one leader orders; followers copy", YELLOW_M, 28)], 1.0),
            "and a record counts",
            (lambda: self.cap("a record counts once everyone in the room has it", YELLOW_M, 28), 0.5),
            "The room is",
            (lambda: [glow(self.lab["room"][0], GOLD_M, 1.01), glow(self.lab["hw"][0], YELLOW_M, 1.02)], 0.9),
        ], after=0.5)
        self.steps("One quick check. The leader's end offset is 9, broker 2 is at 7, and broker 3 at 9, all in sync. "
                   "Where's the high watermark, and what can consumers read? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(prod), FadeOut(parr), *self.add_cells(0, [8], GOLD_M), *self.add_cells(2, [8], TEAL_M),
                      *self.drop("leo0", "leo2")], 0.8),
            (lambda: [*self.leo(0, 9), *self.leo(2, 9)], 0.4),
            "broker 2 is at 7",
            (lambda: [FadeOut(self.cells[1].pop()), *self.leo(1, 7, RED_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("7. Consumers can read up to offset 6. Broker 2 holds everyone back.", [
            (lambda: [*self.uncap(), *self.hw(7)], 0.8),
            "Consumers can read",
            (lambda: [LaggedStart(*[glow(self.cells[0][i][0], GREEN_M, 1.08) for i in range(7)], lag_ratio=0.1)], 1.0),
            "Broker 2 holds",
            (lambda: [Indicate(self.lab["leo1"], color=RED_M, scale_factor=1.3), *self.cap("the smallest end offset in the room sets the line", YELLOW_M, 28)], 0.8),
        ], after=0.3)
        self.wait(2.0)
