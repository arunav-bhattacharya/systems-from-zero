from sfz import *

SAY.insert(0, (r"\bcard_id\b", "card I D"))
SAY.insert(0, (r"\b4242\b", "forty-two forty-two"))
SAY.insert(0, (r"\bINCLUDE\b", "include"))
SAY.insert(0, (r"\bVACUUM\b", "vacuum"))

def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def via(points, color=YELLOW_M, run_time=0.9):
    """A dot that runs along a polyline and stays invisible until its turn."""
    pts = [np.array(p, dtype=float) for p in points]
    path = VMobject().set_points_as_corners(pts)
    d = Dot(radius=0.08, color=color).move_to(pts[0]).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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



NC, NR, SQ, PITCH = 20, 10, 0.27, 0.345      # heap grid: columns, rows, square size, pitch
GX, GY = -0.35, 1.45                          # centre of the top-left square
HX = 3.0                                      # centre of the heap panel
ROOT = np.array([-4.1, 1.6, 0])
INNER = [np.array([x, 0.35, 0]) for x in (-5.85, -4.65, -3.45, -2.25)]
LEAF = [np.array([-6.2 + 0.78 * k, -0.9, 0]) for k in range(6)]
KIDS = {0: (0, 1), 1: (2,), 2: (3, 4), 3: (5,)}
rng = np.random.default_rng(42)
CARD = sorted(rng.choice(NC * NR, 14, replace=False).tolist())          # the 14 heap pages with card 4242's rows
RARE = set(rng.choice(NC * NR, 14, replace=False).tolist())             # pages with no succeeded payment (7%)


