from sfz import *

SAY.insert(0, (r"\bRocksDB\b", "rocks D B"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\bacct-(\d+)\b", r"account \1"))
SAY.insert(0, (r"\bnum\.standby\.replicas\b", "num standby replicas"))
SAY.insert(0, (r"\bMaterialized\.as\b", "materialized dot as"))
SAY.insert(0, (r"\bgroupByKey\b", "group by key"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PAY_Y, PAY_W, PAY_H = 2.45, 1.75, 0.62
PAY_X = [-4.3 + 1.9 * i for i in range(5)]
SLOT5 = -4.3 + 1.9 * 5
PAYS = [("acct-1", "+100"), ("acct-2", "+50"), ("acct-1", "-30"), ("acct-1", "+5"), ("acct-2", "-20")]
OFF_Y, TAG_Y = 1.92, 1.42
BOX_Y, BOX_H = -0.8, 2.95
LX, LW, RX, RW = -3.8, 4.8, 2.6, 7.2
ROW_Y = [-0.2, -0.85]                        # store rows: acct-1, acct-2
CL_X = [-0.08 + 1.12 * i for i in range(6)]  # changelog cells
CL_Y, CL_OFF_Y = -0.55, -1.3
CAP_Y, BAR_Y = -3.22, -2.72


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


def container(x, color, w):
    r = RoundedRectangle(corner_radius=0.16, width=w, height=BOX_H, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.08), 1)
    r.move_to([x, BOX_Y, 0])
    return r


def box_title(x, s, color, size=21, w=LW):
    return fit(T(s, size, color), w - 0.5).move_to([x, BOX_Y + BOX_H / 2 - 0.34, 0])


def pay(i):
    k, v = PAYS[i]
    r = RoundedRectangle(corner_radius=0.1, width=PAY_W, height=PAY_H, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M, 0.2), 1)
    r.move_to([PAY_X[i], PAY_Y, 0])
    return VGroup(r, fit(M(f"{k} {v}", 18), PAY_W - 0.2).move_to(r))


def store_row(k, acct, val, color=GOLD_M):
    r = RoundedRectangle(corner_radius=0.1, width=4.3, height=0.5, stroke_color=color, stroke_width=2.2).set_fill(fillc(color, 0.18), 1)
    r.move_to([LX, ROW_Y[k], 0])
    return VGroup(r, M(f"{acct} = {val}", 20).move_to(r))


def cl_cell(i, acct, val, color=TEAL_M):
    r = RoundedRectangle(corner_radius=0.1, width=1.0, height=0.82, stroke_color=color, stroke_width=2.2).set_fill(fillc(color, 0.18), 1)
    r.move_to([CL_X[i], CL_Y, 0])
    body = VGroup(M(acct, 15), M(val, 15, GREY_A)).arrange(DOWN, buff=0.1).move_to(r)
    return VGroup(r, body, M(str(i), 16, GREY_B).move_to([CL_X[i], CL_OFF_Y, 0]))


def card(y, text, w=4.2):
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.55, stroke_color=GOLD_M, stroke_width=2).set_fill("#2a2418", 1)
    r.move_to([LX, y, 0])
    return VGroup(r, T(text, 20).move_to(r)) if text else VGroup(r)


def bookmark(n):
    t = T(f"saved place: {n}", 18, YELLOW_M)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.35, height=0.42, stroke_color=YELLOW_M, stroke_width=2.2).set_fill(fillc(YELLOW_M, 0.2), 1)
    x = PAY_X[n] if n < 5 else SLOT5
    tip = Triangle(stroke_width=0).set_fill(YELLOW_M, 1).scale(0.08).move_to([x, TAG_Y + 0.29, 0])
    return VGroup(r.move_to([x, TAG_Y, 0]), t.move_to([x, TAG_Y, 0]), tip)


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.3, height=4.1, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.45, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.9, 2.15)
    rows = VGroup()
    cw = M("x" * 40, 14).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 2.9 + ind, 1.6 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["builder.stream(\"payments\")",
        "    .groupByKey()",
        "    .aggregate(() -> 0L,",
        "        (acct, amt, bal) -> bal + amt,",
        "        Materialized.as(\"balances\"));",
        "",
        "// settings: a warm copy on another instance",
        "props.put(\"num.standby.replicas\", 1);"]
