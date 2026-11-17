from sfz import *

# Order matters: the last rule inserted is applied first.
SAY.insert(0, (r"\bledger-2026\.csv\b", "ledger twenty twenty-six dot C S V"))
SAY.insert(0, (r"\bledger\.csv\b", "ledger dot C S V"))
SAY.insert(0, (r"\blatest\.csv\b", "latest dot C S V"))
SAY.insert(0, (r"/tmp/ledger dot C S V", "slash temp slash ledger dot C S V"))
SAY.insert(0, (r"\btmp\b", "temp"))
SAY.insert(0, (r"\binodes\b", "eye nodes"))
SAY.insert(0, (r"\binode\b", "eye node"))
SAY.insert(0, (r"\brm\b", "R M"))
SAY.insert(0, (r"\bsymlink\b", "sim link"))

DIR_C = GREEN_M                             # the directory and its cards

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TOP, BOT = 2.35, -0.75                      # directory and inode 13 share a top and a bottom
CY = (TOP + BOT) / 2
DX0, DX1 = -6.55, -2.35                     # the directory /tmp: a catalogue of cards
DCX = (DX0 + DX1) / 2
CARD_Y = [1.3, 0.55, -0.2]
CARD_W, CARD_H = 3.8, 0.56
IX0, IX1 = -1.25, 2.85                      # inode 13: the numbered book
ICX = (IX0 + IX1) / 2
SPINE = 0.46
LAB_X, VAL_X = IX0 + SPINE + 0.2, IX0 + SPINE + 1.12
FY = [1.3, 0.8, 0.3, -0.18]                 # size, owner..., links, blocks
SYM_TOP, SYM_BOT = -1.3, -2.3               # inode 12, the symlink, under inode 13
SYM_CY = (SYM_TOP + SYM_BOT) / 2
GCX, GCY, CELL, GAP = 5.4, 0.72, 0.42, 0.14  # the disk's blocks
FILE = [1, 2, 5, 6, 9]
PROG_C = np.array([5.3, -1.8, 0])          # a program that has the file open
ROOT_Y = 3.2                               # the small "/" box above the directory
CAP_Y, BAR_Y, CMD_Y = -3.25, -2.72, 3.08


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


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def harrow(a, b, color=GREY_B, sw=3):
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.12, max_stroke_width_to_length_ratio=8)


def dot_run(a, b, color=YELLOW_M, rt=0.7):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


def run(arrow, color=YELLOW_M, rt=0.7):
    return dot_run(arrow.get_start(), arrow.get_end(), color, rt)


