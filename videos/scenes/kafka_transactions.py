from sfz import *

SAY.insert(0, (r"\bpay-(\d+)", r"pay \1"))
SAY.insert(0, (r"\bledger-0\b", "ledger zero"))
SAY.insert(0, (r"\binitTransactions\b", "init transactions"))
SAY.insert(0, (r"\bbeginTransaction\b", "begin transaction"))
SAY.insert(0, (r"\bsendOffsetsToTransaction\b", "send offsets to transaction"))
SAY.insert(0, (r"\bcommitTransaction\b", "commit transaction"))
SAY.insert(0, (r"\bProducerFencedException\b", "producer fenced exception"))
SAY.insert(0, (r"\bread_uncommitted\b", "read uncommitted"))
SAY.insert(0, (r"\bread_committed\b", "read committed"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
SRC_Y, ENT_Y, OFF_Y = 2.55, 0.55, -1.25       # payments, ledger-entries, __consumer_offsets
CW, CH = 0.84, 0.66
PG_C = np.array([1.0, 2.55, 0])               # the ledger program
CO_C = np.array([4.85, 2.55, 0])              # the transaction coordinator
NOTE_Y = 1.85                                 # the sticky note, under the source row
CALL_Y = 1.72                                 # the call being made, under the program
READ_Y = -2.4
CAP_Y, BAR_Y = -3.35, -2.98
NAMES = ["Ana", "Ben", "Cara", "Dev", "Eva", "Finn"]


def sx(k):
    return -5.6 + 0.92 * k


def ex(i):
    return -5.6 + 0.98 * i


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

    # labels that get replaced: one key, one thing on screen
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

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.05):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])




STYLE = {"src": BLUE_M, "plain": TEAL_M, "dup": YELLOW_M, "pencil": GREY_B, "ink": GREEN_M, "abort": RED_M, "name": WHITE}


def cell(text, x, y, style="plain", w=CW):
    c = STYLE[style]
    r = RoundedRectangle(corner_radius=0.08, width=w, height=CH, stroke_color=c, stroke_width=2.5)
    if style == "pencil":
        r.set_fill(BLACK, 1)
        edge = DashedVMobject(r.copy().set_fill(opacity=0), num_dashes=26, dashed_ratio=0.55)
        lab = T(text, 16, GREY_B).move_to([x, y, 0])
        return VGroup(r.move_to([x, y, 0]), lab, edge.move_to([x, y, 0])).set_z_index(3)
    r.set_fill(BLACK if style == "name" else fillc(c, 0.2), 1).move_to([x, y, 0])
    lab = T(text, 16, GREY_B if style == "abort" else WHITE).move_to([x, y, 0])
    return VGroup(r, lab).set_z_index(3)


def marker(kind, x, y):
    c = GREEN_M if kind == "COMMIT" else RED_M
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M, 0.25), 1)
    return VGroup(r.move_to([x, y, 0]), M(kind, 12, c).move_to([x, y, 0])).set_z_index(3)


def box(c, w, h, color):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(BLACK if ManimColor(color).to_hex().upper() == "#FFFFFF" else fillc(color), 1).move_to(c)


def dot_to(a, b, color=YELLOW_M, rt=0.45):
    d = Dot(radius=0.07, color=color).move_to(a).set_z_index(8)
    return Succession(FadeIn(d, run_time=0.03), d.animate(run_time=rt, rate_func=smooth).move_to(b), FadeOut(d, run_time=0.08))


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.3, height=5.0, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.2, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.9, 2.35)
    rows = VGroup()
    cw = M("x" * 40, 14).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 2.9 + ind, 1.85 - 0.31 * k))
    if rows.width > 5.6:
        rows.scale(5.6 / rows.width, about_point=rows.get_corner(UL))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["producer.beginTransaction();",
        "try {",
        "    for (var r : records)",
        "        producer.send(new ProducerRecord<>(",
        "            \"ledger-entries\", r.key(), \"entry:\" + r.value()));",
        "    producer.sendOffsetsToTransaction(nextOffsets(records),",
        "            consumer.groupMetadata());",
        "    producer.commitTransaction();    // together",
        "} catch (ProducerFencedException fenced) {",
        "    throw fenced;                    // a newer copy",
        "} catch (KafkaException e) {",
        "    producer.abortTransaction();     // cancel",
        "    rewind(consumer, records);       // seek back",
        "}"]
