from sfz import *

SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bHerlihy\b", "Her-lee-hee"))
SAY.insert(0, (r"\b1990\b", "nineteen ninety"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CAP_Y, BAR_Y = -3.1, -2.7
X0, SC = -3.6, 0.15                      # time 0 ms at X0, 0.15 units per ms (60 ms -> 5.4)
NAME_X = -6.4
ROW = {"capture": 1.9, "ledger": 0.8, "fraud": -0.3, "email": -1.4}
NAMES = {"capture": "capture", "ledger": "ledger", "fraud": "fraud checker", "email": "email"}
AX_Y = -2.15
REPLAY_Y = 2.95


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
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0, y=BAR_Y):
        bar = Line([-1.0, y, 0], [1.0, y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def glow(m, color=YELLOW_M, s=1.05):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def x(t):
    return X0 + t * SC


def opbar(who, t0, t1, label, color):
    y = ROW[who]
    w = (t1 - t0) * SC
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.48, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.22), 1).move_to([x(t0) + w / 2, y, 0])
    return VGroup(r, fit(M(label, 20), w - 0.15).move_to(r))


def point(who, t, color=YELLOW_M):
    """A chosen instant: a yellow tick through the bar, with its time above."""
    y = ROW[who]
    ln = VGroup(Line([x(t), y + 0.26, 0], [x(t), y + 0.4, 0], stroke_width=5, color=color),
                Line([x(t), y - 0.4, 0], [x(t), y - 0.26, 0], stroke_width=5, color=color))
    lab = M(str(t), 18, color).move_to([x(t), y + 0.56, 0])
    return VGroup(ln, lab)


def board(status, color):
    r = RoundedRectangle(corner_radius=0.12, width=7.0, height=1.7, stroke_color=GREY_B, stroke_width=3).set_fill("#0d0f12", 1)
    head = T("departures", 20, GREY_B).move_to(r.get_top() + 0.3 * DOWN)
    train = M("08:15  Riverside", 26)
    train.move_to(r.get_center() + 0.25 * DOWN).align_to(r, LEFT).shift(0.45 * RIGHT)
    st = M(status, 26, color).move_to(r.get_center() + 0.25 * DOWN + 2.3 * RIGHT)
    return VGroup(r, head, train, st)


def replay_chip(s, color=WHITE):
    return chip(s, color, 20, mono=True)


class Linearizability(Base):
    """cons-02, section 0. A café owner's phone says a payment arrived; her list says it hasn't. What does "behave like
    one copy" demand? A station's departure board flips at one instant and never back (the analogy). The lesson's
    stepper: capture writes status 2 over 0-60 ms; the ledger (5-15) reads -, the fraud checker (20-30) reads 2, the
    email program (40-50) reads -. Pick one instant per bar: ledger 10, write 18, fraud 25, and email fails. The second
    channel, the linearization with email reading 2 (10, 18, 25, 45), the names (Herlihy and Wing, 1990), what
    "seems" allows, locality, the moral, and an overlap check."""

    def construct(self):
        self.capm = None
        self.title_card("One copy, one timeline", "what linearizable demands")

        # ---------------- scene 1: the café owner ----------------
        note = chip("Payment received: 30.00", GREEN_M, 26).move_to([0, 2.3, 0])
        lst = RoundedRectangle(corner_radius=0.12, width=5.0, height=2.3, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0d0f12", 1)
        lst.move_to([0, -0.2, 0])
        lhead = T("payments", 22, GREY_B).move_to(lst.get_top() + 0.32 * DOWN)
        empty = T("(not here yet)", 22, RED_M).move_to(lst.get_center() + 0.1 * DOWN)
        row = M("30.00   received", 24, GREEN_M).move_to(lst.get_center() + 0.1 * DOWN)
        self.steps("A café owner's phone buzzes: payment received, 30.00.", [
            (lambda: [FadeIn(note, shift=0.2 * DOWN)], 0.6),
            (lambda: [Wiggle(note, scale_value=1.05)], 0.7),
        ])
        self.steps("She opens the payments app to look at it, and the payment isn't in the list. She pulls down to refresh, and there it is.", [
            (lambda: [FadeIn(VGroup(lst, lhead), shift=0.1 * UP)], 0.6),
            "isn't in the list",
            (lambda: [FadeIn(empty)], 0.5),
            "She pulls down",
            (lambda: [swap(empty, row, DOWN)], 0.7),
        ])
        self.steps("The message was sent after the payment was saved. The list read a copy that hadn't caught up yet.", [
            (lambda: [glow(note[0], GREEN_M)], 0.7),
            "The list read",
            (lambda: [*self.cap("the list read a copy that hadn't caught up yet", WHITE)], 0.5),
        ])
        self.steps("It's easy to shrug. A second later, everything agreed. But if the app had used that list to decide whether "
                   "the payment could be refunded, a second is plenty of time to decide wrong.", [
            "But if the app",
            (lambda: self.cap("a refund decided from that list: a second is plenty to decide wrong", RED_M), 0.6),
        ])
        self.steps("The usual cure is to make the copies behave like one. So what exactly does one copy demand?", [
            (lambda: self.cap("behave like one copy: what exactly does that demand?", YELLOW_M), 0.6),
        ])

        # ---------------- scene 2: the departure board ----------------
        bd = board("on time", GREEN_M).move_to([0, 0.6, 0])
        bd_b = M("boarding", 26, GOLD_M).move_to(bd[3])
        self.steps("Picture the departure board at a station. One board. At some instant, your train's line flips from on time to boarding.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(note, lst, lhead, row))], 0.6),
            "Picture the",
            (lambda: [FadeIn(bd, shift=0.1 * UP)], 0.7),
            "flips from",
            (lambda: [swap(bd[3], bd_b, DOWN)], 0.6),
        ])
        bd.submobjects[3] = bd_b
        b4 = T("looked before the flip: on time", 22, GREEN_M).move_to([-3.3, -1.0, 0])
        b5 = T("after: boarding", 22, GOLD_M).move_to([3.3, -1.0, 0])
        self.steps("Anyone who looks before the flip sees on time. Anyone after, boarding. If you glance up right while it changes, "
                   "you get one or the other, never half.", [
            (lambda: [FadeIn(b4, shift=0.1 * UP)], 0.5),
            "Anyone after",
            (lambda: [FadeIn(b5, shift=0.1 * UP)], 0.5),
            "one or the other",
            (lambda: self.cap("glance during the change: one or the other, never half"), 0.5),
        ])
        self.steps("And once anybody has seen boarding, nobody who looks later can see on time. A board doesn't flip back.", [
            (lambda: [glow(bd[0], GOLD_M), *self.cap("once anyone has seen boarding, nobody later sees on time", WHITE)], 0.8),
        ])
        self.steps("Map it. The board is one copy. The flip is the instant a write takes effect. And each glance is a read.", [
            (lambda: self.cap("board  =  one copy"), 0.4),
            "The flip",
            (lambda: self.cap("the flip  =  the instant a write takes effect"), 0.4),
            "each glance",
            (lambda: self.cap("a glance  =  a read"), 0.4),
        ])

        # ---------------- scene 3: four programs, one value ----------------
        names = {k: left_at(T(NAMES[k], 22, GREY_B), NAME_X, ROW[k]) for k in ROW}
        lanes = {k: Line([x(0) - 0.2, ROW[k], 0], [x(60) + 0.2, ROW[k], 0], stroke_width=1.2, color=GREY_D) for k in ROW}
        axis = VGroup(Line([x(0), AX_Y, 0], [x(60), AX_Y, 0], stroke_width=2, color=GREY_C))
        for t in range(0, 61, 10):
            axis.add(Line([x(t), AX_Y - 0.07, 0], [x(t), AX_Y + 0.07, 0], stroke_width=2, color=GREY_C))
            axis.add(M(f"{t}" + (" ms" if t == 60 else ""), 18, GREY_B).move_to([x(t) + (0.2 if t == 60 else 0), AX_Y - 0.3, 0]))
        cap_b = opbar("capture", 0, 60, "w status = 2", GOLD_M)
        st_key = VGroup(M("1 = authorized", 20, GREY_B), M("2 = captured", 20, GOLD_M)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        st_key.move_to([0, 0.6, 0])
        self.steps("Now four programs and one value. The payments app keeps each payment's status as a number. "
                   "1 means authorized, the money set aside. 2 means captured, the money moved to the shop.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(bd, b4, b5))], 0.6),
            "keeps each payment's",
            (lambda: [FadeIn(st_key[0], shift=0.1 * UP)], 0.5),
            "2 means",
            (lambda: [FadeIn(st_key[1], shift=0.1 * UP)], 0.5),
        ])
        self.steps("The capture program writes status 2, and the write takes 60 milliseconds from request to answer. "
                   "A value you can read and write like this is called a register.", [
            (lambda: [FadeOut(st_key), FadeIn(names["capture"]), Create(lanes["capture"]), Create(axis)], 0.7),
            "writes status 2",
            (lambda: [GrowFromEdge(cap_b, LEFT)], 1.2),
            "called a register",
            (lambda: self.cap("register: a value you can read and write", WHITE), 0.5),
        ])
        bars = {"ledger": opbar("ledger", 5, 15, "r: -", BLUE_M), "fraud": opbar("fraud", 20, 30, "r: 2", BLUE_M),
                "email": opbar("email", 40, 50, "r: -", BLUE_M)}
        self.steps("Meanwhile, three programs read the status. The ledger, which keeps the books. The fraud checker. "
                   "And the email program, which sends receipts. Each bar runs from when the request is sent to when the answer comes back.", [
            (lambda: [*self.uncap()], 0.3),
            "The ledger",
            (lambda: [FadeIn(names["ledger"]), Create(lanes["ledger"]), FadeIn(bars["ledger"])], 0.5),
            "The fraud checker",
            (lambda: [FadeIn(names["fraud"]), Create(lanes["fraud"]), FadeIn(bars["fraud"])], 0.5),
            "And the email",
            (lambda: [FadeIn(names["email"]), Create(lanes["email"]), FadeIn(bars["email"])], 0.5),
            "Each bar runs",
            (lambda: [*self.cap("each bar: from request sent to answer received"), glow(bars["fraud"][0], WHITE, 1.08)], 0.7),
        ])

        # ---------------- scene 4: the rule ----------------
        self.steps("Here's the board's rule, written for bars. Pick one instant inside each bar where the operation really happened. "
                   "Then replay those instants, in order, on one plain copy. Every answer has to match.", [
            (lambda: self.cap("pick one instant inside each bar", WHITE), 0.5),
            "Then replay",
            (lambda: self.cap("replay the instants, in order, on one plain copy: every answer must match", WHITE), 0.5),
        ])
        pts = {}
        rp = [replay_chip("ledger @10: -", BLUE_M), replay_chip("write @18", GOLD_M), replay_chip("fraud @25: 2", BLUE_M),
              replay_chip("email @45: ?", BLUE_M)]
        rp_lab = T("one copy, in order:", 20, GREY_B)
        rp_row = VGroup(rp_lab, *rp).arrange(RIGHT, buff=0.25).move_to([0.2, REPLAY_Y, 0])
        fit(rp_row, 12.6)
        self.steps("The ledger, from 5 to 15, got the old status. The dash means old. Fine: put its instant at 10, and the write's instant later.", [
            (lambda: [*self.cap("-  :  the old status"), glow(bars["ledger"][0], BLUE_M, 1.1)], 0.7),
            "put its instant",
            (lambda: [FadeIn(pts.setdefault("ledger", point("ledger", 10)), scale=0.6), FadeIn(rp_lab), FadeIn(rp[0], shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("The fraud checker, from 20 to 30, got 2. So the write's instant must come before the fraud check's. "
                   "Put the write at 18, and the fraud check at 25.", [
            (lambda: [glow(bars["fraud"][0], BLUE_M, 1.1)], 0.6),
            "Put the write",
            (lambda: [FadeIn(pts.setdefault("capture", point("capture", 18)), scale=0.6), FadeIn(rp[1], shift=0.1 * DOWN)], 0.5),
            "and the fraud",
            (lambda: [FadeIn(pts.setdefault("fraud", point("fraud", 25)), scale=0.6), FadeIn(rp[2], shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("The capture program hasn't heard back yet. That doesn't matter.", [
            (lambda: [Indicate(cap_b[0], color=GOLD_M, scale_factor=1.03), *self.cap("the write's answer comes at 60: its instant can be earlier")], 0.8),
        ])
        span = Rectangle(width=10 * SC, height=0.62, stroke_width=0).set_fill(YELLOW_M, 0.18).move_to([x(45), ROW["email"], 0])
        self.steps("Now the email program, from 40 to 50, got the old status. Can we place its instant? Pause and guess.", [
            (lambda: [*self.uncap(), glow(bars["email"][0], BLUE_M, 1.1), FadeIn(rp[3], shift=0.1 * DOWN)], 0.7),
            "Can we place",
            (lambda: [FadeIn(span)], 0.5),
            "Pause and guess",
            (lambda: self.cap("can the email's instant go anywhere?   pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        fail = replay_chip("email: no fit", RED_M)
        fail.move_to(rp[3]).align_to(rp[3], LEFT)
        self.steps("No. Its instant must be after 40, so it's after the write. One copy would answer 2 there. "
                   "No choice of instants works. This history isn't linearizable.", [
            (lambda: [*self.uncap(), Indicate(axis, color=YELLOW_M, scale_factor=1.0)], 0.5),
            "after the write",
            (lambda: [glow(pts["capture"][0], YELLOW_M, 1.2)], 0.5),
            "One copy would",
            (lambda: [FadeOut(rp[3]), FadeIn(fail), bars["email"][0].animate.set_stroke(RED_M)], 0.6),
            "No choice",
            (lambda: self.cap("no choice of instants works: not linearizable", RED_M), 0.5),
        ])
        self.steps("Once any read has returned the new value, every read that starts later must return it too.", [
            (lambda: [glow(bars["fraud"][0], GOLD_M, 1.08), *self.cap("once any read returns the new value, every later read must too", YELLOW_M)], 0.9),
        ])

        # ---------------- scene 5: the second channel ----------------
        self.steps("You might be thinking: the fraud checker and the email program run on different computers. "
                   "If they never talk, who would ever notice?", [
            (lambda: self.cap("different computers: who would ever notice?", PURPLE_M), 0.5),
        ])
        ch = Arrow(bars["fraud"][0].get_bottom() + 0.05 * DOWN, bars["email"][0].get_top() + 0.05 * UP,
                   buff=0.05, stroke_width=4, color=GREEN_M, max_tip_length_to_length_ratio=0.15)
        chl = T("\"captured!\"", 20, GREEN_M).next_to(ch, RIGHT, buff=0.15)
        self.steps("Any second channel notices. The fraud checker announces: captured. The email program reacts, and reads the old status. "
                   "That's the café owner's buzz, and her empty list.", [
            "The fraud checker announces",
            (lambda: [GrowArrow(ch), FadeIn(chl)], 0.7),
            "and reads the old",
            (lambda: [Indicate(bars["email"], color=RED_M, scale_factor=1.08)], 0.7),
            "That's the café",
            (lambda: self.cap("the buzz was the second channel; the list was the stale read", WHITE), 0.5),
        ])
        self.steps("It's a friend texting: we're boarding! while the board in front of you still says on time. One of you is about to miss a train. "
                   "So the order that matters is real time, because any message between programs can expose it.", [
            "So the order",
            (lambda: self.cap("the order that matters: real time", YELLOW_M), 0.6),
        ])

        # ---------------- scene 6: the good history, and the names ----------------
        email2 = opbar("email", 40, 50, "r: 2", BLUE_M)
        ok_chip = replay_chip("email @45: 2", GREEN_M).move_to(fail)
        self.steps("Had the email program read 2, the instants would be: the ledger at 10, the write at 18, the fraud check at 25, "
                   "and the email at 45. Each inside its own bar.", [
            (lambda: [*self.uncap(), FadeOut(ch), FadeOut(chl), FadeOut(span), swap(bars["email"], email2)], 0.7),
            "the email at 45",
            (lambda: [FadeIn(pts.setdefault("email", point("email", 45)), scale=0.6), swap(fail, ok_chip)], 0.6),
        ])
        bars["email"] = email2
        self.steps("Replay them on one copy, and every answer matches.", [
            (lambda: [LaggedStart(*[Indicate(c, color=GREEN_M, scale_factor=1.08) for c in (rp[0], rp[1], rp[2], ok_chip)], lag_ratio=0.3)], 1.2),
        ])
        self.steps("That order is called a linearization, and each chosen instant is a linearization point. "
                   "A history that has one is linearizable. Maurice Herlihy and Jeannette Wing gave this exact rule in 1990.", [
            (lambda: self.cap("that order: a linearization", WHITE, 28), 0.5),
            "each chosen instant",
            (lambda: [*self.cap("each chosen instant: a linearization point", YELLOW_M, 28),
                      *[glow(p[0], YELLOW_M, 1.2) for p in pts.values()]], 0.8),
            "Maurice Herlihy",
            (lambda: self.cap("linearizable (Herlihy and Wing, 1990)", WHITE, 28), 0.5),
        ])

        # ---------------- scene 7: the guardrails ----------------
        self.steps("Two things to keep straight. The instant is a thought experiment. The store never reports it. "
                   "We only ask whether some choice works.", [
            (lambda: self.cap("the instant is a thought experiment: the store never reports it"), 0.6),
        ])
        self.steps("And the word seems carries the weight. Inside, a store may hold writes back, copy them, retry them. "
                   "What it may not do is let any client see something one copy couldn't have produced.", [
            (lambda: self.cap("inside: anything goes (hold back, copy, retry)"), 0.5),
            "What it may not",
            (lambda: self.cap("outside: nothing one copy couldn't have produced", YELLOW_M), 0.5),
        ])
        self.steps("One gift from the proof: the rule works value by value. If the operations on each value pass, the whole history passes, "
                   "so a checker can take each value on its own. And sending each write to every copy, sooner or later, doesn't give you this rule.", [
            (lambda: self.cap("local: check each value on its own"), 0.5),
            "And sending",
            (lambda: self.cap("\"every copy gets the write, sooner or later\" is not this rule", RED_M), 0.5),
        ])

        # ---------------- scene 8: moral and check ----------------
        self.steps("So: one copy, one timeline. Every operation lands at one instant inside its bar, and once anyone sees the new value, "
                   "nobody who starts later sees the old one.", [
            (lambda: self.cap("one copy, one timeline", YELLOW_M, 32), 0.6),
            "Every operation",
            (lambda: [LaggedStart(*[glow(p[0], YELLOW_M, 1.2) for p in pts.values()], lag_ratio=0.2)], 1.0),
        ])
        email3 = opbar("email", 22, 32, "r: -", BLUE_M)
        self.steps("One quick check. Suppose the email's read had run from 22 to 32, overlapping the fraud check, and returned the old status. "
                   "Allowed? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(pts["email"]), FadeOut(VGroup(*rp, rp_lab, ok_chip)), swap(bars["email"], email3)], 0.8),
            "Allowed",
            (lambda: self.cap("email 22 to 32, reads -: allowed?   pause and think", YELLOW_M), 0.4),
        ], after=0)
        bars["email"] = email3
        self.countdown(3.0)
        new_pts = [point("email", 23), point("capture", 24), point("fraud", 26)]
        rp2 = VGroup(T("one copy, in order:", 20, GREY_B), replay_chip("ledger @10: -", BLUE_M), replay_chip("email @23: -", BLUE_M),
                     replay_chip("write @24", GOLD_M), replay_chip("fraud @26: 2", BLUE_M)).arrange(RIGHT, buff=0.25).move_to([0.2, REPLAY_Y, 0])
        fit(rp2, 12.6)
        self.steps("Yes. Put the email at 23, the write at 24, and the fraud check at 26. A read that overlaps the change may see either side.", [
            (lambda: [*self.uncap(), FadeOut(pts["capture"]), FadeOut(pts["fraud"])], 0.4),
            "Put the email",
            (lambda: [FadeIn(new_pts[0], scale=0.6)], 0.4),
            "the write at 24",
            (lambda: [FadeIn(new_pts[1], scale=0.6)], 0.4),
            "the fraud check",
            (lambda: [FadeIn(new_pts[2], scale=0.6), FadeIn(rp2, shift=0.1 * DOWN)], 0.6),
            "A read that overlaps",
            (lambda: self.cap("overlapping the change: either side is fine", GREEN_M, 28), 0.5),
        ], after=0.3)
        self.wait(2.0)
