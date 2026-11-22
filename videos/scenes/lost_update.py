from sfz import *

# Amounts are said the way people say them ("fifty"); captions keep "50.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bSELECT FOR UPDATE\b", "select for update"))
SAY.insert(0, (r"\bredo\b", "ree-doo"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ROW_C = np.array([0, 2.5, 0])              # account 109: the row (and, in the story, the whiteboard)
ROW_W, ROW_H = 5.0, 1.1
LOCK_C = ROW_C + [ROW_W / 2 + 0.55, 0, 0]  # where the row lock sits
AX, BX = -3.7, 3.7                         # the two lanes: the card payment, the monthly fee
LANE_Y = 1.4
SLOT = [0.7, 0.1, -0.5, -1.1, -1.7, -2.3]  # time slots, top to bottom
CAP_Y, BAR_Y = -3.25, -2.85


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def row_box():
    r = RoundedRectangle(corner_radius=0.14, width=ROW_W, height=ROW_H, stroke_color=WHITE, stroke_width=3).set_fill("#101010", 1)
    r.move_to(ROW_C)
    t = T("accounts: row 109, Ivy", 20, GREY_B).move_to(ROW_C + [0, 0.27, 0])
    k = M("balance_minor", 20, GREY_B).move_to(ROW_C + [-1.0, -0.2, 0])
    return VGroup(r, t, k)


def row_val(s, color=WHITE):
    return M(s, 30, color).move_to(ROW_C + [1.25, -0.2, 0]).set_z_index(3)


def padlock(color):
    body = RoundedRectangle(corner_radius=0.06, width=0.46, height=0.36, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.5), 1)
    shackle = Arc(radius=0.15, start_angle=0, angle=PI, stroke_color=color, stroke_width=4)
    shackle.next_to(body, UP, buff=0)
    legs = VGroup(Line(shackle.get_start(), shackle.get_start() + 0.04 * DOWN), Line(shackle.get_end(), shackle.get_end() + 0.04 * DOWN)).set_stroke(color, 4)
    return VGroup(shackle, legs, body).move_to(LOCK_C)


def lane_title(s, x, color):
    return T(s, 24, color).move_to([x, LANE_Y, 0])


def step(s, x, k, color=GREY_B, size=20):
    t = M(s, size)
    r = RoundedRectangle(corner_radius=0.08, width=max(3.6, t.width + 0.4), height=0.46, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.18), 1)
    return VGroup(r, t.move_to(r)).move_to([x, SLOT[k], 0])


def person(color):
    head = Circle(radius=0.2, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.4), 1)
    body = Arc(radius=0.36, start_angle=0, angle=PI, stroke_color=color, stroke_width=3)
    body.next_to(head, DOWN, buff=0.06)
    base = Line(body.get_start(), body.get_end(), stroke_width=3, color=color)
    return VGroup(head, body, base)


def whiteboard():
    r = RoundedRectangle(corner_radius=0.08, width=3.4, height=ROW_H, stroke_color=GREY_A, stroke_width=4).set_fill("#f2f2f2", 1)
    r.move_to(ROW_C)
    t = T("grocery card", 20, "#333333").move_to(ROW_C + [0, 0.27, 0])
    return VGroup(r, t)


def wb_val(s, color="#1a1a1a"):
    return T(s, 34, color, slant=ITALIC).move_to(ROW_C + [0, -0.18, 0]).set_z_index(3)


def marker():
    body = RoundedRectangle(corner_radius=0.05, width=0.95, height=0.22, stroke_width=0).set_fill(GREY_A, 1)
    cap = RoundedRectangle(corner_radius=0.05, width=0.3, height=0.24, stroke_width=0).set_fill(BLUE_D, 1)
    cap.move_to(body.get_left() + [0.15, 0, 0])
    tip = Polygon([0, 0.08, 0], [0.18, 0, 0], [0, -0.08, 0], stroke_width=0).set_fill(GREY_D, 1)
    tip.next_to(body, RIGHT, buff=0)
    return VGroup(body, cap, tip).rotate(-PI / 5)


