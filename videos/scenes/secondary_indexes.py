from sfz import *

SAY.insert(0, (r"\bcard-242\b", "card 242"))
SAY.insert(0, (r"\bpay-1234\b", "pay 1234"))
SAY.insert(0, (r"\bM-0042\b", "M zero zero four two"))
SAY.insert(0, (r"\bMongoDB\b", "mongo D B"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CHK_Y = 3.15                                  # the fraud check
SX = [-4.95, -1.65, 1.65, 4.95]
SY = [1.35, -0.75]
SW, SH = 3.0, 1.75
MID_Y, BAR_Y, CAP_Y = -2.2, -2.75, -3.27
GOLD = [1, 2, 0, 1, 3, 1, 0, 2]               # card-242's payments on each of 8 shards (the lesson's demo)
PER = 5                                       # tiles drawn per shard


def sc(k):
    return np.array([SX[k % 4], SY[k // 4], 0])


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

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0]))

    def mid(self, mob):
        return self.put("mid", fit(mob, 12.8).move_to([0, MID_Y, 0]))

    def put(self, key, mob, d=UP):
        old = self.slots.get(key)
        self.slots[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.slots.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(w, h, color, at, a=0.14):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(
        fillc(color, a), 1).move_to(at)


def tile(gold):
    c = GOLD_M if gold else GREY_C
    return Square(0.3, stroke_color=c, stroke_width=2).set_fill(fillc(c, 0.55 if gold else 0.35), 1).set_z_index(3)


def tile_at(k, j):
    return sc(k) + np.array([-1.05 + 0.42 * j, 0.0, 0])


def shard_box(k):
    c = sc(k)
    return VGroup(rbox(SW, SH, BLUE_M, c), T(f"shard {k}", 20).move_to(c + np.array([-0.85, 0.57, 0])))


def ix_line(k, s=None, color=TEAL_M):
    n = GOLD[k]
    s = s or f"index: card-242 → {n}"
    return M(s, 16, color).move_to(sc(k) + np.array([0, -0.55, 0]))


def dot_go(a, b, color=YELLOW_M, rt=0.8):
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), d.animate(run_time=rt, rate_func=smooth).move_to(b), FadeOut(d, run_time=0.1))


class SecondaryIndexes(Base):
    """shard-04, section 0. A thief tests a stolen card; the fraud check counts the card's payments in the last minute.
    One computer: an index finds card 242's ten payments in one step. Split by payment number over 8 shards, the ten
    land on 6 of them. A secondary index; the library with eight branches; each shard indexes its own payments (local
    index): writes stay on one shard, but a search by card asks all 8 (scatter-gather), even shards 2 and 6 that hold
    none. 2,000 checks a second cost 16,000 shard requests, and more shards mean more asking. Uniqueness can't be
    enforced; a question that names the partition key asks one shard. Moral, and a check (32 shards: 64,000)."""

    def construct(self):
        self.slots = {}
        self.title_card("Why did more computers make the check slower?", "a local index, and a search that asks every shard")

        # ---------------- scene 1: a thief and a guard ----------------
        pays = VGroup(*[chip("card-242  1.00", GOLD_M, 20, mono=True) for _ in range(4)]).arrange(DOWN, buff=0.18).move_to([0, 0.6, 0])
        self.steps("Picture a thief with a stolen card number. A program tests it with small payments at online shops, one every 50 milliseconds.", [
            "A program",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.2 * DOWN) for p in pays], lag_ratio=0.4)], 1.6),
            "one every",
            (lambda: self.cap("one test payment every 50 ms", GOLD_M), 0.5),
        ])
        self.steps("A very busy, very small shopper.", [
            (lambda: [Wiggle(pays, scale_value=1.04, rotation_angle=0.02 * TAU)], 0.9),
        ], after=0.4)
        chk = VGroup(rbox(7.2, 0.62, YELLOW_M, [0, CHK_Y, 0]), T("fraud check: card-242, last minute", 22, YELLOW_M).move_to([0, CHK_Y, 0]))
        self.steps("The payments app has a guard for this. Before it says yes, it counts the card's payments in the last minute, "
                   "and refuses when there are more than five.", [
            (lambda: [FadeIn(chk, shift=0.1 * DOWN), *self.drop("cap")], 0.7),
            "and refuses",
            (lambda: [*self.cap("more than 5 in the last minute?  refuse", YELLOW_M), glow(chk[0], YELLOW_M, 1.03)], 0.7),
        ])
        one = T("1 computer: about 1 ms", 26, GREEN_M).move_to([-3.4, -1.6, 0])
        eight = T("8 computers: slower?", 26, RED_M).move_to([3.4, -1.6, 0])
        self.steps("On one computer, that count takes a millisecond. But the payments now live on 8 computers. "
                   "The team added computers to go faster, and the check got slower. Why?", [
            (lambda: [FadeIn(one, shift=0.1 * UP)], 0.5),
            "But the payments",
            (lambda: [FadeIn(eight, shift=0.1 * UP)], 0.5),
            "Why?",
            (lambda: self.cap("why?", YELLOW_M, 30), 0.4),
        ], after=0.6)

        # ---------------- scene 2: one computer, one index ----------------
        order = []                                       # (shard, gold) for every tile, shard by shard
        for k in range(8):
            order += [(k, True)] * GOLD[k] + [(k, False)] * (PER - GOLD[k])
        rng = np.random.default_rng(5)
        perm = rng.permutation(len(order))
        tiles = [tile(g) for k, g in order]
        big = VGroup(rbox(6.4, 3.0, BLUE_M, [0, 0.4, 0]), T("one computer", 22).move_to([-2.0, 1.6, 0]))
        for pos, i in enumerate(perm):
            r, c = divmod(pos, 10)
            tiles[i].move_to([-1.89 + 0.42 * c, 1.0 - 0.42 * r, 0])
        big_ix = M("index: card-242 → 10 rows", 18, TEAL_M).move_to([0, -0.75, 0])
        self.steps("Start with one computer. The payments sit in a table, rows of records, one row per payment.", [
            (lambda: [FadeOut(pays), FadeOut(one), FadeOut(eight), *self.drop("cap")], 0.6),
            (lambda: [FadeIn(big[0]), FadeIn(big[1])], 0.6),
            "The payments sit",
            (lambda: [LaggedStart(*[FadeIn(t) for t in tiles], lag_ratio=0.02)], 1.2),
        ])
        self.steps("An index is a lookup from a value to where its rows are, like the index at the back of a book.", [
            "An index",
            (lambda: [FadeIn(big_ix, shift=0.1 * UP)], 0.6),
            "like the index",
            (lambda: [Indicate(big_ix, color=TEAL_M, scale_factor=1.08)], 0.8),
        ])
        golds = [t for t, (k, g) in zip(tiles, order) if g]
        self.steps("With an index on the card, the check finds card 242's ten payments in one step, instead of reading every row.", [
            (lambda: [dot_go(chk.get_bottom(), big_ix.get_top())], 0.8),
            "card 242's ten",
            (lambda: [LaggedStart(*[t.animate(rate_func=there_and_back).scale(1.5) for t in golds], lag_ratio=0.06)], 1.2),
        ])
        shards = [shard_box(k) for k in range(8)]
        slot_j = {}
        cnt = [0] * 8
        for i, (k, g) in enumerate(order):
            slot_j[i] = cnt[k]
            cnt[k] += 1
        self.steps("Now split the table over 8 computers. Each piece, on its own computer, is a shard.", [
            (lambda: [FadeOut(big), FadeOut(big_ix)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(s) for s in shards], lag_ratio=0.06)], 0.9),
            (lambda: [*[tiles[i].animate.move_to(tile_at(k, slot_j[i])) for i, (k, g) in enumerate(order)]], 1.4),
        ])
        self.steps("A payment's shard comes from its payment number: hash it, divide by 8, keep the remainder. "
                   "The value that picks the shard is called the partition key.", [
            (lambda: self.mid(M("shard = hash(payment number) mod 8", 22, WHITE)), 0.6),
            "called the partition key",
            (lambda: self.cap("partition key: the value that picks the shard (here, the payment number)", WHITE), 0.6),
        ])
        lbl = M("pay-1234", 18, YELLOW_M).move_to([0, CHK_Y - 0.6, 0])
        self.steps("Find a payment by its number, and you ask exactly one shard.", [
            (lambda: [FadeIn(lbl)], 0.4),
            (lambda: [dot_go(chk.get_bottom(), shards[5][0].get_top()), FadeOut(lbl)], 0.9),
            (lambda: [glow(shards[5][0], GREEN_M, 1.03), *self.cap("by payment number: 1 shard", GREEN_M)], 0.8),
        ])

        # ---------------- scene 3: where does the card index live? ----------------
        self.steps("But the fraud check doesn't have a payment number. It has a card.", [
            (lambda: [glow(chk[0], YELLOW_M, 1.03), *self.cap("the check has a card, not a payment number", YELLOW_M)], 0.8),
        ])
        self.steps("An index on a column that isn't the partition key is called a secondary index. "
                   "And with shards, we have to decide where its entries live.", [
            "is called",
            (lambda: self.cap("secondary index: an index on something that isn't the partition key", WHITE), 0.6),
            "where its entries",
            (lambda: self.cap("where do its entries live?", YELLOW_M, 28), 0.5),
        ])
        self.steps("Picture a city library with eight branches. Each book sits at one branch, picked by its number, "
                   "and each branch keeps a catalogue of its own books only.", [
            (lambda: self.cap("a library with eight branches", WHITE, 28), 0.5),
            "Each book",
            (lambda: [LaggedStart(*[glow(s[0], BLUE_M, 1.03) for s in shards], lag_ratio=0.08)], 1.2),
            "a catalogue",
            (lambda: self.cap("each branch: a catalogue of its own books only", WHITE, 28), 0.5),
        ])
        self.steps("Adding a book is easy: the branch that gets it files the card. "
                   "But to find every book by one author, you phone all eight branches and wait for each librarian to look.", [
            "But to find",
            (lambda: self.cap("every book by one author: phone all eight branches", WHITE, 28), 0.5),
        ])
        ixs = [ix_line(k) for k in range(8)]
        self.steps("The simplest index for shards works the same way. The branch is a shard, a book is a payment, "
                   "and the branch's catalogue is that shard's index.", [
            "The branch is",
            (lambda: self.cap("branch  =  shard", WHITE, 28), 0.4),
            "a book is",
            (lambda: [*self.cap("book  =  payment", WHITE, 28),
                      LaggedStart(*[t.animate(rate_func=there_and_back).scale(1.4) for t in tiles], lag_ratio=0.01)], 0.8),
            "and the branch's",
            (lambda: [*self.cap("the branch's catalogue  =  that shard's index", WHITE, 28),
                      LaggedStart(*[FadeIn(x, shift=0.05 * UP) for x in ixs], lag_ratio=0.08)], 1.0),
        ])
        self.steps("Shard 4's index knows card 242's payments on shard 4, and nothing else. This is a local index.", [
            (lambda: [Indicate(ixs[4], color=TEAL_M, scale_factor=1.1)], 0.8),
            "This is a",
            (lambda: [*self.cap("local index: each shard indexes only its own payments", YELLOW_M, 28), *self.drop("mid")], 0.6),
        ])

        # ---------------- scene 4: writes stay simple ----------------
        nt = tile(False).move_to(sc(3) + np.array([0, 2.6, 0]))
        self.steps("Writes stay simple. A new payment and its index entry go to the same shard, together or not at all. "
                   "So the index is never behind its payments.", [
            "A new payment",
            (lambda: [FadeIn(nt)], 0.2),
            (lambda: [nt.animate.move_to(tile_at(3, 5))], 0.8),
            (lambda: [glow(shards[3][0], TEAL_M, 1.03), Indicate(ixs[3], color=TEAL_M, scale_factor=1.1),
                      *self.cap("payment + its index entry: one shard, all or nothing", TEAL_M)], 0.9),
        ])

        # ---------------- scene 5: pause and guess ----------------
        qm = T("?", 48, YELLOW_M).move_to([4.3, CHK_Y, 0]).set_z_index(8)
        self.steps("Now the read. Card 242 has ten payments. How many shards does the fraud check have to ask? Pause and guess.", [
            (lambda: [*self.drop("cap"), glow(chk[0], YELLOW_M, 1.03)], 0.6),
            "Card 242 has",
            (lambda: [LaggedStart(*[t.animate(rate_func=there_and_back).scale(1.5) for t in golds], lag_ratio=0.05)], 1.0),
            "How many",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ticks = [tick(GOLD[k] > 0 or True, 0.15).move_to(sc(k) + np.array([1.2, 0.57, 0])) for k in range(8)]

        def scatter():
            return [*[dot_go(chk.get_bottom(), shards[k][0].get_top(), YELLOW_M, 0.8) for k in range(8)]]

        def gather():
            return [*[dot_go(shards[k][0].get_top(), chk.get_bottom(), GREEN_M, 0.8) for k in range(8)]]

        self.steps("All eight. The ten payments sit on six shards. But shards 2 and 6 hold none, and they still get asked.", [
            (lambda: [FadeOut(qm), *self.drop("cap"), *scatter()], 0.9),
            (lambda: [*gather(), *[Create(t) for t in ticks], *self.mid(T("shards asked: 8", 26, YELLOW_M))], 0.9),
            "The ten payments",
            (lambda: [LaggedStart(*[t.animate(rate_func=there_and_back).scale(1.5) for t in golds], lag_ratio=0.05),
                      *self.mid(T("shards asked: 8.   card 242 found on: 6", 26, YELLOW_M))], 1.0),
            "But shards 2",
            (lambda: [glow(shards[2][0], RED_M, 1.04), glow(shards[6][0], RED_M, 1.04), Indicate(ixs[2], color=RED_M), Indicate(ixs[6], color=RED_M)], 1.0),
        ])
        self.steps("Could we skip them? Only if someone knew they were empty, and shard 4's index knows nothing about shard 2.", [
            "Only if",
            (lambda: [Indicate(ixs[4], color=TEAL_M, scale_factor=1.1)], 0.8),
            "nothing about",
            (lambda: [glow(shards[2][0], GREY_B, 1.04)], 0.8),
        ])
        self.steps("So the check asks every shard and merges the answers. That's called a scatter-gather read.", [
            (lambda: [*scatter()], 0.9),
            (lambda: [*gather()], 0.9),
            "That's called",
            (lambda: self.cap("scatter-gather: ask every shard, then merge the answers", YELLOW_M, 28), 0.6),
        ])
        nones = [ix_line(k, "index: card-242 → 0", GREY_B) for k in range(8)]
        self.steps("And a card with no payments at all? Still eight. Seven librarians say not here, and so does the eighth.", [
            (lambda: [*[FadeOut(x) for x in ixs], *[FadeIn(x) for x in nones], *[t.animate.set_opacity(0.15) for t in golds]], 0.7),
            "Still eight",
            (lambda: [*scatter()], 0.9),
            (lambda: [*gather()], 0.9),
            "Seven librarians",
            1.2,
            (lambda: [*[FadeOut(x) for x in nones], *[FadeIn(x) for x in ixs], *[t.animate.set_opacity(1) for t in golds]], 0.7),
        ], after=0.5)

        # ---------------- scene 6: more shards, more asking ----------------
        self.steps("Now the cost. At 2,000 checks a second, that's 16,000 shard requests a second on 8 shards.", [
            "At 2,000",
            (lambda: self.mid(T("2,000 checks a second  ×  8 shards  =  16,000 shard requests a second", 24, RED_M)), 0.6),
            (lambda: [*scatter()], 0.9),
        ])
        ninth = VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.12, width=3.3, height=0.62, stroke_color=GREY_B, stroke_width=2.5), num_dashes=40),
                       T("9th shard: +2,000 a second", 18, RED_M)).move_to([4.9, MID_Y, 0])
        ninth[1].move_to(ninth[0])
        self.steps("Add a ninth shard, and it gets all 2,000 checks a second too, just like the others. "
                   "So adding shards adds no capacity for this question.", [
            (lambda: [*self.put("mid", T("2,000 checks a second  ×  8 shards  =  16,000", 24, RED_M).move_to([-2.0, MID_Y, 0])), FadeIn(ninth, shift=0.1 * LEFT)], 0.7),
            "So adding",
            (lambda: self.cap("more shards: more asking, not less", RED_M, 28), 0.5),
        ])
        self.steps("That's the slower check from the start. Hiring more librarians doesn't help when every call rings every branch.", [
            (lambda: [glow(chk[0], RED_M, 1.03)], 0.8),
            "every call",
            (lambda: [*scatter()], 0.9),
        ], after=0.5)

        # ---------------- scene 7: two guardrails ----------------
        self.steps("A local index has another blind spot. It can't keep a value unique. "
                   "No shard sees the others' entries, so none can tell that a value is already used elsewhere.", [
            (lambda: [FadeOut(ninth), *self.drop("mid"), *self.cap("unique? a local index can't promise it", RED_M, 28)], 0.6),
            "No shard sees",
            (lambda: [LaggedStart(*[Indicate(x, color=RED_M, scale_factor=1.08) for x in ixs], lag_ratio=0.1)], 1.4),
        ])
        self.steps("MongoDB, a popular database that splits its data over shards, says so in its manual: "
                   "a unique index works only if it starts with the partition key.", [
            "says so",
            (lambda: self.cap("MongoDB's manual: a unique index must start with the partition key", WHITE), 0.6),
        ])
        lbl2 = M("card-242 at shop M-0042", 18, YELLOW_M).move_to([0, CHK_Y - 0.6, 0])
        self.steps("And none of this hurts when the question names the partition key. Split the payments by shop instead, "
                   "and card-242's payments at shop M-0042 go to that one shop's shard, and use the local index there.", [
            "Split the payments",
            (lambda: [*self.mid(M("shard = hash(shop) mod 8", 22, WHITE)), *self.drop("cap")], 0.6),
            "card-242's",
            (lambda: [FadeIn(lbl2)], 0.4),
            "go to that",
            (lambda: [dot_go(chk.get_bottom(), shards[6][0].get_top()), FadeOut(lbl2)], 0.9),
            (lambda: [glow(shards[6][0], GREEN_M, 1.03), *self.cap("the question names the shop: 1 shard", GREEN_M)], 0.8),
        ])
        self.steps("So: a local index is cheap when a question names the partition key, and costly when it doesn't.", [
            (lambda: [*self.drop("mid"), *self.cap("local index: cheap when the question names the partition key, costly when it doesn't", YELLOW_M, 26)], 0.7),
        ], after=0.6)

        # ---------------- scene 8: moral and a check ----------------
        self.steps("So the index works on 8 machines, but each machine only knows its own. "
                   "Ask a question without the partition key, and you ask everyone.", [
            (lambda: [LaggedStart(*[Indicate(x, color=TEAL_M, scale_factor=1.1) for x in ixs], lag_ratio=0.1)], 1.4),
            "Ask a question",
            (lambda: [*self.cap("no partition key in the question: ask every shard", YELLOW_M, 28), *scatter()], 0.9),
        ])
        self.steps("Asking eight shards costs eight times the work. It also costs time, in a way that surprises most people, and that's next.", [
            "It also costs time",
            (lambda: self.cap("it also costs time: next", GREY_B), 0.5),
        ], after=0.5)
        self.steps("One quick check. The app grows to 32 shards, with the same local index. "
                   "How many shard requests do 2,000 checks a second cost now? Pause and think.", [
            (lambda: self.cap("32 shards, local index: 2,000 checks a second cost how many shard requests?", WHITE), 0.6),
            "Pause and think",
            (lambda: self.mid(T("pause and think", 26, YELLOW_M)), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("64,000. Every check asks all 32.", [
            (lambda: [*self.mid(T("2,000  ×  32  =  64,000 shard requests a second", 26, RED_M)), *scatter()], 0.9),
            (lambda: self.cap("every check asks every shard", YELLOW_M, 28), 0.5),
        ], after=0.3)
        self.wait(2.0)
