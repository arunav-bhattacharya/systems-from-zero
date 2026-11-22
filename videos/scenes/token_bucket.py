from sfz import *

SAY.insert(0, (r"\bGCRA\b", "G C R A"))
SAY.insert(0, (r"\bts\b", "T S"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CL_X0, CL_X1, CL_TOP, CL_BOT = -6.5, -4.1, 1.7, -0.7        # the client: the shop's refund program
CL_CX = (CL_X0 + CL_X1) / 2
JAR_C, JAR_W, JAR_H = np.array([-1.25, 0.45, 0]), 2.5, 3.1    # the jar of tokens
JAR_X0, JAR_X1 = JAR_C[0] - JAR_W / 2, JAR_C[0] + JAR_W / 2
JAR_TOP, JAR_BOT = JAR_C[1] + JAR_H / 2, JAR_C[1] - JAR_H / 2
SV_X0, SV_X1, SV_TOP, SV_BOT = 1.5, 6.5, 2.5, -1.4          # the payments service and the tally
SV_CX = (SV_X0 + SV_X1) / 2
REQ_Y = 0.5
STATE_Y, BAR_Y, CAP_Y, CLOCK_Y = -2.1, -2.7, -3.27, 3.25


def tok_pos(k):
    c, r = k % 2, k // 2
    return np.array([JAR_C[0] - 0.5 + 1.0 * c, JAR_BOT + 0.45 + 0.55 * r, 0])


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
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


def frame(x0, x1, top, bot, color, r=0.14):
    return RoundedRectangle(corner_radius=r, width=x1 - x0, height=top - bot, stroke_color=color,
                            stroke_width=3).set_fill(fillc(color), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


def harrow(x0, x1, y, color=GREY_B):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.15)


def run_pts(pts, color=YELLOW_M, rt=0.7, r=0.07):
    """A message dot running along a polyline, visible only while it runs."""
    pts = [np.array(p, dtype=float) for p in pts]
    d = Dot(radius=r, color=color).move_to(pts[0]).set_z_index(8)
    path = VMobject().set_points_as_corners(pts)
    return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.5, height=3.9, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.45, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 2.08)
    rows = VGroup()
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * M("x" * 40, 14).width / 40
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 3.0 + ind, 1.55 - 0.4 * k))
    return VGroup(r, head, rows).set_z_index(10)




JAVA = ["boolean take(String merchant, long nowMillis) {",
        "    Object r = redis.eval(TOKEN_BUCKET,",
        "        List.of(\"bucket:\" + merchant),",
        "        List.of(\"10\", \"500\",",
        "            String.valueOf(nowMillis)));",
        "    return Long.valueOf(1).equals(r);",
        "}"]
KOTLIN = ["fun take(merchant: String,",
          "         nowMillis: Long): Boolean =",
          "    redis.eval(TOKEN_BUCKET,",
          "        listOf(\"bucket:$merchant\"),",
          "        listOf(\"10\", \"500\",",
          "            nowMillis.toString())) == 1L"]


