from sfz import *

SAY.insert(0, (r"\bVACUUM\b", "vacuum"))

# one 8 KB page drawn from byte 0 (left) to byte 8,192 (right); rows to scale with each other, not with the page
PX0, PX1, PY, PH = -6.2, 6.2, 0.55, 1.1
TOP, BOT = PY + PH / 2, PY - PH / 2
HDR_W, SLOT_W = 0.9, 1.3
U = 1 / 200                                   # units per byte, for rows
SX0 = PX0 + HDR_W                             # where the slots start
STRIP_Y = 2.85
IDX = np.array([-4.4, 1.95, 0])                # the index chip, top left
ST_Y = [-2.15, -2.75]                         # status lines under the page


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def rbox(x0, x1, color, sw=2.5):
    r = Rectangle(width=x1 - x0, height=PH, stroke_color=color, stroke_width=sw)
    return r.set_fill(fillc(color), 1).move_to([(x0 + x1) / 2, PY, 0])


def row_blk(name, nbytes, x0, color=BLUE_M):
    x1 = x0 + nbytes * U
    cx = (x0 + x1) / 2
    return VGroup(rbox(x0, x1, color), T(name, 20).move_to([cx, PY + 0.18, 0]),
                  T(f"{nbytes} B", 17, GREY_B).move_to([cx, PY - 0.2, 0]))


def back_row(name, nbytes, x1, color=BLUE_M):
    return row_blk(name, nbytes, x1 - nbytes * U, color)


def hole_blk(x0, nbytes):
    x1 = x0 + nbytes * U
    cx = (x0 + x1) / 2
    r = DashedVMobject(Rectangle(width=x1 - x0 - 0.06, height=PH - 0.06), num_dashes=28).set_stroke(GREY_C, 2)
    r.move_to([cx, PY, 0])
    return VGroup(r, T("hole", 19, GREY_B).move_to([cx, PY + 0.18, 0]), T(f"{nbytes} B", 17, GREY_C).move_to([cx, PY - 0.2, 0]))


def slot_x(k):
    return SX0 + (k - 1) * SLOT_W


def slot_blk(k, body, color=GOLD_M, bcolor=WHITE):
    x0 = slot_x(k)
    cx = x0 + SLOT_W / 2
    return VGroup(rbox(x0, x0 + SLOT_W, color), T(f"slot {k}", 17, GREY_B).move_to([cx, PY + 0.2, 0]),
                  M(body, 15, bcolor).move_to([cx, PY - 0.18, 0]))


def lower_mark(x, val):
    t = Line([x, TOP + 0.02, 0], [x, TOP + 0.36, 0], color=TEAL_M, stroke_width=3)
    return VGroup(t, left_at(T(f"lower {val}", 18, TEAL_M), x + 0.08, TOP + 0.25))


def upper_mark(x, val):
    t = Line([x, TOP + 0.02, 0], [x, TOP + 0.36, 0], color=PURPLE_M, stroke_width=3)
    return VGroup(t, right_at(T(f"upper {val}", 18, PURPLE_M), x - 0.08, TOP + 0.25))


def byte_mark(x, val, color=GREY_B):
    t = Line([x, BOT - 0.02, 0], [x, BOT - 0.24, 0], color=color, stroke_width=2.5)
    return VGroup(t, T(f"{val}", 17, color).move_to([x, BOT - 0.42, 0]))


def pointer(k, row_cx, color=GOLD_M):
    """Curved arrow under the page from slot k to the row it points at."""
    a = np.array([slot_x(k) + SLOT_W / 2, BOT - 0.04, 0])
    b = np.array([row_cx, BOT - 0.04, 0])
    return CurvedArrow(a, b, angle=TAU / 6, color=color, stroke_width=2.5, tip_length=0.16)


def pointer_path(k, row_cx):
    a = np.array([slot_x(k) + SLOT_W / 2, BOT - 0.04, 0])
    b = np.array([row_cx, BOT - 0.04, 0])
    return ArcBetweenPoints(a, b, angle=TAU / 6)


def status(s, k, color=GREY_B, size=22):
    return T(s, size, color).move_to([0, ST_Y[k], 0])


def idx_chip(s, color=GREY_B):
    return mbox(s, color, h=0.6, size=18).move_to(IDX)


def dot_along(path, color=YELLOW_M, rt=0.7):
    d = Dot(radius=0.08, color=color).move_to(path.get_start())
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


