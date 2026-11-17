from sfz import *

SAY.insert(0, (r"\bfutex\b", "few-tex"))
SAY.insert(0, (r"\bT1\b", "T one"))
SAY.insert(0, (r"\bT2\b", "T two"))
SAY.insert(0, (r"\bEAGAIN\b", "E again"))
SAY.insert(0, (r"\bstrace\b", "S trace"))
SAY.insert(0, (r"\bReentrantLock\b", "re-entrant lock"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
DOOR_C, DOOR_W, DOOR_H = np.array([0.0, 1.2, 0]), 2.0, 2.7      # the lock word, drawn as the bathroom door
DOOR_X0, DOOR_X1 = DOOR_C[0] - DOOR_W / 2, DOOR_C[0] + DOOR_W / 2
DOOR_TOP, DOOR_BOT = DOOR_C[1] + DOOR_H / 2, DOOR_C[1] - DOOR_H / 2
PLATE_C = np.array([0.0, 1.78, 0])
NOTE_C = np.array([0.0, 0.42, 0])
MEAN_Y = -0.52
TC = {1: np.array([-4.7, 1.85, 0]), 2: np.array([-4.7, 0.35, 0])}  # the two threads
TW, TH = 3.2, 1.2
LINE_Y = -1.0                                                     # user space above, the kernel below
Q_C, Q_W, Q_H = np.array([0.0, -2.05, 0]), 5.6, 1.0             # the kernel's wait queue (the barista's list)
SLOT = np.array([1.95, -2.05, 0])
NEAR = np.array([-3.3, -0.64, 0])                                 # just under T2, on its way to the kernel
DOORSTEP = np.array([-3.4, -1.5, 0])                              # at the kernel, outside the queue
RX0 = 2.4                                                         # right column: system-call counter and log
CNT_Y, LOG_Y = 2.75, [2.1, 1.55]
CAP_Y, BAR_Y = -3.3, -2.88
TCOL = {1: TEAL_M, 2: PURPLE_M}
WCOL = {0: GREEN_M, 1: RED_M, 2: RED_M}
WMEAN = {0: "free", 1: "taken", 2: "taken, and someone waits"}


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

    def steps(self, text, items, after=0.2):
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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.7, frac=1.0, keep=False):
    """A dot that runs from a to b (part of the way if frac < 1)."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    seq = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=rt)]
    if not keep:
        seq.append(FadeOut(d, run_time=0.12))
    return d, Succession(*seq)


def run(arr, color=YELLOW_M, rt=0.7, back=False):
    a, b = arr.get_start(), arr.get_end()
    return dot_run(b, a, color, rt)[1] if back else dot_run(a, b, color, rt)[1]


def harrow(a, b, color=GREY_B):
    return Arrow(a, b, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12, max_stroke_width_to_length_ratio=8)


# ---- the pieces ----
def door():
    r = RoundedRectangle(corner_radius=0.1, width=DOOR_W, height=DOOR_H, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1).move_to(DOOR_C)
    plate = RoundedRectangle(corner_radius=0.08, width=1.3, height=0.95, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1).move_to(PLATE_C)
    return VGroup(r, plate)


def knob():
    return Circle(radius=0.085, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLUE_M, 0.6).move_to([0.68, 0.98, 0])


def wdigit(v):
    return M(str(v), 46, WCOL[v]).move_to(PLATE_C)


def wmean(v):
    return T(WMEAN[v], 22, WCOL[v]).move_to([DOOR_C[0], MEAN_Y, 0])


def door_note():
    t = T("someone waits", 17, GOLD_M)
    r = RoundedRectangle(corner_radius=0.05, width=t.width + 0.3, height=0.5, stroke_color=GOLD_M, stroke_width=2).set_fill(fillc(GOLD_M, 0.3), 1)
    return VGroup(r, t).move_to(NOTE_C).set_z_index(3)


def tcard(k):
    c = TC[k]
    r = RoundedRectangle(corner_radius=0.12, width=TW, height=TH, stroke_color=TCOL[k], stroke_width=3).set_fill(fillc(TCOL[k]), 1).move_to(c)
    return VGroup(r, T(f"T{k}: the {'refund' if k == 1 else 'payment'}", 24).move_to(c + 0.22 * UP))


def tstate(k, s, color=GREY_B):
    return fit(T(s, 19, color), TW - 0.3).move_to(TC[k] + 0.26 * DOWN)


def cas_arrow(k):
    y = TC[k][1]
    return harrow([TC[k][0] + TW / 2 + 0.08, y, 0], [DOOR_X0 - 0.08, y, 0])


def cas_label(k, s, color=GREY_B):
    y = TC[k][1]
    return T(s, 18, color).move_to([(TC[k][0] + TW / 2 + DOOR_X0) / 2, y + 0.28, 0])


WAIT_A = ([-3.55, TC[2][1] - TH / 2 - 0.08, 0], [Q_C[0] - Q_W / 2 + 0.35, Q_C[1] + Q_H / 2 + 0.08, 0])
CALL_A = ([-2.8, TC[1][1] - TH / 2 - 0.06, 0], [-1.1, Q_C[1] + Q_H / 2 + 0.08, 0])


def qbox():
    r = RoundedRectangle(corner_radius=0.12, width=Q_W, height=Q_H, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1).move_to(Q_C)
    return r


def qtitle(s):
    return left_at(T(s, 22), Q_C[0] - Q_W / 2 + 0.25, Q_C[1])


def sleeper(k):
    return chip(f"T{k}", TCOL[k], 22).set_z_index(5)


class FutexDeadlock(Base):
    """os-05, section 1. One thread takes and releases a lock a million times: how many system calls? Only the kernel can
    make a thread sleep, so the obvious design asks it on every lock and release (two 150 ns calls against a few ns:
    8 ms becomes about 308 ms). The café bathroom: you lock a vacant door yourself and ask the barista only when it's
    locked, leaving a note. Futex word 0, 1, 2; T1 (refund) takes it with one CAS, T2 (payment) sets 2 and calls
    FUTEX_WAIT, T1's release sees 2 and calls FUTEX_WAKE. The check in FUTEX_WAIT prevents a lost wake-up (EAGAIN).
    strace: 1 call for one thread, 2,749 (1,042 EAGAIN) for four. Limits: fairness and contention. Moral and a check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
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

    def word(self, v, note=None):
        """Set the lock word to v: the digit on the door's plate, its meaning below, and the note for 2."""
        out = [*self.put("digit", wdigit(v)), *self.put("mean", wmean(v))]
        want = (v == 2) if note is None else note
        if want and self.note is None:
            self.note = door_note()
            out.append(FadeIn(self.note, shift=0.1 * DOWN))
        if not want and self.note is not None:
            out.append(FadeOut(self.note))
            self.note = None
        return out

    def state(self, k, s, color=GREY_B):
        return self.put(f"st{k}", tstate(k, s, color))

    def count(self, n):
        self.n = n
        return self.put("count", left_at(T(f"system calls: {n}", 26, GOLD_M), RX0, CNT_Y))

    def log(self, i, s, color=WHITE):
        return self.put(f"log{i}", left_at(M(s, 19, color), RX0, LOG_Y[i]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.note = None
        self.n = 0
        self.title_card("The lock that rarely calls the kernel", "a futex, explained with a café bathroom")

        # ---------------- scene 1: the question ----------------
        h1 = T("one thread:  lock, change the balance, release", 32).move_to([0, 1.5, 0])
        h2 = T("no other thread ever wants the lock", 24, GREY_B).move_to([0, 0.85, 0])
        reps = ["× 1", "× 10", "× 1,000", "× 100,000", "× 1,000,000"]
        hc = [M(r, 44, WHITE).move_to([0, -0.2, 0]) for r in reps]
        self.steps("The café's payments program takes a lock every time it changes a balance. "
                   "Picture one thread doing that a million times, while no other thread ever wants the lock.", [
            "takes a lock",
            (lambda: [FadeIn(h1, shift=0.1 * UP)], 0.8),
            "a million times",
            (lambda: [FadeIn(hc[0])], 0.25),
            *[(lambda i=i: [swap(hc[i - 1], hc[i])], 0.3) for i in range(1, len(hc))],
            "while no other",
            (lambda: [FadeIn(h2, shift=0.1 * UP)], 0.6),
        ])
        hk = T("only the kernel can put a thread to sleep, or wake it", 26, TEAL_M).move_to([0, -1.3, 0])
        hq = T("system calls: ?", 34, GOLD_M).move_to([0, -2.3, 0])
        self.steps("Only the kernel, the core of the operating system, can put a thread to sleep or wake it. "
                   "A request from a program to the kernel is called a system call.", [
            (lambda: [FadeIn(hk, shift=0.1 * UP)], 0.7),
            "is called a system call",
            (lambda: [FadeIn(hq, shift=0.1 * UP)], 0.6),
        ])
        self.steps("So how many system calls does this loop make? Make a guess, and hold on to it.", [
            (lambda: [Indicate(hq, color=GOLD_M, scale_factor=1.15)], 0.9),
        ], after=0.6)

        # ---------------- scene 2: the lock word, and the loser ----------------
        dr = door()
        self.steps("The lock is one number in the program's memory, the lock word. 0 is free, and 1 is taken.", [
            (lambda: [FadeOut(VGroup(h1, h2, hc[-1], hk, hq))], 0.6),
            "one number",
            (lambda: [FadeIn(dr, shift=0.1 * UP), *self.word(0),
                      *self.put("dtitle", T("the lock word", 22, BLUE_M).move_to([0, DOOR_TOP + 0.32, 0]))], 0.8),
            "1 is taken",
            (lambda: self.word(1), 0.5),
            0.4,
            (lambda: self.word(0), 0.5),
        ])
        cards = {k: tcard(k) for k in (1, 2)}
        self.steps("T1, a refund, and T2, a payment, both want it. A thread takes it with compare and swap, one instruction: "
                   "if this holds 0, put 1 in it, and tell me whether you did.", [
            (lambda: [FadeIn(cards[1], shift=0.1 * RIGHT), *self.state(1, "running")], 0.6),
            "T2, a payment",
            (lambda: [FadeIn(cards[2], shift=0.1 * RIGHT), *self.state(2, "running")], 0.6),
            "compare and swap",
            (lambda: self.cap("compare and swap: if this holds 0, put 1 in it, and say whether you did", WHITE), 0.6),
        ])
        ca = {k: cas_arrow(k) for k in (1, 2)}
        self.steps("T1 goes first, and gets it.", [
            (lambda: [GrowArrow(ca[1]), *self.put("cl1", cas_label(1, "0 to 1?"))], 0.5),
            (lambda: [run(ca[1])], 0.6),
            (lambda: [*self.word(1), *self.state(1, "has the lock", TEAL_M)], 0.4),
        ])
        no2 = tick(False, 0.14).move_to(ca[2].get_end() + 0.35 * LEFT + 0.3 * DOWN)
        self.steps("T2 finds 1, and fails. Trying again in a loop would burn its turn on the CPU, while T1 isn't even running.", [
            (lambda: [GrowArrow(ca[2]), *self.put("cl2", cas_label(2, "0 to 1?"))], 0.5),
            (lambda: [run(ca[2])], 0.6),
            (lambda: [Create(no2)], 0.3),
            "Trying again",
            (lambda: [*self.state(2, "trying, and trying again", RED_M), FadeOut(no2)], 0.4),
            (lambda: [run(ca[2], RED_M, 0.45)], 0.5),
            "while T1",
            (lambda: [*self.state(1, "has the lock, not running", GREY_B), cards[1].animate.set_opacity(0.45),
                      run(ca[2], RED_M, 0.45)], 0.5),
            (lambda: [run(ca[2], RED_M, 0.45)], 0.5),
        ])
        kline = DashedLine([-6.6, LINE_Y, 0], [6.6, LINE_Y, 0], dash_length=0.12, stroke_width=1.8, color=GREY_C)
        ulab = left_at(T("the program's memory", 18, GREY_B), -6.55, LINE_Y + 0.3)
        klab = left_at(T("the kernel", 18, GREY_B), -6.55, LINE_Y - 0.3)
        self.steps("It should sleep instead, and only the kernel can do that.", [
            (lambda: [*self.uncap(), *self.state(2, "should sleep", PURPLE_M)], 0.5),
            "only the kernel",
            (lambda: [Create(kline), FadeIn(ulab), FadeIn(klab)], 0.8),
        ])

        # ---------------- scene 3: ask the kernel every time ----------------
        call = harrow(*CALL_A, GREY_B)
        self.steps("The obvious design asks the kernel every time: once to take the lock, and once to release it.", [
            (lambda: [FadeOut(ca[1]), FadeOut(ca[2]), *self.drop("cl1", "cl2"), cards[1].animate.set_opacity(1),
                      *self.state(1, "running"), *self.state(2, "running"), *self.word(0), *self.count(0)], 0.6),
            "once to take",
            (lambda: [GrowArrow(call)], 0.4),
            (lambda: [run(call, rt=0.5)], 0.55),
            (lambda: self.count(1), 0.25),
            (lambda: self.word(1), 0.3),
            "once to release",
            (lambda: [run(call, rt=0.5)], 0.55),
            (lambda: [*self.count(2), *self.word(0)], 0.3),
        ])
        l1 = left_at(T("a million pairs, inside the program", 20, GREY_B), RX0, 1.75)
        b1 = Rectangle(width=0.12, height=0.3, stroke_width=0).set_fill(GREEN_M, 1)
        left_at(b1, RX0, 1.3)
        v1 = T("8 ms", 22, GREEN_M).next_to(b1, RIGHT, buff=0.15)
        l2 = left_at(T("plus two system calls each", 20, GREY_B), RX0, 0.65)
        b2 = Rectangle(width=0.12, height=0.3, stroke_width=0).set_fill(RED_M, 1)
        left_at(b2, RX0, 0.2)
        b2_full = Rectangle(width=4.0, height=0.3, stroke_width=0).set_fill(RED_M, 1)
        left_at(b2_full, RX0, 0.2)
        v2 = left_at(T("about 308 ms", 22, RED_M), RX0, -0.25)
        self.steps("A system call costs about 150 nanoseconds. A million free locks, taken and released inside the program, "
                   "take 8 milliseconds. Two system calls a pair add about 300 more.", [
            (lambda: self.cap("one system call: about 150 nanoseconds", WHITE), 0.6),
            "A million free",
            (lambda: [FadeIn(l1), FadeIn(b1), FadeIn(v1)], 0.6),
            "Two system calls",
            (lambda: [FadeIn(l2), FadeIn(b2)], 0.4),
            (lambda: [Transform(b2, b2_full), LaggedStart(*[run(call, rt=0.3) for _ in range(6)], lag_ratio=0.3)], 1.6),
            (lambda: [FadeIn(v2, shift=0.1 * UP)], 0.4),
        ])
        self.steps("Nearly 40 times slower, for a wait that never happens. It's like asking the barista's permission to use an empty bathroom.", [
            (lambda: self.cap("nearly 40 times slower, for a wait that never happens", RED_M), 0.6),
            "It's like asking",
            (lambda: [Indicate(v2, color=RED_M, scale_factor=1.1)], 0.8),
        ])
        self.steps("Wouldn't it be nice if the kernel stayed out of it, until someone really had to wait?", [
            (lambda: self.cap("keep the kernel out, until someone has to wait?", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 4: the café bathroom ----------------
        kn = knob()
        q = qbox()
        self.steps("In a café, you see Vacant on the bathroom door, go in and lock it, and later you come out. "
                   "Nobody asks anyone.", [
            (lambda: [FadeOut(VGroup(l1, b1, v1, l2, b2, v2, call)), *self.uncap(), *self.drop("count")], 0.6),
            "Vacant",
            (lambda: [FadeIn(kn), *self.put("dtitle", T("the bathroom door", 22, BLUE_M).move_to([0, DOOR_TOP + 0.32, 0]))], 0.6),
            "go in and lock",
            (lambda: [GrowArrow(ca[1])], 0.4),
            (lambda: [run(ca[1])], 0.6),
            (lambda: [*self.word(1), *self.state(1, "inside", TEAL_M)], 0.4),
            "later you come out",
            (lambda: [run(ca[1], back=True)], 0.6),
            (lambda: [*self.word(0), *self.state(1, "running")], 0.4),
            "Nobody asks",
            (lambda: [glow(dr[0], BLUE_M, 1.02)], 0.7),
        ])
        self.steps("Only when the door is already locked do you go to the counter, and ask the barista to call you when it's free.", [
            (lambda: [run(ca[1], rt=0.5)], 0.5),
            (lambda: [*self.word(1), *self.state(1, "inside", TEAL_M)], 0.3),
            "already locked",
            (lambda: [GrowArrow(ca[2])], 0.4),
            (lambda: [run(ca[2])], 0.6),
            "go to the counter",
            (lambda: [FadeIn(q), *self.put("qt", qtitle("the barista's list")), *self.put("slot", T("empty", 20, GREY_B).move_to(SLOT))], 0.7),
            "ask the barista",
            (lambda: [*self.state(2, "waiting to be called", PURPLE_M)], 0.5),
        ])
        self.steps("And you leave a note on the door, so whoever comes out knows someone is waiting.", [
            "leave a note",
            (lambda: self.word(2), 0.6),
            "whoever comes out",
            (lambda: [Indicate(self.note, color=GOLD_M, scale_factor=1.1)], 0.8),
        ])
        self.steps("Let's map it. The door's sign is the lock word, in the program's own memory. Each customer is a thread.", [
            "The door's sign",
            (lambda: [*self.put("dtitle", T("the lock word", 22, BLUE_M).move_to([0, DOOR_TOP + 0.32, 0])), glow(dr[1], BLUE_M, 1.05)], 0.8),
            "own memory",
            (lambda: [Indicate(ulab, color=WHITE, scale_factor=1.15)], 0.7),
            "Each customer",
            (lambda: [glow(cards[1][0], TEAL_M, 1.03), glow(cards[2][0], PURPLE_M, 1.03)], 0.8),
        ])
        self.steps("The barista is the kernel, and the list of names at the counter is its wait queue.", [
            (lambda: [Indicate(klab, color=WHITE, scale_factor=1.15)], 0.7),
            "the list of names",
            (lambda: [*self.put("qt", qtitle("the kernel's wait queue")), glow(q, WHITE, 1.02)], 0.8),
        ])
        self.steps("And the note is a third value. 2 means taken, and someone is waiting.", [
            "a third value",
            (lambda: [Indicate(self.lab["digit"], color=RED_M, scale_factor=1.2)], 0.7),
            "2 means",
            (lambda: [Indicate(self.lab["mean"], color=RED_M, scale_factor=1.1)], 0.7),
        ], after=0.5)

        # ---------------- scene 5: one round, counting system calls ----------------
        self.steps("Now one round, counting system calls. T1 wants the lock. The word is 0, so one compare and swap makes it 1. "
                   "T1 is in, and the kernel never heard about it.", [
            (lambda: [FadeOut(ca[1]), FadeOut(ca[2]), *self.word(0), *self.state(1, "running"), *self.state(2, "running"), *self.count(0)], 0.6),
            "T1 wants",
            (lambda: [GrowArrow(ca[1]), *self.put("cl1", cas_label(1, "0 to 1?"))], 0.4),
            "one compare",
            (lambda: [run(ca[1])], 0.6),
            (lambda: [*self.word(1), *self.state(1, "has the lock", TEAL_M), *self.put("cl1", cas_label(1, "got it", GREEN_M))], 0.4),
            "never heard",
            (lambda: [Indicate(self.lab["count"], color=GOLD_M, scale_factor=1.1)], 0.7),
        ])
        no2 = tick(False, 0.14).move_to(ca[2].get_end() + 0.35 * LEFT + 0.3 * DOWN)
        self.steps("T2's compare and swap expects 0, finds 1, and fails.", [
            (lambda: [GrowArrow(ca[2]), *self.put("cl2", cas_label(2, "0 to 1?"))], 0.4),
            "finds 1",
            (lambda: [run(ca[2])], 0.6),
            (lambda: [Create(no2), *self.put("cl2", cas_label(2, "found 1", RED_M))], 0.4),
        ])
        wait_a = harrow(*WAIT_A, PURPLE_M)
        self.steps("So T2 sets the word to 2, the note, and makes the first system call: futex wait. "
                   "Put me to sleep, but only if the word still holds 2.", [
            (lambda: [FadeOut(no2), *self.word(2)], 0.6),
            "makes the first",
            (lambda: [GrowArrow(wait_a), *self.log(0, "FUTEX_WAIT(word, 2)", PURPLE_M)], 0.6),
            (lambda: self.count(1), 0.4),
            "but only if",
            (lambda: [Indicate(self.lab["digit"], color=RED_M, scale_factor=1.2)], 0.8),
        ])
        s2 = sleeper(2).move_to(NEAR)
        self.steps("The kernel checks, and puts T2 on the wait queue. T2 sleeps, and uses no CPU at all.", [
            "puts T2",
            (lambda: [FadeIn(s2), *self.drop("slot")], 0.3),
            (lambda: [s2.animate.move_to(SLOT), cards[2].animate.set_opacity(0.4), *self.state(2, "asleep in the kernel", GREY_B)], 0.9),
            "no CPU",
            (lambda: [glow(q, WHITE, 1.02)], 0.7),
        ])
        call = harrow(*CALL_A, TEAL_M)
        self.steps("T1 finishes. It sets the word to 0, and looks at the old value. It was 2, so T1 makes the second call: "
                   "futex wake, wake one sleeper.", [
            (lambda: [*self.drop("cl1", "cl2"), FadeOut(wait_a), FadeOut(ca[2])], 0.4),
            "sets the word",
            (lambda: [run(ca[1], back=True)], 0.5),
            (lambda: [*self.word(0, note=False), *self.state(1, "done", GREY_B)], 0.4),
            "It was 2",
            (lambda: [*self.put("cl1", cas_label(1, "old value: 2", RED_M))], 0.5),
            "makes the second",
            (lambda: [GrowArrow(call), *self.log(1, "FUTEX_WAKE(word, 1)", TEAL_M)], 0.5),
            (lambda: [run(call), *self.count(2)], 0.7),
        ])
        self.steps("The kernel takes T2 off the queue. T2 tries again and gets the lock. "
                   "It writes 2, to be safe: others may still be asleep.", [
            (lambda: [FadeOut(call), *self.drop("cl1"), FadeOut(ca[1])], 0.3),
            (lambda: [s2.animate.move_to(NEAR), cards[2].animate.set_opacity(1), *self.state(2, "awake"),
                      *self.put("slot", T("empty", 20, GREY_B).move_to(SLOT))], 0.8),
            (lambda: [FadeOut(s2)], 0.2),
            "tries again",
            (lambda: [GrowArrow(ca[2])], 0.3),
            (lambda: [run(ca[2])], 0.5),
            (lambda: [*self.state(2, "has the lock", PURPLE_M), *self.word(2)], 0.4),
            "It writes 2",
            (lambda: [Indicate(self.lab["digit"], color=RED_M, scale_factor=1.2)], 0.7),
        ])
        self.steps("One wait cost two system calls. With nobody waiting, it would have cost none.", [
            (lambda: [Indicate(self.lab["count"], color=GOLD_M, scale_factor=1.12)], 0.8),
            "With nobody",
            (lambda: self.cap("one wait: two system calls.   nobody waiting: none", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 6: the name ----------------
        self.steps("This is called a futex, short for fast user space mutex. Mutex is another name for a lock. "
                   "User space is where ordinary programs run, outside the kernel.", [
            (lambda: [FadeOut(ca[2]), *self.state(2, "running"), *self.word(0), *self.state(1, "running"),
                      *self.cap("futex: fast user-space mutex", BLUE_M, 30)], 0.7),
            "Mutex is",
            (lambda: self.cap("mutex: another name for a lock", WHITE), 0.5),
            "User space",
            (lambda: [*self.cap("user space: where ordinary programs run, outside the kernel", WHITE),
                      Indicate(ulab, color=WHITE, scale_factor=1.15)], 0.7),
        ])

        # ---------------- scene 7: the lost wake-up ----------------
        self.steps("Why does futex wait check the word before it sleeps? Let's be fair to a version that doesn't.", [
            (lambda: [*self.uncap(), *self.drop("log0", "log1"), *self.count(0)], 0.5),
            "a version that doesn't",
            (lambda: self.cap("a futex wait with no check: just sleep", GREY_B), 0.6),
        ])
        wait_a = harrow(*WAIT_A, PURPLE_M)
        call = harrow(*CALL_A, TEAL_M)
        slow = Dot(radius=0.09, color=PURPLE_M).move_to(wait_a.get_start()).set_z_index(6)
        self.steps("T1 holds the lock, and T2 sets the word to 2. But before T2's call reaches the kernel, T1 finishes. "
                   "It sets 0, sees the old 2, and calls wake. The queue is empty, so nobody wakes up.", [
            (lambda: [*self.word(1), *self.state(1, "has the lock", TEAL_M)], 0.5),
            "T2 sets",
            (lambda: [*self.word(2), *self.state(2, "about to sleep", PURPLE_M)], 0.5),
            "But before",
            (lambda: [GrowArrow(wait_a), FadeIn(slow)], 0.4),
            (lambda: [slow.animate(rate_func=linear).move_to(wait_a.point_from_proportion(0.35))], 0.9),
            "T1 finishes",
            (lambda: [*self.word(0, note=False), *self.state(1, "done", GREY_B)], 0.4),
            "calls wake",
            (lambda: [GrowArrow(call)], 0.3),
            (lambda: [run(call), *self.count(1)], 0.7),
            "The queue is empty",
            (lambda: [Indicate(self.lab["slot"], color=RED_M, scale_factor=1.3), *self.log(0, "FUTEX_WAKE: woke nobody", RED_M)], 0.8),
        ])
        s2 = sleeper(2)
        self.steps("Now T2's call arrives. What happens to T2? Pause and guess.", [
            (lambda: [FadeOut(call)], 0.3),
            (lambda: [slow.animate.move_to(wait_a.get_end()), *self.count(2), *self.log(1, "FUTEX_WAIT(word, 2)", PURPLE_M)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("T2 falls asleep, and nobody will ever wake it. The lock is free, and T2 waits outside an empty bathroom, forever. "
                   "That's called a lost wake-up.", [
            (lambda: [*self.uncap(), FadeOut(slow), FadeIn(s2.move_to(DOORSTEP)), *self.drop("slot")], 0.4),
            (lambda: [s2.animate.move_to(SLOT), cards[2].animate.set_opacity(0.4), *self.state(2, "asleep, forever", RED_M),
                      *self.log(1, "FUTEX_WAIT: asleep", RED_M)], 0.9),
            "The lock is free",
            (lambda: [Indicate(self.lab["mean"], color=GREEN_M, scale_factor=1.15)], 0.8),
            "a lost wake-up",
            (lambda: self.cap("a lost wake-up: asleep on a lock that nobody holds", RED_M), 0.6),
        ])
        self.steps("With the check, the kernel sees 0 instead of the 2 that T2 expected, and won't put it to sleep. "
                   "The call fails at once with an error called EAGAIN, try again, and T2 takes the lock.", [
            (lambda: [s2.animate.move_to(DOORSTEP), *self.state(2, "calling futex wait", PURPLE_M),
                      *self.put("slot", T("empty", 20, GREY_B).move_to(SLOT)),
                      cards[2].animate.set_opacity(1), *self.cap("futex wait, with the check", WHITE)], 0.6),
            "the kernel sees 0",
            (lambda: [Indicate(self.lab["digit"], color=GREEN_M, scale_factor=1.25)], 0.7),
            "fails at once",
            (lambda: [s2.animate.move_to(NEAR), *self.log(1, "FUTEX_WAIT: EAGAIN", GOLD_M)], 0.8),
            (lambda: [FadeOut(s2)], 0.2),
            "T2 takes",
            (lambda: [GrowArrow(ca[2])], 0.3),
            (lambda: [run(ca[2])], 0.5),
            (lambda: [*self.word(2), *self.state(2, "has the lock", PURPLE_M)], 0.4),
        ])
        self.steps("It's the barista glancing at the door once more, before writing your name down.", [
            (lambda: [FadeOut(wait_a), glow(dr[0], BLUE_M, 1.02), *self.cap("the check: glance at the door once more, then write the name", BLUE_M)], 0.9),
        ], after=0.5)

        # ---------------- scene 8: count the calls ----------------
        r1a = left_at(T("1 thread, a million locks", 22, WHITE), RX0, 2.1)
        r1b = left_at(T("futex calls: 1", 24, GOLD_M), RX0, 1.62)
        r1c = left_at(T("(the main thread waiting for the worker)", 17, GREY_B), RX0, 1.22)
        r2a = left_at(T("4 threads, one lock", 22, WHITE), RX0, 0.55)
        r2b = left_at(T("futex calls: 2,749", 24, GOLD_M), RX0, 0.07)
        r2c = left_at(T("1,042 failed with EAGAIN", 19, RED_M), RX0, -0.35)
        self.steps("Now, your guess from the start. strace is a tool that counts every system call a program makes.", [
            (lambda: [FadeOut(ca[2]), *self.word(0), *self.state(2, "running"), *self.drop("log0", "log1", "count"),
                      *self.cap("strace: a tool that counts a program's system calls", WHITE)], 0.7),
        ])
        self.steps("One thread, a million locks nobody else wanted: 1 futex call. And that one isn't even the lock: "
                   "it's the main thread, waiting for the worker to finish.", [
            (lambda: [FadeIn(r1a)], 0.5),
            ": 1 futex",
            (lambda: [FadeIn(r1b, shift=0.1 * UP)], 0.5),
            "isn't even",
            (lambda: [Indicate(r1b, color=GOLD_M, scale_factor=1.1)], 0.7),
            "it's the main",
            (lambda: [FadeIn(r1c)], 0.5),
        ])
        self.steps("Four threads, all fighting over one lock: 2,749 calls. And 1,042 of them failed with EAGAIN: "
                   "the check, catching the same race, over and over. A lock is only free while nobody else wants it.", [
            (lambda: [FadeIn(r2a)], 0.5),
            "2,749",
            (lambda: [FadeIn(r2b, shift=0.1 * UP)], 0.5),
            "And 1,042",
            (lambda: [FadeIn(r2c, shift=0.1 * UP)], 0.5),
            "the check, catching",
            (lambda: [Indicate(r2c, color=RED_M, scale_factor=1.1)], 0.8),
            "A lock is only",
            (lambda: self.cap("a lock is only free while nobody else wants it", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 9: limits ----------------
        newc = chip("T3: a newcomer", GREEN_M, 20).move_to([3.4, 1.85, 0])
        new_a = harrow([newc.get_left()[0] - 0.08, 1.85, 0], [DOOR_X1 + 0.08, 1.85, 0], GREEN_M)
        s2 = sleeper(2).move_to(SLOT)
        self.steps("Where the café picture breaks: fairness. A barista calls names in order. A woken thread has to race any newcomer "
                   "for the compare and swap, and the newcomer, already running, often wins.", [
            (lambda: [FadeOut(VGroup(r1a, r1b, r1c, r2a, r2b, r2c)), *self.cap("where the café picture breaks: fairness", WHITE)], 0.6),
            "A woken thread",
            (lambda: [FadeIn(s2), *self.drop("slot"), *self.state(2, "just woken", PURPLE_M)], 0.4),
            (lambda: [s2.animate.move_to(DOORSTEP)], 0.7),
            "any newcomer",
            (lambda: [FadeIn(newc, shift=0.2 * LEFT)], 0.5),
            "already running",
            (lambda: [GrowArrow(new_a)], 0.3),
            (lambda: [run(new_a, GREEN_M, 0.5), *self.word(1)], 0.6),
            "often wins",
            (lambda: [s2.animate.move_to(SLOT), *self.state(2, "back to sleep", GREY_B)], 0.7),
        ])
        self.steps("The kernel wakes you up. It doesn't save your place.", [
            (lambda: self.cap("the kernel wakes you up; it doesn't save your place", YELLOW_M), 0.6),
        ], after=0.4)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So the moral of the story: ask the barista only when the door is locked. "
                   "A free lock costs one instruction, and only waiting reaches the kernel.", [
            (lambda: [FadeOut(VGroup(newc, new_a, s2)), *self.state(2, "running"), *self.word(0),
                      *self.put("slot", T("empty", 20, GREY_B).move_to(SLOT)),
                      *self.cap("ask the barista only when the door is locked", YELLOW_M, 30)], 0.6),
            "A free lock",
            (lambda: [GrowArrow(ca[1])], 0.3),
            (lambda: [run(ca[1]), *self.word(1), *self.state(1, "has the lock", TEAL_M)], 0.7),
            "only waiting",
            (lambda: [glow(q, WHITE, 1.02)], 0.8),
        ], after=0.4)
        self.steps("One quick check. T1 releases the lock, and the old value was 1, not 2. Does T1 call the kernel? Pause and think.", [
            (lambda: [*self.uncap(), *self.count(0)], 0.4),
            "T1 releases",
            (lambda: [run(ca[1], back=True)], 0.6),
            (lambda: [*self.word(0), *self.state(1, "releasing"), *self.put("cl1", cas_label(1, "old value: 1", RED_M))], 0.4),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ok = tick(True, 0.2).next_to(self.lab["count"], RIGHT, buff=0.3)
        self.steps("No. 1 means no note on the door, so nobody is waiting. Releasing the lock is one instruction.", [
            (lambda: [*self.uncap(), *self.state(1, "done, no system call", TEAL_M)], 0.5),
            "no note",
            (lambda: [glow(dr[0], BLUE_M, 1.02)], 0.7),
            "one instruction",
            (lambda: [Create(ok)], 0.5),
        ], after=0.4)
        self.steps("And when waiting is this cheap, a thread that waits forever costs nothing either. "
                   "That's how the café's card reader froze, and it's next.", [
            (lambda: [FadeOut(ok), *self.drop("cl1"), FadeOut(ca[1]), *self.state(1, "running"),
                      *self.cap("when waiting is this cheap, waiting forever is cheap too", WHITE)], 0.6),
            "That's how",
            (lambda: [cards[1].animate.set_opacity(0.4), cards[2].animate.set_opacity(0.4),
                      *self.state(1, "waiting for T2", GREY_B), *self.state(2, "waiting for T1", GREY_B)], 0.9),
        ], after=0.3)
        self.play(*self.cap("ask the barista only when the door is locked", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
