from sfz import *

# Clock times are said the way people say them; captions keep "12:00".
SAY.insert(0, (r"\b11:58\b", "eleven fifty-eight"))
SAY.insert(0, (r"\b12:00\b", "twelve"))
SAY.insert(0, (r"\b12:30\b", "twelve thirty"))
SAY.insert(0, (r"\b13:00\b", "one"))
SAY.insert(0, (r"\b13:30\b", "one thirty"))
SAY.insert(0, (r"\b23P01\b", "two three P zero one"))
SAY.insert(0, (r"\bFOR UPDATE\b", "for update"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
AXIS_Y = 1.95                      # room 4's day, 09:00 to 15:00
X0, PER_H = -5.4, 1.8
TOP_Y, LOW_Y = 2.95, 2.45          # booking bars: upper and lower track
AX, BX = -3.7, 3.7                 # the two teams' lanes
LANE_Y = 1.05
SLOT = [0.45, -0.15, -0.75, -1.35, -1.95]
CAP_Y, BAR_Y = -3.25, -2.8


def hx(h):
    return X0 + (h - 9) * PER_H


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

    def steps(self, text, items, after=0.3):
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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def day_axis():
    ax = Line([hx(9), AXIS_Y, 0], [hx(15), AXIS_Y, 0], stroke_width=2, color=GREY_B)
    ticks = VGroup(*[Line([hx(h), AXIS_Y - 0.07, 0], [hx(h), AXIS_Y + 0.07, 0], stroke_width=2, color=GREY_B) for h in range(9, 16)])
    labs = VGroup(*[T(f"{h:02d}:00", 19, GREY_B).move_to([hx(h), AXIS_Y - 0.27, 0]) for h in range(9, 16)])
    title = T("room 4", 24).move_to([hx(9) + 0.5, 3.35, 0])
    return VGroup(ax, ticks, labs, title)


def bar(h0, h1, y, label, color, size=17):
    r = RoundedRectangle(corner_radius=0.08, width=(h1 - h0) * PER_H, height=0.4, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.35), 1).move_to([(hx(h0) + hx(h1)) / 2, y, 0])
    t = fit(T(label, size), r.width - 0.15).move_to(r).set_z_index(4)
    return VGroup(r, t)


def scan(h0, h1, color):
    r = Rectangle(width=(h1 - h0) * PER_H, height=1.15, stroke_color=color, stroke_width=2).set_fill(color, 0.12)
    return r.move_to([(hx(h0) + hx(h1)) / 2, (TOP_Y + LOW_Y) / 2 + 0.05, 0])


def lane_title(s, x, color):
    return T(s, 24, color).move_to([x, LANE_Y, 0])


def step(s, x, k, color=GREY_B, size=19):
    t = M(s, size)
    r = RoundedRectangle(corner_radius=0.08, width=max(3.6, t.width + 0.4), height=0.46, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.18), 1)
    return VGroup(r, t.move_to(r)).move_to([x, SLOT[k], 0])


def padlock(color, at, s=1.0):
    body = RoundedRectangle(corner_radius=0.06, width=0.46, height=0.36, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.5), 1)
    shackle = Arc(radius=0.15, start_angle=0, angle=PI, stroke_color=color, stroke_width=4)
    shackle.next_to(body, UP, buff=0)
    legs = VGroup(Line(shackle.get_start(), shackle.get_start() + 0.04 * DOWN), Line(shackle.get_end(), shackle.get_end() + 0.04 * DOWN)).set_stroke(color, 4)
    return VGroup(shackle, legs, body).scale(s).move_to(at)


def guard(color):
    head = Circle(radius=0.17, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.4), 1)
    cap = Polygon([-0.22, 0, 0], [0.22, 0, 0], [0.14, 0.12, 0], [-0.14, 0.12, 0], stroke_width=0).set_fill(color, 1)
    cap.next_to(head, UP, buff=-0.06)
    body = Arc(radius=0.3, start_angle=0, angle=PI, stroke_color=color, stroke_width=3)
    body.next_to(head, DOWN, buff=0.05)
    base = Line(body.get_start(), body.get_end(), stroke_width=3, color=color)
    return VGroup(head, cap, body, base)


