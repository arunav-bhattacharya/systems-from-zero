from sfz import *

SAY.insert(0, (r"\bpayment:(\d+)", r"payment \1"))
SAY.insert(0, (r"\bMOVED\b", "moved"))
SAY.insert(0, (r"\bASK\b", "ask"))
SAY.insert(0, (r"\bMSET\b", "M set"))
SAY.insert(0, (r"\bCROSSSLOT\b", "cross slot"))

BAR_Y, BAR_H, BX0, BX1 = 2.85, 0.5, -3.9, 6.0      # the slot bar
NX, NW, NH = 4.75, 3.1, 1.25                       # node boxes, a column on the right
NY = {1: 1.15, 2: -0.55, 3: -2.25}
NC = {1: BLUE_M, 2: TEAL_M, 3: PURPLE_M}
CX, CY = -5.3, -0.55                               # client
MID = -0.65                                        # centre of the free middle area
RANGES = {1: (0, 5460), 2: (5461, 10922), 3: (10923, 16383)}


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along an arrow (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
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


def sx(slot):
    return BX0 + (slot + 0.5) / 16384 * (BX1 - BX0)


def node(k, status=None, scolor=GREY_B):
    x, y = NX, NY[k]
    r = RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=NC[k], stroke_width=3)
    r.set_fill(fill(NC[k]), 1).move_to([x, y, 0])
    g = VGroup(r, T(f"node {k}", 22).move_to([x, y + 0.36, 0]), M(f"127.0.0.1:700{k}", 16, GREY_B).move_to([x, y + 0.02, 0]))
    g.add(nstatus(k, status or "", scolor))
    return g


def nstatus(k, s, color=GREY_B):
    return T(s, 17, color).move_to([NX, NY[k] - 0.36, 0])


def to_node(k, color=GREY_B):
    a = np.array([CX + 0.95, CY, 0])
    b = np.array([NX - NW / 2 - 0.08, NY[k], 0])
    return Arrow(a, b, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.03)


def marker(slot, color=WHITE, label=True):
    x = sx(slot)
    tk = Rectangle(width=0.1, height=BAR_H + 0.16, stroke_color=color, stroke_width=2).set_fill(color, 1).move_to([x, BAR_Y, 0])
    g = VGroup(tk)
    if label:
        g.add(T(f"slot {slot:,}", 18, color).move_to([x, BAR_Y - BAR_H / 2 - 0.32, 0]))
    return g


def mid(s, y, color=WHITE, size=19, mono=True):
    return (M if mono else T)(s, size, color).move_to([MID, y, 0])


