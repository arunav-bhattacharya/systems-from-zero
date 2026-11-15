from sfz import *

LEVEL_Y = [2.45, 1.2, -0.05, -1.25]       # root, two children, four, eight leaves
NW, NH = 1.3, 0.78                        # node box
BAD = {(0, 0), (1, 1), (2, 3), (3, 6)}    # the path down to r6
HASH = {(0, 0): ("9e41", "52c7"), (1, 0): ("a3f9", "a3f9"), (1, 1): ("7c21", "0d8e"),
        (2, 0): ("41bd", "41bd"), (2, 1): ("e07a", "e07a"), (2, 2): ("5f12", "5f12"), (2, 3): ("c88e", "16a4"),
        (3, 0): ("2b6d", "2b6d"), (3, 1): ("90fa", "90fa"), (3, 2): ("d417", "d417"), (3, 3): ("6ec3", "6ec3"),
        (3, 4): ("3a95", "3a95"), (3, 5): ("f20b", "f20b"), (3, 6): ("8d5e", "b731"), (3, 7): ("17c4", "17c4")}
BAR_Y, FOOT_Y = -2.45, -3.3


def leaf_x(j):
    return -5.775 + j * 1.65


def node_x(l, i):
    span = 2 ** (3 - l)
    return (leaf_x(i * span) + leaf_x((i + 1) * span - 1)) / 2


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




def node(l, i):
    x, y = node_x(l, i), LEVEL_Y[l]
    a, b = HASH[(l, i)]
    r = RoundedRectangle(corner_radius=0.1, width=NW, height=NH, stroke_color=GREY_B, stroke_width=2.5)
    r.set_fill(BLACK, 1).move_to([x, y, 0])
    return VGroup(r, M(a, 21, BLUE_M).move_to([x, y + 0.17, 0]), M(b, 21, GOLD_M).move_to([x, y - 0.17, 0]))


def edge(l, i, k):
    p = np.array([node_x(l, i), LEVEL_Y[l] - NH / 2, 0])
    c = np.array([node_x(l + 1, 2 * i + k), LEVEL_Y[l + 1] + NH / 2, 0])
    return Line(p, c, stroke_width=2, color=GREY_D)


def store(title, sub, x, color):
    r = RoundedRectangle(corner_radius=0.14, width=4.1, height=1.05, stroke_color=color, stroke_width=3)
    r.set_fill(fill(color), 1).move_to([x, 2.85, 0])
    return VGroup(r, T(title, 24, color).move_to([x, 3.07, 0]), T(sub, 18, GREY_B).move_to([x, 2.66, 0]))


def counter(n, color=WHITE):
    return right_at(T(f"comparisons: {n}", 24, color), 6.45, FOOT_Y)


