from sfz import *

SAY.insert(0, (r"\bepoll_wait\b", "ee poll wait"))
SAY.insert(0, (r"\bepoll_ctl\b", "ee poll control"))
SAY.insert(0, (r"\bepoll\b", "ee poll"))
SAY.insert(0, (r"\bEAGAIN\b", "E again"))
SAY.insert(0, (r"\bc([1-4])\b", r"C \1"))
SAY.insert(0, (r"\b1,335,566\b", "one million three hundred thirty-five thousand five hundred sixty-six"))
SAY.insert(0, (r"\b2,028\b", "two thousand and twenty-eight"))
SAY.insert(0, (r"\b2,000\b", "two thousand"))
SAY.insert(0, (r"\b7 a\.m\.", "seven A M"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PX, PW = -5.3, 2.4                     # the program: threads, later one event-loop thread
EX0, EX1 = -3.3, 0.1                   # the epoll instance, in the kernel
ECX = (EX0 + EX1) / 2
ROWS = [1.6, 0.7, -0.2, -1.1]          # connections c1 to c4
BELL_X, LAB_X = 0.8, 1.35
Q0, Q1 = 1.8, 6.45                     # each connection's receive queue
CW, CG = 0.36, 0.06
K0, K1, KB, KT = -3.55, 6.65, -2.35, 2.78  # the kernel's dashed outline
LP_Y, LP_H = 0.25, 2.7                 # the one thread's box
IL_Y, RL_Y = 1.0, -1.1                 # interest list and ready list centres
TOP_Y, CAP_Y, BAR_Y = 3.32, -3.25, -2.8
NAMES = ["c1", "c2", "c3", "c4"]


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def harrow(a, b, color=GREY_B, sw=3):
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2, max_stroke_width_to_length_ratio=10)


# ---- the pieces ----
def bell():
    pts = [(-0.17, -0.1), (0.17, -0.1), (0.12, 0.0), (0.1, 0.12), (0.05, 0.17), (-0.05, 0.17), (-0.1, 0.12), (-0.12, 0.0)]
    body = Polygon(*[[x, y, 0] for x, y in pts], stroke_color=GREY_B, stroke_width=2.5).set_fill("#1a1a1a", 1)
    clap = Dot([0, -0.16, 0], radius=0.045, color=GREY_B)
    knob = Dot([0, 0.21, 0], radius=0.035, color=GREY_B)
    return VGroup(body, clap, knob)


def row(k):
    y = ROWS[k]
    q = RoundedRectangle(corner_radius=0.08, width=Q1 - Q0, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill("#0d0d0d", 1)
    q.move_to([(Q0 + Q1) / 2, y, 0])
    return VGroup(M(NAMES[k], 22).move_to([LAB_X, y, 0]), q)


def cell_x(i):
    return Q0 + 0.14 + CW / 2 + i * (CW + CG)


def cell(k, i, color=GOLD_M):
    return Square(CW, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.5), 1).move_to([cell_x(i), ROWS[k], 0])


def chipm(s, color=WHITE, size=18):
    t = M(s, size, color)
    r = RoundedRectangle(corner_radius=0.07, width=t.width + 0.24, height=0.4, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r))


def slot_x(i):
    return EX0 + 0.62 + i * 0.73


