from sfz import *

SAY.insert(0, (r"\bSMS\b", "S M S"))
SAY.insert(0, (r"\bc([123])\b", r"C \1"))

RX0, RDX, RY = -5.25, 1.5, 1.9               # records 0..7
RW, RH = 1.25, 0.75
ST_Y, DL_Y = 1.12, 0.78                       # state and delivery lines under each record
CXS, CY, CW, CH = {1: -4.2, 2: 0.0, 3: 4.2}, -1.3, 3.2, 1.3
CCOL = {1: BLUE_M, 2: TEAL_M, 3: PURPLE_M}
NOTE_Y = [-2.6, -3.15]


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def rx(k):
    return RX0 + k * RDX


def rec(k, state="available", owner=None, delivery=0):
    """Record k with its state and delivery count, coloured by state (or by the consumer holding its lock)."""
    color = {"available": GREY_B, "done": GREEN_M, "archived": RED_M}.get(state, CCOL.get(owner, GREY_B))
    label = {"locked": f"c{owner}, locked"}.get(state, state)
    r = RoundedRectangle(corner_radius=0.1, width=RW, height=RH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([rx(k), RY, 0])
    return VGroup(r, M(str(k), 26).move_to([rx(k), RY, 0]), T(label, 19, color).move_to([rx(k), ST_Y, 0]),
                  T(f"delivery {delivery}", 18, GREY_B if delivery else GREY_D).move_to([rx(k), DL_Y, 0]))


def cons(i, status="", scolor=GREY_B, color=None):
    color = color or CCOL[i]
    x = CXS[i]
    r = RoundedRectangle(corner_radius=0.14, width=CW, height=CH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, CY, 0])
    return VGroup(r, T(f"c{i}", 28).move_to([x, CY + 0.3, 0]), T(status or " ", 21, scolor).move_to([x, CY - 0.22, 0]))


def link(k, i):
    return Line([rx(k), DL_Y - 0.2, 0], [CXS[i], CY + CH / 2 + 0.08, 0])


def note(s, color=GREY_B, k=0):
    return T(s, 22, color).move_to([0, NOTE_Y[k], 0])


def clock(s, color=GREY_B):
    return right_at(M(s, 22, color), 6.4, 3.25)


