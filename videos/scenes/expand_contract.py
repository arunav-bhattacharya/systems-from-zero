from sfz import *

SAY.insert(0, (r"\bamount_minor\b", "amount minor"))
SAY.insert(0, (r"\bNULL\b", "null"))

INST_X = [-5.0 + 2.0 * i for i in range(6)]          # six instances of the payout service
INST_Y = 2.85
VC = {1: BLUE_M, 2: GOLD_M, 3: TEAL_M, 4: PURPLE_M}
COL_X = {"id": -3.0, "amount": -0.6, "minor": 2.4}     # payouts table columns
TL, TR = -4.0, 4.0
HEAD_Y = 1.5
ROW_Y = [0.9, 0.3, -0.3, -0.9]
PH_Y = -2.75
PHASES = ["expand", "dual write", "backfill", "read new", "write new", "contract"]
ERR_Y = -1.85


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


def fill(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    a, b = path.get_start(), path.get_end()
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])




def inst(i, v, bad=False):
    c = RED_M if bad else VC[v]
    r = RoundedRectangle(corner_radius=0.1, width=1.7, height=0.72, stroke_color=c, stroke_width=3)
    r.set_fill(fill(c), 1).move_to([INST_X[i], INST_Y, 0])
    return VGroup(r, T(f"v{v}", 28, c).move_to([INST_X[i], INST_Y, 0]))


def cell(col, y, s, color=WHITE, size=26):
    return M(s, size, color).move_to([COL_X[col], y, 0])


def phase(i, state="off"):
    x = -5.375 + 2.15 * i
    c = {"off": GREY_D, "on": YELLOW_M, "done": GREEN_M}[state]
    r = RoundedRectangle(corner_radius=0.1, width=2.0, height=0.75, stroke_color=c, stroke_width=2.5 if state == "off" else 3.5)
    r.set_fill(fill(c, 0.12 if state == "off" else 0.16), 1).move_to([x, PH_Y, 0])
    tc = GREY_B if state == "off" else WHITE
    return VGroup(r, T(f"{i + 1}. {PHASES[i]}", 21, tc).move_to([x, PH_Y, 0]))


