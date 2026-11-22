from sfz import *

# Amounts are said the way people say them ("forty"); captions keep "40.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\b40\.0\b", "forty point oh"))
SAY.insert(0, (r"\b2 to the 53\b", "two to the fifty-third"))
SAY.insert(0, (r"\bBase64\b", "base sixty-four"))
SAY.insert(0, (r"\b64-bit\b", "sixty-four bit"))

ID = "1849204436731904017"
SHOWN = "1849204436731904000"
J1 = '{"paymentId":' + ID + ',"merchant":"Fern Bakery",'
J2 = '"amountMinor":4000,"currency":"EUR","tags":["card","3ds"]}'

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PY, PW, PH = 2.75, 3.6, 1.05            # the two programs
PLX, PRX = -4.75, 4.75
JY = [1.55, 1.12]                        # the JSON text under the arrow
ROW_Y = [0.4, -0.22]                     # sent / shown
LAB_X, VAL_X = -3.7, -3.4
NL_Y = -2.1                              # the number line
CAP_Y, BAR_Y = -3.36, 3.6


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


def program(x, title, sub, color):
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, PY, 0])
    return VGroup(r, T(title, 24).move_to([x, PY + 0.2, 0]), T(sub, 17, GREY_B).move_to([x, PY - 0.24, 0]))


def number(s, color=WHITE, tail=4, tail_color=None, size=26):
    """A long number in mono, with its last `tail` digits in their own colour."""
    head, end = s[:-tail], s[-tail:]
    g = VGroup(M(head, size, color), M(end, size, tail_color or color)).arrange(RIGHT, buff=0.0)
    g[1].align_to(g[0], DOWN)
    return g


def json_lines(quoted=False, pid=ID):
    a = J1.replace(ID, pid)
    a = a.replace(pid, '"' + pid + '"') if quoted else a
    l1 = M(a, 17)
    l2 = M(J2, 17)
    g = VGroup(l1.move_to([0, JY[0], 0]), l2.move_to([0, JY[1], 0]))
    if quoted:
        i = a.index('"' + pid)
        for k in range(i, i + len(pid) + 2):
            l1[k].set_color(GOLD_M)
    return g


def pow53(size, color=YELLOW_M):
    b = T("2", size, color)
    e = T("53", size * 0.65, color).next_to(b, UR, buff=0.02).shift(0.08 * DOWN)
    return VGroup(b, e)


# number-line helpers: x of a value within a window of values
def nl_x(v, v0, v1, x0=-5.2, x1=5.2):
    return x0 + (v - v0) / (v1 - v0) * (x1 - x0)


def nl_tick(x, color=GREY_B, h=0.32):
    return Line([x, NL_Y - h / 2, 0], [x, NL_Y + h / 2, 0], stroke_width=3, color=color)


def nl_label(x, s, color=GREY_B, size=17):
    return M(s, size, color).move_to([x, NL_Y - 0.45, 0])


def dot_at(x, color=YELLOW_M, y=NL_Y + 0.55):
    return Dot(radius=0.1, color=color).move_to([x, y, 0]).set_z_index(6)


