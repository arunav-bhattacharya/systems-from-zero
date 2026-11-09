from sfz import *

# three services on three timelines; x is roughly real time
ROW = {"auth": 2.3, "capture": 0.6, "ledger": -1.1}
XL, XR = -5.2, 6.3
COL = {"auth": BLUE_M, "capture": GREEN_M, "ledger": PURPLE_M}
# event: (node, x, where its stamp sits)
EV = {
    "a1": ("auth", -3.9, "up"), "a2": ("auth", -2.0, "up"),
    "c1": ("capture", -4.2, "up"), "c3": ("capture", -0.3, "right"), "c4": ("capture", 2.2, "up"),
    "c5": ("capture", 5.2, "up"),
    "l1": ("ledger", -4.4, "up"), "l2": ("ledger", -3.2, "up"), "l3": ("ledger", -2.0, "up"),
    "l4": ("ledger", -0.9, "up"), "l5": ("ledger", 0.2, "up"), "l6": ("ledger", 3.9, "right"),
}
NOTE_L, NOTE_R, NOTE_Y = -6.5, 0.6, [-2.3, -2.78, -3.26]


def P(e):
    n, x, _ = EV[e]
    return np.array([x, ROW[n], 0])


def stamp(e, s, color=WHITE, size=20):
    m = M(s, size, color)
    p = P(e)
    if EV[e][2] == "up":
        return m.move_to(p + [0, 0.34, 0])
    return m.move_to([p[0] + 0.2 + m.width / 2, p[1] + 0.34, 0])


def dot(e):
    return Dot(P(e), radius=0.09, color=COL[EV[e][0]])


def ring(e, color=GOLD_M):
    return Circle(radius=0.16, stroke_color=color, stroke_width=3.5).move_to(P(e))


def msg(a, b):
    return Arrow(P(a), P(b), buff=0.14, stroke_width=3, color=GOLD_M, max_tip_length_to_length_ratio=0.1)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def note(s, col, k, color=GREY_B, size=20):
    return left_at(T(s, size, color), NOTE_L if col == "L" else NOTE_R, NOTE_Y[k])


def path_of(*es, color=YELLOW_M):
    return VMobject(stroke_color=color, stroke_width=9, stroke_opacity=0.45).set_points_as_corners([P(e) for e in es])


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


