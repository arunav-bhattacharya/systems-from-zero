from sfz import *

SAY.insert(0, (r"\bauth:(\d)", r"auth number \1"))
SAY.insert(0, (r"\bget\(auth:(\d)\)", r"get auth number \1"))
SAY.insert(0, (r"\b(CAPTURED|PENDING|TOMBSTONE)\b", lambda m: m.group(1).lower()))


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


class LsmTree(Base):
    """dbi-05: a write goes to the log and the memtable, a flush makes an SSTable, a read goes newest to oldest
    with a Bloom filter, and compaction merges files."""

    def construct(self):
        self.title_card("LSM trees", "memtable, flush and compaction")

        MX, WX, AX, BX = -4.4, -4.4, 0.4, 4.4
        BW, BH = 3.3, 1.5
        MY, DY, OY = 2.0, -1.6, 0.45

        def store(x, y, color, dashed=False):
            r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=color, stroke_width=3)
            r.set_fill(color, opacity=0.1).move_to([x, y, 0])
            return r

        def rowpos(boxm, i):
            return boxm.get_left() + 0.25 * RIGHT + (0.45 - 0.45 * i) * UP

        def row(text, color=WHITE):
            return M(text, 20, color)

        def place(m, boxm, i):
            return m.move_to(rowpos(boxm, i), aligned_edge=LEFT)

        div = DashedLine([-2.2, OY, 0], [6.4, OY, 0], dash_length=0.1, stroke_width=1.5, color=GREY_D)
        mem_l = T("memory", 22, GREY_B).move_to([6.4, OY + 0.3, 0], aligned_edge=RIGHT)
        disk_l = T("disk", 22, GREY_B).move_to([6.4, OY - 0.3, 0], aligned_edge=RIGHT)
        mt = store(MX, MY, TEAL_M)
        mt_l = T("memtable: sorted by key", 24, TEAL_M).next_to(mt, UP, buff=0.18)
        wal = store(WX, DY, GREY_B)
        wal_l = T("log: in arrival order", 24, GREY_B).next_to(wal, DOWN, buff=0.18)

        self.beat("A B+tree rewrites pages in place, so random inserts mean scattered disk writes. "
                  "A log-structured merge tree, or LSM tree, makes them sequential.",
                  Create(div), FadeIn(mem_l), FadeIn(disk_l), FadeIn(mt), FadeIn(mt_l), FadeIn(wal), FadeIn(wal_l),
                  run_time=2.6)

        op = chip("put(auth:1, PENDING)", BLUE_M, size=20, mono=True).move_to([MX, OY, 0])
        up = Arrow(op.get_top(), mt.get_bottom(), buff=0.06, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.35)
        dn = Arrow(op.get_bottom(), wal.get_top(), buff=0.06, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.25)
        mrows = [place(row("auth:1  PENDING"), mt, 0)]
        wrows = [place(row("auth:1  PENDING", GREY_B), wal, 0)]
        self.beat("A write goes to two places. It is appended to a log on disk, so a crash can't lose it, "
                  "and it goes into the memtable, a sorted map in memory.",
                  FadeIn(op, shift=0.2 * RIGHT), GrowArrow(dn), GrowArrow(up),
                  Succession(Wait(0.6), AnimationGroup(FadeIn(wrows[0], shift=0.2 * DOWN), FadeIn(mrows[0], shift=0.2 * UP))),
                  run_time=3.0)

        def newop(text, color=BLUE_M):
            return chip(text, color, size=20, mono=True).move_to([MX, OY, 0])

        r3 = place(row("auth:3  PENDING"), mt, 1)
        w3 = place(row("auth:3  PENDING", GREY_B), wal, 1)
        r2 = place(row("auth:2  PENDING"), mt, 1)
        w2 = place(row("auth:2  PENDING", GREY_B), wal, 2)
        self.beat("Two more arrive, 3 before 2. The memtable keeps them in key order, "
                  "and no page on disk is touched.",
                  Succession(
                      AnimationGroup(Transform(op, newop("put(auth:3, PENDING)")), FadeIn(w3, shift=0.2 * DOWN),
                                     FadeIn(r3, shift=0.2 * UP), run_time=1.2),
                      Wait(0.4),
                      AnimationGroup(Transform(op, newop("put(auth:2, PENDING)")), FadeIn(w2, shift=0.2 * DOWN),
                                     r3.animate.move_to(rowpos(mt, 2), aligned_edge=LEFT), FadeIn(r2, shift=0.2 * UP),
                                     run_time=1.2)),
                  run_time=3.2)
        mrows = [mrows[0], r2, r3]
        wrows += [w3, w2]

        s1 = store(AX, DY, GOLD_M)
        s1_l = T("SSTable 1", 24, GOLD_M).next_to(s1, DOWN, buff=0.18)
        self.steps("When the memtable is full, it is flushed to disk in key order, in one sequential write: "
                   "an SSTable, a sorted string table, which never changes. The log and the memtable start over.",
                   [(lambda: [FadeOut(op), FadeOut(up), FadeOut(dn), FadeIn(s1), FadeIn(s1_l),
                              *[m.animate.move_to(rowpos(s1, i), aligned_edge=LEFT) for i, m in enumerate(mrows)]], 2.4),
                    (lambda: [Circumscribe(s1, color=GOLD_M, buff=0.08)], 1.4),
                    (lambda: [Wait()], 5.4),
                    (lambda: [*[FadeOut(w) for w in wrows], Circumscribe(mt, color=TEAL_M, buff=0.08)], 1.2)])
        s1rows = mrows

        op = newop("put(auth:2, CAPTURED)")
        up = Arrow(op.get_top(), mt.get_bottom(), buff=0.06, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.35)
        dn = Arrow(op.get_bottom(), wal.get_top(), buff=0.06, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.25)
        n2 = place(row("auth:2  CAPTURED"), mt, 0)
        n3 = place(row("auth:3  TOMBSTONE", RED_M), mt, 1)
        v2 = place(row("auth:2  CAPTURED", GREY_B), wal, 0)
        v3 = place(row("auth:3  TOMBSTONE", GREY_B), wal, 1)
        self.beat("Then auth:2 is captured, so a newer version goes into the memtable. "
                  "A delete of auth:3 writes a tombstone, a marker that says deleted.",
                  Succession(
                      AnimationGroup(FadeIn(op), GrowArrow(up), GrowArrow(dn), run_time=0.8),
                      AnimationGroup(FadeIn(n2, shift=0.2 * UP), FadeIn(v2, shift=0.2 * DOWN), run_time=1.0),
                      Wait(1.6),
                      AnimationGroup(Transform(op, newop("delete(auth:3)", RED_M)), FadeIn(n3, shift=0.2 * UP),
                                     FadeIn(v3, shift=0.2 * DOWN), run_time=1.0)),
                  run_time=4.4)

        s2 = store(AX, DY, GOLD_M)
        s2_l = T("SSTable 2", 24, GOLD_M).next_to(s2, DOWN, buff=0.18)
        self.steps("The next flush makes a second table. Now two keys have two versions on disk, "
                   "and the newer table wins.",
                   [(lambda: [FadeOut(op), FadeOut(up), FadeOut(dn), FadeOut(v2), FadeOut(v3)], 0.5),
                    (lambda: [VGroup(s1, s1_l, *s1rows).animate.set_x(BX), FadeIn(s2), FadeIn(s2_l),
                              n2.animate.move_to(rowpos(s2, 0), aligned_edge=LEFT),
                              n3.animate.move_to(rowpos(s2, 1), aligned_edge=LEFT)], 2.2)])
        s2rows = [n2, n3]

        # reads: memtable first, then newest to oldest
        op = newop("get(auth:2)", YELLOW_M)
        up = Arrow(op.get_top(), mt.get_bottom(), buff=0.06, stroke_width=3, color=YELLOW_M, max_tip_length_to_length_ratio=0.35)
        hit2 = SurroundingRectangle(n2, color=GREEN_M, buff=0.1, corner_radius=0.05)
        self.steps("A read checks the memtable, then the tables from newest to oldest, and stops at the first hit. "
                   "get(auth:2) finds CAPTURED in table 2.",
                   [(lambda: [FadeIn(op), GrowArrow(up)], 0.8),
                    (lambda: [Circumscribe(mt, color=YELLOW_M, buff=0.08)], 0.9),
                    (lambda: [Circumscribe(s2, color=YELLOW_M, buff=0.08)], 0.9),
                    (lambda: [Wait()], 3.0),
                    (lambda: [Create(hit2), Transform(op, newop("get(auth:2) = CAPTURED", GREEN_M))], 0.8)])

        # Bloom filters, one per SSTable, kept in memory
        def bloom(x, bits, color):
            sq = VGroup(*[Square(0.28, stroke_width=2, stroke_color=GREY_B).set_fill(color if b else BLACK, opacity=0.85 if b else 1)
                          for b in bits]).arrange(RIGHT, buff=0.04).move_to([x, 1.3, 0])
            return sq

        f2 = bloom(AX, [0, 1, 0, 1, 0, 0, 1, 0], GOLD_M)
        f1 = bloom(BX, [1, 0, 1, 1, 0, 1, 0, 1], GOLD_M)
        f2_l = T("Bloom filter", 22, GREY_B).next_to(f2, UP, buff=0.15)
        f1_l = T("Bloom filter", 22, GREY_B).next_to(f1, UP, buff=0.15)
        self.beat("get(auth:1) is not in table 2, but checking costs a disk read. "
                  "So every table has a Bloom filter: a few bits per key, kept in memory.",
                  FadeOut(hit2), Transform(op, newop("get(auth:1)", YELLOW_M)),
                  FadeIn(f2), FadeIn(f1), FadeIn(f2_l), FadeIn(f1_l), run_time=2.4)

        probe = VGroup(SurroundingRectangle(f2[0], color=RED_M, buff=0.03), SurroundingRectangle(f2[4], color=RED_M, buff=0.03))
        no_l = T("no: definitely not here", 22, RED_M).move_to(f2_l)
        hit1 = SurroundingRectangle(s1rows[0], color=GREEN_M, buff=0.1, corner_radius=0.05)
        self.beat("The filter of table 2 says definitely not here, so the read skips that table and finds auth:1 in table 1.",
                  Succession(AnimationGroup(Create(probe), Transform(f2_l, no_l), run_time=1.0),
                             AnimationGroup(s2.animate.set_stroke(opacity=0.35).set_fill(opacity=0.03), *[r.animate.set_opacity(0.35) for r in s2rows], run_time=0.6),
                             Wait(0.4), Circumscribe(s1, color=YELLOW_M, buff=0.08, run_time=0.8), Create(hit1, run_time=0.6),
                             Transform(op, newop("get(auth:1) = PENDING", GREEN_M), run_time=0.6)),
                  run_time=4.4)

        hit3 = SurroundingRectangle(n3, color=RED_M, buff=0.1, corner_radius=0.05)
        f2_l2 = T("Bloom filter", 22, GREY_B).move_to(f2_l)
        self.steps("get(auth:3) stops at the tombstone in table 2: not found. "
                   "Reading on would bring the deleted value back.",
                   [(lambda: [FadeOut(probe), FadeOut(hit1), Transform(f2_l, f2_l2), s2.animate.set_stroke(opacity=1).set_fill(opacity=0.1),
                              *[r.animate.set_opacity(1) for r in s2rows], Transform(op, newop("get(auth:3)", YELLOW_M))], 1.0),
                    (lambda: [Create(hit3)], 0.7),
                    (lambda: [Transform(op, newop("get(auth:3) = not found", RED_M))], 0.7)])

        # compaction: merge both files, newest version of each key wins, the tombstone goes too
        stale = [s1rows[1], s1rows[2]]
        x_marks = VGroup(*[Line(r.get_left() + 0.05 * LEFT, r.get_right() + 0.05 * RIGHT, stroke_width=3, color=RED_M) for r in stale])
        self.beat("Compaction merges tables, like merge sort, and keeps only the newest version of each key.",
                  FadeOut(hit3), FadeOut(op), FadeOut(up), *[r.animate.set_color(GREY_D) for r in stale], Create(x_marks),
                  run_time=2.8)

        s3 = store((AX + BX) / 2, DY, GOLD_M)
        s3_l = T("SSTable 3", 24, GOLD_M).next_to(s3, DOWN, buff=0.18)
        f3 = bloom((AX + BX) / 2, [1, 1, 0, 0, 1, 0, 1, 0], GOLD_M)
        f3_l = T("Bloom filter", 22, GREY_B).next_to(f3, UP, buff=0.15)
        keep1, keep2 = s1rows[0], n2
        self.beat("The tombstone is dropped as well, since no older table is left that could hold auth:3. "
                  "Now a read checks one table instead of two.",
                  Succession(n3.animate(run_time=1.2).set_color(GREY_D), AnimationGroup(
                      FadeOut(VGroup(*stale, x_marks, n3)), FadeOut(VGroup(s1, s2, s1_l, s2_l)), FadeIn(s3), FadeIn(s3_l),
                      keep1.animate.move_to(rowpos(s3, 0), aligned_edge=LEFT), keep2.animate.move_to(rowpos(s3, 1), aligned_edge=LEFT),
                      FadeOut(VGroup(f1, f2, f1_l, f2_l)), FadeIn(f3), FadeIn(f3_l), run_time=1.6)),
                  run_time=3.4)

        self.beat("So every write is a cheap append. A read may look in several tables, "
                  "and Bloom filters and compaction keep that cheap.",
                  Circumscribe(mt, color=TEAL_M, buff=0.08), Circumscribe(s3, color=GOLD_M, buff=0.08), run_time=2.0)
        self.wait(0.6)