class TokenBucket(Base):
    """cache-08, section 2. A shop's program sends the hour's refunds in one burst: 40 in a second. A window limit
    refuses it (5 a minute) or allows a flood (40 a second). The wish: a burst of up to 10, then 2 a second. The jar: at
    most 10 tokens, one more every 500 ms. Predict: a burst of 15 gets 10; one request every 250 ms gets 10 of 20,
    .+.+...; no timer: tokens and ts in a Redis hash, earned = floor((now - ts) / 500); after 5 quiet seconds the jar
    is full: 10 again. The name, one script, TTL 5 s; GCRA keeps one number (TAT) and agrees on every request.
    When to use it, the code in Java and Kotlin, the moral, and a check (2 quiet seconds: 4)."""

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
        for key in keys:
            old = self.lab.pop(key, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def clock(self, ms):
        return self.put("clock", M(f"t = {ms:,} ms", 26, GREY_B).move_to([0, CLOCK_Y, 0]))

    def state(self, tokens, ts, color=WHITE):
        return self.put("state", M(f"bucket:merchant:m-17   tokens: {tokens}   ts: {ts:,} ms", 20, color).move_to([0, STATE_Y, 0]))

    def sv(self, key, s, y, color=WHITE, size=22, mono=False):
        m = (M if mono else T)(s, size, color)
        return self.put(key, fit(m, SV_X1 - SV_X0 - 0.4).move_to([SV_CX, y, 0]))

    # --- the jar ---
    def refill(self, n):
        anims = []
        for _ in range(n):
            k = len(self.jar)
            if k >= 10:
                break
            t = Circle(radius=0.22, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.6), 1).move_to(tok_pos(k)).set_z_index(4)
            self.jar.append(t)
            anims.append(FadeIn(t, shift=0.3 * DOWN))
        return anims

    def request(self, rt=0.55, color=WHITE):
        """One request: it takes the top token and goes on to the service, or is refused at the jar."""
        a, b = np.array([CL_X1 + 0.1, REQ_Y, 0]), np.array([JAR_X0 - 0.1, REQ_Y, 0])
        c = np.array([SV_X0 - 0.1, REQ_Y, 0])
        if self.jar:
            t = self.jar.pop()
            go = AnimationGroup(run_pts([b + [0, 0, 0], c], GREEN_M, rt * 0.5), FadeOut(t, shift=0.25 * RIGHT, run_time=rt * 0.4))
            return True, Succession(run_pts([a, b], color, rt * 0.5), go)
        x = tick(False, 0.12).move_to(b + 0.35 * DOWN)
        return False, Succession(run_pts([a, b], RED_M, rt * 0.5), Succession(FadeIn(x, run_time=0.05), FadeOut(x, run_time=rt * 0.45)))

    def burst(self, n, lag=0.12):
        res = [self.request(0.6) for _ in range(n)]
        return sum(ok for ok, _ in res), LaggedStart(*[a for _, a in res], lag_ratio=lag)

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab, self.jar = {}, []
        self.title_card("A burst, then a steady rate", "a jar of tokens that never needs a timer")

        client = frame(CL_X0, CL_X1, CL_TOP, CL_BOT, PURPLE_M)
        cl_lab = VGroup(T("the shop's", 21), T("refund program", 21), T("a client", 17, GREY_B)).arrange(DOWN, buff=0.12).move_to(
            [CL_CX, (CL_TOP + CL_BOT) / 2, 0])
        a_in = harrow(CL_X1 + 0.06, JAR_X0 - 0.06, REQ_Y)
        a_out = harrow(JAR_X1 + 0.06, SV_X0 - 0.06, REQ_Y)
        jar = VGroup(RoundedRectangle(corner_radius=0.3, width=JAR_W, height=JAR_H, stroke_color=GOLD_M, stroke_width=3)
                     .set_fill(fillc(GOLD_M, 0.08), 1).move_to(JAR_C),
                     RoundedRectangle(corner_radius=0.08, width=JAR_W * 0.7, height=0.2, stroke_color=GOLD_M, stroke_width=3)
                     .set_fill(fillc(GOLD_M, 0.3), 1).move_to([JAR_C[0], JAR_TOP + 0.12, 0]))
        jar_top = T("the jar: holds 10", 21, GOLD_M).move_to([JAR_C[0], JAR_TOP + 0.55, 0])
        jar_bot = T("+1 token every 500 ms", 19, GREY_B).move_to([JAR_C[0], JAR_BOT - 0.32, 0])
        sv = frame(SV_X0, SV_X1, SV_TOP, SV_BOT, BLUE_M)
        sv_t = T("the payments service", 23).move_to([SV_CX, SV_TOP - 0.3, 0])

        # ---------------- scene 1: the question ----------------
        def flood(n=40, color=WHITE, rt=1.6):
            a, b = np.array([CL_X1 + 0.1, REQ_Y, 0]), np.array([SV_X0 - 0.1, REQ_Y, 0])
            return [LaggedStart(*[run_pts([a + [0, 0.05 * ((k % 5) - 2), 0], b], color, 0.5) for k in range(n)],
                                lag_ratio=0.04, run_time=rt)]

        self.steps("Picture a shop's program that sends the hour's refunds all at once: 40 requests in one second, "
                   "at the end of every hour, and nothing in between.", [
            (lambda: [FadeIn(client), FadeIn(cl_lab), FadeIn(sv), FadeIn(sv_t)], 0.8),
            "40 requests",
            (lambda: [*flood(40), *self.sv("s1", "40 requests in 1 second", 1.35)], 1.6),
            "nothing in between",
            (lambda: self.sv("s2", "then nothing for an hour", 0.85, GREY_B), 0.5),
        ])
        self.steps("Is that an attack? No, just a program in a hurry. But a broken program that sends 40 every second, forever, "
                   "is a problem. How do you write one limit that lets the first through and stops the second?", [
            "a program in a hurry",
            (lambda: self.cap("an honest burst: a program in a hurry"), 0.5),
            "a broken program",
            (lambda: [*self.cap("a broken program: 40 every second, forever", RED_M), *flood(30, RED_M, 1.2)], 1.2),
            (lambda: flood(30, RED_M, 1.2), 1.2),
            "How do you",
            (lambda: self.cap("one limit: let the burst in, stop the flood?", WHITE), 0.5),
        ])

        # ---------------- scene 2: windows can't say it ----------------
        self.steps("The limits so far count requests per window. A limit of 5 a minute refuses most of the burst. "
                   "A limit of 40 a second lets the broken program flood you, forever.", [
            (lambda: [*self.uncap(), *self.drop("s1", "s2"), *self.cap("limits so far: a count per window")], 0.5),
            "5 a minute",
            (lambda: [*self.sv("s1", "5 a minute: 5 of 40 get in", 1.35, RED_M)], 0.5),
            "40 a second",
            (lambda: [*self.sv("s2", "40 a second: the flood gets in", 0.85, RED_M)], 0.5),
        ])
        self.steps("One number per window can't say: bursts are fine, floods are not. "
                   "What we want sounds like this: a burst of up to 10, then 2 a second on average.", [
            (lambda: self.cap("one number per window can't say it"), 0.5),
            "What we want",
            (lambda: [*self.drop("s1", "s2"), *self.cap("the wish: a burst of up to 10, then 2 a second", YELLOW_M, 30)], 0.6),
        ])

        # ---------------- scene 3: the jar ----------------
        self.steps("Picture a jar of tokens on a counter, like tokens for an arcade. It holds at most 10, "
                   "and gains one token every 500 milliseconds.", [
            (lambda: [*self.uncap(), FadeIn(jar), FadeIn(jar_top)], 0.7),
            "It holds",
            (lambda: [LaggedStart(*self.refill(10), lag_ratio=0.15)], 1.2),
            "and gains",
            (lambda: [FadeIn(jar_bot)], 0.5),
        ])
        self.steps("Each request takes a token. If the jar is empty, the request is refused.", [
            (lambda: [GrowArrow(a_in), GrowArrow(a_out)], 0.5),
            "Each request",
            (lambda: [self.request(0.9)[1]], 0.9),
            "If the jar is empty",
            (lambda: [glow(jar[0], RED_M, 1.02)], 0.6),
        ])
        self.steps("Map it: a token is permission for one request. The jar's size, 10, is the burst. "
                   "One new token every 500 milliseconds is the rate: 2 a second.", [
            (lambda: [*self.refill(1), *self.cap("a token: permission for one request")], 0.5),
            "The jar's size",
            (lambda: [*self.cap("the jar's size, 10: the burst"), Indicate(jar_top, color=GOLD_M)], 0.7),
            "One new token",
            (lambda: [*self.cap("one token per 500 ms: the rate, 2 a second"), Indicate(jar_bot, color=WHITE)], 0.7),
        ])

        # ---------------- scene 4: predict a burst, then a steady stream ----------------
        self.steps("The program was quiet, so its jar is full. It sends 15 requests at once. How many get in? Pause and guess.", [
            (lambda: [*self.uncap(), *self.clock(0), *self.state(10, 0)], 0.6),
            "15 requests",
            (lambda: [*self.cap("a burst of 15 at t = 0. how many get in? pause and guess", YELLOW_M)], 0.5),
        ], after=0)
        self.countdown(3.0)
        n, anim = self.burst(15)
        self.steps("Ten. It spends the whole jar, and the last 5 find it empty.", [
            (lambda: [anim], 2.4),
            (lambda: [*self.sv("r1", f"burst of 15 at t = 0:  {n} in", 1.4, GREEN_M), *self.state(0, 0), *self.uncap()], 0.5),
        ])

        marks = []

        def tick_req(i):
            t = 250 * i
            anims = [*self.clock(t)]
            if i % 2 == 0:
                anims += self.refill(1)
            return anims

        def mark_anims(i, ok):
            m = M("+" if ok else ".", 28, GREEN_M if ok else RED_M).move_to([SV_X0 + 0.4 + 0.22 * (i - 1), 0.42, 0])
            marks.append(m)
            return [FadeIn(m)]

        self.steps("Now it sends one request every 250 milliseconds, for 5 seconds. That's 20 requests. How many get in?", [
            (lambda: [*self.sv("r2", "then one every 250 ms for 5 s:", 0.9)], 0.5),
            "How many",
            (lambda: self.cap("20 requests, one every 250 ms: how many get in?", YELLOW_M), 0.5),
        ], after=0.6)
        steady = []
        for i in range(1, 21):
            steady.append((lambda i=i: tick_req(i), 0.12))
            steady.append((lambda i=i: (lambda ok_a: [ok_a[1], *mark_anims(i, ok_a[0])])(self.request(0.4)), 0.34))
        self.steps("Ten. A new token arrives every 500 milliseconds, so every second request finds one. "
                   "Refused, let in, refused, let in: 2 a second, exactly the rate.", [
            (lambda: self.uncap(), 0.2),
            *steady,
            (lambda: [*self.sv("r3", "10 of 20 got in", -0.1, GREEN_M), *self.state(0, 5000)], 0.5),
        ])
        self.stamp("steady")

        # ---------------- scene 5: no timer ----------------
        self.steps("So who drops a token into the jar every 500 milliseconds? A timer for every client? "
                   "With a million clients, that's a million timers ticking for jars nobody is using.", [
            (lambda: [Indicate(jar_bot, color=YELLOW_M, scale_factor=1.15), *self.cap("who drops the tokens in? a timer per client?", PURPLE_M)], 0.8),
            "With a million",
            (lambda: self.cap("a million clients: a million timers, for jars nobody is using", RED_M), 0.6),
        ])
        self.steps("The trick is a lazy shopkeeper. He tops up the jar only when someone walks in, by checking the clock.", [
            (lambda: [*self.cap("a lazy shopkeeper: top up only when someone walks in", YELLOW_M),
                      jar_bot.animate.set_opacity(0.25)], 0.6),
        ])
        self.steps("Store two numbers per client in a Redis hash, a small table of named fields under one key: tokens, "
                   "what was left after the last request, and ts, when the jar was last topped up.", [
            "a Redis hash",
            (lambda: [Indicate(self.lab["state"], color=TEAL_M, scale_factor=1.06), *self.cap("a Redis hash: named fields under one key")], 0.8),
            "tokens, what",
            (lambda: self.cap("tokens: what was left after the last request"), 0.5),
            "and ts",
            (lambda: self.cap("ts: when the jar was last topped up"), 0.5),
        ])
        self.steps("On each request, work out the tokens earned since ts: the time gone by, divided by 500 milliseconds, "
                   "rounded down. Add them, never above 10, and take one.", [
            (lambda: self.cap("earned = floor((now - ts) / 500)", YELLOW_M), 0.5),
            "Add them",
            (lambda: self.cap("tokens = min(10, tokens + earned); then take one", YELLOW_M), 0.5),
        ])
        self.steps("Watch it after 5 quiet seconds. Nothing moved while the program was quiet.", [
            (lambda: [*self.uncap(), *self.clock(10000)], 0.6),
            "Nothing moved",
            (lambda: [glow(jar[0], GREY_B, 1.02)], 0.9),
        ])
        n2 = [0]

        def burst2():
            n, a = self.burst(15)
            n2[0] = n
            return [a]

        self.steps("Then a burst of 15 arrives. The time gone by is 5,000 milliseconds: 10 tokens earned, and the jar is full again. "
                   "Ten get in.", [
            "The time gone by",
            (lambda: self.cap("10,000 - 5,000 = 5,000 ms: 10 tokens earned", YELLOW_M), 0.5),
            "the jar is full",
            (lambda: [LaggedStart(*self.refill(10), lag_ratio=0.05), *self.state(10, 10000)], 0.7),
            "Ten get in",
            (lambda: burst2(), 2.2),
            (lambda: [*self.sv("r4", f"burst after 5 quiet s:  {n2[0]} in", -0.75, GREEN_M), *self.state(0, 10000)], 0.5),
        ])
        self.steps("This is a token bucket. The jar is the bucket.", [
            (lambda: [*self.cap("a token bucket", GOLD_M, 32), Transform(jar_top, T("the jar: the bucket", 21, GOLD_M).move_to(jar_top))], 0.6),
        ], after=0.4)
        self.stamp("poster")

        # ---------------- scene 6: details, and GCRA ----------------
        self.steps("Two details. The whole calculation runs as one script inside Redis, so two servers never both take the last token.", [
            (lambda: self.cap("one script inside Redis: two servers never both take the last token"), 0.6),
        ])
        self.steps("And the key gets a TTL of 5 seconds, the time to fill an empty jar. "
                   "After 5 quiet seconds the jar would be full anyway, so Redis may forget it.", [
            (lambda: self.cap("TTL: 5 s, the time to fill an empty jar"), 0.5),
            "so Redis may forget",
            (lambda: [self.lab["state"].animate(rate_func=there_and_back).set_opacity(0.15), *self.cap("forgotten = full: no answer changes")], 1.2),
        ])

        axis_x0, step_w = -4.0, 0.8
        axis = VGroup(Line([axis_x0, STATE_Y, 0], [axis_x0 + 10 * step_w + 0.6, STATE_Y, 0], stroke_width=2, color=GREY_C),
                      *[Line([axis_x0 + k * step_w, STATE_Y - 0.08, 0], [axis_x0 + k * step_w, STATE_Y + 0.08, 0], stroke_width=2, color=GREY_C)
                        for k in range(11)])
        now_l = T("now", 16, GREY_B).move_to([axis_x0, STATE_Y - 0.36, 0])
        lim = DashedLine([axis_x0 + 10 * step_w, STATE_Y - 0.12, 0], [axis_x0 + 10 * step_w, STATE_Y + 0.25, 0], color=RED_M, dash_length=0.06)
        lim_l = T("now + 10 x 500 ms", 16, RED_M).move_to([axis_x0 + 10 * step_w, STATE_Y - 0.36, 0])
        tat = Triangle(color=YELLOW_M).set_fill(YELLOW_M, 1).scale(0.11).rotate(PI).move_to([axis_x0, STATE_Y + 0.22, 0])
        tat_l = T("next due", 15, YELLOW_M).next_to(tat, UP, buff=0.06)
        gx = tick(False, 0.14).move_to([axis_x0 + 11 * step_w, STATE_Y + 0.45, 0])
        self.steps("There's a version with only one number, called GCRA, the generic cell rate algorithm. "
                   "It keeps a schedule instead of a jar: the time the client's next request would be due, if it sent at exactly the allowed rate.", [
            (lambda: [*self.drop("state"), *self.cap("GCRA: the generic cell rate algorithm", WHITE)], 0.5),
            "It keeps a schedule",
            (lambda: [Create(axis), FadeIn(now_l), FadeIn(tat), FadeIn(tat_l)], 0.8),
            "next request",
            (lambda: self.cap("one number: when the next request would be due"), 0.5),
        ])
        self.steps("Each request that gets in pushes that time 500 milliseconds later. "
                   "A request is refused if it would push it more than 10 steps past now.", [
            (lambda: [FadeIn(lim), FadeIn(lim_l)], 0.4),
            *[(lambda: [VGroup(tat, tat_l).animate.shift(step_w * RIGHT)], 0.22) for _ in range(10)],
            "A request is refused",
            (lambda: [VGroup(tat, tat_l).animate(rate_func=there_and_back).shift(step_w * RIGHT).set_color(RED_M)], 0.7),
            (lambda: [Create(gx)], 0.3),
        ])
        self.steps("In the lesson's demo, the bucket and GCRA got the same traffic, and agreed on every single request. "
                   "The bucket keeps two numbers, GCRA keeps one.", [
            (lambda: self.cap("same traffic: the same answer on every request", GREEN_M), 0.5),
            "The bucket keeps",
            (lambda: self.cap("bucket: {tokens=0, ts=1762500010000}     GCRA: 1762500015000"), 0.5),
        ])
        gcra_parts = VGroup(axis, now_l, lim, lim_l, tat, tat_l, gx)
        self.steps("When should you use one? When you want to cap how often a customer's program calls your service, and still allow "
                   "its bursts. For a small exact limit, like attempts per card, the sliding log from earlier fits better.", [
            (lambda: [*[FadeOut(m) for m in gcra_parts],
                      *self.cap("a cap on a customer's program, bursts allowed: a token bucket or GCRA")], 0.6),
            "For a small",
            (lambda: self.cap("a small exact limit (attempts per card): the sliding log"), 0.5),
        ])

        # ---------------- scene 7: the code ----------------
        keep = [m for m in self.mobjects if m is not self.capm and isinstance(m, VMobject)]
        diagram = VGroup(*keep)
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(rows_j, rows_k, color):
            return [jp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows_j] + \
                   [kp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows_k]

        self.steps("In Java and Kotlin, the call is the same: run the script on the client's key, with 10 tokens, "
                   "500 milliseconds, and the time now. A 1 means let it in.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "run the script",
            (lambda: hl((1, 2), (2, 3), TEAL_M), 1.2),
            "with 10 tokens",
            (lambda: hl((3, 4), (4, 5), GOLD_M), 1.4),
            "A 1 means",
            (lambda: hl((5,), (5,), GREEN_M), 1.0),
        ], after=0.6)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, a burst, then a steady rate: the jar's size is the burst, and its refill is the rate.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            "the jar's size",
            (lambda: [Indicate(jar_top, color=GOLD_M), *self.cap("the jar's size: the burst.   its refill: the rate", WHITE)], 0.7),
        ])
        self.steps("And the jar never needs a timer. It only needs to remember how full it was, and when it last looked.", [
            (lambda: [*self.state(0, 10000), *self.cap("no timer: just how full it was, and when it last looked", YELLOW_M)], 0.6),
        ], after=0.4)
        self.steps("One quick check. A program empties its jar, then stays quiet for 2 seconds, and sends 10 requests at once. "
                   "How many get in? Pause and think.", [
            (lambda: [*self.uncap(), *self.clock(12000), *self.drop("r1", "r2", "r3", "r4"), *[FadeOut(m) for m in marks]], 0.6),
            "stays quiet",
            (lambda: [glow(jar[0], GREY_B, 1.02)], 0.8),
            "Pause and think",
            (lambda: self.cap("2 quiet seconds, then 10 at once: how many get in? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        n3 = [0]

        def last_burst():
            n, a = self.burst(10)
            n3[0] = n
            return [a]

        self.steps("Four. Two seconds is 2,000 milliseconds: four tokens earned, so four get in, and six are refused.", [
            (lambda: [LaggedStart(*self.refill(4), lag_ratio=0.15), *self.state(4, 12000),
                      *self.cap("2,000 ms / 500 ms = 4 tokens earned", YELLOW_M)], 0.7),
            "so four get in",
            (lambda: last_burst(), 1.8),
            (lambda: [*self.sv("r1", f"10 at once after 2 quiet s:  {n3[0]} in", 1.4, GREEN_M), *self.state(0, 12000)], 0.5),
        ])
        self.steps("Next, the customer who pressed Pay twice. A limit lets both presses through, so we'll learn to recognize a repeat.", [
            (lambda: self.cap("a burst, then a steady rate: the jar's size, and its refill", WHITE), 0.6),
        ], after=0.3)
        self.wait(2.0)
