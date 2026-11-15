from sfz import *

AX_Y = -2.95                                 # the timeline
RX, RY, RW, RH = 4.1, 0.75, 3.9, 2.5        # the Redis box
BX, BY, BW, BH = -1.7, 0.55, 1.7, 2.5       # the bucket
JX, JY = -5.3, 0.55                          # the client on the left
CAP = 10


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along an arrow (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def x1(t):
    """Fixed-window timeline: t in seconds of the clock, 58.5 to 61.0."""
    return -6.0 + (t - 58.5) * 4.8


def x2(t):
    """Token-bucket timeline: t in seconds since the burst, 0 to 5."""
    return -5.6 + t * 2.24


def rline(s, k, color=GREY_B, mono=False, size=20):
    """Line k inside the Redis box (0 is the key, 1 and 2 the fields, 3 the status)."""
    y = [RY + 0.35, RY - 0.15, RY - 0.6][k - 1] if k else RY + 0.35
    return (M if mono else T)(s, size, color).move_to([RX, y, 0])


def token_xy(i):
    col, row = i % 2, i // 2
    return [BX + (-0.36 if col == 0 else 0.36), BY - BH / 2 + 0.33 + row * 0.44, 0]


def token(i):
    return Dot(radius=0.16, color=GOLD_M).move_to(token_xy(i))


def mark(t, ok, y=AX_Y + 0.22):
    return Dot(radius=0.07, color=GREEN_M if ok else RED_M).move_to([x2(t), y, 0])


class TokenBucket(Base):
    """cache-08, section 2 (with section 1's seam): a fixed window of 5 a minute lets 10 attempts through in 1.4 s at
    the minute boundary. A token bucket of 10, one token per 500 ms: a burst of 15 gets 10, then one request every
    250 ms gets every other one, 2 a second. The state is one hash (tokens, ts) changed by one Lua script, so two
    pods can't both take the last token; its TTL is the time to refill from empty."""

    def construct(self):
        self.title_card("Rate limits: the token bucket", "a burst up front, then a steady rate")

        # ---- the fixed window and its seam -------------------------------------------------------------------
        rule = chip("at most 5 attempts per card per minute", GREY_B, 20).move_to([2.4, 3.2, 0])
        card = box("card 7", WHITE, w=2.0, h=0.9, size=24).move_to([JX, JY, 0])
        rr = RoundedRectangle(corner_radius=0.14, width=RW, height=RH, stroke_color=BLUE_M, stroke_width=3)
        rr.set_fill(fill(BLUE_M), 1).move_to([RX, RY, 0])
        rt = T("Redis", 24).move_to([RX, RY + RH / 2 - 0.36, 0])
        rk = M("rl:card:7", 20, WHITE).move_to([RX, RY + 0.3, 0])
        rv = T("count: 0 of 5", 22, GREY_B).move_to([RX, RY - 0.25, 0])
        rs = T("minute 0", 19, GOLD_M).move_to([RX, RY - 0.75, 0])
        inc = Arrow([JX + 1.1, JY, 0], [RX - RW / 2 - 0.1, JY, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.05)
        inc_l = M("INCR rl:card:7", 17, GREY_B).next_to(inc, UP, buff=0.14).shift(0.6 * LEFT)

        axis = Line([-6.3, AX_Y, 0], [6.3, AX_Y, 0], stroke_width=2.5, color=GREY_B)
        bnd = DashedLine([x1(60), AX_Y - 0.15, 0], [x1(60), AX_Y + 1.25, 0], dash_length=0.08, stroke_width=2.5, color=WHITE)
        band0 = Rectangle(width=x1(60) - x1(58.5), height=1.25, stroke_width=0).set_fill(GOLD_M, 0.14)
        band0.move_to([(x1(58.5) + x1(60)) / 2, AX_Y + 0.65, 0])
        band1 = Rectangle(width=x1(61) - x1(60), height=1.25, stroke_width=0).set_fill(BLUE_M, 0.14)
        band1.move_to([(x1(60) + x1(61)) / 2, AX_Y + 0.65, 0])
        bl0 = T("minute 0", 19, GOLD_M).move_to([x1(58.5) + 0.75, AX_Y + 1.05, 0])
        bl1 = T("minute 1", 19, BLUE_M).move_to([x1(61) - 0.75, AX_Y + 1.05, 0])
        tl = VGroup(*[T(s, 18, GREY_B).move_to([x1(v), AX_Y - 0.36, 0]) for s, v in (("0:59", 59), ("1:00", 60), ("1:01", 61))])
        tt = VGroup(*[Line([x1(v), AX_Y - 0.08, 0], [x1(v), AX_Y + 0.08, 0], stroke_width=2, color=GREY_B) for v in (59, 60, 61)])

        self.steps("A fraud rule allows five attempts per card per minute. Every pod adds one to the same Redis key, "
                   "and the count starts over each minute.", [
            (lambda: [FadeIn(rule, shift=0.1 * DOWN)], 0.7),
            (lambda: [FadeIn(card)], 0.5),
            "Every pod",
            (lambda: [FadeIn(rr), FadeIn(rt), FadeIn(rk), FadeIn(rv), GrowArrow(inc), FadeIn(inc_l)], 0.9),
            "and the count",
            (lambda: [Create(axis), FadeIn(tt), FadeIn(tl), FadeIn(band0), FadeIn(band1), Create(bnd),
                      FadeIn(bl0), FadeIn(bl1), FadeIn(rs)], 1.1),
        ])

        m0 = [Dot(radius=0.08, color=GREEN_M).move_to([x1(59 + 0.1 * i), AX_Y + 0.3, 0]) for i in range(5)]
        m1 = [Dot(radius=0.08, color=GREEN_M).move_to([x1(60 + 0.1 * i), AX_Y + 0.3, 0]) for i in range(5)]

        def admit(dots, k, minute):
            def f():
                return [FadeIn(dots[k], scale=0.5), flow(inc, GREEN_M, 0.4),
                        Transform(rv, T(f"count: {k + 1} of 5", 22, GREEN_M if k < 4 else GOLD_M).move_to(rv))]
            return f

        self.steps("That's a fixed window. Five attempts land in the last second of minute zero, and fill it.", [
            "Five attempts",
            *[(admit(m0, k, 0), 0.42) for k in range(5)],
            (lambda: [Indicate(rv, color=GOLD_M, scale_factor=1.1)], 0.6),
        ])

        self.steps("At the boundary the count resets, and minute one lets five more attempts in.", [
            (lambda: [Transform(rv, T("count: 0 of 5", 22, GREY_B).move_to(rv)),
                      Transform(rs, T("minute 1", 19, BLUE_M).move_to(rs)), glow(bnd, YELLOW_M, 1.0)], 0.8),
            "five more",
            *[(admit(m1, k, 1), 0.38) for k in range(5)],
        ])

        br = Brace(VGroup(*m0, *m1), UP, buff=1.0, color=RED_M)
        brl = T("10 attempts in 1.4 seconds", 21, RED_M).next_to(br, UP, buff=0.12)
        self.steps("The rule said five a minute. The card got ten in 1.4 seconds.", [
            "The card got",
            (lambda: [GrowFromCenter(br), FadeIn(brl, shift=0.1 * UP), *[d.animate.set_color(RED_M) for d in m0 + m1]], 1.0),
            (lambda: [glow(rr, RED_M, 1.03)], 0.8),
        ])

        # ---- the token bucket --------------------------------------------------------------------------------
        want = chip("a burst of up to 10, then 2 a second", GREEN_M, 20).move_to([2.6, 3.2, 0])
        job = box("refund job", WHITE, w=2.0, h=0.9, size=24).move_to([JX, JY, 0])
        self.steps("Some clients burst on purpose. A merchant's refund job sends forty requests at once, every hour. "
                   "You want a burst of up to ten, then two a second.", [
            (lambda: [FadeOut(br), FadeOut(brl), *[FadeOut(d) for d in m0 + m1], FadeOut(band0), FadeOut(band1),
                      FadeOut(bnd), FadeOut(bl0), FadeOut(bl1), FadeOut(inc), FadeOut(inc_l), FadeOut(rv), FadeOut(rs),
                      FadeOut(rk)], 0.8),
            "A merchant's",
            (lambda: [Transform(card, job), FadeOut(rule)], 0.7),
            "You want",
            (lambda: [FadeIn(want, shift=0.1 * DOWN)], 0.7),
        ])

        rk2 = M("bucket:m-17", 20, WHITE).move_to([RX, RY + 0.45, 0])
        bucket = VMobject(stroke_color=WHITE, stroke_width=4).set_points_as_corners(
            [[BX - BW / 2, BY + BH / 2, 0], [BX - BW / 2, BY - BH / 2, 0], [BX + BW / 2, BY - BH / 2, 0], [BX + BW / 2, BY + BH / 2, 0]])
        toks = [token(i) for i in range(CAP)]
        cap_l = T("holds at most 10", 19, GREY_B).move_to([BX, BY - BH / 2 - 0.33, 0])
        drip = Arrow([BX, BY + BH / 2 + 0.95, 0], [BX, BY + BH / 2 + 0.12, 0], buff=0, stroke_width=3, color=GOLD_M,
                     max_tip_length_to_length_ratio=0.2)
        drip_l = T("+1 token every 500 ms", 19, GOLD_M).next_to(drip, LEFT, buff=0.2).shift(0.25 * UP)
        self.steps("A token bucket does that. The bucket holds at most ten tokens, and gains one every 500 milliseconds.", [
            (lambda: [Create(bucket), FadeIn(rk2)], 0.7),
            "holds at most",
            (lambda: [LaggedStart(*[FadeIn(t, scale=0.5) for t in toks], lag_ratio=0.12), FadeIn(cap_l)], 1.2),
            "and gains",
            (lambda: [GrowArrow(drip), FadeIn(drip_l)], 0.8),
        ])

        req = Arrow([JX + 1.1, BY, 0], [BX - BW / 2 - 0.15, BY, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.12)
        ok_c = T("allowed: 0", 22, GREEN_M).move_to([0.45, 1.05, 0])
        no_c = T("refused: 0", 22, RED_M).move_to([0.45, 0.45, 0])
        burst = [mark(0, k < CAP, AX_Y + 0.22 + 0.105 * k) for k in range(15)]
        burst_l = T("burst of 15", 18, GREY_B).move_to([x2(0) + 1.05, AX_Y + 1.55, 0])
        ticks2 = VGroup(*[Line([x2(v), AX_Y - 0.08, 0], [x2(v), AX_Y + 0.08, 0], stroke_width=2, color=GREY_B) for v in range(6)])
        tl2 = VGroup(*[T(f"{v} s", 18, GREY_B).move_to([x2(v), AX_Y - 0.36, 0]) for v in range(6)])

        def take(k):
            def f():
                return [flow(req, GREEN_M, 0.3), FadeOut(toks[CAP - 1 - k], shift=0.5 * RIGHT),
                        Transform(ok_c, T(f"allowed: {k + 1}", 22, GREEN_M).move_to(ok_c)), FadeIn(burst[k], scale=0.5)]
            return f

        def refuse(k):
            def f():
                return [flow(req, RED_M, 0.3), Transform(no_c, T(f"refused: {k + 1}", 22, RED_M).move_to(no_c)),
                        FadeIn(burst[CAP + k], scale=0.5)]
            return f

        self.steps("Each request takes a token. A burst of fifteen arrives. "
                   "The first ten take every token, and the last five find the bucket empty and are refused.", [
            (lambda: [GrowArrow(req), FadeIn(ok_c), FadeIn(no_c), FadeOut(tt), FadeOut(tl), FadeIn(ticks2), FadeIn(tl2)], 0.8),
            "The first ten",
            *[(take(k), 0.32) for k in range(CAP)],
            (lambda: [FadeIn(burst_l)], 0.3),
            "and the last five",
            *[(refuse(k), 0.3) for k in range(5)],
            (lambda: [glow(bucket, RED_M, 1.02)], 0.6),
        ])

        # steady phase: a request every 250 ms; a token lands every 500 ms
        steady = [mark(0.25 * (k + 1), k % 2 == 1) for k in range(20)]
        stats = {"ok": CAP, "no": 5}

        def drop():
            t = token(0)
            t.move_to([BX, BY + BH / 2 + 0.55, 0])
            return t

        def quarter(k, rt_tok=0.35):
            def f():
                anims = [FadeIn(steady[k], scale=0.5)]
                if k % 2 == 1:
                    stats["ok"] += 1
                    t = drop()
                    self.add(t)
                    anims += [Succession(t.animate(run_time=rt_tok).move_to(token_xy(0)),
                                         t.animate(run_time=rt_tok).shift(0.5 * RIGHT).set_opacity(0)),
                              flow(req, GREEN_M, 2 * rt_tok),
                              Transform(ok_c, T(f"allowed: {stats['ok']}", 22, GREEN_M).move_to(ok_c))]
                else:
                    stats["no"] += 1
                    anims += [flow(req, RED_M, 0.5), Transform(no_c, T(f"refused: {stats['no']}", 22, RED_M).move_to(no_c))]
                return anims
            return f

        rate = chip("2 a second", GREEN_M, 20).move_to([x2(3.6), AX_Y + 1.0, 0])
        self.steps("Now one request comes every 250 milliseconds. A token arrives every 500, "
                   "so every other request gets through. That's two a second.", [
            (quarter(0), 0.6), (quarter(1), 0.8), (quarter(2), 0.6), (quarter(3), 0.8),
            "so every other",
            *[(quarter(k, 0.11), 0.22) for k in range(4, 20)],
            "That's two",
            (lambda: [FadeIn(rate, shift=0.1 * UP)], 0.6),
        ])

        refill = [token(i) for i in range(CAP)]

        # ---- the state in Redis ------------------------------------------------------------------------------
        f1 = M("tokens   0", 20, GOLD_M).move_to([RX, RY + 0.0, 0])
        f2 = M("ts       5000", 20, GREY_A).move_to([RX, RY - 0.42, 0])
        hint = T("a hash with two fields", 18, GREY_B).move_to([RX, RY - RH / 2 - 0.35, 0])
        self.steps("Nothing drips tokens in. Redis keeps two numbers per merchant, in one hash: "
                   "the tokens left after the last request, and ts, when it last refilled.", [
            (lambda: [FadeOut(rate), FadeOut(burst_l), *[FadeOut(d) for d in burst + steady],
                      FadeOut(drip), FadeOut(drip_l)], 0.9),
            "Redis keeps",
            (lambda: [FadeIn(hint), glow(rr, BLUE_M, 1.03)], 0.8),
            "the tokens left",
            (lambda: [FadeIn(f1)], 0.6),
            "and ts",
            (lambda: [FadeIn(f2)], 0.6),
        ])

        calc = VGroup(T("a request at 6,200 ms:", 19, GREY_B),
                      T("1,200 ms since ts = 2 whole tokens", 19, WHITE),
                      T("ts moves on to 6,000", 19, GREY_B)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        calc.move_to([RX - 0.2, -1.55, 0])
        self.steps("On each request, a script counts the whole 500 millisecond steps since ts, adds that many tokens, "
                   "never more than ten, and takes one.", [
            (lambda: [FadeOut(hint), FadeOut(ok_c), FadeOut(no_c)], 0.6),
            "a script counts",
            (lambda: [FadeIn(calc[0]), FadeIn(calc[1])], 0.8),
            "adds that many",
            (lambda: [Transform(f1, M("tokens   2", 20, GOLD_M).move_to(f1)), FadeIn(calc[2]),
                      Transform(f2, M("ts       6000", 20, GREY_A).move_to(f2)),
                      FadeIn(refill[0], shift=0.3 * DOWN), FadeIn(refill[1], shift=0.3 * DOWN)], 0.8),
            "and takes one",
            (lambda: [Transform(f1, M("tokens   1", 20, GOLD_M).move_to(f1)), FadeOut(refill[1], shift=0.5 * RIGHT),
                      flow(req, GREEN_M, 0.5)], 0.8),
        ])

        # ---- two pods, one token -----------------------------------------------------------------------------
        pa = box("pod A", WHITE, w=1.7, h=0.75, size=22).move_to([RX - 1.15, -1.75, 0])
        pb = box("pod B", WHITE, w=1.7, h=0.75, size=22).move_to([RX + 1.15, -1.75, 0])
        aa = Arrow(pa.get_top() + 0.05 * UP, [pa.get_x(), RY - RH / 2 - 0.05, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.2)
        ab = Arrow(pb.get_top() + 0.05 * UP, [pb.get_x(), RY - RH / 2 - 0.05, 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.2)
        ra = T("reads 1, takes it", 18, RED_M).next_to(pa, DOWN, buff=0.2)
        rb = T("reads 1, takes it", 18, RED_M).next_to(pb, DOWN, buff=0.2)
        twice = T("one token, two requests in", 20, RED_M).move_to([RX, -3.2, 0])
        self.steps("Two pods ask at once, with one token left. "
                   "If each one reads and then writes, both see one token, and both take it.", [
            (lambda: [FadeOut(calc), FadeOut(axis), FadeOut(ticks2), FadeOut(tl2), FadeIn(pa), FadeIn(pb),
                      GrowArrow(aa), GrowArrow(ab)], 0.9),
            "both see one",
            (lambda: [flow(aa, GOLD_M, 0.6, back=True), flow(ab, GOLD_M, 0.6, back=True), FadeIn(ra), FadeIn(rb)], 0.8),
            "and both take it",
            (lambda: [flow(aa, RED_M, 0.6), flow(ab, RED_M, 0.6),
                      Transform(f1, M("tokens   0", 20, RED_M).move_to(f1)), FadeIn(twice)], 0.8),
        ])

        ra2 = T("script: 1 left, takes it", 18, GREEN_M).next_to(pa, DOWN, buff=0.2)
        rb2 = T("script: 0 left, refused", 18, RED_M).next_to(pb, DOWN, buff=0.2)
        self.steps("Redis runs the whole script as one command. Pod A's runs first and takes the token. "
                   "Pod B's sees zero, and refuses.", [
            (lambda: [FadeOut(ra), FadeOut(rb), FadeOut(twice), Transform(f1, M("tokens   1", 20, GOLD_M).move_to(f1))], 0.7),
            "Pod A's",
            (lambda: [flow(aa, GOLD_M, 0.6), glow(rr, GREEN_M, 1.03)], 0.7),
            (lambda: [Transform(f1, M("tokens   0", 20, GOLD_M).move_to(f1)), FadeOut(refill[0], shift=0.5 * RIGHT),
                      FadeIn(ra2), flow(aa, GREEN_M, 0.5, back=True)], 0.7),
            "Pod B's",
            (lambda: [flow(ab, GOLD_M, 0.6)], 0.6),
            (lambda: [FadeIn(rb2), flow(ab, RED_M, 0.5, back=True)], 0.6),
        ])

        ttl = M("TTL      5 s", 20, TEAL_M).move_to([RX, RY - 0.84, 0])
        back10 = [token(i) for i in range(CAP)]
        gone = T("expired: same as a full bucket", 18, TEAL_M).move_to([RX, RY - RH / 2 - 0.35, 0])
        self.steps("The key's time to live is five seconds, the time to refill from empty. "
                   "A bucket quiet that long is full anyway, so Redis can drop the key.", [
            (lambda: [FadeOut(ra2), FadeOut(rb2), FadeOut(aa), FadeOut(ab), FadeOut(pa), FadeOut(pb)], 0.6),
            (lambda: [FadeIn(ttl)], 0.6),
            "A bucket quiet",
            (lambda: [LaggedStart(*[FadeIn(t, shift=0.4 * DOWN) for t in back10], lag_ratio=0.3)], 2.0),
            "so Redis can",
            (lambda: [rk2.animate.set_opacity(0.3), f1.animate.set_opacity(0.3), f2.animate.set_opacity(0.3),
                      ttl.animate.set_opacity(0.3), FadeIn(gone)], 0.8),
        ])

        self.steps("A token bucket lets a quiet client spend a burst, then holds it to the refill rate. "
                   "One script on one key keeps every pod on the same count.", [
            (lambda: [glow(bucket, GOLD_M, 1.02)], 0.9),
            "then holds it",
            (lambda: [glow(want[0], GREEN_M, 1.04)], 0.9),
            "One script",
            (lambda: [glow(rr, GREEN_M, 1.03)], 1.0),
        ])
        self.wait(0.6)
