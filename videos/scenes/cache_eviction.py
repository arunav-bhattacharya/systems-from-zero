from sfz import *

# The letter A naming a book: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))
SAY.insert(0, (r"\bS3-FIFO\b", "S three fife oh"))
SAY.insert(0, (r"\bFIFO\b", "fife oh"))
SAY.insert(0, (r"\bLFU\b", "L F U"))
SAY.insert(0, (r"\bSIEVE\b", "sieve"))
SAY.insert(0, (r"\bZipf\b", "zipf"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TOP_Y, SHELF_Y, BW, BH, GAP = 3.05, 0.55, 1.15, 1.5, 0.25
SLOT_X = [(-2.5 + k) * (BW + GAP) for k in range(6)]
IN_X = SLOT_X[-1] + BW + GAP + 0.35          # where a new book waits
HAND_Y = SHELF_Y + BH / 2 + 0.38
END_Y, TICK_Y, CAP_Y, BAR_Y, BASE_Y = SHELF_Y - BH / 2 - 0.3, -1.75, -3.22, -2.72, -1.2
POP = {"A", "B", "C"}


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d, run_time=0.3), FadeIn(new, shift=0.1 * d))


def outline(m, color=YELLOW_M, buff=0.08):
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.1, stroke_width=4).set_z_index(7)
    return Succession(Create(r, run_time=0.35), FadeOut(r, run_time=0.45))


def book(name):
    color = GOLD_M if name in POP else (PURPLE_M if name.startswith("S") else BLUE_M)
    r = RoundedRectangle(corner_radius=0.08, width=BW, height=BH, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.2), 1)
    t = T(name, 30, color).move_to(r.get_center() + [0, -0.15, 0]).set_z_index(3)
    g = VGroup(r, t)
    g.name_ = name
    return g


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0]).set_z_index(3)
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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


