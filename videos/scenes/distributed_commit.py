from sfz import *

SAY.insert(0, (r"\baudit-0\b", "audit zero"))
SAY.insert(0, (r"\bCockroachDB\b", "cockroach D B"))
SAY.insert(0, (r"\b20\.00\b", "twenty"))

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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))



SX, AX, BY = -4.2, 4.2, 2.05             # settle (writer) and audit-0 (reader)
BW, BH = 3.4, 1.05
AXY = -0.35                              # the timestamp axis
TS0, TS1 = -5, 25


def xs(ts):
    return -6.0 + (ts - TS0) * 12.0 / (TS1 - TS0)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


class Who:
    def __init__(self, x, name, sub, color):
        self.c = np.array([x, BY, 0])
        self.color = color
        self.r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(self.c)
        self.n = self.name_t(name)
        self.s = self.sub_t(sub)

    def name_t(self, s):
        return T(s, 26, WHITE).move_to(self.c + UP * 0.2)

    def sub_t(self, s, color=GREY_B):
        return fit(T(s, 20, color), BW - 0.3).move_to(self.c + DOWN * 0.24)

    @property
    def g(self):
        return VGroup(self.r, self.n, self.s)

    def rename(self, name, sub):
        nn, ns = self.name_t(name), self.sub_t(sub)
        on, os_ = self.n, self.s
        self.n, self.s = nn, ns
        return [swap(on, nn), swap(os_, ns)]

    def sub(self, s, color=GREY_B):
        ns = self.sub_t(s, color)
        old, self.s = self.s, ns
        return [swap(old, ns)]


