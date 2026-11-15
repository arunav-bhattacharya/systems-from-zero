from sfz import *

SAY.insert(0, (r"\bauth:90(\d\d)\b", lambda m: "auth ninety oh " + "zero one two three four five six seven eight nine".split()[int(m.group(1)[1])]))
SAY.insert(0, (r"\b(CAPTURED|PENDING|AUTHORIZED|REFUNDED)\b", lambda m: m.group(1).lower()))
SAY.insert(0, (r"\bkeydir\b", "key durr"))   # "key dir" comes out as "key dire"
SAY.insert(0, (r"\bBitcask\b", "bit cask"))
SAY.insert(0, (r"\bRiak\b", "ree ack"))

X0, RW, RH, GAP = -4.3, 1.65, 0.8, 0.12      # records: left edge of the first, width, height, gap
ROW = {"a": 2.6, "b": 1.15, "c": -0.3}        # y of each file row
KX, KY, KW, KH = -3.9, -2.25, 4.6, 2.1        # the keydir box
KROW = [-2.0, -2.45, -2.9]                    # y of keydir entries
PX = 2.7                                      # centre of the request panel


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def flow(a, b, color=YELLOW_M, run_time=0.8):
    """A dot that runs from point a to point b and stays invisible until its turn."""
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def slot(i, row):
    return np.array([X0 + RW / 2 + i * (RW + GAP), ROW[row], 0])


def rec(key, val, i, row, color=BLUE_M):
    c = slot(i, row)
    r = RoundedRectangle(corner_radius=0.1, width=RW, height=RH, stroke_color=color, stroke_width=3).set_fill(fill(color), 1)
    r.move_to(c)
    k = M(key, 16, WHITE).move_to(c + 0.17 * UP)
    v = M(val, 16, WHITE).move_to(c + 0.17 * DOWN)
    return VGroup(r, k, v)


def off(n, i, row, color=GREY_B):
    return T(str(n), 18, color).move_to(slot(i, row) + (RH / 2 + 0.2) * UP)


def dead(r):
    return [r[0].animate.set_stroke(GREY_D, width=2).set_fill(fill(GREY_D, 0.2), 1), r[1].animate.set_color(GREY_D),
            r[2].animate.set_color(GREY_D)]


def row_label(s, row, sub=None, color=GREY_B):
    t = T(s, 20, color)
    t.move_to([X0 - 0.2 - t.width / 2, ROW[row] + (0.13 if sub else 0), 0])
    if not sub:
        return VGroup(t)
    u = T(sub, 17, GREY_C)
    u.move_to([X0 - 0.2 - u.width / 2, ROW[row] - 0.2, 0])
    return VGroup(t, u)


def kkey(s, k, color=WHITE):
    t = M(s, 18, color)
    return t.move_to([KX - KW / 2 + 0.3 + t.width / 2, KROW[k], 0])


def kloc(s, k, color=GREY_A):
    t = T("→ " + s, 20, color)
    return t.move_to([KX - 0.35 + t.width / 2, KROW[k], 0])


def req(s, color=GREY_B):
    return chip(s, color, 18, mono=True).move_to([PX, -1.6, 0])


def note(s, k=0, color=GREY_B):
    return T(s, 20, color).move_to([PX, -2.35 - 0.5 * k, 0])


