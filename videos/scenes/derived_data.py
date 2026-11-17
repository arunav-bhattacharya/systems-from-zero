from sfz import *

# Amounts are said the way people say them ("forty-nine"); captions keep "49.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
NB_X0, NB_X1, NB_TOP, NB_BOT = -6.45, -1.65, 2.45, -1.95          # the notebook: the record
NB_CX, NB_CY = (NB_X0 + NB_X1) / 2, (NB_TOP + NB_BOT) / 2
ROW_Y = [1.05 - 0.6 * i for i in range(5)]
IX_X0, IX_X1, IX_TOP, IX_BOT = 0.15, 3.45, 2.5, 0.75              # the index at the back
IX_CX, IX_CY = (IX_X0 + IX_X1) / 2, (IX_TOP + IX_BOT) / 2
IXR_Y = [IX_TOP - 0.9, IX_TOP - 1.33]
NOTE_C, NOTE_W, NOTE_H = np.array([1.8, -0.75, 0]), 2.6, 2.1     # the sticky note: the cache
NT_X0, NT_X1 = NOTE_C[0] - NOTE_W / 2, NOTE_C[0] + NOTE_W / 2
NT_TOP, NT_BOT = NOTE_C[1] + NOTE_H / 2, NOTE_C[1] - NOTE_H / 2
PH_C, PH_W, PH_H = np.array([5.2, -0.75, 0]), 1.7, 3.0           # the owner's phone
PH_X0 = PH_C[0] - PH_W / 2
CAP_Y, BAR_Y, CHIP_Y = -3.2, -2.78, 3.15
HOOK = 1.5                                                        # the phone's size in the opening

ROWS = [("1", "4417", "", "40.00"), ("2", "8802", "", "9.00"), ("3", "4417", "refund", "-40.00")]
COFFEE = "#8B5A2B"


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def harrow(x0, x1, y, color=GREY_B):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.15)


def dot_run(arrow, color=YELLOW_M, frac=1.0, keep=False):
    """A dot that runs along an arrow (part of the way if frac < 1)."""
    a, b = arrow.get_start(), arrow.get_end()
    d = Dot(radius=0.08, color=color).move_to(a)
    seq = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=0.8)]
    if not keep:
        seq.append(FadeOut(d, run_time=0.15))
    return d, Succession(*seq)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def run(arrow, color=YELLOW_M):
    return dot_run(arrow, color)[1]


# ---- the pieces ----
def notebook():
    r = RoundedRectangle(corner_radius=0.14, width=NB_X1 - NB_X0, height=NB_TOP - NB_BOT, stroke_color=BLUE_M,
                         stroke_width=3).set_fill(fillc(BLUE_M), 1).move_to([NB_CX, NB_CY, 0])
    rings = VGroup(*[Circle(radius=0.075, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLACK, 1).move_to([NB_X0, y, 0])
                     for y in np.arange(NB_TOP - 0.45, NB_BOT + 0.3, -0.55)])
    title = left_at(T("notebook", 26), NB_X0 + 0.45, NB_TOP - 0.38)
    cols = VGroup(T("#", 16, GREY_B).move_to([NB_X0 + 0.45, 1.6, 0]), left_at(T("card", 16, GREY_B), NB_X0 + 0.95, 1.6),
                  right_at(T("amount", 16, GREY_B), NB_X1 - 0.3, 1.6))
    head = Line([NB_X0 + 0.25, 1.37, 0], [NB_X1 - 0.2, 1.37, 0], stroke_width=1.5, color=GREY_C)
    rules = VGroup(*[Line([NB_X0 + 0.25, y - 0.3, 0], [NB_X1 - 0.2, y - 0.3, 0], stroke_width=1.2, color=GREY_D) for y in ROW_Y])
    margin = Line([NB_X0 + 0.72, 1.37, 0], [NB_X0 + 0.72, NB_BOT + 0.15, 0], stroke_width=1.2, color=GREY_D)
    return VGroup(r, rings, title, cols, head, rules, margin)


def nrow(i):
    n, card, kind, amt = ROWS[i]
    y = ROW_Y[i]
    c = GOLD_M if kind else WHITE
    g = VGroup(T(n, 20, GREY_B).move_to([NB_X0 + 0.45, y, 0]), left_at(M(card, 22), NB_X0 + 0.95, y),
               right_at(M(amt, 22, c), NB_X1 - 0.3, y))
    if kind:
        g.add(left_at(M(kind, 22, c), NB_X0 + 2.0, y))
    return g


