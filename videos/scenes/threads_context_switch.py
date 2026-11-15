from sfz import *

SAY.insert(0, (r"\bT1's\b", "T one's"))
SAY.insert(0, (r"\bT2's\b", "T two's"))
SAY.insert(0, (r"\bT1\b", "T one"))
SAY.insert(0, (r"\bT2\b", "T two"))
SAY.insert(0, (r"\bT3\b", "T three"))
SAY.insert(0, (r"\bJDK\b", "J D K"))

CX, CY, CW, CH = -4.4, 1.35, 3.8, 2.7          # the core
TXS = {1: 0.45, 2: 2.75, 3: 5.05}             # thread cards
TW = 2.1
TL_Y, TL_X0, TL_X1 = -1.75, -6.2, 6.2         # timeline of the core
MSU = 0.2                                      # units per ms on the timeline
NOTE_Y = -3.25
COL = {1: GOLD_M, 2: TEAL_M, 3: BLUE_M}
REGS = {1: ["line 45", "T1 stack", "1,200"], 2: ["line 88", "T2 stack", "  417"], 3: ["line 12", "T3 stack", "   90"]}
ROWS = [1.95, 1.45, 0.95]


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def rrect(w, h, c, color=WHITE, sw=3, fill=None):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=sw)
    return r.set_fill(fill if fill is not None else fillc(color), 1).move_to(c)


def core_val(k, s, color):
    m = M(s, 24, color).set_z_index(3)
    return m.move_to([CX + CW / 2 - 0.25 - m.width / 2, ROWS[k], 0])


def card_val(i, k, s, color):
    m = M(s, 20, color).set_z_index(3)
    return m.move_to([TXS[i], ROWS[k], 0])


def card_state(i, s, color=GREY_B):
    return T(s, 20, color).move_to([TXS[i], CY - CH / 2 + 0.35, 0])


def core_state(s, color=GREY_B):
    return T(s, 22, color).move_to([CX, CY - CH / 2 + 0.35, 0])


def slice_rect(t0, ms, color):
    r = Rectangle(width=ms * MSU - 0.03, height=0.42, stroke_width=0).set_fill(color, 0.85)
    return r.move_to([TL_X0 + (t0 + ms / 2) * MSU, TL_Y, 0])


def note(s, color=GREY_B):
    return chip(s, color, 21).move_to([0, NOTE_Y, 0])


