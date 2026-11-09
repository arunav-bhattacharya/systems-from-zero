from sfz import *

PX, PY, PW, PH = -4.3, 0.95, 3.6, 3.9      # the fraud check pod and its grid of requests
RX, RY = 3.4, 2.25                          # Redis
DX, DY = 3.4, -0.25                         # the database
SW, SH = 3.6, 1.5                           # Redis and database boxes
AXY, EX, UPS = -2.95, 4.2, 4.5              # timeline: axis height, expiry, units per second
DELTA = 0.2                                 # one load: 200 ms


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


def store(title, x, y, color, sub, status, scolor=GREY_B):
    r = RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to([x, y, 0])
    return VGroup(r, T(title, 24).move_to([x, y + 0.42, 0]), sub.move_to([x, y + 0.02, 0]), T(status, 19, scolor).move_to([x, y - 0.4, 0]))


def status(x, y, s, color=GREY_B):
    return T(s, 19, color).move_to([x, y - 0.4, 0])


def sub(x, y, s, color=GREY_B):
    return T(s, 18, color).move_to([x, y + 0.02, 0])


def pod_status(s, color=GREY_B):
    return T(s, 19, color).move_to([PX, PY - PH / 2 + 0.36, 0])


def tx(left):
    """x on the timeline for a moment `left` seconds before the expiry."""
    return EX - left * UPS


