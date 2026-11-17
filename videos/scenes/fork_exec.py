from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\btinysh\b", "tiny shell"),
    (r"\bls\b", "L S"),
    (r"\bPID\b", "P I D"),
    (r"\bdup2\b", "dup two"),
    (r"\blisting\.txt\b", "listing dot text"),
    (r"\bProcess\.waitFor\b", "Process dot wait for"),
    (r"\bcopies\b", "cop-eez"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PA, CH = np.array([-3.6, 1.15, 0]), np.array([3.6, 1.15, 0])     # parent and child
BW, BH = 4.0, 1.9
PAGE_DX = [-0.55, -0.1, 0.35, 0.8]
SLOT_Y, SLOT_DX = -0.35, [-0.55, 0.05, 0.65]
TM, TM_W = np.array([-3.6, -2.05, 0]), 3.0                        # the terminal
FL, FL_W = np.array([3.6, -2.05, 0]), 3.6                         # the file listing.txt
BOX_H = 0.8
PROMPT = np.array([-6.3, 3.1, 0])
TAG_Y = 2.42
CAP_Y, BAR_Y = -3.1, -3.48
CODE_X, CODE_TOP, CODE_DY = -0.55, 2.3, 0.4


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def page(c, dx, color=BLUE_M, a=0.35):
    return Square(0.34, stroke_color=color, stroke_width=2).set_fill(fillc(color, a), 1).move_to(c + [dx, -0.45, 0])


def proc(c, name, pid_line):
    """A process: its name, its PID line and a row of four memory pages. [0] box, [1] name, [2] PID, [3] label, [4] pages."""
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    nm = T(name, 26).move_to(c + [0, 0.55, 0])
    pid = M(pid_line, 18, GREY_B).move_to(c + [0, 0.1, 0])
    mlab = left_at(T("memory", 17, GREY_B), c[0] - 1.78, c[1] - 0.45)
    pages = VGroup(*[page(c, dx) for dx in PAGE_DX])
    return VGroup(r, nm, pid, mlab, pages)


def slots(c):
    """The open files: three numbered slots under a process. [0] the slots, [1] the label."""
    sq = VGroup(*[VGroup(Square(0.42, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1), M(str(i), 18)).move_to([c[0] + dx, SLOT_Y, 0])
                  for i, dx in enumerate(SLOT_DX)])
    lab = right_at(T("files", 16, GREY_B), c[0] + SLOT_DX[0] - 0.35, SLOT_Y)
    return VGroup(sq, lab)


def out_arrow(c, target, color=GREY_B):
    a = np.array([c[0] + SLOT_DX[1], SLOT_Y - 0.21, 0])
    return Arrow(a, target, buff=0.06, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.1)


TO_TERM_P = np.array([TM[0] + SLOT_DX[1], TM[1] + BOX_H / 2, 0])
TO_TERM_C = np.array([TM[0] + 1.0, TM[1] + BOX_H / 2, 0])
TO_FILE = np.array([FL[0] + SLOT_DX[1], FL[1] + BOX_H / 2, 0])


def lines_in(c, w, n, color=WHITE):
    """n short lines of text, drawn as strokes on the right side of a box."""
    x1 = c[0] + w / 2 - 0.3
    return VGroup(*[Line([x1 - 0.9, c[1] + 0.21 - 0.14 * k, 0], [x1, c[1] + 0.21 - 0.14 * k, 0], stroke_width=2.5, color=color) for k in range(n)])


CODE = [(0, "pid = fork();", "// 1. copy"), (0, "if (pid == 0) {", "// the child"), (1, "fd = open(file, ...);", "// set up"),
        (1, "dup2(fd, 1);", ""), (1, "execvp(argv[0], argv);", "// 2. swap"), (1, "_exit(127);", "// exec failed"),
        (0, "}", ""), (0, "waitpid(pid, &status, 0);", "// 3. wait")]


def code_line(i):
    ind, s, c = CODE[i]
    body = M(s, 18)
    g = VGroup(left_at(body, CODE_X + 0.5 * ind, CODE_TOP - CODE_DY * i))
    if c:
        g.add(left_at(M(c, 18, GREY_B), CODE_X + 4.45, CODE_TOP - CODE_DY * i))
    return g


class ForkExec(Base):
    """os-02, section 1. tinysh (PID 43) runs `ls os > /tmp/listing.txt`. One spawn call would need a setting for every
    kind of setup. fork copies the shell (PID 45; 45 to the parent, 0 to the child; pages shared until written), the
    child points descriptor 1 at the file in the gap, exec swaps in ls and keeps the PID, the parent and the open files,
    and wait collects status 0. exec returns only on failure (127); a parent waits."""

    def construct(self):
        self.capm = None
        self.title_card("fork, exec and wait", "how one program starts another, and why it takes two steps")

        # ---------------- scene 1: the hook ----------------
        prompt = M("tinysh$ ls os > /tmp/listing.txt", 22, t2c={"> /tmp/listing.txt": YELLOW_M})
        left_at(prompt, PROMPT[0], PROMPT[1])
        term = VGroup(RoundedRectangle(corner_radius=0.12, width=TM_W, height=BOX_H, stroke_color=GREY_B, stroke_width=3).set_fill(BLACK, 1).move_to(TM),
                      left_at(T("terminal", 20, GREY_B), TM[0] - TM_W / 2 + 0.3, TM[1]))
        fbox = VGroup(RoundedRectangle(corner_radius=0.12, width=FL_W, height=BOX_H, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(FL),
                      left_at(M("listing.txt", 20), FL[0] - FL_W / 2 + 0.3, FL[1]))
        flines = lines_in(FL, FL_W, 4)
        tlines = lines_in(TM, TM_W, 3, GREY_B)
        self.steps("You type ls into a shell, the program that reads your commands, and a moment later ls is running, listing files.", [
            (lambda: [FadeIn(prompt[:11])], 0.6),
            "a moment later",
            (lambda: [FadeIn(term)], 0.5),
            (lambda: [LaggedStart(*[Create(l) for l in tlines], lag_ratio=0.4)], 0.8),
        ])
        self.steps("Now add a greater-than sign and a file name. The same ls runs, but its list lands in the file instead of on the screen. "
                   "And ls never knows. How does the shell do that?", [
            (lambda: [FadeIn(prompt[11:], shift=0.1 * LEFT), FadeOut(tlines)], 0.6),
            "The same ls",
            (lambda: [FadeIn(fbox)], 0.5),
            "lands in the file",
            (lambda: [LaggedStart(*[Create(l) for l in flines], lag_ratio=0.4)], 0.9),
            "How does",
            (lambda: self.cap("ls never knows. How does the shell do that?", WHITE), 0.5),
        ])

        # ---------------- scene 2: one call for everything ----------------
        form_x, form_top = 1.2, 2.45
        form = [M("spawn(program,", 20)] + [M(s, 20, GREY_B) for s in
                                            ["output to: ...,", "input from: ...,", "pipe: ...,", "folder: ...,", "settings: ...,", "user: ...,", "limits: ...)"]]
        for i, m in enumerate(form):
            left_at(m, form_x + (0.6 if i else 0), form_top - 0.36 * i)
        ff = VGroup(*form)
        form_x_mark = tick(False, 0.5).move_to(ff.get_center())
        self.steps("The simplest design is one request to the kernel: spawn this program. It works for plain ls.", [
            (lambda: [*self.uncap(), FadeIn(form[0], shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("Now you want the output in a file, so spawn needs a setting for where output goes. Then one for input. "
                   "One for a pipe that feeds one program into another.", [
            "a setting for",
            (lambda: [FadeIn(form[1], shift=0.1 * DOWN)], 0.4),
            "Then one for input",
            (lambda: [FadeIn(form[2], shift=0.1 * DOWN)], 0.4),
            "One for a pipe",
            (lambda: [FadeIn(form[3], shift=0.1 * DOWN)], 0.4),
        ])
        self.steps("One for the folder to start in, for the settings it inherits, for the user, for the limits. "
                   "Every new kind of setup becomes one more setting, and the form only ever gets longer.", [
            (lambda: [FadeIn(form[4], shift=0.1 * DOWN)], 0.35),
            "for the settings",
            (lambda: [FadeIn(form[5], shift=0.1 * DOWN)], 0.35),
            "for the user",
            (lambda: [FadeIn(form[6], shift=0.1 * DOWN)], 0.35),
            "for the limits",
            (lambda: [FadeIn(form[7], shift=0.1 * DOWN)], 0.35),
            "Every new kind",
            (lambda: self.cap("every new kind of setup: one more setting", RED_M), 0.5),
        ])
        self.steps("Unix took another route in the 1970s, and Linux kept it. Split the job into two calls, and let your own code run in between.", [
            (lambda: [Create(form_x_mark)], 0.5),
            "Split the job",
            (lambda: [FadeOut(ff), FadeOut(form_x_mark), *self.cap("two calls, with your own code in between", WHITE)], 0.7),
        ])

        # ---------------- scene 3: the parent, and fork ----------------
        par = proc(PA, "tinysh", "PID 43")
        pslots = slots(PA)
        parr = out_arrow(PA, TO_TERM_P)
        self.steps("Unix used family words for this, and they fit. Every process has a number, its PID, and a parent: the process that started it. "
                   "Here, the parent is the shell, tinysh, with PID 43.", [
            (lambda: self.uncap(), 0.4),
            "Every process",
            (lambda: [FadeIn(par[0]), FadeIn(par[1]), FadeIn(par[3]), FadeIn(par[4])], 0.7),
            "its PID",
            (lambda: [FadeIn(par[2], shift=0.1 * UP)], 0.4),
            "the parent is the shell",
            (lambda: [FadeIn(pslots), GrowArrow(parr), glow(par[0], WHITE, 1.03)], 0.8),
        ])
        cbox = par.copy()
        cslots = pslots.copy()
        fam = DashedLine(PA + [BW / 2 + 0.08, 0, 0], CH - [BW / 2 + 0.08, 0, 0], dash_length=0.1, stroke_width=2, color=GREY_B)
        fam_t = T("parent → child", 18, GREY_B).move_to([0, PA[1] + 0.3, 0])
        cpid = M("PID 45, parent 43", 18, GREY_B).move_to(CH + [0, 0.1, 0])
        carr = out_arrow(CH, TO_TERM_C)
        self.steps("The first call is fork. It makes a copy of the process that calls it. The child gets a new PID, 45.", [
            (lambda: self.cap("fork: copy the process that calls it", WHITE), 0.5),
            "It makes a copy",
            (lambda: [VGroup(cbox, cslots).animate.shift(CH - PA)], 1.2),
            (lambda: [Create(fam), FadeIn(fam_t)], 0.5),
            "The child gets",
            (lambda: [swap(cbox[2], cpid)], 0.6),
        ])
        cbox[2] = cpid
        self.steps("Everything else starts as a copy of the parent: the code, the memory and the open files.", [
            "the code",
            (lambda: [Indicate(cbox[1], color=YELLOW_M, scale_factor=1.1)], 0.5),
            "the memory",
            (lambda: [LaggedStart(*[glow(p, YELLOW_M, 1.12) for p in cbox[4]], lag_ratio=0.2)], 0.7),
            "the open files",
            (lambda: [glow(cslots[0][1][0], YELLOW_M, 1.12), GrowArrow(carr)], 0.7),
        ])
        self.steps("Here the family picture breaks. No real child is born with their parent's memories. "
                   "This one is, down to the line it was in the middle of.", [
            (lambda: self.cap("where the family picture breaks", GREY_B), 0.5),
            "This one is",
            (lambda: [*self.cap("born with all its parent's memories", YELLOW_M), glow(cbox[0], YELLOW_M, 1.03)], 0.8),
        ], after=0.4)

        # ---------------- scene 4: two answers from one call ----------------
        tag_p = M("fork() returned 45", 18, YELLOW_M).move_to([PA[0], TAG_Y, 0])
        tag_c = M("fork() returned 0", 18, YELLOW_M).move_to([CH[0], TAG_Y, 0])
        self.steps("Both of them come back from the same fork call. The parent gets the child's PID, 45. The child gets 0. "
                   "That's how each one knows which it is.", [
            (lambda: self.uncap(), 0.3),
            "The parent gets",
            (lambda: [FadeIn(tag_p, shift=0.1 * DOWN)], 0.5),
            "The child gets",
            (lambda: [FadeIn(tag_c, shift=0.1 * DOWN)], 0.5),
            "That's how",
            (lambda: [Indicate(tag_p, color=YELLOW_M, scale_factor=1.08), Indicate(tag_c, color=YELLOW_M, scale_factor=1.08)], 0.8),
        ])
        shared = left_at(T("shared", 17, YELLOW_M), CH[0] - 1.78, CH[1] - 0.45)
        cow = page(CH, PAGE_DX[2], YELLOW_M, 0.6)
        self.steps("I know what you're thinking: copying a whole process sounds slow. The kernel doesn't copy at first.", [
            "copying a whole",
            (lambda: [FadeOut(tag_p), FadeOut(tag_c)], 0.4),
            "doesn't copy",
            (lambda: [*[p.animate.set_fill(opacity=0).set_stroke(YELLOW_M) for p in cbox[4]], swap(cbox[3], shared)], 0.7),
        ])
        cbox[3] = shared
        self.steps("Parent and child share the memory, and the kernel copies a page, a 4 KB piece, only when one of them writes to it.", [
            (lambda: [*self.cap("one set of pages, shared"), LaggedStart(*[glow(p, YELLOW_M, 1.12) for p in par[4]], lag_ratio=0.2)], 0.8),
            "only when",
            (lambda: [FadeIn(cow, scale=0.6), *self.cap("copied only when written: one 4 KB page", YELLOW_M)], 0.6),
        ], after=0.4)

        # ---------------- scene 5: the gap ----------------
        carr_f = out_arrow(CH, TO_FILE, YELLOW_M)
        wait_t = T("asleep in wait", 18, GREY_B).move_to([PA[0], TAG_Y, 0])
        mem2 = left_at(T("memory", 17, GREY_B), CH[0] - 1.78, CH[1] - 0.45)
        self.steps("Now the gap, which is the whole point. The child still runs the shell's code, "
                   "so it can change things about itself before it becomes ls.", [
            (lambda: [*self.uncap(), FadeOut(cow), *[p.animate.set_fill(opacity=1).set_stroke(BLUE_M) for p in cbox[4]],
                      swap(cbox[3], mem2)], 0.6),
            "The child still runs",
            (lambda: [Indicate(cbox[1], color=YELLOW_M, scale_factor=1.1)], 0.7),
            "change things",
            (lambda: self.cap("the gap: the child sets itself up before it becomes ls", WHITE), 0.5),
        ])
        cbox[3] = mem2
        self.steps("A process names its open files with small numbers, file descriptors. "
                   "0 is where input comes from, 1 is where output goes, and 2 is for errors.", [
            (lambda: self.cap("file descriptors: small numbers for open files"), 0.5),
            "0 is where",
            (lambda: [*self.cap("0: input"), glow(cslots[0][0][0], YELLOW_M, 1.15)], 0.5),
            "1 is where",
            (lambda: [*self.cap("1: output"), glow(cslots[0][1][0], YELLOW_M, 1.15)], 0.5),
            "2 is for",
            (lambda: [*self.cap("2: errors"), glow(cslots[0][2][0], YELLOW_M, 1.15)], 0.5),
        ])
        self.steps("Right now, the child's 1 points at the terminal. So the child opens listing.txt, and points descriptor 1 at it, "
                   "with a call named dup2. Meanwhile the parent goes to sleep in wait.", [
            (lambda: [*self.uncap(), Indicate(carr, color=YELLOW_M)], 0.7),
            "the child opens",
            (lambda: [glow(fbox[0], YELLOW_M, 1.04)], 0.6),
            "points descriptor 1",
            (lambda: [Transform(carr, carr_f)], 0.8),
            "with a call",
            (lambda: self.cap("dup2: make descriptor 1 the file", WHITE), 0.5),
            "Meanwhile",
            (lambda: [FadeIn(wait_t), par.animate.set_opacity(0.4)], 0.6),
        ])

        # ---------------- scene 6: exec, and a prediction ----------------
        ls_nm = T("ls", 26, PURPLE_M).move_to(CH + [0, 0.55, 0])
        ls_pages = VGroup(*[page(CH, dx, PURPLE_M, 0.45) for dx in PAGE_DX])
        self.steps("Then the child calls exec. The kernel throws away the shell's code and memory inside the child, and loads ls from the disk.", [
            (lambda: self.cap("exec: throw away the program, load a new one", WHITE), 0.5),
            "throws away",
            (lambda: [FadeOut(cbox[4], scale=0.6), FadeOut(cbox[1])], 0.6),
            "and loads ls",
            (lambda: [FadeIn(ls_nm, shift=0.1 * DOWN), LaggedStart(*[FadeIn(p, scale=0.6) for p in ls_pages], lag_ratio=0.2)], 0.8),
        ])
        cbox[1], cbox[4] = ls_nm, ls_pages
        self.steps("Before we look: what did ls keep? The PID, the parent, the open files, or none of them? Pause and guess.", [
            (lambda: self.uncap(), 0.3),
            "The PID",
            (lambda: [glow(cbox[0], YELLOW_M, 1.02)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("All three. It's still PID 45, its parent is still 43, and descriptor 1 still points at listing.txt.", [
            (lambda: [*self.cap("all three", GREEN_M)], 0.4),
            "It's still",
            (lambda: [Indicate(cbox[2], color=GREEN_M, scale_factor=1.12)], 0.6),
            "its parent",
            (lambda: [Indicate(fam_t, color=GREEN_M, scale_factor=1.12), fam.animate.set_color(GREEN_M)], 0.6),
            "descriptor 1 still",
            (lambda: [Indicate(carr, color=GREEN_M), glow(cslots[0][1][0], GREEN_M, 1.15)], 0.7),
        ])
        self.steps("exec doesn't start a new process. It swaps the program inside the same one. "
                   "ls writes its list to descriptor 1, as it always does. The lines land in the file, and ls never knew.", [
            (lambda: [fam.animate.set_color(GREY_B), *self.cap("exec swaps the program inside the same process", WHITE)], 0.6),
            "ls writes",
            (lambda: [FadeOut(flines)], 0.3),
            (lambda: [travel(carr, YELLOW_M, 0.6)], 0.7),
            (lambda: [Create(flines[0]), Create(flines[1])], 0.4),
            (lambda: [travel(carr, YELLOW_M, 0.6)], 0.7),
            (lambda: [Create(flines[2]), Create(flines[3])], 0.4),
            "ls never knew",
            (lambda: self.cap("fork makes a copy, exec swaps the program", YELLOW_M), 0.6),
        ], after=0.4)
        print(f"POSTER {self.renderer.time:.1f}")

        # ---------------- scene 7: waiting up ----------------
        st = M("exit status 0", 18, GREEN_M).move_to(CH + [0, -0.45, 0])
        self.steps("The third call closes the loop. ls ends with exit status 0, which means success.", [
            (lambda: self.uncap(), 0.3),
            "ls ends",
            (lambda: [FadeOut(cbox[4]), FadeOut(cbox[3]), FadeIn(st)], 0.7),
            "which means success",
            (lambda: self.cap("exit status 0: success"), 0.5),
        ])
        self.steps("The kernel frees its memory, but keeps a small record: who it was, and how it ended.", [
            "frees its memory",
            (lambda: [FadeOut(carr), FadeOut(cslots), cbox[1].animate.set_color(GREY_B)], 0.6),
            "keeps a small record",
            (lambda: [cbox[0].animate.set_stroke(GREY_C), *self.cap("a small record: who it was, and how it ended")], 0.6),
        ])
        msg = Line(CH - [BW / 2 + 0.08, 0, 0], PA + [BW / 2 + 0.08, 0, 0])
        woke = M("wait: 45, status 0", 18, GREEN_M).move_to([PA[0], TAG_Y, 0])
        self.steps("It wakes the parent, like a parent waiting up to hear how the evening went.", [
            (lambda: [travel(msg, GREEN_M, 0.8)], 0.9),
            (lambda: [par.animate.set_opacity(1), *self.uncap()], 0.5),
            "waiting up",
            (lambda: [glow(par[0], WHITE, 1.03)], 0.7),
        ])
        done = M("[pid 45 exited with status 0]", 22, GREEN_M)
        left_at(done, PROMPT[0], PROMPT[1])
        self.steps("wait hands the parent two numbers, 45 and status 0, and only then does the kernel delete the record.", [
            (lambda: [swap(wait_t, woke)], 0.6),
            "only then",
            (lambda: [FadeOut(VGroup(cbox[0], cbox[1], cbox[2], st)), FadeOut(fam), FadeOut(fam_t)], 0.7),
            (lambda: [swap(prompt, done)], 0.6),
        ])
        self.steps("Between those two moments, the dead child has a grim name. That's the next section.", [
            (lambda: self.cap("between exit and wait: a grim name, in the next section"), 0.6),
        ], after=0.5)

        # ---------------- scene 8: two rules ----------------
        code = [code_line(i) for i in range(len(CODE))]
        hl = SurroundingRectangle(code[4], color=YELLOW_M, buff=0.08, corner_radius=0.05)
        self.steps("Two rules come with this. A successful exec never returns, because the code that called it is gone.", [
            (lambda: [*self.uncap(), FadeOut(woke), LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in code], lag_ratio=0.12)], 1.4),
            "never returns",
            (lambda: [Create(hl), *self.cap("exec returns only when it fails", WHITE)], 0.6),
        ])
        hl2 = SurroundingRectangle(code[5], color=RED_M, buff=0.08, corner_radius=0.05)
        self.steps("So the line after exec runs only if exec failed, and it should exit at once. "
                   "tinysh exits with 127, the number real shells use for command not found.", [
            "the line after",
            (lambda: [Transform(hl, hl2)], 0.6),
            "tinysh exits",
            (lambda: [Indicate(code[5][0], color=RED_M, scale_factor=1.06), *self.cap("127: command not found", RED_M)], 0.8),
        ])
        hl3 = SurroundingRectangle(code[7], color=GREEN_M, buff=0.08, corner_radius=0.05)
        self.steps("And a parent should always wait for its children. "
                   "That's where the shell's dollar question mark, and Java's Process.waitFor, get their number.", [
            (lambda: [Transform(hl, hl3), *self.cap("a parent always waits for its children", WHITE)], 0.6),
            "dollar question mark",
            (lambda: self.cap("the shell's $? and Java's Process.waitFor() read this number"), 0.5),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        steps_hl = [code[0], VGroup(code[2], code[3]), code[4], code[7]]
        self.steps("So how did the shell put ls's list in a file, without ls knowing? "
                   "It copied itself, set up the copy, swapped in ls, and waited for the news.", [
            (lambda: [*self.uncap(), FadeOut(hl)], 0.4),
            "It copied",
            (lambda: [Indicate(steps_hl[0], color=YELLOW_M, scale_factor=1.04), *self.cap("copy", YELLOW_M)], 0.5),
            "set up",
            (lambda: [Indicate(steps_hl[1], color=YELLOW_M, scale_factor=1.04), *self.cap("copy, set up", YELLOW_M)], 0.5),
            "swapped in",
            (lambda: [Indicate(steps_hl[2], color=YELLOW_M, scale_factor=1.04), *self.cap("copy, set up, swap", YELLOW_M)], 0.5),
            "and waited",
            (lambda: [Indicate(steps_hl[3], color=YELLOW_M, scale_factor=1.04), *self.cap("copy, set up, swap, wait", YELLOW_M)], 0.5),
        ])
        gap = SurroundingRectangle(VGroup(code[2], code[3]), color=YELLOW_M, buff=0.1, corner_radius=0.06)
        self.steps("The gap between fork and exec is where all the setup lives, so no call ever needs a setting for it.", [
            "The gap",
            (lambda: [Create(gap)], 0.6),
            "no call ever",
            (lambda: self.cap("the setup lives in the gap, so no call needs a setting for it", WHITE), 0.6),
        ], after=0.5)
        y3, y4 = code[3].get_center()[1], code[4].get_center()[1]
        n3, n4 = code[3].copy().shift((y4 - y3) * UP), code[4].copy().shift((y3 - y4) * UP)
        self.steps("One quick check. Suppose the child called exec first, and pointed descriptor 1 at the file after it. "
                   "Where would the list go? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(gap)], 0.4),
            "Suppose the child",
            (lambda: [Succession(FadeOut(VGroup(code[3], code[4]), run_time=0.4), FadeIn(VGroup(n3, n4), run_time=0.5))], 0.9),
            "Where would",
            (lambda: [glow(fbox[0], WHITE, 1.04), glow(term[0], WHITE, 1.04)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        code[3], code[4] = n3, n4
        never = VGroup(code[3], code[5], code[6])
        nx = tick(False, 0.14).next_to(code[3][0], LEFT, buff=0.18)
        tl2 = lines_in(TM, TM_W, 4)
        self.steps("To the terminal. After a successful exec, the shell's code is gone, so that setup never runs. Setup goes in the gap.", [
            (lambda: [*self.uncap(), LaggedStart(*[Create(l) for l in tl2], lag_ratio=0.3), glow(term[0], YELLOW_M, 1.04)], 0.8),
            "the shell's code is gone",
            (lambda: [never.animate.set_opacity(0.3), Create(nx)], 0.6),
            "Setup goes",
            (lambda: self.cap("setup goes in the gap", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.wait(2.0)
