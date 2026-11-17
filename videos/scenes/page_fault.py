from sfz import *

SAY.insert(0, (r"\b0x1234\b", "hex one two three four"))
SAY.insert(0, (r"\b0x234\b", "hex two three four"))
SAY.insert(0, (r"\b48-bit\b", "forty-eight bit"))
SAY.insert(0, (r"\b2 to the 36\b", "two to the thirty-sixth"))
SAY.insert(0, (r"\b2 to the 12\b", "two to the twelfth"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RAM_X, RAM_W, FH, FGAP, RAM_TOP = 4.9, 2.2, 0.6, 0.07, 2.6     # RAM: 8 frames stacked, frame 0 on top
RAM_X0 = RAM_X - RAM_W / 2
NF = 8
PC = {0: np.array([-4.85, 1.5, 0]), 1: np.array([-4.85, -1.45, 0])}   # program A (payments) above, B below
PW, PH = 3.5, 2.35
PCOL = {0: BLUE_M, 1: PURPLE_M}
PNAME = {0: "the payments program", 1: "another program"}
TABLE = {0: [(0, 5), (1, 2), (2, 7)], 1: [(0, 1), (1, 6), (2, 3)]}   # page: frame
ROW_DY = [0.02, -0.4, -0.82]
SUB_DY, NAME_DY = 0.46, 0.86
CAP_Y, BAR_Y = -3.3, -2.9
ADDR_Y = 3.15


def frame_y(i):
    return RAM_TOP - FH / 2 - i * (FH + FGAP)


def frame_c(i):
    return np.array([RAM_X, frame_y(i), 0])


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

    def steps(self, text, items, after=0.2):
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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


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


def dot_run(a, b, color=YELLOW_M, rt=0.7):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def harrow(a, b, color=GREY_B, sw=2.5):
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.06, max_stroke_width_to_length_ratio=8)


# ---- the pieces ----
def ram_cells():
    return VGroup(*[RoundedRectangle(corner_radius=0.06, width=RAM_W, height=FH, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1)
                    .move_to(frame_c(i)) for i in range(NF)])


def frame_lab(i, word="frame"):
    return T(f"{word} {i}", 18, GREY_B).move_to(frame_c(i) + [-0.45, 0, 0])


def fill_frames(idx, color, label=None, a=0.35):
    """A coloured block over frames idx[0]..idx[-1] (a slice of RAM), with an optional label."""
    top, bot = frame_y(idx[0]) + FH / 2, frame_y(idx[-1]) - FH / 2
    r = RoundedRectangle(corner_radius=0.06, width=RAM_W, height=top - bot, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, a), 1)
    r.move_to([RAM_X, (top + bot) / 2, 0])
    g = VGroup(r)
    if label:
        g.add(T(label, 19).move_to(r))
    return g


def pcard(k):
    c = PC[k]
    return RoundedRectangle(corner_radius=0.12, width=PW, height=PH, stroke_color=PCOL[k], stroke_width=3).set_fill(fillc(PCOL[k]), 1).move_to(c)


def pname(k, s=None):
    return T(s or PNAME[k], 22).move_to(PC[k] + [0, NAME_DY, 0])


def psub(k, s):
    return T(s, 18, GREY_B).move_to(PC[k] + [0, SUB_DY, 0])


def prow(k, j, a="page", b="frame", color=WHITE):
    p, f = TABLE[k][j]
    return M(f"{a} {p}: {b} {f}", 18, color).move_to(PC[k] + [0, ROW_DY[j], 0])


def row_arrow(k, j):
    p, f = TABLE[k][j]
    y = PC[k][1] + ROW_DY[j]
    return harrow([PC[k][0] + PW / 2 + 0.08, y, 0], [RAM_X0 - 0.08, frame_y(f), 0], PCOL[k])


# the tree walk for 0xffff42401234
CH = ["511", "509", "18", "1", "234"]
CHB = ["9 bits", "9 bits", "9 bits", "9 bits", "12 bits"]
CHC = [TEAL_M, GOLD_M, GREEN_M, PURPLE_M, WHITE]
CH_X = [-5.25, -3.3, -1.35, 0.6, 2.45]       # where each field of the address sits
TB_X = [-5.25, -3.3, -1.35, 0.6]             # the four tables, under their fields
TB_Y, TB_W, TB_H = -0.15, 1.6, 2.5
TB_NAME = ["root", "level 1", "level 2", "level 3"]
WALK_FRAME = 2


