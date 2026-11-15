from sfz import *

SAY.insert(0, (r"\bXAUTOCLAIM\b", "X auto claim"))
SAY.insert(0, (r"\bXADD\b", "X add"))
SAY.insert(0, (r"\bXACK\b", "X ack"))
SAY.insert(0, (r"\bw([1-3])\b", r"W \1"))

SY, SX0, SP = 2.55, -5.3, 1.7               # the stream: row, x of the first entry, pitch
GX, GYY = 4.75, 2.55                        # the group box
WY, WX = 0.7, {1: -5.2, 2: -3.05, 3: -0.9}  # workers
HY = [-0.3, -0.85, -1.4]                    # entries a worker holds
TX = {"id": 2.0, "owner": 3.25, "idle": 4.45, "n": 5.8}
TY = [0.3, -0.2, -0.7, -1.2, -1.7]          # PEL rows
CMDY = -3.0
IDS = ["1-1", "1-2", "1-3", "1-4", "1-5"]


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def entry(k):
    x = SX0 + SP * k
    r = RoundedRectangle(corner_radius=0.08, width=1.5, height=0.85, stroke_color=GREY_B, stroke_width=2.5)
    r.set_fill(fillc(GREY_B, 0.18), 1).move_to([x, SY, 0])
    return VGroup(r, M(IDS[k], 18).move_to([x, SY + 0.17, 0]), T(f"p-98{k + 1}", 16, GREY_B).move_to([x, SY - 0.2, 0]))


def held(k, w, i, color=GOLD_M):
    x, y = WX[w], HY[i]
    r = RoundedRectangle(corner_radius=0.07, width=1.1, height=0.42, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.2), 1).move_to([x, y, 0])
    return VGroup(r, M(IDS[k], 17).move_to([x, y, 0])).set_z_index(3)


