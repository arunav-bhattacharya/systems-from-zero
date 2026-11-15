from sfz import *

SAY.insert(0, (r"\bSELECT FOR UPDATE\b", "select for update"))
SAY.insert(0, (r"\bFOR UPDATE\b", "for update"))
SAY.insert(0, (r"\bSKIP LOCKED\b", "skip locked"))

def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def via(points, color=YELLOW_M, run_time=0.9):
    """A dot that runs along a polyline and stays invisible until its turn."""
    pts = [np.array(p, dtype=float) for p in points]
    path = VMobject().set_points_as_corners(pts)
    d = Dot(radius=0.08, color=color).move_to(pts[0]).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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



AX, BX_ = -4.3, 4.3                           # the two transaction lanes
TY = [1.3, 0.6, -0.1, -0.8, -1.5]             # time slots, top to bottom
ROW = np.array([0, 2.55, 0])                  # account 109
JX, JY = 1.6, [1.35, 0.65, -0.05, -0.75, -1.45]  # jobs table rows
WX, WY = -4.4, [0.65, -0.45, -1.55]           # workers


def step(s, lane, k, color=GREY_B):
    return chip(s, color, 17, mono=True).move_to([AX if lane == "A" else BX_, TY[k], 0])


def acct(bal, color=WHITE, note=None):
    r = RoundedRectangle(corner_radius=0.14, width=4.0, height=1.0, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to(ROW)
    t = T("account 109", 20, GREY_B).move_to(ROW + 0.25 * UP)
    b = T(f"balance: {bal}", 28).move_to(ROW + 0.17 * DOWN)
    return VGroup(r, t, b)


def lane_title(s, lane, color):
    return T(s, 21, color).move_to([AX if lane == "A" else BX_, ROW[1], 0])


def job(i, k, state="queued", color=GREY_B):
    p = np.array([JX, JY[k], 0])
    r = RoundedRectangle(corner_radius=0.08, width=3.8, height=0.56, stroke_color=color, stroke_width=2.5).set_fill(fill(color), 1)
    r.move_to(p)
    a = M(f"job {i}", 18).move_to(p + [-1.9 + 0.2 + M(f"job {i}", 18).width / 2, 0, 0])
    s = T(state, 18, color)
    s.move_to(p + [1.9 - 0.2 - s.width / 2, 0, 0])
    return VGroup(r, a, s)


def worker(n, k, color=WHITE):
    return box(f"worker {n}", color, w=1.9, h=0.6, size=20).move_to([WX, WY[k], 0])


def link(wk, jk, color):
    return Arrow([WX + 0.95 + 0.08, WY[wk], 0], [JX - 1.9 - 0.08, JY[jk], 0], buff=0, stroke_width=3, color=color,
                 max_tip_length_to_length_ratio=0.06)


def result(s, color, y=-2.45):
    return T(s, 24, color).move_to([0, y, 0])


class LostUpdate(Base):
    """txn-02, section 0 (with sections 1 and 3): two debits of 1,000 on account 109 (5,000) both read 5,000 and both
    write 4,000, so one vanishes. SELECT ... FOR UPDATE makes the fee's read wait for the payment's commit and see 4,000,
    ending at 3,000. A job queue claims with FOR UPDATE and two workers wait on job 2; SKIP LOCKED sends them to jobs 3 and 5."""

    def construct(self):
        self.title_card("Lost updates", "read, compute, write, and the row lock that fixes it")

        row = acct("5,000")
        ta = lane_title("Tx A: card payment, 1,000", "A", BLUE_M)
        tb = lane_title("Tx B: monthly fee, 1,000", "B", PURPLE_M)
        tarrow = Arrow([0, 1.45, 0], [0, -1.7, 0], buff=0, stroke_width=2.5, color=GREY_D, max_tip_length_to_length_ratio=0.05)
        tlab = T("time", 18, GREY_C).next_to(tarrow, RIGHT, buff=0.12).shift(1.2 * UP)
        goal = result("two debits: it should end at 3,000", GREY_B)
        self.steps("Two services debit Ivy's account 109 at the same moment: a card payment of 1,000 and a monthly fee of 1,000. "
                   "The balance is 5,000, so it should end at 3,000.", [
            (lambda: [FadeIn(row)], 0.7),
            "a card payment",
            (lambda: [FadeIn(ta, shift=0.1 * RIGHT)], 0.6),
            "and a monthly fee",
            (lambda: [FadeIn(tb, shift=0.1 * LEFT)], 0.6),
            "so it should end",
            (lambda: [FadeIn(goal), Create(tarrow), FadeIn(tlab)], 0.8),
        ])

        a1, b1 = step("SELECT → 5000", "A", 0), step("SELECT → 5000", "B", 0)
        a2, b2 = step("b = 5000 - 1000", "A", 1), step("b = 5000 - 1000", "B", 1)
        rd = ROW + 0.5 * DOWN
        self.steps("Each one reads the balance, subtracts in Kotlin, and writes the result. Both read 5,000.", [
            (lambda: [FadeOut(goal)], 0.4),
            "Both read",
            (lambda: [via([rd + 1.2 * LEFT, a1.get_right()], BLUE_M, 0.6), via([rd + 1.2 * RIGHT, b1.get_left()], PURPLE_M, 0.6)], 0.6),
            (lambda: [FadeIn(a1), FadeIn(b1)], 0.5),
            (lambda: [FadeIn(a2), FadeIn(b2)], 0.6),
        ])

        a3 = step("UPDATE 4000; COMMIT", "A", 2, BLUE_M)
        b3 = step("UPDATE 4000; COMMIT", "B", 3, PURPLE_M)
        self.steps("The payment writes 4,000 and commits. Then the fee writes 4,000 and commits.", [
            (lambda: [FadeIn(a3)], 0.5),
            (lambda: [via([a3.get_right(), rd + 1.2 * LEFT], BLUE_M, 0.6)], 0.6),
            (lambda: [Transform(row, acct("4,000"))], 0.5),
            "Then the fee",
            (lambda: [FadeIn(b3)], 0.5),
            (lambda: [via([b3.get_left(), rd + 1.2 * RIGHT], PURPLE_M, 0.6)], 0.6),
            (lambda: [Transform(row, acct("4,000", RED_M))], 0.5),
        ])

        bad = result("two debits ran, the balance fell by 1,000", RED_M)
        lost = chip("lost update", RED_M, 22).move_to([0, -3.1, 0])
        self.steps("Two debits ran, and the balance fell by only 1,000. That's a lost update: the second write erased the first. "
                   "Nothing failed, so no log line tells you.", [
            (lambda: [FadeIn(bad)], 0.7),
            "That's a lost update",
            (lambda: [FadeIn(lost, shift=0.1 * UP), glow(a3[0], RED_M, 1.05)], 0.8),
        ])

        self.steps("The database did put the two writes in order. But the fee's 4,000 came from a read that was "
                   "no longer true.", [
            (lambda: [glow(a3[0], BLUE_M, 1.05)], 0.6),
            (lambda: [glow(b3[0], PURPLE_M, 1.05)], 0.6),
            "But the fee's",
            (lambda: [b1.animate.set_color(RED_M), glow(b1[0], RED_M, 1.08)], 0.9),
        ])

        old = VGroup(a1, a2, a3, b1, b2, b3, bad, lost)
        f1 = step("SELECT … FOR UPDATE → 5000", "A", 0, BLUE_M)
        lockl = T("locked by Tx A", 19, BLUE_M).move_to(ROW + 0.8 * DOWN)
        self.steps("The fix: lock the row when you read it, with SELECT FOR UPDATE. Start again from 5,000. "
                   "The payment reads 5,000 and locks row 109.", [
            (lambda: [FadeOut(old), Transform(row, acct("5,000"))], 0.8),
            "The payment reads",
            (lambda: [FadeIn(f1), via([rd + 1.2 * LEFT, f1.get_right()], BLUE_M, 0.6)], 0.6),
            (lambda: [Transform(row, acct("5,000", BLUE_M)), FadeIn(lockl)], 0.6),
        ])

        g1 = step("SELECT … FOR UPDATE", "B", 0, PURPLE_M)
        wline = DashedLine([BX_, TY[0] - 0.32, 0], [BX_, TY[3] + 0.32, 0], dash_length=0.1, stroke_width=3, color=PURPLE_M)
        wlab = T("waits for the lock", 18, PURPLE_M).next_to(wline, RIGHT, buff=0.15)
        f2 = step("b = 5000 - 1000", "A", 1)
        self.steps("The fee asks for the same row, and its read now waits for that lock.", [
            (lambda: [FadeIn(g1), FadeIn(f2)], 0.6),
            "now waits",
            (lambda: [Create(wline), FadeIn(wlab)], 1.2),
        ])

        f3 = step("UPDATE 4000; COMMIT", "A", 2, BLUE_M)
        g4 = step("→ 4000, b = 4000 - 1000", "B", 3, PURPLE_M)
        self.steps("The payment writes 4,000 and commits, which releases the lock. "
                   "Only then does the fee's read return, and it sees 4,000.", [
            (lambda: [FadeIn(f3)], 0.5),
            (lambda: [via([f3.get_right(), rd + 1.2 * LEFT], BLUE_M, 0.6)], 0.6),
            (lambda: [Transform(row, acct("4,000"))], 0.4),
            "which releases",
            (lambda: [FadeOut(lockl)], 0.5),
            "Only then",
            (lambda: [via([rd + 1.2 * RIGHT, g4.get_left()], PURPLE_M, 0.7)], 0.7),
            (lambda: [FadeIn(g4)], 0.5),
        ])

        g5 = step("UPDATE 3000; COMMIT", "B", 4, PURPLE_M)
        good = result("both debits count", GREEN_M)
        self.steps("It writes 3,000. Both debits count.", [
            (lambda: [FadeIn(g5)], 0.4),
            (lambda: [via([g5.get_left(), rd + 1.2 * RIGHT], PURPLE_M, 0.6)], 0.6),
            (lambda: [Transform(row, acct("3,000", GREEN_M)), FadeIn(good)], 0.6),
        ])

        # ---- the job queue ----------------------------------------------------------------------------------------
        ids = [2, 3, 5, 7, 8]
        jobs = [job(i, k) for k, i in enumerate(ids)]
        jt = T("jobs: 5 queued and due, job 2 oldest", 20, GREY_A).move_to([JX, 2.1, 0])
        ws = [worker(n + 1, n) for n in range(3)]
        q = chip("claim: … FOR UPDATE", GREY_B, 18, mono=True).move_to([WX, 2.1, 0])
        lk = [link(n, 0, GREY_B) for n in range(3)]
        lane = VGroup(f1, f2, f3, g1, g4, g5, wline, wlab, good, ta, tb, tarrow, tlab)
        self.steps("A job queue has the same bug. Five jobs are due, and three workers each claim the oldest one with FOR UPDATE. "
                   "All three pick job 2.", [
            (lambda: [FadeOut(lane), FadeOut(row)], 0.7),
            (lambda: [FadeIn(jt), LaggedStart(*[FadeIn(j, shift=0.1 * LEFT) for j in jobs], lag_ratio=0.12)], 1.0),
            "and three workers",
            (lambda: [LaggedStart(*[FadeIn(w) for w in ws], lag_ratio=0.2), FadeIn(q)], 0.9),
            "All three pick",
            (lambda: [*[GrowArrow(a) for a in lk]], 0.8),
        ])

        dl = [DashedLine(lk[k].get_start(), lk[k].get_end(), dash_length=0.1, stroke_width=3, color=RED_M) for k in (1, 2)]
        self.steps("Worker 1 locks it. The other two wait for the whole job, about 2 seconds, "
                   "so three workers run at the speed of one.", [
            (lambda: [Transform(jobs[0], job(2, 0, "running: worker 1", BLUE_M)), lk[0].animate.set_color(BLUE_M),
                      ws[0][0].animate.set_stroke(BLUE_M)], 0.7),
            "The other two",
            (lambda: [FadeOut(lk[1]), FadeOut(lk[2]), Create(dl[0]), Create(dl[1]),
                      ws[1][1].animate.set_color(RED_M), ws[2][1].animate.set_color(RED_M)], 0.8),
            "so three workers",
            (lambda: [glow(ws[1][0], RED_M), glow(ws[2][0], RED_M)], 0.9),
        ])

        q2 = chip("claim: … FOR UPDATE SKIP LOCKED", GREEN_M, 18, mono=True).move_to([WX + 0.5, 2.1, 0])
        self.steps("But a worker doesn't need job 2. Any due job will do. "
                   "With SKIP LOCKED, a locked row is skipped instead of waited on.", [
            "Any due job",
            (lambda: [*[glow(j[0], GREY_B, 1.03) for j in jobs[1:]]], 0.8),
            "With SKIP LOCKED",
            (lambda: [Transform(q, q2)], 0.8),
        ])

        n1 = link(1, 1, PURPLE_M)
        n2 = link(2, 2, GOLD_M)
        self.steps("Worker 2 skips job 2 and locks job 3. Worker 3 skips both and locks job 5. "
                   "Nobody waits, and three jobs run at once.", [
            (lambda: [FadeOut(dl[0]), GrowArrow(n1), ws[1][1].animate.set_color(WHITE)], 0.7),
            (lambda: [Transform(jobs[1], job(3, 1, "running: worker 2", PURPLE_M)), ws[1][0].animate.set_stroke(PURPLE_M)], 0.5),
            "Worker 3",
            (lambda: [FadeOut(dl[1]), GrowArrow(n2), ws[2][1].animate.set_color(WHITE)], 0.7),
            (lambda: [Transform(jobs[2], job(5, 2, "running: worker 3", GOLD_M)), ws[2][0].animate.set_stroke(GOLD_M)], 0.5),
            "Nobody waits",
            (lambda: [glow(jobs[0][0], BLUE_M, 1.03), glow(jobs[1][0], PURPLE_M, 1.03), glow(jobs[2][0], GOLD_M, 1.03)], 0.9),
        ])

        self.steps("Reading, computing and writing back loses updates. Lock the row you read, "
                   "and when any row will do, skip the locked ones.", [
            "Lock the row",
            (lambda: [glow(jobs[0][0], BLUE_M, 1.03)], 0.8),
            "skip the locked",
            (lambda: [glow(q[0], GREEN_M, 1.04)], 0.9),
        ])
        self.wait(0.6)
