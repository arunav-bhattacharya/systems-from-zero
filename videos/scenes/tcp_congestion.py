from sfz import *

SAY.insert(0, (r"\bCUBIC\b", "cubic"))

# the path from the payment service to its bank, drawn so its length is what it holds: 100 segments
PX0, PX1, PY = -4.4, 4.4, 2.3
SEG = (PX1 - PX0) / 100
ACK_Y = 1.72
SX, RX = -5.55, 5.55
READ_Y = 1.38
# the chart of the window, one point per round trip
OX, OY = -5.6, -3.25
UX, UY = 0.108, 0.0218
R_MAX = 110
# Reno on a path that holds 100 segments (the lesson's stepper)
KP = [(1, 10), (2, 20), (3, 40), (4, 80), (5, 160), (6, 80), (26, 100), (27, 101), (28, 50), (79, 101), (80, 50), (110, 80)]
SEG_BYTES, RTT = 1460, 0.070


def W(r):
    return float(np.interp(r, [p[0] for p in KP], [p[1] for p in KP]))


def cx(r):
    return OX + r * UX


def cy(w):
    return OY + w * UY


def speed(w):
    bps = min(w, 100) * SEG_BYTES / RTT
    return f"{bps / 1e6:.1f} MB/s" if bps >= 1e6 else f"{round(bps / 1e3, -1 if bps >= 100e3 else 0):.0f} KB/s"


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


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def seg(i, color=BLUE_M, y=PY, h=0.26):
    return Rectangle(width=SEG * 0.68, height=h, stroke_width=0).set_fill(color, 1).move_to([PX0 + (i + 0.5) * SEG, y, 0])


def drop_seg(i):
    """The i-th segment past what the path holds: a red row just above the pipe, from its right end back."""
    return seg(99 - i, RED_M, PY + 0.44, 0.18)


def fill(n):
    n = int(round(n))
    g = VGroup(*[seg(i) for i in range(min(n, 100))])
    g.add(*[drop_seg(i) for i in range(max(0, n - 100))])
    return g


