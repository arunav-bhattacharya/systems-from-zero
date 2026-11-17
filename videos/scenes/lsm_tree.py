from sfz import *

# Keys are said as names ("auth two", "auth five hundred"); captions keep "auth:2".
SAY.insert(0, (r"\bauth:0*(\d+)", r"auth \1"))
SAY.insert(0, (r"\b(CAPTURED|PENDING)\b", lambda m: m.group(1).lower()))
SAY.insert(0, (r"\bmemtable\b", "mem table"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BW = 3.8                                   # box width
XS = {"mt": -4.7, "s2": 0.0, "s1": 4.7}    # the memtable (in memory), then the files on disk, newest first
TOP, BOT = 1.7, -0.9
BCY = (TOP + BOT) / 2
ROW_Y = [0.78, 0.3, -0.18]
STAT_Y = -0.62
Q_Y, ZONE_Y = 2.85, 2.08
ANS_Y, CNT_Y, BAR_Y, CAP_Y = -1.55, -2.15, -2.72, -3.25
SHELF_X0, SHELF_X1 = XS["s2"] - BW / 2, XS["s1"] + BW / 2


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
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def harrow(x0, x1, y, color=GREY_B, sw=2.5):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2,
                 max_stroke_width_to_length_ratio=8)


def frame_box(x, color, w=BW, top=TOP, bot=BOT):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=top - bot, stroke_color=color, stroke_width=3)
    return r.set_fill(fillc(color), 1).move_to([x, (top + bot) / 2, 0])


def title_at(x, s, color):
    return T(s, 22, color).move_to([x, TOP - 0.36, 0])


VAL_COL = {"PENDING": WHITE, "CAPTURED": WHITE, "tombstone": RED_M}


