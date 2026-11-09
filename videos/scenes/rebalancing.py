from sfz import *

SAY.insert(0, (r"\bMOVED\b", "moved"))

HASHES = [42, 78, 88, 79, 89, 70, 65, 32, 35, 67, 96, 46, 93, 34, 37, 64, 61, 60, 31, 83]   # 20 keys' hashes
NC = [BLUE_M, TEAL_M, PURPLE_M, GOLD_M, GREEN_M]                                           # node k's colour
XS4 = [-3.9, -1.3, 1.3, 3.9]
XS5 = [-5.2, -2.6, 0.0, 2.6, 5.2]
TILE_Y = [2.95, 2.15]
RULE_Y = 1.33
BAND = 0.76                                     # partitions travel along this line, above the nodes
NY, NH = -1.6, 1.0                              # short nodes (hash mod N)
TOP, BOT = 0.4, -2.9                            # tall nodes (fixed partitions), named underneath
HEAD_Y = -3.22
NW = 2.2
PY = [-0.1 - 0.6 * j for j in range(5)]         # partition slots inside a tall node, top down
K37 = HASHES.index(37)


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1),
                      MoveAlongPath(d, Line(path.get_start(), path.get_end()), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def rbox(x, y, w, h, color, fa=0.14):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    white = ManimColor(color).to_hex().upper() == "#FFFFFF"
    return r.set_fill(BLACK if white else fill(color, fa), 1).move_to([x, y, 0])


def tile(i):
    h = HASHES[i]
    x = -4.275 + 0.95 * (i % 10)
    r = RoundedRectangle(corner_radius=0.08, width=0.8, height=0.6, stroke_color=NC[h % 4], stroke_width=3)
    r.set_fill(fill(NC[h % 4], 0.22), 1).move_to([x, TILE_Y[i // 10], 0])
    return VGroup(r, M(str(h), 22).move_to(r))


def recolor(t, color):
    return [t[0].animate.set_stroke(color).set_fill(fill(color, 0.22), 1)]


def node(k, x, n):
    return VGroup(rbox(x, NY, NW, NH, NC[k]), T(f"node {k}", 22).move_to([x, NY + 0.2, 0]),
                  T(f"{n} keys", 18, GREY_B).move_to([x, NY - 0.2, 0]))


def n_sub(nd, s, color=GREY_B):
    return T(s, 18, color).move_to([nd[0].get_x(), NY - 0.2, 0])


def tall(k, x):
    return rbox(x, (TOP + BOT) / 2, NW, TOP - BOT, NC[k])


def part(p, k, x, j):
    r = RoundedRectangle(corner_radius=0.08, width=1.4, height=0.46, stroke_color=NC[k], stroke_width=2.5)
    r.set_fill(fill(NC[k], 0.25), 1).move_to([x, PY[j], 0])
    return VGroup(r, M(f"p{p}", 20).move_to(r)).set_z_index(2)


def rule(s, color=GREY_B):
    return mbox(s, color, h=0.56, size=20).move_to([0, RULE_Y, 0])


def note(s, color=GREY_B):
    t = T(s, 20, color)
    return t.move_to([6.4 - t.width / 2, RULE_Y, 0])


class Rebalancing(Base):
    """shard-03, section 1: 20 payment keys under hash mod 4 on four nodes; a fifth node under hash mod 5 moves 16 of
    20 (12 of them between old nodes; 10 to 11 nodes moves 91%). Fixed partitions: hash mod 20 picks one of 20
    partitions, a table places five on each node; the fifth node takes one whole partition from each (p16 to p19),
    so 4 of 20 keys move, all to it. A client with the old table sends key 37 (partition 17) to node 1 and gets
    MOVED 17 node 4, then retries there."""

    def construct(self):
        self.title_card("Rebalancing", "moving data when a node joins")

        tiles = [tile(i) for i in range(20)]
        nodes = [node(k, XS4[k], 5) for k in range(4)]
        r4 = rule("node = hash mod 4")
        self.steps("A payments store spreads its keys over four nodes. Each key is hashed to a number, "
                   "and its node is that number mod 4: the remainder after dividing by 4.", [
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.2 * UP) for n in nodes], lag_ratio=0.15)], 1.0),
            "Each key",
            (lambda: [LaggedStart(*[FadeIn(t) for t in tiles], lag_ratio=0.04)], 1.2),
            "and its node",
            (lambda: [FadeIn(r4, shift=0.15 * DOWN)], 0.7),
        ])

        hl = SurroundingRectangle(tiles[K37], color=YELLOW_M, buff=0.08, corner_radius=0.08, stroke_width=4)
        n37 = note("37 mod 4 = 1: node 1", YELLOW_M)
        self.steps("Take the key that hashes to 37. 37 mod 4 is 1, so it lives on node 1. Every node holds five keys.", [
            (lambda: [Create(hl)], 0.6),
            "37 mod 4",
            (lambda: [FadeIn(n37)], 0.6),
            "so it lives",
            (lambda: [glow(nodes[1][0], YELLOW_M, 1.04)], 0.9),
            "Every node",
            (lambda: [*[Indicate(n[2], color=WHITE, scale_factor=1.15) for n in nodes]], 0.9),
        ])

        n4 = node(4, XS5[4], 0)
        r5 = rule("node = hash mod 5")
        self.steps("Before a sales peak, a fifth node joins. The rule becomes hash mod 5.", [
            (lambda: [FadeOut(n37), *[n.animate.shift((XS5[k] - XS4[k]) * RIGHT) for k, n in enumerate(nodes)]], 0.9),
            (lambda: [FadeIn(n4, shift=0.3 * LEFT)], 0.7),
            "The rule",
            (lambda: [Transform(r4, r5)], 0.7),
        ])

        moved = [i for i, h in enumerate(HASHES) if h % 4 != h % 5]
        allnodes = nodes + [n4]
        moved_c = chip("16 of 20 keys moved, 12 of them between old nodes", RED_M, 20).move_to([0, -2.95, 0])
        n37b = note("37 mod 5 = 2: node 2", YELLOW_M)
        self.steps("Almost every answer changes: 16 of the 20 keys move. "
                   "Key 37 goes from node 1 to node 2, and neither of those is new.", [
            (lambda: [*[a for i in moved for a in recolor(tiles[i], NC[HASHES[i] % 5])],
                      *[Transform(n[2], n_sub(n, "4 keys")) for n in allnodes]], 1.0),
            (lambda: [*[tiles[i].animate(rate_func=there_and_back).scale(1.15) for i in moved]], 0.8),
            "Key 37",
            (lambda: [FadeIn(n37b), glow(nodes[1][0], RED_M, 1.04), glow(nodes[2][0], RED_M, 1.04)], 1.0),
            "and neither",
            (lambda: [FadeIn(moved_c, shift=0.15 * UP)], 0.7),
        ])

        share = chip("10 nodes to 11: 91% of keys move", RED_M, 20).move_to([0, -2.95, 0])
        self.steps("The new node needed only four, its fair share. The other twelve moves are waste. "
                   "From ten nodes to eleven, 91% of keys move.", [
            (lambda: [glow(n4[0], GREEN_M, 1.04)], 1.0),
            "The other twelve",
            (lambda: [glow(moved_c[0], RED_M, 1.04)], 0.9),
            "From ten nodes",
            (lambda: [FadeTransform(moved_c, share)], 0.8),
        ])

        rp = rule("partition = hash mod 20")
        n37c = note("37 mod 20 = 17", YELLOW_M)
        self.steps("So split the map in two. First, hash mod 20 puts each key in one of 20 partitions, "
                   "a number fixed when the store is created.", [
            (lambda: [FadeOut(share), FadeOut(n37b), FadeOut(n4, shift=0.3 * RIGHT),
                      *[a for i in moved for a in recolor(tiles[i], NC[HASHES[i] % 4])],
                      *[n.animate.shift((XS4[k] - XS5[k]) * RIGHT) for k, n in enumerate(nodes)]], 1.0),
            (lambda: [*[Transform(n[2], n_sub(n, "5 keys")) for n in nodes]], 0.5),
            "First, hash mod 20",
            (lambda: [Transform(r4, rp)], 0.8),
            "a number fixed",
            (lambda: [FadeIn(n37c)], 0.6),
        ])

        talls = [tall(k, XS4[k]) for k in range(4)]
        heads = [T(f"node {k}", 22).move_to([XS4[k], HEAD_Y, 0]) for k in range(4)]
        parts = {p: part(p, p % 4, XS4[p % 4], 4 - p // 4) for p in range(20)}      # highest partition on top
        p17hl = SurroundingRectangle(parts[17], color=YELLOW_M, buff=0.06, corner_radius=0.08, stroke_width=4)
        self.steps("Then a table says which node holds each partition: five each. "
                   "Key 37 is in partition 17, which lives on node 1.", [
            (lambda: [*[FadeOut(n[2]) for n in nodes], *[Transform(n[0], talls[k]) for k, n in enumerate(nodes)],
                      *[Transform(n[1], heads[k]) for k, n in enumerate(nodes)]], 1.0),
            (lambda: [LaggedStart(*[FadeIn(parts[p]) for p in range(20)], lag_ratio=0.05)], 1.2),
            "Key 37",
            (lambda: [Create(p17hl)], 0.7),
        ])

        t4 = tall(4, XS5[4])
        h4 = T("node 4", 22).move_to([XS5[4], HEAD_Y, 0])
        give = [16, 17, 18, 19]

        def hand_path(p, j):
            """Up out of the old node, along the band above the nodes, and down into node 4, filling it from the bottom."""
            x0 = XS5[p % 4]
            return VMobject().set_points_as_corners([[x0, PY[0], 0], [x0, BAND, 0], [XS5[4], BAND, 0], [XS5[4], PY[3 - j], 0]])
        self.steps("Now the fifth node joins. Its fair share is four partitions, "
                   "so each old node hands it one whole partition.", [
            (lambda: [FadeOut(p17hl), *[m.animate.shift((XS5[k] - XS4[k]) * RIGHT) for k, n in enumerate(nodes) for m in (n[0], n[1])],
                      *[parts[p].animate.shift((XS5[p % 4] - XS4[p % 4]) * RIGHT) for p in range(20)]], 1.0),
            (lambda: [FadeIn(t4), FadeIn(h4)], 0.6),
            "so each old node",
            (lambda: [Succession(*[MoveAlongPath(parts[p], hand_path(p, j), rate_func=smooth, run_time=0.8)
                                   for j, p in enumerate(reversed(give))])], 3.2),
            (lambda: [*[a for p in give for a in recolor(parts[p], GREEN_M)]], 0.5),
        ])

        pmoved = [i for i, h in enumerate(HASHES) if h % 20 in give]
        good = rule("4 of 20 keys moved, all to the new node", GREEN_M)
        self.steps("No key changes partition, so only the keys in those four partitions move: "
                   "one in five, all to the new node, and four old nodes share the copying.", [
            (lambda: [glow(r4[0], YELLOW_M, 1.04)], 0.8),
            "only the keys",
            (lambda: [*[a for i in pmoved for a in recolor(tiles[i], GREEN_M)]], 0.8),
            (lambda: [*[tiles[i].animate(rate_func=there_and_back).scale(1.15) for i in pmoved]], 0.7),
            "one in five",
            (lambda: [FadeOut(n37c), Transform(r4, good)], 0.8),
            "and four old nodes",
            (lambda: [*[glow(n[0], NC[k], 1.02) for k, n in enumerate(nodes)]], 0.9),
        ])

        cx, cy = 0.0, 2.45
        cl = VGroup(rbox(cx, cy, 3.4, 1.0, WHITE), T("client", 22).move_to([cx, cy + 0.2, 0]),
                    M("table: p17 on node 1", 17, GREY_B).move_to([cx, cy - 0.2, 0]))
        a1 = Arrow([cx - 1.1, cy - 0.55, 0], [XS5[1] + 0.4, TOP + 0.1, 0], buff=0, stroke_width=3, color=GREY_B,
                   tip_length=0.2, max_tip_length_to_length_ratio=0.5)
        self.steps("A client still holds the old table, so it sends a request for key 37 to node 1.", [
            (lambda: [*[FadeOut(t) for t in tiles], FadeOut(hl), FadeOut(r4)], 0.8),
            (lambda: [FadeIn(cl, shift=0.2 * DOWN)], 0.7),
            "so it sends",
            (lambda: [GrowArrow(a1)], 0.6),
            (lambda: [flow(a1, YELLOW_M, 0.8)], 0.8),
        ])

        back = Line(a1.get_end(), a1.get_start())
        mv = chip("MOVED 17 node 4", RED_M, 20, mono=True).move_to([-4.6, 1.45, 0])
        self.steps("Node 1 no longer owns partition 17. It answers MOVED: partition 17 lives on node 4 now.", [
            (lambda: [glow(nodes[1][0], RED_M, 1.02)], 0.9),
            "It answers",
            (lambda: [flow(back, RED_M, 0.8)], 0.8),
            (lambda: [FadeIn(mv, shift=0.15 * LEFT)], 0.6),
        ])

        a2 = Arrow([cx + 1.1, cy - 0.55, 0], [XS5[4] - 0.4, TOP + 0.1, 0], buff=0, stroke_width=3, color=GREY_B,
                   tip_length=0.2, max_tip_length_to_length_ratio=0.5)
        ok = chip("found key 37", GREEN_M, 20).move_to([4.75, 1.85, 0])
        self.steps("The client updates its table and retries at node 4. The request costs one extra hop, and it doesn't fail.", [
            (lambda: [Transform(cl[2], M("table: p17 on node 4", 17, GREEN_M).move_to(cl[2]))], 0.7),
            "and retries",
            (lambda: [GrowArrow(a2)], 0.6),
            (lambda: [flow(a2, YELLOW_M, 0.8)], 0.8),
            (lambda: [FadeIn(ok, shift=0.15 * LEFT), glow(t4, GREEN_M, 1.02), glow(parts[17][0], YELLOW_M, 1.1)], 0.8),
        ])

        self.steps("Fix the partitions once and move them whole. A new node takes only its share, "
                   "and a client with an old map is one redirect away from the right node.", [
            (lambda: [*[glow(parts[p][0], GREEN_M, 1.08) for p in give]], 1.0),
            "and a client",
            (lambda: [glow(mv[0], RED_M, 1.05), glow(ok[0], GREEN_M, 1.05)], 1.0),
        ])
        self.wait(0.6)