KOTLIN = ["builder.stream<String, Long>(\"payments\")",
          "    .groupByKey()",
          "    .aggregate({ 0L },",
          "        { _, amt, bal -> bal + amt },",
          "        Materialized.`as`(\"balances\"))",
          "",
          "// settings: a warm copy on another instance",
          "props[\"num.standby.replicas\"] = 1"]


class KTableState(Base):
    """stream-05, section 1. The café's box of cards (2 million balances in memory, gone on a restart: 1.8 billion records,
    five hours). The notebook in the safe: every new total also written down. Kafka Streams, the state store (RocksDB on
    local disk) and the changelog topic. The stepper's four payments on partition 0: rows overwritten, the changelog only
    appends, commit at 4. The lost disk: replay 100, 50, 70, 75, then payment 4 makes acct-2 30. Compaction and the
    Try it's 1,000 restored records for 10 accounts. The wait (50 GB, 8 minutes) and the standby, the code in Java and
    Kotlin, the moral, and a check (acct-1 + 10)."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("The box of cards and the notebook", "where a Kafka Streams table lives")

        # ---------------- scene 1: the box by the till ----------------
        lbox = container(LX, GOLD_M, LW)
        cards = VGroup(card(-0.1, "Sam owes 8.00"), card(-0.75, ""), card(-1.4, ""))
        self.steps("Picture a café that lets its regulars pay at the end of the month. By the till sits a box of cards, "
                   "one per regular, with the amount owed in pencil.", [
            "By the till",
            (lambda: [FadeIn(lbox), *self.put("lt", box_title(LX, "a box of cards by the till", GOLD_M))], 0.7),
            "one per regular",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in cards], lag_ratio=0.25)], 0.9),
        ])
        sam2 = card(-0.1, "Sam owes 12.50")
        self.steps("Sam buys a coffee, the owner finds Sam's card, and changes one number. It's fast.", [
            "finds Sam's card",
            (lambda: [cards[0].animate.shift(0.15 * UP)], 0.4),
            "changes one number",
            (lambda: [Transform(cards[0], sam2.shift(0.15 * UP))], 0.5),
            (lambda: [cards[0].animate.shift(0.15 * DOWN)], 0.4),
        ])
        mem = T("2 million balances", 28, WHITE).move_to([LX, -0.75, 0])
        kafka_in = T("Kafka: 3,000 payments a second", 22, BLUE_M).move_to([LX, 2.2, 0])
        in_arrow = Arrow([LX, 1.9, 0], [LX, BOX_Y + BOX_H / 2 + 0.05, 0], buff=0.05, stroke_width=3, color=BLUE_M,
                         max_tip_length_to_length_ratio=0.2)
        self.steps("Now make that box a program. Kafka is a program that keeps logs of records for other programs to read, "
                   "and here it hands our program every card payment, 3,000 a second.", [
            "Now make that box",
            (lambda: [FadeOut(cards), *self.put("lt", box_title(LX, "the program's memory", WHITE)), lbox.animate.set_stroke(WHITE)], 0.7),
            "Kafka is a program",
            (lambda: [FadeIn(kafka_in, shift=0.1 * DOWN)], 0.6),
            "3,000 a second",
            (lambda: [GrowArrow(in_arrow)], 0.5),
            (lambda: [dot_run([LX, 1.9, 0], [LX, 0.6, 0], BLUE_M, 0.4)], 0.45),
            (lambda: [dot_run([LX, 1.9, 0], [LX, 0.6, 0], BLUE_M, 0.4)], 0.45),
        ])
        self.steps("The program keeps 2 million balances in memory, and adds each payment as it comes.", [
            "2 million",
            (lambda: [FadeIn(mem)], 0.6),
            "adds each payment",
            (lambda: [LaggedStart(*[dot_run([LX, 1.9, 0], [LX, -0.4, 0], BLUE_M, 0.4) for _ in range(4)], lag_ratio=0.3)], 1.2),
        ])
        empty = T("empty", 28, RED_M).move_to([LX, -0.75, 0])
        self.steps("One night the computer restarts. Memory is wiped, and every balance is gone.", [
            "restarts",
            (lambda: [lbox.animate.set_stroke(RED_M)], 0.4),
            "Memory is wiped",
            (lambda: [FadeOut(mem, scale=0.8), FadeIn(empty)], 0.6),
        ])
        self.steps("To get them back, the program must read every payment again from the start. "
                   "A week of payments is 1.8 billion records, about five hours of reading.", [
            "read every payment",
            (lambda: [LaggedStart(*[dot_run([LX, 1.9, 0], [LX, -0.4, 0], BLUE_M, 0.25) for _ in range(10)], lag_ratio=0.25)], 1.6),
            "A week of payments",
            (lambda: self.cap("read every payment again: 1.8 billion records, about five hours", RED_M), 0.6),
        ])
        self.steps("The tests never caught this. Tests never restart halfway through. "
                   "So where should the table live, so that a restart costs minutes and not hours?", [
            "So where",
            (lambda: self.cap("where should the table live, so a restart costs minutes, not hours?", WHITE), 0.7),
        ], after=0.4)

        # ---------------- scene 2: the notebook in the safe ----------------
        rbox = container(RX, TEAL_M, RW)
        cards = VGroup(card(-0.1, "Sam owes 8.00"), card(-0.75, ""), card(-1.4, ""))
        line1 = left_at(T("Sam owes 8.00", 20, GREY_A), RX - 2.3, -0.15)
        line2 = left_at(T("Sam owes 12.50", 20, WHITE), RX - 2.3, -0.65)
        self.steps("Back to the café. Each time the owner changes a card, she also writes the new total as a line in a notebook: "
                   "Sam owes 12.50. And she keeps the notebook in the office safe.", [
            (lambda: [*self.uncap(), FadeOut(empty), FadeOut(kafka_in), FadeOut(in_arrow), lbox.animate.set_stroke(GOLD_M),
                      *self.put("lt", box_title(LX, "a box of cards by the till", GOLD_M)), FadeIn(cards)], 0.8),
            "writes the new total",
            (lambda: [FadeIn(rbox), *self.put("rt", box_title(RX, "a notebook in the office safe", TEAL_M, w=RW)), FadeIn(line1)], 0.7),
            "Sam owes 12.50",
            (lambda: [Transform(cards[0], card(-0.1, "Sam owes 12.50")), Write(line2)], 0.8),
        ])
        cross = VGroup(Line([LX - 2.0, -2.0, 0], [LX + 2.0, 0.4, 0]), Line([LX - 2.0, 0.4, 0], [LX + 2.0, -2.0, 0])).set_stroke(RED_M, 5)
        fresh = VGroup(card(-0.1, "Sam owes 12.50"), card(-0.75, ""), card(-1.4, ""))
        self.steps("Lose the box, and she rebuilds every card from the notebook. She never touches the till receipts.", [
            "Lose the box",
            (lambda: [Create(cross)], 0.5),
            (lambda: [FadeOut(cards), FadeOut(cross)], 0.5),
            "rebuilds every card",
            (lambda: [dot_run([RX - 2.4, -0.4, 0], [LX + 1.5, -0.4, 0], TEAL_M, 0.6),
                      LaggedStart(*[FadeIn(c) for c in fresh], lag_ratio=0.3)], 1.0),
            "till receipts",
            (lambda: self.cap("never the till receipts", WHITE), 0.5),
        ])
        self.steps("Map it out. The box of cards is the table, kept on the program's own disk, right next to the code. "
                   "The notebook is a second log in Kafka, with one line for every change. "
                   "And the till receipts are the payments themselves.", [
            (lambda: [*self.cap("box of cards = the table, on the program's own disk"), glow(lbox, GOLD_M, 1.02)], 0.7),
            "The notebook is",
            (lambda: [*self.cap("notebook = a log in Kafka, one line per change"), glow(rbox, TEAL_M, 1.02)], 0.7),
            "till receipts are",
            (lambda: self.cap("till receipts = the payments"), 0.5),
        ], after=0.3)

        # ---------------- scene 3: the names ----------------
        self.steps("Kafka Streams, a library you add to your own program, builds exactly this. "
                   "It keeps the box of cards in a state store, RocksDB by default.", [
            (lambda: self.cap("Kafka Streams: a library inside your own program", WHITE), 0.6),
            "a state store",
            (lambda: [FadeOut(fresh), FadeOut(line1), FadeOut(line2),
                      *self.put("lt", box_title(LX, "disk: store balances (RocksDB)", GOLD_M))], 0.8),
            "RocksDB by default",
            (lambda: self.cap("state store: the table, kept by Kafka Streams; RocksDB by default", WHITE), 0.6),
        ])
        self.steps("RocksDB is a small database that keeps a value under each key, in files on the local disk. "
                   "A read or a write takes microseconds.", [
            (lambda: self.cap("RocksDB: a value under each key, in files on the local disk", WHITE), 0.6),
            "microseconds",
            (lambda: self.cap("a read or a write: microseconds, no network trip", WHITE), 0.6),
        ])
        self.steps("Every write to the store also goes to a Kafka topic called the changelog. That's the notebook.", [
            "a Kafka topic",
            (lambda: [*self.put("rt", box_title(RX, "Kafka: the changelog topic", TEAL_M, w=RW))], 0.7),
            "That's the notebook",
            (lambda: [*self.cap("changelog: one record for every write to the store"), glow(rbox, TEAL_M, 1.02)], 0.6),
        ], after=0.3)
        self.stamp("names")

        # ---------------- scene 4: four payments ----------------
        pays = [pay(i) for i in range(5)]
        offs = [M(str(i), 18, GREY_B).move_to([PAY_X[i], OFF_Y, 0]) for i in range(5)]
        head = left_at(T("payments, partition 0", 20, BLUE_M), PAY_X[0] - PAY_W / 2, PAY_Y + 0.62)
        head2 = VMobject()
        self.bm = bookmark(0)
        rows = [None, None]
        cells = []

        def set_row(k, acct, val, color=GOLD_M):
            new = store_row(k, acct, val, color)
            old, rows[k] = rows[k], new
            return [swap(old, new)] if old is not None else [FadeIn(new, shift=0.1 * UP)]

        def add_cell(i, acct, val):
            c = cl_cell(i, acct, val)
            cells.append(c)
            return [FadeIn(c, shift=0.1 * LEFT)]

        def flow(i, k, rt=0.5):
            return [dot_run([PAY_X[i], PAY_Y - PAY_H / 2, 0], [LX, ROW_Y[k] + 0.25, 0], YELLOW_M, rt)]

        def to_log(k, i, rt=0.5):
            return [dot_run([LX + 2.15, ROW_Y[k], 0], [CL_X[i] - 0.5, CL_Y, 0], YELLOW_M, rt)]

        self.steps("Kafka splits the payments into separate logs called partitions. Let's follow just one, partition 0, with five payments.", [
            (lambda: [*self.uncap(), FadeIn(head), FadeIn(head2)], 0.5),
            "partition 0",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * DOWN) for p in pays], lag_ratio=0.2),
                      LaggedStart(*[FadeIn(o) for o in offs], lag_ratio=0.2)], 1.2),
            (lambda: [FadeIn(self.bm, shift=0.1 * UP)], 0.4),
        ])
        self.steps("Offset 0: acct-1 pays in 100.00. There's no row yet, so it starts at 0 and becomes 100.00. "
                   "The new value goes into the store, and the same line goes into the changelog.", [
            (lambda: [glow(pays[0][0], YELLOW_M, 1.06)], 0.6),
            "starts at 0",
            (lambda: [*flow(0, 0)], 0.6),
            (lambda: set_row(0, "acct-1", "0.00"), 0.3),
            "becomes 100.00",
            (lambda: set_row(0, "acct-1", "100.00"), 0.5),
            "the same line",
            (lambda: [*to_log(0, 0)], 0.6),
            (lambda: add_cell(0, "acct-1", "100.00"), 0.4),
        ])
        self.steps("Offset 1: acct-2 pays in 50.00. A new key, so a new row, and a new line.", [
            (lambda: [glow(pays[1][0], YELLOW_M, 1.06), *flow(1, 1)], 0.6),
            "a new row",
            (lambda: set_row(1, "acct-2", "50.00"), 0.5),
            "a new line",
            (lambda: [*to_log(1, 1, 0.4)], 0.45),
            (lambda: add_cell(1, "acct-2", "50.00"), 0.4),
        ])
        self.steps("Offset 2: acct-1 pays 30.00. Its row changes from 100.00 to 70.00, in place. "
                   "But a log never changes a line, so the changelog adds acct-1 = 70.00 at the end.", [
            (lambda: [glow(pays[2][0], YELLOW_M, 1.06), *flow(2, 0)], 0.6),
            "Its row changes",
            (lambda: set_row(0, "acct-1", "70.00"), 0.6),
            "a log never changes",
            (lambda: [glow(cells[0][0], TEAL_M, 1.06)], 0.6),
            "adds acct-1",
            (lambda: [*to_log(0, 2)], 0.55),
            (lambda: [*add_cell(2, "acct-1", "70.00"), cells[0].animate.set_opacity(0.45)], 0.5),
        ])
        self.steps("Offset 3: acct-1 pays in 5.00 and reaches 75.00. "
                   "Then the program commits: it saves its place on payments as 4, the next record to read.", [
            (lambda: [glow(pays[3][0], YELLOW_M, 1.06), *flow(3, 0)], 0.6),
            "reaches 75.00",
            (lambda: [*set_row(0, "acct-1", "75.00"), *to_log(0, 3)], 0.6),
            (lambda: [*add_cell(3, "acct-1", "75.00"), cells[2].animate.set_opacity(0.45)], 0.4),
            "the program commits",
            (lambda: [*self.cap("commit: save the place on payments", WHITE)], 0.5),
            "as 4",
            (lambda: [Transform(self.bm, bookmark(4))], 0.7),
        ])
        self.steps("Notice the two shapes. The store keeps one row per account. The changelog keeps every change, in order.", [
            "The store keeps",
            (lambda: [*self.cap("the store: one row per account, overwritten"), glow(rows[0][0], GOLD_M, 1.04), glow(rows[1][0], GOLD_M, 1.04)], 0.8),
            "The changelog keeps",
            (lambda: [*self.cap("the changelog: every change, in order, only added to"),
                      LaggedStart(*[glow(c[0], TEAL_M, 1.08) for c in cells], lag_ratio=0.15)], 1.0),
        ], after=0.4)
        self.stamp("walk")

        # ---------------- scene 5: the bad night ----------------
        gone = T("empty: the disk is gone", 24, RED_M).move_to([LX, -0.8, 0])
        self.steps("Now, the bad night. The computer dies, and its disk goes with it.", [
            (lambda: [*self.uncap(), lbox.animate.set_stroke(RED_M)], 0.5),
            "its disk goes",
            (lambda: [FadeOut(rows[0]), FadeOut(rows[1]), FadeIn(gone)], 0.7),
        ])
        rows[0] = rows[1] = None
        newc = T("a new computer: empty disk", 24, GREY_B).move_to([LX, -0.8, 0])
        self.steps("The work moves to another computer with an empty disk. Before it handles payment 4, what does it do? Pause and guess.", [
            (lambda: [lbox.animate.set_stroke(GREY_B), *self.put("lt", box_title(LX, "new computer: store balances", GREY_B)),
                      FadeOut(gone), FadeIn(newc)], 0.8),
            "Before it handles",
            (lambda: [glow(pays[4][0], YELLOW_M, 1.06)], 0.6),
            "Pause and guess",
            (lambda: self.cap("what does it do before payment 4?  pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        def replay(i, k, acct, val):
            return [dot_run([CL_X[i] - 0.5, CL_Y, 0], [LX + 2.15, ROW_Y[k], 0], TEAL_M, 0.45)]

        self.steps("It reads the changelog from the beginning into a fresh store, oldest first: 100.00, then 50.00, then 70.00, then 75.00.", [
            (lambda: [*self.uncap(), FadeOut(newc), lbox.animate.set_stroke(GOLD_M),
                      *self.cap("replay the changelog, oldest first", WHITE),
                      *[c.animate.set_opacity(1) for c in cells]], 0.6),
            "100.00",
            (lambda: [glow(cells[0][0], TEAL_M, 1.08), *replay(0, 0, "acct-1", "100.00")], 0.5),
            (lambda: set_row(0, "acct-1", "100.00"), 0.25),
            "50.00",
            (lambda: [glow(cells[1][0], TEAL_M, 1.08), *replay(1, 1, "acct-2", "50.00")], 0.5),
            (lambda: set_row(1, "acct-2", "50.00"), 0.25),
            "70.00",
            (lambda: [glow(cells[2][0], TEAL_M, 1.08), *replay(2, 0, "acct-1", "70.00")], 0.5),
            (lambda: set_row(0, "acct-1", "70.00"), 0.25),
            "75.00",
            (lambda: [glow(cells[3][0], TEAL_M, 1.08), *replay(3, 0, "acct-1", "75.00")], 0.5),
            (lambda: set_row(0, "acct-1", "75.00"), 0.25),
        ])
        self.steps("For each account, the last line wins. So acct-1 is 75.00, and acct-2 is 50.00.", [
            "the last line wins",
            (lambda: [*self.cap("for each account, the last line wins", WHITE)], 0.5),
            "So acct-1",
            (lambda: [glow(rows[0][0], GOLD_M, 1.04)], 0.6),
            "and acct-2",
            (lambda: [glow(rows[1][0], GOLD_M, 1.04)], 0.6),
        ])
        self.steps("Only then does it carry on with the payments, from the saved place, 4. acct-2 pays 20.00 and goes down to 30.00.", [
            "from the saved place",
            (lambda: [glow(self.bm[0], YELLOW_M, 1.1), *self.cap("then carry on from the saved place: 4", WHITE)], 0.7),
            "acct-2 pays",
            (lambda: [glow(pays[4][0], YELLOW_M, 1.06), *flow(4, 1)], 0.6),
            "goes down to",
            (lambda: [*set_row(1, "acct-2", "30.00"), *to_log(1, 4, 0.45)], 0.55),
            (lambda: [*add_cell(4, "acct-2", "30.00")], 0.5),
        ])
        self.steps("Nothing came from the old disk. The payments, the changelog and the saved place all live in Kafka. "
                   "Four lines to read, not five hours.", [
            "The payments",
            (lambda: [LaggedStart(*[glow(p[0], BLUE_M, 1.05) for p in pays], lag_ratio=0.1)], 0.7),
            "the changelog",
            (lambda: [glow(rbox, TEAL_M, 1.02)], 0.5),
            "the saved place",
            (lambda: [glow(self.bm[0], YELLOW_M, 1.1)], 0.5),
            "Four lines",
            (lambda: self.cap("four lines to read, not five hours", YELLOW_M), 0.6),
        ], after=0.4)
        self.stamp("restored")

        # ---------------- scene 6: ten accounts, ten lines? ----------------
        self.steps("You might be thinking: the notebook only needs the latest line per account. Kafka can clean a log down to that. "
                   "It's called compaction, and the changelog has it switched on.", [
            (lambda: self.cap("the notebook only needs the latest line per account?", PURPLE_M), 0.6),
            "It's called compaction",
            (lambda: [*self.cap("compaction: keep only the latest record for each key", WHITE),
                      cells[0].animate.set_opacity(0.35), cells[2].animate.set_opacity(0.35)], 0.8),
        ])
        demo = VGroup(
            RoundedRectangle(corner_radius=0.14, width=7.6, height=1.5, stroke_color=PURPLE_M, stroke_width=2.5).set_fill("#0b0d10", 1),
            T("the lesson's demo: 1,000 payments for 10 accounts,", 22),
            T("then delete the local store and start again", 22),
        ).set_z_index(8)
        demo[1].move_to([0, 0.95, 0])
        demo[2].move_to([0, 0.45, 0])
        demo[0].move_to([0, 0.7, 0])
        self.steps("So the lesson's demo adds up 1,000 payments for 10 accounts, then deletes the local store. "
                   "How many records does the restore read? Pause and guess.", [
            (lambda: [FadeIn(demo, shift=0.1 * UP)], 0.7),
            "How many records",
            (lambda: self.cap("10 records, or more?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        out = M("run 2: restored 1000 records", 22, YELLOW_M).move_to([0, -0.05, 0]).set_z_index(9)
        self.steps("1,000. Every update. Compaction never touches the newest file of a log, the one still being written, "
                   "and this changelog is young.", [
            (lambda: [demo[0].animate.stretch_to_fit_height(2.1).move_to([0, 0.45, 0]), FadeIn(out), *self.uncap()], 0.6),
            "Compaction never",
            (lambda: self.cap("compaction never touches the newest file, the one still being written", WHITE), 0.7),
        ])
        self.steps("Well... so much for ten. The balances came back right, just more slowly.", [
            "came back right",
            (lambda: [FadeOut(demo), FadeOut(out), *[c.animate.set_opacity(1) for c in cells],
                      *self.cap("the balances came back right, just more slowly")], 0.7),
        ], after=0.4)

        # ---------------- scene 7: the wait, and a second café ----------------
        self.steps("So the wait grows with the store. 50 GB, read at 100 MB a second, is more than 8 minutes, "
                   "and that partition's payments wait.", [
            "50 GB",
            (lambda: self.cap("a 50 GB store at 100 MB a second: more than 8 minutes", RED_M), 0.7),
            "payments wait",
            (lambda: [LaggedStart(*[glow(p[0], RED_M, 1.05) for p in pays], lag_ratio=0.1)], 0.9),
        ])
        stand = VGroup(
            DashedVMobject(RoundedRectangle(corner_radius=0.16, width=LW - 0.4, height=0.85, stroke_color=GOLD_M, stroke_width=2.5), num_dashes=60),
            fit(T("standby on another computer: a warm copy", 20, GOLD_M), LW - 0.8),
        )
        stand[0].move_to([LX, -1.72, 0])
        stand[1].move_to(stand[0])
        self.steps("One setting shortens it: num.standby.replicas, set to 1. Another copy of the program keeps a warm store "
                   "by reading the changelog all the time.", [
            "One setting",
            (lambda: self.cap(M("num.standby.replicas = 1", 24, YELLOW_M)), 0.6),
            "Another copy",
            (lambda: [FadeIn(stand, shift=0.1 * UP)], 0.7),
            "reading the changelog",
            (lambda: [LaggedStart(*[dot_run([CL_X[i], CL_Y - 0.5, 0], [LX + 1.9, -1.72, 0], TEAL_M, 0.5)
                                    for i in range(5)], lag_ratio=0.2)], 1.3),
        ])
        self.steps("That's a second café keeping its own box from a copy of the notebook. "
                   "After a failure, only the last few lines need replaying.", [
            (lambda: self.cap("a second café, its box kept up to date from a copy of the notebook"), 0.7),
            "only the last few",
            (lambda: self.cap("after a failure: replay only the last few lines", WHITE), 0.6),
        ])
        self.steps("The café picture breaks at scale: one box for the owner, but here one slice of the table per partition, "
                   "and thousands of lines a second.", [
            (lambda: [FadeOut(stand), *self.cap("where the café breaks", WHITE)], 0.5),
            "one slice of the table",
            (lambda: [*self.cap("one slice of the table per partition"), glow(lbox, GOLD_M, 1.02)], 0.7),
            "thousands of lines",
            (lambda: [*self.cap("thousands of changelog records a second"), glow(rbox, TEAL_M, 1.02)], 0.7),
        ], after=0.3)
        self.stamp("guardrail")

        diagram = VGroup(lbox, rbox, head, head2, self.bm, *pays, *offs, *[r for r in rows if r is not None], *cells,
                         *[self.lab[k] for k in ("lt", "rt")])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(panel, rs, color):
            return [panel[2][r].animate(rate_func=there_and_back).set_color(color) for r in rs]

        self.steps("Here it is in Java and Kotlin. groupByKey and aggregate are the fold: start at 0, add each payment.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
            "groupByKey",
            (lambda: [*hl(jp, (1, 2, 3), GOLD_M), *hl(kp, (1, 2, 3), GOLD_M)], 1.6),
        ])
        self.steps("Materialized.as names the store, and the changelog comes with it. One setting asks for the standby.", [
            (lambda: [*hl(jp, (4,), TEAL_M), *hl(kp, (4,), TEAL_M)], 1.4),
            "One setting",
            (lambda: [*hl(jp, (7,), YELLOW_M), *hl(kp, (7,), YELLOW_M)], 1.4),
        ], after=0.5)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: keep the table next to the code for speed, and write every change to a log that outlives the disk.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            "keep the table",
            (lambda: self.cap("keep the table next to the code; write every change to a log", YELLOW_M, 26), 0.6),
        ])
        self.steps("The box of cards is fast. The notebook is what you trust.", [
            (lambda: [glow(lbox, GOLD_M, 1.02)], 0.6),
            "The notebook",
            (lambda: [glow(rbox, TEAL_M, 1.02)], 0.6),
        ], after=0.4)
        p6 = VGroup(RoundedRectangle(corner_radius=0.1, width=PAY_W, height=PAY_H, stroke_color=BLUE_M, stroke_width=2.5)
                    .set_fill(fillc(BLUE_M, 0.2), 1), M("acct-1 +10", 18))
        p6[0].move_to([SLOT5, PAY_Y, 0])
        p6[1].move_to(p6[0])
        o6 = M("5", 18, GREY_B).move_to([SLOT5, OFF_Y, 0])
        self.steps("One quick check. acct-1 pays in 10.00 more. What changes in the store, and what changes in the changelog? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(p6, shift=0.1 * DOWN), FadeIn(o6)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("The store overwrites one row: acct-1 becomes 85.00. The changelog adds one line at the end: acct-1 = 85.00.", [
            (lambda: [*self.uncap(), dot_run([SLOT5, PAY_Y - PAY_H / 2, 0], [LX, ROW_Y[0] + 0.25, 0], YELLOW_M, 0.6)], 0.65),
            (lambda: set_row(0, "acct-1", "85.00"), 0.5),
            "The changelog adds",
            (lambda: [*to_log(0, 5, 0.5)], 0.55),
            (lambda: [*add_cell(5, "acct-1", "85.00"),
                      *self.cap("store: one row overwritten.   changelog: one line added", WHITE)], 0.6),
        ], after=0.4)
        self.play(*self.cap("a fast copy on the disk, every change in the log", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