def chip(i):
    n, card, kind, amt = ROWS[i]
    t = M(f"{card}  {kind + '  ' if kind else ''}{amt}", 22, GOLD_M if kind else WHITE)
    r = RoundedRectangle(corner_radius=0.1, width=t.width + 0.45, height=0.5, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).move_to([NB_CX, CHIP_Y, 0])


def cursor(i):
    x0, x1 = NB_X0 + 0.25, NB_X1 - 0.12
    return RoundedRectangle(corner_radius=0.08, width=x1 - x0, height=0.44, stroke_color=YELLOW_M, stroke_width=4).move_to(
        [(x0 + x1) / 2, ROW_Y[i], 0])


def index_box():
    r = RoundedRectangle(corner_radius=0.14, width=IX_X1 - IX_X0, height=IX_TOP - IX_BOT, stroke_color=TEAL_M,
                         stroke_width=3).set_fill(fillc(TEAL_M), 1).move_to([IX_CX, IX_CY, 0])
    return VGroup(r, left_at(T("index", 26), IX_X0 + 0.3, IX_TOP - 0.38), right_at(T("at the back", 18, GREY_B), IX_X1 - 0.25, IX_TOP - 0.38))


def ixrow(k, card, lines, color=WHITE):
    y = IXR_Y[k]
    return VGroup(left_at(M(card, 20), IX_X0 + 0.35, y), left_at(M(lines, 20, color), IX_X0 + 1.3, y))


def sticky():
    f = 0.38
    body = Polygon([NT_X0, NT_TOP, 0], [NT_X1, NT_TOP, 0], [NT_X1, NT_BOT + f, 0], [NT_X1 - f, NT_BOT, 0], [NT_X0, NT_BOT, 0],
                   stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1)
    fold = Polygon([NT_X1, NT_BOT + f, 0], [NT_X1 - f, NT_BOT + f, 0], [NT_X1 - f, NT_BOT, 0], stroke_color=TEAL_M,
                   stroke_width=2).set_fill(fillc(TEAL_M, 0.32), 1)
    return VGroup(body, fold, T("sticky note", 22).move_to([NOTE_C[0], NT_TOP - 0.32, 0]),
                  T("balance", 20, GREY_B).move_to([NOTE_C[0], NT_TOP - 0.74, 0]))


def note_num(s, color=WHITE):
    return M(s, 40, color).move_to([NOTE_C[0] - 0.1, NOTE_C[1] - 0.45, 0])


