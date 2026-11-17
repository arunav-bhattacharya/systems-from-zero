from sfz import *

SAY.insert(0, (r"\b1,000\b", "one thousand"))
SAY.insert(0, (r"\b5,400\b", "five thousand four hundred"))
SAY.insert(0, (r"\b4\.50\b", "four fifty"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
# top: the café's app and the bank, a wire between them; middle: three kinds of failure (later a one-line summary);
# bottom: the retry storm, requests reaching the bank in each 10 ms.
APP_X, BANK_X, TOP_Y, ST_Y = -4.85, 4.85, 2.75, 1.8
BW, BH = 3.4, 1.25
W0, W1 = APP_X + BW / 2, BANK_X - BW / 2
SORT_X, SORT_Y, SORT_W, SORT_H = [-4.4, 0.0, 4.4], -0.55, 4.05, 3.1
SORT_C = [GREEN_M, YELLOW_M, RED_M]
SUM_Y = 1.2
BASE, CX0, CXS, YS = -2.55, -5.3, 11.4 / 2600, 0.0028   # chart: baseline, x of 0 ms, units per ms, units per request
AXL = -5.45
CAP_Y, CD_Y = -3.36, -3.06

# from the lesson's Jitter.java (fixed seed): requests arriving in each 10 ms
NOJ = {0: 1000, 10: 1000, 30: 1000, 70: 900, 150: 800, 250: 700}
JIT = [1076, 99, 103, 130, 113, 145, 154, 140, 154, 155, 48, 65, 56, 78, 53, 57, 76, 62, 63, 77, 66, 60, 57, 57, 50, 50, 46,
       35, 31, 36, 30, 40, 25, 21, 18, 21, 31, 24, 29, 27, 30, 35, 29, 25, 24, 28, 26, 17, 21, 25, 16, 21, 18, 15, 17, 16, 7, 9,
       9, 10, 10, 7, 4, 6, 1, 2, 3, 0, 3, 3, 4, 4, 3, 4, 3, 3, 5, 2, 2, 1, 4, 2, 6, 7, 2, 6, 3, 3, 3, 6, 1, 4, 3, 0, 3, 2, 1, 2,
       1, 1, 3, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1]
DOWN_SLOTS = 25                                          # the bank is down until 250 ms


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
def actor_box(x, color):
    return RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to([x, TOP_Y, 0])


def actor_text(x, name, sub):
    return VGroup(T(name, 30).move_to([x, TOP_Y + 0.22, 0]), T(sub, 21, GREY_B).move_to([x, TOP_Y - 0.3, 0]))


def msg(s, color=WHITE):
    t = M(s, 22, color)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.36, height=0.5, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r))


def sort_box(i):
    return RoundedRectangle(corner_radius=0.14, width=SORT_W, height=SORT_H, stroke_color=SORT_C[i], stroke_width=3).set_fill(
        fillc(SORT_C[i], 0.08), 1).move_to([SORT_X[i], SORT_Y, 0])


def sort_text(i, title, example, verdict):
    t = VGroup(*[T(s, 27) for s in title]).arrange(DOWN, buff=0.12)
    e = VGroup(*[T(s, 22, GREY_B) for s in example]).arrange(DOWN, buff=0.1)
    v = T(verdict, 23, SORT_C[i])
    g = VGroup(t, e, v).arrange(DOWN, buff=0.3)
    fit(g, SORT_W - 0.3)
    return g.move_to([SORT_X[i], SORT_Y, 0])


ANALOGY = [(["1. the call never", "connects"], ["nobody heard you"], "call again: safe"),
           (["2. you order, then", "the line drops"], ["did they write it down?"], "call again: two tables?"),
           (["3. they answer:", "sorry, we're full"], ["a clear answer"], "call again: same answer")]
MAPPED = [(["never sent"], ["connection refused,", "connecting timed out"], "retry: always safe"),
          (["sent, maybe arrived"], ["a reset,", "a read timeout"], "retry: only if idempotent"),
          (["an answer came back"], ["an error 400", "or 500"], "retry: no, same answer")]


def tx(ms):
    return CX0 + ms * CXS


