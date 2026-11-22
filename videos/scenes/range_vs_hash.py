from sfz import *

# times and ids said the way people read them
SAY.insert(0, (r"\b14:25\b", "two twenty five"))
SAY.insert(0, (r"\b14:00\b", "two o'clock"))
SAY.insert(0, (r"\b14:05\b", "two oh five"))
SAY.insert(0, (r"\bM-0042\b", "M zero zero four two"))
SAY.insert(0, (r"\bshop#time\b", "shop, then time"))
# longest first: inserted last, so it runs before the 14:00 rule
SAY.insert(0, (r"\b14:00:00\.005\b", "two p m and five thousandths of a second"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
AX_Y, AX_X0, AX_X1 = 2.25, -6.1, 6.1      # the sorted line of keys
X4 = [-4.6, -1.53, 1.53, 4.6]             # four shards
W4 = 2.7
X5 = [-5.35, -2.67, 0.0, 2.67, 5.35]      # five, after the split
W5 = 2.35
SY, SH = -0.25, 2.9
S_TOP, S_BOT = SY + SH / 2, SY - SH / 2
CNT_Y = S_BOT - 0.38
KEY_Y = 3.3
CAP_Y, BAR_Y = -3.3, -2.75


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

    def steps(self, text, items, after=0.3):
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays;
        a number waits that long; a string waits until about where that phrase is spoken."""
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


# ---- the pieces ----
def shard(x, w, name, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=SH, stroke_color=color, stroke_width=3).set_fill(BLACK, 1).move_to([x, SY, 0])
    return VGroup(r, T(name, 24).move_to([x, S_TOP - 0.35, 0]))


def fill_bar(x, w, frac, color=GOLD_M):
    """How full of new rows a shard is (frac of the box's usable height)."""
    h = max(0.001, (SH - 0.85) * frac)
    return Rectangle(width=w - 0.5, height=h, stroke_width=0).set_fill(color, 0.75).move_to([x, S_BOT + 0.2 + h / 2, 0])


def seg_bounds(xs, w):
    """Where each shard's stretch of the key line starts and ends (the line is cut where the shards meet)."""
    edges = [AX_X0] + [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)] + [AX_X1]
    return edges


def axis(xs, w):
    line = Line([AX_X0, AX_Y, 0], [AX_X1, AX_Y, 0], stroke_width=3, color=GREY_B)
    ticks = VGroup(*[Line([e, AX_Y - 0.16, 0], [e, AX_Y + 0.16, 0], stroke_width=3, color=GREY_B) for e in seg_bounds(xs, w)[1:-1]])
    guides = VGroup(*[DashedLine([x, AX_Y - 0.2, 0], [x, S_TOP + 0.1, 0], dash_length=0.08, stroke_width=1.5, color=GREY_D) for x in xs])
    return VGroup(line, ticks, guides)


def rain(xs, frac_range=None, n=14, color=GOLD_M, seed=1):
    """New rows falling from the key line into the shards: one dot per row, each into the shard under it."""
    rng = np.random.default_rng(seed)
    anims = []
    for k in range(n):
        if frac_range is None:
            x = rng.uniform(AX_X0 + 0.3, AX_X1 - 0.3)
        else:
            x = rng.uniform(*frac_range)
        d = Dot(radius=0.07, color=color).move_to([x, AX_Y, 0])
        anims.append(Succession(FadeIn(d, run_time=0.05), d.animate(run_time=0.6, rate_func=rush_into).move_to([x, S_BOT + 0.4, 0]),
                                FadeOut(d, run_time=0.1)))
    return LaggedStart(*anims, lag_ratio=0.18)


class RangeVsHash(Base):
    """shard-01, section 1. One machine can't keep up, and copies don't help, so cut the payments into shards. The parcel
    depot sorts by postcode: key ranges. Key = time: every afternoon payment lands on shard 3 (10,000 of 10,000).
    Splitting at 14:25 makes shard 4 the new last range. Shop first: new payments spread over all four, one shop's day
    stays together, but "14:00 to 14:05" asks every shard. The rule, a guardrail, and a check about order numbers."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_key(self, s, color=WHITE):
        new = VGroup(T("key:", 24, GREY_B), M(s, 24, color)).arrange(RIGHT, buff=0.25).move_to([0, KEY_Y, 0])
        old, self.keym = self.keym, new
        return [swap(old, new)]

    def set_ends(self, left, right):
        new = VGroup(T(left, 20, GREY_B).move_to([AX_X0 + 0.9, AX_Y + 0.38, 0]), T(right, 20, GREY_B).move_to([AX_X1 - 0.9, AX_Y + 0.38, 0]))
        old, self.ends = self.ends, new
        return [swap(old, new)]

    def set_cnt(self, i, s, color=WHITE):
        new = M(s, 24, color).move_to([self.xs[i], CNT_Y, 0])
        old, self.cnt[i] = self.cnt[i], new
        return [swap(old, new)]

    def clear_cnt(self):
        olds = [c for c in self.cnt if c is not None]
        self.cnt = [None] * len(self.xs)
        return [FadeOut(c) for c in olds]

    def set_fill(self, i, frac, color=GOLD_M):
        new = fill_bar(self.xs[i], self.w, frac, color)
        old, self.fills[i] = self.fills[i], new
        if old is None:
            return [GrowFromEdge(new, DOWN)]
        return [FadeOut(old), GrowFromEdge(new, DOWN)]

    def clear_fills(self):
        olds = [f for f in self.fills if f is not None]
        self.fills = [None] * len(self.xs)
        return [FadeOut(f) for f in olds]

    def construct(self):
        self.capm = self.keym = self.ends = None
        self.xs, self.w = X4, W4
        self.cnt = [None] * 4
        self.fills = [None] * 4
        self.title_card("Where do the new payments go?", "cutting data into key ranges, and the shard that does all the work")

        # ---------------- scene 1: one machine, stuck ----------------
        one = RoundedRectangle(corner_radius=0.14, width=4.2, height=2.2, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to([0, 0.3, 0])
        one_t = VGroup(T("one database machine", 26), T("every card payment", 22, GREY_B)).arrange(DOWN, buff=0.15).move_to(one)
        one.set_z_index(2)
        one_t.set_z_index(3)
        need = VGroup(T("arriving", 20, GREY_B), M("25,000 a second", 26, RED_M)).arrange(DOWN, buff=0.12).move_to([-4.7, 0.3, 0])
        disk = VGroup(T("disk", 20, GREY_B), M("3 TB of 4 TB", 26, WHITE), M("+40 GB a day", 22, RED_M)).arrange(DOWN, buff=0.12).move_to([4.9, 0.3, 0])
        self.steps("It's the busiest shopping day of the year. You tap your card at a café, and the reader thinks for four seconds before it beeps.", [
            (lambda: self.cap("the busiest shopping day of the year"), 0.5),
            "thinks for four",
            (lambda: [*self.cap("tap... four seconds... beep", WHITE)], 0.5),
        ])
        self.steps("Behind it, one database machine records the card payments of thousands of shops. "
                   "It can't store the 25,000 payments a second that are arriving. And its disk fills up by 40 GB a day.", [
            (lambda: [*self.uncap(), FadeIn(one), FadeIn(one_t)], 0.7),
            "It can't store",
            (lambda: [FadeIn(need, shift=0.2 * RIGHT)], 0.6),
            "its disk",
            (lambda: [FadeIn(disk, shift=0.2 * LEFT)], 0.6),
        ])
        copies = VGroup(*[one.copy().set_z_index(0).set_stroke(GREY_D).scale(0.9).shift(0.22 * k * (DOWN + RIGHT)) for k in (3, 2, 1)])
        self.steps("A copy won't help this time. Every copy stores every payment and writes every payment, so a fourth copy is one more "
                   "full disk that writes no faster. So we cut the payments into parts, one machine per part.", [
            "A copy",
            (lambda: [FadeIn(copies, shift=0.1 * DOWN)], 0.6),
            "one more full disk",
            (lambda: self.cap("a copy stores and writes everything again", RED_M), 0.5),
            "So we cut",
            (lambda: [FadeOut(VGroup(copies, need, disk, one, one_t)), *self.cap("cut the payments into parts, one machine per part", WHITE)], 0.7),
        ])
        bays = [shard(X4[i], W4, f"bay {i}") for i in range(4)]
        self.steps("Each part is called a shard. Every payment lives in exactly one. The question is: which one?", [
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in bays], lag_ratio=0.2)], 0.9),
            "which one",
            (lambda: self.cap("which shard does a payment go to?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 2: the depot ----------------
        ax = axis(X4, W4)
        self.steps("Picture a parcel depot with four bays and a van for each. It sorts by postcode. Bay 0 takes the postcodes from the "
                   "start of the list up to one boundary, bay 1 takes the next stretch, and so on.", [
            (lambda: [*self.uncap()], 0.3),
            "sorts by postcode",
            (lambda: [Create(ax[0]), *self.set_ends("first postcode", "last postcode")], 0.8),
            "up to one boundary",
            (lambda: [Create(ax[1][0]), Create(ax[2][0])], 0.5),
            "the next stretch",
            (lambda: [Create(ax[1][1]), Create(ax[2][1])], 0.5),
            "and so on",
            (lambda: [Create(ax[1][2]), Create(ax[2][2]), Create(ax[2][3])], 0.5),
        ])
        street = Rectangle(width=0.5, height=0.36, stroke_width=0).set_fill(TEAL_M, 0.5).move_to([-2.3, AX_Y, 0])
        self.steps("A driver who delivers to one street finds all its parcels in one bay, because neighbouring postcodes sit together.", [
            "one street",
            (lambda: [FadeIn(street)], 0.5),
            (lambda: [rain(X4, (-2.5, -2.1), n=6, color=TEAL_M, seed=3)], 1.4),
            "in one bay",
            (lambda: [glow(bays[1][0], TEAL_M, 1.03)], 0.7),
        ])
        names = [shard(X4[i], W4, f"shard {i}") for i in range(4)]
        self.steps("Our store does the same with keys. A key is the value we look a row up by. Keep the keys in sorted order, "
                   "and give each shard one unbroken stretch of them. That's key-range sharding.", [
            (lambda: [FadeOut(street), *self.set_ends("smallest key", "largest key")], 0.5),
            "give each shard",
            (lambda: [*[Transform(bays[i][1], names[i][1]) for i in range(4)]], 0.7),
            "key-range sharding",
            (lambda: self.cap("key-range sharding: each shard holds one sorted stretch of keys", WHITE), 0.6),
        ])
        self.shards = bays

        # ---------------- scene 3: key = time ----------------
        self.steps("Now pick the key. Say it's the time the payment was made. The boundaries were cut from the morning's payments, "
                   "so the four shards are the same size.", [
            (lambda: [*self.uncap(), *self.set_key("the time of the payment"), *self.set_ends("earlier", "later")], 0.6),
            "the same size",
            (lambda: [*[a for i in range(4) for a in self.set_fill(i, 0.25, GREY_C)]], 0.7),
        ])
        self.steps("It's the afternoon. A payment arrives, made at 14:00:00.005. Which shard does it go to? Pause and guess.", [
            "A payment arrives",
            (lambda: [*self.set_key("14:00:00.005", GOLD_M)], 0.5),
            "Which shard",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Shard 3. It's later than every key already stored, so it sorts past the last boundary.", [
            (lambda: [*self.uncap(), rain(X4, (5.4, 5.8), n=1, color=GOLD_M, seed=2)], 0.8),
            (lambda: [glow(self.shards[3][0], GOLD_M, 1.03)], 0.7),
            "later than every",
            (lambda: self.cap("every new time is later than every stored time", GOLD_M), 0.5),
        ])
        self.steps("And the next payment? Same story. All afternoon, every new payment is the newest one. "
                   "Ten thousand new payments, and all ten thousand land on shard 3.", [
            (lambda: [rain(X4, (5.0, 5.9), n=18, color=GOLD_M, seed=4)], 2.6),
            "Ten thousand",
            (lambda: [*self.set_fill(3, 0.95, GOLD_M), *self.set_cnt(0, "0"), *self.set_cnt(1, "0"), *self.set_cnt(2, "0"),
                      *self.set_cnt(3, "10,000", GOLD_M)], 0.9),
        ])
        self.steps("Four machines, and one does all the writing. The cluster writes no faster than one machine. "
                   "A shard with far more work than the rest is called a hot spot.", [
            "one does all",
            (lambda: [self.shards[3][0].animate.set_stroke(RED_M), *[self.shards[i][0].animate.set_stroke(GREY_D) for i in range(3)]], 0.7),
            "no faster",
            (lambda: self.cap("four machines, writing at the speed of one", RED_M), 0.5),
            "called a hot spot",
            (lambda: self.cap("hot spot: one shard with far more work than the rest", RED_M), 0.6),
        ])

        # ---------------- scene 4: the obvious fix, split ----------------
        self.steps("The obvious fix: shard 3 is too busy, so split it in half. The store does exactly that, at its middle key, 14:25. "
                   "Let's see if it helps.", [
            "split it in half",
            (lambda: self.cap("split the busy shard?", WHITE), 0.5),
            "at its middle key",
            (lambda: [*self.clear_fills(), *self.clear_cnt()], 0.4),
        ])
        # four shards become five: shard 3 is cut at 14:25 and its upper half becomes shard 4
        new5 = [shard(X5[i], W5, f"shard {i}") for i in range(5)]
        ax5 = axis(X5, W5)
        t1425 = M("14:25", 20, GOLD_M).move_to([seg_bounds(X5, W5)[4], AX_Y - 0.42, 0])
        self.steps("Now there are five shards. Shard 4 holds everything from 14:25 on. And the next new payment goes... to shard 4. "
                   "And the next. And the next.", [
            (lambda: [*[Transform(self.shards[i], new5[i]) for i in range(4)], FadeIn(new5[4], shift=0.2 * LEFT), Transform(ax, ax5),
                      *self.cap("cut at 14:25: the upper half becomes shard 4")], 1.0),
            (lambda: [FadeIn(t1425)], 0.4),
            "to shard 4",
            (lambda: [rain(X5, (5.7, 6.0), n=4, color=GOLD_M, seed=5)], 0.9),
            "And the next. And",
            (lambda: [rain(X5, (5.3, 6.0), n=10, color=GOLD_M, seed=6), new5[4][0].animate.set_stroke(RED_M)], 1.6),
        ])
        self.shards.append(new5[4])
        self.xs, self.w = X5, W5
        self.cnt, self.fills = [None] * 5, [None] * 5
        self.steps("Splitting moved the hot spot to the end. It couldn't spread it. Well... we've built a brand new shard whose only job is the future.", [
            (lambda: [*self.set_fill(4, 0.8, GOLD_M), self.shards[3][0].animate.set_stroke(GREY_D)], 0.7),
            "moved the hot spot",
            (lambda: self.cap("splitting moves the hot spot to the end; it can't spread it", RED_M), 0.6),
        ], after=0.4)
        self.steps("Here the depot picture needs one change. Sort parcels by the date on the label, and every new parcel is today's, "
                   "so every one goes to the last bay.", [
            "by the date",
            (lambda: [glow(self.shards[4][0], RED_M, 1.03), *self.cap("a depot sorted by date: every new parcel, the last bay")], 0.8),
        ])
        self.steps("This one hides well in testing. Load a year of old payments in one go, and they spread nicely, because the "
                   "boundaries were cut to fit them. The trouble starts with live traffic, when every payment is the newest one.", [
            "Load a year",
            (lambda: [*self.clear_fills(), rain(X5, None, n=20, color=GREY_B, seed=7)], 1.8),
            (lambda: [*[a for i in range(5) for a in self.set_fill(i, 0.35, GREY_C)]], 0.6),
            "with live traffic",
            (lambda: [rain(X5, (5.4, 6.0), n=8, color=GOLD_M, seed=8), *self.cap("old data spreads; live traffic doesn't", GOLD_M)], 1.4),
        ])

        # ---------------- scene 5: put the shop first ----------------
        back4 = [shard(X4[i], W4, f"shard {i}") for i in range(4)]
        self.steps("The fix is to put something before the time. Make the key the shop's id, then the time, then the payment's number.", [
            (lambda: [*self.uncap(), *self.clear_fills(), FadeOut(t1425), FadeOut(self.shards[4]),
                      *[Transform(self.shards[i], back4[i]) for i in range(4)], Transform(ax, axis(X4, W4))], 1.0),
            "Make the key",
            (lambda: [*self.set_key("M-0310#14:00:00.005#pay-20001", WHITE), *self.set_ends("first shop", "last shop")], 0.7),
        ])
        self.shards = self.shards[:4]
        self.xs, self.w = X4, W4
        self.cnt, self.fills = [None] * 4, [None] * 4
        self.steps("Now the boundaries are shop ids. And the afternoon's payments come from all 500 shops, so they land in all the "
                   "shops' ranges, on every shard.", [
            "the boundaries are shop ids",
            (lambda: [*[self.shards[i][0].animate.set_stroke(WHITE) for i in range(4)]], 0.5),
            "come from all 500",
            (lambda: [rain(X4, None, n=26, color=GOLD_M, seed=9)], 2.4),
            "on every shard",
            (lambda: [*[a for i in range(4) for a in self.set_fill(i, 0.55, GOLD_M)], *self.cap("new payments spread over all four", GREEN_M)], 0.8),
        ])
        band = Rectangle(width=0.35, height=0.36, stroke_width=0).set_fill(TEAL_M, 0.6).move_to([-5.4, AX_Y, 0])
        band_l = M("M-0042", 20, TEAL_M).next_to(band, DOWN, buff=0.12)
        self.steps("And one shop's payments still sit together, sorted by time. All of shop M-0042's day is one unbroken run, on one shard.", [
            "one shop's",
            (lambda: [FadeIn(band), FadeIn(band_l)], 0.6),
            "on one shard",
            (lambda: [glow(self.shards[0][0], TEAL_M, 1.03), *self.cap("one shop's day: one run, one shard", TEAL_M)], 0.8),
        ])

        # ---------------- scene 6: the name, the bill, the rule ----------------
        slivers = VGroup(*[Rectangle(width=0.12, height=0.36, stroke_width=0).set_fill(PURPLE_M, 0.9).move_to([x, AX_Y, 0])
                           for x in np.linspace(AX_X0 + 0.5, AX_X1 - 0.5, 9)])
        self.steps("But there's a bill, and it arrives on the other question. Every payment from 14:00 to 14:05, across all shops. "
                   "With the time first, that sat on one shard.", [
            (lambda: [FadeOut(band), FadeOut(band_l), *self.uncap()], 0.4),
            "Every payment from",
            (lambda: self.cap("question: every payment from 14:00 to 14:05, all shops", PURPLE_M), 0.6),
            "With the time first",
            (lambda: [glow(self.shards[3][0], PURPLE_M, 1.03)], 0.7),
        ])
        self.steps("With the shop first, those payments are a small run inside every shop's range. So the question has to ask all four shards.", [
            "a small run",
            (lambda: [LaggedStart(*[FadeIn(s, scale=0.5) for s in slivers], lag_ratio=0.1)], 1.0),
            "ask all four",
            (lambda: [*[glow(s[0], PURPLE_M, 1.03) for s in self.shards], *self.cap("now it asks all four shards", PURPLE_M)], 0.8),
        ])
        self.steps("So neither key is better. Each one makes a different question cheap. Here's the rule: whatever comes first in the key "
                   "decides where new rows land. Choose it from the question that must be cheap.", [
            (lambda: [FadeOut(slivers), *self.cap("neither key is better", WHITE)], 0.5),
            "Here's the rule",
            (lambda: self.cap("what comes first in the key decides where new rows land", YELLOW_M), 0.6),
            "Choose it",
            (lambda: self.cap("choose it from the question that must be cheap", YELLOW_M), 0.6),
        ])
        self.steps("One honest limit. The shop-first key spreads new payments only because they happen to come from many shops. "
                   "Next, we'll spread keys whatever they look like, with a hash.", [
            "only because",
            (lambda: self.cap("it spreads only because payments come from many shops"), 0.6),
            "with a hash",
            (lambda: self.cap("next: spreading any key, with a hash"), 0.5),
        ], after=0.5)

        # ---------------- scene 7: moral and a check ----------------
        self.steps("So, where do the new payments go? With key ranges, wherever the start of the key sends them. Time first, "
                   "and that's always the last shard.", [
            (lambda: [*self.clear_fills(), *self.set_key("the time of the payment"), *self.set_ends("earlier", "later"),
                      *self.cap("where do the new payments go?", WHITE)], 0.7),
            "Time first",
            (lambda: [rain(X4, (5.2, 5.9), n=8, color=GOLD_M, seed=10), *self.set_fill(3, 0.9, GOLD_M)], 1.4),
            (lambda: [glow(self.shards[3][0], RED_M, 1.03)], 0.6),
        ], after=0.4)
        self.steps("One quick check. A shop keeps its orders in ranges of the order number, which counts up by one for each new order. "
                   "Where do today's orders land? Pause and think.", [
            (lambda: [*self.uncap(), *self.clear_fills(), *self.set_key("order number: 1, 2, 3...", WHITE), *self.set_ends("smallest number", "largest number")], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("All on the last shard. A number that only grows is a time in disguise. Put something else first.", [
            (lambda: [*self.uncap(), rain(X4, (5.3, 5.9), n=10, color=GOLD_M, seed=11)], 1.4),
            (lambda: [*self.set_fill(3, 0.9, GOLD_M), glow(self.shards[3][0], RED_M, 1.03)], 0.6),
            "a time in disguise",
            (lambda: self.cap("a number that only grows is a time in disguise", RED_M), 0.6),
        ], after=0.3)
        self.play(*self.cap("the start of the key decides where new rows land", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
