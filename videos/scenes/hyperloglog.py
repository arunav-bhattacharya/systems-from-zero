from sfz import *

SAY.insert(0, (r"\bPFADD\b", "P F add"))
SAY.insert(0, (r"\bPFCOUNT\b", "P F count"))
SAY.insert(0, (r"\bPFMERGE\b", "P F merge"))
SAY.insert(0, (r"\bSCARD\b", "S card"))
SAY.insert(0, (r"\bHyperLogLog\b", "hyper log log"))
SAY.insert(0, (r"\bFlajolet\b", "Flah zho lay"))
SAY.insert(0, (r"(?i)\bcard:A\b", "card eh"))
SAY.insert(0, (r"(?i)\bcard:B\b", "card bee"))
SAY.insert(0, (r"(?i)\bcard:C\b", "card see"))
SAY.insert(0, (r"\bINCR\b", "increment"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CMD_Y, BITS_Y, REG_Y, RLAB_Y, NOTE_Y, CAP_Y, BAR_Y = 3.05, 1.75, -0.45, -1.1, -1.95, -3.22, -2.72
REG_W, REG_GAP = 0.95, 0.18
REG_X = [(-3.5 + k) * (REG_W + REG_GAP) for k in range(8)]


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d, run_time=0.3), FadeIn(new, shift=0.1 * d))


def outline(m, color=YELLOW_M, buff=0.08):
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.1, stroke_width=4).set_z_index(7)
    return Succession(Create(r, run_time=0.35), FadeOut(r, run_time=0.45))


def person(c, color=GOLD_M):
    head = Circle(radius=0.16, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.3), 1).move_to(c + np.array([0, 0.32, 0]))
    body = RoundedRectangle(corner_radius=0.12, width=0.42, height=0.42, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.3), 1).move_to(c + np.array([0, -0.08, 0]))
    return VGroup(body, head)


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0]).set_z_index(3)
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


