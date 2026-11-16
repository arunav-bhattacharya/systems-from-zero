from sfz import *

SAY.insert(0, (r"\bWITH RECURSIVE\b", "with recursive"))
SAY.insert(0, (r"\breferred_by\b", "referred by"))
SAY.insert(0, (r"\bCYCLE\b", "cycle"))
# Kokoro says "Asha" as "a chat" and "Elena" as "Alina"
SAY.insert(0, (r"\bAsha\b", "Aasha"))
SAY.insert(0, (r"\bAsha's\b", "Ah sha's"))
SAY.insert(0, (r"\bElena\b", "Elaina"))

CODE_X, CODE_Y = -6.4, [3.2, 2.8, 2.4]
HEAD_Y = 1.95
ROW_Y = [1.45, 0.95, 0.45, -0.05, -0.55, -1.05]
CX_ID, CX_NAME, CX_REF = -6.0, -5.55, -3.1
PEOPLE = [(1, "Asha", None), (3, "Chloe", 1), (5, "Elena", 1), (6, "Farid", 3), (10, "Jonas", 5), (14, "Priya", 10)]
POS = {1: (0.9, 1.75), 3: (-0.3, 0.45), 5: (2.1, 0.45), 6: (-0.3, -0.85), 10: (2.1, -0.85), 14: (2.1, -2.15)}
NW, NH = 1.7, 0.6
PX, PY = 3.55, [1.2, 0.65, 0.1]          # the round panel
ST_Y = -3.1


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def along(path, color=YELLOW_M, run_time=1.0):
    d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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


def code(parts, k):
    """One line of code from (text, colour) segments, left aligned on the code band."""
    g = VGroup()
    x = CODE_X
    for s, c in parts:
        t = left_at(M(s, 17, c), x, CODE_Y[k])
        g.add(t)
        x = t.get_right()[0] + 0.14
    return g


def ref_cell(i, ref, color=WHITE):
    k = [p[0] for p in PEOPLE].index(i)
    return M("NULL" if ref is None else str(ref), 20, GREY_C if ref is None and color == WHITE else color).move_to([CX_REF, ROW_Y[k], 0])


def row(k, color=WHITE):
    i, name, ref = PEOPLE[k]
    return VGroup(M(str(i), 20, color).move_to([CX_ID, ROW_Y[k], 0]), left_at(T(name, 22, color), CX_NAME, ROW_Y[k]),
                  ref_cell(i, ref, color))


