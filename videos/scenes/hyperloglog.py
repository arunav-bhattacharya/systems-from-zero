from sfz import *


BY, BS, BP = 2.25, 0.6, 0.7                 # hash bits: row, square size, pitch
RY, RX0, RP = -1.35, -4.55, 1.3             # registers: row, x of register 0, pitch


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def bits(s, split=False):
    """An 8-bit toy hash, highest bit on the left. Zeros at the right end (before the first 1) are gold; with split,
    the last three bits stand apart in blue (they pick the register) and the run is counted in the rest."""
    body = s[:5] if split else s
    run = len(body) - len(body.rstrip("0"))
    g = VGroup()
    for i, ch in enumerate(s):
        x = (i - 3.5) * BP + (0.3 if split and i >= 5 else 0) - (0.15 if split else 0)
        if split and i >= 5:
            col = BLUE_M
        elif i >= len(body) - run - 1 and i < len(body):
            col = GOLD_M
        else:
            col = GREY_B
        r = Square(BS, stroke_color=col, stroke_width=2.5).set_fill(fillc(col, 0.2), 1).move_to([x, BY, 0])
        g.add(VGroup(r, M(ch, 24, WHITE).move_to([x, BY, 0])))
    return g


def card(name):
    return chip(name, WHITE, 22, mono=True).move_to([-5.2, BY, 0])


def under(s, color=GREY_B):
    return T(s, 20, color).move_to([0, BY - 0.72, 0])


def reg(i, v, color=GREY_B):
    x = RX0 + RP * i
    r = RoundedRectangle(corner_radius=0.1, width=1.1, height=0.8, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.18), 1).move_to([x, RY, 0])
    return VGroup(r, M(str(v), 26).move_to([x, RY, 0]))


