from sfz import *

SAY.insert(0, (r"\bpay-(\d)\b", r"pay \1"))
SAY.insert(0, (r"\bm-cafe's\b", "em cafe's"))
SAY.insert(0, (r"\bm-cafe\b", "em cafe"))
SAY.insert(0, (r"\bm-books\b", "em books"))

# the log, left
LOG_X, LOG_W = -4.35, 4.5
LOG_TOP, LOG_BOT = 2.35, -2.15
ROW_Y = [1.5 - 0.55 * i for i in range(7)]
ROW_X, ROW_W = -4.15, 3.8
OFF_X = -6.3
PID_X, TYP_X, AMT_R = -5.85, -4.8, -2.45
SVC = np.array([LOG_X, 3.15, 0])
# the views, right
V_X0, V_X1 = 0.4, 6.4
V_C = (V_X0 + V_X1) / 2
IDX = (3.45, 1.5)      # top, bottom
TOT = (1.2, -0.75)
CCH = (-1.05, -2.2)
LAB_Y = -2.62
CAP_Y = -3.22

RECS = [("pay-1", "auth", "40.00"), ("pay-2", "auth", "12.50"), ("pay-1", "capture", "40.00"), ("pay-2", "capture", "12.50"),
        ("pay-3", "auth", "9.00"), ("pay-3", "capture", "9.00"), ("pay-1", "refund", "40.00")]


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


def panel(x0, x1, top, bot, color, title, sub=None):
    r = RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])
    g = VGroup(r, left_at(T(title, 26), x0 + 0.3, top - 0.36))
    if sub:
        g.add(right_at(T(sub, 18, GREY_B), x1 - 0.25, top - 0.36))
    return g


def logrow(i, color=GREY_D):
    pid, typ, amt = RECS[i]
    y = ROW_Y[i]
    r = RoundedRectangle(corner_radius=0.07, width=ROW_W, height=0.42, stroke_color=color, stroke_width=1.5)
    r.set_fill(BLACK, 1).move_to([ROW_X, y, 0])
    tc = {"auth": GREY_B, "capture": WHITE, "refund": GOLD_M}[typ]
    return VGroup(r, T(str(i), 20, GREY_B).move_to([OFF_X, y, 0]), left_at(M(pid, 20), PID_X, y),
                  left_at(M(typ, 20, tc), TYP_X, y), right_at(M(amt, 20, tc), AMT_R, y))


def cursor(i):
    return RoundedRectangle(corner_radius=0.08, width=ROW_W + 0.14, height=0.5, stroke_color=YELLOW_M, stroke_width=4).move_to([ROW_X, ROW_Y[i], 0])


def idx_y(k):
    return IDX[0] - 0.8 - 0.42 * k


def tot_y(k):
    return TOT[0] - 0.8 - 0.42 * k


STATUS_C = {"AUTHORIZED": GREY_B, "CAPTURED": WHITE, "REFUNDED": GOLD_M}


def irow(k, pid, status):
    y = idx_y(k)
    return VGroup(left_at(M(pid, 20), V_X0 + 0.45, y), left_at(M(status, 20, STATUS_C[status]), V_X0 + 2.2, y))


def trow(k, merchant, day, amt, color=WHITE):
    y = tot_y(k)
    return VGroup(left_at(M(merchant, 20), V_X0 + 0.45, y), left_at(M(day, 20, GREY_B), V_X0 + 2.2, y),
                  right_at(M(amt, 20, color), V_X0 + 4.6, y))


def cap(s, color=GREY_B, size=24):
    return T(s, size, color).move_to([0, CAP_Y, 0])


