from sfz import *

# The letter A naming a pod, worker or node: Kokoro reads a capital A inside a sentence as the article "uh".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b(?!')", lambda m: m.group(0) if m.group(1) is not None else "eh"))


def _layer(m):
    """Text above chips above arrows above boxes. Box fills are opaque, so without this an animated box
    rectangle is redrawn over its own label."""
    for x in m.get_family():
        if isinstance(x, Text):
            x.set_z_index(4)
        elif isinstance(x, Arrow):
            x.set_z_index(1)
        elif isinstance(x, RoundedRectangle) and 0 < x.get_fill_opacity() < 0.5:
            x.set_z_index(2)


def flash(m, color=YELLOW_M, buff=0.1, scale=1.05):
    """Highlight a box without filling it (Indicate turns an opaque box into a solid block):
    a quick pulse plus an outline drawn and faded around it."""
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.14, stroke_width=4)
    return AnimationGroup(m.animate(rate_func=there_and_back).scale(scale),
                          Succession(Create(r, run_time=0.5), FadeOut(r, run_time=0.5)))


class Layered(VoiceScene):
    def play(self, *anims, **kw):
        for a in anims:
            _layer(a.mobject)
            if getattr(a, "target_mobject", None) is not None:
                _layer(a.target_mobject)
        for m in self.mobjects:
            _layer(m)
        super().play(*anims, **kw)
        for m in self.mobjects:
            _layer(m)


