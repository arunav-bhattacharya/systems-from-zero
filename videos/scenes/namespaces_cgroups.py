from sfz import *

SAY.insert(0, (r"\bcgroups\b", "C groups"))
SAY.insert(0, (r"\bcgroup\b", "C group"))
SAY.insert(0, (r"\bcpu\.max\b", "C P U max"))
SAY.insert(0, (r"\bmemory\.max\b", "memory max"))
SAY.insert(0, (r"\bOOM\b", "O O M"))
SAY.insert(0, (r"\bVMs?\b", lambda m: "V M" + ("s" if m.group(0).endswith("s") else "")))
SAY.insert(0, (r"\bps\b", "P S"))

LX, RX = -3.4, 3.4                     # the ledger's view (left) and the host's view (right)
NS_Y = [2.55, 2.0, 1.45, 0.9]          # pid, uts, net, mnt rows
CW, CHH = 5.2, 0.44                    # namespace chip width, height
PY = -0.6                              # process boxes
KY = -3.0                              # the kernel bar
MX0, MX1, MY = -5.6, -1.2, -1.4        # the cgroup's memory meter: 0 to 64 MB

def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def arr(a, b, color=GREY_B, sw=2.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = np.linalg.norm(b - a)
    return Arrow(a, b, buff=0.04, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2 / n,
                 max_stroke_width_to_length_ratio=20)




def ns_chip(x, k, kind, value, color=GREY_B, vcolor=WHITE):
    y = NS_Y[k]
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CHH, stroke_color=color, stroke_width=2).set_fill(fillc(color), 1)
    r.move_to([x, y, 0])
    return VGroup(r, left_at(M(kind, 17, color), x - CW / 2 + 0.2, y), left_at(T(value, 18, vcolor), x - CW / 2 + 1.0, y))


def proc(x, name, sub, color=WHITE, w=3.4):
    r = RoundedRectangle(corner_radius=0.12, width=w, height=0.82, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, PY, 0])
    return VGroup(r, T(name, 23).move_to([x, PY + 0.17, 0]), T(sub, 16, GREY_B).move_to([x, PY - 0.2, 0]))


