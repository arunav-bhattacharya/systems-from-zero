from sfz import *

SAY.insert(0, (r"\bm-17\b", "M 17"))

GX = {1: -4.2, 2: -2.0, 3: 0.2, 4: 2.4, 5: 4.6}    # partition columns
BW = 1.2                                          # bar width
BASE, H = -2.9, 3.2                               # baseline and full height of the scale
AXX = -5.6                                        # the axis
HY = 1.35                                         # partition headers
PC = {1: BLUE_M, 2: TEAL_M, 3: PURPLE_M, 4: GOLD_M, 5: GREEN_M}


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


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


def yv(v, mx):
    return BASE + v / mx * H


def bar(k, load, ceil, mx):
    """A partition's writes a second: green up to its ceiling, red above it (refused)."""
    x = GX[k]
    ok = min(load, ceil)
    g = Rectangle(width=BW, height=max(ok / mx * H, 0.001), stroke_width=0).set_fill(GREEN_M, 0.75)
    g.move_to([x, BASE + g.height / 2, 0])
    over = max(load - ceil, 0)
    r = Rectangle(width=BW, height=max(over / mx * H, 0.001), stroke_width=0).set_fill(RED_M, 0.8 if over else 0)
    r.move_to([x, yv(ceil, mx) + r.height / 2, 0])
    return VGroup(g, r)


def share(k, v, mx, color=GOLD_M):
    x = GX[k]
    return DashedLine([x - BW / 2 - 0.15, yv(v, mx), 0], [x + BW / 2 + 0.15, yv(v, mx), 0], dash_length=0.08,
                      stroke_width=3, color=color)


def header(k, label=None, color=None):
    return box(label or f"partition {k}", color or PC[k], w=1.95, h=0.65, size=19).move_to([GX[k], HY, 0])


def axis_labels(vals, mx):
    return VGroup(*[T(f"{v:,}", 17, GREY_B).move_to([AXX - 0.2 - 0.3, yv(v, mx), 0]) for v in vals])


def status(s, color=GREY_B):
    return T(s, 20, color).move_to([3.5, 2.95, 0])


