from sfz import *

SAY.insert(0, (r"\bfutex\b", "few-tex"))
SAY.insert(0, (r"\bT1\b", "T one"))
SAY.insert(0, (r"\bT2\b", "T two"))
SAY.insert(0, (r"\bACC-1001\b", "account ten oh one"))
SAY.insert(0, (r"\bACC-2002\b", "account twenty oh two"))

TX, TY, TW, TH = 4.6, 2.3, 3.2, 1.3        # threads at (-TX, TY) and (TX, TY)
WY = 2.3                                   # the lock word
KY, KH = -1.9, 1.3                         # the kernel band
QX, QY, QW = 0.6, -2.1, 4.6               # wait queue inside it
P2Y = 1.1                                  # threads in the deadlock part
LOCKY = {0: 2.6, 1: -0.35}                 # merchant lock above, customer lock below
LW, LH = 3.0, 0.95
NOTE_Y = -3.2


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def rrect(w, h, c, color=WHITE, sw=3, fill=None):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=sw)
    return r.set_fill(fill if fill is not None else fillc(color), 1).move_to(c)


def tpos(side, y=TY):
    return np.array([-TX if side == 0 else TX, y, 0])


def thread(side, name, color, y=TY):
    c = tpos(side, y)
    return VGroup(rrect(TW, TH, c, color), T(name, 26).move_to(c + 0.28 * UP), tstate(side, "running", y=y))


def tstate(side, s, color=GREY_B, y=TY):
    return T(s, 20, color).move_to(tpos(side, y) + 0.27 * DOWN)


def ts2(side, s, color=GREY_B):
    return tstate(side, s, color, P2Y)


def word_val(v):
    col = {0: GREEN_M, 1: GOLD_M, 2: RED_M}[v]
    mean = {0: "free", 1: "taken", 2: "taken, someone waits"}[v]
    return VGroup(M(str(v), 44, col).move_to([0, WY - 0.02, 0]), T(mean, 19, col).move_to([0, WY - 0.55, 0]))


def lock_box(k, acct, who, color=WHITE):
    c = np.array([0, LOCKY[k], 0])
    return VGroup(rrect(LW, LH, c, color, 2.5), M(acct, 24).move_to(c + 0.2 * UP), T(who, 20, GREY_B).move_to(c + 0.23 * DOWN))


def lock_sub(k, s, color=GREY_B):
    return T(s, 20, color).move_to(np.array([0, LOCKY[k], 0]) + 0.23 * DOWN)


def link_ends(side, k):
    """From a thread's inner edge to the near side of lock k."""
    sx = -1 if side == 0 else 1
    a = np.array([sx * (TX - TW / 2) - sx * 0.05, P2Y + (0.38 if k == 0 else -0.38), 0])
    b = np.array([sx * (LW / 2 + 0.08), LOCKY[k], 0])
    return a, b


def qslot(k):
    return np.array([QX - 1.2 + 2.4 * k, QY, 0])


def sleeper(name, color, k):
    return chip(name, color, 20).move_to(qslot(k)).set_z_index(4)


def note(s, color=GREY_B):
    return chip(s, color, 21).move_to([0, NOTE_Y, 0])


def syscalls(n):
    return T(f"system calls: {n}", 22, TEAL_M).move_to([4.85, QY, 0])


