from sfz import *

SAY.insert(0, (r"\bpay-0(\d)\b", r"pay \1"))
SAY.insert(0, (r"\bacct-1\b", "account one"))
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\b11:02\b", "eleven oh two"))
SAY.insert(0, (r"\bcommitSync\b", "commit sync"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CW = 1.15
CELL_Y, OFF_Y, TITLE_Y = 1.9, 1.32, 3.3
BM_Y0, BM_Y1 = 2.28, 2.95             # the bookmark: a blue post above the log
FG_Y = 0.92                           # the finger: a yellow pointer under the offsets
CX = [-5.75 + CW / 2 + CW * k for k in range(10)]
C_C = np.array([-4.0, -1.3, 0])        # the consumer
L_C = np.array([3.6, -1.3, 0])         # the ledger
BAR_Y, CAP_Y = -2.78, -3.27


def edge(k):
    return -5.75 + CW * k


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def rbox(w, h, color, c):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)


def cell(k):
    return Rectangle(width=CW - 0.08, height=0.6, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to([CX[k], CELL_Y, 0])


def pay(k, color=WHITE):
    return M(f"pay-0{k}", 17, color).move_to([CX[k], CELL_Y, 0])


def bookmark(k, name="bookmark"):
    x = edge(k)
    post = Line([x, BM_Y0, 0], [x, BM_Y1, 0], stroke_width=4, color=BLUE_M)
    flag = Polygon([x, BM_Y1, 0], [x + 0.32, BM_Y1 - 0.13, 0], [x, BM_Y1 - 0.26, 0], stroke_width=0).set_fill(BLUE_M, 1)
    lab = T(f"{name}: {k}", 19, BLUE_M)
    if k >= 8:
        right_at(lab, x - 0.15, BM_Y1 - 0.13)
    else:
        left_at(lab, x + 0.42, BM_Y1 - 0.13)
    return VGroup(post, flag, lab).set_z_index(3)


def finger(k, name="finger"):
    x = edge(k)
    tri = Triangle(stroke_width=0).set_fill(YELLOW_M, 1).scale(0.13).move_to([x, FG_Y, 0])
    lab = T(f"{name}: {k}", 19, YELLOW_M)
    if k >= 8:
        right_at(lab, x - 0.25, FG_Y)
    else:
        left_at(lab, x + 0.25, FG_Y)
    return VGroup(tri, lab).set_z_index(3)


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.5, height=4.1, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.25, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 1.9)
    rows = VGroup()
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * M("x" * 40, 16).width / 40
        rows.add(left_at(M(s.strip() if s.strip() else " ", 16, col), x - 3.0 + ind, 1.35 - 0.42 * k))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["props.put(\"enable.auto.commit\", \"false\");",
        "while (running) {",
        "  var batch = consumer.poll(timeout);",
        "  // the work first",
        "  for (var r : batch) ledger.apply(r);",
        "  // then move the bookmark",
        "  consumer.commitSync();",
        "}"]
KOTLIN = ["props[\"enable.auto.commit\"] = \"false\"",
          "while (running) {",
          "  val batch = consumer.poll(timeout)",
          "  // the work first",
          "  for (r in batch) ledger.apply(r)",
          "  // then move the bookmark",
          "  consumer.commitSync()",
          "}"]


class ConsumerOffsets(Base):
    """msg-07, section 2. The ledger crashes at 11:02: one account 20.00 too high, while a team with two lines swapped
    lost three payments. The poll loop over pay-00..pay-09 (10.00 each, acct-1). The book: a finger (the position) and
    a bookmark (the committed offset). Poll 0-4, the finger jumps to 5, work, commit 5. Poll 5-9, crash at pay-07;
    predict where consumer 2 starts: pay-05 and pay-06 again (at-least-once, 120.00). Swap the lines: commit 10 first,
    pay-07..09 lost (at-most-once, 70.00). Why at-least-once for payments; skipping seen ids gives 100.00; auto-commit's
    condition; exactly once across two systems. Code in Java and Kotlin, the moral, the podcast check."""

    def bal(self, s, color=WHITE):
        return self.put("bal", M(s, 36, color).move_to(L_C + 0.05 * DOWN))

    def lnote(self, s, color=GREY_B):
        return self.put("lnote", T(s, 17, color).move_to(L_C + 0.55 * DOWN))

    def cstate(self, s, color=GREY_B):
        return self.put("cstate", fit(T(s, 18, color), 3.3).move_to(C_C + 0.3 * DOWN))

    def ctitle(self, s):
        return self.put("ctitle", T(s, 26).move_to(C_C + 0.35 * UP))

    def set_bm(self, k, name=None):
        self.bm_k, self.bm_name = k, name or self.bm_name
        return self.put("bm", bookmark(k, self.bm_name), RIGHT)

    def set_fg(self, k, name=None):
        self.fg_k, self.fg_name = k, name or self.fg_name
        return self.put("fg", finger(k, self.fg_name), RIGHT)

    def mark(self, ks, color):
        return [self.pays[k].animate.set_color(color) for k in ks]

    def hold(self, ks, on=True):
        return [self.cells[k].animate.set_stroke(YELLOW_M if on else GREY_C, width=3 if on else 2) for k in ks]

    def apply(self, k, total, color=WHITE, pcolor=GREEN_M):
        """The consumer adds one payment: a dot runs from the record to the ledger, and the balance moves."""
        d = Dot(radius=0.08, color=YELLOW_M).move_to([CX[k], CELL_Y - 0.35, 0]).set_z_index(6)
        path = VMobject().set_points_as_corners([d.get_center(), [C_C[0] + 1.85, C_C[1] + 0.2, 0], [L_C[0] - 2.15, L_C[1] + 0.2, 0]])
        return [Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, run_time=0.5), FadeOut(d, run_time=0.05)),
                *self.mark([k], pcolor)], lambda: self.bal(f"{total:.2f}", color)

    def do(self, k, total, color=WHITE, pcolor=GREEN_M):
        a, b = self.apply(k, total, color, pcolor)
        return [(lambda: a, 0.6), (lambda: b(), 0.25)]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.bm_name, self.fg_name = "bookmark", "finger"
        self.title_card("Where does a restart start?", "commit before or after the work")

        self.cells = VGroup(*[cell(k) for k in range(10)])
        offs = VGroup(*[T(str(k), 17, GREY_B).move_to([CX[k], OFF_Y, 0]) for k in range(10)])
        self.pays = [pay(k) for k in range(10)]
        ttl = T("partition 0 of payments: 10.00 each, all for acct-1", 20, GREY_B).move_to([0, TITLE_Y, 0])
        cbox = rbox(3.7, 1.6, GOLD_M, C_C)
        lbox = rbox(4.3, 1.6, GREEN_M, L_C)
        link = Arrow(C_C + [1.9, 0.2, 0], L_C + [-2.2, 0.2, 0], buff=0, stroke_width=2.5, color=GREY_C, max_tip_length_to_length_ratio=0.04)

        # ---------------- scene 1: the Saturday crash ----------------
        self.steps("Picture the payments app on a busy Saturday. Every card payment goes into Kafka, a program that keeps "
                   "a log of messages and lets other programs read it.", [
            "Every card payment",
            (lambda: [FadeIn(self.cells), FadeIn(offs), FadeIn(ttl)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * DOWN) for p in self.pays], lag_ratio=0.15)], 1.4),
        ])
        self.steps("A second program, the ledger, reads each payment and adds it to the right account's balance.", [
            (lambda: [FadeIn(lbox), *self.put("ltitle", T("ledger", 26).move_to(L_C + 0.5 * UP)), *self.bal("0.00")], 0.7),
            "reads each",
            (lambda: [FadeIn(cbox), FadeIn(link), *self.ctitle("ledger's reader"), *self.cstate("reads, adds, repeats")], 0.7),
        ])
        self.steps("At 11:02 the ledger crashes and restarts by itself. By Monday, one account is 20.00 too high: "
                   "two payments were added twice.", [
            "crashes",
            (lambda: [cbox.animate.set_stroke(RED_M), *self.cstate("11:02: crashed, restarted", RED_M)], 0.6),
            "By Monday",
            (lambda: [*self.bal("120.00", RED_M), *self.lnote("should be 100.00: 20.00 too high", RED_M)], 0.6),
        ])
        self.steps("Another team ran the same program with two lines swapped, and lost three payments instead. "
                   "Which two lines? Hold that question.", [
            "lost three",
            (lambda: [*self.bal("70.00", RED_M), *self.lnote("should be 100.00: three payments lost", RED_M)], 0.6),
            "Which two lines",
            (lambda: self.cap("which two lines?", WHITE), 0.5),
        ])

        # ---------------- scene 2: the loop ----------------
        self.steps("The ledger's reader is a consumer, and it runs a loop. Poll: ask Kafka for the next few payments. "
                   "Process: add each one. Commit: save how far you got. Repeat.", [
            (lambda: [*self.uncap(), cbox.animate.set_stroke(GOLD_M), *self.ctitle("consumer 1"), *self.cstate("poll, process, commit"),
                      *self.bal("0.00"), *self.drop("lnote")], 0.7),
            "Poll",
            (lambda: self.cap("poll: ask for the next few"), 0.4),
            "Process",
            (lambda: self.cap("process: add each one to the ledger"), 0.4),
            "Commit",
            (lambda: self.cap("commit: save how far you got"), 0.4),
        ])
        self.steps("A restart doesn't carry on where the crash stopped. Everything in memory is gone. "
                   "It carries on from the last place it wrote down. So when should it write that place down?", [
            (lambda: self.cap("a restart carries on from the last place written down"), 0.5),
            "So when",
            (lambda: self.cap("so when should it write it down?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 3: the book ----------------
        self.steps("Think of reading a long book over many evenings. Your finger marks the line you're reading now. "
                   "A bookmark marks where you'll start tomorrow.", [
            (lambda: self.uncap(), 0.3),
            "Your finger",
            (lambda: self.set_fg(0), 0.6),
            "A bookmark",
            (lambda: self.set_bm(0), 0.6),
        ])
        self.steps("If you nod off, your finger slips, and only the bookmark is left.", [
            "your finger slips",
            (lambda: [self.lab["fg"].animate.shift(0.35 * DOWN).set_opacity(0)], 0.7),
            "only the bookmark",
            (lambda: [glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.6),
            (lambda: self.set_fg(0), 0.4),
        ])
        self.steps("In Kafka, the finger is the position: the next offset the consumer will read. It lives in memory. "
                   "The bookmark is the committed offset. Kafka saves it for the group, and it moves only when you commit.", [
            "the position",
            (lambda: [*self.set_fg(0, "position"), *self.cap("the finger: the position, in memory", YELLOW_M)], 0.6),
            "The bookmark is",
            (lambda: [*self.set_bm(0, "committed"), *self.cap("the bookmark: the committed offset, saved by Kafka", BLUE_M)], 0.6),
        ])

        # ---------------- scene 4: the first batch ----------------
        self.steps("Let's run it. Consumer 1 polls and gets offsets 0 to 4. The position jumps to 5 at once, "
                   "before a single payment is added. The committed offset is still 0.", [
            (lambda: self.uncap(), 0.3),
            "gets offsets",
            (lambda: [*self.hold(range(5)), *self.cstate("holds 0 to 4")], 0.6),
            "jumps to 5",
            (lambda: self.set_fg(5), 0.5),
            "still 0",
            (lambda: [glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.6),
        ])
        steps_b1 = []
        for k in range(5):
            steps_b1 += self.do(k, 10.0 * (k + 1))
        self.steps("It adds pay-00 to pay-04 to the ledger. Then it commits 5: the next record to read.", [
            *steps_b1,
            "Then it commits",
            (lambda: [*self.set_bm(5), *self.hold(range(5), False), *self.cstate("committed 5")], 0.6),
            (lambda: self.cap("commit the next record to read: the last one done, plus one"), 0.4),
        ])

        # ---------------- scene 5: the crash, predicted ----------------
        self.steps("Next poll: 5 to 9, and the position moves to 10. It adds pay-05 and pay-06, and dies while adding pay-07.", [
            (lambda: [*self.uncap(), *self.hold(range(5, 10)), *self.cstate("holds 5 to 9")], 0.5),
            (lambda: self.set_fg(10), 0.5),
            "It adds",
            *self.do(5, 60.0),
            *self.do(6, 70.0),
            "dies",
            (lambda: [cbox.animate.set_stroke(RED_M), *self.cstate("crashed at pay-07", RED_M), *self.mark([7], RED_M)], 0.5),
            (lambda: [self.lab["fg"].animate.shift(0.35 * DOWN).set_opacity(0)], 0.6),
        ])
        self.lab.pop("fg")
        self.steps("Consumer 2, a new copy of the program, takes over. Where does it start, and what happens to pay-05? Pause and guess.", [
            (lambda: [cbox.animate.set_stroke(GOLD_M), *self.ctitle("consumer 2"), *self.cstate("just started"), *self.hold(range(5, 10), False),
                      *self.mark([5, 6, 7], WHITE)], 0.7),
            "Pause and guess",
            (lambda: self.cap("where does consumer 2 start? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It knows only what Kafka saved: committed offset 5. So pay-05 and pay-06, already in the ledger, arrive a second time.", [
            (lambda: [*self.uncap(), glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.6),
            "So pay-05",
            (lambda: [*self.set_fg(5), *self.hold(range(5, 10))], 0.5),
            (lambda: self.set_fg(10), 0.4),
            *self.do(5, 80.0, RED_M, RED_M),
            *self.do(6, 90.0, RED_M, RED_M),
        ])
        steps_rest = []
        for i, k in enumerate(range(7, 10)):
            steps_rest += self.do(k, 90.0 + 10 * (i + 1), RED_M)
        self.steps("Then the rest, and a commit of 10. The balance ends at 120.00. That's the Saturday bug: 20.00 too high.", [
            *steps_rest,
            (lambda: [*self.set_bm(10), *self.hold(range(5, 10), False)], 0.5),
            "That's the Saturday",
            (lambda: [*self.lnote("should be 100.00: 20.00 too high", RED_M), *self.cap("nothing lost, two repeated", WHITE)], 0.6),
        ])
        self.steps("Process, then commit, means every payment is processed at least once, and some twice. "
                   "It's called at-least-once.", [
            "at least once",
            (lambda: self.cap("process, then commit: at-least-once", GREEN_M, 28), 0.6),
        ])

        # ---------------- scene 6: swap the two lines ----------------
        def reset(k_bm):
            return [*self.bal("50.00"), *self.drop("lnote"), *self.mark(range(5), GREEN_M), *self.mark(range(5, 10), WHITE),
                    *self.set_bm(k_bm), *self.set_fg(k_bm), *self.ctitle("consumer 1"), *self.cstate("poll, commit, process")]

        self.steps("So the other team thought: commit first, then nothing can ever repeat. Let's be fair and replay the second "
                   "batch their way.", [
            (lambda: [*self.uncap(), *reset(5)], 0.8),
            "commit first",
            (lambda: self.cap("commit first, then process", PURPLE_M), 0.5),
        ])
        self.steps("Consumer 1 polls 5 to 9 and commits 10 at once. It adds pay-05 and pay-06, and dies at pay-07.", [
            (lambda: [*self.hold(range(5, 10)), *self.set_fg(10)], 0.6),
            "commits 10",
            (lambda: [*self.set_bm(10), *self.cstate("committed 10, before the work", PURPLE_M)], 0.6),
            "It adds",
            *self.do(5, 60.0),
            *self.do(6, 70.0),
            "dies",
            (lambda: [cbox.animate.set_stroke(RED_M), *self.cstate("crashed at pay-07", RED_M)], 0.5),
            (lambda: [self.lab["fg"].animate.shift(0.35 * DOWN).set_opacity(0)], 0.5),
        ])
        self.lab.pop("fg")
        self.steps("Consumer 2 starts at 10. pay-07, pay-08 and pay-09 are never added, and nothing will ever deliver them again.", [
            (lambda: [cbox.animate.set_stroke(GOLD_M), *self.ctitle("consumer 2"), *self.cstate("starts at 10"), *self.set_fg(10),
                      *self.hold(range(5, 10), False)], 0.7),
            "are never added",
            (lambda: [*self.mark([7, 8, 9], RED_M), *[glow(self.cells[k], RED_M, 1.04) for k in (7, 8, 9)]], 0.8),
            "nothing will ever",
            (lambda: [*self.bal("70.00", RED_M), *self.lnote("should be 100.00: three payments lost", RED_M)], 0.6),
        ])
        self.steps("It's like moving your bookmark to the end of the chapter before you read it. Nod off, and tomorrow you skip "
                   "three pages, with no idea what happened in them. That's at-most-once: each record processed at most once, "
                   "and some never.", [
            "moving your bookmark",
            (lambda: [glow(self.lab["bm"][0], BLUE_M, 1.0)], 0.6),
            "That's at-most-once",
            (lambda: self.cap("commit, then process: at-most-once", RED_M, 28), 0.6),
        ])

        # ---------------- scene 7: which one, and the fine print ----------------
        self.steps("For payments, at-least-once is the only safe choice. A lost payment is a missing line that nobody notices. "
                   "A repeat can be spotted.", [
            (lambda: [*self.uncap(), *self.cap("for payments: at-least-once", GREEN_M, 28)], 0.5),
            "A lost payment",
            (lambda: [*[glow(self.cells[k], RED_M, 1.04) for k in (7, 8, 9)]], 0.8),
            "A repeat can be spotted",
            (lambda: [*self.cap("a lost payment: silent.   a repeat: it has an id you can spot", WHITE)], 0.5),
        ])
        self.steps("Watch. Consumer 2 starts at 5 again, and the ledger skips any payment id it has already applied. "
                   "pay-05 and pay-06: skipped. The rest: added. 100.00.", [
            (lambda: [*self.uncap(), *reset(5), *self.ctitle("consumer 2"), *self.cstate("starts at 5"), *self.lnote("skips ids it has seen")], 0.8),
            (lambda: [*self.mark([5, 6], GREEN_M), *self.bal("70.00")], 0.3),
            "pay-05 and pay-06",
            (lambda: [*self.set_fg(10), *self.hold(range(5, 10)), *[glow(self.cells[k], GREY_B, 1.04) for k in (5, 6)],
                      *self.lnote("pay-05, pay-06: seen, skipped")], 0.7),
            "The rest",
            *self.do(7, 80.0), *self.do(8, 90.0), *self.do(9, 100.0, GREEN_M),
            (lambda: [*self.set_bm(10), *self.hold(range(5, 10), False), *self.lnote("100.00: right", GREEN_M), *self.mark([7, 8, 9], GREEN_M)], 0.5),
        ])
        self.stamp("poster")
        self.steps("Two notes. By default, the consumer commits by itself every five seconds, inside poll. That's at-least-once "
                   "only if you finish each batch before the next poll. Hand the work to helper threads, and it can commit "
                   "payments nobody has added yet.", [
            (lambda: self.cap("auto-commit: every 5 seconds, inside poll"), 0.5),
            "only if you finish",
            (lambda: self.cap("safe only if each batch is finished before the next poll"), 0.5),
            "Hand the work",
            (lambda: self.cap("for payments: enable.auto.commit=false, and commit after the work", YELLOW_M), 0.5),
        ])
        self.steps("And exactly once? The commit goes to Kafka, but the work lands somewhere else, like a database. "
                   "No order of two writes to two systems makes them one step. At-least-once, plus work that ignores repeats, "
                   "gets the same result.", [
            (lambda: self.cap("two writes, two systems: never one step"), 0.5),
            "At-least-once, plus",
            (lambda: self.cap("at-least-once + ignore repeats = the effect lands once", GREEN_M), 0.5),
        ])

        # ---------------- scene 8: the code ----------------
        diagram = VGroup(self.cells, offs, ttl, cbox, lbox, link, *self.pays, *self.lab.values())
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin: turn auto-commit off, then in the loop, poll, do the work, and only then call commitSync.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "turn auto-commit",
            (lambda: hl((0,), PURPLE_M), 1.0),
            "do the work",
            (lambda: hl((4,), GREEN_M), 1.0),
            "only then",
            (lambda: hl((6,), BLUE_M), 1.0),
        ], after=0.8)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So which two lines? Process and commit. Both teams had the same two lines, in a different order. "
                   "Move the bookmark after the work, give every payment an id, and a crash costs only a little reading twice.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            "in a different order",
            (lambda: self.cap("process, then commit: a few repeats.   commit, then process: silent losses", WHITE), 0.6),
            "Move the bookmark",
            (lambda: [glow(self.lab["bm"][0], BLUE_M, 1.0), *self.cap("move the bookmark after the work", YELLOW_M, 30)], 0.7),
        ], after=0.6)
        self.steps("One quick check. You pause a podcast, close the app at once, and open it on another device. "
                   "It starts a few seconds early, so you hear them twice. At-least-once, or at-most-once? Pause and think.", [
            (lambda: self.cap("starts a few seconds early: which one? pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("At-least-once. Its bookmark was saved a little behind where you were, so you hear a bit twice, and miss nothing.", [
            (lambda: self.cap("at-least-once: the bookmark was behind, so you repeat, and miss nothing", GREEN_M), 0.6),
        ])
        self.wait(2.0)
