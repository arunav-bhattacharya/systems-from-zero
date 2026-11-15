from sfz import *

SAY.insert(0, (r"\bbalance:7\b", "balance 7"))
SAY.insert(0, (r"\bMULTI\b", "multi"))
SAY.insert(0, (r"\bEXEC\b", "exec"))
SAY.insert(0, (r"\bWATCH\b", "watch"))
# "pod A" alone reads as "pod uh"; "eh" lands on the letter.
SAY.insert(0, (r"\b[Pp]od A\b", "pod eh"))

PA, PB = np.array([-5.0, 2.1, 0]), np.array([-5.0, 0.3, 0])     # the two pods
NOTE_X = -3.6                                                    # each pod's own reasoning, right of it
RX, RY, RW, RH = 4.1, 1.25, 3.8, 2.4                               # Redis and the balance
TY, TLY = -1.85, -2.25                                             # command blocks on the thread, and its line
WHO = {"A": BLUE_M, "B": GOLD_M}


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def slot_x(i):
    return -5.4 + i * 1.68


def cmd(label, who, i, w=1.5, queued=False):
    """A command on the Redis thread, in slot i, coloured by the pod that sent it."""
    c = WHO[who]
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.66, stroke_color=c, stroke_width=2.5)
    r.set_fill(fill(c, 0.25), 1)
    if queued:
        r = DashedVMobject(r, num_dashes=24).set_stroke(c, 2.5)
    x = slot_x(i) + (w - 1.5) / 2
    return VGroup(r.move_to([x, TY, 0]), M(label, 19, WHITE).move_to([x, TY, 0]))


def reply(s, i, color=GREY_B, w=1.5):
    return M(s, 18, color).move_to([slot_x(i) + (w - 1.5) / 2, TY - 0.8, 0])


def note(s, pod, color=GREY_B):
    y = PA[1] if pod == "A" else PB[1]
    return left_at(T(s, 22, color), NOTE_X, y)


