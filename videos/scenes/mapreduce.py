from sfz import *

# The letter A naming a pod, worker or node: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))


def _layer(m):
    """Text above chips above arrows above boxes. Box fills are opaque, so without this an animated box
    rectangle is redrawn over its own label."""
    for x in m.get_family():
        if isinstance(x, Text):
            x.set_z_index(4)
        elif isinstance(x, Arrow):
            x.set_z_index(1)
        elif isinstance(x, RoundedRectangle) and 0 < x.get_fill_opacity() < 0.5:
            x.set_z_index(2)


def flash(m, color=YELLOW_M, buff=0.1, scale=1.05):
    """Highlight a box without filling it (Indicate turns an opaque box into a solid block):
    a quick pulse plus an outline drawn and faded around it."""
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.14, stroke_width=4)
    return AnimationGroup(m.animate(rate_func=there_and_back).scale(scale),
                          Succession(Create(r, run_time=0.5), FadeOut(r, run_time=0.5)))


class Layered(VoiceScene):
    def play(self, *anims, **kw):
        for a in anims:
            _layer(a.mobject)
            if getattr(a, "target_mobject", None) is not None:
                _layer(a.target_mobject)
        for m in self.mobjects:
            _layer(m)
        super().play(*anims, **kw)
        for m in self.mobjects:
            _layer(m)


