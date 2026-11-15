from sfz import *

SAY.insert(0, (r"\bFOR UPDATE\b", "for update"))
SAY.insert(0, (r"\bSERIALIZABLE\b", "serializable"))

def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def via(points, color=YELLOW_M, run_time=0.9):
    """A dot that runs along a polyline and stays invisible until its turn."""
    pts = [np.array(p, dtype=float) for p in points]
    path = VMobject().set_points_as_corners(pts)
    d = Dot(radius=0.08, color=color).move_to(pts[0]).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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



AX, BX_ = -3.6, 3.6                           # the two bookers' lanes
TY = [0.45, -0.25, -0.95, -1.65, -2.35]       # time slots, top to bottom
AXY, BAR1, BAR2 = 1.95, 2.4, 2.92             # timeline axis and the two bar rows


def hx(h):
    """x of a clock time on room 4's timeline, 09:00 to 15:00."""
    return -5.0 + (h - 9) * 1.75


def bar(h0, h1, label, color, y=BAR1, at=None):
    """A booking on the timeline; `at` puts its label at that clock time instead of the middle."""
    r = RoundedRectangle(corner_radius=0.06, width=(h1 - h0) * 1.75 - 0.04, height=0.42, stroke_color=color, stroke_width=2.5)
    r.set_fill(fill(color, 0.3), 1).move_to([(hx(h0) + hx(h1)) / 2, y, 0])
    return VGroup(r, T(label, 16).move_to([hx(at) if at else r.get_center()[0], y, 0]))


def step(s, lane, k, color=GREY_B, mono=True):
    if mono:
        m = chip(s, color, 16, mono=True)
    else:
        m = T(s, 18, color)
    return m.move_to([AX if lane == "A" else BX_, TY[k], 0])


def wait_line(lane, k0, k1, color):
    x = AX if lane == "A" else BX_
    ln = DashedLine([x, TY[k0] - 0.3, 0], [x, TY[k1] + 0.3, 0], dash_length=0.1, stroke_width=3, color=color)
    return VGroup(ln, T("waits", 17, color).next_to(ln, RIGHT, buff=0.12))