class Phantoms(Base):
    """txn-03, section 1. Room 4: two teams book 12:00-13:00 and 12:30-13:30 at 11:58. Each checks for overlapping
    bookings with FOR UPDATE, finds 0 rows, locks nothing, inserts and commits: 12:30-13:00 booked twice. The row lock
    as a literal guard with nothing to stand by. The phantom; Repeatable Read doesn't help; the same shape elsewhere.
    The guardrail from section 2: lock room 4's own row first, or the exclusion constraint (23P01). Moral and a check
    (a unique username)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def add_step(self, key, *args, **kw):
        m = step(*args, **kw)
        self.st[key] = m
        return [FadeIn(m, shift=0.1 * DOWN)]

    def clear_steps(self):
        olds = list(self.st.values())
        self.st = {}
        return [FadeOut(m) for m in olds]

    def construct(self):
        self.capm = None
        self.st = {}
        self.title_card("Booked twice", "when the row you need to lock doesn't exist yet")

        # ---------------- scene 1: the question ----------------
        door = RoundedRectangle(corner_radius=0.1, width=2.2, height=3.2, stroke_color=WHITE, stroke_width=3).set_fill("#101010", 1)
        door.move_to([0, 0.3, 0])
        knob = Dot(door.get_center() + [0.75, -0.1, 0], radius=0.07, color=GREY_B)
        plate = T("room 4", 24).move_to(door.get_center() + [0, 1.1, 0])
        self.steps("Picture the office of the company behind a coffee-shop payments app. It has one small meeting room, room 4.", [
            "one small",
            (lambda: [FadeIn(VGroup(door, knob, plate), shift=0.2 * UP)], 0.8),
        ])
        ta0 = VGroup(T("settlement review", 24, BLUE_M), M("12:00-13:00", 22, BLUE_M)).arrange(DOWN, buff=0.15).move_to([-4.3, 1.2, 0])
        tb0 = VGroup(T("card ops", 24, PURPLE_M), M("12:30-13:30", 22, PURPLE_M)).arrange(DOWN, buff=0.15).move_to([4.3, 1.2, 0])
        clock = M("11:58", 30, GREY_B).move_to([0, 2.65, 0])
        self.steps("At 11:58, two teams open the booking app. One books the room from 12:00 to 13:00. The other, from 12:30 to 13:30.", [
            (lambda: [FadeIn(clock)], 0.5),
            "One books",
            (lambda: [FadeIn(ta0, shift=0.2 * RIGHT)], 0.6),
            "The other",
            (lambda: [FadeIn(tb0, shift=0.2 * LEFT)], 0.6),
        ])
        okA = chip("Booked", GREEN_M, 24).move_to([-4.3, -0.2, 0])
        okB = chip("Booked", GREEN_M, 24).move_to([4.3, -0.2, 0])
        gA = guard(BLUE_M).move_to([-1.75, -1.0, 0])
        gB = guard(PURPLE_M).move_to([1.75, -1.0, 0])
        self.steps("Both see a free room. Both get Booked. And at 12:30, both teams are at the door.", [
            "Both get",
            (lambda: [FadeIn(okA, scale=0.8), FadeIn(okB, scale=0.8)], 0.6),
            "And at 12:30",
            (lambda: [Transform(clock, M("12:30", 30, YELLOW_M).move_to(clock)), FadeIn(gA, shift=0.6 * RIGHT), FadeIn(gB, shift=0.6 * LEFT)], 0.8),
        ])
        q = T("how did this get through?", 28, YELLOW_M).move_to([0, -2.6, 0])
        self.steps("The app checked before it booked. It even locked what it found, the fix that stopped the lost update. "
                   "So how did this get through?", [
            "So how",
            (lambda: [FadeIn(q)], 0.6),
        ])

        # ---------------- scene 2: the room as rows ----------------
        axis = day_axis()
        risk = bar(9, 10, LOW_Y, "risk team", GREY_B)
        self.steps("Let's look at the room the way the database does. Each booking is a row in a table, with the room and a time range. "
                   "Room 4 has one booking this morning: the risk team, nine to ten.", [
            (lambda: [FadeOut(VGroup(door, knob, plate, ta0, tb0, okA, okB, gA, gB, q, clock))], 0.7),
            "Each booking",
            (lambda: [FadeIn(axis)], 0.8),
            "the risk team",
            (lambda: [FadeIn(risk, shift=0.1 * DOWN)], 0.6),
        ])
        chk = VGroup(M("SELECT booking_id FROM room_bookings", 20), M("WHERE room_id = 4 AND during && :my_slot", 20),
                     M("FOR UPDATE;", 20, YELLOW_M)).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        chk_b = RoundedRectangle(corner_radius=0.12, width=chk.width + 0.6, height=chk.height + 0.5, stroke_color=GREY_B,
                                 stroke_width=2).set_fill("#0c0c0c", 1)
        chk_g = VGroup(chk_b, chk.move_to(chk_b)).move_to([0, -0.3, 0])
        chk_t = T("the check, before every booking", 20, GREY_B).next_to(chk_g, UP, buff=0.18)
        lock_demo = padlock(YELLOW_M, [chk_b.get_right()[0] + 0.5, chk[2].get_center()[1], 0], 0.8)
        self.steps("Before it books, the app asks: is there any booking of room 4 that overlaps my slot? "
                   "And it adds FOR UPDATE, which puts a row lock on every row the question finds.", [
            "the app asks",
            (lambda: [FadeIn(chk_b), FadeIn(chk_t), FadeIn(chk[0]), FadeIn(chk[1])], 0.6),
            "And it adds",
            (lambda: [FadeIn(chk[2])], 0.5),
            "a row lock",
            (lambda: [FadeIn(lock_demo, scale=0.6)], 0.5),
        ])
        self.steps("A row lock makes any other writer of that row wait. That's what stopped the lost update.", [
            (lambda: [glow(chk_b, YELLOW_M, 1.02)], 0.8),
        ])

        # ---------------- scene 3: the race ----------------
        ta = lane_title("settlement review", AX, BLUE_M)
        tb = lane_title("card ops", BX, PURPLE_M)
        tarrow = Arrow([0, 0.75, 0], [0, -2.3, 0], buff=0, stroke_width=2.5, color=GREY_D, max_tip_length_to_length_ratio=0.04)
        sA = scan(12, 13, BLUE_M)
        sB = scan(12.5, 13.5, PURPLE_M)
        self.steps("So the settlement review team checks 12:00 to 13:00. A moment later, card ops checks 12:30 to 13:30. "
                   "Does card ops' check wait for the first team? Pause and guess.", [
            (lambda: [FadeOut(VGroup(chk_g, chk_t, lock_demo)), FadeIn(ta), FadeIn(tb), Create(tarrow)], 0.7),
            "checks 12:00",
            (lambda: [FadeIn(sA), *self.add_step("a0", "check 12:00-13:00", AX, 0, BLUE_M)], 0.6),
            "card ops checks",
            (lambda: [FadeIn(sB), *self.add_step("b1", "check 12:30-13:30", BX, 1, PURPLE_M)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        z0a = T("0 rows", 18, BLUE_M).move_to([hx(12.25), TOP_Y, 0])
        z0b = T("0 rows", 18, PURPLE_M).move_to([hx(13.25), LOW_Y, 0])
        self.steps("No. Both checks find zero rows. And a lock goes on the rows a check found, so both lock nothing.", [
            (lambda: [*self.uncap(), FadeIn(z0a), FadeIn(z0b)], 0.6),
            "zero rows",
            (lambda: [Transform(self.st["a0"], step("check: 0 rows, 0 locks", AX, 0, BLUE_M)),
                      Transform(self.st["b1"], step("check: 0 rows, 0 locks", BX, 1, PURPLE_M))], 0.6),
            "both lock nothing",
            (lambda: [*self.cap("no row found, no row locked: nobody waits", YELLOW_M)], 0.6),
        ])
        bA = bar(12, 13, TOP_Y, "settlement review", BLUE_M)
        bB = bar(12.5, 13.5, LOW_Y, "card ops", PURPLE_M)
        overlap = Rectangle(width=0.5 * PER_H, height=1.0, stroke_width=0).set_fill(RED_M, 0.35).set_z_index(2)
        overlap.move_to([(hx(12.5) + hx(13)) / 2, (TOP_Y + LOW_Y) / 2, 0])
        twice = T("12:30-13:00 booked twice", 22, RED_M)
        twice.move_to([hx(13.5) + 0.25 + twice.width / 2, TOP_Y, 0])
        self.steps("Neither can see the other's booking until it commits. So both insert, both commit, and 12:30 to 13:00 is booked twice.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(sA, sB, z0a, z0b))], 0.5),
            "So both insert",
            (lambda: [*self.add_step("a2", "INSERT 12:00-13:00", AX, 2, BLUE_M), FadeIn(bA.set_opacity(0.45))], 0.5),
            (lambda: [*self.add_step("b3", "INSERT 12:30-13:30", BX, 3, PURPLE_M), FadeIn(bB.set_opacity(0.45))], 0.5),
            "both commit",
            (lambda: [*self.add_step("a4", "COMMIT", AX, 4, BLUE_M), *self.add_step("b4", "COMMIT", BX, 4, PURPLE_M),
                      bA.animate.set_opacity(1), bB.animate.set_opacity(1)], 0.6),
            "booked twice",
            (lambda: [FadeIn(overlap), FadeIn(twice, shift=0.1 * LEFT)], 0.6),
        ])
        self.steps("Well. The lock did everything it was asked. It was asked to guard nothing.", [
            0.5,
            (lambda: [glow(self.st["a0"][0], BLUE_M, 1.03), glow(self.st["b1"][0], PURPLE_M, 1.03)], 0.8),
        ], after=0.5)

        # ---------------- scene 4: the literal guard ----------------
        g1 = guard(BLUE_M).move_to([hx(12.3), AXIS_Y + 0.55, 0])
        g2 = guard(PURPLE_M).move_to([hx(13.25), AXIS_Y + 0.55, 0])
        orders = VGroup(T("orders:", 22, GREY_B), T("“stand next to every booking between twelve and one”", 24, GOLD_M)).arrange(DOWN, buff=0.15)
        orders.move_to([0, -0.5, 0])
        self.steps("Think of the row lock as a very literal guard. You say: stand next to every booking between twelve and one.", [
            (lambda: [*self.clear_steps(), FadeOut(VGroup(ta, tb, tarrow, bA, bB, overlap, twice))], 0.6),
            "a very literal guard",
            (lambda: [FadeIn(g1, shift=0.2 * DOWN)], 0.6),
            "You say",
            (lambda: [FadeIn(orders, shift=0.1 * UP)], 0.6),
        ])
        huh = T("?", 34, YELLOW_M).next_to(g1, LEFT, buff=0.2)
        self.steps("He looks at the sheet, finds none, and stands next to... nothing.", [
            "He looks",
            (lambda: [FadeIn(sA)], 0.5),
            (lambda: [g1.animate.shift(0.35 * RIGHT)], 0.4),
            (lambda: [g1.animate.shift(0.35 * LEFT)], 0.4),
            "nothing",
            (lambda: [FadeIn(huh, scale=0.6)], 0.5),
        ])
        bA2 = bar(12, 13, TOP_Y, "settlement review", BLUE_M)
        bB2 = bar(12.5, 13.5, LOW_Y, "card ops", PURPLE_M)
        self.steps("The other team hires the same guard, with the same orders. Two guards, both guarding empty space, and two teams walk in.", [
            "The other team",
            (lambda: [FadeIn(g2, shift=0.2 * DOWN), FadeIn(sB)], 0.6),
            "two teams walk in",
            (lambda: [FadeOut(VGroup(sA, sB, huh)), g1.animate.move_to([hx(12.5), AXIS_Y + 1.45, 0]).scale(0.7),
                      g2.animate.move_to([hx(13.0), AXIS_Y - 0.0, 0]).set_opacity(0)], 0.6),
            (lambda: [FadeIn(bA2), FadeIn(bB2)], 0.6),
        ])
        self.remove(g2)
        maps = VGroup(*[VGroup(T(a, 22, GOLD_M), T("=", 22, GREY_B), T(b, 22)).arrange(RIGHT, buff=0.25)
                        for a, b in (("the guard", "the row lock"), ("what he can stand by", "rows that exist"),
                                     ("the empty slot", "a search that found nothing"))])
        maps.arrange(DOWN, buff=0.28, aligned_edge=LEFT).move_to([0, -0.9, 0])
        self.steps("Map it back. The guard is the row lock. The bookings he can stand next to are rows that exist. "
                   "The empty slot is a search that found nothing. A guard needs something to stand by.", [
            (lambda: [FadeOut(orders), FadeOut(g1)], 0.4),
            "The guard is",
            (lambda: [FadeIn(maps[0], shift=0.1 * UP)], 0.5),
            "The bookings he",
            (lambda: [FadeIn(maps[1], shift=0.1 * UP), glow(risk[0], GREY_B, 1.05)], 0.6),
            "The empty slot",
            (lambda: [FadeIn(maps[2], shift=0.1 * UP)], 0.5),
            "A guard needs",
            (lambda: self.cap("a lock can only hold a row that is already there", YELLOW_M, 26), 0.6),
        ])

        # ---------------- scene 5: the name ----------------
        ph_lab = T("phantom", 22, RED_M).move_to([hx(13.5) + 0.25 + T("phantom", 22).width / 2, LOW_Y, 0])
        self.steps("The second booking has a name: a phantom. It's a row that matches a search, but another transaction wrote it "
                   "after the search ran.", [
            (lambda: [FadeOut(maps), *self.uncap()], 0.5),
            "a phantom",
            (lambda: [FadeIn(ph_lab, shift=0.1 * LEFT), glow(bB2[0], RED_M, 1.04)], 0.7),
            "matches a search",
            (lambda: [FadeIn(sA)], 0.5),
            "after the search",
            (lambda: self.cap("phantom: a row that matches a search, written by someone else after the search ran", RED_M, 24), 0.6),
        ])
        self.steps("Both the check and the write are about a row that doesn't exist yet, so the clash has nothing to hold on to.", [
            "nothing to hold",
            (lambda: [FadeOut(sA), glow(bA2[0], BLUE_M, 1.04), glow(bB2[0], PURPLE_M, 1.04)], 0.8),
        ])
        rr = VGroup(T("Repeatable Read:", 24, GREY_B), T("hides the other booking from your reads", 22),
                    T("doesn't stop the other team inserting it", 22, RED_M)).arrange(DOWN, buff=0.18).move_to([0, -0.6, 0])
        self.steps("And the stricter setting, Repeatable Read, doesn't save us. Its snapshot hides the other booking from your reads. "
                   "It doesn't stop the other team from inserting it.", [
            (lambda: [*self.uncap(), FadeIn(rr[0])], 0.5),
            "Its snapshot",
            (lambda: [FadeIn(rr[1]), bB2.animate.set_opacity(0.25)], 0.6),
            "It doesn't stop",
            (lambda: [FadeIn(rr[2]), bB2.animate.set_opacity(1)], 0.6),
        ])
        shapes = VGroup(*[chip(s, GOLD_M, 22) for s in ("a username that must be unique", "one payout per shop per day",
                                                        "a gift card spent twice")]).arrange(DOWN, buff=0.28).move_to([0, -0.6, 0])
        self.steps("The same shape turns up wherever a rule says no row like this may exist yet: a username that must be unique, "
                   "one payout per shop per day, a gift card spent twice. Each checks that something is missing, then inserts it.", [
            (lambda: [FadeOut(rr)], 0.4),
            "a username",
            (lambda: [FadeIn(shapes[0], shift=0.1 * UP)], 0.4),
            "one payout",
            (lambda: [FadeIn(shapes[1], shift=0.1 * UP)], 0.4),
            "a gift card",
            (lambda: [FadeIn(shapes[2], shift=0.1 * UP)], 0.4),
            "Each checks",
            (lambda: self.cap("check that it's missing, then insert it", GOLD_M, 26), 0.6),
        ])

        # ---------------- scene 6: give the clash something real ----------------
        room = RoundedRectangle(corner_radius=0.12, width=3.4, height=0.75, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1)
        room.move_to([0, 0.75, 0])
        room_t = T("rooms: row 4, always there", 20).move_to(room)
        room_g = VGroup(room, room_t)
        lk1 = padlock(BLUE_M, [2.25, 0.75, 0])
        ta2 = lane_title("settlement review", AX, BLUE_M)
        tb2 = lane_title("card ops", BX, PURPLE_M)
        self.steps("So give the guard something real. Room 4 has its own row, in the rooms table, and it always exists. "
                   "Lock that first, then check.", [
            (lambda: [FadeOut(shapes), *self.uncap(), FadeOut(VGroup(bA2, bB2, ph_lab))], 0.6),
            "Room 4 has",
            (lambda: [FadeIn(room_g, shift=0.1 * DOWN), FadeIn(ta2), FadeIn(tb2)], 0.6),
            "Lock that first",
            (lambda: [*self.add_step("a1", "lock room 4", AX, 1, BLUE_M), FadeIn(lk1, scale=0.6)], 0.6),
        ])
        self.steps("Now card ops waits at the room's row. When the first team commits, card ops checks again, "
                   "sees 12:00 to 13:00, and doesn't book.", [
            (lambda: [*self.add_step("b2", "lock room 4: waits", BX, 2, YELLOW_M)], 0.5),
            (lambda: [*self.add_step("a2", "check, INSERT 12:00-13:00", AX, 2, BLUE_M), FadeIn(bA2)], 0.6),
            "When the first",
            (lambda: [*self.add_step("a3", "COMMIT", AX, 3, BLUE_M), Transform(lk1, padlock(PURPLE_M, [2.25, 0.75, 0]))], 0.6),
            "checks again",
            (lambda: [*self.add_step("b3", "check: 1 row, so no booking", BX, 3, PURPLE_M), FadeIn(sB)], 0.6),
            "doesn't book",
            (lambda: [glow(bA2[0], GREEN_M, 1.04), *self.cap("one row everyone must lock first: the second booker waits, then sees the first", GREEN_M, 24)], 0.7),
        ])
        con = VGroup(M("EXCLUDE USING gist (room_id WITH =, during WITH &&)", 20, GOLD_M),
                     T("no two bookings of one room may overlap", 22, GREY_B)).arrange(DOWN, buff=0.2).move_to([0, -0.45, 0])
        con_b = RoundedRectangle(corner_radius=0.12, width=con.width + 0.6, height=con.height + 0.45, stroke_color=GOLD_M,
                                 stroke_width=2.5).set_fill(fillc(GOLD_M, 0.1), 1).move_to(con)
        err = step("INSERT 12:30-13:30: ERROR 23P01", BX - 0.3, 4, RED_M)
        self.steps("Better still, write the rule into the table: no two bookings of one room may overlap. "
                   "PostgreSQL calls this an exclusion constraint, and it checks every booking, committed or not.", [
            (lambda: [*self.clear_steps(), *self.uncap(), FadeOut(VGroup(lk1, room_g, sB, ta2, tb2))], 0.6),
            "write the rule",
            (lambda: [FadeIn(con_b), FadeIn(con[1])], 0.6),
            "an exclusion constraint",
            (lambda: [FadeIn(con[0])], 0.6),
            "committed or not",
            (lambda: [glow(con_b, GOLD_M, 1.02)], 0.7),
        ])
        bB3 = bar(12.5, 13.5, LOW_Y, "card ops", PURPLE_M).set_opacity(0.45)
        xB = tick(False, 0.22).move_to(bB3)
        self.steps("The second insert waits for the first, then fails with error 23P01. There's no check query to get wrong.", [
            (lambda: [FadeIn(bB3)], 0.5),
            "then fails",
            (lambda: [FadeIn(err, shift=0.1 * DOWN), Create(xB)], 0.6),
            (lambda: [FadeOut(bB3), FadeOut(xB)], 0.5),
        ])
        self.steps("Rule of thumb: if the rule fits a constraint, make it one. A lock on a parent row is next best, "
                   "as long as every path through the code remembers to take it.", [
            (lambda: [FadeOut(err), *self.cap("if the rule fits a constraint, make it one", YELLOW_M, 28)], 0.6),
            "A lock on a parent",
            (lambda: self.cap("next best: lock a parent row, on every path through the code", WHITE, 26), 0.6),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So how did two teams book one room? Each locked what its check found, and its check found nothing. "
                   "A lock can only hold a row that's there.", [
            (lambda: [FadeOut(VGroup(con_b, con)), FadeIn(bB2), FadeIn(overlap), *self.uncap()], 0.7),
            "Each locked",
            (lambda: [FadeIn(sA), FadeIn(sB)], 0.6),
            "A lock can only",
            (lambda: [FadeOut(VGroup(sA, sB)), *self.cap("a lock can only hold a row that's there", YELLOW_M, 30)], 0.6),
        ], after=0.6)
        users = RoundedRectangle(corner_radius=0.12, width=4.2, height=0.75, stroke_color=WHITE, stroke_width=2.5).set_fill("#101010", 1)
        users.move_to([0, 0.55, 0])
        users_t = T("users named ivy: none yet", 22, GREY_B).move_to(users)
        u1 = step("check ivy: 0 rows, INSERT", -3.4, 2, BLUE_M)
        u2 = step("check ivy: 0 rows, INSERT", 3.4, 2, PURPLE_M)
        self.steps("One quick check. A sign-up page checks that no user named ivy exists, with FOR UPDATE, then inserts her. "
                   "Two people sign up as ivy in the same second. What stops a duplicate? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(axis, risk, bA2, bB2, overlap)), FadeIn(VGroup(users, users_t))], 0.7),
            "Two people",
            (lambda: [FadeIn(u1, shift=0.1 * UP), FadeIn(u2, shift=0.1 * UP)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        uq = chip("UNIQUE (username)", GOLD_M, 24, mono=True).move_to([0, -1.9, 0])
        self.steps("Nothing, yet. The check finds no row, so it locks no row. A unique constraint on the username stops it.", [
            (lambda: [*self.uncap(), Transform(users_t, T("users named ivy: 2", 22, RED_M).move_to(users))], 0.6),
            "A unique",
            (lambda: [FadeIn(uq, scale=0.8), Transform(u2, step("INSERT ivy: ERROR", 3.4, 2, RED_M)),
                      Transform(users_t, T("users named ivy: 1", 22, GREEN_M).move_to(users))], 0.7),
        ], after=0.3)
        self.play(*self.cap("a lock can only hold a row that's there", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
