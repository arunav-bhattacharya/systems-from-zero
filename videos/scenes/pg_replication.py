from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz"; spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bpg_basebackup\b", "P G base backup"))
SAY.insert(0, (r"\bpg_stat_replication\b", "P G stat replication"))
SAY.insert(0, (r"\bstandby\.signal\b", "standby dot signal"))
SAY.insert(0, (r"\bwalsender\b", "wall sender"))
SAY.insert(0, (r"\bwalreceiver\b", "wall receiver"))
SAY.insert(0, (r"\bmax_slot_wal_keep_size\b", "max slot wall keep size"))
SAY.insert(0, (r"\bLSN\b", "L S N"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BW, BH = 5.0, 2.9
PR_C = np.array([-3.8, 1.45, 0])         # the primary
ST_C = np.array([3.8, 1.45, 0])          # the standby
TOP = PR_C[1] + BH / 2
TITLE_Y, TAPE_Y, MARK_Y, DATA_Y = TOP - 0.32, PR_C[1] + 0.4, PR_C[1] - 0.05, PR_C[1] - 0.85
NCELL, PITCH = 7, 0.6
PROC_Y = -0.42
WORK_Y = -1.45
CAP_Y, BAR_Y = -3.25, -2.8


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0]))

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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
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


def dot_run(a, b, color=YELLOW_M, rt=0.6, frac=1.0):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.09, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.12))


def run(ar, color=YELLOW_M, rt=0.6):
    return dot_run(ar.get_start(), ar.get_end(), color, rt)



def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def mbody(c, color, w=BW, h=BH, dashed=False):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return r


def cx(c, i):
    return c[0] - PITCH * (NCELL - 1) / 2 + PITCH * i


def wcell(c, i, color=BLUE_M, label=None):
    sq = RoundedRectangle(corner_radius=0.05, width=0.5, height=0.5, stroke_color=color, stroke_width=2.5)
    sq.set_fill(fillc(color, 0.45), 1).move_to([cx(c, i), TAPE_Y, 0])
    return VGroup(sq, M(label or str(i + 1), 18).move_to(sq))


def pages(c, color):
    x0 = c[0] - BW / 2 + 0.45
    sqs = VGroup(*[Square(0.36, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.3), 1).move_to([x0 + 0.48 * k + 0.18, DATA_Y, 0])
                   for k in range(3)])
    lab = T("pages", 18, GREY_B).next_to(sqs, RIGHT, buff=0.2)
    return VGroup(sqs, lab)


def marker(c, i, color, dx=0.0):
    x = cx(c, i) + dx
    return Triangle(stroke_width=0).set_fill(color, 1).scale(0.11).move_to([x, MARK_Y, 0])


