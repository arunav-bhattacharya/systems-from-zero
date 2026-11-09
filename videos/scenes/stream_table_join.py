from sfz import *

SAY.insert(0, (r"\bc-1\b", "C one"))
SAY.insert(0, (r"\bo-(\d)\b", r"O \1"))
SAY.insert(0, (r"\b9:00\b", "nine o'clock"))
SAY.insert(0, (r"\b9:30\b", "nine thirty"))
SAY.insert(0, (r"\b10:00\b", "ten o'clock"))
SAY.insert(0, (r"\b10:0(\d)\b", r"ten oh \1"))

LX0, LX1 = -6.4, -2.5                           # the two input lanes
ORD_Y, TIER_Y = 2.35, -0.75
JX, JY, JW = 0.7, 2.35, 3.0                     # the join
TX, TY, TW, TH = 0.7, -0.75, 4.6, 2.2           # the tiers table
OX = 3.35                                       # output chips, left-aligned
OUT_Y = [2.35, 1.55, 0.75]
CLX, CLY = 5.0, -0.75                           # processing-time clock
RULE_Y = -2.8


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


def lane(y, name):
    tr = RoundedRectangle(corner_radius=0.1, width=LX1 - LX0, height=0.8, stroke_color=GREY_D, stroke_width=2)
    tr.set_fill(BLACK, 1).move_to([(LX0 + LX1) / 2, y, 0])
    lab = T(name, 20, GREY_B)
    lab.move_to([LX0 + lab.width / 2, y + 0.68, 0])
    return VGroup(tr, lab)


def item(text, color, size=19):
    t = M(text, size)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.52, stroke_color=color, stroke_width=2.5)
    r.set_fill(fill(color, 0.25), 1)
    return VGroup(r, t.move_to(r)).set_z_index(3)


def at_lane(m, y, x=None):
    return m.move_to([x if x is not None else LX1 - 0.15 - m.width / 2, y, 0])


def j_sub(s, color=GREY_B):
    return T(s, 18, color).move_to([JX, JY - 0.2, 0])


def out(k, s, color):
    c = chip(s, color, 20)
    return c.move_to([OX + c.width / 2, OUT_Y[k], 0])


def trow(k, s, color=WHITE):
    return M(s, 20, color).move_to([TX, TY + 0.05 - 0.55 * k, 0])


def clock(s, color=WHITE):
    return VGroup(T("processing time", 18, GREY_B), M(s, 28, color)).arrange(DOWN, buff=0.15).move_to([CLX, CLY, 0])


def rule(s, color=GREY_B, y=RULE_Y):
    c = chip(s, color, 20)
    return c.move_to([TX, y, 0])


