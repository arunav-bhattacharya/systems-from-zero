from sfz import *

SAY.insert(0, (r"\bRSS\b", "R S S"))
SAY.insert(0, (r"\bPSS\b", "P S S"))
SAY.insert(0, (r"\b32,768\b", "thirty-two thousand, seven hundred and sixty-eight"))
SAY.insert(0, (r"\b131,072\b", "a hundred and thirty-one thousand"))
SAY.insert(0, (r"\b1\.8 microseconds\b", "one point eight microseconds"))
SAY.insert(0, (r"\b1\.7 milliseconds\b", "one point seven milliseconds"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
FR = "ABCDE"
FR_Y = [2.15, 1.2, 0.25, -0.7, -1.65]          # frames A..E, stacked in the middle; table rows share these heights
FW, FHT = 2.4, 0.72
TX = {0: (-6.5, -2.3), 1: (2.3, 6.5)}          # parent's table on the left, child's on the right
T_TOP, T_BOT = 2.68, -1.18
PCOL = {0: BLUE_M, 1: PURPLE_M}
PNAME = {0: "parent: its page table", 1: "child: its page table"}
MODE_X = {0: -3.15, 1: 5.65}
K_C, K_W, K_H = np.array([0.0, -2.58, 0]), 5.0, 0.6     # the kernel
CAP_Y, BAR_Y = -3.35, -3.0
SEG, BX0 = 0.85, -4.0                           # the 512 MB bars: 8 blocks of 64 MB
BY = {0: 1.45, 1: 0.25}


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


def dot_run(a, b, color=YELLOW_M, rt=0.6, frac=1.0, keep=False):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    seq = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=rt)]
    if not keep:
        seq.append(FadeOut(d, run_time=0.12))
    return Succession(*seq)


def harrow(a, b, color=GREY_B, sw=2.5):
    """Thin arrow with a small tip of the same size whatever its length."""
    ln = np.linalg.norm(np.array(b, dtype=float) - np.array(a, dtype=float))
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, tip_length=0.17, max_tip_length_to_length_ratio=max(0.18, 0.17 / ln),
                 max_stroke_width_to_length_ratio=8)


# ---- the pieces ----
def frame_box(i):
    r = RoundedRectangle(corner_radius=0.08, width=FW, height=FHT, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1).move_to([0, FR_Y[i], 0])
    return VGroup(r, T(f"frame {FR[i]}", 20).move_to([-0.48, FR_Y[i], 0]))


def refs_lab(i, n):
    return T("free" if n == 0 else f"refs {n}", 18, GOLD_M if n > 1 else GREY_B).move_to([0.68, FR_Y[i], 0])


def ptable(k):
    x0, x1 = TX[k]
    r = RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=T_TOP - T_BOT, stroke_color=PCOL[k], stroke_width=3)
    r.set_fill(fillc(PCOL[k]), 1).move_to([(x0 + x1) / 2, (T_TOP + T_BOT) / 2, 0])
    return VGroup(r, T(PNAME[k], 22, PCOL[k]).move_to([(x0 + x1) / 2, T_TOP + 0.3, 0]))


def prow(k, j, f, color=WHITE):
    return left_at(M(f"page {j}: frame {FR[f]}", 18, color), TX[k][0] + 0.25, FR_Y[j])


def mchip(k, j, rw):
    c = chip("rw" if rw else "read-only", GREEN_M if rw else GOLD_M, 17)
    return c.move_to([MODE_X[k], FR_Y[j], 0])


def parrow(k, j, f):
    if k == 0:
        a, b = [TX[0][1] + 0.08, FR_Y[j], 0], [-FW / 2 - 0.08, FR_Y[f], 0]
    else:
        a, b = [TX[1][0] - 0.08, FR_Y[j], 0], [FW / 2 + 0.08, FR_Y[f], 0]
    return harrow(a, b, PCOL[k])


def kbox():
    return RoundedRectangle(corner_radius=0.1, width=K_W, height=K_H, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M), 1).move_to(K_C)


