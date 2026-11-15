from sfz import *

SAY.insert(0, (r"\bledger-2026\.csv\b", "ledger twenty twenty-six dot C S V"))
SAY.insert(0, (r"\bledger\.csv\b", "ledger dot C S V"))
SAY.insert(0, (r"\binode\b", "eye node"))
SAY.insert(0, (r"\binodes\b", "eye nodes"))
SAY.insert(0, (r"\brm\b", "R M"))
SAY.insert(0, (r"\bdu\b", "D U"))
SAY.insert(0, (r"\bdf\b", "D F"))

DX, IX, BX = -4.55, 0.6, 4.95        # directory, inode, disk blocks
RY = 1.15                            # their common centre line
DW, IW, BOXH = 3.8, 4.1, 3.0         # directory and inode widths
PY = -1.85                           # the process holding the file open
ST_Y = -3.2                          # status line
FIELD_Y = [RY + 0.45, RY - 0.05, RY - 0.55, RY - 1.05]
ENTRY_Y = [RY + 0.35, RY - 0.4]
FILE_BLOCKS = [1, 2, 6, 7, 11]       # cells of the grid that hold ledger.csv
NEW_BLOCK, NEW_BLOCK2 = 12, 16


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=0.7, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.12))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


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


def panel(x, w, title, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=BOXH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, RY, 0])
    return VGroup(r, T(title, 30).move_to([x, RY + 1.05, 0]))


def field_label(s, k):
    return left_at(T(s, 26, GREY_B), IX - 1.8, FIELD_Y[k])


def field_val(s, k, color=WHITE):
    return left_at(M(s, 23, color), IX - 0.45, FIELD_Y[k])


def entry(name, k, color=WHITE):
    n = left_at(M(name, 22, color), DX - 1.7, ENTRY_Y[k])
    num = M("13", 23, color).move_to([DX + 1.5, ENTRY_Y[k], 0])
    return VGroup(n, num)


def entry_arrow(k, color=GREY_B):
    s = [DX + DW / 2 + 0.05, ENTRY_Y[k], 0]
    e = [IX - IW / 2 - 0.08, RY + (0.3 if k == 0 else -0.3), 0]
    return Arrow(s, e, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.08)


def status(s, color=GREY_B):
    return T(s, 28, color).move_to([0, ST_Y, 0])


# the naive design: one row per name, holding everything
TCOL = [-6.3, -3.15, -0.6, 0.9]


def trow(cells, y, colors=None, size=23):
    colors = colors or [WHITE] * len(cells)
    return VGroup(*[left_at(M(c, size, col), TCOL[i], y) for i, (c, col) in enumerate(zip(cells, colors))])


