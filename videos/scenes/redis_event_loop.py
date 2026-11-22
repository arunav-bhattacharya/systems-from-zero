from sfz import *

# The letter A naming a client: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bINCRs?\b", lambda m: "increment" + ("s" if m.group(0).endswith("s") else "")))
SAY.insert(0, (r"\bGETs\b", "gets"))
SAY.insert(0, (r"\bSET\b", "set"))
SAY.insert(0, (r"\bHGETALL\b", "H get all"))
SAY.insert(0, (r"\bKEYS \*", "keys star"))
SAY.insert(0, (r"\bDEL\b", "dell"))
SAY.insert(0, (r"\bSLOWLOG GET\b", "slow log get"))
SAY.insert(0, (r"\bepoll_wait\b", "E poll wait"))
SAY.insert(0, (r"\b(card|payment):(\d+)\b", r"\1 \2"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CX, CY, CW, CH = -5.15, [1.55, 0.0, -1.55], 2.8, 1.1      # clients A, B, C
SRV = dict(x0=-2.65, x1=6.55, y0=-2.25, y1=2.45)          # the Redis server outline
LOOP, LW, LH = np.array([0.5, 0.0, 0]), 2.8, 2.0         # the one thread / event loop
MEM, MW, MH = np.array([4.55, 0.1, 0]), 3.7, 3.9          # memory: four keys
ROW_Y = [1.05, 0.35, -0.35, -1.05]
KEY_X, VAL_X = 2.95, 6.15
RX = -1.78                                                # reply chips (outgoing buffers)
CLOCK_Y, STEPS_Y, BAR_Y, CAP_Y = -1.42, -1.98, -2.72, -3.22


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d, run_time=0.3), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6, stay=False):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    parts = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt)]
    if not stay:
        parts.append(FadeOut(d, run_time=0.12))
    return Succession(*parts), d


def outline(m, color=YELLOW_M, buff=0.08):
    """Pulse an outline round a box (Indicate would turn an opaque box into a solid block)."""
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.14, stroke_width=4).set_z_index(7)
    return Succession(Create(r, run_time=0.35), FadeOut(r, run_time=0.45))


def padlock(c, color=RED_M, s=1.0):
    body = RoundedRectangle(corner_radius=0.03, width=0.26 * s, height=0.2 * s, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.4), 1)
    shackle = Arc(radius=0.085 * s, start_angle=0, angle=PI, stroke_color=color, stroke_width=2.5)
    shackle.move_to(body.get_top() + [0, 0.07 * s, 0])
    return VGroup(shackle, body).move_to(c)


def parcel(c, color=GOLD_M):
    sq = Square(0.36, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.45), 1)
    tie = VGroup(Line(sq.get_top(), sq.get_bottom()), Line(sq.get_left(), sq.get_right())).set_stroke(color, 1.5)
    return VGroup(sq, tie).move_to(c).set_z_index(6)


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