class Hyperloglog(Base):
    """cache-04, section 1: distinct cards per merchant per hour; a set of 100,000 card ids took 4.4 MB and INCR counts
    repeats. Hash each card; the zeros at the right end plus one is the rank; rank r turns up once in 2^r cards, so a
    highest rank of 4 hints at about 16 cards, repeats change nothing, and one lucky hash misleads. Many registers: the
    stepper's toy with 8 registers (card:A to register 3 rank 2, card:B to 5 rank 1, card:C to 3 rank 4), combined with a
    harmonic mean; Redis keeps 16,384 six-bit registers, 12,288 bytes, standard error 0.81%."""

    def construct(self):
        self.title_card("HyperLogLog", "counting distinct cards without storing them")

        top = T("merchant m-17, this hour", 20, GREY_B).move_to([-6.1, 3.35, 0], aligned_edge=LEFT)
        sbox = RoundedRectangle(corner_radius=0.14, width=4.4, height=3.6, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        sbox.move_to([-3.5, 0.75, 0])
        stit = T("a set of card ids", 21).move_to([-3.5, 2.2, 0])
        ids = ["card:417", "card:9021", "card:58", "card:7730", "card:1206"]
        lines = [M(s, 19, GREY_B).move_to([-3.5, 1.65 - 0.4 * i, 0]) for i, s in enumerate(ids)]
        more = M("...", 19, GREY_B).move_to([-3.5, -0.4, 0])
        size = chip("100,000 ids: 4.4 MB", RED_M, 20).move_to([-3.5, -1.5, 0])
        many = T("and 20,000 merchants", 20, RED_M).move_to([-3.5, -2.15, 0])
        self.steps("How many distinct cards paid at one merchant this hour? A set of card ids answers exactly, "
                   "but a hundred thousand ids took 4.4 megabytes, and there are 20,000 merchants.", [
            (lambda: [FadeIn(top)], 0.5),
            "A set of card ids",
            (lambda: [FadeIn(sbox), FadeIn(stit)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * DOWN) for l in lines], lag_ratio=0.3), FadeIn(more)], 1.4),
            "but a hundred",
            (lambda: [FadeIn(size, shift=0.1 * UP)], 0.7),
            "and there are",
            (lambda: [FadeIn(many)], 0.6),
        ])

        cbox = RoundedRectangle(corner_radius=0.14, width=4.4, height=3.6, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        cbox.move_to([3.5, 0.75, 0])
        ctit = T("a counter: INCR per payment", 21).move_to([3.5, 2.2, 0])
        val = {"m": M("0", 48).move_to([3.5, 1.1, 0])}
        pays = [chip("card:417 pays", GOLD_M, 18, mono=True).move_to([3.5, 0.0, 0]) for _ in range(3)]
        wrong = T("3 payments, 1 distinct card", 20, RED_M).move_to([3.5, -1.5, 0])

        def tickup(n):
            new = M(str(n), 48).move_to([3.5, 1.1, 0])
            return [FadeIn(pays[n - 1], shift=0.2 * UP, rate_func=there_and_back_with_pause), Transform(val["m"], new)]

        self.steps("A counter is tiny, but it counts payments. A card that pays three times counts three times, "
                   "and skipping repeats means remembering every card.", [
            (lambda: [FadeIn(cbox), FadeIn(ctit), FadeIn(val["m"])], 0.7),
            "A card that pays",
            (lambda: tickup(1), 0.7),
            (lambda: tickup(2), 0.7),
            (lambda: tickup(3), 0.7),
            (lambda: [FadeIn(wrong), val["m"].animate.set_color(RED_M)], 0.6),
            "remembering every card",
            (lambda: [glow(sbox, RED_M, 1.02)], 0.8),
        ])

        c1 = card("card:417")
        b1 = bits("10110100")
        u1 = under("2 zeros at the right end, so rank 3")
        self.steps("So give up exactness. Hash each card id. A good hash looks random: every bit is 0 or 1 with even odds.", [
            (lambda: [FadeOut(VGroup(sbox, stit, *lines, more, size, many, cbox, ctit, val["m"], wrong, *pays))], 0.8),
            "Hash each",
            (lambda: [FadeIn(c1)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * RIGHT) for b in b1], lag_ratio=0.12)], 1.0),
            "every bit",
            (lambda: [*[b[0].animate.set_stroke(WHITE) for b in b1]], 0.4),
            (lambda: [*[b[0].animate.set_stroke(GREY_B) for b in b1]], 0.4),
        ])

        lad = VGroup(*[VGroup(M(f"rank {r}: ...1{'0' * (r - 1)}", 19, GOLD_M if r == 3 else WHITE),
                              T(f"1 in {2 ** r}", 19, GREY_B)).arrange(RIGHT, buff=0.4) for r in range(1, 5)])
        for i, l in enumerate(lad):
            l[0].move_to([1.35, 0.95 - 0.55 * i, 0], aligned_edge=LEFT)
            l[1].move_to([5.6, 0.95 - 0.55 * i, 0], aligned_edge=RIGHT)
        self.steps("Count the zeros at its right end, before the first 1, and add one: that's the rank. "
                   "Half of all hashes have rank 1, a quarter rank 2, an eighth rank 3.", [
            (lambda: [*[glow(b1[i][0], GOLD_M, 1.1) for i in (5, 6, 7)]], 0.8),
            "and add one",
            (lambda: [FadeIn(u1)], 0.6),
            "Half of all",
            (lambda: [FadeIn(lad[0], shift=0.1 * DOWN)], 0.5),
            "a quarter",
            (lambda: [FadeIn(lad[1], shift=0.1 * DOWN)], 0.5),
            "an eighth",
            (lambda: [FadeIn(lad[2], shift=0.1 * DOWN)], 0.5),
        ])

        c2 = card("card:9021")
        b2 = bits("01101000")
        u2 = under("3 zeros at the right end, so rank 4")
        rec = RoundedRectangle(corner_radius=0.14, width=4.2, height=1.5, stroke_color=GOLD_M, stroke_width=2.5)
        rec.set_fill(fillc(GOLD_M, 0.1), 1).move_to([-3.8, 0.45, 0])
        rtit = T("highest rank seen", 20, GOLD_M).move_to([-3.8, 0.8, 0])
        rv = {"m": T("3: about 8 cards", 22).move_to([-3.8, 0.25, 0])}
        self.steps("So a rank of 4 turns up about once in 16 distinct cards. "
                   "If the highest rank you've seen is 4, you've probably seen about 16 cards.", [
            (lambda: [FadeIn(lad[3], shift=0.1 * DOWN), FadeIn(rec), FadeIn(rtit), FadeIn(rv["m"])], 0.8),
            (lambda: [Transform(c1, c2), Transform(b1, b2), Transform(u1, u2),
                      lad[2][0].animate.set_color(WHITE), lad[3][0].animate.set_color(GOLD_M)], 1.0),
            "If the highest",
            (lambda: [Transform(rv["m"], T("4: about 16 cards", 22).move_to([-3.8, 0.25, 0])), glow(rec, GOLD_M, 1.03)], 0.9),
        ])

        c3 = card("card:417")
        b3 = bits("10110100")
        u3 = under("rank 3 again: no change", GREEN_M)
        self.steps("A card that pays again has the same hash and the same rank, so repeats change nothing.", [
            (lambda: [Transform(c1, c3), Transform(b1, b3), Transform(u1, u3)], 1.0),
            "repeats change",
            (lambda: [glow(rec, GREEN_M, 1.03)], 0.8),
        ])

        luck = chip("one lucky hash with 20 zeros: rank 21, about 2 million cards", RED_M, 19).move_to([0, -1.7, 0])
        self.steps("But one record is a wild guess. One lucky card with 20 zeros would claim about two million cards.", [
            "One lucky card",
            (lambda: [FadeIn(luck, shift=0.1 * UP), glow(rec, RED_M, 1.03)], 0.9),
        ])

        cA = card("card:A")
        bA = bits("01010011", split=True)
        uA = under("last 3 bits: register 3. Rest: 1 zero, rank 2")
        regs = [reg(i, 0) for i in range(8)]
        idx = VGroup(*[M(str(i), 17, GREY_C).move_to([RX0 + RP * i, RY - 0.65, 0]) for i in range(8)])
        rlab = T("8 registers", 20, GREY_B).move_to([RX0 - 0.55, RY + 0.75, 0], aligned_edge=LEFT)
        ar = {"m": Arrow([0.0, BY - 0.95, 0], [RX0 + RP * 3, RY + 0.48, 0], buff=0.05, stroke_width=3, color=BLUE_M,
                         max_tip_length_to_length_ratio=0.08)}
        self.steps("So keep many records. The last bits of the hash pick a register, "
                   "and each register keeps the highest rank it has seen.", [
            (lambda: [FadeOut(VGroup(luck, rec, rtit, rv["m"], lad))], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r) for r in regs], lag_ratio=0.08), FadeIn(idx), FadeIn(rlab)], 1.0),
            "The last bits",
            (lambda: [Transform(c1, cA), Transform(b1, bA), Transform(u1, uA)], 0.9),
            "pick a register",
            (lambda: [GrowArrow(ar["m"])], 0.6),
            "keeps the highest",
            (lambda: [Transform(regs[3], reg(3, 2, GOLD_M))], 0.6),
        ])

        def to(i):
            return Arrow([0.0, BY - 0.95, 0], [RX0 + RP * i, RY + 0.48, 0], buff=0.05, stroke_width=3, color=BLUE_M,
                         max_tip_length_to_length_ratio=0.08)

        self.steps("card B lands in register 5 with rank 1. card C lands in register 3 with rank 4, "
                   "and the register keeps the larger value. It never goes down.", [
            (lambda: [Transform(c1, card("card:B")), Transform(b1, bits("11001101", split=True)),
                      Transform(u1, under("register 5, rank 1")), Transform(ar["m"], to(5))], 0.9),
            (lambda: [Transform(regs[5], reg(5, 1, GOLD_M)), regs[3][0].animate.set_stroke(GREY_B)], 0.5),
            "card C",
            (lambda: [Transform(c1, card("card:C")), Transform(b1, bits("01000011", split=True)),
                      Transform(u1, under("register 3, rank 4")), Transform(ar["m"], to(3)), regs[5][0].animate.set_stroke(GREY_B)], 0.9),
            "keeps the larger",
            (lambda: [Transform(regs[3], reg(3, 4, GOLD_M))], 0.7),
            "never goes down",
            (lambda: [glow(regs[3][0], GOLD_M, 1.08)], 0.7),
        ])

        vals = [3, 2, 5, 4, 3, 2, 7, 3]
        form = T("estimate: harmonic mean of 2^register, scaled by the number of registers", 19).move_to([0, -2.85, 0])
        self.steps("After many cards, one register may be lucky. Redis takes a harmonic mean "
                   "of 2 to the power of each register, which damps the lucky ones, and scales it by the number of registers.", [
            (lambda: [FadeOut(ar["m"]), FadeOut(u1), *[Transform(regs[i], reg(i, v)) for i, v in enumerate(vals)]], 1.0),
            "one register may be lucky",
            (lambda: [Transform(regs[6], reg(6, 7, RED_M))], 0.6),
            "Redis takes",
            (lambda: [FadeIn(form, shift=0.1 * UP)], 0.8),
            "which damps",
            (lambda: [regs[6].animate.set_opacity(0.4)], 0.7),
            "and scales",
            (lambda: [*[glow(r[0], GOLD_M, 1.06) for r in regs]], 0.9),
        ])

        rng = np.random.default_rng(7)
        grid = np.clip(rng.geometric(0.5, size=(128, 128)), 1, 12).astype(float)
        img = (40 + 215 * (grid - 1) / 11).astype(np.uint8)
        rgb = np.stack([img * 0.97, img * 0.84, img * 0.44], axis=-1).astype(np.uint8)
        pic = ImageMobject(rgb).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        pic.height = 3.6
        pic.move_to([-3.6, -0.6, 0])
        plab = T("16,384 registers, 6 bits each", 20, GOLD_M).move_to([-3.6, 1.55, 0])
        facts = VGroup(T("16,384 × 6 bits = 12,288 bytes", 24), T("about 12 KB, for a thousand cards or a billion", 20, GREY_B),
                       T("standard error: 0.81%", 24, GOLD_M)).arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to([2.6, -0.6, 0])
        self.steps("Redis keeps 16,384 registers of 6 bits each, 12,288 bytes, "
                   "whether it has seen a thousand cards or a billion. The standard error is 0.81 percent.", [
            (lambda: [FadeOut(VGroup(c1, b1, form, idx, rlab, *regs))], 0.8),
            (lambda: [FadeIn(pic), FadeIn(plab)], 1.0),
            "12,288 bytes",
            (lambda: [FadeIn(facts[0], shift=0.1 * UP)], 0.7),
            "whether it has",
            (lambda: [FadeIn(facts[1], shift=0.1 * UP)], 0.7),
            "The standard error",
            (lambda: [FadeIn(facts[2], shift=0.1 * UP)], 0.7),
        ])

        cmp1 = chip("a set of 100,000 card ids: 4.4 MB", RED_M, 20)
        cmp2 = chip("a HyperLogLog: 12 KB, within about 1%", GREEN_M, 20)
        cmp = VGroup(cmp1, cmp2).arrange(RIGHT, buff=0.5).move_to([0, -3.1, 0])
        self.steps("A HyperLogLog never stores a card. It keeps the longest runs of zeros, "
                   "and counts distinct cards in 12 kilobytes, within about 1 percent.", [
            (lambda: [FadeIn(cmp1, shift=0.1 * UP)], 0.7),
            "It keeps",
            (lambda: [Indicate(plab, color=GOLD_M)], 0.8),
            "and counts",
            (lambda: [FadeIn(cmp2, shift=0.1 * UP)], 0.7),
        ])
        self.wait(0.6)
