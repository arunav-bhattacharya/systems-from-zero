from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\bV(\d)\b", lambda m: "V " + "zero one two three four five six seven eight nine".split()[int(m.group(1))]),
    (r"\bworker-(\d)\b", lambda m: "worker " + "zero one two three four five six seven eight nine".split()[int(m.group(1))]),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RAIL_Y, RAIL_X0, RAIL_X1 = 3.05, -6.3, -0.75
SLIP_Y, SLIP_W, SLIP_H = 2.6, 0.9, 0.5
RAIL_X = [-5.7, -4.6, -3.5, -2.4, -1.3]
B1, B2 = np.array([-4.6, 0.95, 0]), np.array([-1.6, 0.95, 0])     # the baristas (carriers)
BW, BH = 2.6, 1.5
MOUNT_DY = -0.4
BK, BKW, BKH = np.array([4.6, 0.95, 0]), 2.8, 1.5                 # the card's bank
HP, HPW, HPH = np.array([4.6, 2.75, 0]), 2.8, 0.9                 # the heap
PARK = HP + [0.55, 0, 0]
GRID_X0, GRID_Y, CELL, PITCH = -5.76, [-1.1, -1.5], 0.3, 0.36    # the kernel's 64 tasks
GRID_LAB_Y, LEG_Y = -0.62, -1.98
CAP_Y, BAR_Y = -2.75, -3.25


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
        if t > dur + 0.1:
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def slip(label, at, color=BLUE_M):
    r = RoundedRectangle(corner_radius=0.08, width=SLIP_W, height=SLIP_H, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.25), 1)
    return VGroup(r, M(label, 20)).move_to(at)


def rail_at(k):
    return np.array([RAIL_X[k], SLIP_Y, 0])


def mount_at(b):
    return b + [0, MOUNT_DY, 0]


def barista(c, name, sub):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    return VGroup(r, T(name, 20).move_to(c + [0, 0.5, 0]), M(sub, 16, GREY_B).move_to(c + [0, 0.17, 0]))


def cell_pos(i):
    row, col = divmod(i, 32)
    return np.array([GRID_X0 + CELL / 2 + col * PITCH, GRID_Y[row], 0])


def cell(i, color):
    return Square(CELL, stroke_color=color, stroke_width=1.5).set_fill(fillc(color, 0.55), 1).move_to(cell_pos(i))


