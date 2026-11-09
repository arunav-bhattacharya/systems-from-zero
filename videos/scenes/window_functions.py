from sfz import *

SAY.insert(0, (r"\bLAG\b", "lag"))
SAY.insert(0, (r"\bOVER\b", "over"))

# the eight succeeded March payments: merchant, created_at, amount_minor
PAY = {13: ("m5", "03-01 00:00", 64000), 14: ("m1", "03-04 09:30", 5310), 16: ("m5", "03-08 19:20", 31500),
       17: ("m4", "03-12 16:40", 18999), 18: ("m4", "03-12 16:42", 18999), 19: ("m4", "03-15 21:00", 18999),
       21: ("m7", "03-25 12:30", 1325), 22: ("m5", "03-31 23:59", 52000)}
BY_ID = [13, 14, 16, 17, 18, 19, 21, 22]
BY_PART = [14, 17, 18, 19, 13, 16, 22, 21]
PARTS = [("m1", [0], BLUE_M), ("m4", [1, 2, 3], GOLD_M), ("m5", [4, 5, 6], TEAL_M), ("m7", [7], PURPLE_M)]

Q_X, Q_Y = -6.3, [3.2, 2.74]
HDR_Y, RULE_Y = 2.1, 1.84
ROW_Y = [1.45 - 0.53 * i for i in range(8)]
C_PID, C_MER, C_TIME = -5.3, -3.2, -1.0     # column centres
AMT_R, NEW_R = 2.35, 5.6                       # right edges of the number columns
X0, X1 = -6.15, 5.8                            # table extent
BAR_X = -6.42
CAP_Y = [-2.92, -3.4]


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


def query(l1, l2, hl, under=None):
    """Two lines of SQL; the new part in yellow. under: a phrase of line 1 that line 2 lines up beneath."""
    a = left_at(M(l1, 22, t2c={hl: YELLOW_M}), Q_X, Q_Y[0])
    b = M(l2, 22, t2c={hl: YELLOW_M})
    x = Q_X
    if under:
        pre = l1[:l1.index(under)]
        x += M(pre + "P", 22).width - M("P", 22).width
    return VGroup(a, left_at(b, x, Q_Y[1]))


def row(pid, slot):
    mer, ts, amt = PAY[pid]
    y = ROW_Y[slot]
    return VGroup(M(str(pid), 20).move_to([C_PID, y, 0]), M(mer, 20).move_to([C_MER, y, 0]),
                  M(ts, 20, GREY_B).move_to([C_TIME, y, 0]), right_at(M(str(amt), 20), AMT_R, y))


def grouped(mer, total, slot):
    y = ROW_Y[slot]
    return VGroup(M(mer, 20).move_to([C_MER, y, 0]), right_at(M(str(total), 20, GOLD_M), AMT_R, y))


def val(text, slot, color=YELLOW_M):
    return right_at(M(text, 20, color), NEW_R, ROW_Y[slot])


def header(new=None, group=False):
    if group:
        return VGroup(M("merchant_id", 20, GREY_B).move_to([C_MER, HDR_Y, 0]),
                      right_at(M("sum(amount_minor)", 20, GREY_B), AMT_R, HDR_Y))
    g = VGroup(M("payment_id", 20, GREY_B).move_to([C_PID, HDR_Y, 0]), M("merchant_id", 20, GREY_B).move_to([C_MER, HDR_Y, 0]),
               M("created_at", 20, GREY_B).move_to([C_TIME, HDR_Y, 0]), right_at(M("amount_minor", 20, GREY_B), AMT_R, HDR_Y))
    if new:
        g.add(right_at(M(new, 20, YELLOW_M), NEW_R, HDR_Y))
    return g


def tint(slots, color=YELLOW_M):
    g = VGroup()
    for s in slots:
        g.add(Rectangle(width=X1 - X0, height=0.48, stroke_width=0).set_fill(color, 0.13).move_to([(X0 + X1) / 2, ROW_Y[s], 0]))
    return g.set_z_index(-1)


