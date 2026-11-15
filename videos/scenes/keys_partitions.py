from sfz import *

SAY.insert(0, (r"\b[Mm]urmur2\b", "murmur two"))

PX, PY = -5.0, 2.3                          # the producer
RX0, RPITCH = 2.6, 0.64                     # partition rows: y of row 0 and the pitch
LOGL, LOGR = -1.75, 5.6                     # left and right edge of each row's log
LBX = -2.55                                 # row labels
STL, STY = -2.45, -3.0                      # the "processed" strip: label and chips
CW, CH = 1.5, 0.46
GOLD, BLUE, PURP, OTHER = GOLD_M, BLUE_M, PURPLE_M, GREY_B


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


def ry(i):
    return RX0 - RPITCH * i


def slot(k):
    return LOGL + 0.85 + 1.6 * k


def row(i):
    log = RoundedRectangle(corner_radius=0.1, width=LOGR - LOGL, height=0.56, stroke_color=GREY_D, stroke_width=2)
    log.set_fill(BLACK, 1).move_to([(LOGL + LOGR) / 2, ry(i), 0])
    return VGroup(log, T(f"partition {i}", 18, GREY_B).move_to([LBX, ry(i), 0]))


def rec(text, color, x, y):
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.22), 1).move_to([x, y, 0])
    return VGroup(r, T(text, 18).move_to([x, y, 0])).set_z_index(3)


def at(m, i, k):
    """Animation: move record m into row i, slot k."""
    return m.animate.move_to([slot(k), ry(i), 0])


def line(s, y, color=WHITE, size=16):
    return M(s, size, color).move_to([PX, y, 0])


