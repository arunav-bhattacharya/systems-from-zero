from sfz import *

SAY.insert(0, (r"\bXREADGROUP\b", "X read group"))
SAY.insert(0, (r"\bXGROUP\b", "X group"))
SAY.insert(0, (r"\bXPENDING\b", "X pending"))
SAY.insert(0, (r"\bXADD\b", "X add"))
SAY.insert(0, (r"\bXACK\b", "X ack"))
SAY.insert(0, (r"\bPEL\b", "P E L"))
SAY.insert(0, (r"\bw([1-3])\b", r"W \1"))
SAY.insert(0, (r"\b1-([1-5])\b", r"one dash \1"))
SAY.insert(0, (r"\bp-([1-5])\b", r"P \1"))
SAY.insert(0, (r"\bpub/sub\b", "pub sub"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ST_Y, CW, CH = 2.4, 1.3, 0.95             # the stream: the order board
GR_C = np.array([4.75, 2.4, 0])           # the group: settlers
WK = {1: np.array([-4.85, 0.35, 0]), 2: np.array([-4.85, -1.15, 0]), 3: np.array([-4.85, -1.15, 0])}
HOLD_X = [-2.75, -1.6]                    # entries a worker holds, beside it
PEL_X0, PEL_TOP = 0.9, 1.2                # the pending entries list
PEL_COL = [1.6, 3.35, 5.25]               # id, owner, deliveries
PEL_ROW = [0.35, -0.15, -0.65, -1.15]
CMD_Y = -2.35
CAP_Y, BAR_Y = -3.35, -2.95
PAY = [("1-1", "p-1", "1250"), ("1-2", "p-2", "4000"), ("1-3", "p-3", "990"), ("1-4", "p-4", "310"), ("1-5", "p-5", "...")]


def sx(k):
    return -5.0 + 1.55 * k


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




def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.3, height=5.0, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.15, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.9, 2.25)
    rows = VGroup()
    cw = M("x" * 40, 14).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 2.9 + ind, 1.75 - 0.31 * k))
    if rows.width > 5.6:
        rows.scale(5.6 / rows.width, about_point=rows.get_corner(UL))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["var params = xReadGroupParams().count(10).block(2_000);",
        "var fresh = Map.of(\"payments\", XREADGROUP_UNDELIVERED_ENTRY);",
        "while (running) {",
        "    var batch = redis.xreadGroup(\"settlers\", me, params, fresh);",
        "    if (batch == null || batch.isEmpty()) continue;",
        "    for (StreamEntry e : batch.get(0).getValue()) {",
        "        try {",
        "            settle(e.getFields());    // keyed by payment id",
        "            redis.xack(\"payments\", \"settlers\", e.getID());",
        "        } catch (Exception ex) {",
        "            log.warn(\"left pending: \" + e.getID(), ex);",
        "        }",
        "    }",
        "}"]
KOTLIN = ["val params = xReadGroupParams().count(10).block(2_000)",
          "val fresh = mapOf(\"payments\" to XREADGROUP_UNDELIVERED_ENTRY)",
          "while (running) {",
          "    val batch = redis.xreadGroup(\"settlers\", me, params, fresh)",
          "        ?.firstOrNull()?.value ?: continue",
          "    for (e in batch) {",
          "        runCatching { settle(e.fields) }   // keyed by payment id",
          "            .onSuccess { redis.xack(\"payments\", \"settlers\", e.id) }",
          "            .onFailure { log.warn(\"left pending: ${e.id}\", it) }",
          "    }",
          "}"]


def dot_to(a, b, color=GOLD_M, rt=0.5):
    d = Dot(radius=0.07, color=color).move_to(a).set_z_index(8)
    return Succession(FadeIn(d, run_time=0.03), d.animate(run_time=rt, rate_func=smooth).move_to(b), FadeOut(d, run_time=0.08))


def entry(k):
    i, p, a = PAY[k]
    r = RoundedRectangle(corner_radius=0.1, width=CW, height=CH, stroke_color=BLUE_M, stroke_width=2.5).set_fill(fillc(BLUE_M, 0.2), 1)
    r.move_to([sx(k), ST_Y, 0])
    return VGroup(r, M(i, 20).move_to([sx(k), ST_Y + 0.2, 0]), T(f"{p}  {a}", 15, GREY_B).move_to([sx(k), ST_Y - 0.22, 0])).set_z_index(3)


