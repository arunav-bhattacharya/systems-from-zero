from sfz import *


# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CD_X0, CD_X1, CD_TOP, CD_BOT = -6.5, -3.0, 2.5, -1.5      # the workflow code: the instruction sheet
CD_CX = (CD_X0 + CD_X1) / 2
CODE = ["charge(...)", "reserve(...)", "sleep(24 h)", "ship(...)", "return SHIPPED"]
CODE_Y = [1.45, 0.85, 0.25, -0.35, -0.95]
HS_X0, HS_X1, HS_TOP, HS_BOT = -2.6, 1.9, 2.5, -2.3       # the event history: the notebook
HS_CX = (HS_X0 + HS_X1) / 2
EV_Y = [1.55 - 0.45 * i for i in range(8)]
RC_X, RC_W = 4.4, 3.4                                     # right column: workers and the bank
W_Y = {"w1": 1.85, "w2": 0.55, "bank": -1.25}
W_H = {"w1": 1.0, "w2": 1.0, "bank": 1.1}
CAP_Y, BAR_Y = -3.25, -2.85


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


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def panel(x0, x1, top, bot, color):
    return RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=3).set_fill(
        fillc(color), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


def code_line(i, color=WHITE):
    return left_at(M(CODE[i], 22, color), CD_X0 + 0.35, CODE_Y[i])


def cursor(i):
    return RoundedRectangle(corner_radius=0.08, width=CD_X1 - CD_X0 - 0.3, height=0.48, stroke_color=YELLOW_M, stroke_width=4).move_to(
        [CD_CX, CODE_Y[i], 0])


def event(i, s, color=WHITE):
    return VGroup(T(str(i + 1), 18, GREY_B).move_to([HS_X0 + 0.32, EV_Y[i], 0]), left_at(M(s, 19, color), HS_X0 + 0.62, EV_Y[i]))


def rbox(k, color):
    return RoundedRectangle(corner_radius=0.12, width=RC_W, height=W_H[k], stroke_color=color, stroke_width=3).set_fill(
        fillc(color), 1).move_to([RC_X, W_Y[k], 0])


def rname(k, s):
    return T(s, 24).move_to([RC_X, W_Y[k] + 0.2, 0])


def rstat(k, s, color=GREY_B):
    return T(s, 18, color).move_to([RC_X, W_Y[k] - 0.22, 0])


def path_dot(pts, color=YELLOW_M, rt=0.7):
    path = VMobject().set_points_as_corners([np.array(p) for p in pts])
    d = Dot(radius=0.08, color=color).move_to(pts[0])
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.15))


def w_to_bank(k="w1", color=YELLOW_M, back=False):
    """A dot from a worker round the right edge to the bank (or back)."""
    x0, xr = RC_X + RC_W / 2, RC_X + RC_W / 2 + 0.25
    pts = [[x0, W_Y[k], 0], [xr, W_Y[k], 0], [xr, W_Y["bank"], 0], [x0, W_Y["bank"], 0]]
    return path_dot(pts[::-1] if back else pts, color)


def w_to_hist(k="w1", color=YELLOW_M, back=False):
    pts = [[RC_X - RC_W / 2 - 0.05, W_Y[k], 0], [HS_X1 + 0.05, W_Y[k], 0]]
    return path_dot(pts[::-1] if back else pts, color, 0.5)


def hist_to_bank(color=YELLOW_M, back=False):
    pts = [[HS_X1 + 0.05, W_Y["bank"], 0], [RC_X - RC_W / 2 - 0.05, W_Y["bank"], 0]]
    return path_dot(pts[::-1] if back else pts, color, 0.5)


def ev_to_code(e, c, color=GREEN_M):
    pts = [[HS_X0 + 0.1, EV_Y[e], 0], [CD_X1 - 0.1, CODE_Y[c], 0]]
    return path_dot(pts, color, 0.55)


