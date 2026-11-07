from sfz import *


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


class HashJoin(Base):
    """sql-03: the nested loop compares every pair; the hash join builds once and probes once per row."""

    def construct(self):
        self.title_card("How a database runs a join", "the nested loop and the hash join")

        PX, HX, MX = -5.0, -0.3, 4.6
        pys = [2.0, 1.3, 0.6, -0.1, -0.8, -1.5]
        mys = [1.45, 0.65, -0.15, -0.95]
        pm = [1, 2, 4, 3, 5, 2]  # merchant of payments 1 to 6 in the seed data

        pays = VGroup(*[mbox(f"payment {i + 1}: m{m}", BLUE_M, w=2.5, h=0.55, size=20).move_to([PX, y, 0])
                        for i, (m, y) in enumerate(zip(pm, pys))])
        names = ["1 Northwind Grocers", "2 Blue Fern Cafe", "3 Metro Transit", "4 Volt Electronics"]
        mers = VGroup(*[box(n, GOLD_M, w=3.4, h=0.6, size=22).move_to([MX, y, 0]) for n, y in zip(names, mys)])
        ph = T("payments", 28, GREY_B).move_to([PX, 2.75, 0])
        mh = T("merchants", 28, GREY_B).move_to([MX, 2.75, 0])

        VX, Y1, Y2 = -3.3, -2.5, -3.1

        def val(s, y, color=YELLOW_M):
            return T(s, 26, color).move_to([VX, y, 0], aligned_edge=LEFT)

        def count(mob, a, b, fmt, y):
            def show(m, t):
                v = min(b, int(a + (b - a) * t + 1e-6))
                m.become(val(fmt.format(v).replace("1 inserts", "1 insert").replace("1 comparisons", "1 comparison"), y))
            return UpdateFromAlphaFunc(mob, show, rate_func=linear)

        nl_l = T("nested loop", 26, GREY_B).move_to([-6.3, Y1, 0], aligned_edge=LEFT)
        nl_v = val("0 comparisons", Y1)

        self.beat("Each payment holds a merchant id. To show the merchant's name, the database joins the two tables: "
                  "it pairs each payment with the merchant that has the same id.",
                  FadeIn(ph), FadeIn(mh), LaggedStart(*[FadeIn(p, shift=0.15 * RIGHT) for p in pays], lag_ratio=0.1),
                  LaggedStart(*[FadeIn(m, shift=0.15 * LEFT) for m in mers], lag_ratio=0.1), run_time=2.6)

        def fan(i):
            lines = VGroup()
            for j in range(4):
                ok = pm[i] == j + 1
                lines.add(Line(pays[i].get_right() + 0.08 * RIGHT, mers[j].get_left() + 0.08 * LEFT,
                               stroke_width=3 if ok else 2, color=GREEN_M if ok else GREY_C))
            return lines

        f0 = fan(0)
        self.beat("The simplest method is a nested loop. Take payment one and compare it with every merchant: "
                  "four comparisons, and one match.",
                  FadeIn(nl_l), FadeIn(nl_v), pays[0][0].animate.set_stroke(YELLOW_M),
                  Succession(*[Create(l, run_time=0.6) for l in f0]), count(nl_v, 0, 4, "{} comparisons", Y1),
                  run_time=3.0)

        def payment_step(i):
            fi = fan(i)

            def go():
                return [pays[i][0].animate.set_stroke(YELLOW_M), pays[i - 1][0].animate.set_stroke(BLUE_M),
                        LaggedStart(*[Create(l) for l in fi], lag_ratio=0.25),
                        Transform(nl_v, val(f"{4 * (i + 1)} comparisons", Y1))]
            return [(go, 0.85), (lambda: [FadeOut(fi)], 0.25)]

        plan = [(lambda: [FadeOut(f0)], 0.3)]
        for i in range(1, 6):
            plan += payment_step(i)
        plan += [(lambda: [pays[5][0].animate.set_stroke(BLUE_M)], 0.3)]
        self.steps("Then payment two against all four merchants, and so on down the list. "
                   "Six payments times four merchants is 24 comparisons.", plan)

        # the hash table, between the two inputs, one bucket per value of id mod 4
        border = [1, 2, 3, 0]
        hh = T("hash table: id mod 4", 28, GREY_B).move_to([HX, 2.75, 0])
        buckets = VGroup()
        for b, y in zip(border, mys):
            r = RoundedRectangle(corner_radius=0.1, width=3.6, height=0.6, stroke_color=TEAL_M, stroke_width=2.5)
            r.set_fill(BLACK, opacity=1).move_to([HX, y, 0])
            lab = M(f"bucket {b}", 18, GREY_B).move_to(r.get_left() + 0.2 * RIGHT, aligned_edge=LEFT)
            buckets.add(VGroup(r, lab))
        hj_l = T("hash join", 26, GREY_B).move_to([-6.3, Y2, 0], aligned_edge=LEFT)
        hj_v = val("0 inserts", Y2)
        self.beat("A hash join avoids most of that work. First it reads the smaller table, merchants, "
                  "and builds a hash table in memory, with one bucket for each hash value.",
                  pays.animate.set_opacity(0.3), FadeIn(hh), LaggedStart(*[FadeIn(b) for b in buckets], lag_ratio=0.15),
                  FadeIn(hj_l), FadeIn(hj_v), run_time=2.6)

        def entry(s, j):
            t = T(s, 20)
            r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.42, stroke_color=GOLD_M, stroke_width=2)
            r.set_fill(GOLD_M, opacity=0.18)
            g = VGroup(r, t.move_to(r))
            return g.move_to(buckets[j][0].get_right() + 0.14 * LEFT, aligned_edge=RIGHT)

        short = ["1 Northwind", "2 Blue Fern", "3 Metro", "4 Volt"]
        entries = VGroup(*[entry(s, j) for j, s in enumerate(short)])

        def insert(j):
            return lambda: [FadeTransform(mers[j].copy(), entries[j]),
                            Transform(hj_v, val(f"{j + 1} insert" + ("s" if j else ""), Y2))]

        self.steps("The hash here is the id mod four, the remainder after dividing by four. Merchant four lands in "
                   "bucket zero. That is the build phase: four inserts, done once.",
                   [(insert(0), 1.1), (insert(1), 1.1), (insert(2), 1.1), (insert(3), 1.1),
                    (lambda: [mers.animate.set_opacity(0.25), mh.animate.set_opacity(0.4)], 1.0)])

        def probe(i, j):
            return Arrow(pays[i].get_right(), buckets[j][0].get_left(), buff=0.1, stroke_width=3, color=BLUE_M,
                         max_tip_length_to_length_ratio=0.1)

        a0 = probe(0, 0)
        ok0 = tick(True, 0.16).next_to(buckets[0], RIGHT, buff=0.22)
        self.beat("Then the probe phase reads each payment once. Payment one has merchant one. One mod four is one, "
                  "so it goes straight to bucket one, and finds its match.",
                  pays[0].animate.set_opacity(1), GrowArrow(a0), Indicate(entries[0], color=GREEN_M),
                  FadeIn(ok0), Transform(hj_v, val("4 inserts + 1 probe", Y2)), run_time=3.0)

        a4 = probe(4, 0)
        no4 = tick(False, 0.2).next_to(buckets[0], RIGHT, buff=0.22)
        self.beat("Payment five has merchant five, which isn't in this table. Its hash is also one, but the key in "
                  "bucket one is merchant one. No match, so an inner join outputs nothing for it.",
                  FadeOut(a0), FadeOut(ok0), pays[0].animate.set_opacity(0.3), pays[4].animate.set_opacity(1),
                  GrowArrow(a4), Indicate(entries[0], color=RED_M), FadeIn(no4),
                  Transform(hj_v, val("4 inserts + 2 probes", Y2)), run_time=3.2)

        others = [(1, 1), (2, 3), (3, 2), (5, 1)]
        arrs = [probe(i, j) for i, j in others]

        def other(k):
            (i, j), a = others[k], arrs[k]
            return lambda: [pays[i].animate.set_opacity(1), GrowArrow(a), Indicate(entries[j], color=GREEN_M),
                            Transform(hj_v, val(f"4 inserts + {k + 3} probes", Y2))]

        self.steps("The other payments work the same way: one hash, one bucket and one comparison each.",
                   [(lambda: [FadeOut(a4), FadeOut(no4), pays[4].animate.set_opacity(0.3)], 0.4)]
                   + [(other(k), 0.8) for k in range(4)])

        self.beat("In total, four inserts and six probes: ten steps. The nested loop needed 24.",
                  FadeOut(VGroup(*arrs)), pays.animate.set_opacity(1), Transform(hj_v, val("4 inserts + 6 probes = 10 steps", Y2)),
                  Indicate(nl_v, color=YELLOW_M), run_time=2.4)

        nl_big = val("2.5 billion comparisons", Y1, RED_M)
        hj_big = val("about 1 million steps", Y2, GREEN_M)
        self.beat("The gap grows with the data. For a million payments and 2,500 merchants, "
                  "the nested loop needs two and a half billion comparisons. The hash join needs about a million steps.",
                  Transform(nl_v, nl_big), Transform(hj_v, hj_big), run_time=2.4)

        t_nl = T("about 40 s", 26, GREY_B).next_to(nl_big, RIGHT, buff=0.5)
        t_hj = T("174 ms", 26, GREY_B).move_to(t_nl, aligned_edge=LEFT).set_y(Y2)
        self.beat("In the lesson's test, the hash join took 174 milliseconds. Brute force would take about 40 seconds.",
                  FadeIn(t_hj, shift=0.2 * LEFT), FadeIn(t_nl, shift=0.2 * LEFT), run_time=2.0)

        self.beat("So build a hash table once from the smaller table, then read the bigger table once and probe it. "
                  "This works only for an equals condition, and the hash table must fit in memory.",
                  Circumscribe(VGroup(buckets, entries), color=TEAL_M, buff=0.12), run_time=2.0)
        self.wait(0.6)
