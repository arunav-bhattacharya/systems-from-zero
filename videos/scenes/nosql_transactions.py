from sfz import *

# Amounts are said the way people say them ("seventy"); captions keep "70.00".
SAY[0:0] = [
    (r"\b(\d+)\.00\b", r"\1"),
    (r"\bA-(\d)00(\d)\b", r"A \1 thousand \2"),
    (r"\bT(\d)\b", r"T \1"),
    (r"\bTransactionConflict\b", "Transaction Conflict"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CO_X, CO_Y, CO_W, CO_H = [-5.4, -3.6, -1.8], 2.2, 1.5, 1.0         # the coordinator fleet
CO_LAB_Y = 3.08
LG_X, LG_Y, LG_W, LG_H = 3.9, 2.35, 5.0, 1.6                         # the ledger
NX, NY, NW, NH = [-4.4, 0.0, 4.4], -0.45, 3.8, 2.6                    # three storage nodes
N_TOP = NY + NH / 2
ID_Y, OWN_Y, BAL_Y, HELD_Y = 0.52, 0.15, -0.42, -1.25
BAR_Y, CAP_Y = -2.55, -3.2
TC = {"T1": BLUE_M, "T2": GOLD_M, "T3": PURPLE_M}


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
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(cx, cy, w, h, color, a=0.14):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(
        fillc(color, a), 1).move_to([cx, cy, 0])


def padlock(at, color=RED_M):
    body = RoundedRectangle(corner_radius=0.04, width=0.26, height=0.2, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.4), 1)
    shackle = Arc(radius=0.085, start_angle=0, angle=PI, stroke_color=color, stroke_width=2.5)
    shackle.next_to(body, UP, buff=-0.01)
    return VGroup(shackle, body).move_to(at)


class NosqlTransactions(Base):
    """txn-08, section 0. A family's second payment comes back at once with "try again". Last lesson's weak spot was
    waiting on one coordinator. DynamoDB: items in partitions on storage nodes; one request, all or none. The travel
    agent: holds, no waiting list, a file in a shared cabinet any colleague can finish. T1 and T2 collide on A-1001:
    three checks at prepare, T2 rejected at once, one no cancels; T1's decision in the ledger; its coordinator dies
    and another finishes it; two writes per item; T2 retried with the same idempotency key. The rule, limits, check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def _set(self, store, key, new):
        old, store[key] = store[key], new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def node_id(self, n, s, owner):
        return self._set(self.ids, n, VGroup(M(s, 24).move_to([NX[n], ID_Y, 0]), T(owner, 19, GREY_B).move_to([NX[n], OWN_Y, 0])))

    def bal(self, n, s, color=WHITE):
        return self._set(self.bals, n, M(s, 34, color).move_to([NX[n], BAL_Y, 0]))

    def held(self, n, t, color=None):
        """Mark node n as held by transaction t (or free when t is None)."""
        if t is None:
            return self._set(self.helds, n, T("free", 19, GREY_B).move_to([NX[n], HELD_Y, 0]))
        g = VGroup(T("held by", 19, GREY_B), M(t, 20, color or TC.get(t, WHITE))).arrange(RIGHT, buff=0.2)
        return self._set(self.helds, n, g.move_to([NX[n], HELD_Y, 0]))

    def job(self, c, t):
        if t is None:
            return self._set(self.jobs, c, None)
        return self._set(self.jobs, c, M(t, 20, TC[t]).move_to([CO_X[c], CO_Y - 0.22, 0]))

    def ledger(self, s, color=GREEN_M):
        if s is None:
            return self._set(self.lgs, 0, None)
        return self._set(self.lgs, 0, M(s, 22, color).move_to([LG_X, LG_Y - 0.4, 0]))

    def go(self, c, n, color=YELLOW_M, back=False):
        """A dot runs from coordinator c to node n (a message), or back (an answer)."""
        a = np.array([CO_X[c], CO_Y - CO_H / 2, 0])
        b = np.array([NX[n], N_TOP, 0])
        if back:
            a, b = b, a
        d = Dot(radius=0.08, color=color).move_to(a)
        return [Succession(FadeIn(d, run_time=0.05), d.animate(run_time=0.5, rate_func=smooth).move_to(b),
                           FadeOut(d, run_time=0.1))]

    def to_ledger(self, c, color=GREEN_M, back=False):
        a = np.array([CO_X[c] + CO_W / 2, CO_Y + 0.25, 0])
        b = np.array([LG_X - LG_W / 2, CO_Y + 0.25, 0])
        if back:
            a, b = b, a
        d = Dot(radius=0.08, color=color).move_to(a)
        return [Succession(FadeIn(d, run_time=0.05), d.animate(run_time=0.5, rate_func=smooth).move_to(b),
                           FadeOut(d, run_time=0.1))]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.ids, self.bals, self.helds = [None] * 3, [None] * 3, [None] * 3
        self.jobs = [None] * 3
        self.lgs = [None]
        self.title_card("Why didn't my payment wait its turn?", "transactions across machines, with nobody to wait for")

        # ---------------- scene 1: the hook ----------------
        acct = VGroup(rbox(0, 0.9, 3.6, 2.0, WHITE, 0.08), T("family account", 22, GREY_B).move_to([0, 1.55, 0]))
        hb = M("100.00", 44).move_to([0, 0.7, 0])
        groc = VGroup(T("groceries", 22, GOLD_M), M("50.00", 30, GOLD_M)).arrange(DOWN, buff=0.15).move_to([-4.6, 0.9, 0])
        bike = VGroup(T("bike repair", 22, BLUE_M), M("30.00", 30, BLUE_M)).arrange(DOWN, buff=0.15).move_to([4.6, 0.9, 0])
        same = T("the same second", 22, GREY_B).move_to([0, 2.55, 0])
        self.steps("Picture a family sharing one account in a payments app, with 100.00 in it. "
                   "Two of them pay at the same second: 50.00 for groceries, and 30.00 for a bike repair.", [
            (lambda: [FadeIn(acct, shift=0.2 * UP)], 0.7),
            (lambda: [FadeIn(hb)], 0.4),
            "Two of them",
            (lambda: [FadeIn(groc, shift=0.2 * RIGHT), FadeIn(bike, shift=0.2 * LEFT), FadeIn(same)], 0.8),
        ])
        ok = VGroup(tick(True, 0.18), T("paid", 22, GREEN_M)).arrange(RIGHT, buff=0.2).next_to(bike, DOWN, buff=0.35)
        err = VGroup(T("\"someone else is busy with", 21, RED_M), T("this account, try again\"", 21, RED_M)).arrange(DOWN, buff=0.1)
        err.next_to(groc, DOWN, buff=0.35)
        self.steps("There's enough for both. The bike repair goes through. The groceries come back at once, "
                   "with an error: someone else is busy with this account, try again.", [
            "The bike repair",
            (lambda: [FadeIn(ok, shift=0.1 * UP), Transform(hb, M("70.00", 44).move_to(hb))], 0.7),
            "The groceries",
            (lambda: [FadeIn(err, shift=0.1 * UP)], 0.7),
        ])
        self.steps("Why didn't it just wait its turn, like a queue at a counter? Waiting feels fair, and safe.", [
            (lambda: self.cap("why not wait in line?", WHITE), 0.6),
        ])

        # ---------------- scene 2: last lesson's weak spot ----------------
        nodes = [rbox(NX[n], NY, NW, NH, WHITE, 0.0).set_fill(BLACK, 1) for n in range(3)]
        cos = [VGroup(rbox(CO_X[c], CO_Y, CO_W, CO_H, PURPLE_M), M(f"C{c + 1}", 20, PURPLE_M).move_to([CO_X[c], CO_Y + 0.25, 0]))
               for c in range(3)]
        machine = [T("a machine", 22, GREY_B).move_to([NX[n], ID_Y, 0]) for n in range(2)]
        locks = [padlock([NX[n] + NW / 2 - 0.35, ID_Y, 0]) for n in range(2)]
        dead = tick(False, 0.28).move_to(cos[0][0])
        self.steps("Last lesson, waiting was exactly the weak spot. When one payment touches records on two machines, "
                   "a coordinator, the program in charge, asks each machine to promise, writes its decision in its log, "
                   "and then tells them to commit.", [
            (lambda: [FadeOut(VGroup(acct, hb, groc, bike, same, ok, err)), *self.uncap()], 0.6),
            "When one payment",
            (lambda: [FadeIn(nodes[0]), FadeIn(nodes[1]), FadeIn(machine[0]), FadeIn(machine[1])], 0.6),
            "a coordinator",
            (lambda: [FadeIn(cos[0])], 0.5),
            "asks each machine",
            (lambda: [*self.go(0, 0), *self.go(0, 1)], 0.6),
            (lambda: [FadeIn(locks[0], scale=0.6), FadeIn(locks[1], scale=0.6), *self.go(0, 0, GREEN_M, True), *self.go(0, 1, GREEN_M, True)], 0.6),
        ])
        self.steps("And if the coordinator crashes after the promises, the machines wait, holding their records locked, "
                   "until that one program comes back. Everyone in the queue waits with them.", [
            "crashes",
            (lambda: [Create(dead), cos[0][0].animate.set_stroke(RED_M)], 0.6),
            "the machines wait",
            (lambda: [*self.cap("last lesson: one coordinator dies, and everyone waits", RED_M),
                      locks[0].animate(rate_func=there_and_back).scale(1.6), locks[1].animate(rate_func=there_and_back).scale(1.6)], 0.9),
        ])

        # ---------------- scene 3: DynamoDB ----------------
        self.steps("Today's database is DynamoDB, Amazon's database service. You store items, records you look up by a key, "
                   "and Amazon spreads them over many machines.", [
            (lambda: [FadeOut(dead), FadeOut(locks[0]), FadeOut(locks[1]), cos[0][0].animate.set_stroke(PURPLE_M), *self.uncap()], 0.6),
            "Amazon spreads",
            (lambda: [FadeIn(nodes[2])], 0.6),
        ])
        self.steps("Each slice of the data is called a partition, and lives on its own machine, a storage node. "
                   "The family's account is item A-1001. The bike shop is A-2002, and the grocer is A-3003. "
                   "Three items, three machines.", [
            "a storage node",
            (lambda: [*self.cap("a partition: one slice of the data, on its own storage node", WHITE)], 0.5),
            "The family's",
            (lambda: [FadeOut(machine[0]), *self.node_id(0, "A-1001", "the family"), *self.bal(0, "100.00"), *self.held(0, None)], 0.6),
            "The bike shop",
            (lambda: [FadeOut(machine[1]), *self.node_id(1, "A-2002", "the bike shop"), *self.bal(1, "50.00"), *self.held(1, None)], 0.6),
            "and the grocer",
            (lambda: [*self.node_id(2, "A-3003", "the grocer"), *self.bal(2, "0.00"), *self.held(2, None)], 0.6),
        ])
        self.steps("DynamoDB takes a list of changes in one request, and applies all of them, or none.", [
            (lambda: self.cap("one request: a list of changes, all or none", WHITE), 0.6),
        ])

        # ---------------- scene 4: the travel agent ----------------
        lg = VGroup(rbox(LG_X, LG_Y, LG_W, LG_H, GREEN_M), T("ledger", 26, GREEN_M).move_to([LG_X, LG_Y + 0.55, 0]),
                    T("a table, with copies on several machines", 18, GREY_B).move_to([LG_X, LG_Y + 0.18, 0]))
        co_lab = T("coordinators: any one can take any transaction", 19, GREY_B).move_to([-3.6, CO_LAB_Y, 0])
        self.steps("So how does it avoid the waiting? Picture a travel agent booking a flight and a hotel for one trip. "
                   "She asks each to hold a booking, and a held seat can't go to anyone else.", [
            (lambda: self.cap("a travel agent: one trip, a flight and a hotel", YELLOW_M), 0.6),
            "She asks each",
            (lambda: [*self.go(0, 1), *self.go(0, 2)], 0.6),
            "a held seat",
            (lambda: [*self.cap("\"please hold it\"   a held seat goes to nobody else", YELLOW_M)], 0.5),
        ])
        self.steps("When both are held, she writes confirmed in the file, and tells both.", [
            "she writes",
            (lambda: self.cap("both held: write \"confirmed\" in the file, then tell both", YELLOW_M), 0.6),
        ])
        self.steps("Here's the twist. If the seat is already held for another trip, the airline says no at once. No waiting list. "
                   "And the file sits in a shared cabinet, so if she goes home sick, any colleague can finish the booking.", [
            "says no at once",
            (lambda: self.cap("already held for another trip? \"no\", at once", RED_M), 0.6),
            "shared cabinet",
            (lambda: self.cap("the file sits in a shared cabinet; any colleague can finish", YELLOW_M), 0.6),
        ])
        self.steps("Let's map it. The hold is a prepare. The file is DynamoDB's ledger. And the colleague is another coordinator, "
                   "because Amazon runs a whole fleet of them, and any one can take any transaction.", [
            "The hold is",
            (lambda: self.cap("the hold = prepare,   the file = ledger,   a colleague = another coordinator", WHITE), 0.6),
            "The file is",
            (lambda: [FadeIn(lg, shift=0.1 * DOWN)], 0.7),
            "a whole fleet",
            (lambda: [FadeIn(cos[1]), FadeIn(cos[2]), FadeIn(co_lab)], 0.7),
        ])
        self.steps("The picture breaks on time. A hold lasts a day. Here, the whole thing takes milliseconds.", [
            (lambda: self.cap("where the picture breaks: a day, against milliseconds"), 0.6),
        ])

        # ---------------- scene 5: two payments collide ----------------
        self.steps("Now the two payments. T1, the bike repair, goes to coordinator one. T2, the groceries, goes to coordinator two.", [
            (lambda: self.uncap(), 0.3),
            "T1, the bike",
            (lambda: [*self.job(0, "T1"), *self.cap("T1: 30.00 to the bike shop     T2: 50.00 to the grocer", WHITE)], 0.6),
            "T2, the groceries",
            (lambda: self.job(1, "T2"), 0.6),
        ])
        checks = VGroup(T("1. balance at least 30.00?", 21), T("2. newer than the item's last write?", 21),
                        T("3. nobody else busy with it?", 21)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        checks.move_to([0, -2.62, 0])
        self.steps("Phase one is prepare. Coordinator one asks the family's node to check three things. Is the balance at least 30? "
                   "Is this transaction newer than the item's last write? And is nobody else busy with it?", [
            (lambda: [*self.uncap(), *self.go(0, 0)], 0.6),
            "Is the balance",
            (lambda: [FadeIn(checks[0], shift=0.1 * UP)], 0.4),
            "Is this transaction",
            (lambda: [FadeIn(checks[1], shift=0.1 * UP)], 0.4),
            "And is nobody",
            (lambda: [FadeIn(checks[2], shift=0.1 * UP)], 0.4),
        ])
        self.steps("All three hold, so the node says yes, and notes T1 next to the item. "
                   "Nothing has changed yet, but the account is now spoken for.", [
            (lambda: [LaggedStart(*[Indicate(c, color=GREEN_M, scale_factor=1.05) for c in checks], lag_ratio=0.25)], 0.9),
            "says yes",
            (lambda: [FadeOut(checks), *self.go(0, 0, GREEN_M, True), *self.held(0, "T1")], 0.7),
            "Nothing has changed",
            (lambda: [Indicate(self.bals[0], color=WHITE, scale_factor=1.12)], 0.8),
        ])
        self.steps("T2 happens to reach the grocer first, and that node says yes. Then it reaches the family's account, "
                   "which T1 holds. Does T2 wait in line? Pause and guess.", [
            "T2 happens",
            (lambda: self.go(1, 2), 0.6),
            "that node says yes",
            (lambda: [*self.go(1, 2, GREEN_M, True), *self.held(2, "T2")], 0.6),
            "Then it reaches",
            (lambda: self.go(1, 0), 0.6),
            "which T1 holds",
            (lambda: [Indicate(self.helds[0], color=BLUE_M, scale_factor=1.15)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. The node rejects it at once. DynamoDB never makes one transaction wait for another's item.", [
            (lambda: [*self.uncap(), *self.go(1, 0, RED_M, True)], 0.6),
            (lambda: [self.jobs[1].animate.set_color(RED_M)], 0.4),
            "never makes",
            (lambda: self.cap("no waiting list: a held item says no at once", RED_M), 0.6),
        ])
        self.steps("And one no cancels the whole thing. Coordinator two tells the grocer's node to forget T2. "
                   "Your code gets an error called TransactionConflict. That's the family's try again.", [
            "Coordinator two tells",
            (lambda: self.go(1, 2, RED_M), 0.6),
            (lambda: self.held(2, None), 0.5),
            "Your code gets",
            (lambda: self.cap("T2 cancelled: TransactionConflict, \"try again\"", RED_M), 0.6),
        ])

        # ---------------- scene 6: the ledger, a crash, and another coordinator ----------------
        self.steps("Meanwhile the bike shop's node says yes to T1. Everyone has promised, so coordinator one writes "
                   "T1 commit in the ledger, before anything changes. That line is the commit point.", [
            (lambda: [*self.uncap(), *self.go(0, 1)], 0.6),
            "says yes to T1",
            (lambda: [*self.go(0, 1, GREEN_M, True), *self.held(1, "T1")], 0.6),
            "writes",
            (lambda: self.to_ledger(0), 0.6),
            (lambda: self.ledger("T1: commit"), 0.5),
            "That line",
            (lambda: [*self.cap("the commit point: the decision, in the ledger", GREEN_M), Indicate(self.lgs[0], color=GREEN_M, scale_factor=1.2)], 0.8),
        ])
        dead1 = tick(False, 0.28).move_to(cos[0][0])
        self.steps("Now suppose coordinator one crashes, right here. Last lesson, everything would wait for it. "
                   "Here, a recovery program reads the ledger, and hands T1 to coordinator three.", [
            (lambda: self.uncap(), 0.3),
            "crashes",
            (lambda: [Create(dead1), cos[0][0].animate.set_stroke(RED_M), self.jobs[0].animate.set_opacity(0.3)], 0.6),
            "a recovery program",
            (lambda: [Indicate(self.lgs[0], color=GREEN_M, scale_factor=1.2), *self.cap("a recovery program reads the ledger", WHITE)], 0.8),
            "hands T1",
            (lambda: [*self.to_ledger(2, GREEN_M, back=True), *self.job(2, "T1")], 0.6),
        ])
        self.steps("Coordinator three sends the commits. Each node applies its change and lets go of the item. "
                   "The family has 70.00, the bike shop 80.00.", [
            "sends the commits",
            (lambda: [*self.go(2, 0, GREEN_M), *self.go(2, 1, GREEN_M)], 0.6),
            "Each node applies",
            (lambda: [*self.bal(0, "70.00"), *self.bal(1, "80.00", GREEN_M), *self.held(0, None), *self.held(1, None)], 0.7),
            "The family has",
            (lambda: [Indicate(self.bals[0], color=WHITE, scale_factor=1.12), Indicate(self.bals[1], color=GREEN_M, scale_factor=1.12)], 0.8),
        ])
        self.steps("Two rounds, with a write on each item in each round. So every item in a transaction costs two writes.", [
            (lambda: self.cap("prepare + commit: two writes per item", WHITE), 0.6),
            (lambda: [LaggedStart(*[st for n in (0, 1) for st in self.go(2, n)], lag_ratio=0.3),], 0.8),
        ])

        # ---------------- scene 7: the retry ----------------
        self.steps("And T2? DynamoDB's library doesn't retry it for you. Your code waits a few random milliseconds, "
                   "and sends T2 again, with the same idempotency key, a unique id that makes a repeat do nothing.", [
            (lambda: [*self.uncap(), FadeOut(dead1), cos[0][0].animate.set_stroke(PURPLE_M), *self.job(0, None), *self.job(2, None),
                      *self.ledger(None)], 0.6),
            "Your code waits",
            (lambda: self.cap("your code retries: same idempotency key, a new attempt", WHITE), 0.6),
            "and sends T2",
            (lambda: [*self.job(1, "T2")], 0.5),
        ])
        self.steps("The new try checks the balance again: 70 is at least 50. Everyone says yes, and it commits. "
                   "The family has 20.00 left, and the grocer 50.00.", [
            (lambda: [*self.go(1, 0), *self.go(1, 2)], 0.6),
            "70 is at least",
            (lambda: [Indicate(self.bals[0], color=WHITE, scale_factor=1.15)], 0.6),
            "Everyone says yes",
            (lambda: [*self.go(1, 0, GREEN_M, True), *self.go(1, 2, GREEN_M, True), *self.held(0, "T2"), *self.held(2, "T2")], 0.6),
            "and it commits",
            (lambda: [*self.to_ledger(1), *self.ledger("T2: commit")], 0.6),
            "The family has",
            (lambda: [*self.go(1, 0, GREEN_M), *self.go(1, 2, GREEN_M)], 0.5),
            (lambda: [*self.bal(0, "20.00"), *self.bal(2, "50.00", GREEN_M), *self.held(0, None), *self.held(2, None),
                      *self.cap("100.00 - 30.00 - 50.00 = 20.00", GREEN_M)], 0.6),
        ])

        # ---------------- scene 8: the rule ----------------
        self.steps("So here's the rule across machines. Everyone promises first. One decision is written where a crash can't erase it. "
                   "Only then does anything change.", [
            (lambda: [*self.job(1, None), *self.cap("1. everyone promises", YELLOW_M)], 0.5),
            "One decision",
            (lambda: [*self.cap("2. one decision, written where a crash can't erase it", YELLOW_M), glow(lg[0], GREEN_M, 1.02)], 0.8),
            "Only then",
            (lambda: self.cap("3. only then does anything change", YELLOW_M), 0.5),
        ])
        self.steps("DynamoDB adds two things. A busy item says no, instead of making you wait. And any coordinator can finish the job.", [
            "A busy item",
            (lambda: self.cap("a busy item says no;  any coordinator can finish", WHITE), 0.6),
            "any coordinator",
            (lambda: [LaggedStart(*[glow(c[0], PURPLE_M, 1.05) for c in cos], lag_ratio=0.2)], 0.9),
        ])

        # ---------------- scene 9: limits ----------------
        self.steps("It has limits. One transaction holds up to 100 changes, in one Region, one of Amazon's areas of data centres. "
                   "And a busy account means more rejections and more retries, each paying for its writes. "
                   "So keep transactions small, and few on the same item.", [
            (lambda: self.cap("up to 100 changes, in one Region", WHITE), 0.5),
            "And a busy account",
            (lambda: self.cap("a busy account: more no's, more retries, more writes", RED_M), 0.5),
            "So keep",
            (lambda: self.cap("keep transactions small, and few on one item", YELLOW_M), 0.5),
        ])
        self.steps("Think of it as an airline that never keeps a waiting list. A bit rude, but nobody is ever stuck in it.", [
            "A bit rude",
            (lambda: [Wiggle(nodes[0], scale_value=1.03)], 0.8),
        ], after=0.5)

        # ---------------- scene 10: a check ----------------
        self.steps("One quick check. T3 wants to take money from the bike shop's account while T1 holds it, "
                   "prepared but not yet committed. What does the bike shop's node say? Pause and think.", [
            (lambda: [*self.uncap(), *self.ledger(None), *self.held(1, "T1"), *self.job(0, "T1")], 0.6),
            "T3 wants",
            (lambda: [*self.job(1, "T3")], 0.5),
            (lambda: self.go(1, 1, PURPLE_M), 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No, at once. T3 is cancelled, and its code tries again after T1 lets go.", [
            (lambda: [*self.uncap(), *self.go(1, 1, RED_M, True)], 0.6),
            (lambda: self.cap("held? \"no\", at once. Then retry.", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.wait(2.0)
