from sfz import *

SAY.insert(0, (r"\bmongos\b", "mongo S"))
SAY.insert(0, (r"\bMinKey\b", "min key"))
SAY.insert(0, (r"\bMaxKey\b", "max key"))
SAY.insert(0, (r"\bA-0000\b", "A zero"))
SAY.insert(0, (r"\bA-4999\b", "A forty-nine ninety-nine"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
APP = np.array([-4.4, 3.05, 0])
Q_POS = np.array([-0.55, 3.05, 0])
M1, M2 = np.array([-4.5, 1.55, 0]), np.array([-1.5, 1.55, 0])
CFG = np.array([3.85, 2.05, 0])
CFW, CFH = 5.2, 2.7
COLL, COLR = 1.55, 5.55                     # board columns: left edge of the range, centre of the owner
HDR_Y, ROW_Y = 2.45, [1.9, 1.35]
SHX, SHY, SHW, SHH = [-4.3, 0.0, 4.3], -1.25, 3.8, 1.8
RES = np.array([4.3, -1.25, 0])             # where explain() reports, once shard3 has gone
CNT_Y, BAR_Y, CAP_Y = -2.6, -2.95, -3.35
A_C, B_C, C_C = BLUE_M, GOLD_M, GREY_B


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    # captions, a counter line, and labels that swap in place
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

    def count(self, s, color=WHITE, size=24):
        return self.put("cnt", fit(T(s, size, color), 13.0).move_to([0, CNT_Y, 0]))

    def query(self, s, color=YELLOW_M):
        """A query chip; a list of strings stacks into lines so long filters stay readable."""
        lines = s if isinstance(s, list) else [s]
        t = VGroup(*[M(x, 19) for x in lines]).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.3, height=t.height + 0.26, stroke_color=color, stroke_width=2.5)
        r.set_fill(color, opacity=0.18)
        return self.put("q", fit(VGroup(r, t.move_to(r)), 3.9).move_to(Q_POS + 0.25 * LEFT))

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


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def shard_box(title, color, x, w=SHW):
    """A replica set: a frame, a title, P S S members. Parts: [frame, title, members]."""
    fr = RoundedRectangle(corner_radius=0.14, width=w, height=SHH, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.1), 1)
    fr.move_to([x, SHY, 0])
    t = T(title, 22, color).move_to([x, SHY + 0.58, 0])
    mem = VGroup(*[mbox(n, color if n == "P" else GREY_B, w=0.62, h=0.48, size=20) for n in "PSS"]).arrange(RIGHT, buff=0.22)
    mem.move_to([x, SHY - 0.02, 0])
    return VGroup(fr, t, mem)


def top_of(x):
    return np.array([x, SHY + SHH / 2 + 0.06, 0])


def p_of(s):
    return s[2][0].get_center()


