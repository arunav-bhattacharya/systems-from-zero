from sfz import *

SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bSQLSTATE\b", "S Q L state"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_POS = np.array([0, 3.1, 0])              # unused chip slot, top centre
CX, AX, BX = 0.0, -4.6, 4.6                # committed data, Tx A, Tx B
BOX_Y, BOX_W, BOX_H = 0.8, 3.8, 3.2
L1, L2, L3 = 1.6, 0.85, 0.0               # three lines inside each box
TITLE_Y = 2.75
SQL_Y = -1.65
CNT_Y, BAR_Y, CAP_Y = -2.55, -2.95, -3.35
A_C, B_C = BLUE_M, GOLD_M

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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    # captions, a counter line, and labels that swap in place
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def count(self, s, color=WHITE, size=24):
        return self.put("cnt", fit(T(s, size, color), 13.0).move_to([0, CNT_Y, 0]))

    def query(self, s, color=YELLOW_M):
        """A query chip; a list of strings stacks into lines so long filters stay readable."""
        lines = s if isinstance(s, list) else [s]
        t = VGroup(*[M(x, 19) for x in lines]).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=t.height + 0.26, stroke_color=color, stroke_width=2.5)
        r.set_fill(color, opacity=0.18)
        return self.put("q", fit(VGroup(r, t.move_to(r)), 3.9).move_to(Q_POS + 0.25 * LEFT))

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


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def frame(x, color, w=BOX_W):
    return RoundedRectangle(corner_radius=0.16, width=w, height=BOX_H, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.08), 1).move_to([x, BOX_Y, 0])


def line(x, y, s, color=WHITE, size=26, mono=False):
    return (M if mono else T)(s, size, color).move_to([x, y, 0])


def cake(x, y, color):
    base = RoundedRectangle(corner_radius=0.08, width=0.9, height=0.5, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.5), 1)
    top = RoundedRectangle(corner_radius=0.06, width=0.9, height=0.14, stroke_width=0).set_fill(WHITE, 0.85)
    top.move_to(base.get_top() + 0.07 * DOWN)
    return VGroup(base, top).move_to([x, y, 0])


def person(x, y, color):
    head = Circle(radius=0.22, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.3), 1).move_to([x, y + 0.45, 0])
    body = RoundedRectangle(corner_radius=0.2, width=0.8, height=0.65, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.3), 1)
    body.move_to([x, y - 0.15, 0])
    return VGroup(body, head)


