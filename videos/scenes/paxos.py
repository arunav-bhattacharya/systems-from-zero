from sfz import *

SAY.insert(0, (r"\bpay-(\d+)\b", lambda m: "pay " + " ".join(m.group(1))))
SAY.insert(0, (r"\bP([12])\b", r"P \1"))
SAY.insert(0, (r"\bA([123])\b", r"A \1"))
SAY.insert(0, (r"\b([12])\.([12])\b", r"\1 point \2"))

P1_C, P2_C = BLUE_M, GOLD_M
PX = 5.1                                 # proposers at (-PX, 0) and (PX, 0)
AY = [2.0, 0.0, -2.0]                    # acceptors' centres, x = 0
AW, AH = 4.4, 1.45
TOP, BOT = 3.3, -3.35                    # caption rows
BAR = np.array([PX, -1.75, 0])           # countdown bar, under P2's status


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


class Acceptor:
    """A clerk's notebook: a box with its name and two lines, promised and accepted."""

    def __init__(self, i):
        self.i = i
        c = np.array([0, AY[i], 0])
        self.c = c
        self.r = RoundedRectangle(corner_radius=0.14, width=AW, height=AH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
        self.n = T(f"A{i + 1}", 32).move_to(c + LEFT * (AW / 2 - 0.5))
        kx = -AW / 2 + 0.95
        self.k1 = T("promised", 24, GREY_B)
        self.k1.move_to(c + np.array([kx + self.k1.width / 2, 0.27, 0]))
        self.k2 = T("accepted", 24, GREY_B)
        self.k2.move_to(c + np.array([kx + self.k2.width / 2, -0.27, 0]))
        self.vx = kx + max(self.k1.width, self.k2.width) + 0.3
        self.v1 = self.val("-", 0.27)
        self.v2 = self.val("-", -0.27)

    @property
    def g(self):
        return VGroup(self.r, self.n, self.k1, self.k2, self.v1, self.v2)

    def val(self, s, dy, color=WHITE):
        v = T(s, 24, color)
        return v.move_to(self.c + np.array([self.vx + v.width / 2, dy, 0]))

    def promise(self, s):
        new = self.val(s, 0.27, YELLOW_M)
        old, self.v1 = self.v1, new
        return swap(old, new)

    def accept(self, s):
        new = self.val(s, -0.27, GREEN_M if "capture" in s else WHITE)
        old, self.v2 = self.v2, new
        return swap(old, new)

    def calm(self):
        return self.v1.animate.set_color(WHITE)


def proposer(name, want, color, x):
    r = RoundedRectangle(corner_radius=0.14, width=2.8, height=1.2, stroke_color=color, stroke_width=3)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14), opacity=1).move_to([x, 0, 0])
    n = T(name, 32).move_to([x, 0.22, 0])
    w = T(want, 22, GREY_B).move_to([x, -0.26, 0])
    return VGroup(r, n, w)


def msg(a, b, color):
    return edge_arrow(a[0], b.r, color, buff=0.1)


def go(ar, color, rt=0.7):
    return travel(ar, color, rt)


def ret(ar, color, rt=0.7):
    return travel(Line(ar.get_end(), ar.get_start()), color, rt)


def lost(ar, color):
    d = Dot(radius=0.08, color=color).move_to(ar.get_start())
    mid = ar.get_start() + 0.55 * (ar.get_end() - ar.get_start())
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(ar.get_start(), mid), run_time=0.6), FadeOut(d, run_time=0.25))