class LogicalClocks(Base):
    """dist-06, section 1 (with section 2's hybrid logical clocks): auth authorizes pay-81723 and tells capture,
    which captures 5 ms later; auth's clock is 40 ms fast, so the capture (10:00:00.105) sorts before the
    authorization (10:00:00.140). Lamport counters: auth 1, send 2; capture max(1, 2) + 1 = 3, sends 4; ledger at 5
    receives as 6. (2, auth) and (3, ledger) are concurrent. An HLC keeps (.140, 0), (.140, 1), then capture
    (.140, 2), (.140, 3), and (.141, 0) once its own clock passes .140."""

    def construct(self):
        self.title_card("Logical clocks", "ordering events by cause, without a shared clock")

        names = {n: left_at(T(n, 24), -6.5, y) for n, y in ROW.items()}
        lines = {n: Arrow([XL, y, 0], [XR, y, 0], buff=0, stroke_width=2, color=GREY_C, max_tip_length_to_length_ratio=0.015)
                 for n, y in ROW.items()}
        d = {e: dot(e) for e in EV}
        lab = {}
        m1, m2 = msg("a2", "c3"), msg("c4", "l6")
        w_auth = T("authorize pay-81723", 16, GREY_B).move_to(P("a1") + [0.35, -0.3, 0])
        w_cap = T("capture", 16, GREY_B).move_to(P("c3") + [0, -0.3, 0])

        self.steps("Auth authorizes a payment, then tells capture, which captures it 5 milliseconds later.", [
            (lambda: [*[FadeIn(names[n]) for n in ("auth", "capture")], *[Create(lines[n]) for n in ("auth", "capture")]], 0.9),
            (lambda: [FadeIn(d["a1"], scale=0.5), FadeIn(w_auth)], 0.6),
            "then tells",
            (lambda: [GrowArrow(m1)], 0.6),
            (lambda: [travel(m1, GOLD_M, 0.7)], 0.7),
            (lambda: [FadeIn(d["c3"], scale=0.5), FadeIn(w_cap)], 0.5),
        ])

        fast = left_at(T("clock 40 ms fast", 16, GOLD_M), -6.5, ROW["auth"] - 0.36)
        lab["a1"] = stamp("a1", "10:00:00.140", GOLD_M, 17)
        lab["c3"] = stamp("c3", "10:00:00.105", WHITE, 17)
        srt = VGroup(T("sorted by timestamp:", 20, GREY_B), chip("capture  .105", RED_M, 18),
                     chip("authorize  .140", GREY_B, 18), tick(False, 0.18)).arrange(RIGHT, buff=0.3).move_to([0, -2.6, 0])
        self.steps("Auth's clock runs 40 milliseconds fast. Sorted by timestamp, "
                   "the capture comes before the authorization it depends on.", [
            (lambda: [FadeIn(fast, shift=0.1 * DOWN), FadeIn(lab["a1"], shift=0.1 * UP)], 0.8),
            (lambda: [FadeIn(lab["c3"], shift=0.1 * UP)], 0.6),
            "Sorted by",
            (lambda: [FadeIn(srt[0]), FadeIn(srt[1], shift=0.1 * RIGHT)], 0.7),
            (lambda: [FadeIn(srt[2], shift=0.1 * RIGHT)], 0.5),
            "it depends on",
            (lambda: [Create(srt[3])], 0.5),
        ])

        hp = path_of("a1", "a2", "c3")
        goal = note("goal: a cause gets the smaller stamp", "R", 0, GREEN_M)
        goal0 = T("if one event could have caused another, the cause must get the smaller stamp", 20, GREEN_M).move_to([0, -2.6, 0])
        self.steps("What we need is weaker than real time: if one event could have caused another, "
                   "the cause must get the smaller stamp.", [
            (lambda: [FadeOut(srt)], 0.5),
            "if one event",
            (lambda: [Create(hp)], 1.2),
            "the cause must",
            (lambda: [FadeIn(goal0, shift=0.1 * UP)], 0.7),
        ])

        r1 = note("1. before each event: add 1", "L", 0, WHITE)
        new = {"c1": "1", **{f"l{k}": str(k) for k in range(1, 6)}}
        self.steps("Leslie Lamport's answer is a counter on each node. Before each event, the node adds one.", [
            (lambda: [FadeOut(hp), Transform(goal0, goal), FadeIn(names["ledger"]), Create(lines["ledger"])], 0.9),
            "Before each",
            (lambda: [FadeIn(r1), Transform(lab["a1"], stamp("a1", "1")), FadeOut(lab["c3"]), FadeOut(fast)], 0.7),
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(d[e], scale=0.5), FadeIn(self._lab(lab, e, new[e])))
                                    for e in ("c1", "l1", "l2", "l3", "l4", "l5")], lag_ratio=0.3)], 1.8),
        ])

        r2 = note("2. a message carries the counter", "L", 1, WHITE)
        c2 = chip("carries 2", GOLD_M, 17).move_to([-0.35, 1.62, 0])
        self.steps("A message carries the sender's counter. Auth counts the send as 2, and the message carries 2.", [
            (lambda: [FadeIn(r2)], 0.6),
            "Auth counts",
            (lambda: [FadeIn(d["a2"], scale=0.5), FadeIn(self._lab(lab, "a2", "2"))], 0.6),
            "and the message",
            (lambda: [FadeIn(c2, shift=0.1 * DOWN), travel(m1, GOLD_M, 0.8)], 0.8),
        ])

        r3 = note("3. on receipt: the larger of the two, plus 1", "L", 2, WHITE)
        k1 = note("capture: max(1, 2) + 1 = 3", "R", 1, WHITE)
        k2 = VGroup(T("authorize 1 < capture 3", 20, GREEN_M), tick(True, 0.15)).arrange(RIGHT, buff=0.2)
        left_at(k2, NOTE_R, NOTE_Y[2])
        self.steps("Capture's counter is 1. On receipt it takes the larger of the two, 2, and adds one: 3. "
                   "The capture now sorts after the authorization.", [
            (lambda: [Indicate(lab["c1"], color=GOLD_M)], 0.8),
            "On receipt",
            (lambda: [FadeIn(r3), FadeIn(k1)], 0.8),
            "and adds one",
            (lambda: [FadeIn(self._lab(lab, "c3", "3", GOLD_M), scale=1.4)], 0.6),
            "The capture now",
            (lambda: [FadeIn(k2, shift=0.1 * UP)], 0.7),
        ])

        c4 = chip("carries 4", GOLD_M, 17).move_to([3.95, -0.05, 0])
        k3 = note("ledger: max(5, 4) + 1 = 6", "R", 1, WHITE)
        self.steps("Capture sends to the ledger with 4. The ledger has counted to 5 on its own, so the receive becomes 6.", [
            (lambda: [Transform(lab["c3"], stamp("c3", "3")), FadeOut(k2), FadeIn(d["c4"], scale=0.5),
                      FadeIn(self._lab(lab, "c4", "4"))], 0.6),
            (lambda: [GrowArrow(m2), FadeIn(c4)], 0.6),
            (lambda: [travel(m2, GOLD_M, 0.7)], 0.7),
            "The ledger has",
            (lambda: [Indicate(lab["l5"], color=GOLD_M), Transform(k1, k3)], 0.8),
            "so the receive",
            (lambda: [FadeIn(d["l6"], scale=0.5), FadeIn(self._lab(lab, "l6", "6", GOLD_M), scale=1.4)], 0.6),
        ])

        cp = path_of("a1", "a2", "c3", "c4", "l6")
        self.steps("A counter only grows along a node, and jumps past every message. "
                   "So a cause always gets a smaller number, whatever the clocks say.", [
            (lambda: [Transform(lab["l6"], stamp("l6", "6")), Create(cp)], 1.6),
            "So a cause",
            (lambda: [*[Indicate(lab[e], color=YELLOW_M, scale_factor=1.5) for e in ("a1", "a2", "c3", "c4", "l6")]], 1.2),
            (lambda: [FadeOut(cp)], 0.5),
        ])

        rg = VGroup(ring("a2"), ring("l3"))
        k4 = note("2 < 3, yet neither could affect the other", "R", 1, GOLD_M)
        k5 = note("concurrent: Lamport can't tell", "R", 2, GOLD_M)
        self.steps("But a smaller number doesn't mean a cause. Auth's send has 2 and the ledger's third event 3, "
                   "yet neither could affect the other. Lamport stamps can't spot such concurrent events.", [
            (lambda: [FadeOut(k1)], 0.4),
            "Auth's send",
            (lambda: [Create(rg[0])], 0.6),
            "the ledger's third",
            (lambda: [Create(rg[1])], 0.6),
            "yet neither",
            (lambda: [FadeIn(k4, shift=0.1 * UP)], 0.7),
            "Lamport stamps",
            (lambda: [FadeIn(k5, shift=0.1 * UP)], 0.7),
        ])

        # ---- hybrid logical clocks ------------------------------------------------------------------------------
        ledger_all = VGroup(lines["ledger"], names["ledger"], m2, c4, *[d[e] for e in EV if e[0] == "l"],
                            *[lab[e] for e in lab if e[0] == "l"])
        h0 = note("hybrid logical clock: (wall-clock time, counter)", "L", 0, WHITE)
        h1 = note("times are milliseconds past 10:00:00", "L", 1)
        self.steps("A counter also says nothing about the time of day. "
                   "A hybrid logical clock keeps both: a wall-clock time and a small counter.", [
            (lambda: [FadeOut(rg), FadeOut(k4), FadeOut(k5), FadeOut(goal0), FadeOut(c2)], 0.6),
            "A hybrid",
            (lambda: [FadeOut(VGroup(r1, r2, r3)), ledger_all.animate.set_opacity(0.22)], 0.8),
            (lambda: [FadeIn(h0, shift=0.1 * UP), FadeIn(h1)], 0.7),
        ])

        self.steps("Auth stamps its events with its own clock's time. Two in the same millisecond get counters 0 and 1.", [
            (lambda: [FadeIn(fast), Transform(lab["a1"], stamp("a1", "(.140, 0)", WHITE, 18))], 0.8),
            "Two in the same",
            (lambda: [Transform(lab["a2"], stamp("a2", "(.140, 1)", WHITE, 18)),
                      Transform(lab["c1"], stamp("c1", "(.098, 0)", WHITE, 18))], 0.8),
        ])

        k6 = note("capture's clock: .105; the message: .140", "R", 0)
        k7 = note("keep .140, count on: (.140, 2)", "R", 1, GOLD_M)
        self.steps("Capture's clock is 35 milliseconds behind the message. "
                   "So capture keeps the message's time and counts on, to 2.", [
            (lambda: [travel(m1, GOLD_M, 0.7), FadeIn(k6)], 0.8),
            "So capture keeps",
            (lambda: [FadeIn(k7), Transform(lab["c3"], stamp("c3", "(.140, 2)", GOLD_M, 18))], 0.9),
        ])

        k8 = note("its clock passes .140: counter back to 0", "R", 2, GREEN_M)
        self.steps("Once its own clock passes that time, the counter starts again at zero. "
                   "With clocks a few milliseconds apart, it's almost always zero.", [
            (lambda: [Transform(lab["c3"], stamp("c3", "(.140, 2)", WHITE, 18)),
                      Transform(lab["c4"], stamp("c4", "(.140, 3)", WHITE, 18))], 0.7),
            (lambda: [FadeIn(d["c5"], scale=0.5), FadeIn(self._lab(lab, "c5", "(.141, 0)", GREEN_M, 18)), FadeIn(k8)], 0.8),
            "With clocks",
            (lambda: [*[Indicate(lab[e], color=GREEN_M) for e in ("a1", "c1", "c5")]], 1.0),
        ])

        fp = path_of("a1", "a2", "c3", "c4", "c5", color=GREEN_M)
        self.steps("Count along each node and jump past every message, and a cause always sorts before its effect.", [
            (lambda: [Create(fp)], 1.6),
            "and a cause",
            (lambda: [Indicate(lab["a1"], color=GREEN_M, scale_factor=1.3), Indicate(lab["c3"], color=GREEN_M, scale_factor=1.3)], 1.0),
        ])
        self.wait(0.6)

    def _lab(self, lab, e, s, color=WHITE, size=20):
        lab[e] = stamp(e, s, color, size)
        return lab[e]
