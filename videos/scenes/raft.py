from sfz import *

# "pay-A" alone reads as "pay uh"; "eh" lands on the letter.
SAY.insert(0, (r"\bpay-A\b", "pay eh"))
SAY.insert(0, (r"\bpay-B\b", "pay B"))
SAY.insert(0, (r"\bpay-C\b", "pay C"))
SAY.insert(0, (r"\bRequestVote\b", "request vote"))
SAY.insert(0, (r"\bAppendEntries\b", "append entries"))

# a ring of five, stretched wide so every message between neighbours has room to show
P = {3: np.array([-0.6, 2.5, 0]), 2: np.array([-3.7, 0.35, 0]), 4: np.array([2.5, 0.35, 0]),
     1: np.array([-2.2, -2.45, 0]), 5: np.array([1.0, -2.45, 0])}
CW, CH = 2.3, 1.25
ROLE_C = {"follower": GREY_B, "candidate": GOLD_M, "leader": BLUE_M}
TIMEOUT = {1: 241, 2: 205, 3: 162, 4: 274, 5: 228}   # ms, drawn from 150 to 300
ST_X, ST_Y = 2.65, [-0.8, -1.3, -1.8]                  # status lines, right of the ring
RULE_X, RULE_Y = -6.5, [3.1, 2.65]                   # rule lines, top left
CLIENT = np.array([4.9, P[3][1], 0])
CUT_Y = 1.42


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


def fillc(color):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def srv(i, role="follower", term=0, note=None):
    x, y = P[i][0], P[i][1]
    color = WHITE if role == "follower" else ROLE_C[role]
    r = RoundedRectangle(corner_radius=0.14, width=CW, height=CH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    n = left_at(T(f"S{i}", 28), x - 0.95, y + 0.36)
    ro = right_at(T(role, 20, ROLE_C[role]), x + 0.95, y + 0.36)
    te = left_at(T(f"term {term}" + (f", {note}" if note else ""), 20, GREY_B), x - 0.95, y + 0.0)
    slots = VGroup(*[RoundedRectangle(corner_radius=0.06, width=0.95, height=0.34, stroke_color=GREY_D, stroke_width=1.5)
                     .move_to(slot_xy(i, k)) for k in range(2)])
    return VGroup(r, n, ro, te, slots)


def slot_xy(i, k):
    return [P[i][0] + (-0.55 if k == 0 else 0.5), P[i][1] - 0.36, 0]


def entry(i, k, name, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.06, width=0.95, height=0.34, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to(slot_xy(i, k))
    return VGroup(r, M(name, 16, WHITE).move_to(slot_xy(i, k)))


def msg(a, b, color=GOLD_M):
    return edge_arrow(srvs_rect(a), srvs_rect(b), color, buff=0.1)


def srvs_rect(i):
    return Rectangle(width=CW, height=CH).move_to(P[i])


def go(ar, color, rt=0.7):
    return travel(ar, color, rt)


def back(ar, color, rt=0.7):
    return travel(Line(ar.get_end(), ar.get_start()), color, rt)


def lost(ar, color, frac=0.55):
    """A message that dies partway; returns (animation, point where it died)."""
    s, e = ar.get_start(), ar.get_end()
    mid = s + frac * (e - s)
    d = Dot(radius=0.08, color=color).move_to(s)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(s, mid), run_time=0.6), FadeOut(d, run_time=0.25)), mid


def status(s, k, color=GREY_B, size=20):
    return left_at(T(s, size, color), ST_X, ST_Y[k])


def rule(s, k=0, color=GREY_B):
    return left_at(T(s, 20, color), RULE_X, RULE_Y[k])


