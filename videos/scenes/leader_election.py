from sfz import *

SAY.insert(0, (r"\betcd('s)?\b", lambda m: "et C D" + (m.group(1) or "")))
# a lone "A" reads as "uh"; "eh" lands on the letter
SAY.insert(0, (r"\bjob A\b", "job eh"))
SAY.insert(0, (r"\bA's\b", "eh's"))

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



EC = np.array([-4.7, 0.3, 0])            # etcd, the ticket machine
EW, EH = 3.6, 3.2
JX, JY = 0.0, {"A": 1.6, "B": 0.0, "C": -1.6}
JW, JH = 2.4, 0.95
LC = np.array([4.7, 0.3, 0])             # the payout ledger
LW, LH = 3.6, 3.2
KY = {"A": 0.8, "B": 0.15, "C": -0.5, "A2": -1.15}
REV = {"A": 7, "B": 9, "C": 11}
LEASE_X0, LEASE_W = -4.35, 1.6
BAR = np.array([0, -2.6, 0])


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def token_run(a, b, s, color, rt=0.8):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    c = chip(s, color, 22).move_to(a).set_z_index(6)
    return Succession(FadeIn(c, run_time=0.1), MoveAlongPath(c, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(c, run_time=0.15))


class Job:
    def __init__(self, k):
        self.k = k
        self.c = np.array([JX, JY[k], 0])
        self.r = RoundedRectangle(corner_radius=0.12, width=JW, height=JH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(self.c)
        self.n = T(f"job {k}", 26).move_to(self.c + UP * 0.2)
        self.st = self.state_t("waiting", GREY_B)

    def state_t(self, s, color):
        return T(s, 20, color).move_to(self.c + DOWN * 0.22)

    @property
    def g(self):
        return VGroup(self.r, self.n, self.st)

    def state(self, s, color, stroke=None):
        new = self.state_t(s, color)
        old, self.st = self.st, new
        return [swap(old, new), self.r.animate.set_stroke(stroke or color)]

    def right(self):
        return self.c + RIGHT * (JW / 2 + 0.08)

    def left(self):
        return self.c + LEFT * (JW / 2 + 0.08)


class LeaderElection(Base):
    """cons-05, section 3: the stepper. Jobs A, B and C campaign under settlement/ with keys at revisions 7, 9 and 11 on
    10-second leases; the lowest leads; B watches A, C watches B. A pays batch 17 (token 7, accepted). A freezes for
    15 s; its lease runs out; etcd deletes its key (revision 12); B leads with token 9 and pays batch 18. A wakes and
    writes with token 7: refused, 7 < 9. A rejoins at revision 13. Jepsen's 2020 etcd lock results; the check must sit
    in the same atomic step as the write; the Try-it's 56-second wait after a crash."""

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

    def put(self, key, mob):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob)]

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

    def key_row(self, k, rev, who, color=WHITE):
        y = EC[1] + KY[k]
        t = T(f"rev {rev}", 22, color)
        t.move_to([EC[0] - EW / 2 + 0.55 + t.width / 2, y, 0])
        w = T(f"job {who}", 22, color)
        w.move_to([EC[0] - EW / 2 + 1.5 + w.width / 2, y, 0])
        return VGroup(t, w)

    def lease(self, k, frac=1.0):
        y = EC[1] + KY[k]
        tr = Rectangle(width=0.8, height=0.12, stroke_color=GREY_D, stroke_width=1.5)
        tr.move_to([EC[0] + EW / 2 - 0.2 - tr.width / 2, y, 0])
        b = Rectangle(width=tr.width * frac, height=0.12, stroke_width=0).set_fill(TEAL_M, 1).align_to(tr, LEFT).set_y(y)
        return tr, b

    def drain(self, k, frac):
        tr, b = self.leases[k]
        return b.animate.stretch_to_fit_width(max(0.02, tr.width * frac)).align_to(tr, LEFT)

    def ledger_highest(self, n, color=WHITE):
        t = T(f"highest token: {n}", 22, color).move_to(LC + UP * 0.85)
        return self.put("hi", t)

    def ledger_row(self, i, s, color):
        t = fit(T(s, 20, color), LW - 0.4).move_to(LC + UP * (0.25 - 0.5 * i))
        return self.put(f"row{i}", t)

    def construct(self):
        self.capm = None
        self.botm = None
        self.lab = {}
        self.title_card("The counter that says no", "a leader that froze, and the number that stops it")
        J = {k: Job(k) for k in "ABC"}
        A, B, C = J["A"], J["B"], J["C"]

        # ---------------- scene 1: the question ----------------
        self.steps("Each night, one program pays every shop what it took that day. Three copies of it run on three "
                   "machines, so one can die: job A, job B and job C. Only one may pay the shops each night.", [
            (lambda: self.cap("each night, one payout to every shop", WHITE), 0.5),
            "Three copies",
            (lambda: [LaggedStart(*[FadeIn(j.g) for j in J.values()], lag_ratio=0.2)], 0.9),
            "Only one",
            (lambda: self.cap("only one copy may pay each night", WHITE), 0.5),
        ])
        self.steps("One night, job A freezes for 15 seconds. Job B takes over and pays the shops. Then job A wakes up, "
                   "and pays them again. How do we stop that second payout? Hold that question.", [
            "job A freezes",
            (lambda: [*A.state("frozen", BLUE_M)], 0.5),
            "Job B takes over",
            (lambda: [*B.state("pays", GREEN_M)], 0.5),
            "and pays them again",
            (lambda: [*A.state("pays again", RED_M)], 0.5),
            "How do we",
            (lambda: self.bot("how do we stop the second payout?", YELLOW_M), 0.5),
        ], after=0.3)

        # ---------------- scene 2: the ticket machine ----------------
        self.steps("Picture the ticket machine at a busy post office. You pull ticket 47. When it lights up, it's your "
                   "turn, and nobody else's. Wander off, and the screen moves on to 48.", [
            (lambda: [*self.unbot(), *[a for j in J.values() for a in j.state("waiting", GREY_B, WHITE)],
                      *self.cap("a post office ticket machine: 47, then 48", WHITE)], 0.6),
            "Wander off",
            (lambda: self.bot("wander off, and the screen moves on", WHITE), 0.5),
        ])
        ebox = RoundedRectangle(corner_radius=0.14, width=EW, height=EH, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1).move_to(EC)
        etit = T("etcd: settlement/", 24, TEAL_M).move_to(EC + UP * (EH / 2 - 0.35))
        self.steps("Our ticket machine is etcd, a small service that a few servers run together, agreeing on every "
                   "change. Each copy creates a key under one shared name, settlement, and etcd stamps it with a number "
                   "from a counter that only goes up. Job A got 7, job B 9, job C 11.", [
            (lambda: [*self.unbot(), FadeIn(ebox), FadeIn(etit), *self.cap("ticket machine = etcd", TEAL_M)], 0.6),
            "Job A got 7",
            (lambda: [token_run(A.left(), [EC[0], EC[1] + KY["A"], 0], "A", WHITE, 0.5), *self.put("kA", self.key_row("A", 7, "A"))], 0.6),
            "job B 9",
            (lambda: [token_run(B.left(), [EC[0], EC[1] + KY["B"], 0], "B", WHITE, 0.5), *self.put("kB", self.key_row("B", 9, "B"))], 0.6),
            "job C 11",
            (lambda: [token_run(C.left(), [EC[0], EC[1] + KY["C"], 0], "C", WHITE, 0.5), *self.put("kC", self.key_row("C", 11, "C"))], 0.6),
        ])
        self.leases = {k: self.lease(k) for k in "ABC"}
        self.steps("The lowest ticket leads, so job A leads. Each key is tied to a lease, ten seconds here. A copy keeps "
                   "its lease alive by checking in. Stop checking in, the lease runs out, and the key is deleted. "
                   "That's wandering off.", [
            "job A leads",
            (lambda: [*A.state("leader", GREEN_M), self.lab["kA"].animate.set_color(GREEN_M)], 0.6),
            "tied to a lease",
            (lambda: [*[FadeIn(VGroup(*self.leases[k])) for k in "ABC"], *self.cap("each key lives on a 10-second lease", WHITE)], 0.6),
            "by checking in",
            (lambda: [*[dot_run(J[k].left(), [EC[0] + EW / 2 - 0.1, EC[1] + KY[k], 0], TEAL_M, 0.6) for k in "ABC"]], 0.7),
            "Stop checking in",
            (lambda: self.bot("no check-ins: the lease runs out, the key is deleted", WHITE), 0.6),
        ])
        wb = CurvedArrow(np.array([EC[0] - EW / 2 + 0.2, EC[1] + KY["B"] + 0.12, 0]), np.array([EC[0] - EW / 2 + 0.2, EC[1] + KY["A"] - 0.12, 0]),
                         angle=-TAU / 3, color=GREY_A, stroke_width=3, tip_length=0.14)
        wc = CurvedArrow(np.array([EC[0] - EW / 2 + 0.2, EC[1] + KY["C"] + 0.12, 0]), np.array([EC[0] - EW / 2 + 0.2, EC[1] + KY["B"] - 0.12, 0]),
                         angle=-TAU / 3, color=GREY_A, stroke_width=3, tip_length=0.14)
        self.steps("Job B watches job A's key, and job C watches B's. When a leader goes, only the next in line wakes up.", [
            (lambda: [*self.unbot(), Create(wb), *B.state("watches A", GREY_B, WHITE)], 0.6),
            "job C watches",
            (lambda: [Create(wc), *C.state("watches B", GREY_B, WHITE)], 0.6),
        ], after=0.3)
        self.stamp("machine")

        # ---------------- scene 3: trust the turn, and break it ----------------
        lbox = RoundedRectangle(corner_radius=0.14, width=LW, height=LH, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1).move_to(LC)
        ltit = T("payout ledger", 24, GOLD_M).move_to(LC + UP * (LH / 2 - 0.35))
        self.steps("Inside one program, a lock means one holder at a time, and etcd's election sounds like the same "
                   "promise. So job A checks: am I the leader? Yes. And it pays batch 17 into the payout ledger, the "
                   "table where each payout is recorded.", [
            (lambda: self.cap("the obvious plan: check you're the leader, then pay", PURPLE_M), 0.6),
            "am I the leader",
            (lambda: [Indicate(A.st, color=GREEN_M)], 0.6),
            "it pays batch 17",
            (lambda: [FadeIn(lbox), FadeIn(ltit)], 0.5),
            (lambda: [dot_run(A.right(), LC + LEFT * (LW / 2), GREEN_M, 0.6), *self.ledger_row(0, "batch 17 by job A", WHITE)], 0.7),
        ])
        self.steps("Now job A's program stops for 15 seconds. Java pauses everything to clean up memory, or a disk "
                   "stalls. Its check-ins stop with it. To etcd, a frozen program and a dead one look exactly the same.", [
            (lambda: [*A.state("frozen 15 s", BLUE_M), *self.cap("job A freezes for 15 seconds", BLUE_M)], 0.6),
            "Its check-ins",
            (lambda: [self.drain("A", 0.35)], 2.0),
            "To etcd",
            (lambda: self.bot("to etcd, frozen and dead look the same", WHITE), 0.5),
        ])
        self.steps("The lease runs out, and etcd deletes job A's key, as change number 12. Job B's watch fires. Its key "
                   "is now the lowest, so job B leads, and pays batch 18.", [
            (lambda: [self.drain("A", 0.0)], 0.6),
            "etcd deletes",
            (lambda: [*self.drop("kA"), FadeOut(VGroup(*self.leases["A"])), FadeOut(wb), *self.bot("lease gone: key deleted at revision 12", WHITE)], 0.6),
            "Job B's watch",
            (lambda: [Indicate(self.lab["kB"], color=YELLOW_M, scale_factor=1.15)], 0.6),
            "job B leads",
            (lambda: [*B.state("leader", GREEN_M), self.lab["kB"].animate.set_color(GREEN_M), *C.state("watches B", GREY_B, WHITE)], 0.6),
            "pays batch 18",
            (lambda: [dot_run(B.right(), LC + LEFT * (LW / 2), GREEN_M, 0.6), *self.ledger_row(1, "batch 18 by job B", WHITE)], 0.7),
        ])
        self.steps("Then job A wakes, and finishes the payout it was writing when it froze. It checked it was leader "
                   "before the freeze, and nothing has told it otherwise.", [
            (lambda: [*A.state("awake, still sure", YELLOW_M, WHITE), *self.unbot()], 0.6),
            "finishes the payout",
            (lambda: [dot_run(A.right(), LC + LEFT * (LW / 2), RED_M, 0.6), *self.ledger_row(2, "job A pays again", RED_M)], 0.7),
            "nothing has told it",
            (lambda: self.cap("job A checked before the freeze; nothing told it otherwise", WHITE), 0.6),
        ])
        self.steps("Well, the shops in batch 17 may just have been paid twice.", [
            (lambda: [*self.bot("two copies paid: shops may be paid twice", RED_M), Indicate(self.lab["row2"], color=RED_M)], 0.7),
        ], after=0.3)
        self.steps("And this isn't rare. In 2020, Jepsen, a project that tests databases by breaking them, saw two "
                   "holders of an etcd lock overlap within minutes, even in a healthy cluster.", [
            "In 2020",
            (lambda: self.cap("Jepsen, 2020: two etcd lock holders overlapped within minutes", WHITE), 0.6),
        ], after=0.3)
        self.stamp("broken")

        # ---------------- scene 4: the wish, and why checking again isn't enough ----------------
        self.steps("Couldn't job A just check again, right before it writes? It should, but the freeze can land between "
                   "the check and the write, and from inside, a freeze is invisible.", [
            (lambda: [*self.unbot(), *self.cap("check again right before writing?", PURPLE_M)], 0.5),
            "between the check",
            (lambda: self.bot("check ... freeze ... write: the gap is still there", WHITE), 0.6),
        ])
        self.steps("What we want is someone who sees the write at the moment it arrives, and can say no.", [
            (lambda: [*self.cap("wanted: someone who sees the write arrive, and can say no", YELLOW_M),
                      Indicate(lbox, color=GOLD_M, scale_factor=1.03)], 0.7),
        ], after=0.3)

        # ---------------- scene 5: the counter, predict ----------------
        self.steps("Back to the post office. The clerk who has called 48 won't serve ticket 47. So let every write carry "
                   "the writer's ticket number, and let the ledger remember the highest it has accepted.", [
            (lambda: [*self.unbot(), *self.cap("the clerk who has called 48 won't serve 47", WHITE),
                      *[FadeOut(self.lab.pop(f"row{i}")) for i in range(3)]], 0.6),
            "let the ledger",
            (lambda: self.ledger_highest("-", GREY_B), 0.5),
        ])
        self.steps("Replay it. Job A pays batch 17 with token 7. Nothing higher has been seen, so it's accepted. Job B "
                   "pays batch 18 with token 9. 9 is higher than 7, so it's accepted, and the ledger remembers 9.", [
            "Job A pays",
            (lambda: [token_run(A.right(), LC + LEFT * (LW / 2), "7", GREEN_M, 0.7)], 0.8),
            "so it's accepted",
            (lambda: [*self.ledger_highest(7), *self.ledger_row(0, "batch 17, token 7: accepted", GREEN_M)], 0.5),
            "Job B",
            (lambda: [token_run(B.right(), LC + LEFT * (LW / 2), "9", GREEN_M, 0.7)], 0.8),
            "and the ledger remembers",
            (lambda: [*self.ledger_highest(9, YELLOW_M), *self.ledger_row(1, "batch 18, token 9: accepted", GREEN_M)], 0.5),
        ])
        self.steps("Now job A wakes and writes with token 7. What does the ledger do? Pause and guess.", [
            (lambda: [*self.cap("job A writes with token 7: what does the ledger do?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("It refuses. 7 is lower than 9. One copy paid, one copy was turned away at the counter.", [
            (lambda: [token_run(A.right(), LC + LEFT * (LW / 2) + LEFT * 0.1, "7", RED_M, 0.7)], 0.8),
            (lambda: [*self.ledger_row(2, "token 7: refused, 7 < 9", RED_M)], 0.5),
            "One copy paid",
            (lambda: self.bot("one payout; the frozen copy is turned away at the counter", GREEN_M), 0.6),
        ], after=0.3)
        self.stamp("fenced")

        # ---------------- scene 6: the name ----------------
        self.steps("That's called fencing, and the number is a fencing token. Here it comes free. The key's revision was "
                   "handed out by etcd's agreement, so no two leaders share one, and every new leader's is higher.", [
            (lambda: [*self.unbot(), *self.cap("fencing: every write carries a token; the resource refuses old ones", TEAL_M)], 0.6),
            "comes free",
            (lambda: [Indicate(self.lab["kB"], color=TEAL_M, scale_factor=1.15), Indicate(self.lab["kC"], color=TEAL_M, scale_factor=1.15)], 0.8),
        ])
        self.steps("Job A's next check-in fails. Now it knows it lost, so it rejoins at the back, with a new key at "
                   "revision 13. A token never comes back down.", [
            "Job A's next",
            (lambda: [*A.state("lost the lease", GREY_B, WHITE)], 0.5),
            "rejoins at the back",
            (lambda: [*self.put("kA2", self.key_row("A2", 13, "A")), *A.state("watches C", GREY_B, WHITE)], 0.6),
            "never comes back",
            (lambda: self.bot("a token never comes back down", WHITE), 0.5),
        ], after=0.3)

        # ---------------- scene 7: the guardrail ----------------
        self.steps("One rule keeps it honest. The check must happen at the ledger, in the same all or nothing step as the "
                   "write. Check in one step and write in the next, and you've reopened the gap. In a SQL database, "
                   "that's one conditional statement.", [
            (lambda: [*self.unbot(), *self.cap("the check and the write: one all-or-nothing step", YELLOW_M)], 0.6),
            "Check in one step",
            (lambda: self.bot("check, then write in a second step: the gap is back", RED_M), 0.6),
            "In a SQL database",
            (lambda: self.bot("in SQL: one conditional statement", WHITE), 0.5),
        ])
        self.steps("And the lease length is a trade. After a crash in the lesson's run, the next job waited 56 seconds, "
                   "the rest of a 60-second lease. Shorter leases take over faster, with more false alarms.", [
            (lambda: self.cap("the lease length is a trade", WHITE), 0.5),
            "56",
            (lambda: self.bot("a crash: 56 seconds of waiting, the rest of a 60-second lease", WHITE), 0.6),
            "Shorter leases",
            (lambda: self.bot("shorter lease: faster takeover, more false alarms", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: a lease says who should act. Only the resource can refuse the one who "
                   "shouldn't.", [
            (lambda: [*self.unbot(), *self.cap("a lease says who should act", YELLOW_M, 28)], 0.6),
            "Only the resource",
            (lambda: self.bot("only the resource can refuse the one who shouldn't", YELLOW_M, 28), 0.6),
        ], after=0.3)
        self.steps("One quick check. Job B freezes next, and job C takes over with token 11. Then job B wakes and writes "
                   "with token 9. Accepted or refused? Pause and think.", [
            (lambda: [*self.unbot(), *self.cap("job C leads with 11; job B wakes and writes with 9: accepted?  pause and think", YELLOW_M),
                      *B.state("frozen", BLUE_M), *C.state("leader", GREEN_M), self.lab["kC"].animate.set_color(GREEN_M)], 0.7),
        ], after=0)
        self.countdown(3.0)
        self.steps("Refused. Once the ledger has seen 11, every 9 is old news.", [
            (lambda: [*self.ledger_highest(11, YELLOW_M), token_run(B.right(), LC + LEFT * (LW / 2) + LEFT * 0.1, "9", RED_M, 0.7)], 0.8),
            (lambda: self.bot("9 < 11: refused", RED_M), 0.5),
        ], after=0.3)
        self.play(*self.cap("the counter says no", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