KOTLIN = ["producer.beginTransaction()",
          "try {",
          "    for (r in records)",
          "        producer.send(ProducerRecord(",
          "            \"ledger-entries\", r.key(), \"entry:${r.value()}\"))",
          "    producer.sendOffsetsToTransaction(nextOffsets(records),",
          "        consumer.groupMetadata())",
          "    producer.commitTransaction()     // together",
          "} catch (fenced: ProducerFencedException) {",
          "    throw fenced                     // a newer copy",
          "} catch (e: KafkaException) {",
          "    producer.abortTransaction()      // cancel",
          "    rewind(consumer, records)        // seek back",
          "}"]


class KafkaTransactions(Base):
    """msg-10, section 1. The address book copied with a sticky note: four copied, the doorbell, a friend carries on from
    the note, 10 addresses for 6 people. The ledger program does the same (6 payments, 10 entries). The idempotent
    producer doesn't help (a new copy is a new producer). Pencil and one ink stamp: a transaction. The coordinator,
    the transactional id (ledger-0) and five calls, replayed on the crash: instance 1 pencils four entries and dies;
    instance 2's initTransactions aborts them (an ABORT marker, nothing deleted), sends six, sends the bookmark, commits
    (COMMIT markers in ledger-entries and __consumer_offsets). read_committed sees 6, the default sees 10. Rewind after
    an abort, keep transactions short. Java and Kotlin, the moral, and a check (14 aborted entries, default reader)."""

    def construct(self):
        self.lab = {}
        self.ent = []
        self.title_card("Ink the whole batch, or none of it", "a Kafka transaction: the entries and the bookmark as one write")

        # ---------------- scene 1: the address book ----------------
        src = [cell(NAMES[k], sx(k), SRC_Y, "name") for k in range(6)]
        pg = box(PG_C, 2.5, 1.1, WHITE)

        def pg_t(s):
            return self.put("pg_t", T(s, 22).move_to(PG_C + [0, 0.2, 0]))

        def pg_s(s, color=GREY_B):
            return self.put("pg_s", T(s, 16, color).move_to(PG_C + [0, -0.22, 0]))

        def note(s, k=0, color=GOLD_M):
            t = T(s, 16, BLACK)
            r = RoundedRectangle(corner_radius=0.05, width=max(1.2, t.width + 0.3), height=0.42, stroke_width=0).set_fill(color, 1)
            g = VGroup(r, t).move_to([sx(k), NOTE_Y, 0])
            return self.put("note", g)

        def row_lab(key, s, y):
            return self.put(key, left_at(T(s, 20, GREY_B), -6.05, y + 0.62))

        self.steps("Picture copying the addresses from an old address book into a new one. You keep your place with a sticky note.", [
            "from an old",
            (lambda: [*row_lab("src_t", "old address book", SRC_Y), LaggedStart(*[FadeIn(c, shift=0.1 * DOWN) for c in src], lag_ratio=0.12)], 1.2),
            "into a new one",
            (lambda: [*row_lab("ent_t", "new address book", ENT_Y), FadeIn(pg), *pg_t("you")], 0.7),
            "sticky note",
            (lambda: note("sticky note"), 0.6),
        ])

        def write(i, text, style, k_src=None):
            c = cell(text, ex(i), ENT_Y, style)
            if i < len(self.ent):
                self.ent[i] = c
            else:
                self.ent.append(c)
            a = PG_C + [0, -0.55, 0]
            return [Succession(dot_to(a, [ex(i), ENT_Y + 0.4, 0]), FadeIn(c, shift=0.05 * DOWN, run_time=0.2))]

        self.steps("You've copied four when the doorbell rings. While you're away, a friend carries on from the sticky note, "
                   "which still marks the start.", [
            (lambda: [LaggedStart(*[AnimationGroup(*write(i, NAMES[i], "name")) for i in range(4)], lag_ratio=0.5)], 1.8),
            "the doorbell",
            (lambda: [*self.put("bell", T("ding dong", 20, YELLOW_M).move_to(PG_C + [0, 0.85, 0])), glow(pg, YELLOW_M, 1.04)], 0.6),
            "a friend",
            (lambda: [*self.drop("bell"), *pg_t("a friend")], 0.5),
            "still marks",
            (lambda: [Indicate(self.lab["note"], color=GOLD_M, scale_factor=1.2)], 0.8),
        ])
        self.steps("The friend copies from the note to the end. How many addresses are in the new book now? Pause and guess.", [
            (lambda: [LaggedStart(*[AnimationGroup(*write(4 + i, NAMES[i], "name")) for i in range(6)], lag_ratio=0.35)], 2.0),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Ten, for six people. Four of them twice. Nobody did anything wrong. The sticky note stayed behind the work.", [
            (lambda: [*self.cap("10 addresses for 6 people", WHITE)], 0.5),
            "Four of them twice",
            (lambda: [*[self.ent[i][0].animate.set_stroke(YELLOW_M, width=4) for i in list(range(4)) + list(range(4, 8))]], 0.7),
            "The sticky note stayed",
            (lambda: [Indicate(self.lab["note"], color=GOLD_M, scale_factor=1.2)], 0.8),
        ])

        # ---------------- scene 2: the payments program ----------------
        def relabel_src():
            out = []
            for k in range(6):
                new = cell(f"pay-{k}", sx(k), SRC_Y, "src")
                out.append(Transform(src[k], new))
            return out

        def relabel_ent():
            out = []
            names = [f"pay-{i}" for i in range(4)] + [f"pay-{i}" for i in range(6)]
            for i, n in enumerate(names):
                new = cell(n, ex(i), ENT_Y, "dup" if i < 4 or i in (4, 5, 6, 7) else "plain")
                out.append(Transform(self.ent[i], new))
            return out

        self.steps("The café payments program does the same. It reads card payments from Kafka, a program that keeps logs "
                   "of messages for other programs to read.", [
            (lambda: [*self.drop("cap"), *row_lab("src_t", "payments (a log in Kafka)", SRC_Y), *relabel_src()], 1.0),
            "It reads",
            (lambda: [*pg_t("ledger program"), *pg_s("instance 1")], 0.6),
        ])
        self.steps("For each payment, it writes a ledger entry, a line in the book of money movements, to a log called ledger-entries. "
                   "Then it moves its bookmark.", [
            "a log called",
            (lambda: [*row_lab("ent_t", "ledger-entries", ENT_Y), *relabel_ent()], 1.0),
            "its bookmark",
            (lambda: note("bookmark: 0"), 0.6),
        ])
        offs0 = cell("offset 0", -5.25, OFF_Y, "plain", 1.5)
        self.steps("Kafka keeps that bookmark in a log of its own. So these are two separate writes, often on different machines, "
                   "and nothing ties them together. A crash in between, and the lesson's demo ends with 10 entries for 6 payments.", [
            "a log of its own",
            (lambda: [*row_lab("off_t", "__consumer_offsets (where the bookmark is kept)", OFF_Y), FadeIn(offs0)], 0.7),
            "two separate writes",
            (lambda: [dot_to(PG_C + [0, -0.55, 0], [ex(3), ENT_Y + 0.4, 0], WHITE, 0.6), dot_to(PG_C + [-1.3, -0.3, 0], [-4.5, OFF_Y + 0.3, 0], WHITE, 0.8),
                      *self.cap("two writes, nothing tying them together", WHITE)], 0.9),
            "10 entries",
            (lambda: [*self.cap("10 entries for 6 payments: pay-0 to pay-3 twice", YELLOW_M)], 0.6),
        ])

        # ---------------- scene 3: the idempotent producer? ----------------
        self.steps("You might be thinking: Kafka has an idempotent producer, which drops repeats. It drops one kind: "
                   "the same producer sending the same batch twice.", [
            (lambda: self.cap("the idempotent producer drops repeats?", PURPLE_M), 0.5),
            "It drops one kind",
            (lambda: self.cap("it drops one kind: the same producer, the same batch, sent twice", WHITE), 0.5),
        ])
        self.steps("The friend who took over is a new producer with a new id. To Kafka, its four entries are brand new. "
                   "Same face, total stranger.", [
            "a new producer",
            (lambda: [*pg_s("instance 2: a new id", PURPLE_M)], 0.6),
            "brand new",
            (lambda: [LaggedStart(*[glow(self.ent[i][0], YELLOW_M, 1.08) for i in range(4, 8)], lag_ratio=0.2)], 1.0),
        ])
        self.steps("What we want is for the entries and the bookmark to be one write. All of it, or none of it.", [
            (lambda: [*self.cap("the wish: entries and bookmark as one write", WHITE)], 0.6),
            "All of it",
            (lambda: [glow(offs0[0], TEAL_M, 1.05)], 0.6),
        ])

        # ---------------- scene 4: pencil and ink ----------------
        self.steps("Back to the address book. Suppose you copy each address in pencil, and move the sticky note in pencil too.", [
            (lambda: [*[FadeOut(c) for c in self.ent], *self.drop("cap"), *pg_s("instance 1")], 0.6),
            "in pencil",
            (lambda: [LaggedStart(*[AnimationGroup(*write(i, f"pay-{i}", "pencil")) for i in range(3)], lag_ratio=0.4)], 1.2),
            "sticky note in pencil",
            (lambda: [*self.put("note", VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.05, width=1.55, height=0.42, stroke_color=GOLD_M,
                                                                                    stroke_width=2.5), num_dashes=20),
                                               T("bookmark: 3", 16, GOLD_M)).move_to([sx(3), NOTE_Y, 0]))], 0.6),
        ])
        stamp = T("one stamp", 22, GREEN_M).move_to([ex(5) + 0.3, ENT_Y + 0.1, 0])
        self.steps("At the end of the batch you either ink the whole lot with one stamp, or cross the whole lot out. "
                   "A visitor who trusts only ink never sees half a batch.", [
            "ink the whole lot",
            (lambda: [*self.put("stamp", stamp), *[Transform(self.ent[i], cell(f"pay-{i}", ex(i), ENT_Y, "ink")) for i in range(3)]], 0.7),
            "or cross",
            (lambda: [*[Transform(self.ent[i], cell(f"pay-{i}", ex(i), ENT_Y, "abort")) for i in range(3)],
                      *self.put("stamp", T("crossed out", 22, RED_M).move_to(stamp))], 0.7),
            "A visitor",
            (lambda: [*self.cap("a visitor who trusts only ink never sees half a batch", WHITE)], 0.6),
        ])
        self.steps("That's a transaction: a group of writes that count together or not at all. Kafka needs three things to do it.", [
            "a transaction",
            (lambda: [*self.cap("a transaction: writes that count together, or not at all", GREEN_M)], 0.6),
        ])

        # ---------------- scene 5: three things ----------------
        co = box(CO_C, 2.6, 1.1, PURPLE_M)
        self.steps("First, a referee who remembers which logs a transaction touched, and how it ended. Kafka calls it the "
                   "transaction coordinator. One of Kafka's servers takes on the job, and keeps its notes in a log of its own.", [
            (lambda: [*[FadeOut(c) for c in self.ent[:3]], *self.drop("note", "cap", "stamp")], 0.5),
            "a referee",
            (lambda: [FadeIn(co), *self.put("co_t", T("coordinator", 22, PURPLE_M).move_to(CO_C + [0, 0.2, 0]))], 0.7),
            "keeps its notes",
            (lambda: [*self.put("co_s", M("__transaction_state", 13, GREY_B).move_to(CO_C + [0, -0.22, 0]))], 0.6),
        ])
        self.ent = []
        self.steps("Second, a name for each copy of the program, such as ledger-0. It's called the transactional id, and it stays "
                   "the same across restarts, so Kafka knows the next copy is the same program.", [
            "such as ledger-0",
            (lambda: [*pg_s("id: ledger-0", GOLD_M)], 0.6),
            "stays the same",
            (lambda: [glow(pg, GOLD_M, 1.04)], 0.7),
        ])

        def call(s, color=YELLOW_M):
            return self.put("call", M(s, 17, color).move_to([PG_C[0], CALL_Y, 0]))

        def link():
            return [dot_to(PG_C + [1.3, 0, 0], CO_C + [-1.3, 0, 0], PURPLE_M, 0.5)]

        self.steps("Third, five calls, in order. Let's replay the crash with them. initTransactions, once at start-up: "
                   "the copy registers its name with the coordinator.", [
            (lambda: [*note("bookmark: 0")], 0.5),
            "initTransactions",
            (lambda: [*call("1. initTransactions()"), *link()], 0.7),
        ])
        self.steps("beginTransaction: from now on, everything it sends belongs to the transaction.", [
            (lambda: call("2. beginTransaction()"), 0.6),
        ])
        self.steps("Then send. Here's the surprise. The entries go into the log straight away, before anything is decided. "
                   "They're in pencil, but they're in.", [
            (lambda: call("3. send(...)"), 0.5),
            "go into the log",
            (lambda: [LaggedStart(*[AnimationGroup(*write(i, f"pay-{i}", "pencil")) for i in range(4)], lag_ratio=0.45)], 1.8),
            "but they're in",
            (lambda: [*self.cap("records reach the log before the decision", WHITE)], 0.5),
        ])
        crash = tick(False, 0.3).move_to(PG_C)
        self.steps("And now the crash. Instance 1 dies with four entries in pencil.", [
            "the crash",
            (lambda: [Create(crash), pg.animate.set_stroke(RED_M), *self.drop("call")], 0.6),
        ], after=0.5)

        # ---------------- scene 6: instance 2 ----------------
        ab = marker("ABORT", ex(4), ENT_Y)
        self.steps("Instance 2 starts with the same name. Its initTransactions reaches the coordinator, which finishes what the "
                   "older copy left open. It aborts it.", [
            (lambda: [FadeOut(crash), pg.animate.set_stroke(WHITE), *pg_s("instance 2, id: ledger-0", GOLD_M), *self.drop("cap")], 0.6),
            "initTransactions",
            (lambda: [*call("1. initTransactions()"), *link()], 0.7),
            "It aborts it",
            (lambda: [*self.put("co_d", T("ledger-0's open one: abort", 17, RED_M).move_to([CO_C[0], CALL_Y, 0]))], 0.6),
        ])
        self.steps("An abort deletes nothing. It adds a marker after the four, a small record that tells careful readers: skip what came before.", [
            "It adds a marker",
            (lambda: [dot_to(CO_C + [0, -0.55, 0], [ex(4), ENT_Y + 0.4, 0], GOLD_M, 0.6), FadeIn(ab, run_time=0.01)], 0.7),
            (lambda: [*[Transform(self.ent[i], cell(f"pay-{i}", ex(i), ENT_Y, "abort")) for i in range(4)]], 0.7),
            "skip what came before",
            (lambda: [*self.cap("ABORT marker: skip this transaction's records", RED_M)], 0.5),
        ])
        self.ent.append(ab)
        self.steps("Instance 2 begins, reads from the bookmark at 0, and sends six entries, in pencil.", [
            (lambda: [*call("2. beginTransaction()"), *self.drop("co_d", "cap")], 0.5),
            "sends six",
            (lambda: [*call("3. send(...)"), LaggedStart(*[AnimationGroup(*write(5 + i, f"pay-{i}", "pencil")) for i in range(6)], lag_ratio=0.35)], 2.0),
        ])
        offs6 = cell("offset 6", -3.6, OFF_Y, "pencil", 1.5)
        self.steps("sendOffsetsToTransaction: the bookmark joins the transaction. It's in pencil too, and the program has "
                   "turned off saving it on its own.", [
            (lambda: call("4. sendOffsetsToTransaction(...)"), 0.5),
            "the bookmark joins",
            (lambda: [dot_to(PG_C + [-1.3, -0.3, 0], [-3.6, OFF_Y + 0.35, 0], YELLOW_M, 0.7), FadeIn(offs6, run_time=0.01)], 0.8),
            "turned off",
            (lambda: [*self.cap("enable.auto.commit=false", GREY_B)], 0.5),
        ])
        cm1 = marker("COMMIT", ex(11), ENT_Y)
        cm2 = marker("COMMIT", -2.3, OFF_Y)
        self.steps("commitTransaction. The coordinator writes its decision in its notes. Then it puts a COMMIT marker into every log "
                   "the transaction touched: the entries, and the bookmark's log too.", [
            (lambda: [*call("5. commitTransaction()", GREEN_M), *link(), *self.drop("cap")], 0.7),
            "writes its decision",
            (lambda: [*self.put("co_d", T("ledger-0: commit", 17, GREEN_M).move_to([CO_C[0], CALL_Y, 0])), glow(co, GREEN_M, 1.04)], 0.6),
            "a COMMIT marker",
            (lambda: [dot_to(CO_C + [0, -0.55, 0], [ex(11), ENT_Y + 0.4, 0], GOLD_M, 0.5), FadeIn(cm1, run_time=0.01)], 0.6),
            "the bookmark's log",
            (lambda: [dot_to(CO_C + [-0.5, -0.55, 0], [-2.3, OFF_Y + 0.35, 0], GOLD_M, 0.7), FadeIn(cm2, run_time=0.01)], 0.8),
        ])
        self.steps("One stamp, and the whole batch is in ink. The most powerful rubber stamp in the building. "
                   "So the point is: one decision makes six entries and a bookmark count together.", [
            (lambda: [*[Transform(self.ent[5 + i], cell(f"pay-{i}", ex(5 + i), ENT_Y, "ink")) for i in range(6)],
                      Transform(offs6, cell("offset 6", -3.6, OFF_Y, "ink", 1.5)), *note("bookmark: 6", 0)], 0.9),
            "So the point",
            (lambda: [*self.cap("one decision: six entries and the bookmark, together", GREEN_M)], 0.6),
        ])
        self.ent.append(cm1)

        # ---------------- scene 7: what readers see ----------------
        self.steps("So ledger-entries holds ten entries. How many does a reader see? Pause and guess.", [
            (lambda: [*self.drop("call", "co_d"), *self.cap("ten entries in the log", WHITE)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        rc = chip("read_committed: sees 6", GREEN_M, 20, mono=True).move_to([-3.4, READ_Y, 0])
        ru = chip("the default, read_uncommitted: sees 10", RED_M, 20, mono=True).move_to([3.0, READ_Y, 0])
        self.steps("It depends on the reader. A careful reader, set to read_committed, skips the aborted four and sees six, "
                   "each payment once. A reader left on the default, read_uncommitted, sees all ten.", [
            (lambda: self.drop("cap"), 0.3),
            "A careful reader",
            (lambda: [FadeIn(rc, shift=0.1 * UP), *[self.ent[i].animate.set_opacity(0.25) for i in range(5)]], 0.8),
            "the default",
            (lambda: [FadeIn(ru, shift=0.1 * UP), *[self.ent[i].animate.set_opacity(1) for i in range(5)]], 0.8),
        ])
        self.steps("So every program that reads ledger-entries must ask for read_committed, or the transaction protects nothing.", [
            "must ask",
            (lambda: [glow(rc[0], GREEN_M, 1.05), *self.cap("every reader: isolation.level=read_committed", GREEN_M)], 0.8),
        ])

        # ---------------- scene 8: two habits ----------------
        self.steps("Two more habits. After an abort, seek back to the first record of the batch. Reading the batch already moved "
                   "the program's position past it. Without the seek, the next read skips the batch, and it's never written at all.", [
            (lambda: [*self.cap("1. after an abort: seek back to the batch's first record", WHITE)], 0.5),
            "Reading the batch",
            (lambda: [Indicate(self.lab["note"], color=GOLD_M, scale_factor=1.15)], 0.8),
            "never written",
            (lambda: [glow(src[0][0], RED_M, 1.06)], 0.7),
        ])
        self.steps("And keep transactions short, one batch each. Every transaction costs a few extra round trips to the coordinator, "
                   "so one per record is slow. And while one is open, the careful readers wait.", [
            (lambda: [*self.cap("2. one batch per transaction: not one per record, not one per hour", WHITE)], 0.5),
            "round trips",
            (lambda: [*link(), *link()], 0.6),
            "the careful readers wait",
            (lambda: [glow(rc[0], GOLD_M, 1.05)], 0.8),
        ])

        # ---------------- scene 9: the code ----------------
        diagram = VGroup(*[m for m in self.mobjects if isinstance(m, VMobject)])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("Here's one batch, in Java and in Kotlin.", [
            (lambda: [diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
        ])
        self.steps("Begin, send the entries, send the bookmark, commit.", [
            (lambda: hl((0,), YELLOW_M), 0.6),
            "send the entries",
            (lambda: hl((3, 4), YELLOW_M), 0.7),
            "send the bookmark",
            (lambda: hl((5, 6), GOLD_M), 0.7),
            "commit",
            (lambda: hl((7,), GREEN_M), 0.6),
        ])
        self.steps("If anything fails, abort, and seek back. But catch ProducerFencedException first: it means a newer copy "
                   "has taken over the name, so this one must stop.", [
            (lambda: hl((11, 12), RED_M), 1.2),
            "But catch",
            (lambda: hl((8, 9), PURPLE_M), 1.2),
        ], after=0.6)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, how do you stop four entries landing twice? Make the entries and the bookmark one write. Everything goes "
                   "in pencil, then one stamp inks it all, or one marker crosses it all out. And every reader trusts only ink.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: self.cap("how do you stop four entries landing twice?", WHITE), 0.4),
            "one write",
            (lambda: [glow(offs6[0], GREEN_M, 1.05), *[glow(self.ent[5 + i][0], GREEN_M, 1.05) for i in range(6)]], 0.8),
            "one stamp",
            (lambda: [glow(cm1[0], GOLD_M, 1.08), glow(cm2[0], GOLD_M, 1.08)], 0.7),
            "one marker",
            (lambda: [glow(ab[0], GOLD_M, 1.08)], 0.6),
            "trusts only ink",
            (lambda: [glow(rc[0], GREEN_M, 1.05), *self.cap("pencil, then one stamp; readers trust only ink", GREEN_M, 28)], 0.8),
        ])
        self.steps("One quick check. A program writes 14 entries in a transaction, then aborts. Another program reads the topic with "
                   "Kafka's default settings. What does it see? Pause and think.", [
            (lambda: [*self.cap("14 entries, then ABORT. the default reader sees...?", WHITE)], 0.6),
            "default settings",
            (lambda: [glow(ru[0], RED_M, 1.05)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("All 14. The abort only added a marker, and the default reader doesn't look at markers. Set read_committed.", [
            (lambda: [*self.cap("all 14: an abort deletes nothing", RED_M)], 0.6),
            "only added a marker",
            (lambda: [glow(ab[0], GOLD_M, 1.08)], 0.7),
            "Set read_committed",
            (lambda: [*self.cap("readers that trust only ink: read_committed", GREEN_M, 30), glow(rc[0], GREEN_M, 1.05)], 0.7),
        ], after=0.4)
        self.wait(2.0)