def seg(k, i, color):
    r = Rectangle(width=SEG - 0.06, height=0.6, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.45), 1)
    return r.move_to([BX0 + SEG * (i + 0.5), BY[k], 0])


class CowOom(Base):
    """os-07, section 0. cow.c fills 512 MB and forks; memcpy would take 33 ms and a second 512 MB, yet the child runs
    1.7 ms after fork. Copying every page is slow where it hurts (Redis's 10 GB snapshot child; fork then exec).
    Sharing frames breaks: a write by the parent shows up in the child. The kitchen: a second cook shares the recipe
    binder, every page gets an ask-before-you-write sticker, and the manager photocopies one page when someone writes.
    Walkthrough of the lesson's stepper (read, write fault, copy C to E, parent's write reuses C), copy-on-write,
    the smaps numbers (Shared/Private, RSS 513 vs PSS 320 + 320 = 640), the cost (180 ms for every page), moral, check."""

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
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def drop_prefix(self, *prefixes):
        return self.drop(*[k for k in list(self.lab) if k.startswith(prefixes)])

    # one line of a page table: its text, its mode chip, its arrow
    def line(self, k, j, f, rw, grow=True):
        out = [*self.put(f"row{k}{j}", prow(k, j, f)), *self.put(f"mode{k}{j}", mchip(k, j, rw))]
        a = parrow(k, j, f)
        old = self.arr.get((k, j))
        self.arr[(k, j)] = a
        if old is None:
            out.append(GrowArrow(a) if grow else FadeIn(a))
        else:
            out += [FadeOut(old), GrowArrow(a)]
        return out

    def mode(self, k, j, rw):
        return self.put(f"mode{k}{j}", mchip(k, j, rw))

    def refs(self, i, n):
        return self.put(f"refs{i}", refs_lab(i, n))

    def kern(self, s, color=WHITE):
        return self.put("kst", left_at(T(s, 19, color), K_C[0] - K_W / 2 + 0.25, K_C[1]))

    def copies(self, n):
        return self.put("kcp", right_at(T(f"copies: {n}", 19, GOLD_M), K_C[0] + K_W / 2 - 0.25, K_C[1]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def row_pt(self, k, j):
        """Where a dot leaves table k's line j (its arrow's start)."""
        return self.arr[(k, j)].get_start()

    def construct(self):
        self.capm = None
        self.lab = {}
        self.arr = {}
        self.title_card("Copy 512 MB in 1.7 milliseconds", "fork and copy-on-write")

        # ---------------- scene 1: the question ----------------
        prog = VGroup(RoundedRectangle(corner_radius=0.12, width=3.4, height=1.3, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1),
                      T("a program", 26), T("512 MB of memory", 20, GREY_B)).move_to([-3.2, 0.9, 0])
        prog[1].move_to(prog[0].get_center() + 0.22 * UP)
        prog[2].move_to(prog[0].get_center() + 0.25 * DOWN)
        kid = VGroup(RoundedRectangle(corner_radius=0.12, width=3.4, height=1.3, stroke_color=PURPLE_M, stroke_width=3).set_fill(fillc(PURPLE_M), 1),
                     T("its copy", 26), T("running after 1.7 ms", 20, GREEN_M)).move_to([3.2, 0.9, 0])
        kid[1].move_to(kid[0].get_center() + 0.22 * UP)
        kid[2].move_to(kid[0].get_center() + 0.25 * DOWN)
        fk = harrow(prog.get_right() + [0.1, 0, 0], kid.get_left() + [-0.1, 0, 0], GREY_B)
        fk_l = M("fork()", 22).next_to(fk, UP, buff=0.12)
        self.steps("A program fills 512 megabytes of memory. Then it calls fork, the system call that starts a second process "
                   "as an exact copy of the first.", [
            (lambda: [FadeIn(prog, shift=0.1 * RIGHT)], 0.7),
            "Then it calls fork",
            (lambda: [GrowArrow(fk), FadeIn(fk_l)], 0.6),
            "an exact copy",
            (lambda: [FadeIn(kid[0]), FadeIn(kid[1])], 0.6),
        ])
        c1 = left_at(T("copying 512 MB the plain way: 33 ms, and a second 512 MB of RAM", 22, RED_M), -5.0, -0.8)
        self.steps("Copying 512 megabytes takes 33 milliseconds here, and needs another 512 megabytes of RAM. "
                   "Yet the copy is running 1.7 milliseconds after fork.", [
            (lambda: [FadeIn(c1, shift=0.1 * UP)], 0.6),
            "Yet the copy",
            (lambda: [FadeIn(kid[2], shift=0.1 * UP)], 0.6),
            (lambda: [Indicate(kid[2], color=GREEN_M, scale_factor=1.15)], 0.8),
        ])
        qm = T("?", 60, YELLOW_M).move_to([0, -1.9, 0])
        self.steps("How do you copy something faster than copying it?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.5)

        # ---------------- scene 2: a reminder ----------------
        frames = [frame_box(i) for i in range(5)]
        ram_t = T("RAM", 22).move_to([0, T_TOP + 0.3, 0])
        pt = ptable(0)
        self.steps("A quick reminder. Memory comes in pages of 4 kilobytes. Each process has a page table: the kernel's list "
                   "of which frame, which piece of real RAM, holds each of its pages.", [
            (lambda: [FadeOut(VGroup(prog, kid, fk, fk_l, c1, qm))], 0.6),
            "Each process",
            (lambda: [FadeIn(pt)], 0.6),
            "which frame",
            (lambda: [FadeIn(ram_t), LaggedStart(*[FadeIn(f) for f in frames], lag_ratio=0.12)], 0.9),
            (lambda: [*self.refs(0, 1), *self.refs(1, 1), *self.refs(2, 1), *self.refs(3, 1), *self.refs(4, 0)], 0.4),
        ])
        self.steps("Each line also says whether that page may be written. Here's a parent with four pages. "
                   "The real program has 131,072.", [
            (lambda: [*[x for j in range(4) for x in self.line(0, j, j, True)]], 1.0),
            "may be written",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"mode0{j}"], color=GREEN_M) for j in range(4)], lag_ratio=0.15)], 0.9),
            "The real program",
            (lambda: self.cap("4 pages here; 512 MB is 131,072 pages", WHITE), 0.6),
        ])

        # ---------------- scene 3: copy everything ----------------
        self.steps("Now let's design fork ourselves. The simplest version copies every page into fresh frames. "
                   "It's correct, and slow exactly where it hurts.", [
            (lambda: self.cap("fork, version 1: copy every page", WHITE), 0.6),
            "copies every page",
            (lambda: [LaggedStart(*[dot_run([0, FR_Y[j], 0], [3.0, FR_Y[j], 0], YELLOW_M, 0.6) for j in range(4)], lag_ratio=0.25)], 1.3),
        ])
        self.steps("Redis, a program that keeps data in memory, forks a child just to write a snapshot to disk. "
                   "With 10 gigabytes of data, a child that only reads would need 20 gigabytes of RAM.", [
            "Redis",
            (lambda: self.cap("Redis, 10 GB of data: a snapshot child that only reads would need 20 GB", RED_M), 0.6),
        ])
        self.steps("Or a program forks only to start another program, which throws the copy away at once. "
                   "That's photocopying a whole cookbook to read one recipe, then throwing it in the bin.", [
            (lambda: self.cap("fork, then start another program: the copy is thrown away at once", RED_M), 0.6),
            "That's photocopying",
            (lambda: self.cap("a whole cookbook photocopied, to read one recipe", GREY_B), 0.6),
        ], after=0.4)

        # ---------------- scene 4: share, and break it ----------------
        ct = ptable(1)
        self.steps("Next try: share. The child gets its own page table, pointing at the parent's frames. "
                   "That costs only the table, about 1 megabyte for 512 megabytes of pages.", [
            (lambda: self.cap("fork, version 2: share the frames", WHITE), 0.6),
            "its own page table",
            (lambda: [FadeIn(ct)], 0.6),
            "pointing at",
            (lambda: [*[x for j in range(4) for x in self.line(1, j, j, True)], *[x for i in range(4) for x in self.refs(i, 2)]], 1.0),
            "costs only",
            (lambda: self.cap("the only cost: the table, about 1 MB for 512 MB", GREEN_M), 0.6),
        ])
        self.steps("But now, if the parent writes to page 2, the child sees the change. And the child was promised its own copy.", [
            "the parent writes",
            (lambda: [dot_run(self.row_pt(0, 2), self.arr[(0, 2)].get_end(), RED_M, 0.6)], 0.7),
            (lambda: [glow(frames[2][0], RED_M, 1.05)], 0.6),
            "the child sees",
            (lambda: [Indicate(self.lab["row12"], color=RED_M, scale_factor=1.15), *self.cap("the child's page 2 changed too", RED_M)], 0.8),
        ], after=0.4)

        # ---------------- scene 5: the kitchen ----------------
        self.steps("A café kitchen has the same problem. A second cook joins, and is promised their own copy of the recipe binder. "
                   "Photocopying all of it would take all morning, and they'll mostly just read it.", [
            (lambda: self.cap("a second cook, promised their own copy of the recipe binder", WHITE), 0.6),
            "Photocopying all",
            (lambda: self.cap("photocopy it all? all morning, for pages they'll mostly just read", GREY_B), 0.6),
        ])
        self.steps("So the manager does something lazier. Both cooks share the binder, and every page gets a sticker: ask before you write.", [
            (lambda: self.cap("share the binder; a sticker on every page: ask before you write", WHITE), 0.6),
            "a sticker",
            (lambda: [LaggedStart(*[x for k in (0, 1) for j in range(4) for x in self.mode(k, j, False)], lag_ratio=0.08)], 1.2),
        ])
        self.steps("When a cook wants to change page 2, the manager photocopies just page 2, "
                   "and that copy becomes their page 2, with no sticker.", [
            "change page 2",
            (lambda: [Indicate(self.lab["row12"], color=YELLOW_M, scale_factor=1.15)], 0.7),
            "photocopies just",
            (lambda: self.cap("only the page being written gets copied", YELLOW_M), 0.6),
        ])
        self.steps("Let's map it. The cooks are the two processes. The sheets of paper are frames of RAM. "
                   "The sticker is a read-only mark, on every line of both page tables. And the manager is the kernel.", [
            (lambda: [glow(pt[0], BLUE_M, 1.02), glow(ct[0], PURPLE_M, 1.02), *self.cap("the cooks: the two processes", WHITE)], 0.7),
            "The sheets",
            (lambda: [LaggedStart(*[glow(f[0], WHITE, 1.05) for f in frames[:4]], lag_ratio=0.15), *self.cap("the sheets: frames of RAM", WHITE)], 0.9),
            "The sticker",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"mode{k}{j}"], color=GOLD_M) for k in (0, 1) for j in range(4)], lag_ratio=0.08),
                      *self.cap("the sticker: a read-only mark on each line", GOLD_M)], 1.0),
            "the manager",
            (lambda: [*self.put("kbox", kbox()), *self.kern("kernel: idle"), *self.copies(0), *self.cap("the manager: the kernel", TEAL_M)], 0.7),
        ], after=0.4)

        # ---------------- scene 6: the walkthrough ----------------
        self.steps("So here's what fork really does. It builds the child's table pointing at the same frames, and marks every line "
                   "read-only, the parent's too. Each frame now has two lines pointing at it. No data moved.", [
            (lambda: [*self.uncap(), *self.kern("kernel: fork()", TEAL_M)], 0.5),
            "marks every line",
            (lambda: [LaggedStart(*[glow(self.lab[f"mode{k}{j}"][0], GOLD_M, 1.05) for k in (0, 1) for j in range(4)], lag_ratio=0.06)], 1.0),
            "two lines",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"refs{i}"], color=GOLD_M, scale_factor=1.2) for i in range(4)], lag_ratio=0.15)], 0.9),
            "No data moved",
            (lambda: [*self.kern("kernel: idle")], 0.4),
        ])
        self.steps("The child reads page 1. Reading is allowed, so the CPU loads it straight from frame B, and the kernel never hears about it.", [
            (lambda: [Indicate(self.lab["row11"], color=YELLOW_M, scale_factor=1.12)], 0.6),
            "Reading is allowed",
            (lambda: [dot_run(self.row_pt(1, 1), self.arr[(1, 1)].get_end(), YELLOW_M, 0.7)], 0.8),
            "never hears",
            (lambda: [Indicate(self.lab["kst"], color=WHITE)], 0.6),
        ])
        fault_c = harrow([3.8, T_BOT - 0.08, 0], [K_C[0] + K_W / 2 - 0.3, K_C[1] + K_H / 2 + 0.08, 0], RED_M)
        self.steps("Now the child writes to page 2. The line says read-only, so the CPU stops the write, and hands control to the kernel. "
                   "That's called a page fault.", [
            "writes to page 2",
            (lambda: [dot_run([TX[1][0] + 1.2, FR_Y[2], 0], [MODE_X[1] - 0.55, FR_Y[2], 0], RED_M, 0.5)], 0.6),
            "The line says",
            (lambda: [glow(self.lab["mode12"][0], RED_M, 1.1)], 0.6),
            "hands control",
            (lambda: [GrowArrow(fault_c)], 0.5),
            (lambda: [*self.kern("kernel: page fault", RED_M)], 0.4),
            "a page fault",
            (lambda: self.cap("page fault: the CPU stops, and hands control to the kernel", RED_M), 0.6),
        ])
        self.steps("The kernel sees that the page may really be written, and that frame C is shared. "
                   "So it copies frame C's 4 kilobytes into a free frame, E.", [
            (lambda: [*self.uncap(), Indicate(self.lab["refs2"], color=GOLD_M, scale_factor=1.25)], 0.7),
            "So it copies",
            (lambda: [*self.kern("kernel: copy C to E", TEAL_M)], 0.4),
            (lambda: [dot_run([0.95, FR_Y[2], 0], [0.95, FR_Y[4], 0], YELLOW_M, 0.8)], 0.9),
            (lambda: [*self.refs(4, 1), glow(frames[4][0], PURPLE_M, 1.05), *self.copies(1)], 0.5),
        ])
        self.steps("It points the child's line at E, and makes it writable. Then the write runs again, and lands in E.", [
            "points the child's",
            (lambda: [*self.line(1, 2, 4, True), *self.refs(2, 1)], 0.8),
            "the write runs",
            (lambda: [FadeOut(fault_c), *self.kern("kernel: idle")], 0.3),
            (lambda: [dot_run(self.row_pt(1, 2), self.arr[(1, 2)].get_end(), PURPLE_M, 0.7)], 0.8),
        ])
        fault_p = harrow([-3.8, T_BOT - 0.08, 0], [K_C[0] - K_W / 2 + 0.3, K_C[1] + K_H / 2 + 0.08, 0], RED_M)
        self.steps("Now the parent writes to page 2. Its line is still read-only, so it faults too. "
                   "Will the kernel copy frame C again? Pause and guess.", [
            "the parent writes",
            (lambda: [dot_run([TX[0][0] + 1.2, FR_Y[2], 0], [MODE_X[0] - 0.55, FR_Y[2], 0], RED_M, 0.5)], 0.6),
            "it faults",
            (lambda: [GrowArrow(fault_p), *self.kern("kernel: page fault", RED_M)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. Only one line points at C now, so nobody else can see it. The kernel just makes the line writable again, "
                   "and copies nothing.", [
            (lambda: [*self.uncap(), Indicate(self.lab["refs2"], color=WHITE, scale_factor=1.3)], 0.7),
            "just makes",
            (lambda: [*self.mode(0, 2, True), *self.kern("kernel: reuse C, no copy", GREEN_M)], 0.5),
            "copies nothing",
            (lambda: [Indicate(self.lab["kcp"], color=GOLD_M, scale_factor=1.15), FadeOut(fault_p)], 0.7),
        ], after=0.3)
        self.stamp("walk")

        # ---------------- scene 7: the name ----------------
        self.steps("This is called copy-on-write: share every page, and copy one only when someone writes to it. "
                   "The kernel counts the lines pointing at each frame, so it knows when to copy and when not to.", [
            (lambda: [*self.kern("kernel: idle"), *self.cap("copy-on-write: share every page; copy one only when someone writes to it", YELLOW_M)], 0.6),
            "The kernel counts",
            (lambda: [LaggedStart(*[Indicate(self.lab[f"refs{i}"], color=GOLD_M, scale_factor=1.2) for i in range(5)], lag_ratio=0.12)], 1.0),
        ], after=0.4)

        # ---------------- scene 8: count it ----------------
        ttl = T("cow.c: 512 MB, drawn as 8 blocks of 64 MB", 22, GREY_B).move_to([BX0 + 4 * SEG, 2.45, 0])
        plab = {k: right_at(T("parent" if k == 0 else "child", 24, PCOL[k]), BX0 - 0.25, BY[k]) for k in (0, 1)}
        segs = {k: [seg(k, i, TEAL_M) for i in range(8)] for k in (0, 1)}
        shared = T("the same frames", 18, TEAL_M).move_to([BX0 + 4 * SEG, (BY[0] + BY[1]) / 2, 0])
        self.steps("In the lab, the kernel reports each process's memory. Right after fork, the child shows 512 megabytes shared "
                   "with the parent, and 0 of its own.", [
            (lambda: [FadeOut(VGroup(pt, ct, *frames, ram_t, *self.arr.values())), *self.drop_prefix("row", "mode", "refs", "kst", "kcp", "kbox"),
                      *self.uncap()], 0.8),
            (lambda: [FadeIn(ttl), FadeIn(plab[0]), FadeIn(plab[1]), *[FadeIn(s) for k in (0, 1) for s in segs[k]]], 0.8),
            "512 megabytes shared",
            (lambda: [FadeIn(shared), *self.put("n1", left_at(T("Shared 512 MB, Private 0", 18), BX0 + 8 * SEG + 0.2, BY[1])),
                      *self.put("n0", left_at(T("Shared 512 MB, Private 0", 18), BX0 + 8 * SEG + 0.2, BY[0]))], 0.7),
        ])
        newk = {i: seg(1, i, PURPLE_M) for i in (1, 5)}
        newp = {i: seg(0, i, BLUE_M) for i in (1, 5)}
        self.steps("Then it writes one byte in every fourth page. The kernel makes 32,768 copies, 128 megabytes, "
                   "at about 1.8 microseconds each. Now the child shows 384 shared, and 128 of its own.", [
            "every fourth page",
            (lambda: [*[Indicate(segs[1][i], color=RED_M) for i in (1, 5)]], 0.7),
            "The kernel makes",
            (lambda: [*[Transform(segs[1][i], newk[i]) for i in (1, 5)], *[Transform(segs[0][i], newp[i]) for i in (1, 5)],
                      *self.cap("32,768 page faults, one 4 KB copy each, about 1.8 µs each", WHITE)], 0.9),
            "Now the child",
            (lambda: [*self.put("n1", left_at(T("Shared 384 MB, Private 128", 18), BX0 + 8 * SEG + 0.2, BY[1])),
                      *self.put("n0", left_at(T("Shared 384 MB, Private 128", 18), BX0 + 8 * SEG + 0.2, BY[0]))], 0.7),
        ])
        l1 = left_at(T("RSS (every page it has in RAM): 513 + 513 = about 1 GB?", 22, RED_M), BX0, -0.75)
        l2 = left_at(T("really used: 512 + 128 = 640 MB", 22, WHITE), BX0, -1.35)
        l3 = left_at(T("PSS (shared pages split between sharers): 320 + 320 = 640 MB", 22, GREEN_M), BX0, -1.95)
        self.steps("One trap. RSS, the usual memory number, counts every page a process has in RAM. It says 513 for each, "
                   "so adding them claims a gigabyte. They really use 640.", [
            (lambda: [*self.uncap(), FadeIn(l1, shift=0.1 * UP)], 0.6),
            "They really use",
            (lambda: [FadeIn(l2, shift=0.1 * UP)], 0.6),
        ])
        self.steps("PSS splits each shared page between its sharers, and the two PSS numbers add up to exactly 640. "
                   "So to add up memory, add PSS.", [
            (lambda: [FadeIn(l3, shift=0.1 * UP)], 0.6),
            "So to add up",
            (lambda: [*self.cap("to add up memory, add PSS", YELLOW_M, 30), Indicate(l3, color=GREEN_M, scale_factor=1.04)], 0.8),
        ], after=0.4)

        # ---------------- scene 9: the cost ----------------
        allk = [seg(1, i, PURPLE_M) for i in range(8)]
        allp = [seg(0, i, BLUE_M) for i in range(8)]
        self.steps("Copy-on-write isn't free, though. When the child wrote to every page, the faults took 180 milliseconds, "
                   "several times one big copy.", [
            (lambda: [FadeOut(VGroup(l1, l2, l3, shared)), *self.uncap()], 0.5),
            "every page",
            (lambda: [*[Transform(segs[1][i], allk[i]) for i in range(8)], *[Transform(segs[0][i], allp[i]) for i in range(8)],
                      *self.put("n1", left_at(T("Shared 0, Private 512", 18), BX0 + 8 * SEG + 0.2, BY[1])),
                      *self.put("n0", left_at(T("Shared 0, Private 512", 18), BX0 + 8 * SEG + 0.2, BY[0]))], 0.9),
            "the faults took",
            (lambda: self.cap("131,072 faults: 180 ms     one big copy: 28 to 33 ms", RED_M), 0.6),
        ])
        self.steps("The kitchen agrees: asking the manager 131,072 times takes longer than one trip to the copy shop. "
                   "Copy-on-write wins because most children write a little, or start another program and write nothing.", [
            "The kitchen agrees",
            (lambda: self.cap("131,072 trips to the manager, or one trip to the copy shop", GREY_B), 0.6),
            "Copy-on-write wins",
            (lambda: self.cap("it wins because most children write a little, or nothing at all", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 10: moral, and a check ----------------
        self.arr = {}
        frames = [frame_box(i) for i in range(5)]
        pt, ct = ptable(0), ptable(1)

        def rebuild():
            out = [FadeIn(pt), FadeIn(ct), FadeIn(ram_t), *[FadeIn(f) for f in frames], *self.put("kbox", kbox())]
            for k in (0, 1):
                for j in range(4):
                    out += self.line(k, j, j, False, grow=False)
            for i in range(4):
                out += self.refs(i, 2)
            out += self.refs(4, 0)
            out += self.kern("kernel: idle") + self.copies(0)
            return out

        self.steps("So the moral of the story: fork copies the list, not the memory. Everything is shared until someone writes, "
                   "and then only that page is copied.", [
            (lambda: [FadeOut(VGroup(ttl, plab[0], plab[1], *segs[0], *segs[1])), *self.drop("n0", "n1"),
                      *self.cap("fork copies the list, not the memory", YELLOW_M, 30)], 0.7),
            (lambda: rebuild(), 1.0),
            "only that page",
            (lambda: [Indicate(self.lab["row12"], color=YELLOW_M, scale_factor=1.12)], 0.7),
        ])
        self.steps("One quick check. A child only reads, like Redis writing its snapshot. How many pages does the kernel copy? "
                   "Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "only reads",
            (lambda: [LaggedStart(*[dot_run(self.row_pt(1, j), self.arr[(1, j)].get_end(), YELLOW_M, 0.6) for j in range(4)], lag_ratio=0.25)], 1.3),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("None. Reads never fault, so the child can run for minutes without costing a single copy.", [
            (lambda: [*self.uncap(), Indicate(self.lab["kcp"], color=GOLD_M, scale_factor=1.2)], 0.7),
            "Reads never fault",
            (lambda: [LaggedStart(*[dot_run(self.row_pt(1, j), self.arr[(1, j)].get_end(), YELLOW_M, 0.5) for j in range(4)], lag_ratio=0.2)], 1.1),
        ], after=0.3)
        self.play(*self.cap("fork copies the list, not the memory", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
