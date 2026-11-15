from sfz import *

SAY.insert(0, (r"\bM-0042's\b", "M 42's"))
SAY.insert(0, (r"\bM-0042\b", "M 42"))

KX, KW = -5.35, 2.3                    # partition key chips: centre x, width
SX0, DW, DG, BH = -3.85, 1.3, 0.08, 0.55   # partition strips: start x, day block width, gap, height
MY = [2.3, 1.3, 0.3]                   # map rows
PX0, PX1, PT, PB = -1.0, 6.5, -0.35, -3.4  # the zoomed partition panel
GUIDE_X = SX0 + 2.5 * (DW + DG)        # 100,000 rows = 2.5 days of 40,000

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




def key(text, y, color=WHITE):
    r = RoundedRectangle(corner_radius=0.08, width=KW, height=BH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to([KX, y, 0])
    return VGroup(r, M(text, 17).move_to([KX, y, 0]))


def day_x(i):
    return SX0 + i * (DW + DG) + DW / 2


def day(i, y, label, color=GOLD_M, x=None):
    x = day_x(i) if x is None else x
    r = Rectangle(width=DW, height=BH, stroke_color=color, stroke_width=2).set_fill(color, 0.22).move_to([x, y, 0])
    return VGroup(r, T(label, 15).move_to([x, y, 0]))


def bar(w, y, label):
    r = Rectangle(width=w, height=BH, stroke_color=GREY_B, stroke_width=2).set_fill(GREY_B, 0.15).move_to([SX0 + w / 2, y, 0])
    return VGroup(r, T(label, 15, GREY_B).move_to(r))


def link_arrow(y):
    return arr([KX + KW / 2 + 0.04, y, 0], [SX0 - 0.02, y, 0], GREY_B, 2)


ROWS_P = [("09:59:41", "pay-81402", "SETTLED"), ("09:59:58", "pay-81405", "SETTLED"), ("10:00:02", "pay-81411", "CAPTURED"),
          ("10:00:09", "pay-81412", "SETTLED"), ("...", "", ""), ("10:14:57", "pay-81780", "FAILED"),
          ("10:15:06", "pay-81783", "SETTLED")]


def panel(title):
    r = RoundedRectangle(corner_radius=0.14, width=PX1 - PX0, height=PT - PB, stroke_color=GOLD_M, stroke_width=2.5)
    r.set_fill(BLACK, 1).move_to([(PX0 + PX1) / 2, (PT + PB) / 2, 0])
    h = left_at(T(title, 18, GOLD_M), PX0 + 0.3, PT - 0.3)
    rows = VGroup()
    for i, (tm, p, st) in enumerate(ROWS_P):
        y = PT - 0.7 - i * 0.33
        if tm == "...":
            rows.add(VGroup(left_at(T("... every payment from 10:00 to 10:15", 16, GREY_B), PX0 + 1.1, y)))
        else:
            rows.add(VGroup(left_at(M(tm, 16), PX0 + 1.1, y), left_at(M(p, 16, GREY_B), PX0 + 2.75, y),
                            left_at(M(st, 16, GREY_B), PX0 + 4.55, y)))
    return r, h, rows


def row_y(i):
    return PT - 0.7 - i * 0.33


class WideColumn(Base):
    """model-05, section 0: payments_by_merchant as a map from partition key to partition. M-0042's partition holds its
    rows sorted by created_at, so 10:00 to 10:15 is one slice (seek, read, stop). Keyed by merchant alone the partition
    grows forever: 40,000 a day passes the advised 100,000 rows on day three and holds 14.6 million rows (over 2 GB) after
    a year. Bucketing by day, ((merchant_id, day), created_at), caps each partition at 40,000 rows, about 6 MB; a week of
    history becomes 7 partitions."""

    def construct(self):
        self.title_card("Wide-column partitions", "a map of partitions, each a sorted list of rows")

        # ---- 1. the question ------------------------------------------------------------------------------------------
        q = chip("M-0042's payments, today 10:00 to 10:15", GOLD_M, 20).move_to([0, 3.2, 0])
        self.steps("A Cassandra table holds 50 million payments. Support asks for merchant M-0042's payments from ten "
                   "o'clock to ten fifteen today. How does it find them without reading anything else?", [
            "Support asks",
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.7),
        ])

        # ---- 2. a map of partitions --------------------------------------------------------------------------------------
        k = [key("M-0017", MY[0]), key("M-0042", MY[1], GOLD_M), key("M-0108", MY[2])]
        la = [link_arrow(y) for y in MY]
        b17 = bar(2.6, MY[0], "M-0017's rows")
        b108 = bar(3.6, MY[2], "M-0108's rows")
        days = [day(i, MY[1], f"Nov {i + 1}") for i in range(7)]
        kh = T("partition key", 17, GREY_B).move_to([KX, 2.95, 0])
        ph = left_at(T("partition: every row for that key", 17, GREY_B), SX0, 2.95)
        self.steps("A Cassandra table is a map. Its key is the partition key, here the merchant. "
                   "Each value is a partition: every row for that merchant.", [
            (lambda: [FadeOut(q)], 0.4),
            "Its key is",
            (lambda: [LaggedStart(*[FadeIn(x, shift=0.1 * RIGHT) for x in k], lag_ratio=0.25), FadeIn(kh)], 1.0),
            "Each value",
            (lambda: [*[GrowArrow(a) for a in la], FadeIn(ph)], 0.5),
            (lambda: [FadeIn(b17), FadeIn(b108), LaggedStart(*[FadeIn(d, shift=0.1 * RIGHT) for d in days], lag_ratio=0.15)], 1.3),
        ])

        # ---- 3. hash to the replicas ----------------------------------------------------------------------------------------
        hq = VGroup(mbox("M-0042", GOLD_M, h=0.55, size=17), T("hash", 17, GREY_B), chip("a token on the ring", GREY_B, 17),
                    T("picks", 17, GREY_B), chip("3 nodes hold this partition", BLUE_M, 17)).arrange(RIGHT, buff=0.3)
        hq.move_to([0.4, -1.4, 0])
        self.steps("Cassandra hashes the partition key to pick the nodes that hold its partition, usually three. "
                   "A query that names the merchant goes only to them.", [
            (lambda: [FadeIn(hq[0]), FadeIn(hq[1])], 0.6),
            (lambda: [FadeIn(hq[2], shift=0.1 * RIGHT)], 0.5),
            "usually three",
            (lambda: [FadeIn(hq[3]), FadeIn(hq[4], shift=0.1 * RIGHT)], 0.6),
            "goes only",
            (lambda: [glow(k[1][0], GOLD_M), *[glow(d[0], GOLD_M, 1.03) for d in days]], 1.0),
        ])

        # ---- 4. rows sorted by the clustering key ------------------------------------------------------------------------------
        pr, ph2, prow = panel("partition M-0042, rows sorted by created_at")
        zl = DashedLine([day_x(6), MY[1] - BH / 2, 0], [day_x(6), PT, 0], dash_length=0.08, stroke_width=2, color=GOLD_M)
        ck = left_at(T("clustering key: created_at", 17, GOLD_M), -6.4, -1.25)
        self.steps("Inside a partition, rows are sorted by the clustering key, here the time the payment was created. "
                   "That's the order they sit in, in memory and on disk.", [
            (lambda: [FadeOut(hq)], 0.5),
            (lambda: [glow(days[6][0], GOLD_M, 1.05), Create(zl)], 0.6),
            (lambda: [FadeIn(pr), FadeIn(ph2)], 0.6),
            "sorted by",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * UP) for r in prow], lag_ratio=0.12), FadeIn(ck)], 1.3),
        ])

        # ---- 5. one slice ---------------------------------------------------------------------------------------------------
        seek = arr([PX0 + 0.15, row_y(2) + 0.0, 0], [PX0 + 0.95, row_y(2), 0], GREEN_M, 3)
        sl = Rectangle(width=PX1 - PX0 - 1.0, height=0.33 * 3 + 0.3, stroke_color=GREEN_M, stroke_width=2.5).set_fill(GREEN_M, 0.1)
        sl.move_to([PX0 + 0.5 + (PX1 - PX0 - 1.0) / 2, (row_y(2) + row_y(5)) / 2, 0])
        stop = left_at(T("stop", 16, RED_M), PX0 + 0.3, row_y(6))
        cnt = left_at(T("one partition, one slice", 18, GREEN_M), -6.4, -1.8)
        self.steps("So ten o'clock to ten fifteen is one contiguous slice. The node seeks to the first row at ten o'clock, "
                   "and reads until it passes ten fifteen.", [
            (lambda: [prow[0].animate.set_opacity(0.35), prow[1].animate.set_opacity(0.35)], 0.5),
            "The node seeks",
            (lambda: [GrowArrow(seek)], 0.5),
            "and reads",
            (lambda: [GrowFromEdge(sl, UP)], 1.2),
            "until it passes",
            (lambda: [FadeIn(stop), prow[6].animate.set_opacity(0.35), FadeIn(cnt)], 0.6),
        ])

        # ---- 6. it grows forever ---------------------------------------------------------------------------------------------
        NW = 0.6

        def narrow(i, color=GOLD_M):
            x = SX0 + i * (NW + 0.06) + NW / 2
            r = Rectangle(width=NW, height=BH, stroke_color=color, stroke_width=2).set_fill(color, 0.22).move_to([x, MY[1], 0])
            return VGroup(r, T(" ", 10).move_to(r).set_opacity(0))

        more = [narrow(7 + i) for i in range(8)]
        fwd = T("forever", 17, RED_M).move_to([SX0 + 15 * (NW + 0.06) - 0.35, MY[1] + 0.48, 0])
        gx2 = SX0 + 2.5 * (NW + 0.06)
        guide = DashedLine([GUIDE_X, MY[1] + 0.42, 0], [GUIDE_X, MY[1] - 0.42, 0], dash_length=0.07, stroke_width=2.5, color=RED_M)
        gl = T("100,000 rows: the advised limit", 15, RED_M).move_to([GUIDE_X, MY[1] - 0.52 - 0.04, 0])
        grow = ValueTracker(280000)
        gtxt = always_redraw(lambda: left_at(T(f"M-0042's partition: {int(grow.get_value()):,} rows", 20,
                                               RED_M if grow.get_value() > 100000 else GOLD_M), -6.4, -1.25))
        size = left_at(T("after a year: 14.6 million rows, over 2 GB", 20, RED_M), -6.4, -1.8)
        strip = VGroup(*[d for d in days])
        self.steps("But a merchant never stops taking payments. At 40,000 a day, this partition passes the advised "
                   "100,000 rows on day three. After a year it holds 14 million rows, over 2 GB.", [
            (lambda: [FadeOut(VGroup(pr, ph2, prow, seek, sl, stop, zl)), FadeOut(ck), FadeOut(cnt)], 0.6),
            "At 40,000",
            (lambda: [FadeIn(gtxt)], 0.4),
            "this partition passes",
            (lambda: [Create(guide), FadeIn(gl), glow(days[2][0], RED_M, 1.05)], 0.8),
            "After a year",
            (lambda: [*[Transform(days[i], narrow(i)) for i in range(7)], guide.animate.set_x(gx2), gl.animate.set_x(gx2)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.2 * LEFT) for m in more], lag_ratio=0.15), FadeIn(fwd),
                      grow.animate.set_value(14600000)], 1.4),
            (lambda: [FadeIn(size, shift=0.1 * UP)], 0.5),
        ])
        gtxt.clear_updaters()

        # ---- 7. a partition never splits ----------------------------------------------------------------------------------
        self.steps("A partition never splits across nodes. Its three replicas carry all of it, and it never stops growing.", [
            (lambda: [glow(k[1][0], RED_M)], 0.8),
            "and it never",
            (lambda: [*[glow(d[0], RED_M, 1.04) for d in days + more]], 1.0),
        ])

        # ---- 8. bucket by day ------------------------------------------------------------------------------------------------------
        nk = [key(f"M-0042, Nov {5 + i}", MY[i], GOLD_M) for i in range(3)]
        nb = [day(0, MY[i], f"Nov {5 + i}") for i in range(3)]
        nla = [link_arrow(y) for y in MY]
        guide2 = DashedLine([GUIDE_X, MY[0] + 0.42, 0], [GUIDE_X, MY[2] - 0.42, 0], dash_length=0.07, stroke_width=2.5, color=GREY_B)
        gl2 = left_at(T("100,000 rows", 15, GREY_B), GUIDE_X + 0.12, MY[0] + 0.25)
        cap = left_at(T("each partition: at most 40,000 rows, about 6 MB", 20, GREEN_M), -6.4, -1.25)
        pk = VGroup(left_at(M("PRIMARY KEY ((merchant_id, day),", 15, GOLD_M), -6.4, -1.8),
                    left_at(M("created_at)", 15, GOLD_M), -6.4 + 1.47, -2.15))
        dots = VGroup(*[Dot(radius=0.04, color=GREY_B).move_to([KX, MY[2] - 0.45 - 0.13 * j, 0]) for j in range(3)])
        self.steps("The fix is a bucket. Make the partition key the merchant and the day. Every day starts a new partition, "
                   "so none holds more than 40,000 rows, about 6 MB.", [
            (lambda: [FadeOut(size), FadeOut(gtxt), FadeOut(gl), FadeOut(guide), FadeOut(fwd), FadeIn(pk)], 0.6),
            "Every day starts",
            (lambda: [*[FadeOut(d) for d in days[:4] + more], FadeOut(k[1]), FadeOut(la[1]),
                      FadeOut(b17), FadeOut(b108), FadeOut(la[0]), FadeOut(la[2]), FadeOut(k[0]), FadeOut(k[2]),
                      *[ReplacementTransform(days[4 + i], nb[i]) for i in range(3)]], 1.2),
            (lambda: [*[FadeIn(x, shift=0.1 * RIGHT) for x in nk], *[GrowArrow(a) for a in nla]], 0.7),
            "so none holds",
            (lambda: [Create(guide2), FadeIn(gl2), FadeIn(cap)], 0.8),
        ])

        # ---- 9. the query still reads one slice ---------------------------------------------------------------------------------------
        pr2, ph3, prow2 = panel("partition (M-0042, Nov 7), sorted by created_at")
        zl2 = DashedLine(nb[2][0].get_corner(DR), [PX0, PT - 0.25, 0], dash_length=0.08, stroke_width=2, color=GOLD_M)
        sl2 = sl.copy()
        self.steps("The ten o'clock query names the merchant and today: still one partition, one slice.", [
            (lambda: [FadeOut(cap), glow(nk[2][0], GOLD_M)], 0.6),
            (lambda: [Create(zl2), FadeIn(pr2), FadeIn(ph3), FadeIn(prow2)], 0.8),
            "one partition",
            (lambda: [GrowFromEdge(sl2, UP)], 0.9),
        ])

        # ---- 10. the price ------------------------------------------------------------------------------------------------------------
        wk = left_at(T("a week of history: 7 partitions", 20, GOLD_M), -6.4, -1.25)
        wk2 = left_at(T("read in parallel and merged", 18, GREY_B), -6.4, -2.75)
        self.steps("The price: a week of history is now seven partitions, read in parallel and merged.", [
            (lambda: [FadeIn(wk, shift=0.1 * UP), *[glow(b[0], GOLD_M, 1.05) for b in nb], FadeIn(dots)], 0.9),
            "read in parallel",
            (lambda: [FadeIn(wk2)], 0.6),
        ])

        # ---- 11. the sentence to keep --------------------------------------------------------------------------------------------------
        self.steps("A Cassandra table is a map of partitions, each a sorted list of rows. Pick a partition key that every "
                   "query names, and that stops growing.", [
            (lambda: [*[glow(x[0], GOLD_M) for x in nk]], 0.9),
            "each a sorted",
            (lambda: [glow(sl2, GREEN_M, 1.02)], 0.9),
            "and that stops",
            (lambda: [glow(guide2, GREEN_M, 1.0), *[glow(b[0], GREEN_M, 1.05) for b in nb]], 0.9),
        ])
        self.wait(0.6)
