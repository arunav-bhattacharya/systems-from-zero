from sfz import *

# Kokoro reads a lone capital A as the article "uh"; here A is always the withdrawal.
SAY.insert(0, (r"\bA\b", "eh"))
SAY.insert(0, (r"\bSSI\b", "S S I"))
# "read-write" ran together as "re-dried".
SAY.insert(0, (r"\bread-write\b", "read write"))
SAY.insert(0, (r"\bSERIALIZABLE\b", "serializable"))

ROWY = {1: 2.4, 2: 1.5}                   # card rows
RW, RH = 2.6, 0.66
TOTY = 0.62
TX = {"A": -5.05, "B": 5.05}              # transaction boxes
TY, TW, TH = 1.95, 2.7, 1.75
TC = {"A": BLUE_M, "B": GOLD_M}
NX, NY, NR = 2.05, -1.6, 0.42             # dependency graph nodes
TAGX = 2.45


def fillc(color):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def row(k, val, color=WHITE):
    r = RoundedRectangle(corner_radius=0.1, width=RW, height=RH, stroke_color=color, stroke_width=3)
    r.set_fill(BLACK if color is WHITE else fillc(color), 1).move_to([0, ROWY[k], 0])
    return VGroup(r, T(f"card {k}: {val}", 24).move_to([0, ROWY[k], 0]))


def total(v, color=WHITE):
    return T(f"total: {v}", 26, color).move_to([0, TOTY, 0])


def tline(t, i, s, color=GREY_B):
    return T(s, 18, color).move_to([TX[t], TY + 0.18 - 0.35 * i, 0])


