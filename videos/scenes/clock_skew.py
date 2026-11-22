from sfz import *

# "pod A": Kokoro reads a lone capital A as the article "uh".
SAY.insert(0, (r"\b([Pp])od A\b", r"\1od eh"))
# "charj-i-back" otherwise.
SAY.insert(0, (r"\bchargeback\b", "charge-back"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PX, PW, PH = -4.9, 2.6, 0.95            # the two writers (tills, then pods)
PA_Y, PB_Y = 2.6, 1.25
SX, SY, SW, SH = 4.3, 1.9, 3.2, 2.3     # the store (the owner's book)
CHX = -0.5                              # where a write appears
TRUE_Y, STAMP_Y = -0.5, -1.8            # the two rulers
RMIN, RMAX, RX0, RS = -12, 24, -4.3, 0.28   # ms around 10:00:00.000; x of RMIN; units per ms
CAP_Y, BAR_Y = -3.25, -2.92


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

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

    def gather(self, g):
        """Make a group of parts already on screen into one object on screen, so it can be transformed as a whole."""
        self.remove(*g.submobjects)
        self.add(g)
        return g

    def col(self, c):
        self.sil_col = c
        return [Wait(0.01)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])



def pod(y, name, clock, color):
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([PX, y, 0])
    return VGroup(r, T(name, 26).move_to([PX, y + 0.17, 0]), T(clock, 17, GREY_B).move_to([PX, y - 0.22, 0]))


def tx(ms):
    return RX0 + RS * (ms - RMIN)


def wchip(name, stamp, color):
    t = VGroup(T(name, 22, color), M(stamp, 18, GREY_B)).arrange(RIGHT, buff=0.25)
    r = RoundedRectangle(corner_radius=0.1, width=t.width + 0.4, height=0.55, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r))