class MongoSharding(Base):
    """shard-07, section 2. One replica set's two limits (16 GB server, 7.5 GB cache, 3 TB; 8,000 writes a second at
    70%, 25,000 needed); sharding; the rule in the app (A-0000 to A-4999) and why a third shard breaks it; the board by
    the door (config servers) and the porter (mongos); shard key, chunks, MinKey and MaxKey on a hashed _id; 20,000
    payments split 10,079 and 9,921; SINGLE_SHARD and SHARD_MERGE; what scatter-gather costs; a check."""

    def bottom(self, key, x, s, color):
        return self.put(key, T(s, 20, color).move_to([x, SHY - 0.6, 0]))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("A board by the door", "how MongoDB finds the shard that holds a payment")

        app = box("payments service", WHITE, size=22, h=0.7).move_to(APP)
        rs = shard_box("payments: one replica set", WHITE, 0.0, w=4.4)

        # ---------------- scene 1: the question ----------------
        self.steps("The payments app has grown. Three terabytes of payments, and on the busiest shopping day of the year, "
                   "25,000 new ones a second.", [
            (lambda: [FadeIn(app, shift=0.1 * DOWN), FadeIn(rs[0]), FadeIn(rs[1])], 0.9),
            "Three terabytes",
            (lambda: self.cap("3 TB of payments; busiest day: 25,000 writes a second", WHITE), 0.6),
        ])
        self.steps("One group of servers can't keep up any more, so we'll split the payments over several groups. "
                   "But then a new question shows up. When the app wants one payment, how does it know which group has it? "
                   "Hold that question.", [
            "how does it know",
            (lambda: self.cap("which group holds this payment?", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 2: one replica set, two limits ----------------
        in_arrow = Arrow(app.get_bottom(), rs[0].get_top() + np.array([-1.2, 0.05, 0]), buff=0.1, stroke_width=3, color=GREY_B,
                         max_tip_length_to_length_ratio=0.08)
        self.steps("Start with what we have. MongoDB, a free database program, keeps its copies in a replica set: "
                   "a group of servers that hold the same data. One of them, the primary, takes every write, and the others copy it.", [
            (lambda: self.uncap(), 0.4),
            "a replica set",
            (lambda: [LaggedStart(*[FadeIn(m) for m in rs[2]], lag_ratio=0.3)], 0.9),
            "the primary",
            (lambda: [GrowArrow(in_arrow)], 0.5),
            (lambda: [dot_run(in_arrow.get_start(), in_arrow.get_end(), YELLOW_M, 0.6)], 0.65),
            (lambda: [glow(rs[2][0][0], YELLOW_M, 1.1)], 0.5),
            "the others copy",
            (lambda: [dot_run(p_of(rs) + 0.32 * RIGHT, rs[2][1].get_left(), YELLOW_M, 0.4),
                      dot_run(p_of(rs) + 0.32 * RIGHT, rs[2][2].get_left(), YELLOW_M, 0.7)], 0.8),
        ])
        self.steps("In the lesson's cloakroom, one attendant writes every coat in a notebook, and two assistants copy each line, "
                   "so either can take over if he faints.", [
            (lambda: self.cap("the attendant is the primary; the two assistants are the secondaries", WHITE), 0.6),
            "two assistants",
            (lambda: [glow(rs[2][1][0], GREY_B, 1.1), glow(rs[2][2][0], GREY_B, 1.1)], 0.6),
        ])
        stats = [T(s, 20, c) for s, c in [("disk: 3 TB of payments", WHITE), ("cache: about 7.5 GB of 16 GB", WHITE)]]
        for k, s in enumerate(stats):
            s.move_to([2.6 + s.width / 2, SHY + 0.5 - 0.5 * k, 0])
        self.steps("That gives two limits. First, everything must fit on one machine. A 16 GB server gives its cache about 7.5 GB, "
                   "so with 3 TB of payments, most reads go to disk, which is far slower than memory.", [
            "First",
            (lambda: [*self.cap("limit 1: everything must fit on one machine", WHITE)], 0.6),
            "A 16 GB",
            (lambda: [FadeIn(stats[1], shift=0.1 * LEFT)], 0.5),
            "with 3 TB",
            (lambda: [FadeIn(stats[0], shift=0.1 * LEFT)], 0.5),
            "most reads",
            (lambda: [*self.cap("most reads go to disk, far slower than memory", RED_M)], 0.6),
        ])
        w1 = T("writes: 8,000 a second at 70%", 20, WHITE)
        w2 = T("needed: 25,000 a second", 20, RED_M)
        for k, s in enumerate([w1, w2]):
            s.move_to([2.6 + s.width / 2, SHY - 0.5 - 0.5 * k, 0])
        self.steps("Second, every write goes through one primary. Say it takes 8,000 payments a second at 70% of its processor. "
                   "The busy day needs 25,000.", [
            (lambda: [*self.cap("limit 2: every write goes through one primary", WHITE)], 0.6),
            (lambda: [LaggedStart(*[dot_run(in_arrow.get_start(), in_arrow.get_end(), YELLOW_M, 0.5) for _ in range(5)], lag_ratio=0.25)], 1.4),
            "8,000",
            (lambda: [FadeIn(w1, shift=0.1 * LEFT)], 0.5),
            "The busy day",
            (lambda: [FadeIn(w2, shift=0.1 * LEFT), glow(rs[2][0][0], RED_M, 1.15)], 0.6),
        ])
        extra = mbox("S", GREY_B, w=0.62, h=0.48, size=20).move_to(rs[2][2].get_center() + np.array([0.84, 0, 0]))
        self.steps("More secondaries don't help, because each one has to replay all 25,000 writes too. "
                   "Hiring more assistants to copy the notebook never made the attendant write any faster.", [
            (lambda: [FadeIn(extra, shift=0.1 * LEFT)], 0.5),
            "replay all",
            (lambda: [dot_run(p_of(rs) + 0.32 * RIGHT, extra.get_left(), RED_M, 0.8), glow(extra[0], RED_M, 1.15)], 0.9),
            "Hiring more",
            (lambda: [*self.cap("more copies of the notebook: the same one writer", WHITE)], 0.6),
        ], after=0.3)
        self.stamp("limits")

        # ---------------- scene 3: split it ----------------
        s1 = shard_box("shard1", A_C, SHX[0])
        s2 = shard_box("shard2", B_C, SHX[1])
        self.steps("So we split the payments over several replica sets. That's called sharding, and each replica set "
                   "that holds a part is a shard: one attendant, with his own assistants copying his notebook.", [
            (lambda: [FadeOut(VGroup(*stats, w1, w2, extra, in_arrow)), *self.uncap()], 0.5),
            (lambda: [ReplacementTransform(rs, s1)], 1.0),
            (lambda: [FadeIn(s2, shift=0.3 * RIGHT)], 0.8),
            "That's called sharding",
            (lambda: self.cap("sharding: split the data; each part, a replica set of its own, is a shard", WHITE), 0.6),
            "one attendant",
            (lambda: [glow(s1[0], A_C), glow(s2[0], B_C)], 0.8),
        ], after=0.3)

        # ---------------- scene 4: the rule in the app ----------------
        s3 = shard_box("shard3", C_C, SHX[2])
        self.steps("The obvious first version puts the rule in the app. Accounts A-0000 to A-4999 go to shard 1, "
                   "the rest go to shard 2.", [
            (lambda: [*self.uncap(), *self.query(["A-0000 to A-4999 → shard1", "everything else  → shard2"], PURPLE_M)], 0.6),
            "go to shard 1",
            (lambda: [dot_run(app.get_bottom(), top_of(SHX[0]), A_C, 0.8)], 0.85),
            "the rest",
            (lambda: [dot_run(app.get_bottom(), top_of(SHX[1]), B_C, 0.8)], 0.85),
        ])
        self.steps("That works, until shard 1 fills up. Adding a third shard means changing every copy of the program at the same moment, "
                   "and moving payments while new ones keep arriving.", [
            "fills up",
            (lambda: [*self.bottom("b1", SHX[0], "full", RED_M), glow(s1[0], RED_M)], 0.6),
            "Adding a third",
            (lambda: [FadeIn(s3, shift=0.2 * LEFT)], 0.7),
            "changing every copy",
            (lambda: [self.lab["q"][0].animate.set_stroke(RED_M).set_fill(RED_M, 0.18), glow(app[0], RED_M, 1.06)], 0.6),
            "moving payments",
            (lambda: [dot_run([SHX[0], SHY - SHH / 2 - 0.18, 0], [SHX[2], SHY - SHH / 2 - 0.18, 0], RED_M, 0.9),
                      *self.cap("change every copy of the app at once; move data while payments arrive", RED_M)], 0.6),
        ])
        self.steps("It's like reprinting every ticket in the theatre while the show is on.", [
            (lambda: [LaggedStart(*[dot_run(app.get_bottom(), top_of(x), RED_M, 0.6) for x in SHX], lag_ratio=0.3)], 1.3),
        ], after=0.3)
        self.stamp("break")

        # ---------------- scene 5: the board and the porter ----------------
        board = RoundedRectangle(corner_radius=0.16, width=CFW, height=CFH, stroke_color=GOLD_M, stroke_width=3).set_fill(BLACK, 1).move_to(CFG)
        btitle = T("a board by the door", 24, GOLD_M).move_to([CFG[0], CFG[1] + 1.0, 0])

        def hdr(a, b):
            return VGroup(M(a, 18, GREY_B).move_to([COLL, HDR_Y, 0], aligned_edge=LEFT), M(b, 18, GREY_B).move_to([COLR, HDR_Y, 0]))

        def brow(i, a, b, color, mono=True):
            f = M if mono else T
            return VGroup(f(a, 20, color).move_to([COLL, ROW_Y[i], 0], aligned_edge=LEFT), f(b, 20, color).move_to([COLR, ROW_Y[i], 0]))

        h_cl = hdr("tickets", "counter")
        r_cl = [brow(0, "1 to 300", "counter 1", WHITE, False), brow(1, "301 to 600", "counter 2", WHITE, False)]
        porter = mbox("porter", PURPLE_M, w=1.9, h=0.65, size=22).move_to(M2)
        self.steps("Here's the better idea. Take the rule out of the code and make it data: a table of key ranges, "
                   "and the shard that holds each one.", [
            (lambda: [FadeOut(s3), *self.drop("q", "b1"), *self.uncap()], 0.6),
            "make it data",
            (lambda: [FadeIn(board), FadeIn(h_cl)], 0.7),
        ])
        self.steps("In the cloakroom, that's a board by the door. Tickets 1 to 300, counter one. 301 to 600, counter two. "
                   "And a porter stands next to it, reads the board, and sends you to the right counter.", [
            (lambda: [FadeIn(btitle)], 0.5),
            "Tickets 1 to 300",
            (lambda: [FadeIn(r_cl[0], shift=0.1 * RIGHT)], 0.5),
            "301 to 600",
            (lambda: [FadeIn(r_cl[1], shift=0.1 * RIGHT)], 0.5),
            "And a porter",
            (lambda: [FadeIn(porter, shift=0.1 * DOWN)], 0.5),
            "reads the board",
            (lambda: [Indicate(r_cl[1], color=YELLOW_M, scale_factor=1.06)], 0.6),
            "sends you",
            (lambda: [dot_run(porter.get_bottom(), top_of(SHX[1]), YELLOW_M, 0.7)], 0.75),
        ], after=0.3)

        ctitle = VGroup(T("config servers", 24, TEAL_M), T("a replica set", 18, GREY_B)).arrange(RIGHT, buff=0.25, aligned_edge=DOWN)
        ctitle.move_to(btitle)
        mg1 = mbox("mongos", PURPLE_M, w=1.9, h=0.65, size=22).move_to(M1)
        mg2 = mbox("mongos", PURPLE_M, w=1.9, h=0.65, size=22).move_to(M2)
        a1 = Arrow(app.get_bottom(), mg1.get_top(), buff=0.08, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.25)
        a2 = Arrow(app.get_bottom(), mg2.get_top(), buff=0.08, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.12)
        cache = DashedLine(mg2.get_right() + 0.12 * RIGHT, [CFG[0] - CFW / 2 - 0.12, M2[1], 0], dash_length=0.1, stroke_width=2, color=TEAL_M)
        cache_l = T("cached map", 18, TEAL_M).next_to(cache, UP, buff=0.1)
        self.steps("Let's map it. The board is a table that MongoDB keeps on the config servers. "
                   "It's now the most important data in the system, so it gets a replica set of its own.", [
            "on the config servers",
            (lambda: [ReplacementTransform(btitle, ctitle), board.animate.set_stroke(TEAL_M)], 0.7),
            "most important",
            (lambda: [glow(board, TEAL_M, 1.02)], 0.7),
            "a replica set of its own",
            (lambda: self.cap("the board: the config servers, a replica set of their own", WHITE), 0.6),
        ])
        self.steps("The porter is a router called mongos. It keeps a copy of the board in memory and stores nothing on disk.", [
            "a router called mongos",
            (lambda: [ReplacementTransform(porter, mg2), *self.cap("the porter: a router called mongos", WHITE)], 0.7),
            "a copy of the board",
            (lambda: [Create(cache), FadeIn(cache_l)], 0.7),
            "stores nothing",
            (lambda: self.cap("mongos keeps the map in memory and stores nothing on disk", WHITE), 0.6),
        ])
        self.steps("The app talks only to mongos, so you run several, often one next to each copy of the app.", [
            (lambda: [GrowArrow(a2)], 0.5),
            "so you run several",
            (lambda: [FadeIn(mg1, shift=0.1 * DOWN), GrowArrow(a1)], 0.6),
            (lambda: self.cap("apps talk only to mongos; run several", WHITE), 0.6),
        ], after=0.3)
        self.stamp("board")

        # ---------------- scene 6: shard key and chunks ----------------
        h_ch = hdr("hash(_id) range", "shard")
        h_key = hdr("shard key range", "shard")
        r_gen = [brow(0, "[MinKey, k1)", "a shard", WHITE), brow(1, "[k1, MaxKey)", "a shard", WHITE)]
        r_ch = [brow(0, "[MinKey, 0)", "shard2", B_C), brow(1, "[0, MaxKey)", "shard1", A_C)]
        self.steps("Which field does the board go by? You choose it, and it's called the shard key. "
                   "All its possible values are cut into ranges called chunks, and each chunk belongs to one shard.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*r_cl))], 0.5),
            "the shard key",
            (lambda: [ReplacementTransform(h_cl, h_key), *self.cap("shard key: the field the board goes by", WHITE)], 0.7),
            "ranges called chunks",
            (lambda: [*[FadeIn(r, shift=0.1 * RIGHT) for r in r_gen], *self.cap("chunks: ranges of shard key values, each on one shard", WHITE)], 0.6),
        ])
        self.steps("The first chunk starts at MinKey, a value below every other, and the last ends at MaxKey, above every other. "
                   "So every possible key has exactly one home.", [
            "The first chunk",
            (lambda: [Indicate(r_gen[0][0], color=YELLOW_M, scale_factor=1.08)], 0.6),
            "the last ends",
            (lambda: [Indicate(r_gen[1][0], color=YELLOW_M, scale_factor=1.08)], 0.6),
            "every possible key",
            (lambda: [*self.cap("MinKey: below every value.  MaxKey: above every value", WHITE)], 0.6),
        ])
        self.steps("In the lesson's lab, the key is a hash of the payment's id. MongoDB turns each id into a big, random-looking number, "
                   "and the chunks own ranges of those numbers. Below zero goes to shard 2. Zero and up goes to shard 1.", [
            (lambda: [ReplacementTransform(h_key, h_ch), FadeOut(VGroup(*r_gen)),
                      *self.cap(M("sh.shardCollection(\"sfz.payments\", { _id: \"hashed\" })", 20, TEAL_M))], 0.7),
            "Below zero",
            (lambda: [FadeIn(r_ch[0], shift=0.1 * RIGHT), *self.bottom("b2", SHX[1], "chunk [MinKey, 0)", B_C)], 0.6),
            "Zero and up",
            (lambda: [FadeIn(r_ch[1], shift=0.1 * RIGHT), *self.bottom("b1", SHX[0], "chunk [0, MaxKey)", A_C)], 0.6),
        ])
        self.steps("For an insert, mongos reads the key, finds the chunk that holds it, and sends the insert to that shard's primary.", [
            (lambda: [*self.query("insert one payment"), *self.uncap()], 0.5),
            (lambda: [dot_run(app.get_bottom(), mg2.get_top(), YELLOW_M, 0.6)], 0.65),
            "finds the chunk",
            (lambda: [Indicate(r_ch[1], color=YELLOW_M, scale_factor=1.06)], 0.7),
            "sends the insert",
            (lambda: [dot_run(mg2.get_bottom(), p_of(s1) + 0.3 * UP, YELLOW_M, 0.8)], 0.85),
            (lambda: [glow(s1[2][0][0], YELLOW_M, 1.15)], 0.5),
        ], after=0.3)
        self.stamp("chunks")

        # ---------------- scene 7: predict, then route ----------------
        self.steps("Now we insert 20,000 payments. How do they split between the two shards? Pause and guess.", [
            (lambda: [*self.query("insertMany(payments(20000))"), *self.cap("20,000 payments: how do they split?  pause and guess", YELLOW_M)], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("10,079 on shard 1 and 9,921 on shard 2. Almost half and half, and no data had to move.", [
            (lambda: [*self.uncap(), LaggedStart(*[dot_run(mg2.get_bottom(), top_of(SHX[k % 2]), [A_C, B_C][k % 2], 0.6)
                                                   for k in (0, 1, 1, 0, 1, 0, 0, 1)], lag_ratio=0.18)], 1.6),
            (lambda: [*self.bottom("b1", SHX[0], "10,079 payments", A_C), *self.bottom("b2", SHX[1], "9,921 payments", B_C)], 0.6),
            "no data had to move",
            (lambda: self.cap("no data moved: the chunks were cut at 0 before the first insert", WHITE), 0.6),
        ], after=0.3)

        res_t = T("explain() says", 20, GREY_B).move_to(RES + 0.45 * UP)
        self.steps("Next, look up one payment by its id. The filter gives the shard key, so mongos hashes the id, reads the board, "
                   "and asks only one shard.", [
            (lambda: [*self.uncap(), *self.query('{ _id: "pay-101723" }')], 0.6),
            "The filter",
            (lambda: [dot_run(app.get_bottom(), mg2.get_top(), YELLOW_M, 0.6)], 0.65),
            "reads the board",
            (lambda: [Indicate(r_ch[0], color=YELLOW_M, scale_factor=1.06)], 0.7),
            "asks only one",
            (lambda: [dot_run(mg2.get_bottom(), top_of(SHX[1]), YELLOW_M, 0.7)], 0.75),
            (lambda: [glow(s2[0], YELLOW_M, 1.02)], 0.5),
            (lambda: [dot_run(top_of(SHX[1]), mg2.get_bottom(), B_C, 0.6)], 0.65),
        ])
        self.steps("explain, which reports how a query ran, says single shard. That's a targeted query.", [
            (lambda: [FadeIn(res_t), *self.put("res", M("SINGLE_SHARD", 24, GREEN_M).move_to(RES + 0.1 * DOWN))], 0.6),
            "a targeted query",
            (lambda: self.cap("targeted: the filter gives the shard key, so one shard is asked", WHITE), 0.6),
        ], after=0.3)
        self.steps("Now ask for one shop's failed payments. That filter has no shard key. Which shards does mongos ask? Pause and guess.", [
            (lambda: [*self.uncap(), *self.drop("res"), *self.query(['{ merchantId: "M-0042",', '  status: "FAILED" }'])], 0.6),
            "no shard key",
            (lambda: [Indicate(self.lab["q"], color=RED_M, scale_factor=1.05)], 0.6),
            "Pause and guess",
            (lambda: self.cap("which shards does mongos ask?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Every one. Each shard runs the query, and mongos merges the answers. explain says shard merge. "
                   "That's called a scatter-gather read.", [
            (lambda: [*self.uncap(), dot_run(mg2.get_bottom(), top_of(SHX[0]), YELLOW_M, 0.7),
                      dot_run(mg2.get_bottom(), top_of(SHX[1]), YELLOW_M, 0.7)], 0.75),
            "Each shard runs",
            (lambda: [glow(s1[0], YELLOW_M, 1.02), glow(s2[0], YELLOW_M, 1.02)], 0.6),
            "mongos merges",
            (lambda: [dot_run(top_of(SHX[0]), mg2.get_bottom(), A_C, 0.6), dot_run(top_of(SHX[1]), mg2.get_bottom(), B_C, 0.6)], 0.65),
            (lambda: [glow(mg2[0], PURPLE_M, 1.08)], 0.5),
            "explain says",
            (lambda: self.put("res", M("SHARD_MERGE", 24, RED_M).move_to(RES + 0.1 * DOWN)), 0.6),
            "scatter-gather",
            (lambda: self.cap("scatter-gather: ask every shard, merge the answers", WHITE), 0.6),
        ], after=0.3)
        self.stamp("scatter")

        # ---------------- scene 8: what scatter-gather costs ----------------
        self.steps("Why can't mongos do better? Each shard indexes only its own payments, so nothing tells mongos where that shop's payments sit. "
                   "A scatter-gather read is as slow as the slowest shard, and every shard pays for it.", [
            "Each shard indexes",
            (lambda: self.cap("each shard indexes only its own payments", WHITE), 0.6),
            "as slow as",
            (lambda: [glow(s1[0], RED_M, 1.02), glow(s2[0], RED_M, 1.02),
                      *self.cap("as slow as the slowest shard, and every shard pays", RED_M)], 0.8),
        ])
        self.steps("It's the porter shouting at every counter, has anyone seen a red scarf? Every attendant stops what they're doing to look.", [
            (lambda: [glow(mg2[0], PURPLE_M, 1.1)], 0.6),
            "Every attendant",
            (lambda: [LaggedStart(glow(s1[2][0][0], RED_M, 1.15), glow(s2[2][0][0], RED_M, 1.15), lag_ratio=0.4)], 0.9),
        ])
        self.steps("And one more limit: if the config servers can't pick a primary, the board can't change. "
                   "Reads and writes go on, but no data moves.", [
            "can't pick a primary",
            (lambda: [glow(board, RED_M, 1.02)], 0.8),
            "Reads and writes",
            (lambda: self.cap("no config primary: reads and writes go on, but no data moves", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: shards hold the payments, the config servers hold the board, "
                   "and mongos reads the board for every request.", [
            (lambda: [*self.drop("res", "q"), FadeOut(res_t), *self.cap("shards hold the payments; the config servers hold the board", YELLOW_M)], 0.6),
            "shards hold",
            (lambda: [glow(s1[0], A_C, 1.02), glow(s2[0], B_C, 1.02)], 0.6),
            "the config servers hold",
            (lambda: [glow(board, TEAL_M, 1.02)], 0.6),
            "mongos reads",
            (lambda: [glow(mg1[0], PURPLE_M, 1.08), glow(mg2[0], PURPLE_M, 1.08)], 0.6),
        ])
        self.steps("Give it the shard key, and it goes to one counter. Leave it out, and it asks them all.", [
            (lambda: self.cap("with the shard key: one shard.  without it: every shard", YELLOW_M), 0.6),
        ], after=0.3)
        self.steps("One quick check. Support looks up a payment by its id and its status. Which shards does mongos ask? Pause and think.", [
            (lambda: [*self.uncap(), *self.query(['{ _id: "pay-101723",', '  status: "FAILED" }'])], 0.6),
            "Pause and think",
            (lambda: self.cap("which shards?  pause and think", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)
        self.steps("Just one. The id is the shard key, so mongos can hash it and go straight there. The status only narrows the answer.", [
            (lambda: [*self.uncap(), dot_run(app.get_bottom(), mg2.get_top(), YELLOW_M, 0.5)], 0.55),
            (lambda: [Indicate(r_ch[0], color=YELLOW_M, scale_factor=1.06)], 0.6),
            (lambda: [dot_run(mg2.get_bottom(), top_of(SHX[1]), YELLOW_M, 0.6)], 0.65),
            (lambda: [FadeIn(res_t), *self.put("res", M("SINGLE_SHARD", 24, GREEN_M).move_to(RES + 0.1 * DOWN))], 0.6),
        ], after=0.3)
        self.steps("Everything hangs on that key. Next, we'll see what happens when the key is the time a payment was made.", [
            (lambda: self.cap("everything hangs on the shard key", YELLOW_M, 26), 0.6),
        ], after=0.3)
        self.wait(2.0)
