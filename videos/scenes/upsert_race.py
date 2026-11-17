from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\bpayment_uid\b", "payment U I D"),
    (r"\bON CONFLICT\b", "on conflict"),
    (r"\bDO NOTHING\b", "do nothing"),
    (r"\bINSERT\b", "insert"),
    (r"\bCOMMIT\b", "commit"),
    (r"\bROLLBACK\b", "rollback"),
    (r"\bUNIQUE\b", "unique"),
    (r"\bRETURNING\b", "returning"),
    (r"\b23505\b", "two three five zero five"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
READER = np.array([0, 3.2, 0])
WC = {"A": np.array([-4.6, 0.25, 0]), "B": np.array([4.6, 0.25, 0])}
WW, WH = 3.8, 3.9
SLOT_Y = [1.75, 1.2, 0.65, 0.1, -0.45, -1.0]
IX_C, IX_W, IX_H = np.array([0, 1.25, 0]), 4.2, 1.3
CT_C, CT_W, CT_H = np.array([0, -0.75, 0]), 3.4, 1.4
CAP_Y, BAR_Y = -3.3, -2.85
UID = "...a001"


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
        if t > dur + 0.1:
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24, mono=False):
        new = fit((M if mono else T)(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def reader():
    r = RoundedRectangle(corner_radius=0.1, width=2.4, height=0.5, stroke_color=GREY_B, stroke_width=2.5).set_fill("#101214", 1)
    return VGroup(r.move_to(READER), T("card reader", 20).move_to(READER))


def worker(w):
    c = WC[w]
    r = RoundedRectangle(corner_radius=0.12, width=WW, height=WH, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M, 0.08), 1)
    return VGroup(r.move_to(c), T(f"worker {w}", 24, BLUE_M).move_to(c + [0, WH / 2 + 0.3, 0]))


def msg_chip(at, again=False):
    t = M(UID, 20, GOLD_M)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=0.42, stroke_color=GOLD_M, stroke_width=2).set_fill(fillc(GOLD_M, 0.2), 1)
    return VGroup(r, t).move_to(at)


def index_box():
    r = RoundedRectangle(corner_radius=0.12, width=IX_W, height=IX_H, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M, 0.1), 1)
    return VGroup(r.move_to(IX_C), T("unique index on payment_uid", 18, GREY_B).move_to(IX_C + [0, 0.4, 0]))


def count_box():
    r = RoundedRectangle(corner_radius=0.12, width=CT_W, height=CT_H, stroke_color=GREY_B, stroke_width=2.5).set_fill("#101214", 1)
    return VGroup(r.move_to(CT_C), T("payments with this code", 18, GREY_B).move_to(CT_C + [0, 0.45, 0]))


def link_line(w, target_y):
    """A short path from a worker's box to the middle column, for a dot to travel along."""
    sgn = 1 if w == "A" else -1
    x0 = WC[w][0] + sgn * (WW / 2 + 0.05)
    x1 = sgn * -2.15 if target_y > 0.3 else sgn * -1.75
    return Line([x0, target_y, 0], [x1, target_y, 0])