class WatchMulti(Base):
    """txn-06, sections 1 to 3: balance:7 holds 100; pod A (30, coffee) and pod B (50, fuel) both GET 100, A writes 70,
    B writes 50: paid 80, shows 50. MULTI/EXEC runs a batch as one step but can't decide. WATCH, GET 100, decide, B's
    write lands, MULTI SET 70 EXEC answers nil; A retries from 50 and writes 20. A Lua script does the read, test and
    write as one command."""

    def construct(self):
        self.title_card("Redis transactions: WATCH, MULTI and Lua", "a read, a decision and a write, with nothing in between")

        rr = RoundedRectangle(corner_radius=0.14, width=RW, height=RH, stroke_color=RED_M, stroke_width=3)
        rr.set_fill(fill(RED_M), 1).move_to([RX, RY, 0])
        rt = T("Redis", 24, GREY_B).move_to([RX, RY + RH / 2 - 0.35, 0])
        rk = M("balance:7", 24, WHITE).move_to([RX, RY + 0.35, 0])
        val = T("100", 52, WHITE).move_to([RX, RY - 0.45, 0])
        line = Line([-6.1, TLY, 0], [6.1, TLY, 0], stroke_width=2, color=GREY_C)
        tlab = left_at(T("the one Redis thread runs commands in this order", 20, GREY_B), -6.1, TY + 0.72)
        self.steps("Redis runs one command at a time, on one thread. A prepaid card, balance:7, holds 100 euros.", [
            (lambda: [FadeIn(rr), FadeIn(rt)], 0.6),
            (lambda: [Create(line), FadeIn(tlab)], 0.8),
            "A prepaid card",
            (lambda: [FadeIn(rk), FadeIn(val, scale=0.8)], 0.8),
        ])

        pa = VGroup(box("pod A", BLUE_M, w=2.3, h=0.9, size=26).move_to(PA))
        pb = VGroup(box("pod B", GOLD_M, w=2.3, h=0.9, size=26).move_to(PB))
        na = note("coffee: 30 euros", "A", BLUE_M)
        nb = note("fuel: 50 euros", "B", GOLD_M)
        g1 = cmd("GET", "A", 0)
        g2 = cmd("GET", "B", 1)
        r1, r2 = reply("100", 0), reply("100", 1)
        self.steps("Two pods authorize it at once: 30 euros for coffee, 50 for fuel. "
                   "Each one reads the balance, and both see 100.", [
            (lambda: [FadeIn(pa), FadeIn(pb)], 0.6),
            "30 euros",
            (lambda: [FadeIn(na), FadeIn(nb)], 0.7),
            "Each one reads",
            (lambda: [FadeIn(g1, target_position=PA)], 0.6),
            (lambda: [FadeIn(g2, target_position=PB)], 0.6),
            "and both see",
            (lambda: [FadeIn(r1), FadeIn(r2), Transform(na, note("read 100: 100 minus 30 is 70", "A", BLUE_M)),
                      Transform(nb, note("read 100: 100 minus 50 is 50", "B", GOLD_M))], 0.8),
        ])

        s1 = cmd("SET 70", "A", 2)
        s2 = cmd("SET 50", "B", 3)
        bad = chip("paid 80 euros, balance says 50", RED_M, 19).move_to([RX, -0.5, 0])
        self.steps("Pod A writes 70, then pod B writes 50. The card paid 80 euros, and the balance says 50.", [
            (lambda: [FadeIn(s1, target_position=PA)], 0.6),
            (lambda: [Transform(val, T("70", 52, WHITE).move_to(val))], 0.5),
            "then pod B",
            (lambda: [FadeIn(s2, target_position=PB)], 0.6),
            (lambda: [Transform(val, T("50", 52, RED_M).move_to(val))], 0.5),
            "The card paid",
            (lambda: [FadeIn(bad, shift=0.1 * UP), glow(rr, RED_M, 1.03)], 0.8),
        ])

        gap = SurroundingRectangle(VGroup(g2, s1, s2), buff=0.08, color=RED_M, corner_radius=0.08, stroke_width=3)
        gl = T("between pod B's read and its write, pod A wrote", 20, RED_M).move_to([slot_x(2), TY + 0.72, 0])
        self.steps("Each command ran alone, but between two commands the thread serves everyone else, "
                   "and that's where the other write landed.", [
            (lambda: [*[glow(c[0], WHITE, 1.06) for c in (g1, g2, s1, s2)]], 0.9),
            "between two commands",
            (lambda: [Create(gap), FadeOut(tlab), FadeIn(gl)], 0.8),
            "and that's where",
            (lambda: [glow(s1[0], RED_M, 1.12)], 0.9),
        ])

        old = VGroup(g1, g2, s1, s2, r1, r2, gap, gl)
        batch = VGroup(cmd("MULTI", "A", 0), cmd("SET 70", "A", 1, queued=True), cmd("EXEC", "A", 2))
        qb = VGroup(reply("OK", 0), reply("QUEUED", 1), reply("runs it", 2, GREEN_M))
        nodec = chip("but a GET inside answers QUEUED: too late to decide", GREY_B, 19).move_to([1.4, -0.5, 0])
        self.steps("MULTI and EXEC send a batch that runs as one step. "
                   "But a batch can't read a value and decide, so WATCH adds a check.", [
            (lambda: [FadeOut(old), FadeOut(bad), FadeIn(tlab), Transform(val, T("100", 52, WHITE).move_to(val)),
                      Transform(na, note("coffee: 30 euros", "A", BLUE_M)), Transform(nb, note("fuel: 50 euros", "B", GOLD_M))], 0.8),
            (lambda: [LaggedStart(*[FadeIn(b, target_position=PA) for b in batch], lag_ratio=0.35)], 1.2),
            (lambda: [FadeIn(qb)], 0.5),
            "But a batch",
            (lambda: [FadeIn(nodec, shift=0.1 * UP)], 0.7),
        ])

        w1 = cmd("WATCH", "A", 0)
        g3 = cmd("GET", "A", 1)
        wr, gr = reply("OK", 0), reply("100", 1)
        eye = T("watched by pod A", 20, BLUE_M).move_to([RX, RY - RH / 2 - 0.32, 0])
        self.steps("Pod A watches the balance, reads 100, and decides in its own code that 30 fits.", [
            (lambda: [FadeOut(batch), FadeOut(qb), FadeOut(nodec)], 0.5),
            (lambda: [FadeIn(w1, target_position=PA)], 0.6),
            (lambda: [FadeIn(wr), FadeIn(eye), rr.animate.set_stroke(BLUE_M)], 0.6),
            "reads 100",
            (lambda: [FadeIn(g3, target_position=PA), FadeIn(gr)], 0.6),
            "and decides",
            (lambda: [Transform(na, note("read 100: 30 fits, new balance 70", "A", BLUE_M))], 0.8),
        ])

        sb = cmd("SET 50", "B", 2)
        m1 = cmd("MULTI", "A", 3)
        q1 = cmd("SET 70", "A", 4, queued=True)
        e1 = cmd("EXEC", "A", 5)
        sbr, m1r, q1r = reply("OK", 2), reply("OK", 3), reply("QUEUED", 4)
        chg = T("changed since WATCH", 20, RED_M).move_to(eye)
        self.steps("Meanwhile pod B's payment writes 50. Pod A queues its new balance, 70, and sends EXEC.", [
            (lambda: [FadeIn(sb, target_position=PB)], 0.6),
            (lambda: [FadeIn(sbr), Transform(val, T("50", 52, WHITE).move_to(val)), Transform(eye, chg)], 0.7),
            "Pod A queues",
            (lambda: [FadeIn(m1, target_position=PA), FadeIn(m1r)], 0.5),
            (lambda: [FadeIn(q1, target_position=PA), FadeIn(q1r)], 0.5),
            "and sends EXEC",
            (lambda: [FadeIn(e1, target_position=PA)], 0.6),
        ])

        e1r = reply("nil", 5, RED_M)
        xq = tick(False, 0.2).move_to(q1)
        self.steps("The watched key changed after WATCH, so EXEC runs nothing and answers nil.", [
            (lambda: [glow(e1[0], RED_M, 1.1), Indicate(eye, color=RED_M, scale_factor=1.06)], 0.8),
            "so EXEC runs nothing",
            (lambda: [Create(xq), q1[0].animate.set_stroke(RED_M), FadeIn(e1r)], 0.7),
            (lambda: [Transform(na, note("EXEC answered nil: start over", "A", RED_M))], 0.7),
        ])

        retry = [cmd("WATCH", "A", 0), cmd("GET", "A", 1), cmd("MULTI", "A", 2), cmd("SET 20", "A", 3, queued=True), cmd("EXEC", "A", 4)]
        rre = [reply("OK", 0), reply("50", 1), reply("OK", 2), reply("QUEUED", 3), reply("OK", 4, GREEN_M)]
        good = chip("paid 80 euros, balance 20", GREEN_M, 19).move_to([RX, -0.5, 0])
        self.steps("Pod A starts over: it watches, reads 50, and writes 20. This time EXEC runs. Both payments count.", [
            (lambda: [FadeOut(VGroup(w1, g3, wr, gr, sb, m1, q1, e1, sbr, m1r, q1r, e1r, xq)),
                      Transform(eye, T("watched by pod A", 20, BLUE_M).move_to(eye))], 0.6),
            (lambda: [LaggedStart(*[FadeIn(c, target_position=PA) for c in retry[:2]], lag_ratio=0.5), FadeIn(rre[0]), FadeIn(rre[1])], 0.9),
            "and writes 20",
            (lambda: [Transform(na, note("read 50: 30 fits, new balance 20", "A", BLUE_M)),
                      LaggedStart(*[FadeIn(c, target_position=PA) for c in retry[2:]], lag_ratio=0.4), FadeIn(rre[2]), FadeIn(rre[3])], 1.1),
            "This time",
            (lambda: [Transform(retry[3], cmd("SET 20", "A", 3)), FadeIn(rre[4]), Transform(val, T("20", 52, GREEN_M).move_to(val))], 0.8),
            "Both payments",
            (lambda: [FadeIn(good, shift=0.1 * UP), FadeOut(eye), rr.animate.set_stroke(GREEN_M)], 0.7),
        ])

        ev_a = cmd("EVAL: read, test, write", "A", 0, w=4.2)
        ev_b = cmd("EVAL: read, test, write", "B", 2.6, w=4.2)
        ra, rb = reply("1: 70 left", 0, w=4.2), reply("1: 20 left", 2.6, w=4.2)
        one = chip("one command: nothing can run in between", GREEN_M, 18).move_to([RX - 0.6, -0.5, 0])
        self.steps("A Lua script removes the retry. Its read, test and write run as one command, "
                   "so nothing can land in between.", [
            (lambda: [FadeOut(VGroup(*retry, *rre)), FadeOut(good), Transform(val, T("100", 52, WHITE).move_to(val)),
                      rr.animate.set_stroke(RED_M), Transform(na, note("coffee: 30 euros", "A", BLUE_M))], 0.8),
            "Its read",
            (lambda: [FadeIn(ev_a, target_position=PA)], 0.7),
            (lambda: [FadeIn(ra), Transform(val, T("70", 52, WHITE).move_to(val))], 0.5),
            (lambda: [FadeIn(ev_b, target_position=PB)], 0.7),
            (lambda: [FadeIn(rb), Transform(val, T("20", 52, GREEN_M).move_to(val))], 0.5),
            "so nothing",
            (lambda: [FadeIn(one, shift=0.1 * UP)], 0.6),
        ])

        self.steps("One command runs alone. Send the decision as one script, or WATCH the key and retry when EXEC fails.", [
            (lambda: [glow(ev_a[0], BLUE_M, 1.04), glow(ev_b[0], GOLD_M, 1.04)], 0.9),
            "or WATCH",
            (lambda: [glow(rr, GREEN_M, 1.03)], 0.9),
        ])
        self.wait(0.6)
