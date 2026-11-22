from sfz import *

SAY.insert(0, (r"\bpay-(\d+)", r"pay \1"))
SAY.insert(0, (r"\bp(\d+)\b", r"P \1"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RULE_Y = 3.2                                   # the rule chip
NY, NW, NH = 0.95, 3.0, 2.4                    # node boxes
NX3 = [-3.4, 0.0, 3.4]
NX4 = [-5.1, -1.7, 1.7, 5.1]
BAND = 2.6                                     # copies travel along this line, above the nodes
SLOT = [(-0.62, 0.25), (0.62, 0.25), (-0.62, -0.55), (0.62, -0.55)]   # locker slots, relative to a node's centre
TL_Y, TB_Y = -0.62, -1.42                      # the table's label, the table's cells
KEY_Y, BAR_Y, CAP_Y = -2.42, -2.88, -3.27
NAMES = "ABCD"
NC = [BLUE_M, TEAL_M, PURPLE_M, GREEN_M]


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

    # captions and keyed labels: put() swaps a label in a named place, drop() fades it
    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0]))

    def uncap(self):
        return self.drop("cap")

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
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(w, h, color, at, a=0.14):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(
        fillc(color, a), 1).move_to(at)


def rule(s, color=WHITE):
    return mbox(s, color, h=0.56, size=22).move_to([0, RULE_Y, 0])


# ---- the hook: ten machines, then eleven ----
HX10 = [-5.175 + 1.15 * i for i in range(10)]
HX11 = [-5.75 + 1.15 * i for i in range(11)]
HY = 0.75


def machine(i, x, new=False):
    c = GREEN_M if new else GREY_B
    return VGroup(rbox(0.95, 1.0, c, [x, HY, 0], 0.12), T("new" if new else str(i), 22, GREEN_M if new else WHITE).move_to([x, HY, 0]))


# ---- the main picture ----
def node_box(k, x):
    return VGroup(rbox(NW, NH, NC[k], [x, NY, 0]), T(NAMES[k], 26).move_to([x, NY + 0.88, 0]))


def locker(p, k, at):
    r = RoundedRectangle(corner_radius=0.07, width=1.0, height=0.6, stroke_color=NC[k], stroke_width=2.5)
    r.set_fill(fillc(NC[k], 0.28), 1).move_to(at)
    hole = VGroup(Circle(radius=0.05, stroke_width=0).set_fill(GREY_A, 1), Line(DOWN * 0.0, DOWN * 0.11, stroke_width=2.5, color=GREY_A))
    hole.move_to(at + np.array([0.33, 0, 0]))
    return VGroup(r, M(f"p{p}", 20).move_to(at + np.array([-0.1, 0, 0])), hole).set_z_index(2)


def slot_at(x, j):
    return np.array([x + SLOT[j][0], NY + SLOT[j][1], 0])


CX = [-5.61 + 1.02 * i for i in range(12)]


def cell(p, k):
    at = np.array([CX[p], TB_Y, 0])
    r = RoundedRectangle(corner_radius=0.08, width=0.92, height=0.82, stroke_color=GREY_C, stroke_width=2).set_fill(BLACK, 1).move_to(at)
    return VGroup(r, M(f"p{p}", 16, GREY_B).move_to(at + 0.18 * UP), letter(k, p))


def letter(k, p, s=None, color=None):
    return T(s or NAMES[k], 24, color or NC[k]).move_to([CX[p], TB_Y - 0.17, 0])


def keynote(name, p, k, x, color=None):
    t = VGroup(M(f"{name}:", 22, GOLD_M), M(f"p{p}, on", 22), M(NAMES[k], 22, color or NC[k])).arrange(RIGHT, buff=0.18)
    return t.move_to([x, KEY_Y, 0])


