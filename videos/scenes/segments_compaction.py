from sfz import *

SAY.insert(0, (r"\bGiB\b", "gibibyte"))
SAY.insert(0, (r"\bMiB\b", "mebibyte"))
SAY.insert(0, (r"\bsegment\.bytes\b", "segment dot bytes"))
SAY.insert(0, (r"\bsegment\.ms\b", "segment dot M S"))
SAY.insert(0, (r"(?<![\w])\.log\b", "dot log"))
SAY.insert(0, (r"(?<![\w])\.index\b", "dot index"))
SAY.insert(0, (r"\b4,096\b", "four thousand and ninety-six"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ROW_Y, SEG_H = 1.3, 1.65
SEG_W, SEG_GAP = 2.9, 0.25
SEG_X0 = [-6.2 + (SEG_W + SEG_GAP) * k for k in range(4)]       # left edge of segment k
SEG_CX = [x + SEG_W / 2 for x in SEG_X0]
BASES = [0, 104, 208, 312]
LASTS = [103, 207, 311, 399]
LX0, RX1 = SEG_X0[0], SEG_X0[3] + SEG_W
STRIP_Y, STRIP_X0, STRIP_X1 = -0.95, -5.6, 5.6
TOP_Y, CAP_Y, BAR_Y = 3.1, -3.25, -2.7
SEGC = BLUE_M


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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def seg_box(k, color=SEGC):
    r = RoundedRectangle(corner_radius=0.12, width=SEG_W, height=SEG_H, stroke_color=color, stroke_width=3)
    return r.set_fill(fillc(color), 1).move_to([SEG_CX[k], ROW_Y, 0])


def fill_bar(k, frac, color=SEGC):
    """How full segment k is: a soft band along its bottom."""
    w = (SEG_W - 0.2) * frac
    return Rectangle(width=w, height=0.12, stroke_width=0).set_fill(color, 0.75).move_to(
        [SEG_X0[k] + 0.1 + w / 2, ROW_Y - SEG_H / 2 + 0.16, 0])


def nb_label(k):
    return T(f"notebook {k + 1}", 26).move_to([SEG_CX[k], ROW_Y + 0.15, 0])


def file_label(k):
    name = M(f"{BASES[k]:020d}.log", 13)
    rng = T(f"{BASES[k]} to {LASTS[k]}", 26)
    st = T("active: 88 so far" if k == 3 else "closed: 104 records", 18, GOLD_M if k == 3 else GREY_B)
    return VGroup(name, rng, st).arrange(DOWN, buff=0.08).move_to([SEG_CX[k], ROW_Y + 0.12, 0])


class SegmentsCompaction(Base):
    """msg-03, section 1. The café's notebooks: shelve a full one, throw out whole old ones. A log only grows: 3,000
    payments a second at 1 KB is 3 MB a second, 260 GB a day, 1.8 TB a week. One big file can't be cut at its start:
    dropping 260 GB means copying 1.5 TB. So a partition is a chain of segment files; only the active one grows,
    rolling closes it, deleting old data deletes files. The lab's segments 0, 104, 208, 312 (base offsets); offset 230
    is in 208. Inside a 1 GiB file, a sparse .index (an entry about every 4,096 bytes) finds the place. segment.bytes
    and segment.ms; whole files only, so old records can outlive their limit. A check: offset 103."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
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
        return [FadeOut(self.lab.pop(k)) for k in keys if k in self.lab]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def head(self, s, color=GREY_B):
        return self.put("head", left_at(T(s, 22, color), LX0, ROW_Y + SEG_H / 2 + 0.35))

    def query(self, s):
        return self.put("q", chip(s, YELLOW_M, 24).move_to([0, TOP_Y, 0]))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("How does a log forget?", "a chain of files called segments")

        # ---------------- scene 1: the café's notebooks, and the question ----------------
        segs = [seg_box(k, GOLD_M) for k in range(4)]
        nbl = [nb_label(k) for k in range(4)]
        fills = [fill_bar(k, 1.0, GOLD_M) for k in range(3)] + [fill_bar(3, 0.4, GOLD_M)]
        self.steps("Picture a café that writes every order in a notebook. When a notebook fills, the owner shelves it and starts a new one.", [
            (lambda: [FadeIn(segs[0]), FadeIn(nbl[0]), GrowFromEdge(fills[0], LEFT)], 1.0),
            "When a notebook fills",
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(segs[k], shift=0.2 * RIGHT), FadeIn(nbl[k], shift=0.2 * RIGHT),
                                                   GrowFromEdge(fills[k], LEFT)) for k in (1, 2, 3)], lag_ratio=0.5)], 2.0),
        ])
        self.steps("Each Monday, she throws out every notebook whose last order is over a week old.", [
            "throws out",
            (lambda: [glow(segs[0], RED_M, 1.04), *self.cap("each Monday: out with every notebook whose last order is over a week old")], 0.9),
        ])
        big = RoundedRectangle(corner_radius=0.12, width=RX1 - LX0, height=SEG_H, stroke_color=SEGC, stroke_width=3)
        big.set_fill(fillc(SEGC), 1).move_to([(LX0 + RX1) / 2, ROW_Y, 0])
        self.steps("Kafka, the program that keeps logs of records for other programs to read, has the owner's problem. A log only grows.", [
            (lambda: [*self.uncap(), *[FadeOut(m) for m in segs + nbl + fills]], 0.7),
            (lambda: [FadeIn(big), *self.head("one partition of a log: one file")], 0.8),
            "A log only grows",
            (lambda: [glow(big, TEAL_M, 1.02)], 0.9),
        ])
        self.steps("At 3,000 payments a second, about 1 KB each, that's 3 MB a second. About 260 GB a day, and 1.8 TB a week. "
                   "How do you delete the front of something that only grows?", [
            (lambda: self.cap("3,000 payments a second x 1 KB = 3 MB a second"), 0.5),
            "About 260",
            (lambda: [*self.cap("about 260 GB a day; about 1.8 TB a week"),
                      *self.put("size", T("1.8 TB", 30).move_to(big))], 0.7),
            "How do you delete",
            (lambda: self.cap("how do you delete the front?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 2: one big file, broken ----------------
        fw = (RX1 - LX0) * 260 / 1800
        front = Rectangle(width=fw, height=SEG_H - 0.1, stroke_width=0).set_fill(RED_M, 0.35).move_to([LX0 + fw / 2, ROW_Y, 0])
        front_l = T("oldest 260 GB", 18, RED_M).move_to([LX0 + fw / 2, ROW_Y - SEG_H / 2 - 0.3, 0])
        self.steps("The simplest idea: keep the log in one big file, and cut the oldest part off the front.", [
            (lambda: [*self.cap("the simplest idea: one big file, cut off the front", PURPLE_M)], 0.5),
            "cut the oldest",
            (lambda: [FadeIn(front), FadeIn(front_l)], 0.7),
        ])
        endcut = DashedLine([RX1 - 0.5, ROW_Y + 1.0, 0], [RX1 - 0.5, ROW_Y - 1.0, 0], dash_length=0.08, stroke_width=3, color=GREEN_M)
        startcut = DashedLine([LX0 + fw, ROW_Y + 1.0, 0], [LX0 + fw, ROW_Y - 1.0, 0], dash_length=0.08, stroke_width=3, color=RED_M)
        self.steps("Here's the catch. A file system, the part of the computer that keeps files on disk, can cut a file short at its end "
                   "for almost nothing. It can't cut at the start.", [
            "can cut a file short",
            (lambda: [Create(endcut), *self.cap("cut at the end: almost free", GREEN_M)], 0.6),
            "It can't",
            (lambda: [Create(startcut), *self.cap("cut at the start: not possible", RED_M)], 0.6),
        ])
        copy = Rectangle(width=RX1 - LX0 - fw, height=0.7, stroke_color=YELLOW_M, stroke_width=2.5).set_fill(fillc(YELLOW_M), 1)
        copy.move_to([(LX0 + fw + RX1) / 2, -0.6, 0])
        copy_l = T("a new file: copy the other 1.5 TB", 20, YELLOW_M).move_to(copy)
        self.steps("So to drop the oldest 260 GB from a 1.8 TB file, you'd copy the other 1.5 TB into a new file. Every day.", [
            "you'd copy",
            (lambda: [GrowFromEdge(copy, LEFT), FadeIn(copy_l)], 1.6),
            "Every day",
            (lambda: [*self.cap("every day", RED_M, 30), glow(copy, RED_M, 1.02)], 0.7),
        ])
        self.steps("That's tearing out page one of a notebook by copying every other page into a new notebook. By hand. Every morning. "
                   "So deleting has to mean throwing away whole files.", [
            "So deleting",
            (lambda: self.cap("deleting must mean throwing away whole files", YELLOW_M), 0.6),
        ])

        # ---------------- scene 3: the café's answer, mapped ----------------
        segs = [seg_box(k) for k in range(4)]
        fills = [fill_bar(k, 1.0) for k in range(3)] + [fill_bar(3, 88 / 104, GOLD_M)]
        self.steps("The café already solved this: many notebooks, not one. Only the newest takes new orders. "
                   "When it's full, it goes on the shelf, and nobody writes in it again.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(front, front_l, endcut, startcut, copy, copy_l)), *self.drop("size")], 0.6),
            (lambda: [ReplacementTransform(big, VGroup(*segs)), *self.head("one partition: a chain of files")], 1.0),
            "Only the newest",
            (lambda: [segs[3].animate.set_stroke(GOLD_M), GrowFromEdge(fills[3], LEFT)], 0.7),
            "When it's full",
            (lambda: [LaggedStart(*[GrowFromEdge(f, LEFT) for f in fills[:3]], lag_ratio=0.3)], 1.0),
        ])
        bin_x = tick(False, 0.2).move_to([SEG_CX[0], ROW_Y, 0])
        self.steps("And throwing out the oldest costs one trip to the bin, however thick the notebook is.", [
            "one trip",
            (lambda: [VGroup(segs[0], fills[0]).animate.set_opacity(0.15), Create(bin_x)], 0.8),
            1.0,
            (lambda: [VGroup(segs[0], fills[0]).animate.set_opacity(1), FadeOut(bin_x)], 0.5),
        ])
        fl = [file_label(k) for k in range(4)]
        self.steps("Kafka does the same. Each notebook is a file called a segment. The one taking new records is the active segment.", [
            "Each notebook",
            (lambda: [LaggedStart(*[FadeIn(f[0]) for f in fl], lag_ratio=0.15), *self.cap("notebook = segment, one file", SEGC)], 1.0),
            "the active segment",
            (lambda: [FadeIn(fl[3][2]), *self.cap("the newest: the active segment", GOLD_M), glow(segs[3], GOLD_M, 1.04)], 0.8),
        ])
        self.steps("Closing a full one and opening a new one is called rolling. A closed segment never changes. "
                   "And deleting old data means deleting old files, which costs almost nothing.", [
            "called rolling",
            (lambda: [*self.cap("full: close it, open a new one. That's rolling."), LaggedStart(*[FadeIn(f[2]) for f in fl[:3]], lag_ratio=0.2)], 0.9),
            "never changes",
            (lambda: [LaggedStart(*[glow(s, GREY_A, 1.03) for s in segs[:3]], lag_ratio=0.2)], 1.0),
            "deleting old data",
            (lambda: self.cap("deleting old data: deleting old files", GREEN_M), 0.6),
        ])

        # ---------------- scene 4: the lab's segments ----------------
        self.steps("Here's a small log from the lesson's lab: 400 records of 10 KB each, in segments of 1 MiB, a little more than a megabyte. "
                   "About 104 records fit in each.", [
            (lambda: self.cap("the lab: 400 records of 10 KB, segments of 1 MiB"), 0.6),
            "About 104",
            (lambda: [*self.cap("104 records fit in each"), LaggedStart(*[Indicate(f[2], color=WHITE) for f in fl[:3]], lag_ratio=0.2)], 1.0),
        ])
        self.steps("Each segment is named after the offset of its first record, its base offset, padded with zeros to 20 digits. "
                   "So: 0, 104, 208, and the active one, 312, holding the last 88.", [
            "Each segment is named",
            (lambda: [*self.cap("base offset: the first record's offset, in the file's name", YELLOW_M),
                      LaggedStart(*[Indicate(f[0], color=YELLOW_M, scale_factor=1.1) for f in fl], lag_ratio=0.2)], 1.2),
            "So: 0",
            (lambda: [LaggedStart(*[FadeIn(f[1], shift=0.1 * UP) for f in fl], lag_ratio=0.35)], 1.6),
            "holding the last",
            (lambda: [glow(segs[3], GOLD_M, 1.04)], 0.7),
        ])

        # ---------------- scene 5: predict which file ----------------
        self.steps("Now a reader asks for offset 230. Which file does the broker open? Pause and guess.", [
            (lambda: [*self.uncap(), *self.query("read offset 230")], 0.6),
            "Pause and guess",
            (lambda: self.cap("which file?", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        marks = [tick(True, 0.14).move_to([SEG_X0[k] + SEG_W - 0.22, ROW_Y + SEG_H / 2 - 0.2, 0]) for k in range(3)]
        no = tick(False, 0.13).move_to([SEG_X0[3] + SEG_W - 0.22, ROW_Y + SEG_H / 2 - 0.2, 0])
        pick = Arrow([0, TOP_Y - 0.35, 0], [SEG_CX[2], ROW_Y + SEG_H / 2 + 0.05, 0], buff=0.05, stroke_width=3, color=YELLOW_M,
                     max_tip_length_to_length_ratio=0.12)
        self.steps("208. The broker keeps its files sorted by base offset, and picks the largest one at or below 230. "
                   "312 is too high. 208 is the one.", [
            (lambda: [*self.uncap(), Indicate(fl[2][1], color=YELLOW_M, scale_factor=1.2)], 0.6),
            "picks the largest",
            (lambda: [LaggedStart(*[Create(m) for m in marks], lag_ratio=0.3), *self.cap("the largest base offset at or below 230")], 1.0),
            "312 is too high",
            (lambda: [Create(no)], 0.5),
            "208 is the one",
            (lambda: [GrowArrow(pick), glow(segs[2], YELLOW_M, 1.04), FadeOut(VGroup(*marks)), FadeOut(no)], 0.8),
        ])

        # ---------------- scene 6: inside the file ----------------
        strip = Rectangle(width=STRIP_X1 - STRIP_X0, height=0.7, stroke_color=SEGC, stroke_width=2.5).set_fill(fillc(SEGC), 1)
        strip.move_to([(STRIP_X0 + STRIP_X1) / 2, STRIP_Y, 0])
        zl = VGroup(DashedLine(segs[2].get_corner(DL), [STRIP_X0, STRIP_Y + 0.35, 0], dash_length=0.08, stroke_width=1.5, color=GREY_C),
                    DashedLine(segs[2].get_corner(DR), [STRIP_X1, STRIP_Y + 0.35, 0], dash_length=0.08, stroke_width=1.5, color=GREY_C))
        strip_l = M("00000000000000000208.log", 16, GREY_A).move_to(strip.get_center() + [2.3, 0, 0])
        self.steps("But a segment can be 1 GiB. Reading it from the start, at 2 GB a second, takes half a second for one lookup.", [
            (lambda: [Create(zl), FadeIn(strip), FadeIn(strip_l)], 0.9),
            "Reading it from the start",
            (lambda: [*self.cap("from the start: 1 GiB at 2 GB a second, half a second", RED_M)], 0.5),
            (lambda: [Succession(FadeIn(sweep := Line([STRIP_X0, STRIP_Y + 0.42, 0], [STRIP_X0, STRIP_Y - 0.42, 0], stroke_width=5, color=RED_M), run_time=0.1),
                                 sweep.animate(run_time=2.4, rate_func=linear).move_to([STRIP_X1, STRIP_Y, 0]),
                                 FadeOut(sweep, run_time=0.2))], 2.7),
        ])
        ticks = VGroup(*[Line([x, STRIP_Y + 0.35, 0], [x, STRIP_Y + 0.6, 0], stroke_width=3, color=TEAL_M)
                         for x in np.linspace(STRIP_X0 + 0.35, STRIP_X1 - 0.35, 16)])
        idx_l = T(".index: an entry about every 4,096 bytes", 20, TEAL_M).move_to([0, STRIP_Y - 0.65, 0])
        self.steps("So next to each .log file sits a .index file. It maps offsets to byte positions in the file, "
                   "like the index at the back of a book.", [
            (lambda: [*self.uncap(), LaggedStart(*[Create(t) for t in ticks], lag_ratio=0.08)], 1.4),
            "like the index",
            (lambda: [*self.cap("offset to byte position, like the index at the back of a book", TEAL_M)], 0.6),
        ])
        self.steps("It's sparse: an entry about every 4,096 bytes, not one per record, so it's small enough to keep in memory.", [
            (lambda: [FadeIn(idx_l, shift=0.1 * UP), *self.cap("sparse: small enough to keep in memory", TEAL_M)], 0.7),
        ])
        k_near = 4
        tx = ticks[k_near].get_start()[0]
        hop = Arrow([tx - 1.0, STRIP_Y + 0.95, 0], [tx, STRIP_Y + 0.62, 0], buff=0, stroke_width=4, color=YELLOW_M, max_tip_length_to_length_ratio=0.3)
        tgt_x = tx + 0.42
        scan = Line([tx, STRIP_Y, 0], [tgt_x, STRIP_Y, 0], stroke_width=8, color=YELLOW_M)
        t230 = VGroup(Line([tgt_x, STRIP_Y + 0.35, 0], [tgt_x, STRIP_Y - 0.35, 0], stroke_width=3, color=YELLOW_M),
                      T("230", 22, YELLOW_M).move_to([tgt_x + 0.38, STRIP_Y, 0]))
        self.steps("The broker looks up 230 in the index, jumps to the nearest entry at or below it, and reads forward a few kilobytes. "
                   "A third file, the time index, does the same for times.", [
            "jumps to",
            (lambda: [GrowArrow(hop), *self.cap("jump to the nearest entry at or below 230", YELLOW_M)], 0.7),
            "and reads forward",
            (lambda: [Create(scan), *self.cap("read forward a few kilobytes", YELLOW_M)], 0.8),
            (lambda: [FadeIn(t230)], 0.4),
            "A third file",
            (lambda: self.cap(".timeindex: the same, for times"), 0.5),
        ])

        # ---------------- scene 7: when it rolls, and the catch ----------------
        zoom = VGroup(zl, strip, strip_l, ticks, idx_l, hop, scan, t230)
        sb = chip("segment.bytes: 1 GiB (default)", SEGC, 22, mono=False).move_to([-3.2, -0.9, 0])
        sm = chip("segment.ms: 7 days (default)", SEGC, 22, mono=False).move_to([3.2, -0.9, 0])
        self.steps("Two settings decide when the active segment rolls. segment.bytes, 1 GiB by default: roll before the file grows past it.", [
            (lambda: [FadeOut(zoom), FadeOut(pick), *self.drop("q"), *self.uncap()], 0.6),
            (lambda: [glow(segs[3], GOLD_M, 1.04)], 0.7),
            "segment.bytes",
            (lambda: [FadeIn(sb, shift=0.1 * UP), *self.cap("roll before the file would grow past 1 GiB")], 0.6),
        ])
        self.steps("segment.ms, 7 days: roll if the segment is older than that when a new record arrives.", [
            (lambda: [FadeIn(sm, shift=0.1 * UP), *self.cap("or: older than 7 days when a new record arrives")], 0.6),
        ])
        self.steps("And the catch. Deleting means whole files only. Remember the owner who keeps orders for a week? "
                   "A notebook that also holds last Thursday's orders stays on the shelf.", [
            (lambda: [FadeOut(sb), FadeOut(sm), *self.cap("deleting: whole files only", RED_M)], 0.6),
            "Remember the owner",
            (lambda: [*self.head("the café's notebooks", GOLD_M), *[s.animate.set_stroke(GOLD_M) for s in segs]], 0.7),
            "A notebook that also",
            (lambda: [glow(segs[0], GOLD_M, 1.04), *self.cap("one old order and last Thursday's: the notebook stays")], 0.8),
        ])
        self.steps("So an inspector can find a twelve-day-old order there, and the rule wasn't broken. "
                   "Kafka keeps records the same way: often longer than you asked. The next section shows it.", [
            "twelve-day-old",
            (lambda: [*self.cap("a twelve-day-old order, rule not broken", GOLD_M)], 0.6),
            "Kafka keeps",
            (lambda: [*self.head("one partition: a chain of files"), *[s.animate.set_stroke(SEGC) for s in segs[:3]],
                      segs[3].animate.set_stroke(GOLD_M), *self.cap("records live at least as long as you asked, often longer")], 0.8),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So: one log, cut into files. New records go only into the active one, closed ones never change, "
                   "and deleting old data means throwing away whole files.", [
            (lambda: self.cap("one log, cut into files", YELLOW_M, 28), 0.5),
            "New records",
            (lambda: [glow(segs[3], GOLD_M, 1.04)], 0.7),
            "closed ones",
            (lambda: [LaggedStart(*[glow(s, GREY_A, 1.03) for s in segs[:3]], lag_ratio=0.2)], 0.9),
            "and deleting",
            (lambda: self.cap("delete old data by throwing away whole files", YELLOW_M, 28), 0.5),
        ])
        self.steps("The file names find the right file, and a small index finds the place inside it.", [
            (lambda: [LaggedStart(*[Indicate(f[0], color=YELLOW_M, scale_factor=1.1) for f in fl], lag_ratio=0.15),
                      *self.cap("names find the file; the index finds the place", YELLOW_M, 28)], 1.0),
        ], after=0.5)
        self.steps("One quick check. A reader asks for offset 103. Which file does the broker open? Pause and think.", [
            (lambda: [*self.uncap(), *self.query("read offset 103")], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        pick0 = Arrow([0, TOP_Y - 0.35, 0], [SEG_CX[0], ROW_Y + SEG_H / 2 + 0.05, 0], buff=0.05, stroke_width=3, color=YELLOW_M,
                      max_tip_length_to_length_ratio=0.12)
        self.steps("The one named 0. The next file starts at 104, one record later, so 103 is the last record of the first file.", [
            (lambda: [*self.uncap(), GrowArrow(pick0), glow(segs[0], YELLOW_M, 1.04)], 0.8),
            "The next file",
            (lambda: [Indicate(fl[1][1], color=RED_M, scale_factor=1.2)], 0.8),
            "the last record",
            (lambda: [Indicate(fl[0][1], color=YELLOW_M, scale_factor=1.2),
                      *self.cap("103: the last record of file 0", YELLOW_M, 28)], 0.8),
        ], after=0.3)
        self.wait(2.0)
