from sfz import *

SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bamount_minor\b", "amount minor"))
SAY.insert(0, (r"\bBEGIN\b", "begin"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PH_Y, PH_W, PH_H = 3.05, 1.95, 0.72                   # the six phases, a strip across the top
FL_X, FL_W, FL_H = -5.4, 1.5, 0.5                     # the fleet: six instances in a column on the left
FL_Y = [1.55 - 0.66 * i for i in range(6)]
COLS = {"a": (0.0, 2.4), "m": (2.9, 6.1)}             # amount and amount_minor columns
C_TOP, C_BOT = 1.85, -1.45
ROW_Y = [0.45, -0.2, -0.85]
ZONE_Y, CAP_Y, BAR_Y = -2.2, -3.36, -2.85
VC = {1: BLUE_M, 2: TEAL_M, 3: GREEN_M, 4: GOLD_M}
PHASES = ["expand", "dual write", "backfill", "read new", "write new", "contract"]


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
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def cx(c):
    return sum(COLS[c]) / 2


def column_box(c, color):
    x0, x1 = COLS[c]
    r = RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=C_TOP - C_BOT, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([(x0 + x1) / 2, (C_TOP + C_BOT) / 2, 0])
    line = Line([x0 + 0.15, 0.85, 0], [x1 - 0.15, 0.85, 0], stroke_width=1.5, color=GREY_C)
    return VGroup(r, line)


def col_head(c, name, sub, color=WHITE):
    return VGroup(M(name, 22, color).move_to([cx(c), 1.48, 0]), T(sub, 16, GREY_B).move_to([cx(c), 1.1, 0]))


def cell(c, i, s, color=WHITE):
    return M(s, 22, color).move_to([cx(c), ROW_Y[i], 0])


def inst(i, v):
    r = RoundedRectangle(corner_radius=0.1, width=FL_W, height=FL_H, stroke_color=VC[v], stroke_width=2.5)
    r.set_fill(fillc(VC[v]), 1).move_to([FL_X, FL_Y[i], 0])
    return VGroup(r, T(f"v{v}", 20, VC[v]).move_to(r))


def path_to(c, i_from=2):
    """From an instance, over the top of the table, down into a column."""
    a = np.array([FL_X + FL_W / 2 + 0.05, FL_Y[i_from], 0])
    return [a, [-0.6, 2.2, 0], [cx(c), 2.2, 0], [cx(c), C_TOP + 0.05, 0]]


def run_pts(pts, color=YELLOW_M, rt=0.8, r=0.08):
    pts = [np.array(p, dtype=float) for p in pts]
    d = Dot(radius=r, color=color).move_to(pts[0]).set_opacity(0).set_z_index(8)
    path = VMobject().set_points_as_corners(pts)
    return Succession(d.animate(run_time=0.04).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.1))


def phase_box(k, active=False, done=False):
    x = -6.15 + PH_W / 2 + k * (PH_W + 0.1)
    color = GOLD_M if active else (GREY_B if done else GREY_D)
    r = RoundedRectangle(corner_radius=0.1, width=PH_W, height=PH_H, stroke_color=color, stroke_width=3 if active else 2)
    r.set_fill(fillc(GOLD_M) if active else BLACK, 1).move_to([x, PH_Y, 0])
    g = VGroup(r, T(f"{k + 1}", 16, color).move_to([x, PH_Y + 0.17, 0]),
               T(PHASES[k], 18, WHITE if (active or done) else GREY_C).move_to([x, PH_Y - 0.13, 0]))
    return g


class ExpandContract(Base):
    """enc-03, section 3. payouts.amount holds euros (40.00); the company wants amount_minor in cents (4000). Six
    instances update one at a time, so versions overlap. The quick migration breaks every v1 (column "amount" does not
    exist); stopping the program costs downtime (Stripe: 100 million records at one a second, over three years). A new
    bridge beside the old one. Six steps: expand, dual write (v2), backfill after the last v1 (predict why: v1 can
    change amount and leave amount_minor wrong), read new with a shadow read (v3), write new (v4), contract. The rule:
    each step works with the versions on both sides. Locks: an instant ALTER behind an open BEGIN stops every read;
    lock_timeout. The cost. Moral and a check (DROP in v4's own release)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_zone(self, m):
        if m is not None:
            m.move_to([m.get_x(), ZONE_Y, 0])
        old, self.zone = self.zone, m
        if old is None and m is None:
            return []
        if m is None:
            return [FadeOut(old)]
        return [swap(old, m)]

    def fleet(self, vs):
        anims = []
        for i, v in enumerate(vs):
            new = inst(i, v)
            old = self.fl[i]
            self.fl[i] = new
            if old is None:
                anims.append(FadeIn(new))
            elif self.flv[i] != v:
                anims.append(swap(old, new, RIGHT))
            else:
                self.fl[i] = old
            self.flv[i] = v
        return anims

    def phase(self, k):
        new = VGroup(*[phase_box(j, j == k, j < k) for j in range(6)])
        old, self.ph = self.ph, new
        return [swap(old, new, DOWN)] if old is not None else [FadeIn(new, shift=0.1 * DOWN)]

    def set_cell(self, c, i, s, color=WHITE):
        new = cell(c, i, s, color)
        old, self.cells[(c, i)] = self.cells.get((c, i)), new
        return [swap(old, new)]

    def set_head(self, name=None, sub=None, color=WHITE):
        new = col_head("a", name, sub, color) if name else None
        old, self.ha = self.ha, new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        b = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(b), run_time=0.25)
        self.play(Uncreate(b), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.zone = self.ph = self.ha = None
        self.fl, self.flv, self.cells = [None] * 6, [None] * 6, {}
        self.title_card("A new bridge beside the old one", "changing a column while two versions run")

        # ---------------- scene 1: the question ----------------
        ca = column_box("a", BLUE_M)
        tname = T("payouts", 24).move_to([3.05, 2.47, 0])
        self.steps("The payout program keeps every payment it makes to a shop in a table called payouts: rows and columns, like a "
                   "spreadsheet. Its amount column holds euros, like 40.00. You want cents instead, 4000, in a column called "
                   "amount_minor, like every other money field in the company.", [
            "in a table",
            (lambda: [FadeIn(tname), FadeIn(ca), *self.set_head("amount", "euros, numeric(12,2)")], 0.8),
            "like 40.00",
            (lambda: [*self.set_cell("a", 0, "40.00"), *self.set_cell("a", 1, "40.00"), *self.set_cell("a", 2, "…", GREY_B)], 0.6),
            "You want cents",
            (lambda: self.set_zone(VGroup(M("amount_minor:", 22, GREEN_M), M("4000", 22, GREEN_M), T("(cents, bigint)", 18, GREY_B))
                                   .arrange(RIGHT, buff=0.2).move_to([3.0, 0, 0])), 0.7),
        ])
        self.steps("The program runs as six copies, called instances. An update replaces them one at a time, so for a while old and "
                   "new versions run side by side, on the same table. How do you change a column under both of them?", [
            (lambda: self.fleet([1] * 6), 0.8),
            "An update replaces",
            (lambda: self.fleet([2, 1, 1, 1, 1, 1]), 0.5),
            (lambda: self.fleet([2, 2, 1, 1, 1, 1]), 0.5),
            (lambda: self.fleet([2, 2, 2, 1, 1, 1]), 0.5),
            "side by side",
            (lambda: [run_pts(path_to("a", 0), VC[2]), run_pts(path_to("a", 4), VC[1])], 0.9),
            "How do you",
            (lambda: self.cap("how do you change a column under both of them?", WHITE), 0.5),
        ])

        # ---------------- scene 2: the quick way breaks ----------------
        self.steps("The quick way is one migration, a script that changes the table, shipped with the update: rename the column, "
                   "convert it, done. Let's watch it run.", [
            (lambda: [*self.uncap(), *self.fleet([1] * 6), *self.set_zone(None)], 0.6),
            "rename the column",
            (lambda: [*self.set_head("amount_minor", "cents, bigint", GREEN_M), *self.cap("one migration: rename and convert")], 0.7),
            "convert it",
            (lambda: [*self.set_cell("a", 0, "4000", GREEN_M), *self.set_cell("a", 1, "4000", GREEN_M)], 0.6),
            "Let's watch",
            (lambda: self.fleet([2, 1, 1, 1, 1, 1]), 0.5),
        ])
        err = M('ERROR: column "amount" does not exist', 20, RED_M)
        xs = VGroup(*[tick(False, 0.12).next_to(inst(i, 1), RIGHT, buff=0.15) for i in range(1, 6)])
        self.steps("The moment it runs, every old instance still in the fleet fails: column amount does not exist. "
                   "Until the rollout ends, those requests break.", [
            (lambda: [run_pts(path_to("a", 3), VC[1], 0.8)], 0.8),
            "fails",
            (lambda: [*self.set_zone(err.copy().move_to([2.2, 0, 0])), LaggedStart(*[Create(x) for x in xs], lag_ratio=0.15)], 0.9),
            "Until the rollout",
            (lambda: [*self.fleet([2, 2, 2, 1, 1, 1])], 0.6),
            (lambda: [FadeOut(VGroup(*xs[:2]))], 0.3),
        ])
        self.steps("Stop the program first, then? That avoids the errors, but the downtime grows with the table. Stripe, a large "
                   "payments company, worked out that moving 100 million records at one a second would take more than three years.", [
            (lambda: [FadeOut(VGroup(*xs[2:])), *self.set_zone(None), *self.fleet([1] * 6)], 0.5),
            "Stop the program",
            (lambda: [*[self.fl[i].animate.set_opacity(0.2) for i in range(6)], *self.cap("stop everything: no errors, but downtime")], 0.6),
            "Stripe",
            (lambda: self.cap("Stripe: 100 million records at one a second = more than three years", RED_M), 0.5),
        ])
        self.steps("Nobody's customers wait three years. What we want is a change that never surprises anyone, old or new.", [
            (lambda: [*[self.fl[i].animate.set_opacity(1) for i in range(6)]], 0.5),
            "What we want",
            (lambda: self.cap("wish: a change that never surprises any running version", WHITE), 0.5),
        ])

        # ---------------- scene 3: a new bridge beside the old ----------------
        old_b = T("the old bridge", 20, BLUE_M).move_to([cx("a"), C_BOT - 0.32, 0])
        new_b = T("the new bridge", 20, GREEN_M).move_to([cx("m"), C_BOT - 0.32, 0])
        cm = column_box("m", GREEN_M)
        hm = col_head("m", "amount_minor", "cents, bigint", GREEN_M)
        drivers = T("drivers", 20, GREY_B).move_to([FL_X, FL_Y[0] + 0.55, 0])
        self.steps("Think about replacing an old bridge. Nobody blows it up on a Monday and hopes the drivers read the news. You "
                   "build the new bridge next to it. For a while, both are open. Traffic moves across, lane by lane. And only when "
                   "nobody drives over the old one, you take it down.", [
            (lambda: [*self.uncap(), *self.set_head("amount", "euros, numeric(12,2)"), *self.set_cell("a", 0, "40.00"),
                      *self.set_cell("a", 1, "40.00")], 0.6),
            "Think about",
            (lambda: [FadeIn(old_b)], 0.5),
            "You build",
            (lambda: [FadeIn(cm), FadeIn(new_b)], 0.7),
            "Traffic moves",
            (lambda: [run_pts(path_to("a", 1), VC[1]), run_pts(path_to("m", 3), VC[1])], 0.9),
            "you take it down",
            (lambda: [glow(ca[0], RED_M, 1.0)], 0.7),
        ])
        self.steps("Map it. The old bridge is the amount column. The new bridge is amount_minor. The drivers are the instances, and "
                   "some still have last year's map. Taking the old bridge down is dropping the column.", [
            "The old bridge is",
            (lambda: [glow(ca[0], BLUE_M, 1.0)], 0.6),
            "The new bridge is",
            (lambda: [FadeIn(hm), glow(cm[0], GREEN_M, 1.0)], 0.6),
            "The drivers",
            (lambda: [FadeIn(drivers)], 0.5),
            "last year's map",
            (lambda: [Indicate(self.fl[5], color=BLUE_M)], 0.6),
            "Taking the old",
            (lambda: self.cap("taking the old bridge down: dropping the column", RED_M), 0.5),
        ])
        self.steps("The picture breaks in one place. A bridge carries cars, it doesn't hold them. Our columns hold values, so the old "
                   "values also have to be copied across.", [
            (lambda: self.cap("where the bridge picture breaks: columns hold values; the old ones must be copied"), 0.5),
            "copied across",
            (lambda: [Indicate(self.cells[("a", 0)], color=YELLOW_M)], 0.7),
        ])
        self.play(FadeOut(old_b), FadeOut(new_b), FadeOut(drivers), FadeOut(cm), FadeOut(hm), *self.uncap(), run_time=0.5)
        self.stamp("bridge")

        # ---------------- scene 4: the six steps ----------------
        self.steps("Step one: expand. Add amount_minor next to amount, empty. Old instances don't mention it, so they keep working.", [
            (lambda: [*self.phase(0), FadeOut(tname)], 0.6),
            "Add amount_minor",
            (lambda: [FadeIn(cm), FadeIn(hm), *self.set_cell("m", 0, "NULL", GREY_C), *self.set_cell("m", 1, "NULL", GREY_C),
                      *self.set_cell("m", 2, "…", GREY_B)], 0.7),
            "keep working",
            (lambda: [run_pts(path_to("a", 2), VC[1]), *self.cap("ALTER TABLE payouts ADD COLUMN amount_minor bigint", GREY_B)], 0.9),
        ])
        self.steps("Step two: deploy version 2. It writes both columns, and still reads amount. Version 1 and version 2 now run side "
                   "by side, and both are happy.", [
            (lambda: [*self.phase(1), *self.uncap()], 0.5),
            "deploy version 2",
            (lambda: self.fleet([2, 2, 2, 1, 1, 1]), 0.7),
            "It writes both",
            (lambda: [run_pts(path_to("a", 0), VC[2]), run_pts(path_to("m", 0), VC[2])], 0.9),
            (lambda: [*self.set_cell("m", 1, "4000", GREEN_M)], 0.4),
            "and still reads",
            (lambda: [run_pts(list(reversed(path_to("a", 1))), VC[2])], 0.8),
            "both are happy",
            (lambda: [run_pts(path_to("a", 4), VC[1])], 0.8),
        ])
        self.steps("Step three: backfill. Once the last version 1 instance is gone, copy amount times 100 into amount_minor, a few "
                   "thousand rows at a time, in small batches.", [
            (lambda: [*self.phase(2)], 0.5),
            "Once the last",
            (lambda: self.fleet([2] * 6), 0.8),
            "copy amount",
            (lambda: [*self.cap("amount × 100 → amount_minor, where it's NULL or different"),
                      *self.set_cell("m", 0, "4000", GREEN_M)], 0.8),
            "in small batches",
            (lambda: self.cap("a few thousand rows per batch, each in its own short transaction"), 0.5),
        ])
        self.steps("Why wait for the last version 1 to be gone? Pause and guess.", [
            (lambda: self.cap("why wait for the last v1? pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        chg = T("↑ v1 changed it", 17, BLUE_M).move_to([cx("a"), ROW_Y[2], 0])
        self.steps("Because a version 1 instance can still change amount on a row version 2 just wrote, and it never touches "
                   "amount_minor. That row is set, but wrong. So the backfill also fixes rows that differ, not only empty ones.", [
            (lambda: [*self.uncap(), *self.fleet([2, 2, 2, 1, 1, 1])], 0.5),
            "can still change",
            (lambda: [run_pts(path_to("a", 4), VC[1]), ], 0.8),
            (lambda: [*self.set_cell("a", 1, "40.00", BLUE_M), FadeOut(self.cells[("a", 2)]), FadeIn(chg)], 0.5),
            "never touches",
            (lambda: [*self.set_cell("m", 1, "4000", RED_M)], 0.5),
            "set, but wrong",
            (lambda: self.cap("amount_minor: set, but out of date", RED_M), 0.5),
            "So the backfill",
            (lambda: [*self.fleet([2] * 6), FadeOut(chg), FadeIn(self.cells[("a", 2)]), *self.set_cell("a", 1, "40.00"), *self.set_cell("m", 1, "4000", GREEN_M),
                      *self.cap("so wait for the last v1, then fix rows that differ, not only empty ones")], 0.8),
        ])
        self.stamp("backfill")
        shadow = T("shadow read: compare, log every difference", 18, GREY_B).move_to([3.05, C_BOT - 0.32, 0])
        self.steps("Step four: deploy version 3, which reads amount_minor. To be careful, it reads both for a while and logs every "
                   "difference. That's called a shadow read.", [
            (lambda: [*self.uncap(), *self.phase(3)], 0.5),
            "deploy version 3",
            (lambda: self.fleet([3, 3, 3, 3, 3, 3]), 0.9),
            "which reads",
            (lambda: [run_pts(list(reversed(path_to("m", 2))), VC[3])], 0.8),
            "reads both",
            (lambda: [run_pts(list(reversed(path_to("m", 1))), VC[3]), run_pts(list(reversed(path_to("a", 3))), GREY_B)], 0.8),
            "shadow read",
            (lambda: [FadeIn(shadow)], 0.5),
        ])
        self.steps("Step five: version 4 writes only amount_minor. Step six: contract. When no running version mentions amount, "
                   "drop it.", [
            (lambda: [*self.phase(4), FadeOut(shadow)], 0.5),
            "version 4",
            (lambda: [*self.fleet([4] * 6), *self.set_cell("a", 0, "NULL", GREY_C)], 0.8),
            (lambda: [run_pts(path_to("m", 1), VC[4])], 0.7),
            "Step six",
            (lambda: self.phase(5), 0.5),
            "drop it",
            (lambda: [FadeOut(VGroup(ca, *[self.cells[("a", i)] for i in range(3)])), *self.set_head()], 0.8),
        ])
        for i in range(3):
            self.cells[("a", i)] = None
        self.steps("That's expand and contract, also called parallel change. Expand the schema to hold both shapes, move readers and "
                   "writers across one rollout at a time, then contract it. And the rule behind every step: each step must work "
                   "with the versions on both sides of it.", [
            "That's expand",
            (lambda: self.cap("expand and contract, also called parallel change", GOLD_M, 28), 0.6),
            "move readers",
            (lambda: [LaggedStart(*[glow(self.ph[k][0], GOLD_M, 1.04) for k in range(6)], lag_ratio=0.15)], 1.2),
            "And the rule",
            (lambda: self.cap("each step must work with the versions on both sides of it", YELLOW_M, 28), 0.6),
        ], after=0.5)
        self.stamp("rule")

        # ---------------- scene 5: locks, and the cost ----------------
        q = [chip("BEGIN … (left open)", PURPLE_M, 18), chip("ALTER TABLE: waits", GOLD_M, 18),
             chip("SELECT: waits", RED_M, 18), chip("SELECT: waits", RED_M, 18)]
        qg = VGroup(*q).arrange(RIGHT, buff=0.25).move_to([0.9, ZONE_Y, 0])
        self.steps("One hazard remains. Even an instant change to a table takes the strongest lock for a moment. If someone left a "
                   "transaction open, a BEGIN with no end, the change waits for it. And every read that arrives after it waits "
                   "behind the change.", [
            (lambda: [*self.uncap()], 0.4),
            "the strongest lock",
            (lambda: self.cap("every ALTER TABLE takes the strongest lock, if only for a moment"), 0.5),
            "If someone left",
            (lambda: [FadeIn(q[0], shift=0.1 * RIGHT)], 0.5),
            "the change waits",
            (lambda: [FadeIn(q[1], shift=0.1 * RIGHT)], 0.5),
            "And every read",
            (lambda: [FadeIn(q[2], shift=0.1 * RIGHT)], 0.4),
            (lambda: [FadeIn(q[3], shift=0.1 * RIGHT)], 0.4),
        ])
        self.steps("A one-millisecond change can stop every read of the table. So set a lock timeout of a few seconds, and retry if "
                   "it fails.", [
            (lambda: self.cap("a one-millisecond change can stop every read", RED_M), 0.5),
            "So set a lock",
            (lambda: [*self.cap("SET lock_timeout = '2s'; then retry", GREEN_M), FadeOut(q[1]), FadeOut(q[2]), FadeOut(q[3])], 0.7),
        ])
        self.steps("And the cost. A change that used to be one file is now several releases, a backfill that may run for hours, and "
                   "a team that knows what each version may touch. Nothing in the database enforces the order.", [
            (lambda: [FadeOut(q[0]), *self.cap("several releases, a backfill that may run for hours")], 0.5),
            "Nothing in the",
            (lambda: self.cap("nothing in the database enforces the order: the team does", RED_M), 0.5),
        ])

        # ---------------- scene 6: the moral, and a check ----------------
        self.steps("So, how do you change a column under running code? Like a bridge. Build the new one beside the old, move the "
                   "traffic, and take the old one down last.", [
            (lambda: [*self.uncap(), *[glow(self.ph[k][0], GOLD_M, 1.04) for k in (0, 5)]], 0.8),
            "Build the new",
            (lambda: self.cap("build the new one beside the old, move the traffic, take the old one down last", WHITE), 0.5),
        ], after=0.5)
        # the check: back to the moment before the contract, with v3 everywhere
        ca2 = column_box("a", BLUE_M)
        self.steps("One quick check. A teammate's version 4 stops writing amount, and the same release drops the column. What goes "
                   "wrong? Pause and think.", [
            (lambda: [*self.uncap(), *self.phase(4), FadeIn(ca2), *self.set_head("amount", "euros, numeric(12,2)"), *self.set_cell("a", 0, "40.00"),
                      *self.set_cell("a", 1, "40.00"), *self.fleet([3] * 6)], 0.8),
            "version 4 stops",
            (lambda: self.fleet([4, 3, 3, 3, 3, 3]), 0.5),
            "drops the column",
            (lambda: [FadeOut(VGroup(ca2, self.cells[("a", 0)], self.cells[("a", 1)])), *self.set_head()], 0.6),
            "Pause and think",
            (lambda: self.cap("v4 and the DROP in one release: what goes wrong? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.cells[("a", 0)] = self.cells[("a", 1)] = None
        self.countdown(3.0)
        xs2 = VGroup(*[tick(False, 0.12).next_to(inst(i, 3), RIGHT, buff=0.15) for i in range(1, 6)])
        self.steps("The drop runs when the first version 4 starts. The others are still version 3, and still write amount, so every "
                   "one of their writes fails until the rollout ends. And there's no going back to version 3: its column is gone.", [
            (lambda: [*self.uncap(), run_pts(path_to("a", 3), VC[3])], 0.8),
            "so every",
            (lambda: [LaggedStart(*[Create(x) for x in xs2], lag_ratio=0.15),
                      *self.set_zone(M('ERROR: column "amount" does not exist', 20, RED_M).move_to([2.2, 0, 0]))], 0.9),
            "And there's no",
            (lambda: self.cap("no rollback to v3 either: ship the contract one release later", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.wait(2.0)
