from sfz import *

SAY.insert(0, (r"\bm-17\b", "M seventeen"))
SAY.insert(0, (r"\block:merchant:m-17\b", "lock, merchant, M seventeen"))
SAY.insert(0, (r"\bNX\b", "N X"))
SAY.insert(0, (r"\bPX\b", "P X"))
SAY.insert(0, (r"\bputIfAbsent\b", "put if absent"))
SAY.insert(0, (r"\bConcurrentHashMap\b", "concurrent hash map"))
SAY.insert(0, (r"\bCompletableFuture\b", "completable future"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
AP_X0, AP_X1, AP_TOP, AP_BOT = -6.5, -2.6, 2.35, -1.35      # the app: customers, then requests
AP_CX, AP_CY = (AP_X0 + AP_X1) / 2, (AP_TOP + AP_BOT) / 2
RD_X0, RD_X1, RD_TOP, RD_BOT = -1.6, 1.6, 2.35, 0.0         # Redis: the shelf
DB_X0, DB_X1, DB_TOP, DB_BOT = 2.6, 6.5, 2.35, -1.35        # the database: the baker
DB_CX = (DB_X0 + DB_X1) / 2
GET_Y, LANE_Y = 1.5, -0.92
MAP_C, MAP_W, MAP_H = np.array([0.0, LANE_Y, 0]), 2.8, 0.95
TITLE_Y, SUB_Y = 2.06, 1.74
CLOCK_Y, SCORE_Y, BAR_Y, CAP_Y = 3.2, -2.15, -2.72, -3.27
STRIP_Y = [1.47, 0.673, -0.123, -0.92]
STRIP_H = 0.66


def grid_pos(i):
    r, c = divmod(i, 10)
    return np.array([AP_CX - 1.26 + 0.28 * c, 1.34 - 0.28 * r, 0])


def strip_pos(i):
    k, j = divmod(i, 25)
    r, c = divmod(j, 9)
    return np.array([-5.25 + 0.19 * c, STRIP_Y[k] + 0.18 - 0.18 * r, 0])


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


def loaf():
    body = RoundedRectangle(corner_radius=0.22, width=1.3, height=0.55, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M, 0.35), 1)
    cuts = VGroup(*[Line([x - 0.08, -0.14, 0], [x + 0.08, 0.14, 0], stroke_width=3, color=GOLD_M) for x in (-0.33, 0, 0.33)])
    return VGroup(body, cuts)


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


JAVA = ["// inside one copy: one leader per key",
        "var mine = new CompletableFuture<String>();",
        "var running = flights.putIfAbsent(KEY, mine);",
        "if (running != null) return running.join();",
        "",
        "// across copies: one sign in Redis",
        "boolean leader = redis.set(\"lock:\" + KEY, token,",
        "    SetParams.setParams().nx().px(2_000)) != null;"]
KOTLIN = ["// inside one copy: one leader per key",
          "val mine = CompletableFuture<String>()",
          "flights.putIfAbsent(KEY, mine)",
          "    ?.let { return it.join() }",
          "",
          "// across copies: one sign in Redis",
          "val leader = redis.set(\"lock:$KEY\", token,",
          "    SetParams.setParams().nx().px(2_000)) != null"]


class CacheStampede(Base):
    """cache-06, section 3. The bakery: the shelf (Redis), the baker (the database), a loaf with a sell-by time (a copy
    with a TTL). merchant:m-17, 100 reads a second, expires at ten; a reload takes 200 ms. Predict the queries: 100, not
    1; a pool of 20, 80 wait: the stampede. Single-flight ("I've asked, wait here"): one leader per key, 99 join its
    future, 1 query, about 210 ms. Four copies of the app: 4 queries, because no copy sees another's map. A sign on a
    shared board: SET lock:merchant:m-17 <token> NX PX 2000, 1 query. The guardrail (it only saves work; keep both),
    the code in Java and Kotlin, the moral, and a check (20 copies, single-flight only: 20)."""

    # --- small state helpers: each returns animations and records what is on screen ---
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

    def drop(self, key):
        old = self.lab.pop(key, None)
        return [FadeOut(old)] if old is not None else []

    def clock(self, s):
        return self.put("clock", M(s, 28, GREY_B).move_to([0, CLOCK_Y, 0]))

    def rd_status(self, s, color):
        return self.put("rds", fit(T(s, 19, color), 2.9).move_to([0, 0.95, 0]))

    def db_running(self, n, color=WHITE):
        return self.put("dbq", T(f"queries running: {n}", 21, color).move_to([DB_CX, 1.25, 0]))

    def db_wait(self, n, color=WHITE):
        return self.put("dbw", T(f"waiting in line: {n}", 21, color).move_to([DB_CX, -0.6, 0]))

    def count_up(self, key, fmt, a, b, color, y):
        holder = self.lab[key]

        def upd(m, alpha):
            v = int(round(a + (b - a) * alpha))
            if getattr(m, "_v", None) == v:
                return
            m._v = v
            m.become(T(fmt.format(v), 21, color if v else WHITE).move_to([DB_CX, y, 0]))
        return UpdateFromAlphaFunc(holder, upd)

    def score(self, k):
        c = self.score_chips[k]
        self.scores[k] = c
        anims = [FadeIn(c, shift=0.1 * UP)]
        if self.score_lab not in self.mobjects:
            anims.append(FadeIn(self.score_lab))
        return anims

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.scores = [None] * 4
        self.score_lab = T("database calls:", 20, GREY_B)
        self.score_chips = [chip(s, c, 20) for s, c in [("no protection: 100", RED_M), ("single-flight: 1", GREEN_M),
                                                        ("4 copies: 4", GOLD_M), ("lock: 1", YELLOW_M)]]
        VGroup(self.score_lab, *self.score_chips).arrange(RIGHT, buff=0.3).move_to([0, SCORE_Y, 0])
        self.title_card("Can a cache make the database busier?", "a stampede, single-flight, and a sign on a shared board")

        # ---------------- the pieces ----------------
        db = frame(DB_X0, DB_X1, DB_TOP, DB_BOT, BLUE_M)
        db_title = T("database", 26).move_to([DB_CX, TITLE_Y, 0])
        app = frame(AP_X0, AP_X1, AP_TOP, AP_BOT, WHITE)
        rd = frame(RD_X0, RD_X1, RD_TOP, RD_BOT, TEAL_M)
        dots = VGroup(*[Dot(radius=0.07, color=GREY_B).move_to(grid_pos(i)) for i in range(100)]).set_z_index(4)
        a_get = harrow(AP_X1 + 0.06, RD_X0 - 0.06, GET_Y)
        a_lane = harrow(AP_X1 + 0.06, DB_X0 - 0.06, LANE_Y)
        slots = VGroup(*[Square(0.24, stroke_color=BLUE_M, stroke_width=2).set_fill(BLACK, 1).move_to(
            [DB_CX - 1.44 + 0.32 * (k % 10), 0.6 - 0.34 * (k // 10), 0]) for k in range(20)])
        pool_lab = T("pool: 20 connections", 17, GREY_B).move_to([DB_CX, -0.12, 0])
        lane_in = np.array([DB_X0 - 0.1, LANE_Y, 0])
        lane_out = np.array([AP_X1 + 0.1, LANE_Y, 0])
        get_out, get_in = np.array([AP_X1 + 0.1, GET_Y, 0]), np.array([RD_X0 - 0.1, GET_Y, 0])

        # ---------------- scene 1: the question ----------------
        self.steps("A cache is there to protect the database. Every answer it gives is a query saved.", [
            (lambda: self.cap("a cache: every answer it gives is a query saved"), 0.5),
            "protect the database",
            (lambda: [FadeIn(db), FadeIn(db_title)], 0.8),
        ])
        burst_from = np.array([-1.5, LANE_Y, 0])
        self.steps("So can a cache ever make the database busier? At ten one morning, the database gets the same query a hundred times at once. And the cache is the reason.", [
            (lambda: self.cap("can a cache make the database busier?", WHITE), 0.5),
            "At ten",
            (lambda: [LaggedStart(*[run_pts([burst_from + [0, 0.5 * np.sin(k), 0], lane_in], RED_M, 0.5) for k in range(40)],
                                  lag_ratio=0.06)], 2.4),
            (lambda: self.db_running(100, RED_M), 0.4),
            "the cache is the reason",
            (lambda: self.cap("the same query, 100 times: and the cache is the reason", RED_M), 0.5),
        ])

        # ---------------- scene 2: the bakery ----------------
        lf = loaf().move_to([0, 1.05, 0])
        self.steps("Picture a bakery with a shelf of bread by the door. Customers take a loaf and go.", [
            (lambda: [*self.uncap(), *self.drop("dbq"), FadeOut(db_title)], 0.5),
            "a shelf",
            (lambda: [FadeIn(rd), *self.put("rdt", T("shelf", 26).move_to([0, TITLE_Y, 0])), FadeIn(lf, shift=0.1 * DOWN)], 0.8),
            "Customers",
            (lambda: [FadeIn(app), *self.put("apt", T("customers", 26).move_to([AP_CX, TITLE_Y, 0])),
                      LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.01)], 1.2),
            (lambda: [GrowArrow(a_get)], 0.4),
            (lambda: [run_pts([get_out, get_in], WHITE, 0.5)], 0.6),
        ])
        self.steps("When the shelf is empty, a customer asks the baker at the back, who takes a while to bake one.", [
            "the baker",
            (lambda: [*self.put("dbt", T("baker", 26).move_to([DB_CX, TITLE_Y, 0])), GrowArrow(a_lane)], 0.7),
            "takes a while",
            (lambda: [run_pts([lane_out, lane_in], WHITE, 1.2)], 1.3),
        ])
        key = M("merchant:m-17", 20).move_to([0, 1.32, 0])
        ttl_bar = Line([-1.25, 0.62, 0], [1.25, 0.62, 0], stroke_width=5, color=GREEN_M)
        self.steps("In the payments app, the shelf is Redis, a program that keeps data in memory. It holds copies of rows from the slower database, the baker.", [
            "Redis",
            (lambda: [*self.put("rdt", T("Redis", 26).move_to([0, TITLE_Y, 0])),
                      *self.put("rds_sub", T("the shelf", 17, GREY_B).move_to([0, SUB_Y, 0]))], 0.7),
            "the slower database",
            (lambda: [*self.put("dbt", T("database", 26).move_to([DB_CX, TITLE_Y, 0])),
                      *self.put("db_sub", T("the baker: 200 ms a load", 17, GREY_B).move_to([DB_CX, SUB_Y, 0]))], 0.7),
        ])
        self.steps("A loaf is one copy of a row, with a sell-by time: its TTL, or time to live. When it runs out, the copy is gone.", [
            (lambda: [ReplacementTransform(lf, key)], 0.8),
            "sell-by time",
            (lambda: [Create(ttl_bar), *self.rd_status("cached, TTL 1 hour", GREEN_M)], 0.6),
            "When it runs out",
            (lambda: [ttl_bar.animate.put_start_and_end_on([-1.25, 0.62, 0], [-1.2, 0.62, 0]).set_color(RED_M)], 1.0),
            (lambda: [FadeOut(ttl_bar), *self.rd_status("gone", RED_M), key.animate.set_opacity(0.3)], 0.4),
        ])
        self.steps("The rule: ask Redis first. If the copy is there, that's a hit. If not, that's a miss: load the row from the database, put it back in Redis, and go.", [
            (lambda: [*self.put("apt", T("one copy of the app", 24).move_to([AP_CX, TITLE_Y, 0])),
                      *self.put("ap_sub", T("each dot: a request", 17, GREY_B).move_to([AP_CX, SUB_Y, 0])),
                      *self.cap("cache-aside: ask Redis first; on a miss, load and put it back")], 0.6),
            "that's a hit",
            (lambda: [key.animate.set_opacity(1), *self.rd_status("cached", GREEN_M),
                      run_pts([get_out, get_in], WHITE, 0.45)], 0.5),
            (lambda: [run_pts([get_in, get_out], GREEN_M, 0.45)], 0.5),
            "that's a miss",
            (lambda: [*self.rd_status("(nil)", RED_M), key.animate.set_opacity(0.3), run_pts([get_out, get_in], WHITE, 0.45)], 0.5),
            (lambda: [run_pts([get_in, get_out], RED_M, 0.45)], 0.5),
            "load the row",
            (lambda: [run_pts([lane_out, lane_in], WHITE, 0.7)], 0.75),
            (lambda: [run_pts([lane_in, lane_out], WHITE, 0.7)], 0.75),
            "put it back",
            (lambda: [run_pts([get_out, get_in], GREEN_M, 0.45)], 0.5),
            (lambda: [key.animate.set_opacity(1), *self.rd_status("cached", GREEN_M)], 0.3),
        ])

        # ---------------- scene 3: the busy shop ----------------
        def hits(n=10, rt=2.0):
            return [LaggedStart(*[Succession(run_pts([get_out, get_in], WHITE, 0.35), run_pts([get_in, get_out], GREEN_M, 0.35))
                                  for _ in range(n)], lag_ratio=0.15, run_time=rt)]

        ttl2 = Line([-1.25, 0.62, 0], [-0.9, 0.62, 0], stroke_width=5, color=GOLD_M)
        self.steps("Now take the busiest shop on a sale day, merchant m-17, read a hundred times a second.", [
            (lambda: [*self.uncap(), *self.clock("09:59:58.000"), glow(rd[0], TEAL_M, 1.02)], 0.6),
            "a hundred times",
            (lambda: [*self.cap("100 reads a second, from this one copy"), *hits(12, 2.4)], 2.4),
        ])
        self.steps("Every read is a hit, and the database never hears about it.", [
            (lambda: [*hits(8, 1.6), *self.rd_status("cached, TTL 2 s left", GREEN_M), Create(ttl2)], 1.6),
            "the database never",
            (lambda: [*self.db_running(0), *self.cap("a hit: about 0.3 ms. the database: 0 queries for this key")], 0.6),
        ])
        self.steps("Then, at ten o'clock, the TTL runs out. And loading the row takes 200 milliseconds.", [
            (lambda: [ttl2.animate.put_start_and_end_on([-1.25, 0.62, 0], [-1.22, 0.62, 0]).set_color(RED_M)], 1.0),
            (lambda: [FadeOut(ttl2), *self.clock("10:00:00.000"), *self.rd_status("expired", RED_M), key.animate.set_color(RED_M)], 0.5),
            "And loading",
            (lambda: [Indicate(self.lab["db_sub"], color=BLUE_M, scale_factor=1.15), *self.uncap()], 0.9),
        ])

        # ---------------- scene 4: predict, then the stampede ----------------
        self.steps("Within a few milliseconds, a hundred requests ask for the key, and all of them miss. Each one follows the rule. How many database queries? Pause and guess.", [
            (lambda: [*self.clock("10:00:00.005"), LaggedStart(*[run_pts([get_out, get_in], WHITE, 0.3) for _ in range(14)],
                                                                lag_ratio=0.08)], 1.4),
            "all of them miss",
            (lambda: [dots.animate.set_color(RED_M), *self.rd_status("(nil) x 100", RED_M)], 0.6),
            "Pause and guess",
            (lambda: self.cap("how many database queries? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The hopeful answer is one: the first request reloads it, and the rest find it in Redis. But the reload takes 200 milliseconds, and all hundred have already asked.", [
            (lambda: self.cap("the first one reloads it, and the rest find it in Redis?", PURPLE_M), 0.5),
            "But the reload",
            (lambda: [Indicate(self.lab["db_sub"], color=BLUE_M, scale_factor=1.15)], 0.8),
            "all hundred",
            (lambda: [LaggedStart(*[Indicate(d, color=RED_M, scale_factor=1.6) for d in dots], lag_ratio=0.01)], 1.2),
        ])
        q_hold = self.lab["dbq"]
        self.steps("None of them knows about the others, so each one queries the database: a hundred queries.", [
            (lambda: [*self.clock("10:00:00.010"), *self.cap("each one: query the database", RED_M)], 0.5),
            "so each one",
            (lambda: [LaggedStart(*[run_pts([lane_out + [0, 0.06 * ((k % 5) - 2), 0], lane_in], RED_M, 0.55) for k in range(100)],
                                  lag_ratio=0.03),
                      self.count_up("dbq", "queries running: {}", 0, 100, RED_M, 1.25)], 2.6),
            (lambda: [db[0].animate.set_stroke(RED_M)], 0.4),
        ])
        self.steps("With a pool of 20 database connections, 80 queries wait in line, and every other query waits behind them.", [
            (lambda: [Indicate(pool_lab, color=BLUE_M)] if pool_lab in self.mobjects else [FadeIn(slots), FadeIn(pool_lab)], 0.6),
            "a pool of 20",
            (lambda: [LaggedStart(*[s.animate.set_fill(GOLD_M, 0.9) for s in slots], lag_ratio=0.05)], 1.0),
            "80 queries",
            (lambda: [*self.db_wait(0)], 0.2),
            (lambda: [self.count_up("dbw", "waiting in line: {}", 0, 80, RED_M, -0.6)], 1.0),
            "every other query",
            (lambda: [*self.cap("pool of 20: 80 wait, and so does every other query", RED_M)], 0.5),
        ])
        self.steps("This is a cache stampede, also called a thundering herd: a hundred customers walking to the back of the bakery for the same loaf.", [
            (lambda: [*self.cap("a cache stampede (a thundering herd)", WHITE, 30)], 0.6),
            "a hundred customers",
            (lambda: [LaggedStart(*[d.animate(rate_func=there_and_back).shift(0.12 * RIGHT) for d in dots], lag_ratio=0.01)], 1.3),
        ])
        self.steps("The baker bakes the same bread a hundred times. Very fresh, and ninety nine times pointless.", [
            (lambda: self.score(0), 0.6),
        ], after=0.4)
        self.steps("So the moment a busy copy expires, the cache sends everyone at once.", [
            (lambda: self.cap("on average, a cache saves queries"), 0.5),
            "the cache sends",
            (lambda: self.cap("when a busy copy expires, it sends everyone at once", RED_M), 0.5),
        ])
        self.stamp("stampede")

        # ---------------- scene 5: I've asked, wait here ----------------
        mapb = VGroup(RoundedRectangle(corner_radius=0.12, width=MAP_W, height=MAP_H, stroke_color=GOLD_M, stroke_width=3)
                      .set_fill(fillc(GOLD_M), 1).move_to(MAP_C),
                      T("single-flight map", 17, GOLD_M).move_to(MAP_C + [0, 0.24, 0]))
        map_in, map_out = np.array([MAP_C[0] - MAP_W / 2 - 0.08, LANE_Y, 0]), np.array([MAP_C[0] + MAP_W / 2 + 0.08, LANE_Y, 0])

        def reset():
            return [*self.clock("10:00:00.005"), dots.animate.set_color(RED_M), db[0].animate.set_stroke(BLUE_M), key.animate.set_color(RED_M),
                    *[s.animate.set_fill(BLACK, 1) for s in slots], *self.db_running(0), *self.db_wait(0),
                    *self.rd_status("(nil)", RED_M)]

        self.steps("What we want is what polite customers do. The first one says: I've asked, wait here. Let's replay ten o'clock.", [
            (lambda: self.cap("the first customer: I've asked, wait here", YELLOW_M), 0.5),
            "Let's replay",
            (lambda: reset(), 0.8),
        ])
        self.steps("Inside one program, each request runs as a thread, one path of work. The threads share a map, a table of keys and values: in Java, a ConcurrentHashMap.", [
            (lambda: self.cap("a thread: one path of work, running alongside others"), 0.5),
            (lambda: [LaggedStart(*[Indicate(d, color=WHITE, scale_factor=1.6) for d in dots[:10]], lag_ratio=0.1)], 1.0),
            "share a map",
            (lambda: [FadeIn(mapb, shift=0.15 * DOWN)], 0.8),
            "in Java",
            (lambda: self.cap("ConcurrentHashMap: a map many threads can use at once"), 0.5),
        ])
        fut = M("m-17: a future", 16, YELLOW_M).move_to(MAP_C + [0, -0.17, 0])
        self.steps("Each thread that misses makes an empty box for the result, a CompletableFuture, and tries putIfAbsent: add my box under the shop's key, only if nothing is there yet.", [
            (lambda: self.cap("CompletableFuture: a box that will hold the result later"), 0.5),
            "tries putIfAbsent",
            (lambda: [LaggedStart(*[run_pts([lane_out + [0, 0.05 * ((k % 5) - 2), 0], map_in], WHITE, 0.45) for k in range(12)],
                                  lag_ratio=0.08), *self.cap("putIfAbsent: add it only if the key has no entry yet")], 1.3),
        ])
        self.steps("The first thread succeeds. It's the leader, and it queries the database.", [
            (lambda: [dots[0].animate.set_color(YELLOW_M).scale(1.5), FadeIn(fut)], 0.6),
            "the leader",
            (lambda: [*self.cap("the first to put its box in: the leader", YELLOW_M)], 0.4),
            "queries the database",
            (lambda: [run_pts([map_out, lane_in], YELLOW_M, 0.6)], 0.65),
            (lambda: [*self.db_running(1, YELLOW_M), slots[0].animate.set_fill(GOLD_M, 0.9)], 0.3),
        ])
        waiting = T("99 wait on its future", 17, GREY_B).move_to([AP_CX, SUB_Y, 0])
        self.steps("The other 99 find the leader's box already there, and wait on it.", [
            (lambda: [dots[1:].animate.set_color(GREY_D), *self.put("ap_sub", waiting)], 0.8),
            (lambda: [glow(mapb[0], GOLD_M, 1.03)], 0.7),
        ])
        self.steps("After 200 milliseconds, the leader puts the row in Redis and in its box.", [
            (lambda: [*self.clock("10:00:00.210")], 0.5),
            (lambda: [run_pts([lane_in, map_out], YELLOW_M, 0.6), *self.db_running(0), slots[0].animate.set_fill(BLACK, 1)], 0.65),
            "puts the row in Redis",
            (lambda: [run_pts([get_out, get_in], GREEN_M, 0.5)], 0.55),
            (lambda: [key.animate.set_color(WHITE), *self.rd_status("cached again", GREEN_M)], 0.3),
            "in its box",
            (lambda: [Transform(fut, M("m-17: the row", 16, GREEN_M).move_to(fut))], 0.4),
        ])
        self.steps("All 99 wake up with the same value, and the leader clears its entry.", [
            (lambda: [LaggedStart(*[d.animate.set_color(GREEN_M) for d in dots], lag_ratio=0.008), dots[0].animate.scale(1 / 1.5)], 1.2),
            "clears its entry",
            (lambda: [FadeOut(fut), *self.put("ap_sub", T("100 replies, 1 query", 17, GREEN_M).move_to([AP_CX, SUB_Y, 0]))], 0.6),
        ])
        self.steps("One query instead of a hundred, and everyone waited about 210 milliseconds. This is single-flight: one load in flight per key.", [
            (lambda: self.score(1), 0.6),
            "everyone waited",
            (lambda: self.cap("1 query instead of 100; everyone waited about 210 ms"), 0.5),
            "This is single",
            (lambda: self.cap("single-flight: one load in flight per key", GOLD_M, 30), 0.5),
        ])
        self.steps("A hundred customers, one loaf, and a baker who gets to sit down.", [
            (lambda: [glow(db[0], BLUE_M, 1.02)], 0.8),
        ], after=0.4)
        self.stamp("single-flight")

        # ---------------- scene 6: four copies ----------------
        strips = VGroup(*[frame(-6.35, -2.75, y + STRIP_H / 2, y - STRIP_H / 2, GREY_B, 0.1) for y in STRIP_Y]).set_z_index(2)
        strip_labs = VGroup(*[left_at(T(f"copy {k + 1}", 16, GREY_B), -6.2, y) for k, y in enumerate(STRIP_Y)]).set_z_index(3)
        maps = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.06, width=0.62, height=0.34, stroke_color=GOLD_M, stroke_width=2)
                               .set_fill(fillc(GOLD_M), 1), T("map", 14, GOLD_M)).move_to([-3.2, y, 0]) for y in STRIP_Y]).set_z_index(3)
        self.steps("So far so good. But a busy app runs many copies of the same program, so one can fail and the work is shared.", [
            (lambda: [*self.uncap(), *self.put("apt", T("4 copies of the app", 24).move_to([AP_CX, TITLE_Y, 0])),
                      *self.drop("ap_sub")], 0.6),
            "many copies",
            (lambda: [FadeIn(strips), FadeIn(strip_labs), *[d.animate.move_to(strip_pos(i)).scale(0.85) for i, d in enumerate(dots)]], 1.4),
        ])
        self.steps("Say four copies, 25 requests each, each with its own map. How many queries now?", [
            (lambda: [*self.cap("4 copies, 25 requests each")], 0.5),
            "its own map",
            (lambda: [ReplacementTransform(mapb, maps)], 1.0),
            "How many",
            (lambda: [*reset(), *self.cap("each copy has its own map. how many queries?", YELLOW_M)], 0.8),
        ], after=0.6)
        leaders = [dots[25 * k] for k in range(4)]
        self.steps("Four. Each copy's leader asks the database, because no copy can see another copy's map.", [
            (lambda: [*[d.animate.set_color(YELLOW_M) for d in leaders],
                      *[dots[i].animate.set_color(GREY_D) for i in range(100) if i % 25]], 0.5),
            (lambda: [LaggedStart(*[run_pts([lane_out + [0, 0.12 * (k - 1.5), 0], lane_in], YELLOW_M, 0.6) for k in range(4)],
                                  lag_ratio=0.2), self.count_up("dbq", "queries running: {}", 0, 4, YELLOW_M, 1.25)], 1.1),
            (lambda: self.score(2), 0.5),
            "no copy can see",
            (lambda: [*self.cap("each copy sees only its own map"),
                      LaggedStart(*[glow(m[0], GOLD_M, 1.1) for m in maps], lag_ratio=0.2)], 1.0),
        ])
        self.steps("Here the bakery picture breaks. In a shop, everyone sees who's at the counter. Copies of an app see nothing of each other: they need a sign on a shared board.", [
            (lambda: self.cap("where the bakery picture breaks"), 0.5),
            "In a shop",
            (lambda: self.cap("one shop: everyone sees who's at the counter"), 0.5),
            "Copies of an app",
            (lambda: [*self.cap("copies of an app: they see nothing of each other"),
                      LaggedStart(*[glow(s, GREY_B, 1.02) for s in strips], lag_ratio=0.15)], 1.0),
            "a sign on a shared board",
            (lambda: self.cap("they need a sign on a shared board", YELLOW_M), 0.5),
        ])

        # ---------------- scene 7: a sign on the shared board ----------------
        lock = M("lock:merchant:m-17", 16, YELLOW_M).move_to([0, 0.6, 0])
        lock_bar = Line([-1.25, 0.3, 0], [1.25, 0.3, 0], stroke_width=4, color=YELLOW_M)
        self.steps("Redis can be that board, since every copy talks to it. Replay ten o'clock once more.", [
            (lambda: [glow(rd[0], TEAL_M, 1.02), *self.cap("Redis: the shared board")], 0.8),
            "Replay",
            (lambda: reset(), 0.8),
        ])
        self.steps("On a miss, the copy tries to put up the sign: SET lock:merchant:m-17, a token, NX, PX 2000.", [
            (lambda: [*[d.animate.set_color(YELLOW_M) for d in leaders],
                      *[dots[i].animate.set_color(GREY_D) for i in range(100) if i % 25]], 0.5),
            "tries to put up",
            (lambda: [LaggedStart(*[run_pts([get_out + [0, 0.1 * (k - 1.5), 0], get_in], YELLOW_M, 0.5) for k in range(4)],
                                  lag_ratio=0.15)], 1.0),
            (lambda: [FadeIn(lock, shift=0.1 * UP), Create(lock_bar), *self.rd_status("(nil)", RED_M)], 0.5),
            "SET lock",
            (lambda: self.cap("SET lock:merchant:m-17 <token> NX PX 2000", YELLOW_M), 0.5),
        ])
        self.steps("NX means only if the key doesn't exist yet, so exactly one copy wins. The token says whose sign it is.", [
            (lambda: self.cap("NX: only if the key doesn't exist yet"), 0.5),
            "exactly one copy wins",
            (lambda: [*[leaders[k].animate.set_color(GREY_D) for k in (1, 2, 3)], leaders[0].animate.scale(1.5),
                      *self.cap("one copy wins; the other three see the sign")], 0.7),
            "The token",
            (lambda: self.cap("the token: a random value that says whose sign it is"), 0.5),
        ])
        self.steps("PX 2000 rubs the sign out after 2,000 milliseconds, in case its writer wanders off.", [
            (lambda: [*self.cap("PX 2000: the sign rubs itself out after 2,000 ms"),
                      lock_bar.animate(rate_func=there_and_back).put_start_and_end_on([-1.25, 0.3, 0], [-0.2, 0.3, 0])], 1.4),
        ], after=0.4)
        self.steps("The winner loads the row and puts it in Redis. The others check Redis every 10 milliseconds, for up to a second.", [
            (lambda: [run_pts([lane_out, lane_in], YELLOW_M, 0.6)], 0.65),
            (lambda: [*self.db_running(1, YELLOW_M)], 0.3),
            (lambda: [run_pts([lane_in, lane_out], YELLOW_M, 0.6), *self.db_running(0)], 0.65),
            (lambda: [run_pts([get_out, get_in], GREEN_M, 0.45)], 0.5),
            (lambda: [key.animate.set_color(WHITE), *self.rd_status("cached again", GREEN_M)], 0.3),
            "The others check",
            (lambda: [*self.cap("the others: check Redis every 10 ms, for up to a second"),
                      LaggedStart(*[run_pts([get_out + [0, 0.1 * ((k % 3) - 1), 0], get_in], GREY_B, 0.3) for k in range(9)],
                                  lag_ratio=0.25)], 1.6),
            (lambda: [LaggedStart(*[d.animate.set_color(GREEN_M) for d in dots], lag_ratio=0.008), leaders[0].animate.scale(1 / 1.5)], 1.0),
        ])
        self.steps("In the lesson's demo, that made one database call across four copies.", [
            (lambda: self.score(3), 0.6),
            "one database call",
            (lambda: self.cap("4 copies with the sign: 1 database call"), 0.5),
        ], after=0.5)
        self.stamp("poster")

        # ---------------- scene 8: what the sign is for ----------------
        crash = tick(False, 0.2).move_to(leaders[0].get_center())
        self.steps("This lock only saves work. If the winner crashes before it fills the cache, the others stop waiting after a second and load the row themselves.", [
            (lambda: [*reset(), *self.cap("this lock only saves work")], 0.8),
            (lambda: [leaders[0].animate.set_color(YELLOW_M), *[d.animate.set_color(GREY_D) for d in dots[1:]],
                      glow(rd[0], TEAL_M, 1.02)], 0.5),
            "If the winner crashes",
            (lambda: [Create(crash), leaders[0].animate.set_color(GREY_D)], 0.5),
            "stop waiting",
            (lambda: [*self.cap("the others wait a second, then load it themselves"),
                      lock_bar.animate.put_start_and_end_on([-1.25, 0.3, 0], [0.0, 0.3, 0])], 1.2),
            (lambda: [LaggedStart(*[run_pts([lane_out + [0, 0.12 * (k - 1), 0], lane_in], WHITE, 0.6) for k in range(3)],
                                  lag_ratio=0.2), self.count_up("dbq", "queries running: {}", 0, 3, GOLD_M, 1.25)], 1.0),
        ])
        self.steps("That's wasted work, not a wrong answer. A lock that must never fail is a harder problem, for a later lesson.", [
            (lambda: [*self.cap("a second load: wasted work, not a wrong answer"),
                      lock_bar.animate.put_start_and_end_on([-1.25, 0.3, 0], [-1.22, 0.3, 0])], 1.0),
            (lambda: [FadeOut(lock), FadeOut(lock_bar)], 0.4),
            "A lock that must never fail",
            (lambda: self.cap("a lock that must never fail: a later lesson (leases, locks and fencing tokens)"), 0.5),
        ])
        self.steps("And keep single-flight too, so only one thread per copy even reaches for the sign.", [
            (lambda: [FadeOut(crash), *self.db_running(0), *self.cap("single-flight inside each copy, then the sign", WHITE)], 0.6),
            "only one thread",
            (lambda: [LaggedStart(*[glow(m[0], GOLD_M, 1.1) for m in maps], lag_ratio=0.2)], 1.0),
        ], after=0.4)

        # ---------------- scene 9: the code, in Java and Kotlin ----------------
        diagram = VGroup(app, rd, db, dots, a_get, a_lane, slots, pool_lab, key, strips, strip_labs, maps,
                         *[self.lab[k] for k in ("apt", "rdt", "rds_sub", "rds", "dbt", "db_sub", "dbq", "dbw", "clock")],
                         self.score_lab, *[s for s in self.scores if s is not None])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(panel, rows, color):
            return [panel[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows]

        self.steps("Here are both pieces, in Java and in Kotlin.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
        ])
        self.steps("putIfAbsent picks one leader inside a copy, and everyone else joins its future.", [
            "putIfAbsent",
            (lambda: [*hl(jp, (2, 3), GOLD_M), *hl(kp, (2, 3), GOLD_M)], 1.6),
            "everyone else",
            (lambda: [*hl(jp, (3,), GREY_B), *hl(kp, (3,), GREY_B)], 1.0),
        ])
        self.steps("SET with NX and PX picks one copy across all of them. Both languages send Redis the same command.", [
            (lambda: [*hl(jp, (6, 7), YELLOW_M), *hl(kp, (6, 7), YELLOW_M)], 1.8),
            "Both languages",
            (lambda: [*hl(jp, (7,), YELLOW_M), *hl(kp, (7,), YELLOW_M)], 1.2),
        ], after=0.6)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, can a cache make the database busier? For a moment, yes: when a busy copy expires, everyone misses together.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: [*self.cap("can a cache make the database busier?", WHITE)], 0.4),
            "For a moment",
            (lambda: [*self.cap("for one moment, yes: when a busy copy expires", RED_M), Indicate(self.scores[0], color=RED_M)], 0.8),
        ])
        self.steps("The fix is to send one customer to the back: single-flight inside each copy, and a sign in Redis across all of them.", [
            (lambda: self.cap("send one customer to the back", YELLOW_M, 32), 0.6),
            "single-flight inside",
            (lambda: [LaggedStart(*[glow(m[0], GOLD_M, 1.1) for m in maps], lag_ratio=0.2)], 0.9),
            "a sign in Redis",
            (lambda: [glow(rd[0], TEAL_M, 1.02)], 0.8),
        ], after=0.4)
        self.steps("One quick check. Twenty copies, each with single-flight, and no sign in Redis. The busy key expires. How many database queries? Pause and think.", [
            (lambda: [*self.uncap(), *self.put("apt", T("20 copies of the app", 24).move_to([AP_CX, TITLE_Y, 0]))], 0.6),
            "each with single-flight",
            (lambda: [LaggedStart(*[glow(m[0], GOLD_M, 1.1) for m in maps], lag_ratio=0.2)], 0.9),
            "The busy key",
            (lambda: [*reset()], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Twenty: one leader in each copy, because no copy can see another's map.", [
            (lambda: [*[d.animate.set_color(YELLOW_M) for d in leaders],
                      *[dots[i].animate.set_color(GREY_D) for i in range(100) if i % 25]], 0.4),
            (lambda: [LaggedStart(*[run_pts([lane_out + [0, 0.05 * ((k % 5) - 2), 0], lane_in], YELLOW_M, 0.5) for k in range(20)],
                                  lag_ratio=0.08), self.count_up("dbq", "queries running: {}", 0, 20, YELLOW_M, 1.25)], 1.4),
            "no copy can see",
            (lambda: self.cap("20 copies, single-flight only: 20 queries"), 0.5),
        ])
        self.steps("Next, we'll bake the next loaf a little before the shelf runs out.", [
            (lambda: [*self.db_running(0), dots.animate.set_color(GREEN_M), *self.rd_status("cached again", GREEN_M),
                      *self.cap("one customer to the back", YELLOW_M, 32)], 0.8),
        ], after=0.3)
        self.wait(2.0)