class LsmTree(Base):
    """store-05, section 1. One payment, two answers on disk (PENDING in an old file, CAPTURED in a newer one).
    The clerk: a sorted tray on the desk, bound into booklets, newest in front; corrections and cancel slips go into
    the tray. Mapped: memtable, SSTable, tombstone. The stepper builds the stack (three puts, flush, an update and a
    delete, flush). Oldest-first gives last minute's answer; the clerk's way (tray, then booklets from the front,
    stop at the first hit) reads auth:2, auth:1 and auth:3, where the tombstone stops the read. Inside one file:
    blocks of 16 and a sparse index of 63 entries, one read per lookup. Twenty files: 19 useless reads, 20 for a
    missing key, read amplification, and the two fixes. Moral and a check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
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

    def row(self, b, i, key, val, color=None):
        s = f"{key} = {val}" if val else key
        m = left_at(M(s, 20, color or VAL_COL.get(val, WHITE)), XS[b] - BW / 2 + 0.28, ROW_Y[i])
        return self.put((b, i), m, RIGHT)

    def unrow(self, b):
        return self.drop(*[(b, i) for i in range(3)])

    def stat(self, b, s, color=GREY_B):
        return self.put(("st", b), T(s, 19, color).move_to([XS[b], STAT_Y, 0]))

    def title(self, b, s, color):
        return self.put(("t", b), title_at(XS[b], s, color))

    def ask(self, b, s="get(auth:2)"):
        """The read token: a yellow chip above the box being asked. The same read moves; a new read replaces it."""
        new = chip(s, YELLOW_M, 22, mono=True).move_to([XS[b], Q_Y, 0])
        new.q = s
        new.set_z_index(4)
        old = self.lab.get("q")
        if old is not None and old.q == s:
            return [old.animate.move_to(new.get_center())]
        self.lab["q"] = new
        return [swap(old, new)]

    def answer(self, s, color=GREEN_M):
        return self.put("ans", T(s, 26, color).move_to([0, ANS_Y, 0]))

    def count(self, s, color=GREY_B):
        return self.put("cnt", T(s, 22, color).move_to([0, CNT_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def form(self, s, color=WHITE):
        t = M(s, 18, color)
        r = RoundedRectangle(corner_radius=0.06, width=t.width + 0.3, height=0.4, stroke_color=color, stroke_width=2)
        r.set_fill(fillc(color, 0.25), 1)
        return VGroup(r, t.move_to(r)).set_z_index(3)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Two answers on disk", "reading a stack of sorted files, newest first")

        box = {b: frame_box(XS[b], TEAL_M if b == "mt" else BLUE_M) for b in XS}

        # ---------------- scene 1: the question ----------------
        self.steps("Here's a card payment, named auth:2. When the bank said yes, the database saved it as PENDING: "
                   "approved, but no money has moved yet.", [
            "When the bank",
            (lambda: [FadeIn(box["s1"]), *self.title("s1", "a file on disk", BLUE_M)], 0.7),
            "saved it as",
            (lambda: self.row("s1", 1, "auth:2", "PENDING"), 0.6),
            "approved, but",
            (lambda: [Indicate(self.lab[("s1", 1)], color=WHITE, scale_factor=1.06)], 0.8),
        ])
        self.steps("A minute later, the money moved, and the database saved CAPTURED. Both records are on disk now, "
                   "in two different files, and neither file was ever changed.", [
            "the database saved",
            (lambda: [FadeIn(box["s2"]), *self.title("s2", "another file", BLUE_M)], 0.6),
            (lambda: self.row("s2", 1, "auth:2", "CAPTURED"), 0.6),
            "Both records",
            (lambda: [Indicate(self.lab[("s1", 1)], color=WHITE, scale_factor=1.06),
                      Indicate(self.lab[("s2", 1)], color=WHITE, scale_factor=1.06)], 0.9),
            "neither file",
            (lambda: [glow(box["s1"], BLUE_M, 1.02), glow(box["s2"], BLUE_M, 1.02)], 0.8),
        ])
        qm = T("?", 48, YELLOW_M).move_to([XS["mt"], BCY, 0])
        self.steps("So a program asks for auth:2. Which answer comes back? And how does the database know it's the right one?", [
            "asks for",
            (lambda: self.ask("mt"), 0.6),
            "Which answer",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "how does",
            (lambda: [*self.cap("which one comes back, and how does it know?", WHITE)], 0.6),
        ], after=0.4)

        # ---------------- scene 2: the clerk ----------------
        self.steps("To see how two answers got there, picture a clerk with a pile of forms. "
                   "Filing each form in its drawer means a walk across the room, per form.", [
            (lambda: [FadeOut(qm), *self.uncap(), *self.drop("q"), *self.unrow("s1"), *self.unrow("s2"),
                      *self.drop(("t", "s1"), ("t", "s2")), FadeOut(box["s1"]), FadeOut(box["s2"])], 0.8),
            "picture a clerk",
            (lambda: self.cap("a clerk with a pile of forms", WHITE), 0.5),
            "a walk across",
            (lambda: self.cap("filing each form in its drawer: one walk across the room per form", WHITE), 0.5),
        ])
        forms = [self.form(f"form {n}") for n in (7, 3, 5)]
        self.steps("That would make her the fittest clerk in the building, and the slowest. "
                   "So she keeps a tray on her desk, in order by form number.", [
            "So she keeps",
            (lambda: [*self.uncap(), FadeIn(box["mt"]), *self.title("mt", "the tray, on her desk", TEAL_M)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(f.move_to([XS["mt"] - 1.0 + 1.0 * k, Q_Y, 0]), shift=0.15 * DOWN)
                                    for k, f in enumerate(forms)], lag_ratio=0.3)], 0.9),
            "in order",
            (lambda: [forms[1].animate.move_to([XS["mt"], ROW_Y[0], 0]), forms[2].animate.move_to([XS["mt"], ROW_Y[1], 0]),
                      forms[0].animate.move_to([XS["mt"], ROW_Y[2], 0])], 0.9),
        ])
        book1 = frame_box(XS["s1"], BLUE_M)
        nf = DashedVMobject(frame_box(XS["s2"], GREY_C).set_fill(opacity=0), num_dashes=60)
        nft = T("the next one goes in front", 19, GREY_B).move_to([XS["s2"], BCY, 0])
        self.steps("When the tray is full, she binds it into a booklet and puts it on the shelf, newest in front. "
                   "A bound booklet is never changed.", [
            "she binds it",
            (lambda: [FadeIn(book1), *self.title("s1", "booklet 1", BLUE_M),
                      *[f.animate.move_to([XS["s1"], ROW_Y[k], 0]) for k, f in zip((2, 0, 1), forms)]], 1.0),
            "newest in front",
            (lambda: [FadeIn(nf), FadeIn(nft)], 0.7),
            "never changed",
            (lambda: [glow(book1, BLUE_M, 1.02)], 0.8),
        ])
        self.shelf_hint = VGroup(nf, nft)
        fix = self.form("form 5, fixed")
        cancel = self.form("form 7: cancelled", RED_M)
        self.steps("A correction goes into the tray, like any new form. And to cancel a form, she adds a slip to the tray "
                   "that says cancelled.", [
            "A correction",
            (lambda: [FadeIn(fix.move_to([XS["mt"], Q_Y, 0]), shift=0.15 * DOWN)], 0.5),
            (lambda: [fix.animate.move_to([XS["mt"], ROW_Y[0], 0])], 0.6),
            "to cancel",
            (lambda: [FadeIn(cancel.move_to([XS["mt"], Q_Y, 0]), shift=0.15 * DOWN)], 0.5),
            (lambda: [cancel.animate.move_to([XS["mt"], ROW_Y[1], 0])], 0.6),
            "says cancelled",
            (lambda: [Indicate(cancel, color=RED_M, scale_factor=1.1)], 0.7),
        ])
        self.steps("Let's map it. The tray is the memtable: a sorted list in memory that takes every new write.", [
            "The tray is",
            (lambda: [*self.title("mt", "memtable (in memory)", TEAL_M), glow(box["mt"], TEAL_M, 1.02)], 0.8),
        ])
        self.steps("A booklet is an SSTable: a sorted file on disk that never changes.", [
            "A booklet is",
            (lambda: [*self.title("s1", "SSTable (on disk)", BLUE_M), glow(book1, BLUE_M, 1.02)], 0.8),
        ])
        tomb_lab = T("tombstone", 19, RED_M).move_to([XS["mt"], STAT_Y, 0])
        self.steps("And the cancel slip is a tombstone, a record that says this key is deleted.", [
            "the cancel slip",
            (lambda: [Indicate(cancel, color=RED_M, scale_factor=1.1), FadeIn(tomb_lab, shift=0.1 * UP)], 0.8),
        ], after=0.4)
        self.stamp("clerk")

        # ---------------- scene 3: build the stack (the stepper) ----------------
        self.zones = VGroup(T("in memory", 19, GREY_B).move_to([XS["mt"], ZONE_Y, 0]),
                            T("on disk, newest first", 19, GREY_B).move_to([(SHELF_X0 + SHELF_X1) / 2, ZONE_Y, 0]))
        self.steps("Now the real thing, with three payments. auth:1, auth:2 and auth:3 arrive, all PENDING. "
                   "Each goes into the memtable, in key order. No file on disk changes.", [
            (lambda: [FadeOut(VGroup(*forms, fix, cancel, tomb_lab, self.shelf_hint)), FadeOut(book1),
                      *self.drop(("t", "s1"))], 0.7),
            "auth:1, auth:2",
            (lambda: self.row("mt", 0, "auth:1", "PENDING"), 0.4),
            (lambda: self.row("mt", 1, "auth:2", "PENDING"), 0.4),
            (lambda: self.row("mt", 2, "auth:3", "PENDING"), 0.4),
            "No file",
            (lambda: [FadeIn(self.zones)], 0.6),
        ])
        self.steps("The memtable reaches its size limit, so it's written to disk in key order, in one long write. "
                   "That's called a flush, and the new file is SSTable 1.", [
            "written to disk",
            (lambda: [FadeIn(box["s1"]), *self.title("s1", "SSTable 1 (older)", BLUE_M)], 0.5),
            (lambda: [*[self.lab[("mt", i)].animate.move_to(self.lab[("mt", i)].get_center() + [XS["s1"] - XS["mt"], 0, 0])
                        for i in range(3)]], 1.0),
            (lambda: [_relabel(self, "mt", "s1")], 0.05),
            "called a flush",
            (lambda: [*self.stat("mt", "empty"), *self.cap("flush: the memtable, written out as a new file", WHITE)], 0.6),
        ])
        self.steps("Then auth:2's money moves, so CAPTURED goes into the memtable. And auth:3 is deleted, so a tombstone goes in. "
                   "SSTable 1 isn't touched. It still says PENDING for both.", [
            (lambda: [*self.uncap(), *self.drop(("st", "mt"))], 0.3),
            "CAPTURED goes",
            (lambda: self.row("mt", 0, "auth:2", "CAPTURED"), 0.5),
            "a tombstone",
            (lambda: self.row("mt", 1, "auth:3", "tombstone"), 0.5),
            "SSTable 1 isn't",
            (lambda: [glow(box["s1"], BLUE_M, 1.02)], 0.7),
            "still says",
            (lambda: [Indicate(self.lab[("s1", 1)], color=WHITE, scale_factor=1.06),
                      Indicate(self.lab[("s1", 2)], color=WHITE, scale_factor=1.06)], 0.8),
        ])
        self.steps("Another flush makes SSTable 2. So the disk holds two versions of auth:2, and two of auth:3. "
                   "Only the order of the files says which one is current.", [
            "Another flush",
            (lambda: [FadeIn(box["s2"]), *self.title("s2", "SSTable 2 (newer)", BLUE_M)], 0.5),
            (lambda: [*[self.lab[("mt", i)].animate.move_to(self.lab[("mt", i)].get_center() + [XS["s2"] - XS["mt"], 0, 0])
                        for i in range(2)]], 0.9),
            (lambda: [_relabel(self, "mt", "s2"), *self.stat("mt", "empty")], 0.05),
            "two versions of auth:2",
            (lambda: [Indicate(self.lab[("s2", 0)], color=WHITE, scale_factor=1.06),
                      Indicate(self.lab[("s1", 1)], color=WHITE, scale_factor=1.06)], 0.8),
            "two of auth:3",
            (lambda: [Indicate(self.lab[("s2", 1)], color=RED_M, scale_factor=1.06),
                      Indicate(self.lab[("s1", 2)], color=WHITE, scale_factor=1.06)], 0.8),
            "Only the order",
            (lambda: [Indicate(self.zones[1], color=WHITE, scale_factor=1.12)], 0.8),
        ], after=0.4)
        self.stamp("stack")

        # ---------------- scene 4: the wrong model ----------------
        a1 = harrow(XS["mt"] + BW / 2 + 0.1, XS["s2"] - BW / 2 - 0.1, BCY)
        a2 = harrow(XS["s2"] + BW / 2 + 0.1, XS["s1"] - BW / 2 - 0.1, BCY)
        self.steps("So how should a read search the files? One idea feels natural: start at the oldest, "
                   "like reading a book from page one, and take the first match.", [
            "start at the oldest",
            (lambda: [*self.cap("start at the oldest, take the first match?", PURPLE_M)], 0.6),
            (lambda: [*self.ask("s1")], 0.6),
        ])
        self.steps("Let's try it for auth:2. SSTable 1 has it: PENDING. Done? Well... that's last minute's answer. "
                   "The money has already moved.", [
            "SSTable 1 has it",
            (lambda: [Indicate(self.lab[("s1", 1)], color=PURPLE_M, scale_factor=1.06), *self.answer("answer: PENDING", PURPLE_M)], 0.8),
            "that's last minute's",
            (lambda: [*self.answer("answer: PENDING (stale)", RED_M), Indicate(self.lab[("s2", 0)], color=WHITE, scale_factor=1.06)], 0.8),
        ], after=0.4)

        # ---------------- scene 5: newest first, stop at the first hit ----------------
        self.steps("What would the clerk do? She checks the tray first, then the booklets from the front of the shelf, "
                   "and stops at the first one that has the form.", [
            (lambda: [*self.drop("ans"), *self.cap("the clerk: the tray first, then the booklets from the front", WHITE)], 0.6),
            "checks the tray",
            (lambda: [glow(box["mt"], TEAL_M, 1.02)], 0.6),
            "then the booklets",
            (lambda: [GrowArrow(a1), GrowArrow(a2)], 0.7),
            "stops at the first",
            (lambda: self.cap("newest first, and stop at the first file that knows the key", YELLOW_M), 0.6),
        ])
        self.steps("So a read of auth:2 checks the memtable first. Not there. Then SSTable 2, the newest file. "
                   "It has auth:2: CAPTURED. The read stops. SSTable 1, with its old PENDING, is never asked.", [
            (lambda: [*self.uncap(), *self.ask("mt"), *self.count("disk reads: 0")], 0.6),
            "Not there",
            (lambda: self.stat("mt", "no auth:2 here"), 0.4),
            "Then SSTable 2",
            (lambda: [*self.ask("s2"), travel(a1, YELLOW_M, 0.5)], 0.6),
            "It has auth:2",
            (lambda: [Indicate(self.lab[("s2", 0)], color=GREEN_M, scale_factor=1.06), *self.stat("s2", "found", GREEN_M),
                      *self.count("disk reads: 1")], 0.6),
            (lambda: self.answer("answer: CAPTURED"), 0.5),
            "SSTable 1, with",
            (lambda: [box["s1"].animate.set_stroke(GREY_D), *self.stat("s1", "not asked")], 0.6),
        ])
        self.steps("A read of auth:1 checks the memtable. Not there. SSTable 2 doesn't have it either, "
                   "and finding that out costs a block read, for nothing. SSTable 1 does: PENDING.", [
            (lambda: [*self.drop("ans", ("st", "s2"), ("st", "s1")), box["s1"].animate.set_stroke(BLUE_M),
                      *self.ask("mt", "get(auth:1)"), *self.count("disk reads: 0")], 0.6),
            "Not there",
            (lambda: self.stat("mt", "no auth:1 here"), 0.4),
            "SSTable 2 doesn't",
            (lambda: [*self.ask("s2", "get(auth:1)"), travel(a1, YELLOW_M, 0.5)], 0.6),
            "costs a block read",
            (lambda: [*self.stat("s2", "1 read, nothing found", RED_M), *self.count("disk reads: 1")], 0.6),
            "SSTable 1 does",
            (lambda: [*self.ask("s1", "get(auth:1)"), travel(a2, YELLOW_M, 0.5)], 0.6),
            (lambda: [Indicate(self.lab[("s1", 0)], color=GREEN_M, scale_factor=1.06), *self.stat("s1", "found", GREEN_M),
                      *self.count("disk reads: 2"), *self.answer("answer: PENDING")], 0.6),
        ], after=0.4)
        self.stamp("reads")

        # ---------------- scene 6: the tombstone ----------------
        self.steps("Now auth:3, the payment that was deleted. The memtable is empty. SSTable 2 holds a tombstone, "
                   "and SSTable 1 still says PENDING. What should the read answer? Pause and guess.", [
            (lambda: [*self.drop("ans", "cnt", ("st", "s2"), ("st", "s1")), *self.ask("mt", "get(auth:3)"),
                      *self.stat("mt", "empty")], 0.6),
            "SSTable 2 holds",
            (lambda: [Indicate(self.lab[("s2", 1)], color=RED_M, scale_factor=1.06)], 0.7),
            "SSTable 1 still",
            (lambda: [Indicate(self.lab[("s1", 2)], color=WHITE, scale_factor=1.06)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Not found. The read stops at the tombstone. If it carried on, SSTable 1 would hand back PENDING, "
                   "and a deleted payment would come back to life.", [
            (lambda: [*self.uncap(), *self.ask("s2", "get(auth:3)"), travel(a1, YELLOW_M, 0.5)], 0.6),
            (lambda: [*self.stat("s2", "tombstone: stop", RED_M), *self.answer("answer: not found")], 0.6),
            "If it carried on",
            (lambda: [*self.ask("s1", "get(auth:3)"), Indicate(self.lab[("s1", 2)], color=RED_M, scale_factor=1.06),
                      *self.stat("s1", "PENDING: wrong", RED_M)], 0.8),
            "a deleted payment",
            (lambda: [*self.ask("s2", "get(auth:3)"), *self.stat("s1", "not asked")], 0.7),
        ])
        self.steps("Tombstone is a good name for it. It marks the spot, and it tells you not to dig any deeper. "
                   "So the first file that knows the key wins, even when what it knows is deleted.", [
            "It marks the spot",
            (lambda: [Indicate(self.lab[("s2", 1)], color=RED_M, scale_factor=1.06)], 0.7),
            "not to dig",
            (lambda: [box["s1"].animate.set_stroke(GREY_D)], 0.6),
            "So the first file",
            (lambda: self.cap("the first file that knows the key wins, even if it says deleted", YELLOW_M), 0.6),
        ], after=0.4)
        self.stamp("tombstone")

        # ---------------- scene 7: inside one file ----------------
        self.steps("That's which file. Now, what does asking one file cost? An SSTable is records in key order, "
                   "grouped into blocks. In the lab, a block is 16 records.", [
            (lambda: [*self.uncap(), glow(box["s1"], BLUE_M, 1.02)], 0.6),
            "what does asking",
            (lambda: _clear(self), 0.7),
            (lambda: _inside(self), 0.9),
            "grouped into blocks",
            (lambda: [LaggedStart(*[Indicate(b, color=BLUE_M, scale_factor=1.3) for b in self.strip[:8]], lag_ratio=0.15)], 1.0),
            "a block is 16",
            (lambda: self.cap("the lab's file: 1,000 records, 63 blocks of 16", WHITE), 0.6),
        ])
        self.steps("Because the file is sorted, it doesn't need an entry for every key. A small index holds only the first key "
                   "of each block, and where that block starts. That's called a sparse index.", [
            "A small index",
            (lambda: [FadeIn(self.ix_box), FadeIn(self.ix_title)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in self.ix_rows], lag_ratio=0.2)], 1.4),
            "where that block",
            (lambda: [*[Create(l) for l in self.ix_links]], 0.6),
            "called a sparse index",
            (lambda: [Transform(self.ix_title, T("sparse index", 22, TEAL_M).move_to(self.ix_title)), glow(self.ix_box, TEAL_M, 1.02)], 0.7),
        ])
        self.steps("The lab's file of 1,000 records needs 63 entries. That's small enough to keep in memory.", [
            (lambda: self.cap("1,000 records: 63 index entries, kept in memory", TEAL_M), 0.6),
            "small enough",
            (lambda: [glow(self.ix_box, TEAL_M, 1.02)], 0.7),
        ])
        q5 = chip("get(auth:00500)", YELLOW_M, 22, mono=True).move_to([-4.4, 3.2, 0])
        self.steps("To find auth:00500, look for the last block whose first key isn't above it. That's the block that starts at "
                   "auth:00496. Read that one block, and scan it. One disk read.", [
            (lambda: [*self.uncap(), FadeIn(q5, shift=0.1 * DOWN)], 0.5),
            "the last block",
            (lambda: [Indicate(self.ix_rows[3], color=YELLOW_M, scale_factor=1.1), Indicate(self.ix_rows[4], color=GREY_B, scale_factor=1.05)], 0.8),
            "starts at",
            (lambda: [self.ix_rows[3].animate.set_color(YELLOW_M), self.ix_links[1].animate.set_stroke(YELLOW_M, 3)], 0.5),
            "Read that one",
            (lambda: [self.strip[31].animate.set_fill(YELLOW_M, 1).set_stroke(YELLOW_M), FadeIn(self.blk, shift=0.15 * DOWN),
                      Create(self.zoom_l)], 0.8),
            "and scan it",
            (lambda: [LaggedStart(*[Indicate(c, color=YELLOW_M, scale_factor=1.0) for c in self.recs[:5]], lag_ratio=0.3)], 1.0),
            (lambda: [self.recs[4].animate.set_color(GREEN_M)], 0.3),
            "One disk read",
            (lambda: self.cap("one lookup in one file: one block read", YELLOW_M), 0.5),
        ], after=0.4)
        self.stamp("inside")

        # ---------------- scene 8: twenty files ----------------
        n = 20
        gw = (SHELF_X1 - SHELF_X0) / n
        files = VGroup(*[frame_box(SHELF_X0 + gw * (k + 0.5), BLUE_M, w=gw - 0.07) for k in range(n)])
        nums = VGroup(*[T(str(n - k), 15, GREY_B).move_to([SHELF_X0 + gw * (k + 0.5), TOP - 0.3, 0]) for k in range(n)])
        mt_box = box["mt"]
        self.steps("So one file costs at most one read. But how many files? Picture 20 SSTables on the shelf.", [
            (lambda: [*self.uncap()], 0.4),
            (lambda: _clear(self), 0.6),
            "how many files",
            (lambda: [FadeIn(mt_box), *self.title("mt", "memtable (in memory)", TEAL_M), FadeIn(self.zones)], 0.6),
            "Picture 20",
            (lambda: [LaggedStart(*[FadeIn(f) for f in files], lag_ratio=0.05), LaggedStart(*[FadeIn(x) for x in nums], lag_ratio=0.05)], 1.2),
        ])
        marks = [tick(False, 0.12).move_to([SHELF_X0 + gw * (k + 0.5), STAT_Y, 0]) for k in range(n)]
        hit = tick(True, 0.13).move_to([SHELF_X0 + gw * (n - 0.5), STAT_Y, 0])
        old_key = Rectangle(width=gw - 0.2, height=0.5, stroke_width=0).set_fill(GREEN_M, 0.85).move_to([SHELF_X0 + gw * (n - 0.5), ROW_Y[1], 0])
        self.steps("A key that only the oldest one holds costs 19 useless block reads first.", [
            (lambda: [FadeIn(old_key), *self.count("useless block reads: 0")], 0.5),
            "costs 19",
            (lambda: [LaggedStart(*[Create(m) for m in marks[:n - 1]], lag_ratio=0.25), *self.count("useless block reads: 19", RED_M)], 2.0),
            (lambda: [Create(hit)], 0.4),
        ])
        self.steps("And a key that isn't anywhere costs all 20. That's a lot of booklets opened to learn a form isn't there.", [
            (lambda: [FadeOut(old_key), FadeOut(hit), *[FadeOut(m) for m in marks[:n - 1]], *self.count("useless block reads: 0")], 0.5),
            (lambda: [LaggedStart(*[Create(m) for m in marks], lag_ratio=0.2), *self.count("useless block reads: 20", RED_M)], 1.8),
            "That's a lot",
            (lambda: [LaggedStart(*[glow(f, RED_M, 1.04) for f in files], lag_ratio=0.04)], 1.2),
        ])
        self.steps("The number of disk reads for one lookup is called read amplification.", [
            "called read amplification",
            (lambda: [*self.cap("read amplification: disk reads for one lookup", WHITE), Indicate(self.lab["cnt"], color=RED_M, scale_factor=1.12)], 0.8),
        ])
        merged = frame_box((SHELF_X0 + SHELF_X1) / 2, BLUE_M, w=3.2)
        self.steps("LSM trees fight it in two ways. A filter for each file lets most useless reads skip the disk. "
                   "And compaction merges files, so the stack stays short. The next part of the lesson builds the filter.", [
            "A filter for each",
            (lambda: [*self.cap("1. a filter per file: skip most useless reads", WHITE),
                      *[m.animate.set_opacity(0.15) for m in marks], *self.count("most useless reads: skipped", GREEN_M)], 0.8),
            "And compaction",
            (lambda: [*self.cap("2. compaction: merge files, keep the stack short", WHITE), FadeOut(VGroup(*marks)),
                      *self.drop("cnt")], 0.5),
            (lambda: [*[FadeOut(f, target_position=merged.get_center()) for f in files], FadeOut(nums), FadeIn(merged)], 1.0),
            "The next part",
            (lambda: self.cap("next: the filter", GREY_B), 0.5),
        ], after=0.4)
        self.stamp("twenty")

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So the moral of the story: files are never changed, so their order is the truth. "
                   "Read newest first, and the first one that knows the key wins.", [
            (lambda: [FadeOut(merged), *self.uncap()], 0.5),
            (lambda: [FadeIn(box["s1"].set_stroke(BLUE_M)), FadeIn(box["s2"].set_stroke(BLUE_M)), FadeIn(a1), FadeIn(a2),
                      *self.title("s2", "SSTable 2 (newer)", BLUE_M),
                      *self.title("s1", "SSTable 1 (older)", BLUE_M),
                      *self.row("s2", 0, "auth:2", "CAPTURED"), *self.row("s2", 1, "auth:3", "tombstone"),
                      *self.row("s1", 0, "auth:1", "PENDING"), *self.row("s1", 1, "auth:2", "PENDING"),
                      *self.row("s1", 2, "auth:3", "PENDING"), *self.stat("mt", "empty")], 0.8),
            "their order",
            (lambda: [Indicate(self.zones[1], color=WHITE, scale_factor=1.12)], 0.8),
            "Read newest first",
            (lambda: [*self.cap("newest first; the first file that knows the key wins", YELLOW_M, 28), travel(a1), travel(a2)], 0.9),
        ])
        self.steps("One quick check. Say auth:1's money moves now, and CAPTURED goes into the memtable. "
                   "How many SSTables does a read of auth:1 open? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "CAPTURED goes",
            (lambda: [*self.drop(("st", "mt")), *self.row("mt", 0, "auth:1", "CAPTURED")], 0.6),
            "How many",
            (lambda: [*self.ask("mt", "get(auth:1)")], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("None. The memtable knows auth:1, so it answers from memory, and no file is asked.", [
            (lambda: [*self.uncap(), Indicate(self.lab[("mt", 0)], color=GREEN_M, scale_factor=1.06),
                      *self.answer("answer: CAPTURED, 0 files opened")], 0.7),
            "no file is asked",
            (lambda: [*self.stat("s2", "not asked"), *self.stat("s1", "not asked"),
                      box["s2"].animate.set_stroke(GREY_D), box["s1"].animate.set_stroke(GREY_D)], 0.7),
        ], after=0.3)
        self.play(*self.cap("newest first; the first file that knows the key wins", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)


def _clear(scene):
    """Fade out everything on screen now, and forget the labels that pointed at it."""
    scene.lab = {}
    scene.capm = None
    return [FadeOut(Group(*scene.mobjects))]


def _relabel(scene, src, dst):
    """Rows that slid from one box to another now belong to the new box."""
    for i in range(3):
        m = scene.lab.pop((src, i), None)
        if m is not None:
            scene.lab[(dst, i)] = m
    return Wait(0.01)


def _inside(scene):
    """Inside one SSTable: a strip of 63 blocks, block 31 opened, and (built now, shown later) the sparse index."""
    sx0, sx1, sy = -1.2, 6.4, 2.1
    bw = (sx1 - sx0) / 63
    scene.strip = VGroup(*[Rectangle(width=bw - 0.025, height=0.5, stroke_color=BLUE_M, stroke_width=1.2)
                           .set_fill(fillc(BLUE_M, 0.35), 1).move_to([sx0 + bw * (k + 0.5), sy, 0]) for k in range(63)])
    file_t = T("one SSTable on disk: 63 blocks", 22, BLUE_M).move_to([(sx0 + sx1) / 2, sy + 0.62, 0])
    ends = VGroup(T("block 0", 16, GREY_B).move_to([sx0 + 0.35, sy - 0.55, 0]), T("block 62", 16, GREY_B).move_to([sx1 - 0.4, sy - 0.55, 0]))
    # block 31 opened: its 16 records, auth:00496 to auth:00511
    bx0, bx1, btop, bbot = 1.0, 6.4, 0.85, -2.0
    scene.blk = VGroup(RoundedRectangle(corner_radius=0.12, width=bx1 - bx0, height=btop - bbot, stroke_color=YELLOW_M, stroke_width=2.5)
                       .set_fill(BLACK, 1).move_to([(bx0 + bx1) / 2, (btop + bbot) / 2, 0]),
                       T("block 31: 16 records", 19, YELLOW_M).move_to([(bx0 + bx1) / 2, btop - 0.32, 0]))
    scene.recs = [M(f"auth:{496 + k:05d}", 14, WHITE).move_to([bx0 + 0.73 + 1.3 * (k % 4), btop - 0.88 - 0.5 * (k // 4), 0]) for k in range(16)]
    scene.blk.add(*scene.recs)
    scene.zoom_l = VGroup(DashedLine([sx0 + bw * 31, sy - 0.27, 0], [bx0 + 0.15, btop, 0], dash_length=0.06, stroke_width=1.5, color=YELLOW_M),
                          DashedLine([sx0 + bw * 32, sy - 0.27, 0], [bx1 - 0.15, btop, 0], dash_length=0.06, stroke_width=1.5, color=YELLOW_M))
    # the sparse index, in memory
    ix0, ix1, itop, ibot = -6.6, -2.2, 2.6, -2.0
    scene.ix_box = RoundedRectangle(corner_radius=0.14, width=ix1 - ix0, height=itop - ibot, stroke_color=TEAL_M, stroke_width=3) \
        .set_fill(fillc(TEAL_M), 1).move_to([(ix0 + ix1) / 2, (itop + ibot) / 2, 0])
    scene.ix_title = T("index (in memory)", 22, TEAL_M).move_to([(ix0 + ix1) / 2, itop - 0.38, 0])
    rows = [("auth:00000", "block 0"), ("auth:00016", "block 1"), ("...", ""), ("auth:00496", "block 31"),
            ("auth:00512", "block 32"), ("...", ""), ("auth:00992", "block 62")]
    scene.ix_rows = []
    for k, (key, blk) in enumerate(rows):
        y = itop - 1.0 - 0.52 * k
        g = VGroup(left_at(M(key, 18, WHITE if key != "..." else GREY_B), ix0 + 0.3, y))
        if blk:
            g.add(left_at(T(blk, 18, GREY_B), ix0 + 2.75, y))
        scene.ix_rows.append(g)
    # row 3 is auth:00496 (block 31), row 4 is auth:00512 (block 32)
    scene.ix_links = [DashedLine([ix1 + 0.05, scene.ix_rows[0].get_y(), 0], [sx0 + bw * 0.5, sy - 0.27, 0], dash_length=0.06,
                                 stroke_width=1.2, color=GREY_C),
                      DashedLine([ix1 + 0.05, scene.ix_rows[3].get_y(), 0], [sx0 + bw * 31.5, sy - 0.27, 0], dash_length=0.06,
                                 stroke_width=1.2, color=GREY_C)]
    return [FadeIn(scene.strip), FadeIn(file_t), FadeIn(ends)]
