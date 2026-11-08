from sfz import *

SAY.insert(0, (r"\bm-7\b", "M seven"))

S_C, C_C, W_C = TEAL_M, BLUE_M, YELLOW_M        # service, consumer, watermark
LANE_Y = 2.75                                   # the service and the consumer
AX_Y = -1.55                                    # the event-time axis
WIN_Y, WIN_H = -0.25, 2.0                       # windows' centre and height
BOT = -2.85


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def ex(s):
    """x on the event-time axis for s seconds."""
    return -5.4 + s * 0.06


def node(label, x, color):
    r = RoundedRectangle(corner_radius=0.14, width=2.9, height=0.85, stroke_color=color, stroke_width=3)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14), opacity=1).move_to([x, LANE_Y, 0])
    return VGroup(r, T(label, 26).move_to([x, LANE_Y, 0]))


def stamp(kind, t, x, color):
    a = T(kind, 20, GREY_B).move_to([x, LANE_Y - 0.72, 0])
    b = M(t, 20, color).move_to([x, LANE_Y - 1.02, 0])
    return VGroup(a, b)


def win_box(i, stroke=WHITE):
    x0, x1 = ex(60 * i) + 0.06, ex(60 * i + 60) - 0.06
    r = RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=WIN_H, stroke_color=stroke, stroke_width=2.5).set_fill(BLACK, 1)
    return r.move_to([(x0 + x1) / 2, WIN_Y, 0])


def win_title(i):
    return T(f"{60 * i} to {60 * i + 60} s", 24, GREY_B).move_to([ex(60 * i + 30), WIN_Y + 0.72, 0])


def win_status(i, s, color=GREY_B):
    return T(s, 22, color).move_to([ex(60 * i + 30), WIN_Y - 0.72, 0])


def event_chip(s, color):
    t = M(s, 20, WHITE)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.55, stroke_color=color, stroke_width=2.5)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.25), opacity=1)
    return VGroup(r, t)


