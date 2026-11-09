from sfz import *

SAY.insert(0, (r"\bT1's\b", "T one's"))
# "wallet A" mid-sentence comes out as "wallet uh".
SAY.insert(0, (r"\bwallet A\b", "wallet eh"))
SAY.insert(0, (r"\bT1\b", "T one"))

PX = {0: -4.05, 132: -1.25}          # page columns
MEM_Y, DISK_Y = 1.75, -1.55        # page centres in memory and on disk
DIV_Y = 0.2                        # memory above, disk below
PW, PH = 2.4, 1.2
LOG_X, LOG_W = 3.8, 5.2            # the log column
ROW_Y = [2.25, 1.6, 0.95, 0.3]
ROW_H = 0.5
LC1, LC2 = -2.7, -3.15             # caption rows under the pages
RC_X = 1.3                         # left edge of status lines under the log
RC_Y = [-0.55, -1.15]


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


def fillc(color):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def page(num, y, val, color=WHITE):
    x = PX[num]
    r = RoundedRectangle(corner_radius=0.12, width=PW, height=PH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    h = T(f"page {num}", 22, GREY_B).move_to([x, y + 0.3, 0])
    b = M(val, 24, GOLD_M if ManimColor(color).to_hex().upper() == GOLD_M.upper() else WHITE).move_to([x, y - 0.18, 0])
    return VGroup(r, h, b)


def body(num, y, val, color=WHITE):
    return M(val, 24, color).move_to([PX[num], y - 0.18, 0])


def half(num, y, side, color, label):
    x = PX[num] + (-0.53 if side == "l" else 0.53)
    r = Rectangle(width=1.0, height=0.46, stroke_width=0).set_fill(color, 0.3).move_to([x, y - 0.18, 0])
    return VGroup(r, T(label, 18, color).move_to([x, y - 0.18, 0]))


def row(i, text, color=WHITE, dashed=False):
    y = ROW_Y[i]
    bg = RoundedRectangle(corner_radius=0.08, width=LOG_W, height=ROW_H, stroke_width=0).set_fill(fillc(color), 1).move_to([LOG_X, y, 0])
    ol = RoundedRectangle(corner_radius=0.08, width=LOG_W, height=ROW_H, stroke_color=color, stroke_width=2.5).move_to([LOG_X, y, 0])
    if dashed:
        ol = DashedVMobject(ol, num_dashes=60, dashed_ratio=0.55)
    t = M(text, 18, color)
    t.move_to([LOG_X - LOG_W / 2 + 0.2 + t.width / 2, y, 0])
    return VGroup(bg, ol, t)


def solid(i, color=WHITE):
    return RoundedRectangle(corner_radius=0.08, width=LOG_W, height=ROW_H, stroke_color=color, stroke_width=2.5).move_to([LOG_X, ROW_Y[i], 0])


def fpi(i):
    """A small page icon inside a log row: this record carries a full-page image."""
    x, y = LOG_X + LOG_W / 2 - 0.75, ROW_Y[i]
    r = RoundedRectangle(corner_radius=0.05, width=1.2, height=0.34, stroke_color=TEAL_M, stroke_width=2).set_fill(fillc(TEAL_M), 1)
    r.move_to([x, y, 0])
    return VGroup(r, M("full page", 14, TEAL_M).move_to([x, y, 0]))


def lcap(s, y, color=GREY_B, size=22):
    return T(s, size, color).move_to([PX[0] / 2 + PX[132] / 2, y, 0])


def rcap(s, i, color=GREY_B, size=22):
    t = T(s, size, color)
    return t.move_to([RC_X + t.width / 2, RC_Y[i], 0])


def side(name, y, note=None, ncolor=GREY_B):
    """A label left of the pages: which store this row is, and a note under it."""
    x = -6.0
    g = VGroup(T(name, 22, GREY_B).move_to([x, y + (0.15 if note else 0), 0]))
    g.add(T(note or ".", 18, ncolor).move_to([x, y - 0.17, 0]).set_opacity(1 if note else 0))
    return g


def wr(num):
    """Arrow for a page write, memory copy to disk copy."""
    x = PX[num]
    return Arrow([x, MEM_Y - PH / 2 - 0.08, 0], [x, DISK_Y + PH / 2 + 0.08, 0], buff=0, stroke_width=3, color=GOLD_M,
                 max_tip_length_to_length_ratio=0.12)


def marker(i):
    y = ROW_Y[i]
    return Triangle(color=YELLOW_M, fill_opacity=1, stroke_width=0).scale(0.13).rotate(-PI / 2).move_to([LOG_X - LOG_W / 2 - 0.28, y, 0])


class WalRecovery(Base):
    """store-06, section 2 (with the setup from section 0 and the torn page of section 3): a 25-euro transfer changes page
    0 and page 132; COMMIT forces the log, not the pages; the power fails while page 132 is half written; recovery
    replays the log from the last checkpoint, and page 132 comes back from its full-page image."""

    def construct(self):
        self.title_card("Write-ahead logging", "commit, crash, recover")

        div = DashedLine([-6.6, DIV_Y, 0], [0.4, DIV_Y, 0], dash_length=0.08, stroke_width=1.5, color=GREY_D)
        mem_l = side("memory", MEM_Y)
        disk_l = side("disk", DISK_Y, "data file")
        d0, d1 = page(0, DISK_Y, "A = 500"), page(132, DISK_Y, "B = 1,000")
        m0, m1 = page(0, MEM_Y, "A = 500"), page(132, MEM_Y, "B = 1,000")
        self.steps("A transfer moves 25 euros from wallet A on page 0 to wallet B on page 132. "
                   "The database changes these pages in memory, which is lost in a crash.", [
            (lambda: [FadeIn(disk_l), FadeIn(d0, shift=0.1 * UP), FadeIn(d1, shift=0.1 * UP)], 1.0),
            "The database changes",
            (lambda: [Create(div), FadeIn(mem_l), FadeIn(m0, shift=0.5 * UP), FadeIn(m1, shift=0.5 * UP)], 1.1),
        ])

        w0, w1 = wr(0), wr(132)
        c1 = lcap("2 page writes and a force: about 4 ms", LC1)
        self.steps("Both changes must survive a crash, together. Saving both pages at commit means two 8 kilobyte "
                   "writes in two places, and a force: about 4 milliseconds.", [
            (lambda: [Transform(m0, page(0, MEM_Y, "A = 475", GOLD_M)), Transform(m1, page(132, MEM_Y, "B = 1,025", GOLD_M))], 0.9),
            "Saving both",
            (lambda: [GrowArrow(w0), GrowArrow(w1)], 0.7),
            (lambda: [travel(w0, GOLD_M, 0.7)], 0.7),
            (lambda: [Transform(d0[2], body(0, DISK_Y, "A = 475", GOLD_M))], 0.5),
            "and a force",
            (lambda: [FadeIn(c1, shift=0.1 * UP)], 0.6),
        ])

        x1 = tick(False, 0.2).move_to(w1.get_center())
        c2 = lcap("power fails: the debit is on disk, the credit is lost", LC2, RED_M)
        self.steps("And if the power fails between them, the disk holds the debit without the credit.", [
            (lambda: [Create(x1), FadeIn(c2, shift=0.1 * UP)], 0.8),
            "the debit",
            (lambda: [glow(d0[0], RED_M)], 0.8),
            "without the credit",
            (lambda: [glow(d1[0], RED_M)], 0.8),
        ])

        hd = T("log file", 26, WHITE).move_to([LOG_X, 3.08, 0])
        r0 = row(0, "earlier records", GREY_C)
        r1 = row(1, "T1 page 0: A = 475", WHITE, dashed=True)
        sub = T("dashed: not on disk yet", 18, GREY_B).move_to([LOG_X, 2.75, 0])
        self.steps("So the database keeps a log, a file it only appends to. Before changing a page, "
                   "it appends a record of the change.", [
            (lambda: [FadeOut(VGroup(w0, w1, x1, c1, c2)), Transform(d0[2], body(0, DISK_Y, "A = 500")),
                      Transform(m0, page(0, MEM_Y, "A = 500")), Transform(m1, page(132, MEM_Y, "B = 1,000"))], 0.8),
            (lambda: [FadeIn(hd), FadeIn(r0)], 0.8),
            "Before changing",
            (lambda: [FadeIn(r1, shift=0.1 * DOWN), FadeIn(sub)], 0.8),
            (lambda: [Transform(m0, page(0, MEM_Y, "A = 475", GOLD_M))], 0.7),
        ])

        r2 = row(2, "T1 page 132: B = 1,025", WHITE, dashed=True)
        dl0 = T("page 0: dirty", 22, GOLD_M).move_to(m0[1].get_center())
        dl1 = T("page 132: dirty", 22, GOLD_M).move_to(m1[1].get_center())
        self.steps("Both pages change only in memory. They're dirty: newer than the disk.", [
            (lambda: [FadeIn(r2, shift=0.1 * DOWN)], 0.7),
            (lambda: [Transform(m1, page(132, MEM_Y, "B = 1,025", GOLD_M))], 0.7),
            "They're dirty",
            (lambda: [Transform(m0[1], dl0), Transform(m1[1], dl1)], 0.7),
        ])

        r3 = row(3, "T1 commit", GREEN_M, dashed=True)
        s1 = rcap("1 sequential write, 1 fsync", 0)
        ok = rcap("client: OK", 1, GREEN_M)
        self.steps("At commit, it appends a commit record and forces the log to disk: one sequential write and one fsync. "
                   "Then the client hears OK.", [
            (lambda: [FadeIn(r3, shift=0.1 * DOWN)], 0.7),
            "forces the log",
            (lambda: [FadeOut(sub), *[ReplacementTransform(r[1], solid(i, c)) for i, r, c in
                                      [(1, r1, WHITE), (2, r2, WHITE), (3, r3, GREEN_M)]]], 0.9),
            "one sequential",
            (lambda: [FadeIn(s1, shift=0.1 * UP)], 0.6),
            "Then the client",
            (lambda: [FadeIn(ok, shift=0.1 * UP)], 0.6),
        ])

        c3 = lcap("pages: written later, in the background", LC1)
        self.steps("The dirty pages go to the data file later, in the background.", [
            (lambda: [FadeOut(s1), FadeOut(ok)], 0.5),
            (lambda: [FadeIn(c3, shift=0.1 * UP)], 0.7),
        ])

        w1 = wr(132)
        new_h = half(132, DISK_Y, "l", GOLD_M, "new")
        old_h = half(132, DISK_Y, "r", GREY_B, "old")
        pf = lcap("power fails", LC2, RED_M, 26)
        mem_l2 = side("memory", MEM_Y, "wiped", RED_M)
        self.steps("The writer starts on page 132, and halfway through, the power fails.", [
            (lambda: [GrowArrow(w1)], 0.6),
            (lambda: [travel(w1, GOLD_M, 0.6)], 0.6),
            (lambda: [FadeOut(d1[2]), FadeIn(old_h), FadeIn(new_h, shift=0.2 * RIGHT)], 0.8),
            "the power fails",
            (lambda: [FadeIn(pf), Transform(mem_l, mem_l2), FadeOut(VGroup(m0, m1, w1))], 0.9),
        ])

        torn_l = T("page 132: torn", 22, RED_M).move_to(d1[1].get_center())
        c4 = lcap("a drive writes 4 KB at a time; a page is 8 KB", LC1)
        self.steps("Memory is gone. Page 0 on disk has the old balance. Page 132 is torn: "
                   "a drive writes 4 kilobytes at a time, and a page is 8.", [
            "Page 0 on disk",
            (lambda: [glow(d0[0], RED_M)], 0.8),
            "Page 132 is torn",
            (lambda: [d1[0].animate.set_stroke(RED_M), Transform(d1[1], torn_l)], 0.8),
            "a drive writes",
            (lambda: [FadeOut(c3), FadeIn(c4, shift=0.1 * UP)], 0.7),
        ])

        r0b = row(0, "checkpoint: redo point", BLUE_M)
        mk = marker(0)
        c5 = rcap("redo starts here", 0, BLUE_M)
        self.steps("Recovery redoes changes from the last checkpoint on. The checkpoint wrote every dirty page to disk, "
                   "so nothing older needs replaying.", [
            (lambda: [FadeOut(pf), Transform(mem_l, side("memory", MEM_Y, "recovery", BLUE_M)),
                      Transform(r0, r0b)], 0.9),
            (lambda: [FadeIn(mk, shift=0.2 * RIGHT), FadeIn(c5)], 0.6),
            "so nothing older",
            (lambda: [glow(r0[0], BLUE_M)], 0.8),
        ])

        m0r = page(0, MEM_Y, "A = 500")
        self.steps("It replays each record onto its page. Page 0 gets its debit back.", [
            (lambda: [mk.animate.move_to(marker(1))], 0.6),
            (lambda: [FadeIn(m0r, shift=0.5 * UP)], 0.7),
            "Page 0 gets",
            (lambda: [Transform(m0r, page(0, MEM_Y, "A = 475", GOLD_M))], 0.8),
        ])

        x2 = tick(False, 0.2).move_to([PX[132] + PW / 2 + 0.3, DISK_Y + 0.25, 0])
        self.steps("But a small record assumes an intact page. On torn page 132, it would write garbage.", [
            (lambda: [mk.animate.move_to(marker(2))], 0.6),
            "On torn",
            (lambda: [glow(d1[0], RED_M), Create(x2)], 0.9),
        ])

        f1, f2 = fpi(1), fpi(2)
        m1r = page(132, MEM_Y, "B = 1,025", GOLD_M)
        ghost = fpi(2)
        self.steps("So the first change to a page after a checkpoint logs a full copy of it, a full-page image. "
                   "Recovery restores page 132 from that copy.", [
            0.6,
            (lambda: [FadeIn(f1, scale=0.8), FadeIn(f2, scale=0.8)], 0.8),
            "a full-page image",
            (lambda: [Indicate(f2[1], color=TEAL_M)], 0.7),
            "Recovery restores",
            (lambda: [FadeOut(x2), ghost.animate.move_to([PX[132], MEM_Y, 0]).scale(1.3)], 0.9),
            (lambda: [FadeOut(ghost), FadeIn(m1r)], 0.6),
        ])

        ok2 = tick(True, 0.2).move_to([LOG_X + LOG_W / 2 - 0.35, ROW_Y[3], 0])
        c6 = rcap("T1 is back: debit and credit", 1, GREEN_M)
        self.steps("T1's commit record is there, so both changes are back, together.", [
            (lambda: [mk.animate.move_to(marker(3))], 0.6),
            (lambda: [Create(ok2)], 0.5),
            "both changes",
            (lambda: [glow(m0r[0], GREEN_M), glow(m1r[0], GREEN_M), FadeIn(c6)], 0.9),
        ])

        self.steps("A commit forces only the log. The data file can lag, or even tear, because the log can rebuild it.", [
            (lambda: [*[glow(r[0], YELLOW_M, 1.02) for r in (r1, r2, r3)]], 1.0),
            "The data file",
            (lambda: [glow(d0[0], GOLD_M), glow(d1[0], RED_M)], 1.0),
            "because the log",
            (lambda: [Indicate(hd, color=YELLOW_M)], 0.9),
        ])
        self.wait(0.6)
