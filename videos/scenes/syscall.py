from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\bSystem\.out\.println\b", "System dot out dot print line"),
    (r"\bx86-64\b", "x eighty-six sixty-four"),
    (r"\barm64\b", "arm sixty-four"),
    (r"\bx(\d)\b", lambda m: "ex " + "zero one two three four five six seven eight nine".split()[int(m.group(1))]),
    (r"\bsvc\b", "S V C"),
    (r"\beret\b", "E ret"),
    (r"\berrno\b", "air no"),
    (r"\bENOENT\b", "E no ent"),
    (r"\bgetpid\b", "get pid"),
    (r"\bsyscall\b", "sys call"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
UB_C, KB_C, BAND_W, BAND_H = np.array([0, 2.4, 0]), np.array([0, -0.4, 0]), 13.2, 2.2   # user band, kernel band
GAP_Y = 1.0                                     # the glass between the bands
HW_Y = -2.1                                     # the hardware strip
CAP_Y, BAR_Y = -2.9, -3.35
PROG_C, PROG_W, PROG_H = np.array([-3.6, 2.35, 0]), 4.6, 1.1
REG_C = np.array([3.3, 2.35, 0])
ENT_C, ENT_W, ENT_H = np.array([-3.6, 0.3, 0]), 1.8, 0.5
TBL_C = np.array([-0.3, -0.45, 0])
WR_C, WR_W, WR_H = np.array([3.5, -0.05, 0]), 3.0, 0.6
CHK_X, CHK_Y = 1.5, [-0.72, -1.15]
TERM_C = np.array([3.5, HW_Y, 0])
TRAP_X, RET_X = -3.85, -3.35
P_BOT, E_TOP = PROG_C[1] - PROG_H / 2, ENT_C[1] + ENT_H / 2


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


def varrow(x, y0, y1, color, sw=4):
    return Arrow([x, y0, 0], [x, y1, 0], buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.18)


def node(lines, c, w, h, color=WHITE, fill=None):
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3)
    r.set_fill(BLACK if fill is None else fillc(fill), 1).move_to(c)
    g = VGroup(*lines).arrange(DOWN, buff=0.12).move_to(c)
    return VGroup(r, *g)


# ---- the pieces ----
def program(code):
    return node([T("your program", 20, GREY_B), fit(M(code, 22), PROG_W - 0.4)], PROG_C, PROG_W, PROG_H)


REG_POS = {"x8": REG_C + [-1.05, 0.05, 0], "x0": REG_C + [1.05, 0.05, 0], "x1": REG_C + [-1.05, -0.6, 0], "x2": REG_C + [1.05, -0.6, 0]}


def reg(name, val, color=None):
    edge = color or BLUE_M
    r = RoundedRectangle(corner_radius=0.08, width=1.9, height=0.52, stroke_color=edge, stroke_width=2.5)
    r.set_fill(fillc(edge, 0.16), 1).move_to(REG_POS[name])
    return VGroup(r, fit(M(f"{name} = {val}", 20, color or WHITE), 1.75).move_to(REG_POS[name]))


def hw_box(label, x, w):
    return node([T(label, 18, GREY_B)], [x, HW_Y, 0], w, 0.6, GREY_B)


def table():
    title = T("system call table", 18, GOLD_M)
    rows = VGroup(*[M(f"{n}  {name}", 20, GREY_B) for n, name in [(63, "read"), (64, "write"), (65, "readv")]]).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
    g = VGroup(title, rows).arrange(DOWN, buff=0.2)
    r = RoundedRectangle(corner_radius=0.12, width=g.width + 0.6, height=g.height + 0.4, stroke_color=GOLD_M, stroke_width=2.5)
    r.set_fill(fillc(GOLD_M, 0.1), 1)
    return VGroup(r, g).move_to(TBL_C), rows


def check_line(s, k):
    t = tick(True, 0.13)
    txt = T(s, 18)
    g = VGroup(t, txt).arrange(RIGHT, buff=0.16)
    return left_at(g, CHK_X, CHK_Y[k])


