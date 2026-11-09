from sfz import *

SRC_X, SRC_W = -5.35, 2.1                  # sources
CNT_X, CNT_W, CNT_H = 1.3, 2.2, 3.8         # the counter, tall enough to take both inputs
SNK_X, SNK_W = 5.25, 2.3                    # the sink
MID = 0.2                                   # the counter's and the sink's centre line
YC = [1.6, -1.2]                            # channel 0 and channel 1
HEAD_X, SPC = -0.2, 0.6                     # a channel's head (next to the counter) and its spacing
ST_Y, TOP = -3.0, 3.3                       # checkpoint storage, status line
RC = [BLUE_M, TEAL_M]                       # records from source 0 and source 1
B_C = YELLOW_M


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def op(label, sub, x, y, w, h, color, mono_sub=False, ly=0.2):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to([x, y, 0])
    s = (M(sub, 18, GREY_B) if mono_sub else T(sub, 19, GREY_B)).move_to([x, y - ly, 0])
    return VGroup(r, T(label, 24).move_to([x, y + ly, 0]), s)


def rec(ch, n):
    r = RoundedRectangle(corner_radius=0.07, width=0.44, height=0.44, stroke_color=RC[ch], stroke_width=2.5).set_fill(fill(RC[ch], 0.3), 1)
    return VGroup(r, M(str(n), 18).move_to(r))


def barrier():
    bar = Line([0, -0.32, 0], [0, 0.32, 0]).set_stroke(B_C, 7)
    return VGroup(bar, T("B1", 18, B_C).move_to([0, 0.55, 0]))


def is_bar(m):
    return isinstance(m[0], Line)


def at(m, p):
    """Animate a record (by its centre) or a barrier (by its bar) to p."""
    p = np.array(p, dtype=float)
    return m.animate.shift(p - (m[0].get_center() if is_bar(m) else m.get_center()))


def place(m, p):
    p = np.array(p, dtype=float)
    return m.shift(p - (m[0].get_center() if is_bar(m) else m.get_center()))


def pos(ch, k):
    return [HEAD_X - SPC * k, YC[ch], 0]