def field(i):
    t = M(CH[i] if i < 4 else "0x234", 26, CHC[i])
    r = RoundedRectangle(corner_radius=0.08, width=max(1.1, t.width + 0.35), height=0.6, stroke_color=CHC[i], stroke_width=2.5)
    r.set_fill(fillc(CHC[i]), 1)
    g = VGroup(r, t.move_to(r))
    return g.move_to([CH_X[i], 2.45, 0])


def field_bits(i):
    return T(CHB[i], 17, GREY_B).move_to([CH_X[i], 1.92, 0])


def table(i):
    c = np.array([TB_X[i], TB_Y, 0])
    r = RoundedRectangle(corner_radius=0.1, width=TB_W, height=TB_H, stroke_color=CHC[i], stroke_width=2.5).set_fill(BLACK, 1).move_to(c)
    name = T(TB_NAME[i], 20, CHC[i]).move_to(c + [0, TB_H / 2 + 0.25, 0])
    rows = VGroup(*[Line(c + [-TB_W / 2 + 0.12, y, 0], c + [TB_W / 2 - 0.12, y, 0], stroke_width=1, color=GREY_D)
                    for y in np.arange(TB_H / 2 - 0.3, -TB_H / 2 + 0.1, -0.3)])
    foot = T("512 entries", 16, GREY_B).move_to(c + [0, -TB_H / 2 - 0.25, 0])
    return VGroup(r, rows, name, foot)


def entry(i):
    c = np.array([TB_X[i], TB_Y, 0])
    r = RoundedRectangle(corner_radius=0.05, width=TB_W - 0.2, height=0.42, stroke_color=CHC[i], stroke_width=3).set_fill(fillc(CHC[i], 0.4), 1)
    return VGroup(r, M(f"entry {CH[i]}", 16, WHITE)).move_to(c + [0, 0.15 - 0.3 * i, 0]).set_z_index(2)


