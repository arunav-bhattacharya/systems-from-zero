from sfz import *

# "pay nine" blends into "paid nine"; hyphenated, Kokoro keeps the words apart
SAY.insert(0, (r"\bpay-981\b", "pay-nine-eight-one"))

C_C, R_C, I_C = BLUE_M, GOLD_M, PURPLE_M          # capture client, refund client, index
CX = -4.9                                          # clients' x
CY, RY = 2.0, -1.8                                 # capture and refund rows; the database and the index sit on them
SX, SW, SH = 1.9, 4.6, 1.2                         # stores' x, width, height
LOG_Y, TOP = -2.95, 3.15
WH = 1.3                                           # the log's box height
VAL_C = {"AUTHORIZED": GREY_B, "CAPTURED": C_C, "REFUNDED": R_C}


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def store(title, y, color):
    r = RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=color, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([SX, y, 0])
    t = T(title, 22, GREY_B).move_to([SX, y + 0.3, 0])
    return VGroup(r, t)


def value(v, y, color=None):
    k = M("pay-981", 24, WHITE)
    s = M(v, 24, color or VAL_C[v])
    g = VGroup(k, s).arrange(RIGHT, buff=0.4)
    return g.move_to([SX, y - 0.17, 0])


def client(name, sub, y, color):
    r = RoundedRectangle(corner_radius=0.14, width=2.6, height=1.0, stroke_color=color, stroke_width=3)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14), opacity=1).move_to([CX, y, 0])
    n = T(name, 28).move_to([CX, y + 0.2, 0])
    s = T(sub, 20, GREY_B).move_to([CX, y - 0.22, 0])
    return VGroup(r, n, s)


def note(s, y, color):
    return T(s, 22, color).move_to([CX, y - 0.82, 0])


def log_row(chips):
    return VGroup(*chips).arrange(RIGHT, buff=0.18).move_to([0, LOG_Y, 0])


def wire(a, b, color):
    return edge_arrow(a[0], b[0], color, buff=0.1)


def cross(a, b, color):
    """A client's arrow to the store on the other row: from its top or bottom edge to the store's left edge."""
    up = b.get_center()[1] > a.get_center()[1]
    s = a[0].get_edge_center(UP if up else DOWN) + 0.75 * RIGHT
    e = b[0].get_left() + (0.25 * DOWN if up else 0.25 * UP)
    return Arrow(s, e, buff=0.1, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12)