class DistributedCommit(Base):
    """cons-06, section 3: CockroachDB's uncertain reader. The branch picture (clerks stamping slips by their own
    clocks; an auditor). The lab's TRUST_CLOCK run: settle 10 ms fast commits batch 1 at 10, the client hears "paid" at
    8 ms; audit-0, 10 ms slow, reads at -1 and misses it. The RESTART run: the read's window reaches 19, batch 1 (10) is
    inside it, the audit restarts at 10 and sees payouts = 1 (4 ms instead of 2). Max offset (500 ms, 250 for multi-region;
    nodes off by 80% shut down), the name, intents and parallel commits, the moral and a check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, 3.3, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def bot(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, -3.3, 0])
        old, self.botm = self.botm, new
        return [swap(old, new)]

    def unbot(self):
        old, self.botm = self.botm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        p = np.array([0, -2.55, 0])
        bar = Line(p + LEFT * 1.1, p + RIGHT * 1.1, stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def truth(self, s):
        return self.put("true", T(s, 22, YELLOW_M).move_to([0, BY, 0]))

    def marker(self, key, ts, label, color, y):
        x = xs(ts)
        c = chip(label, color, 24).move_to([x, y, 0])
        ln = DashedLine([x, c.get_bottom()[1] - 0.05, 0], [x, AXY + 0.08, 0], dash_length=0.06, stroke_width=2, color=color)
        c[0].set_fill(fillc(color, 0.18), 1)
        g = VGroup(ln, c)
        old = self.lab.get(key)
        self.lab[key] = g
        ln.set_z_index(2)
        c.set_z_index(4)
        return [swap(old, g)]

    def window(self, lo, hi, color=TEAL_M, label=None):
        band = Rectangle(width=xs(hi) - xs(lo), height=0.22, stroke_color=color, stroke_width=2).set_fill(color, 0.3)
        band.move_to([(xs(lo) + xs(hi)) / 2, AXY - 0.55, 0])
        g = VGroup(band)
        if label:
            g.add(T(label, 22, color).move_to([(xs(lo) + xs(hi)) / 2, AXY - 0.98, 0]))
        return self.put("win", g)

    def reads(self, s, color):
        return self.put("reads", T(s, 24, color).move_to([0, -2.05, 0]))

    def construct(self):
        self.capm = None
        self.botm = None
        self.lab = {}
        self.title_card("The reader who isn't sure", "clocks that disagree, and a read that starts over")

        # ---------------- scene 1: the question ----------------
        self.steps("Picture paying a friend back. You send 20.00, your app says Sent, and you text them: done. They open "
                   "their app a second later, and the money isn't there. Then it appears.", [
            (lambda: self.cap("you: Sent", GREEN_M, 28), 0.5),
            "They open",
            (lambda: self.cap("you: Sent        your friend, a second later: nothing yet", WHITE, 28), 0.6),
            "Then it appears",
            (lambda: self.cap("you: Sent        your friend, a second later: 20.00", WHITE, 28), 0.5),
        ])
        self.steps("For a moment, their app showed a world where you hadn't paid. How does a database spread over many "
                   "machines end up showing that? Hold that question.", [
            "How does",
            (lambda: self.bot("how does a database on many machines show a world where you hadn't paid?", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 2: the branches ----------------
        W = Who(SX, "branch clerk", "clock: a little fast", GREEN_M)
        R = Who(AX, "auditor", "clock: a little slow", BLUE_M)
        self.steps("Think of bank branches in different towns. Each clerk stamps deposit slips with the branch's own wall "
                   "clock. An auditor notes the time the audit starts, and counts every slip stamped before it.", [
            (lambda: [*self.unbot(), *self.cap("bank branches, each with its own clock", WHITE)], 0.5),
            "Each clerk",
            (lambda: [FadeIn(W.g)], 0.5),
            "An auditor",
            (lambda: [FadeIn(R.g)], 0.5),
        ])
        self.steps("If the clocks agree, that works. But clocks never quite agree. A slip stamped by a fast clock can look "
                   "newer than an audit that really started after it.", [
            "But clocks",
            (lambda: [Indicate(W.s, color=GREEN_M), Indicate(R.s, color=BLUE_M)], 0.8),
            "A slip stamped",
            (lambda: self.bot("a fast clock's slip can look newer than a later audit", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 3: trust the clocks, in the lab ----------------
        axis = Line([xs(TS0), AXY, 0], [xs(TS1), AXY, 0], stroke_width=2.5, color=GREY_B)
        ticks = VGroup(*[VGroup(Line([xs(t), AXY - 0.08, 0], [xs(t), AXY + 0.08, 0], stroke_width=2, color=GREY_B),
                                T(str(t), 22, GREY_B).move_to([xs(t), AXY - 0.3, 0])) for t in range(-5, 26, 5)])
        alab = T("timestamp (ms)", 20, GREY_B).move_to([xs(TS1) - 0.8, AXY - 0.62, 0])
        self.steps("Now the lab's version. Two servers: settle pays batch 1 of the nightly payout, and its clock runs ten "
                   "milliseconds fast. audit-0 runs an audit, a report that checks the books, and its clock runs ten "
                   "milliseconds slow.", [
            (lambda: [*self.unbot(), *self.cap("the lab: two servers, clocks 10 ms apart from true time", WHITE)], 0.5),
            "settle pays",
            (lambda: W.rename("settle", "clock: 10 ms fast"), 0.6),
            "audit-0 runs",
            (lambda: R.rename("audit-0", "clock: 10 ms slow"), 0.6),
            "milliseconds slow",
            (lambda: [Create(axis), FadeIn(ticks), FadeIn(alab)], 0.8),
        ])
        self.steps("Settle commits batch 1 at timestamp 10, its own clock reading. At 8 milliseconds of true time, the "
                   "client hears: paid.", [
            (lambda: [*self.truth("true time: 0"), *self.marker("batch", 10, "batch 1 @ 10", GREEN_M, 0.35)], 0.6),
            "At 8",
            (lambda: [*self.truth("true time: 8 ms"), *W.sub("client told: paid", GREEN_M)], 0.6),
        ])
        self.steps("One millisecond later, the audit starts. Its clock reads minus 1, so it reads everything stamped up "
                   "to minus 1. Batch 1, stamped 10, looks like the future. The audit reads payouts: zero.", [
            (lambda: [*self.truth("true time: 9 ms"), *R.sub("audit starts", BLUE_M)], 0.5),
            "Its clock reads",
            (lambda: self.marker("read", -1, "read @ -1", BLUE_M, 1.05), 0.6),
            "looks like the future",
            (lambda: [Indicate(self.lab["batch"][1], color=GREY_B, scale_factor=1.1)], 0.7),
            "payouts: zero",
            (lambda: self.reads("audit reads payouts = 0", RED_M), 0.5),
        ])
        self.steps("Well. The batch was paid before the audit began, and the audit missed it. That's your friend's empty "
                   "app, with timestamps.", [
            (lambda: self.bot("paid before the audit began, and the audit missed it", RED_M), 0.6),
        ], after=0.3)
        self.stamp("stale")

        # ---------------- scene 4: the wish ----------------
        self.steps("There are fixes that make every writer pay. A head office can hand out every stamp by phone, or every "
                   "clerk can wait out the clock's error before saying done. But what if writers don't wait at all, and "
                   "the reader handles the doubt?", [
            (lambda: [*self.unbot(), *self.cap("fixes that make every writer pay: a head office, or waiting out the error", WHITE)], 0.6),
            "But what if",
            (lambda: self.cap("wanted: writers never wait; the reader handles the doubt", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 5: the bound, the window, predict ----------------
        self.steps("That's what CockroachDB does, a SQL database that runs on ordinary servers with ordinary clocks. "
                   "It promises a bound on how far any two clocks may disagree.", [
            (lambda: [*self.drop("reads"), *self.cap("CockroachDB: ordinary servers, a promised bound on clock error", TEAL_M)], 0.6),
        ])
        self.steps("So a reader at timestamp T knows that anything stamped above T plus that bound was written after it "
                   "began. Anything in between is uncertain: it may have committed first, on a server whose clock runs "
                   "ahead. In the lab the bound is 20 milliseconds, so the audit's window runs from minus 1 up to 19.", [
            "anything stamped above",
            (lambda: self.bot("above T + bound: surely written after the read began", WHITE), 0.6),
            "Anything in between",
            (lambda: self.bot("between T and T + bound: can't tell", TEAL_M), 0.6),
            "so the audit's window",
            (lambda: self.window(-1, 19, TEAL_M, "uncertain: -1 to 19"), 0.7),
        ])
        self.steps("Batch 1 is stamped 10. Inside the window, or outside? And what should the audit do? Pause and guess.", [
            (lambda: [*self.unbot(), *self.cap("batch 1 at 10: inside the window? what should the audit do?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("Inside. The audit can't tell whether that payment came before it or after, so it can't skip it. It "
                   "moves its own read timestamp up to 10, and reads again: payouts 1, ledger 1. One restart.", [
            (lambda: [Indicate(self.lab["batch"][1], color=TEAL_M, scale_factor=1.15)], 0.7),
            "It moves",
            (lambda: [*self.marker("read", 10, "read @ 10", BLUE_M, 1.0), *R.sub("restarts at 10", BLUE_M)], 0.7),
            "payouts 1",
            (lambda: self.reads("audit reads payouts = 1, ledger = 1", GREEN_M), 0.5),
        ])
        self.steps("The audit took 4 milliseconds instead of 2, and the writer still answered at 8. It's the auditor who "
                   "finds a slip stamped just after the audit began, and starts over to count it in.", [
            (lambda: self.bot("the writer: 8 ms, no wait      the audit: 4 ms instead of 2", WHITE), 0.6),
            "It's the auditor",
            (lambda: self.cap("the auditor starts over and counts the slip in", WHITE), 0.6),
        ], after=0.3)
        self.stamp("restart")

        # ---------------- scene 6: the names ----------------
        self.steps("That window is called the uncertainty interval, and the bound is the max offset. The top of the "
                   "window stays put when the read moves up, so the restarts must end.", [
            (lambda: [*self.unbot(), *self.cap("the window: the uncertainty interval      the bound: the max offset", TEAL_M)], 0.6),
            "The top of the",
            (lambda: [Indicate(self.lab["win"], color=TEAL_M, scale_factor=1.04)], 0.8),
        ])
        self.steps("The writes themselves go in as intents, provisional values, plus one transaction record that says "
                   "commit or abort. With parallel commits, the transaction counts as done once every intent has "
                   "reached agreement: one round instead of two.", [
            (lambda: self.bot("writes: intents + one transaction record", WHITE), 0.6),
            "With parallel commits",
            (lambda: self.bot("parallel commits: done when every intent is agreed, one round instead of two", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 7: the guardrail ----------------
        self.steps("Now, the fine print. The max offset is 500 milliseconds by default, and 250 is suggested for clusters "
                   "spread over several regions. The bound has to hold, so a server whose clock is off from at least half "
                   "the others by 80% of it shuts itself down, rather than give wrong answers.", [
            (lambda: [*self.unbot(), *self.cap("max offset: 500 ms by default, 250 suggested across regions", WHITE)], 0.6),
            "The bound has to hold",
            (lambda: self.bot("a clock off by 80% of the bound: that server shuts itself down", RED_M), 0.6),
        ])
        self.steps("If clocks drift past it anyway, real-time order can break. And here the branch picture breaks too. "
                   "Clerks would recount for seconds. Servers do it for milliseconds, thousands of times a second, so "
                   "clock error becomes a cost you can measure, paid by reads of recently written keys.", [
            (lambda: self.bot("clocks past the bound: real-time order can break", RED_M), 0.6),
            "Servers do it",
            (lambda: self.bot("restarts cost reads of keys written within the last max offset", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: the bound on the clock's error, not the clock's reading, sets the price. "
                   "Know your bound.", [
            (lambda: [*self.unbot(), *self.cap("the bound on the error, not the reading, sets the price", YELLOW_M, 28)], 0.6),
            "Know your bound",
            (lambda: self.bot("know your bound", YELLOW_M, 28), 0.5),
        ], after=0.3)
        self.steps("One quick check. The audit reads at minus 1 again, with its window up to 19. Suppose batch 1 were "
                   "stamped 23 instead. Restart, or not? Pause and think.", [
            (lambda: [*self.unbot(), *self.drop("reads"), *self.marker("read", -1, "read @ -1", BLUE_M, 1.05),
                      *self.marker("batch", 23, "batch 1 @ 23", GREEN_M, 0.35), *R.sub("audit starts", BLUE_M),
                      *self.cap("batch 1 at 23: restart, or not?  pause and think", YELLOW_M)], 0.7),
        ], after=0)
        self.countdown(3.0)
        self.steps("No restart. 23 is above the window's top, so it was surely written after the audit began. The audit "
                   "can skip it with a clear conscience.", [
            (lambda: [Indicate(self.lab["batch"][1], color=GREEN_M, scale_factor=1.15)], 0.7),
            "surely written after",
            (lambda: self.bot("above the window: surely later, safe to skip", GREEN_M), 0.6),
        ], after=0.3)
        self.play(*self.cap("only the uncertain values cost a restart", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