class Encodings(Base):
    """enc-01, section 2. Fern Bakery's refund finds no payment: the payment program sent 1849204436731904017 as JSON
    (116 bytes), and the JavaScript dashboard read it into a double: 1849204436731904000, 17 off, no warning. Scales:
    a kitchen scale in grams, a weighbridge in big steps; a double has 53 binary digits, so big numbers get big steps.
    Predict around 2^53: only 2^53 + 1 changes. Near the payment number the steps are 256 apart. The analogy breaks
    where it matters (an id is a name, not an amount). RFC 8259 sets no size; Twitter's id_str; send 64-bit numbers in
    quotes. JSON's other gaps (fractions, bytes, schema). Moral and a check (…4100 shows as …4000 too)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.8).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_row(self, i, label, value, lcolor=GREY_B):
        lab = right_at(T(label, 22, lcolor), LAB_X, ROW_Y[i])
        left_at(value, VAL_X, ROW_Y[i])
        new = VGroup(lab, value)
        old, self.rows[i] = self.rows[i], new
        return [swap(old, new)]

    def set_js(self, quoted, pid=ID):
        new = json_lines(quoted, pid)
        old, self.js = self.js, new
        return [swap(old, new)]

    def set_sub(self, prog, s, color=GREY_B):
        key = id(prog)
        old = self.subs.get(key, prog[2])
        new = T(s, 17, color).move_to(prog[2])
        self.subs[key] = new
        return [swap(old, new)]

    def clear(self, *mobs):
        return [FadeOut(m) for m in mobs if m is not None]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, -2.95, 0], [1.0, -2.95, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def line_256(self, highlight=False):
        """The steps near the payment number: ...903744, ...904000, ...904256."""
        v0, v1 = -320, 320
        base = Line([-5.5, NL_Y, 0], [5.5, NL_Y, 0], stroke_width=2, color=GREY_C)
        g = VGroup(base)
        for off, s in ((-256, "…903744"), (0, "…904000"), (256, "…904256")):
            x = nl_x(off, v0, v1)
            g.add(nl_tick(x, WHITE), nl_label(x, s, WHITE if off else (YELLOW_M if highlight else WHITE), 19))
        hdr = T("steps 256 apart", 20, GREY_B).move_to([0, NL_Y + 1.05, 0])
        return g, hdr, (lambda off: nl_x(off, v0, v1))

    def construct(self):
        self.capm = None
        self.rows = [None, None]
        self.subs = {}
        self.title_card("Seventeen off, and no warning", "how JSON lost a bakery's payment")

        # ---------------- scene 1: the missing payment ----------------
        dash = program(PRX, "dashboard", "a web page", BLUE_M)
        pay = program(PLX, "payment program", "records every payment", TEAL_M)
        refund = chip("Refund 40.00", GOLD_M, 20).move_to([PRX, PY - 1.05, 0])
        nosuch = T("no such payment", 22, RED_M).move_to([PRX, PY - 1.75, 0])
        self.steps("Picture the owner of Fern Bakery. A customer wants a refund of 40.00. She finds the payment on her dashboard, "
                   "a web page that lists the day's card payments, and presses Refund. The answer: no such payment.", [
            "A customer wants",
            (lambda: [FadeIn(refund, shift=0.1 * UP)], 0.6),
            "on her dashboard",
            (lambda: [FadeIn(dash, shift=0.1 * LEFT)], 0.7),
            "and presses Refund",
            (lambda: [refund.animate(rate_func=there_and_back).scale(1.12)], 0.6),
            "The answer",
            (lambda: [FadeIn(nosuch, shift=0.1 * UP)], 0.6),
        ])
        arr = Arrow([PLX + PW / 2 + 0.1, PY, 0], [PRX - PW / 2 - 0.1, PY, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.04)
        qm = T("?", 40, YELLOW_M).move_to([0, PY + 0.45, 0])
        self.steps("But the payment is there. The program that records payments has it, under a long number, nineteen digits, "
                   "ending in 4017. It sent that number to the dashboard, and neither program reported an error. "
                   "So where did the payment go?", [
            "The program that",
            (lambda: [FadeIn(pay, shift=0.1 * RIGHT)], 0.7),
            "under a long number",
            (lambda: self.set_row(0, "sent", number(ID, WHITE, 4, YELLOW_M)), 0.7),
            "It sent",
            (lambda: [GrowArrow(arr)], 0.6),
            "neither program",
            (lambda: [glow(pay[0], TEAL_M), glow(dash[0], BLUE_M)], 0.8),
            "So where",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
        ])

        # ---------------- scene 2: text everyone reads ----------------
        self.js = json_lines()
        nbytes = T("116 bytes", 20, GREY_B).move_to([0, PY - 0.35, 0])
        self.steps("The two programs are written in different languages, so they agree on text. The payment program writes the "
                   "payment as JSON, a plain text format every language can read: each name in quotes, then its value. "
                   "Here it is, 116 bytes.", [
            (lambda: [FadeOut(qm), FadeOut(refund), FadeOut(nosuch),
                      *self.set_sub(pay, "Kotlin"), *self.set_sub(dash, "JavaScript, in a browser")], 0.8),
            "writes the",
            (lambda: [FadeIn(self.js, shift=0.15 * RIGHT)], 0.9),
            "each name in quotes",
            (lambda: [*[Indicate(self.js[0][k], color=GOLD_M, scale_factor=1.3) for k in range(1, 12)]], 0.9),
            "Here it is",
            (lambda: [FadeIn(nbytes)], 0.5),
        ])
        self.steps("The dashboard runs JavaScript, the language web pages run. It reads the text, and turns every number into a "
                   "JavaScript number, which is a double. And here's what the dashboard shows: the same number, except it ends "
                   "in 4000. Seventeen off, and no warning.", [
            "It reads the text",
            (lambda: [glow(dash[0], BLUE_M)], 0.6),
            "which is a double",
            (lambda: self.set_sub(dash, "every number → a double", RED_M), 0.6),
            "And here's what",
            (lambda: self.set_row(1, "shown", number(SHOWN, WHITE, 4, RED_M)), 0.8),
            "Seventeen off",
            (lambda: [Indicate(self.rows[0][1][1], color=YELLOW_M), Indicate(self.rows[1][1][1], color=RED_M),
                      *self.cap("17 off, and no warning", RED_M)], 0.9),
        ])
        self.steps("A refund for that number finds nothing, or someone else's payment. That's the missing payment. "
                   "Why would a computer change a number nobody asked it to change?", [
            "A refund",
            (lambda: [FadeIn(nosuch.move_to([4.4, ROW_Y[1], 0]), shift=0.1 * UP)], 0.6),
            "Why would",
            (lambda: self.cap("why would a computer change a number?", WHITE), 0.5),
        ])
        self.stamp("shown")

        # ---------------- scene 3: scales ----------------
        k1 = chip("kitchen scale: steps of 1 g", GREEN_M, 20).move_to([-3.3, NL_Y + 0.1, 0])
        k2 = chip("weighbridge: steps of 20 kg (say)", GOLD_M, 20).move_to([3.0, NL_Y + 0.1, 0])
        self.steps("Think about scales. A kitchen scale weighs flour to the gram. The weighbridge that weighs lorries moves in "
                   "bigger steps, say 20 kilos at a time. Nobody minds. Twenty kilos on a lorry is nothing.", [
            (lambda: [*self.uncap(), FadeOut(nosuch)], 0.4),
            "A kitchen scale",
            (lambda: [FadeIn(k1, shift=0.1 * UP)], 0.6),
            "The weighbridge",
            (lambda: [FadeIn(k2, shift=0.1 * UP)], 0.6),
            "Nobody minds",
            (lambda: [glow(k2[0], GOLD_M, 1.05)], 0.7),
        ])
        # a line whose ticks spread out: close on the left, wide on the right
        xs, x, gap = [], -5.4, 0.12
        while x < 5.4:
            xs.append(x)
            x += gap
            gap *= 1.22
        spread = VGroup(Line([-5.6, NL_Y, 0], [5.6, NL_Y, 0], stroke_width=2, color=GREY_C),
                        *[nl_tick(x, GREY_B, 0.26) for x in xs])
        small = T("small numbers: exact steps", 18, GREEN_M).move_to([-3.6, NL_Y - 0.5, 0])
        big = T("big numbers: big steps", 18, GOLD_M).move_to([3.4, NL_Y - 0.5, 0])
        snap_d = dot_at(xs[-2] + 0.45 * (xs[-1] - xs[-2]), YELLOW_M, NL_Y + 0.45)
        self.steps("A double works the same way. It has room for 53 binary digits, and no more. Small numbers get exact steps, "
                   "like the kitchen scale. Big numbers get big steps, like the weighbridge. And a number between two steps is "
                   "snapped to the nearest one.", [
            (lambda: [FadeOut(k1), FadeOut(k2), Create(spread[0]), LaggedStart(*[Create(t) for t in spread[1:]], lag_ratio=0.1)], 1.2),
            "It has room",
            (lambda: self.cap("a double: room for 53 binary digits, and no more", WHITE), 0.5),
            "Small numbers",
            (lambda: [FadeIn(small)], 0.5),
            "Big numbers",
            (lambda: [FadeIn(big)], 0.5),
            "And a number between",
            (lambda: [FadeIn(snap_d, scale=0.5)], 0.4),
            "snapped",
            (lambda: [snap_d.animate.move_to([xs[-2], NL_Y + 0.45, 0])], 0.6),
        ])

        # ---------------- scene 4: the edge, and our number ----------------
        v0, v1 = 988.4, 996.6

        def X(v):
            return nl_x(v, v0, v1)

        base = Line([-5.6, NL_Y, 0], [5.6, NL_Y, 0], stroke_width=2, color=GREY_C)
        ticks = VGroup(*[nl_tick(X(v), WHITE if v <= 992 or v % 2 == 0 else GREY_D) for v in range(989, 997) if v <= 992 or v % 2 == 0])
        labs = VGroup(*[nl_label(X(v), f"…{v}", YELLOW_M if v == 992 else GREY_B) for v in range(989, 997)])
        edge = VGroup(pow53(18), T("= 9,007,199,254,740,992", 18, YELLOW_M)).arrange(RIGHT, buff=0.12)
        edge.move_to([X(992), NL_Y + 1.05, 0])
        lft = T("every whole number", 18, GREEN_M).move_to([X(990.5), NL_Y + 0.62, 0])
        rgt = T("2 apart", 18, GOLD_M).move_to([X(995), NL_Y + 0.62, 0])
        self.steps("Up to 2 to the 53, about nine quadrillion, every whole number has its own step. Just above it, the steps are "
                   "2 apart. Here are four numbers around that edge. Which ones come back changed? Pause and guess.", [
            (lambda: [FadeOut(spread), FadeOut(small), FadeOut(big), FadeOut(snap_d), *self.uncap(),
                      Create(base), FadeIn(ticks), FadeIn(labs)], 0.9),
            "Up to 2",
            (lambda: [FadeIn(edge, shift=0.1 * DOWN)], 0.5),
            "every whole number",
            (lambda: [FadeIn(lft)], 0.5),
            "Just above",
            (lambda: [FadeIn(rgt)], 0.5),
            "Pause and guess",
            (lambda: self.cap("…991, …992, …993, …994: which come back changed? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        dots = {v: dot_at(X(v)) for v in (991, 992, 993, 994)}
        self.play(FadeOut(lft), FadeOut(rgt), LaggedStart(*[FadeIn(d, shift=0.2 * DOWN) for d in dots.values()], lag_ratio=0.2), run_time=0.6)
        self.countdown(3.0)
        self.steps("Only one. 2 to the 53, plus 1, has no step of its own, so it lands on 2 to the 53. The even numbers on either "
                   "side have steps, and survive.", [
            (lambda: [*self.uncap(), *[dots[v].animate.move_to([X(v), NL_Y, 0]).set_color(GREEN_M) for v in (991, 992, 994)]], 0.6),
            "2 to the 53, plus 1",
            (lambda: [Indicate(labs[4], color=RED_M)], 0.6),
            "so it lands",
            (lambda: [dots[993].animate.move_to([X(992), NL_Y + 0.3, 0]).set_color(RED_M)], 0.8),
            (lambda: self.cap("…993 → …992", RED_M), 0.4),
            "The even numbers",
            (lambda: [Indicate(dots[991], color=GREEN_M), Indicate(dots[994], color=GREEN_M)], 0.7),
        ])
        l256, h256, X2 = self.line_256()
        d17 = dot_at(X2(17))
        lab17 = M("…904017", 19, YELLOW_M).move_to([X2(17), NL_Y + 1.0, 0])
        self.steps("Our payment number is far bigger, about two hundred times bigger, so its steps are 256 apart. "
                   "The nearest step to 4017 is 4000. There's the missing 17.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(base, ticks, labs, edge, *dots.values()))], 0.5),
            (lambda: [FadeIn(l256)], 0.6),
            "so its steps",
            (lambda: [FadeIn(h256)], 0.5),
            "The nearest step",
            (lambda: [FadeOut(h256), FadeIn(d17, shift=0.2 * DOWN), FadeIn(lab17)], 0.5),
            (lambda: [d17.animate.move_to([X2(0), NL_Y, 0]).set_color(RED_M)], 0.8),
            "There's the missing",
            (lambda: [*self.cap("4017 → 4000: the missing 17", RED_M), Indicate(self.rows[1][1][1], color=RED_M)], 0.8),
        ])
        self.stamp("snap")

        # ---------------- scene 5: where the scales break, and the rule ----------------
        self.steps("So the scale picture holds, but it breaks in one place that matters. A lorry's weight is an amount, and close "
                   "is fine. A payment number is a name. Off by 17 is a different payment, or none.", [
            "A lorry's weight",
            (lambda: self.cap("a weight is an amount: close is fine", GOLD_M), 0.5),
            "A payment number",
            (lambda: self.cap("a payment number is a name: close is wrong", RED_M), 0.5),
            "Off by 17",
            (lambda: [Indicate(self.rows[1], color=RED_M, scale_factor=1.05)], 0.8),
        ])
        self.steps("You might be thinking JSON should have complained. It can't. The document that defines JSON sets no size for "
                   "numbers. It only warns that whole numbers up to 2 to the 53, minus 1, work in every reader. Twitter hit this "
                   "with the numbers of its posts, and added a second field holding the same number as text.", [
            "It can't",
            (lambda: [FadeOut(VGroup(l256, d17, lab17)), *self.cap("RFC 8259, the document that defines JSON: no size for numbers")], 0.6),
            "It only warns",
            (lambda: self.cap("safe in every reader: whole numbers up to 9,007,199,254,740,991"), 0.5),
            "Twitter hit",
            (lambda: self.cap("Twitter: a second field, id_str, the same number as a string"), 0.5),
        ])
        okm = tick(True, 0.17)
        self.steps("So here's the rule. A big number in JSON is safe only as a string. Send 64-bit numbers in quotes. "
                   "In quotes, the dashboard keeps all 19 digits as text, and a Java program reads it straight back into a "
                   "64-bit number.", [
            "A big number",
            (lambda: self.cap("a big number in JSON is safe only as a string", YELLOW_M, 28), 0.5),
            "Send 64-bit",
            (lambda: self.set_js(True), 0.8),
            "In quotes, the dashboard",
            (lambda: [*self.set_row(1, "shown", number(ID, GREEN_M, 4, GREEN_M))], 0.8),
            (lambda: [Create(okm.next_to(self.rows[1], RIGHT, buff=0.3))], 0.4),
            "and a Java program",
            (lambda: [glow(pay[0], TEAL_M)], 0.7),
        ])

        # ---------------- scene 6: JSON's other gaps ----------------
        gaps = VGroup(T("40.0: an exact amount, or a double?", 22),
                      T("raw bytes: Base64 text, 3 KB → 4 KB", 22),
                      T("no schema: every reader guesses, in its own code", 22)).arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        gaps.move_to([0.3, NL_Y + 0.05, 0])
        self.steps("And numbers are only the first gap. JSON can't tell a whole number from a fraction: is 40.0 an exact amount, "
                   "or a double? It has no type for raw bytes, so a 3 KB signature travels as Base64 text and grows to 4 KB. "
                   "And nothing in a JSON document says what shape the record should be. Every reader guesses, in its own code.", [
            (lambda: [*self.uncap(), FadeOut(okm)], 0.4),
            "JSON can't tell",
            (lambda: [FadeIn(gaps[0], shift=0.1 * UP)], 0.6),
            "It has no type",
            (lambda: [FadeIn(gaps[1], shift=0.1 * UP)], 0.6),
            "And nothing",
            (lambda: [FadeIn(gaps[2], shift=0.1 * UP)], 0.6),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, where did the payment go? Nowhere. The number was sent right, and read into a box too small for it. "
                   "Two programs never share a number. One writes bytes, and the other decides for itself what they mean.", [
            (lambda: [FadeOut(gaps), *self.set_row(1, "shown", number(SHOWN, WHITE, 4, RED_M)), *self.set_js(False)], 0.8),
            "The number was sent",
            (lambda: [*self.cap("sent right, and read into a box too small for it", WHITE), Indicate(self.rows[0][1][1], color=YELLOW_M)], 0.6),
            "Two programs",
            (lambda: [*self.cap("one program writes bytes; the other decides what they mean", YELLOW_M), glow(pay[0], TEAL_M),
                      glow(dash[0], BLUE_M)], 0.8),
        ])
        l256b, h256b, X3 = self.line_256()
        d41 = dot_at(X3(100))
        lab41 = M("…904100", 19, YELLOW_M).move_to([X3(100), NL_Y + 1.0, 0])
        self.steps("One quick check. The next payment's number ends in 4100, and it's sent bare, without quotes. "
                   "What does the dashboard show? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(l256b), *self.set_row(0, "sent", number("1849204436731904100", WHITE, 4, YELLOW_M)),
                      *self.set_js(False, "1849204436731904100"), *self.set_row(1, "shown", M("?", 26, YELLOW_M))], 0.7),
            "ends in 4100",
            (lambda: [FadeIn(d41, shift=0.2 * DOWN), FadeIn(lab41)], 0.5),
            "Pause and think",
            (lambda: self.cap("…904100, sent bare: what does the dashboard show? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It ends in 4000 too. 4100 is nearer to 4000 than to 4256. Two payments, one number on the screen. "
                   "Unless you send them in quotes.", [
            (lambda: [*self.uncap(), d41.animate.move_to([X3(0), NL_Y, 0]).set_color(RED_M)], 0.8),
            (lambda: self.set_row(1, "shown", number(SHOWN, WHITE, 4, RED_M)), 0.6),
            "Two payments",
            (lambda: self.cap("two payments, one number on the screen", RED_M), 0.5),
            "Unless you send",
            (lambda: [*self.set_js(True, "1849204436731904100"), *self.cap("send 64-bit numbers in quotes", YELLOW_M, 28)], 0.8),
        ], after=0.3)
        self.wait(2.0)