def tbox(t, color=None):
    color = color or TC[t]
    r = RoundedRectangle(corner_radius=0.14, width=TW, height=TH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([TX[t], TY, 0])
    return VGroup(r, T(f"withdrawal {t}", 22).move_to([TX[t], TY + 0.57, 0]))


def tag(t, k):
    x = -TAGX if t == "A" else TAGX
    return chip(f"{t} read", TC[t], 17).move_to([x, ROWY[k], 0])


def node(t):
    c = Circle(radius=NR, stroke_color=TC[t], stroke_width=3).set_fill(fillc(TC[t]), 1)
    c.move_to([-NX if t == "A" else NX, NY, 0])
    return VGroup(c, T(t, 28).move_to(c))


def edge(src, color=GREY_A):
    """B to A over the top, A to B underneath."""
    if src == "B":
        a, b = [NX - 0.4, NY + 0.2, 0], [-NX + 0.4, NY + 0.2, 0]
        return CurvedArrow(np.array(a), np.array(b), angle=TAU / 6, color=color, stroke_width=3, tip_length=0.2)
    a, b = [-NX + 0.4, NY - 0.2, 0], [NX - 0.4, NY - 0.2, 0]
    return CurvedArrow(np.array(a), np.array(b), angle=TAU / 6, color=color, stroke_width=3, tip_length=0.2)


def read_dot(t, k, color):
    """A dot carrying a card's value from its row to a transaction."""
    sx = -RW / 2 - 0.05 if t == "A" else RW / 2 + 0.05
    ex = TX[t] + (TW / 2 + 0.05 if t == "A" else -TW / 2 - 0.05)
    return travel(Line([sx, ROWY[k], 0], [ex, TY + 0.1, 0]), color, 0.8)


def write_dot(t, k, color):
    sx = TX[t] + (TW / 2 + 0.05 if t == "A" else -TW / 2 - 0.05)
    ex = -RW / 2 - 0.05 if t == "A" else RW / 2 + 0.05
    return travel(Line([sx, TY - 0.3, 0], [ex, ROWY[k], 0]), color, 0.8)


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


class SSI(Base):
    """txn-05, section 3: acct-17 has two cards with 75 euros each and the rule that the total stays at or above zero.
    Withdrawals A and B each read 150 and take 100 from different cards; under snapshot isolation both commit and the
    total is -50. Under SERIALIZABLE (SSI) each read leaves an SIREAD note; A's write of card 1 meets B's note (edge
    B to A), B's write of card 2 meets A's (edge A to B); a pivot with a committed partner, B fails with 40001, retries,
    sees 50 and refuses."""

    def construct(self):
        self.title_card("Serializable snapshot isolation", "how PostgreSQL catches write skew without blocking reads")

        rule = T("acct-17: the total must never go below zero", 22, GREY_A).move_to([0, 3.35, 0])
        rows = {k: row(k, 75) for k in (1, 2)}
        tot = total(150)
        self.steps("Account 17 has two cards with 75 euros each. The rule: the account's total must never go below zero.", [
            (lambda: [FadeIn(rows[1]), FadeIn(rows[2])], 0.8),
            (lambda: [FadeIn(tot)], 0.5),
            "The rule",
            (lambda: [FadeIn(rule, shift=0.1 * DOWN)], 0.7),
        ])

        box = {t: tbox(t) for t in "AB"}
        ln = {t: [tline(t, 0, "read total: 150"), None, None] for t in "AB"}
        self.steps("Two withdrawals of 100 euros start at once. Each reads both cards from its own snapshot, "
                   "sees a total of 150, and goes ahead.", [
            (lambda: [FadeIn(box["A"]), FadeIn(box["B"])], 0.8),
            "Each reads",
            (lambda: [LaggedStart(*[read_dot(t, k, TC[t]) for t in "AB" for k in (1, 2)], lag_ratio=0.15)], 1.3),
            "sees a total",
            (lambda: [FadeIn(ln["A"][0]), FadeIn(ln["B"][0])], 0.6),
        ])

        def take(t, k, color, val=-25):
            ln[t][1] = tline(t, 1, f"card {k}: minus 100", WHITE)
            return [FadeIn(ln[t][1]), write_dot(t, k, color), Transform(rows[k], row(k, val, color))]

        self.steps("Withdrawal A takes 100 from card 1, and B takes 100 from card 2. Different rows, so no lock ever conflicts.", [
            (lambda: take("A", 1, BLUE_M), 1.0),
            "and B takes",
            (lambda: take("B", 2, GOLD_M), 1.0),
            "Different rows",
            (lambda: [glow(rows[1][0], BLUE_M), glow(rows[2][0], GOLD_M)], 1.0),
        ])

        cross = tick(False, 0.2).move_to([1.45, TOTY, 0])

        def commit_both():
            for t in "AB":
                ln[t][2] = tline(t, 2, "committed", GREEN_M)
            return [FadeIn(ln["A"][2]), FadeIn(ln["B"][2]), Transform(rows[1], row(1, -25)), Transform(rows[2], row(2, -25))]

        self.steps("Under snapshot isolation both commit, and the total is minus 50. "
                   "Run one at a time, the second would have refused.", [
            (lambda: commit_both(), 0.8),
            "and the total",
            (lambda: [Transform(tot, total("-50", RED_M)), Create(cross)], 0.8),
            "Run one at a time",
            (lambda: [glow(rule, RED_M, 1.03)], 1.0),
        ])

        # ---- the same two withdrawals under SERIALIZABLE ---------------------------------------------------------
        mode = T("isolation: SERIALIZABLE", 20, TEAL_M).move_to([0, -0.15, 0])
        tags = {(t, k): tag(t, k) for t in "AB" for k in (1, 2)}

        def reset():
            old = [m for t in "AB" for m in ln[t][1:]]
            for t in "AB":
                ln[t][1:] = [None, None]
            return [Transform(rows[1], row(1, 75)), Transform(rows[2], row(2, 75)), Transform(tot, total(150)),
                    FadeOut(cross), *[FadeOut(m) for m in old], FadeIn(mode)]

        self.steps("Run them again at SERIALIZABLE. Reads still never wait, but each read leaves a note on the row "
                   "saying who read it. The notes block nothing.", [
            (lambda: reset(), 0.9),
            "Reads still",
            (lambda: [LaggedStart(*[read_dot(t, k, TC[t]) for t in "AB" for k in (1, 2)], lag_ratio=0.15)], 1.2),
            "but each read",
            (lambda: [LaggedStart(*[FadeIn(tags[(t, k)], shift=(0.3 * RIGHT if t == "A" else 0.3 * LEFT))
                                    for t in "AB" for k in (1, 2)], lag_ratio=0.2)], 1.3),
            "The notes block",
            (lambda: [*[glow(tags[(t, k)][0], WHITE, 1.08) for t in "AB" for k in (1, 2)]], 0.9),
        ])

        nodes = {t: node(t) for t in "AB"}
        e_ba = edge("B")
        lab_ba = T("B read card 1, then A wrote it: B first", 18, GREY_A).move_to([0, NY + 0.92, 0])
        self.steps("A writes a new card 1, and PostgreSQL finds B's note on it. B read the old value and can't see "
                   "A's change, so B must come first in any one-at-a-time order.", [
            (lambda: take("A", 1, BLUE_M), 1.0),
            "finds B's note",
            (lambda: [glow(tags[("B", 1)][0], GOLD_M, 1.12)], 0.9),
            "B read the old",
            (lambda: [FadeOut(mode), FadeIn(nodes["A"]), FadeIn(nodes["B"])], 0.7),
            "so B must",
            (lambda: [Create(e_ba), FadeIn(lab_ba)], 1.0),
        ])

        self.steps("That's a read-write dependency, an arrow from B to A.", [
            (lambda: [glow(nodes["B"][0], GOLD_M, 1.1)], 0.7),
            (lambda: [e_ba.animate(rate_func=there_and_back).set_stroke(width=7), glow(nodes["A"][0], BLUE_M, 1.1)], 0.8),
        ])

        e_ab = edge("A")
        lab_ab = T("A read card 2, then B wrote it: A first", 18, GREY_A).move_to([0, NY - 0.98, 0])
        self.steps("Then B writes card 2, which A read: an arrow from A to B.", [
            (lambda: take("B", 2, GOLD_M), 1.0),
            "which A read",
            (lambda: [glow(tags[("A", 2)][0], BLUE_M, 1.12)], 0.8),
            "an arrow",
            (lambda: [Create(e_ab), FadeIn(lab_ab)], 0.9),
        ])

        self.steps("Now A must come before B, and B before A. No one-at-a-time order can do both.", [
            (lambda: [e_ab.animate.set_color(RED_M), lab_ab.animate.set_color(RED_M)], 0.7),
            "and B before",
            (lambda: [e_ba.animate.set_color(RED_M), lab_ba.animate.set_color(RED_M)], 0.7),
            "No one-at-a-time",
            (lambda: [glow(nodes["A"][0], RED_M, 1.1), glow(nodes["B"][0], RED_M, 1.1)], 0.9),
        ])

        piv = T("pivot: one arrow in, one out", 18, GOLD_M)
        piv.move_to([NX + NR + 0.2 + piv.width / 2, NY, 0])
        self.steps("Searching for whole cycles is slow. But every such cycle has a transaction with one arrow in "
                   "and one out, called a pivot, so PostgreSQL watches for that.", [
            "But every",
            (lambda: [e_ab.animate(rate_func=there_and_back).set_stroke(width=7)], 0.8),
            (lambda: [e_ba.animate(rate_func=there_and_back).set_stroke(width=7)], 0.8),
            "called a pivot",
            (lambda: [FadeIn(piv, shift=0.1 * LEFT), glow(nodes["B"][0], GOLD_M, 1.12)], 0.9),
        ])

        err = chip("B: ERROR could not serialize access (SQLSTATE 40001)", RED_M, 17).move_to([0, -3.2, 0])

        def commit_a():
            ln["A"][2] = tline("A", 2, "committed", GREEN_M)
            return [FadeIn(ln["A"][2]), Transform(rows[1], row(1, -25)), Transform(tot, total(50))]

        def abort_b():
            ln["B"][2] = tline("B", 2, "aborted", RED_M)
            return [FadeIn(ln["B"][2]), FadeIn(err, shift=0.1 * UP), box["B"][0].animate.set_stroke(RED_M)]

        self.steps("A commits first. B is a pivot, and its partner has committed, "
                   "so B's commit fails with a serialization error.", [
            (lambda: commit_a(), 0.8),
            "B is a pivot",
            (lambda: [glow(nodes["B"][0], GOLD_M, 1.12)], 0.8),
            "so B's commit",
            (lambda: abort_b(), 0.9),
        ])

        self.steps("B's write is thrown away, and the total is 50, as if A ran alone.", [
            (lambda: [Transform(rows[2], row(2, 75)), FadeOut(tags[("A", 2)]), FadeOut(tags[("B", 1)]), FadeOut(tags[("B", 2)]),
                      FadeOut(tags[("A", 1)])], 0.8),
            "and the total",
            (lambda: [Transform(tot, total(50, GREEN_M))], 0.7),
        ])

        def retry():
            new = [tline("B", 0, "retry: total 50", WHITE), tline("B", 1, "not enough for 100", GREY_B),
                   tline("B", 2, "refused", GREEN_M)]
            out = [box["B"][0].animate.set_stroke(GOLD_M), FadeOut(err), FadeOut(e_ab), FadeOut(e_ba), FadeOut(lab_ab),
                   FadeOut(lab_ba), FadeOut(piv), FadeOut(nodes["A"]), FadeOut(nodes["B"]),
                   *[FadeOut(m) for m in ln["B"]], FadeIn(new[0])]
            ln["B"] = new
            return out

        self.steps("The application retries B. Its new snapshot shows 50, not enough for 100, so B refuses.", [
            (lambda: retry(), 0.9),
            "Its new snapshot",
            (lambda: [read_dot("B", 1, GOLD_M), read_dot("B", 2, GOLD_M)], 0.9),
            "not enough",
            (lambda: [FadeIn(ln["B"][1])], 0.5),
            "so B refuses",
            (lambda: [FadeIn(ln["B"][2])], 0.6),
        ])

        self.steps("Snapshot isolation lets both commit. SSI tracks who read what the other wrote and aborts one. "
                   "Your code retries it.", [
            (lambda: [glow(rule, GREEN_M, 1.03)], 0.9),
            "SSI tracks",
            (lambda: [glow(box["A"][0], BLUE_M), glow(box["B"][0], GOLD_M)], 1.0),
            "Your code",
            (lambda: [Indicate(ln["B"][2], color=GREEN_M)], 0.8),
        ])
        self.wait(0.6)
