from sfz import *

SAY.insert(0, (r"\buniq\b", "unique"))
SAY.insert(0, (r"\bGNU\b", "G new"))
SAY.insert(0, (r"\bneighbours\b", "neighbors"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
KEYS = [201, 200, 201, 402, 500, 201, 200, 404, 201, 402, 200, 201]
CX0, CP = -4.4, 0.82
IN_Y, MEM_Y = 2.75, 1.6
RUN_Y = {1: 0.65, 2: -0.05, 3: -0.75, 4: -1.45}
OUT_Y = -2.2
LAB_X = -6.5
MERGE = np.array([3.6, 0.0, 0])
CNT_P = np.array([3.6, 1.6, 0])
CAP_Y, BAR_Y = -3.22, -2.72


def cx(k):
    return CX0 + CP * k


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

    # --- small state helpers: each returns animations and records what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        return [FadeOut(self.lab.pop(k)) for k in keys if k in self.lab]

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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def dot_run(a, b, color=YELLOW_M, rt=0.6):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.08, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))



def key(v, color=BLUE_M):
    r = RoundedRectangle(corner_radius=0.07, width=0.72, height=0.48, stroke_color=color, stroke_width=2).set_fill(fillc(color, 0.25), 1)
    g = VGroup(r, M(str(v), 18).move_to(r)).set_z_index(3)
    g.v = v
    return g


def ballot():
    r = RoundedRectangle(corner_radius=0.05, width=0.62, height=0.42, stroke_color=GOLD_M, stroke_width=2).set_fill("#2a2418", 1)
    lines = VGroup(*[Line([-0.2, y, 0], [0.2, y, 0], stroke_width=1.5, color=GREY_B) for y in (0.07, -0.07)]).move_to(r)
    return VGroup(r, lines).set_z_index(3)


def rlabel(s, y, color=GREY_B):
    return left_at(T(s, 19, color), LAB_X, y)


