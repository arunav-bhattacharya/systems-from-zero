from sfz import *

SAY.insert(0, (r"\bM-0042\b", "M zero zero four two"))
SAY.insert(0, (r"\bA\b(?!')", "eh"))       # holder A: Kokoro reads a bare capital A as the article "uh"

X0, X1, T0, T1 = -3.4, 6.3, 1000, 5000          # time axis: 1 s to 5 s
LANE = {"lease": 2.55, "A": 1.65, "B": 0.75, "ledger": -0.15}
AXIS_Y = -0.7
PAUSE0, PAUSE1 = 1520, 4520                     # A's thread is stopped
END1, GRANT2 = 3105, 3155                       # lease 1 runs out; lease 2 granted to B
A_TICKS = [1060, 1160, 1260, 1360, 1460]
B_TICKS = [3220 + 100 * k for k in range(13)]
STALE = 4530
CODE_Y = [-1.95, -2.45, -2.95]


def X(t):
    return X0 + (X1 - X0) * (t - T0) / (T1 - T0)


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


def fill(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    a, b = path.get_start(), path.get_end()
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])




def hline(t0, t1, y, color, sw=6):
    t1 = max(t1, t0 + 1)
    return Line([X(t0), y, 0], [X(t1), y, 0], stroke_width=sw, color=color)


def world(tk):
    """Everything on the timeline that depends on how far time has got."""
    t = tk.get_value()
    g = VGroup()
    a = LANE["A"]
    g.add(hline(T0, min(t, PAUSE0), a, BLUE_M))
    if t > PAUSE0:
        w = X(min(t, PAUSE1)) - X(PAUSE0)
        r = Rectangle(width=max(w, 0.01), height=0.46, stroke_color=GREY_B, stroke_width=2).set_fill(GREY_D, 0.6)
        g.add(r.move_to([X(PAUSE0) + w / 2, a, 0]))
    if t > PAUSE1:
        g.add(hline(PAUSE1, t, a, BLUE_M))
    b = LANE["B"]
    g.add(DashedLine([X(T0), b, 0], [X(max(min(t, GRANT2), T0 + 5)), b, 0], dash_length=0.08, stroke_width=2.5, color=GREY_C))
    if t > GRANT2:
        g.add(hline(GRANT2, t, b, GREEN_M))
        w = X(t) - X(GRANT2)
        r2 = Rectangle(width=max(w, 0.01), height=0.42, stroke_color=GREEN_M, stroke_width=2.5).set_fill(GREEN_M, 0.25)
        g.add(r2.move_to([X(GRANT2) + w / 2, LANE["lease"], 0]))
    ly = LANE["ledger"]
    for tt in A_TICKS:
        if t >= tt:
            g.add(Line([X(tt), ly - 0.22, 0], [X(tt), ly + 0.22, 0], stroke_width=4, color=BLUE_M))
    for tt in B_TICKS:
        if t >= tt:
            g.add(Line([X(tt), ly - 0.22, 0], [X(tt), ly + 0.22, 0], stroke_width=4, color=GREEN_M))
    if t >= STALE:
        g.add(Line([X(STALE), ly - 0.32, 0], [X(STALE), ly + 0.32, 0], stroke_width=7, color=RED_M))
    return g


_NOW = {}


def now_label(tk):
    """The time, above the lanes, with a marker over the lanes and one on the axis (no line through the lanes)."""
    s = f"{int(round(tk.get_value() / 10) * 10):,} ms"
    if s not in _NOW:
        _NOW[s] = T(s, 20, YELLOW_M)
    x = X(tk.get_value())
    top = Triangle(fill_color=YELLOW_M, fill_opacity=1, stroke_width=0).scale(0.09).rotate(PI).move_to([x, 2.93, 0])
    bot = Triangle(fill_color=YELLOW_M, fill_opacity=1, stroke_width=0).scale(0.09).move_to([x, AXIS_Y - 0.62, 0])
    return VGroup(_NOW[s].copy().move_to([x, 3.22, 0]), top, bot)


def code_line(k, s, color=WHITE):
    return left_at(M(s, 20, color), -6.05, CODE_Y[k])


def pointer(k, color=YELLOW_M):
    return Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.1).rotate(-PI / 2).move_to([-6.3, CODE_Y[k], 0])


def view_line(k, s, color=WHITE, mono=True):
    return left_at((M if mono else T)(s, 20, color), 0.85, CODE_Y[k])


