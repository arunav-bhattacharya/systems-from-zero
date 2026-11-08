from sfz import *

SAY.insert(0, (r"\bUN\b", "U N"))
SAY.insert(0, (r"\bnodetool\b", "node tool"))

NC = [BLUE_M, GOLD_M, GREEN_M, PURPLE_B]          # cass1..cass4 (a lighter purple reads better on black)
RC = np.array([-3.25, -0.3, 0])                    # ring centre
R = 1.85
SPAN = 20
OLD = {0: [2.8, 7.2, 12.3, 16.67], 1: [4.2, 9.5, 13.8, 18.14], 2: [5.7, 10.9, 15.2, 0.5]}
NEW = [2.17, 5.03, 8.87, 18.97]                   # cass4's tokens: each cuts the range just before it
ALL = sorted([(p, n) for n, ps in OLD.items() for p in ps] + [(p, 3) for p in NEW])
BOXP = [(-5.75, 2.25), (-0.75, 2.25), (-0.75, -2.85), (-5.75, -2.85)]
COLX = [1.0, 2.25, 3.95, 5.45]                     # status table: state, address, load, tokens
ROWY = [1.8, 1.3, 0.8, 0.3]


def ang(h):
    return np.radians(90 - 360 * h / SPAN)


def at(h, r=R):
    a = ang(h)
    return RC + r * np.array([np.cos(a), np.sin(a), 0])


def seg_owner(k, joined):
    """Owner of the segment that ends at ALL[k]: the first active token at or after it."""
    for j in range(len(ALL)):
        p, n = ALL[(k + j) % len(ALL)]
        if joined or n != 3:
            return n


def segments():
    g = VGroup()
    for k, (p, n) in enumerate(ALL):
        prev = ALL[k - 1][0]
        length = (p - prev) % SPAN
        g.add(Arc(radius=R, start_angle=ang(prev), angle=-np.radians(360 * length / SPAN), arc_center=RC,
                  stroke_width=8, stroke_color=NC[seg_owner(k, False)], stroke_opacity=0.85))
    return g


def nbox(i, col=None):
    return box(f"cass{i + 1}", col or NC[i], w=1.5, h=0.6, size=26).move_to([*BOXP[i], 0])


def scell(row, col, txt, color=WHITE):
    return M(txt, 24, color).move_to([COLX[col], ROWY[row], 0])


def srow(row, state, load, scol=WHITE):
    return VGroup(scell(row, 0, state, scol), scell(row, 1, f"cass{row + 1}", NC[row]), scell(row, 2, load), scell(row, 3, "16"))


def pulses(arrows):
    """A dot runs down each arrow at once, to show data streaming."""
    out = []
    for a in arrows:
        d = Dot(a.get_start(), radius=0.09, color=a.get_color())
        out.append(Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a.get_start(), a.get_end()), rate_func=smooth),
                              FadeOut(d, run_time=0.1)))
    return out


