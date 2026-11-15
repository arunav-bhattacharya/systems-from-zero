from sfz import *

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



SX0, SP_, SW_, SH_ = -5.25, 1.05, 0.9, 0.8     # page slots: first centre x, pitch, size
CY, DY_ = 0.3, -2.6                             # slot y in the page cache and on the SSD
BX, BW, BH = -2.625, 6.65, 1.6                  # the two boxes: centre x, width, height
RX = 3.9                                        # centre of the right panel
SVC = np.array([-4.6, 2.75, 0])


def sl(k, y):
    return np.array([SX0 + SP_ * k, y, 0])


def empty(k, y):
    r = DashedVMobject(RoundedRectangle(corner_radius=0.08, width=SW_, height=SH_, stroke_color=GREY_D, stroke_width=2),
                       num_dashes=22).move_to(sl(k, y))
    return r


def page(k, y, rec, state):
    """A page holding one record: dirty (gold), clean (grey) or durable on the SSD (green)."""
    color = {"dirty": GOLD_M, "clean": GREY_B, "disk": GREEN_M, "lost": RED_M}[state]
    r = RoundedRectangle(corner_radius=0.08, width=SW_, height=SH_, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to(sl(k, y))
    t = T(f"rec {rec}", 19).move_to(sl(k, y) + 0.13 * UP)
    s = T({"dirty": "dirty", "clean": "clean", "disk": "stored", "lost": "lost"}[state], 15, color).move_to(sl(k, y) + 0.2 * DOWN)
    return VGroup(r, t, s)


def big_box(y, title, color):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fill(color, 0.08), 1)
    r.move_to([BX, y, 0])
    t = T(title, 21, color)
    t.move_to([BX - BW / 2 + 0.2 + t.width / 2, y + BH / 2 - 0.27, 0])
    return VGroup(r, t)


def side(s, k, color=GREY_B, size=21):
    return fit(T(s, size, color), 4.6).move_to([RX, 1.75 - 0.5 * k, 0])


def call(s, color=GREY_B):
    return chip(s, color, 19, mono=True).move_to([-1.55, SVC[1], 0])


