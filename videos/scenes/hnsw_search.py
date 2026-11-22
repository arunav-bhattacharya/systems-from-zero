from sfz import *

SAY.insert(0, (r"\bHNSW\b", "H N S W"))
SAY.insert(0, (r"\bpgvector\b", "P G vector"))
SAY.insert(0, (r"\bef_search\b", "E F search"))
SAY.insert(0, (r"\bYashunin\b", "Yashoonin"))
SAY.insert(0, (r"\b0\.8\.0\b", "zero point eight point zero"))
# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz" (Whisper hears "posters"); spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BX0, BX1, BH = -5.0, 6.4, 0.8
LY = {2: 2.05, 1: 0.75, 0: -0.55}                       # the three layers
LAB_X = -5.85
L2 = [120, 330, 570]                                      # the lesson's stepper, in its own x units
L1 = [120, 220, 330, 440, 500, 570]
L0 = [90, 120, 150, 190, 220, 260, 300, 330, 370, 400, 440, 470, 500, 530, 570, 610]
LAYERS = {2: L2, 1: L1, 0: L0}
QV = 515
STRIP_Y, STRIP_T_Y, CNT_Y, BAR_Y, CAP_Y = -2.05, -1.55, -2.6, -2.95, -3.3


def X(v):
    return BX0 + (v - 80) / 584 * (BX1 - BX0)


def P(layer, v):
    return np.array([X(v), LY[layer], 0])


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))






