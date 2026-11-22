from sfz import *

# Amounts are said the way people say them ("seventy"); captions keep "70.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bt([12])\b", r"tee \1"))
SAY.insert(0, (r"\bQUORUM\b", "quorum"))
SAY.insert(0, (r"\bONE\b", "one"))
SAY.insert(0, (r"\bALL\b", "all"))
# the clerk called A is said "eh", not "uh"
SAY.insert(0, (r"\bA (and|has|says)\b", r"eh \1"))
SAY.insert(0, (r"\b(and|only) A\b", r"\1 eh"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RX, RW, RH = 0.9, 3.3, 1.3                 # the three clerks (replicas), one column
RY = [2.1, 0.15, -1.8]
R_X0, R_X1 = RX - RW / 2, RX + RW / 2
CO = np.array([-3.55, 0.15, 0])            # the coordinator
CO_W, CO_H = 2.5, 1.1
PH = np.array([-5.75, 2.25, 0])            # the owner's phone
PH_W, PH_H = 1.3, 1.9
PX0, PX1, PTOP, PBOT = 4.0, 6.6, 2.75, -2.45   # the panel with the counts
PCX = (PX0 + PX1) / 2
PROW = [2.3, 1.55, 0.95, 0.35, -0.35, -1.0]
CAP_Y, BAR_Y, HEAD_Y = -3.3, -2.85, 3.3
NAMES = "ABC"


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays;
        a number waits that long; a string waits until about where that phrase is spoken."""
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
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, frac=1.0):
    d = Dot(radius=0.08, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=0.8),
                      FadeOut(d, run_time=0.15))


# ---- the pieces ----
def clerk_box(i):
    y = RY[i]
    r = RoundedRectangle(corner_radius=0.14, width=RW, height=RH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([RX, y, 0])
    name = left_at(T(f"clerk {NAMES[i]}", 24), R_X0 + 0.25, y + 0.36)
    return VGroup(r, name)


def val_text(i, s, color=WHITE):
    return M(s, 28, color).move_to([RX, RY[i] - 0.22, 0])


def status_text(i, s, color=RED_M):
    return right_at(T(s, 20, color), R_X1 - 0.25, RY[i] + 0.36)


def phone():
    body = RoundedRectangle(corner_radius=0.22, width=PH_W, height=PH_H, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(PH)
    screen = RoundedRectangle(corner_radius=0.1, width=PH_W - 0.2, height=PH_H - 0.5, stroke_width=0).set_fill("#15191d", 1)
    screen.move_to(PH + 0.02 * DOWN)
    slot = Line(PH + [-0.16, PH_H / 2 - 0.12, 0], PH + [0.16, PH_H / 2 - 0.12, 0], stroke_width=3, color=GREY_C)
    return VGroup(body, screen, slot, T("café app", 15, GREY_B).move_to(PH + [0, 0.5, 0]), T("balance", 15).move_to(PH + [0, 0.1, 0]))


def ph_num(s, color=WHITE):
    return M(s, 22, color).move_to(PH + [0, -0.35, 0])


def coordinator():
    r = RoundedRectangle(corner_radius=0.14, width=CO_W, height=CO_H, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1)
    r.move_to(CO)
    return VGroup(r, T("coordinator", 24).move_to(CO + [0, 0.18, 0]), T("any node", 18, GREY_B).move_to(CO + [0, -0.22, 0]))


def link_arrow(i, color=GOLD_M, dy=0.0):
    a = CO + [CO_W / 2 + 0.08, 0, 0]
    b = np.array([R_X0 - 0.08, RY[i] + dy, 0])
    return Arrow(a, b, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.08)


def panel():
    r = RoundedRectangle(corner_radius=0.14, width=PX1 - PX0, height=PTOP - PBOT, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
    r.move_to([PCX, (PTOP + PBOT) / 2, 0])
    return VGroup(r, T("the counts", 22, GREY_B).move_to([PCX, PROW[0], 0]))


def prow(k, label, value, color=WHITE):
    y = PROW[k]
    return VGroup(left_at(M(label, 24, color), PX0 + 0.3, y), right_at(M(value, 24, color), PX1 - 0.3, y))


def read_ring(i, color=GREEN_M):
    return SurroundingRectangle(Rectangle(width=RW, height=RH).move_to([RX, RY[i], 0]), color=color, buff=0.1,
                                corner_radius=0.2, stroke_width=3)


class Quorums(Base):
    """repl-07, section 1. The café owner's phone shows 100.00 after the app said OK to moving 30.00 out. Three clerks
    in three towns keep the same account book; how many must say "written" before you hang up? W = 3 is slow and
    blocked by one absent clerk; W = 1 lets a read of one clerk miss the write. R = 2 with W = 2: every pair meets the
    write. R = 2 alone is luck (the write reached only A). R + W > N, the quorum; the N = 3 table; what still works
    with clerks down; Cassandra's consistency levels and their low default; one limit; a check question."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def head(self, s, color=GREY_B):
        new = T(s, 24, color).move_to([RX, HEAD_Y, 0])
        old, self.headm = self.headm, new
        return [swap(old, new)]

    def unhead(self):
        old, self.headm = self.headm, None
        return [FadeOut(old)] if old is not None else []

    def set_val(self, i, s, color=WHITE):
        new = val_text(i, s, color)
        old, self.vals[i] = self.vals[i], new
        return [swap(old, new)]

    def set_status(self, i, s=None, color=RED_M):
        old = self.stat[i]
        new = status_text(i, s, color) if s else None
        self.stat[i] = new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def set_row(self, k, label, value, color=WHITE):
        new = prow(k, label, value, color)
        old, self.rows[k] = self.rows.get(k), new
        return [swap(old, new, RIGHT)]

    def set_sum(self, total, ok):
        col = YELLOW_M if ok is None else (GREEN_M if ok else RED_M)
        a = self.set_row(4, "R + W", total, col)
        verdict = {True: "> N: they meet", False: "not > N", None: "must be > N"}[ok]
        new = T(verdict, 20, col).move_to([PCX, PROW[5], 0])
        old, self.rows[5] = self.rows.get(5), new
        return a + [swap(old, new)]

    def clear_rows(self, *ks):
        out = []
        for k in ks:
            old = self.rows.pop(k, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def set_pn(self, s, color=WHITE):
        new = ph_num(s, color)
        old, self.pn = self.pn, new
        return [swap(old, new)]

    def has_write(self, i, on=True):
        c = GOLD_M if on else WHITE
        return [self.boxes[i][0].animate.set_stroke(c)]

    def construct(self):
        self.capm = self.headm = self.pn = None
        self.vals = [None, None, None]
        self.stat = [None, None, None]
        self.rows = {}
        self.title_card("What did OK mean?", "three copies, no leader, and counting who must answer")

        # ---------------- scene 1: the hook ----------------
        ph = phone()
        self.pn = ph_num("100.00")
        hook = VGroup(ph, self.pn)
        HOOK = 1.6
        hook.scale(HOOK).move_to([0, 0.2, 0])
        self.steps("Picture a café owner checking her balance on her phone. A minute ago, she moved 30.00 out of her account, "
                   "and the app said OK.", [
            (lambda: [FadeIn(ph, shift=0.2 * UP)], 0.8),
            (lambda: [FadeIn(self.pn)], 0.4),
        ])
        slip = RoundedRectangle(corner_radius=0.12, width=2.7, height=2.0, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1)
        slip.move_to([-4.3, 0.2, 0])
        slip_t = VGroup(T("moved out", 22, GOLD_M), M("-30.00", 30, GOLD_M), T("the app said: OK", 18, GREY_B)).arrange(DOWN, buff=0.18).move_to(slip)
        should = VGroup(T("should be", 22, GREY_B), M("70.00", 40, GREEN_M)).arrange(DOWN, buff=0.18).move_to([4.3, 0.2, 0])
        self.steps("So the balance should be 70.00. Her phone still shows 100.00.", [
            (lambda: [FadeIn(VGroup(slip, slip_t), shift=0.2 * RIGHT)], 0.7),
            "should be",
            (lambda: [FadeIn(should, shift=0.2 * LEFT)], 0.7),
            "still shows",
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.15)], 0.9),
        ])
        qm = T("?", 64, YELLOW_M).move_to([0, 3.15, 0])
        self.steps("The app said OK, and the app is showing the old number. So what did OK actually mean? Hold that question.", [
            "what did OK",
            (lambda: [FadeIn(qm, scale=0.6), Indicate(slip_t[2], color=GOLD_M, scale_factor=1.15)], 0.8),
        ])

        # ---------------- scene 2: three copies, nobody in charge ----------------
        self.boxes = [clerk_box(i) for i in range(3)]
        for b, n in zip(self.boxes, ["copy A", "copy B", "copy C"]):
            b[1].become(left_at(T(n, 24), R_X0 + 0.25, b[1].get_center()[1]))
        self.links = [link_arrow(i, GREY_B) for i in range(3)]
        self.steps("Behind the app, each balance is kept on three computers, so one can break safely. "
                   "With one computer in charge, you'd just ask that one. Here, none of the three is in charge.", [
            (lambda: [FadeOut(VGroup(slip, slip_t, should, qm)), hook.animate.scale(1 / HOOK).move_to(PH)], 1.0),
            "three computers",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.15 * LEFT) for b in self.boxes], lag_ratio=0.3)], 1.0),
            (lambda: [*[a for i in range(3) for a in self.set_val(i, "100.00 @ t1")], *self.head("three copies of one balance")], 0.6),
            "Here, none",
            (lambda: self.cap("nobody is in charge"), 0.5),
        ])
        # the phone shrank as a group: re-place its number exactly where ph_num puts it
        self.pn.move_to(ph_num("100.00"))
        co = coordinator()
        a_ph = Arrow(PH + [0.3, -PH_H / 2 - 0.05, 0], CO + [-0.6, CO_H / 2 + 0.06, 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.15)
        self.steps("Whichever computer gets a request passes it on to all three copies. Let's call that computer the coordinator.", [
            (lambda: [GrowArrow(a_ph), FadeIn(co, shift=0.1 * RIGHT)], 0.8),
            "passes it on",
            (lambda: [*[GrowArrow(a) for a in self.links]], 0.6),
            (lambda: [dot_run(a_ph.get_start(), a_ph.get_end(), WHITE)], 0.6),
            (lambda: [*[dot_run(link_arrow(i).get_start(), link_arrow(i).get_end(), WHITE) for i in range(3)]], 0.9),
            "the coordinator",
            (lambda: [glow(co[0], BLUE_M, 1.04), *self.cap("coordinator: whichever node got the request", BLUE_M)], 0.8),
        ])

        # ---------------- scene 3: the clerks ----------------
        clerks = [left_at(T(f"clerk {n}", 24), R_X0 + 0.25, RY[i] + 0.36) for i, n in enumerate(NAMES)]
        self.steps("Let's leave computers for a moment. Picture three clerks in three towns, each keeping a copy of the same account book.", [
            (lambda: self.uncap(), 0.3),
            "three clerks",
            (lambda: [*[Transform(self.boxes[i][1], clerks[i]) for i in range(3)], *self.head("three clerks, three towns, one account book")], 0.9),
        ])
        self.steps("You phone each new entry to all three, and each clerk writes down the amount and the time of your call. "
                   "The question is: how many must say written before you hang up?", [
            "You phone",
            (lambda: [*[dot_run(link_arrow(i).get_start(), link_arrow(i).get_end(), YELLOW_M) for i in range(3)]], 0.9),
            "the time of your call",
            (lambda: [*[Indicate(self.vals[i], color=YELLOW_M, scale_factor=1.08) for i in range(3)]], 0.8),
            "how many must",
            (lambda: self.cap("how many must say \"written\" before you hang up?", YELLOW_M), 0.6),
        ])
        self.steps("Let's map it. Each clerk is a copy, which is called a replica. You, making the calls, are the coordinator. "
                   "And every entry carries its time, so when two books disagree, the newer entry wins.", [
            "Each clerk",
            (lambda: [*self.cap("clerk = a copy = a replica"), *[glow(b[0], WHITE, 1.03) for b in self.boxes]], 0.8),
            "You, making",
            (lambda: [*self.cap("you, making the calls = the coordinator", BLUE_M), glow(co[0], BLUE_M, 1.04)], 0.8),
            "every entry carries",
            (lambda: self.cap("every entry carries its time: the newer one wins"), 0.6),
        ])

        # ---------------- scene 4: wait for all, wait for one ----------------
        self.panel_m = panel()
        self.steps("First idea: wait for all three. Then every book has every entry, and any clerk you ask later is right.", [
            (lambda: [*self.uncap(), FadeIn(self.panel_m), *self.set_row(1, "N", "3")], 0.7),
            "wait for all",
            (lambda: self.set_row(2, "W", "3", GOLD_M), 0.5),
            (lambda: [*[dot_run(link_arrow(i).get_start(), link_arrow(i).get_end(), GOLD_M) for i in range(3)]], 0.9),
            "any clerk",
            (lambda: [*[glow(b[0], GOLD_M, 1.03) for b in self.boxes]], 0.8),
        ])
        self.steps("But every call is as slow as the slowest clerk. And if one clerk is out to lunch, you can't write anything at all. "
                   "One sandwich, and the whole account is frozen.", [
            "slowest clerk",
            (lambda: self.cap("as slow as the slowest clerk"), 0.5),
            "out to lunch",
            (lambda: [*self.set_status(2, "out to lunch"), self.boxes[2][0].animate.set_stroke(GREY_D), self.vals[2].animate.set_opacity(0.35)], 0.6),
            "can't write",
            (lambda: self.cap("one clerk away: no write at all", RED_M), 0.5),
            "One sandwich",
            (lambda: [Wiggle(self.stat[2], scale_value=1.1, rotation_angle=0.02 * TAU)], 0.9),
        ])
        self.steps("Second idea: wait for just one. Fast, and almost always possible. That's what the café's app did.", [
            (lambda: [*self.uncap(), *self.set_status(2, None), self.boxes[2][0].animate.set_stroke(WHITE), self.vals[2].animate.set_opacity(1)], 0.6),
            "wait for just one",
            (lambda: self.set_row(2, "W", "1", GOLD_M), 0.5),
            "That's what",
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.2)], 0.8),
        ])
        okc = T("OK", 24, GREEN_M).move_to(PH + [PH_W / 2 + 0.45, 0.35, 0])
        self.steps("Clerk C was restarting when the call came. A and B wrote down 70.00 at time t2, "
                   "and the app heard OK after the first one answered.", [
            (lambda: [*self.set_status(2, "restarting"), self.boxes[2][0].animate.set_stroke(GREY_D), self.vals[2].animate.set_opacity(0.35)], 0.6),
            "A and B",
            (lambda: [dot_run(link_arrow(0).get_start(), link_arrow(0).get_end(), GOLD_M),
                      dot_run(link_arrow(1).get_start(), link_arrow(1).get_end(), GOLD_M),
                      dot_run(link_arrow(2).get_start(), link_arrow(2).get_end(), GOLD_M, frac=0.6)], 0.9),
            (lambda: [*self.set_val(0, "70.00 @ t2", GOLD_M), *self.has_write(0)], 0.5),
            "the app heard OK",
            (lambda: [dot_run(link_arrow(0).get_end(), link_arrow(0).get_start(), GREEN_M)], 0.6),
            (lambda: [FadeIn(okc, shift=0.1 * UP), *self.set_val(1, "70.00 @ t2", GOLD_M), *self.has_write(1)], 0.5),
        ])
        self.rr = read_ring(2)
        self.steps("Then C comes back, still holding 100.00 from t1. And the phone's next read asks just one clerk. It happens to be C.", [
            (lambda: [*self.set_status(2, None), self.boxes[2][0].animate.set_stroke(WHITE), self.vals[2].animate.set_opacity(1), FadeOut(okc)], 0.6),
            "still holding",
            (lambda: [*self.set_val(2, "100.00 @ t1", RED_M)], 0.5),
            "asks just one",
            (lambda: [*self.set_row(3, "R", "1", GREEN_M), FadeIn(self.rr)], 0.6),
            "It happens",
            (lambda: [dot_run(link_arrow(2).get_start(), link_arrow(2).get_end(), GREEN_M)], 0.6),
            (lambda: [dot_run(link_arrow(2).get_end(), link_arrow(2).get_start(), RED_M)], 0.6),
            (lambda: [dot_run(a_ph.get_end(), a_ph.get_start(), RED_M)], 0.5),
            (lambda: [Indicate(self.pn, color=RED_M, scale_factor=1.25)], 0.6),
        ])
        self.steps("So OK meant: at least one clerk wrote it down, somewhere. Nothing promised that the read would ask that one.", [
            "at least one",
            (lambda: [*self.cap("OK at W = 1: at least one clerk wrote it down, somewhere"), glow(self.boxes[0][0], GOLD_M, 1.03)], 0.8),
            "Nothing promised",
            (lambda: [glow(self.rr, GREEN_M, 1.02)], 0.8),
        ])
        self.steps("What we want is simple: the clerks a read asks should always include at least one who has the write.", [
            (lambda: self.cap("wanted: the read always meets a clerk with the write", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 5: count both sides ----------------
        self.steps("Let's give the two sides names. W is how many clerks must confirm a write. R is how many clerks a read asks. "
                   "N is the number of copies, three.", [
            (lambda: [*self.uncap(), FadeOut(self.rr)], 0.4),
            "W is how many",
            (lambda: [Indicate(self.rows[2], color=GOLD_M, scale_factor=1.1), *self.cap("W: clerks that must confirm a write", GOLD_M)], 0.8),
            "R is how many",
            (lambda: [Indicate(self.rows[3], color=GREEN_M, scale_factor=1.1), *self.cap("R: clerks a read asks", GREEN_M)], 0.8),
            "N is the number",
            (lambda: [Indicate(self.rows[1], color=WHITE, scale_factor=1.1), *self.cap("N: the number of copies")], 0.8),
        ])
        self.steps("Try W equals 2 and R equals 2. The write is on A and B. The read asks any two clerks. "
                   "Can it pick two who both missed the write? Pause and guess.", [
            (lambda: [*self.uncap(), *self.set_row(2, "W", "2", GOLD_M), *self.set_row(3, "R", "2", GREEN_M)], 0.6),
            "The write is on",
            (lambda: [glow(self.boxes[0][0], GOLD_M, 1.03), glow(self.boxes[1][0], GOLD_M, 1.03)], 0.8),
            "Can it pick",
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        pairs = [(0, 1), (0, 2), (1, 2)]
        lines = ["A and B: both have it", "A and C: A has it", "B and C: B has it"]

        def show_pair(k):
            a, b = pairs[k]
            rings = VGroup(read_ring(a), read_ring(b))
            return rings

        self.pr = None

        def pair_step(k):
            new = show_pair(k)
            old, self.pr = self.pr, new
            anims = [FadeIn(new)] + ([FadeOut(old)] if old is not None else []) + self.cap(lines[k], GREEN_M)
            return anims

        self.steps("Let's try every pair. A and B: both have it. A and C: A has it. B and C: B has it. "
                   "Every pair includes a clerk with the write.", [
            "A and B",
            (lambda: pair_step(0), 0.5),
            "A and C",
            (lambda: pair_step(1), 0.5),
            (lambda: [glow(self.boxes[0][0], YELLOW_M, 1.03)], 0.6),
            "B and C",
            (lambda: pair_step(2), 0.5),
            (lambda: [glow(self.boxes[1][0], YELLOW_M, 1.03)], 0.6),
            "Every pair",
            (lambda: [FadeOut(self.pr), *self.cap("every pair meets the write", YELLOW_M)], 0.6),
        ])
        self.pr = VGroup(read_ring(2), read_ring(0))
        ans = T("returns 70.00", 22, GREEN_M).move_to(CO + [0, -CO_H / 2 - 0.4, 0])
        self.steps("Say it asks C and A. C says 100.00 at t1. A says 70.00 at t2. The newer one wins, so the read returns 70.00.", [
            (lambda: [*self.uncap(), FadeIn(self.pr)], 0.5),
            "C says",
            (lambda: [dot_run(link_arrow(2).get_end(), link_arrow(2).get_start(), RED_M), Indicate(self.vals[2], color=RED_M, scale_factor=1.1)], 0.8),
            "A says",
            (lambda: [dot_run(link_arrow(0).get_end(), link_arrow(0).get_start(), GOLD_M), Indicate(self.vals[0], color=GOLD_M, scale_factor=1.1)], 0.8),
            "The newer one",
            (lambda: [FadeIn(ans, shift=0.1 * DOWN), *self.cap("t2 is newer than t1: the newer entry wins")], 0.6),
            "returns 70.00",
            (lambda: [dot_run(a_ph.get_end(), a_ph.get_start(), GREEN_M)], 0.5),
            (lambda: self.set_pn("70.00", GREEN_M), 0.4),
        ])
        fix = link_arrow(2, TEAL_M)
        self.steps("And on its way out, the coordinator tells C the new entry, so C catches up too. That's called read repair.", [
            (lambda: [FadeOut(self.pr), FadeOut(ans), *self.uncap()], 0.4),
            "tells C",
            (lambda: [GrowArrow(fix)], 0.5),
            (lambda: [dot_run(fix.get_start(), fix.get_end(), TEAL_M)], 0.7),
            (lambda: [*self.set_val(2, "70.00 @ t2", GOLD_M), *self.has_write(2)], 0.5),
            "read repair",
            (lambda: [FadeOut(fix), *self.cap("read repair: a read fixes the copies it asked", TEAL_M)], 0.6),
        ])

        # ---------------- scene 6: break "just read from two" ----------------
        self.steps("Now, you might be thinking: so the fix is to read from two. Let's be fair to that idea. In the café, R equals 2 would have worked.", [
            (lambda: [*self.uncap()], 0.3),
            "read from two",
            (lambda: [*self.cap("\"just read from two\"?", WHITE)], 0.5),
        ])
        self.steps("But only by luck. The write happened to reach two clerks, and W equals 1 promised only one. "
                   "Run it again, with the write reaching only A.", [
            "only by luck",
            (lambda: [*self.set_row(2, "W", "1", GOLD_M), glow(self.boxes[0][0], GOLD_M), glow(self.boxes[1][0], GOLD_M)], 0.8),
            "Run it again",
            (lambda: [*self.set_val(1, "100.00 @ t1", RED_M), *self.set_val(2, "100.00 @ t1", RED_M), *self.has_write(1, False),
                      *self.has_write(2, False), *self.set_pn("100.00"), *self.cap("this time, only A got t2")], 0.8),
        ])
        self.pr = VGroup(read_ring(1), read_ring(2))
        self.steps("Now a read of B and C gets 100.00 from both. Both agree, both are old, and nothing says so. "
                   "Well... that's two wrong answers in perfect agreement.", [
            (lambda: [FadeIn(self.pr), *self.uncap()], 0.5),
            "gets 100.00",
            (lambda: [dot_run(link_arrow(1).get_end(), link_arrow(1).get_start(), RED_M),
                      dot_run(link_arrow(2).get_end(), link_arrow(2).get_start(), RED_M)], 0.8),
            (lambda: [dot_run(a_ph.get_end(), a_ph.get_start(), RED_M)], 0.5),
            (lambda: [*self.set_pn("100.00", RED_M)], 0.4),
            "Well...",
            (lambda: [*self.cap("R = 2, W = 1: two old answers, and they agree", RED_M)], 0.6),
        ])
        self.steps("So it's never R alone, or W alone. It's the two together.", [
            (lambda: [Indicate(self.rows[2], color=GOLD_M, scale_factor=1.1), Indicate(self.rows[3], color=GREEN_M, scale_factor=1.1)], 0.9),
        ])

        # ---------------- scene 7: the rule, and its name ----------------
        self.steps("Here's the rule. If R plus W is more than N, every read meets every write the client heard OK for.", [
            (lambda: [FadeOut(self.pr), *self.uncap(), *self.set_row(2, "W", "2", GOLD_M), *self.set_row(3, "R", "2", GREEN_M),
                      *self.set_val(1, "70.00 @ t2", GOLD_M), *self.has_write(1), *self.set_val(2, "100.00 @ t1", RED_M)], 0.8),
            "If R plus W",
            (lambda: self.set_sum("4", True), 0.6),
            "every read meets",
            (lambda: self.cap("R + W > N: every read meets every acknowledged write", YELLOW_M), 0.6),
        ])
        self.pr = VGroup(read_ring(1), read_ring(2))
        self.steps("Two plus two is four, and you can't fit four different clerks into three towns. At least one is in both groups.", [
            "Two plus two",
            (lambda: [FadeIn(self.pr)], 0.6),
            "At least one",
            (lambda: [glow(self.boxes[1][0], YELLOW_M, 1.04), Indicate(self.vals[1], color=YELLOW_M, scale_factor=1.1)], 0.9),
            (lambda: [dot_run(a_ph.get_end(), a_ph.get_start(), GREEN_M)], 0.5),
            (lambda: self.set_pn("70.00", GREEN_M), 0.4),
        ])
        self.steps("A group big enough to overlap every other such group is called a quorum. For three copies, a quorum is two.", [
            (lambda: [FadeOut(self.pr)], 0.4),
            "called a quorum",
            (lambda: [*self.cap("quorum: a group big enough to meet every other such group", YELLOW_M), *self.head("quorums of two, out of three", YELLOW_M)], 0.7),
        ])
        # the table, inside the panel
        tab_head = VGroup(left_at(M("W  R", 22, GREY_B), PX0 + 0.3, PROW[1]), right_at(T("meet?", 20, GREY_B), PX1 - 0.3, PROW[1]))
        trows = []
        for k, (w, r, ok) in enumerate([(1, 1, False), (2, 2, True), (1, 3, True), (3, 1, True)]):
            y = PROW[2] - 0.62 * k
            trows.append(VGroup(left_at(M(f"{w}  {r}", 24, GOLD_M if ok else RED_M), PX0 + 0.3, y),
                                right_at(M("yes" if ok else "no", 24, GREEN_M if ok else RED_M), PX1 - 0.3, y)))

        def tline(k):
            return [Indicate(trows[k], color=YELLOW_M, scale_factor=1.12)]

        self.steps("For three copies, here are the choices. One and one is fast, but can be stale. Two and two is the common choice. "
                   "One and three gives fast writes and slow reads. Three and one gives fast reads, and one absent clerk blocks every write.", [
            (lambda: [*self.uncap(), *self.clear_rows(1, 2, 3, 4, 5), FadeIn(tab_head)], 0.6),
            "One and one",
            (lambda: [FadeIn(trows[0], shift=0.1 * RIGHT), *self.cap("1 + 1 = 2: fast, maybe stale")], 0.5),
            "Two and two",
            (lambda: [FadeIn(trows[1], shift=0.1 * RIGHT), *self.cap("2 + 2 = 4: the common choice")], 0.5),
            "One and three",
            (lambda: [FadeIn(trows[2], shift=0.1 * RIGHT), *self.cap("1 + 3 = 4: fast writes, slow reads")], 0.5),
            "Three and one",
            (lambda: [FadeIn(trows[3], shift=0.1 * RIGHT), *self.cap("3 + 1 = 4: fast reads; one clerk away blocks writes")], 0.5),
        ])

        # ---------------- scene 8: what still works, and the guardrail ----------------
        refuse = tick(False, 0.2).move_to(CO + [0, -CO_H / 2 - 0.4, 0])
        self.steps("The same count decides what still works while clerks are away. With one of three away, two and two still work. "
                   "With two away, both fail, and the coordinator refuses before it even tries.", [
            (lambda: [FadeOut(VGroup(tab_head, *trows)), *self.uncap(), *self.set_row(1, "N", "3"), *self.set_row(2, "W", "2", GOLD_M),
                      *self.set_row(3, "R", "2", GREEN_M), *self.set_sum("4", True), *self.unhead()], 0.7),
            "With one of three",
            (lambda: [*self.set_status(2, "away", RED_M), self.boxes[2][0].animate.set_stroke(GREY_D), self.vals[2].animate.set_opacity(0.35),
                      *self.cap("one away: 2 still answer, so W = 2 and R = 2 work", GREEN_M)], 0.7),
            "With two away",
            (lambda: [*self.set_status(1, "away", RED_M), self.boxes[1][0].animate.set_stroke(GREY_D), self.vals[1].animate.set_opacity(0.35),
                      *self.cap("two away: only 1 answers, so both refuse", RED_M)], 0.7),
            "refuses before",
            (lambda: [Create(refuse)], 0.5),
        ])
        self.steps("Cassandra, a free database that spreads its data over many computers, works this way. "
                   "Each request picks its own count, with a setting called the consistency level. "
                   "ONE waits for one copy. QUORUM waits for two of three. ALL waits for every copy.", [
            (lambda: [FadeOut(refuse), *self.uncap(), *self.set_status(1, None), *self.set_status(2, None),
                      self.boxes[1][0].animate.set_stroke(GOLD_M), self.boxes[2][0].animate.set_stroke(WHITE),
                      self.vals[1].animate.set_opacity(1), self.vals[2].animate.set_opacity(1)], 0.7),
            "consistency level",
            (lambda: self.cap("the consistency level: each request picks its own count"), 0.6),
            "ONE waits",
            (lambda: self.cap("ONE = 1", WHITE), 0.4),
            "QUORUM waits",
            (lambda: self.cap("ONE = 1      QUORUM = 2 of 3", WHITE), 0.4),
            "ALL waits",
            (lambda: self.cap("ONE = 1      QUORUM = 2 of 3      ALL = 3", WHITE), 0.4),
        ])
        self.steps("And here's the catch. Out of the box, Cassandra's shell starts at ONE. So until you choose, you're the café.", [
            "starts at ONE",
            (lambda: [*self.cap("the default: ONE, so R = 1 and W = 1", RED_M), *self.set_pn("100.00", RED_M), *self.set_row(2, "W", "1", GOLD_M), *self.set_row(3, "R", "1", GREEN_M),
                      *self.set_sum("2", False)], 0.7),
            "you're the café",
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.25)], 0.8),
        ], after=0.5)
        self.steps("Write and read at QUORUM, and you're back to two plus two.", [
            (lambda: [*self.cap("write and read at QUORUM: 2 + 2 > 3", GREEN_M), *self.set_row(2, "W", "2", GOLD_M), *self.set_row(3, "R", "2", GREEN_M),
                      *self.set_sum("4", True)], 0.7),
            (lambda: self.set_pn("70.00", GREEN_M), 0.4),
        ])
        self.steps("One more limit. Counting copies isn't a transaction. If two people write the same balance at the same moment, "
                   "the later time wins, and the other write is gone without an error. That's the next lesson.", [
            "One more limit",
            (lambda: self.cap("the limit: two writes at the same moment", RED_M), 0.5),
            "the later time wins",
            (lambda: self.cap("the later time wins; the other write is gone, without an error", RED_M), 0.6),
        ], after=0.5)

        # ---------------- scene 9: moral, and a check ----------------
        qm2 = T("?", 30, YELLOW_M).move_to(PH + [PH_W / 2 + 0.4, 0.4, 0])
        self.steps("So, what did OK mean? It meant W copies have the write. Whether your read sees it depends on R. "
                   "Keep R plus W above N, and the two groups have to meet.", [
            (lambda: [*self.cap("what did OK mean?", WHITE), FadeIn(qm2)], 0.5),
            "It meant W",
            (lambda: [Indicate(self.rows[2], color=GOLD_M, scale_factor=1.1), *self.cap("OK: W copies have the write", GOLD_M)], 0.7),
            "depends on R",
            (lambda: [Indicate(self.rows[3], color=GREEN_M, scale_factor=1.1), *self.cap("seeing it: depends on R", GREEN_M)], 0.7),
            "Keep R plus W",
            (lambda: [FadeOut(qm2), Indicate(self.rows[4], color=YELLOW_M, scale_factor=1.1),
                      *self.cap("keep R + W above N, and the groups must meet", YELLOW_M)], 0.8),
        ], after=0.6)
        self.steps("One quick check. Writes wait for one clerk. How many clerks must a read ask, to be sure it sees the write? Pause and think.", [
            (lambda: [*self.uncap(), *self.set_row(2, "W", "1", GOLD_M), *self.set_row(3, "R", "?", GREEN_M), *self.set_sum("?", None),
                      *self.set_val(1, "100.00 @ t1", RED_M), *self.has_write(1, False) ], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.pr = VGroup(*[read_ring(i) for i in range(3)])
        self.steps("All three. One plus three is four, more than three. Any fewer, and the read could miss the one clerk who has it.", [
            (lambda: [*self.uncap(), *self.set_row(3, "R", "3", GREEN_M), *self.set_sum("4", True), FadeIn(self.pr)], 0.7),
            "Any fewer",
            (lambda: [glow(self.boxes[0][0], YELLOW_M, 1.04)], 0.8),
        ], after=0.3)
        self.play(*self.cap("R + W > N: the read and the write must meet", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
