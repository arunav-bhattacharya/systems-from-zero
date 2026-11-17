from sfz import *

SAY.insert(0, (r"\bauth:(\d+)'s\b", lambda m: f"auth {m.group(1)}'s"))
SAY.insert(0, (r"\bauth:(\d+)\b", lambda m: f"auth {m.group(1)}"))
SAY.insert(0, (r"\b(CAPTURED|PENDING|CAPTING)\b", lambda m: m.group(1).lower()))
SAY.insert(0, (r"\bkeydir\b", "key durr"))
SAY.insert(0, (r"\bBitcask('s)?\b", lambda m: "bit cask" + (m.group(1) or "")))
SAY.insert(0, (r"\bRiak\b", "ree ack"))
SAY.insert(0, (r"\bBasho\b", "bah show"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TITLE_Y = 2.95
NB_X0, NB_X1, NB_TOP, NB_BOT = -6.4, 0.45, 2.55, -1.62    # the notebook: data.log on the drive
NB_CX = (NB_X0 + NB_X1) / 2
MARGIN_X = -5.45                                          # the notebook's red margin line
OFF_X = -5.92                                             # byte offsets, in the margin
ROWS = [2.02, 1.22, 0.42, -0.38, -1.18]                   # y of each record (line)
RH = 0.56
RX0 = -5.25                                               # a record's left edge
HW, KW, VW = 1.0, 1.4, 2.15                               # header, key and value cells
SX0, SX1, STOP, SBOT = 1.75, 6.35, 2.55, 0.3              # the slip (later: the keydir)
SCX = (SX0 + SX1) / 2
SLIP_Y = [1.85, 1.05]                                     # its lines: auth:1, auth:2
REQ_Y, RES_Y = -0.45, -1.15                               # the request chip and its result
STAT_Y = [-2.12, -2.6]
CAP_Y = -3.25

OFFS = [0, 33, 66, 100, 134]
RECS = [("auth:1", "PENDING"), ("auth:2", "PENDING"), ("auth:1", "CAPTURED"), ("auth:2", "CAPTURED"), ("auth:1", None)]


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
        if t > dur + 0.1:
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, c=(0, -2.6), secs=3.0):
        bar = Line([c[0] - 1.0, c[1], 0], [c[0] + 1.0, c[1], 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def notebook():
    page = Rectangle(width=NB_X1 - NB_X0, height=NB_TOP - NB_BOT, stroke_color=GREY_B, stroke_width=2.5)
    page.set_fill(fillc(GREY_B, 0.06), 1).move_to([NB_CX, (NB_TOP + NB_BOT) / 2, 0]).set_z_index(-2)
    rules = VGroup(*[Line([MARGIN_X, y - 0.4, 0], [NB_X1, y - 0.4, 0], stroke_width=1.2, color=GREY_D) for y in ROWS[:-1]])
    margin = Line([MARGIN_X, NB_TOP, 0], [MARGIN_X, NB_BOT, 0], stroke_width=2, color=RED_M).set_opacity(0.55)
    return page, rules.set_z_index(-1), margin.set_z_index(-1)


class Rec(VGroup):
    """One record on one line of the notebook: header, key and value cells, with its byte offset in the margin."""

    def __init__(self, i):
        super().__init__()
        key, val = RECS[i]
        y = ROWS[i]
        color = PURPLE_M if val is None else BLUE_M
        self.hdr = Rectangle(width=HW, height=RH, stroke_color=GREY_B, stroke_width=2.5).set_fill(fillc(GREY_B, 0.12), 1)
        self.key = Rectangle(width=KW, height=RH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
        self.val = Rectangle(width=VW, height=RH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.08 if val is None else 0.14), 1)
        left_at(self.hdr, RX0, y)
        left_at(self.key, RX0 + HW, y)
        left_at(self.val, RX0 + HW + KW, y)
        self.ht = M("hdr", 18, GREY_B).move_to(self.hdr)
        self.kt = M(key, 20).move_to(self.key)
        self.vt = (T("no value", 20, GREY_B) if val is None else M(val, 20)).move_to(self.val)
        self.add(self.hdr, self.key, self.val, self.ht, self.kt, self.vt)
        self.off = M(str(OFFS[i]), 20, GREY_B).move_to([OFF_X, y, 0])

    def die(self):
        return [self.key.animate.set_stroke(GREY_D).set_fill(fillc(GREY_D, 0.2), 1),
                self.val.animate.set_stroke(GREY_D).set_fill(fillc(GREY_D, 0.2), 1),
                self.hdr.animate.set_stroke(GREY_D),
                self.kt.animate.set_color(GREY_D), self.vt.animate.set_color(GREY_D), self.ht.animate.set_color(GREY_D)]


def slip():
    r = Rectangle(width=SX1 - SX0, height=STOP - SBOT, stroke_color=TEAL_M, stroke_width=3).set_fill(fillc(TEAL_M, 0.08), 1)
    return r.move_to([SCX, (STOP + SBOT) / 2, 0]).set_z_index(-1)


def sline(k, s, color=WHITE):
    a = left_at(M(["auth:1", "auth:2"][k], 20, color), SX0 + 0.2, SLIP_Y[k])
    b = left_at(T(s, 23, color), SX0 + 1.38, SLIP_Y[k])
    return VGroup(a, b)


def req(s, color=GOLD_M):
    return chip(s, color, 22, mono=True).move_to([SCX, REQ_Y, 0])


def res(s, color=WHITE, size=22):
    return fit(T(s, size, color), SX1 - SX0 + 0.2).move_to([SCX, RES_Y, 0])


def stat(s, k, color=WHITE, size=24):
    return fit(T(s, size, color), 12.6).move_to([0, STAT_Y[k], 0])


# ---- the byte strip for "write over it" (scene 3) ----
CW, CH = 0.29, 0.46
STRIP_Y = 0.95


def strip(spot, a_text, b_text, x0=1.6):
    """Two fixed spots side by side, one cell per byte. Returns (cells, letters, labels, spans)."""
    cells, letters = VGroup(), VGroup()
    spans = []
    x = x0
    for s, txt in enumerate((a_text, b_text)):
        start = x
        for j in range(spot):
            c = Rectangle(width=CW, height=CH, stroke_color=BLUE_M, stroke_width=2).set_fill(fillc(BLUE_M, 0.12 if j < len(txt) else 0.0), 1)
            left_at(c, x, STRIP_Y)
            cells.add(c)
            ch = txt[j] if j < len(txt) else ""
            letters.add(M(ch or " ", 20, WHITE if ch else GREY_D).move_to(c))
            x += CW
        spans.append((start, x))
        x += 0.14
    labels = VGroup(*[M(f"auth:{s + 1}'s spot", 18, GREY_B).move_to([(a + b) / 2, STRIP_Y + 0.55, 0]) for s, (a, b) in enumerate(spans)])
    return cells, letters, labels, spans




def row_mark(i):
    """The scan's place: a yellow outline around one line of the notebook."""
    r = Rectangle(width=NB_X1 - MARGIN_X - 0.16, height=0.66, stroke_color=YELLOW_M, stroke_width=3.5)
    return r.move_to([(MARGIN_X + NB_X1) / 2, ROWS[i], 0])


class LogStore(Base):
    """store-01, section 1. The store appends every record to one file. A scan finds auth:1 but reads all 100 bytes
    (40 MB for a million records). Writing over a fixed spot breaks twice: CAPTURED doesn't fit where PENDING was, and a
    power cut leaves CAPTING. The café notebook in pen with a slip at the front: the slip points at each key's newest
    value (auth:2 at 59, auth:1 at 92). A get is one lookup and one read of 8 bytes; a missing key costs no read. An
    update appends (auth:2 at 100, value at 126); a delete appends a tombstone (134). Names (append-only log, keydir,
    Bitcask), the slip lives in RAM, two limits, the moral, and a check: rebuild the slip after a crash."""

    def construct(self):
        self.capm = None
        self.title_card("Find one payment without reading the file", "an append-only log and a map in memory")

        # ---------------- scene 1: the file, and the question ----------------
        page, rules, margin = notebook()
        t_nb = T("data.log, on the drive", 24, GREY_B).move_to([NB_CX, TITLE_Y, 0])
        R = [Rec(i) for i in range(5)]

        def drop(i):
            return [FadeIn(R[i], shift=0.25 * DOWN), FadeIn(R[i].off)]

        self.steps("Our store keeps every payment in one file, and it only ever adds to the end. "
                   "Payment 1 arrives, PENDING, still waiting for the bank. Then payment 2. "
                   "Then the money for payment 1 really moves, and its new status, CAPTURED, goes at the end too.", [
            (lambda: [FadeIn(page), Create(rules), Create(margin), FadeIn(t_nb)], 1.0),
            "Payment 1 arrives",
            (lambda: drop(0), 0.6),
            "Then payment 2",
            (lambda: drop(1), 0.6),
            "its new status",
            (lambda: drop(2), 0.6),
            (lambda: [glow(R[2].val, YELLOW_M, 1.04)], 0.6),
        ])
        self.steps("Each line is one record, and auth:1 is its key, the name we look it up by. "
                   "The numbers on the left are byte offsets: where each record begins, counted in bytes from the start of the file.", [
            (lambda: [glow(R[0].key, BLUE_M, 1.06), glow(R[2].key, BLUE_M, 1.06)], 0.8),
            "The numbers on the left",
            (lambda: [LaggedStart(*[Indicate(R[i].off, color=YELLOW_M, scale_factor=1.4) for i in range(3)], lag_ratio=0.3),
                      *self.cap("byte offset: where a record begins, in bytes from the start of the file")], 1.2),
        ])
        q = req("get(auth:1)")
        self.steps("Now the card reader asks: what's the status of auth:1?", [
            (lambda: [*self.uncap(), FadeIn(q, shift=0.1 * UP)], 0.6),
            (lambda: [glow(q[0], GOLD_M, 1.06)], 0.6),
        ], after=0.4)

        # ---------------- scene 2: the scan ----------------
        mk = row_mark(0)
        r_scan = res("CAPTURED, after reading all 100 bytes", GOLD_M)
        self.steps("The simplest answer is a scan. Read from the start, and keep the last value you see for that key. "
                   "PENDING at byte 0, then CAPTURED at byte 66. The last one wins. That cost all 100 bytes of the file.", [
            (lambda: self.cap("a scan: read from the start, keep the last value for the key"), 0.5),
            "PENDING at byte 0",
            (lambda: [Create(mk), R[0].vt.animate.set_color(GOLD_M)], 0.4),
            (lambda: [mk.animate.move_to([mk.get_center()[0], ROWS[1], 0])], 0.45),
            "then CAPTURED",
            (lambda: [mk.animate.move_to([mk.get_center()[0], ROWS[2], 0])], 0.45),
            (lambda: [R[2].vt.animate.set_color(GOLD_M), R[0].vt.animate.set_color(WHITE)], 0.3),
            "The last one wins",
            (lambda: [glow(R[2].val, GOLD_M, 1.04)], 0.5),
            "That cost",
            (lambda: [FadeOut(mk), FadeIn(r_scan, shift=0.1 * UP)], 0.5),
        ])
        s1 = stat("1 million records of about 40 bytes: 40 MB read per lookup", 0)
        s2 = stat("and it grows with every payment", 1, RED_M)
        self.steps("With a million records of about 40 bytes, every lookup reads 40 megabytes, and it grows with every payment. "
                   "That's rereading the shop's whole history to answer one question.", [
            (lambda: [*self.uncap(), FadeIn(s1, shift=0.1 * UP)], 0.6),
            "and it grows",
            (lambda: [FadeIn(s2, shift=0.1 * UP)], 0.6),
            "That's rereading",
            (lambda: [LaggedStart(*[glow(R[i].val, RED_M, 1.03) for i in range(3)], lag_ratio=0.25)], 1.0),
        ])
        self.steps("We want to jump straight to auth:1's newest value, and read only that.", [
            (lambda: [FadeOut(s1), FadeOut(s2), R[2].vt.animate.set_color(WHITE), FadeOut(r_scan)], 0.5),
            (lambda: [*self.cap("the wish: jump straight to auth:1's newest value, read only that", YELLOW_M), glow(R[2].val, YELLOW_M, 1.04)], 0.7),
        ], after=0.4)

        # ---------------- scene 3: the obvious fix, broken ----------------
        nb_all = VGroup(page, rules, t_nb, *R[:3], *[r.off for r in R[:3]])
        c7, l7, lab7, sp7 = strip(7, "PENDING", "PENDING")
        self.steps("The obvious idea: give each key a fixed spot, and write over it. Nothing old, nothing to scan.", [
            (lambda: [FadeOut(q), nb_all.animate.set_opacity(0.25), margin.animate.set_opacity(0.15),
                      *self.cap("the obvious fix: one fixed spot per key, write over it")], 0.8),
            "a fixed spot",
            (lambda: [FadeIn(c7), FadeIn(l7), FadeIn(lab7)], 0.9),
        ])
        newl = VGroup()

        def type_over(cells, letters, word, n, color=YELLOW_M):
            seq = []
            for j in range(n):
                def f(j=j):
                    m = M(word[j], 20, color).move_to(cells[j])
                    newl.add(m)
                    return [FadeOut(letters[j]), FadeIn(m), cells[j].animate.set_stroke(color)]
                seq.append((f, 0.16))
            return seq

        c8, l8, lab8, sp8 = strip(8, "PENDING", "PENDING")
        self.steps("Let's be fair and try it. auth:1's spot holds PENDING, 7 bytes. CAPTURED is 8, so its last byte lands on auth:2's spot. "
                   "Make the spots bigger, and every short value wastes room.", [
            "auth:1's spot holds",
            (lambda: [LaggedStart(*[Indicate(l7[j], color=BLUE_M, scale_factor=1.3) for j in range(7)], lag_ratio=0.1),
                      *self.cap("write CAPTURED, 8 bytes, over PENDING, 7 bytes", WHITE)], 0.8),
            "CAPTURED is 8",
            *type_over(c7, l7, "CAPTURED", 8),
            "lands on",
            (lambda: [newl[7].animate.set_color(RED_M), c7[7].animate.set_stroke(RED_M, width=4), *self.cap("the D lands on auth:2's spot", RED_M)], 0.5),
            "Make the spots bigger",
            (lambda: [FadeOut(VGroup(c7, l7, lab7, newl)), FadeIn(c8), FadeIn(l8), FadeIn(lab8), *self.uncap()], 0.6),
            "wastes room",
            (lambda: [c8[7].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B, 0.3), 1), c8[15].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B, 0.3), 1),
                      *self.cap("8-byte spots: an empty byte after every PENDING")], 0.6),
        ])
        newl = VGroup()
        tear = M("CAPTING", 26, RED_M).move_to([(sp8[0][0] + sp8[0][1]) / 2, STRIP_Y - 0.75, 0])
        self.steps("Worse, cut the power in the middle of the write. C, A, P, T, and the lights go out. "
                   "The spot now says CAPTING: half new, half old, and no copy of either. Not a status any bank has heard of.", [
            (lambda: [*self.cap("cut the power in the middle of the write", WHITE),
                      c8[7].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M, 0.0), 1), c8[15].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M, 0.0), 1)], 0.5),
            "C, A, P, T",
            *type_over(c8, l8, "CAPTURED", 4),
            "and the lights go out",
            (lambda: [*self.cap("power cut after 4 bytes", RED_M), *[c8[j].animate.set_stroke(RED_M) for j in range(8)]], 0.5),
            "The spot now says",
            (lambda: [FadeIn(tear, shift=0.1 * DOWN)], 0.5),
            "half new",
            (lambda: [*[Indicate(newl[j], color=YELLOW_M, scale_factor=1.3) for j in range(4)], *[Indicate(l8[j], color=GREY_B, scale_factor=1.3) for j in range(4, 7)],
                      *self.cap("half new, half old, and no copy of either", RED_M)], 1.0),
        ])
        self.steps("So writing over old bytes is the risky part, and our file never does it.", [
            (lambda: [FadeOut(VGroup(c8, l8, lab8, newl, tear)), *self.uncap()], 0.6),
            "and our file",
            (lambda: [nb_all.animate.set_opacity(1), margin.animate.set_opacity(0.55)], 0.8),
            (lambda: self.cap("never touch old bytes: only add to the end", GREEN_M), 0.5),
        ], after=0.4)

        # ---------------- scene 4: the café notebook ----------------
        t_nb2 = T("data.log: the notebook", 24, GREY_B).move_to([NB_CX, TITLE_Y, 0])
        self.steps("A café's paper notebook shows the way. The owner writes each sale on the next empty line, in pen, "
                   "and never rubs anything out. A correction is a new line at the bottom.", [
            (lambda: [*self.cap("the café's notebook"), swap(t_nb, t_nb2)], 0.7),
            "on the next empty line",
            (lambda: [LaggedStart(*[glow(R[i].val, BLUE_M, 1.03) for i in range(3)], lag_ratio=0.25)], 0.9),
            "A correction",
            (lambda: [glow(R[2].val, YELLOW_M, 1.05), *self.cap("a correction: a new line at the bottom")], 0.7),
        ])
        sl = slip()
        t_sl = T("the slip", 24, TEAL_M).move_to([SCX, TITLE_Y, 0])
        self.steps("At the front, she keeps a slip of paper that says which line holds each customer's latest entry. "
                   "To look someone up, she reads the slip, then turns to one line.", [
            (lambda: [*self.uncap(), FadeIn(sl), FadeIn(t_sl)], 0.9),
            "To look someone up",
            (lambda: [glow(sl, TEAL_M, 1.02)], 0.6),
            "then turns to one line",
            (lambda: [glow(R[2].val, TEAL_M, 1.05)], 0.6),
        ])
        t_sl2 = T("the slip: a map in memory", 24, TEAL_M).move_to([SCX, TITLE_Y, 0])
        self.steps("Let's map it. The notebook is our file, and each line is a record. Where a line sits is its byte offset. "
                   "And the slip is a small map in memory, from each key to where its newest value starts.", [
            "The notebook is",
            (lambda: [glow(page, GREY_B, 1.0), *self.cap("the notebook: the file", WHITE)], 0.6),
            "each line is",
            (lambda: [glow(R[1].key, BLUE_M, 1.04), glow(R[1].val, BLUE_M, 1.04), *self.cap("a line: a record", WHITE)], 0.6),
            "Where a line sits",
            (lambda: [LaggedStart(*[Indicate(R[i].off, color=YELLOW_M, scale_factor=1.4) for i in range(3)], lag_ratio=0.2),
                      *self.cap("where a line sits: its byte offset", WHITE)], 0.8),
            "And the slip",
            (lambda: [swap(t_sl, t_sl2), *self.cap("the slip: each key, and where its newest value starts", TEAL_M)], 0.7),
        ], after=0.4)

        # ---------------- scene 5: write the slip ----------------
        e2 = sline(1, "value at 59, 7 bytes")
        self.steps("Let's write the slip. Every record starts with a 20-byte header that holds its sizes, then the key, then the value. "
                   "auth:2's record is at 33, and its key is 6 bytes. So its value starts at 33 plus 20 plus 6: byte 59. "
                   "And PENDING is 7 bytes.", [
            (lambda: self.cap("every record: a 20-byte header, then the key, then the value"), 0.5),
            "Every record starts",
            (lambda: [glow(R[1].hdr, GREY_B, 1.06)], 0.5),
            "then the key",
            (lambda: [glow(R[1].key, BLUE_M, 1.06)], 0.4),
            "then the value",
            (lambda: [glow(R[1].val, BLUE_M, 1.04)], 0.4),
            "auth:2's record",
            (lambda: [Indicate(R[1].off, color=YELLOW_M, scale_factor=1.4)], 0.6),
            "33 plus 20",
            (lambda: self.cap("33 + 20 (header) + 6 (auth:2) = 59", WHITE), 0.5),
            "byte 59",
            (lambda: [FadeIn(e2[0]), FadeIn(e2[1], shift=0.1 * LEFT)], 0.6),
            "And PENDING",
            (lambda: [Indicate(e2[1], color=TEAL_M, scale_factor=1.08)], 0.6),
        ])
        self.steps("Now auth:1 has two records. Which one should the slip point at, and at which byte? Pause and guess.", [
            (lambda: [*self.uncap(), glow(R[0].key, YELLOW_M, 1.06), glow(R[2].key, YELLOW_M, 1.06)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        e1 = sline(0, "value at 92, 8 bytes")
        self.steps("The newest, at 66. Plus 20, plus 6: byte 92, and CAPTURED is 8 bytes. "
                   "The PENDING record at 0 stays in the file, but nothing points at it now. Those are dead bytes.", [
            (lambda: [*self.uncap(), Indicate(R[2].off, color=YELLOW_M, scale_factor=1.4), glow(R[2].val, YELLOW_M, 1.04)], 0.6),
            "Plus 20",
            (lambda: self.cap("66 + 20 + 6 = 92", WHITE), 0.5),
            "byte 92",
            (lambda: [FadeIn(e1[0]), FadeIn(e1[1], shift=0.1 * LEFT)], 0.6),
            "The PENDING record",
            (lambda: [glow(R[0].val, GREY_B, 1.04)], 0.5),
            "nothing points",
            (lambda: R[0].die(), 0.6),
            "Those are dead",
            (lambda: self.cap("dead bytes: still in the file, but nothing points at them", GREY_B), 0.5),
        ], after=0.4)

        # ---------------- scene 6: one lookup, one read ----------------
        q = req("get(auth:1)")

        def point(k, i, color=GOLD_M):
            return Arrow([SX0 - 0.05, SLIP_Y[k], 0], [R[i].val.get_right()[0] + 0.05, ROWS[i], 0], buff=0, stroke_width=3,
                         color=color, max_tip_length_to_length_ratio=0.1)

        ar = point(0, 2)
        r1 = res("read 8 bytes at 92: CAPTURED", GOLD_M)
        self.steps("Now ask again: get auth:1. The slip says byte 92, 8 bytes. One read of exactly those 8 bytes: "
                   "CAPTURED. Eight bytes, where the scan read the whole file.", [
            (lambda: [*self.uncap(), FadeIn(q, shift=0.1 * UP)], 0.5),
            "The slip says",
            (lambda: [e1.animate.set_color(GOLD_M)], 0.4),
            (lambda: [GrowArrow(ar)], 0.6),
            "One read",
            (lambda: [glow(R[2].val, GOLD_M, 1.05), R[2].vt.animate.set_color(GOLD_M)], 0.6),
            "CAPTURED. Eight",
            (lambda: [FadeIn(r1, shift=0.1 * UP)], 0.5),
            "where the scan",
            (lambda: self.cap("8 bytes read, where the scan read all 100", WHITE), 0.5),
        ])
        r7 = res("not on the slip: no read at all", GREY_B)
        self.steps("And a key that isn't on the slip, like auth:7? No trip to the drive at all. The cheapest question there is.", [
            (lambda: [FadeOut(ar), FadeOut(r1), e1.animate.set_color(WHITE), R[2].vt.animate.set_color(WHITE), *self.uncap(),
                      Transform(q, req("get(auth:7)", GREY_B))], 0.6),
            "No trip",
            (lambda: [glow(sl, TEAL_M, 1.02), FadeIn(r7, shift=0.1 * UP)], 0.7),
            "The cheapest",
            (lambda: self.cap("a missing key: no trip to the drive", GREEN_M), 0.5),
        ], after=0.4)

        # ---------------- scene 7: changes are appends too ----------------
        e2b = sline(1, "value at 126, 8 bytes", YELLOW_M)
        self.steps("Now payment 2 is captured. The store adds a record at the end, at 100, and moves auth:2's line on the slip "
                   "to byte 126. The record at 33 is dead too. Nothing was written over.", [
            (lambda: [FadeOut(r7), *self.uncap(), Transform(q, req("put(auth:2, CAPTURED)"))], 0.6),
            "adds a record",
            (lambda: drop(3), 0.6),
            "and moves",
            (lambda: [Transform(e2, e2b)], 0.6),
            "The record at 33",
            (lambda: [*R[1].die(), e2.animate.set_color(WHITE)], 0.6),
            "Nothing was",
            (lambda: self.cap("an update: one more record at the end", WHITE), 0.5),
        ])
        self.steps("And a delete can't rub anything out either. Deleting auth:1 adds a tombstone at 134: the key, with no value, "
                   "and a value size of minus 1. The slip drops auth:1.", [
            (lambda: [*self.uncap(), Transform(q, req("delete(auth:1)", PURPLE_M))], 0.6),
            "adds a tombstone",
            (lambda: drop(4), 0.6),
            "and a value size",
            (lambda: [glow(R[4].hdr, PURPLE_M, 1.06), *self.cap("tombstone: the key, no value, value size = -1", PURPLE_M)], 0.6),
            "The slip drops",
            (lambda: [FadeOut(e1, shift=0.1 * RIGHT), *R[2].die()], 0.7),
        ], after=0.4)

        # ---------------- scene 8: names ----------------
        t_nb3 = T("data.log: an append-only log", 24, GREY_B).move_to([NB_CX, TITLE_Y, 0])
        t_sl3 = T("keydir: a hash map in RAM", 24, TEAL_M).move_to([SCX, TITLE_Y, 0])
        self.steps("This design is Bitcask, a storage engine that the company Basho built in 2010 for its database, Riak. "
                   "A file you only add to is an append-only log. And the slip is the keydir, the store's index: "
                   "a lookup table from each key to where its record lives.", [
            (lambda: [FadeOut(q), *self.cap("Bitcask: a storage engine (Basho, 2010, for Riak)", WHITE)], 0.6),
            "A file you only",
            (lambda: [swap(t_nb2, t_nb3)], 0.6),
            "And the slip is",
            (lambda: [swap(t_sl2, t_sl3), glow(sl, TEAL_M, 1.02)], 0.7),
            "the store's index",
            (lambda: self.cap("an index: a lookup table from a key to where its record lives", TEAL_M), 0.5),
        ], after=0.4)

        # ---------------- scene 9: where the picture breaks ----------------
        self.steps("Here the café picture breaks. Paper survives the night, but the keydir lives in RAM, the computer's memory, "
                   "which forgets everything when the power goes. So after a crash, the store rebuilds it by reading the whole "
                   "file from byte 0.", [
            (lambda: self.cap("where the café picture breaks", WHITE), 0.5),
            "but the keydir",
            (lambda: [glow(sl, RED_M, 1.02)], 0.7),
            "which forgets",
            (lambda: [e2.animate.set_opacity(0.15), *self.cap("RAM: gone when the power goes", RED_M)], 0.6),
            "So after a crash",
            (lambda: self.cap("after a crash: read the whole file from byte 0 to rebuild it", WHITE), 0.5),
            (lambda: [LaggedStart(*[glow(R[i].key, YELLOW_M, 1.04) for i in range(5)], lag_ratio=0.2)], 1.2),
            (lambda: [e2.animate.set_opacity(1)], 0.5),
        ], after=0.4)

        # ---------------- scene 10: two limits ----------------
        g1 = stat("1. every key in RAM: 50 million keys of 40 bytes, plus bookkeeping = several GB", 0)
        g2 = stat("2. no order: a range of keys means checking every key", 1)
        self.steps("Two hard limits. The keydir holds every key in RAM: fifty million keys of 40 bytes, plus the map's own "
                   "bookkeeping, is several gigabytes.", [
            (lambda: [*self.cap("two limits", WHITE)], 0.4),
            "The keydir holds",
            (lambda: [FadeIn(g1, shift=0.1 * UP), glow(sl, TEAL_M, 1.02)], 0.7),
        ])
        self.steps("And it's a hash map: it turns a key into a number that says where to look. That finds one key in one step, "
                   "but keeps no order. So every payment on card 4242 between 9 and 10 means checking every key. "
                   "Later lessons build indexes that keep their keys in order.", [
            (lambda: self.cap("a hash map: a key becomes a number that says where to look", TEAL_M), 0.5),
            "but keeps no order",
            (lambda: [FadeIn(g2, shift=0.1 * UP)], 0.6),
            "So every payment",
            (lambda: self.cap("every payment on card 4242 between 9 and 10? check every key", RED_M), 0.5),
            "Later lessons",
            (lambda: self.cap("B+trees and LSM trees keep keys in order (later in this track)", WHITE), 0.5),
        ], after=0.4)

        # ---------------- scene 11: the moral, and a check ----------------
        self.steps("So: write in pen, at the end, and keep a slip of where each key's newest value starts. "
                   "Every write is one append. Every read is one lookup and one read.", [
            (lambda: [FadeOut(g1), FadeOut(g2), *self.cap("write in pen, at the end; keep a slip of each key's newest value", YELLOW_M, 28)], 0.7),
            "Every write",
            (lambda: [glow(R[4].val, YELLOW_M, 1.03)], 0.6),
            "Every read",
            (lambda: [glow(sl, TEAL_M, 1.02)], 0.6),
        ], after=0.5)
        self.steps("One quick check. The power goes out and the slip is gone. The store reads the file from byte 0 to rebuild it. "
                   "What's on the slip at the end? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "the slip is gone",
            (lambda: [FadeOut(e2)], 0.6),
            "The store reads",
            (lambda: [*[R[i].kt.animate.set_color(WHITE) for i in range(4)], *[R[i].vt.animate.set_color(WHITE) for i in range(4)],
                      *[R[i].key.animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1) for i in range(3)],
                      *[R[i].val.animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1) for i in range(3)],
                      *[R[i].hdr.animate.set_stroke(GREY_B) for i in range(3)], *[R[i].ht.animate.set_color(GREY_B) for i in range(3)]], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown()
        mk = row_mark(0)
        a1 = sline(0, "value at 26, 7 bytes")
        a2 = sline(1, "value at 59, 7 bytes")
        b1 = sline(0, "value at 92, 8 bytes")
        b2 = sline(1, "value at 126, 8 bytes", YELLOW_M)
        cx = mk.get_center()[0]
        self.steps("Only auth:2, with its value at 126, 8 bytes. The tombstone came last, so auth:1 stays off the slip.", [
            (lambda: [*self.uncap(), Create(mk), FadeIn(a1)], 0.45),
            (lambda: [mk.animate.move_to([cx, ROWS[1], 0]), FadeIn(a2)], 0.45),
            (lambda: [mk.animate.move_to([cx, ROWS[2], 0]), Transform(a1, b1), *R[0].die()], 0.45),
            (lambda: [mk.animate.move_to([cx, ROWS[3], 0]), Transform(a2, b2), *R[1].die()], 0.45),
            (lambda: [mk.animate.move_to([cx, ROWS[4], 0]), FadeOut(a1, shift=0.1 * RIGHT), *R[2].die()], 0.5),
            "The tombstone",
            (lambda: [FadeOut(mk), glow(R[4].val, PURPLE_M, 1.03)], 0.6),
            "stays off",
            (lambda: [Indicate(a2[1], color=YELLOW_M, scale_factor=1.08)], 0.6),
        ], after=0.3)
        self.play(*self.cap("write in pen, at the end; keep a slip of each key's newest value", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
