from sfz import *

SAY.insert(0, (r"\bpay-(\d+)", r"pay \1"))

X0, PITCH, CW, CH = -2.75, 0.94, 0.84, 0.6     # partition rows: left end, cell pitch, cell size
NCELL = 9
RY = [2.1, 0.0, -2.1]                         # ledger-entries 0, ledger-entries 1, __consumer_offsets
NAMES = ["ledger-entries, partition 0", "ledger-entries, partition 1", "__consumer_offsets (the group's bookmarks)"]
SVX, SVY, SVW = -5.25, 0.55, 2.55               # the ledger service
COX, COY = -5.25, -2.25                         # the transaction coordinator
READ_Y = 3.3                                    # what the read_committed reader of partition 0 gets


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along an arrow and stays invisible until its turn."""
    d = Dot(radius=0.07, color=color).move_to(path.get_start()).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1),
                      MoveAlongPath(d, Line(path.get_start(), path.get_end()), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


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


def rbox(x, y, w, h, color, fa=0.14):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3)
    white = ManimColor(color).to_hex().upper() == "#FFFFFF"
    return r.set_fill(BLACK if white else fill(color, fa), 1).move_to([x, y, 0])


def cx(i):
    return X0 + 0.1 + CW / 2 + i * PITCH


def row(r):
    w = NCELL * PITCH + 0.1
    track = RoundedRectangle(corner_radius=0.1, width=w, height=CH + 0.2, stroke_color=GREY_D, stroke_width=2)
    track.set_fill(BLACK, 1).move_to([X0 + w / 2, RY[r], 0])
    lab = M(NAMES[r], 17, GREY_B)
    lab.move_to([X0 + lab.width / 2, RY[r] + 0.68, 0])
    return VGroup(track, lab)


def cell(r, i, label, color, tcolor=WHITE):
    rect = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=color, stroke_width=2.5)
    rect.set_fill(fill(color, 0.22), 1).move_to([cx(i), RY[r], 0])
    t = fit(M(label, 17, tcolor), CW - 0.14).move_to(rect)
    num = M(str(i), 14, GREY_C).move_to([cx(i), RY[r] - 0.6, 0])
    return VGroup(rect, t, num)


def marker(r, i, kind):
    c = cell(r, i, kind, GREEN_M if kind == "commit" else RED_M)
    c[1].become(fit(M(kind, 15, GREEN_M if kind == "commit" else RED_M), CW - 0.14).move_to(c[0]))
    return c


def restate(c, color, tcolor=WHITE):
    return [c[0].animate.set_stroke(color).set_fill(fill(color, 0.22), 1), c[1].animate.set_color(tcolor)]


def sv_sub(s, color=GREY_B):
    return T(s, 17, color).move_to([SVX, SVY - 0.2, 0])


def reader(s, color=GREY_B):
    g = VGroup(M("read_committed reader of partition 0 gets:", 17, GREY_B), T(s, 20, color)).arrange(RIGHT, buff=0.25)
    return g.move_to([0.75, READ_Y, 0])


def lso(i, r=0):
    x = X0 + 0.1 + i * PITCH - (PITCH - CW) / 2
    ln = Line([x, RY[r] + 0.48, 0], [x, RY[r] - 0.48, 0], stroke_width=5, color=YELLOW_M)
    lab = T(f"last stable offset: {i}", 18, YELLOW_M).next_to(ln, DOWN, buff=0.35)
    return VGroup(ln, lab)


class KafkaTransactions(Base):
    """msg-10, section 1: the ledger service reads payments and writes entries to two partitions of ledger-entries plus
    its bookmark to __consumer_offsets. Without a transaction a crash between the writes duplicates four entries. With
    one, the entries and the bookmark sit in the log as an open transaction until the coordinator writes a COMMIT
    marker into each partition it touched. A read_committed reader stops at the last stable offset (an open
    transaction at offset 3, so even a plain fee record at 4 waits); an abort writes ABORT markers and the reader skips
    pay-4 and pay-5, then the retried batch commits."""

    def construct(self):
        self.title_card("Kafka transactions", "commit markers and the last stable offset")

        sv = VGroup(rbox(SVX, SVY, SVW, 1.0, TEAL_M), T("ledger service", 22).move_to([SVX, SVY + 0.2, 0]),
                    sv_sub("instance 1"))
        rows = [row(r) for r in range(3)]
        arrs = [Arrow([SVX + SVW / 2 + 0.06, SVY + 0.25 - 0.25 * r, 0], [X0 - 0.12, RY[r], 0], buff=0, stroke_width=3,
                      color=GREY_B, tip_length=0.2, max_tip_length_to_length_ratio=0.5) for r in range(3)]
        self.steps("A ledger service reads payments and writes an entry for each into two partitions. "
                   "Then it saves its bookmark, the next offset to read, in a third.", [
            (lambda: [FadeIn(sv)], 0.7),
            "into two partitions",
            (lambda: [FadeIn(rows[0]), FadeIn(rows[1]), GrowArrow(arrs[0]), GrowArrow(arrs[1])], 1.0),
            "Then it saves",
            (lambda: [FadeIn(rows[2]), GrowArrow(arrs[2])], 0.9),
        ])

        first = [cell(0, 0, "pay-0", GREY_B), cell(0, 1, "pay-2", GREY_B), cell(1, 0, "pay-1", GREY_B), cell(1, 1, "pay-3", GREY_B)]
        cross = tick(False, 0.3).move_to([SVX, SVY + 0.85, 0])
        self.steps("These are three separate writes. Say it writes four entries, then dies before it saves the bookmark.", [
            (lambda: [glow(a, YELLOW_M, 1.0) for a in arrs], 0.9),
            "Say it writes",
            (lambda: [flow(arrs[0], GREY_B, 0.6), flow(arrs[1], GREY_B, 0.6)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(c) for c in first], lag_ratio=0.2)], 0.9),
            "then dies",
            (lambda: [Transform(sv[2], sv_sub("crashed", RED_M)), sv[0].animate.set_stroke(RED_M), FadeIn(cross)], 0.7),
        ])

        dup = [cell(0, 2, "pay-0", RED_M), cell(0, 3, "pay-2", RED_M), cell(1, 2, "pay-1", RED_M), cell(1, 3, "pay-3", RED_M)]
        bm = cell(2, 0, "4", GREY_B)
        twice = chip("four payments debited twice", RED_M, 20).move_to([0.75, READ_Y, 0])
        self.steps("The next instance starts from the old bookmark and writes all four again. "
                   "Four payments are debited twice.", [
            (lambda: [FadeOut(cross), Transform(sv[2], sv_sub("instance 2")), sv[0].animate.set_stroke(TEAL_M)], 0.7),
            "and writes",
            (lambda: [flow(arrs[0], RED_M, 0.6), flow(arrs[1], RED_M, 0.6)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(c) for c in dup], lag_ratio=0.2)], 0.9),
            (lambda: [flow(arrs[2], GREY_B, 0.5)], 0.5),
            (lambda: [FadeIn(bm)], 0.4),
            "Four payments are",
            (lambda: [FadeIn(twice, shift=0.15 * UP)], 0.7),
        ])

        self.steps("A Kafka transaction makes the three writes one: all of them count, or none of them do.", [
            (lambda: [*[FadeOut(c) for c in first + dup], FadeOut(bm), FadeOut(twice), Transform(sv[2], sv_sub("instance 1"))], 0.9),
            "all of them",
            (lambda: [glow(r[0], YELLOW_M, 1.01) for r in rows], 1.0),
        ])

        t1 = [cell(0, 0, "pay-0", YELLOW_M), cell(0, 1, "pay-2", YELLOW_M), cell(1, 0, "pay-1", YELLOW_M), cell(1, 1, "pay-3", YELLOW_M)]
        b1 = cell(2, 0, "4", YELLOW_M)
        self.steps("The service begins a transaction. Its four entries go into the partitions at once, "
                   "marked as open. So does the new bookmark, 4.", [
            (lambda: [Transform(sv[2], sv_sub("transaction open", YELLOW_M))], 0.7),
            "Its four entries",
            (lambda: [flow(arrs[0], YELLOW_M, 0.6), flow(arrs[1], YELLOW_M, 0.6)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(c) for c in t1], lag_ratio=0.2)], 0.9),
            "So does",
            (lambda: [flow(arrs[2], YELLOW_M, 0.6)], 0.6),
            (lambda: [FadeIn(b1)], 0.5),
        ])

        co = VGroup(rbox(COX, COY, SVW, 1.0, GOLD_M), T("coordinator", 22).move_to([COX, COY + 0.2, 0]),
                    T("one of the brokers", 17, GREY_B).move_to([COX, COY - 0.2, 0]))
        cm1 = [marker(0, 2, "commit"), marker(1, 2, "commit"), marker(2, 1, "commit")]
        self.steps("On commit, the coordinator, one of the brokers, records the decision. "
                   "Then it writes a commit marker into every partition the transaction touched.", [
            (lambda: [Transform(sv[2], sv_sub("commit", GREEN_M))], 0.5),
            "the coordinator",
            (lambda: [FadeIn(co, shift=0.15 * UP)], 0.8),
            "records the decision",
            (lambda: [Transform(co[2], T("decided: commit", 17, GREEN_M).move_to([COX, COY - 0.2, 0]))], 0.6),
            "Then it writes",
            (lambda: [glow(co[0], GOLD_M, 1.04), LaggedStart(*[FadeIn(m, scale=1.3) for m in cm1], lag_ratio=0.25)], 1.2),
            (lambda: [*[a for c in t1 + [b1] for a in restate(c, GREEN_M)]], 0.7),
        ])

        rd = reader("pay-0, pay-2")
        self.steps("A marker takes an offset, but no reader ever gets it. "
                   "A reader set to read committed gets only committed records: now pay-0 and pay-2.", [
            (lambda: [*[glow(m[0], GREEN_M, 1.1) for m in cm1]], 1.0),
            "A reader set",
            (lambda: [FadeIn(rd, shift=0.15 * DOWN)], 0.8),
        ])

        t2 = [cell(0, 3, "pay-4", YELLOW_M), cell(1, 3, "pay-5", YELLOW_M)]
        fee = cell(0, 4, "fee", GREY_B)
        pl = T("a plain producer, no transaction", 17, GREY_B).move_to([cx(4) + 0.9, RY[0] - 1.0, 0])
        self.steps("The next transaction writes pay-4 and pay-5. "
                   "Then a plain producer, outside any transaction, appends a fee at offset 4.", [
            (lambda: [Transform(sv[2], sv_sub("transaction open", YELLOW_M)), Transform(co[2], T("open: pay-4, pay-5", 17, YELLOW_M).move_to([COX, COY - 0.2, 0]))], 0.7),
            "writes pay-4",
            (lambda: [flow(arrs[0], YELLOW_M, 0.6), flow(arrs[1], YELLOW_M, 0.6)], 0.6),
            (lambda: [FadeIn(t2[0]), FadeIn(t2[1])], 0.6),
            "Then a plain",
            (lambda: [FadeIn(pl)], 0.6),
            "appends",
            (lambda: [FadeIn(fee, shift=0.2 * DOWN)], 0.6),
        ])

        L = lso(3)
        self.steps("A read committed reader stops at the last stable offset, the first offset of the oldest open transaction: "
                   "here, 3. Even the fee waits, because Kafka hands out records in offset order.", [
            (lambda: [FadeOut(pl), Create(L[0])], 0.7),
            (lambda: [FadeIn(L[1])], 0.6),
            "here, 3",
            (lambda: [glow(t2[0][0], YELLOW_M, 1.1)], 0.8),
            "Even the fee",
            (lambda: [glow(fee[0], GREY_B, 1.1), Transform(rd[1], T("pay-0, pay-2, and it waits", 20, YELLOW_M).move_to(rd[1], aligned_edge=LEFT))], 1.0),
        ])

        am = [marker(0, 5, "abort"), marker(1, 4, "abort")]
        self.steps("Now a send times out, and the service aborts. Nothing is deleted: "
                   "the coordinator writes an abort marker into the two partitions it touched.", [
            (lambda: [Transform(sv[2], sv_sub("abort", RED_M))], 0.6),
            "Nothing is deleted",
            (lambda: [*[a for c in t2 for a in restate(c, RED_M, GREY_C)]], 0.8),
            "the coordinator writes",
            (lambda: [Transform(co[2], T("decided: abort", 17, RED_M).move_to([COX, COY - 0.2, 0])), glow(co[0], GOLD_M, 1.04)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(m, scale=1.3) for m in am], lag_ratio=0.3)], 0.9),
        ])

        L2 = lso(6)
        self.steps("The last stable offset moves on, and the reader skips pay-4 to get the fee. "
                   "A reader left on the default, read uncommitted, would take pay-4 too.", [
            (lambda: [Transform(L, L2)], 1.0),
            "and the reader skips",
            (lambda: [Transform(rd[1], T("pay-0, pay-2, fee", 20, GREEN_M).move_to(rd[1], aligned_edge=LEFT))], 0.8),
            "A reader left",
            (lambda: [glow(t2[0][0], RED_M, 1.1)], 0.9),
        ])

        t3 = [cell(0, 6, "pay-4", YELLOW_M), cell(1, 5, "pay-5", YELLOW_M)]
        b3 = cell(2, 2, "6", YELLOW_M)
        cm3 = [marker(0, 7, "commit"), marker(1, 6, "commit"), marker(2, 3, "commit")]
        L3 = lso(8)
        self.steps("The bookmark is still 4, so the service reads pay-4 and pay-5 again, "
                   "writes them in a new transaction with bookmark 6, and commits.", [
            (lambda: [Transform(sv[2], sv_sub("retry, transaction open", YELLOW_M)), glow(b1[0], GREEN_M, 1.1),
                      Transform(co[2], T("open: pay-4, pay-5", 17, YELLOW_M).move_to([COX, COY - 0.2, 0]))], 0.9),
            "writes them",
            (lambda: [FadeIn(t3[0]), FadeIn(t3[1]), FadeIn(b3)], 0.7),
            "and commits",
            (lambda: [Transform(co[2], T("decided: commit", 17, GREEN_M).move_to([COX, COY - 0.2, 0])),
                      LaggedStart(*[FadeIn(m, scale=1.3) for m in cm3], lag_ratio=0.2), Transform(sv[2], sv_sub("commit", GREEN_M))], 0.9),
            (lambda: [*[a for c in t3 + [b3] for a in restate(c, GREEN_M)], Transform(L, L3),
                      Transform(rd[1], T("pay-0, pay-2, fee, pay-4", 20, GREEN_M).move_to(rd[1], aligned_edge=LEFT))], 0.9),
        ])

        self.steps("Records land in the log before the decision. A marker decides, "
                   "and a read committed reader waits at the first record that isn't decided yet.", [
            (lambda: [*[glow(c[0], YELLOW_M, 1.08) for c in t1 + t2 + t3]], 1.1),
            "A marker decides",
            (lambda: [*[glow(m[0], GREEN_M if m in cm1 + cm3 else RED_M, 1.1) for m in cm1 + am + cm3]], 1.1),
            "and a read committed",
            (lambda: [glow(L[0], YELLOW_M, 1.05)], 1.0),
        ])
        self.wait(0.6)
