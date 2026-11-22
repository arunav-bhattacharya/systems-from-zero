from sfz import *

SAY.insert(0, (r"\bNTP\b", "N T P"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
LANE_Y = [2.1, 0.5, -1.1]            # three timelines: friends first, then nodes
LINE_X0, LINE_X1 = -4.3, 4.75
LAB_X = -6.45
CNT_X = 5.6                           # the counter (tally) box at the end of each lane
CAP_Y, BAR_Y, LIST_Y = -3.1, -2.55, -2.2
SCR_C, SCR_W, SCR_H = np.array([0.1, -1.75, 0]), 7.0, 1.55
LANE_C = [BLUE_M, GREEN_M, PURPLE_M]
R = 0.25

# the lesson's stepper, in scene x units (stepper px 100..620 -> -4.4..6.0)
def sx(px):
    return -4.4 + (px - 100) * 0.02


EVX = {("a", 1): sx(150), ("a", 2): sx(240),
       ("c", 1): sx(140), ("c", 3): sx(320), ("c", 4): sx(400),
       ("l", 1): sx(140), ("l", 2): sx(215), ("l", 3): sx(290), ("l", 4): sx(365), ("l", 5): sx(440), ("l", 6): sx(530)}
LANE = {"a": 0, "c": 1, "l": 2}


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        fit(new, 12.6)
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0, y=BAR_Y):
        bar = Line([-1.0, y, 0], [1.0, y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.06):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def lane_label(s, k):
    return left_at(T(s, 22, LANE_C[k]), LAB_X, LANE_Y[k])


def lane_line(k):
    return Line([LINE_X0, LANE_Y[k], 0], [LINE_X1, LANE_Y[k], 0], stroke_width=2.5, color=GREY_C)


def counter_box(k, val, color=WHITE):
    r = RoundedRectangle(corner_radius=0.1, width=1.1, height=0.62, stroke_color=LANE_C[k], stroke_width=2.5)
    r.set_fill(fillc(LANE_C[k]), 1).move_to([CNT_X, LANE_Y[k], 0])
    return VGroup(r, M(str(val), 26, color).move_to(r))


def ev(k, x, label, color=None, size=22):
    """An event on lane k: a filled circle with its stamp inside (or nothing, for a plain dot)."""
    c = color or LANE_C[k]
    circ = Circle(radius=R, stroke_color=c, stroke_width=3).set_fill(fillc(c, 0.3), 1).move_to([x, LANE_Y[k], 0])
    if label is None or label == "":
        return VGroup(circ)
    return VGroup(circ, M(str(label), size).move_to(circ))


def E(node, n, label=None):
    k = LANE[node]
    return ev(k, EVX[(node, n)], n if label is None else label)


def P(node, n):
    return np.array([EVX[(node, n)], LANE_Y[LANE[node]], 0])


def msg(pa, pb, color=GOLD_M):
    return Arrow(pa, pb, buff=R + 0.04, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12)


def screen_box(title):
    r = RoundedRectangle(corner_radius=0.14, width=SCR_W, height=SCR_H, stroke_color=GREY_B, stroke_width=2.5)
    r.set_fill("#101214", 1).move_to(SCR_C)
    t = left_at(T(title, 18, GREY_B), SCR_C[0] - SCR_W / 2 + 0.3, SCR_C[1] + SCR_H / 2 - 0.27)
    return VGroup(r, t)


def screen_row(i, who, text, stamp, color=WHITE, scolor=GREY_B):
    y = SCR_C[1] + 0.12 - 0.5 * i
    x0 = SCR_C[0] - SCR_W / 2 + 0.3
    g = VGroup(left_at(T(who, 22, GREY_B), x0, y), left_at(T(text, 24, color), x0 + 0.95, y))
    s = M(stamp, 22, scolor)
    g.add(s.move_to([SCR_C[0] + SCR_W / 2 - 0.3 - s.width / 2, y, 0]))
    return g


class LogicalClocks(Base):
    """dist-06, section 1. A group chat sorted by phone clocks shows the answer above its question; the same skew
    puts a payment's capture 35 ms before its approval. What we need is causes before effects, and a cause reaches
    an effect only along a node or along a message. The friends keep tallies instead (the analogy), then three nodes
    run Lamport's rule from the lesson's stepper (capture 1 -> 3, ledger 5 -> 6), the eleven stamps sort into one
    list, and (2,0) < (3,2) breaks the idea that a smaller stamp means earlier or a cause. Limits, moral, check."""

    def construct(self):
        self.capm = None
        self.title_card("Count, don't read the clock", "Lamport timestamps: every cause before its effect")

        # ---------------- scene 1: the chat ----------------
        labs = [lane_label("Ana's phone", 0), lane_label("Ben's phone", 1)]
        lines = [lane_line(0), lane_line(1)]
        scr = screen_box("the chat, sorted by phone time")
        self.steps("Picture a group chat that sorts messages by the time on the phone that sent each one.", [
            (lambda: [Create(lines[0]), Create(lines[1]), FadeIn(labs[0]), FadeIn(labs[1])], 1.0),
            "sorts messages",
            (lambda: [FadeIn(scr, shift=0.1 * UP)], 0.7),
        ])
        q = ev(0, -2.6, None)
        qlab = T("Dinner at eight?", 20).move_to([-2.6, LANE_Y[0] + 0.5, 0])
        qt = M("7:30", 20, GREY_B).move_to([-3.25, LANE_Y[0] - 0.42, 0])
        a_q = msg(q.get_center(), [-1.0, LANE_Y[1], 0])
        rd = ev(1, -1.0, None)
        an = ev(1, 0.7, None)
        anlab = T("Yes, see you there!", 20).move_to([0.7, LANE_Y[1] + 0.5, 0])
        ant = M("7:29", 20, RED_M).move_to([0.7, LANE_Y[1] - 0.5, 0])
        r1 = screen_row(0, "Ben", "Yes, see you there!", "7:29", WHITE, RED_M)
        r2 = screen_row(1, "Ana", "Dinner at eight?", "7:30")
        self.steps("Ana asks: dinner at eight? Ben answers: yes, see you there!", [
            (lambda: [FadeIn(q, scale=0.6), FadeIn(qlab, shift=0.1 * UP), FadeIn(qt)], 0.6),
            (lambda: [GrowArrow(a_q)], 0.6),
            (lambda: [FadeIn(rd, scale=0.6)], 0.3),
            "Ben answers",
            (lambda: [FadeIn(an, scale=0.6), FadeIn(anlab, shift=0.1 * UP)], 0.6),
        ])
        self.steps("But on the screen, the answer sits above the question. Ben's phone runs a minute slow, "
                   "so his answer got an earlier time than her question.", [
            (lambda: [FadeIn(r2, shift=0.1 * UP)], 0.4),
            (lambda: [FadeIn(r1, shift=0.1 * DOWN)], 0.5),
            "the answer sits",
            (lambda: [Indicate(r1[1], color=RED_M, scale_factor=1.08)], 0.8),
            "Ben's phone runs",
            (lambda: [FadeIn(ant, shift=0.1 * DOWN), *self.cap("Ben's phone clock: a minute slow", RED_M)], 0.6),
            "an earlier time",
            (lambda: [Indicate(ant, color=RED_M, scale_factor=1.2), Indicate(r1[2], color=RED_M, scale_factor=1.2)], 0.9),
        ])
        self.steps("So here's the real question. If no two clocks agree, how do you put things in the order they could really have happened?", [
            (lambda: self.cap("no two clocks agree: so how do we order events?", WHITE), 0.6),
        ])

        # ---------------- scene 2: the same bug, with money ----------------
        chat = VGroup(q, qlab, qt, a_q, rd, an, anlab, ant, r1, r2)
        nl0, nl1 = lane_label("auth", 0), lane_label("capture", 1)
        self.steps("In a chat, that's a funny moment. With money, it's a bug. Take a card payment in two steps, on two computers. "
                   "We'll call each computer a node.", [
            "With money",
            (lambda: [FadeOut(chat), FadeOut(scr), *self.uncap()], 0.6),
            "Take a card",
            (lambda: [swap(labs[0], nl0, RIGHT), swap(labs[1], nl1, RIGHT)], 0.8),
            "a node",
            (lambda: self.cap("node: one computer in a system of many"), 0.5),
        ])
        labs = [nl0, nl1]
        ap = ev(0, -2.6, None)
        aplab = T("approve pay-81723", 20).move_to([-2.6, LANE_Y[0] + 0.5, 0])
        cp_x = -2.6 + 0.9
        a_m = msg(ap.get_center(), [cp_x, LANE_Y[1], 0])
        cp = ev(1, cp_x, None)
        cplab = T("capture: move the money", 20).move_to([cp_x + 0.6, LANE_Y[1] - 0.5, 0])
        self.steps("Auth approves a payment and sends a message to capture, which moves the money 5 milliseconds later.", [
            (lambda: [*self.uncap(), FadeIn(ap, scale=0.6), FadeIn(aplab, shift=0.1 * UP)], 0.6),
            "sends a message",
            (lambda: [GrowArrow(a_m)], 0.6),
            "which moves",
            (lambda: [FadeIn(cp, scale=0.6), FadeIn(cplab, shift=0.1 * DOWN)], 0.6),
            "5 milliseconds",
            (lambda: self.cap("real time: 10:00:00.100, then 10:00:00.105"), 0.5),
        ])
        st_a = M("stamp 10:00:00.140", 20, GOLD_M).move_to([-2.6 + 3.0, LANE_Y[0] + 0.5, 0])
        st_c = M("stamp 10:00:00.105", 20, GOLD_M).move_to([cp_x + 3.6, LANE_Y[1] + 0.5, 0])
        self.steps("Auth's clock runs 40 milliseconds ahead. So the approval is stamped a hundred and forty milliseconds past ten, "
                   "and the capture a hundred and five.", [
            (lambda: self.cap("auth's clock: 40 ms ahead", GOLD_M), 0.5),
            "So the approval",
            (lambda: [FadeIn(st_a, shift=0.1 * LEFT)], 0.6),
            "and the capture",
            (lambda: [FadeIn(st_c, shift=0.1 * LEFT)], 0.6),
        ])
        scr2 = screen_box("sorted by stamp")
        s1 = screen_row(0, "1st", "capture: move the money", ".105", RED_M, RED_M)
        s2 = screen_row(1, "2nd", "approve pay-81723", ".140")
        self.steps("Sort by those stamps, and the money moves 35 milliseconds before the payment was even approved.", [
            (lambda: [*self.uncap(), FadeIn(scr2, shift=0.1 * UP)], 0.5),
            (lambda: [FadeIn(s1, shift=0.1 * DOWN), FadeIn(s2, shift=0.1 * DOWN)], 0.6),
            "35 milliseconds",
            (lambda: [Indicate(s1[1], color=RED_M, scale_factor=1.06), *self.cap("the effect sorts 35 ms before its cause", RED_M)], 0.9),
        ])
        self.steps("The obvious fix is better clocks. But NTP, the service that keeps computer clocks close to the right time, "
                   "can easily leave 40 milliseconds between two servers. And a message often takes less than that.", [
            (lambda: self.cap("fix the clocks?", PURPLE_M), 0.5),
            "can easily leave",
            (lambda: self.cap("NTP: clocks close, never equal.   gap: 40 ms", WHITE), 0.5),
            "And a message",
            (lambda: [Indicate(a_m, color=GOLD_M), *self.cap("clock gap 40 ms  >  message trip 5 ms", RED_M)], 0.9),
        ])
        self.steps("Whenever the gap between two clocks is bigger than the trip, sorting by time can flip a cause and its effect. "
                   "Wouldn't it be nice to have an order that stays right, whatever the clocks say?", [
            "Wouldn't it",
            (lambda: self.cap("wish: an order that stays right, whatever the clocks say", YELLOW_M), 0.6),
        ])

        # ---------------- scene 3: what order we need ----------------
        cp2 = ev(1, 0.9, None)
        seg = Line([cp_x + R, LANE_Y[1], 0], [0.9 - R, LANE_Y[1], 0], stroke_width=9, color=YELLOW_M).set_opacity(0.6)
        self.steps("So what order do we actually need? Not the time of day. Causes before their effects.", [
            (lambda: [FadeOut(VGroup(scr2, s1, s2, st_a, st_c)), *self.uncap()], 0.6),
            "Causes before",
            (lambda: self.cap("causes before their effects", WHITE), 0.5),
        ])
        self.steps("And a cause can reach an effect in only two ways. Along one node's own events, one after another. "
                   "Or along a message, from the send to its arrival.", [
            "Along one node",
            (lambda: [FadeIn(cp2, scale=0.6)], 0.4),
            (lambda: [Create(seg)], 0.6),
            (lambda: [*self.cap("1. along one node, one event after another", YELLOW_M)], 0.4),
            "Or along a message",
            (lambda: [a_m.animate.set_color(YELLOW_M).set_stroke(width=6), *self.cap("2. along a message, from send to arrival", YELLOW_M)], 0.6),
        ])
        self.steps("So if a stamp only ever grows along both, an effect can never get a smaller stamp than its cause.", [
            (lambda: self.cap("a stamp that grows along both: effect > cause, always", WHITE), 0.6),
        ], after=0.5)

        # ---------------- scene 4: the friends' tallies ----------------
        fl0, fl1 = lane_label("Ana", 0), lane_label("Ben", 1)
        hdr = T("tally", 20, GREY_B).move_to([CNT_X, LANE_Y[0] + 0.62, 0])
        tal = [counter_box(0, 0), counter_box(1, 0)]
        self.steps("People can do this with no clock at all. Back to the chat. Ana and Ben stop trusting their phones, "
                   "and each keeps a tally instead, a number on a notepad.", [
            (lambda: [FadeOut(VGroup(ap, aplab, a_m, cp, cplab, cp2, seg)), *self.uncap()], 0.6),
            "Back to the chat",
            (lambda: [swap(labs[0], fl0, LEFT), swap(labs[1], fl1, LEFT)], 0.8),
            "each keeps a tally",
            (lambda: [FadeIn(hdr), FadeIn(tal[0], shift=0.1 * LEFT), FadeIn(tal[1], shift=0.1 * LEFT)], 0.7),
        ])
        labs = [fl0, fl1]

        def set_tal(k, val, color=WHITE):
            new = M(str(val), 26, color).move_to(tal[k][0])
            return [Transform(tal[k][1], new), tal[k][0].animate.set_stroke(YELLOW_M)]

        q1 = ev(0, -2.6, 1)
        q1lab = T("question", 20, GREY_B).move_to([-2.6, LANE_Y[0] + 0.52, 0])
        m_q = msg(q1.get_center(), [-1.0, LANE_Y[1], 0])
        m_ql = T("carries 1", 20, GOLD_M).move_to([-1.25, 1.42, 0])
        self.steps("Before Ana sends anything, she adds one to her tally, and writes it on the message. Her question carries 1.", [
            "she adds one",
            (lambda: set_tal(0, 1), 0.5),
            "writes it",
            (lambda: [FadeIn(q1, scale=0.6), FadeIn(q1lab, shift=0.1 * UP)], 0.5),
            "Her question carries",
            (lambda: [GrowArrow(m_q), FadeIn(m_ql)], 0.6),
        ])
        b2 = ev(1, -1.0, 2)
        self.steps("When Ben reads a message, he looks at its number. He takes the bigger of his tally and the message's, and adds one. "
                   "His tally was 0, the message says 1, so the read becomes 2.", [
            (lambda: [tal[0][0].animate.set_stroke(LANE_C[0])], 0.3),
            "He takes the bigger",
            (lambda: self.cap("on reading: the bigger of the two, plus one", WHITE), 0.5),
            "His tally was 0",
            (lambda: [Indicate(tal[1][1], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "the message says 1",
            (lambda: [Indicate(m_ql, color=GOLD_M, scale_factor=1.15)], 0.6),
            "so the read",
            (lambda: [FadeIn(b2, scale=0.6), *set_tal(1, 2), *self.cap("bigger of 0 and 1, plus one: 2", WHITE)], 0.6),
        ])
        b3 = ev(1, 0.7, 3)
        b3lab = T("answer", 20, GREY_B).move_to([0.7, LANE_Y[1] + 0.52, 0])
        scr3 = screen_box("the chat, sorted by tally")
        t1 = screen_row(0, "Ana", "Dinner at eight?", "1", WHITE, GREEN_M)
        t2 = screen_row(1, "Ben", "Yes, see you there!", "3", WHITE, GREEN_M)
        self.steps("Then his answer carries 3. Sort by tally: question 1, answer 3. The right order, and nobody read a clock.", [
            (lambda: [FadeIn(b3, scale=0.6), FadeIn(b3lab, shift=0.1 * UP), *set_tal(1, 3), *self.uncap()], 0.6),
            "Sort by tally",
            (lambda: [FadeIn(scr3, shift=0.1 * UP)], 0.5),
            (lambda: [FadeIn(t1, shift=0.1 * DOWN), FadeIn(t2, shift=0.1 * DOWN)], 0.6),
            "The right order",
            (lambda: [Indicate(t1[2], color=GREEN_M, scale_factor=1.3), Indicate(t2[2], color=GREEN_M, scale_factor=1.3)], 0.8),
        ])
        self.steps("Ben's phone can stay a minute slow forever. Nobody asks it any more.", [
            (lambda: [tal[1][0].animate.set_stroke(LANE_C[1])], 0.4),
        ], after=0.4)
        self.steps("Let's map it. Each friend is a node. The tally is a counter. The number on the message is the stamp it carries. "
                   "And the bigger of the two, plus one, is the jump past the message.", [
            "Each friend",
            (lambda: [Indicate(labs[0], color=BLUE_M), Indicate(labs[1], color=GREEN_M), *self.cap("friend  =  node")], 0.6),
            "The tally",
            (lambda: [glow(tal[0][0], YELLOW_M), glow(tal[1][0], YELLOW_M), *self.cap("tally  =  counter")], 0.6),
            "The number on",
            (lambda: [Indicate(m_ql, color=GOLD_M, scale_factor=1.15), *self.cap("number on the message  =  the stamp it carries")], 0.7),
            "And the bigger",
            (lambda: [Indicate(b2, color=YELLOW_M, scale_factor=1.2), *self.cap("bigger of the two, plus one  =  the jump past the message")], 0.7),
        ])

        # ---------------- scene 5: three nodes, the stepper ----------------
        n0, n1, n2 = lane_label("auth (0)", 0), lane_label("capture (1)", 1), lane_label("ledger (2)", 2)
        line2 = lane_line(2)
        hdr2 = T("counter", 20, GREY_B).move_to(hdr)
        tal.append(counter_box(2, 0))
        self.steps("Now three nodes. Auth approves payments, capture moves the money, and the ledger keeps the balances. "
                   "Each counts its own events, starting at 1.", [
            (lambda: [FadeOut(VGroup(q1, q1lab, m_q, m_ql, b2, b3, b3lab, scr3, t1, t2)), *self.uncap(),
                      *set_tal(0, 0), *set_tal(1, 0)], 0.7),
            (lambda: [tal[0][0].animate.set_stroke(LANE_C[0]), tal[1][0].animate.set_stroke(LANE_C[1])], 0.2),
            "Auth approves",
            (lambda: [swap(labs[0], n0, RIGHT), swap(labs[1], n1, RIGHT), swap(hdr, hdr2)], 0.7),
            "and the ledger",
            (lambda: [Create(line2), FadeIn(n2), FadeIn(tal[2], shift=0.1 * LEFT)], 0.7),
        ])
        labs = [n0, n1, n2]
        evs = {}

        def put(node, n):
            e = E(node, n)
            evs[(node, n)] = e
            return e

        def bump(k, val):
            return set_tal(k, val)

        def rest():
            return [tal[k][0].animate.set_stroke(LANE_C[k]) for k in range(3)]

        self.steps("Auth approves, and gets 1. Capture and the ledger are busy with other payments. "
                   "Capture is at 1, and the ledger counts 1, 2, 3.", [
            (lambda: [FadeIn(put("a", 1), scale=0.6), *bump(0, 1)], 0.6),
            "Capture is at 1",
            (lambda: [*rest(), FadeIn(put("c", 1), scale=0.6), *bump(1, 1)], 0.5),
            "the ledger counts",
            (lambda: [FadeIn(put("l", 1), scale=0.6), *bump(2, 1)], 0.35),
            (lambda: [FadeIn(put("l", 2), scale=0.6), *bump(2, 2)], 0.35),
            (lambda: [FadeIn(put("l", 3), scale=0.6), *bump(2, 3)], 0.35),
            (lambda: rest(), 0.3),
        ])
        m1 = msg(P("a", 2), P("c", 3))
        m1l = T("carries 2", 20, GOLD_M).move_to([-0.05, 1.45, 0])
        qmark = ev(1, EVX[("c", 3)], "?", YELLOW_M)
        self.steps("Auth counts the send as 2, and the message carries 2. Capture's counter says 1. "
                   "What does capture's receive get? Pause and guess.", [
            (lambda: [FadeIn(put("a", 2), scale=0.6), *bump(0, 2)], 0.5),
            "the message carries",
            (lambda: [GrowArrow(m1), FadeIn(m1l)], 0.7),
            "Capture's counter",
            (lambda: [Indicate(tal[1][1], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "What does",
            (lambda: [FadeIn(qmark, scale=0.6)], 0.4),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("3. The bigger of 1 and 2 is 2, plus one. Everything capture does from now on sorts after the approval.", [
            (lambda: [FadeOut(qmark), FadeIn(put("c", 3), scale=0.6), *bump(1, 3), *self.cap("bigger of 1 and 2, plus one: 3", WHITE)], 0.6),
            "Everything capture",
            (lambda: [*rest(), *self.cap("everything capture does now sorts after the approval")], 0.5),
        ])
        m2 = msg(P("c", 4), P("l", 6))
        m2l = T("carries 4", 20, GOLD_M).move_to([3.6, -0.12, 0])
        self.steps("Capture sends to the ledger, with 4. But the ledger has counted to 5 on its own. "
                   "So the receive becomes the bigger of 5 and 4, plus one: 6.", [
            (lambda: [*self.uncap(), FadeIn(put("c", 4), scale=0.6), *bump(1, 4)], 0.5),
            (lambda: [GrowArrow(m2), FadeIn(m2l)], 0.7),
            "But the ledger",
            (lambda: [*rest(), FadeIn(put("l", 4), scale=0.6), *bump(2, 4)], 0.35),
            (lambda: [FadeIn(put("l", 5), scale=0.6), *bump(2, 5)], 0.35),
            "So the receive",
            (lambda: [FadeIn(put("l", 6), scale=0.6), *bump(2, 6), *self.cap("bigger of 5 and 4, plus one: 6", WHITE)], 0.6),
            (lambda: rest(), 0.3),
        ])
        self.steps("Notice what happened. A receive always ends up above the send that caused it. That's the whole guarantee.", [
            "A receive",
            (lambda: [glow(evs[("c", 3)][0]), glow(evs[("l", 6)][0]), *self.cap("a receive always lands above its send", YELLOW_M)], 0.9),
        ])

        # ---------------- scene 6: the name, and one list ----------------
        self.steps("This is called a Lamport timestamp, after Leslie Lamport, who described it in 1978. "
                   "And could have caused has a name too: happens before.", [
            (lambda: self.cap("Lamport timestamps (Leslie Lamport, 1978)", WHITE, 28), 0.6),
            "happens before",
            (lambda: self.cap("could have caused  =  happens-before,  written a → b", WHITE), 0.6),
        ])
        order = [("a", 1), ("c", 1), ("l", 1), ("a", 2), ("l", 2), ("c", 3), ("l", 3), ("c", 4), ("l", 4), ("l", 5), ("l", 6)]
        nid = {"a": 0, "c": 1, "l": 2}
        chips = VGroup(*[M(f"({n},{nid[nd]})", 21, LANE_C[nid[nd]]) for nd, n in order]).arrange(RIGHT, buff=0.3).move_to([0, LIST_Y, 0])
        self.steps("A stamp is the counter plus the node's own number, so a tie breaks the same way everywhere. "
                   "Auth is 0, capture 1, the ledger 2.", [
            (lambda: self.cap("stamp = (counter, node number)"), 0.5),
            "Auth is 0",
            (lambda: [Indicate(labs[0], color=BLUE_M), Indicate(labs[1], color=GREEN_M), Indicate(labs[2], color=PURPLE_M)], 0.9),
        ])
        self.steps("Sort all eleven stamps by counter, then by node number, and every event gets one place in one list. "
                   "Every cause sits before its effect.", [
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in chips], lag_ratio=0.15), *self.uncap()], 1.6),
            "Every cause",
            (lambda: [Indicate(chips[3], color=GOLD_M), Indicate(chips[5], color=GOLD_M),
                      Indicate(chips[7], color=GOLD_M), Indicate(chips[10], color=GOLD_M)], 0.9),
        ])

        # ---------------- scene 7: break the wrong model ----------------
        ring_a = Circle(radius=R + 0.12, stroke_color=YELLOW_M, stroke_width=4).move_to(P("a", 2))
        ring_l = Circle(radius=R + 0.12, stroke_color=YELLOW_M, stroke_width=4).move_to(P("l", 3))
        self.steps("So, does a smaller stamp mean it happened first? It's tempting. Let's test it.", [
            (lambda: self.cap("smaller stamp  =  happened first?", PURPLE_M), 0.6),
        ])
        path = VMobject(stroke_color=YELLOW_M, stroke_width=8, stroke_opacity=0.5).set_points_as_corners(
            [P("a", 2), P("c", 3), P("c", 4), P("l", 6)])
        self.steps("Auth's send has 2. The ledger's third event has 3. Two is smaller. But follow the arrows. "
                   "The only path from auth reaches the ledger at 6, long after its 3.", [
            (lambda: [Create(ring_a), Indicate(chips[3], color=YELLOW_M, scale_factor=1.25)], 0.5),
            "The ledger's third",
            (lambda: [Create(ring_l), Indicate(chips[6], color=YELLOW_M, scale_factor=1.25)], 0.5),
            "But follow",
            (lambda: [Create(path)], 1.4),
            "long after",
            (lambda: [glow(evs[("l", 6)][0]), glow(ring_l, YELLOW_M, 1.15)], 0.8),
        ])
        va = M("[2,0,0]", 20, GREY_B).move_to(P("a", 2) + [0, 0.66, 0])
        vl = M("[0,0,3]", 20, GREY_B).move_to(P("l", 3) + [0, 0.66, 0])
        self.steps("Neither could have known about the other. They're concurrent, and the order between them is only a tie-break.", [
            (lambda: [FadeOut(path), *self.cap("concurrent: neither could have known about the other", WHITE)], 0.6),
        ])
        self.steps("So the rule runs one way only. If a caused b, a's stamp is smaller. A smaller stamp doesn't mean a caused b, "
                   "or even that it came first. Telling those apart takes vector clocks: one counter per node, in every stamp.", [
            "If a caused b",
            (lambda: self.cap("a → b   gives   stamp(a) < stamp(b)", GREEN_M), 0.5),
            "A smaller stamp",
            (lambda: self.cap("stamp(a) < stamp(b)   does not give   a → b", RED_M), 0.5),
            "vector clocks",
            (lambda: [FadeIn(va, shift=0.1 * UP), FadeIn(vl, shift=0.1 * UP),
                      *self.cap("vector clocks: one counter per node. [2,0,0] vs [0,0,3]: neither is bigger", WHITE)], 0.7),
        ])

        # ---------------- scene 8: the limits ----------------
        self.steps("And a counter has no idea what time it is. It's great at after, and hopeless at when. "
                   "Ask it for everything after ten o'clock, and it just stares at you.", [
            (lambda: [FadeOut(VGroup(ring_a, ring_l, va, vl)), *self.cap("after: yes.   when: no idea.", WHITE)], 0.6),
            "Ask it for",
            (lambda: [*self.cap("everything after 10:00?", PURPLE_M),
                      *[Wiggle(tal[k], scale_value=1.08, rotation_angle=0.02 * TAU) for k in range(3)]], 1.0),
        ])
        self.steps("A quiet node counts slowly, so its counter can drift thousands away from a busy one's. "
                   "Use these stamps when you need causes before effects. When you also need the time of day, "
                   "the clock has to come back in, carefully, and that's the next step.", [
            "A quiet node",
            (lambda: [glow(tal[0][0], BLUE_M, 1.1), glow(tal[2][0], PURPLE_M, 1.1), *self.cap("a quiet node's counter falls far behind a busy one's")], 0.9),
            "Use these stamps",
            (lambda: self.cap("use them for causes before effects", GREEN_M), 0.5),
            "When you also",
            (lambda: self.cap("for the time of day too: add the clock back, carefully (next)", WHITE), 0.5),
        ])

        # ---------------- scene 9: moral, and a check ----------------
        self.steps("So, the chat. Count events instead of reading clocks, and jump past every message you receive. "
                   "Then an answer can never sort above its question, whatever the phones say.", [
            (lambda: self.cap("count events, and jump past every message", YELLOW_M, 30), 0.6),
            "Then an answer",
            (lambda: [glow(evs[("c", 3)][0]), glow(evs[("l", 6)][0])], 0.9),
        ])
        hyp = ev(1, 3.4, "?", YELLOW_M)
        hmsg = chip("message carries 4", GOLD_M, 20).move_to([3.4, 1.5, 0])
        harr = Arrow(hmsg.get_bottom(), hyp.get_top(), buff=0.05, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.25)
        self.steps("One quick check. Capture's counter is at 9, and a message arrives carrying 4. "
                   "What stamp does the receive get? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(chips)], 0.5),
            "Capture's counter",
            (lambda: [*set_tal(1, 9)], 0.5),
            "a message arrives",
            (lambda: [FadeIn(hmsg, shift=0.1 * DOWN), GrowArrow(harr), FadeIn(hyp, scale=0.6)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ans = ev(1, 3.4, 10, GREEN_M)
        self.steps("10. The bigger of 9 and 4, plus one. Not 5. The jump only ever goes up.", [
            (lambda: [Transform(hyp, ans), *set_tal(1, 10), *self.cap("bigger of 9 and 4, plus one: 10", GREEN_M)], 0.6),
            "Not 5",
            (lambda: self.cap("not 5: the jump only ever goes up", YELLOW_M, 28), 0.5),
        ], after=0.3)
        self.play(*rest(), run_time=0.5)
        self.wait(2.0)