# ---- the pieces ----
def book(cx, top, bot, w, color, num):
    """A box drawn as a book: the number sits on its spine."""
    r = RoundedRectangle(corner_radius=0.12, width=w, height=top - bot, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([cx, (top + bot) / 2, 0])
    x0 = cx - w / 2
    sp = Rectangle(width=SPINE, height=top - bot - 0.06, stroke_width=0).set_fill(fillc(color, 0.38), 1)
    sp.move_to([x0 + SPINE / 2 + 0.03, (top + bot) / 2, 0])
    n = T(num, 24).move_to([x0 + SPINE / 2 + 0.03, top - 0.38, 0])
    return VGroup(r, sp, n)


def card(k, name, num, color=DIR_C):
    y = CARD_Y[k]
    r = RoundedRectangle(corner_radius=0.08, width=CARD_W, height=CARD_H, stroke_color=color, stroke_width=2.2).set_fill(BLACK, 1)
    r.move_to([DCX, y, 0])
    return VGroup(r, left_at(M(name, 20), DX0 + 0.38, y), right_at(M("→ " + num, 20, color), DX1 - 0.38, y))


def card_arrow(k, target_y, color=GREY_B):
    return harrow([DX1 + 0.05, CARD_Y[k], 0], [IX0 - 0.07, target_y, 0], color)


def field(k, label, val, color=WHITE):
    g = VGroup(left_at(T(label, 20, GREY_B), LAB_X, FY[k]))
    if val is not None:
        g.add(left_at(M(val, 18, color), VAL_X, FY[k]))
    return g


def cells():
    g = VGroup(*[Square(CELL, stroke_color=GREY_D, stroke_width=2).set_fill(BLACK, 1) for _ in range(16)])
    return g.arrange_in_grid(4, 4, buff=GAP).move_to([GCX, GCY, 0])


def gold(c):
    return c.animate.set_stroke(GOLD_M, 2.5).set_fill(fillc(GOLD_M, 0.45), 1)


def grey(c):
    return c.animate.set_stroke(GREY_D, 2).set_fill(BLACK, 1)


# the naive table: one row per name
TC = [-6.45, -3.6, -0.75, 0.95]
TH_Y, TR_Y = 2.05, [1.35, 0.6]


def trow(vals, y, size=20, color=WHITE):
    return VGroup(*[left_at((T if size < 20 else M)(v, 22 if size < 20 else size, color), TC[i], y) for i, v in enumerate(vals)])


class InodesLinks(Base):
    """os-10, section 0. A deleted 20 GB log leaves the disk 98 percent full: what did delete remove? One row per name
    breaks when ledger.csv (2 GB) needs a second name. The library: a numbered book (the inode) and catalogue cards
    (directory entries). Opening /tmp/ledger.csv walks the directories. A hard link is a second card (links 2); a
    symlink is a "see under" card, inode 12 holding the 10 bytes ledger.csv. rm ledger.csv: the hard link still works,
    the symlink fails, no block is freed. rm is unlink; a file is freed when links is 0 and no program has it open
    (the log). Limits, moral, and a check: a new ledger.csv, and where latest.csv leads now."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def cmd(self, s):
        new = None
        if s:
            t = M(s, 22, WHITE)
            r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.5, height=0.52, stroke_color=GREY_C, stroke_width=2).set_fill("#111111", 1)
            new = VGroup(r, t.move_to(r)).move_to([ICX, CMD_Y, 0])
        old, self.cmdm = self.cmdm, new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def setf(self, k, label, val, color=WHITE):
        new = field(k, label, val, color)
        old, self.f[k] = self.f[k], new
        return [swap(old, new, RIGHT)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.cmdm = None
        self.f = [None] * 4
        self.title_card("A file's name only points to it", "inodes, hard links and symlinks")

        # ---------------- scene 1: the full disk ----------------
        fold = RoundedRectangle(corner_radius=0.14, width=5.0, height=2.2, stroke_color=DIR_C, stroke_width=3).set_fill(fillc(DIR_C), 1)
        fold.move_to([-3.3, 0.5, 0])
        fold_t = left_at(T("the log folder", 24), -5.5, 1.2)
        logrow = VGroup(left_at(M("auth.log", 24), -5.5, 0.25), right_at(M("20 GB", 24), -1.1, 0.25))
        gx0, gw = 1.5, 4.6
        gauge = RoundedRectangle(corner_radius=0.1, width=gw, height=0.6, stroke_color=GREY_B, stroke_width=2.5).move_to([gx0 + gw / 2, 0.5, 0])
        gfill = Rectangle(width=gw * 0.98 - 0.08, height=0.48, stroke_width=0).set_fill(RED_M, 0.75)
        left_at(gfill, gx0 + 0.04, 0.5)
        gt = left_at(T("the disk", 24), gx0, 1.2)
        gv = right_at(T("98 percent full", 24, RED_M), gx0 + gw, -0.25)
        self.steps("A small company's program records card payments for coffee shops. It also writes a line about every payment "
                   "to a log file, and the log has grown to 20 GB.", [
            "It also writes",
            (lambda: [FadeIn(fold), FadeIn(fold_t)], 0.7),
            "a log file",
            (lambda: [FadeIn(logrow, shift=0.1 * DOWN)], 0.6),
        ])
        qm = T("?", 64, YELLOW_M).move_to([0, 2.6, 0])
        self.steps("One evening the disk is 98 percent full, so someone deletes the log. It vanishes from the folder. "
                   "And the disk is still 98 percent full.", [
            (lambda: [Create(gauge), FadeIn(gt)], 0.6),
            (lambda: [GrowFromEdge(gfill, LEFT), FadeIn(gv)], 0.8),
            "someone deletes",
            (lambda: [logrow.animate.set_color(RED_M)], 0.4),
            "It vanishes",
            (lambda: [FadeOut(logrow, shift=0.3 * LEFT)], 0.7),
            "And the disk",
            (lambda: [glow(gauge, RED_M, 1.03), Indicate(gv, color=RED_M, scale_factor=1.15)], 1.0),
        ])
        self.steps("So what did delete actually remove? Hold that question.", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.4)

        # ---------------- scene 2: what a file system stores ----------------
        grid = cells()
        g_t = T("disk blocks", 22).move_to([GCX, GCY + 1.43, 0])
        g_s = T("4 KB each", 18, GREY_B).move_to([GCX, GCY - 1.35, 0])
        f0 = 0.32
        page = Polygon([-0.75, 1.0, 0], [0.75 - f0 * 1.6, 1.0, 0], [0.75, 1.0 - f0 * 1.6, 0], [0.75, -1.0, 0], [-0.75, -1.0, 0],
                       stroke_color=WHITE, stroke_width=3).set_fill("#15191d", 1)
        lines = VGroup(*[Line([-0.45, y, 0], [0.45 - 0.25 * (i % 2), y, 0], stroke_width=2.5, color=GREY_C) for i, y in enumerate([0.2, -0.15, -0.5])])
        icon = VGroup(page, lines).move_to([-1.2, 0.6, 0])
        iname = M("ledger.csv", 26).next_to(icon, DOWN, buff=0.3)
        trash = VGroup(RoundedRectangle(corner_radius=0.08, width=1.0, height=1.2, stroke_color=GREY_B, stroke_width=3),
                       Line([-0.65, 0.72, 0], [0.65, 0.72, 0], stroke_width=3, color=GREY_B),
                       *[Line([x, 0.4, 0], [x, -0.4, 0], stroke_width=2, color=GREY_C) for x in (-0.25, 0, 0.25)]).move_to([2.6, 0.3, 0])
        self.steps("It's easy to think a file is its name. A file browser shows it that way: one name, one icon, and delete takes both.", [
            (lambda: [FadeOut(VGroup(fold, fold_t, gauge, gfill, gt, gv, qm))], 0.8),
            "A file browser",
            (lambda: [FadeIn(icon, shift=0.1 * UP), FadeIn(iname)], 0.6),
            "one name, one icon",
            (lambda: [Indicate(iname, color=YELLOW_M), *self.cap("one name, one icon", WHITE)], 0.7),
            "and delete takes both",
            (lambda: [FadeIn(trash)], 0.4),
            (lambda: [VGroup(icon, iname).animate.scale(0.25).move_to(trash.get_center() + 0.1 * UP).set_opacity(0)], 0.7),
        ])
        self.remove(icon, iname)
        hdr = trow(["name", "size", "owner", "blocks"], TH_Y, 19, GREY_B)
        hline = Line([TC[0], TH_Y - 0.3, 0], [IX1, TH_Y - 0.3, 0], stroke_width=1.5, color=GREY_D)
        self.steps("So look at what has to be stored. A disk is a long row of equal pieces called blocks, 4 KB each.", [
            (lambda: [*self.uncap(), FadeOut(trash)], 0.4),
            "A disk is",
            (lambda: [FadeIn(g_t), LaggedStart(*[FadeIn(c) for c in grid], lag_ratio=0.08), FadeIn(g_s)], 1.4),
        ])
        self.steps("For every file, the file system, the part of the operating system that looks after files, records which blocks "
                   "hold its bytes, its size, its owner, who may read it, and when it last changed.", [
            "records which",
            (lambda: [FadeIn(hdr), Create(hline)], 0.8),
            "who may read it",
            (lambda: self.cap("which blocks, size, owner, who may read it, when it changed"), 0.5),
        ])

        # ---------------- scene 3: one row per name ----------------
        r1 = trow(["ledger.csv", "2 GB", "payments", "2065, ..."], TR_Y[0])
        r2 = trow(["ledger-2026.csv", "2 GB", "payments", "2065, ..."], TR_Y[1])
        self.steps("The simplest design keeps all of that next to the name: one row per file.", [
            (lambda: self.uncap(), 0.3),
            "one row per file",
            (lambda: [FadeIn(r1, shift=0.1 * DOWN), *[gold(grid[i]) for i in FILE]], 0.8),
        ])
        self.steps("It breaks on the first file you want under two names. The payments program keeps the year's payments in ledger.csv, 2 GB.", [
            "in ledger.csv",
            (lambda: [Indicate(r1[0], color=YELLOW_M), Indicate(r1[1], color=YELLOW_M)], 0.8),
        ])
        self.steps("An auditor wants the same file as ledger-2026.csv, without a copy. Now two rows must agree forever.", [
            "An auditor",
            (lambda: [FadeIn(r2, shift=0.1 * DOWN)], 0.8),
            "Now two rows",
            (lambda: [Indicate(r1[1], color=YELLOW_M), Indicate(r2[1], color=YELLOW_M)], 0.9),
        ])
        x2 = tick(False, 0.15).move_to([TC[1] + 0.95, TR_Y[1], 0])
        r1s = left_at(M("2 GB + 31 bytes", 20, GOLD_M), TC[1], TR_Y[0])
        self.steps("Add one payment through ledger.csv, and its row grows by 31 bytes. The other row still says 2 GB.", [
            (lambda: [dot_run([TC[0] - 0.2, TR_Y[0] + 0.45, 0], [TC[0] + 0.8, TR_Y[0] + 0.1, 0])], 0.6),
            "its row grows",
            (lambda: [Transform(r1[1], r1s), gold(grid[10])], 0.7),
            "The other row",
            (lambda: [r2[1].animate.set_color(RED_M), Create(x2), *self.cap("two rows, two sizes", RED_M)], 0.7),
        ])
        self.steps("Forever didn't last long. We want one place that holds the file, and names that only point to it.", [
            "We want",
            (lambda: self.cap("one place for the file; names only point to it", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 4: the library ----------------
        bk = book(ICX, TOP, BOT, IX1 - IX0, BLUE_M, "13")
        bk_t = left_at(T("book", 26), LAB_X, TOP - 0.38)
        pages = VGroup(*[Line([LAB_X, y, 0], [IX1 - 0.4 - 0.5 * (i % 2), y, 0], stroke_width=2, color=GREY_D)
                         for i, y in enumerate([1.25, 0.85, 0.45, 0.05, -0.35])])
        lc = [card(0, "title: Ledger", "13"), card(1, "author: Okafor", "13")]
        la = [card_arrow(0, TOP - 0.55), card_arrow(1, TOP - 0.85)]
        cat_t = left_at(T("catalogue", 24), DX0 + 0.25, TOP - 0.38)
        self.steps("Libraries solved this long ago. Every book has a number on its spine, and a catalogue card says: this title, book 13.", [
            (lambda: [FadeOut(VGroup(hdr, hline, r1, r2, x2)), *self.uncap()], 0.7),
            "Every book",
            (lambda: [FadeIn(bk[0]), FadeIn(bk[1]), FadeIn(bk_t), Create(pages)], 0.8),
            "on its spine",
            (lambda: [FadeIn(bk[2], scale=1.4)], 0.5),
            "a catalogue card",
            (lambda: [FadeIn(cat_t), FadeIn(lc[0], shift=0.1 * RIGHT)], 0.6),
            "book 13",
            (lambda: [GrowArrow(la[0])], 0.5),
        ])
        self.steps("One book can have a card under its title and another under its author, and neither card is the book.", [
            "another under",
            (lambda: [FadeIn(lc[1], shift=0.1 * RIGHT), GrowArrow(la[1])], 0.7),
            "neither card",
            (lambda: [glow(lc[0][0], DIR_C, 1.02), glow(lc[1][0], DIR_C, 1.02)], 0.8),
            (lambda: [glow(bk[0], BLUE_M, 1.02)], 0.7),
        ])
        dirb = RoundedRectangle(corner_radius=0.14, width=DX1 - DX0, height=TOP - BOT, stroke_color=DIR_C, stroke_width=3)
        dirb.set_fill(fillc(DIR_C, 0.08), 1).move_to([DCX, CY, 0]).set_z_index(-1)
        dir_t = left_at(T("directory /tmp", 24), DX0 + 0.25, TOP - 0.38)
        ino_t = left_at(T("inode", 26), LAB_X, TOP - 0.38)
        blk_arrow = harrow([IX1 + 0.08, FY[3], 0], [GCX - 1.0 - 0.1, FY[3], 0], GOLD_M)
        self.steps("Linux splits the row the same way. Everything about the file moves into "
                   "one box with a number and no name: size, owner, permissions, times, a count of links, and the list of blocks.", [
            "Everything about",
            (lambda: [FadeOut(pages)], 0.4),
            "size, owner",
            (lambda: [*self.setf(0, "size", "2 GB + 31 bytes")], 0.4),
            "permissions",
            (lambda: [*self.setf(1, "owner, permissions, times", None)], 0.4),
            "a count of links",
            (lambda: [*self.setf(2, "links", "1")], 0.4),
            "the list of blocks",
            (lambda: [*self.setf(3, "blocks", "2065, ..."), GrowArrow(blk_arrow)], 0.6),
        ])
        self.steps("That's the numbered book. It's called an inode, short for index node.", [
            (lambda: [glow(bk[0], BLUE_M, 1.02)], 0.7),
            "It's called",
            (lambda: [swap(bk_t, ino_t), *self.cap("the book: an inode (index node), a number and no name", BLUE_M)], 0.7),
        ])
        c0 = card(0, "ledger.csv", "13")
        a0 = card_arrow(0, TOP - 0.55)
        self.steps("The folder keeps only the cards: each entry is a name and an inode number. Linux calls a folder a directory.", [
            (lambda: [FadeOut(lc[1]), FadeOut(la[1]), swap(lc[0], c0)], 0.8),
            "each entry",
            (lambda: [Indicate(c0[1], color=DIR_C), Indicate(c0[2], color=DIR_C)], 0.8),
            "Linux calls",
            (lambda: [FadeIn(dirb), swap(cat_t, dir_t), *self.cap("a card: a directory entry, a name and an inode number", DIR_C)], 0.8),
        ])
        self.remove(lc[0], la[0])
        self.add(a0)

        # ---------------- scene 5: opening a file ----------------
        root = RoundedRectangle(corner_radius=0.1, width=DX1 - DX0, height=0.6, stroke_color=DIR_C, stroke_width=2.5).set_fill(fillc(DIR_C), 1)
        root.move_to([DCX, ROOT_Y, 0])
        root_t = VGroup(left_at(T("directory /", 22), DX0 + 0.25, ROOT_Y), right_at(M("tmp →", 20, DIR_C), DX1 - 0.38, ROOT_Y))
        down_a = Arrow([DCX + 1.2, ROOT_Y - 0.31, 0], [DCX + 1.2, TOP + 0.03, 0], buff=0, stroke_width=3, color=DIR_C,
                       max_tip_length_to_length_ratio=0.45, max_stroke_width_to_length_ratio=10)
        self.steps("To open /tmp/ledger.csv, the kernel, the core of the operating system, reads the top directory and finds tmp.", [
            (lambda: [*self.uncap()], 0.3),
            "reads the top",
            (lambda: [FadeIn(root), FadeIn(root_t)], 0.6),
            "finds tmp",
            (lambda: [GrowArrow(down_a), Indicate(root_t[1], color=YELLOW_M)], 0.6),
        ])
        self.steps("It reads tmp and finds ledger.csv, 13. Then it reads inode 13.", [
            (lambda: [run(down_a)], 0.6),
            "finds ledger.csv",
            (lambda: [glow(c0[0], YELLOW_M, 1.02)], 0.6),
            "Then it reads",
            (lambda: [run(a0)], 0.6),
            (lambda: [glow(bk[0], YELLOW_M, 1.02), run(blk_arrow)], 0.7),
        ])
        self.steps("Here the library picture breaks: a library has one flat catalogue, but folders sit inside folders.", [
            (lambda: self.cap("a library: one flat catalogue.   files: folders inside folders"), 0.6),
            "folders sit inside",
            (lambda: [glow(root, DIR_C, 1.02), glow(dirb, DIR_C, 1.01)], 0.9),
        ], after=0.4)

        # ---------------- scene 6: a second card ----------------
        c1 = card(1, "ledger-2026.csv", "13")
        a1 = card_arrow(1, TOP - 0.85)
        self.steps("Now the auditor's name is easy. Add a second entry with the same number. That's a hard link.", [
            (lambda: [FadeOut(VGroup(root, root_t, down_a)), *self.uncap(), *self.cmd("$ ln ledger.csv ledger-2026.csv")], 0.7),
            "Add a second",
            (lambda: [FadeIn(c1, shift=0.1 * RIGHT)], 0.6),
            (lambda: [GrowArrow(a1)], 0.5),
            "That's a hard link",
            (lambda: self.cap("a hard link: a second card with the same number", WHITE), 0.5),
        ])
        self.steps("The inode counts its entries: links, 2. Add a payment through either name, and there's only one size to change.", [
            "links, 2",
            (lambda: self.setf(2, "links", "2", GOLD_M), 0.6),
            "Add a payment",
            (lambda: [run(a1, GOLD_M)], 0.7),
            (lambda: [*self.setf(0, "size", "2 GB + 62 bytes", GOLD_M), gold(grid[13])], 0.6),
            "only one size",
            (lambda: [Indicate(self.f[0][1], color=GOLD_M, scale_factor=1.1)], 0.8),
        ])

        # ---------------- scene 7: a card that says "see under" ----------------
        c2 = card(2, "latest.csv", "12", PURPLE_M)
        sym = book(ICX, SYM_TOP, SYM_BOT, IX1 - IX0, PURPLE_M, "12")
        sym_t = VGroup(left_at(T("symlink, 10 bytes:", 20, GREY_B), LAB_X, SYM_TOP - 0.32), left_at(M("ledger.csv", 20, PURPLE_M), LAB_X, SYM_TOP - 0.7))
        a2 = harrow([DX1 + 0.05, CARD_Y[2] - 0.05, 0], [IX0 - 0.07, SYM_CY + 0.15, 0], PURPLE_M)
        self.steps("There's a second kind of link: a card that says, see under Ledger. That's a symbolic link, or symlink.", [
            (lambda: [*self.cmd("$ ln -s ledger.csv latest.csv"), *self.setf(2, "links", "2"), *self.setf(0, "size", "2 GB + 62 bytes"),
                      *self.uncap()], 0.6),
            "a card that says",
            (lambda: [FadeIn(c2, shift=0.1 * RIGHT)], 0.6),
            "That's a symbolic",
            (lambda: self.cap("a symlink: a card that says \"see under\"", PURPLE_M), 0.5),
        ])

        self.steps("latest.csv is an inode of its own, number 12, and its content is a path, the 10 bytes ledger.csv.", [
            "an inode of its own",
            (lambda: [GrowArrow(a2), FadeIn(sym)], 0.7),
            "its content",
            (lambda: [FadeIn(sym_t, shift=0.1 * RIGHT)], 0.6),
        ])
        word = sym_t[1].copy()
        self.steps("The kernel looks that name up again every time the link is opened.", [
            (lambda: [run(a2, YELLOW_M)], 0.6),
            "looks that name",
            (lambda: [word.animate.move_to(c0[1].get_center() + 0.0 * UP)], 0.8),
            (lambda: [FadeOut(word), glow(c0[0], YELLOW_M, 1.02)], 0.5),
            (lambda: [run(a0)], 0.6),
            (lambda: [glow(bk[0], YELLOW_M, 1.02)], 0.6),
        ], after=0.4)

        # ---------------- scene 8: predict: delete ledger.csv ----------------
        self.steps("Now delete ledger.csv. Afterwards, which name still works: ledger-2026.csv, or latest.csv? Pause and guess.", [
            (lambda: [*self.uncap(), *self.cmd("$ rm ledger.csv")], 0.6),
            "which name",
            (lambda: [c1[0].animate.set_stroke(YELLOW_M, 3.5), c2[0].animate.set_stroke(YELLOW_M, 3.5)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The entry is gone, and links drops to 1. ledger-2026.csv still leads to inode 13, every byte intact.", [
            (lambda: [*self.uncap(), c0.animate.set_color(RED_M), a0.animate.set_color(RED_M)], 0.5),
            (lambda: [FadeOut(c0, shift=0.3 * LEFT), FadeOut(a0)], 0.6),
            "links drops",
            (lambda: self.setf(2, "links", "1", GOLD_M), 0.6),
            "still leads",
            (lambda: [run(a1, YELLOW_M)], 0.7),
            (lambda: [run(blk_arrow, YELLOW_M), c1[0].animate.set_stroke(GREEN_M, 3.5), *self.cap("ledger-2026.csv: works", GREEN_M)], 0.7),
        ])
        word2 = sym_t[1].copy()
        empty = DashedVMobject(RoundedRectangle(corner_radius=0.08, width=CARD_W, height=CARD_H).set_stroke(RED_M, 2).move_to([DCX, CARD_Y[0], 0]),
                               num_dashes=40)
        nf = T("No such file or directory", 20, RED_M).move_to([DCX, CARD_Y[0], 0])
        self.steps("latest.csv looks up ledger.csv, finds nothing, and fails. And not one block was freed.", [
            (lambda: [run(a2, YELLOW_M)], 0.6),
            "looks up",
            (lambda: [word2.animate.move_to([DCX, CARD_Y[0], 0])], 0.7),
            (lambda: [FadeOut(word2), Create(empty), FadeIn(nf)], 0.5),
            "and fails",
            (lambda: [c2[0].animate.set_stroke(RED_M, 3.5), *self.cap("latest.csv: fails", RED_M)], 0.4),
            "not one block",
            (lambda: [LaggedStart(*[Indicate(grid[i], color=GOLD_M, scale_factor=1.12) for i in FILE + [10, 13]], lag_ratio=0.12),
                      *self.cap("blocks freed: 0", GOLD_M)], 1.0),
        ], after=0.4)

        # ---------------- scene 9: rm is unlink, and when a file is freed ----------------
        self.steps("So rm, the delete command, doesn't really delete. It sends the kernel a request called unlink: "
                   "remove one entry, and lower the count by one.", [
            (lambda: [FadeOut(VGroup(empty, nf)), *self.setf(2, "links", "1"), c1[0].animate.set_stroke(DIR_C, 2.2),
                      c2[0].animate.set_stroke(PURPLE_M, 2.2)], 0.6),
            "a request called",
            (lambda: [*self.cmd("rm  →  unlink"), *self.cap("unlink: remove one entry, lower the count by one", WHITE)], 0.6),
        ])
        self.steps("rm sounds like a shredder. It's really an eraser for one card.", [
            "an eraser",
            (lambda: [glow(c1[0], DIR_C, 1.03)], 0.8),
        ], after=0.4)
        rule = T("freed when links = 0 and no program has it open", 24, WHITE).move_to([0, CAP_Y, 0])
        self.steps("The kernel frees a file only when the count reaches 0 and no program still has it open, like a library that "
                   "throws a book out only when no card points to it and nobody has it borrowed.", [
            (lambda: [*self.cmd(None), swap(self.capm, rule)], 0.7),
            "like a library",
            (lambda: [glow(bk[0], BLUE_M, 1.02)], 0.8),
            "nobody has it",
            (lambda: [Indicate(rule, color=YELLOW_M, scale_factor=1.06)], 0.8),
        ])
        self.capm = rule
        self.steps("Delete ledger-2026.csv too, and the count is 0. Nobody has it open, so the kernel frees it, and its blocks are free again.", [
            (lambda: [*self.cmd("$ rm ledger-2026.csv"), c1.animate.set_color(RED_M), a1.animate.set_color(RED_M)], 0.5),
            (lambda: [FadeOut(c1, shift=0.3 * LEFT), FadeOut(a1)], 0.6),
            "the count is 0",
            (lambda: self.setf(2, "links", "0", RED_M), 0.6),
            "the kernel frees",
            (lambda: [FadeOut(VGroup(bk, ino_t, *[f for f in self.f], blk_arrow)), *[grey(grid[i]) for i in FILE + [10, 13]]], 0.9),
        ], after=0.3)
        self.f = [None] * 4
        lg = book(ICX, TOP, BOT, IX1 - IX0, BLUE_M, "0")[:2]
        lg_t = left_at(T("the log's inode", 26), LAB_X, TOP - 0.38)
        lg_f = VGroup(field(0, "size", "20 GB"), field(1, "owner, permissions, times", None), field(2, "links", "0", RED_M),
                      field(3, "blocks", "nearly all"))
        lg_a = harrow([IX1 + 0.08, FY[3], 0], [GCX - 1.0 - 0.1, FY[3], 0], GOLD_M)
        prog = RoundedRectangle(corner_radius=0.12, width=2.6, height=1.0, stroke_color=GREY_B, stroke_width=3).set_fill("#15191d", 1)
        prog.move_to(PROG_C)
        prog_t = VGroup(T("payments program", 19), T("still writing to it", 17, GREY_B)).arrange(DOWN, buff=0.1).move_to(PROG_C)
        open_a = harrow(PROG_C + [-1.35, 0.45, 0], [IX1 + 0.08, BOT + 0.15, 0], WHITE)
        self.steps("Now our full disk. The log lost its last name, but the payments program still had it open, writing a line every second.", [
            (lambda: [*self.cmd(None), *self.uncap(), FadeIn(lg), FadeIn(lg_t), FadeIn(lg_f), GrowArrow(lg_a),
                      *[gold(grid[i]) for i in range(16) if i != 15]], 0.9),
            "lost its last name",
            (lambda: [Indicate(lg_f[2][1], color=RED_M, scale_factor=1.3)], 0.7),
            "still had it open",
            (lambda: [FadeIn(prog), FadeIn(prog_t), GrowArrow(open_a)], 0.7),
            "writing a line",
            (lambda: [run(open_a, WHITE, 0.5)], 0.5),
            (lambda: [run(open_a, WHITE, 0.5)], 0.5),
        ])
        self.steps("It's borrowed. So all 20 GB stayed. Later in the lesson, we'll find that file and free it.", [
            (lambda: [glow(lg[0], WHITE, 1.02), *self.cap("links 0, but still open: the kernel keeps all 20 GB", WHITE)], 0.8),
            "all 20 GB",
            (lambda: [LaggedStart(*[Indicate(grid[i], color=GOLD_M, scale_factor=1.12) for i in range(15)], lag_ratio=0.05)], 1.0),
        ], after=0.4)

        # ---------------- scene 10: two limits ----------------
        other = book(ICX, CY + 0.8, CY - 0.8, IX1 - IX0, GREY_B, "13")
        other_t = VGroup(T("on another disk", 20, GREY_B), T("inode 13: a cookbook", 22)).arrange(DOWN, buff=0.15)
        left_at(other_t, LAB_X, CY)
        cross_a = harrow([DX1 + 0.05, CARD_Y[0], 0], [IX0 - 0.07, CY + 0.3, 0], RED_M)
        cross_x = tick(False, 0.15).move_to(cross_a.get_center() + 0.28 * UP)
        self.steps("Two limits on hard links. A hard link holds only a number, so it can't reach into another file system.", [
            (lambda: [*self.cap("a hard link holds only a number", WHITE), FadeOut(VGroup(lg, lg_t, lg_f, lg_a, prog, prog_t, open_a)),
                      *[grey(grid[i]) for i in range(16)]], 0.7),
            "another file system",
            (lambda: [FadeIn(other), FadeIn(other_t)], 0.6),
        ])
        self.steps("Book 13 in another library is a different book, maybe a cookbook.", [
            (lambda: [GrowArrow(cross_a)], 0.5),
            (lambda: [Create(cross_x)], 0.4),
            "maybe a cookbook",
            (lambda: [Indicate(other_t[1], color=GOLD_M, scale_factor=1.15)], 0.8),
        ], after=0.3)
        loop_a = CurvedArrow(np.array([DX1 + 0.06, TOP - 0.55, 0]), np.array([DX1 + 0.06, ROOT_Y, 0]), angle=2.2,
                             color=RED_M, stroke_width=3, tip_length=0.18)
        loop_x = tick(False, 0.14).move_to([DX1 + 0.47, (TOP - 0.55 + ROOT_Y) / 2, 0])
        loop_t = left_at(T("a second name for / inside /tmp", 20, RED_M), DX1 + 0.85, (TOP - 0.55 + ROOT_Y) / 2)
        self.steps("And Linux refuses hard links to directories, which could put a folder inside itself, a loop.", [
            (lambda: [FadeOut(VGroup(other, other_t, cross_a, cross_x)), FadeIn(root), FadeIn(root_t), GrowArrow(down_a)], 0.7),
            "a folder inside itself",
            (lambda: [Create(loop_a), *self.cap("no hard links to directories: no loops", WHITE)], 0.7),
            (lambda: [Create(loop_x), FadeIn(loop_t)], 0.5),
        ], after=0.4)

        # ---------------- scene 11: the moral, and a check ----------------
        self.steps("So, what did delete remove? One name. The file is its inode, names are cards that point to it, "
                   "and the kernel frees it only when no card and no program is left.", [
            (lambda: [FadeOut(VGroup(loop_a, loop_x, loop_t, root, root_t, down_a)), *self.cap("what did delete remove?", WHITE)], 0.6),
            "One name",
            (lambda: self.cap("one name", YELLOW_M, 30), 0.5),
            "The file is",
            (lambda: self.cap("the file is its inode; names are cards that point to it", WHITE), 0.5),
            "and the kernel",
            (lambda: self.cap("freed only when no card and no program is left", GREEN_M), 0.5),
        ], after=0.5)
        nc = card(0, "ledger.csv", "14")
        na = card_arrow(0, TOP - 0.55)
        nb = book(ICX, TOP, BOT, IX1 - IX0, BLUE_M, "14")
        nb_t = left_at(T("inode", 26), LAB_X, TOP - 0.38)
        nf0 = [field(0, "size", "0 bytes"), field(1, "owner, permissions, times", None), field(2, "links", "1")]
        self.steps("One quick check. Someone makes a new, empty ledger.csv. Now you open latest.csv. What do you get? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "Someone makes",
            (lambda: [FadeIn(nc, shift=0.1 * RIGHT), FadeIn(VGroup(nb, nb_t, *nf0))], 0.7),
            (lambda: [GrowArrow(na)], 0.4),
            "Now you open",
            (lambda: [run(a2, YELLOW_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        word3 = sym_t[1].copy()
        self.steps("The new, empty file. A symlink holds a name, not a number, so it follows whatever has that name now.", [
            (lambda: [*self.uncap(), word3.animate.move_to(nc[1])], 0.7),
            (lambda: [FadeOut(word3), glow(nc[0], YELLOW_M, 1.02)], 0.4),
            (lambda: [run(na)], 0.5),
            (lambda: [glow(nb[0], YELLOW_M, 1.02), Indicate(nf0[0][1], color=YELLOW_M)], 0.7),
            "A symlink holds",
            (lambda: self.cap("a symlink holds a name, not a number", PURPLE_M, 28), 0.6),
        ], after=0.4)
        self.wait(2.0)
