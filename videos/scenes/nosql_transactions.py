from sfz import *

SAY.insert(0, (r"\bA-1001's\b", "A-10 oh 1's"))
SAY.insert(0, (r"\bA-1001\b", "A-10 oh 1"))
SAY.insert(0, (r"\bA-2002\b", "A-20 oh 2"))
SAY.insert(0, (r"\bT1\b", "T one"))
SAY.insert(0, (r"\bT2\b", "T two"))

CALLER = np.array([-4.9, 2.75, 0])
COORD = np.array([0.0, 2.75, 0])
LEDGER = np.array([4.9, 2.75, 0])
TOPW, TOPH = 3.1, 1.1
NODE = {1: np.array([-3.4, -0.4, 0]), 2: np.array([3.4, -0.4, 0])}
NW, NH = 4.2, 2.2
ACCT = {1: "A-1001", 2: "A-2002"}
TOTAL_Y, NOTE_Y = -2.4, -3.2


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along an arrow (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def lost(path, color, frac=0.55, back=False):
    """A message that dies partway; returns (animation, point where it died)."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    mid = a + frac * (b - a)
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, mid), run_time=0.6),
                      FadeOut(d, run_time=0.25)), mid


def arr(a, b, color=GREY_B):
    return Arrow(a, b, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.08)


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


def topbox(title, c, color=WHITE, sub="", scolor=GREY_B):
    r = RoundedRectangle(corner_radius=0.14, width=TOPW, height=TOPH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(title, 26).move_to(c + 0.22 * UP), topsub(c, sub, scolor))


def topsub(c, s, color=GREY_B):
    if not s:
        return T("T1", 20, color).move_to(c + 0.25 * DOWN).set_opacity(0)
    return T(s, 20, color).move_to(c + 0.25 * DOWN)


def bal_text(i, s, color=WHITE):
    c = NODE[i]
    m = M(s, 28, color)
    return m.move_to([c[0] + 1.65 - m.width / 2, c[1] + 0.05, 0])


def nstatus(i, s, color=GREY_B):
    c = NODE[i]
    return T(s, 22, color).move_to([c[0], c[1] - 0.64, 0])


def node(i, bal):
    c = NODE[i]
    r = RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    title = T(f"storage node {i}", 22, GREY_B).move_to(c + 0.72 * UP)
    a = M(ACCT[i], 26)
    a.move_to([c[0] - 1.65 + a.width / 2, c[1] + 0.05, 0])
    return VGroup(r, title, a, bal_text(i, bal), nstatus(i, "free"))


def total(s, color=WHITE):
    return M(f"A-1001 + A-2002 = {s}", 26, color).move_to([0, TOTAL_Y, 0])


def note(s, color=GREY_B):
    return chip(s, color, 20).move_to([0, NOTE_Y, 0])


class NosqlTransactions(Base):
    """txn-08, section 0: a transfer of 30.00 from A-1001 (100.00) to A-2002 (50.00), in two partitions. Two plain
    writes lose 30 when the credit times out. A coordinator prepares both items (condition checked, item held), T2
    holding A-2002 makes that node refuse at once and T1 is cancelled; a retry with the same client token prepares
    both, the coordinator writes commit in its ledger, then commits both (70.00 and 80.00). A repeat with the same
    token is answered without writing. The price: two writes per item, and conflicts on busy items."""

    def construct(self):
        self.title_card("Transactions across partitions", "prepare every item, then commit or cancel them all")

        caller = topbox("wallet service", CALLER)
        n = {1: node(1, "100.00"), 2: node(2, "50.00")}
        tot = total("150.00")
        self.steps("A wallet moves 30 from account A-1001 to A-2002. "
                   "They live in different partitions, on two storage nodes.", [
            (lambda: [FadeIn(caller)], 0.6),
            "They live",
            (lambda: [FadeIn(n[1], shift=0.1 * UP), FadeIn(n[2], shift=0.1 * UP)], 0.9),
            (lambda: [FadeIn(tot)], 0.6),
        ])

        one = note("one partition: one node decides alone")
        self.steps("In one partition, one node decides alone, so a single write is atomic for free.", [
            (lambda: [glow(n[1][0], BLUE_M)], 1.0),
            "so a single write",
            (lambda: [FadeIn(one, shift=0.1 * UP)], 0.7),
        ])

        w1 = arr(CALLER + np.array([0.6, -TOPH / 2 - 0.05, 0]), NODE[1] + np.array([-0.9, NH / 2 + 0.08, 0]))
        w2 = arr(CALLER + np.array([1.1, -TOPH / 2 - 0.05, 0]), NODE[2] + np.array([-1.2, NH / 2 + 0.08, 0]))
        self.steps("So try two separate writes. First, debit A-1001.", [
            (lambda: [FadeOut(one)], 0.4),
            "First, debit",
            (lambda: [GrowArrow(w1)], 0.5),
            (lambda: [flow(w1, GOLD_M, 0.7)], 0.7),
            (lambda: [Transform(n[1][3], bal_text(1, "70.00", GOLD_M))], 0.6),
        ])

        xs = {}

        def lose():
            an, pt = lost(w2, GOLD_M, 0.6)
            xs["c"] = tick(False, 0.18).move_to(pt)
            return [an]

        self.steps("Then the credit times out. 30 left one account and reached none. The total fell to 120.", [
            (lambda: [GrowArrow(w2)], 0.4),
            (lambda: lose(), 0.9),
            (lambda: [Create(xs["c"])], 0.4),
            "The total fell",
            (lambda: [Transform(tot, total("120.00", RED_M))], 0.7),
        ])

        coord = topbox("coordinator", COORD, BLUE_M)
        cc = arr(CALLER + np.array([TOPW / 2 + 0.1, 0, 0]), COORD + np.array([-TOPW / 2 - 0.1, 0, 0]))
        self.steps("Try again. DynamoDB gives the transfer, T1, to a coordinator that works in two rounds.", [
            (lambda: [FadeOut(w1), FadeOut(w2), FadeOut(xs["c"]), Transform(n[1][3], bal_text(1, "100.00")),
                      Transform(tot, total("150.00"))], 0.8),
            "DynamoDB gives",
            (lambda: [FadeIn(coord), GrowArrow(cc)], 0.7),
            (lambda: [flow(cc, WHITE, 0.6)], 0.6),
            (lambda: [Transform(coord[2], topsub(COORD, "T1", BLUE_M))], 0.4),
        ])

        c1 = arr(COORD + np.array([-0.7, -TOPH / 2 - 0.05, 0]), NODE[1] + np.array([0.9, NH / 2 + 0.08, 0]))
        c2 = arr(COORD + np.array([0.7, -TOPH / 2 - 0.05, 0]), NODE[2] + np.array([-0.9, NH / 2 + 0.08, 0]))
        self.steps("Round one, prepare. Node 1 checks that A-1001 holds at least 30 and is free, "
                   "so it says yes and holds the item for T1. Nothing has changed yet.", [
            (lambda: [GrowArrow(c1), Transform(coord[2], topsub(COORD, "T1: prepare", BLUE_M))], 0.6),
            (lambda: [flow(c1, BLUE_M, 0.7)], 0.7),
            "so it says yes",
            (lambda: [Transform(n[1][4], nstatus(1, "held for T1", GOLD_M)), n[1][0].animate.set_stroke(GOLD_M)], 0.6),
            (lambda: [flow(c1, GREEN_M, 0.6, back=True)], 0.6),
            "Nothing has changed",
            (lambda: [glow(n[1][0], GOLD_M)], 0.9),
        ])

        xs2 = {}
        self.steps("But another transfer, T2, holds A-2002. When T1's prepare arrives, that node says no at once, without waiting.", [
            (lambda: [Transform(n[2][4], nstatus(2, "held for T2", PURPLE_M)), n[2][0].animate.set_stroke(PURPLE_M)], 0.7),
            "When T1's prepare",
            (lambda: [GrowArrow(c2)], 0.4),
            (lambda: [flow(c2, BLUE_M, 0.7)], 0.7),
            "says no",
            (lambda: [flow(c2, RED_M, 0.6, back=True)], 0.6),
            (lambda: [Transform(coord[2], topsub(COORD, "T1: one no", RED_M))], 0.5),
        ])

        conflict = M("transaction conflict", 18, RED_M).move_to(CALLER + 0.82 * DOWN)
        self.steps("A single no cancels everything. The coordinator tells node 1 to forget T1, "
                   "and the caller gets a transaction conflict. Nothing was written.", [
            "The coordinator tells",
            (lambda: [flow(c1, RED_M, 0.7)], 0.7),
            (lambda: [Transform(n[1][4], nstatus(1, "free")), n[1][0].animate.set_stroke(WHITE),
                      Transform(coord[2], topsub(COORD, "T1: cancelled", RED_M))], 0.6),
            "and the caller",
            (lambda: [flow(cc, RED_M, 0.6, back=True)], 0.6),
            (lambda: [FadeIn(conflict)], 0.5),
            "Nothing was written",
            (lambda: [glow(n[1][0], WHITE, 1.03), glow(n[2][0], PURPLE_M, 1.03)], 0.8),
        ])

        token = M("client token k-1", 18, GOLD_M).move_to(CALLER + 0.82 * DOWN)
        self.steps("T2 finishes. The caller retries T1 "
                   "with the same client token, an id it picked for this transfer. This time both nodes say yes.", [
            (lambda: [Transform(n[2][4], nstatus(2, "free")), n[2][0].animate.set_stroke(WHITE)], 0.6),
            "The caller retries",
            (lambda: [FadeOut(conflict), Transform(coord[2], topsub(COORD, "T1", BLUE_M))], 0.4),
            (lambda: [flow(cc, WHITE, 0.6)], 0.6),
            "with the same client token",
            (lambda: [FadeIn(token)], 0.5),
            "This time",
            (lambda: [Transform(coord[2], topsub(COORD, "T1: prepare", BLUE_M)), flow(c1, BLUE_M, 0.6), flow(c2, BLUE_M, 0.6)], 0.6),
            (lambda: [Transform(n[1][4], nstatus(1, "held for T1", GOLD_M)), n[1][0].animate.set_stroke(GOLD_M),
                      Transform(n[2][4], nstatus(2, "held for T1", GOLD_M)), n[2][0].animate.set_stroke(GOLD_M)], 0.5),
            (lambda: [flow(c1, GREEN_M, 0.6, back=True), flow(c2, GREEN_M, 0.6, back=True)], 0.6),
        ])

        ledger = topbox("ledger", LEDGER, GREEN_M)
        cl = arr(COORD + np.array([TOPW / 2 + 0.1, 0, 0]), LEDGER + np.array([-TOPW / 2 - 0.1, 0, 0]))
        self.steps("The coordinator writes commit in its ledger before it changes anything. "
                   "If it crashed now, another coordinator would finish T1 from there.", [
            (lambda: [FadeIn(ledger), GrowArrow(cl)], 0.7),
            (lambda: [flow(cl, GREEN_M, 0.6)], 0.6),
            (lambda: [Transform(ledger[2], topsub(LEDGER, "T1: commit", GREEN_M)),
                      Transform(coord[2], topsub(COORD, "T1: commit", GREEN_M))], 0.5),
            "If it crashed",
            (lambda: [coord[0].animate.set_stroke(GREY_D)], 0.5),
            "would finish",
            (lambda: [glow(ledger[0], GREEN_M), coord[0].animate.set_stroke(BLUE_M)], 0.9),
        ])

        self.steps("Round two is the commit. Each node applies its change and lets the item go. 70 and 80: the total is still 150.", [
            (lambda: [flow(c1, GREEN_M, 0.7), flow(c2, GREEN_M, 0.7)], 0.7),
            (lambda: [Transform(n[1][3], bal_text(1, "70.00", GREEN_M)), Transform(n[2][3], bal_text(2, "80.00", GREEN_M))], 0.6),
            "and lets the item go",
            (lambda: [Transform(n[1][4], nstatus(1, "free")), n[1][0].animate.set_stroke(WHITE),
                      Transform(n[2][4], nstatus(2, "free")), n[2][0].animate.set_stroke(WHITE)], 0.6),
            "the total",
            (lambda: [Transform(tot, total("150.00", GREEN_M))], 0.6),
        ])

        xs3 = {}

        def lose_ok():
            an, pt = lost(cc, GREEN_M, 0.55, back=True)
            xs3["x"] = tick(False, 0.16).move_to(pt)
            return [an]

        self.steps("If the OK is lost, the caller sends T1 once more. Same token, already committed, "
                   "so DynamoDB just answers OK and writes nothing.", [
            (lambda: lose_ok(), 0.9),
            (lambda: [Create(xs3["x"])], 0.4),
            "the caller sends",
            (lambda: [FadeOut(xs3["x"]), flow(cc, WHITE, 0.6)], 0.6),
            "Same token",
            (lambda: [Transform(coord[2], topsub(COORD, "k-1: already done", GREEN_M)), glow(token, GOLD_M, 1.06)], 0.8),
            "just answers OK",
            (lambda: [flow(cc, GREEN_M, 0.6, back=True), glow(n[1][0], WHITE, 1.03), glow(n[2][0], WHITE, 1.03)], 0.8),
        ])

        cost1 = chip("2 writes per item: twice the capacity", GOLD_M, 19)
        cost2 = chip("held items: more conflicts", RED_M, 19)
        VGroup(cost1, cost2).arrange(RIGHT, buff=0.4).move_to([0, NOTE_Y, 0])
        self.steps("The price: each item is written in both rounds, twice the write capacity. "
                   "And held items turn others away, so busy accounts see more conflicts.", [
            "each item is written",
            (lambda: [flow(c1, BLUE_M, 0.5), flow(c2, BLUE_M, 0.5)], 0.5),
            (lambda: [flow(c1, GREEN_M, 0.5), flow(c2, GREEN_M, 0.5)], 0.5),
            "twice the write",
            (lambda: [FadeIn(cost1, shift=0.1 * UP)], 0.6),
            "And held items",
            (lambda: [FadeIn(cost2, shift=0.1 * UP)], 0.6),
        ])

        self.steps("When a transaction spans partitions, every node promises first, one decision is saved where a crash can't lose it, "
                   "and only then does anything change.", [
            (lambda: [glow(n[1][0], GOLD_M), glow(n[2][0], GOLD_M)], 0.9),
            "one decision",
            (lambda: [glow(ledger[0], GREEN_M)], 0.9),
            "and only then",
            (lambda: [Indicate(n[1][3], color=GREEN_M), Indicate(n[2][3], color=GREEN_M)], 0.9),
        ])
        self.wait(0.6)