class DynamoDBPartitions(Base):
    """shard-08, sections 1 and 2: 400 WCU over four partitions is 100 each; partition 4 gets 150 and the others 50, so
    it is throttled 50 a second while the table uses 300 of 400. Adaptive capacity raises its share to 150; a split
    for consumption puts busy keys on both halves. Then one item takes 1,500 writes a second: the partition ceiling is
    1,000, a split can't cut one key, and an item in a partition of its own still gets 1,000, so 500 are throttled."""

    def construct(self):
        self.title_card("DynamoDB: partitions and hot keys", "every partition has a ceiling")

        MX = 200
        tbl = chip("payments table: a hash of the key picks the partition", GREY_B, 19).move_to([-2.4, 2.95, 0])
        hd = {k: header(k) for k in (1, 2, 3, 4)}
        base = Line([AXX, BASE, 0], [5.6, BASE, 0], stroke_width=2.5, color=GREY_B)
        ax = Line([AXX, BASE, 0], [AXX, BASE + H, 0], stroke_width=2.5, color=GREY_B)
        axt = T("writes a second", 17, GREY_B).move_to([AXX + 0.35, BASE + H + 0.3, 0])
        labs = axis_labels([0, 100, 200], MX)
        self.steps("DynamoDB splits a payments table into partitions. Each one holds a range of key hashes, "
                   "and each has its own budget of writes.", [
            (lambda: [FadeIn(tbl, shift=0.1 * DOWN)], 0.7),
            "Each one holds",
            (lambda: [LaggedStart(*[FadeIn(hd[k], shift=0.1 * DOWN) for k in hd], lag_ratio=0.25)], 1.2),
            "and each has",
            (lambda: [Create(base), Create(ax), FadeIn(axt), FadeIn(labs)], 0.9),
        ])

        sh = {k: share(k, 100, MX) for k in (1, 2, 3, 4)}
        st = status("provisioned: 400 writes a second")
        self.steps("Provision 400 writes a second, and the four partitions each get an equal share, 100.", [
            (lambda: [FadeIn(st)], 0.6),
            "each get",
            (lambda: [LaggedStart(*[Create(sh[k]) for k in sh], lag_ratio=0.2)], 1.0),
        ])

        load = {1: 50, 2: 50, 3: 50, 4: 150}
        b = {k: bar(k, 0, 100, MX) for k in (1, 2, 3, 4)}
        for k in b:
            self.add(b[k])
        self.steps("But traffic is rarely even. Partition four gets 150 writes a second, and the others get 50 each.", [
            "Partition four",
            (lambda: [Transform(b[4], bar(4, 150, 1000, MX))], 1.0),
            "and the others",
            (lambda: [*[Transform(b[k], bar(k, 50, 100, MX)) for k in (1, 2, 3)]], 0.9),
        ])

        thr = T("refused: 50 a second", 19, RED_M).move_to([GX[4], yv(150, MX) + 0.32, 0])
        self.steps("Partition four can't pass its share, so DynamoDB refuses fifty writes a second, "
                   "while the table uses only 300 of its 400.", [
            (lambda: [Transform(b[4], bar(4, 150, 100, MX)), glow(hd[4][0], RED_M, 1.04)], 0.9),
            (lambda: [FadeIn(thr, shift=0.1 * UP)], 0.6),
            "while the table",
            (lambda: [Transform(st, status("used: 300 of 400", GOLD_M))], 0.8),
        ])

        s150 = T("share 150", 17, GOLD_M)
        self.steps("Adaptive capacity fixes this case. The table has unused units, "
                   "so DynamoDB raises partition four's share to 150.", [
            (lambda: [Indicate(st, color=GOLD_M, scale_factor=1.05)], 0.9),
            "so DynamoDB raises",
            (lambda: [sh[4].animate.move_to([GX[4], yv(150, MX), 0]), Transform(b[4], bar(4, 150, 150, MX)),
                      FadeOut(thr)], 1.0),
            (lambda: [FadeIn(s150.next_to(sh[4], RIGHT, buff=0.15))], 0.5),
        ])

        hd5 = header(5)
        sh5 = share(5, 150, MX)
        b5 = bar(5, 0, 150, MX)
        self.steps("If a partition stays busy, DynamoDB also splits it, at a key chosen from its traffic, "
                   "so the busy keys land on both halves.", [
            (lambda: [glow(hd[4][0], GOLD_M, 1.04)], 0.7),
            "splits it",
            (lambda: [FadeIn(hd5, shift=0.4 * RIGHT), FadeIn(sh5), FadeOut(s150)], 0.9),
            "so the busy",
            (lambda: [Transform(b[4], bar(4, 75, 150, MX)), Transform(b5, bar(5, 75, 150, MX))], 1.0),
        ])
        b[5] = b5
        sh[5] = sh5
        hd[5] = hd5

        # ---- one hot item ------------------------------------------------------------------------------------
        MX2 = 1600
        key = chip("total#m-17", RED_M, 18, mono=True).move_to([GX[5], 2.3, 0])
        labs2 = axis_labels([0, 500, 1000, 1500], MX2)
        self.steps("Now a single item gets hot: the running total for merchant m-17, written 1,500 times a second.", [
            (lambda: [FadeOut(VGroup(*sh.values())), Transform(labs, labs2), FadeOut(tbl),
                      *[Transform(b[k], bar(k, 50, 1000, MX2)) for k in (1, 2, 3)],
                      Transform(b[4], bar(4, 75, 1000, MX2)), Transform(b[5], bar(5, 75, 1000, MX2)),
                      Transform(st, status("provisioned: plenty"))], 1.0),
            "the running total",
            (lambda: [FadeIn(key, shift=0.1 * DOWN)], 0.6),
            "written 1,500",
            (lambda: [Transform(b[5], bar(5, 1500, 5000, MX2))], 1.1),
        ])

        cap = DashedLine([AXX + 0.1, yv(1000, MX2), 0], [5.6, yv(1000, MX2), 0], dash_length=0.1, stroke_width=3, color=RED_M)
        capl = T("every partition: at most 1,000", 18, RED_M).move_to([GX[2] - 0.6, yv(1000, MX2) + 0.28, 0])
        self.steps("Every partition has a hard ceiling of 1,000 writes a second. Borrowing from the table stops there.", [
            (lambda: [Create(cap), FadeIn(capl)], 1.0),
            "Borrowing",
            (lambda: [Transform(b[5], bar(5, 1500, 1000, MX2)), glow(hd[5][0], RED_M, 1.04)], 1.0),
        ])

        cut = DashedLine([GX[5] - 0.25, 2.62, 0], [GX[5] + 0.25, 1.98, 0], dash_length=0.08, stroke_width=3, color=GOLD_M)
        nocut = tick(False, 0.3).move_to([GX[5] + 1.25, 2.3, 0])
        own = box("x", GREEN_M, w=2.1, h=0.65, size=19).move_to([GX[5], HY, 0])
        own[1].become(M("only total#m-17", 14, WHITE).move_to(own[0]))
        self.steps("A split cuts a range of keys in two, but one key can't be cut. "
                   "DynamoDB can move the item into a partition of its own, and it still gets 1,000.", [
            (lambda: [Create(cut)], 0.7),
            "but one key",
            (lambda: [Create(nocut), FadeOut(cut)], 0.7),
            "DynamoDB can move",
            (lambda: [FadeOut(nocut), Transform(hd[5], own)], 0.9),
            "and it still",
            (lambda: [cap.animate(rate_func=there_and_back).set_stroke(width=6)], 0.9),
        ])

        thr2 = T("refused: 500 a second", 19, RED_M).move_to([GX[5] - 0.2, yv(1500, MX2) + 0.32, 0])
        self.steps("So 500 writes a second are refused, however much capacity the table has.", [
            (lambda: [FadeIn(thr2, shift=0.1 * UP), glow(hd[5][0], RED_M, 1.04)], 0.8),
            "however much",
            (lambda: [Transform(st, status("more capacity: no help", RED_M))], 0.8),
        ])

        self.steps("Every partition has a ceiling. DynamoDB moves capacity and splits ranges for you, "
                   "but one hot key you have to spread yourself.", [
            (lambda: [cap.animate(rate_func=there_and_back).set_stroke(width=6)], 0.9),
            "DynamoDB moves",
            (lambda: [*[glow(hd[k][0], PC[k], 1.04) for k in (1, 2, 3, 4)]], 0.9),
            "but one hot key",
            (lambda: [glow(key[0], RED_M, 1.08)], 0.9),
        ])
        self.wait(0.6)
