from sfz import *

SAY.insert(0, (r"\bsearch_after\b", "search after"))
SAY.insert(0, (r"\bids\b", "I Ds"))
SAY.insert(0, (r"\bOpenSearch\b", "open search"))

SX = {1: -5.0, 2: -2.5, 3: 0.0, 4: 2.5, 5: 5.0}       # shard columns
SY, SW, SH = -1.65, 2.2, 2.5                          # shard boxes
CX, CY, CW = 0.0, 2.75, 3.2                           # coordinator
MX0, MY0, MDY = 2.0, 3.32, 0.165                     # merged list: left edge, first row, row step
SC = {1: BLUE_M, 2: TEAL_M, 3: PURPLE_M, 4: GOLD_M, 5: GREEN_M}
SCORES = {1: [9.1, 8.4, 7.7, 6.2, 5.9, 5.1, 4.8, 4.0, 3.5, 3.1],
          2: [9.6, 9.0, 8.8, 7.9, 6.0, 5.6, 5.0, 4.4, 4.1, 3.8],
          3: [6.9, 6.5, 5.5, 5.2, 4.9, 4.6, 4.2, 3.9, 3.3, 3.0],
          4: [8.1, 7.2, 6.6, 5.8, 5.3, 4.7, 4.5, 3.6, 3.2, 2.9],
          5: [7.5, 7.0, 6.4, 6.1, 5.4, 4.3, 3.7, 3.4, 3.0, 2.7]}
TOP = sorted([(s, k, i) for k in SCORES for i, s in enumerate(SCORES[k])], reverse=True)[:10]


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along an arrow (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
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


def shard(k, sub="6 million notes", scolor=GREY_B):
    x = SX[k]
    r = RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=SC[k], stroke_width=3)
    r.set_fill(fill(SC[k]), 1).move_to([x, SY, 0])
    return VGroup(r, T(f"shard {k}", 21).move_to([x, SY + SH / 2 - 0.27, 0]), ssub(k, sub, scolor))


def ssub(k, s, color=GREY_B):
    return T(s, 15, color).move_to([SX[k], SY + SH / 2 - 0.58, 0])


def row_y(i):
    return SY + SH / 2 - 0.88 - i * 0.15


def sbar(k, i, score, color=None):
    """Row i of shard k's list: one id and its score, drawn as a bar as long as the score."""
    r = Rectangle(width=score * 0.18, height=0.1, stroke_width=0).set_fill(color or SC[k], 0.9)
    return r.move_to([SX[k] - 0.9 + r.width / 2, row_y(i), 0])


def mbar(j, score, k):
    r = Rectangle(width=score * 0.18, height=0.1, stroke_width=0).set_fill(SC[k], 0.9)
    return r.move_to([MX0 + r.width / 2, MY0 - j * MDY, 0])


def doc(color=WHITE, s=1.0):
    r = Rectangle(width=0.16, height=0.21, stroke_color=color, stroke_width=1.5).set_fill(BLACK, 1)
    ls = VGroup(*[Line([-0.05, 0.05 - 0.05 * i, 0], [0.05, 0.05 - 0.05 * i, 0], stroke_width=1, color=color) for i in range(3)])
    return VGroup(r, ls).scale(s)


def dense(k):
    """A shard's top 10,000: too many rows to draw, so a block of thin lines."""
    return VGroup(*[Line([SX[k] - 0.9, row_y(0) + 0.05 - j * 0.037, 0],
                         [SX[k] - 0.9 + 1.7 * (1 - j / 48), row_y(0) + 0.05 - j * 0.037, 0], stroke_width=1.5, color=SC[k])
                    for j in range(40)])


