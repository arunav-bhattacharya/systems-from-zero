from sfz import *

SAY.insert(0, (r"\betcd\b", "et see dee"))
# a lone "A" after a word reads as "uh"; "eh" lands on the letter
SAY.insert(0, (r"\b[Pp]od A\b", "pod eh"))
SAY.insert(0, (r"\bA's\b", "eh's"))
SAY.insert(0, (r"\bwatches A\b", "watches eh"))

SC, SW_, SH_ = np.array([-4.3, 0.45, 0]), 4.4, 4.2       # the coordination service
RX, RW, RH = -3.85, 3.1, 0.62                            # its nodes, one row per pod
RY = {"A": 1.55, "B": 0.45, "C": -0.65}
REV = {"A": 7, "B": 9, "C": 11}
PX, PW, PH = 0.55, 2.5, 0.78                             # the pods
LC, LW, LH = np.array([4.75, 0.45, 0]), 2.9, 2.3          # the payout ledger
STY, RUY = -2.45, -3.15


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


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def row(p, color=WHITE, rev=None):
    y = RY[p]
    r = RoundedRectangle(corner_radius=0.08, width=RW, height=RH, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([RX, y, 0])
    n = T(f"pod {p}'s node", 19).move_to([RX - RW / 2 + 0.15, y, 0], aligned_edge=LEFT)
    v = M(f"rev {rev or REV[p]}", 18, GREY_A if color is WHITE else color).move_to([RX + RW / 2 - 0.15, y, 0], aligned_edge=RIGHT)
    return VGroup(r, n, v)


def pod(p, role="", color=WHITE, rcolor=GREY_B):
    y = RY[p]
    r = RoundedRectangle(corner_radius=0.12, width=PW, height=PH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([PX, y, 0])
    n = T(f"pod {p}", 22).move_to([PX - PW / 2 + 0.2, y, 0], aligned_edge=LEFT)
    ro = T(role, 18, rcolor).move_to([PX + PW / 2 - 0.2, y, 0], aligned_edge=RIGHT)
    return VGroup(r, n, ro)


def revc(n, color=GREY_B):
    return T(f"revision now: {n}", 19, color).move_to(SC + (SH_ / 2 - 0.4) * DOWN)


def lline(s, k, color=WHITE, mono=True):
    y = [0.65, 0.15, -0.3][k]
    return (M(s, 17, color) if mono else T(s, 19, color)).move_to([LC[0], y, 0])


def status(s, color=GREY_B):
    return T(s, 22, color).move_to([0, STY, 0])


def rule(s, color=GREY_B):
    return T(s, 20, color).move_to([0, RUY, 0])


def watch(a, b, color=PURPLE_M):
    """B's watch on the node just before it: a curve on the left of the service's rows."""
    s = np.array([RX - RW / 2 - 0.05, RY[a] + 0.12, 0])
    e = np.array([RX - RW / 2 - 0.05, RY[b] - 0.12, 0])
    return CurvedArrow(s, e, angle=-PI * 0.75, color=color, stroke_width=3, tip_length=0.16)


class LeaderElection(Base):
    """cons-05, section 3: three settlement pods hold sessions with a coordination service and create ephemeral,
    sequential nodes at revisions 7, 9 and 11. The lowest leads; B watches A and C watches B. A writes batch 17 with
    token 7. A freezes in a 15 s GC pause, its session expires, its node is deleted (revision 12), B's watch fires and
    B leads with token 9 and writes batch 18. A wakes and writes with token 7; the ledger refuses it, 7 < 9."""

    def construct(self):
        self.title_card("Leader election", "ephemeral nodes, watches and a token the old leader can't fake")

        pods = {p: pod(p) for p in RY}
        led = RoundedRectangle(corner_radius=0.14, width=LW, height=LH, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        led.move_to(LC)
        ltitle = T("payout ledger", 22).move_to([LC[0], LC[1] + LH / 2 - 0.32, 0])
        st0 = status("two leaders would pay every merchant twice", GREY_B)
        self.steps("Three settlement pods must agree on one thing: which of them runs tonight's payout batch. "
                   "Two at once would pay every merchant twice.", [
            (lambda: [LaggedStart(*[FadeIn(pods[p], shift=0.1 * RIGHT) for p in RY], lag_ratio=0.25)], 1.0),
            "runs tonight's",
            (lambda: [FadeIn(led), FadeIn(ltitle)], 0.7),
            "Two at once",
            (lambda: [FadeIn(st0, shift=0.1 * UP)], 0.6),
        ])

        svc = RoundedRectangle(corner_radius=0.16, width=SW_, height=SH_, stroke_color=TEAL_M, stroke_width=2.5)
        svc.set_fill(fillc(TEAL_M, 0.06), 1).move_to(SC)
        stitle = T("coordination service", 22, TEAL_M).move_to(SC + (SH_ / 2 - 0.33) * UP)
        ses = {p: DashedLine([SC[0] + SW_ / 2, RY[p], 0], [PX - PW / 2, RY[p], 0], dash_length=0.08, stroke_width=2,
                             color=GREY_C) for p in RY}
        slab = T("session", 16, GREY_B).move_to([(SC[0] + SW_ / 2 + PX - PW / 2) / 2, RY["B"] + 0.24, 0])

        def beats(ps, color=TEAL_M):
            return [travel(Line(ses[p].get_end(), ses[p].get_start()), color, 0.6) for p in ps]

        self.steps("Each pod opens a session with a coordination service, such as ZooKeeper or etcd, "
                   "and keeps it alive with heartbeats.", [
            (lambda: [FadeOut(st0), FadeIn(svc), FadeIn(stitle)], 0.8),
            (lambda: [*[Create(ses[p]) for p in RY], FadeIn(slab)], 0.7),
            "keeps it alive",
            (lambda: beats(RY), 0.7),
            (lambda: beats(RY), 0.7),
        ])

        rows = {p: row(p) for p in RY}
        rc = revc(6)
        self.steps("Then each pod creates a node. It's ephemeral: it lives only as long as its pod's session. "
                   "And it's sequential: the service stamps it with a revision, a number that grows with every write.", [
            (lambda: [FadeIn(rc)], 0.4),
            (lambda: [FadeIn(rows["A"], shift=0.15 * LEFT), Transform(rc, revc(7))], 0.6),
            (lambda: [FadeIn(rows["B"], shift=0.15 * LEFT), Transform(rc, revc(9))], 0.6),
            (lambda: [FadeIn(rows["C"], shift=0.15 * LEFT), Transform(rc, revc(11))], 0.6),
            "It's ephemeral",
            (lambda: [*[glow(ses[p], YELLOW_M, 1.0) for p in RY]], 0.8),
            "the service stamps",
            (lambda: [*[Indicate(rows[p][2], color=YELLOW_M, scale_factor=1.15) for p in RY]], 0.9),
            (lambda: [Indicate(rc, color=YELLOW_M, scale_factor=1.1)], 0.7),
        ])

        r1 = rule("rule: the lowest revision leads")
        self.steps("Pod A got 7, B got 9, C got 11. The lowest revision leads, so pod A is the leader.", [
            (lambda: [FadeIn(r1, shift=0.1 * UP)], 0.6),
            "The lowest",
            (lambda: [Transform(rows["A"], row("A", BLUE_M))], 0.6),
            "so pod A",
            (lambda: [Transform(pods["A"], pod("A", "leader", BLUE_M, BLUE_M)),
                      *[Transform(pods[p], pod(p, "follower")) for p in ("B", "C")]], 0.7),
        ])

        wBA, wCB = watch("B", "A"), watch("C", "B")
        r2 = rule("each pod watches the node just before its own")
        self.steps("Each of the others watches only the node just before its own: B watches A, and C watches B. "
                   "When a node goes, only the pod right behind it hears.", [
            (lambda: [Transform(r1, r2)], 0.6),
            "B watches A",
            (lambda: [Create(wBA)], 0.7),
            "C watches B",
            (lambda: [Create(wCB)], 0.7),
        ])

        wr = {p: edge_arrow(pods[p][0], led, GREY_B, buff=0.1) for p in RY}
        hi = lline("highest token: 7", 0, GOLD_M)
        b17 = lline("batch 17, token 7", 1, GREEN_M)
        self.steps("Pod A writes batch 17 to the ledger and sends its revision with it, as a token. "
                   "The ledger accepts it and remembers 7.", [
            (lambda: [FadeOut(r1), GrowArrow(wr["A"])], 0.6),
            (lambda: [travel(wr["A"], BLUE_M, 0.7)], 0.7),
            "The ledger accepts",
            (lambda: [FadeIn(b17, shift=0.1 * LEFT)], 0.5),
            "and remembers",
            (lambda: [FadeIn(hi, shift=0.1 * DOWN)], 0.6),
        ])

        st1 = status("pod A: 15 second GC pause", GREY_B)
        self.steps("Now pod A freezes in a 15 second garbage collection pause. Its heartbeats stop, and B's and C's go on.", [
            (lambda: [Transform(pods["A"], pod("A", "frozen", GREY_D, GREY_B)), FadeIn(st1, shift=0.1 * UP),
                      wr["A"].animate.set_color(GREY_D)], 0.8),
            "Its heartbeats stop",
            (lambda: beats(("B", "C")), 0.7),
            (lambda: beats(("B", "C")), 0.7),
        ])

        st2 = status("A's session expired: its node is deleted", RED_M)
        self.steps("The session runs out. The service ends A's session and deletes its node, and the revision moves to 12.", [
            (lambda: [Transform(rows["A"], row("A", RED_M)), ses["A"].animate.set_color(RED_M), Transform(st1, st2)], 0.7),
            "deletes its node",
            (lambda: [FadeOut(rows["A"], shift=0.15 * LEFT), FadeOut(ses["A"]), Transform(rc, revc(12, YELLOW_M))], 0.8),
        ])

        r3 = rule("B's node is now the lowest: B leads, token 9")
        self.steps("B's watch fires. B lists the nodes again, sees its own is now the lowest, and takes over with token 9.", [
            (lambda: [wBA.animate.set_color(YELLOW_M)], 0.4),
            (lambda: [FadeOut(wBA)], 0.4),
            "B lists",
            (lambda: [glow(rows["B"][0], YELLOW_M, 1.04), glow(rows["C"][0], YELLOW_M, 1.04)], 0.8),
            "and takes over",
            (lambda: [Transform(rows["B"], row("B", BLUE_M)), Transform(pods["B"], pod("B", "leader", BLUE_M, BLUE_M)),
                      FadeOut(st1), FadeIn(r3, shift=0.1 * UP)], 0.8),
        ])

        b18 = lline("batch 18, token 9", 2, GREEN_M)
        self.steps("B writes batch 18 with token 9. The ledger accepts it, and its highest token becomes 9.", [
            (lambda: [GrowArrow(wr["B"])], 0.5),
            (lambda: [travel(wr["B"], BLUE_M, 0.7)], 0.7),
            (lambda: [FadeIn(b18, shift=0.1 * LEFT)], 0.5),
            "its highest token",
            (lambda: [Transform(hi, lline("highest token: 9", 0, GOLD_M)), glow(led, GOLD_M, 1.03)], 0.7),
        ])

        self.steps("Then pod A wakes up. Nothing has told it yet, so it still believes it leads, and it writes with token 7.", [
            (lambda: [FadeOut(r3), Transform(pods["A"], pod("A", "leader?", GOLD_M, GOLD_M)), wr["A"].animate.set_color(GOLD_M)], 0.8),
            "and it writes",
            (lambda: [travel(wr["A"], GOLD_M, 0.8)], 0.8),
        ])

        no = tick(False, 0.2).move_to(wr["A"].point_from_proportion(0.55))
        st3 = status("refused: token 7 is lower than 9", RED_M)
        self.steps("The ledger checks: 7 is lower than 9, so it refuses the write. The paused leader is fenced off.", [
            (lambda: [Indicate(hi, color=GOLD_M, scale_factor=1.1)], 0.7),
            "so it refuses",
            (lambda: [Create(no), FadeIn(st3, shift=0.1 * UP), wr["A"].animate.set_color(RED_M)], 0.7),
            "fenced off",
            (lambda: [Transform(pods["A"], pod("A", "fenced", RED_M, RED_M))], 0.7),
        ])

        r4 = rule("the lease says who should lead; the ledger checks the token")
        self.steps("The lowest node leads, and each pod watches the one ahead of it. But only the ledger can stop a leader "
                   "that woke up late, so every write carries the token, and the ledger checks it.", [
            (lambda: [glow(rows["B"][0], BLUE_M, 1.04)], 0.8),
            "each pod watches",
            (lambda: [wCB.animate(rate_func=there_and_back).set_stroke(width=6)], 0.8),
            "But only the ledger",
            (lambda: [glow(led, GOLD_M, 1.03), Transform(st3, r4)], 1.0),
        ])
        self.wait(0.6)