def hold(k, slot, w):
    c = WK[w]
    t = M(PAY[k][0], 17, GOLD_M)
    r = RoundedRectangle(corner_radius=0.08, width=0.95, height=0.5, stroke_color=GOLD_M, stroke_width=2).set_fill(fillc(GOLD_M, 0.2), 1)
    return VGroup(r, t).move_to([HOLD_X[slot], c[1], 0]).set_z_index(4)


class RedisStreams(Base):
    """msg-12, section 2. The café's order board (a Redis stream) with each barista's initials next to the orders they took
    (the pending entries list). The lesson's Try-it: a group settlers, four payments 1-1 to 1-4; w1 and w2 read two each
    with '>'; w2's third read gets nothing; XPENDING shows 4 pending, 2 each; w2's XACK leaves 1-1 and 1-2 under w1, count
    1. w1 crashes; '>' will never hand them out again; restarted, it reads its own with 0 and their count becomes 2. That
    is at-least-once, so the handler is idempotent. A Redis group vs a Kafka group. Java and Kotlin, the moral, and a check
    (w2 dies holding 1-5; does w3 get it with '>'?)."""

    def construct(self):
        self.lab = {}
        self.title_card("Initials on the order board", "a Redis consumer group, and the list of who took what")

        # ---------------- scene 1: called out, then written down ----------------
        call = T("\"Flat white for Sam!\"", 40, YELLOW_M).move_to([0, 1.2, 0])
        self.steps("A busy café calls out each drink when it's ready: flat white for Sam! At that moment Sam is washing his hands. "
                   "Nobody calls it twice. His coffee goes cold.", [
            (lambda: [FadeIn(call, scale=0.8)], 0.7),
            "Nobody calls it twice",
            (lambda: [call.animate.set_opacity(0.15)], 0.8),
        ])
        self.steps("Redis, a program that keeps its data in memory, has a tool that works like that, pub/sub. And one that writes "
                   "every message down, like an order board. It's called a stream.", [
            "pub/sub",
            (lambda: [*self.cap("pub/sub: called out once, then forgotten", GREY_B)], 0.5),
            "like an order board",
            (lambda: [FadeOut(call), *self.put("st_t", left_at(T("payments: a stream, the order board", 20, GREY_B), sx(0) - 0.65, 3.3)),
                      *self.cap("a stream: every message written down, in order", WHITE)], 0.7),
        ])
        ents = [entry(k) for k in range(5)]

        def cmd(s, color=GREY_B):
            return self.put("cmd", left_at(M("> " + s, 17, color), -6.3, CMD_Y))

        self.steps("Here's the board for paying shops. Four payments arrive, and Redis gives each an ID: 1-1, 1-2, 1-3, 1-4.", [
            (lambda: [*self.drop("cap"), *cmd("XADD payments 1-1 payment p-1 amount 1250 ...")], 0.5),
            "Four payments",
            (lambda: [LaggedStart(*[FadeIn(e, shift=0.1 * DOWN) for e in ents[:4]], lag_ratio=0.3)], 1.4),
        ])
        self.steps("Each night, workers settle each payment: they add it to what the company owes that shop. Two workers, w1 and w2, "
                   "share the board. Each payment must go to exactly one of them.", [
            "Two workers",
            (lambda: [a for w in (1, 2) for a in self.worker(w)], 0.8),
            "exactly one",
            (lambda: [*self.cap("each payment to exactly one worker", WHITE)], 0.5),
        ])
        self.steps("And if a worker dies holding a payment, how would anybody know? Hold that question.", [
            (lambda: [glow(self.wk[1][0], RED_M, 1.05)], 0.8),
        ], after=0.4)

        # ---------------- scene 2: the group ----------------
        gr = RoundedRectangle(corner_radius=0.14, width=3.2, height=1.05, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1).move_to(GR_C)

        def last(s):
            return self.put("last", T(f"last handed out: {s}", 16, GREY_B).move_to(GR_C + [0, -0.22, 0]))

        self.steps("In the café, the baristas share one board, and each writes their initials next to an order they take. "
                   "In Redis, that's a consumer group. Ours is called settlers.", [
            (lambda: self.drop("cap"), 0.3),
            "a consumer group",
            (lambda: [*cmd("XGROUP CREATE payments settlers $ MKSTREAM"), FadeIn(gr),
                      *self.put("gr_t", T("group: settlers", 20, TEAL_M).move_to(GR_C + [0, 0.2, 0])), *last("0-0")], 0.8),
        ])
        self.held = {1: [], 2: [], 3: []}

        def give(w, ks):
            out = [*last(PAY[ks[-1]][0])]
            for slot, k in enumerate(ks):
                h = hold(k, slot, w)
                self.held[w].append(h)
                out += [dot_to([sx(k), ST_Y - 0.5, 0], [HOLD_X[slot], WK[w][1] + 0.3, 0]), FadeIn(h)]
            return out

        self.steps("w1 asks for two entries with a greater-than sign, which means: never handed to anyone in this group. It gets 1-1 and 1-2.", [
            (lambda: cmd("XREADGROUP GROUP settlers w1 COUNT 2 STREAMS payments >"), 0.5),
            "It gets",
            (lambda: give(1, [0, 1]), 0.8),
        ])
        self.steps("w2 asks the same way, and gets 1-3 and 1-4. Each entry went to one worker only.", [
            (lambda: cmd("XREADGROUP GROUP settlers w2 COUNT 2 STREAMS payments >"), 0.5),
            "and gets",
            (lambda: give(2, [2, 3]), 0.8),
        ])

        # ---------------- scene 3: the list of initials ----------------
        pel = RoundedRectangle(corner_radius=0.14, width=5.4, height=2.75, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.06), 1)
        pel.move_to([PEL_X0 + 2.7, -0.25, 0])
        heads = VGroup(*[T(s, 17, GREY_B).move_to([x, 0.8, 0]) for s, x in zip(("ID", "owner", "deliveries"), PEL_COL)])
        self.rows = {}

        def row(k, owner, n, color=WHITE):
            i = PAY[k][0]
            j = [0, 1, 2, 3][k % 4] if k < 4 else 0
            g = VGroup(M(i, 18, color).move_to([PEL_COL[0], PEL_ROW[j], 0]), M(owner, 18, color).move_to([PEL_COL[1], PEL_ROW[j], 0]),
                       M(str(n), 18, color).move_to([PEL_COL[2], PEL_ROW[j], 0]))
            return self.put(f"row{k}", g)

        self.steps("Redis also writes down every delivery: the entry's ID, who has it, when it went out, and how many times it has "
                   "been delivered. That's the pending entries list, the PEL. Our initials on the board.", [
            "writes down every delivery",
            (lambda: [FadeIn(pel), FadeIn(heads),
                      *self.put("pel_t", T("pending entries list (PEL)", 19, GOLD_M).move_to([PEL_X0 + 2.7, PEL_TOP + 0.33, 0]))], 0.7),
            (lambda: [*row(0, "w1", 1), *row(1, "w1", 1)], 0.5),
            (lambda: [*row(2, "w2", 1), *row(3, "w2", 1)], 0.5),
            "Our initials",
            (lambda: [*cmd("XPENDING payments settlers   ->  4 pending: w1 2, w2 2"), glow(pel, GOLD_M, 1.02)], 0.7),
        ])

        # ---------------- scene 4: predict ----------------
        self.steps("Now w2 asks again, with the greater-than sign. What does it get? Pause and guess.", [
            (lambda: cmd("XREADGROUP GROUP settlers w2 COUNT 2 STREAMS payments >"), 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Nothing. Every entry has been handed out once, and the greater-than sign never hands one out twice.", [
            (lambda: [*cmd("XREADGROUP ... w2 ... >   ->  (nil)", YELLOW_M), *self.cap("(nil): nothing new is left", WHITE)], 0.6),
            "never hands one out twice",
            (lambda: [glow(gr, TEAL_M, 1.04)], 0.7),
        ])
        self.steps("w2 settles its two and says so with XACK. Redis crosses them off the list.", [
            (lambda: [*cmd("XACK payments settlers 1-3 1-4   ->  2"), *self.drop("cap")], 0.5),
            "crosses them off",
            (lambda: [*self.drop("row2", "row3"), *[FadeOut(h) for h in self.held[2]],
                      *[ents[k][0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M, 0.2), 1) for k in (2, 3)]], 0.8),
        ])
        self.held[2] = []

        # ---------------- scene 5: the crash ----------------
        x = tick(False, 0.3).move_to(WK[1])
        self.steps("Now w1 crashes, before its XACK. Are 1-1 and 1-2 lost? Or does Redis quietly give them to w2? Neither.", [
            (lambda: [Create(x), self.wk[1][0].animate.set_stroke(RED_M)], 0.6),
            "Are 1-1",
            (lambda: [*self.cap("lost?   or quietly given to w2?", PURPLE_M)], 0.5),
            "Neither",
            (lambda: [*self.cap("neither", WHITE)], 0.4),
        ])
        self.steps("They stay on the list, under w1's name. Nothing is lost. It's only stuck. And the greater-than sign will never hand "
                   "them out again, because they were already delivered.", [
            "under w1's name",
            (lambda: [*self.cap("pending under w1: stuck, not lost", GOLD_M), Indicate(self.lab["row0"], color=GOLD_M), Indicate(self.lab["row1"], color=GOLD_M)], 0.9),
            "never hand",
            (lambda: [glow(ents[0][0], GOLD_M, 1.05), glow(ents[1][0], GOLD_M, 1.05)], 0.8),
        ])
        self.steps("In the café, a barista went on a break with two orders still marked with their initials. Every other barista "
                   "politely walks past them. That's manners, not a plan.", [
            "politely walks past",
            (lambda: [glow(self.wk[2][0], TEAL_M, 1.05)], 0.8),
        ])

        # ---------------- scene 6: the restart ----------------
        self.steps("When w1 comes back, it reads its own pending entries first. It asks with the ID 0 instead of the greater-than sign, "
                   "and gets back the same two.", [
            (lambda: [FadeOut(x), self.wk[1][0].animate.set_stroke(TEAL_M), *self.put("wk1s", T("restarted", 16, GREEN_M).move_to(WK[1] + [0, -0.22, 0])),
                      *self.drop("cap")], 0.6),
            "with the ID 0",
            (lambda: cmd("XREADGROUP GROUP settlers w1 STREAMS payments 0"), 0.5),
            "the same two",
            (lambda: [glow(self.held[1][0][0], GOLD_M, 1.1), glow(self.held[1][1][0], GOLD_M, 1.1)], 0.7),
        ])
        self.steps("Each one's delivery count goes to 2. When that read comes back empty, w1 switches back to the greater-than sign.", [
            "goes to 2",
            (lambda: [*row(0, "w1", 2, GOLD_M), *row(1, "w1", 2, GOLD_M)], 0.6),
            "switches back",
            (lambda: [*self.cap("own pending first (ID 0), then new ones (>)", WHITE)], 0.5),
        ])

        # ---------------- scene 7: at-least-once ----------------
        self.steps("Notice what this means. Say w1 settled 1-1, then crashed before its XACK. After the restart it settles 1-1 again.", [
            (lambda: [*self.drop("cap"), glow(ents[0][0], RED_M, 1.06)], 0.6),
            "settles 1-1 again",
            (lambda: [*self.cap("settled twice: once before the crash, once after", RED_M)], 0.5),
        ])
        self.steps("This is called at-least-once delivery: every entry is settled at least once, and now and then twice. So the "
                   "settling must be safe to run twice. Key it by the payment's id, and the second time finds the payment done.", [
            "at-least-once",
            (lambda: [*self.cap("at-least-once: every entry at least once, sometimes twice", WHITE)], 0.5),
            "Key it by",
            (lambda: [*self.cap("idempotent: keyed by the payment id, the repeat changes nothing", GREEN_M)], 0.6),
        ])
        self.steps("w1 settles both and sends its XACK. The list is empty.", [
            (lambda: [*cmd("XACK payments settlers 1-1 1-2   ->  2"), *self.drop("row0", "row1", "cap"), *[FadeOut(h) for h in self.held[1]],
                      *[ents[k][0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M, 0.2), 1) for k in (0, 1)]], 0.8),
        ])
        self.held[1] = []

        # ---------------- scene 8: two kinds of group ----------------
        self.steps("Careful: Kafka has consumer groups too, and they share little more than the name. A Kafka group gives each "
                   "partition to one reader, with one bookmark. Order holds, and one stuck record holds up everything behind it.", [
            (lambda: [*self.cap("Kafka's group: one owner per partition, one bookmark, in order", BLUE_M)], 0.6),
            "one stuck record",
            (lambda: [*self.cap("a stuck record holds up everything behind it", RED_M)], 0.5),
        ])
        self.steps("A Redis group keeps a state for every entry, and hands entries to whoever asks. A slow one holds up nobody. "
                   "The price: entries finish in any order.", [
            (lambda: [*self.cap("Redis's group: a state per entry, any worker, any order", TEAL_M), glow(pel, GOLD_M, 1.02)], 0.7),
        ])
        self.steps("And the question we're holding: if w1 never comes back, someone must take its entries over. "
                   "That's called claiming, and it's the next part of the lesson.", [
            (lambda: [*self.cap("never comes back? another worker claims them: next", WHITE)], 0.6),
        ])

        # ---------------- scene 9: the code ----------------
        diagram = VGroup(*[m for m in self.mobjects if isinstance(m, VMobject)])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(rj, rk, color):
            return [jp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rj] + \
                   [kp[2][r].animate(rate_func=there_and_back).set_color(color) for r in rk]

        self.steps("Here's a worker's loop, in Java and in Kotlin, with Jedis, a library for talking to Redis.", [
            (lambda: [diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
        ])
        self.steps("Read new entries through the group, waiting up to two seconds. Settle each one, keyed by the payment, then XACK it. "
                   "If settling fails, leave it pending on purpose.", [
            (lambda: hl((0, 1, 3), (0, 1, 3), YELLOW_M), 1.3),
            "Settle each one",
            (lambda: hl((7, 8), (6, 7), GREEN_M), 1.2),
            "If settling fails",
            (lambda: hl((10,), (8,), GOLD_M), 1.0),
        ], after=0.6)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, how does each payment reach exactly one worker, and how do we know when a worker dies holding one? "
                   "The group hands each entry out once, and writes the worker's initials next to it until the worker says done.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: self.cap("one worker per entry, and a list of who holds what", WHITE), 0.4),
            "writes the worker's initials",
            (lambda: [glow(pel, GOLD_M, 1.02)], 0.8),
        ])
        self.steps("One quick check. w2 reads a new entry, 1-5, and crashes before its XACK. Then w3 joins and asks with the "
                   "greater-than sign. Does w3 get 1-5? Pause and think.", [
            (lambda: [*self.drop("cap"), FadeIn(ents[4], shift=0.1 * DOWN)], 0.5),
            "w2 reads",
            (lambda: [*give(2, [4]), *row(4, "w2", 1)], 0.8),
            "and crashes",
            (lambda: [self.wk[2][0].animate.set_stroke(RED_M)], 0.4),
            "Then w3 joins",
            (lambda: [*self.worker(3)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. 1-5 was already delivered, so it stays pending under w2, until w2 comes back for it, or someone claims it.", [
            (lambda: [*self.cap("no: 1-5 stays pending under w2", GOLD_M), Indicate(self.lab["row4"], color=GOLD_M)], 0.8),
            "or someone claims it",
            (lambda: [*self.cap("initials stay until the worker says done, or someone claims it", WHITE)], 0.6),
        ], after=0.4)
        self.wait(2.0)

    def worker(self, w):
        if not hasattr(self, "wk"):
            self.wk = {}
        b = RoundedRectangle(corner_radius=0.14, width=2.3, height=1.05, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M), 1)
        c = WK[w] if w != 3 else np.array([-4.85, 1.75 - 3.0, 0])
        if w == 3:
            # w3 takes w1's place on screen (w1 has finished and left)
            old = self.wk.pop(1, None)
            c = WK[1]
            g = VGroup(b.move_to(c), T("w3", 22).move_to(c + [0, 0.2, 0]))
            self.wk[3] = g
            out = [FadeOut(old)] if old is not None else []
            return out + self.drop("wk1s") + [FadeIn(g)]
        g = VGroup(b.move_to(c), T(f"w{w}", 22).move_to(c + [0, 0.2, 0]))
        self.wk[w] = g
        return [FadeIn(g, shift=0.1 * RIGHT)]
