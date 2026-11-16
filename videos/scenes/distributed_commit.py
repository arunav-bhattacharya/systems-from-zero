from sfz import *

SAY.insert(0, (r"\bA-1001\b", "A ten oh one"))
SAY.insert(0, (r"\bM-2001\b", "M twenty oh one"))
SAY.insert(0, (r"\bCockroachDB\b", "cockroach D B"))
SAY.insert(0, (r"\bT1\b", "T one"))

RC = {1: np.array([-3.85, 1.0, 0]), 2: np.array([3.85, 1.0, 0])}
RW, RH = 5.5, 3.0
DATA_Y, REC_Y, RAFT_Y = 1.72, 0.92, 0.02
AX_Y = -2.7


def ax(t):
    """x on the timestamp axis for t milliseconds."""
    return -6.0 + 0.02 * t


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.05):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def rng(k, title):
    c = RC[k]
    r = RoundedRectangle(corner_radius=0.16, width=RW, height=RH, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to(c)
    t = left_at(T(title, 21, GREY_B), c[0] - RW / 2 + 0.3, c[1] + RH / 2 - 0.32)
    return VGroup(r, t)


def row(k, key, val, color=WHITE):
    c = RC[k]
    x0 = c[0] - RW / 2 + 0.35
    return VGroup(left_at(M(key, 22, GREY_A), x0, DATA_Y), left_at(M(val, 22, color), x0 + 1.25, DATA_Y))


def intent(k, s, color=GOLD_M):
    c = RC[k]
    return chip(s, color, 18).move_to([c[0] + 1.2, DATA_Y, 0])


def replicas(k):
    c = RC[k]
    out = VGroup()
    for i, name in enumerate(["leader", "replica", "replica"]):
        col = BLUE_M if i == 0 else GREY_B
        b = RoundedRectangle(corner_radius=0.08, width=1.35, height=0.44, stroke_color=col, stroke_width=2.2)
        b.set_fill(fillc(col), 1).move_to([c[0] + (i - 1) * 1.6, RAFT_Y, 0])
        out.add(VGroup(b, T(name, 17, WHITE if i == 0 else GREY_B).move_to(b)))
    return out


def record(s, color=GREY_B):
    return mbox(s, color, h=0.5, size=17).move_to([RC[1][0], REC_Y, 0])


def replicate(reps, color=GOLD_M, rt=0.6):
    """Dots from the leader to both replicas, and acks back."""
    L = reps[0][0]
    out = []
    for f in (reps[1][0], reps[2][0]):
        out.append(travel(Line(L.get_right() if f.get_center()[0] > L.get_center()[0] else L.get_left(),
                               f.get_left()), color, rt))
    return out


def status(s, color=GREY_B, y=-1.35, size=21):
    return T(s, size, color).move_to([0, y, 0])


class DistributedCommit(Base):
    """cons-06, sections 0 and 3: a transfer of 100 from A-1001 (range 1) to M-2001 (range 2), each range its own Raft
    group. Separate writes lose money on a crash; instead T1 writes intents at timestamp 100 that point at a transaction
    record in range 1, and commits by flipping that record (one Raft write). An auditor whose clock runs 120 ms slow
    reads at 30, finds M-2001's value at 100 inside its uncertainty interval (max offset 500 ms) and restarts above it."""

    def construct(self):
        self.title_card("Distributed commit", "one record decides, and a reader that isn't sure restarts")

        r1, r2 = rng(1, "range 1: accounts"), rng(2, "range 2: merchants")
        a = row(1, "A-1001", "400")
        m = row(2, "M-2001", "0")
        gw = mbox("transfer T1: 100 from A-1001 to M-2001", WHITE, h=0.52, size=19).move_to([0, 3.15, 0])
        self.steps("A transfer moves 100 from A-1001 to merchant M-2001. The two rows live in different ranges, on different machines.", [
            (lambda: [FadeIn(gw, shift=0.1 * DOWN)], 0.7),
            "The two rows",
            (lambda: [FadeIn(r1), FadeIn(r2)], 0.8),
            (lambda: [FadeIn(a), FadeIn(m)], 0.7),
        ])

        tot = status("A-1001 + M-2001 = 400")
        lost = status("A-1001 + M-2001 = 300: 100 vanished", RED_M)
        crash = tick(False, 0.22).next_to(gw, RIGHT, buff=0.2)
        self.steps("The simplest plan writes each row on its own. Debit A-1001, crash before the credit, and 100 has vanished.", [
            (lambda: [FadeIn(tot)], 0.5),
            "Debit A-1001",
            (lambda: [travel(Line(gw.get_bottom() + 1.6 * LEFT, a[1].get_top()), WHITE, 0.6)], 0.7),
            (lambda: [Transform(a[1], row(1, "A-1001", "300", RED_M)[1])], 0.5),
            "crash before",
            (lambda: [Create(crash), gw[0].animate.set_stroke(RED_M)], 0.6),
            "and 100",
            (lambda: [Transform(tot, lost)], 0.6),
        ])

        rep1, rep2 = replicas(1), replicas(2)
        self.steps("So start again. Each range is copied to three servers by its own Raft group, with its own leader.", [
            (lambda: [FadeOut(tot), FadeOut(crash), gw[0].animate.set_stroke(WHITE),
                      Transform(a[1], row(1, "A-1001", "400")[1])], 0.8),
            "Each range",
            (lambda: [LaggedStart(*[FadeIn(x, shift=0.1 * UP) for x in [*rep1, *rep2]], lag_ratio=0.12)], 1.2),
            "with its own leader",
            (lambda: [glow(rep1[0][0], BLUE_M, 1.08), glow(rep2[0][0], BLUE_M, 1.08)], 0.8),
        ])

        rec = record("T1 record: PENDING")
        ts = T("timestamp 100", 20, GOLD_M).next_to(gw, DOWN, buff=0.12)
        self.steps("The transfer takes a timestamp, 100, and a transaction record in range 1, marked pending.", [
            (lambda: [FadeIn(ts, shift=0.1 * DOWN)], 0.6),
            "and a transaction record",
            (lambda: [FadeIn(rec, scale=0.9)], 0.7),
            "marked pending",
            (lambda: [glow(rec[0], GREY_A, 1.06)], 0.6),
        ])

        i1, i2 = intent(1, "intent: 300, see T1"), intent(2, "intent: 100, see T1")
        pt1 = DashedLine(i1.get_bottom() + 0.04 * DOWN, rec.get_top() + np.array([1.2, 0.04, 0]), dash_length=0.07,
                         stroke_width=2, color=GOLD_M)
        py = 0.52
        pt2 = DashedVMobject(VMobject().set_points_as_corners([i2.get_bottom() + 0.04 * DOWN, [i2.get_center()[0], py, 0],
                                                               [rec.get_right()[0] - 0.3, py, 0], [rec.get_right()[0] - 0.3, rec.get_bottom()[1] - 0.04, 0]]),
                             num_dashes=90).set_stroke(GOLD_M, 2)
        self.steps("Then it writes intents: provisional values that point at that record. Each range's Raft group copies its own.", [
            (lambda: [travel(Line(gw.get_bottom() + 1.6 * LEFT, i1.get_top()), GOLD_M, 0.6),
                      travel(Line(gw.get_bottom() + 1.6 * RIGHT, i2.get_top()), GOLD_M, 0.6)], 0.7),
            (lambda: [FadeIn(i1, scale=0.9), FadeIn(i2, scale=0.9)], 0.6),
            "that point at",
            (lambda: [Create(pt1), Create(pt2)], 0.8),
            "Each range's Raft",
            (lambda: [*replicate(rep1), *replicate(rep2)], 0.8),
            (lambda: [*replicate(rep1, GREEN_M), *replicate(rep2, GREEN_M)], 0.6),
        ])

        rec2 = record("T1 record: COMMITTED at 100", GREEN_M)
        self.steps("To commit, the gateway flips one thing, the record, from pending to committed. That's a single Raft write.", [
            (lambda: [travel(Line(gw.get_bottom() + 1.6 * LEFT, rec.get_top() + 0.4 * UP), GREEN_M, 0.6)], 0.7),
            "from pending",
            (lambda: [Transform(rec, rec2)], 0.8),
            "That's a single",
            (lambda: [*replicate(rep1, GREEN_M, 0.7)], 0.8),
            (lambda: [glow(rec[0], GREEN_M, 1.06)], 0.6),
        ])

        self.steps("Both intents now count as committed, though nobody touched them. They're cleaned up later.", [
            (lambda: [i1[0].animate.set_stroke(GREEN_M).set_fill(GREEN_M, 0.18), i2[0].animate.set_stroke(GREEN_M).set_fill(GREEN_M, 0.18),
                      pt1.animate.set_color(GREEN_M), pt2.animate.set_color(GREEN_M)], 0.8),
            "They're cleaned up",
            (lambda: [FadeOut(i1), FadeOut(i2), FadeOut(pt1), FadeOut(pt2), Transform(a[1], row(1, "A-1001", "300", GREEN_M)[1]),
                      Transform(m[1], row(2, "M-2001", "100", GREEN_M)[1])], 0.8),
        ])

        decide = status("one record decides: both rows, or neither", GREEN_M)
        self.steps("Had the gateway crashed before the flip, both intents would be thrown away. One record decides.", [
            (lambda: [glow(rec[0], GREY_A, 1.06)], 0.8),
            "One record decides",
            (lambda: [FadeIn(decide, shift=0.1 * UP)], 0.7),
        ])

        # ---- a reader with a slow clock -----------------------------------------------------------------------------------
        aud = mbox("auditor: clock 120 ms slow", TEAL_M, h=0.5, size=18).move_to([3.85, -1.35, 0])
        axis = Line([ax(0), AX_Y, 0], [ax(600), AX_Y, 0], stroke_width=2.5, color=GREY_B)
        axl = T("timestamp, ms", 17, GREY_C).move_to([ax(600) - 0.6, AX_Y - 0.32, 0])
        rmark = Line([ax(30), AX_Y - 0.2, 0], [ax(30), AX_Y + 0.2, 0], stroke_width=4, color=TEAL_M)
        rlab = T("reads at 30", 18, TEAL_M).move_to([ax(30) + 0.15, AX_Y - 0.42, 0])
        self.steps("Right after the commit, an auditor starts on a server whose clock runs 120 ms slow. It reads at timestamp 30.", [
            (lambda: [FadeOut(decide), FadeIn(aud, shift=0.1 * UP)], 0.7),
            "It reads at",
            (lambda: [Create(axis), FadeIn(axl)], 0.7),
            (lambda: [Create(rmark), FadeIn(rlab)], 0.6),
        ])

        vmark = Line([ax(100), AX_Y - 0.2, 0], [ax(100), AX_Y + 0.2, 0], stroke_width=4, color=GOLD_M)
        vlab = T("M-2001 = 100, written at 100", 18, GOLD_M).move_to([ax(100) + 0.55, AX_Y + 0.45, 0])
        q = T("in its future?", 20, GREY_A).move_to([ax(100) + 3.6, AX_Y + 0.45, 0])
        self.steps("It finds M-2001's new value, written at 100. At 30, that looks like the future. Skip it, and the audit misses the transfer.", [
            (lambda: [travel(Line(aud.get_top(), RC[2] + np.array([0, -RH / 2, 0])), TEAL_M, 0.6)], 0.7),
            (lambda: [Create(vmark), FadeIn(vlab)], 0.6),
            "that looks like",
            (lambda: [FadeIn(q)], 0.5),
            "Skip it",
            (lambda: [q.animate.set_color(RED_M), Transform(m[1], row(2, "M-2001", "0?", RED_M)[1])], 0.7),
        ])

        band = Rectangle(width=ax(530) - ax(30), height=0.42, stroke_width=0).set_fill(TEAL_M, 0.22)
        band.move_to([(ax(30) + ax(530)) / 2, AX_Y, 0])
        blab = T("uncertain: 30 to 530", 18, TEAL_M).move_to([ax(400), AX_Y + 0.45, 0])
        self.steps("But CockroachDB allows clocks to differ by up to 500 milliseconds, the max offset. "
                   "So a value written between 30 and 530 may have committed before the read began.", [
            (lambda: [FadeOut(q), Transform(m[1], row(2, "M-2001", "100", GREEN_M)[1])], 0.6),
            "So a value",
            (lambda: [FadeIn(band), FadeIn(blab)], 0.9),
            "may have committed",
            (lambda: [glow(vmark, GOLD_M, 1.0)], 0.6),
        ])

        rmark2 = Line([ax(101), AX_Y - 0.2, 0], [ax(101), AX_Y + 0.2, 0], stroke_width=4, color=GREEN_M)
        rlab2 = T("restarts at 101: sees M-2001 = 100", 18, GREEN_M).move_to([ax(101) + 1.75, AX_Y - 0.42, 0])
        self.steps("The auditor can't skip an uncertain value. It moves its timestamp past 100 and restarts, and sees the transfer.", [
            (lambda: [glow(aud[0], TEAL_M, 1.05)], 0.6),
            "It moves",
            (lambda: [Transform(rmark, rmark2), FadeOut(rlab)], 0.9),
            "and sees",
            (lambda: [FadeIn(rlab2), travel(Line(aud.get_top(), RC[2] + np.array([0, -RH / 2, 0])), GREEN_M, 0.6),
                      glow(m[1], GREEN_M, 1.15)], 0.8),
        ])

        self.steps("Had it met a pending intent, it would wait on the record instead. It never guesses.", [
            (lambda: [glow(rec[0], GREY_A, 1.06)], 0.8),
            "never guesses",
            (lambda: [glow(aud[0], TEAL_M, 1.05)], 0.7),
        ])

        self.steps("Intents on every range, one replicated record that decides, and readers that wait or restart instead of guessing.", [
            (lambda: [glow(r1[0], GOLD_M, 1.02), glow(r2[0], GOLD_M, 1.02)], 0.9),
            "one replicated record",
            (lambda: [glow(rec[0], GREEN_M, 1.08)], 0.8),
            "and readers",
            (lambda: [glow(band, TEAL_M, 1.0), glow(aud[0], TEAL_M, 1.05)], 0.9),
        ])
        self.wait(0.6)