class MapReduce(Layered):
    """data-02: map, partition, shuffle and reduce on three machines, then a combiner that shrinks the shuffle."""

    def construct(self):
        self.title_card("MapReduce", "map, shuffle, reduce")

        ROWS = (1.8, 0.0, -1.8)
        NX, NW, RX, RW, FH = -3.75, 5.7, 4.6, 4.0, 1.45
        OFF = -NX                    # the nodes start centred, then slide left when the reducers appear
        KC = {"declined": GOLD_M, "approved": GREEN_M, "refunded": PURPLE_M}
        RED_OF = {"declined": 0, "approved": 1, "refunded": 2}
        blocks = [["approved", "declined", "approved"], ["approved", "refunded", "approved"], ["declined", "approved", "refunded"]]

        def frame(x, y, w, color=GREY_B):
            r = RoundedRectangle(corner_radius=0.14, width=w, height=FH, stroke_color=color, stroke_width=2.5).move_to([x, y, 0])
            return r.set_fill(BLACK, opacity=1)

        def content(x, y):
            return np.array([x, y - 0.2, 0])

        nodes, lines = VGroup(), VGroup()
        for i, (y, words) in enumerate(zip(ROWS, blocks)):
            f = frame(NX, y, NW)
            lab = T(f"node {'ABC'[i]}, block {i + 1}", 22, GREY_B).move_to([0, y + 0.42, 0]).align_to(f, LEFT).shift(0.22 * RIGHT)
            nodes.add(VGroup(f, lab).shift(OFF * RIGHT))
            lines.add(T("   ".join(words), 26).move_to(content(NX + OFF, y)))

        self.beat("A payment company logs every card authorization. The log is too big for one machine, so it is stored in blocks on three machines.",
                  LaggedStart(*[FadeIn(VGroup(n, l), shift=0.2 * RIGHT) for n, l in zip(nodes, lines)], lag_ratio=0.25), run_time=2.6)

        self.beat("You want to count each status: approved, declined, refunded. Pulling the whole log onto one machine would push every byte through one network link. So each machine works on the block it already has.",
                  LaggedStart(*[Indicate(l, color=YELLOW_M, scale_factor=1.06) for l in lines], lag_ratio=0.3), run_time=3.0)

        def pair(word, n=1, color=WHITE):
            return chip(f"{word}, {n}", color, 20)

        def row_of(chips, y):
            return VGroup(*chips).arrange(RIGHT, buff=0.12).move_to(content(NX, y))

        pairs = [row_of([pair(w) for w in words], y).shift(OFF * RIGHT) for words, y in zip(blocks, ROWS)]
        self.beat("First, map. Each machine reads its block and turns every word into a pair: the word, and the number one.",
                  *[ReplacementTransform(l, p) for l, p in zip(lines, pairs)], run_time=2.0)

        reds = VGroup()
        for k, (word, y) in enumerate(zip(["declined", "approved", "refunded"], ROWS)):
            f = frame(RX, y, RW, KC[word])
            lab = T(f"reducer {k}", 22, KC[word]).move_to([0, y + 0.42, 0]).align_to(f, LEFT).shift(0.22 * RIGHT)
            reds.add(VGroup(f, lab))
        self.beat("That makes nine pairs. Now, which machine counts approved? Three reducers will do the counting.",
                  VGroup(*nodes, *pairs).animate(run_time=1.0).shift(OFF * LEFT),
                  Succession(Wait(0.6), LaggedStart(*[FadeIn(r, shift=0.2 * LEFT) for r in reds], lag_ratio=0.25)), run_time=2.0)

        rule = M("reducer = hash(key) % 3", 24, YELLOW_M).move_to([0, 3.1, 0])
        self.beat("Each machine hashes the key and takes the remainder after dividing by three. That number picks the reducer.",
                  Write(rule), run_time=1.8)

        def color_pair(c, word):
            col = KC[word]
            return AnimationGroup(c[0].animate.set_stroke(col).set_fill(col, opacity=0.18), c[1].animate.set_color(col))

        allc = [(c, w) for p, words in zip(pairs, blocks) for c, w in zip(p, words)]
        appr = [c for c, w in allc if w == "approved"]
        self.beat("The same key gives the same number on every machine, so approved always goes to reducer one.",
                  Succession(LaggedStart(*[color_pair(c, w) for c, w in allc], lag_ratio=0.06, run_time=1.4),
                             AnimationGroup(*[Indicate(c, color=GREEN_M, scale_factor=1.05) for c in appr], flash(reds[1], GREEN_M, scale=1.0), run_time=1.0)),
                  run_time=2.8)

        sent = T("pairs sent over the network: 9", 26).move_to([0, -3.1, 0])

        def dim(c, on=True):
            return AnimationGroup(c[0].animate.set_stroke(opacity=0.35 if on else 1).set_fill(opacity=0.05 if on else 0.18),
                                  c[1].animate.set_opacity(0.35 if on else 1))

        def shuffle(chip_word_pairs, texts):
            copies = [(c.copy(), w) for c, w in chip_word_pairs]
            for cp, _ in copies:
                self.add(cp)
            moves = [cp.animate.move_to(content(RX, ROWS[RED_OF[w]])).scale(0.7).set_opacity(0) for cp, w in copies]
            dims = [dim(c) for c, _ in chip_word_pairs]
            steps = [AnimationGroup(LaggedStart(*moves, lag_ratio=0.1, run_time=2.6), *dims)]
            if texts:
                steps.append(AnimationGroup(*[FadeIn(t) for t in texts], run_time=0.6))
            return copies, Succession(*steps)

        lists = [T("declined: 1, 1", 24, GOLD_M), T("approved: 1, 1, 1, 1, 1", 24, GREEN_M), T("refunded: 1, 1", 24, PURPLE_M)]
        for t, y in zip(lists, ROWS):
            t.move_to(content(RX, y))
        copies, anim = shuffle(allc, [])
        self.beat("Now the shuffle. Every pair crosses the network to its reducer.", anim, FadeIn(sent), run_time=3.2)
        for cp, _ in copies:
            self.remove(cp)

        self.beat("Each reducer sorts what it got by key. Reducer one now holds all five approved pairs, from three different machines.",
                  LaggedStart(*[FadeIn(t, shift=0.1 * RIGHT) for t in lists], lag_ratio=0.2),
                  Succession(Wait(1.2), Indicate(lists[1], color=GREEN_M, scale_factor=1.08)), run_time=3.0)

        totals = [T("declined = 2", 26, GOLD_M), T("approved = 5", 26, GREEN_M), T("refunded = 2", 26, PURPLE_M)]
        for t, y in zip(totals, ROWS):
            t.move_to(content(RX, y))
        self.beat("Reduce adds them up: approved five, declined two, refunded two. No reducer ever needs to ask another, because each key lives in one place.",
                  *[ReplacementTransform(a, b) for a, b in zip(lists, totals)], run_time=1.6)

        # --- the combiner
        self.beat("Look at what crossed the network, though. The same pair, approved one, again and again.",
                  *[dim(c, False) for c, _ in allc], *[FadeOut(t) for t in totals],
                  Succession(Wait(0.9), AnimationGroup(*[Indicate(c, color=GREEN_M, scale_factor=1.05) for c in appr])), run_time=2.6)

        def combine(p, y, word_a, word_b):
            # p = [a, b, a]  ->  [a x2, b]
            merged = pair(word_a, 2, KC[word_a])
            target = VGroup(merged, p[1].copy()).arrange(RIGHT, buff=0.12).move_to(content(NX, y))
            merged.move_to(target[0])
            return merged, AnimationGroup(p[2].animate.move_to(target[0]).set_opacity(0), ReplacementTransform(p[0], merged),
                                          p[1].animate.move_to(target[1]))

        mA, cbA = combine(pairs[0], ROWS[0], "approved", "declined")
        mB, cbB = combine(pairs[1], ROWS[1], "approved", "refunded")
        self.beat("A combiner runs the reduce step on each machine, before the shuffle. Node A turns its two approved ones into one pair: approved, two. Node B does the same.",
                  Succession(Wait(2.2), cbA, Wait(1.2), cbB), run_time=6.0)
        self.remove(pairs[0][2], pairs[1][2])

        after = [(mA, "approved"), (pairs[0][1], "declined"), (mB, "approved"), (pairs[1][1], "refunded")] + list(zip(pairs[2], blocks[2]))
        lists2 = [T("declined: 1, 1", 24, GOLD_M), T("approved: 2, 2, 1", 24, GREEN_M), T("refunded: 1, 1", 24, PURPLE_M)]
        for t, y in zip(lists2, ROWS):
            t.move_to(content(RX, y))
        sent7 = T("pairs sent over the network: 7", 26).move_to(sent)
        copies, anim = shuffle(after, lists2)
        self.beat("Now seven pairs cross the network instead of nine, and the reducers still get the same answer.",
                  Succession(anim, Wait(0.3), AnimationGroup(*[ReplacementTransform(a, b) for a, b in zip(lists2, [t.copy() for t in totals])])),
                  Transform(sent, sent7), run_time=4.4)
        for cp, _ in copies:
            self.remove(cp)

        real = T("one real map task: 1,000,000 pairs, or 3 with a combiner", 26, YELLOW_M).move_to(sent)
        self.beat("On a real log, a map task reads a million events. With a combiner, it sends three pairs, one per status, instead of a million.",
                  FadeOut(sent), FadeIn(real), run_time=1.4)

        self.beat("Map runs where the data lives. A hash sends every key to exactly one reducer. And a combiner shrinks what has to cross the network.",
                  Succession(AnimationGroup(*[flash(n, WHITE, buff=0.05, scale=1.0) for n in nodes], run_time=1.2),
                             Indicate(rule, color=YELLOW_M, run_time=1.2),
                             Indicate(real, color=YELLOW_M, run_time=1.2)), run_time=4.0)
        self.wait(0.6)
