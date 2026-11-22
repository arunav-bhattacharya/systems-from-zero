from sfz import *

# A lone capital A (worker or server A) mid-sentence: Kokoro reads it as the article "uh". Sentence starts keep "A".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b", lambda m: m.group(0) if m.group(1) is not None else "eh"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
X0, TMAX = -4.0, 5200                   # x of 0 ms on the shared timeline, and its last ms
XS = 10.0 / TMAX                        # units per ms
A_Y, S_Y, B_Y, L_Y, AX_Y = 1.3, 0.4, -0.5, -1.35, -2.1   # lanes: worker A, lease service, worker B, ledger; the axis
GAP_Y = -0.93
TOP_Y = 2.75                             # A's loop, top left
ZX0, ZX1, Z_Y, ZMIN, ZMAX = -4.0, 3.0, 2.35, 1490, 1590  # the zoomed strip around the check
CAP_Y, BAR_Y = -3.25, -2.92


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

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
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def gather(self, g):
        """Make a group of parts already on screen into one object on screen, so it can be transformed as a whole."""
        self.remove(*g.submobjects)
        self.add(g)
        return g

    def col(self, c):
        self.sil_col = c
        return [Wait(0.01)]

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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])



def tx(ms):
    return X0 + XS * ms


def lane_label(s, y, color):
    return right_at(T(s, 21, color), X0 - 0.25, y)


def band(a, b, y, color, h=0.36, op=0.35):
    r = Rectangle(width=max(tx(b) - tx(a), 0.01), height=h, stroke_color=color, stroke_width=2).set_fill(fillc(color, op), 1)
    return r.move_to([(tx(a) + tx(b)) / 2, y, 0])


def tickm(ms, y, color, h=0.36, sw=3):
    return Line([tx(ms), y - h / 2, 0], [tx(ms), y + h / 2, 0], stroke_width=sw, color=color)


def face(c, s=1.0):
    head = Circle(radius=0.55 * s, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M, 0.25), 1).move_to(c)
    eyes = VGroup(*[Dot(radius=0.06 * s, color=GOLD_M).move_to(c + np.array([dx * s, 0.15 * s, 0])) for dx in (-0.2, 0.2)])
    mouth = Arc(radius=0.22 * s, start_angle=PI + 0.5, angle=PI - 1.0, stroke_color=GOLD_M, stroke_width=3).move_to(c + np.array([0, -0.2 * s, 0]))
    return VGroup(head, eyes, mouth)