class InodesLinks(Base):
    """os-10, section 0 (with section 2's deleted-but-open file): ledger.csv, 2 GB, wanted under a second name. A row per
    name with size and blocks breaks on the first append. The inode holds the file; a directory entry is a name and an
    inode number; a hard link is a second entry; rm drops one entry and the link count. A JVM holding fd 4 keeps the
    inode alive after the last name goes (du 0, df 2 GB) until it closes."""

    def construct(self):
        self.title_card("Inodes and links", "a file has a number, and names only point at it")

        # ---- the disk and the naive table ------------------------------------------------------------------------
        cells = VGroup(*[Square(0.45, stroke_color=GREY_D, stroke_width=2).set_fill(BLACK, 1) for _ in range(20)])
        cells.arrange_in_grid(4, 5, buff=0.1).move_to([BX, RY - 0.2, 0])
        btitle = T("disk blocks, 4 KB each", 24, GREY_B).move_to([BX, RY + 1.05, 0])
        hdr = trow(["name", "size", "owner", "blocks"], 2.2, [GREY_B] * 4)
        hline = Line([-6.3, 1.85, 0], [2.85, 1.85, 0], stroke_width=1.5, color=GREY_D)
        r1 = trow(["ledger.csv", "2 GB", "settle", "2065, ..."], 1.35)
        q2 = left_at(M("ledger-2026.csv ?", 23, GOLD_M), TCOL[0], 0.6)
        self.steps("The settlement job writes a two gigabyte file, ledger.csv. The audit export wants the same file "
                   "under a second name, ledger-2026.csv, without a copy. How can one file have two names?", [
            (lambda: [FadeIn(cells, lag_ratio=0.03), FadeIn(btitle)], 1.0),
            (lambda: [FadeIn(hdr), Create(hline), FadeIn(r1, shift=0.1 * DOWN),
                      *[cells[i].animate.set_stroke(BLUE_M, 2.5).set_fill(fillc(BLUE_M, 0.35), 1) for i in FILE_BLOCKS]], 1.0),
            "under a second name",
            (lambda: [FadeIn(q2, shift=0.1 * DOWN)], 0.7),
        ])

        r2 = trow(["ledger-2026.csv", "2 GB", "settle", "2065, ..."], 0.6)
        self.steps("The simple design keeps the size, the owner and the blocks next to the name. "
                   "A second name is a second row with the same values.", [
            (lambda: [*[glow_text(h) for h in hdr]], 1.0),
            "A second name",
            (lambda: [FadeOut(q2), FadeIn(r2, shift=0.1 * DOWN)], 0.8),
        ])

        x3 = tick(False, 0.2).move_to([TCOL[2] - 0.35, 0.6, 0])
        st = status("two copies of the size, and they disagree", RED_M)
        self.steps("Append a record through ledger.csv, and only its row grows. "
                   "The other row still says two gigabytes. The two rows disagree.", [
            (lambda: [glow_text(r1[0], BLUE_M)], 0.6),
            (lambda: [cells[NEW_BLOCK].animate.set_stroke(GOLD_M, 2.5).set_fill(fillc(GOLD_M, 0.4), 1),
                      Transform(r1[1], left_at(M("2 GB + 4 KB", 23, GOLD_M), TCOL[1], 1.35))], 0.9),
            "still says",
            (lambda: [r2[1].animate.set_color(RED_M), Create(x3)], 0.6),
            "The two rows disagree",
            (lambda: [FadeIn(st, shift=0.1 * UP)], 0.6),
        ])

        # ---- split the row: the inode ------------------------------------------------------------------------------
        ino = panel(IX, IW, "inode 13", BLUE_M)
        labels = VGroup(*[field_label(s, k) for k, s in enumerate(["size", "owner", "links", "blocks"])])
        vals = [field_val("2 GB + 4 KB", 0), field_val("settle", 1), field_val("1", 2), field_val("2065, ...", 3)]
        barrow = Arrow([IX + IW / 2 + 0.08, FIELD_Y[3], 0], [cells.get_left()[0] - 0.1, FIELD_Y[3], 0], buff=0,
                       stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.12)
        self.steps("So Unix splits the row. The inode is the file itself: size, owner, a count of names, "
                   "and the list of blocks. It has a number, 13, and no name.", [
            (lambda: [FadeOut(VGroup(hdr, hline, r1, r2, x3, st))], 0.6),
            "The inode",
            (lambda: [FadeIn(ino[0]), FadeIn(ino[1])], 0.6),
            (lambda: [LaggedStart(*[FadeIn(VGroup(labels[k], vals[k]), shift=0.08 * RIGHT) for k in range(4)], lag_ratio=0.35)], 1.4),
            (lambda: [GrowArrow(barrow)], 0.5),
            "It has a number",
            (lambda: [glow(ino[0], BLUE_M)], 0.8),
        ])

        dirp = panel(DX, DW, "directory")
        e1 = entry("ledger.csv", 0)
        a1 = entry_arrow(0)
        self.steps("A directory is a list of entries, each a name and an inode number. "
                   "Opening ledger.csv means finding its entry, then reading inode 13.", [
            (lambda: [FadeIn(dirp)], 0.6),
            "each a name",
            (lambda: [FadeIn(e1, shift=0.08 * RIGHT)], 0.6),
            (lambda: [GrowArrow(a1)], 0.5),
            "Opening",
            (lambda: [e1.animate.set_color(YELLOW_M)], 0.4),
            (lambda: [flow(a1, YELLOW_M, 0.7)], 0.7),
            (lambda: [flow(barrow, YELLOW_M, 0.5), e1.animate.set_color(WHITE)], 0.5),
        ])

        e2 = entry("ledger-2026.csv", 1, GOLD_M)
        a2 = entry_arrow(1, GOLD_M)
        self.steps("A hard link is a second entry with the same number. "
                   "The inode counts its names, so links is now 2.", [
            (lambda: [FadeIn(e2, shift=0.08 * RIGHT)], 0.7),
            (lambda: [GrowArrow(a2)], 0.6),
            "The inode counts",
            (lambda: [Transform(vals[2], field_val("2", 2, GOLD_M))], 0.7),
            (lambda: [glow(ino[0], GOLD_M)], 0.8),
        ])

        self.steps("Append through either name, and both see it. There is only one size to change.", [
            (lambda: [flow(a2, GOLD_M, 0.7)], 0.7),
            (lambda: [Transform(vals[0], field_val("2 GB + 8 KB", 0, GOLD_M)),
                      cells[NEW_BLOCK2].animate.set_stroke(GOLD_M, 2.5).set_fill(fillc(GOLD_M, 0.4), 1)], 0.7),
            "There is only",
            (lambda: [glow_text(e1, GOLD_M), glow_text(e2, GOLD_M)], 0.9),
        ])

        self.steps("rm doesn't delete the file. It removes one entry and lowers the count to 1. "
                   "The other name still works.", [
            (lambda: [vals[0].animate.set_color(WHITE), vals[2].animate.set_color(WHITE), e2.animate.set_color(WHITE),
                      a2.animate.set_color(GREY_B)], 0.5),
            "It removes",
            (lambda: [e1.animate.set_color(RED_M), a1.animate.set_color(RED_M)], 0.5),
            (lambda: [FadeOut(e1, shift=0.2 * LEFT), FadeOut(a1)], 0.6),
            "and lowers",
            (lambda: [Transform(vals[2], field_val("1", 2, GOLD_M))], 0.7),
            "The other name",
            (lambda: [flow(a2, BLUE_M, 0.7)], 0.7),
        ])

        # ---- an open descriptor --------------------------------------------------------------------------------------
        proc = RoundedRectangle(corner_radius=0.14, width=IW, height=1.0, stroke_color=TEAL_M, stroke_width=3)
        proc.set_fill(fillc(TEAL_M), 1).move_to([IX, PY, 0])
        ptxt = T("audit export, a JVM", 28).move_to([IX, PY, 0])
        farrow = Arrow([IX, PY + 0.58, 0], [IX, RY - BOXH / 2 - 0.08, 0], buff=0, stroke_width=3, color=TEAL_M,
                       max_tip_length_to_length_ratio=0.2)
        flab = M("fd 4", 23, TEAL_M).move_to([IX + 0.6, (PY + 0.5 + RY - BOXH / 2) / 2, 0])
        self.steps("Now the audit export, a JVM, opens ledger-2026.csv. "
                   "Its file descriptor 4 leads straight to inode 13.", [
            (lambda: [vals[2].animate.set_color(WHITE), FadeIn(proc), FadeIn(ptxt)], 0.7),
            "Its file descriptor",
            (lambda: [GrowArrow(farrow), FadeIn(flab)], 0.7),
            "leads straight",
            (lambda: [flow(farrow, TEAL_M, 0.7)], 0.7),
        ])

        self.steps("Delete the last name, and links is 0. "
                   "The kernel still keeps the file, because the JVM has it open.", [
            (lambda: [e2.animate.set_color(RED_M), a2.animate.set_color(RED_M)], 0.5),
            (lambda: [FadeOut(e2, shift=0.2 * LEFT), FadeOut(a2)], 0.6),
            "and links is 0",
            (lambda: [Transform(vals[2], field_val("0", 2, RED_M))], 0.7),
            "The kernel still",
            (lambda: [glow(ino[0], TEAL_M)], 0.8),
            "has it open",
            (lambda: [farrow.animate(rate_func=there_and_back).set_stroke(width=7), glow(proc, TEAL_M)], 0.9),
        ])

        du = left_at(T("du, adding up names:", 25, GREY_B), -6.3, PY + 0.3)
        duv = left_at(M("0", 24, RED_M), -2.75, PY + 0.3)
        df = left_at(T("df, counting blocks:", 25, GREY_B), -6.3, PY - 0.3)
        dfv = left_at(M("2 GB", 24, GOLD_M), -2.75, PY - 0.3)
        self.steps("du adds up the files it can reach by name, and says 0. df counts the blocks in use, "
                   "and still says two gigabytes.", [
            (lambda: [FadeIn(du), FadeIn(duv)], 0.7),
            "df counts",
            (lambda: [FadeIn(df), FadeIn(dfv)], 0.7),
            (lambda: [glow(ino[0], GOLD_M)], 0.8),
        ])

        self.steps("When the JVM closes the file, nothing points at the inode. "
                   "Only then does the kernel free it, and df drops.", [
            (lambda: [FadeOut(farrow), FadeOut(flab), proc.animate.set_stroke(GREY_D).set_fill(BLACK, 1),
                      ptxt.animate.set_color(GREY_D)], 0.8),
            "Only then",
            (lambda: [ino[0].animate.set_stroke(GREY_D).set_fill(BLACK, 1), ino[1].animate.set_color(GREY_D),
                      labels.animate.set_color(GREY_D), *[v.animate.set_color(GREY_D) for v in vals],
                      barrow.animate.set_color(GREY_D),
                      *[cells[i].animate.set_stroke(GREY_D, 2).set_fill(BLACK, 1)
                        for i in FILE_BLOCKS + [NEW_BLOCK, NEW_BLOCK2]]], 1.0),
            "and df drops",
            (lambda: [Transform(dfv, left_at(M("0", 24, GREEN_M), -2.75, PY - 0.3)), duv.animate.set_color(GREEN_M)], 0.7),
        ])

        rule = chip("freed when no name and no open descriptor points at it", GREEN_M, 26).move_to([0, ST_Y, 0])
        self.steps("A name only points at an inode. The kernel frees a file when no name "
                   "and no open descriptor points at it.", [
            (lambda: [glow(dirp[0], WHITE)], 0.9),
            "The kernel frees",
            (lambda: [FadeIn(rule, shift=0.15 * UP)], 0.8),
        ])
        self.wait(0.6)


def glow_text(m, color=YELLOW_M):
    return m.animate(rate_func=there_and_back).set_color(color).scale(1.08)
