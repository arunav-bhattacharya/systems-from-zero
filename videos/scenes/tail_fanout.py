from sfz import *

SAY.insert(0, (r"\b0\.99\b", "zero point nine nine"))
SAY.insert(0, (r"\b0\.37\b", "zero point three seven"))
SAY.insert(0, (r"\bBigTable\b", "Big Table"))
SAY.insert(0, (r"\bbackend\b", "back end"))   # Kokoro blurs it into "backhand"

S, G = 0.32, 0.08                 # leaf square size and gap
STEP = S + G
GX, GY = -0.5, 0.55               # grid centre
SLOW = 39                         # row 3, column 9: the unlucky server
DX, DY = -5.0, 0.75               # dashboard
RX = 4.9                          # replica


def lpos(i):
    r, c = divmod(i, 10)
    return np.array([GX - 4.5 * STEP + c * STEP, GY + 4.5 * STEP - r * STEP, 0])


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


def counter(fmt, value, place, size=36, color=WHITE):
    cache = {}

    def make():
        s = fmt(value())
        if s not in cache:
            cache[s] = T(s, size, color)
        return place(cache[s].copy())
    return always_redraw(make)


def band(*lines):
    """The numbers area under the diagram: one or two (text, colour) lines."""
    g = VGroup(*[T(s, 28, c) for s, c in lines]).arrange(DOWN, buff=0.24)
    return g.move_to([0, 0, 0]).align_to(np.array([0, -2.3, 0]), UP)


