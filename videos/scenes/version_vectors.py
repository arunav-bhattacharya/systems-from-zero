from sfz import *

# card numbers are said the way people read them; the regions are letters; clock times as people say them
SAY.insert(0, (r"\b4417\b", "forty four seventeen"))
SAY.insert(0, (r"\b5310\b", "fifty three ten"))
SAY.insert(0, (r"\b9921\b", "ninety nine twenty one"))
SAY.insert(0, (r"\bEU\b", "E U"))
SAY.insert(0, (r"\bUS\b", "U S"))
SAY.insert(0, (r"\b10:00:0(\d)\b", r"ten o'clock and \1 seconds"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BX = {"eu": -4.2, "us": 4.2}          # the two copies of the list
BW, BH, BY = 4.4, 4.4, 0.05
B_TOP, B_BOT = BY + BH / 2, BY - BH / 2
TITLE_Y = B_TOP - 0.4
MARK_Y = B_TOP - 1.15                    # the bookmarks row
SEP_Y = B_TOP - 1.68
CARD_Y = [SEP_Y - 0.5, SEP_Y - 1.15, SEP_Y - 1.8]
STAMP_Y = B_BOT - 0.4
WIFI_Y = B_TOP - 0.35
CAP_Y, BAR_Y, HEAD_Y = -3.3, -2.8, 3.3
COL = {"eu": TEAL_M, "us": GOLD_M}
CARDS = ["card-4417", "card-9921", "card-5310"]


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

    def steps(self, text, items, after=0.3):
        """Speak one line and play steps inside it. A step is (fn, run_time), built just before it plays;
        a number waits that long; a string waits until about where that phrase is spoken."""
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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


# ---- the pieces ----
def list_box(side):
    x = BX[side]
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to([x, BY, 0])
    sep = Line([x - BW / 2 + 0.25, SEP_Y, 0], [x + BW / 2 - 0.25, SEP_Y, 0], stroke_width=1.5, color=GREY_D)
    return VGroup(r, sep)


def title(side, s):
    return left_at(T(s, 28), BX[side] - BW / 2 + 0.3, TITLE_Y)


def bookmark(who, n, x, y, hot=False):
    """One bookmark: whose changes, and how far this copy has read into them."""
    c = COL[who]
    t = M(f"{who} {n}", 28, YELLOW_M if hot else WHITE)
    tag = Polygon([-0.8, 0.3, 0], [0.8, 0.3, 0], [0.8, -0.3, 0], [0.0, -0.46, 0], [-0.8, -0.3, 0],
                  stroke_color=c, stroke_width=2.5).set_fill(fillc(c, 0.3), 1)
    return VGroup(tag, t.move_to([0, 0.02, 0])).move_to([x, y, 0])


def marks(side, eu, us, hot=None):
    x = BX[side]
    return VGroup(bookmark("eu", eu, x - 0.95, MARK_Y, hot == "eu"), bookmark("us", us, x + 0.95, MARK_Y, hot == "us"))


def card(side, k, name, color=WHITE):
    return M(name, 32, color).move_to([BX[side], CARD_Y[k], 0])


def strike(m, color=RED_M):
    return Line(m.get_left() + 0.1 * LEFT, m.get_right() + 0.1 * RIGHT, stroke_width=3, color=color)


class VersionVectors(Base):
    """repl-08, section 2. Two tills (two regions) and a list of blocked cards. The Wi-Fi drops: EU unblocks 4417, US
    blocks 5310. Last write wins keeps EU's later list and the stolen card works again. Bookmarks, one per till,
    say how far each copy has read into each till's changes: the version vector. The easy case replaces; the clash
    ([eu 3, us 0] vs [eu 2, us 1]) is concurrent, kept as siblings. The union merge brings 4417 back. Limits, moral,
    and a check: does the merged write [eu 4, us 1] replace both siblings?"""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_title(self, side, s):
        new = title(side, s)
        old, self.titles[side] = self.titles[side], new
        return [swap(old, new)]

    def set_marks(self, side, eu, us, hot=None):
        new = marks(side, eu, us, hot)
        old, self.mk[side] = self.mk[side], new
        return [swap(old, new)]

    def set_stamp(self, side, s=None, color=GREY_B):
        old = self.stamp[side]
        new = T(s, 26, color).move_to([BX[side], STAMP_Y, 0]) if s else None
        self.stamp[side] = new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def construct(self):
        self.capm = None
        self.titles = {"eu": None, "us": None}
        self.mk = {"eu": None, "us": None}
        self.stamp = {"eu": None, "us": None}
        self.title_card("Which list should the shop keep?", "two copies, two changes, and a test for who saw what")

        # ---------------- scene 1: the two tills ----------------
        boxes = {s: list_box(s) for s in ("eu", "us")}
        cards = {s: [card(s, 0, CARDS[0]), card(s, 1, CARDS[1])] for s in ("eu", "us")}
        wifi = DashedLine([BX["eu"] + BW / 2 + 0.1, WIFI_Y, 0], [BX["us"] - BW / 2 - 0.1, WIFI_Y, 0], dash_length=0.12,
                          stroke_width=3, color=GREY_B)
        wifi_l = T("Wi-Fi", 24, GREY_B).next_to(wifi, UP, buff=0.18)
        self.steps("Picture a shop with two tills, and a list of cards to refuse, such as cards reported stolen. "
                   "Each till keeps its own copy, and the copies sync over the shop's Wi-Fi.", [
            "two tills",
            (lambda: [FadeIn(boxes["eu"]), FadeIn(boxes["us"]), *self.set_title("eu", "till 1"), *self.set_title("us", "till 2")], 0.8),
            "a list of cards",
            (lambda: [*[FadeIn(c, shift=0.1 * DOWN) for s in ("eu", "us") for c in cards[s]], *self.cap("cards to refuse")], 0.8),
            "sync over",
            (lambda: [Create(wifi), FadeIn(wifi_l)], 0.6),
            (lambda: [Succession(FadeIn(d := Dot(radius=0.08, color=YELLOW_M).move_to(wifi.get_start()), run_time=0.05),
                                 d.animate(run_time=0.7).move_to(wifi.get_end()), FadeOut(d, run_time=0.15))], 0.9),
        ])
        cut = tick(False, 0.2).move_to(wifi.get_center())
        s1 = strike(cards["eu"][0])
        self.steps("One morning the Wi-Fi drops. At the first till, a customer's lost card has turned up, so the cashier takes card 4417 off the list.", [
            (lambda: [*self.uncap(), wifi.animate.set_color(RED_M), Create(cut), Transform(wifi_l, T("Wi-Fi down", 22, RED_M).move_to(wifi_l))], 0.7),
            "takes card 4417",
            (lambda: [Create(s1)], 0.5),
            (lambda: [cards["eu"][0].animate.set_opacity(0.3), s1.animate.set_opacity(0.6)], 0.5),
        ])
        c5310 = card("us", 2, CARDS[2], GOLD_M)
        self.steps("At the second till, the bank phones about a stolen card, and the cashier adds card 5310.", [
            "adds card",
            (lambda: [FadeIn(c5310, shift=0.15 * DOWN)], 0.6),
        ])
        self.steps("When the Wi-Fi comes back, the two lists disagree. Which one should the shop keep?", [
            (lambda: [FadeOut(cut), wifi.animate.set_color(GREY_B), Transform(wifi_l, T("Wi-Fi", 22, GREY_B).move_to(wifi_l))], 0.6),
            "Which one",
            (lambda: [glow(boxes["eu"][0], YELLOW_M, 1.02), glow(boxes["us"][0], YELLOW_M, 1.02), *self.cap("which list should the shop keep?", YELLOW_M)], 0.9),
        ])

        # ---------------- scene 2: keep the later one ----------------
        self.steps("The common answer is: keep the later one. On one computer, the later write is the newer decision. "
                   "This rule is called last write wins.", [
            (lambda: self.cap("keep the later one?"), 0.5),
            "called last write wins",
            (lambda: self.cap("last write wins: keep the highest time", WHITE), 0.6),
        ])
        self.steps("The first till's list says 10:00:05. The second says 10:00:03. So the first list wins, the whole of it, "
                   "and the second list is thrown away.", [
            (lambda: self.set_stamp("eu", "stamped 10:00:05", WHITE), 0.5),
            "The second says",
            (lambda: self.set_stamp("us", "stamped 10:00:03", WHITE), 0.5),
            "So the first",
            (lambda: [glow(boxes["eu"][0], GREEN_M, 1.02)], 0.7),
            "thrown away",
            (lambda: [*[c.animate.set_opacity(0.25) for c in cards["us"]], c5310.animate.set_opacity(0.25),
                      boxes["us"][0].animate.set_stroke(GREY_D)], 0.7),
        ])
        self.steps("And with it, the stolen card. Card 5310 works again. No error, no warning. "
                   "Well... the thief is having a better morning than the shop.", [
            "Card 5310",
            (lambda: [c5310.animate.set_opacity(1).set_color(RED_M), *self.cap("the stolen card works again", RED_M)], 0.7),
            "No error",
            (lambda: self.cap("no error, no warning", RED_M), 0.5),
        ], after=0.5)
        self.steps("Notice what went wrong. Neither cashier knew about the other's change. Later on the clock doesn't mean the "
                   "writer had seen the other list. And if the first till's clock ran a few seconds fast, it wasn't even later.", [
            (lambda: [*self.cap("neither cashier knew about the other's change")], 0.6),
            "Later on the clock",
            (lambda: self.cap("later on the clock is not \"saw the other list\""), 0.6),
            "ran a few seconds fast",
            (lambda: [Wiggle(self.stamp["eu"], scale_value=1.1, rotation_angle=0.02 * TAU), *self.cap("and a fast clock isn't even later", RED_M)], 0.9),
        ])
        self.steps("What we want is for each list to carry what its writer had already seen. Then the shop could tell a list "
                   "that replaces another from two lists that clash.", [
            (lambda: [*self.set_stamp("eu"), *self.set_stamp("us"), *[c.animate.set_opacity(1) for c in cards["us"]],
                      c5310.animate.set_opacity(1).set_color(GOLD_M), boxes["us"][0].animate.set_stroke(WHITE),
                      *self.cap("wanted: each list carries what its writer had seen", YELLOW_M)], 0.8),
        ], after=0.4)

        # ---------------- scene 3: bookmarks ----------------
        self.steps("Here's an idea from everyday reading: bookmarks. Each till numbers its own changes, one, two, three. "
                   "And every copy of the list carries one bookmark per till, saying how far into that till's changes it has read.", [
            (lambda: self.uncap(), 0.3),
            "bookmarks",
            (lambda: self.cap("one bookmark per till: how far into its changes this copy has read"), 0.6),
            "one bookmark per till",
            (lambda: [*self.set_marks("eu", 2, 0), *self.set_marks("us", 2, 0)], 0.9),
        ])
        self.steps("In the app, the two tills are two copies of the list in two regions, Europe and the US. "
                   "Before the Wi-Fi dropped, both copies had read EU's first two changes, and none from the US.", [
            "two regions",
            (lambda: [*self.set_title("eu", "EU copy"), *self.set_title("us", "US copy"), *self.cap("eu: Europe     us: the US")], 0.8),
            "Before the Wi-Fi",
            (lambda: [*self.set_marks("eu", 2, 0, "eu"), *self.set_marks("us", 2, 0, "eu")], 0.6),
            "and none",
            (lambda: [*self.set_marks("eu", 2, 0, "us"), *self.set_marks("us", 2, 0, "us")], 0.6),
        ])
        self.steps("When a copy takes a change, it moves its own bookmark forward by one. EU removes card 4417, so its EU bookmark "
                   "goes from 2 to 3. US adds card 5310, so its US bookmark goes from 0 to 1.", [
            (lambda: [*self.uncap(), *self.set_marks("eu", 2, 0), *self.set_marks("us", 2, 0)], 0.5),
            "EU removes",
            (lambda: [glow(s1, RED_M, 1.05)], 0.6),
            "goes from 2 to 3",
            (lambda: self.set_marks("eu", 3, 0, "eu"), 0.6),
            "US adds",
            (lambda: [Indicate(c5310, color=GOLD_M, scale_factor=1.1)], 0.6),
            "goes from 0 to 1",
            (lambda: self.set_marks("us", 2, 1, "us"), 0.6),
        ])

        # ---------------- scene 4: the test ----------------
        old_eu = marks("eu", 2, 0).move_to([0, 0.5, 0])
        old_lab = T("EU, before", 20, GREY_B).next_to(old_eu, UP, buff=0.2)
        cmp_ok = T("3 ≥ 2,  0 ≥ 0", 30, GREEN_M).next_to(old_eu, DOWN, buff=0.35)
        self.steps("Now the test. Take the easy case first. EU's list before the change had bookmarks 2 and 0. After, 3 and 0. "
                   "Every bookmark is at least as far along, so the newer list has read everything the old one had. It can replace it.", [
            (lambda: [*self.set_marks("eu", 3, 0), *self.set_marks("us", 2, 1)], 0.4),
            "before the change",
            (lambda: [FadeIn(old_eu, shift=0.2 * RIGHT), FadeIn(old_lab)], 0.6),
            "After, 3",
            (lambda: [glow(self.mk["eu"][0][0], TEAL_M, 1.1)], 0.6),
            "Every bookmark",
            (lambda: [FadeIn(cmp_ok, shift=0.1 * UP)], 0.6),
            "It can replace",
            (lambda: self.cap("at least as far along everywhere: it saw the old one, so it replaces it", GREEN_M), 0.6),
        ])
        self.steps("Now the clash. EU's bookmarks: 3 and 0. US's: 2 and 1. Did either one see the other's change? Pause and guess.", [
            (lambda: [FadeOut(VGroup(old_eu, old_lab, cmp_ok)), *self.uncap()], 0.5),
            "EU's bookmarks",
            (lambda: [glow(boxes["eu"][0], TEAL_M, 1.02)], 0.6),
            "US's: 2",
            (lambda: [glow(boxes["us"][0], GOLD_M, 1.02)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        r_eu = VGroup(M("eu", 28, TEAL_M), M("3 > 2", 32, WHITE)).arrange(RIGHT, buff=0.35).move_to([0, 0.6, 0])
        r_us = VGroup(M("us", 28, GOLD_M), M("0 < 1", 32, WHITE)).arrange(RIGHT, buff=0.35).move_to([0, -0.6, 0])
        ahead_eu = T("EU ahead", 24, TEAL_M).next_to(r_eu, DOWN, buff=0.12)
        ahead_us = T("US ahead", 24, GOLD_M).next_to(r_us, DOWN, buff=0.12)
        self.steps("Compare them one at a time. On EU's changes, EU is ahead, 3 against 2. On US's changes, US is ahead, 1 against 0. "
                   "Each has read something the other hasn't. So neither saw the other.", [
            (lambda: self.uncap(), 0.3),
            "On EU's changes",
            (lambda: [*self.set_marks("eu", 3, 0, "eu"), *self.set_marks("us", 2, 1, "eu"), FadeIn(r_eu)], 0.6),
            "3 against 2",
            (lambda: [FadeIn(ahead_eu, shift=0.1 * LEFT)], 0.4),
            "On US's changes",
            (lambda: [*self.set_marks("eu", 3, 0, "us"), *self.set_marks("us", 2, 1, "us"), FadeIn(r_us)], 0.6),
            "1 against 0",
            (lambda: [FadeIn(ahead_us, shift=0.1 * RIGHT)], 0.4),
            "So neither",
            (lambda: self.cap("each is ahead somewhere: neither saw the other", YELLOW_M), 0.6),
        ])

        # ---------------- scene 5: the names ----------------
        self.steps("That's the test. If every entry of one is at most the other's, the second saw the first, and the first can go. "
                   "If each is ahead somewhere, the writes are concurrent: neither knew about the other.", [
            "If every entry",
            (lambda: self.cap("every entry at most the other's: an ancestor, it can go", GREEN_M), 0.6),
            "If each is ahead",
            (lambda: self.cap("each ahead somewhere: concurrent, neither knew about the other", YELLOW_M), 0.6),
        ])
        vec_eu = M("[(eu, 3)]", 26, TEAL_M).move_to([BX["eu"], STAMP_Y, 0])
        vec_us = M("[(eu, 2), (us, 1)]", 26, GOLD_M).move_to([BX["us"], STAMP_Y, 0])
        self.steps("The bookmarks have a name: a version vector, one counter per copy. "
                   "Dynamo, Amazon's design for a store with many copies, called it a vector clock.", [
            (lambda: [*self.set_marks("eu", 3, 0), *self.set_marks("us", 2, 1)], 0.4),
            "a version vector",
            (lambda: [*self.cap("version vector: one counter per copy", WHITE), FadeIn(vec_eu, shift=0.1 * UP), FadeIn(vec_us, shift=0.1 * UP)], 0.7),
            "called it",
            (lambda: self.cap("Dynamo's name for it: a vector clock"), 0.5),
        ])
        sib = {s: T("sibling", 26, YELLOW_M).move_to([BX[s], B_TOP + 0.35, 0]) for s in ("eu", "us")}
        self.steps("And when two versions are concurrent, Dynamo doesn't pick one. It keeps both, side by side, as siblings, "
                   "and hands both to the program on the next read.", [
            (lambda: [FadeOut(VGroup(r_eu, r_us, ahead_eu, ahead_us)), *self.uncap()], 0.5),
            "keeps both",
            (lambda: [FadeIn(sib["eu"], shift=0.1 * DOWN), FadeIn(sib["us"], shift=0.1 * DOWN), *self.cap("siblings: both versions kept, side by side", YELLOW_M)], 0.7),
        ])

        # ---------------- scene 6: break the obvious merge ----------------
        ub = RoundedRectangle(corner_radius=0.14, width=3.3, height=2.9, stroke_color=GREEN_M, stroke_width=3).set_fill(fillc(GREEN_M), 1)
        ub.move_to([0, -0.6, 0])
        u_t = T("merged", 26, GREEN_M).move_to(ub.get_top() + 0.35 * DOWN)
        u_cards = [M(c, 28, WHITE).move_to([0, ub.get_top()[1] - 1.0 - 0.6 * k, 0]) for k, c in enumerate([CARDS[1], CARDS[2]])]
        u_back = M(CARDS[0], 28, RED_M).move_to([0, ub.get_top()[1] - 1.0 - 0.6 * 2, 0])
        a_l = Arrow([BX["eu"] + BW / 2 + 0.03, -0.6, 0], [ub.get_left()[0] - 0.03, -0.6, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.3)
        a_r = Arrow([BX["us"] - BW / 2 - 0.03, -0.6, 0], [ub.get_right()[0] + 0.03, -0.6, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.3)
        self.steps("So the program has to merge them. The obvious merge: keep every card that's on either list. "
                   "That keeps the stolen card 5310. So far so good.", [
            (lambda: [*self.uncap(), FadeOut(wifi), FadeOut(wifi_l)], 0.4),
            "The obvious merge",
            (lambda: [FadeIn(ub), FadeIn(u_t), GrowArrow(a_l), GrowArrow(a_r), *self.cap("merge: every card on either list")], 0.8),
            (lambda: [FadeIn(u_cards[0], shift=0.1 * DOWN)], 0.4),
            "That keeps",
            (lambda: [FadeIn(u_cards[1], shift=0.1 * DOWN)], 0.4),
            (lambda: [Indicate(u_cards[1], color=GOLD_M, scale_factor=1.1)], 0.6),
        ])
        self.steps("But look. Card 4417 is back. EU removed it, but the US list still had it, and a missing card could mean removed, "
                   "or never added. The union can't tell which.", [
            "Card 4417",
            (lambda: [FadeIn(u_back, shift=0.1 * DOWN)], 0.5),
            (lambda: [Indicate(u_back, color=RED_M, scale_factor=1.15)], 0.6),
            "EU removed it",
            (lambda: [glow(s1, RED_M, 1.05)], 0.6),
            "the US list still",
            (lambda: [Indicate(cards["us"][0], color=GOLD_M, scale_factor=1.1)], 0.6),
            "a missing card",
            (lambda: self.cap("missing: removed, or never added? the union can't tell", RED_M), 0.6),
        ])
        self.steps("So the customer whose lost card turned up gets refused again. Version vectors noticed the clash. They didn't settle it.", [
            "gets refused",
            (lambda: [Wiggle(u_back, scale_value=1.1, rotation_angle=0.02 * TAU)], 0.9),
            "Version vectors noticed",
            (lambda: self.cap("vectors notice the clash; they don't settle it", WHITE), 0.6),
        ], after=0.4)

        # ---------------- scene 7: limits ----------------
        self.steps("Two more limits. Your code gets the siblings and has to merge them well, and the Dynamo paper warns about "
                   "exactly this: a deleted item can come back.", [
            "Your code",
            (lambda: [*self.cap("1. your code merges the siblings"), glow(ub, GREEN_M, 1.03)], 0.7),
            "a deleted item",
            (lambda: self.cap("Dynamo's warning: a deleted item can come back", RED_M), 0.6),
        ])
        self.steps("And the vector grows with every copy that takes writes. Dynamo cut its vectors at about ten entries. "
                   "Next, we'll meet data types that merge themselves, with no code from you.", [
            "the vector grows",
            (lambda: [*self.cap("2. one counter for every copy that takes writes"), Indicate(vec_us, color=GOLD_M, scale_factor=1.1)], 0.7),
            "about ten",
            (lambda: self.cap("Dynamo cut them at about 10 entries"), 0.5),
        ], after=0.4)

        # ---------------- scene 8: moral and a check ----------------
        self.steps("So, which list should the shop keep? Not the later one. Keep a version only if it saw the other. "
                   "If neither saw the other, keep both.", [
            (lambda: [FadeOut(VGroup(ub, u_t, *u_cards, u_back, a_l, a_r)), *self.cap("which list should the shop keep?", WHITE)], 0.6),
            "Not the later one",
            (lambda: self.cap("not the later one", RED_M), 0.4),
            "Keep a version",
            (lambda: self.cap("replace a version only if the new one saw it", GREEN_M), 0.5),
            "If neither",
            (lambda: [*self.cap("neither saw the other: keep both", YELLOW_M), glow(boxes["eu"][0], YELLOW_M, 1.02),
                      glow(boxes["us"][0], YELLOW_M, 1.02)], 0.8),
        ], after=0.5)
        new_mk = marks("eu", 4, 1).move_to([0, 0.4, 0])
        new_lab = T("merged write, via EU", 22, GREEN_M).next_to(new_mk, UP, buff=0.2)
        self.steps("One quick check. The program merges the siblings and writes the result through EU, with bookmarks 4 and 1. "
                   "Does it replace both siblings? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "writes the result",
            (lambda: [FadeIn(new_mk, shift=0.1 * UP), FadeIn(new_lab)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        chk_eu = M("4 ≥ 3,  1 ≥ 0", 26, GREEN_M).move_to([0, -0.6, 0])
        chk_us = M("4 ≥ 2,  1 ≥ 1", 26, GREEN_M).move_to([0, -1.2, 0])
        self.steps("Yes. Against EU's 3 and 0, it's ahead or equal on both. Against US's 2 and 1, the same. "
                   "It has read everything both siblings had.", [
            (lambda: self.uncap(), 0.3),
            "Against EU's",
            (lambda: [FadeIn(chk_eu, shift=0.1 * RIGHT), glow(boxes["eu"][0], TEAL_M, 1.02)], 0.6),
            "Against US's",
            (lambda: [FadeIn(chk_us, shift=0.1 * LEFT), glow(boxes["us"][0], GOLD_M, 1.02)], 0.6),
            "It has read",
            (lambda: [FadeOut(sib["eu"]), FadeOut(sib["us"]), *self.cap("it saw both siblings, so it replaces both", GREEN_M)], 0.6),
        ], after=0.3)
        self.play(*self.cap("keep a version only if the new one saw it", YELLOW_M, 30), run_time=0.7)
        self.wait(2.0)