def phone():
    body = RoundedRectangle(corner_radius=0.25, width=PH_W, height=PH_H, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(PH_C)
    screen = RoundedRectangle(corner_radius=0.12, width=PH_W - 0.24, height=PH_H - 0.62, stroke_width=0).set_fill("#15191d", 1)
    screen.move_to(PH_C + 0.02 * DOWN)
    slot = Line(PH_C + [-0.2, PH_H / 2 - 0.15, 0], PH_C + [0.2, PH_H / 2 - 0.15, 0], stroke_width=3, color=GREY_C)
    return VGroup(body, screen, slot, T("café app", 18, GREY_B).move_to(PH_C + [0, 0.85, 0]), T("balance", 18).move_to(PH_C + [0, 0.1, 0]))


def ph_num(s, color=WHITE):
    return M(s, 30, color).move_to(PH_C + [0, -0.45, 0])


def coffee():
    c = NOTE_C + [-0.1, -0.45, 0]
    blob = Union(*[Circle(radius=r).move_to(c + [x, y, 0]) for r, x, y in
                   [(0.5, 0, 0), (0.4, -0.55, 0.08), (0.38, 0.55, -0.05), (0.2, 0.25, 0.25), (0.16, -0.2, -0.38)]])
    blob.set_fill(COFFEE, 1).set_stroke("#B07A43", 2)
    drops = VGroup(*[Circle(radius=r, stroke_width=0).set_fill(COFFEE, 0.95).move_to(c + [x, y, 0])
                     for r, x, y in [(0.09, 0.95, 0.3), (0.07, -1.0, -0.3), (0.06, 0.8, -0.45)]])
    return VGroup(blob, drops)


def mark(ok, at):
    """A tick, a cross, or (ok=None) a question mark, at a point beside a box."""
    if ok is None:
        return T("?", 34, YELLOW_M).move_to(at)
    return tick(ok, 0.17).move_to(at)


M_NB = np.array([NB_X1 + 0.35, NB_TOP - 0.38, 0])   # where each box's mark sits
M_IX = np.array([IX_X1 + 0.35, IX_TOP - 0.38, 0])
M_NT = np.array([NT_X1 + 0.35, NT_TOP - 0.3, 0])
M_PH = np.array([PH_C[0], PH_C[1] + PH_H / 2 + 0.38, 0])


class DerivedData(Base):
    """found-01, section 1. The café's app shows 49.00, but a 40.00 refund means the balance is 9.00. A paper notebook
    (the record) with an index at the back and a sticky note by the till (copies worked out from it). Which can be
    thrown away and rebuilt? Only the copies: system of record vs derived data. The refund reached the file and the
    index, but the message to the cache was lost, so it went stale. Typing 9.00 over it, and the idea behind that,
    fail; replaying the record rebuilds every copy. Habits, cost, moral, and a check question."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_nn(self, s, color=WHITE):
        new = note_num(s, color)
        old, self.nn = self.nn, new
        return [swap(old, new)]

    def clear_nn(self):
        old, self.nn = self.nn, None
        return [FadeOut(old)] if old is not None else []

    def set_pn(self, s, color=WHITE):
        new = ph_num(s, color)
        old, self.pn = self.pn, new
        return [swap(old, new)]

    def set_ix(self, k, card, lines, color=WHITE):
        new = ixrow(k, card, lines, color)
        old, self.ix[k] = self.ix[k], new
        return [swap(old, new, RIGHT)]

    def clear_ix(self):
        olds = [r for r in self.ix if r is not None]
        self.ix = [None, None]
        return [FadeOut(r) for r in olds]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.nn = self.pn = None
        self.ix = [None, None]
        self.title_card("Which number is true?", "a record, its copies, and the right way to fix a copy")

        # ---------------- scene 1: the symptom ----------------
        ph = phone()
        self.pn = ph_num("49.00")
        hook = VGroup(ph, self.pn)
        hook.scale(HOOK).move_to([0, 0.25, 0])
        self.steps("Picture a busy café. In the morning, the owner opens the café's app on her phone.", [
            "In the morning",
            (lambda: [FadeIn(ph, shift=0.2 * UP)], 0.8),
            "on her phone",
            (lambda: [FadeIn(self.pn)], 0.5),
        ])
        self.steps("Her balance, the money her card sales have brought in, says 49.00.", [
            "says",
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.15)], 0.9),
        ])
        slip = RoundedRectangle(corner_radius=0.12, width=2.6, height=1.85, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1)
        slip.move_to([-4.3, 0.25, 0])
        slip_t = VGroup(T("refund", 22, GOLD_M), M("-40.00", 30, GOLD_M), T("an hour ago", 18, GREY_B)).arrange(DOWN, buff=0.18).move_to(slip)
        should = VGroup(T("should be", 22, GREY_B), M("9.00", 40, GREEN_M)).arrange(DOWN, buff=0.18).move_to([4.3, 0.25, 0])
        self.steps("But an hour ago, she refunded a 40.00 order. So the balance should be 9.00.", [
            "she refunded",
            (lambda: [FadeIn(VGroup(slip, slip_t), shift=0.2 * RIGHT)], 0.8),
            "So the balance",
            (lambda: [FadeIn(should, shift=0.2 * LEFT)], 0.8),
        ])
        qm = T("?", 64, YELLOW_M).move_to([0, 3.1, 0])
        self.steps("Same app, same payments, two answers. Which one is true? And how do you fix the other one?", [
            "two answers",
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.12), Indicate(should[1], color=GREEN_M, scale_factor=1.12)], 0.9),
            "Which one",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])
        orig = self.pn.copy()
        caret = Line(UP * 0.28, DOWN * 0.28, stroke_width=4, color=PURPLE_M)
        self.steps("The tempting fix is to type 9.00 over the 49.00. It's the number everyone sees, so it feels like the real one. "
                   "Hold that thought.", [
            "type 9.00",
            (lambda: [Transform(self.pn, M("9.00", 30 * HOOK, PURPLE_M).move_to(self.pn)), *self.cap("type 9.00 over it?", PURPLE_M)], 0.6),
            (lambda: [FadeIn(caret.next_to(self.pn, RIGHT, buff=0.12))], 0.2),
            (lambda: [caret.animate(rate_func=there_and_back).set_opacity(0)], 0.5),
            (lambda: [caret.animate(rate_func=there_and_back).set_opacity(0)], 0.5),
            "Hold that",
            (lambda: [FadeOut(caret), Transform(self.pn, orig)], 0.6),
        ])

        # ---------------- scene 2: the notebook ----------------
        nb = notebook()
        self.steps("To see which is true, picture the café without the app. It keeps a paper notebook by the till.", [
            (lambda: [FadeOut(VGroup(slip, slip_t, should, qm)), *self.uncap(),
                      hook.animate.scale(1 / HOOK).move_to(PH_C).set_opacity(0.18)], 1.2),
            "It keeps",
            (lambda: [FadeIn(nb, shift=0.15 * UP)], 1.0),
        ])
        rows = [nrow(i) for i in range(3)]
        chips = [chip(i) for i in range(3)]

        def drop(i):
            return [
                (lambda: [FadeIn(chips[i], shift=0.25 * DOWN)], 0.4),
                (lambda: [chips[i].animate.move_to([NB_CX, NB_TOP + 0.32, 0]).set_opacity(0), FadeIn(rows[i], shift=0.1 * DOWN)], 0.55),
            ]

        self.steps("Every sale goes on the next empty line: which card paid, and how much. Nothing is ever rubbed out.", [
            *drop(0),
            "which card",
            *drop(1),
            "Nothing is ever",
            (lambda: [LaggedStart(*[Indicate(r, color=BLUE_M, scale_factor=1.04) for r in rows[:2]], lag_ratio=0.4)], 1.0),
        ])
        ixb = index_box()
        a_ix = harrow(NB_X1 + 0.08, IX_X0 - 0.08, IX_CY)
        self.steps("Two helpers grow around it. At the back, an index: each card, and the lines it's on.", [
            "At the back",
            (lambda: [GrowArrow(a_ix), FadeIn(ixb, shift=0.1 * RIGHT)], 0.8),
            "each card",
            (lambda: [run(a_ix)], 0.6),
            (lambda: [*self.set_ix(0, "4417", "line 1"), *self.set_ix(1, "8802", "line 2")], 0.5),
        ])
        note = sticky()
        a_nt = harrow(NB_X1 + 0.08, NT_X0 - 0.08, NOTE_C[1])
        self.steps("And by the till, a sticky note with the balance, so nobody adds up the notebook every time someone asks.", [
            "a sticky note",
            (lambda: [GrowArrow(a_nt), FadeIn(note, shift=0.1 * RIGHT)], 0.8),
            (lambda: [run(a_nt)], 0.6),
            (lambda: self.set_nn("49.00"), 0.4),
        ])
        cof = coffee()
        self.steps("Now, this is a café. Sooner or later, coffee lands on the sticky note.", [
            "coffee lands",
            (lambda: [FadeIn(cof, shift=0.9 * DOWN, scale=0.5), self.nn.animate.set_opacity(0.08)], 0.45),
        ], after=0.4)
        cur = cursor(0)
        self.steps("Does the owner panic? No. She adds up the notebook and writes a new note.", [
            "She adds up",
            (lambda: [FadeOut(cof), *self.clear_nn(), Create(cur)], 0.5),
            (lambda: [run(a_nt)], 0.55),
            (lambda: self.set_nn("40.00"), 0.3),
            (lambda: [cur.animate.move_to(cursor(1))], 0.35),
            (lambda: [run(a_nt)], 0.55),
            (lambda: self.set_nn("49.00"), 0.3),
            (lambda: [FadeOut(cur)], 0.3),
        ])
        back = Arrow([NT_X0 - 0.08, NOTE_C[1] - 0.55, 0], [NB_X1 + 0.08, NOTE_C[1] - 0.55, 0], buff=0, stroke_width=3,
                     color=RED_M, max_tip_length_to_length_ratio=0.15)
        no = tick(False, 0.16).move_to(back.get_center())
        self.steps("She'd never do it the other way round, and change the notebook to match the note.", [
            "the other way",
            (lambda: [GrowArrow(back)], 0.6),
            (lambda: [Create(no)], 0.4),
            1.0,
            (lambda: [FadeOut(back), FadeOut(no)], 0.5),
        ])

        # ---------------- scene 3: the app works the same way ----------------
        file_lab = right_at(T("the payments file", 18, BLUE_M), NB_X1 - 0.25, NB_TOP - 0.38)
        self.steps("The app works the same way. The program behind the card reader adds each payment as a line at the end of a file. "
                   "That file is the notebook, and the app keeps an index too.", [
            (lambda: [hook.animate.set_opacity(1)], 0.8),
            "That file is",
            (lambda: [FadeIn(file_lab, shift=0.1 * LEFT), glow(nb[0], BLUE_M, 1.02)], 0.8),
            "an index too",
            (lambda: [glow(ixb[0], TEAL_M, 1.03)], 0.7),
        ])
        a_ph = harrow(NT_X1 + 0.08, PH_X0 - 0.08, NOTE_C[1])
        cache_lab = T("the cache", 20, TEAL_M).move_to([NOTE_C[0], NT_BOT - 0.33, 0])
        self.steps("And the balance on her phone? The app doesn't add up the file each time. It reads a saved answer, its sticky note. "
                   "A saved answer like that is called a cache.", [
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.15)], 0.8),
            "It reads",
            (lambda: [GrowArrow(a_ph)], 0.5),
            (lambda: [run(a_ph, WHITE)], 0.7),
            "called a cache",
            (lambda: [FadeIn(cache_lab, shift=0.1 * UP), glow(note[0], TEAL_M, 1.03)], 0.8),
        ])
        self.steps("Why keep copies at all? Adding up millions of lines every time is slow. Each copy makes one question fast.", [
            (lambda: self.cap("why keep copies at all?"), 0.5),
            "Adding up",
            (lambda: self.cap("adding up millions of lines, every time: slow"), 0.5),
            "Each copy",
            (lambda: [*self.cap("each copy makes one question fast"), glow(ixb[0], TEAL_M, 1.03), glow(note[0], TEAL_M, 1.03)], 0.9),
        ])

        # ---------------- scene 4: the test, and the names ----------------
        qs = [mark(None, M_IX), mark(None, M_NT), mark(None, M_NB)]
        self.steps("So which of these is the truth? Here's a test. If a box were thrown away, could we get it back? Pause and guess.", [
            (lambda: self.uncap(), 0.4),
            "If a box",
            (lambda: [LaggedStart(*[FadeIn(q, scale=0.5) for q in qs], lag_ratio=0.35)], 1.2),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        oks = [mark(True, M_IX), mark(True, M_NT), mark(False, M_NB)]
        self.steps("The index: yes. Read the notebook again. The sticky note: yes. We saw the owner do it.", [
            (lambda: [*self.uncap(), FadeOut(qs[0]), Create(oks[0]), *self.clear_ix()], 0.5),
            "Read the notebook",
            (lambda: [run(a_ix)], 0.6),
            (lambda: [*self.set_ix(0, "4417", "line 1"), *self.set_ix(1, "8802", "line 2")], 0.4),
            "The sticky note",
            (lambda: [FadeOut(qs[1]), Create(oks[1])], 0.5),
        ])
        self.steps("The notebook: no. The note knows one number, not which payments made it. Lose the notebook, and those payments are gone.", [
            (lambda: [FadeOut(qs[2]), Create(oks[2])], 0.5),
            "The note knows",
            (lambda: [Indicate(self.nn, color=TEAL_M, scale_factor=1.15)], 0.8),
            "Lose the notebook",
            (lambda: [*[r.animate.set_opacity(0.12) for r in rows[:2]], nb[0].animate.set_stroke(RED_M)], 0.8),
        ])
        sor = T("system of record", 24, BLUE_M).move_to([NB_CX, NB_BOT - 0.4, 0])
        self.steps("The notebook is the system of record, also called the source of truth. Each fact is written there first, and once. "
                   "When anything disagrees with it, the record wins.", [
            (lambda: [FadeOut(VGroup(*oks)), *[r.animate.set_opacity(1) for r in rows[:2]], nb[0].animate.set_stroke(BLUE_M)], 0.6),
            "system of record",
            (lambda: [FadeIn(sor, shift=0.1 * UP)], 0.6),
            "also called",
            (lambda: self.cap("also called: the source of truth"), 0.5),
            "the record wins",
            (lambda: [glow(nb[0], BLUE_M, 1.02)], 0.8),
        ])
        der = T("derived data", 24, TEAL_M).move_to([IX_CX, IX_TOP + 0.38, 0])
        self.steps("The index and the cache are derived data: worked out from the record, so they can be thrown away and worked out again.", [
            (lambda: self.uncap(), 0.3),
            "derived data",
            (lambda: [FadeIn(der, shift=0.1 * DOWN)], 0.6),
            "worked out from",
            (lambda: [run(a_ix), run(a_nt)], 0.8),
            "thrown away",
            (lambda: [glow(ixb[0], TEAL_M, 1.03), glow(note[0], TEAL_M, 1.03)], 0.9),
        ])

        # ---------------- scene 5: the lost message ----------------
        def stream():
            return [LaggedStart(*[run(a) for a in (a_ix, a_nt, a_ph) for _ in range(4)], lag_ratio=0.12)]

        self.steps("So how did the app get 49.00? Here the café picture stops working. The owner updated her note by hand. "
                   "The program updates its copies on its own, thousands of times a second.", [
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.15)], 0.8),
            "Here the café",
            (lambda: self.cap("where the café picture stops working"), 0.5),
            "The owner updated",
            (lambda: self.cap("the owner: by hand, now and then"), 0.5),
            "The program updates",
            (lambda: self.cap("the program: on its own, thousands of times a second"), 0.5),
            (lambda: stream(), 2.2),
        ])
        msg_dot, msg_go = dot_run(a_nt, YELLOW_M, frac=0.5, keep=True)
        forget = T("forget", 18, YELLOW_M).move_to(a_nt.get_center() + 0.32 * UP)
        lost_x = tick(False, 0.15).move_to(a_nt.get_center())
        lost = T("lost", 20, RED_M).move_to(a_nt.get_center() + 0.32 * UP)
        self.steps("Watch the refund. It goes into the file first, as a new line. Then the program updates each copy. The index adds line 3.", [
            (lambda: self.uncap(), 0.3),
            "It goes into",
            *drop(2),
            "updates each copy",
            (lambda: [run(a_ix)], 0.7),
            "The index adds",
            (lambda: self.set_ix(0, "4417", "lines 1, 3"), 0.5),
            (lambda: [Indicate(self.ix[0][1], color=TEAL_M, scale_factor=1.1)], 0.6),
        ])
        stale_lab = T("the cache: stale", 20, RED_M).move_to(cache_lab)
        self.steps("The cache gets a short message: forget your saved balance. But that message got lost on the way. "
                   "So the cache kept handing out 49.00.", [
            "a short message",
            (lambda: [FadeIn(forget, shift=0.1 * UP), msg_go], 0.9),
            "got lost",
            (lambda: [FadeOut(msg_dot, scale=1.8), Create(lost_x), FadeOut(forget), FadeIn(lost)], 0.6),
            "So the cache kept",
            (lambda: [run(a_ph, WHITE)], 0.7),
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.15)], 0.7),
        ])
        self.steps("A copy that missed the newest record is called stale. And nothing on the screen says so. "
                   "A stale 49.00 looks just as sure of itself as 9.00.", [
            "called stale",
            (lambda: [note[0].animate.set_stroke(RED_M), note[1].animate.set_stroke(RED_M), swap(cache_lab, stale_lab),
                      *self.cap("stale: a copy that missed the newest record", RED_M)], 0.8),
            "nothing on the screen",
            (lambda: [Indicate(self.pn, color=WHITE, scale_factor=1.15)], 0.8),
        ])

        # ---------------- scene 6: the tempting fix, tested ----------------
        self.steps("Now, the tempting fix. Type 9.00 over the note. To be fair, the phone now shows the right number.", [
            (lambda: self.cap("type 9.00 over the note, by hand", PURPLE_M), 0.5),
            "Type 9.00",
            (lambda: self.set_nn("9.00", PURPLE_M), 0.6),
            "the phone now",
            (lambda: [run(a_ph, PURPLE_M)], 0.7),
            (lambda: self.set_pn("9.00", PURPLE_M), 0.5),
        ])
        sweep = cursor(0)
        self.steps("But where did you get 9.00? You added up the notebook. So the notebook was the judge all along. "
                   "Typing it in is a rebuild done by hand, for the one number you happened to spot.", [
            "You added up",
            (lambda: [*self.cap("40.00 + 9.00 - 40.00 = 9.00, added up from the notebook"), Create(sweep)], 0.5),
            (lambda: [sweep.animate.move_to(cursor(1))], 0.4),
            (lambda: [sweep.animate.move_to(cursor(2))], 0.4),
            (lambda: [FadeOut(sweep)], 0.3),
            "the judge",
            (lambda: [glow(nb[0], BLUE_M, 1.02)], 0.8),
            "for the one number",
            (lambda: [lost_x.animate(rate_func=there_and_back).scale(1.6), Indicate(lost, color=RED_M)], 0.8),
        ])
        strike = Line([NB_X0 + 0.85, ROW_Y[2], 0], [NB_X1 - 0.2, ROW_Y[2], 0], stroke_width=3, color=GREY_B)
        agree = [mark(True, M_NB), mark(True, M_NT), mark(True, M_PH)]
        gone = left_at(T("a customer's refund: gone", 20, RED_M), NB_X0 + 0.95, ROW_Y[3])
        self.steps("And follow the idea underneath, that the screen is the truth. Then the notebook must be wrong, so rub out the refund. "
                   "Now everything agrees on 49.00, and a customer's refund has vanished.", [
            (lambda: self.cap("if the screen is the truth...", GREY_B), 0.5),
            "Then the notebook",
            (lambda: [*self.set_nn("49.00"), *self.set_pn("49.00")], 0.6),
            "rub out",
            (lambda: [Create(strike)], 0.4),
            (lambda: [rows[2].animate.set_opacity(0.12), strike.animate.set_opacity(0.3)], 0.6),
            "Now everything",
            (lambda: [LaggedStart(*[Create(a) for a in agree], lag_ratio=0.3), *self.uncap()], 0.9),
            "a customer's",
            (lambda: [FadeIn(gone, shift=0.1 * UP)], 0.6),
        ])
        self.steps("Well... that's not the fix we wanted.", [
            0.3,
            (lambda: [*[a.animate.set_stroke(GREY_D) for a in agree]], 0.6),
        ], after=0.5)

        # ---------------- scene 7: rebuild from the record ----------------
        rs = cursor(0)
        self.steps("Let's undo that, and do what the owner did after the coffee. Throw the copies away. "
                   "Nothing is lost, because the file hasn't changed.", [
            (lambda: [FadeOut(gone), FadeOut(strike), FadeOut(VGroup(*agree)), rows[2].animate.set_opacity(1)], 0.7),
            "Throw the copies",
            (lambda: [*self.clear_ix(), *self.clear_nn(), FadeOut(self.pn), FadeOut(lost_x), FadeOut(lost),
                      note[0].animate.set_stroke(TEAL_M), note[1].animate.set_stroke(TEAL_M),
                      swap(stale_lab, T("the cache", 20, TEAL_M).move_to(cache_lab))], 0.8),
            "Nothing is lost",
            (lambda: [glow(nb[0], BLUE_M, 1.02)], 0.8),
        ])
        self.pn = None

        def feed(i):
            return [run(a_ix), run(a_nt)]

        line = "Read the file from the first line, in order, and work each copy out again. 40.00. 49.00. And the refund: 9.00."
        self.steps(line, [
            "the first line",
            (lambda: [Create(rs)], 0.4),
            "work each copy",
            (lambda: feed(0), 0.6),
            (lambda: self.set_ix(0, "4417", "line 1"), 0.3),
            "40.00. 49",
            (lambda: self.set_nn("40.00"), 0.3),
            (lambda: [rs.animate.move_to(cursor(1))], 0.3),
            (lambda: feed(1), 0.5),
            "49.00. And",
            (lambda: [*self.set_nn("49.00"), *self.set_ix(1, "8802", "line 2")], 0.3),
            (lambda: [rs.animate.move_to(cursor(2))], 0.3),
            (lambda: feed(2), 0.5),
            ": 9.00",
            (lambda: [*self.set_nn("9.00", GREEN_M), *self.set_ix(0, "4417", "lines 1, 3")], 0.3),
            (lambda: [run(a_ph, GREEN_M)], 0.6),
            (lambda: self.set_pn("9.00", GREEN_M), 0.3),
        ])
        done = [mark(True, M_IX), mark(True, M_NT), mark(True, M_PH)]
        self.steps("That's called replaying the record. The rebuild didn't need to know what went wrong, and nobody typed a number.", [
            (lambda: [FadeOut(rs), *self.cap("replaying: reading the record from the start, in order")], 0.6),
            "nobody typed",
            (lambda: [LaggedStart(*[Create(d) for d in done], lag_ratio=0.3)], 0.9),
        ], after=0.6)

        # ---------------- scene 8: two habits, and a cost ----------------
        self.steps("Two habits keep this safe. Write the record first and the copies second. If the power cuts out in between, "
                   "a copy is only behind, and a replay catches it up.", [
            (lambda: [FadeOut(VGroup(*done)), *self.uncap()], 0.5),
            "Write the record",
            (lambda: [*self.cap("1. the record first, then the copies", WHITE), glow(nb[0], BLUE_M, 1.02)], 0.8),
            (lambda: [run(a_ix), run(a_nt)], 0.8),
            "If the power",
            (lambda: self.cap("a power cut in between leaves a copy behind; a replay catches it up", WHITE), 0.5),
        ])
        self.steps("And never rub out a line. A rebuild is only as good as the record it reads.", [
            (lambda: self.cap("2. never rub out a line", WHITE), 0.5),
            (lambda: [LaggedStart(*[Indicate(r, color=BLUE_M, scale_factor=1.04) for r in rows], lag_ratio=0.3)], 1.4),
        ])
        sw = cursor(0)
        self.steps("One cost: a rebuild reads the whole record. Three lines take no time. Years of payments can take hours.", [
            (lambda: [*self.cap("the cost: a rebuild reads every line"), Create(sw)], 0.5),
            (lambda: [sw.animate.move_to(cursor(1))], 0.35),
            (lambda: [sw.animate.move_to(cursor(2))], 0.35),
            (lambda: [FadeOut(sw)], 0.3),
            "Years of payments",
            (lambda: self.cap("three lines: no time.   years of payments: hours."), 0.5),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, 49.00 or 9.00? Every copy is worked out from the notebook, and the notebook says 9.00. "
                   "It wins, even when the sticky note has nicer handwriting.", [
            (lambda: self.cap("49.00 or 9.00?", WHITE), 0.5),
            "Every copy",
            (lambda: [run(a_ix), run(a_nt)], 0.8),
            (lambda: [run(a_ph, GREEN_M)], 0.6),
            "the notebook says",
            (lambda: [glow(nb[0], BLUE_M, 1.02), Indicate(self.pn, color=GREEN_M, scale_factor=1.15),
                      *self.cap("the notebook says 9.00, and the notebook wins", BLUE_M)], 0.9),
            "nicer handwriting",
            (lambda: [Wiggle(VGroup(note, self.nn), scale_value=1.04, rotation_angle=0.03 * TAU)], 0.9),
        ])
        self.steps("A copy that disagrees with the record is wrong. Rebuild it, don't retype it. "
                   "And of any data you meet, ask: is this where the fact is decided, or a copy of it?", [
            (lambda: self.cap("rebuild, don't retype", YELLOW_M, 32), 0.6),
            "And of any data",
            (lambda: self.cap("is this where the fact is decided, or a copy of it?", WHITE), 0.6),
        ], after=0.6)
        slot5 = VGroup(DashedVMobject(cursor(4).set_stroke(RED_M, 2.5), num_dashes=40),
                       T("5", 20, GREY_B).move_to([NB_X0 + 0.45, ROW_Y[4], 0]), T("empty", 18, RED_M).move_to([NB_CX + 0.3, ROW_Y[4], 0]))
        self.steps("One quick check. The index says a card is on line 5, but the notebook has no line 5. "
                   "Which one is wrong, and what do you do? Pause and think.", [
            (lambda: self.uncap(), 0.4),
            "The index says",
            (lambda: self.set_ix(1, "8802", "line 5", RED_M), 0.6),
            "no line 5",
            (lambda: [Create(slot5)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        fix = cursor(0)
        self.steps("The index is wrong. Throw it away, and replay the notebook.", [
            (lambda: [*self.uncap(), FadeOut(slot5)], 0.4),
            "Throw it away",
            (lambda: [*self.clear_ix(), Create(fix)], 0.5),
            (lambda: [run(a_ix)], 0.4),
            (lambda: [*self.set_ix(0, "4417", "line 1"), fix.animate.move_to(cursor(1))], 0.35),
            (lambda: [run(a_ix)], 0.4),
            (lambda: [*self.set_ix(1, "8802", "line 2"), fix.animate.move_to(cursor(2))], 0.35),
            (lambda: [run(a_ix)], 0.4),
            (lambda: [*self.set_ix(0, "4417", "lines 1, 3"), FadeOut(fix)], 0.35),
        ], after=0.2)
        self.play(Create(mark(True, M_IX)), *self.cap("rebuild, don't retype", YELLOW_M, 32), run_time=0.7)
        self.wait(2.0)
