from sfz import *

# Amounts are said the way people say them ("twenty"); captions keep "20.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bpay-(\d+)\b", r"pay \1"))
SAY.insert(0, (r"\bacct-(\d+)\b", r"account \1"))
SAY.insert(0, (r"\bv(\d)\b", r"version \1"))
SAY.insert(0, (r"\bUPDATE\b", "update"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TB_C, TB_W, TB_H = np.array([-4.75, 2.45, 0]), 3.3, 1.3          # the accounts table
LG_C, LG_W, LG_H = np.array([-1.7, -0.45, 0]), 9.4, 4.0          # the log: account acct-17's stream
ROW_Y = [0.75 - 0.52 * k for k in range(6)]
FD_C, FD_W, FD_H = np.array([5.0, -0.45, 0]), 2.6, 2.4           # the fold: the balance worked out
CM_C = np.array([5.0, 2.35, 0])                                  # where a command card sits
CAP_Y, TOP_Y, BAR_Y = -3.3, 3.3, -2.72
EVENTS = [("v1", "AccountOpened ", "owner=Mira Okafor", GREY_B),
          ("v2", "MoneyDeposited", "+100.00  salary-0301", GREEN_M),
          ("v3", "MoneyWithdrawn", "-30.00   card pay-981", GOLD_M),
          ("v4", "MoneyWithdrawn", "-45.00   card pay-982", GOLD_M),
          ("v5", "MoneyDeposited", "+45.00   refund of pay-982", GREEN_M),
          ("v6", "MoneyWithdrawn", "-50.00   transfer tx-77", GOLD_M)]
BAL = ["0.00", "100.00", "70.00", "25.00", "70.00", "20.00"]


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def top(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, TOP_Y, 0])
        old, self.topm = self.topm, new
        return [swap(old, new)]

    def untop(self):
        old, self.topm = self.topm, None
        return [FadeOut(old)] if old is not None else []


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])




def rbox(c, w, h, color, fill=True):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    return r.set_fill(fillc(color) if fill else BLACK, 1).move_to(c)


def ev_row(k):
    v, kind, rest, col = EVENTS[k]
    x0 = LG_C[0] - LG_W / 2 + 0.3
    y = ROW_Y[k]
    amt, ref = rest.split(None, 1) if rest[0] in "+-" else ("", rest)
    g = VGroup(left_at(M(v, 20, GREY_B), x0, y), left_at(M(kind.strip(), 20, WHITE), x0 + 0.6, y))
    if amt:
        g.add(M(amt, 20, col).move_to([x0 + 4.6 - M(amt, 20).width / 2, y, 0]))
    g.add(left_at(M(ref, 20, col), x0 + 5.0, y))
    return g


def cursor(k):
    return RoundedRectangle(corner_radius=0.08, width=LG_W - 0.3, height=0.46, stroke_color=YELLOW_M, stroke_width=4).move_to([LG_C[0], ROW_Y[k], 0])


def fold_num(s, color=WHITE):
    return M(s, 44, color).move_to(FD_C + [0, -0.3, 0])


def tb_num(s, color=WHITE):
    t = M(s, 30, color)
    return t.move_to([TB_C[0] + TB_W / 2 - 0.25 - t.width / 2, TB_C[1] - 0.25, 0])


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.5, height=4.8, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.15, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 2.2)
    rows = VGroup()
    cw = M("x" * 40, 16).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if "//" in s else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 16, col), x - 3.0 + ind, 1.65 - 0.34 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["long balance(List<Event> events) {",
        "    long b = 0;",
        "    for (Event e : events) {",
        "        b = switch (e) {",
        "            case Opened o -> 0;",
        "            case Deposited d -> b + d.cents();",
        "            case Withdrawn w -> b - w.cents();",
        "        };",
        "    }",
        "    return b;",
        "}"]
KOTLIN = ["fun balance(events: List<Event>): Long =",
          "    events.fold(0L) { b, e ->",
          "        when (e) {",
          "            is Opened -> 0",
          "            is Deposited -> b + e.cents",
          "            is Withdrawn -> b - e.cents",
          "        }",
          "    }"]


