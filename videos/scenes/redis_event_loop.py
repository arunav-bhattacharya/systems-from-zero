from sfz import *

# The letter A naming a pod, worker or node: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bRedis\b", "reddiss"))   # RED-iss, not REE-diz


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


class RedisEventLoop(Layered):
    """redis-01: one thread runs every command, so each command is atomic, and one slow command stalls everyone."""

    def construct(self):
        self.title_card("One thread, many clients", "the Redis event loop")

        YS = (1.8, 0.0, -1.8)
        PX, WX, TX = -5.75, -3.3, 0.6          # pods, waiting commands, thread(s)

        pods = VGroup(*[box(f"pod {n}", BLUE_M, w=1.7, size=26).move_to([PX, y, 0]) for n, y in zip("ABC", YS)])
        server = RoundedRectangle(corner_radius=0.2, width=8.3, height=5.5, stroke_color=GREY_B, stroke_width=2.5)
        server.move_to([2.4, 0, 0])
        s_lab = T("Redis server", 26, GREY_B).next_to(server, UP, buff=0.18).align_to(server, LEFT).shift(0.1 * RIGHT)

        key = mbox("card:7", WHITE, w=1.75, h=0.75, size=22).move_to([3.95, 0, 0])
        val = mbox("41", WHITE, w=1.0, h=0.75, size=22).move_to([5.45, 0, 0])
        mem_lab = T("memory", 24, GREY_B).next_to(VGroup(key, val), UP, buff=0.3)

        def set_val(v, color=WHITE):
            new = M(v, 22, color).move_to(val[1])
            return Transform(val[1], new)

        def cmd(text, color=BLUE_M, y=0.0):
            return chip(text, color, 22, mono=True).move_to([WX, y, 0])

        self.beat("Three pods of a payment service share one Redis server. In its memory, Redis keeps a counter: card seven has 41 authorizations today.",
                  LaggedStart(*[FadeIn(p, shift=0.2 * RIGHT) for p in pods], lag_ratio=0.2),
                  Create(server), FadeIn(s_lab), FadeIn(mem_lab), FadeIn(key), FadeIn(val), run_time=2.8)

        # --- the obvious design: a thread per connection
        threads = VGroup(*[box(f"thread {i}", GREY_B, w=2.3, h=0.9, size=24).move_to([TX, y, 0]) for i, y in zip((1, 2, 3), YS)])
        self.beat("The obvious design gives every connection its own thread.",
                  LaggedStart(*[FadeIn(t, shift=0.2 * RIGHT) for t in threads], lag_ratio=0.25), run_time=2.0)

        ca, cb = cmd("INCR card:7", BLUE_M, YS[0]), cmd("INCR card:7", BLUE_M, YS[1])
        ra = edge_arrow(threads[0], key, YELLOW_M)
        rb = edge_arrow(threads[1], key, YELLOW_M)

        def relabel(t, s, color):
            return Transform(t[1], T(s, 24, color).move_to(t[1]))

        self.play(FadeIn(ca, shift=0.3 * RIGHT), FadeIn(cb, shift=0.3 * RIGHT), run_time=0.6)
        self.beat("Now pods A and B both add one to the counter. Both threads read 41, at the same moment.",
                  Succession(AnimationGroup(ca.animate.move_to(threads[0]).scale(0.4).set_opacity(0),
                                            cb.animate.move_to(threads[1]).scale(0.4).set_opacity(0), run_time=0.8),
                             AnimationGroup(threads[0][0].animate.set_stroke(YELLOW_M), threads[1][0].animate.set_stroke(YELLOW_M),
                                            relabel(threads[0], "reads 41", YELLOW_M), relabel(threads[1], "reads 41", YELLOW_M),
                                            GrowArrow(ra), GrowArrow(rb), run_time=1.2)), run_time=2.2)
        self.remove(ca, cb)

        lost = T("one add lost", 26, RED_M).next_to(VGroup(key, val), DOWN, buff=0.35)
        self.beat("Both add one and write back 42. Two adds, but the counter only went up by one.",
                  relabel(threads[0], "writes 42", YELLOW_M), relabel(threads[1], "writes 42", YELLOW_M),
                  Succession(Wait(0.6), AnimationGroup(set_val("42", RED_M), val[0].animate.set_stroke(RED_M), FadeIn(lost))),
                  run_time=2.2)

        lock = chip("one lock per key", RED_M, 24).move_to(lost)
        self.beat("To stop that, every key needs a lock, and every command pays for it.",
                  Succession(FadeOut(lost, run_time=0.4), FadeIn(lock, run_time=0.6)), run_time=1.2)

        # --- what Redis does: one thread
        big = RoundedRectangle(corner_radius=0.14, width=2.6, height=1.7, stroke_color=YELLOW_M, stroke_width=3)
        big.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(YELLOW_M), 0.10), opacity=1).move_to([TX, 0, 0])
        big_lab = T("one thread", 26, YELLOW_M).move_to([TX, 0.48, 0])
        one = VGroup(big, big_lab)
        SLOT = np.array([TX, -0.22, 0])
        feed = edge_arrow(big, key, GREY_B)
        self.beat("Redis does something simpler. One thread runs every command.",
                  FadeOut(threads[0]), FadeOut(threads[2]), FadeOut(ra), FadeOut(rb), FadeOut(lock),
                  ReplacementTransform(threads[1], one), set_val("41"), val[0].animate.set_stroke(WHITE),
                  run_time=1.8)
        self.play(GrowArrow(feed), run_time=0.4)

        cA, cB, cC = cmd("INCR card:7", BLUE_M, YS[0]), cmd("INCR card:7", BLUE_M, YS[1]), cmd("GET card:7", BLUE_M, YS[2])
        self.beat("The thread asks the kernel which connections have a command waiting. Then it takes them one at a time.",
                  LaggedStart(*[FadeIn(c, shift=0.3 * RIGHT) for c in (cA, cB, cC)], lag_ratio=0.3), run_time=1.8)

        def reply(text, y):
            r = chip(text, GREEN_M, 22, mono=True).move_to(SLOT)
            return r, Succession(FadeIn(r, run_time=0.2), r.animate(run_time=0.9).move_to([WX, y, 0]), FadeOut(r, run_time=0.3))

        def run(c, new_val=None):
            steps = [c.animate(run_time=0.7).move_to(SLOT)]
            if new_val:
                steps.append(AnimationGroup(flash(VGroup(key, val)), set_val(new_val, YELLOW_M), run_time=1.0))
            else:
                steps.append(AnimationGroup(flash(VGroup(key, val)), run_time=1.0))
            return steps

        r42, rep42 = reply(":42", YS[0])
        self.beat("It runs A's command to the end: read 41, add one, store 42. Only then does it look at the next one.",
                  Succession(*run(cA, "42"), FadeOut(cA, run_time=0.3), rep42), run_time=3.4)
        self.play(set_val("42"), run_time=0.3)

        r43, rep43 = reply(":43", YS[1])
        r43c, rep43c = reply("43", YS[2])
        self.beat("B's command runs next. It reads 42 and stores 43. Then C reads 43. No update is lost, and nobody needed a lock.",
                  Succession(*run(cB, "43"), FadeOut(cB, run_time=0.3), rep43,
                             *run(cC), FadeOut(cC, run_time=0.3), rep43c), run_time=5.0)
        self.play(set_val("43"), run_time=0.3)

        rule = T("one command at a time", 24, YELLOW_M).next_to(big, DOWN, buff=0.4)
        self.beat("Commands never overlap, so every command is atomic. It happens as one step, and no client ever sees it half done.",
                  FadeIn(rule, shift=0.15 * UP), flash(one), run_time=2.0)

        # --- the price: one slow command
        script = cmd("EVAL script", RED_M, YS[0])
        clock = ValueTracker(0)
        busy = counter(lambda v: f"busy for {int(round(v / 50) * 50):,} ms", clock.get_value, lambda m: m.next_to(big, DOWN, buff=0.4), 26, RED_M)
        self.play(FadeIn(script, shift=0.3 * RIGHT), run_time=0.5)
        self.beat("The same rule has a price. Pod A now sends a Lua script, a small program that Redis runs as one command. This one runs for 1.5 seconds.",
                  Succession(script.animate(run_time=0.8).move_to(SLOT),
                             AnimationGroup(big.animate.set_stroke(RED_M), big_lab.animate.set_color(RED_M),
                                            FadeOut(rule), FadeIn(busy), run_time=0.6)), run_time=2.0)

        wB = cmd("GET card:7", BLUE_M, YS[1])
        wC = cmd("GET limit:9", BLUE_M, YS[2])
        wait_lab = T("waiting", 24, RED_M).next_to(VGroup(wB, wC), UP, buff=0.0).move_to([WX, -0.9, 0])
        self.beat("Pod B asks for the counter. That takes half a microsecond of work, but the only thread is busy. B waits. So does pod C, whatever key it wants.",
                  clock.animate(rate_func=linear).set_value(1500),
                  Succession(Wait(0.6), FadeIn(wB, shift=0.3 * RIGHT), Wait(1.0), FadeIn(wC, shift=0.3 * RIGHT),
                             AnimationGroup(pods[1][0].animate.set_stroke(RED_M), pods[2][0].animate.set_stroke(RED_M), FadeIn(wait_lab))),
                  run_time=8.0)

        waited = T("waited 1.2 s", 24, RED_M).next_to(pods[1], DOWN, buff=0.22)
        busy.clear_updaters()
        self.beat("When the script ends, B finally gets its answer. It waited 1.2 seconds.",
                  Succession(AnimationGroup(FadeOut(script), FadeOut(busy), big.animate.set_stroke(YELLOW_M), big_lab.animate.set_color(YELLOW_M), run_time=0.5),
                             wB.animate(run_time=0.6).move_to(SLOT),
                             FadeOut(wB, run_time=0.3), AnimationGroup(reply("43", YS[1])[1], FadeIn(waited), pods[1][0].animate.set_stroke(BLUE_M))),
                  run_time=2.8)
        self.play(FadeOut(wC), FadeOut(wait_lab), pods[2][0].animate.set_stroke(BLUE_M), run_time=0.5)

        keys = cmd("KEYS *", RED_M, YS[0])
        big_keys = T("1 million keys to scan", 24, RED_M).next_to(big, DOWN, buff=0.4)
        self.play(FadeIn(keys, shift=0.3 * RIGHT), FadeOut(waited), run_time=0.5)
        self.beat("KEYS over a million keys does the same. Any command whose work grows with the data freezes every client.",
                  Succession(keys.animate(run_time=0.8).move_to(SLOT),
                             AnimationGroup(big.animate.set_stroke(RED_M), big_lab.animate.set_color(RED_M), FadeIn(big_keys),
                                            *[p[0].animate.set_stroke(RED_M) for p in pods[1:]], run_time=0.8)), run_time=2.4)

        rule2 = T("one command at a time", 24, YELLOW_M).next_to(big, DOWN, buff=0.4)
        self.beat("One thread, one command at a time, each run to the end. That makes every command atomic, and it means one slow command makes everyone wait.",
                  FadeOut(keys), FadeOut(big_keys), FadeIn(rule2), big.animate.set_stroke(YELLOW_M), big_lab.animate.set_color(YELLOW_M),
                  *[p[0].animate.set_stroke(BLUE_M) for p in pods[1:]], run_time=1.6)
        self.play(flash(one), run_time=1.0)
        self.wait(0.6)