class ProcessPause(Base):
    """dist-04, section 0: merchant M-0042's ledger, holders A and B, 2-second leases renewed below 1 second. A checks at
    1,500 ms (1.6 s left), a 3 s GC pause stops it at 1,520 ms, lease 1 runs out at 3,105 ms, B gets lease 2 at 3,155 ms
    and lands 13 updates, A wakes at 4,520 ms and its update lands at 4,530 ms, 1.4 s after its lease ran out. Section 3:
    A's monotonic clock shows the jump only on the next reading. The fix, fencing, is lesson 5."""

    def construct(self):
        self.title_card("Process pauses", "a lease holder that stops between the check and the write")

        labs = VGroup(*[left_at(T(s, 22, GREY_B), -6.5, LANE[k]) for k, s in
                        (("lease", "lease service"), ("A", "holder A"), ("B", "holder B"), ("ledger", "ledger M-0042"))])
        ledline = Line([X0, LANE["ledger"], 0], [X1, LANE["ledger"], 0], stroke_width=1.5, color=GREY_D)
        axis = Line([X0, AXIS_Y, 0], [X1, AXIS_Y, 0], stroke_width=2, color=GREY_B)
        ticks = VGroup(*[VGroup(Line([X(s * 1000), AXIS_Y - 0.08, 0], [X(s * 1000), AXIS_Y + 0.08, 0], stroke_width=2, color=GREY_B),
                                T(f"{s} s", 18, GREY_B).move_to([X(s * 1000), AXIS_Y - 0.3, 0])) for s in range(1, 6)])
        tk = ValueTracker(T0)
        self.steps("Merchant M-0042's ledger takes updates from one worker at a time. "
                   "Workers A and B run the same code, so B can take over if A dies.", [
            (lambda: [FadeIn(labs[3]), Create(ledline), Create(axis), FadeIn(ticks)], 0.9),
            "Workers A and B",
            (lambda: [FadeIn(labs[1]), FadeIn(labs[2])], 0.7),
        ])

        w = always_redraw(lambda: world(tk))
        self.add(w)
        l1 = Rectangle(width=X(END1) - X(T0), height=0.42, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLUE_M, 0.25)
        l1.move_to([(X(T0) + X(END1)) / 2, LANE["lease"], 0])
        l1t = T("lease 1: A, runs out at 3,105 ms", 19).move_to(l1)
        self.steps("They agree through a lease: a lock that runs out on its own. "
                   "A holds it two seconds at a time, and renews it whenever less than one second is left.", [
            (lambda: [FadeIn(labs[0])], 0.5),
            "A holds it",
            (lambda: [FadeIn(l1), FadeIn(l1t)], 0.8),
        ])

        code = RoundedRectangle(corner_radius=0.12, width=5.65, height=1.65, stroke_color=GREY_B, stroke_width=2.5)
        code.set_fill(BLACK, 1).move_to([-3.7, CODE_Y[1], 0])
        c0 = code_line(0, "if (leaseValid())    // check")
        c1 = code_line(1, "  u = buildUpdate()  // 60 ms")
        c2 = code_line(2, "  ledger.write(u)    // act")
        ptr = pointer(0)
        nowl = always_redraw(lambda: now_label(tk))
        self.steps("Every hundred milliseconds, A checks that its lease is still valid, spends about sixty milliseconds "
                   "building an update, and writes it to the ledger.", [
            (lambda: [FadeIn(code), FadeIn(c0), FadeIn(c1), FadeIn(c2), FadeIn(ptr), FadeIn(nowl)], 0.8),
            "A checks",
            (lambda: [Indicate(c0, color=YELLOW_M, scale_factor=1.05)], 0.6),
            "building",
            (lambda: [ptr.animate.move_to(pointer(1)), Indicate(c1, color=YELLOW_M, scale_factor=1.05)], 0.6),
            "and writes",
            (lambda: [ptr.animate.move_to(pointer(2)), Indicate(c2, color=YELLOW_M, scale_factor=1.05)], 0.6),
            (lambda: [tk.animate(rate_func=linear).set_value(1470), ptr.animate.move_to(pointer(0))], 2.0),
        ])

        chk = VGroup(Dot(radius=0.07, color=GREEN_M).move_to([X(1500), LANE["A"], 0]),
                     T("check: 1.6 s left", 19, GREEN_M).move_to([X(1500) + 0.35, LANE["A"] + 0.42, 0]))
        self.steps("At fifteen hundred milliseconds, A checks: one point six seconds left. It starts building the update.", [
            (lambda: [tk.animate(rate_func=linear).set_value(1500)], 0.5),
            "A checks",
            (lambda: [FadeIn(chk, scale=0.8), Indicate(c0, color=GREEN_M, scale_factor=1.05)], 0.7),
            "It starts building",
            (lambda: [ptr.animate.move_to(pointer(1)), tk.animate(rate_func=linear).set_value(1520)], 0.6),
        ])

        pl = left_at(T("A stopped: GC pause, 3 s", 20), X(PAUSE0) + 0.2, LANE["A"])
        self.steps("Twenty milliseconds later, a garbage collection pause stops A's thread. "
                   "For three seconds none of A's code runs, not even the renewal.", [
            "a garbage collection",
            (lambda: [ptr.animate.set_color(GREY_B), Transform(c1, code_line(1, "  u = buildUpdate()  // frozen", GREY_B))], 0.5),
            (lambda: [tk.animate(rate_func=linear).set_value(2550)], 2.4),
            (lambda: [FadeIn(pl), tk.animate(rate_func=linear).set_value(2900)], 1.2),
        ])

        self.steps("The world keeps going. A little after three seconds, lease one runs out, "
                   "and the service grants lease two to B.", [
            (lambda: [tk.animate(rate_func=linear).set_value(END1)], 1.2),
            "lease one runs out",
            (lambda: [l1.animate.set_stroke(RED_M).set_fill(RED_M, 0.2), Transform(l1t, T("lease 1: A, ran out at 3,105 ms", 19, RED_M).move_to(l1))], 0.7),
            "grants lease two",
            (lambda: [tk.animate(rate_func=linear).set_value(GRANT2 + 20)], 0.5),
        ])

        l2t = T("lease 2: B", 19).move_to([X(3800), LANE["lease"], 0])
        self.steps("B starts writing, and thirteen of its updates land on the ledger.", [
            (lambda: [tk.animate(rate_func=linear).set_value(4440)], 2.6),
            (lambda: [FadeIn(l2t)], 0.5),
        ])

        stale = right_at(T("A's stale write", 20, RED_M), X(STALE) - 0.15, LANE["ledger"] + 0.42)
        self.steps("At about four and a half seconds, A's thread runs again. From inside, nothing happened. "
                   "It was in the middle of building the update, so it finishes and writes it, "
                   "one point four seconds after its lease ran out.", [
            (lambda: [tk.animate(rate_func=linear).set_value(PAUSE1)], 0.8),
            "From inside",
            (lambda: [Transform(c1, code_line(1, "  u = buildUpdate()  // 60 ms")), ptr.animate.set_color(YELLOW_M)], 0.5),
            "so it finishes",
            (lambda: [ptr.animate.move_to(pointer(2))], 0.5),
            (lambda: [tk.animate(rate_func=linear).set_value(STALE + 20)], 0.6),
            (lambda: [FadeIn(stale, shift=0.1 * DOWN), Indicate(c2, color=RED_M, scale_factor=1.05)], 0.6),
        ])

        gap = Line([X(1500), LANE["A"] - 0.4, 0], [X(STALE), LANE["A"] - 0.4, 0], stroke_width=4, color=RED_M)
        gapl = right_at(T("check to write: 3 s", 19, RED_M), X(1500) - 0.15, LANE["A"] - 0.4)
        brace = Line([-6.42, CODE_Y[0], 0], [-6.42, CODE_Y[2], 0], stroke_width=4, color=RED_M)
        self.steps("The check was true when it ran. The pause landed between the check and the write, "
                   "and the write went ahead on an answer three seconds old.", [
            (lambda: [Indicate(chk[1], color=GREEN_M)], 0.8),
            "between the check",
            (lambda: [Create(brace), Create(gap)], 0.9),
            "an answer three",
            (lambda: [FadeIn(gapl)], 0.6),
        ])

        panel = RoundedRectangle(corner_radius=0.12, width=6.0, height=1.65, stroke_color=BLUE_M, stroke_width=2.5)
        panel.set_fill(fill(BLUE_M, 0.08), 1).move_to([3.5, CODE_Y[1], 0])
        v0 = view_line(0, "A's clock before: 1,520 ms")
        v1 = view_line(1, "A's clock after:  4,520 ms")
        v2 = view_line(2, "seen only after the write was sent", RED_M, mono=False)
        self.steps("Could A notice the pause? Its own clock jumps by three seconds, but A only sees that on its next reading, "
                   "after the write is already on its way.", [
            (lambda: [FadeIn(panel), FadeIn(v0)], 0.7),
            "Its own clock",
            (lambda: [FadeIn(v1, shift=0.1 * UP)], 0.6),
            "but A only sees",
            (lambda: [FadeIn(v2, shift=0.1 * UP)], 0.6),
        ])

        c2b = code_line(2, "  if (leaseValid()) write(u)", WHITE)
        self.steps("Checking again right before the write shrinks the gap to a few milliseconds. "
                   "But a pause can still land right after that second check.", [
            (lambda: [Transform(c2, c2b), FadeOut(brace)], 0.8),
            "But a pause",
            (lambda: [glow(code, RED_M, 1.03)], 0.9),
        ])

        self.steps("From inside, a program runs without a break. From outside, it can stop between any two instructions. "
                   "Stopping the stale write takes help from the ledger. That is the next lesson, fencing.", [
            (lambda: [Indicate(c0, color=YELLOW_M, scale_factor=1.04), Indicate(c1, color=YELLOW_M, scale_factor=1.04)], 1.0),
            "From outside",
            (lambda: [glow(gap, RED_M, 1.0), Indicate(pl, color=GREY_B)], 0.9),
            "Stopping the stale write",
            (lambda: [Indicate(labs[3], color=GOLD_M), Indicate(stale, color=RED_M)], 1.0),
        ])
        self.wait(0.6)