class Raft(Base):
    """cons-04, section 1 (with section 2's AppendEntries): five servers, S3 times out first at 162 ms, wins term 1 with
    S1, S2 and S4, and commits pay-A on a majority. Cut off, S3 still believes it leads term 1 and appends pay-B; S1 wins
    term 2 and commits pay-C; when the network heals, the higher term makes S3 step down and pay-C replaces pay-B."""

    def construct(self):
        self.title_card("Raft: one leader at a time", "elections, terms and a log copied to a majority")

        sv = {i: srv(i) for i in range(1, 6)}
        r1 = rule("Raft: one leader takes every write")
        self.steps("Five servers keep the same log of payments. Raft picks one leader to take every write and copy it "
                   "to the others.", [
            (lambda: [LaggedStart(*[FadeIn(sv[i], scale=0.95) for i in (3, 4, 5, 1, 2)], lag_ratio=0.2)], 1.4),
            "Raft picks",
            (lambda: [FadeIn(r1, shift=0.1 * DOWN)], 0.7),
        ])

        r2 = rule("a term: at most one leader", 1)
        self.steps("All start as followers in term 0. A term is a numbered period with at most one leader.", [
            (lambda: [*[Indicate(sv[i][2], color=YELLOW_M) for i in sv]], 0.9),
            "A term is",
            (lambda: [*[Indicate(sv[i][3], color=YELLOW_M) for i in sv], FadeIn(r2, shift=0.1 * DOWN)], 0.9),
        ])

        tk = ValueTracker(0)

        def bar(i):
            x, y = P[i][0], P[i][1] - CH / 2 - 0.17
            x0, x1 = x - 1.05, x + 1.05

            def make():
                f = min(tk.get_value(), TIMEOUT[i]) / 300
                done = tk.get_value() >= TIMEOUT[i]
                bg = Line([x0, y, 0], [x1, y, 0], stroke_width=5, color=GREY_D)
                fg = Line([x0, y, 0], [x0 + max(f, 0.002) * (x1 - x0), y, 0], stroke_width=5, color=GOLD_M if done else GREY_B)
                tm = Line([x0 + TIMEOUT[i] / 300 * (x1 - x0), y - 0.11, 0], [x0 + TIMEOUT[i] / 300 * (x1 - x0), y + 0.11, 0],
                          stroke_width=2.5, color=GOLD_M if i == 3 else GREY_C)
                return VGroup(bg, fg, tm)
            return always_redraw(make)

        bars = VGroup(*[bar(i) for i in sv])
        r3 = rule("timeout: random, 150 to 300 ms")
        self.steps("A follower that hears from no leader starts an election, after a random wait of 150 to 300 milliseconds.", [
            (lambda: [FadeIn(bars)], 0.6),
            "after a random",
            (lambda: [FadeOut(r1), FadeIn(r3, shift=0.1 * DOWN)], 0.6),
            (lambda: [tk.animate(rate_func=linear).set_value(140)], 2.6),
        ])

        lab162 = T("162 ms", 20, GOLD_M).move_to([P[3][0] - 1.05 + 162 / 300 * 2.1, P[3][1] - CH / 2 - 0.45, 0])
        self.steps("S3 drew the shortest, 162 milliseconds.", [
            (lambda: [tk.animate(rate_func=linear).set_value(162)], 0.8),
            (lambda: [FadeIn(lab162, shift=0.1 * DOWN)], 0.5),
        ])

        va = {i: msg(3, i, GOLD_M) for i in (1, 2, 4, 5)}
        votes = status("votes for S3: 1", 0, GOLD_M)
        self.steps("It moves to term 1, becomes a candidate, votes for itself, and asks the others with RequestVote.", [
            (lambda: [FadeOut(bars), FadeOut(lab162), Transform(sv[3], srv(3, "candidate", 1))], 0.8),
            "votes for itself",
            (lambda: [FadeIn(votes, shift=0.1 * UP)], 0.5),
            "asks the others",
            (lambda: [*[GrowArrow(a) for a in va.values()]], 0.6),
            (lambda: [*[go(a, GOLD_M) for a in va.values()]], 0.8),
        ])
        bars.clear_updaters()

        r4 = rule("one vote per term, saved to disk", 1)
        votes4 = status("votes for S3: 4 of 5", 0, GOLD_M)
        self.steps("Each server grants one vote per term, written to disk first. S1, S2 and S4 say yes.", [
            (lambda: [FadeOut(r2), FadeIn(r4, shift=0.1 * DOWN)], 0.7),
            "S1, S2",
            (lambda: [*[Transform(sv[i], srv(i, "follower", 1, "voted S3")) for i in (1, 2, 4)]], 0.7),
            (lambda: [*[back(va[i], GREEN_M) for i in (1, 2, 4)]], 0.7),
            (lambda: [Transform(votes, votes4)], 0.5),
        ])

        hb = {i: msg(3, i, BLUE_M) for i in (1, 2, 4, 5)}
        maj = status("a majority is 3", 1)
        self.steps("With 4 votes of 5, a majority, S3 leads term 1. Its heartbeat, every 50 milliseconds, keeps the "
                   "others from starting elections.", [
            (lambda: [FadeIn(maj, shift=0.1 * UP)], 0.6),
            "S3 leads",
            (lambda: [Transform(sv[3], srv(3, "leader", 1)), *[ReplacementTransform(va[i], hb[i]) for i in hb]], 0.8),
            "Its heartbeat",
            (lambda: [*[go(hb[i], BLUE_M, 0.6) for i in hb]], 0.6),
            (lambda: [Transform(sv[5], srv(5, "follower", 1)),
                      *[Transform(sv[i], srv(i, "follower", 1)) for i in (1, 2, 4)]], 0.5),
            (lambda: [*[go(hb[i], BLUE_M, 0.6) for i in hb]], 0.6),
        ])

        cl = mbox("client", GREY_B, w=1.6, h=0.62, size=20).move_to(CLIENT)
        ca = Arrow(cl.get_left() + 0.08 * LEFT, [P[3][0] + CW / 2 + 0.1, P[3][1], 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.06)
        eA = {i: entry(i, 0, "pay-A") for i in sv}
        stA = status("entry 1, term 1: pay-A", 0, WHITE)
        self.steps("A client sends pay-A. The leader appends it as entry 1, term 1, and sends it out with AppendEntries.", [
            (lambda: [FadeOut(maj), FadeOut(votes), FadeIn(cl), GrowArrow(ca)], 0.6),
            (lambda: [go(ca, WHITE, 0.6)], 0.6),
            "The leader appends",
            (lambda: [FadeIn(eA[3], scale=0.8), FadeIn(stA)], 0.7),
            "and sends it out",
            (lambda: [*[go(hb[i], BLUE_M) for i in hb]], 0.8),
        ])

        xs = {}

        def lose(i):
            an, pt = lost(hb[i], BLUE_M)
            xs[i] = tick(False, 0.16).move_to(pt)
            return [an]

        self.steps("S1 and S2 store it. The messages to S4 and S5 are lost.", [
            (lambda: [FadeIn(eA[1], scale=0.8), FadeIn(eA[2], scale=0.8)], 0.6),
            (lambda: [back(hb[1], GREEN_M, 0.6), back(hb[2], GREEN_M, 0.6)], 0.6),
            "The messages to",
            (lambda: [*lose(4), *lose(5)], 0.9),
            (lambda: [Create(xs[4]), Create(xs[5])], 0.4),
        ])

        stA2 = status("on 3 of 5: committed", 1, GREEN_M)
        eA[4], eA[5] = entry(4, 0, "pay-A", GREEN_M), entry(5, 0, "pay-A", GREEN_M)
        ok = T("OK", 22, GREEN_M).move_to(CLIENT + 0.6 * DOWN)
        self.steps("Stored on 3 of 5, a majority, pay-A is committed, and the client hears OK. "
                   "The next heartbeat brings S4 and S5 up to date.", [
            (lambda: [FadeIn(stA2, shift=0.1 * UP), *[Transform(eA[i], entry(i, 0, "pay-A", GREEN_M)) for i in (3, 1, 2)]], 0.8),
            "the client hears",
            (lambda: [back(ca, GREEN_M, 0.6), FadeIn(ok)], 0.7),
            "The next heartbeat",
            (lambda: [FadeOut(xs[4]), FadeOut(xs[5]), go(hb[4], BLUE_M), go(hb[5], BLUE_M)], 0.8),
            (lambda: [FadeIn(eA[4], scale=0.8), FadeIn(eA[5], scale=0.8)], 0.6),
        ])

        cut = DashedLine([-2.4, CUT_Y, 0], [1.2, CUT_Y, 0], dash_length=0.12, stroke_width=3, color=RED_M)
        cut_l = right_at(T("network cut", 20, RED_M), -2.55, CUT_Y)
        eB = entry(3, 1, "pay-B")
        stB = status("pay-B: on 1 of 5", 0, GREY_B)
        self.steps("Now the network cuts S3 off. It still thinks it leads term 1, and appends pay-B, but no one can store it.", [
            (lambda: [FadeOut(VGroup(*hb.values())), FadeOut(stA), FadeOut(stA2), FadeOut(ok), Create(cut), FadeIn(cut_l)], 0.8),
            "It still thinks",
            (lambda: [glow(sv[3][0], BLUE_M)], 0.8),
            "and appends",
            (lambda: [go(ca, WHITE, 0.5)], 0.5),
            (lambda: [FadeIn(eB, scale=0.8), FadeIn(stB)], 0.5),
            "but no one",
            (lambda: [*[self._to_cut(i) for i in (1, 2, 4, 5)]], 0.8),
        ])

        s1v = {i: msg(1, i, GOLD_M) for i in (2, 4, 5)}
        eC = {i: entry(i, 1, "pay-C", GREEN_M) for i in (1, 2, 4, 5)}
        stC = status("pay-C: committed, 4 of 5", 1, GREEN_M)
        self.steps("The others hear no heartbeat. S1 times out, wins term 2 with three more votes, and commits pay-C.", [
            "S1 times out",
            (lambda: [Transform(sv[1], srv(1, "candidate", 2)), *[GrowArrow(a) for a in s1v.values()]], 0.7),
            (lambda: [*[go(a, GOLD_M, 0.6) for a in s1v.values()],
                      *[Transform(sv[i], srv(i, "follower", 2, "voted S1")) for i in (2, 4, 5)]], 0.7),
            (lambda: [*[back(a, GREEN_M, 0.6) for a in s1v.values()]], 0.6),
            (lambda: [Transform(sv[1], srv(1, "leader", 2)), *[a.animate.set_color(BLUE_M) for a in s1v.values()]], 0.5),
            "and commits",
            (lambda: [*[FadeIn(eC[i], scale=0.8) for i in eC], FadeIn(stC)], 0.8),
        ])

        h34 = msg(3, 4, BLUE_M)
        t1l = status("S3 sends term 1", 0, BLUE_M)
        t2l = status("the reply says term 2", 1, TEAL_M)
        self.steps("The network heals. S3 sends a heartbeat for term 1, and the reply carries term 2. "
                   "A higher term means a newer leader, so S3 steps down.", [
            (lambda: [FadeOut(cut), FadeOut(cut_l), FadeOut(VGroup(*s1v.values())), FadeOut(stB), FadeOut(stC)], 0.7),
            "S3 sends",
            (lambda: [GrowArrow(h34), FadeIn(t1l)], 0.5),
            (lambda: [go(h34, BLUE_M, 0.6)], 0.6),
            "the reply",
            (lambda: [back(h34, TEAL_M, 0.6), FadeIn(t2l)], 0.7),
            "so S3 steps down",
            (lambda: [Transform(sv[3], srv(3, "follower", 2))], 0.8),
        ])

        h13 = msg(1, 3, BLUE_M)
        stB2 = status("pay-B: never committed", 0, RED_M)
        stB3 = status("its client retries", 1, GREY_B)
        self.steps("S1's log wins: pay-C replaces pay-B, which was never committed, so its client retries.", [
            (lambda: [FadeOut(h34), FadeOut(t1l), FadeOut(t2l), GrowArrow(h13)], 0.6),
            (lambda: [go(h13, BLUE_M, 0.6)], 0.6),
            "pay-C replaces",
            (lambda: [Transform(eB, entry(3, 1, "pay-C", GREEN_M)), FadeIn(stB2)], 0.8),
            "so its client",
            (lambda: [FadeIn(stB3, shift=0.1 * UP), go(ca, WHITE, 0.6)], 0.7),
        ])

        self.steps("One leader per term, and an entry counts once a majority stores it. That keeps all five logs the same.", [
            (lambda: [FadeOut(h13), glow(sv[1][0], BLUE_M)], 0.9),
            "an entry counts",
            (lambda: [*[glow(e[0], GREEN_M, 1.08) for e in list(eA.values()) + list(eC.values()) + [eB]]], 1.0),
            "That keeps",
            (lambda: [*[glow(sv[i][0], WHITE, 1.03) for i in sv]], 1.0),
        ])
        self.wait(0.6)

    def _to_cut(self, i):
        """A message from S3 that dies where it meets the cut."""
        ar = msg(3, i, BLUE_M)
        s, e = ar.get_start(), ar.get_end()
        f = (s[1] - CUT_Y + 0.06) / (s[1] - e[1])
        an, _ = lost(ar, BLUE_M, f)
        return an