class PgReplication(Base):
    """repl-04, section 0. How do you copy a database that never stops changing? Pages and the write-ahead log; crash
    recovery replays the WAL after a checkpoint. A copy whose recovery never ends, fed the primary's WAL, is a standby
    (the café notebook with a photocopy in another town, read out over the phone). pg_basebackup, standby.signal,
    walsender, walreceiver, startup. LSNs and three positions; the paused-replay test (count 7 while the WAL is on its
    disk, 196,512 bytes behind; 1,007 at once on resume). A stopped standby finds its WAL removed; the replication
    slot; a slot needs a limit (max_slot_wal_keep_size, idle_replication_slot_timeout). The moral, the loop paid off
    (it copies mistakes too: backups), and a check."""

    def count(self, who, n):
        c = PR_C if who == "p" else ST_C
        m = T(f"refunds: {n}", 20).move_to([c[0] + BW / 2 - 0.3, DATA_Y, 0])
        m.shift((c[0] + BW / 2 - 0.3 - m.get_right()[0]) * RIGHT)
        return self.put("cnt" + who, m)

    def pcell(self, i, color=BLUE_M):
        return self.put(f"p{i}", wcell(PR_C, i, color, str(i + 1 + self.off)))

    def scell(self, i, color=TEAL_M):
        return self.put(f"s{i}", wcell(ST_C, i, color, str(i + 1 + self.off)))

    def burst(self, net, n=4, color=YELLOW_M):
        return [LaggedStart(*[dot_run(net.get_start(), net.get_end(), color, 0.5) for _ in range(n)], lag_ratio=0.3)]

    def flushed(self, i):
        return self.put("mf", marker(ST_C, i, GREEN_M, -0.12), RIGHT)

    def replayed(self, i):
        return self.put("mr", marker(ST_C, i, YELLOW_M, 0.12), RIGHT)

    def work(self, mob, y=WORK_Y):
        return self.put("work", mob.move_to([0, y, 0]))

    def apply(self, c, i, pg, color=YELLOW_M):
        """A note on the tape is applied to a page."""
        sq = pg[0][i % 3]
        return [dot_run([cx(c, i), TAPE_Y - 0.28, 0], sq.get_top() + 0.05 * UP, color, 0.5)]

    def construct(self):
        self.lab = {}
        self.off = 0
        self.title_card("A copy that never stops recovering", "how a PostgreSQL standby follows its primary")

        # ---------------- scene 1: the question ----------------
        pr = mbody(PR_C, BLUE_M)
        pr_t = T("primary", 26).move_to([PR_C[0], TITLE_Y, 0])
        pg_p = pages(PR_C, BLUE_M)
        self.steps("Picture a payments company at night. One computer, the primary, keeps every card payment. If its disk dies, payments stop.", [
            "One computer",
            (lambda: [FadeIn(pr), FadeIn(pr_t), FadeIn(pg_p), *self.count("p", 7)], 0.8),
            "If its disk",
            (lambda: [pr.animate.set_stroke(RED_M), *self.cap("disk failed: no payments", RED_M)], 0.5),
            (lambda: [pr.animate.set_stroke(BLUE_M)], 0.5),
        ])
        ghost = DashedVMobject(mbody(ST_C, GREY_D).set_fill(opacity=0).set_stroke(GREY_C, 2), num_dashes=70)
        qm = T("?", 60, YELLOW_M).move_to(ST_C)
        self.steps("So we want a second computer with a copy, a few milliseconds behind, while the first keeps working. "
                   "How do you copy a database that never stops changing?", [
            (lambda: [*self.drop("cap"), Create(ghost)], 0.8),
            "How do you",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
        ])
        self.steps("And a darker question: if someone deletes the wrong rows, does the copy save you? Hold that one.", [
            "deletes the wrong",
            (lambda: self.cap("someone deletes the wrong rows: does the copy save you?", WHITE), 0.6),
        ])

        # ---------------- scene 2: the log, and crash recovery ----------------
        wal_l = left_at(T("WAL", 20, GREY_B), PR_C[0] - BW / 2 + 0.25, TITLE_Y)
        self.steps("PostgreSQL, a free database program, keeps its data in files cut into 8 KB pages.", [
            (lambda: [*self.drop("cap"), FadeOut(qm), FadeOut(ghost)], 0.5),
            "8 KB pages",
            (lambda: [*self.cap("data files, cut into 8 KB pages"), LaggedStart(*[Indicate(s, color=BLUE_M) for s in pg_p[0]], lag_ratio=0.3)], 1.0),
        ])

        def note(i):
            return [(lambda: [*self.pcell(i)], 0.35), (lambda: self.apply(PR_C, i, pg_p, BLUE_M), 0.5)]

        self.steps("Before it changes a page, it adds a note of the change to the end of a log file, the write-ahead log, or WAL. "
                   "It only ever adds to the end.", [
            "adds a note",
            (lambda: [FadeIn(wal_l), *self.cap("first a note in the log, then the page")], 0.5),
            *note(0),
            "the write-ahead",
            *note(1),
            "It only ever",
            *note(2),
            *note(3),
        ])
        ckx = (cx(PR_C, 1) + cx(PR_C, 2)) / 2
        ck = DashedLine([ckx, TAPE_Y + 0.4, 0], [ckx, TAPE_Y - 0.4, 0], dash_length=0.07, stroke_width=2.5, color=WHITE)
        ck_t = T("checkpoint", 16, GREY_B).move_to([ckx, MARK_Y - 0.05, 0])
        cur = SurroundingRectangle(self.lab["p2"], buff=0.06, color=YELLOW_M, stroke_width=4, corner_radius=0.06)
        self.steps("If the server crashes, it goes back to the last checkpoint, a moment when every change so far had reached the data files.", [
            (lambda: [pr.animate.set_stroke(RED_M), *self.cap("crash", RED_M), *[s.animate.set_fill(fillc(RED_M, 0.3)) for s in pg_p[0]]], 0.5),
            "the last checkpoint",
            (lambda: [Create(ck), FadeIn(ck_t), *self.cap("checkpoint: every change before it is in the data files")], 0.7),
        ])
        self.steps("Then it replays each note written after it. That's crash recovery.", [
            (lambda: [Create(cur)], 0.4),
            (lambda: self.apply(PR_C, 2, pg_p), 0.5),
            (lambda: [cur.animate.move_to(self.lab["p3"])], 0.35),
            (lambda: self.apply(PR_C, 3, pg_p), 0.5),
            "That's crash",
            (lambda: [FadeOut(cur), pr.animate.set_stroke(BLUE_M), *[s.animate.set_fill(fillc(BLUE_M, 0.3)) for s in pg_p[0]],
                      *self.cap("crash recovery: replay the notes after the checkpoint", WHITE)], 0.6),
        ])

        # ---------------- scene 3: recovery that never ends ----------------
        st = mbody(ST_C, TEAL_M)
        st_t = T("standby", 26).move_to([ST_C[0], TITLE_Y, 0])
        pg_s = pages(ST_C, TEAL_M)
        net = Arrow([PR_C[0] + BW / 2 + 0.1, TAPE_Y, 0], [ST_C[0] - BW / 2 - 0.1, TAPE_Y, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.12)
        net_t = T("network", 18, GREY_B).next_to(net, UP, buff=0.12)
        pw_l = left_at(T("pg_wal", 20, GREY_B), ST_C[0] - BW / 2 + 0.25, TITLE_Y)

        def stream(i, color=TEAL_M, rt=0.55):
            return [(lambda: [dot_run(net.get_start(), net.get_end(), YELLOW_M, rt)], rt), (lambda: self.scell(i, color), 0.3)]

        self.steps("Now here's the trick. Take a copy of the data folder, and never let its recovery end.", [
            (lambda: [*self.drop("cap"), FadeOut(ck), FadeOut(ck_t)], 0.4),
            "Take a copy",
            (lambda: [FadeIn(st), FadeIn(st_t), FadeIn(pg_s), *self.count("s", 7),
                      *[self.scell(i)[0] for i in range(4)]], 1.0),
            "never let",
            (lambda: [*self.cap("recovery that never ends", YELLOW_M), FadeIn(pw_l)], 0.5),
        ])
        rcur = SurroundingRectangle(self.lab["s3"], buff=0.06, color=YELLOW_M, stroke_width=4, corner_radius=0.06)
        self.steps("Keep feeding it the primary's WAL as it's written, and the copy replays each note onto the same pages. That copy is a standby.", [
            (lambda: [GrowArrow(net), FadeIn(net_t)], 0.5),
            "Keep feeding",
            (lambda: [*self.pcell(4)], 0.35),
            *stream(4),
            "the copy replays",
            (lambda: [Create(rcur.move_to(self.lab["s4"]))], 0.3),
            (lambda: self.apply(ST_C, 4, pg_s), 0.5),
            "That copy is",
            (lambda: [FadeOut(rcur), *self.cap("standby: a copy that keeps replaying the primary's WAL", WHITE)], 0.5),
        ])
        self.steps("It's recovering from a crash that never ends, and that's the whole point.", [
            (lambda: [glow(st, TEAL_M, 1.02)], 0.9),
        ])
        mapping = VGroup(T("the café's notebook  =  the WAL", 24), T("the phone line  =  the network", 24),
                         T("the photocopy in another town  =  the standby", 24)).arrange(DOWN, buff=0.22)
        self.steps("Picture the café's notebook, with a photocopy in another town. Each new line is read out over the phone and written into the copy.", [
            (lambda: [*self.drop("cap"), *self.work(T("a notebook, a phone line, a photocopy in another town", 24, GREY_B), WORK_Y - 0.3)], 0.5),
            "Each new line",
            (lambda: [*self.pcell(5)], 0.35),
            *stream(5, rt=0.8),
        ])
        self.steps("The notebook is the WAL, the phone line is the network, and the copy is the standby.", [
            (lambda: [*self.drop("work"), FadeIn(mapping[0].move_to([0, WORK_Y + 0.3, 0])), glow(VGroup(*[self.lab[f"p{i}"][0] for i in range(6)]), BLUE_M, 1.0)], 0.6),
            "the phone line",
            (lambda: [FadeIn(mapping[1].move_to([0, WORK_Y - 0.3, 0])), Indicate(net_t, color=WHITE)], 0.6),
            "the copy is",
            (lambda: [FadeIn(mapping[2].move_to([0, WORK_Y - 0.9, 0])), glow(st, TEAL_M, 1.02)], 0.6),
        ])
        self.steps("And it's a copy byte for byte: the same pages, the same row positions, the same major version, the 18 in 18.1.", [
            (lambda: [FadeOut(mapping)], 0.4),
            "byte for byte",
            (lambda: [*self.cap("byte for byte: same pages, same row positions, same major version (the 18 in 18.1)", WHITE),
                      *[Indicate(VGroup(a, b), color=WHITE) for a, b in zip(pg_p[0], pg_s[0])]], 0.9),
        ])

        # ---------------- scene 4: building one ----------------
        cmd = chip("pg_basebackup -X stream -R", GOLD_M, 24, mono=True)
        self.steps("One command builds it: pg_basebackup. It copies the running primary's data folder over the network, "
                   "plus the WAL written while it copies.", [
            (lambda: [*self.drop("cap"), *self.work(cmd)], 0.5),
            "It copies",
            (lambda: [*self.burst(net, 4, BLUE_M), glow(pg_s[0], TEAL_M, 1.05), *self.cap("copies the data folder while the primary keeps running")], 1.4),
            "plus the WAL",
            (lambda: [*self.burst(net, 4), glow(VGroup(*[self.lab[f"s{i}"][0] for i in range(6)]), TEAL_M, 1.0)], 1.4),
        ])
        sig = chip("standby.signal", TEAL_M, 20, mono=True).move_to([ST_C[0], DATA_Y, 0])
        sig.move_to([ST_C[0] + 0.3, DATA_Y - 0.0, 0])
        self.steps("Its dash R option leaves a small empty file, standby.signal, which says: start as a standby, and stay in recovery.", [
            "small empty file",
            (lambda: [*self.work(T("-R  writes  standby.signal: start as a standby, stay in recovery", 24, TEAL_M))], 0.6),
            "start as a standby",
            (lambda: [glow(st, TEAL_M, 1.02), *self.drop("cap")], 0.8),
        ])
        ws = chip("walsender", BLUE_M, 20, mono=True).move_to([PR_C[0] + BW / 2 - 1.1, PROC_Y, 0])
        wr = chip("walreceiver", TEAL_M, 20, mono=True).move_to([ST_C[0] - BW / 2 + 1.2, PROC_Y, 0])
        su = chip("startup", YELLOW_M, 20, mono=True).move_to([ST_C[0] + BW / 2 - 0.85, PROC_Y, 0])
        self.steps("Then two processes, running programs, hold the phone line: the walsender on the primary and the walreceiver on the standby.", [
            (lambda: self.drop("work"), 0.3),
            "the walsender",
            (lambda: [FadeIn(ws, shift=0.1 * UP)], 0.5),
            "the walreceiver",
            (lambda: [FadeIn(wr, shift=0.1 * UP)], 0.5),
        ])
        self.steps("The walreceiver writes the WAL into the standby's own folder and forces it onto the disk. Then the startup process replays it.", [
            (lambda: [*self.pcell(6)], 0.35),
            (lambda: [dot_run(net.get_start(), net.get_end(), YELLOW_M, 0.6)], 0.6),
            "writes the WAL",
            (lambda: [*self.scell(6), Indicate(wr, color=TEAL_M)], 0.5),
            "forces it",
            (lambda: [*self.flushed(6), *self.cap("on the standby's disk", GREEN_M)], 0.5),
            "Then the startup",
            (lambda: [FadeIn(su, shift=0.1 * UP), *self.replayed(5)], 0.5),
            (lambda: [*self.replayed(6), *self.apply(ST_C, 6, pg_s), *self.cap("replayed: what queries on the standby can see", YELLOW_M)], 0.6),
        ])

        # ---------------- scene 5: three positions, and a test ----------------
        lsn = VGroup(T("LSN: a count of bytes from the start of the log", 24), M("0/508F830", 24, GREY_B)).arrange(RIGHT, buff=0.5)
        self.steps("A place in the WAL is an LSN, a log sequence number: a count of bytes from the start of the log.", [
            (lambda: [*self.drop("cap"), *self.work(lsn)], 0.6),
        ])
        legend = VGroup(
            VGroup(marker(ST_C, 0, GREEN_M).move_to(ORIGIN), T("written, flushed to disk", 22, GREEN_M)).arrange(RIGHT, buff=0.2),
            VGroup(marker(ST_C, 0, YELLOW_M).move_to(ORIGIN), T("replayed: what queries see", 22, YELLOW_M)).arrange(RIGHT, buff=0.2),
        ).arrange(RIGHT, buff=0.8)
        self.steps("The primary's report, pg_stat_replication, shows three of them for each standby: written, flushed to disk, and replayed. "
                   "Only replayed is what queries on the standby see.", [
            "pg_stat_replication",
            (lambda: self.work(VGroup(M("pg_stat_replication", 22, BLUE_M), T("on the primary, one row per standby", 22, GREY_B)).arrange(RIGHT, buff=0.4)), 0.6),
            "written",
            (lambda: [*self.work(legend), Indicate(self.lab["mf"], color=GREEN_M, scale_factor=1.6)], 0.6),
            "Only replayed",
            (lambda: [Indicate(self.lab["mr"], color=YELLOW_M, scale_factor=1.6)], 0.7),
        ])
        # shift the tapes left so three new cells fit: drop cells 0-2 on both (the picture keeps the last four)
        def compact():
            out = []
            for side, c, col in (("p", PR_C, BLUE_M), ("s", ST_C, TEAL_M)):
                for i in range(3):
                    out += self.drop(f"{side}{i}")
                for i in range(3, 7):
                    m = self.lab.pop(f"{side}{i}")
                    self.lab[f"{side}{i - 3}"] = m
                    out.append(m.animate.shift(3 * PITCH * LEFT))
            out += [self.lab["mf"].animate.shift(3 * PITCH * LEFT), self.lab["mr"].animate.shift(3 * PITCH * LEFT)]
            self.off = 3
            return out

        self.steps("Let's test it. Pause replay on the standby, and insert 1,000 refunds on the primary.", [
            (lambda: [*self.drop("work"), *compact()], 0.8),
            "Pause replay",
            (lambda: [*self.put("su", chip("startup: paused", RED_M, 20, mono=True).move_to(su)), FadeOut(su)], 0.5),
            "insert 1,000",
            (lambda: [*[self.pcell(i, GOLD_M)[0] for i in range(4, 7)], *self.count("p", "1,007")], 0.7),
        ])

        def arrive():
            return [LaggedStart(*[dot_run(net.get_start(), net.get_end(), GOLD_M, 0.5) for _ in range(3)], lag_ratio=0.3)]

        self.steps("Has the WAL reached the standby? And what will a count of refunds there say? Pause and guess.", [
            (lambda: [*self.cap("has the WAL arrived? what does the count say?", WHITE)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        table = VGroup(*[VGroup(T(a, 22, col), M(b, 22, col)).arrange(RIGHT, buff=0.3) for a, b, col in
                         [("written", "0/5111380", GREEN_M), ("flushed", "0/5111380", GREEN_M), ("replayed", "0/50E13E0", YELLOW_M)]])
        table.arrange(RIGHT, buff=0.6)
        behind = T("196,512 bytes behind, about 192 KB", 22, RED_M)
        self.steps("The WAL arrived. Write and flush lag were 2 and 7 milliseconds.", [
            (lambda: [*self.drop("cap"), *arrive()], 1.0),
            (lambda: [*[self.scell(i, GOLD_M)[0] for i in range(4, 7)], *self.flushed(6)], 0.5),
            "Write and flush",
            (lambda: [*self.work(table, WORK_Y + 0.25), *self.cap("write lag 2 ms, flush lag 7 ms", GREEN_M)], 0.6),
        ])
        self.steps("But replay is 196,512 bytes behind, about 192 KB, and the count still says 7.", [
            "196,512",
            (lambda: [*self.put("behind", behind.move_to([0, WORK_Y - 0.4, 0])), Indicate(self.lab["mr"], color=YELLOW_M, scale_factor=1.6)], 0.6),
            "the count still",
            (lambda: [*self.drop("cap"), Indicate(self.lab["cnts"], color=WHITE, scale_factor=1.2)], 0.7),
        ])
        self.steps("Resume replay, and the count is 1,007 at once, because the WAL was already on its disk.", [
            (lambda: [*self.put("su", chip("startup", YELLOW_M, 20, mono=True).move_to(su)), *self.drop("behind")], 0.4),
            (lambda: self.replayed(4), 0.25),
            (lambda: self.replayed(5), 0.25),
            (lambda: [*self.replayed(6), *self.count("s", "1,007")], 0.4),
            "already on its disk",
            (lambda: [Indicate(self.lab["mf"], color=GREEN_M, scale_factor=1.6), *self.cap("the bytes were already on its disk", GREEN_M)], 0.7),
        ])

        # ---------------- scene 6: when the standby stops ----------------
        stopped = T("stopped", 22, RED_M).move_to([ST_C[0], DATA_Y + 0.45, 0])
        self.steps("Now stop the standby for a while. At each checkpoint, the primary deletes old WAL files, called segments, "
                   "once its own crash recovery no longer needs them.", [
            (lambda: [*self.drop("work", "cap"), st.animate.set_stroke(GREY_D), FadeIn(stopped)], 0.6),
            "At each checkpoint",
            (lambda: [*self.cap("checkpoint: old WAL files (segments) are deleted")], 0.5),
            "deletes old",
            (lambda: [*[self.lab[f"p{i}"].animate.set_opacity(0.15) for i in range(3)]], 0.6),
        ])
        err = M("requested WAL segment ... has already been removed", 22, RED_M)
        self.steps("It doesn't ask the standby. When the standby comes back, it gets: requested WAL segment has already been removed. "
                   "It must be built again from a fresh copy.", [
            "When the standby",
            (lambda: [st.animate.set_stroke(TEAL_M), FadeOut(stopped)], 0.5),
            (lambda: [dot_run(net.get_end(), net.get_start(), TEAL_M, 0.6)], 0.6),
            "requested",
            (lambda: [*self.work(fit(err, 12.5))], 0.6),
            "built again",
            (lambda: [*self.cap("rebuild it from a fresh copy", RED_M)], 0.5),
        ])
        slot = chip("slot: oldest WAL needed", GOLD_M, 18).move_to([PR_C[0] - 1.35, PROC_Y, 0])
        flag = Triangle(stroke_width=0).set_fill(GOLD_M, 1).scale(0.11).move_to([cx(PR_C, 1), TAPE_Y - 0.4, 0])
        self.steps("The fix is a replication slot, a note on the primary of the oldest WAL this standby still needs.", [
            (lambda: [*self.drop("work", "cap"), *[self.lab[f"p{i}"].animate.set_opacity(1) for i in range(3)]], 0.5),
            "replication slot",
            (lambda: [FadeIn(flag), FadeIn(slot, shift=0.1 * UP)], 0.6),
            "oldest WAL",
            (lambda: [Indicate(self.lab["p1"], color=GOLD_M)], 0.6),
        ])
        self.steps("In the café, it's a note by the notebook: keep every page from line 5, the other town still needs them.", [
            (lambda: [*self.cap("a note by the notebook: keep every page from here on", GOLD_M)], 0.5),
            "keep every page",
            (lambda: [self.lab["p0"].animate.set_opacity(0.15), *[glow(self.lab[f"p{i}"][0], GOLD_M, 1.1) for i in range(1, 7)]], 0.9),
        ])

        # ---------------- scene 7: a slot needs a limit ----------------
        disk_x0, disk_w, disk_y = -6.0, 4.6, -1.75
        disk = Rectangle(width=disk_w, height=0.4, stroke_color=GREY_B, stroke_width=2).move_to([disk_x0 + disk_w / 2, disk_y, 0])
        disk_l = T("the primary's disk", 20, GREY_B).next_to(disk, UP, buff=0.12)
        fill0 = Rectangle(width=0.6, height=0.36, stroke_width=0).set_fill(BLUE_M, 0.8)
        fill0.move_to([disk_x0 + 0.02 + 0.3, disk_y, 0])
        full = Rectangle(width=disk_w - 0.04, height=0.36, stroke_width=0).set_fill(RED_M, 0.85).move_to(disk)
        gone = DashedVMobject(mbody(ST_C, GREY_D).set_fill(opacity=0).set_stroke(GREY_C, 2), num_dashes=70)
        self.steps("A slot is loyal. Too loyal. If its standby is gone for good, the slot keeps WAL forever, until the folder fills the disk "
                   "and the primary stops.", [
            (lambda: [*self.drop("cap"), FadeIn(disk), FadeIn(disk_l), FadeIn(fill0)], 0.5),
            "gone for good",
            (lambda: [FadeOut(VGroup(st, st_t, pw_l, pg_s, wr, su, self.lab["su"], self.lab["cnts"], self.lab["mf"], self.lab["mr"],
                                     *[self.lab[f"s{i}"] for i in range(7) if f"s{i}" in self.lab])), Create(gone), net.animate.set_opacity(0.2),
                      net_t.animate.set_opacity(0.2)], 0.8),
            "keeps WAL forever",
            (lambda: [Transform(fill0, full), *self.cap("WAL piles up", RED_M)], 2.0),
            "the primary stops",
            (lambda: [pr.animate.set_stroke(RED_M), *self.cap("disk full: the primary stops", RED_M)], 0.5),
        ])
        for k in ("su", "cnts", "mf", "mr") + tuple(f"s{i}" for i in range(7)):
            self.lab.pop(k, None)
        self.steps("Every payment stops, to save letters for a town nobody lives in.", [
            (lambda: [Wiggle(gone, scale_value=1.03)], 1.0),
        ], after=0.4)
        limits = VGroup(M("max_slot_wal_keep_size", 22, GOLD_M), M("idle_replication_slot_timeout", 22, GOLD_M)).arrange(RIGHT, buff=0.6)
        self.steps("So drop slots you no longer use, and give the primary a limit: max_slot_wal_keep_size, "
                   "or, new in PostgreSQL 18, idle replication slot timeout.", [
            (lambda: [FadeOut(disk), FadeOut(disk_l), FadeOut(fill0), pr.animate.set_stroke(BLUE_M),
                      *self.cap("drop slots you don't use, and give them a limit", WHITE)], 0.6),
            "give the primary",
            (lambda: self.work(limits[0].copy()), 0.5),
            "or, new in",
            (lambda: self.work(limits), 0.5),
        ])
        out = VGroup(M(" slot_name | active | wal_status | invalidation_reason", 20, GREY_B),
                     M(" standby1  | f      | lost       | idle_timeout", 20, WHITE)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        self.steps("With the standby stopped and that timeout at 10 seconds, the next checkpoint gave up on the slot.", [
            (lambda: [*self.cap("standby stopped, timeout 10 seconds, then a checkpoint", WHITE)], 0.5),
            "gave up",
            (lambda: [*self.work(out), FadeOut(slot), FadeOut(flag)], 0.7),
            (lambda: [*[self.lab[f"p{i}"].animate.set_opacity(0.15) for i in range(3)]], 0.6),
        ], after=0.6)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, how do you copy a database that never stops changing? Copy its folder once, never let its recovery end, "
                   "and feed it the primary's WAL.", [
            (lambda: [*self.drop("work", "cap"), FadeOut(gone), net.animate.set_opacity(1), net_t.animate.set_opacity(1),
                      *[self.lab[f"p{i}"].animate.set_opacity(1) for i in range(3)]], 0.6),
            "Copy its folder",
            (lambda: [FadeIn(st), FadeIn(st_t), FadeIn(pw_l), FadeIn(pg_s), *self.count("s", "1,007"),
                      *self.cap("copy the folder once", WHITE)], 0.9),
            "never let",
            (lambda: [*self.cap("never let its recovery end", WHITE), FadeIn(wr), FadeIn(su)], 0.6),
            "and feed it",
            (lambda: [*self.cap("feed it the primary's WAL", WHITE), *[self.scell(i, GOLD_M if i >= 4 else TEAL_M)[0] for i in range(7)],
                      *self.flushed(6), *self.replayed(6)], 0.8),
        ])
        self.steps("Keep a slot so it can rejoin, and give the slot a limit.", [
            (lambda: [*self.cap("a slot, so it can rejoin; a limit, so the disk survives", GOLD_M)], 0.6),
        ])
        bad = chip("delete every fee rule", RED_M, 20)
        self.steps("And the darker question? A standby copies bytes, not meaning. When a cleanup script deletes every shop's fee rules, "
                   "the standby deletes them too, a few milliseconds later.", [
            (lambda: [*self.cap("does the copy save you?", WHITE)], 0.5),
            "copies bytes",
            (lambda: [*self.cap("a standby copies bytes, not meaning", WHITE)], 0.5),
            "When a cleanup",
            (lambda: [*self.work(bad), *self.pcell(6, RED_M)], 0.6),
            "the standby deletes",
            (lambda: [dot_run(net.get_start(), net.get_end(), RED_M, 0.6)], 0.6),
            (lambda: [*self.scell(6, RED_M)], 0.3),
            (lambda: self.apply(ST_C, 6, pg_s, RED_M), 0.5),
        ])
        self.steps("For that you need a copy from the past: a backup.", [
            "a copy from the past",
            (lambda: [*self.cap("for mistakes: a copy from the past, a backup", YELLOW_M, 28), *self.drop("work")], 0.6),
        ], after=0.5)
        self.steps("One quick check. Written and flushed are at the newest byte, and replayed is behind. "
                   "Does a query on the standby see the newest rows? Pause and think.", [
            (lambda: [*self.drop("cap"), *self.pcell(6, GOLD_M), *self.scell(6, GOLD_M), *self.replayed(3), *self.count("s", 7)], 0.6),
            "Written and flushed",
            (lambda: [Indicate(self.lab["mf"], color=GREEN_M, scale_factor=1.6)], 0.6),
            "replayed is behind",
            (lambda: [Indicate(self.lab["mr"], color=YELLOW_M, scale_factor=1.6)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. Queries see only what's replayed. The bytes are on its disk, waiting.", [
            (lambda: [*self.cap("queries see only what's replayed", YELLOW_M, 30), Indicate(self.lab["cnts"], color=WHITE, scale_factor=1.2)], 0.7),
            "on its disk",
            (lambda: [*[glow(self.lab[f"s{i}"][0], GREEN_M, 1.1) for i in range(4, 7)]], 0.8),
        ], after=0.3)
        self.wait(2.0)
