from sfz import *

SAY.insert(0, (r"\bCUBIC\b", "cubic"))
SAY.insert(0, (r"\bkbit/s\b", "kilobits a second"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RY = 2.65                                   # the road, the warehouse and the shop
SND = np.array([-5.75, RY, 0])              # the warehouse: the sender
RCV = np.array([5.75, RY, 0])               # the shop: the receiver
BW, BH = 1.6, 1.0
X0, X1 = -4.75, 3.95                        # the road's 100 slots, the last 30 of them the car park
SW = (X1 - X0) / 100
PARK = 70                                   # first slot of the car park
OVER_Y = 3.12                               # vans turned away
LBL_Y = 2.2                                 # labels under the road
LANE_Y = 1.85                               # signed notes come back along this lane
READ_Y = 1.32                               # the guess, by the warehouse
OX, OY = -5.6, -2.75                        # the chart of the guess, one point per round trip
R_MAX = 85
UX, UY = (5.9 - OX) / R_MAX, 3.6 / 170
CAP_Y, BAR_Y = -3.2, -2.95

# Reno on a path that holds 100 segments (the lesson's stepper)
KP = [(1, 10), (2, 20), (3, 40), (4, 80), (5, 160), (6, 80), (26, 100), (27, 101), (28, 50), (79, 101), (80, 50), (85, 55)]


def W(r):
    return float(np.interp(r, [p[0] for p in KP], [p[1] for p in KP]))


def cx(r):
    return OX + r * UX


def cy(w):
    return OY + w * UY


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

    def steps(self, text, items, after=0.2):
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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def place(c, name, sub, color):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(name, 20).move_to(c + [0, 0.17, 0])), T(sub, 16, GREY_B).move_to(c + [0, -0.22, 0])


def road():
    body = RoundedRectangle(corner_radius=0.06, width=X1 - X0 + 0.08, height=0.36, stroke_color=GREY_C, stroke_width=2.5)
    body.move_to([(X0 + X1) / 2, RY, 0])
    return body


def car_park():
    x0 = X0 + PARK * SW
    r = Rectangle(width=X1 - x0 + 0.04, height=0.5, stroke_color=GOLD_M, stroke_width=2.5).move_to([(x0 + X1) / 2, RY, 0])
    return r


def bridge():
    a, b = X1 + 0.06, RCV[0] - BW / 2 - 0.06
    return VGroup(Line([a, RY + 0.09, 0], [b, RY + 0.09, 0]), Line([a, RY - 0.09, 0], [b, RY - 0.09, 0])).set_stroke(GOLD_M, 3)


def van(i, color=BLUE_M, y=RY, h=0.22):
    return Rectangle(width=SW * 0.68, height=h, stroke_width=0).set_fill(color, 1).move_to([X0 + (i + 0.5) * SW, y, 0])


_cache = {}


def vans(n, over=True):
    """n vans: the first 100 fill the road from the warehouse end; the rest are turned away (red, above the car park)."""
    n = int(round(n))
    key = (n, over)
    if key not in _cache:
        g = VGroup(*[van(i) for i in range(min(n, 100))])
        if over:
            g.add(*[van(99 - i, RED_M, OVER_Y, 0.17) for i in range(max(0, n - 100))])
        _cache[key] = g
    return _cache[key].copy()


def lane():
    return Arrow([RCV[0] - BW / 2 - 0.1, LANE_Y, 0], [SND[0] + BW / 2 + 0.1, LANE_Y, 0], buff=0, stroke_width=2, color=GREY_D,
                 max_tip_length_to_length_ratio=0.02)


def notes_back(k=4, color=GREEN_M, rt=0.8):
    ln = Line([RCV[0] - BW / 2 - 0.1, LANE_Y, 0], [SND[0] + BW / 2 + 0.1, LANE_Y, 0])
    return LaggedStart(*[travel(ln, color, rt) for _ in range(k)], lag_ratio=0.25)


LEG_Y = [0.75, 0.2, -0.35, -0.9, -1.45, -2.0]


def legend_row(k, left, right, color=WHITE):
    """One line of the map from the van picture to the network: left = right."""
    y = LEG_Y[k]
    return VGroup(right_at(T(left, 26, GREY_B), -0.35, y), T("=", 26, GREY_B).move_to([0, y, 0]), left_at(T(right, 26, color), 0.35, y))


class TcpCongestion(Base):
    """net-08, section 2. The lesson's vans: a warehouse keeps several vans on the road, but nobody says how much the
    road can take. A narrow bridge with a car park (the bottleneck link and its router's queue) turns vans away when
    full. Resending harder caused the 1986 collapse. So the sender keeps its own guess: slow start doubles 10, 20, 40, 80;
    160 overflows; three duplicate ACKs, resend, halve to 80; +1 per round trip to 100; 101 halves to 50: the sawtooth.
    Names, CUBIC, the cost of loss, the moral, and a check (90 halves to 45)."""

    def readout(self):
        r = self.rt.get_value()
        g = VGroup(T(self.rlabel + ":", 22, BLUE_M), M(str(int(round(W(r)))), 24, BLUE_M)).arrange(RIGHT, buff=0.15)
        return left_at(g, -6.5, READ_Y)

    def curve(self):
        r = self.rt.get_value()
        pts = [[cx(a), cy(b), 0] for a, b in KP if a <= r + 1e-6]
        last = max(a for a, b in KP if a <= r + 1e-6)
        if r - last > 1e-6:
            pts.append([cx(r), cy(W(r)), 0])
        if len(pts) < 2:
            pts = pts + [[pts[0][0] + 0.001, pts[0][1], 0]]
        return VMobject(stroke_color=BLUE_M, stroke_width=4).set_points_as_corners(pts)

    def construct(self):
        self.capm = None
        self.rlabel = "the guess"
        self.show_over = True
        self.title_card("How fast may I send?", "TCP feels for a limit nobody tells it")

        # ---------------- scene 1: the question ----------------
        wh, wh_sub = place(SND, "warehouse", "the sender", BLUE_M)
        sh, sh_sub = place(RCV, "shop", "the receiver", GREEN_M)
        rd = road()
        ln = lane()
        notes_l = T("signed notes", 17, GREY_B).move_to([0, LANE_Y - 0.25, 0])
        first = vans(10)
        self.steps("A warehouse sends parcels by van to a shop far away. It doesn't wait for each van to come back. "
                   "It keeps several on the road at once, and each signed note from the shop frees a place for one more.", [
            (lambda: [FadeIn(wh), FadeIn(sh)], 0.8),
            (lambda: [Create(rd)], 0.7),
            "It keeps several",
            (lambda: [LaggedStart(*[FadeIn(v, shift=0.15 * RIGHT) for v in first], lag_ratio=0.15)], 1.2),
            "each signed note",
            (lambda: [GrowArrow(ln), FadeIn(notes_l)], 0.6),
            (lambda: [notes_back(4)], 1.4),
        ])
        leg = [legend_row(0, "a van", "a segment, one TCP packet", BLUE_M), legend_row(1, "a signed note", "an ACK", GREEN_M),
               legend_row(2, "vans out at once", "the window", BLUE_M), legend_row(3, "the bridge", "the slowest link on the path", GOLD_M),
               legend_row(4, "the car park", "the router's queue", GOLD_M), legend_row(5, "turned away", "dropped", RED_M)]
        win_br = Brace(VGroup(*first), UP, buff=0.08, color=BLUE_M)
        win_t = T("the window", 20, BLUE_M).next_to(win_br, UP, buff=0.08)
        self.steps("In TCP, the vans are segments, its packets, and how many may be out at once is the window. More vans, more speed.", [
            (lambda: [FadeIn(wh_sub), FadeIn(sh_sub), FadeIn(leg[0], shift=0.1 * UP)], 0.7),
            "its packets",
            (lambda: [FadeIn(leg[1], shift=0.1 * UP)], 0.5),
            "is the window",
            (lambda: [GrowFromCenter(win_br), FadeIn(win_t), FadeIn(leg[2], shift=0.1 * UP)], 0.7),
            "More vans",
            (lambda: [*self.cap("more vans out at once: more speed")], 0.5),
        ])
        self.steps("The shop says how much room it has. But nobody says how much the road can take. "
                   "So how many vans should the warehouse send?", [
            (lambda: [FadeOut(win_br), FadeOut(win_t), glow(sh[0], GREEN_M, 1.05)], 0.8),
            "But nobody",
            (lambda: [glow(rd, YELLOW_M, 1.0)], 0.9),
            "So how many",
            (lambda: self.cap("how many vans should it send?", YELLOW_M, 28), 0.6),
        ])

        # ---------------- scene 2: the bridge ----------------
        cp, br = car_park(), bridge()
        cp_l = T("car park", 18, GOLD_M).move_to([(X0 + PARK * SW + X1) / 2, LBL_Y, 0])
        br_l = T("bridge", 18, GOLD_M).move_to([(X1 + RCV[0] - BW / 2) / 2, LBL_Y, 0])
        rd_l = T("the road", 18, GREY_B).move_to([(X0 + X0 + PARK * SW) / 2, LBL_Y, 0])
        self.steps("Somewhere on the way is the narrowest part, the bottleneck. Picture a narrow bridge, with a small car park in front of it.", [
            (lambda: [*self.uncap(), FadeOut(first)], 0.5),
            "Picture a narrow",
            (lambda: [Create(br), FadeIn(br_l)], 0.7),
            "a small car park",
            (lambda: [Create(cp), FadeIn(cp_l), FadeIn(rd_l)], 0.7),
        ])
        full = vans(100, over=False)
        away = VGroup(*[van(99 - i, RED_M, OVER_Y, 0.17) for i in range(12)])
        self.steps("Vans that arrive faster than the bridge lets them over wait in the car park. When the car park is full, "
                   "the next vans are turned away, and their parcels are lost.", [
            (lambda: [LaggedStart(*[FadeIn(v) for v in full], lag_ratio=0.02)], 1.6),
            "When the car park",
            (lambda: [glow(cp, GOLD_M, 1.02)], 0.7),
            "turned away",
            (lambda: [LaggedStart(*[FadeIn(v, shift=0.15 * DOWN) for v in away], lag_ratio=0.1)], 1.0),
        ])
        self.steps("In a network, the bridge is the slowest link on the path. The car park is the queue in the router in front of it, "
                   "a waiting area for packets. And turned away means dropped.", [
            (lambda: [FadeIn(leg[3], shift=0.1 * UP), glow(br, GOLD_M, 1.0)], 0.7),
            "The car park is",
            (lambda: [FadeIn(leg[4], shift=0.1 * UP), glow(cp, GOLD_M, 1.02)], 0.7),
            "And turned away",
            (lambda: [FadeIn(leg[5], shift=0.1 * UP), Indicate(away, color=RED_M)], 0.7),
        ])
        hold = Brace(VGroup(rd, cp), DOWN, buff=0.48, color=GREY_B)
        hold_t = T("together they hold 100", 18, GREY_B).next_to(hold, DOWN, buff=0.06)
        self.steps("Here, the road and the car park together hold 100 vans. The warehouse doesn't know that number.", [
            (lambda: [FadeOut(away), *self.uncap(), FadeOut(rd_l), FadeOut(cp_l), FadeOut(br_l), FadeOut(notes_l), FadeOut(ln)], 0.5),
            (lambda: [GrowFromCenter(hold), FadeIn(hold_t)], 0.7),
            "The warehouse doesn't",
            (lambda: [glow(wh[0], BLUE_M, 1.05), *self.cap("the warehouse doesn't know that number")], 0.7),
        ])

        # ---------------- scene 3: the obvious fix, broken ----------------
        jam1 = VGroup(*[van(99 - i, RED_M, OVER_Y, 0.17) for i in range(25)])
        jam2 = VGroup(*[van(99 - i, RED_M, OVER_Y, 0.17) for i in range(25, 60)])
        self.steps("So parcels get lost. The obvious fix: send them again, just as fast. But the car park is already full. "
                   "Resending at the same speed only adds more vans to the jam.", [
            (lambda: [FadeOut(hold), FadeOut(hold_t), FadeIn(rd_l), FadeIn(cp_l), FadeIn(br_l), FadeIn(ln),
                      LaggedStart(*[FadeIn(v, shift=0.15 * DOWN) for v in jam1], lag_ratio=0.05)], 1.0),
            "The obvious fix",
            (lambda: self.cap("the obvious fix: send them again, just as fast"), 0.5),
            "already full",
            (lambda: [glow(cp, RED_M, 1.02)], 0.7),
            "only adds",
            (lambda: [LaggedStart(*[FadeIn(v, shift=0.15 * DOWN) for v in jam2], lag_ratio=0.04), *self.cap("more vans, the same bridge: a bigger jam", RED_M)], 1.2),
        ])
        self.steps("In October 1986, the early internet did exactly that. A link between two university sites at Berkeley fell "
                   "from 32 kilobits a second to 40 bits a second. Bits, not kilobits.", [
            (lambda: self.cap("October 1986, Berkeley: 32 kbit/s"), 0.5),
            "to 40 bits",
            (lambda: self.cap("October 1986, Berkeley: 32 kbit/s  to  40 bit/s", RED_M), 0.5),
            "Bits, not",
            (lambda: [Indicate(self.capm, color=RED_M, scale_factor=1.06)], 0.8),
        ])
        self.steps("That's called congestion collapse. The fix came from Van Jacobson, no relation to our vans. "
                   "It's called congestion control, and it's been part of TCP since the late 1980s.", [
            (lambda: self.cap("congestion collapse: everyone keeps sending, almost nothing gets through", RED_M), 0.5),
            "The fix came",
            (lambda: [FadeOut(jam1), FadeOut(jam2), FadeOut(full), *self.uncap()], 0.8),
            "It's called congestion",
            (lambda: self.cap("congestion control: part of TCP since the late 1980s", WHITE), 0.5),
        ])

        # ---------------- scene 4: a guess that grows ----------------
        self.rt = ValueTracker(1)
        read = always_redraw(self.readout)
        dyn = always_redraw(lambda: vans(W(self.rt.get_value()), self.show_over))
        self.steps("The idea: the sender keeps its own guess of how much the road can take, and never has more on the road than that guess, "
                   "or the shop's room, whichever is smaller.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*leg)), FadeIn(read, shift=0.1 * UP)], 0.6),
            "never has more",
            (lambda: [FadeIn(dyn)], 0.6),
            "or the shop's room",
            (lambda: [glow(sh[0], GREEN_M, 1.05), *self.cap("on the road: never more than the guess, or the shop's room, whichever is smaller")], 0.8),
        ])
        xax = Line([OX, OY, 0], [cx(R_MAX) + 0.1, OY, 0], stroke_width=2.5, color=GREY_B)
        yax = Line([OX, OY, 0], [OX, cy(170), 0], stroke_width=2.5, color=GREY_B)
        yt = VGroup(*[right_at(T(str(v), 16, GREY_C), OX - 0.12, cy(v)) for v in (50, 100, 150)])
        ylab = right_at(T("the guess, each round trip", 18, GREY_B), cx(R_MAX) + 0.1, cy(160))
        xlab = right_at(T("round trips", 18, GREY_B), cx(R_MAX) + 0.1, OY + 0.25)
        capl = DashedLine([OX, cy(100), 0], [cx(R_MAX) + 0.1, cy(100), 0], dash_length=0.1, stroke_width=2, color=GREY_B)
        capl_t = T("the road holds 100", 17, GREY_B).move_to([0.6, cy(100) + 0.22, 0])
        self.steps("Nobody tells it the right number. So it tries, and it treats a lost parcel as the signal that it went too far.", [
            (lambda: [*self.uncap(), Create(xax), Create(yax), FadeIn(yt), FadeIn(ylab), FadeIn(xlab)], 1.0),
            (lambda: [Create(capl), FadeIn(capl_t)], 0.7),
            "it treats",
            (lambda: self.cap("a lost parcel = the signal: too far"), 0.5),
        ])
        line = always_redraw(self.curve)
        dots = {r: Dot([cx(r), cy(W(r)), 0], radius=0.05, color=BLUE_M if r < 5 else RED_M) for r in (1, 2, 3, 4, 5)}

        def rnd(r, k=4):
            return [(lambda: [self.rt.animate(rate_func=linear).set_value(r), notes_back(k, GREEN_M, 0.6)], 0.9),
                    (lambda: [FadeIn(dots[r], scale=0.5)], 0.2)]

        self.steps("A new connection starts small, at 10 segments, about 14 kilobytes on Linux. Each signed note that comes back adds one more. "
                   "So 10 out means 10 notes back, and 20 next time.", [
            (lambda: [*self.uncap(), FadeIn(dots[1], scale=0.5), FadeIn(line)], 0.5),
            "about 14",
            (lambda: self.cap("start: 10 segments, about 14 KB on Linux"), 0.5),
            "Each signed note",
            (lambda: [notes_back(5, GREEN_M, 0.7), *self.cap("each signed note back: one more van")], 1.4),
            "and 20 next",
            *rnd(2),
        ])
        self.steps("Then 40, then 80. The guess doubles every round trip. This is called slow start. Nobody promised the names would be honest.", [
            *rnd(3), *rnd(4),
            "This is called",
            (lambda: self.cap("slow start: it doubles every round trip", BLUE_M), 0.5),
        ], after=0.4)

        # ---------------- scene 5: predict the overflow ----------------
        self.steps("80 still fits in 100. Next round, it doubles again. What happens? Pause and guess.", [
            (lambda: [*self.uncap(), Indicate(capl_t, color=WHITE)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        lost_t = T("60 turned away", 18, RED_M)
        self.steps("160 vans. 100 fit on the road and in the car park. The other 60 are turned away.", [
            (lambda: [*self.uncap(), self.rt.animate(rate_func=linear).set_value(5)], 1.2),
            (lambda: [FadeIn(dots[5], scale=0.5)], 0.3),
            "The other 60",
            (lambda: [FadeIn(right_at(lost_t, X1 - 60 * SW - 0.15, OVER_Y)), *self.cap("160 sent: 100 fit, 60 dropped", RED_M)], 0.6),
        ])

        # ---------------- scene 6: the signal, and the halving ----------------
        self.steps("How does the warehouse find out? The parcels behind the lost ones still arrive. "
                   "So the shop keeps sending the same note: I'm still missing the one after this.", [
            (lambda: [*self.uncap()], 0.3),
            "The parcels behind",
            (lambda: [notes_back(3, GREEN_M, 0.7)], 1.2),
            "the same note",
            (lambda: self.cap("the same note again: still missing the one after this", GOLD_M), 0.5),
            (lambda: [notes_back(3, GOLD_M, 0.7)], 1.2),
        ])
        resend = Rectangle(width=SW * 0.68 * 2, height=0.17, stroke_width=0).set_fill(GOLD_M, 1)

        def go_resend():
            self.show_over = False
            resend.move_to([X0, OVER_Y, 0])
            return [FadeOut(lost_t), Succession(FadeIn(resend, run_time=0.1),
                                                resend.animate(run_time=0.9, rate_func=smooth).move_to([X1, OVER_Y, 0]),
                                                FadeOut(resend, run_time=0.15))]

        self.steps("Three repeats of the same note, three duplicate ACKs, say exactly one parcel went missing. "
                   "The sender resends it at once, which is called fast retransmit. And it cuts its guess in half, to 80.", [
            "three duplicate",
            (lambda: self.cap("three duplicate ACKs: exactly one parcel is missing", GOLD_M), 0.5),
            "The sender resends",
            (lambda: go_resend(), 1.2),
            "fast retransmit",
            (lambda: self.cap("fast retransmit: resend it at once", GOLD_M), 0.5),
            "And it cuts",
            (lambda: [self.rt.animate(rate_func=smooth).set_value(6), *self.cap("then halve the guess: 160 to 80", WHITE)], 0.9),
        ])
        self.show_over = True
        self.steps("Above that point, it grows gently: one more segment per round trip. Twenty round trips later, it's back at 100.", [
            "one more segment",
            (lambda: self.cap("now: one more per round trip", BLUE_M), 0.5),
            "Twenty round trips",
            (lambda: [self.rt.animate(rate_func=linear).set_value(26), notes_back(8, GREEN_M, 0.6)], 2.4),
        ])
        self.steps("At 101, the car park overflows again, and the guess drops by half, to 50. Then up by one, down by half, again and again.", [
            (lambda: [self.rt.animate(rate_func=linear).set_value(27)], 0.6),
            "the guess drops",
            (lambda: [self.rt.animate(rate_func=smooth).set_value(28)], 0.7),
            "Then up by one",
            (lambda: [self.rt.animate(rate_func=linear).set_value(79)], 2.2),
            (lambda: [self.rt.animate(rate_func=smooth).set_value(80)], 0.4),
            (lambda: [self.rt.animate(rate_func=linear).set_value(85)], 0.6),
        ])

        # ---------------- scene 7: names, and the worse case ----------------
        self.steps("The pattern has a name: additive increase, multiplicative decrease. Add one at a time, cut in half at once.", [
            (lambda: self.cap("additive increase, multiplicative decrease", WHITE, 28), 0.6),
            "Add one at a time",
            (lambda: self.cap("add one at a time, cut in half at once", WHITE), 0.5),
        ])

        def rename():
            self.rlabel = "congestion window"
            read.update()
            return [Circumscribe(read, color=BLUE_M, buff=0.12)]

        avg = DashedLine([cx(28), cy(75), 0], [cx(R_MAX), cy(75), 0], dash_length=0.08, stroke_width=2.5, color=GREEN_M)
        avg_t = left_at(T("average: about 75", 17, GREEN_M), cx(29), cy(75) + 0.22)
        self.steps("The sender's guess is the congestion window. On the chart, it draws a sawtooth. "
                   "On average, it sits at about three quarters of what the road holds.", [
            "congestion window",
            (lambda: [*rename(), *self.cap("the sender's guess = the congestion window", BLUE_M)], 0.8),
            "a sawtooth",
            (lambda: [line.animate(rate_func=there_and_back).set_stroke(width=8)], 1.0),
            "On average",
            (lambda: [Create(avg), FadeIn(avg_t)], 0.8),
        ])
        self.steps("And if nothing comes back at all, not even a repeat, that's worse news. The guess drops to 1, and slow start begins again.", [
            (lambda: self.cap("nothing back at all, for a whole timeout", RED_M), 0.5),
            "The guess drops",
            (lambda: self.cap("then the guess drops to 1, and slow start begins again", RED_M), 0.5),
        ])

        # ---------------- scene 8: two warnings ----------------
        self.steps("Two warnings. First, Linux doesn't run this plain version, called Reno. Its default since 2006 is CUBIC, "
                   "which cuts to 70 percent, not half, and grows back along a curve. Same idea, a flatter sawtooth.", [
            (lambda: [FadeOut(avg), FadeOut(avg_t), *self.cap("this plain version: Reno", WHITE)], 0.5),
            "Its default",
            (lambda: self.cap("Linux's default since 2006: CUBIC. cuts to 70%, grows back along a curve", WHITE), 0.5),
            "Same idea",
            (lambda: [line.animate(rate_func=there_and_back).set_stroke(width=8)], 1.0),
        ])
        cuts = VGroup(*[Circle(radius=0.2, color=RED_M, stroke_width=3).move_to([cx(r), cy(W(r)), 0]) for r in (5, 27, 79)])
        self.steps("Second, loss is expensive. On the lab network, with a 50 millisecond delay, a 10 megabyte download took about 2 seconds. "
                   "With one packet in a hundred dropped, it took about 20.", [
            (lambda: [LaggedStart(*[Create(c) for c in cuts], lag_ratio=0.3), *self.cap("loss is expensive")], 1.0),
            "a 10 megabyte",
            (lambda: self.cap("10 MB, 50 ms delay, no loss: about 2 seconds", GREEN_M), 0.5),
            "With one packet",
            (lambda: self.cap("10 MB, 50 ms delay, 1 packet in 100 lost: about 20 seconds", RED_M), 0.5),
        ])
        self.steps("So when a fast line feels slow, look for loss before you buy a bigger road.", [
            (lambda: [FadeOut(cuts), *self.cap("a fast line feels slow? look for loss first", YELLOW_M)], 0.6),
        ], after=0.4)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, how many vans? The sender can't see the road. It feels for the limit: grow until a parcel is lost, cut in half, and grow again.", [
            (lambda: self.cap("how many vans?", WHITE), 0.5),
            "It feels",
            (lambda: [line.animate(rate_func=there_and_back).set_stroke(width=8), *self.cap("grow until a loss, halve, grow again", BLUE_M, 28)], 1.2),
        ])
        self.steps("Everyone sharing the road does the same, and that's what keeps it moving.", [
            (lambda: [glow(br, GOLD_M, 1.0), glow(cp, GOLD_M, 1.02)], 0.9),
        ])
        q90 = VGroup(T("congestion window:", 22, BLUE_M), M("90", 24, BLUE_M)).arrange(RIGHT, buff=0.15)
        left_at(q90, -6.5, READ_Y)
        qm = T("three duplicate ACKs. next?", 20, YELLOW_M).next_to(q90, RIGHT, buff=0.4)
        self.steps("One quick check. The guess is 90 when three duplicate ACKs arrive. What is it next? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(read), FadeIn(q90)], 0.5),
            "three duplicate",
            (lambda: [FadeIn(qm, shift=0.1 * LEFT), notes_back(3, GOLD_M, 0.6)], 1.0),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        a45 = VGroup(T("congestion window:", 22, BLUE_M), M("45", 24, GREEN_M)).arrange(RIGHT, buff=0.15)
        left_at(a45, -6.5, READ_Y)
        half = T("half of 90, then +1 each round trip", 20, GREEN_M).next_to(a45, RIGHT, buff=0.4)
        self.steps("45. Half of 90. Then it climbs by one each round trip.", [
            (lambda: [*self.uncap(), swap(q90, a45), FadeOut(qm)], 0.6),
            (lambda: [FadeIn(half, shift=0.1 * LEFT)], 0.5),
        ], after=0.3)
        self.play(*self.cap("grow until a loss, halve, grow again", BLUE_M, 28), run_time=0.7)
        self.wait(2.0)