class ClusterSlots(Base):
    """cache-10, sections 0 to 2: 16,384 slots over three primaries; payment:42 is slot 9055 on node 2. Node 1 answers
    MOVED; a cluster client keeps the slot table. Slot 9055 migrates to node 3: node 2 answers ASK for a key that left,
    one command goes to node 3 with ASKING, the table stays; then MOVED. MSET over slots 9055 and 13182 is refused with
    CROSSSLOT although node 3 holds both; {merchant:7} keys both hash to slot 10890."""

    def construct(self):
        self.title_card("Redis Cluster: slots, MOVED and ASK", "16,384 hash slots spread over three primaries")

        cli = box("client", WHITE, w=1.8, h=0.9, size=24).move_to([CX, CY, 0])
        one = box("Redis", RED_M, w=2.6, h=1.2, size=26).move_to([NX, NY[2], 0])
        need = VGroup(T("needs 40 GB of memory", 19, RED_M), T("one thread for every command", 19, RED_M)).arrange(DOWN, buff=0.15)
        need.move_to([NX, NY[3] + 0.05, 0])
        nodes = {k: node(k) for k in (1, 2, 3)}
        q = mid("payment:42", 0.0, GOLD_M, 24)
        qm = T("?", 30, GOLD_M).next_to(q, RIGHT, buff=0.2)
        self.steps("One Redis runs every command on one thread, in one machine's memory. "
                   "When the payment keys outgrow it, you split them across three primaries. So where does payment:42 live?", [
            (lambda: [FadeIn(cli), FadeIn(one)], 0.7),
            "in one machine's",
            (lambda: [FadeIn(need, shift=0.1 * UP), glow(one[0], RED_M, 1.04)], 0.9),
            "you split them",
            (lambda: [FadeOut(need), FadeOut(one), FadeIn(nodes[2]), FadeIn(nodes[1]), FadeIn(nodes[3])], 1.0),
            "So where",
            (lambda: [FadeIn(q, shift=0.1 * RIGHT), FadeIn(qm)], 0.7),
        ])

        modc = chip("hash mod 3, then add a 4th server: 3 keys in 4 move", RED_M, 19).move_to([MID, -2.6, 0])
        self.steps("Hash the key mod three, and adding a fourth server later moves three keys in four.", [
            (lambda: [FadeIn(modc, shift=0.1 * UP)], 0.8),
            "moves three",
            (lambda: [glow(modc[0], RED_M, 1.04)], 0.8),
        ])

        segs, slabs = {}, {}
        for k, (a, b) in RANGES.items():
            x0, x1 = sx(a) - 0.5 * (BX1 - BX0) / 16384, sx(b) + 0.5 * (BX1 - BX0) / 16384
            segs[k] = Rectangle(width=x1 - x0, height=BAR_H, stroke_color=NC[k], stroke_width=2).set_fill(fill(NC[k], 0.35), 1)
            segs[k].move_to([(x0 + x1) / 2, BAR_Y, 0])
            slabs[k] = T(f"{a:,} to {b:,}", 17, NC[k]).move_to([segs[k].get_x(), BAR_Y + BAR_H / 2 + 0.22, 0])
        btitle = VGroup(T("16,384", 24, WHITE), T("hash slots", 19, GREY_B)).arrange(DOWN, buff=0.1).move_to([-5.3, BAR_Y, 0])
        bar = Rectangle(width=BX1 - BX0, height=BAR_H, stroke_color=GREY_B, stroke_width=2).move_to([(BX0 + BX1) / 2, BAR_Y, 0])
        self.steps("Redis Cluster puts a fixed layer in between: 16,384 hash slots. Each primary owns a range of them.", [
            (lambda: [FadeOut(modc), Create(bar), FadeIn(btitle)], 0.8),
            "Each primary",
            (lambda: [LaggedStart(*[AnimationGroup(FadeIn(segs[k]), FadeIn(slabs[k]), glow(nodes[k][0], NC[k], 1.04))
                                    for k in (1, 2, 3)], lag_ratio=0.5)], 1.6),
        ])

        calc = mid("CRC16(payment:42) mod 16384 = 9055", 1.25, WHITE, 18)
        m9 = marker(9055, TEAL_M)
        pick = Arrow([sx(9055), BAR_Y - BAR_H / 2 - 0.55, 0], [NX - NW / 2 + 0.15, NY[2] + NH / 2 + 0.05, 0], buff=0,
                     stroke_width=2.5, color=TEAL_M, max_tip_length_to_length_ratio=0.06)
        self.steps("A key's slot is a checksum of the key, mod 16,384. payment:42 lands in slot 9,055, which node two owns.", [
            (lambda: [FadeOut(qm), FadeIn(calc, shift=0.1 * UP)], 0.8),
            "payment:42 lands",
            (lambda: [FadeIn(m9, shift=0.2 * DOWN)], 0.7),
            "which node two",
            (lambda: [GrowArrow(pick), glow(nodes[2][0], TEAL_M, 1.04)], 0.9),
        ])

        a1 = to_node(1)
        mv = M("MOVED 9055 127.0.0.1:7002", 18, RED_M).move_to([0.6, -0.2, 0])
        a2 = to_node(2, GREEN_M)
        self.steps("Send it to node one, and node one doesn't forward it. It answers MOVED: slot 9,055 is on node two, ask there.", [
            (lambda: [FadeOut(pick), FadeOut(calc), q.animate.move_to([CX, CY + 0.95, 0]).scale(0.75)], 0.7),
            (lambda: [GrowArrow(a1)], 0.5),
            (lambda: [flow(a1, GOLD_M, 0.7)], 0.7),
            "It answers",
            (lambda: [flow(a1, RED_M, 0.7, back=True), FadeIn(mv)], 0.8),
            "ask there",
            (lambda: [GrowArrow(a2), flow(a2, GREEN_M, 0.7)], 0.9),
        ])

        tab = VGroup(T("slot table", 17, GREY_B),
                     M("0 to 5460      7001", 15, BLUE_M), M("5461 to 10922  7002", 15, TEAL_M), M("10923 to 16383 7003", 15, PURPLE_M))
        tab.arrange(DOWN, buff=0.1, aligned_edge=LEFT)
        tab_r = SurroundingRectangle(tab, buff=0.15, corner_radius=0.08, stroke_color=GREY_B, stroke_width=2)
        tabg = VGroup(tab_r, tab).move_to([CX + 0.25, -2.35, 0])
        self.steps("So a cluster client loads the slot table, works out each slot itself, and goes straight to the owner.", [
            (lambda: [FadeOut(mv), FadeOut(a1)], 0.5),
            (lambda: [FadeIn(tabg, shift=0.1 * UP)], 0.8),
            "works out",
            (lambda: [Indicate(tab[2], color=YELLOW_M, scale_factor=1.06)], 0.8),
            "and goes straight",
            (lambda: [flow(a2, GREEN_M, 0.7), flow(a2, GREEN_M, 0.7, back=True)], 0.9),
        ])

        mig = Arrow([NX - 1.0, NY[2] - NH / 2 - 0.04, 0], [NX - 1.0, NY[3] + NH / 2 + 0.04, 0], buff=0, stroke_width=3,
                    color=GOLD_M, max_tip_length_to_length_ratio=0.3)
        self.steps("Now the operator moves slot 9,055 to node three. Its keys copy across in batches, "
                   "so for a while each node holds some of them.", [
            (lambda: [a2.animate.set_color(GREY_B), Transform(m9, marker(9055, GOLD_M))], 0.7),
            (lambda: [Transform(nodes[2][3], nstatus(2, "9055: migrating", GOLD_M)),
                      Transform(nodes[3][3], nstatus(3, "9055: importing", GOLD_M))], 0.8),
            "Its keys copy",
            (lambda: [GrowArrow(mig)], 0.5),
            (lambda: [LaggedStart(*[flow(mig, GOLD_M, 0.5) for _ in range(4)], lag_ratio=0.45)], 1.6),
        ])

        ask = mid("ASK 9055 127.0.0.1:7003", 0.0, GOLD_M, 18)
        a3 = to_node(3, GOLD_M)
        asking = M("ASKING, then GET payment:42", 16, GOLD_M).move_to([-0.9, -2.3, 0])
        keep = T("table unchanged", 17, GREY_B).next_to(tabg, UP, buff=0.12)
        self.steps("Ask node two for a key that already left, and it answers ASK: send just this command to node three, "
                   "and keep your table, because the slot hasn't moved yet.", [
            (lambda: [flow(a2, GOLD_M, 0.7)], 0.7),
            "and it answers",
            (lambda: [flow(a2, GOLD_M, 0.7, back=True), FadeIn(ask)], 0.8),
            "send just this",
            (lambda: [GrowArrow(a3), FadeIn(asking)], 0.7),
            (lambda: [flow(a3, GOLD_M, 0.8)], 0.8),
            "and keep your table",
            (lambda: [glow(tab_r, GREY_B, 1.04), FadeIn(keep)], 0.8),
        ])

        mv2 = M("MOVED 9055 127.0.0.1:7003", 18, RED_M).move_to([0.6, -0.2, 0])
        reload = T("table reloaded", 17, GREEN_M).next_to(tabg, UP, buff=0.12)
        self.steps("When the last key is across, node three owns the slot, and node two answers MOVED from then on.", [
            (lambda: [FadeOut(ask), FadeOut(asking), FadeOut(keep), FadeOut(a3), LaggedStart(*[flow(mig, GOLD_M, 0.4) for _ in range(2)], lag_ratio=0.5)], 0.9),
            "node three owns",
            (lambda: [FadeOut(mig), Transform(m9, marker(9055, PURPLE_M)),
                      Transform(nodes[2][3], nstatus(2, "")), Transform(nodes[3][3], nstatus(3, "owns 9055 now", PURPLE_M)),
                      Transform(tab[3], M("10923 to 16383 7003", 15, PURPLE_M).move_to(tab[3]))], 0.9),
            "and node two",
            (lambda: [flow(a2, GOLD_M, 0.6)], 0.6),
            (lambda: [flow(a2, RED_M, 0.6, back=True), FadeIn(mv2)], 0.7),
            (lambda: [FadeIn(reload), glow(tab_r, GREEN_M, 1.04)], 0.6),
        ])

        ms = mid("MSET payment:42 ok payment:43 ok", 1.25, WHITE, 18)
        m13 = marker(13182, PURPLE_M)
        cs = chip("CROSSSLOT", RED_M, 18, mono=True).move_to([MID, -2.55, 0])
        a3b = to_node(3)
        self.steps("Commands that name several keys need them in one slot. This MSET names slots 9,055 and 13,182, "
                   "so Redis refuses it with CROSSSLOT, even though both sit on node three today.", [
            (lambda: [FadeOut(mv2), FadeOut(reload), FadeOut(a2), FadeOut(q), Transform(nodes[3][3], nstatus(3, ""))], 0.6),
            (lambda: [FadeIn(ms, shift=0.1 * UP)], 0.6),
            "This MSET",
            (lambda: [FadeIn(m13, shift=0.2 * DOWN), Indicate(m9, color=YELLOW_M)], 0.8),
            "so Redis refuses",
            (lambda: [GrowArrow(a3b), flow(a3b, WHITE, 0.6)], 0.8),
            (lambda: [flow(a3b, RED_M, 0.6, back=True), FadeIn(cs)], 0.7),
            "even though",
            (lambda: [glow(nodes[3][0], PURPLE_M, 1.04)], 0.8),
        ])

        def tagged(rest, y):
            k = VGroup(M("{merchant:7}", 19, GOLD_M), M(rest, 19, GREY_B)).arrange(RIGHT, buff=0.04)
            k.move_to([MID, y, 0])
            return k

        kp = tagged(":payments", 1.25)
        kr = tagged(":refunds", 0.7)
        m10 = marker(10890, TEAL_M)
        tl = T("only the part in braces is hashed", 18, GOLD_M).move_to([MID, 0.15, 0])
        a2b = to_node(2, GREEN_M)
        okm = chip("MSET, MULTI and scripts work", GREEN_M, 18).move_to([MID, -1.6, 0])
        self.steps("A hash tag fixes it. Only the part inside the braces is hashed, so both of a merchant's keys "
                   "land in slot 10,890, together.", [
            (lambda: [FadeOut(ms), FadeOut(cs), FadeOut(a3b), FadeOut(m13), FadeOut(m9)], 0.6),
            (lambda: [FadeIn(kp), FadeIn(kr)], 0.7),
            "Only the part",
            (lambda: [FadeIn(tl), Indicate(kp[0], color=YELLOW_M), Indicate(kr[0], color=YELLOW_M)], 0.9),
            "land in slot",
            (lambda: [FadeIn(m10, shift=0.2 * DOWN)], 0.7),
            (lambda: [GrowArrow(a2b), glow(nodes[2][0], TEAL_M, 1.04)], 0.7),
            (lambda: [FadeIn(okm, shift=0.1 * UP)], 0.6),
        ])

        self.steps("A key hashes to a slot, a slot belongs to one node, and keys that must change together share a hash tag.", [
            (lambda: [Indicate(m10[0], color=YELLOW_M, scale_factor=1.3)], 0.8),
            "a slot belongs",
            (lambda: [glow(segs[2], TEAL_M, 1.0), glow(nodes[2][0], TEAL_M, 1.04)], 0.9),
            "and keys that",
            (lambda: [Indicate(kp[0], color=YELLOW_M), Indicate(kr[0], color=YELLOW_M)], 0.9),
        ])
        self.wait(0.6)