class SlottedPages(Base):
    """store-02, section 1 (with section 0's pages and section 2's compaction): a table file as 8 KB pages; packing rows
    from the front breaks an index that stores byte offsets; a slotted page (24-byte header, 4-byte slots, rows of 300,
    200 and 400 bytes from the back) gives row 3 the address (0, 3); deleting row 2 leaves a hole, and compaction moves
    row 3 from 7,292 to 7,492 without changing its slot."""

    def construct(self):
        self.title_card("Slotted pages", "rows move inside a page, and their address stays put")

        # ---- the table file -------------------------------------------------------------------------------------------
        pw, gap = 1.9, 0.2
        pages = VGroup()
        for i in range(5):
            r = Rectangle(width=pw, height=1.0, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
            r.move_to([-4.6 + i * (pw + gap), 0.5, 0])
            pages.add(VGroup(r, T(f"page {i}", 22).move_to(r)))
        dots = T("...", 30, GREY_B).move_to([-4.6 + 5 * (pw + gap) - 0.3, 0.5, 0])
        flab = T("ledger table: one file", 22, GREY_B).move_to([-4.6 - pw / 2 + 1.25, 1.35, 0])
        self.steps("A ledger table can hold a billion rows. PostgreSQL keeps each table in a file, cut into pages of 8 KB.", [
            (lambda: [FadeIn(flab, shift=0.1 * DOWN)], 0.6),
            "PostgreSQL keeps",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.15 * RIGHT) for p in pages], lag_ratio=0.25), FadeIn(dots)], 1.6),
        ])

        offs = VGroup(*[T(f"byte {v}", 18, GREY_B).move_to([pages[i].get_center()[0], -0.28, 0])
                        for i, v in enumerate(["0", "8,192", "16,384", "24,576", "32,768"])])
        calc = T("page 2 starts at 2 × 8,192 = 16,384", 22, GOLD_M).move_to([0, -1.15, 0])
        self.steps("Page n starts at byte n times 8,192, and the database always reads or writes a whole page.", [
            (lambda: [LaggedStart(*[FadeIn(o) for o in offs], lag_ratio=0.15)], 1.2),
            "and the database",
            (lambda: [glow(pages[2][0], GOLD_M, 1.05), offs[2].animate.set_color(GOLD_M), FadeIn(calc, shift=0.1 * UP)], 1.0),
        ])

        # ---- zoom into page 0 -----------------------------------------------------------------------------------------
        strip = VGroup(flab, pages, dots)
        bar = Rectangle(width=PX1 - PX0, height=PH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to([0, PY, 0])
        self.steps("Look inside page 0. Rows have different lengths, and some get deleted. "
                   "How can an index still find row 3 tomorrow?", [
            (lambda: [FadeOut(offs), FadeOut(calc), strip.animate.scale(0.55).move_to([0, STRIP_Y, 0])], 1.0),
            (lambda: [pages[0][0].animate.set_stroke(GOLD_M, 3.5), pages[0][1].animate.set_color(GOLD_M)], 0.5),
            (lambda: [TransformFromCopy(pages[0][0], bar)], 1.0),
        ])
        hdr = VGroup(rbox(PX0, SX0, GREY_B), T("header", 16, GREY_B).move_to([PX0 + HDR_W / 2, PY, 0]))

        # ---- the naive layout: pack from the front, index by byte offset ------------------------------------------------
        n1, n2, n3 = row_blk("row 1", 300, SX0), row_blk("row 2", 200, SX0 + 300 * U), row_blk("row 3", 400, SX0 + 500 * U)
        bm = {v: byte_mark(SX0 + (v - 24) * U, v) for v in (24, 324, 524, 924)}
        x524 = SX0 + 500 * U
        ichip = idx_chip("index: id 3 → page 0, byte 524")
        ichip.move_to([x524, IDX[1], 0])
        iar = Arrow([x524, ichip.get_bottom()[1] - 0.04, 0], [x524, TOP + 0.04, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.3)
        self.steps("The simplest layout packs the rows from the front, and the index keeps each row's byte offset. "
                   "Row 3 starts at byte 524.", [
            (lambda: [FadeIn(hdr), FadeIn(bm[24])], 0.5),
            (lambda: [FadeIn(n1, shift=0.2 * RIGHT)], 0.4),
            (lambda: [FadeIn(n2, shift=0.2 * RIGHT), FadeIn(bm[324])], 0.4),
            (lambda: [FadeIn(n3, shift=0.2 * RIGHT), FadeIn(bm[524]), FadeIn(bm[924])], 0.4),
            "and the index",
            (lambda: [FadeIn(ichip, shift=0.1 * DOWN)], 0.6),
            "Row 3 starts",
            (lambda: [GrowArrow(iar), bm[524].animate.set_color(GOLD_M)], 0.7),
        ])

        x = tick(False, 0.2).move_to([x524 + 0.32, TOP + 0.3, 0])
        bad = status("byte 524 is now the middle of row 3", 0, RED_M)
        self.steps("Now delete row 2, and slide row 3 down to close the gap. "
                   "Byte 524 is now the middle of row 3, and the index reads garbage.", [
            (lambda: [n2[0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1)], 0.5),
            (lambda: [FadeOut(n2), FadeOut(bm[524]), FadeOut(bm[924])], 0.5),
            "and slide",
            (lambda: [n3.animate.shift(200 * U * LEFT)], 1.3),
            (lambda: [FadeIn(byte_mark(SX0 + 700 * U, 724))], 0.4),
            "Byte 524",
            (lambda: [iar.animate.set_color(RED_M), Create(x), FadeIn(bad, shift=0.1 * UP)], 0.8),
            "and the index reads",
            (lambda: [ichip[0].animate.set_stroke(RED_M)], 0.5),
        ])
        keep = [bar, *strip.get_family(), *hdr.get_family()]
        naive = [m for m in self.mobjects if not any(m is k for k in keep)]

        # ---- the slotted page -------------------------------------------------------------------------------------------
        lo = lower_mark(SX0, 24)
        up = upper_mark(PX1, "8,192")
        rule = status("slots grow from the front, rows from the back", 0, GREY_B)
        self.steps("A slotted page adds one level of indirection. Its header keeps two offsets: lower, "
                   "where the slots end, and upper, where the rows begin.", [
            (lambda: [*[FadeOut(m) for m in naive]], 0.8),
            "Its header",
            (lambda: [glow(hdr[0], GREY_A, 1.06)], 0.7),
            "lower,",
            (lambda: [FadeIn(lo, shift=0.1 * DOWN)], 0.5),
            "and upper",
            (lambda: [FadeIn(up, shift=0.1 * DOWN)], 0.5),
        ])

        x1 = {1: PX1, 2: PX1 - 300 * U, 3: PX1 - 500 * U}
        r = {1: back_row("row 1", 300, x1[1]), 2: back_row("row 2", 200, x1[2]), 3: back_row("row 3", 400, x1[3])}
        cx = {k: r[k][0].get_center()[0] for k in r}
        sl = {1: slot_blk(1, "7892, 300"), 2: slot_blk(2, "7692, 200"), 3: slot_blk(3, "7292, 400")}
        pt = {k: pointer(k, cx[k]) for k in r}
        self.steps("Insert row 1, 300 bytes. It goes at the back, so upper drops to 7,892. "
                   "Slot 1, at the front, records that offset and the length.", [
            (lambda: [FadeIn(r[1], shift=0.2 * DOWN)], 0.7),
            "so upper drops",
            (lambda: [Transform(up, upper_mark(x1[2], "7,892"))], 0.7),
            "Slot 1",
            (lambda: [FadeIn(sl[1], shift=0.2 * RIGHT), Transform(lo, lower_mark(slot_x(2), 28))], 0.7),
            "records that offset",
            (lambda: [Create(pt[1])], 0.8),
        ])

        free = T("free: 7,256 bytes", 18, GREY_B).move_to([(slot_x(4) + x1[3] - 400 * U) / 2, PY, 0])
        self.steps("Rows 2 and 3 follow. Slots grow from the front and rows from the back, "
                   "so the free space is always one gap in the middle.", [
            (lambda: [FadeIn(r[2], shift=0.2 * DOWN), FadeIn(sl[2], shift=0.2 * RIGHT), Create(pt[2]),
                      Transform(up, upper_mark(x1[3], "7,692")), Transform(lo, lower_mark(slot_x(3), 32))], 0.9),
            (lambda: [FadeIn(r[3], shift=0.2 * DOWN), FadeIn(sl[3], shift=0.2 * RIGHT), Create(pt[3]),
                      Transform(up, upper_mark(x1[3] - 400 * U, "7,292")), Transform(lo, lower_mark(slot_x(4), 36))], 0.9),
            "Slots grow",
            (lambda: [FadeIn(rule, shift=0.1 * UP)], 0.6),
            "so the free space",
            (lambda: [FadeIn(free)], 0.6),
        ])

        ic2 = idx_chip("index: id 3 → (0, 3)", GOLD_M)
        s3top = np.array([slot_x(3) + SLOT_W / 2, TOP + 0.04, 0])
        iar2 = Arrow(ic2.get_bottom() + np.array([0.9, -0.04, 0]), s3top, buff=0, stroke_width=3, color=GOLD_M,
                     max_tip_length_to_length_ratio=0.25)
        addr = status("address = (page 0, slot 3), never a byte offset", 1, GOLD_M)
        self.steps("The index now stores row 3's address as page 0, slot 3. It never stores a byte offset.", [
            (lambda: [FadeIn(ic2, shift=0.1 * DOWN)], 0.6),
            (lambda: [GrowArrow(iar2)], 0.5),
            (lambda: [dot_along(Line(iar2.get_start(), iar2.get_end()), GOLD_M, 0.5)], 0.6),
            (lambda: [dot_along(pointer_path(3, cx[3]), GOLD_M, 0.8), glow(sl[3][0], GOLD_M, 1.06)], 0.9),
            (lambda: [glow(r[3][0], GOLD_M, 1.04)], 0.6),
            "It never stores",
            (lambda: [FadeIn(addr, shift=0.1 * UP)], 0.6),
        ])

        hole = hole_blk(x1[2] - 200 * U, 200)
        dead = slot_blk(2, "dead", RED_M, RED_M)
        self.steps("Delete row 2. Its slot is marked dead, and its 200 bytes are left as a hole.", [
            (lambda: [FadeOut(rule), FadeOut(addr), r[2][0].animate.set_stroke(RED_M)], 0.5),
            "Its slot",
            (lambda: [Transform(sl[2], dead), FadeOut(pt[2])], 0.7),
            "and its 200 bytes",
            (lambda: [FadeOut(r[2]), FadeIn(hole)], 0.8),
        ])

        r3n = back_row("row 3", 400, x1[2])
        mv = status("row 3 moves: byte 7,292 → byte 7,492", 0, BLUE_M)
        self.steps("Compaction slides the live rows together. In PostgreSQL, VACUUM does it. "
                   "Row 3 moves up 200 bytes, from 7,292 to 7,492.", [
            (lambda: [glow(hole[0], GREY_A, 1.03)], 0.8),
            "Row 3 moves",
            (lambda: [FadeOut(hole), FadeOut(pt[3]), r[3].animate.move_to(r3n), FadeIn(mv, shift=0.1 * UP),
                      Transform(up, upper_mark(x1[2], "7,492"))], 2.0),
        ])

        pt3 = pointer(3, r3n[0].get_center()[0])
        free2 = T("free: 7,456 bytes", 18, GREEN_M).move_to([(slot_x(4) + x1[2] - 400 * U) / 2, PY, 0])
        self.steps("Slot 3 gets the new offset, and the free gap grows by exactly 200 bytes.", [
            (lambda: [Transform(sl[3], slot_blk(3, "7492, 400", GOLD_M, YELLOW_M)), Create(pt3)], 0.9),
            "and the free gap",
            (lambda: [Transform(free, free2)], 0.8),
        ])

        ok = status("the slot number never changed", 1, GREEN_M)
        self.steps("The index still says slot 3, so it still finds row 3. The bytes moved, and the slot number didn't.", [
            (lambda: [glow(ic2[0], GOLD_M, 1.05)], 0.6),
            (lambda: [dot_along(Line(iar2.get_start(), iar2.get_end()), GREEN_M, 0.5)], 0.6),
            (lambda: [dot_along(pointer_path(3, r3n[0].get_center()[0]), GREEN_M, 0.8)], 0.9),
            (lambda: [glow(r[3][0], GREEN_M, 1.04)], 0.6),
            "The bytes moved",
            (lambda: [FadeIn(ok, shift=0.1 * UP)], 0.6),
        ])

        self.steps("A row's address is its page and its slot. Inside the page, its bytes can move anywhere, "
                   "and the address stays the same.", [
            (lambda: [FadeOut(mv), FadeOut(ok), Transform(ic2, idx_chip("index: id 3 → (0, 3)", GREEN_M)),
                      FadeIn(status("a row's address: (page, slot)", 0, WHITE, 24))], 0.9),
            "Inside the page",
            (lambda: [glow(r[1][0], BLUE_M, 1.04), glow(r[3][0], BLUE_M, 1.04)], 0.9),
            "and the address",
            (lambda: [glow(sl[3][0], GREEN_M, 1.06), glow(pages[0][0], GREEN_M, 1.08)], 0.9),
        ])
        self.wait(0.6)
