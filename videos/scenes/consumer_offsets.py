from sfz import *

LX0, LP, LY = -4.84, 0.88, 2.0          # log: x of offset 0, pitch, row height
CWID, CHGT = 0.74, 0.62
CP = np.array([-3.7, -0.7, 0])          # the consumer
DP = np.array([3.7, -0.7, 0])           # the ledger database
BW, BH = 4.8, 1.8
HY = -0.8                               # records in hand
SQ, SQP, SQY = 0.38, 0.46, [-0.6, -1.1]  # ledger squares
STY, VY = -2.3, -3.05


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


def lx(k):
    return LX0 + LP * k


def cell(k, color=WHITE, done=False):
    r = RoundedRectangle(corner_radius=0.08, width=CWID, height=CHGT, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.1 if done else 0.14), 1).move_to([lx(k), LY, 0])
    return VGroup(r, M(str(k), 20, GREY_B if done else WHITE).move_to([lx(k), LY, 0]))


def pos_marker(k):
    tri = Triangle(color=BLUE_M, fill_opacity=1, stroke_width=0).scale(0.11).rotate(PI).move_to([lx(k), LY + 0.55, 0])
    lab = T(f"position {k}", 18, BLUE_M).next_to(tri, RIGHT, buff=0.12)
    return VGroup(tri, lab)


def com_marker(k):
    tri = Triangle(color=GOLD_M, fill_opacity=1, stroke_width=0).scale(0.11).move_to([lx(k), LY - 0.55, 0])
    lab = T(f"committed {k}", 18, GOLD_M).next_to(tri, RIGHT, buff=0.12)
    return VGroup(tri, lab)


def hx(i):
    return CP[0] + (i - 2) * 0.78


