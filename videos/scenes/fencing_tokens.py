from sfz import *

# The letter A naming a pod, worker or node: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bRedis\b", "reddiss"))   # RED-iss, not REE-diz

SAY.insert(0, (r"\bNX\b", "N X"))
SAY.insert(0, (r"\bSET\b", "set"))
SAY.insert(0, (r"\bPX\b", "P X"))


def _layer(m):
    """Text above chips above arrows above boxes. Box fills are opaque, so without this an animated box
    rectangle is redrawn over its own label."""
    for x in m.get_family():
        if isinstance(x, Text):
            x.set_z_index(4)
        elif isinstance(x, Arrow):
            x.set_z_index(1)
        elif isinstance(x, RoundedRectangle) and 0 < x.get_fill_opacity() < 0.5:
            x.set_z_index(2)


def counter(fmt, value, place, size=24, color=WHITE):
    """A text that follows value() each frame; each distinct text is built once (Text is slow to build)."""
    cache = {}

    def make():
        s = fmt(value())
        if s not in cache:
            cache[s] = T(s, size, color)
        return place(cache[s].copy())
    return always_redraw(make)


def flash(m, color=YELLOW_M, buff=0.1, scale=1.05):
    """Highlight a box without filling it (Indicate turns an opaque box into a solid block):
    a quick pulse plus an outline drawn and faded around it."""
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.14, stroke_width=4)
    return AnimationGroup(m.animate(rate_func=there_and_back).scale(scale),
                          Succession(Create(r, run_time=0.5), FadeOut(r, run_time=0.5)))


class Layered(VoiceScene):
    def play(self, *anims, **kw):
        for a in anims:
            _layer(a.mobject)
            if getattr(a, "target_mobject", None) is not None:
                _layer(a.target_mobject)
        for m in self.mobjects:
            _layer(m)
        super().play(*anims, **kw)
        for m in self.mobjects:
            _layer(m)