def flash(m, color, s=1.08):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Never re-add a group whose parts are already on screen (that would draw filled boxes over their labels)."""
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


class CassandraJoin(Base):
    """nosql-14: a fourth node joins a three-node ring (seeds, gossip, tokens, streaming, UJ to UN), cleanup, decommission."""

    def construct(self):
        self.title_card("A node joins the ring", "bootstrap, streaming and cleanup")

        segs = segments()
        dots = VGroup(*[Dot(at(p), radius=0.1, color=NC[n]).set_stroke(BLACK, 2.5) for p, n in ALL if n != 3])
        new_dots = VGroup(*[Dot(at(p), radius=0.1, color=NC[3]).set_stroke(BLACK, 2.5) for p in NEW])
        boxes = VGroup(*[nbox(i) for i in range(3)])
        b4 = nbox(3)
        title = M("$ nodetool status -r", 24, GREY_B)
        title.move_to([0.7 + title.width / 2, 2.85, 0])
        hdr = VGroup(*[M(h, 20, GREY_B).move_to([COLX[k], 2.35, 0]) for k, h in enumerate(("--", "Address", "Load", "Tokens"))])
        rule = Line([0.6, 2.1, 0], [6.1, 2.1, 0], stroke_width=1.5, color=GREY_D)
        rows = VGroup(*[srow(i, "UN", "40 GiB") for i in range(3)])
        status = VGroup(title, hdr, rule, rows)

        self.steps("Each node of your three-node cluster holds 40 gigabytes, and the disks are filling up. "
                   "You add a fourth node to take a share.", [
            (lambda: [Create(segs), FadeIn(dots), LaggedStart(*[FadeIn(b, scale=0.8) for b in boxes], lag_ratio=0.2)], 1.8),
            (lambda: [FadeIn(status, shift=0.2 * LEFT)], 1.0),
            "and the disks", (lambda: [*[Indicate(r[2], color=GOLD_M, scale_factor=1.15) for r in rows]], 1.0),
        ])

        own1 = [k for k in range(len(ALL)) if seg_owner(k, False) == 0]
        self.steps("Each node owns many small ranges of the ring, one ending at each of its tokens. "
                   "Real nodes have sixteen tokens. We draw four.", [
            (lambda: [*[segs[k].animate.set_stroke(width=16) for k in own1], flash(boxes[0], WHITE, 1.1)], 0.9),
            (lambda: [*[segs[k].animate.set_stroke(width=8) for k in own1]], 0.6),
            "Real nodes", (lambda: [*[Indicate(r[3], color=YELLOW_M, scale_factor=1.3) for r in rows]], 1.0),
        ])

        # ---- the new node's settings, and gossip ----------------------------------------------------------
        yaml = VGroup(T("cass4's cassandra.yaml", 22, GREY_B), M("cluster_name: sfz-ring", 22),
                      M('seeds: "cass1"', 22), M("num_tokens: 16", 22)).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        yaml.move_to([3.45, -1.55, 0])
        yframe = SurroundingRectangle(yaml, color=GREY_D, buff=0.25, corner_radius=0.12)
        b4_ghost = nbox(3, GREY_B)
        self.steps("The new node needs two settings: the cluster's name, which must match, "
                   "and a seed, a node it calls first.", [
            (lambda: [FadeIn(b4_ghost, scale=0.8), FadeIn(yframe), FadeIn(yaml[0])], 0.8),
            "the cluster's name", (lambda: [FadeIn(yaml[1], shift=0.15 * RIGHT)], 0.6),
            "and a seed", (lambda: [FadeIn(yaml[2], shift=0.15 * RIGHT), FadeIn(yaml[3], shift=0.15 * RIGHT)], 0.6),
            "a node it calls", (lambda: [flash(boxes[0], YELLOW_M, 1.12), Indicate(yaml[2], color=YELLOW_M, scale_factor=1.08)], 0.9),
        ])

        call = edge_arrow(b4_ghost, boxes[0], GREY_B)
        gl = VGroup(*[DashedLine(*ends(b4, boxes[i]), dash_length=0.1, stroke_width=2, color=GREY_B) for i in (1, 2)])
        self.steps("It starts and gossips its way in. Within seconds every node knows it, and it knows every node's tokens.", [
            (lambda: [GrowArrow(call)], 0.7),
            (lambda: [Transform(b4_ghost, b4)], 0.6),
            "Within seconds", (lambda: [Create(gl)], 0.8),
            (lambda: [flash(boxes[1], NC[1], 1.1), flash(boxes[2], NC[2], 1.1)], 0.7),
            "and it knows", (lambda: [Indicate(dots, color=WHITE, scale_factor=1.4)], 1.0),
        ])

        # ---- tokens, joining, streaming -------------------------------------------------------------------
        new_k = [k for k, (p, n) in enumerate(ALL) if n == 3]
        row4 = srow(3, "UJ", "0 GiB", GOLD_M)
        self.steps("Now it picks its own sixteen tokens, placed by an allocator to even out the load. "
                   "In the status table, it shows as joining.", [
            (lambda: [FadeOut(call), FadeOut(gl)], 0.4),
            (lambda: [LaggedStart(*[FadeIn(d, scale=2.5) for d in new_dots], lag_ratio=0.25)], 1.2),
            (lambda: [*[segs[k].animate.set_stroke(color=NC[3], opacity=0.5) for k in new_k]], 0.8),
            "In the status", (lambda: [FadeIn(row4, shift=0.2 * UP)], 0.7),
            (lambda: [Indicate(row4[0], color=GOLD_M, scale_factor=1.3)], 0.8),
        ])

        src = sorted({seg_owner(k, False) for k in new_k})
        streams = VGroup(*[Arrow(*ends(boxes[i], b4_ghost), buff=0.12, stroke_width=3.5, color=NC[i],
                                 max_tip_length_to_length_ratio=0.06) for i in src])

        def load4(v):
            return lambda: [Transform(row4[2], scell(3, 2, f"{v} GiB")), *pulses(streams)]

        note = VGroup(T("streaming its new ranges", 26, NC[3]), T("writes: yes   reads: not yet", 24, GREY_B)).arrange(DOWN, buff=0.25)
        note.move_to([3.45, -1.55, 0])
        self.steps("Its new ranges still sit on the old nodes, so they stream that data to it, about 30 gigabytes. "
                   "Meanwhile it takes new writes for those ranges, but serves no reads.", [
            (lambda: [FadeOut(yaml), FadeOut(yframe)], 0.5),
            (lambda: [*[GrowArrow(a) for a in streams], FadeIn(note[0], shift=0.15 * UP)], 0.8),
            (load4(8), 1.1), (load4(16), 1.1), "Meanwhile", (lambda: [FadeIn(note[1], shift=0.15 * UP)], 0.5),
            (load4(24), 1.1), (load4(30), 1.1),
        ])

        self.steps("When streaming ends, it turns UN: up and normal. Now those ranges are its own, and it answers reads.", [
            (lambda: [FadeOut(streams), FadeOut(note)], 0.5),
            (lambda: [Transform(row4[0], scell(3, 0, "UN", GREEN_M))], 0.6),
            "Now those", (lambda: [*[segs[k].animate.set_stroke(opacity=0.85) for k in new_k]], 0.8),
            (lambda: [*[Indicate(segs[k], color=NC[3], scale_factor=1.12) for k in new_k], flash(b4_ghost, NC[3], 1.1)], 1.0),
            (lambda: [row4[0].animate.set_color(WHITE)], 0.3),
        ])

        # ---- cleanup --------------------------------------------------------------------------------------
        hl = SurroundingRectangle(VGroup(*[r[2] for r in rows]), color=RED_M, buff=0.12, corner_radius=0.08)
        self.steps("But look at the load column. The old nodes still hold 40 gigabytes each. "
                   "Streaming copied the data. Nothing deleted the old copies.", [
            (lambda: [Create(hl)], 0.8),
            (lambda: [*[r[2].animate.set_color(RED_M) for r in rows]], 0.6),
        ])

        cmd = chip("$ nodetool cleanup", TEAL_M, 24, mono=True).move_to([3.45, -1.55, 0])

        def clean(i):
            return [(lambda: [flash(boxes[i], TEAL_M, 1.12)], 0.6),
                    (lambda: [Transform(rows[i][2], scell(i, 2, "30 GiB", TEAL_M))], 0.6)]

        self.steps("No read will ever ask them for those rows again. So you run nodetool cleanup on each old node, "
                   "one at a time, and each drops to 30.", [
            "So you run", (lambda: [FadeOut(hl), FadeIn(cmd, shift=0.2 * UP)], 0.6),
            *clean(0), *clean(1), *clean(2),
            (lambda: [*[r[2].animate.set_color(WHITE) for r in rows]], 0.4),
        ])

        # ---- decommission -----------------------------------------------------------------------------------
        cmd2 = chip("$ nodetool decommission", GOLD_M, 24, mono=True).move_to([3.45, -1.55, 0])
        self.steps("Removing a node is the same story backwards. You run decommission on the new node, and it shows as leaving.", [
            "You run", (lambda: [Transform(cmd, cmd2)], 0.7),
            (lambda: [flash(b4_ghost, GOLD_M, 1.12)], 0.6),
            "and it shows", (lambda: [Transform(row4[0], scell(3, 0, "UL", GOLD_M))], 0.6),
            (lambda: [Indicate(row4[0], color=GOLD_M, scale_factor=1.3)], 0.8),
        ])

        back = VGroup(*[Arrow(*ends(b4_ghost, boxes[i]), buff=0.12, stroke_width=3.5, color=NC[3],
                              max_tip_length_to_length_ratio=0.06) for i in src])
        gone = [k for k in new_k]
        self.steps("It streams each of its ranges to the node that owns it next, then leaves the ring. "
                   "The others are back to 40 gigabytes each, and there's nothing to clean up.", [
            (lambda: [*[GrowArrow(a) for a in back]], 0.7),
            (lambda: pulses(back), 1.2),
            (lambda: [*[segs[k].animate.set_stroke(color=NC[seg_owner(k, False)]) for k in gone]], 0.8),
            "then leaves", (lambda: [FadeOut(back), FadeOut(new_dots), FadeOut(b4_ghost), FadeOut(row4), FadeOut(cmd)], 0.8),
            "The others", (lambda: [*[Transform(rows[i][2], scell(i, 2, "40 GiB", GREEN_M)) for i in range(3)]], 0.7),
            (lambda: [*[r[2].animate.set_color(WHITE) for r in rows]], 0.4),
        ])

        self.steps("So a joining node gossips in, takes its tokens and streams its ranges. The old owners clean up what they "
                   "no longer need. And you change one node at a time.", [
            (lambda: [Indicate(segs, color=WHITE, scale_factor=1.04)], 1.2),
            "And you change", (lambda: [LaggedStart(*[flash(b, YELLOW_M, 1.1) for b in boxes], lag_ratio=0.3)], 1.6),
        ])
        self.wait(0.6)