class HnswSearch(Base):
    """store-08, section 3. Support wants past complaints that mean the same as a new one. Embeddings turn text into
    vectors, close means similar; the exact search measures every vector (2,138 pages, 77 billion operations at 50
    million). Driving to a friend's house: motorway, main road, streets. The lesson's stepper: 16 vectors in three
    layers, entry 120 -> 330 -> 570 on layer 2, 500 on layer 1, a beam of 4 on layer 0; 10 distances instead of 16.
    HNSW in pgvector (m 16, ef_search 40; 654 pages). Recall (0.89 at 10, 1.0 at 40). The filter trap (4 rows of 10)
    and the iterative scan. Memory. Moral and a check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def dist(self, n):
        return self.put("dist", left_at(T(f"distances worked out: {n}", 22, WHITE), BX0, 2.88))

    def count(self, s, color=WHITE):
        return self.put("cnt", fit(T(s, 24, color), 13.0).move_to([0, CNT_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def state(self, layer, v, kind):
        """Colour one vector: 'at' (where the search stands), 'seen' (looked at, left behind), 'ok' (in the answer)."""
        d = self.dots[(layer, v)]
        col = {"at": BLUE_M, "seen": GREY_D, "ok": GREEN_M, "plain": WHITE}[kind]
        fillcol = {"at": fillc(BLUE_M, 0.6), "seen": BLACK, "ok": fillc(GREEN_M, 0.7), "plain": BLACK}[kind]
        return d.animate.set_stroke(col, 3).set_fill(fillcol, 1)

    def hop(self, layer, a, b, color=YELLOW_M, rt=0.5):
        return dot_run(P(layer, a) + [0.12 if b > a else -0.12, 0, 0], P(layer, b) + [-0.12 if b > a else 0.12, 0, 0], color, rt)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Nearest by meaning", "walking a graph from the top layer down")

        # ---------------- scene 1: the question ----------------
        q = chip("charged twice for one bike rental", YELLOW_M, 26).move_to([0, 1.5, 0])
        m = chip("duplicate charge, scooter hire", GREEN_M, 26).move_to([0, 0.1, 0])
        self.steps("A customer writes to support: charged twice for one bike rental. "
                   "Support wants past complaints like it, by meaning, not by shared words.", [
            "A customer writes",
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.6),
            "by meaning",
            (lambda: self.cap("find past complaints that mean the same thing", WHITE), 0.6),
        ])
        self.steps("So duplicate charge, scooter hire should match, though it shares no word with the first. "
                   "How does a database find complaints that mean the same thing, among millions, fast?", [
            (lambda: [FadeIn(m, shift=0.1 * UP)], 0.6),
            "shares no word",
            (lambda: self.cap("not one word in common", WHITE), 0.5),
            "among millions",
            (lambda: self.cap("among millions, fast?", YELLOW_M), 0.5),
        ], after=0.3)

        # ---------------- scene 2: vectors, and the exact search ----------------
        rng = np.random.default_rng(3)
        pts = [np.array([x, y, 0]) for x, y in zip(rng.uniform(-6.0, 6.0, 46), rng.uniform(-2.0, 2.4, 46))]
        qp = np.array([1.2, 0.5, 0])
        pts = [p for p in pts if np.linalg.norm(p - qp) > 0.45]
        near = sorted(range(len(pts)), key=lambda i: np.linalg.norm(pts[i] - qp))[:4]
        scat = VGroup(*[Dot(p, radius=0.07, color=GREY_B) for p in pts])
        qd = Dot(qp, radius=0.1, color=YELLOW_M).set_z_index(4)
        self.steps("First, meaning has to become something a computer can measure. A model, a program trained on huge amounts of text, "
                   "turns each text into a vector: a list of a few hundred to a few thousand numbers.", [
            (lambda: [*self.uncap(), FadeOut(m), q.animate.scale(0.8).move_to([0, 3.15, 0])], 0.7),
            "turns each text",
            (lambda: [*self.cap(M("[0.12, -0.80, 0.33, ... ]   a few hundred to a few thousand numbers", 20, WHITE))], 0.6),
        ])
        self.steps("Texts with similar meanings land close together, like points on a map. Only this map has hundreds of directions "
                   "instead of two. So finding similar complaints means finding the nearest points to the new one.", [
            "land close together",
            (lambda: [LaggedStart(*[FadeIn(d, scale=0.5) for d in scat], lag_ratio=0.03), FadeIn(qd, scale=0.5)], 1.2),
            "hundreds of directions",
            (lambda: self.cap("close together = similar meaning (the real map has hundreds of directions)", WHITE), 0.6),
            "the nearest points",
            (lambda: [*[scat[i].animate.set_color(GREEN_M).scale(1.4) for i in near]], 0.6),
        ])
        rays = VGroup(*[Line(qp, p, stroke_width=1.2, color=GREY_C) for p in pts])
        self.steps("The plain way: measure the distance from the query to every vector, and keep the closest. In the lab, that's 100,000 "
                   "vectors of 32 numbers, 2,138 pages, about 8 milliseconds.", [
            "measure the distance",
            (lambda: [LaggedStart(*[Create(r) for r in rays], lag_ratio=0.03)], 1.4),
            "In the lab",
            (lambda: self.count("exact search: 100,000 vectors of 32 numbers, 2,138 pages, about 8 ms"), 0.6),
        ])
        self.steps("Now picture 50 million complaints of 1,536 numbers each: 77 billion multiplications and additions for every question. "
                   "And a sorted index can't help. It has one order, and this map has hundreds of directions.", [
            "77 billion",
            (lambda: self.count("50 million x 1,536 numbers: 77 billion operations per question", RED_M), 0.6),
            "a sorted index",
            (lambda: self.cap("a sorted index has one order; this map has hundreds of directions", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 3: the drive ----------------
        bands = {k: RoundedRectangle(corner_radius=0.12, width=BX1 - BX0, height=BH, stroke_color=GREY_C, stroke_width=2)
                 .set_fill(fillc(GREY_B, 0.08), 1).move_to([(BX0 + BX1) / 2, LY[k], 0]) for k in LY}
        names = {2: "motorway", 1: "main roads", 0: "streets"}
        links = {k: VGroup(*[Line(P(k, a) + [0.1, 0, 0], P(k, b) + [-0.1, 0, 0], stroke_width=2, color=GREY_C)
                             for a, b in zip(LAYERS[k], LAYERS[k][1:])]) for k in LY}
        drops = VGroup(*[DashedLine(P(k, v) + [0, -0.1, 0], P(k - 1, v) + [0, 0.1, 0], dash_length=0.06, stroke_width=1.3, color=GREY_D)
                         for k in (2, 1) for v in LAYERS[k]])
        self.dots = {(k, v): Circle(radius=0.1, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(P(k, v)).set_z_index(2)
                     for k in LY for v in LAYERS[k]}
        qdots = {k: Dot(P(k, QV) + [0, 0.22, 0], radius=0.07, color=YELLOW_M).set_z_index(4) for k in LY}
        qlab = T("query", 18, YELLOW_M).move_to([X(QV), LY[2] + BH / 2 + 0.25, 0])
        self.steps("So think how you drive to a friend's house in another city. Motorway first, with exits far apart, "
                   "to the exit nearest their town. Then a main road. Then the streets, to the door.", [
            (lambda: [FadeOut(VGroup(scat, qd, rays, q)), *self.drop("cnt"), *self.uncap()], 0.7),
            "Motorway first",
            (lambda: [FadeIn(bands[2]), *self.put("n2", T(names[2], 20, WHITE).move_to([LAB_X, LY[2], 0])),
                      *[FadeIn(self.dots[(2, v)]) for v in L2], Create(links[2])], 0.8),
            "Then a main road",
            (lambda: [FadeIn(bands[1]), *self.put("n1", T(names[1], 20, WHITE).move_to([LAB_X, LY[1], 0])),
                      *[FadeIn(self.dots[(1, v)]) for v in L1], Create(links[1])], 0.7),
            "Then the streets",
            (lambda: [FadeIn(bands[0]), *self.put("n0", T(names[0], 20, WHITE).move_to([LAB_X, LY[0], 0])),
                      *[FadeIn(self.dots[(0, v)]) for v in L0], Create(links[0])], 0.7),
        ])
        self.steps("Map it. Every vector is a house on the streets, linked to its nearest neighbours. A random few are also on main roads, "
                   "and fewer still on the motorway, with longer links between them.", [
            "Every vector",
            (lambda: [LaggedStart(*[Indicate(self.dots[(0, v)], color=WHITE, scale_factor=1.5) for v in L0], lag_ratio=0.06)], 1.1),
            "A random few",
            (lambda: [Create(drops), *self.put("n1", T("layer 1", 20, WHITE).move_to([LAB_X, LY[1], 0])),
                      *self.put("n0", T("layer 0", 20, WHITE).move_to([LAB_X, LY[0], 0]))], 0.8),
            "fewer still",
            (lambda: [*self.put("n2", T("layer 2", 20, WHITE).move_to([LAB_X, LY[2], 0])), Indicate(links[2], color=WHITE)], 0.8),
        ], after=0.3)
        self.stamp("layers")

        # ---------------- scene 4: the walk (the stepper) ----------------
        self.steps("Here's a small one, drawn in one direction so it fits: 16 vectors, three layers, and the query, the yellow dot.", [
            (lambda: [*self.cap("16 vectors, drawn in one direction (real ones have hundreds)", WHITE)], 0.6),
            "the query",
            (lambda: [*[FadeIn(qdots[k], scale=0.5) for k in LY], FadeIn(qlab)], 0.6),
        ])
        self.steps("The search starts at the single entry point on the motorway. It measures the distance to each neighbour, "
                   "and moves to any that is closer. 330 is closer: move. Then 570, closer still.", [
            (lambda: [*self.uncap(), self.state(2, 120, "at")], 0.6),
            "measures the distance",
            (lambda: [self.hop(2, 120, 330, WHITE, 0.6)], 0.7),
            "330 is closer",
            (lambda: [self.state(2, 120, "seen"), self.state(2, 330, "at"), *self.dist(2), links[2][0].animate.set_stroke(BLUE_M, 3)], 0.6),
            "Then 570",
            (lambda: [self.hop(2, 330, 570, WHITE, 0.5)], 0.6),
            (lambda: [self.state(2, 330, "seen"), self.state(2, 570, "at"), *self.dist(3), links[2][1].animate.set_stroke(BLUE_M, 3)], 0.5),
        ])
        self.steps("From 570, no neighbour on this layer is closer. So it drops to the same vector, one layer down. "
                   "There, 500 is closer: move. Nothing next to 500 is.", [
            "So it drops",
            (lambda: [self.state(2, 570, "seen"), dot_run(P(2, 570) + [0, -0.12, 0], P(1, 570) + [0, 0.12, 0], BLUE_M, 0.5)], 0.6),
            (lambda: [self.state(1, 570, "at")], 0.3),
            "500 is closer",
            (lambda: [self.hop(1, 570, 500, WHITE, 0.4)], 0.5),
            (lambda: [self.state(1, 570, "seen"), self.state(1, 500, "at"), links[1][4].animate.set_stroke(BLUE_M, 3)], 0.5),
            "Nothing next to 500",
            (lambda: [self.hop(1, 500, 440, WHITE, 0.4)], 0.5),
            (lambda: [*self.dist(5)], 0.3),
        ])
        beam = [470, 500, 530, 570]
        self.steps("On the streets, it stops taking the first better step, and keeps a beam: the 4 best vectors seen so far. "
                   "It explores around them until nothing left can beat the worst one it holds.", [
            (lambda: [self.state(1, 500, "seen"), dot_run(P(1, 500) + [0, -0.12, 0], P(0, 500) + [0, 0.12, 0], BLUE_M, 0.5)], 0.6),
            (lambda: [self.state(0, 500, "at")], 0.3),
            "keeps a beam",
            (lambda: [*self.cap("the beam: the 4 best vectors seen so far (ef = 4 here)", WHITE)], 0.5),
            (lambda: [self.hop(0, 500, 470, WHITE, 0.35), self.hop(0, 500, 530, WHITE, 0.35)], 0.45),
            (lambda: [self.state(0, 470, "at"), self.state(0, 530, "at")], 0.35),
            "It explores",
            (lambda: [self.hop(0, 470, 440, WHITE, 0.35), self.hop(0, 530, 570, WHITE, 0.35)], 0.45),
            (lambda: [self.state(0, 440, "seen"), self.state(0, 570, "at")], 0.35),
            (lambda: [self.hop(0, 570, 610, WHITE, 0.35)], 0.45),
            (lambda: [self.state(0, 610, "seen"), *self.dist(10)], 0.35),
            *[(lambda e=e: [links[0][L0.index(e)].animate.set_stroke(BLUE_M, 3)], 0.12) for e in (440, 470, 500, 530, 570)],
        ])
        self.steps("The beam is the answer: the four closest vectors, found with 10 distance calculations, where measuring every vector takes 16.", [
            (lambda: [*[self.state(0, v, "ok") for v in beam]], 0.6),
            "10 distance",
            (lambda: [Indicate(self.lab["dist"], color=GREEN_M, scale_factor=1.1)], 0.6),
            "takes 16",
            (lambda: self.cap("10 distances instead of 16; the gap grows with the data", WHITE), 0.6),
        ], after=0.3)
        self.stamp("walk")

        # ---------------- scene 5: the name ----------------
        self.steps("This is called HNSW, hierarchical navigable small world, from a 2016 paper by Malkov and Yashunin. "
                   "pgvector, an add-on that stores vectors in PostgreSQL, builds it, with 16 links per vector and a beam of 40 by default.", [
            (lambda: self.cap("HNSW: hierarchical navigable small world (Malkov and Yashunin, 2016)", WHITE), 0.6),
            "pgvector",
            (lambda: self.cap(M("pgvector defaults:  m = 16 links,  hnsw.ef_search = 40", 20, WHITE)), 0.6),
        ])
        self.steps("In the lab, the walk read 654 pages, where measuring every vector read 2,138, and it answered in under a millisecond.", [
            (lambda: self.count("HNSW: 654 pages, under 1 ms      exact: 2,138 pages, about 8 ms", GREEN_M), 0.6),
        ], after=0.3)

        # ---------------- scene 6: approximate ----------------
        self.steps("That's great, but there's a catch in the word walk. The search only goes where links lead. "
                   "A true neighbour behind a poor link can be missed.", [
            (lambda: [*self.drop("cnt"), *self.cap("the walk only goes where links lead", WHITE)], 0.6),
            "behind a poor link",
            (lambda: self.cap("a true neighbour behind a poor link can be missed", RED_M), 0.6),
        ])
        self.steps("The share of the true nearest neighbours that comes back is called recall. In the lab, with a beam of 10, "
                   "the walk found 89 percent of the true top 10. With the default beam of 40, all of them. "
                   "A bigger beam finds more, and does more work.", [
            "is called recall",
            (lambda: self.cap("recall: the share of the true nearest neighbours that comes back", WHITE), 0.6),
            "with a beam of 10",
            (lambda: self.count("beam 10: recall 0.89", RED_M), 0.5),
            "With the default",
            (lambda: self.count("beam 10: recall 0.89      beam 40: recall 1.00", WHITE), 0.5),
            "A bigger beam",
            (lambda: self.cap("a bigger beam: more found, more work", WHITE), 0.5),
        ], after=0.3)

        # ---------------- scene 7: the filter trap ----------------
        cands = VGroup(*[Square(0.2, stroke_color=TEAL_M, stroke_width=1.5).set_fill(fillc(TEAL_M, 0.5), 1)
                         .move_to([BX0 + 0.14 + 0.2855 * i, STRIP_Y, 0]) for i in range(40)])
        keep = [3, 15, 24, 36]
        ctitle = T("the walk's 40 candidates (ef_search = 40)", 19, TEAL_M).move_to([(BX0 + BX1) / 2, STRIP_T_Y, 0])
        self.steps("Now a trap. Support adds a filter that keeps about 1 complaint in 11, and asks for 10 results. "
                   "How many come back? Pause and guess.", [
            (lambda: [*self.drop("cnt"), *self.cap(M("... WHERE (1 row in 11 passes) ... LIMIT 10", 20, WHITE))], 0.6),
            "Pause and guess",
            (lambda: self.cap("how many of 10 come back?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("4, on average. pgvector applies the filter after the walk. The walk collected its 40 candidates, "
                   "and the filter kept about 4. Nothing fails, and nothing warns you.", [
            (lambda: [*self.uncap(), *self.count("asked for 10, got 4 on average", RED_M)], 0.6),
            "The walk collected",
            (lambda: [FadeIn(ctitle), LaggedStart(*[FadeIn(c, scale=0.5) for c in cands], lag_ratio=0.04)], 1.0),
            "the filter kept",
            (lambda: [*[cands[i].animate.set_fill(BLACK, 1).set_stroke(GREY_D) for i in range(40) if i not in keep],
                      *[cands[i].animate.set_fill(GREEN_M, 0.8).set_stroke(GREEN_M) for i in keep]], 0.7),
            "nothing warns you",
            (lambda: [Indicate(self.lab["cnt"], color=RED_M, scale_factor=1.1)], 0.7),
        ])
        self.steps("It's a sat-nav that finds 40 shops near you, throws away the closed ones, and proudly hands you 4. "
                   "Since pgvector 0.8.0, an iterative scan keeps walking until enough rows pass: 10 of 10.", [
            "Since pgvector",
            (lambda: self.cap(M("SET hnsw.iterative_scan = relaxed_order", 20, WHITE)), 0.6),
            "keeps walking",
            (lambda: [*[self.hop(0, a, b, WHITE, 0.35) for a, b in ((570, 610), (470, 440))]], 0.5),
            "10 of 10",
            (lambda: self.count("iterative scan: 10 of 10", GREEN_M), 0.5),
        ], after=0.3)
        self.stamp("filter")

        # ---------------- scene 8: memory ----------------
        self.steps("And a cost: the index took 41 MB for 17 MB of vectors. Every hop jumps to a random place, "
                   "so HNSW wants its whole graph in memory.", [
            (lambda: [FadeOut(VGroup(cands, ctitle)), *self.count("the index: 41 MB, for 17 MB of vectors", WHITE)], 0.6),
            "Every hop jumps",
            (lambda: [self.hop(2, 120, 570, WHITE, 0.5), self.hop(1, 220, 500, WHITE, 0.5)], 0.6),
            "whole graph in memory",
            (lambda: self.cap("random jumps: HNSW wants the whole graph in memory", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: to find nearest by meaning, walk the graph, big jumps on top and small steps at the bottom, "
                   "and keep a short list of the best. You trade a little recall for a lot of speed, so measure it.", [
            (lambda: [*self.drop("cnt"), *self.cap("big jumps on top, small steps at the bottom, a short list of the best", YELLOW_M, 26)], 0.6),
            "big jumps",
            (lambda: [*[links[2][i].animate(rate_func=there_and_back).set_stroke(YELLOW_M, 5) for i in range(2)]], 0.7),
            "small steps",
            (lambda: [*[links[0][L0.index(e)].animate(rate_func=there_and_back).set_stroke(YELLOW_M, 5) for e in (440, 470, 500, 530, 570)]], 0.7),
            "a little recall",
            (lambda: self.cap("trade a little recall for a lot of speed, and measure it", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.steps("One quick check. Your search returns 89 percent of the true top 10. What do you turn up? Pause and think.", [
            (lambda: [*self.uncap(), *self.count("recall 0.89", RED_M)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The beam, ef_search. In the lab, raising it from 10 to 40 found all 10, for a little more work.", [
            (lambda: [*self.uncap(), *self.count("hnsw.ef_search: 10 -> 40     recall 0.89 -> 1.00", GREEN_M)], 0.6),
            "found all 10",
            (lambda: [Indicate(self.lab["cnt"], color=GREEN_M, scale_factor=1.08)], 0.7),
        ], after=0.3)
        self.play(*self.cap("big jumps on top, small steps at the bottom, a short list of the best", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
