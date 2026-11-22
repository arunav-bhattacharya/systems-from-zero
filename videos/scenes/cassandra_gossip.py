from sfz import *

SAY.insert(0, (r"\bcass(\d)\b", r"cass \1"))
SAY.insert(0, (r"\blog2\b", "log two"))
SAY.insert(0, (r"\bAck2\b", "ack two"))
SAY.insert(0, (r"\bSyn\b", "sin"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
OC = np.array([0, 0.55, 0])
RX, RY = 2.85, 2.0
ANG = [150, 90, 30, -30, -90, -150]          # cass1 .. cass6, clockwise from top left
BW, BH = 1.7, 1.0
PX = 5.05                                    # right panel centre x
LX = -5.1                                   # left panel centre x
COST_Y, BAR_Y, CAP_Y = -2.45, -2.85, -3.27


def pos(i):
    a = np.radians(ANG[i])
    return OC + np.array([RX * np.cos(a), RY * np.sin(a), 0])


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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
        return self.put("cap", fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0]))

    def cost(self, s, color=RED_M, size=24):
        return self.put("cost", fit(T(s, size, color), 12.8).move_to([0, COST_Y, 0]))

    def panel(self, key, s, y, color=WHITE, size=22, x=PX):
        return self.put(key, fit(T(s, size, color), 3.0).move_to([x, y, 0]))

    def put(self, key, mob, d=UP):
        old = self.slots.get(key)
        self.slots[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.slots.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(w, h, color, at, a=0.14):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(
        fillc(color, a), 1).move_to(at)


def seg(i, j):
    """The straight line between two boxes' edges."""
    a, b = pos(i), pos(j)
    d = (b - a) / np.linalg.norm(b - a)

    def edge(c, d):
        t = min(BW / 2 / abs(d[0]) if abs(d[0]) > 1e-6 else 1e9, BH / 2 / abs(d[1]) if abs(d[1]) > 1e-6 else 1e9)
        return c + (t + 0.06) * d
    return edge(a, d), edge(b, -d)


def call(i, j, color=YELLOW_M, back=GREEN_M, rt=1.0, both=True):
    """A phone line between two nodes, with a dot each way."""
    a, b = seg(i, j)
    ln = Line(a, b, stroke_width=2.5, color=GREY_B).set_z_index(1)
    d1 = Dot(radius=0.07, color=color).move_to(a).set_z_index(4)
    d2 = Dot(radius=0.07, color=back).move_to(b).set_z_index(4)
    seq = [Create(ln, run_time=0.2), MoveAlongPath(d1, Line(a, b), run_time=rt * 0.45)]
    if both:
        seq.append(MoveAlongPath(d2, Line(b, a), run_time=rt * 0.45))
    seq += [FadeOut(VGroup(ln, d1, d2), run_time=0.15)]
    return Succession(*seq)


class CassandraGossip(Base):
    """shard-05, section 2. Six nodes, no boss: the office clerks who ring one colleague at random. Two jobs: hear each
    change, keep hearing heartbeats. Telling everyone costs N x (N-1) (30, 870, about a million) and loses news for a
    restarting node. One random peer a second: cass6's LEAVING at version 412 reaches cass2, then cass1 and cass3, then
    everyone (pulled by cass5) in 3 rounds; about log2 N rounds, 3 x N messages a round. Digests and versions (Syn, Ack,
    Ack2), the generation for restarts, seeds for strangers, the moral, and a check (1,000 nodes: about 10 rounds)."""

    def construct(self):
        self.slots = {}
        self.title_card("Nobody in charge", "how a Cassandra cluster spreads news by gossip")

        # ---------------- scene 1: the office with no manager ----------------
        boxes = [rbox(BW, BH, BLUE_M, pos(i)) for i in range(6)]
        names = [T("clerk", 22).move_to(pos(i) + 0.2 * UP) for i in range(6)]
        lines = [M("list", 16, GREY_B).move_to(pos(i) + 0.22 * DOWN) for i in range(6)]
        self.steps("Cassandra is a database program that spreads its data over many equal computers. No computer is in charge.", [
            (lambda: [LaggedStart(*[FadeIn(VGroup(b, n)) for b, n in zip(boxes, names)], lag_ratio=0.12)], 1.4),
            "No computer",
            (lambda: self.cap("no computer is in charge", YELLOW_M, 28), 0.5),
        ])
        crown = VGroup(Polygon([-0.5, 0, 0], [0.5, 0, 0], [0.6, 0.55, 0], [0.25, 0.2, 0], [0, 0.6, 0], [-0.25, 0.2, 0], [-0.6, 0.55, 0],
                               stroke_color=GOLD_M, stroke_width=4).set_fill(fillc(GOLD_M, 0.4), 1)).move_to(OC)
        no = tick(False, 0.45).move_to(OC)
        self.steps("That sounds odd, because most offices and most programs have a boss somewhere. "
                   "A boss is simple, right up to the day the boss is the one that fails.", [
            "have a boss",
            (lambda: [FadeIn(crown, scale=0.6)], 0.6),
            "right up to",
            (lambda: [Create(no)], 0.5),
            (lambda: [FadeOut(VGroup(crown, no))], 0.5),
        ])
        self.steps("So how does every machine hear that something changed? Picture an office with six clerks and no manager. "
                   "Each clerk keeps a copy of the staff list.", [
            (lambda: self.cap("how does every machine hear that something changed?", WHITE), 0.5),
            "Each clerk keeps",
            (lambda: [LaggedStart(*[FadeIn(l) for l in lines], lag_ratio=0.1), *self.cap("six clerks, no manager, a staff list each", WHITE)], 0.9),
        ])
        rng = np.random.default_rng(11)
        rand_pairs = [(0, 3), (2, 5), (1, 4), (4, 0), (3, 1), (5, 2)]

        def news(idxs, color=GREEN_M):
            return [*[boxes[i].animate.set_stroke(color) for i in idxs], *[l.animate.set_color(color) for l in [lines[i] for i in idxs]]]

        self.steps("A new clerk arrives in the morning, and by lunch every list has her name on it. Nobody sent an email.", [
            "A new clerk",
            (lambda: news([1]), 0.5),
            (lambda: [call(1, 4), *news([4])], 1.0),
            (lambda: [call(1, 2), call(4, 5), *news([2, 5])], 1.0),
            (lambda: [call(2, 3), call(5, 0), *news([3, 0])], 1.0),
            "Nobody sent",
            (lambda: self.cap("nobody sent an email", WHITE), 0.5),
        ])
        self.steps("Every few minutes, each clerk rang one colleague at random, and the two compared lists.", [
            (lambda: [*[call(a, b, YELLOW_M, YELLOW_M) for a, b in rand_pairs[:3]]], 1.2),
            (lambda: [*[call(a, b, YELLOW_M, YELLOW_M) for a, b in rand_pairs[3:]]], 1.2),
            (lambda: self.cap("each clerk rings one colleague at random, and they compare lists", WHITE), 0.5),
        ], after=0.5)

        # ---------------- scene 2: the map and the heartbeat ----------------
        nn = [T(f"cass{i + 1}", 22).move_to(pos(i) + 0.2 * UP) for i in range(6)]
        vl = [M("cass6: v410", 16, GREY_B).move_to(pos(i) + 0.22 * DOWN) for i in range(6)]
        self.steps("Map it. Each clerk is a node, one machine.", [
            (lambda: [*[Transform(names[i], nn[i]) for i in range(6)], *[b.animate.set_stroke(BLUE_M) for b in boxes],
                      *self.cap("clerk  =  node, one machine", WHITE, 26)], 0.8),
        ])
        self.steps("The staff list is the node's map of the cluster: who's in it, and what each one says about itself.", [
            (lambda: [*[Transform(lines[i], vl[i]) for i in range(6)], *self.cap("staff list  =  the node's map of the cluster", WHITE, 26)], 0.8),
        ])
        self.steps("Every node has two jobs. Hear each change, like a node that's leaving. And keep hearing that every other node is alive.", [
            "Hear each change",
            (lambda: self.cap("job 1: hear each change", WHITE, 26), 0.5),
            "And keep hearing",
            (lambda: self.cap("job 2: keep hearing that every other node is alive", WHITE, 26), 0.5),
        ])
        hb = M("heartbeat 409", 16, RED_M).next_to(boxes[5], LEFT, buff=0.15)
        self.steps("For that, each node raises a counter once a second, its heartbeat, that just says still here.", [
            "raises a counter",
            (lambda: [FadeIn(hb)], 0.3),
            (lambda: [Transform(hb, M("heartbeat 410", 16, RED_M).move_to(hb))], 0.5),
            0.4,
            (lambda: [Transform(hb, M("heartbeat 411", 16, RED_M).move_to(hb)), *self.cap("heartbeat: a counter raised once a second: still here", WHITE, 26)], 0.5),
        ], after=0.4)

        # ---------------- scene 3: tell everyone ----------------
        pairs = [(i, j) for i in range(6) for j in range(i + 1, 6)]
        self.steps("The obvious way: whoever changes tells everyone, and every node sends its heartbeat to every other node, once a second.", [
            (lambda: [FadeOut(hb), *self.cap("the obvious way: everyone tells everyone", WHITE, 26)], 0.5),
            "every node sends",
            (lambda: [*[call(i, j, YELLOW_M, YELLOW_M, 1.2) for i, j in pairs]], 1.6),
        ])
        self.steps("For six nodes, that's 6 times 5, 30 messages a second. Fine. For 30 nodes, 870. For a thousand, about a million, every second.", [
            (lambda: [*self.panel("p1", "6 nodes: 6 × 5 = 30", 2.6, WHITE), *[call(i, j, YELLOW_M, YELLOW_M, 1.0) for i, j in pairs]], 1.3),
            "For 30",
            (lambda: self.panel("p2", "30 nodes: 870", 1.9, GOLD_M), 0.5),
            "For a thousand",
            (lambda: self.panel("p3", "1,000 nodes: a million", 1.2, RED_M), 0.5),
        ])
        self.steps("The machines would spend more time on the phone than at their desks.", [
            (lambda: [*[call(i, j, YELLOW_M, YELLOW_M, 0.8) for i, j in pairs]], 1.0),
            (lambda: [*[call(i, j, YELLOW_M, YELLOW_M, 0.8) for i, j in pairs]], 1.0),
        ], after=0.4)
        miss = T("missed it", 20, RED_M).next_to(boxes[3], DOWN, buff=0.12)
        self.steps("And there's a quieter problem. A node that was restarting when the news went out never hears it again. Nobody calls back.", [
            (lambda: [*self.drop("p1", "p2", "p3"), boxes[3].animate.set_stroke(GREY_D).set_opacity(0.3),
                      VGroup(names[3], lines[3]).animate.set_opacity(0.3), *self.cap("cass4 is restarting", GREY_B)], 0.7),
            "never hears",
            (lambda: [*[call(5, j, GREEN_M, GREEN_M, 0.9, both=False) for j in (0, 1, 2, 4)],
                      *[Transform(lines[i], M("cass6: v412", 16, GREEN_M).move_to(lines[i])) for i in (0, 1, 2, 4, 5)]], 1.0),
            (lambda: [boxes[3].animate.set_stroke(BLUE_M).set_opacity(1), VGroup(names[3], lines[3]).animate.set_opacity(1)], 0.6),
            "Nobody calls",
            (lambda: [FadeIn(miss), Indicate(lines[3], color=RED_M), *self.cap("telling everyone: too many messages, and lost news", RED_M)], 0.8),
        ], after=0.5)

        # ---------------- scene 4: one random call a second ----------------
        know = [False] * 6

        def mark(i):
            know[i] = True
            return [boxes[i].animate.set_stroke(GREEN_M), Transform(lines[i], M("cass6: v412", 16, GREEN_M).move_to(lines[i]))]

        def reset():
            return [*[b.animate.set_stroke(BLUE_M) for b in boxes],
                    *[Transform(lines[i], M("cass6: v410", 16, GREY_B).move_to(lines[i])) for i in range(6)], FadeOut(miss)]

        self.steps("So do what the clerks did. Once a second, each node tells one random peer what it knows, "
                   "and that peer passes it on in its own rounds.", [
            (lambda: [*reset(), *self.cap("once a second: tell one random peer", YELLOW_M, 28)], 0.8),
            "and that peer",
            (lambda: [call(0, 3, YELLOW_M, YELLOW_M), call(2, 4, YELLOW_M, YELLOW_M)], 1.0),
        ])
        qm = T("?", 54, YELLOW_M).move_to(OC)
        self.steps("cass6 has news: it's leaving, version 412. How many rounds until all six know? Pause and guess.", [
            (lambda: [*mark(5), *self.panel("rnd", "round 0", 2.6, WHITE), *self.panel("kn", "knows the news: 1 of 6", 1.9, GREEN_M)], 0.7),
            "How many",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Round one. cass6 rings cass2. Now two know.", [
            (lambda: [FadeOut(qm), *self.drop("cap"), *self.panel("rnd", "round 1", 2.6, WHITE)], 0.4),
            "cass6 rings",
            (lambda: [call(5, 1)], 1.1),
            (lambda: [*mark(1), *self.panel("kn", "knows the news: 2 of 6", 1.9, GREEN_M)], 0.5),
        ])
        self.steps("Round two. Both of them ring someone: cass6 picks cass1, cass2 picks cass3. Four know. It doubled.", [
            (lambda: self.panel("rnd", "round 2", 2.6, WHITE), 0.4),
            "cass6 picks",
            (lambda: [call(5, 0), call(1, 2)], 1.1),
            (lambda: [*mark(0), *mark(2), *self.panel("kn", "knows the news: 4 of 6", 1.9, GREEN_M)], 0.5),
            "It doubled",
            (lambda: [Indicate(self.slots["kn"], color=GREEN_M)], 0.7),
        ])
        self.steps("Round three. This time cass5, who hasn't heard, rings cass1, and gets the news in the answer. "
                   "News flows both ways, pushed and pulled. All six know, after three rounds.", [
            (lambda: self.panel("rnd", "round 3", 2.6, WHITE), 0.4),
            "rings cass1",
            (lambda: [call(4, 0, GREY_B, GREEN_M), call(2, 3)], 1.2),
            (lambda: [*mark(4), *mark(3)], 0.5),
            "pushed and pulled",
            (lambda: self.cap("pushed and pulled: news flows both ways", WHITE), 0.5),
            "All six",
            (lambda: [*self.panel("kn", "knows the news: 6 of 6", 1.9, GREEN_M), *[glow(b, GREEN_M, 1.04) for b in boxes]], 0.8),
        ])
        self.steps("The number that knows roughly doubles every round, so it reaches N nodes in about log2 of N rounds: "
                   "the number of doublings to get there. About ten for a thousand nodes. The lesson's demo counts 8 rounds for 6,000.", [
            (lambda: [*self.drop("cap"), *self.panel("p1", "1 → 2 → 4 → 8 → …", 1.2, WHITE)], 0.6),
            "log2 of N",
            (lambda: self.cost("about log2 N rounds: the number of doublings to reach N", YELLOW_M), 0.6),
            "About ten",
            (lambda: self.panel("p2", "1,000 nodes: about 10", 0.5, WHITE, 20), 0.5),
            "The lesson's demo",
            (lambda: self.panel("p3", "6,000 nodes: 8 (demo)", -0.2, WHITE, 20), 0.5),
        ])
        self.steps("And a round costs about three small messages per node, not a million. A node that missed the news just hears it at its next call.", [
            (lambda: self.cost("a round: about 3 small messages per node, not N × N", GREEN_M), 0.6),
            "A node that missed",
            (lambda: [glow(boxes[3], GREEN_M, 1.05), call(3, 1, GREY_B, GREEN_M)], 1.1),
        ], after=0.5)

        # ---------------- scene 5: compare the dates first ----------------
        self.steps("One more saving. Sending your whole map every second is a waste when almost nothing changed.", [
            (lambda: [*self.drop("p1", "p2", "p3", "rnd", "kn", "cost"), *reset(), *self.cap("sending the whole map every second: a waste", WHITE)], 0.8),
        ])
        hb6 = M("heartbeat 411, LEAVING 412", 16, GOLD_M).next_to(boxes[5], LEFT, buff=0.15)
        self.steps("So each node numbers every change to its own state: its heartbeat took 411, leaving took 412. That number is the version.", [
            "its heartbeat",
            (lambda: [FadeIn(hb6), *mark(5)], 0.6),
            "That number",
            (lambda: self.cap("version: the number a node gives each change to its own state", WHITE), 0.5),
        ])

        def card(s, color):
            t = M(s, 16, color)
            r = RoundedRectangle(corner_radius=0.08, width=2.9, height=0.62, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.18), 1)
            return VGroup(r, fit(t, 2.7).move_to(r))

        syn = card("Syn: cass6 at v412", YELLOW_M).move_to([LX, 2.4, 0])
        ack = card("Ack: I have v410, send newer", TEAL_M).move_to([LX, 1.6, 0])
        ack2 = card("Ack2: heartbeat 411, LEAVING 412", GREEN_M).move_to([LX, 0.8, 0])
        self.steps("Two nodes first swap short summaries, called digests: for each node, just its highest version.", [
            "swap short",
            (lambda: [call(5, 1, YELLOW_M, GREY_B, 1.0, both=False), FadeIn(syn, shift=0.1 * RIGHT)], 1.0),
            "called digests",
            (lambda: self.cap("digest: for each node, just its highest version", WHITE), 0.5),
        ])
        self.steps("cass2's copy says 410, so it answers: send me what's newer than 410. And only those two states travel.", [
            (lambda: [Indicate(lines[1], color=TEAL_M, scale_factor=1.2)], 0.7),
            "so it answers",
            (lambda: [call(1, 5, TEAL_M, GREY_B, 1.0, both=False), FadeIn(ack, shift=0.1 * RIGHT)], 1.0),
            "And only",
            (lambda: [call(5, 1, GREEN_M, GREY_B, 1.0, both=False), FadeIn(ack2, shift=0.1 * RIGHT)], 1.0),
            (lambda: mark(1), 0.5),
        ])
        self.steps("Three messages: Syn, Ack, Ack2. That's gossip.", [
            (lambda: [LaggedStart(*[glow(c[0], c[0].get_stroke_color(), 1.05) for c in (syn, ack, ack2)], lag_ratio=0.3)], 1.2),
            "That's gossip",
            (lambda: self.cap("gossip: once a second, compare notes with one random peer", YELLOW_M, 28), 0.6),
        ], after=0.5)

        # ---------------- scene 6: restarts and strangers ----------------
        self.steps("Two details keep it honest. A restarted node starts counting from zero again, "
                   "so its versions look older than what the cluster remembers.", [
            (lambda: [FadeOut(VGroup(syn, ack, ack2, hb6)), *self.drop("cap")], 0.5),
            "A restarted",
            (lambda: [boxes[2].animate.set_stroke(GREY_D).set_opacity(0.3), VGroup(names[2], lines[2]).animate.set_opacity(0.3)], 0.6),
            (lambda: [boxes[2].animate.set_stroke(BLUE_M).set_opacity(1), VGroup(names[2], lines[2]).animate.set_opacity(1)], 0.6),
            "look older",
            (lambda: self.cap("restarted: its counter starts again from zero", WHITE), 0.5),
        ])
        gen = M("new generation, heartbeat 32", 16, GOLD_M).next_to(boxes[2], DOWN, buff=0.12)
        self.steps("So each node also carries a generation, its start time, and a higher generation wins first. "
                   "In the lab, cass3 came back with a bigger generation and heartbeat 32, and everyone took the new state.", [
            "a generation",
            (lambda: self.cap("generation: the node's start time; a higher generation wins first", WHITE), 0.6),
            "In the lab",
            (lambda: [FadeIn(gen)], 0.5),
            "and everyone took",
            (lambda: [*[call(2, j, GOLD_M, GREY_B, 0.9, both=False) for j in (0, 1, 3, 4, 5)]], 1.1),
        ])
        newb = VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=GREY_B, stroke_width=3), num_dashes=36),
                      T("new node", 20, GREY_B)).move_to([LX, 2.45, 0])
        newb[1].move_to(newb[0])
        seed = T("seed", 20, GOLD_M).next_to(boxes[0], UP, buff=0.1)
        self.steps("And a brand-new node knows nobody. So its settings list a few seeds, nodes to ask for the map.", [
            (lambda: [FadeOut(gen), FadeIn(newb, shift=0.2 * RIGHT)], 0.6),
            "a few seeds",
            (lambda: [FadeIn(seed), glow(boxes[0], GOLD_M, 1.04), *self.cap("seeds: a few nodes a newcomer asks for the map", WHITE)], 0.7),
            "to ask for",
            (lambda: [Succession(Create(ln := Line(newb.get_right() + 0.08 * RIGHT, boxes[0].get_left() + 0.08 * LEFT, stroke_width=2.5, color=GREY_B)),
                                 FadeOut(ln))], 1.0),
        ])
        self.steps("One rule: never list a new node as its own seed, or it skips copying its data and answers reads with empty rows.", [
            (lambda: self.cap("a new node must never list itself as a seed: it would skip copying its data", RED_M), 0.6),
            "empty rows",
            (lambda: [glow(newb[0], RED_M, 1.05)], 0.8),
        ], after=0.5)

        # ---------------- scene 7: moral, loop, check ----------------
        self.steps("So nobody is in charge, and nobody needs to be. Each node rings one random peer a second, "
                   "the news doubles, and only what's new travels.", [
            (lambda: [FadeOut(VGroup(newb, seed)), *reset(), *self.drop("cap")], 0.6),
            (lambda: mark(5), 0.4),
            "Each node rings",
            (lambda: [call(5, 1)], 1.0),
            (lambda: [*mark(1), call(5, 0), call(1, 2)], 1.0),
            (lambda: [*mark(0), *mark(2), call(4, 0, GREY_B, GREEN_M), call(2, 3)], 1.0),
            (lambda: [*mark(4), *mark(3), *self.cap("one random call a second; the news doubles; only what's new travels", YELLOW_M, 26)], 0.6),
        ])
        self.steps("But gossip only carries what each node says about itself. A dead node says nothing at all. How the others read that silence is next.", [
            "A dead node",
            (lambda: [boxes[3].animate.set_stroke(GREY_D).set_opacity(0.3), VGroup(names[3], lines[3]).animate.set_opacity(0.3),
                      *self.cap("a dead node says nothing: how the others read silence is next", GREY_B)], 0.8),
        ], after=0.5)
        self.steps("One quick check. A cluster of 1,000 nodes, and one of them changes. Roughly how many rounds until everyone knows? Pause and think.", [
            (lambda: [boxes[3].animate.set_stroke(GREEN_M).set_opacity(1), VGroup(names[3], lines[3]).animate.set_opacity(1),
                      *self.cap("1,000 nodes, one change: about how many rounds until everyone knows?", WHITE)], 0.7),
            "Pause and think",
            (lambda: self.cost("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("About ten. A thousand is about two, doubled ten times.", [
            (lambda: [*self.drop("cost"), *self.cap("about 10 rounds: 2 doubled 10 times is 1,024", GREEN_M, 28)], 0.7),
        ], after=0.3)
        self.wait(2.0)