class RedisEventLoop(Base):
    """cache-02, section 1. Two worries (slow? risky?). A thread per client: memory, switching, and the lost count
    (both read 41, both write 42), so a lock on every key. The post office: one clerk finishes each job before the
    next; the clerk never waits at an empty window (epoll_wait). One pass of the event loop with three clients (the
    stepper). Two INCRs at once: 42, 43, 44, so each command is atomic. Half a microsecond per GET, so queues stay
    invisible. The four hundred parcels: a 1.5 s script, B's GET answered 1,200 ms late. Guardrails: commands that
    grow with a key, SLOWLOG GET; atomic covers one command (1,611 of 8,000; INCR gives 8000), Java and Kotlin.
    The moral, and a check (C asks for another key)."""

    # ---------- small state helpers ----------
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0]).set_z_index(3)
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
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

    def cmd(self, i, s, color=WHITE):
        return self.put(f"cmd{i}", fit(M(s, 16, color), CW - 0.3).move_to([CX, CY[i] - 0.2, 0]))

    def cname(self, i, s, color=WHITE):
        return self.put(f"name{i}", T(s, 22, color).move_to([CX, CY[i] + 0.24, 0]))

    def cstroke(self, i, color):
        return [self.crect[i].animate.set_stroke(color).set_fill(fillc(color), 1)]

    def lstate(self, a, b=None, ca=WHITE, cb=GREY_B, mono_a=False):
        out = self.put("l1", fit((M(a, 18, ca) if mono_a else T(a, 21, ca)), LW - 0.3).move_to(LOOP + [0, -0.02, 0]))
        if b is None:
            out += self.drop("l2")
        else:
            out += self.put("l2", fit(T(b, 18, cb), LW - 0.3).move_to(LOOP + [0, -0.45, 0]))
        return out

    def ltitle(self, s, color=YELLOW_M):
        return self.put("lt", T(s, 24, color).move_to(LOOP + [0, 0.55, 0]))

    def lcolor(self, color):
        return [self.loop.animate.set_stroke(color).set_fill(fillc(color, 0.12), 1)]

    def val(self, r, s, color=WHITE):
        return self.put(f"v{r}", right_at(M(s, 18, color), VAL_X, ROW_Y[r]))

    def clock(self, s, color=GREY_B):
        return self.put("clock", T(s, 19, color).move_to([LOOP[0], CLOCK_Y, 0]))

    def reply(self, i, s, color=GREEN_M):
        return self.put(f"rep{i}", fit(chip(s, color, 16, mono=True), 1.6).move_to([RX, CY[i], 0]))

    def to_loop(self, i, color=YELLOW_M, rt=0.5, stay=False):
        a = [CX + CW / 2, CY[i], 0]
        b = [LOOP[0] - LW / 2, float(np.clip(CY[i], -0.7, 0.7)), 0]
        return dot_run(a, b, color, rt, stay)

    def to_mem(self, r, color=YELLOW_M):
        a = LOOP + [LW / 2, 0.3 * (1.5 - r) - 0.1, 0]
        b = [MEM[0] - MW / 2, ROW_Y[r], 0]
        return Arrow(a, b, buff=0.06, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.25,
                     max_stroke_width_to_length_ratio=10).set_z_index(2)

    def send(self, i):
        """The reply chip travels to its client, then fades."""
        ch = self.lab.pop(f"rep{i}")
        return Succession(ch.animate(run_time=0.5).move_to([CX + CW / 2 - 0.4, CY[i], 0]).set_opacity(0.0), run_time=0.6)

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def run_cmd(self, i, r, line, new_val, rep, vcolor=YELLOW_M):
        """One command from client i, run to the end against memory row r: steps for steps()."""
        holder = {}

        def go():
            anim, _ = self.to_loop(i)
            return [anim]

        def runit():
            holder["a"] = self.to_mem(r)
            out = [*self.lstate(line, None, WHITE, mono_a=True), GrowArrow(holder["a"]), outline(self.crect[i], YELLOW_M)]
            if new_val is not None:
                out += self.val(r, new_val, vcolor)
            return out

        def done():
            return [FadeOut(holder["a"]), *self.reply(i, rep)]

        return [(go, 0.5), (runit, 0.6), (done, 0.45)]

    # ---------- the video ----------
    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("One clerk for every window", "how Redis runs each command")

        srv = RoundedRectangle(corner_radius=0.2, width=SRV["x1"] - SRV["x0"], height=SRV["y1"] - SRV["y0"],
                               stroke_color=GREY_C, stroke_width=2).move_to([(SRV["x0"] + SRV["x1"]) / 2, (SRV["y0"] + SRV["y1"]) / 2, 0])
        srv_lab = left_at(T("Redis server", 22, GREY_B), SRV["x0"] + 0.1, SRV["y1"] + 0.3)
        mem = RoundedRectangle(corner_radius=0.14, width=MW, height=MH, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1).move_to(MEM)
        mem_lab = T("memory", 20, GREY_B).move_to([MEM[0], MEM[1] + MH / 2 - 0.32, 0])
        keys = ["auths:today", "card:7", "card:9", "payment:42"]
        vals0 = ["41", "ok", "(none)", "approved"]
        key_m = VGroup(*[left_at(M(k, 18, WHITE), KEY_X, y) for k, y in zip(keys, ROW_Y)]).set_z_index(3)
        self.crect = [RoundedRectangle(corner_radius=0.12, width=CW, height=CH, stroke_color=BLUE_M, stroke_width=3)
                      .set_fill(fillc(BLUE_M), 1).move_to([CX, y, 0]) for y in CY]
        self.loop = RoundedRectangle(corner_radius=0.14, width=LW, height=LH, stroke_color=YELLOW_M, stroke_width=3).set_fill(fillc(YELLOW_M, 0.12), 1).move_to(LOOP)
        more = T("... and thousands more", 19, GREY_B).move_to([CX, -2.5, 0])
        chips = {"slow": chip("slow?", RED_M, 22).move_to([3.55, 3.12, 0]), "risky": chip("risky?", RED_M, 22).move_to([5.35, 3.12, 0])}

        # ---------------- scene 1: two worries ----------------
        self.steps("Redis is a program that keeps data in memory and answers requests over the network.", [
            (lambda: [Create(srv), FadeIn(srv_lab), FadeIn(mem), FadeIn(mem_lab)], 0.9),
            "keeps data in memory",
            (lambda: [FadeIn(key_m), *[x for r in range(4) for x in self.val(r, vals0[r])]], 0.7),
        ])
        self.steps("Thousands of programs can talk to one Redis server at once, sending short commands "
                   "like \"add one to this counter\".", [
            "Thousands",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.15 * RIGHT) for r in self.crect], lag_ratio=0.2),
                      *[x for i in range(3) for x in self.cname(i, f"client {'ABC'[i]}")], FadeIn(more)], 1.0),
            "like",
            (lambda: [outline(VGroup(key_m[0], self.lab["v0"]), YELLOW_M, 0.1)], 0.8),
        ])
        self.steps("Redis runs all of them on a single thread, one line of work inside the program.", [
            "a single thread",
            (lambda: [FadeIn(self.loop), *self.ltitle("one thread")], 0.7),
        ])
        self.steps("One thread, for thousands? That sounds slow, and risky. Hold on to both worries.", [
            "sounds slow",
            (lambda: [FadeIn(chips["slow"], shift=0.1 * UP)], 0.4),
            "and risky",
            (lambda: [FadeIn(chips["risky"], shift=0.1 * UP)], 0.4),
        ], after=0.3)
        self.stamp("worries")

        # ---------------- scene 2: a thread for every client ----------------
        thr = [RoundedRectangle(corner_radius=0.12, width=2.6, height=0.9, stroke_color=GREY_B, stroke_width=3)
               .set_fill(fillc(GREY_B, 0.12), 1).move_to([LOOP[0], y, 0]) for y in CY]
        thr_t = [T(f"thread {k}", 21, GREY_B).move_to([LOOP[0], y, 0]).set_z_index(3) for k, y in zip((1, 2, 3), CY)]
        wires = [Line([CX + CW / 2, y, 0], [LOOP[0] - 1.3, y, 0], stroke_width=2, color=GREY_C) for y in CY]
        self.steps("The obvious design gives each client its own thread. A client reaches the server through a connection, "
                   "an open line between two programs.", [
            (lambda: [FadeOut(self.loop), *self.drop("lt"), *[FadeIn(t) for t in thr], *[FadeIn(t) for t in thr_t]], 0.8),
            "through a connection",
            (lambda: [*[Create(w) for w in wires]], 0.7),
            "an open line",
            (lambda: [LaggedStart(*[dot_run(w.get_start(), w.get_end(), YELLOW_M, 0.5)[0] for w in wires], lag_ratio=0.3)], 1.0),
        ])
        self.steps("Ten thousand clients need ten thousand threads, each with its own memory, "
                   "and the computer spends much of its time switching between them.", [
            "Ten thousand",
            (lambda: self.cap("10,000 clients: 10,000 threads, each with its own memory", WHITE), 0.6),
            "switching",
            (lambda: [Succession(*[outline(t, RED_M, 0.06) for t in thr + thr])], 1.6),
        ])
        ra, rb = Arrow([LOOP[0] + 1.3, CY[0], 0], [MEM[0] - MW / 2, ROW_Y[0], 0], buff=0.06, stroke_width=3, color=YELLOW_M,
                       max_tip_length_to_length_ratio=0.15), \
            Arrow([LOOP[0] + 1.3, CY[1], 0], [MEM[0] - MW / 2, ROW_Y[0] - 0.08, 0], buff=0.06, stroke_width=3, color=YELLOW_M,
                  max_tip_length_to_length_ratio=0.15)
        ra.set_z_index(2), rb.set_z_index(2)
        self.steps("Worse, two threads can touch the same key at once. A key is a name for a value, like this counter.", [
            (lambda: self.cap("worse: two threads, one key", WHITE), 0.5),
            "A key is",
            (lambda: [outline(VGroup(key_m[0], self.lab["v0"]), YELLOW_M, 0.1)], 0.8),
        ])

        def relabel(k, s, color):
            new = T(s, 21, color).move_to(thr_t[k])
            old = thr_t[k]
            thr_t[k] = new.set_z_index(3)
            return [swap(old, new)]

        self.steps("Client A and client B both send INCR, add one. Both threads read 41. Both write 42. "
                   "Two adds, and the counter went up by one.", [
            (lambda: [*self.uncap(), *self.cmd(0, "INCR auths:today"), *self.cmd(1, "INCR auths:today")], 0.6),
            "Both threads read",
            (lambda: [GrowArrow(ra), GrowArrow(rb), *relabel(0, "reads 41", YELLOW_M), *relabel(1, "reads 41", YELLOW_M),
                      thr[0].animate.set_stroke(YELLOW_M), thr[1].animate.set_stroke(YELLOW_M)], 0.7),
            "Both write",
            (lambda: [*relabel(0, "writes 42", YELLOW_M), *relabel(1, "writes 42", YELLOW_M), *self.val(0, "42", RED_M)], 0.6),
            "Two adds",
            (lambda: self.cap("two adds, and the counter went up by one", RED_M), 0.6),
        ])
        locks = [padlock([2.33, y, 0]) for y in ROW_Y]
        self.steps("The fix is a lock on every key, a marker that lets one thread in at a time, and every command pays for it.", [
            (lambda: [FadeOut(ra), FadeOut(rb), *relabel(0, "thread 1", GREY_B), *relabel(1, "thread 2", GREY_B),
                      thr[0].animate.set_stroke(GREY_B), thr[1].animate.set_stroke(GREY_B)], 0.5),
            "a lock on every key",
            (lambda: [LaggedStart(*[FadeIn(l, scale=0.6) for l in locks], lag_ratio=0.2)], 0.8),
            "every command pays",
            (lambda: self.cap("a lock on every key: every command pays for it", WHITE), 0.6),
        ])
        self.steps("What we'd like is a design where two commands can never collide, with no locks at all.", [
            (lambda: self.cap("wanted: two commands that can never collide, and no locks", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("threads")

        # ---------------- scene 3: the post office ----------------
        self.steps("Picture a small post office with one clerk and six windows.", [
            (lambda: [*self.uncap(), *[FadeOut(x) for x in thr + thr_t + wires + locks], *self.drop("cmd0", "cmd1"),
                      *self.val(0, "41"), *[r.animate.set_stroke(GOLD_M).set_fill(fillc(GOLD_M), 1) for r in self.crect],
                      *[x for i in range(3) for x in self.cname(i, f"window {i + 1}", GOLD_M)], FadeOut(more),
                      VGroup(mem_lab, key_m, srv_lab).animate.set_opacity(0.25), mem.animate.set_stroke(opacity=0.25),
                      srv.animate.set_stroke(opacity=0.25),
                      *[self.lab[f"v{r}"].animate.set_opacity(0.25) for r in range(4)]], 0.9),
            "one clerk",
            (lambda: [FadeIn(self.loop.set_stroke(GOLD_M).set_fill(fillc(GOLD_M, 0.12), 1)), *self.ltitle("the clerk", GOLD_M)], 0.6),
        ])
        par = [parcel([CX + CW / 2 + 0.3, y, 0]) for y in CY]

        def serve(k):
            p = par[k]
            return [Succession(FadeIn(p, run_time=0.15), p.animate(run_time=0.6).move_to(LOOP + [0, -0.3, 0]),
                               Wait(0.35), FadeOut(p, run_time=0.2))]

        self.steps("The clerk serves the first window, then the second, round the room, finishing each job before starting the next.", [
            "the first window",
            (lambda: serve(0), 1.3),
            "then the second",
            (lambda: serve(1), 1.3),
            "round the room",
            (lambda: serve(2), 1.3),
        ])
        drawer = T("stamp drawer: no lock", 19, GOLD_M).move_to(LOOP + [0, -0.4, 0])
        self.steps("There's one pair of hands, so two customers can never grab the same parcel. The clerk never even locks the stamp drawer. "
                   "Who would she lock it against?", [
            "one pair of hands",
            (lambda: self.cap("one pair of hands: nobody grabs the same parcel", WHITE), 0.6),
            "stamp drawer",
            (lambda: [*self.put("l2", drawer)], 0.5),
        ], after=0.3)

        maps = [("window = a connection", "connections"), ("the clerk = the one thread", "thread"), ("a job = a command", "command")]
        self.steps("That's Redis. The clerk is the one thread, the windows are the connections, and each job is a command.", [
            (lambda: [*self.drop("l2"), VGroup(mem_lab, key_m, srv_lab).animate.set_opacity(1), mem.animate.set_stroke(opacity=1),
                      srv.animate.set_stroke(opacity=1),
                      *[self.lab[f"v{r}"].animate.set_opacity(1) for r in range(4)]], 0.6),
            "The clerk is",
            (lambda: [*self.cap(maps[1][0], YELLOW_M), *self.lcolor(YELLOW_M), *self.ltitle("one thread")], 0.6),
            "the windows are",
            (lambda: [*self.cap(maps[0][0], BLUE_M), *[r.animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1) for r in self.crect],
                      *[x for i in range(3) for x in self.cname(i, f"client {'ABC'[i]}")]], 0.7),
            "each job is",
            (lambda: self.cap(maps[2][0], WHITE), 0.5),
        ])
        self.steps("And the clerk never waits at an empty window. Redis's thread asks the operating system, the program that runs "
                   "the computer, which connections have bytes waiting.", [
            "never waits",
            (lambda: self.cap("the clerk never waits at an empty window", WHITE), 0.6),
            "asks the operating system",
            (lambda: [*self.lstate("which connections", "have bytes waiting?", WHITE, WHITE)], 0.6),
        ])
        self.steps("On Linux, that request is called epoll_wait. If none do, the thread sleeps until one does.", [
            "epoll_wait",
            (lambda: self.cap(M("epoll_wait: \"tell me which connections have bytes waiting\"", 19, GREY_B)), 0.6),
            "sleeps",
            (lambda: [*self.lstate("asleep in epoll_wait", "using no CPU")], 0.6),
        ], after=0.3)
        self.stamp("post office")

        # ---------------- scene 4: ask, read, run, send ----------------
        self.steps("Let's watch with three clients. Client A sends INCR. B asks for card:7. C stores a value under card:9. "
                   "The thread is asleep, using no CPU.", [
            (lambda: [*self.uncap(), *self.clock("t = 0 ms")], 0.4),
            "sends INCR",
            (lambda: self.cmd(0, "INCR auths:today"), 0.5),
            "asks for",
            (lambda: self.cmd(1, "GET card:7"), 0.5),
            "stores a value",
            (lambda: self.cmd(2, "SET card:9 blocked"), 0.5),
            "The thread is asleep",
            (lambda: [outline(self.loop, GREY_B, 0.08)], 0.8),
        ])
        steps_lab = {}

        def step_lab(n):
            words = ["1 ask", "2 read", "3 run", "4 send"]
            g = VGroup(*[T(w, 18, YELLOW_M if k < n else GREY_D) for k, w in enumerate(words)]).arrange(RIGHT, buff=0.28)
            return self.put("steps", g.move_to([LOOP[0], STEPS_Y, 0]))

        self.steps("The operating system wakes it: three connections have bytes waiting.", [
            "wakes it",
            (lambda: [*self.lstate("epoll: A, B, C ready", None, YELLOW_M), *step_lab(1)], 0.6),
            "three connections",
            (lambda: [*[outline(r, YELLOW_M) for r in self.crect]], 0.8),
        ])
        self.steps("The thread reads A's bytes, cuts out one complete command, and runs it from start to finish: "
                   "read 41, add one, store 42.", [
            (lambda: [*step_lab(2)], 0.3),
            (lambda: [self.to_loop(0)[0], *self.lstate("read A's bytes", "cut one command", WHITE, WHITE)], 0.6),
            "runs it",
            (lambda: [*step_lab(3)], 0.3),
            *self.run_cmd(0, 0, "INCR auths:today", None, ":42")[1:2],
            "store 42",
            (lambda: self.val(0, "42", YELLOW_M), 0.4),
        ])
        self.steps("The reply waits in A's outgoing buffer, a holding area. It isn't sent yet.", [
            (lambda: [*[FadeOut(m) for m in self.mobjects if isinstance(m, Arrow)], *self.reply(0, ":42")], 0.5),
            "isn't sent yet",
            (lambda: self.cap("reply :42 waits in A's outgoing buffer: not sent yet", WHITE), 0.6),
        ])
        self.steps("Then B's GET, then C's SET, each to the end.", [
            *self.run_cmd(1, 1, "GET card:7", None, '"ok"'),
            "then C's SET",
            *self.run_cmd(2, 2, "SET card:9 blocked", "blocked", "+OK"),
        ])
        self.steps("Before it sleeps again, it sends every waiting reply.", [
            (lambda: [*self.uncap(), *step_lab(4), *self.lstate("send every reply", None, GREEN_M)], 0.5),
            "sends every",
            (lambda: [self.send(0), self.send(1), self.send(2), *self.clock("t = 0.1 ms")], 0.7),
            (lambda: [*[outline(r, GREEN_M) for r in self.crect]], 0.7),
        ])
        self.steps("Ask, read, run, send. This loop is the event loop, and Redis runs it over and over.", [
            (lambda: [*self.val(0, "42"), *self.val(2, "blocked"), *self.lstate("asleep in epoll_wait", "using no CPU")], 0.5),
            "This loop",
            (lambda: [*self.ltitle("event loop"), *self.cap("the event loop: ask, read, run, send, over and over", YELLOW_M)], 0.7),
            "over and over",
            (lambda: [outline(self.lab["steps"], YELLOW_M, 0.1)], 0.8),
        ], after=0.4)
        self.stamp("loop")

        # ---------------- scene 5: two adds at once ----------------
        self.steps("Now the race from before. Client A and client B both send INCR at the same moment. The counter says 42. "
                   "Where does it end up? Pause and guess.", [
            (lambda: [*self.uncap(), *self.cmd(0, "INCR auths:today"), *self.cmd(1, "INCR auths:today"), *self.drop("cmd2")], 0.6),
            "The counter says",
            (lambda: [outline(VGroup(key_m[0], self.lab["v0"]), YELLOW_M, 0.1)], 0.8),
            "Pause and guess",
            (lambda: self.cap("both at once, from 42: where does it end up?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("44. One INCR runs to the end, 42 to 43, and only then the other, 43 to 44.", [
            (lambda: [*self.uncap(), *self.lstate("epoll: A, B ready", None, YELLOW_M), *step_lab(1)], 0.4),
            "One INCR",
            (lambda: [*step_lab(3)], 0.2),
            *self.run_cmd(0, 0, "INCR (client A)", "43", ":43")[:2],
            (lambda: [*[FadeOut(m) for m in self.mobjects if isinstance(m, Arrow)], *self.reply(0, ":43")], 0.4),
            "only then the other",
            *self.run_cmd(1, 0, "INCR (client B)", "44", ":44", GREEN_M),
        ])
        tick_r = tick(True, 0.17).next_to(chips["risky"], RIGHT, buff=0.12).set_z_index(5)
        self.steps("Commands never overlap, so every command is atomic: it happens as one step, and no client ever sees it half done.", [
            (lambda: [*step_lab(4), self.send(0), self.send(1)], 0.6),
            "atomic",
            (lambda: [*self.cap("atomic: one step, never seen half done", YELLOW_M), *self.lstate("asleep in epoll_wait", "using no CPU")], 0.6),
        ])
        self.steps("Fifty programs calling INCR on one key never lose a count, with no lock at all. Nobody else is running. "
                   "That's the risky worry.", [
            "never lose",
            (lambda: self.cap("50 programs, one key: no count lost, no lock", WHITE), 0.6),
            "risky worry",
            (lambda: [Create(tick_r), chips["risky"][0].animate.set_stroke(GREEN_M).set_fill(GREEN_M, 0.18)], 0.5),
        ], after=0.3)
        self.stamp("atomic")

        # ---------------- scene 6: is one thread slow? ----------------
        tick_s = tick(True, 0.17).next_to(chips["slow"], RIGHT, buff=0.12).set_z_index(5)
        self.steps("And the slow worry? On the lab server, a GET costs the thread about half a microsecond.", [
            (lambda: [outline(chips["slow"], YELLOW_M, 0.06), *self.drop("cmd0", "cmd1"), *self.val(0, "44")], 0.7),
            "half a microsecond",
            (lambda: self.cap("one GET: about half a microsecond of the thread's time", WHITE), 0.6),
        ])
        self.steps("Here the post office picture breaks, on speed. A clerk needs a minute per customer. "
                   "So queues that would be hopeless at a post office stay invisible in Redis.", [
            "on speed",
            (lambda: self.cap("where the post office picture breaks: speed", GOLD_M), 0.6),
            "A clerk needs",
            (lambda: self.cap("a clerk: a minute per customer.   Redis: half a microsecond", WHITE), 0.6),
            "stay invisible",
            (lambda: [Create(tick_s), chips["slow"][0].animate.set_stroke(GREEN_M).set_fill(GREEN_M, 0.18)], 0.5),
        ])
        self.steps("Until one slow request arrives.", [
            (lambda: self.cap("until one slow request arrives", RED_M), 0.5),
        ], after=0.3)
        self.stamp("speed")

        # ---------------- scene 7: four hundred parcels ----------------
        pile = VGroup(*[parcel([0, 0, 0]) for _ in range(6)]).arrange_in_grid(2, 3, buff=0.06).move_to([CX, 2.62, 0])
        self.steps("Then a customer asks for four hundred parcels to be weighed, and every window waits.", [
            (lambda: [*self.uncap(), *self.cap("four hundred parcels to weigh", GOLD_M)], 0.5),
            "four hundred parcels",
            (lambda: [FadeIn(pile, lag_ratio=0.1)], 0.7),
            "every window waits",
            (lambda: [*self.cstroke(1, RED_M), *self.cstroke(2, RED_M)], 0.5),
        ])
        tr = ValueTracker(0)
        ck = {}

        def make_clock():
            v = int(round(tr.get_value() / 50) * 50)
            s = f"t = {v:,} ms"
            if s not in ck:
                ck[s] = T(s, 19, RED_M)
            return ck[s].copy().move_to([LOOP[0], CLOCK_Y, 0]).set_z_index(3)

        clk = always_redraw(make_clock)
        self.steps("In Redis, client A sends a Lua script, a small program that Redis runs as one command. This one spins for 1.5 seconds.", [
            (lambda: [FadeOut(pile), *self.cstroke(1, BLUE_M), *self.cstroke(2, BLUE_M), *self.uncap()], 0.5),
            "a Lua script",
            (lambda: [*self.cmd(0, "EVAL busy 1500 ms", RED_M), *self.cstroke(0, RED_M)], 0.5),
            "runs as one command",
            (lambda: [self.to_loop(0, RED_M)[0], *self.lcolor(RED_M), *self.lstate("inside the script", "EVAL (1,500 ms)", RED_M, RED_M),
                      *step_lab(3)], 0.7),
            "This one spins",
            (lambda: [*self.drop("clock"), FadeIn(clk)], 0.3),
        ])
        self.lab["clock"] = clk
        parked = {}

        def park():
            anim, d = dot_run([CX + CW / 2, CY[1], 0], [SRV["x0"] - 0.12, CY[1], 0], RED_M, 0.5, stay=True)
            parked["d"] = d
            return [anim]

        self.steps("At 300 milliseconds, B sends GET payment:42. The only thread that could read it is busy inside the script. B waits.", [
            (lambda: [tr.animate(rate_func=linear).set_value(300)], 0.9),
            "B sends",
            (lambda: [*self.cmd(1, "GET payment:42")], 0.4),
            (park, 0.5),
            "busy inside",
            (lambda: [outline(self.loop, RED_M, 0.08)], 0.8),
            "B waits",
            (lambda: [*self.cstroke(1, RED_M), *self.cap("B's command sits unread", RED_M)], 0.5),
        ])
        self.steps("At 1,500 milliseconds the script returns, and B finally gets its half a microsecond of work, 1,200 milliseconds late.", [
            (lambda: [tr.animate(rate_func=linear).set_value(1500)], 1.6),
            (lambda: [*self.lcolor(YELLOW_M), *self.cstroke(0, BLUE_M), *self.cmd(0, "EVAL busy 1500 ms"), *self.reply(0, "1")], 0.5),
            "B finally",
            (lambda: [MoveAlongPath(parked["d"], Line(parked["d"].get_center(), [LOOP[0] - LW / 2, 0, 0]), rate_func=smooth),
                      *self.lstate("GET payment:42", None, WHITE, mono_a=True)], 0.5),
            (lambda: [FadeOut(parked["d"]), outline(VGroup(key_m[3], self.lab["v3"]), YELLOW_M, 0.1), *self.reply(1, '"approved"')], 0.6),
            "1,200 milliseconds late",
            (lambda: [*self.cap("answered 1,200 ms late", RED_M)], 0.5),
        ])
        self.steps("One 1.5-second command costs as much as three million GETs.", [
            "One 1.5",
            (lambda: [self.send(0), self.send(1), *self.cstroke(1, BLUE_M),
                      *self.cap("one command of 1.5 seconds = the time of 3 million GETs", WHITE)], 0.7),
        ])
        self.steps("Somewhere in that queue, a customer with one stamp is learning patience. So the danger is one long command.", [
            (lambda: [*self.lstate("asleep in epoll_wait", "using no CPU"), *self.drop("cmd0", "cmd1"), FadeOut(clk.clear_updaters()),
                      *step_lab(0)], 0.5),
            "So the danger",
            (lambda: self.cap("the danger: one long command", YELLOW_M), 0.6),
        ], after=0.3)
        self.lab.pop("clock", None)
        self.stamp("parcels")

        # ---------------- scene 8: guardrails ----------------
        self.steps("Two guardrails. First, watch for commands whose work grows with a key.", [
            (lambda: self.cap("1. watch for commands whose work grows with the key", WHITE), 0.6),
        ])

        def slow(s, why):
            return [*self.cmd(0, s, RED_M), *self.cstroke(0, RED_M), *self.lcolor(RED_M), *self.lstate(why, None, RED_M)]

        self.steps("KEYS *, which lists every key. HGETALL on a hash with a million fields. Deleting a huge key with DEL.", [
            (lambda: slow("KEYS *", "lists every key"), 0.6),
            "HGETALL",
            (lambda: slow("HGETALL (1M fields)", "reads a million fields"), 0.6),
            "Deleting",
            (lambda: slow("DEL huge-key", "frees all of it at once"), 0.6),
        ])
        self.steps("SLOWLOG GET lists every command over 10 milliseconds.", [
            "SLOWLOG GET",
            (lambda: [*self.cap(M("SLOWLOG GET: every command over 10 ms", 20, WHITE))], 0.6),
        ], after=0.3)

        diagram = VGroup(srv, srv_lab, mem, mem_lab, key_m, *self.crect, self.loop, *chips.values(), tick_r, tick_s)
        PX = [-3.32, 3.32]
        PW, PH, PY = 6.3, 1.75, 1.0
        panels = [RoundedRectangle(corner_radius=0.12, width=PW, height=PH, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1).move_to([x, PY, 0])
                  for x in PX]
        heads = [T(s, 24, GREY_B).move_to([x, PY + PH / 2 + 0.35, 0]) for s, x in zip(("Java", "Kotlin"), PX)]
        java = ['String v = redis.get("auths:today");', "long n = v == null ? 0 : Long.parseLong(v);",
                'redis.set("auths:today", String.valueOf(n + 1));']
        kot = ['val v: String? = redis.get("auths:today")', "val n = v?.toLong() ?: 0L", 'redis.set("auths:today", (n + 1).toString())']

        def code(lines, x, color=WHITE):
            g = VGroup(*[M(l, 15, color) for l in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            fit(g, PW - 0.6)
            return left_at(g, x - PW / 2 + 0.2, PY).set_z_index(3)

        cj, ck_ = code(java, PX[0]), code(kot, PX[1])
        self.steps("Second, atomic covers one command, not three.", [
            (lambda: [*self.drop("cmd0"), *self.cstroke(0, BLUE_M), *self.lcolor(YELLOW_M),
                      *self.lstate("asleep in epoll_wait", "using no CPU"), *self.cap("2. atomic covers one command, not three", WHITE)], 0.6),
            (lambda: [FadeOut(VGroup(diagram, *[self.lab[k] for k in list(self.lab)]))], 0.6),
        ])
        saved = dict(self.lab)
        self.lab = {}
        out_y = PY - PH / 2 - 0.5
        self.steps("A program with eight threads counts payments: GET the counter, add one, SET it back.", [
            (lambda: [*[FadeIn(p) for p in panels], *[FadeIn(h) for h in heads]], 0.5),
            "GET the counter",
            (lambda: [FadeIn(cj[0]), FadeIn(ck_[0])], 0.4),
            "add one",
            (lambda: [FadeIn(cj[1]), FadeIn(ck_[1])], 0.4),
            "SET it back",
            (lambda: [FadeIn(cj[2]), FadeIn(ck_[2])], 0.4),
        ])
        self.steps("After 8,000 calls it printed 1,611.", [
            "printed",
            (lambda: [*self.put("out", T("8,000 calls printed 1,611, then 1,654, then 1,628", 22, RED_M).move_to([0, out_y, 0]))], 0.6),
        ])
        self.steps("Between one GET and its SET, the loop ran other clients' commands.", [
            (lambda: [cj[0].animate.set_color(YELLOW_M), ck_[0].animate.set_color(YELLOW_M)], 0.4),
            "its SET",
            (lambda: [cj[2].animate.set_color(YELLOW_M), ck_[2].animate.set_color(YELLOW_M)], 0.4),
            "the loop ran",
            (lambda: self.cap("between GET and SET, other clients' commands run", WHITE), 0.6),
        ])
        cj2 = code(['redis.incr("auths:today");'], PX[0], GREEN_M)
        ck2 = code(['redis.incr("auths:today")'], PX[1], GREEN_M)
        self.steps("Send INCR instead, and the read, the add and the write are one command: 8,000, every run.", [
            "Send INCR",
            (lambda: [FadeOut(cj), FadeOut(ck_), FadeIn(cj2), FadeIn(ck2), *self.drop("out")], 0.7),
            "one command",
            (lambda: self.cap("INCR: the read, the add and the write in one command", WHITE), 0.5),
            "8,000",
            (lambda: [*self.put("out", T("8,000 calls printed 8000, on every run", 22, GREEN_M).move_to([0, out_y, 0]))], 0.5),
        ], after=0.4)
        self.stamp("code")

        # ---------------- scene 9: the moral, and a check ----------------
        self.lab = {**saved, **{k: v for k, v in self.lab.items() if k == "out"}}
        self.steps("So the moral of the story. One thread runs every command to the end.", [
            (lambda: [FadeOut(VGroup(*panels, *heads, cj2, ck2)), *self.drop("out")], 0.5),
            (lambda: [FadeIn(diagram), *[FadeIn(m) for k, m in self.lab.items()]], 0.7),
            "One thread runs",
            (lambda: self.cap("one thread runs every command to the end", YELLOW_M, 26), 0.6),
        ])
        self.steps("Each command is atomic, with no locks, and one slow command makes everyone wait.", [
            "atomic",
            (lambda: [outline(chips["risky"], GREEN_M, 0.06)], 0.6),
            "one slow command",
            (lambda: [outline(chips["slow"], RED_M, 0.06)], 0.6),
        ], after=0.3)
        self.steps("One quick check. A script runs for two seconds, and C asks for card:9, a key the script never touches. "
                   "Does C wait? Pause and think.", [
            (lambda: [*self.uncap(), *self.cmd(0, "EVAL (2 seconds)", RED_M), *self.cstroke(0, RED_M), *self.lcolor(RED_M),
                      *self.lstate("inside the script", None, RED_M)], 0.6),
            "C asks",
            (lambda: [*self.cmd(2, "GET card:9")], 0.4),
            "never touches",
            (lambda: [outline(VGroup(key_m[2], self.lab["v2"]), GREY_B, 0.1)], 0.8),
            "Pause and think",
            (lambda: self.cap("does C wait?  pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Yes. One job at a time, whatever parcel you came for.", [
            (lambda: [*self.uncap(), *self.cstroke(2, RED_M), *self.reply(2, "waiting", RED_M)], 0.6),
            "whatever parcel",
            (lambda: self.cap("yes: one job at a time, whatever key you came for", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("one thread, every command to the end", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
