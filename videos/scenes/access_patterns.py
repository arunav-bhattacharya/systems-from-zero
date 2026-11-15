from sfz import *

SAY.insert(0, (r"\bM-0042's\b", "M 42's"))
SAY.insert(0, (r"\bM-0042\b", "M 42"))

GX0, GD, SQ = 0.9, 0.56, 0.42          # partition grids: first centre x, spacing, square size
G1Y = [2.75, 2.19, 1.63, 1.07]         # the main table's 4 rows of 10 partitions
G2Y = [-0.35, -0.91, -1.47, -2.03]     # the second copy
LCX, LW = -3.65, 5.7                   # left column: centre x, width
AP_Y = [2.7, 2.1, 1.5]
TGT = (0, 3)                           # the partition that ends up holding M-0042's day
SCAT = [(1, 0), (4, 0), (8, 0), (2, 1), (6, 1), (9, 1), (0, 2), (3, 2), (5, 2), (7, 3), (4, 3), (9, 3)]

def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def arr(a, b, color=GREY_B, sw=2.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = np.linalg.norm(b - a)
    return Arrow(a, b, buff=0.04, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2 / n,
                 max_stroke_width_to_length_ratio=20)




def sq_xy(c, r, rows=G1Y):
    return np.array([GX0 + c * GD, rows[r], 0])


def grid(rows):
    return VGroup(*[Square(SQ, stroke_color=GREY_B, stroke_width=2).set_fill(fillc(GREY_B, 0.12), 1).move_to(sq_xy(c, r, rows))
                    for r in range(4) for c in range(10)])


def cell(g, c, r):
    return g[r * 10 + c]


def ap(k, text, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.08, width=LW, height=0.48, stroke_color=color, stroke_width=2).set_fill(fillc(color), 1)
    r.move_to([LCX, AP_Y[k], 0])
    return VGroup(r, left_at(T(text, 18), LCX - LW / 2 + 0.2, AP_Y[k]))


def counters(parts, items, color=GREY_B):
    a = right_at(T(f"partitions asked: {parts}", 20, color), 6.45, -2.6)
    b = right_at(T(f"payments read: {items}", 20, color), 6.45, -3.1)
    return VGroup(a, b)


ROWS_P = [("09:00:03", "pay-80211"), ("09:00:41", "pay-80218"), ("...", "40,000 a day"),
          ("10:29:51", "pay-81722"), ("10:29:58", "pay-81729"), ("10:30:12", "pay-81730")]


class AccessPatterns(Base):
    """model-02, section 1 (with section 0's two-part address): 50 million payments on 40 partitions. Keyed by payment id,
    M-0042's day is scattered, so the question asks all 40. Write the questions first: a merchant's day, newest first; a
    payment by id. Partition key (merchant, day) puts the day in one partition; sort key time makes newest-first one slice.
    A second copy keyed by payment id answers question two in one item. An unplanned question reads all 50 million."""

    def construct(self):
        self.title_card("Model the access patterns first", "write the questions down, then choose the keys")

        # ---- 1. 40 partitions, keyed by payment id ------------------------------------------------------------------
        g1 = grid(G1Y)
        t1 = left_at(T("payments, keyed by payment id", 19, GREY_B), GX0 - SQ / 2, 3.3)
        pid = mbox("pay-81730", WHITE, h=0.5, size=18).move_to([-3.4, 2.1, 0])
        ha = arr([pid.get_right()[0] + 0.05, 2.1, 0], cell(g1, 0, 1).get_left() + 0.03 * LEFT, GREY_B)
        hl = T("hash of the id", 16, GREY_B).move_to([-0.95, 2.37, 0])
        self.steps("Fifty million payments are spread over 40 partitions, each on its own machine. To place a payment, "
                   "the store hashes its id to pick a partition.", [
            (lambda: [LaggedStart(*[FadeIn(s, scale=0.8) for s in g1], lag_ratio=0.03), FadeIn(t1)], 1.6),
            "To place",
            (lambda: [FadeIn(pid, shift=0.1 * RIGHT)], 0.5),
            "hashes its id",
            (lambda: [GrowArrow(ha), FadeIn(hl)], 0.6),
            (lambda: [travel(ha, YELLOW_M, 0.6)], 0.6),
            (lambda: [glow(cell(g1, 0, 1), YELLOW_M, 1.15)], 0.6),
        ])

        # ---- 2. the merchant's day is everywhere ------------------------------------------------------------------------
        dots = VGroup(*[Dot(radius=0.075, color=GOLD_M).move_to(sq_xy(c, r)) for c, r in SCAT])
        q1 = left_at(T("merchant M-0042, today", 20, GOLD_M), -6.5, 1.2)
        cnt = counters("40 of 40", "50,000,000", RED_M)
        self.steps("Now ask for merchant M-0042's payments today. They're scattered over nearly every partition, so the "
                   "store asks all 40, and each one reads everything it holds.", [
            (lambda: [FadeOut(pid), FadeOut(ha), FadeOut(hl), FadeIn(q1, shift=0.1 * RIGHT)], 0.6),
            "They're scattered",
            (lambda: [LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.08)], 1.2),
            "so the store asks",
            (lambda: [LaggedStart(*[s.animate.set_stroke(RED_M) for s in g1], lag_ratio=0.02)], 1.2),
            "and each one",
            (lambda: [FadeIn(cnt)], 0.6),
        ])

        # ---- 3. write the questions down ---------------------------------------------------------------------------------
        aph = left_at(T("the questions, written down first", 20, GOLD_M), LCX - LW / 2, 3.3)
        self.steps("A store like this finds data only by its key. So before you choose keys, write down the questions "
                   "your code will ask.", [
            (lambda: [FadeOut(cnt), FadeOut(q1), *[s.animate.set_stroke(GREY_B) for s in g1]], 0.7),
            "So before",
            (lambda: [FadeIn(aph, shift=0.1 * DOWN)], 0.6),
        ])

        a1 = ap(0, "1. a merchant's payments for one day, newest first", GOLD_M)
        a2 = ap(1, "2. one payment, by its id", BLUE_M)
        self.steps("One: a merchant's payments for one day, newest first. Two: a single payment, by its id.", [
            (lambda: [FadeIn(a1, shift=0.1 * RIGHT)], 0.6),
            "Two:",
            (lambda: [FadeIn(a2, shift=0.1 * RIGHT)], 0.6),
        ])

        # ---- 4. partition key = (merchant, day) ---------------------------------------------------------------------------
        t1b = left_at(T("payments, keyed by merchant and day", 19, GOLD_M), GX0 - SQ / 2, 3.3)
        tgt = cell(g1, *TGT)
        tl = T("M-0042, today", 15, GOLD_M).next_to(tgt, DOWN, buff=0.12)
        tl.align_to(tgt, LEFT)
        cnt1 = counters("1 of 40", "...", GOLD_M)
        self.steps("For question one, make the partition key the merchant and the day. All of M-0042's payments for today "
                   "now land in one partition.", [
            (lambda: [glow(a1[0], GOLD_M, 1.02)], 0.6),
            "make the partition key",
            (lambda: [Transform(t1, t1b)], 0.7),
            "All of",
            (lambda: [*[d.animate.move_to(tgt.get_center() + 0.09 * np.array([(i % 4) - 1.5, (i // 4) - 1, 0])).scale(0.6)
                        for i, d in enumerate(dots)]], 1.2),
            (lambda: [tgt.animate.set_stroke(GOLD_M, 3).set_fill(fillc(GOLD_M, 0.3), 1), FadeIn(tl), FadeIn(cnt1[0])], 0.6),
        ])

        # ---- 5. sort key = time --------------------------------------------------------------------------------------------
        pan = RoundedRectangle(corner_radius=0.14, width=LW, height=4.0, stroke_color=GOLD_M, stroke_width=2.5).set_fill(BLACK, 1)
        pan.move_to([LCX, -1.2, 0])
        ph = left_at(T("partition (M-0042, today), sorted by time", 18, GOLD_M), LCX - LW / 2 + 0.25, 0.5)
        lk = DashedLine(tgt.get_corner(DL), pan.get_corner(UR) + np.array([-0.15, -0.05, 0]), dash_length=0.08, stroke_width=1.8,
                        color=GOLD_M)
        rows = VGroup()
        for i, (tm, p) in enumerate(ROWS_P):
            y = 0.0 - i * 0.52
            if tm == "...":
                rows.add(VGroup(T("... 40,000 payments a day", 16, GREY_B).move_to([LCX, y, 0])))
            else:
                rows.add(VGroup(left_at(M(tm, 17, WHITE), LCX - LW / 2 + 0.45, y), left_at(M(p, 17, GREY_B), LCX - 0.2, y)))
        sl = Rectangle(width=LW - 0.4, height=1.5, stroke_color=GREEN_M, stroke_width=2.5).set_fill(GREEN_M, 0.1)
        sl.move_to([LCX, -2.08, 0])
        sll = right_at(T("newest 20", 17, GREEN_M), LCX + LW / 2 - 0.3, -2.08)
        cnt2 = counters("1 of 40", "20", GREEN_M)
        self.steps("Inside it, a sort key, the time, keeps them in order. Newest first is one slice: start at the end, "
                   "and read back 20.", [
            (lambda: [Create(lk), FadeIn(pan), FadeIn(ph)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * UP) for r in rows], lag_ratio=0.15)], 1.2),
            "Newest first",
            (lambda: [FadeIn(sl), FadeIn(sll)], 0.7),
            "and read back",
            (lambda: [Transform(cnt1, cnt2)], 0.6),
        ])

        # ---- 6. a two-part address ---------------------------------------------------------------------------------------------
        addr = VGroup(chip("partition key: merchant, day", GOLD_M, 17), chip("sort key: time", GREEN_M, 17)).arrange(RIGHT, buff=0.25)
        addr.move_to([3.6, -0.6, 0])
        self.steps("So each payment has a two-part address. The partition key picks the partition, "
                   "and the sort key says where inside it.", [
            (lambda: [FadeIn(addr[0], shift=0.1 * UP)], 0.6),
            "The partition key picks",
            (lambda: [glow(tgt, GOLD_M, 1.2)], 0.8),
            "and the sort key",
            (lambda: [FadeIn(addr[1], shift=0.1 * UP), glow(sl, GREEN_M, 1.02)], 0.8),
        ])

        # ---- 7. question two needs a second copy ----------------------------------------------------------------------------------
        g2 = grid(G2Y)
        t2 = left_at(T("a second copy, keyed by payment id", 19, BLUE_M), GX0 - SQ / 2, 0.2)
        hit = cell(g2, 6, 1)
        cnt3 = counters("1 of 40", "1", BLUE_M)
        wr = left_at(T("one more write per payment", 18, BLUE_M), GX0 - SQ / 2, -2.6)
        self.steps("Question two gives only a payment id, which isn't in that address. So the store keeps a second copy, "
                   "keyed by id: one partition, one item. It costs one more write per payment.", [
            (lambda: [glow(a2[0], BLUE_M, 1.02), FadeOut(addr)], 0.6),
            "So the store keeps",
            (lambda: [LaggedStart(*[FadeIn(s, scale=0.8) for s in g2], lag_ratio=0.02), FadeIn(t2)], 1.2),
            "one partition",
            (lambda: [hit.animate.set_stroke(BLUE_M, 3).set_fill(fillc(BLUE_M, 0.4), 1), Transform(cnt1, cnt3)], 0.7),
            "It costs",
            (lambda: [FadeIn(wr)], 0.6),
        ])

        # ---- 8. the question nobody planned -----------------------------------------------------------------------------------------
        a3 = ap(2, "3. failed payments over €500, any merchant", RED_M)
        nk = T("no key", 16, RED_M).move_to([LCX + LW / 2 - 0.55, AP_Y[2], 0])
        cnt4 = counters("40 of 40", "50,000,000", RED_M)
        self.steps("Then a question nobody planned for arrives: failed payments over 500 euros, at any merchant. No key "
                   "matches, so the store reads all 40 partitions, 50 million payments, to return a handful.", [
            (lambda: [FadeOut(wr), hit.animate.set_stroke(GREY_B, 2).set_fill(fillc(GREY_B, 0.12), 1),
                      FadeIn(a3, shift=0.1 * RIGHT)], 0.7),
            "so the store reads",
            (lambda: [LaggedStart(*[s.animate.set_stroke(RED_M) for s in g1 if s is not tgt], lag_ratio=0.02),
                      tgt.animate.set_stroke(RED_M)], 1.2),
            "50 million",
            (lambda: [Transform(cnt1, cnt4)], 0.6),
        ])

        # ---- 9. the sentence to keep ----------------------------------------------------------------------------------------------
        self.steps("Write the questions down first, and give each one a key that makes it one read in one partition. "
                   "A question you didn't plan for reads everything.", [
            (lambda: [*[s.animate.set_stroke(GREY_B) for s in g1], tgt.animate.set_stroke(GOLD_M, 3),
                      glow(a1[0], GOLD_M, 1.02), glow(a2[0], BLUE_M, 1.02)], 0.9),
            "one read in one partition",
            (lambda: [glow(tgt, GOLD_M, 1.25), glow(hit, BLUE_M, 1.25)], 0.9),
            "A question you didn't",
            (lambda: [glow(a3[0], RED_M, 1.02), *[s.animate(rate_func=there_and_back).set_stroke(RED_M) for s in g1]], 1.0),
        ])
        self.wait(0.6)
