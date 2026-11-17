from sfz import *

SAY.insert(0, (r"\bcgroups\b", "C groups"))
SAY.insert(0, (r"\bcgroup\b", "C group"))
SAY.insert(0, (r"\bseccomp\b", "sec comp"))
SAY.insert(0, (r"\bOOM\b", "O O M"))
SAY.insert(0, (r"\bps\b", "P S"))
SAY.insert(0, (r"\b40037\b", "forty thousand and thirty-seven"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
HX0, HX1, HB, HT = -6.65, 6.65, -2.7, 3.0          # the one computer: the host
KY, KH = -2.15, 0.6                                 # the one kernel, along the bottom
CB_, CT = -1.3, 2.4                                 # containers' bottom and top
CY = (CB_ + CT) / 2
AX, BX, PX = -4.2, 0.55, 4.75                       # payments, nightly job, the host's own view
CW, PW = 4.3, 3.2
TITLE_Y = CT - 0.3
PA_Y = 0.45                                         # the payments program's box
JB = np.array([0.0, 1.3, 0])                        # the nightly job's box
MTR_X0, MTR_X1 = 3.0, 6.05                          # the tasks meter in the kernel bar
CAP_Y, BAR_Y = -3.2, -2.9


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
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


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
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def harrow(a, b, color=GREY_B, sw=3):
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.18, max_stroke_width_to_length_ratio=10)


# ---- the pieces ----
def container(x, name, color=GREY_B, w=CW):
    r = RoundedRectangle(corner_radius=0.16, width=w, height=CT - CB_, stroke_color=color, stroke_width=3).set_fill("#0b0b0b", 1)
    r.move_to([x, CY, 0])
    t = VGroup(T("container", 20, GREY_B), T(name, 24)).arrange(RIGHT, buff=0.18)
    left_at(t, x - w / 2 + 0.28, TITLE_Y)
    t[1].align_to(t[0], DOWN)
    return VGroup(r, t).set_z_index(-1)


def prog_box(c, w, h, name, color):
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(name, 20).move_to(c + np.array([0, h / 2 - 0.28, 0])))


def tdot(p, color=BLUE_M, r=0.11):
    return Dot(p, radius=r, color=color)


