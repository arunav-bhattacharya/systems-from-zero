from sfz import *

SAY.insert(0, (r"\bRequestVote\b", "request vote"))
SAY.insert(0, (r"\betcd\b", "et C D"))
SAY.insert(0, (r"\bn([1-5])('s)?\b", lambda m: "N " + m.group(1) + (m.group(2) or "")))

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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))



C0 = np.array([0, -0.15, 0])
RAD = 2.3
ANG = [90, 18, -54, -126, 162]           # n1 top, then clockwise
BW, BH, TW = 1.9, 1.0, 1.6
ROLE_C = {"follower": WHITE, "candidate": YELLOW_M, "leader": GREEN_M}
RX, LX = 5.2, -5.2                       # side panels
BAR = np.array([RX, -1.2, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


class Node:
    def __init__(self, i):
        self.i = i
        self.c = C0 + RAD * np.array([np.cos(np.radians(ANG[i])), np.sin(np.radians(ANG[i])), 0])
        self.r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(self.c)
        self.n = T(f"n{i + 1}", 28).move_to(self.c + np.array([-BW / 2 + 0.35, 0.22, 0]))
        self.role = "follower"
        self.term = 0
        self.tm = self.term_t(0)
        self.ro = self.role_t("follower")
        y = self.c[1] - BH / 2 - 0.17
        self.track = Rectangle(width=TW, height=0.1, stroke_color=GREY_D, stroke_width=1.5).move_to([self.c[0], y, 0])
        self.bar = Rectangle(width=TW, height=0.1, stroke_width=0).set_fill(TEAL_M, 1).move_to([self.c[0], y, 0])

    def term_t(self, k, color=GREY_B):
        t = T(f"term {k}", 20, color)
        return t.move_to(self.c + np.array([BW / 2 - 0.15 - t.width / 2, 0.22, 0]))

    def role_t(self, s):
        return T(s, 22, ROLE_C[s]).move_to(self.c + np.array([0, -0.2, 0]))

    @property
    def g(self):
        return VGroup(self.r, self.n, self.tm, self.ro, self.track, self.bar)

    def set_term(self, k):
        self.term = k
        new = self.term_t(k, YELLOW_M)
        old, self.tm = self.tm, new
        return [swap(old, new)]

    def set_role(self, s):
        self.role = s
        new = self.role_t(s)
        old, self.ro = self.ro, new
        return [swap(old, new), self.r.animate.set_stroke(ROLE_C[s])]

    def timer(self, frac):
        w = max(0.02, TW * frac)
        return self.bar.animate.stretch_to_fit_width(w).align_to(self.track, LEFT)

    def edge(self, other):
        return ends(self.r, other.r)


class Raft(Base):
    """cons-04, section 1: choosing a leader. The club and its minutes book (chair = leader, period of office = term,
    book = log). The lab's election run: n4 times out at 186 ms, votes from n1 (187), n2 and n3 (190), wins term 1 at
    192, n5's vote at 194 changes nothing; heartbeats every 50 ms. A cut-off leader steps down on the first reply with
    a higher term. The split scenario (every timeout 150 ms, every message 5 ms): 20 refusals a round, 330 elections and
    term 66 after 10 s, no leader. Random timeouts (150 to 300 ms) and the paper's numbers (over 10 s, 287 ms, 513 ms).
    The guardrail (10 to 500 ms; etcd's 1,000 ms), where the club breaks, the moral and a check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, 3.3, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def bot(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, -3.3, 0])
        old, self.botm = self.botm, new
        return [swap(old, new)]

    def unbot(self):
        old, self.botm = self.botm, None
        return [FadeOut(old)] if old is not None else []

    def side(self, key, lines, x, color=WHITE, size=22, y0=1.6):
        g = VGroup(*[T(s, size, color) for s in lines]).arrange(DOWN, buff=0.22)
        fit(g, 2.8)
        g.move_to([x, y0 - g.height / 2, 0])
        old = self.lab.get(key)
        self.lab[key] = g
        return [swap(old, g)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line(BAR + LEFT * 1.1, BAR + RIGHT * 1.1, stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def msg(self, a, b, color, rt=0.6):
        pa, pb = a.edge(b)
        return dot_run(pa, pb, color, rt)

    def construct(self):
        self.capm = None
        self.botm = None
        self.lab = {}
        self.title_card("One chair per term", "how five servers choose a leader")
        N = [Node(i) for i in range(5)]
        n1, n2, n3, n4, n5 = N

        # ---------------- scene 1: the question ----------------
        self.steps("Picture a café at lunchtime. You tap your card, and the screen says Approved. Behind that word, five "
                   "computers saved your payment. One of them, the leader, takes each payment and copies it to the others.", [
            (lambda: self.cap("card tapped: Approved", WHITE), 0.5),
            "five",
            (lambda: [LaggedStart(*[FadeIn(VGroup(n.r, n.n)) for n in N], lag_ratio=0.15)], 1.0),
            "the leader",
            (lambda: [n4.r.animate.set_stroke(GREEN_M)], 0.5),
            "copies it",
            (lambda: [*[self.msg(n4, n, GREEN_M, 0.6) for n in N if n is not n4]], 0.8),
        ])
        cut = tick(False, 0.2).move_to(n4.r.get_corner(UL) + np.array([0.0, 0.0, 0]))
        self.steps("Now the leader's network cable comes loose. How do the other four even notice? And how do they make "
                   "sure exactly one of them takes over, not two? Hold that question.", [
            "comes loose",
            (lambda: [Create(cut), VGroup(n4.r, n4.n).animate.set_opacity(0.35)], 0.6),
            "How do the other",
            (lambda: self.cap("how do the others notice?", WHITE), 0.5),
            "exactly one",
            (lambda: self.cap("how do they make sure exactly one takes over?", YELLOW_M), 0.5),
        ], after=0.3)

        # ---------------- scene 2: the club ----------------
        self.steps("Think of a club with a minutes book. Each period of office has one chair, chosen by vote. "
                   "If the chair stops turning up, a member calls an election.", [
            (lambda: [FadeOut(cut), n4.r.animate.set_stroke(WHITE, opacity=1).set_fill(BLACK, 1), n4.n.animate.set_opacity(1),
                      *self.cap("a club with a minutes book", WHITE)], 0.6),
            "one chair",
            (lambda: self.side("map", ["one chair per period,", "chosen by vote"], LX, WHITE), 0.5),
            "calls an election",
            (lambda: self.side("map", ["one chair per period,", "chosen by vote", "chair missing: election"], LX, WHITE), 0.5),
        ])
        self.steps("Our five computers work the same way: the chair is the leader, the period of office is a term, "
                   "numbered 1, 2, 3, and the minutes book is the log of payments. Everyone else is a follower.", [
            "the chair is",
            (lambda: self.side("map", ["chair = leader"], LX, WHITE), 0.5),
            "a term",
            (lambda: self.side("map", ["chair = leader", "period = term 1, 2, 3"], LX, WHITE), 0.5),
            "the minutes book",
            (lambda: self.side("map", ["chair = leader", "period = term 1, 2, 3", "minutes book = log"], LX, WHITE), 0.5),
            "Everyone else",
            (lambda: self.side("map", ["chair = leader", "period = term 1, 2, 3", "minutes book = log", "members = followers"], LX, WHITE), 0.5),
        ], after=0.3)
        self.stamp("club")

        # ---------------- scene 3: the lab's first election ----------------
        fr = [0.82, 0.9, 0.95, 0.62, 0.88]
        self.steps("Watch it from the start, in the lab's run. Nobody is leader yet. Every server is a follower with a "
                   "timer. If the timer runs out before it hears from a leader, it calls an election.", [
            (lambda: [*self.cap("the lab's run: five servers start, no leader", WHITE),
                      *[FadeIn(VGroup(n.tm, n.ro)) for n in N]], 0.7),
            "with a",
            (lambda: [*[FadeIn(VGroup(n.track, n.bar)) for n in N]], 0.6),
            "If the timer",
            (lambda: [*[n.timer(f * 0.3) for n, f in zip(N, fr)]], 2.0),
        ])
        self.steps("n4's timer runs out first, at 186 milliseconds. It moves to term 1, becomes a candidate, votes for "
                   "itself, and asks the others for their votes.", [
            (lambda: [*[n.timer(0.0 if n is n4 else f * 0.12) for n, f in zip(N, fr)],
                      *self.side("clk", ["t = 186 ms"], RX, YELLOW_M, 26)], 0.6),
            "It moves",
            (lambda: [*n4.set_term(1), *n4.set_role("candidate")], 0.6),
            "votes for",
            (lambda: self.side("tally", ["votes for n4: 1"], RX, YELLOW_M, 24, 0.9), 0.4),
            "asks the others",
            (lambda: [*[self.msg(n4, n, YELLOW_M, 0.7) for n in N if n is not n4]], 0.8),
        ])
        self.steps("Each server gives at most one vote per term, to the first candidate that asks, and writes it to disk "
                   "before answering. n1 votes at 187, n2 and n3 at 190. Three of five is a majority, so at 192, n4 wins "
                   "term 1.", [
            (lambda: self.cap("one vote per server per term, written to disk first", WHITE), 0.6),
            "n1 votes",
            (lambda: [self.msg(n1, n4, GREEN_M, 0.5), *n1.set_term(1), *self.side("clk", ["t = 187 ms"], RX, YELLOW_M, 26),
                      *self.side("tally", ["votes for n4: 2"], RX, YELLOW_M, 24, 0.9)], 0.6),
            "n2 and n3",
            (lambda: [self.msg(n2, n4, GREEN_M, 0.5), self.msg(n3, n4, GREEN_M, 0.5), *n2.set_term(1), *n3.set_term(1),
                      *self.side("clk", ["t = 190 ms"], RX, YELLOW_M, 26), *self.side("tally", ["votes for n4: 3"], RX, YELLOW_M, 24, 0.9)], 0.6),
            "Three of five",
            (lambda: self.side("tally", ["votes for n4: 3", "3 of 5: a majority"], RX, GREEN_M, 24, 0.9), 0.5),
            "n4 wins",
            (lambda: [*n4.set_role("leader"), *self.side("clk", ["t = 192 ms"], RX, YELLOW_M, 26)], 0.6),
        ])
        self.steps("It sends a heartbeat at once, a small I'm still here message, and keeps sending one every 50 "
                   "milliseconds. Each one restarts every timer. n5's vote arrives at 194 and changes nothing. "
                   "The chair is already seated.", [
            (lambda: [*[self.msg(n4, n, GREEN_M, 0.5) for n in N if n is not n4]], 0.6),
            (lambda: [*[n.timer(f) for n, f in zip(N, fr) if n is not n4], n4.timer(1.0),
                      *self.cap("heartbeat: \"I'm still here\", every 50 ms", WHITE)], 0.5),
            "n5's vote",
            (lambda: [self.msg(n5, n4, GREY_B, 0.5), *n5.set_term(1), *self.side("clk", ["t = 194 ms"], RX, YELLOW_M, 26)], 0.6),
            "already seated",
            (lambda: [*[self.msg(n4, n, GREEN_M, 0.5) for n in N if n is not n4]], 0.6),
        ], after=0.3)
        self.stamp("elected")

        # ---------------- scene 4: a cut-off leader, and terms ----------------
        cut = tick(False, 0.2).move_to(n4.r.get_corner(UL))
        nf = [n for n in N if n is not n4]
        self.steps("Now n4's cable comes loose. The heartbeats stop, and the timers run down. Say n2's runs out first. "
                   "It moves to term 2, and n1, n3 and n5 vote for it. n2 leads term 2.", [
            (lambda: [*self.drop("clk", "tally"), Create(cut), *self.cap("n4's cable comes loose", RED_M)], 0.5),
            "the timers",
            (lambda: [*[n.timer(0.0 if n is n2 else 0.25) for n in nf]], 1.6),
            "It moves to term 2",
            (lambda: [*n2.set_term(2), *n2.set_role("candidate")], 0.5),
            (lambda: [*[self.msg(n2, n, YELLOW_M, 0.5) for n in (n1, n3, n5)]], 0.6),
            "vote for it",
            (lambda: [*[self.msg(n, n2, GREEN_M, 0.5) for n in (n1, n3, n5)], *n1.set_term(2), *n3.set_term(2), *n5.set_term(2)], 0.6),
            "n2 leads",
            (lambda: [*n2.set_role("leader"), *[n.timer(1.0) for n in nf], *self.cap("n2 leads term 2", GREEN_M)], 0.6),
        ])
        self.steps("Then the cable goes back in. n4 still thinks it leads term 1, and sends a heartbeat. But every message "
                   "carries the sender's term, and the reply says term 2.", [
            (lambda: [FadeOut(cut), *self.cap("n4 is back, still sure it leads term 1", WHITE)], 0.5),
            "sends a heartbeat",
            (lambda: [self.msg(n4, n3, GREEN_M, 0.7)], 0.7),
            "the reply says",
            (lambda: [self.msg(n3, n4, YELLOW_M, 0.7), *self.bot("reply: term 2", YELLOW_M)], 0.7),
        ])
        self.steps("A server that sees a higher term takes that number and becomes a follower, and a message with a lower "
                   "term is refused. So n4 steps down at the first reply, and nobody acts on its old messages.", [
            (lambda: self.cap("see a higher term: take it, become a follower", WHITE), 0.5),
            "a lower",
            (lambda: self.bot("a message with a lower term: refused", RED_M), 0.5),
            "steps down",
            (lambda: [*n4.set_term(2), *n4.set_role("follower"), n4.timer(1.0)], 0.6),
        ], after=0.3)

        # ---------------- scene 5: the name ----------------
        self.steps("This method is Raft. The roles are follower, candidate and leader, the vote request is called "
                   "RequestVote, and the timer is the election timeout. Two leaders in one term would need two majorities "
                   "with no server in common, and five servers can't form those.", [
            (lambda: [*self.unbot(), *self.drop("map"), *self.cap("Raft: follower, candidate, leader", TEAL_M)], 0.6),
            "RequestVote",
            (lambda: self.side("names", ["vote request:", "RequestVote", "timer:", "election timeout"], LX, TEAL_M, 22), 0.6),
            "Two leaders",
            (lambda: self.bot("two leaders in one term would need two majorities with no server in common", WHITE), 0.6),
        ], after=0.3)
        self.stamp("named")

        # ---------------- scene 6: break it: no randomness ----------------
        self.steps("So does the timer matter much? Restart all five, but make every timeout exactly 150 milliseconds, and "
                   "every message take exactly 5. Who wins? Pause and guess.", [
            (lambda: [*self.unbot(), *self.drop("names"), *self.cap("every timeout 150 ms, every message 5 ms: who wins?", PURPLE_M),
                      *[a for n in N for a in n.set_role("follower")], *[a for n in N for a in n.set_term(0)],
                      *[n.timer(1.0) for n in N]], 0.7),
            "Pause and guess",
            (lambda: self.bot("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        pairs = [(a, b) for a in N for b in N if a is not b]
        self.steps("Nobody. All five time out in the same millisecond. Each votes for itself and refuses the other four, "
                   "because it already voted in that term. Twenty refusals.", [
            (lambda: [*self.unbot(), *[n.timer(0.0) for n in N]], 0.8),
            "All five",
            (lambda: [*[a for n in N for a in n.set_role("candidate")], *[a for n in N for a in n.set_term(1)]], 0.6),
            "refuses",
            (lambda: [*[self.msg(a, b, RED_M, 0.6) for a, b in pairs]], 0.8),
            "Twenty refusals",
            (lambda: self.side("clk", ["20 refusals", "no winner"], RX, RED_M, 24), 0.5),
        ])
        self.steps("150 milliseconds later, the same thing again, one term higher. After 10 seconds: 330 elections, term 66, "
                   "and still no leader.", [
            (lambda: [*[n.timer(1.0) for n in N]], 0.3),
            (lambda: [*[n.timer(0.0) for n in N]], 0.9),
            (lambda: [*[a for n in N for a in n.set_term(2)], *[self.msg(a, b, RED_M, 0.5) for a, b in pairs]], 0.7),
            "After 10 seconds",
            (lambda: [*self.side("clk", ["after 10,000 ms:", "330 elections", "highest term 66", "leader: none"], RX, RED_M, 24),
                      *[n.set_term(66)[0] for n in N]], 0.7),
        ])
        self.steps("A club where everyone nominates themselves at the same second, forever. The rules are fine. "
                   "The tie is the problem.", [
            "The tie",
            (lambda: self.cap("the rules are fine; the tie is the problem", WHITE), 0.5),
        ], after=0.3)
        self.stamp("split")

        # ---------------- scene 7: random timers ----------------
        rnd = [0.55, 0.8, 0.95, 0.3, 0.7]
        self.steps("The fix is almost silly: draw each timeout at random, from 150 to 300 milliseconds in Raft's paper. "
                   "One server usually wakes well before the others, and collects its votes first.", [
            (lambda: [*self.drop("clk"), *self.cap("each timeout drawn at random: 150 to 300 ms", GREEN_M),
                      *[a for n in N for a in n.set_role("follower")], *[n.set_term(0)[0] for n in N],
                      *[n.timer(f) for n, f in zip(N, rnd)]], 0.8),
            "One server",
            (lambda: [*[n.timer(f - 0.3) for n, f in zip(N, rnd)]], 1.4),
            "collects its votes",
            (lambda: [*n4.set_role("candidate"), *n4.set_term(1), *[self.msg(n, n4, GREEN_M, 0.5) for n in (n1, n2)]], 0.7),
            (lambda: [*n4.set_role("leader"), *[n.timer(1.0) for n in N], *n1.set_term(1), *n2.set_term(1),
                      *n3.set_term(1), *n5.set_term(1)], 0.5),
        ])
        self.steps("The paper measured it on five servers. With no randomness, split votes left them leaderless for more "
                   "than 10 seconds. With just 5 milliseconds of randomness, the median wait fell to 287 milliseconds. "
                   "With 50, the worst of 1,000 trials took 513.", [
            "With no randomness",
            (lambda: self.side("clk", ["no randomness:", "over 10 s, no leader"], RX, RED_M, 22), 0.5),
            "With just 5",
            (lambda: self.side("clk", ["no randomness:", "over 10 s, no leader", "5 ms random:", "median 287 ms"], RX, WHITE, 22), 0.5),
            "With 50",
            (lambda: self.side("clk", ["no randomness:", "over 10 s, no leader", "5 ms random:", "median 287 ms",
                                       "50 ms random:", "worst of 1,000: 513 ms"], RX, WHITE, 22), 0.5),
        ], after=0.3)
        self.stamp("random")

        # ---------------- scene 8: the guardrail ----------------
        self.steps("So why not make the timeout tiny? One round of messages, disk writes included, takes 0.5 to 20 "
                   "milliseconds. The timeout must be many of those, or followers unseat a healthy leader that was merely "
                   "slow.", [
            (lambda: [*self.drop("clk"), *self.cap("why not a tiny timeout?", WHITE)], 0.5),
            "One round",
            (lambda: self.side("g", ["one round of messages:", "0.5 to 20 ms"], RX, WHITE, 22), 0.5),
            "or followers",
            (lambda: [*self.bot("too short: a slow but healthy leader gets replaced", RED_M),
                      Indicate(n4.r, color=RED_M, scale_factor=1.05)], 0.6),
        ])
        self.steps("So it sits between 10 and 500 milliseconds. etcd, a small database built on Raft, waits 1,000 "
                   "milliseconds before calling an election.", [
            (lambda: self.side("g", ["one round of messages:", "0.5 to 20 ms", "election timeout:", "10 to 500 ms"], RX, WHITE, 22), 0.5),
            "etcd",
            (lambda: self.bot("etcd: 100 ms heartbeat, 1,000 ms election timeout", WHITE), 0.5),
        ])
        self.steps("And here the club picture breaks. Members in a room can see who's there. A server can't tell a dead "
                   "leader from a slow network, so every rule runs on timers and term numbers.", [
            (lambda: [*self.drop("g"), *self.cap("where the club breaks: a server can't see who's in the room", WHITE)], 0.6),
            "every rule",
            (lambda: self.bot("dead or just slow? only timers and term numbers can tell", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral: one leader per numbered term, won by a majority, one vote per server per term. "
                   "Random timers break ties, and the higher term always wins.", [
            (lambda: [*self.unbot(), *self.cap("one leader per term, won by a majority; one vote per server per term", YELLOW_M)], 0.6),
            "Random timers",
            (lambda: self.bot("random timers break ties; the higher term wins", YELLOW_M), 0.6),
        ], after=0.3)
        self.steps("One quick check. Could two servers both win term 1? Pause and think.", [
            (lambda: [*self.unbot(), *self.cap("could two servers both win term 1?  pause and think", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. Each winner needs three votes, so two winners need six. Five servers have only five votes in "
                   "term 1.", [
            (lambda: self.side("g", ["two winners:", "3 + 3 = 6 votes", "five servers:", "5 votes per term"], RX, WHITE, 22), 0.6),
            "only five",
            (lambda: [LaggedStart(*[Indicate(n.r, color=YELLOW_M, scale_factor=1.05) for n in N], lag_ratio=0.15)], 1.0),
        ], after=0.3)
        self.play(*self.cap("one chair per term", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
