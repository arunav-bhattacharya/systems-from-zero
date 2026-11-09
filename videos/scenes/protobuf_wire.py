from sfz import *

SAY.insert(0, (r"\ba0\b", "A zero"))
SAY.insert(0, (r"\b1f\b", "one F"))
# said "variant" otherwise; a varint is a "var int"
SAY.insert(0, (r"\bvarints?\b", lambda m: "var int" + ("s" if m.group(0).endswith("s") else "")))

# top: the writer's schema (left) and the bytes on the wire (right)
PANEL_TOP, PANEL_BOT = 3.45, 0.08
SCH_X0, SCH_X1 = -6.6, -1.85
WIRE_X0, WIRE_X1 = -1.5, 6.5
LINE_Y = [2.66 - 0.32 * k for k in range(8)]
DECL_X = -6.3
BX_L, BX0, BSTEP = -1.22, -0.02, 0.46
# bottom: the work area
CELL_Y, BIN_Y, L1_Y, L2_Y, SUM_Y = -0.85, -1.65, -2.28, -2.72, -3.22
CW = (M("x" * 21, 18).width - M("x", 18).width) / 20      # one monospace character at size 18

WIRE = [("field 1", "08 91 80 ed 83 b4 b4 ec d4 19"), ("field 2", "12 0b 46 65 72 6e 20 42 61 6b 65 72 79"),
        ("field 3", "18 a0 1f"), ("field 4", "22 03 45 55 52"), ("field 5", "2a 04 63 61 72 64"), ("field 5", "2a 03 33 64 73")]


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


def fillc(color):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def panel(x0, x1, title, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=PANEL_TOP - PANEL_BOT, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK, 1).move_to([(x0 + x1) / 2, (PANEL_TOP + PANEL_BOT) / 2, 0])
    return VGroup(r, left_at(T(title, 24), x0 + 0.3, PANEL_TOP - 0.36))


def sline(k, decl, num, color=WHITE):
    """One schema line: the declaration, '=', and the field number in blue (its own mobject, so it can be pointed at)."""
    y = LINE_Y[k]
    return VGroup(left_at(M(decl, 18, color), DECL_X, y), left_at(M("=", 18, GREY_B), DECL_X + 21 * CW, y),
                  left_at(M(f"{num};", 18, BLUE_M), DECL_X + 23 * CW, y))


def brow(k, label, hexes, color=WHITE):
    y = LINE_Y[k]
    bs = VGroup(*[M(h, 18, GOLD_M if j == 0 else color).move_to([BX0 + j * BSTEP, y, 0]) for j, h in enumerate(hexes.split())])
    return VGroup(left_at(T(label, 18, GREY_B), BX_L, y), bs)


def cell(h, x, color=GOLD_M):
    r = RoundedRectangle(corner_radius=0.1, width=1.0, height=0.7, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, CELL_Y, 0])
    # the label sits above the box fill, which fades in after it is added
    return VGroup(r, M(h, 30).move_to([x, CELL_Y, 0]).set_z_index(1))


def bits(parts, x):
    """Binary digits in coloured groups, centred at x on the binary row."""
    g = VGroup(*[M(s, 26, c) for s, c in parts]).arrange(RIGHT, buff=0.22)
    return g.move_to([x, BIN_Y, 0])


def lab(s, x, y, color=GREY_B, size=22, **kw):
    return T(s, size, color, **kw).move_to([x, y, 0])


def llab(s, x, y, color=GREY_B, size=22, **kw):
    return left_at(T(s, size, color, **kw), x, y)