class ExpandContract(Base):
    """enc-03, section 3: payouts.amount (numeric euros) becomes amount_minor (bigint cents) under a rolling upgrade of six
    instances. Done in one step, every v1 instance fails with column "amount" does not exist (SQLSTATE 42703). Expand and
    contract: add amount_minor, v2 writes both, backfill after the last v1 is gone, v3 reads the new column, v4 writes only
    it, then drop amount. Row values (40.00, 12.50, 8.75, 3.20) are invented."""

    def construct(self):
        self.title_card("Expand and contract", "changing a column while two versions of the code run")

        insts = [inst(i, 1) for i in range(6)]
        frame = RoundedRectangle(corner_radius=0.12, width=TR - TL, height=HEAD_Y - ROW_Y[3] + 0.75, stroke_color=GREY_B, stroke_width=2.5)
        frame.set_fill(BLACK, 1).move_to([0, (HEAD_Y + 0.37 + ROW_Y[3] - 0.38) / 2, 0])
        ttl = left_at(T("payouts table", 20, GREY_B), TL, HEAD_Y + 0.62)
        hline = Line([TL, HEAD_Y - 0.3, 0], [TR, HEAD_Y - 0.3, 0], stroke_width=1.5, color=GREY_D)
        h_id = cell("id", HEAD_Y, "id", GREY_B)
        h_am = cell("amount", HEAD_Y, "amount", GREY_B)
        vals = ["40.00", "12.50"]
        r_id = [cell("id", ROW_Y[k], str(k + 1)) for k in range(2)]
        r_am = [cell("amount", ROW_Y[k], vals[k]) for k in range(2)]
        self.steps("The payouts table keeps each amount in euros, like 40.00. You want a column of whole cents instead, "
                   "amount_minor, like every other money field. Six instances of the payout service use this column all day.", [
            (lambda: [FadeIn(frame), FadeIn(ttl), Create(hline), FadeIn(h_id), FadeIn(h_am), *[FadeIn(m) for m in r_id + r_am]], 1.0),
            "You want",
            (lambda: [Indicate(h_am, color=YELLOW_M)], 0.8),
            "Six instances",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * DOWN) for b in insts], lag_ratio=0.12)], 1.2),
        ])

        def roll(idx, v):
            return [LaggedStart(*[Transform(insts[i], inst(i, v)) for i in idx], lag_ratio=0.25)]

        self.steps("A deploy replaces them one at a time, so for a few minutes old code and new code run side by side "
                   "against the same table.", [
            (lambda: roll([0, 1], 2), 1.4),
            "side by side",
            (lambda: [*[glow(insts[i][0], VC[2], 1.05) for i in (0, 1)], *[glow(insts[i][0], VC[1], 1.05) for i in range(2, 6)]], 1.0),
        ])

        h_new = cell("amount", HEAD_Y, "amount_minor", GREY_B)
        err = chip('ERROR: column "amount" does not exist', RED_M, 22).move_to([0, ERR_Y, 0])
        xs = [tick(False, 0.18).move_to([INST_X[i] + 0.72, INST_Y + 0.32, 0]) for i in range(2, 6)]
        self.steps("Rename and convert the column in one migration, and the moment it runs, every old instance fails: "
                   "column amount does not exist. Stopping the service first means downtime instead.", [
            (lambda: [Transform(h_am, h_new), Transform(r_am[0], cell("amount", ROW_Y[0], "4000")),
                      Transform(r_am[1], cell("amount", ROW_Y[1], "1250"))], 0.9),
            "every old instance",
            (lambda: [*[Transform(insts[i], inst(i, 1, True)) for i in range(2, 6)], *[Create(x) for x in xs]], 0.8),
            "column amount",
            (lambda: [FadeIn(err, shift=0.1 * UP)], 0.7),
        ])

        phs = [phase(i) for i in range(6)]
        self.steps("Instead, change it in phases. Each phase works with the code on both sides of it.", [
            (lambda: [FadeOut(err), *[FadeOut(x) for x in xs], Transform(h_am, cell("amount", HEAD_Y, "amount", GREY_B)),
                      Transform(r_am[0], cell("amount", ROW_Y[0], "40.00")), Transform(r_am[1], cell("amount", ROW_Y[1], "12.50")),
                      *[Transform(insts[i], inst(i, 1)) for i in range(6)]], 1.0),
            "in phases",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * UP) for p in phs], lag_ratio=0.12)], 1.1),
        ])

        # ---- 1. expand ---------------------------------------------------------------------------------------------
        h_mi = cell("minor", HEAD_Y, "amount_minor", YELLOW_M)
        r_mi = [cell("minor", ROW_Y[k], "NULL", GREY_C) for k in range(2)]
        self.steps("First, expand: add amount_minor as a new, empty column. It allows NULL, so old inserts that "
                   "never mention it keep working.", [
            (lambda: [Transform(phs[0], phase(0, "on"))], 0.5),
            "add amount_minor",
            (lambda: [FadeIn(h_mi, shift=0.1 * LEFT), *[FadeIn(m) for m in r_mi]], 0.8),
            "so old inserts",
            (lambda: [*[glow(insts[i][0], VC[1], 1.05) for i in range(6)]], 0.9),
        ])

        r3 = VGroup(cell("id", ROW_Y[2], "3"), cell("amount", ROW_Y[2], "8.75"), cell("minor", ROW_Y[2], "875", GOLD_M))
        r4 = VGroup(cell("id", ROW_Y[3], "4"), cell("amount", ROW_Y[3], "3.20"), cell("minor", ROW_Y[3], "NULL", RED_M))

        def write(i, cols, y, color):
            return [flow(Line([INST_X[i], INST_Y - 0.4, 0], [COL_X[c], y + 0.2, 0]), color, 0.6) for c in cols]

        self.steps("Then deploy v2, which writes both columns in one statement but still reads amount. "
                   "Until the rollout ends, a v1 instance can still add a row with no amount_minor.", [
            (lambda: [Transform(phs[0], phase(0, "done")), Transform(phs[1], phase(1, "on"))], 0.5),
            "deploy v2",
            (lambda: roll([0, 1, 2, 3], 2), 1.2),
            "writes both",
            (lambda: write(1, ["amount", "minor"], ROW_Y[2], GOLD_M), 0.7),
            (lambda: [FadeIn(r3, shift=0.1 * DOWN)], 0.5),
            "a v1 instance",
            (lambda: write(5, ["amount"], ROW_Y[3], BLUE_M), 0.7),
            (lambda: [FadeIn(r4, shift=0.1 * DOWN)], 0.5),
        ])

        self.steps("Once the last v1 instance is gone, a backfill job fills every NULL with amount times a hundred, "
                   "a few thousand rows per transaction.", [
            (lambda: [Transform(phs[1], phase(1, "done")), Transform(phs[2], phase(2, "on")), *roll([4, 5], 2)], 1.0),
            "a backfill job",
            (lambda: [Transform(r_mi[0], cell("minor", ROW_Y[0], "4000", GREEN_M))], 0.45),
            (lambda: [Transform(r_mi[1], cell("minor", ROW_Y[1], "1250", GREEN_M))], 0.45),
            (lambda: [Transform(r4[2], cell("minor", ROW_Y[3], "320", GREEN_M))], 0.45),
        ])

        rcol = RoundedRectangle(corner_radius=0.08, width=2.7, height=HEAD_Y - ROW_Y[3] + 0.5, stroke_color=TEAL_M, stroke_width=3)
        rcol.move_to([COL_X["minor"], (HEAD_Y + ROW_Y[3]) / 2, 0])
        self.steps("Deploy v3, which reads amount_minor. For a while it also reads amount and logs any row where the two disagree.", [
            (lambda: [Transform(phs[2], phase(2, "done")), Transform(phs[3], phase(3, "on")), *roll(range(6), 3)], 1.4),
            "which reads",
            (lambda: [Create(rcol), *[flow(Line([COL_X["minor"], HEAD_Y + 0.25, 0], [INST_X[i], INST_Y - 0.4, 0]), TEAL_M, 0.6)
                                      for i in (2, 4)]], 0.9),
            "and logs",
            (lambda: [*[Indicate(m, color=TEAL_M) for m in [r_am[0], r_am[1], r3[1], r4[1]]]], 0.9),
        ])

        amg = VGroup(h_am, *r_am, r3[1], r4[1])
        self.steps("Then v4 writes only amount_minor, and nothing reads amount any more.", [
            (lambda: [Transform(phs[3], phase(3, "done")), Transform(phs[4], phase(4, "on")), FadeOut(rcol), *roll(range(6), 4)], 1.4),
            "nothing reads",
            (lambda: [amg.animate.set_opacity(0.3)], 0.8),
        ])

        mig = VGroup(h_mi, *r_mi, r3[2], r4[2])
        self.steps("Last, contract: once no running version mentions amount, drop it.", [
            (lambda: [Transform(phs[4], phase(4, "done")), Transform(phs[5], phase(5, "on"))], 0.5),
            "drop it",
            (lambda: [FadeOut(amg, shift=0.2 * DOWN)], 0.7),
            (lambda: [mig.animate.shift((COL_X["amount"] - COL_X["minor"] + 0.2) * RIGHT).set_color(WHITE)], 0.8),
        ])

        self.steps("One rename became several deploys, and at no point did a running version see a schema it couldn't use.", [
            (lambda: [Transform(phs[5], phase(5, "done"))], 0.5),
            "several deploys",
            (lambda: [LaggedStart(*[glow(p[0], GREEN_M, 1.05) for p in phs], lag_ratio=0.15)], 1.4),
            "at no point",
            (lambda: [*[glow(b[0], VC[4], 1.05) for b in insts]], 1.0),
        ])
        self.wait(0.6)
