from sfz import *

SAY.insert(0, (r"\b4242('s)?\b", lambda m: "forty-two forty-two" + (m.group(1) or "")))
SAY.insert(0, (r"\bctid\b", "C T I D"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
COLS, ROWS, PITCH, CELL = 20, 12, 0.32, 0.26
GX0, GTOP = 0.2, 2.3                      # the table (or the cookbook): one square per group of pages
GTITLE_Y, GSCALE_Y = 2.72, -1.85
ROOT = np.array([-3.55, 1.95, 0])
INNER_X, INNER_Y = [-5.75, -4.28, -2.82, -1.35], 0.8
LEAF_X, LEAF_Y = [-6.3 + 0.59 * k for k in range(10)], -0.35
LEAF_OF = [0, 0, 0, 1, 1, 2, 2, 2, 3, 3]  # which inner page each drawn leaf hangs from
CALL_Y, CNT_Y, BAR_Y, CAP_Y = -1.55, -2.4, -2.85, -3.27
Q_POS = np.array([-3.55, 3.2, 0])

rng = np.random.default_rng(7)
CARD = sorted(rng.choice(COLS * ROWS, 14, replace=False).tolist())     # where card 4242's 14 rows happen to sit
LEMON = sorted(rng.choice(COLS * ROWS, 6, replace=False).tolist())     # the six lemon pages (toy positions)


def cell_xy(n):
    r, c = divmod(n, COLS)
    return np.array([GX0 + PITCH * (c + 0.5), GTOP - PITCH * (r + 0.5), 0])


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))






def small_box(c, w, h, label, color, size=17):
    r = RoundedRectangle(corner_radius=0.08, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(label, size, color).move_to(c)) if label else VGroup(r)


