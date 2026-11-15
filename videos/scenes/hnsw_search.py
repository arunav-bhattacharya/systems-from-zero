import heapq

from sfz import *

SAY.insert(0, (r"\bHNSW\b", "H N S W"))
SAY.insert(0, (r"\bpgvector\b", "P G vector"))
SAY.insert(0, (r"\bef_search\b", "E F search"))
SAY.insert(0, (r"\bef search\b", "E F search"))

# ---- the data: 40 vectors in a plane, a three-layer graph, and a real search over it ------------------------------------
SEED, QXY, N = 16, (0.2, -2.6), 40


def build():
    rng = np.random.default_rng(SEED)
    pts = []
    while len(pts) < N:
        p = np.array([rng.uniform(-6.3, 1.5), rng.uniform(-3.1, 2.3)])
        if all(np.linalg.norm(p - q) > 0.62 for q in pts):
            pts.append(p)
    P = np.array(pts)
    near = lambda xy, c: min(c, key=lambda i: np.linalg.norm(P[i] - np.array(xy)))
    L2 = [near(a, range(N)) for a in [(-5.6, 2.0), (-2.2, 0.2), (1.2, 1.9)]]
    L1 = list(L2)
    while len(L1) < 10:                          # spread out, like a random few
        L1.append(max(range(N), key=lambda i: min(np.linalg.norm(P[i] - P[j]) for j in L1)))

    def knn(nodes, k):
        E = set()
        for i in nodes:
            for j in sorted([j for j in nodes if j != i], key=lambda j: np.linalg.norm(P[i] - P[j]))[:k]:
                E.add((min(i, j), max(i, j)))
        return E
    E = {2: {(min(a, b), max(a, b)) for a in L2 for b in L2 if a != b}, 1: knn(L1, 3), 0: knn(range(N), 3)}
    return P, L2, L1, E


P, L2, L1, E = build()
Q = np.array(QXY)


def dist(i):
    return float(np.linalg.norm(P[i] - Q))


def nbrs(layer, i):
    return sorted(b if a == i else a for a, b in E[layer] if i in (a, b))


def search(ef):
    """HNSW search: greedy (one candidate) in layers 2 and 1, a beam of ef in layer 0. Returns the results and a trace
    of (layer, kind, node, neighbours whose distance was computed), plus how many distances it computed."""
    trace, nd, cur = [], 1, L2[0]
    for layer in (2, 1):
        vis = {cur}
        while True:
            comp = [j for j in nbrs(layer, cur) if j not in vis]
            vis |= set(comp)
            nd += len(comp)
            trace.append((layer, "look", cur, comp))
            best = min([cur] + nbrs(layer, cur), key=dist)
            if best == cur:
                break
            trace.append((layer, "move", best, []))
            cur = best
    vis = {cur}
    C, W = [(dist(cur), cur)], [(-dist(cur), cur)]
    while C:
        dc, c = heapq.heappop(C)
        if dc > -W[0][0]:
            break
        comp = [j for j in nbrs(0, c) if j not in vis]
        vis |= set(comp)
        nd += len(comp)
        trace.append((0, "expand", c, comp))
        for j in comp:
            if len(W) < ef or dist(j) < -W[0][0]:
                heapq.heappush(C, (dist(j), j))
                heapq.heappush(W, (-dist(j), j))
                if len(W) > ef:
                    heapq.heappop(W)
    return sorted([i for _, i in W], key=dist), trace, nd


RES4, TR4, ND4 = search(4)
RES6, TR6, ND6 = search(6)
TRUE4 = sorted(range(N), key=dist)[:4]
assert TR6[:len(TR4)] == TR4                    # the wider beam walks the same path, then keeps going

PX = 2.45                                       # right panel, left edge
LAYER_Y = {2: 2.35, 1: 1.8, 0: 1.25}
LC = {2: PURPLE_M, 1: BLUE_M, 0: GREY_C}


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


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def pt(i):
    return np.array([P[i][0], P[i][1], 0])


def qpt():
    return np.array([Q[0], Q[1], 0])


def edges(layer, color, sw, opacity=1.0):
    return VGroup(*[Line(pt(a), pt(b), stroke_width=sw, color=color).set_opacity(opacity) for a, b in sorted(E[layer])])


def ring(i, color=YELLOW_M, r=0.17, sw=3.5):
    return Circle(radius=r, color=color, stroke_width=sw).move_to(pt(i))


def layer_bar(layer, on):
    n = {2: 3, 1: 10, 0: 40}[layer]
    c = LC[layer]
    r = RoundedRectangle(corner_radius=0.08, width=4.0, height=0.44, stroke_color=c if on else GREY_D, stroke_width=2.5 if on else 1.5)
    r.set_fill(fillc(c, 0.2) if on else BLACK, 1).move_to([PX + 2.0, LAYER_Y[layer], 0])
    t = T(f"layer {layer}: {n} vectors", 20, WHITE if on else GREY_C).move_to(r)
    return VGroup(r, t)


