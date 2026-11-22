from sfz import *

# Said the way people say them; captions keep "12.40", "SHA-256" and "1,024".
SAY.insert(0, (r"\b12\.40\b", "twelve forty"))
SAY.insert(0, (r"\bSHA-256\b", "shah two fifty six"))
SAY.insert(0, (r"\b1,024\b", "one thousand and twenty four"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
LEVEL_Y = [2.45, 1.2, -0.05, -1.25]       # root, two children, four, eight leaves
NW, NH = 1.3, 0.78                        # node box
BAD = {(0, 0), (1, 1), (2, 3), (3, 6)}    # the path down to r6
HASH = {(0, 0): ("9e41", "52c7"), (1, 0): ("a3f9", "a3f9"), (1, 1): ("7c21", "0d8e"),
        (2, 0): ("41bd", "41bd"), (2, 1): ("e07a", "e07a"), (2, 2): ("5f12", "5f12"), (2, 3): ("c88e", "16a4"),
        (3, 0): ("2b6d", "2b6d"), (3, 1): ("90fa", "90fa"), (3, 2): ("d417", "d417"), (3, 3): ("6ec3", "6ec3"),
        (3, 4): ("3a95", "3a95"), (3, 5): ("f20b", "f20b"), (3, 6): ("8d5e", "b731"), (3, 7): ("17c4", "17c4")}
BAR_Y, RL_Y, FOOT_Y = -2.45, -1.85, -3.3
STORE_Y = 2.85
CD_Y = 3.3                                # countdown bar, between the two stores


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

    def steps(self, text, items, after=0.3):
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


def glow(m, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(a, b, color=YELLOW_M, run_time=0.8):
    """A dot that runs from a to b."""
    d = Dot(radius=0.075, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d, run_time=0.25), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


# ---- the pieces ----
def node(l, i, pair=None):
    x, y = node_x(l, i), LEVEL_Y[l]
    a, b = pair or HASH[(l, i)]
    r = RoundedRectangle(corner_radius=0.1, width=NW, height=NH, stroke_color=GREY_B, stroke_width=2.5)
    r.set_fill(BLACK, 1).move_to([x, y, 0])
    return VGroup(r, M(a, 21, BLUE_M).move_to([x, y + 0.17, 0]), M(b, 21, GOLD_M).move_to([x, y - 0.17, 0]))


def edge(l, i, k):
    p = np.array([node_x(l, i), LEVEL_Y[l] - NH / 2, 0])
    c = np.array([node_x(l + 1, 2 * i + k), LEVEL_Y[l + 1] + NH / 2, 0])
    return Line(p, c, stroke_width=2, color=GREY_D)


def store(title, sub, x, color):
    r = RoundedRectangle(corner_radius=0.14, width=4.1, height=1.05, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, STORE_Y, 0])
    return VGroup(r, T(title, 24, color).move_to([x, STORE_Y + 0.22, 0]), T(sub, 18, GREY_B).move_to([x, STORE_Y - 0.19, 0]))


class MerkleAudit(Base):
    """derive-05, section 2. The café owner was paid 12.40 too little; an audit rebuilds the balances from the log and
    compares them with the live view, but each view has 50 million rows on different machines. A hash (SHA-256, 32
    bytes) is a fingerprint; one hash per view says whether, not where. Two libraries on the phone narrowing down wing,
    room, shelf. A Merkle tree over 8 ranges: the walk finds r6 in 7 comparisons; only r6's rows are compared. With
    1,024 ranges, 1 + 2 x 10 = 21. The lab: 17, 101, 369 comparisons for 1, 10, 100 bad accounts in 256 ranges, so when
    most ranges differ a plain scan is cheaper. Hash values are made-up stand-ins for SHA-256."""

    def put(self, key, new, d=UP):
        old = self.lab.get(key)
        self.lab[key] = new
        return [swap(old, new, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            old = self.lab.pop(k, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def cap(self, s, color=GREY_B, size=22):
        return self.put("cap", T(s, size, color).move_to([0, FOOT_Y, 0]))

    def foot(self, s, color=GREY_B):
        return self.put("foot", left_at(T(s, 20, color), -6.45, FOOT_Y))

    def count(self, n, color=WHITE):
        return self.put("cnt", right_at(T(f"comparisons: {n}", 24, color), 6.45, FOOT_Y))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, CD_Y, 0], [1.0, CD_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.lab = {}
        self.title_card("One bad row in fifty million", "a tree of hashes finds it")

        # ---------------- scene 1: the question ----------------
        live = store("live view", "serves the app, 50 million rows", -4.45, BLUE_M)
        reco = store("rebuilt view", "warehouse, 50 million rows", 4.45, GOLD_M)
        link = DashedLine([-2.3, STORE_Y, 0], [2.3, STORE_Y, 0], dash_length=0.1, stroke_width=2.5, color=GREY_B)
        netl = T("network", 18, GREY_B).next_to(link, DOWN, buff=0.15)
        self.steps("Picture a café owner who was paid 12.40 too little, while every program reported success.", [
            "paid 12.40",
            (lambda: self.cap("paid 12.40 too little; every program said success", RED_M, 26), 0.7),
        ])
        self.steps("One way to catch that: work the balances out again from the log, the list of every payment, "
                   "and compare them with the live ones, account by account.", [
            "work the balances",
            (lambda: self.cap("the audit: rebuild the balances from the log, compare them with the live ones", WHITE), 0.6),
        ])
        self.steps("Now make it real. The live view has 50 million rows, in the database that serves the app.", [
            "The live view",
            (lambda: [FadeIn(live, shift=0.1 * RIGHT)], 0.8),
        ])
        self.steps("The rebuilt view sits in the warehouse, a separate database kept for analysis, on other machines.", [
            "The rebuilt view",
            (lambda: [FadeIn(reco, shift=0.1 * LEFT)], 0.8),
            "on other machines",
            (lambda: [Create(link), FadeIn(netl)], 0.7),
        ])
        self.steps("Somewhere one balance is off. How do you find it without sending fifty million rows across the network? "
                   "Hold that question.", [
            (lambda: self.cap("one balance is off. which one?", YELLOW_M, 26), 0.6),
            "without sending",
            (lambda: [glow(live[0], BLUE_M, 1.03), glow(reco[0], GOLD_M, 1.03)], 0.9),
        ])

        # ---------------- scene 2: row by row ----------------
        sent = ValueTracker(0)
        sent_t = always_redraw(lambda: T(f"rows sent: {int(sent.get_value()):,}", 24, RED_M).move_to([0, 1.7, 0]))
        a, b = link.get_start(), link.get_end()
        self.steps("The plain way is row by row. Every check sends all fifty million rows across, to find one bad balance.", [
            (lambda: self.drop("cap"), 0.3),
            "Every check",
            (lambda: [FadeIn(sent_t)], 0.3),
            (lambda: [sent.animate(rate_func=linear).set_value(50_000_000),
                      LaggedStart(*[flow(a, b, RED_M, 0.5) for _ in range(12)], lag_ratio=0.25)], 2.6),
        ])
        sent_t.clear_updaters()
        self.steps("That's two libraries checking they hold the same books by reading every page to each other over the phone. "
                   "Bring snacks.", [
            "two libraries",
            (lambda: self.cap("two libraries, reading every page to each other over the phone", RED_M), 0.6),
        ])
        self.steps("What we want is a fingerprint for data: something short that the two sides can compare instead.", [
            "a fingerprint",
            (lambda: [*self.cap("wanted: a short fingerprint to compare instead", YELLOW_M), FadeOut(sent_t)], 0.6),
        ])

        # ---------------- scene 3: a fingerprint ----------------
        rows = VGroup(*[RoundedRectangle(corner_radius=0.04, width=2.0, height=0.22, stroke_color=GREY_B, stroke_width=2)
                        .set_fill(fillc(GREY_B, 0.12), 1).move_to([-4.0, 0.95 - 0.33 * i, 0]) for i in range(6)])
        rows_l = T("the data", 20, GREY_B).move_to([-4.0, 1.4, 0])
        hbox = VGroup(RoundedRectangle(corner_radius=0.12, width=2.6, height=1.1, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1),
                      ).move_to([0, 0.15, 0])
        hbox.add(T("hash function", 22).move_to([0, 0.35, 0]), M("SHA-256", 18, GREY_B).move_to([0, -0.05, 0]))
        ar1 = Arrow([-2.85, 0.15, 0], [-1.4, 0.15, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.15)
        ar2 = Arrow([1.4, 0.15, 0], [2.85, 0.15, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.15)
        out_l = T("its hash: 32 bytes", 18, GREY_B).move_to([4.0, 0.75, 0])

        def hout(s, color):
            return self.put("hout", M(s, 34, color).move_to([4.0, 0.15, 0]))

        self.steps("There's a tool for that, called a hash function. SHA-256 is a widely used one.", [
            (lambda: self.drop("cap"), 0.3),
            "a hash function",
            (lambda: [FadeIn(hbox, shift=0.1 * UP)], 0.7),
            "SHA-256",
            (lambda: [glow(hbox[0], WHITE, 1.04)], 0.7),
        ])
        self.steps("It turns any amount of data into a short number of a fixed size, 32 bytes, called its hash.", [
            "any amount",
            (lambda: [FadeIn(rows), FadeIn(rows_l), GrowArrow(ar1)], 0.7),
            (lambda: [flow(ar1.get_start(), ar1.get_end(), WHITE, 0.5)], 0.6),
            "a short number",
            (lambda: [GrowArrow(ar2)], 0.4),
            (lambda: [*hout("9e41...", BLUE_M), FadeIn(out_l)], 0.6),
        ])
        flip = T("one bit flipped", 18, RED_M).move_to([-4.0, -1.3, 0])
        self.steps("The same data always gives the same hash. Change even one bit, and the hash comes out different.", [
            (lambda: [flow(ar1.get_start(), ar1.get_end(), WHITE, 0.5)], 0.6),
            (lambda: [Indicate(self.lab["hout"], color=BLUE_M, scale_factor=1.1)], 0.7),
            "Change even",
            (lambda: [rows[3].animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.3), 1), FadeIn(flip)], 0.5),
            (lambda: [flow(ar1.get_start(), ar1.get_end(), RED_M, 0.5)], 0.6),
            (lambda: hout("52c7...", GOLD_M), 0.6),
        ])

        # ---------------- scene 4: one hash for everything ----------------
        nodes = {(l, i): node(l, i) for l in range(4) for i in range(2 ** l)}
        root = nodes[(0, 0)]
        self.steps("So, the obvious plan. Each side hashes its whole view and sends one hash. They differ. Good, something's wrong.", [
            (lambda: [*[FadeOut(m) for m in (rows, rows_l, hbox, ar1, ar2, out_l, flip, link, netl)], *self.drop("hout")], 0.7),
            "Each side hashes",
            (lambda: [FadeIn(root, scale=0.8)], 0.6),
            (lambda: [flow(live.get_right(), root.get_left(), BLUE_M, 0.6), flow(reco.get_left(), root.get_right(), GOLD_M, 0.6)], 0.8),
            "They differ",
            (lambda: [root[0].animate.set_stroke(RED_M, width=4).set_fill(fillc(RED_M), 1)], 0.5),
        ])
        self.steps("Where? One hash can't say. It's a smoke alarm that won't tell you which room. We're back to fifty million rows.", [
            (lambda: self.cap("something differs. where?", RED_M, 26), 0.5),
            "a smoke alarm",
            (lambda: [glow(root[0], RED_M, 1.08)], 0.8),
            "We're back",
            (lambda: self.cap("one hash says whether, not where", RED_M, 26), 0.5),
        ])

        # ---------------- scene 5: the librarians ----------------
        talk = [("is the whole library the same?", "no", RED_M), ("the east wing?", "same: skip it", GREEN_M),
                ("the west wing?", "different", RED_M), ("its rooms... its shelves...", "one shelf", YELLOW_M)]
        tl = [VGroup(right_at(T(q, 22), -0.2, 0.9 - 0.62 * i), left_at(T(a_, 22, c), 0.2, 0.9 - 0.62 * i)) for i, (q, a_, c) in enumerate(talk)]
        self.steps("Back to the two libraries on the phone. A smarter pair asks: is the whole library the same? No.", [
            (lambda: [*self.drop("cap"), root.animate.set_opacity(0.25)], 0.5),
            "is the whole",
            (lambda: [FadeIn(tl[0][0])], 0.4),
            "No.",
            (lambda: [FadeIn(tl[0][1])], 0.3),
        ], after=0.2)
        self.steps("The east wing? Same, so skip it. The west wing? Different.", [
            (lambda: [FadeIn(tl[1][0])], 0.4),
            "Same",
            (lambda: [FadeIn(tl[1][1])], 0.3),
            "The west wing",
            (lambda: [FadeIn(tl[2][0])], 0.4),
            "Different",
            (lambda: [FadeIn(tl[2][1])], 0.3),
        ], after=0.2)
        self.steps("Then its rooms, then their shelves, until they're down to one shelf. "
                   "Only then do they read books aloud, from that one shelf.", [
            (lambda: [FadeIn(tl[3][0])], 0.5),
            "down to one shelf",
            (lambda: [FadeIn(tl[3][1])], 0.4),
            "Only then",
            (lambda: [Indicate(tl[3][1], color=YELLOW_M, scale_factor=1.15)], 0.8),
        ])
        self.steps("Let's map it. The library is the view. A shelf is a range of keys. A shelf's fingerprint is the hash of everything on it.", [
            "The library is",
            (lambda: self.cap("the library = the view", WHITE), 0.5),
            "A shelf is",
            (lambda: self.cap("a shelf = a range of keys", WHITE), 0.5),
            "A shelf's fingerprint",
            (lambda: self.cap("a shelf's fingerprint = the hash of everything on it", WHITE), 0.5),
        ])
        self.steps("A room's fingerprint is a hash of its shelves' fingerprints, and so on up. The phone line is the network.", [
            (lambda: self.cap("a room's fingerprint = a hash of its shelves' fingerprints", WHITE), 0.5),
            "The phone line",
            (lambda: self.cap("the phone line = the network", WHITE), 0.5),
        ])

        # ---------------- scene 6: build the tree ----------------
        edges = {(l, i, k): edge(l, i, k) for l in range(3) for i in range(2 ** l) for k in (0, 1)}
        seg = [RoundedRectangle(corner_radius=0.05, width=1.55, height=0.36, stroke_color=GREY_C, stroke_width=2)
               .set_fill(fillc(GREY_B, 0.1), 1).move_to([leaf_x(j), BAR_Y, 0]) for j in range(8)]
        rl = [T(f"r{j}", 20, GREY_B).move_to([leaf_x(j), RL_Y, 0]) for j in range(8)]
        self.steps("Let's build it small. Each side cuts its keys into 8 ranges. "
                   "A key's range comes from a hash of the key, so the ranges come out even.", [
            (lambda: [*[FadeOut(t) for t in tl], *self.drop("cap")], 0.6),
            "cuts its keys",
            (lambda: [LaggedStart(*[FadeIn(s) for s in seg], lag_ratio=0.1), LaggedStart(*[FadeIn(r) for r in rl], lag_ratio=0.1)], 1.1),
            "A key's range",
            (lambda: self.foot("50 million rows, 8 ranges, cut by a hash of the key"), 0.6),
        ])
        self.steps("Each leaf is the hash of every entry in its range, in key order. Live on top, in blue. Rebuilt underneath, in gold.", [
            (lambda: [LaggedStart(*[FadeIn(nodes[(3, j)], shift=0.1 * UP) for j in range(8)], lag_ratio=0.12)], 1.4),
            "Live on top",
            (lambda: [*[Indicate(nodes[(3, j)][1], color=BLUE_M, scale_factor=1.15) for j in range(8)]], 0.8),
            "Rebuilt underneath",
            (lambda: [*[Indicate(nodes[(3, j)][2], color=GOLD_M, scale_factor=1.15) for j in range(8)]], 0.8),
        ])
        rooms = T("rooms", 18, GREY_C).move_to([0, LEVEL_Y[2], 0])
        wings = T("wings", 18, GREY_C).move_to([0, LEVEL_Y[1], 0])

        def build(l):
            return [*[Create(edges[(l, i, k)]) for i in range(2 ** l) for k in (0, 1)],
                    *[FadeIn(nodes[(l, i)], shift=0.1 * UP) for i in range(2 ** l)]]

        self.steps("Above them, each parent is the hash of its two children, level by level, up to a single root.", [
            "each parent",
            (lambda: build(2) + [FadeIn(rooms)], 0.8),
            "level by level",
            (lambda: build(1) + [FadeIn(wings)], 0.7),
            "up to a single root",
            (lambda: [*[Create(edges[(0, 0, k)]) for k in (0, 1)], root.animate.set_opacity(1)], 0.7),
        ])
        self.steps("That's a Merkle tree. Each side builds its own, where its data lives.", [
            (lambda: [*self.cap("a Merkle tree", WHITE, 26), *self.drop("foot")], 0.5),
            "Each side builds",
            (lambda: [glow(live[0], BLUE_M, 1.03), glow(reco[0], GOLD_M, 1.03)], 0.9),
        ])

        # ---------------- scene 7: walk down ----------------
        def reset_root():
            return [root[0].animate.set_stroke(GREY_B, width=2.5).set_fill(BLACK, 1)]

        self.steps("One balance is off by a flipped bit. How many comparisons to find its range among the eight? Pause and guess.", [
            (lambda: [*reset_root(), *self.drop("cap")], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        def compare(keys, n):
            out = []
            for key in keys:
                c = RED_M if key in BAD else GREEN_M
                out.append(nodes[key][0].animate.set_stroke(c, width=4).set_fill(fillc(c), 1))
            return out + self.count(n)

        def dim(l, i):
            """Fade everything below node (l, i): it matched, so nobody looks there."""
            ms = []
            for ll in range(l + 1, 4):
                span = 2 ** (ll - l)
                for ii in range(i * span, (i + 1) * span):
                    ms += [nodes[(ll, ii)], edges[(ll - 1, ii // 2, ii % 2)]]
            j0, j1 = i * 2 ** (3 - l), (i + 1) * 2 ** (3 - l)
            ms += [rl[j] for j in range(j0, j1)] + [seg[j] for j in range(j0, j1)]
            return [m.animate.set_opacity(0.22) for m in ms]

        self.steps("Compare the roots. They differ. One comparison.", [
            (lambda: [*self.drop("cap"), flow(live.get_right(), root.get_left(), BLUE_M, 0.5),
                      flow(reco.get_left(), root.get_right(), GOLD_M, 0.5)], 0.7),
            "They differ",
            (lambda: compare([(0, 0)], 1), 0.6),
        ])
        self.steps("Compare the root's two children. The left one matches, so the first four ranges are the same, "
                   "and nothing below it needs a look. The right one differs. Three.", [
            (lambda: [nodes[(1, 0)][0].animate.set_stroke(GREEN_M, width=4).set_fill(fillc(GREEN_M), 1)], 0.6),
            "nothing below it",
            (lambda: dim(1, 0) + [rooms.animate.set_opacity(0.4)], 0.9),
            "The right one",
            (lambda: compare([(1, 0), (1, 1)], 3), 0.6),
        ])
        self.steps("Under it, left matches, right differs. Five.", [
            (lambda: compare([(2, 2), (2, 3)], 5), 0.7),
            (lambda: dim(2, 2), 0.7),
        ])
        found = T("found: r6", 22, RED_M).move_to([leaf_x(6), RL_Y, 0])
        self.steps("At the bottom, range six differs and range seven matches. Seven comparisons, and only hashes crossed the network.", [
            (lambda: compare([(3, 6), (3, 7)], 7), 0.7),
            "Seven comparisons",
            (lambda: [ReplacementTransform(rl[6], found), rl[7].animate.set_opacity(0.22), seg[7].animate.set_opacity(0.22),
                      seg[6].animate.set_stroke(RED_M, width=3)], 0.7),
            "only hashes",
            (lambda: [Indicate(self.lab["cnt"], color=WHITE, scale_factor=1.12)], 0.6),
        ])
        self.steps("Now, and only now, compare rows, only inside range six: an eighth of the keys.", [
            (lambda: self.foot("rows compared: range r6 only, an eighth of the keys", RED_M), 0.6),
            "inside range six",
            (lambda: [glow(seg[6], RED_M, 1.08),
                      flow(seg[6].get_left() + 0.1 * RIGHT, seg[6].get_right() + 0.1 * LEFT, RED_M, 0.5)], 0.8),
        ])

        # ---------------- scene 8: scale it up ----------------
        path = [nodes[k][0] for k in sorted(BAD)]
        big = chip("1,024 ranges: 1 + 2 x 10 = 21 comparisons, then about a thousandth of the rows", GREEN_M, 21).move_to([0, FOOT_Y, 0])
        self.steps("Each level costs two comparisons.", [
            (lambda: [Succession(*[glow(p, RED_M, 1.06) for p in path[1:]], run_time=1.5)], 1.5),
        ])
        self.steps("So with 1,024 ranges, ten levels deep, it's one plus two times ten: 21 comparisons, "
                   "instead of 1,024 ranges, or fifty million rows. And it leaves about a thousandth of the rows to compare.", [
            (lambda: [*self.drop("foot", "cnt")], 0.4),
            "one plus two",
            (lambda: [FadeIn(big, shift=0.1 * UP)], 0.7),
            "about a thousandth",
            (lambda: [glow(big[0], GREEN_M, 1.03)], 0.8),
        ])

        # ---------------- scene 9: when the tree stops paying ----------------
        rows_t = [("bad accounts", "comparisons", GREY_B), ("1", "17", WHITE), ("10", "101", WHITE), ("100", "369", RED_M)]
        head = T("the lesson's lab, 256 ranges:", 20, GREY_B)
        cells = VGroup(head, *[T(f"{x1} bad: {x2}", 20, c) for x1, x2, c in rows_t[1:]], T("a plain scan: 256", 20, GREEN_M))
        cells.arrange(RIGHT, buff=0.45).move_to([0, FOOT_Y, 0])
        self.steps("So more ranges are always better, and the tree always wins? Let's be fair. "
                   "The cost grows with the number of bad ranges, not the size of the view.", [
            (lambda: [FadeOut(big), *self.cap("more ranges always better? the tree always wins?", PURPLE_M)], 0.6),
            "The cost grows",
            (lambda: [Succession(*[glow(p, RED_M, 1.06) for p in path], run_time=1.4)], 1.4),
        ])
        self.steps("In the lesson's lab, with 256 ranges, one bad account took 17 comparisons. Ten took 101. "
                   "A hundred took 369: more than the 256 ranges a plain scan would compare.", [
            (lambda: self.drop("cap"), 0.3),
            (lambda: [FadeIn(cells[0])], 0.4),
            "one bad account",
            (lambda: [FadeIn(cells[1])], 0.4),
            "Ten took",
            (lambda: [FadeIn(cells[2])], 0.4),
            "A hundred",
            (lambda: [FadeIn(cells[3])], 0.4),
            "more than",
            (lambda: [FadeIn(cells[4])], 0.4),
            (lambda: [Indicate(cells[3], color=RED_M, scale_factor=1.12)], 0.7),
        ])
        self.steps("When most ranges differ, a plain scan is cheaper. And then you don't have a hundred small bugs. "
                   "You have one big one, and a few ranges are enough to find it.", [
            "a plain scan",
            (lambda: [*[glow(s, GREY_B, 1.06) for s in seg]], 0.9),
            "one big one",
            (lambda: [FadeOut(cells), *self.cap("most ranges differ: one big bug, and a plain scan is cheaper", WHITE)], 0.6),
        ])
        self.steps("If the whole library is flooded, nobody checks it shelf by shelf.", [], after=0.4)
        self.steps("Could two different ranges share a hash by chance? With SHA-256, the odds are far too small to worry about.", [
            (lambda: self.cap("two ranges with the same hash by chance? odds far too small to worry about", WHITE), 0.6),
        ])

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, how do you find one bad row in fifty million? Exchange hashes, not rows, and go down only where they differ.", [
            (lambda: self.cap("one bad row in fifty million?", WHITE), 0.5),
            "Exchange hashes",
            (lambda: [*self.cap("exchange hashes, not rows; go down only where they differ", YELLOW_M, 26),
                      flow(live.get_right(), root.get_left(), BLUE_M, 0.5), flow(reco.get_left(), root.get_right(), GOLD_M, 0.5)], 0.7),
            "go down only",
            (lambda: [Succession(*[glow(p, RED_M, 1.06) for p in path], run_time=1.4)], 1.4),
        ])
        self.steps("Git, which keeps a project's code history, uses the same kind of tree.", [], after=0.4)
        eq = node(0, 0, ("9e41", "9e41"))
        self.steps("One quick check. The two roots match. How many more comparisons do you need? Pause and think.", [
            (lambda: [*self.drop("cap"), FadeOut(found), *[m.animate.set_opacity(0.22) for k, m in nodes.items() if k != (0, 0)],
                      *[e.animate.set_opacity(0.22) for e in edges.values()], *[s.animate.set_opacity(0.22) for s in seg],
                      *[r.animate.set_opacity(0.22) for r in rl[:6] + rl[7:]]], 0.7),
            "The two roots",
            (lambda: [FadeOut(root), FadeIn(eq)], 0.5),
            (lambda: [eq[0].animate.set_stroke(GREEN_M, width=4).set_fill(fillc(GREEN_M), 1)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("None. Equal roots mean equal views. The audit is done after one comparison.", [
            (lambda: [*self.cap("equal roots, equal views", GREEN_M, 26)], 0.5),
            "The audit is done",
            (lambda: [*self.put("cnt", right_at(T("comparisons: 1", 24, GREEN_M), 6.45, FOOT_Y)), glow(eq[0], GREEN_M, 1.08)], 0.7),
        ], after=0.4)
        self.play(*self.drop("cnt"), *self.cap("exchange hashes, not rows; go down only where they differ", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