class EventSourcing(Base):
    """stream-03, section 0. "Why is my balance 20.00?" The accounts table holds one number. The bank app's list explains
    it. Every UPDATE overwrote the answer before it; a trigger-built history is a second truth. Event sourcing: account
    acct-17's stream v1 to v6, folded in order (0, 100, 70, 25, 70, 20). Predict the balance after v4. Questions the
    table can't answer (as of v5: 70.00; pay-982: v4, v5). The table as a cache. Command vs event (withdraw 80.00 is
    refused), corrections as new events. Versus CDC; a redesign, not a switch. The fold in Java and Kotlin, the moral,
    a check."""

    def construct(self):
        self.capm = self.topm = None
        self.title_card("Why is my balance 20.00?", "keep the list, work out the number: event sourcing")

        tb = rbox(TB_C, TB_W, TB_H, BLUE_M)
        tb_t = T("accounts table", 24).move_to(TB_C + [0, TB_H / 2 - 0.32, 0])
        tb_k = left_at(M("acct-17", 22, GREY_B), TB_C[0] - TB_W / 2 + 0.25, TB_C[1] - 0.25)
        lg = rbox(LG_C, LG_W, LG_H, GREY_B, fill=False)
        fd = rbox(FD_C, FD_W, FD_H, GREEN_M)
        self.tn = tb_num("20.00")
        self.fn = None
        self.lt = None
        self.ft = None
        rows = [ev_row(k) for k in range(6)]

        def set_tn(s, color=WHITE):
            new = tb_num(s, color)
            old, self.tn = self.tn, new
            return [swap(old, new)]

        def set_fn(s, color=WHITE):
            new = fold_num(s, color)
            old, self.fn = self.fn, new
            return [swap(old, new)]

        def set_lt(s, color=GREY_B):
            new = T(s, 22, color).move_to(LG_C + [0, LG_H / 2 - 0.33, 0])
            old, self.lt = self.lt, new
            return [swap(old, new)]

        def set_ft(s, color=GREY_B):
            new = T(s, 24, color).move_to(FD_C + [0, FD_H / 2 - 0.4, 0])
            old, self.ft = self.ft, new
            return [swap(old, new)]

        # ---------------- scene 1: the question ----------------
        self.steps("A customer calls the payments help line. Why is my balance 20.00? Support opens the accounts table: "
                   "one row for her account, acct-17, and one number, 20.00. That's all there is.", [
            "Why is my",
            (lambda: self.cap("“why is my balance 20.00?”", WHITE, 30), 0.6),
            "Support opens",
            (lambda: [FadeIn(tb), FadeIn(tb_t)], 0.7),
            "one row",
            (lambda: [FadeIn(tb_k), FadeIn(self.tn)], 0.6),
            "That's all",
            (lambda: [glow(tb, BLUE_M, 1.04)], 0.8),
        ])
        self.steps("Twenty. But why twenty? The table can't say.", [
            (lambda: [Indicate(self.tn, color=YELLOW_M, scale_factor=1.15)], 0.8),
        ], after=0.4)

        # ---------------- scene 2: the bank app ----------------
        self.steps("Now think of your own bank app. The balance sits at the top, and under it, a list. "
                   "Salary in, a coffee, a book, the book refunded, fifty to a friend.", [
            (lambda: self.uncap(), 0.3),
            "The balance sits",
            (lambda: [FadeIn(fd), *set_ft("balance"), *set_fn("20.00")], 0.7),
            "a list",
            (lambda: [FadeIn(lg), *set_lt("the list under it")], 0.6),
            "Salary in",
            (lambda: [FadeIn(rows[0]), FadeIn(rows[1])], 0.4),
            "a coffee",
            (lambda: [FadeIn(rows[2])], 0.4),
            "a book",
            (lambda: [FadeIn(rows[3])], 0.4),
            "the book refunded",
            (lambda: [FadeIn(rows[4])], 0.4),
            "fifty to",
            (lambda: [FadeIn(rows[5])], 0.4),
        ])
        self.steps("Read the list, and the number makes sense.", [
            (lambda: [LaggedStart(*[Indicate(r, color=YELLOW_M, scale_factor=1.03) for r in rows], lag_ratio=0.15)], 1.4),
        ], after=0.3)

        # ---------------- scene 3: the table overwrites ----------------
        diagram_app = VGroup(lg, fd, *rows)
        gone = []
        self.steps("So why can't the table say? Watch how it got to 20.00. Every change is an UPDATE, a command that changes a row, "
                   "and each one writes over the answer before it.", [
            (lambda: [diagram_app.animate.set_opacity(0.15), self.lt.animate.set_opacity(0.15), self.ft.animate.set_opacity(0.15),
                      self.fn.animate.set_opacity(0.15)], 0.6),
            "Every change",
            (lambda: [*set_tn("0.00"), *self.cap("UPDATE accounts SET balance = ...", WHITE)], 0.6),
        ])

        def overwrite(k):
            old = self.tn.copy()
            gone.append(old)
            return [old.animate.shift(0.75 * DOWN).set_opacity(0), *set_tn(BAL[k])]

        self.steps("100.00. 70.00. 25.00. 70.00. 20.00. Each old number is gone the moment the new one lands.", [
            "100.00",
            (lambda: overwrite(1), 0.5),
            "70.00. 25",
            (lambda: overwrite(2), 0.5),
            "25.00",
            (lambda: overwrite(3), 0.5),
            "70.00. 20",
            (lambda: overwrite(4), 0.5),
            "20.00. Each",
            (lambda: overwrite(5), 0.5),
            "Each old number",
            (lambda: self.cap("each UPDATE overwrites the answer before it", RED_M), 0.5),
        ])
        hist = rbox(TB_C + [4.6, 0, 0], TB_W, 1.2, GREY_B, fill=False)
        hist_t = T("history table", 22, GREY_B).move_to(hist.get_center() + [0, 0.25, 0])
        hist_n = T("a second truth?", 20, RED_M).move_to(hist.get_center() + [0, -0.2, 0])
        h_a = Arrow(TB_C + [TB_W / 2, 0, 0], hist.get_left(), buff=0.06, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.3)
        self.steps("You could bolt history back on, with a small program the database runs on every change, copying it into a second table. "
                   "But now there are two records of the truth, and when they disagree, which one wins?", [
            "You could bolt",
            (lambda: [*self.uncap(), GrowArrow(h_a), FadeIn(hist), FadeIn(hist_t)], 0.8),
            "two records",
            (lambda: [FadeIn(hist_n)], 0.5),
            "which one wins",
            (lambda: [glow(tb, RED_M, 1.04), glow(hist, RED_M, 1.04)], 0.9),
        ])
        self.steps("What we really want is the app's list as the truth itself.", [
            (lambda: [FadeOut(VGroup(hist, hist_t, hist_n, h_a)), diagram_app.animate.set_opacity(1), self.lt.animate.set_opacity(1)], 0.7),
        ], after=0.3)

        # ---------------- scene 4: the log ----------------
        self.steps("So turn it around. Store every change as an event, a record of one thing that happened, and never change it. "
                   "The events go into a log you only add to the end of, like a notebook you never rub out.", [
            "Store every change",
            (lambda: self.cap("an event: a record of one thing that happened", WHITE), 0.5),
            "into a log",
            (lambda: [*self.cap("append-only: add to the end, never change a line"), glow(lg, GREY_B, 1.02)], 0.8),
        ])
        self.steps("Here's account acct-17's own list, its stream, each event with a version number.", [
            "its stream",
            (lambda: set_lt("stream account-acct-17", WHITE), 0.6),
            "version number",
            (lambda: [LaggedStart(*[Indicate(r[0], color=YELLOW_M, scale_factor=1.3) for r in rows], lag_ratio=0.15)], 1.2),
        ])

        # ---------------- scene 5: fold, predict ----------------
        self.steps("Now the balance. Start from an empty account and apply each event in order, the way you'd add up a column "
                   "one line at a time. What's the balance after v4? Pause and guess.", [
            (lambda: [*self.uncap(), *set_ft("worked out"), *set_fn("?", GREY_B)], 0.6),
            "Start from",
            (lambda: [Create(self._cur(0))], 0.4),
            "What's the balance",
            (lambda: [*self.cap("balance after v4? pause and guess", YELLOW_M), self.cur.animate.move_to(cursor(3))], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("25.00. Zero, a hundred, seventy, twenty-five. Then the refund brings it back to seventy, and the transfer leaves twenty.", [
            (lambda: [*self.uncap(), self.cur.animate.move_to(cursor(0)), *set_fn("0.00")], 0.4),
            "Zero, a hundred",
            (lambda: [self.cur.animate.move_to(cursor(1)), *set_fn("100.00")], 0.4),
            "seventy, twenty",
            (lambda: [self.cur.animate.move_to(cursor(2)), *set_fn("70.00")], 0.4),
            "twenty-five. Then",
            (lambda: [self.cur.animate.move_to(cursor(3)), *set_fn("25.00", YELLOW_M)], 0.4),
            "the refund",
            (lambda: [self.cur.animate.move_to(cursor(4)), *set_fn("70.00")], 0.4),
            "the transfer",
            (lambda: [self.cur.animate.move_to(cursor(5)), *set_fn("20.00", GREEN_M)], 0.4),
        ])
        self.stamp("poster")
        self.steps("Adding up in order like that is called a fold. And the help line has its answer: a fifty transfer, "
                   "after a card payment and its refund.", [
            "called a fold",
            (lambda: [*set_ft("fold", GREEN_M), *self.cap("a fold: start empty, apply each event in order", WHITE)], 0.6),
            "a fifty transfer",
            (lambda: [Indicate(rows[5][2], color=GOLD_M, scale_factor=1.1)], 0.7),
            "a card payment",
            (lambda: [Indicate(rows[3][2], color=GOLD_M, scale_factor=1.1), Indicate(rows[4][2], color=GREEN_M, scale_factor=1.1)], 0.8),
        ])
        self.steps("And questions the table never could answer are easy. The balance before the transfer? Fold to v5: 70.00. "
                   "Everything that mentions pay-982? v4 and v5.", [
            "The balance before",
            (lambda: [*self.cap("as of v5?"), self.cur.animate.move_to(cursor(4)), *set_fn("70.00", YELLOW_M)], 0.6),
            "Everything that",
            (lambda: [*self.cap("mentions pay-982?"), FadeOut(self.cur), *set_fn("20.00", GREEN_M)], 0.5),
            "v4 and v5",
            (lambda: [Indicate(rows[3], color=YELLOW_M, scale_factor=1.04), Indicate(rows[4], color=YELLOW_M, scale_factor=1.04)], 0.9),
        ])

        # ---------------- scene 6: the name ----------------
        cache_l = left_at(T("a cache: where the log ends", 22, BLUE_M), TB_C[0] + TB_W / 2 + 0.3, TB_C[1])
        t_a = Arrow([TB_C[0], LG_C[1] + LG_H / 2, 0], [TB_C[0], TB_C[1] - TB_H / 2, 0], buff=0.06, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.35)
        self.steps("Keeping every change as an event, and working the state out from them, is called event sourcing.", [
            (lambda: self.uncap(), 0.3),
            "is called",
            (lambda: self.cap("event sourcing: the events are the truth; the state is worked out", WHITE, 26), 0.7),
        ])
        self.steps("The accounts table, if you keep one, is just a cache: a saved copy of where the log ends, that you can always work out again.", [
            "is just a cache",
            (lambda: [GrowArrow(t_a), FadeIn(cache_l)], 0.8),
            "work out again",
            (lambda: [glow(tb, BLUE_M, 1.04)], 0.8),
        ])
        self.steps("The table was never lying, by the way. It just had a very short memory.", [], after=0.4)

        # ---------------- scene 7: command vs event ----------------
        cmd = VGroup(rbox(CM_C, 3.0, 1.1, PURPLE_M), T("command", 22, PURPLE_M).move_to(CM_C + [0, 0.25, 0]),
                     M("withdraw 80.00", 20).move_to(CM_C + [0, -0.2, 0]))
        refused = T("refused: balance 20.00", 22, RED_M).move_to(CM_C + [0, -0.85, 0])
        self.steps("Two words need to stay apart. A command is a request, an order: withdraw 80.00 from acct-17. It can be refused. "
                   "Fold the log, the balance is 20.00, so this one is.", [
            (lambda: self.uncap(), 0.3),
            "A command is",
            (lambda: [FadeIn(cmd, shift=0.2 * RIGHT)], 0.7),
            "Fold the log",
            (lambda: [Indicate(self.fn, color=GREEN_M, scale_factor=1.15)], 0.7),
            "so this one is",
            (lambda: [FadeIn(refused), cmd[0].animate.set_stroke(RED_M)], 0.6),
        ])
        self.steps("An event is a fact, in the past tense: 80.00 was withdrawn. It already happened, so nothing later may refuse it. "
                   "Only a command that passes the rules becomes an event.", [
            "An event is",
            (lambda: self.cap("an event: a fact, in the past tense; nothing may refuse it", WHITE), 0.6),
            "Only a command",
            (lambda: self.cap("only a command that passes the rules becomes an event", YELLOW_M), 0.6),
        ])
        self.steps("And a mistake is never rubbed out. You add a correcting event, the way v5 refunds v4. "
                   "A bank books a reversal. It doesn't tear a page out of its ledger.", [
            (lambda: [FadeOut(cmd), FadeOut(refused), *self.uncap()], 0.5),
            "the way v5",
            (lambda: [Indicate(rows[3], color=GOLD_M, scale_factor=1.04)], 0.6),
            (lambda: [Indicate(rows[4], color=GREEN_M, scale_factor=1.04)], 0.6),
            "A bank books",
            (lambda: self.cap("correct with a new event; never edit an old one"), 0.5),
        ])

        # ---------------- scene 8: versus change data capture ----------------
        self.steps("Isn't this the change log from the first lesson? Change data capture reads row changes out of the database: "
                   "the balance went from 100.00 to 70.00. That's only what the number became.", [
            (lambda: self.uncap(), 0.3),
            "Change data capture",
            (lambda: self.cap("a row change: balance 100.00 -> 70.00", GREY_B, 26), 0.6),
        ])
        self.steps("The event says MoneyWithdrawn, card pay-981: what happened, and why. So event sourcing means redesigning the program "
                   "around events. You can't switch it on later.", [
            "The event says",
            (lambda: [Indicate(rows[2], color=GOLD_M, scale_factor=1.05)], 0.8),
            "So event sourcing",
            (lambda: self.cap("a redesign around events, not a setting you switch on", YELLOW_M), 0.6),
        ])
        self.steps("And the log only grows, so folding years of events gets slow. Snapshots, later in this lesson, keep it fast.", [
            "the log only grows",
            (lambda: [*self.cap("the log only grows: a long fold is slow, snapshots keep it fast"), glow(lg, GREY_B, 1.02)], 0.8),
        ])

        # ---------------- scene 9: the code, the moral, a check ----------------
        diag = VGroup(tb, tb_t, tb_k, self.tn, t_a, cache_l, lg, self.lt, *rows, fd, self.ft, self.fn)
        jp, kp = code_panel("Java", JAVA, -3.4), code_panel("Kotlin", KOTLIN, 3.4)

        def hl(p, rws, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for r in rws]

        self.steps("In Java and Kotlin the fold is a few lines. Start at zero, and for each event, add a deposit or take away a withdrawal.", [
            (lambda: [*self.uncap(), diag.animate.set_opacity(0.02)], 0.5),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.6),
            "Start at zero",
            (lambda: [*hl(jp, (1,), YELLOW_M), *hl(kp, (1,), YELLOW_M)], 0.9),
            "add a deposit",
            (lambda: [*hl(jp, (5, 6), GREEN_M), *hl(kp, (4, 5), GREEN_M)], 1.1),
        ], after=0.8)
        self.steps("So keep the list, and work the number out from it. A balance tells you what. The log tells you why.", [
            (lambda: [FadeOut(jp), FadeOut(kp), diag.animate.set_opacity(1)], 0.7),
            "A balance tells",
            (lambda: self.cap("a balance tells you what; the log tells you why", YELLOW_M, 30), 0.6),
        ], after=0.5)
        self.steps("One quick check. Support wants the balance as it was right after v3. Can the table tell them? Can the log? Pause and think.", [
            (lambda: [*self.uncap(), *set_fn("?", GREY_B)], 0.5),
            "right after v3",
            (lambda: [glow(rows[2], YELLOW_M, 1.03)], 0.6),
            "Pause and think",
            (lambda: self.cap("as of v3: table, or log? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The table can't. It only knows 20.00. The log can: fold to v3, and it's 70.00.", [
            (lambda: [*self.uncap(), Indicate(self.tn, color=RED_M, scale_factor=1.15)], 0.7),
            "The log can",
            (lambda: [Create(self._cur(0))], 0.3),
            (lambda: [self.cur.animate.move_to(cursor(1))], 0.3),
            (lambda: [self.cur.animate.move_to(cursor(2)), *set_fn("70.00", GREEN_M)], 0.4),
            "70.00",
            (lambda: self.cap("a balance tells you what; the log tells you why", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.play(Create(tick(True, 0.2).move_to(FD_C + [0, FD_H / 2 + 0.35, 0])), run_time=0.6)
        self.wait(2.0)

    def _cur(self, k):
        self.cur = cursor(k)
        return self.cur