class Rebalancing(Base):
    """shard-03, section 1. Ten machines on hash mod 10 get an eleventh: hash mod 11 moves 91,032 of 100,000 payments
    when the new machine needs about 9,100. The left-luggage office: numbered lockers (partitions), attendants (nodes),
    the number on the key (hash mod P, fixed) and the manager's list (the table). Twelve partitions on A, B, C; D joins
    and takes p9, p10 and p11 whole, copied while serving; pay-7 moves with p9, pay-81701 stays in p2 on C. Where the
    picture breaks (gigabytes, not keys), the names, the real stores, the catch (P is chosen once; 480 vs 512), the
    moral and a check."""

    def construct(self):
        self.slots = {}
        self.title_card("One new machine, one share", "fixed partitions: number the lockers once, move them whole")

        # ---------------- scene 1: one more machine ----------------
        ms = [machine(i, HX10[i]) for i in range(10)]
        r10 = rule("machine = hash(id) mod 10")
        self.steps("The payments company keeps its payments on ten machines. Each payment lives on machine number hash mod 10.", [
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.15 * UP) for m in ms], lag_ratio=0.08)], 1.2),
            "Each payment",
            (lambda: [FadeIn(r10, shift=0.1 * DOWN)], 0.6),
        ])
        pay = chip("pay-42", GOLD_M, 22, mono=True).move_to([HX10[2], 2.1, 0])
        self.steps("Turn the payment's id into a big random-looking number, its hash, divide by 10, and keep the remainder.", [
            (lambda: [FadeIn(pay, shift=0.1 * DOWN)], 0.5),
            "divide by 10",
            (lambda: [pay.animate.move_to([HX10[2], HY + 0.85, 0]).scale(0.8)], 0.7),
            "keep the remainder",
            (lambda: [glow(ms[2][0], YELLOW_M, 1.06)], 0.8),
            (lambda: [FadeOut(pay)], 0.3),
        ])
        new = machine(10, HX11[10], new=True)
        r11 = rule("machine = hash(id) mod 11", YELLOW_M)
        self.steps("The busiest shopping day of the year is a week away, and an eleventh machine has just arrived.", [
            "an eleventh",
            (lambda: [*[m.animate.move_to([HX11[i], HY, 0]) for i, m in enumerate(ms)]], 0.8),
            (lambda: [FadeIn(new, shift=0.3 * LEFT)], 0.6),
        ])
        qm = T("?", 60, YELLOW_M).move_to([0, -1.1, 0])
        self.steps("The plan fits on one line: switch to hash mod 11, and copy every payment whose answer changed. "
                   "So how many payments move? Hold your guess.", [
            "switch to",
            (lambda: [Transform(r10, r11)], 0.7),
            "So how many",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.6)

        # ---------------- scene 2: nine in ten pack up ----------------
        share = T("fair share for the new machine: about 9,100", 26, GREEN_M).move_to([0, -0.9, 0])
        self.steps("The new machine needs only its fair share, one payment in eleven. Out of 100,000 payments, that's about 9,100.", [
            (lambda: [FadeOut(qm), glow(new[0], GREEN_M, 1.06)], 0.8),
            "Out of",
            (lambda: [FadeIn(share, shift=0.1 * UP)], 0.6),
        ])
        rng = np.random.default_rng(3)
        pairs = [(int(a), int(b)) for a, b in rng.choice(10, (14, 2)) if a != b][:10] + [(1, 10), (6, 10)]

        def hop(a, b):
            pa, pb = np.array([HX11[a], HY + 0.5, 0]), np.array([HX11[b], HY + 0.5, 0])
            arc = ArcBetweenPoints(pa, pb, angle=-PI / 2.2 if b > a else PI / 2.2)
            d = Dot(radius=0.08, color=GREEN_M if b == 10 else YELLOW_M).move_to(pa)
            return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, arc, run_time=0.9), FadeOut(d, run_time=0.1))

        moved = T("hash mod 11 moves 91,032 of 100,000", 26, RED_M).move_to([0, -1.6, 0])
        self.steps("Now count what hash mod 11 actually moves. 91,032. Nine payments in ten pack up and leave, "
                   "and most of them just go from one old machine to another.", [
            "Now count",
            (lambda: [LaggedStart(*[hop(a, b) for a, b in pairs], lag_ratio=0.15)], 2.6),
            "91,032",
            (lambda: [FadeIn(moved, shift=0.1 * UP)], 0.5),
            "most of them",
            (lambda: [LaggedStart(*[hop(a, b) for a, b in pairs[:10]], lag_ratio=0.12)], 2.2),
        ])
        landed = T("only 9,150 of them land on the new machine", 22, GREY_B).move_to([0, -2.2, 0])
        self.steps("It's like hiring one new cashier and making every cashier in the shop swap tills.", [
            (lambda: [FadeIn(landed, shift=0.1 * UP)], 0.6),
            "swap tills",
            (lambda: [*[m.animate(rate_func=there_and_back).shift(0.12 * UP) for m in ms]], 0.8),
        ])
        tb = T("3 TB stored: 2.7 TB copied, when 270 GB would do", 24, RED_M).move_to([0, -2.8, 0])
        self.steps("On three terabytes of payments, that's 2.7 terabytes of copying, when 270 gigabytes would do. "
                   "Wouldn't it be nice if the new machine took its share, and nothing else moved?", [
            (lambda: [FadeIn(tb, shift=0.1 * UP)], 0.6),
            "Wouldn't it",
            (lambda: [FadeOut(VGroup(share, moved, landed, tb)), *self.cap("wish: the new machine takes its share, and nothing else moves", YELLOW_M, 26)], 0.8),
            (lambda: [glow(new[0], GREEN_M, 1.06)], 0.8),
        ], after=0.5)

        # ---------------- scene 3: the left-luggage office ----------------
        key = VGroup(Circle(radius=0.32, stroke_color=GOLD_M, stroke_width=5), Line([0.32, 0, 0], [1.6, 0, 0], stroke_color=GOLD_M, stroke_width=6),
                     Line([1.3, 0, 0], [1.3, -0.28, 0], stroke_color=GOLD_M, stroke_width=6),
                     Line([1.5, 0, 0], [1.5, -0.22, 0], stroke_color=GOLD_M, stroke_width=6))
        tag = chip("locker 417", GOLD_M, 24).next_to(key[0], LEFT, buff=0.35)
        keyg = VGroup(tag, key).move_to([0, 0.9, 0])
        self.steps("Picture the left-luggage office at a big station. A thousand numbered lockers, ten attendants, a hundred lockers each.", [
            (lambda: [FadeOut(VGroup(*ms, new, r10)), *self.uncap()], 0.8),
            "A thousand",
            (lambda: self.cap("1,000 lockers,  10 attendants,  100 lockers each", WHITE, 28), 0.6),
        ])
        self.steps("A traveller's locker number is stamped on their key, and it never changes.", [
            "stamped",
            (lambda: [FadeIn(keyg, shift=0.15 * UP)], 0.8),
            "never changes",
            (lambda: [Indicate(tag[1], color=GOLD_M, scale_factor=1.15)], 0.8),
        ])
        self.steps("When an eleventh attendant starts, the manager hands her the keys to 90 lockers, about nine from each of the others. "
                   "No locker moves, and no traveller gets a new number.", [
            "the manager",
            (lambda: self.cap("an 11th attendant: 90 lockers, about 9 from each of the others", WHITE, 28), 0.6),
            "No locker",
            (lambda: [Indicate(tag[1], color=GOLD_M, scale_factor=1.15)], 0.8),
        ])
        nodes = [node_box(k, NX3[k]) for k in range(3)]
        lk = {p: locker(p, p % 3, slot_at(NX3[p % 3], p // 3)) for p in range(12)}
        self.steps("Let's shrink it to twelve lockers and three attendants, and map it.", [
            (lambda: [FadeOut(keyg), *self.uncap()], 0.6),
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.15 * UP) for n in nodes], lag_ratio=0.2)], 0.9),
            (lambda: [LaggedStart(*[FadeIn(lk[p], shift=0.1 * DOWN) for p in range(12)], lag_ratio=0.1)], 1.6),
        ])
        self.steps("Each locker is a partition: a fixed bucket of payments.", [
            (lambda: self.cap("a locker  =  a partition: a fixed bucket of payments", WHITE, 26), 0.5),
            (lambda: [LaggedStart(*[glow(lk[p][0], YELLOW_M, 1.08) for p in range(12)], lag_ratio=0.05)], 1.2),
        ])
        self.steps("Each attendant is a machine, and from here on we'll call a machine a node.", [
            (lambda: self.cap("an attendant  =  a machine, called a node", WHITE, 26), 0.5),
            "we'll call",
            (lambda: [*[Transform(n[1], T(f"node {NAMES[k]}", 26).move_to(n[1])) for k, n in enumerate(nodes)]], 0.8),
        ])
        rp = rule("partition = hash(key) mod 12")
        self.steps("The number on the key is hash mod 12, worked out once and never changed.", [
            (lambda: [*self.cap("the number on the key  =  hash mod 12, never changed", WHITE, 26), FadeIn(rp, shift=0.1 * DOWN)], 0.7),
        ])
        tlab = T("the table: which node holds each partition", 19, GREY_B)
        tlab.move_to([CX[0] - 0.46 + tlab.width / 2, TL_Y, 0])
        cells = [cell(p, p % 3) for p in range(12)]
        self.steps("And the manager's list is a table: which node looks after which partition.", [
            (lambda: [*self.cap("the manager's list  =  the table", WHITE, 26), FadeIn(tlab)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * UP) for c in cells], lag_ratio=0.08)], 1.4),
        ])

        # ---------------- scene 4: node D joins ----------------
        self.steps("The payment pay-7 hashes to partition 9, which lives on node A.", [
            (lambda: [*self.uncap(), *self.put("k7", keynote("pay-7", 9, 0, -3.4))], 0.6),
            "partition 9",
            (lambda: [glow(lk[9][0], GOLD_M, 1.12), glow(cells[9][0], GOLD_M, 1.1)], 0.9),
        ])
        self.steps("And pay-81701 is in partition 2, on node C.", [
            (lambda: self.put("k8", keynote("pay-81701", 2, 2, 3.4)), 0.6),
            (lambda: [glow(lk[2][0], GOLD_M, 1.12), glow(cells[2][0], GOLD_M, 1.1)], 0.9),
        ])
        dnode = node_box(3, NX4[3])
        dnode[1].become(T("node D", 26).move_to(dnode[1]))

        def shift3():
            out = []
            for k in range(3):
                dx = (NX4[k] - NX3[k]) * RIGHT
                out.append(nodes[k].animate.shift(dx))
                out += [lk[p].animate.shift(dx) for p in range(k, 12, 3)]
            return out

        qd = T("?", 44, YELLOW_M).move_to([NX4[3], NY - 0.15, 0])
        self.steps("Now node D joins. How many partitions should it get? And how many payments get a new partition number? Pause and guess.", [
            (lambda: shift3(), 0.9),
            (lambda: [FadeIn(dnode, shift=0.3 * LEFT)], 0.6),
            "How many partitions",
            (lambda: [FadeIn(qd, scale=0.6)], 0.5),
            "And how many",
            (lambda: [glow(rp[0], YELLOW_M, 1.04)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        three = T("12 ÷ 4 = 3", 26, GREEN_M).move_to([NX4[3], NY - 0.15, 0])
        self.steps("Three partitions: twelve, split four ways. And not one payment gets a new number, because twelve didn't change. "
                   "Only the table is about to change.", [
            (lambda: [*self.uncap(), swap(qd, three)], 0.6),
            "not one payment",
            (lambda: [glow(rp[0], GREEN_M, 1.04), *self.cap("no payment gets a new partition number", GREEN_M)], 0.8),
            "Only the table",
            (lambda: [glow(VGroup(*[c[0] for c in cells]), YELLOW_M, 1.01)], 0.9),
        ])

        def path(p, src_x, j):
            a = lk[p].get_center()
            b = slot_at(NX4[3], j)
            return VMobject().set_points_as_corners([a, [a[0], BAND, 0], [b[0], BAND, 0], b])

        copies = {}

        def start_copy(p, k, j):
            c = locker(p, 3, lk[p].get_center()).set_z_index(5)
            copies[p] = c
            return c, path(p, NX4[k], j)

        c9, pth9 = start_copy(9, 0, 0)
        bar_bg = Rectangle(width=1.0, height=0.08, stroke_width=0).set_fill(GREY_D, 1).move_to(slot_at(NX4[3], 0) + 0.42 * DOWN)
        bar_fg = Rectangle(width=0.01, height=0.08, stroke_width=0).set_fill(GREEN_M, 1).move_to(bar_bg.get_left(), aligned_edge=LEFT)
        self.steps("They're all tied at four, so A goes first, and hands over its highest partition, p9.", [
            (lambda: [*self.uncap(), FadeOut(three)], 0.4),
            "A goes first",
            (lambda: [glow(nodes[0][0], BLUE_M, 1.03)], 0.8),
            "its highest",
            (lambda: [glow(lk[9][0], YELLOW_M, 1.12)], 0.8),
        ])
        self.steps("A copies p9 to D, and keeps serving payments from it while it copies.", [
            (lambda: [FadeIn(c9), MoveAlongPath(c9, pth9, rate_func=smooth)], 1.4),
            (lambda: [FadeIn(bar_bg), FadeIn(bar_fg), *self.cap("A keeps serving p9 while it copies", GREY_B)], 0.3),
            (lambda: [bar_fg.animate.stretch_to_fit_width(1.0).move_to(bar_bg), lk[9][0].animate(rate_func=there_and_back).set_stroke(YELLOW_M, 6)], 1.5),
        ])
        self.steps("When D has caught up, the table says p9 lives on D.", [
            "the table says",
            (lambda: [FadeOut(bar_bg), FadeOut(bar_fg), Transform(cells[9][2], letter(3, 9)), glow(cells[9][0], GREEN_M, 1.1),
                      lk[9].animate.set_opacity(0.15), *self.uncap()], 0.8),
        ])
        c10, pth10 = start_copy(10, 1, 1)
        c11, pth11 = start_copy(11, 2, 2)
        self.steps("Then B gives p10, and C gives p11. Every node holds three.", [
            (lambda: [FadeIn(c10), MoveAlongPath(c10, pth10, rate_func=smooth)], 1.0),
            (lambda: [Transform(cells[10][2], letter(3, 10)), lk[10].animate.set_opacity(0.15)], 0.4),
            "and C gives",
            (lambda: [FadeIn(c11), MoveAlongPath(c11, pth11, rate_func=smooth)], 1.0),
            (lambda: [Transform(cells[11][2], letter(3, 11)), lk[11].animate.set_opacity(0.15)], 0.4),
            "Every node",
            (lambda: [*[FadeOut(lk[p]) for p in (9, 10, 11)]], 0.5),
        ])
        self.steps("Check both payments. pay-81701 is still in p2, and p2 never left C.", [
            "pay-81701",
            (lambda: [glow(lk[2][0], GOLD_M, 1.12), glow(cells[2][0], GOLD_M, 1.1)], 0.9),
            (lambda: [Indicate(self.slots["k8"], color=GOLD_M, scale_factor=1.06)], 0.7),
        ])
        self.steps("pay-7 is still in p9, which now lives on D. It moved, but only as part of a whole partition.", [
            (lambda: [glow(c9[0], GOLD_M, 1.12), glow(cells[9][0], GOLD_M, 1.1)], 0.9),
            (lambda: self.put("k7", keynote("pay-7", 9, 3, -3.4)), 0.7),
        ])
        self.steps("Three partitions of twelve moved: a quarter, D's fair share, and three nodes shared the sending. "
                   "Hash mod N, going from three nodes to four, would have moved three payments in four.", [
            (lambda: self.cap("3 of 12 partitions moved: all to D, from 3 senders", GREEN_M), 0.6),
            "three nodes shared",
            (lambda: [*[glow(nodes[k][0], NC[k], 1.03) for k in range(3)]], 0.9),
            "Hash mod N",
            (lambda: self.cap("hash mod N, 3 nodes to 4: three payments in four move", RED_M), 0.6),
        ], after=0.5)

        # ---------------- scene 5: where the lockers break, and the name ----------------
        self.steps("Here the lockers picture breaks. Handing over a key takes a second. "
                   "Moving a partition means copying gigabytes between machines that are busy serving payments, "
                   "and the copying loads the very nodes it's meant to relieve.", [
            (lambda: self.cap("where the lockers picture breaks", GREY_B), 0.5),
            "Handing over",
            (lambda: self.cap("a key: one second.   a partition: gigabytes, copied while serving", RED_M), 0.6),
            "and the copying",
            (lambda: [*[glow(nodes[k][0], RED_M, 1.03) for k in range(3)]], 1.0),
        ])
        self.steps("The new attendant isn't handed keys. She's handed the luggage, by colleagues who are still serving the queue.", [
            "the luggage",
            (lambda: [glow(dnode[0], GREEN_M, 1.03)], 0.9),
        ], after=0.5)
        self.steps("At full size, a thousand partitions on ten nodes, the eleventh node takes 90, and only 8,955 of the 100,000 payments move. "
                   "All of them go to the new node, sent by all ten old ones.", [
            (lambda: self.cap("1,000 partitions, 10 nodes to 11: the new node takes 90", WHITE), 0.6),
            "and only",
            (lambda: self.cap("8,955 of 100,000 payments move, all to the new node, from 10 senders", GREEN_M), 0.6),
        ])
        self.steps("Moving data so every node holds a fair share is called rebalancing.", [
            "is called",
            (lambda: self.cap("rebalancing: moving data so every node holds a fair share", YELLOW_M, 26), 0.6),
        ])
        self.steps("And this design is called fixed partitions: far more partitions than nodes, chosen once, and moved whole.", [
            "fixed partitions",
            (lambda: [*self.cap("fixed partitions: many more than nodes, chosen once, moved whole", YELLOW_M, 26), glow(rp[0], YELLOW_M, 1.04)], 0.7),
            "moved whole",
            (lambda: [*[glow(copies[p][0], GREEN_M, 1.1) for p in (9, 10, 11)]], 0.8),
        ])
        self.steps("Kafka, a program that keeps logs of messages, splits each log into a fixed number of partitions.", [
            "Kafka, a",
            (lambda: self.cap("Kafka: each log split into a fixed number of partitions", WHITE), 0.6),
        ])
        self.steps("And Notion, the notes app, runs 480 shards. Going from 32 machines to 96, whole shards moved, and no workspace changed shard.", [
            (lambda: self.cap("Notion: 480 shards; 32 machines to 96, no workspace changed shard", WHITE), 0.6),
        ], after=0.5)

        # ---------------- scene 6: the catch ----------------
        self.steps("The catch is that the number of partitions, call it P, is chosen once. Pick too few, and you hit a wall.", [
            (lambda: [*self.cap("the catch: P, the number of partitions, is chosen once", WHITE), glow(rp[0], YELLOW_M, 1.04)], 0.7),
            "Pick too few",
            (lambda: self.cap("too few: you hit a wall", RED_M), 0.5),
        ])
        self.steps("With twelve partitions, a thirteenth node has nothing to hold. It gets a chair and no lockers.", [
            (lambda: self.cap("12 partitions, 13 nodes: one node holds nothing", RED_M), 0.6),
            "a chair",
            (lambda: [glow(dnode[0], RED_M, 1.03)], 0.9),
        ])
        self.steps("Pick too many, and every partition's fixed cost adds up: its own files, its own line in the table.", [
            (lambda: self.cap("too many: every partition has its own files and its own line in the table", RED_M), 0.6),
            "its own line",
            (lambda: [LaggedStart(*[glow(c[0], RED_M, 1.08) for c in cells], lag_ratio=0.06)], 1.2),
        ])
        olds = [c[2] for c in cells]
        qs = [letter(0, p, "?", GREY_B) for p in range(12)]
        rp13 = rule("partition = hash(key) mod 13", RED_M)
        rp12 = rule("partition = hash(key) mod 12")
        self.steps("And changing P later means rehashing the keys, which is the hash mod N mess all over again.", [
            (lambda: [Transform(rp, rp13), *self.cap("changing P later: most keys get a new partition", RED_M)], 0.6),
            (lambda: [*[FadeOut(o) for o in olds], *[FadeIn(q) for q in qs]], 0.5),
            "all over again",
            1.0,
            (lambda: [Transform(rp, rp12), *[FadeOut(q) for q in qs], *[FadeIn(o) for o in olds]], 0.6),
        ])
        self.steps("So pick a P with plenty of divisors. Notion chose 480 for the same reason an hour has 60 minutes.", [
            (lambda: self.cap("pick a P with plenty of divisors", YELLOW_M, 26), 0.6),
            "an hour",
            (lambda: self.cap("480, for the same reason an hour has 60 minutes", WHITE), 0.6),
        ])
        self.steps("480 spreads evenly over 32, 40, 48 or 96 machines. 512 doesn't. "
                   "On 96 machines, some hold six and some hold five, and the busiest carries 13% more than the average.", [
            (lambda: self.cap("480: even on 32, 40, 48 or 96 machines (96: 5 each)", GREEN_M), 0.6),
            "512 doesn't",
            (lambda: self.cap("512 on 96 machines: 6 or 5 each, the busiest carries 13% more", RED_M), 0.6),
        ], after=0.5)

        # ---------------- scene 7: the moral ----------------
        self.steps("So, how much should one new machine disturb? Only its share.", [
            (lambda: self.uncap(), 0.4),
            "Only its share",
            (lambda: [*[glow(copies[p][0], GREEN_M, 1.1) for p in (9, 10, 11)], glow(dnode[0], GREEN_M, 1.03)], 0.9),
        ])
        self.steps("Number the lockers once, hand them over whole, and change only the list. Pick P once, for the size you expect years from now.", [
            (lambda: [*self.cap("number the lockers once, move them whole, change only the list", YELLOW_M, 28), glow(rp[0], YELLOW_M, 1.04)], 0.7),
            "change only the list",
            (lambda: [glow(VGroup(*[c[0] for c in cells]), YELLOW_M, 1.01)], 0.9),
            "Pick P once",
            (lambda: self.cap("pick P once, for the size you expect years from now", WHITE), 0.6),
        ], after=0.6)
        # ---------------- scene 8: a quick check ----------------
        self.steps("One quick check. A fifth node, E, joins our cluster. Does pay-81701 get a new partition number? Pause and think.", [
            (lambda: self.cap("a fifth node joins: does pay-81701 get a new partition number?", WHITE), 0.6),
            "Does pay-81701",
            (lambda: [Indicate(self.slots["k8"], color=GOLD_M, scale_factor=1.06)], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. It stays in p2, forever. At most, p2 gets a new node, and only the table changes.", [
            (lambda: [*self.cap("p2, forever: only the table can change", GREEN_M, 26), glow(lk[2][0], GREEN_M, 1.12)], 0.7),
            "At most",
            (lambda: [glow(cells[2][0], GREEN_M, 1.1)], 0.8),
            "only the table",
            (lambda: [glow(rp[0], GREEN_M, 1.04)], 0.8),
        ], after=0.3)
        self.wait(2.0)
