from sfz import *

SAY.insert(0, (r"\bc-1\b", "C one"))
SAY.insert(0, (r"\bo-(\d)\b", r"O \1"))
SAY.insert(0, (r"\b09:00\b", "nine o'clock"))
SAY.insert(0, (r"\b09:30\b", "nine thirty"))
SAY.insert(0, (r"\b09:59\b", "nine fifty-nine"))
SAY.insert(0, (r"\b10:0([1-9])\b", r"ten oh \1"))
SAY.insert(0, (r"\b10:00\b", "ten o'clock"))
SAY.insert(0, (r"\b11:00\b", "eleven o'clock"))
SAY.insert(0, (r"\bcustomer-tiers\b", "customer tiers"))
SAY.insert(0, (r"(\d)%", r"\1 percent"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TL_Y, TL_X0 = 2.75, -5.0


def tx(minutes):
    """x on the timeline for minutes after 09:00 (10 units for 90 minutes)."""
    return TL_X0 + minutes / 9.0


ARR_Y = 1.45
BOX_Y, BOX_W, BOX_H = -0.4, 5.9, 2.0
LX, RX = -3.4, 3.4
ROW_Y = [-0.3, -0.92]
RES_Y = -1.95
CAP_Y, BAR_Y = -3.22, -2.72
SILVER = "#C8CCD2"


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

    # --- small state helpers: each returns animations and records what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
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
        return [FadeOut(self.lab.pop(k)) for k in keys if k in self.lab]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


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


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))



def tbox(x, color, title, w=BOX_W):
    r = RoundedRectangle(corner_radius=0.16, width=w, height=BOX_H, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.08), 1)
    r.move_to([x, BOX_Y, 0])
    t = fit(T(title, 21, color), w - 0.5).move_to([x, BOX_Y + BOX_H / 2 - 0.3, 0])
    return r, t


def trow(x, k, text, color):
    r = RoundedRectangle(corner_radius=0.1, width=5.0, height=0.5, stroke_color=color, stroke_width=2.2).set_fill(fillc(color, 0.2), 1)
    r.move_to([x, ROW_Y[k], 0])
    return VGroup(r, M(text, 20).move_to(r))


def res(x, text, color, dx=0.0):
    return chip(text, color, 20, mono=True).move_to([x + dx, RES_Y, 0])


def order_chip(text):
    return chip(text, BLUE_M, 20, mono=True).move_to([0, ARR_Y, 0])


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.4, height=4.2, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.05, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.95, 1.85)
    rows = VGroup()
    cw = M("x" * 40, 14).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 2.95 + ind, 1.3 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["// the table keeps every version, 7 days of it",
        "KTable<String, String> tiers = builder.table(",
        "    \"customer-tiers\",",
        "    Materialized.as(Stores",
        "        .persistentVersionedKeyValueStore(",
        "            \"tiers\", Duration.ofDays(7))));",
        "",
        "orders.join(tiers, (o, t) -> cashback(o, t));"]
KOTLIN = ["// the table keeps every version, 7 days of it",
          "val tiers = builder.table(",
          "    \"customer-tiers\",",
          "    Materialized.`as`(Stores",
          "        .persistentVersionedKeyValueStore(",
          "            \"tiers\", Duration.ofDays(7))))",
          "",
          "orders.join(tiers) { o, t -> cashback(o, t) }"]


