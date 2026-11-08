from sfz import *

SAY.insert(0, (r"\bpgactive\b", "P G active"))
SAY.insert(0, (r"\ball-to-all\b", "all to all"))   # hyphenated, Kokoro runs it into one word
SAY.insert(0, (r"\bM-0042\b", "M zero zero four two"))
SAY.insert(0, (r"\b38\.5%", "thirty eight and a half percent"))
SAY.insert(0, (r"\b12\.5%", "twelve and a half percent"))

EU, US, AP = np.array([-4.3, 1.45, 0]), np.array([4.3, 1.45, 0]), np.array([0, -1.55, 0])
PW, PH = 4.6, 1.45
CHIP_W, CHIP_H = 1.25, 0.46
COL = {"eu": BLUE_M, "us": GOLD_M, "ap": TEAL_M}


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


def leader(name, city, c):
    col = COL[name]
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=col, stroke_width=2.5)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(col), 0.08), opacity=1).move_to(c)
    head = VGroup(T(name, 30, col), T(city, 22, GREY_B)).arrange(RIGHT, buff=0.25, aligned_edge=DOWN)
    head.move_to(c + UP * (PH / 2 - 0.38))
    return VGroup(r, head)


def row(c, key, value, color=WHITE):
    """The one row each leader shows: a key on the left, a value on the right."""
    k = M(key, 20, GREY_B)
    v = M(value, 20, color)
    k.move_to(c + DOWN * 0.22 + LEFT * (PW / 2 - 0.3 - k.width / 2))
    v.move_to(c + DOWN * 0.22 + RIGHT * (PW / 2 - 0.3 - v.width / 2))
    return VGroup(k, v)


def solid_chip(text, color, size=20):
    t = M(text, size, WHITE)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=max(0.46, t.height + 0.24), stroke_color=color, stroke_width=2.5)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.3), opacity=1)
    return VGroup(r, t)


def ext(n, w, h):
    """Half-extent of a w x h box along unit direction n."""
    return abs(n[0]) * w / 2 + abs(n[1]) * h / 2


def side_label(txt, line, sign, along=0.0, gap=0.3):
    """Put txt beside line, far enough that a message chip sliding along the line never touches it."""
    a, b = line.get_start(), line.get_end()
    d = (b - a) / np.linalg.norm(b - a)
    n = sign * np.array([-d[1], d[0], 0])
    return txt.move_to((a + b) / 2 + n * (ext(n, CHIP_W, CHIP_H) + gap + ext(n, txt.width, txt.height)) + d * along)


def inset(line):
    """The stretch of a line a chip's centre can travel without the chip touching the boxes at its ends."""
    a, b = line.get_start(), line.get_end()
    d = (b - a) / np.linalg.norm(b - a)
    k = ext(d, CHIP_W, CHIP_H) + 0.08
    return a + d * k, b - d * k


def edge(a, b):
    d = (b - a) / np.linalg.norm(b - a)
    pa = exit_point(Rectangle(width=PW, height=PH).move_to(a), d) + 0.12 * d
    pb = exit_point(Rectangle(width=PW, height=PH).move_to(b), -d) - 0.12 * d
    return Line(pa, pb, stroke_width=2.5, color=GREY_C)