def worker(w):
    r = RoundedRectangle(corner_radius=0.12, width=1.9, height=0.8, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([WX[w], WY, 0])
    return VGroup(r, T(f"w{w}", 22).move_to([WX[w], WY, 0]))


def group_line(s):
    return M(f"last delivered: {s}", 16, GOLD_M).move_to([GX, GYY - 0.2, 0])


def pel(i, k, owner, idle, n, color=WHITE):
    y = TY[i]
    return VGroup(M(IDS[k], 18, color).move_to([TX["id"], y, 0]), M(owner, 18, color).move_to([TX["owner"], y, 0]),
                  M(idle, 18, color).move_to([TX["idle"], y, 0]), M(str(n), 18, color).move_to([TX["n"], y, 0]))


def cmd(s):
    return M(s, 17, GREY_B).move_to([0, CMDY, 0])


class RedisStreams(Base):
    """msg-12, sections 1 to 3: a stream is a log in one key, in memory; XADD gives each entry an ID (clock and counter).
    The group settlers hands w1 entries 1-1 to 1-3 with '>' and records each in the PEL (owner, idle, deliveries);
    w2 settles 1-4 and 1-5 and XACKs them. w1 is OOM-killed, its entries stay pending and their idle time grows; '>'
    will not return them. XAUTOCLAIM payments settlers w3 30000 0-0 moves them to w3 (idle 0, deliveries 2), and w3
    settles and acknowledges them, so every payment is settled at least once."""

    def construct(self):
        self.title_card("Redis Streams", "a consumer group, its pending list, and a worker that dies")

        stl = T("stream payments: one key, in memory", 20, GREY_B).move_to([-6.05, 3.35, 0], aligned_edge=LEFT)
        ents = [entry(k) for k in range(5)]
        wl = T("settlement workers", 18, GREY_B).move_to([-6.15, WY + 0.72, 0], aligned_edge=LEFT)
        ws = {w: worker(w) for w in (1, 2, 3)}
        c0 = cmd("XADD payments * payment p-981 amount 1250")
        self.steps("Three workers settle payments from one Redis stream. "
                   "If a worker dies holding three payments, how does anyone find out?", [
            (lambda: [FadeIn(wl), *[FadeIn(ws[w], shift=0.1 * UP) for w in ws]], 0.9),
            "from one Redis stream",
            (lambda: [FadeIn(stl)], 0.6),
            "If a worker dies",
            (lambda: [glow(ws[1][0], RED_M, 1.06)], 0.9),
        ])

        note = T("IDs shortened here", 16, GREY_C).move_to([2.25, 3.35, 0], aligned_edge=RIGHT)
        self.steps("A stream is a log in one key, kept in memory. XADD appends an entry, "
                   "and Redis gives it an ID made of its clock in milliseconds and a counter.", [
            "XADD appends",
            (lambda: [FadeIn(c0)], 0.5),
            (lambda: [LaggedStart(*[FadeIn(e, shift=0.15 * LEFT) for e in ents], lag_ratio=0.3)], 1.6),
            "and Redis gives it",
            (lambda: [*[Indicate(e[1], color=GOLD_M) for e in ents[:2]]], 0.8),
            (lambda: [FadeIn(note)], 0.5),
        ])

        gbox = RoundedRectangle(corner_radius=0.12, width=3.2, height=0.95, stroke_color=GOLD_M, stroke_width=2.5)
        gbox.set_fill(fillc(GOLD_M, 0.1), 1).move_to([GX, GYY, 0])
        gtit = T("group: settlers", 19, GOLD_M).move_to([GX, GYY + 0.2, 0])
        gl = group_line("0-0")
        c1 = cmd("XREADGROUP GROUP settlers w1 COUNT 3 STREAMS payments >")
        h1 = [held(k, 1, k) for k in range(3)]
        self.steps("A consumer group splits the stream among workers. "
                   "w1 asks for entries never delivered to anyone in the group, and Redis hands it the first three.", [
            (lambda: [FadeIn(gbox), FadeIn(gtit), FadeIn(gl)], 0.8),
            "w1 asks",
            (lambda: [Transform(c0, c1), glow(ws[1][0], GOLD_M, 1.06)], 0.8),
            "and Redis hands",
            (lambda: [LaggedStart(*[TransformFromCopy(ents[k], h1[k]) for k in range(3)], lag_ratio=0.25),
                      Transform(gl, group_line("1-3"))], 1.3),
        ])

        ptit = T("pending entries list", 19, BLUE_M).move_to([4.05, 1.65, 0])
        hdr = VGroup(*[T(s, 17, GREY_B).move_to([TX[c], 0.8, 0]) for s, c in (("ID", "id"), ("owner", "owner"), ("idle", "idle"),
                                                                               ("deliveries", "n"))])
        frame = RoundedRectangle(corner_radius=0.12, width=5.3, height=3.45, stroke_color=BLUE_M, stroke_width=2).move_to([4.05, -0.33, 0])
        rows = {k: pel(k, k, "w1", "0 s", 1) for k in range(3)}
        self.steps("Redis writes each delivery into the group's pending entries list: the entry, its owner, "
                   "how long it's been idle, and how many times it was delivered.", [
            (lambda: [FadeIn(frame), FadeIn(ptit), FadeIn(hdr)], 0.8),
            "the entry",
            (lambda: [LaggedStart(*[FadeIn(rows[k], shift=0.1 * LEFT) for k in range(3)], lag_ratio=0.25)], 1.0),
            "its owner",
            (lambda: [*[Indicate(rows[k][1], color=GOLD_M) for k in range(3)]], 0.6),
            "how long",
            (lambda: [*[Indicate(rows[k][2], color=GOLD_M) for k in range(3)]], 0.6),
            "how many times",
            (lambda: [*[Indicate(rows[k][3], color=GOLD_M) for k in range(3)]], 0.6),
        ])

        h2 = [held(k, 2, k - 3) for k in (3, 4)]
        rows.update({k: pel(k, k, "w2", "0 s", 1) for k in (3, 4)})
        c2 = cmd("XACK payments settlers 1-4 1-5")
        self.steps("w2 gets the other two, settles them, and acknowledges them with XACK, which removes them from the list.", [
            (lambda: [Transform(c0, cmd("XREADGROUP GROUP settlers w2 COUNT 10 STREAMS payments >"))], 0.5),
            (lambda: [*[TransformFromCopy(ents[k], h2[k - 3]) for k in (3, 4)], Transform(gl, group_line("1-5")),
                      *[FadeIn(rows[k], shift=0.1 * LEFT) for k in (3, 4)]], 1.0),
            "settles them",
            (lambda: [*[h[0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M, 0.2), 1) for h in h2]], 0.6),
            "and acknowledges",
            (lambda: [Transform(c0, c2)], 0.5),
            "which removes",
            (lambda: [FadeOut(rows[3], shift=0.2 * RIGHT), FadeOut(rows[4], shift=0.2 * RIGHT), FadeOut(VGroup(*h2))], 0.8),
        ])

        dead = T("w1 killed", 20, RED_M).move_to([WX[1], WY, 0])

        def idle(s):
            return [Transform(rows[k][2], M(s, 18, RED_M if s.startswith("3") else WHITE).move_to([TX["idle"], TY[k], 0]))
                    for k in range(3)]

        self.steps("w1 is killed before it acknowledges anything. "
                   "Its three entries stay pending under its name, and their idle time keeps growing.", [
            (lambda: [ws[1][0].animate.set_stroke(RED_M), Transform(ws[1][1], dead), FadeOut(c0)], 0.8),
            (lambda: [*[h[0].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B, 0.2), 1) for h in h1]], 0.5),
            "Its three entries",
            (lambda: [*[Indicate(rows[k][1], color=RED_M) for k in range(3)]], 0.8),
            "and their idle",
            (lambda: idle("10 s"), 0.6),
            (lambda: idle("20 s"), 0.6),
            (lambda: idle("31 s"), 0.6),
        ])

        c3 = cmd("XREADGROUP GROUP settlers w3 COUNT 10 STREAMS payments >")
        none = T("nothing new", 18, GREY_B).move_to([WX[3], HY[0], 0])
        self.steps("Asking for new entries won't return them, because they were already delivered. "
                   "They aren't lost, only stuck.", [
            (lambda: [FadeIn(c3)], 0.5),
            (lambda: [glow(gbox, GOLD_M, 1.04), FadeIn(none)], 0.8),
            "They aren't lost",
            (lambda: [*[glow(h[0], GREY_B, 1.1) for h in h1]], 0.8),
        ])

        c4 = cmd("XAUTOCLAIM payments settlers w3 30000 0-0 COUNT 100")
        h3 = [held(k, 3, k) for k in range(3)]
        new = {k: pel(k, k, "w3", "0 s", 2, GOLD_M) for k in range(3)}
        self.steps("So w3 runs XAUTOCLAIM with a threshold of 30 seconds. Every entry idle longer than that moves to w3. "
                   "Its idle time resets, and its delivery count goes to 2.", [
            (lambda: [FadeOut(none), Transform(c3, c4)], 0.6),
            "Every entry",
            (lambda: [*[Transform(h1[k], h3[k]) for k in range(3)], *[Transform(rows[k][1], new[k][1]) for k in range(3)]], 1.1),
            "Its idle time",
            (lambda: [*[Transform(rows[k][2], new[k][2]) for k in range(3)]], 0.6),
            "and its delivery",
            (lambda: [*[Transform(rows[k][3], new[k][3]) for k in range(3)], *[rows[k][0].animate.set_color(GOLD_M) for k in range(3)]], 0.6),
        ])

        thr = SurroundingRectangle(c4[28:33], color=GOLD_M, buff=0.06, stroke_width=2)
        self.steps("Pick the threshold above your slowest normal run, so a worker that's only slow keeps its entries.", [
            (lambda: [Create(thr)], 0.6),
            "a worker that's only slow",
            (lambda: [glow(ws[2][0], WHITE, 1.06)], 0.8),
            (lambda: [FadeOut(thr)], 0.4),
        ])

        empty = T("empty", 19, GREEN_M).move_to([4.05, TY[1], 0])
        self.steps("w3 settles all three and acknowledges them, and the list is empty. "
                   "A crash between settling and acknowledging means a second delivery, so settling must be idempotent.", [
            (lambda: [*[h[0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M, 0.2), 1) for h in h1]], 0.7),
            "and acknowledges",
            (lambda: [Transform(c3, cmd("XACK payments settlers 1-1 1-2 1-3"))], 0.5),
            (lambda: [*[FadeOut(rows[k], shift=0.2 * RIGHT) for k in range(3)], FadeOut(VGroup(*h1))], 0.8),
            (lambda: [FadeIn(empty)], 0.5),
            "A crash between",
            (lambda: [glow(frame, BLUE_M, 1.02)], 0.9),
        ])

        self.steps("A consumer group remembers every delivery until it's acknowledged. "
                   "When a worker dies, another claims its entries once they've sat idle long enough.", [
            (lambda: [glow(frame, BLUE_M, 1.02), glow(gbox, GOLD_M, 1.04)], 1.0),
            "When a worker dies",
            (lambda: [glow(ws[1][0], RED_M, 1.06)], 0.7),
            "another claims",
            (lambda: [glow(ws[3][0], GOLD_M, 1.06)], 0.8),
        ])
        self.wait(0.6)
