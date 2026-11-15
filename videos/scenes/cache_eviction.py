from sfz import *

SAY.insert(0, (r"\bSIEVE\b", "sieve"))

X0, DX, ROW_Y = -5.6, 1.6, 1.25       # eight slots, left to right
SW, SH = 1.36, 0.8
HAND_Y = 2.0
STATUS_Y = 2.78
TOP_Y = 3.25
END_Y = 0.08
# hit-ratio chart: time left to right, 0 to 100% bottom to top
CX0, CX1, CY0, CH = -5.6, 6.0, -3.35, 2.4
SCAN0, SCAN1 = -2.4, 2.8
HOT = {"m-17", "m-42", "m-08", "m-93"}


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.06):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def pos(i):
    return np.array([X0 + i * DX, ROW_Y, 0])


def kcolor(k):
    return GOLD_M if k in HOT else (PURPLE_M if k.startswith("m-5") else GREY_B)


def key_box(k, bit=None):
    c = kcolor(k)
    r = RoundedRectangle(corner_radius=0.1, width=SW, height=SH, stroke_color=c, stroke_width=3).set_fill(fillc(c), 1)
    g = VGroup(r, M(k, 22, WHITE))
    if bit is not None:
        b = Square(0.24, stroke_color=GOLD_M, stroke_width=2).set_fill(GOLD_M, 1 if bit else 0)
        b.move_to([0, -SH / 2 - 0.3, 0])
        g.add(b)
    return g


def at(g, i):
    return g.shift(pos(i) - g[0].get_center())


def cy(p):
    return CY0 + p * CH


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


class Row:
    """Eight cache slots. LRU keeps them least recent to most recent; SIEVE keeps them oldest to newest,
    each with a visited bit, and a hand that walks from oldest to newest."""

    def __init__(self, keys, bits=None):
        self.order = list(keys)
        self.bits = dict(zip(keys, bits)) if bits else None
        self.mob = {k: at(key_box(k, self.bits[k] if bits else None), i) for i, k in enumerate(keys)}
        self.hand = 0

    def group(self):
        return VGroup(*[self.mob[k] for k in self.order])

    def _settle(self, skip=None):
        return [self.mob[k].animate.shift(pos(i) - self.mob[k][0].get_center())
                for i, k in enumerate(self.order) if k != skip and not np.allclose(self.mob[k][0].get_center(), pos(i))]

    def lru_hit(self, k):
        self.order.remove(k)
        self.order.append(k)
        m = self.mob[k]
        return [m.animate(path_arc=-0.8).shift(pos(7) - m[0].get_center()), *self._settle(skip=k)]

    def _evict(self, victim):
        m = self.mob.pop(victim)
        self.order.remove(victim)
        return [m.animate.shift(0.7 * DOWN).set_opacity(0)]

    def _insert(self, k, bit=None):
        g = at(key_box(k, bit), 7)
        self.mob[k] = g
        self.order.append(k)
        if self.bits is not None:
            self.bits[k] = 0
        return [FadeIn(g, shift=0.6 * LEFT)]

    def lru_miss(self, k):
        v = self.order[0]
        return [*self._evict(v), *self._settle_after(v), *self._insert(k)]

    def _settle_after(self, v):
        return self._settle()

    def set_bit(self, k, on):
        self.bits[k] = 1 if on else 0
        return self.mob[k][2].animate.set_fill(GOLD_M, 1 if on else 0)


def hand_xy(i):
    return [pos(i)[0], HAND_Y + 0.08, 0]


class Sieve:
    """SIEVE's logic runs when a step is planned; each step's visuals run when it plays and look keys up by name."""

    def __init__(self, keys, bits, hand):
        self.order = list(keys)
        self.bits = dict(zip(keys, bits))
        self.mob = {k: at(key_box(k, b), i) for i, (k, b) in enumerate(zip(keys, bits))}
        self.hand = 0
        self.hm = hand

    def hit(self, k, rt=0.5):
        self.bits[k] = 1
        return [(lambda: [self.mob[k][2].animate.set_fill(GOLD_M, 1), glow(self.mob[k][0], GREEN_M)], rt)]

    def miss(self, k, rt=0.6, step=0.28):
        out = []
        i = self.hand
        while self.bits[self.order[i]]:
            kk = self.order[i]
            self.bits[kk] = 0
            out.append((lambda kk=kk: [self.mob[kk][2].animate.set_fill(GOLD_M, 0), glow(self.mob[kk][0], GOLD_M, 1.04)], step))
            i = (i + 1) % len(self.order)
            out.append((lambda i=i: [self.hm.animate.move_to(hand_xy(i))], step))
        victim = self.order.pop(i)
        self.order.append(k)
        self.bits[k] = 0
        nxt = i if i < len(self.order) - 1 else 0
        self.hand = nxt
        new_order = list(self.order)

        def ev():
            m = self.mob.pop(victim)
            g = at(key_box(k, 0), 7)
            self.mob[k] = g
            anims = [m.animate.shift(0.7 * DOWN).set_opacity(0)]
            for j, kk in enumerate(new_order[:-1]):
                c = self.mob[kk][0].get_center()
                if not np.allclose(c, pos(j)):
                    anims.append(self.mob[kk].animate.shift(pos(j) - c))
            anims.append(FadeIn(g, shift=0.6 * LEFT))
            if nxt != i:
                anims.append(self.hm.animate.move_to(hand_xy(nxt)))
            return anims
        return out + [(lambda: [glow(self.mob[victim][0], RED_M, 1.04)], step), (ev, rt)]


