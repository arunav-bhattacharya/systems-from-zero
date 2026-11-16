from sfz import *

SAY.insert(0, (r"\bJSON\.parse\b", "jay-son dot parse"))
SAY.insert(0, (r"\bvarints?\b", lambda m: "var int" + ("s" if m.group(0).endswith("s") else "")))
SAY.insert(0, (r"\b2 to the 53\b", "two to the fifty-third"))

ID = "1849204436731904017"
L1 = '{"paymentId":' + ID + ',"merchant":"Fern Bakery",'
L2 = '"amountMinor":4000,"currency":"EUR","tags":["card","3ds"]}'
JX0, JY = -6.5, [2.85, 2.4]
BX0, BY = -6.5, 0.6
K = 0.029                                   # bar units per byte
BAR_X, BAR_Y = 3.2, [1.75, 1.15]
NL_Y, T0, T1 = -2.25, -3.0, 3.0              # number line: ...904000 at T0, ...904256 at T1


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


def glow(rect, color=YELLOW_M, s=1.05):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def glyphs(line_text, line_mob, sub):
    """The glyphs of every occurrence of sub in a Text (Text has no glyphs for spaces)."""
    out, start = VGroup(), 0
    while True:
        i = line_text.find(sub, start)
        if i < 0:
            return out
        a = len(line_text[:i].replace(" ", ""))
        b = a + len(sub.replace(" ", ""))
        out.add(*line_mob[a:b])
        start = i + len(sub)


FIELDS = [  # field number, schema name, value shown, bytes on the wire
    (1, "paymentId", ID, 10), (2, "merchant", "Fern Bakery", 13), (3, "amountMinor", "4000", 3),
    (4, "currency", "EUR", 5), (5, "tags", "card", 6), (5, "", "3ds", 5)]


def fbox(x0, num, value, nbytes, color=GREY_B, name=""):
    v = M(value, 15, WHITE)
    w = max(v.width + 0.62, T(name, 14).width + 0.15 if name else 0)
    key = Rectangle(width=0.34, height=0.54, stroke_width=0).set_fill(fillc(GOLD_M, 0.35), 1).move_to([x0 + 0.2, BY, 0])
    r = RoundedRectangle(corner_radius=0.06, width=w, height=0.6, stroke_color=color, stroke_width=2.2).set_fill(BLACK, 0)
    r.move_to([x0 + w / 2, BY, 0])
    k = M(str(num), 16, GOLD_M).move_to(key)
    v.move_to([x0 + 0.38 + (w - 0.38) / 2, BY, 0])
    n = T(f"{nbytes} B", 16, GREY_B).move_to([x0 + w / 2, BY - 0.52, 0])
    return VGroup(r, key, k, v, n), w


def bar(k, nbytes, label, color):
    b = Rectangle(width=nbytes * K, height=0.44, stroke_width=0).set_fill(color, 0.55)
    b.move_to([BAR_X + nbytes * K / 2, BAR_Y[k], 0])
    t = T(label, 18, WHITE)
    if t.width + 0.2 < b.width:
        t.move_to(b)
    else:
        left_at(t, BAR_X + b.width + 0.12, BAR_Y[k])
    return VGroup(b, t)


def nlx(last):
    """x on the number line for an integer ending ...9040xx (last = offset from ...904000)."""
    return T0 + (T1 - T0) * last / 256


