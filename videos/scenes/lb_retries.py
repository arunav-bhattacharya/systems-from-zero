from sfz import *

CX, CY = -5.35, 1.9                    # your service
LX, LY = -1.5, 1.9                     # load balancer
BX, BY = 3.2, [3.0, 1.9, 0.8]         # backends
STATUS_Y = 0.0
BASE, X0, XS, YS = -3.0, -5.4, 11.0 / 2600, 0.0022  # chart: baseline, x of 0 ms, units per ms, units per request
FIXED = [(0, 1000), (100, 1000), (200, 1000), (300, 1000), (400, 900), (500, 800)]
BACKOFF = [(0, 1000), (100, 1000), (300, 1000), (700, 900), (1500, 800), (2500, 700)]
# full jitter, from the lesson's simulation: retries arriving in each 100 ms, shown as the average per 10 ms
JITTER = [1269, 635, 488, 266, 260, 138, 39, 31, 42, 18, 6, 2]


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(a, b, color=YELLOW_M, run_time=0.6):
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.1))


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


def node(name, color, x, y, w, h, size=26):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, y, 0])
    return VGroup(r, T(name, size).move_to([x, y, 0]))


def lat(i, s, color=GREY_B):
    t = T(s, 22, color)
    return t.move_to([BX + 1.5 + t.width / 2, BY[i], 0])


def status(s, color=GREY_B):
    return T(s, 24, color).move_to([0, STATUS_Y, 0])


def tx(t):
    return X0 + t * XS


def spike(t, n, color=RED_M, w=0.14):
    h = max(n * YS, 0.004)
    return Rectangle(width=w, height=h, stroke_width=0).set_fill(color, 0.9).move_to([tx(t), BASE + h / 2, 0])


def bucket(k, n, color=GREEN_M):
    h = max(n / 10 * YS, 0.01)
    return Rectangle(width=100 * XS - 0.04, height=h, stroke_width=0).set_fill(color, 0.9).move_to([tx(100 * k + 50), BASE + h / 2, 0])