class FencingTokens(Layered):
    """redis-08: a lock with a lease, a 35-second GC pause, two writers, and the fencing token that stops the stale one.
    Names follow the lesson: lock:settle, pod-a, the payout file and its store, tokens 33 and 34."""

    def construct(self):
        self.title_card("Distributed locks and fencing tokens", "when a lease runs out under you")

        A_C, B_C = BLUE_M, GOLD_M
        wa = box("pod A", A_C, w=2.0, size=26).move_to([-4.9, -0.3, 0])
        wb = box("pod B", B_C, w=2.0, size=26).move_to([4.9, -0.3, 0])

        led = RoundedRectangle(corner_radius=0.16, width=5.6, height=1.45, stroke_color=GREY_B, stroke_width=2.5).move_to([0, -2.3, 0])
        led.set_fill(BLACK, opacity=1).set_z_index(-1)
        led_lab = T("payout store", 26, GREY_B).next_to(led, UP, buff=0.15)
        ROW1, ROW2 = -2.02, -2.58

        self.beat("Two pods can each start the nightly settlement batch, which builds the payout file for the bank. If both run it, every merchant gets paid twice.",
                  FadeIn(wa, shift=0.2 * RIGHT), FadeIn(wb, shift=0.2 * LEFT), Create(led), FadeIn(led_lab), run_time=2.4)

        R1, R2 = 2.15, 1.25
        red = RoundedRectangle(corner_radius=0.16, width=6.2, height=1.1, stroke_color=GREY_B, stroke_width=2.5).move_to([0, R1, 0])
        red_tall = RoundedRectangle(corner_radius=0.16, width=6.2, height=2.0, stroke_color=GREY_B, stroke_width=2.5).move_to([0, (R1 + R2) / 2, 0])
        red_tall.set_fill(BLACK, opacity=1).align_to(red, UP)
        red.set_fill(BLACK, opacity=1).set_z_index(-1)
        red_tall.set_z_index(-1)
        red_lab = T("Redis", 26, GREY_B).next_to(red, UP, buff=0.12)
        KX, HX = -1.45, 0.72                       # key column, holder column
        key = mbox("lock:settle", WHITE, w=2.75, h=0.66, size=22).move_to([KX, R1, 0])
        holder = mbox("pod-a", A_C, w=1.35, h=0.66, size=22).move_to([HX, R1, 0])
        ttl = ValueTracker(30)
        ttl_t = counter(lambda v: f"{int(np.ceil(v - 1e-6))} s left", ttl.get_value, lambda m: m.move_to([2.2, R1, 0]), 24, GREY_B)

        def command(who, color):
            parts = VGroup(M(f"SET lock:settle {who}", 20), M("NX", 20), M("PX 30000", 20))
            parts.arrange(RIGHT, buff=0.22)
            r = RoundedRectangle(corner_radius=0.08, width=parts.width + 0.36, height=0.62, stroke_color=color, stroke_width=2.5)
            r.set_fill(color, opacity=0.18)
            return VGroup(r, parts.move_to(r)).move_to([0, -0.05, 0])

        cmd_a = command("pod-a", A_C)
        to_ra = edge_arrow(wa, red, A_C)
        self.beat("So they take a lock in Redis. Pod A sends a SET command with two options, NX and PX.",
                  Create(red), FadeIn(red_lab), FadeIn(key), GrowArrow(to_ra), FadeIn(cmd_a, shift=0.2 * UP), run_time=2.2)

        ok_a = tick(True, 0.22).next_to(wa, UP, buff=0.25)
        self.beat("NX means: only set the key if it doesn't exist yet. The key is free, so A gets the lock.",
                  cmd_a[1][1].animate.set_color(YELLOW_M), Succession(Wait(1.2), AnimationGroup(FadeIn(holder, scale=1.3), Create(ok_a))),
                  run_time=3.0)

        self.beat("PX sets a lease. Redis deletes the key by itself after 30 seconds, so a pod that crashes can't hold the lock forever.",
                  cmd_a[1][1].animate.set_color(WHITE), cmd_a[1][2].animate.set_color(YELLOW_M), FadeIn(ttl_t), run_time=1.6)

        cmd_b = command("pod-b", B_C)
        to_rb = edge_arrow(wb, red, B_C)
        no_b = tick(False, 0.22).next_to(wb, UP, buff=0.25)
        self.beat("Pod B sends the same command. The key already exists, so B gets nothing, and waits.",
                  FadeOut(to_ra), ReplacementTransform(cmd_a, cmd_b), GrowArrow(to_rb),
                  Succession(Wait(1.0), AnimationGroup(flash(holder, A_C), FadeIn(no_b))), run_time=2.6)

        # --- A pauses; the lease runs out
        pause = ValueTracker(0)
        pause_t = counter(lambda v: f"GC pause: {int(v)} s", pause.get_value, lambda m: m.next_to(wa, DOWN, buff=0.3), 24, RED_M)
        self.beat("Now A freezes. A 35-second garbage collection pause halts every thread in its JVM. Pod A has no idea that time is passing.",
                  FadeOut(cmd_b), FadeOut(to_rb), FadeOut(no_b), FadeOut(ok_a),
                  wa[0].animate.set_stroke(GREY_D).set_fill(BLACK), wa[1].animate.set_color(GREY_D), FadeIn(pause_t),
                  pause.animate(rate_func=linear).set_value(8), ttl.animate(rate_func=linear).set_value(22), run_time=5.0)

        self.beat("30 seconds go by. The lease runs out, and Redis deletes the key. As far as Redis knows, nobody holds the lock.",
                  Succession(AnimationGroup(pause.animate(rate_func=linear).set_value(30), ttl.animate(rate_func=linear).set_value(0), run_time=2.6),
                             AnimationGroup(FadeOut(holder), key.animate.set_opacity(0.3), run_time=0.6)), run_time=3.2)
        ttl_t.clear_updaters()
        self.play(FadeOut(ttl_t), run_time=0.3)

        holder_b = mbox("pod-b", B_C, w=1.35, h=0.66, size=22).move_to([HX, R1, 0])
        to_rb2 = edge_arrow(wb, red, B_C)
        to_lb = edge_arrow(wb, led, B_C)
        w_b = T("B writes the payout file", 24, B_C).move_to([0, ROW1, 0])
        self.beat("B asks again and gets the lock. B writes the payout file.",
                  pause.animate(rate_func=linear).set_value(35),
                  Succession(GrowArrow(to_rb2), AnimationGroup(key.animate.set_opacity(1), FadeIn(holder_b, scale=1.3)),
                             AnimationGroup(FadeOut(to_rb2), GrowArrow(to_lb)), FadeIn(w_b)), run_time=3.0)

        to_la = edge_arrow(wa, led, A_C)
        w_a = T("A writes the payout file", 24, RED_M).move_to([0, ROW2, 0])
        pause_t.clear_updaters()
        self.beat("Then A wakes up. From where A stands, nothing happened. It still thinks it holds the lock, so it writes the payout file too.",
                  Succession(AnimationGroup(FadeOut(pause_t), wa[0].animate.set_stroke(A_C).set_fill(interpolate_color(ManimColor("#000000"), ManimColor(A_C), 0.14), opacity=1), wa[1].animate.set_color(WHITE), run_time=0.8),
                             Wait(1.6), GrowArrow(to_la), FadeIn(w_a), AnimationGroup(led.animate.set_stroke(RED_M), led_lab.animate.set_color(RED_M))),
                  run_time=5.0)

        twice = T("paid twice", 26, RED_M).next_to(wa, DOWN, buff=0.3)
        self.beat("A lease can't prevent this. Checking the lock first doesn't help: the pause can strike right after the check.",
                  FadeIn(twice), Indicate(w_a, color=RED_M), run_time=1.6)

        # --- fencing tokens
        fkey = mbox("fence:settle", WHITE, w=2.75, h=0.66, size=22).move_to([KX, R2, 0])
        fval = mbox("32", TEAL_M, w=0.9, h=0.66, size=22).move_to([HX - 0.225, R2, 0])
        self.beat("The fix is a fencing token. The script that takes the lock also adds one to a counter in Redis, and hands back the new number.",
                  FadeOut(twice), FadeOut(w_a), FadeOut(w_b), FadeOut(to_la), FadeOut(to_lb), FadeOut(holder_b),
                  led.animate.set_stroke(GREY_B), led_lab.animate.set_color(GREY_B),
                  Succession(Transform(red, red_tall, run_time=0.6), AnimationGroup(FadeIn(fkey), FadeIn(fval), run_time=0.8)), run_time=2.4)

        def setv(mb, s, color):
            return Transform(mb[1], M(s, 22, color).move_to(mb[1]))

        tok_a = chip("token 33", A_C, 24).next_to(wa, UP, buff=0.3)
        tok_b = chip("token 34", B_C, 24).next_to(wb, UP, buff=0.3)
        hold = mbox("pod-a", A_C, w=1.35, h=0.66, size=22).move_to([HX, R1, 0])
        frozen = T("GC pause", 24, RED_M).next_to(wa, DOWN, buff=0.3)
        self.beat("Run it again. Pod A gets the lock with token 33, then pauses. The lease runs out, and B gets the lock with token 34.",
                  Succession(AnimationGroup(FadeIn(hold, scale=1.3), setv(fval, "33", TEAL_M), FadeIn(tok_a, shift=0.2 * DOWN), run_time=0.9),
                             AnimationGroup(wa[0].animate.set_stroke(GREY_D), wa[1].animate.set_color(GREY_D), FadeIn(frozen), run_time=0.8),
                             Wait(0.9),
                             AnimationGroup(Transform(hold, mbox("pod-b", B_C, w=1.35, h=0.66, size=22).move_to([HX, R1, 0])),
                                            setv(fval, "34", TEAL_M), FadeIn(tok_b, shift=0.2 * DOWN), run_time=0.9)),
                  run_time=6.2)

        to_lb = edge_arrow(wb, led, B_C)
        seen = T("highest token seen: 34", 24, TEAL_M).move_to([0, ROW1, 0])
        okb = T("B, token 34: accepted", 24, GREEN_M).move_to([0, ROW2, 0])
        self.beat("Every write carries its token, and the store remembers the highest token it has accepted. B writes with 34. Accepted.",
                  Succession(GrowArrow(to_lb), FadeIn(seen), Wait(0.6), FadeIn(okb)), run_time=4.6)

        to_la = edge_arrow(wa, led, A_C)
        bad = T("A, token 33: refused", 24, RED_M).move_to([0, ROW2, 0])
        self.beat("When A wakes up and writes with 33, the store sees that 33 is lower than 34, and refuses the write.",
                  Succession(AnimationGroup(FadeOut(frozen), wa[0].animate.set_stroke(A_C).set_fill(interpolate_color(ManimColor("#000000"), ManimColor(A_C), 0.14), opacity=1), wa[1].animate.set_color(WHITE), run_time=0.6),
                             GrowArrow(to_la), AnimationGroup(FadeOut(okb), FadeIn(bad)), Indicate(seen, color=TEAL_M)),
                  run_time=4.4)

        self.beat("The lock alone is not enough. The store has to check the token and refuse any write with an older one.",
                  flash(VGroup(led, seen, bad), TEAL_M, buff=0.12, scale=1.0), run_time=2.0)
        self.wait(0.6)