class Watermarks(Base):
    """stream-04, section 2: event time against processing time (the redeploy spike), then the stepper's run: one event a
    second, one-minute windows, a watermark with 10 s of grace, a straggler from 59 s counted, one from 100 s dropped."""

    def construct(self):
        self.title_card("Watermarks", "event time, windows and late events")

        svc, con = node("payment service", -4.75, S_C), node("consumer", 4.75, C_C)
        pipe = Arrow([-3.25, LANE_Y, 0], [3.25, LANE_Y, 0], buff=0.05, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.04)
        self.steps("The fraud team counts card authorizations for merchant m-7. Each one arrives as an event, sent by the payment service to a consumer.", [
            (lambda: [FadeIn(svc), FadeIn(con)], 0.9),
            "Each one arrives",
            (lambda: [GrowArrow(pipe)], 0.7),
            (lambda: [LaggedStart(*[travel(pipe, S_C, 1.0) for _ in range(4)], lag_ratio=0.3)], 1.9),
        ])

        st_e = stamp("event time", "10:01:07.000", -4.75, S_C)
        st_p = stamp("processing time", "10:01:07.004", 4.75, C_C)
        self.steps("Each event carries the time the card was used, stamped by the payment service. That's its event time. "
                   "The moment the consumer reads it is processing time.", [
            "stamped by",
            (lambda: [FadeIn(st_e, shift=0.1 * DOWN)], 0.8),
            "The moment",
            (lambda: [travel(pipe, S_C, 1.0)], 1.0),
            (lambda: [FadeIn(st_p, shift=0.1 * DOWN)], 0.8),
        ])

        q = Rectangle(width=0.05, height=0.36, stroke_width=0).set_fill(S_C, 0.55).move_to([3.1, LANE_Y, 0], aligned_edge=RIGHT)
        q_full = Rectangle(width=4.2, height=0.36, stroke_width=0).set_fill(S_C, 0.55).move_to([3.1, LANE_Y, 0], aligned_edge=RIGHT)
        q_l = T("6,000 events waiting", 22, S_C).move_to([1.0, LANE_Y + 0.45, 0])
        down = T("redeploying", 22, RED_M).move_to([4.75, LANE_Y - 0.72, 0])
        self.steps("Usually they're milliseconds apart. But stop the consumer for a minute to redeploy it, "
                   "and that minute's events pile up, then arrive at once.", [
            "But stop",
            (lambda: [FadeOut(st_p), FadeOut(st_e), con[0].animate.set_stroke(GREY_D), con[1].animate.set_color(GREY_C), FadeIn(down)], 0.8),
            "and that minute's",
            (lambda: [FadeIn(q)], 0.1),
            (lambda: [Transform(q, q_full), FadeIn(q_l)], 1.6),
            "then arrive at once",
            (lambda: [FadeOut(down), con[0].animate.set_stroke(C_C), con[1].animate.set_color(WHITE)], 0.5),
            (lambda: [q.animate.stretch_to_fit_width(0.05).move_to([3.1, LANE_Y, 0], aligned_edge=RIGHT), FadeOut(q_l)], 1.0),
        ])

        by_p = T("by processing time: 100, then 0 for a minute, then 2,000 a second", 24, RED_M).move_to([0, 1.25, 0])
        by_e = T("by event time: 100 every second", 24, GREEN_M).move_to([0, 0.55, 0])
        self.steps("Counted by processing time, that's a minute of zeros, then a spike of 2,000 a second that never happened. "
                   "Counted by event time, it's 100 every second.", [
            (lambda: [FadeOut(q), FadeIn(by_p, shift=0.15 * DOWN)], 0.9),
            "Counted by event time",
            (lambda: [FadeIn(by_e, shift=0.15 * DOWN)], 0.9),
        ])

        # ---- windows over event time ------------------------------------------------------------------------------
        wm = ValueTracker(-1)
        bonus = ValueTracker(0)
        axis = Line([ex(0), AX_Y, 0], [ex(180), AX_Y, 0], stroke_width=2, color=GREY_B)
        aticks = VGroup(*[Line([ex(s), AX_Y - 0.08, 0], [ex(s), AX_Y + 0.08, 0], stroke_width=2, color=GREY_B) for s in (0, 60, 120, 180)])
        ax_l = T("event time", 20, GREY_B)
        ax_l.move_to([ex(0) + ax_l.width / 2, AX_Y - 0.5, 0])
        boxes = [win_box(i) for i in range(3)]
        titles = [win_title(i) for i in range(3)]
        stats = [win_status(0, "open"), win_status(1, "not started", GREY_D), win_status(2, "not started", GREY_D)]

        def count(i):
            n = int(min(60, max(0, np.floor(wm.get_value()) - 60 * i + 1)))
            if i == 0:
                n += int(round(bonus.get_value()))
            return n

        counts = [always_redraw(lambda i=i: T(str(count(i)), 40, WHITE if count(i) else GREY_D).move_to([ex(60 * i + 30), WIN_Y, 0]))
                  for i in range(3)]
        rug = always_redraw(lambda: VGroup(*[Line([ex(s), AX_Y + 0.04, 0], [ex(s), AX_Y + 0.18, 0], stroke_width=1.6, color=S_C)
                                             for s in range(0, int(np.floor(wm.get_value())) + 1)]))
        self.steps("So count by event time. Each one-minute window collects the events that happened inside it, whenever they arrive. "
                   "Here, one event a second.", [
            (lambda: [FadeOut(by_p), FadeOut(by_e), Create(axis), FadeIn(aticks), FadeIn(ax_l)], 0.9),
            "Each one-minute window",
            (lambda: [*[FadeIn(b) for b in boxes], *[FadeIn(t) for t in titles], *[FadeIn(c) for c in counts], *[FadeIn(s) for s in stats]], 1.0),
            "Here, one event",
            (lambda: [self.add(rug) and Wait(0.02)], 0.02),
            (lambda: [wm.animate(rate_func=linear).set_value(59), LaggedStart(*[travel(pipe, S_C, 0.6) for _ in range(5)], lag_ratio=0.35)], 2.6),
        ])

        self.steps("But when is a window finished? An event from 59 seconds can still show up after one from 65.", [
            (lambda: [Indicate(stats[0], color=YELLOW_M)], 1.0),
        ])

        mark = always_redraw(lambda: Triangle(fill_color=W_C, fill_opacity=1, stroke_width=0).scale(0.12)
                             .move_to([ex(wm.get_value()), AX_Y - 0.24, 0]))
        mark_l = always_redraw(lambda: T(f"watermark {int(round(wm.get_value()))} s", 22, W_C)
                               .next_to([ex(wm.get_value()) + 0.05, AX_Y - 0.5, 0], RIGHT, buff=0.0))
        self.steps("A watermark answers that. It's the latest event time seen so far, and it claims that nothing earlier is still coming.", [
            (lambda: [FadeIn(mark), FadeIn(mark_l)], 0.9),
            "nothing earlier",
            (lambda: [Indicate(mark_l, color=W_C)], 1.0),
        ])

        grace = ValueTracker(10)
        band = always_redraw(lambda: Rectangle(width=max(0.01, ex(wm.get_value()) - ex(wm.get_value() - grace.get_value())), height=0.14,
                                               stroke_width=0).set_fill(W_C, 0.45)
                             .move_to([ex(wm.get_value()), AX_Y, 0], aligned_edge=RIGHT))
        band_l = always_redraw(lambda: T(f"grace {int(round(grace.get_value()))} s", 22, GREY_B)
                               .next_to([ex(wm.get_value() - grace.get_value()) - 0.1, AX_Y - 0.5, 0], LEFT, buff=0.0))
        self.steps("That's a guess, so each window also waits a grace period, here 10 seconds. "
                   "It closes when the watermark passes its end plus 10.", [
            "a grace period",
            (lambda: [FadeIn(band), FadeIn(band_l)], 0.9),
            "It closes",
            (lambda: [glow(boxes[0], YELLOW_M, 1.02)], 1.0),
        ])

        s59 = event_chip("happened at 59 s", GOLD_M).move_to([-3.2, LANE_Y, 0])
        tick59 = Line([ex(59), AX_Y + 0.04, 0], [ex(59), AX_Y + 0.2, 0], stroke_width=3, color=GOLD_M)
        st1 = win_status(1, "open")
        self.steps("The watermark reaches 65. Now a straggler arrives that happened at 59 seconds. Its window is still open, so it counts: 61.", [
            (lambda: [wm.animate(rate_func=linear).set_value(65), Transform(stats[1], st1)], 1.2),
            "Now a straggler",
            (lambda: [FadeIn(s59)], 0.3),
            (lambda: [s59.animate.move_to([3.2, LANE_Y, 0])], 1.0),
            (lambda: [s59.animate.move_to([ex(59), 1.35, 0])], 0.9),
            "so it counts",
            (lambda: [FadeOut(s59, shift=0.4 * DOWN), Create(tick59), bonus.animate.set_value(1)], 0.7),
        ])

        sent = chip("sent: 0 to 60 s = 61", GREEN_M, 22).move_to([-3.4, BOT, 0])
        st0 = win_status(0, "closed, sent once", GREEN_M)
        self.steps("At 70, the window's end plus its grace, it closes. Its count, 61, goes out once, and its state is dropped.", [
            (lambda: [wm.animate(rate_func=linear).set_value(70)], 1.0),
            "it closes",
            (lambda: [Transform(stats[0], st0), boxes[0].animate.set_stroke(GREY_D)], 0.7),
            "goes out once",
            (lambda: [FadeIn(sent, shift=0.15 * DOWN)], 0.8),
        ])

        st1b = win_status(1, "closed, sent once", GREEN_M)
        st2 = win_status(2, "open")
        sent2 = chip("sent: 60 to 120 s = 60", GREEN_M, 22).move_to([-3.4, BOT, 0])
        self.steps("The next window closes the same way, at 130, with 60 events.", [
            (lambda: [wm.animate(rate_func=linear).set_value(130), Transform(stats[2], st2)], 1.8),
            (lambda: [Transform(stats[1], st1b), boxes[1].animate.set_stroke(GREY_D), Transform(sent, sent2)], 0.8),
        ])

        s100 = event_chip("happened at 100 s", RED_M).move_to([-3.2, LANE_Y, 0])
        late = chip("dropped as late: 1", RED_M, 22).move_to([3.4, BOT, 0])
        no = tick(False, 0.2).move_to([ex(100), 1.35, 0])
        self.steps("At 150, an event from 100 seconds arrives. Its window is gone, so the event is dropped as late, and the late counter goes up.", [
            (lambda: [wm.animate(rate_func=linear).set_value(150)], 1.0),
            "an event from",
            (lambda: [FadeIn(s100)], 0.3),
            (lambda: [s100.animate.move_to([3.2, LANE_Y, 0])], 0.9),
            (lambda: [s100.animate.move_to([ex(100), 1.35, 0])], 0.8),
            "Its window is gone",
            (lambda: [Indicate(stats[1], color=RED_M)], 0.8),
            "dropped as late",
            (lambda: [FadeOut(s100), Create(no), FadeIn(late, shift=0.15 * DOWN)], 0.8),
        ])

        self.steps("A 60 second grace would have kept it, but every window would then report a minute later.", [
            (lambda: [grace.animate.set_value(60)], 1.4),
            "but every",
            (lambda: [Indicate(sent, color=YELLOW_M)], 1.0),
        ])

        self.steps("Choosing the grace period is choosing between late results and lost events.", [
            (lambda: [grace.animate.set_value(10)], 1.0),
            "late results",
            (lambda: [Indicate(sent, color=YELLOW_M)], 0.8),
            "lost events",
            (lambda: [Indicate(late, color=RED_M)], 0.8),
        ])
        self.wait(0.6)