class QueryThenFetch(Base):
    """shard-09, section 2: a search over five shards. Fetching each shard's ten best documents whole moves 50 to return
    10. Query then fetch: each shard returns ids and scores of its top ten, the coordinator merges them into the global
    top ten (4 from shard 2, none from shard 3), then fetches only those ten. Page 1,000 (from 9,990) makes every shard
    find its top 10,000 and the coordinator sort 50,000; max_result_window stops it, search_after pages instead."""

    def construct(self):
        self.title_card("Searching every shard: query, then fetch", "ids and scores first, documents last")

        sh = {k: shard(k) for k in SX}
        q = chip("search: chargeback", GREY_B, 19).move_to([-4.6, CY, 0])
        self.steps("A search for chargeback notes runs on an index split into five shards. "
                   "Each shard indexes only its own documents, so any of them might hold the best matches.", [
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.6),
            "split into five",
            (lambda: [LaggedStart(*[FadeIn(sh[k], shift=0.1 * UP) for k in SX], lag_ratio=0.15)], 1.2),
            "Each shard indexes",
            (lambda: [*[glow(sh[k][0], SC[k], 1.03) for k in SX]], 1.0),
        ])

        co = box("coordinator", WHITE, w=CW, h=0.8, size=24).move_to([CX, CY, 0])
        ar = {k: Arrow([CX + (k - 3) * 0.55, CY - 0.42, 0], [SX[k], SY + SH / 2 + 0.06, 0], buff=0, stroke_width=2.5,
                       color=GREY_C, max_tip_length_to_length_ratio=0.04) for k in SX}
        grid = [doc().move_to([-6.05 + (n % 10) * 0.25, 2.1 - (n // 10) * 0.29, 0]) for n in range(50)]
        self.steps("The coordinator, the node that took the request, needs the global top ten. "
                   "The simplest plan: every shard sends back its ten best documents, whole.", [
            (lambda: [FadeIn(co)], 0.6),
            "needs the global",
            (lambda: [*[GrowArrow(ar[k]) for k in SX]], 0.8),
            (lambda: [*[flow(ar[k], GREY_A, 0.7) for k in SX]], 0.8),
            "every shard sends",
            (lambda: [LaggedStart(*[FadeIn(grid[n], shift=0.6 * DOWN) for n in range(50)], lag_ratio=0.06),
                      *[LaggedStart(*[flow(ar[k], WHITE, 0.6, back=True) for _ in range(3)], lag_ratio=0.4) for k in SX]], 2.2),
        ])

        wasted = T("50 sent, 10 used", 19, RED_M).move_to([-5.05, 0.55, 0])
        self.steps("That's fifty full documents to return ten. Forty were read, sent and thrown away.", [
            (lambda: [FadeIn(wasted, shift=0.1 * UP)], 0.7),
            "Forty were",
            (lambda: [*[grid[n][0].animate.set_stroke(RED_M) for n in range(10, 50)]], 0.6),
            (lambda: [*[grid[n].animate.set_opacity(0.15) for n in range(10, 50)]], 0.8),
        ])

        bars = {k: [sbar(k, i, s) for i, s in enumerate(SCORES[k])] for k in SX}
        self.steps("So the search runs in two phases. In the query phase, each shard scores its own matches "
                   "and sends back only ids and scores for its top ten.", [
            (lambda: [*[FadeOut(g) for g in grid], FadeOut(wasted), *[a.animate.set_color(GREY_C) for a in ar.values()]], 0.7),
            "In the query phase",
            (lambda: [*[flow(ar[k], GOLD_M, 0.7) for k in SX],
                      *[Transform(sh[k][2], ssub(k, "query phase: score", GOLD_M)) for k in SX]], 0.8),
            "each shard scores",
            (lambda: [*[LaggedStart(*[GrowFromEdge(b, LEFT) for b in bars[k]], lag_ratio=0.12) for k in SX]], 1.4),
            "and sends back",
            (lambda: [*[Transform(sh[k][2], ssub(k, "top 10: ids, scores", GOLD_M)) for k in SX]], 0.7),
        ])

        ups = []
        for j, (s, k, i) in enumerate(TOP):
            ups.append((bars[k][i], mbar(j, s, k)))
        topl = T("global top 10", 18, WHITE).move_to([4.85, MY0 - 4.5 * MDY, 0])
        cnt = T("4 from shard 2, none from shard 3", 18, GREY_B).move_to([4.6, 1.45, 0])
        self.steps("That's fifty small pairs. The coordinator merges them into the global top ten. "
                   "Here, four come from shard two, and none from shard three.", [
            (lambda: [*[LaggedStart(*[flow(ar[k], SC[k], 0.5, back=True) for _ in range(3)], lag_ratio=0.3) for k in SX]], 1.3),
            "The coordinator merges",
            (lambda: [LaggedStart(*[ReplacementTransform(b.copy(), m) for b, m in ups], lag_ratio=0.15), FadeIn(topl)], 1.8),
            "Here, four",
            (lambda: [glow(sh[2][0], TEAL_M, 1.03), FadeIn(cnt)], 0.8),
            "none from shard three",
            (lambda: [sh[3].animate.set_opacity(0.35), *[b.animate.set_opacity(0.3) for b in bars[3]]], 0.8),
        ])

        need = {1: 3, 2: 4, 4: 2, 5: 1}
        docs = [doc(SC[k]).move_to([MX0 + 1.95, MY0 - j * MDY, 0]).scale(0.75) for j, (s, k, i) in enumerate(TOP)]
        got = T("10 documents, from 4 shards", 18, GREEN_M).move_to([4.6, 1.45, 0])
        self.steps("In the fetch phase, it asks for just those ten documents, and only from the shards that hold them.", [
            (lambda: [FadeOut(cnt), *[Transform(sh[k][2], ssub(k, f"fetch: {need[k]} document" + ("s" if need[k] > 1 else ""), GREEN_M)) for k in need],
                      Transform(sh[3][2], ssub(3, "not asked", GREY_B)), ar[3].animate.set_opacity(0.2)], 0.8),
            (lambda: [*[flow(ar[k], GREEN_M, 0.7) for k in need]], 0.8),
            "and only from",
            (lambda: [*[flow(ar[k], GREEN_M, 0.7, back=True) for k in need],
                      LaggedStart(*[FadeIn(d, shift=0.2 * RIGHT) for d in docs], lag_ratio=0.1)], 1.3),
            (lambda: [FadeIn(got)], 0.5),
        ])

        page = chip("page 1,000: from 9,990, size 10", RED_M, 19).move_to([-4.3, CY, 0])
        blocks = {k: dense(k) for k in SX}
        self.steps("Now ask for page one thousand: skip 9,990 hits, return ten. "
                   "No shard knows which of its hits get skipped, so each must find its top 10,000.", [
            (lambda: [FadeOut(got), *[FadeOut(d) for d in docs], FadeOut(q), FadeIn(page, shift=0.1 * DOWN),
                      sh[3].animate.set_opacity(1), ar[3].animate.set_opacity(1),
                      *[Transform(sh[k][2], ssub(k, "6 million notes")) for k in SX]], 0.9),
            "No shard knows",
            (lambda: [*[flow(ar[k], GOLD_M, 0.6) for k in SX]], 0.7),
            "so each must",
            (lambda: [*[FadeOut(b) for k in SX for b in bars[k]], *[FadeIn(blocks[k]) for k in SX],
                      *[Transform(sh[k][2], ssub(k, "top 10,000", RED_M)) for k in SX]], 1.0),
        ])

        sortl = T("sorts 50,000 to return 10", 19, RED_M).move_to([4.6, 1.45, 0])
        self.steps("The coordinator sorts 50,000 ids and scores to return ten documents, "
                   "and the cost grows with every page.", [
            (lambda: [*[LaggedStart(*[flow(ar[k], RED_M, 0.45, back=True) for _ in range(6)], lag_ratio=0.2) for k in SX],
                      co[0].animate.set_stroke(RED_M)], 1.6),
            (lambda: [FadeIn(sortl)], 0.6),
            "and the cost",
            (lambda: [glow(co[0], RED_M, 1.04)], 0.9),
        ])

        win = chip("max_result_window: 10,000", GREY_B, 16, mono=True).move_to([-4.55, 2.0, 0])
        sa = chip("search_after: the last hit's sort values", GREEN_M, 17).move_to([-4.55, 2.0, 0])
        nxt = {k: [sbar(k, i, s * 0.35) for i, s in enumerate(SCORES[k])] for k in SX}
        self.steps("That's why OpenSearch stops at 10,000 by default. To page deeper, search_after passes the last hit's "
                   "sort values, so each shard sends only its next ten.", [
            (lambda: [FadeIn(win, shift=0.1 * DOWN)], 0.7),
            "To page deeper",
            (lambda: [FadeOut(win), FadeIn(sa, shift=0.1 * DOWN), FadeOut(sortl), co[0].animate.set_stroke(WHITE),
                      Transform(page, chip("page 1,000", GREY_B, 19).move_to(page))], 0.8),
            (lambda: [*[flow(ar[k], GREEN_M, 0.6) for k in SX]], 0.7),
            "so each shard",
            (lambda: [*[FadeOut(blocks[k]) for k in SX], *[FadeIn(b) for k in SX for b in nxt[k]],
                      *[Transform(sh[k][2], ssub(k, "next 10 only", GREEN_M)) for k in SX]], 0.9),
        ])

        self.steps("Ask every shard for ids and scores, fetch only the page you return, and page with search_after "
                   "rather than skipping.", [
            (lambda: [*[flow(ar[k], GOLD_M, 0.6) for k in SX]], 0.8),
            "fetch only",
            (lambda: [glow(co[0], GREEN_M, 1.04)], 0.9),
            "and page with",
            (lambda: [glow(sa[0], GREEN_M, 1.05)], 0.9),
        ])
        self.wait(0.6)