class MerkleAudit(Base):
    """derive-05, section 2: a live balances view of 50 million rows and a view recomputed from the log should match. Each
    side cuts the keys into 8 ranges, hashes each range and then pairs of hashes up to a root. Comparing roots, then only
    children that differ, finds the one bad range (r6) in 7 comparisons; only r6's rows are diffed. With 1,024 ranges it is
    1 + 2 x 10 = 21 comparisons. Hash values are made up 4-digit stand-ins for SHA-256."""

    def construct(self):
        self.title_card("Auditing with a Merkle tree", "compare hashes, and go down only where they differ")

        live = store("live view", "serving database, 50 million rows", -4.45, BLUE_M)
        reco = store("recomputed view", "warehouse, 50 million rows", 4.45, GOLD_M)
        link = DashedLine([-2.3, 2.85, 0], [2.3, 2.85, 0], dash_length=0.1, stroke_width=2.5, color=GREY_B)
        netl = T("network", 18, GREY_B).next_to(link, UP, buff=0.12)
        self.steps("The live balances view has fifty million rows. An audit job recomputes the same view from the log, "
                   "in the warehouse. The two should match exactly.", [
            (lambda: [FadeIn(live, shift=0.1 * RIGHT)], 0.8),
            "An audit job",
            (lambda: [FadeIn(reco, shift=0.1 * LEFT)], 0.8),
            "The two should",
            (lambda: [Create(link), FadeIn(netl)], 0.7),
        ])

        sent = ValueTracker(0)
        sent_t = always_redraw(lambda: T(f"rows sent: {int(sent.get_value()):,}", 22, RED_M).move_to([0, 2.3, 0]))
        self.steps("Somewhere, one balance is off by a single flipped bit. Comparing row by row means sending "
                   "all fifty million rows across the network, on every audit.", [
            "Comparing row by row",
            (lambda: [FadeIn(sent_t)], 0.3),
            (lambda: [sent.animate(rate_func=linear).set_value(50_000_000),
                      LaggedStart(*[flow(link, RED_M, 0.5) for _ in range(12)], lag_ratio=0.25)], 2.6),
            "on every audit",
            (lambda: [glow(live[0], RED_M, 1.03), glow(reco[0], RED_M, 1.03)], 0.9),
        ])
        sent_t.clear_updaters()

        # ---- leaves: ranges and their hashes -------------------------------------------------------------------
        nodes = {(l, i): node(l, i) for l in range(4) for i in range(2 ** l)}
        edges = {(l, i, k): edge(l, i, k) for l in range(3) for i in range(2 ** l) for k in (0, 1)}
        seg = [RoundedRectangle(corner_radius=0.05, width=1.55, height=0.36, stroke_color=GREY_C, stroke_width=2)
               .set_fill(fill(GREY_B, 0.1), 1).move_to([leaf_x(j), BAR_Y, 0]) for j in range(8)]
        rl = [T(f"r{j}", 20, GREY_B).move_to([leaf_x(j), -1.85, 0]) for j in range(8)]
        foot = left_at(T("50 million rows, cut into 8 ranges by a hash of the key", 20, GREY_B), -6.45, FOOT_Y)
        self.steps("Instead, each side cuts its keys into ranges, here eight, and hashes all the rows in each range. "
                   "If the rows match, the hashes match. Each box shows both sides, live on top.", [
            (lambda: [FadeOut(sent_t), FadeOut(link), FadeOut(netl), LaggedStart(*[FadeIn(s) for s in seg], lag_ratio=0.1),
                      LaggedStart(*[FadeIn(r) for r in rl], lag_ratio=0.1), FadeIn(foot)], 1.2),
            "and hashes",
            (lambda: [LaggedStart(*[FadeIn(nodes[(3, j)], shift=0.1 * UP) for j in range(8)], lag_ratio=0.12)], 1.4),
            "If the rows match",
            (lambda: [glow(nodes[(3, 0)][0], GREEN_M, 1.05), glow(nodes[(3, 1)][0], GREEN_M, 1.05)], 0.9),
            "Each box",
            (lambda: [*[Indicate(nodes[(3, j)][1], color=BLUE_M, scale_factor=1.15) for j in range(8)]], 0.9),
        ])

        def build(l):
            return [*[Create(edges[(l, i, k)]) for i in range(2 ** l) for k in (0, 1)],
                    *[FadeIn(nodes[(l, i)], shift=0.1 * UP) for i in range(2 ** l)]]

        self.steps("Then each side hashes pairs of hashes, level by level, up to a single root. "
                   "This is a Merkle tree.", [
            (lambda: build(2), 0.8),
            (lambda: build(1), 0.7),
            (lambda: build(0), 0.7),
            "This is a Merkle tree",
            (lambda: [glow(nodes[(0, 0)][0], WHITE, 1.06)], 0.8),
        ])

        cnt = counter(0)

        def compare(keys, n):
            out = []
            for key in keys:
                c = RED_M if key in BAD else GREEN_M
                out.append(nodes[key][0].animate.set_stroke(c, width=4).set_fill(fill(c), 1))
            out.append(Transform(cnt, counter(n)))
            return out

        def dim(l, i):
            """Fade everything below node (l, i): it matched, so nobody looks there."""
            ms = []
            for ll in range(l + 1, 4):
                span = 2 ** (ll - l)
                for ii in range(i * span, (i + 1) * span):
                    ms.append(nodes[(ll, ii)])
                    pl, pi = ll - 1, ii // 2
                    ms.append(edges[(pl, pi, ii % 2)])
            return [m.animate.set_opacity(0.25) for m in ms]

        self.steps("Now the two sides exchange one hash each: the root. They differ, so the views differ somewhere. "
                   "One comparison.", [
            (lambda: [FadeIn(cnt)], 0.4),
            "exchange one hash",
            (lambda: [flow(Line(live.get_right(), nodes[(0, 0)].get_left()), BLUE_M, 0.6),
                      flow(Line(reco.get_left(), nodes[(0, 0)].get_right()), GOLD_M, 0.6)], 0.7),
            "They differ",
            (lambda: compare([(0, 0)], 1), 0.7),
        ])

        self.steps("Compare the root's two children. The left one matches, so half the ranges are identical, "
                   "and nothing below it is looked at. Three comparisons.", [
            (lambda: compare([(1, 0), (1, 1)], 3), 0.8),
            "and nothing below",
            (lambda: dim(1, 0) + [rl[j].animate.set_opacity(0.3) for j in range(4)] + [seg[j].animate.set_opacity(0.3) for j in range(4)], 1.0),
        ])

        self.steps("Under the right child, the left one matches and the right one differs. Five.", [
            (lambda: compare([(2, 2), (2, 3)], 5), 0.8),
            (lambda: dim(2, 2) + [rl[j].animate.set_opacity(0.3) for j in (4, 5)] + [seg[j].animate.set_opacity(0.3) for j in (4, 5)], 0.9),
        ])

        found = T("found: r6", 22, RED_M).move_to([leaf_x(6), -1.85, 0])
        self.steps("At the bottom, range six differs and range seven matches. "
                   "Seven comparisons found the one bad range out of eight.", [
            (lambda: compare([(3, 6), (3, 7)], 7), 0.8),
            "Seven comparisons",
            (lambda: [Transform(rl[6], found), rl[7].animate.set_opacity(0.3), seg[7].animate.set_opacity(0.3),
                      seg[6].animate.set_stroke(RED_M, width=3)], 0.8),
        ])

        r6link = Line([leaf_x(6), BAR_Y + 0.2, 0], [leaf_x(6), BAR_Y - 0.2, 0])
        foot2 = left_at(T("rows diffed: range 6 only, about 6 million of 50", 20, RED_M), -6.45, FOOT_Y)
        self.steps("Only now do rows cross the network, and only the rows in range six: an eighth of them.", [
            "Only now",
            (lambda: [Transform(foot, foot2), glow(seg[6], RED_M, 1.08)], 0.9),
            "an eighth",
            (lambda: [*[flow(Line(seg[6].get_left() + 0.1 * RIGHT, seg[6].get_right() + 0.1 * LEFT), RED_M, 0.5)]], 0.7),
        ])

        big = chip("1,024 ranges: 1 + 2 × 10 = 21 comparisons, then about 50,000 rows", GREEN_M, 21)
        big.move_to([-0.6, FOOT_Y, 0])
        self.steps("Each level costs two comparisons. With a thousand and twenty four ranges, the walk takes twenty one "
                   "comparisons, and leaves about fifty thousand rows to diff, not fifty million.", [
            (lambda: [glow(nodes[(1, 1)][0], RED_M, 1.05), glow(nodes[(2, 3)][0], RED_M, 1.05)], 0.9),
            "With a thousand",
            (lambda: [FadeOut(foot), FadeOut(cnt), FadeIn(big, shift=0.1 * UP)], 0.8),
        ])

        self.steps("The cost grows with the number of ranges that differ, not with the size of the view. "
                   "If most ranges differ, a plain scan is cheaper.", [
            (lambda: [glow(live[0], BLUE_M, 1.03), glow(reco[0], GOLD_M, 1.03)], 1.0),
            "If most ranges",
            (lambda: [*[glow(s, GREY_B, 1.06) for s in seg]], 1.0),
        ])

        path = [nodes[k][0] for k in sorted(BAD)]
        self.steps("Exchange hashes, not rows, and go down only where the hashes differ.", [
            (lambda: [glow(nodes[(0, 0)][0], YELLOW_M, 1.06), glow(live[0], BLUE_M, 1.03), glow(reco[0], GOLD_M, 1.03)], 0.9),
            "go down only",
            (lambda: [Succession(*[glow(p, RED_M, 1.06) for p in path[1:]], run_time=1.4)], 1.4),
        ])
        self.wait(0.6)
