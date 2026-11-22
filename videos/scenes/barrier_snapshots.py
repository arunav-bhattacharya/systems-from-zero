from sfz import *

SAY.insert(0, (r"\bB1\b", "B one"))
SAY.insert(0, (r"\bChandy\b", "Chandee"))
SAY.insert(0, (r"\bFlink's\b", "Flinks"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
SRC_X, SRC_Y = -5.65, [1.5, -1.0]
LANE_X0, LANE_X1 = -4.8, -0.98
FRONT_X, PITCH = -1.5, 0.62
CNT = np.array([0.0, 0.25, 0])
CNT_W, CNT_H = 1.9, 3.6
SINK = np.array([3.85, 0.25, 0])
SINK_LANE = (1.0, 2.8)
STORE = np.array([3.85, -1.9, 0])
WORLD_Y = 1.62
CAP_Y, BAR_Y = -3.22, -2.72


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

    # --- small state helpers: each returns animations and records what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


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


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))



def rbox(c, w, h, color, fill=0.1):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color, fill), 1).move_to(c)


def rec(label, color=BLUE_M):
    r = RoundedRectangle(corner_radius=0.07, width=0.5, height=0.5, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.3), 1)
    return VGroup(r, M(label, 15).move_to(r)).set_z_index(3)


def barrier(label="B1"):
    r = Rectangle(width=0.16, height=0.7, stroke_width=0).set_fill(YELLOW_M, 1)
    g = VGroup(r, M(label, 16, YELLOW_M).next_to(r, UP, buff=0.08)).set_z_index(4)
    g.is_bar = True
    return g


def slot(i, k):
    return np.array([FRONT_X - PITCH * k, SRC_Y[i], 0])