class Syscall(Base):
    """os-01, section 2. Inside one println: the C library's write(1, "ok\\n", 3) fills in a slip in registers (x8 = 64,
    x0 to x2), svc traps through the one door the kernel chose, the kernel looks up entry 64, checks the descriptor and
    the buffer's address, copies the bytes, puts 3 in x0 and returns with eret. Errors come back negative (-2, ENOENT).
    The lesson's bank: customer, vault, teller, glass, slip. It breaks on speed: about 150 ns a trip."""

    def set_reg(self, name, val, color=None):
        new = reg(name, val, color)
        old, self.regs[name] = self.regs[name], new
        return [swap(old, new)]

    def construct(self):
        self.capm = None
        self.regs = {k: None for k in REG_POS}
        self.title_card("One door into the kernel", "how a program asks for something, and gets an answer back")

        # ---------------- scene 1: the hook ----------------
        prog = program('System.out.println("ok")')
        nic, disk = hw_box("network card", -2.4, 2.3), hw_box("disk", 0.4, 1.5)
        term = node([T("terminal", 18, GREY_B)], TERM_C, 2.6, 0.6, GREY_B)
        hw_l = left_at(T("hardware", 20, GREY_B), -6.35, HW_Y)
        self.steps("In Java, System.out.println looks like any other method call. It returns almost at once.", [
            (lambda: [FadeIn(prog, shift=0.2 * DOWN)], 0.8),
            "It returns",
            (lambda: [glow(prog[0], WHITE, 1.03)], 0.7),
        ])
        direct = Arrow(PROG_C + [PROG_W / 2 - 0.3, -PROG_H / 2, 0], TERM_C + [-0.9, 0.3, 0], buff=0.1, stroke_width=3, color=GREY_B,
                       max_tip_length_to_length_ratio=0.05)
        cross = tick(False, 0.3).move_to(direct.point_from_proportion(0.5))
        self.steps("But no program on your laptop can touch the screen, the disk or the network. Not even this one.", [
            (lambda: [FadeIn(hw_l), LaggedStart(FadeIn(term), FadeIn(disk), FadeIn(nic), lag_ratio=0.3)], 1.0),
            "Not even",
            (lambda: [GrowArrow(direct)], 0.6),
            (lambda: [direct.animate.set_color(RED_M), Create(cross)], 0.5),
        ])
        self.steps("So what happens inside that one line? It ends up asking the kernel, "
                   "the one program that may touch the hardware. Let's follow that request in, and back out.", [
            (lambda: self.cap("what happens inside that one line?", WHITE), 0.5),
            "It ends up",
            (lambda: [FadeOut(direct), FadeOut(cross)], 0.5),
            "asking the kernel",
            (lambda: self.cap("the kernel: the one program that may touch the hardware"), 0.5),
        ])

        # ---------------- scene 2: the bank, mapped ----------------
        ub = RoundedRectangle(corner_radius=0.15, width=BAND_W, height=BAND_H, stroke_color=BLUE_M, stroke_width=2).move_to(UB_C)
        ub.set_fill(BLUE_M, 0.07).set_z_index(-10)
        kb = RoundedRectangle(corner_radius=0.15, width=BAND_W, height=BAND_H, stroke_color=GOLD_M, stroke_width=2).move_to(KB_C)
        kb.set_fill(GOLD_M, 0.03).set_z_index(-10)
        ul = left_at(T("user mode", 22, BLUE_M), -6.35, UB_C[1] + BAND_H / 2 - 0.3)
        kl = left_at(T("kernel mode", 22, GOLD_M), -6.35, KB_C[1] - BAND_H / 2 + 0.3)
        self.steps("First, a picture from earlier in this lesson: a bank. Customers can't walk into the vault. They fill in a slip, "
                   "push it under the glass, and a teller checks it, does the work and slides back the result.", [
            (lambda: [*self.uncap(), FadeIn(ub), FadeIn(ul), FadeIn(kb), FadeIn(kl)], 1.0),
            "fill in a slip",
            (lambda: [glow(prog[0], WHITE, 1.03)], 0.7),
            "a teller checks",
            (lambda: [glow(kb, GOLD_M, 1.01)], 0.8),
        ])
        t_cust = left_at(T("the customer", 20, GREY_B), PROG_C[0] + PROG_W / 2 + 0.3, PROG_C[1])
        t_vault = left_at(T("the vault", 20, GREY_B), TERM_C[0] + 1.6, HW_Y)
        t_teller = T("the teller", 30, GOLD_M).move_to([0.6, KB_C[1], 0])
        self.steps("Map it. Your program is the customer. The vault is the hardware. The teller is the kernel, "
                   "working in kernel mode, where the processor runs every instruction.", [
            "Your program",
            (lambda: [FadeIn(t_cust, shift=0.1 * DOWN)], 0.5),
            "The vault",
            (lambda: [FadeIn(t_vault, shift=0.1 * LEFT), glow(term[0], WHITE, 1.04), glow(disk[0], WHITE, 1.04), glow(nic[0], WHITE, 1.04)], 0.8),
            "The teller",
            (lambda: [FadeIn(t_teller, shift=0.1 * UP)], 0.6),
            "where the processor",
            (lambda: [Indicate(kl, color=GOLD_M, scale_factor=1.1)], 0.8),
        ])
        t_glass = T("the glass", 20, GREY_B).move_to([1.2, GAP_Y, 0])
        self.steps("The glass is user mode. In user mode, the processor refuses the instructions that talk to devices. "
                   "And the slip is a system call: a request with a number that names the service.", [
            (lambda: [FadeIn(t_glass), Indicate(ul, color=BLUE_M, scale_factor=1.1)], 0.8),
            "And the slip",
            (lambda: self.cap("the slip: a system call, a request with a number that names the service", WHITE), 0.6),
        ])

        # ---------------- scene 3: the obvious idea, broken ----------------
        kc_r = RoundedRectangle(corner_radius=0.12, width=3.9, height=1.75, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.1), 1)
        kc_r.move_to([1.2, -0.4, 0])
        kc_lines = [T("kernel code for write", 18, GOLD_M), T("1  check: is this allowed?", 19), T("2  do the work", 19), T("3  hand back the result", 19)]
        for i, m in enumerate(kc_lines):
            left_at(m, kc_r.get_left()[0] + 0.3, 0.2 - 0.4 * i)
        kcode = VGroup(kc_r, *kc_lines)
        call = Arrow(PROG_C + [1.2, -PROG_H / 2, 0], kc_lines[1].get_left() + [-0.05, 0, 0], buff=0.1, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.08)
        jump = Arrow(PROG_C + [0.4, -PROG_H / 2, 0], kc_lines[2].get_left() + [-0.05, 0, 0], buff=0.1, stroke_width=3, color=RED_M,
                     max_tip_length_to_length_ratio=0.08)
        jx = tick(False, 0.2).move_to(jump.point_from_proportion(0.75))
        self.steps("So how does the slip get under the glass? The obvious idea is an ordinary function call. "
                   "The kernel is code. Jump to its write function and run it.", [
            (lambda: [*self.uncap(), FadeOut(t_cust), FadeOut(t_vault), FadeOut(t_teller), FadeOut(t_glass)], 0.5),
            "The kernel is code",
            (lambda: [FadeIn(kcode, shift=0.1 * UP)], 0.7),
            "Jump to",
            (lambda: [GrowArrow(call)], 0.7),
        ])
        self.steps("But look at what that allows. The kernel's code checks permissions first, then does the work. "
                   "If a program may jump to any address, it can land right past the check, and run the rest with full power.", [
            "checks permissions",
            (lambda: [Indicate(kc_lines[1], color=YELLOW_M, scale_factor=1.06)], 0.8),
            "land right past",
            (lambda: [FadeOut(call), GrowArrow(jump)], 0.7),
            (lambda: [kc_lines[1].animate.set_opacity(0.25)], 0.4),
            "full power",
            (lambda: [Indicate(kc_lines[2], color=RED_M, scale_factor=1.06), Indicate(kc_lines[3], color=RED_M, scale_factor=1.06)], 0.8),
        ])
        self.steps("That's a customer who climbs over the counter. Banks have a word for that customer, and it isn't customer. "
                   "So the program must never choose where it lands.", [
            (lambda: [Create(jx), *self.cap("a customer who climbs over the counter", RED_M)], 0.6),
            "So the program",
            (lambda: self.cap("the program must never choose where it lands", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 4: one door, the trap ----------------
        ent = node([T("entry point", 18, GOLD_M)], ENT_C, ENT_W, ENT_H, GOLD_M, GOLD_M)
        saved = T("place saved", 18, YELLOW_M).move_to([-0.35, PROG_C[1] - 0.25, 0])
        preview = DashedLine([TRAP_X, P_BOT - 0.05, 0], [TRAP_X, E_TOP + 0.05, 0], dash_length=0.1, stroke_width=3, color=YELLOW_M)
        self.steps("What we want is one door, and the kernel decides where it leads. "
                   "The processor has exactly that: one special instruction that does three things at once.", [
            (lambda: [*self.uncap(), FadeOut(kcode), FadeOut(jump), FadeOut(jx)], 0.6),
            "one door",
            (lambda: [FadeIn(ent, scale=0.8)], 0.6),
            (lambda: [glow(ent[0], YELLOW_M, 1.06)], 0.7),
            "three things",
            (lambda: self.cap("one special instruction, three things at once", WHITE), 0.5),
        ])
        self.steps("It switches to kernel mode. It saves where the program was. "
                   "And it jumps to an entry point the kernel picked when the computer started.", [
            (lambda: [*self.cap("1. switch to kernel mode", WHITE), ub.animate.set_fill(BLUE_M, 0.02), kb.animate.set_fill(GOLD_M, 0.1)], 0.6),
            "It saves",
            (lambda: [*self.cap("2. save where the program was", WHITE), FadeIn(saved, shift=0.1 * LEFT)], 0.6),
            "And it jumps",
            (lambda: [*self.cap("3. jump to the entry point the kernel chose", WHITE), Create(preview)], 0.7),
            "the computer started",
            (lambda: [glow(ent[0], YELLOW_M, 1.06)], 0.7),
        ])
        self.steps("The program can't choose where it lands. This switch is called a trap. "
                   "On arm64, the chip family in an Apple Silicon Mac, the instruction is svc.", [
            "This switch",
            (lambda: self.cap("a trap: one door, and the kernel chose where it leads", YELLOW_M), 0.6),
            "On arm64",
            (lambda: [*self.cap("arm64: svc        (x86-64: syscall)", WHITE), FadeOut(preview), FadeOut(saved),
                      ub.animate.set_fill(BLUE_M, 0.07), kb.animate.set_fill(GOLD_M, 0.03)], 0.7),
        ])

        # ---------------- scene 5: the slip, in registers ----------------
        prog2 = program('write(1, "ok\\n", 3)')
        self.steps("One door for everything means the slip must say which service, and with what. "
                   "Let's shrink it to the smallest request: write 3 bytes, o, k and a newline, to file descriptor 1.", [
            (lambda: self.uncap(), 0.4),
            "Let's shrink",
            (lambda: [swap(prog[2], prog2[2])], 0.7),
        ])
        prog[2] = prog2[2]
        self.steps("A file descriptor is a small number a program uses to name something it has open. "
                   "1 is standard output, usually your terminal window.", [
            (lambda: self.cap("file descriptor: a small number for something the program has open", WHITE), 0.6),
            "1 is standard",
            (lambda: [*self.cap("1 = standard output, usually your terminal window"), glow(term[0], WHITE, 1.05)], 0.8),
        ])
        reg_t = T("registers", 20, GREY_B).move_to(REG_C + [-0.55, 0.7, 0])
        slip_t = T("the slip", 18, YELLOW_M).next_to(reg_t, RIGHT, buff=0.5)
        self.steps("The C library's write function, still in user mode, "
                   "fills in the slip, in registers: the few dozen small storage slots inside the processor.", [
            (lambda: [*self.uncap(), glow(prog[0], WHITE, 1.03)], 0.7),
            "still in user mode",
            (lambda: [Indicate(ul, color=BLUE_M, scale_factor=1.1)], 0.7),
            "in registers",
            (lambda: [FadeIn(reg_t), FadeIn(slip_t)], 0.6),
            "the few dozen",
            (lambda: self.cap("registers: a few dozen small storage slots inside the processor"), 0.5),
        ])
        self.steps("The service number goes in x8. Like the form number printed on a bank slip, 64 means write. "
                   "The three inputs go in x0, x1 and x2. x1 holds the address of the bytes, called the buffer.", [
            (lambda: [*self.uncap(), *self.set_reg("x8", "64")], 0.6),
            "64 means write",
            (lambda: [Indicate(self.regs["x8"][1], color=YELLOW_M, scale_factor=1.15)], 0.7),
            "The three inputs",
            (lambda: self.set_reg("x0", "1"), 0.4),
            (lambda: self.set_reg("x1", "buf"), 0.4),
            (lambda: self.set_reg("x2", "3"), 0.4),
            "x1 holds",
            (lambda: [*self.cap("x1: the address of the bytes, the buffer"), Indicate(self.regs["x1"][1], color=YELLOW_M, scale_factor=1.15)], 0.8),
        ])

        # ---------------- scene 6: through the door ----------------
        trap = varrow(TRAP_X, P_BOT, E_TOP, YELLOW_M)
        trap_l = right_at(M("svc #0", 20, YELLOW_M), TRAP_X - 0.2, GAP_Y)
        tbl, rows = table()
        wr = node([T("the code for write", 20, GOLD_M)], WR_C, WR_W, WR_H, GOLD_M, GOLD_M)
        hi = SurroundingRectangle(rows[1], color=YELLOW_M, buff=0.07, corner_radius=0.05)
        look = Arrow(rows[1].get_right() + [0.35, 0, 0], wr.get_left(), buff=0.1, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.12)
        saved2 = T("place saved", 18, YELLOW_M).move_to([-0.35, PROG_C[1] - 0.25, 0])
        self.steps("Then it runs svc. The processor saves its place, switches to kernel mode and lands at the entry point.", [
            (lambda: [*self.uncap(), FadeIn(trap_l)], 0.5),
            "saves its place",
            (lambda: [FadeIn(saved2, shift=0.1 * LEFT)], 0.4),
            "switches to kernel",
            (lambda: [GrowArrow(trap), ub.animate.set_fill(BLUE_M, 0.02), kb.animate.set_fill(GOLD_M, 0.1)], 0.9),
            "lands at",
            (lambda: [glow(ent[0], YELLOW_M, 1.06)], 0.6),
        ])
        self.steps("The kernel reads x8, finds entry 64 in its system call table, and runs the code for write.", [
            (lambda: [Indicate(self.regs["x8"][1], color=YELLOW_M, scale_factor=1.15)], 0.6),
            "finds entry",
            (lambda: [FadeIn(tbl)], 0.5),
            (lambda: [rows[1].animate.set_color(WHITE), Create(hi)], 0.5),
            "runs the code",
            (lambda: [GrowArrow(look), FadeIn(wr, shift=0.1 * RIGHT)], 0.7),
        ])

        # ---------------- scene 7: what could x1 hold? ----------------
        self.steps("Before it copies anything, look at x1 again. It's an address, and the program wrote it. "
                   "What could a sneaky program put there? Pause and guess.", [
            "look at x1",
            (lambda: [glow(self.regs["x1"][0], YELLOW_M, 1.08)], 0.7),
            "the program wrote",
            (lambda: [glow(prog[0], WHITE, 1.03)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        bad = T("x1: the kernel's own memory", 18, RED_M).move_to([REG_POS["x1"][0] + 0.6, GAP_Y, 0])
        self.steps("The address of the kernel's own memory. Then the kernel would write out its own secrets.", [
            (lambda: [*self.uncap(), *self.set_reg("x1", "buf", RED_M), FadeIn(bad, shift=0.1 * DOWN)], 0.7),
            "its own secrets",
            (lambda: [*self.cap("the kernel's own memory, written out for anyone", RED_M), glow(kb, RED_M, 1.01)], 0.8),
        ])
        c1, c2 = check_line("descriptor 1 is open for writing", 0), check_line("the buffer is the program's memory", 1)
        self.steps("So the code for write checks first. Is descriptor 1 open for writing? Is the buffer really the program's own memory? "
                   "An address from user mode could point anywhere. The kernel checks every one.", [
            (lambda: [*self.uncap(), *self.set_reg("x1", "buf"), FadeOut(bad)], 0.6),
            "Is descriptor 1",
            (lambda: [FadeIn(c1, shift=0.1 * RIGHT), Indicate(self.regs["x0"][1], color=YELLOW_M, scale_factor=1.15)], 0.7),
            "Is the buffer",
            (lambda: [FadeIn(c2, shift=0.1 * RIGHT), Indicate(self.regs["x1"][1], color=YELLOW_M, scale_factor=1.15)], 0.7),
            "An address from",
            (lambda: self.cap("an address from user mode could point anywhere: the kernel checks every one", WHITE), 0.6),
        ])

        # ---------------- scene 8: back out ----------------
        copy = varrow(WR_C[0], WR_C[1] - WR_H / 2 - 0.05, HW_Y + 0.35, GOLD_M, 3)
        okt = M("ok", 22, YELLOW_M).move_to(TERM_C + [0.85, 0, 0])
        ret = varrow(RET_X, E_TOP, P_BOT, GREEN_M)
        ret_l = left_at(M("eret", 20, GREEN_M), RET_X + 0.2, GAP_Y)
        self.steps("Only then does it copy the 3 bytes out to the terminal. It puts the result in x0: 3 bytes written.", [
            (lambda: [*self.uncap(), FadeOut(c1), FadeOut(c2)], 0.4),
            "copy the 3 bytes",
            (lambda: [GrowArrow(copy), Indicate(self.regs["x2"][1], color=YELLOW_M, scale_factor=1.15)], 0.6),
            (lambda: [term[1].animate.shift(0.45 * LEFT), FadeIn(okt, shift=0.2 * DOWN), glow(term[0], YELLOW_M, 1.05)], 0.6),
            "It puts the result",
            (lambda: self.set_reg("x0", "3", GREEN_M), 0.6),
        ])
        self.steps("Then it runs eret, short for exception return. "
                   "The processor drops back to user mode, at the instruction right after svc.", [
            (lambda: [FadeIn(ret_l)], 0.5),
            "drops back",
            (lambda: [GrowArrow(ret), ub.animate.set_fill(BLUE_M, 0.07), kb.animate.set_fill(GOLD_M, 0.03)], 0.9),
            "right after svc",
            (lambda: [FadeOut(saved2, shift=0.1 * RIGHT)], 0.5),
        ])
        self.steps("The C library returns 3, and your program carries on. It never touched the hardware.", [
            (lambda: [glow(prog[0], GREEN_M, 1.03), Indicate(self.regs["x0"][1], color=GREEN_M, scale_factor=1.15)], 0.8),
            "It never touched",
            (lambda: [*self.cap("the program never touched the hardware", WHITE)], 0.5),
        ], after=0.4)
        print(f"POSTER {self.renderer.time:.1f}")

        # ---------------- scene 10: where the bank breaks, and the cost ----------------
        cost1 = left_at(T("one trip in and out: about 150 ns", 19, YELLOW_M), CHK_X, CHK_Y[0])
        cost2 = left_at(T("a million trips: about 150 ms", 19, YELLOW_M), CHK_X, CHK_Y[1])
        self.steps("Here the bank picture breaks. A teller takes minutes, and serves other people while you wait. "
                   "There's no queue here, and no pen on a little chain.", [
            (lambda: [FadeOut(copy), *self.cap("where the bank picture breaks")], 0.6),
            "A teller takes",
            (lambda: self.cap("a teller: minutes, and a queue"), 0.5),
            "There's no queue",
            (lambda: self.cap("here: no queue, and no pen on a little chain"), 0.5),
        ])
        self.steps("The kernel does the work on your program's own processor, and it's quick. In the lab box, one tiny call, getpid, which asks for the program's own process number, "
                   "takes about 150 nanoseconds.", [
            (lambda: [*self.cap("the kernel works on your program's own processor", WHITE), glow(kb, GOLD_M, 1.01)], 0.8),
            "one tiny call",
            (lambda: self.cap("getpid: what's my process number?"), 0.6),
            "takes about",
            (lambda: [FadeIn(cost1, shift=0.1 * RIGHT), Indicate(trap, color=YELLOW_M), Indicate(ret, color=GREEN_M)], 0.9),
        ])

        def pulses(n):
            seq = []
            for _ in range(n):
                seq += [Indicate(trap, color=YELLOW_M, scale_factor=1.1, run_time=0.3), Indicate(ret, color=GREEN_M, scale_factor=1.1, run_time=0.3)]
            return [Succession(*seq)]

        self.steps("A nanosecond is a billionth of a second. Once, that's nothing. "
                   "A million times, it's about 150 milliseconds spent going in and out.", [
            (lambda: self.cap("a nanosecond: a billionth of a second"), 0.5),
            "A million times",
            (lambda: [FadeIn(cost2, shift=0.1 * RIGHT), *self.uncap()], 0.6),
            (lambda: pulses(4), 2.4),
        ])
        self.steps("So a program that writes each line of its notes straight to a file pays the trip for every line. "
                   "Gather small writes into bigger ones, and cross less often.", [
            (lambda: self.cap("one write per line: one trip per line"), 0.5),
            "Gather small",
            (lambda: self.cap("gather small writes into bigger ones, and cross less often", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 11: the moral, and a check ----------------
        self.steps("So what happens inside that one print? The library fills in a slip in the registers, svc takes it through the one door, "
                   "and the kernel checks everything before it answers in x0.", [
            (lambda: [*self.uncap(), FadeOut(cost1), FadeOut(cost2)], 0.5),
            "The library fills",
            (lambda: [LaggedStart(*[glow(self.regs[k][0], YELLOW_M, 1.08) for k in ("x8", "x0", "x1", "x2")], lag_ratio=0.2)], 0.9),
            "svc takes it",
            (lambda: [Indicate(trap, color=YELLOW_M), glow(ent[0], YELLOW_M, 1.06)], 0.8),
            "the kernel checks",
            (lambda: [glow(wr[0], GOLD_M, 1.04)], 0.7),
            "it answers",
            (lambda: [Indicate(ret, color=GREEN_M), Indicate(self.regs["x0"][1], color=GREEN_M, scale_factor=1.15)], 0.8),
        ])
        self.steps("One door, one slip, and every address checked.", [
            (lambda: self.cap("one door, one slip, every address checked", YELLOW_M, 30), 0.6),
        ], after=0.6)
        self.steps("One quick check. Suppose the slip says 63 in x8, instead of 64. Which service does the kernel run? "
                   "Pause and look at the table.", [
            (lambda: [*self.uncap(), rows[1].animate.set_color(GREY_B), FadeOut(hi)], 0.4),
            "Suppose the slip",
            (lambda: self.set_reg("x8", "63", YELLOW_M), 0.6),
            "Pause and look",
            (lambda: self.cap("pause and look at the table", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        hi63 = SurroundingRectangle(rows[0], color=GREEN_M, buff=0.07, corner_radius=0.05)
        self.steps("Read. Entry 63 is read. The number on the slip picks the service, and the program never picks the address.", [
            (lambda: [*self.uncap(), rows[0].animate.set_color(WHITE), Create(hi63)], 0.6),
            "The number on the slip",
            (lambda: [Indicate(self.regs["x8"][1], color=YELLOW_M, scale_factor=1.15), glow(tbl[0], GOLD_M, 1.03)], 0.8),
            "never picks",
            (lambda: [glow(ent[0], YELLOW_M, 1.06)], 0.7),
        ], after=0.3)
        self.play(*self.cap("one door, one slip, every address checked", YELLOW_M, 30), run_time=0.6)
        self.wait(2.0)
