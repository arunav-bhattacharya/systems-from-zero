from sfz import *

SAY.insert(0, (r"\bcard-status\b", "card status"))

SW, SH, SY = 2.8, 1.2, 0.9                  # segment boxes: width, height, row
SX = [-4.65, -1.55, 1.55, 4.65]             # segment centres
SP, STW = 0.32, 0.24                        # record strips: pitch and width
BASE = [0, 104, 208, 312]
NY, STY, MKY = 1.78, 0.02, -0.62             # file names, status line under the boxes, first-readable marker
RW, RP, RY = 1.3, 1.42, 0.9                 # compaction: record boxes
CX0 = -5.15                                 # x of offset 0 in the card-status segment


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def strip(x, y=SY, color=TEAL_M):
    r = RoundedRectangle(corner_radius=0.04, width=STW, height=0.8, stroke_color=color, stroke_width=2)
    return r.set_fill(fillc(color, 0.45), 1).move_to([x, y, 0]).set_z_index(2)


def bx(j):
    """x of strip j in the one big file."""
    return SX[0] - 1.12 + j * SP


def sx(s, i):
    """x of strip i (0 to 7) in segment s."""
    return SX[s] - 1.12 + i * SP


def bar(n, y=SY):
    w = n * SP + 0.24
    r = RoundedRectangle(corner_radius=0.12, width=w, height=SH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
    return r.move_to([SX[0] - SW / 2 + w / 2, y, 0])


def seg(s, color=WHITE):
    r = RoundedRectangle(corner_radius=0.12, width=SW, height=SH, stroke_color=color, stroke_width=3).set_fill(BLACK, 1)
    return r.move_to([SX[s], SY, 0])


def fname(s):
    n = f"{BASE[s]:020d}"
    k = len(n) - len(str(BASE[s])) if BASE[s] else 19
    return Text(n + ".log", font=MONO, font_size=13, t2c={f"[0:{k}]": GREY_D}).move_to([SX[s], NY, 0])


def under(s, text, color=GREY_B):
    return T(text, 18, color).move_to([SX[s], STY, 0])


def marker(x, k):
    tri = Triangle(color=GOLD_M, fill_opacity=1, stroke_width=0).scale(0.1).move_to([x, MKY, 0])
    lab = T(f"first readable offset: {k}", 18, GOLD_M).next_to(tri, RIGHT, buff=0.12)
    return VGroup(tri, lab)


def rx(k):
    return CX0 + k * RP


def record(k, key, val, color, x=None):
    x = rx(k) if x is None else x
    tomb = val == "null"
    r = RoundedRectangle(corner_radius=0.1, width=RW, height=1.3, stroke_color=RED_M if tomb else GREY_B, stroke_width=2.5)
    r.set_fill(fillc(RED_M if tomb else GREY_B, 0.12), 1).move_to([x, RY, 0])
    v = (M(val, 18, color) if tomb else T(val, 19, color)).move_to([x, RY - 0.38, 0])
    return VGroup(r, M(str(k), 16, GREY_B).move_to([x, RY + 0.4, 0]), M(key, 17).move_to([x, RY, 0]), v)


class SegmentsCompaction(Base):
    """msg-03, section 1: a partition only grows (about 260 GB a day); one big file can only be cut at its end, so
    dropping a day means copying 1.5 TB. The broker keeps a chain of segments named after base offsets 0, 104, 208, 312;
    the active one rolls when full. Retention (7 days) deletes a segment only when its newest record has expired: 0 and
    104 go, 208 stays with 208 to 249 still readable, and the first readable offset jumps from 0 to 208. Then
    compaction on card-status: the cleaner maps each key to its last offset, rewrites the closed segment keeping 3, 4, 5
    (gaps where 0 to 2 were), and keeps card-2's tombstone for a day."""

    def construct(self):
        self.title_card("Segments, retention and compaction", "how a broker deletes from a log it only appends to")

        title = T("card-auths topic, partition 0: one big file", 20, GREY_B).move_to([-6.05, 3.25, 0], aligned_edge=LEFT)
        bars = {"b": bar(0.01)}
        strips = []
        cnt = {}

        def day(d):
            new = [strip(bx(3 * d + i)) for i in range(3)]
            strips.extend(new)
            sz = ["260 GB", "520 GB", "780 GB", "1 TB", "1.3 TB", "1.6 TB", "1.8 TB"][d]
            c = T(f"{d + 1} day{'s' if d else ''}: {sz}", 22, WHITE).move_to([4.4, SY, 0])
            out = [Transform(bars["b"], bar(3 * d + 3)), LaggedStart(*[FadeIn(s, shift=0.1 * LEFT) for s in new], lag_ratio=0.3)]
            if d == 0:
                cnt["m"] = c
                return out + [FadeIn(c)]
            return out + [Transform(cnt["m"], c)]

        old = VGroup()
        oldl = T("oldest day", 18, RED_M).move_to([bx(1), NY, 0])
        self.steps("A busy payments partition takes about 260 gigabytes a day. "
                   "After seven days, the oldest records must go.", [
            (lambda: [FadeIn(title), FadeIn(bars["b"])], 0.5),
            *[(lambda d=d: day(d), 0.5) for d in range(7)],
            "the oldest records",
            (lambda: [*[s.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.45), 1) for s in strips[:3]], FadeIn(oldl)], 0.7),
        ])

        cutx = (bx(2) + bx(3)) / 2
        endx = bars["b"].get_right()[0]
        cut0 = DashedLine([cutx, SY - 0.72, 0], [cutx, SY + 0.58, 0], dash_length=0.07, stroke_width=3, color=RED_M)
        cut1 = DashedLine([endx + 0.12, SY - 0.72, 0], [endx + 0.12, SY + 0.72, 0], dash_length=0.07, stroke_width=3, color=GREEN_M)
        lab0 = VGroup(tick(False, 0.16), T("can't cut at the start", 18, RED_M)).arrange(RIGHT, buff=0.14)
        lab0.next_to([cutx, STY - 0.06, 0], RIGHT, buff=0.18)
        lab1 = VGroup(tick(True, 0.16), T("cheap to cut at the end", 18, GREEN_M)).arrange(RIGHT, buff=0.14)
        lab1.next_to([endx + 0.12, STY - 0.06, 0], RIGHT, buff=0.18)
        CY = -1.6
        copybar = bar(18, CY)
        copies = [strip(bx(j), CY) for j in range(18)]
        cost = chip("copy 1.5 TB, every day", RED_M, 20).move_to([4.4, CY, 0])
        self.steps("One big file won't do. A file system can cut a file short only at its end, "
                   "so dropping the oldest day means copying the other one and a half terabytes, every day.", [
            "A file system",
            (lambda: [Create(cut1), FadeIn(lab1)], 0.7),
            "only at its end",
            (lambda: [Create(cut0), FadeIn(lab0)], 0.7),
            "so dropping",
            (lambda: [FadeIn(copybar)], 0.4),
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.25 * DOWN) for c in copies], lag_ratio=0.08),
                      FadeIn(cost, shift=0.1 * UP)], 2.0),
        ])

        segs = [seg(0), seg(1), seg(2, BLUE_M)]
        names = [fname(s) for s in range(4)]
        title2 = T("card-auths topic, partition 0: a chain of segments", 20, GREY_B).move_to(title, aligned_edge=LEFT)
        slot = [(0, i) for i in range(8)] + [(1, i) for i in range(8)] + [(2, i) for i in range(5)]

        def split():
            return [ReplacementTransform(bars["b"], VGroup(*segs)), Transform(title, title2),
                    *[s.animate.move_to([sx(a, i), SY, 0]).set_stroke(TEAL_M).set_fill(fillc(TEAL_M, 0.45), 1)
                      for s, (a, i) in zip(strips, slot)]]

        self.steps("So the broker cuts the log into a chain of files called segments, each named after its first record's offset.", [
            (lambda: [FadeOut(VGroup(copybar, *copies, cost, cut0, cut1, lab0, lab1, oldl, cnt["m"]))], 0.6),
            (lambda: split(), 1.3),
            "each named",
            (lambda: [LaggedStart(*[FadeIn(names[s], shift=0.1 * DOWN) for s in range(3)], lag_ratio=0.3)], 1.0),
            (lambda: [*[glow(names[s], WHITE, 1.08) for s in range(3)]], 0.7),
        ])

        act = T("active", 18, BLUE_M).move_to([SX[2], STY, 0])
        more = [strip(sx(2, i)) for i in range(5, 8)]
        seg3 = seg(3, BLUE_M)
        s3 = [strip(sx(3, i)) for i in range(7)]
        closed = [under(s, "closed") for s in range(3)]
        self.steps("Only the newest, the active segment, takes appends. When it's full, the broker closes it and starts the next. "
                   "Closed segments never change.", [
            (lambda: [FadeIn(act), glow(segs[2], BLUE_M, 1.03)], 0.7),
            "takes appends",
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.15 * LEFT) for s in more], lag_ratio=0.4)], 1.0),
            "the broker closes",
            (lambda: [segs[2].animate.set_stroke(WHITE)], 0.5),
            "starts the next",
            (lambda: [FadeIn(seg3), FadeIn(names[3], shift=0.1 * DOWN), act.animate.move_to([SX[3], STY, 0])], 0.7),
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.15 * LEFT) for s in s3], lag_ratio=0.25)], 1.2),
            "Closed segments",
            (lambda: [*[FadeIn(c) for c in closed], *[glow(segs[s], WHITE, 1.03) for s in range(3)]], 0.9),
        ])
        strips = strips + more
        expired = strips[:19]          # offsets 0 to 249: all of 0 and 104, the first three strips of 208

        leg = VGroup(strip(0, 0, RED_M), T("older than 7 days", 18, GREY_B), strip(0, 0), T("newer", 18, GREY_B))
        leg.arrange(RIGHT, buff=0.16)
        leg[2].shift(0.3 * RIGHT)
        leg[3].shift(0.3 * RIGHT)
        leg.move_to([-4.0, -2.4, 0])
        self.steps("Retention lets records older than seven days go: the red ones. "
                   "But the broker deletes files, so a segment goes only when its newest record has expired.", [
            "the red ones",
            (lambda: [LaggedStart(*[s.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.45), 1) for s in expired], lag_ratio=0.05),
                      FadeIn(leg)], 1.2),
            "deletes files",
            (lambda: [*[glow(segs[s], WHITE, 1.03) for s in range(3)]], 0.8),
            "its newest record",
            (lambda: [*[glow(strips[8 * s + 7], YELLOW_M, 1.25) for s in range(3)]], 1.0),
        ])

        exp0, exp1 = under(0, "newest expired", RED_M), under(1, "newest expired", RED_M)
        keep = under(2, "newest is fresh: keep", TEAL_M)
        self.steps("Every five minutes it checks from the oldest. Segments 0 and 104 have expired. "
                   "208's newest record is fresh, so the check stops.", [
            "Segments 0",
            (lambda: [glow(strips[7], YELLOW_M, 1.3), Transform(closed[0], exp0)], 0.7),
            (lambda: [glow(strips[15], YELLOW_M, 1.3), Transform(closed[1], exp1)], 0.7),
            "208's newest",
            (lambda: [glow(strips[23], YELLOW_M, 1.3), Transform(closed[2], keep)], 0.8),
        ])

        mk = marker(sx(0, 0), 0)
        gone = VGroup(segs[0], segs[1], *strips[:16], names[0], names[1], closed[0], closed[1])
        self.steps("Both files are deleted whole, and the first readable offset jumps from 0 to 208.", [
            (lambda: [FadeIn(mk, shift=0.1 * UP)], 0.5),
            (lambda: [segs[0].animate.set_stroke(RED_M), segs[1].animate.set_stroke(RED_M)], 0.4),
            (lambda: [FadeOut(gone, shift=0.2 * DOWN)], 0.9),
            "jumps from",
            (lambda: [Transform(mk, marker(sx(2, 0), 208))], 1.0),
        ])

        still = chip("208 to 249: past 7 days, still readable", RED_M, 18).move_to([2.6, -2.4, 0])
        self.steps("Records 208 to 249 are past seven days but still readable, since they share a file with fresh ones. "
                   "Seven days is a minimum.", [
            (lambda: [*[glow(s, YELLOW_M, 1.25) for s in strips[16:19]], FadeIn(still, shift=0.1 * UP)], 1.0),
            "since they share",
            (lambda: [glow(segs[2], WHITE, 1.03)], 0.9),
            "Seven days is",
            (lambda: [glow(still[0], RED_M, 1.04)], 0.8),
        ])

        # ---- compaction --------------------------------------------------------------------------------------------
        title3 = T("card-status topic, partition 0", 20, GREY_B).move_to(title, aligned_edge=LEFT)
        cseg = RoundedRectangle(corner_radius=0.14, width=8.8, height=1.7, stroke_color=BLUE_M, stroke_width=3).set_fill(BLACK, 1)
        cseg.move_to([-1.6, RY, 0])
        clab = T("active segment", 18, BLUE_M).move_to([-1.6, RY + 1.15, 0])
        data = [("card-1", "active", GREEN_M), ("card-2", "active", GREEN_M), ("card-1", "frozen", BLUE_M),
                ("card-3", "active", GREEN_M), ("card-1", "active", GREEN_M), ("card-2", "null", RED_M)]
        recs = [record(k, *d) for k, d in enumerate(data)]
        rest = VGroup(segs[2], seg3, *strips[16:], *s3, names[2], names[3], closed[2], act, mk, still, leg)
        self.steps("Some topics hold state. Each card-status record gives a card's latest status, "
                   "and services replay them to rebuild a map.", [
            (lambda: [FadeOut(rest)], 0.8),
            (lambda: [Transform(title, title3), FadeIn(cseg), FadeIn(clab)], 0.7),
            "Each card-status",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.2 * LEFT) for r in recs[:5]], lag_ratio=0.35)], 2.2),
        ])

        age = T("unchanged for 3 weeks", 18, RED_M).move_to([rx(3), RY - 1.15, 0])
        self.steps("Deleting by age would drop a card unchanged for three weeks. You want the last record for each key.", [
            (lambda: [glow(recs[3][0], RED_M, 1.06), FadeIn(age)], 0.8),
            "You want",
            (lambda: [FadeOut(age), recs[0].animate.set_opacity(0.3), recs[2].animate.set_opacity(0.3)], 0.7),
            (lambda: [*[glow(recs[k][0], YELLOW_M, 1.06) for k in (1, 3, 4)]], 0.9),
        ])

        tlab = T("tombstone", 18, RED_M).move_to([rx(5), RY - 1.15, 0])
        self.steps("To delete a card, you append its key with no value. That record is a tombstone.", [
            (lambda: [FadeIn(recs[5], shift=0.2 * LEFT)], 0.8),
            (lambda: [recs[1].animate.set_opacity(0.3)], 0.6),
            "That record",
            (lambda: [FadeIn(tlab), glow(recs[5][0], RED_M, 1.06)], 0.8),
        ])

        aseg = RoundedRectangle(corner_radius=0.14, width=1.7, height=1.7, stroke_color=BLUE_M, stroke_width=3).set_fill(BLACK, 1)
        aseg.move_to([4.1, RY, 0])
        alab = T("active", 18, BLUE_M).move_to([4.1, RY + 1.15, 0])
        r6 = record(6, "card-4", "active", GREEN_M, x=4.1)
        clab2 = T("closed segment", 18, GREY_B).move_to(clab)
        mbx = RoundedRectangle(corner_radius=0.14, width=4.6, height=2.1, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.1), 1)
        mbx.move_to([-1.6, -2.05, 0])
        mtl = T("log cleaner: last offset per key", 20, GOLD_M).move_to([-1.6, -1.32, 0])
        rows = [M(f"{k} → {o}", 20).move_to([-1.6, y, 0]) for (k, o), y in zip((("card-1", 4), ("card-2", 5), ("card-3", 3)),
                                                                              (-1.8, -2.25, -2.7))]
        self.steps("Once the segment rolls, the log cleaner, a background thread, notes the offset of each key's last record.", [
            (lambda: [cseg.animate.set_stroke(WHITE), Transform(clab, clab2), FadeIn(aseg), FadeIn(alab)], 0.7),
            (lambda: [FadeIn(r6, shift=0.2 * LEFT)], 0.6),
            "the log cleaner",
            (lambda: [FadeIn(mbx), FadeIn(mtl)], 0.7),
            "notes the offset",
            (lambda: [FadeIn(rows[0]), glow(recs[4][0], GOLD_M, 1.06)], 0.6),
            (lambda: [FadeIn(rows[1]), glow(recs[5][0], GOLD_M, 1.06)], 0.6),
            (lambda: [FadeIn(rows[2]), glow(recs[3][0], GOLD_M, 1.06)], 0.6),
        ])

        gap = T("0 to 2: removed", 18, GREY_B).move_to([rx(1), RY, 0])
        self.steps("Then it rewrites the segment, keeping only those. Offsets never change, so it has gaps.", [
            (lambda: [*[recs[k][0].animate.set_stroke(RED_M) for k in (0, 1, 2)]], 0.5),
            (lambda: [FadeOut(VGroup(recs[0], recs[1], recs[2]), scale=0.8)], 0.8),
            "Offsets never",
            (lambda: [*[glow(recs[k][0], GREEN_M, 1.06) for k in (3, 4, 5)]], 0.8),
            "so it has gaps",
            (lambda: [FadeIn(gap)], 0.6),
        ])

        kept = T("kept for 1 day", 18, RED_M).move_to(tlab)
        self.steps("The tombstone stays a day, so every reader sees card-2 go. Then it goes too.", [
            (lambda: [Transform(tlab, kept), glow(recs[5][0], RED_M, 1.06)], 0.8),
            "Then it goes",
            (lambda: [FadeOut(recs[5], scale=0.8), FadeOut(tlab), rows[1].animate.set_opacity(0.3)], 0.8),
        ])

        f1 = chip("retention: drop old segments whole", TEAL_M, 18).move_to([3.7, -1.55, 0])
        f2 = chip("compaction: keep each key's last value", GOLD_M, 18).move_to([3.7, -2.45, 0])
        self.steps("Retention drops whole old segments, "
                   "and compaction rewrites them to keep each key's last value.", [
            (lambda: [FadeIn(f1, shift=0.1 * UP)], 0.7),
            "and compaction",
            (lambda: [FadeIn(f2, shift=0.1 * UP), *[glow(recs[k][0], GREEN_M, 1.06) for k in (3, 4)]], 0.9),
        ])
        self.wait(0.6)