class DurableReplay(Base):
    """enc-05, section 2. An order (charge, reserve, sleep 24 h, ship) whose program restarts after the charge. Running
    it again from the top charges twice. The shop's instruction sheet and notebook, handed over at a change of shift.
    Durable execution: workflow, activities, event history (Temporal). Worker-1 writes events 1 to 5 and is killed;
    worker-2 replays: charge and reserve come from the history, the sleep returns, ship runs for real. The demo:
    worker-2 ran charge=0 reserve=0 ship=1, cards charged: 1. Three rules (the notebook breaks at the gap), a check."""

    def cap(self, s, color=GREY_B, size=24, mono=False):
        new = (M if mono else T)(s, size, color).move_to([0, CAP_Y, 0])
        fit(new, 13.0)
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def stat(self, k, s, color=GREY_B):
        new = rstat(k, s, color)
        old, self.st[k] = self.st.get(k), new
        return [swap(old, new)]

    def unstat(self, k):
        old, self.st[k] = self.st.get(k), None
        return [FadeOut(old)] if old is not None else []

    def name(self, k, s):
        new = rname(k, s)
        old, self.nm[k] = self.nm.get(k), new
        return [swap(old, new)]

    def ev(self, i, s, color=WHITE):
        new = event(i, s, color)
        old, self.evs[i] = self.evs[i], new
        return [swap(old, new, RIGHT)]

    def cur(self, i):
        if self.curm is None:
            self.curm = cursor(i)
            return [Create(self.curm)]
        return [self.curm.animate.move_to(cursor(i))]

    def uncur(self):
        old, self.curm = self.curm, None
        return [FadeOut(old)] if old is not None else []

    def charged(self, n, color=WHITE):
        return self.stat("bank", f"cards charged: {n}", color)

    def construct(self):
        self.capm = self.curm = None
        self.st, self.nm = {}, {}
        self.evs = [None] * 8
        self.title_card("Write it down, then replay", "how a program carries on after a crash")

        # ---------------- scene 1: processing, forever ----------------
        page = VGroup(RoundedRectangle(corner_radius=0.12, width=3.4, height=1.3, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1),
                      VGroup(T("your order", 22, GREY_B), T("Processing...", 30)).arrange(DOWN, buff=0.15))
        page[1].move_to(page[0])
        page.move_to([HS_CX, 0.6, 0])
        self.steps("Picture ordering a book online. That evening, your banking app shows the money gone. "
                   "A week later, there's no parcel, and the order page still says: Processing.", [
            "your banking app",
            (lambda: [*self.cap("your bank: the money is gone", WHITE)], 0.6),
            "A week later",
            (lambda: [FadeIn(page, shift=0.1 * UP)], 0.8),
            "still says",
            (lambda: [Indicate(page[1][1], color=WHITE, scale_factor=1.1)], 0.9),
        ])
        code_box = VGroup(panel(CD_X0, CD_X1, CD_TOP, CD_BOT, WHITE), T("the order's code", 22, GREY_B).move_to([CD_CX, CD_TOP - 0.35, 0]))
        lines = [code_line(i) for i in range(5)]
        w1 = rbox("w1", TEAL_M)
        bank = rbox("bank", GOLD_M)
        self.steps("Behind that page, the shop's program had a few jobs. Charge your card. Set a copy of the book aside in the warehouse. "
                   "Wait a day, then book a courier. In code, that's a few lines, run one after another.", [
            (lambda: [*self.uncap(), FadeIn(code_box)], 0.6),
            "Charge your card",
            (lambda: [FadeIn(lines[0], shift=0.1 * RIGHT)], 0.4),
            "Set a copy",
            (lambda: [FadeIn(lines[1], shift=0.1 * RIGHT)], 0.4),
            "Wait a day",
            (lambda: [FadeIn(lines[2], shift=0.1 * RIGHT)], 0.4),
            "book a courier",
            (lambda: [FadeIn(lines[3], shift=0.1 * RIGHT), FadeIn(lines[4], shift=0.1 * RIGHT)], 0.4),
            "In code",
            (lambda: [FadeIn(w1), *self.name("w1", "the shop's program"), *self.stat("w1", "running"),
                      FadeIn(bank), *self.name("bank", "the bank"), *self.charged(0)], 0.7),
        ])
        self.steps("It charged the card. Then its computer restarted for an update.", [
            (lambda: self.cur(0), 0.4),
            (lambda: [w_to_bank()], 0.8),
            (lambda: self.charged(1), 0.4),
            (lambda: self.cur(1), 0.4),
            "restarted",
            (lambda: [w1.animate.set_stroke(RED_M), *self.stat("w1", "restarted", RED_M)], 0.6),
        ])
        self.steps("Everything the program held in memory, including which line it had reached, was gone. "
                   "Nothing will ever come back for the other jobs.", [
            "including which line",
            (lambda: [Indicate(self.curm, color=RED_M), *self.cap("memory wiped: which line it had reached, gone", RED_M)], 0.8),
            (lambda: self.uncur(), 0.6),
            "Nothing will",
            (lambda: [*[l.animate.set_opacity(0.35) for l in lines[1:4]]], 0.8),
        ])
        qm = T("?", 56, YELLOW_M).move_to([HS_CX, -1.0, 0])
        self.steps("So here's the question. After a crash, how does a program carry on from where it stopped?", [
            (lambda: [FadeIn(qm, scale=0.6), *self.cap("after a crash: carry on from where it stopped?", YELLOW_M)], 0.7),
        ])

        # ---------------- scene 2: run it from the top? ----------------
        self.steps("The tempting fix: when the program starts again, run the order from the top. Each step worked the first time, "
                   "so it feels safe. Let's try it. Charge... and the bank charges the card a second time.", [
            (lambda: [FadeOut(qm), FadeOut(page), *[l.animate.set_opacity(1) for l in lines[1:4]],
                      w1.animate.set_stroke(TEAL_M), *self.stat("w1", "started again"), *self.cap("run it again from the top?", PURPLE_M)], 0.7),
            "Let's try it",
            (lambda: self.cur(0), 0.4),
            "the bank charges",
            (lambda: [w_to_bank(color=PURPLE_M)], 0.8),
            (lambda: [*self.charged(2, RED_M), glow(bank, RED_M)], 0.6),
        ])
        self.steps("Two charges, and still no book. That's a bookshop with a very odd business model.", [
            (lambda: self.cap("two charges, and still no book", RED_M), 0.6),
        ], after=0.5)
        self.steps("What we want is the same plain lines of code, and a program that remembers what it already did, even when its memory is wiped.", [
            (lambda: [*self.uncur(), *self.charged(1), *self.stat("w1", "running")], 0.6),
            "the same plain",
            (lambda: [glow(code_box[0], WHITE, 1.02)], 0.8),
            "remembers",
            (lambda: self.cap("same code, and a program that remembers what it already did", YELLOW_M), 0.6),
        ])

        # ---------------- scene 3: the shop's notebook ----------------
        hist = VGroup(panel(HS_X0, HS_X1, HS_TOP, HS_BOT, BLUE_M), T("notebook", 22, BLUE_M).move_to([HS_CX, HS_TOP - 0.35, 0]))
        w2 = rbox("w2", TEAL_M)
        r_sheet = T("instruction sheet", 20, GREY_B).move_to([CD_CX, CD_BOT - 0.33, 0])
        r_book = T("notebook", 20, GREY_B).move_to([HS_CX, HS_BOT - 0.33, 0])
        r_shift = T("workers on shifts", 20, GREY_B).move_to([RC_X, W_Y["w1"] + 0.82, 0])
        hand = [left_at(T("10:02  charged the card: ch_1", 20, BLUE_M, slant=ITALIC), HS_X0 + 0.3, EV_Y[0]),
                left_at(T("set the book aside: res_1", 20, BLUE_M, slant=ITALIC), HS_X0 + 0.3, EV_Y[1])]
        self.steps("Picture a shop with workers on shifts. Each order has an instruction sheet, and a notebook beside it.", [
            (lambda: [*self.uncap(), FadeIn(w2), *self.name("w1", "worker 1"), *self.stat("w1", "on shift"),
                      *self.name("w2", "worker 2"), *self.stat("w2", "next shift"), FadeIn(r_shift)], 0.8),
            "an instruction sheet",
            (lambda: [FadeIn(r_sheet), glow(code_box[0], WHITE, 1.02)], 0.6),
            "a notebook",
            (lambda: [FadeIn(hist), FadeIn(r_book)], 0.7),
        ])
        self.steps("The first worker does a step, then writes it in the notebook: ten oh two, charged the card, here's the receipt. "
                   "Sets the book aside, and writes that down too.", [
            (lambda: self.cur(0), 0.4),
            (lambda: [w_to_bank()], 0.7),
            "writes it in",
            (lambda: [Write(hand[0])], 0.9),
            "Sets the book",
            (lambda: self.cur(1), 0.4),
            "writes that",
            (lambda: [Write(hand[1])], 0.8),
        ])
        ticks = [tick(True, 0.13).move_to([CD_X1 - 0.35, CODE_Y[i], 0]) for i in range(2)]
        self.steps("At the change of shift, the next worker has never seen this order. So they read the sheet from the top, with the notebook open.", [
            (lambda: [*self.uncur(), *self.stat("w1", "gone home"), w1.animate.set_opacity(0.4),
                      *self.stat("w2", "on shift", WHITE)], 0.7),
            "read the sheet",
            (lambda: self.cur(0), 0.5),
            "notebook open",
            (lambda: [glow(hist[0], BLUE_M, 1.02)], 0.8),
        ])
        self.steps("Every step the notebook shows, they skip, and use the result written there. They start work at the first step with no entry.", [
            (lambda: [ev_to_code(0, 0, BLUE_M), Create(ticks[0])], 0.6),
            (lambda: self.cur(1), 0.4),
            (lambda: [ev_to_code(1, 1, BLUE_M), Create(ticks[1])], 0.6),
            "They start work",
            (lambda: self.cur(2), 0.5),
            (lambda: [glow(self.curm, GREEN_M, 1.05), *self.cap("start at the first step with no entry", GREEN_M)], 0.8),
        ])

        # ---------------- scene 4: name the parts ----------------
        h_title = T("event history (server)", 22, BLUE_M).move_to(hist[1])
        c_title = T("workflow code", 22, GREY_B).move_to(code_box[1])
        self.steps("In software, this idea is called durable execution. Durable means it lasts through a crash.", [
            (lambda: [*self.uncap(), *self.uncur(), FadeOut(VGroup(*ticks)), FadeOut(hand[0]), FadeOut(hand[1]),
                      w1.animate.set_opacity(1), w1.animate.set_stroke(TEAL_M), *self.unstat("w1"), *self.unstat("w2")], 0.7),
            "durable execution",
            (lambda: self.cap("durable execution: it lasts through a crash", YELLOW_M), 0.6),
        ])
        acts = [0, 1, 3]
        self.steps("The sheet is your code, called the workflow: the part that decides what happens next. "
                   "The steps that touch the outside world, charge, reserve and ship, are called activities.", [
            "called the workflow",
            (lambda: [swap(code_box[1], c_title), swap(r_sheet, T("the workflow", 20, WHITE).move_to(r_sheet))], 0.7),
            "are called activities",
            (lambda: [*[lines[i].animate.set_color(GOLD_M) for i in acts], *self.cap("activities: the steps that touch the outside world", GOLD_M)], 0.8),
        ])
        r_book2 = T("each line: an event", 20, WHITE).move_to(r_book)
        self.steps("The notebook is the event history, and each line in it is an event. And the workers are your programs.", [
            (lambda: [swap(hist[1], h_title)], 0.6),
            "each line in it",
            (lambda: [swap(r_book, r_book2)], 0.6),
            "the workers are",
            (lambda: [*self.name("w1", "worker-1"), *self.name("w2", "worker-2"),
                      swap(r_shift, T("workers: your programs", 20, GREY_B).move_to(r_shift))], 0.7),
        ])
        self.steps("Temporal is one well-known engine that works this way: a free program that keeps the history of every workflow, "
                   "on a server, in a database of its own.", [
            (lambda: self.cap("Temporal: a free program that keeps the history of every workflow", WHITE), 0.6),
            "on a server",
            (lambda: [glow(hist[0], BLUE_M, 1.02)], 0.8),
        ])

        # ---------------- scene 5: worker-1 writes it down ----------------
        self.steps("Watch worker-1 run the order. At charge, Temporal's library, the part of Temporal inside your program, "
                   "doesn't call the bank itself. It asks the server to schedule the charge. The server writes: Charge scheduled.", [
            (lambda: [*self.uncap(), FadeOut(r_book2), *self.charged(0), *self.stat("w1", "running the order", WHITE)], 0.6),
            "At charge",
            (lambda: self.cur(0), 0.4),
            "doesn't call",
            (lambda: [*self.cap("the library doesn't call the bank itself", WHITE)], 0.5),
            "It asks",
            (lambda: [w_to_hist()], 0.6),
            "Charge scheduled",
            (lambda: self.ev(0, "Charge scheduled"), 0.5),
        ])
        self.steps("The bank charges the card, and the server writes: Charge done, with the receipt.", [
            (lambda: [hist_to_bank()], 0.6),
            (lambda: self.charged(1), 0.4),
            "the server writes",
            (lambda: [hist_to_bank(GREEN_M, back=True)], 0.5),
            (lambda: self.ev(1, "Charge done: ch_1", GREEN_M), 0.5),
        ])
        self.steps("Reserve goes the same way: scheduled, then done. Then the sleep for a day becomes a timer. The server writes: Timer started.", [
            (lambda: [*self.uncap(), *self.cur(1), w_to_hist()], 0.6),
            "scheduled",
            (lambda: self.ev(2, "Reserve scheduled"), 0.4),
            "then done",
            (lambda: self.ev(3, "Reserve done: res_1", GREEN_M), 0.4),
            "Then the sleep",
            (lambda: [*self.cur(2), w_to_hist()], 0.6),
            "Timer started",
            (lambda: self.ev(4, "Timer started: 24 h"), 0.4),
        ])
        self.steps("No thread, no path of work in your program, waits a whole day.", [
            (lambda: [*self.stat("w1", "free for other work"), *self.cap("no thread waits a whole day", WHITE)], 0.6),
        ])
        self.steps("Now we kill worker-1. Everything it held in memory about this order is gone. The history is untouched.", [
            (lambda: [*self.uncap(), w1.animate.set_stroke(RED_M), *self.stat("w1", "killed", RED_M)], 0.6),
            "Everything it held",
            (lambda: [*self.uncur(), w1.animate.set_opacity(0.4)], 0.6),
            "The history",
            (lambda: [glow(hist[0], BLUE_M, 1.02)], 0.8),
        ])

        # ---------------- scene 6: a guess ----------------
        qb = T("?", 40, YELLOW_M).move_to([RC_X + RC_W / 2 - 0.3, W_Y["bank"] + 0.2, 0])
        self.steps("A day later, the timer fires, and the server hands the order to worker-2, which has never seen it. "
                   "So who calls the bank this time? Pause and guess.", [
            (lambda: self.ev(5, "Timer fired"), 0.5),
            "hands the order",
            (lambda: [w_to_hist("w2", back=True), *self.stat("w2", "gets the task", WHITE)], 0.6),
            "who calls the bank",
            (lambda: [FadeIn(qb, scale=0.6)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 7: replay ----------------
        self.steps("Worker-2 runs the code from the first line. Wait, from the top? That's the fix that charged twice. Here's the difference.", [
            (lambda: [*self.uncap(), FadeOut(qb), *self.stat("w2", "replaying", WHITE)], 0.5),
            (lambda: self.cur(0), 0.5),
            "Wait, from the top",
            (lambda: self.cap("from the top? that's the fix that charged twice...", PURPLE_M), 0.6),
        ])
        self.steps("At charge, the library finds Charge done in the history, and hands back the receipt at once. The bank isn't called.", [
            (lambda: [*self.uncap(), Indicate(self.evs[1], color=GREEN_M, scale_factor=1.06)], 0.8),
            "hands back",
            (lambda: [ev_to_code(1, 0)], 0.6),
            "The bank isn't",
            (lambda: [glow(bank, GREEN_M), *self.cap("the bank isn't called", GREEN_M)], 0.8),
        ])
        self.steps("Reserve: its result comes from the history too. And the sleep returns at once, because its timer already fired.", [
            (lambda: [*self.uncap(), *self.cur(1)], 0.4),
            (lambda: [ev_to_code(3, 1)], 0.6),
            "And the sleep",
            (lambda: self.cur(2), 0.4),
            (lambda: [ev_to_code(5, 2)], 0.6),
        ])
        self.steps("Then the code reaches ship. There's no event for it. So this time, the library schedules it for real. Ship done.", [
            (lambda: self.cur(3), 0.4),
            "no event",
            (lambda: [Indicate(VGroup(*[e for e in self.evs if e is not None]), color=BLUE_M, scale_factor=1.0)], 0.6),
            "for real",
            (lambda: [w_to_hist("w2")], 0.5),
            (lambda: self.ev(6, "Ship scheduled"), 0.4),
            "Ship done",
            (lambda: self.ev(7, "Ship done: trk_1", GREEN_M), 0.4),
        ])
        self.steps("The order returns: SHIPPED.", [
            (lambda: [*self.cur(4), lines[4].animate.set_color(GREEN_M)], 0.6),
        ])
        self.steps("The lesson's demo prints the same. Worker-2 ran charge zero times, reserve zero times, ship once. Cards charged: one.", [
            (lambda: [*self.uncur(), *self.cap("worker-2 ran charge=0 reserve=0 ship=1     cards charged: 1", WHITE, 22, mono=True)], 0.7),
            "Cards charged",
            (lambda: [glow(bank, GREEN_M), Indicate(self.st["bank"], color=GREEN_M)], 0.8),
        ])
        self.steps("Running the code again against its history is called replay.", [
            (lambda: [*self.cap("replay: run the code again against its history", YELLOW_M), *self.stat("w2", "done", GREEN_M)], 0.6),
        ])
        self.steps("A colleague who reads the notes before touching anything. Every shop could use one.", [
            (lambda: [glow(w2, TEAL_M)], 0.8),
        ], after=0.5)

        # ---------------- scene 8: three things to keep in mind ----------------
        self.steps("Three things to keep in mind. One: the workflow code never touches the outside world itself. "
                   "It runs again on every replay, so a bank call written straight into it would run again too.", [
            (lambda: self.cap("1. the workflow code never touches the outside world itself", WHITE), 0.6),
            "It runs again",
            (lambda: [glow(code_box[0], WHITE, 1.02)], 0.8),
            "a bank call",
            (lambda: self.cap("it runs again on every replay: only activities call out", WHITE), 0.6),
        ])
        self.steps("Two: a healthy worker rarely replays. It keeps recent orders in memory, and the server sends its next task back to it. "
                   "Replay is for when a worker dies.", [
            (lambda: self.cap("2. a healthy worker rarely replays: replay is for when one dies", WHITE), 0.6),
            "sends its next task",
            (lambda: [w_to_hist("w2", back=True)], 0.6),
        ])
        gap = VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.08, width=HS_X1 - HS_X0 - 0.3, height=0.42, stroke_color=RED_M,
                                                     stroke_width=3), num_dashes=40)).move_to([HS_CX, EV_Y[1], 0])
        self.steps("Three: here's where the notebook breaks. A worker who charged the card, and died before writing it down, leaves no trace. "
                   "So the next one charges again.", [
            (lambda: self.cap("3. where the notebook breaks", RED_M), 0.6),
            "A worker who charged",
            (lambda: [hist_to_bank(), self.evs[1].animate.set_opacity(0.15), Create(gap)], 0.7),
            "leaves no trace",
            (lambda: self.cap("charged, but not written down yet: no trace", RED_M), 0.6),
            "charges again",
            (lambda: [hist_to_bank(RED_M), *self.charged(2, RED_M)], 0.7),
        ])
        self.steps("That's why each step still needs a key, so the bank can spot a repeat.", [
            (lambda: self.cap("so each step still needs a key, and the bank spots the repeat", YELLOW_M), 0.6),
            "spot a repeat",
            (lambda: [*self.charged(1, WHITE), self.evs[1].animate.set_opacity(1), FadeOut(gap)], 0.7),
        ])

        # ---------------- scene 9: moral and check ----------------
        self.steps("So how does a program carry on after a crash? It doesn't remember. It writes every step down outside itself.", [
            (lambda: self.cap("carry on after a crash?", WHITE), 0.5),
            "It doesn't remember",
            (lambda: [glow(w2, GREY_B)], 0.7),
            "It writes every",
            (lambda: [glow(hist[0], BLUE_M, 1.02), *self.cap("write every step down outside the program", BLUE_M)], 0.8),
        ])
        self.steps("Then any worker can replay the code against those notes: finished steps hand back their recorded answers, "
                   "and real work starts at the first step with no entry.", [
            (lambda: self.cap("then replay: finished steps hand back their answers", YELLOW_M), 0.6),
            "finished steps",
            (lambda: [LaggedStart(ev_to_code(1, 0), ev_to_code(3, 1), ev_to_code(5, 2), lag_ratio=0.4)], 1.2),
            "real work starts",
            (lambda: self.cap("real work starts at the first step with no entry", GREEN_M), 0.6),
        ], after=0.5)
        self.steps("One quick check. Suppose worker-1 dies right after Reserve done, before the sleep starts. Worker-2 replays. "
                   "What's the first thing it does for real? Pause and think.", [
            (lambda: [*self.uncap(), *[FadeOut(self.evs[i]) for i in range(4, 8)], lines[4].animate.set_color(WHITE),
                      *self.stat("w2", "replaying", WHITE)], 0.7),
            "right after Reserve done",
            (lambda: [Indicate(self.evs[3], color=GREEN_M, scale_factor=1.06)], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        for i in range(4, 8):
            self.evs[i] = None
        self.countdown(3.0)
        self.steps("It starts the timer. Charge and reserve come from the history, and the sleep is the first step with no entry.", [
            (lambda: [*self.uncap(), *self.cur(0), ev_to_code(1, 0)], 0.6),
            (lambda: [*self.cur(1), ev_to_code(3, 1)], 0.6),
            (lambda: [*self.cur(2), w_to_hist("w2")], 0.6),
            (lambda: self.ev(4, "Timer started: 24 h", GREEN_M), 0.5),
            "Charge and reserve",
            (lambda: self.cap("charge, reserve: from the history.   sleep: the first step with no entry", GREEN_M), 0.6),
        ], after=0.3)
        self.play(*self.cap("write every step down, then replay", YELLOW_M), run_time=0.7)
        self.wait(2.0)