class BarrierSnapshots(Base):
    """stream-07, section 1: two sources feed a keyed counter, which feeds a sink. Checkpoint 1: sources record offsets
    7 and 7 and inject barrier B1; the counter aligns (blocks input 0 while 7 and 8 wait), snapshots 14 = 7 + 7, forwards
    B1; the sink commits 14 updates. Crash at 17; restore 14, rewind both sources to 7, replay, 17 again, each once."""

    def construct(self):
        self.title_card("Checkpoints with barriers", "a snapshot of a running stream job")

        srcs = [op(f"source {i}", "offset 7", SRC_X, YC[i], SRC_W, 1.0, WHITE, mono_sub=True) for i in range(2)]
        for s in srcs:
            s[0].set_fill(BLACK, 1)
        cnt = op("counter", "9 counted", CNT_X, MID, CNT_W, CNT_H, GOLD_M, ly=0.25)
        snk = op("sink", "open transaction", SNK_X, MID, SNK_W, 1.1, GREEN_M)
        lines = [Line([SRC_X + SRC_W / 2 + 0.05, y, 0], [CNT_X - CNT_W / 2 - 0.05, y, 0], stroke_width=2, color=GREY_D) for y in YC]
        sline = Line([CNT_X + CNT_W / 2 + 0.05, MID, 0], [SNK_X - SNK_W / 2 - 0.05, MID, 0], stroke_width=2, color=GREY_D)
        chans = [[rec(0, n) for n in (4, 5, 6)], [rec(1, n) for n in (5, 6)]]
        for ch in range(2):
            for k, m in enumerate(chans[ch]):
                place(m, pos(ch, k))
        count = [9]
        park = [0, 0]                           # 1 while a barrier waits at the head of that channel
        parked = [None, None]

        def cstat(text, color=GREY_B, size=22):
            return T(text, size, color).move_to([CNT_X, MID - 0.25, 0])

        cnt.remove(cnt[2])
        cnt.add(cstat("9 counted"))

        def set_count(n):
            count[0] = n
            return Transform(cnt[2], cstat(f"{n} counted"))

        def sstat(i, n, color=GREY_B):
            return M(f"offset {n}", 18, color).move_to([SRC_X, YC[i] - 0.2, 0])

        def adv(ch):
            """The record at the head of channel ch goes into the counter; the rest move up one place."""
            it = chans[ch].pop(0)
            anims = [it.animate.move_to([CNT_X - CNT_W / 2 + 0.1, YC[ch], 0]).set_opacity(0), set_count(count[0] + 1)]
            anims += [at(m, pos(ch, k + park[ch])) for k, m in enumerate(chans[ch])]
            return anims

        def arrive(ch):
            """The barrier at the head of channel ch has reached the counter: it waits there, and so does what is behind it."""
            parked[ch] = chans[ch].pop(0)
            park[ch] = 1
            return [Indicate(parked[ch][1], color=B_C)]

        def release():
            anims = [FadeOut(b) for b in parked if b is not None]
            park[0] = park[1] = 0
            anims += [at(m, pos(ch, k)) for ch in range(2) for k, m in enumerate(chans[ch])]
            return anims

        def emit(ch, n, off):
            r = place(rec(ch, n), pos(ch, len(chans[ch]) + park[ch]))
            chans[ch].append(r)
            return [FadeIn(r, shift=0.3 * RIGHT), Transform(srcs[ch][2], sstat(ch, off))]

        def inject():
            anims = []
            for ch, b in enumerate(bars):
                place(b, pos(ch, len(chans[ch])))
                chans[ch].append(b)
                anims.append(FadeIn(b, shift=0.3 * RIGHT))
            return anims

        self.steps("A stream job counts payments per card. Two sources read payment events from Kafka, "
                   "a counter adds them up, and a sink writes the results out.", [
            "Two sources",
            (lambda: [FadeIn(srcs[0]), FadeIn(srcs[1])], 0.8),
            "a counter",
            (lambda: [Create(lines[0]), Create(lines[1]), FadeIn(cnt)], 0.8),
            "and a sink",
            (lambda: [Create(sline), FadeIn(snk)], 0.8),
        ])

        self.steps("Each source keeps an offset: how far it has read into its log. Both are at 7, "
                   "and the counter has counted 9 so far. Five more are on their way.", [
            "Each source keeps",
            (lambda: [Indicate(srcs[0][2], color=YELLOW_M), Indicate(srcs[1][2], color=YELLOW_M)], 1.0),
            "and the counter",
            (lambda: [Indicate(cnt[2], color=GOLD_M)], 0.9),
            "Five more",
            (lambda: [*[FadeIn(m, shift=0.2 * RIGHT) for m in chans[0] + chans[1]]], 0.9),
        ])

        sto = RoundedRectangle(corner_radius=0.14, width=12.8, height=0.95, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        sto.move_to([0, ST_Y, 0])
        sto_l = T("durable checkpoint storage", 20, GREY_B)
        sto_l.move_to([-6.2 + sto_l.width / 2, ST_Y, 0])
        sto_v = T("no checkpoint yet", 22, GREY_C).move_to([1.6, ST_Y, 0])
        self.steps("If the machine dies, the count in memory is gone. Recovery needs a saved count, "
                   "and the offsets from the same moment.", [
            (lambda: [glow(cnt[0], RED_M, 1.02)], 1.0),
            "Recovery needs",
            (lambda: [FadeIn(sto), FadeIn(sto_l), FadeIn(sto_v)], 0.9),
        ])

        status = chip("stop everything, then save: the job stalls", RED_M, 22).move_to([0, TOP, 0])
        status2 = chip("save while payments keep flowing", GREEN_M, 22).move_to([0, TOP, 0])
        self.steps("Stopping the job to save would stall it. So the snapshot is taken while payments keep flowing.", [
            (lambda: [FadeIn(status, shift=0.15 * DOWN)], 0.8),
            "So the snapshot",
            (lambda: [FadeTransform(status, status2)], 0.8),
        ])

        bars = [barrier(), barrier()]
        cp1 = chip("checkpoint 1 starts", B_C, 22).move_to([0, TOP, 0])
        v1 = T("checkpoint 1: offsets 7, 7", 22, WHITE).move_to([1.6, ST_Y, 0])
        self.steps("Checkpoint 1 starts. Each source writes down its offset, 7 and 7, and sends a marker called a barrier "
                   "down its channel, behind the payments it has already sent.", [
            (lambda: [FadeTransform(status2, cp1)], 0.8),
            "Each source writes",
            (lambda: [Indicate(srcs[0][2], color=B_C), Indicate(srcs[1][2], color=B_C)], 0.8),
            (lambda: [FadeOut(sto_v)], 0.3),
            (lambda: [FadeIn(v1)], 0.5),
            "and sends a marker",
            (lambda: inject(), 0.9),
        ])

        aft = T("after", 18, GREY_B).move_to([pos(0, 3)[0] - 0.9, YC[0] - 0.48, 0])
        bef = T("before", 18, GREY_B).move_to([pos(0, 1)[0], YC[0] - 0.48, 0])
        self.steps("A barrier never overtakes a payment, so it splits each channel in two: before the checkpoint, and after.", [
            (lambda: [*[Indicate(b[1], color=B_C) for b in bars]], 0.9),
            "before the checkpoint",
            (lambda: [FadeIn(bef)], 0.6),
            "and after",
            (lambda: [FadeIn(aft)], 0.6),
        ])

        blocked = T("blocked", 18, RED_M).move_to([HEAD_X - 0.3, YC[0] - 0.48, 0])
        seen = T("B1 in on input 0", 18, B_C).move_to([CNT_X, MID - 0.75, 0])
        al = chip("alignment", B_C, 22).move_to([0, TOP, 0])
        self.steps("Source 0's barrier reaches the counter first. The counter stops reading that input, "
                   "because payments 7 and 8 behind it belong after the checkpoint.", [
            (lambda: [FadeOut(aft), FadeOut(bef), *adv(0), *adv(1), *emit(0, 7, 8), *emit(1, 7, 8)], 0.7),
            (lambda: [*adv(0), *emit(0, 8, 9)], 0.6),
            (lambda: [*adv(0)], 0.5),
            (lambda: [*arrive(0), FadeIn(seen)], 0.6),
            "The counter stops",
            (lambda: [FadeIn(blocked), FadeTransform(cp1, al)], 0.7),
            "because payments 7 and 8",
            (lambda: [*[Indicate(m, color=RED_M) for m in chans[0]]], 1.0),
        ])

        self.steps("It keeps reading the other input until that barrier arrives too. This wait is called alignment.", [
            (lambda: [*adv(1)], 0.7),
            (lambda: [*arrive(1), Transform(seen, T("B1 on both inputs", 18, B_C).move_to(seen))], 0.7),
            "This wait",
            (lambda: [glow(al[0], B_C, 1.05)], 0.9),
        ])

        v2 = T("checkpoint 1: offsets 7, 7, counter 14", 22, WHITE).move_to([1.6, ST_Y, 0])
        snap = T("14", 22, GOLD_M).move_to([CNT_X, MID - 0.25, 0])
        b_out = place(barrier(), [CNT_X + CNT_W / 2 + 0.35, MID, 0])
        match = cstat("14 = 7 + 7", GOLD_M)
        self.steps("Now the counter has counted 14, seven from each source, the same as the saved offsets. "
                   "It saves 14 and passes the barrier on.", [
            (lambda: [Transform(cnt[2], match)], 0.8),
            "the same as",
            (lambda: [Indicate(v1, color=B_C)], 0.9),
            "It saves 14",
            (lambda: [FadeIn(snap)], 0.05),
            (lambda: [snap.animate.move_to([2.6, ST_Y + 0.62, 0]).set_opacity(0), FadeOut(v1)], 0.8),
            (lambda: [FadeIn(v2)], 0.5),
            "and passes",
            (lambda: [*release(), FadeOut(seen), FadeOut(blocked), FadeIn(b_out, shift=0.2 * RIGHT),
                      Transform(cnt[2], cstat("14 counted"))], 0.8),
        ])

        done = chip("checkpoint 1 complete", GREEN_M, 22).move_to([0, TOP, 0])
        v3 = T("checkpoint 1 complete: offsets 7, 7, counter 14", 22, GREEN_M).move_to([1.4, ST_Y, 0])
        world = T("world sees: 14 updates", 19, GREEN_M).move_to([SNK_X, MID + 1.05, 0])
        self.steps("The sink holds its writes in a transaction. When the barrier reaches it, checkpoint 1 is complete "
                   "and the sink commits 14 updates.", [
            (lambda: [Indicate(snk[2], color=GREEN_M)], 0.9),
            "When the barrier",
            (lambda: [at(b_out, [SNK_X - SNK_W / 2 - 0.3, MID, 0])], 0.9),
            "checkpoint 1 is complete",
            (lambda: [FadeOut(b_out), FadeTransform(al, done), FadeOut(v2)], 0.5),
            (lambda: [FadeIn(v3)], 0.5),
            "and the sink commits",
            (lambda: [Transform(snk[2], T("committed 14", 19, GREEN_M).move_to([SNK_X, MID - 0.2, 0])), FadeIn(world, shift=0.15 * UP)], 0.8),
        ])

        crash = chip("the machine dies", RED_M, 22).move_to([0, TOP, 0])
        x = tick(False, 0.35).move_to([CNT_X, MID + 1.15, 0])
        self.steps("The counter reaches 17, and then the machine dies. "
                   "The count, the channels and the sink's open transaction are lost.", [
            (lambda: [*adv(0), *adv(1), *emit(0, 9, 10), *emit(1, 8, 9),
                      Transform(snk[2], T("open: 2 updates", 19, GREY_B).move_to([SNK_X, MID - 0.2, 0]))], 0.7),
            (lambda: [*adv(0), Transform(snk[2], T("open: 3 updates", 19, GREY_B).move_to([SNK_X, MID - 0.2, 0]))], 0.7),
            "and then the machine",
            (lambda: [FadeTransform(done, crash), cnt[0].animate.set_stroke(RED_M), Create(x)], 0.8),
            "The count",
            (lambda: [Transform(cnt[2], cstat("state lost", RED_M)), *[FadeOut(m) for m in chans[0] + chans[1]],
                      Transform(snk[2], T("open writes lost", 19, RED_M).move_to([SNK_X, MID - 0.2, 0]))], 1.0),
            (lambda: [chans[0].clear() or chans[1].clear() or Wait(0.01)], 0.01),
        ])

        rest = chip("restore from checkpoint 1", GREEN_M, 22).move_to([0, TOP, 0])
        up14 = T("14", 22, GOLD_M).move_to([2.6, ST_Y + 0.75, 0])
        ups = [M("7", 18, GREEN_M).move_to([-3.4 + 0.4 * i, ST_Y + 0.75, 0]) for i in range(2)]
        self.steps("Kafka still has the input, and storage has checkpoint 1. "
                   "The counter loads 14, and each source rewinds to offset 7.", [
            (lambda: [glow(srcs[0][0], WHITE, 1.04), glow(srcs[1][0], WHITE, 1.04)], 0.9),
            "and storage has",
            (lambda: [glow(sto, GREEN_M, 1.01), FadeTransform(crash, rest)], 0.9),
            "The counter loads",
            (lambda: [FadeOut(x), cnt[0].animate.set_stroke(GOLD_M), FadeIn(up14)], 0.3),
            (lambda: [up14.animate.move_to([CNT_X, MID - 0.25, 0]).set_opacity(0), Transform(cnt[2], cstat("14 counted")),
                      Transform(snk[2], T("new transaction", 19, GREY_B).move_to([SNK_X, MID - 0.2, 0]))], 0.9),
            "and each source",
            (lambda: [*[FadeIn(u) for u in ups]], 0.2),
            (lambda: [ups[0].animate.move_to(srcs[0][2]).set_opacity(0), ups[1].animate.move_to(srcs[1][2]).set_opacity(0),
                      Transform(srcs[0][2], sstat(0, 7, GREEN_M)), Transform(srcs[1][2], sstat(1, 7, GREEN_M))], 1.0),
        ])
        count[0] = 14

        self.steps("Payments 7 and up go through a second time, but none of them were in the 14. "
                   "Each one counts once, and the count is 17 again.", [
            (lambda: [*emit(0, 7, 8), *emit(1, 7, 8)], 0.6),
            (lambda: [*emit(0, 8, 9)], 0.5),
            "but none of them",
            (lambda: [*[Indicate(m, color=GREEN_M) for m in chans[0] + chans[1]]], 0.9),
            "Each one counts once",
            (lambda: [*adv(0), *adv(1)], 0.7),
            (lambda: [*adv(0)], 0.7),
            "and the count",
            (lambda: [Indicate(cnt[2], color=GOLD_M)], 0.9),
        ])

        self.steps("Some payments were processed twice. Each one still counted once.", [
            (lambda: [glow(srcs[0][0], WHITE, 1.04), glow(srcs[1][0], WHITE, 1.04)], 0.9),
            "Each one still",
            (lambda: [glow(cnt[0], GOLD_M, 1.02)], 1.0),
        ])
        self.wait(0.6)
