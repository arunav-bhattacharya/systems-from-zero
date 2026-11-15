from sfz import *

# letters as names: "a" alone reads as "uh"
SAY.insert(0, (r"\b[Aa]gent a\b", "agent eh"))
SAY.insert(0, (r"\b[Aa]gent a's\b", "agent eh's"))
SAY.insert(0, (r"\b[Aa]gent b\b", "agent bee"))
SAY.insert(0, (r"\b[Aa]gent b's\b", "agent bee's"))
SAY.insert(0, (r"\bcopy c\b", "copy see"))
SAY.insert(0, (r"\b(\d)a\b", r"\1 eh"))
SAY.insert(0, (r"\b(\d)b\b", r"\1 bee"))

X0, PITCH, CW, CH = -3.9, 0.92, 0.8, 1.0
ROWY = {"a": 2.4, "b": 0.3, "c": -1.8}
CHIPX = 5.0
NOTE_Y = -3.35
A_C, B_C = GOLD_M, TEAL_M


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def sx(k):
    return X0 + k * PITCH


def cell(ch, color=GREY_B, cid=None):
    r = RoundedRectangle(corner_radius=0.08, width=CW, height=CH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    t = M(ch if ch != " " else "x", 40, WHITE)
    if ch == " ":
        t.set_opacity(0)
    g = VGroup(r, t)
    if cid:
        g.add(M(cid, 19, GREY_B).next_to(r, DOWN, buff=0.12))
    return g


class Row:
    """One copy of the note: a list of (key, cell), laid out left to right."""

    def __init__(self, y, items):
        self.y = y
        self.cells = []
        for key, ch, color, cid in items:
            c = cell(ch, color, cid)
            self.cells.append((key, c))
        for k, (_, c) in enumerate(self.cells):
            c.move_to([sx(k), y, 0], aligned_edge=ORIGIN)
            c.shift((y - c[0].get_center()[1]) * UP)

    def group(self):
        return VGroup(*[c for _, c in self.cells])

    def get(self, key):
        return dict(self.cells)[key]

    def index(self, key):
        return [k for k, _ in self.cells].index(key)

    def insert(self, k, key, ch, color, cid=None):
        """Animations that open slot k and drop a new character into it."""
        anims = [c.animate.shift(PITCH * RIGHT) for _, c in self.cells[k:]]
        new = cell(ch, color, cid)
        new.shift([sx(k), self.y, 0] - new[0].get_center())
        self.cells.insert(k, (key, new))
        return anims + [FadeIn(new, shift=0.3 * DOWN)]

    def drop(self, key):
        k = self.index(key)
        _, c = self.cells.pop(k)
        return [FadeOut(c)] + [c2.animate.shift(PITCH * LEFT) for _, c2 in self.cells[k:]]


def glow_row(row, color, s=1.06):
    return [glow(c[0], color, s) for _, c in row.cells]


def ruler(y, color=GREY_C):
    return VGroup(*[M(str(k), 20, color).move_to([sx(k), y - 0.8, 0]) for k in range(8)])


def label(s, y, color=WHITE):
    t = T(s, 28, color)
    return t.move_to([X0 - 0.75 - t.width / 2, y, 0])


def edit(s, color, y):
    return fit(chip(s, color, 22, mono=True), 3.1).move_to([CHIPX, y, 0])


def note(s, color=GREY_B):
    return chip(s, color, 21).move_to([0, NOTE_Y, 0])


BASE = [("1a", "p"), ("2a", "a"), ("3a", "y"), ("4a", " "), ("5a", "4"), ("6a", "0")]


class CrdtText(Base):
    """repl-06, section 3 (with section 2's failure): the note "pay 40"; agent a inserts "$" at 4, agent b inserts "!" at
    6, both offline. Replayed by position, b gets "pay $40!" and a gets "pay $4!0". In RGA every character has an id
    (counter + site): "$" is 7a after 4a, "!" is 7b after 6a; both copies, and a third that hears them in the other
    order, end with "pay $40!". Ties: the bigger id first. The price: ids and tombstones, 17 bytes per visible character
    in the lab's run."""

    def construct(self):
        self.title_card("Text that merges by itself", "a sequence CRDT names every character")

        ra = Row(ROWY["a"], [(k, ch, GREY_B, None) for k, ch in BASE])
        rb = Row(ROWY["b"], [(k, ch, GREY_B, None) for k, ch in BASE])
        la, lb = label("agent a", ROWY["a"], A_C), label("agent b", ROWY["b"], B_C)
        off = T("both offline", 22, GREY_B).move_to([CHIPX, (ROWY["a"] + ROWY["b"]) / 2, 0])
        self.steps("Two agents edit the same dispute note on their laptops, both offline. The note says pay 40.", [
            (lambda: [FadeIn(la), FadeIn(lb)], 0.6),
            (lambda: [FadeIn(ra.group(), shift=0.1 * UP), FadeIn(rb.group(), shift=0.1 * UP)], 0.9),
            "both offline",
            (lambda: [FadeIn(off)], 0.5),
            "The note says",
            (lambda: [*[glow(c[0], WHITE, 1.06) for _, c in ra.cells + rb.cells]], 0.9),
        ])

        self.steps("Agent a types a dollar sign before the 4. Agent b types an exclamation mark at the end.", [
            (lambda: ra.insert(4, "$", "$", A_C), 0.8),
            "Agent b types",
            (lambda: rb.insert(6, "!", "!", B_C), 0.8),
        ])

        rua, rub = ruler(ROWY["a"]), ruler(ROWY["b"])
        ea = edit("insert $ at 4", A_C, ROWY["a"])
        eb = edit("insert ! at 6", B_C, ROWY["b"])
        self.steps("The simplest edit names a position: insert dollar sign at 4, and insert exclamation mark at 6.", [
            (lambda: [FadeOut(off), FadeIn(rua), FadeIn(rub)], 0.7),
            "insert dollar",
            (lambda: [FadeIn(ea, shift=0.1 * LEFT), rua[4].animate.set_color(A_C).scale(1.3)], 0.6),
            "and insert",
            (lambda: [FadeIn(eb, shift=0.1 * LEFT), rub[6].animate.set_color(B_C).scale(1.3)], 0.6),
        ])

        ea_b = edit("insert $ at 4", A_C, ROWY["b"] - 0.85)
        self.steps("Back online, they swap. Agent b puts the dollar sign at position 4, and gets the text they both meant.", [
            (lambda: [rua[4].animate.set_color(GREY_C).scale(1 / 1.3), rub[6].animate.set_color(GREY_C).scale(1 / 1.3)], 0.4),
            (lambda: [FadeOut(ea, shift=0.3 * DOWN)], 0.4),
            (lambda: [FadeIn(ea_b, shift=0.3 * DOWN)], 0.4),
            "Agent b puts",
            (lambda: [rub[4].animate.set_color(A_C).scale(1.3)], 0.5),
            (lambda: rb.insert(4, "$", "$", A_C), 0.8),
            "and gets",
            (lambda: [*[c[0].animate.set_stroke(GREEN_M) for _, c in rb.cells]], 0.6),
        ])

        self.steps("Agent a puts the exclamation mark at position 6. But a's text grew by one in front of that spot, "
                   "so 6 now falls between the 4 and the 0.", [
            (lambda: [rub[4].animate.set_color(GREY_C).scale(1 / 1.3), FadeOut(ea_b),
                      eb.animate.move_to([CHIPX, ROWY["a"] + 0.0, 0])], 0.8),
            (lambda: [rua[6].animate.set_color(B_C).scale(1.3)], 0.5),
            "But a's text",
            (lambda: [glow(ra.get("$")[0], A_C, 1.12)], 0.8),
            "so 6 now falls",
            (lambda: ra.insert(6, "!", "!", B_C), 0.8),
            (lambda: [*[c[0].animate.set_stroke(RED_M) for _, c in ra.cells]], 0.6),
        ])

        diff = note("the copies differ: pay $4!0 and pay $40!", RED_M)
        self.steps("Now the copies differ. Position 6 meant after the 0 to agent b, and something else to agent a.", [
            (lambda: [FadeOut(eb), FadeIn(diff, shift=0.1 * UP)], 0.7),
            "Position 6 meant",
            (lambda: [glow(rb.get("6a")[0], B_C, 1.12)], 0.8),
            "and something else",
            (lambda: [glow(ra.get("5a")[0], RED_M, 1.12), glow(ra.get("6a")[0], RED_M, 1.12)], 0.8),
        ])

        def plain(row):
            return [c[0].animate.set_stroke(GREY_B) for k, c in row.cells if k not in ("$", "!")]

        def add_ids(row):
            out = []
            for k, c in row.cells:
                lab = M(k, 19, GREY_B).next_to(c[0], DOWN, buff=0.12)
                c.add(lab)
                out.append(FadeIn(lab, shift=0.1 * UP))
            return out

        self.steps("Start again with a sequence CRDT, which never sends a position. "
                   "Each character gets a permanent id when it's typed: a counter, plus the site that typed it.", [
            (lambda: [FadeOut(diff), *plain(ra), *plain(rb), rua[6].animate.set_color(GREY_C).scale(1 / 1.3)], 0.4),
            (lambda: [*ra.drop("!"), *rb.drop("!")], 0.5),
            (lambda: [*ra.drop("$"), *rb.drop("$")], 0.5),
            "Each character",
            (lambda: [FadeOut(rua), FadeOut(rub)], 0.4),
            (lambda: [*add_ids(ra), *add_ids(rb)], 0.8),
            "a counter",
            (lambda: [*[glow(c[0], GOLD_M, 1.06) for _, c in ra.cells]], 0.8),
        ])

        ea2 = edit("$ is 7a, after 4a", A_C, ROWY["a"])
        eb2 = edit("! is 7b, after 6a", B_C, ROWY["b"])
        self.steps("Agent a's dollar sign becomes 7a, inserted after 4a, the space. "
                   "Agent b's exclamation mark becomes 7b, after 6a, the 0.", [
            (lambda: ra.insert(4, "$", "$", A_C, "7a"), 0.8),
            "inserted after",
            (lambda: [FadeIn(ea2, shift=0.1 * LEFT), glow(ra.get("4a")[0], A_C, 1.12)], 0.8),
            "Agent b's",
            (lambda: rb.insert(6, "!", "!", B_C, "7b"), 0.8),
            "after 6a",
            (lambda: [FadeIn(eb2, shift=0.1 * LEFT), glow(rb.get("6a")[0], B_C, 1.12)], 0.8),
        ])

        self.steps("Swap again. At agent a, the exclamation mark goes right after 6a, wherever 6a has moved.", [
            (lambda: [eb2.animate.move_to([CHIPX, ROWY["a"] - 0.85, 0])], 0.8),
            "goes right after",
            (lambda: [glow(ra.get("6a")[0], B_C, 1.12)], 0.8),
            (lambda: ra.insert(ra.index("6a") + 1, "!", "!", B_C, "7b"), 0.8),
            (lambda: [*[c[0].animate.set_stroke(GREEN_M) for _, c in ra.cells]], 0.6),
        ])

        self.steps("At agent b, the dollar sign goes after 4a. Both copies now read the same.", [
            (lambda: [FadeOut(eb2)], 0.3),
            (lambda: [ea2.animate.move_to([CHIPX, ROWY["b"] - 0.85, 0])], 0.7),
            (lambda: [glow(rb.get("4a")[0], A_C, 1.12)], 0.6),
            (lambda: rb.insert(rb.index("4a") + 1, "$", "$", A_C, "7a"), 0.8),
            "Both copies",
            (lambda: [FadeOut(ea2), *[c[0].animate.set_stroke(GREEN_M) for _, c in rb.cells]], 0.6),
        ])

        rc = Row(ROWY["c"], [(k, ch, GREY_B, k) for k, ch in BASE])
        lc = label("copy c", ROWY["c"], GREY_A)
        e1 = edit("! is 7b, after 6a", B_C, ROWY["c"] + 0.45)
        e2 = edit("$ is 7a, after 4a", A_C, ROWY["c"] - 0.45)
        self.steps("Order doesn't matter either. A third copy, copy c, hears agent b's edit first and agent a's second, "
                   "and ends with the same text.", [
            (lambda: [FadeIn(lc), FadeIn(rc.group(), shift=0.1 * UP)], 0.7),
            "hears agent b's",
            (lambda: [FadeIn(e1, shift=0.1 * LEFT)], 0.4),
            (lambda: rc.insert(6, "!", "!", B_C, "7b"), 0.7),
            "and agent a's",
            (lambda: [FadeIn(e2, shift=0.1 * LEFT)], 0.4),
            (lambda: rc.insert(4, "$", "$", A_C, "7a"), 0.7),
            "and ends",
            (lambda: [FadeOut(e1), FadeOut(e2), *[c[0].animate.set_stroke(GREEN_M) for _, c in rc.cells]], 0.6),
        ])

        tie = note("two inserts after the same character: the bigger id goes first, everywhere", GREY_A)
        self.steps("If two inserts follow the same character, every copy puts the bigger id first.", [
            (lambda: [FadeIn(tie, shift=0.1 * UP)], 0.8),
            "every copy",
            (lambda: [*glow_row(ra, GREEN_M), *glow_row(rb, GREEN_M), *glow_row(rc, GREEN_M)], 1.0),
        ])

        def tomb(row):
            c = row.get("!")
            s = Line(c[0].get_corner(DL) + 0.08 * (UP + RIGHT), c[0].get_corner(UR) - 0.08 * (UP + RIGHT), stroke_width=3, color=RED_M)
            c.add(s)
            return [c[0].animate.set_stroke(GREY_D).set_fill(BLACK, 1), c[1].animate.set_color(GREY_D), Create(s)]

        cost = note("in the lab: 17 bytes of ids and flags per visible character", GOLD_M)
        self.steps("The price is the ids, kept forever. A deleted character stays as a tombstone, "
                   "because a late edit may still name it. In the lab, that cost 17 bytes per visible character.", [
            (lambda: [FadeOut(tie), *[c[2].animate.set_color(GOLD_M) for r in (ra, rb, rc) for _, c in r.cells]], 0.8),
            "A deleted",
            (lambda: [*tomb(ra), *tomb(rb), *tomb(rc)], 0.8),
            "because a late edit",
            (lambda: [*[glow(r.get("!")[0], GREY_B, 1.1) for r in (ra, rb, rc)]], 0.8),
            "In the lab",
            (lambda: [FadeIn(cost, shift=0.1 * UP)], 0.7),
        ])

        self.steps("Name every character, never a position, and every copy that sees the same edits ends with the same text.", [
            (lambda: [*[c[2].animate.set_color(GREY_B) for r in (ra, rb, rc) for _, c in r.cells]], 0.8),
            "and every copy",
            (lambda: [*glow_row(ra, GREEN_M), *glow_row(rb, GREEN_M), *glow_row(rc, GREEN_M)], 1.0),
        ])
        self.wait(0.6)
