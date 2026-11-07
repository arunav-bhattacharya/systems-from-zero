from sfz import *


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Like Scene's, but never re-adds a group whose parts are already on screen (that would draw
        filled boxes over their own labels), and leaves introducers inside groups to add themselves on cue."""
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
        """Removing a group removes its parts too, even when the parts were added one by one."""
        fam = []
        for m in mobjects:
            fam.extend(m.get_family())
        return super().remove(*fam)

    def steps(self, text, steps, after=0.25):
        """Speak one line and play several animations one after another inside it. Each step is built
        just before it plays, so it starts from where the previous one ended."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        t = 0
        for fn, rt in steps:
            self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


SW, SH = 0.7, 0.62           # one key slot
LY, IY, RY = -1.3, 0.55, 2.35  # leaf, internal and root levels


def frame(color):
    r = RoundedRectangle(corner_radius=0.08, width=3 * SW, height=SH, stroke_color=color, stroke_width=3)
    divs = VGroup(*[Line([x, -SH / 2, 0], [x, SH / 2, 0], stroke_width=1.5, color=GREY_D) for x in (-SW / 2, SW / 2)])
    return VGroup(r, divs)


class Node:
    def __init__(self, x, y, color, hidden=True):
        self.f = frame(color).move_to([x, y, 0])
        self.children = []
        if hidden:
            self.f.set_stroke(opacity=0)

    def slot(self, i):
        return self.f[0].get_left() + (i + 0.5) * SW * RIGHT

    def show(self):
        return self.f.animate.set_stroke(opacity=1)