class CacheStampede(Base):
    """cache-06, section 3: merchant:m-17 read 100 times a second in one pod; its TTL ends, 100 requests miss and run
    the same 200 ms query 100 times (pool of 20: 80 wait). Single-flight: the first miss puts a future in a map and loads,
    99 wait on it, one query. Then section 4's fix: refresh early at random (XFetch), so one read reloads before expiry."""

    def construct(self):
        self.title_card("Cache stampedes", "a hot key expires, and a hundred requests miss at once")

        pod = RoundedRectangle(corner_radius=0.16, width=PW, height=PH, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        pod.move_to([PX, PY, 0])
        ptitle = T("fraud check, one pod", 22, GREY_B).move_to([PX, PY + PH / 2 - 0.33, 0])
        grid = VGroup(*[Dot(radius=0.055, color=GREY_C) for _ in range(100)]).arrange_in_grid(10, 10, buff=0.13)
        grid.move_to([PX, PY + 0.1, 0])
        pst = pod_status("100 reads a second")
        redis = store("Redis", RX, RY, GREEN_M, M("merchant:m-17", 19), "cached", GREEN_M)
        get = Arrow([PX + PW / 2 + 0.1, RY, 0], [RX - SW / 2 - 0.1, RY, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.06)
        glab = M("GET merchant:m-17", 16, GREY_B).next_to(get, UP, buff=0.14)
        self.steps("The fraud check reads one merchant's profile from Redis about a hundred times a second. "
                   "On a sale day, every read is a hit.", [
            (lambda: [FadeIn(pod), FadeIn(ptitle)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(d) for d in grid], lag_ratio=0.01), FadeIn(pst)], 1.0),
            "from Redis",
            (lambda: [FadeIn(redis), GrowArrow(get), FadeIn(glab)], 0.9),
            "every read is a hit",
            (lambda: [grid.animate.set_color(GREEN_M), Transform(pst, pod_status("100 reads a second, all hits", GREEN_M)),
                      LaggedStart(*[flow(get, GREEN_M, 0.5) for _ in range(5)], lag_ratio=0.3)], 1.4),
        ])

        self.steps("Each copy in Redis has a time to live. When that runs out, Redis deletes the key.", [
            (lambda: [Transform(redis[3], status(RX, RY, "time to live: 2 s left", GREEN_M))], 0.7),
            "When that runs out",
            (lambda: [Transform(redis[3], status(RX, RY, "time to live: 1 s left", GREEN_M))], 0.5),
            0.3,
            (lambda: [Transform(redis[3], status(RX, RY, "expired, key deleted", RED_M)),
                      redis[0].animate.set_stroke(RED_M).set_fill(fill(RED_M), 1)], 0.7),
        ])

        db = store("database", DX, DY, BLUE_M, sub(DX, DY, "200 ms a query"), "queries running: 0")
        sel = Arrow([PX + PW / 2 + 0.1, DY, 0], [DX - SW / 2 - 0.1, DY, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.06)
        slab = T("on a miss, query the database", 18, GREY_B).next_to(sel, UP, buff=0.14)
        self.steps("Loading the row again takes 200 milliseconds. Before any load can finish, "
                   "a hundred requests ask for the key, and all of them miss.", [
            (lambda: [FadeIn(db), GrowArrow(sel), FadeIn(slab)], 1.0),
            "a hundred requests",
            (lambda: [LaggedStart(*[d.animate.set_color(RED_M) for d in grid], lag_ratio=0.02),
                      Transform(pst, pod_status("100 misses", RED_M))], 1.4),
        ])

        self.steps("None of them knows about the others, so each one queries the database: the same query, a hundred times.", [
            "so each one",
            (lambda: [LaggedStart(*[flow(sel, RED_M, 0.6) for _ in range(14)], lag_ratio=0.12)], 1.8),
            (lambda: [Transform(db[3], status(DX, DY, "the same query, 100 times", RED_M)),
                      db[0].animate.set_stroke(RED_M)], 0.7),
        ])

        stamp = chip("cache stampede: 100 misses, 100 queries", RED_M, 18).move_to([DX, -1.6, 0])
        self.steps("Its pool has 20 connections, so 80 requests wait in line, and every other query waits behind them. "
                   "This is a cache stampede.", [
            (lambda: [Transform(db[2], sub(DX, DY, "pool of 20 connections")),
                      Transform(db[3], status(DX, DY, "20 running, 80 waiting", RED_M))], 0.9),
            "and every other",
            (lambda: [glow(db[0], RED_M, 1.04)], 1.0),
            "This is a cache",
            (lambda: [FadeIn(stamp, shift=0.15 * UP)], 0.8),
        ])

        lead = grid[0]
        fut = mbox("map: m-17 → future", GOLD_M, h=0.46, size=15).move_to(pst)
        self.steps("Single-flight fixes it inside one process. The first request to miss puts a placeholder for the result, "
                   "called a future, in a map. Only this leader queries the database.", [
            (lambda: [FadeOut(stamp), grid.animate.set_color(GREY_C), Transform(pst, pod_status("100 reads a second")),
                      Transform(db[2], sub(DX, DY, "200 ms a query")), Transform(db[3], status(DX, DY, "queries running: 0")),
                      db[0].animate.set_stroke(BLUE_M)], 0.9),
            "The first request",
            (lambda: [lead.animate.set_color(GOLD_M).scale(1.8)], 0.6),
            "in a map",
            (lambda: [FadeOut(pst), FadeIn(fut)], 0.7),
            "Only this leader",
            (lambda: [flow(sel, GOLD_M, 0.8)], 0.8),
            (lambda: [Transform(db[3], status(DX, DY, "queries running: 1", GOLD_M))], 0.5),
        ])

        leg = VGroup(Dot(radius=0.08, color=GOLD_M), T("leader", 18, GREY_B), Dot(radius=0.07, color=PURPLE_M).shift(0.3 * RIGHT),
                     T("waiting on the future", 18, GREY_B)).arrange(RIGHT, buff=0.14)
        leg[2].shift(0.22 * RIGHT)
        leg[3].shift(0.22 * RIGHT)
        leg.move_to([PX, -1.5, 0])
        self.steps("The other 99 find the future in the map and wait on it.", [
            (lambda: [LaggedStart(*[d.animate.set_color(PURPLE_M) for d in grid[1:]], lag_ratio=0.02)], 1.4),
            "and wait",
            (lambda: [FadeIn(leg)], 0.6),
            (lambda: [glow(fut[0], GOLD_M, 1.05)], 0.9),
        ])

        self.steps("After 200 milliseconds the leader writes the row back to Redis and completes the future. "
                   "All 99 wake up with the same row.", [
            (lambda: [flow(sel, GOLD_M, 0.8, back=True)], 0.8),
            "writes the row",
            (lambda: [flow(get, GOLD_M, 0.8)], 0.8),
            (lambda: [redis[0].animate.set_stroke(GREEN_M).set_fill(fill(GREEN_M), 1),
                      Transform(redis[3], status(RX, RY, "cached again", GREEN_M))], 0.5),
            "and completes",
            (lambda: [Transform(fut, mbox("map: m-17 → row", GREEN_M, h=0.46, size=15).move_to(fut))], 0.6),
            "All 99",
            (lambda: [LaggedStart(*[d.animate.set_color(GREEN_M) for d in grid], lag_ratio=0.015),
                      Transform(db[3], status(DX, DY, "1 query in total", GREEN_M))], 1.3),
        ])

        one = chip("single-flight: 1 query, not 100", GREEN_M, 18).move_to([DX, -1.6, 0])
        pods = chip("20 pods: still 20 queries", GREY_B, 18).move_to([DX, -2.35, 0])
        self.steps("That's one query instead of a hundred. "
                   "But the map lives in one process, so twenty pods still send twenty queries.", [
            (lambda: [FadeIn(one, shift=0.15 * UP)], 0.8),
            "But the map",
            (lambda: [glow(fut[0], GREY_B, 1.05)], 0.9),
            "so twenty pods",
            (lambda: [FadeIn(pods, shift=0.15 * UP)], 0.8),
        ])

        # ---- refresh early, at random ------------------------------------------------------------------------------
        axis = Line([tx(2.2), AXY, 0], [5.6, AXY, 0], stroke_width=2.5, color=GREY_B)
        ticks = VGroup(*[Line([tx(i * 0.05), AXY - 0.1, 0], [tx(i * 0.05), AXY + 0.1, 0], stroke_width=2, color=GREY_C)
                         for i in range(1, 41)])
        exp = DashedLine([EX, AXY - 0.22, 0], [EX, AXY + 0.78, 0], dash_length=0.08, stroke_width=2.5, color=RED_M)
        elab = T("expiry", 18, RED_M).move_to([EX, AXY + 0.98, 0])
        lab2 = T("2 s left", 17, GREY_B).move_to([tx(2.0), AXY - 0.36, 0])
        lab1 = T("1 s left", 17, GREY_B).move_to([tx(1.0), AXY - 0.36, 0])
        rlab = T("reads of the key", 17, GREY_B).move_to([tx(1.55), AXY + 0.32, 0])
        win = Rectangle(width=0.5 * UPS, height=0.5, stroke_width=0).set_fill(GOLD_M, 0.22)
        win.move_to([EX - 0.25 * UPS, AXY + 0.08, 0])
        wlab = chip("reload in the last half second: 50 reloads", GOLD_M, 18).move_to([-0.45, -1.6, 0])
        self.steps("Better still, refresh the key before it expires. "
                   "But if every read in the last half second reloads, that's 50 reloads.", [
            (lambda: [FadeOut(one), FadeOut(pods), FadeOut(leg), FadeOut(fut), FadeIn(pst), lead.animate.scale(1 / 1.8)], 0.8),
            (lambda: [Create(axis), FadeIn(lab2), FadeIn(lab1), Create(exp), FadeIn(elab)], 1.0),
            (lambda: [LaggedStart(*[FadeIn(t) for t in ticks], lag_ratio=0.03), FadeIn(rlab)], 0.9),
            "But if every",
            (lambda: [FadeIn(win), *[t.animate.set_color(GOLD_M) for t in ticks[:10]]], 0.8),
            "that's 50",
            (lambda: [FadeIn(wlab, shift=0.15 * UP)], 0.7),
        ])

        self.steps("So each read decides alone, at random. Next to the row, Redis keeps how long the last load took, "
                   "200 milliseconds. Call it delta.", [
            (lambda: [FadeOut(win), FadeOut(wlab), *[t.animate.set_color(GREY_C) for t in ticks[:10]]], 0.7),
            "Next to the row",
            (lambda: [Transform(redis[3], status(RX, RY, "last load took 200 ms", GREEN_M))], 0.8),
            "Call it delta",
            (lambda: [Transform(redis[3], status(RX, RY, "delta = 200 ms", GOLD_M)), glow(redis[0], GOLD_M, 1.04)], 0.9),
        ])

        rule = chip("refresh if now + delta × r is past the expiry", GREY_B, 18).move_to([-0.45, -1.6, 0])
        AY_ = AXY + 0.42

        def pretend(left, r, color):
            x0 = tx(left)
            mark = Line([x0, AXY - 0.16, 0], [x0, AXY + 0.16, 0], stroke_width=4, color=color)
            a = Arrow([x0, AY_, 0], [x0 + r * DELTA * UPS, AY_, 0], buff=0, stroke_width=3, color=color,
                      max_tip_length_to_length_ratio=0.12)
            return mark, a

        ma, aa = pretend(1.6, 1.2, GREY_A)
        mb, ab = pretend(1.0, 2.0, GREY_A)
        self.steps("Each read draws a random number, usually about one, and pretends it's that many deltas later. "
                   "Far from the expiry, that falls short.", [
            (lambda: [FadeOut(rlab), FadeIn(rule, shift=0.15 * UP)], 0.8),
            "and pretends",
            (lambda: [FadeIn(ma)], 0.3),
            (lambda: [GrowArrow(aa)], 0.8),
            "Far from",
            (lambda: [FadeOut(aa), FadeOut(ma), FadeIn(mb)], 0.5),
            (lambda: [GrowArrow(ab)], 0.8),
            (lambda: [FadeOut(ab), FadeOut(mb)], 0.5),
        ])

        mc, ac = pretend(0.6, 3.2, GOLD_M)
        late = VGroup(*[t for t in ticks if t.get_center()[0] > tx(0.6) + 0.01])
        self.steps("Near the expiry the odds climb fast. Usually one read lands past it and refreshes early, "
                   "while the others keep reading the old row.", [
            (lambda: [FadeIn(mc)], 0.3),
            (lambda: [GrowArrow(ac)], 0.9),
            "and refreshes early",
            (lambda: [flow(sel, GOLD_M, 0.6), Transform(db[3], status(DX, DY, "1 query, early", GOLD_M))], 0.8),
            (lambda: [flow(sel, GOLD_M, 0.6, back=True)], 0.6),
            (lambda: [flow(get, GOLD_M, 0.6)], 0.6),
            "while the others",
            (lambda: [late.animate.set_color(GREEN_M), Transform(redis[3], status(RX, RY, "refreshed, never expired", GREEN_M)),
                      exp.animate.set_color(GREY_D), elab.animate.set_color(GREY_D)], 1.0),
        ])

        self.steps("A hot key's misses arrive together. Let one request load it, "
                   "or refresh it just before it expires.", [
            (lambda: [glow(db[0], GREEN_M, 1.04)], 0.9),
            "Let one request",
            (lambda: [lead.animate(rate_func=there_and_back).scale(2.2).set_color(GOLD_M)], 1.0),
            "or refresh it",
            (lambda: [ac.animate(rate_func=there_and_back).set_stroke(width=7), glow(redis[0], GREEN_M, 1.04)], 1.0),
        ])
        self.wait(0.6)
