from sfz import *

# Amounts are said the way people say them ("seventy"); captions keep "70.00".
SAY[0:0] = [
    (r"\b(\d+)\.00\b", r"\1"),
    (r"\btxf-1\b", "T X F one"),
    (r"\bw-17\b", "W seventeen"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BOX_TOP, BOX_BOT = 2.75, -1.15
BOX_CY = (BOX_TOP + BOX_BOT) / 2
SW = 4.0                                   # a server's width
SX = {"w": -4.6, "p": 4.6}                 # wallets, payouts
CW = 3.6                                   # the coordinator in the middle
ROW_Y, DIV_Y, LOGL_Y = 1.5, 1.08, 0.8
LOG_Y = [0.4, 0.0, -0.4, -0.8]             # a server's log lines
LINK_Y = 1.5
TAG_Y = 3.15                               # the dinner tags above the boxes
READ_Y, BAR_Y, CAP_Y = -1.72, -2.6, -3.2
VOTE_Y = {"w": 0.4, "p": 0.0}
CLOG_Y = -0.62                             # the coordinator's one log line
SC = {"w": BLUE_M, "p": GOLD_M}
CC = PURPLE_M


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


def frame_box(cx, w, color):
    return RoundedRectangle(corner_radius=0.16, width=w, height=BOX_TOP - BOX_BOT, stroke_color=color,
                            stroke_width=3).set_fill(fillc(color), 1).move_to([cx, BOX_CY, 0])


def server(k, name, sub):
    cx, c = SX[k], SC[k]
    x0, x1 = cx - SW / 2, cx + SW / 2
    return VGroup(frame_box(cx, SW, c), T(name, 28, c).move_to([cx, 0, 0]).align_to([0, BOX_TOP - 0.2, 0], UP),
                  T(sub, 19, GREY_B).move_to([cx, BOX_TOP - 0.74, 0]),
                  Line([x0 + 0.2, DIV_Y, 0], [x1 - 0.2, DIV_Y, 0], stroke_width=1.5, color=GREY_D),
                  left_at(T("log on disk", 17, GREY_B), x0 + 0.25, LOGL_Y))


def padlock(at, color=RED_M):
    body = RoundedRectangle(corner_radius=0.04, width=0.26, height=0.2, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.4), 1)
    shackle = Arc(radius=0.085, start_angle=0, angle=PI, stroke_color=color, stroke_width=2.5)
    shackle.next_to(body, UP, buff=-0.01)
    return VGroup(shackle, body).move_to(at)


class TwoPhaseCommit(Base):
    """txn-07, section 1. 30.00 leaves wallet w-17 on `wallets` and never reaches the café on `payouts`. One server
    commits with one log line, but two servers have no single line. Commit-one-then-the-other breaks. The dinner by
    text: ask, everyone keeps Friday free, one diary line decides. Prepare (log, yes, keep the lock), predict the
    commit point, the coordinator's txf-1 COMMIT line, phase two forward only, a reader may see the debit first. A no
    vote: presumed abort. Two points of no return. The price: two round trips, 140 ms instead of 70, locks held.
    Moral, an open loop to the dead coordinator, and a check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_amt(self, k, s, color=WHITE):
        new = right_at(M(s, 24, color), SX[k] + SW / 2 - 0.3, ROW_Y)
        old, self.amt[k] = self.amt[k], new
        return [swap(old, new)]

    def log(self, k, s, color=WHITE):
        i = len(self.logs[k])
        m = left_at(M(s, 17, color), SX[k] - SW / 2 + 0.3, LOG_Y[i])
        self.logs[k].append(m)
        return [FadeIn(m, shift=0.08 * RIGHT)]

    def clear_log(self, k):
        olds, self.logs[k] = self.logs[k], []
        return [FadeOut(m) for m in olds]

    def lock(self, k, on=True):
        if on:
            self.locks[k] = padlock([SX[k] - SW / 2 + 1.75, ROW_Y + 0.02, 0])
            return [FadeIn(self.locks[k], scale=0.6)]
        old, self.locks[k] = self.locks[k], None
        return [FadeOut(old, scale=1.4)] if old is not None else []

    def vote(self, k, s, color, name=None):
        name = name or ("wallets" if k == "w" else "payouts")
        new = VGroup(T(name, 19, SC[k]), T(s, 19, color)).arrange(RIGHT, buff=0.3).move_to([0, VOTE_Y[k], 0])
        old, self.votes[k] = self.votes[k], new
        if new is None:
            return []
        return [swap(old, new)]

    def clear_votes(self):
        olds = [v for v in self.votes.values() if v is not None]
        self.votes = {"w": None, "p": None}
        return [FadeOut(v) for v in olds]

    def set_clog(self, s, color=WHITE, size=19, mono=True):
        new = (M if mono else T)(s, size, color).move_to([0, CLOG_Y, 0])
        old, self.clog = self.clog, new
        return [swap(old, new)]

    def clear_clog(self):
        old, self.clog = self.clog, None
        return [FadeOut(old)] if old is not None else []

    def go(self, k, color=YELLOW_M, back=False):
        """A dot runs from the coordinator to server k (a message), or back (an answer)."""
        a = np.array([-CW / 2 if k == "w" else CW / 2, LINK_Y, 0])
        b = np.array([SX[k] + (SW / 2 if k == "w" else -SW / 2), LINK_Y, 0])
        if back:
            a, b = b, a
        d = Dot(radius=0.08, color=color).move_to(a)
        return [Succession(FadeIn(d, run_time=0.05), d.animate(run_time=0.45, rate_func=smooth).move_to(b),
                           FadeOut(d, run_time=0.1))]

    def reader(self, w, p, wc=WHITE, pc=WHITE):
        new = VGroup(T("someone reading both sees:", 20, GREY_B), T("wallet", 20, BLUE_M), M(w, 22, wc),
                     T("café", 20, GOLD_M), M(p, 22, pc)).arrange(RIGHT, buff=0.22)
        new[3].shift(0.25 * RIGHT)
        new[4].shift(0.25 * RIGHT)
        new.move_to([0, READ_Y, 0])
        old, self.rd = self.rd, new
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.clog = self.rd = None
        self.amt = {"w": None, "p": None}
        self.logs = {"w": [], "p": []}
        self.locks = {"w": None, "p": None}
        self.votes = {"w": None, "p": None}
        self.title_card("Everyone promises, then one line decides", "paying across two databases with two-phase commit")

        # ---------------- scene 1: the missing 30 ----------------
        sw_ = server("w", "wallets", "your wallet")
        sp_ = server("p", "payouts", "what the café is owed")
        w_id = left_at(M("w-17", 22), SX["w"] - SW / 2 + 0.3, ROW_Y)
        p_id = left_at(M("m-cafe", 22), SX["p"] - SW / 2 + 0.3, ROW_Y)
        self.steps("Picture paying for a coffee from the money you keep in a café chain's app, your wallet. "
                   "The app says it went through, and your wallet drops from 100.00 to 70.00.", [
            (lambda: [FadeIn(sw_[0]), FadeIn(sw_[1]), FadeIn(sw_[2]), FadeIn(w_id)], 0.8),
            (lambda: self.set_amt("w", "100.00"), 0.5),
            "drops from",
            (lambda: self.set_amt("w", "70.00"), 0.6),
        ])
        self.steps("That evening, the café's owner checks what she's owed. Your 30.00 isn't there. "
                   "It left your wallet, and never arrived.", [
            (lambda: [FadeIn(sp_[0]), FadeIn(sp_[1]), FadeIn(sp_[2]), FadeIn(p_id)], 0.8),
            (lambda: self.set_amt("p", "0.00", RED_M), 0.5),
            "never arrived",
            (lambda: self.reader("70.00", "0.00", WHITE, RED_M), 0.6),
        ])
        self.steps("How can money leave one place and never land in the other? And how do two machines agree "
                   "to do both, or neither?", [
            (lambda: self.cap("both, or neither?", WHITE), 0.6),
        ])

        # ---------------- scene 2: one server is easy; two are not ----------------
        sw_sub2 = T("a database server", 19, GREY_B).move_to(sw_[2])
        sp_sub2 = T("another server", 19, GREY_B).move_to(sp_[2])
        self.steps("The app keeps its records in a database, a program that stores rows of data, a bit like a spreadsheet. "
                   "The wallets live on one database server, a computer called wallets. The shops' balances live on another, called payouts.", [
            (lambda: [*self.uncap(), FadeOut(self.rd), *self.set_amt("w", "100.00"), *self.set_amt("p", "0.00")], 0.6),
            "The wallets live",
            (lambda: [swap(sw_[2], sw_sub2)], 0.6),
            "The shops'",
            (lambda: [swap(sp_[2], sp_sub2)], 0.6),
        ])
        self.rd = None
        self.steps("On one server, this is easy. A transaction groups changes so that all of them happen, or none do. "
                   "It commits, becomes permanent, at one moment: when one line reaches the server's log on disk.", [
            "A transaction",
            (lambda: [FadeIn(sw_[3]), FadeIn(sw_[4])], 0.6),
            "It commits",
            (lambda: self.log("w", "commit"), 0.5),
            (lambda: [Indicate(self.logs["w"][0], color=GREEN_M, scale_factor=1.2)], 0.8),
        ])
        self.steps("But our payment has two halves, on two disks. No single line can commit both.", [
            (lambda: [*self.clear_log("w"), FadeIn(sp_[3]), FadeIn(sp_[4])], 0.6),
            "two halves",
            (lambda: [glow(sw_[0], BLUE_M, 1.02), glow(sp_[0], GOLD_M, 1.02)], 0.9),
            "No single line",
            (lambda: self.cap("no single line can commit both", WHITE), 0.5),
        ])
        crash = tick(False, 0.3).move_to([SX["p"], LOG_Y[1], 0])
        self.steps("So the obvious plan: commit the debit on wallets, then the credit on payouts. "
                   "Now payouts crashes a moment before its commit.", [
            (lambda: self.cap("the obvious plan: commit one side, then the other", WHITE), 0.5),
            "commit the debit",
            (lambda: [*self.log("w", "debit, commit"), *self.set_amt("w", "70.00")], 0.6),
            "then the credit",
            (lambda: self.log("p", "credit ..."), 0.5),
            "Now payouts crashes",
            (lambda: [Create(crash), sp_[0].animate.set_stroke(RED_M)], 0.6),
        ])
        self.steps("You've paid 30.00, and the café got nothing. That's our missing money.", [
            (lambda: [*self.reader("70.00", "0.00", WHITE, RED_M), *self.cap("paid, and never arrived", RED_M)], 0.6),
        ])
        self.steps("Then undo the debit? By then, another payment may already have been approved against your 70.00. "
                   "Putting it back is a new transaction, a refund, and that can fail too. Well... we've just moved the problem.", [
            (lambda: self.cap("undo it? a refund is one more thing that can fail", WHITE), 0.6),
            "Well",
            (lambda: [Wiggle(self.logs["w"][0], scale_value=1.1)], 0.8),
        ])
        self.steps("What we want is this: nobody commits until everybody has promised that they can.", [
            (lambda: [*self.clear_log("w"), *self.clear_log("p"), FadeOut(crash), sp_[0].animate.set_stroke(GOLD_M),
                      *self.set_amt("w", "100.00"), *self.set_amt("p", "0.00"), FadeOut(self.rd)], 0.7),
            "nobody commits",
            (lambda: self.cap("nobody commits until everybody has promised", YELLOW_M), 0.6),
        ])
        self.rd = None

        # ---------------- scene 3: the dinner ----------------
        co = VGroup(frame_box(0, CW, CC), T("coordinator", 26, CC).move_to([0, BOX_TOP - 0.36, 0]),
                    T("runs the payment", 19, GREY_B).move_to([0, BOX_TOP - 0.74, 0]),
                    Line([-CW / 2 + 0.2, DIV_Y, 0], [CW / 2 - 0.2, DIV_Y, 0], stroke_width=1.5, color=GREY_D),
                    T("answers", 17, GREY_B).move_to([0, LOGL_Y, 0]),
                    Line([-CW / 2 + 0.2, -0.3, 0], [CW / 2 - 0.2, -0.3, 0], stroke_width=1.5, color=GREY_D))
        links = VGroup(Line([-CW / 2, LINK_Y, 0], [SX["w"] + SW / 2, LINK_Y, 0], stroke_width=2.5, color=GREY_C),
                       Line([CW / 2, LINK_Y, 0], [SX["p"] - SW / 2, LINK_Y, 0], stroke_width=2.5, color=GREY_C))
        tags = [T("you, organising", 20, GREY_B, slant=ITALIC).move_to([0, TAG_Y, 0]),
                T("a friend", 20, GREY_B, slant=ITALIC).move_to([SX["w"], TAG_Y, 0]),
                T("a friend", 20, GREY_B, slant=ITALIC).move_to([SX["p"], TAG_Y, 0])]
        self.steps("Picture organising a dinner by text. You ask each friend: Friday at eight? "
                   "If you say yes, keep the evening free.", [
            (lambda: [*self.uncap(), FadeIn(co[0]), FadeIn(co[3]), FadeIn(co[4]), FadeIn(co[5]), Create(links),
                      FadeIn(tags[0])], 0.8),
            "You ask",
            (lambda: [FadeIn(tags[1]), FadeIn(tags[2]), *self.go("w"), *self.go("p")], 0.6),
            "Friday at eight",
            (lambda: self.cap("\"Friday at eight? If yes, keep the evening free.\"", YELLOW_M), 0.5),
        ])
        self.steps("Only when everyone has said yes do you write dinner is on in your diary, and then text everyone. "
                   "If anyone says no, you text off.", [
            "everyone has said yes",
            (lambda: [*self.go("w", GREEN_M, back=True), *self.go("p", GREEN_M, back=True)], 0.6),
            (lambda: [*self.vote("w", "yes", GREEN_M, "a friend"), *self.vote("p", "yes", GREEN_M, "a friend")], 0.4),
            "in your diary",
            (lambda: self.set_clog("diary: dinner is on", YELLOW_M, 20, mono=False), 0.6),
            "If anyone says no",
            (lambda: self.cap("anyone says no: \"off\"", WHITE), 0.5),
        ])
        self.steps("Let's map it. You're the coordinator: the program running the payment, which decides how it ends. "
                   "The friends are the participants: the servers that hold the data. "
                   "And the whole thing gets one id that everyone shares, txf-1.", [
            (lambda: [*self.uncap(), *self.clear_votes(), *self.clear_clog()], 0.5),
            "You're the coordinator",
            (lambda: [FadeIn(co[1]), FadeIn(co[2]), glow(co[0], CC, 1.02)], 0.7),
            "The friends are",
            (lambda: [glow(sw_[0], BLUE_M, 1.02), glow(sp_[0], GOLD_M, 1.02),
                      *self.cap("you = coordinator,   friends = participants", WHITE)], 0.8),
            "one id",
            (lambda: self.cap("one shared id:  txf-1", WHITE), 0.5),
        ])

        # ---------------- scene 4: phase one, and the commit point ----------------
        self.steps("Phase one is prepare. The coordinator sends each server its changes, and asks: can you commit?", [
            (lambda: self.cap("phase one: prepare", YELLOW_M), 0.5),
            "sends each server",
            (lambda: [*self.go("w"), *self.go("p")], 0.6),
            (lambda: [*self.lock("w"), *self.lock("p")], 0.5),
            "can you commit",
            (lambda: [*self.go("w"), *self.go("p")], 0.6),
        ])
        self.steps("wallets checks its rules, writes the changes and a line saying prepared to its log, "
                   "makes sure the disk has them, and answers yes.", [
            "writes the changes",
            (lambda: self.log("w", "txf-1  -30.00"), 0.5),
            "a line saying",
            (lambda: self.log("w", "txf-1  prepared"), 0.5),
            "answers yes",
            (lambda: [*self.go("w", GREEN_M, back=True), *self.vote("w", "yes", GREEN_M)], 0.6),
        ])
        self.steps("That yes is a promise. Whatever happens next, even a crash and a restart, it will commit if told to. "
                   "So it can't give up on its own any more, and it keeps a lock on your wallet's row, "
                   "a mark that stops anyone else changing it. That's the friend keeping Friday free.", [
            (lambda: [Indicate(self.logs["w"][1], color=GREEN_M, scale_factor=1.15)], 0.8),
            "it keeps a lock",
            (lambda: [self.locks["w"].animate(rate_func=there_and_back).scale(1.6)], 0.8),
            "That's the friend",
            (lambda: self.cap("a yes = keeping Friday free", YELLOW_M), 0.5),
        ])
        self.steps("payouts does the same, and says yes.", [
            (lambda: [*self.log("p", "txf-1  +30.00"), *self.log("p", "txf-1  prepared")], 0.6),
            (lambda: [*self.go("p", GREEN_M, back=True), *self.vote("p", "yes", GREEN_M), *self.uncap()], 0.6),
        ])
        self.steps("Both servers said yes, and neither has committed. So at what moment is the payment really committed? "
                   "Pause and guess.", [
            (lambda: [*self.reader("100.00", "0.00")], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The moment the coordinator writes one line to its own log, txf-1 COMMIT, and the disk has it. "
                   "That one line is the commit point. It's the note in your diary.", [
            (lambda: self.uncap(), 0.3),
            "txf-1 COMMIT",
            (lambda: self.set_clog("txf-1 COMMIT", GREEN_M, 24), 0.6),
            "That one line",
            (lambda: [*self.cap("the commit point: one line in the coordinator's log", GREEN_M),
                      Indicate(self.clog, color=GREEN_M, scale_factor=1.25)], 0.9),
        ])
        self.steps("Neither server has changed yet, but the outcome is fixed.", [
            (lambda: [glow(sw_[0], BLUE_M, 1.02), glow(sp_[0], GOLD_M, 1.02), Indicate(self.rd, color=WHITE, scale_factor=1.05)], 0.9),
        ])

        # ---------------- scene 5: phase two ----------------
        self.steps("Phase two is commit. The coordinator tells wallets to commit. It commits, and lets go of the lock.", [
            (lambda: self.cap("phase two: commit", YELLOW_M), 0.5),
            "tells wallets",
            (lambda: self.go("w", GREEN_M), 0.6),
            "It commits",
            (lambda: [*self.log("w", "txf-1  committed", GREEN_M), *self.set_amt("w", "70.00"), *self.lock("w", False)], 0.7),
        ])
        self.steps("For a moment, someone reading both servers sees the debit without the credit. "
                   "The outcome is all or nothing. It just doesn't show on both servers at the same instant.", [
            (lambda: self.reader("70.00", "0.00", WHITE, YELLOW_M), 0.6),
            "all or nothing",
            (lambda: self.cap("all or nothing, but not at the same instant", WHITE), 0.5),
        ])
        self.steps("Then payouts commits too. If payouts were out of reach, the coordinator would keep resending, "
                   "for minutes or days, because once the line is written, the only way is forward.", [
            (lambda: self.go("p", GREEN_M), 0.6),
            (lambda: [*self.log("p", "txf-1  committed", GREEN_M), *self.set_amt("p", "30.00", GREEN_M), *self.lock("p", False),
                      *self.reader("70.00", "30.00", WHITE, GREEN_M)], 0.7),
            "If payouts were",
            (lambda: [LaggedStart(*[st for _ in range(3) for st in self.go("p", GREEN_M)], lag_ratio=0.5)], 1.6),
            "the only way",
            (lambda: self.cap("after the line: only forward", WHITE), 0.5),
        ])
        self.steps("That's two-phase commit. Everyone promises first, then one line decides.", [
            (lambda: self.cap("two-phase commit: everyone promises, then one line decides", YELLOW_M), 0.7),
        ], after=0.6)

        # ---------------- scene 6: a no, and presumed abort ----------------
        self.steps("Now a different run. This time payouts finds a payout entry for txf-1 already there, "
                   "so one of its rules fails, and it answers no.", [
            (lambda: [*self.uncap(), *self.clear_log("w"), *self.clear_log("p"), *self.clear_votes(), *self.clear_clog(),
                      *self.set_amt("w", "100.00"), *self.set_amt("p", "0.00"), *self.reader("100.00", "0.00")], 0.7),
            (lambda: [*self.go("w"), *self.go("p"), *self.lock("w"), *self.lock("p")], 0.6),
            (lambda: [*self.log("w", "txf-1  -30.00"), *self.log("w", "txf-1  prepared"),
                      *self.go("w", GREEN_M, back=True), *self.vote("w", "yes", GREEN_M)], 0.6),
            "already there",
            (lambda: self.log("p", "txf-1  already paid", RED_M), 0.5),
            "answers no",
            (lambda: [*self.go("p", RED_M, back=True), *self.vote("p", "no", RED_M), *self.lock("p", False)], 0.6),
        ])
        self.steps("The coordinator writes nothing at all, and tells wallets to roll back, to undo its prepared changes. "
                   "Your wallet stays at 100.00.", [
            "writes nothing",
            (lambda: self.set_clog("(nothing written)", GREY_B, 20, mono=False), 0.6),
            "tells wallets",
            (lambda: self.go("w", RED_M), 0.6),
            (lambda: [*self.log("w", "txf-1  rolled back", RED_M), *self.lock("w", False)], 0.6),
            "Your wallet stays",
            (lambda: [Indicate(self.amt["w"], color=WHITE, scale_factor=1.2)], 0.8),
        ])
        self.steps("A payment with no line in the log counts as aborted. That's called presumed abort, and it's safe, "
                   "because nobody can commit without the line. A server that doesn't answer in time counts as a no, too.", [
            "presumed abort",
            (lambda: self.cap("presumed abort: no line means aborted", WHITE), 0.6),
            "doesn't answer",
            (lambda: self.cap("no answer in time = no", WHITE), 0.5),
        ])
        self.steps("So notice the two points of no return. A server's yes takes away its own right to abort. "
                   "The coordinator's line takes away everyone's.", [
            (lambda: [*self.clear_log("w"), *self.clear_log("p"), *self.clear_votes(), *self.uncap(),
                      *self.vote("w", "yes", GREEN_M), *self.vote("p", "yes", GREEN_M)], 0.6),
            "A server's yes",
            (lambda: [Indicate(self.votes["w"][1], color=GREEN_M, scale_factor=1.3), Indicate(self.votes["p"][1], color=GREEN_M, scale_factor=1.3),
                      *self.cap("1. a yes: that server can no longer abort", WHITE)], 0.9),
            "The coordinator's line",
            (lambda: [*self.set_clog("txf-1 COMMIT", GREEN_M, 24), *self.cap("2. the line: nobody can", WHITE)], 0.7),
        ])

        # ---------------- scene 7: the price ----------------
        self.steps("Now the price. A normal commit is one round trip, a message there and its answer back, "
                   "plus one wait for the disk. Two-phase commit needs two round trips to every server, and three disk waits in a row.", [
            (lambda: self.cap("one commit: 1 round trip, 1 disk wait", WHITE), 0.5),
            "Two-phase commit needs",
            (lambda: [*self.cap("two-phase commit: 2 round trips, 3 disk waits in a row", YELLOW_M),
                      LaggedStart(*[st for _ in range(2) for k in ("w", "p") for st in (self.go(k) + self.go(k, GREEN_M, back=True))],
                                  lag_ratio=0.3)], 2.2),
        ])
        self.steps("Between data centres at the two ends of a continent, a round trip takes about 70 milliseconds. "
                   "So each payment spends about 140 on the network, instead of 70. And every prepared server holds its locks "
                   "the whole time.", [
            "about 70",
            (lambda: self.cap("one round trip across a continent: about 70 ms", WHITE), 0.5),
            "So each payment",
            (lambda: self.cap("each payment: about 140 ms on the network, not 70", YELLOW_M), 0.5),
            "holds its locks",
            (lambda: [*self.lock("w"), *self.lock("p")], 0.6),
        ])
        self.steps("It's like a friend who can't accept any other plan until you text back. Hope you don't lose your phone. "
                   "What happens when the coordinator dies right after the yeses? That's next.", [
            "Hope you",
            (lambda: [Wiggle(co[0], scale_value=1.03)], 0.9),
            "What happens",
            (lambda: [*self.clear_clog(), co[0].animate.set_stroke(GREY_D), *self.cap("the coordinator dies after the yeses?  next", WHITE)], 0.7),
        ], after=0.5)

        # ---------------- scene 8: moral and a check ----------------
        self.steps("So where did the 30.00 go? Into the gap between two separate commits. "
                   "Two-phase commit closes it: every server promises first, and one line on disk decides.", [
            (lambda: [co[0].animate.set_stroke(CC), *self.lock("w", False), *self.lock("p", False), *self.clear_votes(),
                      *self.cap("where did the 30.00 go?  between two separate commits", WHITE)], 0.7),
            "every server promises",
            (lambda: [*self.vote("w", "yes", GREEN_M), *self.vote("p", "yes", GREEN_M)], 0.6),
            "one line on disk",
            (lambda: [*self.set_clog("txf-1 COMMIT", GREEN_M, 24), *self.cap("promise first, then one line decides", YELLOW_M)], 0.7),
        ], after=0.5)
        crash2 = tick(False, 0.3).move_to([SX["p"] + 1.2, LOG_Y[1], 0])
        self.steps("One quick check. payouts said yes, then crashed and restarted before phase two. "
                   "The coordinator's log says txf-1 COMMIT. What must payouts do? Pause and think.", [
            (lambda: [*self.uncap(), *self.log("p", "txf-1  +30.00"), *self.log("p", "txf-1  prepared"),
                      *self.log("w", "txf-1  committed", GREEN_M), *self.set_amt("w", "70.00"), *self.set_amt("p", "0.00"), *self.reader("70.00", "0.00", WHITE, YELLOW_M)], 0.6),
            "then crashed",
            (lambda: [Create(crash2), sp_[0].animate.set_stroke(RED_M)], 0.6),
            "and restarted",
            (lambda: [FadeOut(crash2), sp_[0].animate.set_stroke(GOLD_M)], 0.6),
            "The coordinator's log",
            (lambda: [Indicate(self.clog, color=GREEN_M, scale_factor=1.2)], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Commit. Its yes was a promise that survives a crash, and the line has already decided.", [
            (lambda: [*self.uncap(), *self.go("p", GREEN_M)], 0.6),
            (lambda: [*self.log("p", "txf-1  committed", GREEN_M), *self.set_amt("p", "30.00", GREEN_M),
                      *self.reader("70.00", "30.00", WHITE, GREEN_M)], 0.6),
            "survives a crash",
            (lambda: self.cap("a yes survives a crash; the line decides", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.wait(2.0)