def spike(slot, n, w=0.09, color=RED_M, ok=GREEN_M):
    """A bar for one 10 ms slot: red for requests the bank refused, green for the ones it answered."""
    x = tx(slot * 10 + 5)
    served = 0 if slot < DOWN_SLOTS else min(n, 100)
    g = VGroup()
    if n - served > 0:
        g.add(Rectangle(width=w, height=(n - served) * YS, stroke_width=0).set_fill(color, 0.9).move_to(
            [x, BASE + served * YS + (n - served) * YS / 2, 0]))
    if served:
        g.add(Rectangle(width=w, height=served * YS, stroke_width=0).set_fill(ok, 0.95).move_to([x, BASE + served * YS / 2, 0]))
    return g


class LbRetries(Base):
    """net-12, section 2. A payment that times out after the bank approved it gets charged twice on retry. Booking a
    table by phone sorts failures: never sent (always safe), maybe arrived (only if idempotent, or with an idempotency
    key), an answer (never). Then 1,000 cafés, a bank down for 250 ms that answers 100 per 10 ms: backoff without
    jitter answers 400 (5,400 requests); full jitter answers all 1,000 by 1.13 s (4,194 requests, at most 155 retries in
    10 ms). Retries multiply (27), a retry budget of about 10%, one layer. A check question."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        b = Line([-1.0, CD_Y, 0], [1.0, CD_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b), run_time=secs, rate_func=linear)

    def state(self, who, s, color=GREY_B):
        x = APP_X if who == "A" else BANK_X
        new = fit(T(s, 22, color), 3.1).move_to([x, ST_Y, 0]) if s else None
        old, self.st[who] = self.st[who], new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def names(self, app=None, bank=None):
        out = []
        if app:
            new = actor_text(APP_X, *app)
            out.append(swap(self.at, new))
            self.at = new
        if bank:
            new = actor_text(BANK_X, *bank)
            out.append(swap(self.bt, new))
            self.bt = new
        return out

    def send(self, s, color=WHITE, back=False, lost=False, rt=1.0):
        """A message card runs along the wire (or is lost halfway, with a red cross)."""
        m = msg(s, color)
        a, b = (W1 - m.width / 2 - 0.1, W0 + m.width / 2 + 0.1) if back else (W0 + m.width / 2 + 0.1, W1 - m.width / 2 - 0.1)
        m.move_to([a, TOP_Y, 0])
        if lost:
            x = tick(False, 0.2).move_to([0, TOP_Y, 0])
            self.lost.append(x)
            return Succession(FadeIn(m, run_time=0.15), m.animate(run_time=rt * 0.5, rate_func=linear).move_to([0, TOP_Y, 0]),
                              AnimationGroup(m.animate(run_time=0.35).shift(0.6 * DOWN).set_opacity(0), Create(x, run_time=0.35)))
        return Succession(FadeIn(m, run_time=0.15), m.animate(run_time=rt, rate_func=linear).move_to([b, TOP_Y, 0]),
                          FadeOut(m, run_time=0.2))

    def clear_lost(self):
        out = [FadeOut(x) for x in self.lost]
        self.lost = []
        return out

    def clear_stats(self):
        old, self.statm = self.statm, None
        return [FadeOut(old)] if old is not None else []

    def stats(self, s, color=WHITE):
        new = right_at(T(s, 22, color), 6.2, 0.6)
        old, self.statm = self.statm, new
        return [swap(old, new)]

    def construct(self):
        self.capm = self.statm = None
        self.st = {"A": None, "K": None}
        self.lost = []
        self.title_card("Try again, but safely and at random", "which failures to retry, and how to wait")

        abox, kbox = actor_box(APP_X, BLUE_M), actor_box(BANK_X, GREEN_M)
        self.at = actor_text(APP_X, "the café's app", "sends each payment")
        self.bt = actor_text(BANK_X, "the bank", "approves payments")
        wire = Line([W0, TOP_Y, 0], [W1, TOP_Y, 0], stroke_width=3, color=GREY_C)

        # ---------------- scene 1: tap again ----------------
        self.steps("At a café, the card reader shows an error message. The cashier asks you to tap again, and this time it works.", [
            (lambda: [FadeIn(abox), FadeIn(self.at)], 0.6),
            "shows an error message",
            (lambda: self.state("A", "error", RED_M), 0.5),
            "tap again",
            (lambda: [GrowFromEdge(wire, LEFT), FadeIn(kbox), FadeIn(self.bt)], 0.8),
            "this time it works",
            (lambda: [self.send("pay 4.50", rt=0.8)], 1.1),
            (lambda: self.state("A", "approved", GREEN_M), 0.4),
        ])
        self.steps("So why not let the app do that for you, and try every failed payment again? Many careful teams do exactly that.", [
            (lambda: [*self.state("A", None), *self.cap("try every failed payment again?", WHITE)], 0.6),
        ])
        self.steps("Two questions spoil the plan. Was the first payment really not made? "
                   "And what happens when a thousand apps try again at the same moment?", [
            "Was the first",
            (lambda: self.cap("1. was the first payment really not made?", WHITE), 0.5),
            "And what happens",
            (lambda: self.cap("2. what if a thousand apps try again at once?", WHITE), 0.5),
        ])

        # ---------------- scene 2: one coffee, two charges ----------------
        self.steps("Start with one payment. The app sends it, and the bank approves it. Then the answer gets lost on the way back.", [
            (lambda: self.uncap(), 0.3),
            "The app sends it",
            (lambda: [self.send("pay 4.50")], 1.2),
            (lambda: self.state("K", "charges: 1", WHITE), 0.4),
            "Then the answer",
            (lambda: [self.send("approved", GREEN_M, back=True, lost=True)], 1.0),
        ])
        self.steps("The app waited, and nothing came. That's a timeout. So it tries again, and the bank, seeing a perfectly good payment, "
                   "approves it again. One coffee, two charges.", [
            "That's a timeout",
            (lambda: self.state("A", "timeout", RED_M), 0.5),
            "So it tries again",
            (lambda: [*self.clear_lost(), self.send("pay 4.50")], 1.3),
            "approves it again",
            (lambda: self.state("K", "charges: 2", RED_M), 0.5),
            "One coffee",
            (lambda: [*self.cap("one coffee, two charges", RED_M), Indicate(self.st["K"], color=RED_M, scale_factor=1.2)], 0.8),
        ])
        self.steps("And never trying again isn't safe either, because some payments would never go through. "
                   "We need to know which failures are safe to try again.", [
            (lambda: self.cap("never retrying: some payments never go through"), 0.5),
            "We need to know",
            (lambda: [*self.cap("which failures are safe to try again?", WHITE), *self.state("A", None), *self.state("K", None)], 0.6),
        ])

        # ---------------- scene 3: booking a table by phone ----------------
        boxes = [sort_box(i) for i in range(3)]
        texts = [sort_text(i, *ANALOGY[i]) for i in range(3)]
        self.steps("Think of booking a table by phone. Three things can go wrong.", [
            (lambda: [*self.uncap(), *self.names(("you, calling", "on the phone"), ("the restaurant", "takes bookings"))], 0.8),
            "Three things",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in boxes], lag_ratio=0.25)], 0.9),
        ])
        self.steps("One, the call never connects. Nobody heard you, so calling again is always safe.", [
            (lambda: [FadeIn(texts[0][0])], 0.5),
            "Nobody heard",
            (lambda: [FadeIn(texts[0][1])], 0.4),
            "so calling again",
            (lambda: [FadeIn(texts[0][2], shift=0.1 * UP)], 0.5),
        ])
        self.steps("Two, you say, a table for four at eight, and the line drops. Did they write it down? You can't tell. "
                   "Calling again might get you two tables.", [
            (lambda: [FadeIn(texts[1][0])], 0.5),
            "Did they write",
            (lambda: [FadeIn(texts[1][1])], 0.4),
            "Calling again",
            (lambda: [FadeIn(texts[1][2], shift=0.1 * UP)], 0.5),
        ])
        self.steps("Three, they answer: sorry, we're full. Calling again gets the same answer.", [
            (lambda: [FadeIn(texts[2][0])], 0.5),
            (lambda: [FadeIn(texts[2][1])], 0.4),
            "Calling again",
            (lambda: [FadeIn(texts[2][2], shift=0.1 * UP)], 0.5),
        ])
        mapped = [sort_text(i, *MAPPED[i]) for i in range(3)]
        self.steps("Now map it. A call that never connects is a request that never left: the connection was refused, or connecting timed out.", [
            (lambda: self.names(("the café's app", "sends each payment"), ("the bank", "approves payments")), 0.7),
            "A call that never",
            (lambda: [swap(texts[0], mapped[0])], 0.8),
        ])
        self.steps("A dropped line after you spoke is a reset or a read timeout: the request may have arrived. "
                   "And sorry, we're full, is an answer, like an error 400 or 500. The same request gets it again.", [
            (lambda: [swap(texts[1], mapped[1])], 0.8),
            "And sorry",
            (lambda: [swap(texts[2], mapped[2])], 0.8),
        ])

        # ---------------- scene 4: idempotent, and the key ----------------
        self.steps("The middle case is the hard one. It's safe only if doing the thing twice has the same effect as doing it once. "
                   "That's called idempotent.", [
            (lambda: [glow(boxes[1], YELLOW_M, 1.03), boxes[0].animate.set_opacity(0.3), boxes[2].animate.set_opacity(0.3),
                      mapped[0].animate.set_opacity(0.3), mapped[2].animate.set_opacity(0.3)], 0.8),
            "That's called",
            (lambda: [*self.cap("idempotent: twice has the same effect as once", YELLOW_M), Indicate(mapped[1][2], color=YELLOW_M)], 0.8),
        ])
        self.steps("Reading a payment's status twice is fine. Approving a payment twice is not, unless the app sends an idempotency key: "
                   "a unique id for this payment.", [
            (lambda: self.cap("reading a status twice: fine", GREEN_M), 0.5),
            "Approving a payment",
            (lambda: self.cap("approving twice: two charges", RED_M), 0.5),
            "unless the app",
            (lambda: self.cap("an idempotency key: a unique id for this payment", WHITE), 0.5),
            "a unique id",
            (lambda: [self.send("pay 4.50  key 812")], 1.2),
            (lambda: self.state("K", "key 812: 1 charge", WHITE), 0.5),
        ])
        self.steps("The bank stores the result under it, and a repeat with the same key gets the first result back.", [
            (lambda: [self.send("approved", GREEN_M, back=True, lost=True)], 1.0),
            "a repeat",
            (lambda: [*self.clear_lost(), self.send("pay 4.50  key 812")], 1.3),
            "gets the first result",
            (lambda: [self.send("approved (key 812)", GREEN_M, back=True), *self.state("K", "key 812 again: still 1 charge", GREEN_M)], 1.3),
        ])
        self.steps("Like giving the restaurant a booking number. A person might recognise your voice; the bank's program needs the number.", [
            (lambda: self.cap("the booking number: the idempotency key", WHITE), 0.5),
            "A person might",
            (lambda: self.cap("a person might recognise your voice; a program needs the key"), 0.5),
        ], after=0.5)

        # ---------------- scene 5: a thousand cafés ----------------
        summ = VGroup(T("never sent: retry", 22, GREEN_M), T("maybe arrived: only if idempotent", 22, YELLOW_M),
                      T("an answer: don't retry", 22, RED_M)).arrange(RIGHT, buff=0.7).move_to([0, SUM_Y, 0])
        fit(summ, 12.6)
        shadows = VGroup(*[actor_box(APP_X, BLUE_M).shift(d * (UP + RIGHT)).set_opacity(0.45) for d in (0.16, 0.08)]).set_z_index(-1)
        axes = VGroup(Line([AXL, BASE, 0], [6.2, BASE, 0], stroke_width=2.5, color=GREY_B),
                      Line([AXL, BASE, 0], [AXL, BASE + 1000 * YS + 0.2, 0], stroke_width=2.5, color=GREY_B))
        yt = VGroup(right_at(T("1,000", 20, GREY_B), AXL - 0.12, BASE + 1000 * YS), right_at(T("100", 20, GREY_B), AXL - 0.12, BASE + 100 * YS))
        xt = VGroup(T("1 s", 20, GREY_B).move_to([tx(1000), BASE - 0.25, 0]), T("2 s", 20, GREY_B).move_to([tx(2000), BASE - 0.25, 0]))
        capl = DashedLine([AXL, BASE + 100 * YS, 0], [6.2, BASE + 100 * YS, 0], dash_length=0.1, stroke_width=2, color=GREEN_M)
        capt = T("the bank's limit: 100 per 10 ms", 18, GREEN_M).move_to([3.5, BASE + 100 * YS + 0.22, 0])
        down = Rectangle(width=tx(250) - AXL - 0.03, height=1000 * YS + 0.2, stroke_width=0).set_fill(RED_M, 0.13)
        down.move_to([(AXL + 0.03 + tx(250)) / 2, BASE + (1000 * YS + 0.2) / 2, 0])
        downt = T("bank down", 20, RED_M).move_to([(AXL + tx(250)) / 2, BASE - 0.28, 0])
        self.steps("Now the second question. Picture 1,000 cafés, and the bank's program restarts. For 250 milliseconds, every payment fails.", [
            (lambda: [*self.uncap(), *self.state("K", None), *[FadeOut(VGroup(b)) for b in boxes], *[FadeOut(m) for m in mapped],
                      FadeIn(summ, shift=0.1 * UP)], 0.9),
            "Picture 1,000",
            (lambda: [FadeIn(shadows), *self.names(("1,000 cafés", "one app each"))], 0.7),
            "the bank's program",
            (lambda: [Create(axes), FadeIn(yt), FadeIn(xt), kbox.animate.set_stroke(RED_M)], 0.8),
            "For 250",
            (lambda: [FadeIn(down), FadeIn(downt), *self.cap("down for 250 ms: every payment fails", RED_M)], 0.6),
        ])
        self.steps("After that, the bank can answer 100 requests in each 10 milliseconds. Every app tries again, and waits longer each time: "
                   "100 milliseconds, then 200, 400, 800, at most a second, and six tries in all. That's called exponential backoff.", [
            (lambda: [kbox.animate.set_stroke(GREEN_M), Create(capl), FadeIn(capt), *self.uncap()], 0.8),
            "Every app tries",
            (lambda: self.cap("wait 100 ms, then 200, 400, 800, at most 1 s; six tries in all"), 0.5),
            "That's called",
            (lambda: self.cap("exponential backoff: each wait doubles", WHITE), 0.5),
        ])
        self.steps("How many of the 1,000 cafés get an answer? Pause and guess.", [
            (lambda: self.cap("how many of the 1,000 get an answer?", WHITE), 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 6: in step ----------------
        spikes = VGroup(*[spike(s, n) for s, n in NOJ.items()])
        self.steps("Only 400. Look at the arrivals. Every app works out the same waits, so each round of retries lands "
                   "in the same 10 milliseconds: a thousand requests where a hundred fit.", [
            (lambda: [*self.uncap(), *self.stats("400 of 1,000 answered", RED_M)], 0.6),
            "Look at the arrivals",
            (lambda: [LaggedStart(*[GrowFromEdge(s, DOWN) for s in spikes], lag_ratio=0.5)], 2.4),
            "a thousand requests",
            (lambda: [*self.cap("1,000 requests in one 10 ms slot, where 100 fit", RED_M), Indicate(spikes[2], color=RED_M)], 0.8),
        ])
        self.steps("A hundred get through, and the rest fail together and come back together. "
                   "After six tries, 600 cafés give up, and the bank saw 5,400 requests.", [
            (lambda: [LaggedStart(*[Indicate(s[-1], color=GREEN_M, scale_factor=1.3) for s in spikes[2:]], lag_ratio=0.3)], 1.2),
            "the rest fail",
            (lambda: [LaggedStart(*[Indicate(s[0], color=RED_M, scale_factor=1.1) for s in spikes[2:]], lag_ratio=0.3)], 1.2),
            "After six tries",
            (lambda: self.stats("400 of 1,000 answered, 5,400 requests", RED_M), 0.6),
        ])

        # ---------------- scene 7: stop agreeing ----------------
        self.steps("It's like a radio call-in show where everyone who hears the busy tone redials after exactly ten seconds. "
                   "The line is jammed again, every time. Everyone is so punctual.", [
            (lambda: self.cap("everyone redials after exactly ten seconds", GREY_B), 0.5),
            "The line is jammed",
            (lambda: [LaggedStart(*[glow(s[0], RED_M, 1.05) for s in spikes[2:]], lag_ratio=0.2)], 1.0),
        ])
        jit = VGroup(*[spike(i, n, w=0.044, ok=TEAL_M) for i, n in enumerate(JIT) if n > 0])
        self.steps("The fix is to stop agreeing. Each app waits a random time, between zero and its current limit. That's called full jitter.", [
            (lambda: [spikes.animate.set_opacity(0.18), *self.cap("wait a random time between 0 and the current limit", WHITE)], 0.7),
            "That's called",
            (lambda: self.cap("full jitter", TEAL_M, 28), 0.5),
        ])
        self.steps("Same bank, same 1,000 cafés. The retries spread out, never more than 155 in any 10 milliseconds. "
                   "Every café gets an answer within about 1.1 seconds, with fewer requests in all.", [
            (lambda: [*self.uncap(), LaggedStart(*[GrowFromEdge(b, DOWN) for b in jit], lag_ratio=0.03)], 2.4),
            "never more than",
            (lambda: self.cap("at most 155 retries in any 10 ms", TEAL_M), 0.5),
            "Every café",
            (lambda: self.stats("1,000 of 1,000 answered by 1.13 s, 4,194 requests", TEAL_M), 0.6),
        ])

        # ---------------- scene 8: retries multiply ----------------
        chain = VGroup(T("1 request", 40), T("3", 46, YELLOW_M), T("9", 52, GOLD_M), T("27", 58, RED_M)).arrange(RIGHT, buff=1.5)
        chain.move_to([0, -0.8, 0])
        arrows = VGroup(*[Arrow(chain[i].get_right(), chain[i + 1].get_left(), buff=0.18, stroke_width=3, color=GREY_B,
                                max_tip_length_to_length_ratio=0.25) for i in range(3)])
        x3 = VGroup(*[T("× 3", 26, GREY_B).next_to(a, UP, buff=0.1) for a in arrows])
        self.steps("One more trap: retries multiply. If a request passes through three programs, each calling the next, "
                   "and each one tries three times, one request becomes 27 at the bottom, right when the bottom is struggling.", [
            (lambda: [FadeOut(VGroup(spikes, jit, axes, yt, xt, capl, capt, down, downt)), *self.clear_stats(), *self.uncap()], 0.7),
            "three programs",
            (lambda: [FadeIn(chain[0])], 0.4),
            "each one tries",
            (lambda: [LaggedStart(*[AnimationGroup(GrowArrow(arrows[i]), FadeIn(x3[i]), FadeIn(chain[i + 1], scale=0.6)) for i in range(3)],
                                  lag_ratio=0.6)], 1.8),
            "right when",
            (lambda: [Indicate(chain[3], color=RED_M, scale_factor=1.2)], 0.7),
        ])
        self.steps("So keep a retry budget: retries may add at most about 10 percent to what you send, and once it's spent, "
                   "failures go straight back. And retry at one layer only, the one closest to the user.", [
            (lambda: self.cap("a retry budget: retries add at most about 10%", WHITE), 0.5),
            "once it's spent",
            (lambda: self.cap("budget spent: failures go straight back", GREY_B), 0.5),
            "And retry at one layer",
            (lambda: [*self.cap("retry at one layer: the one closest to the user", WHITE),
                      VGroup(arrows[1:], x3[1:], chain[2:]).animate.set_opacity(0.2)], 0.8),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        boxes2 = [sort_box(i) for i in range(3)]
        mapped2 = [sort_text(i, *MAPPED[i]) for i in range(3)]
        self.steps("So, should the app try every failed payment again? Only when it's safe: never sent, or idempotent. "
                   "At a random time. From one place.", [
            (lambda: [FadeOut(VGroup(chain, arrows, x3)), *self.cap("try every failed payment again?", WHITE),
                      *self.names(("the café's app", "sends each payment")), FadeOut(shadows), FadeOut(summ),
                      *[FadeIn(VGroup(b, m), shift=0.1 * UP) for b, m in zip(boxes2, mapped2)]], 0.9),
            "Only when it's safe",
            (lambda: [*self.cap("only when it's safe: never sent, or idempotent", WHITE), glow(boxes2[0], GREEN_M, 1.02),
                      glow(boxes2[1], YELLOW_M, 1.02)], 0.8),
            "At a random time",
            (lambda: self.cap("safe, at a random time, from one place", YELLOW_M), 0.5),
        ], after=0.6)
        self.steps("One quick check. The app asks the bank for a payment's status, a request that only reads, and the read times out. "
                   "Try again or not? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "for a payment's status",
            (lambda: [self.send("GET status")], 1.2),
            (lambda: [self.send("status", GREEN_M, back=True, lost=True)], 0.9),
            "the read times out",
            (lambda: self.state("A", "read timeout", RED_M), 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Try again. Reading twice changes nothing, so it's idempotent. Wait a random time first.", [
            (lambda: [*self.uncap(), glow(boxes2[1], YELLOW_M, 1.04), Indicate(mapped2[1][2], color=YELLOW_M, scale_factor=1.12)], 0.8),
            "Reading twice",
            (lambda: self.cap("reading twice changes nothing: idempotent, so retry", GREEN_M), 0.5),
            "Wait a random",
            (lambda: [*self.clear_lost(), *self.state("A", "random wait, then retry", GREEN_M), self.send("GET status", rt=0.8)], 1.1),
        ], after=0.4)
        self.wait(2.0)
