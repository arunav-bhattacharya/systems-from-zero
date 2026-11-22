from sfz import *

SAY.insert(0, (r"\bshared_buffers\b", "shared buffers"))
SAY.insert(0, (r"\bmmap\b", "em map"))
SAY.insert(0, (r"\b2 TB\b", "2 terabytes"))
SAY.insert(0, (r"\b8 KB\b", "8 kilobytes"))
SAY.insert(0, (r"\b64 GB\b", "64 gigabytes"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TITLE_Y = 2.9
DX = -5.2                                   # the drive (the shelf)
DTOP, DBOT = 2.4, -1.95
DCOL = [-5.65, -4.75]
DROW = [1.85, 1.2, 0.55, -0.1, -0.75, -1.4]
DPAGES = ["0", "1", "2", "…", "10", "11", "12", "13", "…", "42", "43", "…"]
FX = [-2.55, -0.85, 0.85, 2.55]             # the frames (places on the desk)
FY, FW, FH = 1.32, 1.45, 1.05
DESK = (-3.45, 3.45, 0.62, 2.45)
TB_TOP, TB_BOT = -0.2, -1.75                # the page table
TBX = [-1.7, 1.7]
TBY = [-0.62, -1.32]
RX = 5.05                                   # requests and results
REQ_Y, RES_Y = 1.32, 0.45
BAND = [-2.3, -2.75]
CAP_Y = -3.25


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


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def dtile(i):
    s = DPAGES[i]
    pos = [DCOL[i % 2], DROW[i // 2], 0]
    if s == "…":
        return M("…", 22, GREY_B).move_to(pos)
    r = RoundedRectangle(corner_radius=0.06, width=0.75, height=0.48, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M), 1)
    return VGroup(r, M(s, 20, GOLD_M).move_to(r)).move_to(pos)


def dpos(n):
    return DPAGES.index(str(n))


def ftile(n, k, color=GOLD_M):
    r = RoundedRectangle(corner_radius=0.08, width=1.2, height=0.56, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    return VGroup(r, M(f"page {n}", 18, WHITE).move_to(r)).move_to([FX[k], FY, 0])


def frame_box(k):
    return Rectangle(width=FW, height=FH, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M, 0.06), 1).move_to([FX[k], FY, 0])


def flabel(k, word):
    return M(f"{word} {k}", 18, BLUE_M).move_to([FX[k], FY + FH / 2 + 0.24, 0])


def tentry(n, k, word="place", color=WHITE):
    i = [0, 1, 2, 3][k]
    return M(f"page {n} → {word} {k}", 20, color).move_to([TBX[i % 2], TBY[i // 2], 0])


def req(s, color=YELLOW_M):
    return fit(chip(s, color, 22, mono=True), 2.75).move_to([RX, REQ_Y, 0])


def res(a, b, color):
    lines = [b] if isinstance(b, str) else b
    g = VGroup(T(a, 30, color), *[T(x, 22, GREY_B) for x in lines]).arrange(DOWN, buff=0.1)
    for m in g:
        fit(m, 2.7)
    return g.next_to([RX, REQ_Y - 0.45, 0], DOWN, buff=0.05)


def band(s, k, color=WHITE, size=24):
    return fit(T(s, size, color), 12.6).move_to([0, BAND[k], 0])


class BufferPool(Base):
    """store-03, section 0. Every query reads pages; from an SSD about 100 µs each, from memory well under 1 µs. The study
    desk: four books on the desk, the rest on a shelf. Keeping every page read breaks on size (2 TB vs 64 GB). Four
    frames and a page table: pages 10 to 13 miss and fill the frames, page 11 again is a hit. Page 42 needs a victim
    (page 13, for now). PostgreSQL's shared_buffers (128 MB, 16,384 frames); the Try it's 1,280 reads become 1,280 hits,
    and the reads took 0.15 ms from the kernel's copy. Why the database keeps its own pool (mmap 2 to 20 times slower).
    The moral, and a check: pages 11 and 13."""

    def construct(self):
        self.capm = None
        self.title_card("A desk with four places", "the database's own page cache: the buffer pool")

        # ---------------- scene 1: every query reads pages ----------------
        drive = Rectangle(width=1.95, height=DTOP - DBOT, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.05), 1)
        drive.move_to([DX, (DTOP + DBOT) / 2, 0]).set_z_index(-1)
        t_dr = T("the drive", 24, GOLD_M).move_to([DX, TITLE_Y, 0])
        D = [dtile(i) for i in range(len(DPAGES))]
        n1 = band("one 8 KB page from a fast SSD: about 100 µs", 0, GOLD_M)
        n2 = band("from memory: well under 1 µs", 1, BLUE_M)
        self.steps("Every question a program asks a database reads pages. Looking up one payment reads a few. "
                   "A monthly report reads thousands. Reading one 8 KB page from a fast SSD takes about 100 microseconds. "
                   "From memory, it takes well under one.", [
            (lambda: [FadeIn(drive), FadeIn(t_dr), LaggedStart(*[FadeIn(d) for d in D], lag_ratio=0.05)], 1.2),
            "Looking up one",
            (lambda: [LaggedStart(*[glow(D[i][0], YELLOW_M, 1.08) for i in (4, 5, 6)], lag_ratio=0.2)], 0.8),
            "A monthly report",
            (lambda: [LaggedStart(*[glow(d[0], YELLOW_M, 1.08) for d in D if isinstance(d, VGroup)], lag_ratio=0.05)], 1.0),
            "Reading one 8 KB",
            (lambda: [FadeIn(n1, shift=0.1 * UP)], 0.6),
            "From memory",
            (lambda: [FadeIn(n2, shift=0.1 * UP)], 0.6),
        ])
        self.steps("And queries keep coming back to the same pages: today's payments, the table of card limits. "
                   "So keep copies in memory. But memory is small. Which pages stay, and what happens when it's full?", [
            "And queries keep",
            (lambda: [glow(D[5][0], YELLOW_M, 1.08), glow(D[6][0], YELLOW_M, 1.08)], 0.6),
            (lambda: [glow(D[5][0], YELLOW_M, 1.08), glow(D[6][0], YELLOW_M, 1.08)], 0.6),
            "So keep copies",
            (lambda: [FadeOut(n1), FadeOut(n2), *self.cap("keep copies of busy pages in memory", WHITE)], 0.6),
            "Which pages stay",
            (lambda: self.cap("which pages stay, and what happens when memory is full?", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 2: the desk ----------------
        desk = RoundedRectangle(corner_radius=0.15, width=DESK[1] - DESK[0], height=DESK[3] - DESK[2], stroke_color=BLUE_M, stroke_width=3)
        desk.move_to([(DESK[0] + DESK[1]) / 2, (DESK[2] + DESK[3]) / 2, 0]).set_z_index(-2)
        F = [frame_box(k) for k in range(4)]
        FL = [flabel(k, "place") for k in range(4)]
        t_mem = T("memory: a desk", 24, BLUE_M).move_to([0, TITLE_Y, 0])
        self.steps("Picture yourself studying at a small desk. It holds four open books, and the rest sit on a shelf across the room. "
                   "A glance at the desk takes a second. A walk to the shelf takes a minute.", [
            (lambda: [*self.uncap(), Create(desk), FadeIn(t_mem)], 0.8),
            "It holds four",
            (lambda: [LaggedStart(*[FadeIn(f) for f in F], lag_ratio=0.15), LaggedStart(*[FadeIn(l) for l in FL], lag_ratio=0.15)], 0.9),
            "and the rest",
            (lambda: [glow(drive, GOLD_M, 1.01)], 0.6),
            "A glance",
            (lambda: self.cap("a glance at the desk: a second", BLUE_M), 0.5),
            "A walk to the shelf",
            (lambda: self.cap("a walk to the shelf: a minute", GOLD_M), 0.5),
        ])
        self.steps("So you keep the books you're using on the desk. And when you need a fifth book, one has to go back. "
                   "Which one? Hold that thought.", [
            "And when you need",
            (lambda: [*self.cap("a fifth book: one has to go back. which one?", YELLOW_M),
                      LaggedStart(*[glow(f, YELLOW_M, 1.03) for f in F], lag_ratio=0.15)], 1.0),
        ], after=0.4)
        t_dr2 = T("the drive: the shelf", 24, GOLD_M).move_to([DX + 0.25, TITLE_Y, 0])
        t_mem2 = T("memory: the desk", 24, BLUE_M).move_to([0, TITLE_Y, 0])
        self.steps("Let's map it. The shelf is the drive. The desk is memory. And each book is a page.", [
            "The shelf is",
            (lambda: [swap(t_dr, t_dr2), *self.cap("the shelf: the drive", GOLD_M)], 0.6),
            "The desk is",
            (lambda: [swap(t_mem, t_mem2), *self.cap("the desk: memory", BLUE_M)], 0.6),
            "And each book",
            (lambda: [LaggedStart(*[glow(D[i][0], GOLD_M, 1.08) for i in (4, 5, 6, 7)], lag_ratio=0.15), *self.cap("a book: a page", WHITE)], 0.8),
        ])
        self.steps("The picture breaks in one small way. A desk takes books of every size. In memory, every place holds "
                   "exactly one 8 KB page, so any page fits in any place.", [
            (lambda: self.cap("where the desk picture breaks", WHITE), 0.5),
            "In memory",
            (lambda: [LaggedStart(*[glow(f, BLUE_M, 1.03) for f in F], lag_ratio=0.15),
                      *self.cap("every place holds exactly one 8 KB page: any page fits anywhere", BLUE_M)], 1.0),
        ], after=0.4)

        # ---------------- scene 3: keep everything you read ----------------
        bx0, bw = -3.6, 10.0
        b1 = Rectangle(width=bw, height=0.36, stroke_width=0).set_fill(GOLD_M, 0.85)
        b1.move_to([bx0 + bw / 2, -0.75, 0])
        b2 = Rectangle(width=bw * 64 / 2048, height=0.36, stroke_width=0).set_fill(BLUE_M, 1)
        b2.move_to([bx0 + b2.width / 2, -1.55, 0])
        l1 = T("a 2 TB table", 22, GOLD_M)
        l1.move_to([bx0 + l1.width / 2, -0.3, 0])
        l2 = T("64 GB of memory", 22, BLUE_M).next_to(b2, RIGHT, buff=0.2)
        self.steps("The first idea: a map in memory from each page number to that page's bytes, filled on every read. "
                   "It works, until the database is bigger than memory, and most are. "
                   "A 2 TB table won't fit in a server's 64 GB of memory. That desk would need to be the size of the library.", [
            (lambda: self.cap("idea 1: keep every page you read, in a map in memory"), 0.6),
            "It works, until",
            (lambda: self.cap("until the database is bigger than memory", RED_M), 0.5),
            "A 2 TB table",
            (lambda: [FadeIn(l1), GrowFromEdge(b1, LEFT)], 1.0),
            "in a server's",
            (lambda: [GrowFromEdge(b2, LEFT), FadeIn(l2)], 0.7),
            "That desk would",
            (lambda: [glow(desk, RED_M, 1.01)], 0.7),
        ])
        self.steps("So the cache needs a fixed size. And once it's full, something has to leave.", [
            (lambda: [FadeOut(VGroup(b1, b2, l1, l2)), *self.cap("a fixed size, and once it's full, something leaves", YELLOW_M)], 0.7),
            (lambda: [glow(desk, BLUE_M, 1.01)], 0.6),
        ], after=0.4)

        # ---------------- scene 4: four places and a list ----------------
        table = Rectangle(width=DESK[1] - DESK[0], height=TB_TOP - TB_BOT, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M, 0.06), 1)
        table.move_to([(DESK[0] + DESK[1]) / 2, (TB_TOP + TB_BOT) / 2, 0]).set_z_index(-2)
        t_tb = T("the list: which page is in which place", 22, TEAL_M).move_to([0, TB_TOP + 0.38, 0])
        FT = [None] * 4
        TE = [None] * 4
        q = req("read page 10")

        def miss(n, k, rt=0.7, word="place"):
            src = D[dpos(n)]
            FT[k] = ftile(n, k)
            TE[k] = tentry(n, k, word)
            ghost = src.copy()
            return [
                (lambda: [ghost.animate.move_to(FT[k]).scale(1.2)], rt),
                (lambda: [FadeOut(ghost), FadeIn(FT[k]), FadeIn(TE[k], shift=0.1 * DOWN)], 0.4),
            ]

        r_miss = res("miss", ["a walk to the drive:", "about 100 µs"], RED_M)
        self.steps("So, four places on the desk, and a list of which page sits in which place. A query wants page 10. "
                   "The list doesn't have it. So we walk to the shelf, read page 10 into place 0, and write it on the list.", [
            (lambda: [*self.uncap(), FadeIn(table), FadeIn(t_tb)], 0.8),
            "A query wants",
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.5),
            "The list doesn't",
            (lambda: [glow(table, RED_M, 1.01), FadeIn(r_miss, shift=0.1 * UP)], 0.7),
            "So we walk",
            *miss(10, 0, 0.9),
        ])
        self.steps("Pages 11, 12 and 13 fill the other places the same way.", [
            (lambda: [FadeOut(r_miss), Transform(q, req("read pages 11, 12, 13"))], 0.4),
            *miss(11, 1, 0.45), *miss(12, 2, 0.45), *miss(13, 3, 0.45),
        ])
        r_hit = res("hit", "no trip to the drive", GREEN_M)
        self.steps("Now page 11 again. The list says place 1. No walk at all.", [
            (lambda: [Transform(q, req("read page 11"))], 0.5),
            "The list says",
            (lambda: [TE[1].animate.set_color(GREEN_M), glow(FT[1][0], GREEN_M, 1.08)], 0.6),
            "No walk",
            (lambda: [FadeIn(r_hit, shift=0.1 * UP)], 0.5),
        ])
        t_bp = T("the buffer pool", 24, BLUE_M).move_to([0, TITLE_Y, 0])
        t_tb2 = T("the page table", 22, TEAL_M).move_to([0, TB_TOP + 0.38, 0])
        self.steps("These have names. The places are frames, each the size of one page. The list is the page table. "
                   "Found on the list is a hit, and no input or output happens, no trip to the drive. Not found is a miss. "
                   "The whole thing is the buffer pool.", [
            "The places are",
            (lambda: [*[Transform(FL[k], flabel(k, "frame")) for k in range(4)], *self.cap("frame: a page-sized place in memory", BLUE_M)], 0.7),
            "The list is",
            (lambda: [swap(t_tb, t_tb2), TE[1].animate.set_color(WHITE),
                      *[Transform(TE[k], tentry([10, 11, 12, 13][k], k, "frame")) for k in range(4)]], 0.7),
            "Found on the list",
            (lambda: [*self.cap("hit: found in the pool, no I/O (input and output: a trip to the drive)", GREEN_M)], 0.5),
            "Not found",
            (lambda: [*self.cap("miss: not in the pool, read it from the drive", RED_M)], 0.5),
            "The whole thing",
            (lambda: [FadeOut(r_hit), swap(t_mem2, t_bp), glow(desk, BLUE_M, 1.01), *self.uncap()], 0.7),
        ], after=0.4)

        # ---------------- scene 5: the fifth book ----------------
        self.steps("Now a query wants page 42. Every frame is full. What has to happen first? Pause and guess.", [
            (lambda: [Transform(q, req("read page 42", RED_M))], 0.5),
            "Every frame is full",
            (lambda: [LaggedStart(*[glow(f, YELLOW_M, 1.03) for f in F], lag_ratio=0.15)], 0.9),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        old13, old_te = FT[3], TE[3]
        self.steps("A page has to leave. The pool picks a victim, a page to throw out, or evict. Say, for now, page 13. "
                   "Then page 42 is read into its frame, and the list is updated.", [
            (lambda: [*self.cap("a page has to leave: the victim", WHITE)], 0.5),
            "Say, for now",
            (lambda: [old13[0].animate.set_stroke(RED_M), old13[1].animate.set_color(RED_M), *self.cap("evict: throw a page out of the pool (page 13, for now)", RED_M)], 0.5),
            (lambda: [old13.animate.move_to(D[dpos(13)]).scale(0.7).set_opacity(0), FadeOut(old_te)], 0.8),
            "Then page 42",
            *miss(42, 3, 0.8, "frame"),
        ])
        self.remove(old13)
        self.steps("Which page should be the victim? That's the fifth book from the desk, and the rest of this lesson.", [
            (lambda: self.cap("which page should leave? the rest of this lesson", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 6: PostgreSQL's pool, and a guess ----------------
        p1 = band("PostgreSQL: shared_buffers = 128 MB = 16,384 frames of 8 KB", 0, BLUE_M)
        self.steps("PostgreSQL, a free database many companies run, calls its pool shared_buffers. By default it's 128 megabytes: "
                   "16,384 frames of 8 KB, shared by every program connected to it.", [
            (lambda: [*self.uncap(), FadeOut(q)], 0.4),
            "calls its pool",
            (lambda: [FadeIn(p1, shift=0.1 * UP)], 0.6),
            "16,384 frames",
            (lambda: [glow(desk, BLUE_M, 1.01)], 0.7),
        ])
        p2 = band("first count: shared read=1280", 1, RED_M)
        p3 = band("second count: shared hit=1280", 1, GREEN_M)
        self.steps("In the Try it, a table of 200,000 payments takes 1,280 pages. We throw them out of the pool and count the rows. "
                   "The first run reads all 1,280 pages. Run the same count again. What will it say? Pause and guess.", [
            (lambda: [FadeOut(p1), *self.cap("the Try it: 200,000 payments in 1,280 pages", WHITE)], 0.6),
            "The first run",
            (lambda: [FadeIn(p2, shift=0.1 * UP)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(c=(0, -2.25))
        p4 = band("1,280 reads in 0.15 ms: the operating system's copy, not the SSD", 0, GREY_B)
        self.steps("1,280 hits, and no reads at all. One more honest detail: those first 1,280 reads took 0.15 milliseconds in all. "
                   "The operating system kept its own copy of the pages in memory, so the SSD was never touched.", [
            (lambda: [*self.uncap(), p2.animate.move_to([0, BAND[0], 0]), FadeIn(p3, shift=0.1 * UP)], 0.7),
            "One more honest",
            (lambda: [FadeOut(p3), Transform(p2, p4)], 0.7),
            "The operating system",
            (lambda: [Indicate(p2, color=WHITE, scale_factor=1.05)], 0.7),
        ], after=0.4)

        # ---------------- scene 7: why not let the kernel do it? ----------------
        knows = VGroup(T("the database knows:", 24, GREY_B),
                       T("1. which pages a query is using right now", 24),
                       T("2. a changed page must not reach the drive before its log record", 24),
                       T("3. a big scan's pages won't be read again", 24)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        fit(knows, 9.8)
        knows.move_to([-3.7 + knows.width / 2, -0.95, 0])
        mm = band("mmap: 2 to 20 times slower once memory filled up (Crotty, Leis and Pavlo, 2022)", 1, RED_M)
        self.steps("So why not let the operating system cache everything? Some systems do. But the database knows three things "
                   "the kernel doesn't.", [
            (lambda: [FadeOut(p2), FadeOut(VGroup(table, t_tb2, *TE)), *self.cap("why not let the operating system cache everything?", WHITE)], 0.7),
            "But the database",
            (lambda: [FadeIn(knows[0])], 0.4),
        ])
        self.steps("Which pages a query is using right now. That a changed page must not reach the drive before the log record "
                   "that describes it. And that a big scan's pages won't be read again.", [
            (lambda: [*self.uncap(), FadeIn(knows[1], shift=0.1 * UP)], 0.5),
            "That a changed",
            (lambda: [FadeIn(knows[2], shift=0.1 * UP)], 0.5),
            "And that a big",
            (lambda: [FadeIn(knows[3], shift=0.1 * UP)], 0.5),
        ])
        self.steps("A 2022 study measured databases that leave these choices to the kernel through mmap. Once memory filled up, "
                   "they were 2 to 20 times slower. The kernel means well. It just can't see inside a query.", [
            "Once memory",
            (lambda: [FadeIn(mm, shift=0.1 * UP)], 0.6),
            "The kernel means",
            (lambda: self.cap("the kernel means well; it can't see inside a query", GREY_B), 0.5),
        ], after=0.4)

        # ---------------- scene 8: the moral, and a check ----------------
        TE2 = [tentry(n, k, "frame") for k, n in enumerate([10, 11, 12, 42])]
        self.steps("So: keep a fixed number of page-sized frames in memory, and a page table that says which page is in which frame. "
                   "A hit costs nothing. A miss costs a trip to the drive, and maybe a victim.", [
            (lambda: [FadeOut(knows), FadeOut(mm), FadeIn(VGroup(table, t_tb2, *TE2)),
                      *self.cap("fixed frames, a page table; a hit costs nothing, a miss costs a trip", YELLOW_M, 26)], 0.8),
            "A hit costs",
            (lambda: [glow(FT[1][0], GREEN_M, 1.08)], 0.6),
            "A miss costs",
            (lambda: [glow(drive, RED_M, 1.01)], 0.6),
        ], after=0.5)
        q = req("read 11, then 13")
        self.steps("One quick check. The frames now hold pages 10, 11, 12 and 42. A query reads page 11, then page 13. "
                   "Which read is a miss? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(q, shift=0.1 * DOWN)], 0.5),
            "The frames now",
            (lambda: [LaggedStart(*[glow(t[0], GOLD_M, 1.06) for t in FT], lag_ratio=0.15)], 0.9),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        r13 = res("13: miss", ["it went back", "to the shelf"], RED_M)
        r11 = res("11: hit", "frame 1", GREEN_M)
        self.steps("Page 13. It was the victim, so it's back on the shelf. Page 11 is a hit.", [
            (lambda: [*self.uncap(), FadeIn(r13, shift=0.1 * UP), glow(D[dpos(13)][0], RED_M, 1.1)], 0.7),
            "Page 11 is",
            (lambda: [FadeOut(r13), FadeIn(r11, shift=0.1 * UP), TE2[1].animate.set_color(GREEN_M), glow(FT[1][0], GREEN_M, 1.08)], 0.7),
        ], after=0.3)
        self.play(*self.cap("a hit costs nothing; a miss costs a trip to the drive, and maybe a victim", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
