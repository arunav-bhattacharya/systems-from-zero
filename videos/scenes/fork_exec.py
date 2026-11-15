from sfz import *

SAY.insert(0, (r"\bls\b", "L S"))
SAY.insert(0, (r"\bfiles\.txt\b", "files dot text"))
# the voice says the verb "copies" as "cop is"
SAY.insert(0, (r"(?<!Both )\bcopies\b", "cop-eez"))

PX, KX, BY, BW, BH = -3.6, 3.6, 1.55, 4.6, 2.0      # parent and child boxes
PG_Y, PG_W, PG_H = -1.55, 1.3, 0.75                  # pages in RAM
SHARED = [-5.8, -4.35, -2.9, -1.45]
COPY_X = 0.2
LS = [2.1, 3.55, 5.0]
STATUS_Y = -3.33


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(a, b, color=YELLOW_M, run_time=0.6):
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.1))


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


def pbox(x, color):
    r = RoundedRectangle(corner_radius=0.16, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    return r.move_to([x, BY, 0])


def pid(x, s, color=WHITE):
    t = M(s, 24, color)
    return t.move_to([x - BW / 2 + 0.28 + t.width / 2, BY + 0.6, 0])


def prog(x, s, color=WHITE):
    t = T(s, 26, color)
    return t.move_to([x + BW / 2 - 0.28 - t.width / 2, BY + 0.6, 0])


def fd(x, s, color=GREY_A):
    t = M(s, 22, color)
    return t.move_to([x - BW / 2 + 0.28 + t.width / 2, BY, 0])


def st(x, s, color=GREY_B, mono=False):
    t = M(s, 22, color) if mono else T(s, 24, color)
    return t.move_to([x - BW / 2 + 0.28 + t.width / 2, BY - 0.6, 0])


def page(x, label, color=GREY_B, size=21):
    r = RoundedRectangle(corner_radius=0.08, width=PG_W, height=PG_H, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    return VGroup(r.move_to([x, PG_Y, 0]), T(label, size).move_to([x, PG_Y, 0]))


def maps(xs_from, xs_to, color, dashed=False):
    top, bot = BY - BH / 2, PG_Y + PG_H / 2
    ls = []
    for a, b in zip(xs_from, xs_to):
        ln = (DashedLine([a, top, 0], [b, bot, 0], dash_length=0.1) if dashed else Line([a, top, 0], [b, bot, 0]))
        ls.append(ln.set_stroke(color, 2))
    return VGroup(*ls)


def status(s, color=GREY_B):
    return T(s, 24, color).move_to([0, STATUS_Y, 0])


class ForkExec(Base):
    """os-02, sections 1 and 2: a shell runs `ls -l > files.txt`. fork copies the process (PID 41 makes PID 42; fork returns
    42 and 0) and shares its pages read-only until a write copies one; the child points fd 1 at files.txt, then exec loads
    ls (same PID, same files); the parent waits, ls exits with 0, the kernel keeps only the PID and status, and wait reaps
    it. A parent that never waits leaves zombies that hold PIDs."""

    def construct(self):
        self.title_card("fork, exec and wait", "how one program starts another, and the zombie it can leave behind")

        cmd = M("$ ls -l > files.txt", 24, GREY_A)
        cmd.move_to([-6.4 + cmd.width / 2, 3.25, 0])
        pr = pbox(PX, BLUE_M)
        p_pid, p_prog = pid(PX, "PID 41"), prog(PX, "program: tinysh")
        p_fd, p_st = fd(PX, "fd 1 → terminal"), st(PX, "running")
        pages = [page(x, n) for x, n in zip(SHARED, ("code", "data", "heap", "stack"))]
        pmaps = maps([PX - 1.5, PX - 0.5, PX + 0.5, PX + 1.5], SHARED, BLUE_M)
        mem = T("physical memory", 20, GREY_B)
        mem.move_to([-6.4 + mem.width / 2, PG_Y - 0.65, 0])
        self.steps("A shell has to run ls, with its output going to a file. How does one program start another?", [
            (lambda: [AddTextLetterByLetter(cmd)], 1.0),
            "How does",
            (lambda: [FadeIn(pr), FadeIn(p_pid), FadeIn(p_prog), FadeIn(p_fd), FadeIn(p_st)], 0.7),
            (lambda: [Create(pmaps), *[FadeIn(p) for p in pages], FadeIn(mem)], 0.8),
        ])

        kr = pbox(KX, TEAL_M)
        k_pid, k_prog = pid(KX, "PID 42", TEAL_M), prog(KX, "program: tinysh")
        k_fd, k_st = fd(KX, "fd 1 → terminal"), st(KX, "running")
        farr = Arrow([PX + BW / 2 + 0.1, BY + 0.2, 0], [KX - BW / 2 - 0.1, BY + 0.2, 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.15)
        flab = M("fork()", 20, GREY_A).next_to(farr, UP, buff=0.12)
        self.steps("On Linux it takes three calls. The first is fork. It makes a copy of the calling process, with a new PID.", [
            "The first is fork",
            (lambda: [GrowArrow(farr), FadeIn(flab)], 0.6),
            "It makes a copy",
            (lambda: [TransformFromCopy(pr, kr), TransformFromCopy(p_prog, k_prog), TransformFromCopy(p_fd, k_fd),
                      TransformFromCopy(p_st, k_st), TransformFromCopy(p_pid, k_pid)], 1.0),
            "with a new PID",
            (lambda: [Indicate(k_pid, color=TEAL_M)], 0.8),
        ])

        self.steps("Both copies return from the same fork. The parent gets the child's PID, 42. "
                   "The child gets 0, and that's how each one knows which it is.", [
            "The parent gets",
            (lambda: [Transform(p_st, st(PX, "fork() returned 42", GOLD_M, mono=True))], 0.7),
            "The child gets 0",
            (lambda: [Transform(k_st, st(KX, "fork() returned 0", GOLD_M, mono=True))], 0.7),
            "and that's how",
            (lambda: [Indicate(p_st, color=GOLD_M), Indicate(k_st, color=GOLD_M)], 0.9),
        ])

        kfrom = [KX - 1.5, KX - 0.5, KX + 0.5, KX + 1.5]
        kmaps = maps(kfrom, SHARED, TEAL_M, dashed=True)
        ro = status("the same pages, shared and marked read-only")
        self.steps("Copying all its memory would be slow. So the kernel copies nothing: "
                   "both processes point at the same pages, marked read only.", [
            "So the kernel",
            (lambda: [Create(kmaps)], 1.0),
            "marked read only",
            (lambda: [*[p[0].animate.set_stroke(GOLD_M) for p in pages], FadeIn(ro, shift=0.1 * UP)], 0.7),
        ])

        cp = page(COPY_X, "heap copy", TEAL_M, 18)
        new3 = maps([kfrom[2]], [COPY_X], TEAL_M)[0]
        cow = status("copy on write: the kernel copies a page only when it's written", TEAL_M)
        self.steps("Only when one of them writes to a page does the kernel copy that one page. This is copy on write.", [
            "writes to a page",
            (lambda: [glow(pages[2][0], TEAL_M, 1.1)], 0.7),
            "does the kernel copy",
            (lambda: [TransformFromCopy(pages[2], cp)], 0.8),
            (lambda: [Transform(kmaps[2], new3)], 0.6),
            "This is copy",
            (lambda: [Transform(ro, cow)], 0.7),
        ])

        fchip = chip("files.txt", GOLD_M, 20, mono=True).move_to([KX + 1.6, 3.25, 0])
        self.steps("The child is still running the shell's code. So it sets itself up first: "
                   "it opens files.txt, and points descriptor 1, its output, at it.", [
            (lambda: [FadeOut(ro), Indicate(k_prog, color=TEAL_M)], 0.9),
            "it opens",
            (lambda: [FadeIn(fchip, shift=0.1 * DOWN)], 0.6),
            "and points",
            (lambda: [Transform(k_fd, fd(KX, "fd 1 → files.txt", GOLD_M))], 0.8),
        ])

        ls_pages = [page(x, n, TEAL_M, 19) for x, n in zip(LS, ("ls code", "ls data", "ls stack"))]
        lmaps = maps([KX - 1.2, KX, KX + 1.2], LS, TEAL_M)
        elab = M("exec(ls)", 20, GREY_A).move_to([KX, BY + BH / 2 + 0.3, 0])
        self.steps("Then the child calls exec. The kernel throws away the shell's code and memory, and loads ls. "
                   "The PID stays 42, and so do the open files.", [
            (lambda: [FadeIn(elab, shift=0.1 * DOWN)], 0.5),
            "The kernel throws",
            (lambda: [FadeOut(kmaps), FadeOut(cp), *[p[0].animate.set_stroke(GREY_B) for p in pages]], 0.8),
            "and loads ls",
            (lambda: [Transform(k_prog, prog(KX, "program: ls", TEAL_M)), Transform(k_st, st(KX, "running ls")),
                      *[FadeIn(p) for p in ls_pages], Create(lmaps)], 0.9),
            "The PID stays",
            (lambda: [Indicate(k_pid, color=YELLOW_M)], 0.6),
            "and so do",
            (lambda: [Indicate(k_fd, color=YELLOW_M)], 0.6),
        ])

        out_a = k_fd.get_right() + 0.15 * RIGHT
        self.steps("ls writes to descriptor 1, as always, and its lines land in the file. ls never knew.", [
            (lambda: [flow(out_a, fchip.get_bottom() + 0.05 * DOWN, GOLD_M, 0.6)], 0.7),
            (lambda: [flow(out_a, fchip.get_bottom() + 0.05 * DOWN, GOLD_M, 0.6), glow(fchip[0], GOLD_M, 1.08)], 0.8),
            "ls never knew",
            (lambda: [flow(out_a, fchip.get_bottom() + 0.05 * DOWN, GOLD_M, 0.6)], 0.7),
        ])

        zr = pbox(KX, GREY_C)
        self.steps("Meanwhile the parent sleeps in wait. When ls exits with status 0, the kernel frees its memory and files, "
                   "but keeps a small record: the PID and the exit status.", [
            (lambda: [Transform(p_st, st(PX, "sleeping in wait()")), FadeOut(farr), FadeOut(flab), FadeOut(elab)], 0.7),
            "When ls exits",
            (lambda: [Transform(k_st, st(KX, "exit status 0", WHITE))], 0.6),
            "the kernel frees",
            (lambda: [FadeOut(VGroup(*ls_pages)), FadeOut(lmaps), FadeOut(fchip), Transform(k_fd, fd(KX, "no files, no memory", GREY_C)),
                      Transform(k_prog, prog(KX, "exited", GREY_B))], 0.9),
            "but keeps",
            (lambda: [Transform(kr, zr), Indicate(k_pid, color=WHITE), Indicate(k_st, color=WHITE)], 0.9),
        ])

        warr = Arrow([KX - BW / 2 - 0.1, BY - 0.3, 0], [PX + BW / 2 + 0.1, BY - 0.3, 0], buff=0, stroke_width=3, color=GREEN_M,
                     max_tip_length_to_length_ratio=0.15)
        wlab = T("status 0", 20, GREEN_M).next_to(warr, DOWN, buff=0.12)
        reap = status("reaping: wait collects the status, the record is deleted", GREEN_M)
        self.steps("wait hands the status to the parent, and the kernel deletes the record. "
                   "That's reaping, and it's where dollar question mark gets its 0.", [
            (lambda: [GrowArrow(warr), FadeIn(wlab)], 0.7),
            (lambda: [Transform(p_st, st(PX, "$? = 0", GREEN_M, mono=True))], 0.6),
            "and the kernel deletes",
            (lambda: [FadeOut(VGroup(kr, k_pid, k_prog, k_fd, k_st, warr, wlab))], 0.8),
            "That's reaping",
            (lambda: [FadeIn(reap, shift=0.1 * UP)], 0.6),
            "dollar question mark",
            (lambda: [Indicate(p_st, color=GREEN_M)], 0.8),
        ])

        zr2 = pbox(KX, GREY_C)
        z_pid, z_prog = pid(KX, "PID 42", GREY_A), prog(KX, "Z  <defunct>", GREY_A)
        z_fd, z_st = fd(KX, "no CPU, no memory", GREY_C), st(KX, "exit status 0, never read", GREY_B)
        self.steps("If the parent never waits, that record stays. The dead child is a zombie: "
                   "it uses no CPU and can't be killed, but it holds a PID.", [
            (lambda: [FadeOut(reap), Transform(p_st, st(PX, "never calls wait()", RED_M))], 0.7),
            "that record stays",
            (lambda: [FadeIn(VGroup(zr2, z_pid, z_fd, z_st))], 0.7),
            "The dead child",
            (lambda: [FadeIn(z_prog)], 0.6),
            "but it holds",
            (lambda: [Indicate(z_pid, color=RED_M, scale_factor=1.3)], 0.9),
        ])

        zs = VGroup(*[chip(f"Z  PID {43 + k}", GREY_C, 18, mono=True) for k in range(7)]).arrange(RIGHT, buff=0.2)
        zs.move_to([0, -2.78, 0])
        fit(zs, 12.6)
        leak = status("every zombie keeps a PID, and the container's supply runs out", RED_M)
        self.steps("Leak one per call, and the container eventually runs out of PIDs.", [
            (lambda: [LaggedStart(*[FadeIn(z, shift=0.1 * UP) for z in zs], lag_ratio=0.3)], 1.6),
            (lambda: [FadeIn(leak, shift=0.1 * UP)], 0.6),
        ])

        self.steps("fork copies cheaply, exec swaps the program, and a dead child waits as a zombie "
                   "until its parent collects it.", [
            (lambda: [glow(pr, BLUE_M, 1.03)], 0.9),
            "exec swaps",
            (lambda: [Indicate(z_prog, color=TEAL_M)], 0.8),
            "and a dead child",
            (lambda: [glow(zr2, GREY_A, 1.03), *[z.animate(rate_func=there_and_back).set_opacity(0.4) for z in zs]], 1.0),
        ])
        self.wait(0.6)