class LbRetries(Base):
    """net-12, sections 0 to 3: a load balancer spreads requests over three backends; backend 2 slows down, a 500 ms
    timeout and a retry land on backend 3; retries must be safe. The issuer restarts (down until 250 ms, then 100 answers
    per 10 ms) and 1,000 clients retry: fixed waits and plain backoff arrive in waves (the lesson's Jitter.java: 400 of
    1,000 answered, 5,400 requests); full jitter answers all 1,000 in about 1.1 s. Retries multiply across layers (27);
    a budget caps them. Pooled connections skip the handshakes, and an idle one the balancer forgot gets a reset."""

    def construct(self):
        self.title_card("Load balancers, timeouts and retries", "and why a thousand retries should never arrive together")

        client = node("your service", BLUE_M, CX, CY, 2.4, 1.2, 26)
        lb = node("load balancer", WHITE, LX, LY, 2.7, 1.2, 26)
        bes = [node(f"backend {i + 1}", GREEN_M, BX, BY[i], 2.7, 0.85, 24) for i in range(3)]
        wc = Line([CX + 1.2, CY, 0], [LX - 1.35, LY, 0], stroke_width=3, color=GREY_D)
        wb = [Line([LX + 1.35, LY, 0], [BX - 1.35, BY[i], 0], stroke_width=3, color=GREY_D) for i in range(3)]
        lats = [lat(i, "120 ms") for i in range(3)]

        def call(i, color=BLUE_M, rt=0.45):
            return [(lambda: [flow(wc.get_start(), wc.get_end(), color, rt)], rt + 0.05),
                    (lambda: [flow(wb[i].get_start(), wb[i].get_end(), color, rt)], rt + 0.05)]

        self.steps("Your service calls a card issuer through a load balancer, "
                   "which hands each request to the next healthy backend.", [
            (lambda: [FadeIn(client)], 0.5),
            "through a load",
            (lambda: [Create(wc), FadeIn(lb)], 0.6),
            (lambda: [*[Create(w) for w in wb], *[FadeIn(b) for b in bes]], 0.8),
            "which hands",
            *call(0), *call(1), *call(2),
        ])

        stuck = Dot(radius=0.09, color=RED_M).move_to(bes[1][0].get_left() + 0.2 * RIGHT)
        timer = T("waiting 0 ms", 22, GREY_B).move_to([CX, CY - 0.95, 0])
        self.steps("Each answers in about 120 milliseconds. Then backend 2 slows down, and a request sent there just waits.", [
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * LEFT) for l in lats], lag_ratio=0.3)], 0.9),
            "Then backend 2",
            (lambda: [bes[1][0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1), Transform(lats[1], lat(1, "slow", RED_M))], 0.7),
            "and a request",
            *call(1),
            (lambda: [FadeIn(stuck), FadeIn(timer)], 0.3),
            (lambda: [Transform(timer, T("waiting 2 s, 3 s, 4 s …", 22, RED_M).move_to(timer))], 1.0),
        ])

        to = T("timeout: 500 ms", 22, GOLD_M).move_to(timer)
        xs = tick(False, 0.16).move_to(stuck)
        self.steps("So every call gets a timeout, a bit above the issuer's normal slowest answer: 500 milliseconds. "
                   "Then the client retries, and lands on another backend.", [
            (lambda: [Transform(timer, to)], 0.7),
            "Then the client",
            (lambda: [FadeOut(stuck), Create(xs)], 0.4),
            *call(2, GOLD_M),
            (lambda: [flow(wb[2].get_end(), wb[2].get_start(), GREEN_M, 0.45)], 0.5),
            (lambda: [flow(wc.get_end(), wc.get_start(), GREEN_M, 0.45), FadeOut(xs),
                      Transform(timer, T("answered in 620 ms", 22, GREEN_M).move_to(timer))], 0.5),
        ])

        safe = status("safe to retry: a read, or a payment with an idempotency key", GOLD_M)
        self.steps("That's safe because this call only reads. "
                   "Retrying a payment needs an idempotency key, or the card could be charged twice.", [
            (lambda: [FadeIn(safe, shift=0.1 * UP)], 0.7),
            "Retrying a payment",
            (lambda: [Indicate(safe, color=GOLD_M, scale_factor=1.05)], 1.0),
        ])

        axis = Line([X0 - 0.1, BASE, 0], [6.3, BASE, 0], stroke_width=2.5, color=GREY_B)
        tl = VGroup(*[T(s, 19, GREY_B).move_to([tx(t), BASE - 0.3, 0])
                      for t, s in ((0, "0"), (500, "0.5 s"), (1000, "1 s"), (1500, "1.5 s"), (2000, "2 s"), (2500, "2.5 s"))])
        ylab = T("requests arriving per 10 ms", 19, GREY_B).move_to([3.7, -0.5, 0])
        down = Rectangle(width=250 * XS, height=2.4, stroke_width=0).set_fill(RED_M, 0.13).move_to([tx(125), BASE + 1.2, 0])
        downl = T("issuer down", 18, RED_M).move_to([tx(150), BASE + 2.58, 0])
        t0 = spike(0, 1000)
        many = T("1,000 clients", 26).move_to(client[1])
        self.steps("Now the issuer restarts, and is down for 250 milliseconds. A thousand clients fail at once.", [
            (lambda: [FadeOut(safe), FadeOut(timer), FadeOut(lats[0]), FadeOut(lats[2]), FadeOut(lats[1]),
                      *[b[0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1) for b in bes]], 0.7),
            (lambda: [Create(axis), FadeIn(tl), FadeIn(ylab)], 0.7),
            (lambda: [FadeIn(down), FadeIn(downl)], 0.6),
            "A thousand",
            (lambda: [Transform(client[1], many)], 0.5),
            (lambda: [GrowFromEdge(t0, DOWN)], 0.7),
        ])

        cap = DashedLine([tx(250), BASE + 100 * YS, 0], [6.3, BASE + 100 * YS, 0], dash_length=0.1, stroke_width=2.5, color=GREEN_M)
        capl = T("it can answer 100", 18, GREEN_M).move_to([3.4, BASE + 100 * YS + 0.22, 0])
        fixed = [spike(t, n) for t, n in FIXED[1:]]
        self.steps("Each retries after a fixed 100 milliseconds, so all thousand retries land together, "
                   "where the issuer can answer 100.", [
            "so all thousand",
            (lambda: [LaggedStart(*[GrowFromEdge(s, DOWN) for s in fixed], lag_ratio=0.35)], 1.6),
            "where the issuer",
            (lambda: [Create(cap), FadeIn(capl)], 0.8),
        ])

        back = [spike(t, n) for t, n in BACKOFF[1:]]
        self.steps("Backoff doubles the wait: 100, 200, 400, 800. The waves spread out, "
                   "but every client counts the same way, so each wave still lands at once.", [
            "Backoff",
            (lambda: [*[Transform(fixed[k], back[k]) for k in range(5)]], 1.6),
            "but every client",
            (lambda: [*[Indicate(f, color=YELLOW_M, scale_factor=1.08) for f in fixed]], 1.0),
        ])

        st1 = status("no jitter: 400 of 1,000 answered, 5,400 requests", RED_M)
        self.steps("After six tries, 600 clients give up. The issuer saw 5,400 requests and answered 400 clients.", [
            (lambda: [Transform(client[1], T("600 gave up", 26, RED_M).move_to(client[1]))], 0.7),
            "The issuer saw",
            (lambda: [FadeIn(st1, shift=0.1 * UP)], 0.7),
        ])

        jit = [bucket(k, n) for k, n in enumerate(JITTER)]
        st2 = status("full jitter: all 1,000 answered in about 1.1 s, 4,194 requests", GREEN_M)
        self.steps("Jitter fixes it: each client waits a random time up to its ceiling. "
                   "Retries spread out, and all 1,000 are answered in about 1.1 seconds.", [
            "each client waits",
            (lambda: [FadeOut(VGroup(*fixed)), LaggedStart(*[GrowFromEdge(b, DOWN) for b in jit], lag_ratio=0.15)], 1.6),
            "Retries spread out",
            (lambda: [Transform(st1, st2), Transform(client[1], T("1,000 clients", 26, GREEN_M).move_to(client[1])),
                      *[b[0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M), 1) for b in bes]], 0.8),
        ])

        rows = VGroup()
        labels = VGroup()
        for k, n in enumerate((3, 9, 27)):
            y = -0.85 - 0.8 * k
            dots = VGroup(*[Dot(radius=0.08, color=GOLD_M) for _ in range(n)]).arrange(RIGHT, buff=0.2)
            dots.move_to([-3.6 + dots.width / 2, y, 0])
            rows.add(dots)
            labels.add(T(f"layer {k + 1}: {n} requests", 22, GREY_B).move_to([-5.0, y, 0]))
        st3 = status("retry budget: retries add at most about 10%", GOLD_M)
        self.steps("Retries also multiply: three layers that each try three times turn one request into 27. "
                   "A retry budget caps them at about 10 percent of traffic.", [
            (lambda: [FadeOut(VGroup(*jit, axis, tl, ylab, down, downl, t0, cap, capl, st1))], 0.6),
            "three layers",
            *[(lambda k=k: [FadeIn(labels[k]), LaggedStart(*[FadeIn(d, scale=0.5) for d in rows[k]], lag_ratio=0.05)], 0.6)
              for k in range(3)],
            "A retry budget",
            (lambda: [FadeIn(st3, shift=0.1 * UP), *[r[1:].animate.set_color(GREY_D) for r in rows]], 0.9),
        ])

        pool = VGroup(*[Line([CX + 1.2, CY + d, 0], [LX - 1.35, LY + d, 0], stroke_width=2.5, color=BLUE_M) for d in (0.25, 0, -0.25)])
        poll = T("pool", 20, BLUE_M).move_to([(CX + LX) / 2 - 0.08, CY + 0.55, 0])
        st4 = status("a new connection pays TCP and TLS handshakes; a pooled one doesn't", BLUE_M)
        self.steps("Last, the connections. A new one costs a TCP and a TLS round trip, "
                   "so a pool keeps some open and reuses them.", [
            (lambda: [FadeOut(VGroup(rows, labels, st3)), Transform(client[1], T("your service", 26).move_to(client[1]))], 0.6),
            "A new one",
            (lambda: [FadeIn(st4, shift=0.1 * UP)], 0.6),
            "so a pool",
            (lambda: [FadeOut(wc), Create(pool), FadeIn(poll)], 0.8),
            (lambda: [flow(pool[0].get_start(), pool[0].get_end(), BLUE_M, 0.4),
                      flow(pool[2].get_start(), pool[2].get_end(), BLUE_M, 0.4)], 0.5),
        ])

        idle = T("idle 350 s: the balancer forgets it", 22, RED_M).move_to([(CX + LX) / 2, CY - 0.95, 0])
        xr = tick(False, 0.17).move_to([LX - 1.6, LY - 0.25, 0])
        st5 = status("keep the pool's idle timeout shorter than the balancer's", GOLD_M)
        self.steps("But the balancer forgets a connection idle for 350 seconds, and tells nobody. "
                   "The next request on it gets a reset. Keep the pool's idle timeout shorter.", [
            (lambda: [FadeOut(st4), pool[2].animate.set_stroke(RED_M).set_opacity(0.6), FadeIn(idle)], 0.8),
            "The next request",
            (lambda: [flow(pool[2].get_start(), pool[2].get_end() + 0.25 * LEFT, RED_M, 0.5)], 0.55),
            (lambda: [Create(xr)], 0.4),
            "Keep the pool's",
            (lambda: [FadeIn(st5, shift=0.1 * UP)], 0.6),
        ])

        self.steps("Retries arrive just when the issuer is weakest. Spread them out at random, and cap them with a budget.", [
            (lambda: [FadeOut(xr), FadeOut(idle), FadeOut(pool[2]), *[glow(b[0], GREEN_M, 1.04) for b in bes]], 0.9),
            "Spread them",
            (lambda: [glow(client[0], BLUE_M, 1.05), glow(lb[0], WHITE, 1.05)], 1.0),
        ])
        self.wait(0.6)
