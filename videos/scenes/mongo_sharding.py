from sfz import *

SAY.insert(0, (r"\bmongos\b", "mongo S"))
SAY.insert(0, (r"\bM-0042\b", "M zero zero four two"))
SAY.insert(0, (r"\bpay-(\d+)\b", lambda m: "pay " + " ".join(m.group(1))))

A_C, B_C = BLUE_M, GOLD_M
AX, BX, SHY = -3.3, 3.0, -2.15       # shard centres
SW, SH = 5.0, 2.3                    # shard box size
CFX, CFW = 3.8, 5.4                 # config servers box centre x and width
ROW0, ROWH = 2.2, 0.4                # first table row y, row spacing
RX, SX = CFX - CFW / 2 + 0.3, CFX + CFW / 2 - 0.77   # range column left edge, shard column centre


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Like Scene's, but never re-adds a group whose parts are already on screen (that would draw
        filled boxes over their own labels), and leaves introducers inside groups to add themselves on cue."""
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
        """Removing a group removes its parts too, even when the parts were added one by one."""
        fam = []
        for m in mobjects:
            fam.extend(m.get_family())
        return super().remove(*fam)

    def steps(self, text, steps, after=0.25):
        """Speak one line and play several animations one after another inside it. Each step is built
        just before it plays, so it starts from where the previous one ended."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        t = 0
        for fn, rt in steps:
            if fn is None:
                self.wait(rt)
            else:
                self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def flash(m, color, s=1.08):
    """Stroke-and-scale flash that keeps an opaque box's label visible."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


def dot_run(a, b, color=YELLOW_M, rt=0.8):
    """A dot from point a to point b, built when called."""
    d = Dot(radius=0.09, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.15))


def shard(title, sub, color, fill, x, fill_col=None):
    """A shard: a replica set (P, S, S) and a bar for how full its disk is."""
    fr = RoundedRectangle(corner_radius=0.16, width=SW, height=SH, stroke_color=color, stroke_width=3)
    fr.set_fill(BLACK, 1)
    t = T(title, 30, color)
    s = T(sub, 22, GREY_B)
    head = VGroup(t, s).arrange(RIGHT, buff=0.25, aligned_edge=DOWN).move_to([0, 0.72, 0])
    mem = VGroup(*[mbox(n, color if n == "P" else GREY_B, w=0.7, h=0.56, size=22) for n in "PSS"]).arrange(RIGHT, buff=0.25)
    mem.move_to([0, 0.05, 0])
    bw = 3.4
    out = Rectangle(width=bw, height=0.3, stroke_color=GREY_C, stroke_width=2).move_to([-0.35, -0.68, 0])
    bar = Rectangle(width=max(0.02, bw * fill), height=0.3, stroke_width=0).set_fill(fill_col or color, 0.8)
    bar.move_to(out.get_left(), aligned_edge=LEFT)
    pct = T(f"{round(fill * 100)}%", 24, fill_col or color).next_to(out, RIGHT, buff=0.2)
    return VGroup(fr, head, mem, VGroup(out, bar, pct)).move_to([x, SHY, 0])


def row(i, lo, hi, owner, color):
    rng = M(f"{lo:<10}→ {hi}", 20, color).move_to([RX, ROW0 - i * ROWH, 0], aligned_edge=LEFT)
    sh = M(owner, 20, color).move_to([SX, ROW0 - i * ROWH, 0])
    return VGroup(rng, sh)


class MongoSharding(Base):
    """nosql-15: one replica set fills up, the collection is split into chunks over two shards, the config servers
    keep the chunk table, mongos routes targeted and scatter-gather queries, a monotonic key piles inserts on the last
    chunk, the balancer splits and moves a chunk, and a hashed key spreads the inserts."""

    def construct(self):
        self.title_card("Sharding MongoDB", "mongos, config servers and chunks")

        app = box("payments service", WHITE, size=24).move_to([-5.0, 3.0, 0])
        rs = shard("payments", "one replica set", WHITE, 0.9, 0, fill_col=RED_M)
        w_in = Arrow(app.get_bottom(), rs[0].get_corner(UR) + np.array([-0.7, 0.04, 0]), buff=0.12, stroke_width=3, color=GREY_B,
                     tip_length=0.22, max_tip_length_to_length_ratio=0.5)
        self.steps("Your payments collection lives in one replica set. Its disk is almost full, and one primary handles every change. "
                   "More secondaries don't help: each one replays every change too.", [
            (lambda: [FadeIn(app, shift=0.2 * DOWN), FadeIn(rs[0]), FadeIn(rs[1]), FadeIn(rs[2])], 1.0),
            (lambda: [FadeIn(rs[3][0]), GrowFromEdge(rs[3][1], LEFT), FadeIn(rs[3][2])], 1.0),
            (None, 0.8),
            (lambda: [GrowArrow(w_in)], 0.7),
            (lambda: [dot_run(w_in.get_start(), w_in.get_end(), YELLOW_M, 0.6)], 0.7),
            (lambda: [flash(rs[2][0], YELLOW_M, 1.2)], 0.7),
            (None, 0.8),
            (lambda: [LaggedStart(flash(rs[2][1], GREY_B, 1.2), flash(rs[2][2], GREY_B, 1.2), lag_ratio=0.4)], 1.2),
        ])

        sa = shard("shard1", "replica set", A_C, 0.45, AX)
        sb = shard("shard2", "replica set", B_C, 0.45, BX)
        self.steps("So you split the collection across two replica sets. Each one is a shard.", [
            (lambda: [FadeOut(w_in), ReplacementTransform(rs, sa)], 1.2),
            (lambda: [TransformFromCopy(sa, sb)], 1.2),
        ])

        # ---- chunks and the config servers ------------------------------------------------------------------
        cfg = RoundedRectangle(corner_radius=0.16, width=CFW, height=2.9, stroke_color=TEAL_M, stroke_width=3)
        cfg.set_fill(BLACK, 1).move_to([CFX, 2.0, 0])
        cfg_t = VGroup(T("config servers", 26, TEAL_M), T("a replica set", 20, GREY_B)).arrange(RIGHT, buff=0.25, aligned_edge=DOWN)
        cfg_t.move_to([CFX, 3.12, 0])
        hdr = VGroup(M("_id range", 18, GREY_B).move_to([RX, 2.66, 0], aligned_edge=LEFT), M("shard", 18, GREY_B).move_to([SX, 2.66, 0]))
        rows = VGroup(row(0, "MinKey", "pay-80000", "shard1", A_C), row(1, "pay-80000", "MaxKey", "shard2", B_C))
        self.steps("The split follows a shard key, here the payment id. MongoDB cuts the key's values into ranges called chunks, "
                   "and each chunk lives on one shard.", [
            (lambda: [FadeIn(cfg), FadeIn(hdr)], 0.8),
            (None, 1.4),
            (lambda: [FadeIn(rows[0], shift=0.2 * RIGHT)], 0.7),
            (lambda: [FadeIn(rows[1], shift=0.2 * RIGHT)], 0.7),
            (None, 1.4),
            (lambda: [flash(sa[0], A_C, 1.03), Indicate(rows[0][1], color=A_C, scale_factor=1.4)], 1.0),
            (lambda: [flash(sb[0], B_C, 1.03), Indicate(rows[1][1], color=B_C, scale_factor=1.4)], 1.0),
        ])

        self.steps("The config servers, a replica set of their own, keep this map of which range lives where.", [
            (lambda: [FadeIn(cfg_t, shift=0.2 * DOWN)], 0.8),
            (lambda: [flash(cfg, TEAL_M, 1.03)], 1.0),
        ])

        # ---- mongos ---------------------------------------------------------------------------------------
        m1 = mbox("mongos", PURPLE_M, w=1.9, h=0.7, size=24).move_to([-4.6, 0.85, 0])
        m2 = mbox("mongos", PURPLE_M, w=1.9, h=0.7, size=24).move_to([-2.0, 0.85, 0])
        a1 = Arrow(app.get_bottom(), m1.get_top(), buff=0.1, stroke_width=3, color=GREY_B, tip_length=0.2,
                   max_tip_length_to_length_ratio=0.5)
        a2 = Arrow(app.get_bottom(), m2.get_top(), buff=0.1, stroke_width=3, color=GREY_B, tip_length=0.2,
                   max_tip_length_to_length_ratio=0.5)
        cache = DashedLine(m2.get_right() + 0.12 * RIGHT, [cfg.get_left()[0] - 0.12, 0.85, 0], dash_length=0.1,
                           stroke_width=2, color=TEAL_M)
        cache_l = T("cached map", 20, TEAL_M).next_to(cache, UP, buff=0.1)
        self.steps("Your app never talks to a shard. It talks to mongos, a router that keeps a cached copy of that map.", [
            (lambda: [FadeIn(m1, shift=0.2 * DOWN), FadeIn(m2, shift=0.2 * DOWN)], 0.9),
            (lambda: [GrowArrow(a1), GrowArrow(a2)], 0.8),
            (None, 1.2),
            (lambda: [Create(cache), FadeIn(cache_l)], 0.9),
        ])

        def q_chip(text):
            return chip(text, YELLOW_M, 18, mono=True).move_to([-1.1, 3.0, 0])

        def to_shard(s):
            return s[0].get_top() + 0.08 * UP

        q1 = q_chip('{ _id: "pay-81002" }')
        self.steps("Find payment pay-81002. The filter has the shard key, so the router sends it only to the shard that owns that range.", [
            (lambda: [FadeIn(q1, shift=0.2 * DOWN)], 0.6),
            (lambda: [dot_run(app.get_bottom(), m2.get_top(), YELLOW_M, 0.7)], 0.8),
            (None, 0.8),
            (lambda: [Indicate(rows[1], color=YELLOW_M, scale_factor=1.06)], 0.9),
            (lambda: [dot_run(m2.get_bottom(), to_shard(sb), YELLOW_M, 0.9)], 1.0),
            (lambda: [flash(sb[0], YELLOW_M, 1.03)], 0.7),
            (lambda: [dot_run(to_shard(sb), m2.get_bottom(), B_C, 0.8)], 0.9),
        ])

        q2 = q_chip('{ merchantId: "M-0042" }')
        sg = T("scatter-gather", 24, RED_M).next_to(m2, RIGHT, buff=0.35).shift(0.75 * DOWN)
        self.steps("Find merchant M-0042's payments. That filter has no shard key, so the router asks every shard and merges "
                   "the answers. That's a scatter-gather query.", [
            (lambda: [FadeOut(q1), FadeIn(q2, shift=0.2 * DOWN)], 0.6),
            (lambda: [dot_run(app.get_bottom(), m2.get_top(), YELLOW_M, 0.7)], 0.8),
            (None, 0.9),
            (lambda: [dot_run(m2.get_bottom(), to_shard(sa), YELLOW_M, 0.9), dot_run(m2.get_bottom(), to_shard(sb), YELLOW_M, 0.9)], 1.0),
            (lambda: [flash(sa[0], YELLOW_M, 1.03), flash(sb[0], YELLOW_M, 1.03)], 0.7),
            (lambda: [dot_run(to_shard(sa), m2.get_bottom(), A_C, 0.8), dot_run(to_shard(sb), m2.get_bottom(), B_C, 0.8)], 0.9),
            (lambda: [FadeIn(sg, shift=0.2 * UP)], 0.6),
        ])

        # ---- a key that only goes up ----------------------------------------------------------------------
        q3 = q_chip('insert pay-90001, ...')
        hot = SurroundingRectangle(rows[1], color=RED_M, buff=0.08, corner_radius=0.06, stroke_width=2.5)

        def b_fill(f, col=B_C):
            return shard("shard2", "replica set", B_C, f, BX, fill_col=col)[3]

        self.steps("Now new payments arrive. Ids only go up, so every insert lands in the last chunk, and one shard takes them all.", [
            (lambda: [FadeOut(q2), FadeOut(sg), FadeIn(q3, shift=0.2 * DOWN)], 0.6),
            (lambda: [LaggedStart(*[dot_run(app.get_bottom(), m1.get_top(), YELLOW_M, 0.6) for _ in range(4)], lag_ratio=0.3)], 1.4),
            (lambda: [Create(hot)], 0.6),
            (lambda: [LaggedStart(*[dot_run(m1.get_bottom(), to_shard(sb), RED_M, 0.8) for _ in range(5)], lag_ratio=0.25),
                      Transform(sb[3], b_fill(0.75, RED_M))], 2.0),
            (lambda: [flash(sb[2][0], RED_M, 1.25)], 0.8),
        ])

        # ---- split and migrate ----------------------------------------------------------------------------
        split = VGroup(row(1, "pay-80000", "pay-90000", "shard2", B_C), row(2, "pay-90000", "MaxKey", "shard2", B_C))
        bal = chip("balancer", TEAL_M, 22).move_to([CFX, 0.15, 0])
        self.steps("When shard 2 holds 384 megabytes more, the balancer, on the config server primary, "
                   "cuts a range off that chunk and moves it to shard 1.", [
            (lambda: [FadeOut(q3), FadeOut(hot), Transform(sb[3], b_fill(0.75))], 0.7),
            (lambda: [flash(sb[3][1], B_C, 1.06), flash(sa[3][1], A_C, 1.06)], 1.2),
            (None, 1.2),
            (lambda: [FadeIn(bal, shift=0.2 * UP)], 0.7),
            (None, 1.6),
            (lambda: [FadeOut(rows[1], shift=0.15 * LEFT)], 0.4),
            (lambda: [LaggedStart(FadeIn(split[0], shift=0.15 * RIGHT), FadeIn(split[1], shift=0.15 * RIGHT), lag_ratio=0.4)], 0.8),
            (lambda: [Indicate(split[0], color=TEAL_M, scale_factor=1.06)], 0.9),
        ])
        rows = VGroup(rows[0], *split)

        moved = row(1, "pay-80000", "pay-90000", "shard1", A_C)
        # the range crosses the empty gap between the two shards, so it never passes over a label
        path = Line([BX - SW / 2 - 0.3, SHY, 0], [AX + SW / 2 + 0.3, SHY, 0])
        blk = Rectangle(width=0.5, height=0.3, stroke_width=0).set_fill(B_C, 0.9).move_to(path.get_start())

        def a_fill(f):
            return shard("shard1", "replica set", A_C, f, AX)[3]

        self.steps("Shard 1 copies the documents, the config servers record the new owner, and shard 2 deletes its copy. "
                   "But new payments still land on shard 2.", [
            (lambda: [flash(sb[3][1], B_C, 1.06)], 0.5),
            (lambda: [FadeIn(blk, shift=0.2 * LEFT)], 0.2),
            (lambda: [MoveAlongPath(blk, path)], 1.0),
            (lambda: [FadeOut(blk), Transform(sa[3], a_fill(0.6))], 0.6),
            (lambda: [Transform(rows[1], moved)], 0.9),
            (lambda: [Transform(sb[3], b_fill(0.6))], 0.8),
            (None, 0.7),
            (lambda: [LaggedStart(*[dot_run(m1.get_bottom(), to_shard(sb), RED_M, 0.7) for _ in range(3)], lag_ratio=0.3),
                      Indicate(rows[2], color=RED_M, scale_factor=1.06)], 1.4),
        ])

        # ---- hashed ---------------------------------------------------------------------------------------
        hdr2 = VGroup(M("hash(_id) range", 18, GREY_B).move_to([RX, 2.66, 0], aligned_edge=LEFT),
                      M("shard", 18, GREY_B).move_to([SX, 2.66, 0]))
        hrows = VGroup(row(0, "MinKey", "-4.6e18", "shard1", A_C), row(1, "-4.6e18", "0", "shard1", A_C),
                       row(2, "0", "4.6e18", "shard2", B_C), row(3, "4.6e18", "MaxKey", "shard2", B_C))
        q4 = q_chip('insert pay-90001, ...')
        self.steps("A hashed shard key fixes that. MongoDB hashes the id first. Ids next to each other get far-apart hashes, "
                   "so inserts spread over both shards.", [
            (lambda: [FadeOut(bal), Transform(hdr, hdr2), FadeOut(rows, shift=0.2 * LEFT)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.2 * RIGHT) for r in hrows], lag_ratio=0.2)], 1.2),
            (lambda: [FadeIn(q4, shift=0.2 * DOWN)], 0.6),
            (lambda: [LaggedStart(*[dot_run(app.get_bottom(), m1.get_top(), YELLOW_M, 0.6) for _ in range(4)], lag_ratio=0.3)], 1.3),
            (lambda: [LaggedStart(*[dot_run(m1.get_bottom(), to_shard(s), c, 0.8)
                                    for s, c in [(sa, A_C), (sb, B_C), (sb, B_C), (sa, A_C), (sa, A_C), (sb, B_C)]], lag_ratio=0.25),
                      LaggedStart(*[Indicate(hrows[i], color=YELLOW_M, scale_factor=1.05) for i in (1, 3, 2, 0)], lag_ratio=0.3)], 2.2),
        ])

        q5 = q_chip('{ _id: "pay-81002" }')
        self.steps("A lookup by id is still targeted, since the router can hash it too. Only a range of ids goes to every shard.", [
            (lambda: [FadeOut(q4), FadeIn(q5, shift=0.2 * DOWN)], 0.6),
            (lambda: [dot_run(app.get_bottom(), m2.get_top(), YELLOW_M, 0.7)], 0.8),
            (lambda: [Indicate(hrows[2], color=YELLOW_M, scale_factor=1.06)], 0.8),
            (lambda: [dot_run(m2.get_bottom(), to_shard(sb), YELLOW_M, 0.9)], 1.0),
            (lambda: [dot_run(to_shard(sb), m2.get_bottom(), B_C, 0.8)], 0.9),
        ])

        self.steps("So pick a shard key that your busiest reads filter on, with many values and no steady growth. mongos routes by it, "
                   "and the balancer keeps the shards even.", [
            (lambda: [FadeOut(q5)], 0.5),
            (None, 1.6),
            (lambda: [flash(m1, PURPLE_M, 1.1), flash(m2, PURPLE_M, 1.1)], 1.0),
            (None, 0.6),
            (lambda: [flash(sa[0], A_C, 1.03), flash(sb[0], B_C, 1.03)], 1.0),
        ])
        self.wait(0.6)
