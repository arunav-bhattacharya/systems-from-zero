from sfz import *

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TOP_Y = 2.65                       # the three machines
MX, WX, SX = -4.6, 0.4, 4.8        # payments machine, watcher, standby
BW, BH = 2.9, 0.85
SUB_Y = TOP_Y - BH / 2 - 0.27      # the mapping labels under the boxes
SIL_Y = 1.2                        # the silence bar
AX0, SPS = -4.5, 3.0               # x of 0 s, units per second (shared by the silence bar and the histogram)
AXY = -1.9                         # the histogram's axis
HMAX = 2.2                         # the tallest bar
CAP_Y, BAR_Y = -3.25, -2.92
LINK_Y = TOP_Y + 0.66

# The jittery link's 300 gaps, in bins of 0.1 s (bin k holds gaps from k/10 to (k+1)/10 s). Drawn from delays of
# 30 to 830 ms (seeded so that, as in the lab, exactly 15 gaps are longer than 1.5 s).
JIT_BINS = {2: 3, 3: 2, 4: 17, 5: 12, 6: 24, 7: 25, 8: 35, 9: 35, 10: 36, 11: 24, 12: 31, 13: 23, 14: 18, 15: 6, 16: 6, 17: 3}
JIT_FIRST = [1.086, 0.788, 0.993, 0.906, 1.483]
CALM_FIRST = [1.002, 0.998, 1.003]


def xs(t):
    return AX0 + SPS * t


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def gather(self, g):
        """Make a group of parts already on screen into one object on screen, so it can be transformed as a whole."""
        self.remove(*g.submobjects)
        self.add(g)
        return g

    def col(self, c):
        self.sil_col = c
        return [Wait(0.01)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
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


def machine(x, label, color):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, TOP_Y, 0])
    return VGroup(r, T(label, 24).move_to(r))


def sub(x, s, color=GREY_B):
    return T(s, 19, color).move_to([x, SUB_Y, 0])


