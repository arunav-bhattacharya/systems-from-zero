from sfz import *

SAY.insert(0, (r"\bpd_lower\b", "P D lower"))
SAY.insert(0, (r"\bpd_upper\b", "P D upper"))
SAY.insert(0, (r"\bVACUUM\b", "vacuum"))
SAY.insert(0, (r"\b4 KB\b", "4 kilobytes"))
SAY.insert(0, (r"\b8 KB\b", "8 kilobytes"))
SAY.insert(0, (r"\bDelete B\.", "Delete row B."))
SAY.insert(0, (r"\bbetween A and C\b", "between row A and row C"))
# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz" (Whisper hears "posters"); spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TITLE_Y = 2.9
X0, X1 = -6.2, 6.2                 # the page bar: byte 0 on the left, 4,096 on the right
BAR_Y, BAR_H = 0.85, 1.1
BAR_TOP, BAR_BOT = BAR_Y + BAR_H / 2, BAR_Y - BAR_H / 2
IN_H = BAR_H - 0.14                # height of things inside the bar
SC = 0.004                         # units per byte for rows (header and slots are drawn wider than their 4 bytes)
HDR_W, SLW = 0.66, 0.6              # header and slot boxes
MK_Y = BAR_TOP + 0.66              # marker labels
TAB = [(1.6, -0.95), (4.6, -0.95), (1.6, -1.6), (4.6, -1.6)]   # slot table entries
IDX = (-3.6, -1.6)                 # the index chip
CAP_Y = -3.25