class ProcessPause(Base):
    """dist-04, section 0. A friend freezes on a video call and answers a question everyone moved past. Worker A holds
    a 2-second lease on shop M-0042's ledger and loops: check, build (60 ms), write. The lab's run on one timeline: check
    at 1,500 ms (1.6 s left), the JVM stops A at 1,520 for 3 s, lease 1 runs out at 3,105, B gets lease 2 at 3,155 and
    writes from 3,320, A wakes at 4,520 and its update lands at 4,530, on top of 13 of B's. Check-then-act. The careful
    worker's second check catches a pause at 1,520 but not one at 1,562 (lands at 4,567). Guardrail, moral, check."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Frozen between the check and the write", "a program can't feel its own pause")

        # ---------------- scene 1: the frozen call ----------------
        tile = RoundedRectangle(corner_radius=0.2, width=4.4, height=3.0, stroke_color=WHITE, stroke_width=3).set_fill("#15191d", 1).move_to([0, 0.5, 0])
        fc = face(np.array([0, 0.75, 0]))
        nm = T("your friend", 18, GREY_B).move_to([-1.35, -0.7, 0])
        said = T("\"...and the best day for me is\"", 22, WHITE).move_to([0, -1.6, 0])
        self.steps("Picture a video call with a friend. Her picture freezes, halfway through a sentence.", [
            (lambda: [FadeIn(tile), FadeIn(fc), FadeIn(nm)], 0.7),
            "halfway",
            (lambda: [FadeIn(said)], 0.4),
            (lambda: [tile.animate.set_stroke(BLUE_M), *self.put("frz", T("frozen", 22, BLUE_M).move_to([1.5, -0.7, 0]))], 0.4),
        ])
        timer = ValueTracker(0)
        tnum = always_redraw(lambda: T(f"{int(timer.get_value())} s", 22, BLUE_M).move_to([1.5, 1.75, 0]))
        self.steps("Ten seconds later, it moves again, and she finishes the sentence: answering a question everyone else has already moved past.", [
            (lambda: [FadeIn(tnum)], 0.2),
            (lambda: [timer.animate(rate_func=linear).set_value(10)], 2.0),
            "it moves again",
            (lambda: [FadeOut(tnum), tile.animate.set_stroke(WHITE), *self.drop("frz"),
                      Transform(said, T("\"...Tuesday!\"", 22, WHITE).move_to(said))], 0.5),
            "already moved past",
            (lambda: [*self.cap("everyone else: already on Thursday", GREY_B)], 0.5),
        ])
        self.steps("From her side, nothing happened. Programs freeze the same way, and they can't feel it either. "
                   "So what if a program freezes in the middle of a job?", [
            "From her side",
            (lambda: [Wiggle(fc, scale_value=1.05, rotation_angle=0.02 * TAU)], 0.8),
            "So what if",
            (lambda: [*self.cap("what if a program freezes in the middle of a job?", WHITE, 28)], 0.5),
        ])

        # ---------------- scene 2: the lease ----------------
        self.play(FadeOut(VGroup(tile, fc, nm, said)), *self.uncap(), run_time=0.8)
        la, ls, lb, ll = (lane_label("worker A", A_Y, BLUE_M), lane_label("lease service", S_Y, WHITE),
                          lane_label("worker B", B_Y, GREEN_M), lane_label("ledger M-0042", L_Y, TEAL_M))
        guides = VGroup(*[DashedLine([X0, y, 0], [tx(TMAX), y, 0], dash_length=0.06, stroke_width=1, color=GREY_D) for y in (A_Y, S_Y, B_Y, L_Y)]).set_z_index(-1)
        self.steps("A small company records card payments for shops. Each shop has a ledger, the list of every change to its balance. "
                   "Two updates at the same moment could both start from the old balance and lose a change.", [
            "Each shop has a ledger",
            (lambda: [FadeIn(ll), Create(guides[3])], 0.6),
            "lose a change",
            (lambda: [*self.cap("so only one worker may update a ledger at a time", WHITE)], 0.5),
        ])
        self.steps("So only one worker may update it at a time. There are two workers, A and B, running the same code, so one can take over if the other dies.", [
            "two workers",
            (lambda: [FadeIn(la), Create(guides[0]), FadeIn(lb), Create(guides[2])], 0.8),
        ])
        l1 = band(0, 3105, S_Y, BLUE_M)
        l1t = left_at(T("lease 1: A", 17, BLUE_M), tx(0) + 0.12, S_Y).set_z_index(3)
        self.steps("They agree on who may write with a lease: a permission to act that runs out on its own. "
                   "A lease service grants A the lease for two seconds, and A renews it whenever less than one second is left.", [
            "a lease",
            (lambda: [FadeIn(ls), Create(guides[1]), *self.cap("a lease: a permission that runs out on its own", WHITE)], 0.6),
            "A lease service grants",
            (lambda: [GrowFromEdge(l1, LEFT), FadeIn(l1t)], 1.0),
            "renews it",
            (lambda: [*self.cap("2 s at a time, renewed when under 1 s is left", WHITE),
                      *self.put("rn", tickm(1100, S_Y, WHITE, 0.5, 2))], 0.5),
        ])
        self.steps("If A crashes, the renewals stop, the lease runs out, and B gets it. Nobody has to decide whether A is dead.", [
            "the lease runs out",
            (lambda: [Indicate(l1, color=BLUE_M, scale_factor=1.03)], 0.8),
            "Nobody has to",
            (lambda: [*self.cap("nobody has to decide whether A is dead", GREY_B)], 0.5),
        ])
        steps_ = VGroup(T("1. check: is my lease still valid?", 21, YELLOW_M), T("2. build the update (about 60 ms)", 21, WHITE),
                        T("3. write it to the ledger", 21, WHITE)).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        left_at(steps_, -6.3, TOP_Y)
        loop_lab = left_at(T("A's loop, every 100 ms", 18, GREY_B), -1.6, TOP_Y + 0.4)
        self.hl = None

        def hi(i, color=YELLOW_M):
            r = SurroundingRectangle(steps_[i], buff=0.08, color=color, stroke_width=2.5, corner_radius=0.06)
            old, self.hl = self.hl, r
            return [swap(old, r)] if old is not None else [Create(r)]

        self.steps("Worker A's loop runs every 100 milliseconds. First the check: is my lease still valid? Then the act: build the update, and write it.", [
            (lambda: [*self.uncap(), FadeIn(loop_lab), FadeIn(steps_[0])], 0.5),
            "Then the act",
            (lambda: [FadeIn(steps_[1]), FadeIn(steps_[2])], 0.6),
        ])
        self.steps("On a laptop, the check and the write run a millionth of a second apart. So it's easy to treat them as one step, "
                   "and every test you run agrees with you.", [
            (lambda: [*hi(0)], 0.4),
            (lambda: [*hi(1)], 0.4),
            (lambda: [*hi(2)], 0.4),
            "one step",
            (lambda: [*self.cap("check and act: they feel like one step", PURPLE_M)], 0.5),
        ])

        # ---------------- scene 3: the run ----------------
        axis = VGroup(Line([X0, AX_Y, 0], [tx(TMAX), AX_Y, 0], stroke_width=2, color=GREY_B),
                      *[VGroup(Line([tx(m), AX_Y, 0], [tx(m), AX_Y - 0.1, 0], stroke_width=2, color=GREY_B),
                               T(f"{m:,} ms", 15, GREY_B).move_to([tx(m), AX_Y - 0.3, 0])) for m in range(0, 5001, 1000)])
        now = ValueTracker(0)
        head = always_redraw(lambda: Line([tx(now.get_value()), A_Y + 0.4, 0], [tx(now.get_value()), L_Y - 0.3, 0], stroke_width=2, color=YELLOW_M))
        clock = always_redraw(lambda: T(f"{int(now.get_value()):,} ms", 18, YELLOW_M).move_to([tx(now.get_value()), A_Y + 0.52, 0]))
        a_ticks = VGroup(*[tickm(m, L_Y, BLUE_M) for m in range(270, 1471, 100)])
        a_run = band(0, 1520, A_Y, BLUE_M, op=0.25)
        v = lambda: now.get_value()
        a_live = always_redraw(lambda: band(0, min(max(v(), 1), 1520), A_Y, BLUE_M, op=0.25))
        frz_live = always_redraw(lambda: band(1520, min(max(v(), 1521), 4520), A_Y, GREY_B, op=0.18))
        b_live = always_redraw(lambda: band(3155, min(max(v(), 3156), TMAX), B_Y, GREEN_M, op=0.25))

        def go(ms, rt):
            return now.animate(rate_func=linear).set_value(ms)

        self.steps("Here is one run from the lab's simulator, which plays out the workers, the service and the ledger on a pretend clock, "
                   "so the same run happens every time.", [
            (lambda: [*self.uncap(), Create(axis), FadeIn(head), FadeIn(clock)], 0.6),
            (lambda: [FadeIn(a_live, run_time=0.1)], 0.1),
            (lambda: [go(1450, 2.6), LaggedStart(*[FadeIn(t) for t in a_ticks], lag_ratio=0.9)], 2.6),
        ], after=0)
        chk = Dot(radius=0.09, color=YELLOW_M).move_to([tx(1500), A_Y, 0]).set_z_index(3)
        chk_l = right_at(T("check: 1.6 s left", 16, YELLOW_M), tx(1500) - 0.12, A_Y - 0.4)
        self.steps("At 1,500 milliseconds, A checks. Its lease has 1.6 seconds left. So it starts building the update.", [
            (lambda: [go(1500, 0.4)], 0.4),
            "A checks",
            (lambda: [FadeIn(chk, scale=0.5), *hi(0)], 0.4),
            "1.6 seconds",
            (lambda: [FadeIn(chk_l), Indicate(l1, color=BLUE_M, scale_factor=1.03)], 0.7),
            "starts building",
            (lambda: [*hi(1)], 0.4),
        ])
        frz = band(1520, 4520, A_Y, GREY_B, op=0.18)
        frz_t = T("frozen: 3 s", 18, GREY_B).move_to(frz).set_z_index(3)
        self.steps("At 1,520, the JVM, the program that runs Java and Kotlin code, stops A for three seconds.", [
            (lambda: [go(1520, 0.3)], 0.3),
            (lambda: [FadeIn(frz_live, run_time=0.1)], 0.1),
            "stops A",
            (lambda: [*self.cap("1,520 ms: A stops, for 3 s", RED_M), steps_[1].animate.set_opacity(0.4), self.hl.animate.set_color(GREY_B)], 0.5),
        ])
        self.steps("Here's the question. When A wakes up, does its update reach the ledger? Pause and guess.", [
            "Pause and guess",
            (lambda: [*self.cap("pause and guess: does A's update reach the ledger?", YELLOW_M)], 0.4),
        ], after=0)
        self.countdown(3.0)
        out1 = right_at(T("lease 1 runs out: 3,105", 16, RED_M), tx(3105) - 0.12, S_Y - 0.4)
        self.steps("Watch the clock. Worker A is frozen, so it sends no renewals. At 3,105, lease 1 runs out. That's the service doing its job.", [
            (lambda: [*self.uncap(), go(3105, 2.2)], 2.2),
            "lease 1 runs out",
            (lambda: [FadeIn(out1), l1.animate.set_fill(fillc(BLUE_M, 0.12), 1)], 0.5),
        ], after=0)
        l2 = band(3155, TMAX, S_Y, GREEN_M)
        l2t = left_at(T("lease 2: B", 17, GREEN_M), tx(3155) + 0.12, S_Y).set_z_index(3)
        b_ticks = VGroup(*[tickm(m, L_Y, GREEN_M) for m in range(3320, 4521, 100)])
        b_run = band(3155, TMAX, B_Y, GREEN_M, op=0.25)
        b_lab = left_at(T("B: lease 2", 16, GREEN_M), tx(3155) + 0.12, B_Y).set_z_index(3)
        self.steps("At 3,155, B asks, and gets lease 2. From 3,320, B's updates land, one every 100 milliseconds. "
                   "The ledger has no reason to doubt them. B really is the holder now.", [
            (lambda: [go(3155, 0.4)], 0.4),
            "gets lease 2",
            (lambda: [GrowFromEdge(l2, LEFT), FadeIn(l2t), FadeIn(b_live), FadeIn(b_lab)], 0.7),
            "From 3,320",
            (lambda: [go(4450, 2.4), LaggedStart(*[FadeIn(t) for t in b_ticks[:12]], lag_ratio=0.9)], 2.4),
        ], after=0)
        a_back = band(4520, TMAX, A_Y, BLUE_M, op=0.25)
        late = Line([tx(4530), L_Y - 0.3, 0], [tx(4530), L_Y + 0.3, 0], stroke_width=4, color=RED_M)
        late_l = T("A's update, 4,530", 16, RED_M).move_to([tx(4530) - 0.2, L_Y - 0.48, 0])
        self.steps("At 4,520, A runs again. From the inside, nothing happened. It was in the middle of building its update, "
                   "so it finishes, and writes.", [
            (lambda: [go(4520, 0.4), FadeIn(b_ticks[12])], 0.4),
            (lambda: [FadeOut(frz_live, run_time=0.05), FadeIn(frz, run_time=0.05), FadeIn(frz_t, run_time=0.05), FadeOut(a_live, run_time=0.05), FadeIn(a_run, run_time=0.05)], 0.05),
            "A runs again",
            (lambda: [FadeIn(a_back), steps_[1].animate.set_opacity(1), self.hl.animate.set_color(YELLOW_M)], 0.5),
            "so it finishes",
            (lambda: [*hi(2)], 0.4),
        ], after=0)
        gap = DoubleArrow([tx(3105), GAP_Y, 0], [tx(4530), GAP_Y, 0], buff=0, stroke_width=2.5, color=RED_M, tip_length=0.15)
        gap_t = VGroup()
        self.steps("4,530. The ledger applies A's update, 1.4 seconds after A's lease ran out, on top of 13 updates from B.", [
            (lambda: [go(4530, 0.2), Create(late), FadeIn(late_l)], 0.5),
            "1.4 seconds",
            (lambda: [GrowFromCenter(gap), *self.cap("1.4 s after A's lease ran out, on top of 13 of B's updates", RED_M)], 0.6),
            "on top of 13",
            (lambda: [Indicate(b_ticks, color=GREEN_M, scale_factor=1.15)], 0.8),
        ])
        self.stamp("late")
        self.steps("So, yes, it gets through. Worker A finds out its lease is gone at its next check, 100 milliseconds too late to matter.", [
            (lambda: [go(4620, 0.5), *hi(0, RED_M)], 0.5),
            (lambda: [*self.cap("A's next check, at 4,620: lease gone. Too late.", RED_M)], 0.5),
        ])

        # ---------------- scene 4: the map, and the name ----------------
        self.steps("It's the video call. Worker A is the friend. The three seconds frozen is the frozen picture. "
                   "And the lease that ran out is the question everyone already moved past.", [
            (lambda: [*self.uncap(), FadeOut(head), FadeOut(clock), FadeOut(b_live), FadeIn(b_run)], 0.4),
            "Worker A is the friend",
            (lambda: [Indicate(la, color=BLUE_M)], 0.6),
            "The three seconds",
            (lambda: [glow(frz, BLUE_M, 1.0)], 0.7),
            "the lease that ran out",
            (lambda: [Indicate(out1, color=RED_M)], 0.6),
        ])
        self.steps("But here the picture breaks. On a call, everyone waits for her. Here, nobody waits. "
                   "The service hands the lease to B, and the ledger takes A's late write as if it were on time.", [
            "nobody waits",
            (lambda: [*self.cap("on a call, everyone waits. here, nobody waits.", GOLD_M)], 0.5),
            "The service hands",
            (lambda: [Indicate(l2t, color=GREEN_M)], 0.6),
            "the ledger takes",
            (lambda: [Indicate(late_l, color=RED_M)], 0.6),
        ])
        self.steps("The check was right when it ran. Then worker A stopped between the check and the act. "
                   "This pattern, checking and then acting as a separate step, is called check-then-act. Every lease and every lock has one.", [
            "The check was right",
            (lambda: [Indicate(chk_l, color=YELLOW_M)], 0.6),
            "called check-then-act",
            (lambda: [*self.cap("check-then-act: a check, then an act, as two separate steps", WHITE)], 0.5),
        ])
        self.steps("Seen from inside, a program is one continuous run. Seen from outside, it can stop between any two steps, for any length of time.", [
            (lambda: [*self.cap("inside: one continuous run.   outside: it can stop between any two steps", YELLOW_M)], 0.5),
        ], after=0.5)

        # ---------------- scene 5: check again ----------------
        zl = Line([ZX0, Z_Y, 0], [ZX1, Z_Y, 0], stroke_width=2, color=GREY_B)

        def zx(ms):
            return ZX0 + (ZX1 - ZX0) * (ms - ZMIN) / (ZMAX - ZMIN)

        zt = VGroup(*[VGroup(Line([zx(m), Z_Y - 0.06, 0], [zx(m), Z_Y + 0.06, 0], stroke_width=2, color=GREY_B),
                             T(f"{m:,}", 14, GREY_B).move_to([zx(m), Z_Y - 0.25, 0])) for m in (1500, 1520, 1540, 1560, 1580)])
        zoom_lines = right_at(T("zoomed in:", 18, GREY_B), ZX0 - 0.3, Z_Y)
        zc1 = VGroup(Dot(radius=0.08, color=YELLOW_M).move_to([zx(1500), Z_Y + 0.35, 0]), T("check", 16, YELLOW_M).move_to([zx(1500), Z_Y + 0.62, 0]))
        zb = Rectangle(width=zx(1560) - zx(1500), height=0.2, stroke_width=0).set_fill(BLUE_M, 0.6).move_to([(zx(1500) + zx(1560)) / 2, Z_Y + 0.35, 0])
        zbt = T("build, 60 ms", 16, BLUE_M).move_to([(zx(1500) + zx(1560)) / 2, Z_Y + 0.62, 0])
        zc2 = VGroup(Dot(radius=0.08, color=YELLOW_M).move_to([zx(1560), Z_Y + 0.35, 0]), T("check again", 16, YELLOW_M).move_to([zx(1560) + 0.25, Z_Y + 0.62, 0]))
        zs = Arrow([zx(1562), Z_Y + 0.35, 0], [zx(1580) + 0.6, Z_Y + 0.35, 0], buff=0, stroke_width=3, color=WHITE, max_tip_length_to_length_ratio=0.25)
        zst = T("send", 16, WHITE).move_to([zx(1580) + 0.95, Z_Y + 0.35, 0])

        def freeze_at(ms):
            return VGroup(Line([zx(ms), Z_Y - 0.1, 0], [zx(ms), Z_Y + 0.45, 0], stroke_width=4, color=RED_M),
                          T("freeze", 16, RED_M).move_to([zx(ms), Z_Y - 0.55, 0]))

        self.steps("The obvious fix: check again, right before you write. The lab's careful worker does exactly that, with 200 milliseconds to spare.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(steps_, loop_lab, self.hl)), Create(zl), FadeIn(zt), FadeIn(zoom_lines)], 0.8),
            "check again",
            (lambda: [FadeIn(zc1), GrowFromEdge(zb, LEFT), FadeIn(zbt)], 0.7),
            (lambda: [FadeIn(zc2)], 0.4),
            (lambda: [GrowArrow(zs), FadeIn(zst)], 0.4),
        ])
        self.hl = None
        f1 = freeze_at(1520)
        self.steps("Same pause, at 1,520, in the middle of the build. When A wakes up, its second check fails, and it drops the update.", [
            "Same pause",
            (lambda: [FadeIn(f1)], 0.5),
            "its second check fails",
            (lambda: [zc2.animate.set_color(RED_M), FadeOut(late), FadeOut(late_l), FadeOut(gap),
                      *self.cap("A drops its update: the check before sending failed", GREEN_M)], 0.7),
        ])
        self.steps("Fixed? Let's be fair to it: that run has no stale write at all. Now start the same pause 42 milliseconds later, at 1,562. "
                   "That's just after the second check, while the update is on its way.", [
            "Now start",
            (lambda: [*self.uncap(), zc2.animate.set_color(YELLOW_M), f1.animate.move_to([zx(1562), f1.get_y(), 0])], 0.8),
            "while the update",
            (lambda: [Indicate(zs, color=WHITE)], 0.6),
        ])
        late3 = Line([tx(4567), L_Y - 0.3, 0], [tx(4567), L_Y + 0.3, 0], stroke_width=4, color=RED_M)
        late3_l = T("A's update, 4,567", 16, RED_M).move_to([tx(4567) - 0.2, L_Y - 0.48, 0])
        self.steps("At 4,567, the ledger applies A's stale update again. The second check didn't close the gap. It only moved it.", [
            (lambda: [Create(late3), FadeIn(late3_l)], 0.5),
            "It only moved it",
            (lambda: [*self.cap("the second check only moved the gap", RED_M, 28)], 0.5),
        ])
        self.stamp("moved")
        self.steps("Asking a frozen program to check once more is like asking a sleepwalker to double-check that they're awake. "
                   "The one doing the checking is the one that freezes.", [
            "The one doing",
            (lambda: [*self.cap("the one doing the checking is the one that freezes", YELLOW_M)], 0.5),
        ])

        # ---------------- scene 6: guardrail ----------------
        self.steps("So keep the checks. They're cheap, and in the lab they made stale writes about fourteen times rarer. "
                   "But never impossible.", [
            (lambda: [*self.cap("checks: about 14 times rarer in the lab. never impossible.", WHITE)], 0.5),
        ])
        self.steps("What freezes programs? Memory clean-up, the cloud, the operating system, a slow disk. The rest of the lesson measures each one. "
                   "And the real fix lives outside A: someone who sees every write has to refuse the late one. That's the next lesson.", [
            (lambda: [*self.cap("freezes: memory clean-up, the cloud, the operating system, the disk", GREY_B)], 0.5),
            "And the real fix",
            (lambda: [*self.cap("the fix lives outside A: the ledger has to refuse the late write", TEAL_M), glow(ll, TEAL_M)], 0.6),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, the moral. A check tells you about the moment it ran, and nothing after. Between any two steps, the world can move on without you.", [
            (lambda: [*self.cap("a check tells you about the moment it ran, and nothing after", YELLOW_M)], 0.5),
        ], after=0.5)
        self.steps("One quick check. Say A's freeze at 1,520 had lasted one second instead of three. Would its update be late? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(f1, late3, late3_l, l2, l2t, b_ticks, b_run, b_lab, out1, chk_l)), l1.animate.set_fill(fillc(BLUE_M, 0.35), 1),
                      Transform(frz, band(1520, 2520, A_Y, GREY_B, op=0.18)), Transform(frz_t, T("1 s", 18, GREY_B).move_to([(tx(1520) + tx(2520)) / 2, A_Y, 0])),
                      Transform(a_back, band(2520, TMAX, A_Y, BLUE_M, op=0.25))], 1.0),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ok = Line([tx(2530), L_Y - 0.3, 0], [tx(2530), L_Y + 0.3, 0], stroke_width=4, color=GREEN_M)
        self.steps("No. Worker A wakes at 2,520, and lease 1 doesn't run out until 3,105. A pause only hurts when it outlasts what's left of the lease.", [
            (lambda: [*self.uncap(), Create(ok)], 0.5),
            "doesn't run out",
            (lambda: [Indicate(l1, color=BLUE_M, scale_factor=1.03)], 0.7),
            "A pause only hurts",
            (lambda: [*self.cap("a pause only hurts when it outlasts what's left of the lease", YELLOW_M)], 0.5),
        ])
        self.wait(2.0)