def copy_pos(i):
    return np.array([BX + ((i % 8) - 3.5) * 0.47, [0.35, -0.1, -0.55, -1.0][i // 8], 0])


FW, FH = PW, 0.8


def feature0(c, top, color):
    r = RoundedRectangle(corner_radius=0.1, width=FW, height=FH, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1).move_to(c)
    return VGroup(r, left_at(T(top, 22, GREY_B), c[0] - FW / 2 + 0.22, c[1]))


def feature(c, top, name, sub, color):
    r = RoundedRectangle(corner_radius=0.1, width=FW, height=FH, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1).move_to(c)
    a = fit(T(name, 22, color), FW - 0.4)
    b = fit(T(f"{top}: {sub}", 17, GREY_B), FW - 0.4)
    left_at(a, c[0] - FW / 2 + 0.22, c[1] + 0.15)
    left_at(b, c[0] - FW / 2 + 0.22, c[1] - 0.2)
    return VGroup(r, a, b)


class NamespacesCgroups(Base):
    """os-12, section 0. Two containers on one computer: the nightly job copies itself and the payments program can't
    start a thread. From both sides, sleep is PID 1 inside and 40037 on the host (NSpid: 40037 1), with the same kernel
    (6.12.76-linuxkit): a container is a process. What containers are for, a VM each and its cost, then one kernel and
    four features as a block of flats (namespaces, cgroup, capabilities and seccomp, overlay). One of each kernel part;
    the shared kernel as the limit. The job had no meter for tasks; check: with a meter of 20, only the job notices."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def klabel(self, s):
        new = left_at(T(s, 22), HX0 + 0.55, KY)
        old, self.klab = self.klab, new
        return [swap(old, new)]

    def meter(self, frac, color=GOLD_M):
        w = max(0.02, (MTR_X1 - MTR_X0 - 0.06) * frac)
        new = Rectangle(width=w, height=0.22, stroke_width=0).set_fill(color, 0.9)
        left_at(new, MTR_X0 + 0.03, KY)
        old, self.mfill = self.mfill, new
        if old is None:
            return [GrowFromEdge(new, LEFT)]
        return [FadeOut(old), FadeIn(new)]

    def construct(self):
        self.capm = self.klab = self.mfill = None
        self.title_card("A container is a process", "in a very good disguise: namespaces, cgroups and one shared kernel")

        host = DashedVMobject(RoundedRectangle(corner_radius=0.22, width=HX1 - HX0, height=HT - HB, stroke_color=GREY_C, stroke_width=2),
                              num_dashes=110).move_to([(HX0 + HX1) / 2, (HB + HT) / 2, 0])
        host_t = left_at(T("one computer: the host", 20, GREY_B), HX0 + 0.3, HT - 0.22)
        kbar = RoundedRectangle(corner_radius=0.12, width=HX1 - HX0 - 0.6, height=KH, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M, 0.3), 1)
        kbar.move_to([(HX0 + HX1) / 2, KY, 0])
        mt_lab = right_at(T("tasks", 20, GREY_B), MTR_X0 - 0.15, KY)
        mt_box = Rectangle(width=MTR_X1 - MTR_X0, height=0.28, stroke_color=GREY_B, stroke_width=1.5).move_to([(MTR_X0 + MTR_X1) / 2, KY, 0])

        ca = container(AX, "payments")
        cb = container(BX, "nightly job")
        pa = prog_box(np.array([AX, PA_Y, 0]), 2.85, 1.0, "payments program", BLUE_M)
        th = [tdot([AX - 0.6 + 0.3 * i, PA_Y - 0.22, 0]) for i in range(3)]
        jb = prog_box(JB, 2.2, 0.9, "nightly job", GOLD_M)
        jd = tdot(JB + np.array([0, -0.2, 0]), GOLD_M)

        # ---------------- scene 1: the box next door ----------------
        self.steps("One computer runs two programs for the coffee-shop payments company: the payments program, and a nightly job "
                   "that adds up what each shop is owed.", [
            (lambda: [Create(host), FadeIn(host_t)], 0.8),
            "the payments program",
            (lambda: [FadeIn(pa), *[FadeIn(d) for d in th]], 0.6),
            "a nightly job",
            (lambda: [FadeIn(jb), FadeIn(jd)], 0.6),
            "adds up",
            (lambda: [FadeIn(kbar), *self.klabel("one kernel"), FadeIn(mt_lab), Create(mt_box), *self.meter(0.12)], 0.8),
        ])
        self.steps("Each runs in its own container, a boxed-off space with its own name, files and list of running programs.", [
            "its own container",
            (lambda: [FadeIn(ca[0]), FadeIn(cb[0])], 0.7),
            (lambda: [FadeIn(ca[1]), FadeIn(cb[1])], 0.5),
        ])
        copies = [tdot(copy_pos(i), GOLD_M) for i in range(32)]
        self.steps("One night, a bug makes the job copy itself, over and over.", [
            "copy itself",
            (lambda: [LaggedStart(*[FadeIn(c, scale=0.3) for c in copies], lag_ratio=0.12), *self.meter(1.0, RED_M)], 2.6),
        ])
        nt = tdot([AX + 0.3, PA_Y - 0.22, 0])
        nx = tick(False, 0.14).move_to(nt)
        self.steps("Minutes later, the payments program fails too, in a container nobody touched. It can't start a thread, a new line of work.", [
            "fails too",
            (lambda: [glow(pa[0], RED_M, 1.03)], 0.7),
            "It can't start",
            (lambda: [FadeIn(nt, scale=0.3)], 0.4),
            (lambda: [FadeOut(nt), Create(nx), *self.cap("payments: can't start a thread", RED_M)], 0.5),
        ])
        qm = T("?", 64, YELLOW_M).move_to([PX, 0.6, 0])
        self.steps("How did a bug in one box break the box next door?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.4)

        # ---------------- scene 2: look from both sides ----------------
        self.steps("It's easy to think a container is a small computer, with its own name, its own files, even its own process number 1.", [
            (lambda: [FadeOut(qm), *self.uncap(), FadeOut(nx)], 0.4),
            "a small computer",
            (lambda: self.cap("a container: a small computer of its own?", WHITE), 0.5),
        ])
        cs = container(AX, "sleep")
        ins_t = left_at(T("inside: ps", 20, GREY_B), AX - CW / 2 + 0.3, 1.3)
        ins_p = left_at(M("PID 1    sleep", 24), AX - CW / 2 + 0.3, 0.6)
        hp = RoundedRectangle(corner_radius=0.16, width=PW, height=CT - CB_, stroke_color=GREY_B, stroke_width=3).set_fill("#0b0b0b", 1).move_to([PX, CY, 0])
        hp.set_z_index(-1)
        hp_t = left_at(T("on the host", 24), PX - PW / 2 + 0.28, TITLE_Y)
        hp_ps = left_at(T("ps", 20, GREY_B), PX - PW / 2 + 0.3, 1.3)
        hp_q = left_at(M("PID ?", 24, YELLOW_M), PX - PW / 2 + 0.3, 0.6)
        self.steps("Let's look at one from both sides. Here's a container that runs sleep, a program that waits and does nothing.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(ca, cb, pa, *th, jb, jd, *copies)), *self.meter(0.12)], 0.8),
            "Here's a container",
            (lambda: [FadeIn(cs)], 0.6),
        ])
        self.steps("Inside, ps, the command that lists running programs, shows sleep as process number 1.", [
            "Inside",
            (lambda: [FadeIn(ins_t)], 0.4),
            "shows sleep",
            (lambda: [FadeIn(ins_p, shift=0.1 * RIGHT)], 0.6),
        ])
        self.steps("Now look from the host, the computer that runs the containers. What number does sleep have there?", [
            "Now look",
            (lambda: [FadeIn(hp), FadeIn(hp_t), glow(host, WHITE, 1.0)], 0.7),
            "What number",
            (lambda: [FadeIn(hp_ps), FadeIn(hp_q)], 0.5),
        ])
        self.steps("And does the container have a kernel of its own, the core of the operating system? Pause and guess.", [
            "a kernel of its own",
            (lambda: [glow(kbar, BLUE_M, 1.01)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        hp_p = left_at(fit(M("PID 40037 sleep", 24, YELLOW_M), PW - 0.6), PX - PW / 2 + 0.3, 0.6)
        link = DashedLine(ins_p.get_right() + np.array([0.2, 0, 0]), hp_p.get_left() + np.array([-0.2, 0, 0]), dash_length=0.12,
                          stroke_width=2.5, color=YELLOW_M)
        same = T("the same process", 22, YELLOW_M).move_to(link.get_center() + 0.32 * UP)
        nsp = left_at(M("NSpid: 40037 1", 20), PX - PW / 2 + 0.3, 0.0)
        self.steps("On the host, the same process is number 40037. Its status file lists both numbers, 40037 and 1.", [
            (lambda: [*self.uncap(), swap(hp_q, hp_p)], 0.6),
            "the same process",
            (lambda: [Create(link), FadeIn(same)], 0.7),
            "Its status file",
            (lambda: [FadeIn(nsp, shift=0.1 * UP)], 0.6),
            "40037 and 1",
            (lambda: [Indicate(nsp, color=YELLOW_M, scale_factor=1.08)], 0.7),
        ])
        un_in = VGroup(T("uname -r", 18, GREY_B), M("6.12.76-linuxkit", 18)).arrange(DOWN, buff=0.08)
        left_at(un_in, AX - CW / 2 + 0.3, -0.75)
        un_out = un_in.copy()
        left_at(un_out, PX - PW / 2 + 0.3, -0.75)
        dn_in = harrow([un_in.get_center()[0], CB_ - 0.04, 0], [un_in.get_center()[0], KY + KH / 2 + 0.04, 0], BLUE_M)
        dn_out = harrow([un_out.get_center()[0], CB_ - 0.04, 0], [un_out.get_center()[0], KY + KH / 2 + 0.04, 0], BLUE_M)
        self.steps("And the kernel version is the same on both sides.", [
            (lambda: [FadeIn(un_in), FadeIn(un_out)], 0.6),
            (lambda: [GrowArrow(dn_in), GrowArrow(dn_out), *self.klabel("one kernel · 6.12.76-linuxkit")], 0.7),
        ])
        self.steps("There's no second kernel and no second computer. Just one process in a very good disguise. A container is a process.", [
            "Just one process",
            (lambda: [glow(cs[0], YELLOW_M, 1.01)], 0.8),
            "A container is",
            (lambda: self.cap("a container is a process", WHITE, 30), 0.6),
        ], after=0.5)

        # ---------------- scene 3: what containers are for ----------------
        demo = VGroup(cs, ins_t, ins_p, hp, hp_t, hp_ps, hp_p, link, same, nsp, un_in, un_out, dn_in, dn_out)
        self.steps("So what are containers for? An old problem: run many programs on one computer, and let each act as if it were alone.", [
            (lambda: [FadeOut(demo), *self.uncap(), *self.klabel("one kernel")], 0.7),
            "run many programs",
            (lambda: [FadeIn(VGroup(ca, cb)), FadeIn(VGroup(pa, *th, jb, jd))], 0.7),
            "as if it were alone",
            (lambda: self.cap("many programs, one computer, each as if alone", WHITE), 0.5),
        ])
        self.steps("The payments program shouldn't see the job's processes or files. A memory leak in one shouldn't get the other killed. "
                   "And a program an attacker breaks into shouldn't change the computer's clock.", [
            (lambda: self.cap("not see the other's processes or files", GREY_B), 0.5),
            "A memory leak",
            (lambda: self.cap("one's memory leak can't get the other killed", GREY_B), 0.5),
            "And a program",
            (lambda: self.cap("a broken-into program can't change the clock", GREY_B), 0.5),
        ])
        vk = []
        for x in (AX, BX):
            r = RoundedRectangle(corner_radius=0.1, width=CW - 0.6, height=0.46, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M, 0.3), 1)
            r.move_to([x, CB_ + 0.42, 0])
            vk.append(VGroup(r, T("its own kernel", 18).move_to(r)))
        self.steps("The simplest complete answer is a virtual machine for each program: a pretend computer with its own kernel. "
                   "It works, and every program pays for a kernel, a start-up and a slice of memory.", [
            "a virtual machine",
            (lambda: [*self.cap("a virtual machine each: a pretend computer", WHITE)], 0.5),
            "with its own kernel",
            (lambda: [LaggedStart(*[FadeIn(v, shift=0.1 * UP) for v in vk], lag_ratio=0.3)], 0.8),
            "every program pays",
            (lambda: self.cap("per program: a kernel, a start-up, a slice of memory", GOLD_M), 0.6),
        ], after=0.3)

        # ---------------- scene 4: a block of flats ----------------
        self.steps("Containers keep one kernel, and use four things it already has. Picture a block of flats.", [
            (lambda: [*self.uncap(), *[v.animate.move_to([v.get_x(), KY, 0]).set_opacity(0) for v in vk]], 0.8),
            "four things",
            (lambda: [glow(kbar, BLUE_M, 1.01)], 0.7),
            "a block of flats",
            (lambda: self.cap("a block of flats", WHITE), 0.5),
        ])
        self.remove(*vk)
        FC = {k: np.array([PX, y, 0]) for k, y in zip(("ns", "cg", "cap", "ov"), (1.9, 0.95, 0.0, -0.95))}
        f_head = T("a flat's four features", 20, GREY_B).move_to([PX, 2.6, 0])
        f_ns0 = feature0(FC["ns"], "walls, letterbox", GREEN_M)
        f_ns = feature(FC["ns"], "walls, letterbox", "namespaces", "what it sees", GREEN_M)
        f_cg0 = feature0(FC["cg"], "meter, fuse", GOLD_M)
        f_cg = feature(FC["cg"], "meter, fuse", "a cgroup", "how much it uses", GOLD_M)
        f_cp0 = feature0(FC["cap"], "house rules", PURPLE_M)
        f_cp = feature(FC["cap"], "house rules", "capabilities, seccomp", "what it may ask for", PURPLE_M)
        f_ov0 = feature0(FC["ov"], "furniture", TEAL_M)
        f_ov = feature(FC["ov"], "furniture", "the overlay", "its own files", TEAL_M)
        door = M("1", 24, GREEN_M).move_to([AX + 1.7, PA_Y + 0.3, 0])
        self.steps("The walls and a private letterbox: a tenant sees only their own rooms and post, and can number their door 1.", [
            (lambda: [*self.uncap(), FadeIn(f_head), FadeIn(f_ns0)], 0.6),
            "and can number",
            (lambda: [FadeIn(door, scale=1.5)], 0.5),
        ])
        self.steps("Every tenant can be number 1, which is great for morale.", [
            (lambda: [Indicate(door, color=GREEN_M, scale_factor=1.4)], 0.8),
        ], after=0.2)
        self.steps("Those are namespaces: each container gets its own view, its own process numbers, computer name, network and list of disks.", [
            (lambda: [swap(f_ns0, f_ns), FadeOut(door)], 0.6),
            "its own view",
            (lambda: self.cap("namespaces: its own process numbers, name, network, disks", GREEN_M), 0.5),
        ])
        self.steps("The meter: so much power and water, and the fuse trips for this flat only. "
                   "That's a cgroup: a cap on how many tasks, how much memory and CPU time.", [
            (lambda: [*self.uncap(), FadeIn(f_cg0)], 0.6),
            "That's a cgroup",
            (lambda: [swap(f_cg0, f_cg), *self.cap("a cgroup: a cap on tasks, memory and CPU time", GOLD_M)], 0.6),
        ])
        self.steps("The house rules: hang pictures, but don't touch the boiler. "
                   "Those are capabilities and seccomp: what the process may ask the kernel to do.", [
            (lambda: [*self.uncap(), FadeIn(f_cp0)], 0.6),
            "Those are capabilities",
            (lambda: [swap(f_cp0, f_cp), *self.cap("capabilities and seccomp: what it may ask the kernel to do", PURPLE_M)], 0.6),
        ])
        self.steps("And the furniture belongs to the building, but what you change is yours until you move out. "
                   "That's the overlay: the container's own files, laid over a shared, read-only image.", [
            (lambda: [*self.uncap(), FadeIn(f_ov0)], 0.6),
            "That's the overlay",
            (lambda: [swap(f_ov0, f_ov), *self.cap("the overlay: its own files over a shared, read-only image", TEAL_M)], 0.6),
        ], after=0.4)
        feats = VGroup(f_ns, f_cg, f_cp, f_ov, f_head)

        # ---------------- scene 5: one of each part ----------------
        parts = T("scheduler · page cache · OOM killer", 20).move_to([-1.1, KY, 0])
        ka = harrow([AX, CB_ - 0.04, 0], [AX, KY + KH / 2 + 0.04, 0], BLUE_M)
        kb = harrow([BX, CB_ - 0.04, 0], [BX, KY + KH / 2 + 0.04, 0], BLUE_M)
        self.steps("Underneath, there's still one of each part: one scheduler picking what runs, one page cache, "
                   "one OOM killer, the part that ends a process when memory runs out.", [
            (lambda: [*self.uncap(), GrowArrow(ka), GrowArrow(kb)], 0.6),
            "one scheduler",
            (lambda: [FadeIn(parts), *self.cap("one of each, shared by every container", WHITE)], 0.6),
            "one OOM killer",
            (lambda: [Indicate(parts, color=BLUE_M, scale_factor=1.05)], 0.8),
        ], after=0.3)

        # ---------------- scene 6: where the flats picture breaks ----------------
        cx = -1.0
        crack = VMobject(stroke_color=RED_M, stroke_width=4).set_points_as_corners(
            [[cx, KY + 0.3, 0], [cx + 0.12, KY + 0.12, 0], [cx - 0.08, KY - 0.02, 0], [cx + 0.1, KY - 0.16, 0], [cx - 0.02, KY - 0.3, 0]])
        self.steps("And here the flats picture breaks. Real flats share foundations, but each has its own wiring. "
                   "Containers share the one kernel, wiring and all.", [
            (lambda: [*self.cap("where the flats picture breaks", WHITE), FadeOut(parts)], 0.5),
            "each has its own wiring",
            (lambda: self.cap("real flats: each has its own wiring", GREY_B), 0.5),
            "Containers share",
            (lambda: [*self.cap("containers: one kernel, wiring and all", WHITE), glow(kbar, WHITE, 1.01)], 0.8),
        ])
        ra = harrow([AX + 1.2, CB_ - 0.04, 0], [cx - 0.12, KY + 0.33, 0], RED_M)
        rb = harrow([BX - 1.2, CB_ - 0.04, 0], [cx + 0.12, KY + 0.33, 0], RED_M)
        self.steps("So a kernel bug that one container can reach is a bug in every container on the machine.", [
            "a kernel bug",
            (lambda: [Create(crack)], 0.5),
            "one container can reach",
            (lambda: [GrowArrow(ra)], 0.5),
            "every container",
            (lambda: [GrowArrow(rb), *self.cap("a kernel bug one container can reach is in every container", RED_M)], 0.6),
        ])
        self.steps("That's why Docker's filter blocks dozens of requests a program could make to the kernel. "
                   "When you need a hard wall, you need a virtual machine.", [
            (lambda: self.cap("Docker's filter blocks dozens of system calls", WHITE), 0.5),
            "When you need",
            (lambda: self.cap("a hard wall: a virtual machine", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 7: back to the nightly job ----------------
        copies2 = [tdot(copy_pos(i), GOLD_M) for i in range(32)]
        self.steps("Back to the nightly job. Both containers are processes on one kernel. Every copy of the job is a task, and so is every thread.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(crack, ra, rb)), feats.animate.set_opacity(0.3), *self.meter(0.12)], 0.7),
            "Both containers",
            (lambda: [glow(ka, WHITE, 1.0), glow(kb, WHITE, 1.0)], 0.6),
            "Every copy",
            (lambda: [LaggedStart(*[FadeIn(c, scale=0.3) for c in copies2[:6]], lag_ratio=0.2), *self.meter(0.3)], 0.9),
            "every thread",
            (lambda: [LaggedStart(*[Indicate(d, color=BLUE_M, scale_factor=1.5) for d in th], lag_ratio=0.2)], 0.7),
        ])
        nt2 = tdot([AX + 0.3, PA_Y - 0.22, 0])
        nx2 = tick(False, 0.14).move_to(nt2)
        self.steps("Nobody put a meter on the job's flat for tasks. So its copies used up something the flats share, "
                   "and the payments program couldn't start a thread.", [
            (lambda: [*self.cap("no meter on the job's flat for tasks", GOLD_M), f_cg.animate.set_opacity(1)], 0.5),
            "So its copies",
            (lambda: [LaggedStart(*[FadeIn(c, scale=0.3) for c in copies2[6:]], lag_ratio=0.1), *self.meter(1.0, RED_M)], 2.0),
            "couldn't start",
            (lambda: [FadeIn(nt2, scale=0.3)], 0.3),
            (lambda: [FadeOut(nt2), Create(nx2)], 0.4),
        ], after=0.4)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So a container is a process: walls, a meter, house rules and its own furniture, on a kernel it shares with everyone else.", [
            (lambda: [FadeOut(VGroup(*copies2, nx2)), *self.meter(0.12), *self.cap("a container is a process", WHITE)], 0.7),
            "walls, a meter",
            (lambda: [feats.animate.set_opacity(1)], 0.5),
            (lambda: [LaggedStart(*[glow(f[0], f[0].get_stroke_color(), 1.03) for f in (f_ns, f_cg, f_cp, f_ov)], lag_ratio=0.3)], 1.4),
            "on a kernel",
            (lambda: [*self.cap("a process with walls, a meter, house rules and furniture, on a shared kernel", WHITE), glow(kbar, BLUE_M, 1.01)], 0.8),
        ], after=0.4)
        jm = VGroup(RoundedRectangle(corner_radius=0.1, width=1.25, height=0.9, stroke_color=GREEN_M, stroke_width=2.5).set_fill(BLACK, 1),
                    VGroup(T("meter", 18, GREEN_M), T("20 tasks", 18)).arrange(DOWN, buff=0.08)).move_to([BX + 1.35, JB[1], 0])
        jm[1].move_to(jm[0])
        self.steps("One quick check. Put a meter on the job's flat: at most 20 tasks. The bug strikes again. "
                   "Who notices: the job, the payments program, or both? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "Put a meter",
            (lambda: [FadeIn(jm, scale=0.8), glow(f_cg[0], GOLD_M, 1.03)], 0.6),
            "The bug strikes",
            (lambda: [glow(jb[0], GOLD_M, 1.04)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        copies3 = [tdot(copy_pos(i), GOLD_M) for i in range(19)]
        fail = copy_pos(19)
        fx = tick(False, 0.14).move_to(fail)
        ok_t = tdot([AX + 0.3, PA_Y - 0.22, 0])
        ok_m = tick(True, 0.13).move_to([AX + 0.72, PA_Y - 0.22, 0])
        self.steps("Only the job. Its fuse trips at 20, and its next copy fails.", [
            (lambda: [*self.uncap(), LaggedStart(*[FadeIn(c, scale=0.3) for c in copies3], lag_ratio=0.12), *self.meter(0.2)], 1.8),
            "its next copy",
            (lambda: [Create(fx), *self.cap("the job: copy fails at 20 tasks (EAGAIN)", GOLD_M), glow(jm[0], GREEN_M, 1.05)], 0.6),
        ])
        self.steps("Next door, the payments program starts its threads and never hears a thing.", [
            "starts its threads",
            (lambda: [FadeIn(ok_t, scale=0.3)], 0.4),
            (lambda: [Create(ok_m), *self.cap("payments: starts its threads as usual", BLUE_M)], 0.5),
        ], after=0.4)
        self.wait(2.0)
