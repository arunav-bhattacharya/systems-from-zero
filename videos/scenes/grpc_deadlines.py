from sfz import *

SAY.insert(0, (r"\bDEADLINE_EXCEEDED\b", "deadline exceeded"))
SAY.insert(0, (r"\bgrpc-java\b", "G R P C java"))
SAY.insert(0, (r"\bgrpc-timeout\b", "G R P C timeout"))
SAY.insert(0, (r"\bgRPC's\b", "G R P C's"))
SAY.insert(0, (r"\bgRPC\b", "G R P C"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BOX_Y, BW, BH = 2.7, 2.3, 0.7
BX = {"A": -4.6, "B": 0.0, "C": 4.6}
CHIP_Y = 3.2
ROLE_Y = 2.05
LANE_Y = {"A": 1.25, "B": 0.6, "C": -0.05}
LANE_H = 0.42
AX_Y = -0.55
TL0, TPU = -4.1, 0.0158          # x of t = 0 ms, units per ms
OUT_Y0, OUT_DY = -1.3, 0.36      # the demo's printed lines
CAP_Y, BAR_Y = -3.3, -2.9


def tx(t):
    return TL0 + t * TPU


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
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


def svc(k, name, color):
    t = T(name, 24)
    r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    return VGroup(r, t.move_to(r)).move_to([BX[k], BOX_Y, 0])


def hop(a, b, color=GREY_B):
    return Arrow([BX[a] + BW / 2 + 0.08, BOX_Y, 0], [BX[b] - BW / 2 - 0.08, BOX_Y, 0], buff=0, stroke_width=3, color=color,
                 max_tip_length_to_length_ratio=0.12)


def hop_chip(a, b, s, color=YELLOW_M, size=17):
    t = T(s, size, color)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.44, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    g = VGroup(r, t.move_to(r))
    return fit(g, 2.15).move_to([(BX[a] + BX[b]) / 2, CHIP_Y + 0.03, 0])


def dot_hop(a, b, color=YELLOW_M, rt=0.6, frac=1.0, keep=False):
    s = np.array([BX[a] + BW / 2 + 0.1, BOX_Y, 0])
    e = np.array([BX[b] - BW / 2 - 0.1, BOX_Y, 0])
    e = s + frac * (e - s)
    d = Dot(radius=0.08, color=color).move_to(s)
    seq = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(s, e), rate_func=smooth, run_time=rt)]
    if not keep:
        seq.append(FadeOut(d, run_time=0.15))
    return d, Succession(*seq)


def role(k, s, color=GREY_B):
    return T(s, 20, color).move_to([BX[k], ROLE_Y, 0])


def seg(k, t0, t1, color, label="", lcolor=WHITE, op=0.55):
    r = Rectangle(width=max(0.02, (t1 - t0) * TPU), height=LANE_H, stroke_width=0).set_fill(color, op)
    r.move_to([(tx(t0) + tx(t1)) / 2, LANE_Y[k], 0])
    g = VGroup(r)
    if label:
        t = T(label, 16, lcolor)
        if t.width + 0.2 < r.width:
            g.add(t.move_to(r))
    return g


def grow(g, rt=None):
    anims = [GrowFromEdge(g[0], LEFT)]
    if len(g) > 1:
        anims.append(FadeIn(g[1]))
    return Succession(*anims) if len(anims) > 1 else anims[0]


def lane_labels():
    return VGroup(*[right_at(T(n, 20, c), TL0 - 0.25, LANE_Y[k]) for k, n, c in
                    [("A", "checkout", WHITE), ("B", "payments", BLUE_M), ("C", "issuer", GOLD_M)]])


def axis():
    line = Line([tx(0), AX_Y, 0], [tx(650), AX_Y, 0], stroke_width=2, color=GREY_C)
    ticks = VGroup(*[Line([tx(t), AX_Y - 0.07, 0], [tx(t), AX_Y + 0.07, 0], stroke_width=2, color=GREY_C) for t in range(0, 700, 100)])
    nums = VGroup(*[T(str(t), 16, GREY_B).move_to([tx(t), AX_Y - 0.27, 0]) for t in range(0, 700, 100)])
    unit = T("ms", 16, GREY_B).move_to([tx(650) + 0.05, AX_Y - 0.27, 0])
    return VGroup(line, ticks, nums, unit)


