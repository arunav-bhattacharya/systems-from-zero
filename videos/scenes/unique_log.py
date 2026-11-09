from sfz import *

SAY.insert(0, (r"@ana\b", "at Anna"))
SAY.insert(0, (r"@bob\b", "at Bob"))

CX, CY = -5.3, [1.5, -1.5]                      # the two users' clients
SX = -1.35                                      # app servers (the broken design)
DBX = 3.9                                       # the database
ROW_Y = [1.8, 0.6, -0.6, -1.8]                  # log partitions P0..P3
LX0, LX1 = -2.8, 1.6
SLOT_X = [-2.1, -0.7, 0.7]
PRX, PRW = 4.4, 3.2                             # processors
RULE = [-0.6, -3.0, 0]


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


def client(name, y):
    return VGroup(rbox(CX, y, 2.3, 1.0, WHITE), M(name, 20).move_to([CX, y + 0.2, 0]),
                  T("wants @ana", 18, GREY_B).move_to([CX, y - 0.2, 0]))


def c_sub(y, s, color=GREY_B):
    return T(s, 18, color).move_to([CX, y - 0.2, 0])


def server(y):
    return VGroup(rbox(SX, y, 2.9, 1.0, BLUE_M), T("app server", 21).move_to([SX, y + 0.2, 0]),
                  T("waiting", 17, GREY_B).move_to([SX, y - 0.2, 0]))


def s_sub(y, s, color=GREY_B):
    return T(s, 17, color).move_to([SX, y - 0.2, 0])


def processor(k):
    y = ROW_Y[k]
    return VGroup(rbox(PRX, y, PRW, 0.95, TEAL_M), T(f"processor {k}", 20).move_to([PRX, y + 0.2, 0]),
                  T("taken: none", 17, GREY_B).move_to([PRX, y - 0.2, 0]))


def p_sub(k, s, color=GREY_B, y=None):
    return T(s, 17, color).move_to([PRX, (ROW_Y[k] if y is None else y) - 0.2, 0])


