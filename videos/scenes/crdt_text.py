from sfz import *

# Say the ids the way the lesson writes them: "4a" is "four A".
SAY.insert(0, (r"\b(\d)([ab])\b", lambda m: f"{m.group(1)} {'eh' if m.group(2) == 'a' else 'bee'}"))
SAY.insert(0, (r"\b([Aa]gent|[Ss]ite) a\b", r"\1 eh"))
SAY.insert(0, (r"\ba's\b", "eh's"))
SAY.insert(0, (r"(?<![\w'])a (sends|deletes|types)\b", r"eh \1"))
SAY.insert(0, (r"\bpay \$40!", "pay, dollar, forty, exclamation mark"))
SAY.insert(0, (r"\bpay \$45!", "pay, dollar, forty-five, exclamation mark"))
SAY.insert(0, (r"\bpay \$4!0\b", "pay, dollar, four, exclamation mark, zero"))
SAY.insert(0, (r"\bAutomerge\b", "auto-merge"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
ROW_Y = {"a": 1.45, "b": -1.05}
COLR = {"a": BLUE_M, "b": TEAL_M}
X0, PITCH, TS = -3.0, 0.85, 0.72
LAB_X = -5.15
CAP_Y, BAR_Y = -3.25, -2.75
BAND_Y = 0.2


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
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays; a number
        waits that long; a string waits until about where that phrase is spoken."""
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

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0]))

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


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def dot_run(a, b, color=YELLOW_M, rt=0.6, frac=1.0):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    d = Dot(radius=0.09, color=color).move_to(a).set_z_index(6)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.12))


def run(ar, color=YELLOW_M, rt=0.6):
    return dot_run(ar.get_start(), ar.get_end(), color, rt)



def slot(r, i):
    return np.array([X0 + PITCH * i, ROW_Y[r], 0])


def tile(r, i, ch, idt=None, color=None):
    c = color or COLR[r]
    sq = RoundedRectangle(corner_radius=0.08, width=TS, height=TS, stroke_color=c, stroke_width=2.5).set_fill(fillc(c, 0.3), 1)
    g = VGroup(sq)
    if ch == " ":
        g.add(Line([-0.16, -0.16, 0], [0.16, -0.16, 0], stroke_width=3, color=GREY_B))
    else:
        g.add(M(ch, 30, WHITE))
    if idt:
        g.add(M(idt, 18, GREY_B).move_to([0, -0.62, 0]))
    g.move_to(ORIGIN)
    g.shift(slot(r, i) - sq.get_center())
    return g


def mchip(text, color):
    return chip(text, color, 18, mono=True).set_z_index(7)


class CrdtText(Base):
    """repl-06, section 3. Two agents type into the note "pay 40" at once with no server. Position edits break:
    site a ends with "pay $4!0". Name every character instead (a serial number under every letter): ids 1a to 6a, a
    counter plus a site, next counter = 1 + highest seen. "$ 7a after 4a" and "! 7b after 6a" converge to "pay $40!"
    on both sites. Ties: the bigger id first. Deletes leave tombstones (a deletes the 0 while b types 5 named 8b after
    it: both "pay $45!"). The cost (10,000 edits: 2,136 visible, 6,068 kept, 17 bytes per visible character;
    Automerge 2 vs 3), "agree is not right", the moral and a check."""

    def row(self, r, spec, ids=True, color=None):
        """Replace row r with spec: a list of (char, id) pairs; returns animations."""
        out = []
        for t in self.rows.get(r, []):
            out.append(FadeOut(t["mob"]))
        self.rows[r] = []
        for i, (ch, idt) in enumerate(spec):
            m = tile(r, i, ch, idt if ids else None, color)
            self.rows[r].append({"ch": ch, "id": idt, "mob": m, "dead": False})
            out.append(FadeIn(m))
        return out

    def relayout(self, r):
        return [t["mob"].animate.shift(slot(r, i) - t["mob"][0].get_center()) for i, t in enumerate(self.rows[r])]

    def insert(self, r, idx, ch, idt=None, color=GOLD_M):
        m = tile(r, idx, ch, idt, color)
        self.rows[r].insert(idx, {"ch": ch, "id": idt, "mob": m, "dead": False})
        moves = [t["mob"].animate.shift(slot(r, i) - t["mob"][0].get_center()) for i, t in enumerate(self.rows[r]) if i != idx]
        return moves, m

    def ins_steps(self, r, idx, ch, idt=None, color=GOLD_M, rt=0.5):
        holder = {}

        def a():
            moves, m = self.insert(r, idx, ch, idt, color)
            holder["m"] = m
            return moves or [Wait(0.01)]

        def b():
            return [FadeIn(holder["m"], shift=0.2 * DOWN)]
        return [(a, rt), (b, 0.4)]

    def index_of(self, r, idt):
        return [t["id"] for t in self.rows[r]].index(idt)

    def kill(self, r, idt):
        t = self.rows[r][self.index_of(r, idt)]
        t["dead"] = True
        sq = t["mob"][0]
        x = VGroup(Line(sq.get_corner(UL), sq.get_corner(DR)), Line(sq.get_corner(DL), sq.get_corner(UR))).set_stroke(GREY_B, 2)
        t["mob"].add(x)
        return [sq.animate.set_stroke(GREY_D).set_fill(BLACK, 1), t["mob"][1].animate.set_opacity(0.3), Create(x)]

    def mark_all(self, r, color):
        return [t["mob"][0].animate.set_stroke(color) for t in self.rows[r] if not t["dead"]]

    def construct(self):
        self.lab = {}
        self.rows = {}
        self.title_card("Name every character", "how two people's typing merges, with no one in charge")
        base = [(c, f"{i + 1}a") for i, c in enumerate("pay 40")]
        la = VGroup(T("site a", 26, BLUE_M), T("agent a's laptop", 18, GREY_B)).arrange(DOWN, buff=0.1).move_to([LAB_X, ROW_Y["a"], 0])
        lb = VGroup(T("site b", 26, TEAL_M), T("agent b's laptop", 18, GREY_B)).arrange(DOWN, buff=0.1).move_to([LAB_X, ROW_Y["b"], 0])

        # ---------------- scene 1: no one in charge ----------------
        self.steps("Two support agents are typing into the same note at the same moment.", [
            (lambda: [FadeIn(la), FadeIn(lb), *self.row("a", base, False), *self.row("b", base, False)], 1.0),
        ])
        self.steps("Each one's typing shows up at once on their own laptop, and there's no server in the middle deciding who went first.", [
            "no server",
            (lambda: self.cap("no server in the middle", WHITE), 0.5),
        ])
        qm = T("?", 56, YELLOW_M).move_to([4.9, BAND_Y, 0])
        self.steps("At the end, both laptops must show the same note, with both people's typing kept. How, with no one in charge?", [
            "both laptops",
            (lambda: self.cap("same note on both, with both people's typing kept", WHITE), 0.5),
            "How, with",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
        ], after=0.4)

        # ---------------- scene 2: positions shift ----------------
        def posnums(r, n):
            return VGroup(*[M(str(i), 18, GREY_B).move_to(slot(r, i) + [0, -0.62, 0]) for i in range(n)])

        self.steps("Start with the simplest way to send an edit: insert a character at a position, counting from 0.", [
            (lambda: [FadeOut(qm), *self.drop("cap")], 0.4),
            "counting from 0",
            (lambda: [*self.put("pa", posnums("a", 6)), *self.put("pb", posnums("b", 6))], 0.7),
        ])
        ca = mchip("insert '$' at 4", BLUE_M)
        cb = mchip("insert '!' at 6", TEAL_M)
        self.steps("Agent a types a dollar sign before the 4: insert dollar at 4. Agent b types an exclamation mark at the end: insert it at 6.", [
            (lambda: self.drop("pa", "pb"), 0.3),
            *self.ins_steps("a", 4, "$"),
            "insert dollar",
            (lambda: [FadeIn(ca.move_to([-1.6, BAND_Y + 0.15, 0]))], 0.4),
            "Agent b types",
            *self.ins_steps("b", 6, "!"),
            "insert it at 6",
            (lambda: [FadeIn(cb.move_to([2.4, BAND_Y - 0.25, 0]))], 0.4),
        ])
        self.steps("Each sends the edit to the other. b's copy becomes pay $40!. a's copy becomes pay $4!0.", [
            (lambda: [ca.animate.move_to([-1.6, BAND_Y - 0.25, 0]), cb.animate.move_to([2.4, BAND_Y + 0.15, 0])], 1.0),
            "b's copy",
            (lambda: [FadeOut(ca)], 0.2),
            *self.ins_steps("b", 4, "$", color=BLUE_M),
            "a's copy",
            (lambda: [FadeOut(cb)], 0.2),
            *self.ins_steps("a", 6, "!", color=TEAL_M),
            (lambda: [*self.mark_all("a", RED_M), *self.put("pa", posnums("a", 8))], 0.5),
        ])
        self.steps("Position 6 meant after the 0 in b's text. In a's text, it's in the middle of the 40. Same number, two different places.", [
            "Position 6",
            (lambda: [Indicate(self.rows["b"][7]["mob"], color=WHITE)], 0.7),
            "In a's text",
            (lambda: [Indicate(self.rows["a"][6]["mob"], color=RED_M)], 0.7),
            "Same number",
            (lambda: self.cap("positions shift under each other", RED_M), 0.5),
        ])
        self.steps("One fix moves the positions before applying them, and it usually needs a server to agree the order. "
                   "What if an edit never mentioned a position at all?", [
            (lambda: self.cap("one fix: shift the positions first (it usually needs a server)", GREY_B), 0.5),
            "What if",
            (lambda: self.cap("what if an edit never mentioned a position?", YELLOW_M), 0.5),
        ])

        # ---------------- scene 3: a serial number under every letter ----------------
        self.steps("Picture a printed page with a small serial number under every letter.", [
            (lambda: [*self.drop("cap", "pa"), *self.row("a", base), *self.row("b", base)], 1.0),
        ])
        self.steps("Instead of put this at position 5, each person writes put this after letter 4a.", [
            "put this after",
            (lambda: [*self.cap("put this after letter 4a", WHITE), glow(self.rows["a"][3]["mob"][0], YELLOW_M, 1.1),
                      glow(self.rows["b"][3]["mob"][0], YELLOW_M, 1.1)], 0.9),
        ])
        self.steps("Anyone can apply the notes in any order, and get the same page. The serial number is the character's id, "
                   "and it never changes. The note is the edit.", [
            "any order",
            (lambda: self.cap("any order, same page", WHITE), 0.5),
            "The serial number",
            (lambda: [*self.cap("serial number = the character's id, forever", WHITE),
                      LaggedStart(*[Indicate(t["mob"][2], color=YELLOW_M) for t in self.rows["a"]], lag_ratio=0.15)], 1.0),
            "The note is",
            (lambda: self.cap("the note = the edit", WHITE), 0.5),
        ])

        # ---------------- scene 4: where the names come from ----------------
        self.steps("This is a CRDT, a conflict-free replicated data type: a data type whose copies can take edits apart, and still merge to the same result.", [
            "CRDT",
            (lambda: self.cap("CRDT: copies take edits apart, and merge to the same result", YELLOW_M), 0.6),
        ])
        expl = T("counter 6 + site a", 20, YELLOW_M).move_to(slot("a", 5) + [1.9, -0.62, 0])
        self.steps("In the lesson's version, an id is a counter plus a site name. Site a typed pay 40, so its letters are 1a to 6a.", [
            "a counter plus",
            (lambda: [*self.put("expl", expl), Indicate(self.rows["a"][5]["mob"][2], color=YELLOW_M, scale_factor=1.4)], 0.7),
            "1a to 6a",
            (lambda: [LaggedStart(*[Indicate(t["mob"][2], color=BLUE_M) for t in self.rows["a"]], lag_ratio=0.15)], 1.0),
        ])
        self.steps("Each site's next counter is one more than the highest it has seen from anyone. "
                   "So a letter typed after another always has a bigger counter.", [
            (lambda: [*self.drop("expl"), *self.cap("next counter = 1 + the highest seen (6, so 7)", WHITE)], 0.6),
            "So a letter",
            (lambda: self.cap("typed later means a bigger counter", WHITE), 0.5),
        ])

        # ---------------- scene 5: predict the merge ----------------
        ca = mchip("'$' 7a after 4a", BLUE_M)
        cb = mchip("'!' 7b after 6a", TEAL_M)
        self.steps("Now the same two edits, by name. a sends: insert dollar, named 7a, after 4a, the space.", [
            (lambda: self.drop("cap"), 0.3),
            *self.ins_steps("a", 4, "$", "7a"),
            "a sends",
            (lambda: [FadeIn(ca.move_to([-1.6, BAND_Y + 0.15, 0]))], 0.4),
        ])
        self.steps("b sends: insert exclamation mark, named 7b, after 6a, the 0. Neither mentions a position.", [
            *self.ins_steps("b", 6, "!", "7b"),
            (lambda: [FadeIn(cb.move_to([2.6, BAND_Y - 0.25, 0]))], 0.4),
            "Neither",
            (lambda: self.cap("no positions, only names", WHITE), 0.5),
        ])
        self.steps("What will each copy show? Pause and guess.", [
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Both say pay $40!.", [
            (lambda: [*self.drop("cap"), ca.animate.move_to([-1.6, BAND_Y - 0.25, 0]), cb.animate.move_to([2.6, BAND_Y + 0.15, 0])], 0.6),
            (lambda: [FadeOut(ca), FadeOut(cb)], 0.2),
            *self.ins_steps("b", 4, "$", "7a", BLUE_M, 0.4),
            *self.ins_steps("a", 7, "!", "7b", TEAL_M, 0.4),
        ])
        ticks = VGroup(*[tick(True, 0.2).move_to(slot(r, 8) + [0.3, 0, 0]) for r in "ab"])
        self.steps("The dollar finds the space wherever the space has moved to, and the exclamation mark finds the 0.", [
            (lambda: [Indicate(self.rows["b"][3]["mob"], color=YELLOW_M), Indicate(self.rows["b"][4]["mob"], color=YELLOW_M)], 0.8),
            "the exclamation",
            (lambda: [Indicate(self.rows["a"][6]["mob"], color=YELLOW_M), Indicate(self.rows["a"][7]["mob"], color=YELLOW_M)], 0.8),
        ])
        self.steps("Nobody had to be in charge. Each edit carries the name it hangs on.", [
            (lambda: [Create(ticks[0]), Create(ticks[1]), *self.cap("ids now: 1a 2a 3a 4a 7a 5a 6a 7b, on both sites", WHITE)], 0.7),
            "Each edit carries",
            (lambda: self.cap("each edit carries the name it hangs on", YELLOW_M), 0.5),
        ], after=0.5)

        # ---------------- scene 6: ties, and the letter that stays ----------------
        self.steps("Two more rules. When two inserts name the same letter, the bigger id goes first, on every site.", [
            (lambda: [FadeOut(ticks), *self.cap("two inserts after the same letter: the bigger id goes first", WHITE)], 0.6),
        ])
        self.steps("And deletes. On paper you'd rub the letter out. Here that breaks.", [
            "rub the letter",
            (lambda: self.cap("on paper: rub it out", GREY_B), 0.5),
            "Here that breaks",
            (lambda: self.cap("here, that breaks", RED_M), 0.4),
        ])
        da = mchip("delete 6a", BLUE_M)
        db = mchip("'5' 8b after 6a", TEAL_M)
        self.steps("Say a deletes the 0, while b types a 5 right after it, named 8b.", [
            (lambda: [*self.drop("cap"), *self.kill("a", "6a")], 0.6),
            (lambda: [FadeIn(da.move_to([-1.6, BAND_Y + 0.15, 0]))], 0.3),
            "while b types",
            *self.ins_steps("b", 7, "5", "8b"),
            (lambda: [FadeIn(db.move_to([2.6, BAND_Y - 0.25, 0]))], 0.3),
            "named 8b",
            (lambda: self.cap("after 6a there's already 7b; 8b is bigger, so it goes first", WHITE), 0.5),
        ])
        self.steps("b's note says after 6a. If 6a were gone, b's 5 would have nowhere to go.", [
            "If 6a were gone",
            (lambda: [*self.cap("rubbed out, 6a is gone: after what?", RED_M), self.rows["a"][6]["mob"].animate.set_opacity(0.1)], 0.6),
            (lambda: [self.rows["a"][6]["mob"].animate.set_opacity(1)], 0.4),
            (lambda: [self.rows["a"][6]["mob"][1].animate.set_opacity(0.3)], 0.2),
        ])
        self.steps("So a delete only marks its letter as gone, and keeps the name. That mark is called a tombstone.", [
            "marks its letter",
            (lambda: [*self.cap("a delete marks the letter, and keeps its name: a tombstone", YELLOW_M)], 0.6),
            (lambda: [Indicate(self.rows["a"][6]["mob"], color=GREY_B)], 0.7),
        ])
        self.steps("The letter is dead, but it still gets mail. Both sites end with pay $45!.", [
            (lambda: [da.animate.move_to([-1.6, BAND_Y - 0.25, 0]), db.animate.move_to([2.6, BAND_Y + 0.15, 0])], 0.6),
            (lambda: [FadeOut(da), FadeOut(db)], 0.2),
            *self.ins_steps("a", 7, "5", "8b", TEAL_M, 0.4),
            (lambda: self.kill("b", "6a"), 0.5),
            "Both sites end",
            (lambda: [*self.cap("both: pay $45!, with the 0 kept as a tombstone", WHITE)], 0.5),
        ], after=0.5)

        # ---------------- scene 7: what it costs, and what it promises ----------------
        veil = Rectangle(width=16, height=9, stroke_width=0).set_fill(BLACK, 0.95).set_z_index(8)
        lines = VGroup(
            T("10,000 random edits", 28, WHITE),
            T("2,136 letters you can see      6,068 kept      3,932 tombstones", 26, GREY_B),
            T("17 bytes of names and marks per visible letter   (plain text: 0)", 26, RED_M),
            T("Automerge 2: 700 MB for one long novel      Automerge 3: 1.3 MB", 26, GOLD_M),
        ).arrange(DOWN, buff=0.4).move_to([0, 0.5, 0])
        for m in lines.get_family():
            m.set_z_index(9)
        self.steps("The price is extra data, and it only grows. In the lesson's test, 10,000 random edits leave 2,136 letters you can see, "
                   "and 6,068 kept, one for every letter ever typed.", [
            (lambda: [*self.drop("cap"), FadeIn(veil), FadeIn(lines[0])], 0.7),
            "2,136",
            (lambda: [FadeIn(lines[1])], 0.6),
        ])
        self.steps("That's 17 bytes of names and marks for each visible letter. A plain string needs none.", [
            (lambda: [FadeIn(lines[2])], 0.6),
        ])
        self.steps("Real libraries carry more: in Automerge 2, a CRDT library, pasting a long novel took 700 MB of memory. "
                   "Automerge 3 takes 1.3 MB for the same paste.", [
            "in Automerge 2",
            (lambda: [FadeIn(lines[3])], 0.6),
        ], after=0.4)
        twice = VGroup(T("both add the missing 0:", 24, GREY_B), M("pay 4  ->  pay 400", 26, RED_M)).arrange(RIGHT, buff=0.4)
        twice.move_to([0, -2.1, 0]).set_z_index(9)
        self.steps("And one more limit. A CRDT promises that the copies agree, not that the result is what anyone meant.", [
            (lambda: [*self.cap("the copies agree; that's not the same as right", YELLOW_M)], 0.6),
        ])
        self.lab["cap"].set_z_index(9)
        self.steps("Two agents who fix the same typo at once can end up with the fix typed twice. Agreed, and wrong together.", [
            "the fix typed twice",
            (lambda: [FadeIn(twice)], 0.6),
        ], after=0.4)

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, how do two copies merge with no one in charge? Name every letter when it's typed.", [
            (lambda: [FadeOut(veil), FadeOut(lines), FadeOut(twice), *self.cap("name every letter when it's typed", WHITE)], 0.7),
        ])
        self.steps("Insert after a name, never at a position. Keep the names, even of deleted letters.", [
            (lambda: self.cap("insert after a name, never at a position", WHITE), 0.5),
            "Keep the names",
            (lambda: [*self.cap("keep the names, even of deleted letters", WHITE), Indicate(self.rows["b"][6]["mob"], color=GREY_B)], 0.6),
        ], after=0.4)
        q = mchip("'x' 9a after 8a", BLUE_M).move_to([3.4, BAND_Y, 0])
        miss = VGroup(DashedVMobject(RoundedRectangle(corner_radius=0.08, width=TS, height=TS, stroke_color=RED_M, stroke_width=2), num_dashes=24),
                      M("8a?", 18, RED_M)).move_to([5.5, ROW_Y["b"], 0])
        self.steps("One quick check. Site b receives: insert x, named 9a, after 8a. But b has never seen 8a. "
                   "Should it apply the insert now? Pause and think.", [
            (lambda: self.drop("cap"), 0.3),
            "Site b receives",
            (lambda: [FadeIn(q, shift=0.2 * DOWN)], 0.5),
            "never seen 8a",
            (lambda: [FadeIn(miss)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. It waits until 8a arrives. An edit can only hang on a name the site already has.", [
            (lambda: [*self.cap("wait until 8a arrives", YELLOW_M, 30), q.animate.set_stroke(YELLOW_M)], 0.6),
            "An edit can only",
            (lambda: self.cap("an edit can only hang on a name the site already has", YELLOW_M), 0.6),
        ], after=0.3)
        self.wait(2.0)