class PageCacheFsync(Base):
    """os-09, section 1 (with section 2's fsync and group commit): write() copies a record into the page cache, marks the
    page dirty and returns in about 10 µs; the flusher writes it after 30 s. A refund written but not forced is lost in a
    power cut. fsync waits for the device (2 to 9 ms in the lab), so a few hundred records a second; group commit makes
    one fsync cover many records."""

    def construct(self):
        self.title_card("The page cache and fsync", "when a write returns, and when it is really on disk")

        svc = box("payment service", WHITE, w=2.8, h=0.75, size=22).move_to(SVC)
        cache = big_box(0.55, "page cache: the kernel's copy in RAM", GOLD_M)
        ssd = big_box(-2.35, "SSD", BLUE_M)
        ce = VGroup(*[empty(k, CY) for k in range(6)])
        de = VGroup(*[empty(k, DY_) for k in range(6)])
        c = call("write(rec 1)")
        clock = ValueTracker(0)
        clk = always_redraw(lambda: T(f"t = {int(round(clock.get_value()))} s", 30, WHITE).move_to([RX, 2.75, 0]))
        p1 = page(0, CY, 1, "dirty")
        w10 = side("write returned: about 10 µs", 0, WHITE)
        self.steps("The payment service appends a 4 kilobyte authorization record to its log with a write call. "
                   "The call returns in about ten microseconds. Is the record on disk?", [
            (lambda: [FadeIn(svc), FadeIn(cache), FadeIn(ce), FadeIn(ssd), FadeIn(de), FadeIn(clk)], 1.0),
            "with a write call",
            (lambda: [FadeIn(c)], 0.5),
            (lambda: [via([SVC + 0.4 * DOWN, sl(0, CY) + 0.4 * UP], YELLOW_M, 0.6)], 0.6),
            (lambda: [FadeIn(p1, scale=0.9)], 0.4),
            "The call returns",
            (lambda: [FadeIn(w10)], 0.6),
            "Is the record",
            (lambda: [glow(de[0], RED_M, 1.15)], 0.8),
        ])

        self.steps("Not yet. The kernel copied it into the page cache, its copy of file data in RAM, "
                   "and marked the page dirty: newer than the disk. Then it returned.", [
            "The kernel copied",
            (lambda: [glow(cache[0], GOLD_M, 1.02)], 0.9),
            "and marked",
            (lambda: [glow(p1[0], GOLD_M, 1.15)], 0.8),
            "Then it returned",
            (lambda: [via([sl(0, CY) + 0.4 * UP, SVC + 0.4 * DOWN], GREEN_M, 0.6)], 0.6),
        ])

        fl = side("writeback: the flusher thread", 1, GOLD_M)
        fl2 = side("after a page is dirty for 30 s", 2, GREY_B)
        self.steps("The kernel's flusher thread writes dirty pages later. Once a page has been dirty for 30 seconds, "
                   "the flusher writes it at its next wake up. This is writeback.", [
            (lambda: [FadeIn(fl)], 0.6),
            "Once a page",
            (lambda: [FadeIn(fl2), clock.animate(rate_func=linear).set_value(30)], 2.2),
            "the flusher writes",
            (lambda: [via([sl(0, CY) + 0.4 * DOWN, sl(0, DY_) + 0.4 * UP], GOLD_M, 0.8)], 0.8),
            (lambda: [FadeIn(page(0, DY_, 1, "disk"), scale=0.9), Transform(p1, page(0, CY, 1, "clean"))], 0.6),
        ])

        c2 = call("write(rec 2)")
        p2 = page(1, CY, 2, "dirty")
        rf = side("rec 2: a refund", 1, WHITE)
        self.steps("Record 2 is a refund. Its write call returns just as fast, and the new page is dirty.", [
            (lambda: [FadeOut(fl), FadeOut(fl2), Transform(c, c2), FadeIn(rf), clock.animate.set_value(31)], 0.6),
            (lambda: [via([SVC + 0.4 * DOWN, sl(1, CY) + 0.4 * UP], YELLOW_M, 0.6)], 0.6),
            (lambda: [FadeIn(p2, scale=0.9)], 0.4),
            "and the new page",
            (lambda: [glow(p2[0], GOLD_M, 1.15)], 0.7),
        ])

        flash = cache[0].copy().set_fill(RED_M, 0.55).set_stroke(RED_M, 4)
        pc = side("power cut: RAM is wiped", 0, RED_M)
        lost = page(1, DY_, 2, "lost")
        xr = tick(False, 0.18).move_to(sl(1, DY_) + [0.6, 0.3, 0])
        self.steps("Now the power goes out. The page cache was RAM, so it's wiped. Record 2 is gone, "
                   "though its write returned success, and the caller may already have heard saved.", [
            (lambda: [FadeIn(flash), FadeOut(w10), FadeOut(rf), FadeIn(pc)], 0.4),
            (lambda: [FadeOut(flash), FadeOut(p1), FadeOut(p2), FadeOut(c)], 0.8),
            "Record 2 is gone",
            (lambda: [FadeIn(lost), Create(xr)], 0.7),
            "and the caller",
            (lambda: [glow(svc[0], RED_M, 1.04)], 0.8),
        ])

        c3 = call("write + fsync", GREEN_M)
        p2b = page(1, CY, 2, "dirty")
        ok = side("rec 2 is durable", 1, GREEN_M)
        self.steps("So the service calls fsync before it answers. The kernel writes the file's dirty pages, "
                   "tells the SSD to flush its own cache, and returns only when the device says the data is stored.", [
            (lambda: [FadeOut(pc), FadeOut(lost), FadeOut(xr), FadeOut(clk), FadeIn(c3)], 0.6),
            (lambda: [via([SVC + 0.4 * DOWN, sl(1, CY) + 0.4 * UP], YELLOW_M, 0.5)], 0.5),
            (lambda: [FadeIn(p2b, scale=0.9)], 0.4),
            "The kernel writes",
            (lambda: [via([sl(1, CY) + 0.4 * DOWN, sl(1, DY_) + 0.4 * UP], GREEN_M, 0.9)], 0.9),
            "tells the SSD",
            (lambda: [glow(ssd[0], BLUE_M, 1.02)], 0.8),
            "and returns only",
            (lambda: [FadeIn(page(1, DY_, 2, "disk"), scale=0.9), Transform(p2b, page(1, CY, 2, "clean"))], 0.6),
            (lambda: [via([sl(1, CY) + 0.4 * UP, SVC + 0.4 * DOWN], GREEN_M, 0.6), FadeIn(ok)], 0.6),
        ])

        cost1 = side("write: 7 to 14 µs a record", 2, GREY_B)
        cost2 = side("fsync each record: 2 to 9 ms", 3, RED_M)
        cost3 = side("one thread: a few hundred a second", 4, RED_M)
        self.steps("That costs milliseconds, not microseconds. In the lab, forcing after every record took 2 to 9 milliseconds, "
                   "so one thread can make only a few hundred records a second durable.", [
            (lambda: [FadeIn(cost1)], 0.6),
            "In the lab",
            (lambda: [FadeIn(cost2)], 0.6),
            "so one thread",
            (lambda: [FadeIn(cost3)], 0.6),
        ])

        cw = call("4 callers waiting", GOLD_M)
        ps = [page(k, CY, k + 1, "dirty") for k in range(2, 6)]
        gc = side("group commit: 1 fsync, 4 records", 1, GREEN_M)
        self.steps("Group commit shares that cost. While one fsync runs, more requests arrive. The service writes all their "
                   "records, calls fsync once, then answers every caller in the group.", [
            (lambda: [FadeOut(ok), FadeOut(cost1), FadeOut(cost3), cost2.animate.set_color(GREY_B), Transform(c3, cw)], 0.7),
            "The service writes",
            (lambda: [LaggedStart(*[via([SVC + 0.4 * DOWN, sl(k, CY) + 0.4 * UP], YELLOW_M, 0.5) for k in range(2, 6)], lag_ratio=0.2)], 1.0),
            (lambda: [LaggedStart(*[FadeIn(p, scale=0.9) for p in ps], lag_ratio=0.15)], 0.6),
            "calls fsync once",
            (lambda: [Transform(c3, call("fsync once", GREEN_M)),
                      *[via([sl(k, CY) + 0.4 * DOWN, sl(k, DY_) + 0.4 * UP], GREEN_M, 0.9) for k in range(2, 6)]], 0.9),
            (lambda: [*[FadeIn(page(k, DY_, k + 1, "disk"), scale=0.9) for k in range(2, 6)],
                      *[Transform(ps[k - 2], page(k, CY, k + 1, "clean")) for k in range(2, 6)], FadeIn(gc)], 0.6),
            "then answers",
            (lambda: [Transform(c3, call("4 callers: OK", GREEN_M)),
                      *[via([sl(k, CY) + 0.4 * UP, SVC + 0.4 * DOWN], GREEN_M, 0.6) for k in range(2, 6)]], 0.7),
        ])

        g100 = side("once per 100 records: tens of µs each", 2, GREEN_M)
        pg = side("PostgreSQL: commits share one log flush", 3, GREY_B)
        self.steps("Forcing once per 100 records brings the cost down to tens of microseconds a record. "
                   "PostgreSQL commits work the same way: concurrent commits share one flush of the log.", [
            (lambda: [FadeOut(cost2), FadeIn(g100)], 0.7),
            "PostgreSQL commits",
            (lambda: [FadeIn(pg)], 0.7),
        ])

        self.steps("A write returns when the kernel has your bytes. fsync returns when the disk has them. "
                   "Answer only after fsync, and let many records share each one.", [
            (lambda: [glow(cache[0], GOLD_M, 1.02)], 0.9),
            "fsync returns",
            (lambda: [glow(ssd[0], GREEN_M, 1.02)], 0.9),
            "and let many",
            (lambda: [glow(c3[0], GREEN_M, 1.06)], 0.9),
        ])
        self.wait(0.6)
