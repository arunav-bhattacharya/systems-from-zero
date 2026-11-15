from sfz import *

SXS = [-4.65, -1.55, 1.55, 4.65]      # shard centres
SY, SW, SH = -0.35, 2.7, 1.7
BAR0, BARH, BARW = -3.3, 1.6, 1.3     # write-count bars under the shards, full height = 10,000
RTR = np.array([0, 2.2, 0])
CHIP_Y = 3.2
TOP_Y = 3.25
RANGES = ["pay-00000 to 04999", "pay-05000 to 09999", "pay-10000 to 14999", "pay-15000 and up"]
# md5 of the id, low 8 bytes, mod 4: what this scene's hash function gives
HASHED = {"pay-20000": 0, "pay-20001": 2, "pay-20002": 1}
EVEN = [2499, 2530, 2530, 2441]       # the next 10,000 ids, pay-20000 to pay-29999


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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


def shard(i, color=WHITE):
    x = SXS[i]
    r = RoundedRectangle(corner_radius=0.14, width=SW, height=SH, stroke_color=color, stroke_width=3)
    r.set_fill(BLACK if color == WHITE else fillc(color), 1).move_to([x, SY, 0])
    return VGroup(r, T(f"shard {i}", 24).move_to([x, SY + 0.5, 0]))


def key_lab(i, s, color=GREY_B):
    return M(s, 16, color).move_to([SXS[i], SY - 0.02, 0])


def link(i):
    return Line(RTR + 0.36 * DOWN, [SXS[i], SY + SH / 2, 0], stroke_width=2, color=GREY_D)


