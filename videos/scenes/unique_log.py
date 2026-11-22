from sfz import *

# How the handles and names are said; captions keep "@ana", "20.00" and "ID".
SAY.insert(0, (r"@ana\b", "at Anna"))
SAY.insert(0, (r"@bob\b", "at Bob"))
SAY.insert(0, (r"@leo\b", "at Leo"))
SAY.insert(0, (r"(?i)(?<!@)\bana\b", "Anna"))
SAY.insert(0, (r"\b20\.00\b", "twenty"))
SAY.insert(0, (r"\bF12\b", "F twelve"))
SAY.insert(0, (r"\bID\b", "I D"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CX, CY = -5.3, [1.5, -1.5]                      # the two users' phones
SX = -1.35                                      # app servers (the broken design)
DBX = 3.9                                       # the database
ROW_Y = [1.8, 0.6, -0.6, -1.8]                  # log partitions P0..P3
LX0, LX1 = -2.8, 1.6
LXC = (LX0 + LX1) / 2
SLOT_X = [-2.1, -0.7, 0.7]
PRX, PRW = 4.4, 3.2                             # processors
CAP_Y, BAR_Y = -3.15, -2.55


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
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=0.8):
    """A dot that runs along an arrow."""
    a, b = path.get_start(), path.get_end()
    d = Dot(radius=0.075, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d, run_time=0.25), FadeIn(new, shift=0.1 * d))


def rbox(x, y, w, h, color, fa=0.14):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    white = ManimColor(color).to_hex().upper() == "#FFFFFF"
    return r.set_fill(BLACK if white else fillc(color, fa), 1).move_to([x, y, 0])


def harrow(x0, x1, y, color=GREY_B):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.2)


# ---- the pieces ----
def phone(name, y):
    return VGroup(rbox(CX, y, 2.3, 1.0, WHITE), M(name, 21).move_to([CX, y + 0.2, 0]))


def phone_sub(k, s, color=GREY_B):
    return T(s, 18, color).move_to([CX, CY[k] - 0.2, 0])


def server(y):
    return VGroup(rbox(SX, y, 2.9, 1.0, BLUE_M), T("app server", 21).move_to([SX, y + 0.2, 0]))


def server_sub(k, s, color=GREY_B):
    return T(s, 17, color).move_to([SX, CY[k] - 0.2, 0])


def processor(k, y=None, title=None):
    y = ROW_Y[k] if y is None else y
    return VGroup(rbox(PRX, y, PRW, 0.95, TEAL_M), T(title or f"processor {k}", 20).move_to([PRX, y + 0.2, 0]))


def proc_sub(k, s, color=GREY_B, y=None):
    return T(s, 17, color).move_to([PRX, (ROW_Y[k] if y is None else y) - 0.2, 0])


def part_row(y, name):
    r = Rectangle(width=LX1 - LX0, height=0.72, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([LXC, y, 0])
    divs = VGroup(*[Line([x, y - 0.36, 0], [x, y + 0.36, 0], stroke_width=1.5, color=GREY_D) for x in (-1.4, 0.0)])
    g = VGroup(r, divs)
    if name:
        g.add(T(name, 20, GREY_B).move_to([-3.25, y, 0]))
    return g


def claim(rid, handle, color=GOLD_M):
    t = M(f"{rid} {handle}", 16)
    r = RoundedRectangle(corner_radius=0.08, width=1.22, height=0.5, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.25), 1)
    return VGroup(r, t).set_z_index(2)