def sq_pos(k):
    return np.array([GX + (k % NC) * PITCH, GY - (k // NC) * PITCH, 0])


def node(p, w, h, label=None, color=GREY_B, size=18):
    r = RoundedRectangle(corner_radius=0.08, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(fill(color, 0.1), 1)
    r.move_to(p)
    return VGroup(r, T(label, size).move_to(p)) if label else VGroup(r)


def edge(a, b, color=GREY_D):
    return Line(a, b, stroke_width=2, color=color)


def counter(tr, cc):
    """The running page count; cc["c"] holds its colour."""
    return always_redraw(lambda: T(f"pages read: {int(round(tr.get_value())):,}", 28, cc["c"]).move_to([HX, -2.55, 0]))


def query(s, color=GREY_B):
    return chip(s, color, 19, mono=True).move_to([-4.1, 3.05, 0])


class IndexScan(Base):
    """store-07, section 0 (with sections 3 and 4): card 4242's 14 payments among 1,000,478 rows in 23,818 pages. A
    sequential scan reads every page (about a quarter of a second); the B+tree on card_id descends root, inner page and
    leaf and reads only the 14 heap pages, 17 in all. With INCLUDE, an index-only scan never reads the heap (once VACUUM has
    set the visibility map). For status = 'succeeded', 93% of rows, the planner still reads the table straight through."""

    def construct(self):
        self.title_card("Index scans and sequential scans", "when an index reads 17 pages, and when it shouldn't be used")

        sqs = VGroup(*[Square(SQ, stroke_color=GREY_D, stroke_width=1.5).set_fill(BLACK, 1).move_to(sq_pos(k)) for k in range(NC * NR)])
        htitle = T("payments table: 23,818 pages of 8 KB", 22, GREY_A).move_to([HX, 2.15, 0])
        hsub = T("one square: about 120 pages", 17, GREY_C).move_to([HX, -1.95, 0])
        q = query("WHERE card_id = 4242")
        self.steps("The support screen asks for one card's payments. The payments table has a million rows in 23,818 pages "
                   "of 8 kilobytes. Card 4242 has 14 payments. Which pages are they on?", [
            (lambda: [FadeIn(q)], 0.6),
            "The payments table",
            (lambda: [FadeIn(htitle), LaggedStart(*[FadeIn(s) for s in sqs], lag_ratio=0.004), FadeIn(hsub)], 1.6),
            "Which pages",
            (lambda: [*[glow(sqs[k], GOLD_M, 1.3) for k in CARD]], 1.0),
        ])

        tr = ValueTracker(0)
        cc = {"c": WHITE}
        cnt = counter(tr, cc)
        ln_t = T("about a quarter of a second", 20, RED_M).move_to([HX, -3.1, 0])
        self.steps("With no index, there's only one way to find out: read every page and test every row.", [
            (lambda: [FadeIn(cnt)], 0.4),
            "read every page",
            (lambda: [LaggedStart(*[sqs[k].animate.set_fill(GOLD_M if k in CARD else interpolate_color(BLACK, ManimColor(BLUE_M), 0.45), 1)
                                    for k in range(NC * NR)], lag_ratio=0.012),
                      tr.animate(rate_func=linear).set_value(23818)], 3.2),
        ])

        self.steps("That's 23,818 pages for 14 rows, about a quarter of a second, and it gets slower as the table grows.", [
            (lambda: [cc.update(c=RED_M), Wait()][1:], 0.4),
            "about a quarter",
            (lambda: [FadeIn(ln_t)], 0.6),
        ])
        root = node(ROOT, 1.4, 0.55, "root", GREY_B, 19)
        inner = [node(p, 0.95, 0.5) for p in INNER]
        leaves = [node(p, 0.62, 0.45) for p in LEAF]
        edges = VGroup(*[edge(root[0].get_bottom(), i[0].get_top()) for i in inner],
                       *[edge(inner[a][0].get_bottom(), leaves[b][0].get_top()) for a, ks in KIDS.items() for b in ks])
        ttitle = T("index on card_id: a B+tree", 21, TEAL_M).move_to([-4.1, 2.35, 0])
        tsub = T("3 levels, 1,130 leaves", 18, GREY_C).move_to([-4.2, -1.7, 0])
        self.steps("An index fixes this. It's a B+tree: a sorted copy of card_id, where every entry points to the page "
                   "that holds its row.", [
            (lambda: [cc.update(c=WHITE), tr.animate.set_value(0), FadeOut(ln_t), *[s.animate.set_fill(BLACK, 1) for s in sqs]][1:], 0.6),
            (lambda: [FadeIn(ttitle), FadeIn(root), *[FadeIn(i) for i in inner], *[FadeIn(lf) for lf in leaves], Create(edges)], 1.2),
            "where every entry",
            (lambda: [FadeIn(tsub)], 0.6),
        ])

        path = [root, inner[1], leaves[2]]
        e1 = edge(root[0].get_bottom(), inner[1][0].get_top(), TEAL_M).set_stroke(width=4)
        e2 = edge(inner[1][0].get_bottom(), leaves[2][0].get_top(), TEAL_M).set_stroke(width=4)
        self.steps("The search starts at the root and goes down: the root, one inner page, then the leaf that holds 4242.", [
            (lambda: [root[0].animate.set_stroke(TEAL_M, width=4).set_fill(fill(TEAL_M), 1), tr.animate.set_value(1)], 0.6),
            "one inner page",
            (lambda: [Create(e1), inner[1][0].animate.set_stroke(TEAL_M, width=4).set_fill(fill(TEAL_M), 1), tr.animate.set_value(2)], 0.7),
            "then the leaf",
            (lambda: [Create(e2), leaves[2][0].animate.set_stroke(TEAL_M, width=4).set_fill(fill(TEAL_M), 1), tr.animate.set_value(3)], 0.7),
        ])

        call = chip("4242: 14 row addresses", TEAL_M, 17, mono=True).move_to([-4.2, -1.7, 0])
        sp = T("about a quarter of a millisecond", 20, GREEN_M).move_to([HX, -3.1, 0])
        start = leaves[2][0].get_right()
        self.steps("The leaf lists 14 row addresses, so PostgreSQL reads just those 14 table pages: "
                   "17 pages in all, about a quarter of a millisecond.", [
            (lambda: [FadeOut(tsub), FadeIn(call)], 0.6),
            "so PostgreSQL reads",
            (lambda: [LaggedStart(*[via([start, sq_pos(k)], GOLD_M, 0.6) for k in CARD], lag_ratio=0.12),
                      LaggedStart(*[sqs[k].animate.set_fill(GOLD_M, 1) for k in CARD], lag_ratio=0.12),
                      tr.animate(rate_func=linear).set_value(17)], 2.2),
            "17 pages",
            (lambda: [cc.update(c=GREEN_M), Wait()][1:], 0.4),
            "about a quarter",
            (lambda: [FadeIn(sp)], 0.6),
        ])

        q2 = query("SELECT sum(amount_minor) ... WHERE card_id = 4242")
        call2 = chip("4242: 14 amounts, too", TEAL_M, 17, mono=True).move_to([-4.2, -1.7, 0])
        inc = M("INCLUDE (amount_minor)", 17, TEAL_M).move_to([-4.2, -2.35, 0])
        self.steps("Now ask for the card's total. If the index also stores the amount, with INCLUDE, "
                   "the leaf already has everything the query needs.", [
            (lambda: [FadeOut(sp), Transform(q, fit(q2.copy(), 6.2).move_to([-3.4, 3.05, 0]))], 0.7),
            "If the index",
            (lambda: [FadeIn(inc, shift=0.1 * UP)], 0.6),
            "the leaf already",
            (lambda: [Transform(call, call2), glow(leaves[2][0], TEAL_M, 1.2)], 0.8),
        ])

        vm = T("if VACUUM has marked those pages all visible", 18, GREY_B).move_to([HX, -3.1, 0])
        self.steps("That's an index only scan. It reads three index pages and never touches the table, "
                   "as long as VACUUM has marked those table pages all visible.", [
            (lambda: [cc.update(c=TEAL_M), *[sqs[k].animate.set_fill(BLACK, 1).set_stroke(GREY_D) for k in CARD]][1:], 0.6),
            (lambda: [tr.animate.set_value(3)], 0.8),
            (lambda: [glow(root[0], TEAL_M), glow(inner[1][0], TEAL_M), glow(leaves[2][0], TEAL_M, 1.2)], 0.8),
            "as long as",
            (lambda: [FadeIn(vm)], 0.6),
        ])

        q3 = query("WHERE status = 'succeeded'")
        ttitle2 = T("index on status", 21, TEAL_M).move_to([-4.1, 2.35, 0])
        pct = T("93% of rows: on almost every page", 20, GOLD_M).move_to([HX, -3.1, 0])
        self.steps("So why not use an index for every query? Take the succeeded payments. "
                   "They're 93 percent of all payments, and they sit on almost every page.", [
            (lambda: [cc.update(c=WHITE), tr.animate.set_value(0), FadeOut(vm), FadeOut(inc), FadeOut(call), Transform(q, q3), Transform(ttitle, ttitle2),
                      FadeOut(e1), FadeOut(e2), *[x[0].animate.set_stroke(GREY_B, width=2.5).set_fill(fill(GREY_B, 0.1), 1)
                                                  for x in path]][1:], 0.8),
            "They're 93 percent",
            (lambda: [LaggedStart(*[sqs[k].animate.set_fill(interpolate_color(BLACK, ManimColor(GOLD_M), 0.55), 1)
                                    for k in range(NC * NR) if k not in RARE], lag_ratio=0.004), FadeIn(pct)], 1.4),
        ])

        jumps = [int(k) for k in rng.choice([k for k in range(NC * NR) if k not in RARE], 46)]
        jl = T("930,000 jumps, pages read again and again", 20, RED_M).move_to([HX, -3.1, 0])
        self.steps("Through the index, that's 930,000 jumps from an index entry to its table page, "
                   "in no useful order, landing on the same pages again and again.", [
            (lambda: [cc.update(c=RED_M), FadeOut(pct), FadeIn(jl)][1:], 0.5),
            (lambda: [LaggedStart(*[via([LEAF[k % 6] + [0.31, 0, 0], sq_pos(j)], RED_M, 0.45) for k, j in enumerate(jumps)],
                                  lag_ratio=0.12), tr.animate(rate_func=linear).set_value(930000)], 3.4),
        ])

        once = T("each page once, in order", 20, GREEN_M).move_to([HX, -3.1, 0])
        seq = chip("plan: Seq Scan", GREEN_M, 19, mono=True).move_to([-4.2, -2.35, 0])
        self.steps("Reading the table straight through touches each page once, in order. "
                   "So the planner picks the sequential scan, even with an index on status.", [
            (lambda: [cc.update(c=WHITE), FadeOut(jl), tr.animate.set_value(0)][1:], 0.4),
            (lambda: [LaggedStart(*[s.animate.set_fill(interpolate_color(BLACK, ManimColor(BLUE_M), 0.45), 1) for s in sqs], lag_ratio=0.01),
                      tr.animate(rate_func=linear).set_value(23818)], 2.6),
            (lambda: [FadeIn(once)], 0.5),
            "So the planner",
            (lambda: [FadeIn(seq, shift=0.1 * UP)], 0.6),
        ])

        self.steps("An index wins when the query needs a short run of entries. When it needs most of the table, "
                   "read the table.", [
            (lambda: [glow(leaves[2][0], TEAL_M, 1.2), glow(root[0], TEAL_M)], 0.9),
            "When it needs",
            (lambda: [glow(seq[0], GREEN_M, 1.05)], 0.9),
        ])
        self.wait(0.6)
