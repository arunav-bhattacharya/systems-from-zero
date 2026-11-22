from sfz import *

SAY.insert(0, (r"\bv4\.metadata\.json\b", "v four dot metadata dot jay-son"))
SAY.insert(0, (r"\bParquet\b", "par-kay"))
SAY.insert(0, (r"\b250,067\b", "two hundred fifty thousand and sixty-seven"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PX, MX, LX, NX, FX0 = -5.85, -3.75, -1.0, 1.9, 3.6     # pointer, metadata, manifest lists, manifests, first data file
FP = 0.6                                                 # data file pitch
RY = [1.45, 0.1, -1.25]                                  # rows: S1 / M1, S2 / M2, S3 / M3
HEAD_Y, CNT_Y, CAP_Y, BAR_Y = 2.65, -2.35, -3.3, -2.85
SC = [BLUE_M, TEAL_M, GOLD_M]                            # snapshot / append colours
NOTE_X = 4.35


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

    def note(self, k, s, color=GREY_B, size=18, y=None):
        m = fit(T(s, 22, color), 12.0)
        return self.put("n", m.move_to([0, -2.4, 0]))

    def notes_off(self):
        return self.drop("n")

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.04):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def rbox(c, w, h, color, fill=None):
    return RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(
        fill if fill is not None else fillc(color), 1).move_to(c)


def dot_run(a, b, color=YELLOW_M, rt=0.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0).set_z_index(6)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.1))


def card(name, color, c):
    return VGroup(rbox(c, 1.5, 0.9, color), T(name, 22, color if color is not GREY_C else GREY_B).move_to(c))


def ptr_box(n):
    c = np.array([PX, RY[1], 0])
    return VGroup(rbox(c, 1.45, 1.3, YELLOW_M), M("version-hint", 12, GREY_B).move_to(c + 0.38 * UP),
                  T(str(n), 40, YELLOW_M).move_to(c + 0.12 * DOWN))


def meta_box(v, snaps, cur):
    c = np.array([MX, RY[1], 0])
    lines = [M(f"v{v}.metadata.json", 15, WHITE), T("columns", 19, GREY_B), T("rule: group by day", 19, GREY_B),
             T(f"snapshots: {snaps}", 19, GREY_B), T(f"current: {cur}", 19, SC[int(cur[1]) - 1])]
    g = VGroup(*[fit(l, 2.2) for l in lines]).arrange(DOWN, buff=0.17).move_to(c)
    return VGroup(rbox(c, 2.5, 3.2, WHITE, BLACK), g)


def list_box(k):
    c = np.array([LX, RY[k], 0])
    return VGroup(rbox(c, 2.0, 0.85, SC[k]), T(f"snapshot S{k + 1}", 21).move_to(c + 0.16 * UP),
                  T("manifest list", 17, SC[k]).move_to(c + 0.2 * DOWN))


def man_box(k):
    c = np.array([NX, RY[k], 0])
    return VGroup(rbox(c, 2.0, 0.85, SC[k]), T(f"manifest M{k + 1}", 21).move_to(c + 0.16 * UP),
                  T("3 files, min/max", 17, SC[k]).move_to(c + 0.2 * DOWN))


def files(k):
    return VGroup(*[Square(0.42, stroke_color=SC[k], stroke_width=2).set_fill(fillc(SC[k], 0.35), 1)
                    .move_to([FX0 + FP * j, RY[k], 0]) for j in range(3)])


def link(a, b, color, sw=2):
    return Line(a, b, stroke_width=sw, color=color)


def l2m(k, m):
    """From manifest list k's right edge to manifest m's left edge."""
    return link([LX + 1.0, RY[k] + 0.12 * (1 - m), 0], [NX - 1.0, RY[m] + 0.12 * (1 - k), 0], SC[k])


def m2f(k):
    return link([NX + 1.0, RY[k], 0], [FX0 - 0.21, RY[k], 0], SC[k])


def meta2l(k):
    return link([MX + 1.25, RY[1] + 0.3 * (1 - k), 0], [LX - 1.0, RY[k], 0], GREY_B)


