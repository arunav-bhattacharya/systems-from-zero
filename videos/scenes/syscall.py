from sfz import *

SAY.insert(0, (r"\bx([0-9])\b", lambda m: "ex " + "zero one two three four five six seven eight nine".split()[int(m.group(1))]))
SAY.insert(0, (r"\bsvc\b", "S V C"))
SAY.insert(0, (r"\beret\b", "E ret"))

def flash(m, color, s=1.08):
    """Indicate for solid-filled boxes: grow and recolour the outline, then back, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)



class Syscall(VoiceScene):
    """os-01: write(1, "ok\\n", 3) crosses from user mode into the kernel and back, and what the crossing costs."""

    def seq(self, text, *steps, after=0.25):
        """Speak one line and play several animation steps inside it. A step is (anims or a function
        returning anims, run_time), or a number of seconds to wait."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        used = 0.0
        for st in steps:
            if isinstance(st, (int, float)):
                self.wait(st)
                used += st
                continue
            anims, rt = st
            anims = anims() if callable(anims) else anims
            self.play(*anims, run_time=rt)
            used += rt
        if used > dur + 0.05:
            print(f"WARNING: steps {used:.1f}s longer than line {dur:.1f}s: {text[:40]}")
        if dur - used > 0.02:
            self.wait(dur - used)
        if after:
            self.wait(after)

    def construct(self):
        self.title_card("A system call crosses into the kernel", "write(), step by step")

        # three bands: user mode, kernel mode, hardware
        ub = RoundedRectangle(corner_radius=0.15, width=13.2, height=3.0, stroke_color=BLUE_M, stroke_width=2).move_to([0, 1.95, 0])
        kb = RoundedRectangle(corner_radius=0.15, width=13.2, height=2.7, stroke_color=GOLD_M, stroke_width=2).move_to([0, -1.1, 0])
        ub.set_fill(BLUE_M, 0.08)
        kb.set_fill(GOLD_M, 0.03)
        ul = T("user mode", 22, BLUE_M).move_to([-6.3, 3.1, 0], aligned_edge=LEFT)
        kl = T("kernel mode", 22, GOLD_M).move_to([-6.3, -0.1, 0], aligned_edge=LEFT)
        hl = T("hardware", 22, GREY_B).move_to([-6.3, -3.05, 0], aligned_edge=LEFT)
        term = box("terminal", GREY_B, size=22, h=0.7).move_to([0.45, -3.05, 0])

        code = M('write(1, "ok\\n", 3)', 26)
        prog_t = T("your program", 20, GREY_B)
        pg = VGroup(prog_t, code).arrange(DOWN, buff=0.18)
        prog_r = RoundedRectangle(corner_radius=0.12, width=pg.width + 0.6, height=pg.height + 0.45, stroke_color=WHITE, stroke_width=3)
        prog_r.set_fill(BLACK, 1)
        prog = VGroup(prog_r, pg).move_to([-3.0, 2.0, 0])

        self.beat("Your program wants to print ok and a newline. That's three bytes, written to file descriptor 1, the program's standard output.",
                  FadeIn(prog, shift=0.2 * DOWN), run_time=1.6)

        # why it can't do it itself
        direct = Arrow(prog.get_bottom() + 0.6 * RIGHT, term.get_top() + 0.4 * LEFT, buff=0.1, stroke_width=3, color=GREY_B,
                       max_tip_length_to_length_ratio=0.06)
        cross = tick(False, 0.32).move_to(direct.point_from_proportion(0.5))
        self.seq("It can't drive the terminal itself. The CPU runs it in user mode, and user mode refuses the instructions that talk to devices.",
                 ([FadeIn(hl), FadeIn(term)], 0.6),
                 ([FadeIn(ub), FadeIn(ul)], 0.8),
                 1.2,
                 ([GrowArrow(direct)], 0.9),
                 ([FadeIn(cross, scale=1.4), direct.animate.set_color(RED_M)], 0.6))

        # the kernel band, its table and the write handler
        rows = VGroup(*[M(f"{n}  {name}", 20, GREY_B) for n, name in [(63, "read"), (64, "write"), (65, "readv")]]).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        tt = T("system call table", 20, GOLD_M)
        tg = VGroup(tt, rows).arrange(DOWN, buff=0.22)
        tbl_r = RoundedRectangle(corner_radius=0.12, width=tg.width + 0.6, height=tg.height + 0.45, stroke_color=GOLD_M, stroke_width=2.5)
        tbl_r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(GOLD_M), 0.08), 1)
        tbl = VGroup(tbl_r, tg).move_to([-3.0, -1.15, 0])
        hnd = box("write handler", GOLD_M, size=22, h=0.7).move_to([0.45, -0.75, 0])
        self.beat("Only one program runs in kernel mode: the kernel. So your program has to ask it, with a system call.",
                  FadeOut(direct), FadeOut(cross), FadeIn(kb), FadeIn(kl), FadeIn(tbl), FadeIn(hnd), run_time=1.6)

        # registers
        regs = {}
        cells = []
        for name, val in [("x8", "64"), ("x0", "1"), ("x1", "buf"), ("x2", "3")]:
            c = chip(f"{name} = {val}", BLUE_M, size=22, mono=True)
            regs[name] = c
            cells.append(c)
        for c in cells:
            c[0].stretch_to_fit_width(1.75)
        grid = VGroup(*cells).arrange_in_grid(rows=2, cols=2, buff=(0.3, 0.25))
        reg_t = T("registers", 20, GREY_B)
        reg = VGroup(reg_t, grid).arrange(DOWN, buff=0.2).move_to([3.2, 1.95, 0])
        self.seq("First the C library loads registers, the CPU's own small storage slots. The number for write, 64, goes in x8. The three arguments go in x0, x1 and x2.",
                 ([FadeIn(reg_t)], 0.5),
                 2.2,
                 ([FadeIn(regs["x8"], shift=0.15 * DOWN)], 0.8),
                 1.0,
                 ([LaggedStart(*[FadeIn(regs[k], shift=0.15 * DOWN) for k in ("x0", "x1", "x2")], lag_ratio=0.3)], 1.4))

        # the trap
        trap = Arrow(prog.get_bottom(), tbl.get_top(), buff=0.12, stroke_width=4, color=YELLOW_M, max_tip_length_to_length_ratio=0.12)
        trap_l = M("svc #0", 24, YELLOW_M).move_to([trap.get_x() - 0.3, 0.97, 0], aligned_edge=RIGHT)
        self.seq("Then it runs one special instruction, svc. The CPU saves where the program was, switches to kernel mode, and jumps to an entry point the kernel set at boot. The program can't choose where it lands. This is a trap.",
                 ([FadeIn(trap_l)], 0.6),
                 1.6,
                 ([GrowArrow(trap), ub.animate.set_fill(BLUE_M, 0.03), kb.animate.set_fill(GOLD_M, 0.1), prog.animate.set_opacity(0.5)], 1.2),
                 2.4,
                 ([flash(tbl, YELLOW_M, 1.04)], 1.0))

        # the table lookup
        hi = SurroundingRectangle(rows[1], color=YELLOW_M, buff=0.08, corner_radius=0.05)
        look = Arrow(rows[1].get_right() + 0.15 * RIGHT, hnd.get_left(), buff=0.12, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.1)
        self.seq("The kernel reads x8, finds entry 64 in its system call table, and runs the write handler.",
                 ([Indicate(regs["x8"], color=YELLOW_M), rows[1].animate.set_color(WHITE), Create(hi)], 1.2),
                 0.6,
                 ([GrowArrow(look), flash(hnd, YELLOW_M)], 1.0))

        # the checks
        c1 = VGroup(tick(True, 0.16), T("fd 1 is open for writing", 20)).arrange(RIGHT, buff=0.18)
        c2 = VGroup(tick(True, 0.16), T("buf is the program's memory", 20)).arrange(RIGHT, buff=0.18)
        checks = VGroup(c1, c2).arrange(DOWN, buff=0.2, aligned_edge=LEFT).next_to(hnd, RIGHT, buff=0.45)
        self.seq("The handler checks that file descriptor 1 is open, and that the buffer really is the program's own memory. It never trusts a pointer from user mode.",
                 ([FadeIn(c1, shift=0.1 * RIGHT), Indicate(regs["x0"], color=YELLOW_M)], 1.0),
                 1.2,
                 ([FadeIn(c2, shift=0.1 * RIGHT), Indicate(regs["x1"], color=YELLOW_M)], 1.0))

        # the work
        out = Arrow(hnd.get_bottom(), term.get_top(), buff=0.1, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.15)
        okb = M("ok", 22, YELLOW_M).next_to(out, RIGHT, buff=0.2)
        self.seq("Then it copies the three bytes and hands them to the terminal.",
                 ([GrowArrow(out), Indicate(regs["x2"], color=YELLOW_M)], 0.8),
                 ([FadeIn(okb, shift=0.3 * DOWN), flash(term, YELLOW_M)], 0.9))

        # the return
        x0n = chip("x0 = 3", GREEN_M, size=22, mono=True)
        x0n[0].stretch_to_fit_width(1.75)
        x0n.move_to(regs["x0"])
        back = Arrow(hnd.get_top() + 0.2 * LEFT, prog.get_right() + 0.3 * DOWN, buff=0.12, stroke_width=4, color=GREEN_M,
                     max_tip_length_to_length_ratio=0.1)
        back_l = M("eret", 24, GREEN_M).next_to(back.point_from_proportion(0.72), RIGHT, buff=0.3)
        self.seq("It puts the result, 3 bytes written, in x0, and runs eret. The CPU drops back to user mode, right after the svc instruction.",
                 ([FadeOut(checks), FadeOut(hi), rows[1].animate.set_color(GREY_B), Transform(regs["x0"], x0n)], 1.0),
                 1.6,
                 ([GrowArrow(back), FadeIn(back_l), ub.animate.set_fill(BLUE_M, 0.08), kb.animate.set_fill(GOLD_M, 0.03),
                   prog.animate.set_opacity(1)], 1.2))

        self.beat("The C library returns 3, and the program carries on. It never touched the hardware.",
                  flash(prog, GREEN_M, 1.04), run_time=1.4)

        # the cost
        cost = VGroup()
        for i, (left, right) in enumerate([("one crossing", "≈ 150 ns"), ("a million crossings", "≈ 150 ms")]):
            l = T(left, 22, YELLOW_M).move_to([0, -0.5 * i, 0], aligned_edge=LEFT)
            r = M(right, 22, YELLOW_M).move_to([2.75, -0.5 * i, 0], aligned_edge=LEFT)
            cost.add(VGroup(l, r))
        fit(cost, 3.9)
        cost.next_to(hnd, RIGHT, buff=0.55)
        self.seq("The crossing costs about 150 nanoseconds. Once, that's nothing. A logger that writes a million lines with one call each spends 150 milliseconds just crossing.",
                 ([FadeOut(okb), FadeOut(look), VGroup(trap, back).animate.set_opacity(0.6)], 0.6),
                 ([FadeIn(cost[0])], 0.8),
                 2.6,
                 ([FadeIn(cost[1])], 0.8))

        self.beat("Every trip into the kernel goes through that one door, and every trip costs time. So batch small writes into big ones, and cross less often.",
                  Indicate(trap, color=YELLOW_M), Indicate(back, color=GREEN_M), run_time=1.8)
        self.wait(0.6)
