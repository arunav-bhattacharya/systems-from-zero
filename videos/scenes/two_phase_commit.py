from sfz import *

SAY.insert(0, (r"\bw-17\b", "W seventeen"))

C_C = PURPLE_M
WX, PX, SY = -3.6, 3.6, -0.75          # wallets and payouts centres
CY = 2.45                              # coordinator centre


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


def panel(title, c, w, h, color):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK, opacity=1).move_to(c)
    t = T(title, 28, color).move_to(np.array(c) + UP * (h / 2 - 0.36))
    return VGroup(r, t)


def line(s, x, y, color=WHITE, size=26, mono=False):
    return (M if mono else T)(s, size - (4 if mono else 0), color).move_to([x, y, 0])


def padlock(color=RED_M, s=1.0):
    body = RoundedRectangle(corner_radius=0.04, width=0.3, height=0.24, stroke_color=color, stroke_width=3)
    body.set_fill(color, opacity=0.35)
    shackle = Arc(radius=0.1, start_angle=0, angle=PI, stroke_color=color, stroke_width=3).next_to(body, UP, buff=0)
    return VGroup(body, shackle).scale(s)


def msg(s, color):
    return chip(s, color, 22)


class TwoPhaseCommit(Base):
    """txn-07, sections 1-2: two-phase commit, then the coordinator that crashes after prepare,
    leaving the participants in doubt and holding their locks."""

    def construct(self):
        self.title_card("Two-phase commit", "every server promises, then one log line decides")

        wal = panel("wallets", [WX, SY, 0], 4.6, 1.9, BLUE_M)
        pay = panel("payouts", [PX, SY, 0], 4.6, 1.9, GOLD_M)
        wrow = line("w-17:  100.00 → 70.00", WX + 0.2, SY - 0.05)
        prow = line("m-cafe:  + 30.00", PX + 0.2, SY - 0.05)
        wst = line("working", WX, SY - 0.55, GREY_B, 24)
        pst = line("working", PX, SY - 0.55, GREY_B, 24)
        self.steps("A coffee purchase moves 30 from wallet w-17 to the cafe. The debit is on one database server, wallets, "
                   "and the credit on another, payouts.", [
            "The debit",
            (lambda: [FadeIn(wal), FadeIn(wrow), FadeIn(wst)], 1.0),
            "and the credit",
            (lambda: [FadeIn(pay), FadeIn(prow), FadeIn(pst)], 1.0),
        ])

        def status(st, s, color):
            return Transform(st, line(s, st.get_x(), SY - 0.55, color, 24))

        crash = tick(False, 0.3).move_to([PX + 1.7, SY + 1.4, 0])
        band = T("the customer paid, the cafe got nothing", 28, RED_M).move_to([0, -2.55, 0])
        self.steps("Both must happen, or neither. If wallets commits first and payouts then crashes, the customer has paid and the cafe got nothing.", [
            "If wallets",
            (lambda: [status(wst, "committed", GREEN_M)], 0.8),
            "and payouts",
            (lambda: [Create(crash), pay[0].animate.set_stroke(RED_M), status(pst, "crashed", RED_M)], 0.8),
            "the customer",
            (lambda: [FadeIn(band, shift=0.15 * UP)], 0.8),
        ])

        # ---- the coordinator -------------------------------------------------------------------------------
        coord = panel("coordinator", [0, CY, 0], 5.2, 1.25, C_C)
        clog = line("log:  empty", 0, CY - 0.2, GREY_B, 26, mono=True)
        self.steps("Two-phase commit adds a coordinator: a process that runs the transaction and decides how it ends.", [
            (lambda: [FadeOut(band), FadeOut(crash), pay[0].animate.set_stroke(GOLD_M),
                      status(wst, "working", GREY_B), status(pst, "working", GREY_B)], 0.8),
            "adds a coordinator",
            (lambda: [FadeIn(coord, shift=0.2 * DOWN), FadeIn(clog)], 1.0),
        ])

        def down(x_side, color=C_C):
            s = coord[0].get_bottom() + RIGHT * (1.7 if x_side > 0 else -1.7)
            e = (pay if x_side > 0 else wal)[0].get_top() + RIGHT * (-0.9 if x_side > 0 else 0.9)
            return Arrow(s, e, buff=0.12, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12)

        aw, ap = down(-1), down(1)

        def label(ar, s, color, side):
            return msg(s, color).move_to(ar.get_center() + np.array([1.25 * side, 0.1, 0]))

        phase = T("phase 1: prepare", 30, C_C).move_to([0, -2.55, 0])
        q_w, q_p = label(aw, "prepare?", C_C, -1), label(ap, "prepare?", C_C, 1)
        self.steps("Phase one is prepare. The coordinator sends each server its changes, then asks if it can commit.", [
            (lambda: [FadeIn(phase, shift=0.15 * UP)], 0.8),
            "The coordinator",
            (lambda: [GrowArrow(aw), GrowArrow(ap)], 0.8),
            "then asks",
            (lambda: [travel(aw, C_C, 0.6), travel(ap, C_C, 0.6), FadeIn(q_w), FadeIn(q_p)], 0.9),
        ])

        yes_w = label(aw, "yes", GREEN_M, -1)
        lk_w = padlock().next_to(wrow, LEFT, buff=0.2)
        self.steps("Wallets checks its rules, and writes the changes to its log on disk, marked prepared. Then it votes yes.", [
            (lambda: [status(wst, "prepared", YELLOW_M)], 0.9),
            "Then it votes",
            (lambda: [travel(Line(aw.get_end(), aw.get_start()), GREEN_M, 0.6), Transform(q_w, yes_w)], 0.9),
        ])
        self.steps("That yes is a promise. Wallets can't abort on its own anymore, and it keeps its lock on w-17.", [
            (lambda: [Indicate(q_w, color=GREEN_M, scale_factor=1.1)], 0.9),
            "and it keeps",
            (lambda: [FadeIn(lk_w, scale=1.4), status(wst, "prepared, locked", YELLOW_M)], 0.9),
        ])

        yes_p = label(ap, "yes", GREEN_M, 1)
        lk_p = padlock().next_to(prow, LEFT, buff=0.2)
        self.steps("Payouts does the same, and votes yes too.", [
            (lambda: [status(pst, "prepared, locked", YELLOW_M), FadeIn(lk_p, scale=1.4)], 0.8),
            (lambda: [travel(Line(ap.get_end(), ap.get_start()), GREEN_M, 0.6), Transform(q_p, yes_p)], 0.8),
        ])

        clog_c = line("log:  txf-1 COMMIT", 0, CY - 0.2, GREEN_M, 26, mono=True)
        self.steps("Every vote is yes, so the coordinator writes commit to its own log on disk. "
                   "That line is the moment the whole transfer commits.", [
            "so the coordinator",
            (lambda: [Transform(clog, clog_c)], 1.0),
            "That line",
            (lambda: [Circumscribe(clog, color=GREEN_M, buff=0.12)], 1.2),
        ])

        phase2 = T("phase 2: commit", 30, C_C).move_to([0, -2.55, 0])
        c_w, c_p = label(aw, "commit", C_C, -1), label(ap, "commit", C_C, 1)
        self.steps("Phase two: the coordinator tells both servers to commit. Each one commits, and drops its lock.", [
            (lambda: [Transform(phase, phase2), Transform(q_w, c_w), Transform(q_p, c_p)], 0.8),
            (lambda: [travel(aw, C_C, 0.6), travel(ap, C_C, 0.6)], 0.7),
            "Each one",
            (lambda: [status(wst, "committed", GREEN_M), status(pst, "committed", GREEN_M), FadeOut(lk_w), FadeOut(lk_p)], 0.9),
        ])

        # ---- the coordinator dies ------------------------------------------------------------------------
        phase3 = T("run it again", 30, GREY_B).move_to([0, -2.55, 0])
        dead = tick(False, 0.38).next_to(coord, RIGHT, buff=0.3)
        y_w, y_p = label(aw, "yes", GREEN_M, -1), label(ap, "yes", GREEN_M, 1)
        self.steps("Now run it again. Both servers vote yes, the coordinator logs commit, "
                   "and then it crashes before telling anyone.", [
            (lambda: [Transform(phase, phase3), Transform(clog, line("log:  empty", 0, CY - 0.2, GREY_B, 26, mono=True)),
                      FadeOut(q_w), FadeOut(q_p), status(wst, "working", GREY_B), status(pst, "working", GREY_B)], 0.9),
            "Both servers",
            (lambda: [FadeIn(y_w), FadeIn(y_p), FadeIn(lk_w), FadeIn(lk_p),
                      status(wst, "prepared, locked", YELLOW_M), status(pst, "prepared, locked", YELLOW_M)], 1.0),
            "the coordinator logs",
            (lambda: [Transform(clog, line("log:  txf-1 COMMIT", 0, CY - 0.2, GREEN_M, 26, mono=True))], 0.8),
            "and then",
            (lambda: [Create(dead), coord[0].animate.set_stroke(RED_M), coord[1].animate.set_color(RED_M),
                      FadeOut(aw), FadeOut(ap), FadeOut(y_w), FadeOut(y_p)], 1.0),
        ])

        doubt = T("in doubt", 30, RED_M).move_to([0, -2.55, 0])
        self.steps("Payouts has promised to commit if told to, and nobody is telling it anything. It's in doubt.", [
            (lambda: [Indicate(pst, color=YELLOW_M)], 1.0),
            "It's in doubt",
            (lambda: [Transform(phase, doubt), status(pst, "in doubt, locked", RED_M), status(wst, "in doubt, locked", RED_M)], 0.9),
        ])

        why1 = T("commit?  maybe wallets voted no", 26, GREY_B)
        why2 = T("abort?  maybe the log says COMMIT", 26, GREY_B)
        whys = VGroup(why1, why2).arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([PX - 0.1, 1.0, 0])
        self.steps("It can't commit: maybe the wallets server voted no. It can't abort either: maybe the coordinator logged commit, "
                   "and wallets has already committed. So it waits.", [
            (lambda: [FadeIn(why1, shift=0.15 * UP)], 0.8),
            "It can't abort",
            (lambda: [FadeIn(why2, shift=0.15 * UP)], 0.8),
        ])

        qs = VGroup(*[chip(f"purchase {i}", GOLD_M, 22) for i in (1, 2, 3)]).arrange(RIGHT, buff=0.2)
        qs.next_to(pay, DOWN, buff=0.35).align_to(pay, RIGHT)
        q_l = T("waiting on m-cafe", 22, RED_M).next_to(qs, LEFT, buff=0.3)
        self.steps("While it waits, it holds its locks, so every purchase at that cafe queues. "
                   "Restarting the database doesn't help: the prepared transaction comes back from disk, locks and all.", [
            (lambda: [FadeOut(phase), LaggedStart(*[FadeIn(c, shift=0.3 * LEFT) for c in qs], lag_ratio=0.3), FadeIn(q_l)], 1.6),
            "Restarting",
            (lambda: [Indicate(lk_p, color=RED_M, scale_factor=1.6), Indicate(lk_w, color=RED_M, scale_factor=1.6)], 1.2),
        ])

        self.steps("Only the coordinator's log knows the outcome. When it comes back, it reads the log and finishes every transfer left in doubt.", [
            (lambda: [FadeOut(why1), FadeOut(why2), FadeOut(dead), coord[0].animate.set_stroke(C_C), coord[1].animate.set_color(C_C)], 0.8),
            "it reads the log",
            (lambda: [Circumscribe(clog, color=GREEN_M, buff=0.12)], 1.0),
            "and finishes",
            (lambda: [GrowArrow(aw), GrowArrow(ap)], 0.6),
            (lambda: [travel(aw, C_C, 0.6), travel(ap, C_C, 0.6)], 0.6),
            (lambda: [status(wst, "committed", GREEN_M), status(pst, "committed", GREEN_M), FadeOut(lk_w), FadeOut(lk_p),
                      FadeOut(qs), FadeOut(q_l)], 0.9),
        ])

        self.steps("Every server promises, one log line decides, then everyone commits. Lose the coordinator in between, and the servers wait.", [
            (lambda: [Circumscribe(clog, color=GREEN_M, buff=0.12)], 1.4),
        ])
        self.wait(0.6)