class Epoll(Base):
    """os-11, section 1. 2,000 quiet card readers cost 2,028 threads and about 200 MB: a waiter standing by every table.
    One waiter asking "ready yet?" spins (the lesson's test: 1,335,566 failed reads and a full second of CPU for 8
    bytes). select and poll check every connection on every call. epoll is a bell on every table: an interest list
    filled once by epoll_ctl, a ready list the kernel fills, and epoll_wait returning only that. c3's 10 bytes; the
    event loop. Level- versus edge-triggered on c4's 10 KB read 4 KB at a time: 6 KB stranded; read until EAGAIN.
    Where the restaurant breaks, the moral, and a check (2,000 connections, 3 with data)."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def top(self, s, color=WHITE):
        new = T(s, 24, color).move_to([0, TOP_Y, 0])
        old, self.topm = self.topm, new
        return [swap(old, new)]

    def state(self, *lines):
        """Rewrite the thread's state lines (each a (text, color) pair)."""
        g = VGroup(*[T(s, 20, c) for s, c in lines]).arrange(DOWN, buff=0.16).move_to([PX, LP_Y - 0.25, 0])
        fit(g, PW - 0.3)
        old, self.stm = self.stm, g
        return [swap(old, g)]

    def countdown(self, secs=3.0, *extra):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar, rate_func=linear), *extra, run_time=secs)

    def ring(self, k, on=True):
        b = self.bells[k]
        if on:
            return [b[0].animate.set_stroke(YELLOW_M).set_fill(fillc(YELLOW_M, 0.6), 1), b[1].animate.set_color(YELLOW_M),
                    b[2].animate.set_color(YELLOW_M)]
        return [b[0].animate.set_stroke(GREY_B).set_fill("#1a1a1a", 1), b[1].animate.set_color(GREY_B), b[2].animate.set_color(GREY_B)]

    def shake(self, k):
        return Wiggle(self.bells[k], scale_value=1.15, rotation_angle=0.08 * TAU, n_wiggles=4)

    def arrive(self, k, n, start=0):
        """n cells slide in from the network on the right into connection k's queue."""
        cs = [cell(k, start + i) for i in range(n)]
        self.q[k] += cs
        return [LaggedStart(*[FadeIn(c, shift=(7.6 - c.get_x()) * LEFT * 0.35) for c in cs], lag_ratio=0.12)]

    def take(self, k, n):
        """The thread reads the first n cells of connection k's queue; the rest slide forward."""
        got, self.q[k] = self.q[k][:n], self.q[k][n:]
        target = np.array([PX, LP_Y - 1.0, 0])
        out = [LaggedStart(*[c.animate.move_to(target).scale(0.4).set_opacity(0) for c in got], lag_ratio=0.08)]
        out += [c.animate.move_to([cell_x(i), ROWS[k], 0]) for i, c in enumerate(self.q[k])]
        return out

    def to_ready(self, k):
        c = chipm(NAMES[k], YELLOW_M).move_to([BELL_X, ROWS[k], 0])
        self.ready[k] = c
        return [Succession(FadeIn(c, run_time=0.1), c.animate(run_time=0.6).move_to([slot_x(k), RL_Y - 0.25, 0]))]

    def wait_returns(self, k, keep=False):
        """epoll_wait hands back connection k: a copy flies to the thread (keep), or the chip itself leaves the list."""
        c = self.ready[k]
        if keep:
            c2 = c.copy()
            return [c2.animate.move_to([PX, LP_Y + 0.5, 0]).set_opacity(0)]
        self.ready[k] = None
        return [c.animate.move_to([PX, LP_Y + 0.5, 0]).set_opacity(0)]

    def construct(self):
        self.capm = self.topm = self.stm = None
        self.q = [[], [], [], []]
        self.ready = [None] * 4
        self.title_card("One waiter, a bell on every table", "how one thread waits on thousands of connections with epoll")

        # ---------------- scene 1: a quiet Sunday ----------------
        kern = DashedVMobject(RoundedRectangle(corner_radius=0.2, width=K1 - K0, height=KT - KB, stroke_color=GREY_C, stroke_width=2),
                              num_dashes=90).move_to([(K0 + K1) / 2, (KT + KB) / 2, 0])
        kern_t = left_at(T("kernel", 22, GREY_B), K0 + 0.25, KT - 0.26)
        prog_t = T("the program", 22, GREY_B).move_to([PX, KT - 0.26, 0])
        rows = [row(k) for k in range(4)]
        more = T("and 1,996 more connections", 20, GREY_B).move_to([(Q0 + Q1) / 2 - 0.3, -1.78, 0])
        rq_t = T("receive queues", 18, GREY_B).move_to([(Q0 + Q1) / 2, ROWS[0] + 0.48, 0])
        self.steps("A quiet Sunday morning. Card readers in 2,000 coffee shops stay connected to the payments program all day, "
                   "ready to send a payment.", [
            "Card readers",
            (lambda: [Create(kern), FadeIn(kern_t), LaggedStart(*[FadeIn(r, shift=0.1 * LEFT) for r in rows], lag_ratio=0.15),
                      FadeIn(more)], 1.2),
            "stay connected",
            (lambda: [FadeIn(rq_t), *self.top("2,000 card readers, connected all day")], 0.6),
        ])
        self.steps("At 7 a.m., hardly anyone buys coffee. The program has almost nothing to do, yet it holds about 200 MB of memory. "
                   "Why does waiting cost so much?", [
            "The program has",
            (lambda: [FadeIn(prog_t)], 0.5),
            "yet it holds",
            (lambda: self.top("2,000 card readers · about 200 MB of memory"), 0.6),
            "Why does waiting",
            (lambda: [Indicate(self.topm, color=YELLOW_M, scale_factor=1.06), *self.cap("why does waiting cost so much?", WHITE)], 0.8),
        ], after=0.4)

        # ---------------- scene 2: a waiter for every table ----------------
        tb = []
        for k in range(4):
            r = RoundedRectangle(corner_radius=0.1, width=PW, height=0.56, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M), 1)
            r.move_to([PX, ROWS[k], 0])
            tb.append(VGroup(r, left_at(M(f"T{k + 1}", 20), PX - PW / 2 + 0.18, ROWS[k]),
                             left_at(T("asleep in read()", 17, GREY_B), PX - PW / 2 + 0.62, ROWS[k])))
        ties = [DashedLine([PX + PW / 2 + 0.06, ROWS[k], 0], [LAB_X - 0.35, ROWS[k], 0], dash_length=0.08, stroke_width=1.6, color=GREY_C)
                for k in range(4)]
        tmore = T("and 1,996 more threads", 20, GREY_B).move_to([PX, -1.78, 0])
        self.steps("The simple way is a restaurant where every table has its own waiter, standing by until the guests decide.", [
            (lambda: [*self.uncap()], 0.3),
            "every table",
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(tb[k]), Create(ties[k])) for k in range(4)], lag_ratio=0.2)], 1.2),
        ])
        self.steps("The waiter is a thread, one line of work the operating system runs. The table is a connection.", [
            (lambda: [*self.cap("the waiter: a thread", BLUE_M), glow(tb[0][0], BLUE_M, 1.03)], 0.7),
            "The table is",
            (lambda: [*self.cap("the table: a connection", WHITE), Indicate(rows[0][0], color=YELLOW_M)], 0.7),
        ])
        self.steps("Standing there is a blocking read: the kernel, the core of the operating system, puts the thread to sleep "
                   "until bytes arrive.", [
            (lambda: self.cap("standing by: a blocking read, asleep until bytes arrive", WHITE), 0.6),
            "puts the thread",
            (lambda: [LaggedStart(*[t[2].animate(rate_func=there_and_back).set_color(BLUE_M) for t in tb], lag_ratio=0.2)], 1.2),
        ])
        self.steps("Asleep, it uses no CPU, but each thread is a task with memory set aside. "
                   "2,000 card readers meant 2,028 threads and about 200 MB.", [
            (lambda: self.cap("asleep: no CPU.   but each thread has memory set aside", GREY_B), 0.6),
            "2,000 card readers",
            (lambda: [FadeIn(tmore), *self.top("2,000 connections · 2,028 threads · about 200 MB", GOLD_M)], 0.8),
        ], after=0.4)

        # ---------------- scene 3: ready yet? ----------------
        lp = RoundedRectangle(corner_radius=0.14, width=PW, height=LP_H, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1)
        lp.move_to([PX, LP_Y, 0])
        lp_t = T("one thread", 24).move_to([PX, LP_Y + LP_H / 2 - 0.35, 0])

        def trip(k, rt=0.5, color=YELLOW_M):
            a, b = np.array([PX + PW / 2, ROWS[k] if k is not None else LP_Y, 0]), np.array([LAB_X - 0.35, ROWS[k], 0])
            a = np.array([PX + PW / 2, LP_Y + 0.3, 0])
            d = Dot(a, radius=0.08, color=color)
            return Succession(FadeIn(d, run_time=0.03), d.animate(run_time=rt / 2, rate_func=linear).move_to(b),
                              d.animate(run_time=rt / 2, rate_func=linear).move_to(a).set_color(RED_M), FadeOut(d, run_time=0.03))

        self.steps("So try one waiter for every table. A read can be told never to wait: on an empty connection it fails at once, "
                   "with an error called EAGAIN, try again.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*tb, *ties, tmore)), FadeIn(lp), FadeIn(lp_t),
                      *self.top("one thread for all 2,000", WHITE)], 0.9),
            "fails at once",
            (lambda: [trip(1, 0.8)], 0.86),
            "with an error",
            (lambda: [*self.state(("EAGAIN: try again", RED_M))], 0.5),
        ])
        self.steps("The waiter runs from table to table: ready yet? Ready yet?", [
            (lambda: [LaggedStart(*[trip(k, 0.45) for k in (0, 1, 2, 3, 0, 1, 2, 3)], lag_ratio=0.5)], 2.6),
        ])
        vt = ValueTracker(0)
        cnt = always_redraw(lambda: M(f"{int(vt.get_value()):,}", 22, RED_M).move_to([PX, LP_Y - 0.55, 0]))
        cpu_lab = T("CPU", 18, GREY_B).move_to([PX - 0.7, LP_Y - 1.0, 0])
        cpu_box = Rectangle(width=1.1, height=0.24, stroke_color=GREY_B, stroke_width=1.5).move_to([PX + 0.38, LP_Y - 1.0, 0])
        cpu_fill = Rectangle(width=1.08, height=0.22, stroke_width=0).set_fill(RED_M, 0.85)
        left_at(cpu_fill, PX + 0.38 - 0.54, LP_Y - 1.0)
        self.steps("Here's a test with one connection that answers after one second. How much CPU does the waiter burn? Pause and guess.", [
            (lambda: [*self.state(("failed reads:", GREY_B)), *[r.animate.set_opacity(0.25) for r in rows[1:]], more.animate.set_opacity(0.25),
                      *self.top("a test: one connection, the answer after one second", WHITE)], 0.7),
            (lambda: [FadeIn(cnt), FadeIn(cpu_lab), Create(cpu_box)], 0.4),
            "How much CPU",
            (lambda: [LaggedStart(*[trip(0, 0.4) for _ in range(5)], lag_ratio=0.6)], 1.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0, LaggedStart(*[trip(0, 0.4) for _ in range(6)], lag_ratio=0.75))
        self.add(cnt)
        c8 = cell(0, 0)
        self.steps("All of it. A full second, and 1,335,566 failed reads, for 8 bytes the sleeping read got for free.", [
            (lambda: [*self.uncap(), GrowFromEdge(cpu_fill, LEFT), vt.animate.set_value(1335566),
                      LaggedStart(*[trip(0, 0.3) for _ in range(5)], lag_ratio=0.8)], 1.6),
            "for 8 bytes",
            (lambda: [FadeIn(c8, shift=0.6 * LEFT)], 0.5),
            (lambda: [c8.animate.move_to([PX, LP_Y + 0.3, 0]).scale(0.4).set_opacity(0)], 0.6),
            "the sleeping read",
            (lambda: self.cap("the sleeping read: the same 8 bytes, 0.00 s of CPU", GREY_B), 0.5),
        ])
        self.steps("Ready yet is a fine question once. Not a million times a second.", [
            "Not a million",
            (lambda: [Indicate(cnt, color=RED_M, scale_factor=1.15)], 0.8),
        ], after=0.4)

        # ---------------- scene 4: asking from a chair ----------------
        self.remove(c8)
        lst = chipm("c1 c2 c3 c4 … all 2,000", WHITE, 18).move_to([PX, LP_Y + 0.4, 0])
        sweep = SurroundingRectangle(rows[0], color=YELLOW_M, buff=0.08, corner_radius=0.08, stroke_width=3)
        self.steps("We want a call that sleeps until any connection in a set has data. The first answers, select and poll, "
                   "take the whole list every time, and the kernel checks every connection.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(cnt, cpu_lab, cpu_box, cpu_fill)), *self.state(),
                      *[r.animate.set_opacity(1) for r in rows[1:]], more.animate.set_opacity(1),
                      *self.top("wanted: sleep until any connection has data", WHITE)], 0.8),
            "select and poll",
            (lambda: [*self.state(("asleep in poll()", GREY_B)), FadeIn(lst)], 0.5),
            "take the whole list",
            (lambda: [lst.animate.move_to([ECX, 0.25, 0])], 0.8),
            "checks every",
            (lambda: [Create(sweep)], 0.3),
            (lambda: [Succession(*[sweep.animate(run_time=0.3).move_to(rows[k]) for k in (1, 2, 3)],
                                 sweep.animate(run_time=0.4).surround(more, buff=0.08))], 1.3),
        ])
        self.steps("With 2,000 connections and 3 active, every wake-up checks 2,000. Still asking every table, just from a chair.", [
            (lambda: [*self.cap("2,000 connections, 3 with data: every call checks 2,000", WHITE), FadeOut(sweep)], 0.6),
            "Still asking",
            (lambda: [glow(lst[0], YELLOW_M, 1.06)], 0.8),
        ], after=0.4)

        # ---------------- scene 5: a bell on every table ----------------
        self.bells = [bell().move_to([BELL_X, ROWS[k], 0]) for k in range(4)]
        ep = RoundedRectangle(corner_radius=0.14, width=EX1 - EX0, height=4.36, stroke_color=PURPLE_M, stroke_width=3).set_fill(fillc(PURPLE_M, 0.1), 1)
        ep.move_to([ECX, 0.0, 0])
        ep_t = T("epoll", 24, PURPLE_M).move_to([ECX, 1.95, 0])
        il = RoundedRectangle(corner_radius=0.1, width=EX1 - EX0 - 0.3, height=1.4, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
        il.move_to([ECX, IL_Y - 0.05, 0])
        il_t = T("interest list", 20, GREY_B).move_to([ECX, IL_Y + 0.38, 0])
        rl = RoundedRectangle(corner_radius=0.1, width=EX1 - EX0 - 0.3, height=1.25, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
        rl.move_to([ECX, RL_Y, 0])
        rl_t = T("ready list", 20, GREY_B).move_to([ECX, RL_Y + 0.38, 0])
        ichips = [chipm(NAMES[k], WHITE).move_to([slot_x(k), IL_Y - 0.1, 0]) for k in range(4)]
        imore = T("+ 1,996 more", 17, GREY_B).move_to([ECX, IL_Y - 0.55, 0])
        self.steps("Now put a bell on every table. The waiter registers each bell once, sits down, and walks only to the tables that rang.", [
            (lambda: [*self.uncap(), FadeOut(lst), *self.state(), *self.top("a bell on every table", WHITE)], 0.5),
            "a bell on every",
            (lambda: [LaggedStart(*[FadeIn(b, scale=0.5) for b in self.bells], lag_ratio=0.2)], 0.9),
            "sits down",
            (lambda: self.state(("sitting down", GREY_B)), 0.5),
            "walks only",
            (lambda: [*self.ring(2), self.shake(2)], 0.8),
            (lambda: self.ring(2, False), 0.3),
        ])
        self.steps("That's epoll, on Linux. epoll_ctl registers each connection once, in the kernel's interest list.", [
            (lambda: [FadeIn(ep), FadeIn(ep_t), *self.top("epoll: sign up once, then wait", WHITE)], 0.7),
            "epoll_ctl",
            (lambda: [FadeIn(il), FadeIn(il_t), *self.cap("epoll_ctl: sign each connection up, once", WHITE)], 0.5),
            (lambda: [LaggedStart(*[Succession(FadeIn(c.copy().move_to([PX, LP_Y + 0.3, 0]).set_opacity(0), run_time=0.01),
                                               FadeIn(c, shift=(c.get_x() - PX) * LEFT * 0.0 + 0.2 * RIGHT, run_time=0.5)) for c in ichips],
                                  lag_ratio=0.3), FadeIn(imore)], 1.3),
        ])
        self.steps("When bytes arrive, the kernel itself puts that connection on the ready list. "
                   "And epoll_wait sleeps until the ready list has something, then returns only that.", [
            "the ready list",
            (lambda: [FadeIn(rl), FadeIn(rl_t)], 0.5),
            "And epoll_wait",
            (lambda: [*self.state(("asleep in", GREY_B), ("epoll_wait", WHITE)), *self.cap("epoll_wait: sleep until the ready list has something", WHITE)], 0.6),
            "returns only that",
            (lambda: [glow(rl, YELLOW_M, 1.03)], 0.8),
        ], after=0.3)
        lp_t2 = T("event loop", 24).move_to(lp_t)

        # ---------------- scene 6: watch one request ----------------
        self.steps("Watch. 10 bytes arrive for c3. The kernel puts c3 on the ready list and wakes the thread. epoll_wait returns c3.", [
            (lambda: [*self.uncap(), *self.top("10 bytes arrive for c3", GOLD_M)], 0.4),
            "10 bytes arrive",
            (lambda: self.arrive(2, 1), 0.6),
            "The kernel puts",
            (lambda: [*self.ring(2), self.shake(2), *self.to_ready(2)], 0.8),
            "wakes the thread",
            (lambda: [glow(lp, YELLOW_M, 1.02), *self.state(("awake", YELLOW_M))], 0.6),
            "epoll_wait returns",
            (lambda: [*self.wait_returns(2), *self.state(("epoll_wait", GREY_B), ("returned: c3", YELLOW_M))], 0.7),
        ])
        self.steps("The thread reads the 10 bytes, reads again, gets EAGAIN, and goes back to sleep. It never touched c1, c2 or c4.", [
            (lambda: [*self.take(2, 1), *self.state(("read c3:", GREY_B), ("10 bytes", GREEN_M))], 0.7),
            "reads again",
            (lambda: [*self.state(("read c3 again:", GREY_B), ("EAGAIN", RED_M)), *self.ring(2, False)], 0.6),
            "goes back",
            (lambda: self.state(("asleep in", GREY_B), ("epoll_wait", WHITE)), 0.5),
            "It never touched",
            (lambda: [LaggedStart(*[Indicate(rows[k][0], color=GREY_B, scale_factor=1.2) for k in (0, 1, 3)], lag_ratio=0.3),
                      *self.cap("c1, c2, c4: never touched", GREY_B)], 1.0),
        ])
        self.steps("A thread living in this wait-and-handle cycle is called an event loop.", [
            (lambda: [swap(lp_t, lp_t2), *self.cap("an event loop: wait, handle what's ready, wait again", BLUE_M)], 0.7),
            (lambda: [glow(lp, BLUE_M, 1.02)], 0.7),
        ], after=0.4)

        # ---------------- scene 7: two ways to ring ----------------
        self.steps("The bell can ring in two ways, and the difference bites. 10 KB arrive on c4, and the loop reads only 4 KB.", [
            (lambda: [*self.uncap(), *self.top("10 KB arrive on c4", GOLD_M)], 0.4),
            "10 KB arrive",
            (lambda: [*self.arrive(3, 10)], 1.2),
            (lambda: [*self.ring(3), self.shake(3), *self.to_ready(3)], 0.8),
            "and the loop reads",
            (lambda: [*self.wait_returns(3, keep=True), *self.state(("epoll_wait", GREY_B), ("returned: c4", YELLOW_M))], 0.6),
            (lambda: [*self.take(3, 4), *self.state(("read c4:", GREY_B), ("4 KB, 6 KB left", GOLD_M))], 0.8),
        ])
        self.steps("By default, epoll is level-triggered: the bell keeps ringing while the table has anything left to order.", [
            (lambda: self.cap("level-triggered: rings while anything is left", WHITE), 0.6),
            "keeps ringing",
            (lambda: [self.shake(3), Indicate(self.ready[3], color=YELLOW_M)], 0.9),
            (lambda: [self.shake(3)], 0.8),
        ])
        self.steps("So the next epoll_wait returns c4 again, and the loop reads the rest.", [
            "returns c4 again",
            (lambda: [*self.wait_returns(3), *self.state(("epoll_wait", GREY_B), ("returned: c4 again", YELLOW_M))], 0.7),
            "reads the rest",
            (lambda: [*self.take(3, 6), *self.state(("read c4:", GREY_B), ("the other 6 KB", GREEN_M)), *self.ring(3, False)], 0.9),
        ], after=0.3)
        self.steps("Edge-triggered rings once, each time new data arrives. Same 10 KB, same 4 KB read, and the loop waits again.", [
            (lambda: [*self.cap("edge-triggered: rings once, when new data arrives", WHITE), *self.state(("asleep in", GREY_B), ("epoll_wait", WHITE))], 0.6),
            "Same 10 KB",
            (lambda: [*self.arrive(3, 10)], 1.0),
            (lambda: [*self.ring(3), self.shake(3), *self.to_ready(3)], 0.7),
            (lambda: [*self.wait_returns(3), *self.ring(3, False)], 0.6),
            "same 4 KB",
            (lambda: [*self.take(3, 4), *self.state(("read c4:", GREY_B), ("4 KB", GOLD_M))], 0.7),
            "the loop waits",
            (lambda: self.state(("asleep in", GREY_B), ("epoll_wait", WHITE)), 0.5),
        ])
        self.steps("What happens to the other 6 KB? Pause and guess.", [
            (lambda: [*self.top("6 KB still in c4's queue", GOLD_M), *[Indicate(c, color=GOLD_M, scale_factor=1.15) for c in self.q[3]]], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("They sit there. They aren't new, so epoll_wait sleeps.", [
            (lambda: [*self.uncap(), *[c.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.5), 1) for c in self.q[3]]], 0.6),
            "They aren't new",
            (lambda: [*self.cap("not new, so no ring: the loop sleeps on", RED_M), Indicate(self.stm, color=GREY_B)], 0.7),
        ])
        self.steps("And the client sent its whole request and waits for an answer, so nothing new will come. "
                   "The waiter took half the order and sat down.", [
            (lambda: [*self.top("the client sent everything and waits for an answer", WHITE)], 0.6),
            "nothing new",
            (lambda: self.cap("nothing new will come: 6 KB stranded", RED_M), 0.5),
            "half the order",
            (lambda: [glow(lp, RED_M, 1.02)], 0.8),
        ])
        self.steps("Edge-triggered wakes the loop less often, which some servers want. The rule for that code: on every event, read until EAGAIN.", [
            (lambda: self.cap("edge-triggered: fewer wake-ups", GREY_B), 0.5),
            "The rule",
            (lambda: [*self.cap("on every event, read until EAGAIN", YELLOW_M, 30),
                      *[c.animate.set_stroke(GOLD_M).set_fill(fillc(GOLD_M, 0.5), 1) for c in self.q[3]]], 0.6),
            (lambda: [*self.take(3, 4), *self.state(("read c4:", GREY_B), ("4 KB", GOLD_M))], 0.6),
            (lambda: [*self.take(3, 2), *self.state(("read c4:", GREY_B), ("2 KB", GOLD_M))], 0.6),
            (lambda: self.state(("read c4:", GREY_B), ("EAGAIN: done", GREEN_M)), 0.5),
        ], after=0.5)

        # ---------------- scene 8: where the restaurant breaks ----------------
        self.steps("Here the restaurant picture breaks. A bell is free, but every connection in the interest list costs the kernel a little memory.", [
            (lambda: [*self.top("where the restaurant picture breaks", WHITE), *self.cap("a bell: free", GREY_B),
                      *self.state(("asleep in", GREY_B), ("epoll_wait", WHITE))], 0.6),
            "but every connection",
            (lambda: [*self.cap("each connection in the interest list: a little kernel memory", WHITE), glow(il, YELLOW_M, 1.03)], 0.8),
        ])
        self.steps("And waiters are expensive, while threads are cheap until there are thousands. "
                   "Ten card readers can have a thread each. Thousands of quiet ones want an event loop.", [
            (lambda: self.cap("threads: cheap, until there are thousands", WHITE), 0.5),
            "Ten card readers",
            (lambda: self.cap("10 readers: a thread each is fine.   thousands: an event loop", WHITE), 0.6),
            "Thousands of quiet",
            (lambda: [glow(lp, BLUE_M, 1.02)], 0.8),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So why did a quiet Sunday cost 200 MB? Every connection had its own sleeping waiter.", [
            (lambda: [*self.uncap(), *self.top("why did a quiet Sunday cost 200 MB?", WHITE)], 0.5),
            "Every connection",
            (lambda: self.cap("2,000 connections, 2,028 sleeping threads", GOLD_M), 0.5),
        ])
        self.steps("epoll is one waiter and a bell on every table: sign up once, sleep, and walk only to the tables that rang.", [
            (lambda: self.cap("epoll: sign up once, sleep, handle only what rang", WHITE), 0.6),
            "sign up once",
            (lambda: [glow(il, WHITE, 1.03)], 0.7),
            "sleep",
            (lambda: [glow(lp, BLUE_M, 1.02)], 0.6),
            "walk only",
            (lambda: [glow(rl, YELLOW_M, 1.03)], 0.7),
        ], after=0.4)
        self.steps("One quick check. 2,000 connections, and 3 have data. How many does poll check, and how many does epoll_wait return? "
                   "Pause and think.", [
            (lambda: [*self.uncap(), *self.top("2,000 connections, 3 with data", WHITE)], 0.5),
            "3 have data",
            (lambda: [*self.arrive(0, 1), *self.arrive(1, 1), *self.arrive(3, 1)], 0.7),
            (lambda: [*self.ring(0), *self.ring(1), *self.ring(3), *self.to_ready(0), *self.to_ready(1), *self.to_ready(3)], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        sweep2 = SurroundingRectangle(rows[0], color=YELLOW_M, buff=0.08, corner_radius=0.08, stroke_width=3)
        self.steps("poll checks all 2,000. epoll_wait returns just the 3.", [
            (lambda: [*self.uncap(), Create(sweep2)], 0.3),
            (lambda: [Succession(*[sweep2.animate(run_time=0.25).move_to(rows[k]) for k in (1, 2, 3)],
                                 sweep2.animate(run_time=0.3).surround(more, buff=0.08)), *self.cap("poll: checks all 2,000", WHITE)], 1.05),
            "epoll_wait returns",
            (lambda: [FadeOut(sweep2), *[glow(self.ready[k][0], YELLOW_M, 1.1) for k in (0, 1, 3)],
                      *self.cap("poll: checks all 2,000.   epoll_wait: returns 3", YELLOW_M)], 0.8),
        ], after=0.4)
        self.wait(2.0)