class ExternalSort(Base):
    """batch-02, section 3. The tally ran out of memory; doesn't sorting need every key in memory too? The ballot pile
    too big for the table: sort an armful, set the stack aside, merge by the top ballot of each. Twelve status codes, a
    memory for 4: runs 1 to 3. Predict the passes at fan-in 2: two. Merge pass 1 with a priority queue (run 4, 8 keys),
    pass 2 to the output; uniq -c counts 3, 5, 2, 1, 1; never more than 4 in memory. At scale: 100 GB, 1 GB, 100 runs;
    fan-in 16: 100, 7, 1; 128: one pass; every pass reads and writes everything; GNU sort -S 4M: 73 runs, under 7 MB.
    The moral, and a check (5 runs at fan-in 2: 3 passes)."""

    def counter(self, s, color=GREY_B):
        return self.put("cnt", fit(T(s, 20, color), 3.6).move_to(CNT_P))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("An armful at a time", "sorting more than fits in memory")

        mem = RoundedRectangle(corner_radius=0.12, width=CP * 4 + 0.2, height=0.72, stroke_color=GOLD_M, stroke_width=3)
        mem.set_fill(fillc(GOLD_M, 0.1), 1).move_to([(cx(0) + cx(3)) / 2, MEM_Y, 0])

        # ---------------- scene 1: the tally ran out ----------------
        flood = [key(v, RED_M) for v in (201, 200, 404, 500, 402, 301, 302, 503, 204, 418)]
        for k, m in enumerate(flood):
            m.move_to([cx(k) + (0.35 if k >= 4 else 0), MEM_Y, 0])
        self.steps("In the last section, the tally ran out of memory: a hash map keeps one line per different key, "
                   "and there were too many keys.", [
            (lambda: [FadeIn(mem), *self.put("ml", rlabel("memory", MEM_Y, GOLD_M))], 0.6),
            "one line per different key",
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.2 * DOWN) for m in flood], lag_ratio=0.15)], 1.6),
            "too many keys",
            (lambda: [mem.animate.set_stroke(RED_M), *self.cap("out of memory", RED_M)], 0.5),
        ])
        self.steps("Sorting looks like it has the same problem. To put keys in order, surely you need them all in memory at once?", [
            (lambda: [*[FadeOut(m) for m in flood], mem.animate.set_stroke(GOLD_M)], 0.6),
            "surely you need",
            (lambda: self.cap("sorting needs every key in memory?", PURPLE_M), 0.6),
        ])
        self.steps("A sort done in memory does, and it would fail exactly like the hash map. Hold that thought.", [
            "Hold that thought",
            (lambda: self.cap("a sort done in memory fails the same way. Hold that thought.", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 2: too big for the table ----------------
        bal = [ballot().move_to([cx(k), IN_Y, 0]) for k in range(12)]
        self.steps("Back at the ballot table, picture a pile too big for the table.", [
            (lambda: [*self.uncap(), *self.put("il", rlabel("the pile", IN_Y, GOLD_M)), *self.put("ml", rlabel("the table", MEM_Y, GOLD_M)),
                      LaggedStart(*[FadeIn(b, shift=0.1 * DOWN) for b in bal], lag_ratio=0.05)], 1.0),
        ])

        def armful(a, row, rt=0.5):
            return [*[bal[a * 4 + j].animate.move_to([cx(j), MEM_Y, 0]) for j in range(4)]]

        def to_stack(a, row):
            return [*[bal[a * 4 + j].animate.move_to([cx(j), RUN_Y[row], 0]) for j in range(4)]]

        self.steps("Take an armful, sort it by name, and set the sorted stack aside.", [
            "Take an armful",
            (lambda: armful(0, 1), 0.6),
            "sort it",
            (lambda: [bal[0].animate.move_to([cx(2), MEM_Y, 0]), bal[2].animate.move_to([cx(0), MEM_Y, 0])], 0.5),
            "set the sorted stack",
            (lambda: [*to_stack(0, 1), *self.put("r1", rlabel("stack 1", RUN_Y[1], GOLD_M))], 0.6),
        ])
        self.steps("Take the next armful, and the next, until the pile is gone.", [
            (lambda: armful(1, 2), 0.5),
            (lambda: [*to_stack(1, 2), *self.put("r2", rlabel("stack 2", RUN_Y[2], GOLD_M))], 0.5),
            "and the next",
            (lambda: armful(2, 3), 0.5),
            (lambda: [*to_stack(2, 3), *self.put("r3", rlabel("stack 3", RUN_Y[3], GOLD_M))], 0.5),
        ])
        tops = [bal[0], bal[4], bal[8]]
        self.steps("Then merge the stacks: look at the top ballot of each, take the one that comes first in the alphabet, and repeat.", [
            "look at the top",
            (lambda: [glow(b[0], YELLOW_M, 1.2) for b in tops], 0.8),
            "take the one",
            (lambda: [bal[4].animate.move_to([cx(0), OUT_Y, 0])], 0.6),
            "and repeat",
            (lambda: [bal[0].animate.move_to([cx(1), OUT_Y, 0])], 0.5),
        ])
        self.steps("Equal names come out side by side, and you count them as they pass.", [
            (lambda: [glow(bal[4][0], YELLOW_M, 1.2), glow(bal[0][0], YELLOW_M, 1.2)], 0.8),
        ])
        self.steps("Map it out. The table is the memory. An armful is what fits in it. "
                   "Each sorted stack is a file on disk. And the merge only ever looks at the top of each stack.", [
            (lambda: [*self.cap("table = memory"), glow(mem, GOLD_M, 1.03)], 0.5),
            "An armful",
            (lambda: self.cap("armful = what fits in memory"), 0.5),
            "Each sorted stack",
            (lambda: self.cap("sorted stack = a file on disk"), 0.5),
            "the merge only",
            (lambda: [*self.cap("the merge looks only at the top of each stack"),
                      *[glow(b[0], YELLOW_M, 1.2) for b in (bal[1], bal[5], bal[8])]], 0.7),
        ], after=0.3)

        # ---------------- scene 3: making runs ----------------
        keys = [key(v) for v in KEYS]
        for k, m in enumerate(keys):
            m.move_to([cx(k), IN_Y, 0])
        self.steps("Let's shrink it. A web server's log records a status code for every request, a number like 200 for OK "
                   "or 404 for not found. Here are twelve of them, and a memory that holds only 4.", [
            (lambda: [*self.uncap(), *[FadeOut(b) for b in bal], *self.drop("r1", "r2", "r3"),
                      *self.put("il", rlabel("input", IN_Y, BLUE_M)), *self.put("ml", rlabel("memory", MEM_Y, GOLD_M))], 0.6),
            "Here are twelve",
            (lambda: [LaggedStart(*[FadeIn(m, shift=0.1 * DOWN) for m in keys], lag_ratio=0.06)], 1.0),
            "holds only 4",
            (lambda: [glow(mem, GOLD_M, 1.03), *self.put("room", left_at(T("room for 4", 18, GOLD_M), mem.get_right()[0] + 0.2, MEM_Y))], 0.6),
        ])
        self.runs = {}

        def load(a):
            return [keys[a * 4 + j].animate.move_to([cx(j), MEM_Y, 0]) for j in range(4)]

        def sort_mem(a):
            batch = keys[a * 4:a * 4 + 4]
            order = sorted(range(4), key=lambda j: (batch[j].v, j))
            self.runs[a + 1] = [batch[j] for j in order]
            return [batch[j].animate.move_to([cx(p), MEM_Y, 0]) for p, j in enumerate(order)]

        def write(a):
            row = a + 1
            return [*[m.animate.move_to([cx(p), RUN_Y[row], 0]) for p, m in enumerate(self.runs[row])],
                    *self.put(f"r{row}", rlabel(f"run {row}", RUN_Y[row], BLUE_M))]

        self.steps("Read the first 4, sort them in memory, and write them to a temporary file.", [
            "Read the first 4",
            (lambda: load(0), 0.6),
            "sort them",
            (lambda: sort_mem(0), 0.6),
            "write them",
            (lambda: [*write(0), *self.counter("runs on disk: 1")], 0.6),
        ])
        self.steps("A sorted file like this is called a run.", [
            (lambda: [*self.cap("run: a sorted file on disk", WHITE), *[glow(m[0], BLUE_M, 1.15) for m in self.runs[1]]], 0.7),
        ])
        self.steps("Two more batches give runs 2 and 3.", [
            (lambda: load(1), 0.4),
            (lambda: sort_mem(1), 0.4),
            (lambda: [*write(1), *self.counter("runs on disk: 2")], 0.4),
            "and 3",
            (lambda: load(2), 0.4),
            (lambda: sort_mem(2), 0.4),
            (lambda: [*write(2), *self.counter("runs on disk: 3")], 0.4),
        ])
        self.steps("The input has been read once, and every key sits in a sorted run. The memory never held more than 4.", [
            (lambda: self.cap("input read once; every key in a sorted run"), 0.6),
            "never held more",
            (lambda: [glow(mem, GOLD_M, 1.03)], 0.6),
        ])
        self.steps("It's a very short table, and it never complained.", [], after=0.4)

        # ---------------- scene 4: how many passes? ----------------
        mbox = RoundedRectangle(corner_radius=0.14, width=3.6, height=1.5, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M, 0.1), 1).move_to(MERGE)
        mtitle = T("merge: reads 2 runs at once", 19, TEAL_M).move_to(MERGE + [0, 0.48, 0])
        self.steps("Now the merge. Our merge reads only 2 runs at once. We have 3 runs. "
                   "How many rounds of merging until one sorted file is left? Pause and guess.", [
            (lambda: [*self.uncap(), FadeIn(mbox), FadeIn(mtitle)], 0.6),
            "We have 3 runs",
            (lambda: [*[Indicate(self.lab[f"r{r}"], color=BLUE_M) for r in (1, 2, 3)]], 0.6),
            "Pause and guess",
            (lambda: self.cap("3 runs, 2 at a time: how many rounds?  pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 5: merging ----------------
        def heads(a, b):
            return self.put("heads", M(f"{a}   {b}", 24, YELLOW_M).move_to(MERGE + [0, -0.2, 0]))

        r1, r2 = list(self.runs[1]), list(self.runs[2])
        merged = []
        while r1 or r2:
            if r2 and (not r1 or r2[0].v < r1[0].v):
                merged.append((r2.pop(0), list(r1), list(r2)))
            else:
                merged.append((r1.pop(0), list(r1), list(r2)))
        out4 = []

        def take(n):
            m, a, b = merged[n]
            out4.append(m)
            ha = a[0].v if a else "-"
            hb = b[0].v if b else "-"
            return [m.animate.move_to([cx(n), RUN_Y[4], 0]), *heads(ha, hb)]

        self.steps("Two. Pass 1 opens runs 1 and 2. It keeps the first key of each in a small priority queue, "
                   "a structure that always hands back its smallest item first.", [
            (lambda: [*self.cap("two rounds: 3 runs, then 2, then 1", WHITE)], 0.6),
            "Pass 1 opens",
            (lambda: [*self.counter("merge pass 1"), *self.put("r4", rlabel("run 4", RUN_Y[4], TEAL_M)),
                      glow(self.runs[1][0][0], YELLOW_M, 1.2), glow(self.runs[2][0][0], YELLOW_M, 1.2)], 0.7),
            "first key of each",
            (lambda: heads(self.runs[1][0].v, self.runs[2][0].v), 0.5),
            "priority queue",
            (lambda: self.cap("priority queue: always hands back its smallest item first", WHITE), 0.6),
        ])
        self.steps("Write the smaller one, refill from the run it came from, and repeat. 200, 200, 201, and on.", [
            "Write the smaller",
            (lambda: take(0), 0.6),
            "200, 200",
            (lambda: take(1), 0.5),
            (lambda: take(2), 0.5),
            "and on",
            (lambda: take(3), 0.35),
            (lambda: take(4), 0.35),
        ])
        self.steps("Memory holds one key per open run, however long the runs are.", [
            (lambda: [*self.cap("memory: one key per open run"), Indicate(self.lab["heads"], color=YELLOW_M)], 0.6),
            (lambda: take(5), 0.35),
            (lambda: take(6), 0.35),
            (lambda: take(7), 0.35),
        ])
        self.steps("Runs 1 and 2 become run 4, with 8 keys. Run 3 had no partner, so it waits. 3 runs became 2.", [
            "become run 4",
            (lambda: [*self.drop("r1", "r2", "heads"), *[glow(m[0], TEAL_M, 1.15) for m in out4]], 0.7),
            "Run 3 had",
            (lambda: [Indicate(self.lab["r3"], color=BLUE_M)], 0.5),
            "3 runs became 2",
            (lambda: self.counter("after pass 1: 2 runs"), 0.5),
        ])
        r4, r3 = list(out4), list(self.runs[3])
        order2 = []
        while r4 or r3:
            if r3 and (not r4 or r3[0].v < r4[0].v):
                order2.append(r3.pop(0))
            else:
                order2.append(r4.pop(0))
        self.steps("Pass 2 merges run 4 with run 3, and writes the final sorted file.", [
            (lambda: [*self.counter("merge pass 2"), *self.put("ol", rlabel("output", OUT_Y, GREEN_M))], 0.5),
            "writes the final",
            (lambda: [Succession(*[m.animate(run_time=0.17).move_to([cx(n), OUT_Y, 0]) for n, m in enumerate(order2)])], 2.0),
            (lambda: [*self.drop("r3", "r4"), *self.counter("after pass 2: 1 run, the sorted output", GREEN_M)], 0.5),
        ])
        self.steps("Each pass read and wrote every key once, from the start of each file to its end, the way disks read fastest.", [
            (lambda: [*self.cap("each pass reads and writes every key once, start to end"),
                      LaggedStart(*[glow(m[0], GREEN_M, 1.15) for m in order2], lag_ratio=0.06)], 1.2),
        ], after=0.3)
        self.stamp("sorted")

        # ---------------- scene 6: counting, and the name ----------------
        groups = [(0, 2, 3), (3, 7, 5), (8, 9, 2), (10, 10, 1), (11, 11, 1)]
        braces = VGroup()
        for a, b, n in groups:
            g = VGroup(*order2[a:b + 1])
            br = Brace(g, UP, buff=0.08, color=YELLOW_M)
            braces.add(VGroup(br, M(str(n), 20, YELLOW_M).next_to(br, UP, buff=0.06)))
        self.steps("Equal keys are now neighbours, so uniq, a small program that collapses repeated lines, counts them "
                   "with a single counter: 200 comes three times, 201 five times, 402 twice, 404 and 500 once each.", [
            (lambda: [*self.cap("uniq -c: one counter, equal keys side by side", WHITE)], 0.6),
            "200 comes three times",
            (lambda: [FadeIn(braces[0])], 0.4),
            "201 five times",
            (lambda: [FadeIn(braces[1])], 0.4),
            "402 twice",
            (lambda: [FadeIn(braces[2])], 0.4),
            "404 and 500",
            (lambda: [FadeIn(braces[3]), FadeIn(braces[4])], 0.4),
        ])
        self.steps("At no step did the sort hold more than 4 keys.", [
            (lambda: [*self.cap("never more than 4 keys in memory", YELLOW_M), glow(mem, GOLD_M, 1.03)], 0.6),
        ])
        self.steps("This is called an external merge sort: external because the runs live outside memory, on disk.", [
            "external merge sort",
            (lambda: self.cap("external merge sort: the runs live outside memory, on disk", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 7: at scale ----------------
        scene_objs = VGroup(*keys, braces, mem, mbox, mtitle)

        def stage(x, y, s, color):
            return VGroup(RoundedRectangle(corner_radius=0.12, width=1.9, height=0.7, stroke_color=color, stroke_width=2.5)
                          .set_fill(fillc(color, 0.15), 1), T(s, 20, color)).move_to([x, y, 0])

        f16 = VGroup(left_at(T("fan-in 16", 22, TEAL_M), -6.2, 0.9), stage(-3.1, 0.9, "100 runs", BLUE_M), stage(0.0, 0.9, "7 runs", BLUE_M),
                     stage(3.1, 0.9, "1 run", GREEN_M), left_at(T("2 passes", 22, WHITE), 4.4, 0.9))
        f16.add(edge_arrow(f16[1], f16[2]), edge_arrow(f16[2], f16[3]))
        f128 = VGroup(left_at(T("fan-in 128", 22, TEAL_M), -6.2, -0.6), stage(-3.1, -0.6, "100 runs", BLUE_M),
                      stage(3.1, -0.6, "1 run", GREEN_M), left_at(T("1 pass", 22, WHITE), 4.4, -0.6))
        f128.add(edge_arrow(f128[1], f128[2]))
        head = T("100 GB of keys, a 1 GB buffer: 100 runs", 24, WHITE).move_to([0, 2.3, 0])
        self.steps("Now the real numbers. 100 GB of keys and a 1 GB buffer give 100 runs.", [
            (lambda: [*self.uncap(), FadeOut(scene_objs), *self.drop("il", "ml", "room", "ol", "cnt")], 0.7),
            "100 GB",
            (lambda: [FadeIn(head)], 0.6),
        ])
        self.steps("The number of runs one merge reads at once is the fan-in. With a fan-in of 16, the first pass leaves 7 runs "
                   "and the second leaves 1: two passes. With 128, one.", [
            "is the fan-in",
            (lambda: self.cap("fan-in: how many runs one merge reads at once", WHITE), 0.6),
            "With a fan-in of 16",
            (lambda: [FadeIn(f16[0]), FadeIn(f16[1])], 0.5),
            "leaves 7",
            (lambda: [GrowArrow(f16[5]), FadeIn(f16[2])], 0.5),
            "leaves 1",
            (lambda: [GrowArrow(f16[6]), FadeIn(f16[3]), FadeIn(f16[4])], 0.5),
            "With 128",
            (lambda: [FadeIn(f128[0]), FadeIn(f128[1]), GrowArrow(f128[4]), FadeIn(f128[2]), FadeIn(f128[3])], 0.6),
        ])
        self.steps("Every pass reads and writes all 100 GB. So a sort costs more processor work and extra trips over the disk, "
                   "and in exchange it never runs out of memory. It only gets slower as the input grows.", [
            (lambda: self.cap("every pass reads and writes all 100 GB", RED_M), 0.6),
            "in exchange",
            (lambda: self.cap("it never runs out of memory; it only gets slower", YELLOW_M), 0.6),
        ])
        tryit = VGroup(M("sort -S 4M paths.txt", 22, WHITE), T("46 MB of keys: 73 runs, never more than about 7 MB of memory", 21, GREY_A)
                       ).arrange(DOWN, buff=0.25).move_to([0, -1.85, 0])
        self.steps("GNU sort, the sort program on Linux, does all this on its own: with a 4 MB buffer, 46 MB of keys made 73 runs, "
                   "and it never held more than about 7 MB.", [
            (lambda: [*self.uncap(), FadeIn(tryit[0])], 0.6),
            "46 MB",
            (lambda: [FadeIn(tryit[1])], 0.6),
        ], after=0.4)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So the moral of the story: when the keys don't fit, sort an armful at a time, and merge by looking only at the top of each run.", [
            (lambda: [FadeOut(f16), FadeOut(f128), FadeOut(head), FadeOut(tryit), FadeIn(scene_objs)], 0.8),
            "sort an armful",
            (lambda: self.cap("sort an armful at a time; merge by the top of each run", YELLOW_M, 26), 0.6),
        ])
        self.steps("The tally falls off a cliff. The sort just walks a little slower.", [
            (lambda: [glow(mem, GOLD_M, 1.03)], 0.6),
        ], after=0.4)
        five = VGroup(*[stage(0, 0, "run", BLUE_M).scale(0.8) for _ in range(5)]).arrange(RIGHT, buff=0.2).move_to([0, 1.0, 0])
        self.steps("One quick check. With a fan-in of 2, how many merge passes do 5 runs need? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(scene_objs), FadeIn(five)], 0.7),
            "Pause and think",
            (lambda: self.cap("fan-in 2, 5 runs: how many passes?  pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ans = T("5 runs, then 3, then 2, then 1: 3 passes", 30, GREEN_M).move_to([0, -0.3, 0])
        self.steps("Three. 5 runs become 3, then 2, then 1.", [
            (lambda: [*self.uncap(), FadeIn(ans)], 0.7),
        ], after=0.4)
        self.play(*self.cap("each pass turns r runs into r divided by the fan-in, rounded up", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
