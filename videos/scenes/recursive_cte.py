from sfz import *

SAY.insert(0, (r"\breferred_by\b", "referred by"))
SAY.insert(0, (r"\bUNION ALL\b", "union all"))
SAY.insert(0, (r"\bWITH\b", "with"))
SAY.insert(0, (r"\bRECURSIVE\b", "recursive"))
SAY.insert(0, (r"\bNULL\b", "null"))
SAY.insert(0, (r"\bCTE\b", "C T E"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
DEPTH_Y = [2.25, 1.0, -0.25, -1.5]
COLS = [-6.05, -4.88, -3.71, -2.54, -1.37, -0.2]
POS = {1: ((COLS[0] + COLS[1]) / 2, 0), 3: (COLS[0], 1), 5: (COLS[1], 1), 6: (COLS[0], 2), 10: (COLS[1], 2),
       2: (COLS[2], 0), 4: (COLS[2], 1), 8: (COLS[2], 2), 13: (COLS[2], 3), 7: (COLS[3], 0), 12: (COLS[3], 1), 9: (COLS[4], 0),
       11: (COLS[5], 0)}
PARENT = {3: 1, 5: 1, 6: 3, 10: 5, 4: 2, 8: 4, 13: 8, 12: 7}
NAMES = {1: "Asha", 2: "Ben", 3: "Chloe", 4: "Daniel", 5: "Elena", 6: "Farid", 7: "Grace", 8: "Hugo", 9: "Ivy", 10: "Jonas",
         11: "Kofi", 12: "Lena", 13: "Mateo"}
ASHA = [1, 3, 5, 6, 10]
BX0, BX1 = 1.45, 6.55                              # the boxes on the right
BCX = (BX0 + BX1) / 2
WT_T, WT_B = 2.6, 1.5                              # working table
RS_T, RS_B = 1.25, -1.95                           # result
RROW_Y = [0.6, 0.18, -0.24, -0.66, -1.08]
CAP_Y, BAR_Y, QY = -2.45, -2.8, -3.2
CODE = ["WITH RECURSIVE downline AS (", "    SELECT customer_id, full_name, 0 AS depth", "    FROM customers",
        "    WHERE customer_id = 1", "  UNION ALL", "    SELECT c.customer_id, c.full_name, d.depth + 1", "    FROM customers c",
        "    JOIN downline d ON c.referred_by = d.customer_id", ")", "SELECT * FROM downline;"]
CODE_Y0, CODE_DY = 2.4, 0.46


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

    def steps(self, text, items, after=0.2):
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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def framed(x0, x1, top, bot, color, a=0.08, sw=2.5):
    return RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=sw).set_fill(
        fillc(color, a), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


# ---- the pieces ----
def xy(c):
    x, d = POS[c]
    return np.array([x, DEPTH_Y[d], 0])


def node(c):
    b = RoundedRectangle(corner_radius=0.1, width=1.04, height=0.44, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1).move_to(xy(c))
    lab = VGroup(T(str(c), 15, GREY_B), T(NAMES[c], 17)).arrange(RIGHT, buff=0.08, aligned_edge=DOWN).move_to(xy(c))
    return VGroup(b, lab)


def edge(c):
    p = xy(PARENT[c])
    return Line(p + 0.24 * DOWN, xy(c) + 0.24 * UP, stroke_width=2, color=GREY_C)


def paint(n, color, a=0.3):
    if color is None:
        return [n[0].animate.set_stroke(GREY_B, 2.5).set_fill(BLACK, 1)]
    return [n[0].animate.set_stroke(color, 3).set_fill(fillc(color, a), 1)]


class RecursiveCte(Base):
    """model-07, section 1. A café app's invitations: thank Asha for her whole chain. A level query is right today and
    quietly misses tomorrow's newcomer. Phone calls by rounds: call only the people named in the last round, stop when a
    round names nobody. WITH RECURSIVE downline: anchor (Asha, depth 0), UNION ALL, recursive term (one step down), run
    with a working table: {1}, {3, 5}, {6, 10}, empty; the Try-it's five rows. Despite the name, a while loop. The forest
    from its five roots: {1, 2, 7, 9, 11}, {3, 4, 5, 12}, {6, 8, 10}, {13}, empty: 13 rows, four runs of the recursive
    term; 50,000 customers in 8 rounds and about 40 ms. It can't count inside the loop, and it has no built-in limit
    (SQL Server stops at 100). The moral, and a check (the walk from Ben)."""

    def cap(self, s, color=GREY_B, size=22, mono=False):
        new = fit((M(s, 17, color) if mono else T(s, size, color)), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def strip(self, q, v="", vcolor=GREEN_M):
        out = []
        nq = left_at(T(q, 21), -6.25, QY) if q else None
        nv = right_at(T(v, 21, vcolor), 6.25, QY) if v else None
        for old, new in ((self.qm, nq), (self.vm, nv)):
            if old is not None and new is not None:
                out.append(swap(old, new))
            elif old is not None:
                out.append(FadeOut(old))
            elif new is not None:
                out.append(FadeIn(new, shift=0.1 * UP))
        self.qm, self.vm = nq, nv
        return out

    def found(self, v, vcolor=GREEN_M):
        nv = right_at(T(v, 21, vcolor), 6.25, QY)
        old, self.vm = self.vm, nv
        return [swap(old, nv)]

    def wt(self, s, color=YELLOW_M, mono=True):
        new = (M(s, 24, color) if mono else T(s, 24, color)).move_to([BCX, 1.85, 0])
        fit(new, BX1 - BX0 - 0.4)
        old, self.wtm = self.wtm, new
        return [swap(old, new)]

    def wt_title(self, s):
        new = left_at(T(s, 19, YELLOW_M), BX0 + 0.25, 2.33)
        old, self.wtt = self.wtt, new
        return [swap(old, new)]

    def add_row(self, k, s, color=GREEN_M):
        r = left_at(M(s, 17, color), BX0 + 0.3, RROW_Y[k])
        self.rrows.append(r)
        return [FadeIn(r, shift=0.1 * LEFT)]

    def clear_rows(self):
        out = [FadeOut(r) for r in self.rrows]
        self.rrows = []
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar, rate_func=linear), run_time=secs)

    def construct(self):
        self.capm = self.qm = self.vm = self.wtm = self.wtt = None
        self.rrows = []
        self.title_card("Round after round of phone calls", "a recursive query is a loop")

        nodes = {c: node(c) for c in POS}
        edges = {c: edge(c) for c in PARENT}
        others = [c for c in POS if c not in ASHA]
        qbox = RoundedRectangle(corner_radius=0.1, width=13.0, height=0.56, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([0, QY, 0])

        # ---------------- scene 1: Asha's thank-you ----------------
        self.steps("Picture a café app that gives you a free coffee for inviting a friend. Asha invited Chloe and Elena, "
                   "and each of them invited a friend.", [
            "Asha invited",
            (lambda: [FadeIn(nodes[1], shift=0.1 * DOWN)], 0.5),
            "Chloe and Elena",
            (lambda: [Create(edges[3]), Create(edges[5]), FadeIn(nodes[3]), FadeIn(nodes[5])], 0.8),
            "each of them",
            (lambda: [Create(edges[6]), Create(edges[10]), FadeIn(nodes[6]), FadeIn(nodes[10])], 0.8),
        ])
        self.steps("Now the company wants to thank Asha for her whole chain: everyone who joined through her, at any distance.", [
            (lambda: [FadeIn(qbox), *self.strip("thank Asha: everyone below her, at any distance")], 0.7),
            "everyone who joined",
            (lambda: [LaggedStart(*[AnimationGroup(*paint(nodes[c], GOLD_M)) for c in ASHA], lag_ratio=0.2)], 1.2),
        ])
        band = Rectangle(width=2.6, height=3.35, stroke_color=YELLOW_M, stroke_width=1.5).set_fill(YELLOW_M, 0.06)
        band.move_to([(COLS[0] + COLS[1]) / 2, 0.97, 0])
        band = DashedVMobject(band, num_dashes=60).set_stroke(YELLOW_M, 1.5)
        bandfill = Rectangle(width=2.6, height=3.35, stroke_width=0).set_fill(YELLOW_M, 0.07).move_to([(COLS[0] + COLS[1]) / 2, 0.97, 0])
        self.steps("The first query people write counts by levels: her friends, then her friends' friends, one more step for each level. "
                   "It's right today.", [
            "her friends,",
            (lambda: [*[a for c in (3, 5) for a in paint(nodes[c], GREEN_M)]], 0.6),
            "her friends' friends",
            (lambda: [*[a for c in (6, 10) for a in paint(nodes[c], GREEN_M)]], 0.6),
            "It's right today",
            (lambda: [FadeIn(bandfill), Create(band), *self.cap("the level query looks here: two levels", YELLOW_M)], 0.8),
        ])
        newf = VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.1, width=1.04, height=0.44).set_stroke(RED_M, 2), num_dashes=24),
                      T("?", 20, RED_M)).move_to([COLS[0], DEPTH_Y[3], 0])
        newe = DashedLine(xy(6) + 0.24 * DOWN, newf.get_top(), dash_length=0.06, stroke_width=2, color=RED_M)
        miss = tick(False, 0.13).next_to(newf, RIGHT, buff=0.15)
        self.steps("Then someone at the bottom invites a friend, and the answer quietly leaves them out. No error. Just one person short.", [
            "invites a friend",
            (lambda: [Create(newe), FadeIn(newf, shift=0.1 * DOWN)], 0.7),
            "quietly leaves them out",
            (lambda: [Create(miss), *self.cap("a new friend, below the levels: left out", RED_M)], 0.6),
            "No error",
            (lambda: [*self.found("no error, one person short", RED_M)], 0.6),
        ])

        # ---------------- scene 2: one step per level ----------------
        tb = VGroup(M("customer_id  full_name     referred_by", 17, GREY_B), M("1            Asha Rao      NULL", 17),
                    M("3            Chloe Martin  1", 17), M("6            Farid Haddad  3", 17)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        fit(tb, BX1 - BX0 - 0.3)
        left_at(tb, BX0 + 0.1, 1.0)
        self.steps("Here's the data. The app's database is PostgreSQL, a free database program. Its customers table has 13 rows, "
                   "and a column, referred_by, that holds the id of whoever invited each customer, or NULL when nobody did.", [
            (lambda: [*self.uncap(), *self.strip("customers: 13 rows"), FadeOut(VGroup(band, bandfill, newf, newe, miss))], 0.6),
            "Its customers table",
            (lambda: [FadeIn(tb[0]), FadeIn(tb[1:], shift=0.1 * UP)], 0.8),
            "referred_by",
            (lambda: [Indicate(tb[2], color=GREEN_M, scale_factor=1.04), Indicate(tb[3], color=GREEN_M, scale_factor=1.04)], 0.9),
            "or NULL",
            (lambda: [Indicate(tb[1], color=GOLD_M, scale_factor=1.04)], 0.8),
        ])
        self.steps("Draw those pointers and you get trees: a forest of five, with Asha at the top of one.", [
            "Draw those pointers",
            (lambda: [*[a for c in ASHA for a in paint(nodes[c], None)]], 0.4),
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(nodes[c]), *([Create(edges[c])] if c in PARENT else [])) for c in others],
                                  lag_ratio=0.12)], 1.6),
            "a forest of five",
            (lambda: [LaggedStart(*[AnimationGroup(*paint(nodes[c], GOLD_M)) for c in (1, 2, 7, 9, 11)], lag_ratio=0.2),
                      *self.cap("five roots: nobody invited them", GOLD_M)], 1.0),
        ])
        self.steps("Asha's chain is two levels deep today, so the level query asks two levels. "
                   "The day Farid invites a friend, there's a third level, and the query never looks there.", [
            (lambda: [*[a for c in (2, 7, 9, 11) for a in paint(nodes[c], None)], *[n.animate.set_opacity(0.3) for c, n in nodes.items() if c not in ASHA],
                      *[e.animate.set_opacity(0.3) for c, e in edges.items() if c not in ASHA], *self.uncap()], 0.7),
            "so the level query",
            (lambda: [FadeIn(bandfill), Create(band)], 0.7),
            "The day Farid",
            (lambda: [Create(newe), FadeIn(newf, shift=0.1 * DOWN)], 0.6),
            "never looks there",
            (lambda: [Create(miss), *self.cap("one step per level: the depth must be known before it runs", RED_M)], 0.6),
        ])

        # ---------------- scene 3: phone calls ----------------
        wbox = framed(BX0, BX1, WT_T, WT_B, YELLOW_M, 0.06)
        self.steps("How would you do it by hand? With a phone. Call Asha: whom did you invite? Chloe and Elena.", [
            (lambda: [*self.uncap(), FadeOut(tb), FadeOut(VGroup(band, bandfill, newf, newe, miss)), *paint(nodes[1], None)], 0.6),
            "With a phone",
            (lambda: [FadeIn(wbox), *self.wt_title("to call this round")], 0.6),
            "Call Asha",
            (lambda: [*self.wt("Asha", YELLOW_M, mono=False), *paint(nodes[1], YELLOW_M), *self.strip("call Asha: whom did you invite?")], 0.7),
            "Chloe and Elena",
            (lambda: [*paint(nodes[3], GREEN_M), *paint(nodes[5], GREEN_M), *self.found("Chloe, Elena")], 0.6),
        ])
        self.steps("Then call each person she named. Chloe says Farid, Elena says Jonas. Call those two: nobody. "
                   "A round that names nobody new means you're done.", [
            (lambda: [*self.wt("Chloe, Elena", YELLOW_M, mono=False), *paint(nodes[1], None), *paint(nodes[3], YELLOW_M), *paint(nodes[5], YELLOW_M),
                      *self.strip("call Chloe and Elena")], 0.7),
            "Chloe says",
            (lambda: [*paint(nodes[6], GREEN_M), *paint(nodes[10], GREEN_M), *self.found("Farid, Jonas")], 0.6),
            "Call those two",
            (lambda: [*self.wt("Farid, Jonas", YELLOW_M, mono=False), *paint(nodes[3], None), *paint(nodes[5], None), *paint(nodes[6], YELLOW_M),
                      *paint(nodes[10], YELLOW_M), *self.strip("call Farid and Jonas")], 0.7),
            "nobody",
            (lambda: [*self.found("nobody", GREY_B)], 0.5),
            "A round that names",
            (lambda: [*self.wt("nobody: stop", GREY_B, mono=False), *paint(nodes[6], None), *paint(nodes[10], None)], 0.6),
        ])
        self.steps("Notice the rule. In each round, you only call the people you heard about in the round before. "
                   "You never needed to know how deep the chain was.", [
            "In each round",
            (lambda: self.cap("each round: call only the people named in the round before", WHITE), 0.6),
            "You never needed",
            (lambda: self.cap("no depth written anywhere", GREEN_M), 0.6),
        ])

        # ---------------- scene 4: the loop, written as one query ----------------
        tree = VGroup(*nodes.values(), *edges.values())
        code = VGroup(*[left_at(M(s.lstrip(" "), 17), -6.45 + (len(s) - len(s.lstrip(" "))) * 0.133, CODE_Y0 - i * CODE_DY) for i, s in enumerate(CODE)])
        fa = SurroundingRectangle(VGroup(code[1], code[3]), buff=0.08, color=GOLD_M, stroke_width=2.5, corner_radius=0.08)
        fr = SurroundingRectangle(VGroup(code[5], code[7]), buff=0.08, color=TEAL_M, stroke_width=2.5, corner_radius=0.08)
        self.steps("SQL can run that loop inside one query. WITH gives a query a name, here downline, and RECURSIVE lets that query read itself.", [
            (lambda: [*self.uncap(), *self.strip("", ""), FadeOut(tree), FadeOut(self.wtm)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.05 * RIGHT) for l in code], lag_ratio=0.08)], 1.3),
            "WITH gives",
            (lambda: [Indicate(code[0], color=YELLOW_M, scale_factor=1.03)], 0.8),
            "RECURSIVE lets",
            (lambda: [Indicate(code[7], color=YELLOW_M, scale_factor=1.02)], 0.8),
        ])
        self.wtm = None
        self.steps("The whole thing is called a recursive common table expression, or CTE.", [
            (lambda: self.cap("CTE: a named query; RECURSIVE: it may read itself", WHITE), 0.6),
        ])
        self.steps("The first part, the anchor, is where the loop starts: Asha, at depth 0.", [
            "the anchor",
            (lambda: [Create(fa), *self.cap("the anchor: where the loop starts", GOLD_M)], 0.7),
        ])
        self.steps("The second part, the recursive term, takes one step down: customers whose inviter is already in downline. "
                   "UNION ALL stacks the two parts into one result.", [
            "the recursive term",
            (lambda: [Create(fr), *self.cap("the recursive term: one step down", TEAL_M)], 0.7),
            "UNION ALL",
            (lambda: [Indicate(code[4], color=YELLOW_M, scale_factor=1.06), *self.cap("UNION ALL: stack both parts into one result", WHITE)], 0.8),
        ])
        rbox = framed(BX0, BX1, RS_T, RS_B, GREEN_M, 0.06)
        rtitle = VGroup(left_at(T("result", 19, GREEN_M), BX0 + 0.25, 0.98), right_at(T("customer_id, full_name, depth", 15, GREY_B), BX1 - 0.25, 0.98))
        self.steps("PostgreSQL runs it with a working table: the people you heard about in the last round of calls. Run the anchor once.", [
            (lambda: [*self.uncap(), *self.wt_title("working table: the last round's rows"), FadeIn(rbox), FadeIn(rtitle)], 0.7),
            "Run the anchor",
            (lambda: [glow(fa, GOLD_M, 1.02), *self.wt("{1}"), *self.add_row(0, "1   Asha Rao        0"), *self.strip("anchor", "{1}")], 0.9),
        ])
        self.steps("Then run the recursive term, reading only the working table. Its new rows join the result and become the next working table. "
                   "Repeat until a round comes back empty.", [
            "Then run",
            (lambda: [glow(fr, TEAL_M, 1.02), *self.strip("round 1: who did {1} invite?", "{3, 5}")], 0.7),
            "Its new rows",
            (lambda: [*self.add_row(1, "3   Chloe Martin    1"), *self.add_row(2, "5   Elena Petrova   1"), *self.wt("{3, 5}")], 0.8),
            "Repeat",
            (lambda: [glow(fr, TEAL_M, 1.02), *self.strip("round 2: who did {3, 5} invite?", "{6, 10}")], 0.6),
            (lambda: [*self.add_row(3, "6   Farid Haddad    2"), *self.add_row(4, "10  Jonas Weber     2"), *self.wt("{6, 10}")], 0.7),
            "comes back empty",
            (lambda: [glow(fr, TEAL_M, 1.02), *self.strip("round 3: who did {6, 10} invite?", "nobody", GREY_B), *self.wt("empty: stop", GREY_B)], 0.8),
        ])
        self.steps("So despite the name, nothing calls itself. The PostgreSQL docs call it iteration. "
                   "Recursive is the name on the box; inside, it's a while loop.", [
            "nothing calls itself",
            (lambda: self.cap("nothing calls itself: the docs call it iteration", WHITE), 0.6),
            "Recursive is the name",
            (lambda: [*self.cap("recursive on the box; a while loop inside", YELLOW_M, 26), Indicate(code[0], color=YELLOW_M, scale_factor=1.03)], 0.8),
        ])

        # ---------------- scene 5: the whole forest ----------------
        for c, n in nodes.items():
            n.set_opacity(1)
            n[0].set_stroke(GREY_B, 2.5).set_fill(BLACK, 1)
        for e in edges.values():
            e.set_opacity(1)
        roots = [1, 2, 7, 9, 11]
        rounds = [[3, 4, 5, 12], [6, 8, 10], [13]]
        self.steps("Now start from all five roots at once: everyone nobody invited. "
                   "How many times does the recursive term run before the loop stops? Pause and guess.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(code, fa, fr)), *self.clear_rows(), *self.strip("anchor: WHERE referred_by IS NULL", "")], 0.7),
            (lambda: [FadeIn(tree)], 0.8),
            "all five roots",
            (lambda: [*[a for c in roots for a in paint(nodes[c], YELLOW_M)], *self.wt("{1, 2, 7, 9, 11}"),
                      *self.add_row(0, "depth 0:  1 2 7 9 11"), *self.found("5 roots")], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        def step_round(k, sets, label):
            prev = roots if k == 0 else rounds[k - 1]
            new = rounds[k]
            return [*[a for c in prev for a in paint(nodes[c], GREEN_M)], *[a for c in new for a in paint(nodes[c], YELLOW_M)],
                    *self.wt(sets), *self.add_row(k + 1, label), *self.strip(f"round {k + 1}", ", ".join(map(str, new)))]

        self.steps("Round one finds 3, 4, 5 and 12. Round two finds 6, 8 and 10. Round three finds only Mateo. "
                   "Round four finds nobody, and the loop ends with all 13 customers.", [
            (lambda: self.uncap(), 0.2),
            (lambda: step_round(0, "{3, 4, 5, 12}", "depth 1:  3 4 5 12"), 0.8),
            "Round two",
            (lambda: step_round(1, "{6, 8, 10}", "depth 2:  6 8 10"), 0.8),
            "Round three",
            (lambda: step_round(2, "{13}", "depth 3:  13"), 0.8),
            "Round four",
            (lambda: [*paint(nodes[13], GREEN_M), *self.wt("empty: stop", GREY_B), *self.strip("round 4", "nobody", GREY_B)], 0.7),
            "all 13",
            (lambda: [*self.add_row(4, "13 rows", WHITE)], 0.5),
        ])
        self.steps("Four runs, and the last one finds nothing. Nobody wrote a stop condition. The data running out is the stop.", [
            (lambda: self.cap("the recursive term ran 4 times; the 4th found nobody", WHITE), 0.6),
            "Nobody wrote",
            (lambda: [*self.cap("the stop: the data running out", GREEN_M, 26), glow(wbox, YELLOW_M, 1.02)], 0.7),
        ])
        self.steps("On a copy with 50,000 customers, the whole forest takes 8 rounds and about 40 milliseconds.", [
            (lambda: self.cap("50,000 customers: 8 rounds, about 40 ms", WHITE), 0.6),
        ])

        # ---------------- scene 6: two things the loop can't do ----------------
        self.steps("Two things follow from the working table. First, each round sees only the last round's rows, never the whole result. "
                   "So it can't count.", [
            (lambda: [*self.uncap(), *self.strip("", ""), *[a for c in POS for a in paint(nodes[c], None)]], 0.6),
            "each round sees only",
            (lambda: [glow(wbox, YELLOW_M, 1.02)], 0.8),
            "never the whole result",
            (lambda: [glow(rbox, GREY_B, 1.01)], 0.8),
        ])
        self.steps("Put count in the recursive term and PostgreSQL refuses. Count in the main query, after the loop.", [
            "PostgreSQL refuses",
            (lambda: self.cap("ERROR: aggregate functions are not allowed in a recursive query's recursive term", RED_M, mono=True), 0.7),
            "Count in the main",
            (lambda: self.cap("count in the main query, after the loop", GREEN_M), 0.6),
        ])
        self.steps("Second, there's no built-in limit. The loop stops when a round comes back empty, and only then.", [
            "no built-in limit",
            (lambda: self.cap("no built-in limit: it stops only when a round is empty", WHITE), 0.6),
        ])
        self.steps("SQL Server, Microsoft's database program, stops after 100 levels by default. PostgreSQL doesn't.", [
            (lambda: self.cap("SQL Server, Microsoft's database program: stops after 100 levels by default", GREY_B), 0.6),
            "PostgreSQL doesn't",
            (lambda: self.cap("PostgreSQL: no limit", WHITE), 0.5),
        ])
        cyc = ["{2}", "{4}", "{8}", "{13}", "{2}", "{4}"]
        self.steps("If the data ever loops back on itself, you'll be making calls until the battery dies. A later section adds the guard.", [
            "loops back",
            (lambda: [*self.cap("if the data loops back (say Mateo had invited Ben)", RED_M)], 0.5),
            *[((lambda s=s, k=k: [*self.wt(s, RED_M), *self.strip(f"round {k + 5}", "someone, again", RED_M)]), 0.45) for k, s in enumerate(cyc)],
            "A later section",
            (lambda: [*self.wt("…", RED_M), *self.cap("a later section adds the guard", WHITE)], 0.5),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, Asha's thank-you. The loop has no depth written in it: start somewhere, take one step from the rows you found last, "
                   "and stop when a step finds nothing.", [
            (lambda: self.strip("thank Asha: everyone below her, at any distance"), 0.5),
            "start somewhere",
            (lambda: [*self.cap("start somewhere", GOLD_M, 26), *paint(nodes[1], GOLD_M)], 0.6),
            "take one step",
            (lambda: [*self.cap("take one step from the rows you found last", TEAL_M, 26), *[a for c in (3, 5) for a in paint(nodes[c], TEAL_M)]], 0.6),
            "and stop when",
            (lambda: [*self.cap("stop when a step finds nothing", GREEN_M, 26), *self.wt("empty: stop", GREY_B)], 0.6),
        ], after=0.5)
        ben = [2, 4, 8, 13]
        self.steps("One quick check. Start the walk from Ben instead. How many rows come back, and how many rounds find someone? Pause and think.", [
            (lambda: [*self.uncap(), *[a for c in (1, 3, 5) for a in paint(nodes[c], None)], *self.clear_rows(),
                      *[n.animate.set_opacity(0.3) for c, n in nodes.items() if c not in ben], *[e.animate.set_opacity(0.3) for c, e in edges.items() if c not in ben]], 0.7),
            "Start the walk from Ben",
            (lambda: [*paint(nodes[2], YELLOW_M), *self.wt("{2}"), *self.strip("anchor: Ben", "{2}")], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        rows_b = ["2   Ben Carter      0", "4   Daniel Kim      1", "8   Hugo Silva      2", "13  Mateo Ruiz      3"]
        self.steps("Four rows: Ben, Daniel, Hugo and Mateo. Three rounds find someone, and a fourth finds nobody.", [
            (lambda: [*self.uncap(), *self.add_row(0, rows_b[0])], 0.3),
            (lambda: [*paint(nodes[2], GREEN_M), *paint(nodes[4], YELLOW_M), *self.wt("{4}"), *self.add_row(1, rows_b[1]), *self.strip("round 1", "4")], 0.55),
            (lambda: [*paint(nodes[4], GREEN_M), *paint(nodes[8], YELLOW_M), *self.wt("{8}"), *self.add_row(2, rows_b[2]), *self.strip("round 2", "8")], 0.55),
            (lambda: [*paint(nodes[8], GREEN_M), *paint(nodes[13], YELLOW_M), *self.wt("{13}"), *self.add_row(3, rows_b[3]), *self.strip("round 3", "13")], 0.55),
            "and a fourth",
            (lambda: [*paint(nodes[13], GREEN_M), *self.wt("empty: stop", GREY_B), *self.strip("round 4", "nobody", GREY_B)], 0.6),
        ], after=0.5)
        self.play(*self.cap("start somewhere, step from the last round, stop when a step finds nothing", YELLOW_M, 24), run_time=0.7)
        self.wait(2.0)
