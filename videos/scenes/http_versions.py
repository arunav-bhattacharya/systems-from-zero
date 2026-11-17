from sfz import *

SAY.insert(0, (r"\b1,000\b", "one thousand"))
SAY.insert(0, (r"\b3,000\b", "three thousand"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
# left: the bank (the kitchen) with three answers; middle: the connection (the hatch); right: your app's computer,
# with the app's three streams on top and TCP's receive buffer underneath; bottom: when each answer arrived.
BK_X0, BK_X1 = -6.55, -3.35
AP_X0, AP_X1 = 3.15, 6.55
BOX_TOP, BOX_BOT = 3.35, -0.55
BK_CX, AP_CX = (BK_X0 + BK_X1) / 2, (AP_X0 + AP_X1) / 2
PY = 0.15                                   # the connection's centre line, and TCP's slots
P0, P1 = BK_X1, AP_X0
PIPE_MID = (P0 + P1) / 2
SLOT_X = [3.9, 4.85, 5.8]                   # TCP's slots, in byte order, and the app's streams above them
CHIP_Y, DIV_Y = 2.2, 1.55
CARD_Y = [2.2, 1.5, 0.8]                    # the three answers inside the bank
COLS = [BLUE_M, TEAL_M, GOLD_M]
STREAMS = ["1", "3", "5"]
X0, XS = -4.5, 9.8 / 900                    # chart: x of 0 ms, units per ms
BAR_YS = [-1.55, -2.1, -2.65]
CAP_Y, CD_Y = -3.33, -3.0
LANES = [PY + 0.46, PY, PY - 0.46]


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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def frame_box(x0, x1, color):
    return RoundedRectangle(corner_radius=0.16, width=x1 - x0, height=BOX_TOP - BOX_BOT, stroke_color=color,
                            stroke_width=3).set_fill(fillc(color, 0.08), 1).move_to([(x0 + x1) / 2, (BOX_TOP + BOX_BOT) / 2, 0])


def card(k):
    r = RoundedRectangle(corner_radius=0.1, width=2.75, height=0.56, stroke_color=COLS[k], stroke_width=2.5).set_fill(fillc(COLS[k], 0.3), 1)
    return VGroup(r, T(f"answer, stream {STREAMS[k]}", 22).move_to(r)).move_to([BK_CX, CARD_Y[k], 0])


def seg(k, s=1.0, y=PY):
    sq = RoundedRectangle(corner_radius=0.07, width=0.6, height=0.6, stroke_color=COLS[k], stroke_width=3).set_fill(fillc(COLS[k], 0.45), 1)
    return VGroup(sq, M(str(k + 1), 26).move_to(sq)).scale(s).move_to([P0 + 0.45, y, 0])


def slot(k):
    return DashedVMobject(Square(0.7, stroke_color=GREY_B, stroke_width=2), num_dashes=16).move_to([SLOT_X[k], PY, 0])


def chip(k, done=False):
    r = RoundedRectangle(corner_radius=0.08, width=0.7, height=0.7, stroke_color=COLS[k], stroke_width=3)
    r.set_fill(fillc(COLS[k], 0.55) if done else BLACK, 1)
    if not done:
        r.set_stroke(opacity=0.55)
    return VGroup(r, T(STREAMS[k], 28, WHITE if done else GREY_B).move_to(r)).move_to([SLOT_X[k], CHIP_Y, 0])


def pipe_one():
    return VGroup(*[Line([P0, PY + d, 0], [P1, PY + d, 0], stroke_width=3, color=GREY_B) for d in (0.45, -0.45)])


def pipe_three():
    """Three separate connections: three thin pipes."""
    g = VGroup()
    for y in LANES:
        g.add(Line([P0, y + 0.19, 0], [P1, y + 0.19, 0], stroke_width=2.5, color=GREY_B),
              Line([P0, y - 0.19, 0], [P1, y - 0.19, 0], stroke_width=2.5, color=GREY_B))
    return g


def pipe_lanes():
    """One connection with a lane per stream."""
    outer = VGroup(*[Line([P0, PY + d, 0], [P1, PY + d, 0], stroke_width=3, color=GREY_B) for d in (0.7, -0.7)])
    seps = VGroup(*[DashedLine([P0, PY + d, 0], [P1, PY + d, 0], dash_length=0.12, stroke_width=1.8, color=GREY_C) for d in (0.23, -0.23)])
    return VGroup(outer, seps)


def bar(k, ms, color=None):
    r = Rectangle(width=max(ms * XS, 0.01), height=0.32, stroke_width=0).set_fill(color or COLS[k], 0.85)
    left_at(r, X0, BAR_YS[k])
    return r


def bar_lab(r, s, color=WHITE):
    return T(s, 24, color).next_to(r, RIGHT, buff=0.15)


class HttpVersions(Base):
    """net-11, section 2. The bank sends three 1,000-byte answers (streams 1, 3 and 5) on one HTTP/2 connection, one
    segment each, 50 ms each way. Lose segment 1: all three requests finish about 120 ms late (0.509 s becomes 0.627 s),
    because TCP hands bytes over only in order. The café's single hatch; head-of-line blocking one layer down;
    HTTP/1.1 with three connections (two on time, one 330 ms late on a timer); QUIC's lane per stream; when it
    matters (loss on phones, rare in a data center); a check: lose segment 3 instead."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar_ = Line([-1.0, CD_Y, 0], [1.0, CD_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar_), run_time=0.25)
        self.play(Uncreate(bar_), run_time=secs, rate_func=linear)

    def relabel(self, key, s, color=WHITE, size=28):
        """Swap one of the fixed titles (bank, app, buffer, pipe)."""
        pos = {"bank": [BK_CX, 2.93, 0], "app": [AP_CX, 2.93, 0], "buf": [AP_CX, 1.13, 0], "pipe": [PIPE_MID, PY + 0.8, 0],
               "pipe3": [PIPE_MID, PY + 1.05, 0]}
        k = "pipe" if key == "pipe3" else key
        new = T(s, size, color).move_to(pos[key])
        old, self.lab[k] = self.lab[k], new
        return [swap(old, new)]

    def set_chip(self, k, done):
        new = chip(k, done)
        old, self.chips[k] = self.chips[k], new
        return [ReplacementTransform(old, new)] if old is not None else [FadeIn(new)]

    def chips_reset(self):
        out = []
        for k in range(3):
            out += self.set_chip(k, False)
        return out

    def travel(self, k, lost=False, lane=None, rt=0.9):
        """A segment leaves the bank and runs along the connection to its slot (or is lost halfway)."""
        y = PY if lane is None else LANES[k]
        s = seg(k, 1.0 if lane is None else 0.72, y)
        self.segs[k] = s
        if lost:
            x = tick(False, 0.2).move_to([PIPE_MID - 1.2, PY - 0.95, 0])
            self.lost_x = x
            path = [FadeIn(s, run_time=0.1), s.animate(run_time=rt * 0.35, rate_func=linear).move_to([PIPE_MID - 1.2, y, 0]),
                    AnimationGroup(s.animate(run_time=0.35).shift(0.9 * DOWN).set_opacity(0), Create(x, run_time=0.35))]
        else:
            path = [FadeIn(s, run_time=0.1), s.animate(run_time=rt, rate_func=linear).move_to([AP_X0 - 0.1, y, 0]),
                    s.animate(run_time=0.3).move_to([SLOT_X[k], PY, 0]).scale(1.0 if lane is None else 1 / 0.72)]
        return Succession(*path)

    def rise(self, ks):
        """TCP (or QUIC) hands these segments up to the app: each lands on its stream, which turns done."""
        out = []
        for k in ks:
            s = self.segs[k]
            out.append(s.animate.move_to([SLOT_X[k], CHIP_Y, 0]).set_opacity(0))
            out += self.set_chip(k, True)
            self.segs[k] = None
        return out

    def clear_round(self):
        out = [FadeOut(s) for s in self.segs if s is not None]
        self.segs = [None, None, None]
        if self.lost_x is not None:
            out.append(FadeOut(self.lost_x))
            self.lost_x = None
        return out + self.chips_reset()

    def set_bars(self, specs):
        """specs: list of (ms, colour, label) per row, or None to leave a row empty."""
        out = []
        for k, sp in enumerate(specs):
            if sp is None:
                continue
            old = self.bars[k]
            if old is not None:
                out.append(FadeOut(old))
            if sp == "clear":
                self.bars[k] = None
                continue
            ms, color, s = sp
            r = bar(k, ms, color)
            g = VGroup(r, bar_lab(r, s))
            self.bars[k] = g
            out.append(Succession(GrowFromEdge(r, LEFT, run_time=0.6), FadeIn(g[1], run_time=0.2)))
        return out

    def set_rows(self, names):
        out = []
        for k, s in enumerate(names):
            new = right_at(T(s, 24, COLS[k]), X0 - 0.2, BAR_YS[k])
            old, self.rowl[k] = self.rowl[k], new
            out.append(swap(old, new))
        return out

    def construct(self):
        self.capm = self.lost_x = None
        self.lab = {"bank": None, "app": None, "buf": None, "pipe": None}
        self.chips = [None, None, None]
        self.segs = [None, None, None]
        self.bars = [None, None, None]
        self.rowl = [None, None, None]
        self.title_card("One lost packet, three late answers", "why HTTP/2 still waits, and how HTTP/3 stops")

        bank = frame_box(BK_X0, BK_X1, GREEN_M)
        app = frame_box(AP_X0, AP_X1, BLUE_M)
        div = Line([AP_X0, DIV_Y, 0], [AP_X1, DIV_Y, 0], stroke_width=2, color=GREY_D)
        pipe = pipe_one()
        slots = VGroup(*[slot(k) for k in range(3)])
        cards = [card(k) for k in range(3)]

        # ---------------- scene 1: numbered tickets ----------------
        self.steps("Remember the café with numbered tickets? You order, you get a number, and the coffees come out "
                   "in whatever order they're ready.", [
            (lambda: [FadeIn(bank), *self.relabel("bank", "the kitchen")], 0.6),
            "You order",
            (lambda: [FadeIn(app), *self.relabel("app", "the counter")], 0.6),
            "you get a number",
            (lambda: self.chips_reset(), 0.6),
            "the coffees come out",
            (lambda: self.set_chip(1, True), 0.4),
            (lambda: self.set_chip(2, True), 0.4),
            (lambda: self.set_chip(0, True), 0.4),
        ])
        self.steps("HTTP/2 works the same way. Many requests share one connection, and each one gets a number, called a stream.", [
            (lambda: [*self.relabel("bank", "the bank"), *self.relabel("app", "your app"), *self.chips_reset()], 0.7),
            "Many requests share",
            (lambda: [Create(pipe), *self.relabel("pipe", "one connection")], 0.8),
            "called a stream",
            (lambda: [*self.cap("each request and its answer: a stream, with a number"),
                      LaggedStart(*[Indicate(c, color=COLS[k], scale_factor=1.15) for k, c in enumerate(self.chips)], lag_ratio=0.3)], 1.0),
        ])
        qm = T("?", 60, YELLOW_M).move_to([PIPE_MID, 1.75, 0])
        self.steps("So here's a question. If one packet on that connection gets lost, how many requests have to wait for it? "
                   "Most people say one. Keep your answer.", [
            (lambda: self.uncap(), 0.3),
            "If one packet",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "Most people say one",
            (lambda: self.cap("one lost packet: how many requests wait?", WHITE), 0.5),
            "Keep your answer",
            (lambda: [FadeOut(qm)], 0.4),
        ])

        # ---------------- scene 2: shrink it, nothing lost ----------------
        self.steps("Let's shrink it. Your app asks the bank for three answers at once, on streams 1, 3 and 5. "
                   "The bank needs 300 milliseconds for each.", [
            (lambda: self.uncap(), 0.3),
            "three answers",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in cards], lag_ratio=0.3)], 1.0),
            "300 milliseconds",
            (lambda: self.cap("each answer: ready after 300 ms"), 0.5),
        ])
        self.steps("Then it sends each answer, 1,000 bytes, in one segment. A segment is TCP's word for one of its packets.", [
            (lambda: [Create(div), FadeIn(slots), *self.relabel("buf", "TCP's receive buffer", GREY_B, 22),
                      *self.cap("each answer: 1,000 bytes, one segment")], 0.8),
            "A segment is",
            (lambda: self.cap("a segment: TCP's word for one of its packets"), 0.5),
        ])

        def send_all(lost=None, lane=None, rt=0.9):
            return [LaggedStart(*[self.travel(k, lost == k, lane, rt) for k in range(3)], lag_ratio=0.3)]

        self.steps("The path takes 50 milliseconds each way. With nothing lost, all three answers arrive together, "
                   "about half a second after the start.", [
            (lambda: self.cap("50 ms each way: a round trip is 100 ms"), 0.5),
            "With nothing lost",
            (lambda: send_all(), 1.9),
            (lambda: self.rise([0, 1, 2]), 0.6),
            "about half",
            (lambda: [*self.set_rows(["stream 1", "stream 3", "stream 5"]),
                      *self.set_bars([(509, None, "0.51 s")] * 3), *self.cap("nothing lost: every answer in 0.51 s")], 0.9),
        ])
        ref = DashedLine([X0 + 509 * XS, -1.28, 0], [X0 + 509 * XS, -2.92, 0], dash_length=0.08, stroke_width=2, color=GREY_C)
        ref_l = T("no loss", 20, GREY_C).move_to([X0 + 509 * XS, -1.1, 0])

        # ---------------- scene 3: predict ----------------
        self.steps("Now we drop one segment on purpose, the one carrying stream 1. Segments 2 and 3 arrive whole. "
                   "Which requests are late? Pause and guess.", [
            (lambda: [*self.clear_round(), *self.set_bars(["clear"] * 3), Create(ref), FadeIn(ref_l), *self.uncap()], 0.6),
            "Now we drop",
            (lambda: send_all(lost=0), 1.9),
            "Which requests",
            (lambda: self.cap("which requests are late?", WHITE), 0.4),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 4: show, and why ----------------
        self.steps("All three. Every one of them, about 120 milliseconds late.", [
            (lambda: [*self.uncap(), *self.set_bars([(627, RED_M, "0.63 s")] * 3)], 0.9),
            "about 120",
            (lambda: self.cap("one lost segment: all three requests 120 ms late", RED_M), 0.5),
        ])
        hole = Square(0.7, stroke_color=RED_M, stroke_width=3).move_to([SLOT_X[0], PY, 0])
        hole_l = T("missing", 20, RED_M).move_to([SLOT_X[0], BOX_BOT - 0.3, 0])
        self.steps("Here's why. TCP promises one stream of bytes, delivered in order. "
                   "To TCP, these three answers are bytes 1 to 3,000 of that one stream, and the first 1,000 are missing.", [
            (lambda: self.cap("TCP: one stream of bytes, in order"), 0.5),
            "To TCP",
            (lambda: [*self.cap("to TCP: bytes 1 to 3,000 of one stream"),
                      LaggedStart(*[Indicate(s, color=WHITE, scale_factor=1.15) for s in (self.segs[1], self.segs[2])], lag_ratio=0.4)], 1.0),
            "the first 1,000",
            (lambda: [Create(hole), FadeIn(hole_l)], 0.6),
        ])
        self.steps("So segments 2 and 3 wait in TCP's receive buffer, complete, and your app gets nothing. "
                   "Stream 5 has its whole answer, sitting on the counter, and nobody may pick it up.", [
            (lambda: [glow(self.segs[1][0], WHITE, 1.1), glow(self.segs[2][0], WHITE, 1.1),
                      *self.cap("the receive buffer: where TCP keeps segments until it may hand them over")], 0.9),
            "your app gets nothing",
            (lambda: [LaggedStart(*[Indicate(c, color=GREY_B, scale_factor=1.12) for c in self.chips], lag_ratio=0.2)], 0.9),
            "Stream 5 has",
            (lambda: [Wiggle(self.segs[2], scale_value=1.1, rotation_angle=0.03 * TAU)], 0.9),
        ])
        ask = Dot(radius=0.08, color=WHITE)
        self.steps("Your app's computer keeps asking for the missing bytes. About a round trip later, the bank sends them again. "
                   "The hole fills, and TCP hands everything over at once.", [
            (lambda: [*self.cap("please resend bytes 1 to 1,000"), FadeIn(ask.move_to([P1 - 0.2, PY, 0]), run_time=0.1)], 0.3),
            (lambda: [ask.animate.move_to([P0 + 0.2, PY, 0])], 0.9),
            (lambda: [FadeOut(ask)], 0.2),
            "the bank sends them again",
            (lambda: [FadeOut(self.lost_x), self.travel(0)], 1.3),
            "The hole fills",
            (lambda: [FadeOut(hole), FadeOut(hole_l)], 0.3),
            "hands everything over",
            (lambda: self.rise([0, 1, 2]), 0.7),
        ])
        self.lost_x = None

        # ---------------- scene 5: the café's hatch ----------------
        self.steps("Here's the café version. The kitchen makes coffees in any order, but every tray leaves through one narrow hatch, in single file.", [
            (lambda: [*self.uncap(), *self.relabel("bank", "the kitchen"), *self.relabel("app", "the counter"),
                      *self.chips_reset()], 0.7),
            "one narrow hatch",
            (lambda: [*self.relabel("pipe", "one narrow hatch", YELLOW_M), glow(pipe, YELLOW_M, 1.0)], 0.7),
            "in single file",
            (lambda: send_all(lost=0, rt=0.7), 1.6),
        ])
        self.steps("Drop one tray, and every tray behind it waits until that coffee is made again, even the ones that are ready.", [
            "every tray behind it",
            (lambda: [glow(self.segs[1][0], WHITE, 1.1), glow(self.segs[2][0], WHITE, 1.1)], 0.8),
            "made again",
            (lambda: [FadeOut(self.lost_x), self.travel(0, rt=0.7)], 1.1),
            (lambda: self.rise([0, 1, 2]), 0.6),
        ])
        self.lost_x = None
        self.steps("The hatch is the TCP connection. The trays are segments. And the orders are streams.", [
            (lambda: [*self.relabel("pipe", "one TCP connection"), *self.relabel("bank", "the bank"), *self.relabel("app", "your app"),
                      *self.cap("the hatch: the TCP connection")], 0.6),
            "The trays",
            (lambda: self.cap("the trays: segments"), 0.4),
            "And the orders",
            (lambda: [*self.cap("the orders: streams"),
                      LaggedStart(*[Indicate(c, color=COLS[k], scale_factor=1.15) for k, c in enumerate(self.chips)], lag_ratio=0.3)], 0.9),
        ])
        self.steps("This has a name: head-of-line blocking, the first in line holding up everyone behind. "
                   "HTTP/2 removed it from HTTP, and kept it one layer down, in TCP.", [
            "head-of-line blocking",
            (lambda: self.cap("head-of-line blocking: the first in line holds up everyone behind", WHITE), 0.6),
            "HTTP/2 removed it",
            (lambda: [*self.cap("HTTP/2 removed it from HTTP, and kept it in TCP", WHITE), glow(pipe, RED_M, 1.0)], 0.8),
        ])

        # ---------------- scene 6: back to three connections? ----------------
        pipe3 = pipe_three()
        self.steps("So, go back to HTTP/1.1, with three connections, three hatches? The lesson's lab tried that too. "
                   "The loss hits only one request, and the other two finish on time.", [
            (lambda: [*self.uncap(), *self.clear_round(), FadeOut(pipe), Create(pipe3), *self.relabel("pipe3", "HTTP/1.1: three connections")], 0.9),
            "The loss hits",
            (lambda: [*self.set_rows(["connection 1", "connection 2", "connection 3"]),
                      *self.set_bars(["clear", (514, None, "0.51 s"), (514, None, "0.51 s")])], 0.9),
            "finish on time",
            (lambda: self.cap("one loss, one late request", WHITE), 0.5),
        ])
        self.steps("But the unlucky one was 330 milliseconds late. With no segment behind its hole, nothing told the bank quickly, "
                   "so it waited for a timer. And every extra connection pays its own handshakes.", [
            (lambda: self.set_bars([(841, RED_M, "0.84 s"), None, None]), 0.9),
            "With no segment",
            (lambda: self.cap("alone on its connection, the loss waited for a timer", RED_M), 0.5),
            "And every extra",
            (lambda: self.cap("and three connections pay three sets of handshakes", GREY_B), 0.5),
        ])

        # ---------------- scene 7: a hatch per order: QUIC ----------------
        lanes = pipe_lanes()
        self.steps("The real fix gives every order its own hatch, on one connection. That's QUIC, the transport under HTTP/3. "
                   "It runs over UDP, and numbers the bytes of each stream separately.", [
            (lambda: [*self.uncap(), FadeOut(pipe3), Create(lanes), *self.relabel("pipe3", "QUIC: a lane per stream"),
                      *self.set_bars(["clear"] * 3), *self.set_rows(["stream 1", "stream 3", "stream 5"])], 1.0),
            "That's QUIC",
            (lambda: [*self.relabel("buf", "QUIC: order per stream", GREY_B, 21),
                      *self.cap("QUIC: the transport, the layer that delivers bytes, under HTTP/3")], 0.7),
            "It runs over UDP",
            (lambda: self.cap("it runs over UDP, and keeps each stream's bytes in order separately"), 0.5),
        ])
        seps = VGroup(*[Line([x, PY - 0.42, 0], [x, PY + 0.42, 0], stroke_width=2, color=GREY_C) for x in ((SLOT_X[0] + SLOT_X[1]) / 2, (SLOT_X[1] + SLOT_X[2]) / 2)])
        self.steps("Lose the same segment. Segments 2 and 3 complete streams 3 and 5, and go straight to your app. "
                   "Only stream 1 waits for its resend.", [
            (lambda: [*self.uncap(), Create(seps)], 0.4),
            (lambda: send_all(lost=0, lane=True), 1.9),
            "and go straight",
            (lambda: [*self.rise([1, 2]), *self.set_bars([None, (509, None, "0.51 s"), (509, None, "0.51 s")])], 0.9),
            "Only stream 1",
            (lambda: [FadeOut(self.lost_x), self.travel(0, lane=True, rt=0.8)], 1.2),
            (lambda: [*self.rise([0]), *self.set_bars([(609, RED_M, "+ its resend"), None, None])], 0.8),
        ])
        self.lost_x = None

        # ---------------- scene 8: when it matters ----------------
        self.steps("Should everything leave HTTP/2, then? Not so fast. Inside a data center, a building full of servers, "
                   "loss is rare and a round trip takes a fraction of a millisecond. There, one HTTP/2 connection is a fine default.", [
            (lambda: [*self.cap("leave HTTP/2 everywhere?", WHITE), *self.clear_round(), FadeOut(seps), FadeOut(lanes), Create(pipe),
                      *self.relabel("pipe", "one TCP connection (HTTP/2)"), *self.relabel("buf", "TCP's receive buffer", GREY_B, 22),
                      *self.set_bars(["clear"] * 3)], 1.0),
            "Inside a data center",
            (lambda: self.cap("inside a data center: loss is rare, a round trip under a millisecond", GREEN_M), 0.5),
            "There, one HTTP/2",
            (lambda: self.cap("there, one HTTP/2 connection is a fine default", GREEN_M), 0.5),
        ])
        self.steps("On a phone with 1 percent loss, a busy connection hits several holes a second, and each one stalls every request in flight. "
                   "One loss also slows the whole connection's sending, for every stream at once.", [
            (lambda: self.cap("a phone at 1% loss: several holes a second, each stalls every request", RED_M), 0.5),
            (lambda: send_all(lost=1, rt=0.6), 1.4),
            "each one stalls",
            (lambda: [glow(pipe, RED_M, 1.0)], 0.8),
            (lambda: self.clear_round(), 0.4),
            "One loss also",
            (lambda: [*self.cap("and one loss slows the whole connection, for every stream", RED_M), glow(pipe, RED_M, 1.0)], 0.8),
        ])
        self.steps("So measure under loss. Testing on a clean office network is like testing an umbrella indoors.", [
            (lambda: self.cap("measure under loss, not on a clean network", WHITE), 0.5),
            "like testing an umbrella",
            (lambda: self.cap("a clean office network is an umbrella tested indoors", GREY_B), 0.5),
        ], after=0.5)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, how many requests wait for one lost packet? On HTTP/2, every one behind the hole. "
                   "HTTP/2 removed the wait in HTTP, not the wait in TCP.", [
            (lambda: self.cap("one lost packet: how many requests wait?", WHITE), 0.5),
            "every one behind",
            (lambda: self.cap("on HTTP/2: every one behind the hole", RED_M), 0.5),
            "HTTP/2 removed",
            (lambda: self.cap("HTTP/2 removed the wait in HTTP, not the wait in TCP", YELLOW_M), 0.6),
        ], after=0.6)
        hole3 = Square(0.7, stroke_color=RED_M, stroke_width=3).move_to([SLOT_X[2], PY, 0])
        self.steps("One quick check. This time segment 3 is lost, the one carrying stream 5, and segments 1 and 2 arrive. "
                   "Over HTTP/2, which requests wait? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "This time",
            (lambda: send_all(lost=2), 1.9),
            (lambda: [Create(hole3)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Only stream 5. Segments 1 and 2 came before the hole, so TCP hands them over on time. "
                   "A hole only holds up what's behind it.", [
            (lambda: [*self.uncap(), *self.rise([0, 1])], 0.8),
            "Segments 1 and 2",
            (lambda: self.cap("segments 1 and 2 are before the hole: handed over on time", WHITE), 0.5),
            "A hole only",
            (lambda: [*self.cap("a hole only holds up what's behind it", YELLOW_M), glow(hole3, RED_M, 1.1)], 0.8),
        ], after=0.4)
        self.wait(2.0)
