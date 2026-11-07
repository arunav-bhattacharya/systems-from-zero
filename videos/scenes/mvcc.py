from sfz import *

SAY.insert(0, (r"\bxmin\b", "ex min"))
SAY.insert(0, (r"\bxmax\b", "ex max"))
SAY.insert(0, (r"\bVACUUM\b", "vacuum"))
SAY.insert(0, (r"\bAutovacuum\b", "Auto vacuum"))


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


class Mvcc(Base):
    """dbi-07: an UPDATE writes a new version, two snapshots see different versions without waiting, VACUUM."""

    def construct(self):
        self.title_card("MVCC", "every update writes a new version")

        V1, V2 = 0.55, -0.45
        RW = 6.4
        CX = [-2.2, -0.85, 0.95, 2.25]  # xmin, xmax, id, balance

        def version(xmin, xmax, bal, y, color=WHITE, hidden=True):
            r = RoundedRectangle(corner_radius=0.1, width=RW, height=0.7, stroke_color=color, stroke_width=3)
            r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.12), opacity=1).move_to([0, y, 0])
            sep = DashedLine([0.05, y - 0.25, 0], [0.05, y + 0.25, 0], dash_length=0.06, stroke_width=1.5, color=GREY_C)
            a = M(str(xmin), 24, GREY_B).move_to([CX[0], y, 0])
            b = M(str(xmax), 24, GREY_B).move_to([CX[1], y, 0])
            c = M(str(bal), 24, WHITE).move_to([CX[3], y, 0])
            idt = M("7", 24, WHITE).move_to([CX[2], y, 0])
            g = VGroup(r, sep, a, b, c, idt)
            if hidden:
                for m in (sep, a, b):
                    m.set_opacity(0)
            return g

        def status(s, color):
            return T(s, 28, color).move_to([0, -2.85, 0])

        v1 = version(100, 0, 500, V1)
        hdr = VGroup(*[M(n, 20, GREY_B).move_to([x, V1 + 0.66, 0]) for n, x in zip(["xmin", "xmax", "id", "balance"], CX)])
        hdr[0].set_opacity(0)
        hdr[1].set_opacity(0)
        writer = box("transaction 105: UPDATE balance to 450", GOLD_M, h=0.7, size=24).move_to([0, 2.55, 0])
        wa = Arrow(writer.get_bottom(), v1.get_top(), buff=0.1, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.15)
        ra_box = box("reader 1", BLUE_M, w=2.1, h=0.7, size=26).move_to([-5.25, 0.05, 0])
        ra = Arrow(ra_box.get_right(), v1[0].get_left() + 0.0 * UP, buff=0.1, stroke_width=3, color=BLUE_M,
                   max_tip_length_to_length_ratio=0.15)
        st = status("one of them has to wait", RED_M)
        self.beat("A report is reading one row while a payment job updates it. With only one copy of the row, "
                  "one of them has to wait for the other.",
                  FadeIn(v1), FadeIn(hdr), FadeIn(writer), GrowArrow(wa), FadeIn(ra_box), GrowArrow(ra), FadeIn(st), run_time=2.6)

        page = RoundedRectangle(corner_radius=0.15, width=RW + 0.5, height=2.9, stroke_color=GREY_D, stroke_width=2).move_to([0, 0.28, 0])
        page_l = T("one page of the accounts table", 22, GREY_B).next_to(page, DOWN, buff=0.15)
        self.beat("Postgres avoids the wait by keeping more than one version of a row. "
                  "This is MVCC, multi-version concurrency control.",
                  FadeOut(st), FadeOut(wa), FadeOut(ra), Create(page), FadeIn(page_l), run_time=2.0)

        self.beat("Every version carries two hidden fields. xmin is the transaction that created it. "
                  "xmax is the transaction that replaced it, or zero while nobody has.",
                  Succession(AnimationGroup(*[m.animate.set_opacity(1) for m in [*v1[1:4], hdr[0], hdr[1]]], run_time=1.0),
                             AnimationGroup(Indicate(VGroup(hdr[0], v1[2]), color=YELLOW_M), Indicate(VGroup(hdr[1], v1[3]), color=YELLOW_M), run_time=1.4)),
                  run_time=2.8)

        v2 = version(105, 0, 450, V2, GOLD_M, hidden=False)
        x105 = M("105", 24, GOLD_M).move_to(v1[3])
        self.beat("Transaction 105 changes the balance to 450. It doesn't overwrite the row. It writes a new version "
                  "with xmin 105, and stamps 105 into the old version's xmax.",
                  Circumscribe(writer, color=GOLD_M, buff=0.08), TransformFromCopy(v1, v2),
                  Succession(Wait(1.4), Transform(v1[3], x105)), run_time=3.4)

        ra_l = VGroup(T("snapshot taken", 22, BLUE_M), T("while 105 runs", 22, BLUE_M)).arrange(DOWN, buff=0.1)
        ra_l.next_to(ra_box, DOWN, buff=0.2)
        self.beat("Each reader works from a snapshot: a note of which transactions had committed when it started.",
                  FadeIn(ra_l, shift=0.2 * UP), Circumscribe(ra_box, color=BLUE_M, buff=0.08), run_time=2.0)

        ra = Arrow(ra_box.get_right(), v1[0].get_left(), buff=0.1, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.15)
        self.beat("Reader 1 took its snapshot while 105 was still running, so everything 105 wrote is invisible to it. "
                  "It reads the old version, and sees 500.",
                  GrowArrow(ra), v2.animate.set_opacity(0.3), Indicate(v1[4], color=BLUE_M), run_time=2.8)

        rb_box = box("reader 2", PURPLE_M, w=2.1, h=0.7, size=26).move_to([5.25, 0.05, 0])
        rb_l = VGroup(T("snapshot taken", 22, PURPLE_M), T("after 105 commits", 22, PURPLE_M)).arrange(DOWN, buff=0.1)
        rb_l.next_to(rb_box, DOWN, buff=0.2)
        rb = Arrow(rb_box.get_left(), v2[0].get_right(), buff=0.1, stroke_width=3, color=PURPLE_M, max_tip_length_to_length_ratio=0.15)
        self.beat("Reader 2 starts after 105 commits. For it, the old version has been replaced, and the new one is live. "
                  "It sees 450.",
                  FadeIn(rb_box), FadeIn(rb_l), v2.animate.set_opacity(1), Succession(Wait(0.8), GrowArrow(rb, run_time=0.8)),
                  run_time=3.0)

        st = status("nobody waited", GREEN_M)
        self.beat("Nobody waited. The writer made a new version instead of changing the one reader 1 was using. "
                  "Readers don't block writers, and writers don't block readers.",
                  FadeIn(st, shift=0.2 * UP), Indicate(v2[4], color=PURPLE_M), Indicate(v1[4], color=BLUE_M), run_time=2.2)

        st2 = status("dead version: no snapshot can see it", GREY_B)
        self.beat("When reader 1 finishes, no snapshot can see the old version anymore. It is a dead version, "
                  "and it still takes up space in the page.",
                  FadeOut(VGroup(ra_box, ra_l, ra)), v1.animate.set_opacity(0.35), Transform(st, st2), run_time=2.6)

        free = DashedVMobject(RoundedRectangle(corner_radius=0.1, width=RW, height=0.7, stroke_color=GREY_C, stroke_width=2),
                              num_dashes=60).move_to([0, V1, 0])
        free_l = T("free space", 22, GREY_B).move_to(free)
        vac = chip("VACUUM", TEAL_M, size=24, mono=True).move_to([-5.25, V1, 0])
        st3 = status("the space is free for new rows", TEAL_M)
        self.beat("VACUUM finds versions that no snapshot can see, and marks their space free for new rows. "
                  "Postgres also runs it on its own, in the background.",
                  FadeIn(vac, shift=0.2 * RIGHT), Succession(Wait(0.8), AnimationGroup(FadeOut(v1), Create(free), FadeIn(free_l))),
                  Transform(st, st3), run_time=3.0)

        st4 = status("keep transactions short", YELLOW_M)
        self.beat("A version stays as long as any snapshot might still need it. So one transaction left open for hours "
                  "stops VACUUM, and dead versions pile up.",
                  Transform(st, st4), run_time=2.0)
        self.beat("So every update writes a new version, every snapshot picks the versions it may see, "
                  "and VACUUM clears away the ones nobody can see.",
                  Circumscribe(v2[0], color=GOLD_M, buff=0.08), Indicate(vac, color=TEAL_M), run_time=2.0)
        self.wait(0.6)