class ThreadsContextSwitch(Base):
    """os-03, section 4. A barista who watches the milk; one thread per payment fills a 64-task container at 42 with an
    error that blames memory. Callbacks avoid waiting but lose plain code. A few baristas and a rail of slips: virtual
    threads mount on carriers (worker-1 TID 66, worker-2 TID 67), unmount to the heap on a wait, remount anywhere.
    10,000 virtual threads run on 37 tasks. Limits: the whole stack moves, pinning, not faster, one per job."""

    def set_cap_cells(self, cells):
        old, self.cells = self.cells, cells
        return [FadeOut(old)] if old is not None else []

    def construct(self):
        self.capm = None
        self.cells = None
        self.title_card("Virtual threads", "ten thousand waits on a few baristas")

        # ---------------- scene 1: the barista who watches the milk ----------------
        rail = Line([RAIL_X0, RAIL_Y, 0], [RAIL_X1, RAIL_Y, 0], stroke_width=3, color=GREY_B)
        rail_t = left_at(T("the line", 18, GREY_B), RAIL_X1 + 0.2, RAIL_Y)
        b1 = barista(B1, "barista", "")
        bank = VGroup(RoundedRectangle(corner_radius=0.14, width=BKW, height=BKH, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1).move_to(BK),
                      T("the card's bank", 22).move_to(BK + [0, 0.25, 0]), T("answers in 120 ms", 18, GREY_B).move_to(BK + [0, -0.25, 0]))
        s1 = slip("1", mount_at(B1))
        ask = Line(B1 + [BW / 2, 0, 0], BK - [BKW / 2, 0, 0])
        line_slips = [slip(str(k + 2), rail_at(k)) for k in range(4)]
        self.steps("Picture a café at the morning rush, with one barista. She takes an order, starts the milk, then stands and watches it.", [
            (lambda: [FadeIn(b1[0]), FadeIn(b1[1])], 0.7),
            "She takes",
            (lambda: [FadeIn(s1, shift=0.2 * DOWN)], 0.5),
            "starts the milk",
            (lambda: [FadeIn(bank)], 0.6),
            (lambda: [travel(ask, YELLOW_M, 0.8)], 0.9),
            "stands and watches",
            (lambda: [glow(b1[0], GREY_B, 1.03)], 0.8),
        ])
        self.steps("The line grows, and the only thing working is the machine.", [
            (lambda: [Create(rail), FadeIn(rail_t), LaggedStart(*[FadeIn(s, shift=0.15 * DOWN) for s in line_slips], lag_ratio=0.35)], 1.6),
            "the only thing",
            (lambda: [glow(bank[0], GOLD_M, 1.03)], 0.7),
        ])
        self.steps("The café's payments program does the same. Each payment waits about 120 milliseconds for the card's bank to say yes. "
                   "A thread that waits does nothing else.", [
            (lambda: self.cap("one payment: about 120 ms waiting for the bank"), 0.5),
            "A thread that waits",
            (lambda: [*self.cap("a thread that waits does nothing else", WHITE), glow(b1[0], GREY_B, 1.03)], 0.8),
        ])

        # ---------------- scene 2: one barista per customer ----------------
        b2 = barista(B2, "barista", "")
        s2 = line_slips[0]
        grid_t = left_at(T("the kernel's tasks in this container: limit 64", 18, GREY_B), GRID_X0, GRID_LAB_Y)
        empty = VGroup(*[Square(CELL, stroke_color=GREY_D, stroke_width=1.2).move_to(cell_pos(i)) for i in range(64)])
        self.steps("The easy fix is one barista per customer: one thread per payment. In Java that's a platform thread. "
                   "Each one is a task the kernel counts, with about 2 megabytes of stack set aside.", [
            (lambda: [*self.uncap(), FadeIn(b2)], 0.6),
            (lambda: [s2.animate.move_to(mount_at(B2))], 0.7),
            "a platform thread",
            (lambda: self.cap("one barista per customer: one platform thread per payment", WHITE), 0.5),
            "Each one is a task",
            (lambda: [FadeIn(grid_t), Create(empty, lag_ratio=0.02)], 1.2),
            "2 megabytes",
            (lambda: self.cap("each one: a task, and about 2 MB of stack set aside"), 0.5),
        ])
        self.steps("Now 10,000 payments wait at once. That's 10,000 tasks and about 20 gigabytes of stack addresses, mostly to watch milk steam.", [
            (lambda: self.cap("10,000 waiting payments: 10,000 tasks, about 20 GB of stack addresses"), 0.6),
            "mostly to watch",
            (lambda: [glow(b1[0], GREY_B, 1.03), glow(b2[0], GREY_B, 1.03)], 0.8),
        ])
        own = VGroup(*[cell(i, GREY_B) for i in range(22)])
        pay = VGroup(*[cell(22 + i, BLUE_M) for i in range(42)])
        leg_own = left_at(T("shell and the JVM's own: 22", 18, GREY_B), GRID_X0, LEG_Y)
        leg_pay = left_at(T("payment threads: 42", 18, BLUE_M), -1.6, LEG_Y)
        self.steps("In the lab, the program ran in a container that allows 64 tasks. Watch the count. "
                   "The shell and the JVM's own threads take about 22. The payments get 42.", [
            (lambda: self.uncap(), 0.3),
            "Watch the count",
            (lambda: [glow(empty, YELLOW_M, 1.0)], 0.6),
            "The shell and",
            (lambda: [LaggedStart(*[FadeIn(c) for c in own], lag_ratio=0.15), FadeIn(leg_own)], 1.2),
            "The payments get",
            (lambda: [LaggedStart(*[FadeIn(c) for c in pay], lag_ratio=0.15), FadeIn(leg_pay)], 1.8),
        ])
        bad = Square(CELL, stroke_color=RED_M, stroke_width=2).set_fill(fillc(RED_M, 0.5), 1).move_to(cell_pos(31) + [PITCH + 0.12, 0, 0])
        badx = tick(False, 0.12).move_to(bad)
        heap = VGroup(RoundedRectangle(corner_radius=0.12, width=HPW, height=HPH, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1).move_to(HP),
                      left_at(T("heap", 22, TEAL_M), HP[0] - HPW / 2 + 0.25, HP[1]))
        gauge = VGroup(Rectangle(width=1.5, height=0.24, stroke_color=GREY_B, stroke_width=1.5).move_to(HP + [0.45, 0, 0]),
                       Rectangle(width=0.08, height=0.24, stroke_width=0).set_fill(TEAL_M, 1).move_to(HP + [0.45 - 0.71, 0, 0]))
        self.steps("The next one fails, with an error that blames memory. But memory sat nearly empty. The kernel had refused a new task.", [
            (lambda: [FadeIn(bad), Create(badx), *self.cap("OutOfMemoryError: unable to create native thread", RED_M)], 0.7),
            "But memory",
            (lambda: [FadeIn(heap), FadeIn(gauge)], 0.6),
            (lambda: [glow(heap[0], TEAL_M, 1.04)], 0.6),
            "The kernel had",
            (lambda: [*self.cap("the kernel refused a new task: the limit was full", WHITE), glow(VGroup(*own, *pay), RED_M, 1.0)], 0.8),
        ], after=0.4)

        # ---------------- scene 3: never wait? ----------------
        code = VGroup(M("askBank(payment)", 20), M("  .thenCompose(r -> save(r))", 20), M("  .thenAccept(r -> reply(r));", 20))
        for i, c in enumerate(code):
            left_at(c, -5.6 + (0.35 if i else 0), 1.5 - 0.45 * i)
        where = left_at(T("it failed. Where?", 20, RED_M), 0.6, 1.05)
        cafe = VGroup(b1, b2, s1, s2, *line_slips[1:], rail, rail_t)
        self.steps("One way out is never to wait: hand over a function to run when the answer comes, and move on.", [
            (lambda: [*self.uncap(), FadeOut(cafe), FadeOut(bad), FadeOut(badx), FadeOut(gauge),
                      VGroup(own, pay, leg_own, leg_pay, grid_t).animate.set_opacity(0.25), empty.animate.set_stroke(opacity=0.25)], 0.8),
            "hand over",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in code], lag_ratio=0.4)], 1.2),
        ])
        self.steps("It works, but the code turns into chains of callbacks, and when something fails, the error no longer shows the path that led there.", [
            "chains of callbacks",
            (lambda: [Indicate(code[1], color=YELLOW_M, scale_factor=1.04), Indicate(code[2], color=YELLOW_M, scale_factor=1.04)], 0.9),
            "when something fails",
            (lambda: [FadeIn(where, shift=0.1 * LEFT)], 0.6),
        ])
        self.steps("What we want is plain code that waits, top to bottom, without a kernel task for every wait.", [
            (lambda: self.cap("the wish: plain code that waits, without a task for every wait", WHITE), 0.6),
        ])

        # ---------------- scene 4: a few baristas and a rail ----------------
        rail_t2 = left_at(T("the rail", 18, GREY_B), RAIL_X1 + 0.2, RAIL_Y)
        slips = [slip(str(k + 1), rail_at(k)) for k in range(5)]
        b1, b2 = barista(B1, "barista", ""), barista(B2, "barista", "")
        self.steps("Back to the café. Keep two baristas, and give them a rail of order slips.", [
            (lambda: [*self.uncap(), FadeOut(code), FadeOut(where)], 0.5),
            "Keep two",
            (lambda: [FadeIn(b1), FadeIn(b2)], 0.6),
            "a rail of",
            (lambda: [Create(rail), FadeIn(rail_t2), LaggedStart(*[FadeIn(s, shift=0.15 * DOWN) for s in slips], lag_ratio=0.25)], 1.2),
        ])
        ask2 = Line(B2 + [BW / 2, 0, 0], BK - [BKW / 2, 0, 0])
        pin_t = T("pinned up by the machine", 17, GREY_B)
        pin_t.move_to([HP[0] - HPW / 2 - 0.25 - pin_t.width / 2, HP[1], 0])
        self.steps("A barista takes a slip and starts the milk. Then, instead of watching it, she pins the slip up by the machine, and takes the next one.", [
            (lambda: [slips[0].animate.move_to(mount_at(B1)), slips[1].animate.move_to(mount_at(B2))], 0.8),
            "starts the milk",
            (lambda: [travel(ask2, YELLOW_M, 0.7)], 0.8),
            "she pins",
            (lambda: [slips[1].animate.move_to(PARK), FadeIn(heap[0]), FadeIn(pin_t)], 0.8),
            "takes the next",
            (lambda: [slips[2].animate.move_to(mount_at(B2))], 0.7),
        ])
        self.steps("When the milk is ready, that slip goes back in line, and whichever barista is free picks it up.", [
            "When the milk",
            (lambda: [travel(Line(BK + [0, BKH / 2, 0], HP - [0, HPH / 2, 0]), GREEN_M, 0.6)], 0.7),
            "goes back in line",
            (lambda: [slips[1].animate.move_to(rail_at(4)), slips[3].animate.move_to(rail_at(0)), slips[4].animate.move_to(rail_at(1))], 0.9),
            "whichever barista",
            (lambda: [FadeOut(slips[0], shift=0.3 * DOWN)], 0.4),
            (lambda: [slips[3].animate.move_to(mount_at(B1))], 0.6),
        ])
        tag_b = T("a few real threads", 18, YELLOW_M).move_to([(B1[0] + B2[0]) / 2, B1[1] - BH / 2 - 0.27, 0])
        tag_s = left_at(T("the payments", 18, YELLOW_M), RAIL_X1 + 0.2, RAIL_Y - 0.4)
        tag_m = T("the wait for the bank", 18, YELLOW_M).move_to(BK + [0, -BKH / 2 - 0.27, 0])
        self.steps("Map it. The baristas are a few real threads, the kind the kernel runs. The slips are the payments. "
                   "And the steaming milk is the wait for the bank.", [
            (lambda: [FadeOut(pin_t)], 0.3),
            "The baristas are",
            (lambda: [FadeIn(tag_b, shift=0.1 * UP), glow(b1[0], YELLOW_M, 1.03), glow(b2[0], YELLOW_M, 1.03)], 0.7),
            "The slips are",
            (lambda: [FadeIn(tag_s), glow(slips[1][0], YELLOW_M, 1.1), glow(slips[4][0], YELLOW_M, 1.1)], 0.7),
            "the steaming milk",
            (lambda: [FadeIn(tag_m, shift=0.1 * UP), glow(bank[0], YELLOW_M, 1.03)], 0.7),
        ])

        # ---------------- scene 5: mount, unmount, mount again ----------------
        c1, c2 = barista(B1, "carrier worker-1", "TID 66"), barista(B2, "carrier worker-2", "TID 67")
        v1, v2, v3 = slip("V1", mount_at(B1)), slip("V2", mount_at(B2)), slip("V3", rail_at(0))
        heap_l = left_at(T("heap", 22, TEAL_M), HP[0] - HPW / 2 + 0.25, HP[1])
        self.steps("Java has worked this way since JDK 21. The slips are called virtual threads.", [
            (lambda: [FadeOut(VGroup(tag_b, tag_s, tag_m)), FadeOut(VGroup(slips[1], slips[2], slips[3], slips[4]))], 0.6),
            (lambda: [FadeIn(v1), FadeIn(v2), FadeIn(v3)], 0.6),
            "virtual threads",
            (lambda: [*self.cap("virtual threads: the slips", WHITE), swap(rail_t2, left_at(T("the queue", 18, GREY_B), RAIL_X1 + 0.2, RAIL_Y))], 0.6),
        ])
        self.steps("A virtual thread is a Java object, not a kernel task. To run, it mounts on a carrier: "
                   "an ordinary platform thread from a small pool the JVM keeps, by default one per processor.", [
            "a Java object",
            (lambda: self.cap("a virtual thread: a Java object, not a kernel task"), 0.5),
            "it mounts",
            (lambda: [Transform(b1, c1), Transform(b2, c2)], 0.8),
            "an ordinary platform",
            (lambda: [*self.cap("a carrier: a platform thread, one per processor by default"), glow(b1[0], WHITE, 1.03), glow(b2[0], WHITE, 1.03)], 0.8),
        ])
        stack = VGroup(*[Rectangle(width=0.7, height=0.11, stroke_color=BLUE_M, stroke_width=1.5).set_fill(fillc(BLUE_M, 0.5), 1) for _ in range(4)]).arrange(DOWN, buff=0.04)
        self.steps("Watch V2. It asks the bank, and waits. The JVM unmounts it: it saves V2's stack, its place in the code, on the heap, and frees the carrier.", [
            (lambda: self.uncap(), 0.3),
            "It asks the bank",
            (lambda: [travel(ask2, YELLOW_M, 0.7)], 0.8),
            "The JVM unmounts",
            (lambda: [FadeIn(heap_l), v2.animate.move_to(PARK)], 0.9),
            "its place in the code",
            (lambda: [*self.cap("unmount: V2's stack is saved on the heap"), glow(heap[0], TEAL_M, 1.04)], 0.6),
            "frees the carrier",
            (lambda: [glow(b2[0], GREEN_M, 1.03)], 0.6),
        ])
        self.steps("worker-2 picks up V3 at once. The kernel noticed nothing: task 67 never stopped running.", [
            (lambda: [v3.animate.move_to(mount_at(B2))], 0.7),
            "The kernel noticed",
            (lambda: [Indicate(b2[2], color=YELLOW_M, scale_factor=1.2), *self.cap("to the kernel, task 67 never stopped running", WHITE)], 0.9),
        ])
        self.steps("When the bank answers, V2 goes back on the rail, and mounts on whichever carrier is free first. This time, that's worker-1.", [
            (lambda: [*self.uncap(), travel(Line(BK + [0, BKH / 2, 0], HP - [0, HPH / 2, 0]), GREEN_M, 0.6)], 0.7),
            "V2 goes back",
            (lambda: [v2.animate.move_to(rail_at(0))], 0.8),
            "whichever carrier",
            (lambda: [FadeOut(v1, shift=0.3 * DOWN)], 0.5),
            "This time",
            (lambda: [v2.animate.move_to(mount_at(B1))], 0.7),
        ], after=0.4)
        print(f"POSTER {self.renderer.time:.1f}")

        # ---------------- scene 6: the same limit, 10,000 waits ----------------
        many = VGroup(*[slip("", rail_at(k)).shift(0.06 * k * UP * 0) for k in range(5)])
        many_t = left_at(M("× 10,000", 22, YELLOW_M), RAIL_X[4] + SLIP_W / 2 + 0.3, SLIP_Y)
        self.steps("Now the lab again: the same container, the same limit of 64 tasks, and 10,000 payments, each on its own virtual thread. "
                   "How many tasks does the kernel see? Pause and guess.", [
            (lambda: [FadeOut(VGroup(own, pay, leg_own, leg_pay)), grid_t.animate.set_opacity(1), empty.animate.set_stroke(opacity=1)], 0.6),
            "and 10,000 payments",
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.1 * DOWN) for s in many], lag_ratio=0.2), FadeIn(many_t)], 0.9),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        helpers = VGroup(*[cell(i, GREY_B) for i in range(25)])
        carriers = VGroup(*[cell(25 + i, TEAL_M) for i in range(12)])
        leg_h = left_at(T("the JVM's helpers: 25", 18, GREY_B), GRID_X0, LEG_Y)
        leg_c = left_at(T("carriers: 12", 18, TEAL_M), -2.0, LEG_Y)
        leg_t = left_at(T("37 tasks", 18, WHITE), 1.0, LEG_Y)
        self.steps("37. All 10,000 started and waited at once. The kernel saw the JVM's usual helpers, plus one carrier per processor, 12 in the lab box.", [
            (lambda: [*self.cap("10,000 virtual threads, 37 tasks", WHITE)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(c) for c in helpers], lag_ratio=0.1)], 0.9),
            "The kernel saw",
            (lambda: [FadeIn(leg_h)], 0.4),
            "plus one carrier",
            (lambda: [LaggedStart(*[FadeIn(c) for c in carriers], lag_ratio=0.15), FadeIn(leg_c)], 1.0),
            (lambda: [FadeIn(leg_t)], 0.4),
        ])
        print(f"POSTER2 {self.renderer.time:.1f}")
        self.steps("It had no idea it was running a café. The waiting lived on the heap.", [
            "The waiting lived",
            (lambda: [glow(heap[0], TEAL_M, 1.04), *self.cap("the waiting lived on the heap, not in the kernel")], 0.8),
        ], after=0.5)

        # ---------------- scene 7: where the café breaks: pinning ----------------
        dim_k = VGroup(grid_t, helpers, carriers, leg_h, leg_c, leg_t)
        self.steps("Here the café picture breaks. An order slip is a few words. A virtual thread's slip is its whole stack, copied to the heap and back.", [
            (lambda: [*self.cap("where the café picture breaks"), dim_k.animate.set_opacity(0.3), empty.animate.set_stroke(opacity=0.3),
                      FadeOut(many), FadeOut(many_t)], 0.6),
            "its whole stack",
            (lambda: [FadeIn(stack.move_to(mount_at(B1) + [0, 0.55, 0]))], 0.5),
            "copied to the heap",
            (lambda: [stack.animate.move_to(PARK)], 0.6),
            "and back",
            (lambda: [stack.animate.move_to(mount_at(B1) + [0, 0.55, 0])], 0.6),
            (lambda: [FadeOut(stack)], 0.2),
        ])
        pin1 = VGroup(Circle(0.11, color=RED_M, stroke_width=3).set_fill(RED_M, 1), Line(UP * 0, DOWN * 0.22, color=RED_M, stroke_width=3).shift(0.11 * DOWN))
        pin2 = pin1.copy()
        pin1.move_to(mount_at(B1) + [SLIP_W / 2 + 0.25, 0, 0])
        pin2.move_to(mount_at(B2) + [SLIP_W / 2 + 0.25, 0, 0])
        v4 = slip("V4", rail_at(0))
        self.steps("And a few waits still hold on to the carrier. That's called pinning.", [
            (lambda: [*self.uncap(), FadeIn(v4)], 0.4),
            "hold on to",
            (lambda: [FadeIn(pin1, shift=0.1 * DOWN), v2[0].animate.set_stroke(RED_M)], 0.6),
            "called pinning",
            (lambda: self.cap("pinning: a wait that keeps the carrier", RED_M), 0.5),
        ])
        self.steps("In JDK 25, waiting inside a class's static initializer, code that runs once when a class is first used, still pins.", [
            (lambda: self.cap("JDK 25: waiting inside static { } still pins", RED_M), 0.5),
            "code that runs once",
            (lambda: self.cap("static { }: code that runs once, when a class is first used"), 0.5),
        ])
        self.steps("If every carrier gets pinned, no other virtual thread in the JVM can run, like baristas each stuck holding one cup.", [
            (lambda: [FadeIn(pin2, shift=0.1 * DOWN), v3[0].animate.set_stroke(RED_M)], 0.6),
            "no other",
            (lambda: [v4.animate.set_opacity(0.35), *self.cap("every carrier pinned: nothing else can run", RED_M)], 0.6),
            "stuck holding",
            (lambda: [glow(b1[0], RED_M, 1.03), glow(b2[0], RED_M, 1.03)], 0.8),
        ], after=0.4)

        # ---------------- scene 8: not faster ----------------
        self.steps("And virtual threads aren't faster. Java's own proposal says it plainly: Virtual threads are not faster threads.", [
            (lambda: [FadeOut(pin1), FadeOut(pin2), v2[0].animate.set_stroke(BLUE_M), v3[0].animate.set_stroke(BLUE_M),
                      v4.animate.set_opacity(1), *self.cap("they aren't faster")], 0.6),
            "Virtual threads are not",
            (lambda: self.cap("“Virtual threads are not faster threads.”  (JEP 444)", WHITE), 0.6),
        ])
        self.steps("They let far more tasks wait at once. So they suit a program that spends its time waiting, on a bank or a database. "
                   "A thread that's busy computing gains nothing.", [
            (lambda: self.cap("they let far more tasks wait at once"), 0.5),
            "So they suit",
            (lambda: [*self.cap("waiting on a bank or a database: yes", GREEN_M), glow(bank[0], GREEN_M, 1.03)], 0.6),
            "busy computing",
            (lambda: self.cap("busy computing: no gain", RED_M), 0.5),
        ])
        self.steps("And make a new one per job; don't keep them in a pool.", [
            (lambda: self.cap("one per job, never a pool", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        def flow():
            return [Succession(v2.animate(run_time=0.5).move_to(PARK), v4.animate(run_time=0.5).move_to(mount_at(B1)),
                               v2.animate(run_time=0.5).move_to(rail_at(0)))]

        self.steps("So how does one program wait on 10,000 payments? It stops giving every wait its own barista. "
                   "The waits sit on the rail, a few baristas do the work, and your code still reads top to bottom.", [
            (lambda: self.uncap(), 0.3),
            "It stops giving",
            (lambda: flow(), 1.5),
            "a few baristas",
            (lambda: [glow(b1[0], WHITE, 1.03), glow(b2[0], WHITE, 1.03)], 0.7),
            "your code still",
            (lambda: self.cap("a wait should free the barista", YELLOW_M, 30), 0.6),
        ], after=0.5)
        p1, p2 = pin1.copy(), pin2.copy()
        self.steps("One quick check. The lab box has 12 carriers. Twelve virtual threads each wait inside a static initializer. "
                   "What happens to the next virtual thread that wants to run? Pause and think.", [
            (lambda: self.cap("12 carriers, 12 waits inside static { }"), 0.5),
            "Twelve virtual",
            (lambda: [FadeIn(p1, shift=0.1 * DOWN), FadeIn(p2, shift=0.1 * DOWN), v4[0].animate.set_stroke(RED_M), v3[0].animate.set_stroke(RED_M)], 0.6),
            "the next virtual",
            (lambda: [glow(v2[0], YELLOW_M, 1.1)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        vx = tick(False, 0.13).next_to(v2, RIGHT, buff=0.15)
        self.steps("It waits. Every carrier is pinned, so nothing else can mount until one frees up.", [
            (lambda: [*self.uncap(), Create(vx), v2.animate.set_opacity(0.4)], 0.5),
            "Every carrier",
            (lambda: [glow(b1[0], RED_M, 1.03), glow(b2[0], RED_M, 1.03)], 0.8),
        ], after=0.3)
        self.play(*self.cap("a wait should free the barista", YELLOW_M, 30), run_time=0.6)
        self.wait(2.0)
