from sfz import *

SAY.insert(0, (r"\bepoll_wait\b", "ee poll wait"))
SAY.insert(0, (r"\bepoll wait\b", "ee poll wait"))
SAY.insert(0, (r"\bepoll\b", "ee poll"))

GX, GY = -4.75, 0.55         # the sockets
MX = -0.65                 # middle column: threads, later the kernel
TX, TY = 4.6, 0.85          # the one thread
READY = [17, 42, 88]


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


def left(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def tstate(s, color=GREY_B):
    return T(s, 22, color).move_to([TX, TY - 0.32, 0])


class Epoll(Base):
    """os-11, sections 0 and 1: 10,000 mostly idle connections. A thread per connection sleeps in read() and costs a
    thread each (the lab: 2,000 idle clients, 2,028 threads, about 200 MB). Polling non-blocking sockets burns a CPU;
    select and poll check every socket on every call. epoll registers sockets once, the kernel puts a socket on the
    ready list when data arrives, and epoll_wait returns only those (the lab's Selector server: 19 threads, 51 MB)."""

    def construct(self):
        self.title_card("Blocking reads and epoll", "ten thousand connections, a few of them talking")

        dots = VGroup(*[Dot(radius=0.09, color=GREY_C) for _ in range(100)]).arrange_in_grid(10, 10, buff=0.19)
        dots.move_to([GX, GY, 0])
        glab = T("10,000 open connections", 26).move_to([GX, 2.85, 0])
        gsub = T("100 of them drawn", 18, GREY_B).move_to([GX, GY - 2.05, 0])
        self.steps("A payment gateway holds 10,000 open connections from merchants. At any moment, only a few have sent "
                   "anything. How many threads does it need?", [
            (lambda: [FadeIn(glab), LaggedStart(*[FadeIn(d) for d in dots], lag_ratio=0.01), FadeIn(gsub)], 1.4),
            "only a few",
            (lambda: [*[dots[i].animate(rate_func=there_and_back).set_color(GOLD_M).scale(1.6) for i in READY]], 1.0),
        ])

        caps = VGroup(*[RoundedRectangle(corner_radius=0.04, width=0.12, height=0.26, stroke_width=0).set_fill(GREY_D, 1)
                        for _ in range(100)]).arrange_in_grid(10, 10, buff=(0.25, 0.09))
        caps.move_to([MX, GY, 0])
        clab = T("a thread for each, asleep in read()", 20, GREY_B).move_to([MX, GY - 2.05, 0])
        self.steps("The simplest design gives each connection its own thread. "
                   "The thread calls read, and the kernel puts it to sleep until bytes arrive.", [
            (lambda: [TransformFromCopy(dots, caps)], 1.2),
            "The thread calls read",
            (lambda: [FadeIn(clab)], 0.6),
            "puts it to sleep",
            (lambda: [caps.animate.set_fill(GREY_D, 0.6)], 0.6),
        ])

        def wake(i):
            return [(lambda: [dots[i].animate.set_color(GOLD_M).scale(1.5)], 0.4),
                    (lambda: [caps[i].animate.set_fill(GOLD_M, 1).scale(1.6)], 0.4),
                    (lambda: [caps[i].animate.set_fill(GREY_D, 0.6).scale(1 / 1.6), dots[i].animate.set_color(GREY_C).scale(1 / 1.5)], 0.5)]

        self.steps("When a request comes in, the kernel wakes that one thread. It reads, answers, and calls read again.", [
            *wake(READY[0]),
            "It reads",
            *wake(READY[1]),
        ])

        sx = 1.65
        s1 = left(T("in the lab, 2,000 idle clients:", 22, GREY_B), sx, 1.95)
        s2 = left(T("2,028 threads", 28, RED_M), sx, 1.4)
        s3 = left(T("about 200 MB of memory", 28, RED_M), sx, 0.85)
        s4 = left(T("almost all of them asleep", 22, GREY_B), sx, 0.35)
        s5 = T("at 10,000: a stack for every thread, and a context switch for every wake-up", 22, GREY_B).move_to([0, -2.3, 0])
        self.steps("It works, but in the lab, 2,000 idle clients took 2,028 threads and about 200 megabytes, "
                   "almost all of it asleep. At 10,000, every thread's stack and every wake-up adds up.", [
            "in the lab",
            (lambda: [FadeIn(s1)], 0.5),
            "2,028 threads",
            (lambda: [FadeIn(s2, shift=0.1 * UP)], 0.5),
            "and about 200",
            (lambda: [FadeIn(s3, shift=0.1 * UP)], 0.5),
            "almost all",
            (lambda: [FadeIn(s4)], 0.5),
            "At 10,000",
            (lambda: [FadeIn(s5, shift=0.1 * UP)], 0.6),
        ])

        tb = RoundedRectangle(corner_radius=0.16, width=3.3, height=1.5, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1)
        tb.move_to([TX, TY, 0])
        tt = T("one thread", 26).move_to([TX, TY + 0.3, 0])
        ts = tstate("waits on all of them")
        want = T("what we want: one thread, told which sockets have data", 22, BLUE_M).move_to([0, -2.3, 0])
        self.steps("What we want is one thread that waits on all of them, and is told which ones have data.", [
            (lambda: [FadeOut(VGroup(s1, s2, s3, s4, clab)), FadeOut(s5), FadeOut(caps)], 0.6),
            (lambda: [FadeIn(tb)], 0.5),
            (lambda: [FadeIn(tt), FadeIn(ts)], 0.5),
            "and is told",
            (lambda: [FadeIn(want, shift=0.1 * UP)], 0.6),
        ])

        band = Rectangle(width=3.8, height=0.36, stroke_width=0).set_fill(RED_M, 0.35).move_to(dots[0:10].get_center())
        rows = [dots[10 * r:10 * r + 10].get_center() for r in range(10)]
        spin = T("read, read, read …: nearly every read fails", 22, RED_M).move_to([0, -2.3, 0])
        self.steps("Asking each socket in turn doesn't work. A non-blocking read on a quiet socket fails at once, "
                   "so the loop burns a whole CPU on failures.", [
            (lambda: [FadeOut(want), FadeIn(band)], 0.3),
            (lambda: [band.animate(rate_func=linear).move_to(rows[9])], 1.3),
            (lambda: [band.animate.move_to(rows[0]), Transform(ts, tstate("CPU: 100%", RED_M))], 0.3),
            "fails at once",
            (lambda: [FadeIn(spin, shift=0.1 * UP)], 0.5),
            (lambda: [band.animate(rate_func=linear).move_to(rows[9])], 1.2),
        ])

        kb = RoundedRectangle(corner_radius=0.16, width=3.1, height=3.5, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1)
        kb.move_to([MX, GY, 0])
        kt = T("kernel", 26, TEAL_M).move_to([MX, GY + 1.4, 0])
        call = Arrow([TX - 1.75, TY + 0.3, 0], [MX + 1.65, TY + 0.3, 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.2)
        clab2 = VGroup(T("the whole list,", 18, GREY_B), T("every call", 18, GREY_B)).arrange(DOWN, buff=0.08)
        clab2.move_to([(TX - 1.75 + MX + 1.65) / 2, TY + 0.82, 0])
        kchk = T("checks all 10,000", 24).move_to([MX, GY + 0.6, 0])
        kfound = T("finds 3 ready", 24, GOLD_M).move_to([MX, GY + 0.05, 0])
        tband = band.copy().set_fill(TEAL_M, 0.35).move_to(rows[0])
        self.steps("The older calls, select and poll, hand the kernel the whole list every time. "
                   "The kernel checks all 10,000 sockets to find the three that are ready.", [
            (lambda: [FadeOut(band), FadeOut(spin), Transform(ts, tstate("calls select or poll")), FadeIn(kb), FadeIn(kt)], 0.7),
            "hand the kernel",
            (lambda: [GrowArrow(call), FadeIn(clab2)], 0.6),
            "The kernel checks",
            (lambda: [FadeIn(kchk), FadeIn(tband)], 0.4),
            (lambda: [tband.animate(rate_func=linear).move_to(rows[9])], 1.4),
            "to find the three",
            (lambda: [FadeOut(tband), FadeIn(kfound), *[dots[i].animate.set_color(GOLD_M).scale(1.5) for i in READY]], 0.6),
        ])

        ilab = T("interest list", 24).move_to([MX, GY + 0.85, 0])
        isub = T("all 10,000, added once", 19, GREY_B).move_to([MX, GY + 0.5, 0])
        frame = SurroundingRectangle(dots, color=TEAL_M, buff=0.14, corner_radius=0.1, stroke_width=2)
        self.steps("epoll splits that in two. The thread registers each socket once, and the kernel keeps the list.", [
            (lambda: [FadeOut(VGroup(call, clab2, kchk, kfound)), *[dots[i].animate.set_color(GREY_C).scale(1 / 1.5) for i in READY],
                      Transform(ts, tstate("epoll"))], 0.7),
            "registers each socket",
            (lambda: [Create(frame)], 0.8),
            "and the kernel keeps",
            (lambda: [FadeIn(ilab), FadeIn(isub)], 0.6),
        ])

        rlab = T("ready list", 24, GOLD_M).move_to([MX, GY - 0.25, 0])
        slots_x = [MX - 0.95, MX, MX + 0.95]
        slots = VGroup(*[RoundedRectangle(corner_radius=0.06, width=0.85, height=0.42, stroke_color=GREY_D, stroke_width=1.5)
                         .move_to([x, GY - 0.85, 0]) for x in slots_x])
        fds = [chip(f"fd {i}", GOLD_M, 16, mono=True).move_to([x, GY - 0.85, 0]) for i, x in zip(READY, slots_x)]
        self.steps("When bytes arrive, the kernel itself puts that socket on a ready list. Nobody had to check.", [
            (lambda: [FadeIn(rlab), FadeIn(slots)], 0.6),
            "When bytes arrive",
            (lambda: [LaggedStart(*[dots[i].animate.set_color(GOLD_M).scale(1.6) for i in READY], lag_ratio=0.4)], 0.8),
            "puts that socket",
            (lambda: [LaggedStart(*[TransformFromCopy(dots[i], f) for i, f in zip(READY, fds)], lag_ratio=0.4)], 1.2),
            "Nobody had",
            (lambda: [glow(kb, GOLD_M, 1.02)], 0.8),
        ])

        ret = Arrow([MX + 1.65, TY - 0.4, 0], [TX - 1.75, TY - 0.4, 0], buff=0, stroke_width=3, color=GOLD_M,
                    max_tip_length_to_length_ratio=0.2)
        got = VGroup(*[chip(f"fd {i}", GOLD_M, 16, mono=True) for i in READY]).arrange(RIGHT, buff=0.15).move_to([TX, TY - 1.25, 0])
        self.steps("The thread calls epoll wait. It sleeps until the ready list has something, then gets back just those three.", [
            (lambda: [Transform(ts, tstate("asleep in epoll_wait()", GREY_B))], 0.6),
            "It sleeps",
            (lambda: [tb.animate.set_fill(fillc(BLUE_M, 0.05), 1)], 0.6),
            "then gets back",
            (lambda: [GrowArrow(ret), tb.animate.set_fill(fillc(BLUE_M), 1), Transform(ts, tstate("woken: 3 ready", GOLD_M))], 0.6),
            (lambda: [*[ReplacementTransform(f, g) for f, g in zip(fds, got)]], 0.9),
        ])

        def serve(k):
            i = READY[k]
            return (lambda: [Transform(ts, tstate(f"answers fd {i}", WHITE)), got[k].animate.set_opacity(0.15),
                             dots[i].animate.set_color(GREY_C).scale(1 / 1.6)], 0.6)

        quiet = T("the 9,997 quiet sockets cost nothing", 22, GREEN_M).move_to([0, -2.3, 0])
        self.steps("It reads each one, answers, and asks again. Quiet connections cost nothing on each call.", [
            serve(0), serve(1), serve(2),
            "and asks again",
            (lambda: [FadeOut(got), FadeOut(ret), Transform(ts, tstate("asleep in epoll_wait()", GREY_B))], 0.6),
            "Quiet connections",
            (lambda: [FadeIn(quiet, shift=0.1 * UP)], 0.6),
        ])

        hdr = T("in the lab, 2,000 idle clients", 20, GREY_B)
        left(hdr, -6.3, -2.05)
        r1 = VGroup(left(T("a thread per connection", 24, RED_M), -6.3, -2.5), left(T("2,028 threads", 24, RED_M), 0.2, -2.5),
                    left(T("about 200 MB", 24, RED_M), 3.6, -2.5))
        r2 = VGroup(left(T("one Selector thread, on epoll", 24, GREEN_M), -6.3, -3.05), left(T("19 threads", 24, GREEN_M), 0.2, -3.05),
                    left(T("51 MB", 24, GREEN_M), 3.6, -3.05))
        self.steps("In the lab, a Selector server, which is epoll underneath, served the same 2,000 clients "
                   "with 19 threads and 51 megabytes.", [
            (lambda: [FadeOut(quiet), FadeIn(hdr), FadeIn(r1)], 0.8),
            "a Selector server",
            (lambda: [FadeIn(r2[0], shift=0.1 * UP)], 0.6),
            "with 19 threads",
            (lambda: [FadeIn(r2[1], shift=0.1 * UP)], 0.5),
            "and 51",
            (lambda: [FadeIn(r2[2], shift=0.1 * UP)], 0.5),
        ])

        users = VGroup(*[chip(s, BLUE_M, 16) for s in ("Netty", "Kafka client", "virtual threads")]).arrange(RIGHT, buff=0.2)
        users.move_to([TX - 0.3, -0.45, 0])
        self.steps("Netty, the Kafka client and Java's virtual threads all run this loop for you.", [
            (lambda: [LaggedStart(*[FadeIn(u, shift=0.1 * UP) for u in users], lag_ratio=0.4)], 1.2),
            (lambda: [glow(tb, BLUE_M, 1.04)], 0.8),
        ])

        self.steps("A thread per connection pays for every connection. epoll pays only for the ones with data.", [
            (lambda: [Indicate(r1, color=RED_M, scale_factor=1.04)], 1.0),
            "epoll pays",
            (lambda: [Indicate(r2, color=GREEN_M, scale_factor=1.04), glow(kb, GOLD_M, 1.02)], 1.0),
        ])
        self.wait(0.6)