def counter(n, label="distances computed", color=WHITE):
    return left_at(T(f"{label}: {n}", 22, color), PX, 0.45)


def note(lines, y, color=GREY_B, size=20):
    g = VGroup(*[T(s, size, WHITE) for s in lines]).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
    r = RoundedRectangle(corner_radius=0.08, width=4.1, height=g.height + 0.32, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.18), 1)
    left_at(g, PX + 0.16, y)
    r.move_to([PX + 2.05, y, 0])
    return VGroup(r, g)


class HnswSearch(Base):
    """store-08, section 3: 40 dispute vectors in a plane (a stand-in for hundreds of dimensions). Exact search measures
    all 40. HNSW links each vector to its nearest neighbours in layer 0, a spread-out 10 in layer 1 and 3 in layer 2. The
    search starts at the top entry point, moves greedily, drops a layer when no neighbour is closer, and keeps a beam in
    layer 0. The graph, the layers and every count on screen come from running that search on these points: a beam of 4
    computes 17 distances and finds 3 of the true 4 nearest; a beam of 6 computes 22 and finds all 4. Then the lesson's
    pgvector numbers: recall@10 0.89 at ef_search 10, 1.0 at 40; 654 pages against 2,138 for the exact scan."""

    def construct(self):
        self.title_card("HNSW: nearest neighbours by walking a graph", "a layered graph, searched from the top down")

        dots = VGroup(*[Dot(pt(i), radius=0.075, color=GREY_B) for i in range(N)])
        qd = Dot(qpt(), radius=0.1, color=YELLOW_M)
        ql = T("query", 20, YELLOW_M).next_to(qd, LEFT, buff=0.15)
        cap = left_at(T("“charged twice for one bike rental”", 24, YELLOW_M), -6.5, 3.15)
        sub = left_at(T("40 past disputes, drawn in 2 of their hundreds of dimensions", 20, GREY_B), PX, -0.35)
        sub = VGroup(*[left_at(T(s, 20, GREY_B), PX, y) for s, y in
                       [("40 past disputes, drawn in 2", -0.2), ("of their hundreds of dimensions", -0.55)]])
        self.steps("A customer writes: charged twice for one bike rental. Support wants past disputes that mean the same. "
                   "An embedding model turns each text into a vector, and similar meanings land close together.", [
            (lambda: [FadeIn(cap, shift=0.1 * DOWN)], 0.8),
            "An embedding model",
            (lambda: [LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.04), FadeIn(sub)], 1.8),
            "and similar meanings",
            (lambda: [FadeIn(qd, scale=0.5), FadeIn(ql)], 0.7),
        ])

        rays = VGroup(*[Line(qpt(), pt(i), stroke_width=1.2, color=GOLD_M).set_opacity(0.6) for i in range(N)])
        cnt = counter(40, "exact: distances computed", GOLD_M)
        self.steps("The exact search measures the distance from the query to every vector: 40 here.", [
            (lambda: [FadeOut(sub)], 0.4),
            "measures the distance",
            (lambda: [LaggedStart(*[Create(r) for r in rays], lag_ratio=0.03)], 1.8),
            "40 here",
            (lambda: [FadeIn(cnt, shift=0.1 * UP)], 0.6),
        ])

        big = note(["50 million vectors of 1,536 numbers:", "77 billion multiply-adds a query"], -0.75, RED_M, 18)
        self.steps("With 50 million vectors of 1,536 numbers, that's 77 billion multiply-adds a query.", [
            (lambda: [FadeIn(big, shift=0.1 * UP)], 0.8),
            "77 billion",
            (lambda: [glow(big[0], RED_M, 1.03)], 0.9),
        ])

        # ---- the graph and its layers ------------------------------------------------------------------------------
        e0, e1, e2 = edges(0, GREY_D, 1.6), edges(1, BLUE_M, 2.2), edges(2, PURPLE_M, 3)
        for e in (e0, e1, e2):
            e.set_z_index(-1)
        bars = {k: layer_bar(k, False) for k in (2, 1, 0)}
        self.steps("HNSW gives up exactness for speed. It links every vector to a few of its nearest neighbours, "
                   "and searches by walking toward the query.", [
            (lambda: [FadeOut(rays), FadeOut(cnt), FadeOut(big)], 0.6),
            "It links",
            (lambda: [LaggedStart(*[Create(l) for l in e0], lag_ratio=0.02)], 1.8),
            (lambda: [FadeIn(bars[0]), Transform(bars[0], layer_bar(0, True))], 0.6),
        ])

        l1dots = VGroup(*[dots[i] for i in L1])
        l2dots = VGroup(*[dots[i] for i in L2])
        others1 = VGroup(*[dots[i] for i in range(N) if i not in L1])
        others2 = VGroup(*[dots[i] for i in L1 if i not in L2])
        self.steps("It also builds express lanes. A random few vectors sit in a layer above, with longer links, "
                   "and fewer still in the top layer.", [
            (lambda: [e0.animate.set_opacity(0.15), others1.animate.set_opacity(0.25), FadeIn(bars[1]), FadeIn(bars[2]),
                      Transform(bars[0], layer_bar(0, False))], 0.8),
            "A random few",
            (lambda: [Transform(bars[1], layer_bar(1, True)), *[dots[i].animate.set_color(BLUE_M).scale(1.3) for i in L1],
                      LaggedStart(*[Create(l) for l in e1], lag_ratio=0.08)], 1.4),
            "and fewer still",
            (lambda: [Transform(bars[1], layer_bar(1, False)), Transform(bars[2], layer_bar(2, True)),
                      e1.animate.set_opacity(0.15), others2.animate.set_opacity(0.25),
                      *[dots[i].animate.set_color(PURPLE_M).scale(1.3) for i in L2], *[Create(l) for l in e2]], 1.2),
        ])

        # ---- the search ----------------------------------------------------------------------------------------------
        S = {"n": 1, "cnt": counter(1), "cur": ring(L2[0]), "seen": VGroup()}

        def clear_seen():
            old, S["seen"] = S["seen"], VGroup()
            return [FadeOut(old)]

        def bump(k):
            S["n"] += k
            old, S["cnt"] = S["cnt"], counter(S["n"])
            return [FadeOut(old), FadeIn(S["cnt"])]

        def look(layer, node, comp, color):
            """Measure the distance from the query to each new neighbour: a flash along each link."""
            an = []
            for j in comp:
                an.append(ShowPassingFlash(Line(pt(node), pt(j), stroke_width=5, color=GOLD_M), time_width=0.6))
                m = ring(j, GOLD_M, 0.12, 2)
                S["seen"].add(m)
                an.append(FadeIn(m))
            return an + bump(len(comp))

        def move(node):
            return [S["cur"].animate.move_to(pt(node))]

        t4 = list(TR4)
        entry = left_at(T("entry point", 20, PURPLE_M), pt(L2[0])[0] + 0.25, pt(L2[0])[1] + 0.3)
        self.steps("The search starts at the entry point in the top layer. It measures its neighbours, "
                   "and moves to the one closest to the query.", [
            (lambda: [Create(S["cur"]), FadeIn(entry), FadeIn(S["cnt"])], 0.8),
            "It measures",
            (lambda: look(2, t4[0][2], t4[0][3], PURPLE_M), 1.0),
            "and moves",
            (lambda: [FadeOut(entry), *move(t4[1][2])], 0.9),
        ])

        def show_layer(k):
            an = [*[Transform(bars[j], layer_bar(j, j == k)) for j in (2, 1, 0)]]
            if k == 1:
                an += [e2.animate.set_opacity(0.15), e1.animate.set_opacity(1), others2.animate.set_opacity(1)]
            if k == 0:
                an += [e1.animate.set_opacity(0.15), e0.animate.set_opacity(1), others1.animate.set_opacity(1)]
            return an

        self.steps("Nothing there is closer, so it drops a layer, at the same vector.", [
            (lambda: [glow(S["cur"], YELLOW_M, 1.3)], 0.8),
            "so it drops",
            (lambda: show_layer(1), 1.0),
        ])

        lay1 = [x for x in t4 if x[0] == 1]
        self.steps("Layer 1 has shorter links. Two moves bring the search into the query's neighbourhood.", [
            (lambda: look(1, lay1[0][2], lay1[0][3], BLUE_M), 0.9),
            "Two moves",
            (lambda: move(lay1[1][2]), 0.7),
            (lambda: look(1, lay1[2][2], lay1[2][3], BLUE_M), 0.9),
            (lambda: move(lay1[3][2]), 0.7),
        ])

        exp4 = [x for x in t4 if x[0] == 0]
        beam = left_at(T("beam: the 4 best so far", 20, TEAL_M), PX, -0.2)
        self.steps("The bottom layer holds every vector. Here it keeps a beam of the four best so far, "
                   "and expands the closest until nothing improves.", [
            (lambda: show_layer(0), 1.0),
            "keeps a beam",
            (lambda: [FadeIn(beam, shift=0.1 * UP)], 0.6),
            "and expands",
            *[(lambda x=x: [*move(x[2]), *(look(0, x[2], x[3], GREY_B) if x[3] else [])], 0.75) for x in exp4],
        ])

        found = VGroup(*[ring(i, GREEN_M, 0.17, 4) for i in RES4])
        missed = [i for i in TRUE4 if i not in RES4][0]
        extra = [i for i in RES4 if i not in TRUE4][0]
        miss_r = DashedVMobject(Circle(radius=0.19, color=RED_M, stroke_width=3.5), num_dashes=12).move_to(pt(missed))
        miss_l = left_at(T("dashed: the one it missed", 20, RED_M), PX, -1.05)
        rc = left_at(T("found 3 of the true 4", 22, RED_M), PX, -0.65)
        self.steps(f"It stops after 17 distances instead of 40. But one of the four it returns is not a true nearest "
                   "neighbour. This closer one was never reached.", [
            (lambda: [FadeOut(S["cur"]), *clear_seen(), *[Create(r) for r in found]], 0.9),
            "But one",
            (lambda: [Indicate(dots[extra], color=RED_M, scale_factor=2.5)], 0.8),
            "This closer one",
            (lambda: [Create(miss_r), FadeIn(miss_l), FadeIn(rc, shift=0.1 * UP)], 0.9),
        ])

        more = [x for x in TR6[len(TR4):]]
        S["cur"] = ring(exp4[-1][2])
        found6 = VGroup(*[ring(i, GREEN_M, 0.17, 4) for i in RES6[:4]])
        rc6 = left_at(T("found all 4", 22, GREEN_M), PX, -0.65)
        beam6 = left_at(T("beam: the 6 best so far", 20, TEAL_M), PX, -0.2)
        self.steps("Recall is the share of the true nearest neighbours a search returns. Widen the beam to six, "
                   "and it keeps expanding a little longer. It finds all four, for 22 distances.", [
            (lambda: [Indicate(rc, color=RED_M, scale_factor=1.0)], 0.8),
            "Widen the beam",
            (lambda: [FadeOut(found), FadeOut(miss_l), Transform(beam, beam6), Create(S["cur"])], 0.7),
            *[(lambda x=x: [*move(x[2]), *(look(0, x[2], x[3], GREY_B) if x[3] else [])], 0.75) for x in more],
            "It finds all four",
            (lambda: [FadeOut(S["cur"]), *clear_seen(), FadeOut(miss_r), *[Create(r) for r in found6], Transform(rc, rc6)], 0.9),
        ])
        assert ND4 == 17 and ND6 == 22 and S["n"] == ND6

        tab = VGroup(left_at(T("pgvector, 100,000 vectors", 20, GREY_B), PX, -1.2),
                     left_at(M("ef_search  recall@10", 16, GREY_B), PX, -1.6),
                     left_at(M("10         0.89", 16, RED_M), PX, -1.95),
                     left_at(M("40         1.00", 16, GREEN_M), PX, -2.3),
                     left_at(M("200        1.00", 16, GREEN_M), PX, -2.65),
                     VGroup(left_at(T("pages read: 654 through the index,", 19, WHITE), PX, -3.0),
                            left_at(T("2,138 for the exact scan", 19, WHITE), PX, -3.32)))
        self.steps("In pgvector the beam is ef search, 40 by default. On the lesson's 100,000 vectors, a beam of 10 found "
                   "89 percent of the true top ten, and 40 found them all, reading 654 pages to the exact scan's 2,138.", [
            (lambda: [FadeIn(tab[0]), FadeIn(tab[1])], 0.7),
            "a beam of 10",
            (lambda: [FadeIn(tab[2], shift=0.1 * UP)], 0.6),
            "and 40 found",
            (lambda: [FadeIn(tab[3], shift=0.1 * UP), FadeIn(tab[4], shift=0.1 * UP)], 0.7),
            "reading 654",
            (lambda: [FadeIn(tab[5], shift=0.1 * UP)], 0.7),
        ])

        self.steps("Start at the sparse top, walk toward the query, and drop a layer each time you stop improving. "
                   "A wider beam buys recall with more distances.", [
            (lambda: [glow(bars[2][0], PURPLE_M, 1.03), *[Indicate(d, color=PURPLE_M, scale_factor=1.6) for d in l2dots]], 1.0),
            "and drop a layer",
            (lambda: [glow(bars[1][0], BLUE_M, 1.03)], 0.6),
            (lambda: [glow(bars[0][0], GREY_B, 1.03)], 0.6),
            "A wider beam",
            (lambda: [*[glow(r, GREEN_M, 1.3) for r in found6], Indicate(tab[3], color=GREEN_M, scale_factor=1.0)], 1.0),
        ])
        self.wait(0.6)
