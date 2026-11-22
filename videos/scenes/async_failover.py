from sfz import *

SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bMySQL\b", "my S Q L"))
SAY.insert(0, (r"\bf1\b", "F one"))
SAY.insert(0, (r"\bf2\b", "F two"))
SAY.insert(0, (r"\b1,001\b", "one thousand and one"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ROW_Y = {"L": 1.75, "f1": 0.4, "f2": -0.95}
BOX_X, BOX_W, BOX_H = -4.9, 2.4, 0.95
POS = list(range(243, 251))
CELL_X0, CELL_W, CELL_GAP = -3.3, 0.72, 0.06
SC_X, SC_W = 4.9, 3.2                      # score panel
SC_Y = {"wait": 1.75, "ok": 0.4, "lost": -0.95}
CR_Y = 3.1                                 # card reader / rule line
CAP_Y, BAR_Y = -3.25, -2.85
COLOR = {"L": BLUE_M, "f1": TEAL_M, "f2": TEAL_M}


def cx(i):
    return CELL_X0 + CELL_W / 2 + i * (CELL_W + CELL_GAP)


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def mbox_(k, color):
    return RoundedRectangle(corner_radius=0.12, width=BOX_W, height=BOX_H, stroke_color=color, stroke_width=3).set_fill(
        fillc(color), 1).move_to([BOX_X, ROW_Y[k], 0])


def cell(k, i, state):
    """state: 'has', 'empty', 'lost'."""
    y = ROW_Y[k]
    col = {"has": COLOR[k], "empty": GREY_D, "lost": RED_M}[state]
    r = Rectangle(width=CELL_W, height=0.62, stroke_color=col, stroke_width=2)
    r.set_fill(col if state != "empty" else BLACK, 0.45 if state != "empty" else 1).move_to([cx(i), y, 0])
    lab = M(str(POS[i]), 17, WHITE if state != "empty" else GREY_C).move_to(r)
    return VGroup(r, lab)


def score_panel():
    r = RoundedRectangle(corner_radius=0.14, width=SC_W, height=4.1, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1)
    r.move_to([SC_X, 0.4, 0])
    labs = VGroup(*[T(s, 18, GREY_B).move_to([SC_X, SC_Y[k] + 0.32, 0]) for k, s in
                    [("wait", "each payment waits"), ("ok", "said OK in the first second"), ("lost", "lost when the leader dies")]])
    return VGroup(r, labs)


def sc_val(k, s, color=WHITE):
    return fit(M(s, 30, color), SC_W - 0.4).move_to([SC_X, SC_Y[k] - 0.18, 0])


def dot_down(i, frm, to, color=YELLOW_M, rt=0.6, frac=1.0, keep=False):
    a = np.array([cx(i), ROW_Y[frm] - 0.33, 0])
    b = np.array([cx(i), ROW_Y[to] + 0.33, 0])
    b = a + frac * (b - a)
    d = Dot(radius=0.07, color=color).move_to(a)
    seq = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt)]
    if not keep:
        seq.append(FadeOut(d, run_time=0.12))
    return d, Succession(*seq)