class BarrierSnapshots(Base):
    """stream-07, section 1. The email that went twice. The desk with two shoeboxes, a tally and a note: consistent.
    Stop everything (seconds at every checkpoint). Flink: sources, a counter with two inputs, a sink, channels; a
    checkpoint. Barrier B1 at offsets 7 and 7; alignment (13 counted, input 0 blocked, then 14 = 7 + 7); the sink
    commits 14; the crash at 17 and the restore. Asynchronous barrier snapshotting, the limits, the moral, and a check
    (offsets 9 and 7: 16)."""

    # ---- queue helpers: self.ch[i] lists the chips in channel i, front first ----
    def place(self, i):
        return [m.animate.move_to(slot(i, k) + (0 if not getattr(m, "is_bar", False) else 0.1 * UP)) for k, m in enumerate(self.ch[i])]

    def push(self, i, m):
        m.move_to(slot(i, len(self.ch[i])) + 0.6 * LEFT)
        if getattr(m, "is_bar", False):
            m.shift(0.1 * UP)
        self.ch[i].append(m)
        return [FadeIn(m, shift=0.3 * RIGHT), *self.place(i)]

    def pop(self, i):
        m = self.ch[i].pop(0)
        return [m.animate.move_to(CNT + [-0.55, SRC_Y[i] - CNT[1], 0]).set_opacity(0), *self.place(i)]

    def counted(self, n, color=WHITE, note=None):
        g = VGroup(T(f"{n}", 44, color), T("counted", 20, GREY_B)).arrange(DOWN, buff=0.12).move_to(CNT)
        if note:
            g.add(fit(T(note, 17, YELLOW_M), CNT_W - 0.4).next_to(g, DOWN, buff=0.2))
        return self.put("cnt", g)

    def offset(self, i, n, color=GREY_B):
        return self.put(f"off{i}", T(f"offset {n}", 19, color).move_to([SRC_X, SRC_Y[i] - 0.68, 0]))

    def sink_txt(self, s, color=GREY_B):
        return self.put("sinkt", fit(T(s, 18, color), 1.8).move_to(SINK + [0, -0.35, 0]))

    def world(self, n, color=WHITE):
        return self.put("world", T(f"the world sees {n} updates", 20, color).move_to([SINK[0], WORLD_Y, 0]))

    def store(self, s, color=GREY_B):
        return self.put("store", fit(T(s, 19, color), 4.1).move_to(STORE + [0, -0.12, 0]))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.ch = [[], []]
        self.title_card("A coloured card in each shoebox", "snapshotting a program that never stops")

        # ---------------- scene 1: the email that went twice ----------------
        prog = rbox(CNT, CNT_W + 1.0, 2.0, WHITE, 0.0)
        prog_t = T("counting program", 20).move_to(CNT + [0, 0.65, 0])
        email = chip("email: was this you?", GOLD_M, 20).move_to(SINK + [0, 0.35, 0])
        email2 = chip("email: was this you?", RED_M, 20).move_to(SINK + [0, -0.45, 0])
        self.steps("Picture a small program that counts every card's payments. When a card has paid ten times, "
                   "it emails the owner: was this you?", [
            (lambda: [FadeIn(prog), FadeIn(prog_t), *self.put("cnt", T("card-1: 9", 26).move_to(CNT + [0, -0.1, 0]))], 0.7),
            "When a card",
            (lambda: [*self.put("cnt", T("card-1: 10", 26, GOLD_M).move_to(CNT + [0, -0.1, 0]))], 0.5),
            "it emails",
            (lambda: [dot_run(CNT + [1.5, 0, 0], email.get_left(), GOLD_M, 0.5), FadeIn(email, shift=0.1 * RIGHT)], 0.7),
        ])
        self.steps("One busy Saturday its machine loses power. A minute later it's back, carrying on from where it last wrote down.", [
            "loses power",
            (lambda: [prog.animate.set_stroke(RED_M), *self.cap("power lost", RED_M)], 0.5),
            "A minute later",
            (lambda: [prog.animate.set_stroke(WHITE), *self.cap("back, from where it last wrote down")], 0.6),
        ])
        self.steps("On Monday, a customer calls: she got the same email twice, and the counts show some payments twice too.", [
            "the same email twice",
            (lambda: [dot_run(CNT + [1.5, 0, 0], email2.get_left(), RED_M, 0.5), FadeIn(email2, shift=0.1 * RIGHT),
                      *self.cap("the same email, twice", RED_M)], 0.8),
            "the counts show",
            (lambda: [*self.put("cnt", T("card-1: 12?", 26, RED_M).move_to(CNT + [0, -0.1, 0]))], 0.5),
        ])
        self.steps("So how do you save the place of a program that never stops, so that nothing counts twice?", [
            (lambda: self.cap("how do you save the place of a program that never stops?", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 2: the desk ----------------
        boxes = [VGroup(rbox([SRC_X, SRC_Y[i], 0], 1.7, 1.0, GOLD_M, 0.2), T(f"box {'AB'[i]}", 20, GOLD_M).move_to([SRC_X, SRC_Y[i], 0]))
                 for i in range(2)]
        sheet = VGroup(rbox(CNT, CNT_W, CNT_H, WHITE, 0.05), T("tally", 22).move_to(CNT + [0, 1.45, 0]))
        tally = VGroup(*[T(s, 20, GREY_A) for s in ("card-1: 3", "card-2: 6", "card-3: 5")]).arrange(DOWN, buff=0.25).move_to(CNT + [0, 0.1, 0])
        note = rbox(STORE, 4.4, 0.85, GOLD_M, 0.15)
        note_t = T("note: tally, box A at 7, box B at 7", 19, GOLD_M).move_to(STORE)

        def receipt(i):
            return dot_run([SRC_X + 0.9, SRC_Y[i], 0], CNT + [-0.95, SRC_Y[i] - CNT[1], 0], GOLD_M, 0.5)

        self.steps("Picture yourself at a desk, counting receipts from two shoeboxes, with a tally per card on a sheet.", [
            (lambda: [*self.uncap(), FadeOut(prog), FadeOut(prog_t), FadeOut(email), FadeOut(email2), *self.drop("cnt")], 0.5),
            "two shoeboxes",
            (lambda: [FadeIn(boxes[0]), FadeIn(boxes[1])], 0.6),
            "a tally",
            (lambda: [FadeIn(sheet), FadeIn(tally)], 0.6),
            (lambda: [LaggedStart(*[receipt(k % 2) for k in range(6)], lag_ratio=0.3)], 1.4),
        ])
        self.steps("Every so often, you write a note: the tally, and how far you've got in each box. After an interruption, you start again from the note.", [
            "you write a note",
            (lambda: [FadeIn(note), FadeIn(note_t)], 0.6),
            "After an interruption",
            (lambda: [glow(note, GOLD_M, 1.03)], 0.7),
        ])
        twice = T("5 receipts counted twice", 20, RED_M).move_to(CNT + [0, -2.1, 0])
        self.steps("But the note only works if the tally and the two places describe the same moment. If the tally includes "
                   "five receipts the note says you haven't reached, you'll count those five twice.", [
            "the same moment",
            (lambda: [glow(sheet[0], WHITE, 1.02), glow(note, GOLD_M, 1.03)], 0.8),
            "If the tally includes",
            (lambda: [LaggedStart(*[receipt(0) for _ in range(5)], lag_ratio=0.2)], 1.2),
            "count those five twice",
            (lambda: [FadeIn(twice)], 0.5),
        ])
        self.steps("A snapshot like that, where every record counted comes before the saved places and none after, is called consistent.", [
            "is called consistent",
            (lambda: [FadeOut(twice), *self.cap("consistent: everything counted comes before the saved places, none after", WHITE)], 0.7),
        ], after=0.3)

        # ---------------- scene 3: stop everything? ----------------
        stops = VGroup(*[T("stop", 22, RED_M).move_to([SRC_X, SRC_Y[i] + 0.75, 0]) for i in range(2)])
        self.steps("The easy way is to stop. Stop reading both boxes, finish what's in your hands, write the note, start again. It's consistent.", [
            "Stop reading",
            (lambda: [FadeIn(stops), boxes[0][0].animate.set_stroke(RED_M), boxes[1][0].animate.set_stroke(RED_M)], 0.6),
            "write the note",
            (lambda: [glow(note, GOLD_M, 1.03)], 0.6),
        ])
        self.steps("But a real program does this every few seconds, and every time, everything stops. "
                   "Wouldn't it be nice to take the note while the counting goes on?", [
            (lambda: self.cap("consistent, and everything stops at every note", RED_M), 0.6),
            "Wouldn't it be nice",
            (lambda: [FadeOut(stops), boxes[0][0].animate.set_stroke(GOLD_M), boxes[1][0].animate.set_stroke(GOLD_M),
                      *self.cap("wanted: take the note while the counting goes on", YELLOW_M)], 0.7),
        ], after=0.3)

        # ---------------- scene 4: the program, named ----------------
        srcs = [VGroup(rbox([SRC_X, SRC_Y[i], 0], 1.5, 0.9, BLUE_M, 0.18), T(f"source {i}", 20, BLUE_M).move_to([SRC_X, SRC_Y[i], 0]))
                for i in range(2)]
        lanes = [Line([LANE_X0, SRC_Y[i], 0], [LANE_X1, SRC_Y[i], 0], stroke_width=2, color=GREY_D) for i in range(2)]
        cnt_box = rbox(CNT, CNT_W, CNT_H, WHITE, 0.05)
        cnt_t = T("counter", 22).move_to(CNT + [0, 1.45, 0])
        ins = VGroup(*[T(f"input {i}", 15, GREY_B).move_to([CNT[0] - 0.42, SRC_Y[i] - 0.42, 0]) for i in range(2)])
        sink_lane = Line([SINK_LANE[0], SINK[1], 0], [SINK_LANE[1], SINK[1], 0], stroke_width=2, color=GREY_D)
        sink_b = rbox(SINK, 2.0, 1.6, GREEN_M, 0.1)
        sink_t = T("sink", 22, GREEN_M).move_to(SINK + [0, 0.35, 0])
        store_b = rbox(STORE, 4.4, 0.85, TEAL_M, 0.1)
        store_h = T("durable checkpoint storage", 15, TEAL_M).move_to(STORE + [0, 0.24, 0])

        self.steps("Flink is a program that runs stream jobs across many machines. A job is a chain of steps called operators.", [
            (lambda: [*self.uncap(), FadeOut(tally), FadeOut(note_t)], 0.5),
            "A job is a chain",
            (lambda: self.cap("Flink: runs stream jobs across many machines; a job is a chain of operators", WHITE), 0.6),
        ])
        self.steps("Sources read the input, here two Kafka logs of payments: those are the shoeboxes.", [
            "Sources read",
            (lambda: [*[ReplacementTransform(boxes[i], srcs[i]) for i in range(2)], *self.offset(0, 7), *self.offset(1, 7)], 0.8),
            "the shoeboxes",
            (lambda: self.cap("shoeboxes = sources, each reading a Kafka log"), 0.5),
        ])
        self.steps("A counter keeps the count per card: that's the tally. A sink, the last step, writes results out to the world.", [
            "A counter",
            (lambda: [ReplacementTransform(sheet, VGroup(cnt_box, cnt_t)), FadeIn(ins), *self.counted(9),
                      *self.cap("tally = the counter: a count per card")], 0.8),
            "A sink",
            (lambda: [FadeIn(sink_b), FadeIn(sink_t), FadeIn(sink_lane), *self.sink_txt("open: 8 updates"), *self.world(0),
                      *self.cap("sink: writes results out to the world")], 0.8),
        ])
        u = rec("u", GREEN_M).move_to([1.9, SINK[1], 0])
        self.steps("Between two steps runs a channel, a queue where records wait in the order they were sent.", [
            "a channel",
            (lambda: [Create(lanes[0]), Create(lanes[1])], 0.5),
            (lambda: [*self.push(0, rec("c1")), *self.push(1, rec("c3"))], 0.35),
            (lambda: [*self.push(0, rec("c2")), *self.push(1, rec("c2")), FadeIn(u)], 0.35),
            (lambda: [*self.push(0, rec("c3"))], 0.35),
            "in the order",
            (lambda: self.cap("channel: a queue between two steps; the front is on the right"), 0.6),
        ])
        # the queue was filled back to front; reverse so the front (right) is first
        self.ch[0].reverse()
        self.ch[1].reverse()
        self.play(*self.place(0), *self.place(1), run_time=0.3)
        self.steps("Every few seconds, Flink saves every operator's state and every source's offset. "
                   "That saved snapshot is called a checkpoint: the note.", [
            (lambda: [ReplacementTransform(note, store_b), FadeIn(store_h), *self.store("no checkpoint yet")], 0.7),
            "a checkpoint",
            (lambda: self.cap("checkpoint: every operator's state + every source's offset = the note", WHITE), 0.6),
        ], after=0.3)
        self.stamp("named")

        # ---------------- scene 5: a coloured card ----------------
        b0, b1 = barrier(), barrier()
        self.steps("Here's the trick, from Chandy and Lamport in 1985. Slip a coloured card into each shoebox. Flink calls it a barrier.", [
            (lambda: self.cap("the trick (Chandy and Lamport, 1985): a coloured card in each box", WHITE), 0.6),
            "Flink calls it",
            (lambda: self.cap("Flink calls the card a barrier", YELLOW_M), 0.5),
        ])
        self.steps("It starts checkpoint 1: each source writes down its offset, 7 and 7, and puts barrier B1 into its channel, "
                   "behind the records it has already sent.", [
            "each source writes",
            (lambda: [*self.store("checkpoint 1 started: offsets 7, 7", TEAL_M), glow(self.lab["off0"], YELLOW_M, 1.2),
                      glow(self.lab["off1"], YELLOW_M, 1.2)], 0.7),
            "puts barrier B1",
            (lambda: [*self.push(0, b0), *self.push(1, b1)], 0.8),
        ])
        self.steps("Barriers never overtake records, so B1 splits each channel into before the checkpoint and after it. "
                   "And nothing stops. The sources keep reading.", [
            "splits each channel",
            (lambda: [*self.cap("right of B1: before checkpoint 1.   left of B1: after"),
                      *[glow(m[0], BLUE_M, 1.15) for m in self.ch[0][:3] + self.ch[1][:2]]], 0.9),
            "nothing stops",
            (lambda: [glow(srcs[0][0], BLUE_M, 1.05), glow(srcs[1][0], BLUE_M, 1.05)], 0.6),
        ], after=0.3)

        # ---------------- scene 6: the first card arrives ----------------
        self.steps("B1 reaches the counter on input 0 first. Input 1 still has a record ahead of its B1.", [
            (lambda: [*self.uncap(), *self.pop(0), *self.pop(1), *self.counted(11), *self.sink_txt("open: 10 updates")], 0.5),
            (lambda: [*self.pop(0), *self.counted(12)], 0.4),
            (lambda: [*self.pop(0), *self.counted(13, WHITE, "B1 seen on input 0"), *self.sink_txt("open: 12 updates")], 0.5),
            "Input 1 still",
            (lambda: [glow(self.ch[1][0][0], BLUE_M, 1.2)], 0.6),
        ])
        n1, n2, n3 = rec("c1"), rec("c2"), rec("c3")
        self.steps("Two new records from source 0 are queuing behind the barrier. Should the counter read them? Pause and guess.", [
            (lambda: [*self.push(0, n1), *self.offset(0, 8)], 0.4),
            (lambda: [*self.push(0, n2), *self.push(1, n3), *self.offset(0, 9), *self.offset(1, 8)], 0.4),
            "Should the counter",
            (lambda: self.cap("read the two records behind B1?  pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Let's steelman yes. Reading never stops, which is the whole point. But those two records come after offset 7.", [
            (lambda: [*self.cap("steelman: yes, keep reading", PURPLE_M)], 0.5),
            "come after offset 7",
            (lambda: [glow(n1[0], RED_M, 1.2), glow(n2[0], RED_M, 1.2), *self.cap("but they come after offset 7", WHITE)], 0.7),
        ])
        self.steps("Count them now, save, and after a crash the source rewinds to 7 and counts them again. That's the five receipts from the desk.", [
            "counts them again",
            (lambda: self.cap("count them now, and a restore counts them again", RED_M), 0.6),
        ])
        blocked = VGroup(T("blocked", 18, RED_M)).move_to([-2.75, SRC_Y[0] + 0.5, 0])
        self.steps("So the counter blocks input 0, and keeps reading input 1.", [
            "blocks input 0",
            (lambda: [lanes[0].animate.set_color(RED_M), FadeIn(blocked), *self.cap("block input 0; keep reading input 1", WHITE)], 0.6),
        ])
        self.steps("At the desk, you reach the coloured card in box A, so you stop taking from box A until you reach the card in box B. "
                   "This waiting is called alignment.", [
            "This waiting",
            (lambda: self.cap("alignment: wait at the first barrier until the other arrives", YELLOW_M), 0.6),
        ])
        snap = Dot(radius=0.1, color=TEAL_M).set_z_index(7)
        self.steps("B1 arrives on input 1. The counter has counted exactly 14 records: 7 from each source, 7 plus 7, the offsets in the note.", [
            (lambda: [*self.uncap(), *self.pop(1), *self.counted(14, WHITE, "B1 on both inputs"), *self.sink_txt("open: 14 updates")], 0.6),
            "exactly 14",
            (lambda: [*self.counted(14, YELLOW_M, "= 7 + 7"), *self.cap("14 counted = 7 + 7, the saved offsets", YELLOW_M)], 0.7),
        ])
        sb = barrier()
        sb.move_to([SINK_LANE[0] + 0.3, SINK[1] + 0.1, 0])
        self.steps("It saves its state, sends one B1 on to the sink, and unblocks input 0.", [
            "saves its state",
            (lambda: [dot_run(CNT + [0.5, -1.4, 0], STORE + [-2.0, 0.1, 0], TEAL_M, 0.7)], 0.75),
            (lambda: [*self.store("checkpoint 1: offsets 7, 7, counter 14", TEAL_M)], 0.5),
            "sends one B1",
            (lambda: [FadeOut(self.ch[0].pop(0)), FadeOut(self.ch[1].pop(0)), FadeIn(sb, shift=0.2 * RIGHT), FadeOut(u), *self.place(0), *self.place(1)], 0.6),
            "unblocks",
            (lambda: [lanes[0].animate.set_color(GREY_D), FadeOut(blocked), *self.counted(14)], 0.5),
        ], after=0.3)
        self.stamp("aligned")

        # ---------------- scene 7: commit, crash, restore ----------------
        self.steps("B1 reaches the sink. The sink has held its 14 updates in an open transaction, a batch that nobody outside can see until it's committed.", [
            (lambda: [sb.animate.move_to([SINK_LANE[1] - 0.35, SINK[1] + 0.1, 0])], 0.7),
            "an open transaction",
            (lambda: [*self.sink_txt("open: 14 updates", GREEN_M), glow(sink_b, GREEN_M, 1.04)], 0.7),
        ])
        self.steps("Every operator has now saved its part, so checkpoint 1 is complete, and the sink commits. The world sees 14 updates.", [
            "checkpoint 1 is complete",
            (lambda: [FadeOut(sb), *self.store("checkpoint 1 complete: offsets 7, 7, counter 14", TEAL_M)], 0.6),
            "the sink commits",
            (lambda: [*self.sink_txt("committed", GREEN_M)], 0.5),
            "The world sees",
            (lambda: [*self.world(14, GREEN_M)], 0.5),
        ])
        crash = T("crash", 30, RED_M).move_to([-2.6, 0.25, 0]).set_z_index(9)
        self.steps("Then the machine dies. The counter's 17, the channels and the sink's open batch are gone.", [
            (lambda: [*self.pop(0), *self.pop(1), *self.counted(16), *self.offset(0, 10), *self.offset(1, 9),
                      *self.sink_txt("open: 2 updates")], 0.5),
            (lambda: [*self.pop(0), *self.counted(17), *self.sink_txt("open: 3 updates")], 0.5),
            "the machine dies",
            (lambda: [FadeIn(crash, scale=1.3), cnt_box.animate.set_stroke(RED_M), sink_b.animate.set_stroke(RED_M)], 0.5),
            "are gone",
            (lambda: [*self.counted("?", RED_M, "state lost"), *self.sink_txt("open batch lost", RED_M),
                      *[FadeOut(m) for m in self.ch[0] + self.ch[1]], *self.cap("lost: the counter's 17, the channels, the open batch", RED_M)], 0.7),
        ])
        self.ch = [[], []]
        self.steps("The 3 updates after the checkpoint were never committed, so there's nothing to undo.", [
            "never committed",
            (lambda: [glow(self.lab["world"], GREEN_M, 1.06), *self.cap("the world still sees 14: nothing to undo", WHITE)], 0.7),
        ])
        self.steps("Every operator loads checkpoint 1, and each source rewinds to offset 7.", [
            (lambda: [FadeOut(crash), cnt_box.animate.set_stroke(WHITE), sink_b.animate.set_stroke(GREEN_M)], 0.4),
            "loads checkpoint 1",
            (lambda: [dot_run(STORE + [-2.0, 0.1, 0], CNT + [0.5, -1.4, 0], TEAL_M, 0.6)], 0.65),
            (lambda: [*self.counted(14, WHITE, "loaded"), *self.sink_txt("open: 0 updates")], 0.5),
            "rewinds to offset 7",
            (lambda: [*self.offset(0, 7, YELLOW_M), *self.offset(1, 7, YELLOW_M)], 0.6),
        ])
        self.steps("Those records are read again, and since none were in the 14, each is counted once. Records processed twice, effects shown once.", [
            "read again",
            (lambda: [*self.push(0, rec("c2")), *self.push(1, rec("c2"))], 0.5),
            (lambda: [*self.push(0, rec("c1"))], 0.4),
            "each is counted once",
            (lambda: [*self.pop(0), *self.pop(1), *self.counted(16), *self.offset(0, 8), *self.offset(1, 8)], 0.6),
            "Records processed twice",
            (lambda: self.cap("records processed twice, effects shown once", YELLOW_M), 0.6),
        ], after=0.4)
        self.stamp("restored")

        # ---------------- scene 8: names, and the limits ----------------
        env = chip("email: sent twice", RED_M, 18).move_to([SINK[0], WORLD_Y + 0.62, 0])
        self.steps("Flink calls all this asynchronous barrier snapshotting. Asynchronous because each operator writes its state "
                   "to storage in the background while processing goes on.", [
            (lambda: self.cap("asynchronous barrier snapshotting", WHITE), 0.6),
            "Asynchronous because",
            (lambda: [*self.cap("asynchronous: state is written to storage in the background"),
                      dot_run(CNT + [0.5, -1.4, 0], STORE + [-2.0, 0.1, 0], TEAL_M, 0.7)], 0.8),
        ])
        self.steps("Two limits. The desk picture breaks: you count alone and can pause whenever you like, "
                   "but Flink's operators run on different machines, so the barriers do the lining up.", [
            "The desk picture",
            (lambda: self.cap("where the desk breaks: operators on different machines never pause together", WHITE), 0.7),
            "the barriers do",
            (lambda: [*self.push(0, barrier("B2")), *self.push(1, barrier("B2"))], 0.6),
        ])
        self.steps("And waiting at the coloured card is still waiting; the next section measures it. "
                   "As for the email: it left the program before the restore, and no snapshot can call it back.", [
            "still waiting",
            (lambda: [lanes[0].animate(rate_func=there_and_back).set_color(RED_M), *self.cap("alignment is waiting: it has a cost", RED_M)], 0.8),
            "As for the email",
            (lambda: [FadeIn(env, shift=0.1 * UP), *self.cap("an email leaves the program: no checkpoint can take it back", RED_M)], 0.7),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: a marker in every stream splits it into before and after, "
                   "and a step with two inputs waits for both markers before it saves.", [
            (lambda: [FadeOut(env), *self.cap("a marker splits each stream; two inputs wait for both before saving", YELLOW_M, 26)], 0.7),
        ])
        self.steps("Then the count always equals the sum of the saved offsets.", [
            (lambda: self.cap("records counted = the sum of the saved offsets", YELLOW_M, 28), 0.6),
        ], after=0.3)
        self.steps("One quick check. A checkpoint saved offsets 9 and 7. How many records does the counter's saved count hold? Pause and think.", [
            (lambda: [*self.uncap(), *self.store("checkpoint 2: offsets 9, 7, counter ?", TEAL_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("16. 9 plus 7.", [
            (lambda: [*self.uncap(), *self.store("checkpoint 2: offsets 9, 7, counter 16", YELLOW_M)], 0.6),
        ], after=0.4)
        self.play(*self.cap("16 = 9 + 7: the count and the places describe one moment", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