class IcebergSnapshots(Layered):
    """data-09: a folder of files shows half a write; Iceberg's metadata tree, an atomic pointer swap, and time travel.
    Names follow the lesson: pointer, v2/v3.metadata.json, snapshots S1/S2, manifests M1/M2, data files d1..d5."""

    def construct(self):
        self.title_card("Iceberg", "snapshots, manifests and time travel")

        YC, YM, YL, YA, YD = 3.05, 1.7, 0.35, -1.0, -2.4      # catalog, metadata, manifest list, manifest, data
        XL, XR = -2.3, 3.0
        FX = [-3.7, -2.3, -0.9, 2.3, 3.7]
        LIFT = 1.8                                              # the folder starts higher, then drops to make room

        def dfile(i, color=WHITE):
            return mbox(f"d{i + 1}", color, w=1.15, h=0.7, size=22).move_to([FX[i], YD + LIFT, 0])

        files = [dfile(i) for i in range(3)]
        folder = RoundedRectangle(corner_radius=0.14, width=9.0, height=1.1, stroke_color=GREY_B, stroke_width=2).move_to([0, YD + LIFT, 0])
        f_lab = M("s3://lake/payments/", 22, GREY_B).next_to(folder, DOWN, buff=0.2).align_to(folder, LEFT)
        reader = box("reader", BLUE_M, w=1.8, size=26).move_to([-3.6, 1.5, 0])
        r_arrow = edge_arrow(reader, folder, BLUE_M)

        self.beat("A table in a data lake is often just a folder of Parquet files. To read the table, a reader lists the folder and reads every file in it.",
                  Create(folder), FadeIn(f_lab), LaggedStart(*[FadeIn(f, shift=0.2 * UP) for f in files], lag_ratio=0.2),
                  FadeIn(reader), GrowArrow(r_arrow), run_time=2.8)

        job = box("nightly job", TEAL_M, w=2.6, size=26).move_to([3.0, 1.5, 0])
        f4 = dfile(3, TEAL_M)
        j4 = edge_arrow(job, f4, TEAL_M)
        self.beat("A nightly job adds two new files to the table. It writes them one at a time.",
                  FadeIn(job), Succession(Wait(0.8), GrowArrow(j4), FadeIn(f4, shift=0.2 * DOWN)), run_time=2.6)

        half = T("half a write", 26, RED_M).next_to(reader, UP, buff=0.3)
        self.beat("A reader that lists the folder right now sees the first new file, but not the second. It reads half a write.",
                  LaggedStart(*[f[0].animate.set_stroke(BLUE_M, width=5) for f in (*files, f4)], lag_ratio=0.15),
                  Succession(Wait(1.4), FadeIn(half)), run_time=2.6)

        crash = tick(False, 0.3).next_to(job, RIGHT, buff=0.3)
        self.beat("And if the job crashes now, the half-written batch stays in the table for good. A folder has no single moment when a write happens.",
                  FadeIn(crash), job[0].animate.set_stroke(RED_M), f4[0].animate.set_stroke(RED_M), f4[1].animate.set_color(RED_M), run_time=1.6)

        # --- Iceberg's metadata tree, built from the bottom up
        for f in files:                         # drop each file and give back its white outline in one move
            f.generate_target()
            f.target.shift(LIFT * DOWN)
            f.target[0].set_stroke(WHITE, width=3)
        self.beat("Iceberg fixes this with a small tree of metadata that names exactly which files belong to the table.",
                  FadeOut(VGroup(job, crash, j4, f4, half, reader, r_arrow)),
                  *[MoveToTarget(f) for f in files], folder.animate.shift(LIFT * DOWN), f_lab.animate.shift(LIFT * DOWN), run_time=1.8)

        man_a = box("manifest M1", PURPLE_M, w=2.4, h=0.7, size=24).move_to([XL, YA, 0])
        a_arrows = VGroup(*[edge_arrow(man_a, f, PURPLE_M) for f in files])
        self.beat("At the bottom are the data files, as before. Above them, a manifest lists data files, with each file's row count and the minimum and maximum of every column.",
                  FadeIn(man_a, shift=0.2 * UP), LaggedStart(*[GrowArrow(a) for a in a_arrows], lag_ratio=0.2), run_time=2.2)

        list_1 = box("manifest list", GOLD_M, w=2.6, h=0.7, size=24).move_to([XL, YL, 0])
        l1_a = edge_arrow(list_1, man_a, GOLD_M)
        snap_1 = T("snapshot S1", 24, GOLD_M).next_to(list_1, LEFT, buff=0.3)
        self.beat("A manifest list names every manifest in one snapshot. A snapshot is the whole table at one moment.",
                  FadeIn(list_1, shift=0.2 * UP), GrowArrow(l1_a), Succession(Wait(1.6), FadeIn(snap_1)), run_time=2.6)

        meta_1 = mbox("v2.metadata.json", TEAL_M, w=3.2, h=0.7, size=20).move_to([XL, YM, 0])
        m1_l = edge_arrow(meta_1, list_1, TEAL_M)
        cat = box("pointer", YELLOW_M, w=2.0, h=0.7, size=24).move_to([(XL + XR) / 2, YC, 0])
        ptr = edge_arrow(cat, meta_1, YELLOW_M)
        self.beat("The metadata file holds the table's schema and its list of snapshots. The catalog keeps one pointer: which metadata file is current. Every reader starts there.",
                  Succession(AnimationGroup(FadeIn(meta_1, shift=0.2 * UP), GrowArrow(m1_l)), Wait(1.6),
                             AnimationGroup(FadeIn(cat, shift=0.2 * UP), GrowArrow(ptr))), run_time=4.0)

        # --- a commit: new files, new metadata, one pointer swap
        new = [mbox(f"d{i + 1}", TEAL_M, w=1.15, h=0.7, size=22).move_to([FX[i], YD, 0]) for i in (3, 4)]
        self.beat("Now the job writes two new files. No reader sees them yet, because nothing points at them.",
                  LaggedStart(*[FadeIn(f, shift=0.2 * UP) for f in new], lag_ratio=0.4), run_time=1.6)

        man_b = box("manifest M2", PURPLE_M, w=2.4, h=0.7, size=24).move_to([XR, YA, 0])
        b_arrows = VGroup(*[edge_arrow(man_b, f, PURPLE_M) for f in new])
        list_2 = box("manifest list", GOLD_M, w=2.6, h=0.7, size=24).move_to([XR, YL, 0])
        l2_b = edge_arrow(list_2, man_b, GOLD_M)
        l2_a = edge_arrow(list_2, man_a, GOLD_M)
        snap_2 = T("snapshot S2", 24, GOLD_M).next_to(list_2, RIGHT, buff=0.3)
        meta_2 = mbox("v3.metadata.json", TEAL_M, w=3.2, h=0.7, size=20).move_to([XR, YM, 0])
        m2_l = edge_arrow(meta_2, list_2, TEAL_M)
        m2_old = edge_arrow(meta_2, list_1, GREY_B)
        self.beat("The job writes a manifest for them, then a manifest list that reuses the old manifest, then a new metadata file that knows both snapshots.",
                  Succession(AnimationGroup(FadeIn(man_b, shift=0.2 * UP), *[GrowArrow(a) for a in b_arrows], run_time=1.0), Wait(0.6),
                             AnimationGroup(FadeIn(list_2, shift=0.2 * UP), GrowArrow(l2_b), GrowArrow(l2_a), FadeIn(snap_2), run_time=1.0), Wait(0.8),
                             AnimationGroup(FadeIn(meta_2, shift=0.2 * UP), GrowArrow(m2_l), GrowArrow(m2_old), run_time=1.0)),
                  run_time=6.0)

        ptr2 = edge_arrow(cat, meta_2, YELLOW_M)
        self.beat("Then it swaps the catalog's pointer to the new metadata file. That one swap is the commit. A reader sees all of snapshot two, or none of it.",
                  Succession(Wait(0.6), Transform(ptr, ptr2, run_time=1.0), flash(cat)), run_time=3.0)

        def path(mobs, color):
            anims = []
            for m in mobs:
                if isinstance(m, Arrow):
                    anims.append(m.animate.set_color(color))
                else:
                    anims.append(m[0].animate.set_stroke(color, width=5))
            return anims

        def restore(pairs):
            anims = []
            for m, c in pairs:
                if isinstance(m, Arrow):
                    anims.append(m.animate.set_color(c))
                else:
                    anims.append(m[0].animate.set_stroke(c, width=3))
            return anims

        old_path = [meta_1, m1_l, list_1, l1_a, man_a, *a_arrows, *files]
        old_cols = [(meta_1, TEAL_M), (m1_l, TEAL_M), (list_1, GOLD_M), (l1_a, GOLD_M), (man_a, PURPLE_M),
                    *[(a, PURPLE_M) for a in a_arrows], *[(f, WHITE) for f in files]]
        self.beat("A reader that started a moment earlier still holds the old metadata file. It reads snapshot one to the end, and nothing it needs has changed.",
                  *path(old_path, BLUE_M), run_time=1.6)

        tt = chip("VERSION AS OF S1", BLUE_M, 22, mono=True).move_to([4.6, YC, 0])
        self.beat("Old snapshots stay in the metadata, and their files stay in storage. So you can still ask for the table as it was in snapshot one. That is time travel.",
                  *restore([(meta_1, TEAL_M), (m1_l, TEAL_M)]), FadeIn(tt, shift=0.2 * LEFT),
                  m2_old.animate.set_color(BLUE_M), meta_2[0].animate.set_stroke(BLUE_M, width=5), run_time=2.2)

        self.beat("Files never change. Each commit adds a snapshot and moves one pointer, and every old snapshot stays readable until you expire it.",
                  *restore([(m2_old, GREY_B), (meta_2, TEAL_M), (list_1, GOLD_M), (l1_a, GOLD_M), (man_a, PURPLE_M),
                            *[(a, PURPLE_M) for a in a_arrows], *[(f, WHITE) for f in files]]),
                  FadeOut(tt), Succession(Wait(1.0), Indicate(ptr, color=YELLOW_M), AnimationGroup(flash(list_1, GOLD_M), flash(list_2, GOLD_M))),
                  run_time=4.0)
        self.wait(0.6)