class Paxos(Base):
    """cons-03, section 3: the stepper's single-decree Paxos run for pay-77, told as three clerks with notebooks and two
    managers. P1 gets capture chosen with ballot 1.1 and crashes; P2's ballot 2.2 hears about it from A2 and must
    propose capture, not void. Two majorities share A2. Then the Try-it's 500 hostile runs: 0, 114 and 36 splits."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, TOP, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def bot(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, BOT, 0])
        old, self.botm = self.botm, new
        return [swap(old, new)]

    def unbot(self):
        old, self.botm = self.botm, None
        return [FadeOut(old)] if old is not None else []

    def status(self, k, s, color):
        x = -PX if k == 1 else PX
        new = fit(T(s, 22, color), 2.9).move_to([x, -1.0, 0])
        old = self.st.get(k)
        self.st[k] = new
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        bar = Line(BAR + LEFT * 1.1, BAR + RIGHT * 1.1, stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.botm = None
        self.st = {}
        self.title_card("Two majorities always share someone", "one decision that survives a crash")

        p1 = proposer("P1", "wants capture", P1_C, -PX)
        p2 = proposer("P2", "wants void", P2_C, PX)
        qm = T("?", 60, YELLOW_M).move_to([0, 0, 0])

        # ---------------- scene 1: the question ----------------
        self.steps("A payment, pay-77, needs one decision. One program wants it captured: the money moves to the shop. "
                   "Another wants it voided: cancelled. Never both.", [
            (lambda: self.cap("pay-77: capture or void?", WHITE), 0.6),
            "One program",
            (lambda: [FadeIn(p1, shift=0.2 * RIGHT)], 0.7),
            "Another wants",
            (lambda: [FadeIn(p2, shift=0.2 * LEFT)], 0.7),
            "Never both",
            (lambda: self.bot("one or the other, never both", WHITE), 0.6),
        ])
        self.steps("Three computers keep the decision, messages get lost, and any program can stop at any moment. So if the "
                   "program that started the decision crashes halfway, how does the next one finish it without changing the "
                   "answer? Hold that question.", [
            "messages get lost",
            (lambda: self.bot("messages get lost; anything can stop", WHITE), 0.6),
            "So if the",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "crashes halfway",
            (lambda: [Indicate(p1[0], color=RED_M, scale_factor=1.05)], 0.8),
            "Hold that",
            (lambda: self.bot("the first one crashes halfway: how does the next finish without changing the answer?", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 2: clerks and notebooks ----------------
        acc = [Acceptor(i) for i in range(3)]
        self.steps("Picture three clerks with notebooks, and two managers giving them instructions. The managers, called "
                   "proposers, are the programs: P1 wants capture, P2 wants void. The clerks are the three computers, "
                   "called acceptors.", [
            (lambda: [FadeOut(qm), *self.unbot(), *self.cap("three clerks with notebooks, two managers", WHITE)], 0.6),
            "three clerks",
            (lambda: [LaggedStart(*[FadeIn(a.g, shift=0.15 * DOWN) for a in acc], lag_ratio=0.25)], 1.2),
            "called proposers",

            (lambda: self.cap("managers = proposers", WHITE), 0.5),
            (lambda: [Indicate(p1[1], color=P1_C), Indicate(p2[1], color=P2_C)], 0.8),
            "The clerks are",
            (lambda: self.cap("managers = proposers      clerks = acceptors", WHITE), 0.5),
        ])
        self.steps("Each notebook has two lines: the request number the clerk has promised to listen to, and the last "
                   "instruction it wrote down. The notebook is the computer's disk, so it survives a restart.", [
            "two lines",
            (lambda: [*[Indicate(a.k1, color=YELLOW_M) for a in acc]], 0.9),
            "and the last",
            (lambda: [*[Indicate(a.k2, color=YELLOW_M) for a in acc]], 0.9),
            "The notebook is",
            (lambda: self.cap("notebook = the computer's disk: it survives a restart", WHITE), 0.6),
        ])
        self.steps("Each request carries a number, round dot proposer, so 2.2 is round 2 from P2, and beats 1.1. A value is "
                   "chosen once two clerks out of three, a majority, have written it under the same number.", [
            (lambda: self.cap("request number: round.proposer      2.2 beats 1.1", WHITE), 0.6),
            "A value is",
            (lambda: self.cap("chosen: a majority (2 of 3) wrote the same value under the same number", YELLOW_M), 0.7),
        ], after=0.3)
        self.stamp("map")

        # ---------------- scene 3: P1's two rounds ----------------
        a1 = [msg(p1, acc[i], P1_C) for i in range(3)]
        self.steps("Let's play it slowly. P1 picks number 1.1 and sends a prepare to every clerk. It means: promise to "
                   "ignore anything lower than 1.1, and tell me what you've already written.", [
            "P1 picks",
            (lambda: [*self.status(1, "sent prepare 1.1", P1_C), *self.cap("round 1: prepare", WHITE), *[GrowArrow(a) for a in a1]], 0.8),
            (lambda: [go(a1[0], P1_C), go(a1[1], P1_C)], 0.8),
            "promise to",
            (lambda: [Indicate(acc[0].k1, color=YELLOW_M), Indicate(acc[1].k1, color=YELLOW_M)], 0.9),
            "and tell me",
            (lambda: [Indicate(acc[0].k2, color=YELLOW_M), Indicate(acc[1].k2, color=YELLOW_M)], 0.9),
        ])
        self.steps("A1 and A2 write promised 1.1, and answer with a promise. Neither has written any value. "
                   "Two out of three is a majority, so P1 doesn't wait for A3.", [
            (lambda: [acc[0].promise("1.1"), acc[1].promise("1.1")], 0.7),
            "answer with",
            (lambda: [ret(a1[0], WHITE), ret(a1[1], WHITE)], 0.8),
            "Two out of three",
            (lambda: self.status(1, "2 promises: a majority", P1_C), 0.6),
            "doesn't wait",
            (lambda: [a1[2].animate.set_opacity(0.3), acc[2].g.animate.set_opacity(0.5)], 0.6),
        ])
        no3 = tick(False, 0.18).move_to(a1[2].get_start() + 0.55 * (a1[2].get_end() - a1[2].get_start()))
        self.steps("No one reported a value, so P1 may use its own. It sends accept 1.1, capture. A1 and A2 write it down. "
                   "The copy to A3 is lost.", [
            "It sends accept",
            (lambda: [*self.status(1, "sent accept 1.1 capture", P1_C), *self.cap("round 2: accept", WHITE),
                      a1[2].animate.set_opacity(1), acc[2].g.animate.set_opacity(1), acc[0].calm(), acc[1].calm()], 0.6),
            (lambda: [go(a1[0], P1_C), go(a1[1], P1_C), lost(a1[2], P1_C)], 0.9),
            "A1 and A2 write",
            (lambda: [acc[0].accept("1.1 capture"), acc[1].accept("1.1 capture")], 0.7),
            "The copy to A3",
            (lambda: [Create(no3)], 0.5),
        ])
        p1x = tick(False, 0.2).move_to(p1.get_corner(UR) + np.array([-0.25, -0.25, 0]))
        self.steps("Two notebooks out of three now say 1.1 capture, so capture is chosen. And then P1 crashes, before a single "
                   "reply reaches it.", [
            (lambda: [*self.bot("capture is chosen", GREEN_M), Indicate(acc[0].v2, color=GREEN_M), Indicate(acc[1].v2, color=GREEN_M)], 1.0),
            "And then P1 crashes",
            (lambda: [FadeOut(VGroup(*a1)), FadeOut(no3), p1.animate.set_opacity(0.35), *self.status(1, "crashed", RED_M), Create(p1x)], 0.8),
        ])
        self.steps("So P1 had the best moment of its career and never found out. Nobody knows yet, and that's the point: "
                   "chosen is a fact about the notebooks, not about who heard.", [
            "Nobody knows yet",
            (lambda: self.bot("capture is chosen, and nobody knows yet", GREEN_M), 0.6),
            "chosen is a fact",
            (lambda: self.cap("chosen is a fact about the notebooks, not about who heard", WHITE), 0.6),
        ], after=0.3)
        self.stamp("p1done")

        # ---------------- scene 4: the pain, and P2's first round ----------------
        self.steps("Now P2 hears nothing, and its timer runs out. The obvious move is to start fresh and push void. But "
                   "capture is already chosen, so some services would move the money while others cancel it.", [
            (lambda: [Indicate(p2[0], color=P2_C, scale_factor=1.05)], 0.8),
            "The obvious move",
            (lambda: self.cap("the obvious move: start fresh and push void", PURPLE_M), 0.6),
            "so some services",
            (lambda: self.bot("money moved and cancelled: two answers", RED_M), 0.6),
        ])
        a2 = [msg(p2, acc[i], P2_C) for i in range(3)]
        slow = T("slow", 22, GREY_B).move_to([-AW / 2 - 0.6, AY[0], 0])
        self.steps("What we want is for the next manager to find out what may already be decided, before saying anything. "
                   "That's the first round's job. P2 picks a higher number, 2.2, and sends prepare. A1 is slow, so only "
                   "A2 and A3 answer.", [
            (lambda: [*self.unbot(), *self.cap("wanted: find out what may be decided, before saying anything", YELLOW_M)], 0.6),
            "P2 picks",
            (lambda: [*self.status(2, "sent prepare 2.2", P2_C), *[GrowArrow(a) for a in a2]], 0.8),
            (lambda: [go(a2[1], P2_C), go(a2[2], P2_C)], 0.8),
            "A1 is slow",
            (lambda: [a2[0].animate.set_opacity(0.25), acc[0].g.animate.set_opacity(0.5), FadeIn(slow)], 0.6),
        ])
        self.steps("A3 promises 2.2, with nothing written. A2 raises its promise to 2.2, and reports what it wrote: "
                   "1.1, capture.", [
            (lambda: [acc[2].promise("2.2")], 0.6),
            (lambda: [ret(a2[2], WHITE)], 0.7),
            "A2 raises",
            (lambda: [acc[1].promise("2.2")], 0.6),
            "and reports",
            (lambda: [ret(a2[1], GREEN_M), Indicate(acc[1].v2, color=GREEN_M)], 0.9),
            (lambda: self.status(2, "A2 reports 1.1 capture", P2_C), 0.5),
        ], after=0.3)

        # ---------------- scene 5: predict, then the rule ----------------
        self.steps("So P2 wants void, and one of its two promises carries capture. What must it propose? Pause and guess.", [
            (lambda: self.cap("what must P2 propose?  pause and guess", YELLOW_M), 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("Capture. The rule is: propose the value with the highest number among the promises, or your own if "
                   "there's none. It's a shift handover. The colleague who takes over finishes the job that's already "
                   "signed, and keeps their own opinion for later.", [
            (lambda: self.status(2, "proposes capture", GREEN_M), 0.5),
            "The rule is",
            (lambda: self.cap("the rule: propose the highest-numbered value reported, or your own if none", YELLOW_M), 0.7),
            "or your own",
            (lambda: [Indicate(p2[2], color=RED_M)], 0.8),
            "It's a shift handover",
            (lambda: self.bot("a shift handover: finish the job that's already signed", WHITE), 0.6),
        ])
        self.steps("P2 sends accept 2.2, capture. A2 and A3 write it down, and P2 learns the decision: capture, the same "
                   "value that was chosen when P1 crashed.", [
            (lambda: [acc[1].calm(), acc[2].calm(), *self.unbot()], 0.4),
            (lambda: [go(a2[1], P2_C), go(a2[2], P2_C)], 0.8),
            "A2 and A3 write",
            (lambda: [acc[1].accept("2.2 capture"), acc[2].accept("2.2 capture")], 0.7),
            (lambda: [ret(a2[1], WHITE), ret(a2[2], WHITE)], 0.7),
            "and P2 learns",
            (lambda: self.status(2, "learned: capture", GREEN_M), 0.6),
        ], after=0.3)
        self.stamp("p2done")

        # ---------------- scene 6: why it had to be capture ----------------
        m1 = SurroundingRectangle(VGroup(acc[0].r, acc[1].r), color=P1_C, buff=0.12, corner_radius=0.2, stroke_width=3)
        m2 = SurroundingRectangle(VGroup(acc[1].r, acc[2].r), color=P2_C, buff=0.2, corner_radius=0.24, stroke_width=3)
        m1_l = T("majority for 1.1", 22, P1_C)
        m1_l.move_to([m1.get_left()[0] - 0.3 - m1_l.width / 2, 1.9, 0])
        m2_l = T("majority for 2.2", 22, P2_C)
        m2_l.move_to([m2.get_right()[0] + 0.3 + m2_l.width / 2, -1.9, 0])
        self.steps("Was that luck? No. P1's majority was A1 and A2. P2's majority was A2 and A3.", [
            (lambda: [FadeOut(VGroup(*a2)), FadeOut(slow), acc[0].g.animate.set_opacity(1), *self.cap("was that luck?", WHITE)], 0.6),
            "P1's majority",
            (lambda: [Create(m1), FadeIn(m1_l)], 0.8),
            "P2's majority",
            (lambda: [Create(m2), FadeIn(m2_l)], 0.8),
        ])
        self.steps("Any two majorities of three share at least one clerk, here A2. A value that's chosen sits in a majority of "
                   "notebooks, so the next manager's majority always includes someone who wrote it down. "
                   "Once chosen, it stays chosen.", [
            (lambda: self.cap("any two majorities of three share a clerk", YELLOW_M), 0.6),
            "here A2",
            (lambda: [Indicate(acc[1].n, color=YELLOW_M, scale_factor=1.4), Indicate(acc[1].v2, color=GREEN_M)], 1.0),
            "Once chosen",
            (lambda: [*self.bot("once chosen, it stays chosen", GREEN_M),
                      *[Indicate(a.v2, color=GREEN_M) for a in acc]], 0.9),
        ], after=0.3)
        self.stamp("overlap")

        # ---------------- scene 7: the name ----------------
        self.steps("What we just played is Paxos, Leslie Lamport's method for deciding one value. The request number is "
                   "called a ballot, and the two rounds are prepare and promise, then accept.", [
            (lambda: [*self.unbot(), *self.cap("Paxos: deciding one value (Leslie Lamport)", TEAL_M)], 0.6),
            "is called a ballot",
            (lambda: self.bot("request number = ballot      round 1: prepare, promise      round 2: accept", WHITE), 0.6),
        ])
        self.steps("Lamport first told it as a story about a Greek island's parliament. Readers struggled, so his next paper "
                   "was called Paxos Made Simple. A title like that is mostly an apology. The whole method is the two rounds "
                   "you just watched.", [
            "Paxos Made Simple",
            (lambda: self.cap("first a Greek island's parliament; then \"Paxos Made Simple\"", TEAL_M), 0.6),
            "The whole method",
            (lambda: self.cap("the whole method: two rounds", TEAL_M), 0.5),
        ], after=0.3)

        # ---------------- scene 8: break it on purpose ----------------
        stage = VGroup(p1, p1x, p2, *[a.g for a in acc], m1, m2, m1_l, m2_l, self.st[1], self.st[2])
        rows = [("Paxos as written", "0", GREEN_M),
                ("proposers push their own value", "114", RED_M),
                ("acceptors forget their notebook", "36", RED_M)]
        head = T("500 hostile runs: how many chose two different values?", 26, WHITE).move_to([0, 1.7, 0])
        tbl = []
        for k, (a, b, c) in enumerate(rows):
            y = 0.6 - 1.0 * k
            la = T(a, 28, WHITE).move_to([-0.6, y, 0], aligned_edge=RIGHT)
            la.move_to([-0.6 - la.width / 2, y, 0])
            lb = T(b, 36, c)
            lb.move_to([0.9 + lb.width / 2, y, 0])
            tbl.append(VGroup(la, lb))
        setup = T("5 acceptors, 3 proposers, 20% of messages lost, 10% sent twice, crashes", 22, GREY_B).move_to([0, 2.45, 0])
        self.steps("Now let's break it on purpose. The lesson's demo plays 500 runs with five acceptors, lost and repeated "
                   "messages, and crashes everywhere.", [
            (lambda: [FadeOut(stage), *self.unbot(), *self.cap("break it on purpose", PURPLE_M)], 0.7),
            "500 runs",
            (lambda: [FadeIn(head)], 0.5),
            "five acceptors",
            (lambda: [FadeIn(setup)], 0.5),
        ])
        self.steps("Paxos as written: zero runs out of 500 chose two values. Now let proposers ignore the promises and push "
                   "their own value: 114 runs split. Now let acceptors forget their notebook when they restart, as if they "
                   "answered before writing to disk: 36 runs split.", [
            (lambda: [FadeIn(tbl[0][0])], 0.4),
            "zero runs",
            (lambda: [FadeIn(tbl[0][1], scale=0.7)], 0.4),
            "Now let proposers",
            (lambda: [FadeIn(tbl[1][0])], 0.4),
            "114 runs",
            (lambda: [FadeIn(tbl[1][1], scale=0.7)], 0.4),
            "Now let acceptors",
            (lambda: [FadeIn(tbl[2][0])], 0.4),
            "36 runs",
            (lambda: [FadeIn(tbl[2][1], scale=0.7)], 0.4),
        ])
        self.steps("Well, that's a lot of payments both captured and cancelled. So every rule matters: read what's written, "
                   "carry the highest forward, and write to disk before you answer.", [
            "every rule",
            (lambda: self.bot("read what's written; carry the highest forward; write to disk before you answer", YELLOW_M), 0.7),
        ], after=0.3)
        self.stamp("break")

        # ---------------- scene 9: the guardrail ----------------
        costs = VGroup(*[chip(s, c, 26) for s, c in [
            ("one decision: 2 round trips", RED_M),
            ("a majority must be up: 3 survive 1 failure, 5 survive 2", RED_M),
            ("Multi-Paxos: a steady leader, then 1 round trip per command", TEAL_M)]]).arrange(DOWN, buff=0.45).move_to([0, 0.2, 0])
        self.steps("So what does it cost? One decision takes two round trips. A majority must be up: three acceptors survive "
                   "one failure, five survive two.", [
            (lambda: [FadeOut(VGroup(head, setup, *tbl)), *self.unbot(), *self.cap("what it costs", WHITE)], 0.6),
            "One decision",
            (lambda: [FadeIn(costs[0], shift=0.1 * UP)], 0.5),
            "A majority must",
            (lambda: [FadeIn(costs[1], shift=0.1 * UP)], 0.5),
        ])
        self.steps("And plain Paxos decides one value, but a real system needs a log of them. So real systems run Multi-Paxos: "
                   "a steady leader runs the first round once, then each command costs one round trip. Google's lock "
                   "service, Chubby, works this way.", [
            "a log of them",
            (lambda: self.cap("a real system needs a log: many values in order", WHITE), 0.6),
            "So real systems",
            (lambda: [FadeIn(costs[2], shift=0.1 * UP)], 0.5),
            "Google's lock service",
            (lambda: self.bot("Chubby, Google's lock service, works this way", GREY_B), 0.6),
        ], after=0.3)

        # ---------------- scene 10: the moral, and a check ----------------
        for a in acc:
            a.g.set_opacity(1)
        stage2 = VGroup(p1, p1x, p2, *[a.g for a in acc], self.st[1], self.st[2])
        self.steps("So the moral: before you propose, ask a majority what they've written, and carry the highest forward. "
                   "Two majorities always share a notebook, so a crash can delay a chosen value, never change it.", [
            (lambda: [FadeOut(costs), *self.unbot(), FadeIn(stage2), *self.cap("ask a majority first; carry the highest forward", YELLOW_M)], 0.8),
            "Two majorities",
            (lambda: self.bot("a crash can delay a chosen value, never change it", GREEN_M), 0.6),
        ], after=0.3)
        self.steps("One quick check. Suppose P2's promises had come from A1 and A3 instead. Would it still have proposed "
                   "capture? Pause and think.", [
            (lambda: [*self.unbot(), *self.cap("promises from A1 and A3: still capture?  pause and think", YELLOW_M)], 0.6),
            "from A1 and A3",
            (lambda: [Indicate(acc[0].n, color=P2_C, scale_factor=1.4), Indicate(acc[2].n, color=P2_C, scale_factor=1.4)], 0.9),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. A1 wrote 1.1 capture, and A1 is in that majority too. Any two clerks out of three include A1 or A2, "
                   "so every majority hears about capture.", [
            (lambda: [Indicate(acc[0].v2, color=GREEN_M, scale_factor=1.3)], 0.8),
            "Any two clerks",
            (lambda: self.bot("every majority includes A1 or A2: everyone hears about capture", GREEN_M), 0.6),
        ], after=0.3)
        self.play(*self.cap("two majorities always share someone", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
