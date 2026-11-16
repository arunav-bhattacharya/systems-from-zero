from sfz import *

SAY.insert(0, (r"\b3f \+ 1\b", "three F plus one"))
SAY.insert(0, (r"\b2f \+ 1\b", "two F plus one"))
SAY.insert(0, (r"\bf lying\b", "F lying"))
SAY.insert(0, (r"\bCRC\b", "C R C"))

P3 = {0: (-2.7, 2.1), 1: (-5.0, -1.2), 2: (-0.4, -1.2)}
P4 = {0: (-2.7, 2.2), 1: (-5.1, -0.8), 2: (-2.7, -2.35), 3: (-0.3, -0.8)}
NW, NH = 2.3, 0.85
NAMES = {0: "leader", 1: "follower 1", 2: "follower 2", 3: "follower 3"}
VC = {"approve": GREEN_M, "decline": GOLD_M}
PX = 1.6
PL = [1.95, 1.5, 1.05, 0.35, -0.1, -0.55, -1.25, -1.75, -2.25, -2.75]


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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


def nbox(i, pos, color=WHITE, decision=None, dcolor=GREY_B):
    x, y = pos
    r = RoundedRectangle(corner_radius=0.12, width=NW, height=NH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    d = T(decision or "", 18, dcolor) if decision else T("waiting", 18, GREY_D)
    return VGroup(r, T(NAMES[i], 22).move_to([x, y + 0.17, 0]), d.move_to([x, y - 0.19, 0]))


def decide(i, pos, v, color=WHITE):
    return nbox(i, pos, color, f"decides: {v}", VC.get(v, GREY_B))


def rect_at(pos):
    return Rectangle(width=NW, height=NH).move_to([pos[0], pos[1], 0])


def msg(pa, pb, color=GREY_B):
    return edge_arrow(rect_at(pa), rect_at(pb), color, buff=0.1)


def vchip(v, pos, said=False, solid=False):
    c = chip(("said: " if said else "") + v, VC[v], 20).move_to([pos[0], pos[1], 0])
    if solid:
        c[0].set_fill(fillc(VC[v], 0.25), 1)
    return c


def pline(s, k, color=GREY_B, size=20):
    return left_at(T(s, size, color), PX, PL[k])


def tag(s, x, y, color=RED_M):
    return left_at(T(s, 20, color), x, y)


class Byzantine(Base):
    """dist-07, section 3 (with section 4's small lies): three nodes decide one payment; one lies. World A: honest leader
    says approve, follower 2 lies that it said decline. World B: the leader tells follower 1 approve and follower 2 decline.
    Follower 1 hears the same in both, so no rule works. Four nodes: each follower hears three verdicts, one liar spoils at
    most one. 3f + 1 for lies, 2f + 1 for crashes. Databases assume crashes and use checksums: one flipped bit turns
    40.00 into 50.00 and the CRC-32C no longer matches."""

    def construct(self):
        self.title_card("Byzantine faults", "why one liar takes four nodes to out-vote")

        n = {i: nbox(i, P3[i]) for i in range(3)}
        l1, l2 = msg(P3[0], P3[1]), msg(P3[0], P3[2])
        c1 = vchip("approve", (-4.95, 0.6))
        c2 = vchip("approve", (-0.45, 0.6))
        self.steps("Three nodes must agree: approve this payment, or decline it. The leader sends its verdict to both "
                   "followers.", [
            (lambda: [LaggedStart(*[FadeIn(n[i], scale=0.95) for i in range(3)], lag_ratio=0.25)], 1.2),
            "The leader",
            (lambda: [glow(n[0][0], WHITE)], 0.7),
            "sends its verdict",
            (lambda: [GrowArrow(l1), GrowArrow(l2)], 0.6),
            (lambda: [flow(l1, GREEN_M, 0.7), flow(l2, GREEN_M, 0.7)], 0.7),
            (lambda: [FadeIn(c1, scale=0.9), FadeIn(c2, scale=0.9)], 0.5),
        ])

        y21, y12 = -1.0, -1.4
        r21 = Arrow([P3[2][0] - NW / 2 - 0.08, y21, 0], [P3[1][0] + NW / 2 + 0.08, y21, 0], buff=0, stroke_width=3,
                    color=GREY_B, max_tip_length_to_length_ratio=0.08)
        r12 = Arrow([P3[1][0] + NW / 2 + 0.08, y12, 0], [P3[2][0] - NW / 2 - 0.08, y12, 0], buff=0, stroke_width=3,
                    color=GREY_B, max_tip_length_to_length_ratio=0.08)
        self.steps("Each follower passes on what the leader said, then decides by majority.", [
            (lambda: [GrowArrow(r21), GrowArrow(r12)], 0.6),
            (lambda: [flow(r21, GREEN_M, 0.7), flow(r12, GREEN_M, 0.7)], 0.7),
            "then decides",
            (lambda: [Transform(n[1], decide(1, P3[1], "approve")), Transform(n[2], decide(2, P3[2], "approve"))], 0.8),
        ])

        lie2 = tag("lies", P3[2][0] - 0.25, P3[2][1] - NH / 2 - 0.3)
        cr = vchip("decline", (-2.7, -0.55), said=True)
        ptitle = left_at(T("what follower 1 hears", 24), PX, 2.6)
        wa = [pline("world A: follower 2 lies", 0, RED_M), pline("leader: approve", 1, WHITE),
              pline("follower 2: it said decline", 2, WHITE)]
        self.steps("Now let one node lie. In world A, the leader is honest and says approve. Follower 2 lies: it tells "
                   "follower 1 the leader said decline.", [
            (lambda: [Transform(n[1], nbox(1, P3[1])), Transform(n[2], nbox(2, P3[2])), r12.animate.set_opacity(0.25),
                      FadeIn(ptitle)], 0.7),
            "In world A",
            (lambda: [FadeIn(wa[0]), glow(n[0][0], GREEN_M)], 0.7),
            (lambda: [FadeIn(wa[1])], 0.4),
            "Follower 2 lies",
            (lambda: [Transform(n[2], nbox(2, P3[2], RED_M)), FadeIn(lie2)], 0.6),
            "it tells",
            (lambda: [flow(r21, GOLD_M, 0.7)], 0.7),
            (lambda: [FadeIn(cr, scale=0.9), FadeIn(wa[2])], 0.5),
        ])

        lie0 = tag("lies", P3[0][0] + NW / 2 + 0.2, P3[0][1])
        c2d = vchip("decline", (-0.45, 0.6))
        wb = [pline("world B: the leader lies", 3, RED_M), pline("leader: approve", 4, WHITE),
              pline("follower 2: it said decline", 5, WHITE)]
        self.steps("In world B, the leader lies. It tells follower 1 approve and follower 2 decline, and follower 2 "
                   "honestly passes decline on.", [
            (lambda: [Transform(n[2], nbox(2, P3[2])), FadeOut(lie2), FadeOut(cr), FadeIn(wb[0])], 0.7),
            "the leader lies",
            (lambda: [Transform(n[0], nbox(0, P3[0], RED_M)), FadeIn(lie0)], 0.6),
            "It tells",
            (lambda: [FadeOut(c1), FadeOut(c2), flow(l1, GREEN_M, 0.6), flow(l2, GOLD_M, 0.6)], 0.7),
            (lambda: [FadeIn(c1), FadeIn(c2d), FadeIn(wb[1])], 0.5),
            "and follower 2",
            (lambda: [flow(r21, GOLD_M, 0.7)], 0.7),
            (lambda: [FadeIn(cr, scale=0.9), FadeIn(wb[2])], 0.5),
        ])

        box_a = SurroundingRectangle(VGroup(*wa[1:]), color=YELLOW_M, buff=0.12, corner_radius=0.08, stroke_width=2.5)
        box_b = SurroundingRectangle(VGroup(*wb[1:]), color=YELLOW_M, buff=0.12, corner_radius=0.08, stroke_width=2.5)
        same = pline("the same two messages: who lied?", 6, YELLOW_M, 22)
        self.steps("Follower 1 hears exactly the same thing in both worlds: approve from the leader, decline from "
                   "follower 2. It can't tell who is lying.", [
            (lambda: [glow(n[1][0], YELLOW_M)], 0.8),
            "the same thing",
            (lambda: [Create(box_a), Create(box_b)], 0.9),
            "It can't tell",
            (lambda: [FadeIn(same, shift=0.1 * UP)], 0.7),
        ])

        t1 = pline("trust the leader: world B splits", 7, RED_M)
        t2 = pline("trust follower 2: world A overrules", 8, RED_M)
        t3 = pline("an honest leader", 9, RED_M)
        split = T("split", 22, RED_M).move_to([-2.7, -2.05, 0])
        self.steps("Trust the leader, and world B ends split. Trust the peer, and world A overrules an honest leader. "
                   "No rule gets both right.", [
            (lambda: [FadeIn(t1), Transform(n[1], decide(1, P3[1], "approve"))], 0.7),
            "ends split",
            (lambda: [Transform(n[2], decide(2, P3[2], "decline")), FadeIn(split)], 0.7),
            "Trust the peer",
            (lambda: [FadeIn(t2), FadeIn(t3)], 0.7),
            "No rule",
            (lambda: [glow(box_a, RED_M, 1.02), glow(box_b, RED_M, 1.02)], 0.9),
        ])

        # ---- four nodes ------------------------------------------------------------------------------------------------
        n3 = nbox(3, P4[3])
        L = {i: msg(P4[0], P4[i]) for i in (1, 2, 3)}
        rel = VGroup(*[Line(*ends(rect_at(P4[a]), rect_at(P4[b])), stroke_width=2, color=GREY_D)
                       for a, b in [(1, 2), (2, 3), (1, 3)]])
        self.steps("Add a fourth node. Now each follower hears three verdicts: one from the leader, and two passed on "
                   "by the others.", [
            (lambda: [FadeOut(VGroup(*wa, *wb, box_a, box_b, same, t1, t2, t3, ptitle, split, lie0, cr, c1, c2d, r21, r12,
                                     l1, l2))], 0.7),
            (lambda: [Transform(n[0], nbox(0, P4[0])), Transform(n[1], nbox(1, P4[1])), Transform(n[2], nbox(2, P4[2]))], 0.8),
            (lambda: [FadeIn(n3, scale=0.95)], 0.5),
            "Now each follower",
            (lambda: [*[GrowArrow(L[i]) for i in L]], 0.5),
            (lambda: [*[flow(L[i], GREEN_M, 0.6) for i in L]], 0.6),
            "and two passed on",
            (lambda: [Create(rel)], 0.5),
            (lambda: [*[flow(l, GREEN_M, 0.6) for l in rel], *[flow(l, GREEN_M, 0.6, back=True) for l in rel]], 0.7),
        ])
        n[3] = n3

        lie2b = tag("lies", P4[2][0] + NW / 2 + 0.2, P4[2][1])
        CP = {1: 0.4, 2: 0.55, 3: 0.4}
        ch = {i: vchip("approve", L[i].point_from_proportion(CP[i])[:2], solid=True) for i in (1, 2, 3)}
        h1 = pline("follower 1: approve, approve, decline", 0, WHITE)
        h3 = pline("follower 3: approve, approve, decline", 2, WHITE)
        ptitle2 = left_at(T("what each follower hears", 24), PX, 2.6)
        self.steps("Let follower 2 lie. It spoils one verdict out of three. Followers 1 and 3 still hear two approves, "
                   "so the majority wins.", [
            (lambda: [FadeIn(VGroup(*ch.values())), FadeIn(ptitle2), Transform(n[2], nbox(2, P4[2], RED_M)), FadeIn(lie2b)], 0.8),
            "It spoils",
            (lambda: [flow(rel[0], GOLD_M, 0.7, back=True), flow(rel[1], GOLD_M, 0.7)], 0.8),
            "Followers 1 and 3",
            (lambda: [FadeIn(h1), FadeIn(h3)], 0.6),
            "so the majority",
            (lambda: [Transform(n[1], decide(1, P4[1], "approve")), Transform(n[3], decide(3, P4[3], "approve"))], 0.8),
        ])

        lie0b = tag("lies", P4[0][0] + NW / 2 + 0.2, P4[0][1])
        ch2d = vchip("decline", L[2].point_from_proportion(CP[2])[:2], solid=True)
        g1 = pline("follower 1: approve, decline, approve", 0, WHITE)
        g2 = pline("follower 2: decline, approve, approve", 1, WHITE)
        g3 = pline("follower 3: approve, approve, decline", 2, WHITE)
        agree = pline("all three decide approve", 3, GREEN_M, 22)
        self.steps("If the leader lies instead, it can split its story, but the followers pass on what they got. "
                   "Each hears approve twice and decline once, so all three agree.", [
            (lambda: [Transform(n[2], nbox(2, P4[2])), FadeOut(lie2b), Transform(n[1], nbox(1, P4[1])),
                      Transform(n[3], nbox(3, P4[3])), FadeOut(h1), FadeOut(h3)], 0.6),
            (lambda: [Transform(n[0], nbox(0, P4[0], RED_M)), FadeIn(lie0b)], 0.5),
            "it can split",
            (lambda: [Transform(ch[2], ch2d), flow(L[2], GOLD_M, 0.6)], 0.7),
            "but the followers",
            (lambda: [*[flow(l, GREY_A, 0.6) for l in rel], *[flow(l, GREY_A, 0.6, back=True) for l in rel]], 0.7),
            (lambda: [LaggedStart(FadeIn(g1), FadeIn(g2), FadeIn(g3), lag_ratio=0.3)], 0.9),
            "so all three agree",
            (lambda: [*[Transform(n[i], decide(i, P4[i], "approve")) for i in (1, 2, 3)], FadeIn(agree)], 0.8),
        ])

        rule1 = chip("lies: 3f + 1 nodes to survive f liars", RED_M, 22).move_to([4.05, -0.9, 0])
        rule2 = chip("crashes: 2f + 1 nodes", GREY_B, 22).move_to([4.05, -1.75, 0])
        self.steps("In general, surviving f lying nodes takes 3f + 1 of them. Crashes need only 2f + 1, because a crashed "
                   "node never says anything false.", [
            (lambda: [FadeIn(rule1, shift=0.1 * UP)], 0.8),
            "Crashes need",
            (lambda: [FadeIn(rule2, shift=0.1 * UP)], 0.8),
            "because a crashed",
            (lambda: [glow(n[3][0], GREY_B)], 0.9),
        ])

        same_code = pline("one codebase on every replica", 0, RED_M, 22)
        self.steps("Most databases don't pay for that. Their replicas all run the same code, so a bug that makes one lie "
                   "makes them all lie the same way.", [
            (lambda: [FadeOut(VGroup(g1, g2, g3, agree, ptitle2, lie0b, *ch.values())), FadeOut(rule1), FadeOut(rule2),
                      *[Transform(n[i], nbox(i, P4[i])) for i in range(4)]], 0.8),
            "Their replicas",
            (lambda: [FadeIn(same_code)], 0.6),
            "so a bug",
            (lambda: [*[n[i][0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1) for i in range(4)]], 0.9),
        ])

        crashed = tick(False, 0.35).move_to([*P4[3], 0])
        crash_m = pline("usual model: nodes crash, never lie", 0, WHITE, 22)
        rec = left_at(M("pay-7731|m-cafe|EUR|00004000|CAPTURED", 17), PX, -0.6)
        reclab = left_at(T("one record, with its checksum", 20, GREY_B), PX, -0.1)
        crc = left_at(M("stored crc32c: 7d47b10e", 17, GREEN_M), PX, -1.1)
        self.steps("So they assume nodes crash, and guard against the small lies: a bit flipped on disk or in memory.", [
            (lambda: [*[n[i][0].animate.set_stroke(WHITE).set_fill(BLACK, 1) for i in range(4)],
                      Transform(same_code, crash_m)], 0.8),
            (lambda: [Create(crashed), n[3].animate.set_opacity(0.4)], 0.6),
            "and guard against",
            (lambda: [FadeIn(reclab), FadeIn(rec)], 0.6),
            "a bit flipped",
            (lambda: [FadeIn(crc)], 0.6),
        ])

        digit = rec[24]
        five = M("5", 17, RED_M).move_to(digit)
        now = left_at(M("crc32c now:    4d95896b", 17, RED_M), PX, -1.55)
        caught = pline("mismatch: the read fails loudly", 8, RED_M, 22)
        self.steps("A checksum on every record, checked on every read, catches those. One flipped bit turns 40 euros "
                   "into 50, and the CRC no longer matches.", [
            (lambda: [crc.animate(rate_func=there_and_back).scale(1.1)], 0.7),
            "One flipped bit",
            (lambda: [Transform(digit, five)], 0.7),
            "and the CRC",
            (lambda: [FadeIn(now, shift=0.1 * UP)], 0.6),
            (lambda: [FadeIn(caught, shift=0.1 * UP)], 0.6),
        ])

        frame = SurroundingRectangle(VGroup(rec, crc, now), color=GREY_B, buff=0.15, corner_radius=0.08, stroke_width=2)
        self.steps("One liar takes four nodes to out-vote. Most systems assume crashes instead, and use checksums for the "
                   "small lies.", [
            (lambda: [n[3].animate.set_opacity(1), FadeOut(crashed)], 0.6),
            (lambda: [*[glow(n[i][0], WHITE, 1.05) for i in range(4)]], 0.9),
            "and use checksums",
            (lambda: [FadeIn(frame)], 0.5),
            (lambda: [glow(frame, GREEN_M, 1.02)], 0.8),
        ])
        self.wait(0.6)