class KeysPartitions(Base):
    """msg-05, sections 0 to 3: round robin puts acct-17's authorization in partition 0 and its capture in partition 1,
    and a faster consumer processes the capture first. The default partitioner hashes the key: murmur2 of acct-17 is
    -1871546916, the sign bit cleared gives 275936732, and % 6 = 2. One key, one partition, in send order; across
    partitions a consumer may read 2, 5, 1, 3, 4. Growing to 8 partitions moves about 3 keys in 4 (acct-17: 2 to 4), so
    its refund lands in partition 4 and can be processed before the capture still waiting in partition 2."""

    def construct(self):
        self.title_card("Keys, partitions and order", "how a producer picks the partition, and which order you keep")

        pbox = RoundedRectangle(corner_radius=0.14, width=2.9, height=1.1, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
        pbox.move_to([PX, PY, 0])
        ptit = T("payment service", 22).move_to([PX, PY + 0.2, 0])
        psub = T("producer", 18, GREY_B).move_to([PX, PY - 0.22, 0])
        rows = [row(i) for i in range(8)]
        topic = T("payments topic: 6 partitions, 6 logs", 20, GREY_B).move_to([LOGL, 3.35, 0], aligned_edge=LEFT)
        q_auth = rec("auth", GOLD, PX - 0.78, 1.35)
        q_cap = rec("capture", GOLD, PX + 0.78, 1.35)
        self.steps("Your payment service sends an authorization, then a capture, for account 17. "
                   "The topic has six partitions, six separate logs. Which one gets each record?", [
            (lambda: [FadeIn(pbox), FadeIn(ptit), FadeIn(psub)], 0.6),
            (lambda: [FadeIn(q_auth, shift=0.1 * DOWN)], 0.4),
            (lambda: [FadeIn(q_cap, shift=0.1 * DOWN)], 0.4),
            "The topic",
            (lambda: [FadeIn(topic), LaggedStart(*[FadeIn(rows[i], shift=0.1 * LEFT) for i in range(6)], lag_ratio=0.12)], 1.2),
            "Which one",
            (lambda: [glow(q_auth[0], GOLD, 1.1), glow(q_cap[0], GOLD, 1.1)], 0.8),
        ])

        rule = T("rule: next partition in turn", 18, GREY_B).move_to([PX, 0.8, 0])
        self.steps("The simplest rule is round robin, each record to the next partition. "
                   "The authorization lands in partition 0, and the capture in partition 1.", [
            (lambda: [FadeIn(rule)], 0.6),
            "The authorization",
            (lambda: [at(q_auth, 0, 0)], 0.8),
            "and the capture",
            (lambda: [at(q_cap, 1, 0)], 0.8),
        ])

        slab = T("processed, in order:", 18, GREY_B).move_to([LOGL, STL, 0], aligned_edge=LEFT)
        p_cap = rec("capture", GOLD, slot(0), STY)
        p_auth = rec("auth", GOLD, slot(1), STY)
        bad = chip("a capture with no authorization", RED_M, 18).move_to([3.9, STY, 0])
        self.steps("Each partition is read by its own consumer, at its own pace. "
                   "If partition 1's consumer is ahead, the capture is processed first, for a payment that was never authorized.", [
            (lambda: [FadeIn(slab)], 0.6),
            "If partition 1's",
            (lambda: [glow(rows[1][0], GOLD, 1.02)], 0.7),
            (lambda: [TransformFromCopy(q_cap, p_cap)], 0.9),
            (lambda: [p_cap[0].animate.set_stroke(RED_M), FadeIn(bad, shift=0.1 * LEFT)], 0.6),
            "never authorized",
            (lambda: [TransformFromCopy(q_auth, p_auth)], 0.9),
        ])

        psub8 = T("producer, 8 instances", 18, GREY_B).move_to(psub)
        shadows = VGroup(*[pbox.copy().set_stroke(GREY_D, 2).shift(d * np.array([0.1, 0.1, 0])) for d in (2, 1)])
        shadows.set_z_index(-1)
        self.steps("So all of one account's records must go to one partition. "
                   "And all eight instances of the service must pick the same one, without asking each other.", [
            (lambda: [FadeOut(VGroup(q_auth, q_cap, p_cap, p_auth, bad, slab))], 0.7),
            "And all eight",
            (lambda: [FadeIn(shadows), Transform(psub, psub8)], 0.8),
            "without asking",
            (lambda: [glow(pbox, WHITE, 1.03)], 0.8),
        ])

        rule2 = T("rule: hash the key", 18, GOLD).move_to(rule)
        l1 = line("key: acct-17", 0.25, GOLD, 18)
        l2 = line("murmur2 → -1871546916", -0.35)
        l3 = line("sign bit off → 275936732", -0.95)
        l4 = line("275936732 % 6 = 2", -1.55, GOLD, 18)
        self.steps("The producer hashes the record's key, the account id. Murmur2 turns the key into a 32-bit number. "
                   "The producer clears the sign bit and takes the remainder by six: 2.", [
            (lambda: [Transform(rule, rule2)], 0.6),
            "the account id",
            (lambda: [FadeIn(l1, shift=0.1 * DOWN)], 0.6),
            "Murmur2",
            (lambda: [FadeIn(l2, shift=0.1 * DOWN)], 0.7),
            "clears the sign",
            (lambda: [FadeIn(l3, shift=0.1 * DOWN)], 0.7),
            "takes the remainder",
            (lambda: [FadeIn(l4, shift=0.1 * DOWN)], 0.7),
            (lambda: [glow(rows[2][0], GOLD, 1.02), rows[2][1].animate.set_color(GOLD)], 0.8),
        ])

        sends = [("1 auth", GOLD, 2, 0), ("2 auth", BLUE, 0, 0), ("3 capture", GOLD, 2, 1), ("4 auth", PURP, 1, 0),
                 ("5 capture", BLUE, 0, 1)]
        recs = [rec(t, c, PX, 1.35) for t, c, _, _ in sends]

        def send(n):
            t, c, i, k = sends[n]
            return [(lambda: [FadeIn(recs[n])], 0.2), (lambda: [at(recs[n], i, k)], 0.6)]

        self.steps("Same key, same number, same partition, from every instance, every time. "
                   "The authorization and the capture line up in partition 2, in the order they were sent.", [
            *send(0), *send(1),
            "every time",
            *send(2), *send(3), *send(4),
            "line up",
            (lambda: [glow(recs[0][0], GOLD, 1.1), glow(recs[2][0], GOLD, 1.1)], 0.9),
        ])

        others = [rec("auth", OTHER, slot(k), ry(i)) for i, k in ((3, 0), (3, 1), (4, 0), (5, 0), (5, 1))]
        self.steps("Other accounts hash to other partitions, so the work spreads across all six.", [
            (lambda: [glow(recs[1][0], BLUE, 1.1), glow(recs[3][0], PURP, 1.1), glow(recs[4][0], BLUE, 1.1)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(o, shift=0.2 * RIGHT) for o in others], lag_ratio=0.2)], 1.2),
        ])

        slab2 = T("one consumer reads, in this order:", 18, GREY_B).move_to([LOGL, STL, 0], aligned_edge=LEFT)
        order = [1, 4, 0, 2, 3]
        reads = [rec(sends[n][0], sends[n][1], slot(j), STY) for j, n in enumerate(order)]
        self.steps("Across partitions there's no order. A consumer might read partition 0 first, records 2 and 5, then 1 and 3. "
                   "Each account is still in order. The topic as a whole is not.", [
            (lambda: [FadeIn(slab2)], 0.6),
            "A consumer might",
            (lambda: [TransformFromCopy(recs[1], reads[0]), TransformFromCopy(recs[4], reads[1])], 0.9),
            "then 1 and 3",
            (lambda: [TransformFromCopy(recs[0], reads[2]), TransformFromCopy(recs[2], reads[3])], 0.9),
            (lambda: [TransformFromCopy(recs[3], reads[4])], 0.6),
            "Each account",
            (lambda: [*[glow(reads[j][0], GREEN_M, 1.1) for j in (2, 3)]], 0.7),
            (lambda: [*[glow(reads[j][0], GREEN_M, 1.1) for j in (0, 1)]], 0.7),
            "The topic as a whole",
            (lambda: [*[reads[j][0].animate.set_stroke(RED_M) for j in range(5)]], 0.7),
        ])

        topic8 = T("payments topic: 8 partitions", 20, GREY_B).move_to(topic, aligned_edge=LEFT)
        l4b = line("275936732 % 8 = 4", -1.55, GOLD, 18)
        moved = chip("about 3 keys in 4 move", RED_M, 18).move_to([PX, -2.45, 0])
        self.steps("Now grow the topic from six partitions to eight. The hash stays the same, but the remainder changes. "
                   "About three keys in four move, and account 17 now maps to partition 4.", [
            (lambda: [FadeOut(VGroup(*reads)), FadeOut(slab2)], 0.6),
            (lambda: [Transform(topic, topic8), FadeIn(rows[6], shift=0.1 * LEFT), FadeIn(rows[7], shift=0.1 * LEFT)], 0.9),
            "The hash stays",
            (lambda: [Indicate(l2, color=WHITE, scale_factor=1.08)], 0.6),
            "the remainder changes",
            (lambda: [Transform(l4, l4b)], 0.8),
            "About three keys",
            (lambda: [FadeIn(moved, shift=0.1 * UP)], 0.6),
            "now maps",
            (lambda: [rows[2][1].animate.set_color(GREY_B), rows[4][1].animate.set_color(GOLD), glow(rows[4][0], GOLD, 1.02)], 0.8),
        ])

        refund = rec("6 refund", GOLD, PX, 1.35)
        slab3 = T("processed, in order:", 18, GREY_B).move_to([LOGL, STL, 0], aligned_edge=LEFT)
        pr_ref = rec("6 refund", GOLD, slot(0), STY)
        pr_cap = rec("3 capture", GOLD, slot(1), STY)
        bad2 = chip("a refund before its capture", RED_M, 18).move_to([3.9, STY, 0])
        self.steps("Its old records stay in partition 2, and its refund goes to 4. "
                   "If partition 2's consumer is behind, the refund is processed before the capture.", [
            (lambda: [glow(recs[0][0], GOLD, 1.1), glow(recs[2][0], GOLD, 1.1)], 0.8),
            "and its refund",
            (lambda: [FadeIn(refund)], 0.2),
            (lambda: [at(refund, 4, 1)], 0.7),
            "If partition 2's",
            (lambda: [FadeIn(slab3)], 0.4),
            (lambda: [TransformFromCopy(refund, pr_ref)], 0.8),
            "before the capture",
            (lambda: [TransformFromCopy(recs[2], pr_cap), pr_ref[0].animate.set_stroke(RED_M), FadeIn(bad2, shift=0.1 * LEFT)], 0.9),
        ])

        self.steps("Order lives inside one partition. "
                   "Choose the key for the order you need, and fix the partition count up front.", [
            (lambda: [glow(rows[2][0], GOLD, 1.02)], 0.8),
            "Choose the key",
            (lambda: [Indicate(l1, color=GOLD, scale_factor=1.1)], 0.8),
            "fix the partition count",
            (lambda: [*[glow(rows[i][0], WHITE, 1.01) for i in range(8)]], 1.0),
        ])
        self.wait(0.6)
