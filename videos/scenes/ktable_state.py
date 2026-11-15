from sfz import *

SAY.insert(0, (r"\bRocksDB\b", "rocks D B"))

PAY_Y, CELL_W, CELL_X = 2.55, 1.75, [-3.85, -1.95, -0.05, 1.85, 3.75]     # payments-0: five records
PAYS = [("acct-1", "+100"), ("acct-2", "+50"), ("acct-1", "-30"), ("acct-1", "+5"), ("acct-2", "-20")]
IX, IY, IW, IH = -3.5, -0.85, 5.6, 3.0                                      # the instance
SX, SY, SW, SH = -3.5, -1.0, 4.9, 2.1                                        # its store
ROW_SY = [-0.72, -1.3]                                                       # store rows: acct-1, acct-2
CX, CW = 3.5, 4.4                                                            # changelog rows
CL_Y = [-0.15, -0.7, -1.25, -1.8, -2.35]
CLOG = [("acct-1", "100.00"), ("acct-2", "50.00"), ("acct-1", "70.00"), ("acct-1", "75.00"), ("acct-2", "30.00")]


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


def fill(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    a, b = path.get_start(), path.get_end()
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])




def cell(k, color=GREY_B):
    a, amt = PAYS[k]
    r = RoundedRectangle(corner_radius=0.08, width=CELL_W, height=0.6, stroke_color=color, stroke_width=2.5)
    r.set_fill(fill(color), 1).move_to([CELL_X[k], PAY_Y, 0])
    return VGroup(r, M(f"{a} {amt}", 17).move_to([CELL_X[k], PAY_Y, 0]))


def clrow(k, color=TEAL_M):
    a, v = CLOG[k]
    y = CL_Y[k]
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=0.46, stroke_color=color, stroke_width=2.5)
    r.set_fill(fill(color), 1).move_to([CX, y, 0])
    return VGroup(r, left_at(M(str(k), 18, GREY_B), CX - CW / 2 + 0.2, y), left_at(M(f"{a} = {v}", 20), CX - CW / 2 + 0.75, y))


def srow(i, a, v, color=WHITE):
    return left_at(M(f"{a} = {v}", 24, color), SX - 1.5, ROW_SY[i])


def pointer(k):
    x = CELL_X[k]
    tri = Triangle(color=GOLD_M, fill_color=GOLD_M, fill_opacity=1, stroke_width=0).scale(0.1).move_to([x - 0.55, 1.62, 0])
    return VGroup(tri, left_at(T(f"committed {k}", 19, GOLD_M), x - 0.4, 1.62))


