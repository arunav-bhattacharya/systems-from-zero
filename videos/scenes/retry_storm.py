from sfz import *

SAY.insert(0, (r"\b111,557\b", "a hundred and eleven thousand, five hundred and fifty-seven"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CL, CL_W, CL_H = np.array([-5.0, 0.3, 0]), 2.0, 1.3      # the customers, later the clients
SV, SV_W, SV_H = np.array([4.0, 0.3, 0]), 2.4, 1.3       # the barista, later the server
RAIL_Y, SLIP_Y = 0.62, 0.36                              # the rail of slips, later the queue
RAIL_X0, RAIL_X1 = -2.5, 2.05
SLIP_X = [1.75 - 0.36 * k for k in range(12)]             # k = 0 is the front, next to the barista
LOOP_Y, ANS_Y = 2.0, -1.15                               # the retry loop above, the answers path below
RISER_X = 1.4
QLAB = np.array([-0.45, -0.15, 0])
BIN = np.array([1.55, -0.55, 0])
READ_Y, BAR_Y, CAP_Y = -1.68, -2.6, -3.2
CLOCK = np.array([-5.45, 3.1, 0])
BOARD_X, BOARD_Y = 2.1, 3.1                              # the scoreboard of fixes, top right


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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def poly(pts):
    return VMobject().set_points_as_corners([np.array([x, y, 0]) for x, y in pts])


def dot_on(path, color=YELLOW_M, rt=0.8, frac=1.0):
    """A dot that runs along a path (part of the way if frac < 1, then fades: nobody there to take it)."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start())
    seq = [FadeIn(d, run_time=0.05)]
    if frac < 1:
        seq += [MoveAlongPath(d, path, rate_func=lambda t: smooth(t) * frac, run_time=rt), FadeOut(d, scale=1.8, run_time=0.25)]
    else:
        seq += [MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15)]
    return Succession(*seq)


def labelled_box(c, w, h, color, top, sub, sub_color=GREY_B):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    a = T(top, 26).move_to(c + [0, 0.22, 0])
    b = T(sub, 19, sub_color).move_to(c + [0, -0.25, 0])
    return r, a, b


class RetryStorm(Base):
    """found-03, section 3. A program slows for five seconds and is still down a minute later. A coffee counter: slips
    on a rail, a barista, customers who reorder after three minutes, a slow coffee machine, a café full of ghosts.
    Mapped to server, queue, clients, timeout and retry; the lab's numbers (1,000 a second, 800 arriving, 200 ms,
    4 attempts, 400 a second for five seconds). Goodput, metastable failure. Backoff and no retries tried; a retry
    budget and dropping expired work fix it. Guardrail, moral and a check question."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = (T(s, size, color) if isinstance(s, str) else s)
        fit(new, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def clock(self, s):
        return self.put("clock", T(s, 26, WHITE).move_to(CLOCK))

    def rate(self, s, color=WHITE):
        return self.put("rate", T(s, 20, color).move_to([(CL[0] + CL_W / 2 + RAIL_X0) / 2, 0.68, 0]))

    def queued(self, s, color=GREY_B):
        return self.put("qname", T("the queue: " + s.split(": ")[1], 20, color).move_to(QLAB))

    def reads(self, good, waste):
        g = T(f"goodput: {good} a second", 22, GREEN_M if good != "0" else RED_M).move_to([-3.0, READ_Y, 0])
        w = T(f"wasted: {waste} a second", 22, RED_M if waste != "0" else GREY_B).move_to([2.2, READ_Y, 0])
        return self.put("good", g) + self.put("waste", w)

    def rail(self, yellow, grey):
        """The slips on the rail: `grey` slips at the front (nobody waits for them), then `yellow` ones behind."""
        out = []
        for k, s in enumerate(self.slips):
            if k < grey:
                out.append(s.animate.set_stroke(GREY_C, opacity=1).set_fill(fillc(GREY_C, 0.35), 1))
            elif k < grey + yellow:
                out.append(s.animate.set_stroke(YELLOW_M, opacity=1).set_fill(fillc(YELLOW_M, 0.3), 1))
            else:
                out.append(s.animate.set_stroke(opacity=0).set_fill(opacity=0))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Trying again, all at once", "how retries keep a program down")

        # ---------------- scene 1: the symptom ----------------
        X0, X1, Y0, Y1 = -4.6, 4.6, -1.3, 1.6

        def px(t):
            return X0 + (X1 - X0) * t / 60

        def py(v):
            return Y0 + (Y1 - Y0) * v / 1000

        axes = VGroup(Line([X0, Y0, 0], [X1 + 0.2, Y0, 0], stroke_width=2, color=GREY_B),
                      Line([X0, Y0, 0], [X0, Y1 + 0.2, 0], stroke_width=2, color=GREY_B))
        ticks = VGroup(*[T(str(t), 18, GREY_B).move_to([px(t), Y0 - 0.3, 0]) for t in (0, 10, 15, 30, 60)])
        axl = VGroup(T("seconds", 18, GREY_B).move_to([X1, Y0 - 0.62, 0]),
                     left_at(T("useful answers a second", 20, GREY_B), X0 - 0.1, Y1 + 0.45))
        band = Rectangle(width=px(15) - px(10), height=Y1 - Y0, stroke_width=0).set_fill(RED_M, 0.22).move_to([(px(10) + px(15)) / 2, (Y0 + Y1) / 2, 0])
        band_l = left_at(T("slow for 5 s", 20, RED_M), px(15) + 0.15, Y1 - 0.2)
        good_a = poly([(px(0), py(800)), (px(10), py(800)), (px(10.5), py(161)), (px(11), py(0))]).set_stroke(GREEN_M, 4)
        good_b = poly([(px(11), py(0)), (px(60), py(0))]).set_stroke(RED_M, 5)
        self.steps("Here's a strange outage. A program slows down for five seconds, then gets its speed back.", [
            (lambda: [Create(axes), FadeIn(ticks), FadeIn(axl)], 1.0),
            "A program",
            (lambda: [Create(good_a)], 1.0),
            "slows down",
            (lambda: [FadeIn(band), FadeIn(band_l)], 0.6),
        ])
        self.steps("Yet a minute later, it's still giving useful answers to nobody. The cause is long gone, so what's keeping it down?", [
            (lambda: [Create(good_b)], 2.0),
            "The cause",
            (lambda: self.cap("the cause: gone after 5 seconds.   useful answers: still zero a minute later", WHITE), 0.6),
        ])
        self.steps("The culprit is the most innocent habit in programming: trying again.", [
            (lambda: self.cap("the culprit: trying again", YELLOW_M, 28), 0.6),
        ], after=0.5)

        # ---------------- scene 2: the coffee counter ----------------
        cl_r, cl_a, cl_b = labelled_box(CL, CL_W, CL_H, BLUE_M, "customers", "at the till")
        sv_r, sv_a, sv_b = labelled_box(SV, SV_W, SV_H, TEAL_M, "barista", "makes drinks")
        rail = Line([RAIL_X0, RAIL_Y, 0], [RAIL_X1, RAIL_Y, 0], stroke_width=4, color=GREY_B)
        self.slips = VGroup(*[Rectangle(width=0.27, height=0.46, stroke_width=2.5).set_stroke(YELLOW_M, opacity=0)
                              .set_fill(BLACK, 0).move_to([x, SLIP_Y, 0]) for x in SLIP_X])
        a_in = Arrow([CL[0] + CL_W / 2 + 0.08, CL[1], 0], [RAIL_X0 - 0.08, CL[1], 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.25)
        a_out = Arrow([RAIL_X1 + 0.08, SV[1], 0], [SV[0] - SV_W / 2 - 0.08, SV[1], 0], buff=0, stroke_width=3, color=GREY_B,
                      max_tip_length_to_length_ratio=0.3)
        ans_pts = [(SV[0], SV[1] - SV_H / 2 - 0.08), (SV[0], ANS_Y), (CL[0], ANS_Y), (CL[0], CL[1] - CL_H / 2 - 0.08)]
        ans = poly(ans_pts).set_stroke(GREY_C, 2)
        ans_tip = Arrow([CL[0], ANS_Y + 0.3, 0], [CL[0], CL[1] - CL_H / 2 - 0.08, 0], buff=0, stroke_width=2, color=GREY_C,
                        max_tip_length_to_length_ratio=0.5)
        ans_path = poly(ans_pts)
        in_path = Line(a_in.get_start(), a_in.get_end())
        out_path = Line(a_out.get_start(), a_out.get_end())

        def flow(n=3, useful=True, ans_col=GREEN_M):
            """n orders arrive, n are served; each answer reaches the customer (useful) or fades (nobody waiting)."""
            arrive = LaggedStart(*[dot_on(in_path, YELLOW_M, 0.5) for _ in range(n)], lag_ratio=0.35)
            serve = LaggedStart(*[Succession(dot_on(out_path, YELLOW_M, 0.4),
                                             dot_on(ans_path, ans_col if useful else RED_M, 1.1, 1.0 if useful else 0.45))
                                  for _ in range(n)], lag_ratio=0.35)
            return [arrive, serve]

        self.steps("Picture a coffee counter. Each order is a slip on a rail, and the barista makes drinks in the order the slips sit there.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(axes, ticks, axl, band, band_l, good_a, good_b))], 0.7),
            "Picture a coffee",
            (lambda: [FadeIn(VGroup(cl_r, cl_a, cl_b), shift=0.1 * RIGHT), FadeIn(VGroup(sv_r, sv_a, sv_b), shift=0.1 * LEFT)], 0.8),
            "Each order",
            (lambda: [Create(rail), GrowArrow(a_in), GrowArrow(a_out), *self.put("qname", T("the rail", 20, GREY_B).move_to(QLAB))], 0.8),
            "a slip on a rail",
            (lambda: self.rail(3, 0), 0.5),
            "the barista makes",
            (lambda: [Create(ans), GrowArrow(ans_tip), *self.put("ans", T("drinks", 20, GREY_B).move_to([-1.5, ANS_Y + 0.3, 0]))], 0.7),
            (lambda: flow(2), 2.0),
        ])
        self.steps("On a normal morning she keeps up, and the rail stays almost empty.", [
            (lambda: [*flow(3), *self.rail(1, 0)], 2.2),
        ])
        loop_pts = [(RISER_X, RAIL_Y + 0.06), (RISER_X, LOOP_Y), (CL[0], LOOP_Y), (CL[0], CL[1] + CL_H / 2 + 0.08)]
        loop = poly(loop_pts).set_stroke(RED_M, 3)
        loop_tip = Arrow([CL[0], LOOP_Y - 0.3, 0], [CL[0], CL[1] + CL_H / 2 + 0.08, 0], buff=0, stroke_width=3, color=RED_M,
                         max_tip_length_to_length_ratio=0.5)
        loop_path = poly(loop_pts)
        self.steps("One more rule. A customer who has waited three minutes gives up, goes back to the till and orders again. "
                   "The first slip stays on the rail.", [
            "A customer who",
            (lambda: [Create(loop), GrowArrow(loop_tip),
                      *self.put("loop", T("waited 3 minutes: order again", 20, RED_M).move_to([-3.35, LOOP_Y + 0.3, 0]))], 1.0),
            "orders again",
            (lambda: [dot_on(loop_path, RED_M, 1.0)], 1.0),
            "The first slip",
            (lambda: [Indicate(self.slips[0], color=YELLOW_M, scale_factor=1.3)], 0.8),
        ])

        # ---------------- scene 3: the slow machine ----------------
        sv_b2 = T("slow machine", 19, RED_M).move_to(sv_b)
        sv_b3 = T("makes drinks", 19, GREY_B).move_to(sv_b)
        sv_a2 = T("server", 26).move_to(sv_a)
        cl_a2 = T("clients", 26).move_to(cl_a)
        cl_b2 = T("send requests", 19, GREY_B).move_to(cl_b)
        sv_cap2 = T("1,000 a second", 19, GREY_B).move_to(sv_b)
        sv_slow2 = T("400 a second", 19, RED_M).move_to(sv_b)
        sv_cap3 = T("1,000 a second", 19, GREY_B).move_to(sv_b)
        self.steps("Now the coffee machine runs slowly for a few minutes. Slips pile up. People give up and order again, "
                   "so the pile grows even faster.", [
            "runs slowly",
            (lambda: [sv_r.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.25), 1), swap(sv_b, sv_b2)], 0.7),
            "Slips pile up",
            (lambda: [*flow(4), *self.rail(6, 0)], 1.8),
            "People give up",
            (lambda: [LaggedStart(*[dot_on(loop_path, RED_M, 0.9) for _ in range(3)], lag_ratio=0.3), *self.rail(7, 3)], 1.6),
            (lambda: self.rail(8, 4), 0.6),
        ])
        self.steps("Soon the barista is making drinks for people who have left. Then the machine recovers, and it makes no difference. "
                   "The reorders keep coming faster than she can work.", [
            "making drinks",
            (lambda: [*flow(3, useful=False), *self.rail(4, 8)], 2.0),
            "Then the machine",
            (lambda: [sv_r.animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1), swap(sv_b2, sv_b3)], 0.7),
            "The reorders",
            (lambda: [LaggedStart(*[dot_on(loop_path, RED_M, 0.8) for _ in range(4)], lag_ratio=0.25), *flow(3, useful=False),
                      *self.rail(4, 8)], 2.0),
        ])
        self.steps("She's busier than ever, serving a café full of ghosts. So the slowdown is over, but the reorders keep the rail full.", [
            (lambda: [*flow(3, useful=False), *self.cap("a café full of ghosts")], 1.8),
            "So the slowdown",
            (lambda: [*self.cap("the slowdown is over; the reorders keep the rail full", WHITE),
                      LaggedStart(*[Indicate(s, color=GREY_B, scale_factor=1.15) for s in self.slips], lag_ratio=0.06)], 1.2),
        ])

        # ---------------- scene 4: the program, with numbers ----------------
        self.steps("Programs do the same. The barista is the server, the program doing the work. The rail is its queue. "
                   "The customers are clients, programs that send it requests.", [
            (lambda: [*self.uncap(), *self.rail(0, 0)], 0.5),
            "The barista is",
            (lambda: [swap(sv_a, sv_a2), glow(sv_r, TEAL_M)], 0.7),
            "The rail is",
            (lambda: self.put("qname", T("the queue", 20, GREY_B).move_to(QLAB)), 0.6),
            "The customers",
            (lambda: [swap(cl_a, cl_a2), swap(cl_b, cl_b2), glow(cl_r, BLUE_M)], 0.7),
        ])
        self.steps("Three minutes is the timeout, how long a client waits before giving up. And ordering again is a retry.", [
            "Three minutes",
            (lambda: self.put("loop", T("timed out after 200 ms: a retry", 20, RED_M).move_to([-3.35, LOOP_Y + 0.3, 0])), 0.7),
            "a retry",
            (lambda: [dot_on(loop_path, RED_M, 1.0), *self.put("ans", T("answers", 20, GREY_B).move_to([-1.5, ANS_Y + 0.3, 0]))], 1.0),
        ])
        sv_cap = T("1,000 a second", 19, GREY_B).move_to(sv_b)
        self.steps("Now with numbers. The server can finish 1,000 requests a second, and gets 800. "
                   "So it's 80% busy, and answers in about a millisecond.", [
            "The server can",
            (lambda: [swap(sv_b3, sv_cap), *self.clock("t = 5 s")], 0.7),
            "and gets 800",
            (lambda: [*self.rate("800/s"), *flow(3), *self.queued("queued: 0")], 1.6),
            "So it's 80%",
            (lambda: self.reads("800", "0"), 0.6),
        ])
        self.steps("Clients give up on an attempt after 200 milliseconds and try again at once, up to 4 attempts in all.", [
            (lambda: [glow(loop, RED_M, 1.0)], 0.9),
            "up to 4",
            (lambda: self.cap("each request: up to 4 attempts", WHITE), 0.6),
        ])

        # ---------------- scene 5: predict, then watch ----------------
        sv_slow = T("400 a second", 19, RED_M).move_to(sv_b)
        self.steps("At ten seconds in, something the server depends on slows down. For five seconds, it can finish only 400 a second. "
                   "Then it's back to 1,000. When does the service recover? Pause and guess.", [
            (lambda: [*self.uncap(), *self.clock("t = 10 s")], 0.5),
            "For five seconds",
            (lambda: [sv_r.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.25), 1), swap(sv_cap, sv_slow)], 0.7),
            "When does",
            (lambda: self.cap("slow from 10 s to 15 s.  back to normal when?", WHITE), 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Let's watch. In a fifth of a second, 80 are queued: "
                   "200 milliseconds of work at this speed. So anything joining now times out before it's served.", [
            (lambda: [*self.uncap(), *flow(3), *self.rail(3, 0), *self.reads("400", "0")], 1.6),
            "In a fifth",
            (lambda: [*self.clock("t = 10.2 s"), *self.queued("queued: 80", WHITE), *self.rail(6, 0)], 0.6),
            "200 milliseconds",
            (lambda: self.cap("80 queued, at 400 a second: 200 ms of waiting", WHITE), 0.6),
            "So anything",
            (lambda: [Indicate(self.slips[5], color=RED_M, scale_factor=1.3)], 0.8),
        ])
        self.steps("Every attempt times out, so every request is sent four times. 800 new requests become 3,200 attempts a second.", [
            (lambda: [*self.clock("t = 11 s"), LaggedStart(*[dot_on(loop_path, RED_M, 0.9) for _ in range(4)], lag_ratio=0.25),
                      *self.rail(7, 5)], 1.6),
            "800 new",
            (lambda: [*self.rate("3,200/s", RED_M), *self.queued("queued: 4,157", WHITE), *self.cap("800 new requests × 4 attempts = 3,200 a second", WHITE)], 0.7),
        ])
        self.steps("The server can't tell who's still waiting. It works through the queue in order, and every answer goes to a client "
                   "that already gave up.", [
            (lambda: [*self.uncap(), *self.rail(4, 8)], 0.6),
            "It works through",
            (lambda: [*flow(3, useful=False), *self.reads("0", "400")], 2.0),
        ])
        self.steps("At fifteen seconds, the server is back to full speed. It makes no difference. "
                   "3,200 attempts arrive each second, more than three times what it can do.", [
            (lambda: [*self.clock("t = 16 s"), sv_r.animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1), swap(sv_slow, sv_cap2)], 0.7),
            "It makes no",
            (lambda: [*flow(3, useful=False), *self.reads("0", "1,000"), *self.queued("queued: 16,957", WHITE)], 1.6),
            "3,200 attempts",
            (lambda: [Indicate(self.lab["rate"], color=RED_M, scale_factor=1.3), LaggedStart(*[dot_on(loop_path, RED_M, 0.8) for _ in range(4)], lag_ratio=0.25)], 1.4),
        ])
        self.steps("A minute in, 111,557 attempts are queued, and not one answer is useful. Well... that was a long five seconds.", [
            (lambda: [*self.clock("t = 59 s"), *self.queued("queued: 111,557", RED_M), *flow(3, useful=False)], 1.6),
            "Well",
            (lambda: [Indicate(self.lab["good"], color=RED_M, scale_factor=1.15)], 0.8),
        ], after=0.4)
        self.stamp("storm")
        self.steps("The rate of answers someone is still waiting for is called goodput. Here it's zero, and it stays zero.", [
            "called goodput",
            (lambda: [*self.cap("goodput: answers someone is still waiting for"), glow(ans, GREEN_M, 1.0)], 0.8),
        ])
        self.steps("A trigger pushed the system into a bad state, and its own behaviour keeps it there after the trigger is gone. "
                   "That's called a metastable failure. Getting out takes a strong push, like cutting the load or restarting.", [
            "its own behaviour",
            (lambda: [glow(loop, RED_M, 1.0), LaggedStart(*[dot_on(loop_path, RED_M, 0.8) for _ in range(3)], lag_ratio=0.3)], 1.2),
            "That's called",
            (lambda: self.cap("metastable failure: the trigger is gone, and the system keeps itself down", YELLOW_M), 0.7),
            "Getting out",
            (lambda: self.cap("getting out: cut the load, or restart"), 0.6),
        ])

        # ---------------- scene 6: the obvious fixes ----------------
        rows = []

        def board(text, result, color):
            y = BOARD_Y - 0.4 * len(rows)
            r = VGroup(left_at(T(text, 20, GREY_B), BOARD_X, y), right_at(T(result, 20, color), BOARD_X + 4.3, y))
            rows.append(r)
            return [FadeIn(r, shift=0.1 * LEFT)]

        def tag(text, color=WHITE):
            r = RoundedRectangle(corner_radius=0.1, width=1.9, height=0.5, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1)
            return self.put("tag", VGroup(r, T(text, 18, color)).move_to([0.1, LOOP_Y, 0]))

        self.steps("So what fixes it? The obvious idea: wait longer before each retry, doubling the wait each time, "
                   "with a random part so clients don't retry in step. That's exponential backoff with jitter.", [
            (lambda: [*self.uncap(), *board("retry up to 4, at once", "never", RED_M)], 0.7),
            "wait longer",
            (lambda: tag("wait, then double"), 0.6),
            "That's exponential",
            (lambda: self.cap("exponential backoff with jitter: wait longer each time, plus a random part", WHITE), 0.6),
        ])
        self.steps("To be fair, it spreads the retries out. But every attempt still times out, so there are just as many. "
                   "This run never recovers.", [
            (lambda: [*self.rate("1,438/s", RED_M)], 0.5),
            (lambda: [*self.rate("3,063/s", RED_M)], 0.5),
            (lambda: [*self.rate("3,228/s", RED_M)], 0.5),
            "This run",
            (lambda: [*board("backoff with jitter", "never", RED_M), *self.cap("spread out in time, but just as many", WHITE)], 0.7),
        ])
        self.steps("No retries at all? It recovers at 24 seconds. But then every everyday hiccup, like a dropped connection, becomes an error.", [
            (lambda: [*self.drop("tag"), loop.animate.set_stroke(opacity=0.15), loop_tip.animate.set_opacity(0.15),
                      self.lab["loop"].animate.set_opacity(0.2), *self.rate("800/s")], 0.7),
            "It recovers",
            (lambda: board("no retries at all", "24 s", GOLD_M), 0.6),
            "But then",
            (lambda: self.cap("a dropped connection needs exactly one retry", WHITE), 0.6),
        ])

        # ---------------- scene 7: a budget, and the bin ----------------
        self.steps("A better rule is a retry budget: retries may add at most 10% to the work coming in. "
                   "Now the server never gets more than 880 a second.", [
            (lambda: [loop.animate.set_stroke(opacity=1), loop_tip.animate.set_opacity(1), self.lab["loop"].animate.set_opacity(1), *self.uncap()], 0.6),
            "a retry budget",
            (lambda: tag("budget: +10%", GREEN_M), 0.6),
            "Now the server",
            (lambda: [*self.rate("880/s", GOLD_M), *self.cap("800 new + 10% = at most 880 a second", WHITE)], 0.7),
        ])
        self.steps("It recovers at 34 seconds. Slowly, because it still serves a backlog of attempts nobody is waiting for.", [
            (lambda: [*board("retry budget, 10%", "34 s", GOLD_M), *self.queued("queued: 2,257", WHITE), *self.clock("t = 15 s")], 0.7),
            "Slowly",
            (lambda: [*flow(3, useful=False), *self.reads("0", "1,000")], 1.8),
            (lambda: [*self.queued("queued: 457", WHITE), *self.rail(2, 3), *self.clock("t = 30 s")], 0.5),
        ])
        def home(yellow, grey):
            for k, sl in enumerate(self.slips):
                sl.move_to([SLIP_X[k], SLIP_Y, 0])
            return self.rail(yellow, grey)

        bin_r = RoundedRectangle(corner_radius=0.08, width=0.9, height=0.5, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M), 1).move_to(BIN)
        bin_t = T("bin", 18, GOLD_M).move_to(BIN)
        self.steps("So drop those too. Picture a barista who throws away slips older than three minutes. In a program, each request carries "
                   "its deadline, and the server drops attempts that are past it without working on them.", [
            (lambda: [*self.drop("tag"), *self.uncap(), *self.rail(4, 8), *self.reads("0", "400"), *self.clock("t = 11 s"),
                      sv_r.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.25), 1), swap(sv_cap2, sv_slow2), *self.rate("3,200/s", RED_M),
                      *self.queued("queued: 4,157", WHITE)], 0.8),
            "Picture a barista",
            (lambda: [FadeIn(VGroup(bin_r, bin_t), shift=0.1 * DOWN)], 0.6),
            "older than",
            (lambda: [*[self.slips[k].animate.move_to(BIN).set_opacity(0) for k in range(8)]], 1.0),
            "each request carries",
            (lambda: [*self.cap("each attempt carries its deadline; past it, the server drops it unread", WHITE), *home(4, 0)], 0.7),
        ])
        self.steps("Clients still retry four times. During the slowdown, all 400 answers a second are now useful. "
                   "And the moment the server is back to full speed, at fifteen seconds, so is the service.", [
            (lambda: [*self.rate("2,000/s", RED_M), *self.queued("queued: 404", WHITE), *self.uncap()], 0.6),
            "During the slowdown",
            (lambda: [*flow(3), *self.reads("400", "0")], 1.8),
            "And the moment",
            (lambda: [*self.clock("t = 16 s"), sv_r.animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1), swap(sv_slow2, sv_cap3),
                      *self.rate("800/s"), *self.queued("queued: 0", WHITE), *self.rail(1, 0), *self.reads("880", "0")], 0.8),
            "so is the service",
            (lambda: [*board("retry up to 4, drop expired", "15 s", GREEN_M), *flow(2)], 1.6),
        ])
        self.stamp("fixed")

        # ---------------- scene 8: a word of fairness ----------------
        self.steps("So retries aren't the villain. The trouble is retries under overload.", [
            (lambda: self.cap("the trouble: retries under overload", WHITE), 0.6),
        ])
        self.steps("And here the café picture breaks: a real customer reorders once and goes home. "
                   "A program retries four times and never gets tired.", [
            (lambda: self.cap("where the café picture breaks", GREY_B), 0.5),
            "a real customer",
            (lambda: self.cap("a customer: reorders once, goes home", BLUE_M), 0.5),
            "A program retries",
            (lambda: [*self.cap("a program: retries four times, never tires", RED_M), LaggedStart(*[dot_on(loop_path, RED_M, 0.7) for _ in range(4)], lag_ratio=0.25)], 1.4),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So why was it still down a minute later? Its own clients kept it down, asking again for answers nobody would wait for.", [
            (lambda: self.cap("why still down a minute later?", WHITE), 0.5),
            "Its own clients",
            (lambda: [glow(loop, RED_M, 1.0), glow(cl_r, BLUE_M)], 1.0),
        ])
        self.steps("Give retries a budget, and drop work nobody waits for.", [
            (lambda: [*self.cap("give retries a budget, and drop work nobody waits for", YELLOW_M, 28), glow(bin_r, GOLD_M, 1.05)], 0.9),
        ], after=0.6)
        self.steps("One quick check. With a 10% budget and 800 new requests a second, what's the most the server is ever sent? Pause and think.", [
            (lambda: [*self.cap("a 10% budget, 800 new a second: the most the server is ever sent?", WHITE), *self.rate("?/s", YELLOW_M)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("880 a second: the 800 new ones, plus 10% more.", [
            (lambda: [*self.rate("880/s", GREEN_M), *self.cap("880 a second: 800 new, plus 10%", GREEN_M, 28)], 0.7),
        ], after=0.3)
        self.play(*self.cap("give retries a budget, and drop work nobody waits for", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])
