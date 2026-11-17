from sfz import *

# Amounts are said the way people say them ("twenty-five"); captions keep "25.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bT([123])('s)?\b", lambda m: "T " + ["one", "two", "three"][int(m.group(1)) - 1] + (m.group(2) or "")))
SAY.insert(0, (r"\bLSNs?\b", lambda m: "L S N" + ("s" if m.group(0).endswith("s") else "")))
SAY.insert(0, (r"\b(BEGIN|COMMIT)\b", lambda m: m.group(1).lower()))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RW, RG = 1.22, 0.055                       # log records: width, gap
RX0 = -(10 * RW + 9 * RG) / 2              # left edge of the log strip
LOG_Y, LSN_Y, LOGT_Y = 2.62, 2.0, 3.32
PW = 2.4
PX = [-2.8 + k * (PW + 0.27) for k in range(4)]   # page boxes 1 to 4
MEM_Y, DISK_Y, PH = 0.62, -1.08, 1.1
LAB_X = -5.35
STAT_Y, BAR_Y, CAP_Y = -2.28, -2.78, -3.28

# the stepper's log: (kind, arg, LSN, transaction)
REC = [("BEGIN", "T1", 0, 1), ("UPD", "p1=700", 29, 1), ("UPD", "p2=300", 58, 1), ("COMMIT", "T1", 87, 1),
       ("BEGIN", "T2", 116, 2), ("UPD", "p2=250", 145, 2), ("UPD", "p3=50", 174, 2),
       ("BEGIN", "T3", 203, 3), ("UPD", "p4=42", 232, 3), ("COMMIT", "T3", 261, 3)]
TXC = {1: BLUE_M, 2: PURPLE_M, 3: TEAL_M}


def rx(i):
    return RX0 + RW / 2 + i * (RW + RG)


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


def page_frame(k, y):
    r = RoundedRectangle(corner_radius=0.12, width=PW, height=PH, stroke_color=GREY_B, stroke_width=2.5)
    return r.set_fill(fillc(GREY_B, 0.1), 1).move_to([PX[k], y, 0])