class RangeVsHash(Base):
    """shard-01, sections 1 and 2: payment ids over four shards. Key ranges keep pay-12000..12050 on one shard (one
    shard per range scan), but new ids pay-20000 and up all land on shard 3: 10,000 of 10,000 writes. Hash mod 4 spreads
    them 2,499 / 2,530 / 2,530 / 2,441, and the same range scan has rows on all four shards, so it asks all four."""

    def construct(self):
        self.title_card("Range or hash", "how a key picks its shard, and what each choice costs")

        sh = [shard(i) for i in range(4)]
        rtr = box("router", WHITE, w=2.2, h=0.72, size=24).move_to(RTR)
        links = VGroup(*[link(i) for i in range(4)])
        cnt = [ValueTracker(0) for _ in range(4)]
        writes = [always_redraw(lambda i=i: T(f"new writes: {int(round(cnt[i].get_value())):,}", 18, GREY_B)
                                .move_to([SXS[i], SY - 0.52, 0])) for i in range(4)]

        def bar(i):
            def make():
                h = max(cnt[i].get_value() / 10000 * BARH, 0.001)
                c = RED_M if (cnt[i].get_value() > 6000) else BLUE_M
                return Rectangle(width=BARW, height=h, stroke_width=0).set_fill(c, 0.75).move_to([SXS[i], BAR0 + h / 2, 0])
            return always_redraw(make)
        bars = [bar(i) for i in range(4)]
        base = Line([-6.3, BAR0, 0], [6.3, BAR0, 0], stroke_width=2, color=GREY_B)
        self.steps("A payments table has grown too big for one machine, so it's split across four shards. "
                   "Each payment's id decides which shard holds it. How should the ids be split?", [
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.1 * UP) for s in sh], lag_ratio=0.15)], 1.2),
            "Each payment's id",
            (lambda: [FadeIn(rtr), LaggedStart(*[Create(l) for l in links], lag_ratio=0.1)], 0.9),
            "How should",
            (lambda: [*[glow(s[0], GOLD_M) for s in sh]], 0.9),
        ])

        rule = left_at(T("split by key range", 24, WHITE), -6.6, TOP_Y)
        kl = [key_lab(i, RANGES[i]) for i in range(4)]
        bnd = left_at(M("boundaries: 05000, 10000, 15000", 17, GREY_B), 1.4, RTR[1])
        self.steps("The simplest way is by range. Shard 0 holds ids 0 to 4,999, shard 1 the next five thousand, "
                   "and so on. The router keeps the boundaries and finds where an id falls.", [
            (lambda: [FadeIn(rule, shift=0.1 * DOWN)], 0.6),
            "Shard 0 holds",
            (lambda: [LaggedStart(*[FadeIn(k) for k in kl], lag_ratio=0.35)], 1.6),
            "The router keeps",
            (lambda: [FadeIn(bnd, shift=0.1 * LEFT)], 0.7),
        ])

        q = chip("scan pay-12000 to pay-12050", GOLD_M, 18, mono=True).move_to([0, CHIP_Y, 0])
        ask1 = right_at(T("asks 1 shard", 22, GOLD_M), 6.6, TOP_Y)
        self.steps("Neighbours stay together. A scan from payment 12,000 to 12,050 goes to shard 2 alone, "
                   "which reads those rows in order.", [
            (lambda: [FadeIn(q, shift=0.1 * DOWN)], 0.6),
            "goes to shard 2",
            (lambda: [links[2].animate.set_stroke(GOLD_M, 4)], 0.4),
            (lambda: [travel(links[2], GOLD_M, 0.7)], 0.7),
            (lambda: [sh[2][0].animate.set_stroke(GOLD_M), kl[2].animate.set_color(GOLD_M), FadeIn(ask1)], 0.6),
            "which reads",
            (lambda: [glow(sh[2][0], GOLD_M)], 0.9),
        ])

        def payment(k, i, rt=1.2):
            c = chip(k, BLUE_M, 18, mono=True).move_to([0, CHIP_Y, 0])
            return Succession(FadeIn(c, shift=0.15 * DOWN, run_time=0.3),
                              c.animate(run_time=0.3).move_to(rtr).scale(0.4).set_opacity(0),
                              travel(links[i], BLUE_M, rt - 0.6))

        self.steps("But ids only grow. Each new payment gets a bigger id than the last: "
                   "20,000, then 20,001, then 20,002.", [
            (lambda: [FadeOut(q), FadeOut(ask1), links[2].animate.set_stroke(GREY_D, 2),
                      sh[2][0].animate.set_stroke(WHITE), kl[2].animate.set_color(GREY_B)], 0.6),
            (lambda: [*[FadeIn(w) for w in writes], Create(base)], 0.6),
            "20,000",
            (lambda: [payment("pay-20000", 3), cnt[3].animate.set_value(1)], 1.2),
            (lambda: [payment("pay-20001", 3), cnt[3].animate.set_value(2)], 1.2),
            (lambda: [payment("pay-20002", 3), cnt[3].animate.set_value(3)], 1.2),
        ])

        hot = chip("hot spot: one shard takes every write", RED_M, 18).move_to([0, -2.2, 0])
        self.steps("Every one is past the last boundary, so every one lands on shard 3. Of the next 10,000 writes, "
                   "shard 3 takes all 10,000, and the other three take none.", [
            (lambda: [kl[3].animate.set_color(RED_M), glow(sh[3][0], RED_M)], 0.8),
            "Of the next",
            (lambda: [*[FadeIn(b) for b in bars]], 0.2),
            (lambda: [cnt[3].animate(rate_func=linear).set_value(10000),
                      LaggedStart(*[travel(links[3], BLUE_M, 0.5) for _ in range(14)], lag_ratio=0.25)], 2.6),
            (lambda: [sh[3][0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1)], 0.5),
        ])

        self.steps("That's a hot spot. And splitting shard 3 doesn't help: its upper half becomes the new last shard, "
                   "and takes every new write.", [
            (lambda: [FadeIn(hot, shift=0.1 * DOWN)], 0.7),
            "And splitting",
            (lambda: [glow(sh[3][0], RED_M, 1.06)], 1.0),
        ])

        # ---- hash -------------------------------------------------------------------------------------------------
        rule2 = left_at(T("split by hash", 24, WHITE), -6.6, TOP_Y)
        hfn = left_at(M("shard = hash(id) mod 4", 17, GREY_B), 1.4, RTR[1])
        hl = [key_lab(i, f"hash mod 4 = {i}") for i in range(4)]
        self.steps("Hashing goes the other way. The router turns each id into a big number that looks random, "
                   "and takes that number mod 4.", [
            (lambda: [FadeOut(hot), *[c.animate.set_value(0) for c in cnt], sh[3][0].animate.set_stroke(WHITE).set_fill(BLACK, 1),
                      Transform(rule, rule2)], 0.8),
            "The router turns",
            (lambda: [Transform(bnd, hfn), *[Transform(kl[i], hl[i]) for i in range(4)]], 0.9),
            (lambda: [glow(rtr[0], GOLD_M, 1.05)], 0.8),
        ])

        self.steps("Payment 20,000 lands on shard 0, 20,001 on shard 2, and 20,002 on shard 1. "
                   "Neighbours end up far apart.", [
            (lambda: [payment("pay-20000", 0), cnt[0].animate.set_value(1)], 1.2),
            "20,001",
            (lambda: [payment("pay-20001", 2), cnt[2].animate.set_value(1)], 1.2),
            "and 20,002",
            (lambda: [payment("pay-20002", 1), cnt[1].animate.set_value(1)], 1.2),
        ])

        even = chip("even: about 2,500 each", BLUE_M, 18).move_to([0, -2.2, 0])
        self.steps("Of the next 10,000 writes, each shard takes about 2,500. The load is even.", [
            (lambda: [*[cnt[i].animate(rate_func=linear).set_value(EVEN[i]) for i in range(4)],
                      LaggedStart(*[travel(links[j % 4], BLUE_M, 0.5) for j in (0, 2, 1, 3, 2, 0, 3, 1, 0, 1, 2, 3, 1, 0)],
                                  lag_ratio=0.25)], 2.6),
            "The load is even",
            (lambda: [FadeIn(even, shift=0.1 * DOWN)], 0.6),
        ])

        ask4 = right_at(T("asks all 4 shards", 22, GOLD_M), 6.6, TOP_Y)
        self.steps("But the range scan breaks. Payments 12,000 to 12,050 now sit on every shard, and the router can't "
                   "tell which shards to skip, so it asks all four.", [
            (lambda: [FadeOut(even), FadeIn(q, shift=0.1 * DOWN)], 0.6),
            "now sit on",
            (lambda: [*[glow(s[0], GOLD_M) for s in sh]], 0.9),
            "so it asks",
            (lambda: [*[l.animate.set_stroke(GOLD_M, 4) for l in links], FadeIn(ask4)], 0.5),
            (lambda: [*[travel(l, GOLD_M, 0.7) for l in links]], 0.7),
        ])

        self.steps("With ranges, that scan asked one shard. With a hash, it asks every shard, "
                   "and waits for the slowest one.", [
            (lambda: [Transform(ask4, right_at(T("range: 1 shard. hash: 4 shards", 22, GOLD_M), 6.6, TOP_Y))], 0.8),
            "and waits",
            (lambda: [*[travel(Line(l.get_end(), l.get_start()), GOLD_M, 0.6) for l in links[:3]]], 0.6),
            (lambda: [travel(Line(links[3].get_end(), links[3].get_start()), RED_M, 1.4)], 1.4),
        ])

        self.steps("So choose by the query that must be cheap. Ranges keep neighbours together, but pile new keys on one "
                   "shard. A hash spreads the writes, but scatters every range.", [
            (lambda: [*[l.animate.set_stroke(GREY_D, 2) for l in links], FadeOut(q)], 0.6),
            "Ranges keep",
            (lambda: [glow(sh[2][0], GOLD_M)], 0.9),
            "A hash spreads",
            (lambda: [*[b.animate(rate_func=there_and_back).set_opacity(1) for b in bars]], 0.9),
        ])
        self.wait(0.6)