class AsyncFailover(Base):
    """repl-01, section 1. A leader and followers f1 (20 ms) and f2 (50 ms); a payment every 4 ms; the leader dies at
    1,001 ms. The clerk who says "noted" before or after a town has the line. OK at once: 250 OKs, 4 lost (f1 at 246).
    OK after both: 100 ms each, and a frozen follower stops everything. OK after one: 40 ms, 0 lost (semi-sync).
    On a bad day semi-sync switches itself off (500 ms, then 149 lost). Moral, and the 2 ms / 70 ms check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def rule(self, s, color=WHITE):
        new = fit(T(s, 24, color), 7.2)
        left_at(new, -0.9, CR_Y)
        old, self.rulem = self.rulem, new
        return [swap(old, new)]

    def stat(self, k, s, color=GREY_B):
        new = T(s, 17, color).move_to([BOX_X, ROW_Y[k] - 0.22, 0])
        old, self.st[k] = self.st.get(k), new
        return [swap(old, new)]

    def unstat(self, k):
        old, self.st[k] = self.st.get(k), None
        return [FadeOut(old)] if old is not None else []

    def score(self, k, s, color=WHITE):
        new = sc_val(k, s, color)
        old, self.sc[k] = self.sc.get(k), new
        return [swap(old, new)]

    def set_cells(self, k, states):
        anims = []
        for i, s in enumerate(states):
            new = cell(k, i, s)
            old = self.cells[k][i]
            self.cells[k][i] = new
            anims.append(FadeOut(old) if old is not None else Wait(0))
            anims.append(FadeIn(new))
        return anims

    def construct(self):
        self.capm = self.rulem = None
        self.st, self.sc = {}, {}
        self.cells = {k: [None] * 8 for k in ROW_Y}
        self.title_card("Saved. On how many machines?", "when the leader says OK, and what a crash takes with it")

        # ---------------- scene 1: saved where? ----------------
        reader = chip("card reader", GREY_B, 22).move_to([BOX_X, CR_Y, 0])
        ok = chip("OK", GREEN_M, 22).next_to(reader, RIGHT, buff=0.3)
        self.steps("You tap your card, and the reader beeps: OK. Your payment is saved. Saved where, exactly? On how many machines?", [
            (lambda: [FadeIn(reader, shift=0.1 * DOWN)], 0.6),
            "beeps",
            (lambda: [FadeIn(ok, scale=0.7)], 0.4),
            "Saved where",
            (lambda: self.cap("saved where? on how many machines?", YELLOW_M), 0.6),
        ])
        boxes = {k: mbox_(k, COLOR[k]) for k in ROW_Y}
        names = {k: T(n, 24).move_to([BOX_X, ROW_Y[k] + 0.18, 0]) for k, n in [("L", "leader"), ("f1", "f1"), ("f2", "f2")]}
        self.steps("Here's the setup from the start of this lesson. The payments live in a database, a program that stores records. "
                   "One machine, the leader, takes every new payment, and writes it at the next numbered position in its log.", [
            (lambda: [*self.uncap(), FadeOut(ok)], 0.4),
            "One machine",
            (lambda: [FadeIn(boxes["L"]), FadeIn(names["L"])], 0.6),
            "at the next numbered",
            (lambda: self.set_cells("L", ["empty"] * 8), 0.6),
            (lambda: self.set_cells("L", ["has"] * 4 + ["empty"] * 4), 0.8),
        ])
        self.steps("Two followers, f1 and f2, copy that log in order. f1 is 20 milliseconds away, and f2 is 50.", [
            (lambda: [*[FadeIn(boxes[k]) for k in ("f1", "f2")], *[FadeIn(names[k]) for k in ("f1", "f2")],
                      *self.set_cells("f1", ["empty"] * 8), *self.set_cells("f2", ["empty"] * 8)], 0.8),
            (lambda: [dot_down(i, "L", "f1")[1] for i in range(4)], 0.6),
            (lambda: self.set_cells("f1", ["has"] * 4 + ["empty"] * 4), 0.4),
            "f1 is 20",
            (lambda: self.stat("f1", "20 ms away"), 0.5),
            "and f2 is",
            (lambda: self.stat("f2", "50 ms away"), 0.5),
        ])
        sp = score_panel()
        q = T("?", 34, YELLOW_M).next_to(reader, RIGHT, buff=0.35)
        self.steps("A card reader sends a payment. The leader writes it, and sends it on. At some moment, it tells the card reader OK. "
                   "Which moment? That choice decides what a dying leader can take with it.", [
            (lambda: [Indicate(reader, color=WHITE, scale_factor=1.08)], 0.6),
            "The leader writes",
            (lambda: self.set_cells("L", ["has"] * 5 + ["empty"] * 3), 0.4),
            "sends it on",
            (lambda: [dot_down(4, "L", "f1")[1]], 0.6),
            (lambda: self.set_cells("f1", ["has"] * 5 + ["empty"] * 3), 0.3),
            "At some moment",
            (lambda: [FadeIn(q, scale=0.6)], 0.5),
            "That choice",
            (lambda: [FadeIn(sp)], 0.8),
        ])

        # ---------------- scene 2: the clerk says "noted" ----------------
        roles = {k: T(s, 18, GREY_B).move_to([BOX_X, ROW_Y[k] - 0.66, 0]) for k, s in
                 [("L", "the clerk"), ("f1", "town 1"), ("f2", "town 2")]}
        noted = chip("noted", YELLOW_M, 22).next_to(reader, RIGHT, buff=0.3)
        self.okchip = chip("OK", GREEN_M, 22).next_to(reader, RIGHT, buff=0.3)
        self.steps("Think back to the lesson's club notebook. One clerk writes each payment on the next numbered line, "
                   "and posts photocopies to two other towns. A member hands over money, and waits for the clerk to say: noted.", [
            "One clerk",
            (lambda: [FadeIn(roles["L"])], 0.5),
            "two other towns",
            (lambda: [FadeIn(roles["f1"]), FadeIn(roles["f2"])], 0.5),
            "waits for the clerk",
            (lambda: [swap(q, noted)], 0.6),
        ])
        self.steps("She can say it the moment the ink is dry. Or she can wait until a town phones back: we have your line.", [
            (lambda: self.cap("noted: when the ink is dry?", WHITE), 0.5),
            (lambda: [glow(boxes["L"], BLUE_M)], 0.7),
            "Or she can wait",
            (lambda: self.cap("...or when a town phones back?", WHITE), 0.5),
            (lambda: [dot_down(4, "L", "f1")[1]], 0.6),
            (lambda: [glow(boxes["f1"], TEAL_M)], 0.6),
        ])
        self.steps("Say it early, and the member leaves sooner. But if the office burns down that night, "
                   "a line she said \"noted\" for may exist nowhere else.", [
            "if the office",
            (lambda: [boxes["L"].animate.set_stroke(RED_M), self.cells["L"][4].animate.set_opacity(0.2)], 0.7),
            "exist nowhere",
            (lambda: [*self.cap("a line said \"noted\" for, on no other machine", RED_M)], 0.6),
            (lambda: [boxes["L"].animate.set_stroke(BLUE_M), self.cells["L"][4].animate.set_opacity(1)], 0.6),
        ])
        self.steps("Map it. The clerk is the leader, the notebook is the log, and the towns are followers. "
                   "Saying \"noted\" is called acknowledging the write. And the moment a change becomes final is its commit.", [
            (lambda: self.uncap(), 0.3),
            "The clerk is",
            (lambda: [glow(boxes["L"], BLUE_M)], 0.5),
            "the notebook is",
            (lambda: [LaggedStart(*[Indicate(c, color=BLUE_M, scale_factor=1.08) for c in self.cells["L"][:5]], lag_ratio=0.15)], 0.8),
            "the towns are",
            (lambda: [glow(boxes["f1"], TEAL_M), glow(boxes["f2"], TEAL_M)], 0.6),
            "acknowledging",
            (lambda: [swap(noted, self.okchip),
                      *self.cap("acknowledge: tell the client OK", WHITE)], 0.6),
            "its commit",
            (lambda: self.cap("commit: the moment a change becomes final", WHITE), 0.6),
        ])

        # ---------------- scene 3: OK at once ----------------
        self.steps("Now the lesson's simulator, with exact numbers. A payment arrives every 4 milliseconds. "
                   "First rule: the leader says OK as soon as the payment is on its own disk.", [
            (lambda: [*self.uncap(), *[FadeOut(r) for r in roles.values()]], 0.5),
            "every 4",
            (lambda: self.cap("a payment every 4 ms; the simulator's numbers", GREY_B), 0.5),
            "First rule",
            (lambda: self.rule("OK when: the leader's own disk has it", WHITE), 0.6),
        ])
        self.steps("Nobody waits at all. In the first second, 250 card readers hear OK.", [
            (lambda: [*self.set_cells("L", ["has"] * 8), *self.score("wait", "0 ms", GREEN_M)], 0.8),
            "In the first second",
            (lambda: self.score("ok", "250"), 0.5),
        ])
        dl = T("1,001 ms", 20, RED_M).next_to(boxes["L"], LEFT, buff=0.12)
        flying = [dot_down(i, "L", "f1", frac=0.5, keep=True) for i in range(4, 8)]
        self.steps("At 1,001 milliseconds, the leader dies. How many payments that already heard OK are now gone? Pause and guess.", [
            (lambda: [*self.uncap(), *self.set_cells("f1", ["has"] * 4 + ["empty"] * 4)], 0.4),
            (lambda: [f[1] for f in flying], 0.6),
            "the leader dies",
            (lambda: [boxes["L"].animate.set_stroke(RED_M), *self.stat("L", "dead", RED_M)], 0.5),
            "Pause and guess",
            (lambda: [*self.score("lost", "?", YELLOW_M), *self.cap("pause and guess", YELLOW_M)], 0.4),
        ], after=0)
        self.countdown(3.0)
        crosses = VGroup(*[tick(False, 0.11).move_to(f[0]) for f in flying])
        self.steps("Four. f1 had everything up to 246. Entries 247 to 250 were still on the wire, and they died with the leader.", [
            (lambda: [*self.uncap(), *self.score("lost", "4", RED_M)], 0.5),
            "f1 had",
            (lambda: [LaggedStart(*[Indicate(c, color=TEAL_M, scale_factor=1.1) for c in self.cells["f1"][:4]], lag_ratio=0.15)], 0.8),
            "Entries 247",
            (lambda: [*[FadeOut(f[0]) for f in flying], Create(crosses),
                      *[c[0].animate.set_fill(RED_M, 0.45).set_stroke(RED_M) for c in self.cells["L"][4:]]], 0.7),
            "died with",
            (lambda: [*[c.animate.set_opacity(0.25) for c in self.cells["L"]], boxes["L"].animate.set_opacity(0.4)], 0.6),
        ])
        self.steps("f1 takes over as the new leader. Four card readers heard OK for payments that exist on no running machine.", [
            (lambda: [*self.stat("f1", "new leader, at 246", GREEN_M)], 0.6),
            "Four card readers",
            (lambda: [Indicate(self.sc["lost"], color=RED_M, scale_factor=1.2),
                      *self.cap("4 payments heard OK, and exist on no running machine", RED_M)], 0.8),
        ])
        self.steps("This is asynchronous replication: the copies happen in the background. And four is a good day.", [
            (lambda: self.cap("asynchronous replication: copies in the background", YELLOW_M), 0.6),
        ])
        self.steps("A follower is usually a few milliseconds behind, but nothing limits it. Stuck behind a slow link, it can be minutes behind, "
                   "and a crash then takes minutes of payments.", [
            "nothing limits it",
            (lambda: self.cap("usually milliseconds behind; nothing stops it falling minutes behind", WHITE), 0.6),
            "minutes behind",
            (lambda: self.set_cells("f1", ["empty"] * 8), 0.7),
        ])

        # ---------------- scene 4: wait for everyone ----------------
        def reset(f2_ok=True):
            anims = [FadeOut(crosses), boxes["L"].animate.set_stroke(BLUE_M).set_opacity(1), *self.unstat("L"),
                     *self.stat("f1", "20 ms away"), *self.stat("f2", "50 ms away")]
            anims += self.set_cells("L", ["has"] * 8) + self.set_cells("f1", ["has"] * 8) + self.set_cells("f2", ["has"] * 8)
            return anims

        self.steps("So the obvious fix: say OK only when every follower has the payment. Run it again. Nothing is lost.", [
            (lambda: [*self.uncap(), *reset()], 0.8),
            (lambda: self.rule("OK when: both followers have it", WHITE), 0.6),
            "Nothing is lost",
            (lambda: [*self.score("lost", "0", GREEN_M), *self.score("ok", "226")], 0.6),
        ])
        self.steps("But each payment now waits 100 milliseconds, the round trip to f2, the farthest.", [
            (lambda: [dot_down(7, "L", "f1")[1], dot_down(7, "L", "f2", rt=1.2)[1]], 1.2),
            (lambda: [dot_down(7, "L", "f2", GREEN_M, rt=0.01)[1]], 0.1),
            "100",
            (lambda: [*self.score("wait", "100 ms", RED_M), *self.cap("each payment waits for the round trip to f2: 2 x 50 ms", WHITE)], 0.6),
        ])
        queue = VGroup(*[RoundedRectangle(corner_radius=0.05, width=0.32, height=0.32, stroke_color=GREY_B, stroke_width=2).set_fill(GOLD_M, 0.4)
                         for _ in range(6)]).arrange(RIGHT, buff=0.1).next_to(reader, RIGHT, buff=0.3)
        self.steps("And it gets worse. Say f2 freezes for 40 seconds while its machine is moved. Every payment waits for it. "
                   "Card payments stop, everywhere, for 40 seconds.", [
            (lambda: [*self.uncap(), FadeOut(self.okchip)], 0.3),
            "Say f2 freezes",
            (lambda: [boxes["f2"].animate.set_stroke(GREY_C).set_fill(BLACK), *self.stat("f2", "frozen: 40 s", GREY_B)], 0.6),
            "Every payment waits",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * LEFT) for b in queue], lag_ratio=0.3)], 1.5),
            "Card payments stop",
            (lambda: [*self.score("wait", "40 s", RED_M), *self.cap("one frozen follower: every payment waits", RED_M)], 0.6),
        ])
        self.steps("The whole system now moves at the speed of its sleepiest machine. That's fully synchronous replication.", [
            (lambda: [glow(boxes["f2"], GREY_B), Indicate(self.st["f2"], color=GREY_B)], 0.9),
            "fully synchronous",
            (lambda: self.cap("fully synchronous replication: wait for every follower", YELLOW_M), 0.6),
        ])

        # ---------------- scene 5: the middle ----------------
        self.steps("Most systems choose the middle: wait for any one follower. Each payment waits 40 milliseconds, the round trip to f1.", [
            (lambda: [*self.uncap(), FadeOut(queue), boxes["f2"].animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M), 1),
                      *self.stat("f2", "50 ms away")], 0.6),
            "wait for any one",
            (lambda: self.rule("OK when: one follower has it", WHITE), 0.6),
            "Each payment",
            (lambda: [dot_down(7, "L", "f1")[1]], 0.7),
            "40",
            (lambda: [*self.score("wait", "40 ms", YELLOW_M), *self.score("ok", "241")], 0.6),
        ])
        self.steps("And the crash loses nothing, because every acknowledged payment is on at least two machines. "
                   "That's usually called semi-synchronous replication.", [
            (lambda: self.score("lost", "0", GREEN_M), 0.5),
            "on at least two",
            (lambda: [glow(boxes["L"], GREEN_M), glow(boxes["f1"], GREEN_M)], 0.8),
            "semi-synchronous",
            (lambda: self.cap("semi-synchronous replication: wait for one follower", YELLOW_M), 0.6),
        ])
        hdr = ["OK when", "waits", "said OK", "lost"]
        rows = [["own disk", "0 ms", "250", "4"], ["one follower", "40 ms", "241", "0"], ["both followers", "100 ms", "226", "0"]]
        colx = [-5.2, -1.6, 0.4, 2.3]
        ty = [-1.72, -2.17, -2.57, -2.97]
        table = VGroup(*[left_at(T(h, 19, GREY_B), x, ty[0]) for h, x in zip(hdr, colx)])
        trows = []
        for r, row in enumerate(rows):
            g = VGroup()
            for j, (v, x) in enumerate(zip(row, colx)):
                col = WHITE
                if j == 3:
                    col = RED_M if v != "0" else GREEN_M
                g.add(left_at((T if j == 0 else M)(v, 19 if j == 0 else 20, col), x, ty[r + 1]))
            trows.append(g)
        rule_line = Line([-5.3, ty[0] - 0.2, 0], [2.9, ty[0] - 0.2, 0], stroke_width=1.5, color=GREY_D)
        self.steps("Side by side: no waiting, 250 OKs, four lost. Wait for one, 40 milliseconds, 241, none lost. Wait for both, 100, 226, none lost.", [
            (lambda: [*self.uncap(), FadeIn(table), Create(rule_line)], 0.5),
            (lambda: [FadeIn(trows[0], shift=0.1 * UP)], 0.5),
            "Wait for one",
            (lambda: [FadeIn(trows[1], shift=0.1 * UP)], 0.5),
            "Wait for both",
            (lambda: [FadeIn(trows[2], shift=0.1 * UP)], 0.5),
        ])
        self.steps("The waiting rules sent fewer OKs only because their last payments were still waiting when the leader died.", [
            (lambda: [Indicate(trows[1][2], color=YELLOW_M), Indicate(trows[2][2], color=YELLOW_M)], 1.0),
        ], after=0.5)

        # ---------------- scene 6: the bad day ----------------
        tab_all = VGroup(table, rule_line, *trows)
        self.steps("Now the small print. What if no follower answers? MySQL, a popular free database, waits up to 10 seconds by default. "
                   "Then it quietly goes back to asynchronous. No card reader sees an error.", [
            (lambda: [FadeOut(tab_all), *[boxes[k].animate.set_stroke(GREY_C).set_fill(BLACK) for k in ("f1", "f2")],
                      *self.stat("f1", "not answering", GREY_B), *self.stat("f2", "not answering", GREY_B)], 0.7),
            "MySQL",
            (lambda: self.cap("MySQL, a popular free database: waits up to 10 seconds by default", WHITE), 0.6),
            "Then it quietly",
            (lambda: self.cap("...then quietly goes back to asynchronous. No error anywhere.", RED_M), 0.6),
        ])
        self.steps("The lab shows it with a 500 millisecond timeout and both followers stalled. The first payment waits the full 500.", [
            (lambda: [*self.uncap(), *self.rule("OK when: one follower has it (timeout 500 ms)", WHITE),
                      *self.stat("f1", "stalled: 600 ms", GREY_B), *self.stat("f2", "stalled: 700 ms", GREY_B)], 0.7),
            "The first payment",
            (lambda: self.score("wait", "500 ms", RED_M), 0.6),
        ])
        self.steps("Then semi-sync switches itself off, and every later payment gets its OK at once.", [
            "switches itself off",
            (lambda: [*self.rule("OK when: the leader's own disk has it (quietly)", RED_M)], 0.7),
            "every later",
            (lambda: [*self.score("wait", "then 0 ms", RED_M), *self.score("ok", "250")], 0.6),
        ])
        self.steps("When the leader dies, 149 acknowledged payments are lost, under a setting with \"synchronous\" in its name.", [
            (lambda: [boxes["L"].animate.set_stroke(RED_M), *self.stat("L", "dead", RED_M)], 0.5),
            "149",
            (lambda: [*self.score("lost", "149", RED_M), *self.stat("f1", "new leader, at 101", GREEN_M)], 0.6),
            "under a setting",
            (lambda: [Indicate(self.rulem, color=RED_M, scale_factor=1.05)], 0.8),
        ])
        my = VGroup(T("MySQL", 22, WHITE), T("keeps payments flowing,", 19, GREY_B), T("drops its promise", 19, RED_M)).arrange(DOWN, buff=0.12)
        pg = VGroup(T("PostgreSQL", 22, WHITE), T("keeps its promise,", 19, GREY_B), T("stops the payments", 19, RED_M)).arrange(DOWN, buff=0.12)
        my.move_to([-3.0, -2.3, 0])
        pg.move_to([1.6, -2.3, 0])
        self.steps("PostgreSQL, another free database, does the opposite: it keeps payments waiting until a follower is back.", [
            (lambda: [*self.uncap(), FadeIn(my)], 0.5),
            "PostgreSQL",
            (lambda: [FadeIn(pg)], 0.6),
        ])
        self.steps("Neither is wrong. One keeps payments flowing and drops its promise. The other keeps its promise and stops the payments.", [
            "One keeps",
            (lambda: [Indicate(my, color=WHITE, scale_factor=1.05)], 0.8),
            "The other",
            (lambda: [Indicate(pg, color=WHITE, scale_factor=1.05)], 0.8),
        ], after=0.5)

        # ---------------- scene 7: moral and check ----------------
        self.steps("So, saved where? On as many machines as the leader waited for before it said OK.", [
            (lambda: [FadeOut(my), FadeOut(pg), *reset(), *self.rule("OK when: one follower has it", WHITE),
                      *self.score("wait", "40 ms", YELLOW_M), *self.score("ok", "241"), *self.score("lost", "0", GREEN_M)], 0.8),
            "On as many",
            (lambda: [*self.cap("saved on as many machines as the leader waited for", YELLOW_M), glow(boxes["L"], GREEN_M), glow(boxes["f1"], GREEN_M)], 0.8),
        ])
        self.steps("And here's the rule to keep: a setting's name describes a good day. Find out what it does on a bad one.", [
            (lambda: self.cap("a setting's name describes a good day. Find out what it does on a bad one.", YELLOW_M, 26), 0.7),
        ], after=0.8)
        self.steps("One quick check. Move f1 to 2 milliseconds away, and f2 to 70. Waiting for one follower, how long does each payment wait? "
                   "Pause and think.", [
            (lambda: [*self.uncap(), *self.stat("f1", "2 ms away", WHITE)], 0.5),
            "and f2 to 70",
            (lambda: self.stat("f2", "70 ms away", WHITE), 0.5),
            "how long",
            (lambda: [*self.score("wait", "?", YELLOW_M), *self.score("ok", "-"), *self.score("lost", "-")], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("4 milliseconds: the round trip to f1. Waiting for both now costs 140.", [
            (lambda: [*self.uncap(), dot_down(7, "L", "f1", GREEN_M, rt=0.4)[1]], 0.5),
            (lambda: self.score("wait", "4 ms", GREEN_M), 0.5),
            "Waiting for both",
            (lambda: self.cap("one follower: 2 x 2 = 4 ms.   both: 2 x 70 = 140 ms", GREEN_M), 0.6),
        ], after=0.3)
        self.play(*self.cap("a setting's name describes a good day. Find out what it does on a bad one.", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