class WriteSkew(Base):
    """txn-01, section 3. Ivy's two accounts of 50.00 and two payments of 80.00 end at minus 60.00; two flatmates take
    two different cakes; inside PostgreSQL: accounts 109 and 209 at 5,000, two withdrawals of 8,000 at Repeatable Read,
    both see 10,000, different rows, no wait, both commit, -6,000; write skew named; Oracle's SERIALIZABLE is snapshot
    isolation; fix 1, FOR UPDATE; fix 2, Serializable with SQLSTATE 40001 and a retry; a check (two refunds)."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Both checked, both paid", "how Ivy goes below zero")

        # committed data and the two transactions (built now, shown on cue)
        cfr = frame(CX, WHITE)
        afr, bfr = frame(AX, A_C), frame(BX, B_C)
        ct = T("committed data", 24, GREY_B).move_to([CX, TITLE_Y, 0])
        at = T("Tx A: from 109", 24, A_C).move_to([AX, TITLE_Y, 0])
        bt = T("Tx B: from 209", 24, B_C).move_to([BX, TITLE_Y, 0])
        self.rows = {}

        def crow(key, s, y, color=WHITE):
            return self.put(key, line(CX, y, s, color, 28))

        # ---------------- scene 1: the puzzle ----------------
        accts = VGroup(box("account 1: 50.00", WHITE, size=24, w=3.6), box("account 2: 50.00", WHITE, size=24, w=3.6)).arrange(RIGHT, buff=1.2).move_to([0, 1.6, 0])
        pays = [chip("groceries: 80.00", A_C, 22).move_to([accts[0].get_x(), 0.2, 0]), chip("phone: 80.00", B_C, 22).move_to([accts[1].get_x(), 0.2, 0])]
        sees = [T("sees 100.00: go", 22, GREEN_M).move_to([accts[k].get_x(), -0.55, 0]) for k in range(2)]
        self.steps("Ivy has two accounts with a payments company, with 50.00 in each. The company lets one account go below zero, "
                   "as long as the two together stay at zero or above.", [
            (lambda: [LaggedStart(*[FadeIn(a, shift=0.1 * UP) for a in accts], lag_ratio=0.3)], 0.9),
            "The company lets",
            (lambda: self.cap("rule: one account may go below zero if the two together stay at zero or above", WHITE), 0.6),
        ])
        self.steps("One evening, in the same second, she pays 80.00 for groceries from one account, and her phone company takes 80.00 from the other.", [
            "she pays",
            (lambda: [FadeIn(pays[0], shift=0.1 * UP)], 0.5),
            "her phone company",
            (lambda: [FadeIn(pays[1], shift=0.1 * UP)], 0.5),
        ])
        self.steps("Each payment checks her total, sees 100.00, and goes through. Ivy ends the evening at minus 60.00.", [
            "sees 100.00",
            (lambda: [FadeIn(sees[0]), FadeIn(sees[1])], 0.6),
            "goes through",
            (lambda: [Transform(accts[0], box("account 1: −30.00", RED_M, size=24, w=3.6).move_to(accts[0])),
                      Transform(accts[1], box("account 2: −30.00", RED_M, size=24, w=3.6).move_to(accts[1]))], 0.8),
            "Ivy ends",
            (lambda: self.count("total: −60.00", RED_M, 28), 0.6),
        ])
        self.steps("Each one checked first. So how did that happen? Hold that question.", [
            (lambda: self.cap("each one checked first. so how?", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 2: two cakes ----------------
        fridge = frame(CX, WHITE)
        fr_t = T("the fridge", 22, GREY_B).move_to([CX, TITLE_Y, 0])
        cakes = [cake(CX - 0.75, BOX_Y, "#8B5A3C"), cake(CX + 0.75, BOX_Y, YELLOW_M)]
        cake_l = [T("chocolate", 18, GREY_B).move_to([CX - 0.75, BOX_Y - 0.55, 0]), T("lemon", 18, GREY_B).move_to([CX + 0.75, BOX_Y - 0.55, 0])]
        pa, pb = person(AX, BOX_Y, A_C), person(BX, BOX_Y, B_C)
        pa_t = T("flatmate 1", 22, A_C).move_to([AX, TITLE_Y, 0])
        pb_t = T("flatmate 2", 22, B_C).move_to([BX, TITLE_Y, 0])
        think = [T("sees 2 cakes: fine", 20, GREEN_M).move_to([x, -0.1, 0]) for x in (AX, BX)]
        self.steps("Picture two flatmates and a fridge with two cakes. The house rule: always leave at least one cake for guests.", [
            (lambda: [FadeOut(VGroup(accts, *pays, *sees)), *self.drop("cnt"), *self.uncap()], 0.6),
            (lambda: [FadeIn(fridge), FadeIn(fr_t), *[FadeIn(c) for c in cakes], *[FadeIn(l) for l in cake_l]], 0.7),
            (lambda: [FadeIn(pa), FadeIn(pb), FadeIn(pa_t), FadeIn(pb_t)], 0.6),
            "The house rule",
            (lambda: self.cap("house rule: always leave at least one cake for guests", WHITE), 0.6),
        ])
        self.steps("At the same moment, both open the fridge. Each sees two cakes, so each thinks, fine, I can take one.", [
            "both open",
            (lambda: [dot_run([AX + 0.6, BOX_Y, 0], [CX - 1.95, BOX_Y, 0], A_C, 0.5), dot_run([BX - 0.6, BOX_Y, 0], [CX + 1.95, BOX_Y, 0], B_C, 0.5)], 0.6),
            "Each sees",
            (lambda: [FadeIn(think[0]), FadeIn(think[1])], 0.5),
        ])
        self.steps("One takes the chocolate cake, the other takes the lemon one. They never reached for the same cake, so nobody argued. "
                   "And the guests get an empty fridge.", [
            "One takes",
            (lambda: [cakes[0].animate.move_to([AX, -1.35, 0]), FadeOut(cake_l[0])], 0.7),
            "the other takes",
            (lambda: [cakes[1].animate.move_to([BX, -1.35, 0]), FadeOut(cake_l[1])], 0.7),
            "nobody argued",
            (lambda: self.cap("different cakes: nobody argued", WHITE), 0.5),
            "an empty fridge",
            (lambda: [glow(fridge, RED_M, 1.03), *self.cap("and the guests get an empty fridge", RED_M)], 0.7),
        ])
        self.steps("Let's map it. The cakes are Ivy's two accounts. The rule over both cakes is the rule over her total. "
                   "And each flatmate is one payment, checking everything but changing only its own part.", [
            "The cakes are",
            (lambda: self.cap("cakes = Ivy's two accounts", WHITE), 0.5),
            "The rule over both",
            (lambda: self.cap("the rule over both cakes = the rule over her total", WHITE), 0.5),
            "each flatmate",
            (lambda: self.cap("each flatmate = one payment: reads both, changes one", WHITE), 0.5),
        ], after=0.3)
        self.stamp("cakes")

        # ---------------- scene 3: inside the database ----------------
        sql = VGroup(M("BEGIN ISOLATION LEVEL REPEATABLE READ;", 18, GREY_B),
                     M("SELECT sum(balance_minor) FROM accounts WHERE customer_id = 9;", 18, GREY_B),
                     M("UPDATE accounts SET balance_minor = balance_minor - 8000 WHERE account_id = 109;", 18, GREY_B),
                     M("COMMIT;", 18, GREY_B)).arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        fit(sql, 12.6).move_to([0, SQL_Y, 0])
        self.steps("Now inside the database. Ivy is customer 9. Her accounts, 109 and 209, hold 5,000 each, counted in hundredths.", [
            (lambda: [FadeOut(VGroup(pa, pb, pa_t, pb_t, *think, *cakes)), ReplacementTransform(fr_t, ct), *self.uncap()], 0.7),
            "Her accounts",
            (lambda: [*crow("c1", "109: 5,000", L1), *crow("c2", "209: 5,000", L2)], 0.6),
            "hold 5,000",
            (lambda: [*crow("c3", "total: 10,000", L3, GREY_B), *self.cap("customer 9: two accounts, counted in hundredths", WHITE)], 0.6),
        ])
        self.steps("Two withdrawals of 8,000 arrive together, one from each account. Each runs in its own transaction at Repeatable Read, "
                   "so each reads from a snapshot, a picture of the committed data taken at its first statement.", [
            "Two withdrawals",
            (lambda: [FadeIn(afr), FadeIn(bfr), FadeIn(at), FadeIn(bt)], 0.7),
            "its own transaction",
            (lambda: [FadeIn(sql)], 0.6),
            "a snapshot",
            (lambda: self.cap("snapshot: a picture of the committed data, taken at the first statement", WHITE), 0.6),
        ])
        self.steps("Each adds up her balances and sees 10,000: allowed.", [
            (lambda: [Indicate(sql[1], color=YELLOW_M, scale_factor=1.03)], 0.5),
            "sees 10,000",
            (lambda: [dot_run([CX - 1.9, L3, 0], [AX + 1.9, L1, 0], A_C, 0.5), dot_run([CX + 1.9, L3, 0], [BX - 1.9, L1, 0], B_C, 0.5),
                      *self.put("a1", line(AX, L1, "sees 10,000: allowed", GREEN_M)), *self.put("b1", line(BX, L1, "sees 10,000: allowed", GREEN_M))], 0.7),
        ])
        lockA = chip("lock: A", A_C, 18).move_to([CX + 1.15, L1, 0])
        self.steps("Transaction A takes 8,000 from 109. Its draft says minus 3,000, and it holds the lock on that row.", [
            (lambda: [Indicate(sql[2], color=A_C, scale_factor=1.03)], 0.5),
            "Its draft",
            (lambda: self.put("a2", line(AX, L2, "draft 109: −3,000", A_C)), 0.6),
            "holds the lock",
            (lambda: [self.lab["c1"].animate.shift(0.5 * LEFT), FadeIn(lockA, shift=0.1 * LEFT)], 0.6),
        ])
        self.steps("Transaction B takes 8,000 from 209. A's lock is on 109, not 209, so B doesn't wait.", [
            "Transaction B",
            (lambda: self.put("b2", line(BX, L2, "draft 209: −3,000", B_C)), 0.6),
            "not 209",
            (lambda: [glow(lockA[0], A_C, 1.1)], 0.5),
            "doesn't wait",
            (lambda: self.cap("different rows: no lock in the way, no waiting", WHITE), 0.6),
        ], after=0.3)
        self.stamp("drafts")

        # ---------------- scene 4: predict the commits ----------------
        self.steps("Now both commit. Does either one fail? Pause and guess.", [
            (lambda: [FadeOut(sql), *self.put("a3", line(AX, L3, "COMMIT ?", WHITE)), *self.put("b3", line(BX, L3, "COMMIT ?", WHITE)),
                      *self.cap("does either commit fail?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("Neither. Both commits succeed. 109 is minus 3,000, 209 is minus 3,000, and Ivy's total is minus 6,000. No error anywhere.", [
            (lambda: [*self.uncap(), *self.put("a3", line(AX, L3, "COMMIT: ok", GREEN_M)), *self.put("b3", line(BX, L3, "COMMIT: ok", GREEN_M))], 0.6),
            "109 is",
            (lambda: [FadeOut(lockA), *crow("c1", "109: −3,000", L1, RED_M), dot_run([AX + 1.9, L2, 0], [CX - 1.9, L1, 0], A_C, 0.5)], 0.7),
            "209 is",
            (lambda: [*crow("c2", "209: −3,000", L2, RED_M), dot_run([BX - 1.9, L2, 0], [CX + 1.9, L2, 0], B_C, 0.5)], 0.7),
            "Ivy's total",
            (lambda: [*crow("c3", "total: −6,000", L3, RED_M), glow(cfr, RED_M, 1.03)], 0.7),
            "No error",
            (lambda: self.count("account_id 109: −3000    account_id 209: −3000", WHITE, 22), 0.5),
        ])
        self.steps("Well, the fridge is empty.", [], after=0.4)

        # ---------------- scene 5: name it ----------------
        self.steps("This is called write skew. Each transaction read rows that the other one then changed, and each write was right for the data it saw.", [
            (lambda: [*self.drop("cnt"), *self.cap("write skew", YELLOW_M, 30)], 0.6),
            "Each transaction read",
            (lambda: [dot_run([CX - 1.9, L2, 0], [AX + 1.9, L1, 0], A_C, 0.6), dot_run([CX + 1.9, L1, 0], [BX - 1.9, L1, 0], B_C, 0.6)], 0.7),
            "each write was right",
            (lambda: self.cap("each read rows the other changed; each write was right for what it saw", WHITE), 0.6),
        ])
        self.steps("Run one after the other, the second would have seen 2,000 and refused. Run together, they made a state that no order of the two could have made.", [
            "the second would have seen",
            (lambda: self.count("one after the other: B sees 2,000 and refuses", GREEN_M), 0.6),
            "Run together",
            (lambda: [*self.cap("together: a state no order of the two could make", RED_M)], 0.6),
        ])
        self.steps("And Repeatable Read only complains when two transactions change the same row. These two didn't.", [
            (lambda: [*self.drop("cnt"), *self.cap("Repeatable Read complains only when both change the same row", WHITE)], 0.6),
            "These two didn't",
            (lambda: [glow(afr, A_C, 1.02), glow(bfr, B_C, 1.02)], 0.7),
        ])
        ex = VGroup(*[chip(s, PURPLE_M, 20) for s in ("a daily limit, several card readers", "two bookings, one meeting room", "two refunds, one payment")])
        ex.arrange(RIGHT, buff=0.3)
        fit(ex, 12.8).move_to([0, SQL_Y, 0])
        self.steps("Any rule that reads rows it doesn't write has this hole: a daily limit checked at several card readers, "
                   "two bookings of one meeting room, or two refunds of one payment.", [
            (lambda: self.cap("any rule that reads rows it doesn't write has this hole", YELLOW_M), 0.6),
            "a daily limit",
            (lambda: [FadeIn(ex[0], shift=0.1 * UP)], 0.5),
            "two bookings",
            (lambda: [FadeIn(ex[1], shift=0.1 * UP)], 0.5),
            "two refunds",
            (lambda: [FadeIn(ex[2], shift=0.1 * UP)], 0.5),
        ], after=0.3)
        self.stamp("named")

        # ---------------- scene 6: names that mislead ----------------
        lv = VGroup(*[chip(s, RED_M, 20) for s in ("Read Committed: lets it through", "Oracle SERIALIZABLE = snapshot isolation: lets it through")])
        lv.arrange(RIGHT, buff=0.3)
        fit(lv, 12.8).move_to([0, SQL_Y, 0])
        self.steps("The label won't save you either. Read Committed lets it through, and so does Oracle's level called SERIALIZABLE, "
                   "which is really snapshot isolation.", [
            (lambda: [FadeOut(ex), *self.uncap()], 0.5),
            "Read Committed",
            (lambda: [FadeIn(lv[0], shift=0.1 * UP)], 0.5),
            "Oracle's level",
            (lambda: [FadeIn(lv[1], shift=0.1 * UP)], 0.5),
        ])
        self.steps("A sign on the fridge that says serializable doesn't keep a cake in it.", [
            (lambda: self.cap("check what a level does, not what it's called", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 7: fix one, FOR UPDATE ----------------
        def reset():
            return [*crow("c1", "109: 5,000", L1), *crow("c2", "209: 5,000", L2), *crow("c3", "total: 10,000", L3, GREY_B),
                    *self.drop("a1", "a2", "a3", "b1", "b2", "b3")]

        fu = M("SELECT ... FROM accounts WHERE customer_id = 9 FOR UPDATE;", 20, GREEN_M).move_to([0, SQL_Y, 0])
        lockAll = chip("lock: A", A_C, 18)
        lockAll2 = chip("lock: A", A_C, 18)
        self.steps("The first fix: lock the fridge door before you look. Each transaction first locks all of Ivy's accounts with SELECT FOR UPDATE, then checks.", [
            (lambda: [FadeOut(lv), *reset(), *self.cap("fix 1: lock the fridge door before you look", GREEN_M)], 0.7),
            "Each transaction first",
            (lambda: [FadeIn(fu)], 0.5),
            "locks all",
            (lambda: [self.lab["c1"].animate.shift(0.5 * LEFT), self.lab["c2"].animate.shift(0.5 * LEFT),
                      FadeIn(lockAll.move_to([CX + 1.15, L1, 0])), FadeIn(lockAll2.move_to([CX + 1.15, L2, 0])),
                      *self.put("a1", line(AX, L1, "locks 109 and 209", A_C))], 0.7),
        ])
        self.steps("B's lock request waits until A commits.", [
            (lambda: [*self.put("b1", line(BX, L1, "waits for A...", GREY_B)), glow(lockAll[0], A_C, 1.1), glow(lockAll2[0], A_C, 1.1)], 0.6),
            "until A commits",
            (lambda: [*self.put("a2", line(AX, L2, "109: −3,000", A_C)), *self.put("a3", line(AX, L3, "COMMIT: ok", GREEN_M)),
                      *crow("c1", "109: −3,000", L1 , RED_M), FadeOut(lockAll), FadeOut(lockAll2), *crow("c2", "209: 5,000", L2)], 0.8),
        ])
        self.steps("Then it reads the newest values, minus 3,000 and 5,000, and refuses. Withdrawals for one customer now run one at a time.", [
            "reads the newest",
            (lambda: [*crow("c3", "total: 2,000", L3, GREY_B), *self.put("b1", line(BX, L1, "sees 2,000", WHITE))], 0.6),
            "and refuses",
            (lambda: self.put("b2", line(BX, L2, "refused", RED_M)), 0.5),
            "one at a time",
            (lambda: self.cap("one customer's withdrawals now run one at a time", WHITE), 0.6),
        ], after=0.3)
        self.stamp("forupdate")

        # ---------------- scene 8: fix two, Serializable ----------------
        err = VGroup(M("ERROR: could not serialize access due to read/write dependencies among transactions", 18, RED_M),
                     M("SQLSTATE 40001", 18, RED_M)).arrange(DOWN, buff=0.1)
        fit(err, 12.6).move_to([0, SQL_Y, 0])
        self.steps("The second fix: PostgreSQL's Serializable. It runs from snapshots as before, but it also notes what each transaction read.", [
            (lambda: [FadeOut(fu), *reset(), *self.cap("fix 2: Serializable", GREEN_M)], 0.7),
            "runs from snapshots",
            (lambda: [*self.put("a1", line(AX, L1, "sees 10,000", WHITE)), *self.put("b1", line(BX, L1, "sees 10,000", WHITE)),
                      *self.put("a2", line(AX, L2, "draft 109: −3,000", A_C)), *self.put("b2", line(BX, L2, "draft 209: −3,000", B_C))], 0.7),
            "notes what each",
            (lambda: self.cap("PostgreSQL also notes what each transaction read", WHITE), 0.6),
        ])
        self.steps("A read 209, which B wrote, and B read 109, which A wrote. No order of the two explains that, so B's commit fails with SQLSTATE 40001.", [
            "A read 209",
            (lambda: [dot_run([CX - 1.9, L2, 0], [AX + 1.9, L1, 0], A_C, 0.6)], 0.65),
            "B read 109",
            (lambda: [dot_run([CX + 1.9, L1, 0], [BX - 1.9, L1, 0], B_C, 0.6)], 0.65),
            "No order",
            (lambda: [*self.put("a3", line(AX, L3, "COMMIT: ok", GREEN_M)), *crow("c1", "109: −3,000", L1, RED_M)], 0.6),
            "B's commit fails",
            (lambda: [*self.put("b3", line(BX, L3, "COMMIT: error", RED_M)), FadeIn(err)], 0.7),
        ])
        self.steps("The program runs B again from the start. Its new snapshot includes A's commit: the total is 2,000, and the check refuses.", [
            (lambda: [*self.drop("b2", "b3"), *self.put("b1", line(BX, L1, "again from the start", B_C))], 0.6),
            "the total is 2,000",
            (lambda: [*crow("c3", "total: 2,000", L3, GREY_B), *self.put("b2", line(BX, L2, "sees 2,000", WHITE))], 0.6),
            "the check refuses",
            (lambda: self.put("b3", line(BX, L3, "refused", RED_M)), 0.5),
        ])
        self.steps("The catch: your code has to retry, and the retry has to be safe to repeat.", [
            (lambda: [FadeOut(err), *self.cap("the catch: retry, and make the retry safe to repeat", YELLOW_M)], 0.6),
        ], after=0.3)
        self.stamp("serializable")

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: checking first isn't enough when the check reads rows that someone else may change. "
                   "Lock what you read, or let Serializable catch it.", [
            (lambda: self.cap("checking first isn't enough when others change what you read", YELLOW_M, 26), 0.6),
            "Lock what you read",
            (lambda: self.cap("lock what you read, or let Serializable catch it", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.steps("One quick check. Two refunds of one payment each check how much is left, then each writes its own refund row, at Repeatable Read. "
                   "Can they refund too much? Pause and think.", [
            (lambda: [*reset(), *self.uncap(), Transform(at, T("refund 1", 22, A_C).move_to(at)), Transform(bt, T("refund 2", 22, B_C).move_to(bt)),
                      *crow("c1", "payment: 80.00", L1), *crow("c2", "refunds: 0", L2), *crow("c3", "left: 80.00", L3, GREY_B)], 0.8),
            "Pause and think",
            (lambda: self.cap("can they refund too much?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. Each reads the same amount left and writes a different row. That's write skew again: two cakes, two flatmates, one empty fridge.", [
            (lambda: [*self.uncap(), *self.put("a1", line(AX, L1, "sees 80.00 left", WHITE)), *self.put("b1", line(BX, L1, "sees 80.00 left", WHITE))], 0.6),
            "writes a different row",
            (lambda: [*self.put("a2", line(AX, L2, "new refund row", A_C)), *self.put("b2", line(BX, L2, "new refund row", B_C))], 0.6),
            "write skew again",
            (lambda: self.cap("write skew again: each reads the rule, each writes its own row", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.wait(2.0)