class IndexScan(Base):
    """store-07, section 0. Support asks for card 4242's payments. The cookbook: lemons through the index at the back,
    and the quick dinner it can't find. The heap: 1,000,478 payments in 23,818 pages, card 4242's 14 rows spread out;
    a sequential scan reads every page (3 processes, 333,488 rows thrown away each, a quarter of a second). Why not sort
    the table (one order only)? The index: card numbers in order with row addresses (ctid (339,35)); 1,130 leaves, 4
    inner pages, a root: a B+tree. The walk: 3 index pages + 14 table pages = 17, about a thousand times faster. The
    guardrail (its order only; 9 MB; writes cost more), the moral, and a check (one shop)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
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

    def count(self, s, color=WHITE, size=24):
        return self.put("cnt", fit(T(s, size, color), 13.0).move_to([0, CNT_Y, 0]))

    def gtitle(self, s, color=BLUE_M):
        return self.put("gt", T(s, 22, color).move_to([GX0 + COLS * PITCH / 2, GTITLE_Y, 0]))

    def query(self, s):
        return self.put("q", chip(s, YELLOW_M, 22, mono=True).move_to(Q_POS))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def paint(self, cells, color, opacity=0.85):
        return [self.grid[n].animate.set_fill(color, opacity).set_stroke(color) for n in cells]

    def reset_grid(self):
        return [c.animate.set_fill(fillc(BLUE_M, 0.3), 1).set_stroke(BLUE_M) for c in self.grid]

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("17 pages instead of 23,818", "how an index finds one card's payments")

        self.grid = VGroup(*[Square(CELL, stroke_color=BLUE_M, stroke_width=1.5).set_fill(fillc(BLUE_M, 0.3), 1).move_to(cell_xy(n))
                             for n in range(COLS * ROWS)])

        qm = T("?", 48, YELLOW_M).move_to([-3.55, 0.6, 0])
        sc = T("each square: about 100 pages of 8 KB", 18, GREY_B).move_to([GX0 + COLS * PITCH / 2, GSCALE_Y, 0])
        pg = T("(339,35) = page 339, row 35", 18, YELLOW_M).move_to([-3.55, -1.95, 0])

        # ---------------- scene 1: the question ----------------
        self.steps("A customer calls support about a coffee. The support screen asks the database for every payment made with card 4242.", [
            "The support screen",
            (lambda: self.query("card 4242: every payment"), 0.6),
        ])
        self.steps("The table holds about a million payments, and 14 of them are this card's. "
                   "How much does the database have to read to find those 14? Hold that question.", [
            "The table holds",
            (lambda: [FadeIn(self.grid, lag_ratio=0.002), *self.gtitle("payments: about a million")], 1.0),
            "14 of them",
            (lambda: self.paint(CARD, GREEN_M), 0.7),
            "How much",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "Hold that",
            (lambda: self.cap("how much does it read to find 14 rows?", WHITE), 0.5),
        ], after=0.3)

        # ---------------- scene 2: the cookbook ----------------
        card = VGroup(RoundedRectangle(corner_radius=0.14, width=5.6, height=3.1, stroke_color=GOLD_M, stroke_width=3)
                      .set_fill(fillc(GOLD_M), 1).move_to([-3.55, 0.45, 0]))
        card_t = T("the index at the back", 22, GOLD_M).move_to([-3.55, 1.65, 0])
        rows = [VGroup(left_at(T(a, 20, WHITE if a != "..." else GREY_B), -5.9, y), right_at(T(b, 20, GREY_B), -1.2, y))
                for a, b, y in [("garlic", "...", 0.95), ("lemon", "6 pages", 0.4), ("mint", "...", -0.15), ("...", "", -0.6)]]
        self.steps("Start with a cookbook of six hundred pages. Which recipes use lemons? You could turn every page and look.", [
            (lambda: [*self.uncap(), *self.paint(CARD, fillc(BLUE_M, 0.3), 1), FadeOut(qm),
                      *self.query("lemons?"), *self.gtitle("a cookbook: 600 pages", GOLD_M)], 0.7),
            (lambda: [self.grid.animate.set_stroke(GOLD_M).set_fill(fillc(GOLD_M, 0.3), 1)], 0.5),
            "turn every page",
            (lambda: [LaggedStart(*[Indicate(c, color=YELLOW_M, scale_factor=1.0) for c in self.grid], lag_ratio=0.01)], 1.6),
        ])
        self.steps("Or you could open the index at the back, find lemon, and read off six page numbers.", [
            "open the index",
            (lambda: [FadeIn(card), FadeIn(card_t), *[FadeIn(r) for r in rows]], 0.7),
            "find lemon",
            (lambda: [rows[1].animate.set_color(YELLOW_M)], 0.4),
            "six page numbers",
            (lambda: [*[dot_run([-1.3, 0.4, 0], cell_xy(n), YELLOW_M, 0.6) for n in LEMON]], 0.8),
            (lambda: self.paint(LEMON, YELLOW_M), 0.4),
        ])
        no20 = tick(False, 0.3).move_to([-3.55, 0.45, 0]).set_z_index(5)
        self.steps("Now ask the same book for every recipe that takes under 20 minutes. The index is no help at all. "
                   "It's sorted by ingredient, and cooking time isn't in it. Keep that one in your pocket.", [
            (lambda: [*self.query("under 20 minutes?"), *self.paint(LEMON, fillc(GOLD_M, 0.3), 1), rows[1].animate.set_color(WHITE)], 0.6),
            "no help at all",
            (lambda: [Create(no20)], 0.5),
            "sorted by ingredient",
            (lambda: self.cap("sorted by ingredient: cooking time isn't in it", WHITE), 0.6),
            "in your pocket",
            (lambda: [FadeOut(no20)], 0.4),
        ], after=0.3)
        self.stamp("cookbook")

        # ---------------- scene 3: the table, and a sequential scan ----------------
        self.steps("A database table is a book too. PostgreSQL, a free database program, keeps it in pages of 8 KB, "
                   "the block it reads at a time. This table holds 1,000,478 payments in 23,818 pages.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(card, card_t, *rows)), *self.query("card 4242: every payment"),
                      self.grid.animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M, 0.3), 1), *self.gtitle("payments: 23,818 pages")], 0.8),
            "pages of 8 KB",
            (lambda: [FadeIn(sc)], 0.5),
            "This table holds",
            (lambda: self.gtitle("payments: 1,000,478 rows in 23,818 pages"), 0.6),
        ])
        self.steps("Each new row goes wherever there's room, in no particular order. So card 4242's 14 payments are spread across the file.", [
            "spread across",
            (lambda: self.paint(CARD, GREEN_M), 0.7),
            (lambda: [LaggedStart(*[Indicate(self.grid[n], color=GREEN_M, scale_factor=1.4) for n in CARD], lag_ratio=0.08)], 1.2),
        ])
        sweep = Rectangle(width=COLS * PITCH + 0.06, height=PITCH, stroke_color=YELLOW_M, stroke_width=3).move_to(
            [GX0 + COLS * PITCH / 2, GTOP - PITCH / 2, 0]).set_z_index(4)
        self.steps("With nothing else to go on, there's one way to find them: read every page, and test every row. "
                   "That's called a sequential scan.", [
            "read every page",
            (lambda: [Create(sweep), *self.count("pages read: 0")], 0.4),
            (lambda: [Succession(*[sweep.animate(run_time=0.17).move_to([GX0 + COLS * PITCH / 2, GTOP - PITCH * (r + 0.5), 0])
                                   for r in range(1, ROWS)]),
                      LaggedStart(*[AnimationGroup(*[self.grid[n].animate.set_fill(GREY_D, 1).set_stroke(GREY_C)
                                                     for n in range(r * COLS, (r + 1) * COLS) if n not in CARD]) for r in range(ROWS)],
                                  lag_ratio=1.0)], 2.0),
            (lambda: [FadeOut(sweep), *self.count("pages read: 23,818", RED_M)], 0.5),
            "sequential scan",
            (lambda: self.cap("sequential scan: read every page, test every row", WHITE), 0.6),
        ])
        self.steps("PostgreSQL's report of the run says three processes shared the work, and each threw away 333,488 rows. "
                   "That's 23,818 pages for 14 rows, in a quarter of a second. And the cost grows with the table.", [
            "three processes",
            (lambda: self.cap(M("Parallel Seq Scan on payments (... loops=3)", 20, GREY_B)), 0.6),
            "each threw away",
            (lambda: self.cap(M("Rows Removed by Filter: 333488   (in each of 3 processes)", 20, GREY_B)), 0.6),
            "That's 23,818",
            (lambda: [*self.cap("23,818 pages for 14 rows: a quarter of a second", WHITE)], 0.6),
            "grows with the table",
            (lambda: [Indicate(self.lab["cnt"], color=RED_M, scale_factor=1.1)], 0.7),
        ])
        self.steps("It's reading the whole cookbook every time someone wants lemonade. What we want is the cookbook's trick: "
                   "a list at the back that jumps straight to the right pages.", [
            "What we want",
            (lambda: [*self.cap("wanted: a list that jumps straight to the right pages", YELLOW_M), *self.reset_grid(),
                      *self.drop("cnt")], 0.7),
            (lambda: self.paint(CARD, GREEN_M), 0.5),
        ], after=0.3)
        self.stamp("scan")

        # ---------------- scene 4: why not sort the table? ----------------
        orders = VGroup(*[chip(s, PURPLE_M, 22) for s in ("by card", "by shop", "by date")]).arrange(RIGHT, buff=0.35).move_to([-3.55, 0.45, 0])
        one = T("a table has one order", 20, PURPLE_M).move_to([-3.55, -0.3, 0])
        self.steps("First, the obvious idea: why not keep the table itself sorted by card number? Because a table can be in only "
                   "one order, and support asks by card, by shop and by date.", [
            (lambda: self.cap("why not keep the table sorted by card number?", PURPLE_M), 0.6),
            "support asks",
            (lambda: [LaggedStart(*[FadeIn(o, shift=0.1 * UP) for o in orders], lag_ratio=0.3)], 0.9),
            (lambda: [FadeIn(one)], 0.4),
        ])
        self.steps("Keeping it sorted would also mean moving rows to make room whenever a payment lands in the middle. "
                   "So PostgreSQL leaves the table in arrival order, and builds a separate sorted copy.", [
            "moving rows",
            (lambda: self.cap("sorted rows: shuffle rows whenever one lands in the middle", WHITE), 0.6),
            "builds a separate",
            (lambda: [FadeOut(orders), FadeOut(one), *self.cap("keep the table in arrival order; build a sorted copy", WHITE)], 0.6),
        ], after=0.3)

        # ---------------- scene 5: the index, and a row's address ----------------
        root = small_box(ROOT, 1.5, 0.55, "root", TEAL_M, 18)
        inner = [small_box([x, INNER_Y, 0], 1.15, 0.5, "inner", TEAL_M, 16) for x in INNER_X]
        leaves = [small_box([x, LEAF_Y, 0], 0.42, 0.42, "", TEAL_M) for x in LEAF_X]
        e1 = VGroup(*[Line(ROOT + [0, -0.28, 0], [x, INNER_Y + 0.25, 0], stroke_width=1.8, color=GREY_C) for x in INNER_X])
        e2 = VGroup(*[Line([INNER_X[LEAF_OF[k]], INNER_Y - 0.25, 0], [LEAF_X[k], LEAF_Y + 0.21, 0], stroke_width=1.5, color=GREY_C)
                      for k in range(10)])
        leaf_lab = T("1,130 leaves", 18, TEAL_M).move_to([-3.55, LEAF_Y - 0.5, 0])
        self.steps("That copy is the index. The cookbook's index lists every ingredient in order, with its pages. "
                   "Ours lists every card number in order, with the address of each of its rows.", [
            (lambda: [*self.cap(M("CREATE INDEX payments_card_idx ON payments (card_id)", 20, TEAL_M))], 0.6),
            "Ours lists",
            (lambda: [LaggedStart(*[FadeIn(l) for l in leaves], lag_ratio=0.08), FadeIn(leaf_lab)], 0.9),
            "with the address",
            (lambda: [*self.put("call", fit(M("... 4241: ...   4242: (339,35) and 13 more   4243: ...", 17, WHITE), 6.0)
                                .move_to([-3.55, CALL_Y, 0]))], 0.6),
        ])
        addr = CARD[5]
        self.steps("A row's address is its page and its slot on that page. Card 4242's first payment is at 339, 35: "
                   "row 35 on page 339. PostgreSQL calls this address a ctid.", [
            "Card 4242's first",
            (lambda: [dot_run([-3.2, CALL_Y + 0.2, 0], cell_xy(addr), YELLOW_M, 0.7)], 0.8),
            (lambda: [Indicate(self.grid[addr], color=YELLOW_M, scale_factor=1.6),
                      FadeIn(pg)], 0.6),
            "a ctid",
            (lambda: self.cap("a row's address (page, slot) is called a ctid", WHITE), 0.6),
        ], after=0.2)

        # ---------------- scene 6: the tree ----------------
        self.steps("A million sorted card numbers still fill 1,130 pages, called leaves. That's still a lot to search.", [
            (lambda: [FadeOut(pg), *self.cap("1,130 leaf pages: still a lot to search", WHITE)], 0.6),
            "a lot to search",
            (lambda: [LaggedStart(*[glow(l[0], TEAL_M, 1.15) for l in leaves], lag_ratio=0.1)], 1.0),
        ])
        self.steps("So above every 283 or so leaves, PostgreSQL adds an inner page that says which card number each leaf starts with, "
                   "and one root page above those. A big book's index does the same with letter headings: "
                   "you find L before you look for lemon.", [
            "an inner page",
            (lambda: [*[FadeIn(b) for b in inner], Create(e2)], 0.8),
            "one root page",
            (lambda: [FadeIn(root), Create(e1)], 0.7),
            "letter headings",
            (lambda: self.cap("like letter headings: find L before you look for lemon", WHITE), 0.6),
        ])
        self.steps("The result is a B+tree, a tree of pages where each level narrows the search: one root, 4 inner pages "
                   "and 1,130 leaves.", [
            "a B+tree",
            (lambda: self.cap("B+tree: 1 root, 4 inner pages, 1,130 leaves", TEAL_M), 0.6),
            "one root",
            (lambda: [glow(root[0], TEAL_M, 1.1)], 0.5),
            "4 inner",
            (lambda: [*[glow(b[0], TEAL_M, 1.1) for b in inner]], 0.5),
            "1,130 leaves",
            (lambda: [*[glow(l[0], TEAL_M, 1.15) for l in leaves]], 0.5),
        ], after=0.3)
        self.stamp("tree")

        # ---------------- scene 7: predict, then walk ----------------
        self.steps("So how many pages does card 4242 cost now? Pause and guess.", [
            (lambda: [*self.cap("how many pages for card 4242 now?  pause and guess", YELLOW_M), *self.reset_grid()], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("One walk down the tree: the root, an inner page and a leaf. That's 3 pages, and the leaf holds the 14 addresses. "
                   "Then the 14 table pages they point to.", [
            (lambda: [*self.uncap(), root[0].animate.set_fill(YELLOW_M, 0.35).set_stroke(YELLOW_M), *self.count("index pages: 1")], 0.5),
            (lambda: [dot_run(ROOT + [0, -0.28, 0], [INNER_X[1], INNER_Y + 0.25, 0], YELLOW_M, 0.4)], 0.45),
            (lambda: [inner[1][0].animate.set_fill(YELLOW_M, 0.35).set_stroke(YELLOW_M), *self.count("index pages: 2")], 0.4),
            (lambda: [dot_run([INNER_X[1], INNER_Y - 0.25, 0], [LEAF_X[4], LEAF_Y + 0.21, 0], YELLOW_M, 0.4)], 0.45),
            (lambda: [leaves[4][0].animate.set_fill(YELLOW_M, 0.6).set_stroke(YELLOW_M), *self.count("index pages: 3")], 0.4),
            "the leaf holds",
            (lambda: [Indicate(self.lab["call"], color=YELLOW_M, scale_factor=1.06)], 0.7),
            "Then the 14",
            (lambda: [LaggedStart(*[dot_run([LEAF_X[4], LEAF_Y - 0.21, 0], cell_xy(n), GREEN_M, 0.5) for n in CARD], lag_ratio=0.12)], 1.6),
            (lambda: [*self.paint(CARD, GREEN_M), *self.count("3 index pages + 14 table pages = 17", GREEN_M)], 0.5),
        ])
        self.steps("17 pages in all, instead of 23,818. A quarter of a millisecond instead of a quarter of a second: "
                   "about a thousand times faster. Same 14 rows, same coffee, a lot less reading.", [
            "instead of 23,818",
            (lambda: self.cap("17 pages instead of 23,818", WHITE), 0.5),
            "A quarter of a millisecond",
            (lambda: self.cap("0.25 ms instead of 250 ms: about a thousand times faster", WHITE), 0.6),
            "Same 14 rows",
            (lambda: [LaggedStart(*[Indicate(self.grid[n], color=GREEN_M, scale_factor=1.4) for n in CARD], lag_ratio=0.06)], 1.0),
        ], after=0.3)
        self.stamp("walk")

        # ---------------- scene 8: the guardrail ----------------
        self.steps("Now, the question in your pocket. This index is sorted by card. Ask for payments by anything else, and its order "
                   "can't help, just as the cookbook's index couldn't find a quick dinner.", [
            (lambda: self.cap("the index answers questions about its own order: card number", WHITE), 0.6),
            "anything else",
            (lambda: [*self.query("by anything else?")], 0.5),
            "a quick dinner",
            (lambda: [Create(no20.move_to([-1.35, 3.2, 0]))], 0.5),
        ])
        self.steps("And a copy has a cost. This one takes 9 MB, next to the table's 186. Every new payment goes into it too, "
                   "so indexes make reads cheap and writes more expensive.", [
            (lambda: [FadeOut(no20), *self.query("card 4242: every payment")], 0.5),
            "This one takes",
            (lambda: self.count("index: 1,136 pages, 9 MB      table: 23,818 pages, 186 MB", WHITE, 22), 0.6),
            "Every new payment",
            (lambda: [LaggedStart(dot_run([GX0 + 3.2, GTOP + 0.1, 0], [GX0 + 3.2, GTOP - 0.4, 0], WHITE, 0.4),
                                  dot_run([-2.0, LEAF_Y + 0.6, 0], [LEAF_X[6], LEAF_Y + 0.21, 0], WHITE, 0.4), lag_ratio=0.5)], 0.8),
            "reads cheap",
            (lambda: self.cap("indexes make reads cheap and writes more expensive", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: an index is a sorted copy of a few columns, each entry pointing to its row. "
                   "A query is fast when it can find one short run of entries in that copy.", [
            (lambda: [*self.drop("cnt"), *self.cap("an index: a sorted copy, each entry pointing to its row", YELLOW_M, 26)], 0.6),
            "one short run",
            (lambda: [*self.cap("fast when the query finds one short run of entries", YELLOW_M, 26),
                      Indicate(self.lab["call"], color=YELLOW_M, scale_factor=1.06)], 0.7),
        ], after=0.3)
        self.steps("One quick check. Support now asks for every payment at one shop. Does the index on card number help? Pause and think.", [
            (lambda: [*self.uncap(), *self.query("one shop: every payment"), *self.reset_grid()], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        shop = sorted(rng.choice(COLS * ROWS, 16, replace=False).tolist())
        self.steps("No. One shop's payments are spread all over an index sorted by card. It's the quick dinner again, "
                   "so it's back to reading every page.", [
            (lambda: [*self.uncap(), Create(no20.move_to([-1.35, 3.2, 0]))], 0.5),
            "spread all over",
            (lambda: [*[leaves[k][0].animate.set_fill(PURPLE_M, 0.5).set_stroke(PURPLE_M) for k in range(10)]], 0.6),
            "back to reading",
            (lambda: [*self.paint(shop, PURPLE_M), *self.count("pages read: 23,818", RED_M)], 0.6),
        ], after=0.3)
        self.play(*self.cap("an index answers the questions its order answers", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
