from sfz import *

NW, NH = 2.7, 1.75                                    # leader and follower boxes
LP = np.array([-5.15, 0.1, 0])                        # leader
FP = {1: np.array([4.9, 1.35, 0]), 2: np.array([4.9, -1.25, 0])}
CP, CW, CH = np.array([-0.65, 0.1, 0]), 4.2, 1.75     # the log entry card
TX, TY = [-4.3, 0.0, 4.3], 3.15                       # the three formats, across the top
STY = -2.95                                           # status line


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def node(c, name, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to(c)
    slot = RoundedRectangle(corner_radius=0.08, width=NW - 0.4, height=0.5, stroke_color=GREY_D, stroke_width=1.5)
    slot.set_fill(BLACK, 1).move_to(c + 0.42 * DOWN)
    return VGroup(r, T(name, 24).move_to(c + 0.5 * UP), ver(c, "PostgreSQL 17"), slot, val(c, "id 42  fee 0.00", GREY_B))


def ver(c, s, color=GREY_B):
    return T(s, 18, color).move_to(c + 0.12 * UP)


def val(c, s, color=WHITE):
    return M(s, 18, color).move_to(c + 0.42 * DOWN)


def card_lines(lines, color=WHITE):
    g = VGroup(*[M(s, 17, color) for s in lines]).arrange(DOWN, buff=0.17)
    return g.move_to(CP)


def fmt(i, s, color=GREY_B):
    return T(s, 22, color).move_to([TX[i], TY, 0])


def verdict(i, s, color, ok):
    t = T(s, 19, color)
    k = tick(ok, 0.13)
    g = VGroup(k, t).arrange(RIGHT, buff=0.14)
    return g.move_to([TX[i], TY - 0.5, 0])


def status(s, color=GREY_B):
    return T(s, 22, color).move_to([0, STY, 0])


class ReplicationLogs(Base):
    """repl-02, sections 0 to 2: the leader logs UPDATE ... SET fee = 1 + random() and each follower draws its own
    number; the physical WAL ships bytes at a page and offset, exact but readable only by the same major version
    (a follower upgraded to 18 first can't replay 17's records); a logical row entry ships the result,
    "row 42 now has fee 1.37", which a follower on any version stores, and stores again harmlessly."""

    def construct(self):
        self.title_card("Replication logs", "what one entry in the log should say")

        ld = node(LP, "leader")
        fs = {i: node(FP[i], f"follower {i}") for i in FP}
        card = RoundedRectangle(corner_radius=0.12, width=CW, height=CH, stroke_color=GREY_B, stroke_width=2.5)
        card.set_fill(BLACK, 1).move_to(CP)
        clab = T("one log entry", 18, GREY_B).move_to(CP + (CH / 2 + 0.25) * UP)
        q = T("?", 44, GREY_B).move_to(CP)
        a0 = Arrow([LP[0] + NW / 2 + 0.08, LP[1], 0], [CP[0] - CW / 2 - 0.08, CP[1], 0], buff=0, stroke_width=3,
                   color=GREY_B, max_tip_length_to_length_ratio=0.2)
        af = {i: edge_arrow(card, fs[i][0], GREY_B, buff=0.1) for i in FP}
        self.steps("A leader copies every change to two followers through a log. Payment 42 needs a new fee. "
                   "What should the log entry say?", [
            (lambda: [FadeIn(ld, scale=0.95)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(fs[i], scale=0.95) for i in FP], lag_ratio=0.3)], 0.8),
            "through a log",
            (lambda: [FadeIn(card), FadeIn(clab), GrowArrow(a0), *[GrowArrow(af[i]) for i in FP]], 0.8),
            "Payment 42",
            (lambda: [glow(ld[3], YELLOW_M, 1.05), glow(fs[1][3], YELLOW_M, 1.05), glow(fs[2][3], YELLOW_M, 1.05)], 0.9),
            "What should",
            (lambda: [FadeIn(q, scale=0.8)], 0.5),
        ])

        f1 = fmt(0, "1. the statement", WHITE)
        stmt = card_lines(["UPDATE payments", "SET fee = 1 + random()", "WHERE id = 42"])
        self.steps("The simplest entry is the statement itself: update payment 42, and set its fee to one plus a random number.", [
            (lambda: [FadeIn(f1, shift=0.1 * DOWN)], 0.6),
            (lambda: [FadeOut(q), card.animate.set_stroke(WHITE)], 0.4),
            "update payment",
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * RIGHT) for l in stmt], lag_ratio=0.35)], 1.4),
        ])

        self.steps("The leader runs it. Its random number is 0.37, so the fee is 1.37.", [
            (lambda: [Transform(ld[4], val(LP, "1 + random()", YELLOW_M)), glow(ld[0], YELLOW_M)], 0.8),
            "so the fee",
            (lambda: [Transform(ld[4], val(LP, "id 42  fee 1.37", WHITE))], 0.7),
        ])

        self.steps("Each follower receives the same statement, and runs it again, later, with its own random generator.", [
            (lambda: [travel(a0, YELLOW_M, 0.6)], 0.6),
            (lambda: [*[travel(af[i], YELLOW_M, 0.8) for i in FP]], 0.8),
            "and runs it again",
            (lambda: [*[Transform(fs[i][4], val(FP[i], "1 + random()", YELLOW_M)) for i in FP],
                      *[glow(fs[i][0], YELLOW_M) for i in FP]], 0.9),
        ])

        st1 = status("three copies, three different fees", RED_M)
        v1 = verdict(0, "the fees differ", RED_M, False)
        self.steps("Follower one gets 1.82. Follower two gets 1.05. Three copies of the same payment now disagree.", [
            (lambda: [Transform(fs[1][4], val(FP[1], "id 42  fee 1.82", RED_M))], 0.6),
            "Follower two",
            (lambda: [Transform(fs[2][4], val(FP[2], "id 42  fee 1.05", RED_M))], 0.6),
            "Three copies",
            (lambda: [FadeIn(st1, shift=0.1 * UP), fs[1][0].animate.set_stroke(RED_M), fs[2][0].animate.set_stroke(RED_M)], 0.7),
            (lambda: [FadeIn(v1, shift=0.1 * DOWN)], 0.5),
        ])

        st1b = status("now(), new ids, row order: the same problem", RED_M)
        self.steps("The function now, which reads each server's own clock, breaks the same way. Anything that depends on where or when "
                   "a statement runs can come out different.", [
            (lambda: [Transform(st1, st1b)], 0.8),
            "Anything that",
            (lambda: [glow(card, RED_M, 1.03)], 1.0),
        ])

        f2 = fmt(1, "2. the WAL bytes", WHITE)
        wal = card_lines(["page 7, offset 312", "new bytes:", "ec 51 b8 1e 85 eb f5 3f"])
        self.steps("PostgreSQL ships something else: its write-ahead log, the record it already keeps of which bytes "
                   "changed on which 8 kilobyte page of the table's file.", [
            (lambda: [FadeOut(st1), f1.animate.set_color(GREY_B), FadeIn(f2, shift=0.1 * DOWN),
                      *[Transform(fs[i][4], val(FP[i], "id 42  fee 0.00", GREY_B)) for i in FP],
                      *[fs[i][0].animate.set_stroke(WHITE) for i in FP]], 0.9),
            "which bytes",
            (lambda: [FadeOut(stmt), FadeIn(wal[0]), FadeIn(wal[1]), FadeIn(wal[2])], 0.9),
            "on which 8 kilobyte",
            (lambda: [Indicate(wal[0], color=YELLOW_M, scale_factor=1.1)], 0.9),
        ])

        st2 = status("nothing to compute: an exact copy", GREEN_M)
        self.steps("There is nothing left to compute. Each follower writes the same bytes at the same place, "
                   "and all three show 1.37.", [
            (lambda: [travel(a0, TEAL_M, 0.6)], 0.6),
            (lambda: [*[travel(af[i], TEAL_M, 0.8) for i in FP]], 0.8),
            "and all three",
            (lambda: [*[Transform(fs[i][4], val(FP[i], "id 42  fee 1.37", GREEN_M)) for i in FP],
                      Transform(ld[4], val(LP, "id 42  fee 1.37", GREEN_M)), FadeIn(st2, shift=0.1 * UP)], 0.8),
        ])

        st3 = status("PostgreSQL 18 can't replay 17's WAL", GOLD_M)
        self.steps("But those bytes are in one major version's private format. Upgrade follower two to version 18 first, "
                   "and it can't replay the records that 17 writes.", [
            (lambda: [glow(wal[2], GOLD_M, 1.05)], 0.8),
            "Upgrade follower two",
            (lambda: [FadeOut(st2), Transform(fs[2][2], ver(FP[2], "PostgreSQL 18", GOLD_M)), glow(fs[2][0], GOLD_M),
                      *[Transform(fs[i][4], val(FP[i], "id 42  fee 0.00", GREY_B)) for i in FP],
                      Transform(ld[4], val(LP, "id 42  fee 0.00", GREY_B))], 0.9),
            "and it can't",
            (lambda: [travel(a0, TEAL_M, 0.5)], 0.5),
            (lambda: [travel(af[1], TEAL_M, 0.7), travel(af[2], TEAL_M, 0.7)], 0.7),
            (lambda: [Transform(fs[1][4], val(FP[1], "id 42  fee 1.37", GREEN_M)),
                      Transform(ld[4], val(LP, "id 42  fee 1.37", WHITE)),
                      Transform(fs[2][4], val(FP[2], "can't replay", RED_M)), fs[2][0].animate.set_stroke(RED_M),
                      FadeIn(st3, shift=0.1 * UP)], 0.7),
        ])

        v2 = verdict(1, "one version only", GOLD_M, False)
        self.steps("So you can't upgrade a follower first and fail over to it. Every server upgrades together, "
                   "with a short outage.", [
            (lambda: [FadeIn(v2, shift=0.1 * DOWN)], 0.6),
            "Every server",
            (lambda: [glow(ld[0], GOLD_M), glow(fs[1][0], GOLD_M), glow(fs[2][0], GOLD_M)], 1.0),
        ])

        f3 = fmt(2, "3. the row values", WHITE)
        row = card_lines(["UPDATE payments", "row id 42", "fee = 1.37"])
        self.steps("A logical log sits between the two. Each entry names one row and the values it now holds: "
                   "row 42 now has fee 1.37.", [
            (lambda: [FadeOut(st3), f2.animate.set_color(GREY_B), FadeIn(f3, shift=0.1 * DOWN),
                      fs[2][0].animate.set_stroke(WHITE), Transform(fs[2][4], val(FP[2], "id 42  fee 0.00", GREY_B)),
                      Transform(fs[1][4], val(FP[1], "id 42  fee 0.00", GREY_B))], 0.9),
            "Each entry",
            (lambda: [FadeOut(wal), FadeIn(row[0]), FadeIn(row[1])], 0.8),
            "row 42 now",
            (lambda: [FadeIn(row[2], shift=0.1 * RIGHT), card.animate.set_stroke(GREEN_M)], 0.7),
        ])

        st4 = status("the leader computed it once; the followers only store it", GREEN_M)
        self.steps("The leader computed the value once. A follower on any version, even another kind of database, "
                   "only has to store it.", [
            (lambda: [glow(ld[0], GREEN_M)], 0.7),
            "A follower",
            (lambda: [travel(a0, GREEN_M, 0.5)], 0.5),
            (lambda: [*[travel(af[i], GREEN_M, 0.8) for i in FP]], 0.8),
            (lambda: [*[Transform(fs[i][4], val(FP[i], "id 42  fee 1.37", GREEN_M)) for i in FP],
                      FadeIn(st4, shift=0.1 * UP)], 0.7),
        ])

        v3 = verdict(2, "any version", GREEN_M, True)
        st5 = status("sent twice, still 1.37", GREEN_M)
        self.steps("If a reconnect sends the same entry twice, the row still says 1.37.", [
            (lambda: [FadeIn(v3, shift=0.1 * DOWN)], 0.5),
            "sends the same entry",
            (lambda: [travel(af[1], GREEN_M, 0.7)], 0.7),
            (lambda: [glow(fs[1][3], GREEN_M, 1.06), Transform(st4, st5)], 0.8),
        ])

        self.steps("Log the result the leader computed, written as rows. Every follower stores the same fee, "
                   "whatever version it runs.", [
            (lambda: [glow(card, GREEN_M, 1.03)], 0.9),
            "Every follower",
            (lambda: [*[glow(fs[i][0], GREEN_M) for i in FP], glow(ld[0], GREEN_M)], 1.0),
        ])
        self.wait(0.6)