class WalRecovery(Base):
    """store-06, section 2. The café refund: the screen said Refunded, then the power failed, and only ~200 bytes of log
    were on disk. The whiteboard, the notebook by the door, and the photo. The lab's stepper: T1 moves 300 from page 1 to
    page 2 and commits (log forced to LSN 116); the background writer saves page 1; T2 starts (records in the buffer);
    T3 commits and its flush makes T2's records durable; the power fails. Where to start (the checkpoint and its redo
    point), redo with the page LSN (skip page 1, apply page 2), T2 dropped (the whiteboard picture breaks), T3 redone,
    the log's end. A second crash during recovery gives the same result: idempotent. Limits, the refund answered,
    the moral, and a check (page 3)."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
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

    def rec(self, i, durable):
        """Log record i: solid when it's on disk, dashed while it waits in the log buffer in memory."""
        kind, arg, lsn, tx = REC[i]
        c = TXC[tx]
        r = RoundedRectangle(corner_radius=0.08, width=RW, height=0.8, stroke_color=c, stroke_width=2.5)
        r.set_fill(fillc(c, 0.16 if durable else 0.05), 1).move_to([rx(i), LOG_Y, 0])
        frame = r if durable else VGroup(r.copy().set_stroke(opacity=0), DashedVMobject(r.copy().set_fill(opacity=0), num_dashes=24))
        g = VGroup(frame, M(kind, 15, c).move_to([rx(i), LOG_Y + 0.17, 0]), M(arg, 15, WHITE).move_to([rx(i), LOG_Y - 0.18, 0]),
                   T(str(lsn), 16, GREY_B).move_to([rx(i), LSN_Y, 0]))
        return self.put(("rec", i), g, DOWN)

    def page(self, row, k, val, lsn, note="", color=WHITE):
        y = MEM_Y if row == "mem" else DISK_Y
        line1 = M(f"page {k + 1} = {val}", 18, color).move_to([PX[k], y + 0.2, 0])
        s = f"LSN {lsn}" + (f", {note}" if note else "")
        nc = {"dirty": GOLD_M, "redone": GREEN_M, "skipped": GREY_B}.get(note, GREY_B)
        line2 = T(s, 17, nc).move_to([PX[k], y - 0.24, 0])
        return self.put((row, k), VGroup(line1, line2))

    def blank(self, row, k, s, color=GREY_B):
        y = MEM_Y if row == "mem" else DISK_Y
        return self.put((row, k), T(s, 17, color).move_to([PX[k], y, 0]))

    def durable(self, lsn, color=GREEN_M):
        return self.put("dur", right_at(T(f"on disk up to LSN {lsn}", 19, color), RX0 + 10 * RW + 9 * RG, LOGT_Y))

    def status(self, s, color=WHITE):
        return self.put("stat", fit(T(s, 22, color), 13.0).move_to([0, STAT_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def to_page(self, i, row, k, color=YELLOW_M, rt=0.6):
        """A dot from log record i down to page k of a row."""
        y = (MEM_Y if row == "mem" else DISK_Y) + PH / 2
        return dot_run([rx(i), LOG_Y - 0.42, 0], [PX[k], y, 0], color, rt)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Rebuilt from the log", "after a crash: replay from the last checkpoint")

        # ---------------- scene 1: the refund ----------------
        shop = VGroup(T("shop's balance", 22, GREY_B), M("-25.00", 34, GOLD_M)).arrange(DOWN, buff=0.22).move_to([-4.3, 1.0, 0])
        cust = VGroup(T("customer's balance", 22, GREY_B), M("+25.00", 34, GREEN_M)).arrange(DOWN, buff=0.22).move_to([4.3, 1.0, 0])
        btn = chip("Refunded", GREEN_M, 30).move_to([0, 2.15, 0])
        mv = Arrow(shop.get_right() + [0.2, 0, 0], cust.get_left() + [-0.2, 0, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.05)
        self.steps("Picture a café owner pressing Refund. The app takes 25.00 from her shop's balance, adds it to a customer's, "
                   "and the screen says Refunded.", [
            "The app takes",
            (lambda: [FadeIn(shop, shift=0.1 * RIGHT)], 0.6),
            "adds it to",
            (lambda: [GrowArrow(mv), FadeIn(cust, shift=0.1 * LEFT)], 0.7),
            "the screen says",
            (lambda: [FadeIn(btn, scale=0.8)], 0.5),
        ])
        dark = Rectangle(width=15, height=9, stroke_width=0).set_fill(BLACK, 0.92).set_z_index(20)
        disk = VGroup(RoundedRectangle(corner_radius=0.12, width=10.4, height=1.5, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1),
                      T("on disk at that moment:", 20, BLUE_M)).move_to([0, -1.6, 0])
        disk[1].move_to(disk[0].get_top() + 0.35 * DOWN)
        unchanged = T("both balances: unchanged        the log: about 200 bytes added at the end", 20, WHITE).move_to(disk[0].get_center() + 0.2 * DOWN)
        self.steps("A second later, the power fails. At that moment, neither balance had changed on disk. "
                   "The database had only added about 200 bytes to the end of one file, the log.", [
            "the power fails",
            (lambda: [FadeIn(dark)], 0.25),
            (lambda: [FadeOut(dark)], 0.45),
            "At that moment",
            (lambda: [FadeIn(disk, shift=0.1 * UP)], 0.6),
            "neither balance",
            (lambda: [FadeIn(unchanged)], 0.6),
        ])
        qm = T("?", 56, YELLOW_M).move_to([0, -0.15, 0])
        self.steps("So how does it rebuild both balances, and know what's already done?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "and know",
            (lambda: self.cap("how does it rebuild both, and know what's already done?", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 2: the back room ----------------
        logt = left_at(T("the notebook by the door", 22, WHITE), RX0, LOGT_Y)
        memf = [page_frame(k, MEM_Y) for k in range(4)]
        dskf = [page_frame(k, DISK_Y) for k in range(4)]
        self.steps("A café's back room has the same problem. The stock counts sit on a whiteboard, quick to rub out. "
                   "But before anyone changes a number, they write the change in a notebook by the door.", [
            (lambda: [FadeOut(VGroup(shop, cust, btn, mv, disk, unchanged, qm)), *self.uncap()], 0.7),
            "The stock counts",
            (lambda: [*self.put("lmem", T("the whiteboard", 22, WHITE).move_to([LAB_X, MEM_Y, 0])), *[FadeIn(f) for f in memf]], 0.7),
            "they write the change",
            (lambda: [FadeIn(logt), *self.rec(0, True)], 0.6),
            (lambda: [*self.rec(1, True)], 0.4),
            (lambda: [self.to_page(1, "mem", 0)], 0.7),
        ])
        self.steps("If the whiteboard gets wiped, the notebook can rebuild it.", [
            "gets wiped",
            (lambda: [*[f.animate.set_fill(fillc(RED_M, 0.3)) for f in memf]], 0.5),
            (lambda: [*[f.animate.set_fill(fillc(GREY_B, 0.1)) for f in memf]], 0.4),
            "the notebook can",
            (lambda: [self.to_page(0, "mem", 0, GREEN_M), self.to_page(1, "mem", 0, GREEN_M)], 0.8),
        ])
        photo = left_at(T("the last photo", 22, WHITE), LAB_X - 0.95, DISK_Y)
        self.steps("Nobody wants to replay a notebook from page one. So now and then, someone takes a photo of the whiteboard. "
                   "After a wipe, start from the last photo, and replay only the lines after it.", [
            "takes a photo",
            (lambda: [*[FadeIn(f) for f in dskf], FadeIn(photo)], 0.6),
            (lambda: [*[dot_run([PX[k], MEM_Y - PH / 2, 0], [PX[k], DISK_Y + PH / 2, 0], WHITE, 0.5) for k in range(4)]], 0.7),
            "start from the last",
            (lambda: [*[dot_run([PX[k], DISK_Y + PH / 2, 0], [PX[k], MEM_Y - PH / 2, 0], WHITE, 0.5) for k in range(4)]], 0.7),
            "replay only",
            (lambda: [self.to_page(1, "mem", 0, GREEN_M)], 0.7),
        ])
        self.steps("Map it: the whiteboard is the pages in memory, and the notebook is the log on disk.", [
            "the whiteboard is",
            (lambda: [*self.put("lmem", VGroup(T("pages in", 20, WHITE), T("memory", 20, WHITE)).arrange(DOWN, buff=0.1).move_to([LAB_X, MEM_Y, 0]))], 0.6),
            "the notebook is",
            (lambda: [Transform(logt, left_at(T("the log (LSN under each record)", 22, WHITE), RX0, LOGT_Y)), FadeOut(photo),
                      *self.put("ldsk", VGroup(T("pages on", 20, WHITE), T("disk", 20, WHITE)).arrange(DOWN, buff=0.1).move_to([LAB_X, DISK_Y, 0]))], 0.7),
        ], after=0.3)
        self.stamp("analogy")

        # ---------------- scene 3: the lab's model (stepper frames 1 to 4) ----------------
        self.steps("The lab's model has four pages, one number each. At the last photo, page 1 held 1,000.", [
            (lambda: self.drop(("rec", 0), ("rec", 1)), 0.4),
            "four pages",
            (lambda: [*[x for k in range(4) for x in self.page("mem", k, 1000 if k == 0 else 0, 0)],
                      *[x for k in range(4) for x in self.page("dsk", k, 1000 if k == 0 else 0, 0)]], 0.8),
            "page 1 held",
            (lambda: [Indicate(self.lab[("dsk", 0)], color=WHITE, scale_factor=1.08)], 0.7),
        ])
        self.steps("Transaction T1 moves 300 from page 1 to page 2. A transaction is a group of changes that must all happen, or none. "
                   "It writes four records to the log: BEGIN, two updates, and COMMIT.", [
            "It writes four",
            (lambda: [*self.rec(0, False)], 0.35),
            (lambda: [*self.rec(1, False)], 0.35),
            (lambda: [*self.rec(2, False)], 0.35),
            (lambda: [*self.rec(3, False)], 0.35),
        ])
        self.steps("Each record's place in the log, counted in bytes, is its LSN, its log sequence number. "
                   "COMMIT forces the log to disk up to LSN 116. The pages change in memory only, stamped 116.", [
            "counted in bytes",
            (lambda: [LaggedStart(*[Indicate(self.lab[("rec", i)][3], color=WHITE, scale_factor=1.3) for i in range(4)], lag_ratio=0.25)], 1.0),
            "COMMIT forces",
            (lambda: [*[x for i in range(4) for x in self.rec(i, True)], *self.durable(116)], 0.7),
            "The pages change",
            (lambda: [self.to_page(1, "mem", 0), self.to_page(2, "mem", 1)], 0.7),
            (lambda: [*self.page("mem", 0, 700, 116, "dirty"), *self.page("mem", 1, 300, 116, "dirty")], 0.5),
        ])
        self.steps("Later, the background writer, a process that saves changed pages, writes page 1 to disk, LSN and all. "
                   "Page 2 is still only in memory. That's fine: the log has all of T1.", [
            "writes page 1",
            (lambda: [dot_run([PX[0], MEM_Y - PH / 2, 0], [PX[0], DISK_Y + PH / 2, 0], GOLD_M, 0.6)], 0.7),
            (lambda: [*self.page("mem", 0, 700, 116, "clean"), *self.page("dsk", 0, 700, 116)], 0.5),
            "Page 2 is still",
            (lambda: [Indicate(self.lab[("mem", 1)], color=GOLD_M, scale_factor=1.08)], 0.7),
            "the log has all",
            (lambda: [LaggedStart(*[Indicate(self.lab[("rec", i)], color=BLUE_M, scale_factor=1.06) for i in range(4)], lag_ratio=0.2)], 0.9),
        ])
        self.steps("Then T2 starts moving 50 from page 2 to page 3, and T3 sets page 4 to 42 and commits. "
                   "T3's flush writes T2's records to disk too, because the log is one stream.", [
            (lambda: [*self.rec(4, False)], 0.3),
            (lambda: [*self.rec(5, False)], 0.3),
            (lambda: [*self.rec(6, False)], 0.3),
            "and T3",
            (lambda: [*self.rec(7, False)], 0.3),
            (lambda: [*self.rec(8, False)], 0.3),
            (lambda: [*self.rec(9, False), self.to_page(8, "mem", 3)], 0.5),
            (lambda: self.page("mem", 3, 42, 290, "dirty"), 0.4),
            "T3's flush",
            (lambda: [*[x for i in range(4, 10) for x in self.rec(i, True)], *self.durable(290)], 0.7),
            "T2's records",
            (lambda: [LaggedStart(*[Indicate(self.lab[("rec", i)], color=PURPLE_M, scale_factor=1.06) for i in (4, 5, 6)], lag_ratio=0.2)], 0.9),
        ], after=0.3)
        self.stamp("model")

        # ---------------- scene 4: the power fails ----------------
        self.steps("Then the power fails. Memory is gone. Left on disk: the log up to LSN 290, and pages that are partly up to date. "
                   "Page 1 lost its 300, and page 2 never got it.", [
            (lambda: [FadeIn(dark)], 0.25),
            (lambda: [*[x for k in range(4) for x in self.blank("mem", k, "gone", RED_M)]], 0.4),
            (lambda: [FadeOut(dark)], 0.4),
            "Left on disk",
            (lambda: [Indicate(self.lab["dur"], color=GREEN_M, scale_factor=1.1)], 0.7),
            "and pages that",
            (lambda: [*[Indicate(self.lab[("dsk", k)], color=WHITE, scale_factor=1.06) for k in range(4)]], 0.7),
            "Page 1 lost",
            (lambda: [Indicate(self.lab[("dsk", 0)], color=GOLD_M, scale_factor=1.08),
                      *self.status("on disk: 300 left page 1, and never reached page 2", RED_M)], 0.7),
            "page 2 never",
            (lambda: [Indicate(self.lab[("dsk", 1)], color=RED_M, scale_factor=1.08)], 0.7),
        ], after=0.4)

        # ---------------- scene 5: where to start ----------------
        self.steps("Where should recovery start? The log's first record would work, but that could take hours, "
                   "and the log could never be thrown away.", [
            (lambda: [*self.drop("stat"), *self.cap("start at the very first record of the log?", PURPLE_M)], 0.6),
            "could take hours",
            (lambda: self.cap("it works, but it could take hours, and the log must be kept forever", WHITE), 0.6),
        ])
        redo = VGroup(Line([RX0 - 0.03, LOG_Y + 0.55, 0], [RX0 - 0.03, LSN_Y - 0.1, 0], stroke_width=4, color=YELLOW_M),
                      T("redo point", 17, YELLOW_M).move_to([RX0 + 0.62, LSN_Y - 0.3, 0]))
        self.steps("That's the photo. A checkpoint writes every changed page to disk, forces it there, and then logs a redo point, "
                   "where recovery may start. PostgreSQL, a free database program, takes one every 5 minutes, "
                   "or after about a gigabyte of log.", [
            "A checkpoint",
            (lambda: [*self.cap("checkpoint: write every changed page, force it to disk, then log the redo point", WHITE)], 0.6),
            "logs a redo point",
            (lambda: [Create(redo[0]), FadeIn(redo[1])], 0.6),
            (lambda: [glow(dskf[0], WHITE, 1.03)], 0.7),
            "PostgreSQL",
            (lambda: self.cap("PostgreSQL: every 5 minutes, or after about 1 GB of log", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 6: redo with the page LSN ----------------
        self.steps("Recovery reads the log from the redo point. At T1's COMMIT, it redoes T1's changes, "
                   "but only where a page is missing them. How can it tell?", [
            (lambda: [*self.uncap(), *self.put("lmem", VGroup(T("pages in", 20, WHITE), T("memory, rebuilt", 20, WHITE)).arrange(DOWN, buff=0.1).move_to([LAB_X, MEM_Y, 0])),
                      *[x for k in range(4) for x in self.page("mem", k, *((700, 116) if k == 0 else (0, 0)))]], 0.7),
            "At T1's COMMIT",
            (lambda: [*[glow(self.lab[("rec", i)][0], BLUE_M, 1.06) for i in range(4)]], 0.8),
            "How can it tell",
            (lambda: self.cap("does the page already have this change?", YELLOW_M), 0.5),
        ])
        self.steps("Page 1 on disk says LSN 116, so it already has every change up to 116: skip. "
                   "Page 2 says LSN 0: apply the 300, and stamp 116.", [
            (lambda: [*self.uncap(), *self.status("T1's COMMIT ends at LSN 116", BLUE_M)], 0.5),
            "Page 1 on disk",
            (lambda: [Indicate(self.lab[("mem", 0)], color=WHITE, scale_factor=1.08)], 0.6),
            ": skip",
            (lambda: [*self.page("mem", 0, 700, 116, "skipped"), *self.status("page 1: LSN 116, not below 116: skip", GREY_B)], 0.6),
            "Page 2 says",
            (lambda: [Indicate(self.lab[("mem", 1)], color=WHITE, scale_factor=1.08)], 0.5),
            "apply the 300",
            (lambda: [self.to_page(2, "mem", 1, GREEN_M), *self.status("page 2: LSN 0, below 116: apply 300", GREEN_M)], 0.7),
            (lambda: self.page("mem", 1, 300, 116, "redone", GREEN_M), 0.5),
        ])
        self.steps("That stamp is the page LSN. On the whiteboard, it's the notebook line number written next to each count.", [
            "the page LSN",
            (lambda: [*self.cap("page LSN: the position just past the last record that changed the page", WHITE),
                      Indicate(self.lab[("mem", 1)][1], color=GREEN_M, scale_factor=1.15)], 0.7),
            "line number",
            (lambda: [Indicate(self.lab[("rec", 3)][3], color=WHITE, scale_factor=1.3)], 0.7),
        ], after=0.3)
        self.stamp("redo")

        # ---------------- scene 7: the unfinished transaction ----------------
        self.steps("Next come T2's records. They're on disk, written by T3's commit. Does recovery apply them? Pause and guess.", [
            (lambda: [*self.uncap(), *self.drop("stat")], 0.4),
            "Next come",
            (lambda: [*[glow(self.lab[("rec", i)][0], PURPLE_M, 1.06) for i in (4, 5, 6)]], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        xs = VGroup(*[tick(False, 0.14).move_to([rx(i), LOG_Y + 0.64, 0]) for i in (4, 5, 6)]).set_z_index(5)
        self.steps("No. T2 has no COMMIT, so recovery drops its records. Here the whiteboard picture breaks. "
                   "Every line in the café's notebook counts. A database log also holds changes that never finished.", [
            (lambda: [*self.uncap(), *self.status("T2: no COMMIT in the log, so its records are dropped", PURPLE_M)], 0.6),
            (lambda: [Create(xs), *[self.lab[("rec", i)].animate.set_opacity(0.35) for i in (4, 5, 6)]], 0.6),
            "Here the whiteboard",
            (lambda: self.cap("where the whiteboard picture breaks: a log also holds changes that never finished", WHITE), 0.6),
        ])
        endm = DashedLine([RX0 + 10 * RW + 9 * RG + 0.06, LOG_Y + 0.4, 0], [RX0 + 10 * RW + 9 * RG + 0.06, LOG_Y - 0.4, 0],
                          dash_length=0.06, stroke_width=3, color=RED_M)
        self.steps("At T3's COMMIT, page 4 says LSN 0, below 290, so 42 goes in. After 290, the next record doesn't check out. "
                   "That's the end of the log.", [
            (lambda: [*self.uncap(), *self.status("T3's COMMIT ends at LSN 290", TEAL_M)], 0.5),
            "page 4 says",
            (lambda: [self.to_page(8, "mem", 3, GREEN_M), *self.status("page 4: LSN 0, below 290: apply 42", GREEN_M)], 0.7),
            (lambda: self.page("mem", 3, 42, 290, "redone", GREEN_M), 0.5),
            "After 290",
            (lambda: [Create(endm)], 0.4),
            "the end of the log",
            (lambda: self.status("every committed change is back; T2 left no trace", GREEN_M), 0.6),
        ], after=0.3)
        self.stamp("dropped")

        # ---------------- scene 8: crash again ----------------
        self.steps("Now the nasty case. The power fails again, halfway through recovery. What does the next recovery do? Pause and guess.", [
            (lambda: self.drop("stat"), 0.3),
            "fails again",
            (lambda: [FadeIn(dark)], 0.25),
            (lambda: [*[x for k in range(4) for x in self.blank("mem", k, "gone", RED_M)]], 0.4),
            (lambda: [FadeOut(dark)], 0.4),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Exactly the same work, with the same result. Doing it twice gives the same as doing it once. "
                   "That's called idempotent. Pull the plug on recovery as often as you like; it never holds a grudge.", [
            (lambda: [*self.uncap(), *[x for k in range(4) for x in self.page("mem", k, *((700, 116) if k == 0 else (0, 0)))]], 0.6),
            (lambda: [self.to_page(2, "mem", 1, GREEN_M), self.to_page(8, "mem", 3, GREEN_M)], 0.7),
            (lambda: [*self.page("mem", 1, 300, 116, "redone", GREEN_M), *self.page("mem", 3, 42, 290, "redone", GREEN_M),
                      *self.page("mem", 0, 700, 116, "skipped")], 0.5),
            "Doing it twice",
            (lambda: self.status("same log, same checks, same pages", GREEN_M), 0.5),
            "That's called idempotent",
            (lambda: self.cap("idempotent: doing it twice gives the same result as doing it once", WHITE), 0.6),
            "never holds a grudge",
            (lambda: [*[Indicate(self.lab[("mem", k)], color=GREEN_M, scale_factor=1.06) for k in (1, 3)]], 0.8),
        ], after=0.3)
        self.stamp("again")

        # ---------------- scene 9: a limit ----------------
        self.steps("One limit of the lab: it never lets unfinished changes into pages. Real engines can, so they add a step that "
                   "undoes them. PostgreSQL has none: a transaction with no commit record counts as cancelled, and stays invisible.", [
            (lambda: [*self.drop("stat"), *self.cap("the lab keeps unfinished changes out of pages; real engines add an undo step", WHITE)], 0.6),
            "PostgreSQL has none",
            (lambda: self.cap("PostgreSQL: no COMMIT means cancelled, and its changes stay invisible", WHITE), 0.6),
            "stays invisible",
            (lambda: [*[Indicate(self.lab[("rec", i)], color=PURPLE_M, scale_factor=1.06) for i in (4, 5, 6)]], 0.7),
        ], after=0.3)

        # ---------------- scene 10: the refund, the moral, and a check ----------------
        self.steps("So, the refund was safe all along. About 200 bytes of log, forced at commit, held everything needed "
                   "to rebuild both balances, and the page LSNs told recovery what was already there.", [
            (lambda: self.cap("the refund: about 200 bytes of log, forced at commit, was enough", WHITE), 0.6),
            "held everything",
            (lambda: [*[glow(self.lab[("rec", i)][0], BLUE_M, 1.06) for i in range(4)]], 0.8),
            "the page LSNs",
            (lambda: [*[Indicate(self.lab[("mem", k)][1], color=WHITE, scale_factor=1.15) for k in range(4)]], 0.8),
        ])
        self.steps("The moral of the story: start at the last checkpoint, redo what a page is missing, skip what it has, "
                   "and drop what never committed.", [
            (lambda: self.cap("start at the checkpoint, redo what a page is missing, skip what it has", YELLOW_M, 26), 0.6),
            "drop what never",
            (lambda: [Indicate(xs, color=RED_M, scale_factor=1.2)], 0.7),
        ], after=0.4)
        self.steps("One quick check. T2 also wanted to put 50 into page 3. After recovery, what does page 3 hold? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "T2 also wanted",
            (lambda: [Indicate(self.lab[("rec", 6)], color=PURPLE_M, scale_factor=1.1)], 0.7),
            "what does page 3",
            (lambda: [*self.put(("mem", 2), T("page 3 = ?", 20, YELLOW_M).move_to([PX[2], MEM_Y, 0]))], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Zero. T2 never committed, so its change was dropped, and page 3 is as the checkpoint left it.", [
            (lambda: [*self.uncap(), *self.page("mem", 2, 0, 0)], 0.6),
            "was dropped",
            (lambda: [Indicate(xs[2], color=RED_M, scale_factor=1.3)], 0.6),
            "as the checkpoint",
            (lambda: [Indicate(self.lab[("dsk", 2)], color=WHITE, scale_factor=1.08)], 0.7),
        ], after=0.3)
        self.play(*self.cap("start at the checkpoint, redo what a page is missing, skip what it has", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