class DualWrites(Base):
    """stream-01: the lesson's dual-write race on pay-981 (capture and refund each write PostgreSQL, then the index;
    the table's t1 to t4 order leaves the index at CAPTURED), then the fix: the index follows the database's log."""

    def construct(self):
        self.title_card("Dual writes", "two systems, one truth")

        pg = store("PostgreSQL", CY, WHITE)
        ix = store("search index", RY, I_C)
        pv, iv = value("AUTHORIZED", CY), value("AUTHORIZED", RY)
        self.steps("A payment service keeps each payment in PostgreSQL. The support team searches a second copy of it, in a search index.", [
            (lambda: [FadeIn(pg), FadeIn(pv)], 0.9),
            "The support team",
            (lambda: [FadeIn(ix), FadeIn(iv)], 0.9),
        ])

        rule = chip("rule: update the database, then send the change to the index", GREY_B, 22).move_to([0, TOP, 0])
        self.steps("The service keeps that copy fresh the obvious way: update the database, then send the same change to the index. "
                   "That's a dual write.", [
            "update the database",
            (lambda: [FadeIn(rule, shift=0.15 * DOWN)], 0.9),
            "That's a dual write",
            (lambda: [glow(pg[0], YELLOW_M, 1.03), glow(ix[0], YELLOW_M, 1.03)], 1.0),
        ])

        cap = client("capture job", "sets CAPTURED", CY, C_C)
        ref = client("refund", "sets REFUNDED", RY, R_C)
        self.steps("Two requests for payment pay-981 arrive a millisecond apart. A capture job sets it to captured, and a refund sets it to refunded.", [
            "A capture job",
            (lambda: [FadeIn(cap, shift=0.2 * RIGHT)], 0.8),
            "and a refund",
            (lambda: [FadeIn(ref, shift=0.2 * RIGHT)], 0.8),
        ])

        log = [chip("database: CAPTURED", C_C, 20), chip("database: REFUNDED", R_C, 20),
               chip("index: REFUNDED", R_C, 20), chip("index: CAPTURED", RED_M, 20)]
        log_row(log)
        c_pg, r_ix = wire(cap, pg, C_C), wire(ref, ix, R_C)
        c_ix, r_pg = cross(cap, ix, C_C), cross(ref, pg, R_C)
        paused = note("paused", CY, RED_M)
        self.steps("The capture commits to the database first. Then its thread stalls for a few milliseconds, say in a garbage collection pause.", [
            (lambda: [GrowArrow(c_pg)], 0.6),
            (lambda: [travel(c_pg, C_C, 0.6)], 0.6),
            (lambda: [Transform(pv, value("CAPTURED", CY)), FadeIn(log[0], shift=0.15 * UP)], 0.7),
            "Then its thread",
            (lambda: [FadeOut(c_pg), cap[0].animate.set_stroke(GREY_D), cap[1].animate.set_color(GREY_C), FadeIn(paused)], 0.8),
        ])

        self.steps("The refund commits next, so the database says refunded. That's right: the refund came second.", [
            (lambda: [GrowArrow(r_pg)], 0.6),
            (lambda: [travel(r_pg, R_C, 0.6)], 0.6),
            (lambda: [Transform(pv, value("REFUNDED", CY)), FadeIn(log[1], shift=0.15 * UP)], 0.7),
            "That's right",
            (lambda: [Indicate(pv[1], color=GREEN_M)], 1.0),
        ])

        self.steps("The refund also updates the index, which now says refunded too.", [
            (lambda: [FadeOut(r_pg), GrowArrow(r_ix)], 0.6),
            (lambda: [travel(r_ix, R_C, 0.6)], 0.6),
            (lambda: [Transform(iv, value("REFUNDED", RY)), FadeIn(log[2], shift=0.15 * UP)], 0.7),
        ])

        self.steps("Then the capture wakes up and makes its second write. The index now says captured.", [
            (lambda: [FadeOut(r_ix), FadeOut(paused), cap[0].animate.set_stroke(C_C), cap[1].animate.set_color(WHITE)], 0.7),
            "and makes",
            (lambda: [GrowArrow(c_ix)], 0.6),
            (lambda: [travel(c_ix, C_C, 0.7)], 0.7),
            "The index now",
            (lambda: [Transform(iv, value("CAPTURED", RY, RED_M)), FadeIn(log[3], shift=0.15 * UP), ix[0].animate.set_stroke(RED_M)], 0.8),
        ])

        self.steps("Every call reported success. There's no error and no log line, and the index stays wrong until someone writes pay-981 again.", [
            (lambda: [FadeOut(c_ix), *[Indicate(c, color=GREEN_M, scale_factor=1.05) for c in log]], 1.2),
            "and the index stays wrong",
            (lambda: [Indicate(pv, color=R_C), Indicate(iv, color=RED_M)], 1.2),
        ])

        cause = chip("two writers, each picking its own order", RED_M, 22).move_to([0, TOP, 0])
        self.steps("The cause: two writers, each picking its own order, and neither store follows the other.", [
            (lambda: [ReplacementTransform(rule, cause)], 0.8),
            "two writers",
            (lambda: [glow(cap[0], C_C, 1.05), glow(ref[0], R_C, 1.05)], 1.0),
            "and neither store",
            (lambda: [glow(pg[0], WHITE, 1.03), glow(ix[0], RED_M, 1.03)], 1.0),
        ])

        # ---- one leader, one log --------------------------------------------------------------------------------
        wy = (CY + RY) / 2
        wal = RoundedRectangle(corner_radius=0.12, width=5.2, height=WH, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        wal.move_to([SX, wy, 0])
        wal_t = T("the database's log, in commit order", 20, GREY_B).move_to([SX, wy + 0.36, 0])
        to_wal = Arrow([SX, CY - SH / 2, 0], [SX, wy + WH / 2, 0], buff=0.08, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.25)
        self.steps("A database's own replicas never have this problem. One leader picks the order of writes, records it in a log, "
                   "and every copy applies the log in that order.", [
            (lambda: [FadeOut(VGroup(*log)), Transform(pv, value("AUTHORIZED", CY)), Transform(iv, value("AUTHORIZED", RY)),
                      ix[0].animate.set_stroke(I_C), cap.animate.set_opacity(0.35), ref.animate.set_opacity(0.35)], 1.0),
            "records it in a log",
            (lambda: [GrowArrow(to_wal), FadeIn(wal), FadeIn(wal_t)], 1.0),
            "and every copy",
            (lambda: [Indicate(wal_t, color=YELLOW_M)], 1.0),
        ])

        fix = chip("fix: write only the database; the index follows its log", GREEN_M, 22).move_to([0, TOP, 0])
        fol = Arrow([SX, wy - WH / 2, 0], [SX, RY + SH / 2, 0], buff=0.08, stroke_width=3, color=I_C, max_tip_length_to_length_ratio=0.25)
        fol_l = T("follower", 22, I_C).next_to(fol, RIGHT, buff=0.2)
        self.steps("So do the same here. The services write only to PostgreSQL. The index follows the database's log.", [
            "The services",
            (lambda: [ReplacementTransform(cause, fix), cap.animate.set_opacity(1), ref.animate.set_opacity(1)], 0.9),
            "The index follows",
            (lambda: [GrowArrow(fol), FadeIn(fol_l)], 0.9),
        ])

        e768 = chip("768  CAPTURED", C_C, 18)
        e769 = chip("769  REFUNDED", R_C, 18)
        VGroup(e768, e769).arrange(RIGHT, buff=0.25).move_to([SX, wy - 0.2, 0])
        waits = note("waits for the lock", RY, R_C)
        c_pg2, r_pg2 = wire(cap, pg, C_C), cross(ref, pg, R_C)
        self.steps("Run the race again. The capture locks the row, so the refund waits. "
                   "The log records the capture as commit 768, then the refund as 769.", [
            (lambda: [GrowArrow(c_pg2), GrowArrow(r_pg2)], 0.7),
            "The capture locks",
            (lambda: [travel(c_pg2, C_C, 0.6)], 0.6),
            (lambda: [Transform(pv, value("CAPTURED", CY))], 0.5),
            "so the refund waits",
            (lambda: [FadeIn(waits), Indicate(r_pg2, color=R_C)], 0.8),
            "The log records",
            (lambda: [FadeIn(e768, shift=0.15 * DOWN)], 0.7),
            "then the refund",
            (lambda: [FadeOut(waits), travel(r_pg2, R_C, 0.6)], 0.6),
            (lambda: [Transform(pv, value("REFUNDED", CY))], 0.5),
            (lambda: [FadeIn(e769, shift=0.15 * DOWN)], 0.6),
        ])

        bm = T("bookmark: 768", 20, GREY_B).next_to(fol, LEFT, buff=0.2)
        bm2 = T("bookmark: 769", 20, GREY_B).move_to(bm, aligned_edge=RIGHT)
        self.steps("The follower applies the log in order, captured then refunded, and remembers how far it got. Both stores end at refunded.", [
            (lambda: [FadeOut(c_pg2), FadeOut(r_pg2), Indicate(e768, color=C_C, scale_factor=1.05), travel(fol, C_C, 0.7)], 0.8),
            (lambda: [Transform(iv, value("CAPTURED", RY)), FadeIn(bm)], 0.6),
            "then refunded",
            (lambda: [Indicate(e769, color=R_C, scale_factor=1.05), travel(fol, R_C, 0.7)], 0.8),
            (lambda: [Transform(iv, value("REFUNDED", RY)), Transform(bm, bm2)], 0.6),
            "Both stores",
            (lambda: [Indicate(pv[1], color=GREEN_M), Indicate(iv[1], color=GREEN_M)], 1.0),
        ])

        self.steps("The price is lag: the index trails the database by a few milliseconds. "
                   "But it can't disagree about the order, because it no longer picks one.", [
            (lambda: [Indicate(fol_l, color=I_C)], 1.0),
            "But it can't",
            (lambda: [Indicate(e768, color=C_C, scale_factor=1.05), Indicate(e769, color=R_C, scale_factor=1.05)], 1.2),
        ])
        self.wait(0.6)
