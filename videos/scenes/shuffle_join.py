from sfz import *

# Kokoro runs "reduce task" together into "reduced task"; this spelling keeps the two words apart
SAY.insert(0, (r"\breduce task", "ree-duce task"))
SAY.insert(0, (r"\b1,000,500\b", "a million and five hundred"))
SAY.insert(0, (r"\bHashMap\b", "hash map"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
MX, FX, RX = -4.9, -1.2, 4.6              # map tasks, shuffle files / copies, reduce tasks
YS = [2.15, 1.0, -0.15, -1.3]             # rows 0..3
SHOP_Y = -2.45                            # the shops table (left) and the driver (right)
BW, BH = 2.8, 0.85
BLK = 0.42
PC = [BLUE_M, TEAL_M, PURPLE_M, GOLD_M]   # reduce task k's colour; shop 42 hashes to 3
GOLD_AT = [2, 5, 1, 4]                    # where shop 42's dot sits in each map task
HEAD_Y, CAP_Y, BAR_Y = 3.25, -3.3, -2.95
CNT = np.array([RX, HEAD_Y, 0])


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

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn, so it can sit inside a LaggedStart."""
    d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_opacity(0).set_z_index(6)
    line = Line(path.get_start(), path.get_end())
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def frame(x, y, color, w=BW, h=BH, fill=None):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    return r.set_fill(fill if fill is not None else fillc(color), opacity=1).move_to([x, y, 0])


def dots(x, y, gold, color=GREY_C, n=7):
    g = VGroup(*[Dot(radius=0.065, color=GOLD_M if j == gold else color) for j in range(n)]).arrange(RIGHT, buff=0.17)
    return g.move_to([x, y, 0])


def label(s, x, y, color=WHITE, size=22):
    return fit(T(s, size, color), BW - 0.3).move_to([x, y + 0.18, 0])


def status(s, x, y, color=GREY_B, size=19):
    return fit(T(s, size, color), BW - 0.35).move_to([x, y - 0.2, 0])


def shuffle_file(y):
    sq = VGroup()
    for k in range(4):
        r = Square(BLK, stroke_color=PC[k], stroke_width=2.5).set_fill(fillc(PC[k], 0.3), opacity=1)
        r.move_to([FX + (k - 1.5) * BLK, y, 0])
        sq.add(VGroup(r, M(str(k), 17).move_to(r)))
    return sq


def write_arrow(y):
    return Arrow([MX + BW / 2 + 0.06, y, 0], [FX - 2 * BLK - 0.06, y, 0], buff=0, stroke_width=2.5, color=GREY_B,
                 max_tip_length_to_length_ratio=0.25)


def fetch(y0, k, i, color=None):
    """From a shuffle file's right edge at height y0 to reduce task k's left edge."""
    s = [FX + 2 * BLK + 0.08, y0 + (1.5 - k) * 0.07, 0]
    e = [RX - BW / 2 - 0.06, YS[k] + (1.5 - i) * 0.08, 0]
    return Arrow(s, e, buff=0, stroke_width=2.5, color=color or PC[k], max_tip_length_to_length_ratio=0.045)


class ShuffleJoin(Base):
    """batch-07, section 4. The report that went from 6 to 25 minutes after joining a 500-row shops table. The post
    office: clerks, letters, a one page list of postcodes. Way one, shuffle both sides by hash(shop) mod 4 and
    sort-merge (1,000,500 rows, 4 stages, 9.4 MB). Way two, photocopy the list: broadcast hash join (0 payments moved,
    91 ms against 165 ms). The trap: after a filter Spark keeps its old size guess (over 10 MB), so the fix is a
    broadcast() hint. The guardrail (2 GB to 100 executors = 200 GB), the moral and a check (a 3 GB customers table)."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Move the letters, or copy the list?", "two ways Spark joins two tables")

        # ---------------- scene 1: the slow report ----------------
        rep = chip("report: 6 min", GREEN_M, 34).move_to([0, 1.3, 0])
        rep2 = chip("report: 25 min", RED_M, 34).move_to([0, 1.3, 0])
        code = M('payments.join(merchants, "merchant_id")', 26, TEAL_M).move_to([0, 0.1, 0])
        plus = T("one new line:", 22, GREY_B).next_to(code, UP, buff=0.22)
        tiny = chip("shops: 500 rows", GREEN_M, 26).move_to([0, -1.2, 0])
        qm = T("?", 64, YELLOW_M).move_to([2.6, 1.3, 0])
        self.steps("Picture the company that runs a café's card payments. Every hour, a report adds up what each shop took. "
                   "It takes about 6 minutes.", [
            "Every hour",
            (lambda: [FadeIn(rep, shift=0.1 * UP)], 0.6),
        ])
        self.steps("Then the owners want totals per kind of shop: cafés, bookshops, grocers. Only the shops table knows each "
                   "shop's kind, so a teammate adds one line that matches each payment with its shop.", [
            "a teammate adds",
            (lambda: [FadeIn(plus), FadeIn(code, shift=0.1 * DOWN)], 0.7),
        ])
        self.steps("The report now takes 25 minutes. And the shops table is tiny, just 500 rows. "
                   "So where did nineteen minutes go? Hold that question.", [
            (lambda: [FadeTransform(rep, rep2)], 0.7),
            "the shops table is tiny",
            (lambda: [FadeIn(tiny, shift=0.1 * UP)], 0.6),
            "So where",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
        ], after=0.3)
        self.stamp("report")

        # ---------------- scene 2: both rows in one task ----------------
        boxes = [frame(MX, y, WHITE, fill=BLACK) for y in YS]
        labs = [label(f"task {i}", MX, y) for i, y in enumerate(YS)]
        pays = [dots(MX, y - 0.2, GOLD_AT[i]) for i, y in enumerate(YS)]
        sbox = frame(MX, SHOP_Y, GREEN_M)
        slab = label("shops: 500 rows", MX, SHOP_Y, GREEN_M)
        sdots = dots(MX, SHOP_Y - 0.2, 3, GREEN_M)
        self.steps("The report runs on Spark, a program that runs one job across many computers. "
                   "Spark cuts the payments into slices called partitions, and a task works on each slice. "
                   "Here, a million payments sit in four partitions.", [
            (lambda: [FadeOut(VGroup(rep2, plus, code, tiny, qm))], 0.6),
            "cuts the payments",
            (lambda: [LaggedStart(*[FadeIn(VGroup(b, p)) for b, p in zip(boxes, pays)], lag_ratio=0.2)], 1.0),
            "a task works",
            (lambda: [LaggedStart(*[FadeIn(l) for l in labs], lag_ratio=0.2)], 0.8),
            "a million payments",
            (lambda: self.cap("1,000,000 payments: 4 partitions of 250,000", WHITE), 0.6),
        ])
        self.steps("Matching the rows of two tables that share a key is called a join. And here's the catch. "
                   "Spark can only match two rows that sit in the same task.", [
            "called a join",
            (lambda: [FadeIn(VGroup(sbox, slab, sdots), shift=0.15 * UP),
                      *self.put("head", T("payments JOIN shops, on the shop number", 24, GREY_B).move_to([-2.9, HEAD_Y, 0]))], 0.8),
            "the same task",
            (lambda: self.cap("a match needs both rows in the same task", WHITE), 0.6),
        ])
        self.steps("Shop 42 has payments in all four partitions, and its own row is in the shops table, somewhere else. "
                   "So before any matching, rows have to move.", [
            "Shop 42",
            (lambda: [*[p[GOLD_AT[i]].animate(rate_func=there_and_back).scale(1.9) for i, p in enumerate(pays)]], 1.0),
            "its own row",
            (lambda: [sdots[3].animate(rate_func=there_and_back).scale(1.9)], 0.8),
            "rows have to move",
            (lambda: self.cap("before any matching, rows have to move", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("tasks")

        # ---------------- scene 3: the post office ----------------
        clerks = [label(f"clerk {i + 1}", MX, y, GOLD_M) for i, y in enumerate(YS)]
        plist = label("postcode list: 1 page", MX, SHOP_Y, GOLD_M)
        self.steps("Picture a post office at the end of the day. Four clerks each hold a sack of letters from all over town.", [
            (lambda: [*self.uncap(), *self.drop("head")], 0.4),
            "Four clerks",
            (lambda: [*[Transform(l, c) for l, c in zip(labs, clerks)], *[b.animate.set_stroke(GOLD_M) for b in boxes]], 0.8),
            "a sack of letters",
            (lambda: [LaggedStart(*[Indicate(p, color=GOLD_M, scale_factor=1.1) for p in pays], lag_ratio=0.15)], 1.0),
        ])
        self.steps("Every letter has a postcode, and a one page list says which district each postcode is in. "
                   "The job is to write the district on every letter.", [
            "a one page list",
            (lambda: [Transform(slab, plist)], 0.7),
            "The job",
            (lambda: self.cap("the job: write the district on every letter", WHITE), 0.6),
        ])
        self.steps("Let's map it. The clerks are the tasks. The letters are the payments. "
                   "The postcode is the shop number. And the one page list is the shops table.", [
            "The clerks are",
            (lambda: [*[Transform(l, label(f"map task {i}", MX, YS[i])) for i, l in enumerate(labs)],
                      *[b.animate.set_stroke(WHITE) for b in boxes], *self.cap("clerks = tasks", WHITE)], 0.7),
            "The letters are",
            (lambda: self.cap("clerks = tasks      letters = payments", WHITE), 0.5),
            "The postcode",
            (lambda: self.cap("clerks = tasks      letters = payments      postcode = shop number", WHITE), 0.5),
            "And the one page",
            (lambda: [Transform(slab, label("shops: 500 rows", MX, SHOP_Y, GREEN_M)),
                      *self.cap("clerks = tasks      letters = payments      postcode = shop number      list = shops table", WHITE)], 0.6),
        ], after=0.3)
        self.stamp("post office")

        # ---------------- scene 4: way one, move everything ----------------
        reds = [VGroup(frame(RX, y, PC[k]), label(f"reduce task {k}", RX, y)) for k, y in enumerate(YS)]
        rstat = [status("waiting", RX, y, GREY_C) for y in YS]
        rule = mbox("hash(shop number) mod 4", GREY_B, size=21, h=0.6).move_to([0.9, HEAD_Y, 0])
        self.steps("Way one moves everything. Each task works out a number for every row: hash the shop number, "
                   "divide by four, keep the remainder. Shop 42 gets 3.", [
            (lambda: [*self.cap("way one: move everything", WHITE)], 0.5),
            "hash the shop",
            (lambda: [FadeIn(rule, shift=0.1 * DOWN)], 0.6),
            "keep the remainder",
            (lambda: [LaggedStart(*[FadeIn(VGroup(r, s), shift=0.15 * LEFT) for r, s in zip(reds, rstat)], lag_ratio=0.15)], 1.0),
            "Shop 42 gets 3",
            (lambda: [glow(reds[3][0], GOLD_M, 1.04)], 0.8),
        ])
        files = [shuffle_file(y) for y in YS]
        warrs = [write_arrow(y) for y in YS]
        disk = T("each task's own disk", 19, GREY_B).move_to([FX, YS[0] + 0.5, 0])
        golds = [p[GOLD_AT[i]].copy() for i, p in enumerate(pays)]
        self.steps("Like clerks sorting letters into four pigeonholes, one per van, each task writes its rows to its own disk in four blocks.", [
            "writes its rows",
            (lambda: [*[GrowArrow(a) for a in warrs]], 0.5),
            (lambda: [*[LaggedStart(*[FadeIn(b) for b in f], lag_ratio=0.25) for f in files], FadeIn(disk)], 0.9),
            "in four blocks",
            (lambda: [*[g.animate.move_to(files[i][3]).scale(1.3) for i, g in enumerate(golds)]], 0.8),
            (lambda: [*[FadeOut(g) for g in golds], *[glow(f[3][0], GOLD_M, 1.1) for f in files]], 0.5),
        ])
        f3 = [fetch(YS[i], 3, i) for i in range(4)]
        rest = [fetch(YS[i], k, i) for k in range(3) for i in range(4)]
        self.steps("Then each task on the far side, called a reduce task, collects its block from every file, like a van doing its round. "
                   "Spark calls this move a shuffle.", [
            "collects its block",
            (lambda: [*[GrowArrow(a) for a in f3]], 0.6),
            (lambda: [LaggedStart(*[flow(a, GOLD_M, 0.8) for a in f3], lag_ratio=0.15),
                      Transform(rstat[3], status("payments of shop 42", RX, YS[3], GOLD_M))], 1.3),
            "Spark calls",
            (lambda: [LaggedStart(*[GrowArrow(a) for a in rest], lag_ratio=0.05),
                      *self.cap("the shuffle: write blocks to disk, then fetch them", WHITE)], 1.2),
        ])
        mfile, mwarr = shuffle_file(SHOP_Y), write_arrow(SHOP_Y)
        mf = fetch(SHOP_Y, 3, 4, GREEN_M)
        self.steps("The shops go through the same shuffle, with the same rule. "
                   "So shop 42's row lands in reduce task 3, right beside its payments.", [
            (lambda: [GrowArrow(mwarr), LaggedStart(*[FadeIn(b) for b in mfile], lag_ratio=0.25)], 0.9),
            "So shop 42's row",
            (lambda: [GrowArrow(mf)], 0.5),
            (lambda: [flow(mf, GOLD_M, 0.8)], 0.8),
            (lambda: [Transform(rstat[3], status("shop 42: both sides", RX, YS[3], GOLD_M))], 0.5),
        ])
        self.steps("Each reduce task sorts both piles by shop number and walks them together, like merging two sorted piles of letters. "
                   "That's a sort-merge join. It works at any size, because sorting can spill to disk.", [
            (lambda: [*[Transform(s, status("sort, then merge", RX, YS[k], PC[k])) for k, s in enumerate(rstat)]], 0.7),
            "That's a sort-merge",
            (lambda: [*self.cap("sort-merge join: shuffle both sides, sort, merge", WHITE),
                      LaggedStart(*[glow(r[0], PC[k], 1.03) for k, r in enumerate(reds)], lag_ratio=0.15)], 1.0),
        ])
        allf = f3 + rest + [mf]
        self.steps("But count what moved. Every payment and every shop: 1,000,500 rows, written to disk, read back and sent across. "
                   "In the lesson's demo, that's four stages and about 9.4 MB.", [
            "Every payment",
            (lambda: [*self.put("cnt", chip("rows moved: 1,000,500", RED_M, 22).move_to(CNT)), FadeOut(rule)], 0.6),
            "written to disk",
            (lambda: [*[glow(f[k][0], PC[k], 1.1) for f in files + [mfile] for k in range(4)]], 0.8),
            "sent across",
            (lambda: [LaggedStart(*[flow(a, a.get_color(), 0.8) for a in allf], lag_ratio=0.03)], 1.4),
            "In the lesson's demo",
            (lambda: self.cap("the demo: 1,000,500 rows, 4 stages, about 9.4 MB shuffled", WHITE), 0.6),
        ], after=0.3)
        self.stamp("sort-merge")

        # ---------------- scene 5: photocopy the list ----------------
        self.steps("Back in the post office, that's a lot of driving for a one page list. Wouldn't it be nicer to move the list instead?", [
            "a lot of driving",
            (lambda: [*self.cap("a lot of driving, for a one page list", WHITE)], 0.6),
            "move the list",
            (lambda: [*[FadeOut(a) for a in allf + warrs + [mwarr]], *[FadeOut(f) for f in files + [mfile]], FadeOut(disk),
                      *[FadeOut(VGroup(r, s)) for r, s in zip(reds, rstat)], *self.drop("cnt")], 0.9),
        ])
        self.steps("So photocopy it. Every clerk gets a copy and writes the district on each letter right at the desk. "
                   "How many letters have to move now? Pause and guess.", [
            "So photocopy",
            (lambda: [glow(sbox, GOLD_M, 1.04)], 0.7),
            "Every clerk",
            (lambda: [*self.cap("every clerk gets a copy of the list", WHITE)], 0.5),
            "Pause and guess",
            (lambda: self.cap("how many letters move now?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("None. Not one letter leaves the desk.", [
            (lambda: [*self.put("cnt", chip("payments moved: 0", GREEN_M, 22).move_to(CNT)), *self.uncap()], 0.6),
        ], after=0.3)

        # ---------------- scene 6: broadcast hash join ----------------
        drv = VGroup(frame(RX, SHOP_Y, GREEN_M), label("driver", RX, SHOP_Y, GREEN_M), status("plans the job", RX, SHOP_Y))
        col = Arrow([MX + BW / 2 + 0.06, SHOP_Y, 0], [RX - BW / 2 - 0.06, SHOP_Y, 0], buff=0, stroke_width=3, color=GREEN_M,
                    max_tip_length_to_length_ratio=0.03)
        copies = [chip("copy of 500 shops", GREEN_M, 19).move_to([FX, y, 0]) for y in YS]
        carrs = [Arrow([RX - BW / 2 + 0.25, SHOP_Y + BH / 2 + 0.04, 0], [copies[i].get_right()[0] + 0.08, YS[i] - 0.08, 0], buff=0,
                       stroke_width=2.5, color=GREEN_M, max_tip_length_to_length_ratio=0.04) for i in range(4)]
        self.steps("Spark does the same. The driver, the program that plans the job, collects the 500 shops and sends a copy to every worker. "
                   "Spark calls these workers executors.", [
            "The driver",
            (lambda: [FadeIn(drv, shift=0.15 * LEFT)], 0.7),
            "collects the 500",
            (lambda: [GrowArrow(col)], 0.5),
            (lambda: [flow(col, GREEN_M, 0.9), Transform(drv[2], status("holds 500 shops", RX, SHOP_Y))], 0.9),
            "sends a copy",
            (lambda: [*[GrowArrow(a) for a in carrs]], 0.6),
            (lambda: [*[flow(a, GREEN_M, 0.7) for a in carrs], *[FadeIn(c) for c in copies]], 0.8),
            "executors",
            (lambda: self.cap("each worker, called an executor, gets a full copy", WHITE), 0.6),
        ])
        tabs = [chip("hash table: 500 shops", GREEN_M, 19).move_to([FX, y, 0]) for y in YS]
        self.steps("Each task builds a hash table from its copy: a lookup that finds a shop in one step, like a HashMap. "
                   "Then it streams its 250,000 payments through it and joins them where they sit.", [
            (lambda: [*[FadeOut(a) for a in carrs], FadeOut(col), *[FadeTransform(c, t) for c, t in zip(copies, tabs)]], 0.8),
            "a lookup",
            (lambda: self.cap("a hash table finds a shop in one step", WHITE), 0.5),
            "Then it streams",
            (lambda: [*[LaggedStart(*[Indicate(d, color=GREEN_M, scale_factor=1.6) for d in p], lag_ratio=0.1) for p in pays]], 1.2),
            "joins them",
            (lambda: [*[Transform(p, status("joined in place", MX, YS[i], GREEN_M)) for i, p in enumerate(pays)]], 0.8),
        ])
        smj_t = chip("sort-merge join: 165 ms", PURPLE_M, 21).move_to([RX, 1.55, 0])
        bhj_t = chip("broadcast hash join: 91 ms", GREEN_M, 21).move_to([RX, 0.55, 0])
        self.steps("That's a broadcast hash join. No payment is shuffled, and nothing is sorted. "
                   "In the demo, it took 91 milliseconds, against 165 for the sort-merge join. About half.", [
            "broadcast hash join",
            (lambda: [*self.cap("broadcast hash join: copy the small side, leave the big side where it is", WHITE),
                      LaggedStart(*[glow(t[0], GREEN_M, 1.06) for t in tabs], lag_ratio=0.15)], 1.0),
            "In the demo",
            (lambda: [FadeIn(bhj_t, shift=0.1 * UP)], 0.5),
            "against 165",
            (lambda: [FadeIn(smj_t, shift=0.1 * UP)], 0.5),
            "About half",
            (lambda: [glow(bhj_t[0], GREEN_M, 1.05)], 0.6),
        ], after=0.3)
        self.stamp("broadcast")

        # ---------------- scene 7: the trap ----------------
        rule2 = chip("Spark broadcasts if its guess is under 10 MB", GREY_B, 21).move_to([-0.9, HEAD_Y, 0])
        self.steps("So why didn't Spark do this for our report? It does broadcast on its own, when its size guess for one side is under 10 MB.", [
            (lambda: [FadeOut(smj_t), FadeOut(bhj_t), *self.cap("so why didn't Spark do this for our report?", WHITE)], 0.6),
            "It does broadcast",
            (lambda: [FadeIn(rule2, shift=0.1 * DOWN)], 0.6),
        ])
        filt = T("filter: still in business", 19, GREEN_M)
        filt.move_to([FX, SHOP_Y + 0.22, 0])
        guess = T("Spark's guess: over 10 MB", 19, RED_M).move_to([FX, SHOP_Y - 0.22, 0])
        xs = [tick(False, 0.28).move_to(t) .set_z_index(5) for t in tabs]
        self.steps("Here's the trap. The report keeps only the shops still in business. After a filter, Spark often can't tell how small "
                   "a table has become, so it kept its guess for the whole table: over 10 MB. It weighed the shops before their diet.", [
            "keeps only the shops",
            (lambda: [FadeIn(filt, shift=0.1 * RIGHT)], 0.6),
            "so it kept its guess",
            (lambda: [FadeIn(guess, shift=0.1 * RIGHT), glow(sbox, RED_M, 1.04)], 0.8),
            "It weighed",
            (lambda: self.cap("it weighed the shops before their diet", WHITE), 0.6),
        ])
        self.steps("So it planned a sort-merge join, and every payment took the van. That's where the nineteen minutes went.", [
            (lambda: [*[Create(x) for x in xs], *self.put("cnt", chip("rows moved: 1,000,500", RED_M, 22).move_to(CNT))], 0.8),
            "That's where",
            (lambda: self.cap("6 min + a shuffle of every payment = 25 min", RED_M), 0.6),
        ])
        fix = M('payments.join(broadcast(merchants), "merchant_id")', 22, TEAL_M)
        kt = T("Kotlin", 18, GREY_B)
        self.steps("When you know a side is small, say so. Wrap it in broadcast. A hint is a request, and Spark can refuse it. "
                   "Here it copies the shops, and the payments stay where they are.", [
            "Wrap it in broadcast",
            (lambda: self.cap(VGroup(kt, fix).arrange(RIGHT, buff=0.35)), 0.7),
            "Here it copies",
            (lambda: [*[FadeOut(x) for x in xs], FadeOut(guess), *self.put("cnt", chip("payments moved: 0", GREEN_M, 22).move_to(CNT)),
                      LaggedStart(*[glow(t[0], GREEN_M, 1.06) for t in tabs], lag_ratio=0.15)], 1.0),
        ], after=0.3)
        self.stamp("trap")

        # ---------------- scene 8: the photocopier's limit ----------------
        big = [chip("copy: 2 GB", RED_M, 19).move_to([FX, y, 0]) for y in YS]
        self.steps("Now, where the photocopy picture breaks. Copying one page costs almost nothing. "
                   "But a broadcast table passes through the driver, and a full copy lands in every executor's memory.", [
            (lambda: [FadeOut(rule2), FadeOut(filt), *self.cap("where the photocopy picture breaks", WHITE)], 0.6),
            "passes through the driver",
            (lambda: [glow(drv[0], GREEN_M, 1.05)], 0.7),
            "a full copy lands",
            (lambda: [LaggedStart(*[glow(t[0], GREEN_M, 1.06) for t in tabs], lag_ratio=0.15)], 0.9),
        ])
        self.steps("Broadcast a 2 GB table to 100 executors and you've moved 200 GB, if the driver survives collecting it. "
                   "That's photocopying the phone book for every clerk. Keep broadcasts to tables of tens of megabytes.", [
            (lambda: [Transform(slab, label("a 2 GB table", MX, SHOP_Y, RED_M)), sbox.animate.set_stroke(RED_M),
                      *[FadeTransform(t, b) for t, b in zip(tabs, big)]], 0.8),
            "you've moved",
            (lambda: [*self.put("cnt", chip("2 GB × 100 executors = 200 GB", RED_M, 22).move_to([RX - 0.3, HEAD_Y, 0]))], 0.6),
            "if the driver survives",
            (lambda: [drv[0].animate.set_stroke(RED_M), Transform(drv[2], status("collects 2 GB", RX, SHOP_Y, RED_M))], 0.6),
            "photocopying the phone book",
            (lambda: self.cap("photocopying the phone book for every clerk", WHITE), 0.6),
            "Keep broadcasts",
            (lambda: self.cap("keep broadcasts to tables of tens of MB", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 9: moral and check ----------------
        tabs2 = [chip("hash table: 500 shops", GREEN_M, 19).move_to([FX, y, 0]) for y in YS]
        self.steps("So the moral of the story. Both sides big: shuffle both, and sort-merge. "
                   "One side small: send it to the data, and the big side stays put.", [
            (lambda: [Transform(slab, label("shops: 500 rows", MX, SHOP_Y, GREEN_M)), sbox.animate.set_stroke(GREEN_M),
                      drv[0].animate.set_stroke(GREEN_M), Transform(drv[2], status("holds 500 shops", RX, SHOP_Y)),
                      *[FadeTransform(b, t) for b, t in zip(big, tabs2)], *self.drop("cnt"),
                      *self.cap("both sides big: shuffle both, and sort-merge", WHITE)], 0.9),
            "One side small",
            (lambda: [*self.cap("one side small: send it to the data", YELLOW_M),
                      *self.put("cnt", chip("payments moved: 0", GREEN_M, 22).move_to(CNT))], 0.7),
        ], after=0.3)
        self.steps("One quick check. A report joins the payments with a customers table of 3 GB. "
                   "Should you broadcast the customers? Pause and think.", [
            (lambda: [Transform(slab, label("customers: 3 GB", MX, SHOP_Y, GOLD_M)), sbox.animate.set_stroke(GOLD_M),
                      *self.drop("cnt"), *self.uncap()], 0.7),
            "Pause and think",
            (lambda: self.cap("broadcast the customers?  pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        nos = [tick(False, 0.28).move_to(t).set_z_index(5) for t in tabs2]
        self.steps("No. Three gigabytes in every executor is the phone book again. Both sides are big, so shuffle both.", [
            (lambda: [*[Create(x) for x in nos], *self.uncap()], 0.7),
            "so shuffle both",
            (lambda: self.cap("both sides big: shuffle both, and sort-merge", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("both big: shuffle both.  one small: send it to the data", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