class ProtobufWire(Base):
    """enc-02, section 0 (with section 1's unknown fields and reused numbers): the Authorization record as 42 bytes of
    Protobuf. Field 3's key 0x18 splits into field number 3 and wire type 0; its varint a0 1f decodes to 32 + 31 x 128
    = 4,000. A new field 6 (risk score 87, bytes 30 57) is skipped and kept by old code. Reusing number 3 for a fee of 150
    makes old code read the fee as the amount, with no error."""

    def construct(self):
        self.title_card("Protobuf on the wire", "field numbers, varints and unknown fields")

        sch = panel(SCH_X0, SCH_X1, "schema: Authorization")
        lines = [sline(0, "int64 payment_id", 1), sline(1, "string merchant", 2), sline(2, "int64 amount_minor", 3),
                 sline(3, "string currency", 4), sline(4, "repeated string tags", 5)]
        self.steps("A payment authorization has five fields, and its schema gives each one a number, from 1 to 5.", [
            (lambda: [FadeIn(sch)], 0.6),
            (lambda: [LaggedStart(*[FadeIn(l, shift=0.1 * RIGHT) for l in lines], lag_ratio=0.2)], 1.4),
            "a number",
            (lambda: [Succession(*[Indicate(l[2], color=YELLOW_M, run_time=0.4) for l in lines])], 2.0),
        ])

        wire = panel(WIRE_X0, WIRE_X1, "on the wire: 42 bytes")
        rows = [brow(k, lab_, hx) for k, (lab_, hx) in enumerate(WIRE)]
        self.steps("Protobuf never writes the names. For each field, it writes a key, then the value. "
                   "This authorization takes 42 bytes.", [
            (lambda: [FadeIn(wire)], 0.6),
            "For each field",
            (lambda: [LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in rows], lag_ratio=0.25)], 1.6),
            "This authorization",
            (lambda: [*[Indicate(r[1][0], color=GOLD_M) for r in rows]], 0.9),
        ])

        kx, ax, fx = -4.4, -0.4, 3.6
        ck = cell("18", kx)
        self.steps("Take the amount, 4,000 cents. Its key is one byte: 18 in hex.", [
            (lambda: [*[r.animate.set_opacity(0.35) for i, r in enumerate(rows) if i != 2],
                      *[l.animate.set_opacity(0.35) for i, l in enumerate(lines) if i != 2]], 0.7),
            "Its key",
            (lambda: [TransformFromCopy(rows[2][1][0], ck[1]), FadeIn(ck[0])], 0.9),
        ])

        kb = bits([("00011", BLUE_M), ("000", TEAL_M)], kx)
        kl1 = lab("wire type 0: a varint", kx, L1_Y, TEAL_M)
        kl2 = lab("field number: 3", kx, L2_Y, BLUE_M)
        self.steps("In bits, the lowest three are the wire type. Here it's 0, a varint, which holds a whole number. "
                   "The bits above them are the field number, 3.", [
            (lambda: [FadeIn(kb, shift=0.1 * DOWN)], 0.7),
            "the lowest three",
            (lambda: [Indicate(kb[1], color=TEAL_M)], 0.7),
            "Here it's 0",
            (lambda: [FadeIn(kl1, shift=0.1 * UP)], 0.6),
            "The bits above",
            (lambda: [Indicate(kb[0], color=BLUE_M)], 0.7),
            (lambda: [FadeIn(kl2, shift=0.1 * UP), Indicate(lines[2][2], color=BLUE_M)], 0.8),
        ])

        ca, cf = cell("a0", ax, WHITE), cell("1f", fx, WHITE)
        ab = bits([("1", GOLD_M), ("0100000", WHITE)], ax)
        fb = bits([("0", GOLD_M), ("0011111", WHITE)], fx)
        self.steps("A varint keeps 7 bits of the number in each byte, lowest bits first. "
                   "The top bit of each byte says whether another byte follows.", [
            (lambda: [TransformFromCopy(rows[2][1][1], ca[1]), FadeIn(ca[0]),
                      TransformFromCopy(rows[2][1][2], cf[1]), FadeIn(cf[0])], 0.9),
            (lambda: [FadeIn(ab, shift=0.1 * DOWN), FadeIn(fb, shift=0.1 * DOWN)], 0.7),
            "The top bit",
            (lambda: [Indicate(ab[0], color=GOLD_M), Indicate(fb[0], color=GOLD_M)], 0.9),
        ])

        al1 = lab("top bit 1: more follows", ax, L1_Y, GOLD_M)
        al2 = lab("low 7 bits: 32", ax, L2_Y, WHITE)
        self.steps("a0 has its top bit set, so another byte follows. Its low 7 bits are 32.", [
            (lambda: [glow(ca[0], GOLD_M)], 0.7),
            (lambda: [FadeIn(al1, shift=0.1 * UP)], 0.6),
            "Its low 7 bits",
            (lambda: [Indicate(ab[1], color=YELLOW_M)], 0.7),
            (lambda: [FadeIn(al2, shift=0.1 * UP)], 0.6),
        ])

        fl1 = lab("top bit 0: last byte", fx, L1_Y, GOLD_M)
        fl2 = lab("31 x 128 = 3,968", fx, L2_Y, WHITE)
        tot = lab("32 + 3,968 = 4,000", (ax + fx) / 2, SUM_Y, GREEN_M, 26)
        self.steps("1f has a top bit of 0, so it's the last byte. It holds 31, and comes second, so it counts 31 times 128. "
                   "32 plus 3,968 is 4,000.", [
            (lambda: [glow(cf[0], GOLD_M)], 0.7),
            (lambda: [FadeIn(fl1, shift=0.1 * UP)], 0.6),
            "It holds 31",
            (lambda: [Indicate(fb[1], color=YELLOW_M)], 0.7),
            (lambda: [FadeIn(fl2, shift=0.1 * UP)], 0.6),
            "32 plus",
            (lambda: [FadeIn(tot, shift=0.1 * UP)], 0.7),
        ])

        # field 6 arrives
        work_a = VGroup(ck, kb, kl1, kl2, ca, cf, ab, fb, al1, al2, fl1, fl2, tot)
        l6 = sline(5, "int64 risk_score", 6, GOLD_M)
        r6 = brow(6, "field 6", "30 57")
        w44 = left_at(T("on the wire: 44 bytes", 24), WIRE_X0 + 0.3, PANEL_TOP - 0.36)
        self.steps("Now the risk team adds field 6, a risk score. The payment service starts writing it: "
                   "two more bytes, a key and the score, 87.", [
            (lambda: [FadeOut(work_a), *[r.animate.set_opacity(1) for r in rows], *[l.animate.set_opacity(1) for l in lines]], 0.8),
            (lambda: [FadeIn(l6, shift=0.1 * RIGHT)], 0.7),
            "The payment service",
            (lambda: [FadeIn(r6, shift=0.1 * RIGHT), Transform(wire[1], w44)], 0.8),
        ])

        rd = VGroup(RoundedRectangle(corner_radius=0.14, width=4.1, height=1.3, stroke_color=WHITE, stroke_width=3)
                    .set_fill(BLACK, 1).move_to([-4.45, -1.3, 0]),
                    T("settlement service", 24).move_to([-4.45, -1.05, 0]),
                    T("old code: fields 1 to 5", 20, GREY_B).move_to([-4.45, -1.52, 0]))
        c30, c57 = cell("30", -0.3), cell("57", 0.9, WHITE)
        b30 = bits([("00110", BLUE_M), ("000", TEAL_M)], -0.3)
        n57 = llab("57 is the value: 87", 1.9, CELL_Y, WHITE)
        k30 = llab("field 6, wire type 0", 1.9, BIN_Y, TEAL_M, t2c={"field 6": BLUE_M})
        self.steps("The settlement service still runs old code that has never heard of field 6. "
                   "It reads the key, hex 30: field 6, wire type 0.", [
            (lambda: [FadeIn(rd, shift=0.1 * UP)], 0.8),
            "It reads the key",
            (lambda: [TransformFromCopy(r6[1][0], c30[1]), FadeIn(c30[0])], 0.8),
            (lambda: [FadeIn(b30, shift=0.1 * DOWN)], 0.6),
            "field 6",
            (lambda: [FadeIn(k30, shift=0.1 * LEFT)], 0.6),
        ])

        unk = lab("unknown field 6: kept aside, no error", 0.6, L2_Y - 0.1, GOLD_M, 24)
        self.steps("Wire type 0 says a varint comes next, so the old code reads it and keeps the bytes aside, as an unknown field. "
                   "When it writes the record back, the risk score goes with it.", [
            (lambda: [TransformFromCopy(r6[1][1], c57[1]), FadeIn(c57[0])], 0.7),
            (lambda: [FadeIn(n57, shift=0.1 * LEFT)], 0.6),
            "and keeps the bytes",
            (lambda: [FadeIn(unk, shift=0.1 * UP), glow(rd[0], GOLD_M)], 0.8),
            "When it writes",
            (lambda: [Indicate(r6[1], color=GOLD_M)], 0.9),
        ])

        # number 3 is reused
        l3f = sline(2, "int64 fee_minor", 3, GOLD_M)
        l8 = sline(6, "int64 amount_minor", 8)
        self.steps("A year later, someone moves the amount to number 8, and gives number 3 to a new field, the fee.", [
            (lambda: [FadeOut(VGroup(c30, c57, b30, n57, k30, unk))], 0.6),
            "moves the amount",
            (lambda: [FadeIn(l8, shift=0.1 * RIGHT), lines[2].animate.set_opacity(0.35)], 0.8),
            "and gives number 3",
            (lambda: [Transform(lines[2], l3f)], 0.9),
        ])

        r3f = brow(2, "field 3", "18 96 01")
        r8 = brow(7, "field 8", "40 a0 1f")
        w = left_at(T("on the wire", 24), WIRE_X0 + 0.3, PANEL_TOP - 0.36)
        c18, c96, c01 = cell("18", -0.3), cell("96", 0.9, WHITE), cell("01", 2.1, WHITE)
        b18 = bits([("00011", BLUE_M), ("000", TEAL_M)], -0.3)
        n150 = llab("96 01 = 150", 3.1, CELL_Y, WHITE)
        k18 = llab("field 3, wire type 0", 1.9, BIN_Y, TEAL_M, t2c={"field 3": BLUE_M})
        self.steps("The payment service writes a fee of 150 cents under number 3. Its key is 18 again.", [
            (lambda: [Transform(rows[2], r3f), FadeIn(r8, shift=0.1 * RIGHT), Transform(wire[1], w)], 0.9),
            "Its key",
            (lambda: [TransformFromCopy(rows[2][1][0], c18[1]), FadeIn(c18[0]),
                      TransformFromCopy(rows[2][1][1], c96[1]), FadeIn(c96[0]),
                      TransformFromCopy(rows[2][1][2], c01[1]), FadeIn(c01[0])], 0.9),
            (lambda: [FadeIn(b18, shift=0.1 * DOWN), FadeIn(n150, shift=0.1 * LEFT), FadeIn(k18, shift=0.1 * LEFT)], 0.7),
        ])

        rd2 = T("old code: 3 is amount_minor", 20, GREY_B).move_to(rd[2])
        bad = lab("old code reads amount_minor = 150, not 4,000", 0.6, L2_Y - 0.1, RED_M, 24)
        self.steps("The old code still thinks 3 is the amount. It reads 150 cents instead of 4,000, with no error at all.", [
            (lambda: [Transform(rd[2], rd2), glow(rd[0], RED_M)], 0.9),
            "It reads",
            (lambda: [FadeIn(bad, shift=0.1 * UP), Indicate(n150, color=RED_M)], 0.9),
        ])

        res = left_at(M("reserved 3;", 18, GREY_B), DECL_X, LINE_Y[2])
        l9 = sline(7, "int64 fee_minor", 9, GOLD_M)
        self.steps("On the wire, the number is the field. Never change a field's number, and never reuse a deleted one. "
                   "Reserve it instead, and give the new field a new number.", [
            (lambda: [*[Indicate(l[2], color=BLUE_M) for l in lines if l is not lines[2]], Indicate(l6[2], color=BLUE_M),
                      Indicate(l8[2], color=BLUE_M)], 1.0),
            "never reuse",
            (lambda: [glow(rd[0], RED_M)], 0.8),
            "Reserve it",
            (lambda: [FadeOut(lines[2]), FadeIn(res), FadeOut(bad), rows[2].animate.set_opacity(0.35)], 0.8),
            "give the new field",
            (lambda: [FadeIn(l9, shift=0.1 * RIGHT)], 0.7),
        ])
        self.wait(0.6)