def cur(slot):
    return RoundedRectangle(corner_radius=0.06, width=X1 - X0 + 0.1, height=0.5, stroke_color=YELLOW_M, stroke_width=3)\
        .move_to([(X0 + X1) / 2, ROW_Y[slot], 0])


def bar(slots, color):
    top, bot = ROW_Y[slots[0]] + 0.2, ROW_Y[slots[-1]] - 0.2
    return Line([BAR_X, top, 0], [BAR_X, bot, 0], stroke_width=6, color=color)


def cap(s, k=0, color=GREY_B, size=24):
    return T(s, size, color).move_to([0, CAP_Y[k], 0])


class WindowFunctions(Base):
    """sql-06, section 0 (with section 3's running total and section 2's LAG): eight succeeded March payments.
    GROUP BY merchant folds them into four rows; sum() OVER (PARTITION BY merchant_id) keeps all eight and gives each its
    merchant's total; ORDER BY created_at turns that into a running total whose frame grows row by row; lag(payment_id)
    reads the row before, so payment 18 sits next to 17, two minutes earlier."""

    def construct(self):
        self.title_card("Window functions", "every row stays, and sees its partition")

        rows = {p: row(p, i) for i, p in enumerate(BY_ID)}
        hdr = header()
        rule = Line([X0, RULE_Y, 0], [X1, RULE_Y, 0], stroke_width=1.5, color=GREY_D)
        self.steps("Eight card payments from March, at four merchants. "
                   "Finance wants each payment next to its merchant's total.", [
            (lambda: [FadeIn(hdr), Create(rule)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(rows[p], shift=0.1 * DOWN) for p in BY_ID], lag_ratio=0.15)], 1.6),
            "Finance wants",
            (lambda: [*[Indicate(rows[p][1], color=YELLOW_M) for p in BY_ID]], 0.9),
        ])

        qg = query("SELECT merchant_id, sum(amount_minor)", "FROM payments GROUP BY merchant_id", "GROUP BY merchant_id")
        totals = {"m1": 5310, "m4": 56997, "m5": 147500, "m7": 1325}
        g = {m: grouped(m, totals[m], k) for k, (m, _, _) in enumerate(PARTS)}
        c1 = cap("GROUP BY: 8 rows in, 4 rows out")
        self.steps("GROUP BY merchant adds up each merchant's payments, and folds them into one row. "
                   "Eight rows go in, four come out.", [
            (lambda: [FadeIn(qg, shift=0.1 * DOWN)], 0.7),
            (lambda: [*[rows[p].animate.move_to([rows[p].get_center()[0], ROW_Y[BY_PART.index(p)], 0]) for p in BY_ID]], 1.0),
            "and folds",
            (lambda: [Transform(hdr, header(group=True)),
                      *[rows[BY_PART[s]].animate.move_to([rows[BY_PART[s]].get_center()[0], ROW_Y[k], 0]).set_opacity(0)
                        for k, (m, slots, _) in enumerate(PARTS) for s in slots],
                      *[FadeIn(g[m]) for m in g]], 1.2),
            "Eight rows go in",
            (lambda: [FadeIn(c1, shift=0.1 * UP)], 0.6),
        ])

        c2 = cap("no single payment_id is left to show")
        self.steps("The payments are gone. A grouped row stands for a whole merchant, "
                   "so there's no payment id left to show.", [
            (lambda: [FadeOut(c1), FadeIn(c2)], 0.6),
            "A grouped row",
            (lambda: [*[Indicate(g[m][1], color=GOLD_M) for m in g]], 1.0),
        ])

        qw = query("SELECT payment_id, merchant_id, amount_minor,", "  sum(amount_minor) OVER (PARTITION BY merchant_id)",
                   "OVER (PARTITION BY merchant_id)")
        rows = {p: row(p, BY_PART.index(p)) for p in BY_ID}
        bars = VGroup(*[bar(slots, c) for _, slots, c in PARTS])
        c3 = cap("a partition: the rows with the same merchant")
        self.steps("A window function keeps every row. Write OVER after the sum, with PARTITION BY merchant. "
                   "Rows with the same merchant form a partition.", [
            (lambda: [FadeOut(c2), FadeOut(qg), FadeIn(qw),
                      *[FadeOut(g[m]) for m in g],
                      *[FadeIn(rows[BY_PART[s]], target_position=g[m].get_center()) for m, slots, _ in PARTS for s in slots],
                      Transform(hdr, header("merchant_total"))], 1.3),
            "Rows with the same",
            (lambda: [LaggedStart(*[Create(b) for b in bars], lag_ratio=0.3), FadeIn(c3)], 1.1),
        ])

        vals = {}

        def put(pid, text, color=YELLOW_M):
            v = val(text, BY_PART.index(pid), color)
            if pid in vals:
                return [Transform(vals[pid], v)]
            vals[pid] = v
            return [FadeIn(v, shift=0.1 * LEFT)]

        cr = cur(0)
        w = tint([0])
        c4 = cap("current row 14: its window is merchant 1's partition")
        self.steps("For each row, the database adds up the row's window, here its partition, "
                   "and writes the sum into a new column.", [
            (lambda: [Create(cr), FadeOut(c3), FadeIn(c4)], 0.6),
            "here its partition",
            (lambda: [FadeIn(w)], 0.5),
            "and writes",
            (lambda: put(14, "5310"), 0.6),
        ])

        c5 = cap("18999 + 18999 + 18999 = 56997")
        self.steps("The window of payment 17 holds payments 17, 18 and 19, so its total is 56,997. "
                   "Rows 18 and 19 have the same window, and the same total.", [
            (lambda: [cr.animate.move_to(cur(1)), Transform(w, tint([1, 2, 3])), FadeOut(c4)], 0.7),
            "so its total",
            (lambda: [*put(17, "56997"), FadeIn(c5)], 0.6),
            "Rows 18 and 19",
            (lambda: [cr.animate.move_to(cur(2))], 0.4),
            (lambda: put(18, "56997"), 0.4),
            (lambda: [cr.animate.move_to(cur(3))], 0.4),
            (lambda: put(19, "56997"), 0.4),
        ])

        c6 = cap("8 rows in, 8 rows out")
        self.steps("Every row gets its merchant's total. Eight rows in, eight rows out.", [
            (lambda: [FadeOut(c5), cr.animate.move_to(cur(4)), Transform(w, tint([4, 5, 6]))], 0.5),
            (lambda: [*put(13, "147500"), *put(16, "147500"), *put(22, "147500")], 0.5),
            (lambda: [cr.animate.move_to(cur(7)), Transform(w, tint([7]))], 0.4),
            (lambda: put(21, "1325"), 0.4),
            "Eight rows in",
            (lambda: [FadeOut(cr), FadeOut(w), FadeIn(c6)], 0.5),
            (lambda: [*[Indicate(rows[p][0], color=YELLOW_M) for p in BY_ID]], 0.8),
        ])

        qr = query("SELECT ..., sum(amount_minor) OVER (PARTITION BY merchant_id", "ORDER BY created_at)",
                   "ORDER BY created_at", under="PARTITION")
        c7 = cap("frame: from the partition's first row to the current row")
        cr = cur(1)
        w = tint([1])
        self.steps("Now add ORDER BY created at, inside OVER. The rows that a window function adds up are called its frame. "
                   "With ORDER BY, the frame stops at the current row.", [
            (lambda: [FadeOut(c6), FadeOut(qw), FadeIn(qr), Transform(hdr, header("running_total")),
                      *[FadeOut(vals.pop(p)) for p in [13, 16, 17, 18, 19, 22]]], 1.0),
            "The rows that",
            (lambda: [Create(cr), FadeIn(w), FadeIn(c7)], 0.6),
            "With ORDER BY",
            (lambda: put(17, "18999"), 0.5),
            (lambda: [cr.animate.move_to(cur(2)), Transform(w, tint([1, 2]))], 0.5),
            (lambda: put(18, "37998"), 0.5),
            (lambda: [cr.animate.move_to(cur(3)), Transform(w, tint([1, 2, 3]))], 0.5),
            (lambda: put(19, "56997"), 0.5),
        ])

        c8 = cap("64000, then + 31500 = 95500, then + 52000 = 147500")
        self.steps("At merchant 5, payment 13 adds up only itself. Payment 16 adds two rows, and payment 22 all three.", [
            (lambda: [cr.animate.move_to(cur(4)), Transform(w, tint([4])), FadeOut(c7), FadeIn(c8)], 0.6),
            (lambda: put(13, "64000"), 0.5),
            "Payment 16",
            (lambda: [cr.animate.move_to(cur(5)), Transform(w, tint([4, 5]))], 0.5),
            (lambda: put(16, "95500"), 0.5),
            "and payment 22",
            (lambda: [cr.animate.move_to(cur(6)), Transform(w, tint([4, 5, 6]))], 0.5),
            (lambda: put(22, "147500"), 0.5),
        ])

        c9 = cap("a running total: one addition per row")
        self.steps("That's a running total. The database sorts each partition once, "
                   "then carries the sum down: one addition per row.", [
            (lambda: [FadeOut(cr), FadeOut(w), FadeOut(c8), FadeIn(c9)], 0.6),
            "then carries",
            (lambda: [Succession(*[Indicate(vals[p], color=YELLOW_M, run_time=0.45) for p in [13, 16, 22]])], 1.4),
        ])

        ql = query("SELECT ..., lag(payment_id) OVER (PARTITION BY merchant_id", "ORDER BY created_at)",
                   "lag(payment_id)", under="PARTITION")
        c10 = cap("lag: the value from the row before, in the same partition")
        self.steps("Lag reads just one row of the window: the row before the current one.", [
            (lambda: [FadeOut(c9), FadeOut(qr), FadeIn(ql), Transform(hdr, header("prev_id")),
                      *[FadeOut(vals.pop(p)) for p in list(vals)]], 1.0),
            "the row before",
            (lambda: [FadeIn(c10)], 0.6),
        ])

        cr = cur(1)
        fly = {}

        def read17():
            fly["c"] = rows[17][0].copy().set_color(YELLOW_M)
            vals[18] = val("17", 2)
            return [ReplacementTransform(fly["c"], vals[18])]

        self.steps("Payment 17 is first at merchant 4, so it has no row before it, and lag gives null. "
                   "For payment 18, the row before is 17.", [
            (lambda: [Create(cr)], 0.5),
            "and lag gives",
            (lambda: put(17, "NULL", GREY_B), 0.6),
            "For payment 18",
            (lambda: [cr.animate.move_to(cur(2))], 0.5),
            (lambda: [Indicate(rows[17][0], color=YELLOW_M)], 0.6),
            (read17, 0.8),
            (lambda: [*put(19, "18"), *put(14, "NULL", GREY_B), *put(13, "NULL", GREY_B), *put(16, "13"),
                      *put(22, "16"), *put(21, "NULL", GREY_B)], 0.7),
        ])

        c11 = cap("same merchant, same amount, 2 minutes apart", 0, GOLD_M)
        self.steps("Payment 18 came two minutes after 17, for the same amount. "
                   "Put each payment next to the one before it, and a double charge stands out.", [
            (lambda: [FadeOut(c10), FadeIn(c11)], 0.5),
            (lambda: [Indicate(rows[17][2], color=GOLD_M), Indicate(rows[18][2], color=GOLD_M)], 0.9),
            "for the same amount",
            (lambda: [Indicate(rows[17][3], color=GOLD_M), Indicate(rows[18][3], color=GOLD_M)], 0.9),
            "and a double charge",
            (lambda: [cr.animate.set_stroke(GOLD_M, 4)], 0.5),
        ])

        self.steps("GROUP BY folds each group into one row. A window keeps every row, and lets it see its partition.", [
            (lambda: [FadeOut(cr), FadeOut(c11)], 0.5),
            (lambda: [*[Indicate(rows[p][1], color=YELLOW_M) for p in BY_ID]], 0.9),
            "A window keeps",
            (lambda: [LaggedStart(*[FadeIn(tint(slots, c), rate_func=there_and_back) for _, slots, c in PARTS],
                                  lag_ratio=0.3)], 1.6),
        ])
        self.wait(0.6)