def thought(s, x, y, color):
    t = T(s, 24, color)
    r = RoundedRectangle(corner_radius=0.25, width=t.width + 0.5, height=0.6, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).move_to([x, y, 0])


def panel(x, title, lines, color):
    g = VGroup(T(title, 24, color), *[fit(M(s, 18), 5.2) if mono else T(s, 20, GREY_B) for s, mono in lines]).arrange(DOWN, buff=0.22)
    r = RoundedRectangle(corner_radius=0.14, width=5.8, height=g.height + 0.6, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.12), 1)
    return VGroup(r, g.move_to(r)).move_to([x, -0.6, 0])


class LostUpdate(Base):
    """txn-02, section 0. Ivy's account (5,000 cents) takes two charges of 1,000 in one second and ends at 4,000. Both
    read 5,000 and work out 4,000 in Kotlin; the row lock makes the fee's UPDATE wait for the payment's commit, and it
    still writes its old 4,000: a lost update. The fridge whiteboard and its one marker (row and row lock). The fix
    from section 1: subtract inside the UPDATE, so the waiting write rereads 4,000 and ends at 3,000; then FOR UPDATE
    and compare-and-set for logic SQL can't write. Moral and a check (a like counter)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_rv(self, s, color=WHITE):
        new = row_val(s, color)
        old, self.rv = self.rv, new
        return [swap(old, new)]

    def _drop_rv(self):
        old, self.rv = self.rv, None
        return old

    def lock(self, color):
        """Put the row lock on (in the holder's colour), move it to another holder, or (None) take it off."""
        old = self.lk
        if color is None:
            self.lk = None
            return [FadeOut(old, scale=0.6)] if old is not None else []
        new = padlock(color)
        self.lk = new
        if old is None:
            return [FadeIn(new, scale=0.6)]
        return [Succession(FadeOut(old, scale=0.6), FadeIn(new, scale=0.6))]

    def add_step(self, key, *args, **kw):
        m = step(*args, **kw)
        self.st[key] = m
        return [FadeIn(m, shift=0.1 * DOWN)]

    def clear_steps(self):
        olds = list(self.st.values())
        self.st = {}
        return [FadeOut(m) for m in olds]

    def construct(self):
        self.capm = self.rv = self.lk = None
        self.st = {}
        self.title_card("Where did ten dollars go?", "two charges, one row, and a lost update")

        # ---------------- scene 1: the question ----------------
        acct = RoundedRectangle(corner_radius=0.18, width=4.6, height=2.2, stroke_color=WHITE, stroke_width=3).set_fill("#101010", 1)
        acct.move_to([0, 0.9, 0])
        acct_t = T("Ivy's spending account", 24, GREY_B).move_to(acct.get_center() + [0, 0.6, 0])
        bal = M("50.00", 54).move_to(acct.get_center() + [0, -0.2, 0])
        c1 = chip("coffee  -10.00", GOLD_M, 24).move_to([-4.4, 1.5, 0])
        c2 = chip("monthly fee  -10.00", GOLD_M, 24).move_to([-4.4, 0.3, 0])
        should = VGroup(T("should show", 22, GREY_B), M("30.00", 36, GREEN_M)).arrange(DOWN, buff=0.15).move_to([4.5, 1.5, 0])
        shows = VGroup(T("shows", 22, GREY_B), M("40.00", 36, RED_M)).arrange(DOWN, buff=0.15).move_to([4.5, 0.1, 0])
        self.steps("Picture the company behind a coffee-shop payments app, checking its numbers at the month's end.", [
            "checking its",
            (lambda: [FadeIn(VGroup(acct, acct_t), shift=0.2 * UP)], 0.8),
        ])
        self.steps("Ivy's spending account started the month at 50.00. On the first morning, in one second, two charges came in: "
                   "10.00 for a coffee, and a 10.00 monthly fee.", [
            "started the month",
            (lambda: [FadeIn(bal)], 0.6),
            "two charges",
            (lambda: [FadeIn(c1, shift=0.2 * RIGHT)], 0.6),
            "and a 10.00",
            (lambda: [FadeIn(c2, shift=0.2 * RIGHT)], 0.6),
        ])
        self.steps("It should show 30.00. It shows 40.00.", [
            (lambda: [FadeIn(should, shift=0.2 * LEFT)], 0.6),
            "It shows",
            (lambda: [FadeIn(shows, shift=0.2 * LEFT), Transform(bal, M("40.00", 54, RED_M).move_to(bal))], 0.7),
        ])
        log = VGroup(T("payments list:  coffee, monthly fee", 22, GREY_B), T("both programs:  success.   errors:  none", 22, GREY_B))
        log.arrange(DOWN, buff=0.2).move_to([0, -1.55, 0])
        qm = T("where did 10.00 go?", 30, YELLOW_M).move_to([0, -2.85, 0])
        self.steps("Both charges are in the list of payments. Both programs said success. No error anywhere. "
                   "So where did ten dollars go?", [
            (lambda: [FadeIn(log[0])], 0.6),
            "Both programs",
            (lambda: [FadeIn(log[1])], 0.6),
            "So where",
            (lambda: [FadeIn(qm, scale=0.8)], 0.6),
        ])

        # ---------------- scene 2: the code we've all written ----------------
        row = row_box()
        self.rv = bal
        self.steps("Let's put it in the database. The company keeps its data in PostgreSQL, a free database program, in tables made of rows. "
                   "Ivy's account is row 109, and it keeps the balance in cents. So 50.00 is 5,000.", [
            (lambda: [FadeOut(VGroup(c1, c2, should, shows, log, qm, acct_t)), Transform(bal, row_val("40.00", RED_M)),
                      Transform(acct, row[0])], 1.0),
            "Ivy's account",
            (lambda: [FadeIn(row[1:])], 0.6),
            "So 50.00",
            (lambda: self.set_rv("5,000"), 0.5),
        ])
        self.remove(acct)
        self.add(row)

        code = VGroup(M("val balance = selectBalance(109)        // 5000", 22),
                      M("updateBalance(109, balance - 1000)      // 4000", 22)).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        code_box = RoundedRectangle(corner_radius=0.12, width=code.width + 0.7, height=code.height + 0.6, stroke_color=GREY_B,
                                    stroke_width=2).set_fill("#0c0c0c", 1)
        code_g = VGroup(code_box, code.move_to(code_box)).move_to([0, 0.1, 0])
        code_t = T("each charge, in Kotlin", 20, GREY_B).next_to(code_g, UP, buff=0.18)
        three = VGroup(*[chip(s, c, 22) for s, c in (("1. read", BLUE_M), ("2. subtract in the program", GOLD_M), ("3. write", BLUE_M))])
        three.arrange(RIGHT, buff=0.35).move_to([0, -1.55, 0])
        self.steps("Each charge runs in a transaction, a group of statements the database applies together or not at all. "
                   "And each does three things we've all written: read the balance, subtract in its own Kotlin code, and write the result back.", [
            "we've all written",
            (lambda: [FadeIn(VGroup(code_box, code_t)), FadeIn(code[0])], 0.6),
            "read the balance",
            (lambda: [FadeIn(three[0], shift=0.1 * UP)], 0.4),
            "subtract in",
            (lambda: [FadeIn(three[1], shift=0.1 * UP), FadeIn(code[1])], 0.4),
            "and write",
            (lambda: [FadeIn(three[2], shift=0.1 * UP)], 0.4),
        ])
        self.steps("Run them one after the other, and the balance goes 5,000, 4,000, 3,000. So far so good.", [
            (lambda: [FadeOut(VGroup(code_g, code_t, three))], 0.5),
            "4,000",
            (lambda: self.set_rv("4,000"), 0.4),
            "3,000",
            (lambda: self.set_rv("3,000", GREEN_M), 0.4),
            "So far",
            (lambda: [glow(row[0], GREEN_M, 1.02)], 0.7),
        ])

        # ---------------- scene 3: the lock, and the prediction ----------------
        ta = lane_title("the card payment: -1,000", AX, BLUE_M)
        tb = lane_title("the monthly fee: -1,000", BX, PURPLE_M)
        tarrow = Arrow([0, 1.0, 0], [0, -2.55, 0], buff=0, stroke_width=2.5, color=GREY_D, max_tip_length_to_length_ratio=0.04)
        tlab = T("time", 18, GREY_C).move_to([0.42, 0.85, 0])
        self.steps("Now, you might be thinking: the database won't let two writes on one row clash. And you'd be half right.", [
            (lambda: self.set_rv("5,000"), 0.5),
            "two writes",
            (lambda: [FadeIn(ta, shift=0.1 * RIGHT), FadeIn(tb, shift=0.1 * LEFT)], 0.7),
            "half right",
            (lambda: [Create(tarrow), FadeIn(tlab)], 0.6),
        ])
        self.steps("When a transaction updates a row, PostgreSQL puts a row lock on it, a mark that makes any other writer of that row "
                   "wait until this transaction commits.", [
            "a row lock",
            (lambda: self.lock(GREY_B), 0.5),
            (lambda: [*self.cap("row lock: other writers of this row wait until the holder commits")], 0.5),
            "wait until",
            (lambda: self.lock(None), 0.4),
        ])
        self.steps("So let the two overlap. The payment reads 5,000 and works out 4,000. The fee reads 5,000 too, and works out 4,000.", [
            (lambda: self.uncap(), 0.3),
            "The payment reads",
            (lambda: self.add_step("a0", "read 5,000, work out 4,000", AX, 0, BLUE_M), 0.6),
            "The fee reads",
            (lambda: self.add_step("b1", "read 5,000, work out 4,000", BX, 1, PURPLE_M), 0.6),
        ])
        self.steps("The payment writes 4,000 and takes the lock. The fee tries to write, and waits. Good, it's taking turns.", [
            (lambda: self.add_step("a2", "UPDATE balance = 4,000", AX, 2, BLUE_M), 0.5),
            (lambda: [*self.set_rv("4,000"), *self.lock(BLUE_M)], 0.5),
            "The fee tries",
            (lambda: self.add_step("b3", "UPDATE balance = 4,000", BX, 3, YELLOW_M), 0.5),
            "and waits",
            (lambda: self.cap("the fee waits for the payment's lock", YELLOW_M), 0.5),
            "taking turns",
            (lambda: [glow(self.st["b3"][0], YELLOW_M, 1.04)], 0.7),
        ])
        self.steps("The payment commits, which makes its change permanent, and lets go of the lock. "
                   "What does the fee write now? Pause and guess.", [
            (lambda: self.add_step("a4", "COMMIT", AX, 4, BLUE_M), 0.5),
            "lets go",
            (lambda: [*self.lock(None), *self.uncap()], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("4,000. The number it worked out before it waited. Two charges ran, and the balance went down by one.", [
            (lambda: [*self.uncap(), *self.lock(PURPLE_M), self.st["b3"][0].animate.set_stroke(PURPLE_M)], 0.4),
            (lambda: self.add_step("b5", "writes 4,000, COMMIT", BX, 5, PURPLE_M), 0.5),
            (lambda: [*self.set_rv("4,000", RED_M), *self.lock(None)], 0.5),
            "The number it worked",
            (lambda: [glow(self.st["b1"][0], RED_M, 1.04)], 0.8),
            "Two charges ran",
            (lambda: self.cap("two charges, and the balance fell by 1,000", RED_M), 0.5),
        ])
        self.steps("Well... the lock did its job. It just wasn't the job we needed.", [
            0.4,
            (lambda: [glow(self.st["a2"][0], BLUE_M, 1.03), glow(self.st["b3"][0], PURPLE_M, 1.03)], 0.8),
        ], after=0.5)

        # ---------------- scene 4: the fridge whiteboard ----------------
        wb = whiteboard()
        self.wv = wb_val("50")
        mk = marker().move_to(LOCK_C + [0.2, 0, 0])
        p1 = person(BLUE_M).move_to([AX, 0.25, 0])
        p2 = person(PURPLE_M).move_to([BX, 0.25, 0])
        n1 = T("flatmate 1", 22, BLUE_M).move_to([AX, LANE_Y, 0])
        n2 = T("flatmate 2", 22, PURPLE_M).move_to([BX, LANE_Y, 0])
        self.steps("Let's leave computers for a minute. Two flatmates share a grocery card, and its balance is on the whiteboard "
                   "on the fridge: 50.", [
            (lambda: [*self.uncap(), *self.clear_steps(), FadeOut(VGroup(tarrow, tlab))], 0.6),
            "Two flatmates",
            (lambda: [FadeOut(VGroup(row, self._drop_rv())), FadeIn(wb), FadeIn(self.wv),
                      Transform(ta, n1), Transform(tb, n2), FadeIn(p1), FadeIn(p2)], 0.9),
            "on the fridge",
            (lambda: [glow(wb[0], GREY_B, 1.03)], 0.6),
        ])
        th1 = thought("50 - 10 = 40", AX, -1.05, BLUE_M)
        th2 = thought("50 - 10 = 40", BX, -1.05, PURPLE_M)
        self.steps("In the morning, both glance at it. Each spends 10, works out 40 in their head, and comes home to write it down.", [
            "both glance",
            (lambda: [p1.animate.shift(0.15 * UP), p2.animate.shift(0.15 * UP)], 0.5),
            "works out 40",
            (lambda: [FadeIn(th1, scale=0.8), FadeIn(th2, scale=0.8)], 0.7),
        ])
        hold1 = [AX + 1.25, 0.45, 0]
        hold2 = [BX - 1.25, 0.45, 0]
        self.steps("There's only one marker. So the second flatmate waits politely while the first writes 40. "
                   "Then she takes the marker, and writes... 40.", [
            "one marker",
            (lambda: [FadeIn(mk, scale=0.6)], 0.5),
            "while the first",
            (lambda: [mk.animate.move_to(hold1), *self.cap("flatmate 2 waits for the marker", YELLOW_M)], 0.6),
            (lambda: [Transform(self.wv, wb_val("40"))], 0.5),
            "Then she takes",
            (lambda: [mk.animate.move_to(hold2), *self.uncap()], 0.6),
            "writes...",
            1.0,
            (lambda: [Transform(self.wv, wb_val("40", "#c0392b"))], 0.5),
        ])
        self.steps("Waiting her turn didn't help, because she brought an answer from the morning.", [
            "an answer from",
            (lambda: [glow(th2[0], RED_M, 1.05)], 0.8),
        ])
        k_row = row_box()
        self.steps("Map it back. The whiteboard is row 109. The marker is the row lock. The glance is the read, "
                   "and the sum in her head is the Kotlin code.", [
            "The whiteboard is",
            (lambda: [FadeOut(VGroup(wb, self.wv)), FadeIn(k_row), *self.set_rv("4,000", RED_M)], 0.7),
            "The marker is",
            (lambda: [Transform(mk, padlock(PURPLE_M))], 0.6),
            "The glance",
            (lambda: [Transform(p1, step("read 5,000", AX, 1, BLUE_M)), Transform(p2, step("read 5,000", BX, 1, PURPLE_M)),
                      Transform(ta, lane_title("the card payment: -1,000", AX, BLUE_M)),
                      Transform(tb, lane_title("the monthly fee: -1,000", BX, PURPLE_M))], 0.7),
            "the sum in",
            (lambda: [Transform(th1, step("Kotlin: 5,000 - 1,000", AX, 2, BLUE_M)), Transform(th2, step("Kotlin: 5,000 - 1,000", BX, 2, PURPLE_M))], 0.7),
        ])
        # swap what the mapping morphed for clean copies, so later pulses hit the right parts
        fresh = {"r1": step("read 5,000", AX, 1, BLUE_M), "r2": step("read 5,000", BX, 1, PURPLE_M),
                 "k1": step("Kotlin: 5,000 - 1,000", AX, 2, BLUE_M), "k2": step("Kotlin: 5,000 - 1,000", BX, 2, PURPLE_M)}
        for old_m, key in ((p1, "r1"), (p2, "r2"), (th1, "k1"), (th2, "k2")):
            self.remove(old_m)
            self.add(fresh[key])
        self.st = fresh
        self.remove(mk)
        self.lk = padlock(PURPLE_M)
        self.add(self.lk)
        row = k_row
        self.steps("The lock put the two writes in order. It couldn't fix a number worked out from an old read.", [
            "in order",
            (lambda: [glow(self.lk[2], PURPLE_M, 1.1)], 0.7),
            "an old read",
            (lambda: [glow(self.st["r2"][0], RED_M, 1.04), glow(self.st["k2"][0], RED_M, 1.04)], 0.8),
        ])

        # ---------------- scene 5: the name ----------------
        self.steps("This has a name: a lost update. Two transactions read the same value, each writes a result worked out from it, "
                   "and the second write erases the first. Nothing failed, so no log line tells you.", [
            (lambda: [*self.lock(None), *self.cap("lost update: the second write erases the first", RED_M, 28)], 0.6),
            "each writes",
            (lambda: [*self.add_step("w1", "writes 4,000", AX, 3, BLUE_M), *self.add_step("w2", "writes 4,000", BX, 3, PURPLE_M)], 0.6),
            "the second write",
            (lambda: [glow(row[0], RED_M, 1.02)], 0.8),
            "Nothing failed",
            (lambda: [*self.add_step("c1", "COMMIT: ok", AX, 4, BLUE_M), *self.add_step("c2", "COMMIT: ok", BX, 4, PURPLE_M)], 0.6),
        ])
        hides = VGroup(*[chip(s, GOLD_M, 22) for s in ("a counter of likes", "load a document, save it all back",
                                                       "read the next job, mark it taken")])
        hides.arrange(DOWN, buff=0.28).move_to([0, -0.4, 0])
        self.steps("The shape behind it is called a read-modify-write cycle: read a value, change it in the program, write it back. "
                   "It hides in a counter of likes, in a program that loads a whole document and saves it back, "
                   "and in a worker that reads which job is next and then marks it taken.", [
            (lambda: self.cap("read-modify-write: read, change it in the program, write it back", GOLD_M, 26), 0.6),
            "It hides",
            (lambda: [*self.clear_steps(), *self.set_rv("5,000")], 0.5),
            "a counter of likes",
            (lambda: [FadeIn(hides[0], shift=0.1 * UP)], 0.4),
            "loads a whole",
            (lambda: [FadeIn(hides[1], shift=0.1 * UP)], 0.4),
            "a worker",
            (lambda: [FadeIn(hides[2], shift=0.1 * UP)], 0.4),
        ])

        # ---------------- scene 6: the fix ----------------
        wb2 = VGroup(T("bring an instruction, not a number:", 24, GREY_B), T("“take 10 off”", 34, GOLD_M)).arrange(DOWN, buff=0.2)
        wb2.move_to([0, -0.3, 0])
        self.steps("So how do the flatmates fix it? Don't bring a number home. Bring an instruction: take 10 off. "
                   "Whoever holds the marker reads the board right then, and subtracts.", [
            (lambda: [FadeOut(hides), *self.uncap()], 0.5),
            "Bring an instruction",
            (lambda: [FadeIn(wb2, shift=0.1 * UP)], 0.6),
            "Whoever holds",
            (lambda: self.lock(GREY_B), 0.5),
            "and subtracts",
            (lambda: [glow(row[0], GOLD_M, 1.02), *self.lock(None)], 0.7),
        ])
        sql = M("UPDATE accounts SET balance_minor = balance_minor - 1000 WHERE account_id = 109", 19, WHITE)
        sql_b = RoundedRectangle(corner_radius=0.1, width=sql.width + 0.5, height=0.62, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.12), 1)
        sql_g = VGroup(sql_b, sql.move_to(sql_b)).move_to([0, -0.3, 0])
        self.steps("In SQL, that's one statement: set the balance to the balance minus 1,000. "
                   "The read and the write happen in one step, inside the database.", [
            (lambda: [FadeOut(wb2), FadeIn(sql_g)], 0.6),
            "in one step",
            (lambda: [glow(sql_b, GOLD_M, 1.02)], 0.8),
        ])
        self.steps("Same race. The payment's update takes the lock. The fee's update waits. The payment commits. "
                   "Now what does the balance end at? Pause and guess.", [
            (lambda: [FadeOut(sql_g)], 0.3),
            (lambda: [Create(tarrow), FadeIn(tlab)], 0.4),
            "The payment's update",
            (lambda: [*self.add_step("f0", "SET balance = balance - 1,000", AX, 0, BLUE_M)], 0.5),
            (lambda: [*self.set_rv("4,000"), *self.lock(BLUE_M)], 0.4),
            "The fee's update",
            (lambda: [*self.add_step("f1", "SET balance = balance - 1,000", BX, 1, YELLOW_M)], 0.5),
            "The payment commits",
            (lambda: [*self.add_step("f2", "COMMIT", AX, 2, BLUE_M), *self.lock(None)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("3,000. When the lock went, PostgreSQL read row 109 again, as the payment left it, and subtracted from 4,000. "
                   "Both charges are there, and nobody had to try again.", [
            (lambda: [*self.uncap(), *self.lock(PURPLE_M), self.st["f1"][0].animate.set_stroke(PURPLE_M)], 0.4),
            (lambda: self.add_step("f3", "rereads 4,000, writes 3,000", BX, 3, PURPLE_M), 0.5),
            (lambda: self.set_rv("3,000", GREEN_M), 0.5),
            "Both charges",
            (lambda: [*self.add_step("f4", "COMMIT", BX, 4, PURPLE_M), *self.lock(None), glow(row[0], GREEN_M, 1.02),
                      *self.cap("both charges: 5,000 - 1,000 - 1,000 = 3,000", GREEN_M)], 0.7),
        ])

        # ---------------- scene 7: two more fixes ----------------
        pa = panel(-3.2, "lock when you read", [("SELECT balance_minor ... FOR UPDATE", True), ("take the marker before you look", False),
                                               ("the fee's read waits, then sees 4,000", False)], BLUE_M)
        pb = panel(3.2, "compare and set", [("UPDATE ... WHERE balance_minor = 5000", True), ("write only if it still says 5,000", False),
                                            ("0 rows changed: read again, try again", False)], PURPLE_M)
        self.steps("Sometimes the new value needs logic SQL can't write, like a fraud score from another program. Then there are two more fixes.", [
            (lambda: [*self.clear_steps(), *self.uncap(), FadeOut(VGroup(tarrow, tlab, ta, tb)), *self.set_rv("5,000")], 0.6),
            "two more fixes",
            (lambda: self.cap("when SQL can't do the arithmetic", GREY_B), 0.5),
        ])
        self.steps("Lock when you read: SELECT FOR UPDATE takes the marker before you look. The fee's read waits for the payment, then sees 4,000.", [
            (lambda: [FadeIn(pa[0]), FadeIn(pa[1][0])], 0.5),
            "SELECT FOR UPDATE",
            (lambda: [FadeIn(pa[1][1]), *self.lock(BLUE_M)], 0.5),
            "takes the marker",
            (lambda: [FadeIn(pa[1][2])], 0.4),
            "The fee's read",
            (lambda: [FadeIn(pa[1][3]), *self.set_rv("4,000")], 0.5),
        ])
        self.steps("Or compare and set: write 4,000 only if the balance is still 5,000. If someone got there first, the update changes no rows, "
                   "and the program reads again and tries again.", [
            (lambda: [*self.lock(None), *self.set_rv("5,000"), FadeIn(pb[0]), FadeIn(pb[1][0])], 0.5),
            "write 4,000",
            (lambda: [FadeIn(pb[1][1])], 0.5),
            "only if",
            (lambda: [FadeIn(pb[1][2])], 0.4),
            "If someone",
            (lambda: [FadeIn(pb[1][3])], 0.5),
        ])
        self.steps("A rule of thumb: lock rows that many transactions want at once. Compare and set on rows that are rarely shared.", [
            (lambda: [*self.cap("busy row: lock it.   rarely shared row: compare and set.", WHITE)], 0.6),
            "lock rows",
            (lambda: [glow(pa[0], BLUE_M, 1.02)], 0.7),
            "Compare and set",
            (lambda: [glow(pb[0], PURPLE_M, 1.02)], 0.7),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, where did the ten dollars go? The fee wrote a number it worked out before it waited. "
                   "The lock puts writes in line. It doesn't redo your sums.", [
            (lambda: [FadeOut(VGroup(pa, pb)), *self.cap("where did 10.00 go?", WHITE)], 0.6),
            "The fee wrote",
            (lambda: [*self.set_rv("4,000", RED_M)], 0.5),
            "The lock puts",
            (lambda: [*self.lock(GREY_B), *self.cap("a lock puts writes in line. It doesn't redo your sums.", YELLOW_M, 28)], 0.6),
        ])
        self.steps("Let the database do the arithmetic, or make it check yours.", [
            (lambda: [*self.lock(None), *self.set_rv("3,000", GREEN_M), *self.cap("let the database do the arithmetic, or make it check yours", YELLOW_M, 28)], 0.7),
        ], after=0.6)
        post = VGroup(T("a post", 22, GREY_B), M("41 likes", 36)).arrange(DOWN, buff=0.15).move_to([0, 0.15, 0])
        post_b = RoundedRectangle(corner_radius=0.14, width=3.2, height=1.5, stroke_color=WHITE, stroke_width=3).set_fill("#101010", 1).move_to(post)
        lk1 = step("read 41, write 42", AX, 4, BLUE_M)
        lk2 = step("read 41, write 42", BX, 4, PURPLE_M)
        self.steps("One quick check. A post has 41 likes. Two people tap like at once, and each program reads 41, adds one in code, "
                   "and writes 42. What does the post show? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(VGroup(post_b, post))], 0.6),
            "Two people",
            (lambda: [FadeIn(lk1, shift=0.1 * UP), FadeIn(lk2, shift=0.1 * UP)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("42. One like is lost. Set likes to likes plus one, and it shows 43.", [
            (lambda: [*self.uncap(), Transform(post[1], M("42 likes", 36, RED_M).move_to(post[1]))], 0.6),
            "Set likes",
            (lambda: [*self.cap("SET likes = likes + 1", GOLD_M, 28), Transform(lk1, step("SET likes = likes + 1", AX, 4, BLUE_M)),
                      Transform(lk2, step("SET likes = likes + 1", BX, 4, PURPLE_M))], 0.7),
            "it shows 43",
            (lambda: [Transform(post[1], M("43 likes", 36, GREEN_M).move_to(post[1]))], 0.6),
        ], after=0.3)
        self.play(*self.cap("a lock puts writes in line. It doesn't redo your sums.", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