class StreamTableJoin(Base):
    """stream-06, section 1: orders joined with a table of customer tiers built from the customer-tiers changelog.
    c-1 is silver from 09:00 and gold from 10:00; order o-1 (09:30) sits in a lagging partition, reaches the join at
    10:01 and gets gold; a rebuild that interleaves the other way gets silver. A versioned table joins on the version
    in force at the order's timestamp (silver, every run). A late table update: o-2 (10:02) arrives before the upgrade
    and gets silver; a 5-minute grace period holds it until the upgrade arrives, so it gets gold, 5 minutes later."""

    def construct(self):
        self.title_card("Stream-table joins", "the tier as it is now, or as it was")

        ol = lane(ORD_Y, "orders")
        jn = VGroup(rbox(JX, JY, JW, 1.0, TEAL_M), T("join", 22).move_to([JX, JY + 0.2, 0]), j_sub("waiting"))
        oarr = Arrow([LX1 + 0.1, ORD_Y, 0], [JX - JW / 2 - 0.08, JY, 0], buff=0, stroke_width=3, color=GREY_B,
                     tip_length=0.2, max_tip_length_to_length_ratio=0.5)
        ohead = T("output", 20, GREY_B).move_to([OX + 0.4, 3.08, 0])
        jarr = Arrow([JX + JW / 2 + 0.08, JY, 0], [OX - 0.12, JY, 0], buff=0, stroke_width=3, color=GREY_B,
                     tip_length=0.2, max_tip_length_to_length_ratio=0.5)
        self.steps("Every order needs its customer's loyalty tier, because the tier sets the cashback.", [
            (lambda: [FadeIn(ol), FadeIn(jn), GrowArrow(oarr)], 1.0),
            "because the tier",
            (lambda: [GrowArrow(jarr), FadeIn(ohead)], 0.8),
        ])

        tl = lane(TIER_Y, "customer-tiers: every tier change")
        tb = VGroup(rbox(TX, TY, TW, TH, BLUE_M), T("tiers table", 22).move_to([TX, TY + 0.75, 0]))
        tarr = Arrow([LX1 + 0.1, TIER_Y, 0], [TX - TW / 2 - 0.08, TIER_Y, 0], buff=0, stroke_width=3, color=GREY_B,
                     tip_length=0.2, max_tip_length_to_length_ratio=0.5)
        look = Arrow([JX, JY - 0.55, 0], [TX, TY + TH / 2 + 0.05, 0], buff=0, stroke_width=3, color=GREY_B,
                     tip_length=0.2, max_tip_length_to_length_ratio=0.5)
        one = T("one row per customer", 18, GREY_B).move_to([TX, TY - 0.78, 0])
        self.steps("Calling the customer database for every order would mean 3,000 calls a second. "
                   "So the join keeps a local copy: a table built from every tier change, one row per customer.", [
            "So the join",
            (lambda: [FadeIn(tl), FadeIn(tb), GrowArrow(tarr)], 1.0),
            "one row",
            (lambda: [GrowArrow(look), FadeIn(one)], 0.8),
        ])

        ck = clock("09:00")
        s1 = item("c-1  silver  from 09:00", GREY_B)
        at_lane(s1, TIER_Y, LX0 + 0.2 + s1.width / 2)
        r1 = trow(0, "c-1   silver", GREY_A)
        self.steps("Customer c-1 is silver from 9:00. Its row goes into the table.", [
            (lambda: [FadeIn(ck), FadeIn(s1, shift=0.3 * RIGHT)], 0.8),
            "Its row",
            (lambda: [s1.animate.move_to([TX, TY + 0.05, 0]).scale(0.6).set_opacity(0)], 1.0),
            (lambda: [FadeIn(r1)], 0.5),
        ])

        g1 = item("c-1  gold  from 10:00", GOLD_M)
        at_lane(g1, TIER_Y, LX0 + 0.2 + g1.width / 2)
        self.steps("At 10:00, c-1 is upgraded to gold. The table overwrites the row, and silver is gone.", [
            (lambda: [Transform(ck[1], M("10:00", 28).move_to(ck[1])), FadeIn(g1, shift=0.3 * RIGHT)], 0.8),
            "The table overwrites",
            (lambda: [g1.animate.move_to([TX, TY + 0.05, 0]).scale(0.6).set_opacity(0)], 1.0),
            (lambda: [Transform(r1, trow(0, "c-1   gold", GOLD_M))], 0.6),
            "and silver",
            (lambda: [glow(tb[0], GOLD_M, 1.02)], 0.8),
        ])

        o1 = item("o-1  c-1  placed 09:30", WHITE)
        at_lane(o1, ORD_Y, LX0 + 0.2 + o1.width / 2)
        behind = T("its partition's consumer is behind", 17, GREY_B).move_to([(LX0 + LX1) / 2, ORD_Y - 0.66, 0])
        self.steps("Order o-1 was placed at 9:30, but it sat in a partition whose consumer is behind. "
                   "It reaches the join at 10:01.", [
            (lambda: [FadeIn(o1, shift=0.3 * RIGHT)], 0.7),
            "but it sat",
            (lambda: [FadeIn(behind)], 0.6),
            "It reaches",
            (lambda: [Transform(ck[1], M("10:01", 28).move_to(ck[1])), FadeOut(behind),
                      o1.animate.move_to([JX, JY + 0.05, 0]).scale(0.5).set_opacity(0)], 1.1),
            (lambda: [Transform(jn[2], j_sub("o-1 for c-1", WHITE))], 0.5),
        ])

        oo1 = out(0, "o-1: gold cashback", RED_M)
        self.steps("The join looks up c-1 and finds gold, the only row it has. "
                   "The order earns gold cashback for a purchase made while c-1 was silver.", [
            (lambda: [flow(look, YELLOW_M, 0.7)], 0.7),
            (lambda: [glow(tb[0], GOLD_M, 1.02)], 0.7),
            "The order earns",
            (lambda: [flow(jarr, GOLD_M, 0.6)], 0.6),
            (lambda: [FadeIn(oo1, shift=0.2 * RIGHT)], 0.6),
        ])

        o1b = item("o-1  c-1  placed 09:30", WHITE)
        at_lane(o1b, ORD_Y, LX0 + 0.2 + o1b.width / 2)
        oo2 = out(1, "rebuild, o-1: silver", RED_M)
        self.steps("Rebuild the output next week from the same topics, and the partitions may interleave the other way. "
                   "Now o-1 arrives before the upgrade, and gets silver.", [
            (lambda: [Transform(jn[2], j_sub("rebuild from the topics")), Transform(r1, trow(0, "c-1   silver", GREY_A)),
                      Transform(ck[1], M("09:40", 28).move_to(ck[1]))], 0.9),
            "Now o-1 arrives",
            (lambda: [FadeIn(o1b, shift=0.3 * RIGHT)], 0.5),
            (lambda: [o1b.animate.move_to([JX, JY + 0.05, 0]).scale(0.5).set_opacity(0)], 0.8),
            (lambda: [flow(look, YELLOW_M, 0.5)], 0.5),
            "and gets silver",
            (lambda: [FadeIn(oo2, shift=0.2 * RIGHT)], 0.6),
        ])

        nd = rule("same input, two answers: not deterministic", RED_M)
        self.steps("Same input, two answers. The result depends on arrival order, so the join isn't deterministic.", [
            (lambda: [glow(oo1[0], RED_M, 1.05), glow(oo2[0], RED_M, 1.05)], 0.9),
            "The result depends",
            (lambda: [FadeIn(nd, shift=0.15 * UP)], 0.8),
        ])

        vt = T("versioned tiers table", 22).move_to(tb[1])
        v0 = trow(0, "c-1  silver  from 09:00", GREY_A)
        v1 = trow(1, "c-1  gold    from 10:00", GOLD_M)
        self.steps("The fix is to keep the table's history. Make the table versioned: it stores each version "
                   "with the time it took effect.", [
            (lambda: [FadeOut(nd), FadeOut(one), Transform(jn[2], j_sub("waiting")), Transform(ck[1], M("10:01", 28).move_to(ck[1]))], 0.7),
            "Make the table",
            (lambda: [Transform(tb[1], vt), Transform(r1, v0)], 0.8),
            (lambda: [FadeIn(v1, shift=0.2 * DOWN)], 0.7),
        ])

        asof = rule("pick the latest version at or before the order's time", GREEN_M)
        hl = SurroundingRectangle(r1, color=GREEN_M, buff=0.1, corner_radius=0.06, stroke_width=3)
        self.steps("For o-1, the join now asks which version was valid at the order's own time, 9:30. "
                   "That's silver, in every run.", [
            (lambda: [Transform(jn[2], j_sub("o-1 as of 09:30", WHITE)), FadeIn(asof, shift=0.15 * UP)], 0.9),
            "at the order's",
            (lambda: [flow(look, YELLOW_M, 0.6)], 0.6),
            (lambda: [Create(hl)], 0.6),
            "That's silver",
            (lambda: [Transform(oo1, out(0, "o-1: silver", GREEN_M)), Transform(oo2, out(1, "rebuild, o-1: silver", GREEN_M))], 0.8),
        ])

        o2 = item("o-2  c-1  placed 10:02", WHITE)
        at_lane(o2, ORD_Y, LX0 + 0.2 + o2.width / 2)
        g2 = item("c-1  gold  from 10:00", GOLD_M)
        at_lane(g2, TIER_Y, LX0 + 0.2 + g2.width / 2)
        late = T("the upgrade is running late", 17, GREY_B).move_to([(LX0 + LX1) / 2, TIER_Y - 0.66, 0])
        oo3 = out(2, "o-2: silver", RED_M)
        self.steps("Versions can't help when the table is the late one. If the upgrade arrives late, "
                   "order o-2, placed at 10:02, gets there first and is joined with silver.", [
            (lambda: [FadeOut(hl), FadeOut(asof), FadeOut(v1, shift=0.2 * UP), FadeIn(g2), FadeIn(late)], 0.9),
            "order o-2",
            (lambda: [FadeIn(o2, shift=0.3 * RIGHT), Transform(ck[1], M("10:03", 28).move_to(ck[1]))], 0.6),
            (lambda: [o2.animate.move_to([JX, JY + 0.05, 0]).scale(0.5).set_opacity(0)], 0.8),
            "and is joined",
            (lambda: [Transform(jn[2], j_sub("o-2 as of 10:02", WHITE)), flow(look, YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(oo3, shift=0.2 * RIGHT)], 0.5),
        ])

        grace = rule("grace period: hold each order 5 minutes of stream time", YELLOW_M)
        v1b = trow(1, "c-1  gold    from 10:00", GOLD_M)
        self.steps("A grace period holds each order a while first, say 5 minutes of stream time. "
                   "The upgrade arrives meanwhile, so o-2 gets gold, and every order comes out 5 minutes later.", [
            (lambda: [FadeOut(oo3), FadeIn(grace, shift=0.15 * UP), Transform(jn[2], j_sub("holding o-2 until 10:07", YELLOW_M))], 0.9),
            "The upgrade arrives",
            (lambda: [FadeOut(late), g2.animate.move_to(v1b).scale(0.6).set_opacity(0)], 0.9),
            (lambda: [FadeIn(v1b)], 0.4),
            "so o-2 gets gold",
            (lambda: [flow(look, YELLOW_M, 0.5), Transform(jn[2], j_sub("o-2 as of 10:02", WHITE))], 0.5),
            (lambda: [FadeIn(out(2, "o-2: gold, 5 minutes later", GREEN_M), shift=0.2 * RIGHT)], 0.6),
        ])

        self.steps("A plain table answers with the tier as it is now. "
                   "To get the tier as it was, keep the history and look it up by the order's own time.", [
            (lambda: [Indicate(ck[1], color=YELLOW_M, scale_factor=1.15)], 1.0),
            "To get the tier",
            (lambda: [glow(tb[0], BLUE_M, 1.02), Indicate(r1, color=GREEN_M, scale_factor=1.08)], 1.1),
        ])
        self.wait(0.6)