class ClockSkew(Base):
    """dist-03, section 2. Two tills, one 15 s slow: the owner keeps the latest receipt and the return vanishes. Last
    write wins with client stamps (Cassandra). pod-b 15 ms behind: captured kept, refunded dropped with an OK, settled
    kept, chargeback dropped. Two rulers, true time and stamps. 5 ms loses nothing, 7 ms loses the refund: the skew only
    has to beat the 6 ms gap between causally related writes. 4%, 14%, 50%; Jepsen's 285 of 1,009. Never let two
    machines' clocks decide; keep every receipt. Moral, and a check (the fast clock wins)."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("The refund that came second", "and the clock that threw it away")

        # ---------------- scene 1: two tills ----------------
        ta = pod(PA_Y, "till A", "clock right", BLUE_M)
        tb = pod(PB_Y, "till B", "clock 15 s slow", GOLD_M)
        store = RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to([SX, SY, 0])
        st_title = T("the owner's book", 22, GREY_B).move_to([SX, SY + 0.7, 0])
        self.steps("Picture a shop with two tills. Each one prints the time on every receipt. Till B runs fifteen seconds slow, and nobody knows.", [
            (lambda: [FadeIn(ta, shift=0.1 * RIGHT), FadeIn(tb, shift=0.1 * RIGHT)], 0.8),
            "Till B runs",
            (lambda: [glow(tb[0], GOLD_M)], 0.8),
        ])
        sale = wchip("jacket sold", "12:00:00", BLUE_M).move_to([CHX, PA_Y, 0])
        ret = wchip("jacket returned", "11:59:55", GOLD_M).move_to([CHX, PB_Y, 0])
        self.steps("A customer buys a jacket at till A. Ten seconds later, she returns it at till B.", [
            "buys a jacket",
            (lambda: [FadeIn(sale, shift=0.2 * RIGHT)], 0.6),
            "Ten seconds later",
            (lambda: [FadeIn(ret, shift=0.2 * RIGHT), *self.cap("till B: really 12:00:10, minus 15 s = 11:59:55", GOLD_M)], 0.6),
        ])
        val = T("jacket sold", 28, BLUE_M).move_to([SX, SY, 0])
        self.steps("That evening, the owner keeps only the latest receipt for each item. "
                   "By the printed times, the return came five seconds before the sale. So she keeps the sale.", [
            (lambda: [FadeIn(store), FadeIn(st_title)], 0.6),
            "By the printed",
            (lambda: [*self.cap("11:59:55 is before 12:00:00", GOLD_M)], 0.5),
            "So she keeps",
            (lambda: [sale.animate.move_to([SX, SY - 0.05, 0]).set_opacity(0), FadeIn(val),
                      ret.animate.set_opacity(0.25)], 0.8),
        ])
        self.steps("The books now say the jacket was never returned. Which receipt really came last? And why did a clock get to decide?", [
            (lambda: [ret.animate.set_opacity(0), *self.cap("the return: gone", RED_M)], 0.7),
            "Which receipt",
            (lambda: [*self.cap("which receipt really came last?", WHITE, 28)], 0.5),
        ])
        self.remove(sale, ret)

        # ---------------- scene 2: last write wins ----------------
        self.steps("It's tempting to trust printed times. Your phone always seems right. "
                   "But right means within a few milliseconds, sometimes more. And computers do things a few milliseconds apart.", [
            (lambda: [*self.cap("\"right\": within a few milliseconds, sometimes more", GREY_B)], 0.5),
            "And computers",
            (lambda: [*self.cap("computers do things a few milliseconds apart", YELLOW_M)], 0.5),
        ])
        self.steps("Many databases use the owner's rule. When two writes hit the same item, keep the one with the highest timestamp, "
                   "and drop the other. It's called last write wins.", [
            "keep the one",
            (lambda: [glow(store, WHITE)], 0.8),
            "last write wins",
            (lambda: [*self.cap("last write wins: keep the highest stamp, drop the rest", WHITE)], 0.5),
        ])
        self.steps("Cassandra, a database that spreads data over many machines, takes those stamps from the program that sends the write, "
                   "read from that machine's own clock.", [
            "takes those stamps",
            (lambda: [glow(ta[0], BLUE_M), glow(tb[0], GOLD_M)], 0.8),
        ])
        pa = pod(PA_Y, "pod-a", "clock exact", BLUE_M)
        pb = pod(PB_Y, "pod-b", "clock 15 ms behind", GOLD_M)
        st2 = T("payment status", 22, GREY_B).move_to(st_title)
        self.steps("So here are our tills: two copies of the payments program, pod A and pod B. Each stamps its writes with its own clock, "
                   "and pod B's clock is fifteen milliseconds behind. The owner's book is the store: one payment's status, and its stamp.", [
            (lambda: [*self.uncap(), Transform(ta, pa), FadeOut(val)], 0.8),
            "pod B's clock",
            (lambda: [Transform(tb, pb)], 0.8),
            "The owner's book",
            (lambda: [Transform(st_title, st2)], 0.6),
        ])

        # the two rulers
        def ruler(y, name):
            ln = Line([tx(RMIN), y, 0], [tx(RMAX), y, 0], stroke_width=2, color=GREY_C)
            return VGroup(ln, right_at(T(name, 20, GREY_B), RX0 - 0.25, y))

        r_true, r_st = ruler(TRUE_Y, "true time"), ruler(STAMP_Y, "stamp")
        ticks = VGroup(*[VGroup(Line([tx(m), STAMP_Y - 0.08, 0], [tx(m), STAMP_Y + 0.08, 0], stroke_width=2, color=GREY_C),
                                M(lbl, 15, GREY_B).move_to([tx(m), STAMP_Y - 0.33, 0]))
                         for m, lbl in [(-10, "09:59:59.990"), (0, "10:00:00.000"), (10, ".010"), (20, ".020")]])
        zero = DashedLine([tx(0), TRUE_Y + 0.15, 0], [tx(0), STAMP_Y + 0.12, 0], dash_length=0.06, stroke_width=1.2, color=GREY_D)
        self.steps("Let's draw two lines. On top, true time, in thousandths of a second around ten o'clock. Underneath, the stamp each write carries.", [
            "On top",
            (lambda: [Create(r_true[0]), FadeIn(r_true[1])], 0.6),
            "Underneath",
            (lambda: [Create(r_st[0]), FadeIn(r_st[1]), FadeIn(ticks), Create(zero)], 0.8),
        ])

        # ---------------- scene 3: the trace ----------------
        self.value = None

        def set_value(name, stamp, color):
            v = VGroup(T(name, 30, color), M(stamp, 20, GREY_B)).arrange(DOWN, buff=0.2).move_to([SX, SY - 0.2, 0])
            old, self.value = self.value, v
            return [swap(old, v)]

        def send(chip, y):
            return chip.animate.move_to([SX - SW / 2 - chip.width / 2 - 0.15, y, 0])

        def ok_back(y):
            o = T("OK", 22, GREEN_M).move_to([SX - SW / 2 - 0.4, (y + SY) / 2, 0])
            return Succession(FadeIn(o, run_time=0.1), o.animate(run_time=0.7).move_to([PX + PW / 2 + 0.35, y, 0]), FadeOut(o, run_time=0.2))

        def mark(ms, y, color, name=None, up=True):
            d = Dot(radius=0.09, color=color).move_to([tx(ms), y, 0])
            if name is None:
                return d
            lab = T(name, 17, color).move_to([tx(ms), y + (0.3 if up else -0.3), 0])
            return VGroup(d, lab)

        def link(t_ms, s_ms, color):
            return DashedLine([tx(t_ms), TRUE_Y - 0.1, 0], [tx(s_ms), STAMP_Y + 0.1, 0], dash_length=0.06, stroke_width=1.5, color=color)

        c1 = wchip("captured", "10:00:00.002", BLUE_M).move_to([CHX, PA_Y, 0])
        m1 = mark(2, TRUE_Y, BLUE_M, "captured")
        s1 = mark(2, STAMP_Y, BLUE_M)
        l1 = link(2, 2, BLUE_M)
        self.steps("pod A writes captured: the money has moved. Its stamp is two thousandths past ten. "
                   "The store is empty, so it keeps it, and says OK.", [
            (lambda: [FadeIn(c1, shift=0.2 * RIGHT), FadeIn(m1, scale=0.6)], 0.6),
            "Its stamp",
            (lambda: [Create(l1), FadeIn(s1, scale=0.6)], 0.6),
            "so it keeps",
            (lambda: [send(c1, PA_Y)], 0.6),
            (lambda: [FadeOut(c1), *set_value("captured", "10:00:00.002", BLUE_M)], 0.5),
            "says OK",
            (lambda: [ok_back(PA_Y)], 1.0),
        ])
        self.stamp("captured")
        m2 = mark(8, TRUE_Y, GOLD_M, "refunded")
        self.steps("pod B reads the status, sees captured, and six thousandths later writes refunded. "
                   "This write was decided after seeing the first one. So it's later by cause, and later in real time.", [
            "reads the status",
            (lambda: [Indicate(self.value, color=GOLD_M)], 0.6),
            "writes refunded",
            (lambda: [FadeIn(m2, scale=0.6)], 0.5),
            (lambda: [*self.cap("6 ms after captured, and because of it", GOLD_M)], 0.5),
        ])
        c2 = wchip("refunded", "09:59:59.993", GOLD_M).move_to([CHX, PB_Y, 0])
        s2 = mark(-7, STAMP_Y, GOLD_M)
        l2 = link(8, -7, GOLD_M)
        self.steps("But pod B's clock is fifteen behind, so its stamp says seven thousandths before ten.", [
            (lambda: [FadeIn(c2, shift=0.2 * RIGHT), *self.uncap()], 0.6),
            "its stamp",
            (lambda: [Create(l2), FadeIn(s2, scale=0.6)], 0.8),
        ])
        self.steps("The store compares the stamps. What does it keep, and what does it tell pod B? Pause and guess.", [
            (lambda: [send(c2, PB_Y)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        lost2 = tick(False, 0.13).move_to(s2.get_center() + 0.7 * DOWN)
        self.steps("It keeps captured, and drops the refund. And it tells pod B: OK.", [
            (lambda: [*self.uncap(), *self.cap("09:59:59.993 is lower than 10:00:00.002: dropped", RED_M)], 0.5),
            "drops the refund",
            (lambda: [c2.animate.set_opacity(0), s2.animate.set_color(RED_M), Create(lost2), Indicate(self.value, color=BLUE_M)], 0.8),
            "tells pod B",
            (lambda: [ok_back(PB_Y)], 1.0),
        ])
        self.remove(c2)
        self.steps("Very polite. The refund was confirmed, it's gone, and nothing logged an error.", [
            (lambda: [*self.cap("confirmed, and gone; no error anywhere", RED_M)], 0.5),
        ])
        c3 = wchip("settled", "10:00:00.014", BLUE_M).move_to([CHX, PA_Y, 0])
        m3, s3, l3 = mark(14, TRUE_Y, BLUE_M, "settled"), mark(14, STAMP_Y, BLUE_M), link(14, 14, BLUE_M)
        self.steps("pod A writes settled: paid out to the shop. Stamp, fourteen past. Higher than two, so it's kept.", [
            (lambda: [*self.uncap(), FadeIn(c3, shift=0.2 * RIGHT), FadeIn(m3, scale=0.6)], 0.6),
            "Stamp",
            (lambda: [Create(l3), FadeIn(s3, scale=0.6)], 0.5),
            "so it's kept",
            (lambda: [send(c3, PA_Y)], 0.5),
            (lambda: [FadeOut(c3), *set_value("settled", "10:00:00.014", BLUE_M), ok_back(PA_Y)], 1.0),
        ])
        c4 = wchip("chargeback", "10:00:00.005", GOLD_M).move_to([CHX, PB_Y, 0])
        m4, s4, l4 = mark(20, TRUE_Y, GOLD_M, "chargeback"), mark(5, STAMP_Y, GOLD_M), link(20, 5, GOLD_M)
        lost4 = tick(False, 0.13).move_to(s4.get_center() + 0.7 * DOWN)
        self.steps("pod B writes chargeback: the customer's bank took the money back. Its stamp, five past. "
                   "Lower than fourteen. Dropped, and OK again.", [
            (lambda: [FadeIn(c4, shift=0.2 * RIGHT), FadeIn(m4, scale=0.6)], 0.6),
            "Its stamp",
            (lambda: [Create(l4), FadeIn(s4, scale=0.6)], 0.6),
            "Lower than",
            (lambda: [send(c4, PB_Y)], 0.6),
            "Dropped",
            (lambda: [c4.animate.set_opacity(0), s4.animate.set_color(RED_M), Create(lost4)], 0.5),
            (lambda: [ok_back(PB_Y)], 1.0),
        ])
        self.remove(c4)
        self.stamp("four")
        self.steps("Four writes, four OKs, two gone. Look at the two lines. In true time, the writes take turns. "
                   "By the stamps, every pod B write slides fifteen thousandths to the left, behind the pod A write it followed.", [
            (lambda: [*self.cap("4 writes, 4 OKs, 2 gone", RED_M, 28)], 0.5),
            "In true time",
            (lambda: [Indicate(VGroup(m1, m2, m3, m4), color=WHITE, scale_factor=1.1)], 0.9),
            "slides fifteen",
            (lambda: [glow(l2, RED_M, 1.0), glow(l4, RED_M, 1.0)], 1.0),
        ])
        self.steps("And pod B keeps losing like this, until its clock passes the highest stamp pod A wrote.", [
            (lambda: [*self.cap("pod B loses until its clock passes pod A's highest stamp", GOLD_M)], 0.5),
        ])

        # ---------------- scene 4: how much skew? ----------------
        sk = T("clock 15 ms behind", 17, GREY_B).move_to(tb[2])
        self.remove(tb[2])
        self.add(sk)
        self.sk = sk

        def skew(ms, ok2, ok4):
            new = T(f"clock {ms} ms behind", 17, YELLOW_M).move_to([PX, PB_Y - 0.22, 0])
            old, self.sk = self.sk, new
            st2_, st4_ = 8 - ms, 20 - ms
            out = [swap(old, new),
                   s2.animate.move_to([tx(st2_), STAMP_Y, 0]).set_color(GREEN_M if ok2 else RED_M),
                   s4.animate.move_to([tx(st4_), STAMP_Y, 0]).set_color(GREEN_M if ok4 else RED_M),
                   Transform(l2, link(8, st2_, GOLD_M)), Transform(l4, link(20, st4_, GOLD_M)),
                   lost2.animate.move_to([tx(st2_), STAMP_Y - 0.7, 0]).set_opacity(0 if ok2 else 1),
                   lost4.animate.move_to([tx(st4_), STAMP_Y - 0.7, 0]).set_opacity(0 if ok4 else 1)]
            return out

        self.steps("You might think: fifteen thousandths is a big error, so better clocks fix this. Let's test that. "
                   "Shrink pod B's error to five.", [
            (lambda: [*self.cap("better clocks fix this?", PURPLE_M, 28)], 0.5),
            "Shrink",
            (lambda: skew(5, True, True), 1.2),
        ])
        self.steps("Now the refund's stamp is three past, above captured's two. Kept. Nothing lost.", [
            (lambda: [*self.cap("5 ms behind: refunded .003 > captured .002: kept", GREEN_M)], 0.5),
            "Nothing lost",
            (lambda: [Indicate(s2, color=GREEN_M, scale_factor=1.6), Indicate(s4, color=GREEN_M, scale_factor=1.6)], 0.8),
        ])
        self.steps("Now seven. The stamp is one past. Below two. Lost again.", [
            (lambda: skew(7, False, False), 1.2),
            "Lost again",
            (lambda: [*self.cap("7 ms behind: refunded .001 < captured .002: lost", RED_M)], 0.5),
        ])
        self.stamp("seven")
        gap = VGroup(Line([tx(2), TRUE_Y + 0.62, 0], [tx(8), TRUE_Y + 0.62, 0], stroke_width=3, color=YELLOW_M),
                     T("6 ms", 18, YELLOW_M).move_to([tx(5), TRUE_Y + 0.88, 0]))
        self.steps("So the skew doesn't need to be big. It only has to be bigger than the gap between two writes "
                   "where the second was decided after seeing the first. Writes like that are called causally related. Here the gap is six thousandths.", [
            "bigger than the gap",
            (lambda: [Create(gap[0]), FadeIn(gap[1])], 0.6),
            "causally related",
            (lambda: [*self.cap("causally related: the second write was decided after seeing the first", WHITE)], 0.5),
        ])
        self.steps("Add some thinking time between the writes, and the lab counts the damage. Ten milliseconds of skew loses four percent "
                   "of confirmed writes. Twenty loses fourteen percent. A hundred or more loses half.", [
            (lambda: [*self.cap("skew 10 ms: 4% of confirmed writes lost", GOLD_M)], 0.5),
            "Twenty",
            (lambda: [*self.cap("skew 10 ms: 4%.   20 ms: 14%", GOLD_M)], 0.5),
            "A hundred",
            (lambda: [*self.cap("skew 10 ms: 4%.   20 ms: 14%.   100 ms or more: 50%", RED_M)], 0.5),
        ])
        self.steps("Why stop at half? By then every pod B write that follows a pod A write is lost, and every pod A write survives. "
                   "And over the internet, clock errors of ten to twenty milliseconds are ordinary.", [
            "every pod B write",
            (lambda: [Indicate(VGroup(s2, s4), color=RED_M, scale_factor=1.5)], 0.8),
            "over the internet",
            (lambda: [*self.cap("over the internet, clocks 10 to 20 ms off are ordinary", WHITE)], 0.5),
        ])
        self.steps("It happened for real. In 2013, Kyle Kingsbury tested Cassandra with writers that took turns behind a perfect lock. "
                   "It still lost 285 of 1,009 confirmed writes, about twenty-eight percent. The stamps, not the lock, decided which write survived.", [
            "It still lost",
            (lambda: [*self.cap("Jepsen, 2013: 285 of 1,009 confirmed writes lost, about 28%", RED_M)], 0.5),
        ])

        # ---------------- scene 5: the rule, and the fix ----------------
        self.steps("So here's the rule. Never let two machines' clocks decide which write wins.", [
            (lambda: [*self.cap("never let two machines' clocks decide which write wins", YELLOW_M, 28)], 0.6),
        ], after=0.6)
        rows = VGroup(*[T(n, 20, c) for n, c in
                        [("captured", BLUE_M), ("refunded", GOLD_M), ("settled", BLUE_M), ("chargeback", GOLD_M)]])
        rows.arrange(DOWN, buff=0.1).move_to([SX, SY - 0.38, 0])
        self.steps("Better clocks shrink the window. They don't close it. The fixes stop comparing stamps from different machines. "
                   "Back in the shop: keep every receipt, not just the latest.", [
            "Back in the shop",
            (lambda: [*self.cap("keep every receipt, not just the latest", GREEN_M, 28), *([FadeOut(self.value)] if self.value else []),
                      Transform(st_title, T("every status change", 22, GREY_B).move_to(st_title))], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * DOWN) for r in rows], lag_ratio=0.3)], 1.2),
        ])
        self.value = None
        self.steps("In a database, that's one new row for each status change, never overwritten, and you read them all. "
                   "Or you make the order explicit, with a write that applies only if the value is still the one you read. Later lessons build those.", [
            (lambda: [*self.cap("one row per change, never overwritten; read them all", WHITE)], 0.5),
            "Or you make",
            (lambda: [*self.cap("or: a write that applies only if the value is still the one you read", WHITE)], 0.5),
        ])

        # ---------------- scene 6: the moral, and a check ----------------
        self.steps("So, which receipt came last? The clock never knew. It only knew what it printed. "
                   "Two clocks can't put two machines' writes in order, so don't ask them to.", [
            (lambda: [*self.cap("which receipt came last?", WHITE, 28)], 0.5),
            "The clock never",
            (lambda: [glow(tb[0], GOLD_M)], 0.8),
            "Two clocks",
            (lambda: [*self.cap("two clocks can't order two machines' writes", YELLOW_M, 28)], 0.5),
        ])
        self.steps("One quick check. Flip it. Pod B's clock now runs fifteen milliseconds ahead. Whose writes get lost? Pause and think.", [
            (lambda: [*self.uncap(), *self.put("flip", T("clock 15 ms ahead", 17, YELLOW_M).move_to([PX, PB_Y - 0.22, 0])),
                      FadeOut(self.sk)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Pod A's. Last write wins always favours the fast clock. The slow one loses, and nobody gets an error.", [
            (lambda: [*self.uncap(), glow(ta[0], RED_M)], 0.8),
            "always favours",
            (lambda: [*self.cap("last write wins favours the fast clock; the slow one loses, silently", YELLOW_M)], 0.5),
        ])
        self.wait(2.0)
