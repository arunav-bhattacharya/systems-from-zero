from sfz import *

SAY.insert(0, (r"\bm-7\b", "M 7"))
SAY.insert(0, (r"\bredeploy\b", "re-deploy"))
SAY.insert(0, (r"\b61 goes out\b", "sixty-one goes out"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
AX_Y, AX_X0, AX_X1, T_MAX = -0.9, -6.0, 6.0, 180
WIN_Y, WIN_H = 0.25, 1.6
WM_TOP, WM_LAB_Y, GR_LAB_Y, ST_Y = 1.45, 2.0, 1.62, 2.8
EMIT_C, DROP_C = np.array([-3.3, -2.15, 0]), np.array([3.6, -2.15, 0])
CAP_Y, TOP_Y, BAR_Y = -3.3, 3.3, -2.72
GRACE = 10


def X(t):
    return AX_X0 + (AX_X1 - AX_X0) * t / T_MAX


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def top(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, TOP_Y, 0])
        old, self.topm = self.topm, new
        return [swap(old, new)]

    def untop(self):
        old, self.topm = self.topm, None
        return [FadeOut(old)] if old is not None else []


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])




def win_box(k):
    x0, x1 = X(60 * k) + 0.06, X(60 * (k + 1)) - 0.06
    r = RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=WIN_H, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M), 1)
    r.move_to([(x0 + x1) / 2, WIN_Y, 0])
    t = T(f"{60 * k} to {60 * (k + 1)} s", 22, GREY_B).move_to([(x0 + x1) / 2, WIN_Y + WIN_H / 2 - 0.3, 0])
    return VGroup(r, t).set_z_index(2)


def win_text(k, s, color=WHITE, size=30):
    return T(s, size, color).move_to([X(60 * k + 30), WIN_Y - 0.25, 0]).set_z_index(3)


def axis():
    line = Line([AX_X0, AX_Y, 0], [AX_X1, AX_Y, 0], stroke_width=3, color=GREY_B)
    ticks = VGroup(*[Line([X(t), AX_Y - 0.1, 0], [X(t), AX_Y + 0.1, 0], stroke_width=3, color=GREY_B) for t in (0, 60, 120, 180)])
    labs = VGroup(*[T(f"{t} s", 20, GREY_B).move_to([X(t), AX_Y - 0.38, 0]) for t in (0, 60, 120, 180)])
    return VGroup(line, ticks, labs)


def seen_bar(t, color=YELLOW_M):
    """The events seen so far: one a second, drawn as a strip along the axis up to event time t."""
    t = max(t, 0.5)
    return Line([X(0), AX_Y + 0.17, 0], [X(t), AX_Y + 0.17, 0], stroke_width=6, color=color)


def run(arrow, color=YELLOW_M, rt=0.6):
    return travel(arrow, color, rt)


def postcard(mark, x, y, color=WHITE):
    r = RoundedRectangle(corner_radius=0.06, width=1.9, height=1.25, stroke_color=color, stroke_width=2.5).set_fill("#101214", 1).move_to([x, y, 0])
    stamp = Circle(radius=0.3, stroke_color=color, stroke_width=2).move_to([x + 0.5, y + 0.2, 0])
    m = T(mark, 20, color).move_to([x - 0.2, y - 0.3, 0])
    return VGroup(r, stamp, m)


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.7, height=2.9, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.4, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.1, 1.5)
    rows = VGroup()
    cw = M("x" * 40, 17).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if "//" in s else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 17, col), x - 3.1 + ind, 0.95 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["payments.groupByKey()",
        "    .windowedBy(TimeWindows.ofSizeAndGrace(",
        "        Duration.ofMinutes(1),",
        "        Duration.ofSeconds(10)))  // grace",
        "    .count();"]
KOTLIN = ["payments.groupByKey()",
          "    .windowedBy(TimeWindows.ofSizeAndGrace(",
          "        Duration.ofMinutes(1),",
          "        Duration.ofSeconds(10)))  // grace",
          "    .count()"]