class Phantoms(Base):
    """txn-03, section 1 (with section 2's fixes and section 4's SERIALIZABLE): two bookings of room 4 each check for an
    overlap with FOR UPDATE, find no rows, lock nothing, and both insert; 12:30 to 13:00 is booked twice. Locking room 4's
    row in rooms makes the second booker wait and see the first booking. An exclusion constraint fails the second insert
    with 23P01, and SERIALIZABLE fails the second commit with 40001."""

    def construct(self):
        self.title_card("Phantoms", "when the row you need to lock doesn't exist yet")

        axis = Line([hx(9), AXY, 0], [hx(15), AXY, 0], stroke_width=2.5, color=GREY_B)
        ticks = VGroup(*[VGroup(Line([hx(h), AXY - 0.08, 0], [hx(h), AXY + 0.08, 0], stroke_width=2, color=GREY_B),
                                T(f"{h:02d}:00", 16, GREY_C).move_to([hx(h), AXY - 0.3, 0])) for h in range(9, 16)])
        rlab = T("room 4", 20, GREY_A).move_to([-5.85, BAR1, 0])
        old = VGroup(bar(9, 10, "standup", GREY_B), bar(14, 15, "card ops", GREY_B))
        free = Rectangle(width=hx(13) - hx(12), height=0.42, stroke_width=0).set_fill(GREEN_M, 0.18).move_to([(hx(12) + hx(13)) / 2, BAR1, 0])
        flab = T("free", 17, GREEN_M).move_to(free)
        ta = T("A: settlement review, 12:00 to 13:00", 19, BLUE_M).move_to([AX, 1.1, 0])
        tb = T("B: fraud sync, 12:30 to 13:30", 19, PURPLE_M).move_to([BX_, 1.1, 0])
        self.steps("Room 4 is free from twelve to one. Two people book it at the same moment: a settlement review "
                   "from twelve to one, and a fraud sync from twelve thirty to one thirty.", [
            (lambda: [Create(axis), FadeIn(ticks), FadeIn(rlab), FadeIn(old)], 1.0),
            "is free",
            (lambda: [FadeIn(free), FadeIn(flab)], 0.6),
            "a settlement review",
            (lambda: [FadeIn(ta, shift=0.1 * DOWN)], 0.6),
            "and a fraud sync",
            (lambda: [FadeIn(tb, shift=0.1 * DOWN)], 0.6),
        ])

        a0, b0 = step("check overlap … FOR UPDATE", "A", 0), step("check overlap … FOR UPDATE", "B", 0)
        self.steps("Each app checks first: does any booking of room 4 overlap mine? It even adds FOR UPDATE, "
                   "the row lock that stopped lost updates.", [
            (lambda: [FadeIn(a0), FadeIn(b0)], 0.7),
            "It even adds",
            (lambda: [glow(a0[0], YELLOW_M, 1.05), glow(b0[0], YELLOW_M, 1.05)], 0.9),
        ])

        a1, b1 = step("0 rows, so 0 locks", "A", 1, GREY_B, False), step("0 rows, so 0 locks", "B", 1, GREY_B, False)
        self.steps("Both checks find no rows. A row lock is a mark on a row that exists, "
                   "so they lock nothing, and neither one waits.", [
            (lambda: [glow(free, GREEN_M, 1.05)], 0.6),
            (lambda: [FadeIn(a1), FadeIn(b1)], 0.6),
            "so they lock nothing",
            (lambda: [a1.animate.set_color(RED_M), b1.animate.set_color(RED_M)], 0.6),
        ])

        a2, b2 = step("INSERT 12:00 to 13:00", "A", 2, BLUE_M), step("INSERT 12:30 to 13:30", "B", 2, PURPLE_M)
        a3, b3 = step("COMMIT", "A", 3, BLUE_M), step("COMMIT", "B", 3, PURPLE_M)
        ba = bar(12, 13, "A", BLUE_M, at=12.25)
        bb = bar(12.5, 13.5, "B", PURPLE_M, BAR2, at=13.25)
        clash = Rectangle(width=hx(13) - hx(12.5), height=1.0, stroke_color=RED_M, stroke_width=3).set_fill(RED_M, 0.25)
        clash.move_to([(hx(12.5) + hx(13)) / 2, (BAR1 + BAR2) / 2, 0])
        twice = T("booked twice", 19, RED_M).move_to([clash.get_center()[0], BAR2 + 0.47, 0])
        self.steps("Both insert, and both commit. Twelve thirty to one is now booked twice.", [
            (lambda: [FadeIn(a2), FadeIn(b2)], 0.5),
            (lambda: [FadeIn(a3), FadeIn(b3), FadeOut(free), FadeOut(flab), FadeIn(ba, shift=0.2 * UP), FadeIn(bb, shift=0.2 * UP)], 0.8),
            "Twelve thirty",
            (lambda: [FadeIn(clash), FadeIn(twice)], 0.7),
        ])

        ph = T("phantom: a row that matches the search, written after it ran", 19, RED_M).move_to([0, -3.05, 0])
        self.steps("Each new booking is a phantom to the other: a row that matches its search but didn't exist when it "
                   "searched. A row lock can't protect an absence.", [
            (lambda: [FadeIn(ph)], 0.7),
            (lambda: [glow(bb[0], PURPLE_M, 1.08)], 0.8),
            "A row lock",
            (lambda: [glow(a0[0], RED_M, 1.05), glow(b0[0], RED_M, 1.05)], 0.9),
        ])

        lanes1 = VGroup(a0, a1, a2, a3, b0, b1, b2, b3, ph, clash, twice, ba, bb)
        room = box("rooms: room 4", WHITE, w=2.6, h=0.62, size=19).move_to([0, TY[0], 0])
        c0 = step("lock room 4 FOR UPDATE", "A", 0, BLUE_M)
        d0 = step("lock room 4 FOR UPDATE", "B", 0, PURPLE_M)
        lk = T("locked by A", 17, BLUE_M).next_to(room, DOWN, buff=0.12)
        self.steps("First fix: give the conflict a row. Each booking first locks room 4's own row in the rooms table, "
                   "which always exists.", [
            (lambda: [FadeOut(lanes1), FadeIn(free), FadeIn(flab)], 0.7),
            "Each booking",
            (lambda: [FadeIn(room), FadeIn(c0), FadeIn(d0)], 0.7),
            "which always exists",
            (lambda: [room[0].animate.set_stroke(BLUE_M), FadeIn(lk)], 0.6),
        ])

        w = wait_line("B", 0, 3, PURPLE_M)
        c1 = step("check: 0 rows", "A", 1, GREY_B)
        c2 = step("INSERT; COMMIT", "A", 2, BLUE_M)
        d3 = step("check: 1 row overlaps", "B", 3, PURPLE_M)
        d4 = step("refuse: room taken", "B", 4, GREEN_M)
        ba2 = bar(12, 13, "A", BLUE_M)
        self.steps("The second booker waits there. When the first commits, the second one's check runs and sees "
                   "the new booking, so it refuses.", [
            (lambda: [Create(w[0]), FadeIn(w[1])], 0.8),
            (lambda: [FadeIn(c1)], 0.4),
            "When the first",
            (lambda: [FadeIn(c2), FadeOut(free), FadeOut(flab), FadeIn(ba2, shift=0.2 * UP)], 0.6),
            (lambda: [room[0].animate.set_stroke(WHITE), FadeOut(lk)], 0.4),
            "the second one's",
            (lambda: [FadeIn(d3)], 0.5),
            "so it refuses",
            (lambda: [FadeIn(d4)], 0.5),
        ])

        mat = T("materializing the conflict: every writer must remember the lock", 19, GREY_A).move_to([0, -3.05, 0])
        self.steps("This is materializing the conflict. It holds only if every code path remembers to lock the room.", [
            (lambda: [FadeIn(mat)], 0.7),
            "every code path",
            (lambda: [glow(room[0], YELLOW_M, 1.05)], 0.9),
        ])

        lanes2 = VGroup(c0, c1, c2, d0, d3, d4, w, mat, room, ba2)
        ex = chip("EXCLUDE USING gist (room_id WITH =, during WITH &&)", GREEN_M, 17, mono=True).move_to([0, -3.05, 0])
        e0 = step("INSERT 12:00 to 13:00", "A", 0, BLUE_M)
        f0 = step("INSERT 12:30 to 13:30", "B", 0, PURPLE_M)
        self.steps("Better: state the rule and let the database enforce it. An exclusion constraint says no two bookings "
                   "of one room may overlap.", [
            (lambda: [FadeOut(lanes2), FadeIn(free), FadeIn(flab)], 0.7),
            "An exclusion",
            (lambda: [FadeIn(ex, shift=0.1 * UP)], 0.8),
        ])

        w2 = wait_line("B", 0, 2, PURPLE_M)
        e1 = step("COMMIT", "A", 1, BLUE_M)
        f2 = step("ERROR 23P01: overlaps", "B", 2, RED_M)
        ba3 = bar(12, 13, "A", BLUE_M)
        self.steps("Its check looks at every row in the index, committed or not. The second insert finds the first, "
                   "waits for it, and fails the moment it commits.", [
            (lambda: [FadeIn(e0), FadeIn(f0)], 0.6),
            "The second insert",
            (lambda: [glow(f0[0], PURPLE_M, 1.05)], 0.6),
            "waits for it",
            (lambda: [Create(w2[0]), FadeIn(w2[1])], 0.7),
            "and fails",
            (lambda: [FadeIn(e1), FadeOut(free), FadeOut(flab), FadeIn(ba3, shift=0.2 * UP)], 0.5),
            (lambda: [FadeIn(f2)], 0.5),
        ])

        lanes3 = VGroup(e0, e1, f0, f2, w2)
        ser = chip("BEGIN ISOLATION LEVEL SERIALIZABLE", GOLD_M, 17, mono=True).move_to([0, -3.05, 0])
        s0, t0 = step("check: 0 rows", "A", 0), step("check: 0 rows", "B", 0)
        s1, t1 = step("INSERT; COMMIT", "A", 1, BLUE_M), step("INSERT", "B", 1, PURPLE_M)
        t2 = step("COMMIT fails: 40001", "B", 2, RED_M)
        t3 = step("retry: 1 row, refuse", "B", 3, GREEN_M)
        self.steps("When the rule is arithmetic across rows, such as a sum of refunds, run at SERIALIZABLE. "
                   "PostgreSQL notes what each check read, fails one commit, and the retry sees the booking.", [
            (lambda: [FadeOut(lanes3), Transform(ex, ser)], 0.8),
            "PostgreSQL notes",
            (lambda: [FadeIn(s0), FadeIn(t0)], 0.5),
            (lambda: [FadeIn(s1), FadeIn(t1)], 0.5),
            "fails one commit",
            (lambda: [FadeIn(t2)], 0.5),
            "and the retry",
            (lambda: [FadeIn(t3)], 0.5),
        ])

        self.steps("A lock needs a row. When the conflict is about a row that doesn't exist yet, lock a row that stands for it, "
                   "or let a constraint or SERIALIZABLE catch it.", [
            (lambda: [glow(ba3[0], BLUE_M, 1.08)], 0.8),
            "or let a constraint",
            (lambda: [glow(ex[0], GOLD_M, 1.04), glow(t3[0], GREEN_M, 1.05)], 0.9),
        ])
        self.wait(0.6)