class UpsertRace(Base):
    """sql-09, section 2. A card reader sends one payment message twice; two workers each look for its code, find
    nothing and insert: paid twice. Two waiters and one order book. The unique index on payment_uid is a book where
    checking and writing are one movement of one pen; a transaction hides A's unfinished row, so B waits, then fails
    with 23505. ON CONFLICT DO NOTHING skips instead, and RETURNING tells B it was a repeat. The pen breaks on speed.
    Moral, and a check where A crashes before COMMIT."""

    def set_line(self, w, k, s, color=WHITE, mono=False, size=None):
        size = size or (19 if mono else 23)
        new = left_at((M if mono else T)(s, size, color), WC[w][0] - WW / 2 + 0.22, SLOT_Y[k])
        old, self.wl[w][k] = self.wl[w][k], new
        return [swap(old, new, RIGHT)]

    def clear_lines(self, w, keep=0):
        out = []
        for k in range(keep, len(SLOT_Y)):
            if self.wl[w][k] is not None:
                out.append(FadeOut(self.wl[w][k]))
                self.wl[w][k] = None
        return out

    def set_count(self, v, color=WHITE):
        new = M(str(v), 44, color).move_to(CT_C + [0, -0.2, 0])
        old, self.cnt = self.cnt, new
        return [swap(old, new)]

    def set_entry(self, s, color=WHITE):
        new = T(s, 22, color).move_to(IX_C + [0, -0.2, 0])
        old, self.ent = self.ent, new
        return [swap(old, new)]

    def go(self, w, y, color=YELLOW_M):
        return travel(link_line(w, y), color, 0.6)

    def construct(self):
        self.capm = self.cnt = self.ent = None
        self.wl = {"A": [None] * 6, "B": [None] * 6}
        self.title_card("Paid twice for one coffee?", "check, then insert, and the unique index that decides")

        # ---------------- scene 1: paid twice ----------------
        rd = reader()
        wa, wb = worker("A"), worker("B")
        ct = count_box()
        m1, m2 = msg_chip(READER), msg_chip(READER)
        m1.set_z_index(3)
        m2.set_z_index(3)                     # the chips land inside the workers' boxes, so draw them on top
        self.steps("Picture a café on a busy morning. You tap your card, and the card reader sends a message about the payment "
                   "to the company that records it.", [
            "You tap",
            (lambda: [FadeIn(rd, shift=0.2 * DOWN)], 0.6),
            "sends a message",
            (lambda: [FadeIn(m1, scale=0.6)], 0.3),
            (lambda: [m1.animate.move_to(READER + [-2.2, -0.05, 0])], 0.6),
        ])
        self.steps("The reader hears nothing back, so it sends the same message again. Both copies arrive a millisecond apart.", [
            "hears nothing",
            (lambda: [*self.cap("no answer...", GREY_B)], 0.5),
            "sends the same",
            (lambda: [FadeIn(m2, scale=0.6), *self.cap("so it sends the same message again", GOLD_M)], 0.3),
            (lambda: [m2.animate.move_to(READER + [2.2, -0.05, 0])], 0.6),
        ])
        self.steps("The company runs two copies of its program, called workers, so one can carry on if the other crashes. "
                   "Each worker picks up one copy, and asks the database: do we have this payment yet?", [
            (lambda: [*self.uncap(), FadeIn(wa), FadeIn(wb)], 0.8),
            "Each worker picks",
            (lambda: [m1.animate.move_to(WC["A"] + [0, SLOT_Y[0] - WC["A"][1], 0]), m2.animate.move_to(WC["B"] + [0, SLOT_Y[0] - WC["B"][1], 0]),
                      FadeIn(ct), *self.set_count(0)], 0.9),
            "do we have",
            (lambda: [*self.set_line("A", 1, "do we have it?"), *self.set_line("B", 1, "do we have it?")], 0.6),
        ])
        self.steps("Each hears no. Each stores it. You've paid for one coffee twice.", [
            (lambda: [*self.set_line("A", 1, "do we have it? no"), *self.set_line("B", 1, "do we have it? no")], 0.5),
            "Each stores",
            (lambda: [*self.set_line("A", 2, "store it"), self.go("A", CT_C[1])], 0.6),
            (lambda: self.set_count(1), 0.3),
            (lambda: [*self.set_line("B", 2, "store it"), self.go("B", CT_C[1])], 0.6),
            (lambda: self.set_count(2, RED_M), 0.3),
            "You've paid",
            (lambda: self.cap("one coffee, paid twice", RED_M), 0.5),
        ])
        self.steps("Looking before you write felt careful. So how did it go wrong?", [
            (lambda: self.cap("looking before you write felt careful. so how did it go wrong?", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 2: a code to spot a repeat ----------------
        self.steps("First, how can a worker tell a repeat from a new payment? The card reader gives every payment a long unique code, "
                   "called payment_uid. A copy sent again carries the same code.", [
            (lambda: [*self.uncap(), *self.clear_lines("A", 1), *self.clear_lines("B", 1), *self.set_count(0)], 0.6),
            "a long unique code",
            (lambda: [glow(m1[0], GOLD_M, 1.12)], 0.7),
            "A copy sent again",
            (lambda: [glow(m2[0], GOLD_M, 1.12), *self.cap("payment_uid ...a001: the same code on both copies", GOLD_M)], 0.7),
        ])
        self.steps("A code like that is called an idempotency key: it lets the receiver spot a repeat.", [
            (lambda: self.cap("an idempotency key: lets the receiver spot a repeat", WHITE), 0.6),
        ])
        self.steps("So the obvious plan: look for the code. If it's not there, insert the payment. "
                   "With one message at a time, this passes every test.", [
            (lambda: self.uncap(), 0.3),
            "look for the code",
            (lambda: [*self.set_line("A", 1, "1. look for ...a001"), *self.set_line("B", 1, "1. look for ...a001")], 0.6),
            "If it's not",
            (lambda: [*self.set_line("A", 2, "2. not there? insert"), *self.set_line("B", 2, "2. not there? insert")], 0.6),
            "With one message",
            (lambda: self.cap("one message at a time: passes every test"), 0.5),
        ], after=0.4)

        # ---------------- scene 3: two waiters, and a guess ----------------
        self.steps("Picture two waiters and one paper order book. An order comes in twice, one copy to each waiter. "
                   "Each checks the book. Nothing. Each walks off to write it down. Two plates, one table, one very full customer.", [
            (lambda: [*self.cap("two waiters, one paper order book", WHITE)], 0.5),
            "one copy to each",
            (lambda: [glow(wa[0], BLUE_M, 1.02), glow(wb[0], BLUE_M, 1.02)], 0.8),
            "Each checks the book",
            (lambda: [glow(ct[0], WHITE, 1.04)], 0.8),
            "Two plates",
            (lambda: self.cap("two plates, one table, one very full customer"), 0.5),
        ])
        self.steps("The waiters are the workers, the book is the payments table, checking is a look, and writing is an insert.", [
            (lambda: [*self.cap("waiter = worker", WHITE), Indicate(wa[1], color=BLUE_M), Indicate(wb[1], color=BLUE_M)], 0.6),
            "the book",
            (lambda: [*self.cap("the order book = the payments table", WHITE), glow(ct[0], WHITE, 1.04)], 0.6),
            "checking is",
            (lambda: self.cap("check = a look;   write = an insert", WHITE), 0.5),
        ])
        self.steps("Let's slow our workers down. Worker A looks, worker B looks, and only then does either one insert. "
                   "What does each look find? Pause and guess.", [
            (lambda: [*self.uncap(), *self.clear_lines("A", 1), *self.clear_lines("B", 1)], 0.5),
            "Worker A looks",
            (lambda: [*self.set_line("A", 1, "look: ?", YELLOW_M), self.go("A", CT_C[1], WHITE)], 0.6),
            "worker B looks",
            (lambda: [*self.set_line("B", 1, "look: ?", YELLOW_M), self.go("B", CT_C[1], WHITE)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Zero, for both. Neither has written anything yet. So both decide to insert.", [
            (lambda: [*self.uncap(), *self.set_line("A", 1, "look: 0 found"), *self.set_line("B", 1, "look: 0 found")], 0.6),
            "So both decide",
            (lambda: [*self.set_line("A", 2, "insert"), self.go("A", CT_C[1])], 0.5),
            (lambda: self.set_count(1), 0.3),
            (lambda: [*self.set_line("B", 2, "insert"), self.go("B", CT_C[1])], 0.5),
            (lambda: self.set_count(2, RED_M), 0.3),
        ])
        self.steps("The answer was true when they asked, and out of date a moment later.", [
            (lambda: [*self.cap("true when they asked, out of date a moment later", WHITE), Indicate(self.cnt, color=RED_M, scale_factor=1.2)], 0.7),
        ], after=0.4)

        # ---------------- scene 4: the referee ----------------
        ix = index_box()
        self.steps("Something does stop it here. The payment_uid column is marked UNIQUE: no two rows may share a value.", [
            (lambda: [*self.uncap(), *self.clear_lines("A", 1), *self.clear_lines("B", 1), *self.set_count(0)], 0.6),
            "marked UNIQUE",
            (lambda: self.cap("UNIQUE: no two rows may share a value", WHITE), 0.5),
        ])
        self.steps("PostgreSQL keeps that rule with a unique index: a sorted list of every code in the column, "
                   "and every insert must pass through it.", [
            "a unique index",
            (lambda: [FadeIn(ix, shift=0.1 * DOWN), *self.set_entry("no entry for ...a001", GREY_B)], 0.8),
            "every insert",
            (lambda: [*self.cap("every insert passes through it"), self.go("A", IX_C[1]), self.go("B", IX_C[1])], 0.8),
        ])
        self.steps("In the café, that's a book where checking and writing are one movement of one pen.", [
            (lambda: [*self.cap("a book where checking and writing are one movement of one pen", TEAL_M), glow(ix[0], TEAL_M, 1.03)], 0.9),
        ], after=0.4)

        # ---------------- scene 5: unfinished work ----------------
        self.steps("One more word. A transaction is a group of changes that the database applies all together, or not at all.", [
            "A transaction",
            (lambda: self.cap("a transaction: a group of changes, all together or not at all", WHITE), 0.5),
        ])
        self.steps("COMMIT saves them for good, and shows them to everyone else. ROLLBACK throws them away. "
                   "Until a worker commits, no other worker can see its new row.", [
            (lambda: self.cap("COMMIT: save for good, and show everyone", GREEN_M), 0.5),
            "ROLLBACK",
            (lambda: self.cap("ROLLBACK: throw the changes away", RED_M), 0.5),
            "Until a worker",
            (lambda: self.cap("until COMMIT, nobody else sees the row", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 6: replay the race ----------------
        self.steps("Now replay the race. Worker A inserts. Its code goes into the unique index at once, "
                   "marked as belonging to A's unfinished transaction.", [
            (lambda: self.uncap(), 0.3),
            "Worker A inserts",
            (lambda: [*self.set_line("A", 1, "INSERT: 1 row", mono=True), self.go("A", IX_C[1])], 0.6),
            "Its code goes",
            (lambda: [*self.set_entry("...a001: A's, not committed", GOLD_M), ix[0].animate.set_stroke(GOLD_M)], 0.6),
        ])
        wait_b = T("waits for A", 20, GOLD_M)
        self.steps("Worker B's insert reaches the index and finds the same code. B can't know yet whether A will commit, so it waits.", [
            "Worker B's insert",
            (lambda: [*self.set_line("B", 1, "INSERT:", mono=True), self.go("B", IX_C[1])], 0.6),
            "finds the same",
            (lambda: [Indicate(self.ent, color=GOLD_M, scale_factor=1.1)], 0.6),
            "so it waits",
            (lambda: self.set_line("B", 2, "... waits for A", GOLD_M), 0.5),
            (lambda: [Indicate(self.wl["B"][2], color=GOLD_M, scale_factor=1.1)], 0.7),
        ])
        self.steps("A commits. B's insert fails: duplicate key value violates unique constraint. Its error code is 23505.", [
            (lambda: [*self.set_line("A", 2, "COMMIT: ok", GREEN_M, mono=True), *self.set_entry("...a001: committed", GREEN_M),
                      ix[0].animate.set_stroke(GREEN_M)], 0.6),
            (lambda: [self.go("A", CT_C[1], GREEN_M)], 0.5),
            (lambda: self.set_count(1, GREEN_M), 0.3),
            "B's insert fails",
            (lambda: [*self.set_line("B", 2, "ERROR 23505", RED_M, mono=True),
                      *self.cap("ERROR:  duplicate key value violates unique constraint", RED_M, 22, mono=True)], 0.6),
        ])
        self.steps("Had A rolled back instead, B's insert would have gone through. Either way, one row.", [
            (lambda: self.cap("had A rolled back: B's insert goes through"), 0.5),
            "Either way",
            (lambda: [*self.cap("either way: one row", GREEN_M), Indicate(self.cnt, color=GREEN_M, scale_factor=1.2)], 0.6),
        ], after=0.4)

        # ---------------- scene 7: safe, but clumsy ----------------
        stack = VGroup(*[Square(0.16, stroke_width=0).set_fill(GREY_C, 1) for _ in range(12)]).arrange(RIGHT, buff=0.07)
        left_at(stack, WC["B"][0] - WW / 2 + 0.22, SLOT_Y[4])
        self.steps("So the data is safe. But catching that error is clumsy. An error spoils the whole transaction it happens in.", [
            (lambda: self.cap("safe, but clumsy"), 0.5),
            "An error spoils",
            (lambda: [*self.set_line("B", 3, "500 messages"), FadeIn(stack)], 0.6),
            (lambda: self.cap("one error spoils the whole transaction", RED_M), 0.5),
        ])
        self.steps("A worker that stores 500 messages in one transaction loses all 500 to a single repeat. "
                   "One extra coffee, and the whole morning's orders go back in the queue.", [
            "loses all 500",
            (lambda: [LaggedStart(*[s.animate.set_fill(RED_M, 1) for s in stack], lag_ratio=0.1)], 1.0),
            "One extra coffee",
            (lambda: self.cap("one repeat: all 500 thrown away", RED_M), 0.5),
        ], after=0.4)

        # ---------------- scene 8: decide inside the insert ----------------
        self.steps("Better to put the decision inside the insert itself: INSERT, ON CONFLICT on payment_uid, DO NOTHING. "
                   "The insert asks the unique index in the same step as the write.", [
            (lambda: [FadeOut(stack), *self.clear_lines("A", 1), *self.clear_lines("B", 1), *self.set_count(0),
                      *self.set_entry("no entry for ...a001", GREY_B), ix[0].animate.set_stroke(TEAL_M)], 0.7),
            "INSERT, ON CONFLICT",
            (lambda: self.cap("INSERT ... ON CONFLICT (payment_uid) DO NOTHING RETURNING payment_id", YELLOW_M, 22, mono=True), 0.6),
            "The insert asks",
            (lambda: [glow(ix[0], TEAL_M, 1.03)], 0.8),
        ])
        self.steps("Replay it. A's insert goes in, and RETURNING hands back the new payment's number, 40. "
                   "B's insert finds A's unfinished entry, and waits, as before.", [
            "A's insert",
            (lambda: [*self.set_line("A", 1, "ON CONFLICT DO NOTHING", mono=True, size=17), self.go("A", IX_C[1]),
                      *self.set_entry("...a001: A's, not committed", GOLD_M), ix[0].animate.set_stroke(GOLD_M)], 0.7),
            "RETURNING hands",
            (lambda: self.set_line("A", 2, "1 row back: 40", mono=True), 0.5),
            "B's insert",
            (lambda: [*self.set_line("B", 1, "ON CONFLICT DO NOTHING", mono=True, size=17), self.go("B", IX_C[1])], 0.7),
            "and waits",
            (lambda: self.set_line("B", 2, "... waits for A", GOLD_M), 0.5),
        ])
        self.steps("A commits. This time, B's insert sees the code is there, and skips the row. No error.", [
            (lambda: [*self.set_line("A", 3, "COMMIT: ok", GREEN_M, mono=True), *self.set_entry("...a001: committed", GREEN_M),
                      ix[0].animate.set_stroke(GREEN_M), *self.set_count(1, GREEN_M)], 0.6),
            "skips the row",
            (lambda: self.set_line("B", 2, "skips the row", GREEN_M), 0.5),
            "No error",
            (lambda: self.cap("no error, nothing spoiled", GREEN_M), 0.5),
        ])
        self.steps("RETURNING gives B zero rows, which is how B's program knows the message was a repeat. One payment.", [
            (lambda: self.set_line("B", 3, "0 rows back: a repeat", GREEN_M, mono=True, size=18), 0.6),
            "One payment",
            (lambda: [*self.cap("one payment", GREEN_M), Indicate(self.cnt, color=GREEN_M, scale_factor=1.2)], 0.6),
        ], after=0.4)

        # ---------------- scene 9: where the pen breaks ----------------
        def stream():
            dots = []
            for k in range(24):
                y = IX_C[1] + (-0.45 + 0.9 * ((k * 7) % 24) / 23)
                d = Dot(radius=0.08, color=GREY_B).move_to([-2.4 if k % 2 else 2.4, y, 0])
                dots.append(Succession(FadeIn(d, run_time=0.05), d.animate(run_time=0.6).move_to([0.0, y, 0]), FadeOut(d, run_time=0.1)))
            return [LaggedStart(*dots, lag_ratio=0.08)]

        self.steps("Here the pen picture breaks. A pen serves one writer at a time. PostgreSQL lets thousands of inserts "
                   "with different codes through at once. Only inserts with the same code wait for each other.", [
            (lambda: self.cap("where the pen picture breaks"), 0.5),
            "A pen serves",
            (lambda: self.cap("a pen: one writer at a time"), 0.5),
            "PostgreSQL lets",
            (lambda: [*self.cap("different codes: thousands at once", WHITE), *stream()], 2.2),
            "Only inserts",
            (lambda: [*self.cap("only the same code waits", GOLD_M), glow(m1[0], GOLD_M, 1.12), glow(m2[0], GOLD_M, 1.12)], 0.7),
        ])
        self.steps("And some second messages carry news, and should change the row instead of being skipped. That's the next section.", [
            (lambda: self.cap("news in a second message: change the row (the next section)"), 0.5),
        ], after=0.4)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So how did one coffee get paid twice? Each worker looked, then wrote, and the look was out of date before the write. "
                   "A check in a separate statement can be out of date before you act on it. Let the unique index decide.", [
            (lambda: self.cap("how did one coffee get paid twice?", WHITE), 0.5),
            "Each worker looked",
            (lambda: self.cap("look, then write: the look was out of date before the write", WHITE), 0.5),
            "A check in",
            (lambda: [*self.cap("a separate check can be out of date: let the unique index decide", YELLOW_M), glow(ix[0], GREEN_M, 1.03)], 0.8),
        ])
        self.steps("One quick check. A's insert goes in, and then A crashes before it commits. B is waiting. "
                   "How many payments end up stored, and who stores them? Pause and think.", [
            (lambda: [*self.uncap(), *self.clear_lines("A", 1), *self.clear_lines("B", 1), *self.set_count(0),
                      *self.set_entry("no entry for ...a001", GREY_B), ix[0].animate.set_stroke(TEAL_M)], 0.6),
            "A's insert goes in",
            (lambda: [*self.set_line("A", 1, "ON CONFLICT DO NOTHING", mono=True, size=17),
                      *self.set_entry("...a001: A's, not committed", GOLD_M), ix[0].animate.set_stroke(GOLD_M)], 0.6),
            "A crashes",
            (lambda: self.set_line("A", 2, "crashed, no COMMIT", RED_M), 0.5),
            "B is waiting",
            (lambda: [*self.set_line("B", 1, "ON CONFLICT DO NOTHING", mono=True, size=17), *self.set_line("B", 2, "... waits for A", GOLD_M)], 0.6),
            "Pause and think",
            (lambda: [*self.set_count("?", YELLOW_M), *self.cap("pause and think", YELLOW_M)], 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("One, stored by B. A's unfinished entry vanishes, and B's insert goes ahead. "
                   "Every order of events ends with exactly one row.", [
            (lambda: [*self.uncap(), *self.set_count(1, GREEN_M)], 0.5),
            "A's unfinished",
            (lambda: [*self.set_entry("...a001: B's", GREEN_M), ix[0].animate.set_stroke(GREEN_M)], 0.6),
            "B's insert goes",
            (lambda: self.set_line("B", 2, "1 row back", GREEN_M, mono=True), 0.5),
            "Every order",
            (lambda: self.cap("every order of events: exactly one row", WHITE), 0.5),
        ], after=0.3)
        self.play(*self.cap("let the unique index decide", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