class CacheEviction(Base):
    """cache-05, section 3. The cache is full and a new key arrives: which one goes? The library's shelf and its
    basement. FIFO, LRU, LFU as kinds of evidence. LRU on a shelf of six: a hit moves a book to the newest end; a
    one-time scan pushes every popular book out. One-hit wonders (26% of keys in the median trace, 72% in a short
    stretch). SIEVE: one FIFO list, a visited bit, a hand that spares visited books in place; predict the scan, and the
    scan books evict each other. The lab's numbers (10,000 slots: LRU 26.1 → 29.0 with scans, SIEVE 21.6 → 21.6).
    Guardrails, Java and Kotlin, the moral, and a check (where does a spared key end up?)."""

    # ---------- the shelf ----------
    def title(self, s, color=WHITE):
        return self.put("title", T(s, 28, color).move_to([0, TOP_Y, 0]))

    def tick(self, s, color=WHITE):
        return self.put("tick", fit(T(s, 22, color), 13.0).move_to([0, TICK_Y, 0]))

    def lay(self):
        return [b.animate.move_to([SLOT_X[k], SHELF_Y, 0]) for k, b in enumerate(self.shelf)]

    def bit(self, b, on):
        key = id(b)
        out = []
        if on and key not in self.bits:
            d = Dot(radius=0.11, color=GREEN_M).move_to(b.get_center() + [0, 0.45, 0]).set_z_index(5)
            d.add_updater(lambda m, b=b: m.move_to(b.get_center() + [0, 0.45, 0]))
            self.bits[key] = d
            out.append(FadeIn(d, scale=0.5))
        elif not on and key in self.bits:
            d = self.bits.pop(key)
            out.append(FadeOut(d, scale=0.5))
        return out

    def hit(self, name, lru=True):
        """A request finds its book on the shelf: LRU moves it to the newest end; SIEVE sets its bit."""
        b = next(x for x in self.shelf if x.name_ == name)
        if lru:
            self.shelf.remove(b)
            self.shelf.append(b)
            return [outline(b, GREEN_M, 0.05), *self.lay()]
        return [outline(b, GREEN_M, 0.05), *self.bit(b, True)]

    def arrive(self, name):
        b = book(name).move_to([IN_X, SHELF_Y, 0])
        self.incoming = b
        return [FadeIn(b, shift=0.3 * LEFT)]

    def evict(self, b):
        self.shelf.remove(b)
        out = [b.animate.move_to(b.get_center() + [0, -1.7, 0]).set_opacity(0), *self.bit(b, False)]
        return out

    def admit(self):
        b = self.incoming
        self.shelf.append(b)
        self.incoming = None
        return self.lay()

    def hand_to(self, b, color=YELLOW_M):
        x = b.get_center()[0] if not isinstance(b, (int, float)) else b
        tri = Triangle(color=color, fill_opacity=1, stroke_width=0).scale(0.16).rotate(PI).move_to([x, HAND_Y, 0]).set_z_index(6)
        if self.hand is None:
            self.hand = tri
            return [FadeIn(tri, shift=0.1 * DOWN)]
        return [self.hand.animate.move_to([x, HAND_Y, 0])]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.bits = {}
        self.hand = None
        self.incoming = None
        self.title_card("A scan that empties the shelf", "LRU, and SIEVE's visited bit")

        start = ["D", "A", "E", "B", "F", "C"]
        self.shelf = [book(n).move_to([x, SHELF_Y, 0]) for n, x in zip(start, SLOT_X)]
        ends = VGroup(T("oldest", 20, GREY_B).move_to([SLOT_X[0], END_Y, 0]), T("newest", 20, GREY_B).move_to([SLOT_X[-1], END_Y, 0]))
        base_l = T("basement", 20, GREY_B).move_to([-6.0, BASE_Y, 0])

        # ---------------- scene 1: the question ----------------
        self.steps("Picture a library with full shelves. A new book arrives, and one book has to go down to the basement. Which one?", [
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in self.shelf], lag_ratio=0.1)], 1.0),
            "A new book",
            (lambda: self.arrive("G"), 0.5),
            "the basement",
            (lambda: [FadeIn(base_l)], 0.4),
            "Which one",
            (lambda: self.cap("the shelf is full: which book goes?", YELLOW_M), 0.5),
        ])
        self.steps("A cache faces the same choice. It keeps copies of data close by in memory, and when memory is full, "
                   "it has to guess which key it will need least soon, and throw that one out.", [
            "A cache",
            (lambda: self.cap("a cache: copies kept close by. Full memory: guess which key is needed least soon", WHITE), 0.6),
            "throw that one out",
            (lambda: [outline(VGroup(*self.shelf), GREY_B, 0.12)], 0.8),
        ])
        self.steps("Every way of choosing, called an eviction policy, answers with a different kind of evidence about the past.", [
            "eviction policy",
            (lambda: self.cap("eviction policy: how the cache chooses, from evidence about the past", WHITE), 0.6),
        ], after=0.3)
        self.stamp("question")

        # ---------------- scene 2: FIFO, LRU, LFU ----------------
        self.steps("FIFO, first in, first out, removes the book that arrived first, however often people read it.", [
            (lambda: [*self.uncap(), *self.title("FIFO: the first to arrive goes", BLUE_M), FadeIn(ends)], 0.6),
            "arrived first",
            (lambda: [outline(self.shelf[0], RED_M, 0.06)], 0.8),
        ])
        self.steps("LRU, least recently used, removes the book nobody has opened for the longest. LFU removes the one opened the fewest times.", [
            (lambda: self.title("LRU: the longest unopened goes", GOLD_M), 0.5),
            "LFU",
            (lambda: self.title("LFU: the least often opened goes", GREY_B), 0.5),
        ])
        self.steps("LRU is the usual choice. Here's how it keeps its order. The shelf runs from oldest to newest. "
                   "When someone reads a book, it moves to the newest end.", [
            (lambda: self.title("LRU", GOLD_M), 0.4),
            "oldest to newest",
            (lambda: [outline(ends, GREY_B, 0.1)], 0.8),
            "When someone reads",
            (lambda: [*self.tick("read A: it moves to the newest end", GREEN_M), *self.hit("A")], 0.9),
            (lambda: [*self.tick("read B", GREEN_M), *self.hit("B")], 0.8),
        ])
        self.steps("And the book that goes is the one at the oldest end.", [
            (lambda: [*self.tick("new book G: the oldest one goes", WHITE), *self.evict(self.shelf[0])], 0.7),
            (lambda: self.admit(), 0.6),
        ], after=0.3)
        self.stamp("lru")

        # ---------------- scene 3: the scan breaks LRU ----------------
        self.steps("Now the three popular books, A, B and C, get read all day. Then, one night, a report reads every key once. "
                   "That's called a scan.", [
            (lambda: [*self.tick("A, B and C: read all day", GOLD_M), *self.hit("C"), ], 0.8),
            (lambda: [*self.hit("A")], 0.6),
            (lambda: [*self.hit("B")], 0.6),
            "a report",
            (lambda: [*self.title("a one-time scan: every key read once", PURPLE_M)], 0.5),
        ])
        self.steps("Before you watch, guess. What does a scan do to an LRU shelf? Pause and guess.", [
            (lambda: self.cap("a scan on an LRU shelf: what happens?  pause and guess", YELLOW_M), 0.6),
        ], after=0)
        self.countdown(3.0)

        def scan_lru(k):
            return [(lambda k=k: [*self.tick(f"scan book S{k}: read once, never again", PURPLE_M), *self.arrive(f"S{k}")], 0.35),
                    (lambda: self.evict(self.shelf[0]), 0.35), (lambda: self.admit(), 0.35)]

        self.steps("Each scan book arrives, looks like the newest thing on the shelf, and pushes the oldest one out. "
                   "Six scan books later, every popular book is in the basement.", [
            (lambda: self.uncap(), 0.3),
            *[x for k in range(1, 7) for x in scan_lru(k)],
            "every popular book",
            (lambda: [*self.cap("the scan made every key look recent, and pushed the popular ones out", RED_M)], 0.6),
        ])
        self.steps("Tomorrow, the first reader of A misses. Well, that's not the shelf we wanted.", [
            (lambda: self.tick("read A: a miss", RED_M), 0.5),
        ])
        self.steps("LRU has a second cost. Every hit moves a key, and the list it moves on has a lock, so only one thread at a time "
                   "can change it. Busy threads queue for it.", [
            (lambda: self.cap("and every hit moves a key, under one lock: busy threads queue", WHITE), 0.6),
        ], after=0.3)
        self.stamp("scan")

        # ---------------- scene 4: one-hit wonders ----------------
        self.steps("How common are books read only once? A 2023 study looked at 6,594 recordings of the requests real caches received.", [
            (lambda: [*self.drop("tick"), *self.uncap(), *self.title("one-hit wonders: keys asked for once, never again", PURPLE_M)], 0.6),
            "6,594",
            (lambda: self.cap("the S3-FIFO study (2023): 6,594 traces from real caches", WHITE), 0.6),
        ])
        self.steps("In the middle trace, 26 percent of keys were asked for once and never again. In a short stretch of a trace, 72 percent were. "
                   "So the evidence says: drop new keys quickly, unless they prove themselves.", [
            "26 percent",
            (lambda: self.cap("median trace: 26% of keys are one-hit wonders.  a short stretch: 72%", WHITE), 0.6),
            "So the evidence",
            (lambda: self.cap("wanted: drop new keys quickly, unless they prove themselves", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("wonders")

        # ---------------- scene 5: SIEVE ----------------
        reset = ["D", "A", "E", "B", "F", "C"]

        def reset_shelf():
            old = self.shelf
            self.shelf = [book(n).move_to([x, SHELF_Y, 0]) for n, x in zip(reset, SLOT_X)]
            return [FadeOut(VGroup(*old)), *[FadeIn(b) for b in self.shelf]]

        self.steps("SIEVE, from 2024, keeps the books in arrival order, and gives each one a sticky dot. A read puts a dot on the book, "
                   "and moves nothing.", [
            (lambda: [*self.uncap(), *self.title("SIEVE: arrival order, and one visited dot per book", TEAL_M), *reset_shelf()], 0.8),
            "A read puts",
            (lambda: [*self.tick("read A, read B, read C: a dot each, nothing moves", GREEN_M), *self.hit("A", False)], 0.6),
            (lambda: [*self.hit("B", False)], 0.5),
            (lambda: [*self.hit("C", False)], 0.5),
        ])
        self.steps("To make room, a hand walks from the oldest book toward the newest. A book with a dot keeps its place, "
                   "and loses its dot. The first book without a dot goes.", [
            (lambda: [*self.tick("new book S1", PURPLE_M), *self.arrive("S1")], 0.5),
            "a hand walks",
            (lambda: self.hand_to(self.shelf[0]), 0.4),
            "The first book without",
            (lambda: [outline(self.shelf[0], RED_M, 0.05)], 0.5),
            (lambda: [*self.evict(self.shelf[0]), *self.hand_to(SLOT_X[0] + 0.0)], 0.5),
            (lambda: [*self.admit()], 0.5),
        ])
        self.steps("In code, that dot is one visited bit per key.", [
            (lambda: self.cap("the dot = a visited bit; the hand = a pointer that walks the list", WHITE), 0.6),
        ], after=0.3)

        def sieve_step(name, spared, victim):
            """The hand spares `spared` books (clearing dots), then evicts `victim`."""
            out = [(lambda: [*self.tick(f"new book {name}", PURPLE_M), *self.arrive(name)], 0.4)]
            for s in spared:
                out.append((lambda s=s: [*self.hand_to(next(b for b in self.shelf if b.name_ == s)),
                                         *self.bit(next(b for b in self.shelf if b.name_ == s), False)], 0.45))
            out.append((lambda: [*self.hand_to(next(b for b in self.shelf if b.name_ == victim))], 0.35))
            out.append((lambda: [*self.evict(next(b for b in self.shelf if b.name_ == victim))], 0.4))
            out.append((lambda: [*self.admit()], 0.45))
            return out

        self.steps("Now run the scan. Pause and guess first: which books end up in the basement?", [
            (lambda: self.cap("the scan on a SIEVE shelf: who goes?  pause and guess", YELLOW_M), 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("The hand spares A, clears its dot, and drops E. It spares B and drops F. It spares C, and drops S1, "
                   "the first scan book. From then on, scan books push out scan books.", [
            (lambda: self.uncap(), 0.2),
            *sieve_step("S2", ["A"], "E"),
            "It spares B",
            *sieve_step("S3", ["B"], "F"),
            "It spares C",
            *sieve_step("S4", ["C"], "S1"),
            "From then on",
            *sieve_step("S5", [], "S2"),
            *sieve_step("S6", [], "S3"),
        ])
        self.steps("Books A, B and C are still on the shelf, and their next reads put the dots back.", [
            (lambda: [*self.cap("the popular books stay; one-time books leave first", GREEN_M)], 0.5),
            "put the dots back",
            (lambda: [*self.hit("A", False), *self.hit("B", False), *self.hit("C", False)], 0.7),
        ], after=0.3)
        self.stamp("sieve")

        # ---------------- scene 6: the lab's numbers ----------------
        shelf_g = VGroup(*self.shelf, ends, base_l)
        rows = [("", "Zipf", "Zipf + scans"), ("FIFO", "29.8%", "32.2%"), ("LRU", "26.1%", "29.0%"), ("SIEVE", "21.6%", "21.6%")]
        cols = [-3.0, 0.2, 3.4]
        tbl = VGroup()
        for r, row in enumerate(rows):
            for c, s in enumerate(row):
                color = GREY_B if r == 0 or c == 0 else WHITE
                tbl.add(T(s, 26 if r else 22, color).move_to([cols[c], 1.4 - 0.75 * r, 0]))
        rule = Line([-4.2, 1.05, 0], [4.6, 1.05, 0], stroke_width=1.5, color=GREY_C)
        self.steps("The lesson's lab races all three on a million requests with Zipf traffic, the skewed kind where a few keys get "
                   "most of the requests. The cache holds 10,000 keys, and we count misses, requests the cache can't answer.", [
            (lambda: [*self.drop("tick"), FadeOut(shelf_g), *[FadeOut(d) for d in self.bits.values()], FadeOut(self.hand),
                      *self.title("miss ratio, cache of 10,000 keys", WHITE)], 0.7),
            "Zipf traffic",
            (lambda: [FadeIn(rule), *[FadeIn(tbl[k]) for k in range(0, 3)]], 0.5),
            "we count misses",
            (lambda: [*[FadeIn(tbl[k]) for k in (3, 4, 6, 7, 9, 10)], *self.cap("miss: a request the cache can't answer", WHITE)], 0.7),
        ])
        self.steps("SIEVE misses least: 21.6 percent, against 26.1 for LRU. Then the lab mixes in scans. Pause and guess the last column.", [
            "SIEVE misses least",
            (lambda: [outline(VGroup(tbl[10], tbl[7]), TEAL_M, 0.1)], 0.8),
            "Pause and guess",
            (lambda: self.cap("with scans mixed in: guess the last column", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(2.5)
        self.steps("FIFO rises to 32.2, and LRU to 29.0. SIEVE stays at 21.6. Scan keys arrive without a dot, "
                   "so the hand drops them before any key that was read.", [
            (lambda: [FadeIn(tbl[5]), tbl[5].animate.set_color(RED_M)], 0.5),
            "LRU to 29.0",
            (lambda: [FadeIn(tbl[8]), tbl[8].animate.set_color(RED_M)], 0.5),
            "SIEVE stays",
            (lambda: [FadeIn(tbl[11]), tbl[11].animate.set_color(GREEN_M)], 0.5),
            "Scan keys arrive",
            (lambda: self.cap("scan keys arrive without a dot: the hand drops them first", WHITE), 0.6),
        ], after=0.3)
        self.stamp("numbers")

        # ---------------- scene 7: guardrails, and the code ----------------
        self.steps("A few limits. With a cache of only 1,000 keys, the scans changed little for any policy. Every policy is a bet "
                   "on the past, and your traffic decides which bet wins. And throwing keys away is right for a cache, "
                   "and wrong for data you can't rebuild.", [
            "1,000 keys",
            (lambda: self.cap("cache of 1,000 keys: the scans changed little", WHITE), 0.5),
            "a bet",
            (lambda: self.cap("every policy is a bet on the past: your traffic decides", WHITE), 0.6),
            "throwing keys away",
            (lambda: self.cap("evicting is right for a cache, wrong for data you can't rebuild", YELLOW_M), 0.6),
        ], after=0.3)
        PX, PW, PY = [-3.32, 3.32], 6.3, 0.55
        panels = [RoundedRectangle(corner_radius=0.12, width=PW, height=3.3, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1).move_to([x, PY, 0]) for x in PX]
        heads = [T(s, 24, GREY_B).move_to([x, PY + 2.0, 0]) for s, x in zip(("Java", "Kotlin"), PX)]
        java = ["// a hit: set the bit, move nothing", "node.visited = true;", "", "// the hand: spare, clear, walk on",
                "while (o.visited) {", "    o.visited = false;", "    o = o.newer != null ? o.newer : tail;", "}"]
        kot = ["// a hit: set the bit, move nothing", "it.visited = true", "", "// the hand: spare, clear, walk on",
               "while (o.visited) {", "    o.visited = false", "    o = o.newer ?: tail!!", "}"]
        CHW = M("x" * 20, 16).width / 20

        def code(lines, x):
            ms = []
            for l in lines:
                ind = len(l) - len(l.lstrip(" "))
                m = M(l.strip() or "x", 16, GREY_B if l.strip().startswith("//") else WHITE)
                if not l.strip():
                    m.set_opacity(0)
                ms.append((m, ind))
            g = VGroup(*[m for m, _ in ms]).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
            for m, ind in ms:
                m.shift(ind * CHW * RIGHT)
            fit(g, PW - 0.6)
            return g.move_to([x - PW / 2 + 0.3 + g.width / 2, PY, 0]).set_z_index(3)

        cj, ck = code(java, PX[0]), code(kot, PX[1])
        self.steps("Here's the heart of the lab's SIEVE, in Java and Kotlin. A hit sets one bit. The hand clears bits until it finds "
                   "a key without one. Because a hit moves nothing, SIEVE ran at twice LRU's speed on 16 threads.", [
            (lambda: [FadeOut(VGroup(tbl, rule)), *self.drop("title"), *[FadeIn(p) for p in panels], *[FadeIn(h) for h in heads]], 0.6),
            "A hit sets",
            (lambda: [FadeIn(VGroup(*cj[:2])), FadeIn(VGroup(*ck[:2]))], 0.5),
            "The hand clears",
            (lambda: [FadeIn(VGroup(*cj[3:])), FadeIn(VGroup(*ck[3:]))], 0.6),
            "twice LRU's speed",
            (lambda: self.cap("a hit moves nothing: twice LRU's speed on 16 threads (the SIEVE paper)", WHITE), 0.6),
        ], after=0.3)
        self.stamp("code")

        # ---------------- scene 8: moral and check ----------------
        self.shelf = [book(n).move_to([x, SHELF_Y, 0]) for n, x in zip(["A", "B", "C", "S4", "S5", "S6"], SLOT_X)]
        self.bits = {}
        self.hand = None
        self.steps("So the moral of the story. LRU trusts the last read, so one scan can fool it. SIEVE asks a new key to prove "
                   "itself once before it may stay.", [
            (lambda: [FadeOut(VGroup(*panels, *heads, cj, ck)), *[FadeIn(b) for b in self.shelf], FadeIn(ends), FadeIn(base_l)], 0.7),
            "LRU trusts",
            (lambda: self.cap("LRU trusts the last read: one scan fools it", WHITE), 0.5),
            "SIEVE asks",
            (lambda: self.cap("SIEVE: a new key must be read again to stay", YELLOW_M), 0.5),
        ], after=0.3)
        self.steps("One quick check. The hand reaches B, and B has a dot. Where does B end up? Pause and think.", [
            (lambda: [*self.bit(self.shelf[1], True), *self.hand_to(self.shelf[1]), *self.cap("B has a dot: where does it end up?  pause and think", YELLOW_M)], 0.7),
        ], after=0)
        self.countdown(3.0)
        self.steps("Right where it was. It loses its dot and keeps its place. LRU would have moved it; SIEVE never moves anything.", [
            (lambda: [*self.bit(self.shelf[1], False), outline(self.shelf[1], GREEN_M, 0.06), *self.hand_to(self.shelf[2])], 0.7),
            "LRU would have",
            (lambda: self.cap("spared books stay in place; only the dot changes", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("drop new keys quickly, unless they prove themselves", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