class MultiLeader(Base):
    """repl-05, sections 1-2: all-to-all multi-leader replication, an UPDATE that overtakes its INSERT,
    and what last write wins does to concurrent edits."""

    def construct(self):
        self.title_card("Many leaders", "an update that overtakes its insert")

        eu, us, ap = leader("eu", "Frankfurt", EU), leader("us", "Virginia", US), leader("ap", "Asia Pacific", AP)
        eu_us, eu_ap, us_ap = edge(EU, US), edge(EU, AP), edge(US, AP)
        self.steps("A payments company runs a database leader in three regions. Each takes its own customers' writes, "
                   "and sends every change to the other two.", [
            (lambda: [LaggedStart(*[FadeIn(p, scale=0.95) for p in (eu, us, ap)], lag_ratio=0.3)], 1.6),
            "and sends",
            (lambda: [Create(eu_us), Create(eu_ap), Create(us_ap)], 1.2),
        ])

        l_eu_us = side_label(T("40 ms", 24, GREY_B), eu_us, 1)
        l_us_ap = side_label(T("30 ms", 24, GREY_B), us_ap, 1, along=-0.5)
        l_eu_ap = side_label(VGroup(T("150 ms", 24, RED_M), T("slow today", 22, RED_M)).arrange(DOWN, buff=0.08), eu_ap, -1, along=-0.5)
        self.steps("This is all-to-all replication. Today the link from Europe to Asia is slow: 150 milliseconds.", [
            (lambda: [FadeIn(l_eu_us), FadeIn(l_us_ap)], 0.8),
            "Today the link",
            (lambda: [FadeIn(l_eu_ap), eu_ap.animate.set_color(RED_M)], 0.9),
        ])

        # ---- one clock drives every message in flight ------------------------------------------------------
        clock = ValueTracker(0)
        cache = {}

        def clock_t():
            s = f"t = {int(round(clock.get_value()))} ms"
            if s not in cache:
                cache[s] = T(s, 30)
            return cache[s].copy().move_to([0, 3.15, 0])
        clk = always_redraw(clock_t)

        def flight(label, color, line, start, dur, reverse=False):
            c = solid_chip(label, color)
            pa, pb = inset(line)
            if reverse:
                pa, pb = pb, pa

            def upd(m):
                t = clock.get_value()
                if start <= t < start + dur:
                    m.move_to(pa + (pb - pa) * (t - start) / dur)
                else:
                    m.move_to([0, 30, 0])
            c.add_updater(upd)
            return c

        ins_us = flight("INSERT", BLUE_M, eu_us, 0, 40)
        ins_ap = flight("INSERT", BLUE_M, eu_ap, 0, 150)
        upd_ap = flight("UPDATE", GOLD_M, us_ap, 45, 30)
        upd_eu = flight("UPDATE", GOLD_M, eu_us, 45, 40, reverse=True)

        key = "pay-81723"
        r_eu = row(EU, key, "AUTHORIZED", BLUE_M)
        r_us = row(US, key, "no row", GREY_D)
        r_ap = row(AP, key, "no row", GREY_D)
        self.steps("At time zero, Europe inserts a payment as authorized, and sends the insert to both.", [
            (lambda: [FadeIn(clk), FadeIn(r_us), FadeIn(r_ap)], 0.6),
            (lambda: [FadeIn(r_eu, shift=0.1 * UP)], 0.7),
            "and sends",
            (lambda: [*[FadeIn(m) for m in (ins_us, ins_ap, upd_ap, upd_eu)], clock.animate(rate_func=linear).set_value(20)], 1.6),
        ])

        def setv(r, c, s, color):
            return Transform(r[1], row(c, key, s, color)[1])

        self.steps("The US gets it at 40 milliseconds, and at 45 it captures the payment: an update to captured.", [
            (lambda: [clock.animate(rate_func=linear).set_value(40)], 1.2),
            (lambda: [setv(r_us, US, "AUTHORIZED", BLUE_M)], 0.6),
            "at 45",
            (lambda: [clock.animate(rate_func=linear).set_value(45)], 0.6),
            (lambda: [setv(r_us, US, "CAPTURED", GOLD_M)], 0.8),
        ])

        self.steps("It sends the update on. Its link to Asia takes only 30 milliseconds.", [
            (lambda: [clock.animate(rate_func=linear).set_value(62)], 2.4),
            "Its link",
            (lambda: [Indicate(l_us_ap, color=GOLD_M)], 1.0),
        ])

        miss = T("update for a row it doesn't have", 22, RED_M).next_to(ap, DOWN, buff=0.18)
        self.steps("So at 75 milliseconds, the update reaches Asia before the insert. Asia has no such row.", [
            (lambda: [clock.animate(rate_func=linear).set_value(75)], 1.6),
            "Asia has no",
            (lambda: [FadeIn(miss), Indicate(r_ap[1], color=RED_M)], 1.0),
        ])

        drop = T("pgactive's default: discard the update", 22, RED_M).next_to(ap, DOWN, buff=0.18)
        self.steps("pgactive, an active-active extension for PostgreSQL, discards such an update by default.", [
            (lambda: [Transform(miss, drop)], 1.0),
        ])

        bad = T("eu and us: CAPTURED.  ap: AUTHORIZED, for good.", 26, RED_M)
        self.steps("At 150 milliseconds the insert arrives. Europe and the US say captured. "
                   "Asia says authorized, and nothing left in flight can repair it.", [
            (lambda: [clock.animate(rate_func=linear).set_value(85)], 0.6),
            (lambda: [setv(r_eu, EU, "CAPTURED", GOLD_M)], 0.5),
            (lambda: [clock.animate(rate_func=linear).set_value(150)], 1.6),
            (lambda: [setv(r_ap, AP, "AUTHORIZED", RED_M), FadeOut(miss)], 0.6),
            "Asia says",
            (lambda: [Indicate(r_ap[1], color=RED_M), ap[0].animate.set_stroke(RED_M)], 1.0),
        ])

        skew = T("us clock 60 ms behind", 22, RED_M).next_to(us, UP, buff=0.18)
        self.steps("Timestamps don't help either. If the US clock runs 60 milliseconds behind, the capture gets an earlier stamp than the insert. "
                   "Keep the later stamp, and every region throws the capture away.", [
            "If the US clock",
            (lambda: [FadeIn(skew)], 0.8),
            "and every region",
            (lambda: [setv(r_eu, EU, "AUTHORIZED", RED_M), setv(r_us, US, "AUTHORIZED", RED_M)], 1.0),
        ])

        # ---- last write wins on concurrent edits ------------------------------------------------------------
        hkey = "M-0042 holds"
        h_eu = row(EU, hkey, "h-eu", BLUE_M)
        h_us = row(US, hkey, "h-us", GOLD_M)
        lww = chip("last write wins", RED_M, 26).move_to([0, 3.15, 0])
        self.steps("That rule, keep the later stamp, is called last write wins. It also settles two regions editing the same row at once.", [
            (lambda: [FadeOut(skew), FadeOut(clk), *[FadeOut(r) for r in (r_eu, r_us, r_ap)],
                      FadeOut(ap), FadeOut(us_ap), FadeOut(eu_ap), FadeOut(l_us_ap), FadeOut(l_eu_ap), FadeOut(l_eu_us)], 1.0),
            "last write wins",
            (lambda: [FadeIn(lww, shift=0.15 * DOWN)], 0.8),
        ])

        st_eu = T("10:00:00.000", 22, GREY_B).next_to(eu, DOWN, buff=0.18)
        st_us = T("10:00:00.010", 22, GREY_B).next_to(us, DOWN, buff=0.18)
        ok_eu = tick(True, 0.16).next_to(st_eu, RIGHT, buff=0.2)
        ok_us = tick(True, 0.16).next_to(st_us, RIGHT, buff=0.2)
        self.steps("Europe adds hold h-eu to merchant M-0042. Ten milliseconds later, before that crosses the ocean, "
                   "the US adds hold h-us. Both are told OK.", [
            (lambda: [FadeIn(h_eu, shift=0.1 * UP), FadeIn(st_eu)], 0.8),
            "the US adds",
            (lambda: [FadeIn(h_us, shift=0.1 * UP), FadeIn(st_us)], 0.8),
            "Both are told",
            (lambda: [Create(ok_eu), Create(ok_us)], 0.6),
        ])

        m1 = solid_chip("h-eu  .000", BLUE_M)
        m2 = solid_chip("h-us  .010", GOLD_M)
        for f in (ins_us, ins_ap, upd_ap, upd_eu):
            f.clear_updaters()
            self.remove(f)
        a0, a1 = eu_us.get_start(), eu_us.get_end()
        k = max(m1.width, m2.width) / 2 + 0.2
        p0, p1 = a0 + RIGHT * k, a1 + LEFT * k
        m1.move_to(p0 + 0.3 * UP)
        m2.move_to(p1 + 0.3 * DOWN)
        lost = T("h-eu is gone, and no error anywhere", 30, RED_M).move_to([0, -0.4, 0])
        self.steps("The changes cross, and each leader keeps the newer one. "
                   "Both end with h-us, and hold h-eu is gone, with no error anywhere.", [
            (lambda: [FadeIn(m1), FadeIn(m2)], 0.4),
            (lambda: [m1.animate.move_to(p1 + 0.3 * UP), m2.animate.move_to(p0 + 0.3 * DOWN)], 1.6),
            "Both end with",
            (lambda: [FadeOut(m1), FadeOut(m2), Transform(h_eu[1], row(EU, hkey, "h-us", GOLD_M)[1])], 0.9),
            "and hold h-eu",
            (lambda: [FadeIn(lost, shift=0.15 * UP)], 0.9),
        ])

        nums = VGroup(T("lab, 20 to 80 ms of lag:", 24, GREY_B),
                      T("writes 5 s apart: 1% lost", 24), T("300 ms apart: 12.5%", 24), T("50 ms apart: 38.5%", 24, RED_M))
        nums.arrange(RIGHT, buff=0.45).move_to([0, -2.1, 0])
        fit(nums, 13.0)
        self.steps("In the lesson's lab, with writes 50 milliseconds apart, 38.5% of acknowledged holds vanish.", [
            (lambda: [FadeIn(nums[0]), FadeIn(nums[1]), FadeIn(nums[2])], 1.0),
            "with writes 50",
            (lambda: [FadeIn(nums[3], shift=0.15 * UP)], 0.8),
        ])

        self.steps("With many leaders, a change can arrive before the change it depends on, and a clock can't put them back in order.", [
            (lambda: [Indicate(lww, color=RED_M)], 1.4),
        ])
        self.wait(0.6)