class Encodings(Base):
    """enc-01, section 2 (with section 3's byte counts and lesson 2's field numbers): the authorization as 116 bytes of
    JSON (55 of them names, quotes and colons) and as 42 bytes of Protobuf (field numbers and varints); JSON.parse in a
    TypeScript dashboard turns 1849204436731904017 into the double 1849204436731904000 (doubles are 256 apart up
    there); the schema reader decodes field 1 as a 64-bit integer."""

    def construct(self):
        self.title_card("Encodings", "the same payment as text and as binary")

        jl = left_at(T("JSON text", 20, GREY_B), JX0, 3.4)
        l1 = left_at(M(L1, 17, GREY_A, disable_ligatures=True), JX0, JY[0])
        l2 = left_at(M(L2, 17, GREY_A, disable_ligatures=True), JX0, JY[1])
        jb = bar(0, 116, "JSON: 116 bytes", PURPLE_M)
        self.steps("A payment authorization leaves the payment service as bytes. "
                   "As JSON text it takes 116 bytes, and any language can read it.", [
            (lambda: [FadeIn(jl), AddTextLetterByLetter(l1, run_time=1.4)], 1.4),
            (lambda: [AddTextLetterByLetter(l2, run_time=1.4)], 1.4),
            "116 bytes",
            (lambda: [GrowFromEdge(jb[0], LEFT), FadeIn(jb[1])], 0.8),
        ])

        names = VGroup(*[glyphs(s, m, f'"{n}":') for s, m in ((L1, l1), (L2, l2))
                         for n in ("paymentId", "merchant", "amountMinor", "currency", "tags")])
        idg = glyphs(L1, l1, ID)
        nlab = T("names, quotes, colons: 55 bytes", 18, PURPLE_M).move_to([BAR_X + 1.65, BAR_Y[0] + 0.55, 0])
        self.steps("Count what those bytes hold. Field names, quotes and colons take 55 of them, "
                   "and the ID is written out as 19 decimal digits.", [
            "Field names",
            (lambda: [names.animate.set_color(PURPLE_M), FadeIn(nlab)], 0.9),
            "and the ID",
            (lambda: [idg.animate.set_color(GOLD_M)], 0.8),
        ])

        bl = left_at(T("binary, with a schema", 20, GREY_B), BX0, BY + 1.05)
        boxes, x = VGroup(), BX0
        for num, name, val, nb in FIELDS:
            g, w = fbox(x, num, val, nb, name=name)
            if name:
                g.add(T(name, 14, GREY_C).move_to([x + w / 2, BY + 0.5, 0]))
            boxes.add(g)
            x += w + 0.08
        self.steps("A binary encoding with a schema works differently. Writer and reader share a schema "
                   "that gives each field a number, one to five. The bytes carry the number, never the name.", [
            (lambda: [FadeIn(bl)], 0.5),
            "Writer and reader",
            (lambda: [LaggedStart(*[FadeIn(b[5]) for b in boxes[:5]], lag_ratio=0.15)], 1.0),
            "The bytes carry",
            (lambda: [LaggedStart(*[FadeIn(VGroup(*b[:4]), shift=0.1 * UP) for b in boxes], lag_ratio=0.12)], 1.3),
            "never the name",
            (lambda: [*[b[1].animate.set_fill(fillc(GOLD_M, 0.6), 1) for b in boxes]], 0.6),
        ])

        self.steps("Whole numbers are varints: seven bits per byte, and only as many bytes as the value needs. "
                   "4,000 fits in 2, and the 19-digit ID in 9.", [
            "4,000 fits",
            (lambda: [glow(boxes[2][0], TEAL_M, 1.08), FadeIn(boxes[2][4])], 0.8),
            "and the 19-digit",
            (lambda: [glow(boxes[0][0], TEAL_M, 1.04), FadeIn(boxes[0][4])], 0.8),
        ])

        bb = bar(1, 42, "binary: 42 bytes", TEAL_M)
        self.steps("With every field counted, the record is 42 bytes, against 116.", [
            (lambda: [LaggedStart(*[FadeIn(b[4]) for b in boxes if b[4] not in self.mobjects], lag_ratio=0.15)], 0.8),
            "the record is",
            (lambda: [GrowFromEdge(bb[0], LEFT), FadeIn(bb[1])], 0.9),
        ])

        # ---- the dashboard reads the JSON -------------------------------------------------------------------------------
        dash = mbox("support dashboard, TypeScript", TEAL_M, h=0.55, size=18).move_to([-4.2, -0.75, 0])
        fact = left_at(T("JSON.parse: every number becomes a double, 53 bits of digits", 19, GREY_A), -1.45, -0.75)
        self.steps("Now a support dashboard in TypeScript reads the JSON. "
                   "JSON.parse turns every number into a double, which holds 53 bits of digits.", [
            (lambda: [FadeOut(nlab), FadeIn(dash, shift=0.1 * UP)], 0.6),
            (lambda: [travel(Line(l2.get_bottom() + 4.0 * LEFT, dash.get_top()), TEAL_M, 0.8)], 0.8),
            "JSON.parse turns",
            (lambda: [FadeIn(fact, shift=0.1 * UP)], 0.7),
        ])

        nl = Line([T0 - 1.6, NL_Y, 0], [T1 + 1.6, NL_Y, 0], stroke_width=2.5, color=GREY_B)
        tk = VGroup(*[Line([x_, NL_Y - 0.14, 0], [x_, NL_Y + 0.14, 0], stroke_width=3, color=GREY_A) for x_ in (T0, T1)])
        tl = VGroup(M("...904000", 16, GREY_A).move_to([T0, NL_Y - 0.4, 0]), M("...904256", 16, GREY_A).move_to([T1, NL_Y - 0.4, 0]))
        gap = T("neighbouring doubles: 256 apart", 18, GREY_B).move_to([0, NL_Y - 0.4, 0])
        lim = left_at(T("exact only up to 2 to the 53 = 9,007,199,254,740,992", 19, GREY_A), -6.5, -1.45)
        idm = Dot(radius=0.09, color=GOLD_M).move_to([nlx(17), NL_Y, 0])
        idl = M("ID ...904017", 16, GOLD_M).move_to([nlx(17) + 0.3, NL_Y + 0.38, 0])
        self.steps("Every whole number up to 2 to the 53, about 9 quadrillion, fits exactly. "
                   "Our ID is about 200 times bigger, and up there, neighbouring doubles are 256 apart.", [
            (lambda: [FadeIn(lim, shift=0.1 * UP)], 0.7),
            "Our ID",
            (lambda: [Create(nl), FadeIn(tk), FadeIn(idm), FadeIn(idl)], 0.8),
            "neighbouring doubles",
            (lambda: [FadeIn(tl), FadeIn(gap)], 0.8),
        ])

        parsed = left_at(M("paymentId = 1849204436731904000", 19, WHITE), -6.5, -3.1)
        parsed[-3:].set_color(RED_M)
        noerr = T("no error, no warning", 18, RED_M).move_to([2.6, -3.1, 0])
        self.steps("So the parser rounds to the nearest one it can hold. The ID now ends in 4000 instead of 4017, "
                   "and there's no error and no warning.", [
            (lambda: [idm.animate.move_to([T0, NL_Y, 0]).set_color(RED_M), idl.animate.move_to([T0 + 0.3, NL_Y + 0.38, 0]).set_color(RED_M)], 1.2),
            "The ID now ends",
            (lambda: [FadeIn(parsed, shift=0.1 * UP), idg[-4:].animate.set_color(RED_M)], 0.8),
            "and there's no error",
            (lambda: [FadeIn(noerr)], 0.6),
        ])

        refund = chip("refund ...904000: not found", RED_M, 18).move_to([2.6, -3.1, 0])
        self.steps("A refund for that ID finds nothing, or someone else's payment.", [
            (lambda: [FadeOut(noerr), FadeIn(refund, shift=0.1 * UP)], 0.8),
            (lambda: [glow(refund[0], RED_M, 1.06)], 0.7),
        ])

        ok = tick(True, 0.2).next_to(boxes[0], DOWN, buff=0.12).shift(0.75 * RIGHT)
        fix = chip("in JSON, send 64-bit IDs as strings", GREEN_M, 18).move_to([2.6, -3.1, 0])
        self.steps("A reader with the schema knows field 1 is a 64-bit integer, and decodes all 9 bytes exactly. "
                   "In JSON, send such IDs as strings.", [
            (lambda: [boxes[0][0].animate.set_stroke(GREEN_M, 3)], 0.6),
            "and decodes",
            (lambda: [Create(ok), glow(boxes[0][0], GREEN_M, 1.04)], 0.8),
            "In JSON",
            (lambda: [FadeOut(refund), FadeIn(fix, shift=0.1 * UP)], 0.7),
        ])

        self.steps("That's what a schema buys. Numbers replace names, so the bytes shrink, and every field has a declared type, "
                   "so no reader has to guess.", [
            "Numbers replace names",
            (lambda: [*[b[1].animate(rate_func=there_and_back).set_fill(GOLD_M, 0.9) for b in boxes], glow(bb[0], TEAL_M, 1.03)], 1.0),
            "every field has",
            (lambda: [*[glow(b[0], GREEN_M, 1.04) for b in boxes]], 1.0),
        ])

        self.steps("Text carries every name and leaves the types to each reader. "
                   "A schema moves both into an agreement, and the bytes carry only values.", [
            (lambda: [names.animate(rate_func=there_and_back).set_color(WHITE), glow(jb[0], PURPLE_M, 1.03)], 1.0),
            "A schema moves",
            (lambda: [*[glow(b[0], TEAL_M, 1.04) for b in boxes]], 1.0),
        ])
        self.wait(0.6)
