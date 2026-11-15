from sfz import *

CBX, CBY, CBW, CBH = -5.0, 1.1, 3.2, 2.9      # your service
SBX, SBW = 5.45, 2.1                           # the issuer
PX0, PX1, PY = -3.4, 4.4, 1.1                  # the connection
SX = [-5.95, -5.0, -4.05]                      # stream columns inside your service
APP_Y, DIV_Y, KLAB_Y, KER_Y = 1.6, 1.05, 0.74, 0.2
COL = [BLUE_M, TEAL_M, GOLD_M]
CH_Y, AXIS_Y, TICK_Y, STATUS_Y = [-1.0, -1.55, -2.1], -2.5, -2.82, -3.3
X0, SC = -4.4, 9.9 / 900                       # chart: x of 0 ms, units per ms


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(a, b, color=YELLOW_M, run_time=0.6, r=0.08):
    """A dot from a to b that stays invisible until its turn."""
    d = Dot(radius=r, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.1))


def block(color, a, b, run_time=0.9, s=0.24):
    """A small frame that slides from a to b."""
    q = Square(s).set_fill(color, 1).set_stroke(width=0).move_to(a).set_opacity(0)
    return Succession(q.animate(run_time=0.05).set_opacity(1), MoveAlongPath(q, Line(a, b), rate_func=linear, run_time=run_time),
                      FadeOut(q, run_time=0.1))


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


def sid(i, label):
    """A request (later a stream) in your service."""
    c = COL[i]
    r = RoundedRectangle(corner_radius=0.08, width=0.78, height=0.52, stroke_color=c, stroke_width=2.5).set_fill(fillc(c), 1)
    return VGroup(r, T(label, 22)).move_to([SX[i], APP_Y, 0])


def pipe(y, h=0.62):
    return RoundedRectangle(corner_radius=0.12, width=PX1 - PX0, height=h, stroke_color=GREY_C, stroke_width=2).move_to([(PX0 + PX1) / 2, y, 0])


def bar(i, t0, t1, color):
    return Rectangle(width=(t1 - t0) * SC, height=0.32, stroke_width=0).set_fill(color, 0.85).move_to(
        [X0 + (t0 + t1) / 2 * SC, CH_Y[i], 0])


def status(s, color=GREY_B):
    return T(s, 24, color).move_to([0, STATUS_Y, 0])


def packet(i, x, color=None):
    c = color or COL[i]
    q = RoundedRectangle(corner_radius=0.06, width=0.52, height=0.52, stroke_width=0).set_fill(c, 0.9)
    return VGroup(q, T(str(2 * i + 1), 22, BLACK)).move_to([x, PY, 0])


def slot(i):
    return RoundedRectangle(corner_radius=0.06, width=0.6, height=0.6, stroke_color=GREY_D, stroke_width=2).move_to([SX[i], KER_Y, 0])


def into(m, i):
    """Path from where a packet is in the pipe to its slot in your service."""
    p = VMobject().set_points_as_corners([m.get_center(), [PX0 + 0.35, PY, 0], [SX[i], KER_Y, 0]])
    return MoveAlongPath(m, p, rate_func=smooth)


