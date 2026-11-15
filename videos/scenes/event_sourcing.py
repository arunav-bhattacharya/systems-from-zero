from sfz import *

LX, LW, RH = -3.55, 6.0, 0.62                        # the log: centre x, row width, row height
ROW_Y = [2.55, 1.75, 0.95, 0.15, -0.65, -1.45]       # v1..v6
PX, PW = 4.05, 5.0                                   # projections: centre x, width
BAL_Y, STM_Y, FRD_Y = 2.3, 0.15, -2.0
BAL_H, STM_H, FRD_H = 1.4, 1.3, 1.4
FOLD_Y = -2.65
EVENTS = [("v1", "Opened", "", "Mira Okafor"),
          ("v2", "Deposited", "+100.00", "salary"),
          ("v3", "Withdrawn", "-30.00", "card pay-981"),
          ("v4", "Withdrawn", "-45.00", "card pay-982"),
          ("v5", "Deposited", "+45.00", "refund of pay-982"),
          ("v6", "Withdrawn", "-50.00", "transfer tx-77")]
RUNNING = ["0.00", "100.00", "70.00", "25.00", "70.00", "20.00"]


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


def fill(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    a, b = path.get_start(), path.get_end()
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def ev_row(i, color=GREY_B):
    v, kind, amt, ref = EVENTS[i]
    y = ROW_Y[i]
    r = RoundedRectangle(corner_radius=0.08, width=LW, height=RH, stroke_color=color, stroke_width=2.5)
    r.set_fill(fill(color), 1).move_to([LX, y, 0])
    return VGroup(r, left_at(M(v, 20, GREY_B), LX - LW / 2 + 0.18, y),
                  left_at(M(f"{kind:<10}{amt:>7}", 20), LX - LW / 2 + 0.66, y),
                  left_at(T(ref, 18, GREY_B), LX - LW / 2 + 4.0, y))


def pbox(y, h, color=WHITE):
    r = RoundedRectangle(corner_radius=0.12, width=PW, height=h, stroke_color=color, stroke_width=3)
    return r.set_fill(fill(color), 1).move_to([PX, y, 0])


def ptitle(s, y, h, color=GREY_B):
    return left_at(T(s, 20, color), PX - PW / 2, y + h / 2 + 0.24)


def bookmark(s, y, h, color=GREY_B):
    return right_at(M(s, 16, color), PX + PW / 2, y + h / 2 + 0.24)


class EventSourcing(Base):
    """stream-03, section 0 (with sections 1 and 2): acct-17's balance of 20.00 as one overwritten row, then as six events
    (opened, salary 100.00, card payments 30.00 and 45.00, a refund of 45.00, a transfer of 50.00) folded to 20.00.
    Two projections (balances, a statement: 145.00 in, 125.00 out) read the same log; months later a new fraud
    projection, withdrawals of 40.00 or more, is built by replaying from v1."""

    def construct(self):
        self.title_card("Event sourcing", "keep every change, and compute the state from it")

        # ---- the table that only knows the answer --------------------------------------------------------------
        TY, CX = 1.0, 2.0                       # table centre y; column half-width
        tab = pbox(TY, BAL_H)
        tab.move_to([0, TY, 0])
        tbody = VGroup(left_at(M("account", 20, GREY_B), -CX, TY + 0.28), right_at(M("balance", 20, GREY_B), CX, TY + 0.28),
                       left_at(M("acct-17", 26), -CX, TY - 0.22))
        tval = right_at(M("20.00", 26), CX, TY - 0.22)
        ttl = left_at(T("accounts table", 20, GREY_B), -PW / 2, TY + BAL_H / 2 + 0.24)
        ask = chip("help line: why is my balance 20.00?", GOLD_M, 24).move_to([0, -0.9, 0])
        self.steps("A customer calls the help line: why is my balance twenty euros? "
                   "The accounts table has one row, and it only says twenty euros.", [
            (lambda: [FadeIn(ask, shift=0.1 * UP)], 0.8),
            "The accounts table",
            (lambda: [FadeIn(tab), FadeIn(tbody), FadeIn(ttl), FadeIn(tval)], 0.9),
            "it only says",
            (lambda: [glow(tab, GOLD_M, 1.03)], 0.9),
        ])

        ghosts = []

        def overwrite(k):
            old = tval.copy()
            ghosts.append(old)
            new = right_at(M(RUNNING[k], 26, RED_M if k < 5 else WHITE), CX, TY - 0.22)
            return [old.animate.shift(0.45 * UP).set_opacity(0), Transform(tval, new)]

        lost = T("five updates, each one wrote over the last", 22, RED_M).move_to([0, -1.95, 0])
        self.steps("It got there through five updates, and each one wrote over the number before it. The reasons are gone.", [
            (lambda: [Transform(tval, right_at(M("0.00", 26, RED_M), CX, TY - 0.22))], 0.35),
            *[(lambda k=k: overwrite(k), 0.45) for k in range(1, 6)],
            "The reasons",
            (lambda: [FadeIn(lost, shift=0.1 * UP), ask[0].animate.set_stroke(RED_M), tab.animate.set_stroke(RED_M)], 0.8),
        ])
        for g in ghosts:
            self.remove(g)

        # ---- the log -------------------------------------------------------------------------------------------
        rows = [ev_row(i) for i in range(6)]
        ltl = left_at(T("stream account-acct-17", 20, GREY_B), LX - LW / 2, ROW_Y[0] + 0.62)
        d = np.array([PX, BAL_Y - TY, 0])

        def to_right():
            return [FadeOut(ask), FadeOut(lost),
                    tab.animate.shift(d).set_stroke(WHITE).set_opacity(0.35),
                    tbody.animate.shift(d).set_opacity(0.35), tval.animate.shift(d).set_opacity(0.35),
                    ttl.animate.shift(d).set_opacity(0.35)]

        self.steps("Event sourcing keeps the reasons. The service never overwrites a balance. "
                   "It appends every change to a log, as an event.", [
            (lambda: to_right(), 1.0),
            "It appends",
            (lambda: [FadeIn(ltl)], 0.5),
            (lambda: [FadeIn(rows[0], shift=0.15 * DOWN)], 0.6),
        ])

        self.steps("The account was opened. A salary of a hundred came in. Then two card payments took thirty and forty five. "
                   "The forty five came back as a refund, and a transfer took fifty.", [
            "A salary",
            (lambda: [FadeIn(rows[1], shift=0.15 * DOWN)], 0.5),
            "two card",
            (lambda: [FadeIn(rows[2], shift=0.15 * DOWN)], 0.5),
            (lambda: [FadeIn(rows[3], shift=0.15 * DOWN)], 0.5),
            "came back",
            (lambda: [FadeIn(rows[4], shift=0.15 * DOWN)], 0.5),
            "a transfer",
            (lambda: [FadeIn(rows[5], shift=0.15 * DOWN)], 0.5),
        ])

        ao = right_at(T("append only", 20, TEAL_M), LX + LW / 2, ROW_Y[0] + 0.62)
        self.steps("Each event is a fact in the past tense, and nobody edits it. "
                   "To undo the card payment, the service appended a refund.", [
            (lambda: [FadeIn(ao, shift=0.1 * DOWN)], 0.6),
            "To undo",
            (lambda: [glow(rows[3][0], GOLD_M, 1.02)], 0.8),
            "appended a refund",
            (lambda: [glow(rows[4][0], TEAL_M, 1.02)], 0.8),
        ])

        # ---- the fold ------------------------------------------------------------------------------------------
        fbox = RoundedRectangle(corner_radius=0.12, width=LW, height=0.85, stroke_color=BLUE_M, stroke_width=3)
        fbox.set_fill(fill(BLUE_M), 1).move_to([LX, FOLD_Y, 0])
        flab = left_at(T("fold", 24, BLUE_M), LX - LW / 2 + 0.3, FOLD_Y)

        def fval(k, color=WHITE):
            return right_at(M("balance " + RUNNING[k], 24, color), LX + LW / 2 - 0.3, FOLD_Y)

        fv = fval(0)
        cur = SurroundingRectangle(rows[0][0], color=YELLOW_M, buff=0.05, corner_radius=0.1, stroke_width=4)
        self.steps("So where is the balance? You compute it. Start from an empty account at zero, and apply each event "
                   "in order. This is called a fold.", [
            "You compute",
            (lambda: [FadeIn(fbox), FadeIn(flab)], 0.7),
            "Start from",
            (lambda: [FadeIn(fv)], 0.5),
            "and apply",
            (lambda: [Create(cur)], 0.6),
        ])

        def step_to(k, color=WHITE):
            return [cur.animate.move_to(rows[k][0]), Transform(fv, fval(k, color))]

        self.steps("The balance goes to a hundred, then seventy, twenty five, seventy again, and twenty. "
                   "The fold lands on twenty euros, with a reason for every step.", [
            (lambda: step_to(1), 0.5),
            "seventy,",
            (lambda: step_to(2), 0.5),
            "twenty five",
            (lambda: step_to(3), 0.5),
            "seventy again",
            (lambda: step_to(4), 0.5),
            "and twenty",
            (lambda: step_to(5, GREEN_M), 0.5),
            "with a reason",
            (lambda: [*[Indicate(r[3], color=YELLOW_M, scale_factor=1.08) for r in rows[1:]]], 1.0),
        ])

        # ---- projections ---------------------------------------------------------------------------------------
        SRC = np.array([LX + LW / 2 + 0.12, 0.55, 0])

        def parrow(y):
            return Arrow(SRC, [PX - PW / 2 - 0.12, y, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.07)

        a_bal = parrow(BAL_Y)
        bal_t = ptitle("projection: balances", BAL_Y, BAL_H, WHITE)
        bal_bm = bookmark("read up to v6", BAL_Y, BAL_H)
        self.steps("Folding the log for every question is slow, so the system keeps read models, called projections. "
                   "The accounts table becomes one, fed by the log.", [
            (lambda: [FadeOut(cur), FadeOut(fbox), FadeOut(flab), FadeOut(fv)], 0.7),
            "The accounts table",
            (lambda: [tab.animate.set_opacity(1).set_fill(BLACK, 1), tbody.animate.set_opacity(1),
                      Transform(tval, right_at(M("20.00", 26), PX + CX, BAL_Y - 0.22)),
                      Transform(ttl, bal_t)], 0.8),
            "fed by",
            (lambda: [GrowArrow(a_bal), FadeIn(bal_bm)], 0.6),
            (lambda: [LaggedStart(*[flow(a_bal, YELLOW_M, 0.6) for _ in range(4)], lag_ratio=0.3)], 1.4),
        ])

        stm = pbox(STM_Y, STM_H)
        a_stm = parrow(STM_Y)
        stm_t = ptitle("projection: statement", STM_Y, STM_H, WHITE)
        stm_bm = bookmark("read up to v6", STM_Y, STM_H)
        stm_in = VGroup(left_at(M("money in", 22, GREY_B), PX - CX, STM_Y + 0.24), right_at(M("+145.00", 24, GREEN_M), PX + CX, STM_Y + 0.24))
        stm_out = VGroup(left_at(M("money out", 22, GREY_B), PX - CX, STM_Y - 0.24), right_at(M("-125.00", 24, RED_M), PX + CX, STM_Y - 0.24))
        self.steps("A monthly statement is another projection of the same six events: "
                   "a hundred and forty five in, a hundred and twenty five out. Each projection keeps a bookmark, "
                   "the last event it applied.", [
            (lambda: [FadeIn(stm), FadeIn(stm_t), GrowArrow(a_stm)], 0.7),
            (lambda: [LaggedStart(*[flow(a_stm, YELLOW_M, 0.6) for _ in range(4)], lag_ratio=0.3)], 1.4),
            "a hundred and forty five",
            (lambda: [FadeIn(stm_in, shift=0.1 * UP)], 0.5),
            "a hundred and twenty five",
            (lambda: [FadeIn(stm_out, shift=0.1 * UP), FadeIn(stm_bm)], 0.5),
            "Each projection keeps",
            (lambda: [Indicate(bal_bm, color=YELLOW_M), Indicate(stm_bm, color=YELLOW_M)], 1.0),
        ])

        frd = pbox(FRD_Y, FRD_H, GOLD_M)
        frd_t = ptitle("new: withdrawals \u2265 40.00", FRD_Y, FRD_H, GOLD_M)
        frd_bm = bookmark("read up to v0", FRD_Y, FRD_H)
        empty = T("empty", 22, GREY_C).move_to([PX, FRD_Y, 0])
        a_frd = parrow(FRD_Y)
        self.steps("Months later, the fraud team asks a new question: show every withdrawal of forty euros or more. "
                   "No projection ever kept that.", [
            (lambda: [FadeIn(frd), FadeIn(frd_t), FadeIn(frd_bm), FadeIn(empty)], 0.9),
            "No projection",
            (lambda: [glow(frd, GOLD_M, 1.03)], 0.9),
        ])

        def fline(i, y):
            v, kind, amt, ref = EVENTS[i]
            return VGroup(left_at(M(v, 22, GREY_B), PX - CX, y), left_at(M(amt, 22, GOLD_M), PX - CX + 0.65, y),
                          left_at(T(ref, 20, GREY_B), PX + 0.2, y))

        f4, f6 = fline(3, FRD_Y + 0.26), fline(5, FRD_Y - 0.26)
        cur2 = SurroundingRectangle(rows[0][0], color=GOLD_M, buff=0.05, corner_radius=0.1, stroke_width=4)

        def rp(k):
            out = [cur2.animate.move_to(rows[k][0]), Transform(frd_bm, bookmark(f"read up to v{k + 1}", FRD_Y, FRD_H)),
                   flow(a_frd, GOLD_M, 0.45)]
            if k == 3:
                out += [FadeOut(empty), FadeIn(f4, shift=0.1 * LEFT)]
            if k == 5:
                out += [FadeIn(f6, shift=0.1 * LEFT)]
            return out

        self.steps("Write it, and replay the log from the very first event. "
                   "Forty five and fifty land in it, though they happened long before it existed.", [
            (lambda: [GrowArrow(a_frd)], 0.5),
            "replay the log",
            (lambda: [Create(cur2), Transform(frd_bm, bookmark("read up to v1", FRD_Y, FRD_H))], 0.5),
            *[(lambda k=k: rp(k), 0.5) for k in range(1, 6)],
            "though they happened",
            (lambda: [glow(rows[3][0], GOLD_M, 1.02), glow(rows[5][0], GOLD_M, 1.02)], 0.9),
        ])

        same = chip("same events, same order: the same view, every time", GREEN_M, 22).move_to([0, -3.4, 0])
        self.steps("Replay is safe because the same events in the same order give the same view. "
                   "So a projection never looks up today's exchange rate, and never sends an email.", [
            (lambda: [FadeOut(cur2), FadeIn(same, shift=0.1 * UP)], 0.8),
            "So a projection",
            (lambda: [glow(stm, GREEN_M, 1.03), glow(frd, GREEN_M, 1.03)], 1.0),
        ])

        self.steps("So keep every event. The balance, the statement and any view you think of later "
                   "are folds you can run again from the start.", [
            (lambda: [*[glow(r[0], YELLOW_M, 1.02) for r in rows]], 1.0),
            "The balance",
            (lambda: [glow(tab, WHITE, 1.03)], 0.6),
            "the statement",
            (lambda: [glow(stm, WHITE, 1.03)], 0.6),
            "and any view",
            (lambda: [glow(frd, GOLD_M, 1.03)], 0.6),
        ])
        self.wait(0.6)