def kbar(text, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.1, width=12.6, height=0.55, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to([0, KY, 0])
    return VGroup(r, T(text, 19).move_to([0, KY, 0]))


HOST = [("pid", "300 processes, ledger is 40037"), ("uts", "hostname: box-priv"),
        ("net", "eth0 and lo, the host's ports"), ("mnt", "the host's mount table")]
MINE = [("pid", "2 processes, ledger is PID 1"), ("uts", "hostname: ledger-box"),
        ("net", "its own lo and ports"), ("mnt", "its own root file system")]


class NamespacesCgroups(Base):
    """os-12, section 0 (with sections 1 and 2): the ledger and the fraud check on one kernel. A VM each costs a kernel,
    a boot and reserved RAM. A container is a process (PID 40037 on the host). Namespaces copy the host's tables: PID 1 of
    2 processes, hostname ledger-box, its own network and mounts. Seeing less isn't using less, so a cgroup caps it:
    cpu.max half a CPU, memory.max 64 MB. It leaks 48 MB, the next 16 MB triggers the OOM killer in the group only,
    exit code 137, and the fraud check and the host's 6 GB free are untouched."""

    def construct(self):
        self.title_card("Containers: namespaces and cgroups", "a container is a process with its own view and its own limits")

        # ---- 1. two services, one machine -----------------------------------------------------------------------
        led = proc(LX, "ledger", "a Java service")
        fra = proc(RX, "fraud check", "a Java service")
        kb = kbar("one machine, one Linux kernel")
        self.steps("The ledger service and the fraud check share one machine. Each should act as if it were alone: "
                   "it can't see the other's processes, and a leak in one can't kill the other.", [
            (lambda: [FadeIn(kb)], 0.6),
            (lambda: [FadeIn(led, shift=0.1 * UP), FadeIn(fra, shift=0.1 * UP)], 0.8),
            "Each should act",
            (lambda: [glow(led[0], BLUE_M), glow(fra[0], BLUE_M)], 0.9),
        ])

        # ---- 2. a VM each ------------------------------------------------------------------------------------------
        def vm(x):
            r = RoundedRectangle(corner_radius=0.16, width=4.6, height=2.3, stroke_color=PURPLE_M, stroke_width=2.5)
            r.move_to([x, PY - 0.35, 0])
            kk = RoundedRectangle(corner_radius=0.06, width=3.6, height=0.38, stroke_color=PURPLE_M, stroke_width=2)
            kk.set_fill(fillc(PURPLE_M), 1).move_to([x, PY - 1.15, 0])
            return VGroup(r, left_at(T("VM", 18, PURPLE_M), x - 2.12, PY + 0.45), kk, T("its own kernel", 15).move_to(kk))

        vms = [vm(LX), vm(RX)]
        cost = T("a VM each: its own kernel, a boot, reserved memory", 22, PURPLE_M).move_to([0, 1.6, 0])
        self.steps("A virtual machine each would do that. But every VM costs its own kernel, a boot, "
                   "and a slice of memory set aside.", [
            (lambda: [*[Create(v[0]) for v in vms], *[FadeIn(v[1]) for v in vms]], 0.9),
            "But every VM",
            (lambda: [*[FadeIn(v[2]) for v in vms], *[FadeIn(v[3]) for v in vms]], 0.7),
            (lambda: [FadeIn(cost, shift=0.1 * DOWN)], 0.6),
        ])

        # ---- 3. a container is a process -------------------------------------------------------------------------
        led2 = proc(LX, "ledger", "PID 40037 on the host")
        self.steps("Containers keep one kernel. A container is just a process: on the host, the ledger is PID 40,037.", [
            (lambda: [*[FadeOut(v) for v in vms], FadeOut(cost)], 0.8),
            (lambda: [glow(kb[0], GREEN_M, 1.01)], 0.8),
            "A container is",
            (lambda: [Transform(led, led2)], 0.7),
        ])

        # ---- 4. namespaces: private copies of the kernel's tables --------------------------------------------------
        hh = T("on the host", 22, GREY_B).move_to([RX, 3.2, 0])
        lh = T("what the ledger sees", 22, GOLD_M).move_to([LX, 3.2, 0])
        host = [ns_chip(RX, k, *HOST[k]) for k in range(4)]
        mine = [ns_chip(LX, k, *MINE[k], GOLD_M) for k in range(4)]
        self.steps("The kernel keeps tables that every process used to share: process IDs, the hostname, network "
                   "interfaces, mounted file systems. A namespace is a private copy of one of them.", [
            (lambda: [FadeIn(hh)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(h, shift=0.1 * LEFT) for h in host], lag_ratio=0.35)], 2.2),
            "A namespace is",
            (lambda: [FadeIn(lh), TransformFromCopy(host[0][0], mine[0][0]), TransformFromCopy(host[0][1], mine[0][1])], 1.0),
        ])

        # ---- 5. its own PID namespace -----------------------------------------------------------------------------
        led3 = proc(LX, "ledger", "PID 1 inside, 40037 on the host", GOLD_M)
        self.steps("In its own PID namespace, the ledger is PID 1, and ps lists 2 processes instead of 300.", [
            (lambda: [FadeIn(mine[0][2]), glow(mine[0][0], GOLD_M, 1.03)], 0.8),
            "the ledger is",
            (lambda: [Transform(led, led3)], 0.7),
            "and ps lists",
            (lambda: [Indicate(mine[0][2], color=GOLD_M, scale_factor=1.06), Indicate(host[0][2], color=GREY_B, scale_factor=1.06)], 1.0),
        ])

        # ---- 6. hostname, network, mounts -------------------------------------------------------------------------
        def copy(k):
            return [TransformFromCopy(host[k][0], mine[k][0]), TransformFromCopy(host[k][1], mine[k][1]), FadeIn(mine[k][2])]

        self.steps("It gets its own hostname, its own network interfaces and ports, and its own mounts, so its own root "
                   "file system.", [
            "its own hostname",
            (lambda: copy(1), 0.8),
            "its own network",
            (lambda: copy(2), 0.8),
            "its own mounts",
            (lambda: copy(3), 0.8),
        ])

        # ---- 7. seeing less isn't using less ------------------------------------------------------------------------
        fv = ValueTracker(6.0)
        free = always_redraw(lambda: T(f"host RAM 7.9 GB, free: {fv.get_value():.1f} GB", 20,
                                       GREEN_M if fv.get_value() > 2 else RED_M).move_to([RX, MY, 0]))
        uses = always_redraw(lambda: T(f"ledger uses: {6.1 - fv.get_value():.1f} GB", 20,
                                       GREY_B if fv.get_value() > 2 else RED_M).move_to([LX, MY, 0]))
        self.steps("But namespaces only change what it sees. Nothing stops it from using the host's memory, "
                   "until the whole machine runs short.", [
            (lambda: [FadeIn(free), FadeIn(uses)], 0.6),
            "Nothing stops it",
            (lambda: [fv.animate(rate_func=linear).set_value(0.3)], 2.4),
            "until the whole",
            (lambda: [glow(fra[0], RED_M), glow(kb[0], RED_M, 1.01)], 0.9),
        ])

        # ---- 8. a cgroup ---------------------------------------------------------------------------------------------
        fence = RoundedRectangle(corner_radius=0.16, width=5.8, height=2.75, stroke_color=TEAL_M, stroke_width=3)
        fence.move_to([LX, -0.925, 0])
        fl = left_at(T("cgroup", 19, TEAL_M), LX - 2.7, 0.17)
        path = left_at(M("/sys/fs/cgroup/ledger", 15, TEAL_M), LX - 1.6, 0.17)
        meter = Rectangle(width=MX1 - MX0, height=0.42, stroke_color=TEAL_M, stroke_width=2).move_to([(MX0 + MX1) / 2, MY, 0])
        mv = ValueTracker(0.0)
        fillbar = always_redraw(lambda: Rectangle(width=max((MX1 - MX0) * mv.get_value() / 64, 0.001), height=0.42, stroke_width=0)
                                .set_fill(TEAL_M if mv.get_value() < 50 else GOLD_M, 0.45)
                                .move_to([MX0 + (MX1 - MX0) * mv.get_value() / 128, MY, 0]))
        mtxt = always_redraw(lambda: T(f"{int(round(mv.get_value()))} of 64 MB", 17).move_to([(MX0 + MX1) / 2, MY, 0]))
        lim_m = T("memory.max: 64 MB", 17, TEAL_M)
        lim_c = T("cpu.max: half a CPU", 17, TEAL_M)
        VGroup(lim_m, lim_c).arrange(RIGHT, buff=0.5).move_to([LX, -1.97, 0])
        self.steps("A cgroup caps what it may use. It's a directory the kernel watches. Write the ledger's PID into it, "
                   "and everything the ledger uses counts against the group's limits.", [
            (lambda: [FadeOut(uses), fv.animate.set_value(6.0)], 0.8),
            "It's a directory",
            (lambda: [Create(fence), FadeIn(fl), FadeIn(path)], 0.9),
            "Write the ledger's",
            (lambda: [glow(led[0], TEAL_M)], 0.7),
            "and everything",
            (lambda: [FadeIn(lim_m), FadeIn(lim_c), Create(meter), FadeIn(fillbar), FadeIn(mtxt)], 0.8),
        ])

        # ---- 9. cpu.max ------------------------------------------------------------------------------------------------
        self.steps("cpu.max gives it half a CPU: once it has run for 50 of every 100 milliseconds, it waits for the next "
                   "100.", [
            (lambda: [Indicate(lim_c, color=TEAL_M, scale_factor=1.12)], 0.9),
            "it waits",
            (lambda: [glow(led[0], TEAL_M)], 0.8),
        ])

        # ---- 10. the leak ---------------------------------------------------------------------------------------------
        self.steps("memory.max is 64 MB. Now the ledger leaks: 16, 32, 48 MB.", [
            (lambda: [Indicate(lim_m, color=TEAL_M, scale_factor=1.12)], 0.8),
            "Now the ledger",
            (lambda: [mv.animate(rate_func=linear).set_value(16)], 0.6),
            0.2,
            (lambda: [mv.animate(rate_func=linear).set_value(32)], 0.6),
            0.2,
            (lambda: [mv.animate(rate_func=linear).set_value(48)], 0.6),
        ])

        # ---- 11. the OOM killer, inside the group -----------------------------------------------------------------------
        over = Rectangle(width=(MX1 - MX0) * 16 / 64, height=0.42, stroke_color=RED_M, stroke_width=2.5).set_fill(RED_M, 0.25)
        over.move_to([MX1 + (MX1 - MX0) * 8 / 64 - 0.0, MY, 0]).shift(0.0 * RIGHT)
        over.move_to([MX0 + (MX1 - MX0) * 56 / 64, MY, 0])
        dead = proc(LX, "ledger: killed", "exit code 137", RED_M)
        self.steps("Its next 16 MB would pass the limit. The kernel tries to reclaim memory inside the group, then runs the "
                   "OOM killer on this group alone. The ledger dies, with exit code 137.", [
            (lambda: [FadeIn(over)], 0.6),
            "The kernel tries",
            (lambda: [Transform(kb, kbar("kernel: reclaim inside the ledger's cgroup", GOLD_M))], 0.7),
            "then runs",
            (lambda: [Transform(kb, kbar("kernel: OOM killer, in this cgroup only", RED_M)), fence.animate.set_stroke(RED_M)], 0.7),
            "The ledger dies",
            (lambda: [Transform(led, dead), FadeOut(over), mv.animate.set_value(0)], 0.9),
        ])

        # ---- 12. the host is fine ---------------------------------------------------------------------------------------
        self.steps("The fraud check never notices, and the host still has 6 GB free.", [
            (lambda: [Transform(kb, kbar("one machine, one Linux kernel")), fence.animate.set_stroke(TEAL_M),
                      glow(fra[0], GREEN_M)], 0.9),
            "and the host",
            (lambda: [Indicate(free, color=GREEN_M, scale_factor=1.08)], 0.9),
        ])

        # ---- 13. the sentence to keep -----------------------------------------------------------------------------------
        self.steps("A container is a process. Namespaces decide what it can see, and a cgroup decides how much it can use.", [
            (lambda: [glow(led[0], RED_M)], 0.7),
            "Namespaces decide",
            (lambda: [*[glow(m[0], GOLD_M, 1.03) for m in mine]], 0.9),
            "and a cgroup",
            (lambda: [glow(fence, TEAL_M, 1.02)], 0.9),
        ])
        self.wait(0.6)