def person(x, seat):
    head = Circle(radius=0.16, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1).move_to([x, 0.42, 0])
    body = RoundedRectangle(corner_radius=0.18, width=0.55, height=0.55, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
    body.move_to([x, -0.05, 0])
    return VGroup(head, body, M(seat, 18, GOLD_M).move_to([x, -0.62, 0]))


class UniqueLog(Base):
    """derive-04, section 0. Two people named Ana (u-17, u-43) ask for @ana in the same millisecond and both are told
    yes: check-then-save on two app servers, with no row to wait on. A theatre box office: one clerk with Friday's
    seating chart, handling requests one at a time (processor, table of taken handles, log). One log is correct but
    slow (p99 5,785 steps for 2,000 claims). Split by handle: "ana" hashes to 96,724, remainder 0 of 4, so r-1 and r-2
    meet in partition 0; r-1 granted, r-2 refused; 8 partitions give p99 2,274 and no duplicates. Keyed by user ID,
    u-17 goes to P2 and u-43 to P3 and both are granted (937 extra owners). A crashed processor replays its partition;
    the request ID repeats the answer. Moral and a check question (@leo, partition 2)."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def put(self, key, new, d=UP):
        old = self.lab.get(key)
        self.lab[key] = new
        return [swap(old, new, d)]

    def drop(self, key):
        old = self.lab.pop(key, None)
        return [FadeOut(old)] if old is not None else []

    def cap(self, s, color=GREY_B, size=22):
        return self.put("cap", T(s, size, color).move_to([0, CAP_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([LXC - 1.0, BAR_Y, 0], [LXC + 1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.lab = {}
        self.title_card("Who gets @ana?", "one decider per handle, built from a log")

        # ---------------- scene 1: Friday evening ----------------
        p17, p43 = phone("u-17", CY[0]), phone("u-43", CY[1])
        self.steps("Picture a Friday evening. A payments app has added wallets, so friends can send each other money by a "
                   "short name, called a handle.", [
            "A payments app",
            (lambda: [FadeIn(p17, shift=0.1 * RIGHT), FadeIn(p43, shift=0.1 * RIGHT)], 0.9),
        ])
        self.steps("Two people named Ana sign up in the same millisecond. Both ask for the handle @ana, and both are told it's theirs.", [
            "Both ask",
            (lambda: [*self.put("s17", phone_sub(0, "wants @ana")), *self.put("s43", phone_sub(1, "wants @ana"))], 0.6),
            "both are told",
            (lambda: [*self.put("s17", phone_sub(0, "got @ana", GOLD_M)), *self.put("s43", phone_sub(1, "got @ana", GOLD_M))], 0.6),
        ])
        money = chip("20.00 to @ana, for concert tickets", GOLD_M, 22).move_to([0, 3.0, 0])
        self.steps("On Saturday a friend sends 20.00 to @ana for concert tickets, and it lands with the wrong Ana. "
                   "Somewhere, the other Ana is having a very nice Saturday.", [
            "a friend sends",
            (lambda: [FadeIn(money, shift=0.15 * DOWN)], 0.6),
            "and it lands",
            (lambda: [money.animate.scale(0.8).next_to(p43, RIGHT, buff=0.3)], 1.0),
            (lambda: [*self.put("s43", phone_sub(1, "the wrong Ana", RED_M)), p43[0].animate.set_stroke(RED_M)], 0.5),
            "Somewhere",
            (lambda: [Wiggle(money, scale_value=1.06, rotation_angle=0.03 * TAU)], 0.9),
        ])
        qm = T("?", 72, YELLOW_M).move_to([0.6, 0.2, 0])
        self.steps("So how can two people both be told yes? Hold that question.", [
            (lambda: [FadeOut(money), p43[0].animate.set_stroke(WHITE), *self.put("s43", phone_sub(1, "got @ana", GOLD_M))], 0.6),
            "both be told",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the code that looks right ----------------
        code = M('if (!taken("ana")) save("ana", me)', 24).move_to([0.6, 3.05, 0])
        self.steps("The sign-up code looks right. Check whether @ana is taken, and if it isn't, save it. "
                   "It reads like the rule, and it passes every test that sends one sign-up at a time.", [
            (lambda: [FadeOut(qm), *self.put("s17", phone_sub(0, "wants @ana")), *self.put("s43", phone_sub(1, "wants @ana"))], 0.5),
            "Check whether",
            (lambda: [FadeIn(code, shift=0.1 * DOWN)], 0.7),
            "passes every test",
            (lambda: [*self.cap("one sign-up at a time: every test passes", GREEN_M)], 0.6),
        ])
        sa, sb = server(CY[0]), server(CY[1])
        ca = [harrow(CX + 1.25, SX - 1.55, y) for y in CY]
        db = VGroup(rbox(DBX, 0, 3.8, 2.6, GREY_B), T("database", 22).move_to([DBX, 0.85, 0]),
                    T("table of handles", 17, GREY_B).move_to([DBX, 0.48, 0]))
        da = [Arrow([SX + 1.55, CY[0], 0], [DBX - 2.0, 0.55, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.1),
              Arrow([SX + 1.55, CY[1], 0], [DBX - 2.0, -0.55, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.1)]
        self.steps("The app runs on many app servers: computers that each run a copy of the program.", [
            (lambda: self.drop("cap"), 0.4),
            "The app runs",
            (lambda: [FadeIn(sa), FadeIn(sb), GrowArrow(ca[0]), GrowArrow(ca[1])], 0.9),
        ])
        self.steps("Handles live in a database, a program that keeps records as rows in a table.", [
            "Handles live",
            (lambda: [FadeIn(db), GrowArrow(da[0]), GrowArrow(da[1])], 0.9),
            "as rows",
            (lambda: self.put("db", T("no row for ana", 18, GREY_B).move_to([DBX, -0.15, 0])), 0.5),
        ])
        self.steps("The two sign-ups reach two servers. Each asks the database: is there a row for ana? Each finds none.", [
            "reach two",
            (lambda: [flow(ca[0], WHITE, 0.6), flow(ca[1], WHITE, 0.6)], 0.8),
            "Each asks",
            (lambda: [flow(da[0], BLUE_M, 0.7), flow(da[1], BLUE_M, 0.7)], 0.9),
            "Each finds none",
            (lambda: [*self.put("sa", server_sub(0, "no row: free")), *self.put("sb", server_sub(1, "no row: free"))], 0.6),
        ])
        r1 = M("ana   u-17", 18, RED_M).move_to([DBX, -0.15, 0])
        r2 = M("ana   u-43", 18, RED_M).move_to([DBX, -0.6, 0])
        self.steps("So each one saves a row. Two rows now say @ana.", [
            (lambda: [*self.put("sa", server_sub(0, "saves ana, u-17", GOLD_M)), *self.put("sb", server_sub(1, "saves ana, u-43", GOLD_M)),
                      flow(da[0], GOLD_M, 0.7), flow(da[1], GOLD_M, 0.7)], 0.9),
            "Two rows",
            (lambda: [*self.drop("db"), FadeIn(r1), FadeIn(r2), db[0].animate.set_stroke(RED_M),
                      *self.cap("check, then save: @ana given out twice", RED_M)], 0.8),
        ])
        self.steps("Why didn't the database stop it? It makes a second writer wait on a row that exists. "
                   "Here there was no row yet, so nothing to wait on.", [
            "It makes",
            (lambda: self.cap("two writers, one row: the second one waits"), 0.6),
            "Here there was",
            (lambda: [*self.cap("each check looked for a row that didn't exist yet: nothing to wait on", RED_M),
                      flow(da[0], BLUE_M, 0.7), flow(da[1], BLUE_M, 0.7)], 0.9),
        ])
        self.steps("Tests are polite. They take turns. Users don't. Two servers each said yes without hearing "
                   "from the other. What we want is one place that hears both requests, one after the other.", [
            "Two servers",
            (lambda: [*self.cap("two deciders, each sure it was alone", RED_M)], 0.5),
            (lambda: [glow(sa[0], RED_M, 1.04), glow(sb[0], RED_M, 1.04)], 1.0),
            "What we want",
            (lambda: self.cap("wanted: one place that hears both, one after the other", YELLOW_M), 0.6),
        ])

        # ---------------- scene 3: the box office ----------------
        booth = VGroup(rbox(PRX, 0, PRW, 1.5, TEAL_M), T("the clerk", 22).move_to([PRX, 0.42, 0]),
                       T("Friday's seating chart", 18, GREY_B).move_to([PRX, 0.04, 0]))
        q = [person(x, s) for x, s in ((2.0, "F12"), (0.8, "C4"), (-0.4, "F12"))]
        self.steps("A theatre box office has this problem every night, and an old answer.", [
            (lambda: [*[FadeOut(m) for m in (sa, sb, *ca, *da, db, r1, r2, code)], *self.drop("sa"), *self.drop("sb"),
                      *self.drop("cap"), p17.animate.set_opacity(0.25), p43.animate.set_opacity(0.25),
                      self.lab["s17"].animate.set_opacity(0.25), self.lab["s43"].animate.set_opacity(0.25)], 1.0),
            "box office",
            (lambda: [FadeIn(booth, shift=0.1 * LEFT)], 0.8),
        ])

        def chart(s, color=WHITE):
            return self.put("chart", M(s, 18, color).move_to([PRX, -0.38, 0]))

        self.steps("Every request for Friday's show goes to the one clerk who holds Friday's seating chart. She handles them one at a time.", [
            (lambda: chart("F12: free"), 0.5),
            "Every request",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.3 * RIGHT) for p in q], lag_ratio=0.3)], 1.2),
            "one at a time",
            (lambda: [glow(booth[0], TEAL_M, 1.03)], 0.8),
        ])

        def step_queue(i):
            return [q[i].animate.shift(0.5 * RIGHT).set_opacity(0), *[q[j].animate.shift(1.2 * RIGHT) for j in range(i + 1, 3)]]

        sold = T("sorry, sold", 22, RED_M).move_to([PRX, 1.1, 0])
        self.steps("The first request for seat F12 gets it. The second is told: sorry, sold.", [
            (lambda: step_queue(0), 0.6),
            (lambda: chart("F12: sold", GREEN_M), 0.4),
            "The second",
            (lambda: step_queue(1), 0.5),
            (lambda: chart("F12, C4: sold", GREEN_M), 0.3),
            "sorry, sold",
            (lambda: [FadeIn(sold, shift=0.1 * UP), q[2][2].animate.set_color(RED_M)], 0.5),
        ])
        plab = T("processor", 20, TEAL_M).move_to([PRX, -1.05, 0])
        llab = T("the log", 20, GOLD_M).move_to([1.2, -1.05, 0])
        self.steps("Let's map it. The clerk is a processor: a program that reads requests in order and decides each one.", [
            (lambda: [FadeOut(sold)], 0.4),
            "The clerk is",
            (lambda: [FadeIn(plab, shift=0.1 * UP), *self.cap("the clerk = a processor", TEAL_M)], 0.6),
            "reads requests",
            (lambda: [glow(booth[0], TEAL_M, 1.03)], 0.8),
        ])
        self.steps("Her seating chart is its table of taken handles.", [
            (lambda: [*self.cap("her seating chart = its table of taken handles", TEAL_M), glow(self.lab["chart"], TEAL_M, 1.0)], 0.7),
        ])
        self.steps("And the queue at her window is a log: a list of records that only ever grows at the end.", [
            "the queue",
            (lambda: [FadeIn(llab, shift=0.1 * UP), *self.cap("the queue at her window = a log, a list that only grows at the end", GOLD_M),
                      Indicate(q[2], color=GOLD_M, scale_factor=1.1)], 0.8),
        ])

        # ---------------- scene 4: one line for everyone ----------------
        one = part_row(0, "")
        olab = T("claims log", 20, GREY_B).move_to([LXC, 0.66, 0])
        oproc = processor(0, 0, "one processor")
        osub = proc_sub(0, "first claim wins", GREY_B, 0)
        oarr = harrow(LX1 + 0.08, PRX - PRW / 2 - 0.08, 0)
        queued = [claim(r, h, c).move_to([x, 0, 0]) for r, h, c, x in
                  (("r-1", "@ana", GOLD_M, SLOT_X[0]), ("r-7", "@bob", BLUE_M, SLOT_X[1]), ("r-8", "@leo", GREY_B, SLOT_X[2]))]
        more = T("...", 30, GREY_B).move_to([LX1 + 0.35, 0.3, 0])
        self.steps("The simplest version: one log, and one processor that does one thing at a time.", [
            (lambda: [FadeOut(q[2]), FadeOut(llab), FadeOut(plab), *self.drop("chart"), *self.drop("cap"),
                      ReplacementTransform(booth[0], oproc[0]), ReplacementTransform(booth[1], oproc[1]), FadeOut(booth[2])], 0.9),
            "one log",
            (lambda: [FadeIn(one), FadeIn(olab), FadeIn(osub)], 0.6),
            (lambda: [GrowArrow(oarr)], 0.4),
        ])
        self.steps("The first claim for @ana wins, and later ones are rejected. That's correct.", [
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.3 * RIGHT) for c in queued], lag_ratio=0.3)], 1.0),
            "wins",
            (lambda: [flow(oarr, TEAL_M, 0.6)], 0.7),
            "That's correct",
            (lambda: self.cap("one decider: correct", GREEN_M), 0.5),
        ])
        self.steps("But now every claim in the whole app waits in one queue. That's one clerk selling seats for every show in the city. "
                   "Very fair, and very slow.", [
            "every claim",
            (lambda: [*self.cap("every claim in the app waits in this one queue", RED_M), FadeIn(more)], 0.6),
            "Very fair",
            (lambda: [glow(oproc[0], RED_M, 1.04)], 0.8),
        ])
        self.steps("In the lesson's simulation of 2,000 claims, one claim in a hundred waited 5,785 steps or longer.", [
            "2,000 claims",
            (lambda: [LaggedStart(*[flow(oarr, TEAL_M, 0.4) for _ in range(6)], lag_ratio=0.4)], 1.6),
            "one claim in a hundred",
            (lambda: self.cap("one log, 2,000 claims: 1 in 100 waited 5,785 steps or longer", RED_M), 0.6),
        ])

        # ---------------- scene 5: split by night ----------------
        self.steps("The box office grows by nights, not by seats. Friday's seats never clash with Saturday's. "
                   "And claims for @bob never clash with claims for @ana.", [
            (lambda: [*self.cap("split by night, not by seat", WHITE), FadeOut(more)], 0.5),
            "And claims for",
            (lambda: [Indicate(queued[1], color=BLUE_M, scale_factor=1.12)], 0.7),
            "claims for @ana",
            (lambda: [Indicate(queued[0], color=GOLD_M, scale_factor=1.12)], 0.7),
        ])
        rows = [part_row(y, f"P{k}") for k, y in enumerate(ROW_Y)]
        procs = [processor(k) for k in range(4)]
        parr = [harrow(LX1 + 0.08, PRX - PRW / 2 - 0.08, y) for y in ROW_Y]
        head = T("claims log, 4 partitions", 20, GREY_B).move_to([LXC, 2.9, 0])
        offs = [T(f"offset {j}", 15, GREY_C).move_to([x, 2.42, 0]) for j, x in enumerate(SLOT_X)]
        self.steps("So split the log into partitions: separate logs, each with its own processor. Here, four.", [
            (lambda: [*[FadeOut(c) for c in queued], FadeOut(olab), FadeOut(osub), *self.drop("cap")], 0.5),
            "So split",
            (lambda: [*[ReplacementTransform(one[0].copy(), r[0]) for r in rows], FadeOut(one),
                      *[ReplacementTransform(oproc[0].copy(), p[0]) for p in procs], FadeOut(oproc), FadeOut(oarr)], 1.1),
            (lambda: [*[FadeIn(r[1]) for r in rows], *[FadeIn(r[2]) for r in rows], FadeIn(head),
                      *[FadeIn(p[1]) for p in procs], *[GrowArrow(a) for a in parr]], 0.8),
            (lambda: [*[self.put(f"p{k}", proc_sub(k, "taken: none"))[0] for k in range(4)]], 0.5),
        ])
        self.steps("A hash of the handle picks the partition. "
                   "A hash is a number worked out from the text, always the same for the same text.", [
            "A hash of the",
            (lambda: self.cap("partition = hash(handle), divided by 4: the remainder", WHITE), 0.6),
            "always the same",
            (lambda: [*[glow(r[0], GREY_B, 1.02) for r in rows]], 0.8),
        ])
        k1, k2 = claim("r-1", "@ana"), claim("r-2", "@ana")
        k1.move_to([CX, 0.55, 0])
        k2.move_to([CX, -0.55, 0])
        self.steps("The hash of ana is 96,724. Divide by four, and the remainder is 0. "
                   "So user 17's claim goes to partition 0, at offset 0, the first place.", [
            (lambda: [*self.cap('hash("ana") = 96,724;   96,724 divided by 4 leaves 0', GOLD_M),
                      p17.animate.set_opacity(1), p43.animate.set_opacity(1),
                      *self.put("s17", phone_sub(0, "wants @ana")), *self.put("s43", phone_sub(1, "wants @ana"))], 0.7),
            "remainder is 0",
            (lambda: [glow(rows[0][0], GOLD_M, 1.02)], 0.8),
            "So user 17's",
            (lambda: [FadeIn(k1), FadeIn(offs[0])], 0.4),
            (lambda: [k1.animate.move_to([SLOT_X[0], ROW_Y[0], 0])], 1.0),
        ])
        self.steps("User 43's claim names the same handle, so it lands right behind it, at offset 1. "
                   "Whatever the phones' clocks say, the log has fixed the order.", [
            (lambda: [FadeIn(k2), FadeIn(offs[1])], 0.4),
            (lambda: [k2.animate.move_to([SLOT_X[1], ROW_Y[0], 0])], 1.2),
            "Whatever the",
            (lambda: [glow(k1[0], GOLD_M, 1.1), glow(k2[0], GOLD_M, 1.1)], 0.9),
        ])
        self.steps("Processor 0 reads them in order. What does it say to each? Pause and guess.", [
            (lambda: [glow(procs[0][0], TEAL_M, 1.04)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Offset 0: ana is free, so it's noted as user 17's, and the claim is granted.", [
            (lambda: [*self.drop("cap"), flow(parr[0], GOLD_M, 0.7)], 0.8),
            "so it's noted",
            (lambda: self.put("p0", proc_sub(0, "taken: ana (u-17)", GREEN_M)), 0.6),
            "granted",
            (lambda: [*self.put("s17", phone_sub(0, "granted @ana", GREEN_M)), k1[0].animate.set_stroke(GREEN_M)], 0.6),
        ])
        self.steps("Offset 1: ana is taken, so user 43 is told no. Nothing else can change processor 0's table.", [
            (lambda: [flow(parr[0], GOLD_M, 0.7)], 0.8),
            "is told no",
            (lambda: [*self.put("s43", phone_sub(1, "refused", RED_M)), k2[0].animate.set_stroke(RED_M)], 0.6),
            "Nothing else",
            (lambda: [glow(procs[0][0], TEAL_M, 1.04)], 0.9),
        ])
        k3 = claim("r-3", "@bob", BLUE_M).move_to([-4.3, ROW_Y[1], 0])
        self.steps("Meanwhile @bob hashes to partition 1, and processor 1 decides it at the same moment.", [
            (lambda: [FadeIn(k3)], 0.3),
            (lambda: [k3.animate.move_to([SLOT_X[0], ROW_Y[1], 0])], 0.8),
            "and processor 1",
            (lambda: [flow(parr[1], BLUE_M, 0.7), flow(parr[0], GOLD_M, 0.7)], 0.8),
            (lambda: self.put("p1", proc_sub(1, "taken: bob", GREEN_M)), 0.5),
        ])
        self.steps("With eight partitions, the slow tail fell from 5,785 steps to 2,274, and no handle was given out twice.", [
            "With eight",
            (lambda: self.cap("8 partitions: 1 in 100 waited 2,274 steps or longer (one log: 5,785)", GREEN_M), 0.6),
            "and no handle",
            (lambda: self.cap("8 partitions: 1 in 100 waited 2,274 steps or longer;  handles given twice: 0", GREEN_M), 0.6),
        ])

        # ---------------- scene 6: the wrong key ----------------
        self.steps("Now let's break it on purpose. Say someone routes claims by user ID instead. "
                   "It sounds tidy. Where do the two claims for @ana go now? Pause and guess.", [
            (lambda: [FadeOut(k1), FadeOut(k2), FadeOut(k3), FadeOut(offs[0]), FadeOut(offs[1]),
                      *self.put("p0", proc_sub(0, "taken: none")), *self.put("p1", proc_sub(1, "taken: none")),
                      *self.put("s17", phone_sub(0, "wants @ana")), *self.put("s43", phone_sub(1, "wants @ana"))], 0.8),
            "routes claims",
            (lambda: self.cap("partition = hash(user ID), divided by 4: the remainder", RED_M), 0.6),
            "Pause and guess",
            (lambda: [glow(rows[0][0], YELLOW_M, 1.02)], 0.6),
        ], after=0)
        self.countdown(3.0)
        j1, j2 = claim("r-1", "@ana"), claim("r-2", "@ana")
        j1.move_to([CX, 0.55, 0])
        j2.move_to([CX, -0.55, 0])
        self.steps("User 17 hashes to partition 2, and user 43 to partition 3. Two empty tables, and both say yes.", [
            (lambda: [FadeIn(j1)], 0.3),
            (lambda: [j1.animate.move_to([SLOT_X[0], ROW_Y[2], 0])], 0.9),
            "and user 43",
            (lambda: [FadeIn(j2)], 0.3),
            (lambda: [j2.animate.move_to([SLOT_X[0], ROW_Y[3], 0])], 0.9),
            "Two empty",
            (lambda: [flow(parr[2], GOLD_M, 0.6), flow(parr[3], GOLD_M, 0.6)], 0.7),
            "both say yes",
            (lambda: [*self.put("p2", proc_sub(2, "taken: ana (u-17)", RED_M)), *self.put("p3", proc_sub(3, "taken: ana (u-43)", RED_M)),
                      procs[2][0].animate.set_stroke(RED_M), procs[3][0].animate.set_stroke(RED_M)], 0.7),
        ])
        self.steps("Nothing failed, and nothing was logged. And @ana has two owners again.", [
            "And @ana",
            (lambda: [*self.put("s17", phone_sub(0, "granted @ana", RED_M)), *self.put("s43", phone_sub(1, "granted @ana", RED_M))], 0.7),
        ])
        self.steps("That's two clerks, each with a copy of Friday's chart, both politely selling seat F12. "
                   "The simulation counted 937 extra owners. The plain check, then save, gave 31.", [
            "two clerks",
            (lambda: [glow(procs[2][0], RED_M, 1.04), glow(procs[3][0], RED_M, 1.04)], 0.9),
            "The simulation",
            (lambda: self.cap("keyed by user ID: 937 extra owners", RED_M), 0.6),
            "The plain check",
            (lambda: self.cap("keyed by user ID: 937 extra owners.   check, then save: 31", RED_M), 0.6),
        ])
        self.steps("So the value that picks the partition is called the partition key. And for a rule like this one, "
                   "the partition key is the rule. Every claim for one handle must meet one decider, one after the other.", [
            "called the partition key",
            (lambda: self.cap("partition key: the value that picks the partition", WHITE), 0.6),
            "the partition key is the rule",
            (lambda: [*self.cap("partition key = the handle: one decider per handle", GREEN_M),
                      *self.put("p2", proc_sub(2, "taken: none")), *self.put("p3", proc_sub(3, "taken: none")),
                      procs[2][0].animate.set_stroke(TEAL_M), procs[3][0].animate.set_stroke(TEAL_M),
                      j1.animate.move_to([SLOT_X[0], ROW_Y[0], 0]), j2.animate.move_to([SLOT_X[1], ROW_Y[0], 0]),
                      FadeIn(offs[0]), FadeIn(offs[1])], 1.1),
            "Every claim",
            (lambda: [flow(parr[0], GOLD_M, 0.6)], 0.6),
            (lambda: [*self.put("p0", proc_sub(0, "taken: ana (u-17)", GREEN_M)), j1[0].animate.set_stroke(GREEN_M), j2[0].animate.set_stroke(RED_M),
                      *self.put("s17", phone_sub(0, "granted @ana", GREEN_M)), *self.put("s43", phone_sub(1, "refused", RED_M))], 0.7),
        ])

        # ---------------- scene 7: when the clerk faints ----------------
        self.steps("The box office picture breaks at a crash. A clerk who faints still has her chart. "
                   "A crashed processor loses its memory.", [
            (lambda: self.cap("where the box office picture breaks: a crash", WHITE), 0.6),
            "A crashed processor",
            (lambda: [procs[0][0].animate.set_stroke(GREY_D), procs[0][1].animate.set_opacity(0.4),
                      *self.put("p0", proc_sub(0, "crashed: table lost", RED_M))], 0.8),
        ])
        cur = RoundedRectangle(corner_radius=0.08, width=1.36, height=0.62, stroke_color=YELLOW_M, stroke_width=4).move_to([SLOT_X[0], ROW_Y[0], 0])
        self.steps("It reads its partition again from offset 0 and decides the same way, in the same order. "
                   "So ana goes to user 17 again.", [
            "reads its partition",
            (lambda: [procs[0][0].animate.set_stroke(TEAL_M), procs[0][1].animate.set_opacity(1), Create(cur),
                      *self.put("p0", proc_sub(0, "replaying..."))], 0.6),
            (lambda: [flow(parr[0], GOLD_M, 0.6)], 0.7),
            (lambda: [cur.animate.move_to([SLOT_X[1], ROW_Y[0], 0])], 0.4),
            (lambda: [flow(parr[0], GOLD_M, 0.6)], 0.7),
            "So ana goes",
            (lambda: [FadeOut(cur), *self.put("p0", proc_sub(0, "taken: ana (u-17)", GREEN_M))], 0.6),
        ])
        k4 = claim("r-2", "@ana").move_to([CX, -0.55, 0])
        off2 = T("offset 2", 15, GREY_C).move_to([SLOT_X[2], 2.42, 0])
        self.steps("Each claim carries a request ID, one per tap. If user 43's claim arrives again, "
                   "the processor finds that ID among its answers and says no again.", [
            "a request ID",
            (lambda: [*self.cap("each claim carries a request ID, one per tap: r-1, r-2", WHITE),
                      Indicate(j1[1], color=GOLD_M, scale_factor=1.15), Indicate(j2[1], color=GOLD_M, scale_factor=1.15)], 0.8),
            "arrives again",
            (lambda: [FadeIn(k4), FadeIn(off2)], 0.3),
            (lambda: [k4.animate.move_to([SLOT_X[2], ROW_Y[0], 0])], 1.0),
            "finds that ID",
            (lambda: [flow(parr[0], GOLD_M, 0.6)], 0.7),
            (lambda: [*self.put("p0", proc_sub(0, "r-2 again: same answer, no", RED_M)), k4[0].animate.set_stroke(RED_M)], 0.6),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, how were two people both told yes? Two deciders, each sure it was alone. The fix is one decider per handle: "
                   "a partition keyed by the handle, where one processor says yes or no, in order.", [
            (lambda: [FadeOut(k4), FadeOut(off2), *self.put("p0", proc_sub(0, "taken: ana (u-17)", GREEN_M)),
                      *self.cap("how were two people both told yes?", WHITE)], 0.6),
            "Two deciders",
            (lambda: self.cap("two deciders, each sure it was alone", RED_M), 0.5),
            "The fix is",
            (lambda: [*self.cap("one decider per handle, one after the other", YELLOW_M, 26), glow(rows[0][0], GOLD_M, 1.02)], 0.7),
            "one processor says",
            (lambda: [glow(procs[0][0], TEAL_M, 1.04)], 0.8),
        ])
        l5 = claim("r-5", "@leo", GREY_B).move_to([CX, 0.3, 0])
        l6 = claim("r-6", "@leo", GREY_B).move_to([CX, -0.35, 0])
        self.steps("One quick check. Two people ask for @leo at the same moment. Which processor decides, and who gets it? Pause and think.", [
            (lambda: [*self.drop("cap")], 0.4),
            "Two people",
            (lambda: [FadeIn(l5, shift=0.2 * RIGHT), FadeIn(l6, shift=0.2 * RIGHT)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Leo hashes to partition 2. Processor 2 decides both, and the claim that landed first in the log gets @leo.", [
            (lambda: [*self.cap('hash("leo") = 107,030;   divided by 4 leaves 2', GREY_B)], 0.5),
            (lambda: [l5.animate.move_to([SLOT_X[0], ROW_Y[2], 0])], 0.7),
            (lambda: [l6.animate.move_to([SLOT_X[1], ROW_Y[2], 0])], 0.7),
            "Processor 2 decides",
            (lambda: [flow(parr[2], GOLD_M, 0.6)], 0.7),
            (lambda: [*self.put("p2", proc_sub(2, "taken: leo (r-5)", GREEN_M)), l5[0].animate.set_stroke(GREEN_M)], 0.5),
            (lambda: [flow(parr[2], GOLD_M, 0.6)], 0.7),
            (lambda: [l6[0].animate.set_stroke(RED_M)], 0.4),
        ], after=0.3)
        self.play(*self.cap("one decider per handle, one after the other", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
