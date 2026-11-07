from sfz import *

SAY.insert(0, (r"\bREPEATABLE READ\b", "repeatable read"))
SAY.insert(0, (r"\bSERIALIZABLE\b", "serializable"))


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Like Scene's, but never re-adds a group whose parts are already on screen (that would draw
        filled boxes over their own labels), and leaves introducers inside groups to add themselves on cue."""
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
        """Removing a group removes its parts too, even when the parts were added one by one."""
        fam = []
        for m in mobjects:
            fam.extend(m.get_family())
        return super().remove(*fam)

    def steps(self, text, steps, after=0.25):
        """Speak one line and play several animations one after another inside it. Each step is built
        just before it plays, so it starts from where the previous one ended."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        t = 0
        for fn, rt in steps:
            self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


class WriteSkew(Base):
    """sql-12: two snapshot transactions each keep a rule, write different rows, and break it together."""

    def construct(self):
        self.title_card("Snapshot isolation and write skew", "two safe withdrawals that break the rule together")

        AX, BX = -4.6, 4.6
        RY = [1.6, 0.95, 0.2]

        def panel(x, vals, color, dashed=False):
            fr = RoundedRectangle(corner_radius=0.12, width=2.9, height=2.3, stroke_color=color, stroke_width=2.5)
            fr.set_fill(BLACK, opacity=1).move_to([x, 0.9, 0])
            if dashed:
                fr = DashedVMobject(fr, num_dashes=40)
            div = Line([x - 1.2, 0.57, 0], [x + 1.2, 0.57, 0], stroke_width=1.5, color=GREY_D)
            labs = VGroup(*[M(n, 22, GREY_B).move_to([x - 1.15, y, 0], aligned_edge=LEFT)
                            for n, y in zip(["109", "209", "total"], RY)])
            vs = VGroup(*[value(v, x, y) for v, y in zip(vals, RY)])
            return VGroup(fr, div, labs, vs)

        def value(v, x, y, color=WHITE):
            return M(str(v), 24, color).move_to([x + 1.15, y, 0], aligned_edge=RIGHT)

        db = panel(0, [50, 50, 100], WHITE)
        db_l = T("database", 24, GREY_B).move_to([0, -0.55, 0])
        rule = T("rule: Ivy's total never goes below 0", 28, GREY_B).move_to([0, -3.0, 0])

        self.beat("Ivy Chen has two accounts with 50 euros in each. The bank's rule: her total must never go below zero.",
                  FadeIn(db), FadeIn(db_l), FadeIn(rule, shift=0.2 * UP), run_time=2.4)

        ha = box("app: take 80 from 109", BLUE_M, h=0.7, size=22).move_to([AX, 2.75, 0])
        hb = box("ATM: take 80 from 209", PURPLE_M, h=0.7, size=22).move_to([BX, 2.75, 0])
        lvl = chip("REPEATABLE READ", GREY_B, size=22, mono=True).move_to([0, 2.75, 0])
        self.beat("Two withdrawals of 80 euros arrive at once, one in the app and one at an ATM. "
                  "Each runs in its own transaction, at REPEATABLE READ.",
                  FadeIn(ha, shift=0.2 * RIGHT), FadeIn(hb, shift=0.2 * LEFT), FadeIn(lvl), run_time=2.4)

        sa = panel(AX, [50, 50, 100], BLUE_M, dashed=True)
        sb = panel(BX, [50, 50, 100], PURPLE_M, dashed=True)
        sa_l = T("app's snapshot", 24, BLUE_M).move_to([AX, -0.55, 0])
        sb_l = T("ATM's snapshot", 24, PURPLE_M).move_to([BX, -0.55, 0])
        self.beat("At this level each transaction reads from a snapshot: the data as it was when the transaction started.",
                  TransformFromCopy(db, sa), TransformFromCopy(db, sb), FadeIn(sa_l), FadeIn(sb_l), run_time=2.6)

        def status(s, x, color=WHITE):
            return T(s, 24, color).move_to([x, -1.35, 0])

        st_a = status("sees total 100: enough", AX)
        st_b = status("sees total 100: enough", BX)
        self.beat("Each checks the rule against its snapshot. Each sees 100 euros, so taking 80 looks fine.",
                  Indicate(sa[3][2], color=YELLOW_M), Indicate(sb[3][2], color=YELLOW_M),
                  FadeIn(st_a), FadeIn(st_b), run_time=2.2)

        def setv(p, i, v, x, color):
            return Transform(p[3][i], value(v, x, RY[i], color))

        self.beat("The app takes 80 from account 109. The ATM takes 80 from account 209. Different rows, so neither waits.",
                  setv(sa, 0, -30, AX, BLUE_M), setv(sb, 1, -30, BX, PURPLE_M),
                  Transform(st_a, status("109 becomes -30", AX)), Transform(st_b, status("209 becomes -30", BX)),
                  run_time=2.4)

        wa = Arrow([sa[0].get_right()[0], RY[0], 0], [db[0].get_left()[0], RY[0], 0], buff=0.1, stroke_width=3,
                   color=BLUE_M, max_tip_length_to_length_ratio=0.15)
        wb = Arrow([sb[0].get_left()[0], RY[1], 0], [db[0].get_right()[0], RY[1], 0], buff=0.1, stroke_width=3,
                   color=PURPLE_M, max_tip_length_to_length_ratio=0.15)
        ok_a = tick(True, 0.16).next_to(ha, DOWN, buff=0.12).set_x(AX + 1.75)
        self.beat("Both commit. Snapshot isolation only stops two writes to the same row.",
                  GrowArrow(wa), GrowArrow(wb), setv(db, 0, -30, 0, BLUE_M), setv(db, 1, -30, 0, PURPLE_M),
                  Transform(st_a, status("COMMIT: ok", AX, GREEN_M)), Transform(st_b, status("COMMIT: ok", BX, GREEN_M)),
                  run_time=2.6)

        skew = T("write skew", 34, RED_M).move_to([0, -2.2, 0])
        bad = tick(False, 0.22).next_to(rule, RIGHT, buff=0.3)
        self.beat("Now her total is minus 60 euros. Each transaction kept the rule, and together they broke it.",
                  FadeOut(wa), FadeOut(wb), setv(db, 2, -60, 0, RED_M), rule.animate.set_color(RED_M), FadeIn(bad),
                  run_time=2.2)
        self.beat("This is write skew: two transactions read the same data, then each writes a different row, "
                  "and neither sees the other's write.",
                  FadeIn(skew, scale=1.1), Indicate(sa[3][1], color=RED_M), Indicate(sb[3][0], color=RED_M), run_time=2.4)

        # run it again under SERIALIZABLE
        lvl2 = chip("SERIALIZABLE", YELLOW_M, size=22, mono=True).move_to([0, 2.75, 0])
        sa2 = panel(AX, [50, 50, 100], BLUE_M, dashed=True)
        sb2 = panel(BX, [50, 50, 100], PURPLE_M, dashed=True)
        db2 = panel(0, [50, 50, 100], WHITE)
        self.beat("Now run them again at SERIALIZABLE, from 50 and 50.",
                  Transform(lvl, lvl2), FadeOut(skew), FadeOut(bad), rule.animate.set_color(GREY_B),
                  Transform(db, db2), Transform(sa, sa2), Transform(sb, sb2),
                  Transform(st_a, status("sees total 100: enough", AX)), Transform(st_b, status("sees total 100: enough", BX)),
                  run_time=2.4)

        wa = Arrow([sa[0].get_right()[0], RY[0], 0], [db[0].get_left()[0], RY[0], 0], buff=0.1, stroke_width=3,
                   color=BLUE_M, max_tip_length_to_length_ratio=0.15)
        self.beat("Both read 100 and both take 80, as before. The app commits first, so account 109 is now minus 30.",
                  setv(sa, 0, -30, AX, BLUE_M), setv(sb, 1, -30, BX, PURPLE_M),
                  Transform(st_b, status("209 becomes -30", BX)),
                  Succession(Wait(0.6), AnimationGroup(GrowArrow(wa), setv(db, 0, -30, 0, BLUE_M), setv(db, 2, 20, 0, WHITE),
                                                       Transform(st_a, status("COMMIT: ok", AX, GREEN_M)))),
                  run_time=3.0)

        def ring(x, y):
            return RoundedRectangle(corner_radius=0.08, width=2.62, height=0.5, stroke_color=RED_M, stroke_width=3).move_to([x, y, 0])

        ring_b = ring(BX, RY[0])
        ring_a = ring(AX, RY[1])
        self.beat("But Postgres also tracked what each one read. The ATM's check used the old balance of 109, which the app "
                  "changed. The app's check used the old 209, which the ATM changed.",
                  FadeOut(wa), Create(ring_b), Create(ring_a), run_time=2.8)
        self.beat("Running them one after the other could never give this result. "
                  "So when the ATM commits, Postgres refuses with a serialization failure and rolls it back.",
                  Transform(st_b, status("serialization failure", BX, RED_M)), setv(sb, 1, 50, BX, GREY_B),
                  FadeOut(ring_a), FadeOut(ring_b), run_time=2.6)

        sb3 = panel(BX, [-30, 50, 20], PURPLE_M, dashed=True)
        good = tick(True, 0.2).next_to(rule, RIGHT, buff=0.3)
        self.beat("The ATM retries its transaction. The new snapshot shows a total of 20 euros, not enough for 80, "
                  "so the withdrawal is refused and the rule holds.",
                  Transform(sb, sb3), Transform(st_b, status("sees total 20: refused", BX, GOLD_M)),
                  rule.animate.set_color(GREEN_M), FadeIn(good), run_time=3.0)

        self.beat("Only SERIALIZABLE catches write skew, so your code must be ready to retry.",
                  Indicate(lvl, color=YELLOW_M), run_time=1.8)
        self.wait(0.6)