ROWS = {"A": (300, BLUE_M), "B": (200, GOLD_M), "C": (400, GREEN_M), "D": (250, PURPLE_M)}


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
        if t > dur + 0.1:
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, c=(0, -2.55), secs=3.0):
        bar = Line([c[0] - 1.0, c[1], 0], [c[0] + 1.0, c[1], 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def xb(off):
    """x of a byte offset counted from the back of the page (rows live there)."""
    return X1 - (4096 - off) * SC


def xf(off):
    """x of a byte offset counted from the front (the broken versions pack rows there)."""
    return X0 + off * SC


def row(name, x_left, y=BAR_Y):
    n, color = ROWS[name]
    w = n * SC
    r = Rectangle(width=w - 0.04, height=IN_H, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    a = T(name, 26, color)
    b = T(f"{n} B", 16, GREY_B)
    g = VGroup(r, VGroup(a, b).arrange(DOWN, buff=0.06))
    g[1].move_to(r)
    return g.move_to([x_left + w / 2, y, 0])


def back_row(name, off):
    return row(name, xb(off))


def hdr_box():
    r = Rectangle(width=HDR_W - 0.06, height=IN_H, stroke_color=GREY_B, stroke_width=2.5).set_fill(fillc(GREY_B, 0.2), 1)
    return VGroup(r, M("hdr", 16, GREY_B).move_to(r)).move_to([X0 + HDR_W / 2, BAR_Y, 0])


def slot_x(k):
    return X0 + HDR_W + k * SLW


def slot_box(k, color, dead=False):
    r = Rectangle(width=SLW - 0.06, height=IN_H, stroke_color=GREY_D if dead else TEAL_M, stroke_width=2.5)
    r.set_fill(fillc(GREY_D if dead else color, 0.22), 1)
    return VGroup(r, M(str(k), 22, GREY_D if dead else color).move_to(r)).move_to([slot_x(k) + SLW / 2, BAR_Y, 0])


def tab(k, off, ln, color):
    return chip(f"{k} = ({off}, {ln})", GREY_D if off == 0 else color, 20, mono=True).move_to([TAB[k][0], TAB[k][1], 0])


def marker(name, x, val, side=0):
    ln = Line([x, BAR_TOP + 0.05, 0], [x, BAR_TOP + 0.42, 0], stroke_width=3, color=YELLOW_M)
    lab = T(f"{name} = {val}", 22, YELLOW_M)
    cx = min(max(x, X0 + lab.width / 2), X1 - lab.width / 2)
    lab.move_to([cx, MK_Y, 0])
    return VGroup(ln, lab)


def free_lab(lo_x, up_x, n):
    return T(f"free {n} B", 22, GREY_B).move_to([(lo_x + up_x) / 2, BAR_Y, 0])


def idx_chip(s, color=WHITE):
    return chip(s, color, 22).move_to([IDX[0], IDX[1], 0])


def up_arrow(x, color=YELLOW_M):
    return Arrow([x, IDX[1] + 0.33, 0], [x, BAR_BOT - 0.04, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12)


class SlottedPages(Base):
    """store-02, section 1. Rows of different sizes in one page. Packing them from the front makes a lookup a walk, and
    deleting B and sliding C breaks an index that noted byte 500. A fixed list at the front caps the rows. The filing
    drawer with a list taped inside. The lab's 4 KB slotted page: lower 4 and upper 4,096; A 300 at 3,796 in slot 0; B
    at 3,596 in slot 1; C at 3,196 in slot 2 (free 3,180); the index stores page 7, slot 2. Delete B marks slot 1
    (0, 0); tidying moves C to 3,396 and the slot stays. Slots and rows share the space; D gets slot 3, never the dead
    one. Names, PostgreSQL's page (lower 652, upper 656), the cost and the promise, and a check: delete C."""

    def construct(self):
        self.capm = None
        self.title_card("The row moved, so why does the index still find it?", "slotted pages")

        # ---------------- scene 1: the question ----------------
        bar = Rectangle(width=X1 - X0, height=BAR_H, stroke_color=GREY_B, stroke_width=2.5).move_to([0, BAR_Y, 0]).set_z_index(-1)
        t_pg = T("one page of a table", 24, GREY_B).move_to([0, TITLE_Y, 0])
        e0 = M("0", 18, GREY_B).move_to([X0 + 0.1, BAR_TOP + 0.3, 0])
        e1 = M("4,096", 18, GREY_B)
        e1.move_to([X1 - e1.width / 2, BAR_TOP + 0.3, 0])
        loose = {k: row(k, x, -1.0) for k, x in (("A", -3.6), ("B", -1.4), ("C", 0.6))}
        self.steps("A database keeps each table in a file of fixed-size pages. Rows come in different sizes: "
                   "a ledger row takes 48 bytes, and one with a long note over 500. So how do we fit them "
                   "into one page, and find one again quickly?", [
            (lambda: [Create(bar), FadeIn(t_pg)], 0.9),
            "Rows come in",
            (lambda: self.cap("a row in the ledger table: 48 bytes; one with a long note: over 500"), 0.6),
            "So how do we",
            (lambda: self.cap("fit rows of different sizes in one page, and find one again quickly?", YELLOW_M), 0.6),
        ])
        t_pg2 = T("the lab's page: 4 KB = 4,096 bytes", 24, GREY_B).move_to([0, TITLE_Y, 0])
        self.steps("The lab's page holds 4,096 bytes. Our rows: A is 300 bytes, B is 200, and C is 400.", [
            (lambda: [*self.uncap(), swap(t_pg, t_pg2), FadeIn(e0), FadeIn(e1)], 0.7),
            "A is 300",
            (lambda: [FadeIn(loose["A"], shift=0.1 * UP)], 0.4),
            "B is 200",
            (lambda: [FadeIn(loose["B"], shift=0.1 * UP)], 0.4),
            "and C is 400",
            (lambda: [FadeIn(loose["C"], shift=0.1 * UP)], 0.4),
        ], after=0.4)

        # ---------------- scene 2: pack them from the front ----------------
        fr = {"A": row("A", xf(0)), "B": row("B", xf(300)), "C": row("C", xf(500))}
        o300 = M("300", 18, GREY_B).move_to([xf(300), BAR_TOP + 0.3, 0])
        o500 = M("500", 18, GREY_B).move_to([xf(500), BAR_TOP + 0.3, 0])
        walk = Line([xf(0), BAR_BOT - 0.12, 0], [xf(0), BAR_BOT - 0.12, 0], stroke_width=5, color=YELLOW_M)
        self.steps("The simplest way packs them back to back from the start. A at byte 0, B at 300, C at 500. "
                   "To find C, you read A's length and skip it, then B's length and skip it. Slow, but it works.", [
            (lambda: self.cap("version 1: pack the rows from the front"), 0.5),
            "A at byte 0",
            (lambda: [ReplacementTransform(loose["A"], fr["A"])], 0.6),
            "B at 300",
            (lambda: [ReplacementTransform(loose["B"], fr["B"]), FadeIn(o300)], 0.6),
            "C at 500",
            (lambda: [ReplacementTransform(loose["C"], fr["C"]), FadeIn(o500)], 0.6),
            "To find C",
            (lambda: [Create(walk)], 0.2),
            (lambda: [walk.animate.put_start_and_end_on([xf(0), BAR_BOT - 0.12, 0], [xf(300), BAR_BOT - 0.12, 0])], 0.6),
            "then B's length",
            (lambda: [walk.animate.put_start_and_end_on([xf(0), BAR_BOT - 0.12, 0], [xf(500), BAR_BOT - 0.12, 0])], 0.6),
            "Slow, but",
            (lambda: [glow(fr["C"][0], GREEN_M, 1.05)], 0.5),
        ])
        ix = idx_chip("index: C at byte 500")
        ia = up_arrow(xf(500))
        self.steps("Say an index, a lookup table elsewhere, notes that C starts at byte 500.", [
            (lambda: [FadeOut(walk), *self.uncap(), FadeIn(ix, shift=0.1 * UP)], 0.6),
            "notes that",
            (lambda: [GrowArrow(ia)], 0.6),
        ])
        o300b = M("300", 18, GREY_B).move_to([xf(300), BAR_TOP + 0.3, 0])
        self.steps("Now delete B, and slide C down to close the gap. "
                   "C now starts at 300, and byte 500 is the middle of C. "
                   "The index now points, with full confidence, at the middle of a row.", [
            (lambda: [fr["B"][0].animate.set_stroke(RED_M)], 0.4),
            (lambda: [FadeOut(fr["B"], shift=0.3 * UP)], 0.5),
            "and slide C",
            (lambda: [fr["C"].animate.shift(LEFT * 200 * SC), FadeOut(o500)], 0.9),
            "C now starts",
            (lambda: [Indicate(o300, color=YELLOW_M, scale_factor=1.4)], 0.5),
            "and byte 500",
            (lambda: [ia.animate.set_color(RED_M), ix[0].animate.set_stroke(RED_M), *self.cap("byte 500: the middle of C", RED_M)], 0.6),
            "The index now points",
            (lambda: [glow(fr["C"][0], RED_M, 1.04)], 0.6),
        ], after=0.4)

        # ---------------- scene 3: a list at the front ----------------
        LW = 1.85
        lst = VGroup(Rectangle(width=LW - 0.06, height=IN_H, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M, 0.18), 1))
        lst.add(T("list: 3 entries", 18, TEAL_M).move_to(lst[0]))
        lst.move_to([X0 + LW / 2, BAR_Y, 0])
        v2 = {"A": row("A", X0 + LW), "B": row("B", X0 + LW + 300 * SC), "C": row("C", X0 + LW + 500 * SC)}
        arc2 = ArcBetweenPoints([X0 + LW / 2 + 0.3, BAR_BOT - 0.05, 0], [v2["C"].get_center()[0], BAR_BOT - 0.05, 0], angle=0.9,
                                color=TEAL_M, stroke_width=3).add_tip(tip_length=0.15)
        self.steps("Next idea: a small numbered list at the start of the page. Entry 2 holds C's offset and length. "
                   "Finding C is one lookup, and C can move, as long as entry 2 is updated.", [
            (lambda: [FadeOut(VGroup(fr["A"], fr["C"], o300, ix, ia)), *self.cap("version 2: a numbered list at the front")], 0.7),
            "a small numbered list",
            (lambda: [FadeIn(lst), FadeIn(v2["A"]), FadeIn(v2["B"]), FadeIn(v2["C"])], 0.8),
            "Entry 2 holds",
            (lambda: [Create(arc2)], 0.7),
            "Finding C is one",
            (lambda: self.cap("one lookup: entry 2 says where C is", TEAL_M), 0.5),
        ])
        self.steps("But how long is the list? Fix its size, and you cap the rows per page. "
                   "Grow it, and every row behind it has to move.", [
            (lambda: [FadeOut(arc2)], 0.4),
            "Fix its size",
            (lambda: [glow(lst[0], RED_M, 1.04), *self.cap("a fixed list: at most 3 rows per page", RED_M)], 0.7),
            "Grow it",
            (lambda: [lst.animate.stretch_to_fit_width(LW + 0.5 - 0.06).move_to([X0 + (LW + 0.5) / 2, BAR_Y, 0]),
                      *[v2[k].animate.shift(0.5 * RIGHT) for k in "ABC"], *self.cap("a longer list: every row moves", RED_M)], 0.9),
            (lambda: [*[glow(v2[k][0], RED_M, 1.04) for k in "ABC"]], 0.6),
        ], after=0.4)

        # ---------------- scene 4: the filing drawer ----------------
        t_dr = T("the page: a drawer", 24, GREY_B).move_to([0, TITLE_Y, 0])
        lw2 = 1.5
        tape = VGroup(Rectangle(width=lw2, height=IN_H, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M, 0.18), 1))
        lines = VGroup(*[M(s, 17, TEAL_M) for s in ("0: A", "1: B", "2: C")]).arrange(DOWN, buff=0.08)
        tape.add(lines.move_to(tape[0]))
        tape.move_to([X0 + 0.07 + lw2 / 2, BAR_Y, 0])
        dr = {"A": back_row("A", 3796), "B": back_row("B", 3596), "C": back_row("C", 3196)}
        self.steps("A filing drawer shows the fix. Inside its front, a numbered list is taped: line 2 says where folder 2 sits.", [
            (lambda: [FadeOut(VGroup(lst, *v2.values(), e0, e1)), *self.uncap(), swap(t_pg2, t_dr)], 0.7),
            "Inside its front",
            (lambda: [FadeIn(tape), LaggedStart(*[FadeIn(dr[k], shift=0.1 * DOWN) for k in "ABC"], lag_ratio=0.2)], 1.0),
            "line 2 says",
            (lambda: [Indicate(lines[2], color=YELLOW_M, scale_factor=1.3), glow(dr["C"][0], GREEN_M, 1.04)], 0.8),
        ])
        self.steps("Pull a folder out and push the rest together, and you correct the positions on the list. "
                   "But line 2 is still line 2. Anyone who wrote down drawer 0, line 2 still finds the folder.", [
            "Pull a folder",
            (lambda: [FadeOut(dr["B"], shift=0.5 * UP)], 0.6),
            "push the rest",
            (lambda: [dr["C"].animate.shift(RIGHT * 200 * SC)], 0.7),
            "you correct",
            (lambda: [Indicate(lines[2], color=YELLOW_M, scale_factor=1.3)], 0.6),
            "But line 2",
            (lambda: self.cap("line 2 is still line 2", YELLOW_M), 0.5),
            "Anyone who wrote",
            (lambda: [*self.cap("\"drawer 0, line 2\" still finds the folder", WHITE), glow(dr["C"][0], GREEN_M, 1.04)], 0.6),
        ])
        self.steps("Let's map it. The drawer is the page. The list is an array of slots, one per row. And each folder is a row.", [
            "The drawer is",
            (lambda: [glow(bar, GREY_B, 1.0), *self.cap("the drawer: the page", WHITE)], 0.6),
            "The list is",
            (lambda: [glow(tape[0], TEAL_M, 1.04), *self.cap("the list: an array of slots, one per row", TEAL_M)], 0.6),
            "And each folder",
            (lambda: [glow(dr["A"][0], BLUE_M, 1.04), glow(dr["C"][0], GREEN_M, 1.04), *self.cap("a folder: a row", WHITE)], 0.6),
        ], after=0.4)

        # ---------------- scene 5: grow toward each other ----------------
        t_sp = T("the lab's 4 KB page: slots from the front, rows from the back", 24, GREY_B).move_to([0, TITLE_Y, 0])
        hb = hdr_box()
        st = {"lo": marker("lower", slot_x(0), 4), "up": marker("upper", X1, "4,096"), "free": free_lab(slot_x(0), X1, "4,092")}

        def set_state(n_slots, upper, free, color_lo=YELLOW_M):
            lo_x = slot_x(n_slots)
            new = {"lo": marker("lower", lo_x, 4 + 4 * n_slots), "up": marker("upper", xb(upper), f"{upper:,}"),
                   "free": free_lab(lo_x, xb(upper), f"{free:,}")}
            anims = [Transform(st[k], new[k]) for k in new]
            return anims

        self.steps("So let the two grow toward each other. A 4-byte header at the start keeps two numbers. "
                   "lower is where the slots end: 4, right after the header. upper is where the rows begin: 4,096, the end of the page. "
                   "Everything between them is free.", [
            (lambda: [FadeOut(VGroup(tape, dr["A"], dr["C"])), *self.uncap(), swap(t_dr, t_sp)], 0.7),
            "A 4-byte header",
            (lambda: [FadeIn(hb)], 0.5),
            "lower is where",
            (lambda: [FadeIn(st["lo"], shift=0.1 * DOWN)], 0.6),
            "upper is where",
            (lambda: [FadeIn(st["up"], shift=0.1 * DOWN)], 0.6),
            "Everything between",
            (lambda: [FadeIn(st["free"])], 0.5),
        ])
        R = {}
        S = {}
        TB = {}

        def insert(name, k, off, n_slots, free):
            R[name] = back_row(name, off)
            S[k] = slot_box(k, ROWS[name][1])
            TB[k] = tab(k, off, ROWS[name][0], ROWS[name][1])
            return R[name], S[k], TB[k], set_state(n_slots, off, free)

        def ins_a():
            r, s, t, a = insert("A", 0, 3796, 1, 3788)
            return r, s, t, a

        ra, sa, ta, aa = ins_a()
        self.steps("Insert A, 300 bytes. It goes at the back, so upper drops to 3,796. "
                   "Slot 0 goes at the front and holds A's offset and length, 3,796 and 300, and lower grows to 8.", [
            "It goes at the back",
            (lambda: [FadeIn(ra, shift=0.3 * DOWN)], 0.6),
            "so upper drops",
            (lambda: [aa[1]], 0.6),
            "Slot 0 goes",
            (lambda: [FadeIn(sa, shift=0.2 * DOWN)], 0.5),
            "and holds",
            (lambda: [FadeIn(ta, shift=0.1 * UP)], 0.6),
            "and lower grows",
            (lambda: [aa[0], aa[2]], 0.6),
        ])
        rb, sb, tb_, ab = insert("B", 1, 3596, 2, 3584)
        self.steps("B, 200 bytes, gets slot 1, at 3,596.", [
            (lambda: [FadeIn(rb, shift=0.3 * DOWN), FadeIn(sb, shift=0.2 * DOWN), *ab], 0.8),
            (lambda: [FadeIn(tb_, shift=0.1 * UP)], 0.5),
        ])
        self.steps("Now C, 400 bytes. Where does it start, and which slot does it get? Pause and guess.", [
            (lambda: [glow(st["up"][0], YELLOW_M, 1.0)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        rc, sc_, tc, ac = insert("C", 2, 3196, 3, 3180)
        ixc = idx_chip("index: C is at page 7, slot 2")
        iac = up_arrow(slot_x(2) + SLW / 2)
        self.steps("At 3,196, in slot 2. lower is 16 now, and the free space is still one gap in the middle, 3,180 bytes. "
                   "So the index stores C's address as page 7, slot 2. It never stores the byte offset.", [
            (lambda: [*self.uncap(), FadeIn(rc, shift=0.3 * DOWN), FadeIn(sc_, shift=0.2 * DOWN), *ac], 0.8),
            (lambda: [FadeIn(tc, shift=0.1 * UP)], 0.5),
            "and the free space",
            (lambda: [Indicate(st["free"], color=WHITE, scale_factor=1.15)], 0.7),
            "So the index",
            (lambda: [FadeIn(ixc, shift=0.1 * UP)], 0.5),
            (lambda: [GrowArrow(iac)], 0.5),
            "It never stores",
            (lambda: self.cap("the address: page and slot, never the byte offset", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 6: delete, then tidy ----------------
        self.steps("Delete B. The page only marks slot 1 dead, as zero, zero. B's 200 bytes are still there, a hole between "
                   "A and C, and the free gap is still 3,180.", [
            (lambda: [*self.uncap(), rb[0].animate.set_stroke(RED_M)], 0.4),
            "marks slot 1",
            (lambda: [Transform(sb, slot_box(1, GOLD_M, dead=True)), Transform(tb_, tab(1, 0, 0, GREY_D))], 0.7),
            "B's 200 bytes",
            (lambda: [rb[0].animate.set_stroke(GREY_C).set_fill(fillc(GREY_C, 0.1), 1), rb[1].animate.set_color(GREY_C),
                      *self.cap("B's bytes stay: a hole between A and C", GREY_B)], 0.6),
            "and the free gap",
            (lambda: [Indicate(st["free"], color=WHITE, scale_factor=1.15)], 0.6),
        ])
        free2 = free_lab(slot_x(3), xb(3396), "3,380")
        up2 = marker("upper", xb(3396), "3,396")
        iac_ok = up_arrow(slot_x(2) + SLW / 2, GREEN_M)
        self.steps("Tidying the page slides the live rows toward the end. C moves up 200 bytes, to 3,396, "
                   "and slot 2 gets the new offset. The index still says slot 2, so it still finds C, "
                   "and the gap grows to 3,380. Same as the drawer: the folder moved, and line 2 didn't.", [
            (lambda: self.cap("tidy the page: slide the live rows toward the end", WHITE), 0.5),
            "C moves up",
            (lambda: [FadeOut(rb), rc.animate.shift(RIGHT * 200 * SC), Transform(st["up"], up2)], 1.0),
            "and slot 2 gets",
            (lambda: [Transform(tc, tab(2, 3396, 400, GREEN_M)), glow(sc_[0], YELLOW_M, 1.05)], 0.7),
            "The index still",
            (lambda: [Transform(iac, iac_ok), ixc[0].animate.set_stroke(GREEN_M), glow(sc_[0], GREEN_M, 1.05)], 0.6),
            (lambda: [glow(rc[0], GREEN_M, 1.04)], 0.5),
            "and the gap grows",
            (lambda: [Transform(st["free"], free2)], 0.6),
            "Same as the drawer",
            (lambda: self.cap("the row moved; slot 2 didn't", GREEN_M), 0.5),
        ], after=0.4)

        # ---------------- scene 7: where the drawer breaks, and a rule ----------------
        self.steps("Here the drawer picture breaks. A list taped inside a drawer takes no room from the folders. "
                   "On a page, the slots and the rows share the same 4 KB. The page is full when lower and upper would cross.", [
            (lambda: self.cap("where the drawer picture breaks", WHITE), 0.5),
            "On a page",
            (lambda: [LaggedStart(*[glow(S[k][0], TEAL_M, 1.05) for k in (0, 1, 2)], lag_ratio=0.15),
                      LaggedStart(*[glow(R[n][0], ROWS[n][1], 1.04) for n in ("A", "C")], lag_ratio=0.15),
                      *self.cap("slots and rows share the same 4 KB", WHITE)], 1.0),
            "The page is full",
            (lambda: [st["lo"].animate.shift(0.3 * RIGHT), st["up"].animate.shift(0.3 * LEFT), *self.cap("full: when lower and upper would cross", RED_M)], 0.6),
            (lambda: [st["lo"].animate.shift(0.3 * LEFT), st["up"].animate.shift(0.3 * RIGHT)], 0.6),
        ])
        rd, sd, td, ad = insert("D", 3, 3146, 4, 3126)
        self.steps("Insert D, 250 bytes. It gets slot 3, not the dead slot 1. An old index entry might still say slot 1, "
                   "and it would find D instead of nothing. It's like giving out an old phone number: whoever saved it "
                   "reaches a stranger.", [
            (lambda: [*self.uncap(), FadeIn(rd, shift=0.3 * DOWN), FadeIn(sd, shift=0.2 * DOWN), *ad], 0.8),
            (lambda: [FadeIn(td, shift=0.1 * UP)], 0.5),
            "not the dead slot 1",
            (lambda: [glow(sb[0], GREY_B, 1.08), *self.cap("D gets slot 3; dead slot 1 is never handed out again", WHITE)], 0.7),
            "An old index entry",
            (lambda: [glow(S[3][0], RED_M, 1.06)], 0.6),
            "It's like giving",
            (lambda: self.cap("reusing slot 1: an old phone number, a stranger answers", GREY_B), 0.5),
        ])
        self.steps("PostgreSQL reuses a dead slot only after its cleanup, VACUUM, has removed every index entry that points at it.", [
            (lambda: self.cap("PostgreSQL: reuse a dead slot only after VACUUM removed every index entry to it", WHITE), 0.6),
            (lambda: [glow(sb[0], GREY_B, 1.08)], 0.6),
        ], after=0.4)

        # ---------------- scene 8: names, and a real page ----------------
        t_nm = T("a slotted page", 24, WHITE).move_to([0, TITLE_Y, 0])
        self.steps("This layout is called a slotted page. PostgreSQL uses it, with a 24-byte header and 4-byte slots it calls "
                   "line pointers. Its header calls the two numbers pd_lower and pd_upper.", [
            (lambda: [*self.uncap(), swap(t_sp, t_nm)], 0.6),
            "PostgreSQL uses it",
            (lambda: self.cap("PostgreSQL: a 24-byte header, 4-byte slots called line pointers", WHITE), 0.6),
            "Its header calls",
            (lambda: [*self.cap("lower = pd_lower, upper = pd_upper", YELLOW_M), Indicate(st["lo"][1], color=YELLOW_M, scale_factor=1.15),
                      Indicate(st["up"][1], color=YELLOW_M, scale_factor=1.15)], 0.8),
        ])
        pg = VGroup(T("PostgreSQL, ledger table, page 0 (8 KB):", 24, GREY_B),
                    T("lower = 24 + 157 × 4 = 652", 26, WHITE),
                    T("upper = 8,192 − 157 × 48 = 656", 26, WHITE),
                    T("free: 4 bytes; one more row needs 48 + 4 = 52", 26, RED_M)).arrange(DOWN, buff=0.17)
        pg.move_to([0, -1.4, 0])
        self.steps("On a real 8 KB page of the ledger table, lower is 652 and upper is 656: "
                   "a 24-byte header and 157 line pointers, 4 free bytes, then 157 rows of 48 bytes. "
                   "One more row needs 52, so the page is full.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*TB.values(), tb_, ixc, iac)), FadeIn(pg[0])], 0.7),
            "lower is 652",
            (lambda: [FadeIn(pg[1], shift=0.1 * UP)], 0.5),
            "and upper is 656",
            (lambda: [FadeIn(pg[2], shift=0.1 * UP)], 0.5),
            "a 24-byte header",
            (lambda: [Indicate(pg[1], color=YELLOW_M, scale_factor=1.05)], 0.8),
            "then 157 rows",
            (lambda: [Indicate(pg[2], color=YELLOW_M, scale_factor=1.05)], 0.8),
            "One more row",
            (lambda: [FadeIn(pg[3], shift=0.1 * UP)], 0.5),
        ], after=0.4)

        # ---------------- scene 9: the cost, the promise, and a check ----------------
        self.steps("The slots add one step to every lookup: the index points at the slot, and the slot points at the row. "
                   "That step buys one promise. A row's slot number never changes while the row lives, even when its bytes move.", [
            (lambda: [FadeOut(pg), FadeIn(VGroup(*[TB[k] for k in (0, 2, 3)], tb_, ixc, iac))], 0.7),
            "the index points",
            (lambda: [glow(ixc[0], GREEN_M, 1.04)], 0.5),
            "the slot points",
            (lambda: [glow(sc_[0], GREEN_M, 1.06), glow(rc[0], GREEN_M, 1.04)], 0.6),
            "That step buys",
            (lambda: self.cap("a row's slot number never changes while the row lives", YELLOW_M, 28), 0.6),
        ], after=0.5)
        self.steps("One quick check. Delete C now. What happens to lower, upper and the free gap? Pause and think.", [
            (lambda: [*self.uncap(), rc[0].animate.set_stroke(RED_M)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        self.steps("Nothing, yet. Slot 2 is marked dead, and C's 400 bytes stay where they are until the page is tidied.", [
            (lambda: [*self.uncap(), *[Indicate(st[k], color=YELLOW_M, scale_factor=1.1) for k in ("lo", "up", "free")]], 0.9),
            "Slot 2 is marked",
            (lambda: [Transform(sc_, slot_box(2, GREEN_M, dead=True)), Transform(tc, tab(2, 0, 0, GREY_D)),
                      FadeOut(iac), ixc[0].animate.set_stroke(GREY_D)], 0.7),
            "and C's 400",
            (lambda: [rc[0].animate.set_stroke(GREY_C).set_fill(fillc(GREY_C, 0.1), 1), rc[1].animate.set_color(GREY_C)], 0.6),
        ], after=0.3)
        self.play(*self.cap("the index points at the slot; the slot points at the row", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