class LogStore(Base):
    """store-01, section 1 (with section 3's merge): every put appends a record to one file; the keydir, a hash map in RAM,
    keeps the byte offset of each key's newest record, so a get is one lookup and one read. Overwrites leave dead records
    (the lab: 36 KB of file for 370 bytes live); closed segments are merged, keeping only the records the keydir points to."""

    def construct(self):
        self.title_card("A log-structured store", "append every write, index the newest in memory")

        lab = row_label("data.log", "a", "on disk")
        r = [rec("auth:9001", "AUTHORIZED", 0, "a"), rec("auth:9002", "PENDING", 1, "a")]
        o = [off(0, 0, "a"), off(39, 1, "a")]
        q = req("put auth:9001 AUTHORIZED")

        def put(i, row, r_, o_, q_):
            return [
                (lambda: [Transform(q, q_) if q in self.mobjects else FadeIn(q)], 0.5),
                (lambda: [flow(q.get_top(), slot(i, row) + (RH / 2) * DOWN, YELLOW_M, 0.6)], 0.6),
                (lambda: [FadeIn(r_, scale=0.9), FadeIn(o_)], 0.5),
                (lambda: [glow(r_[0])], 0.5),
            ]

        self.steps("A payment service stores each card authorization as a key and a status. "
                   "The cheapest way to write is to append every change to the end of one file.", [
            (lambda: [FadeIn(lab)], 0.6),
            "The cheapest",
            *put(0, "a", r[0], o[0], q),
            *put(1, "a", r[1], o[1], req("put auth:9002 PENDING")),
        ])

        r.append(rec("auth:9001", "CAPTURED", 2, "a"))
        o.append(off(75, 2, "a"))
        self.steps("When auth:9001 is captured, its new record goes at the end too. "
                   "So which record should a read of auth:9001 trust?", [
            *put(2, "a", r[2], o[2], req("put auth:9001 CAPTURED")),
            "So which",
            (lambda: [Transform(q, req("get auth:9001", GOLD_M)), r[0][1].animate.set_color(GOLD_M), r[2][1].animate.set_color(GOLD_M)], 0.7),
        ])

        head = Line(slot(0, "a") + [-RW / 2 - 0.06, -0.55, 0], slot(0, "a") + [-RW / 2 - 0.06, 0.55, 0], stroke_width=4, color=GOLD_M)
        n1 = note("scan: read every byte, keep the last match", 0)
        n2 = note("found CAPTURED after 112 bytes", 1, GOLD_M)
        self.steps("With only the file, you scan it from the start and keep the last match you see.", [
            (lambda: [FadeIn(head), FadeIn(n1)], 0.5),
            (lambda: [head.animate(rate_func=linear).shift((3 * RW + 3 * GAP) * RIGHT)], 2.2),
            (lambda: [FadeIn(n2), glow(r[2][0], GOLD_M)], 0.6),
        ])

        n3 = note("1 million records: 40 MB read per get", 0, RED_M)
        n4 = note("and it grows with every write", 1, RED_M)
        self.steps("With a million records, every lookup reads 40 megabytes, and it gets slower with each write.", [
            (lambda: [FadeOut(head), FadeOut(n1), FadeOut(n2), FadeIn(n3)], 0.7),
            "and it gets",
            (lambda: [FadeIn(n4)], 0.6),
        ])

        kbox = RoundedRectangle(corner_radius=0.14, width=KW, height=KH, stroke_color=TEAL_M, stroke_width=3).set_fill(fill(TEAL_M, 0.1), 1)
        kbox.move_to([KX, KY, 0])
        ktitle = T("keydir: a hash map in RAM", 20, TEAL_M).move_to([KX, KY + KH / 2 - 0.3, 0])
        kk = [kkey("auth:9001", 0), kkey("auth:9002", 1), kkey("auth:9003", 2)]
        kl = [kloc("byte 75", 0), kloc("byte 39", 1), None]
        self.steps("Bitcask, the engine built for the Riak database, adds a hash map in memory called the keydir. "
                   "For each key, it holds the byte offset of that key's newest record.", [
            (lambda: [FadeOut(n3), FadeOut(n4), FadeOut(q), r[0][1].animate.set_color(WHITE), r[2][1].animate.set_color(WHITE)], 0.5),
            (lambda: [FadeIn(kbox), FadeIn(ktitle)], 0.8),
            "For each key",
            (lambda: [FadeIn(kk[0]), FadeIn(kl[0]), o[2].animate.set_color(TEAL_M)], 0.6),
            (lambda: [FadeIn(kk[1]), FadeIn(kl[1]), o[1].animate.set_color(TEAL_M)], 0.6),
            "newest record",
            (lambda: [*dead(r[0]), o[0].animate.set_color(GREY_D)], 0.7),
        ])

        q = req("get auth:9001", GOLD_M)
        g1 = note("1 lookup, then 37 bytes read at 75", 0, GOLD_M)
        g2 = note("auth:9999: not in the map, 0 bytes read", 1)
        self.steps("A get is one lookup in the map, then one read of exactly those bytes: 37 bytes at offset 75. "
                   "A key that isn't in the map costs no disk read at all.", [
            (lambda: [FadeIn(q)], 0.5),
            (lambda: [flow(q.get_left(), kl[0].get_right() + 0.1 * RIGHT, GOLD_M, 0.5), kk[0].animate.set_color(GOLD_M)], 0.6),
            (lambda: [flow(kl[0].get_right() + 0.15 * RIGHT, r[2].get_bottom(), GOLD_M, 0.7)], 0.7),
            (lambda: [glow(r[2][0], GOLD_M), FadeIn(g1)], 0.6),
            "A key that",
            (lambda: [Transform(q, req("get auth:9999", GREY_B)), kk[0].animate.set_color(WHITE), FadeIn(g2)], 0.7),
        ])

        r.append(rec("auth:9002", "AUTHORIZED", 3, "a"))
        o.append(off(112, 3, "a", TEAL_M))
        self.steps("A put appends the record, then moves that key's entry to it. "
                   "The old record is dead now: nothing points at it.", [
            (lambda: [FadeOut(g1), FadeOut(g2)], 0.3),
            *put(3, "a", r[3], o[3], req("put auth:9002 AUTHORIZED")),
            (lambda: [Transform(kl[1], kloc("byte 112", 1, YELLOW_M))], 0.6),
            "The old record",
            (lambda: [*dead(r[1]), o[1].animate.set_color(GREY_D), kl[1].animate.set_color(GREY_A)], 0.7),
        ])

        r += [rec("auth:9003", "PENDING", 4, "a"), rec("auth:9002", "CAPTURED", 5, "a")]
        o += [off(151, 4, "a", TEAL_M), off(187, 5, "a", TEAL_M)]
        kl[2] = kloc("byte 151", 2)
        cnt = note("6 records, 3 live", 0)
        self.steps("Every update leaves one more dead record behind.", [
            (lambda: [FadeIn(r[4], scale=0.9), FadeIn(o[4]), FadeIn(kk[2]), FadeIn(kl[2]), Transform(q, req("put auth:9003 PENDING"))], 0.6),
            (lambda: [FadeIn(r[5], scale=0.9), FadeIn(o[5]), Transform(kl[1], kloc("byte 187", 1)),
                      Transform(q, req("put auth:9002 CAPTURED"))], 0.6),
            (lambda: [*dead(r[3]), o[3].animate.set_color(GREY_D), FadeIn(cnt)], 0.6),
        ])

        l1 = note("lab: 1,000 records, 36 KB of file", 0, RED_M)
        l2 = note("live data: 370 bytes", 1, GREEN_M)
        self.steps("In the lab, ten card balances updated a hundred times each leave a thousand records: "
                   "36 kilobytes of file for 370 bytes of live data.", [
            (lambda: [FadeOut(q), Transform(cnt, l1)], 0.7),
            "for 370",
            (lambda: [FadeIn(l2)], 0.6),
        ])

        lab1 = row_label("segment 1", "a", "closed")
        lab2 = row_label("segment 2", "b", "active", BLUE_M)
        cap = DashedLine(slot(5, "a") + [RW / 2 + 0.08, -0.5, 0], slot(5, "a") + [RW / 2 + 0.08, 0.5, 0], dash_length=0.07,
                         stroke_width=3, color=RED_M)
        self.steps("So the log is cut into segments. When the active segment reaches its size limit, it's closed and never "
                   "changes again, and new writes go to a fresh one.", [
            (lambda: [FadeOut(cnt), FadeOut(l2), Transform(lab, lab1)], 0.7),
            "When the active",
            (lambda: [Create(cap)], 0.6),
            "and new writes",
            (lambda: [FadeIn(lab2)], 0.7),
        ])

        s2 = [rec("auth:9003", "AUTHORIZED", 0, "b"), rec("auth:9001", "REFUNDED", 1, "b")]
        o2 = [off(0, 0, "b", TEAL_M), off(39, 1, "b", TEAL_M)]
        self.steps("Then auth:9003 is authorized and auth:9001 is refunded. "
                   "Their older records in segment 1 are dead.", [
            (lambda: [FadeIn(s2[0], scale=0.9), FadeIn(o2[0]), Transform(kl[2], kloc("seg 2, byte 0", 2, YELLOW_M)),
                      Transform(kl[1], kloc("seg 1, byte 187", 1))], 0.7),
            (lambda: [FadeIn(s2[1], scale=0.9), FadeIn(o2[1]), Transform(kl[0], kloc("seg 2, byte 39", 0, YELLOW_M))], 0.7),
            "Their older",
            (lambda: [*dead(r[4]), *dead(r[2]), o[4].animate.set_color(GREY_D), o[2].animate.set_color(GREY_D),
                      kl[0].animate.set_color(GREY_A), kl[2].animate.set_color(GREY_A)], 0.8),
        ])

        lab3 = row_label("merged", "c", "new file", GREEN_M)
        m0 = rec("auth:9002", "CAPTURED", 0, "c", GREEN_M)
        mo = off(0, 0, "c", TEAL_M)
        ghost = r[5].copy()
        self.steps("A merge runs in the background over the closed segments. "
                   "It copies only the records the keydir still points to into a new file.", [
            (lambda: [glow(r[5][0], GREEN_M)], 0.9),
            "It copies",
            (lambda: [FadeIn(lab3)], 0.5),
            (lambda: [ghost.animate.move_to(m0)], 1.2),
            (lambda: [FadeIn(m0), FadeIn(mo)], 0.3),
        ])
        self.remove(ghost)

        seg1 = VGroup(*r, *o, lab, cap)
        self.steps("The keydir switches to the new copy, and segment 1 is deleted. Six records became one.", [
            (lambda: [Transform(kl[1], kloc("merged, byte 0", 1, GREEN_M))], 0.7),
            "and segment 1",
            (lambda: [FadeOut(seg1, shift=0.2 * UP)], 0.8),
            (lambda: [VGroup(m0, mo, lab3).animate.shift((ROW["a"] - ROW["c"]) * UP)], 0.9),
            "Six records",
            (lambda: [FadeIn(note("6 records became 1", 0, GREEN_M))], 0.6),
        ])

        self.steps("A log store appends every write, keeps each key's newest offset in memory, "
                   "and merges the dead records away later.", [
            (lambda: [glow(s2[1][0]), glow(s2[0][0])], 0.9),
            "keeps each key's",
            (lambda: [glow(kbox, TEAL_M, 1.02)], 0.9),
            "and merges",
            (lambda: [glow(m0[0], GREEN_M)], 0.9),
        ])
        self.wait(0.6)