class CacheEviction(Base):
    """cache-05, section 3: eight slots, four hot merchants take 9 requests in 10. LRU: a nightly report reads 1,000
    merchants once each, ten for every fraud check; eight report keys flush the hot ones and the fraud check's hits fall
    from 90% to 0 while it runs. SIEVE: one FIFO, a visited bit per key, a hand that clears bits and evicts the first
    clear one; the hand parks among the report keys, the hot keys stay, hits stay at 88% (simulated)."""

    def construct(self):
        self.title_card("Cache eviction: LRU and SIEVE", "what a one-time scan does to the hot keys")

        lru = Row(["m-230", "m-17", "m-415", "m-42", "m-08", "m-602", "m-93", "m-777"])
        self.steps("The fraud check caches merchant profiles, and the cache has room for eight. "
                   "Traffic is skewed: nine requests in ten ask for one of four busy merchants.", [
            (lambda: [LaggedStart(*[FadeIn(lru.mob[k], scale=0.9) for k in lru.order], lag_ratio=0.12)], 1.5),
            "nine requests",
            (lambda: [*[glow(lru.mob[k][0], GOLD_M) for k in lru.order if k in HOT]], 1.0),
        ])

        rule = left_at(T("LRU: evict the least recently used key", 22, WHITE), -6.6, TOP_Y)
        e_l = T("least recent", 18, GREY_B).move_to([pos(0)[0], END_Y, 0])
        e_r = T("most recent", 18, GREY_B).move_to([pos(7)[0], END_Y, 0])
        self.steps("When it's full, a new key pushes one out. LRU evicts the key used least recently, "
                   "the one at this end.", [
            (lambda: [FadeIn(rule, shift=0.1 * DOWN)], 0.7),
            "LRU evicts",
            (lambda: [FadeIn(e_l), FadeIn(e_r)], 0.6),
            "the one at",
            (lambda: [glow(lru.mob[lru.order[0]][0], RED_M)], 0.9),
        ])

        st = {}

        def status(s, color):
            new = M(s, 22, color).move_to([0, STATUS_Y, 0])
            if "s" in st:
                old = st["s"]
                st["s"] = new
                return [FadeOut(old, shift=0.1 * UP), FadeIn(new, shift=0.1 * UP)]
            st["s"] = new
            return [FadeIn(new, shift=0.1 * UP)]

        xax = Line([CX0, CY0, 0], [CX1, CY0, 0], stroke_width=2.5, color=GREY_B)
        yax = Line([CX0, CY0, 0], [CX0, cy(1.05), 0], stroke_width=2.5, color=GREY_B)
        tlab = right_at(T("time", 18, GREY_B), CX1, CY0 + 0.25)
        before = Line([CX0, cy(0.9), 0], [SCAN0, cy(0.9), 0], stroke_width=4, color=WHITE)
        b_lab = left_at(T("fraud check: 9 in 10 hit", 18, WHITE), CX0 + 0.15, cy(0.9) + 0.26)
        self.steps("A hit moves a key to the recent end. A miss brings the new key in there, and the oldest drops out. "
                   "So the busy merchants stay, and nine requests in ten hit.", [
            (lambda: status("GET m-17: hit", GREEN_M), 0.5),
            (lambda: lru.lru_hit("m-17"), 1.0),
            "A miss",
            (lambda: status("GET m-311: miss", RED_M), 0.5),
            (lambda: lru.lru_miss("m-311"), 1.0),
            "So the busy",
            (lambda: [Create(xax), Create(yax), FadeIn(tlab)], 0.7),
            (lambda: [Create(before), FadeIn(b_lab)], 0.8),
        ])

        shade = Rectangle(width=SCAN1 - SCAN0, height=CH + 0.15, stroke_width=0).set_fill(PURPLE_M, 0.12)
        shade.move_to([(SCAN0 + SCAN1) / 2, CY0 + (CH + 0.15) / 2, 0])
        sh_lab = T("the report runs", 18, PURPLE_M).move_to([(SCAN0 + SCAN1) / 2, cy(1.05) + 0.25, 0])
        cnt = {}

        def counter(n):
            new = right_at(T(f"report: {n:,} of 1,000 read", 20, PURPLE_M), 6.6, TOP_Y)
            if "c" in cnt:
                old = cnt["c"]
                cnt["c"] = new
                return [FadeOut(old), FadeIn(new)]
            cnt["c"] = new
            return [FadeIn(new, shift=0.1 * DOWN)]

        self.steps("Then the nightly report reads all 1,000 merchants, each one once, ten for every request the fraud "
                   "check makes.", [
            (lambda: [*counter(0), FadeIn(shade), FadeIn(sh_lab)], 0.8),
            "each one once",
            (lambda: [glow(shade, PURPLE_M, 1.0)], 0.8),
        ])

        def scan(n, rt, f):
            """The n-th report key (1-based) arrives: status, then the policy's own animation."""
            k = f"m-{500 + n}"
            return [(lambda: [*status(f"GET {k}: miss", PURPLE_M), *counter(n)], 0.3), (lambda: f(k), rt)]

        self.steps("Each report key is new, so it misses, goes in at the recent end, and pushes the oldest key out.", [
            *scan(1, 0.9, lru.lru_miss), *scan(2, 0.8, lru.lru_miss), *scan(3, 0.7, lru.lru_miss),
        ])

        self.steps("Five report keys later, the busy merchants are gone. "
                   "The cache is full of keys nobody will ask for again.", [
            *scan(4, 0.5, lru.lru_miss), *scan(5, 0.5, lru.lru_miss), *scan(6, 0.5, lru.lru_miss),
            *scan(7, 0.5, lru.lru_miss), *scan(8, 0.5, lru.lru_miss),
            "The cache is full",
            (lambda: [*[glow(lru.mob[k][0], PURPLE_M) for k in lru.order]], 0.9),
        ])

        lru_d = VMobject(stroke_color=RED_M, stroke_width=4).set_points_as_corners(
            [[SCAN0, cy(0.9), 0], [SCAN0 + 0.12, cy(0.0), 0], [SCAN1, cy(0.0), 0]])
        lru_a = VMobject(stroke_color=RED_M, stroke_width=4).set_points_as_corners(
            [[SCAN1, cy(0.0), 0], [SCAN1 + 0.3, cy(0.89), 0], [CX1, cy(0.89), 0]])
        l_lab = T("LRU: 0 hits", 18, RED_M).move_to([(SCAN0 + SCAN1) / 2, cy(0.0) + 0.26, 0])
        self.steps("So while the report runs, the fraud check misses every time. Its hits fall from nine in ten to "
                   "none, and come back only when the report is done.", [
            (lambda: status("GET m-17: miss", RED_M), 0.5),
            "Its hits fall",
            (lambda: [Create(lru_d)], 1.2),
            (lambda: [FadeIn(l_lab)], 0.5),
            "and come back",
            (lambda: [Create(lru_a)], 0.9),
        ])

        # ---- SIEVE ---------------------------------------------------------------------------------------------
        hand = VGroup(Triangle(color=WHITE, fill_opacity=1, stroke_width=0).scale(0.13).rotate(PI),
                      T("hand", 18, WHITE))
        hand[1].next_to(hand[0], UP, buff=0.08)
        hand.move_to(hand_xy(0))
        sv = Sieve(["m-17", "m-230", "m-42", "m-415", "m-08", "m-602", "m-93", "m-777"], [1, 0, 0, 0, 1, 0, 1, 0], hand)
        rule2 = left_at(T("SIEVE: a visited bit per key, and a hand", 22, WHITE), -6.6, TOP_Y)
        o_l = T("oldest", 18, GREY_B).move_to([pos(0)[0], END_Y, 0])
        o_r = T("newest", 18, GREY_B).move_to([pos(7)[0], END_Y, 0])
        leg = VGroup(Square(0.2, stroke_color=GOLD_M, stroke_width=2).set_fill(GOLD_M, 1), T("visited bit set", 18, GREY_B))
        leg.arrange(RIGHT, buff=0.15).move_to([0, END_Y, 0])
        self.steps("SIEVE keeps the keys in the order they arrived, and gives each one a visited bit. "
                   "A hit sets the bit, and nothing moves.", [
            (lambda: [FadeOut(lru.group()), FadeOut(st.pop("s")), FadeOut(cnt.pop("c")), FadeOut(rule), FadeOut(e_l),
                      FadeOut(e_r), lru_d.animate.set_stroke(opacity=0.35), lru_a.animate.set_stroke(opacity=0.35),
                      l_lab.animate.set_opacity(0.35)], 0.8),
            (lambda: [FadeIn(rule2, shift=0.1 * DOWN), FadeIn(o_l), FadeIn(o_r),
                      LaggedStart(*[FadeIn(sv.mob[k], scale=0.9) for k in sv.order], lag_ratio=0.1)], 1.4),
            "and gives each",
            (lambda: [FadeIn(leg)], 0.6),
            "A hit sets",
            (lambda: status("GET m-42: hit", GREEN_M), 0.5),
            *sv.hit("m-42", 0.8),
        ])

        m311 = sv.miss("m-311", rt=1.0, step=0.6)     # clear m-17, hand to 1, mark m-230, evict it
        self.steps("To make room, a hand walks from the oldest key toward the newest. A key whose bit is set gets a "
                   "second chance: the hand clears the bit and moves on.", [
            (lambda: [FadeIn(hand, shift=0.1 * DOWN)], 0.6),
            "A key whose bit",
            (lambda: status("GET m-311: miss", RED_M), 0.4),
            m311[0],
            "and moves on",
            m311[1],
        ])

        self.steps("The first key with a clear bit is evicted. The new key goes in at the newest end, "
                   "with its bit clear.", [
            m311[2],
            "The new key",
            m311[3],
        ])

        plan = []
        for n in range(1, 5):
            plan += [(lambda n=n: [*status(f"GET m-{500 + n}: miss", PURPLE_M), *counter(n)], 0.25)]
            plan += sv.miss(f"m-{500 + n}", rt=0.5, step=0.22)
        self.steps("Now run the report. The hand clears the busy merchants' bits as it passes, "
                   "and evicts the keys nobody came back for.", [
            "The hand clears",
            *plan,
        ])

        plan = []
        for n in range(5, 9):
            plan += [(lambda n=n: [*status(f"GET m-{500 + n}: miss", PURPLE_M), *counter(n)], 0.25)]
            plan += sv.miss(f"m-{500 + n}", rt=0.45, step=0.2)
        self.steps("Then it stops among the report keys. Each new report key evicts the one before it, "
                   "and the hand never reaches the busy merchants.", [
            (lambda: [glow(hand[0], PURPLE_M, 1.3)], 0.6),
            "Each new",
            *plan,
            "and the hand never",
            (lambda: [*[glow(sv.mob[k][0], GOLD_M) for k in ("m-17", "m-42", "m-08", "m-93")]], 0.9),
        ])

        sv_d = VMobject(stroke_color=GREEN_M, stroke_width=4).set_points_as_corners(
            [[SCAN0, cy(0.9), 0], [SCAN0 + 0.12, cy(0.88), 0], [SCAN1, cy(0.88), 0], [SCAN1 + 0.3, cy(0.9), 0], [CX1, cy(0.9), 0]])
        s_lab = T("SIEVE: 88% hit", 18, GREEN_M).move_to([(SCAN0 + SCAN1) / 2, cy(0.88) - 0.26, 0])
        self.steps("Meanwhile the fraud check keeps asking for them, so their bits are set again, and they hit. "
                   "Its hits stay near nine in ten.", [
            (lambda: status("GET m-42: hit", GREEN_M), 0.4),
            *sv.hit("m-42", 0.4),
            (lambda: status("GET m-17: hit", GREEN_M), 0.4),
            *sv.hit("m-17", 0.4),
            (lambda: status("GET m-93: hit", GREEN_M), 0.4),
            *sv.hit("m-93", 0.4),
            "Its hits stay",
            (lambda: [Create(sv_d)], 1.2),
            (lambda: [FadeIn(s_lab)], 0.5),
        ])

        self.steps("A one-time scan makes every key look recent to LRU. SIEVE keeps the keys that were asked for again, "
                   "so the scan passes through.", [
            (lambda: [lru_d.animate.set_stroke(opacity=1), l_lab.animate.set_opacity(1)], 0.8),
            "SIEVE keeps",
            (lambda: [*[glow(sv.mob[k][0], GOLD_M) for k in ("m-17", "m-42", "m-08", "m-93")]], 1.0),
            "so the scan",
            (lambda: [sv_d.animate(rate_func=there_and_back).set_stroke(width=8)], 1.0),
        ])
        self.wait(0.6)