def hand(i, k, color=WHITE):
    r = RoundedRectangle(corner_radius=0.07, width=0.62, height=0.5, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([hx(i), HY, 0])
    return VGroup(r, M(str(k), 18, WHITE).move_to([hx(i), HY, 0]))


def sq(i, k, color=GREEN_M):
    x = DP[0] + (i % 8 - 3.5) * SQP
    y = SQY[i // 8]
    r = Square(SQ, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.2), 1).move_to([x, y, 0])
    return VGroup(r, M(str(k), 15, WHITE).move_to([x, y, 0]))


def box(c, title, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=BW if c is CP else 4.4, height=BH, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK, 1).move_to(c)
    return VGroup(r, T(title, 22).move_to(c + 0.65 * UP))


def status(s, color=GREY_B):
    return T(s, 22, color).move_to([0, STY, 0])


def verdict(x, s, color):
    return chip(s, color, 19).move_to([x, VY, 0])


class ConsumerOffsets(Base):
    """msg-07, section 2: a ledger consumer polls offsets 0 to 4, applies them, commits 5. With 5 to 9 in hand, commit
    first and crash after 5 and 6: the new consumer starts at 10, and 7, 8, 9 are never applied (at most once).
    Process first and crash before the commit: the new consumer starts at 5 and 5, 6 reach the ledger twice (at least
    once). An idempotency key stored with the payment, in one transaction, makes the replay a no-op."""

    def construct(self):
        self.title_card("Consumer offsets", "when you commit decides what a crash costs")

        title = T("Kafka: the payments topic, partition 0", 20, GREY_B).move_to([-6.5, 3.35, 0], aligned_edge=LEFT)
        cells = {k: cell(k) for k in range(12)}
        com = com_marker(0)
        self.steps("A ledger consumer reads payments from one partition of a Kafka topic. Kafka keeps the consumer's "
                   "bookmark, the committed offset. It's 0: the next record to read.", [
            (lambda: [FadeIn(title), LaggedStart(*[FadeIn(cells[k], shift=0.1 * LEFT) for k in cells], lag_ratio=0.06)], 1.2),
            "Kafka keeps",
            (lambda: [FadeIn(com, shift=0.1 * UP)], 0.6),
            "It's 0",
            (lambda: [glow(cells[0][0], GOLD_M, 1.1)], 0.8),
        ])

        cons = box(CP, "ledger consumer")
        db = box(DP, "ledger database")
        ap = Arrow([CP[0] + BW / 2 + 0.1, CP[1], 0], [DP[0] - 2.2 - 0.1, DP[1], 0], buff=0, stroke_width=3, color=GREY_B,
                   max_tip_length_to_length_ratio=0.12)
        apl = T("apply", 18, GREY_B).next_to(ap, UP, buff=0.12)
        pos = pos_marker(0)
        h = {}

        def poll(ks):
            for i, k in enumerate(ks):
                h[i] = hand(i, k)
            return [LaggedStart(*[TransformFromCopy(cells[k], h[i]) for i, k in enumerate(ks)], lag_ratio=0.15)]

        self.steps("The consumer polls, and Kafka hands it a batch, offsets 0 to 4. Its position, kept in memory, "
                   "jumps to 5 at once, before it has looked at a single record.", [
            (lambda: [FadeIn(cons), FadeIn(db), GrowArrow(ap), FadeIn(apl), FadeIn(pos, shift=0.1 * DOWN)], 0.8),
            "Kafka hands",
            (lambda: poll(range(5)), 1.2),
            "jumps to 5",
            (lambda: [Transform(pos, pos_marker(5))], 0.7),
        ])

        led = []

        def apply(i, k, color=GREEN_M, rt=None):
            s = sq(len(led), k, color)
            led.append(s)
            return [TransformFromCopy(h[i], s), h[i].animate.set_opacity(0.35)]

        def commit(k):
            return [Transform(com, com_marker(k)), *[Transform(cells[j], cell(j, done=True)) for j in range(k) if j < 12]]

        st0 = status("poll, process, commit, repeat")
        self.steps("It applies each payment to the ledger. Then it commits 5, the next offset to read, and Kafka saves it.", [
            (lambda: [LaggedStart(*[AnimationGroup(*apply(i, i)) for i in range(5)], lag_ratio=0.3)], 2.0),
            "Then it commits",
            (lambda: [*commit(5), *[FadeOut(h[i]) for i in range(5)]], 0.8),
            (lambda: [FadeIn(st0, shift=0.1 * UP)], 0.5),
        ])

        gap = Brace(VGroup(*[cells[k] for k in range(5, 10)]), DOWN, buff=0.62, color=GREY_B)
        gapl = T("in hand, not committed", 18, GREY_B).next_to(gap, DOWN, buff=0.1)
        self.steps("It polls again: 5 to 9. Now it holds records that Kafka still counts as unread. "
                   "If it crashes here, what happens depends on one choice: commit before processing, or after.", [
            (lambda: [FadeOut(st0)] + poll(range(5, 10)), 1.2),
            (lambda: [Transform(pos, pos_marker(10))], 0.6),
            "Now it holds",
            (lambda: [GrowFromCenter(gap), FadeIn(gapl)], 0.8),
        ])
        gap_sh = VGroup(gap, gapl)

        crash = T("crashed", 20, RED_M).move_to([CP[0], -1.35, 0])
        h1 = T("1. commit, then process", 22, WHITE).move_to([0, STY, 0])
        self.steps("First, commit before processing. It commits 10, processes 5 and 6, and crashes.", [
            (lambda: [FadeOut(gap_sh), FadeIn(h1, shift=0.1 * UP)], 0.6),
            "It commits 10",
            (lambda: commit(10), 0.8),
            "processes 5",
            (lambda: apply(0, 5), 0.6),
            (lambda: apply(1, 6), 0.6),
            "and crashes",
            (lambda: [cons[0].animate.set_stroke(RED_M), FadeIn(crash), *[FadeOut(h[i]) for i in range(5)]], 0.6),
        ])

        newc = T("new consumer: starts at 10", 18, GREY_B).move_to([CP[0], -1.35, 0])
        v1 = verdict(-3.4, "commit first: at most once", RED_M)
        self.steps("A new consumer starts from the committed offset, 10. Payments 7, 8 and 9 are never processed. "
                   "That's at most once: nothing twice, and some never.", [
            (lambda: [cons[0].animate.set_stroke(WHITE), ReplacementTransform(crash, newc)], 0.6),
            (lambda: [glow(com[0], GOLD_M, 1.3), Transform(pos, pos_marker(10))], 0.7),
            "Payments 7",
            (lambda: [*[Transform(cells[k], cell(k, RED_M)) for k in (7, 8, 9)]], 0.8),
            "That's at most once",
            (lambda: [FadeIn(v1, shift=0.1 * UP)], 0.6),
        ])

        h2 = T("2. process, then commit", 22, WHITE).move_to([0, STY, 0])

        def rewind():
            gone = led[5:]
            del led[5:]
            return [FadeOut(VGroup(*gone)), FadeOut(newc), Transform(h1, h2),
                    Transform(com, com_marker(5)), *[Transform(cells[k], cell(k)) for k in range(5, 10)]]

        crash2 = T("crashed", 20, RED_M).move_to([CP[0], -1.35, 0])
        self.steps("Now rewind to 5 and swap the order. It polls 5 to 9, processes 5 and 6, and crashes before it commits.", [
            (lambda: rewind(), 0.9),
            "It polls",
            (lambda: poll(range(5, 10)), 0.9),
            (lambda: [Transform(pos, pos_marker(10))], 0.4),
            "processes 5",
            (lambda: apply(0, 5), 0.6),
            (lambda: apply(1, 6), 0.6),
            "and crashes",
            (lambda: [cons[0].animate.set_stroke(RED_M), FadeIn(crash2), *[FadeOut(h[i]) for i in range(5)]], 0.6),
        ])

        newc2 = T("new consumer: starts at 5", 18, GREY_B).move_to([CP[0], -1.35, 0])
        twice = status("5 and 6 applied twice", RED_M)
        self.steps("The new consumer starts at 5 and gets the whole batch again. Payments 5 and 6 reach the ledger twice.", [
            (lambda: [cons[0].animate.set_stroke(WHITE), ReplacementTransform(crash2, newc2),
                      Transform(pos, pos_marker(5)), glow(com[0], GOLD_M, 1.3)], 0.7),
            (lambda: poll(range(5, 10)), 0.9),
            (lambda: [Transform(pos, pos_marker(10))], 0.4),
            "Payments 5 and 6",
            (lambda: [LaggedStart(AnimationGroup(*apply(0, 5, RED_M)), AnimationGroup(*apply(1, 6, RED_M)),
                                  *[AnimationGroup(*apply(i, k)) for i, k in ((2, 7), (3, 8), (4, 9))], lag_ratio=0.3)], 1.6),
            (lambda: [Transform(h1, twice)], 0.5),
        ])

        v2 = verdict(3.4, "commit after: at least once", GOLD_M)
        self.steps("That's at least once: nothing lost, and some records twice. For payments it's the right choice, "
                   "because a duplicate can be caught.", [
            (lambda: [*commit(10), *[FadeOut(h[i]) for i in range(5)]], 0.7),
            "That's at least once",
            (lambda: [FadeIn(v2, shift=0.1 * UP)], 0.6),
            "a duplicate can be caught",
            (lambda: [glow(led[7][0], RED_M, 1.2), glow(led[8][0], RED_M, 1.2)], 0.9),
        ])

        db2 = T("ledger: unique payment keys", 22).move_to(DP + 0.65 * UP)
        self.steps("Give each payment an idempotency key, its payment id. The ledger stores the key with the payment, "
                   "in the same transaction, and the key must be unique.", [
            (lambda: [Transform(db[1], db2), FadeOut(h1)], 0.8),
            "in the same transaction",
            (lambda: [*[glow(s[0], GREEN_M, 1.15) for s in led[:7]]], 1.0),
        ])

        def rewind2():
            gone = led[7:]
            del led[7:]
            return [FadeOut(VGroup(*gone)), Transform(com, com_marker(5)),
                    *[Transform(cells[k], cell(k)) for k in range(5, 10)], Transform(pos, pos_marker(5))]

        skip = status("5 and 6: key already there, skipped", GREEN_M)
        bounce = {}

        def replay(i):
            tgt = led[5 + i]
            ghost = sq(5 + i, 5 + i, RED_M)
            bounce[i] = ghost
            return [Succession(TransformFromCopy(h[i], ghost, run_time=0.6), FadeOut(ghost, scale=0.5, run_time=0.3))]

        self.steps("Replay the same crash. Payments 5 and 6 arrive again, their keys are already there, "
                   "and the ledger skips them.", [
            (lambda: rewind2(), 0.8),
            (lambda: poll(range(5, 10)), 0.9),
            (lambda: [Transform(pos, pos_marker(10))], 0.4),
            "their keys",
            (lambda: [*replay(0), *replay(1), glow(led[5][0], GREEN_M, 1.2), glow(led[6][0], GREEN_M, 1.2)], 0.9),
            "skips them",
            (lambda: [FadeIn(skip, shift=0.1 * UP), h[0].animate.set_opacity(0.35), h[1].animate.set_opacity(0.35)], 0.6),
        ])

        once = status("every payment applied once", GREEN_M)
        self.steps("Payments 7, 8 and 9 go in, it commits 10, and every payment has landed exactly once.", [
            (lambda: [LaggedStart(*[AnimationGroup(*apply(i, k)) for i, k in ((2, 7), (3, 8), (4, 9))], lag_ratio=0.3)], 1.2),
            "it commits 10",
            (lambda: [*commit(10), *[FadeOut(h[i]) for i in range(5)]], 0.7),
            "every payment",
            (lambda: [Transform(skip, once)], 0.6),
        ])

        self.steps("Commit after processing, so a crash replays instead of losing. "
                   "Make the write idempotent, so the replay does no harm.", [
            (lambda: [glow(v2[0], GOLD_M, 1.05), glow(com[0], GOLD_M, 1.3)], 1.0),
            "Make the write",
            (lambda: [glow(db[0], GREEN_M, 1.03)], 1.0),
        ])
        self.wait(0.6)
