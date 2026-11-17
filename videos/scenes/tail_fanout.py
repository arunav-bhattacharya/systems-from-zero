from sfz import *

SAY.insert(0, (r"\b0\.99\b", "zero point nine nine"))
SAY.insert(0, (r"\b0\.37\b", "zero point three seven"))
SAY.insert(0, (r"\bidempotency\b", "eye-dem-potency"))
SAY.insert(0, (r"\bidempotent\b", "eye-dem-potent"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
S, G = 0.30, 0.08                  # slot size and gap
STEP = S + G
GX, GY = -0.75, 0.55               # centre of the tray
SLOW = 39                          # row 4, column 10: the unlucky slot
TRAY = 10 * STEP - G + 0.36
TR_X0, TR_X1, TR_TOP, TR_BOT = GX - TRAY / 2, GX + TRAY / 2, GY + TRAY / 2, GY - TRAY / 2
PH_C, PH_W, PH_H = np.array([-5.1, 0.55, 0]), 1.7, 3.0    # the owner's phone
HOOK = 1.5
LAB_Y, ICON_Y, CAP_Y, BAR_Y = -1.85, -2.45, -3.2, -2.78
SEED = 9                           # ten trays, six of them late (one random run, see the script)


def lpos(i):
    r, c = divmod(i, 10)
    return np.array([GX - 4.5 * STEP + c * STEP, GY + 4.5 * STEP - r * STEP, 0])


RP = np.array([4.6, lpos(SLOW)[1], 0])     # the second cook, later the replica
RP_W, RP_H = 2.1, 0.7
TS = np.array([4.6, -0.85, 0])             # the shared toaster
TS_W, TS_H = 2.6, 0.7


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def run_on(path, color=YELLOW_M, rt=0.8):
    """A dot that runs along a line or an arc."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start())
    line = Line(path.get_start(), path.get_end()) if isinstance(path, Line) else path
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, line, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


# ---- the pieces ----
def phone():
    body = RoundedRectangle(corner_radius=0.25, width=PH_W, height=PH_H, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(PH_C)
    screen = RoundedRectangle(corner_radius=0.12, width=PH_W - 0.24, height=PH_H - 0.62, stroke_width=0).set_fill("#15191d", 1)
    screen.move_to(PH_C + 0.02 * DOWN)
    slot = Line(PH_C + [-0.2, PH_H / 2 - 0.15, 0], PH_C + [0.2, PH_H / 2 - 0.15, 0], stroke_width=3, color=GREY_C)
    return VGroup(body, screen, slot, T("home screen", 18, GREY_B).move_to(PH_C + [0, 0.85, 0]),
                  T("to appear", 16, GREY_B).move_to(PH_C + [0, -0.5, 0]))


def tray_box():
    return RoundedRectangle(corner_radius=0.14, width=TRAY, height=TRAY, stroke_color=GREY_B, stroke_width=3).move_to([GX, GY, 0])


def slot(i):
    return RoundedRectangle(corner_radius=0.05, width=S, height=S, stroke_width=2, stroke_color=GREY_C).set_fill(BLACK, 1).move_to(lpos(i))


def side_box(label, color, c, w, h, size=22):
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return r, T(label, size).move_to(c)


class TailFanout(Base):
    """found-02, section 3. The café owner's home screen waits for 100 answers, each slow one time in a hundred, and is
    slow most of the time. A kitchen tray of 100 sandwiches that leaves only when every slot is full; ten trays, six
    late; 0.99 to the power 100 is 0.37. Fan-out, the tail, tail latency amplification. A second cook (a replica)
    makes the same sandwich: the hedged request. When it can't help: a shared toaster, and requests that aren't
    safe to run twice. Moral and a check question."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = (T(s, size, color) if isinstance(s, str) else s)
        fit(new, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_lab(self, s, color=GREY_B):
        new = T(s, 22, color).move_to([GX, LAB_Y, 0])
        old, self.lab = self.lab, new
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.lab = None
        self.title_card("Waiting for a hundred answers", "fan-out, the tail, and a second copy")

        rng = np.random.default_rng(7)
        base = list(rng.uniform(5, 15, 100))
        base[SLOW] = 1000.0
        st = {"mode": "idle", "times": list(base), "hedge_at": 1e9, "only": 100}
        clock = ValueTracker(0)

        # ten trays for the prediction: each slot is dropped with chance 1 in 100
        trng = np.random.default_rng(SEED)
        trays = []
        for _ in range(10):
            m = trng.random(100) < 0.01
            t = list(np.random.default_rng(len(trays) + 20).uniform(5, 15, 100))
            for i in np.flatnonzero(m):
                t[i] = 1000.0
            trays.append((t, bool(m.any())))

        # ---------------- scene 1: the symptom ----------------
        ph = phone()
        cache = {}

        def make_ctr():
            v = clock.get_value()
            v = int(round(v)) if v < 30 else int(round(v / 10.0) * 10)
            s = f"{v:,} ms"
            if s not in cache:
                cache[s] = M(s, 20)
            k = ph[0].width / PH_W
            return cache[s].copy().scale(k).move_to(ph[0].get_center() + k * 0.12 * UP).set_opacity(ph[0].get_stroke_opacity())
        ctr = always_redraw(make_ctr)

        hook = VGroup(ph)
        hook.scale(HOOK).move_to([0, 0.25, 0])
        self.steps("The café owner opens her app's home screen. Some mornings it appears at once. Most mornings, it hangs for a whole second.", [
            (lambda: [FadeIn(ph, shift=0.2 * UP)], 0.8),
            (lambda: [FadeIn(ctr)], 0.3),
            "Some mornings",
            (lambda: [clock.animate(rate_func=linear).set_value(12)], 0.5),
            "Most mornings",
            (lambda: [clock.animate.set_value(0)], 0.2),
            (lambda: [clock.animate(rate_func=linear).set_value(1000)], 2.0),
        ])
        left = VGroup(T("100 small answers", 22), T("each slow", 22, GREY_B), T("1 time in 100", 22, GREY_B)).arrange(DOWN, buff=0.16)
        lbox = RoundedRectangle(corner_radius=0.12, width=left.width + 0.6, height=left.height + 0.5, stroke_color=GREY_B,
                                stroke_width=3).set_fill(fillc(GREY_B), 1)
        lg = VGroup(lbox, left.move_to(lbox)).move_to([-4.4, 0.25, 0])
        right = VGroup(T("the screen", 22), T("slow", 30, RED_M), T("most mornings", 22, RED_M)).arrange(DOWN, buff=0.16).move_to([4.4, 0.25, 0])
        self.steps("Here's the odd part. The screen is built from 100 small answers, and each one is slow only one time in a hundred.", [
            "The screen is built",
            (lambda: [FadeIn(lg, shift=0.2 * RIGHT)], 0.8),
        ])
        qm = T("?", 64, YELLOW_M).move_to([0, 3.1, 0])
        self.steps("So why is the screen slow most of the time?", [
            (lambda: [FadeIn(right, shift=0.2 * LEFT)], 0.8),
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the tray ----------------
        tray = tray_box()
        slots = VGroup(*[slot(i) for i in range(100)])

        def leaf_upd(i):
            def f(m):
                mode, t, tm = st["mode"], clock.get_value(), st["times"][i]
                if i >= st["only"]:
                    m.set_stroke(GREY_D, opacity=0.35).set_fill(BLACK, 1)
                elif mode == "idle":
                    m.set_stroke(GREY_C, opacity=1).set_fill(BLACK, 1)
                elif tm > 15 and t >= st["hedge_at"]:
                    m.set_stroke(TEAL_M, opacity=1).set_fill(TEAL_M, 0.85)        # filled by the second copy
                elif t >= tm:
                    m.set_stroke(GREEN_M, opacity=1).set_fill(GREEN_M, 0.85)
                elif t > 15.2:
                    m.set_stroke(RED_M, opacity=1).set_fill(RED_M, 0.9)
                else:
                    m.set_stroke(YELLOW_M, opacity=1).set_fill(BLACK, 1)
            return f

        def go(times, upto, hedge_at=1e9):
            st.update(mode="run", times=list(times), hedge_at=hedge_at)
            clock.set_value(0)
            return [clock.animate(rate_func=linear).set_value(upto)]

        def reset():
            st.update(mode="idle", hedge_at=1e9)
            return [clock.animate.set_value(0)]

        def show_tray():
            for i, s in enumerate(slots):
                s.add_updater(leaf_upd(i))
            return [Create(tray), LaggedStart(*[FadeIn(s, scale=0.6) for s in slots], lag_ratio=0.008)]

        self.steps("Let's leave the app and go to the café's kitchen. A big order comes in: a tray of 100 sandwiches.", [
            (lambda: [FadeOut(VGroup(lg, right, qm)), hook.animate.scale(1 / HOOK).move_to(PH_C).set_opacity(0.18)], 1.2),
            (lambda: [FadeOut(ctr)], 0.2),
            "a tray of",
            (show_tray, 1.6),
        ])
        self.steps("A hundred cooks make one each, all at once. The tray goes out only when every slot is full.", [
            (lambda: self.set_lab("the tray: 100 slots, 100 cooks"), 0.6),
            "all at once",
            (lambda: go(base, 0.0), 0.3),
            "only when every",
            (lambda: [glow(tray, GREY_B, 1.02)], 0.9),
        ])
        self.steps("Each sandwich is quick. But one time in a hundred, a cook drops it on the floor and starts again.", [
            (lambda: [clock.animate(rate_func=linear).set_value(15.0)], 1.6),
            "drops it",
            (lambda: [clock.animate(rate_func=linear).set_value(15.4)], 0.2),
            (lambda: [Flash(slots[SLOW], color=RED_M, line_length=0.18, flash_radius=0.3)], 0.6),
        ])
        self.steps("Now the whole tray waits for that one cook. Ninety-nine slots are full, and nobody can leave.", [
            "the whole tray",
            (lambda: [glow(tray, YELLOW_M, 1.02)], 0.9),
            "Ninety-nine",
            (lambda: self.cap("99 full, 1 empty: the tray waits"), 0.6),
        ])

        # ---------------- scene 3: predict, then send ten trays ----------------
        self.steps("So each cook is late one time in a hundred. How often is the tray late? Pause and guess.", [
            (lambda: [*reset(), *self.cap("each cook: late 1 time in 100.   the tray?", WHITE)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        icons = VGroup(*[RoundedRectangle(corner_radius=0.06, width=0.42, height=0.42, stroke_color=GREY_C, stroke_width=2.5)
                         .set_fill(BLACK, 1) for _ in range(10)]).arrange(RIGHT, buff=0.2).move_to([GX - 0.9, ICON_Y, 0])
        self.steps("Most people say about one in a hundred, since that's what each cook does. Let's send out ten trays and watch.", [
            (lambda: self.cap("about 1 in 100?", PURPLE_M), 0.5),
            "Let's send",
            (lambda: [*self.uncap(), LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in icons], lag_ratio=0.1)], 0.9),
        ], after=0.2)
        for k, (times, late) in enumerate(trays):
            self.play(*go(times, 16.0), run_time=0.4)
            col = RED_M if late else GREEN_M
            self.play(icons[k].animate.set_stroke(col).set_fill(fillc(col, 0.6), 1), run_time=0.2)
            self.wait(0.05)
        count = T("late: 6 of 10", 24, RED_M)
        count.move_to([icons.get_right()[0] + 0.35 + count.width / 2, ICON_Y, 0])
        self.steps("Six of the ten were late. Well... that's not one in a hundred.", [
            (lambda: [FadeIn(count, shift=0.1 * LEFT)], 0.6),
            "Well",
            (lambda: [LaggedStart(*[Indicate(icons[k], color=RED_M, scale_factor=1.2) for k in range(10) if trays[k][1]], lag_ratio=0.15)], 1.2),
        ], after=0.4)
        self.steps("The tray is on time only if all 100 cooks are. Each one is on time 99 times in 100, so 0.99. "
                   "All 100: 0.99 multiplied by itself 100 times, about 0.37.", [
            (lambda: [FadeOut(icons), FadeOut(count), *reset()], 0.5),
            "Each one is",
            (lambda: self.cap("one cook on time: 0.99", WHITE), 0.5),
            "All 100:",
            (lambda: self.cap("all 100 on time:  0.99 × 0.99 × ... (100 times)  =  0.37", WHITE), 0.5),
        ])
        both = VGroup(T("on time: 37 in 100.", 26, GREEN_M), T("late: 63 in 100.", 26, RED_M)).arrange(RIGHT, buff=0.5)
        self.steps("So the tray is late 63 times in 100. Every extra cook is one more chance to draw the dropped sandwich.", [
            (lambda: self.cap(both), 0.6),
            "Every extra cook",
            (lambda: [LaggedStart(*[Indicate(s, color=YELLOW_M, scale_factor=1.3) for s in slots[::7]], lag_ratio=0.05)], 1.4),
        ])
        self.stamp("after-63")

        # ---------------- scene 4: the app works the same way ----------------
        fans = VGroup(*[Line([PH_C[0] + PH_W / 2 + 0.1, PH_C[1], 0], [TR_X0 - 0.08, lpos(10 * r)[1], 0], stroke_width=1.5, color=GREY_D)
                        for r in range(10)])
        self.steps("The app works the same way, in thousandths of a second, called milliseconds. "
                   "To draw the home screen, the program asks 100 places for a piece each, all at once, and waits for every answer.", [
            (lambda: [*self.uncap(), hook.animate.set_opacity(1)], 0.8),
            (lambda: [FadeIn(ctr)], 0.3),
            "the program asks",
            (lambda: [LaggedStart(*[Create(f) for f in fans], lag_ratio=0.06)], 1.0),
            "all at once",
            (lambda: [*go(base, 0.0), LaggedStart(*[run_on(f, YELLOW_M, 0.6) for f in fans], lag_ratio=0.04)], 1.0),
        ])
        self.steps("Each place, a small program or a piece of a big database, is called a leaf. "
                   "The screen is the tray, and the leaves are the cooks.", [
            "is called a leaf",
            (lambda: self.set_lab("the screen: 100 leaves (the cooks)"), 0.7),
            "The screen is",
            (lambda: [glow(tray, GREY_B, 1.02)], 0.8),
        ])
        self.steps("A leaf answers in 5 to 15 milliseconds. But one time in a hundred, it hits a pause and takes a full second. "
                   "And the screen waits the whole second.", [
            (lambda: [clock.animate(rate_func=linear).set_value(15.0)], 2.4),
            "it hits a pause",
            (lambda: [clock.animate(rate_func=linear).set_value(15.4)], 0.2),
            "And the screen",
            (lambda: [clock.animate(rate_func=linear).set_value(1000)], 2.2),
        ])
        fo = T("fan-out", 24, YELLOW_M).move_to([-3.5, -1.35, 0])
        self.steps("When one request sets off many requests behind it, that's called fan-out.", [
            (lambda: [LaggedStart(*[run_on(f, YELLOW_M, 0.5) for f in fans], lag_ratio=0.04)], 1.0),
            "called fan-out",
            (lambda: [FadeIn(fo, shift=0.1 * UP)], 0.6),
        ])
        self.steps("The rare slow answers are called the tail, because they sit at the slow end when you sort the times.", [
            "are called the tail",
            (lambda: [*self.cap("the tail: the rare slow end of the answer times"), Indicate(slots[SLOW], color=RED_M, scale_factor=1.6)], 0.9),
        ])
        self.steps("Fan-out turns the tail into the normal case: 63 screens in 100 take a second. "
                   "That's called tail latency amplification, where latency is the time you wait.", [
            "63 screens",
            (lambda: self.cap("fan-out turns the tail into the normal case: 63 screens in 100 take a second", WHITE), 0.6),
            "That's called",
            (lambda: self.cap("tail latency amplification   (latency: the time you wait)", YELLOW_M), 0.6),
        ])

        # ---------------- scene 5: fix the leaves? ----------------
        self.steps("So, fix the leaves? To keep only 1 screen in 100 slow, each leaf could be slow only once in 10,000 answers. "
                   "And some pauses can't be removed at all.", [
            "To keep only",
            (lambda: self.cap("1 slow screen in 100 needs each leaf slow only 1 time in 10,000", WHITE), 0.6),
            "And some pauses",
            (lambda: self.cap("a hundred times stricter, and some pauses can't be removed"), 0.6),
        ])
        self.steps("Wouldn't it be nice to stop waiting for the unlucky one?", [
            (lambda: [*self.cap("stop waiting for the unlucky one?", YELLOW_M), *go(base, 15.4)], 1.0),
        ], after=0.5)

        # ---------------- scene 6: a second cook ----------------
        rp_r, rp_t = side_box("second cook", TEAL_M, RP, RP_W, RP_H, 22)
        same = DashedLine([TR_X1 + 0.08, RP[1], 0], [RP[0] - RP_W / 2 - 0.08, RP[1], 0], dash_length=0.08, stroke_width=2.5, color=TEAL_M)
        same_t = T("same sandwich", 18, TEAL_M).move_to(same.get_center() + 0.26 * UP)

        def copy_lands():
            st["hedge_at"] = clock.get_value()
            return [Flash(slots[SLOW], color=TEAL_M, line_length=0.18, flash_radius=0.3)]

        self.steps("Back in the kitchen, the answer is plain. If a slot is still empty after longer than a sandwich usually takes, "
                   "ask a second cook to make the same one, and use whichever is ready first.", [
            (lambda: [*self.uncap(), Indicate(slots[SLOW], color=RED_M, scale_factor=1.6)], 0.9),
            "ask a second cook",
            (lambda: [FadeIn(VGroup(rp_r, rp_t), shift=0.2 * LEFT)], 0.7),
            (lambda: [Create(same), FadeIn(same_t)], 0.6),
            "and use whichever",
            (lambda: [run_on(Line(same.get_end(), same.get_start()), TEAL_M, 0.8)], 1.0),
            (copy_lands, 0.5),
        ])
        self.steps("And the spare sandwich? The staff eat it. So the cost is a little extra work, only for the late ones.", [
            (lambda: self.cap("the spare sandwich: the staff eat it"), 0.5),
            "So the cost",
            (lambda: self.cap("the cost: a little extra work, only for the late ones", WHITE), 0.6),
        ])
        rep_t = T("replica", 24).move_to(RP)
        data_t = T("same data", 18, TEAL_M).move_to(same_t)
        self.steps("In the app, the second cook is a replica: another computer that holds a copy of the same data.", [
            "is a replica",
            (lambda: [swap(rp_t, rep_t), swap(same_t, data_t), *self.cap("replica: another computer with a copy of the same data")], 0.8),
        ])
        p0, p1 = PH_C + [0, PH_H / 2 + 0.12, 0], RP + [0, RP_H / 2 + 0.12, 0]
        hedge = CurvedArrow(p0, p1, angle=-0.36 * PI, color=TEAL_M, stroke_width=3, tip_length=0.2)
        out_arc, back_arc = ArcBetweenPoints(p0, p1, angle=-0.36 * PI), ArcBetweenPoints(p1, p0, angle=0.36 * PI)
        self.steps("The program waits 15 milliseconds, longer than any quick leaf takes. Then it sends the same request to the replica, "
                   "and keeps the first answer back. How long does the screen take now? Pause and guess.", [
            (lambda: [*self.uncap(), *reset()], 0.5),
            (lambda: [*go(base, 0.0), LaggedStart(*[run_on(f, YELLOW_M, 0.5) for f in fans], lag_ratio=0.04)], 0.9),
            (lambda: [clock.animate(rate_func=linear).set_value(15.4)], 1.4),
            "Then it sends",
            (lambda: [Create(hedge)], 0.8),
            (lambda: [run_on(out_arc, TEAL_M, 1.0)], 1.2),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        def answer():
            st["hedge_at"] = 23
            return [clock.animate(rate_func=linear).set_value(23), run_on(back_arc, GREEN_M, 1.3)]

        self.steps("23 milliseconds. The replica answered while the first leaf was still stuck.", [
            (lambda: [*self.uncap(), *answer()], 1.5),
            (lambda: [Circumscribe(ctr, color=GREEN_M, buff=0.15)], 0.9),
        ])
        self.stamp("hedged")
        hchip = chip("hedged request", TEAL_M, 22).move_to(RP + [0, -0.85, 0])
        self.steps("That second copy is called a hedged request. Over many screens, 99 in 100 now finish within 30 milliseconds, "
                   "and only 1 request in 100 needed a copy.", [
            "called a hedged",
            (lambda: [FadeIn(hchip, shift=0.1 * UP), glow(hedge, TEAL_M, 1.0)], 0.8),
            "Over many",
            (lambda: self.cap("hedge after 15 ms:  99 screens in 100 done within 30 ms,  1 request in 100 copied", WHITE), 0.6),
        ])
        self.steps("A common rule is to wait as long as 95 answers in 100 take, so at most about 5 in 100 get a copy.", [
            (lambda: self.cap("a common rule: wait as long as 95 answers in 100 take, so about 5 in 100 get a copy"), 0.6),
        ])

        # ---------------- scene 7: when a hedge can't help ----------------
        ts_r, ts_t = side_box("one toaster", GREY_B, TS, TS_W, TS_H, 22)
        to_rep = Line([TS[0], TS[1] + TS_H / 2 + 0.08, 0], [RP[0], RP[1] - RP_H / 2 - 0.08, 0], stroke_width=2, color=GREY_B)
        to_leaf = Line([TS[0] - TS_W / 2 - 0.08, TS[1] + 0.1, 0], [TR_X1 + 0.08, RP[1] - 0.25, 0], stroke_width=2, color=GREY_B)
        bad_fill = fillc(RED_M, 0.3)
        self.steps("A hedge needs two things. First, each copy must be slow for its own reasons. "
                   "If both cooks share one toaster and it jams, the second cook is stuck too.", [
            (lambda: [*self.cap("1. each copy slow for its own reasons", WHITE), FadeOut(hchip)], 0.6),
            "If both cooks",
            (lambda: [FadeIn(VGroup(ts_r, ts_t), shift=0.1 * UP), Create(to_rep), Create(to_leaf)], 0.8),
            "and it jams",
            (lambda: [ts_r.animate.set_stroke(RED_M).set_fill(bad_fill, 1), to_rep.animate.set_color(RED_M), to_leaf.animate.set_color(RED_M)], 0.6),
            "stuck too",
            (lambda: [rp_r.animate.set_stroke(RED_M).set_fill(bad_fill, 1), hedge.animate.set_color(RED_M)], 0.6),
        ])
        ts_t2 = T("one faulty version", 22).move_to(TS)
        self.steps("In a program, that's one faulty new version on every replica, or one overloaded disk under both. "
                   "Then the extra request buys nothing.", [
            (lambda: [swap(ts_t, ts_t2), *self.cap("one faulty new version on every replica, or one overloaded disk under both")], 0.7),
            "Then the extra",
            (lambda: self.cap("the hedge is slow too: the extra request buys nothing", RED_M), 0.6),
        ])
        teal_fill = fillc(TEAL_M)
        self.steps("Second, the request must be safe to run twice. A spare sandwich is fine. A second charge on someone's card is not.", [
            (lambda: [FadeOut(VGroup(ts_r, ts_t2, to_rep, to_leaf)), rp_r.animate.set_stroke(TEAL_M).set_fill(teal_fill, 1),
                      hedge.animate.set_color(TEAL_M), *self.cap("2. safe to run twice", WHITE)], 0.8),
            "A spare sandwich",
            (lambda: self.cap(VGroup(T("a spare sandwich: fine.", 24, GREEN_M), T("a second charge on a card: not fine.", 24, RED_M))
                              .arrange(RIGHT, buff=0.5)), 0.6),
        ])
        self.steps("Reading a balance twice is harmless. A card payment is safe only with an idempotency key, a unique label the bank checks "
                   "so it charges once. Safe to run twice is called idempotent.", [
            (lambda: self.cap("reading a balance twice: harmless"), 0.5),
            "A card payment",
            (lambda: self.cap("a card payment: safe only with an idempotency key, a unique label the bank checks", WHITE), 0.6),
            "Safe to run twice",
            (lambda: self.cap("safe to run twice: idempotent", YELLOW_M), 0.6),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So why was the screen slow most of the time? It waits for the slowest of 100 answers, "
                   "and with 100 tries, the rare slow one turns up most of the time.", [
            (lambda: [*self.cap("why was the screen slow most of the time?", WHITE), *reset()], 0.6),
            "It waits",
            (lambda: [*go(base, 15.4), LaggedStart(*[run_on(f, YELLOW_M, 0.5) for f in fans], lag_ratio=0.04)], 1.2),
            (lambda: [glow(tray, YELLOW_M, 1.02), *self.cap("the slowest of 100 answers sets the time", WHITE)], 0.9),
        ])
        self.steps("You can't make every leaf perfect. So stop waiting for the unlucky one: ask a second copy, and keep the first answer.", [
            "So stop waiting",
            (lambda: [run_on(out_arc, TEAL_M, 0.9)], 1.0),
            (lambda: [run_on(back_arc, GREEN_M, 0.9), *self.cap("ask a second copy, and keep the first answer", TEAL_M)], 1.0),
            (copy_lands, 0.4),
        ], after=0.6)

        def ten_only():
            st["only"] = 10
            return [FadeOut(fo, run_time=0.3), *[f.animate.set_stroke(opacity=0.15) for f in fans[1:]], *self.cap("10 leaves instead of 100: slow more often, or less?", WHITE)]

        self.steps("One quick check. Say the screen asked only 10 leaves. Slow more often, or less, and roughly how often? Pause and think.", [
            (lambda: [*self.uncap(), *reset()], 0.5),
            "only 10 leaves",
            (ten_only, 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Less often: about 1 screen in 10. Fewer leaves, fewer chances to draw the slow one.", [
            (lambda: self.cap("less often: about 1 screen in 10", GREEN_M, 28), 0.6),
            "Fewer leaves",
            (lambda: [*go(base, 15.4)], 0.9),
        ], after=0.3)
        self.play(*self.cap("fewer leaves, fewer chances to draw the slow one", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