class TailFanout(Base):
    """found-02, section 3: fan-out to 100 servers makes the slowest one set the page time; a hedged request cuts it."""

    def construct(self):
        self.title_card("Fan-out and the tail", "why the slowest server sets the page time")

        rng = np.random.default_rng(7)
        times = list(rng.uniform(5, 15, 100))
        times[SLOW] = 1000.0
        st = {"mode": "idle", "hedge_at": 1e9}
        clock = ValueTracker(0)

        dash = box("dashboard", BLUE_M, w=2.6, h=0.9, size=28).move_to([DX, DY, 0])
        clock_l = T("page time", 22, GREY_B).move_to([DX, -0.1, 0])

        def fmt(v):
            v = int(round(v)) if v < 30 else int(round(v / 10.0) * 10)
            return f"{v:,} ms"
        clock_t = counter(fmt, clock.get_value, lambda m: m.move_to([DX, -0.68, 0]))

        leaves = VGroup(*[RoundedRectangle(corner_radius=0.05, width=S, height=S, stroke_width=2, stroke_color=GREY_C)
                          .set_fill(BLACK, opacity=1).move_to(lpos(i)) for i in range(100)])
        grid_l = T("100 servers", 24, GREY_B).move_to([GX, GY - 5 * STEP - 0.3, 0])
        start = dash.get_right() + 0.08 * RIGHT
        fan = VGroup(*[Line(start, lpos(10 * r) + (S / 2 + 0.1) * LEFT, stroke_width=1.5, color=GREY_D) for r in range(10)])

        def leaf_upd(i):
            def f(m):
                mode, t = st["mode"], clock.get_value()
                if mode == "idle":
                    m.set_stroke(GREY_C).set_fill(BLACK, 1)
                elif i == SLOW and t >= st["hedge_at"]:
                    m.set_stroke(GREY_C).set_fill(GREY_D, 0.6)          # its answer is no longer needed
                elif t >= times[i]:
                    m.set_stroke(GREEN_M).set_fill(GREEN_M, 0.85)
                elif t > 15.2:
                    m.set_stroke(RED_M).set_fill(RED_M, 0.9)
                else:
                    m.set_stroke(YELLOW_M).set_fill(BLACK, 1)
            return f

        # ---- one page, 100 servers ---------------------------------------------------------------------
        def send():
            for i, l in enumerate(leaves):
                l.add_updater(leaf_upd(i))
            st["mode"] = "run"
            return [LaggedStart(*[travel(l, YELLOW_M, 0.7) for l in fan], lag_ratio=0.05), FadeIn(clock_l), FadeIn(clock_t)]
        self.steps("A merchant opens their dashboard. The backend asks 100 servers for one piece each, all at once, and waits for every answer.", [
            (lambda: [FadeIn(dash, shift=0.2 * RIGHT)], 1.0),
            "The backend",
            (lambda: [LaggedStart(*[Create(l) for l in fan], lag_ratio=0.05),
                      LaggedStart(*[FadeIn(l, scale=0.6) for l in leaves], lag_ratio=0.01), FadeIn(grid_l)], 2.2),
            "and waits",
            (send, 1.4),
        ])

        self.steps("Each server usually answers in 5 to 15 milliseconds. But one call in a hundred hits a pause, and takes a full second.", [
            (lambda: [clock.animate(rate_func=linear).set_value(15.4)], 2.6),
            "But one call",
            (lambda: [Indicate(leaves[SLOW], color=RED_M, scale_factor=1.8)], 1.2),
        ])
        self.steps("99 servers are done. The page still waits for the last one, a whole second.", [
            "The page still",
            (lambda: [clock.animate(rate_func=linear).set_value(1000)], 2.6),
        ])

        # ---- the arithmetic ----------------------------------------------------------------------------
        b1 = band(("one server: slow 1 call in 100", WHITE), ("the page is fast only if all 100 are fast", WHITE))
        self.steps("One server is slow one time in a hundred. The page is fast only if all 100 are fast.", [
            (lambda: [FadeIn(b1[0], shift=0.15 * UP)], 0.8),
            "The page",
            (lambda: [FadeIn(b1[1], shift=0.15 * UP)], 0.8),
        ])
        b2 = band(("all 100 fast:  0.99 × 0.99 × … (100 times)  =  0.37", WHITE), ("slow pages: 63 in 100", RED_M))
        self.steps("That's 0.99 multiplied by itself 100 times, about 0.37. So 63 page loads in 100 take a second or more.", [
            (lambda: [FadeOut(b1, shift=0.15 * UP), FadeIn(b2[0], shift=0.15 * UP)], 1.0),
            "So 63",
            (lambda: [FadeIn(b2[1], shift=0.15 * UP)], 0.8),
        ])

        # ---- hedging -----------------------------------------------------------------------------------
        rep = box("replica", TEAL_M, w=1.9, h=0.66, size=26).move_to([RX, lpos(SLOW)[1], 0])
        same = DashedLine(lpos(SLOW) + (S / 2 + 0.1) * RIGHT, rep.get_left() + 0.1 * LEFT, dash_length=0.08, stroke_width=2, color=TEAL_M)
        same_l = T("same data", 22, TEAL_M).next_to(same, UP, buff=0.14)

        def reset():
            st["mode"] = "idle"
            return [FadeOut(b2), clock.animate.set_value(0)]
        self.steps("So stop waiting for the unlucky server. Keep each piece of data on a second server too, a copy called a replica.", [
            (reset, 1.0),
            "Keep each",
            (lambda: [Create(same), FadeIn(same_l), FadeIn(rep, shift=0.2 * LEFT)], 1.4),
        ])

        p0, p1 = dash.get_top() + 0.1 * UP, rep.get_top() + 0.1 * UP
        hedge = CurvedArrow(p0, p1, angle=-0.46 * PI, color=TEAL_M, stroke_width=3, tip_length=0.2)
        go, back = ArcBetweenPoints(p0, p1, angle=-0.46 * PI), ArcBetweenPoints(p1, p0, angle=0.46 * PI)

        def run2():
            st["mode"] = "run"
            return [LaggedStart(*[travel(l, YELLOW_M, 0.6) for l in fan], lag_ratio=0.04)]
        self.steps("Run it again. At 15 milliseconds, one call is still out. So the backend sends the same call to the replica.", [
            (run2, 1.0),
            (lambda: [clock.animate(rate_func=linear).set_value(15.4)], 2.0),
            "So the backend",
            (lambda: [Create(hedge), travel(go, TEAL_M, 1.2)], 1.4),
        ])

        def answer():
            st["hedge_at"] = 23
            return [clock.animate(rate_func=linear).set_value(23), travel(back, GREEN_M, 1.4),
                    rep[0].animate.set_stroke(GREEN_M)]
        self.steps("The backend takes whichever answer comes first. Here it's the replica's, and the page is done at 23 milliseconds.", [
            "Here it's",
            (answer, 1.6),
            (lambda: [Circumscribe(clock_t, color=GREEN_M, buff=0.15)], 1.0),
        ])

        hchip = chip("hedged request", TEAL_M, 24).move_to([RX, lpos(SLOW)[1] - 0.85, 0])
        b4 = band(("hedge after 15 ms:  page 1,000 ms → 23 ms", GREEN_M), ("extra calls: about 1 in 100", WHITE))
        self.steps("That second call is a hedged request. Only late calls get one, about 1 in 100.", [
            (lambda: [FadeIn(hchip, shift=0.15 * UP), FadeIn(b4[0], shift=0.15 * UP)], 1.0),
            "Only late",
            (lambda: [FadeIn(b4[1], shift=0.15 * UP)], 0.8),
        ])

        b5 = band(("BigTable, 1,000 keys on 100 servers, hedge after 10 ms", WHITE),
                  ("slowest read in 1,000:  1,800 ms → 74 ms,  for 2% more requests", GREEN_M))
        self.steps("Google tested it on a database, BigTable, reading 1,000 keys spread over 100 servers. "
                   "Hedging after 10 milliseconds cut the slowest read in a thousand from 1,800 milliseconds to 74, for 2% more requests.", [
            (lambda: [FadeOut(b4, shift=0.15 * UP), FadeIn(b5[0], shift=0.15 * UP)], 1.0),
            "Hedging after",
            (lambda: [FadeIn(b5[1], shift=0.15 * UP)], 0.8),
        ])

        # ---- when it fails ---------------------------------------------------------------------------
        c1 = T("1.  the replica is slow for its own reasons", 28)
        c2 = T("2.  the call is safe to run twice", 28)
        VGroup(c1, c2).arrange(DOWN, buff=0.24, aligned_edge=LEFT).move_to([0, 0, 0]).align_to(np.array([0, -2.3, 0]), UP)
        red_fill = interpolate_color(ManimColor("#000000"), ManimColor(RED_M), 0.3)
        teal_fill = interpolate_color(ManimColor("#000000"), ManimColor(TEAL_M), 0.14)
        self.steps("It needs two things. The replica must be slow for its own reasons. If one bad deploy slows both copies, the hedge is slow too.", [
            (lambda: [FadeOut(b5), FadeIn(c1, shift=0.15 * UP)], 1.0),
            "If one bad",
            (lambda: [rep[0].animate.set_stroke(RED_M).set_fill(red_fill, 1), hedge.animate.set_color(RED_M)], 1.0),
        ])
        self.steps("And the call must be safe to run twice. A read is. A card payment needs a key that the issuer checks, so it charges once.", [
            (lambda: [rep[0].animate.set_stroke(GREEN_M).set_fill(teal_fill, 1), hedge.animate.set_color(TEAL_M),
                      FadeIn(c2, shift=0.15 * UP)], 1.0),
        ])

        self.steps("When a page waits for 100 servers, the slowest one sets its time. A hedge asks a second server and keeps the first answer.", [
            (lambda: [Indicate(leaves[SLOW], color=RED_M, scale_factor=1.8)], 1.4),
            "A hedge",
            (lambda: [Indicate(rep[1], color=TEAL_M), Indicate(hchip, color=TEAL_M)], 1.4),
        ])
        self.wait(0.6)
