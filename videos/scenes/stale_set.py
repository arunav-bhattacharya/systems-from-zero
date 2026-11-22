from sfz import *

SAY.insert(0, (r"\bFietsen\b", "feetsen"))
SAY.insert(0, (r"\bVelo\b", "vaylo"))
SAY.insert(0, (r"\bUtrecht\b", "oo trekt"))
SAY.insert(0, (r"\bt-A\b", "T A"))
SAY.insert(0, (r"\bt-B\b", "T B"))
SAY.insert(0, (r"\bNX\b", "N X"))
SAY.insert(0, (r"\bPX\b", "P X"))
SAY.insert(0, (r"\bEVAL\b", "eval"))
SAY.insert(0, (r"\bmemcache\b", "mem cache"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
DB_X0, DB_X1, TOP, BOT = -6.4, -2.7, 2.4, 0.15             # the back-office list
RD_X0, RD_X1 = 2.7, 6.4                                    # the shop window
DB_CX, RD_CX = (DB_X0 + DB_X1) / 2, (RD_X0 + RD_X1) / 2
TITLE_Y, SUB_Y = 2.1, 1.78
VAL_Y, LEASE_Y = 0.85, 0.45
ACT_Y = {"A": 2.0, "W": 1.05, "B": 0.1}
ACT_X = {"db": -1.3, "mid": 0.0, "rd": 1.3}
TL_Y, TL_LAB_Y, NOTE_Y, BAR_Y, CAP_Y = -1.05, -1.55, -2.2, -2.72, -3.27
TL_X = [-5.5 + 2.2 * k for k in range(6)]

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




def tag(text, color=GOLD_M, size=15):
    t = M(text, size, color)
    r = RoundedRectangle(corner_radius=0.07, width=t.width + 0.3, height=0.34, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.2), 1)
    return VGroup(r, t.move_to(r)).set_z_index(5)


def pause_icon():
    return VGroup(*[Rectangle(width=0.07, height=0.3, stroke_width=0).set_fill(YELLOW_M, 1).shift(x * RIGHT) for x in (-0.07, 0.07)]).set_z_index(6)


JAVA = ["// reader, on a miss: take the lease",
        "String took = redis.set(LEASE, token,",
        "    SetParams.setParams().nx().px(10_000));",
        "// read the row, then fill with the script",
        "Object ok = redis.eval(FILL_WITH_LEASE,",
        "    List.of(KEY, LEASE), List.of(token, name));",
        "// writer, after its commit",
        "redis.del(KEY, LEASE);"]
KOTLIN = ["// reader, on a miss: take the lease",
          "val took = redis.set(LEASE, token,",
          "    SetParams.setParams().nx().px(10_000))",
          "// read the row, then fill with the script",
          "val ok = redis.eval(FILL_WITH_LEASE,",
          "    listOf(KEY, LEASE), listOf(token, name))",
          "// writer, after its commit",
          "redis.del(KEY, LEASE)"]
RACE1 = ["A: GET, miss", "A: SELECT v1", "W: UPDATE v2", "W: DEL, 0 deleted", "A: SET v1, OK", "B: GET, gets v1"]
RACE2 = ["A: miss, lease t-A", "A: SELECT v1", "W: UPDATE v2", "W: DEL copy + lease", "A: fill refused", "B: lease t-B, fills v2"]


class StaleSet(Base):
    """cache-07, section 1 (and the lease from section 2). Fietsen Utrecht renamed Velo Utrecht; the save deleted the
    copy, yet receipts show the old name. The rule (commit, then DEL). The shop window: the back-office list (database),
    the window (Redis), tags (copies), a slow clerk. The race in six steps: A misses and reads v1, stalls; the writer
    commits v2 and DELs (0 keys deleted); A's SET stores v1 for an hour; B reads it. Named: a fill, a stale set (Meta's
    memcache paper). The window between read and fill; one in a million (TAO); the TTL caps it, a suspended flag. The
    tempting fix (delete again later) breaks. The lease: a numbered ticket a write tears up; SET lease NX PX 10000, DEL
    both keys, fill by script. Replay: refused, B fills v2. Guardrail, the code in Java and Kotlin, the moral, a check."""

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

    def dbv(self, s, color=WHITE):
        return self.put("dbv", M(s, 18, color).move_to([DB_CX, VAL_Y, 0]))

    def rdv(self, mob):
        return self.put("rdv", mob.move_to([RD_CX, VAL_Y, 0]))

    def rd_empty(self):
        return self.rdv(T("(empty)", 18, GREY_B))

    def note(self, side, s, color=GREY_B):
        x = RD_CX if side == "rd" else DB_CX
        return self.put("note_" + side, T(s, 17, color).move_to([x, -0.32, 0]))

    def dim(self, who, on):
        c = self.act[who]
        return [c[0].animate.set_fill(opacity=0.05 if on else 0.18).set_stroke(opacity=0.4 if on else 1),
                c[1].animate.set_opacity(0.4 if on else 1)]

    def walk(self, who, where):
        p = np.array([ACT_X[where], ACT_Y[who], 0])
        anims = [self.act[who].animate.move_to(p)]
        if self.carry.get(who) is not None:
            anims.append(self.carry[who].animate.move_to(p + 0.42 * DOWN))
        if self.paused.get(who) is not None:
            anims.append(self.paused[who].animate.move_to(p + 1.0 * RIGHT))
        return anims

    def pick(self, who, text, color=GOLD_M):
        t = tag(text, color).move_to(self.act[who].get_center() + 0.42 * DOWN)
        self.carry[who] = t
        return [FadeIn(t, scale=0.6)]

    def step(self, k, labels=None, color=YELLOW_M):
        labels = labels or self.labels
        lab = fit(T(labels[k], 15, color), 2.1).move_to([TL_X[k], TL_LAB_Y, 0])
        return [self.dots_tl[k].animate.set_fill(color, 1).set_stroke(color), *self.put(f"tl{k}", lab)]

    def tl_reset(self, labels):
        self.labels = labels
        return [*[d.animate.set_fill(BLACK, 1).set_stroke(GREY_C) for d in self.dots_tl], *self.drop(*[f"tl{k}" for k in range(6)])]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab, self.carry, self.paused = {}, {}, {}
        self.title_card("How did the old name get back?", "a slow reader, a stale set, and a lease")

        db = frame(DB_X0, DB_X1, TOP, BOT, BLUE_M)
        rd = frame(RD_X0, RD_X1, TOP, BOT, TEAL_M)
        db_row = T("merchants row m-17", 16, GREY_B).move_to([DB_CX, 1.32, 0])
        rd_key = M("merchant:{m-17}", 17, GREY_B).move_to([RD_CX, 1.32, 0])
        self.act = {"A": chip("reader A", PURPLE_M, 22), "W": chip("writer", BLUE_M, 22), "B": chip("reader B", GREEN_M, 22)}
        for k, c in self.act.items():
            c.move_to([0, ACT_Y[k], 0]).set_z_index(4)
        tl_line = Line([TL_X[0], TL_Y, 0], [TL_X[5], TL_Y, 0], stroke_width=2, color=GREY_D)
        self.dots_tl = VGroup(*[Circle(radius=0.2, stroke_color=GREY_C, stroke_width=2.5).set_fill(BLACK, 1).move_to([x, TL_Y, 0])
                                for x in TL_X])
        tl_nums = VGroup(*[T(str(k + 1), 17, GREY_B).move_to([x, TL_Y, 0]).set_z_index(3) for k, x in enumerate(TL_X)])
        self.labels = RACE1

        # ---------------- scene 1: the question ----------------
        self.steps("A bike shop in Utrecht changes its name, from Fietsen Utrecht to Velo Utrecht. "
                   "The save deletes the cached copy right after, as it should.", [
            (lambda: [FadeIn(db), FadeIn(rd), *self.put("dbt", T("database", 26).move_to([DB_CX, TITLE_Y, 0])),
                      *self.put("rdt", T("Redis", 26).move_to([RD_CX, TITLE_Y, 0])), FadeIn(db_row), FadeIn(rd_key),
                      *self.dbv("v1  Fietsen Utrecht"), *self.rdv(tag("v1  Fietsen Utrecht", WHITE))], 1.0),
            "to Velo",
            (lambda: self.dbv("v2  Velo Utrecht", GREEN_M), 0.6),
            "The save deletes",
            (lambda: [*self.rd_empty(), *self.note("rd", "deleted after the save")], 0.6),
        ])
        self.steps("An hour later, a customer's receipt still says Fietsen Utrecht. "
                   "If every save deletes the copy, how did the old name get back in?", [
            "An hour later",
            (lambda: [*self.rdv(tag("v1  Fietsen Utrecht", RED_M)), *self.note("rd", "an hour later: the old name", RED_M),
                      rd[0].animate.set_stroke(RED_M)], 0.7),
            "how did",
            (lambda: self.cap("every save deletes the copy. how did the old name get back in?", WHITE), 0.5),
        ])

        # ---------------- scene 2: the rule ----------------
        self.steps("The rule from the last lesson is simple. Commit the new row to the database, then delete the copy in Redis.", [
            (lambda: [*self.uncap(), *self.drop("note_rd"), rd[0].animate.set_stroke(TEAL_M), *self.dbv("v1  Fietsen Utrecht"),
                      *self.rdv(tag("v1  Fietsen Utrecht", WHITE)), FadeIn(self.act["W"], shift=0.1 * UP),
                      *self.cap("the rule: commit, then delete the copy")], 0.8),
            "Commit",
            (lambda: self.walk("W", "db"), 0.6),
            (lambda: self.dbv("v2  Velo Utrecht", GREEN_M), 0.4),
            "then delete",
            (lambda: self.walk("W", "rd"), 0.7),
            (lambda: self.rd_empty(), 0.4),
            (lambda: self.walk("W", "mid"), 0.5),
        ])
        self.steps("The next reader misses, loads the new row, and fills the cache. So far so good.", [
            (lambda: [FadeIn(self.act["B"], shift=0.1 * UP), *self.walk("B", "rd")], 0.7),
            "loads the new row",
            (lambda: self.walk("B", "db"), 0.7),
            (lambda: self.pick("B", "v2  Velo Utrecht", GREEN_M), 0.3),
            "fills the cache",
            (lambda: self.walk("B", "rd"), 0.7),
            (lambda: [*self.rdv(self.carry.pop("B")), *self.walk("B", "mid")], 0.6),
        ])

        # ---------------- scene 3: the shop window ----------------
        self.steps("Picture a shop window. The prices live on a list in the back office, and clerks copy them onto tags for the window. "
                   "When a price changes, someone takes the old tag down, and the next clerk copies a fresh one.", [
            (lambda: self.uncap(), 0.3),
            "a shop window",
            (lambda: [glow(rd[0], TEAL_M, 1.02)], 0.7),
            "a list in the back office",
            (lambda: [glow(db[0], BLUE_M, 1.02)], 0.7),
            "clerks copy",
            (lambda: [glow(self.act["B"][0], GREEN_M, 1.1)], 0.6),
            "takes the old tag down",
            (lambda: [glow(self.act["W"][0], BLUE_M, 1.1)], 0.6),
        ])
        self.steps("The list is the database. The window is Redis. A tag is the cached copy, and taking it down is the delete.", [
            (lambda: self.put("db_sub", T("the back-office list", 17, GREY_B).move_to([DB_CX, SUB_Y, 0])), 0.5),
            "The window",
            (lambda: self.put("rd_sub", T("the shop window", 17, GREY_B).move_to([RD_CX, SUB_Y, 0])), 0.5),
            "A tag",
            (lambda: [Indicate(self.lab["rdv"], color=GOLD_M)], 0.7),
            "taking it down",
            (lambda: self.cap("a tag: the cached copy.   taking it down: DEL"), 0.5),
        ])

        # ---------------- scene 4: the slow clerk ----------------
        self.steps("Now picture a slow clerk. Start again: version 1 in the database, and nothing in Redis.", [
            (lambda: [*self.uncap(), FadeIn(self.act["A"], shift=0.1 * UP), *self.cap("a slow clerk: reader A", PURPLE_M)], 0.6),
            "Start again",
            (lambda: [*self.dbv("v1  Fietsen Utrecht"), *self.rd_empty(), Create(tl_line), FadeIn(self.dots_tl), FadeIn(tl_nums)], 0.9),
        ])
        self.steps("Reader A, a server checking a payment, misses on the shop's key. It reads the row: version 1, Fietsen Utrecht.", [
            (lambda: self.cap("reader A: a server checking a payment"), 0.4),
            "misses",
            (lambda: self.walk("A", "rd"), 0.6),
            (lambda: [*self.step(0), *self.walk("A", "mid")], 0.6),
            "It reads",
            (lambda: self.walk("A", "db"), 0.6),
            (lambda: [*self.pick("A", "v1  Fietsen Utrecht"), *self.step(1)], 0.4),
            (lambda: self.walk("A", "mid"), 0.6),
        ])
        self.steps("Then it stalls before it can store it: a pause to clean up memory, or a wait for a database connection.", [
            (lambda: [*self.uncap()], 0.2),
            "stalls",
            (lambda: [FadeIn(self.paused.setdefault("A", pause_icon().move_to(self.act["A"].get_center() + 1.0 * RIGHT))),
                      *self.dim("A", True)], 0.5),
            "a pause",
            (lambda: self.cap("paused: cleaning up memory, or waiting for a connection", YELLOW_M), 0.5),
        ])
        self.steps("Meanwhile, the writer renames the shop and commits version 2. Then it deletes the copy. "
                   "But the window is empty, so the delete removes nothing: zero keys deleted.", [
            (lambda: [*self.uncap(), *self.walk("W", "db")], 0.6),
            "commits version 2",
            (lambda: [*self.dbv("v2  Velo Utrecht", GREEN_M), *self.step(2)], 0.5),
            "Then it deletes",
            (lambda: self.walk("W", "rd"), 0.6),
            "the window is empty",
            (lambda: [Indicate(self.lab["rdv"], color=GREY_B)], 0.6),
            "zero keys",
            (lambda: [*self.step(3), *self.note("rd", "DEL: 0 keys deleted")], 0.5),
            (lambda: self.walk("W", "mid"), 0.5),
        ])
        self.steps("Now reader A wakes up and sends its SET: Fietsen Utrecht, for an hour. Will Redis take it? Pause and guess.", [
            (lambda: [FadeOut(self.paused.pop("A")), *self.dim("A", False)], 0.4),
            "sends its SET",
            (lambda: [self.act["A"].animate.move_to([0.6, ACT_Y["A"], 0]),
                      self.carry["A"].animate.move_to([0.6, ACT_Y["A"] - 0.42, 0])], 0.6),
            "Pause and guess",
            (lambda: self.cap("SET v1 EX 3600: will Redis take it? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It does. Redis keeps no record of the delete, and no versions, so it stores the old name for an hour.", [
            (lambda: self.walk("A", "rd"), 0.4),
            (lambda: [*self.rdv(self.carry.pop("A")), *self.step(4, color=RED_M), *self.note("rd", "SET v1 EX 3600: OK", RED_M)], 0.6),
            "no record",
            (lambda: [*self.cap("Redis keeps no record of the delete"), *self.walk("A", "mid")], 0.6),
            "for an hour",
            (lambda: [*self.rdv(tag("v1  Fietsen Utrecht", RED_M)), rd[0].animate.set_stroke(RED_M)], 0.5),
        ])
        self.steps("Reader B, and every reader after it, gets Fietsen Utrecht. And no save is coming to delete it: "
                   "the save that should have deleted it was already over.", [
            (lambda: [*self.uncap(), *self.walk("B", "rd")], 0.6),
            (lambda: [*self.pick("B", "v1  Fietsen Utrecht", RED_M), *self.step(5, color=RED_M)], 0.4),
            (lambda: self.walk("B", "mid"), 0.6),
            "no save is coming",
            (lambda: [*self.cap("the save that should have deleted it is already over", RED_M), glow(self.act["W"][0], BLUE_M, 1.1),
                      FadeOut(self.carry.pop("B"))], 0.8),
        ])
        self.stamp("race")

        # ---------------- scene 5: the name ----------------
        self.steps("Storing a copy after a miss is called a fill. A fill that stores a value already out of date when it arrives "
                   "is called a stale set. Meta, the company behind Facebook, named it in a paper about its cache, memcache.", [
            (lambda: self.cap("a fill: storing a copy after a miss"), 0.5),
            "A fill that",
            (lambda: [*self.cap("a stale set: a fill that was out of date when it arrived", RED_M, 28),
                      Indicate(self.dots_tl[4], color=RED_M)], 0.8),
            "Meta",
            (lambda: [*self.note("db", "the name: Meta's memcache paper")], 0.5),
        ])

        # ---------------- scene 6: the window, and what it costs ----------------
        win = SurroundingRectangle(VGroup(self.dots_tl[1], self.dots_tl[4]), color=YELLOW_M, buff=0.15, corner_radius=0.1)
        self.steps("The race needs two things: A's read comes before the commit, and A's fill comes after the delete.", [
            (lambda: [*self.uncap(), *self.drop("note_db")], 0.3),
            "A's read",
            (lambda: [Indicate(self.dots_tl[1], color=YELLOW_M, scale_factor=1.4)], 0.7),
            "A's fill",
            (lambda: [Indicate(self.dots_tl[4], color=YELLOW_M, scale_factor=1.4)], 0.7),
            (lambda: [Create(win), *self.cap("the gap: between A's read and A's fill", YELLOW_M)], 0.7),
        ])
        self.steps("Between a read and its fill there's usually a millisecond or two. A pause can stretch it to hundreds. "
                   "So it's rare for one request, and frequent across millions.", [
            (lambda: self.cap("usually 1 or 2 ms"), 0.5),
            "A pause can",
            (lambda: [*self.cap("a pause: hundreds of ms"), win.animate(rate_func=there_and_back).stretch(1.12, 0)], 0.9),
            "rare for one",
            (lambda: self.cap("rare for one request, frequent across millions", WHITE), 0.5),
        ])
        self.steps("When Meta measured its own cache, about one write in a million was still wrong five minutes later. "
                   "One in a million sounds safe, until you serve a quadrillion reads a day.", [
            (lambda: self.cap("Meta: about 1 cache write in a million still wrong 5 minutes later"), 0.6),
            "until you serve",
            (lambda: self.cap("TAO, Meta's cache: more than a quadrillion reads a day", RED_M), 0.6),
        ])
        self.steps("At that volume, it's a steady stream of wrong answers.", [], after=0.3)
        self.steps("Here the TTL caps the damage at an hour. For a shop's name, that's a nuisance. "
                   "For a flag that says the shop is suspended for fraud, it's an hour of payments that should have been refused.", [
            (lambda: [*self.cap("the TTL caps it: one hour"), *self.note("rd", "TTL: 1 hour", GREY_B)], 0.5),
            "a nuisance",
            (lambda: self.cap("a shop's old name for an hour: a nuisance"), 0.5),
            "suspended",
            (lambda: self.cap("an old 'not suspended' flag for an hour: payments that should be refused", RED_M), 0.6),
        ])

        # ---------------- scene 7: the tempting fix ----------------
        self.steps("The tempting fix is to delete the key again, a moment later. It helps, since most slow readers finish within the wait.", [
            (lambda: [FadeOut(win), *self.cap("delete again, a moment later?", PURPLE_M)], 0.5),
            "a moment later",
            (lambda: self.walk("W", "rd"), 0.6),
            (lambda: [*self.rd_empty(), *self.note("rd", "second DEL: 1 key deleted", GREEN_M), rd[0].animate.set_stroke(TEAL_M)], 0.5),
            (lambda: self.walk("W", "mid"), 0.5),
            "It helps",
            (lambda: self.cap("it helps: most slow readers finish within the wait"), 0.5),
        ])
        self.steps("But a reader that pauses longer still gets in. It shrinks the gap without closing it, "
                   "and you have to guess how slow your slowest reader can be.", [
            "pauses longer",
            (lambda: [*self.pick("A", "v1  Fietsen Utrecht"), FadeIn(self.paused.setdefault("A", pause_icon().move_to(
                self.act["A"].get_center() + 1.0 * RIGHT)))], 0.5),
            (lambda: [FadeOut(self.paused.pop("A")), *self.walk("A", "rd")], 0.7),
            (lambda: [*self.rdv(self.carry.pop("A")), *self.note("rd", "a later SET: the old name again", RED_M),
                      rd[0].animate.set_stroke(RED_M), *self.walk("A", "mid")], 0.6),
            "It shrinks",
            (lambda: self.cap("it shrinks the gap without closing it", RED_M), 0.5),
            "you have to guess",
            (lambda: self.cap("and you have to guess how slow your slowest reader is"), 0.5),
        ])

        # ---------------- scene 8: the lease ----------------
        self.steps("Back to the window. Before a clerk copies a price, he takes a numbered ticket from the office. "
                   "A price change tears up every ticket for that item, and the window takes a tag only with a ticket that's still valid.", [
            (lambda: [*self.uncap(), *self.drop("note_rd"), *self.rd_empty(), rd[0].animate.set_stroke(TEAL_M)], 0.5),
            "a numbered ticket",
            (lambda: [*self.put("lease", tag("ticket 41", YELLOW_M).move_to([RD_CX, LEASE_Y, 0]))], 0.6),
            "tears up",
            (lambda: [self.lab["lease"].animate(rate_func=there_and_back).rotate(0.25), *self.cap("a price change tears up the tickets")], 0.7),
            "still valid",
            (lambda: self.cap("the window takes a tag only with a valid ticket", YELLOW_M), 0.5),
        ])
        self.steps("That ticket is called a lease. In Redis, the reader takes it on a miss: SET lease, a random token, NX, PX 10000.", [
            (lambda: self.cap("the ticket: a lease", YELLOW_M, 30), 0.5),
            "In Redis",
            (lambda: [*self.put("lease", tag("lease:{m-17} = t-A", YELLOW_M).move_to([RD_CX, LEASE_Y, 0]))], 0.6),
            "SET lease",
            (lambda: self.cap("SET lease:{m-17} <random token> NX PX 10000", YELLOW_M), 0.5),
        ])
        self.steps("NX means only if nobody holds it, and PX 10000 lets it vanish after ten seconds if the reader crashes.", [
            (lambda: self.cap("NX: only if nobody holds it"), 0.5),
            "PX 10000",
            (lambda: self.cap("PX 10000: gone after 10 s if the reader crashes"), 0.5),
        ])
        self.steps("After its commit, the writer deletes the copy and the lease, in one command. And the fill runs as a small script "
                   "inside Redis: if the lease still holds my token, store the name, otherwise store nothing.", [
            (lambda: self.cap("the writer: DEL merchant:{m-17} lease:{m-17}"), 0.5),
            "And the fill",
            (lambda: self.cap("the fill: a script. lease still holds my token? store. otherwise: nothing"), 0.6),
        ])
        self.steps("A script runs as one command, so no delete can land between the check and the store.", [
            (lambda: self.cap("one script, one command: nothing lands in between"), 0.5),
        ])

        # ---------------- scene 9: the replay ----------------
        self.steps("Replay the race. A misses, takes lease t-A, reads version 1, and stalls.", [
            (lambda: [*self.uncap(), *self.tl_reset(RACE2), *self.dbv("v1  Fietsen Utrecht"), *self.drop("lease")], 0.7),
            "A misses",
            (lambda: self.walk("A", "rd"), 0.5),
            (lambda: [*self.put("lease", tag("lease:{m-17} = t-A", YELLOW_M).move_to([RD_CX, LEASE_Y, 0])), *self.step(0)], 0.5),
            "reads version 1",
            (lambda: self.walk("A", "db"), 0.6),
            (lambda: [*self.pick("A", "v1  Fietsen Utrecht"), *self.step(1)], 0.4),
            (lambda: self.walk("A", "mid"), 0.5),
            "stalls",
            (lambda: [FadeIn(self.paused.setdefault("A", pause_icon().move_to(self.act["A"].get_center() + 1.0 * RIGHT))),
                      *self.dim("A", True)], 0.4),
        ])
        self.steps("The writer commits version 2 and deletes both keys: one key deleted, the lease.", [
            (lambda: self.walk("W", "db"), 0.5),
            (lambda: [*self.dbv("v2  Velo Utrecht", GREEN_M), *self.step(2)], 0.4),
            "deletes both",
            (lambda: self.walk("W", "rd"), 0.6),
            (lambda: [*self.drop("lease"), *self.step(3), *self.note("rd", "DEL: 1 key deleted (the lease)")], 0.5),
            (lambda: self.walk("W", "mid"), 0.5),
        ])
        refused = tick(False, 0.18)
        self.steps("A wakes up, and its fill is refused: the lease is gone. The old name never reaches the window.", [
            (lambda: [FadeOut(self.paused.pop("A")), *self.dim("A", False)], 0.4),
            (lambda: self.walk("A", "rd"), 0.6),
            "refused",
            (lambda: [Create(refused.move_to(self.carry["A"].get_center() + 1.4 * RIGHT)), *self.step(4, color=GREEN_M),
                      *self.note("rd", "fill with t-A: refused", GREEN_M)], 0.5),
            "never reaches",
            (lambda: [FadeOut(self.carry.pop("A"), shift=0.3 * DOWN), FadeOut(refused), *self.walk("A", "mid")], 0.6),
        ])
        self.steps("Reader B misses, takes lease t-B, reads version 2, and fills Velo Utrecht.", [
            (lambda: self.walk("B", "rd"), 0.5),
            (lambda: self.put("lease", tag("lease:{m-17} = t-B", YELLOW_M).move_to([RD_CX, LEASE_Y, 0])), 0.4),
            "reads version 2",
            (lambda: self.walk("B", "db"), 0.6),
            (lambda: self.pick("B", "v2  Velo Utrecht", GREEN_M), 0.3),
            "fills",
            (lambda: self.walk("B", "rd"), 0.6),
            (lambda: [*self.rdv(self.carry.pop("B")), *self.drop("lease"), *self.step(5, color=GREEN_M),
                      *self.note("rd", "fill with t-B: stored", GREEN_M), *self.walk("B", "mid")], 0.6),
        ], after=0.5)
        self.stamp("poster")

        # ---------------- scene 10: the guardrail ----------------
        self.steps("Two notes. A lease works only when every fill starts with a miss; the lesson's next fix, a version number, "
                   "covers the rest. And keep the TTL: it caps whatever still slips through.", [
            (lambda: self.cap("a lease needs every fill to start with a miss"), 0.5),
            "a version number",
            (lambda: self.cap("for the rest: a version number (the next section)"), 0.5),
            "keep the TTL",
            (lambda: self.cap("keep the TTL: it caps whatever slips through", WHITE), 0.5),
        ])

        # ---------------- scene 11: the code ----------------
        diagram = VGroup(db, rd, db_row, rd_key, *self.act.values(), tl_line, self.dots_tl, tl_nums,
                         *[m for k, m in self.lab.items()])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, the reader takes the lease with SET, NX and PX, and fills with one EVAL of the script. "
                   "The writer sends one DEL with both keys.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "takes the lease",
            (lambda: hl((1, 2), YELLOW_M), 1.3),
            "fills with",
            (lambda: hl((4, 5), GOLD_M), 1.3),
            "The writer",
            (lambda: hl((7,), BLUE_M), 1.1),
        ], after=0.8)

        # ---------------- scene 12: the moral, and a check ----------------
        self.steps("So how did the old name get back in? A slow reader put it there after the delete.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            "A slow reader",
            (lambda: self.cap("a slow reader put it back after the delete", WHITE), 0.5),
        ])
        self.steps("On a busy system, things don't happen in the order your code lists them, so a late copy must show a ticket "
                   "that's still valid.", [
            (lambda: self.cap("things don't happen in the order your code lists them"), 0.5),
            "so a late copy",
            (lambda: self.cap("a late copy must show a ticket that's still valid", YELLOW_M, 30), 0.5),
        ], after=0.4)
        self.steps("One quick check. Reader A takes the lease and stalls for three seconds, but nobody renames the shop. "
                   "Is A's fill stored or refused? Pause and think.", [
            (lambda: [*self.uncap(), *self.tl_reset(RACE2), *self.drop("note_rd"), *self.dbv("v1  Fietsen Utrecht"),
                      *self.rd_empty()], 0.6),
            "Reader A takes",
            (lambda: [*self.put("lease", tag("lease:{m-17} = t-A", YELLOW_M).move_to([RD_CX, LEASE_Y, 0])),
                      *self.pick("A", "v1  Fietsen Utrecht"),
                      FadeIn(self.paused.setdefault("A", pause_icon().move_to(self.act["A"].get_center() + 1.0 * RIGHT)))], 0.6),
            "nobody renames",
            (lambda: [glow(self.act["W"][0], GREY_B, 1.1)], 0.6),
            "Pause and think",
            (lambda: self.cap("stored or refused? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Stored. Nothing tore up its ticket, and version 1 is still true. A lease refuses only copies that a write has made old.", [
            (lambda: [FadeOut(self.paused.pop("A")), *self.walk("A", "rd")], 0.6),
            (lambda: [*self.rdv(self.carry.pop("A")), *self.drop("lease"), *self.note("rd", "fill with t-A: stored", GREEN_M),
                      *self.walk("A", "mid")], 0.6),
            "A lease refuses",
            (lambda: self.cap("a lease refuses only copies a write has made old", YELLOW_M, 28), 0.6),
        ])
        self.wait(2.0)
