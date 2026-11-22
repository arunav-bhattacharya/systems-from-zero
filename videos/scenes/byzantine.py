from sfz import *

SAY.insert(0, (r"\b3f \+ 1\b", "three F plus one"))
SAY.insert(0, (r"\b2f \+ 1\b", "two F plus one"))
SAY.insert(0, (r"\b2f\b", "two F"))
SAY.insert(0, (r"\b3f\b", "three F"))
SAY.insert(0, (r"\bf\b", "F"))
SAY.insert(0, (r"\bPBFT\b", "P B F T"))
SAY.insert(0, (r"\bShostak\b", "Shostack"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CAP_Y, BAR_Y = -3.1, -2.6
WA, WB = -3.5, 3.5                      # centres of world A and world B
LY, FY, DX = 1.7, -0.6, 2.0             # leader row, follower row, follower offset
BW, BH = 1.8, 0.75
OK_C, NO_C = GREEN_M, RED_M


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


def node(label, at, color=WHITE):
    return box(label, color, w=BW, h=BH, size=24).move_to([at[0], at[1], 0])


def verdict(ok, size=18):
    c = chip("APPROVE" if ok else "DECLINE", OK_C if ok else NO_C, size, mono=True)
    c[0].set_fill(interpolate_color(ManimColor("#000000"), ManimColor(OK_C if ok else NO_C), 0.22), 1)
    return c


def relabel(b, s, color=WHITE):
    """Swap the label inside a node box (the box keeps the new label as its own)."""
    old, new = b[1], T(s, 24).move_to(b[0])
    b.submobjects[1] = new
    return Succession(FadeOut(old, shift=0.1 * UP), FadeIn(new, shift=0.1 * UP))


def on(arrow, v, t=0.5):
    a, b = arrow.get_start(), arrow.get_end()
    return v.move_to(a + t * (b - a))


def harr(x0, x1, y, color=GREY_B):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12)


def heard(cx, items, y=-1.95, label="follower 1 heard:"):
    chips = [verdict(v) for v in items]
    g = VGroup(*([T(label, 20, GREY_B)] if label else []), *chips).arrange(RIGHT, buff=0.22).move_to([cx, y, 0])
    return g


class Byzantine(Base):
    """dist-07, section 3. Two honest nodes against one liar: surely the majority wins? The office version (the boss
    says approve, a colleague says the boss said decline) and the lesson's two worlds: follower 1 hears APPROVE and
    DECLINE in both, so no tie rule gets both right (the lab: every rule fails with 3 nodes). A fourth node gives each
    follower three verdicts, and one liar spoils only one (40 rounds, none fail). Byzantine fault, 3f + 1 and its
    count, PBFT, and why a payments database doesn't pay for it. Moral and a check: two liars take seven."""

    def construct(self):
        self.capm = None
        self.title_card("Why one liar takes four", "Byzantine faults: computers that lie")

        # world A positions
        L_A, F1_A, F2_A = (WA, LY), (WA - DX, FY), (WA + DX, FY)
        L_B, F1_B, F2_B = (WB, LY), (WB - DX, FY), (WB + DX, FY)

        # ---------------- scene 1: the question ----------------
        lead = node("computer", L_A)
        f1 = node("computer", F1_A)
        f2 = node("computer", F2_A)
        self.steps("So far, a broken computer has simply stopped, or come back with gaps in its memory. "
                   "Now picture a worse one. It keeps talking, and it lies.", [
            (lambda: self.cap("so far: a faulty computer stops, or forgets", GREY_B), 0.5),
            "It keeps talking",
            (lambda: self.cap("worse: it keeps talking, and it lies", RED_M), 0.5),
        ])
        self.steps("Three computers decide one card payment, approve or decline, and one of them lies. "
                   "Two honest against one liar. Surely the majority wins? Hold that guess.", [
            (lambda: [*self.uncap(), LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in (lead, f1, f2)], lag_ratio=0.3)], 1.0),
            "Two honest",
            (lambda: self.cap("2 honest  vs  1 liar: the majority wins?", WHITE), 0.5),
            "Hold that",
            (lambda: [Indicate(self.capm, color=YELLOW_M, scale_factor=1.05)], 0.7),
        ])

        # ---------------- scene 2: the office ----------------
        a_lf1 = edge_arrow(lead, f1)
        a_lf2 = edge_arrow(lead, f2)
        a_21 = harr(F2_A[0] - BW / 2 - 0.1, F1_A[0] + BW / 2 + 0.1, FY - 0.15)
        a_12 = harr(F1_A[0] + BW / 2 + 0.1, F2_A[0] - BW / 2 - 0.1, FY + 0.17)
        v_boss = on(a_lf1, verdict(True))
        v_col = on(a_21, verdict(False))
        self.steps("You've felt this at work. Your boss tells you: approve it.", [
            (lambda: [*self.uncap(), relabel(lead, "boss"), relabel(f1, "you"), relabel(f2, "colleague")], 0.8),
            "approve it",
            (lambda: [GrowArrow(a_lf1), FadeIn(v_boss, scale=0.7)], 0.7),
        ])
        self.steps("Then a colleague says: funny, the boss told me to decline.", [
            "the boss told me",
            (lambda: [GrowArrow(a_21), FadeIn(v_col, scale=0.7)], 0.7),
        ])
        self.steps("Somebody is lying. Is it the boss, or your colleague? From where you sit, you can't tell.", [
            "Is it the boss",
            (lambda: [glow(lead[0], RED_M)], 0.6),
            "or your colleague",
            (lambda: [glow(f2[0], RED_M)], 0.6),
            "you can't tell",
            (lambda: self.cap("from where you sit: you can't tell", WHITE), 0.5),
        ])

        # ---------------- scene 3: the same, with nodes ----------------
        self.steps("Computers do exactly this. One node, the leader, holds a verdict and sends it to the other two, the followers.", [
            (lambda: [*self.uncap(), FadeOut(v_boss), FadeOut(v_col), FadeOut(a_21),
                      relabel(lead, "leader"), relabel(f1, "follower 1"), relabel(f2, "follower 2")], 0.8),
            "sends it",
            (lambda: [GrowArrow(a_lf2)], 0.5),
            (lambda: [glow(f1[0], WHITE), glow(f2[0], WHITE)], 0.6),
        ])
        a_21 = harr(F2_A[0] - BW / 2 - 0.1, F1_A[0] + BW / 2 + 0.1, FY - 0.17)
        self.steps("Each follower tells the other what the leader said. Then each one decides by majority over the two verdicts it heard.", [
            (lambda: [GrowArrow(a_12), GrowArrow(a_21)], 0.7),
            "Then each one",
            (lambda: self.cap("each follower decides by majority over the two verdicts it heard", WHITE), 0.5),
        ])
        self.steps("So the leader is the boss, the followers are you and your colleague, "
                   "and passing on what the leader said is the chat by the coffee machine.", [
            (lambda: self.cap("leader  =  boss"), 0.4),
            "the followers",
            (lambda: self.cap("followers  =  you and your colleague"), 0.4),
            "passing on",
            (lambda: [*self.cap("passing on what the leader said  =  the chat by the coffee machine"),
                      Indicate(a_12, color=YELLOW_M), Indicate(a_21, color=YELLOW_M)], 0.8),
        ])

        # ---------------- scene 4: world A ----------------
        ttl_a = T("world A: the leader is honest", 24, WHITE).move_to([WA, 3.05, 0])
        liar_a = T("liar", 20, RED_M).move_to([F2_A[0], FY - 0.62, 0])
        va1 = on(a_lf1, verdict(True))
        va2 = on(a_lf2, verdict(True))
        va3 = on(a_21, verdict(False))
        self.steps("In world A, the leader is honest, and says approve. Follower 2 lies. It tells follower 1 that the leader said decline.", [
            (lambda: [*self.uncap(), FadeOut(a_12), FadeIn(ttl_a, shift=0.1 * DOWN)], 0.6),
            "says approve",
            (lambda: [FadeIn(va1, scale=0.7), FadeIn(va2, scale=0.7)], 0.6),
            "Follower 2 lies",
            (lambda: [f2[0].animate.set_stroke(RED_M), FadeIn(liar_a)], 0.5),
            "the leader said decline",
            (lambda: [FadeIn(va3, scale=0.7)], 0.6),
        ])
        ha = heard(WA, [True, False])
        self.steps("So follower 1 hears approve from the leader, and decline from follower 2.", [
            (lambda: [FadeIn(ha, shift=0.1 * UP), glow(f1[0], YELLOW_M)], 0.8),
        ])

        # ---------------- scene 5: world B ----------------
        lead_b, f1_b, f2_b = node("leader", L_B, RED_M), node("follower 1", F1_B), node("follower 2", F2_B)
        b_lf1, b_lf2 = edge_arrow(lead_b, f1_b), edge_arrow(lead_b, f2_b)
        b_21 = harr(F2_B[0] - BW / 2 - 0.1, F1_B[0] + BW / 2 + 0.1, FY - 0.17)
        ttl_b = T("world B: the leader lies", 24, WHITE).move_to([WB, 3.05, 0])
        liar_b = T("liar", 20, RED_M).move_to([WB + BW / 2 + 0.45, LY, 0])
        vb1 = on(b_lf1, verdict(True))
        vb2 = on(b_lf2, verdict(False))
        vb3 = on(b_21, verdict(False))
        self.steps("In world B, the leader lies. It tells follower 1 approve, and follower 2 decline.", [
            (lambda: [FadeIn(ttl_b, shift=0.1 * DOWN), FadeIn(VGroup(lead_b, f1_b, f2_b)), FadeIn(liar_b)], 0.8),
            "It tells follower 1",
            (lambda: [GrowArrow(b_lf1), FadeIn(vb1, scale=0.7)], 0.6),
            "and follower 2",
            (lambda: [GrowArrow(b_lf2), FadeIn(vb2, scale=0.7)], 0.6),
        ])
        hb = heard(WB, [True, False])
        self.steps("Follower 2 is honest, and passes its decline on. So follower 1 hears approve from the leader, and decline from follower 2.", [
            (lambda: [GrowArrow(b_21), FadeIn(vb3, scale=0.7)], 0.7),
            "So follower 1",
            (lambda: [FadeIn(hb, shift=0.1 * UP), glow(f1_b[0], YELLOW_M)], 0.8),
        ])
        self.steps("Exactly the same as in world A.", [
            (lambda: [Indicate(ha, color=YELLOW_M, scale_factor=1.05), Indicate(hb, color=YELLOW_M, scale_factor=1.05)], 1.0),
        ])

        # ---------------- scene 6: predict, and the break ----------------
        self.steps("So what should follower 1 decide? Pause and guess.", [
            (lambda: self.cap("what should follower 1 decide?   pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        must_a = T("follower 1 must approve", 22, OK_C).move_to([WA, -2.5, 0])
        must_b = T("follower 1 must match follower 2", 22, YELLOW_M).move_to([WB, -2.5, 0])
        self.steps("In world A, it must approve, because an honest leader's verdict has to win.", [
            (lambda: [*self.uncap(), FadeIn(must_a, shift=0.1 * UP)], 0.6),
            "an honest leader's",
            (lambda: [glow(lead[0], OK_C)], 0.7),
        ])
        self.steps("In world B, it must decide the same as follower 2, the other honest node, whose view is the mirror of its own.", [
            (lambda: [FadeIn(must_b, shift=0.1 * UP)], 0.6),
            "the other honest",
            (lambda: [glow(f2_b[0], YELLOW_M)], 0.7),
        ])
        self.steps("One verdict each way is a tie, and nothing in the tie tells the two worlds apart.", [
            (lambda: self.cap("one APPROVE, one DECLINE: a tie, in both worlds", WHITE), 0.5),
        ])
        split1 = T("approves", 20, OK_C).move_to([F1_B[0], FY - 0.62, 0])
        split2 = T("declines", 20, NO_C).move_to([F2_B[0], FY - 0.62, 0])
        over = T("declines", 20, NO_C).move_to([F1_A[0], FY - 0.62, 0])
        xa = tick(False, 0.18).move_to([WA, FY + 0.72, 0])
        xb = tick(False, 0.18).move_to([WB, FY + 0.72, 0])
        self.steps("Trust the leader on a tie, and world B splits: one follower approves, the other declines.", [
            (lambda: self.cap("rule 1: on a tie, trust the leader", PURPLE_M), 0.5),
            "one follower approves",
            (lambda: [FadeIn(split1)], 0.4),
            "the other declines",
            (lambda: [FadeIn(split2), Create(xb)], 0.6),
        ])
        self.steps("Pick a fixed answer instead, say decline, and in world A a lying follower overrules an honest leader.", [
            (lambda: [*self.cap("rule 2: on a tie, always decline", PURPLE_M), FadeOut(split1), FadeOut(split2)], 0.5),
            "a lying follower",
            (lambda: [FadeIn(over), Create(xa)], 0.6),
        ])
        self.steps("The lesson's lab tries every rule and every lie. With three nodes, every rule breaks. Well... "
                   "two honest against one liar wasn't enough.", [
            (lambda: self.cap("the lab, 3 nodes: every tie rule breaks", RED_M), 0.5),
            "Well",
            (lambda: [Indicate(self.capm, color=RED_M, scale_factor=1.04)], 0.6),
        ], after=0.5)

        # ---------------- scene 7: a fourth node ----------------
        P4 = {"L": (0, 2.3), "1": (-4.4, 0.3), "2": (4.4, 0.3), "3": (0, -1.3)}
        n4 = {k: node(s, P4[k]) for k, s in [("L", "leader"), ("1", "follower 1"), ("2", "follower 2"), ("3", "follower 3")]}
        worlds = VGroup(lead, f1, f2, a_lf1, a_lf2, a_21, va1, va2, va3, ttl_a, liar_a, ha, must_a, over, xa,
                        lead_b, f1_b, f2_b, b_lf1, b_lf2, b_21, vb1, vb2, vb3, ttl_b, liar_b, hb, must_b, xb)
        self.steps("Add a fourth node. Now each follower hears three verdicts: one from the leader, and two passed on by the others.", [
            (lambda: [*self.uncap(), FadeOut(worlds)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(n4[k], shift=0.1 * UP) for k in "L123"], lag_ratio=0.25)], 1.0),
            "three verdicts",
            (lambda: self.cap("each follower hears 3 verdicts: 1 from the leader, 2 passed on", WHITE), 0.5),
        ])
        l1 = edge_arrow(n4["L"], n4["1"])
        l2 = edge_arrow(n4["L"], n4["2"])
        l3 = edge_arrow(n4["L"], n4["3"])
        r21 = edge_arrow(n4["2"], n4["1"])
        r31 = edge_arrow(n4["3"], n4["1"])
        lv = [on(l1, verdict(True)), on(l2, verdict(True)), on(l3, verdict(True), 0.3)]
        rv2 = on(r21, verdict(False), 0.3)
        rv3 = on(r31, verdict(True), 0.45)
        liar2 = T("liar", 20, RED_M).move_to([4.4, 0.3 - 0.62, 0])
        h4 = heard(-4.4, [True, False, True], y=-1.65, label=None)
        h4lab = T("follower 1 heard:", 20, GREY_B).move_to([-4.4, -1.08, 0])
        self.steps("Let follower 2 lie. The leader says approve to everyone. Follower 2 tells follower 1 decline, and follower 3 passes on approve.", [
            (lambda: [*self.uncap(), n4["2"][0].animate.set_stroke(RED_M), FadeIn(liar2)], 0.5),
            "The leader says",
            (lambda: [GrowArrow(l1), GrowArrow(l2), GrowArrow(l3), *[FadeIn(v, scale=0.7) for v in lv]], 0.8),
            "Follower 2 tells",
            (lambda: [*[m.animate.set_opacity(0.3) for m in (l2, l3, lv[1], lv[2])], GrowArrow(r21), FadeIn(rv2, scale=0.7)], 0.7),
            "and follower 3",
            (lambda: [GrowArrow(r31), FadeIn(rv3, scale=0.7)], 0.7),
        ])
        self.steps("The liar spoils one verdict out of three. Follower 1 still hears approve twice, and the honest majority wins.", [
            (lambda: [FadeIn(h4lab), FadeIn(h4, shift=0.1 * UP)], 0.6),
            "approve twice",
            (lambda: [Indicate(h4[0], color=OK_C), Indicate(h4[2], color=OK_C)], 0.8),
            "the honest majority",
            (lambda: self.cap("2 APPROVE to 1: the honest leader wins", OK_C), 0.5),
        ])
        lv2 = on(l2, verdict(False))
        self.steps("If the leader lies instead, the followers pass on honestly what they got. So every honest follower hears the same three verdicts, "
                   "and reaches the same decision.", [
            (lambda: [*self.uncap(), n4["2"][0].animate.set_stroke(WHITE), n4["L"][0].animate.set_stroke(RED_M),
                      liar2.animate.move_to([0 + BW / 2 + 0.45, 2.3, 0]), l2.animate.set_opacity(1),
                      swap(lv[1], lv2), *self.cap("say the leader tells follower 2 DECLINE; follower 2 now passes it on honestly")], 0.8),
            "every honest follower",
            (lambda: [glow(n4["1"][0], YELLOW_M), glow(n4["2"][0], YELLOW_M), glow(n4["3"][0], YELLOW_M),
                      *self.cap("a lying leader: every honest follower hears the same three", WHITE)], 0.9),
        ])
        self.steps("The lab runs every way one node can lie with four nodes, 40 rounds, and not one of them breaks.", [
            (lambda: self.cap("the lab, 4 nodes: 40 rounds, none breaks", OK_C), 0.5),
        ], after=0.4)

        # ---------------- scene 8: the name, and the count ----------------
        self.steps("A node that lies like this has a name: a Byzantine fault. It comes from a 1982 paper by Lamport, Shostak and Pease, "
                   "told as a story about generals agreeing on a plan by messenger, while some of them are traitors.", [
            (lambda: self.cap("a Byzantine fault: a node that lies", WHITE, 28), 0.5),
            "It comes from",
            (lambda: self.cap("Lamport, Shostak and Pease, 1982: generals, messengers, and traitors"), 0.5),
        ])
        four = VGroup(*n4.values(), l1, l2, l3, r21, r31, lv[0], lv2, lv[2], rv2, rv3, liar2, h4, h4lab)
        rule = [T(s, 30, c) for s, c in [("with N nodes, wait for at most  N − f  replies", WHITE),
                                         ("up to  f  of them may be lies", RED_M),
                                         ("so at least  N − 2f  are honest", OK_C),
                                         ("honest must outnumber lies:  N − 2f > f", WHITE),
                                         ("N > 3f,   so  N = 3f + 1", YELLOW_M)]]
        VGroup(*rule).arrange(DOWN, buff=0.32).move_to([0, 0.2, 0])
        self.steps("The general rule: surviving f liars takes at least 3f + 1 nodes. Here's why.", [
            (lambda: [FadeOut(four), *self.cap("surviving f liars takes at least 3f + 1 nodes", YELLOW_M)], 0.7),
        ])
        self.steps("With N nodes, a decision can't wait for more than N minus f replies, because the faulty ones may never answer.", [
            (lambda: [FadeIn(rule[0], shift=0.1 * UP), *self.uncap()], 0.6),
        ])
        self.steps("Up to f of those replies may be lies. So at least N minus 2f are honest, and they must outnumber the lies.", [
            (lambda: [FadeIn(rule[1], shift=0.1 * UP)], 0.5),
            "So at least",
            (lambda: [FadeIn(rule[2], shift=0.1 * UP)], 0.5),
            "they must outnumber",
            (lambda: [FadeIn(rule[3], shift=0.1 * UP)], 0.5),
        ])
        self.steps("N minus 2f bigger than f means N bigger than 3f. For one liar, that's four.", [
            (lambda: [FadeIn(rule[4], shift=0.1 * UP)], 0.5),
            "For one liar",
            (lambda: [glow(rule[4], YELLOW_M, 1.04), *self.cap("f = 1:  N = 4", YELLOW_M, 28)], 0.7),
        ])
        self.steps("If computers only crash, 2f + 1 is enough, three for one crash, because a crashed node never says anything false.", [
            (lambda: self.cap("crashes only: 2f + 1 (a crashed node never says anything false)", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 9: the guardrail ----------------
        pay = [node("copy", (x, 0.6)) for x in (-4.5, -1.5, 1.5, 4.5)]
        for p in pay:
            p[0].set_stroke(GREEN_M)
        self.steps("Some systems do pay for this. PBFT, short for practical Byzantine fault tolerance, runs 3f + 1 copies of a program, "
                   "with three rounds of messages for each request.", [
            (lambda: [FadeOut(VGroup(*rule)), *self.cap("PBFT (Castro and Liskov, 1999): 3f + 1 copies, 3 rounds per request", WHITE)], 0.7),
            "runs 3f",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * UP) for p in pay], lag_ratio=0.2)], 1.0),
        ])
        self.steps("Its authors' file server ran only 3% slower than a plain one. Blockchains, shared records kept by parties who don't trust each other, "
                   "use the same family.", [
            (lambda: self.cap("their file server: only 3% slower"), 0.5),
            "Blockchains",
            (lambda: self.cap("the same family: blockchains, shared records between parties who don't trust each other"), 0.5),
        ])
        self.steps("A payments database almost certainly doesn't. Surviving one liar takes four copies instead of three, and more rounds of messages.", [
            (lambda: [*self.cap("a payments database: almost certainly not"), *[p[0].animate.set_stroke(BLUE_M) for p in pay]], 0.8),
            "four copies",
            (lambda: [glow(pay[3][0], GOLD_M), *self.cap("one liar: 4 copies instead of 3, and more rounds", WHITE)], 0.7),
        ])
        bugs = [T("same bug", 20, RED_M).move_to([p.get_center()[0], -0.25, 0]) for p in pay]
        self.steps("And it wouldn't help. Every copy runs the same code, so a bug lies the same way four times. "
                   "Four copies of one bug just agree with each other, very confidently.", [
            "Every copy",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in bugs], lag_ratio=0.2),
                      *[p[0].animate.set_stroke(RED_M) for p in pay]], 1.0),
            "Four copies",
            (lambda: self.cap("four copies of one bug: a confident, unanimous wrong answer", RED_M), 0.5),
        ])
        self.steps("An attacker's trick that breaks into one copy usually breaks into all of them. Checking who is asking, "
                   "limiting what each program may touch, encryption and firewalls do that job.", [
            (lambda: self.cap("an attacker's trick for one copy usually works on all"), 0.5),
            "Checking who",
            (lambda: self.cap("instead: check who is asking, limit what each program may touch, encryption, firewalls", WHITE), 0.6),
        ])

        # ---------------- scene 10: moral, and a check ----------------
        hm = heard(0, [True, False], y=0.6, label="hears:")
        self.steps("So, two honest against one liar? Not enough. A follower that hears one verdict each way can't tell a lying leader from a lying friend.", [
            (lambda: [FadeOut(VGroup(*pay, *bugs)), *self.cap("2 honest vs 1 liar: not enough", WHITE)], 0.6),
            "A follower that hears",
            (lambda: [FadeIn(hm, shift=0.1 * UP)], 0.6),
        ])
        hm3 = heard(0, [True, False, True], y=0.6, label="hears:")
        self.steps("Give it three verdicts, and one liar can only spoil one. One liar takes four nodes.", [
            (lambda: [FadeOut(hm), FadeIn(hm3, shift=0.1 * UP)], 0.6),
            "One liar takes",
            (lambda: self.cap("one liar takes four nodes:  3f + 1", YELLOW_M, 32), 0.6),
        ], after=0.5)
        self.steps("One quick check. How many nodes does it take to survive two liars? Pause and think.", [
            (lambda: [FadeOut(hm3), *self.cap("two liars: how many nodes?   pause and think", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0, y=0.6)
        ans = T("3 × 2 + 1  =  7", 56, YELLOW_M).move_to([0, 0.6, 0])
        self.steps("Seven. Three times two, plus one.", [
            (lambda: [Write(ans), *self.cap("two liars: 7 nodes", YELLOW_M, 28)], 0.9),
        ], after=0.3)
        self.wait(2.0)
