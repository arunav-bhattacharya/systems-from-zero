from sfz import *

XS = [-4.65, -1.55, 1.55, 4.65]
SY, SW, SH = -1.1, 2.7, 2.2           # row shards
IY, IH = 1.55, 0.9                    # index shards (global index)
FC = np.array([0, 3.15, 0])           # the fraud check
ROWS = {0: [("pay-118", "F"), ("pay-204", "A")], 1: [("pay-342", "F"), ("pay-415", "C")],
        2: [("pay-263", "B"), ("pay-530", "D")], 3: [("pay-577", "F"), ("pay-611", "A")]}
LOCAL = {0: "F → pay-118", 1: "F → pay-342", 2: "F → none", 3: "F → pay-577"}
GLOBAL = {0: "A → 204, 611", 1: "F → 118, 342, 577", 2: "B → 263, C → 415", 3: "D → 530"}
LAT = [2, 3, 2, 50]                   # this check's replies, in ms


def fillc(color, a=0.14):
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
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def row_y(j):
    return SY + 0.35 - 0.35 * j


def row(i, j, pid, card):
    color = GOLD_M if card == "F" else GREY_B
    return M(f"{pid}  card {card}", 15, color).move_to([XS[i], row_y(j), 0])


def shard(i):
    x = XS[i]
    r = RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([x, SY, 0])
    title = left_at(T(f"shard {i}", 22), x - SW / 2 + 0.2, SY + SH / 2 - 0.3)
    rows = VGroup(*[row(i, j, p, c) for j, (p, c) in enumerate(ROWS[i])])
    return VGroup(r, title, rows)


def strip(i, color=TEAL_M):
    x, y = XS[i], SY - 0.8
    r = RoundedRectangle(corner_radius=0.08, width=SW - 0.3, height=0.42, stroke_color=color, stroke_width=2).set_fill(fillc(color), 1)
    r.move_to([x, y, 0])
    return VGroup(r, M(f"index: {LOCAL[i]}", 14, WHITE).move_to([x, y, 0]))


def ishard(i, text=None, color=TEAL_M):
    x = XS[i]
    r = RoundedRectangle(corner_radius=0.12, width=SW, height=IH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, IY, 0])
    return VGroup(r, T(f"index shard {i}", 20).move_to([x, IY + 0.2, 0]),
                  fit(M(text or GLOBAL[i], 14, GREY_A), SW - 0.5).move_to([x, IY - 0.2, 0]))


def line(a, b, color=GREY_B, sw=2.5):
    return Line(a, b, stroke_width=sw, color=color)


def back(l, color, rt):
    return travel(Line(l.get_end(), l.get_start()), color, rt)