class KTableState(Base):
    """stream-05, section 1: payments-0 (acct-1 +100, acct-2 +50, acct-1 -30, acct-1 +5, acct-2 -20) folded by one task into
    the 'balances' store on local disk; every update also goes to balances-changelog-0. Commit at offset 4, the instance
    and its disk are lost, a new instance restores 4 changelog records (acct-1 = 75.00, acct-2 = 50.00), then carries on
    at offset 4 (acct-2 = 30.00). Section 0's numbers: 3,000 payments a second, 2 million accounts, 1.8 billion records."""

    def construct(self):
        self.title_card("Tables in Kafka Streams", "a local store, and a changelog that outlives it")

        cells = [cell(k) for k in range(5)]
        offs = VGroup(*[M(str(k), 17, GREY_B).move_to([CELL_X[k], PAY_Y - 0.5, 0]) for k in range(5)])
        ptl = left_at(T("payments-0", 22, GREY_B), -6.5, PAY_Y)
        inst = RoundedRectangle(corner_radius=0.16, width=IW, height=IH, stroke_color=WHITE, stroke_width=3)
        inst.set_fill(BLACK, 1).move_to([IX, IY, 0])
        ititle = left_at(T("balance app, instance 1", 22), IX - IW / 2 + 0.3, IY + IH / 2 - 0.32)
        sbox = RoundedRectangle(corner_radius=0.12, width=SW, height=SH, stroke_color=GREY_B, stroke_width=2.5)
        sbox.set_fill(fill(GREY_B, 0.1), 1).move_to([SX, SY, 0])
        stitle = T("map in memory", 20, GREY_B).move_to([SX, SY + SH / 2 - 0.27, 0])
        scontent = T("2 million balances", 24).move_to([SX, SY - 0.15, 0])
        self.steps("A balance service reads the payments topic, about three thousand payments a second, and keeps the balance "
                   "of two million accounts. If its machine dies, how does the next one get those balances back?", [
            (lambda: [FadeIn(ptl), LaggedStart(*[FadeIn(c, shift=0.1 * LEFT) for c in cells], lag_ratio=0.15), FadeIn(offs)], 1.2),
            "and keeps",
            (lambda: [FadeIn(inst), FadeIn(ititle), FadeIn(sbox), FadeIn(stitle)], 0.8),
            (lambda: [FadeIn(scontent)], 0.5),
            "If its machine",
            (lambda: [glow(inst, GOLD_M, 1.02)], 1.0),
        ])

        empty = T("empty", 24, RED_M).move_to([SX, SY - 0.15, 0])
        self.steps("The simplest version keeps them in a map in memory. After a restart the map is empty, "
                   "and the only way back is to read every payment again.", [
            "After a restart",
            (lambda: [inst.animate.set_stroke(RED_M), Transform(scontent, empty)], 0.8),
            "read every payment",
            (lambda: [*[glow(c[0], RED_M, 1.04) for c in cells]], 1.0),
        ])

        cost = chip("replay 7 days: 1.8 billion records, about 5 hours", RED_M, 21).move_to([0, -3.2, 0])
        self.steps("Seven days of payments is one point eight billion records: five hours to read, "
                   "and older payments are already gone.", [
            (lambda: [FadeIn(cost, shift=0.1 * UP)], 0.8),
            "and older payments",
            (lambda: [glow(cost[0], RED_M, 1.04)], 0.9),
        ])

        # ---- the store and the changelog -----------------------------------------------------------------------
        st2 = T("store: balances (RocksDB, local disk)", 20, BLUE_M).move_to([SX, SY + SH / 2 - 0.27, 0])
        fast = T("a read takes microseconds", 19, GREY_B).move_to([SX, SY - 0.15, 0])
        self.steps("Kafka Streams keeps the table in a store on local disk, "
                   "a small RocksDB database inside the service, so a read takes microseconds.", [
            (lambda: [FadeOut(cost), FadeOut(scontent), inst.animate.set_stroke(WHITE),
                      sbox.animate.set_stroke(BLUE_M).set_fill(fill(BLUE_M), 1), Transform(stitle, st2)], 1.0),
            "so a read",
            (lambda: [FadeIn(fast)], 0.6),
        ])

        cltl = left_at(T("changelog topic: balances-changelog-0", 20, TEAL_M), CX - CW / 2, 0.42)
        wr = Arrow([IX + IW / 2 + 0.08, SY, 0], [CX - CW / 2 - 0.1, SY, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.15)
        wrl = T("every write", 18, GREY_B).next_to(wr, UP, buff=0.1)
        self.steps("And every write to the store is also sent to a topic in Kafka, the store's changelog.", [
            (lambda: [FadeOut(fast), GrowArrow(wr), FadeIn(wrl)], 0.8),
            "the store's changelog",
            (lambda: [FadeIn(cltl, shift=0.1 * DOWN)], 0.7),
        ])

        ptr = pointer(0)
        srows = [None, None]
        crows = [clrow(k) for k in range(5)]
        cur = SurroundingRectangle(cells[0][0], color=YELLOW_M, buff=0.05, corner_radius=0.1, stroke_width=4)

        def read(k):
            path = Line([CELL_X[k], PAY_Y - 0.72, 0], [IX + 0.4 * (CELL_X[k] - IX) / 4, IY + IH / 2 + 0.05, 0])
            return [cur.animate.move_to(cells[k][0]), flow(path, YELLOW_M, 0.5)]

        def put(i, a, v, color=WHITE):
            new = srow(i, a, v, color)
            if srows[i] is None:
                srows[i] = new
                return [FadeIn(new, scale=0.9)]
            return [Transform(srows[i], new)]

        self.steps("Offset zero: account one pays in a hundred. The store gets account one at a hundred, "
                   "and the changelog gets the same record.", [
            (lambda: [FadeIn(ptr), Create(cur)], 0.6),
            (lambda: read(0), 0.6),
            "The store gets",
            (lambda: put(0, "acct-1", "100.00"), 0.6),
            "and the changelog",
            (lambda: [flow(wr, TEAL_M, 0.5)], 0.5),
            (lambda: [FadeIn(crows[0], shift=0.1 * RIGHT)], 0.5),
        ])

        self.steps("Account two pays in fifty: a new row. Then account one pays thirty. The row changes in place to seventy, "
                   "but a log can't change a record, so the changelog appends a new one.", [
            (lambda: read(1), 0.6),
            (lambda: [*put(1, "acct-2", "50.00"), flow(wr, TEAL_M, 0.5)], 0.6),
            (lambda: [FadeIn(crows[1], shift=0.1 * RIGHT)], 0.4),
            "Then account one",
            (lambda: read(2), 0.6),
            "The row changes",
            (lambda: put(0, "acct-1", "70.00", YELLOW_M), 0.6),
            "so the changelog",
            (lambda: [flow(wr, TEAL_M, 0.5)], 0.5),
            (lambda: [FadeIn(crows[2], shift=0.1 * RIGHT)], 0.5),
        ])

        self.steps("Account one gets five back and reaches seventy five. "
                   "Then the app commits offset four: the next payment it will read.", [
            (lambda: [*read(3), Transform(srows[0], srow(0, "acct-1", "70.00"))], 0.6),
            (lambda: [*put(0, "acct-1", "75.00"), flow(wr, TEAL_M, 0.5)], 0.6),
            (lambda: [FadeIn(crows[3], shift=0.1 * RIGHT)], 0.4),
            "Then the app commits",
            (lambda: [FadeOut(cur), Transform(ptr, pointer(4))], 0.9),
        ])

        # ---- the instance dies -----------------------------------------------------------------------------------
        gone = T("empty: the disk is gone", 22, RED_M).move_to([SX, SY - 0.15, 0])
        dead = tick(False, 0.3).move_to([IX + IW / 2 - 0.45, IY + IH / 2 - 0.35, 0])
        self.steps("Now the instance dies, and its disk goes with it. The store is gone.", [
            (lambda: [inst.animate.set_stroke(RED_M), Create(dead), Transform(ititle, left_at(T("instance 1: gone", 22, RED_M),
                      IX - IW / 2 + 0.3, IY + IH / 2 - 0.32))], 0.8),
            "The store is gone",
            (lambda: [FadeOut(srows[0]), FadeOut(srows[1]), FadeIn(gone), sbox.animate.set_stroke(RED_M).set_fill(fill(RED_M), 1)], 0.8),
        ])

        self.steps("Kafka still has everything that matters: the payments, the changelog and the committed offset.", [
            "the payments",
            (lambda: [*[glow(c[0], GREEN_M, 1.04) for c in cells]], 0.7),
            "the changelog",
            (lambda: [*[glow(crows[k][0], GREEN_M, 1.03) for k in range(4)]], 0.7),
            "the committed",
            (lambda: [Indicate(ptr, color=GREEN_M)], 0.8),
        ])

        cur2 = SurroundingRectangle(crows[0][0], color=YELLOW_M, buff=0.05, corner_radius=0.1, stroke_width=4)
        rest = T("restoring", 20, BLUE_M).move_to([SX, -1.75, 0])
        srows = [None, None]

        def restore(k):
            a, v = CLOG[k]
            i = 0 if a == "acct-1" else 1
            out = [cur2.animate.move_to(crows[k][0]), flow(Line(wr.get_end(), wr.get_start()), TEAL_M, 0.45)]
            return out + put(i, a, v, YELLOW_M if k == 2 or k == 3 else WHITE)

        self.steps("A new instance takes over. Before it reads any payment, it replays the changelog from the start "
                   "into a fresh store. For each account, the last value wins.", [
            (lambda: [FadeOut(dead), inst.animate.set_stroke(BLUE_M), sbox.animate.set_stroke(BLUE_M).set_fill(fill(BLUE_M), 1),
                      Transform(ititle, left_at(T("balance app, instance 2", 22, BLUE_M), IX - IW / 2 + 0.3, IY + IH / 2 - 0.32)),
                      FadeOut(gone)], 0.9),
            "it replays",
            (lambda: [Create(cur2), FadeIn(rest)], 0.5),
            *[(lambda k=k: restore(k), 0.55) for k in range(4)],
            "the last value wins",
            (lambda: [Transform(srows[0], srow(0, "acct-1", "75.00", GREEN_M)), Transform(srows[1], srow(1, "acct-2", "50.00", GREEN_M)),
                      FadeOut(rest)], 0.7),
        ])

        cur = SurroundingRectangle(cells[4][0], color=YELLOW_M, buff=0.05, corner_radius=0.1, stroke_width=4)
        self.steps("Then it carries on from offset four: account two pays twenty and drops to thirty.", [
            (lambda: [FadeOut(cur2), Create(cur), Indicate(ptr, color=GOLD_M)], 0.8),
            "account two pays",
            (lambda: [flow(Line([CELL_X[4], PAY_Y - 0.72, 0], [IX + 0.4 * (CELL_X[4] - IX) / 4, IY + IH / 2 + 0.05, 0]), YELLOW_M, 0.6),
                      Transform(srows[0], srow(0, "acct-1", "75.00"))], 0.6),
            (lambda: [Transform(srows[1], srow(1, "acct-2", "30.00", YELLOW_M))], 0.5),
            (lambda: [flow(wr, TEAL_M, 0.5)], 0.5),
            (lambda: [FadeIn(crows[4], shift=0.1 * RIGHT)], 0.5),
        ])

        def strike(k):
            r = crows[k][0]
            return Line(r.get_left() + 0.15 * RIGHT, r.get_right() + 0.15 * LEFT, stroke_width=3, color=RED_M)

        strikes = [strike(k) for k in (0, 1, 2)]
        two = chip("restore reads about 2 million records, not 1.8 billion", GREEN_M, 21).move_to([0, -3.2, 0])
        self.steps("Over time, compaction keeps only the latest value per account. "
                   "So a restore reads about two million records, not one point eight billion.", [
            (lambda: [FadeOut(cur), Transform(srows[1], srow(1, "acct-2", "30.00")),
                      *[crows[k].animate.set_opacity(0.3) for k in (0, 1, 2)], *[Create(s) for s in strikes]], 1.0),
            "keeps only the latest",
            (lambda: [glow(crows[3][0], GREEN_M, 1.03), glow(crows[4][0], GREEN_M, 1.03)], 0.9),
            "So a restore",
            (lambda: [FadeIn(two, shift=0.1 * UP)], 0.8),
        ])

        self.steps("The table lives on local disk, so reads are fast. Its changelog lives in Kafka, "
                   "so the table outlives the disk.", [
            (lambda: [glow(sbox, BLUE_M, 1.03)], 1.0),
            "Its changelog",
            (lambda: [glow(crows[3][0], TEAL_M, 1.03), glow(crows[4][0], TEAL_M, 1.03)], 1.0),
            "outlives",
            (lambda: [glow(inst, BLUE_M, 1.02)], 1.0),
        ])
        self.wait(0.6)
