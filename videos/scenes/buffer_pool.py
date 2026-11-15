from sfz import *

SAY.insert(0, (r"\bCLOCK\b", "clock"))

C = np.array([-0.3, -0.2, 0])                 # centre of the clock of frames
R, FW, FH = 2.3, 1.75, 1.15                   # clock radius, frame size
LX = -5.05                                    # centre of the left panel
DX, DY, DW, DH = 4.85, -0.2, 3.3, 3.4         # the SSD box
CELL = {10: (0, 0), 11: (1, 0), 12: (2, 0), 13: (0, 1), 14: (1, 1), 15: (2, 1), 42: (0, 2), 50: (1, 2)}
LEG_Y = [-1.25, -1.7, -2.15]


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def via(points, color=YELLOW_M, run_time=0.9):
    """A dot that runs along a polyline and stays invisible until its turn."""
    pts = [np.array(p, dtype=float) for p in points]
    path = VMobject().set_points_as_corners(pts)
    d = Dot(radius=0.08, color=color).move_to(pts[0]).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def ang(i):
    return np.radians(90 - 60 * i)


def fpos(i):
    return C + R * np.array([np.cos(ang(i)), np.sin(ang(i)), 0])


def frame(i, page=None, ref=None, pin=None, dirty=False, color=WHITE):
    """One frame of the pool: the page it holds and, once introduced, its reference bit, pin count and dirty flag."""
    p = fpos(i)
    if page is None:
        r = DashedVMobject(RoundedRectangle(corner_radius=0.12, width=FW, height=FH, stroke_color=GREY_C, stroke_width=2.5),
                           num_dashes=30).move_to(p)
        return VGroup(r, T("free", 20, GREY_C).move_to(p), VGroup(), VGroup())
    r = RoundedRectangle(corner_radius=0.12, width=FW, height=FH, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to(p)
    pg = T(f"page {page}", 22).move_to(p + 0.27 * UP)
    parts = []
    if ref is not None:
        parts.append(M(f"ref {ref}", 15, GREEN_M if ref else GREY_B))
    if pin is not None:
        parts.append(M(f"pin {pin}", 15, PURPLE_M if pin else GREY_B))
    meta = VGroup(*parts).arrange(RIGHT, buff=0.3).move_to(p + 0.08 * DOWN) if parts else VGroup()
    dt = T("dirty", 17, GOLD_M).move_to(p + 0.37 * DOWN) if dirty else VGroup()
    return VGroup(r, pg, meta, dt)


def cell_pos(pg):
    c, r = CELL[pg]
    return np.array([DX - 0.9 + 0.9 * c, DY + 0.55 - 0.7 * r, 0])


def left(s, k, color=GREY_B, size=20):
    return fit(T(s, size, color), 3.0).move_to([LX, 2.1 - 0.45 * k, 0])


def req(s, color=GREY_B):
    return chip(s, color, 20, mono=True).move_to([LX, 2.85, 0])


def legend(s, k, color):
    return fit(T(s, 19, color), 3.0).move_to([LX, LEG_Y[k], 0])


class BufferPool(Base):
    """store-03, sections 0 to 2: six frames on a clock face hold pages of a 2 TB ledger. A miss reads from the SSD (about
    100 µs), a hit costs no I/O. Page 11 is pinned, page 13 is dirty. page 50 needs a victim: FIFO would evict hot page 10;
    CLOCK's hand clears reference bits, skips the pin, stops at page 13, writes it back, and loads page 50 there."""

    def construct(self):
        self.title_card("The buffer pool", "frames, pins, dirty pages and the clock hand")

        dbox = RoundedRectangle(corner_radius=0.14, width=DW, height=DH, stroke_color=BLUE_M, stroke_width=3).set_fill(fill(BLUE_M, 0.1), 1)
        dbox.move_to([DX, DY, 0])
        dtitle = T("SSD: 2 TB ledger", 22, BLUE_M).move_to([DX, DY + DH / 2 - 0.35, 0])
        cells = {}
        for pg in CELL:
            r = RoundedRectangle(corner_radius=0.06, width=0.78, height=0.5, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
            r.move_to(cell_pos(pg))
            cells[pg] = VGroup(r, T(str(pg), 19).move_to(cell_pos(pg)))
        dots = T("…", 22, GREY_B).move_to(cell_pos(50) + 0.9 * RIGHT)
        dnote = T("8 KB pages, about 100 µs a read", 19, GREY_B).move_to([DX, DY - DH / 2 - 0.32, 0])
        fr = [frame(i) for i in range(6)]
        ptitle = VGroup(T("buffer pool", 24), T("6 frames in RAM", 19, GREY_B)).arrange(DOWN, buff=0.15).move_to(C)
        self.steps("A payments ledger is 2 terabytes of 8 kilobyte pages on an SSD, about 100 microseconds a read. "
                   "So the database keeps copies of pages in a fixed set of slots in RAM, called frames: the buffer pool.", [
            (lambda: [FadeIn(dbox), FadeIn(dtitle)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(c) for c in cells.values()], FadeIn(dots), lag_ratio=0.1)], 0.9),
            "about 100",
            (lambda: [FadeIn(dnote, shift=0.1 * UP)], 0.6),
            "So the database",
            (lambda: [LaggedStart(*[FadeIn(f, scale=0.9) for f in fr], lag_ratio=0.15)], 1.5),
            "the buffer pool",
            (lambda: [FadeIn(ptitle)], 0.6),
        ])

        q = req("fetch(page 10)")
        o1 = left("miss: read it from the SSD", 1, RED_M)
        self.steps("A query asks for page 10. It isn't in the pool, so that's a miss: "
                   "the pool reads it from the SSD into a free frame.", [
            (lambda: [FadeIn(q)], 0.6),
            "so that's a miss",
            (lambda: [FadeIn(o1)], 0.5),
            "the pool reads",
            (lambda: [glow(cells[10][0], YELLOW_M, 1.08)], 0.5),
            (lambda: [via([cell_pos(10) + 0.25 * UP, [3.0, 2.95, 0], fpos(0) + [FW / 2, 0.3, 0]], YELLOW_M, 1.0)], 1.0),
            (lambda: [Transform(fr[0], frame(0, 10))], 0.5),
        ])

        o2 = left("hit: no disk read", 1, GREEN_M)
        self.steps("More misses fill the other frames. Ask for page 12 again, and it's already there. "
                   "That's a hit, with no disk read at all.", [
            (lambda: [FadeOut(o1), LaggedStart(*[Transform(fr[i], frame(i, 10 + i)) for i in range(1, 6)], lag_ratio=0.2)], 1.4),
            "Ask for page 12",
            (lambda: [Transform(q, req("fetch(page 12)", GREEN_M))], 0.5),
            "That's a hit",
            (lambda: [glow(fr[2][0], GREEN_M), FadeIn(o2)], 0.8),
        ])

        lp = legend("pin above 0: in use", 0, PURPLE_M)
        self.steps("A query reading page 11 right now holds a pin on it. "
                   "A frame with a pin is never evicted.", [
            (lambda: [FadeOut(q), FadeOut(o2), *[Transform(fr[i], frame(i, 10 + i, pin=0)) for i in range(6) if i != 1],
                      Transform(fr[1], frame(1, 11, pin=0))], 0.7),
            "A query reading",
            (lambda: [Transform(fr[1], frame(1, 11, pin=1, color=PURPLE_M)), FadeIn(lp)], 0.8),
            "never evicted",
            (lambda: [glow(fr[1][0], PURPLE_M)], 0.8),
        ])

        ld = legend("dirty: newer than disk", 1, GOLD_M)
        self.steps("An update changed page 13 in memory only. Its frame is dirty: newer than the copy on disk.", [
            (lambda: [Transform(fr[3], frame(3, 13, pin=0, dirty=True, color=GOLD_M))], 0.8),
            "Its frame is dirty",
            (lambda: [FadeIn(ld)], 0.6),
            "newer than",
            (lambda: [glow(cells[13][0], GOLD_M, 1.08)], 0.7),
        ])

        q = req("fetch(page 50)", RED_M)
        o3 = left("miss, and no free frame", 1, RED_M)
        self.steps("Now page 50 is needed, and every frame is full. Which page should leave?", [
            (lambda: [FadeIn(q), glow(cells[50][0], RED_M, 1.08)], 0.7),
            "and every frame",
            (lambda: [FadeIn(o3), *[glow(f[0], RED_M, 1.03) for f in fr]], 0.9),
        ])

        fifo = T("loaded first", 18, RED_M).next_to(fr[0], LEFT, buff=0.2)
        o4 = left("an index top every query reads", 2, RED_M, 19)
        self.steps("Evicting the page loaded first would throw out page 10, the top of an index that every query reads. "
                   "The next query would read it straight back.", [
            (lambda: [fr[0][0].animate.set_stroke(RED_M), FadeIn(fifo)], 0.7),
            "the top of an index",
            (lambda: [FadeIn(o4)], 0.6),
            "The next query",
            (lambda: [via([fpos(0) + [FW / 2, 0.3, 0], [3.0, 2.95, 0], cell_pos(10) + 0.25 * UP], RED_M, 0.7)], 0.7),
            (lambda: [via([cell_pos(10) + 0.25 * UP, [3.0, 2.95, 0], fpos(0) + [FW / 2, 0.3, 0]], RED_M, 0.7)], 0.7),
        ])

        refs = {0: 1, 1: 0, 2: 1, 3: 0, 4: 1, 5: 0}
        lr = legend("ref 1: used recently", 2, GREEN_M)

        def fstate(i):
            return frame(i, 10 + i, ref=refs[i], pin=1 if i == 1 else 0, dirty=(i == 3),
                         color=PURPLE_M if i == 1 else GOLD_M if i == 3 else WHITE)

        self.steps("Least recently used is better, but it reorders one shared list on every hit. "
                   "CLOCK keeps one bit per frame instead: a hit sets its frame's reference bit to 1.", [
            (lambda: [FadeOut(fifo), FadeOut(o4), Transform(fr[0], frame(0, 10, pin=0))], 0.6),
            "CLOCK keeps",
            (lambda: [*[Transform(fr[i], frame(i, 10 + i, ref=0, pin=1 if i == 1 else 0, dirty=(i == 3),
                                               color=PURPLE_M if i == 1 else GOLD_M if i == 3 else WHITE)) for i in range(6)]], 0.7),
            "a hit sets",
            (lambda: [*[Transform(fr[i], fstate(i)) for i in (0, 2, 4)], *[glow(fr[i][0], GREEN_M) for i in (0, 2, 4)], FadeIn(lr)], 0.9),
        ])

        hand = Arrow(C, C + 1.3 * UP, buff=0, stroke_width=5, color=YELLOW_M, max_tip_length_to_length_ratio=0.2)
        hub = Dot(C, radius=0.09, color=YELLOW_M)

        def turn(n=1):
            return Rotate(hand, -n * PI / 3, about_point=C)

        self.steps("To find a victim, a hand sweeps the frames like a clock. A bit set to 1 is cleared, "
                   "and that frame gets a second chance. A pinned frame is skipped.", [
            (lambda: [FadeOut(o3), FadeOut(ptitle)], 0.4),
            (lambda: [GrowArrow(hand), FadeIn(hub)], 0.6),
            "A bit set to 1",
            (lambda: [glow(fr[0][0], GREEN_M)], 0.5),
            (lambda: [Transform(fr[0], frame(0, 10, ref=0, pin=0))], 0.6),
            "A pinned frame",
            (lambda: [turn()], 0.6),
            (lambda: [glow(fr[1][0], PURPLE_M)], 0.6),
            (lambda: [turn()], 0.6),
            (lambda: [Transform(fr[2], frame(2, 12, ref=0, pin=0))], 0.6),
        ])

        o5 = left("victim: page 13", 1, RED_M)
        self.steps("The first unpinned frame with its bit at 0 is the victim: page 13.", [
            (lambda: [turn()], 0.7),
            "is the victim",
            (lambda: [fr[3][0].animate.set_stroke(RED_M, width=4), FadeIn(o5)], 0.7),
        ])

        out = [fpos(3) + [FW / 2, 0, 0], [2.9, -2.8, 0], cell_pos(13) + [-0.39, -0.1, 0]]
        o6 = left("write page 13 back first", 2, GOLD_M)
        self.steps("Page 13 is dirty, so the pool writes it back to the SSD first. A clean one is just dropped.", [
            (lambda: [FadeIn(o6)], 0.5),
            (lambda: [via(out, GOLD_M, 1.1)], 1.1),
            (lambda: [glow(cells[13][0], GOLD_M, 1.1)], 0.6),
            (lambda: [Transform(fr[3], frame(3, 13, ref=0, pin=0, color=RED_M))], 0.6),
        ])

        inn = [cell_pos(50) + 0.25 * DOWN, [2.9, -2.8, 0], fpos(3) + [FW / 2, 0, 0]]
        o7 = left("page 50 loaded, ref 1", 1, GREEN_M)
        self.steps("Then page 50 is read into that frame, and the hand rests just past it.", [
            (lambda: [FadeOut(o5), FadeOut(o6), via(inn, YELLOW_M, 1.1)], 1.1),
            (lambda: [Transform(fr[3], frame(3, 50, ref=1, pin=0)), FadeIn(o7), Transform(q, req("fetch(page 50)", GREEN_M))], 0.7),
            "and the hand",
            (lambda: [turn()], 0.7),
        ])

        o8 = left("hit on page 10: ref 1 again", 2, GREEN_M, 19)
        pg = T("PostgreSQL: a count up to 5", 19, GREY_B).move_to([LX, -2.9, 0])
        self.steps("A hot page sets its bit again before the hand comes back, so it stays. "
                   "A page touched once leaves first. PostgreSQL uses a small count, up to 5, in place of the bit.", [
            (lambda: [FadeOut(o7), Transform(q, req("fetch(page 10)", GREEN_M))], 0.5),
            (lambda: [Transform(fr[0], frame(0, 10, ref=1, pin=0)), glow(fr[0][0], GREEN_M), FadeIn(o8)], 0.8),
            "A page touched once",
            (lambda: [glow(fr[5][0], GREY_B)], 0.8),
            "PostgreSQL uses",
            (lambda: [FadeIn(pg, shift=0.1 * UP)], 0.7),
        ])

        self.steps("A buffer pool keeps hot pages in a fixed set of frames. Never evict a pinned page, "
                   "give recent ones a second chance, and write a dirty victim back first.", [
            (lambda: [*[glow(f[0], WHITE, 1.02) for f in fr]], 0.9),
            "Never evict",
            (lambda: [glow(fr[1][0], PURPLE_M)], 0.8),
            "give recent",
            (lambda: [Rotate(hand, -2 * PI, about_point=C)], 1.6),
            "and write",
            (lambda: [Indicate(ld, color=GOLD_M)], 1.0),
        ])
        self.wait(0.6)