def part_row(y, name):
    r = Rectangle(width=LX1 - LX0, height=0.72, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([(LX0 + LX1) / 2, y, 0])
    divs = VGroup(*[Line([x, y - 0.36, 0], [x, y + 0.36, 0], stroke_width=1.5, color=GREY_D) for x in (-1.4, 0.0)])
    return VGroup(r, divs, *([T(name, 20, GREY_B).move_to([-3.25, y, 0])] if name else []))


def claim(rid, handle, color):
    t = M(f"{rid} {handle}", 16)
    r = RoundedRectangle(corner_radius=0.08, width=1.22, height=0.5, stroke_color=color, stroke_width=2.5).set_fill(fill(color, 0.25), 1)
    return VGroup(r, t).set_z_index(2)


def rule(s, color=GREY_B):
    return mbox(s, color, h=0.56, size=17).move_to(RULE)


class UniqueLog(Base):
    """derive-04, section 0: two users (u-17, u-43) claim @ana at once; check-then-insert on two app servers grants it
    twice. One decider per value: a claims log with 4 partitions keyed by hash(handle) ("ana".hashCode() = 96,724,
    mod 4 = 0), processor 0 grants r-1 and refuses r-2. Keyed by user id instead, u-17 lands in partition 2 and u-43 in
    partition 3, and both are granted (937 extra owners in the lesson's simulation)."""

    def construct(self):
        self.title_card("One decider per handle", "a uniqueness rule without a shared database")

        c17, c43 = client("u-17", CY[0]), client("u-43", CY[1])
        self.steps("Two people sign up for a wallet app at the same moment, "
                   "and both ask for the handle @ana.", [
            (lambda: [FadeIn(c17[0]), FadeIn(c17[1]), FadeIn(c43[0]), FadeIn(c43[1])], 0.9),
            "and both ask",
            (lambda: [FadeIn(c17[2]), FadeIn(c43[2])], 0.7),
        ])

        sa, sb = server(CY[0]), server(CY[1])
        ca = [Arrow([CX + 1.25, y, 0], [SX - 1.55, y, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.15) for y in CY]
        db = VGroup(rbox(DBX, 0, 3.8, 2.6, GREY_B), T("database", 22).move_to([DBX, 0.85, 0]),
                    T("table of handles", 17, GREY_B).move_to([DBX, 0.48, 0]))
        none = T("no row for ana", 18, GREY_B).move_to([DBX, -0.15, 0])
        da = [Arrow([SX + 1.55, CY[0], 0], [DBX - 2.0, 0.55, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.1),
              Arrow([SX + 1.55, CY[1], 0], [DBX - 2.0, -0.55, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.1)]
        self.steps("Their requests reach two different app servers. Each one checks for a row with that handle, "
                   "finds none, and inserts one.", [
            (lambda: [FadeIn(sa), FadeIn(sb), GrowArrow(ca[0]), GrowArrow(ca[1]), FadeIn(db), GrowArrow(da[0]), GrowArrow(da[1])], 1.0),
            "Each one checks",
            (lambda: [flow(da[0], BLUE_M, 0.7), flow(da[1], BLUE_M, 0.7), FadeIn(none)], 0.8),
            "finds none",
            (lambda: [Transform(sa[2], s_sub(CY[0], "checked: no row")), Transform(sb[2], s_sub(CY[1], "checked: no row"))], 0.6),
            "and inserts",
            (lambda: [Transform(sa[2], s_sub(CY[0], "inserts ana, u-17", GOLD_M)), Transform(sb[2], s_sub(CY[1], "inserts ana, u-43", GOLD_M)),
                      flow(da[0], GOLD_M, 0.7), flow(da[1], GOLD_M, 0.7)], 0.9),
        ])

        r1 = M("ana   u-17", 18, RED_M).move_to([DBX, -0.15, 0])
        r2 = M("ana   u-43", 18, RED_M).move_to([DBX, -0.6, 0])
        twice = chip("check, then insert: @ana granted twice", RED_M, 19).move_to(RULE)
        self.steps("Both commit. Two users now own @ana, and money sent to @ana goes to whichever row a query finds first.", [
            (lambda: [FadeOut(none), FadeIn(r1), FadeIn(r2), Transform(sa[2], s_sub(CY[0], "committed")),
                      Transform(sb[2], s_sub(CY[1], "committed"))], 0.9),
            "Two users",
            (lambda: [Transform(c17[2], c_sub(CY[0], "got @ana", RED_M)), Transform(c43[2], c_sub(CY[1], "got @ana", RED_M)),
                      db[0].animate.set_stroke(RED_M)], 0.8),
            "and money",
            (lambda: [FadeIn(twice, shift=0.15 * UP)], 0.8),
        ])

        self.steps("Each server said yes without hearing from the other. "
                   "The rule needs one decider that sees every claim for a handle, one at a time.", [
            (lambda: [glow(sa[0], RED_M, 1.04), glow(sb[0], RED_M, 1.04)], 1.0),
            "The rule needs",
            (lambda: [*[FadeOut(m) for m in (sa, sb, *ca, *da, db, r1, r2, twice)],
                      Transform(c17[2], c_sub(CY[0], "wants @ana")), Transform(c43[2], c_sub(CY[1], "wants @ana"))], 1.0),
        ])

        one = part_row(0, "")
        olab = T("claims log", 20, GREY_B).move_to([(LX0 + LX1) / 2, 0.68, 0])
        queued = [claim(r, h, GREY_B).move_to([x, 0, 0]) for r, h, x in (("r-7", "@bob", SLOT_X[0]), ("r-8", "@cy", SLOT_X[1]),
                                                                           ("r-9", "@dee", SLOT_X[2]))]
        oproc = VGroup(rbox(PRX, 0, PRW, 0.95, TEAL_M), T("one processor", 20).move_to([PRX, 0.2, 0]),
                       T("first claim wins", 17, GREY_B).move_to([PRX, -0.2, 0]))
        oarr = Arrow([LX1 + 0.08, 0, 0], [PRX - PRW / 2 - 0.08, 0, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.2)
        line = T("every claim in the system waits in this one line", 18, RED_M).move_to([(LX0 + LX1) / 2, -0.68, 0])
        self.steps("The simplest decider is one process reading one log in order: the first claim wins. "
                   "But then every claim in the system waits in one line.", [
            (lambda: [FadeIn(one[0]), FadeIn(one[1]), FadeIn(olab)], 0.7),
            (lambda: [FadeIn(oproc), GrowArrow(oarr)], 0.7),
            "the first claim",
            (lambda: [LaggedStart(*[FadeIn(q, shift=0.2 * RIGHT) for q in queued], lag_ratio=0.3)], 1.0),
            (lambda: [flow(oarr, TEAL_M, 0.7)], 0.7),
            "But then",
            (lambda: [FadeIn(line)], 0.7),
        ])

        rows = [part_row(y, f"P{k}") for k, y in enumerate(ROW_Y)]
        procs = [processor(k) for k in range(4)]
        parr = [Arrow([LX1 + 0.08, y, 0], [PRX - PRW / 2 - 0.08, y, 0], buff=0, stroke_width=3, color=GREY_B,
                      max_tip_length_to_length_ratio=0.2) for y in ROW_Y]
        head = T("claims log, 4 partitions", 20, GREY_B).move_to([(LX0 + LX1) / 2, 2.9, 0])
        offs = [T(f"offset {j}", 15, GREY_C).move_to([x, 2.42, 0]) for j, x in enumerate(SLOT_X)]
        hrule = rule("partition = hash(handle) mod 4")
        self.steps("Claims for different handles never conflict. So split the log into four partitions "
                   "by a hash of the handle, with one processor each.", [
            (lambda: [FadeOut(line), *[FadeOut(q) for q in queued], FadeOut(olab)], 0.6),
            "So split",
            (lambda: [*[ReplacementTransform(one[0].copy(), r[0]) for r in rows], FadeOut(one[0]), FadeOut(one[1]),
                      *[ReplacementTransform(oproc[0].copy(), p[0]) for p in procs], FadeOut(oproc), FadeOut(oarr)], 1.1),
            (lambda: [*[FadeIn(r[1]) for r in rows], *[FadeIn(r[2]) for r in rows], FadeIn(head),
                      *[FadeIn(p[1]) for p in procs], *[FadeIn(p[2]) for p in procs], *[GrowArrow(a) for a in parr]], 0.8),
            "by a hash",
            (lambda: [FadeIn(hrule, shift=0.15 * UP)], 0.7),
        ])

        k1, k2 = claim("r-1", "@ana", GOLD_M), claim("r-2", "@ana", GOLD_M)
        k1.move_to(c17[0]).shift(0.85 * DOWN)
        k2.move_to(c43[0]).shift(0.85 * DOWN)
        self.steps("@ana hashes to partition 0. User 17's claim lands there first, at offset 0. "
                   "User 43's claim names the same handle, so it lands right behind, at offset 1.", [
            (lambda: [Transform(hrule, rule('hash("ana") = 96,724, and 96,724 mod 4 = 0', GOLD_M)), glow(rows[0][0], GOLD_M, 1.02)], 1.0),
            "User 17's",
            (lambda: [FadeIn(k1), FadeIn(offs[0])], 0.4),
            (lambda: [k1.animate.move_to([SLOT_X[0], ROW_Y[0], 0])], 1.0),
            "User 43's",
            (lambda: [FadeIn(k2), FadeIn(offs[1])], 0.4),
            (lambda: [k2.animate.move_to([SLOT_X[1], ROW_Y[0], 0])], 1.2),
        ])

        self.steps("The log now fixes their order. Processor 0 reads offset 0. The handle is free, "
                   "so it records it for user 17 and grants the claim.", [
            (lambda: [glow(k1[0], GOLD_M, 1.1), glow(k2[0], GOLD_M, 1.1)], 0.9),
            "Processor 0 reads",
            (lambda: [flow(parr[0], GOLD_M, 0.8)], 0.8),
            "so it records",
            (lambda: [Transform(procs[0][2], p_sub(0, "taken: ana by u-17", GREEN_M))], 0.7),
            "and grants",
            (lambda: [Transform(c17[2], c_sub(CY[0], "granted @ana", GREEN_M)), k1[0].animate.set_stroke(GREEN_M)], 0.7),
        ])

        self.steps("Then it reads offset 1. The handle is taken, so user 43's claim is refused. "
                   "Nobody else writes that table.", [
            (lambda: [flow(parr[0], GOLD_M, 0.8)], 0.8),
            "so user 43's",
            (lambda: [Transform(c43[2], c_sub(CY[1], "refused", RED_M)), k2[0].animate.set_stroke(RED_M)], 0.8),
            "Nobody else",
            (lambda: [glow(procs[0][0], TEAL_M, 1.04)], 1.0),
        ])

        k3 = claim("r-3", "@bob", BLUE_M).move_to([SLOT_X[0], ROW_Y[3], 0])
        self.steps("Claims for other handles, like @bob, are decided in other partitions at the same time.", [
            (lambda: [FadeIn(k3, shift=0.4 * RIGHT)], 0.8),
            (lambda: [flow(parr[3], BLUE_M, 0.8)], 0.8),
            (lambda: [Transform(procs[3][2], p_sub(3, "taken: bob by u-08", GREEN_M))], 0.7),
        ])

        j1, j2 = claim("r-1", "@ana", GOLD_M), claim("r-2", "@ana", GOLD_M)
        j1.move_to(c17[0]).shift(0.85 * DOWN)
        j2.move_to(c43[0]).shift(0.85 * DOWN)
        self.steps("Now the bug. Route claims by user id instead: user 17's claim lands in partition 2, "
                   "and user 43's in partition 3.", [
            (lambda: [*[FadeOut(m) for m in (k1, k2, k3, offs[0], offs[1])], Transform(procs[0][2], p_sub(0, "taken: none")),
                      Transform(procs[3][2], p_sub(3, "taken: none")), Transform(c17[2], c_sub(CY[0], "wants @ana")),
                      Transform(c43[2], c_sub(CY[1], "wants @ana"))], 0.8),
            "Route claims",
            (lambda: [Transform(hrule, rule("partition = hash(user id) mod 4", RED_M))], 0.8),
            "user 17's claim",
            (lambda: [FadeIn(j1)], 0.3),
            (lambda: [j1.animate.move_to([SLOT_X[0], ROW_Y[2], 0])], 1.0),
            "and user 43's",
            (lambda: [FadeIn(j2)], 0.3),
            (lambda: [j2.animate.move_to([SLOT_X[0], ROW_Y[3], 0])], 1.0),
        ])

        sim = chip("simulation: 937 extra owners", RED_M, 18)
        sim.move_to([6.1 - sim.width / 2, RULE[1], 0])
        self.steps("Two processors with two empty tables both say yes, and @ana has two owners again. "
                   "The lesson's simulation counted 937 extra owners.", [
            (lambda: [flow(parr[2], GOLD_M, 0.7), flow(parr[3], GOLD_M, 0.7)], 0.7),
            (lambda: [Transform(procs[2][2], p_sub(2, "taken: ana by u-17", RED_M)), Transform(procs[3][2], p_sub(3, "taken: ana by u-43", RED_M)),
                      procs[2][0].animate.set_stroke(RED_M), procs[3][0].animate.set_stroke(RED_M)], 0.8),
            "and @ana has",
            (lambda: [Transform(c17[2], c_sub(CY[0], "granted @ana", RED_M)), Transform(c43[2], c_sub(CY[1], "granted @ana", RED_M))], 0.8),
            "The lesson's",
            (lambda: [FadeIn(sim, shift=0.15 * UP)], 0.8),
        ])

        self.steps("For a uniqueness rule, the partition key is the constraint. "
                   "So every claim for one value has to reach the same decider.", [
            (lambda: [Transform(hrule, rule("partition = hash(handle) mod 4", GREEN_M)), FadeOut(sim)], 0.9),
            (lambda: [j1.animate.move_to([SLOT_X[0], ROW_Y[0], 0]), j2.animate.move_to([SLOT_X[1], ROW_Y[0], 0]),
                      Transform(procs[2][2], p_sub(2, "taken: none")), Transform(procs[3][2], p_sub(3, "taken: none")),
                      procs[2][0].animate.set_stroke(TEAL_M), procs[3][0].animate.set_stroke(TEAL_M)], 1.1),
            "So every claim",
            (lambda: [Transform(procs[0][2], p_sub(0, "taken: ana by u-17", GREEN_M)), j1[0].animate.set_stroke(GREEN_M), j2[0].animate.set_stroke(RED_M),
                      Transform(c17[2], c_sub(CY[0], "granted @ana", GREEN_M)), Transform(c43[2], c_sub(CY[1], "refused", RED_M))], 0.8),
            (lambda: [glow(hrule[0], GREEN_M, 1.05), glow(procs[0][0], GREEN_M, 1.04)], 1.0),
        ])
        self.wait(0.6)
