from sfz import *

SAY.insert(0, (r"\bvarints?\b", lambda m: "var int" + ("s" if m.group(0).endswith("s") else "")))
SAY.insert(0, (r"\bsint64\b", "S int sixty-four"))
SAY.insert(0, (r"\bfixed64\b", "fixed sixty-four"))
SAY.insert(0, (r"\bint64\b", "int sixty-four"))
SAY.insert(0, (r"\bProtobuf\b", "proto buff"))
SAY.insert(0, (r"(?<!\w)\.proto\b", "dot proto"))
SAY.insert(0, (r"\bMessagePack\b", "message pack"))
SAY.insert(0, (r"\bEUR\b", "E U R"))
SAY.insert(0, (r"\bpaymentId\b", "payment I D"))
SAY.insert(0, (r"\bamountMinor\b", "amount minor"))
SAY.insert(0, (r"\bZigZag\b", "zig zag"))
SAY.insert(0, (r"\ba0\b", "A zero"))
SAY.insert(0, (r"\b1f\b", "one F"))
SAY.insert(0, (r"\b0b\b", "zero B"))
SAY.insert(0, (r"\bhex 08\b", "hex zero eight"))
SAY.insert(0, (r"\bhex 12\b", "hex one two"))
SAY.insert(0, (r"\bhex 18\b", "hex one eight"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
FX0, FX1, FTOP, FBOT = -6.6, -2.45, 2.95, -0.95     # the form on the wall, later the .proto file
FCX = (FX0 + FX1) / 2
LINE_Y = [2.45 - 0.55 * i for i in range(6)]          # the bytes, one line per field
KEY_X, VAL_X, MEAN_X = -1.8, -1.25, 6.6
ZOOM_Y = [-1.5, -2.05, -2.6]                          # the zoom strip
CAP_Y, BAR_Y = -3.36, -3.0

LINES = [("08", "91 80 ed 83 b4 b4 ec d4 19", "1849204436731904017"),
         ("12", "0b 46 65 72 6e 20 42 …", "\"Fern Bakery\""),
         ("18", "a0 1f", "4000"),
         ("22", "03 45 55 52", "\"EUR\""),
         ("2a", "04 63 61 72 64", "\"card\""),
         ("2a", "03 33 64 73", "\"3ds\"")]
PROTO = [("message Authorization {", None), ("  int64  payment_id", "= 1;"), ("  string merchant", "= 2;"),
         ("  int64  amount_minor", "= 3;"), ("  string currency", "= 4;"), ("  repeated string tags", "= 5;"), ("}", None)]
J1 = '{"paymentId":1849204436731904017,"merchant":"Fern Bakery",'
J2 = '"amountMinor":4000,"currency":"EUR","tags":["card","3ds"]}'


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
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


CW = M("x" * 40, 15).width / 40          # one character of the .proto text


def parts(*pieces, size=24):
    """A line made of coloured pieces: (text, colour, mono?). Leading spaces in a piece widen the gap before it."""
    g = VGroup()
    x = 0.0
    for s, c, mono in pieces:
        n = len(s) - len(s.lstrip())
        m = (M if mono else T)(s.strip(), size, c)
        if len(g):
            x += 0.14 + 0.14 * n
        left_at(m, x, 0)
        x += m.width
        g.add(m)
    return g


def zrow(i, *pieces, size=24):
    g = parts(*pieces, size=size)
    return fit(g, 12.6).move_to([0, ZOOM_Y[i], 0])


def keym(i, s=None, color=GOLD_M):
    return M(s or LINES[i][0], 23, color).move_to([KEY_X, LINE_Y[i], 0])


def valm(i):
    g = VGroup(*[M(b, 22, TEAL_M) for b in LINES[i][1].split()]).arrange(RIGHT, buff=0.1)
    for m in g:
        m.align_to(g[0], DOWN)
    return left_at(g, VAL_X, LINE_Y[i])


def meanm(i, s=None, color=GREY_B):
    return right_at(M(s or LINES[i][2], 21, color), MEAN_X, LINE_Y[i])


def paper():
    r = RoundedRectangle(corner_radius=0.08, width=FX1 - FX0, height=FTOP - FBOT, stroke_color="#E8E2D0", stroke_width=3)
    return r.set_fill("#16140f", 1).move_to([FCX, (FTOP + FBOT) / 2, 0])


def cafe_form():
    title = T("catering order", 24).move_to([FCX, FTOP - 0.4, 0])
    rows = VGroup()
    for k, lab in enumerate(["name", "", "amount", "", "notes"]):
        y = FTOP - 1.0 - 0.6 * k
        num = T(str(k + 1), 22, GOLD_M).move_to([FX0 + 0.45, y, 0])
        boxr = Rectangle(width=2.6, height=0.44, stroke_color=GREY_B, stroke_width=1.5).move_to([FX0 + 2.15, y, 0])
        g = VGroup(num, boxr)
        if lab:
            g.add(left_at(T(lab, 18, GREY_B), FX0 + 0.95, y))
        rows.add(g)
    return VGroup(title, rows)


def proto_text():
    title = T("payment.proto", 22, GREY_B).move_to([FCX, FTOP - 0.38, 0])
    lines, nums = VGroup(), VGroup()
    x0 = FX0 + 0.22
    for k, (body, num) in enumerate(PROTO):
        y = FTOP - 0.95 - 0.42 * k
        lines.add(left_at(M(body.strip(), 15), x0 + (len(body) - len(body.lstrip())) * CW, y))
        if num:
            nums.add(left_at(M(num, 15, GOLD_M), x0 + 23 * CW, y))
    return VGroup(title, lines, nums)


def bar(nbytes, y, color, label, K=0.072):
    lab = right_at(T(label, 20, GREY_B), -3.3, y)
    r = Rectangle(width=nbytes * K, height=0.36, stroke_width=0).set_fill(color, 0.8)
    left_at(r, -3.1, y)
    num = T(f"{nbytes} bytes", 20, color).next_to(r, RIGHT, buff=0.2)
    return VGroup(lab, r, num)


class ProtobufWire(Base):
    """enc-02, section 0. The payment's JSON spends most of its 116 bytes on names (MessagePack 84, a bare list 39 but
    which value is which?). The café's catering form: numbered boxes, the blank on the kitchen wall = a schema; box
    numbers = field numbers. The .proto file; = 1 is not a default. Each field is a key (field number × 8 + wire type)
    and a value; predict field 2's key (hex 12). Varints: 4000 = a0 1f. The whole record: 42 bytes. Varints aren't
    always smaller: the payment number takes 9 (fixed64: 8), -1 takes 10 (sint64 with ZigZag: 1). Moral, a check
    (field 3's key: 18), and skipping an unknown field by its length, into the next section."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def zoom(self, i, new):
        old, self.z[i] = self.z[i], new
        return [swap(old, new)]

    def unzoom(self):
        olds = [m for m in self.z if m is not None]
        self.z = [None, None, None]
        return [FadeOut(m) for m in olds]

    def countdown(self, secs=3.0):
        bar_ = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar_), run_time=0.25)
        self.play(Uncreate(bar_), run_time=secs, rate_func=linear)

    def show_line(self, i, mean=None):
        self.keys[i], self.vals[i], self.means[i] = keym(i), valm(i), meanm(i, mean)
        return [FadeIn(self.keys[i], shift=0.1 * RIGHT), FadeIn(self.vals[i], shift=0.1 * RIGHT), FadeIn(self.means[i])]

    def construct(self):
        self.capm = None
        self.z = [None, None, None]
        self.keys, self.vals, self.means = [None] * 6, [None] * 6, [None] * 6
        self.title_card("Numbers instead of names", "how Protobuf writes a payment in 42 bytes")

        # ---------------- scene 1: the names fill the bytes ----------------
        j1, j2 = M(J1, 17).move_to([0, 2.45, 0]), M(J2, 17).move_to([0, 2.0, 0])

        def names():
            out = []
            for line, src in ((j1, J1), (j2, J2)):
                txt = src.replace(" ", "")
                for nm in ("paymentId", "merchant", "amountMinor", "currency", "tags"):
                    k = txt.find('"' + nm + '"')
                    if k >= 0:
                        out.append(VGroup(*line[k:k + len(nm) + 2]))
            return out

        nm = names()
        b116 = bar(116, 0.7, BLUE_M, "JSON")
        self.steps("Here's our card payment again, written as JSON text: 116 bytes. Look at what fills them. paymentId, merchant, "
                   "amountMinor, currency, tags. The names of the fields, spelled out, in every single record.", [
            (lambda: [FadeIn(VGroup(j1, j2), shift=0.1 * UP)], 0.8),
            "116 bytes",
            (lambda: [FadeIn(b116, shift=0.1 * RIGHT)], 0.6),
            "paymentId",
            (lambda: [LaggedStart(*[m.animate.set_color(GOLD_M) for m in nm], lag_ratio=0.5)], 2.6),
            "spelled out",
            (lambda: [*self.cap("the names, in every single record", GOLD_M)], 0.5),
        ])
        b84 = bar(84, 0.0, PURPLE_M, "MessagePack")
        b39 = bar(39, -0.7, GREEN_M, "just the values")
        qm = T("which is which?", 22, YELLOW_M).next_to(b39, RIGHT, buff=0.35)
        self.steps("Even MessagePack, the binary form of JSON that keeps the names, needs 84 bytes. Drop the names, write just the "
                   "five values, and it's 39. But then how does the reader know which value is which?", [
            (lambda: self.uncap(), 0.3),
            "needs 84",
            (lambda: [FadeIn(b84, shift=0.1 * RIGHT)], 0.6),
            "and it's 39",
            (lambda: [FadeIn(b39, shift=0.1 * RIGHT)], 0.6),
            "But then",
            (lambda: [FadeIn(qm, shift=0.1 * LEFT)], 0.6),
        ])

        # ---------------- scene 2: the form on the wall ----------------
        pp = paper()
        form = cafe_form()
        wall = T("on the kitchen wall", 18, GREY_B).move_to([FCX, FBOT - 0.32, 0])
        self.steps("Picture a café that takes catering orders on a paper form. Every box has a number: box 1 is the name, box 3 the "
                   "amount, box 5 any notes. The cooks keep a blank copy on the wall, and read each order by box number, never by "
                   "the printed questions.", [
            (lambda: [FadeOut(VGroup(j1, j2, b116, b84, b39, qm))], 0.6),
            (lambda: [FadeIn(pp), FadeIn(form[0])], 0.7),
            "Every box",
            (lambda: [LaggedStart(*[FadeIn(r) for r in form[1]], lag_ratio=0.25)], 1.2),
            "box 1 is",
            (lambda: [Indicate(form[1][0][0], color=GOLD_M, scale_factor=1.4)], 0.5),
            "box 3",
            (lambda: [Indicate(form[1][2][0], color=GOLD_M, scale_factor=1.4)], 0.5),
            "box 5",
            (lambda: [Indicate(form[1][4][0], color=GOLD_M, scale_factor=1.4)], 0.5),
            "a blank copy",
            (lambda: [FadeIn(wall)], 0.5),
            "by box number",
            (lambda: [LaggedStart(*[r[0].animate(rate_func=there_and_back).scale(1.4) for r in form[1]], lag_ratio=0.2)], 1.2),
        ])
        self.steps("Map it. The blank form on the wall is a schema: a description of a record's fields and their types, kept apart "
                   "from the data. Both sides keep a copy. And the box numbers are field numbers. They travel in the bytes, in "
                   "place of the names.", [
            "is a schema",
            (lambda: [*self.cap("the blank form on the wall: a schema"), glow(pp, WHITE, 1.02)], 0.6),
            "Both sides",
            (lambda: self.cap("a schema: a record's fields and their types, kept apart from the data; both sides keep a copy"), 0.5),
            "And the box numbers",
            (lambda: [*self.cap("box numbers: field numbers, sent in place of the names", GOLD_M),
                      LaggedStart(*[Indicate(r[0], color=GOLD_M, scale_factor=1.4) for r in form[1]], lag_ratio=0.2)], 1.2),
        ])

        # ---------------- scene 3: Protobuf and its .proto file ----------------
        proto = proto_text()
        self.steps("Protocol Buffers, or Protobuf, is the most common way to do this in Java and Kotlin programs. You write the form "
                   "in a .proto file. Each line names a field, its type, and a number. And careful: equals 1 is not a default value. "
                   "It's the box number. It looks like a default, and that has fooled more of us than anyone admits.", [
            (lambda: self.uncap(), 0.3),
            "You write the form",
            (lambda: [FadeOut(form), FadeOut(wall), FadeIn(proto[0]), FadeIn(proto[1]), FadeIn(proto[2])], 0.9),
            "Each line",
            (lambda: [LaggedStart(*[Indicate(m, color=WHITE, scale_factor=1.05) for m in proto[1][1:6]], lag_ratio=0.2)], 1.2),
            "And careful",
            (lambda: [*self.cap("= 1 is not a default value: it's the field number", GOLD_M),
                      LaggedStart(*[Indicate(m, color=GOLD_M, scale_factor=1.3) for m in proto[2]], lag_ratio=0.2)], 1.2),
        ])
        self.stamp("proto")

        # ---------------- scene 4: the key ----------------
        self.steps("Now the bytes. Each field becomes a key, then a value. The key packs two things into one number: the field "
                   "number times eight, plus a wire type. The wire type tells the reader how to find where the value ends.", [
            (lambda: self.uncap(), 0.3),
            "Each field",
            (lambda: [*self.show_line(2)], 0.7),
            "The key packs",
            (lambda: self.zoom(0, zrow(0, ("key", GOLD_M, False), ("=", WHITE, False), ("field number × 8", GOLD_M, False),
                                         ("+", WHITE, False), ("wire type", YELLOW_M, False))), 0.6),
            "The wire type tells",
            (lambda: [Indicate(self.vals[2], color=TEAL_M)], 0.8),
        ])
        self.steps("Type 0 is a varint, a whole number. Type 2 is a length, followed by that many bytes, for text and lists. "
                   "Programmers write bytes in hex, base sixteen, two digits a byte. Field 1 is a varint, so its key is 1 times 8, "
                   "plus 0: hex 08. Field 2 is text. What's its key? Pause and work it out.", [
            (lambda: [FadeOut(VGroup(self.keys[2], self.vals[2], self.means[2]))], 0.4),
            "Type 0",
            (lambda: self.zoom(1, zrow(1, ("wire type 0:", YELLOW_M, False), ("a varint, a whole number", WHITE, False),
                                         ("      wire type 2:", YELLOW_M, False), ("a length, then that many bytes", WHITE, False))), 0.6),
            "Programmers write",
            (lambda: self.cap("hex: base 16, two digits a byte (00 to ff)"), 0.5),
            "Field 1 is",
            (lambda: self.zoom(2, zrow(2, ("field 1, varint:", GREY_B, False), ("1 × 8 + 0 = 8 = hex 08", GOLD_M, True))), 0.6),
            (lambda: [FadeIn(keym(0)), ], 0.4),
            "Field 2 is",
            (lambda: [*self.uncap(), *self.zoom(2, zrow(2, ("field 2, text:", GREY_B, False), ("2 × 8 + 2 = ?", GOLD_M, True)))], 0.6),
            "Pause and",
            (lambda: self.cap("field 2's key? pause and work it out", YELLOW_M), 0.4),
        ], after=0)
        self.keys[0] = [m for m in self.mobjects if isinstance(m, Text) and m.text == "08"][-1]
        self.countdown(3.0)
        self.steps("2 times 8 is 16, plus 2 is 18. In hex, that's 12. After it comes the length, 11, written 0b, then the 11 bytes "
                   "of Fern Bakery.", [
            (lambda: [*self.uncap(), *self.zoom(2, zrow(2, ("field 2, text:", GREY_B, False), ("2 × 8 + 2 = 18 = hex 12", GOLD_M, True)))], 0.6),
            "In hex",
            (lambda: [FadeIn(keym(1), shift=0.1 * RIGHT)], 0.5),
            "After it comes",
            (lambda: [FadeIn(valm(1)[0])], 0.5),
            "then the 11",
            (lambda: [FadeIn(VGroup(*valm(1)[1:])), FadeIn(meanm(1))], 0.7),
        ])
        # keep handles to what is on screen for line 1
        self.keys[1] = keym(1)
        self.vals[1] = valm(1)
        self.means[1] = meanm(1)
        self.stamp("key")

        # ---------------- scene 5: the varint ----------------
        self.steps("Whole numbers use a varint: as few bytes as the number needs. Each byte holds seven bits of the number, lowest "
                   "bits first. Its eighth bit, the top one, is a little flag that says: more to come.", [
            (lambda: [*self.unzoom()], 0.4),
            "Each byte holds",
            (lambda: self.zoom(0, zrow(0, ("a byte:", GREY_B, False), ("1", RED_M, True), ("0100000", TEAL_M, True),
                                         ("   seven bits of the number, and a flag", GREY_B, False))), 0.6),
            "a little flag",
            (lambda: self.cap("the top bit: 1 = more to come, 0 = this is the last byte", RED_M), 0.5),
        ])
        self.steps("Take the amount, 4000. Its lowest seven bits are worth 32, and more is coming, so the flag is set: a0. What's left "
                   "is 31, with the flag clear: 1f. So 4000 is two bytes, a0 1f. Check it: 32, plus 31 times 128, is 4000.", [
            (lambda: [*self.uncap(), *self.zoom(0, zrow(0, ("4000 =", WHITE, False), ("11111", GOLD_M, True), ("0100000", TEAL_M, True),
                                                       ("in binary", GREY_B, False)))], 0.6),
            "Its lowest seven",
            (lambda: self.zoom(1, zrow(1, ("byte 1:", GREY_B, False), ("1", RED_M, True), ("0100000", TEAL_M, True),
                                         ("= a0", WHITE, True), ("(32, more to come)", GREY_B, False))), 0.6),
            "What's left",
            (lambda: self.zoom(2, zrow(2, ("byte 2:", GREY_B, False), ("0", RED_M, True), ("0011111", GOLD_M, True),
                                         ("= 1f", WHITE, True), ("(31, the last byte)", GREY_B, False))), 0.6),
            "So 4000 is",
            (lambda: [*self.show_line(2)], 0.6),
            "Check it",
            (lambda: self.cap("32 + 31 × 128 = 32 + 3,968 = 4,000", GREEN_M), 0.5),
        ])
        self.stamp("varint")

        # ---------------- scene 6: the whole payment ----------------
        total = T("42 bytes   (JSON: 116)", 24, GREEN_M).move_to([2.6, LINE_Y[5] - 0.7, 0])
        self.steps("Now the whole payment. Field 1, the payment number. Field 2, Fern Bakery. Field 3, 4000. Field 4, EUR. And field 5 "
                   "twice, once per tag. 42 bytes, against 116 for JSON. Numbers, wire types and values, and not one name.", [
            (lambda: [*self.unzoom(), *self.uncap()], 0.4),
            "Field 1",
            (lambda: [FadeIn(valm(0)), FadeIn(meanm(0))], 0.6),
            "Field 4",
            (lambda: [*self.show_line(3)], 0.5),
            "And field 5",
            (lambda: [*self.show_line(4)], 0.5),
            (lambda: [*self.show_line(5)], 0.5),
            "42 bytes",
            (lambda: [FadeIn(total, shift=0.1 * UP)], 0.6),
            "and not one name",
            (lambda: [LaggedStart(*[Indicate(k, color=GOLD_M, scale_factor=1.3) for k in self.mobjects
                                    if isinstance(k, Text) and k.text in ("08", "12", "18", "22", "2a")], lag_ratio=0.15)], 1.2),
        ])
        self.stamp("whole")

        # ---------------- scene 7: is a varint always smaller? ----------------
        v0 = [m for m in self.mobjects if isinstance(m, VGroup) and len(m) == 9 and all(isinstance(x, Text) for x in m)]
        self.steps("So should every number be a varint? Let's be fair to them. Anything below 128 takes one byte. But the payment "
                   "number is huge and random-looking. As a varint it takes 9 bytes. Declared as fixed64, a type that always uses "
                   "8, it takes 8.", [
            (lambda: [FadeOut(total)], 0.4),
            "Anything below 128",
            (lambda: self.cap("below 128: one byte", GREEN_M), 0.5),
            "As a varint",
            (lambda: [*([v0[-1].animate.set_color(RED_M)] if v0 else []),
                      *self.zoom(0, zrow(0, ("payment number:", GREY_B, False), ("int64 (varint): 9 bytes", RED_M, True),
                                         ("   fixed64: 8 bytes", GREEN_M, True)))], 0.7),
        ])
        self.steps("Negative numbers are worse. A computer stores minus 1 with all 64 bits set, so a plain int64 needs 10 bytes for "
                   "it. The type sint64 first applies ZigZag: 0 becomes 0, minus 1 becomes 1, 1 becomes 2, minus 2 becomes 3. "
                   "Then minus 1 takes one byte.", [
            (lambda: self.uncap(), 0.3),
            "so a plain",
            (lambda: self.zoom(1, zrow(1, ("-1:", GREY_B, False), ("int64: 10 bytes", RED_M, True), ("   sint64: 1 byte", GREEN_M, True))), 0.6),
            "first applies ZigZag",
            (lambda: self.zoom(2, zrow(2, ("ZigZag:", GREY_B, False), ("0→0   -1→1   1→2   -2→3", YELLOW_M, True))), 0.6),
            "Then minus 1",
            (lambda: [Indicate(self.z[1], color=GREEN_M, scale_factor=1.05)], 0.7),
        ])
        self.steps("So the type you declare decides the bytes. Pick it for the values you expect.", [
            (lambda: self.cap("the type you declare decides the bytes: pick it for the values you expect", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 8: the moral, a check, and the box-6 loop ----------------
        self.steps("So: put a number on each field, and let the bytes carry numbers, not names. Both sides keep the form, and every "
                   "value says how long it is.", [
            (lambda: [*self.unzoom(), *([v0[-1].animate.set_color(TEAL_M)] if v0 else [])], 0.5),
            "put a number",
            (lambda: [*self.cap("numbers, not names", GOLD_M), LaggedStart(*[Indicate(m, color=GOLD_M, scale_factor=1.3) for m in proto[2]], lag_ratio=0.15)], 1.0),
            "every value says",
            (lambda: self.cap("both sides keep the form; every value says how long it is", WHITE), 0.5),
        ])
        k3 = [m for m in self.mobjects if isinstance(m, Text) and m.text == "18"][-1]
        q3 = M("?", 23, YELLOW_M).move_to(k3)
        self.steps("One quick check. Field 3, the amount, is a varint. What's its key byte? Pause and think.", [
            (lambda: [*self.uncap(), FadeOut(k3), FadeIn(q3)], 0.5),
            "What's its key",
            (lambda: self.cap("field 3, a varint: what's its key byte? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("3 times 8, plus 0, is 24. In hex, 18. That's the 18 in front of a0 1f.", [
            (lambda: [*self.uncap(), *self.zoom(1, zrow(1, ("field 3, varint:", GREY_B, False), ("3 × 8 + 0 = 24 = hex 18", GOLD_M, True)))], 0.6),
            "In hex",
            (lambda: [FadeOut(q3), FadeIn(k3)], 0.5),
            "That's the 18",
            (lambda: [Indicate(k3, color=GOLD_M, scale_factor=1.4)], 0.7),
        ])
        v4 = valm(4)
        v5 = valm(5)
        cur = SurroundingRectangle(keym(4), buff=0.08, stroke_color=YELLOW_M, stroke_width=3)
        self.steps("And every value says how long it is: that matters more than it looks. A reader that didn't know field 5 could "
                   "still read its length and skip exactly that many bytes. Next, the café adds box 6, and the night cook still "
                   "has last month's form.", [
            (lambda: [*self.unzoom()], 0.4),
            "A reader that",
            (lambda: [Create(cur)], 0.4),
            "still read its length",
            (lambda: [cur.animate.become(SurroundingRectangle(v4[0], buff=0.08, stroke_color=YELLOW_M, stroke_width=3))], 0.4),
            (lambda: [cur.animate.become(SurroundingRectangle(VGroup(*v4[1:]), buff=0.08, stroke_color=GREY_B, stroke_width=3)),
                      *self.cap("an unknown field: read its length, skip that many bytes")], 0.6),
            (lambda: [cur.animate.become(SurroundingRectangle(keym(5), buff=0.08, stroke_color=YELLOW_M, stroke_width=3))], 0.4),
            (lambda: [cur.animate.become(SurroundingRectangle(v5[0], buff=0.08, stroke_color=YELLOW_M, stroke_width=3))], 0.4),
            (lambda: [cur.animate.become(SurroundingRectangle(VGroup(*v5[1:]), buff=0.08, stroke_color=GREY_B, stroke_width=3))], 0.5),
            "Next, the café",
            (lambda: [FadeOut(cur), *self.cap("next: the café adds box 6", GOLD_M)], 0.6),
        ], after=0.3)
        self.wait(2.0)
