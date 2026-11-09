from sfz import *

KW, KH, KP = 0.72, 0.5, 0.82                        # a key's box and the pitch between keys
IN_Y, OUT_Y, CNT_Y = 2.75, -1.5, -2.25              # input row, output row, counts
IN_X = [-4.25 + i * KP for i in range(12)]
MEM_X = [-4.53 + j * KP for j in range(4)]          # memory: room for 4 keys
MEM_Y = 1.2
RUN_Y = [1.2, 0.45, -0.3]                           # runs on disk
RUN_X = [1.6 + j * KP for j in range(4)]
LAB_X, TOP_Y = -6.25, 1.95
KEYS = [201, 200, 201, 402, 500, 201, 200, 404, 201, 402, 200, 201]
KC = {200: GREEN_M, 201: TEAL_M, 402: GOLD_M, 404: PURPLE_M, 500: RED_M}


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def key(v, x, y):
    c = KC[v]
    r = RoundedRectangle(corner_radius=0.08, width=KW, height=KH, stroke_color=c, stroke_width=2.5).set_fill(fill(c, 0.25), 1)
    return VGroup(r, M(str(v), 20)).move_to([x, y, 0]).set_z_index(2)   # always above the boxes it moves through


def frame_box(x0, x1, y0, y1, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=y1 - y0, stroke_color=color, stroke_width=2.5)
    return r.set_fill(BLACK, 1).move_to([(x0 + x1) / 2, (y0 + y1) / 2, 0])


def lab(s, x, y, size=20, color=GREY_B):
    t = T(s, size, color)
    return t.move_to([x + t.width / 2, y, 0])


def row(path, count, y):
    p = M(path, 18)
    c = M(count, 18, GREY_A)
    return VGroup(p.move_to([-3.6 + p.width / 2, y, 0]), c.move_to([3.6 - c.width / 2, y, 0]))