class SecondaryIndexes(Base):
    """shard-04, sections 0 to 2: payments hash-sharded by id over four shards; the fraud check wants card F's payments
    (on shards 0, 1 and 3). A local index per shard: one shard per write, every shard per read, and the read waits for
    the slowest (2, 3, 2 and 50 ms). A global index split by card: one index shard per read, but the entry for a new
    payment is written after the payment, so a check right after it finds 3 of 4."""

    def construct(self):
        self.title_card("Secondary indexes across shards", "local or global, and what each one costs")

        sh = [shard(i) for i in range(4)]
        fc = box("fraud check", WHITE, w=2.4, h=0.62, size=22).move_to(FC)
        self.steps("The payments table is split across four shards by payment id. The fraud check needs every payment "
                   "card F made in the last hour. They were placed by id, so they're scattered.", [
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.1 * UP) for s in sh], lag_ratio=0.15)], 1.3),
            "The fraud check",
            (lambda: [FadeIn(fc, shift=0.1 * DOWN)], 0.6),
            "They were placed",
            (lambda: [*[glow(sh[i][0], GOLD_M) for i in (0, 1, 3)]], 1.0),
        ])

        q = left_at(T("which payments has card F made?", 20, GOLD_M), 1.45, FC[1])
        self.steps("Finding rows by card needs an index on card, a secondary index. Where should its entries live?", [
            (lambda: [FadeIn(q, shift=0.1 * LEFT)], 0.7),
            "Where should",
            (lambda: [glow(fc[0], GOLD_M, 1.06)], 0.9),
        ])

        st = [strip(i) for i in range(4)]
        loc = left_at(T("local index: one per shard", 20, TEAL_M), -6.6, FC[1])
        self.steps("The simplest answer: each shard indexes its own rows. That's a local index. "
                   "A payment and its index entry go to the same shard, so they always agree.", [
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.1 * UP) for s in st], lag_ratio=0.15), FadeOut(q)], 1.2),
            "That's a local",
            (lambda: [FadeIn(loc)], 0.6),
            "A payment and",
            (lambda: [glow(st[0][0], TEAL_M, 1.05), glow(sh[0][0], TEAL_M, 1.02)], 0.9),
        ])

        asks = [line(FC + 0.32 * DOWN + (i - 1.5) * 0.25 * RIGHT, [XS[i], SY + SH / 2, 0]) for i in range(4)]
        self.steps("But shard 1's index knows nothing about shard 3's rows. So the fraud check has to ask all four "
                   "shards, even shard 2, which has none.", [
            (lambda: [glow(st[1][0], TEAL_M, 1.05)], 0.8),
            "So the fraud check",
            (lambda: [*[Create(a) for a in asks]], 0.6),
            (lambda: [*[travel(a, GOLD_M, 0.7) for a in asks]], 0.7),
            "even shard 2",
            (lambda: [glow(sh[2][0], GREY_B), glow(st[2][0], TEAL_M, 1.05)], 0.9),
        ])

        lat = [right_at(T(f"{LAT[i]} ms", 20, RED_M if LAT[i] > 10 else GREEN_M), XS[i] + SW / 2 - 0.2, SY + SH / 2 - 0.3)
               for i in range(4)]
        took = left_at(T("check took 50 ms", 20, RED_M), 1.45, FC[1])
        self.steps("Then it waits for the slowest. Three answer in 2 or 3 milliseconds. This time one takes 50, "
                   "so the whole check takes 50.", [
            "Three answer",
            (lambda: [*[back(asks[i], GREEN_M, 0.6) for i in range(3)], *[FadeIn(lat[i]) for i in range(3)]], 0.7),
            "This time",
            (lambda: [back(asks[3], RED_M, 1.6), FadeIn(lat[3])], 1.6),
            "so the whole",
            (lambda: [FadeIn(took, shift=0.1 * LEFT), sh[3][0].animate.set_stroke(RED_M)], 0.7),
        ])

        tail = left_at(T("asking 10 shards: about 1 check in 10 is slow", 20, RED_M), 1.45, FC[1])
        self.steps("If each shard is slow one time in a hundred, a check that asks ten shards waits on a slow one "
                   "about one time in ten.", [
            "a check that asks ten",
            (lambda: [Transform(took, tail)], 0.8),
        ])

        # ---- global index -------------------------------------------------------------------------------------------
        ix = [ishard(i) for i in range(4)]
        glob = left_at(T("global index: split by card", 20, TEAL_M), -6.6, FC[1])
        self.steps("Turn the index around. A global index is split by card, not by payment id. "
                   "All of card F's entries live on one index shard.", [
            (lambda: [*[FadeOut(a) for a in asks], *[FadeOut(l) for l in lat], FadeOut(took), FadeOut(loc),
                      sh[3][0].animate.set_stroke(WHITE), *[s.animate.set_opacity(0.25) for s in st]], 0.8),
            (lambda: [LaggedStart(*[FadeIn(x, shift=0.1 * DOWN) for x in ix], lag_ratio=0.15), FadeIn(glob)], 1.2),
            "All of card F's",
            (lambda: [ix[1][0].animate.set_stroke(GOLD_M), ix[1][2].animate.set_color(GOLD_M)], 0.6),
            (lambda: [glow(ix[1][0], GOLD_M, 1.05)], 0.8),
        ])

        to_ix = line(FC + 0.32 * DOWN + 0.3 * LEFT, [XS[1] + 0.3, IY + IH / 2, 0], GOLD_M)
        fetch = [line([XS[1], IY - IH / 2, 0], [XS[i], SY + SH / 2, 0], GOLD_M) for i in (0, 1, 3)]
        one = left_at(T("asks 1 index shard", 20, GOLD_M), 1.45, FC[1])
        self.steps("Now the check asks that one index shard, gets three payment ids, and fetches just those rows.", [
            (lambda: [Create(to_ix), FadeIn(one)], 0.6),
            (lambda: [travel(to_ix, GOLD_M, 0.6)], 0.6),
            "gets three",
            (lambda: [back(to_ix, GOLD_M, 0.6)], 0.6),
            "and fetches",
            (lambda: [*[Create(f) for f in fetch]], 0.5),
            (lambda: [*[travel(f, GOLD_M, 0.6) for f in fetch]], 0.6),
            (lambda: [*[glow(sh[i][0], GOLD_M) for i in (0, 1, 3)]], 0.7),
        ])

        new = chip("pay-901  card F", BLUE_M, 16, mono=True).move_to([XS[2], -3.3, 0])
        new_row = row(2, 2, "pay-901", "F")
        upath = Line([XS[2] - 0.5, SY + SH / 2, 0], [XS[1] + 0.5, IY - IH / 2, 0])
        upd = DashedLine(upath.get_start(), upath.get_end(), dash_length=0.1, stroke_width=2.5, color=BLUE_M)
        self.steps("The cost moves to the write. A new payment for card F lands on row shard 2, but its index entry "
                   "belongs on index shard 1, another machine.", [
            (lambda: [FadeOut(to_ix), *[FadeOut(f) for f in fetch], FadeOut(one)], 0.5),
            "A new payment",
            (lambda: [FadeIn(new, shift=0.2 * UP)], 0.5),
            (lambda: [ReplacementTransform(new, new_row)], 0.8),
            "but its index",
            (lambda: [Create(upd)], 0.8),
        ])

        dot = Dot(radius=0.09, color=BLUE_M).move_to(upath.get_start())
        later = left_at(T("index updated after the write", 20, BLUE_M), 1.45, FC[1])
        self.steps("Stores like DynamoDB update that index in the background, after the write has already succeeded.", [
            (lambda: [FadeIn(later, shift=0.1 * LEFT), glow(sh[2][0], GREEN_M)], 0.8),
            "in the background",
            (lambda: [FadeIn(dot), dot.animate(rate_func=linear).move_to(upath.point_from_proportion(0.3))], 1.6),
        ])

        miss = left_at(T("found 3 payments, missed pay-901", 20, RED_M), 1.45, FC[1])
        self.steps("So a check that runs right after the payment reads the index too early. It finds three payments, "
                   "and misses the new one.", [
            (lambda: [dot.animate(rate_func=linear).move_to(upath.point_from_proportion(0.5)), FadeOut(later)], 1.0),
            (lambda: [Create(to_ix), dot.animate(rate_func=linear).move_to(upath.point_from_proportion(0.6))], 0.6),
            (lambda: [travel(to_ix, GOLD_M, 0.6), dot.animate(rate_func=linear).move_to(upath.point_from_proportion(0.7))], 0.6),
            "It finds three",
            (lambda: [back(to_ix, RED_M, 0.6), FadeIn(miss, shift=0.1 * LEFT),
                      dot.animate(rate_func=linear).move_to(upath.point_from_proportion(0.78))], 0.7),
            (lambda: [new_row.animate(rate_func=there_and_back).set_color(RED_M)], 0.8),
        ])

        ix1b = ishard(1, "F → 118, 342, 577, 901", GOLD_M)
        ix1b[2].set_color(GOLD_M)
        seen = left_at(T("next check: finds all 4", 20, GREEN_M), 1.45, FC[1])
        self.steps("A fraction of a second later the entry arrives, and the next check sees all four.", [
            (lambda: [dot.animate(rate_func=linear).move_to(upath.get_end())], 0.8),
            (lambda: [FadeOut(dot), Transform(ix[1], ix1b), FadeOut(upd)], 0.6),
            "and the next",
            (lambda: [travel(to_ix, GOLD_M, 0.5), Transform(miss, seen)], 0.6),
            (lambda: [back(to_ix, GREEN_M, 0.5)], 0.5),
        ])

        self.steps("A local index stays in step with its rows, but every read asks every shard. "
                   "A global index answers from one shard, but it can lag behind the write.", [
            (lambda: [FadeOut(to_ix), FadeOut(miss), *[s.animate.set_opacity(1) for s in st]], 0.6),
            (lambda: [Transform(st[2][1], M("index: F → pay-901", 14, WHITE).move_to(st[2][1]))], 0.5),
            (lambda: [*[glow(s[0], TEAL_M, 1.05) for s in st]], 0.9),
            "A global index",
            (lambda: [*[s.animate.set_opacity(0.25) for s in st], glow(ix[1][0], GOLD_M, 1.05)], 0.9),
            "but it can lag",
            (lambda: [glow(sh[2][0], BLUE_M)], 0.9),
        ])
        self.wait(0.6)