class HttpVersions(Base):
    """net-11, sections 0 to 3: three authorizations of 300 ms each. HTTP/1.1 answers them one after another on a
    connection (900 ms) or needs three connections; HTTP/2 interleaves frames of streams 1, 3 and 5 on one connection
    (300 ms); one lost TCP packet holds streams 3 and 5 in the kernel until the resend, 100 ms later; HTTP/3 over QUIC
    delivers 3 and 5 at once and only stream 1 waits."""

    def construct(self):
        self.title_card("HTTP/1.1, HTTP/2 and HTTP/3", "one lost packet, and who has to wait for it")

        cbox = RoundedRectangle(corner_radius=0.16, width=CBW, height=CBH, stroke_color=WHITE, stroke_width=2.5)
        cbox.set_fill(BLACK, 1).move_to([CBX, CBY, 0])
        ctitle = T("your service", 24).move_to([CBX, CBY + CBH / 2 - 0.33, 0])
        sbox = RoundedRectangle(corner_radius=0.16, width=SBW, height=CBH, stroke_color=GREEN_M, stroke_width=2.5)
        sbox.set_fill(fillc(GREEN_M), 1).move_to([SBX, CBY, 0])
        stext = VGroup(T("issuer", 26), T("300 ms per", 19, GREY_B), T("authorization", 19, GREY_B)).arrange(DOWN, buff=0.14)
        stext.move_to([SBX, CBY, 0])
        reqs = [sid(i, str(i + 1)) for i in range(3)]
        p1 = pipe(PY)
        plab = T("one connection", 20, GREY_B).move_to([(PX0 + PX1) / 2, PY + 0.58, 0])
        rowl = [T(f"auth {i + 1}", 22, COL[i]).move_to([-5.7, CH_Y[i], 0]) for i in range(3)]
        axis = Line([X0, AXIS_Y, 0], [X0 + 900 * SC + 0.2, AXIS_Y, 0], stroke_width=2.5, color=GREY_B)
        ticks = VGroup(*[Line([X0 + t * SC, AXIS_Y - 0.08, 0], [X0 + t * SC, AXIS_Y + 0.08, 0], stroke_width=2, color=GREY_B)
                         for t in (0, 300, 600, 900)])
        tlabs = VGroup(*[T(s, 19, GREY_B).move_to([X0 + t * SC, TICK_Y, 0]) for t, s in
                         ((0, "0"), (300, "300"), (600, "600"), (900, "900 ms"))])
        self.steps("Your payment service sends three authorizations to an issuer, and each takes the issuer 300 milliseconds. "
                   "How soon are all three answered?", [
            (lambda: [FadeIn(cbox), FadeIn(ctitle)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, scale=0.8) for r in reqs], lag_ratio=0.3)], 0.9),
            "to an issuer",
            (lambda: [FadeIn(sbox), FadeIn(stext[0]), Create(p1), FadeIn(plab)], 0.8),
            "300 milliseconds",
            (lambda: [FadeIn(stext[1:])], 0.5),
            "How soon",
            (lambda: [*[FadeIn(r) for r in rowl], Create(axis), FadeIn(ticks), FadeIn(tlabs)], 0.9),
        ])

        title = T("HTTP/1.1", 34).move_to([0, 3.2, 0])
        bars = []
        green = lambda r: r[0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M), 1)

        def one(i):
            b = bar(i, 300 * i, 300 * (i + 1), COL[i])
            bars.append(b)
            return [
                (lambda: [flow([PX0 + 0.1, PY, 0], [PX1 - 0.1, PY, 0], COL[i], 0.45)], 0.5),
                (lambda: [glow(sbox, COL[i], 1.02), GrowFromEdge(b, LEFT)], 0.6),
                (lambda: [flow([PX1 - 0.1, PY, 0], [PX0 + 0.1, PY, 0], COL[i], 0.45), green(reqs[i])], 0.5),
            ]

        self.steps("HTTP/1.1 sends one request at a time on a connection. A response carries no label, "
                   "so the next request waits for this one's answer.", [
            (lambda: [FadeIn(title, shift=0.1 * DOWN)], 0.6),
            *one(0),
            "so the next",
            *one(1),
            *one(2),
        ])

        p_up, p_dn = pipe(1.9, 0.5), pipe(0.3, 0.5)
        hs = status("three connections: each pays its own TCP and TLS handshakes", GOLD_M)
        bars2 = [bar(i, 0, 300, COL[i]) for i in range(3)]
        lanes = [1.9, PY, 0.3]
        self.steps("Three requests take 900 milliseconds. The usual fix is more connections, "
                   "and each new one pays its own TCP and TLS handshakes.", [
            (lambda: [Indicate(tlabs[3], color=YELLOW_M, scale_factor=1.3)], 0.9),
            "The usual fix",
            (lambda: [FadeOut(VGroup(*bars)), FadeOut(plab), *[r[0].animate.set_stroke(COL[i]).set_fill(fillc(COL[i]), 1)
                                                               for i, r in enumerate(reqs)],
                      p1.animate.become(pipe(PY, 0.5)), Create(p_up), Create(p_dn)], 0.8),
            "and each new one",
            (lambda: [FadeIn(hs, shift=0.1 * UP)], 0.6),
            (lambda: [*[flow([PX0 + 0.1, lanes[i], 0], [PX1 - 0.1, lanes[i], 0], COL[i], 0.45) for i in range(3)]], 0.5),
            (lambda: [*[GrowFromEdge(b, LEFT) for b in bars2]], 0.6),
            (lambda: [*[flow([PX1 - 0.1, lanes[i], 0], [PX0 + 0.1, lanes[i], 0], COL[i], 0.45) for i in range(3)],
                      *[green(r) for r in reqs]], 0.5),
        ])

        title2 = T("HTTP/2", 34).move_to(title)
        streams = [sid(i, str(2 * i + 1)) for i in range(3)]
        rowl2 = [T(f"stream {2 * i + 1}", 22, COL[i]).move_to([-5.6, CH_Y[i], 0]) for i in range(3)]
        plab2 = T("one connection, streams 1, 3 and 5", 20, GREY_B).move_to(plab)
        self.steps("HTTP/2 keeps one connection and labels everything. "
                   "Each request and its response is a stream with a number: 1, 3 and 5.", [
            (lambda: [Transform(title, title2), FadeOut(hs), FadeOut(VGroup(*bars2)), FadeOut(p_up), FadeOut(p_dn),
                      p1.animate.become(pipe(PY))], 0.8),
            "and labels",
            (lambda: [FadeIn(plab2)], 0.5),
            "Each request",
            (lambda: [*[Transform(reqs[i], streams[i]) for i in range(3)], *[Transform(rowl[i], rowl2[i]) for i in range(3)]], 0.8),
            "1, 3 and 5",
            (lambda: [*[glow(r[0], COL[i], 1.1) for i, r in enumerate(reqs)]], 0.8),
        ])

        order = [0, 1, 2, 0, 1, 2]
        back = [1, 0, 2, 1, 0, 2]
        bars3 = [bar(i, 0, 300, COL[i]) for i in range(3)]
        st2 = status("one connection, all three answered in 300 ms", GREEN_M)
        self.steps("Messages are cut into frames, and each frame names its stream. "
                   "Frames of all three take turns, and answers come back in any order.", [
            (lambda: [LaggedStart(*[block(COL[i], [PX0 + 0.15, PY, 0], [PX1 - 0.15, PY, 0], 0.8) for i in order], lag_ratio=0.2)], 1.8),
            "and answers",
            (lambda: [LaggedStart(*[block(COL[i], [PX1 - 0.15, PY, 0], [PX0 + 0.15, PY, 0], 0.8) for i in back], lag_ratio=0.2),
                      *[GrowFromEdge(b, LEFT) for b in bars3]], 1.8),
            (lambda: [*[green(reqs[i]) for i in (1, 0, 2)], FadeIn(st2, shift=0.1 * UP)], 0.5),
        ])

        div = DashedLine([CBX - CBW / 2 + 0.15, DIV_Y, 0], [CBX + CBW / 2 - 0.15, DIV_Y, 0], dash_length=0.08, stroke_width=1.5, color=GREY_C)
        klab = T("TCP, in the kernel", 19, GREY_B).move_to([CBX, KLAB_Y, 0])
        slots = VGroup(*[slot(i) for i in range(3)])
        pk = [packet(i, x) for i, x in zip(range(3), (2.4, 3.05, 3.7))]
        plab3 = T("one TCP connection: one ordered stream of bytes", 20, GREY_B).move_to(plab)
        self.steps("Underneath, it's still TCP: one ordered stream of bytes. Say the three answers leave in three packets.", [
            (lambda: [FadeOut(VGroup(*bars3)), FadeOut(st2), *[r[0].animate.set_stroke(COL[i]).set_fill(fillc(COL[i]), 1)
                                                                for i, r in enumerate(reqs)],
                      Transform(plab2, plab3)], 0.7),
            (lambda: [Create(div), FadeIn(klab), FadeIn(slots)], 0.8),
            "Say the three",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.2 * LEFT) for p in pk], lag_ratio=0.3)], 0.9),
        ])

        lost_x = tick(False, 0.2).move_to([0.6, PY, 0])
        self.steps("The packet with stream 1 is lost. The packets for streams 3 and 5 arrive whole.", [
            (lambda: [pk[0].animate.move_to([0.6, PY, 0]), pk[1].animate.move_to([1.25, PY, 0]),
                      pk[2].animate.move_to([1.9, PY, 0])], 0.9),
            (lambda: [FadeOut(pk[0], scale=0.6), Create(lost_x)], 0.5),
            "The packets for",
            (lambda: [into(pk[1], 1), into(pk[2], 2), FadeOut(lost_x)], 1.2),
        ])

        hole = DashedVMobject(RoundedRectangle(corner_radius=0.06, width=0.6, height=0.6, stroke_color=RED_M, stroke_width=3),
                              num_dashes=14).move_to([SX[0], KER_Y, 0])
        held = status("3 and 5 are complete, but held behind the hole", RED_M)
        self.steps("But TCP hands nothing past a hole to your service. Streams 3 and 5 sit in the kernel, complete, waiting.", [
            (lambda: [Create(hole)], 0.6),
            "to your service",
            (lambda: [*[r.animate.set_opacity(0.4) for r in reqs]], 0.7),
            "Streams 3 and 5",
            (lambda: [pk[1].animate(rate_func=there_and_back).scale(1.15), pk[2].animate(rate_func=there_and_back).scale(1.15)], 0.7),
            (lambda: [FadeIn(held, shift=0.1 * UP)], 0.6),
        ])

        re1 = packet(0, PX1 - 0.4)
        stalled = [bar(i, 300, 400, RED_M) for i in range(3)]
        bars4 = [bar(i, 0, 300, COL[i]) for i in range(3)]
        st3 = status("one lost packet: every stream waits about 100 ms", RED_M)
        self.steps("The resend takes at least a round trip, say 100 milliseconds, and all three requests wait for it. "
                   "One loss stalled every stream.", [
            (lambda: [FadeOut(held), *[GrowFromEdge(b, LEFT) for b in bars4]], 0.6),
            (lambda: [FadeIn(re1, shift=0.2 * LEFT), *[GrowFromEdge(b, LEFT) for b in stalled]], 0.9),
            (lambda: [into(re1, 0)], 1.2),
            (lambda: [FadeOut(hole), *[r.animate.set_opacity(1) for r in reqs],
                      *[m.animate.move_to([SX[i], APP_Y, 0]).set_opacity(0) for i, m in enumerate([re1, pk[1], pk[2]])]], 0.7),
            (lambda: [*[green(r) for r in reqs]], 0.4),
            "One loss",
            (lambda: [FadeIn(st3, shift=0.1 * UP)], 0.6),
        ])

        st4 = status("at 1% loss: several stalls a second, each stopping every stream", RED_M)
        self.steps("At one percent loss, a busy connection hits several holes a second, "
                   "and each one stalls everything in flight.", [
            (lambda: [Transform(st3, st4)], 0.7),
            "and each one",
            (lambda: [*[Indicate(b, color=RED_M, scale_factor=1.15) for b in stalled]], 1.0),
        ])

        title3 = T("HTTP/3 over QUIC", 34).move_to(title)
        klab2 = T("QUIC: each stream on its own", 15, GREY_B).move_to([CBX, KLAB_Y, 0])
        seps = VGroup(*[DashedLine([x, KER_Y - 0.36, 0], [x, KER_Y + 0.36, 0], dash_length=0.06, stroke_width=1.5, color=GREY_C)
                        for x in ((SX[0] + SX[1]) / 2, (SX[1] + SX[2]) / 2)])
        plab4 = T("one QUIC connection over UDP", 20, GREY_B).move_to(plab)
        self.steps("HTTP/3 moves the streams into the transport itself. "
                   "QUIC runs over UDP and keeps each stream in order on its own.", [
            (lambda: [Transform(title, title3), FadeOut(st3), FadeOut(VGroup(*bars4, *stalled)),
                      *[r[0].animate.set_stroke(COL[i]).set_fill(fillc(COL[i]), 1) for i, r in enumerate(reqs)]], 0.8),
            "QUIC runs",
            (lambda: [Transform(plab2, plab4)], 0.6),
            "keeps each stream",
            (lambda: [Transform(klab, klab2), Create(seps)], 0.8),
        ])

        qk = [packet(i, x) for i, x in zip(range(3), (2.4, 3.05, 3.7))]
        lost2 = tick(False, 0.2).move_to([0.6, PY, 0])
        b35 = [bar(i, 0, 300, COL[i]) for i in (1, 2)]
        b1 = bar(0, 0, 300, COL[0])
        s1 = bar(0, 300, 400, RED_M)
        re2 = packet(0, PX1 - 0.4)
        st5 = status("only stream 1 waits for its resend", GREEN_M)
        self.steps("Lose the same packet. Streams 3 and 5 go straight to your service, "
                   "and only stream 1 waits for its resend.", [
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.2 * LEFT) for p in qk], lag_ratio=0.2)], 0.6),
            (lambda: [qk[0].animate.move_to([0.6, PY, 0]), qk[1].animate.move_to([1.25, PY, 0]),
                      qk[2].animate.move_to([1.9, PY, 0])], 0.8),
            (lambda: [FadeOut(qk[0], scale=0.6), Create(lost2), Create(hole)], 0.5),
            "Streams 3 and 5",
            (lambda: [into(qk[1], 1), into(qk[2], 2), FadeOut(lost2)], 1.0),
            (lambda: [*[qk[i].animate.move_to([SX[i], APP_Y, 0]).set_opacity(0) for i in (1, 2)],
                      green(reqs[1]), green(reqs[2]), *[GrowFromEdge(b, LEFT) for b in b35], GrowFromEdge(b1, LEFT)], 0.7),
            "and only stream 1",
            (lambda: [FadeIn(re2, shift=0.2 * LEFT), GrowFromEdge(s1, LEFT)], 0.7),
            (lambda: [into(re2, 0)], 1.0),
            (lambda: [FadeOut(hole), re2.animate.move_to([SX[0], APP_Y, 0]).set_opacity(0), green(reqs[0]),
                      FadeIn(st5, shift=0.1 * UP)], 0.6),
        ])

        self.steps("HTTP/2 removed the queue inside HTTP and kept the one inside TCP. "
                   "With HTTP/3, a lost packet costs only its own stream.", [
            (lambda: [glow(p1, GREY_A, 1.02)], 1.0),
            "With HTTP/3",
            (lambda: [Indicate(s1, color=RED_M, scale_factor=1.2), *[Indicate(b, color=GREEN_M, scale_factor=1.1) for b in b35]], 1.2),
        ])
        self.wait(0.6)
