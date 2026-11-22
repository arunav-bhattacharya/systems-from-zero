from sfz import *

SAY.insert(0, (r"\bM-00(\d\d)\b", lambda m: "M zero zero " + " ".join(m.group(1))))
SAY.insert(0, (r"\bBM25\b", "B M twenty-five"))
SAY.insert(0, (r"\bOpenSearch\b", "Open Search"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
Q_POS = np.array([-4.7, 2.95, 0])          # the request chip, top left
COORD = np.array([-0.6, 2.95, 0])          # the coordinating node
HITS_X, HITS_Y = 4.35, 3.05                # the merged hit list, top right
X3 = [-4.2, 0.0, 4.2]
X5 = [-5.4, -2.7, 0.0, 2.7, 5.4]
PY, RY = 0.75, -0.3                        # primary row, replica row
RET_Y = [-1.2, -1.7]                     # what a shard sends back
CNT_Y, BAR_Y, CAP_Y = -2.45, -2.9, -3.35

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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    # captions, a counter line, and labels that swap in place
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

    def count(self, s, color=WHITE, size=24):
        return self.put("cnt", fit(T(s, size, color), 13.0).move_to([0, CNT_Y, 0]))

    def query(self, s, color=YELLOW_M):
        """A query chip; a list of strings stacks into lines so long filters stay readable."""
        lines = s if isinstance(s, list) else [s]
        t = VGroup(*[M(x, 19) for x in lines]).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=t.height + 0.26, stroke_color=color, stroke_width=2.5)
        r.set_fill(color, opacity=0.18)
        return self.put("q", fit(VGroup(r, t.move_to(r)), 3.9).move_to(Q_POS + 0.25 * LEFT))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def copy_box(label, color, x, y, w=3.1, size=24, dashed=False):
    r = RoundedRectangle(corner_radius=0.1, width=w, height=0.74, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.12), 1)
    if dashed:
        r = DashedVMobject(r, num_dashes=40).set_fill(fillc(color, 0.12), 1)
    return VGroup(r, T(label, size, color)).move_to([x, y, 0])


def ret_chip(s, color, x, y, w=2.4):
    t = M(s, 19, WHITE)
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.4, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.2), 1)
    return VGroup(r, fit(t, w - 0.2).move_to(r)).move_to([x, y, 0])


def hit_list(rows, color=WHITE, title="hits"):
    g = VGroup(T(title, 20, GREY_B))
    for i, (a, b) in enumerate(rows):
        g.add(VGroup(M(a, 20, color), M(b, 20, GREY_B)).arrange(RIGHT, buff=0.45))
    g.arrange(DOWN, buff=0.1, aligned_edge=LEFT)
    return g.move_to([HITS_X, HITS_Y - g.height / 2 + 0.1, 0])


PLAIN = [("M-0045", "0.769"), ("M-0042", "0.566"), ("M-0043", "0.284"), ("M-0054", "0.284")]
DFS = [("M-0042", "0.929"), ("M-0045", "0.850"), ("M-0043", "0.735"), ("M-0054", "0.735")]