class Hyperloglog(Base):
    """cache-04, section 1. How many different cards paid today? A set of 100,000 cards takes 4.4 MB; INCR counts
    repeats. The fair: everyone flips a coin until heads; keep only the longest run of tails. The hash is the coin;
    the rank is the run. Predict: a card that pays again can't raise the record. One record is a wild guess, so 8
    registers picked by the low bits (the stepper's card:A, card:B, card:C). The name, 16,384 registers of 6 bits in
    12 KB, 0.81% error. The real run: 101,058 for 100,000, 14,364 bytes against 4,361,843. Guardrail: it only counts;
    PFMERGE. The moral, and a check (did card:A pay?)."""

    def cmd(self, s):
        return self.put("cmd", fit(M("> " + s, 19, YELLOW_M), 13.0).move_to([0, CMD_Y, 0]))

    def note(self, s, color=WHITE, size=22):
        return self.put("note", fit(T(s, size, color), 13.0).move_to([0, NOTE_Y, 0]))

    def reg(self, k, v, color=WHITE):
        return self.put(f"r{k}", M(str(v), 26, color).move_to([REG_X[k], REG_Y, 0]))

    def bits(self, card, rest, idx, rest_note, idx_note):
        lab = M(f"hash({card}) =", 22, GREY_B)
        r = M(rest, 30, WHITE)
        i = M(idx, 30, YELLOW_M)
        g = VGroup(lab, r, i).arrange(RIGHT, buff=0.3).move_to([0, BITS_Y, 0])
        rn = T(rest_note, 18, WHITE).next_to(r, DOWN, buff=0.22)
        inn = T(idx_note, 18, YELLOW_M).next_to(i, DOWN, buff=0.22)
        if rn.get_right()[0] > inn.get_left()[0] - 0.3:
            rn.shift((inn.get_left()[0] - 0.3 - rn.get_right()[0]) * RIGHT)
        return self.put("bits", VGroup(g, rn, inn))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Counting cards without a list", "a HyperLogLog in 12 KB")

        # ---------------- scene 1: the question ----------------
        cafe = RoundedRectangle(corner_radius=0.14, width=3.2, height=1.6, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M, 0.1), 1).move_to([-4.2, 0.9, 0])
        cafe_t = T("the café", 22, GOLD_M).move_to(cafe.get_top() + [0, -0.3, 0])
        cards_in = [M(s, 18, WHITE) for s in ("card 7", "card 9", "card 7", "card 7", "card 3")]
        listbox = RoundedRectangle(corner_radius=0.12, width=2.6, height=2.6, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M, 0.1), 1).move_to([1.2, 0.6, 0])
        list_t = T("cards seen", 20, BLUE_M).next_to(listbox, UP, buff=0.15)
        seen = [M(s, 18, WHITE).move_to([1.2, 1.4 - 0.45 * k, 0]) for k, s in enumerate(("card 7", "card 9", "card 3"))]
        cnt = T("different cards: 3", 24, GREEN_M).move_to([4.9, 0.6, 0])
        self.steps("Picture a café owner who wants one new number on her screen: how many different cards paid at her café today. "
                   "A regular who buys three coffees counts once.", [
            (lambda: [FadeIn(cafe), FadeIn(cafe_t)], 0.6),
            "how many different",
            (lambda: [FadeIn(listbox), FadeIn(list_t)], 0.6),
            "A regular",
            (lambda: [Succession(*[Succession(FadeIn(c.move_to(cafe.get_center() + [0, -0.2, 0]), run_time=0.1),
                                              c.animate(run_time=0.35).move_to(listbox.get_center()).set_opacity(0), run_time=0.45)
                                   for c in cards_in]), Succession(*[FadeIn(s) for s in seen], lag_ratio=1.0, run_time=2.2)], 2.3),
            (lambda: [FadeIn(cnt)], 0.4),
        ])
        self.steps("The company keeps numbers like this in Redis, a program that holds data in memory and answers commands from other programs. "
                   "The obvious answer is a list of every card that paid. It's exact, and tiny for one café.", [
            "a list of every card",
            (lambda: [outline(listbox, BLUE_M, 0.06)], 0.8),
        ])
        self.steps("But there are 20,000 shops, counted every hour. And the list grows with every new card: 100,000 cards took about 4.4 MB. "
                   "Can you count without the list? Hold that question.", [
            "20,000 shops",
            (lambda: self.cap("20,000 shops, every hour", WHITE), 0.5),
            "100,000 cards",
            (lambda: [*self.cap("a set of 100,000 cards: about 4.4 MB", RED_M), listbox.animate.set_stroke(RED_M)], 0.6),
            "Hold that",
            (lambda: self.cap("can you count without the list?", YELLOW_M), 0.5),
        ], after=0.3)
        self.stamp("question")

        # ---------------- scene 2: INCR, and the wish ----------------
        self.steps("Try the simplest counter: INCR, add one, on every payment. It counts payments, not cards. The regular counts three times.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*seen)), list_t.animate.set_opacity(0), listbox.animate.set_stroke(BLUE_M),
                      *self.put("incr", T("INCR on every payment: 5", 24, RED_M).move_to([5.0, 0.6, 0])), FadeOut(cnt)], 0.7),
            "three times",
            (lambda: self.cap("card 7 counted three times: 5, not 3", RED_M), 0.5),
        ])
        self.steps("To skip the repeats, you must remember which cards you've seen. That's the list again. "
                   "An exact count of different things needs memory that grows with the count.", [
            "the list again",
            (lambda: [*self.drop("incr"), list_t.animate.set_opacity(1), *[FadeIn(s) for s in seen]], 0.6),
            "An exact count",
            (lambda: self.cap("an exact count of different things: memory that grows with the count", WHITE), 0.6),
        ])
        self.steps("So let's give up a little exactness.", [
            (lambda: self.cap("wanted: a small, fixed memory, and an answer that's nearly right", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("pain")

        # ---------------- scene 3: the fair ----------------
        runs = ["H", "T H", "H", "T T T H", "T H", "H"]
        tails = [0, 1, 0, 3, 1, 0]
        px = [-5.6 + 1.45 * k for k in range(6)]
        people = [person(np.array([x, 1.0, 0])) for x in px]
        flips = [M(r, 18, WHITE).move_to([x, 0.2, 0]) for r, x in zip(runs, px)]
        board = RoundedRectangle(corner_radius=0.12, width=3.0, height=1.5, stroke_color=YELLOW_M, stroke_width=3).set_fill(fillc(YELLOW_M, 0.1), 1).move_to([4.8, 0.7, 0])
        board_t = T("longest run of tails", 19, YELLOW_M).move_to(board.get_top() + [0, -0.3, 0])

        def record(v):
            return self.put("rec", T(str(v), 36, WHITE).move_to(board.get_center() + [0, -0.18, 0]))

        self.steps("Picture a fair, where you want to know how many people came, without writing down a single name.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(cafe, cafe_t, listbox, list_t, *seen))], 0.6),
            "a fair",
            (lambda: [LaggedStart(*[FadeIn(p) for p in people], lag_ratio=0.12)], 0.9),
        ])
        self.steps("You ask each visitor to flip a coin until it lands heads, and to tell you how many tails came first. "
                   "You keep one number: the longest run of tails anyone has reported.", [
            "flip a coin",
            (lambda: [LaggedStart(*[FadeIn(f, shift=0.1 * DOWN) for f in flips], lag_ratio=0.15)], 1.2),
            "You keep one number",
            (lambda: [FadeIn(board), FadeIn(board_t), *record(0)], 0.5),
            *[x for k in (1, 3) for x in ((lambda k=k: [outline(flips[k], YELLOW_M, 0.06), *record(tails[k])], 0.6),)],
        ])
        self.steps("A run of 10 tails turns up about once in 1,024 tries. So if your record is 10, about a thousand people have probably come.", [
            "A run of 10",
            (lambda: [*record(10), *self.cap("a run of 10 tails: about once in 1,024 tries", WHITE)], 0.6),
            "about a thousand",
            (lambda: self.cap("record 10: about a thousand people", YELLOW_M), 0.5),
        ])
        self.steps("It's the laziest head count ever taken, and it works.", [], after=0.3)
        self.stamp("fair")

        # ---------------- scene 4: the hash is the coin ----------------
        self.steps("In code, the coin flips come from a hash function. It turns any text into a number that looks random, "
                   "and the same text always gives the same number.", [
            (lambda: [*self.cap("the coin = a hash function: random-looking, but the same text gives the same number", WHITE)], 0.6),
            "any text",
            (lambda: [*self.put("hx", M("hash(\"card:A\") = ...1011 0100", 26, WHITE).move_to([0, -1.0, 0]))], 0.6),
        ])
        self.steps("Read its bits from the right. A 0 is a tail, a 1 is heads. Count the zeros before the first 1, and add one. "
                   "That's the hash's rank.", [
            "from the right",
            (lambda: [outline(self.lab["hx"], YELLOW_M, 0.08)], 0.7),
            "Count the zeros",
            (lambda: self.cap("two zeros, then a 1: rank 3", YELLOW_M), 0.5),
            "rank",
            (lambda: self.cap("rank = the zeros before the first 1, plus one", WHITE), 0.5),
        ])
        self.steps("A rank of r turns up about once in 2 to the power r different cards.", [
            (lambda: self.cap("rank r: about once in 2 to the r different cards", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 5: predict, repeats are free ----------------
        self.steps("Now the regular pays again. Does her card push the record up? Pause and guess.", [
            (lambda: [*self.cap("the same card pays again: does the record go up?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. A visitor who flips again gets a new run. A card that pays again has the same hash, so the same rank. "
                   "Here the fair picture breaks, in our favor: repeats are free.", [
            (lambda: [outline(self.lab["hx"], GREEN_M, 0.08)], 0.7),
            "same rank",
            (lambda: self.cap("same card, same hash, same rank: the record can't move", GREEN_M), 0.5),
            "in our favor",
            (lambda: self.cap("where the fair picture breaks, in our favor: repeats are free", GOLD_M), 0.6),
        ], after=0.3)
        self.stamp("repeats")

        # ---------------- scene 6: one record is a wild guess; registers ----------------
        self.steps("One record is a wild guess, though. A single lucky card with 20 zeros would make you believe in a million cards.", [
            (lambda: [*self.drop("hx"), *record(20), board.animate.set_stroke(RED_M)], 0.6),
            "a million",
            (lambda: self.cap("one lucky card, 20 zeros: \"a million cards\"", RED_M), 0.5),
        ])
        regs = VGroup(*[RoundedRectangle(corner_radius=0.08, width=REG_W, height=0.8, stroke_color=TEAL_M, stroke_width=3)
                        .set_fill(fillc(TEAL_M, 0.12), 1).move_to([x, REG_Y, 0]) for x in REG_X])
        rl = VGroup(*[T(f"r{k}", 18, GREY_B).move_to([x, RLAB_Y, 0]) for k, x in enumerate(REG_X)])
        self.steps("So keep many records. Split the cards into groups by a few bits of their hash, and keep the highest rank in each group.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*people, *flips, board, board_t)), *self.drop("rec")], 0.6),
            "many records",
            (lambda: [LaggedStart(*[FadeIn(r) for r in regs], lag_ratio=0.08), FadeIn(rl),
                      *[x for k in range(8) for x in self.reg(k, 0, GREY_B)]], 1.0),
            "keep the highest",
            (lambda: self.cap("8 records, called registers: each keeps the highest rank in its group", TEAL_M), 0.6),
        ])
        self.steps("Card:A. Its lowest three bits, 0 1 1, pick register 3. The rest ends in one zero, then a 1: rank 2.", [
            (lambda: [*self.cmd("PFADD visitors card:A"), *self.bits("card:A", "10110", "011", "rest: one 0, then a 1: rank 2", "index 011 = r3")], 0.7),
            "pick register 3",
            (lambda: [regs[3].animate.set_stroke(YELLOW_M)], 0.4),
            "rank 2",
            (lambda: [*self.reg(3, 2, YELLOW_M), *self.note("PFADD returns 1: register 3 went from 0 to 2", GREEN_M)], 0.5),
        ])
        self.steps("Card:B lands in register 5, rank 1. Half of all hashes look like that.", [
            (lambda: [regs[3].animate.set_stroke(TEAL_M), *self.reg(3, 2), *self.cmd("PFADD visitors card:B"),
                      *self.bits("card:B", "00111", "101", "rest ends in a 1 at once: rank 1", "index 101 = r5")], 0.7),
            "register 5",
            (lambda: [regs[5].animate.set_stroke(YELLOW_M), *self.reg(5, 1, YELLOW_M), *self.note("PFADD returns 1: register 5 went from 0 to 1", GREEN_M)], 0.5),
        ])
        self.steps("Card:C also lands in register 3, with three zeros: rank 4. The register keeps the larger, so 4.", [
            (lambda: [regs[5].animate.set_stroke(TEAL_M), *self.reg(5, 1), *self.cmd("PFADD visitors card:C"),
                      *self.bits("card:C", "01000", "011", "rest ends in three 0s: rank 4", "index 011 = r3 again")], 0.7),
            "The register keeps",
            (lambda: [regs[3].animate.set_stroke(YELLOW_M), *self.reg(3, 4, YELLOW_M), *self.note("PFADD returns 1: register 3 went from 2 to 4", GREEN_M)], 0.5),
        ])
        self.steps("And card:A pays again: same register, rank 2, and 2 isn't above 4. Nothing changes.", [
            (lambda: [regs[3].animate.set_stroke(TEAL_M), *self.reg(3, 4), *self.cmd("PFADD visitors card:A"),
                      *self.bits("card:A", "10110", "011", "same card, same hash, same rank 2", "r3 again")], 0.7),
            "Nothing changes",
            (lambda: [outline(regs[3], GREEN_M, 0.06), *self.note("PFADD returns 0: no register changed", WHITE)], 0.6),
        ])
        guess = [3, 2, 5, 1, 4, 3, 2, 3]
        self.steps("After thousands of cards, each register holds the longest run it saw. A kind of average combines them, "
                   "one that stops a lucky register from pulling the answer too far.", [
            (lambda: [*self.drop("bits", "note"), *self.cmd("PFCOUNT visitors"), *[x for k in range(8) for x in self.reg(k, guess[k])]], 0.8),
            "A kind of average",
            (lambda: [*self.cap("the estimate: a careful average of all the registers", WHITE), *[outline(r, TEAL_M, 0.04) for r in regs]], 0.8),
        ], after=0.3)
        self.stamp("registers")

        # ---------------- scene 7: the name, and the real numbers ----------------
        self.steps("Redis does this with 16,384 registers. Fourteen bits of the hash pick the register. A rank fits in 6 bits, "
                   "so all the registers take 12,288 bytes.", [
            (lambda: [*self.note("16,384 registers x 6 bits = 12,288 bytes", WHITE)], 0.6),
            "Fourteen bits",
            (lambda: self.cap("64-bit hash: 14 bits pick the register, 50 bits give the rank (at most 51)", WHITE), 0.6),
        ])
        self.steps("That structure is a HyperLogLog. It takes at most 12 KB, and its standard error is 0.81 percent: about two times in "
                   "three, the estimate is within 0.81 percent of the truth, for a thousand cards or a billion.", [
            "a HyperLogLog",
            (lambda: [*self.put("name", T("HyperLogLog", 34, TEAL_M).move_to([0, BITS_Y, 0])), *self.drop("cmd")], 0.6),
            "standard error",
            (lambda: self.cap("standard error 0.81%: two times in three, within 0.81% of the truth", WHITE), 0.6),
        ])
        self.steps("The commands start with PF, for Philippe Flajolet, who invented the method. PFADD adds cards, and PFCOUNT gives the estimate.", [
            "PFADD adds",
            (lambda: self.cap(M("PFADD key card ...      PFCOUNT key", 20, YELLOW_M)), 0.5),
        ], after=0.3)

        set_bar = Rectangle(width=9.0, height=0.42, stroke_color=RED_M, stroke_width=2).set_fill(fillc(RED_M, 0.5), 1)
        hll_bar = Rectangle(width=0.03, height=0.42, stroke_color=TEAL_M, stroke_width=1.5).set_fill(TEAL_M, 1)
        set_bar.move_to([-4.0 + 4.5, 1.25, 0])
        hll_bar.move_to([-4.0 + 0.015, 0.45, 0])
        set_l = T("set", 22, RED_M).next_to(set_bar, LEFT, buff=0.25)
        hll_l = T("HyperLogLog", 22, TEAL_M).move_to([set_l.get_center()[0] - 0.75, 0.45, 0])
        set_v = T("SCARD 100000    4,361,843 bytes", 20, WHITE).next_to(set_bar, UP, buff=0.12).align_to(set_bar, LEFT)
        hll_v = T("PFCOUNT 101058    14,364 bytes", 20, WHITE).next_to(hll_bar, RIGHT, buff=0.3)
        self.steps("On the lab server, 100,000 cards went into a set and into a HyperLogLog. The set says exactly 100,000. "
                   "The HyperLogLog says 101,058: 1.06 percent too high.", [
            (lambda: [*self.drop("name", "note"), *self.uncap(), FadeOut(VGroup(regs, rl)), *self.drop(*[f"r{k}" for k in range(8)])], 0.6),
            "into a set",
            (lambda: [FadeIn(set_l), FadeIn(hll_l)], 0.5),
            "exactly 100,000",
            (lambda: [FadeIn(set_v)], 0.5),
            "says 101,058",
            (lambda: [FadeIn(hll_v), *self.cap("101,058 for 100,000: 1.06% too high", WHITE)], 0.6),
        ])
        self.steps("And the memory? The set takes 4,361,843 bytes. The HyperLogLog takes 14,364, about 300 times less.", [
            "The set takes",
            (lambda: [GrowFromEdge(set_bar, LEFT)], 1.0),
            "The HyperLogLog takes",
            (lambda: [GrowFromEdge(hll_bar, LEFT)], 0.4),
            "300 times less",
            (lambda: [*self.cap("about 300 times less memory, off by about 1%", YELLOW_M), outline(hll_bar, YELLOW_M, 0.08)], 0.7),
        ], after=0.3)
        self.stamp("numbers")

        # ---------------- scene 8: guardrails ----------------
        self.steps("In exchange, it can't list the cards it has seen, and it can't say whether one card is among them. It only counts. "
                   "So use it when one percent either way is fine.", [
            (lambda: self.cap("it can't list the cards, or say if one card is in: it only counts", WHITE), 0.6),
            "one percent either way",
            (lambda: self.cap("use it when 1% either way is fine", YELLOW_M), 0.5),
        ])
        self.steps("One more gift. PFMERGE keeps the larger value of each register, so 24 hourly counters merge into one for the day, "
                   "and a card that paid in two hours still counts once.", [
            "PFMERGE",
            (lambda: self.cap(M("PFMERGE day hour:00 hour:01 ... hour:23", 20, YELLOW_M)), 0.5),
            "still counts once",
            (lambda: self.cap("each register: the larger of the two, so a repeat still counts once", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 9: moral and check ----------------
        self.steps("So the moral of the story: you don't need a list to count. Keep the longest runs, and the count comes out of them, "
                   "in 12 KB, whatever the crowd.", [
            (lambda: self.cap("you don't need a list to count: keep the longest runs", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.steps("One quick check. The owner asks: did card:A pay today? Can the HyperLogLog answer? Pause and think.", [
            (lambda: [*self.cmd("did card:A pay today?"), *self.cap("can the HyperLogLog answer?  pause and think", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. It kept only the longest runs, never the cards. It can count them, but it can't name one.", [
            (lambda: [*self.cap("no: it keeps runs, not cards. It counts, it can't name one", WHITE)], 0.6),
        ], after=0.3)
        self.play(*self.cap("a HyperLogLog: count different things in 12 KB, about 1% off", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