class DerivedData(Base):
    """found-01, section 1: a payments service appends seven events to payments.log, the system of record. An index,
    daily totals and a cached balance are derived from it. The index is lost in a restart and rebuilt by replaying the
    log from offset 0 to the same answer; the log itself has no such source, so losing it loses the payments."""

    def construct(self):
        self.title_card("Systems of record and derived data", "one log, and everything computed from it")

        svc = box("payments service", WHITE, w=3.4, h=0.6, size=24).move_to(SVC)
        logp = panel(LOG_X - LOG_W / 2, LOG_X + LOG_W / 2, LOG_TOP, LOG_BOT, BLUE_M, "payments.log")
        logp[1].move_to([LOG_X, LOG_TOP - 0.36, 0])
        wa = Arrow(SVC + 0.32 * DOWN, [LOG_X, LOG_TOP + 0.04, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.35)
        rows = [logrow(i) for i in range(7)]
        self.steps("A payments service writes every event to the end of one file, a log. "
                   "It never changes a line. It only adds new ones.", [
            (lambda: [FadeIn(svc, shift=0.1 * DOWN)], 0.7),
            "to the end",
            (lambda: [FadeIn(logp), GrowArrow(wa)], 0.8),
            (lambda: [travel(wa, YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(rows[0], shift=0.15 * DOWN)], 0.5),
            "It only adds",
            (lambda: [travel(wa, YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(rows[1], shift=0.15 * DOWN)], 0.5),
        ])

        self.steps("Seven records so far. Three payments are each authorized, then captured, "
                   "and the last record refunds pay-1.", [
            (lambda: [LaggedStart(*[FadeIn(rows[i], shift=0.15 * DOWN) for i in range(2, 6)], lag_ratio=0.35)], 1.8),
            "and the last",
            (lambda: [travel(wa, YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(rows[6], shift=0.15 * DOWN)], 0.5),
            (lambda: [glow(rows[6][0], GOLD_M, 1.03)], 0.7),
        ])

        cur = cursor(0)
        idx = panel(V_X0, V_X1, IDX[0], IDX[1], TEAL_M, "index", "payment id to status")
        ia = Arrow([LOG_X + LOG_W / 2 + 0.05, 0.1, 0], [V_X0 - 0.05, (IDX[0] + IDX[1]) / 2, 0], buff=0, stroke_width=3,
                   color=GREY_B, max_tip_length_to_length_ratio=0.08)
        ir = [irow(0, "pay-1", "REFUNDED"), irow(1, "pay-2", "CAPTURED"), irow(2, "pay-3", "CAPTURED")]
        self.steps("To find one payment in the log, you'd read it from the top. So the service builds an index: "
                   "each payment id, with its latest status.", [
            (lambda: [Create(cur)], 0.4),
            (lambda: [cur.animate(rate_func=linear).move_to(cursor(6))], 1.6),
            (lambda: [FadeOut(cur)], 0.3),
            "So the service",
            (lambda: [GrowArrow(ia), FadeIn(idx)], 0.8),
            "each payment id",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in ir], lag_ratio=0.3)], 1.0),
        ])

        tot = panel(V_X0, V_X1, TOT[0], TOT[1], TEAL_M, "daily totals", "per merchant and day")
        ta = Arrow([LOG_X + LOG_W / 2 + 0.05, 0.1, 0], [V_X0 - 0.05, (TOT[0] + TOT[1]) / 2, 0], buff=0, stroke_width=3,
                   color=GREY_B, max_tip_length_to_length_ratio=0.1)
        tr = [trow(0, "m-cafe", "03-02", "49.00"), trow(1, "m-cafe", "03-03", "-40.00", GOLD_M),
              trow(2, "m-books", "03-02", "12.50")]
        self.steps("Daily totals feed the merchant dashboard. The refund counts on the day it happened, the third of March.", [
            (lambda: [GrowArrow(ta), FadeIn(tot)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in tr], lag_ratio=0.3)], 1.0),
            "The refund counts",
            (lambda: [glow(rows[6][0], GOLD_M, 1.03)], 0.7),
            (lambda: [Indicate(tr[1][2], color=GOLD_M)], 0.8),
        ])

        cch = panel(V_X0, V_X1, CCH[0], CCH[1], TEAL_M, "cache", "a saved answer")
        ca = Arrow([LOG_X + LOG_W / 2 + 0.05, 0.1, 0], [V_X0 - 0.05, (CCH[0] + CCH[1]) / 2, 0], buff=0, stroke_width=3,
                   color=GREY_B, max_tip_length_to_length_ratio=0.08)
        cr = VGroup(left_at(M("m-cafe balance", 20), V_X0 + 0.45, CCH[0] - 0.78), right_at(M("9.00", 20), V_X0 + 4.6, CCH[0] - 0.78))
        self.steps("And a cache keeps the balance of m-cafe, so the dashboard doesn't add it up again on every refresh.", [
            (lambda: [GrowArrow(ca), FadeIn(cch)], 0.8),
            (lambda: [FadeIn(cr, shift=0.1 * RIGHT)], 0.6),
        ])

        sor = T("system of record", 24, BLUE_M).move_to([LOG_X, LAB_Y, 0])
        der = T("derived data", 24, TEAL_M).move_to([V_C, LAB_Y, 0])
        self.steps("The log is the system of record. Each fact is written there first, and only once. "
                   "The index, the totals and the cache are derived data: all three are computed from the log.", [
            (lambda: [FadeIn(sor, shift=0.1 * UP), glow(logp[0], BLUE_M, 1.02)], 0.9),
            "The index",
            (lambda: [FadeIn(der, shift=0.1 * UP)], 0.6),
            (lambda: [glow(idx[0], TEAL_M, 1.02), glow(tot[0], TEAL_M, 1.02), glow(cch[0], TEAL_M, 1.03)], 0.9),
            "all three",
            (lambda: [travel(ia, YELLOW_M, 0.6), travel(ta, YELLOW_M, 0.6), travel(ca, YELLOW_M, 0.6)], 0.6),
        ])

        lost_sub = right_at(T("lost in a restart", 18, RED_M), V_X1 - 0.25, IDX[0] - 0.36)
        c1 = cap("the index lived in memory", RED_M)
        self.steps("Now the machine that holds the index restarts. The index lived in memory, and it's gone.", [
            (lambda: [idx[0].animate.set_stroke(RED_M), FadeOut(idx[2]), FadeIn(lost_sub)], 0.8),
            "The index lived",
            (lambda: [*[FadeOut(r, shift=0.1 * DOWN) for r in ir], FadeIn(c1)], 0.9),
        ])

        empty = T("(empty)", 22, GREY_B).move_to([V_C, idx_y(1), 0])
        c2 = cap("replay from offset 0, in order")
        cur = cursor(0)
        self.steps("Nothing is lost, because the log still has every fact. Start an empty index, "
                   "go back to the first record, and replay the log in order.", [
            (lambda: [glow(logp[0], BLUE_M, 1.02)], 0.9),
            "Start an empty",
            (lambda: [idx[0].animate.set_stroke(TEAL_M), FadeOut(lost_sub), FadeIn(idx[2]), FadeIn(empty)], 0.8),
            "go back to",
            (lambda: [FadeOut(c1), FadeIn(c2), Create(cur)], 0.7),
        ])

        n = [irow(0, "pay-1", "AUTHORIZED"), irow(1, "pay-2", "AUTHORIZED")]
        self.steps("Records 0 and 1 authorize pay-1 and pay-2. Records 2 and 3 capture them.", [
            (lambda: [FadeOut(empty), travel(ia, YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(n[0], shift=0.1 * RIGHT)], 0.4),
            (lambda: [cur.animate.move_to(cursor(1))], 0.4),
            (lambda: [travel(ia, YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(n[1], shift=0.1 * RIGHT)], 0.4),
            "Records 2 and 3",
            (lambda: [cur.animate.move_to(cursor(2))], 0.4),
            (lambda: [Transform(n[0], irow(0, "pay-1", "CAPTURED"))], 0.5),
            (lambda: [cur.animate.move_to(cursor(3))], 0.4),
            (lambda: [Transform(n[1], irow(1, "pay-2", "CAPTURED"))], 0.5),
        ])

        n.append(irow(2, "pay-3", "AUTHORIZED"))
        self.steps("Records 4 and 5 authorize and capture pay-3. Record 6, the refund, marks pay-1 as refunded.", [
            (lambda: [cur.animate.move_to(cursor(4))], 0.4),
            (lambda: [FadeIn(n[2], shift=0.1 * RIGHT)], 0.4),
            (lambda: [cur.animate.move_to(cursor(5))], 0.4),
            (lambda: [Transform(n[2], irow(2, "pay-3", "CAPTURED"))], 0.5),
            "Record 6",
            (lambda: [cur.animate.move_to(cursor(6))], 0.5),
            "marks pay-1",
            (lambda: [Transform(n[0], irow(0, "pay-1", "REFUNDED"))], 0.6),
        ])

        oks = [tick(True, 0.14).move_to([V_X1 - 0.55, idx_y(k), 0]) for k in range(3)]
        c3 = cap("rebuilt: the same three answers as before", GREEN_M)
        self.steps("The rebuilt index gives the same answers as the one that was lost, and nobody typed anything in by hand.", [
            (lambda: [FadeOut(cur), FadeOut(c2)], 0.4),
            (lambda: [LaggedStart(*[Create(o) for o in oks], lag_ratio=0.3), FadeIn(c3)], 1.0),
            (lambda: [glow(idx[0], GREEN_M, 1.02)], 0.8),
        ])

        c4 = cap("refund replayed before the capture: pay-1 would end up CAPTURED", GOLD_M)
        self.steps("The order matters. Replay the refund before the capture, and pay-1 would end up captured. "
                   "So the log keeps every record, in the order it was written.", [
            (lambda: [FadeOut(c3), FadeIn(c4)], 0.7),
            (lambda: [glow(rows[6][0], GOLD_M, 1.03), glow(rows[2][0], WHITE, 1.03)], 0.9),
            "So the log keeps",
            (lambda: [LaggedStart(*[glow(r[0], BLUE_M, 1.03) for r in rows], lag_ratio=0.12)], 1.4),
        ])

        lost_t = T("payments.log: lost", 24, RED_M).move_to(logp[1])
        log_t = logp[1].copy()
        c5 = cap("lose the log, and no view can rebuild the payments", RED_M)
        self.steps("Now ask the same of the log. If it's gone, nothing can bring it back. The index knows statuses, "
                   "and the totals know sums. Neither knows what each payment was.", [
            (lambda: [FadeOut(VGroup(*oks)), FadeOut(c4)], 0.5),
            "If it's gone",
            (lambda: [logp[0].animate.set_stroke(RED_M), *[r.animate.set_opacity(0.25) for r in rows], Transform(logp[1], lost_t), FadeIn(c5)], 1.0),
            "The index knows",
            (lambda: [glow(idx[0], RED_M, 1.02)], 0.8),
            "the totals know",
            (lambda: [glow(tot[0], RED_M, 1.02)], 0.8),
        ])

        self.steps("So write each fact to the system of record first. Every view derived from it "
                   "can be thrown away, and computed again.", [
            (lambda: [Transform(logp[1], log_t), FadeOut(c5), logp[0].animate.set_stroke(BLUE_M), *[r.animate.set_opacity(1) for r in rows]], 0.9),
            (lambda: [travel(wa, YELLOW_M, 0.6)], 0.6),
            (lambda: [glow(logp[0], BLUE_M, 1.02)], 0.8),
            "Every view",
            (lambda: [travel(ia, YELLOW_M, 0.7), travel(ta, YELLOW_M, 0.7), travel(ca, YELLOW_M, 0.7)], 0.7),
            (lambda: [glow(idx[0], TEAL_M, 1.02), glow(tot[0], TEAL_M, 1.02), glow(cch[0], TEAL_M, 1.03)], 0.9),
        ])
        self.wait(0.6)