def node(i, color=WHITE, dashed=False):
    name = [p[1] for p in PEOPLE if p[0] == i][0]
    x, y = POS[i]
    r = RoundedRectangle(corner_radius=0.12, width=NW, height=NH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    if dashed:
        r = DashedVMobject(r, num_dashes=30).set_fill(fillc(color), 0)
    return VGroup(r, T(f"{name} ({i})", 22).move_to([x, y, 0]))


def edge(a, b, color=GREY_B):
    (xa, ya), (xb, yb) = POS[a], POS[b]
    return Arrow([xa + (xb - xa) * 0.12, ya - NH / 2, 0], [xb, yb + NH / 2, 0], buff=0.06, stroke_width=3, color=color,
                 max_tip_length_to_length_ratio=0.12)


def pline(s, k, color=GREY_B, size=22):
    return left_at(T(s, size, color), PX, PY[k])


def status(s, color=GREY_B):
    return T(s, 24, color).move_to([0, ST_Y, 0])


def hl(k, color=YELLOW_M):
    return RoundedRectangle(corner_radius=0.08, width=4.25, height=0.42, stroke_color=color, stroke_width=2.5).move_to(
        [-4.33, ROW_Y[k], 0])


class RecursiveCte(Base):
    """model-07, section 1 (with section 0's self joins and section 3's cycles): Asha's referral downline stored as
    referred_by pointers. One filter finds level 1, one self join level 2, and a fixed-depth query misses Priya, referred
    later. WITH RECURSIVE: the anchor {1}, then rounds {3, 5}, {6, 10}, {14}, then an empty round stops it. A bad update
    makes Asha referred by Farid: the working table never empties; carrying the path (or CYCLE) stops it."""

    def construct(self):
        self.title_card("Recursive CTEs", "walking a tree in SQL, one level per round")

        heads = VGroup(M("id", 17, GREY_B).move_to([CX_ID, HEAD_Y, 0]), left_at(M("name", 17, GREY_B), CX_NAME, HEAD_Y),
                       M("referred_by", 17, GREY_B).move_to([CX_REF, HEAD_Y, 0]))
        hline = Line([-6.4, HEAD_Y - 0.24, 0], [-2.2, HEAD_Y - 0.24, 0], stroke_width=1.5, color=GREY_D)
        rows = [row(k) for k in range(5)]
        ask = status("Who is in Asha's downline?", WHITE)
        self.steps("Marketing pays a bonus for a referrer's whole downline, every level of it. Who is in Asha's?", [
            (lambda: [FadeIn(heads), Create(hline)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.08 * RIGHT) for r in rows], lag_ratio=0.15)], 1.2),
            "Who is in",
            (lambda: [FadeIn(ask, shift=0.1 * UP)], 0.6),
        ])

        nodes = {i: node(i) for i in (1, 3, 5, 6, 10)}
        edges = {(a, b): edge(a, b) for a, b in [(1, 3), (1, 5), (3, 6), (5, 10)]}
        self.steps("Each row stores one pointer, referred_by, the id of the customer who referred them. "
                   "Follow the pointers and you get a tree.", [
            (lambda: [*[r[2].animate.set_color(GOLD_M) for r in rows[1:]], heads[2].animate.set_color(GOLD_M)], 0.7),
            "Follow the pointers",
            (lambda: [LaggedStart(*[FadeIn(nodes[i], scale=0.9) for i in (1, 3, 5, 6, 10)], lag_ratio=0.15)], 1.0),
            (lambda: [LaggedStart(*[GrowArrow(e) for e in edges.values()], lag_ratio=0.2),
                      *[r[2].animate.set_color(WHITE) for r in rows[1:]], heads[2].animate.set_color(GREY_B)], 0.9),
        ])

        c1 = code([("SELECT * FROM customers WHERE referred_by = 1", WHITE)], 0)
        h3, h5 = hl(1, TEAL_M), hl(2, TEAL_M)
        self.steps("One level down is a plain filter. Referred by 1 gives Chloe and Elena.", [
            (lambda: [FadeOut(ask), FadeIn(c1)], 0.7),
            "Referred by 1",
            (lambda: [Create(h3), Create(h5), *[nodes[i][0].animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1) for i in (3, 5)]], 0.8),
        ])

        c2a = code([("SELECT g.* FROM customers c JOIN customers g ON g.referred_by = c.customer_id", WHITE)], 0)
        c2b = code([("WHERE c.referred_by = 1", WHITE)], 1)
        h6, h10 = hl(3, BLUE_M), hl(4, BLUE_M)
        joins = pline("1 join: level 2", 0, BLUE_M)
        self.steps("The next level needs a self join, customers joined to customers. That finds Farid and Jonas.", [
            (lambda: [FadeOut(c1), FadeIn(c2a), FadeIn(c2b)], 0.8),
            "customers joined",
            (lambda: [edges[(3, 6)].animate.set_color(BLUE_M), edges[(5, 10)].animate.set_color(BLUE_M)], 0.7),
            "That finds",
            (lambda: [Create(h6), Create(h10), FadeIn(joins),
                      *[nodes[i][0].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1) for i in (6, 10)]], 0.8),
        ])

        prow = row(5, GREY_B)
        pnode = node(14, RED_M, dashed=True)
        pedge = edge(10, 14, GREY_B)
        missed = left_at(T("missed, and no error", 22, RED_M), POS[14][0] + NW / 2 + 0.25, POS[14][1])
        joins2 = pline("level 3 needs a 2nd join", 1, GREY_B)
        self.steps("Every further level costs one more join, so the query bakes in today's depth. When Jonas refers Priya, "
                   "the two level query misses her, with no error.", [
            (lambda: [FadeIn(joins2, shift=0.1 * UP)], 0.7),
            "When Jonas",
            (lambda: [FadeIn(prow, shift=0.08 * RIGHT), GrowArrow(pedge), FadeIn(pnode, scale=0.9)], 0.9),
            "misses her",
            (lambda: [FadeIn(missed, shift=0.1 * LEFT)], 0.7),
        ])
        rows.append(prow)
        nodes[14] = pnode
        edges[(10, 14)] = pedge

        prow2, n14 = row(5), node(14)
        k1 = code([("var frontier = listOf(1)", WHITE), ("// start from Asha", GREY_C)], 0)
        k2 = code([("while (frontier.isNotEmpty()) frontier = childrenOf(frontier)", WHITE)], 1)
        self.steps("In Kotlin you'd write a loop: start from Asha, find the children of the last round, and stop when "
                   "a round finds nobody.", [
            (lambda: [FadeOut(VGroup(h3, h5, h6, h10)), FadeOut(joins), FadeOut(joins2), FadeOut(missed),
                      FadeOut(c2a), FadeOut(c2b), FadeIn(k1), FadeIn(k2),
                      *[nodes[i][0].animate.set_stroke(WHITE).set_fill(BLACK, 1) for i in (3, 5, 6, 10)],
                      *[e.animate.set_color(GREY_B) for e in edges.values()],
                      FadeOut(prow), FadeIn(prow2), FadeOut(pnode), FadeIn(n14)], 1.0),
            "find the children",
            (lambda: [k2[0][37:57].animate(rate_func=there_and_back).set_color(GOLD_M)], 0.9),
            "and stop",
            (lambda: [k2[0][0:28].animate(rate_func=there_and_back).set_color(TEAL_M)], 0.9),
        ])

        rows[5], nodes[14] = prow2, n14
        anc = code([("WITH RECURSIVE downline AS (", GREY_B), ("SELECT ... WHERE customer_id = 1", GOLD_M)], 0)
        rec = code([("UNION ALL", GREY_B), ("SELECT ... JOIN downline d ON c.referred_by = d.customer_id", TEAL_M),
                    (")", GREY_B)], 1)
        alab = right_at(T("anchor", 20, GOLD_M), 6.5, CODE_Y[0])
        rlab = right_at(T("recursive term", 20, TEAL_M), 6.5, CODE_Y[1])
        p0 = pline("anchor, once", 0, GOLD_M)
        p1 = pline("working table: {1}", 1, WHITE)
        p2 = pline("result: 1 row", 2, GREY_B)

        def paint(i, color):
            return nodes[i][0].animate.set_stroke(color).set_fill(fillc(color), 1)

        self.steps("WITH RECURSIVE is that loop in SQL. The anchor runs once: Asha goes into the result and into the "
                   "working table.", [
            (lambda: [FadeOut(k1), FadeOut(k2), FadeIn(anc), FadeIn(rec)], 0.9),
            "The anchor",
            (lambda: [FadeIn(alab), FadeIn(p0)], 0.6),
            "Asha goes",
            (lambda: [paint(1, GOLD_M), FadeIn(p2)], 0.6),
            "and into the",
            (lambda: [FadeIn(p1)], 0.6),
        ])

        self.steps("The recursive term joins customers to the working table only. Round one finds Chloe and Elena, "
                   "and they become the new working table.", [
            (lambda: [FadeIn(rlab), rec[1].animate(rate_func=there_and_back).scale(1.04)], 0.8),
            "Round one",
            (lambda: [Transform(p0, pline("round 1", 0, TEAL_M)), flow(edges[(1, 3)], GOLD_M, 0.6),
                      flow(edges[(1, 5)], GOLD_M, 0.6)], 0.7),
            (lambda: [paint(3, GOLD_M), paint(5, GOLD_M), paint(1, GREEN_M)], 0.6),
            "and they become",
            (lambda: [Transform(p1, pline("working table: {3, 5}", 1, WHITE)), Transform(p2, pline("result: 3 rows", 2))], 0.7),
        ])

        self.steps("Round two joins to Chloe and Elena only, and finds Farid and Jonas.", [
            (lambda: [Transform(p0, pline("round 2", 0, TEAL_M)), flow(edges[(3, 6)], GOLD_M, 0.6),
                      flow(edges[(5, 10)], GOLD_M, 0.6)], 0.7),
            "and finds",
            (lambda: [paint(6, GOLD_M), paint(10, GOLD_M), paint(3, GREEN_M), paint(5, GREEN_M),
                      Transform(p1, pline("working table: {6, 10}", 1, WHITE)), Transform(p2, pline("result: 5 rows", 2))], 0.8),
        ])

        stop = status("an empty round: the loop stops, 6 rows", GREEN_M)
        self.steps("Round three finds Priya, with no change to the query. Round four finds nobody, so the working table "
                   "is empty and the loop stops.", [
            (lambda: [Transform(p0, pline("round 3", 0, TEAL_M)), flow(edges[(10, 14)], GOLD_M, 0.6)], 0.7),
            (lambda: [paint(14, GOLD_M), paint(6, GREEN_M), paint(10, GREEN_M),
                      Transform(p1, pline("working table: {14}", 1, WHITE)), Transform(p2, pline("result: 6 rows", 2))], 0.7),
            "Round four",
            (lambda: [Transform(p0, pline("round 4", 0, TEAL_M))], 0.5),
            "so the working",
            (lambda: [paint(14, GREEN_M), Transform(p1, pline("working table: { }", 1, GREEN_M))], 0.6),
            "and the loop stops",
            (lambda: [FadeIn(stop, shift=0.1 * UP)], 0.6),
        ])

        # ---- a cycle ---------------------------------------------------------------------------------------------------
        fx, fy = POS[6]
        ax, ay = POS[1]
        bend = -1.65
        cyc = VGroup(Line([fx - NW / 2 - 0.05, fy, 0], [bend, fy, 0]), Line([bend, fy, 0], [bend, ay, 0]),
                     Arrow([bend, ay, 0], [ax - NW / 2 - 0.02, ay, 0], buff=0, max_tip_length_to_length_ratio=0.12)).set_color(RED_M)
        cyc.set_stroke(width=3)
        cpath = VMobject().set_points_as_corners([[fx - NW / 2 - 0.05, fy, 0], [bend, fy, 0], [bend, ay, 0],
                                                   [ax - NW / 2 - 0.02, ay, 0]])
        self.steps("Now a bad update records Asha as referred by Farid. The pointers form a cycle: one, three, six, and "
                   "back to one.", [
            (lambda: [FadeOut(stop), FadeOut(rlab), FadeOut(alab), *[paint(i, WHITE) for i in nodes],
                      FadeOut(p0), FadeOut(p1), FadeOut(p2)], 0.8),
            "records Asha",
            (lambda: [Transform(rows[0][2], ref_cell(1, 6, RED_M))], 0.6),
            "The pointers",
            (lambda: [Create(cyc)], 1.0),
            "one, three",
            (lambda: [Succession(*[glow(nodes[i][0], RED_M, 1.06) for i in (1, 3, 6)], run_time=1.4),
                      Succession(Wait(1.0), along(cpath, RED_M, 0.7))], 1.8),
        ])

        r_ = ValueTracker(3)
        wt = ["{1, 14}", "{3, 5}", "{6, 10}"]
        q0 = always_redraw(lambda: pline(f"round {int(r_.get_value())}", 0, RED_M))
        q1 = always_redraw(lambda: pline("working table: " + wt[(int(r_.get_value()) - 3) % 3], 1, WHITE))
        q2 = always_redraw(lambda: pline(f"result: {2 * int(r_.get_value()) + 1} rows", 2))
        never = status("the working table never empties", RED_M)
        self.steps("Round three finds Asha again, round four finds Chloe and Elena again, and the working table never "
                   "empties. The query runs until something cancels it.", [
            (lambda: [FadeIn(q0), FadeIn(q1), FadeIn(q2), glow(nodes[1][0], GOLD_M, 1.06), glow(nodes[14][0], GOLD_M, 1.06)], 0.7),
            "round four",
            (lambda: [r_.animate.set_value(4), glow(nodes[3][0], GOLD_M, 1.06), glow(nodes[5][0], GOLD_M, 1.06)], 0.7),
            "never",
            (lambda: [r_.animate(rate_func=linear).set_value(11.9), FadeIn(never, shift=0.1 * UP)], 2.4),
        ])
        for m in (q0, q1, q2):
            m.clear_updaters()

        c3 = code([(") CYCLE customer_id SET is_cycle USING path", PURPLE_M)], 2)
        path = M("path {1,3,6}", 18, PURPLE_M).move_to([fx, fy - NH / 2 - 0.3, 0])
        xmark = tick(False, 0.2).move_to([bend, (fy + ay) / 2, 0])
        cut = status("1 is already on the path: don't step there", PURPLE_M)
        self.steps("So you write the stop condition. Carry the path down each row, and never step onto a node already "
                   "on it. PostgreSQL's CYCLE clause does this for you.", [
            (lambda: [FadeOut(never), FadeOut(q0), FadeOut(q1), FadeOut(q2)], 0.6),
            "Carry the path",
            (lambda: [FadeIn(path, shift=0.1 * DOWN)], 0.7),
            "and never step",
            (lambda: [Create(xmark), cyc.animate.set_opacity(0.4), FadeIn(cut, shift=0.1 * UP)], 0.8),
            "PostgreSQL's",
            (lambda: [FadeOut(rec[2]), FadeIn(c3)], 0.9),
        ])

        self.steps("A recursive query is a loop: start somewhere, step one level from the rows you found last, and stop "
                   "when a step finds nothing.", [
            (lambda: [FadeOut(cut), glow(nodes[1][0], GOLD_M, 1.06)], 0.8),
            "step one level",
            (lambda: [LaggedStart(*[flow(edges[k], GOLD_M, 0.5) for k in [(1, 3), (1, 5), (3, 6), (5, 10), (10, 14)]],
                                  lag_ratio=0.3)], 1.4),
            "and stop",
            (lambda: [glow(nodes[14][0], GREEN_M, 1.06)], 0.9),
        ])
        self.wait(0.6)