class IcebergSnapshots(Base):
    """batch-11, section 1. The café board hung in one move; one big list is too costly to rewrite; Iceberg builds the
    board from panels: pointer -> metadata file -> manifest list per snapshot -> manifests -> Parquet files. The third
    append of the demo writes 3 files, 1 manifest, 1 manifest list, v4, and moves the pointer 3 -> 4; S3 reuses M1 and
    M2. A reader walks down and skips by statistics (149..250,067). The folder is not the table. Check: delete a file of
    the first append by hand: all three snapshots break."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("A new board without repainting", "Iceberg's tree of files that are never edited")

        # ---------------- scene 1: the half-changed menu ----------------
        names = ["coffee", "tea", "juice", "cake", "toast", "soup"]
        pos = [np.array([-1.8 + 1.8 * (i % 3), 1.0 - 1.2 * (i // 3), 0]) for i in range(6)]
        board = rbox([0, 0.4, 0], 6.0, 3.0, GREY_B, BLACK)
        cards = [card(n, GREY_C, p) for n, p in zip(names, pos)]
        btitle = T("menu board", 20, GREY_B).move_to([0, 2.25, 0])
        self.steps("Picture a café changing its menu. The owner swaps the price cards on the wall one at a time.", [
            (lambda: [FadeIn(board), FadeIn(btitle), LaggedStart(*[FadeIn(c) for c in cards], lag_ratio=0.1)], 1.0),
            "swaps the price cards",
            (lambda: [Transform(cards[0], card("coffee", GOLD_M, pos[0]))], 0.6),
            (lambda: [Transform(cards[1], card("tea", GOLD_M, pos[1]))], 0.6),
            (lambda: [Transform(cards[2], card("juice", GOLD_M, pos[2]))], 0.6),
        ])
        self.steps("A customer who reads the wall halfway through sees new prices for coffee and old ones for cake, "
                   "a menu that never existed.", [
            "new prices for coffee",
            (lambda: [glow(cards[0][0], GOLD_M, 1.06)], 0.6),
            "old ones for cake",
            (lambda: [glow(cards[3][0], GREY_B, 1.06)], 0.6),
            "a menu that never",
            (lambda: self.cap("half new, half old: a menu that never existed", RED_M), 0.6),
        ])
        self.steps("A table kept as a folder of files has the same problem. A job adding 200 files drops them in one by one, "
                   "and a report that reads the folder halfway counts part of the job.", [
            "A job adding",
            (lambda: self.cap("a folder table: 200 new files land one by one", WHITE), 0.6),
            "counts part of the job",
            (lambda: self.cap("a report reading halfway counts part of the job", RED_M), 0.6),
        ])
        newb = VGroup(rbox([0, 0.4, 0], 6.0, 3.0, GOLD_M, BLACK), *[card(n, GOLD_M, p) for n, p in zip(names, pos)])
        newb.shift(9 * RIGHT)
        nail = VGroup(Dot([0, 2.75, 0], radius=0.09, color=YELLOW_M),
                      T("pointer", 20, YELLOW_M).move_to([0.75, 2.75, 0]))
        self.steps("A careful owner fills a new board in the back room, and hangs it in one move. A table can do that too. "
                   "Write every new file first, then a new list of the table's files, then move one pointer to the new list. "
                   "A reader sees the old table or the new one, never a mix.", [
            (lambda: [*self.uncap(), *[Transform(c, card(n, GREY_C, p)) for c, n, p in zip(cards[:3], names, pos)]], 0.5),
            "fills a new board",
            (lambda: [FadeIn(newb)], 0.4),
            "hangs it in one move",
            (lambda: [newb.animate.shift(9 * LEFT), FadeOut(btitle)], 1.0),
            "Write every new file",
            (lambda: [FadeIn(nail, shift=0.1 * DOWN), *self.cap("new files first, then a new list, then move one pointer", WHITE)], 0.6),
            "A reader sees",
            (lambda: self.cap("the old table or the new one, never a mix", GREEN_M), 0.6),
        ], after=0.3)
        self.remove(board, *cards)
        self.stamp("board")

        # ---------------- scene 2: one big list ----------------
        strip = VGroup(rbox([0, 0.4, 0], 2.6, 3.4, WHITE, BLACK),
                       *[Line([-1.0, 1.85 - 0.16 * i, 0], [1.0 - 0.3 * (i % 3), 1.85 - 0.16 * i, 0], stroke_width=2, color=GREY_C)
                         for i in range(18)])
        stitle = T("the list: 1,000,000 lines", 20, WHITE).move_to([0, 2.45, 0])
        add10 = chip("+10 files", GREEN_M, 22).move_to([2.6, 0.4, 0])
        self.steps("But here's the catch. If the list is one file, every change rewrites all of it. "
                   "A table of a million files gets a new million-line list, for a change that adds ten.", [
            (lambda: [FadeOut(newb), FadeOut(nail), *self.uncap()], 0.5),
            "If the list is one file",
            (lambda: [FadeIn(strip), FadeIn(stitle)], 0.7),
            "A table of a million",
            (lambda: [FadeIn(add10, shift=0.1 * LEFT)], 0.5),
            "a new million-line",
            (lambda: [LaggedStart(*[l.animate.set_color(RED_M) for l in strip[1:]], lag_ratio=0.05), strip[0].animate.set_stroke(RED_M)], 1.2),
            (lambda: self.cap("one new list of 1,000,000 lines, for 10 new files", RED_M), 0.6),
        ])
        ghosts = [strip.copy().set_opacity(0.35).shift(0.25 * (j + 1) * (UP + RIGHT)).set_z_index(-1) for j in range(3)]
        self.steps("That's repainting the whole board to change one price. And if we keep the old versions too, "
                   "isn't that a mountain of copies? What we want is to rewrite only what changed. Hold that question.", [
            "repainting the whole board",
            (lambda: self.cap("repainting the whole board to change one price", WHITE), 0.6),
            "a mountain of copies",
            (lambda: [*[FadeIn(g, shift=0.2 * (UP + RIGHT)) for g in ghosts]], 0.8),
            "What we want",
            (lambda: self.cap("wanted: rewrite only what changed", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("list")

        # ---------------- scene 3: panels ----------------
        pw = 1.9
        panels = [VGroup(rbox([-2.0 + 2.0 * k, 0.4, 0], pw, 2.8, SC[k]),
                         card(names[k], SC[k], [-2.0 + 2.0 * k, 0.95, 0]), card(names[k + 3], SC[k], [-2.0 + 2.0 * k, -0.15, 0]))
                  for k in range(3)]
        tags = [T(s, 19, SC[k]).move_to([-2.0 + 2.0 * k, -1.3, 0]) for k, s in enumerate(["reused", "reused", "new"])]
        self.steps("Apache Iceberg is a set of free rules and code for tables made of plain files. Its trick is to build the board from panels.", [
            (lambda: [FadeOut(VGroup(strip, stitle, add10, *ghosts)), *self.uncap()], 0.6),
            "Its trick",
            (lambda: [FadeIn(panels[0]), FadeIn(panels[1])], 0.8),
        ])
        self.steps("A new board reuses the old panels as they are, and adds one new panel for the new cards.", [
            "reuses the old panels",
            (lambda: [FadeIn(tags[0]), FadeIn(tags[1])], 0.5),
            "adds one new panel",
            (lambda: [FadeIn(panels[2], shift=0.4 * LEFT), FadeIn(tags[2])], 0.8),
        ], after=0.3)

        # ---------------- scene 4: the tree, from the top ----------------
        heads = [T(s, 21, GREY_B).move_to([x, HEAD_Y, 0]) for s, x in
                 [("pointer", PX), ("table metadata", MX), ("manifest lists", LX), ("manifests", NX), ("data files", FX0 + FP)]]
        ptr = ptr_box(3)
        meta = meta_box(3, "S1, S2", "S2")
        p2m = Arrow([PX + 0.72, RY[1], 0], [MX - 1.25, RY[1], 0], buff=0.05, stroke_width=3, color=YELLOW_M, max_tip_length_to_length_ratio=0.25)
        lists = [list_box(k) for k in range(3)]
        mans = [man_box(k) for k in range(3)]
        fls = [files(k) for k in range(3)]
        m2l = [meta2l(k) for k in range(3)]
        edges = {(0, 0): l2m(0, 0), (1, 0): l2m(1, 0), (1, 1): l2m(1, 1), (2, 0): l2m(2, 0), (2, 1): l2m(2, 1), (2, 2): l2m(2, 2)}
        mf = [m2f(k) for k in range(3)]
        self.steps("Here's a table after two appends. From the top. The pointer says which version is current. Here, it's a tiny file that says 3.", [
            (lambda: [*[FadeOut(p) for p in panels], *[FadeOut(t) for t in tags], *self.uncap()], 0.6),
            "The pointer",
            (lambda: [FadeIn(heads[0]), FadeIn(ptr)], 0.7),
            "says 3",
            (lambda: [Indicate(ptr[2], color=YELLOW_M)], 0.6),
        ])
        self.steps("It points to the table metadata file. Metadata means data about the data. This file holds the columns, "
                   "the rule for grouping files by day, and the list of the table's versions, called snapshots. One of them is current.", [
            (lambda: [GrowArrow(p2m), FadeIn(heads[1]), FadeIn(meta[0]), FadeIn(meta[1][0])], 0.8),
            "the columns",
            (lambda: [FadeIn(meta[1][1])], 0.4),
            "the rule",
            (lambda: [FadeIn(meta[1][2])], 0.4),
            "called snapshots",
            (lambda: [FadeIn(meta[1][3]), *self.cap("a snapshot: one version of the table", WHITE)], 0.5),
            "One of them",
            (lambda: [FadeIn(meta[1][4])], 0.4),
        ])
        self.steps("Each snapshot has a manifest list: one row per manifest, with the range of days inside it.", [
            (lambda: [FadeIn(heads[2]), *[Create(m2l[k]) for k in range(2)], *[FadeIn(lists[k]) for k in range(2)]], 0.9),
            "one row per manifest",
            (lambda: self.cap("manifest list: one row per manifest, with its range of days", WHITE), 0.6),
        ])
        self.steps("Each manifest has one row per data file: where it is, its day, its row count, "
                   "and the smallest and largest value of every column.", [
            (lambda: [FadeIn(heads[3]), *[FadeIn(mans[k]) for k in range(2)],
                      *[Create(edges[e]) for e in ((0, 0), (1, 0), (1, 1))]], 0.9),
            "where it is",
            (lambda: self.cap("manifest: one row per file: where, which day, how many rows, min and max", WHITE), 0.6),
        ])
        self.steps("And at the bottom, the data files: plain Parquet, a common file format for tables.", [
            (lambda: [FadeIn(heads[4]), *[Create(mf[k]) for k in range(2)], *[FadeIn(fls[k]) for k in range(2)]], 0.9),
        ])
        self.steps("In café terms, a snapshot is a whole board, a manifest is a panel, and the data files are the price cards.", [
            "a snapshot is",
            (lambda: [*self.cap("snapshot = a whole board", WHITE), *[glow(lists[k][0], SC[k], 1.05) for k in range(2)]], 0.7),
            "a manifest is",
            (lambda: [*self.cap("snapshot = a whole board      manifest = a panel", WHITE), *[glow(mans[k][0], SC[k], 1.05) for k in range(2)]], 0.7),
            "the data files",
            (lambda: [*self.cap("snapshot = a whole board      manifest = a panel      data file = a price card", WHITE),
                      *[Indicate(f, color=SC[k], scale_factor=1.1) for k, f in enumerate(fls[:2])]], 0.7),
        ], after=0.3)
        self.stamp("tree")

        # ---------------- scene 5: predict ----------------
        self.steps("In the lesson's demo, the table was created, then got three appends of 1,000 payments, three days each. "
                   "Now the third append. When it's done, how many metadata files will there be? "
                   "And how many manifests will the new snapshot name? Pause and guess.", [
            (lambda: self.cap("create the table, then 3 appends of 1,000 payments", WHITE), 0.6),
            "how many metadata",
            (lambda: [*self.note(0, "metadata files?", YELLOW_M, 20)], 0.5),
            "how many manifests",
            (lambda: [*self.note(1, "metadata files?   manifests named by the new snapshot?", YELLOW_M, 20)], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 6: the commit ----------------
        self.steps("Watch. It writes three data files, and nobody reads them yet. Then one new manifest that lists them.", [
            (lambda: [*self.notes_off(), *self.uncap()], 0.4),
            "It writes three",
            (lambda: [LaggedStart(*[FadeIn(s, scale=0.6) for s in fls[2]], lag_ratio=0.2)], 0.8),
            "nobody reads",
            (lambda: [*self.note(0, "1. three data files (unseen)", GOLD_M)], 0.5),
            "Then one new manifest",
            (lambda: [FadeIn(mans[2]), Create(mf[2]), *self.note(1, "2. one manifest", GOLD_M)], 0.7),
        ])
        self.steps("Then one new manifest list, naming the new manifest plus the two old ones. Then one new metadata file, version 4.", [
            (lambda: [FadeIn(lists[2]), *self.note(2, "3. one manifest list", GOLD_M)], 0.6),
            "naming the new",
            (lambda: [Create(edges[(2, 2)])], 0.4),
            "plus the two old",
            (lambda: [Create(edges[(2, 0)]), Create(edges[(2, 1)])], 0.6),
            "Then one new metadata",
            (lambda: [Transform(meta, meta_box(4, "S1, S2, S3", "S3")), Create(m2l[2]), *self.note(3, "4. metadata v4", GOLD_M)], 0.8),
        ])
        self.steps("And last, one move of the pointer, from 3 to 4.", [
            (lambda: [Transform(ptr[2], T("4", 40, YELLOW_M).move_to(ptr[2])), glow(ptr[0], YELLOW_M, 1.06),
                      *self.note(4, "5. the pointer: 3 → 4", YELLOW_M)], 0.9),
        ])
        self.steps("So four metadata files: one for creating the table, one per append. And the new snapshot names all three manifests. "
                   "Two of them are reused, not copied.", [
            (lambda: [*self.cap("metadata files: 4      manifest lists: 3      manifests: 3      data files: 9", WHITE)], 0.6),
            "all three manifests",
            (lambda: [*[glow(mans[k][0], SC[k], 1.05) for k in range(3)]], 0.7),
            "Two of them are reused",
            (lambda: [edges[(2, 0)].animate.set_stroke(width=5), edges[(2, 1)].animate.set_stroke(width=5)], 0.6),
        ])
        self.steps("That's why snapshots are cheap. Two snapshots share every manifest that didn't change.", [
            (lambda: [*self.cap("snapshots share every manifest that didn't change", YELLOW_M)], 0.6),
            "share every manifest",
            (lambda: [Indicate(VGroup(edges[(0, 0)], edges[(1, 0)], edges[(2, 0)]), color=YELLOW_M, scale_factor=1.0)], 0.9),
        ])
        self.steps("Here the café picture breaks, in a useful place. A café throws its old board away. "
                   "Iceberg keeps the old snapshots, and they share most of their cards with the new one.", [
            (lambda: [*self.notes_off(), *self.cap("where the café picture breaks", WHITE)], 0.5),
            "Iceberg keeps",
            (lambda: [*self.cap("old snapshots stay, sharing most of their cards", WHITE),
                      *[glow(lists[k][0], SC[k], 1.05) for k in range(2)]], 0.8),
        ], after=0.3)
        self.stamp("commit")

        # ---------------- scene 7: a reader walks down ----------------
        bounds = T("amounts in M3's files: 149 to 250,067 cents", 20, GOLD_M).move_to([FX0 + FP - 0.3, RY[2] - 0.75, 0])
        self.steps("A reader walks the tree from the top: the pointer, the metadata, the current snapshot, and its manifest list.", [
            (lambda: [*self.cap("a reader walks down from the top", WHITE)], 0.5),
            "the pointer",
            (lambda: [glow(ptr[0], YELLOW_M, 1.06), dot_run([PX + 0.7, RY[1], 0], [MX - 1.25, RY[1], 0], YELLOW_M, 0.5)], 0.6),
            "the metadata",
            (lambda: [glow(meta[0], WHITE, 1.03), dot_run([MX + 1.25, RY[1] - 0.3, 0], [LX - 1.0, RY[2], 0], YELLOW_M, 0.5)], 0.6),
            "the current snapshot",
            (lambda: [glow(lists[2][0], GOLD_M, 1.06)], 0.5),
        ])
        self.steps("Then it opens only the manifests whose days can match, and only the files whose smallest and largest values can match. "
                   "In the newest manifest, amounts run from 149 to 250,067 cents.", [
            "opens only the manifests",
            (lambda: [LaggedStart(*[dot_run(edges[(2, m)].get_start(), edges[(2, m)].get_end(), YELLOW_M, 0.5) for m in range(3)], lag_ratio=0.2)], 0.9),
            "only the files",
            (lambda: [dot_run(mf[2].get_start(), mf[2].get_end(), YELLOW_M, 0.5)], 0.6),
            "In the newest",
            (lambda: [FadeIn(bounds, shift=0.1 * LEFT)], 0.6),
        ])
        skip = VGroup(*[tick(False, 0.22).move_to(s) for s in fls[2]]).set_z_index(5)
        self.steps("Ask for amounts above that, and all three of its files are skipped without opening one. "
                   "And notice: the reader never lists the folder.", [
            "Ask for amounts",
            (lambda: [*self.cap(M("WHERE amount_cents > 250067", 22, YELLOW_M))], 0.5),
            "all three",
            (lambda: [Create(skip), *[s.animate.set_fill(GREY_D, 1).set_stroke(GREY_C) for s in fls[2]]], 0.8),
            "never lists the folder",
            (lambda: self.cap("skipped without opening; the folder is never listed", WHITE), 0.6),
        ], after=0.3)

        # ---------------- scene 8: the folder is not the table ----------------
        stray = Square(0.42, stroke_color=GREY_B, stroke_width=2).set_fill(GREY_D, 1).move_to([FX0 + FP, -2.0, 0])
        stray_l = T("copied in by hand", 19, GREY_B).next_to(stray, RIGHT, buff=0.2)
        self.steps("That cuts both ways. Copy a file into the folder by hand, and no reader ever sees it. "
                   "It's a card pinned to the wall behind the board.", [
            (lambda: [FadeOut(skip), FadeOut(bounds), *[s.animate.set_fill(fillc(GOLD_M, 0.35), 1).set_stroke(GOLD_M) for s in fls[2]],
                      *self.uncap()], 0.5),
            "Copy a file",
            (lambda: [FadeIn(stray, shift=0.2 * UP), FadeIn(stray_l)], 0.6),
            "no reader",
            (lambda: [*self.cap("no manifest names it: invisible", WHITE)], 0.5),
            "a card pinned",
            (lambda: self.cap("a card pinned to the wall behind the board", WHITE), 0.5),
        ])
        gone = tick(False, 0.22).move_to(fls[0][0]).set_z_index(5)
        self.steps("Delete a file by hand, and every snapshot that lists it breaks. The snapshot is the table, not the folder. "
                   "Change the table through Iceberg.", [
            "Delete a file",
            (lambda: [FadeOut(stray), FadeOut(stray_l), fls[0][0].animate.set_fill(BLACK, 1).set_stroke(RED_M), Create(gone)], 0.6),
            "every snapshot",
            (lambda: [glow(mans[0][0], RED_M, 1.06), *self.cap("every snapshot that lists it breaks", RED_M)], 0.7),
            "The snapshot is the table",
            (lambda: self.cap("the snapshot is the table, not the folder: change it through Iceberg", YELLOW_M), 0.6),
        ], after=0.3)
        self.stamp("folder")

        # ---------------- scene 9: moral and check ----------------
        self.steps("So the moral of the story. Files are written once and never edited. The tree reuses everything below what changed. "
                   "And one pointer move makes a new version appear whole.", [
            (lambda: [FadeOut(gone), fls[0][0].animate.set_fill(fillc(BLUE_M, 0.35), 1).set_stroke(BLUE_M),
                      *self.cap("files are written once, never edited", WHITE)], 0.6),
            "The tree reuses",
            (lambda: [*self.cap("the tree reuses everything below what changed", WHITE),
                      edges[(2, 0)].animate.set_stroke(width=5), edges[(2, 1)].animate.set_stroke(width=5)], 0.6),
            "one pointer move",
            (lambda: [*self.cap("one pointer move: a new version, whole", YELLOW_M), glow(ptr[0], YELLOW_M, 1.06)], 0.6),
        ], after=0.3)
        self.steps("One quick check. Someone deletes, by hand, a data file that the first append wrote. Which snapshots break? Pause and think.", [
            (lambda: [*self.uncap()], 0.3),
            "a data file",
            (lambda: [fls[0][1].animate.set_fill(BLACK, 1).set_stroke(RED_M)], 0.5),
            "Pause and think",
            (lambda: self.cap("which snapshots break?  pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("All three. Manifest 1 is shared by every snapshot, so every board loses that card.", [
            (lambda: [*self.cap("all three: M1 is shared by every snapshot", RED_M),
                      *[l[0].animate.set_stroke(RED_M) for l in lists]], 0.7),
            "Manifest 1",
            (lambda: [Indicate(VGroup(edges[(0, 0)], edges[(1, 0)], edges[(2, 0)]), color=RED_M, scale_factor=1.0)], 0.9),
        ], after=0.3)
        self.wait(2.0)