class BTreeSplit(Base):
    """dbi-04: inserts fill a leaf, the leaf splits, a separator is copied up, the root splits, a range scan."""

    def construct(self):
        self.title_card("A B+tree grows", "splits, separators and range scans")

        leaves, inner = [], []

        def edges():
            g = VGroup()
            for n in inner:
                left, bot = n.f[0].get_left()[0], n.f[0].get_bottom()[1]
                for k, c in enumerate(n.children):
                    op = min(n.f[0].get_stroke_opacity(), c.f[0].get_stroke_opacity())
                    g.add(Line([left + k * SW, bot, 0], c.f[0].get_top(), stroke_width=2, color=GREY_B).set_stroke(opacity=op))
            for a, b in zip(leaves, leaves[1:]):
                op = min(a.f[0].get_stroke_opacity(), b.f[0].get_stroke_opacity())
                g.add(Arrow(a.f[0].get_right(), b.f[0].get_left(), buff=0.05, stroke_width=2.5, color=BLUE_M,
                            max_tip_length_to_length_ratio=0.35, max_stroke_width_to_length_ratio=12).set_opacity(op))
            return g

        self.add(always_redraw(edges))

        def key(k, color=WHITE):
            return M(str(k), 22, color)

        def drop(n, i, k):
            m = key(k).move_to(n.slot(i))
            return m, FadeIn(m, shift=0.5 * DOWN)

        def over(n):
            """an extra red slot to the right of a full node, for the key that does not fit"""
            s = RoundedRectangle(corner_radius=0.08, width=SW, height=SH, stroke_color=RED_M, stroke_width=3)
            return s.move_to(n.slot(3))

        def leafgroup(n, *keys):
            return VGroup(n.f, *keys)

        L0 = Node(0, 0, BLUE_M, hidden=False)
        leaves.append(L0)
        note = T("one page, with room for 3 keys", 24, GREY_B).move_to([0, -1.0, 0])
        self.beat("An index keeps its keys sorted, in pages of a fixed size. In this toy tree a page holds three keys. "
                  "A real page of 8 kilobytes holds about 400.",
                  FadeIn(L0.f), FadeIn(note, shift=0.2 * UP), run_time=2.0)

        ks = {}
        anims = []
        for i, k in enumerate([10, 20, 30]):
            ks[k], a = drop(L0, i, k)
            anims.append(a)
        self.beat("Keys 10, 20 and 30 go into the page in order. Now it is full.",
                  Succession(*anims), run_time=3.0)

        ov = over(L0)
        ks[40] = key(40, RED_M).move_to(ov)
        self.play(FadeOut(note), FadeIn(ov), FadeIn(ks[40], shift=0.5 * DOWN), run_time=0.8)
        L1 = Node(1.3, 0, BLUE_M)
        leaves.append(L1)
        self.beat("Key 40 doesn't fit, and a page can't grow. So the page splits: a new page is made on its right, "
                  "and the upper half of the keys moves there.",
                  leafgroup(L0, ks[10], ks[20]).animate.set_x(-1.3), L1.show(), FadeOut(ov),
                  ks[30].animate.move_to(L1.slot(0)), ks[40].animate.move_to(L1.slot(1)).set_color(WHITE),
                  run_time=2.4)

        R0 = Node(0, IY, TEAL_M)
        R0.children = [L0, L1]
        inner.append(R0)
        sep = {30: key(30, TEAL_M).move_to(R0.slot(0))}
        self.beat("Now a search must know which page to read. So a new node is made above, holding one separator: "
                  "30, the new page's first key. Below 30, go left. 30 and up, go right.",
                  VGroup(L0.f, L1.f, ks[10], ks[20], ks[30], ks[40]).animate.shift(LY * UP),
                  R0.show(), TransformFromCopy(ks[30], sep[30]), run_time=2.4)
        self.beat("The 30 is copied up, not moved. The bottom pages, the leaves, must hold every key. "
                  "The node above holds only signposts.",
                  Indicate(ks[30], color=YELLOW_M), Indicate(sep[30], color=YELLOW_M), run_time=2.0)

        # 50 to 90: two more leaf splits, two more separators. Leaves keep a spacing of 2.6.
        L2, L3 = Node(2.6, LY, BLUE_M), Node(3.9, LY, BLUE_M)

        def s50():
            ks[50] = key(50).move_to(L1.slot(2))
            return [FadeIn(ks[50], shift=0.5 * DOWN)]

        def s60():
            leaves.append(L2)
            R0.children.append(L2)
            sep[50] = key(50, TEAL_M).move_to(R0.slot(1))
            ks[60] = key(60).move_to(L2.slot(1))
            return [leafgroup(L0, ks[10], ks[20]).animate.set_x(-2.6), leafgroup(L1, ks[30], ks[40]).animate.set_x(0),
                    L2.show(), ks[50].animate.move_to(L2.slot(0)), FadeIn(ks[60], shift=0.5 * DOWN),
                    TransformFromCopy(ks[50], sep[50])]

        def s70():
            ks[70] = key(70).move_to(L2.slot(2))
            return [FadeIn(ks[70], shift=0.5 * DOWN)]

        def s80():
            leaves.append(L3)
            R0.children.append(L3)
            sep[70] = key(70, TEAL_M).move_to(R0.slot(2))
            ks[80] = key(80).move_to(L3.slot(1))
            return [leafgroup(L0, ks[10], ks[20]).animate.set_x(-3.9), leafgroup(L1, ks[30], ks[40]).animate.set_x(-1.3),
                    leafgroup(L2, ks[50], ks[60]).animate.set_x(1.3), L3.show(), ks[70].animate.move_to(L3.slot(0)),
                    FadeIn(ks[80], shift=0.5 * DOWN), TransformFromCopy(ks[70], sep[70])]

        def s90():
            ks[90] = key(90).move_to(L3.slot(2))
            return [FadeIn(ks[90], shift=0.5 * DOWN)]

        self.steps("Keys 50 to 90 arrive. Each time a leaf is full, it splits the same way, "
                   "and one more separator is copied up.",
                   [(s50, 0.8), (s60, 1.8), (s70, 0.8), (s80, 1.8), (s90, 0.8)])

        # insert 100: the last leaf splits, 90 is copied up, and the node above overflows
        X5 = [-5.2, -2.6, 0.0, 2.6, 5.2]
        L4 = Node(X5[4], LY, BLUE_M)
        ov = over(L3)
        ks[100] = key(100, RED_M).move_to(ov)
        self.play(FadeIn(ov), FadeIn(ks[100], shift=0.5 * DOWN), run_time=0.8)
        leaves.append(L4)
        R0.children.append(L4)
        rov = over(R0)
        sep[90] = key(90, RED_M).move_to(rov)
        self.beat("Now insert 100. The last leaf is full, so it splits, and 90 is copied up. "
                  "But now the node above has four keys, one too many.",
                  leafgroup(L0, ks[10], ks[20]).animate.set_x(X5[0]), leafgroup(L1, ks[30], ks[40]).animate.set_x(X5[1]),
                  leafgroup(L2, ks[50], ks[60]).animate.set_x(X5[2]), leafgroup(L3, ks[70], ks[80]).animate.set_x(X5[3]),
                  FadeOut(ov), L4.show(), ks[90].animate.move_to(L4.f[0].get_left() + 0.5 * SW * RIGHT),
                  ks[100].animate.move_to(L4.f[0].get_left() + 1.5 * SW * RIGHT).set_color(WHITE),
                  Succession(Wait(1.4), AnimationGroup(FadeIn(rov), TransformFromCopy(ks[90], sep[90]))), run_time=3.2)

        # the node above splits: 70 is pushed up into a new root
        I1 = Node((X5[3] + X5[4]) / 2, IY, TEAL_M)
        R1 = Node((X5[1] + I1.f.get_x()) / 2, RY, TEAL_M)
        R0.children = [L0, L1, L2]
        I1.children = [L3, L4]
        R1.children = [R0, I1]
        inner.extend([I1, R1])
        self.beat("So it splits too. Its middle key, 70, moves up and is not kept below, because up here keys are only "
                  "signposts. Nothing is above it, so 70 becomes the new root.",
                  VGroup(R0.f, sep[30], sep[50]).animate.set_x(X5[1]), I1.show(), FadeOut(rov),
                  sep[90].animate.move_to(I1.slot(0)).set_color(TEAL_M), R1.show(), sep[70].animate.move_to(R1.slot(0)),
                  run_time=2.8)

        note = T("search for 60: 3 page reads", 24, GREY_B).move_to([0, -2.5, 0])
        path = Succession(Indicate(R1.f, color=YELLOW_M, run_time=0.8), Indicate(R0.f, color=YELLOW_M, run_time=0.8),
                          Indicate(L2.f, color=YELLOW_M, run_time=0.8), ks[60].animate(run_time=0.4).set_color(YELLOW_M))
        self.beat("That is the only way the tree gets taller: a new root on top. So every leaf is at the same depth, "
                  "and finding 60 reads one page per level: three pages.",
                  FadeIn(note), path, run_time=3.6)

        note2 = T("keys 40 to 70: 5 page reads", 24, GREY_B).move_to([0, -2.5, 0])
        down = Succession(Indicate(R1.f, color=YELLOW_M, run_time=0.6), Indicate(R0.f, color=YELLOW_M, run_time=0.6),
                          Indicate(L1.f, color=YELLOW_M, run_time=0.6), ks[40].animate(run_time=0.4).set_color(YELLOW_M))
        self.beat("The leaves are linked left to right, which makes ranges cheap. To read keys 40 to 70, "
                  "the search goes down once, to the leaf with 40.",
                  ks[60].animate.set_color(WHITE), Transform(note, note2), down, run_time=3.0)
        walk = Succession(Indicate(L2.f, color=YELLOW_M, run_time=0.6),
                          AnimationGroup(ks[50].animate.set_color(YELLOW_M), ks[60].animate.set_color(YELLOW_M), run_time=0.5),
                          Indicate(L3.f, color=YELLOW_M, run_time=0.6), ks[70].animate(run_time=0.4).set_color(YELLOW_M),
                          ks[80].animate(run_time=0.4).set_color(RED_M))
        self.beat("Then it walks right along the links, and stops at 80, the first key above 70.",
                  walk, run_time=3.4)

        self.beat("A real page holds about 400 keys. So three levels hold 64 million keys, "
                  "and any one of them is three page reads away.",
                  *[ks[k].animate.set_color(WHITE) for k in (40, 50, 60, 70, 80)],
                  Indicate(VGroup(R1.f, R0.f, I1.f), color=TEAL_M, scale_factor=1.05), run_time=2.0)
        self.wait(0.6)