class ShareGroups(Base):
    """msg-11, section 1 (with section 0's limit): texts take 200 ms; a consumer group gives one partition one owner,
    so six partitions cap the service at 30 texts a second against 300. A share group: the broker hands out records,
    each acquired under a 30 s lock with a delivery count; ACCEPT, RELEASE, an expired lock after a GC pause, and
    archiving after five deliveries. Order between records is what you give up."""

    def construct(self):
        self.title_card("Share groups", "many consumers on one partition, a lock on every record")

        plab = left_at(T("notifications, partition 0", 22, GREY_B), -6.15, 2.85)
        R = {k: rec(k) for k in range(8)}
        C = {i: cons(i) for i in (1, 2, 3)}
        self.steps("The notification service sends a text for every authorized payment. Each send takes about 200 "
                   "milliseconds, because the SMS provider is slow.", [
            (lambda: [FadeIn(plab), LaggedStart(*[FadeIn(R[k], shift=0.1 * LEFT) for k in range(8)], lag_ratio=0.1)], 1.3),
            "Each send",
            (lambda: [LaggedStart(*[FadeIn(C[i], scale=0.95) for i in (1, 2, 3)], lag_ratio=0.2)], 1.0),
        ])

        own = Arrow([0.75, DL_Y - 0.2, 0], [CXS[3] - 0.3, CY + CH / 2 + 0.08, 0], buff=0, stroke_width=3, color=PURPLE_M,
                    max_tip_length_to_length_ratio=0.08)
        self.steps("In a consumer group, each partition has exactly one owner. Here c3 reads the whole partition, and "
                   "the other two sit idle.", [
            (lambda: [GrowArrow(own), Transform(C[3], cons(3, "owns partition 0", WHITE))], 0.9),
            "Here c3",
            (lambda: [LaggedStart(*[flow(link(k, 3), PURPLE_M, 0.5) for k in range(8)], lag_ratio=0.15)], 1.6),
            "and the other two",
            (lambda: [Transform(C[1], cons(1, "idle", GREY_C, GREY_D)), Transform(C[2], cons(2, "idle", GREY_C, GREY_D))], 0.7),
        ])

        n1 = note("6 partitions: at most 6 busy consumers, 30 texts a second", GREY_B)
        n2 = note("sale day: 300 a second, the backlog grows by 270 every second", RED_M, 1)
        self.steps("The real topic has six partitions, so at most six busy consumers, each sending five texts a second: "
                   "30 in all. On a sale day 300 payments a second arrive, and the backlog grows by 270 every second.", [
            (lambda: [FadeIn(n1, shift=0.1 * UP)], 0.8),
            "On a sale day",
            (lambda: [FadeIn(n2, shift=0.1 * UP)], 0.8),
            "and the backlog",
            (lambda: [glow(C[1][0], RED_M), glow(C[2][0], RED_M)], 1.0),
        ])

        sg = note("share group “notify”: no owners", TEAL_M)
        self.steps("A share group drops the owner. The broker hands out records one at a time, so all three consumers "
                   "read the same partition.", [
            (lambda: [FadeOut(own), FadeOut(n1), FadeOut(n2), FadeIn(sg)], 0.8),
            "The broker",
            (lambda: [*[Transform(C[i], cons(i, "ready")) for i in (1, 2, 3)]], 0.8),
        ])

        clk = clock("10:00:00")
        hold = {1: (0, 1), 2: (2, 3), 3: (4, 5)}
        self.steps("A poll acquires records. Each one is locked to its consumer for 30 seconds, and its delivery count "
                   "goes up by one.", [
            (lambda: [FadeIn(clk), *[flow(link(k, i), CCOL[i], 0.6) for i, ks in hold.items() for k in ks]], 0.8),
            (lambda: [*[Transform(C[i], cons(i, f"holds {a}, {b}", WHITE)) for i, (a, b) in hold.items()],
                      *[Transform(R[k], rec(k, "locked", i, 0)) for i, ks in hold.items() for k in ks]], 0.7),
            "locked to",
            (lambda: [*[glow(R[k][0], CCOL[i], 1.08) for i, ks in hold.items() for k in ks]], 0.9),
            "and its delivery",
            (lambda: [*[Transform(R[k], rec(k, "locked", i, 1)) for i, ks in hold.items() for k in ks]], 0.7),
        ])

        self.steps("c2's texts go out, so it acknowledges both with accept. Records 2 and 3 are done.", [
            (lambda: [Transform(C[2], cons(2, "ACCEPT 2, 3", GREEN_M))], 0.6),
            (lambda: [flow(link(2, 2), GREEN_M, 0.6, back=True), flow(link(3, 2), GREEN_M, 0.6, back=True)], 0.7),
            "Records 2 and 3",
            (lambda: [Transform(R[2], rec(2, "done", None, 1)), Transform(R[3], rec(3, "done", None, 1)),
                      Transform(C[2], cons(2, "ready"))], 0.7),
        ])

        self.steps("c3 sends 4, but the provider times out on 5. Release hands 5 back, available for another try.", [
            (lambda: [flow(link(4, 3), GREEN_M, 0.6, back=True), Transform(R[4], rec(4, "done", None, 1))], 0.7),
            "times out",
            (lambda: [Transform(C[3], cons(3, "timeout on 5", RED_M))], 0.6),
            "Release",
            (lambda: [Transform(C[3], cons(3, "RELEASE 5", GOLD_M)), flow(link(5, 3), GOLD_M, 0.6, back=True)], 0.7),
            (lambda: [Transform(R[5], rec(5, "available", None, 1)), Transform(C[3], cons(3, "ready"))], 0.6),
        ])

        self.steps("Any member can take it next. c2 acquires 5 and 6, so record 5 gets its second delivery, on a "
                   "different consumer.", [
            "c2 acquires",
            (lambda: [flow(link(5, 2), TEAL_M, 0.6), flow(link(6, 2), TEAL_M, 0.6)], 0.7),
            (lambda: [Transform(R[5], rec(5, "locked", 2, 1)), Transform(R[6], rec(6, "locked", 2, 1)),
                      Transform(C[2], cons(2, "holds 5, 6", WHITE))], 0.6),
            "gets its second",
            (lambda: [Transform(R[5], rec(5, "locked", 2, 2))], 0.5),
            (lambda: [glow(R[5][0], GOLD_M, 1.1)], 0.8),
        ])

        t = ValueTracker(0)
        clk2 = always_redraw(lambda: clock(f"10:00:{int(t.get_value()):02d}", RED_M if t.get_value() >= 29.5 else GREY_B))
        self.steps("Now c1 freezes in a long garbage collection pause and never answers. At 30 seconds the broker ends "
                   "its locks, and 0 and 1 are available again. No rebalance needed.", [
            (lambda: [Transform(C[1], cons(1, "paused, no answer", GREY_C, GREY_D))], 0.7),
            "At 30 seconds",
            (lambda: [FadeOut(clk), FadeIn(clk2)], 0.1),
            (lambda: [t.animate(rate_func=linear).set_value(30)], 1.4),
            "and 0 and 1",
            (lambda: [Transform(R[0], rec(0, "available", None, 1)), Transform(R[1], rec(1, "available", None, 1))], 0.7),
            "No rebalance",
            (lambda: [glow(R[0][0], GREY_B, 1.08), glow(R[1][0], GREY_B, 1.08)], 0.8),
        ])
        clk2.clear_updaters()

        self.steps("c3 acquires them on their second delivery, and accepts both. A record that keeps failing is "
                   "archived after five deliveries, so it can't bounce forever.", [
            (lambda: [flow(link(0, 3), PURPLE_M, 0.6), flow(link(1, 3), PURPLE_M, 0.6)], 0.7),
            (lambda: [Transform(R[0], rec(0, "locked", 3, 2)), Transform(R[1], rec(1, "locked", 3, 2)),
                      Transform(C[3], cons(3, "holds 0, 1", WHITE))], 0.6),
            "and accepts",
            (lambda: [Transform(R[0], rec(0, "done", None, 2)), Transform(R[1], rec(1, "done", None, 2)),
                      Transform(C[3], cons(3, "ACCEPT 0, 1", GREEN_M)), Transform(R[6], rec(6, "done", None, 1))], 0.7),
            "A record that",
            (lambda: [Transform(C[3], cons(3, "ready")), Transform(C[2], cons(2, "RELEASE 5", GOLD_M)),
                      Transform(R[5], rec(5, "locked", 2, 3))], 0.5),
            (lambda: [Transform(R[5], rec(5, "locked", 2, 4))], 0.4),
            (lambda: [Transform(R[5], rec(5, "locked", 2, 5))], 0.4),
            "archived",
            (lambda: [Transform(R[5], rec(5, "archived", None, 5)), Transform(C[2], cons(2, "ready"))], 0.6),
        ])

        tag5 = T("card 7", 18, GOLD_M).move_to([rx(5), RY + RH / 2 + 0.25, 0])
        tag6 = T("card 7", 18, GOLD_M).move_to([rx(6), RY + RH / 2 + 0.25, 0])
        lost = note("same card: 6 went out, 5 never did", RED_M)
        self.steps("What you give up is order. If 5 and 6 were two texts about one card, 6 went out and 5 never did.", [
            (lambda: [FadeOut(sg), FadeIn(tag5, shift=0.1 * DOWN), FadeIn(tag6, shift=0.1 * DOWN)], 0.8),
            "6 went out",
            (lambda: [glow(R[6][0], GREEN_M, 1.08)], 0.7),
            "and 5 never",
            (lambda: [glow(R[5][0], RED_M, 1.08), FadeIn(lost, shift=0.1 * UP)], 0.8),
        ])

        rule = note("any free consumer takes the next record, under a lock", TEAL_M)
        self.steps("So use share groups for independent jobs like these texts, never for a ledger. Any free consumer "
                   "takes the next record under a lock, and per key order is the price.", [
            (lambda: [*[Transform(C[i], cons(i, "ready")) for i in (1, 2, 3)]], 0.7),
            "Any free consumer",
            (lambda: [Transform(lost, rule), Transform(R[7], rec(7, "locked", 1, 1)), flow(link(7, 1), BLUE_M, 0.7),
                      Transform(C[1], cons(1, "holds 7", WHITE))], 0.9),
            "per key order",
            (lambda: [glow(R[5][0], RED_M, 1.08), glow(R[6][0], GREEN_M, 1.08)], 0.9),
        ])
        self.wait(0.6)