class FailureDetection(Base):
    """dist-02, section 0. A friend on a hike texts "all good" every half hour; an hour of silence. The payments
    machine sends a heartbeat every second to a watcher that can hand its work to a standby. A timeout T: long strands
    20,000 payments; short raises a false alarm and runs one job twice (and Elasticsearch's 3 s timeout split the
    cluster). A timeout detects silence, not death. Pick T from measured gaps: the calm link (1 to 5 ms) and the
    jittery link (30 to 830 ms). 1.5 s: 0 and 15 false alarms in 5 minutes; 3 s: quiet on both, the calm link twice as
    slow. One number can't suit both links. Rules, the moral, and a check."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Slow or dead?", "how long to wait before you call it")

        # ---------------- scene 1: the hike ----------------
        ph = RoundedRectangle(corner_radius=0.3, width=2.9, height=4.6, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
        ph.move_to([0, 0.2, 0])
        scr = RoundedRectangle(corner_radius=0.15, width=2.6, height=3.9, stroke_width=0).set_fill("#15191d", 1).move_to(ph.get_center() + 0.05 * DOWN)
        who = T("your friend, hiking", 18, GREY_B).move_to([0, 2.05, 0])

        def bubble(s, t, y, color=GREEN_M):
            tx = T(s, 22, color)
            r = RoundedRectangle(corner_radius=0.14, width=tx.width + 0.4, height=0.55, stroke_color=color, stroke_width=2).set_fill(fillc(color), 1)
            g = VGroup(r, tx.move_to(r))
            left_at(g, -1.1, y)
            return VGroup(g, T(t, 16, GREY_B).next_to(g, RIGHT, buff=0.15))

        b1, b2 = bubble("all good", "10:00", 1.35), bubble("all good", "10:30", 0.6)
        self.steps("Your friend is hiking alone, and she promised to text you \"all good\" every half hour.", [
            (lambda: [FadeIn(VGroup(ph, scr), shift=0.2 * UP), FadeIn(who)], 0.8),
            "promised",
            (lambda: [FadeIn(b1, shift=0.15 * UP)], 0.5),
            "every half hour",
            (lambda: [FadeIn(b2, shift=0.15 * UP)], 0.5),
        ])
        clock = VGroup(T("now", 18, GREY_B), M("11:30", 30, YELLOW_M)).arrange(DOWN, buff=0.12).move_to([0, -1.1, 0])
        dots = T("no message for an hour", 18, RED_M).move_to([0, -0.25, 0])
        self.steps("An hour passes. Nothing.", [
            (lambda: [FadeIn(clock)], 0.6),
            "Nothing",
            (lambda: [FadeIn(dots)], 0.5),
        ], after=0.5)
        causes = VGroup(*[T(s, 22, GOLD_M) for s in ("she fell?", "no signal?", "flat phone?")])
        for i, c in enumerate(causes):
            right_at(c, -2.2, 1.1 - 1.0 * i)
        sil = chip("silence", RED_M, 24).move_to([4.1, 0.1, 0])
        arrs = VGroup(*[Arrow(c.get_right() + 0.15 * RIGHT, [-1.6, c.get_y(), 0], buff=0, stroke_width=2.5, color=GREY_B,
                              max_tip_length_to_length_ratio=0.25) for c in causes])
        a_out = Arrow([1.6, 0.1, 0], sil.get_left() + 0.12 * LEFT, buff=0, stroke_width=2.5, color=GREY_B, max_tip_length_to_length_ratio=0.2)
        self.steps("Maybe she fell. Maybe she's in a valley with no signal. Maybe her phone is flat. "
                   "From your sofa, all three look exactly the same: silence.", [
            (lambda: [FadeIn(causes[0], shift=0.1 * RIGHT), GrowArrow(arrs[0])], 0.5),
            "Maybe she's",
            (lambda: [FadeIn(causes[1], shift=0.1 * RIGHT), GrowArrow(arrs[1])], 0.5),
            "Maybe her",
            (lambda: [FadeIn(causes[2], shift=0.1 * RIGHT), GrowArrow(arrs[2])], 0.5),
            "all three",
            (lambda: [GrowArrow(a_out), FadeIn(sil, scale=0.8)], 0.7),
        ])
        self.steps("So when do you call rescue? Call too soon, and a helicopter finds her eating a sandwich. "
                   "Call too late, and help arrives late.", [
            (lambda: self.cap("when do you call rescue?", WHITE, 28), 0.6),
            "Call too soon",
            (lambda: self.cap("too soon: a helicopter finds her eating a sandwich", GOLD_M), 0.6),
            "Call too late",
            (lambda: self.cap("too late: help arrives late", RED_M), 0.6),
        ])
        self.play(FadeOut(VGroup(ph, scr, who, b1, b2, clock, dots, causes, arrs, a_out, sil)), *self.uncap(), run_time=1.0)

        # ---------------- scene 2: heartbeats, a watcher, a timeout ----------------
        mach = machine(MX, "payments machine", BLUE_M)
        wat = machine(WX, "watcher", TEAL_M)
        stb = machine(SX, "standby", GREY_B)
        hb = Arrow([MX + BW / 2 + 0.1, TOP_Y, 0], [WX - BW / 2 - 0.1, TOP_Y, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.12)
        fo = Arrow([WX + BW / 2 + 0.1, TOP_Y, 0], [SX - BW / 2 - 0.1, TOP_Y, 0], buff=0, stroke_width=3, color=GOLD_M,
                   max_tip_length_to_length_ratio=0.12)
        self.steps("Put the hike into a payments app. One machine records every café's payments. "
                   "A second machine watches it, ready to hand its work to a spare, the standby, if it dies.", [
            "One machine",
            (lambda: [FadeIn(mach, shift=0.1 * UP)], 0.6),
            "A second machine",
            (lambda: [FadeIn(wat, shift=0.1 * UP)], 0.6),
            "the standby",
            (lambda: [FadeIn(stb, shift=0.1 * UP)], 0.6),
        ])

        def beat_dot(rt=0.5, color=YELLOW_M, arrow=hb):
            d = Dot(radius=0.09, color=color).move_to(arrow.get_start())
            return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, Line(arrow.get_start(), arrow.get_end()), run_time=rt - 0.08),
                              FadeOut(d, run_time=0.04))

        self.steps("The watcher can't see inside the first machine. All it sees is messages. "
                   "So the first machine sends a small \"I'm alive\" message every second. That's called a heartbeat, like your friend's text.", [
            "All it sees",
            (lambda: [GrowArrow(hb)], 0.5),
            "So the first",
            (lambda: [beat_dot(0.6)], 0.6),
            0.4,
            (lambda: [beat_dot(0.6)], 0.6),
            "called a heartbeat",
            (lambda: [*self.put("link", T("heartbeat, every second", 18, YELLOW_M).move_to([(MX + WX) / 2, LINK_Y, 0])), beat_dot(0.6)], 0.6),
        ])
        subs = [sub(MX, "your friend"), sub(WX, "you, on the sofa"), sub(SX, "the rescue team")]
        self.steps("Map it out loud. Your friend is the machine. Her text is the heartbeat. "
                   "You, on the sofa, are the watcher. And the rescue team is the standby.", [
            "Your friend",
            (lambda: [FadeIn(subs[0], shift=0.1 * UP)], 0.5),
            "Her text",
            (lambda: [beat_dot(0.6)], 0.6),
            "You, on the sofa",
            (lambda: [FadeIn(subs[1], shift=0.1 * UP)], 0.5),
            "the rescue team",
            (lambda: [FadeIn(subs[2], shift=0.1 * UP)], 0.5),
        ])

        # the silence bar
        self.sil = ValueTracker(0.0)
        self.sil_col = YELLOW_M
        track = Line([AX0, SIL_Y, 0], [xs(3.0), SIL_Y, 0], stroke_width=2, color=GREY_D)
        ticks = VGroup(*[VGroup(Line([xs(t), SIL_Y - 0.14, 0], [xs(t), SIL_Y + 0.14, 0], stroke_width=2, color=GREY_D),
                                T(f"{t} s", 16, GREY_B).move_to([xs(t), SIL_Y + 0.33, 0])) for t in range(4)])
        sil_lab = right_at(T("silence", 22, YELLOW_M), AX0 - 0.3, SIL_Y)

        def bar_now():
            v = self.sil.get_value()
            return Rectangle(width=max(SPS * v, 0.001), height=0.22, stroke_width=0).set_fill(self.sil_col, 0.9).move_to([AX0 + SPS * v / 2, SIL_Y, 0])

        bar = always_redraw(bar_now)

        def cycle(g, dot_rt=0.5):
            """The silence grows for g seconds until a heartbeat lands, then drops to zero."""
            return [
                (lambda: [self.sil.animate(rate_func=linear).set_value(g), Succession(Wait(max(0.01, g - dot_rt)), beat_dot(dot_rt))], g),
                (lambda: [self.sil.animate.set_value(0)], 0.12),
            ]

        self.steps("Now watch the silence: the time since the last heartbeat. It grows, and each heartbeat drops it back to zero. "
                   "A healthy machine is never quiet for long.", [
            (lambda: [Create(track), FadeIn(ticks), FadeIn(sil_lab)], 0.6),
            (lambda: [FadeIn(bar)], 0.1),
            *cycle(1.0), *cycle(1.0), *cycle(1.0), *cycle(1.0),
        ])
        self.steps("So the watcher keeps one rule: if nothing has arrived for T seconds, suspect the machine. "
                   "A program with a rule like that is called a failure detector, and T is its timeout.", [
            (lambda: self.cap("if nothing arrives for T seconds, suspect the machine", WHITE), 0.6),
            *cycle(1.0),
            "called a failure detector",
            (lambda: [*self.put("wsub", sub(WX, "the failure detector", TEAL_M)), FadeOut(subs[1])], 0.6),
            *cycle(1.0),
        ])
        self.steps("The only question is how big T should be. And neither answer is free.", [
            (lambda: self.cap("how big should T be?", WHITE, 28), 0.5),
            *cycle(1.0),
        ])

        # ---------------- scene 3: a long timeout ----------------
        t10 = VGroup(Arrow([xs(3.0) + 0.1, SIL_Y, 0], [xs(3.0) + 0.75, SIL_Y, 0], buff=0, stroke_width=3, color=RED_M,
                           max_tip_length_to_length_ratio=0.3),
                     T("T = 10 s", 20, RED_M).move_to([xs(3.0) + 0.45, SIL_Y - 0.4, 0]))
        cross = tick(False, 0.3).move_to(mach[0].get_center())
        self.steps("Try a long timeout first: ten seconds. Now the machine dies.", [
            (lambda: [*self.uncap(), FadeIn(t10, shift=0.1 * RIGHT)], 0.6),
            *cycle(1.0),
            "Now the machine dies",
            (lambda: [mach[0].animate.set_stroke(GREY_D).set_fill(fillc(GREY_D)), mach[1].animate.set_opacity(0.15), Create(cross)], 0.6),
        ], after=0)
        waiting = ValueTracker(0.0)
        pay = ValueTracker(0.0)
        cnt = always_redraw(lambda: VGroup(
            T(f"silence: {waiting.get_value():.0f} s", 26, YELLOW_M),
            T(f"payments with nowhere to go: {int(pay.get_value()):,}", 26, GOLD_M)).arrange(DOWN, buff=0.35).move_to([0, -0.6, 0]))
        self.steps("The watcher waits, ten whole seconds. Meanwhile payments keep arriving, two thousand a second, and nobody takes them. "
                   "By the time it acts, twenty thousand payments are stranded.", [
            (lambda: [FadeIn(cnt)], 0.3),
            (lambda: [self.sil.animate(rate_func=linear).set_value(3.0), waiting.animate(rate_func=linear).set_value(3),
                      pay.animate(rate_func=linear).set_value(6000)], 2.4),
            (lambda: [waiting.animate(rate_func=linear).set_value(10), pay.animate(rate_func=linear).set_value(20000),
                      Indicate(t10[1], color=RED_M)], 4.0),
            "twenty thousand",
            (lambda: [*self.cap("10 s x 2,000 payments a second = 20,000 stranded", GOLD_M)], 0.6),
        ])
        self.steps("Only then does the standby take over. That step has a name too: failover.", [
            (lambda: [*self.col(RED_M), *self.put("wsub", sub(WX, "verdict: dead", RED_M))], 0.4),
            (lambda: [GrowArrow(fo), stb[0].animate.set_stroke(GOLD_M).set_fill(fillc(GOLD_M))], 0.7),
            "failover",
            (lambda: [*self.cap("failover: the standby takes over the work", GOLD_M)], 0.6),
        ])

        # ---------------- scene 4: a short timeout ----------------
        TS = 1.5
        tl = DashedLine([xs(TS), SIL_Y + 0.16, 0], [xs(TS), SIL_Y - 0.3, 0], dash_length=0.08, stroke_width=3, color=RED_M).set_z_index(3)
        tlab = left_at(T("T = 1.5 s", 20, RED_M), xs(TS) + 0.12, SIL_Y - 0.42)
        self.steps("So make it short. Say one and a half seconds. The machine is fine this time.", [
            (lambda: [FadeOut(cnt), FadeOut(t10), FadeOut(cross), FadeOut(fo), *self.uncap(), self.sil.animate.set_value(0), *self.col(YELLOW_M),
                      mach[0].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M)), mach[1].animate.set_opacity(1),
                      stb[0].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B)), *self.put("wsub", sub(WX, "the failure detector", TEAL_M))], 0.8),
            "Say one",
            (lambda: [Create(tl), FadeIn(tlab)], 0.5),
            *cycle(1.0),
        ], after=0)
        self.steps("But one heartbeat gets stuck on the way.", [
            *cycle(1.0),
            "gets stuck",
            (lambda: [self.sil.animate(rate_func=linear).set_value(TS)], 1.3),
        ], after=0)

        def late_dot():
            d = Dot(radius=0.09, color=YELLOW_M).move_to(hb.get_start())
            return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, Line(hb.get_start(), hb.get_end()), run_time=1.2), FadeOut(d, run_time=0.04))

        self.steps("The silence passes T. The watcher declares a live machine dead, and the standby takes over its work. "
                   "But the first machine is still doing that work.", [
            (lambda: [*self.col(RED_M), self.sil.animate(rate_func=linear).set_value(1.75), late_dot()], 1.3),
            "declares",
            (lambda: [*self.put("wsub", sub(WX, "verdict: dead", RED_M))], 0.4),
            "the standby takes",
            (lambda: [GrowArrow(fo), stb[0].animate.set_stroke(GOLD_M).set_fill(fillc(GOLD_M))], 0.6),
            "But the first",
            (lambda: [self.sil.animate.set_value(0), glow(mach[0], GOLD_M), glow(stb[0], GOLD_M)], 0.9),
            (lambda: self.col(YELLOW_M), 0.05),
        ])
        self.steps("Two machines, one job: a whole machine's worth of payments, charged twice.", [
            (lambda: self.cap("two machines doing one job: payments charged twice", RED_M), 0.6),
            (lambda: [glow(mach[0], GOLD_M), glow(stb[0], GOLD_M)], 0.9),
        ])
        self.steps("Well... the helicopter just found her eating a sandwich. That wrong verdict is called a false alarm.", [
            "false alarm",
            (lambda: self.cap("a false alarm: a live machine declared dead", RED_M), 0.6),
        ])
        self.steps("And it spreads. The moved work slows other machines' heartbeats, and the next false alarm follows. "
                   "A group can talk itself into declaring everyone dead.", [
            (lambda: self.cap("moved work slows the next machine's heartbeats", GREY_B), 0.5),
            "A group can",
            (lambda: self.cap("one false alarm can cause the next", RED_M), 0.5),
        ])
        self.steps("This happens for real. Elasticsearch, a search program that runs on a group of machines, split itself in two "
                   "on about one start in ten, because its machines were sometimes slower than its three second timeout. "
                   "Fifteen seconds fixed it.", [
            "split itself",
            (lambda: self.cap("a real case: a 3 s timeout split the group on about 1 start in 10", GREY_B), 0.5),
            "Fifteen seconds",
            (lambda: self.cap("a 15 s timeout fixed it", GREEN_M), 0.5),
        ])
        self.steps("Wouldn't it be nice if the watcher could just tell slow from dead? It can't. "
                   "From where it sits, a slow heartbeat and a dead machine send exactly the same thing: nothing.", [
            (lambda: [*self.uncap(), FadeOut(fo), stb[0].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B)),
                      *self.put("wsub", sub(WX, "the failure detector", TEAL_M))], 0.7),
            "exactly the same",
            (lambda: [self.sil.animate(rate_func=linear).set_value(1.4)], 1.4),
            (lambda: [self.sil.animate.set_value(0)], 0.2),
        ])
        self.steps("A timeout detects silence, not death.", [
            (lambda: self.cap("a timeout detects silence, not death", YELLOW_M, 32), 0.6),
        ], after=0.8)

        # ---------------- scene 5: pick T from data ----------------
        axis = Line([AX0, AXY, 0], [xs(3.0) + 0.1, AXY, 0], stroke_width=2, color=GREY_B)
        aticks = VGroup(*[VGroup(Line([xs(t), AXY, 0], [xs(t), AXY - 0.1, 0], stroke_width=2, color=GREY_B),
                                 T(f"{t} s", 16, GREY_B).move_to([xs(t), AXY - 0.3, 0])) for t in range(4)])
        atitle = T("gap between two heartbeats", 18, GREY_B).move_to([xs(1.5), AXY - 0.62, 0])
        tl_long = DashedLine([xs(TS), SIL_Y + 0.16, 0], [xs(TS), AXY, 0], dash_length=0.08, stroke_width=3, color=RED_M).set_z_index(3)
        U = 0.14                                    # one brick, before the full five minutes
        self.stacks = {}

        def brick_from_bar(g, color):
            k = int(g * 10)
            n = self.stacks.get(k, 0)
            self.stacks[k] = n + 1
            b = Rectangle(width=SPS * 0.1 - 0.04, height=U - 0.02, stroke_width=0).set_fill(color, 0.85)
            b.move_to([xs(k / 10 + 0.05), AXY + U * n + U / 2, 0])
            src = Rectangle(width=SPS * g, height=0.22, stroke_width=0).set_fill(color, 0.9).move_to([AX0 + SPS * g / 2, SIL_Y, 0])
            return src, b

        self.bricks = VGroup()

        def drop_cycle(g, color):
            out = cycle(g)[:1]

            def fall():
                src, b = brick_from_bar(g, color)
                self.add(src)
                self.sil.set_value(0)
                self.bricks.add(b)
                return [ReplacementTransform(src, b)]
            out.append((fall, 0.5))
            return out

        self.steps("So we pick T from data. Every time a heartbeat lands, write down the gap since the one before. Then stack the gaps up.", [
            (lambda: [*self.uncap(), Create(axis), FadeIn(aticks), FadeIn(atitle), ReplacementTransform(tl, tl_long)], 0.8),
            "write down",
            *drop_cycle(CALM_FIRST[0], TEAL_M),
            *drop_cycle(CALM_FIRST[1], TEAL_M),
        ], after=0)
        self.steps("Start with a calm link inside one building, where each heartbeat takes one to five milliseconds.", [
            (lambda: [*self.put("link", T("calm link: each heartbeat takes 1 to 5 ms", 18, TEAL_M).move_to([(MX + WX) / 2, LINK_Y, 0]))], 0.5),
            *drop_cycle(CALM_FIRST[2], TEAL_M),
        ], after=0)
        calm = Rectangle(width=SPS * 0.1 - 0.04, height=HMAX, stroke_width=0).set_fill(TEAL_M, 0.85).move_to([xs(1.05), AXY + HMAX / 2, 0])
        calm_lab = T("all 300 gaps", 18, TEAL_M).next_to(calm, LEFT, buff=0.2).align_to(calm, UP)
        self.steps("Five minutes of gaps, and every one lands within a few milliseconds of one second.", [
            (lambda: [ReplacementTransform(self.gather(self.bricks), calm)], 1.0),
            (lambda: [FadeIn(calm_lab)], 0.4),
        ])
        self.steps("With T at one and a half seconds, no gap reaches it: no false alarms. "
                   "And when the machine dies, the watcher notices in about one and a half seconds.", [
            (lambda: [glow(tl_long, RED_M, 1.0)], 0.7),
            "no false alarms",
            (lambda: self.cap("calm link, T = 1.5 s: 0 false alarms in 5 minutes", TEAL_M), 0.5),
            "notices in",
            (lambda: self.cap("calm link, T = 1.5 s: 0 false alarms, a crash noticed in 1.5 s", TEAL_M), 0.5),
        ])
        self.stamp("calm")

        # the jittery link
        self.stacks = {}
        self.bricks = VGroup()
        self.steps("Now a jittery link between two regions far apart, where each heartbeat takes anywhere from 30 to 830 milliseconds.", [
            (lambda: [FadeOut(calm), FadeOut(calm_lab), *self.uncap(),
                      *self.put("link", T("jittery link: each heartbeat takes 30 to 830 ms", 18, GOLD_M).move_to([(MX + WX) / 2, LINK_Y, 0]))], 0.6),
            *drop_cycle(JIT_FIRST[0], GOLD_M),
            *drop_cycle(JIT_FIRST[1], GOLD_M),
            *drop_cycle(JIT_FIRST[2], GOLD_M),
        ], after=0)
        self.steps("Same timeout, one and a half seconds. In five minutes, how many false alarms? Pause and guess.", [
            *drop_cycle(JIT_FIRST[3], GOLD_M),
            *drop_cycle(JIT_FIRST[4], GOLD_M),
            "Pause and guess",
            (lambda: self.cap("pause and guess: how many false alarms in 5 minutes?", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        top = max(JIT_BINS.values())
        bars = VGroup(*[Rectangle(width=SPS * 0.1 - 0.04, height=HMAX * n / top, stroke_width=0).set_fill(GOLD_M, 0.85)
                        .move_to([xs(k / 10 + 0.05), AXY + HMAX * n / top / 2, 0]) for k, n in sorted(JIT_BINS.items())])
        past = VGroup(*[b for b, (k, n) in zip(bars, sorted(JIT_BINS.items())) if k >= 15])
        self.steps("Fifteen. On a machine that never failed.", [
            (lambda: [*self.uncap(), ReplacementTransform(self.gather(self.bricks), bars)], 0.9),
            (lambda: [*[b.animate.set_fill(RED_M, 0.9) for b in past]], 0.5),
            (lambda: [*self.put("n15", T("15 false alarms", 22, RED_M).move_to([xs(1.65) + 0.95, AXY + 1.15, 0]))], 0.4),
        ])
        self.stamp("jittery15")
        self.steps("Here's why. A gap is one second, plus the difference between two delays. "
                   "One heartbeat comes fast, the next one slow, and a gap can stretch to 1.8 seconds.", [
            (lambda: self.cap("gap = 1 s + (this delay - the last delay)", WHITE), 0.5),
            "One heartbeat comes fast",
            (lambda: [beat_dot(0.25)], 0.3),
            (lambda: [beat_dot(1.0)], 1.0),
            "stretch to",
            (lambda: self.cap("1 s + (830 ms - 30 ms) = 1.8 s at most", WHITE), 0.5),
        ])
        self.steps("Every gap past T is a false alarm. And every bit of T is time a dead machine goes unnoticed.", [
            "Every gap past",
            (lambda: [glow(past, RED_M, 1.05)], 0.8),
            "every bit of T",
            (lambda: self.cap("every gap past T: a false alarm.   every second of T: a crash not yet noticed", WHITE), 0.6),
        ])
        TL = 3.0
        tl3 = DashedLine([xs(TL), SIL_Y + 0.16, 0], [xs(TL), AXY, 0], dash_length=0.08, stroke_width=3, color=RED_M).set_z_index(3)
        tlab3 = right_at(T("T = 3 s", 20, RED_M), xs(TL) - 0.12, SIL_Y - 0.42)
        self.steps("So move T out to three seconds. Now both links are quiet. "
                   "But the calm link waits three seconds to notice a crash, twice as long as it needs.", [
            (lambda: [*self.uncap(), ReplacementTransform(tl_long, tl3), ReplacementTransform(tlab, tlab3)], 0.9),
            (lambda: [*[b.animate.set_fill(GOLD_M, 0.85) for b in past], *self.put("n15", T("0 false alarms", 22, GREEN_M).move_to([xs(2.3), AXY + 1.15, 0]))], 0.5),
            "But the calm link",
            (lambda: self.cap("calm link, T = 3 s: a crash noticed in 3 s, twice as long as it needs", TEAL_M), 0.5),
        ])

        # ---------------- scene 6: one number for both links ----------------
        def cell(s, color=WHITE, size=21):
            return T(s, size, color)

        rows = [
            [cell("", GREY_B), cell("T = 1.5 s", RED_M), cell("T = 3 s", RED_M)],
            [cell("calm link", TEAL_M), cell("0 false alarms, 1.5 s to notice", GREEN_M), cell("0 false alarms, 3 s to notice", GOLD_M)],
            [cell("jittery link", GOLD_M), cell("15 false alarms", RED_M), cell("0 false alarms, 3.7 s to notice", GREEN_M)],
        ]
        colx, rowy = [-4.4, -0.9, 3.4], [0.3, -0.5, -1.3]
        table = VGroup(*[r[i].move_to([colx[i], rowy[j], 0]) for j, r in enumerate(rows) for i in range(3)])
        rules = VGroup(Line([-5.6, -0.1, 0], [5.6, -0.1, 0], stroke_width=1.5, color=GREY_D),
                       Line([-5.6, -0.9, 0], [5.6, -0.9, 0], stroke_width=1.5, color=GREY_D))
        self.steps("Side by side. At one and a half seconds, the calm link is perfect and the jittery link raises fifteen false alarms. "
                   "At three seconds, both are quiet, and the calm link is twice as slow.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(bars, axis, aticks, atitle)), *self.drop("n15"),
                      FadeOut(tlab3), Transform(tl3, DashedLine([xs(TL), SIL_Y + 0.16, 0], [xs(TL), SIL_Y - 0.3, 0], dash_length=0.08, stroke_width=3, color=RED_M))], 0.6),
            (lambda: [FadeIn(VGroup(*rows[0])), Create(rules), FadeIn(rows[1][0]), FadeIn(rows[2][0])], 0.5),
            "At one and a half",
            (lambda: [FadeIn(rows[1][1]), FadeIn(rows[2][1])], 0.6),
            "At three seconds",
            (lambda: [FadeIn(rows[1][2]), FadeIn(rows[2][2])], 0.6),
        ])
        self.stamp("table")
        self.steps("Remember the tempting plan for the hike: one deadline, say an hour, for every walk. "
                   "But she's never late in the city, and often late in the mountains. One number can't suit both links either.", [
            "But she's",
            (lambda: self.cap("the city walk is the calm link; the mountain walk is the jittery one", GREY_B), 0.5),
            "One number",
            (lambda: [*self.cap("one number can't suit both links", YELLOW_M, 30), glow(tl3, RED_M, 1.0)], 0.7),
        ])

        # ---------------- scene 7: rules ----------------
        self.steps("So, a few rules. Measure the gaps over days and over many machines, "
                   "and put T beyond the gaps you see when things are normal.", [
            (lambda: self.cap("1. measure the gaps: over days, over many machines", WHITE), 0.5),
            "and put T",
            (lambda: self.cap("2. put T beyond the gaps you see when things are normal", WHITE), 0.5),
        ])
        self.steps("And if one link needs a quick verdict and the other needs patience, "
                   "you need a timeout that learns what normal looks like. That comes next.", [
            (lambda: self.cap("3. long T strands payments; short T does the work twice", WHITE), 0.5),
            "you need",
            (lambda: self.cap("next: a timeout that learns what normal looks like", TEAL_M), 0.5),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, when do you call rescue? When the silence is longer than anything you've measured as normal.", [
            (lambda: [FadeOut(VGroup(table, rules)), FadeIn(tlab3), self.cap("when do you call rescue?", WHITE, 28)[0]], 0.6),
            "longer than anything",
            (lambda: [self.sil.animate(rate_func=linear).set_value(2.2)], 1.6),
            (lambda: [self.sil.animate.set_value(0)], 0.2),
        ])
        self.steps("A timeout detects silence, not death.", [
            (lambda: self.cap("a timeout detects silence, not death", YELLOW_M, 32), 0.6),
        ], after=0.8)
        self.steps("One quick check. Heartbeats come every second on the calm link, T is three seconds, and the machine dies. "
                   "At the very least, how long until the watcher suspects it? Pause and think.", [
            (lambda: [*self.uncap(), *self.put("link", T("calm link: each heartbeat takes 1 to 5 ms", 18, TEAL_M).move_to([(MX + WX) / 2, LINK_Y, 0]))], 0.5),
            *cycle(1.0),
            "the machine dies",
            (lambda: [mach[0].animate.set_stroke(GREY_D).set_fill(fillc(GREY_D)), mach[1].animate.set_opacity(0.15), Create(cross)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Three seconds. The timeout itself is the least time any crash takes to notice. That's the price of every second of T.", [
            (lambda: [*self.uncap(), self.sil.animate(rate_func=linear).set_value(3.0)], 2.4),
            (lambda: [*self.col(RED_M), *self.put("wsub", sub(WX, "verdict: dead, after 3 s", RED_M))], 0.4),
            "That's the price",
            (lambda: self.cap("the timeout is the least time a crash takes to notice", YELLOW_M, 28), 0.5),
        ])
        self.wait(2.0)