class PageFault(Base):
    """os-06, section 0. Two programs keep data at the same address and each reads its own. Real RAM addresses for each
    program fail three ways; base and limit fix two and break on one unbroken slice (a JVM's 4 GB heap and 40 stacks).
    The hotel: each tour group's letter says rooms 1 to 40, and the desk's list per group says which real room each
    number means. Pages and frames (4 KB in the lab box, 16 KB on Apple Silicon), one page table per program, virtual
    addresses. The offset is the last three hex digits. A flat table would be 512 GB per program; the tree of four
    512-entry tables walks 0xffff42401234 (511, 509, 18, 1, byte 0x234). Where the hotel stops: the walk happens on every
    access. Moral and a check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Same address, different rooms", "virtual addresses and the page table")

        # ---------------- scene 1: the puzzle ----------------
        cells = ram_cells()
        ram_t = T("RAM", 24).move_to([RAM_X, RAM_TOP + 0.35, 0])
        cards = {k: pcard(k) for k in (0, 1)}
        self.steps("A computer's memory, its RAM, is one long row of bytes. Each byte has a number, its address, "
                   "and programs read and write memory by address.", [
            (lambda: [*self.put("ramt", ram_t), LaggedStart(*[FadeIn(c) for c in cells], lag_ratio=0.08)], 1.2),
            "Each byte",
            (lambda: self.cap("an address: the number of one byte in memory", WHITE), 0.6),
        ])
        hexn = T("addresses are written in hexadecimal: digits 0 to 9, then a to f", 22, GREY_B)
        self.steps("Addresses are written in hexadecimal, base 16, with the digits 0 to 9 and then a to f.", [
            (lambda: self.cap(hexn), 0.6),
        ])
        adr = {k: M("0x1234", 24, PCOL[k]).move_to(PC[k] + [0, -0.1, 0]) for k in (0, 1)}
        val = {0: M("balance: 9", 20, WHITE).move_to(PC[0] + [0, -0.62, 0]), 1: M("count: 300", 20, WHITE).move_to(PC[1] + [0, -0.62, 0])}
        self.steps("Now, something odd. Two programs on the same computer can each keep data at the very same address, 0x1234. "
                   "And each one reads back its own.", [
            (lambda: [*self.uncap(), FadeIn(cards[0], shift=0.1 * RIGHT), FadeIn(cards[1], shift=0.1 * RIGHT),
                      *self.put("n0", pname(0)), *self.put("n1", pname(1))], 0.8),
            "the very same",
            (lambda: [FadeIn(adr[0]), FadeIn(adr[1])], 0.6),
            "each one reads",
            (lambda: [FadeIn(val[0], shift=0.1 * DOWN), FadeIn(val[1], shift=0.1 * DOWN)], 0.7),
        ])
        qm = T("?", 60, YELLOW_M).move_to([-0.2, 0.0, 0])
        self.steps("How can one address hold two different things?", [
            (lambda: [FadeIn(qm, scale=0.6), Indicate(adr[0], color=BLUE_M), Indicate(adr[1], color=PURPLE_M)], 0.8),
        ], after=0.5)

        # ---------------- scene 2: real addresses ----------------
        ksl = fill_frames([7], GREY_B, "the kernel", 0.3)
        self.steps("The simplest idea: give each program a slice of the 8 gigabytes, "
                   "and let its addresses be real RAM addresses.", [
            (lambda: [FadeOut(qm), FadeOut(val[0]), FadeOut(val[1]), FadeOut(adr[0]), FadeOut(adr[1]),
                      *self.put("ramt", T("RAM, 8 GB", 24).move_to(ram_t))], 0.6),
            "a slice",
            (lambda: [FadeIn(ksl)], 0.5),
            (lambda: self.put("slA", fill_frames([0, 1, 2], BLUE_M, "payments", 0.3)), 0.5),
            (lambda: self.put("slB", fill_frames([3, 4], PURPLE_M, "another", 0.3)), 0.5),
            "real RAM",
            (lambda: self.cap("each program's addresses: real places in RAM", WHITE), 0.6),
        ])
        clash = fill_frames([0, 1], RED_M, "both want this", 0.35)
        self.steps("It breaks three ways. Two programs built to use the same addresses can't both run.", [
            (lambda: self.cap("1. two programs built for the same addresses can't both run", RED_M), 0.6),
            "can't both run",
            (lambda: [FadeIn(clash)], 0.5),
            1.0,
            (lambda: [FadeOut(clash)], 0.4),
        ])
        bad = harrow(cards[0].get_right() + [0.08, -0.6, 0], [RAM_X0 - 0.08, frame_y(4), 0], RED_M, 3)
        self.steps("A bad pointer, an address that points to the wrong place, can overwrite another program's memory, or the kernel's.", [
            (lambda: self.cap("2. a bad pointer overwrites another program's memory", RED_M), 0.6),
            "can overwrite",
            (lambda: [GrowArrow(bad)], 0.6),
            (lambda: [Indicate(self.lab["slB"][0], color=RED_M, scale_factor=1.04)], 0.7),
            "or the kernel's",
            (lambda: [Transform(bad, harrow(bad.get_start(), [RAM_X0 - 0.08, frame_y(7), 0], RED_M, 3))], 0.6),
        ])
        grow = DashedVMobject(fill_frames([3], BLUE_M, None, 0.0)[0], num_dashes=30)
        self.steps("And a program can't grow, if a neighbour sits right after it.", [
            (lambda: [FadeOut(bad), *self.cap("3. it can't grow past its neighbour", RED_M)], 0.6),
            "can't grow",
            (lambda: [Create(grow)], 0.6),
            (lambda: [Indicate(self.lab["slB"][0], color=RED_M, scale_factor=1.04)], 0.7),
            (lambda: [FadeOut(grow)], 0.4),
        ])

        # ---------------- scene 3: base and limit ----------------
        b_lab = left_at(T("base", 17, BLUE_M), RAM_X0 + RAM_W + 0.15, frame_y(0) + FH / 2)
        l_lab = left_at(T("limit", 17, BLUE_M), RAM_X0 + RAM_W + 0.15, frame_y(2) - FH / 2)
        self.steps("Next try: a base and a limit. The hardware adds the base to every address, and refuses any address past the limit. "
                   "Now every program can start at 0, and none can reach outside its slice.", [
            (lambda: self.cap("each program: a base and a limit", WHITE), 0.6),
            "adds the base",
            (lambda: [FadeIn(b_lab, shift=0.1 * LEFT)], 0.4),
            "refuses any",
            (lambda: [FadeIn(l_lab, shift=0.1 * LEFT)], 0.4),
            "start at 0",
            (lambda: [*self.put("r0", M("addresses from 0", 18).move_to(PC[0] + [0, -0.1, 0])),
                      *self.put("r1", M("addresses from 0", 18).move_to(PC[1] + [0, -0.1, 0]))], 0.6),
            "none can reach",
            (lambda: [glow(self.lab["slA"][0], BLUE_M, 1.03)], 0.7),
        ])
        jvm = left_at(T("a JVM wants 4 GB in one piece", 20, GOLD_M), -2.3, 1.05)
        self.steps("But the slice must be one unbroken run of RAM. A JVM, the program that runs Java code, "
                   "may grow its heap to 4 gigabytes.", [
            (lambda: [*self.cap("but each slice must be one unbroken run of RAM", RED_M), FadeOut(b_lab), FadeOut(l_lab)], 0.6),
            "A JVM",
            (lambda: [FadeIn(jvm, shift=0.1 * UP)], 0.6),
        ])
        gaps = VGroup(*[DashedVMobject(fill_frames([i], GREEN_M, None, 0.0)[0], num_dashes=28) for i in (5, 6)])
        gap_l = left_at(T("free, in pieces", 18, GREEN_M), RAM_X0 + RAM_W + 0.15, (frame_y(5) + frame_y(6)) / 2)
        self.steps("So it grabs one huge chunk up front. And free memory breaks into gaps, too small to use.", [
            "one huge chunk",
            (lambda: [Indicate(jvm, color=GOLD_M, scale_factor=1.08)], 0.7),
            "free memory",
            (lambda: [Create(gaps), FadeIn(gap_l)], 0.8),
        ])
        self.steps("Wouldn't it be nice if a program's memory could sit in any free scraps of RAM, "
                   "and still look like one neat run to the program?", [
            (lambda: self.cap("any scraps of RAM, that look like one neat run?", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 4: the hotel ----------------
        self.steps("A hotel solves this every week, for tour groups. Each group's letter says rooms 1 to 40.", [
            (lambda: [FadeOut(VGroup(jvm, gaps, gap_l, ksl)), *self.drop("slA", "slB", "r0", "r1"), *self.uncap(),
                      *self.put("ramt", T("the hotel's real rooms", 22).move_to(ram_t))], 0.8),
            "tour groups",
            (lambda: [*self.put("n0", pname(0, "tour group A")), *self.put("n1", pname(1, "tour group B"))], 0.6),
            "rooms 1 to 40",
            (lambda: [*self.put("r0", psub(0, "letter: rooms 1 to 40")), *self.put("r1", psub(1, "letter: rooms 1 to 40"))], 0.6),
        ])
        flabs = VGroup(*[T(f"room {100 + i}", 18, GREY_B).move_to(frame_c(i)) for i in range(NF)])
        hrows = {k: [M(f"room {p + 11}: {100 + f}", 18).move_to(PC[k] + [0, ROW_DY[j], 0]) for j, (p, f) in enumerate(TABLE[k])]
                 for k in (0, 1)}
        self.steps("The front desk keeps a list for each group, saying which real room each number means.", [
            (lambda: [LaggedStart(*[FadeIn(l) for l in flabs], lag_ratio=0.06)], 0.8),
            "keeps a list",
            (lambda: [LaggedStart(*[FadeIn(r) for k in (0, 1) for r in hrows[k]], lag_ratio=0.12)], 1.2),
        ])
        ha = {k: harrow([PC[k][0] + PW / 2 + 0.08, PC[k][1] + ROW_DY[1], 0], [RAM_X0 - 0.08, frame_y(TABLE[k][1][1]), 0], PCOL[k])
              for k in (0, 1)}
        self.steps("So two groups' room 12 are different rooms. And no guest can walk into another group's room, "
                   "because their group's list doesn't contain it.", [
            "room 12",
            (lambda: [GrowArrow(ha[0]), GrowArrow(ha[1])], 0.8),
            (lambda: [dot_run(ha[0].get_start(), ha[0].get_end(), BLUE_M), dot_run(ha[1].get_start(), ha[1].get_end(), PURPLE_M)], 0.9),
            "no guest",
            (lambda: [Indicate(hrows[1][0], color=PURPLE_M), Indicate(hrows[1][1], color=PURPLE_M), Indicate(hrows[1][2], color=PURPLE_M)], 0.9),
        ])
        self.steps("Let's map it. Each tour group is a program. The room numbers on its letter are its addresses. "
                   "The real rooms are RAM. And the desk's list is a table the hardware reads, on every single read and write.", [
            (lambda: [glow(cards[0], BLUE_M, 1.02), glow(cards[1], PURPLE_M, 1.02)], 0.7),
            "The room numbers",
            (lambda: [Indicate(self.lab["r0"], color=WHITE), Indicate(self.lab["r1"], color=WHITE)], 0.7),
            "The real rooms",
            (lambda: [*self.put("ramt", T("RAM", 24).move_to(ram_t))], 0.5),
            "the desk's list",
            (lambda: [LaggedStart(*[Indicate(r, color=YELLOW_M, scale_factor=1.1) for k in (0, 1) for r in hrows[k]], lag_ratio=0.1)], 1.0),
        ], after=0.4)

        # ---------------- scene 5: pages, frames, page tables ----------------
        frow = {k: [prow(k, j) for j in range(3)] for k in (0, 1)}
        flab2 = VGroup(*[T(f"frame {i}", 18, GREY_B).move_to(frame_c(i)) for i in range(NF)])
        self.steps("In the computer, the rooms are pieces of RAM of one fixed size, called frames. "
                   "A program's addresses are cut into pieces of the same size, called pages.", [
            (lambda: [FadeOut(ha[0]), FadeOut(ha[1])], 0.4),
            "called frames",
            (lambda: [ReplacementTransform(flabs[i], flab2[i]) for i in range(NF)], 0.7),
            "called pages",
            (lambda: [*[Transform(hrows[k][j], frow[k][j]) for k in (0, 1) for j in range(3)],
                      *self.put("r0", psub(0, "its own addresses, in pages")), *self.put("r1", psub(1, "its own addresses, in pages")),
                      *self.put("n0", pname(0)), *self.put("n1", pname(1))], 0.9),
        ])
        self.steps("4 kilobytes in the lab box, and 16 on an Apple Silicon Mac.", [
            (lambda: self.cap("one page = one frame = 4 KB in the lab box, 16 KB on an Apple Silicon Mac", WHITE), 0.6),
        ])
        arrows = {k: [row_arrow(k, j) for j in range(3)] for k in (0, 1)}
        tlab = {k: T("page table", 18, PCOL[k]).move_to(PC[k] + [PW / 2 - 0.75, -PH / 2 - 0.22, 0]) for k in (0, 1)}
        self.steps("Each program has a page table, which says which frame holds each of its pages. Any page can live in any frame.", [
            (lambda: [FadeIn(tlab[0]), FadeIn(tlab[1]), *self.uncap()], 0.5),
            "which frame holds",
            (lambda: [LaggedStart(*[GrowArrow(a) for a in arrows[0]], lag_ratio=0.3)], 1.0),
            (lambda: [LaggedStart(*[GrowArrow(a) for a in arrows[1]], lag_ratio=0.3)], 1.0),
            "Any page",
            (lambda: [LaggedStart(*[Indicate(flab2[f], color=WHITE) for k in (0, 1) for _, f in TABLE[k]], lag_ratio=0.1)], 1.0),
        ])
        self.steps("So a 1 gigabyte heap needs no unbroken gigabyte. And a program can't touch another's memory, "
                   "because the other's frames aren't in its table.", [
            (lambda: self.cap("no unbroken run needed: any page in any frame", WHITE), 0.6),
            "can't touch",
            (lambda: [*self.cap("a program reaches only the frames in its own table", WHITE),
                      *[a.animate.set_opacity(0.25) for a in arrows[1]], *[r.animate.set_opacity(0.35) for r in hrows[1]]], 0.7),
            (lambda: [LaggedStart(*[dot_run(a.get_start(), a.get_end(), BLUE_M, 0.6) for a in arrows[0]], lag_ratio=0.3)], 1.3),
        ])
        self.steps("These addresses are called virtual. Every program has its own set, and the hardware translates them "
                   "into real places in RAM.", [
            (lambda: [*[a.animate.set_opacity(1) for a in arrows[1]], *[r.animate.set_opacity(1) for r in hrows[1]],
                      *self.cap("virtual addresses: each program's own; the hardware translates them", BLUE_M)], 0.7),
            "translates",
            (lambda: [LaggedStart(*[dot_run(a.get_start(), a.get_end(), PCOL[k], 0.6) for k in (0, 1) for a in arrows[k]], lag_ratio=0.15)], 1.4),
        ])
        self.steps("So, the puzzle. Both programs use address 0x1234, which is in page 1. But their tables send page 1 to different frames.", [
            (lambda: [*self.cap("0x1234 is in page 1", WHITE), *[a.animate.set_opacity(0.2) for k in (0, 1) for j, a in enumerate(arrows[k]) if j != 1]], 0.6),
            "page 1",
            (lambda: [Indicate(hrows[0][1], color=BLUE_M), Indicate(hrows[1][1], color=PURPLE_M)], 0.7),
            "different frames",
            (lambda: [dot_run(arrows[0][1].get_start(), arrows[0][1].get_end(), BLUE_M), dot_run(arrows[1][1].get_start(), arrows[1][1].get_end(), PURPLE_M)], 0.8),
            (lambda: [Indicate(flab2[2], color=BLUE_M, scale_factor=1.3), Indicate(flab2[6], color=PURPLE_M, scale_factor=1.3)], 0.8),
        ], after=0.4)

        # ---------------- scene 6: page number and offset ----------------
        a1 = M("0x1", 34, PURPLE_M)
        a2 = M("234", 34, WHITE)
        a12 = VGroup(a1, a2).arrange(RIGHT, buff=0.04).move_to([-0.6, ADDR_Y, 0])
        b1 = T("page number", 19, PURPLE_M)
        b1.move_to([a1.get_left()[0] - 0.2 - b1.width / 2, ADDR_Y, 0])
        b2 = T("offset: the byte inside the page", 19, YELLOW_M)
        b2.move_to([a2.get_right()[0] + 0.2 + b2.width / 2, ADDR_Y, 0])
        self.steps("How does the hardware find the page? It splits the address in two. With 4 kilobyte pages, "
                   "the last three hexadecimal digits are the offset, the position inside the page.", [
            (lambda: [*self.uncap(), *[a.animate.set_opacity(1) for k in (0, 1) for a in arrows[k]], FadeIn(a12, shift=0.1 * DOWN)], 0.6),
            "the last three",
            (lambda: [a2.animate.set_color(YELLOW_M)], 0.4),
            (lambda: [FadeIn(b2, shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("Each digit is 4 bits, so that's 12 bits, and 2 to the 12 is 4,096: one page. The rest is the page number.", [
            (lambda: self.cap("3 digits × 4 bits = 12 bits;   2 to the 12 = 4,096 bytes = one page", WHITE), 0.6),
            "The rest",
            (lambda: [a2.animate.set_color(WHITE), FadeIn(b1, shift=0.1 * DOWN), Indicate(a1, color=PURPLE_M, scale_factor=1.2)], 0.7),
        ])
        self.steps("So 0x1234 is byte 0x234 of page 1.", [
            (lambda: [Indicate(hrows[0][1], color=BLUE_M), Indicate(a2, color=WHITE, scale_factor=1.2)], 0.8),
        ], after=0.5)

        # ---------------- scene 7: how big is the table? ----------------
        real = M("0xffff42401234", 34, WHITE).move_to([0, ADDR_Y, 0])
        self.steps("Real addresses are longer, like this one from the lab box. So how big is a page table, "
                   "if it's a plain list with one line for every possible page?", [
            (lambda: [FadeOut(VGroup(a12, b1, b2)), FadeIn(real, shift=0.1 * DOWN)], 0.7),
            "how big",
            (lambda: [FadeOut(VGroup(*arrows[0], *arrows[1], cards[1], *hrows[1], tlab[1])), *self.drop("r1", "n1")], 0.7),
        ])
        tall = RoundedRectangle(corner_radius=0.1, width=2.9, height=3.95, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLACK, 1).move_to([-0.6, 0.375, 0])
        tall_rows = VGroup(*[M(f"page {i}: ...", 16, GREY_B).move_to([-0.6, 1.95 - 0.4 * i, 0]) for i in range(4)],
                           M("...", 22, GREY_B).move_to([-0.6, 0.3, 0]),
                           T("a line for every page", 17, GREY_B).move_to([-0.6, -0.4, 0]),
                           M("...", 22, GREY_B).move_to([-0.6, -1.05, 0]))
        self.steps("The lab box gives each program 48-bit addresses, 256 terabytes in all. That's 2 to the 36 pages, "
                   "and each line takes 8 bytes. More or less than the machine's 8 gigabytes? Pause and guess.", [
            (lambda: [FadeIn(tall), FadeIn(tall_rows)], 0.8),
            "256 terabytes",
            (lambda: self.cap("48-bit addresses: 256 TB  =  2 to the 36 pages  (about 69 billion)", WHITE), 0.6),
            "each line takes",
            (lambda: self.cap("about 69 billion lines × 8 bytes  =  ?", WHITE), 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        big = T("512 GB, for every program", 26, RED_M).move_to([-0.6, -2.12, 0])
        self.steps("512 gigabytes. For every program. The hotel's guest list would be 64 times bigger than the hotel.", [
            (lambda: [*self.uncap(), FadeIn(big, shift=0.1 * UP), tall.animate.set_stroke(RED_M)], 0.7),
            "The hotel's",
            (lambda: [*self.cap("64 times the whole machine, just for one program's list", RED_M)], 0.6),
            (lambda: [Wiggle(VGroup(tall, tall_rows), scale_value=1.03, rotation_angle=0.02 * TAU)], 0.9),
        ], after=0.5)

        # ---------------- scene 8: the tree ----------------
        fields = [field(i) for i in range(5)]
        bits = [field_bits(i) for i in range(5)]
        tabs = [table(i) for i in range(4)]
        ents = [entry(i) for i in range(4)]
        self.steps("So the table is a tree. The 36 bits of page number split into four groups of 9.", [
            (lambda: [FadeOut(VGroup(tall, tall_rows, big, cards[0], *hrows[0], tlab[0])), *self.drop("r0", "n0"), *self.uncap()], 0.7),
            "split into four",
            (lambda: [ReplacementTransform(real, VGroup(*fields)), LaggedStart(*[FadeIn(b) for b in bits], lag_ratio=0.15)], 1.2),
        ])
        self.steps("Each group picks one of 512 entries in one small table. And 512 entries of 8 bytes fill exactly one page.", [
            "one small table",
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.1 * DOWN) for t in tabs], lag_ratio=0.2)], 1.2),
            "512 entries of",
            (lambda: self.cap("512 entries × 8 bytes = 4,096 bytes = one page", WHITE), 0.6),
        ])
        links = [harrow(ents[i].get_right() + [0.06, 0, 0], tabs[i + 1][0].get_left() + [-0.06, ents[i + 1].get_center()[1] - TB_Y, 0], CHC[i])
                 for i in range(3)]
        flink = harrow(ents[3].get_right() + [0.06, 0, 0], [RAM_X0 - 0.08, frame_y(WALK_FRAME), 0], CHC[3])
        drops = [DashedLine(fields[i].get_bottom() + [0, -0.38, 0], tabs[i][2].get_top() + [0, 0.06, 0], dash_length=0.06, stroke_width=1.5, color=CHC[i])
                 for i in range(4)]
        self.steps("The root's entry points to a level 1 table. Its entry points to level 2, then level 3, "
                   "whose entry holds the frame number.", [
            (lambda: [*self.uncap(), Create(drops[0]), FadeIn(ents[0])], 0.6),
            (lambda: [GrowArrow(links[0])], 0.5),
            "level 2",
            (lambda: [Create(drops[1]), FadeIn(ents[1]), GrowArrow(links[1])], 0.7),
            "then level 3",
            (lambda: [Create(drops[2]), FadeIn(ents[2]), GrowArrow(links[2])], 0.7),
            "holds the frame",
            (lambda: [Create(drops[3]), FadeIn(ents[3]), GrowArrow(flink)], 0.7),
            (lambda: [Indicate(flab2[WALK_FRAME], color=PURPLE_M, scale_factor=1.3)], 0.6),
        ])
        byte = Dot(radius=0.09, color=YELLOW_M).move_to(frame_c(WALK_FRAME) + [0.8, 0, 0])
        blab = M("byte 0x234", 17, YELLOW_M).move_to(frame_c(WALK_FRAME) + [-0.2, 0, 0])
        self.steps("Then the offset picks the byte, inside that frame.", [
            (lambda: [Indicate(fields[4], color=YELLOW_M, scale_factor=1.1)], 0.6),
            (lambda: [FadeIn(byte, scale=0.5), FadeOut(flab2[WALK_FRAME]), *self.put("blab", blab)], 0.6),
        ])
        self.steps("At the hotel, it's a binder with tabs. The first part of the room number picks a tab, "
                   "the next picks a page behind it, and so on.", [
            (lambda: self.cap("a binder with tabs: the first part picks a tab, the next a page behind it...", WHITE), 0.6),
            "picks a tab",
            (lambda: [glow(tabs[0][0], TEAL_M, 1.03)], 0.6),
            "picks a page",
            (lambda: [glow(tabs[1][0], GOLD_M, 1.03)], 0.6),
            "and so on",
            (lambda: [glow(tabs[2][0], GREEN_M, 1.03), glow(tabs[3][0], PURPLE_M, 1.03)], 0.7),
        ])
        self.steps("Tables exist only under addresses a program uses. So a small program needs just a few dozen kilobytes of them.", [
            (lambda: self.cap("tables exist only where something is mapped: a few dozen KB for a small program", WHITE), 0.7),
        ], after=0.4)
        self.stamp("tree")

        # ---------------- scene 9: where the hotel stops ----------------
        walk = [links[0], links[1], links[2], flink]
        self.steps("Here's where the hotel picture stops working. A desk looks a room up once, when you check in. "
                   "The hardware walks this tree on every single read and write.", [
            (lambda: self.cap("where the hotel stops: the desk looks up once; the hardware, on every access", WHITE), 0.7),
            "on every single",
            (lambda: [Succession(*[dot_run(a.get_start(), a.get_end(), YELLOW_M, 0.35) for a in walk])], 1.9),
        ])
        self.steps("Four lookups in memory, every time. That sounds slow, and it would be. Next in the lesson, the shortcut that makes it cheap.", [
            (lambda: [*self.cap("four lookups in memory, for every read and write", RED_M),
                      LaggedStart(*[Indicate(e, color=RED_M, scale_factor=1.12) for e in ents], lag_ratio=0.25)], 1.2),
            "Next in the lesson",
            (lambda: self.cap("next: the shortcut that makes it cheap", GREY_B), 0.6),
        ], after=0.4)

        # ---------------- scene 10: moral, and a check ----------------
        self.steps("So the moral of the story: an address is a room number on your own group's letter. "
                   "The page table says which real room it means.", [
            (lambda: [FadeOut(VGroup(*fields, *bits, *tabs, *ents, *links, flink, *drops, byte)), *self.drop("blab"), FadeIn(flab2[WALK_FRAME]),
                      *self.cap("an address is a room number on your own group's letter", YELLOW_M, 28)], 0.8),
            "The page table",
            (lambda: [FadeIn(cards[0]), FadeIn(cards[1]), *[FadeIn(r) for k in (0, 1) for r in hrows[k]], FadeIn(tlab[0]), FadeIn(tlab[1]),
                      *self.put("n0", pname(0)), *self.put("n1", pname(1))], 0.8),
            (lambda: [LaggedStart(*[GrowArrow(a) for k in (0, 1) for a in arrows[k]], lag_ratio=0.12)], 1.2),
        ])
        self.steps("One quick check. The payments program keeps its balance in frame 5. Another program's table has no line for frame 5. "
                   "Can that program read the balance? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "frame 5",
            (lambda: [Indicate(flab2[5], color=BLUE_M, scale_factor=1.3), Indicate(hrows[0][0], color=BLUE_M)], 0.8),
            "no line for frame 5",
            (lambda: [LaggedStart(*[Indicate(r, color=PURPLE_M) for r in hrows[1]], lag_ratio=0.2)], 1.0),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        try_a = [PC[1][0] + PW / 2 + 0.08, PC[1][1] + 0.55, 0]
        try_b = np.array(try_a) + 0.3 * (np.array([RAM_X0 - 0.08, frame_y(5), 0]) - np.array(try_a))
        tryl = DashedLine(try_a, try_b, dash_length=0.1, stroke_width=2.5, color=PURPLE_M)
        nope = tick(False, 0.2).move_to(try_b + [0.25, 0, 0])
        self.steps("No. Its addresses can only reach frames in its own table. If the room isn't on your group's list, no address leads there.", [
            (lambda: [*self.uncap(), Create(tryl)], 0.5),
            (lambda: [Create(nope)], 0.4),
            "only reach frames",
            (lambda: [LaggedStart(*[dot_run(a.get_start(), a.get_end(), PURPLE_M, 0.6) for a in arrows[1]], lag_ratio=0.25)], 1.3),
        ], after=0.3)
        self.play(FadeOut(nope), FadeOut(tryl), *self.cap("an address is a room number on your own group's letter", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
