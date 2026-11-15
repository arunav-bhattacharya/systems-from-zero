from sfz import *

SAY.insert(0, (r"\bON CONFLICT\b", "on conflict"))
SAY.insert(0, (r"\bEXCLUDED\b", "excluded"))
SAY.insert(0, (r"\bINSERT\b", "insert"))
SAY.insert(0, (r"\buid\b", "U I D"))

LF = 17                                        # log text size
AX, BX = -6.55, 2.45                           # left edges of the two consumers' logs
CA, CB = -4.45, 4.5                            # consumer box centres
C_Y = 2.8
LOG_Y = [1.75, 1.25, 0.75, 0.25]
IX, IY, IW, IH = 0.0, 1.0, 4.0, 1.2            # the unique index
TH_Y, TR_Y = -1.35, [-1.78, -2.2]              # payments table: header, rows
T_UID, T_AMT_R, T_ST = -2.1, 0.95, 1.4
CODE_Y = [-2.88, -3.25]
CF = 15                                        # code text size
CHIP_Y = -0.2


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def swap(old, new):
    return [FadeOut(old), FadeIn(new)]


def log(side, k, s, color=WHITE):
    return left_at(M(s, LF, color), AX if side == "A" else BX, LOG_Y[k])


def consumer(name, x, msg, mcolor):
    r = RoundedRectangle(corner_radius=0.12, width=4.1, height=1.0, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([x, C_Y, 0])
    t = T(name, 24).move_to([x, C_Y + 0.22, 0])
    m = M(msg, 17, mcolor).move_to([x, C_Y - 0.22, 0])
    return VGroup(r, t, m)


def ix_status(s, color=GREY_B):
    return M(s, 16, color).move_to([IX, IY - 0.24, 0])


def prow(k, status, color=WHITE):
    y = TR_Y[k]
    return VGroup(M("...a001", 18, color).move_to([T_UID, y, 0]), right_at(M("4200", 18, color), T_AMT_R, y),
                  left_at(M(status, 18, color), T_ST, y))


def code(s, k, hl=None):
    return M(s, CF, t2c=hl or {}).move_to([0, CODE_Y[k], 0])


def span(line, full, sub, color, buff=0.06):
    """A box around `sub` inside a one-line monospace Text `line` that spells `full`."""
    w = M("X" * 40, CF).width / 40
    x0 = line.get_left()[0] + full.index(sub) * w
    r = Rectangle(width=len(sub) * w + 2 * buff, height=line.height + 2 * buff + 0.08, stroke_color=color, stroke_width=2.5)
    return r.move_to([x0 + len(sub) * w / 2, line.get_center()[1], 0])


class UpsertRace(Base):
    """sql-09, section 2 (with section 3's DO UPDATE): the authorization (pending) and the capture (succeeded) of one
    payment, same payment_uid, reach two consumers at once. Check-then-insert: both SELECTs find nothing and both insert;
    without a unique constraint that stores the payment twice, and with one B waits for A and fails with 23505, aborting
    its batch. INSERT ... ON CONFLICT (payment_uid) DO UPDATE consults the unique index as it writes: B waits for A, then
    its insert becomes an update, pending to succeeded, one row."""

    def construct(self):
        self.title_card("Upserts and the check-then-insert race", "let the unique index decide")

        A = consumer("consumer A", CA, "uid ...a001: pending", GOLD_M)
        B = consumer("consumer B", CB, "uid ...a001: succeeded", GREEN_M)
        self.steps("The card network sends two messages for one payment: the authorization, which is pending, "
                   "and then the capture, which succeeded. Both carry the same payment uid.", [
            (lambda: [FadeIn(A[0]), FadeIn(A[1]), FadeIn(A[2], shift=0.2 * DOWN)], 0.8),
            "and then the capture",
            (lambda: [FadeIn(B[0]), FadeIn(B[1]), FadeIn(B[2], shift=0.2 * DOWN)], 0.8),
            "the same payment uid",
            (lambda: [Indicate(A[2], color=YELLOW_M, scale_factor=1.0), Indicate(B[2], color=YELLOW_M, scale_factor=1.0)], 0.9),
        ])

        kc = code("if (payments.findByUid(msg.uid) == null) payments.insert(msg)", 0)
        th = VGroup(M("payment_uid", 16, GREY_B).move_to([T_UID, TH_Y, 0]), right_at(M("amount_minor", 16, GREY_B), T_AMT_R, TH_Y),
                    left_at(M("status", 16, GREY_B), T_ST, TH_Y))
        trule = Line([T_UID - 1.0, TH_Y - 0.24, 0], [T_ST + 1.45, TH_Y - 0.24, 0], stroke_width=1.5, color=GREY_D)
        ttl = T("payments with this uid", 22, GREY_B).next_to(th, UP, buff=0.18)
        self.steps("After a Kafka rebalance, two consumers handle them at the same moment. "
                   "The obvious code checks first: if the uid isn't stored yet, insert it.", [
            (lambda: [glow(A[0], WHITE, 1.03), glow(B[0], WHITE, 1.03)], 0.9),
            (lambda: [FadeIn(ttl), FadeIn(th), Create(trule)], 0.7),
            "The obvious code",
            (lambda: [FadeIn(kc, shift=0.1 * UP)], 0.8),
        ])

        la0, lb0 = log("A", 0, "SELECT by uid: 0 rows"), log("B", 0, "SELECT by uid: 0 rows")
        self.steps("Both checks run before either insert, and both find nothing.", [
            (lambda: [FadeIn(la0, shift=0.1 * DOWN), FadeIn(lb0, shift=0.1 * DOWN)], 0.8),
            "both find nothing",
            (lambda: [Indicate(la0, color=YELLOW_M, scale_factor=1.0), Indicate(lb0, color=YELLOW_M, scale_factor=1.0)], 0.9),
        ])

        la1, lb1 = log("A", 1, "INSERT pending: 1 row"), log("B", 1, "INSERT succeeded: 1 row", RED_M)
        r0, r1 = prow(0, "pending"), prow(1, "succeeded", RED_M)
        twice = chip("one payment stored twice: settled twice", RED_M, 20).move_to([0, CHIP_Y, 0])
        self.steps("So both insert. Without a unique constraint, the table now holds one payment twice, "
                   "and settlement pays the merchant twice.", [
            (lambda: [FadeIn(la1, shift=0.1 * DOWN), FadeIn(lb1, shift=0.1 * DOWN)], 0.7),
            (lambda: [FadeIn(r0, shift=0.1 * UP), FadeIn(r1, shift=0.1 * UP)], 0.7),
            "and settlement",
            (lambda: [FadeIn(twice, shift=0.1 * UP)], 0.7),
        ])

        # ---- with the unique index -------------------------------------------------------------------------------------
        ixr = RoundedRectangle(corner_radius=0.12, width=IW, height=IH, stroke_color=BLUE_M, stroke_width=2.5)
        ixr.set_fill(fillc(BLUE_M), 1).move_to([IX, IY, 0])
        ixt = M("unique index on payment_uid", 16, BLUE_M).move_to([IX, IY + 0.26, 0])
        IXS = {"m": ix_status("no entry for ...a001")}

        def set_ix(text, color=GREY_B):
            old, IXS["m"] = IXS["m"], ix_status(text, color)
            return swap(old, IXS["m"])

        lb1w = log("B", 1, "INSERT succeeded: waits for A", GOLD_M)
        self.steps("The course schema has a unique index on the uid. Run it again. "
                   "A inserts first, and B's insert finds A's uncommitted entry in the index, and waits.", [
            (lambda: [FadeOut(twice), FadeOut(r1), FadeOut(r0), FadeOut(la1), FadeOut(lb1)], 0.6),
            (lambda: [FadeIn(ixr), FadeIn(ixt), FadeIn(IXS["m"])], 0.7),
            "A inserts first",
            (lambda: [FadeIn(la1, shift=0.1 * DOWN), *set_ix("...a001: A's, not committed", GOLD_M)], 0.8),
            "and waits",
            (lambda: [FadeIn(lb1w, shift=0.1 * DOWN), glow(ixr, GOLD_M, 1.03)], 0.8),
        ])

        la2 = log("A", 2, "COMMIT", GREEN_M)
        lb2 = log("B", 2, "ERROR 23505: duplicate key", RED_M)
        r0 = prow(0, "pending")
        batch = chip("the error aborts B's whole batch of 500", RED_M, 20).move_to([0, CHIP_Y, 0])
        self.steps("A commits, and B fails with a duplicate key error. One row, but the error aborts B's whole transaction, "
                   "a batch of 500 messages, and the capture never lands.", [
            (lambda: [FadeIn(la2, shift=0.1 * DOWN), FadeIn(r0, shift=0.1 * UP), *set_ix("...a001: committed", GREEN_M)], 0.7),
            "and B fails",
            (lambda: [FadeIn(lb2, shift=0.1 * DOWN)], 0.6),
            "but the error",
            (lambda: [FadeIn(batch, shift=0.1 * UP)], 0.7),
            "and the capture",
            (lambda: [Indicate(r0[2], color=GOLD_M)], 0.8),
        ])

        gy = (LOG_Y[0] + LOG_Y[1]) / 2
        gap = VGroup(DashedLine([AX, gy, 0], [IX - IW / 2 - 0.15, gy, 0], dash_length=0.1, stroke_width=2.5, color=YELLOW_M),
                     DashedLine([BX - 0.1, gy, 0], [6.55, gy, 0], dash_length=0.1, stroke_width=2.5, color=YELLOW_M))
        gapl = chip("between the check and the write, the other consumer acts", YELLOW_M, 20).move_to([0, CHIP_Y, 0])
        self.steps("The trouble is the gap. The check and the write are two steps, and the other consumer can act between them.", [
            (lambda: [FadeOut(batch), Create(gap)], 0.8),
            "two steps",
            (lambda: [Indicate(la0, color=YELLOW_M, scale_factor=1.0), Indicate(la1, color=YELLOW_M, scale_factor=1.0)], 0.9),
            "and the other",
            (lambda: [FadeIn(gapl, shift=0.1 * UP)], 0.6),
        ])

        # ---- ON CONFLICT ---------------------------------------------------------------------------------------------
        c1 = code("INSERT INTO payments AS p (payment_uid, ..., status) VALUES ('...a001', ..., 'succeeded')", 0)
        c2 = code("ON CONFLICT (payment_uid) DO UPDATE SET status = EXCLUDED.status WHERE p.status = 'pending'", 1,
                  {"ON CONFLICT (payment_uid) DO UPDATE": YELLOW_M})
        olds = VGroup(la0, la1, la2, lb0, lb1w, lb2, r0, gap, gapl)
        self.steps("INSERT with ON CONFLICT makes them one step. There is no separate check: "
                   "the insert asks the unique index itself, as it writes.", [
            (lambda: [FadeOut(olds), *set_ix("no entry for ...a001"), *swap(kc, c1), FadeIn(c2)], 1.0),
            "There is no",
            (lambda: [glow(ixr, BLUE_M, 1.03)], 0.8),
            "as it writes",
            (lambda: [Indicate(c2, color=YELLOW_M, scale_factor=1.0)], 0.9),
        ])

        na0 = log("A", 0, "INSERT ... ON CONFLICT: 1 row")
        nb0 = log("B", 0, "INSERT ... ON CONFLICT: waits", GOLD_M)
        r0 = prow(0, "pending")
        self.steps("Replay it. A inserts the authorization. B's insert hits A's entry in the index and waits.", [
            "A inserts",
            (lambda: [FadeIn(na0, shift=0.1 * DOWN), *set_ix("...a001: A's, not committed", GOLD_M)], 0.8),
            "B's insert",
            (lambda: [FadeIn(nb0, shift=0.1 * DOWN), glow(ixr, GOLD_M, 1.03)], 0.8),
        ])

        na1 = log("A", 1, "COMMIT", GREEN_M)
        nb1 = log("B", 1, "conflict: UPDATE 1", GREEN_M)
        nb2 = log("B", 2, "pending -> succeeded", GREEN_M)
        r0s = prow(0, "succeeded", GREEN_M)
        self.steps("When A commits, B's conflict turns into an update. Pending becomes succeeded. "
                   "No error, and one row.", [
            (lambda: [FadeIn(na1, shift=0.1 * DOWN), *set_ix("...a001: committed", GREEN_M), FadeIn(r0, shift=0.1 * UP)], 0.8),
            "B's conflict",
            (lambda: [FadeIn(nb1, shift=0.1 * DOWN)], 0.6),
            "Pending becomes",
            (lambda: [FadeIn(nb2, shift=0.1 * DOWN), Transform(r0, r0s)], 0.8),
            "No error",
            (lambda: [Indicate(r0, color=GREEN_M, scale_factor=1.0)], 0.8),
        ])

        C2 = "ON CONFLICT (payment_uid) DO UPDATE SET status = EXCLUDED.status WHERE p.status = 'pending'"
        guard = span(c2, C2, "WHERE p.status = 'pending'", GOLD_M)
        exb = span(c2, C2, "EXCLUDED.status", YELLOW_M)
        late = chip("a late pending message changes nothing", GOLD_M, 20).move_to([0, CHIP_Y, 0])
        self.steps("EXCLUDED is the row B tried to insert. The WHERE keeps a late authorization "
                   "from setting a succeeded payment back to pending.", [
            (lambda: [Create(exb)], 0.7),
            "The WHERE",
            (lambda: [FadeOut(exb), Create(guard)], 0.7),
            "back to pending",
            (lambda: [FadeIn(late, shift=0.1 * UP)], 0.7),
        ])

        self.steps("A check in a separate statement can be out of date before you act on it. "
                   "Let the unique index decide, with the check and the write in one statement.", [
            (lambda: [FadeOut(late), FadeOut(guard), Indicate(na0, color=YELLOW_M, scale_factor=1.0)], 1.0),
            "Let the unique index",
            (lambda: [glow(ixr, BLUE_M, 1.04)], 0.9),
            "in one statement",
            (lambda: [Indicate(c2, color=YELLOW_M, scale_factor=1.0), Indicate(c1, color=YELLOW_M, scale_factor=1.0)], 1.0),
        ])
        self.wait(0.6)
