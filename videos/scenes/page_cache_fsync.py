from sfz import *

SAY.insert(0, (r"\bdd\b", "D D"))
SAY.insert(0, (r"\bkill -9\b", "kill minus nine"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BOX_TOP, BOX_BOT = 2.3, -1.3
PG = (-6.6, -4.0)                      # the payments program
PC = (-3.1, 0.9)                       # the page cache (RAM): the outgoing tray
DK = (2.4, 6.6)                        # the disk
SLOT_Y = [1.55, 0.45, -0.65]
VAN_HOME = np.array([1.65, 2.72, 0])
GAUGE_Y, STATUS_Y, CAP_Y, BAR_Y = -1.9, -2.5, -3.32, -2.95
G_X0, G_W = PC[0], PC[1] - PC[0]        # the dirty-data gauge, 0 to 25 % of memory


def cx(r):
    return (r[0] + r[1]) / 2


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
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def harrow(a, b, color=GREY_B, sw=2.5):
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.15, max_stroke_width_to_length_ratio=8)


def bigbox(r, color):
    rect = RoundedRectangle(corner_radius=0.14, width=r[1] - r[0], height=BOX_TOP - BOX_BOT, stroke_color=color, stroke_width=3)
    return rect.set_fill(fillc(color), 1).move_to([cx(r), (BOX_TOP + BOX_BOT) / 2, 0])


def box_title(r, s, color):
    return T(s, 22, color).move_to([cx(r), BOX_TOP + 0.35, 0])


def slot(r, j):
    return RoundedRectangle(corner_radius=0.08, width=r[1] - r[0] - 0.4, height=0.82, stroke_color=GREY_C, stroke_width=2) \
        .set_fill(BLACK, 1).move_to([cx(r), SLOT_Y[j], 0])


def slot_text(r, j, s, color=WHITE):
    return left_at(M(s, 16, color), r[0] + 0.38, SLOT_Y[j])


def slot_state(r, j, s, color):
    return right_at(T(s, 18, color), r[1] - 0.38, SLOT_Y[j])


STATE_COL = {"dirty": GOLD_M, "clean": GREEN_M, "empty": GREY_B, "nothing yet": GREY_B, "on disk": GREEN_M, "lost": RED_M}


class PageCacheFsync(Base):
    """os-09, section 1. A payment approved two seconds before a power cut is gone afterwards. write() copies into the
    page cache, marks pages dirty and returns; dd's 64 MB shows file_dirty 67108864 and waits about 30 s. The post
    office: the clerk says done, the letter waits in the outgoing tray, a van empties it now and then. Writeback by
    the flusher threads: age (30 s, wake-ups every 5 s), 10 % background, 20 % throttling, fsync. The stepper's three
    records: one written back by age, one forced with fsync, one lost in the power cut. A crash loses nothing; a
    power cut loses dirty pages. Guardrail, the opening answered, moral, check."""

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

    def page(self, j, rec, state):
        """Page j of the cache: what it holds and whether it's dirty or clean."""
        txt = f"page {j}: rec {rec}" if rec else f"page {j}"
        return [*self.put(f"pt{j}", slot_text(PC, j, txt)), *self.put(f"ps{j}", slot_state(PC, j, state, STATE_COL[state]))]

    def block(self, j, rec, state):
        txt = f"block {j}: rec {rec}" if rec else f"block {j}"
        return [*self.put(f"bt{j}", slot_text(DK, j, txt)), *self.put(f"bs{j}", slot_state(DK, j, state, STATE_COL[state]))]

    def call(self, s, res=None, color=WHITE):
        out = self.put("call", fit(M(s, 18, color), 2.3).move_to([cx(PG), 0.75, 0]))
        if res == "":
            out += self.drop("res")
        elif res is not None:
            out += self.put("res", fit(T(res, 17, GREY_B), 2.3).move_to([cx(PG), 0.25, 0]))
        return out

    def clock(self, s):
        return self.put("clock", T(s, 22, WHITE).move_to([cx(PG), BOX_TOP + 0.35, 0]))

    def status(self, s, color):
        return self.put("status", T(s, 22, color).move_to([0, STATUS_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def van_trip(self, j, color=GREEN_M):
        """The van (flusher) carries page j from the tray to the disk."""
        v = self.van
        return Succession(v.animate(run_time=0.4).move_to([VAN_HOME[0], SLOT_Y[j] + 0.62, 0]),
                          dot_run([PC[1] - 0.25, SLOT_Y[j], 0], [DK[0] + 0.25, SLOT_Y[j], 0], color, 0.6),
                          v.animate(run_time=0.35).move_to(VAN_HOME))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Done, but not on the disk", "the page cache and writeback")

        # ---------------- scene 1: the power cut ----------------
        reader = VGroup(RoundedRectangle(corner_radius=0.15, width=2.6, height=1.7, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1),
                        T("card reader", 20, GREY_B)).move_to([-4.2, 0.6, 0])
        reader[1].move_to(reader[0].get_top() + 0.35 * DOWN)
        appr = VGroup(tick(True, 0.16), T("approved", 24, GREEN_M)).arrange(RIGHT, buff=0.15).move_to(reader[0].get_center() + 0.2 * DOWN)
        logf = VGroup(RoundedRectangle(corner_radius=0.1, width=4.4, height=2.2, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1),
                      T("the log file", 20, BLUE_M)).move_to([2.6, 0.6, 0])
        logf[1].move_to(logf[0].get_top() + 0.32 * DOWN)
        lines = [left_at(M(s, 18, GREY_B), 0.75, 0.75 - 0.42 * i) for i, s in enumerate(["...", "pay 4417  40.00"])]
        newl = left_at(M("pay 8802  9.00", 18, YELLOW_M), 0.75, -0.09)
        self.steps("Picture a power cut on the café's street, two seconds after a customer taps their card. "
                   "The card reader had already beeped.", [
            (lambda: [FadeIn(reader, shift=0.1 * RIGHT)], 0.7),
            "The card reader",
            (lambda: [FadeIn(appr, scale=0.8)], 0.5),
        ])
        wr = harrow(reader.get_right() + [0.1, 0, 0], logf.get_left() + [-0.1, 0, 0], GREY_B)
        self.steps("The payments program had written the payment to its log file, and said approved.", [
            (lambda: [FadeIn(logf), *[FadeIn(l) for l in lines]], 0.6),
            "had written",
            (lambda: [GrowArrow(wr)], 0.4),
            (lambda: [FadeIn(newl, shift=0.1 * LEFT)], 0.5),
            "said approved",
            (lambda: [Indicate(appr, color=GREEN_M, scale_factor=1.1)], 0.7),
        ])
        dark = Rectangle(width=15, height=9, stroke_width=0).set_fill(BLACK, 0.92).set_z_index(20)
        gone = left_at(T("(not there)", 18, RED_M), 0.75, -0.09)
        self.steps("When the power comes back, the payment isn't in the file. Every step had said it worked. "
                   "So where did the payment go?", [
            (lambda: [FadeIn(dark)], 0.25),
            (lambda: [FadeOut(newl), FadeOut(wr)], 0.4),
            (lambda: [FadeOut(dark)], 0.35),
            "isn't in the file",
            (lambda: [FadeIn(gone)], 0.5),
            "Every step",
            (lambda: [Indicate(appr, color=GREEN_M, scale_factor=1.1)], 0.7),
            "So where",
            (lambda: [FadeIn(T("?", 60, YELLOW_M).move_to([0, -1.6, 0]), scale=0.6)], 0.5),
        ], after=0.4)
        hook = [m for m in self.mobjects]

        # ---------------- scene 2: watch a write ----------------
        pg = bigbox(PG, TEAL_M)
        pg_t = T("payments program", 20).move_to([cx(PG), BOX_TOP - 0.38, 0])
        pc = bigbox(PC, GOLD_M)
        dk = bigbox(DK, BLUE_M)
        pslots = [slot(PC, j) for j in range(3)]
        bslots = [slot(DK, j) for j in range(3)]
        wa = [harrow([PG[1] + 0.08, SLOT_Y[j], 0], [PC[0] - 0.08, SLOT_Y[j], 0], GREY_B) for j in range(3)]
        self.steps("Let's watch a write. A program adds a record to a file with a call named write. "
                   "It returns success in microseconds.", [
            (lambda: [FadeOut(Group(*hook))], 0.6),
            "Let's watch",
            (lambda: [FadeIn(pg), FadeIn(pg_t), FadeIn(dk), *self.put("dktitle", box_title(DK, "disk", BLUE_M)), *[FadeIn(s) for s in bslots],
                      *[x for j in range(3) for x in self.block(j, None, "nothing yet")]], 0.8),
            "a call named write",
            (lambda: [*self.call("write(rec 1)"), GrowArrow(wa[0])], 0.5),
            "It returns",
            (lambda: [*self.call("write(rec 1)", "returned at once", WHITE)], 0.5),
        ])
        rd = fit(M("read: gets rec 1", 17, GREEN_M), 2.3).move_to([cx(PG), -0.35, 0])
        self.steps("And any program that reads the file straight after sees the new record. So far, it looks like it's on the disk.", [
            (lambda: [FadeIn(rd, shift=0.1 * UP)], 0.5),
            "So far",
            (lambda: [Indicate(self.lab["bs0"], color=RED_M, scale_factor=1.2)], 0.8),
        ])
        dd1 = T("dd: 64 MB written to a file, in a fraction of a second", 22, WHITE)
        dd2 = M("memory.stat:  file_dirty 67108864", 22, GOLD_M)
        self.steps("Here's a bigger test from the lab. A command called dd writes 64 megabytes to a file, in a fraction of a second. "
                   "Right after, the kernel's own count says: 64 megabytes of that file are in RAM, and not on the disk.", [
            (lambda: [FadeOut(rd), *self.cap(dd1)], 0.6),
            "Right after",
            (lambda: self.cap(dd2), 0.6),
            "in RAM",
            (lambda: [FadeIn(pc), *self.put("pctitle", box_title(PC, "page cache (RAM)", GOLD_M)), *[FadeIn(s) for s in pslots]], 0.7),
            (lambda: [*[x for j in range(3) for x in self.page(j, None, "dirty")], *self.clock("t = 0 s")], 0.6),
        ])
        self.steps("So when does it reach the disk? Pause and guess.", [
            (lambda: self.cap("when does it reach the disk?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.van = VGroup(RoundedRectangle(corner_radius=0.1, width=1.0, height=0.46, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M, 0.4), 1),
                          T("van", 18, TEAL_M)).move_to(VAN_HOME).set_z_index(4)
        self.van[1].move_to(self.van[0])
        self.steps("About 30 seconds later, when nothing else was going on. Until then, the newest data was only in RAM.", [
            (lambda: [*self.uncap(), *self.clock("t = 10 s")], 0.4),
            (lambda: self.clock("t = 20 s"), 0.4),
            (lambda: self.clock("t = 30 s"), 0.4),
            (lambda: [FadeIn(self.van)], 0.3),
            (lambda: [self.van_trip(0), *self.page(0, None, "clean"), *self.block(0, None, "on disk")], 1.4),
            (lambda: [self.van_trip(1), *self.page(1, None, "clean"), *self.block(1, None, "on disk")], 1.4),
            (lambda: [self.van_trip(2), *self.page(2, None, "clean"), *self.block(2, None, "on disk")], 1.4),
            (lambda: self.cap("64 MB waited 30 to 34 seconds", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 3: what write really does ----------------
        self.steps("Here's what write really does. It copies your bytes into the page cache, the kernel's copy of file pages in RAM. "
                   "It marks each page dirty, meaning newer than the disk. And it returns.", [
            (lambda: [*self.uncap(), *[x for j in range(3) for x in self.page(j, None, "empty")],
                      *[x for j in range(3) for x in self.block(j, None, "nothing yet")], *self.clock("t = 0 s"),
                      *self.call("write(rec 1)")], 0.6),
            "copies your bytes",
            (lambda: [dot_run(wa[0].get_start(), wa[0].get_end(), YELLOW_M, 0.6)], 0.7),
            (lambda: self.page(0, 1, "empty"), 0.3),
            "page cache, the",
            (lambda: [glow(pc, GOLD_M, 1.02)], 0.7),
            "marks each page dirty",
            (lambda: self.page(0, 1, "dirty"), 0.5),
            "And it returns",
            (lambda: self.call("write(rec 1)", "returned at once"), 0.5),
        ])
        self.steps("Why not wait for the disk each time? Then every small write would pay for a trip to the device. "
                   "And a page rewritten a hundred times in a second can go to the disk once.", [
            (lambda: self.cap("wait for the disk on every write? every small write pays for a trip", WHITE), 0.6),
            "a page rewritten",
            (lambda: [*self.cap("rewritten 100 times in a second, written to the disk once", WHITE),
                      LaggedStart(*[dot_run(wa[0].get_start(), wa[0].get_end(), YELLOW_M, 0.3) for _ in range(5)], lag_ratio=0.3)], 1.4),
        ], after=0.4)

        # ---------------- scene 4: the post office ----------------
        self.steps("A post office works the same way. You hand the clerk a letter. The clerk says done, and drops it in the outgoing tray. "
                   "Now and then, a van empties the tray.", [
            (lambda: [*self.uncap(), *self.put("pctitle", box_title(PC, "the outgoing tray", GOLD_M))], 0.6),
            "The clerk says done",
            (lambda: [Indicate(self.lab["res"], color=WHITE, scale_factor=1.15)], 0.6),
            "drops it",
            (lambda: [Indicate(self.lab["pt0"], color=GOLD_M, scale_factor=1.1)], 0.6),
            "a van empties",
            (lambda: [glow(self.van[0], TEAL_M, 1.1)], 0.7),
        ])
        self.steps("And anyone who asks for your letter before the van comes gets it straight from the tray.", [
            (lambda: [FadeIn(rd.move_to([cx(PG), -0.35, 0]), shift=0.1 * UP)], 0.5),
            "straight from the tray",
            (lambda: [dot_run(wa[0].get_end(), wa[0].get_start(), GREEN_M, 0.6)], 0.7),
        ])
        self.steps("So the clerk wasn't lying. Your letter really is in the building. It just hasn't left yet.", [
            (lambda: [FadeOut(rd), *self.cap("the clerk wasn't lying: the letter is in the building, it just hasn't left yet", WHITE)], 0.6),
            "It just hasn't",
            (lambda: [Indicate(self.lab["ps0"], color=GOLD_M, scale_factor=1.25)], 0.7),
        ], after=0.3)
        self.steps("Let's map it. The clerk saying done is write returning. The tray is the page cache. A letter in the tray is a dirty page. "
                   "And the van is called writeback: kernel threads, called flushers, that write dirty pages to the disk later.", [
            (lambda: [*self.uncap(), Indicate(self.lab["res"], color=WHITE, scale_factor=1.15)], 0.6),
            "The tray is",
            (lambda: [*self.put("pctitle", box_title(PC, "page cache (RAM)", GOLD_M)), glow(pc, GOLD_M, 1.02)], 0.7),
            "A letter in",
            (lambda: [Indicate(self.lab["ps0"], color=GOLD_M, scale_factor=1.25)], 0.6),
            "the van is called",
            (lambda: [*self.cap("writeback: flusher threads in the kernel write dirty pages later", TEAL_M)], 0.6),
            "called flushers",
            (lambda: [Transform(self.van[1], T("flusher", 17, TEAL_M).move_to(self.van[0])), glow(self.van[0], TEAL_M, 1.1)], 0.7),
        ], after=0.4)

        # ---------------- scene 5: what sends the van ----------------
        gbar = Rectangle(width=G_W, height=0.26, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1)
        left_at(gbar, G_X0, GAUGE_Y)
        glab = right_at(T("dirty data", 18, GREY_B), G_X0 - 0.2, GAUGE_Y)
        gx = lambda pct: G_X0 + G_W * pct / 25
        ticks = VGroup(*[VGroup(Line([gx(p), GAUGE_Y - 0.2, 0], [gx(p), GAUGE_Y + 0.2, 0], stroke_width=2.5, color=c),
                                T(f"{p}%", 16, c).move_to([gx(p), GAUGE_Y - 0.36, 0])) for p, c in ((10, TEAL_M), (20, RED_M))])

        def fill_to(p, color=GOLD_M):
            r = Rectangle(width=max(0.02, G_W * p / 25), height=0.26, stroke_width=0).set_fill(color, 0.8)
            return left_at(r, G_X0, GAUGE_Y)

        self.gf = fill_to(0.2)
        self.steps("Four things send the van. First, age. A page that has been dirty for 30 seconds goes at the flusher's next wake-up, "
                   "every 5 seconds by default.", [
            (lambda: [*self.uncap(), *self.cap("1. age: dirty for 30 seconds", WHITE), *self.clock("t = 25 s")], 0.6),
            "for 30 seconds",
            (lambda: self.clock("t = 30 s"), 0.4),
            "next wake-up",
            (lambda: [self.van_trip(0), *self.page(0, 1, "clean"), *self.block(0, 1, "on disk")], 1.4),
            "every 5",
            (lambda: self.cap("1. age: dirty for 30 seconds; the flusher wakes every 5 seconds", WHITE), 0.5),
        ])
        self.steps("Second, a full tray. When dirty data passes 10 percent of the memory it could use, the flusher starts early.", [
            (lambda: [*self.cap("2. a full tray: past 10% of memory, write back early", WHITE), FadeIn(gbar), FadeIn(glab), FadeIn(ticks), FadeIn(self.gf)], 0.7),
            "passes 10",
            (lambda: [Transform(self.gf, fill_to(11))], 0.9),
            "starts early",
            (lambda: [self.van_trip(1), Transform(self.gf, fill_to(6))], 1.4),
        ])
        self.steps("Third, an overflowing tray. Past 20 percent, a program that writes more is made to wait, and help. "
                   "That's when write suddenly gets slow.", [
            (lambda: [*self.cap("3. an overflowing tray: past 20%, writers must wait and help", RED_M), Transform(self.gf, fill_to(21, RED_M))], 1.0),
            "made to wait",
            (lambda: [*self.call("write(...)", "made to wait", RED_M), glow(pg, RED_M, 1.02)], 0.7),
            "suddenly gets slow",
            (lambda: [Indicate(self.lab["res"], color=RED_M, scale_factor=1.15)], 0.7),
        ])
        self.steps("And fourth, the program asks, with a call named fsync.", [
            (lambda: [*self.cap("4. the program asks: fsync", WHITE), Transform(self.gf, fill_to(3)), *self.call("fsync(fd)", "")], 0.7),
        ], after=0.4)

        # ---------------- scene 6: three records ----------------
        self.steps("Let's follow the log file. Record 1 is a payment. write copies it into page 0, marks it dirty, and returns. "
                   "If the power went out now, record 1 would be lost.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(gbar, glab, ticks, self.gf)), *self.clock("t = 0 s"),
                      *[x for j in range(3) for x in self.page(j, None, "empty")], *[x for j in range(3) for x in self.block(j, None, "nothing yet")]], 0.7),
            "write copies",
            (lambda: [*self.call("write(rec 1)"), dot_run(wa[0].get_start(), wa[0].get_end(), YELLOW_M, 0.5)], 0.6),
            (lambda: [*self.page(0, 1, "dirty"), *self.call("write(rec 1)", "returned at once")], 0.5),
            "If the power",
            (lambda: self.status("if the power went out now: record 1 is lost", RED_M), 0.5),
        ])
        self.steps("30 seconds later, the flusher wakes. Page 0 has been dirty long enough, so it goes to the disk, and the page is clean.", [
            (lambda: [*self.clock("t = 30 s"), *self.call("(busy elsewhere)", "")], 0.5),
            "so it goes",
            (lambda: [self.van_trip(0), *self.page(0, 1, "clean"), *self.block(0, 1, "on disk")], 1.4),
            (lambda: self.status("if the power went out now: record 1 survives", GREEN_M), 0.5),
        ])
        self.steps("Record 2 is a refund the program must not lose. write returns just as fast. So before it says approved, "
                   "the program calls fsync.", [
            (lambda: [*self.clock("t = 31 s"), *self.call("write(rec 2)"), GrowArrow(wa[1])], 0.5),
            (lambda: [dot_run(wa[1].get_start(), wa[1].get_end(), YELLOW_M, 0.5)], 0.6),
            (lambda: [*self.page(1, 2, "dirty"), *self.call("write(rec 2)", "returned at once"),
                      *self.status("if the power went out now: record 2 is lost", RED_M)], 0.5),
            "calls fsync",
            (lambda: self.call("fsync(fd)", "waiting for the disk", GOLD_M), 0.5),
        ])
        self.steps("The kernel writes the page, tells the disk to save it, and returns only when the disk confirms. "
                   "Milliseconds instead of microseconds, and record 2 is safe.", [
            (lambda: [dot_run([PC[1] - 0.25, SLOT_Y[1], 0], [DK[0] + 0.25, SLOT_Y[1], 0], GOLD_M, 0.7)], 0.8),
            (lambda: [*self.page(1, 2, "clean"), *self.block(1, 2, "on disk")], 0.4),
            "returns only",
            (lambda: [dot_run([DK[0] + 0.25, SLOT_Y[1] - 0.2, 0], [PG[1] + 0.1, SLOT_Y[1] - 0.2, 0], GREEN_M, 0.7)], 0.8),
            (lambda: self.call("fsync(fd)", "returned in about 3 ms", GREEN_M), 0.4),
            "record 2 is safe",
            (lambda: self.status("if the power went out now: records 1 and 2 survive", GREEN_M), 0.5),
        ])
        self.steps("Record 3 is written, and not forced. It sits in the cache, dirty.", [
            (lambda: [*self.clock("t = 32 s"), *self.call("write(rec 3)"), GrowArrow(wa[2])], 0.5),
            (lambda: [dot_run(wa[2].get_start(), wa[2].get_end(), YELLOW_M, 0.5)], 0.6),
            (lambda: [*self.page(2, 3, "dirty"), *self.call("write(rec 3)", "returned at once")], 0.5),
            "dirty",
            (lambda: self.status("if the power went out now: record 3 is lost", RED_M), 0.5),
        ], after=0.4)

        # ---------------- scene 7: two accidents ----------------
        self.steps("Now, two different accidents. In one, the program crashes, killed on the spot. In the other, the power goes out. "
                   "Which one loses record 3? Pause and guess.", [
            (lambda: [*self.drop("status"), *self.cap("a crash, or a power cut: which one loses record 3?", WHITE)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Only the power cut. The dirty pages belong to the kernel, not the program. So after a crash, "
                   "the flusher still writes record 3 to the disk.", [
            (lambda: [*self.cap("a crash (kill -9): nothing lost", GREEN_M), pg.animate.set_stroke(RED_M), *self.call("(killed)", "", RED_M)], 0.7),
            "belong to the kernel",
            (lambda: [glow(pc, GOLD_M, 1.02)], 0.7),
            "the flusher still",
            (lambda: [self.van_trip(2), *self.page(2, 3, "clean"), *self.block(2, 3, "on disk")], 1.4),
        ])
        lost = [slot_state(PC, j, "lost", RED_M) for j in range(3)]
        self.steps("A power cut wipes RAM, and record 3 goes with it, although its write said success.", [
            (lambda: [*self.cap("a power cut: everything in RAM is gone", RED_M), pg.animate.set_stroke(TEAL_M),
                      *self.call("write(rec 3)", "returned at once"), *self.page(2, 3, "dirty"), *self.block(2, None, "nothing yet")], 0.7),
            "wipes RAM",
            (lambda: [FadeIn(dark)], 0.25),
            (lambda: [*[x for j in range(3) for x in self.put(f"ps{j}", lost[j])], *self.call("(gone)", "power cut", RED_M)], 0.5),
            (lambda: [FadeOut(dark)], 0.4),
            "although its write",
            (lambda: [Indicate(self.lab["bs2"], color=RED_M, scale_factor=1.2)], 0.7),
        ])
        self.steps("Here's where the post office picture breaks. A tray of letters survives a power cut. RAM doesn't.", [
            (lambda: [*self.cap("where the post office picture breaks: a tray survives a power cut; RAM doesn't", WHITE),
                      glow(pc, RED_M, 1.02)], 0.8),
        ], after=0.4)
        self.stamp("accidents")

        # ---------------- scene 8: the guardrail, and the opening ----------------
        self.steps("So is half a minute in RAM a problem? For most files, no. For a payment that was just approved, yes. "
                   "If you'll tell someone it's saved, call fsync first.", [
            (lambda: self.cap("half a minute in RAM: fine for most files", WHITE), 0.6),
            "For a payment",
            (lambda: [*self.cap("not fine for a payment you just approved", RED_M), Indicate(self.lab["bt1"], color=GREEN_M, scale_factor=1.1)], 0.6),
            "call fsync first",
            (lambda: self.cap("if you'll tell someone it's saved, call fsync first", YELLOW_M, 28), 0.6),
        ])
        self.steps("It costs milliseconds each time, and the next part of the lesson shows how to share that cost.", [
            (lambda: [Indicate(self.lab["bs1"], color=GREEN_M, scale_factor=1.2)], 0.7),
        ])
        self.steps("And the café's payment? It was approved two seconds before the power cut, still dirty in RAM. "
                   "One fsync before saying approved would have saved it.", [
            (lambda: [*self.cap("the café's payment: dirty in RAM, two seconds old", RED_M), Indicate(self.lab["ps2"], color=RED_M, scale_factor=1.2)], 0.7),
            "One fsync",
            (lambda: [*self.cap("one fsync before \"approved\" would have saved it", GREEN_M)], 0.6),
        ], after=0.4)

        # ---------------- scene 9: moral, and a check ----------------
        self.steps("So the moral of the story: write returns when the kernel has your bytes. fsync returns when the disk has them.", [
            (lambda: [*self.cap("write: the kernel has your bytes.   fsync: the disk has them.", YELLOW_M, 28), *self.clock("t = 40 s"),
                      *self.drop("call", "res"), *[x for j in range(3) for x in self.page(j, j + 1, "clean")],
                      *[x for j in range(3) for x in self.block(j, j + 1, "on disk")]], 0.8),
            "the kernel has",
            (lambda: [glow(pc, GOLD_M, 1.02)], 0.7),
            "the disk has",
            (lambda: [glow(dk, BLUE_M, 1.02)], 0.7),
        ])
        self.steps("One quick check. The program writes record 4 into page 0, and is killed a second later. The power stays on. "
                   "Is record 4 on the disk a minute later? Pause and think.", [
            (lambda: [*self.call("write(rec 4)"), dot_run(wa[0].get_start(), wa[0].get_end(), YELLOW_M, 0.5)], 0.6),
            (lambda: [*self.page(0, 4, "dirty"), *self.block(0, 1, "on disk"), *self.call("write(rec 4)", "returned at once")], 0.5),
            "is killed",
            (lambda: [pg.animate.set_stroke(RED_M), *self.call("(killed)", "", RED_M)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. The kernel still holds the dirty page, and the flusher writes it about 30 seconds after the write.", [
            (lambda: [*self.uncap(), glow(pc, GOLD_M, 1.02)], 0.6),
            "the flusher writes",
            (lambda: [*self.clock("t = 71 s"), self.van_trip(0), *self.page(0, 4, "clean"), *self.block(0, 4, "on disk")], 1.4),
        ], after=0.3)
        self.play(*self.cap("write: the kernel has your bytes.   fsync: the disk has them.", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