class ExternalSort(Base):
    """batch-02, section 3 (with section 2's hash map first): counting paths with a hash map needs one entry per distinct
    path (351,305 in the log, ~111 bytes each; a 64 MB heap died at ~617,000). External merge sort on the lesson's 12
    status codes with memory for 4: three sorted runs, one 3-way merge taking the smallest head, then one counting scan.
    At scale: 100 GB, 1 GB buffer, 100 runs; fan-in 16 takes two passes, 128 takes one."""

    def construct(self):
        self.title_card("External merge sort", "counting keys that don't fit in memory")

        log = chip("access.log: 2,000,000 lines, one per request", GREY_B, 20).move_to([0, 2.85, 0])
        heap = frame_box(-4.0, 4.0, -0.7, 1.8)
        hlab = lab("memory: a hash map from path to count", -4.0, 2.1)
        rows = [row("/v1/authorizations", "100,759", 1.4), row("/v1/captures", "59,071", 0.95),
                row("/v1/payments/pay_0556303", "1", 0.5), row("/v1/payments/pay_0556304", "1", 0.05)]
        self.steps("Your payments API logs one line per request. To count requests per path, the quickest way is a hash map "
                   "in memory: read each line once, and add one to its path's count.", [
            (lambda: [FadeIn(log, shift=0.15 * DOWN)], 0.7),
            "the quickest way",
            (lambda: [FadeIn(heap), FadeIn(hlab)], 0.8),
            "read each line",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.15 * DOWN) for r in rows[:2]], lag_ratio=0.4)], 1.0),
        ])

        more = T("and 351,301 more", 19, GREY_B).move_to([0, -0.4, 0])
        bar = Rectangle(width=8.0, height=0.34, stroke_color=GREY_B, stroke_width=2).move_to([0, -1.25, 0])
        used = Rectangle(width=0.01, height=0.34, stroke_width=0).set_fill(TEAL_M, 0.7)
        used.move_to([-4.0 + 0.005, -1.25, 0])
        blab = lab("heap used", -4.0, -1.7, 18)
        cap = T("64 MB", 18, GREY_B)
        cap.move_to([4.0 - cap.width / 2, -1.7, 0])
        size = chip("351,305 paths × about 111 bytes = 39 MB", TEAL_M, 20).move_to([0, -2.55, 0])
        self.steps("But the map needs an entry for every different path, and every payment has its own page. "
                   "Yesterday's log has about 350,000 of them, at about 111 bytes each.", [
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.15 * DOWN) for r in rows[2:]], lag_ratio=0.4)], 1.0),
            "and every payment",
            (lambda: [rows[2][0].animate.set_color(TEAL_M), rows[3][0].animate.set_color(TEAL_M)], 0.6),
            "Yesterday's log",
            (lambda: [FadeIn(more), Create(bar), FadeIn(blab), FadeIn(cap)], 0.8),
            (lambda: [used.animate.stretch_to_fit_width(8.0 * 39 / 64).move_to([-4.0 + 4.0 * 39 / 64, -1.25, 0])], 1.2),
            "at about 111",
            (lambda: [FadeIn(size, shift=0.15 * UP)], 0.7),
        ])

        oom = chip("OutOfMemoryError after about 617,000 paths", RED_M, 20).move_to(size)
        self.steps("The map can't drop an entry until the last line is read. In the lesson's demo, "
                   "a 64 megabyte heap ran out after about 617,000 paths, and the job died.", [
            (lambda: [glow(heap, TEAL_M, 1.02)], 1.0),
            "a 64 megabyte",
            (lambda: [used.animate.stretch_to_fit_width(8.0).move_to([0, -1.25, 0]).set_fill(RED_M, 0.7)], 1.6),
            "and the job died",
            (lambda: [FadeTransform(size, oom), heap.animate.set_stroke(RED_M)], 0.8),
        ])

        keys = [key(v, IN_X[i], IN_Y) for i, v in enumerate(KEYS)]
        ilab = lab("input", LAB_X, IN_Y)
        mem = frame_box(MEM_X[0] - 0.56, MEM_X[3] + 0.56, MEM_Y - 0.45, MEM_Y + 0.45)
        mlab = lab("memory: room for 4 keys", MEM_X[0] - 0.56, TOP_Y)
        disk = frame_box(0.2, 4.75, -0.75, MEM_Y + 0.45)
        dlab = lab("disk", 0.2, TOP_Y)
        olab = lab("output", LAB_X, OUT_Y)
        self.steps("Sorting brings equal keys together too, and an external merge sort never needs all the keys in memory "
                   "at once. Shrink it to see how: twelve keys, and room for four.", [
            (lambda: [*[FadeOut(m) for m in (*rows, more, bar, used, blab, cap, oom, log)], heap.animate.set_stroke(GREY_B)], 0.8),
            "and an external",
            (lambda: [ReplacementTransform(heap, mem), FadeTransform(hlab, mlab)], 0.9),
            "twelve keys",
            (lambda: [LaggedStart(*[FadeIn(k, shift=0.15 * DOWN) for k in keys], lag_ratio=0.08), FadeIn(ilab)], 1.0),
            "and room for four",
            (lambda: [glow(mem, GREY_A, 1.03), FadeIn(disk), FadeIn(dlab), FadeIn(olab)], 0.9),
        ])

        runs, rlabs = [], []

        def batch(b, rt):
            ks = keys[4 * b:4 * b + 4]
            order = sorted(range(4), key=lambda j: (KEYS[4 * b + j], j))
            srt = [ks[j] for j in order]
            runs.append(srt)
            rl = lab(f"run {b + 1}", 0.45, RUN_Y[b], 19)
            rlabs.append(rl)
            return [
                (lambda: [*[k.animate.move_to([MEM_X[j], MEM_Y, 0]) for j, k in enumerate(ks)]], rt),
                (lambda: [*[k.animate.move_to([MEM_X[j], MEM_Y, 0]) for j, k in enumerate(srt)]], rt),
                (lambda: [*[k.animate.move_to([RUN_X[j], RUN_Y[b], 0]) for j, k in enumerate(srt)], FadeIn(rl)], rt),
            ]

        self.steps("Read four keys, sort them in memory, and write them to disk. A sorted file like this is called a run.", [
            *batch(0, 0.8)[:2],
            "and write them",
            (lambda: [*[k.animate.move_to([RUN_X[j], RUN_Y[0], 0]) for j, k in enumerate(runs[0])], FadeIn(rlabs[0])], 0.8),
            "is called a run",
            (lambda: [glow(VGroup(*[k[0] for k in runs[0]]), YELLOW_M, 1.04)], 0.9),
        ])

        self.steps("Do that twice more. The input has been read once, and every key now sits in one of three sorted runs.", [
            *batch(1, 0.5),
            *batch(2, 0.5),
            "and every key",
            (lambda: [glow(disk, GREY_A, 1.02)], 0.9),
        ])

        ptr = [0, 0, 0]
        out = []
        self.steps("Now merge all three runs in one pass. Memory holds just the first key of each run, its head.", [
            "Memory holds",
            (lambda: [*[runs[r][0].animate.move_to([MEM_X[r], MEM_Y, 0]) for r in range(3)]], 1.0),
            "its head",
            (lambda: [*[glow(runs[r][0][0], YELLOW_M, 1.08) for r in range(3)]], 0.9),
        ])

        def take():
            """Write the smallest head to the output and refill its slot from the same run."""
            r = min((r for r in range(3) if ptr[r] < 4), key=lambda r: (KEYS_OF(runs[r][ptr[r]]), r))
            k = runs[r][ptr[r]]
            n = len(out)
            out.append(k)
            ptr[r] += 1
            anims = [k.animate.move_to([IN_X[n], OUT_Y, 0])]
            if ptr[r] < 4:
                anims.append(runs[r][ptr[r]].animate.move_to([MEM_X[r], MEM_Y, 0]))
            return r, anims

        val = {id(k): v for k, v in zip(keys, KEYS)}

        def KEYS_OF(k):
            return val[id(k)]

        def smallest():
            r = min((r for r in range(3) if ptr[r] < 4), key=lambda r: (KEYS_OF(runs[r][ptr[r]]), r))
            return runs[r][ptr[r]]

        self.steps("Take the smallest head and write it out. Then refill from the run it came from, and repeat.", [
            (lambda: [glow(smallest()[0], YELLOW_M, 1.1)], 0.6),
            (lambda: take()[1], 0.8),
            "Then refill",
            (lambda: [glow(smallest()[0], YELLOW_M, 1.1)], 0.5),
            (lambda: take()[1], 0.7),
            (lambda: take()[1], 0.7),
        ])

        self.steps("When the runs are empty, the output is sorted, and memory never held more than three keys.", [
            *[(lambda: take()[1], 0.4) for _ in range(9)],
            "and memory never",
            (lambda: [*[FadeOut(r) for r in rlabs], glow(mem, YELLOW_M, 1.03)], 0.9),
        ])

        groups = [(0, 3), (3, 8), (8, 10), (10, 11), (11, 12)]
        marks = []
        for a, b in groups:
            x0, x1 = IN_X[a] - KW / 2, IN_X[b - 1] + KW / 2
            c = KC[KEYS_OF(out[a])]
            marks.append(VGroup(Line([x0 + 0.04, OUT_Y - 0.4, 0], [x1 - 0.04, OUT_Y - 0.4, 0], stroke_width=3, color=c),
                                T(f"×{b - a}", 24, c).move_to([(x0 + x1) / 2, CNT_Y, 0])))
        self.steps("Equal keys now sit side by side, so a single scan with one counter finds every count.", [
            (lambda: [glow(VGroup(*[k[0] for k in out]), GREY_A, 1.01)], 0.8),
            "a single scan",
            (lambda: [LaggedStart(*[Create(m[0]) for m in marks], lag_ratio=0.5),
                      LaggedStart(*[FadeIn(m[1], shift=0.1 * DOWN) for m in marks], lag_ratio=0.5)], 2.4),
        ])

        c1 = chip("100 GB of keys, 1 GB of memory: 100 runs", GREY_B, 20).move_to([0, -3.1, 0])
        c2 = chip("merge 16 at a time: 100 runs, then 7, then 1", GOLD_M, 20).move_to([0, -3.1, 0])
        c3 = chip("merge 128 at a time: one pass", GREEN_M, 20).move_to([0, -3.1, 0])
        self.steps("At full size, 100 gigabytes of keys and a 1 gigabyte buffer make 100 runs. The sort command merges 16 "
                   "at a time by default, so it needs two passes. At 128 at a time, it needs one.", [
            (lambda: [FadeIn(c1, shift=0.15 * UP)], 0.8),
            "The sort command",
            (lambda: [FadeTransform(c1, c2)], 0.8),
            "At 128",
            (lambda: [FadeTransform(c2, c3)], 0.8),
        ])

        self.steps("A hash map is fastest while the different keys fit in memory. "
                   "A sort never runs out of memory. It just gets slower as the input grows.", [
            (lambda: [glow(mem, TEAL_M, 1.03)], 1.0),
            "A sort never",
            (lambda: [glow(disk, GREEN_M, 1.02), glow(c3[0], GREEN_M, 1.04)], 1.0),
        ])
        self.wait(0.6)