class TcpCongestion(Base):
    """net-08, section 2: a settlement file over a 70 ms round trip. Stop and wait moves 20 KB/s; a window of 10
    segments moves 200 KB/s (window / round trip). The path holds 100 segments; slow start doubles 10, 20, 40, 80,
    160 overflows, three duplicate ACKs halve it to 80, +1 per round trip back to 100, 101 halves to 50: the sawtooth."""

    def construct(self):
        self.title_card("TCP congestion control", "a window that grows until a loss, then halves")

        snd = box("sender", WHITE, w=1.9, h=1.0, size=26).move_to([SX, PY, 0])
        rcv = box("bank", WHITE, w=1.9, h=1.0, size=26).move_to([RX, PY, 0])
        pipe = RoundedRectangle(corner_radius=0.12, width=PX1 - PX0, height=0.46, stroke_color=GREY_B, stroke_width=2.5)
        pipe.move_to([(PX0 + PX1) / 2, PY, 0])
        rtt = T("70 ms there and back", 20, GREY_B).move_to([0, PY + 0.8, 0])
        samp = VGroup(*[seg(i) for i in range(6)])
        self.steps("A payment service sends a settlement file to its bank, 70 milliseconds away there and back. "
                   "TCP sends it in segments of about 1,500 bytes.", [
            (lambda: [FadeIn(snd), FadeIn(rcv)], 0.8),
            "70 milliseconds",
            (lambda: [Create(pipe), FadeIn(rtt)], 0.9),
            "TCP sends",
            (lambda: [LaggedStart(*[FadeIn(m, scale=0.5) for m in samp], lag_ratio=0.25)], 1.0),
            (lambda: [FadeOut(samp)], 0.4),
        ])

        ack_ln = Arrow([PX1, ACK_Y, 0], [PX0, ACK_Y, 0], buff=0, stroke_width=2, color=GREY_D, max_tip_length_to_length_ratio=0.02)
        ack_lab = T("ACKs", 18, GREY_B).move_to([PX1 - 0.6, ACK_Y - 0.28, 0])
        win = left_at(T("1 segment per round trip", 20, BLUE_M), SX - 0.95, READ_Y)
        spd = right_at(T("speed: 21 KB/s", 20, GREEN_M), RX + 0.95, READ_Y)
        self.steps("The simplest rule: send one segment, then wait for the bank's reply, an ACK. "
                   "That's about 20 kilobytes a second, and the link sits almost empty.", [
            (lambda: [GrowArrow(ack_ln), FadeIn(ack_lab)], 0.6),
            (lambda: [self._one()], 0.9),
            (lambda: [travel(ack_ln, GREEN_M, 0.7)], 0.7),
            "That's about",
            (lambda: [FadeIn(win, shift=0.1 * UP), FadeIn(spd, shift=0.1 * UP)], 0.6),
            "and the link",
            (lambda: [glow(pipe, GREY_B, 1.01)], 0.9),
        ])

        ten = VGroup(*[seg(i) for i in range(10)])
        win10 = left_at(T("window: 10", 22, BLUE_M), SX - 0.95, READ_Y)
        self.steps("So TCP keeps many segments in flight, sent but not yet acknowledged. "
                   "How many is the window. A window of 10 sends 10 every round trip.", [
            (lambda: [LaggedStart(*[FadeIn(s, scale=0.5) for s in ten], lag_ratio=0.15)], 1.3),
            "How many is the window",
            (lambda: [Transform(win, win10)], 0.6),
            "sends 10",
            (lambda: [LaggedStart(*[travel(ack_ln, GREEN_M, 0.6) for _ in range(4)], lag_ratio=0.25)], 1.3),
        ])

        rt = ValueTracker(1)
        self.rt = rt
        formula = chip("speed = window ÷ round trip", GREEN_M, 22).move_to([3.0, -0.05, 0])
        self.steps("Speed is the window divided by the round trip. Ten segments every 70 milliseconds is about "
                   "200 kilobytes a second.", [
            (lambda: [FadeIn(formula, shift=0.1 * UP)], 0.8),
            "Ten segments",
            (lambda: [glow(formula[0], GREEN_M, 1.04)], 0.8),
            (lambda: [Transform(spd, right_at(T("speed: 210 KB/s", 20, GREEN_M), RX + 0.95, READ_Y))], 0.6),
        ])
        # from here the pipe, both readouts and the chart follow the round-trip tracker
        dyn_fill = always_redraw(lambda: fill(W(rt.get_value())))
        self.remove(ten)
        self.add(dyn_fill)

        cap_lab = T("this path holds 100 segments, counting the router's queue", 20, GREY_B).move_to([0, PY + 0.8, 0])
        xax = Line([OX, OY, 0], [cx(R_MAX) + 0.1, OY, 0], stroke_width=2.5, color=GREY_B)
        yax = Line([OX, OY, 0], [OX, cy(165), 0], stroke_width=2.5, color=GREY_B)
        ylab = left_at(T("window, in segments", 18, GREY_B), OX + 0.15, cy(165) + 0.42)
        xlab = right_at(T("round trips", 18, GREY_B), cx(R_MAX) + 0.1, OY + 0.28)
        yt = VGroup(*[right_at(T(str(v), 16, GREY_C), OX - 0.12, cy(v)) for v in (50, 100, 150)])
        cap = DashedLine([OX, cy(100), 0], [cx(R_MAX) + 0.1, cy(100), 0], dash_length=0.1, stroke_width=2, color=GREY_B)
        cap_t = right_at(T("the path holds 100", 17, GREY_B), cx(R_MAX) + 0.1, cy(100) + 0.24)
        self.steps("Bigger is faster, until the path is full. This one holds 100 segments, counting a router's queue, "
                   "and the router drops what doesn't fit. Nobody tells the sender that number.", [
            "This one holds",
            (lambda: [Transform(rtt, cap_lab)], 0.8),
            (lambda: [Create(xax), Create(yax), FadeIn(ylab), FadeIn(xlab), FadeIn(yt)], 1.0),
            (lambda: [Create(cap), FadeIn(cap_t)], 0.7),
            "Nobody tells",
            (lambda: [glow(snd[0], GOLD_M, 1.05)], 1.0),
        ])

        line = always_redraw(self._curve)
        d1 = Dot([cx(1), cy(10), 0], radius=0.05, color=BLUE_M)
        dots = {r: Dot([cx(r), cy(W(r)), 0], radius=0.05, color=BLUE_M if r < 5 else RED_M) for r in (2, 3, 4, 5)}
        dyn_win = always_redraw(lambda: left_at(T(f"window: {int(round(W(rt.get_value())))}", 22, BLUE_M), SX - 0.95, READ_Y))
        dyn_spd = always_redraw(lambda: right_at(T(f"speed: {speed(W(rt.get_value()))}", 20, GREEN_M), RX + 0.95, READ_Y))
        ss = T("slow start: double every round trip", 20, BLUE_M).move_to([0, READ_Y, 0])

        def rnd(r):
            return [(lambda: [rt.animate(rate_func=linear).set_value(r), travel(ack_ln, GREEN_M, 0.7)], 0.9),
                    (lambda: [FadeIn(dots[r], scale=0.5)], 0.25)]

        def swap_readouts():
            self.remove(win, spd)
            self.add(dyn_win, dyn_spd)
            return [FadeIn(d1, scale=0.5)]

        self.steps("So it probes. It starts at 10, and every ACK adds one more: 20, then 40, then 80. "
                   "Doubling every round trip is called slow start.", [
            (lambda: swap_readouts(), 0.5),
            (lambda: [FadeIn(line)], 0.1),
            "20, then",
            *rnd(2), *rnd(3), *rnd(4),
            "Doubling every",
            (lambda: [FadeIn(ss, shift=0.1 * UP)], 0.6),
        ])

        drop_lab = T("160 sent, 100 fit, 60 dropped", 20, RED_M).move_to([0, PY + 0.8, 0])
        self.steps("Round five sends 160. Only 100 fit, and the router drops the other 60.", [
            (lambda: [FadeOut(ss), rt.animate(rate_func=linear).set_value(5)], 1.4),
            (lambda: [FadeIn(dots[5], scale=0.5)], 0.3),
            "and the router",
            (lambda: [Transform(rtt, drop_lab)], 0.6),
        ])

        dup = T("3 duplicate ACKs: one segment is missing", 20, GOLD_M).move_to([0, READ_Y, 0])
        half = T("resend it, halve the window: 160 → 80", 20, GOLD_M).move_to([0, READ_Y, 0])
        self.steps("The bank keeps repeating its last ACK. Three duplicate ACKs tell the sender one segment is missing. "
                   "It resends it and halves the window, to 80.", [
            (lambda: [LaggedStart(*[travel(ack_ln, GOLD_M, 0.6) for _ in range(3)], lag_ratio=0.45)], 1.4),
            (lambda: [FadeIn(dup, shift=0.1 * UP)], 0.5),
            "It resends",
            (lambda: [Transform(dup, half), self._one(GOLD_M)], 0.9),
            (lambda: [rt.animate(rate_func=smooth).set_value(6), Transform(rtt, cap_lab.copy())], 0.9),
        ])

        lin = T("now: one more segment per round trip", 20, BLUE_M).move_to([0, READ_Y, 0])
        self.steps("Now it adds just one segment per round trip. Twenty round trips later it's back at 100, "
                   "and at 101 the queue overflows again: the window halves to 50.", [
            (lambda: [Transform(dup, lin)], 0.6),
            "Twenty round trips",
            (lambda: [rt.animate(rate_func=linear).set_value(26)], 2.2),
            "and at 101",
            (lambda: [rt.animate(rate_func=linear).set_value(27)], 0.6),
            "the window halves",
            (lambda: [rt.animate(rate_func=smooth).set_value(28)], 0.8),
        ])

        aimd = T("add one per round trip, halve on a loss", 20, BLUE_M).move_to([0, READ_Y, 0])
        self.steps("Then up by one, and down by half, over and over: a sawtooth. This is Reno. "
                   "Linux's default, CUBIC, cuts less, but also backs off on loss.", [
            (lambda: [Transform(dup, aimd)], 0.6),
            (lambda: [rt.animate(rate_func=linear).set_value(79)], 3.0),
            (lambda: [rt.animate(rate_func=smooth).set_value(80)], 0.5),
            (lambda: [rt.animate(rate_func=linear).set_value(110)], 2.0),
        ])

        avg = DashedLine([cx(28), cy(75), 0], [cx(R_MAX), cy(75), 0], dash_length=0.08, stroke_width=2.5, color=GREEN_M)
        avg_t = left_at(T("average: about 75", 17, GREEN_M), cx(28) + 0.15, cy(75) + 0.25)
        f75 = chip("75 segments every 70 ms: 1.6 MB/s", GREEN_M, 22).move_to(formula)
        self.steps("On average it fills three quarters of the path: about 1.6 megabytes a second.", [
            (lambda: [Create(avg), FadeIn(avg_t)], 0.9),
            "about 1.6",
            (lambda: [Transform(formula, f75)], 0.8),
        ])

        cuts = VGroup(*[Circle(radius=0.2, color=RED_M, stroke_width=3).move_to([cx(r), cy(W(r)), 0]) for r in (5, 27, 79)])
        self.steps("Each loss halves the speed too. That's why losing one packet in a hundred can make a download "
                   "ten times slower.", [
            (lambda: [LaggedStart(*[Create(c) for c in cuts], lag_ratio=0.3)], 1.2),
            "That's why",
            (lambda: [*[c.animate(rate_func=there_and_back).scale(1.4) for c in cuts]], 1.0),
        ])

        self.steps("The sender can't see the network. It grows the window until a loss, then halves it, "
                   "and its speed is the window divided by the round trip.", [
            (lambda: [FadeOut(cuts), glow(snd[0], GOLD_M, 1.05)], 0.9),
            "It grows the",
            (lambda: [line.animate(rate_func=there_and_back).set_stroke(width=8)], 1.2),
            "and its speed",
            (lambda: [glow(formula[0], GREEN_M, 1.04)], 1.0),
        ])
        self.wait(0.6)

    def _one(self, color=BLUE_M):
        s = seg(0, color)
        return Succession(FadeIn(s, run_time=0.05), s.animate(run_time=0.75, rate_func=linear).move_to([PX1 - SEG / 2, PY, 0]),
                          FadeOut(s, run_time=0.1))

    def _curve(self):
        r = self.rt.get_value()
        pts = [[cx(a), cy(b), 0] for a, b in KP if a <= r + 1e-6]
        last = max(a for a, b in KP if a <= r + 1e-6)
        if r - last > 1e-6:
            pts.append([cx(r), cy(W(r)), 0])
        m = VMobject(stroke_color=BLUE_M, stroke_width=4)
        if len(pts) < 2:
            pts = pts + [[pts[0][0] + 0.001, pts[0][1], 0]]
        m.set_points_as_corners(pts)
        return m