class QueryThenFetch(Base):
    """shard-09, section 2. A write of M-0054 hashes to shard 2, goes to its primary and on to the replica (total 2,
    successful 2); a search for "northwind bikes" asks one copy of every shard; the query phase (ids and scores) and the
    fetch phase (the page's documents); from 9990 + size 10 on 5 shards = 50,000 hits sorted, max_result_window 10,000,
    search_after; the slowest shard (0.99^10, about 90%); each shard's own word counts and dfs_query_then_fetch; a check."""

    def query(self, s, color=YELLOW_M):
        return self.put("q", fit(chip(s, color, 20, mono=True), 3.2).move_to(Q_POS))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Three volumes, one search", "why a search asks every shard")

        coord = mbox("coordinating node", PURPLE_M, w=3.0, h=0.62, size=20).move_to(COORD)
        prim = [copy_box(f"shard {i}: primary", BLUE_M, x, PY) for i, x in enumerate(X3)]
        repl = [copy_box(f"shard {i}: copy", GREY_B, x, RY) for i, x in enumerate(X3)]
        vols = [copy_box(f"volume {i + 1}", GOLD_M, x, PY) for i, x in enumerate(X3)]
        photo = [copy_box(f"photocopy {i + 1}", GOLD_M, x, RY, dashed=True) for i, x in enumerate(X3)]
        idx = [T("index at the back", 20, GOLD_M).move_to([x, PY + 0.62, 0]) for x in X3]

        def ptop(i, xs=X3):
            return np.array([xs[i], PY + 0.42, 0])

        cbot = COORD + 0.36 * DOWN

        # ---------------- scene 1: the question ----------------
        self.steps("Support types northwind bikes into the shop search. The search index is split over three machines.", [
            (lambda: self.query('"northwind bikes"'), 0.6),
            "split over three",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * UP) for p in prim], lag_ratio=0.25)], 1.0),
        ])
        self.steps("When we look up one shop by its id, we know exactly which machine to ask. But a word isn't an id.", [
            "by its id",
            (lambda: self.cap("an id: we know which machine to ask", WHITE), 0.6),
            "But a word",
            (lambda: self.cap("a word isn't an id", YELLOW_M), 0.6),
        ])
        self.steps("So how does the search find the ten best shops? And why won't most sites let you jump straight to page 1,000? Hold both questions.", [
            (lambda: self.cap("how does it find the ten best shops?", YELLOW_M), 0.6),
            "page 1,000",
            (lambda: self.cap("and why can't you jump to page 1,000?", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 2: the encyclopedia ----------------
        self.steps("Picture an encyclopedia in three volumes, each with its own index at the back.", [
            (lambda: [*self.uncap(), *self.query('"bicycles"', GOLD_M), *[ReplacementTransform(p, v) for p, v in zip(prim, vols)]], 0.9),
            "its own index",
            (lambda: [LaggedStart(*[FadeIn(t) for t in idx], lag_ratio=0.2)], 0.7),
        ])
        self.steps("To find every page about bicycles, you open all three indexes and put the pages together. No volume can tell you what the others hold.", [
            "you open all three",
            (lambda: [LaggedStart(*[dot_run(Q_POS + 0.35 * DOWN, ptop(i) + 0.5 * UP, YELLOW_M, 0.6) for i in range(3)], lag_ratio=0.3)], 1.2),
            "No volume",
            (lambda: self.cap("no volume knows what the others hold", WHITE), 0.6),
        ])
        self.steps("And a careful librarian keeps a photocopy of every volume on a different shelf.", [
            "a photocopy",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * DOWN) for p in photo], lag_ratio=0.25)], 1.0),
        ], after=0.3)
        prim = [copy_box(f"shard {i}: primary", BLUE_M, x, PY) for i, x in enumerate(X3)]
        self.steps("OpenSearch, a free search program, works the same way. Each volume is a shard, a piece of the search index.", [
            (lambda: self.cap("OpenSearch: a free search program", WHITE), 0.6),
            "Each volume is a shard",
            (lambda: [*[ReplacementTransform(v, p) for v, p in zip(vols, prim)], *self.cap("volume = shard, a piece of the search index", WHITE)], 0.9),
        ])
        self.steps("Its index at the back is the shard's inverted index, a list of every word with the documents that contain it.", [
            "inverted index",
            (lambda: [*[t.animate.set_color(BLUE_M) for t in idx], *self.cap("index at the back = inverted index: each word, with the documents that hold it", WHITE)], 0.7),
        ])
        self.steps("And each photocopy is a replica, a copy of the shard kept on another machine.", [
            "a replica",
            (lambda: [*[ReplacementTransform(p, r) for p, r in zip(photo, repl)], FadeOut(VGroup(*idx)),
                      *self.cap("photocopy = replica, a copy on another machine", WHITE)], 0.9),
        ], after=0.3)
        self.stamp("map")

        # ---------------- scene 3: a write goes to one shard ----------------
        self.steps("First, a write. A new shop, M-0054, can arrive at any node, which coordinates the request.", [
            (lambda: [*self.uncap(), *self.query("PUT merchants/_doc/M-0054", GREEN_M)], 0.6),
            "any node",
            (lambda: [FadeIn(coord, shift=0.1 * DOWN), dot_run(Q_POS + 1.6 * RIGHT, COORD + 1.5 * LEFT, GREEN_M, 0.5)], 0.7),
        ])
        self.steps("It hashes the id, and the hash says shard 2. So it sends the shop to shard 2's primary copy, which passes it on to the replica.", [
            "the hash says",
            (lambda: self.cap("hash(M-0054) → shard 2", WHITE), 0.6),
            "sends the shop",
            (lambda: [dot_run(cbot, ptop(2), GREEN_M, 0.8)], 0.85),
            (lambda: [glow(prim[2][0], GREEN_M, 1.04)], 0.5),
            "passes it on",
            (lambda: [dot_run([X3[2] + 1.7, PY, 0], [X3[2] + 1.7, RY, 0], GREEN_M, 0.5), glow(repl[2][0], GREEN_M, 1.04)], 0.7),
        ])
        self.steps("Only when both have it does the answer come back: total 2, successful 2. One shard, two copies, nobody else bothered.", [
            (lambda: [dot_run(ptop(2), cbot, GREEN_M, 0.7)], 0.75),
            (lambda: self.count('"_shards": {"total": 2, "successful": 2}', GREEN_M, 22), 0.5),
            "nobody else",
            (lambda: [*[glow(prim[i][0], GREY_B, 1.02) for i in (0, 1)], *self.cap("a write: one shard, two copies", WHITE)], 0.7),
        ], after=0.3)

        # ---------------- scene 4: a search asks everyone ----------------
        q_q = '"northwind bikes"'
        self.steps("Now the search. You might think it works the same way: find the right shard and ask it. But which shard holds northwind?", [
            (lambda: [*self.drop("cnt"), *self.query(q_q)], 0.6),
            "find the right shard",
            (lambda: self.cap("find the right shard and ask it?", PURPLE_M), 0.6),
        ])
        self.steps("Each shard's index covers only its own shops, like the index at the back of one volume. No shard can say which other shards hold matches.", [
            (lambda: self.cap("each shard's index covers only its own shops", WHITE), 0.6),
            "No shard can say",
            (lambda: [*[glow(p[0], RED_M, 1.03) for p in prim]], 0.7),
        ])
        chosen = [0, 1, 0]   # which copy each shard's request goes to: primary (0) or replica (1)

        def target(i):
            return ptop(i) if chosen[i] == 0 else np.array([X3[i] - 1.7, RY, 0])

        self.steps("So the coordinator asks them all. It sends the query to one copy of every shard, primary or replica, "
                   "picking the copy that has answered fastest lately.", [
            "asks them all",
            (lambda: [*self.cap("a search: one copy of every shard", YELLOW_M)], 0.5),
            "one copy of every shard",
            (lambda: [*[dot_run(cbot, target(i), YELLOW_M, 0.8) for i in range(3)]], 0.85),
            (lambda: [glow(prim[0][0], YELLOW_M, 1.04), glow(repl[1][0], YELLOW_M, 1.04), glow(prim[2][0], YELLOW_M, 1.04)], 0.6),
            "picking the copy",
            (lambda: self.cap("each time, the copy that has answered fastest lately", WHITE), 0.6),
        ], after=0.3)
        self.stamp("fanout")

        # ---------------- scene 5: query, then fetch ----------------
        rets = [VGroup(ret_chip("id, score", BLUE_M, x, RET_Y[0]), ret_chip("id, score", BLUE_M, x, RET_Y[1])) for x in X3]
        merged = hit_list(PLAIN, WHITE, "merged ranking")
        self.steps("Here's the trick that keeps it cheap. In the first round, each shard scores its own shops with BM25, the ranking formula, "
                   "and sends back only ids and scores, for the best few it has. No documents yet. That's the query phase.", [
            "In the first round",
            (lambda: self.count("round 1: the query phase", YELLOW_M), 0.5),
            "scores its own",
            (lambda: [*[glow(p[0], BLUE_M, 1.03) for p in prim]], 0.6),
            "sends back only",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in rets], lag_ratio=0.2)], 0.9),
            (lambda: [*[dot_run(target(i), cbot, BLUE_M, 0.7) for i in range(3)]], 0.75),
            "No documents",
            (lambda: self.cap("only ids and scores travel; no documents yet", WHITE), 0.6),
        ])
        self.steps("The coordinator merges those short lists into one ranking. Then the second round asks for the full documents of the page it will show, "
                   "and nothing else. That's the fetch phase.", [
            (lambda: [FadeIn(merged, shift=0.1 * LEFT), glow(coord[0], PURPLE_M, 1.05)], 0.8),
            "the second round",
            (lambda: [*self.count("round 2: the fetch phase", YELLOW_M)], 0.5),
            "the full documents",
            (lambda: [dot_run(cbot, ptop(0), YELLOW_M, 0.6), dot_run(cbot, ptop(2), YELLOW_M, 0.6)], 0.65),
            (lambda: [dot_run(ptop(0), cbot, GREEN_M, 0.6), dot_run(ptop(2), cbot, GREEN_M, 0.6)], 0.65),
            "nothing else",
            (lambda: self.cap("then only the page's documents are fetched", WHITE), 0.6),
        ])
        self.steps("Query, then fetch. Like jotting page numbers from each volume's index before you carry any book to the desk.", [
            (lambda: self.cap("query, then fetch", YELLOW_M, 28), 0.6),
            "Like jotting",
            (lambda: [LaggedStart(*[Indicate(r, color=YELLOW_M, scale_factor=1.06) for r in rets], lag_ratio=0.2)], 1.0),
        ], after=0.3)
        self.stamp("qtf")

        # ---------------- scene 6: page 1,000 ----------------
        prim5 = [copy_box(f"shard {i}", BLUE_M, x, PY, w=2.2) for i, x in enumerate(X5)]
        self.steps("Now ask for a deep page: skip 9,990 hits and show 10, on an index with five shards. How many hits does the coordinator have to sort? Pause and guess.", [
            (lambda: [*self.drop("cnt"), *self.uncap(), FadeOut(merged), FadeOut(VGroup(*rets)), FadeOut(VGroup(*prim, *repl)),
                      *self.query('{ "from": 9990, "size": 10 }')], 0.7),
            "five shards",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * UP) for p in prim5], lag_ratio=0.15)], 0.9),
            "Pause and guess",
            (lambda: self.cap("how many hits to sort?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        rets5 = [ret_chip("top 10,000", RED_M, x, RET_Y[0], w=2.2) for x in X5]
        self.steps("50,000. No shard knows where its hits fall in the overall order, so each must send its own top 10,000, "
                   "and the coordinator sorts all 50,000 to return 10.", [
            (lambda: [*self.uncap(), *[dot_run(cbot, ptop(i, X5), YELLOW_M, 0.7) for i in range(5)]], 0.75),
            "each must send",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in rets5], lag_ratio=0.15)], 0.9),
            (lambda: [*[dot_run(ptop(i, X5), cbot, RED_M, 0.7) for i in range(5)]], 0.75),
            "sorts all 50,000",
            (lambda: self.count("5 shards × 10,000 = 50,000 hits sorted, to return 10", RED_M), 0.6),
        ])
        self.steps("That's five librarians each copying out ten thousand page numbers so you can read the last ten.", [
            (lambda: [LaggedStart(*[glow(r[0], RED_M, 1.06) for r in rets5], lag_ratio=0.15)], 1.0),
        ], after=0.3)
        self.steps("So OpenSearch stops skip plus size at 10,000 by default, with a setting called max result window. "
                   "To go deeper, search after carries on from the last hit of the page before. And that's why page 1,000 is out of reach.", [
            (lambda: self.cap(M("index.max_result_window: from + size ≤ 10,000", 22, WHITE)), 0.6),
            "To go deeper",
            (lambda: self.cap(M("search_after: carry on from the last hit of the page before", 22, GREEN_M)), 0.6),
            "page 1,000",
            (lambda: self.cap("page 1,000: every shard would rank everything before it", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("deep")

        # ---------------- scene 7: the slowest shard ----------------
        DX = [-5.4 + 1.2 * k for k in range(10)]
        dots = VGroup(*[Dot(radius=0.12, color=GREEN_M).move_to([x, RET_Y[1] + 0.05, 0]) for x in DX])
        self.steps("There's a second cost. A search is as slow as its slowest shard.", [
            (lambda: [*self.drop("cnt"), *self.uncap(), FadeOut(VGroup(*rets5)), *self.query("any search")], 0.6),
            "slowest shard",
            (lambda: [glow(prim5[3][0], RED_M, 1.05), *self.cap("a search is as slow as its slowest shard", WHITE)], 0.7),
        ])
        self.steps("Say each shard answers in time 99% of the time. Then all 10 shards of a search answer in time only 0.99 to the power 10, about 90% of the time.", [
            "each shard",
            (lambda: [FadeIn(dots), *self.count("each shard: on time 99% of the time", WHITE)], 0.6),
            "all 10 shards",
            (lambda: [LaggedStart(*[Indicate(d, color=YELLOW_M, scale_factor=1.6) for d in dots], lag_ratio=0.08)], 1.0),
            "0.99 to the power",
            (lambda: [dots[6].animate.set_color(RED_M), *self.count("all 10 on time: 0.99¹⁰ ≈ 0.90, about 90%", RED_M)], 0.6),
        ], after=0.3)

        # ---------------- scene 8: each volume counts on its own ----------------
        prim = [copy_box(f"shard {i}: primary", BLUE_M, x, PY) for i, x in enumerate(X3)]
        plain = hit_list(PLAIN, WHITE, "plain search")
        self.steps("One more surprise. BM25 counts how rare a word is, and each shard counts only its own shops.", [
            (lambda: [FadeOut(dots), *self.drop("cnt"), FadeOut(VGroup(*prim5)), *self.query(q_q)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(p) for p in prim], lag_ratio=0.2), *self.uncap()], 0.8),
            "each shard counts",
            (lambda: self.cap("how rare is a word? each shard counts its own shops", WHITE), 0.6),
        ])
        self.steps("With millions per shard, they agree. With a handful, they don't. In the lesson's lab, the plain search ranks M-0045 first.", [
            "With a handful",
            (lambda: [*[glow(p[0], RED_M, 1.03) for p in prim]], 0.6),
            "the plain search",
            (lambda: [FadeIn(plain, shift=0.1 * LEFT)], 0.7),
        ])
        dfs = hit_list(DFS, GREEN_M, "dfs_query_then_fetch")
        self.steps("Ask for D F S query then fetch, which adds a first round to collect those counts from every shard, "
                   "and M-0042, which has both words, comes first again.", [
            "adds a first round",
            (lambda: [*[dot_run(cbot, ptop(i), GREY_B, 0.6) for i in range(3)], *self.count("round 0: collect the word counts from every shard", WHITE)], 0.7),
            (lambda: [*[dot_run(ptop(i), cbot, GREY_B, 0.6) for i in range(3)]], 0.65),
            "comes first again",
            (lambda: [FadeOut(plain), FadeIn(dfs, shift=0.1 * LEFT)], 0.7),
            (lambda: [Indicate(dfs[1], color=GREEN_M, scale_factor=1.08)], 0.6),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: a search asks every shard, and more shards add work to every search.", [
            (lambda: [*self.drop("cnt"), *self.cap("a search asks every shard", YELLOW_M, 26)], 0.6),
            "more shards",
            (lambda: [*[dot_run(cbot, ptop(i), YELLOW_M, 0.6) for i in range(3)], *self.cap("more shards add work to every search", YELLOW_M, 26)], 0.7),
        ], after=0.3)
        self.steps("One quick check. Support fetches shop M-0054 by its id. How many shards get asked? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(dfs), *self.query("GET merchants/_doc/M-0054", GREEN_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("how many shards?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Just one. The id hashes to shard 2, so it goes straight there. Words make you ask everyone; ids don't.", [
            (lambda: [*self.uncap(), dot_run(cbot, ptop(2), GREEN_M, 0.7)], 0.75),
            (lambda: [glow(prim[2][0], GREEN_M, 1.05), *self.count("hash(M-0054) → shard 2: one shard", GREEN_M)], 0.6),
            "Words make you",
            (lambda: self.cap("words ask every shard; ids ask one", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.wait(2.0)