class StreamTableJoin(Base):
    """stream-06, section 1. Mira's 09:30 coffee reaches the cashback program at 10:01, after her 10:00 upgrade: gold, 5%;
    a rerun next week says silver, 2%. Enrichment: ask the database (3,000 a second x 5 ms = 15 waiting), or keep a
    local table. The plain table overwrites silver with gold; o-1 arriving late gets gold; arriving early, silver: not
    deterministic. The logbook: a versioned table picks the version at or before the order's own time: silver both
    times. Limits: 7 days of history; a late upgrade (o-2 at 10:02) needs a grace period (5 minutes, stream time past
    10:07). The code in Java and Kotlin, the moral (or print it on the receipt), and a check (o-3 at 09:59)."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Gold one week, silver the next", "join with the tier as it was")

        # ---- the timeline ----
        axis = Line([tx(0), TL_Y, 0], [tx(90), TL_Y, 0], stroke_width=2, color=GREY_D)
        seg_s = Line([tx(0), TL_Y, 0], [tx(60), TL_Y, 0], stroke_width=8, color=SILVER)
        seg_g = Line([tx(60), TL_Y, 0], [tx(90), TL_Y, 0], stroke_width=8, color=GOLD_M)
        ticks = VGroup(*[VGroup(Line([tx(m), TL_Y - 0.12, 0], [tx(m), TL_Y + 0.12, 0], stroke_width=2, color=GREY_B),
                                M(s, 17, GREY_B).move_to([tx(m), TL_Y - 0.38, 0]))
                         for m, s in ((0, "09:00"), (30, "09:30"), (60, "10:00"), (90, "10:30"))])
        lab_s = T("silver: 2% back", 19, SILVER).move_to([tx(12), TL_Y + 0.38, 0])
        lab_g = T("gold: 5% back", 19, GOLD_M).move_to([tx(78), TL_Y + 0.38, 0])
        who = left_at(T("Mira (c-1)", 19, GREY_B), -6.55, TL_Y)
        cup = Dot(radius=0.11, color=BLUE_M).move_to([tx(30), TL_Y, 0]).set_z_index(5)
        cup_l = T("coffee", 19, BLUE_M).move_to([tx(30), TL_Y + 0.38, 0])

        self.steps("Picture a café chain with a loyalty scheme. Silver members get 2% of each purchase back, and gold members get 5%.", [
            "Picture",
            (lambda: [Create(axis), FadeIn(ticks), FadeIn(who)], 0.8),
            "Silver members",
            (lambda: [Create(seg_s), FadeIn(lab_s)], 0.6),
            "gold members",
            (lambda: [Create(seg_g), FadeIn(lab_g)], 0.6),
        ])
        self.steps("Mira is upgraded to gold at 10:00. She bought a coffee at 09:30, but that payment was held up, "
                   "and reached the program that works out cashback at 10:01.", [
            "upgraded to gold",
            (lambda: [glow(seg_g, GOLD_M, 1.0)], 0.6),
            "a coffee at 09:30",
            (lambda: [FadeIn(cup, scale=0.5), FadeIn(cup_l)], 0.5),
            "held up",
            (lambda: [*self.put("arr", order_chip("coffee: bought 09:30, arrives 10:01"))], 0.6),
        ])
        five = res(0, "5% back", GOLD_M)
        two = res(0, "next week: 2% back", SILVER)
        self.steps("The program looks up Mira's tier, finds gold, and gives her 5%. Next week, the company runs the same program again "
                   "over the same payments, to check its sums. This time Mira's coffee gets 2%.", [
            "finds gold",
            (lambda: [FadeIn(five.move_to([-1.8, 0.2, 0]))], 0.5),
            "This time",
            (lambda: [FadeIn(two.move_to([1.8, 0.2, 0]))], 0.5),
        ])
        self.steps("Same data, same code, two answers. Which one is right, and why did the program change its mind?", [
            (lambda: self.cap("same data, same code, two answers", WHITE), 0.6),
            "Which one",
            (lambda: self.cap("which one is right?", YELLOW_M), 0.5),
        ], after=0.4)

        # ---------------- scene 2: the lookup ----------------
        db_r, db_t = tbox(RX, GREY_B, "the tiers database (another team's)")
        topic = T("every change: a record on topic customer-tiers", 19, GREY_B).move_to([RX, BOX_Y - 0.55, 0])
        self.steps("Adding a detail to each event from a table is called enrichment. Each order needs its customer's tier, "
                   "because the tier sets the cashback.", [
            (lambda: [*self.uncap(), FadeOut(five), FadeOut(two), *self.drop("arr")], 0.6),
            "called enrichment",
            (lambda: self.cap("enrichment: add a detail to each event from a table", WHITE), 0.6),
        ])
        self.steps("The tiers live in a database that another team runs, and every change to it is copied as a record "
                   "onto a Kafka topic, customer-tiers.", [
            "The tiers live",
            (lambda: [FadeIn(db_r), FadeIn(db_t)], 0.6),
            "every change",
            (lambda: [FadeIn(topic)], 0.5),
        ])
        qs = VGroup(*[Dot(radius=0.07, color=YELLOW_M).move_to([RX - 2.45 + 0.35 * i, BOX_Y + 0.1, 0]) for i in range(15)])
        self.steps("Version 1 asks the database for every order. At 3,000 orders a second and 5 ms a question, "
                   "that's 15 questions waiting at every moment.", [
            "asks the database",
            (lambda: [*self.cap("version 1: ask the database for every order")], 0.5),
            "15 questions",
            (lambda: [LaggedStart(*[FadeIn(q, scale=0.5) for q in qs], lag_ratio=0.1),
                      *self.cap("3,000 a second, 5 ms each: 15 questions always waiting", RED_M)], 1.2),
        ])
        p_r, p_t = tbox(LX, BLUE_M, "plain table: one row per customer")
        self.steps("Version 2 keeps a local copy: a table built from customer-tiers, on the program's own disk, as in the last lesson. "
                   "It keeps the latest value for each customer, and a lookup takes microseconds.", [
            "Version 2",
            (lambda: [FadeIn(p_r), FadeIn(p_t), *self.cap("version 2: a local copy on the program's own disk")], 0.7),
            "the latest value",
            (lambda: [dot_run([RX - 2.9, BOX_Y, 0], [LX + 2.9, BOX_Y, 0], GREY_B, 0.6)], 0.7),
            "microseconds",
            (lambda: [*self.cap("one row per customer; a lookup takes microseconds"), FadeOut(qs)], 0.6),
        ], after=0.3)

        # ---------------- scene 3: the late coffee ----------------
        self.row = None

        def set_row(text, color):
            new = trow(LX, 0, text, color)
            old, self.row = self.row, new
            return [swap(old, new)]

        self.steps("Now watch c-1, that's Mira. Her silver record arrives: c-1 is silver from 09:00.", [
            (lambda: [*self.uncap(), FadeOut(db_r), FadeOut(db_t), FadeOut(topic)], 0.6),
            "Her silver record",
            (lambda: [dot_run([tx(0), TL_Y - 0.15, 0], [LX, ROW_Y[0] + 0.25, 0], SILVER, 0.7)], 0.75),
            (lambda: set_row("c-1: silver", SILVER), 0.5),
        ])
        self.steps("Then the upgrade arrives, and the row is overwritten: gold. Silver is gone. "
                   "A tier change sends nothing on, so orders joined earlier keep what they got.", [
            "Then the upgrade",
            (lambda: [dot_run([tx(60), TL_Y - 0.15, 0], [LX, ROW_Y[0] + 0.25, 0], GOLD_M, 0.7)], 0.75),
            "overwritten",
            (lambda: set_row("c-1: gold", GOLD_M), 0.6),
            "Silver is gone",
            (lambda: self.cap("the row is overwritten: silver is gone", RED_M), 0.5),
            "sends nothing on",
            (lambda: self.cap("a tier change sends nothing on", WHITE), 0.5),
        ])
        r1 = res(LX, "o-1: gold, 5%", RED_M)
        self.steps("Now o-1, the coffee placed at 09:30, finally arrives at 10:01. The join looks up c-1, finds gold, "
                   "the only row it has, and pays 5%. No error. No warning.", [
            (lambda: [*self.uncap(), *self.put("arr", order_chip("o-1: placed 09:30, arrives 10:01"))], 0.6),
            "The join looks up",
            (lambda: [dot_run([-1.5, ARR_Y - 0.3, 0], [LX + 1.0, ROW_Y[0] + 0.25, 0], BLUE_M, 0.6)], 0.65),
            "finds gold",
            (lambda: [glow(self.row[0], GOLD_M, 1.04)], 0.5),
            "pays 5%",
            (lambda: [FadeIn(r1, shift=0.1 * DOWN)], 0.5),
            "No error",
            (lambda: self.cap("no error, no warning", RED_M), 0.5),
        ], after=0.3)

        # ---------------- scene 4: next week ----------------
        self.steps("Next week, the same topics are read again, and this time the partitions are read in a different order. "
                   "o-1 arrives before the upgrade. What does the join say now? Pause and guess.", [
            (lambda: [*self.cap("next week: the same topics, read in a different order"), r1.animate.move_to([LX - 1.5, RES_Y, 0])], 0.7),
            "o-1 arrives before",
            (lambda: [*set_row("c-1: silver", SILVER), *self.put("arr", order_chip("o-1: placed 09:30, arrives before the upgrade"))], 0.7),
            "Pause and guess",
            (lambda: self.cap("what does the join say now?  pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        r2 = res(LX, "o-1: silver, 2%", SILVER).move_to([LX + 1.5, RES_Y, 0])
        self.steps("Silver. Same input, two answers. A join like this isn't deterministic: two runs over the same data disagree.", [
            (lambda: [*self.uncap(), dot_run([-1.5, ARR_Y - 0.3, 0], [LX + 1.0, ROW_Y[0] + 0.25, 0], BLUE_M, 0.5)], 0.55),
            (lambda: [FadeIn(r2, shift=0.1 * DOWN)], 0.5),
            "isn't deterministic",
            (lambda: [*self.cap("not deterministic: two runs over the same data disagree", RED_M), glow(r1[0], RED_M, 1.06),
                      glow(r2[0], RED_M, 1.06)], 0.8),
        ])
        self.steps("It's a cashier who charges whatever the board says when you reach the front of the queue, "
                   "not when you picked up the cup.", [
            (lambda: [*set_row("c-1: gold", GOLD_M), *self.drop("arr")], 0.6),
        ], after=0.4)
        self.stamp("break")

        # ---------------- scene 5: the logbook ----------------
        v_r, v_t = tbox(RX, TEAL_M, "versioned table: every version, with its start")
        v1 = trow(RX, 0, "c-1: silver from 09:00", SILVER)
        v2 = trow(RX, 1, "c-1: gold from 10:00", GOLD_M)
        board = T("wall board", 19, BLUE_M)
        self.steps("Back to the café. The wall board has one line per member, rubbed out and rewritten.", [
            (lambda: [*self.cap("the wall board: one line per member, rubbed out and rewritten"), glow(p_r, BLUE_M, 1.02)], 0.8),
            "rubbed out",
            (lambda: [*set_row("c-1: silver", SILVER)], 0.4),
            (lambda: [*set_row("c-1: gold", GOLD_M)], 0.4),
        ])
        self.steps("Now picture a logbook instead, with a dated line for every change: Mira, silver from 09:00. Mira, gold from 10:00.", [
            "a logbook",
            (lambda: [FadeIn(v_r), *self.put("vt", fit(T("a logbook: a dated line for every change", 21, TEAL_M), BOX_W - 0.5)
                                              .move_to(v_t))], 0.7),
            "silver from 09:00",
            (lambda: [FadeIn(v1, shift=0.1 * UP)], 0.5),
            "gold from 10:00",
            (lambda: [FadeIn(v2, shift=0.1 * UP)], 0.5),
        ])
        self.steps("And look at the time printed on the till receipt: 09:30. Which line was in force then? Silver. "
                   "It doesn't matter when the receipt reaches the office.", [
            "the till receipt",
            (lambda: [glow(cup_l, BLUE_M, 1.2)], 0.6),
            "Which line",
            (lambda: [glow(seg_s, SILVER, 1.0), glow(cup, YELLOW_M, 1.4)], 0.7),
            "Silver",
            (lambda: [glow(v1[0], SILVER, 1.04)], 0.6),
        ])
        self.steps("Map it out. The wall board is the plain table. The logbook is a table that keeps every version, "
                   "with the time it took effect. And the receipt's time is the order's own timestamp.", [
            (lambda: [*self.cap("wall board = the plain table"), glow(p_r, BLUE_M, 1.02)], 0.6),
            "The logbook is",
            (lambda: [*self.cap("logbook = a table that keeps every version, with its start time"), glow(v_r, TEAL_M, 1.02)], 0.6),
            "the receipt's time",
            (lambda: [*self.cap("the receipt's time = the order's own timestamp"), glow(cup_l, BLUE_M, 1.2)], 0.6),
        ])
        self.steps("Kafka Streams calls this a versioned table. The join picks the version with the latest time at or before the order's time.", [
            "a versioned table",
            (lambda: [*self.put("vt", v_t)], 0.6),
            "at or before",
            (lambda: [*self.cap("pick the version with the latest time at or before the order's time", YELLOW_M), glow(v1[0], YELLOW_M, 1.04)], 0.8),
        ])
        g1 = res(RX, "silver", GREEN_M, -1.25)
        g2 = res(RX, "silver", GREEN_M, 1.25)
        self.steps("Run it both ways: silver, and silver.", [
            (lambda: [dot_run([1.5, ARR_Y - 0.3, 0], [RX - 1.0, ROW_Y[0] + 0.25, 0], BLUE_M, 0.45)], 0.5),
            (lambda: [FadeIn(g1, shift=0.1 * DOWN)], 0.3),
            "and silver",
            (lambda: [dot_run([1.5, ARR_Y - 0.3, 0], [RX - 1.0, ROW_Y[0] + 0.25, 0], BLUE_M, 0.45)], 0.5),
            (lambda: [FadeIn(g2, shift=0.1 * DOWN)], 0.3),
        ], after=0.4)
        self.steps("Which answer was right? Silver. She paid at 09:30.", [
            (lambda: [*self.cap("which answer was right? silver: she paid at 09:30", GREEN_M)], 0.6),
        ], after=0.5)
        self.stamp("versioned")

        # ---------------- scene 6: its limits ----------------
        self.steps("Two limits. First, the logbook isn't endless. Here it keeps 7 days. An order older than that can't be answered: "
                   "an inner join drops it, and a left join joins it with nothing.", [
            (lambda: [*self.cap("limit 1: history is bounded, here 7 days", WHITE), ], 0.6),
            "an inner join drops",
            (lambda: self.cap("older than 7 days: an inner join drops it, a left join gets nothing", WHITE), 0.7),
        ])
        o2 = Dot(radius=0.11, color=BLUE_M).move_to([tx(62), TL_Y, 0]).set_z_index(5)
        o2_l = T("o-2", 19, BLUE_M).move_to([tx(62) + 0.25, TL_Y + 0.38, 0])
        s3 = res(RX, "o-2: silver", RED_M)
        self.steps("Second, versions fix late orders, not late table updates. Order o-2 is placed at 10:02, but this time "
                   "the upgrade itself is late, and o-2 gets there first.", [
            (lambda: [*self.cap("limit 2: versions fix late orders, not late table updates", WHITE), FadeOut(g1), FadeOut(g2),
                      FadeOut(r1), FadeOut(r2)], 0.6),
            "Order o-2",
            (lambda: [FadeIn(o2, scale=0.5), FadeIn(o2_l)], 0.5),
            "the upgrade itself",
            (lambda: [v2.animate.set_opacity(0.15)], 0.5),
            "o-2 gets there",
            (lambda: [*self.put("arr", order_chip("o-2: placed 10:02, arrives before the upgrade"))], 0.6),
        ])
        self.steps("The table only knows silver, so o-2 gets silver.", [
            (lambda: [dot_run([1.5, ARR_Y - 0.3, 0], [RX - 1.0, ROW_Y[0] + 0.25, 0], BLUE_M, 0.5)], 0.55),
            (lambda: [FadeIn(s3, shift=0.1 * DOWN)], 0.5),
        ])
        hold = VGroup(Rectangle(width=3.0, height=0.34, stroke_color=YELLOW_M, stroke_width=2).move_to([-1.1, 0.83, 0]))
        fill = Rectangle(width=3.0, height=0.34, stroke_width=0).set_fill(YELLOW_M, 0.5).move_to([-1.1, 0.83, 0])
        hold_l = left_at(T("grace: hold 5 minutes", 18, YELLOW_M), 0.6, 0.83)
        s4 = res(RX, "o-2: gold", GREEN_M)
        self.steps("The fix is a grace period on the order side: hold each order 5 minutes, in stream time.", [
            (lambda: [FadeOut(s3), *self.cap("the fix: a grace period on the order side", YELLOW_M)], 0.6),
            "hold each order",
            (lambda: [Create(hold), FadeIn(hold_l)], 0.6),
        ])
        fill.stretch_to_fit_width(0.01).align_to(hold, LEFT)
        self.steps("o-2 waits until stream time passes 10:07, the upgrade arrives meanwhile, and o-2 gets gold.", [
            "o-2 waits",
            (lambda: [fill.animate.stretch_to_fit_width(3.0).move_to([-1.1, 0.83, 0])], 1.4),
            "the upgrade arrives",
            (lambda: [v2.animate.set_opacity(1)], 0.5),
            "o-2 gets gold",
            (lambda: [dot_run([0.4, 0.83, 0], [RX - 1.0, ROW_Y[1] + 0.25, 0], BLUE_M, 0.5)], 0.55),
            (lambda: [FadeIn(s4, shift=0.1 * DOWN)], 0.4),
        ])
        self.steps("The price is that every order now comes out 5 minutes later.", [
            (lambda: [*self.cap("the price: every order comes out 5 minutes later", RED_M)], 0.6),
        ], after=0.4)

        # ---------------- scene 7: the code ----------------
        diagram = VGroup(axis, seg_s, seg_g, ticks, lab_s, lab_g, who, cup, cup_l, o2, o2_l, p_r, p_t, self.row, v_r, v1, v2,
                         hold, fill, hold_l, s4, *self.lab.values())
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(panel, rs, color):
            return [panel[2][r].animate(rate_func=there_and_back).set_color(color) for r in rs]

        self.steps("In Java and Kotlin, the change is the store: a persistent versioned store with 7 days of history. "
                   "The join itself stays the same.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "a persistent versioned",
            (lambda: [*hl(jp, (3, 4, 5), TEAL_M), *hl(kp, (3, 4, 5), TEAL_M)], 1.6),
            "The join itself",
            (lambda: [*hl(jp, (7,), YELLOW_M), *hl(kp, (7,), YELLOW_M)], 1.2),
        ], after=0.5)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: join each event with the table as it was when the event happened, "
                   "not as it is when the event arrives.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: [FadeOut(hold), FadeOut(fill), FadeOut(hold_l), FadeOut(s4), *self.drop("arr"),
                      *self.cap("join with the table as it was when the event happened", YELLOW_M, 26)], 0.6),
        ])
        self.steps("Or print the answer on the receipt: if the till writes the tier into the order when Mira pays, "
                   "no later join can change it.", [
            (lambda: self.cap("or write the tier into the order when she pays", WHITE), 0.6),
        ], after=0.3)
        o3 = Dot(radius=0.11, color=PURPLE_M).move_to([tx(59), TL_Y, 0]).set_z_index(6)
        o3_l = T("o-3", 19, PURPLE_M).move_to([tx(59) - 0.25, TL_Y + 0.38, 0])
        self.steps("One quick check. Order o-3 was placed at 09:59 and arrives at 11:00. What does the versioned join give it? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(o3, scale=0.5), FadeIn(o3_l),
                      *self.put("arr", chip("o-3: placed 09:59, arrives 11:00", PURPLE_M, 20, mono=True).move_to([0, ARR_Y, 0]))], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        s5 = res(RX, "o-3: silver", GREEN_M)
        self.steps("Silver. 09:59 is before 10:00, so the silver line was in force.", [
            (lambda: [*self.uncap(), glow(seg_s, SILVER, 1.0), glow(o3, YELLOW_M, 1.4)], 0.6),
            (lambda: [FadeIn(s5, shift=0.1 * DOWN), glow(v1[0], SILVER, 1.04)], 0.6),
        ], after=0.4)
        self.play(*self.cap("the tier in force when she paid, every time", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