class ThreadsContextSwitch(Base):
    """os-03, section 4 (with os-04's context switch): one core, three threads. The scheduler saves T1's registers and
    loads T2's; 3 ms turns; 30 busy threads wait about 90 ms each. T2 blocks 120 ms on the card issuer and leaves the
    queue. 10,000 waiting requests as platform threads: 10,000 kernel tasks, about 20 GB of stack reserved. Virtual
    threads mount on a carrier and unmount when they block; in the lab, 10,000 ran on 37 OS threads under a 64-task
    limit, where platform threads failed after 42."""

    def construct(self):
        self.title_card("Context switches and virtual threads", "one core, many threads, and who waits")

        core = rrect(CW, CH, [CX, CY, 0], WHITE, fill=BLACK)
        ctitle = T("CPU core", 26).move_to([CX, CY + CH / 2 - 0.35, 0])
        rlab = VGroup(*[T(s, 20, GREY_B) for s in ("next line", "stack", "a value")])
        for k, m in enumerate(rlab):
            m.move_to([CX - CW / 2 + 0.25 + m.width / 2, ROWS[k], 0])
        cards, names, vals, states = {}, {}, {}, {}
        for i in (1, 2, 3):
            cards[i] = rrect(TW, CH, [TXS[i], CY, 0], COL[i], 2.5)
            names[i] = T(f"T{i}", 26, COL[i]).move_to([TXS[i], CY + CH / 2 - 0.35, 0])
            vals[i] = VGroup(*[card_val(i, k, REGS[i][k], COL[i]) for k in range(3)])
            states[i] = card_state(i, "runnable")
        cst = core_state("idle")
        self.steps("A payment service has three threads, each handling one card authorization. The machine has one CPU core.", [
            (lambda: [LaggedStart(*[FadeIn(VGroup(cards[i], names[i], vals[i], states[i]), shift=0.1 * UP) for i in (1, 2, 3)],
                                  lag_ratio=0.25)], 1.2),
            "The machine",
            (lambda: [FadeIn(core), FadeIn(ctitle), FadeIn(rlab), FadeIn(cst)], 0.8),
        ])

        cv = {}

        def load(i):
            cv[i] = VGroup(*[core_val(k, REGS[i][k], COL[i]) for k in range(3)])
            return [*[ReplacementTransform(vals[i][k], cv[i][k]) for k in range(3)],
                    Transform(cst, core_state(f"running: T{i}", COL[i])), Transform(states[i], card_state(i, "running", COL[i])),
                    core.animate.set_stroke(COL[i])]

        def save(i):
            vals[i] = VGroup(*[card_val(i, k, REGS[i][k], COL[i]) for k in range(3)])
            return [*[ReplacementTransform(cv[i][k], vals[i][k]) for k in range(3)], Transform(states[i], card_state(i, "runnable"))]

        self.steps("A core runs one thread at a time, whatever sits in its registers: "
                   "the next line of code, the stack, and the values in use.", [
            (lambda: load(1), 1.0),
            "the next line",
            (lambda: [Indicate(cv[1][0], color=GOLD_M)], 0.6),
            "the stack",
            (lambda: [Indicate(cv[1][1], color=GOLD_M)], 0.6),
            "and the values",
            (lambda: [Indicate(cv[1][2], color=GOLD_M)], 0.6),
        ])

        axis = Line([TL_X0, TL_Y - 0.3, 0], [TL_X1, TL_Y - 0.3, 0], stroke_width=2, color=GREY_D)
        tlab = T("the core over time", 20, GREY_B).move_to([TL_X0 + 1.1, TL_Y + 0.5, 0])
        tticks = VGroup(*[Line([TL_X0 + k * 15 * MSU, TL_Y - 0.38, 0], [TL_X0 + k * 15 * MSU, TL_Y - 0.22, 0], stroke_width=2,
                               color=GREY_D) for k in range(5)])
        tnum = VGroup(*[T(f"{k * 15} ms", 18, GREY_C).move_to([TL_X0 + k * 15 * MSU, TL_Y - 0.6, 0]) for k in range(5)])
        sl = []
        sl.append(slice_rect(0, 3, COL[1]))
        timer = T("timer interrupt", 20, RED_M).move_to([CX, CY + CH / 2 + 0.35, 0])
        self.steps("Every few milliseconds a timer interrupts, and the kernel's scheduler picks who runs next.", [
            (lambda: [Create(axis), FadeIn(tlab), FadeIn(tticks), FadeIn(tnum)], 0.7),
            (lambda: [GrowFromEdge(sl[0], LEFT)], 0.7),
            "a timer",
            (lambda: [FadeIn(timer, shift=0.1 * DOWN), glow(core, RED_M, 1.03)], 0.8),
        ])

        cs = note("context switch: save one thread's registers, load another's", GREY_A)
        self.steps("It saves T1's registers to memory and loads T2's. That's a context switch.", [
            (lambda: save(1), 0.9),
            "and loads",
            (lambda: load(2), 0.9),
            (lambda: [FadeOut(timer)], 0.3),
            "That's a context switch",
            (lambda: [FadeIn(cs, shift=0.1 * UP)], 0.6),
        ])

        t = [3]

        def run(i, ms=3, rt=0.4):
            r = slice_rect(t[0], ms, COL[i])
            sl.append(r)
            t[0] += ms
            return (lambda r=r: [GrowFromEdge(r, LEFT)], rt)

        def switch(a, b, rt=0.5):
            return (lambda: [*save(a), *load(b)], rt)

        self.steps("With turns of about 3 milliseconds each, all three seem to run at once.", [
            run(2),
            switch(2, 3), run(3),
            switch(3, 1), run(1),
        ])

        busy = note("30 busy threads on one core: each waits about 90 ms between turns", RED_M)
        self.steps("Each switch costs a trip into the kernel, and leaves caches full of another thread's data. "
                   "With 30 busy threads on one core, each waits about 90 milliseconds for a turn.", [
            (lambda: [glow(core, RED_M, 1.03)], 0.8),
            "With 30 busy",
            (lambda: [FadeOut(cs), FadeIn(busy, shift=0.1 * UP)], 0.7),
        ])

        wait_lab = card_state(2, "waiting: 120 ms", GREY_B)

        def block2():
            vals[2] = VGroup(*[card_val(2, k, REGS[2][k], COL[2]).set_opacity(0.35) for k in range(3)])
            return [*[ReplacementTransform(cv[2][k], vals[2][k]) for k in range(3)], Transform(states[2], wait_lab),
                    cards[2].animate.set_stroke(GREY_D).set_fill(BLACK, 1), names[2].animate.set_opacity(0.4),
                    Transform(cst, core_state("switching")), core.animate.set_stroke(WHITE)]

        self.steps("But most service threads just wait. T2 calls the card issuer and waits 120 milliseconds.", [
            (lambda: [FadeOut(busy), *save(1), *load(2)], 0.6),
            run(2, 1, 0.3),
            "T2 calls",
            (lambda: block2(), 0.8),
        ])

        back2 = note("a thread that blocks frees the core", GREEN_M)
        self.steps("While it waits, it's off the queue, so the core runs only T1 and T3. "
                   "When the reply comes, T2 is runnable again.", [
            (lambda: load(3), 0.4), run(3), switch(3, 1), run(1), switch(1, 3), run(3), switch(3, 1), run(1),
            (lambda: [FadeIn(back2, shift=0.1 * UP)], 0.5),
            "When the reply",
            (lambda: [Transform(states[2], card_state(2, "runnable")), cards[2].animate.set_stroke(COL[2]).set_fill(fillc(COL[2]), 1),
                      names[2].animate.set_opacity(1), vals[2].animate.set_opacity(1)], 0.7),
        ])

        # ---- ten thousand waiting requests ----------------------------------------------------------------------------
        grid = VGroup(*[Square(0.2, stroke_width=0).set_fill(GREY_B, 1) for _ in range(100)]).arrange_in_grid(10, 10, buff=0.07)
        grid.move_to([2.75, CY + 0.1, 0])
        glab = T("each square: 100 platform threads", 18, GREY_B).move_to([2.75, -0.3, 0])
        big = T("10,000 platform threads", 26, RED_M).move_to([2.75, 3.35, 0])
        cost = VGroup(chip("10,000 kernel tasks to switch between", RED_M, 20), chip("about 20 GB of stack reserved", RED_M, 20))
        cost.arrange(RIGHT, buff=0.35).move_to([0, NOTE_Y, 0])
        timeline = VGroup(axis, tlab, tticks, tnum)
        self.steps("So a waiting service wants a thread per request. "
                   "10,000 requests in flight means 10,000 platform threads, each a kernel task with its own stack.", [
            (lambda: [FadeOut(back2), FadeOut(timeline), *[FadeOut(r) for r in sl],
                      *[FadeOut(VGroup(cards[i], names[i], vals[i], states[i])) for i in (2, 3)],
                      FadeOut(VGroup(cards[1], names[1], states[1])), *[FadeOut(m) for m in cv[1]],
                      Transform(cst, core_state("one of 10,000 at a time")), core.animate.set_stroke(WHITE)], 0.8),
            "10,000 requests",
            (lambda: [LaggedStart(*[FadeIn(q) for q in grid], lag_ratio=0.01), FadeIn(big), FadeIn(glab)], 1.4),
        ])

        self.steps("That's 10,000 tasks for the kernel to switch between, and about 20 gigabytes of stack reserved, "
                   "almost all of it for waiting.", [
            (lambda: [FadeIn(cost[0], shift=0.1 * UP)], 0.6),
            "and about 20",
            (lambda: [FadeIn(cost[1], shift=0.1 * UP)], 0.6),
            "almost all of it",
            (lambda: [grid.animate.set_opacity(0.4)], 0.8),
        ])

        heap = rrect(4.4, 3.8, [2.75, 1.15, 0], PURPLE_M, 2.5, fill=BLACK)
        hlab = T("Java heap", 22, PURPLE_M).move_to([2.75, -0.48, 0])
        vgrid = VGroup(*[Dot(radius=0.075, color=PURPLE_M).set_z_index(3) for _ in range(100)]).arrange_in_grid(10, 10, buff=0.13)
        vgrid.move_to([2.75, CY + 0.05, 0])
        orig = [d.get_center() for d in vgrid]
        vlab = T("10,000 virtual threads", 26, PURPLE_M).move_to(big)
        carrier = T("carrier thread", 22, GREY_A).move_to([CX, CY + CH / 2 - 0.35, 0])
        self.steps("Virtual threads move that switching into the JDK. Each one is a Java object on the heap. "
                   "To run, it mounts on a carrier, a platform thread, one per core.", [
            (lambda: [FadeOut(cost), FadeOut(glab), FadeIn(heap), *[ReplacementTransform(a, b) for a, b in zip(grid, vgrid)],
                      Transform(big, vlab)], 1.0),
            (lambda: [FadeIn(hlab)], 0.4),
            "To run",
            (lambda: [Transform(ctitle, carrier), core.animate.set_stroke(GREY_A), Transform(cst, core_state("carrier: idle")),
                      FadeOut(rlab)], 0.6),
            "a platform thread",
            (lambda: [glow(core, GREY_A, 1.03)], 0.8),
        ])

        slot = np.array([CX, CY + 0.15, 0])
        v = {}

        def mount(k, name):
            d = vgrid[k]
            v[name] = T(name, 26, PURPLE_M).move_to(slot + 0.45 * DOWN)
            return [d.animate.move_to(slot + 0.35 * UP).scale(2.2), Transform(cst, core_state(f"running: {name}", PURPLE_M)),
                    FadeIn(v[name])]

        def unmount(k, name):
            d = vgrid[k]
            return [d.animate.move_to(orig[k]).scale(1 / 2.2).set_opacity(0.4), FadeOut(v[name])]

        self.steps("When one blocks on the issuer, the JDK saves its stack on the heap and unmounts it. "
                   "The carrier picks up the next one, and the kernel sees no switch.", [
            (lambda: mount(0, "V1"), 0.8),
            "When one blocks",
            (lambda: unmount(0, "V1"), 0.8),
            "The carrier picks",
            (lambda: mount(1, "V2"), 0.7),
            (lambda: unmount(1, "V2"), 0.5),
            (lambda: mount(2, "V3"), 0.6),
            "and the kernel",
            (lambda: [glow(core, GREEN_M, 1.03)], 0.8),
        ])

        lab = VGroup(chip("lab, limit of 64 tasks: platform threads failed after 42", RED_M, 20),
                     chip("10,000 virtual threads ran on 37 OS threads", GREEN_M, 20)).arrange(DOWN, buff=0.18)
        lab.move_to([0, -2.75, 0])
        self.steps("In the lab, under a limit of 64 tasks, platform threads failed after 42, "
                   "while 10,000 virtual threads ran on 37 OS threads.", [
            (lambda: [FadeIn(lab[0], shift=0.1 * UP)], 0.6),
            "10,000 virtual",
            (lambda: [FadeIn(lab[1], shift=0.1 * UP)], 0.6),
        ])

        self.steps("A core runs one thread at a time, and every kernel switch costs. "
                   "Virtual threads make waiting cheap, so thousands can wait on a few OS threads.", [
            (lambda: [glow(core, WHITE, 1.03)], 0.9),
            "Virtual threads",
            (lambda: [LaggedStart(*[d.animate(rate_func=there_and_back).scale(1.6) for d in vgrid[3:]], lag_ratio=0.01)], 1.4),
        ])
        self.wait(0.6)