def deadline_line():
    l = DashedLine([tx(300), AX_Y, 0], [tx(300), LANE_Y["A"] + 0.38, 0], dash_length=0.1, stroke_width=3, color=YELLOW_M)
    lab = T("deadline: 300 ms", 18, YELLOW_M).move_to([tx(300), LANE_Y["A"] + 0.6, 0])
    return VGroup(l, lab)


def out_line(i, s, color=WHITE):
    return left_at(M(s, 17, color), -5.6, OUT_Y0 - i * OUT_DY)


class GrpcDeadlines(Base):
    """enc-04, section 2. checkout -> payments -> issuer, over gRPC. Without a deadline a lost reply means waiting
    forever. The bike-shop phone call: "I can hold for five minutes", and the clerk who passes the time on (or
    doesn't). The lesson's demo: a 300 ms deadline, 120 ms of payments work, an issuer that needs 500 ms. The fair
    guess (the issuer works to 627 for nobody) is broken by the real run: 173 ms left, everyone stops by 321.
    grpc-timeout carries time remaining, not a clock time. One line of Kotlin, three rules, a check question."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        fit(new, 13.0)
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_chip(self, i, a, b, s, color=YELLOW_M):
        new = hop_chip(a, b, s, color)
        old, self.chips[i] = self.chips[i], new
        return [swap(old, new)]

    def clear_chips(self):
        olds = [c for c in self.chips if c is not None]
        self.chips = [None, None]
        return [FadeOut(c) for c in olds]

    def construct(self):
        self.capm = None
        self.chips = [None, None]
        self.title_card("How long should a call wait?", "a deadline that travels down the call chain")

        # ---------------- scene 1: the question ----------------
        A = svc("A", "checkout", WHITE)
        far = VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=GREY_B, stroke_width=2.5),
                                    num_dashes=36), T("far away", 22, GREY_B)).move_to([BX["C"], BOX_Y, 0])
        far_ar = Arrow([BX["A"] + BW / 2 + 0.08, BOX_Y, 0], [BX["C"] - BW / 2 - 0.08, BOX_Y, 0], buff=0, stroke_width=3,
                       color=GREY_B, max_tip_length_to_length_ratio=0.03)
        self.steps("Picture buying a book online. You press Pay, and the shop's program asks another program, far away, to charge your card. "
                   "Then it waits.", [
            "You press Pay",
            (lambda: [FadeIn(A, shift=0.15 * UP)], 0.7),
            "another program",
            (lambda: [FadeIn(far), GrowArrow(far_ar)], 0.8),
            "to charge",
            (lambda: [dot_hop("A", "C", rt=1.0)[1]], 1.2),
            "Then it waits",
            (lambda: self.cap("waiting...", GREY_B), 0.5),
        ])
        qm = T("?", 60, YELLOW_M).move_to([0, 0.6, 0])
        self.steps("How long should it wait? And when it gives up, does the far side stop working too?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
            "does the far side",
            (lambda: [glow(far[0], GREY_B, 1.05)], 0.9),
        ])
        lost_dot, lost_go = dot_hop("A", "C", rt=0.9, frac=0.5, keep=True)
        lost_x = tick(False, 0.15).move_to([(BX["A"] + BX["C"]) / 2, BOX_Y, 0])
        self.steps("In your own code, a function call returns, or it throws, faster than you can blink. "
                   "A call to another computer can do a third thing: nothing at all. "
                   "The question gets lost, or the answer does, and no reply ever comes.", [
            (lambda: [FadeOut(qm), *self.cap("a call in your own code: it returns, or it throws", WHITE)], 0.6),
            "A call to another",
            (lambda: self.cap("a call to another computer: returns, throws, or... nothing", YELLOW_M), 0.6),
            "The question gets lost",
            (lambda: [lost_go], 1.0),
            (lambda: [FadeOut(lost_dot, scale=1.8), Create(lost_x)], 0.5),
        ])

        # ---------------- scene 2: waiting forever ----------------
        B = svc("B", "payments", BLUE_M)
        C = svc("C", "issuer", GOLD_M)
        ab, bc = hop("A", "B"), hop("B", "C")
        bank_lab = role("C", "the card's bank", GOLD_M)
        self.steps("Let's give the programs names. Checkout is the shop's program. It calls payments, "
                   "which calls the issuer, the bank that gave the customer the card.", [
            (lambda: [FadeOut(lost_x), FadeOut(far_ar), FadeOut(far), *self.uncap()], 0.6),
            "Checkout is",
            (lambda: [glow(A[0], WHITE, 1.05)], 0.7),
            "It calls payments",
            (lambda: [GrowArrow(ab), FadeIn(B, shift=0.1 * RIGHT)], 0.7),
            "which calls the issuer",
            (lambda: [GrowArrow(bc), FadeIn(C, shift=0.1 * RIGHT)], 0.7),
            "the bank",
            (lambda: [FadeIn(bank_lab)], 0.5),
        ])
        self.steps("They talk with gRPC, a free tool from Google that lets one program call a function inside another program, over the network.", [
            (lambda: self.cap("gRPC: one program calls a function in another, over the network", WHITE), 0.6),
            "call a function",
            (lambda: [dot_hop("A", "B")[1]], 0.8),
            (lambda: [dot_hop("B", "C")[1]], 0.8),
        ])
        wait_bar = Rectangle(width=0.02, height=LANE_H, stroke_width=0).set_fill(GREY_B, 0.55)
        wait_bar.move_to([-5.6, LANE_Y["A"], 0], aligned_edge=LEFT)
        wait_lab = left_at(T("checkout waiting", 18, GREY_B), -5.6, LANE_Y["A"] + 0.42)
        self.steps("And here's the catch. gRPC sets no time limit unless you set one. So if a reply is lost, checkout waits forever.", [
            (lambda: [FadeOut(bank_lab), *self.set_chip(0, "A", "B", "no time limit", RED_M)], 0.6),
            "So if a reply",
            (lambda: [FadeIn(wait_lab), wait_bar.animate.stretch_to_fit_width(11.6).move_to([-5.6, LANE_Y["A"], 0], aligned_edge=LEFT)], 3.0),
        ])
        threads = VGroup(*[RoundedRectangle(corner_radius=0.06, width=0.36, height=0.36, stroke_color=GREY_B, stroke_width=2)
                           .set_fill(BLACK, 1) for _ in range(10)]).arrange(RIGHT, buff=0.18)
        left_at(threads, -5.6 + 1.9, LANE_Y["C"])
        th_lab = right_at(T("threads", 20, GREY_B), -5.6 + 1.65, LANE_Y["C"])
        self.steps("While it waits, it holds a thread, one path of work in the program. "
                   "Lose enough replies, and the shop runs out of threads.", [
            (lambda: [*self.cap("a thread: one path of work in the program", WHITE), FadeIn(th_lab), FadeIn(threads)], 0.7),
            (lambda: [threads[0].animate.set_fill(RED_M, 0.6).set_stroke(RED_M)], 0.4),
            "Lose enough",
            (lambda: [LaggedStart(*[t.animate.set_fill(RED_M, 0.6).set_stroke(RED_M) for t in threads[1:]], lag_ratio=0.3)], 2.0),
            (lambda: self.cap("all threads waiting: nothing left to serve the next customer", RED_M), 0.5),
        ])
        self.steps("Forever is a long time, even for a computer.", [0.2], after=0.5)
        self.steps("What we want is a rule: wait this long, and no longer. And when we stop waiting, everyone down the line should stop too.", [
            (lambda: [FadeOut(VGroup(wait_bar, wait_lab, threads, th_lab)), *self.set_chip(0, "A", "B", "wait this long", YELLOW_M)], 0.7),
            "everyone down",
            (lambda: [*self.cap("wait this long, and no longer. Then everyone stops.", YELLOW_M),
                      glow(B[0], BLUE_M), glow(C[0], GOLD_M)], 0.9),
        ])

        # ---------------- scene 3: the bike shop ----------------
        roles = [role("A", "you"), role("B", "the clerk"), role("C", "the warehouse")]
        self.steps("Think of a phone call. You ring a bike shop and ask for a part. You say: I can hold for five minutes.", [
            (lambda: [*self.uncap(), *self.clear_chips()], 0.5),
            "You ring",
            (lambda: [FadeIn(roles[0]), FadeIn(roles[1])], 0.6),
            (lambda: [dot_hop("A", "B", WHITE)[1]], 0.7),
            "I can hold",
            (lambda: self.set_chip(0, "A", "B", "I can hold 5 min", YELLOW_M), 0.6),
        ])
        self.steps("The clerk puts you on hold and phones the warehouse. A good clerk says: I need it within three minutes. "
                   "Two minutes have gone already, so three are left.", [
            "phones the warehouse",
            (lambda: [FadeIn(roles[2]), dot_hop("B", "C", WHITE)[1]], 0.7),
            "A good clerk",
            (lambda: self.set_chip(1, "B", "C", "within 3 min", GREEN_M), 0.6),
            "Two minutes",
            (lambda: self.cap("5 minutes, minus 2 already gone: 3 left", WHITE), 0.6),
        ])
        hung = role("A", "hung up", RED_M)
        search = role("C", "searching: 10 min", RED_M)
        self.steps("A careless clerk says nothing. So the warehouse climbs a ladder and searches for ten minutes, for a customer who hung up long ago.", [
            (lambda: [*self.uncap(), *self.set_chip(1, "B", "C", "(nothing)", RED_M)], 0.6),
            "searches for ten",
            (lambda: [swap(roles[2], search), Wiggle(C, scale_value=1.05, rotation_angle=0.02 * TAU)], 1.0),
            "who hung up",
            (lambda: [swap(roles[0], hung)], 0.6),
        ], after=0.5)
        r0c, r2c = roles[0].copy(), roles[2].copy()
        role_mobs = [r0c, roles[1], r2c]
        self.steps("Let's map it. You are checkout. The clerk is payments. The warehouse is the issuer.", [
            (lambda: [swap(hung, r0c), swap(search, r2c), *self.set_chip(1, "B", "C", "within 3 min", GREEN_M)], 0.6),
            "You are checkout",
            (lambda: [glow(A[0], WHITE)], 0.6),
            "The clerk is",
            (lambda: [glow(B[0], BLUE_M)], 0.6),
            "The warehouse is",
            (lambda: [glow(C[0], GOLD_M)], 0.6),
        ])
        self.steps("And \"I can hold for five minutes\" is the deadline: the moment after which the caller stops waiting.", [
            (lambda: [glow(self.chips[0][0], YELLOW_M, 1.1)], 0.7),
            "is the deadline",
            (lambda: self.cap("the deadline: the moment after which the caller stops waiting", YELLOW_M), 0.6),
        ])

        # ---------------- scene 4: the numbers, and a guess ----------------
        ax, lanes, dl = axis(), lane_labels(), deadline_line()
        w_work = T("120 ms of work", 17, BLUE_M)
        w_need = T("needs 500 ms", 17, GOLD_M)
        self.steps("Now the real numbers, from the lesson's demo. Checkout calls payments with a deadline of 300 milliseconds.", [
            (lambda: [*self.uncap(), *[FadeOut(m) for m in role_mobs], *self.clear_chips()], 0.5),
            (lambda: [Create(ax), FadeIn(lanes)], 1.0),
            "with a deadline",
            (lambda: [*self.set_chip(0, "A", "B", "deadline 300 ms"), Create(dl[0]), FadeIn(dl[1])], 0.8),
        ])
        self.steps("Payments does 120 milliseconds of its own work, then calls the issuer, and sets no deadline of its own. "
                   "The issuer is slow today. It needs 500 milliseconds.", [
            "Payments does",
            (lambda: [FadeIn(left_at(w_work, tx(0), LANE_Y["B"]))], 0.5),
            "then calls the issuer",
            (lambda: self.set_chip(1, "B", "C", "no deadline set", GREY_B), 0.6),
            "It needs",
            (lambda: [FadeIn(left_at(w_need, tx(127), LANE_Y["C"]))], 0.5),
        ])
        self.steps("So when the issuer's call arrives, how much time does it see left? And who gives up first? Pause and guess.", [
            (lambda: [glow(self.chips[1][0], YELLOW_M, 1.1)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 5: the fair guess, then the real run ----------------
        g_a = seg("A", 0, 300, GREY_B, "waiting")
        g_b1 = seg("B", 0, 120, BLUE_M, "own work")
        g_b2 = seg("B", 120, 300, GREY_B, "waiting")
        g_c1 = seg("C", 127, 300, GOLD_M, "working")
        g_c2 = seg("C", 300, 627, RED_M, "work for nobody")
        x_a = tick(False, 0.13).move_to([tx(300) + 0.22, LANE_Y["A"], 0])
        end627 = T("627", 16, RED_M).move_to([tx(627), LANE_Y["C"] - 0.36, 0])
        self.steps("The fair guess goes like this. Payments set no deadline, so the issuer has none. At 300, checkout gives up.", [
            (lambda: [*self.uncap(), FadeOut(w_work), FadeOut(w_need), *self.cap("the fair guess", PURPLE_M)], 0.5),
            "so the issuer",
            (lambda: [grow(g_a), grow(g_b1)], 0.9),
            (lambda: [grow(g_b2), grow(g_c1)], 0.9),
            "At 300",
            (lambda: [Create(x_a)], 0.5),
        ])
        self.steps("But the issuer works on until about 627. A third of a second of work for nobody, holding a thread the whole time. The careless clerk.", [
            (lambda: [grow(g_c2)], 1.4),
            (lambda: [FadeIn(end627)], 0.4),
            "The careless",
            (lambda: [glow(self.chips[1][0], RED_M, 1.1)], 0.7),
        ])
        self.steps("Now the real run.", [
            (lambda: [FadeOut(VGroup(g_a, g_b1, g_b2, g_c1, g_c2, x_a, end627)), *self.uncap(),
                      *self.set_chip(0, "A", "B", "deadline 300 ms"), *self.set_chip(1, "B", "C", "?", GREY_B)], 0.6),
        ])
        r_a = seg("A", 0, 311, GREY_B, "waiting")
        r_b1 = seg("B", 1, 121, BLUE_M, "own work")
        r_b2 = seg("B", 121, 312, GREY_B, "waiting")
        r_c = seg("C", 127, 321, GOLD_M, "working")
        outs = [out_line(0, "  1 ms  payments got pay-1, 299 ms left"),
                out_line(1, "127 ms  issuer   got pay-1, 173 ms left", GOLD_M),
                out_line(2, "311 ms  checkout gets DEADLINE_EXCEEDED", RED_M),
                out_line(3, "312 ms  payments issuer call ended: DEADLINE_EXCEEDED"),
                out_line(4, "321 ms  issuer   sees the call cancelled, stops", GOLD_M)]
        self.steps("Payments gets the call with 299 milliseconds left. At 127, the issuer gets its call, with 173 milliseconds left.", [
            (lambda: [FadeIn(outs[0]), *self.set_chip(0, "A", "B", "299 ms left"), dot_hop("A", "B")[1]], 0.7),
            (lambda: [grow(r_b1)], 0.8),
            "At 127",
            (lambda: [FadeIn(outs[1]), dot_hop("B", "C")[1]], 0.7),
            "with 173",
            (lambda: [*self.set_chip(1, "B", "C", "173 ms left", GREEN_M), grow(r_c)], 0.7),
        ])
        self.steps("Payments never set a deadline, and still the issuer knew.", [
            (lambda: [glow(self.chips[1][0], GREEN_M, 1.12), Indicate(outs[1], color=GOLD_M, scale_factor=1.05)], 1.0),
        ])
        stops = VGroup(*[tick(False, 0.11).move_to([tx(t) + 0.2, LANE_Y[k], 0]) for k, t in [("A", 311), ("B", 312), ("C", 321)]])
        self.steps("At 311, checkout gets deadline exceeded. One millisecond later, payments' call to the issuer ends too. "
                   "And at 321, the issuer sees its call cancelled, and stops.", [
            (lambda: [grow(r_a), grow(r_b2)], 0.8),
            (lambda: [FadeIn(outs[2]), Create(stops[0])], 0.5),
            "One millisecond",
            (lambda: [FadeIn(outs[3]), Create(stops[1])], 0.5),
            "And at 321",
            (lambda: [FadeIn(outs[4]), Create(stops[2])], 0.5),
        ])
        self.steps("So the library was the good clerk all along.", [
            (lambda: [*self.cap("everyone stops together, near 300", GREEN_M)], 0.6),
        ], after=0.6)

        # ---------------- scene 6: how it travels, and its name ----------------
        hdr = hop_chip("B", "C", "grpc-timeout: 173 ms", GREEN_M)
        self.steps("Here's how it travels. Every call carries headers, lines of extra detail sent with it. "
                   "The deadline rides in one named grpc-timeout, as time remaining, not as a time on the clock.", [
            (lambda: [*self.uncap(), *[FadeOut(o) for o in outs]], 0.5),
            "headers",
            (lambda: self.cap("headers: lines of extra detail sent with a call", WHITE), 0.6),
            "named grpc-timeout",
            (lambda: [swap(self.chips[1], hdr)], 0.7),
            "as time remaining",
            (lambda: self.cap("time remaining, not a time on the clock", YELLOW_M), 0.6),
        ])
        self.chips[1] = hdr
        clk = VGroup(T("checkout's clock  12:00:00.000", 18, WHITE), T("payments' clock   12:00:00.400", 18, PURPLE_M)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        clk_box = VGroup(SurroundingRectangle(clk, buff=0.18, corner_radius=0.08, stroke_color=PURPLE_M, stroke_width=2).set_fill(BLACK, 1), clk)
        clk_box.move_to([3.4, -1.95, 0])
        self.steps("Why not send a clock time, like \"stop at 12 o'clock and 300 milliseconds\"? "
                   "Because two machines' clocks never agree exactly.", [
            (lambda: self.cap("stop at 12:00:00.300?", PURPLE_M), 0.6),
            "Because two",
            (lambda: [FadeIn(clk_box, shift=0.1 * UP)], 0.7),
        ])
        no_clk = tick(False, 0.22).move_to(clk_box.get_right() + 0.4 * RIGHT)
        self.steps("\"I can hold for five minutes\" works whatever each watch says.", [
            (lambda: [Create(no_clk)], 0.5),
            (lambda: self.cap("time remaining: the clocks don't have to agree", YELLOW_M), 0.6),
        ])
        self.steps("grpc-java, gRPC's library for Java and Kotlin, and its library for the Go language, "
                   "pass the time that's left on to the next call by themselves.", [
            (lambda: [FadeOut(clk_box), FadeOut(no_clk), *self.cap("grpc-java (Java, Kotlin) and grpc-go pass it on by themselves", WHITE)], 0.6),
            "pass the time",
            (lambda: [dot_hop("B", "C", GREEN_M)[1]], 0.8),
        ])
        self.steps("When it runs out, the caller gets deadline exceeded, and the server's side of the call is cancelled.", [
            "the caller gets",
            (lambda: [FadeIn(outs[2], shift=0.1 * UP)], 0.6),
            "is cancelled",
            (lambda: [FadeIn(outs[4], shift=0.1 * UP)], 0.6),
        ])

        # ---------------- scene 7: in code ----------------
        code = VGroup(
            M('call(toPayments, charge, "pay-1",', 16),
            M('CallOptions.DEFAULT.withDeadlineAfter(300, TimeUnit.MILLISECONDS))', 16, YELLOW_M),
            M("call(toIssuer, authorize, request)", 16),
            M("// grpc-java passes the remaining deadline on by itself", 16, GREY_B),
        ).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        code[1].shift(RIGHT * 0.6)
        code[2].shift(DOWN * 0.1)
        code[3].shift(DOWN * 0.1)
        fit(code, 12.4)
        code_box = VGroup(SurroundingRectangle(code, buff=0.2, corner_radius=0.1, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1), code)
        code_box.move_to([0, -2.25, 0])
        self.steps("In code, it's one setting on the call: with deadline after, 300, milliseconds. And payments' own call to the issuer needs nothing extra.", [
            (lambda: [*self.uncap(), FadeOut(outs[2]), FadeOut(outs[4])], 0.5),
            (lambda: [FadeIn(code_box[0]), FadeIn(code[0]), FadeIn(code[1])], 0.7),
            "And payments'",
            (lambda: [FadeIn(code[2]), FadeIn(code[3])], 0.6),
        ], after=0.8)

        # ---------------- scene 8: rules ----------------
        rules = VGroup(T("1. gRPC sets no deadline unless you do: give every call one", 22),
                       T("2. Java and Go pass it on; elsewhere, check, and pass it on yourself", 22),
                       T("3. deadline exceeded: nobody knows what happened, so a retry isn't safe yet", 22, RED_M))
        rules.arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        fit(rules, 12.6).move_to([0, -2.05, 0])
        self.steps("Three rules. One: gRPC sets no deadline unless you do, so give every call one.", [
            (lambda: [FadeOut(code_box)], 0.5),
            (lambda: [FadeIn(rules[0], shift=0.1 * UP)], 0.6),
        ])
        self.steps("Two: Java and Go pass it on for you. With another library, check, and pass it on yourself if you have to.", [
            (lambda: [FadeIn(rules[1], shift=0.1 * UP)], 0.6),
        ])
        self.steps("Three: deadline exceeded means nobody knows what happened. The card may have been charged just before the end. "
                   "So calling again isn't safe yet. Later in this lesson, a retry gets a key, so it can't charge a card twice.", [
            (lambda: [FadeIn(rules[2], shift=0.1 * UP)], 0.6),
            "The card may",
            (lambda: [glow(C[0], RED_M)], 0.8),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So how long should a call wait? As long as its caller can, and no longer. Give the first call a deadline.", [
            (lambda: [FadeOut(rules)], 0.5),
            "As long as",
            (lambda: [*self.cap("as long as its caller can, and no longer", YELLOW_M), glow(A[0], WHITE)], 0.7),
            "Give the first",
            (lambda: [Indicate(self.chips[0], color=YELLOW_M, scale_factor=1.08)], 0.7),
        ])
        self.steps("It travels down the chain as time remaining, and when it runs out, everyone stops together. "
                   "No warehouse searching for a customer who hung up.", [
            (lambda: [dot_hop("A", "B")[1]], 0.6),
            (lambda: [dot_hop("B", "C")[1]], 0.6),
            "everyone stops",
            (lambda: [LaggedStart(*[Indicate(s, color=RED_M, scale_factor=1.5) for s in stops], lag_ratio=0.3)], 1.0),
        ], after=0.5)
        c_b1 = seg("B", 0, 250, BLUE_M, "250 ms of work")
        self.steps("One quick check. Checkout sets 300 milliseconds again. This time, payments works for 250 before it calls the issuer. "
                   "About how much time does the issuer see left? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(r_a, r_b1, r_b2, r_c, stops)), *self.set_chip(0, "A", "B", "deadline 300 ms"),
                      *self.set_chip(1, "B", "C", "? ms left", YELLOW_M)], 0.6),
            "payments works",
            (lambda: [grow(c_b1)], 1.0),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        c_c = seg("C", 250, 300, GOLD_M)
        self.steps("About 50 milliseconds. 300, minus the 250 already spent.", [
            (lambda: [*self.set_chip(1, "B", "C", "about 50 ms left", GREEN_M), *self.uncap()], 0.6),
            "300, minus",
            (lambda: [grow(c_c), *self.cap("300 - 250 = about 50 ms left", GREEN_M)], 0.8),
        ], after=0.3)
        self.play(*self.cap("a deadline travels as time left, and everyone stops together", YELLOW_M), run_time=0.7)
        self.wait(2.0)