class FutexDeadlock(Base):
    """os-05, sections 1 to 3: a lock word taken with one compare-and-swap (0 to 1) and no system call; T2 finds 1, sets
    2 and calls FUTEX_WAIT; T1's unlock sees 2 and calls FUTEX_WAKE (lab: one thread, a million lock pairs, no futex
    call for them; four threads, 2,749). Then a refund of 120 (merchant ACC-1001 to customer ACC-2002) and a payment of 80
    the other way each lock their source first: deadlock, both asleep in the kernel. Ordering by account id removes the
    cycle; the merchant ends at 10,000 - 120 + 80 = 9,960."""

    def construct(self):
        self.title_card("Futexes and deadlock", "cheap locks, and two threads waiting on each other forever")

        t1, t2 = thread(0, "T1", BLUE_M), thread(1, "T2", PURPLE_M)
        wbox = rrect(3.0, 1.7, [0, WY, 0], WHITE, fill=BLACK)
        wtitle = T("lock word", 20, GREY_B).move_to([0, WY + 0.58, 0])
        wv = word_val(0)
        self.steps("Two payment threads update one merchant balance, so each must take a lock first.", [
            (lambda: [FadeIn(t1, shift=0.1 * RIGHT), FadeIn(t2, shift=0.1 * LEFT)], 0.8),
            "so each must",
            (lambda: [FadeIn(wbox), FadeIn(wtitle), FadeIn(wv)], 0.7),
        ])

        band = rrect(12.8, KH, [0, KY, 0], TEAL_M)
        klab = T("kernel", 24, TEAL_M).move_to([-6.4 + 0.75, KY + KH / 2 - 0.3, 0])
        user = T("your process's memory", 20, GREY_B).move_to([0, 0.85, 0])
        a1 = Arrow([-TX + TW / 2 + 0.05, WY, 0], [-1.55, WY, 0], buff=0, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.15)
        c1 = M("CAS 0→1", 18, BLUE_M).move_to([(-TX + TW / 2 - 1.55) / 2, WY - 0.95, 0])
        sc = syscalls(0)
        self.steps("The lock is one number in memory, and 0 means free. T1 takes it with a compare and swap: "
                   "if it's 0, make it 1. One instruction, and the kernel never hears of it.", [
            (lambda: [FadeIn(band), FadeIn(klab), FadeIn(user), FadeIn(sc)], 0.7),
            "T1 takes it",
            (lambda: [GrowArrow(a1), FadeIn(c1)], 0.5),
            (lambda: [flow(a1, BLUE_M, 0.5)], 0.5),
            "make it 1",
            (lambda: [Transform(wv, word_val(1)), Transform(t1[2], tstate(0, "has the lock", BLUE_M))], 0.6),
            "and the kernel",
            (lambda: [glow(band, TEAL_M, 1.01), Indicate(sc, color=TEAL_M)], 0.9),
        ])

        a2 = Arrow([TX - TW / 2 - 0.05, WY, 0], [1.55, WY, 0], buff=0, stroke_width=3, color=PURPLE_M, max_tip_length_to_length_ratio=0.15)
        c2 = M("CAS 0→1", 18, PURPLE_M).move_to([(TX - TW / 2 + 1.55) / 2, WY - 0.95, 0])
        xs = {}

        def fail():
            xs["x"] = tick(False, 0.16).move_to([(TX - TW / 2 + 1.55) / 2, WY + 0.35, 0])
            return [Create(xs["x"]), Transform(t2[2], tstate(1, "CAS failed", RED_M))]

        self.steps("T2's swap expects 0, finds 1, and fails. Rather than spin, it should sleep, "
                   "and only the kernel can do that.", [
            (lambda: [GrowArrow(a2), FadeIn(c2)], 0.5),
            (lambda: [flow(a2, PURPLE_M, 0.5)], 0.5),
            "and fails",
            (lambda: fail(), 0.5),
            "it should sleep",
            (lambda: [glow(band, TEAL_M, 1.01)], 0.8),
        ])

        down = Arrow([TX, TY - TH / 2 - 0.05, 0], [TX, KY + KH / 2 + 0.05, 0], buff=0, stroke_width=3, color=PURPLE_M,
                     max_tip_length_to_length_ratio=0.12)
        wait_call = M("futex(FUTEX_WAIT, &word, 2)", 18, PURPLE_M)
        wait_call.move_to([TX - 0.2 - wait_call.width / 2, 0.15, 0])
        qbox = rrect(QW, 0.7, [QX, QY, 0], GREY_B, 2, fill=BLACK)
        qlab = T("asleep on a futex", 18, GREY_B).move_to([QX, QY + 0.57, 0])
        s2 = sleeper("T2", PURPLE_M, 0)
        self.steps("T2 sets the word to 2, taken with a waiter, and calls futex wait. "
                   "The kernel checks it still says 2, and puts T2 to sleep.", [
            (lambda: [FadeOut(xs["x"]), Transform(wv, word_val(2)), flow(a2, PURPLE_M, 0.5)], 0.6),
            "and calls futex",
            (lambda: [GrowArrow(down), FadeIn(wait_call), Transform(sc, syscalls(1))], 0.7),
            "The kernel checks",
            (lambda: [FadeIn(qbox), FadeIn(qlab), Indicate(wv[0], color=RED_M)], 0.7),
            "and puts T2",
            (lambda: [FadeIn(s2, shift=0.4 * DOWN), Transform(t2[2], tstate(1, "asleep, no CPU", GREY_B)),
                      t2[0].animate.set_stroke(GREY_D)], 0.7),
        ])

        up = Arrow([-TX, TY - TH / 2 - 0.05, 0], [-TX, KY + KH / 2 + 0.05, 0], buff=0, stroke_width=3, color=BLUE_M,
                   max_tip_length_to_length_ratio=0.12)
        wake_call = M("futex(FUTEX_WAKE, &word, 1)", 18, BLUE_M)
        wake_call.move_to([-TX + 0.2 + wake_call.width / 2, 0.15, 0])
        self.steps("T1 unlocks by swapping in 0. The old value was 2, so it makes a futex call to wake a sleeper. "
                   "The kernel wakes T2, which takes the lock.", [
            (lambda: [Transform(wv, word_val(0)), Transform(t1[2], tstate(0, "unlocked", BLUE_M))], 0.6),
            "so it makes",
            (lambda: [FadeOut(wait_call), FadeOut(down), GrowArrow(up), FadeIn(wake_call), Transform(sc, syscalls(2))], 0.7),
            "The kernel wakes",
            (lambda: [FadeOut(s2, shift=0.4 * UP), t2[0].animate.set_stroke(PURPLE_M)], 0.6),
            "which takes the lock",
            (lambda: [Transform(wv, word_val(2)), Transform(t2[2], tstate(1, "has the lock", PURPLE_M)), flow(a2, PURPLE_M, 0.5)], 0.6),
        ])

        lab = note("lab: 1 thread, a million lock pairs: no futex calls for them. 4 threads: 2,749", TEAL_M)
        self.steps("With no waiters, the kernel never joins in. That's a futex. In the lab, a million uncontended locks "
                   "made no futex calls, and four threads fighting made 2,749.", [
            (lambda: [FadeOut(up), FadeOut(wake_call)], 0.5),
            "That's a futex",
            (lambda: [glow(wbox, GREEN_M, 1.04)], 0.8),
            "In the lab",
            (lambda: [FadeIn(lab, shift=0.1 * UP)], 0.7),
        ])

        # ---- two locks ------------------------------------------------------------------------------------------------
        L = {0: lock_box(0, "ACC-1001", "merchant: 10,000"), 1: lock_box(1, "ACC-2002", "customer")}
        rf, pm = thread(0, "refund", BLUE_M, P2Y), thread(1, "payment", PURPLE_M, P2Y)
        rf_sub = T("merchant → customer, 120", 18, GREY_B).move_to(tpos(0, P2Y) + 0.95 * DOWN)
        pm_sub = T("customer → merchant, 80", 18, GREY_B).move_to(tpos(1, P2Y) + 0.95 * DOWN)
        self.steps("Now two locks. A refund moves 120 from the merchant to a customer, and a payment moves 80 back. "
                   "Each locks its source first.", [
            (lambda: [FadeOut(lab), FadeOut(VGroup(a1, a2, c1, c2)), FadeOut(VGroup(wbox, wtitle, wv)), FadeOut(user),
                      Transform(sc, syscalls(0))], 0.6),
            (lambda: [FadeIn(L[0], shift=0.1 * DOWN), FadeIn(L[1], shift=0.1 * UP)], 0.7),
            "A refund",
            (lambda: [Transform(t1, rf), FadeIn(rf_sub)], 0.7),
            "and a payment",
            (lambda: [Transform(t2, pm), FadeIn(pm_sub)], 0.7),
        ])

        def hold(side, k, color):
            a, b = link_ends(side, k)
            return Line(a, b, stroke_width=7, color=color)

        def want(side, k, color):
            a, b = link_ends(side, k)
            return DashedLine(a, b, dash_length=0.12, stroke_width=3, color=color).add_tip(tip_length=0.2, tip_width=0.2)

        hlab = {}

        h_rf, h_pm = hold(0, 0, BLUE_M), hold(1, 1, PURPLE_M)
        self.steps("The refund locks the merchant. At the same moment, the payment locks the customer.", [
            (lambda: [FadeOut(rf_sub), FadeOut(pm_sub), Create(h_rf), L[0][0].animate.set_stroke(BLUE_M),
                      Transform(t1[2], ts2(0, "holds ACC-1001", BLUE_M))], 0.7),
            "At the same moment",
            (lambda: [Create(h_pm), L[1][0].animate.set_stroke(PURPLE_M), Transform(t2[2], ts2(1, "holds ACC-2002", PURPLE_M))], 0.7),
        ])

        w_rf, w_pm = want(0, 1, RED_M), want(1, 0, RED_M)
        q1, q2 = sleeper("refund", BLUE_M, 0), sleeper("payment", PURPLE_M, 1)
        self.steps("Now the refund wants the customer, so it sleeps on that lock's futex. "
                   "The payment wants the merchant, and sleeps too.", [
            (lambda: [Create(w_rf)], 0.7),
            "so it sleeps",
            (lambda: [FadeIn(q1, shift=0.4 * DOWN), Transform(t1[2], ts2(0, "asleep", GREY_B)), Transform(sc, syscalls(1))], 0.7),
            "The payment wants",
            (lambda: [Create(w_pm)], 0.7),
            "and sleeps too",
            (lambda: [FadeIn(q2, shift=0.4 * DOWN), Transform(t2[2], ts2(1, "asleep", GREY_B)), Transform(sc, syscalls(2))], 0.7),
        ])

        dl = note("deadlock: each holds the lock the other needs", RED_M)
        self.steps("Each holds what the other needs: a deadlock. The kernel just sees two "
                   "sleeping threads using no CPU, and nothing will ever wake them.", [
            (lambda: [glow(t1[0], RED_M, 1.03), glow(t2[0], RED_M, 1.03)], 0.8),
            "a deadlock",
            (lambda: [FadeIn(dl, shift=0.1 * UP), *[m.animate.set_stroke(width=9) for m in (h_rf, h_pm)]], 0.7),
            "The kernel just sees",
            (lambda: [glow(band, TEAL_M, 1.01)], 0.9),
        ])

        order = note("lock order: smaller account id first", GREEN_M)
        self.steps("The fix: always take the smaller account id first, whichever way the money goes.", [
            (lambda: [FadeOut(VGroup(h_rf, h_pm, w_rf, w_pm)), FadeOut(q1), FadeOut(q2), FadeOut(dl),
                      L[0][0].animate.set_stroke(WHITE), L[1][0].animate.set_stroke(WHITE),
                      Transform(t1[2], ts2(0, "running")), Transform(t2[2], ts2(1, "running")),
                      Transform(sc, syscalls(0))], 0.8),
            "always take",
            (lambda: [FadeIn(order, shift=0.1 * UP)], 0.6),
        ])

        h2_rf = hold(0, 0, BLUE_M)
        w2_pm = want(1, 0, GREY_B)
        q3 = sleeper("payment", PURPLE_M, 0)
        self.steps("Now both start with ACC-1001. The refund gets it. The payment waits for it, holding nothing.", [
            (lambda: [Indicate(L[0][1], color=GREEN_M)], 0.7),
            "The refund gets it",
            (lambda: [Create(h2_rf), L[0][0].animate.set_stroke(BLUE_M), Transform(t1[2], ts2(0, "holds ACC-1001", BLUE_M))], 0.6),
            "The payment waits",
            (lambda: [Create(w2_pm), FadeIn(q3, shift=0.4 * DOWN), Transform(t2[2], ts2(1, "asleep, holds nothing", GREY_B)),
                      Transform(sc, syscalls(1))], 0.8),
        ])

        h3_rf = hold(0, 1, BLUE_M)
        h3_pm, h4_pm = hold(1, 0, PURPLE_M), hold(1, 1, PURPLE_M)
        done = note("merchant: 10,000 − 120 + 80 = 9,960", GREEN_M)
        self.steps("The refund takes the customer lock too, moves the money, and lets both go. "
                   "Then the payment runs, and the merchant ends at 9,960.", [
            (lambda: [Create(h3_rf), L[1][0].animate.set_stroke(BLUE_M)], 0.6),
            "moves the money",
            (lambda: [Transform(L[0][2], lock_sub(0, "merchant: 9,880", BLUE_M))], 0.5),
            "and lets both go",
            (lambda: [FadeOut(h2_rf), FadeOut(h3_rf), L[0][0].animate.set_stroke(WHITE), L[1][0].animate.set_stroke(WHITE),
                      Transform(t1[2], ts2(0, "done", GREEN_M)), FadeOut(q3, shift=0.4 * UP), FadeOut(w2_pm),
                      Transform(sc, syscalls(2))], 0.7),
            "Then the payment",
            (lambda: [Create(h3_pm), Create(h4_pm), L[0][0].animate.set_stroke(PURPLE_M), L[1][0].animate.set_stroke(PURPLE_M),
                      Transform(t2[2], ts2(1, "holds both", PURPLE_M))], 0.7),
            "and the merchant ends",
            (lambda: [Transform(L[0][2], lock_sub(0, "merchant: 9,960", GREEN_M)), FadeOut(h3_pm), FadeOut(h4_pm),
                      L[0][0].animate.set_stroke(WHITE), L[1][0].animate.set_stroke(WHITE),
                      Transform(t2[2], ts2(1, "done", GREEN_M)), FadeOut(order), FadeIn(done, shift=0.1 * UP)], 0.8),
        ])

        self.steps("A free lock costs one instruction, and only waiting reaches the kernel. "
                   "Take locks in one fixed order, and the waiting can never loop back.", [
            (lambda: [Indicate(sc, color=TEAL_M)], 0.9),
            "Take locks",
            (lambda: [glow(L[0][0], GREEN_M, 1.05), glow(L[1][0], GREEN_M, 1.05)], 0.9),
        ])
        self.wait(0.6)