class Watermarks(Base):
    """stream-04, section 2. Per-minute counts for shop m-7, one payment a second. Closing windows by the program's
    clock plus 10 s breaks at a 60 s redeploy (a window closes with 0 before the backlog is read). Two clocks; the
    postcards: add up July once the latest postmark minus a few days passes the end of July. The watermark (stream
    time, the largest event time seen) and a 10 s grace: the straggler from 59 s read at 65 s is counted (61), the window
    is final at 70 s; a payment from 100 s read at 150 s is dropped as late. Predict with 60 s grace: one of three
    stragglers dropped, and every result waits a minute. Too fast, too slow. Kafka Streams in Java and Kotlin, the
    moral, a check."""

    def construct(self):
        self.capm = self.topm = None
        self.title_card("When is a minute's count final?", "event time, watermarks and grace")

        ax = axis()
        ax_l = T("the program's clock", 22, GREY_B).move_to([X(150), AX_Y - 0.75, 0])
        wins = [win_box(k) for k in range(3)]
        self.wt = [None, None, None]
        self.bar = None
        self.wm = None
        self.drop = None
        self.emit = None

        def set_wt(k, s, color=WHITE, size=30):
            new = win_text(k, s, color, size)
            old, self.wt[k] = self.wt[k], new
            return [swap(old, new)]

        def set_bar(t, color=YELLOW_M):
            new = seen_bar(t, color)
            old, self.bar = self.bar, new
            if old is None:
                return [Create(new)]
            return [FadeOut(old, run_time=0.01), Create(new)]

        def wm_group(t, label="watermark", grace=True):
            g = VGroup(Line([X(t), AX_Y, 0], [X(t), WM_TOP, 0], stroke_width=4, color=YELLOW_M),
                       T(f"{label} {t} s", 22, YELLOW_M).move_to([X(t), WM_LAB_Y, 0]))
            if grace:
                g.add(DashedLine([X(t - GRACE), AX_Y, 0], [X(t - GRACE), WM_TOP - 0.45, 0], stroke_width=3, color=GREY_B, dash_length=0.08))
                g.add(T("minus 10 s grace", 18, GREY_B).move_to([X(t - GRACE) - 1.0, GR_LAB_Y - 0.25, 0]))
            return g

        def set_wm(t, label="watermark", grace=True):
            new = wm_group(t, label, grace)
            old, self.wm = self.wm, new
            if old is None:
                return [FadeIn(new)]
            return [ReplacementTransform(old, new)]

        def set_drop(n, color=GREY_B):
            new = T(f"dropped as late: {n}", 22, color).move_to(DROP_C)
            old, self.drop = self.drop, new
            return [swap(old, new)]

        def set_emit(s, color=GREEN_M):
            new = T(s, 22, color).move_to(EMIT_C)
            old, self.emit = self.emit, new
            return [swap(old, new)]

        def clear(attr):
            old = getattr(self, attr)
            setattr(self, attr, None)
            return [FadeOut(old)] if old is not None else []

        # ---------------- scene 1: the question ----------------
        self.steps("A café chain's card payments flow into Kafka, a program that keeps a log of messages for other programs to read. "
                   "A counting program reads them, and counts the payments per minute for one shop, m-7.", [
            "A counting program",
            (lambda: [Create(ax), FadeIn(ax_l)], 0.9),
            "counts the payments",
            (lambda: [LaggedStart(*[FadeIn(w) for w in wins], lag_ratio=0.3)], 1.0),
        ])
        self.steps("One payment a second, so every minute should say sixty. The question is when to say it. "
                   "When is the minute from 0 to 60 seconds complete?", [
            "One payment",
            (lambda: [*set_bar(60), *set_wt(0, "60")], 1.2),
            "When is the minute",
            (lambda: [*self.top("when is the window 0 to 60 s complete?", WHITE, 28), glow(wins[0][0], BLUE_M, 1.03)], 0.8),
        ], after=0.4)

        # ---------------- scene 2: by the program's clock ----------------
        stop = Rectangle(width=X(120) - X(60), height=0.5, stroke_width=0).set_fill(GREY_D, 0.6).move_to([X(90), AX_Y + 0.17, 0])
        stop_l = T("stopped: redeploy", 20, GREY_B).move_to([X(90), AX_Y - 0.75, 0])
        pile = VGroup(*[Dot(radius=0.06, color=RED_M).move_to([X(122) + 0.14 * i, AX_Y + 0.17, 0]) for i in range(14)])
        self.steps("The simple answer is the program's own clock. When it passes the minute's end, wait 10 more seconds for stragglers, "
                   "then send out the count. A straggler is an event that arrives later than its neighbours.", [
            (lambda: self.untop(), 0.3),
            "When it passes",
            (lambda: set_wm(70, "clock", grace=False), 0.8),
            "then send out",
            (lambda: [*set_wt(0, "sent: 60", GREEN_M), *self.cap("by the clock: the minute's end, plus 10 s")], 0.6),
            "A straggler is",
            (lambda: self.cap("a straggler: an event that arrives later than its neighbours"), 0.5),
        ])
        self.steps("That works until the first redeploy. Stop the program for sixty seconds to install a new version. "
                   "When it comes back, its clock says that minute is over, so the window closes before it reads a single waiting payment.", [
            (lambda: self.uncap(), 0.3),
            "Stop the program",
            (lambda: [FadeIn(stop), FadeIn(stop_l), FadeOut(ax_l)], 0.7),
            "When it comes back",
            (lambda: set_wm(130, "clock", grace=False), 0.8),
            "the window closes",
            (lambda: [*set_wt(1, "sent: 0", RED_M), wins[1][0].animate.set_stroke(RED_M)], 0.6),
            "a single waiting",
            (lambda: [LaggedStart(*[FadeIn(d, shift=0.2 * DOWN) for d in pile], lag_ratio=0.05)], 1.0),
        ])
        self.steps("The count goes out as zero, and the real payments arrive to find their window gone. "
                   "A zero, sent with total confidence.", [
            "find their window",
            (lambda: [Indicate(pile, color=RED_M, scale_factor=1.1)], 0.8),
            "A zero",
            (lambda: [Indicate(self.wt[1], color=RED_M, scale_factor=1.2)], 0.8),
        ], after=0.4)

        # ---------------- scene 3: two clocks ----------------
        self.steps("The trouble is mixing two clocks. Event time is when the payment happened, stamped by the till. "
                   "Processing time is when our program reads it.", [
            "Event time is",
            (lambda: self.cap("event time: when it happened, stamped by the till", WHITE), 0.6),
            "Processing time",
            (lambda: self.cap("processing time: when the program reads it"), 0.6),
        ])
        diagram = VGroup(ax, *wins, stop, stop_l, pile)
        cards = [postcard("30 July", -4.8, 0.6), postcard("31 July", -2.4, 0.6), postcard("2 August", 0.0, 0.6),
                 postcard("31 July", 2.4, 0.6, GOLD_M), postcard("4 August", 4.8, 0.6)]
        rule = T("latest postmark, minus a few days", 26, YELLOW_M).move_to([0, 2.4, 0])
        self.steps("A friend on holiday sends you a postcard a day, and you want to add up July. The post is slow, and sometimes jumbled.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.04), *clear("wm"), *clear("bar"), *self._clear_wt()], 0.6),
            "a postcard a day",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.2 * DOWN) for c in cards[:3]], lag_ratio=0.3)], 1.0),
            "sometimes jumbled",
            (lambda: [FadeIn(cards[3], shift=0.2 * DOWN)], 0.5),
        ])
        self.steps("So when do you add up July? Not when your calendar says August. When the latest postmark you've received "
                   "passes the end of July, minus a few days for slow post.", [
            "When the latest",
            (lambda: [FadeIn(rule)], 0.5),
            (lambda: [glow(cards[2][0], YELLOW_M, 1.04)], 0.7),
            "minus a few days",
            (lambda: [FadeIn(cards[4], shift=0.2 * DOWN), *self.cap("4 August, minus three days, is past July: add up July")], 0.7),
        ])
        self.steps("Map it. The postmark is event time. The latest postmark is how far the stream has got. "
                   "The few days are your allowance for stragglers. And adding up July is closing the window.", [
            "The postmark is",
            (lambda: [*self.cap("postmark = event time", WHITE), *[Indicate(c[2], color=WHITE, scale_factor=1.1) for c in cards]], 0.7),
            "The latest postmark",
            (lambda: [*self.cap("latest postmark = how far the stream has got", YELLOW_M), glow(cards[4][0], YELLOW_M, 1.04)], 0.7),
            "The few days",
            (lambda: self.cap("a few days = the allowance for stragglers"), 0.5),
            "And adding up",
            (lambda: self.cap("adding up July = closing the window", GREEN_M), 0.5),
        ])

        # ---------------- scene 4: the watermark ----------------
        self.steps("That latest postmark is called a watermark: the program's running claim, I believe no more events "
                   "older than this will arrive.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*cards)), FadeOut(rule), FadeOut(VGroup(stop, stop_l, pile)), ax.animate.set_opacity(1),
                      *[w.animate.set_opacity(1) for w in wins]], 0.8),
            "called a watermark",
            (lambda: [wins[1][0].animate.set_stroke(BLUE_M), *self.top("watermark: “no more events older than this will arrive”", YELLOW_M, 26)], 0.6),
        ])
        ax_l2 = T("event time", 22, GREY_B).move_to([X(150), AX_Y - 0.75, 0])
        self.steps("Kafka Streams, a library for writing such counting programs, uses the largest event time seen so far, "
                   "and gives each window a grace period on top. When the watermark passes a window's end plus its grace, "
                   "the window is final, and its count goes out. Sending it on is called emitting.", [
            "Kafka Streams",
            (lambda: [FadeIn(ax_l2)], 0.5),
            "the largest event time",
            (lambda: [*set_bar(59), *set_wm(59), *set_wt(0, "count 60")], 0.9),
            "a grace period",
            (lambda: [*self.cap("grace here: 10 s")], 0.5),
            "Sending it on",
            (lambda: self.cap("emitting: sending a final count on"), 0.5),
        ])

        # ---------------- scene 5: the walkthrough ----------------
        st = T("read at 65 s, happened at 59 s", 22, GOLD_M).move_to([X(62), ST_Y, 0])
        sd = Dot(radius=0.1, color=GOLD_M).set_z_index(4).move_to([X(59), ST_Y - 0.38, 0])
        self.stamp("walk")
        self.steps("Watch it with 10 seconds of grace. At 65 seconds, a straggler arrives that happened at 59. "
                   "Its window is still open, until 60 plus 10. So it's counted: 61.", [
            (lambda: [*self.uncap(), *self.untop(), *set_drop(0), *set_emit("emitted: nothing yet", GREY_B)], 0.5),
            "At 65",
            (lambda: [*set_bar(65), *set_wm(65), *set_wt(1, "count 6")], 0.8),
            "a straggler",
            (lambda: [FadeIn(st), FadeIn(sd)], 0.5),
            "Its window",
            (lambda: [sd.animate.move_to([X(59), AX_Y + 0.17, 0])], 0.6),
            "counted",
            (lambda: [FadeOut(sd), *set_wt(0, "count 61", GOLD_M)], 0.5),
        ])
        self.steps("At 70, the window is final. 61 goes out, once, and the program forgets it. That wait is the price: "
                   "every result comes out 10 seconds later.", [
            (lambda: [FadeOut(st), *set_bar(70), *set_wm(70), *set_wt(1, "count 11")], 0.7),
            "the window is final",
            (lambda: [*set_wt(0, "final: 61", GREEN_M), wins[0][0].animate.set_stroke(GREEN_M)], 0.5),
            "61 goes out",
            (lambda: set_emit("emitted: 0 to 60 s = 61"), 0.5),
            "That wait",
            (lambda: self.cap("the price of grace: every result waits 10 s longer"), 0.5),
        ])
        self.stamp("poster")
        st2 = T("read at 150 s, happened at 100 s", 22, RED_M).move_to([X(115), ST_Y, 0])
        sd2 = Dot(radius=0.1, color=RED_M).set_z_index(4).move_to([X(100), ST_Y - 0.38, 0])
        self.steps("The second window closes at 130, with 60. Then, at 150, a payment from 100 seconds arrives. Its window is gone, "
                   "and its count is out. So it's dropped as late, and the late counter goes up.", [
            (lambda: [*self.uncap(), *set_bar(130), *set_wm(130), *set_wt(1, "final: 60", GREEN_M), wins[1][0].animate.set_stroke(GREEN_M),
                      *set_wt(2, "count 11")], 0.8),
            "Then, at 150",
            (lambda: [*set_bar(150), *set_wm(150), *set_wt(2, "count 31"), FadeIn(st2), FadeIn(sd2)], 0.8),
            "Its window is gone",
            (lambda: [sd2.animate.move_to([X(100), WIN_Y + WIN_H / 2 + 0.05, 0])], 0.5),
            "dropped as late",
            (lambda: [sd2.animate.set_opacity(0).shift(0.4 * UP), *set_drop(1, RED_M)], 0.5),
        ])

        # ---------------- scene 6: predict the grace ----------------
        self.steps("Here's the lesson's test. Three stragglers arrive 5, 30 and 90 seconds after their windows end. "
                   "With 10 seconds of grace, two are dropped. With 60 seconds of grace, how many? Pause and guess.", [
            (lambda: [FadeOut(st2), *self.cap("stragglers 5 s, 30 s and 90 s past their windows")], 0.5),
            "With 10 seconds",
            (lambda: self.cap("grace 10 s: 2 dropped"), 0.5),
            "how many",
            (lambda: self.cap("grace 60 s: how many dropped? pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("One. Only the one 90 seconds late. But now every window waits a whole minute before its count goes out. "
                   "More grace keeps more stragglers, and delays every result by the same amount.", [
            (lambda: self.cap("grace 60 s: 1 dropped, and every result a minute late", WHITE), 0.6),
            "More grace",
            (lambda: self.cap("more grace: fewer drops, later results", YELLOW_M), 0.5),
        ], after=0.4)

        # ---------------- scene 7: a guess, wrong two ways ----------------
        self.steps("Remember, a watermark is a guess, and it can be wrong two ways. Too fast: an older event still arrives, "
                   "from a phone that was offline. That's a late event.", [
            "Too fast",
            (lambda: [*self.cap("too fast: older events still arrive (late events)", RED_M), Indicate(self.drop, color=RED_M)], 0.7),
        ])
        self.steps("Too slow: Flink, another engine, reads several inputs and takes the smallest of their watermarks. "
                   "One quiet input holds every window open.", [
            "Too slow",
            (lambda: self.cap("too slow: one quiet input holds every window open", GOLD_M), 0.6),
            "holds every window",
            (lambda: [LaggedStart(*[glow(w[0], GOLD_M, 1.02) for w in wins], lag_ratio=0.2)], 1.0),
        ])
        self.steps("It's like refusing to add up July until every friend has sent a card, including the one who never writes. "
                   "So you mark a quiet input as idle, and it stops holding things back.", [
            "So you mark",
            (lambda: self.cap("mark a quiet input as idle", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 8: the code, the moral, a check ----------------
        diag2 = VGroup(ax, ax_l2, *wins, *[w for w in self.wt if w is not None], self.bar, self.wm, self.drop, self.emit)
        jp, kp = code_panel("Java", JAVA, -3.45), code_panel("Kotlin", KOTLIN, 3.45)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Kafka Streams, in Java and Kotlin, it's one line: one-minute windows, with 10 seconds of grace.", [
            (lambda: [*self.uncap(), diag2.animate.set_opacity(0.04)], 0.5),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.6),
            "one-minute windows",
            (lambda: hl((2,), BLUE_M), 0.9),
            "10 seconds of grace",
            (lambda: hl((3,), YELLOW_M), 0.9),
        ], after=1.0)
        self.steps("So count by the postmark, not by the letterbox. The watermark says when a count is final, "
                   "and the grace says how long you wait for stragglers.", [
            (lambda: [FadeOut(jp), FadeOut(kp), diag2.animate.set_opacity(1)], 0.7),
            (lambda: self.cap("count by the postmark, not the letterbox", YELLOW_M, 30), 0.6),
        ], after=0.5)
        sd3 = Dot(radius=0.1, color=GOLD_M).set_z_index(4).move_to([X(115), ST_Y - 0.38, 0])
        st3 = T("happened at 115 s", 22, GOLD_M).move_to([X(115), ST_Y, 0])
        self.steps("One quick check. Grace is 10 seconds, and the watermark is at 125. A payment from 115 seconds arrives. "
                   "Counted, or dropped? Pause and think.", [
            (lambda: [*self.uncap(), *clear("emit"), *set_drop(0), *set_bar(125), *set_wm(125), *set_wt(1, "count 60"),
                      wins[1][0].animate.set_stroke(BLUE_M), *set_wt(2, "count 6")], 0.8),
            "A payment from",
            (lambda: [FadeIn(st3), FadeIn(sd3)], 0.5),
            "Pause and think",
            (lambda: self.cap("counted, or dropped? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Counted. Its window, 60 to 120, stays open until 130.", [
            (lambda: [*self.uncap(), sd3.animate.move_to([X(115), AX_Y + 0.17, 0])], 0.6),
            (lambda: [FadeOut(sd3), FadeOut(st3), *set_wt(1, "count 61", GOLD_M)], 0.5),
            "stays open",
            (lambda: [glow(wins[1][0], GREEN_M, 1.03), *self.cap("count by the postmark, not the letterbox", YELLOW_M, 30)], 0.8),
        ], after=0.3)
        self.play(Create(tick(True, 0.2).move_to([X(90), WIN_Y + WIN_H / 2 + 0.35, 0])), run_time=0.6)
        self.wait(2.0)

    def _clear_wt(self):
        out = []
        for k in range(3):
            if self.wt[k] is not None:
                out.append(FadeOut(self.wt[k]))
                self.wt[k] = None
        return out
